#!/usr/bin/env python3
"""``python -m ascend_profile.html_report_v2`` entry point."""
from __future__ import annotations

# Observe the real CLI before optional runtime imports; copied remote helpers stay standalone.
if __name__ == "__main__":
    import sys as _vaws_sys
    from pathlib import Path as _VawsPath
    _vaws_parents = _VawsPath(__file__).absolute().parents
    _vaws_lib = _vaws_parents[5] / "lib" if len(_vaws_parents) > 5 else None
    _vaws_entry = None
    if _vaws_lib is not None and (_vaws_lib / "vaws_diagnostics_adapter.py").is_file():
        _vaws_sys.path.insert(0, str(_vaws_lib))
        from vaws_diagnostics_adapter import bootstrap as _vaws_bootstrap
        _vaws_entry = _vaws_bootstrap(__file__)

try:
    from ascend_profile.html_report_v2 import main  # type: ignore
except ImportError:  # pragma: no cover - script-mode fallback
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from html_report_v2 import main  # type: ignore[no-redef]

if __name__ == "__main__":
    import sys
    from pathlib import Path
    _repo_root = Path(__file__).resolve().parents[6]
    _lib = _repo_root / ".agents" / "lib"
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))
    from vaws_venv import ensure_workspace_interpreter
    ensure_workspace_interpreter(repo_root=_repo_root)
    raise SystemExit((_vaws_entry.run(main) if _vaws_entry else main()))
