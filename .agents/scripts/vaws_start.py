#!/usr/bin/env python3
"""Prepare one new native task's workspace; repeat calls reuse its selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))

from vaws_environment import read_receipt, saved_ready, select_environment
from vaws_knowledge_service import knowledge_config_path
from vaws_local_state import prepared_workspace, shared_workspace_root
from vaws_native_workspace import create_prepared_workspace
from vaws_session_state import task_dir, write_json
from vaws_task_target import resolve_context_file
from vaws_venv import configure_windows_stdio, ensure_workspace_interpreter
from vaws_workspace_entry import (FIRST_USE_REFERENCE, MAINTENANCE_REFERENCE, copy_workspace_identity,
                                  prepared_sources, read_preparation, workspace_entry, write_preparation)
from vaws_workspace_update import WorkspaceUpdater, available_sources, git, path_lock, redact, update_lock
from vaws_worktree_setup import configure_target, unpinned_environment

CLIENTS = ("codex", "cursor", "claude", "grok", "kimi")


def native_source_preference(cwd: str, sources: dict) -> str | None:
    actual = Path(cwd).resolve()
    for name, path in sources.items():
        root = Path(path).resolve()
        if name != "workspace" and (actual == root or root in actual.parents):
            return name
    return None


def native_prepared(context: dict, project: Path) -> tuple[Path, dict] | None:
    """Use the explicitly prepared directory, including independent clones."""
    cwd = Path(context["attachment"]["cwd"])
    selected = prepared_workspace(cwd, project)
    if selected is None:
        return None
    return selected, saved_ready(selected)


def prepare_latest(project: Path, source_channel: str = "development", *, sources=None, latest=False) -> tuple[Path, dict, dict]:
    """Select locally by default; contact upstream only for an explicit latest request."""
    waiting = time.monotonic()
    with update_lock(project, wait_seconds=180):
        lock_seconds = time.monotonic()-waiting
        updater = WorkspaceUpdater(project, source_channel=source_channel, source_names=sources)
        if not latest:
            update, prepared = updater.local_prepare()
            return Path(prepared["stage"]), prepared, {**update, "lock_wait_seconds": lock_seconds}
        update = updater.step(apply=True, activate=False)
        if update.get("status") not in {"ready", "current"}:
            previous = updater.state
            if previous.get("phase") in {"ready", "active"} and previous.get("prepared"):
                try:
                    stage = updater.validate_prepared(previous, previous["prepared"])
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                    pass
                else:
                    selected = previous["prepared"]
                    if sources is not None:
                        if not set(sources) <= selected["sources"].keys():
                            raise RuntimeError("cached preparation does not contain the requested sources")
                        selected = {**selected, "sources": {name: selected["sources"][name] for name in sources},
                                    "revisions": {name: selected["revisions"][name] for name in ("workspace", *sources)}}
                    return stage, selected, {
                        "status": "cached", "target": previous["target"],
                        "upstream_check": update, "upstream_checked": True,
                        "lock_wait_seconds": lock_seconds,
                    }
            error = RuntimeError(update.get("detail") or update.get("reason") or "upstream preparation failed")
            error.evidence = update
            raise error
        prepared = updater.state.get("prepared")
        if not prepared:
            prepared = updater.prepare(update, updater.preparation_inputs(update))
            updater.save(**{key: value for key, value in update.items() if key != "status"},
                         prepared=prepared, phase="ready", status="ready")
        # step/prepare has already validated this invocation's completed plan.
        return Path(prepared["stage"]), prepared, {**update, "upstream_checked": True,
                                                  "lock_wait_seconds": lock_seconds}


def selected_result(workspace: Path, receipt: dict, context: dict, *, status: str, evidence: Path,
                    head: str | None = None, **facts) -> dict:
    config = knowledge_config_path(workspace)
    editor = workspace / ".vaws-local/vaws.code-workspace"
    return {"status": status, "workspace": str(workspace), "head": head or git(workspace, "rev-parse", "HEAD"),
            "editor_workspace": str(editor) if editor.is_file() else None,
            "environment": {key: receipt[key] for key in ("key", "python", "receipt")},
            "context_file": context["context_file"], "native_cwd": context["attachment"]["cwd"],
            "knowledge_config": str(config) if config.is_file() else None,
            "evidence": str(evidence), **facts}


def reuse(record: Path) -> dict:
    """Resume a completed selection without shared locks, Git or preparation."""
    from vaws_source_view import recorded_focus
    previous = json.loads(record.read_text(encoding="utf-8"))
    workspace = Path(previous["workspace"])
    if not workspace.is_dir() or not (workspace / ".git").exists():
        raise ValueError(f"selected editing directory is unavailable: {workspace}")
    for name, path in previous.get("sources", {}).items():
        if not (Path(path) / ".git").exists():
            raise ValueError(f"selected source {name} is unavailable: {path}")
    receipt = read_receipt(previous["environment"]["receipt"])
    if receipt["key"] != previous["environment"]["key"]:
        raise ValueError("selected task environment receipt changed")
    recorded_focus(workspace, previous.get("sources", {}), previous)
    return {**previous, "status": "reused"}


def start(client: str, project: Path = ROOT, context_file: str | None = None,
          *, source_channel: str = "development", sources=None, latest=False, preferred=None) -> dict:
    from vaws_coordinator.agent_session import AgentSessions, load_context
    from vaws_source_view import recorded_focus, source_focus

    phase, context, record, workspace = "context", None, None, None
    begun = time.monotonic()
    timings = {}
    try:
        context = load_context(resolve_context_file(context_file))
        if context["attachment"]["client"] != client:
            raise ValueError("--client differs from the existing native attachment")
        project = shared_workspace_root(project.resolve())
        record = task_dir(context["session"]["id"], project) / "start.json"
        phase = "reuse"
        if set(sources or ()) - {"vllm", "vllm-ascend"}:
            raise ValueError("sources must be vllm or vllm-ascend")
        if record.is_file():
            previous = reuse(record)
            return {**previous, "startup_timings": {"total_seconds": time.monotonic()-begun},
                    "selection": "existing_task"}
        phase = "preparation_lock"
        # Only callers for this native task wait for its copy and client wiring.
        # The project lock is confined to preparing the shared immutable stage.
        waiting = time.monotonic()
        with path_lock(record.with_name("start.lock"), wait_seconds=180):
            timings["task_lock_wait_seconds"] = time.monotonic()-waiting
            phase = "reuse"
            if record.is_file():
                return {**reuse(record), "startup_timings": {**timings, "total_seconds": time.monotonic()-begun},
                        "selection": "existing_task"}
            prepared_native = native_prepared(context, project)
            update = {}
            selected_head = None
            if prepared_native:
                workspace, receipt = prepared_native
                preparation = "native"
                sources = prepared_sources(workspace)
                native_record = read_preparation(workspace)
                source_channel = native_record["source_channel"]
                base_focus = recorded_focus(workspace, sources, native_record)
                choice = preferred or native_source_preference(context["attachment"]["cwd"], sources)
                focus = source_focus(workspace, sources, preferred=choice) if choice is not None else base_focus
            else:
                phase = "upstream" if latest else "local_preparation"
                print("VAWS: selecting fixed workspace inputs and required packages", file=sys.stderr, flush=True)
                mark = time.monotonic()
                stage, prepared, update = prepare_latest(project, source_channel, sources=sources, latest=latest)
                timings["preparation_seconds"] = time.monotonic()-mark
                workspace = project.parent / (project.name + "-" + context["session"]["id"])
                if workspace.exists():
                    # An interrupted copy may contain edits made during repair.
                    # Retain it and retry in a fresh sibling without a reset.
                    workspace = workspace.with_name(workspace.name + "-" + uuid.uuid4().hex[:8])
                phase = "workspace_copy"
                print(f"VAWS: creating {workspace}", file=sys.stderr, flush=True)
                mark = time.monotonic()
                copied = create_prepared_workspace(prepared, workspace)
                selected_head = copied["head"]
                timings["copy_seconds"] = time.monotonic()-mark
                timings["repositories"] = copied.get("copy_seconds", {})
                sources = copied["sources"]
                if preferred is None:
                    cwd = Path(context["attachment"]["cwd"]).resolve()
                    # An explicit native business cwd is evidence, unlike a
                    # prompt or another task's recently selected repository.
                    preferred = native_source_preference(str(cwd), available_sources(project) if cwd != project else {})
                focus = source_focus(workspace, sources, preferred=preferred)
                copy_workspace_identity(project, workspace)
                phase = "environment"
                environment = unpinned_environment()
                # The updater prepared this exact committed stage. Do not let
                # the caller's old VAWS_ENV_RECEIPT select the new task runtime.
                receipt = prepared["receipt"]
                mark = time.monotonic()
                configure_target(client, workspace, receipt, environment, owner_project=project)
                select_environment(workspace, receipt)
                write_preparation(workspace, project_root=project,
                                  native_workspace=Path(context["attachment"]["cwd"]), workspace=workspace,
                                  sources=sources, source_channel=source_channel, environment=receipt,
                                  preferred=focus["repository"])
                timings["configuration_seconds"] = time.monotonic()-mark
                preparation = "created"
            phase = "sources"
            store = AgentSessions(Path(context["state_dir"]))
            # Defaults belong to this attachment. Explicit user sources, including
            # an empty map, retain precedence in the coordinator.
            context = store.bind_native_sources(context, sources=sources)
            result = selected_result(workspace, receipt, context, status="ready", evidence=record,
                                     preparation=preparation, update=update, sources=sources,
                                     source_channel=source_channel, head=selected_head, **focus)
            result["startup_timings"] = {**timings, "total_seconds": time.monotonic()-begun}
            write_json(record, result)
            if preparation == "created":
                write_json(project / ".vaws-local/latest-runtime.json",
                           {key: result[key] for key in ("workspace", "environment", "head")})
            return result
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        result = {"status": "failed", "phase": phase, "error": redact(str(exc)),
                  "error_type": type(exc).__name__,
                  "startup_timings": {**timings, "total_seconds": time.monotonic()-begun}}
        if context:
            result["context_file"] = context["context_file"]
        if workspace:
            result["workspace"] = str(workspace)
        if record:
            path = record.with_name("start-error.json")
            write_json(path, {**result, "details": getattr(exc, "evidence", {})})
            result["evidence"] = str(path)
        return result


def main(argv=None) -> int:
    configure_windows_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=CLIENTS, required=True)
    parser.add_argument("--context-file", help="existing native context, when the shell cannot provide it")
    parser.add_argument("--source-channel", choices=("development", "release"), default="development",
                        help="vLLM baseline paired with the selected Ascend commit; existing tasks keep their selection")
    parser.add_argument("--sources", nargs="*", choices=("vllm", "vllm-ascend"),
                        help="select business roots for a new task; existing tasks retain their source selection")
    parser.add_argument("--latest", action="store_true", help="explicitly check upstream for a new task; resumed tasks keep their version")
    parser.add_argument("--repo", choices=("workspace", "vllm", "vllm-ascend"), help="explicit editing repository for a new task")
    args = parser.parse_args(argv)
    setup = workspace_entry(shared_workspace_root(ROOT), announce=False)
    if setup["state"] != "configured":
        first_use = setup["state"] in {"identity_pending", "needs_github_user"}
        reference = FIRST_USE_REFERENCE if first_use else MAINTENANCE_REFERENCE
        next_step = (f"Read {FIRST_USE_REFERENCE} for this repository's one-time initialization. "
                     "Reuse an already supplied personal GitHub username, or ask once." if first_use else
                     setup.get("message") or
                     f"Inspect the reported state and {MAINTENANCE_REFERENCE} for the relevant maintenance command; "
                     "do not restart first-use initialization.")
        print(json.dumps({"status": "needs_setup" if first_use else "failed", "phase": "initialization",
                          "setup": setup, "reference": reference, "next": next_step}, ensure_ascii=False))
        return 1
    ensure_workspace_interpreter(repo_root=ROOT)
    result = start(args.client, ROOT, args.context_file, source_channel=args.source_channel,
                   sources=None if args.sources is None else tuple(args.sources), latest=args.latest, preferred=args.repo)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
