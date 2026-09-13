"""Fork editing focus follows an explicit source task without changing its view."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_native_workspace import repository
from test_native_worktree_setup import fixture as native_fixture, setup
from test_vaws_start import start
from vaws_coordinator.agent_session import AgentSessions
import vaws_mcp_runtime as runtime


def assert_view(record, repository_name):
    assert record["repository"] == repository_name
    assert record["cwd"] == record["sources"][repository_name]
    path = Path(record["editor_workspace"])
    view = json.loads(path.read_text(encoding="utf-8"))
    assert view["folders"][0]["name"] == repository_name
    assert (path.parent / view["folders"][0]["path"]).resolve() == Path(record["cwd"])
    assert view["settings"]["terminal.integrated.cwd"] == "${workspaceFolder:" + repository_name + "}"


def saved_files(*paths):
    return {Path(path): Path(path).read_bytes() for path in paths}


def forbid_copy(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid source task reached workspace copy or configuration")
    for name in ("create_workspace", "create_prepared_workspace", "prepare_canonical", "configure_target"):
        monkeypatch.setattr(setup, name, unexpected)


@pytest.fixture
def parent_task(native_fixture, tmp_path, monkeypatch):
    f = native_fixture
    for name in ("VAWS_CONTEXT_FILE", "VAWS_PARENT_CONTEXT", "VAWS_ATTACH_CONTEXT"):
        monkeypatch.delenv(name, raising=False)
    roots = {"workspace": str(f.source)}
    for name in ("vllm", "vllm-ascend"):
        roots[name] = str(repository(f.source / name))
    setup.select_environment(f.source, f.receipt_old)
    preparation = setup.write_preparation(
        f.source, project_root=f.source, native_workspace=f.source,
        workspace=f.source, sources=roots,
    )
    assert_view(preparation, "vllm-ascend")
    original_preparation = saved_files(
        f.source / ".vaws-local/native-workspace.json", preparation["editor_workspace"],
    )

    def read_receipt(path):
        receipts = {receipt["receipt"]: receipt for receipt in (f.receipt_old, f.receipt_new)}
        return receipts[str(path)]

    monkeypatch.setattr(start, "saved_ready", setup.saved_ready)
    monkeypatch.setattr(start, "read_receipt", read_receipt)
    monkeypatch.setattr(runtime, "read_receipt", read_receipt)
    monkeypatch.setattr(start, "resolve_context_file", lambda explicit: explicit)
    monkeypatch.setattr(start, "prepare_latest", lambda *a, **k: pytest.fail("prepared task refreshed sources"))
    monkeypatch.setattr(start, "configure_target", lambda *a, **k: pytest.fail("prepared task configured a client"))
    monkeypatch.setattr(setup, "copy_workspace_identity", lambda *a, **k: None)

    store = AgentSessions(tmp_path / "task registry")
    context = store.attach("kimi", "explicit-parent-task", str(f.source))
    result = start.start("kimi", f.source, context["context_file"], preferred="vllm")
    assert result["status"] == "ready", result
    assert result["workspace"] == str(f.source)
    assert_view(result, "vllm")
    assert result["editor_workspace"] != preparation["editor_workspace"]
    assert saved_files(*original_preparation) == original_preparation
    protected = saved_files(*original_preparation, result["editor_workspace"], result["evidence"])
    return SimpleNamespace(f=f, store=store, context=context, preparation=preparation,
                           result=result, protected=protected)


def test_explicit_parent_start_focus_is_copied_and_source_views_are_unchanged(parent_task):
    p = parent_task
    assert setup.source_task_focus(p.f.source, p.context["context_file"]) == {
        "repository": "vllm", "cwd": str(p.f.source / "vllm"),
    }
    target = p.f.source.parent / "fork 用户"
    result = setup.prepare_worktree("kimi", p.f.source, target, preserve_source=True,
                                    source_context_file=p.context["context_file"])
    assert result["status"] == "ready" and result["workspace"] == str(target)
    assert_view(result, "vllm")
    assert setup.read_preparation(target)["cwd"] == str(target / "vllm")
    assert all((Path(path) / ".git").is_dir() for path in result["sources"].values())
    assert p.f.calls["prepare"] == []
    assert saved_files(*p.protected) == p.protected
    resumed_parent = start.start("kimi", p.f.source, p.context["context_file"])
    assert resumed_parent["status"] == "reused"
    assert_view(resumed_parent, "vllm")
    assert saved_files(*p.protected) == p.protected


def test_fork_without_source_context_uses_preparation_not_ambient_task(parent_task, monkeypatch):
    p = parent_task
    monkeypatch.setenv("VAWS_CONTEXT_FILE", p.context["context_file"])
    monkeypatch.setattr(setup, "source_task_focus", lambda *a, **k: pytest.fail("fork inferred a parent task"))
    result = setup.prepare_worktree("kimi", p.f.source, p.f.source.parent / "ordinary fork",
                                    preserve_source=True)
    assert_view(result, "vllm-ascend")
    assert saved_files(*p.protected) == p.protected


def test_explicit_fork_repository_overrides_valid_parent_task(parent_task):
    p = parent_task
    result = setup.prepare_worktree("kimi", p.f.source, p.f.source.parent / "workspace fork",
                                    preserve_source=True, preferred="workspace",
                                    source_context_file=p.context["context_file"])
    assert_view(result, "workspace")
    assert saved_files(*p.protected) == p.protected


@pytest.mark.parametrize("preferred", [None, "workspace"])
def test_context_for_another_workspace_fails_before_copy(parent_task, monkeypatch, preferred):
    p = parent_task
    setup.select_environment(p.f.stage, p.f.receipt_new)
    setup.write_preparation(p.f.stage, project_root=p.f.source, native_workspace=p.f.stage,
                            workspace=p.f.stage, sources={"workspace": str(p.f.stage)})
    wrong = p.store.attach("kimi", "another-parent-task", str(p.f.stage))
    selected = start.start("kimi", p.f.source, wrong["context_file"])
    assert selected["status"] == "ready", selected
    assert selected["workspace"] == str(p.f.stage)
    target = p.f.source.parent / "rejected fork"
    forbid_copy(monkeypatch)
    with pytest.raises(ValueError, match="another editing workspace"):
        setup.prepare_worktree("kimi", p.f.source, target, preserve_source=True,
                               preferred=preferred, source_context_file=wrong["context_file"])
    assert not target.exists()
    assert saved_files(*p.protected) == p.protected


@pytest.mark.parametrize("empty", ["", " ", "\n\t"])
def test_empty_explicit_context_never_falls_back_to_environment(parent_task, monkeypatch, empty):
    p = parent_task
    monkeypatch.setenv("VAWS_CONTEXT_FILE", p.context["context_file"])
    monkeypatch.setattr("vaws_coordinator.agent_session.load_context",
                        lambda *a, **k: pytest.fail("empty explicit context reached ambient context lookup"))
    target = p.f.source.parent / "empty context fork"
    forbid_copy(monkeypatch)
    with pytest.raises(ValueError, match="context must be supplied explicitly"):
        setup.prepare_worktree("kimi", p.f.source, target, preserve_source=True,
                               source_context_file=empty)
    assert not target.exists()
    assert saved_files(*p.protected) == p.protected


def test_existing_target_resumes_its_own_focus_without_consulting_parent(parent_task, monkeypatch):
    p = parent_task
    target = p.f.source.parent / "existing fork"
    first = setup.prepare_worktree("kimi", p.f.source, target, preserve_source=True,
                                   source_context_file=p.context["context_file"])
    assert_view(first, "vllm")
    protected = saved_files(*p.protected, target / ".vaws-local/native-workspace.json",
                            first["editor_workspace"])
    forbid_copy(monkeypatch)
    monkeypatch.setattr(setup, "source_task_focus", lambda *a, **k: pytest.fail("resume read a parent task"))
    monkeypatch.setattr(setup, "select_environment", lambda *a, **k: pytest.fail("resume changed environment"))
    result = setup.prepare_worktree("kimi", p.f.source, target, preserve_source=True,
                                    preferred="workspace", source_context_file="")
    assert result["status"] == "reused"
    for key in ("workspace", "repository", "cwd", "editor_workspace", "sources", "environment"):
        assert result[key] == first[key]
    assert_view(result, "vllm")
    assert saved_files(*protected) == protected
