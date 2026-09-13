"""The editor opens exactly the prepared repositories with portable paths."""
import json
from pathlib import Path
import subprocess

import pytest

from vaws_source_view import native_focus, recorded_focus, source_focus, write_source_view


def test_view_lists_selected_roots_only_and_survives_a_directory_move(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "vllm").mkdir(parents=True)
    view = write_source_view(workspace, {"vllm": workspace / "vllm"})
    content = json.loads(view.read_text(encoding="utf-8"))
    assert [item["name"] for item in content["folders"]] == ["workspace", "vllm"]
    assert all(not Path(item["path"]).is_absolute() for item in content["folders"])
    moved = tmp_path / "moved"
    workspace.rename(moved)
    for item in content["folders"]:
        assert (moved / ".vaws-local" / item["path"]).resolve().is_dir()


def test_new_task_defaults_to_ascend_without_git_or_source_discovery(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    sources = {"workspace": workspace, "vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    def forbidden(*args, **kwargs):
        pytest.fail("focus must not discover or prepare sources")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(Path, "iterdir", forbidden)
    assert source_focus(workspace, sources) == {
        "repository": "vllm-ascend", "cwd": str((workspace / "vllm-ascend").resolve())}
    assert not workspace.exists()


def test_native_focus_is_read_only_and_respects_explicit_child_or_saved_root(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    sources = {"workspace": workspace, "vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    record = source_focus(workspace, sources, preferred="workspace")
    def forbidden(*args, **kwargs):
        pytest.fail("native focus must not scan repositories or write selection")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(Path, "iterdir", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    assert native_focus(workspace, sources, record, cwd=workspace) == record
    assert native_focus(workspace, sources, record, cwd=workspace / "vllm/subdir")["repository"] == "vllm"
    assert native_focus(workspace, sources, record, cwd=workspace / "vllm", preferred="workspace") == record
    assert native_focus(workspace, sources, {}, cwd=workspace)["repository"] == "workspace"
    with pytest.raises(ValueError, match="both"):
        native_focus(workspace, sources, {"repository": "vllm"}, preferred="workspace")
    with pytest.raises(ValueError, match="absolute"):
        native_focus(workspace, sources, record, cwd="vllm")
    assert not workspace.exists()


def test_task_editor_views_keep_shared_default_and_remain_portable(tmp_path):
    workspace = tmp_path / "workspace"
    sources = {"workspace": workspace, "vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    for root in sources.values():
        root.mkdir(parents=True, exist_ok=True)
    shared = write_source_view(workspace, sources, preferred="vllm-ascend")
    before = shared.read_bytes()
    first = write_source_view(workspace, sources, preferred="vllm", task_id="task/one")
    second = write_source_view(workspace, sources, preferred="workspace", task_id="task/two")
    assert shared.read_bytes() == before and first != second != shared
    assert first == write_source_view(workspace, sources, preferred="vllm", task_id="task/one")
    data = json.loads(first.read_text(encoding="utf-8"))
    moved = tmp_path / "moved"
    workspace.rename(moved)
    for folder in data["folders"]:
        assert (moved / first.relative_to(workspace).parent / folder["path"]).resolve().is_dir()
    assert data["folders"][0]["name"] == "vllm"
    assert data["settings"]["terminal.integrated.cwd"] == "${workspaceFolder:vllm}"


@pytest.mark.parametrize("preferred", ["workspace", "vllm", "vllm-ascend"])
def test_explicit_repository_selects_editor_order_and_terminal(tmp_path, preferred):
    workspace = tmp_path / "workspace"
    sources = {"vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    path = write_source_view(workspace, sources, preferred=preferred)
    content = json.loads(path.read_text(encoding="utf-8"))
    assert content["folders"][0]["name"] == preferred
    assert len(content["folders"]) == 3
    assert content["settings"]["terminal.integrated.cwd"] == "${workspaceFolder:" + preferred + "}"
    assert all(not Path(row["path"]).is_absolute() for row in content["folders"])


def test_default_view_shows_ascend_first_and_keeps_other_repositories(tmp_path):
    workspace = tmp_path / "workspace"
    sources = {"workspace": workspace, "vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    result = json.loads(write_source_view(workspace, sources).read_text(encoding="utf-8"))
    assert [row["name"] for row in result["folders"]] == ["vllm-ascend", "workspace", "vllm"]
    assert result["settings"]["git.autoRepositoryDetection"] is True


def test_root_only_never_adds_an_unselected_ascend_repository(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "vllm-ascend").mkdir(parents=True)
    assert source_focus(workspace, {}) == {"repository": "workspace", "cwd": str(workspace.resolve())}
    with pytest.raises(ValueError, match="was not selected"):
        write_source_view(workspace, {}, preferred="vllm-ascend")
    assert not (workspace / ".vaws-local").exists()


@pytest.mark.parametrize("sources", [
    {"workspace": "different"}, {"outside": "../outside"},
    {"../bad": "workspace"}, {"bad}": "workspace"},
])
def test_invalid_views_fail_before_writing(tmp_path, sources):
    workspace = tmp_path / "workspace"
    mapped = {name: tmp_path / value for name, value in sources.items()}
    with pytest.raises(ValueError):
        write_source_view(workspace, mapped)
    assert not workspace.exists()


@pytest.mark.parametrize("preferred", ["workspace", "vllm", "vllm-ascend", None])
def test_client_setup_view_refresh_keeps_existing_task_focus(tmp_path, preferred):
    workspace = tmp_path / "workspace"
    sources = {"workspace": str(workspace), "vllm": str(workspace / "vllm"),
               "vllm-ascend": str(workspace / "vllm-ascend")}
    receipt = workspace / ".vaws-local/native-workspace.json"
    receipt.parent.mkdir(parents=True)
    facts = {"state": "ready", "project_root": str(workspace), "native_workspace": str(workspace),
             "workspace": str(workspace), "sources": sources}
    if preferred is not None:
        facts.update(source_focus(workspace, sources, preferred=preferred))
    receipt.write_text(json.dumps(facts), encoding="utf-8")
    before = receipt.read_bytes()
    # This is the existing all-client setup call shape: no preferred argument.
    view = json.loads(write_source_view(workspace, sources).read_text(encoding="utf-8"))
    expected = preferred or "workspace"
    assert view["folders"][0]["name"] == expected
    assert view["settings"]["terminal.integrated.cwd"] == "${workspaceFolder:" + expected + "}"
    assert receipt.read_bytes() == before


def test_native_reference_refresh_writes_actual_bundle_view(tmp_path):
    native, workspace = tmp_path / "native", tmp_path / "bundle"
    sources = {"workspace": str(workspace), "vllm-ascend": str(workspace / "vllm-ascend")}
    receipt = native / ".vaws-local/native-workspace.json"
    receipt.parent.mkdir(parents=True)
    facts = {"state": "ready", "project_root": str(tmp_path), "native_workspace": str(native),
             "workspace": str(workspace), "sources": sources,
             **source_focus(workspace, sources)}
    receipt.write_text(json.dumps(facts), encoding="utf-8")
    view = write_source_view(native, sources)
    assert view == workspace / ".vaws-local/vaws.code-workspace"
    assert not (native / ".vaws-local/vaws.code-workspace").exists()
    assert json.loads(view.read_text(encoding="utf-8"))["folders"][0]["name"] == "vllm-ascend"


@pytest.mark.parametrize("repository", ["workspace", "vllm", "vllm-ascend"])
def test_recorded_focus_preserves_explicit_repository_without_git(tmp_path, monkeypatch, repository):
    workspace = tmp_path / "bundle"
    sources = {"vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    original = source_focus(workspace, sources, preferred=repository)
    def forbidden(*args, **kwargs):
        pytest.fail("recorded focus must not inspect or prepare sources")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    assert recorded_focus(workspace, sources, original) == original
    assert not workspace.exists()


def test_old_record_does_not_adopt_new_ascend_default(tmp_path):
    workspace = tmp_path / "bundle"
    assert recorded_focus(workspace, {"vllm-ascend": workspace / "vllm-ascend"}, {}) == {
        "repository": "workspace", "cwd": str(workspace.resolve())}


@pytest.mark.parametrize("record", [
    {"repository": "vllm-ascend"}, {"cwd": "bundle/vllm-ascend"},
    {"repository": "vllm-ascend", "cwd": "relative"},
    {"repository": None, "cwd": "relative"},
    {"repository": "unknown", "cwd": "relative"},
])
def test_partial_or_invalid_recorded_focus_is_rejected(tmp_path, record):
    workspace = tmp_path / "bundle"
    with pytest.raises(ValueError):
        recorded_focus(workspace, {"vllm-ascend": workspace / "vllm-ascend"}, record)


def test_cwd_inside_bundle_but_in_wrong_repository_is_rejected(tmp_path):
    workspace = tmp_path / "bundle"
    sources = {"vllm": workspace / "vllm", "vllm-ascend": workspace / "vllm-ascend"}
    for wrong in (workspace, workspace / "vllm", workspace / "vllm-ascend/subdir", tmp_path / "outside"):
        with pytest.raises(ValueError, match="does not match"):
            recorded_focus(workspace, sources, {"repository": "vllm-ascend", "cwd": str(wrong)})


def test_recorded_paths_use_existing_owner_path_conversion(tmp_path, monkeypatch):
    import vaws_local_owner
    workspace = tmp_path / "bundle"
    source = workspace / "vllm-ascend"
    translations = {"foreign-workspace": str(workspace), "foreign-source": str(source)}
    monkeypatch.setattr(vaws_local_owner, "accessible_windows_path", lambda value: translations.get(str(value), str(value)))
    assert recorded_focus("foreign-workspace", {"vllm-ascend": "foreign-source"},
                          {"repository": "vllm-ascend", "cwd": "foreign-source"}) == {
        "repository": "vllm-ascend", "cwd": str(source.resolve())}
