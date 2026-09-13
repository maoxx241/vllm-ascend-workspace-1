"""Local initialization guidance and non-secret identity snapshots."""
import json
import subprocess
import sys
import types

import pytest
import vaws_workspace_entry as entry


def configure(root):
    path = root / ".vaws-local/github.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema": "vaws.github.v1", "login": "alice"}))



def test_first_use_does_not_probe_network_and_notice_is_once(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network/child")))
    assert entry.workspace_entry(tmp_path)["state"] == "needs_github_user"
    assert entry.workspace_entry(tmp_path)["state"] == "identity_pending"
    assert not (tmp_path / ".vaws-local/github.json").exists()



def test_hidden_gui_hook_does_not_consume_visible_first_use_notice(tmp_path):
    assert entry.workspace_entry(tmp_path, announce=False)["state"] == "identity_pending"
    assert not (tmp_path / ".vaws-local/updates/onboarding-notice.json").exists()
    assert entry.workspace_entry(tmp_path)["state"] == "needs_github_user"



def test_missing_identity_after_client_initialization_is_a_repair(tmp_path):
    record = tmp_path / ".vaws-local/client-initialization.json"
    record.parent.mkdir()
    record.write_text('{"clients":{"codex":{"state":"configured"}}}')
    original = record.read_bytes()
    for announce in (False, True):
        result = entry.workspace_entry(tmp_path, announce=announce)
        assert result["state"] == "identity_missing"
        assert result["evidence"] == str(record)
        assert result["path"] == str(record.parent / "github.json")
        assert result["reference"] == entry.MAINTENANCE_REFERENCE
        assert record.read_bytes() == original
    assert not (record.parent / "updates/onboarding-notice.json").exists()



def test_local_entry_never_starts_children_or_updates(tmp_path, monkeypatch):
    configure(tmp_path)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("background process"))
    monkeypatch.setitem(sys.modules, "vaws_workspace_update", types.SimpleNamespace())
    assert entry.workspace_entry(tmp_path)["state"] == "configured"
    assert entry.workspace_entry(tmp_path, announce=False)["state"] == "configured"



def test_disabled_or_invalid_config_does_not_break_startup(tmp_path, monkeypatch):
    configure(tmp_path)
    state = tmp_path / ".vaws-local/updates"
    state.mkdir()
    config = state / "config.json"
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("child")))
    config.write_text('{"enabled": false}')
    assert entry.workspace_entry(tmp_path)["state"] == "disabled"
    config.write_text('{')
    assert entry.workspace_entry(tmp_path)["state"] == "unavailable"



def test_identity_copy_keeps_only_setup_fields_and_preserves_target(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    configure(source)
    identity_path = source / ".vaws-local/github.json"
    identity_path.write_text(json.dumps({"schema": "vaws.github.v1", "login": "alice", "github_user_id": 123,
                                         "forks": {"workspace": "alice/vllm-ascend-workspace-1"},
                                         "task_id": "do-not-copy", "token": "do-not-copy"}))
    entry.copy_workspace_identity(source, target)
    copied = target / ".vaws-local/github.json"
    assert json.loads(copied.read_text()) == {"schema": "vaws.github.v1", "login": "alice", "github_user_id": 123,
                                            "forks": {"workspace": "alice/vllm-ascend-workspace-1"}}
    copied.write_text('{"schema":"vaws.github.v1","login":"existing"}')
    entry.copy_workspace_identity(source, target)
    assert json.loads(copied.read_text())["login"] == "existing"
    assert not (target / ".vaws-local/updates/config.json").exists()
