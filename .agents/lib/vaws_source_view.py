"""An optional standard editor view of the source roots already selected."""
from __future__ import annotations

import os
from pathlib import Path

from vaws_session_state import write_json


def write_source_view(workspace: Path, sources: dict) -> Path:
    workspace = Path(workspace).resolve()
    target = workspace / ".vaws-local/vaws.code-workspace"
    roots = {"workspace": workspace, **{name: Path(path).resolve() for name, path in sources.items()}}
    folders = [{"name": name, "path": Path(os.path.relpath(path, target.parent)).as_posix()}
               for name, path in roots.items()]
    write_json(target, {"folders": folders, "settings": {"git.autoRepositoryDetection": True}})
    return target
