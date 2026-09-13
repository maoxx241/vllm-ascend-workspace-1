"""Reference maintenance consumes the shared community choice without replacing it."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("workspace_knowledge_setup", ROOT / ".agents/scripts/knowledge_setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


@pytest.mark.parametrize("publishing", [{}, {"enabled": False},
    {"enabled": True, "repository": "example/references"},
    {"enabled": True, "repository": "example/references", "fork": "example/fork"}])
def test_default_setup_prepares_locally_without_changing_publishing(tmp_path, monkeypatch, capsys, publishing):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    path = tmp_path / ".vaws-local/knowledge/service.json"
    path.parent.mkdir(parents=True)
    original = json.dumps({"publishing": publishing, "custom": "preserve"}, indent=2)
    path.write_text(original, encoding="utf-8")
    calls = []
    monkeypatch.setattr(setup, "prepare_knowledge", lambda root: calls.append(root) or {"status": "ready", "ready": True})
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda *args: pytest.fail("default setup must not configure a public fork"))
    assert setup.main([]) == 0
    assert calls == [tmp_path]
    assert path.read_text(encoding="utf-8") == original
    assert json.loads(capsys.readouterr().out)["status"] == "ready"


def test_first_setup_delegates_local_configuration_to_package(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(setup, "prepare_knowledge", lambda root: calls.append(root) or {"status": "ready", "ready": True})
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda *args: pytest.fail("fresh setup must not create a fork"))
    assert setup.main([]) == 0
    assert calls == [tmp_path]


def save_choice(root, decision, *, identity=True):
    directory = root / ".vaws-local"
    directory.mkdir(parents=True, exist_ok=True)
    if decision is not None:
        (directory / "community.json").write_text(json.dumps({"schema": "vaws.community.v1", "workspace_id": "a"*32,
            "decision": decision, "revision": "b"*32}), encoding="utf-8")
    if identity:
        (directory / "github.json").write_text(json.dumps({"schema": "vaws.github.v1", "login": "alice", "forks": {}}), encoding="utf-8")


@pytest.mark.parametrize("decision,publishing,identity,read_only", [
    ("enabled", {"enabled": True, "fork": "example/fork"}, True, False),
    ("disabled", {"enabled": True, "fork": "example/fork"}, True, True),
    (None, {"enabled": True, "fork": "example/fork"}, True, True),
    ("enabled", {"enabled": True}, True, True),
    ("enabled", {"enabled": False, "fork": "example/fork"}, True, True),
    ("enabled", {"enabled": True, "fork": "example/fork"}, False, True),
])
def test_repository_change_retains_only_currently_authorized_publishing(tmp_path, monkeypatch, decision, publishing, identity, read_only):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    save_choice(tmp_path, decision, identity=identity)
    path = tmp_path / ".vaws-local/knowledge/service.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"publishing": publishing, "shared_sync": {"repository": "example/references"}}), encoding="utf-8")
    policy = tmp_path / ".vaws-local/community.json"
    previous = policy.read_bytes() if policy.exists() else None
    calls = []
    monkeypatch.setattr(setup, "prepare_knowledge", lambda root: {"status": "ready", "ready": True})
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda root, command: calls.append((root, command)) or (0, {"status": "configured"}))
    assert setup.main(["--repository", "example/new"]) == 0
    root, command = calls[0]
    assert root == tmp_path
    assert command[:4] == ["publishing", "configure", "--config", str(path)]
    assert command[command.index("--repository") + 1] == "example/new"
    assert command[command.index("--consent-file") + 1] == str(policy)
    if not read_only:
        assert command[command.index("--github-user") + 1] == "alice"
    assert ("--read-only" in command) is read_only
    assert (policy.read_bytes() if policy.exists() else None) == previous


def test_pending_preparation_is_reported_without_configuring_contribution(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup, "prepare_knowledge", lambda root: {"status": "pending", "ready": False, "reason": "offline"})
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda *args: pytest.fail("pending setup must not enable contribution"))
    assert setup.main([]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "offline"


@pytest.mark.parametrize("flag", ["--read-only", "--contribute"])
def test_old_contribution_flags_are_rejected_without_side_effects(tmp_path, monkeypatch, flag):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda *args: pytest.fail("removed flags must not configure contributions"))
    monkeypatch.setattr(setup, "prepare_knowledge", lambda *args: pytest.fail("removed flags must not start maintenance"))
    with pytest.raises(SystemExit) as caught:
        setup.main([flag])
    assert caught.value.code == 2
    assert not (tmp_path / ".vaws-local/community.json").exists()


def test_invalid_consent_keeps_repository_change_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    save_choice(tmp_path, "enabled")
    policy = tmp_path / ".vaws-local/community.json"
    policy.write_text("broken policy", encoding="utf-8")
    path = tmp_path / ".vaws-local/knowledge/service.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"publishing": {"enabled": True, "fork": "alice/references"}}), encoding="utf-8")
    operations = []
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda root, command: operations.append(command) or (0, {"status": "configured"}))
    monkeypatch.setattr(setup, "prepare_knowledge", lambda root: operations.append("prepare") or {"ready": True})
    assert setup.main(["--repository", "example/new"]) == 0
    assert "--read-only" in operations[0]
    assert operations[1] == "prepare"
    assert policy.read_text(encoding="utf-8") == "broken policy"


def test_configuration_failure_does_not_start_maintenance(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup, "run_knowledge_cli", lambda *args: (1, {"status": "error", "reason": "consent changed"}))
    monkeypatch.setattr(setup, "prepare_knowledge", lambda *args: pytest.fail("failed reconfiguration must remain pending"))
    assert setup.main(["--repository", "example/new"]) == 1


@pytest.mark.parametrize("decision", ["enabled", "disabled", None])
def test_linked_worktree_uses_its_owner_consent_identity_and_runtime_configuration(tmp_path, monkeypatch, capsys, decision):
    from vaws_knowledge_service import knowledge_server_env, shared_project_config

    primary = (tmp_path / "primary").resolve()
    linked = (tmp_path / "task").resolve()
    subprocess.run(["git", "init", "-q", str(primary)], check=True)
    subprocess.run(["git", "-C", str(primary), "-c", "user.name=fixture", "-c",
                    "user.email=fixture@example.com", "commit", "--allow-empty", "-qm", "fixture"], check=True)
    subprocess.run(["git", "-C", str(primary), "worktree", "add", "-q", "--detach", str(linked)], check=True)
    save_choice(primary, decision)
    monkeypatch.setenv("VAWS_COMMUNITY_POLICY", str(tmp_path / "unrelated-enabled-policy.json"))
    path = primary / ".vaws-local/knowledge/service.json"
    path.parent.mkdir(parents=True)
    original = {"publishing": {"enabled": True, "fork": "alice/references"},
                "shared_sync": {"repository": "example/references"}, "custom": "preserve"}
    path.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(setup, "ROOT", linked)
    calls = []

    def configure(root, command):
        calls.append(command)
        assert root == linked
        assert Path(command[command.index("--config") + 1]) == path
        assert Path(command[command.index("--consent-file") + 1]) == primary / ".vaws-local/community.json"
        if decision == "enabled":
            assert command[command.index("--github-user") + 1] == "alice"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["publishing"]["enabled"] = "--read-only" not in command
        payload["shared_sync"]["repository"] = command[command.index("--repository") + 1]
        path.write_text(json.dumps(payload), encoding="utf-8")
        return 0, {"status": "configured"}

    def prepare(root):
        assert calls, "configuration must finish before maintenance"
        assert shared_project_config(root) == path
        active = Path(knowledge_server_env(root)["VAWS_KNOWLEDGE_CONFIG"])
        return {"ready": True, "config": str(active), "active": json.loads(active.read_text(encoding="utf-8"))}

    monkeypatch.setattr(setup, "run_knowledge_cli", configure)
    monkeypatch.setattr(setup, "prepare_knowledge", prepare)
    assert setup.main(["--repository", "example/new"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["config"] == str(path)
    assert result["active"]["publishing"]["enabled"] is (decision == "enabled")
    assert result["active"]["publishing"]["fork"] == "alice/references"
    assert result["active"]["shared_sync"]["repository"] == "example/new"
    assert result["active"]["custom"] == "preserve"
    assert not (linked / ".vaws-local/knowledge/service.json").exists()
