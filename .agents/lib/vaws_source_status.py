"""On-demand Git facts for selected local sources; never prepare or publish code."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

from vaws_local_state import read_preparation
from vaws_native_workspace import git

BUSINESS_REPOS = ("vllm", "vllm-ascend")


def source_roots(path: Path) -> tuple[Path, dict[str, Path], str]:
    """Resolve an explicit bundle or only the two existing known child roots."""
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError("source inspection requires a directory")
    nearest = None
    for candidate in (path, *path.parents):
        if nearest is None and os.path.lexists(candidate / ".git"):
            nearest = candidate
        marker = candidate / ".vaws-local/native-workspace.json"
        if os.path.lexists(marker):
            record = read_preparation(candidate)
            if record is None:
                raise ValueError(f"unreadable preparation receipt: {marker}")
            roots = {"workspace": Path(record["workspace"]),
                     **{name: Path(value) for name, value in record["sources"].items()}}
            if nearest is not None and nearest not in {*roots.values(), Path(record["native_workspace"])}:
                raise ValueError(f"current repository is not selected by this workspace: {nearest}")
            return Path(record["workspace"]), roots, "prepared"
    if nearest is None:
        raise ValueError(f"no repository boundary found: {path}")
    # A known direct child belongs to its enclosing bundle. An arbitrary nested
    # Git checkout remains its own root; never enumerate other nested repos.
    root = nearest
    if root.name in BUSINESS_REPOS and os.path.lexists(root.parent / ".git"):
        root = root.parent
    roots = {"workspace": root}
    roots.update({name: root / name for name in BUSINESS_REPOS if os.path.lexists(root / name)})
    return root, roots, "existing"


def _text(value: bytes) -> str:
    return value.decode("utf-8", "replace")


def _parse_status(raw: bytes) -> dict:
    result = {"head": None, "branch": None, "upstream": None, "ahead": None, "behind": None,
              "staged": [], "working": [], "untracked": [], "conflicted": []}
    records = iter(raw.split(b"\0"))
    for row in records:
        if not row:
            continue
        if row.startswith(b"# "):
            key, value = row[2:].split(b" ", 1)
            if key == b"branch.oid":
                result["head"] = None if value == b"(initial)" else _text(value)
            elif key == b"branch.head":
                result["branch"] = None if value == b"(detached)" else _text(value)
            elif key == b"branch.upstream":
                result["upstream"] = _text(value)
            elif key == b"branch.ab":
                ahead, behind = value.split()
                result.update(ahead=int(ahead), behind=-int(behind))
            continue
        if row.startswith(b"? "):
            result["untracked"].append(_text(row[2:]))
            continue
        kind = row[:1]
        fields = row.split(b" ", {b"1": 8, b"2": 9, b"u": 10}.get(kind, 0))
        if kind not in {b"1", b"2", b"u"} or len(fields) != {b"1": 9, b"2": 10, b"u": 11}[kind]:
            raise ValueError("unexpected Git porcelain status record")
        entry = {"path": _text(fields[-1]), "code": _text(fields[1])}
        if kind == b"2":
            original = next(records, None)
            if original is None or not original:
                raise ValueError("incomplete Git rename record")
            entry["original_path"] = _text(original)
        if kind == b"u":
            result["conflicted"].append(entry)
        if fields[1][:1] != b".":
            result["staged"].append(entry)
        if fields[1][1:] != b".":
            result["working"].append(entry)
    result["worktree_clean"] = not any(result[key] for key in ("staged", "working", "untracked", "conflicted"))
    # Ahead/behind use existing local tracking refs, never a fetch or a claim
    # that all branches, stashes or objects have been published elsewhere.
    result["upstream_comparison"] = "local_tracking_ref" if result["ahead"] is not None else "unavailable"
    return result


def _repository_identity(path: Path) -> str:
    if not path.is_dir() or not os.path.lexists(path / ".git"):
        raise ValueError(f"selected source is missing its Git boundary: {path}")
    top = Path(_text(git(path, "rev-parse", "--show-toplevel", timeout=30)).strip()).resolve()
    if top != path.resolve():
        raise ValueError(f"Git resolved a different source root: {path}")
    common = _text(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir", timeout=30)).strip()
    return str(Path(common).resolve())


def _repository_status(path: Path) -> dict:
    result = _parse_status(git(path, "status", "--porcelain=v2", "-z", "--branch",
                               "--untracked-files=all", "--ignore-submodules=none", timeout=30))
    return {"path": str(path), "complete": True, **result}


def workspace_status(path: Path, *, repo: str | None = None) -> dict:
    """Read worktree facts, including explicit failures instead of false clean."""
    try:
        workspace, roots, selection = source_roots(path)
        if repo is not None and repo not in roots:
            raise ValueError(f"repository is not selected: {repo}")
    except (OSError, ValueError, RuntimeError) as exc:
        return {"complete": False, "worktree_clean": None, "repositories": {}, "error": str(exc)}
    results, common_dirs = {}, {}
    for name, root in roots.items():
        selected = repo is None or repo == name
        if not selected and (not root.is_dir() or not os.path.lexists(root / ".git")):
            continue
        try:
            # Other declared roots establish repository identity only. A single
            # repository request must not scan their workfiles or depend on
            # their availability.
            common = _repository_identity(root)
            if common in common_dirs:
                previous = common_dirs[common]
                if previous != "workspace" and previous in results:
                    results[previous] = {"path": str(roots[previous]), "complete": False,
                                         "worktree_clean": None,
                                         "error": f"source shares the Git repository of {name}: {roots[previous]}"}
                raise ValueError(f"source shares the Git repository of {common_dirs[common]}: {root}")
            common_dirs[common] = name
            if selected:
                results[name] = _repository_status(root)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            if selected:
                results[name] = {"path": str(root), "complete": False, "worktree_clean": None, "error": str(exc)}
    complete = all(row["complete"] for row in results.values())
    return {"workspace": str(workspace), "selection": selection, "complete": complete,
            "worktree_clean": all(row["worktree_clean"] for row in results.values()) if complete else None,
            "repositories": results}


def workspace_diff(path: Path, *, repo: str | None = None, staged: bool = False,
                   max_bytes: int = 32768) -> dict:
    """Return patches with one shared byte budget; untracked files remain facts."""
    if not 1 <= max_bytes <= 1048576:
        raise ValueError("max_bytes must be between 1 and 1048576")
    result = workspace_status(path, repo=repo)
    remaining = max_bytes
    for row in result["repositories"].values():
        for field in ("staged", "working", "untracked", "conflicted"):
            if field in row:
                row[field + "_count"] = len(row.pop(field))
        if not row["complete"]:
            continue
        try:
            patch = git(Path(row["path"]), "diff", "--no-ext-diff", "--no-textconv", "--no-color",
                        *(["--cached"] if staged else []), "--", timeout=30)
            rendered = patch[:remaining].decode("utf-8", "ignore")
            used = len(rendered.encode("utf-8"))
            row.update(diff=rendered, diff_bytes=len(patch), truncated=used < len(patch))
            remaining -= used
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            row.update(complete=False, worktree_clean=None, error=str(exc))
            result.update(complete=False, worktree_clean=None)
    return {**result, "staged": staged, "max_bytes": max_bytes,
            "truncated": any(row.get("truncated", False) for row in result["repositories"].values())}
