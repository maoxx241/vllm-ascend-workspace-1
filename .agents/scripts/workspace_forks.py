#!/usr/bin/env python3
"""Plan or configure personal development forks independently of agent skills."""

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from vaws_github import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit((_vaws_entry.run(main) if _vaws_entry else main()))
