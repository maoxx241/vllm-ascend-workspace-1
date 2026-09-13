"""Exercise real stdio backends selected by two independent native tasks."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
import vaws_mcp_runtime as runtime


FAKE_SERVER = '''import json,os,sys,threading,time
from pathlib import Path
key,evidence,init_gate=sys.argv[1:]
lock=threading.Lock()
waiting={}
cancelled=set()
def respond(message):
 method=message.get("method")
 params=message.get("params",{})
 if method=="initialize":
  while init_gate!="-" and not Path(init_gate).exists(): time.sleep(.01)
  result={"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"serverInfo":{"name":"fixture","version":key}}
 elif method=="tools/list":
  result={"tools":[{"name":"knowledge_query","description":"fixture","inputSchema":{"type":"object","properties":{"text":{"type":"string"}},"additionalProperties":False}}]}
 elif method=="tools/call":
  if params["name"]=="exit": os._exit(7)
  if params["name"]=="fail":
   with lock: print(json.dumps({"jsonrpc":"2.0","id":message["id"],"error":{"code":-32000,"message":"fixture remote failure"}}),flush=True)
   return
  if message["id"] in waiting:
   waiting[message["id"]].wait()
   if message["id"] in cancelled: return
  payload={"runtime":key,"arguments":params["arguments"],"meta":params.get("_meta")}
  result={"content":[{"type":"text","text":json.dumps(payload)}],"structuredContent":payload,"isError":False}
 else: result={}
 with lock: print(json.dumps({"jsonrpc":"2.0","id":message["id"],"result":result}),flush=True)
for line in sys.stdin:
 message=json.loads(line)
 with open(evidence,"a",encoding="utf-8") as log: log.write(json.dumps(message)+"\\n")
 if message.get("method")=="notifications/cancelled":
  identifier=message["params"]["requestId"]
  cancelled.add(identifier)
  if identifier in waiting: waiting[identifier].set()
  continue
 if "id" not in message: continue
 if message.get("params",{}).get("arguments",{}).get("wait"):
  waiting[message["id"]]=threading.Event()
 threading.Thread(target=respond,args=(message,),daemon=True).start()
'''


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.script = self.root / "provider.py"
        self.script.write_text(FAKE_SERVER)
        self.workspaces = []
        self.selections = {}
        for key in ("old", "new"):
            workspace = self.root / key
            workspace.mkdir()
            self.workspaces.append(workspace)
            self.selections[key] = runtime.Selection(workspace, str(workspace / "ready.json"), sys.executable, key)
        self.init_gate = None
        self.command_patch = patch.object(runtime, "provider_command", side_effect=lambda kind, selected, env:
                                          ([sys.executable, str(self.script), selected.key,
                                            str(self.root / (selected.key + ".jsonl")), str(self.init_gate or "-")], dict(env)))
        self.command_patch.start()
        self.addCleanup(self.command_patch.stop)
        # These subprocess protocol fixtures represent legacy complete owners;
        # lazy split-owner/catalog behavior has its own real install tests.
        receipt_patch = patch.object(runtime, "read_receipt", return_value={"schema_version": 1})
        receipt_patch.start()
        self.addCleanup(receipt_patch.stop)
        from mcp.client import stdio
        launch = stdio._create_platform_compatible_process
        self.processes = []
        async def observe_launch(*args, **kwargs):
            process = await launch(*args, **kwargs)
            self.processes.append(process)
            return process
        process_patch = patch.object(stdio, "_create_platform_compatible_process", side_effect=observe_launch)
        process_patch.start()
        self.addCleanup(process_patch.stop)

    async def received(self, predicate, *, key="new"):
        async def wait():
            path = self.root / (key + ".jsonl")
            while True:
                for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # The child may still be appending this line.
                    if predicate(message):
                        return message
                await asyncio.sleep(.01)
        return await asyncio.wait_for(wait(), timeout=5)

    async def test_persistent_provider_uses_each_tasks_fixed_runtime(self):
        provider = runtime.Provider("knowledge", self.root)
        contexts = {"first": {"id": "old", "context_file": "first"},
                    "second": {"id": "new", "context_file": "second"}}
        def choose(root, context=None, *, catalog=False, require_prepared=True):
            return self.selections[context["id"] if context else "new"]
        try:
            with patch.object(runtime, "caller_context", side_effect=lambda args, meta, **kw: contexts[args["context_file"]]), \
                 patch.object(runtime, "selection", side_effect=choose):
                tools = await provider.list_tools()
                self.assertIn("context_file", tools[0].inputSchema["properties"])
                old = await provider.call_tool("knowledge_query", {"text": "first", "context_file": "first"})
                new = await provider.call_tool("knowledge_query", {"text": "second", "context_file": "second"})
                again = await provider.call_tool("knowledge_query", {"text": "resume", "context_file": "first"})
            self.assertEqual([old.structuredContent["runtime"], new.structuredContent["runtime"], again.structuredContent["runtime"]],
                             ["old", "new", "old"])
            self.assertNotIn("context_file", new.structuredContent["arguments"])
            self.assertEqual(new.meta["vaws_provider"]["environment"], "new")
            self.assertTrue(Path(new.meta["vaws_provider"]["stderr"]).is_file())
            self.assertEqual(len(provider.backends), 2)
        finally:
            await provider.close()
        self.assertTrue(all(item.worker.done() for item in provider.backends.values()))

    async def test_task_context_and_native_metadata_survive_forwarding(self):
        provider = runtime.Provider("task", self.root)
        metadata = {"x-codex-turn-metadata": {"thread_id": "test-thread"}}
        try:
            with patch.object(runtime, "caller_context", return_value={"context_file": "known-context"}), \
                 patch.object(runtime, "selection", return_value=self.selections["new"]):
                result = await provider.call_tool("vaws_session", {}, metadata)
            self.assertEqual(result.structuredContent["arguments"]["context_file"], "known-context")
            self.assertEqual(result.structuredContent["meta"]["x-codex-turn-metadata"], metadata["x-codex-turn-metadata"])
        finally:
            await provider.close()

    async def test_kimi_catalog_requires_the_existing_native_context(self):
        for kind in ("task", "remote", "knowledge"):
            provider = runtime.Provider(kind, self.root, {"VAWS_MCP_CLIENT": "kimi"})
            try:
                with patch.object(runtime, "selection", return_value=self.selections["new"]):
                    tools = await provider.list_tools()
                if kind == "task":
                    self.assertIn("context_file", tools[0].inputSchema["required"])
                    self.assertIn("native hook", tools[0].inputSchema["properties"]["context_file"]["description"])
                else:
                    self.assertNotIn("context_file", tools[0].inputSchema.get("required", []))
            finally:
                await provider.close()

    async def test_missing_backend_returns_failure_without_hidden_fallback(self):
        from vaws_diagnostics import configure
        with patch.dict("os.environ", {"VAWS_DIAGNOSTICS_ROOT": str(self.root / "diagnostics"), "VAWS_LOG_LEVEL": "INFO"}):
            recorder = configure("vaws-workspace", root=str(self.root / "diagnostics"))
            provider = runtime.Provider("task", self.root)
            try:
                with patch.object(runtime, "provider_command", return_value=([sys.executable, str(self.root / "missing.py")], {})):
                    backend = provider.backend(self.selections["new"])
                    with self.assertRaises(Exception):
                        await asyncio.wait_for(backend.request("list_tools"), timeout=10)
                    self.assertTrue(backend.stderr.is_file())
                    records = [json.loads(line) for line in backend.stderr.read_text(encoding="utf-8").splitlines()]
                    previews = [row.get("attributes", {}).get("preview", "") for row in records
                                if row.get("event") == "process.stderr"]
                    # A private/high-entropy temporary path may be redacted in
                    # full. The OS failure must remain diagnostically useful.
                    self.assertTrue(any("can't open file" in text and "[Errno 2]" in text for text in previews))
            finally:
                await provider.close()
                recorder.close()
            self.assertEqual([process.returncode for process in self.processes], [2])

    async def test_task_without_context_does_not_start_a_runtime(self):
        for kind in ("task",):
            provider = runtime.Provider(kind, self.root)
            with patch.object(runtime, "caller_context", return_value=None):
                with self.assertRaisesRegex(ValueError, "No native task context"):
                    await provider.call_tool("unused", {})
            self.assertEqual(provider.backends, {})

    async def test_explicit_companion_works_without_task_preparation(self):
        for kind in ("knowledge", "remote"):
            provider = runtime.Provider(kind, self.root)
            try:
                with patch.object(runtime, "caller_context", return_value=None), \
                     patch.object(runtime, "selection", return_value=self.selections["new"]) as select:
                    arguments = {"text": "fixture"} if kind == "knowledge" else {"host": "fixture", "container": "repro"}
                    result = await provider.call_tool("knowledge_query" if kind == "knowledge" else "read", arguments)
                select.assert_called_once_with(self.root, None, require_prepared=False)
                self.assertEqual(result.structuredContent["arguments"], arguments)
            finally:
                await provider.close()

    async def test_long_call_keeps_status_and_stop_concurrent_and_cancellation_reaches_exact_request(self):
        provider = runtime.Provider("remote", self.root)
        backend = provider.backend(self.selections["new"])
        try:
            slow = asyncio.create_task(backend.request("call_tool", name="remote_bash", arguments={"wait": True}))
            request = await self.received(lambda row: row.get("params", {}).get("name") == "remote_bash")
            replies = await asyncio.wait_for(asyncio.gather(
                backend.request("call_tool", name="remote_job_status", arguments={"job_id": "owned"}),
                backend.request("call_tool", name="remote_job_stop", arguments={"job_id": "owned"}),
            ), timeout=3)
            self.assertFalse(slow.done())
            self.assertEqual([row.structuredContent["arguments"] for row in replies], [{"job_id": "owned"}] * 2)
            slow.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await slow
            cancelled = await self.received(lambda row: row.get("method") == "notifications/cancelled")
            self.assertEqual(cancelled["params"]["requestId"], request["id"])
            self.assertEqual((await backend.request("list_tools")).tools[0].name, "knowledge_query")
        finally:
            await provider.close()
        self.assertTrue(backend.worker.done())
        self.assertTrue(self.processes)
        self.assertTrue(all(process.returncode is not None for process in self.processes))

    async def test_cancel_during_initialization_does_not_cancel_other_callers_startup(self):
        self.init_gate = self.root / "initialize-release"
        provider = runtime.Provider("remote", self.root)
        backend = provider.backend(self.selections["new"])
        try:
            first = asyncio.create_task(backend.request("list_tools"))
            await self.received(lambda row: row.get("method") == "initialize")
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertFalse(backend.ready.cancelled())
            second = asyncio.create_task(backend.request("list_tools"))
            self.init_gate.touch()
            self.assertEqual((await asyncio.wait_for(second, timeout=3)).tools[0].name, "knowledge_query")
            self.assertFalse(backend.worker.done())
        finally:
            await provider.close()
        self.assertTrue(all(process.returncode is not None for process in self.processes))

    async def test_remote_error_keeps_selected_runtime_and_raw_failure_visible(self):
        provider = runtime.Provider("remote", self.root)
        backend = provider.backend(self.selections["new"])
        try:
            with self.assertRaisesRegex(RuntimeError, "fixture remote failure") as error:
                await backend.request("call_tool", name="fail", arguments={})
            self.assertIn("remote provider call_tool failed in new", str(error.exception))
            self.assertIn(str(backend.stderr), str(error.exception))
            self.assertIsNotNone(error.exception.__cause__)
            self.assertTrue(backend.stderr.is_file())
            self.assertEqual((await backend.request("list_tools")).tools[0].name, "knowledge_query")
        finally:
            await provider.close()

    async def test_child_exit_returns_evidence_and_close_reaps_the_process(self):
        provider = runtime.Provider("remote", self.root)
        backend = provider.backend(self.selections["new"])
        try:
            with self.assertRaisesRegex(RuntimeError, "evidence:") as error:
                await asyncio.wait_for(backend.request("call_tool", name="exit", arguments={}), timeout=3)
            self.assertIn(str(backend.stderr), str(error.exception))
        finally:
            await provider.close()
        self.assertEqual([process.returncode for process in self.processes], [7])

    async def test_dead_backend_recovers_only_for_a_new_call_without_replaying_exit(self):
        provider = runtime.Provider("remote", self.root)
        selected = self.selections["old"]
        backend = provider.backend(selected)
        try:
            with self.assertRaisesRegex(RuntimeError, "evidence:"):
                await asyncio.wait_for(backend.request("call_tool", name="exit", arguments={}), 3)
            await asyncio.wait_for(backend.closed.wait(), 3)
            recovered = provider.backend(selected)
            self.assertIsNot(recovered, backend)
            self.assertEqual(recovered.selected, selected)
            self.assertEqual((await recovered.request("list_tools")).tools[0].name, "knowledge_query")
            messages = [json.loads(line) for line in (self.root / "old.jsonl").read_text().splitlines()]
            self.assertEqual(sum(row.get("params", {}).get("name") == "exit" for row in messages), 1)
            self.assertEqual(sum(row.get("method") == "initialize" for row in messages), 2)
        finally:
            await provider.close()
        self.assertTrue(all(process.returncode is not None for process in self.processes))

    async def test_failed_start_can_recover_on_the_same_fixed_selection(self):
        provider = runtime.Provider("remote", self.root)
        selected = self.selections["old"]
        try:
            with patch.object(runtime, "provider_command", return_value=([sys.executable, str(self.root / "missing.py")], {})):
                failed = provider.backend(selected)
                with self.assertRaises(RuntimeError):
                    await asyncio.wait_for(failed.request("list_tools"), 3)
                await asyncio.wait_for(asyncio.shield(failed.worker), 3)
            recovered = provider.backend(selected)
            self.assertIsNot(recovered, failed)
            self.assertEqual((await recovered.request("list_tools")).tools[0].name, "knowledge_query")
        finally:
            await provider.close()

    async def test_new_catalog_arguments_never_reach_incompatible_old_backend(self):
        provider = runtime.Provider("knowledge", self.root)
        try:
            with patch.object(runtime, "selection", return_value=self.selections["new"]):
                await provider.list_tools()
            with patch.object(runtime, "caller_context", return_value={"context_file": "old"}), \
                 patch.object(runtime, "selection", return_value=self.selections["old"]):
                result = await provider.call_tool("knowledge_query", {"text": "query", "future_option": True})
                missing = await provider.call_tool("new_mutation", {})
                accepted = await provider.call_tool("knowledge_query", {"text": "compatible"})
            self.assertTrue(result.isError)
            self.assertFalse(result.structuredContent["submitted"])
            self.assertEqual(result.structuredContent["environment"], "old")
            self.assertIn("input_schema", result.structuredContent)
            self.assertTrue(missing.isError)
            self.assertEqual(accepted.structuredContent["runtime"], "old")
            messages = [json.loads(line) for line in (self.root / "old.jsonl").read_text().splitlines()]
            self.assertEqual(sum(row.get("method") == "tools/call" for row in messages), 1)
            self.assertEqual(sum(row.get("method") == "tools/list" for row in messages), 1)
        finally:
            await provider.close()

    async def test_scoped_catalog_uses_native_tasks_fixed_environment(self):
        provider = runtime.Provider("task", self.root)
        context = {"context_file": "old"}
        metadata = {"x-codex-turn-metadata": {"thread_id": "old-thread"}}
        try:
            with patch.object(runtime, "caller_context", return_value=context), \
                 patch.object(runtime, "selection", return_value=self.selections["old"]) as choose:
                await provider.list_tools(metadata)
            choose.assert_called_once_with(self.root, context, catalog=False, require_prepared=False)
            self.assertEqual(provider.scoped_catalogs, {"old": "old"})
            self.assertIsNone(provider.catalog_selection)
        finally:
            await provider.close()

    async def test_diagnostic_directory_failure_does_not_block_owner_startup(self):
        provider = runtime.Provider("remote", self.root)
        blocked = self.root / "unwritable-diagnostics"
        blocked.write_text("not a directory")
        try:
            with patch.dict("os.environ", {"VAWS_DIAGNOSTICS_ROOT": str(blocked)}):
                backend = provider.backend(self.selections["new"])
                result = await asyncio.wait_for(backend.request("list_tools"), timeout=3)
                self.assertEqual(result.tools[0].name, "knowledge_query")
        finally:
            await provider.close()
        self.assertEqual(len(self.processes), 1)



class SelectionTests(unittest.TestCase):
    def prepared_focus(self, base, preferred="vllm-ascend"):
        from vaws_workspace_entry import write_preparation

        # Match shared_workspace_root's physical owner path. macOS temporary
        # directories may be spelled /var while their real root is /private/var.
        base = base.resolve()
        project, workspace = base / "project", base / "bundle"
        project.mkdir()
        sources = {"workspace": workspace, "vllm": workspace / "vllm",
                   "vllm-ascend": workspace / "vllm-ascend"}
        for path in sources.values():
            (path / ".git").mkdir(parents=True)
        record = write_preparation(workspace, project_root=project, native_workspace=workspace,
                                   workspace=workspace, sources=sources, preferred=preferred)
        context = {"session": {"id": "vaws-" + "a" * 32}, "context_file": "known",
                   "attachment": {"cwd": str(workspace)}}
        saved = {"key": "prepared", "python": sys.executable, "receipt": "fixed-receipt"}
        protected = [workspace / ".vaws-local/native-workspace.json", Path(record["editor_workspace"])]
        return project, workspace, sources, context, saved, protected

    def test_prepared_child_cwd_selects_its_repository_without_start_or_shared_writes(self):
        for suffix in ("vllm", "vllm/src"):
            with self.subTest(cwd=suffix), tempfile.TemporaryDirectory() as tmp:
                project, workspace, sources, context, saved, protected = self.prepared_focus(Path(tmp))
                child = workspace / suffix
                child.mkdir(parents=True, exist_ok=True)
                context["attachment"]["cwd"] = str(child)
                before = {path: path.read_bytes() for path in protected}
                files = set((workspace / ".vaws-local").rglob("*"))
                with patch.object(runtime, "shared_workspace_root", return_value=project), \
                     patch.object(runtime, "saved_ready", return_value=saved), \
                     patch("vaws_workspace_update.git", side_effect=AssertionError("unneeded Git discovery")):
                    selected = runtime.selection(project, context)
                self.assertEqual(selected.workspace, workspace)
                self.assertEqual(selected.repository, "vllm")
                self.assertEqual(selected.cwd, sources["vllm"])
                self.assertEqual(selected.key, saved["key"])
                self.assertFalse((runtime.task_dir(context["session"]["id"], project) / "start.json").exists())
                self.assertEqual({path: path.read_bytes() for path in protected}, before)
                self.assertEqual(set((workspace / ".vaws-local").rglob("*")), files)

    def test_prepared_root_cwd_keeps_explicit_receipt_focus_without_shared_writes(self):
        for preferred in ("workspace", "vllm"):
            with self.subTest(repository=preferred), tempfile.TemporaryDirectory() as tmp:
                project, workspace, sources, context, saved, protected = self.prepared_focus(Path(tmp), preferred)
                before = {path: path.read_bytes() for path in protected}
                with patch.object(runtime, "shared_workspace_root", return_value=project), \
                     patch.object(runtime, "saved_ready", return_value=saved):
                    selected = runtime.selection(project, context)
                self.assertEqual(selected.repository, preferred)
                self.assertEqual(selected.cwd, sources[preferred])
                self.assertEqual({path: path.read_bytes() for path in protected}, before)
                self.assertFalse((runtime.task_dir(context["session"]["id"], project) / "start.json").exists())

    def test_existing_start_focus_wins_over_native_child_and_shared_preparation(self):
        for preferred in ("workspace", "vllm"):
            with self.subTest(repository=preferred), tempfile.TemporaryDirectory() as tmp:
                project, workspace, sources, context, saved, protected = self.prepared_focus(Path(tmp))
                context["attachment"]["cwd"] = str(sources["vllm-ascend"])
                path = runtime.task_dir(context["session"]["id"], project) / "start.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"workspace": str(workspace), "sources": {
                    name: str(root) for name, root in sources.items()}, "environment": saved,
                    "repository": preferred, "cwd": str(sources[preferred])}), encoding="utf-8")
                protected.append(path)
                before = {item: item.read_bytes() for item in protected}
                with patch.object(runtime, "shared_workspace_root", return_value=project), \
                     patch.object(runtime, "read_receipt", return_value=saved), \
                     patch.object(runtime, "saved_ready", side_effect=AssertionError("reselected prepared runtime")):
                    selected = runtime.selection(project, context)
                self.assertEqual(selected.repository, preferred)
                self.assertEqual(selected.cwd, sources[preferred])
                self.assertEqual({item: item.read_bytes() for item in protected}, before)

    def test_metadata_cannot_override_an_explicit_different_native_context(self):
        with patch("vaws_coordinator.agent_session.AgentSessions") as store:
            store.return_value.native_context.return_value = {"context_file": "native-context"}
            with self.assertRaisesRegex(ValueError, "differs"):
                runtime.caller_context({"context_file": "another-task"},
                                       {"x-codex-turn-metadata": {"thread_id": "native"}})

    def test_persistent_process_environment_is_not_a_caller_identity(self):
        with patch.dict("os.environ", {"VAWS_CONTEXT_FILE": "parent-task"}), \
             patch("vaws_coordinator.agent_session.load_context") as load:
            self.assertIsNone(runtime.caller_context({}, {}))
            load.assert_not_called()

    def test_no_identity_does_not_open_registry(self):
        with patch("vaws_coordinator.agent_session.AgentSessions", side_effect=AssertionError("registry opened")):
            self.assertIsNone(runtime.caller_context({}, {}))

    def test_task_receipt_wins_over_latest_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = root / "old", root / "new"
            old.mkdir()
            new.mkdir()
            record = runtime.task_dir("vaws-" + "a" * 32, root) / "start.json"
            record.parent.mkdir(parents=True)
            record.write_text(json.dumps({"workspace": str(old), "environment": {"receipt": "old"}}))
            latest = root / ".vaws-local/latest-runtime.json"
            latest.write_text(json.dumps({"workspace": str(new), "environment": {"receipt": "new"}}))
            context = {"session": {"id": "vaws-" + "a" * 32}, "context_file": "known", "attachment": {"cwd": str(root)}}
            with patch.object(runtime, "read_receipt", side_effect=lambda key: {"key": key, "python": sys.executable, "receipt": key}):
                self.assertEqual(runtime.selection(root, context).workspace, old.resolve())
                self.assertEqual(runtime.selection(root, catalog=True).workspace, new.resolve())

    def test_direct_companion_uses_configured_selection_without_git_or_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / ".vaws-local/latest-runtime.json"
            latest.parent.mkdir()
            latest.write_text("not a valid catalog")
            saved = {"key": "configured", "python": sys.executable, "receipt": "configured-receipt"}
            with patch.object(runtime, "saved_ready", return_value=saved) as ready, \
                 patch.object(runtime, "shared_workspace_root", side_effect=AssertionError("unneeded Git discovery")):
                selected = runtime.selection(root, require_prepared=False)
            self.assertEqual(selected.workspace, root)
            self.assertEqual(selected.key, "configured")
            ready.assert_called_once_with(root)

    def test_only_prepared_linked_worktree_can_supply_a_missing_task_receipt(self):
        from vaws_workspace_update import git
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mother"
            root.mkdir()
            git(root, "init")
            git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture")
            worktree = Path(tmp) / "prepared worktree"
            git(root, "worktree", "add", "--detach", str(worktree), "HEAD")
            context = {"session": {"id": "vaws-" + "a" * 32}, "context_file": "known", "attachment": {"cwd": str(root)}}
            saved = {"key": "prepared", "python": sys.executable, "receipt": "fixed-receipt"}
            mother_selection = root / ".vaws-local/environment-selection" / f"{sys.platform}.json"
            mother_selection.parent.mkdir(parents=True)
            mother_selection.write_text(json.dumps(saved))
            with patch.object(runtime, "saved_ready", return_value=saved) as ready:
                with self.assertRaisesRegex(ValueError, "no prepared workspace"):
                    runtime.selection(root, context)
                ready.assert_not_called()
                self.assertEqual(runtime.selection(root, context, require_prepared=False).workspace, root.resolve())
                ready.reset_mock()
                context["attachment"]["cwd"] = str(worktree)
                with self.assertRaisesRegex(ValueError, "no prepared workspace"):
                    runtime.selection(root, context)
                ready.assert_not_called()
                native_selection = worktree / ".vaws-local/environment-selection" / f"{sys.platform}.json"
                native_selection.parent.mkdir(parents=True)
                native_selection.write_text(json.dumps(saved))
                self.assertEqual(runtime.selection(root, context).workspace, worktree.resolve())
                child = worktree / "src"
                child.mkdir()
                context["attachment"]["cwd"] = str(child)
                self.assertEqual(runtime.selection(root, context).workspace, worktree.resolve())
                self.assertEqual(ready.call_args.args, (worktree.resolve(),))


if __name__ == "__main__":
    unittest.main()
