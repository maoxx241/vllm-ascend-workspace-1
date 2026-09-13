"""Real locked installs prove an optional upgrade leaves the runtime intact."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
import vaws_environment as envs
from vaws_environment_capabilities import plans
from test_immutable_environment import workspace, execute, BASE
from vaws_knowledge_catalog import RELATIVE_PATH, locked_identity, frozen_catalog


def configure(root, version="1"):
    wheel = root.parent / f"vaws_knowledge-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("vaws_knowledge.py", f"VALUE = {version!r}\n")
        prefix = f"vaws_knowledge-{version}.dist-info"
        archive.writestr(prefix + "/METADATA", f"Metadata-Version: 2.1\nName: vaws-knowledge\nVersion: {version}\n")
        archive.writestr(prefix + "/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr(prefix + "/RECORD", "")
    url = (root / ".test-wheel-url").read_text()
    (root / "pyproject.toml").write_text(
        "[project]\nname='env-test'\nversion='0'\nrequires-python='>=3.11'\n"
        f"dependencies=['vaws-env-fixture @ {url}/vaws_env_fixture-1-py3-none-any.whl',"
        f"'vaws-knowledge @ {url}/{wheel.name}']\n"
        "[dependency-groups]\ndev=[]\n[tool.uv]\npackage=false\ndefault-groups=[]\n"
        "[tool.vaws.environment]\nsplit-knowledge=true\n", encoding="utf-8")
    result = subprocess.run(["uv", "lock", "--project", str(root), "--python", BASE],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    catalog = {"schema_version": 1, "owner": locked_identity((root / "uv.lock").read_bytes()),
               "tools": [{"name": "knowledge_query", "inputSchema": {"type": "object",
                         "properties": {"text": {"type": "string"}}, "required": ["text"],
                         "additionalProperties": False}}]}
    (root / RELATIVE_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / RELATIVE_PATH).write_text(json.dumps(catalog), encoding="utf-8")


def test_knowledge_upgrade_reuses_runtime_and_keeps_old_task_selection(workspace, monkeypatch):
    configure(workspace)
    first = envs.prepare_environment(workspace)
    assert first["schema_version"] == 2
    runtime = envs.capability_receipt(first)
    assert not Path(first["components"]["knowledge"]).exists()
    assert execute(runtime["python"], "import vaws_env_fixture;print(vaws_env_fixture.VALUE)") == "1"
    assert execute(runtime["python"], "import importlib.util;print(importlib.util.find_spec('vaws_knowledge'))") == "None"
    assert envs.native_ready(workspace) == first
    before = Path(runtime["receipt"]).read_bytes()
    configure(workspace, "2")
    second = envs.prepare_environment(workspace)
    assert first["key"] != second["key"]
    assert envs.capability_receipt(second)["receipt"] == runtime["receipt"]
    assert Path(runtime["receipt"]).read_bytes() == before
    # The old task first uses knowledge only after the checkout and selection
    # changed. Installation must consume its saved v1 lock, not current v2.
    knowledge = envs.capability_receipt(first, "knowledge", prepare_missing=True)
    assert envs.saved_ready(workspace) == second
    assert execute(envs.capability_receipt(second, "knowledge", prepare_missing=True)["python"], "import vaws_knowledge;print(vaws_knowledge.VALUE)") == "2"
    assert execute(knowledge["python"], "import vaws_knowledge;print(vaws_knowledge.VALUE)") == "1"
    assert envs.native_ready(workspace, pin=first["receipt"]) == first
    monkeypatch.setattr(envs, "_install", lambda *args: pytest.fail("warm sync installed packages"))
    assert envs.prepare_environment(workspace) == second
    monkeypatch.setattr(envs.subprocess, "run", lambda *args, **kw: pytest.fail("runtime read spawned a process"))
    assert envs.saved_ready(workspace) == second


def test_core_ready_without_knowledge_but_invalid_component_path_is_rejected(workspace):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    path = Path(ready["receipt"])
    invalid = {**ready, "components": {**ready["components"], "knowledge": ready["components"]["runtime"]}}
    path.write_text(json.dumps(invalid))
    with pytest.raises(envs.EnvironmentError, match="differs from its fixed selection"):
        envs.read_receipt(path)
    path.write_text(json.dumps(ready))
    assert envs.read_receipt(path) == ready
    with pytest.raises(envs.EnvironmentError, match="not prepared"):
        envs.capability_receipt(ready, "knowledge")


def test_status_catalog_and_core_reads_do_not_install_optional_owner(workspace, monkeypatch):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    monkeypatch.setattr(envs, "_install", lambda *args: pytest.fail("read installed optional packages"))
    monkeypatch.setattr(envs.subprocess, "run", lambda *args, **kw: pytest.fail("read started a process"))
    assert envs.read_receipt(ready["receipt"]) == ready
    assert envs.capability_receipt(ready)["root"] == ready["root"]
    assert frozen_catalog(ready)["tools"][0]["name"] == "knowledge_query"
    from vaws_dependency import capability_distribution, inspect
    from vaws_capability import probe_shared
    assert capability_distribution("vaws-knowledge", workspace) == (True, None)
    assert inspect("vaws-knowledge", workspace)["state"] == "missing"
    assert probe_shared(workspace)["status"] == "absent"
    assert not Path(ready["components"]["knowledge"]).exists()


@pytest.mark.parametrize("filename", ["pyproject.toml", "uv.lock", "knowledge-catalog.json"])
def test_corrupt_fixed_inputs_refuse_optional_use_but_leave_core_ready(workspace, monkeypatch, filename):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    frozen = Path(ready["receipt"]).parent / "inputs" / filename
    frozen.write_bytes(frozen.read_bytes() + b"\n# modified")
    monkeypatch.setattr(envs, "_install", lambda *args: pytest.fail("corrupt inputs used for installation"))
    assert envs.read_receipt(ready["receipt"]) == ready
    with pytest.raises(envs.EnvironmentError, match="hash differs|locked dependency inputs"):
        frozen_catalog(ready)
    with pytest.raises(envs.EnvironmentError, match="hash differs"):
        envs.capability_receipt(ready, "knowledge", prepare_missing=True)


def test_failed_optional_install_leaves_core_and_selection_unchanged(workspace, monkeypatch):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    before = Path(ready["receipt"]).read_bytes()
    def fail(*args):
        raise envs.EnvironmentError("synthetic install failure")
    monkeypatch.setattr(envs, "_install", fail)
    with pytest.raises(envs.EnvironmentError, match="synthetic install failure"):
        envs.capability_receipt(ready, "knowledge", prepare_missing=True)
    assert Path(ready["receipt"]).read_bytes() == before
    assert envs.saved_ready(workspace) == ready
    assert execute(ready["python"], "import vaws_env_fixture;print(vaws_env_fixture.VALUE)") == "1"


def test_legacy_bundle_ready_child_works_missing_child_has_explicit_remedy(workspace):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    legacy = {key: value for key, value in ready.items() if key not in ("frozen_inputs", "knowledge_catalog_sha256")}
    Path(ready["receipt"]).write_text(json.dumps(legacy))
    assert envs.read_receipt(ready["receipt"]) == legacy
    with pytest.raises(envs.EnvironmentError, match="legacy fixed selection"):
        envs.capability_receipt(legacy, "knowledge", prepare_missing=True)
    envs.capability_receipt(ready, "knowledge", prepare_missing=True)
    assert envs.capability_receipt(legacy, "knowledge")["key"] == ready["selection"]["components"]["knowledge"]
    assert frozen_catalog(legacy) is None


def test_concurrent_first_knowledge_use_publishes_one_fixed_child(workspace):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    from test_immutable_environment import clean_environment
    code = ("import sys,json;from vaws_environment import read_receipt,capability_receipt;"
            "print(json.dumps(capability_receipt(read_receipt(sys.argv[1]),'knowledge',prepare_missing=True)))")
    processes = [subprocess.Popen([sys.executable, "-X", "utf8", "-c", code, ready["receipt"]],
                 env=clean_environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
    results = [process.communicate(timeout=45) for process in processes]
    assert all(process.returncode == 0 for process in processes), results
    assert json.loads(results[0][0])["key"] == json.loads(results[1][0])["key"]
    assert envs.saved_ready(workspace) == ready


def test_projection_pin_mismatch_refuses_publication_before_install(workspace, monkeypatch):
    configure(workspace)
    path = workspace / RELATIVE_PATH
    catalog = json.loads(path.read_text())
    catalog["owner"]["version"] = "different"
    path.write_text(json.dumps(catalog))
    monkeypatch.setattr(envs, "_install", lambda *args: pytest.fail("mismatched catalog should be rejected first"))
    with pytest.raises(envs.EnvironmentError, match="differs from uv.lock"):
        envs.prepare_environment(workspace)


def test_explicit_development_environment_keeps_all_packages(workspace):
    configure(workspace)
    ready = envs.prepare_environment(workspace, groups=["dev"])
    assert ready["schema_version"] == 1
    assert execute(ready["python"], "import vaws_env_fixture,vaws_knowledge;print(vaws_knowledge.VALUE)") == "1"


def test_actual_lock_closures_keep_knowledge_out_of_runtime():
    root = Path(__file__).resolve().parents[2]
    _, lock, document, _, _ = envs._inputs(root)
    selected = plans(document, lock, {"groups": [], "extras": [], "project": True})
    assert "vaws-knowledge" in selected["runtime"]["exclude"]
    assert "openviking" in selected["runtime"]["exclude"]
    assert "vaws-coordinator" not in selected["runtime"]["exclude"]
    assert "tree-sitter" not in selected["knowledge"]["exclude"]
    assert "mcp" not in selected["knowledge"]["exclude"]
