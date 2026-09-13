#!/usr/bin/env python3
"""Prepare an independent workspace for Claude's WorktreeCreate hook.

Input is the native hook JSON on stdin. Stdout contains only the resulting
directory. Preparation facts and failures go to stderr and the new directory's
local receipt. The callback does not run on SessionStart or resume.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
from vaws_workspace_update import repository_root, write_json, Deferred
from vaws_local_state import prepared_workspace, read_preparation, shared_workspace_root


def prepare(source: Path, target: Path, *, preserve_source: bool = False) -> dict:
    spec = importlib.util.spec_from_file_location("vaws_claude_native_setup", ROOT / ".agents/scripts/vaws_worktree_setup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prepare_worktree("claude", source, target, preserve_source=preserve_source)


def create_worktree(payload: dict) -> tuple[Path, dict]:
    if payload.get("hook_event_name") != "WorktreeCreate":
        raise ValueError("this callback only handles Claude WorktreeCreate")
    name = payload.get("name", "")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", name) or ".." in name:
        raise ValueError("Claude worktree name must be a single Git-compatible slug")
    source = Path(payload["cwd"]).resolve()
    source = repository_root(source)
    owner = shared_workspace_root(source)
    for ancestor in (source, *source.parents):
        record = read_preparation(ancestor)
        if record is not None:
            owner = Path(record["project_root"])
            selected = prepared_workspace(source, owner)
            if selected is None:
                raise ValueError("Claude cwd is outside the prepared workspace's selected sources")
            source = selected
            break
    target = owner.parent / (owner.name + "-vaws-claude-" + name)
    if target.exists():
        record = read_preparation(target)
        if record is None:
            raise ValueError(f"Claude workspace preparation is incomplete: {target}")
        if Path(record["project_root"]) != owner:
            raise ValueError(f"Claude workspace belongs to another project: {target}")
    try:
        result = prepare(source, target, preserve_source=payload.get("source") == "fork")
    except (OSError, ValueError, RuntimeError) as exc:
        result = {"status": "failed", "phase": "claude_worktree_setup", "workspace": str(target),
                  "error": str(exc), **({"evidence": exc.evidence} if isinstance(exc, Deferred) else {})}
        if target.is_dir():
            write_json(target / ".vaws-local/claude-worktree-setup.json", result)
        # Leave the owned directory and raw facts available for repair; never
        # delete user files as compensation for failed dependency preparation.
        disposition = f"new workspace retained at {target}" if target.exists() else "workspace preparation failed before creation"
        raise RuntimeError(f"{disposition}: {exc}") from exc
    target = Path(result["workspace"])
    write_json(target / ".vaws-local/claude-worktree-setup.json", result)
    return target, result


def main() -> int:
    try:
        target, result = create_worktree(json.load(sys.stdin))
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(json.dumps({"status": "failed", "phase": "claude_worktree_setup", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
    print(target, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
