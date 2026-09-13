#!/usr/bin/env python3
"""Start a native client in an independent editing workspace.

Same command in PowerShell, bash or zsh:
  uv run --no-project python .agents/scripts/vaws_client.py codex
  uv run --no-project python .agents/scripts/vaws_client.py kimi --workspace PATH

New directories reuse prepared or local fixed inputs; --latest checks upstream.
Existing --workspace directories keep their code, environment and configuration.
Pass native arguments after --; resume with the original --workspace directory.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
sys.path.insert(0, str(ROOT / ".agents/scripts"))
from vaws_native_workspace import WorkspaceCopyError
from vaws_venv import ensure_workspace_interpreter

CLIENT_COMMANDS = {"codex": "codex", "grok": "grok", "kimi": "kimi", "claude": "claude", "cursor": "cursor-agent"}
NATIVE_IDENTITY_ENV = {"VAWS_CONTEXT_FILE", "VAWS_PARENT_CONTEXT", "VAWS_ATTACH_CONTEXT",
                       "CODEX_THREAD_ID", "CODEX_SESSION_ID", "VAWS_RELEASE_LAUNCH"}


def resolve_client(client: str) -> list[str]:
    executable = None
    if client == "kimi":
        # Match client setup's Kimi Code selection when legacy kimi-cli also
        # provides a `kimi` command on PATH with a different config contract.
        candidate = Path(os.environ.get("KIMI_CODE_HOME", str(Path.home() / ".kimi-code"))) / "bin" / ("kimi.exe" if os.name == "nt" else "kimi")
        if candidate.is_file():
            executable = str(candidate)
    if not executable:
        executable = shutil.which(CLIENT_COMMANDS[client])
    if not executable:
        raise WorkspaceCopyError(f"{client} is not installed in this environment; install its native CLI before starting it")
    return [executable]


def prepare_workspace(client: str, workspace: Path | None, *, source: Path = ROOT,
                      source_channel: str = "development", sources=None, latest=False, preferred=None) -> dict:
    from vaws_local_state import shared_workspace_root
    from vaws_workspace_entry import read_preparation
    from vaws_worktree_setup import prepare_worktree

    project = shared_workspace_root(source)
    target = workspace.expanduser().resolve() if workspace else project.parent / (
        project.name + "-" + client + "-" + uuid.uuid4().hex[:12])
    if target.exists():
        record = read_preparation(target)
        if record is None:
            raise WorkspaceCopyError("--workspace must name a completed editing workspace; use a new path to prepare one")
        if Path(record["project_root"]).resolve() != project:
            raise WorkspaceCopyError("--workspace belongs to another project")
    options = {"source_channel": source_channel}
    if sources is not None:
        options["sources"] = sources
    if latest:
        options["latest"] = True
    if preferred is not None:
        options["preferred"] = preferred
    return prepare_worktree(client, source, target, **options)


def client_environment(environment=None) -> dict[str, str]:
    # A new native session obtains identity from its own hook. Starting from
    # another agent process does not implicitly join that agent's task.
    return {key: value for key, value in (os.environ if environment is None else environment).items()
            if key not in NATIVE_IDENTITY_ENV}


def activated_client_environment(receipt: dict, environment=None) -> dict[str, str]:
    """Give native shells ordinary venv activation without shell-specific code."""
    result = dict(os.environ if environment is None else environment)
    scripts = str(Path(receipt["python"]).parent)
    result["PATH"] = scripts + os.pathsep + result.get("PATH", "")
    result["VIRTUAL_ENV"] = str(receipt["root"])
    result.pop("PYTHONHOME", None)
    return result


def run_client(command: list[str], workspace: Path, *, environment=None) -> int:
    environment = client_environment(environment)
    if os.name == "nt":
        from vaws_windows import owned_process
        with owned_process(command, cwd=str(workspace), env=environment, stdin=sys.stdin,
                           stdout=sys.stdout, stderr=sys.stderr, release_on_exit=True,
                           preserve_console=True) as process:
            return process.wait()
    # Native interactive clients retain their terminal and signal behavior.
    # The process has its real cwd before any model or tool request can run.
    os.chdir(workspace)
    os.execvpe(command[0], command, environment)
    raise AssertionError("exec returned")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client", choices=sorted(CLIENT_COMMANDS))
    parser.add_argument("--workspace", type=Path, help="reuse a prepared workspace or create one at a new path")
    parser.add_argument("--source-channel", choices=("development", "release"), default="development")
    parser.add_argument("--latest", action="store_true", help="explicitly check upstream for a new workspace")
    parser.add_argument("--sources", nargs="*", choices=("vllm", "vllm-ascend"))
    parser.add_argument("--repo", choices=("workspace", "vllm", "vllm-ascend"), help="explicit editing repository for a new workspace")
    values = list(sys.argv[1:] if argv is None else argv)
    split = values.index("--") if "--" in values else len(values)
    args = parser.parse_args(values[:split])
    native_args = values[split + 1:]
    try:
        command = resolve_client(args.client)
        from vaws_environment import MANAGED_PIN_ENV, PIN_ENV, saved_ready
        from vaws_local_owner import accessible_windows_path, windows_mounted_workspace
        from vaws_worktree_setup import unpinned_environment

        # Preparation owns code, packages and wiring once. The native process
        # starts with the returned real cwd, before its first tool call.
        os.environ.pop(PIN_ENV, None)
        os.environ.pop(MANAGED_PIN_ENV, None)
        existing = args.workspace is not None and args.workspace.expanduser().exists()
        bootstrap = ROOT
        if existing:
            from vaws_workspace_entry import read_preparation
            bootstrap = args.workspace.expanduser().resolve()
            record = read_preparation(bootstrap)
            if record is not None:
                bootstrap = Path(record["workspace"])
            pinned = saved_ready(bootstrap)
            os.environ[PIN_ENV] = pinned["receipt"]
            if pinned["platform"] == "win32":
                os.environ[MANAGED_PIN_ENV] = pinned["receipt"]
            elif windows_mounted_workspace(bootstrap):
                os.environ[MANAGED_PIN_ENV] = saved_ready(bootstrap, target_platform="win32")["receipt"]
        ensure_workspace_interpreter(repo_root=bootstrap, use_saved=existing)
        options = {"source_channel": args.source_channel}
        if args.sources is not None:
            options["sources"] = tuple(args.sources)
        if args.latest:
            options["latest"] = True
        if args.repo is not None:
            options["preferred"] = args.repo
        result = prepare_workspace(args.client, args.workspace, source=ROOT, **options)
        target = Path(result["workspace"])
        native = saved_ready(target)
        import vaws_client_setup
        provider = vaws_client_setup.existing_task_env(args.client, target)
        environment = activated_client_environment(native, unpinned_environment())
        environment[PIN_ENV] = native["receipt"]
        if native["platform"] == "win32":
            environment[MANAGED_PIN_ENV] = native["receipt"]
        elif windows_mounted_workspace(target):
            environment[MANAGED_PIN_ENV] = saved_ready(target, target_platform="win32")["receipt"]
        for key in ("VAWS_AGENT_SESSIONS_DIR", "VAWS_COORDINATOR_STATE_DIR", "VAWS_GITHUB_IDENTITY_FILE"):
            if key in provider:
                environment[key] = accessible_windows_path(provider[key])
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr, flush=True)
        return run_client([*command, *native_args], target, environment=environment)

    except (WorkspaceCopyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
