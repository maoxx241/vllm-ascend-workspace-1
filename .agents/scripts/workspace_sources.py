#!/usr/bin/env python3
"""Inspect local source Git state or explicitly refresh locked source inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))

from vaws_source_lock import CHANNELS, refresh_source_lock, selected_sources, write_source_lock
from vaws_venv import configure_windows_stdio


def main(argv=None) -> int:
    configure_windows_stdio()
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, help="source directory; status/diff default to the current directory")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="Read selected source revisions locally, without network access")
    show.add_argument("--channel", choices=CHANNELS, default="development")
    refresh = commands.add_parser("refresh", help="Refresh only sources.lock.json; do not check out code")
    refresh.add_argument("--ascend-commit", help="Use this exact Ascend commit instead of resolving main once")
    status = commands.add_parser("status", help="Inspect actual selected repositories locally; never prepare sources")
    status.add_argument("--repo", help="inspect one selected repository name")
    diff = commands.add_parser("diff", help="Show bounded patches from the actual selected repositories")
    diff.add_argument("--repo", help="inspect one selected repository name")
    diff.add_argument("--staged", action="store_true", help="show index changes instead of working changes")
    diff.add_argument("--max-bytes", type=int, default=32768, help="total patch byte limit (1 to 1048576)")
    args = parser.parse_args(argv)
    try:
        if args.command in {"status", "diff"}:
            from vaws_source_status import workspace_diff, workspace_status
            root = args.root if args.root is not None else Path.cwd()
            result = (workspace_status(root, repo=args.repo) if args.command == "status" else
                      workspace_diff(root, repo=args.repo, staged=args.staged, max_bytes=args.max_bytes))
            print(json.dumps({"ok": result["complete"], **result}, ensure_ascii=False))
            return 0 if result["complete"] else 1
        elif args.command == "show":
            result = {"sources": selected_sources(args.root or ROOT, args.channel), "channel": args.channel}
        else:
            lock = refresh_source_lock(ascend_commit=args.ascend_commit)
            changed = write_source_lock(args.root or ROOT, lock)
            result = {"changed": changed, "lock": lock, "evidence": "upstream source declarations"}
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
