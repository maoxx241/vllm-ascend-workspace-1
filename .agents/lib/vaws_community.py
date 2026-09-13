"""One explicit workspace choice; local diagnostics and reference reads stay available."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import uuid
from datetime import datetime, timezone

SCHEMA = "vaws.community.v1"
POLICY_URL = "https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/main/docs/community-collaboration.md"


def local_policy_path(root: Path) -> Path:
    """Bootstrap reads only explicit preparation; it never spawns Git."""
    root = Path(root).resolve()
    marker = root / ".vaws-local/native-workspace.json"
    if marker.is_file():
        from vaws_local_state import read_preparation
        record = read_preparation(root)
        if record is not None:
            root = Path(record["project_root"])
    return root / ".vaws-local/community.json"


def policy_path(root: Path) -> Path:
    from vaws_local_state import shared_workspace_root
    return shared_workspace_root(Path(root)) / ".vaws-local/community.json"


def read_choice(root: Path) -> dict | None:
    return read_policy_file(policy_path(root))


def read_policy_file(path: Path) -> dict | None:
    """Bounded stdlib reader also usable before the diagnostics package exists."""
    if not path.exists():
        return None
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Community choice must not traverse symlinks")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Community choice must be a regular file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0)
                 | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        after = os.fstat(stream.fileno())
        if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError("Community choice changed while opening")
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise ValueError("Community choice exceeds its size limit")
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get("schema") != SCHEMA
            or value.get("decision") not in {"enabled", "disabled"}
            or any(not isinstance(value.get(key), str) or not re.fullmatch(r"[0-9a-f]{32}", value[key])
                   for key in ("workspace_id", "revision"))):
        raise ValueError("Saved community choice is invalid; automatic contributions remain disabled")
    return value


def write_choice(root: Path, decision: str) -> dict:
    """Revoke before any optional network work; unchanged decisions are byte-stable."""
    from vaws_session_state import write_json
    from vaws_workspace_update import path_lock
    if decision not in {"enabled", "disabled"}:
        raise ValueError("community must be enabled or disabled")
    path = policy_path(root)
    # This lock never covers installation, authentication or a network request.
    # Concurrent first choices must also agree on one stable workspace ID.
    with path_lock(path.with_suffix(".lock"), wait_seconds=5):
        previous = read_policy_file(path)
        if previous is not None and previous["decision"] == decision:
            return previous
        value = {"schema": SCHEMA, "workspace_id": previous["workspace_id"] if previous else uuid.uuid4().hex,
                 "decision": decision, "revision": uuid.uuid4().hex,
                 "decided_at": datetime.now(timezone.utc).isoformat(), "policy_url": POLICY_URL}
        write_json(path, value)
        return value


def community_environment(root: Path, base: dict | None = None) -> dict:
    result = dict(os.environ if base is None else base)
    # A selected workspace replaces any inherited unrelated project's policy.
    result["VAWS_COMMUNITY_POLICY"] = str(policy_path(root))
    return result


def disable_knowledge(root: Path) -> dict:
    """Disable the selected workspace's publishing before optional setup work."""
    from vaws_session_state import write_json
    from vaws_workspace_update import path_lock
    policy = policy_path(root)
    # A delayed off operation cannot overwrite a newer enabled configuration.
    # Hold only the local policy/config read and write, never owner setup.
    with path_lock(policy.with_suffix(".lock"), wait_seconds=5):
        choice = read_policy_file(policy)
        if choice is not None and choice["decision"] == "enabled":
            return {"state": "unchanged", "reason": "community_enabled"}
        path = policy.parent / "knowledge/service.json"
        if not path.exists():
            return {"state": "disabled", "configured": False}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("publishing", {}), dict):
            raise ValueError("Knowledge configuration is invalid; repair its contribution configuration")
        publishing = payload.setdefault("publishing", {})
        publishing.update(enabled=False, consent_file=str(policy))
        write_json(path, payload)
        return {"state": "disabled", "configured": True}
