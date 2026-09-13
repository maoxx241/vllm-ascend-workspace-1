#!/usr/bin/env python3
"""Start, inspect or stop one managed vLLM service."""
from __future__ import annotations

# Observe the real CLI before optional runtime imports; copied remote helpers stay standalone.
if __name__ == "__main__":
    import sys as _vaws_sys
    from pathlib import Path as _VawsPath
    _vaws_parents = _VawsPath(__file__).absolute().parents
    _vaws_lib = _vaws_parents[3] / "lib" if len(_vaws_parents) > 3 else None
    _vaws_entry = None
    if _vaws_lib is not None and (_vaws_lib / "vaws_diagnostics_adapter.py").is_file():
        _vaws_sys.path.insert(0, str(_vaws_lib))
        from vaws_diagnostics_adapter import bootstrap as _vaws_bootstrap
        _vaws_entry = _vaws_bootstrap(__file__)

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / '.agents/lib'))
from vaws_venv import ensure_workspace_interpreter

if __name__ == "__main__":
    from vaws_managed_entry import ensure_managed_entry
    ensure_managed_entry(repo_root=ROOT, entry_file=__file__, local_options=("--wrap-script-local",))

ensure_workspace_interpreter(repo_root=ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=('start', 'status', 'stop'))
    parser.add_argument('args', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    module = importlib.import_module(f'_serving_{args.action}')
    return module.main(args.args)


if __name__ == '__main__':
    raise SystemExit((_vaws_entry.run(main) if _vaws_entry else main()))
