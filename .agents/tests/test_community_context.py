"""Selected-workspace consent remains isolated when initialization is broken."""
import json
import os

import pytest

import vaws_community
import vaws_diagnostics_adapter as diagnostics


@pytest.mark.parametrize("missing_core", [False, True])
@pytest.mark.parametrize("broken_source", [False, True])
def test_selected_workspace_never_inherits_foreign_consent(tmp_path, monkeypatch, missing_core, broken_source):
    import vaws_diagnostics
    root = tmp_path / "logs"
    owner, selected = tmp_path / "owner", tmp_path / "selected"
    vaws_community.write_choice(owner, "enabled")
    vaws_community.write_choice(selected, "disabled")
    monkeypatch.setenv("VAWS_DIAGNOSTICS_ROOT", str(root))
    monkeypatch.setenv("VAWS_COMMUNITY_POLICY", str(owner / ".vaws-local/community.json"))
    if broken_source:
        def broken(root):
            raise ValueError("broken receipt")
        monkeypatch.setattr(vaws_community, "local_policy_path", broken)
    if missing_core:
        monkeypatch.setattr(diagnostics, "_api", lambda: None)
    with pytest.raises(ValueError, match="fixture"):
        with diagnostics.community_context(selected), diagnostics.operation("fixture"):
            raise ValueError("fixture")
    rows = [json.loads(line) for path in root.glob("events/**/*.jsonl")
            for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows and all(not row.get("community") for row in rows)
    assert vaws_diagnostics.current_consent()["policy_file"] == str(owner / ".vaws-local/community.json")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX named pipe")
def test_policy_named_pipe_is_rejected_without_opening(tmp_path):
    path = tmp_path / "policy"
    os.mkfifo(path)
    with pytest.raises(ValueError, match="regular file"):
        vaws_community.read_policy_file(path)
