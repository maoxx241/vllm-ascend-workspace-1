"""Local first-use guidance and explicit completed workspace preparation.

These helpers perform no upstream fetch, source discovery or environment setup.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

from vaws_local_state import read_preparation

FIRST_USE_REFERENCE = ".agents/bootstrap/repo-init/SKILL.md"
MAINTENANCE_REFERENCE = "docs/forks-and-updates.md#显式维护与证据"


def prepared_sources(root: Path) -> dict[str, str] | None:
    """Return only roots published by preparation; absence does not prepare them."""
    record = read_preparation(root)
    return dict(record["sources"]) if record is not None else None


def write_preparation(root: Path, *, project_root: Path, native_workspace: Path,
                      workspace: Path, sources: dict, source_channel: str = "development",
                      preferred: str | None = None,
                      **facts) -> dict:
    """Publish caller-validated preparation using the existing local receipt."""
    from vaws_session_state import write_json
    from vaws_source_view import source_focus, write_source_view

    root = Path(root).resolve()
    record = {**facts, "state": "ready", "project_root": str(Path(project_root).resolve()),
              "native_workspace": str(Path(native_workspace).resolve()),
              "workspace": str(Path(workspace).resolve()), "source_channel": source_channel,
              "sources": {name: str(Path(path).resolve()) for name, path in sources.items()}}
    if record["sources"].get("workspace", record["workspace"]) != record["workspace"]:
        raise ValueError("workspace source must match the editing workspace")
    record["sources"]["workspace"] = record["workspace"]
    if str(root) not in (record["workspace"], record["native_workspace"]):
        raise ValueError("preparation receipt must belong to its native or editing workspace")
    if not Path(record["workspace"]).is_dir():
        raise ValueError("editing workspace does not exist")
    for name, path in record["sources"].items():
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("source names must be single repository names")
        target = Path(path)
        workspace_path = Path(record["workspace"])
        if target != workspace_path and workspace_path not in target.parents:
            raise ValueError("prepared source must belong to the editing workspace")
        if not target.is_dir() or not (target / ".git").exists():
            raise ValueError(f"prepared source is not a populated repository: {target}")
    focus = source_focus(Path(record["workspace"]), record["sources"], preferred=preferred)
    for key, value in focus.items():
        if key in facts and facts[key] != value:
            raise ValueError(f"preparation {key} conflicts with the selected editing repository")
    record.update(focus)
    if root == Path(record["workspace"]):
        record["editor_workspace"] = str(write_source_view(root, record["sources"], preferred=focus["repository"]))
    write_json(root / ".vaws-local/native-workspace.json", record)
    return record


def copy_workspace_identity(source: Path, target: Path) -> None:
    """Copy a non-secret setup snapshot; never copy task identity or replace it."""
    from vaws_github import load_github_identity
    identity = load_github_identity(source)
    if identity:
        destination = target / ".vaws-local/github.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {key: identity[key] for key in ("schema", "login", "github_user_id", "forks") if key in identity}
        try:
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(snapshot, stream, ensure_ascii=False)
                stream.write("\n")
        except FileExistsError:
            pass


def workspace_entry(root: Path, *, announce: bool = True) -> dict:
    root = root.resolve()
    state = root / ".vaws-local/updates"
    try:
        identity_path = root / ".vaws-local/github.json"
        if not identity_path.is_file():
            initialized = root / ".vaws-local/client-initialization.json"
            if initialized.is_file():
                return {"state": "identity_missing", "path": str(identity_path),
                        "evidence": str(initialized), "reference": MAINTENANCE_REFERENCE,
                        "message": "Saved GitHub identity is missing from an initialized repository. "
                                   "Restore its prior snapshot or inspect workspace_forks.py's plan using "
                                   "the already confirmed username; do not restart first-use setup."}
            if not announce or os.environ.get("VAWS_RELEASE_LAUNCH") == "1":
                # Successful GUI hook stderr may be invisible. Do not consume
                # the first visible prompt merely because a hook fired.
                return {"state": "identity_pending", "reference": FIRST_USE_REFERENCE}
            notice = state / "onboarding-notice.json"
            state.mkdir(parents=True, exist_ok=True)
            try:
                with notice.open("x", encoding="utf-8") as stream:
                    json.dump({"offered_at": time.time()}, stream)
            except FileExistsError:
                return {"state": "identity_pending", "reference": FIRST_USE_REFERENCE}
            return {"state": "needs_github_user", "message":
                    "First use: provide your personal GitHub username to configure personal forks and upstream updates. "
                    f"Read {FIRST_USE_REFERENCE} for this repository's one-time initialization. "
                    "Local work remains available.", "reference": FIRST_USE_REFERENCE}
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        if (not isinstance(identity, dict) or identity.get("schema") != "vaws.github.v1"
                or not isinstance(identity.get("login"), str) or not identity["login"].strip()):
            return {"state": "identity_invalid", "path": str(identity_path),
                    "reference": MAINTENANCE_REFERENCE,
                    "message": "Saved GitHub identity has no login. Restore its prior snapshot or inspect "
                               "workspace_forks.py's plan using the already confirmed username."}
        config_path = state / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
        if not isinstance(config, dict):
            return {"state": "configuration_invalid", "message": "Update configuration must be a JSON object."}
        if config.get("enabled") is False:
            return {"state": "disabled"}
        return {"state": "configured"}
    except Exception as exc:
        # This optional entry cannot prevent the user's native session. Retain
        # concrete diagnostics instead of converting an update failure into a
        # task/knowledge prerequisite.
        return {"state": "unavailable", "error": str(exc)}
