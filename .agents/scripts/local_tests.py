#!/usr/bin/env python3
"""Run selected local tests with per-file/suite progress and retained logs."""

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
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
from vaws_venv import ensure_workspace_interpreter

ensure_workspace_interpreter(repo_root=ROOT)

from vaws_local_tests import main

if __name__ == "__main__":
    raise SystemExit((_vaws_entry.run(lambda: main(ROOT)) if _vaws_entry else main(ROOT)))
