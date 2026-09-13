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


def test_knowledge_upgrade_reuses_runtime_and_keeps_old_task_selection(workspace, monkeypatch):
    configure(workspace)
    first = envs.prepare_environment(workspace)
    assert first["schema_version"] == 2
    runtime = envs.capability_receipt(first)
    knowledge = envs.capability_receipt(first, "knowledge")
    assert execute(runtime["python"], "import vaws_env_fixture;print(vaws_env_fixture.VALUE)") == "1"
    assert execute(runtime["python"], "import importlib.util;print(importlib.util.find_spec('vaws_knowledge'))") == "None"
    assert execute(knowledge["python"], "import vaws_knowledge;print(vaws_knowledge.VALUE)") == "1"
    assert envs.native_ready(workspace) == first
    before = Path(runtime["receipt"]).read_bytes()
    configure(workspace, "2")
    second = envs.prepare_environment(workspace)
    assert first["key"] != second["key"]
    assert envs.capability_receipt(second)["receipt"] == runtime["receipt"]
    assert Path(runtime["receipt"]).read_bytes() == before
    assert execute(envs.capability_receipt(second, "knowledge")["python"], "import vaws_knowledge;print(vaws_knowledge.VALUE)") == "2"
    assert execute(knowledge["python"], "import vaws_knowledge;print(vaws_knowledge.VALUE)") == "1"
    assert envs.native_ready(workspace, pin=first["receipt"]) == first
    monkeypatch.setattr(envs, "_install", lambda *args: pytest.fail("warm sync installed packages"))
    assert envs.prepare_environment(workspace) == second
    monkeypatch.setattr(envs.subprocess, "run", lambda *args, **kw: pytest.fail("runtime read spawned a process"))
    assert envs.saved_ready(workspace) == second


def test_partial_or_mismatched_component_cannot_be_ready(workspace):
    configure(workspace)
    ready = envs.prepare_environment(workspace)
    path = Path(ready["receipt"])
    invalid = {**ready, "components": {**ready["components"], "knowledge": ready["components"]["runtime"]}}
    path.write_text(json.dumps(invalid))
    with pytest.raises(envs.EnvironmentError, match="differs from its fixed selection"):
        envs.read_receipt(path)
    path.write_text(json.dumps(ready))
    Path(ready["components"]["knowledge"]).unlink()
    with pytest.raises(envs.EnvironmentError, match="not ready"):
        envs.read_receipt(path)


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
