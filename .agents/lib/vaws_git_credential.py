"""Git credential protocol only: read a GitHub PAT from this process's environment.

This helper intentionally has no diagnostics or normal CLI output. Its stdout is
Git's private credential pipe, never a user-visible diagnostic channel.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    if sys.argv[1:] != ["get"]:
        return 0  # store/erase never persist or remove the supplied credential.
    raw = sys.stdin.buffer.read(16 * 1024 + 1)
    if len(raw) > 16 * 1024:
        return 1
    values = {}
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line:
            break
        name, separator, value = line.partition("=")
        if separator:
            values[name] = value
    if values.get("protocol") != "https" or values.get("host") != "github.com":
        return 0
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token or any(character.isspace() or ord(character) < 32 for character in token):
        return 0
    sys.stdout.write("username=x-access-token\npassword=" + token + "\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
