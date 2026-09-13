"""Repo-init prepares references without consuming an existing public queue."""
import json
from types import SimpleNamespace

import pytest

import vaws_onboarding as onboarding
from vaws_knowledge import publishing
from vaws_knowledge.contribution.pending import iter_pending, pending_dir
from vaws_knowledge.server.capture import capture
from vaws_knowledge.server.layers import load_config


@pytest.mark.parametrize(("shared_enabled", "explicit_reference_repository"), [(False, True), (True, True), (True, False)])
def test_reference_preparation_cannot_reload_publishing_or_modify_pending_records(
        tmp_path, monkeypatch, capsys, shared_enabled, explicit_reference_repository):
    # Exercise the production load_config -> maintain -> run_once path with a
    # real authorized pending record. Only reference transport is a fixture;
    # the memory backend runs real catalog and Markdown index preparation.
    policy = tmp_path / "community.json"
    policy.write_text(json.dumps({"schema": "vaws.community.v1", "workspace_id": "1" * 32,
                                 "decision": "enabled", "revision": "a" * 32}), encoding="utf-8")
    shared_root = tmp_path / "shared"
    shared_root.mkdir()
    (shared_root / "reference.md").write_text("# Reference\n\nReusable local reference.\n", encoding="utf-8")
    path = tmp_path / "service.json"
    path.write_text(json.dumps({
        "backend": "memory", "state_root": str(tmp_path / "state"),
        "layers": {"candidate": {"root": str(tmp_path / "candidate")},
                   "project": {"enabled": False},
                   "shared": {"roots": [str(shared_root)], "enabled": shared_enabled}},
        "shared_sync": {"enabled": shared_enabled, **({"repository": "fixture/reference-corpus"}
                                                      if explicit_reference_repository else {})},
        "publishing": {"enabled": True, "repository": "fixture/contribution-corpus", "fork": "alice/corpus",
                       "consent_file": str(policy), "git_repo": str(tmp_path / "fork")},
    }), encoding="utf-8")
    monkeypatch.setenv("VAWS_KNOWLEDGE_CONFIG", str(path))
    monkeypatch.setenv("VAWS_DIAGNOSTICS_ROOT", str(tmp_path / "diagnostics"))
    monkeypatch.setenv("VAWS_COMMUNITY_POLICY", str(policy))
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.setenv(name, "")

    def forbidden(*args, **kwargs):
        pytest.fail("Reference preparation attempted credentials, public contribution, network, or model/server setup")

    monkeypatch.setattr("vaws_knowledge.github_transport.github_token", forbidden)
    monkeypatch.setattr("vaws_knowledge.contribution.github.UrllibContributionGitHub", forbidden)
    monkeypatch.setattr(publishing, "submit_pending", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("vaws_knowledge.local.instance.LocalInstance.ensure", forbidden)

    original = load_config(path=path, env={})
    saved = capture(title="Existing pending contribution", content="This record must remain available for its authorized worker.",
                    config=original, index=False)
    assert saved["contribution"]["status"] == "pending"
    records = iter_pending(original.state_root)
    assert len(records) == 1
    assert publishing.publication_allowed(publishing.current_publishing(original), records[0])
    before_config, before_policy = path.read_bytes(), policy.read_bytes()
    queue = pending_dir(original.state_root)
    before_queue = {item.name: item.read_bytes() for item in queue.glob("*.json")}

    reference_reads = []
    def reference_source(location, **kwargs):
        reference_reads.append(location)
        return object()

    def reference_sync(*args, **kwargs):
        # No model preparation or client_factory is needed by this verified
        # unchanged-release fixture. The production run_once still chooses it.
        return SimpleNamespace(ok=True, to_dict=lambda: {"status": "unchanged", "ok": True})

    monkeypatch.setattr("vaws_knowledge.distribution.release.source_from_location", reference_source)
    monkeypatch.setattr(publishing, "check_and_sync", reference_sync)
    observed = []
    run_once = publishing.run_once

    def inspect_run_once(config, **kwargs):
        observed.append(config)
        assert config.config_path is None
        assert publishing.current_publishing(config)["enabled"] is False
        assert config.mounts == original.mounts
        assert config.state_root == original.state_root
        assert config.shared_sync == original.shared_sync
        return run_once(config, **kwargs)

    monkeypatch.setattr(publishing, "run_once", inspect_run_once)
    exec(onboarding.REFERENCE_PREPARE_CODE, {})
    result = json.loads(capsys.readouterr().out)
    assert result["ready"] is True
    assert result["local_ready"] is True
    assert result["catalog"]["status"] == "ready"
    assert len(observed) == 1
    repository = "fixture/reference-corpus" if explicit_reference_repository else "fixture/contribution-corpus"
    assert reference_reads == ([f"github://{repository}"] if shared_enabled else [])
    assert path.read_bytes() == before_config
    assert policy.read_bytes() == before_policy
    assert {item.name: item.read_bytes() for item in queue.glob("*.json")} == before_queue
    # The user's saved enabled setting survives the private, read-only copy.
    assert publishing.current_publishing(original)["enabled"] is True
