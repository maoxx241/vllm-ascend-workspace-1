"""Native subprocess download/resume/verify lifecycle with offline SDK/API fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / ".agents/skills/modelscope/scripts"
pytestmark = pytest.mark.skipif(os.name != "nt", reason="native Windows process regression")


def test_status_preserves_worker_and_resume_verification(tmp_path):
    fixture = tmp_path / "fixtures"
    fixture.mkdir()
    ready = fixture / "sdk-ready"
    release = fixture / "sdk-release"
    data = b"partial bytes continued by the SDK fixture\n"
    metadata = {"Success": True, "Data": {"Files": [
        {"Type": "blob", "Path": "weights.bin", "Size": len(data), "Sha256": hashlib.sha256(data).hexdigest()}
    ]}}
    (fixture / "requests.py").write_text(
        "class Response:\n    def raise_for_status(self): pass\n    def json(self): return " + repr(metadata) +
        "\nclass Session:\n    def get(self,*a,**k): return Response()\n", encoding="utf-8")
    (fixture / "modelscope.py").write_text(
        "from pathlib import Path\nimport time\n"
        "def snapshot_download(model_id,revision,local_dir,max_workers=None,**kwargs):\n"
        "    root=Path(local_dir); path=root/'weights.bin'; data=" + repr(data) + "\n"
        "    previous=path.read_bytes() if path.exists() else b''\n"
        "    assert data.startswith(previous)\n"
        "    control=Path(__file__).parent\n"
        "    (control/'sdk-ready').write_text('ready',encoding='utf-8')\n"
        "    deadline=time.monotonic()+90\n"
        "    while not (control/'sdk-release').is_file():\n"
        "        if time.monotonic()>=deadline: raise TimeoutError('SDK fixture release marker was not received')\n"
        "        time.sleep(.05)\n"
        "    with path.open('ab') as f: f.write(data[len(previous):])\n"
        "    return str(root)\n", encoding="utf-8")
    local = tmp_path / "中文 🧪 model"
    local.mkdir()
    (local / "weights.bin").write_bytes(data[:7])
    env = {**os.environ, "PYTHONPATH": str(fixture)}
    def run(action):
        result = subprocess.run([sys.executable, str(SCRIPTS / "modelscope_auto.py"), action,
                                 "--model", "fixture/tiny=" + str(local)], env=env,
                                capture_output=True, timeout=20)
        return result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8")
    sys.path.insert(0, str(ROOT / ".agents/lib"))
    from vaws_windows import pid_alive
    pid = None
    try:
        code, out, err = run("ensure")
        assert code == 0 and "download-started" in out, (out, err)
        record = json.loads((local / "download.pid").read_text(encoding="utf-8"))
        pid = record["pid"]
        deadline = time.monotonic() + 15
        while not ready.is_file() and pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(.1)
        assert ready.is_file(), "SDK worker did not reach the controlled active phase"
        code, out, err = run("status")
        assert code == 0 and "active" in out, (out, err)
        assert pid_alive(pid), "status terminated the running worker"
        code, out, err = run("ensure")
        assert code == 0 and json.loads((local / "download.pid").read_text(encoding="utf-8"))["pid"] == pid
        assert (local / "weights.bin").read_bytes() == data[:7]
        release.touch()
        deadline = time.monotonic() + 15
        while pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(.1)
        assert not pid_alive(pid)
        assert (local / "weights.bin").read_bytes() == data
        assert json.loads((local / "modelscope_sha256.report.json").read_text(encoding="utf-8"))["all_ok"]
        assert (local / "SHA256SUMS").is_file()
        code, out, err = run("status")
        assert code == 0 and "verified" in out, (out, err)
        (local / "weights.bin").write_bytes(b"X" * len(data))
        code, out, err = run("status")
        assert code == 0 and "needs-verify" in out and "verify=stale" in out, (out, err)
        code, out, err = run("verify")
        assert code == 1 and "verify=failed" in out, (out, err)
        code, out, err = run("ensure")
        assert code == 0 and "verify-failed" in out, (out, err)
        assert (local / "weights.bin").read_bytes() == b"X" * len(data)
    finally:
        release.touch()
        if pid is not None and pid_alive(pid):
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
