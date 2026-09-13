"""Route a provider call to the immutable environment selected by its task.

This adapter owns stdio connections, not task execution or knowledge behavior.
Native identity selects a prepared receipt; existing task receipts never follow
the latest catalog. Backend stderr and selected inputs remain inspectable.
"""
from __future__ import annotations

import asyncio
import copy
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys

from vaws_environment import read_receipt, saved_ready, PIN_ENV, capability_receipt
from vaws_local_state import prepared_workspace, shared_workspace_root
from vaws_session_state import task_dir


@dataclass(frozen=True)
class Selection:
    workspace: Path
    receipt: str
    python: str
    key: str
    context_file: str = ""
    cwd: Path | None = None
    repository: str | None = None


def caller_context(arguments: dict, metadata: dict | None, *, state_dir: str = "") -> dict | None:
    supplied = arguments.get("context_file")
    metadata = metadata or {}
    if not supplied and not any(key in metadata for key in ("x-codex-turn-metadata", "kimi_code/session_id")):
        return None
    from vaws_coordinator.agent_session import AgentSessions, load_context

    context = None
    if "x-codex-turn-metadata" in metadata:
        store = AgentSessions(Path(state_dir) if state_dir else None)
        turn = metadata["x-codex-turn-metadata"]
        native = turn.get("thread_id") if isinstance(turn, dict) else None
        if not isinstance(native, str) or not native:
            raise ValueError("native Codex request has no thread_id")
        context = store.native_context("codex", native)
    elif "kimi_code/session_id" in metadata:
        store = AgentSessions(Path(state_dir) if state_dir else None)
        native = metadata["kimi_code/session_id"]
        agent = metadata.get("kimi_code/agent_id", "")
        if not isinstance(native, str) or not native or not isinstance(agent, str):
            raise ValueError("native Kimi request has no session identity")
        context = store.native_context("kimi", native, "" if agent == "main" else agent)
    if context is not None:
        if supplied and str(supplied) != context["context_file"]:
            raise ValueError("context_file differs from the native caller")
        return context
    return load_context(supplied, allow_native_context=False) if supplied else None


def selection(root: Path, context: dict | None = None, *, catalog: bool = False,
              require_prepared: bool = True) -> Selection:
    focus = {}
    if context is None and not catalog:
        # Direct capabilities use their configured workspace, without task or
        # catalog discovery. No Git process is needed to read this selection.
        receipt = saved_ready(root)
        return Selection(root, receipt["receipt"], receipt["python"], receipt["key"])
    shared = shared_workspace_root(root)
    path = (task_dir(context["session"]["id"], shared) / "start.json" if context else
            shared / ".vaws-local/latest-runtime.json")
    if (context or catalog) and path.is_file():
        result = json.loads(path.read_text(encoding="utf-8"))
        focus = result
        target = Path(result["workspace"]).resolve(strict=True)
        receipt = read_receipt(result["environment"]["receipt"])
    else:
        # No prepared task record is needed for native worktrees. Its actual
        # attachment already names the directory prepared before the Agent.
        target = Path(context["attachment"]["cwd"]) if context else root
        target = target.resolve(strict=True)
        if context:
            prepared = prepared_workspace(target, root, owner=shared)
            if prepared is not None:
                target = prepared.resolve(strict=True)
                from vaws_local_state import read_preparation
                focus = read_preparation(target) or {}
            else:
                from vaws_workspace_update import common_dir, git, repository_root
                shared_git = common_dir(root)
                target = repository_root(target)
                actual_git = Path(git(target, "rev-parse", "--absolute-git-dir")).resolve()
                selected_file = target / ".vaws-local/environment-selection" / f"{sys.platform}.json"
                if (common_dir(target) != shared_git or not selected_file.is_file()
                        or (require_prepared and actual_git == shared_git)):
                    raise ValueError("This new task has no prepared workspace. Run the project vaws_start.py entry once, then reuse its context.")
        receipt = saved_ready(target)
    from vaws_source_view import recorded_focus
    editing = recorded_focus(target, focus.get("sources", {}), focus)
    return Selection(target, receipt["receipt"], receipt["python"], receipt["key"],
                     context["context_file"] if context else "",
                     Path(editing["cwd"]), editing["repository"])


def provider_command(kind: str, selected: Selection, environment: dict) -> tuple[list[str], dict]:
    from vaws_coordinator_launch import coordinator_environment
    from vaws_knowledge_service import knowledge_server_env

    modules = {"task": ["-m", "vaws_coordinator", "task-server"],
               "remote": ["-m", "remote_dev.mcp.server"],
               "knowledge": ["-m", "vaws_knowledge.server.mcp_server"]}
    owner = capability_receipt(read_receipt(selected.receipt), kind)
    executable = owner["python"]
    env = dict(environment)
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "VAWS_MANAGED_ENV_RECEIPT",
                "VAWS_CONTEXT_FILE", "VAWS_PARENT_CONTEXT", "VAWS_ATTACH_CONTEXT"):
        env.pop(key, None)
    env[PIN_ENV] = selected.receipt
    env["VIRTUAL_ENV"] = owner["root"]
    env["PATH"] = str(Path(executable).parent) + os.pathsep + env.get("PATH", "")
    if kind == "task":
        env = coordinator_environment(env, repo_root=selected.workspace)
    elif kind == "remote":
        env.setdefault("REMOTE_DEV_DEFAULT_USER", "root")
        env["REMOTE_DEV_STATE_DIR"] = str(selected.workspace / ".vaws-local/remote-dev-state")
    elif kind == "knowledge":
        # A user MCP entry may have inherited its mother checkout's config.
        # Target settings must win; model credentials/explicit backend settings
        # are unrelated and remain in the environment.
        for key in ("VAWS_KNOWLEDGE_CONFIG", "VAWS_KNOWLEDGE_PROJECT_ROOTS",
                    "VAWS_KNOWLEDGE_CANDIDATE_ROOT", "VAWS_KNOWLEDGE_STATE"):
            env.pop(key, None)
        env.update(knowledge_server_env(selected.workspace))
    else:
        raise ValueError(f"unknown provider: {kind}")
    return [executable, *modules[kind]], env


class Backend:
    """One task environment connection, owned and closed by one async worker."""

    def __init__(self, kind: str, selected: Selection, root: Path, environment: dict):
        self.kind, self.selected = kind, selected
        self.command, self.environment = provider_command(kind, selected, environment)
        digest = hashlib.sha256(str(selected.workspace).encode()).hexdigest()[:12]
        self.stderr = shared_workspace_root(root) / ".vaws-local/mcp/providers" / f"{kind}-{selected.key[:12]}-{digest}.log"
        self.closed = asyncio.Event()
        self.requests = set()
        self.catalog = None
        self.catalog_request = None
        self.ready = asyncio.get_running_loop().create_future()
        self.worker = asyncio.create_task(self.run())

    async def run(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp import types
        import anyio

        class CancellableSession(ClientSession):
            async def _receive_loop(session):
                try:
                    await super()._receive_loop()
                finally:
                    # EOF is a definite dead transport, including an idle child
                    # exit. Let its owner close it; never replay pending calls.
                    self.closed.set()

            async def send_request(self, request, result_type, *args, **kwargs):
                # MCP SDK 1.30 assigns this ID before its first await, but does
                # not send notifications/cancelled when its caller cancels.
                request_id = self._request_id
                try:
                    return await super().send_request(request, result_type, *args, **kwargs)
                except asyncio.CancelledError:
                    with anyio.move_on_after(1, shield=True):
                        with suppress(Exception):
                            await self.send_notification(types.ClientNotification(types.CancelledNotification(
                                method="notifications/cancelled", params=types.CancelledNotificationParams(
                                    requestId=request_id, reason="native caller cancelled"))))
                    raise

        try:
            self.stderr.parent.mkdir(parents=True, exist_ok=True)
            with self.stderr.open("a", encoding="utf-8") as log:
                facts = {"provider": self.kind, "workspace": str(self.selected.workspace),
                         "environment": self.selected.key, "python": self.command[0],
                         "receipt": self.selected.receipt, "stderr": str(self.stderr)}
                log.write(json.dumps({"vaws_provider_start": facts}) + "\n")
                log.flush()
                print(json.dumps({"vaws_provider_start": facts}), file=sys.stderr, flush=True)
                parameters = StdioServerParameters(command=self.command[0], args=self.command[1:],
                                                   cwd=self.selected.workspace, env=self.environment)
                async with stdio_client(parameters, errlog=log) as (reader, writer):
                    async with CancellableSession(reader, writer, read_timeout_seconds=timedelta(seconds=1800)) as session:
                        await session.initialize()
                        self.ready.set_result(session)
                        await self.closed.wait()
        except BaseException as exc:
            if not self.ready.done():
                if isinstance(exc, asyncio.CancelledError):
                    self.ready.cancel()
                else:
                    self.ready.set_exception(exc)
            if not isinstance(exc, asyncio.CancelledError):
                failure = json.dumps({"vaws_provider_failed": type(exc).__name__, "error": str(exc),
                                      "evidence": str(self.stderr)})
                with suppress(OSError):
                    with self.stderr.open("a", encoding="utf-8") as log:
                        log.write(failure + "\n")
                print(failure, file=sys.stderr, flush=True)
            for request in self.requests:
                request.cancel()
            if isinstance(exc, asyncio.CancelledError):
                raise

    async def request(self, method: str, **arguments):
        try:
            session = await asyncio.shield(self.ready)
        except Exception as exc:
            raise RuntimeError(f"{self.kind} provider could not start in {self.selected.key}; evidence: {self.stderr}: {exc}") from exc
        if self.worker.done():
            raise RuntimeError(f"provider stopped; evidence: {self.stderr}")
        request = asyncio.create_task(getattr(session, method)(**arguments))
        self.requests.add(request)
        try:
            return await request
        except Exception as exc:
            raise RuntimeError(f"{self.kind} provider {method} failed in {self.selected.key}; evidence: {self.stderr}: {exc}") from exc
        finally:
            self.requests.discard(request)

    async def tools(self):
        if self.catalog is None:
            if self.catalog_request is None:
                self.catalog_request = asyncio.create_task(self.request("list_tools"))
            try:
                result = await asyncio.shield(self.catalog_request)
                self.catalog = {tool.name: tool for tool in result.tools}
            except Exception:
                self.catalog_request = None
                raise
        return self.catalog

    async def close(self):
        pending = list(self.requests)
        for request in pending:
            request.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if not self.worker.done():
            self.worker.cancel()
        with suppress(asyncio.CancelledError):
            await self.worker


class Provider:
    def __init__(self, kind: str, root: Path, environment: dict | None = None):
        self.kind, self.root = kind, root
        self.environment = dict(os.environ if environment is None else environment)
        self.backends = {}
        self.retired = []
        self.catalog_selection = None
        self.scoped_catalogs = {}

    def backend(self, selected: Selection) -> Backend:
        key = (str(selected.workspace), selected.receipt)
        previous = self.backends.get(key)
        if previous is not None and (previous.worker.done() or previous.closed.is_set()):
            self.retired.append(previous)
            del self.backends[key]
        if key not in self.backends:
            self.backends[key] = Backend(self.kind, selected, self.root, self.environment)
        return self.backends[key]

    async def tools_for(self, selected: Selection):
        if self.kind == "knowledge":
            from vaws_knowledge_catalog import frozen_catalog
            receipt = read_receipt(selected.receipt)
            projected = frozen_catalog(receipt)
            if projected is not None:
                from mcp.types import Tool
                return {row["name"]: Tool.model_validate(row) for row in projected["tools"]}
            if receipt.get("schema_version") == 2:
                # Legacy selections can use an existing backend, but cannot
                # invent either its catalog or missing installation inputs.
                capability_receipt(receipt, "knowledge")
        return await self.backend(selected).tools()

    async def list_tools(self, metadata: dict | None = None):
        context = (caller_context({}, metadata, state_dir=self.environment.get("VAWS_AGENT_SESSIONS_DIR", ""))
                   if metadata else None)
        # A list request carrying a native association can describe that task's
        # fixed version. Unscoped clients still get the current catalog.
        selected = selection(self.root, context, catalog=context is None, require_prepared=False)
        catalog = await self.tools_for(selected)
        if context is not None:
            self.scoped_catalogs[context["context_file"]] = selected.key
        else:
            self.catalog_selection = selected.key
        tools = []
        for tool in catalog.values():
            item = tool.model_copy(deep=True)
            schema = copy.deepcopy(item.inputSchema)
            schema.setdefault("properties", {}).setdefault("context_file", {
                "type": "string", "description": "Existing VAWS context; native hooks normally supply it."})
            if self.kind == "task" and self.environment.get("VAWS_MCP_CLIENT") == "kimi":
                schema["properties"]["context_file"] = {
                    "type": "string", "description": "Copy context_file supplied by this session's native hook or vaws_start result."}
                required = schema.setdefault("required", [])
                if "context_file" not in required:
                    required.append("context_file")
            item.inputSchema = schema
            tools.append(item)
        return tools

    async def call_tool(self, name: str, arguments: dict, metadata: dict | None = None):
        context = caller_context(arguments, metadata, state_dir=self.environment.get("VAWS_AGENT_SESSIONS_DIR", ""))
        if context is None and self.kind == "task":
            raise ValueError("No native task context was supplied. Pass the context_file from session startup; no workspace or runtime was guessed.")
        selected = selection(self.root, context, require_prepared=self.kind == "task")
        values = dict(arguments)
        if self.kind == "task" and context:
            values["context_file"] = context["context_file"]
        elif self.kind != "task":
            values.pop("context_file", None)
        catalog_selection = self.scoped_catalogs.get(context["context_file"], self.catalog_selection) if context else self.catalog_selection
        if self.kind == "knowledge" or (catalog_selection is not None and catalog_selection != selected.key):
            # A long-lived native client may retain a newer schema than this
            # task. Check the fixed backend before sending a possible mutation.
            catalog = await self.tools_for(selected)
            tool = catalog.get(name)
            problem = "tool is unavailable in this task's fixed environment" if tool is None else None
            if tool is not None:
                from jsonschema.validators import validator_for
                validator = validator_for(tool.inputSchema)(tool.inputSchema)
                error = next(validator.iter_errors(values), None)
                if error is not None:
                    problem = error.message
            if problem is not None:
                from mcp.types import CallToolResult, TextContent
                facts = {"status": "unsupported_task_capability", "tool": name,
                         "environment": selected.key, "submitted": False,
                         "reason": problem, "input_schema": tool.inputSchema if tool else None,
                         "available_tools": sorted(catalog) if tool is None else None}
                return CallToolResult(isError=True, structuredContent=facts,
                                      content=[TextContent(type="text", text=json.dumps(facts))])
        if self.kind == "knowledge":
            # Keyed local preparation can take time. Other providers and
            # cancellation remain responsive; no tool has been submitted yet.
            await asyncio.to_thread(capability_receipt, read_receipt(selected.receipt),
                                    "knowledge", prepare_missing=True)
        backend = self.backend(selected)
        result = await backend.request("call_tool", name=name, arguments=values, meta=metadata)
        result.meta = {**(result.meta or {}), "vaws_provider": {
            "environment": selected.key, "workspace": str(selected.workspace),
            "python": backend.command[0], "stderr": str(backend.stderr)}}
        return result

    async def close(self):
        await asyncio.gather(*(backend.close() for backend in [*self.backends.values(), *self.retired]), return_exceptions=True)


async def serve(kind: str, root: Path):
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server

    provider = Provider(kind, root)
    server = Server("vaws-" + kind + "-environment", version="1")

    @server.list_tools()
    async def list_tools():
        meta = server.request_context.meta
        return await provider.list_tools(meta.model_dump(exclude_none=True) if meta else None)

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        meta = server.request_context.meta
        return await provider.call_tool(name, arguments, meta.model_dump(exclude_none=True) if meta else None)

    try:
        async with stdio_server() as (reader, writer):
            await server.run(reader, writer, server.create_initialization_options())
    finally:
        await provider.close()
