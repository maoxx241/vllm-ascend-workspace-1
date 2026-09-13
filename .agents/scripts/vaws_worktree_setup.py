#!/usr/bin/env python3
"""Prepare a worktree supplied by a native client's creation lifecycle.

Codex and Cursor run this before the new Agent starts. They own the directory
and native session; the normal session hook then attaches it to VAWS. This is
not a command an Agent needs to call, and never runs from SessionStart/resume.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))

from vaws_environment import EnvironmentError, PIN_ENV, MANAGED_PIN_ENV, native_ready, saved_ready, select_environment, _inputs
from vaws_workspace_entry import copy_workspace_identity, workspace_entry, read_preparation, write_preparation
from vaws_workspace_update import (Deferred, WorkspaceUpdater, available_sources, clean_checkout, common_dir,
                                   git, run, update_lock)
from vaws_native_workspace import create_workspace, create_prepared_workspace
from vaws_local_state import shared_workspace_root


def native_paths(client: str, environment: dict, cwd: Path) -> tuple[Path, Path]:
    source_key = "CODEX_SOURCE_TREE_PATH" if client == "codex" else "ROOT_WORKTREE_PATH"
    if not environment.get(source_key):
        raise ValueError(f"{source_key} is missing; this entry belongs to native worktree creation")
    if client == "codex" and not environment.get("CODEX_WORKTREE_PATH"):
        raise ValueError("CODEX_WORKTREE_PATH is missing; the native client must supply its new worktree")
    source = Path(environment[source_key]).expanduser().resolve()
    target = Path(environment.get("CODEX_WORKTREE_PATH", cwd) if client == "codex" else cwd).resolve()
    if source == target or target != cwd.resolve():
        raise ValueError("native setup must run inside its new worktree, separate from the source")
    shared = common_dir(source).resolve()
    if shared != common_dir(target).resolve():
        raise ValueError("native source and worktree do not belong to the same Git repository")
    target_gitdir = Path(git(target, "rev-parse", "--absolute-git-dir")).resolve()
    if target_gitdir == shared or Path(git(target, "rev-parse", "--show-toplevel")).resolve() != target:
        raise ValueError("native setup target must be the root of a linked worktree, not the main checkout")
    return source, target


def unpinned_environment() -> dict:
    environment = dict(os.environ)
    for name in (PIN_ENV, MANAGED_PIN_ENV, "VAWS_CONTEXT_FILE", "VAWS_PARENT_CONTEXT", "VAWS_ATTACH_CONTEXT",
                 "VAWS_RELEASE_LAUNCH", "VAWS_VENV_REEXEC", "VAWS_SKIP_VENV_REEXEC", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH"):
        environment.pop(name, None)
    return environment


def ready_for_target(source: Path, target: Path, environment: dict) -> dict:
    """Reuse matching source inputs, otherwise prepare only the required packages."""
    try:
        receipt = native_ready(source)
        if receipt["input_id"] == _inputs(target)[3]:
            return receipt
    except EnvironmentError:
        pass
    try:
        return native_ready(target)
    except EnvironmentError:
        result = run([getattr(sys, "_base_executable", sys.executable),
                      str(target / ".agents/scripts/vaws_deps.py"), "sync", "--locked"],
                     cwd=target, env=environment, timeout=1800)
        return json.loads(result.stdout)["receipt"]


def configure_target(client: str, target: Path, receipt: dict, environment: dict, *, owner_project: Path | None = None) -> None:
    # The selected revision owns its wiring. No shared editing directory or
    # already-running client's hook/MCP commands are rewritten.
    arguments = [receipt["python"], str(target / ".agents/scripts/vaws_client_setup.py"),
                 "--client", client, "--project", str(target), "--apply"]
    if client == "kimi":
        # One installed Kimi lifecycle adapter routes each native event to its
        # selected environment; a new worktree must not append global hooks.
        arguments += ["--kimi-config", str(target / ".vaws-local/kimi-hooks.toml")]
    if owner_project is not None:
        arguments += ["--owner-project", str(owner_project)]
    run(arguments, cwd=target, env={**environment, PIN_ENV: receipt["receipt"]}, timeout=120)


def default_branch_snapshot(source: Path, original: str) -> dict | None:
    """Recognize the local default-branch tip, not the user's selected ref.

    Codex passes only source/target paths to setup. An explicit selection of
    this exact tip is indistinguishable from the default; the result records
    that boundary. Other commits and named target branches are not eligible.
    """
    branches = set()
    for remote in ("origin", "upstream"):
        reference = git(source, "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD", check=False)
        prefix = f"refs/remotes/{remote}/"
        if reference.startswith(prefix):
            branches.add(reference[len(prefix):])
    if len(branches) != 1:
        return None
    reference = "refs/heads/" + branches.pop()
    if git(source, "rev-parse", "--verify", reference + "^{commit}", check=False) != original:
        return None
    return {"kind": "local_default_branch_snapshot", "ref": reference, "head": original,
            "native_ref_selection": "unavailable"}


def prepare_canonical(source: Path, baseline: dict | None = None, *, source_channel: str = "development",
                      sources=None, latest=False) -> tuple[dict, dict | None]:
    """Use existing preparation without requiring the editing source on main."""
    project = shared_workspace_root(source)
    result = workspace_entry(project)
    if result["state"] != "configured":
        return result, None
    waiting = time.monotonic()
    with update_lock(project, wait_seconds=180):
        lock_seconds = time.monotonic()-waiting
        updater = WorkspaceUpdater(project, source_root=source, source_channel=source_channel, source_names=sources)
        if not latest:
            result, prepared = updater.local_prepare()
            return {**result, "lock_wait_seconds": lock_seconds}, prepared
        result = updater.step(apply=True, activate=False)
        if result.get("status") not in {"ready", "current"}:
            return result, None
        if baseline is not None and "refs/heads/" + result["branch"] != baseline["ref"]:
            return {"status": "kept", "reason": "default_branch_changed"}, None
        if updater.state.get("phase") not in {"ready", "active"}:
            return result, None
        # step has already validated the completed preparation in this call.
        return {**result, "upstream_checked": True, "lock_wait_seconds": lock_seconds}, updater.state["prepared"]


def source_task_focus(source: Path, context_file: str) -> dict:
    """Read a caller-supplied parent task; never infer one from a directory."""
    from vaws_coordinator.agent_session import load_context
    from vaws_mcp_runtime import selection

    if not isinstance(context_file, (str, Path)) or not str(context_file).strip():
        raise ValueError("source task context must be supplied explicitly")
    context = load_context(context_file, allow_native_context=False)
    selected = selection(source, context)
    if selected.workspace.resolve() != source.resolve():
        raise ValueError("source task context belongs to another editing workspace")
    return {"repository": selected.repository or "workspace", "cwd": str(selected.cwd or source)}


def prepare_worktree(client: str, source: Path, target: Path, *, preserve_source: bool = False,
                     source_channel: str = "development", sources=None, latest=False, preferred=None,
                     source_context_file: str | None = None) -> dict:
    """Prepare a complete independent bundle, outside an existing native worktree.

    Clients that accept a returned cwd can request a missing target directly.
    Clients that already created a linked worktree receive its external bundle
    path; their original checkout remains unchanged and stores only a reference.
    """
    from vaws_local_owner import windows_mounted_workspace
    from vaws_source_view import recorded_focus
    started = time.monotonic()
    timings = {}
    requested_sources = sources
    source, target = source.resolve(), target.resolve()
    if source_channel not in {"development", "release"}:
        raise ValueError("source_channel must be development or release")
    if source_context_file is not None and not preserve_source:
        raise ValueError("source task context is only used when preserving a fork source")
    if windows_mounted_workspace(target):
        raise ValueError("run native worktree setup with the Windows owner for this mounted workspace")
    if source == target:
        raise ValueError("native setup needs a separate target")
    environment = unpinned_environment()
    existing = read_preparation(target)
    if existing is not None:
        actual = Path(existing["workspace"])
        for path in existing["sources"].values():
            repository = Path(path)
            if not (repository / ".git").is_dir() or (repository / ".git/objects/info/alternates").exists():
                raise ValueError(f"prepared repository is missing or is not independent: {repository}")
        receipt = saved_ready(actual)
        focus = recorded_focus(actual, existing["sources"], existing)
        return {**existing, **focus, "status": "reused", "environment": receipt["key"],
                "native_cwd_changed": False, "startup_timings": {"total_seconds": time.monotonic()-started}}
    source_record = read_preparation(source)
    if source_record is not None:
        source = Path(source_record["workspace"])
        if preserve_source:
            source_channel = source_record["source_channel"]
            focus = recorded_focus(source, source_record["sources"], source_record)
            if preferred is None and source_context_file is None:
                preferred = focus["repository"]
    if source_context_file is not None:
        focus = source_task_focus(source, source_context_file)
        # An explicit override applies to this new fork only. Always validate
        # the supplied parent, even when the override chooses another repo.
        if preferred is None:
            preferred = focus["repository"]
    project = shared_workspace_root(source)
    supplied = target.exists()
    if supplied:
        if not (target / ".git").is_file():
            raise ValueError(f"workspace preparation is incomplete at {target}; preserved this directory; choose a new target")
        if (Path(git(target, "rev-parse", "--show-toplevel")).resolve() != target
                or Path(git(target, "rev-parse", "--absolute-git-dir")).resolve() == common_dir(target)):
            raise ValueError("existing native target must be a linked Git worktree root")
        bundle = project.parent / f"{project.name}-vaws-{uuid.uuid4().hex}"
    else:
        bundle = target
    if target in bundle.parents or source == bundle or source in bundle.parents:
        raise ValueError("task bundle must be outside the source and native cleanup directories")
    editing = target if supplied and not preserve_source else source
    original = git(editing, "rev-parse", "HEAD")
    branch = git(editing, "symbolic-ref", "--quiet", "--short", "HEAD", check=False) or None
    result = {"status": "kept", "reason": "fork_source" if preserve_source else "explicit_source"}
    baseline = None
    prepared = None
    chosen = editing
    selection = editing / ".vaws-local/environment-selection" / f"{sys.platform}.json"
    if not preserve_source and (not supplied or not selection.is_file()):
        try:
            if supplied:
                clean_checkout(editing, branch=branch)
                for path in available_sources(editing).values():
                    child = Path(path)
                    child_branch = git(child, "symbolic-ref", "--quiet", "--short", "HEAD", check=False) or None
                    clean_checkout(child, branch=child_branch)
            if supplied and client == "codex" and branch is None:
                baseline = default_branch_snapshot(source, original)
            if not supplied or baseline is not None or original == git(source, "rev-parse", "HEAD"):
                if baseline is None:
                    baseline = {"kind": "source_head_snapshot", "head": original, "native_ref_selection": "unavailable"}
                check_baseline = baseline if baseline["kind"] == "local_default_branch_snapshot" else None
                mark = time.monotonic()
                options = {"source_channel": source_channel}
                if requested_sources is not None:
                    options["sources"] = requested_sources
                if latest:
                    options["latest"] = True
                result, prepared = prepare_canonical(source, check_baseline, **options)
                timings["preparation_seconds"] = time.monotonic()-mark
                if prepared is not None:
                    if supplied:
                        clean_checkout(editing, branch=branch, expected={original})
                    chosen = Path(prepared["stage"])
        except Deferred as exc:
            # Nothing in the supplied checkout has been changed. Keeping it is
            # safe only before copying; failures after copying propagate.
            result = {"status": "kept", "reason": exc.reason}
            prepared = None
            chosen = editing
    if baseline is not None:
        result = {**result, "baseline": baseline}
    mark = time.monotonic()
    if prepared is not None:
        copied = create_prepared_workspace(prepared, bundle)
        if supplied and branch:
            # The native branch is a user-visible choice. Only this fresh
            # independent clone binds that name to the adopted canonical HEAD.
            git(bundle, "switch", "-C", branch)
    else:
        sources = available_sources(chosen)
        if supplied and read_preparation(chosen) is None:
            # Native Git worktrees do not populate ignored business repositories.
            sources = {**available_sources(source), **sources}
        if requested_sources is not None:
            missing = set(requested_sources)-sources.keys()
            if missing:
                raise ValueError(f"selected editing sources are unavailable: {sorted(missing)}")
            sources = {name: sources[name] for name in requested_sources}
        copied = create_workspace(chosen, bundle, sources=sources)
    timings["copy_seconds"] = time.monotonic()-mark
    timings["repositories"] = copied.get("copy_seconds", {})
    for relative in (".claude/settings.local.json", ".mcp.json"):
        original_settings, copied_settings = source / relative, bundle / relative
        if original_settings.is_file() and not copied_settings.exists():
            copied_settings.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original_settings, copied_settings)
    identity = {}
    try:
        copy_workspace_identity(source, bundle)
    except (OSError, ValueError, RuntimeError) as exc:
        identity = {"status": "unavailable", "error": str(exc)}
    inherited = None
    if preserve_source or (supplied and selection.is_file()):
        try:
            inherited = saved_ready(editing)
        except EnvironmentError:
            pass
    mark = time.monotonic()
    receipt = inherited or (prepared["receipt"] if prepared is not None else ready_for_target(source, bundle, environment))
    configure_target(client, bundle, receipt, environment, owner_project=project)
    select_environment(bundle, receipt)
    timings["configuration_seconds"] = time.monotonic()-mark
    facts = {"head": copied["head"], "environment": receipt["key"], "source": str(chosen),
             "update": result, "native_cwd_changed": False,
             "startup_timings": {**timings, "total_seconds": time.monotonic()-started},
             **({"identity": identity} if identity else {})}
    record = write_preparation(bundle, project_root=project, native_workspace=target, workspace=bundle,
                               sources=copied["sources"], source_channel=source_channel, preferred=preferred, **facts)
    if supplied:
        write_preparation(target, project_root=project, native_workspace=target, workspace=bundle,
                          sources=copied["sources"], source_channel=source_channel, preferred=record["repository"], **facts)
    return {**record, "status": "ready"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "cursor"), required=True)
    parser.add_argument("--latest", action="store_true", help="check upstream for a new workspace explicitly")
    parser.add_argument("--sources", nargs="*", choices=("vllm", "vllm-ascend"))
    parser.add_argument("--repo", choices=("workspace", "vllm", "vllm-ascend"), help="explicit editing repository for a new workspace")
    parser.add_argument("--source-context-file", help="explicit parent task context for a source-preserving fork")
    args = parser.parse_args(argv)
    # Native setup starts before session pins exist; inherited parent pins
    # must not choose this new directory's dependencies.
    os.environ.pop(PIN_ENV, None)
    os.environ.pop(MANAGED_PIN_ENV, None)
    try:
        source, target = native_paths(args.client, os.environ, Path.cwd())
        result = prepare_worktree(args.client, source, target, latest=args.latest,
                                  sources=None if args.sources is None else tuple(args.sources), preferred=args.repo,
                                  preserve_source=args.source_context_file is not None,
                                  source_context_file=args.source_context_file)
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        result = {"status": "failed", "phase": "native_worktree_setup", "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
