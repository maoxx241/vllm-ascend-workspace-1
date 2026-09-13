"""Official catalog projection and real lazy package construction boundaries."""
import asyncio
from importlib import metadata
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import vaws_environment as envs
import vaws_knowledge_catalog as catalogs
import vaws_mcp_runtime as runtime
from test_capability_environment import configure
from test_immutable_environment import workspace, execute


def test_projection_matches_locked_official_package_without_importing_it():
    root = Path(__file__).resolve().parents[2]
    data = catalogs.generate_catalog((root / "uv.lock").read_bytes())
    assert (root / catalogs.RELATIVE_PATH).read_bytes() == data


def test_generator_rejects_wrong_installed_commit():
    root = Path(__file__).resolve().parents[2]
    real = metadata.distribution("vaws-knowledge")
    wrong = SimpleNamespace(version=real.version, read_text=lambda name: '{"vcs_info":{"commit_id":"wrong"}}')
    with pytest.raises(ValueError, match="does not match"):
        catalogs.generate_catalog((root / "uv.lock").read_bytes(), wrong)


def test_tools_list_keeps_package_missing_and_call_installs_fixed_owner(workspace, monkeypatch):
    configure(workspace)
    receipt = envs.prepare_environment(workspace)
    selected = runtime.Selection(workspace, receipt["receipt"], receipt["python"], receipt["key"])
    monkeypatch.setattr(runtime, "selection", lambda *args, **kw: selected)
    monkeypatch.setattr(runtime, "caller_context", lambda *args, **kw: None)
    provider = runtime.Provider("knowledge", workspace)
    calls = []
    class Backend:
        command = ["selected-knowledge"]
        stderr = workspace / "backend.log"
        async def tools(self):
            pytest.fail("a generated catalog must not start the backend, even after installation")
        async def request(self, method, **kwargs):
            from mcp.types import CallToolResult
            owner = envs.capability_receipt(receipt, "knowledge")
            assert execute(owner["python"], "import vaws_knowledge;print(vaws_knowledge.VALUE)") == "1"
            calls.append((method, kwargs))
            return CallToolResult(content=[], structuredContent={"ok": True})
    def backend(selected):
        assert Path(receipt["components"]["knowledge"]).exists()
        return Backend()
    monkeypatch.setattr(provider, "backend", backend)
    async def scenario():
        assert (await provider.list_tools())[0].name == "knowledge_query"
        assert not Path(receipt["components"]["knowledge"]).exists()
        invalid = await provider.call_tool("knowledge_query", {"unknown": 1})
        assert invalid.isError and invalid.structuredContent["submitted"] is False
        assert not Path(receipt["components"]["knowledge"]).exists()
        result = await provider.call_tool("knowledge_query", {"text": "actual use"})
        assert result.structuredContent == {"ok": True}
        assert len(calls) == 1
        assert (await provider.list_tools())[0].name == "knowledge_query"
    asyncio.run(scenario())
    assert envs.saved_ready(workspace) == receipt


def test_scoped_catalog_uses_original_bundle_after_checkout_update(workspace, monkeypatch):
    configure(workspace)
    first = envs.prepare_environment(workspace)
    configure(workspace, "2")
    path = workspace / catalogs.RELATIVE_PATH
    value = json.loads(path.read_bytes())
    value["tools"][0]["name"] = "knowledge_query_new"
    path.write_text(json.dumps(value))
    second = envs.prepare_environment(workspace)
    monkeypatch.setattr(runtime, "selection", lambda root, context=None, **kw:
        runtime.Selection(workspace, (first if context else second)["receipt"], first["python"],
                          (first if context else second)["key"]))
    monkeypatch.setattr(runtime, "caller_context", lambda *args, **kw: {"context_file": "original"})
    provider = runtime.Provider("knowledge", workspace)
    monkeypatch.setattr(provider, "backend", lambda *args: pytest.fail("listing must not start knowledge"))
    async def scenario():
        assert (await provider.list_tools())[0].name == "knowledge_query_new"
        assert (await provider.list_tools({"native": "original"}))[0].name == "knowledge_query"
    asyncio.run(scenario())


def test_missing_legacy_catalog_is_explicitly_unavailable(workspace, monkeypatch):
    configure(workspace)
    receipt = envs.prepare_environment(workspace)
    receipt.pop("knowledge_catalog_sha256")
    receipt.pop("frozen_inputs")
    Path(receipt["receipt"]).write_text(json.dumps(receipt))
    provider = runtime.Provider("knowledge", workspace)
    selected = runtime.Selection(workspace, receipt["receipt"], receipt["python"], receipt["key"])
    monkeypatch.setattr(runtime, "selection", lambda *args, **kw: selected)
    monkeypatch.setattr(provider, "backend", lambda *args: pytest.fail("no legacy missing backend"))
    with pytest.raises(envs.EnvironmentError, match="not prepared"):
        asyncio.run(provider.list_tools())


def test_windows_handoff_uses_bundle_runtime_and_fixed_receipt(monkeypatch):
    import vaws_local_owner as local
    # Host-independent contract test: the executable/arguments derive solely
    # from the supplied fixed owner, never Linux's selected environment.
    receipt = {"platform": "win32", "receipt": "C:/fixed/.vaws-ready.json"}
    monkeypatch.setenv("WSL_DISTRO_NAME", "fixture")
    monkeypatch.setattr(envs, "_read_capability", lambda value, kind: {"python": "C:/fixed/runtime/python.exe"})
    monkeypatch.setattr(local, "accessible_windows_path", lambda value: "/mnt/" + value)
    monkeypatch.setattr(local, "managed_path", lambda value, **kw: "D:/workspace/.agents/lib")
    calls = []
    monkeypatch.setattr(envs.subprocess, "run", lambda command, **kw:
                        calls.append((command, kw)) or SimpleNamespace(returncode=0))
    envs._prepare_windows_capability(receipt)
    command, kwargs = calls[0]
    assert command[0] == "/mnt/C:/fixed/runtime/python.exe"
    assert command[-2:] == ["D:/workspace/.agents/lib", receipt["receipt"]]
    assert kwargs["env"][envs.PIN_ENV] == receipt["receipt"]
    assert "prepare_missing=True" in command[command.index("-c") + 1]


def test_cancel_during_preparation_submits_no_knowledge_call(workspace, monkeypatch):
    import threading
    configure(workspace)
    receipt = envs.prepare_environment(workspace)
    selected = runtime.Selection(workspace, receipt["receipt"], receipt["python"], receipt["key"])
    monkeypatch.setattr(runtime, "selection", lambda *args, **kw: selected)
    monkeypatch.setattr(runtime, "caller_context", lambda *args, **kw: None)
    entered, finish = threading.Event(), threading.Event()
    def prepare(*args, **kw):
        entered.set()
        assert finish.wait(5)
    monkeypatch.setattr(runtime, "capability_receipt", prepare)
    provider = runtime.Provider("knowledge", workspace)
    monkeypatch.setattr(provider, "backend", lambda *args: pytest.fail("cancelled call was submitted"))
    async def scenario():
        call = asyncio.create_task(provider.call_tool("knowledge_query", {"text": "cancel me"}))
        while not entered.is_set():
            await asyncio.sleep(.01)
        call.cancel()
        with pytest.raises(asyncio.CancelledError):
            await call
        finish.set()
    asyncio.run(scenario())
