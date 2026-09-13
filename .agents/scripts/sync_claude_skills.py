#!/usr/bin/env python3
"""Generate Claude Code skill shims from `.agents/skills`.

`.claude/skills/<name>/SKILL.md` exposes the canonical skill's metadata and
points to its instructions. Edit skills in `.agents/skills`, then regenerate.

    python3 .agents/scripts/sync_claude_skills.py          # regenerate
    python3 .agents/scripts/sync_claude_skills.py --check  # verify, exit 1 on drift
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

import sys

import argparse
import json
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / ".agents" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
from vaws_venv import ensure_workspace_interpreter  # noqa: E402

ensure_workspace_interpreter(repo_root=ROOT)

import yaml  # noqa: E402

AGENTS_SKILLS = ROOT / ".agents" / "skills"
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
MAX_SHIM_LINES = 60


def parse_frontmatter(source: Path) -> dict[str, str]:
    lines = source.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    end = lines.index("---", 1)
    return yaml.safe_load("\n".join(lines[1:end]))


def first_markdown_heading(source: Path, default: str) -> str:
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip() or default
    return default


def expected_skill_body(skill_dir: Path) -> str:
    source = skill_dir / "SKILL.md"
    frontmatter = parse_frontmatter(source)
    name = frontmatter.get("name") or skill_dir.name
    description = frontmatter.get("description") or first_markdown_heading(source, skill_dir.name)
    title = first_markdown_heading(source, name)
    return f"""---
name: {json.dumps(name, ensure_ascii=False)}
description: {json.dumps(description, ensure_ascii=False)}
---

<!-- Generated from .agents/skills/{skill_dir.name}/SKILL.md. Do not edit. -->

# {title}

Read `.agents/skills/{skill_dir.name}/SKILL.md` and only the references needed
for the current task. The canonical skill owns the workflow.
"""


def source_skill_dirs() -> list[Path]:
    return sorted(path for path in AGENTS_SKILLS.iterdir() if path.is_dir() and (path / "SKILL.md").exists())


class ProjectionConflict(RuntimeError):
    """A generated target is linked or contains user-owned content."""


def _require_projection_path(root: Path, target: Path) -> None:
    current = root
    for part in (None, *target.relative_to(root).parts):
        if part is not None:
            current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ProjectionConflict(f"linked projection path is not writable: {current}")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ProjectionConflict(f"projection target escapes its root: {target}")


def _shim_marker(name: str) -> str:
    return f"<!-- Generated from .agents/skills/{name}/SKILL.md. Do not edit. -->"


def check_shims() -> list[str]:
    errors: list[str] = []
    expected_names = {path.name for path in source_skill_dirs()}
    observed_names = {path.name for path in CLAUDE_SKILLS.iterdir() if path.is_dir()} if CLAUDE_SKILLS.exists() else set()
    for missing in sorted(expected_names - observed_names):
        errors.append(f"missing Claude skill shim: {missing}")
    for extra in sorted(observed_names - expected_names):
        errors.append(f"extra Claude skill shim: {extra}")
    for name in sorted(observed_names & expected_names):
        for path in sorted((CLAUDE_SKILLS / name).iterdir()):
            if path.name != "SKILL.md":
                errors.append(f"unexpected file in Claude skill shim {name}: {path.name}")
    for skill_dir in source_skill_dirs():
        target = CLAUDE_SKILLS / skill_dir.name / "SKILL.md"
        if not target.exists():
            continue
        expected = expected_skill_body(skill_dir)
        observed = target.read_text(encoding="utf-8")
        if observed != expected:
            errors.append(f"stale Claude skill shim: {skill_dir.name}")
        if len(observed.splitlines()) > MAX_SHIM_LINES:
            errors.append(f"Claude skill shim is too large: {skill_dir.name}")
    return errors


def sync_shims() -> None:
    _require_projection_path(CLAUDE_SKILLS.parent, CLAUDE_SKILLS)
    CLAUDE_SKILLS.mkdir(parents=True, exist_ok=True)
    for skill_dir in source_skill_dirs():
        target_dir = CLAUDE_SKILLS / skill_dir.name
        target = target_dir / "SKILL.md"
        _require_projection_path(CLAUDE_SKILLS.parent, target)
        if target.exists() and _shim_marker(skill_dir.name) not in target.read_text(encoding="utf-8").splitlines():
            raise ProjectionConflict(f"existing Claude skill is not a generated shim: {target}")
        target_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(expected_skill_body(skill_dir), encoding="utf-8", newline="\n")
    for existing in CLAUDE_SKILLS.iterdir():
        if (
            not existing.is_dir()
            or existing.is_symlink()
            or existing.resolve().parent != CLAUDE_SKILLS.resolve()
            or (AGENTS_SKILLS / existing.name / "SKILL.md").exists()
        ):
            continue
        target = existing / "SKILL.md"
        if target.is_symlink() or list(existing.iterdir()) != [target]:
            continue
        try:
            _require_projection_path(CLAUDE_SKILLS.parent, target)
        except ProjectionConflict:
            continue
        if target.is_file() and _shim_marker(existing.name) in target.read_text(encoding="utf-8").splitlines():
            target.unlink()
            existing.rmdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync generated Claude Code skill shims from .agents/skills."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify that .claude/skills shims are synchronized.",
    )
    args = parser.parse_args(argv)
    if args.check:
        errors = check_shims()
        for error in errors:
            print(error)
        return 1 if errors else 0
    try:
        sync_shims()
    except ProjectionConflict as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit((_vaws_entry.run(main) if _vaws_entry else main()))
