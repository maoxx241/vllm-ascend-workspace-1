#!/usr/bin/env python3
"""Generate/check the lightweight catalog from the locked official package."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))

from vaws_knowledge_catalog import RELATIVE_PATH, generate_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = generate_catalog((ROOT / "uv.lock").read_bytes())
    path = ROOT / RELATIVE_PATH
    if args.check:
        if not path.is_file() or path.read_bytes() != data:
            parser.exit(1, "knowledge catalog is stale; run sync_knowledge_catalog.py in the locked dev environment\n")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


if __name__ == "__main__":
    main()
