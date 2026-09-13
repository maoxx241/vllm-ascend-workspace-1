"""The editor opens exactly the prepared repositories with portable paths."""
import json
from pathlib import Path

from vaws_source_view import write_source_view


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
