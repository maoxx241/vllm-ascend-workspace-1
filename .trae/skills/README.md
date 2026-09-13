# Trae skill entry points

The serving stub reads its canonical package under `.agents/skills/`.
First-use setup is linked from AGENTS, outside automatic Skill discovery. ModelScope is a generated projection of its canonical skill.
Use `uv run --no-project python .agents/scripts/sync_claude_skills.py` after editing ModelScope.

Task binding and managed execution use coordinator tools directly. For explicit
knowledge editing, read the installed skill with
the configured interpreter's `python -m vaws_knowledge skill` or install it into the native client's
skill directory with `--install-dir`.
