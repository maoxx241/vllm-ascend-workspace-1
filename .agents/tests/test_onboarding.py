"""First-use decisions, interrupted setup and revocation use real local state."""
import json
from pathlib import Path

import pytest

import vaws_community as community
import vaws_onboarding as onboarding
import vaws_workspace_entry as entry


class GitHub:
    def __init__(self):
        self.calls = []

    def api(self, endpoint):
        self.calls.append(endpoint)
        assert endpoint == "user"
        return {"login": "alice", "id": 12, "type": "User"}

    def ensure_star(self, repository):
        self.calls.append("star")
        return {"state": "starred"}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    import vaws_local_state
    monkeypatch.setattr(vaws_local_state, "shared_workspace_root", lambda root: Path(root))
    calls = []
    account = GitHub()
    def runner(command, root, environment):
        calls.append(command)
        assert environment["VAWS_COMMUNITY_POLICY"] == str(root / ".vaws-local/community.json")
        if "sync" in command:
            return {"ok": True, "receipt": {"python": "fixed-python", "key": "fixed"}}
        return {"state": "configured"}
    def knowledge(root, decision, login, **kwargs):
        calls.append(["knowledge", decision, login])
        assert community.read_choice(root)["decision"] == decision
        return {"configured": True}
    monkeypatch.setattr(onboarding, "configure_knowledge", knowledge)
    monkeypatch.setattr(onboarding, "configure_reporting", lambda *args: calls.append(["worker"]) or {"state": "running"})
    return tmp_path, account, calls, runner


def initialize(setup, **kwargs):
    root, account, calls, runner = setup
    return onboarding.initialize(root, github=account, runner=runner, **kwargs)


def test_unanswered_choices_do_not_create_fork_star_or_enable_contribution(setup):
    root, account, calls, _ = setup
    result = initialize(setup, github_user="alice")
    assert result["state"] == "needs_choices"
    assert account.calls == calls == []
    assert not (root / ".vaws-local/community.json").exists()
    assert not (root / ".vaws-local/github.json").exists()


def test_declined_features_keep_identity_and_no_upload_worker(setup):
    root, account, calls, _ = setup
    result = initialize(setup, github_user="alice", fork=False, star=False, community="disabled")
    assert result["state"] == "ready"
    assert account.calls == []
    assert ["worker"] not in calls
    assert json.loads((root / ".vaws-local/github.json").read_text())["forks"] == {}
    assert entry.workspace_entry(root)["state"] == "configured"


def test_ready_reuses_answers_without_auth_install_write_or_star(setup):
    root, account, calls, _ = setup
    first = initialize(setup, github_user="alice", fork=False, star=True, community="enabled")
    assert first["state"] == "ready"
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
              for path in (root / ".vaws-local/onboarding.json", root / ".vaws-local/community.json")}
    counts = len(account.calls), len(calls)
    second = initialize(setup)
    assert second["reused"] is True
    assert (len(account.calls), len(calls)) == counts
    assert before == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}


def test_resume_preserves_selected_client(setup):
    root, account, calls, _ = setup
    assert initialize(setup, github_user="alice", fork=False, star=False, community="disabled", client="codex")["state"] == "ready"
    previous_calls = list(calls)
    assert initialize(setup)["reused"] is True
    assert calls == previous_calls


def test_optional_service_failure_does_not_block_task_setup_and_retries_only_that_stage(setup, monkeypatch):
    root, account, calls, _ = setup
    def unavailable(*args):
        raise RuntimeError("service unavailable")
    monkeypatch.setattr(onboarding, "configure_reporting", unavailable)
    first = initialize(setup, github_user="alice", fork=False, star=False, community="enabled")
    assert first["state"] == "ready" and first["pending_optional"] == ["reporting"]
    assert first["collaboration_state"] == "pending"
    assert entry.workspace_entry(root)["state"] == "configured"
    old_calls = list(calls)
    monkeypatch.setattr(onboarding, "configure_reporting", lambda *args: {"state": "running"})
    second = initialize(setup)
    assert second["pending_optional"] == [] and second["collaboration_state"] == "configured"
    assert calls == old_calls and account.calls == []


def test_failure_after_identity_is_incomplete_and_resumes_only_failed_stages(setup, monkeypatch):
    root, account, calls, runner = setup
    def failing(command, root, environment):
        raise RuntimeError("package network failure")
    failed = onboarding.initialize(root, github=account, runner=failing, github_user="alice",
                                    fork=False, star=False, community="disabled")
    assert failed["state"] == "pending" and failed["phase"] == "dependencies"
    assert (root / ".vaws-local/github.json").exists()
    assert entry.workspace_entry(root)["state"] == "setup_pending"
    result = initialize(setup)
    assert result["state"] == "ready"
    assert account.calls == []


def test_revocation_happens_before_failing_reconfiguration_and_keeps_other_workspace(setup, monkeypatch):
    root, account, calls, runner = setup
    assert initialize(setup, github_user="alice", fork=False, star=False, community="enabled")["state"] == "ready"
    original = community.read_choice(root)
    other = root / "unrelated"
    other_choice = community.write_choice(other, "enabled")
    def failing(root, decision, login, **kwargs):
        assert community.read_choice(root)["decision"] == "disabled"
        raise RuntimeError("unavailable owner")
    monkeypatch.setattr(onboarding, "configure_knowledge", failing)
    result = initialize(setup, community="disabled")
    assert result["state"] == "ready" and result["collaboration_state"] == "pending"
    assert community.read_choice(root)["workspace_id"] == original["workspace_id"]
    assert community.read_choice(root)["revision"] != original["revision"]
    assert community.read_choice(other) == other_choice


def test_choice_is_not_implicitly_authorized_and_revision_is_idempotent(setup):
    root, *_ = setup
    assert community.read_choice(root) is None
    enabled = community.write_choice(root, "enabled")
    assert community.write_choice(root, "enabled") == enabled
    disabled = community.write_choice(root, "disabled")
    reenabled = community.write_choice(root, "enabled")
    assert len({enabled["revision"], disabled["revision"], reenabled["revision"]}) == 3
    assert enabled["workspace_id"] == disabled["workspace_id"] == reenabled["workspace_id"]


def test_malformed_choice_fails_closed_without_replacing_prior_record(setup):
    root, *_ = setup
    path = root / ".vaws-local/community.json"
    path.parent.mkdir()
    path.write_text('{"schema":"vaws.community.v1","decision":true}')
    original = path.read_bytes()
    with pytest.raises(ValueError, match="invalid"):
        community.write_choice(root, "enabled")
    assert path.read_bytes() == original


def test_task_policy_comes_from_explicit_owner_not_inherited_environment(setup, monkeypatch):
    root, *_ = setup
    from vaws_community import community_environment, local_policy_path
    env = community_environment(root, {"VAWS_COMMUNITY_POLICY": "foreign", "CUSTOM": "keep"})
    assert env == {"VAWS_COMMUNITY_POLICY": str(root / ".vaws-local/community.json"), "CUSTOM": "keep"}
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("bootstrap spawned a process"))
    assert local_policy_path(root) == root / ".vaws-local/community.json"


def test_opt_out_before_setup_does_not_require_fork_star_answers_or_auth(setup):
    root, account, calls, _ = setup
    state = root / ".vaws-local"
    state.mkdir()
    (state / "github.json").write_text('{"schema":"vaws.github.v1","login":"alice"}')
    config = state / "knowledge/service.json"
    config.parent.mkdir()
    config.write_text('{"publishing":{"enabled":true,"fork":"alice/references"},"custom":"preserve"}')
    result = initialize(setup, community="disabled")
    assert result["state"] == "choice_updated"
    assert community.read_choice(root)["decision"] == "disabled"
    assert json.loads(config.read_text())["publishing"]["enabled"] is False
    assert json.loads(config.read_text())["custom"] == "preserve"
    assert account.calls == []
    assert calls == []


def test_resume_never_reenables_a_revoked_choice_from_old_onboarding_record(setup):
    root, account, calls, _ = setup
    assert initialize(setup, github_user="alice", fork=False, star=False, community="enabled")["state"] == "ready"
    revoked = community.write_choice(root, "disabled")
    count = len(account.calls)
    resumed = initialize(setup)
    assert resumed["state"] == "ready"
    assert resumed["choices"]["community"] == "disabled"
    assert community.read_choice(root) == revoked
    assert len(account.calls) == count


def test_dependency_change_reconfigures_consumers_without_repeating_github_choices(setup):
    root, account, calls, _ = setup
    assert initialize(setup, github_user="alice", fork=False, star=True, community="enabled")["state"] == "ready"
    calls.clear()
    (root / "uv.lock").write_text("updated exact dependency closure")
    result = initialize(setup)
    assert result["state"] == "ready" and not result["reused"]
    assert account.calls == ["user", "star"]
    assert len(calls) == 4  # dependency, client, knowledge, reporter
    calls.clear()
    assert initialize(setup)["reused"] is True
    assert calls == []


def test_disabled_knowledge_does_not_prepare_or_launch_an_owner(tmp_path, monkeypatch):
    import vaws_local_state
    import vaws_knowledge_service
    monkeypatch.setattr(vaws_local_state, "shared_workspace_root", lambda root: Path(root))
    monkeypatch.setattr(vaws_knowledge_service, "_run_knowledge", lambda *a, **k: pytest.fail("unneeded owner launch"))
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("unneeded owner preparation"))
    result = onboarding.configure_knowledge(tmp_path, "disabled", "alice")
    assert result["owner_prepared"] is False
    config = tmp_path / ".vaws-local/knowledge/service.json"
    assert not config.exists()
    config.parent.mkdir(parents=True)
    config.write_text('{"publishing":{"enabled":true}}')
    onboarding.configure_knowledge(tmp_path, "disabled", "alice")
    assert json.loads(config.read_text())["publishing"]["enabled"] is False
