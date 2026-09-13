#!/usr/bin/env python3
"""Show locked source inputs or explicitly refresh their upstream declarations."""
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
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="Read selected source revisions locally, without network access")
    show.add_argument("--channel", choices=CHANNELS, default="development")
    refresh = commands.add_parser("refresh", help="Refresh only sources.lock.json; do not check out code")
    refresh.add_argument("--ascend-commit", help="Use this exact Ascend commit instead of resolving main once")
    args = parser.parse_args(argv)
    try:
        if args.command == "show":
            result = {"sources": selected_sources(args.root, args.channel), "channel": args.channel}
        else:
            lock = refresh_source_lock(ascend_commit=args.ascend_commit)
            changed = write_source_lock(args.root, lock)
            result = {"changed": changed, "lock": lock, "evidence": "upstream source declarations"}
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
