"""Split optional knowledge dependencies without adding a client setup choice.

uv.lock remains the resolver. Each environment installs an exact, conservative
dependency closure from that lock; a tiny immutable selection pins both owners.
Explicit development groups retain a complete environment for in-process tests.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import tomllib


def _name(value):
    return re.sub(r"[-_.]+", "-", value).lower()


def enabled(document, selection):
    return (document.get("tool", {}).get("vaws", {}).get("environment", {}).get("split-knowledge") is True
            and selection.get("project", True) and not selection.get("groups"))


def plans(document, lock, selection):
    """Keep all platform alternatives, and only the extras reached by inputs."""
    from vaws_environment import EnvironmentError, _digest

    data = tomllib.loads(lock.decode("utf-8-sig"))
    packages = data.get("package", [])
    by_name = {}
    for package in packages:
        by_name.setdefault(_name(package["name"]), []).append(package)
    project_name = _name(document["project"]["name"])
    roots = by_name.get(project_name, [])
    if len(roots) != 1 or roots[0].get("source") != {"virtual": "."}:
        raise EnvironmentError("capability environments require one locked virtual project")
    root = roots[0]
    dependencies = list(root.get("dependencies", []))
    for extra in selection.get("extras", []):
        dependencies.extend(root.get("optional-dependencies", {}).get(extra, []))
    optional = [row for row in dependencies if _name(row["name"]) == "vaws-knowledge"]
    if not optional:
        raise EnvironmentError("knowledge environment has no locked vaws-knowledge dependency")
    runtime = [row for row in dependencies if _name(row["name"]) != "vaws-knowledge"]
    knowledge = [*optional, *[row for row in runtime if _name(row["name"]) == "mcp"]]
    result = {}
    for capability, pending in (("runtime", runtime), ("knowledge", knowledge)):
        queue = list(pending)
        visited, names = set(), set()
        while queue:
            edge = queue.pop()
            name = _name(edge["name"])
            extras = edge.get("extra", [])
            extras = [extras] if isinstance(extras, str) else extras
            marker = (name, tuple(sorted(extras)))
            if marker in visited:
                continue
            visited.add(marker)
            names.add(name)
            variants = by_name.get(name)
            if not variants:
                raise EnvironmentError(f"locked dependency {name!r} has no package")
            for package in variants:
                queue.extend(package.get("dependencies", []))
                for extra in extras:
                    queue.extend(package.get("optional-dependencies", {}).get(extra, []))
        selected = [package for package in packages if _name(package["name"]) in names]
        # Resolver policy is shared; unrelated source pins are not. A knowledge
        # upgrade therefore reuses exactly the same runtime dependency closure.
        uv = dict(document.get("tool", {}).get("uv", {}))
        uv["sources"] = {name: value for name, value in uv.get("sources", {}).items() if _name(name) in names}
        fingerprint = {"capability": capability, "roots": pending, "packages": selected,
                       "requires-python": document["project"]["requires-python"], "uv": uv,
                       "lock_version": data.get("version"), "lock_revision": data.get("revision")}
        result[capability] = {"input_id": _digest(fingerprint), "lock_sha256": _digest(selected),
                              "selection": {"groups": [], "extras": selection.get("extras", []),
                                            "project": True, "capability": capability},
                              "exclude": sorted(set(by_name) - names - {project_name})}
    return result


def bundle_selection(document, lock, selection, identity):
    from vaws_environment import _key

    base = {key: selection[key] for key in ("groups", "extras", "project")}
    components = plans(document, lock, base)
    return {**base, "layout": "capabilities-v1", "components": {
        name: _key(identity, plan["input_id"], plan["selection"]) for name, plan in components.items()}}


def save_bundle_inputs(root: Path, project: bytes, lock: bytes, catalog: bytes) -> dict:
    """Save the exact validated inputs before publishing a new bundle receipt."""
    from vaws_environment import EnvironmentError
    directory = root / "inputs"
    if root.resolve() != root.absolute() or directory.resolve() != directory.absolute():
        raise EnvironmentError("frozen capability inputs must not traverse a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, data in (("pyproject.toml", project), ("uv.lock", lock), ("knowledge-catalog.json", catalog)):
        path = directory / name
        if path.is_symlink():
            raise EnvironmentError("frozen capability input must not be a symlink")
        with path.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        result[name] = hashlib.sha256(data).hexdigest()
    return result


def frozen_bundle_inputs(receipt: dict):
    """Recover the original task's inputs, never the caller's current checkout."""
    from vaws_environment import EnvironmentError, READY_NAME, _access_path, _inputs
    expected = receipt.get("frozen_inputs")
    if not expected:
        raise EnvironmentError("legacy fixed selection has no saved knowledge inputs; restore its original ready "
                               "knowledge environment or prepare the original matching locked sources")
    root = _access_path(receipt["store"]) / receipt["key"]
    if _access_path(receipt["receipt"]).absolute() != (root / READY_NAME).absolute():
        raise EnvironmentError("fixed selection input root differs")
    directory = root / "inputs"
    if root.resolve() != root.absolute() or directory.resolve() != directory.absolute():
        raise EnvironmentError("frozen capability inputs must not traverse a symlink")
    try:
        if any((directory / name).is_symlink() for name in ("pyproject.toml", "uv.lock")):
            raise EnvironmentError("frozen capability input must not be a symlink")
        frozen = _inputs(directory)
        project, lock, document, input_id, lock_sha = frozen
        for name, data in (("pyproject.toml", project), ("uv.lock", lock)):
            if hashlib.sha256(data).hexdigest() != expected[name]:
                raise EnvironmentError("frozen capability input hash differs: " + name)
        if input_id != receipt["input_id"] or lock_sha != receipt["lock_sha256"]:
            raise EnvironmentError("frozen capability input identity differs")
        selected = bundle_selection(document, lock, receipt["selection"], receipt["python_identity"])
        if selected != receipt["selection"]:
            raise EnvironmentError("frozen capability closure differs from the task's fixed selection")
        return directory, frozen
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise EnvironmentError("cannot read the fixed knowledge preparation inputs: " + str(exc)) from exc
