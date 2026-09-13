#!/usr/bin/env python3
"""Prepare local knowledge; public contribution is an explicit setup choice."""
from __future__ import annotations

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

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
from vaws_knowledge_service import knowledge_config_path, knowledge_owner_path, prepare_knowledge, run_knowledge_cli  # noqa: E402
from vaws_venv import configure_windows_stdio  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    configure_windows_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", help="change the shared corpus while retaining the contribution choice")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--read-only", action="store_true", help="enable shared updates and disable public contribution")
    mode.add_argument("--contribute", action="store_true", help="explicitly enable public contribution and prepare its fork")
    args = parser.parse_args(argv)
    config = knowledge_config_path(ROOT)
    configured = None
    if args.repository is not None or args.read_only or args.contribute:
        existing = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
        if not isinstance(existing, dict):
            raise ValueError("existing knowledge configuration must be a JSON object")
        settings = existing.get("publishing") or {}
        shared = existing.get("shared_sync") or {}
        repository = args.repository or shared.get("repository") or settings.get("repository")
        contribute = args.contribute or bool(settings.get("enabled") and settings.get("fork") and not args.read_only)
        command = ["publishing", "configure", "--config", knowledge_owner_path(ROOT, config)]
        if repository:
            command.extend(["--repository", repository])
        if not contribute:
            command.append("--read-only")
        code, configured = run_knowledge_cli(ROOT, command)
        if code:
            print(json.dumps(configured, ensure_ascii=False, indent=2))
            return 1
    result = prepare_knowledge(ROOT)
    if configured is not None:
        result = {**result, "configuration": configured}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit((_vaws_entry.run(main) if _vaws_entry else main()))
