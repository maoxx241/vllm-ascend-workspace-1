"""Source declarations are exact Git objects, never inferred from image tags."""
from __future__ import annotations

import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
import vaws_source_lock as sources

ASCEND = "a" * 40
DEVELOPMENT = "b" * 40
RELEASE = "c" * 40
ANNOTATION = "d" * 40
TAG = "v0.28.0"


def lock():
    return {"schema_version": 1,
            "vllm-ascend": {"repository": sources.ASCEND_REPOSITORY, "revision": ASCEND},
            "vllm": {"repository": sources.VLLM_REPOSITORY,
                     "development": {"revision": DEVELOPMENT},
                     "release": {"tag": TAG, "revision": RELEASE}}}


def encoded(path, text):
    return {"type": "file", "path": path, "encoding": "base64",
            "content": base64.b64encode(text.encode()).decode()}


class Upstream:
    def __init__(self):
        self.calls = []
        ascend = f"repos/{sources.ASCEND_REPOSITORY}"
        vllm = f"repos/{sources.VLLM_REPOSITORY}"
        self.responses = {
            f"{ascend}/commits/main": {"sha": ASCEND},
            f"{ascend}/commits/{ASCEND}": {"sha": ASCEND},
            f"{ascend}/contents/{sources.MAIN_FILE}?ref={ASCEND}": encoded(sources.MAIN_FILE, DEVELOPMENT + "\n"),
            f"{ascend}/contents/{sources.RELEASE_FILE}?ref={ASCEND}": encoded(sources.RELEASE_FILE, TAG + "\n"),
            f"{vllm}/commits/{DEVELOPMENT}": {"sha": DEVELOPMENT},
            f"{vllm}/commits/{RELEASE}": {"sha": RELEASE},
            f"{vllm}/git/ref/tags/{TAG}": {"ref": f"refs/tags/{TAG}",
                                          "object": {"type": "commit", "sha": RELEASE}},
        }

    def api(self, endpoint):
        self.calls.append(endpoint)
        response = deepcopy(self.responses[endpoint])
        # Simulate main moving as soon as its HEAD was read.
        if endpoint.endswith("/commits/main"):
            self.responses[endpoint] = {"sha": "e" * 40}
        return response


def test_refresh_freezes_ascend_once_and_resolves_both_official_baselines():
    upstream = Upstream()
    assert sources.refresh_source_lock(client=upstream) == lock()
    assert len([call for call in upstream.calls if call.endswith("/commits/main")]) == 1
    content_calls = [call for call in upstream.calls if "/contents/" in call]
    assert len(content_calls) == 2 and all(call.endswith(f"?ref={ASCEND}") for call in content_calls)
    assert all(call.startswith("repos/vllm-project/") for call in upstream.calls)


def test_explicit_ascend_commit_never_resolves_main():
    upstream = Upstream()
    assert sources.refresh_source_lock(client=upstream, ascend_commit=ASCEND) == lock()
    assert not any(call.endswith("/main") for call in upstream.calls)


def test_annotated_release_tag_is_peeled_through_immutable_objects():
    upstream = Upstream()
    prefix = f"repos/{sources.VLLM_REPOSITORY}/git"
    upstream.responses[f"{prefix}/ref/tags/{TAG}"]["object"] = {"type": "tag", "sha": ANNOTATION}
    upstream.responses[f"{prefix}/tags/{ANNOTATION}"] = {
        "sha": ANNOTATION, "object": {"type": "commit", "sha": RELEASE}}
    assert sources.refresh_source_lock(client=upstream) == lock()
    assert f"{prefix}/tags/{ANNOTATION}" in upstream.calls


@pytest.mark.parametrize("value", ["main", "b" * 7, "B" * 40, "b" * 40 + "\nmain", "$(bad)"])
def test_invalid_development_declaration_is_rejected_without_fallback(value):
    upstream = Upstream()
    endpoint = f"repos/{sources.ASCEND_REPOSITORY}/contents/{sources.MAIN_FILE}?ref={ASCEND}"
    upstream.responses[endpoint] = encoded(sources.MAIN_FILE, value)
    with pytest.raises(sources.SourceLockError):
        sources.refresh_source_lock(client=upstream)
    assert not any("workflows" in call or "Dockerfile" in call or "/docs/" in call for call in upstream.calls)


@pytest.mark.parametrize("value", ["main", "releases-v0.13.0", "v0.28.0/other", "v0.28.0;bad", ""])
def test_image_names_or_ambiguous_release_refs_are_rejected(value):
    upstream = Upstream()
    endpoint = f"repos/{sources.ASCEND_REPOSITORY}/contents/{sources.RELEASE_FILE}?ref={ASCEND}"
    upstream.responses[endpoint] = encoded(sources.RELEASE_FILE, value)
    with pytest.raises(sources.SourceLockError):
        sources.refresh_source_lock(client=upstream)


@pytest.mark.parametrize("fault", ["missing", "wrong_path", "symlink", "encoding", "invalid_base64", "too_large"])
def test_invalid_declaration_response_is_not_interpreted_as_a_pin(fault):
    upstream = Upstream()
    endpoint = f"repos/{sources.ASCEND_REPOSITORY}/contents/{sources.MAIN_FILE}?ref={ASCEND}"
    response = upstream.responses[endpoint]
    if fault == "missing":
        upstream.responses[endpoint] = {"message": "Not Found"}
    elif fault == "wrong_path":
        response["path"] = sources.RELEASE_FILE
    elif fault == "symlink":
        response["type"] = "symlink"
    elif fault == "encoding":
        response["encoding"] = "utf-8"
    elif fault == "invalid_base64":
        response["content"] = "!invalid!"
    else:
        response["content"] = "a" * 1025
    with pytest.raises(sources.SourceLockError):
        sources.refresh_source_lock(client=upstream)


@pytest.mark.parametrize("fault", ["wrong_ref", "tree", "cycle", "wrong_commit", "wrong_annotation"])
def test_release_tag_must_resolve_to_the_requested_commit(fault):
    upstream = Upstream()
    prefix = f"repos/{sources.VLLM_REPOSITORY}"
    response = upstream.responses[f"{prefix}/git/ref/tags/{TAG}"]
    if fault == "wrong_ref":
        response["ref"] = "refs/heads/" + TAG
    elif fault == "tree":
        response["object"]["type"] = "tree"
    elif fault == "wrong_commit":
        upstream.responses[f"{prefix}/commits/{RELEASE}"]["sha"] = DEVELOPMENT
    else:
        response["object"] = {"type": "tag", "sha": ANNOTATION}
        upstream.responses[f"{prefix}/git/tags/{ANNOTATION}"] = {
            "sha": ANNOTATION if fault == "cycle" else RELEASE,
            "object": {"type": "tag", "sha": ANNOTATION}}
    with pytest.raises(sources.SourceLockError):
        sources.refresh_source_lock(client=upstream)


def test_local_selection_is_offline_and_preserves_one_ascend_revision(tmp_path, monkeypatch):
    sources.write_source_lock(tmp_path, lock())
    def forbidden(*args, **kwargs):
        pytest.fail("reading an existing source lock must not launch a process")
    monkeypatch.setattr(subprocess, "run", forbidden)
    development = sources.selected_sources(tmp_path)
    release = sources.selected_sources(tmp_path, "release")
    assert set(development) == {"vllm", "vllm-ascend"}
    assert development["vllm-ascend"] == release["vllm-ascend"] == lock()["vllm-ascend"]
    assert development["vllm"]["revision"] == DEVELOPMENT
    assert release["vllm"]["revision"] == RELEASE


@pytest.mark.parametrize("fault", ["unknown_repo", "path", "short_sha", "unknown_key", "schema_bool", "missing_release"])
def test_lock_rejects_unsafe_or_incomplete_inputs(tmp_path, fault):
    value = lock()
    if fault == "unknown_repo":
        value["vllm"]["repository"] = "other/vllm"
    elif fault == "path":
        value["../vllm"] = value.pop("vllm")
    elif fault == "short_sha":
        value["vllm-ascend"]["revision"] = "a" * 7
    elif fault == "unknown_key":
        value["validated_on_npu"] = True
    elif fault == "schema_bool":
        value["schema_version"] = True
    else:
        value["vllm"].pop("release")
    with pytest.raises(sources.SourceLockError):
        sources.write_source_lock(tmp_path, value)
    assert not (tmp_path / sources.LOCK_NAME).exists()


def test_missing_duplicate_and_invalid_channel_do_not_scan_old_checkout(tmp_path):
    (tmp_path / "vllm-ascend").mkdir()
    with pytest.raises(sources.SourceLockError):
        sources.selected_sources(tmp_path)
    target = tmp_path / sources.LOCK_NAME
    target.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(sources.SourceLockError, match="duplicate"):
        sources.load_source_lock(tmp_path)
    with pytest.raises(sources.SourceLockError, match="channel"):
        sources.selected_sources(tmp_path, "latest")


def test_lock_refresh_is_atomic_and_noop_retains_mtime(tmp_path, monkeypatch):
    target = tmp_path / sources.LOCK_NAME
    assert sources.write_source_lock(tmp_path, lock())
    before = target.read_bytes(), target.stat().st_mtime_ns
    assert not sources.write_source_lock(tmp_path, lock())
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before
    updated = lock()
    updated["vllm-ascend"]["revision"] = "e" * 40
    def interrupted(*args):
        raise OSError("simulated replacement interruption")
    monkeypatch.setattr(sources.os, "replace", interrupted)
    with pytest.raises(OSError):
        sources.write_source_lock(tmp_path, updated)
    assert target.read_bytes() == before[0]
    assert list(tmp_path.iterdir()) == [target]


def test_cli_show_needs_no_installed_packages_or_github(tmp_path):
    sources.write_source_lock(tmp_path, lock())
    result = subprocess.run([sys.executable, "-S", str(ROOT / ".agents/scripts/workspace_sources.py"),
                             "--root", str(tmp_path), "show", "--channel", "release"],
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["sources"]["vllm"]["revision"] == RELEASE
    assert payload["channel"] == "release"


def test_cli_failed_refresh_preserves_previous_lock(tmp_path, monkeypatch, capsys):
    path = ROOT / ".agents/scripts/workspace_sources.py"
    spec = importlib.util.spec_from_file_location("source_lock_cli_test", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    sources.write_source_lock(tmp_path, lock())
    before = (tmp_path / sources.LOCK_NAME).read_bytes()
    def failed(**kwargs):
        raise sources.SourceLockError("upstream declaration is missing")
    monkeypatch.setattr(cli, "refresh_source_lock", failed)
    assert cli.main(["--root", str(tmp_path), "refresh"]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False
    assert (tmp_path / sources.LOCK_NAME).read_bytes() == before


def maintenance_pr():
    canonical = {"full_name": "vllm-ascend-workspace/vllm-ascend-workspace"}
    return {"state": "open", "merged": False, "draft": False, "changed_files": 1,
            "base": {"ref": "main", "repo": dict(canonical)},
            "head": {"ref": "codex/update-source-lock", "sha": DEVELOPMENT, "repo": dict(canonical)}}, [
                {"filename": "sources.lock.json", "status": "modified"}]


def test_source_update_body_links_declarations_at_the_locked_ascend_commit():
    body = sources.source_update_pr_body(lock())
    assert f"/blob/{ASCEND}/{sources.MAIN_FILE}#L1" in body
    assert f"/blob/{ASCEND}/{sources.RELEASE_FILE}#L1" in body
    assert f"/commit/{DEVELOPMENT}" in body and f"/commit/{RELEASE}" in body
    assert "/blob/main/" not in body


def test_source_update_policy_accepts_the_exact_canonical_data_only_commit():
    pr, files = maintenance_pr()
    assert sources.source_update_pr_matches(pr, files, DEVELOPMENT)


@pytest.mark.parametrize("fault", ["wrong_head", "closed", "merged", "draft", "missing_field", "boolean_count",
                                  "wrong_base", "wrong_branch", "fork_base", "fork_head", "missing_repo",
                                  "more_files", "partial_files", "wrong_file", "renamed", "added", "no_files"])
def test_source_update_policy_rejects_changed_or_non_data_prs(fault):
    pr, files = maintenance_pr()
    if fault == "wrong_head":
        pr["head"]["sha"] = RELEASE
    elif fault == "closed":
        pr["state"] = "closed"
    elif fault in {"merged", "draft"}:
        pr[fault] = True
    elif fault == "missing_field":
        pr.pop("merged")
    elif fault == "boolean_count":
        pr["changed_files"] = True
    elif fault == "wrong_base":
        pr["base"]["ref"] = "release"
    elif fault == "wrong_branch":
        pr["head"]["ref"] = "contributor/source-update"
    elif fault in {"fork_base", "fork_head"}:
        pr[fault[5:]]["repo"]["full_name"] = "someone/vllm-ascend-workspace"
    elif fault == "missing_repo":
        pr["head"]["repo"] = None
    elif fault == "more_files":
        files.append({"filename": ".github/workflows/skill-catalog.yml", "status": "modified"})
    elif fault == "partial_files":
        pr["changed_files"] = 101
    elif fault == "wrong_file":
        files[0]["filename"] = ".agents/lib/vaws_source_lock.py"
    elif fault == "renamed":
        files[0]["previous_filename"] = "malicious.py"
    elif fault == "added":
        files[0]["status"] = "added"
    else:
        files = []
    assert not sources.source_update_pr_matches(pr, files, DEVELOPMENT)


def test_source_update_policy_rejects_non_exact_test_commit():
    pr, files = maintenance_pr()
    with pytest.raises(sources.SourceLockError):
        sources.source_update_pr_matches(pr, files, "main")
