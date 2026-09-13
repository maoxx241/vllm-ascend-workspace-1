"""One native task adopts canonical inputs once without changing its attachment."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".agents/lib"), str(ROOT / ".agents/scripts")]
spec = importlib.util.spec_from_file_location("vaws_start_test", ROOT / ".agents/scripts/vaws_start.py")
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)
from vaws_coordinator.agent_session import AgentSessions


def git(path, *args):
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(path), *args],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


def commit(path, message):
    git(path, "add", ".")
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", message)
    return git(path, "rev-parse", "HEAD")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    project, stage = tmp_path / "母仓 project", tmp_path / "canonical stage"
    project.mkdir()
    git(project, "init", "-b", "main")
    (project / ".gitignore").write_text(".vaws-local/\n", encoding="utf-8")
    (project / "README").write_text("old\n", encoding="utf-8")
    old = commit(project, "old")
    git(project, "worktree", "add", "--detach", str(stage), old)
    (stage / "README").write_text("canonical latest\n", encoding="utf-8")
    (stage / "uv.lock").write_text("new locked components\n", encoding="utf-8")
    latest = commit(stage, "latest")
    git(project, "switch", "-c", "feature-work")
    (project / "README").write_text("keep local work\n", encoding="utf-8")
    (project / "untracked.txt").write_text("keep untracked work\n", encoding="utf-8")
    receipt = {"key": "latest-environment", "python": sys.executable,
               "receipt": str(tmp_path / "latest-ready.json")}
    calls, selected = [], {}

    class Updater:
        def __init__(self, root):
            assert root == project
            self.state = {"prepared": {"stage": str(stage), "receipt": receipt, "knowledge": {"ready": True}}}

        def step(self, **kwargs):
            calls.append(("update", kwargs))
            assert kwargs == {"apply": True, "activate": False}
            return {"status": "ready", "target": latest, "branch": "main"}

        def validate_prepared(self, result, prepared):
            assert result["target"] == latest
            return Path(prepared["stage"])

    def select(path, chosen):
        selected[path] = chosen
        file = path / ".vaws-local/environment-selection" / f"{sys.platform}.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(chosen), encoding="utf-8")

    monkeypatch.setattr(start, "WorkspaceUpdater", Updater)
    monkeypatch.setattr(start, "select_environment", select)
    monkeypatch.setattr(start, "saved_ready", lambda path: selected[path])
    def read_fixed(path):
        assert path == receipt["receipt"]
        return receipt
    monkeypatch.setattr(start, "read_receipt", read_fixed)
    monkeypatch.setattr(start, "resolve_context_file", lambda explicit: explicit)
    monkeypatch.setattr(start, "configure_target", lambda client, target, chosen, env:
                        calls.append(("configure", client, target, chosen, env)))
    monkeypatch.setattr(start, "prepare_selected_knowledge", lambda target, chosen: {"ready": True})
    monkeypatch.setenv("VAWS_ENV_RECEIPT", "old-parent-environment")
    store = AgentSessions(tmp_path / "native-registry")
    return project, stage, latest, receipt, calls, selected, select, store


@pytest.mark.parametrize("client", start.CLIENTS)
def test_new_task_uses_canonical_worktree_and_preserves_native_cwd(workspace, client):
    project, _, latest, receipt, calls, _, _, store = workspace
    context = store.attach(client, "actual-native-session", str(project))
    result = start.start(client, project, context["context_file"])
    assert result["status"] == "ready", result
    target = Path(result["workspace"])
    assert target.parent == project.parent and target != project
    assert result["head"] == latest
    assert result["environment"] == receipt
    assert result["knowledge"] == {"ready": True}
    assert (target / "README").read_text(encoding="utf-8") == "canonical latest\n"
    assert not (target / "untracked.txt").exists()
    assert (project / "README").read_text(encoding="utf-8") == "keep local work\n"
    assert (project / "untracked.txt").read_text(encoding="utf-8") == "keep untracked work\n"
    assert git(project, "branch", "--show-current") == "feature-work"
    current = store.context(context["attachment"]["id"])
    assert current["attachment"] == context["attachment"]
    assert current["source_defaults"]["origin"] == "explicit"
    assert current["source_defaults"]["sources"][project.name]["path"] == str(target)
    configured = next(call for call in calls if call[0] == "configure")
    assert configured[3] == receipt and "VAWS_ENV_RECEIPT" not in configured[4]
    before = list(calls)
    latest_runtime = project / ".vaws-local/latest-runtime.json"
    assert json.loads(latest_runtime.read_text(encoding="utf-8")) == {key: result[key] for key in ("workspace", "environment", "head")}
    runtime_time = latest_runtime.stat().st_mtime_ns
    (target / "README").write_text("ongoing task edits\n", encoding="utf-8")
    repeated = start.start(client, target, context["context_file"])
    assert repeated["status"] == "reused" and repeated["workspace"] == str(target)
    assert calls == before and (target / "README").read_text(encoding="utf-8") == "ongoing task edits\n"
    assert latest_runtime.stat().st_mtime_ns == runtime_time


def test_prepared_native_old_ref_reuses_its_directory_and_receipt(workspace):
    project, stage, _, _, calls, _, select, store = workspace
    old_receipt = {"key": "native-old", "python": sys.executable, "receipt": "/old/selected.json"}
    git(stage, "checkout", "--detach", git(project, "rev-parse", "HEAD"))
    select(stage, old_receipt)
    config = project / ".vaws-local/knowledge/service.json"
    config.parent.mkdir(parents=True)
    config.write_text("{}", encoding="utf-8")
    context = store.attach("codex", "native-prepared", str(stage))
    result = start.start("codex", project, context["context_file"])
    assert result["status"] == "ready" and result["preparation"] == "native"
    assert result["workspace"] == str(stage)
    assert result["environment"] == old_receipt
    assert result["knowledge_config"] == str(config)
    assert calls == []
    assert not (project / ".vaws-local/latest-runtime.json").exists()
    assert store.context(context["attachment"]["id"])["attachment"] == context["attachment"]


def test_a_second_task_gets_a_separate_directory(workspace):
    project, _, _, _, _, _, _, store = workspace
    first = store.attach("grok", "native-first", str(project))
    second = store.attach("grok", "native-second", str(project))
    a = start.start("grok", project, first["context_file"])
    b = start.start("grok", project, second["context_file"])
    assert a["status"] == b["status"] == "ready"
    assert a["workspace"] != b["workspace"]


def test_repeat_keeps_task_receipt_after_explicit_workspace_maintenance(workspace):
    project, _, _, receipt, calls, _, select, store = workspace
    context = store.attach("codex", "native-fixed-runtime", str(project))
    first = start.start("codex", project, context["context_file"])
    target = Path(first["workspace"])
    maintained = {"key": "maintenance-environment", "python": sys.executable, "receipt": "/new/ready.json"}
    select(target, maintained)
    before = list(calls)
    repeated = start.start("codex", target, context["context_file"])
    assert repeated["status"] == "reused" and repeated["environment"] == receipt
    assert start.saved_ready(target) == maintained
    assert calls == before


def test_missing_or_wrong_native_identity_never_prepares(workspace, monkeypatch):
    project, _, _, _, calls, _, _, store = workspace
    context = store.attach("kimi", "native-kimi", str(project))
    result = start.start("grok", project, context["context_file"])
    assert result["status"] == "failed" and result["phase"] == "context"
    monkeypatch.setattr(start, "resolve_context_file", lambda _: (_ for _ in ()).throw(ValueError("native context required")))
    assert start.start("grok", project)["status"] == "failed"
    assert calls == []


def test_failed_update_returns_evidence_without_binding_or_creating(workspace, monkeypatch):
    project, _, _, _, _, _, _, store = workspace
    context = store.attach("cursor", "native-update-failed", str(project))

    def failed(self, **kwargs):
        return {"status": "deferred", "reason": "network_unavailable", "log": "/raw/updater-log.json"}

    monkeypatch.setattr(start.WorkspaceUpdater, "step", failed)
    result = start.start("cursor", project, context["context_file"])
    assert result["status"] == "failed" and result["phase"] == "upstream"
    assert json.loads(Path(result["evidence"]).read_text(encoding="utf-8"))["details"]["log"] == "/raw/updater-log.json"
    assert store.context(context["attachment"]["id"])["source_defaults"]["origin"] != "explicit"
    assert not (project.parent / (project.name + "-" + context["session"]["id"])).exists()


def test_first_use_returns_setup_before_dependency_or_native_context_checks(workspace, monkeypatch, capsys):
    project = workspace[0]
    monkeypatch.setattr(start, "ROOT", project)
    monkeypatch.setattr(start, "ensure_workspace_interpreter", lambda **kwargs: pytest.fail("first use bootstrapped dependencies"))
    monkeypatch.setattr(start, "resolve_context_file", lambda *_: pytest.fail("first use required a native attachment"))
    assert start.main(["--client", "grok"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "needs_setup" and result["phase"] == "initialization"
    assert result["reference"] == ".agents/bootstrap/repo-init/SKILL.md"
    assert "ask once" in result["next"]
    assert not (project / ".vaws-local/updates/onboarding-notice.json").exists()


@pytest.mark.parametrize("failure", ["missing_identity", "invalid_identity", "invalid_config"])
def test_established_configuration_failure_never_routes_to_first_use(workspace, monkeypatch, capsys, failure):
    project = workspace[0]
    state = project / ".vaws-local"
    state.mkdir(exist_ok=True)
    (state / "client-initialization.json").write_text('{"clients":{}}')
    if failure != "missing_identity":
        (state / "github.json").write_text(json.dumps(
            {"schema": "vaws.github.v1", "login": "fixture" if failure == "invalid_config" else ""}))
    if failure == "invalid_config":
        updates = state / "updates"
        updates.mkdir()
        (updates / "config.json").write_text("{")
    monkeypatch.setattr(start, "ROOT", project)
    monkeypatch.setattr(start, "ensure_workspace_interpreter", lambda **kwargs: pytest.fail("configuration failure installed dependencies"))
    monkeypatch.setattr(start, "start", lambda *args: pytest.fail("configuration failure started a task"))
    assert start.main(["--client", "codex"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "failed"
    assert result["reference"] == start.MAINTENANCE_REFERENCE
    assert "repo-init" not in json.dumps(result)
    assert not (state / "updates/onboarding-notice.json").exists()


def test_configured_repository_starts_without_bootstrap_rerun(workspace, monkeypatch, capsys):
    project = workspace[0]
    identity = project / ".vaws-local/github.json"
    identity.parent.mkdir(exist_ok=True)
    identity.write_text('{"schema":"vaws.github.v1","login":"fixture"}')
    before = identity.read_bytes()
    monkeypatch.setattr(start, "ROOT", project)
    calls = []
    monkeypatch.setattr(start, "ensure_workspace_interpreter", lambda **kwargs: calls.append("environment"))
    monkeypatch.setattr(start, "start", lambda *args: calls.append(args) or {"status": "ready"})
    assert start.main(["--client", "codex", "--context-file", "native.json"]) == 0
    assert calls == ["environment", ("codex", project, "native.json")]
    assert json.loads(capsys.readouterr().out) == {"status": "ready"}
    assert identity.read_bytes() == before
    assert not (project / ".vaws-local/client-initialization.json").exists()
