#!/usr/bin/env python3
"""Route a Codex native event to its actual workspace's selected environment.

The user hook definition stays fixed across worktrees and dependency updates.
This entry only selects an existing environment; native hooks retain task
identity, and native worktree setup retains creation and update ownership.
"""
from __future__ import annotations

# Observe the real CLI before optional runtime imports; copied remote helpers stay standalone.
if __name__ == "__main__":
    import sys as _vaws_sys
    from pathlib import Path as _VawsPath
    _vaws_parents = _VawsPath(__file__).absolute().parents
    _vaws_lib = _vaws_parents[1] / "lib" if len(_vaws_parents) > 1 else None
    _vaws_entry = None
    if _vaws_lib is not None and (_vaws_lib / "vaws_diagnostics_adapter.py").is_file():
        _vaws_sys.path.insert(0, str(_vaws_lib))
        from vaws_diagnostics_adapter import bootstrap as _vaws_bootstrap
        _vaws_entry = _vaws_bootstrap(__file__)

import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
sys.path.insert(0, str(ROOT / ".agents/scripts"))

def scoped_workspace(payload: dict, source: Path) -> Path | None:
    """Use only native cwd, including a subdirectory of a linked worktree."""
    from vaws_local_owner import accessible_windows_path
    from vaws_local_state import prepared_workspace
    from vaws_workspace_update import common_dir, repository_root

    value = payload.get("cwd")
    if not isinstance(value, str) or not value:
        return None
    cwd = Path(accessible_windows_path(value)).expanduser()
    if not cwd.is_absolute():
        return None
    try:
        prepared = prepared_workspace(cwd, source)
        if prepared is not None:
            return prepared
        target = repository_root(cwd)
        return target if common_dir(target).resolve() == common_dir(source).resolve() else None
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None


def forward(target: Path, payload: dict) -> int:
    from vaws_environment import PIN_ENV, saved_ready
    from vaws_native_task_env import task_env
    from vaws_worktree_setup import unpinned_environment

    receipt = saved_ready(target)
    environment = unpinned_environment()
    environment.update(task_env("codex", target))
    environment[PIN_ENV] = receipt["receipt"]
    event = payload.get("hook_event_name") or payload.get("hookEventName")
    kind = "summary" if event == "Stop" else "session"
    name = "knowledge_summary.py" if kind == "summary" else "vaws_session.py"
    hook = target / ".agents/hooks" / name
    if not hook.is_file():
        raise RuntimeError(f"selected workspace hook is missing: {hook}")
    command = [receipt["python"], str(hook), "--client", "codex", "--project", str(target),
               "--environment-receipt", receipt["receipt"]]
    print(json.dumps({"vaws_codex_hook": kind, "workspace": str(target),
                      "python": command[0], "receipt": receipt["receipt"]}), file=sys.stderr, flush=True)
    return subprocess.run(command, input=json.dumps(payload), text=True,
                          cwd=target, env=environment, check=False).returncode


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("Codex hook input must be an object")
        event = str(payload.get("hook_event_name") or payload.get("hookEventName") or "")
        if re.sub(r"[^a-z]", "", event.lower()) == "pretooluse":
            name = str(payload.get("tool_name") or payload.get("toolName") or "")
            arguments = payload.get("tool_input", payload.get("toolInput", {}))
            # The stable gateway also routes companion calls to a prepared
            # task's package selection. Ordinary local tools need no runtime.
            relevant = (re.search(r"(?:^|:|__)vaws_(session|run|execution|finish|message)$", name)
                        or re.search(r"^(?:MCP:)?(?:mcp__)?(?:vaws[-_]knowledge__knowledge_(?:query|explain|capture)|remote[-_]dev__remote_[a-z_]+)$", name))
            if (not relevant
                    or not isinstance(arguments, dict) or arguments.get("context_file")):
                return 0
        target = scoped_workspace(payload, ROOT)
        if target is None:
            return 0
        return forward(target, payload)
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "phase": "codex_session_hook", "error": str(exc)}),
              file=sys.stderr, flush=True)
        return 0  # Association/knowledge failures do not block ordinary local work.


if __name__ == "__main__":
    raise SystemExit((_vaws_entry.run(main) if _vaws_entry else main()))
