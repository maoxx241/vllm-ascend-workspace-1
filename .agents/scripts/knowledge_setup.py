#!/usr/bin/env python3
"""Prepare knowledge references or maintain their corpus; reuse community consent."""
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
from vaws_community import policy_path, read_choice  # noqa: E402
from vaws_github import load_github_identity  # noqa: E402
from vaws_local_state import shared_workspace_root  # noqa: E402
from vaws_venv import configure_windows_stdio  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    configure_windows_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", help="change the shared corpus while retaining currently authorized publishing")
    args = parser.parse_args(argv)
    config = knowledge_config_path(ROOT)
    configured = None
    if args.repository is not None:
        existing = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
        if not isinstance(existing, dict):
            raise ValueError("existing knowledge configuration must be a JSON object")
        settings = existing.get("publishing", {})
        if not isinstance(settings, dict):
            raise ValueError("existing knowledge publishing configuration must be a JSON object")
        owner = shared_workspace_root(ROOT)
        try:
            choice = read_choice(owner)
        except (OSError, ValueError):
            choice = None  # Invalid consent cannot authorize contribution.
        identity = (load_github_identity(owner) or {}) if choice and choice["decision"] == "enabled" else {}
        login = identity.get("login")
        contribute = bool(choice and choice["decision"] == "enabled" and login
                          and settings.get("enabled") is True and settings.get("fork"))
        command = ["publishing", "configure", "--config", knowledge_owner_path(ROOT, config),
                   "--repository", args.repository, "--consent-file", knowledge_owner_path(ROOT, policy_path(owner))]
        if login:
            command.extend(["--github-user", login])
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
