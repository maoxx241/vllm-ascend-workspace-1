#!/usr/bin/env python3
"""Local untracked state helpers for vllm-ascend-workspace.

Machine inventory and native attachments share the primary Git worktree.
Business result directories remain local to the current worktree.
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATE_DIRNAME = ".vaws-local"
INVENTORY_FILENAME = "machine-inventory.json"

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / STATE_DIRNAME


def read_preparation(root: Path) -> dict | None:
    """Read the existing preparation receipt; never discover or prepare sources."""
    from vaws_local_owner import accessible_windows_path

    root = root.expanduser().resolve()
    path = root / STATE_DIRNAME / "native-workspace.json"
    if not path.is_file():
        return None
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or result.get("state") != "ready":
        raise ValueError(f"workspace preparation is incomplete: {path}")
    result = dict(result)
    for key in ("project_root", "native_workspace", "workspace"):
        value = result.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"workspace preparation has no {key}: {path}")
        target = Path(accessible_windows_path(value)).expanduser()
        if not target.is_absolute():
            raise ValueError(f"workspace preparation {key} is not absolute: {path}")
        result[key] = str(target.resolve())
    if str(root) not in (result["workspace"], result["native_workspace"]):
        raise ValueError(f"workspace preparation belongs to another directory: {path}")
    sources = result.get("sources")
    if not isinstance(sources, dict):
        raise ValueError(f"workspace preparation has no source map: {path}")
    normalized = {}
    workspace = Path(result["workspace"])
    for name, value in sources.items():
        if not isinstance(name, str) or not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError(f"invalid prepared source name: {path}")
        if not isinstance(value, str) or not value:
            raise ValueError(f"invalid prepared source path: {path}")
        target = Path(accessible_windows_path(value)).expanduser()
        if not target.is_absolute():
            raise ValueError(f"prepared source path is not absolute: {path}")
        target = target.resolve()
        if target != workspace and workspace not in target.parents:
            raise ValueError(f"prepared source is outside its workspace: {path}")
        normalized[name] = str(target)
    result["sources"] = normalized
    if normalized.get("workspace") != result["workspace"]:
        raise ValueError(f"prepared workspace source does not match its directory: {path}")
    return result


def prepared_workspace(cwd: Path, project: Path, *, owner: Path | None = None) -> Path | None:
    """Match a native cwd to explicit preparation, including declared child repos.

    Inspect only ancestor markers, not directory contents or Git history. An
    unrelated nested repository is excluded unless its exact root was selected.
    This is workspace routing; native context remains the task identity.
    """
    cwd, project = cwd.expanduser().resolve(), project.expanduser().resolve()
    nearest_git = None
    for candidate in (cwd, *cwd.parents):
        if nearest_git is None and (candidate / ".git").exists():
            nearest_git = candidate
        record = read_preparation(candidate)
        if record is None:
            continue
        owner = owner or shared_workspace_root(project)
        if Path(record["project_root"]) != owner:
            return None
        allowed = {Path(record["workspace"]), Path(record["native_workspace"]),
                   *(Path(value) for value in record["sources"].values())}
        if nearest_git is not None and nearest_git not in allowed:
            return None
        return Path(record["workspace"])
    return None


def shared_workspace_root(repo_root: Path = ROOT) -> Path:
    """Use the explicit preparation owner, or a native single-repo Git owner."""
    repo_root = repo_root.expanduser().resolve()
    preparation = read_preparation(repo_root)
    if preparation is not None:
        return Path(preparation["project_root"])
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return repo_root
    if result.returncode != 0 or not result.stdout.strip():
        return repo_root
    common_dir = Path(result.stdout.strip()).expanduser()
    if not common_dir.is_absolute():
        common_dir = repo_root / common_dir
    common_dir = common_dir.resolve()
    if common_dir.name.lower() == ".git" and common_dir.is_dir():
        return common_dir.parent
    return repo_root


def shared_inventory_path(repo_root: Path = ROOT) -> Path:
    return shared_workspace_root(repo_root) / STATE_DIRNAME / INVENTORY_FILENAME


def agent_sessions_root(repo_root: Path = ROOT) -> Path:
    """Native attachments share task identity across linked scaffold worktrees.

    This is a local identity registry, never a second resource allocator.
    Independent clones join a task only through an explicit context receipt.
    """
    return shared_workspace_root(repo_root) / STATE_DIRNAME / "agent-sessions"


class WorkspaceStateError(RuntimeError):
    """Raised for deterministic user-facing local-state failures."""


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ensure_state_dir(path: Path = STATE_DIR) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


SAFE_RUN_TOKEN_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_run_token(value: str, *, fallback: str = "run", max_len: int = 80) -> str:
    """Sanitize an arbitrary tag into a path-safe run token.

    Over-long tokens are truncated with a stable uuid5 digest suffix so
    distinct inputs stay distinguishable.
    """
    token = SAFE_RUN_TOKEN_RE.sub("-", value.strip()).strip(".-_")
    if not token:
        token = fallback
    if len(token) <= max_len:
        return token
    digest = uuid.uuid5(uuid.NAMESPACE_URL, token).hex[:8]
    keep = max(1, max_len - len(digest) - 1)
    return f"{token[:keep].rstrip('.-_')}-{digest}"


def allocate_run_dir(base_dir: Path, tag: str = "", *, attempts: int = 10) -> Path:
    """Allocate a unique ``<base_dir>/<utc-ts>_<safe_tag>`` directory.

    The first attempt uses the plain ``<ts>_<tag>`` name; collisions retry
    with a short random suffix. Raises after ``attempts`` collisions.
    """
    base_dir = Path(base_dir)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tag_token = safe_run_token(tag) if tag else ""
    stem = f"{ts}_{tag_token}" if tag_token else ts
    for attempt in range(attempts):
        name = stem if attempt == 0 else f"{stem}_{uuid.uuid4().hex[:8]}"
        run_dir = base_dir / name
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
        except FileExistsError:
            continue
    raise WorkspaceStateError(f"failed to allocate a unique run directory under {base_dir}")
