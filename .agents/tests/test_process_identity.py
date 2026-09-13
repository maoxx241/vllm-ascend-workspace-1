"""Process ownership remains birth plus raw command, including old CIM records."""
from __future__ import annotations

import ctypes
from contextlib import ExitStack
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import vaws_process_identity as identity


@pytest.mark.parametrize("pid", [None, True, "1", 0, -1])
def test_invalid_pid_is_unowned(pid):
    assert identity.process_identity(pid) is None


def fake_windows(monkeypatch, fault=None):
    kernel = SimpleNamespace(OpenProcess=Mock(return_value=123),
        GetProcessTimes=Mock(), WaitForSingleObject=Mock(return_value=0x102),
        CloseHandle=Mock(return_value=1))
    native = SimpleNamespace(NtQueryInformationProcess=Mock())
    monkeypatch.setattr(ctypes, "WinDLL", lambda name, **kwargs:
        kernel if name == "kernel32" else native, raising=False)
    command = '"C:\\Unicode 中文 🧪\\python.exe" worker "" "a\\\"b"'
    encoded = command.encode("utf-16-le")
    if fault == "invalid_utf16":
        encoded = b"\x00\xd8"
    elif fault == "embedded_null":
        encoded = "worker\0other".encode("utf-16-le")
    header_size = ctypes.sizeof(identity._UnicodeString)
    capacity = header_size + len(encoded) + 2

    def times(handle, creation, exit_time, kernel_time, user_time):
        birth = 134337700861979955 if fault != "zero_birth" else 0
        creation._obj.low = birth & 0xFFFFFFFF
        creation._obj.high = birth >> 32
        return fault != "times_failed"

    def query(handle, info_class, buffer, size, returned):
        assert handle == 123 and info_class == 60
        if fault == "query_exception":
            raise OSError("native query failed")
        if buffer is None:
            returned._obj.value = ({"empty_size": 0, "header_only": header_size,
                "oversized": 65536 + header_size + 1}.get(fault, capacity))
            return -1073741821 if fault == "unsupported" else -1073741820
        assert size == capacity
        returned._obj.value = capacity
        if fault == "second_failed":
            return -1073741820
        if fault == "returned_past_allocation":
            returned._obj.value = capacity + 1
        elif fault == "returned_header_only":
            returned._obj.value = header_size
        value = identity._UnicodeString.from_buffer(buffer)
        base = ctypes.addressof(buffer)
        value.buffer = base + header_size
        value.length = len(encoded)
        value.maximum_length = len(encoded) + 2
        ctypes.memmove(value.buffer, encoded + b"\0\0", len(encoded) + 2)
        if fault == "null_pointer":
            value.buffer = None
        elif fault == "pointer_in_header":
            value.buffer = base
        elif fault == "pointer_past_end":
            value.buffer = base + capacity
        elif fault == "unaligned_pointer":
            value.buffer += 1
        elif fault == "odd_length":
            value.length -= 1
        elif fault == "odd_maximum":
            value.maximum_length -= 1
        elif fault == "length_past_maximum":
            value.maximum_length = value.length - 2
        elif fault == "empty_command":
            value.length = 0
        return 0

    kernel.GetProcessTimes.side_effect = times
    native.NtQueryInformationProcess.side_effect = query
    if fault == "open_failed":
        kernel.OpenProcess.return_value = None
    elif fault == "already_exited":
        kernel.WaitForSingleObject.return_value = 0
    elif fault == "exits_during_query":
        kernel.WaitForSingleObject.side_effect = [0x102, 0]
    elif fault == "wait_failed":
        kernel.WaitForSingleObject.return_value = 0xFFFFFFFF
    return kernel, native, command


def test_native_buffer_preserves_raw_command_and_cim_precision(monkeypatch):
    kernel, native, command = fake_windows(monkeypatch)
    assert identity._windows_process_identity(42) == {
        "started": "639248932861979950", "command": command}
    kernel.OpenProcess.assert_called_once_with(0x00101000, False, 42)
    assert native.NtQueryInformationProcess.call_count == 2
    assert kernel.WaitForSingleObject.call_count == 2
    kernel.CloseHandle.assert_called_once_with(123)


@pytest.mark.parametrize("fault", ["open_failed", "already_exited", "wait_failed",
    "times_failed", "zero_birth", "unsupported", "query_exception", "empty_size", "header_only",
    "oversized", "second_failed", "returned_past_allocation", "returned_header_only",
    "null_pointer", "pointer_in_header", "pointer_past_end", "unaligned_pointer",
    "odd_length", "odd_maximum", "length_past_maximum", "empty_command",
    "invalid_utf16", "embedded_null", "exits_during_query"])
def test_native_faults_are_unowned_and_close_the_held_handle(monkeypatch, fault):
    kernel, _, _ = fake_windows(monkeypatch, fault)
    assert identity._windows_process_identity(42) is None
    if fault == "open_failed":
        kernel.CloseHandle.assert_not_called()
    else:
        kernel.CloseHandle.assert_called_once_with(123)


def test_unavailable_native_api_and_oversized_pid_do_not_probe_other_process(monkeypatch):
    loader = Mock(side_effect=OSError("unavailable native API"))
    monkeypatch.setattr(ctypes, "WinDLL", loader, raising=False)
    assert identity._windows_process_identity(2**32 + 42) is None
    loader.assert_not_called()
    assert identity._windows_process_identity(42) is None


@pytest.mark.skipif(os.name != "nt", reason="native Windows process identity")
def test_native_self_identity_rejects_other_birth_and_command_without_powershell(monkeypatch):
    monkeypatch.setattr(identity.subprocess, "run", Mock(side_effect=AssertionError("unexpected subprocess")))
    observed = identity.process_identity(os.getpid())
    assert observed and observed["command"]
    assert identity.same_process(os.getpid(), observed)
    assert not identity.same_process(os.getpid(), {**observed, "started": str(int(observed["started"]) + 10)})
    assert not identity.same_process(os.getpid(), {**observed, "command": observed["command"] + " other"})
    assert not identity.same_process(os.getpid(), None)


@pytest.mark.skipif(os.name != "nt", reason="native Windows venv identity")
def test_native_new_venv_child_unicode_identity(tmp_path):
    from vaws_windows import owned_process

    ready = tmp_path / "child-ready.json"
    command = [sys.executable, "-B", "-c",
        "import json,os,sys; from pathlib import Path; "
        "ready=Path(sys.argv[1]); pending=ready.with_suffix('.tmp'); "
        "pending.write_text(json.dumps({'pid':os.getpid()}),encoding='utf-8'); "
        "pending.replace(ready); sys.stdin.read(1)", str(ready),
        "中文 🧪 model", "", "trailing\\", 'a"b']
    child_pid = None
    with ExitStack() as stack:
        process = stack.enter_context(owned_process(command, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8"))
        stack.callback(process.stdin.close)
        stack.callback(process.stderr.close)
        early = identity.process_identity(process.pid)
        assert early, "identity must be available just after CreateProcess"
        deadline = time.monotonic() + 10
        while not ready.is_file() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.is_file(), "owned Python child did not publish its ready marker within 10 seconds"
        child_pid = json.loads(ready.read_text(encoding="utf-8"))["pid"]
        assert identity.process_identity(process.pid) == early
        assert "中文 🧪 model" in early["command"]
        child_identity = identity.process_identity(child_pid)
        assert child_identity and child_identity["command"] == early["command"]
        if child_pid != process.pid:
            assert child_identity["started"] != early["started"]
            assert not identity.same_process(process.pid, child_identity)
        # Normal completion releases stdin. On assertion/timeout the Job context
        # cleans up both redirector and child, without a masking communicate().
        process.communicate("x", timeout=5)
    assert process.returncode == 0
    assert identity.process_identity(process.pid) is None
    assert child_pid is not None and identity.process_identity(child_pid) is None


@pytest.mark.skipif(os.name != "nt" or os.environ.get("VAWS_TEST_LEGACY_CIM") != "1",
    reason="opt-in legacy CIM comparison: VAWS_TEST_LEGACY_CIM=1")
def test_native_legacy_cim_identity_opt_in():
    observed = identity.process_identity(os.getpid())
    assert observed
    script = ("[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
        f"$observedProcess=Get-CimInstance Win32_Process -Filter 'ProcessId={os.getpid()}'; "
        "@{started=$observedProcess.CreationDate.ToUniversalTime().Ticks.ToString(); "
        "command=$observedProcess.CommandLine} | ConvertTo-Json -Compress")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    legacy = json.loads(result.stdout)
    assert legacy == observed
    assert identity.same_process(os.getpid(), legacy)
