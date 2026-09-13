"""Split optional knowledge dependencies without adding a client setup choice.

uv.lock remains the resolver. Each environment installs an exact, conservative
dependency closure from that lock; a tiny immutable selection pins both owners.
Explicit development groups retain a complete environment for in-process tests.
"""
from __future__ import annotations

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
