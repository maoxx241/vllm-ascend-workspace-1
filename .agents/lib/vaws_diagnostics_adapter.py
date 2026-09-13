"""Consumer observation, available before the selected runtime is importable.

The diagnostics package owns storage, levels, redaction and support export.
This adapter owns only consumer call boundaries. Missing diagnostics never
installs packages, changes business results or writes to protocol stdout.
"""
from __future__ import annotations

import atexit
import argparse
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from datetime import datetime, timezone
import functools
import inspect
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import uuid

_active = ContextVar("vaws_workspace_observation", default=None)
_entry = None
_module = None
_loaded = False
_warned = False
_root = None
_process_instance = uuid.uuid4().hex
_recorder = None
_recorder_key = None
_recorder_lock = threading.Lock()


def _after_fork_child():
    global _recorder, _recorder_key, _recorder_lock, _entry, _process_instance
    _recorder = _recorder_key = None
    _recorder_lock = threading.Lock()
    _process_instance = uuid.uuid4().hex
    _active.set(None)
    if _entry is not None:
        # The parent's registered atexit callback is inherited too.
        _entry.done = True
        if not _entry.quiet and sys.excepthook == _entry.excepthook:
            sys.excepthook = _entry.original_hook
    _entry = None


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork_child)


def _configured(api):
    global _recorder, _recorder_key
    root = os.environ.get("VAWS_DIAGNOSTICS_ROOT") or _root
    key = (id(api), root, os.environ.get("VAWS_LOG_LEVEL", "INFO"))
    with _recorder_lock:
        if _recorder_key != key:
            _recorder = api.configure("vaws-workspace", root=root)
            _recorder_key = key
        return _recorder


def _warn(category):
    global _warned
    if _warned:
        return
    _warned = True
    try:
        sys.stderr.write(json.dumps({"level": "WARNING", "event": "diagnostics.unavailable",
                                     "component": "workspace", "category": category}) + "\n")
        sys.stderr.flush()
    except (OSError, ValueError, AttributeError):
        pass


def _api():
    global _module, _loaded
    if not _loaded:
        _loaded = True
        try:
            import vaws_diagnostics
            _module = vaws_diagnostics
        except Exception:
            _warn("package_unavailable")
    return _module


def redact(value):
    """Never fall back to printing arbitrary unredacted exception/argument text."""
    api = _api()
    if api is not None:
        try:
            return api.redact_text(str(value))
        except Exception:
            _warn("redaction_failed")
    return "[diagnostic text unavailable]"


def _fallback_failure(observation, error_type, category):
    """One schema-compatible, static-only bootstrap error when core is absent."""
    root = os.environ.get("VAWS_DIAGNOSTICS_ROOT")
    if root:
        base = Path(root).expanduser()
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "vaws/diagnostics"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "vaws/diagnostics"
    operation_id = observation.fallback_id
    payload = {"schema": 1, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
               "monotonic_ns": time.monotonic_ns(), "pid": os.getpid(),
               "process_instance_id": _process_instance, "component": "vaws-workspace",
               "package_version": "unavailable", "severity": "ERROR", "event": "operation.end",
               "operation_id": operation_id, "trace_id": observation.fallback_trace,
               "parent_operation_id": None, "operation": "bootstrap", "status": "error",
               "started_at": observation.started_at, "duration_ms": observation.duration_ms,
               "attributes": {"error_type": error_type if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,79}", error_type) else "Error",
                              "category": category, "logging_failed": True}}
    try:
        from vaws_community import read_policy_file
        policy_file = os.environ.get("VAWS_COMMUNITY_POLICY", "")
        policy = Path(policy_file)
        if policy.is_absolute() and not policy_file.startswith(("\\\\", "//")) and len(policy_file) <= 4096:
            choice = read_policy_file(policy)
            if choice and choice["decision"] == "enabled":
                payload["community"] = {"policy_file": str(policy), "workspace_id": choice["workspace_id"],
                                        "revision": choice["revision"]}
    except Exception:
        pass  # Local evidence remains available; no consent is inferred.
    reference = None
    try:
        folder = base / "events/vaws-workspace"
        if any(parent.is_symlink() for parent in (folder, *folder.parents)):
            raise OSError("unsafe diagnostic root")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{os.getpid()}-{operation_id}.jsonl"
        encoded = (json.dumps(payload, ensure_ascii=True) + "\n").encode("utf-8")
        if len(encoded) <= 16384:
            with path.open("xb") as stream:
                stream.write(encoded)
            reference = str(path)
    except OSError:
        pass
    try:
        sys.stderr.write(json.dumps({"level": "ERROR", "event": "bootstrap.failed", "error_type": payload["attributes"]["error_type"],
                                     "record_ref": reference, "operation_id": operation_id}) + "\n")
    except (OSError, ValueError):
        pass


class Observation:
    def __init__(self, name, attributes=None, *, parent=None):
        self.name, self.attributes, self.parent = name, attributes or {}, parent
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.started = time.monotonic_ns()
        self.finished_at = None
        self.duration_ms = None
        self.status = "running"
        self.scope = self.owner = None
        self.token = None
        self.fallback_id = uuid.uuid4().hex
        self.fallback_trace = parent.fallback_trace if parent is not None else self.fallback_id

    def __enter__(self):
        api = _api()
        if api is not None:
            try:
                if self.parent is not None and self.parent.owner is not None:
                    self.scope = self.parent.owner.phase(self.name, **self.attributes)
                else:
                    recorder = _configured(api)
                    self.scope = recorder.operation(self.name, **self.attributes)
                self.owner = self.scope.__enter__()
            except Exception:
                self.scope = self.owner = None
                _warn("observer_start_failed")
        self.token = _active.set(self)
        return self

    def event(self, level, event, **attributes):
        if self.owner is not None:
            try:
                self.owner.event(level, event, **attributes)
            except Exception:
                _warn("observer_event_failed")

    def fail(self, category, **attributes):
        self.status = "failed"
        if self.owner is not None:
            try:
                self.owner.fail(category, **attributes)
            except Exception:
                _warn("observer_failure_failed")

    def summary(self):
        facts = {"operation": self.name, "status": self.status,
                 "started_at": self.started_at, "finished_at": self.finished_at,
                 "duration_ms": self.duration_ms if self.duration_ms is not None else
                    (time.monotonic_ns() - self.started) / 1_000_000,
                 "record_ref": None, "logging_failed": self.owner is None}
        if self.owner is not None:
            try:
                facts.update(self.owner.summary())
            except Exception:
                _warn("observer_summary_failed")
        return facts

    def __exit__(self, kind, error, traceback):
        self.duration_ms = (time.monotonic_ns() - self.started) / 1_000_000
        self.finished_at = datetime.now(timezone.utc).isoformat()
        if isinstance(error, SystemExit) and error.code in (None, 0):
            kind, error, traceback = None, None, None
        if kind is not None:
            self.status = "cancelled" if kind.__name__ in {"CancelledError", "KeyboardInterrupt", "GeneratorExit"} else "failed"
        elif self.status == "running":
            self.status = "success"
        try:
            if self.scope is not None:
                self.scope.__exit__(kind, error, traceback)
        except Exception:
            _warn("observer_end_failed")
        finally:
            if self.token is not None:
                _active.reset(self.token)
        if self.owner is None and self.parent is None and self.status == "failed":
            _fallback_failure(self, kind.__name__ if kind is not None else "OperationError", "bootstrap_unavailable")
        return False


def operation(name, **attributes):
    return Observation(name, attributes)


def phase(name, **attributes):
    return Observation(name, attributes, parent=_active.get())


def event(level, name, **attributes):
    active = _active.get()
    if active is not None:
        active.event(level, name, **attributes)


def failure(category, **attributes):
    active = _active.get()
    if active is not None:
        active.fail(category, **attributes)


def measured(name):
    """Time shared boundaries without serializing their arguments or return data."""
    def decorate(fn):
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def asynchronous(*args, **kwargs):
                if _entry is not None and _entry.quiet:
                    return await fn(*args, **kwargs)
                try:
                    with phase(name):
                        return await fn(*args, **kwargs)
                except BaseException:
                    _early_exit()
                    raise
            return asynchronous
        @functools.wraps(fn)
        def synchronous(*args, **kwargs):
            if _entry is not None and _entry.quiet:
                return fn(*args, **kwargs)
            try:
                with phase(name):
                    return fn(*args, **kwargs)
            except BaseException:
                _early_exit()
                raise
        return synchronous
    return decorate


def _early_exit():
    # Interpreter selection may deliberately exit before main is defined. Wait
    # until its outermost measured scope unwinds before closing the entry.
    if (_entry is not None and not _entry.main_started
            and _active.get() is _entry.observation):
        error = sys.exc_info()[1]
        code = error.code if isinstance(error, SystemExit) else 1
        _entry.finish(code if isinstance(code, int) else (1 if code else 0), sys.exc_info())


def wrap_context(fn):
    context = copy_context()
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        return context.copy().run(fn, *args, **kwargs)
    return wrapped


def context_environment(environment):
    result = dict(environment)
    api = _api()
    if api is not None:
        try:
            context = api.current_context()
            if context:
                result["VAWS_DIAGNOSTICS_CONTEXT"] = json.dumps(context, separators=(",", ":"))
        except Exception:
            _warn("context_unavailable")
    return result


def context_metadata(metadata=None):
    result = dict(metadata or {})
    api = _api()
    if api is not None:
        try:
            result["vaws_diagnostics"] = api.current_context()
        except Exception:
            _warn("context_unavailable")
    return result


@contextmanager
def community_context(root):
    """Bind a configured gateway's workspace without changing process-global env."""
    scope = None
    api = _api()
    try:
        if api is not None and hasattr(api, "bind_community_policy"):
            from vaws_community import local_policy_path
            scope = api.bind_community_policy(local_policy_path(root))
            scope.__enter__()
    except Exception:
        scope = None
        _warn("community_scope_unavailable")
    try:
        yield
    finally:
        if scope is not None:
            scope.__exit__(None, None, None)


@contextmanager
def request_context(metadata=None):
    """A persistent server gets a distinct trace per call unless one is supplied."""
    scope = None
    api = _api()
    if api is not None:
        try:
            context = metadata.get("vaws_diagnostics") if isinstance(metadata, dict) else None
            scope = api.bind_context(context)
            scope.__enter__()
        except Exception:
            scope = None
            _warn("request_context_unavailable")
    try:
        yield
    finally:
        if scope is not None:
            try:
                scope.__exit__(None, None, None)
            except Exception:
                _warn("request_context_restore_failed")


@contextmanager
def captured_stderr(observation):
    """Drain a real child stderr fd with bounded buffering into the owner sink.

    No diagnostic file is a prerequisite for process launch. The reader keeps
    draining even when logging fails; an unterminated line cannot grow memory.
    """
    try:
        reader, writer = os.pipe()
    except OSError:
        observation.event("WARNING", "process.stderr_pipe_unavailable")
        yield sys.stderr
        return
    output = os.fdopen(writer, "w", encoding="utf-8", buffering=1)
    def drain():
        pending, length, discarded = b"", 0, False
        def emit_line():
            if discarded:
                observation.event("WARNING", "process.stderr_line_omitted", bytes=length, truncated=True)
            elif pending:
                observation.event("INFO", "process.stderr", preview=pending.decode("utf-8", "replace"), bytes=length)
        try:
            while True:
                block = os.read(reader, 4096)
                if not block:
                    break
                parts = block.split(b"\n")
                for index, part in enumerate(parts):
                    length += len(part)
                    if length > 8192:
                        pending, discarded = b"", True
                    elif not discarded:
                        pending += part
                    if index < len(parts) - 1:
                        emit_line()
                        pending, length, discarded = b"", 0, False
            if pending or discarded:
                observation.event("WARNING", "process.stderr_line_omitted", bytes=length, incomplete=True)
        except OSError:
            observation.event("WARNING", "process.stderr_unavailable")
        finally:
            os.close(reader)
    worker = threading.Thread(target=wrap_context(drain), name="vaws-stderr", daemon=True)
    worker.start()
    try:
        yield output
    finally:
        try:
            output.close()
        except OSError:
            observation.event("WARNING", "process.stderr_close_failed")
        worker.join(timeout=1)
        if worker.is_alive():
            observation.event("WARNING", "process.stderr_not_drained")


@contextmanager
def captured_process_output(name):
    """CLI-only fd capture; its own process drains until work and children exit.

    Never use this process-wide redirection in a concurrent MCP server.
    """
    with operation(name) as observation:
        api = _api()
        scope = None
        try:
            if api is not None and observation.owner is not None:
                scope = api.capture_output(observation.owner)
                scope.__enter__()
        except Exception:
            scope = None
            observation.event("WARNING", "process.output_capture_unavailable")
        try:
            yield
        finally:
            if scope is not None:
                try:
                    scope.__exit__(*sys.exc_info())
                except Exception:
                    observation.event("WARNING", "process.output_restore_failed")


def attempt_facts():
    active = _entry.observation if _entry is not None else _active.get()
    if active is None:
        return {"started_at": None, "duration_ms": None}
    summary = active.summary()
    return {"started_at": summary.get("started_at", active.started_at),
            "duration_ms": int(summary.get("duration_ms") or 0)}


def redact_arguments(arguments):
    result, hidden = [], False
    names = {"password", "passwd", "token", "secret", "api-key", "apikey", "access-key", "authorization", "credential"}
    for value in arguments:
        value = str(value)
        if hidden:
            result.append("[redacted]")
            hidden = False
            continue
        option, equal, tail = value.partition("=")
        sensitive = option.lstrip("-").lower().replace("_", "-") in names
        result.append(option + "=[redacted]" if sensitive and equal else redact(value))
        hidden = sensitive and not equal
    return result


def report_failure(category, error, **attributes):
    try:
        message = str(error)
    except Exception:
        message = "unprintable exception"
    active = _active.get()
    if active is not None:
        active.event("WARNING", category, error_type=type(error).__name__, error=message, **attributes)
    else:
        with operation(category) as observation:
            observation.event("WARNING", category, error_type=type(error).__name__, error=message, **attributes)


class Entry:
    def __init__(self, name, *, quiet=False):
        self.quiet = quiet
        self.observation = None if quiet else operation(name)
        self.done = False
        self.main_started = False
        if self.observation is not None:
            self.observation.__enter__()
            exported = context_environment(os.environ)
            if "VAWS_DIAGNOSTICS_CONTEXT" in exported:
                os.environ["VAWS_DIAGNOSTICS_CONTEXT"] = exported["VAWS_DIAGNOSTICS_CONTEXT"]
            self.original_hook = sys.excepthook
            sys.excepthook = self.excepthook
            original_error = argparse.ArgumentParser.error
            def parser_error(parser, message):
                self.observation.fail("caller", submission_state="not_submitted")
                # argparse formats rejected values in stderr. Preserve usage and
                # exit behavior, while preventing those values leaking to logs.
                return original_error(parser, redact(message))
            argparse.ArgumentParser.error = parser_error
            atexit.register(self.unfinished)

    def finish(self, code=0, exc_info=(None, None, None)):
        if self.done or self.observation is None:
            return
        self.done = True
        cancelled = exc_info[0] is not None and exc_info[0].__name__ in {"CancelledError", "KeyboardInterrupt", "GeneratorExit"}
        if code and not cancelled and self.observation.status != "failed":
            self.observation.fail("tool", returncode=code)
        self.observation.event("INFO", "process.result", returncode=code)
        self.observation.__exit__(*exc_info)

    def run(self, function, *args, **kwargs):
        self.main_started = True
        try:
            with phase("entry.main") if not self.quiet else _quiet_scope():
                result = function(*args, **kwargs)
        except SystemExit as exc:
            self.finish(exc.code if isinstance(exc.code, int) else (1 if exc.code else 0), sys.exc_info())
            raise
        except BaseException:
            self.finish(130 if isinstance(sys.exc_info()[1], KeyboardInterrupt) else 1, sys.exc_info())
            raise
        self.finish(result if isinstance(result, int) else 0)
        return result

    def excepthook(self, kind, error, traceback):
        self.finish(1, (kind, error, traceback))
        if self.original_hook is not sys.__excepthook__:
            # A host may have installed Sentry or another exception integration.
            # Observation adds evidence without replacing that integration.
            self.original_hook(kind, error, traceback)
            return
        try:
            sys.stderr.write(json.dumps({"level": "ERROR", "event": "entry.failed", "error_type": kind.__name__,
                                         "message": redact(str(error))[:1200],
                                         "diagnostics": self.observation.summary()}) + "\n")
        except (OSError, ValueError):
            pass

    def unfinished(self):
        if not self.done:
            self.observation.fail("entry_incomplete", submission_state="unknown")
            self.finish()


@contextmanager
def _quiet_scope():
    yield


def bootstrap(entry_file):
    global _entry
    source = Path(entry_file).absolute()
    try:
        agent_root = next((parent for parent in source.parents if parent.name == ".agents"), None)
        if agent_root is not None:
            from vaws_community import local_policy_path
            os.environ["VAWS_COMMUNITY_POLICY"] = str(local_policy_path(agent_root.parent))
    except Exception:
        # An unreadable policy must not inherit another project's upload choice.
        os.environ.pop("VAWS_COMMUNITY_POLICY", None)
    quiet = False
    for value in sys.argv[1:]:
        if value in {"--", "--serve-args", "--bench-args", "--extra-serve-args"}:
            break
        if value in ("--help", "-h"):
            quiet = True
            break
    _entry = Entry(source.stem, quiet=quiet)
    return _entry
