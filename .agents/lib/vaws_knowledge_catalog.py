"""Generated official tool descriptions; reading these never starts knowledge."""
from __future__ import annotations

import ast
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import tomllib

RELATIVE_PATH = Path(".agents/generated/knowledge-catalog.json")
FROZEN_NAME = "knowledge-catalog.json"


def locked_identity(lock: bytes) -> dict:
    rows = [row for row in tomllib.loads(lock.decode("utf-8-sig"))["package"]
            if row["name"].replace("_", "-") == "vaws-knowledge"]
    if len(rows) != 1:
        raise ValueError("knowledge catalog requires exactly one locked owner")
    row = rows[0]
    source = row["source"]
    revision = source.get("git", "").partition("#")[2] or None
    if "git" in source and (not revision or not re.fullmatch("[0-9a-f]{40}", revision)):
        raise ValueError("knowledge catalog requires a fixed Git revision")
    return {"name": "vaws-knowledge", "version": row["version"], "source": source, "revision": revision}


def validate_catalog(data: bytes, lock: bytes) -> dict:
    value = json.loads(data)
    if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("owner") != locked_identity(lock):
        raise ValueError("knowledge catalog differs from uv.lock; regenerate sync_knowledge_catalog.py")
    tools = value.get("tools")
    if (not isinstance(tools, list) or not tools
            or any(not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                   or not isinstance(tool.get("inputSchema"), dict) for tool in tools)
            or len({tool["name"] for tool in tools}) != len(tools)):
        raise ValueError("invalid generated knowledge catalog")
    return value


def generate_catalog(lock: bytes, distribution=None) -> bytes:
    """Extract literal TOOLS from the pinned installed package, without imports."""
    owner = locked_identity(lock)
    dist = distribution or metadata.distribution("vaws-knowledge")
    direct = json.loads(dist.read_text("direct_url.json") or "{}")
    if (dist.version != owner["version"]
            or (owner["revision"] and direct.get("vcs_info", {}).get("commit_id") != owner["revision"])):
        raise ValueError("installed knowledge does not match the locked catalog owner")
    path = dist.locate_file("vaws_knowledge/server/mcp_server.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    declarations = [node.value for node in tree.body
                    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                    and node.target.id == "TOOLS"]
    declarations += [node.value for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "TOOLS" for target in node.targets)]
    if len(declarations) != 1:
        raise ValueError("official knowledge TOOLS is not one literal declaration")
    tools = ast.literal_eval(declarations[0])
    data = (json.dumps({"schema_version": 1, "owner": owner, "tools": tools},
                       ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    validate_catalog(data, lock)
    return data


def frozen_catalog(receipt: dict) -> dict | None:
    """None denotes an older selection, whose ready backend remains authoritative."""
    if receipt.get("schema_version") != 2 or "knowledge_catalog_sha256" not in receipt:
        return None
    from vaws_environment import EnvironmentError
    from vaws_environment_capabilities import frozen_bundle_inputs
    directory, frozen = frozen_bundle_inputs(receipt)
    path = directory / FROZEN_NAME
    try:
        if path.is_symlink() or path.resolve() != path.absolute():
            raise ValueError("knowledge catalog path escapes fixed inputs")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != receipt["knowledge_catalog_sha256"]:
            raise ValueError("frozen knowledge catalog hash differs")
        return validate_catalog(data, frozen[1])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise EnvironmentError("cannot read fixed knowledge catalog: " + str(exc)) from exc
