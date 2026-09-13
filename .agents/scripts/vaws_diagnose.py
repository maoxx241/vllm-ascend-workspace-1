#!/usr/bin/env python3
"""Local diagnostics and reporting worker; no managed environment bootstrap."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents" / "lib"))


def main(argv=None):
    try:
        from vaws_diagnostics.cli import main as diagnostics_main
    except ImportError:
        print(json.dumps({"status": "unavailable", "component": "vaws-diagnostics",
                          "reason": "The diagnostics package is unavailable in this interpreter; no setup or upload was attempted."}),
              file=sys.stderr)
        return 2
    return diagnostics_main(argv)


if __name__ == "__main__":
    from vaws_diagnostics_adapter import bootstrap
    raise SystemExit(bootstrap(__file__).run(main))
