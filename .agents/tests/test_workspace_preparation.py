"""Explicit multi-repository preparation routes clones without Git discovery."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

import vaws_local_state as state
from vaws_workspace_entry import prepared_sources, read_preparation, write_preparation


def repository(path):
    (path / ".git").mkdir(parents=True)
    return path.resolve()


@pytest.fixture
def prepared(tmp_path):
    project, native, workspace = [repository(tmp_path / name) for name in ("project", "native", "bundle")]
    children = {name: repository(workspace / name) for name in ("vllm", "vllm-ascend")}
    write_preparation(project, project_root=project, native_workspace=project,
                      workspace=project, sources={})
    arguments = dict(project_root=project, native_workspace=native, workspace=workspace,
                     sources=children, source_channel="release")
    write_preparation(workspace, **arguments)
    write_preparation(native, **arguments)
    return project, native, workspace, {"workspace": str(workspace), **{key: str(value) for key, value in children.items()}}


def test_explicit_clone_and_native_reference_reuse_owner_and_all_sources_without_git(prepared):
    project, native, workspace, sources = prepared
    with patch.object(state.subprocess, "run", side_effect=AssertionError("Git discovery")):
        for root in (native, workspace):
            assert state.shared_workspace_root(root) == project
            assert state.agent_sessions_root(root) == project / ".vaws-local/agent-sessions"
            assert prepared_sources(root) == sources
        child = workspace / "vllm" / "engine"
        child.mkdir()
        assert state.prepared_workspace(child, project) == workspace
        assert state.prepared_workspace(native, project) == workspace


def test_unselected_nested_repository_and_foreign_owner_are_not_associated(prepared, tmp_path):
    project, _, workspace, _ = prepared
    unrelated = repository(workspace / "unrelated")
    assert state.prepared_workspace(unrelated, project) is None
    foreign = repository(tmp_path / "foreign")
    write_preparation(foreign, project_root=foreign, native_workspace=foreign, workspace=foreign, sources={})
    assert state.prepared_workspace(workspace, foreign) is None


def test_no_receipt_does_not_prepare_or_read_source_lock(tmp_path):
    (tmp_path / "sources.lock").write_text("invalid candidate lock")
    with patch.object(state.subprocess, "run", side_effect=AssertionError("Git discovery")):
        assert prepared_sources(tmp_path) is None
    assert not (tmp_path / ".vaws-local").exists()


@pytest.mark.parametrize("change", [
    {"state": "preparing"}, {"workspace": "relative"}, {"project_root": ""},
    {"sources": {}}, {"sources": {"workspace": "/outside"}},
])
def test_incomplete_or_misdirected_receipt_is_not_ready(prepared, change):
    _, _, workspace, _ = prepared
    path = workspace / ".vaws-local/native-workspace.json"
    record = json.loads(path.read_text())
    path.write_text(json.dumps({**record, **change}))
    with pytest.raises(ValueError):
        read_preparation(workspace)


def test_failed_source_validation_publishes_no_ready(tmp_path):
    workspace = repository(tmp_path / "workspace")
    empty = workspace / "vllm"
    empty.mkdir()
    with pytest.raises(ValueError, match="populated repository"):
        write_preparation(workspace, project_root=workspace, native_workspace=workspace,
                          workspace=workspace, sources={"vllm": empty})
    assert read_preparation(workspace) is None


def test_new_preparation_publishes_ascend_focus_and_explicit_override(prepared):
    project, native, workspace, sources = prepared
    record = read_preparation(workspace)
    assert record["repository"] == "vllm-ascend"
    assert record["cwd"] == sources["vllm-ascend"]
    changed = write_preparation(workspace, project_root=project, native_workspace=native,
                                workspace=workspace, sources=sources, preferred="vllm")
    assert changed["repository"] == "vllm" and changed["cwd"] == sources["vllm"]
    assert changed["sources"] == sources


def test_invalid_focus_does_not_replace_existing_preparation(prepared):
    project, native, workspace, sources = prepared
    receipt = workspace / ".vaws-local/native-workspace.json"
    view = workspace / ".vaws-local/vaws.code-workspace"
    before = (receipt.read_bytes(), view.read_bytes())
    with pytest.raises(ValueError, match="was not selected"):
        write_preparation(workspace, project_root=project, native_workspace=native,
                          workspace=workspace, sources=sources, preferred="unselected")
    assert (receipt.read_bytes(), view.read_bytes()) == before


def test_conflicting_focus_is_not_published(prepared):
    project, native, workspace, sources = prepared
    path = workspace / ".vaws-local/native-workspace.json"
    before = path.read_bytes()
    with pytest.raises(ValueError, match="conflicts"):
        write_preparation(workspace, project_root=project, native_workspace=native,
                          workspace=workspace, sources=sources, preferred="workspace",
                          cwd=sources["vllm-ascend"])
    assert path.read_bytes() == before


def test_runtime_routes_prepared_independent_clone_and_child_with_fixed_receipt(prepared):
    import vaws_mcp_runtime as runtime
    project, native, workspace, _ = prepared
    context = {"session": {"id": "vaws-" + "a" * 32}, "context_file": "native-context",
               "attachment": {"cwd": str(workspace / "vllm")}}
    receipt = {"key": "fixed", "receipt": "fixed-receipt", "python": sys.executable}
    with patch.object(state.subprocess, "run", side_effect=AssertionError("Git discovery")), \
         patch.object(runtime, "saved_ready", return_value=receipt) as ready:
        selected = runtime.selection(project, context)
        assert selected.workspace == workspace and selected.key == "fixed"
        ready.assert_called_once_with(workspace)
        context["attachment"]["cwd"] = str(native)
        assert runtime.selection(project, context).workspace == workspace


def test_codex_hook_routes_declared_clone_and_child_without_git(prepared):
    import importlib.util
    path = Path(__file__).resolve().parents[1] / "scripts/vaws_codex_session.py"
    spec = importlib.util.spec_from_file_location("prepared_codex_hook", path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    project, native, workspace, _ = prepared
    with patch.object(state.subprocess, "run", side_effect=AssertionError("Git discovery")):
        for cwd in (native, workspace, workspace / "vllm"):
            assert adapter.scoped_workspace({"cwd": str(cwd)}, project) == workspace
