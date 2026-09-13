"""Project existing task preparation facts into native startup hints.

The coordinator still owns attachment and hook scope. This read-only adapter
uses the same selection as MCP dispatch; it never prepares or changes a task.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from vaws_mcp_runtime import selection


def hint_event(payload: object) -> bool:
    return isinstance(payload, dict) and (
        payload.get("hook_event_name") or payload.get("hookEventName")
    ) in {"SessionStart", "UserPromptSubmit"}


def existing_context(client: str, payload: dict) -> dict:
    from vaws_coordinator.agent_session import AgentSessions

    # These are native hook identities, never a directory or an inherited
    # shell context. Cursor's documented SessionStart also supplies session_id.
    field = "sessionId" if client == "grok" else "session_id"
    native = payload.get("conversation_id") if client == "cursor" else None
    native = native or payload.get(field)
    if not isinstance(native, str) or not native:
        raise ValueError("hook has no native session identity; no task was guessed")
    event = payload.get("hook_event_name") or payload.get("hookEventName")
    agent = payload.get("agent_id") or "" if event != "SessionStart" else ""
    if client == "kimi" and agent == "main":
        agent = ""
    if not isinstance(agent, str):
        raise ValueError("hook agent identity is not a string")
    state = os.environ.get("VAWS_AGENT_SESSIONS_DIR")
    return AgentSessions(Path(state) if state else None).native_context(client, native, agent)


def preparation_hint(root: Path, context: dict) -> str:
    try:
        selected = selection(root, context)
    except ValueError as exc:
        # This is selection's sole explicit unprepared result. All errors in
        # an existing task record or native selection remain failures below.
        if str(exc) != ("This new task has no prepared workspace. Run the project "
                        "vaws_start.py entry once, then reuse its context."):
            raise
        # A native attachment does not select workspace preparation. Review and
        # explicit endpoint work need neither preparation nor personal identity.
        return ""
    cwd = Path(getattr(selected, "cwd", None) or selected.workspace).resolve()
    workspace = Path(selected.workspace).resolve()
    if cwd != workspace and workspace not in cwd.parents:
        raise ValueError("selected editing cwd is outside its prepared workspace")
    repository = getattr(selected, "repository", None)
    editing = f"Default shell and file directory: {cwd}"
    if repository:
        editing += f" (Git repository: {repository})"
    return (f"VAWS task workspace is prepared: W={selected.workspace}\n"
            f"{editing}\n"
            f"Selected environment: {selected.key}\nSelected Python: {selected.python}\n"
            "Use this default directory for shell commands and absolute file paths there. "
            "VAWS scripts and skills remain under W; use their absolute paths. "
            "An explicitly requested repository or endpoint takes precedence. "
            "Reuse this task's workspace and environment without repeating preparation.")


def project_output(client: str, payload: dict, raw: str, *, root: Path) -> str:
    """Preserve package noops/errors and each client's native output envelope."""
    if not hint_event(payload) or not raw.strip():
        return raw
    event = payload.get("hook_event_name") or payload.get("hookEventName")
    text_only = client == "kimi" and event == "UserPromptSubmit"
    if text_only:
        hint, output = raw.rstrip("\n"), None
    else:
        try:
            output = json.loads(raw)
        except ValueError:
            return raw
        if not isinstance(output, dict) or not output:
            return raw
        specific = output.get("hookSpecificOutput", {})
        hint = output.get("additional_context") if client == "cursor" else specific.get("additionalContext")
        # Some Cursor package events use the generic envelope. The client
        # contract still consumes additional_context at the root.
        if client == "cursor" and hint is None:
            hint = specific.get("additionalContext")
        if not isinstance(hint, str) or not hint:
            return raw
    try:
        facts = preparation_hint(root, existing_context(client, payload))
    except Exception as exc:
        facts = (f"VAWS workspace selection could not be read: {type(exc).__name__}: {exc}. "
                 "The existing task selection was left unchanged; inspect its context and "
                 "recorded environment before continuing. No new workspace was inferred.")
    hint = hint.replace("Client startup owns workspace and component preparation. ", "")
    if facts:
        hint = facts + "\n\n" + hint
    if text_only:
        return hint + "\n"
    if client == "cursor":
        output["additional_context"] = hint
        if "additionalContext" in specific:
            specific.pop("additionalContext")
            if set(specific) <= {"hookEventName"}:
                output.pop("hookSpecificOutput")
    else:
        specific["additionalContext"] = hint
    return json.dumps(output, ensure_ascii=False) + "\n"
