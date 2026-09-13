"""Select an editing repository and display the roots already prepared.

Selection never discovers repositories, runs Git, or prepares missing sources.
The caller owns task identity and decides whether a new default is appropriate.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from vaws_session_state import write_json


def _source_roots(workspace: Path, sources: dict) -> dict[str, Path]:
    workspace = Path(workspace).resolve()
    roots = {"workspace": workspace}
    for name, value in sources.items():
        if (not isinstance(name, str) or not name or name in {".", ".."}
                or any(character in name for character in "/\\${}")):
            raise ValueError("source names must be single repository names")
        path = Path(value).resolve()
        if path != workspace and workspace not in path.parents:
            raise ValueError("source view must stay inside its editing workspace")
        if name == "workspace" and path != workspace:
            raise ValueError("workspace source must match the editing workspace")
        roots[name] = path
    return roots


def source_focus(workspace: Path, sources: dict, *, preferred: str | None = None) -> dict[str, str]:
    """Choose the default for a new preparation, or an explicit selected source.

    Existing tasks must reuse their recorded focus. A missing old focus is not
    permission to apply this new default during resume.
    """
    roots = _source_roots(workspace, sources)
    if preferred is not None and not isinstance(preferred, str):
        raise ValueError("editing repository must be a selected repository name")
    repository = preferred if preferred is not None else (
        "vllm-ascend" if "vllm-ascend" in roots else "workspace")
    if repository not in roots:
        raise ValueError(f"editing repository was not selected: {repository}")
    return {"repository": repository, "cwd": str(roots[repository])}


def recorded_focus(workspace: Path, sources: dict, record: dict) -> dict[str, str]:
    """Validate saved focus without applying a new task's default on resume."""
    from vaws_local_owner import accessible_windows_path

    def absolute(value, label):
        if not isinstance(value, (str, Path)) or not str(value):
            raise ValueError(f"recorded {label} must be an absolute path")
        path = Path(accessible_windows_path(value)).expanduser()
        if not path.is_absolute():
            raise ValueError(f"recorded {label} must be an absolute path")
        return path.resolve()

    workspace = absolute(workspace, "workspace")
    fields = {"cwd", "repository"}.intersection(record)
    if not fields:
        return {"repository": "workspace", "cwd": str(workspace)}
    if fields != {"cwd", "repository"} or not isinstance(record["repository"], str):
        raise ValueError("recorded editing focus requires both repository and cwd")
    normalized = {name: absolute(value, "source") for name, value in sources.items()}
    focus = source_focus(workspace, normalized, preferred=record["repository"])
    if absolute(record["cwd"], "cwd") != Path(focus["cwd"]):
        raise ValueError("recorded editing cwd does not match its selected repository")
    return focus


def native_focus(workspace: Path, sources: dict, record: dict, *,
                 cwd: str | Path | None = None, preferred: str | None = None) -> dict[str, str]:
    """Resolve a new native attachment without changing saved workspace defaults."""
    from vaws_local_owner import accessible_windows_path

    workspace = Path(accessible_windows_path(workspace)).resolve()
    sources = {name: Path(accessible_windows_path(value)) for name, value in sources.items()}
    base = recorded_focus(workspace, sources, record)
    if preferred is None and cwd is not None:
        actual = Path(accessible_windows_path(cwd))
        if not actual.is_absolute():
            raise ValueError("native editing cwd must be absolute")
        actual = actual.resolve()
        for name, value in sources.items():
            root = value.resolve()
            if name != "workspace" and (actual == root or root in actual.parents):
                preferred = name
                break
    return source_focus(workspace, sources, preferred=preferred) if preferred is not None else base


def write_source_view(workspace: Path, sources: dict, *, preferred: str | None = None,
                      task_id: str | None = None) -> Path:
    workspace = Path(workspace).resolve()
    if preferred is None:
        # Explicit client maintenance must not replace an existing task choice.
        # New preparation passes its chosen repository and skips this read.
        from vaws_local_state import read_preparation
        existing = read_preparation(workspace)
        if existing is not None:
            workspace = Path(existing["workspace"])
            sources = existing["sources"]
            preferred = recorded_focus(workspace, sources, existing)["repository"]
    roots = _source_roots(workspace, sources)
    focus = source_focus(workspace, sources, preferred=preferred)
    names = [focus["repository"], *(name for name in roots if name != focus["repository"])]
    if task_id is not None and (not isinstance(task_id, str) or not task_id):
        raise ValueError("a task editor view requires an explicit task identity")
    target = workspace / ".vaws-local/vaws.code-workspace"
    if task_id is not None:
        # The existing native identity scopes a generated view, not a new task
        # registry. Concurrent tasks may choose different repos in the same W.
        name = hashlib.sha256(task_id.encode("utf-8")).hexdigest() + ".code-workspace"
        target = workspace / ".vaws-local/editor-workspaces" / name
    folders = [{"name": name, "path": Path(os.path.relpath(roots[name], target.parent)).as_posix()}
               for name in names]
    write_json(target, {"folders": folders, "settings": {
        "git.autoRepositoryDetection": True,
        "terminal.integrated.cwd": "${workspaceFolder:" + focus["repository"] + "}",
    }})
    return target
