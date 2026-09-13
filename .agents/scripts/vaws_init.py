#!/usr/bin/env python3
"""Inspect or complete first-use choices; repeated tasks reuse local setup."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))


def main(argv=None):
    from vaws_onboarding import initialize, status
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("status", help="read local choices; authentication discovery is explicit")
    inspect.add_argument("--detect-auth", action="store_true")
    apply = sub.add_parser("apply", help="apply explicit choices or resume completed stages")
    apply.add_argument("--github-user")
    apply.add_argument("--fork", choices=("yes", "no"))
    apply.add_argument("--star", choices=("yes", "no"))
    apply.add_argument("--community", choices=("enabled", "disabled"))
    apply.add_argument("--client", choices=("all", "codex", "cursor", "claude", "grok", "kimi"),
                       help="first setup defaults to all installed clients; resume preserves the selection")
    args = parser.parse_args(argv)
    if args.command == "status":
        result = status(ROOT, detect_auth=args.detect_auth)
    else:
        result = initialize(ROOT, github_user=args.github_user, fork=None if args.fork is None else args.fork == "yes",
                            star=None if args.star is None else args.star == "yes", community=args.community, client=args.client)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if args.command == "status" or result["state"] in {"ready", "choice_updated"} else 1


if __name__ == "__main__":
    from vaws_diagnostics_adapter import bootstrap
    raise SystemExit(bootstrap(__file__).run(main))
