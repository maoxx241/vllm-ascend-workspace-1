"""Resumable first-use setup with explicit choices and no per-task network probe."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time

from vaws_community import POLICY_URL, community_environment, read_choice, write_choice, policy_path, disable_knowledge
from vaws_github import atomic_json, load_github_identity

SCHEMA = "vaws.onboarding.v1"
REFERENCE = ".agents/bootstrap/repo-init/SKILL.md"


def setup_inputs(root: Path) -> str:
    """Invalidate explicit setup on dependency changes, without a network probe."""
    digest = hashlib.sha256()
    for name in ("pyproject.toml", "uv.lock"):
        path = root / name
        digest.update(name.encode())
        digest.update(path.read_bytes() if path.exists() else b"missing")
    return digest.hexdigest()


def record_path(root: Path) -> Path:
    from vaws_local_state import shared_workspace_root
    return shared_workspace_root(root) / ".vaws-local/onboarding.json"


def read_record(root: Path) -> dict | None:
    path = record_path(root)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != SCHEMA or not isinstance(value.get("steps"), dict):
        raise ValueError("Saved onboarding record is invalid; repair it without resetting existing work")
    return value


def status(root: Path, *, detect_auth: bool = False) -> dict:
    record = read_record(root)
    identity = load_github_identity(root)
    choice = read_choice(root)
    state = record.get("state", "pending") if record else "existing" if identity else "needs_choices"
    result = {"state": state, "reference": REFERENCE, "policy_url": POLICY_URL,
              "github_user": (identity or {}).get("login"), "community": choice,
              "choices": (record or {}).get("choices", {}),
              "steps": (record or {}).get("steps", {}), "record": str(record_path(root)),
              "network_checked": False}
    if detect_auth and state != "ready":
        from vaws_github import detect_github_auth
        result["authentication"] = detect_github_auth()
        result["network_checked"] = True
    return result


def run_json(command: list[str], root: Path, environment: dict) -> dict:
    completed = subprocess.run(command, cwd=root, env=environment, text=True, encoding="utf-8",
                               stdout=subprocess.PIPE, stderr=sys.stderr, check=False, timeout=900)
    try:
        value = json.loads(completed.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"Setup command returned no JSON object (exit {completed.returncode})") from exc
    if completed.returncode or not isinstance(value, dict):
        raise RuntimeError(f"Setup command failed (exit {completed.returncode}); inspect its local diagnostic log")
    return value


def configure_knowledge(root: Path, decision: str, login: str, *, receipt: dict | None = None) -> dict:
    if decision == "disabled":
        disable_knowledge(root)
        return {"state": "disabled", "local_reference": True, "owner_prepared": False}
    from vaws_knowledge_service import knowledge_config_path, knowledge_owner_path, run_knowledge_cli, _run_knowledge
    command = ["publishing", "configure", "--config", knowledge_owner_path(root, knowledge_config_path(root)),
               "--consent-file", knowledge_owner_path(root, policy_path(root)), "--github-user", login]
    code, result = (_run_knowledge(root, ["-m", "vaws_knowledge", *command], receipt=receipt) if receipt else
                    run_knowledge_cli(root, command))
    if code:
        raise RuntimeError("Knowledge contribution configuration failed; the recorded choice is retained")
    return result


def configure_reporting(root: Path, receipt: dict, environment: dict) -> dict:
    """The installed diagnostics owner provides platform supervision and reuse."""
    base = (Path(environment.get("LOCALAPPDATA") or Path.home() / "AppData/Local") if os.name == "nt" else
            Path(environment.get("XDG_STATE_HOME") or Path.home() / ".local/state"))
    log_root = Path(environment.get("VAWS_DIAGNOSTICS_ROOT") or base / "vaws/diagnostics")
    state = log_root.parent / "diagnostics-worker"
    save_token = ["--save-token"] if environment.get("GH_TOKEN") or environment.get("GITHUB_TOKEN") else []
    return run_json([receipt["python"], "-m", "vaws_diagnostics.cli", "service", "install",
                     "--root", str(log_root), "--state", str(state), "--python", receipt["python"], *save_token],
                    root, environment)


def initialize(root: Path, *, github_user: str | None = None, fork: bool | None = None,
               star: bool | None = None, community: str | None = None, client: str | None = None,
               github=None, runner=run_json) -> dict:
    from vaws_github import GitHubClient, setup, validate_github_user
    from vaws_local_state import shared_workspace_root
    from vaws_workspace_update import path_lock
    from vaws_diagnostics_adapter import phase, redact

    root = shared_workspace_root(root.resolve())
    begun = time.monotonic()
    with path_lock(root / ".vaws-local/onboarding.lock", wait_seconds=180):
        previous = read_record(root)
        client = client or (previous or {}).get("client") or "all"
        saved = (previous or {}).get("choices", {})
        current_choice = read_choice(root)
        if community == "disabled":
            # Revocation is independent of unanswered first-use questions,
            # GitHub authentication, package installation and the old receipt.
            current_choice = write_choice(root, "disabled")
            disable_knowledge(root)
        choices = {"github_user": github_user or saved.get("github_user") or (load_github_identity(root) or {}).get("login"),
                   "fork": fork if fork is not None else saved.get("fork"),
                   "star": star if star is not None else saved.get("star"),
                   "community": community if community is not None else (current_choice or {}).get("decision", saved.get("community"))}
        if not choices["github_user"] or any(choices[key] is None for key in ("fork", "star", "community")):
            return {**status(root), "state": "choice_updated" if community == "disabled" else "needs_choices", "choices": choices,
                    "setup_state": "needs_choices",
                    "message": "Ask once for missing choices; reuse explicit answers. No fork, star or upload was attempted."}
        if type(choices["fork"]) is not bool or type(choices["star"]) is not bool:
            raise ValueError("fork and star choices must be boolean")
        if choices["community"] not in {"enabled", "disabled"}:
            raise ValueError("community must be enabled or disabled")
        if not isinstance(choices["github_user"], str) or not re.fullmatch(
                r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", choices["github_user"]):
            raise ValueError("GitHub ID must be a personal account login")
        inputs = setup_inputs(root)
        if (previous and previous.get("state") == "ready" and choices == saved
                and previous.get("inputs") == inputs
                and current_choice and current_choice["decision"] == choices["community"]
                and previous.get("community_revision") == current_choice["revision"]
                and all(item.get("state") == "ready" for item in previous["steps"].values())
                and previous.get("client") == client):
            return {**previous, "record": str(record_path(root)), "seconds": time.monotonic()-begun,
                    "reused": True, "native_client_loaded": False}
        steps = dict((previous or {}).get("steps", {}))
        if previous and previous.get("inputs") != inputs:
            for name in ("dependencies", "clients", "knowledge", "reporting"):
                steps.pop(name, None)
        if previous and current_choice and previous.get("community_revision") != current_choice["revision"]:
            for name in ("knowledge", "reporting"):
                steps.pop(name, None)
        if previous and previous.get("client") != client:
            steps.pop("clients", None)
        if previous and choices != saved:
            for field, affected in {"github_user": ("fork", "star", "knowledge"), "fork": ("fork",),
                                    "star": ("star",), "community": ("knowledge", "reporting")}.items():
                if choices[field] != saved.get(field):
                    for name in affected:
                        steps.pop(name, None)
        record = {"schema": SCHEMA, "state": "pending", "choices": choices, "steps": steps,
                  "policy_url": POLICY_URL, "client": client, "inputs": inputs}
        # The consent switch is effective even if a later setup stage fails.
        choice = write_choice(root, choices["community"])
        record["community_revision"] = choice["revision"]
        environment = community_environment(root)
        environment["PYTHONUTF8"] = "1"
        environment.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1")
        atomic_json(record_path(root), record)
        github = github or GitHubClient()

        def step(name, action):
            if steps.get(name, {}).get("state") == "ready":
                return steps[name]["result"]
            started = time.monotonic()
            record["phase"] = name
            atomic_json(record_path(root), record)
            print(f"VAWS initialization: {name}", file=sys.stderr, flush=True)
            with phase(f"initialization.{name}"):
                result = action()
            steps[name] = {"state": "ready", "seconds": time.monotonic()-started, "result": result}
            atomic_json(record_path(root), record)
            return result

        def identity_only():
            # A confirmed label is sufficient for local task ownership. It is
            # never an API credential; each external write authenticates itself.
            login = choices["github_user"]
            saved_identity = load_github_identity(root) or {}
            if saved_identity and saved_identity.get("login", "").casefold() != login.casefold():
                raise ValueError("Confirmed account differs from the saved workspace owner")
            identity = {**saved_identity, "schema": "vaws.github.v1", "login": login,
                        "forks": saved_identity.get("forks", {})}
            atomic_json(root / ".vaws-local/github.json", identity)
            return {"state": "configured", "fork": "declined", "github_user": login}

        try:
            step("fork", lambda: setup(root, choices["github_user"], apply=True, roles=["workspace"], client=github)
                 if choices["fork"] else identity_only())
            dependency = step("dependencies", lambda: runner(
                [sys.executable, str(root / ".agents/scripts/vaws_deps.py"), "sync", "--locked"], root, environment))
            receipt = dependency["receipt"]
            step("clients", lambda: runner([receipt["python"], str(root / ".agents/scripts/vaws_client_setup.py"),
                                             "--client", client, "--project", str(root), "--apply"], root, environment))
        except Exception as exc:
            if getattr(exc, "status", None) in {401, 403}:
                from vaws_diagnostics_adapter import failure
                failure("caller", submission_state="not_submitted")
            record.update(state="pending", error={"type": type(exc).__name__, "message": redact(str(exc))})
            atomic_json(record_path(root), record)
            return {**record, "record": str(record_path(root)), "seconds": time.monotonic()-begun,
                    "next": "Fix the reported stage and rerun vaws_init.py apply; saved choices and completed steps are reused."}
        # Optional community capabilities never turn reference availability into
        # a task gate. Keep failed stages explicit and resumable independently.
        def configure_star():
            if not choices["star"]:
                return {"state": "declined"}
            validate_github_user(github.api("user"), choices["github_user"])
            return github.ensure_star("vllm-ascend-workspace/vllm-ascend-workspace")

        optional = {
            "star": configure_star,
            "knowledge": lambda: configure_knowledge(root, choice["decision"], choices["github_user"], receipt=receipt),
            "reporting": lambda: configure_reporting(root, receipt, environment)
                         if choice["decision"] == "enabled" else {"state": "disabled", "local_logs": True},
        }
        for name, action in optional.items():
            try:
                step(name, action)
            except Exception as exc:
                steps[name] = {"state": "pending", "error": {"type": type(exc).__name__, "message": redact(str(exc))}}
                atomic_json(record_path(root), record)
        record["pending_optional"] = [name for name in optional if steps[name]["state"] != "ready"]
        record["collaboration_state"] = "pending" if any(name in record["pending_optional"] for name in ("knowledge", "reporting")) else "configured"
        record.update(state="ready", phase="complete", completed_at=datetime.now(timezone.utc).isoformat())
        atomic_json(record_path(root), record)
        return {**record, "record": str(record_path(root)), "seconds": time.monotonic()-begun,
                "reused": False,
                "native_client_loaded": False}
