"""Small OS process snapshots for the workspace's two local launchers.

A persisted PID alone is not ownership: compare birth time and command before
reusing or stopping a process. Unreadable or legacy records remain unowned.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class _FileTime(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class _UnicodeString(ctypes.Structure):
    _fields_ = [("length", ctypes.c_uint16), ("maximum_length", ctypes.c_uint16),
                ("buffer", ctypes.c_void_p)]


def _windows_process_identity(pid: int) -> dict[str, str] | None:
    """Read one held process handle, without starting another interpreter.

    ProcessCommandLineInformation is an internal NT query, not a guaranteed
    public Win32 contract. Unsupported queries remain unknown. Its string is
    copied into our bounded buffer; no remote PEB layout or memory read is used.
    """
    if pid <= 0 or pid > 0xFFFFFFFF:
        return None
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = ctypes.WinDLL("ntdll")
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.GetProcessTimes.argtypes = [ctypes.c_void_p, *([ctypes.POINTER(_FileTime)] * 4)]
        kernel.GetProcessTimes.restype = ctypes.c_int
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_int
        query = ntdll.NtQueryInformationProcess
        query.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
                          ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
        query.restype = ctypes.c_int32
        # QUERY_LIMITED_INFORMATION | SYNCHRONIZE; observation grants no kill.
        handle = kernel.OpenProcess(0x00101000, False, pid)
        if not handle:
            return None
        try:
            if kernel.WaitForSingleObject(handle, 0) != 0x102:
                return None
            times = [_FileTime() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
                return None
            birth = (times[0].high << 32) | times[0].low
            if not birth:
                return None
            needed = ctypes.c_uint32()
            status = query(handle, 60, None, 0, ctypes.byref(needed))
            if status not in (0, -1073741820, -1073741789):
                return None  # INFO_LENGTH_MISMATCH / BUFFER_TOO_SMALL only.
            header_size = ctypes.sizeof(_UnicodeString)
            if not header_size < needed.value <= 65536 + header_size:
                return None
            buffer = ctypes.create_string_buffer(needed.value)
            status = query(handle, 60, buffer, len(buffer), ctypes.byref(needed))
            if status < 0 or not header_size < needed.value <= len(buffer):
                return None
            value = _UnicodeString.from_buffer(buffer)
            address = ctypes.addressof(buffer)
            pointer = value.buffer
            if (not pointer or not value.length or value.length % 2
                    or value.maximum_length % 2 or value.length > value.maximum_length
                    or pointer % 2 or pointer < address + header_size
                    or pointer + value.maximum_length > address + needed.value):
                return None
            command = ctypes.string_at(pointer, value.length).decode("utf-16-le")
            if not command or "\0" in command or kernel.WaitForSingleObject(handle, 0) != 0x102:
                return None
            # CIM CreationDate has microsecond precision. Preserve its existing
            # .NET ticks representation exactly, without float conversion.
            started = str((birth // 10) * 10 + 504911232000000000)
            return {"started": started, "command": command}
        finally:
            kernel.CloseHandle(handle)
    except (AttributeError, OSError, ValueError, OverflowError, ctypes.ArgumentError):
        return None


def process_identity(pid: int) -> dict[str, str] | None:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    try:
        if os.name == "nt":
            return _windows_process_identity(pid)
        if sys.platform == "darwin":
            result = subprocess.run(["ps", "-ww", "-p", str(pid), "-o", "stat=", "-o", "lstart=", "-o", "command="],
                                    capture_output=True, text=True, timeout=10, check=False,
                                    env={**os.environ, "LC_ALL": "C"})
            fields = result.stdout.strip().split(None, 6)
            if result.returncode != 0 or len(fields) != 7 or fields[0].startswith("Z"):
                return None
            return {"started": " ".join(fields[1:6]), "command": fields[6]}
        proc = Path("/proc") / str(pid)
        stat = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        if stat[0] == "Z":
            return None
        command = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        again = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        if not command or again[0] == "Z" or again[19] != stat[19]:
            return None
        return {"started": f"{boot}:{stat[19]}", "command": command}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def same_process(pid: int, identity: Any) -> bool:
    return (isinstance(identity, dict) and bool(identity.get("started"))
            and bool(identity.get("command")) and process_identity(pid) == identity)
