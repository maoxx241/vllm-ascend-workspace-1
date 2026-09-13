"""Exact upstream-declared source baselines; reading a lock never uses the network.

The release choice selects a vLLM baseline for the same Ascend commit. These
declarations are not a record of NPU validation or a version compatibility range.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path
import re
import tempfile

LOCK_NAME = "sources.lock.json"
ASCEND_REPOSITORY = "vllm-project/vllm-ascend"
VLLM_REPOSITORY = "vllm-project/vllm"
MAIN_FILE = ".github/vllm-main-verified.commit"
RELEASE_FILE = ".github/vllm-release-tag.commit"
CHANNELS = ("development", "release")
SHA = re.compile(r"[0-9a-f]{40}")
TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[.-][A-Za-z0-9]+)*")


class SourceLockError(ValueError):
    """The declared source inputs are missing, ambiguous or invalid."""


def _revision(value, field: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise SourceLockError(f"{field} must be a full lowercase Git commit SHA")
    return value


def _tag(value) -> str:
    if not isinstance(value, str) or not TAG.fullmatch(value):
        raise SourceLockError("vLLM release must name an explicit version tag")
    return value


def _keys(value, expected: set[str], field: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise SourceLockError(f"{field} has missing or unsupported fields")
    return value


def validate_source_lock(value) -> dict:
    """Validate and return a normalized lock with only the two canonical names."""
    _keys(value, {"schema_version", "vllm-ascend", "vllm"}, LOCK_NAME)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise SourceLockError("unsupported source lock schema_version")
    ascend = _keys(value["vllm-ascend"], {"repository", "revision"}, "vllm-ascend")
    vllm = _keys(value["vllm"], {"repository", "development", "release"}, "vllm")
    if ascend["repository"] != ASCEND_REPOSITORY or vllm["repository"] != VLLM_REPOSITORY:
        raise SourceLockError("source repositories must be the canonical vllm-project repositories")
    development = _keys(vllm["development"], {"revision"}, "vllm.development")
    release = _keys(vllm["release"], {"tag", "revision"}, "vllm.release")
    return {
        "schema_version": 1,
        "vllm-ascend": {"repository": ASCEND_REPOSITORY,
                        "revision": _revision(ascend["revision"], "vllm-ascend.revision")},
        "vllm": {"repository": VLLM_REPOSITORY,
                 "development": {"revision": _revision(development["revision"], "vllm.development.revision")},
                 "release": {"tag": _tag(release["tag"]),
                             "revision": _revision(release["revision"], "vllm.release.revision")}},
    }


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SourceLockError("duplicate source lock field")
        value[key] = item
    return value


def load_source_lock(root: Path) -> dict:
    """Read a committed lock locally; never scan repositories or resolve refs."""
    try:
        value = json.loads((Path(root) / LOCK_NAME).read_text(encoding="utf-8"),
                           object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceLockError(f"cannot read {LOCK_NAME}: {type(exc).__name__}") from exc
    return validate_source_lock(value)


def selected_sources(root: Path, channel: str = "development") -> dict[str, dict[str, str]]:
    """Return canonical directory names, repositories and immutable revisions.

    ``channel`` chooses vLLM's development or release baseline for one Ascend
    revision. Materialization and actual source paths belong to the caller.
    """
    if channel not in CHANNELS:
        raise SourceLockError("source channel must be development or release")
    lock = load_source_lock(root)
    return {
        "vllm": {"repository": VLLM_REPOSITORY, "revision": lock["vllm"][channel]["revision"]},
        "vllm-ascend": dict(lock["vllm-ascend"]),
    }


def write_source_lock(root: Path, value: dict) -> bool:
    """Atomically replace only the lock, preserving it on validation failure."""
    rendered = json.dumps(validate_source_lock(value), indent=2, ensure_ascii=False) + "\n"
    target = Path(root) / LOCK_NAME
    if target.exists() and target.read_text(encoding="utf-8") == rendered:
        return False
    descriptor, temporary = tempfile.mkstemp(prefix=f".{LOCK_NAME}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def _commit(client, repository: str, ref: str) -> str:
    result = client.api(f"repos/{repository}/commits/{ref}")
    revision = _revision(result.get("sha"), f"{repository} commit")
    if SHA.fullmatch(ref) and revision != ref:
        raise SourceLockError("GitHub resolved a different commit than requested")
    return revision


def _declaration(client, ascend_commit: str, path: str) -> str:
    result = client.api(f"repos/{ASCEND_REPOSITORY}/contents/{path}?ref={ascend_commit}")
    content = result.get("content")
    if (result.get("type") != "file" or result.get("path") != path
            or result.get("encoding") != "base64" or not isinstance(content, str)
            or len(content) > 1024):
        raise SourceLockError(f"invalid upstream declaration file: {path}")
    try:
        return base64.b64decode("".join(content.split()), validate=True).decode("utf-8").strip()
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise SourceLockError(f"cannot decode upstream declaration: {path}") from exc


def _release_commit(client, tag: str) -> str:
    result = client.api(f"repos/{VLLM_REPOSITORY}/git/ref/tags/{tag}")
    if result.get("ref") != f"refs/tags/{tag}":
        raise SourceLockError("GitHub did not return the requested vLLM tag")
    target = result.get("object")
    seen = set()
    for _ in range(8):
        if not isinstance(target, dict):
            raise SourceLockError("vLLM release tag has an invalid Git object")
        revision = _revision(target.get("sha"), "vLLM release tag object")
        if revision in seen:
            raise SourceLockError("vLLM release tag contains an object cycle")
        seen.add(revision)
        if target.get("type") == "commit":
            return _commit(client, VLLM_REPOSITORY, revision)
        if target.get("type") != "tag":
            raise SourceLockError("vLLM release tag does not resolve to a commit")
        annotated = client.api(f"repos/{VLLM_REPOSITORY}/git/tags/{revision}")
        if annotated.get("sha") != revision:
            raise SourceLockError("GitHub returned a different annotated tag object")
        target = annotated.get("object")
    raise SourceLockError("vLLM release tag nesting exceeds the supported bound")


def refresh_source_lock(*, client=None, ascend_commit: str | None = None) -> dict:
    """Resolve both declarations from one Ascend commit during explicit maintenance.

    No workflow, Dockerfile, documentation or installed-package fallback is used.
    This reads official declarations and Git objects, not NPU test results.
    """
    if ascend_commit is not None:
        _revision(ascend_commit, "requested Ascend commit")
    if client is None:
        from vaws_github import GitHubClient
        client = GitHubClient()
    ascend = _commit(client, ASCEND_REPOSITORY, ascend_commit or "main")
    development = _revision(_declaration(client, ascend, MAIN_FILE), "verified vLLM declaration")
    release = _tag(_declaration(client, ascend, RELEASE_FILE))
    development = _commit(client, VLLM_REPOSITORY, development)
    release_revision = _release_commit(client, release)
    return validate_source_lock({
        "schema_version": 1,
        "vllm-ascend": {"repository": ASCEND_REPOSITORY, "revision": ascend},
        "vllm": {"repository": VLLM_REPOSITORY, "development": {"revision": development},
                 "release": {"tag": release, "revision": release_revision}},
    })


def source_update_pr_body(value: dict) -> str:
    """Make a reviewable maintenance description with links at the locked SHA."""
    lock = validate_source_lock(value)
    ascend = lock["vllm-ascend"]["revision"]
    development = lock["vllm"]["development"]["revision"]
    release = lock["vllm"]["release"]
    upstream = f"https://github.com/{ASCEND_REPOSITORY}"
    vllm = f"https://github.com/{VLLM_REPOSITORY}"
    return f"""Refresh `sources.lock.json` from one fixed upstream Ascend commit.

| Source baseline | Exact Git commit |
| --- | --- |
| Ascend | [{ascend}]({upstream}/commit/{ascend}) |
| vLLM development (default) | [{development}]({vllm}/commit/{development}) |
| vLLM release {release['tag']} | [{release['revision']}]({vllm}/commit/{release['revision']}) |

The [development declaration]({upstream}/blob/{ascend}/{MAIN_FILE}#L1) and
[release declaration]({upstream}/blob/{ascend}/{RELEASE_FILE}#L1) were read from
that same Ascend commit. The release choice uses the same Ascend source revision.

The maintenance workflow runs the existing Linux, Windows and macOS local CI
against the exact PR head before an enabled automatic merge policy can proceed.
These declarations and CPU checks do not establish NPU correctness, performance,
or complete runtime compatibility.

Scheduled maintenance updates this same PR and never runs during ordinary tasks.
GitHub's required checks and branch protections still apply to merging.
"""


def source_update_pr_matches(pr: dict, files: list, expected_head: str) -> bool:
    """Check the data-only PR boundary before CI and immediately before merge.

    CI success comes from the reusable validation job dependency, not polling
    historical runs. GitHub enforces required checks and branch protections.
    """
    _revision(expected_head, "source update PR head")
    canonical = "vllm-ascend-workspace/vllm-ascend-workspace"
    if (not isinstance(pr, dict) or pr.get("state") != "open"
            or pr.get("merged") is not False or pr.get("draft") is not False
            or type(pr.get("changed_files")) is not int or pr["changed_files"] != 1):
        return False
    for side, branch in (("base", "main"), ("head", "codex/update-source-lock")):
        ref = pr.get(side)
        if (not isinstance(ref, dict) or ref.get("ref") != branch
                or not isinstance(ref.get("repo"), dict)
                or ref["repo"].get("full_name") != canonical):
            return False
    if pr["head"].get("sha") != expected_head:
        return False
    return (isinstance(files, list) and len(files) == 1 and isinstance(files[0], dict)
            and files[0].get("filename") == LOCK_NAME and files[0].get("status") == "modified"
            and "previous_filename" not in files[0])
