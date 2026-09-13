"""Codex setup rebuilds reserved VAWS entries from the current configuration."""
import json
from pathlib import Path
import tomllib

import pytest

from test_gateway_client_setup import configured_project
from test_knowledge_client_setup import setup


@pytest.mark.parametrize("launcher", [".remote-dev/mcp/server.py", "retired-provider.py"])
def test_setup_replaces_reserved_entries_and_keeps_unrelated_configuration(launcher, configured_project):
    project, _, _ = configured_project
    path = project / ".codex/config.toml"
    path.parent.mkdir()
    before = ('# user settings\napproval_policy = "on-request"\n'
              '[mcp_servers.remote-dev]\ncommand = "python3"\n'
              f'args = [{json.dumps(launcher)}]\nstartup_timeout_sec = 31\n'
              '[mcp_servers.remote-dev.env]\nREMOTE_DEV_DEFAULT_ROOT = "/old-root"\n'
              '[mcp_servers.remote_dev]\ncommand = "duplicate-alias"\n'
              '[mcp_servers.remote_dev.tools.remote_read]\napproval_mode = "prompt"\n'
              '[mcp_servers.other]\ncommand = "user-provider"\n'
              '[mcp_servers.other.env]\nCUSTOM = "keep"\n')
    path.write_text(before)
    desired = setup.desired_mcp_servers()
    plan = setup.build_plan("codex", project)
    text = plan["files"][path]
    parsed = tomllib.loads(text)
    assert parsed["approval_policy"] == "on-request"
    assert text.startswith("# user settings\n")
    assert parsed["mcp_servers"]["other"] == {"command": "user-provider", "env": {"CUSTOM": "keep"}}
    assert set(parsed["mcp_servers"]) == {"remote_dev", "vaws_task", "vaws_knowledge", "other"}
    for name, entry in desired.items():
        assert parsed["mcp_servers"][name.replace("-", "_")] == {
            key: entry[key] for key in ("command", "args", "env")}
    changed = setup.apply_plan(plan)
    backup = next(item["backup"] for item in changed if item["path"] == str(path))
    assert Path(backup).read_text() == before
    repeated = setup.build_plan("codex", project)
    assert repeated["files"].get(path, text) == text
    assert setup.apply_plan(repeated) == []


def test_task_only_replaces_only_task_configuration(configured_project):
    project, _, _ = configured_project
    path = project / ".codex/config.toml"
    path.parent.mkdir()
    before = ('[mcp_servers.vaws-task]\ncommand = "old-task"\n'
              '[mcp_servers.vaws-task.env]\nVAWS_AGENT_SESSIONS_DIR = "/retired-sessions"\n'
              '[mcp_servers.remote_dev]\ncommand = "keep-remote"\n'
              '[mcp_servers.vaws_knowledge]\ncommand = "keep-knowledge"\n')
    path.write_text(before)
    plan = setup.build_plan("codex", project, task_only=True)
    providers = tomllib.loads(plan["files"][path])["mcp_servers"]
    assert providers["remote_dev"] == {"command": "keep-remote"}
    assert providers["vaws_knowledge"] == {"command": "keep-knowledge"}
    assert "vaws-task" not in providers
    assert providers["vaws_task"]["args"][-1] == "task"
    assert "/retired-sessions" not in json.dumps(providers["vaws_task"])
    assert "/retired-sessions" not in plan["files"][project / ".codex/hooks.json"]


def test_ambiguous_toml_fails_before_applying_any_files(configured_project):
    project, _, _ = configured_project
    path = project / ".codex/config.toml"
    path.parent.mkdir()
    before = 'note = """\n[mcp_servers.remote_dev]\nkeep this user text\n"""\n'
    path.write_text(before)
    with pytest.raises((ValueError, tomllib.TOMLDecodeError)):
        setup.build_plan("codex", project)
    assert path.read_text() == before
    assert list(path.parent.iterdir()) == [path]
