"""Project instructions for one native session's selected editing directory.

The native clients read these files themselves. Planning does not start a
session, invoke a Skill, or infer identity from the current directory.
"""
from __future__ import annotations

from pathlib import Path


BEGIN = "<!-- BEGIN VAWS session-start -->"
END = "<!-- END VAWS session-start -->"


def guidance(client: str | None = None) -> str:
    name = client or "CLIENT"
    selection = (" CLIENT is codex, cursor, claude, grok or kimi."
                 if client is None else "")
    kimi = (
        " Official Kimi task tools require `context_file`; companion tools accept it "
        "when reusing the task's selected environment."
        if client in (None, "kimi") else ""
    )
    return (
        "Reuse a prepared workspace W and environment supplied by the native hook. "
        "Ordinary local review uses native tools; explicit remote endpoint or existing-container "
        "work uses remote-dev directly. These tasks need no startup, identity or knowledge preparation.\n\n"
        "When independent local editing or managed preparation is needed and no W is prepared, run "
        f"`uv run --no-project python .agents/scripts/vaws_start.py --client {name}` once."
        + selection + " Follow its result without a separate initialization probe. "
        "Pass `--context-file PATH` when the hook supplies context outside the client environment.\n\n"
        "Use the returned `workspace` as W for shell calls and absolute paths under W for file, "
        "search and patch tools, even if the client UI shows the original project. Sources and "
        "environment are bound. Pass the existing `context_file` to tools that need task context."
        + kimi + " Resume reuses the earlier W, task and environment without preparation or updates.\n"
    )


def managed_block(original: str, body: str) -> str:
    block = BEGIN + "\n" + body.rstrip() + "\n" + END
    if BEGIN in original or END in original:
        if original.count(BEGIN) != 1 or original.count(END) != 1:
            raise ValueError("VAWS session-start instruction markers are incomplete or duplicated")
        start, end = original.index(BEGIN), original.index(END)
        if end < start:
            raise ValueError("VAWS session-start instruction markers are reversed")
        return original[:start] + block + original[end + len(END):]
    return block + "\n\n" + original


def add_start_guidance(files: dict[Path, str], notes: list, client: str, project: Path) -> None:
    """Plan only generated blocks; keep all other project instructions intact."""
    path = project / "AGENTS.md"
    original = files.get(path)
    if original is None:
        original = path.read_text(encoding="utf-8") if path.exists() else ""
    files[path] = managed_block(original, guidance())
    if client == "claude":
        projection = project / "CLAUDE.md"
        original = files.get(projection)
        if original is None:
            original = projection.read_text(encoding="utf-8") if projection.exists() else ""
        if BEGIN in original or END in original or "@AGENTS.md" not in original.splitlines():
            files[projection] = managed_block(original, "@AGENTS.md")
    elif client == "cursor":
        projection = project / ".cursor/rules/vaws-session-start.mdc"
        original = files.get(projection)
        if original is None:
            original = projection.read_text(encoding="utf-8") if projection.exists() else ""
        if original and BEGIN not in original and END not in original:
            notes.append({"path": str(projection), "action": "preserved", "reason": "custom-session-start-rule"})
        elif original:
            files[projection] = managed_block(original, guidance("cursor"))
        else:
            body = managed_block("", guidance("cursor"))
            files[projection] = "---\ndescription: Select this native session's editing workspace\nalwaysApply: true\n---\n\n" + body
    notes.append({"client": client, "path": str(path), "action": "configured",
                  "reason": "new-session-project-guidance", "skill_required": False,
                  "resume": "reuse-existing-workspace"})
