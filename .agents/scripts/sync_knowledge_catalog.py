#!/usr/bin/env python3
"""Generate/check the lightweight catalog from the locked official package."""

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
    (_vaws_entry.run(main) if _vaws_entry else main())
