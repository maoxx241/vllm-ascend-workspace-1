"""Real local Git selection and fork preservation, without network preparation."""
from pathlib import Path
import json
import pytest

from test_workspace_update import fixture, git, updater, commit
from test_native_workspace import repository
import vaws_workspace_update as updates
import vaws_native_workspace as copying
from test_vaws_start import workspace as startup_workspace, start
from test_native_worktree_setup import fixture as native_fixture, setup


def test_local_selection_and_cache_never_discover_or_fetch(fixture, monkeypatch):
    subject = updater(fixture)
    monkeypatch.setattr(subject, "discover", lambda: pytest.fail("local selection discovered upstream"))
    result, prepared = subject.local_prepare()
    assert result["status"] == "local" and result["target"] == fixture["old"]
    assert not result["upstream_checked"]
    assert not fixture["api"].calls
    assert not any("fetch" in call or "push" in call for call in fixture["calls"])
    fixture["calls"].clear()
    again, cached = updater(fixture).local_prepare()
    assert again["status"] == "cached" and cached == prepared
    assert fixture["prepares"] == [fixture["old"]]
    # One local HEAD selection plus two Git validation operations; no packages.
    assert len(fixture["calls"]) == 3
    assert all("fetch" not in call and "push" not in call for call in fixture["calls"])


def test_damaged_optional_cache_falls_back_to_local_without_overwriting(fixture):
    _, prepared = updater(fixture).local_prepare()
    stage = Path(prepared["stage"])
    (stage / "README").write_text("keep cache diagnosis")
    result, replacement = updater(fixture).local_prepare()
    assert result["status"] == "local" and "cache_rejected" in result
    assert Path(replacement["stage"]) != stage
    assert (stage / "README").read_text() == "keep cache diagnosis"
    assert git(Path(replacement["stage"]), "rev-parse", "HEAD") == fixture["old"]


def test_local_update_supersedes_valid_older_preparation(fixture):
    _, old = updater(fixture).local_prepare()
    newer = commit(fixture["root"], "new local feature already pulled")
    result, selected = updater(fixture).local_prepare()
    assert result["status"] == "local" and result["target"] == newer
    assert selected["revisions"]["workspace"] == newer
    assert selected["stage"] != old["stage"]
    assert not fixture["api"].calls


@pytest.mark.parametrize("activate", [False, True])
def test_explicit_latest_reuses_local_stage_then_completes_fork_update(fixture, activate):
    git(fixture["root"], "fetch", str(fixture["upstream"]), "stable")
    git(fixture["root"], "merge", "--ff-only", fixture["new"])
    _, prepared = updater(fixture).local_prepare()
    assert git(fixture["fork"], "rev-parse", "stable") == fixture["old"]
    subject = updater(fixture)
    result = subject.step(apply=True, activate=activate)
    assert result["status"] == ("applied" if activate else "ready"), result
    assert subject.state["prepared"] == prepared
    assert fixture["prepares"] == [fixture["new"]]
    assert git(fixture["fork"], "rev-parse", "stable") == fixture["new"]
    assert subject.state["branch"] == "stable"


def test_clean_validation_batches_branch_head_and_dirty_state(fixture):
    fixture["calls"].clear()
    facts = updates.clean_checkout(fixture["root"], branch="stable", expected={fixture["old"]})
    assert facts["head"] == fixture["old"]
    assert len(fixture["calls"]) == 2
    (fixture["root"] / "new.txt").write_text("draft")
    with pytest.raises(updates.Deferred, match="dirty_checkout"):
        updates.clean_checkout(fixture["root"], branch="stable")


def test_fork_preserves_all_refs_stash_history_branch_config_and_dirty_index(tmp_path):
    source = repository(tmp_path / "source")
    copying.git(source, "switch", "-c", "feature/current")
    copying.git(source, "branch", "feature/other")
    copying.git(source, "update-ref", "refs/private/review", "HEAD")
    copying.git(source, "remote", "add", "origin", "https://example.invalid/personal.git")
    copying.git(source, "config", "branch.feature/current.remote", "origin")
    copying.git(source, "config", "branch.feature/current.merge", "refs/heads/review")
    copying.git(source, "config", "branch.feature/current.pushRemote", "origin")
    for value in ("first stash\n", "second stash\n"):
        (source / "file.txt").write_text(value)
        copying.git(source, "stash", "push", "-m", value.strip())
    (source / "file.txt").write_text("staged\n")
    copying.git(source, "add", "file.txt")
    (source / "file.txt").write_text("working\n")
    before = {name: (source / ".git" / name).read_bytes() for name in ("HEAD", "index", "config", "logs/refs/stash")}
    target = tmp_path / "fork"
    copying.create_workspace(source, target)
    for name, value in before.items():
        assert (source / ".git" / name).read_bytes() == value
    assert copying.git(source, "show-ref") == copying.git(target, "show-ref")
    assert copying.git(source, "stash", "list") == copying.git(target, "stash", "list")
    assert copying.git(source, "stash", "show", "-p", "stash@{1}") == copying.git(target, "stash", "show", "-p", "stash@{1}")
    for key in ("remote", "merge", "pushRemote"):
        assert copying.git(source, "config", "--get-all", "branch.feature/current."+key) == copying.git(target, "config", "--get-all", "branch.feature/current."+key)
    assert not (target / ".git/objects/info/alternates").exists()
    (target / "file.txt").write_text("independent fork change\n")
    assert (source / "file.txt").read_text() == "working\n"


@pytest.mark.parametrize("push_setting", [None, "false"])
def test_prepared_new_repositories_have_ordinary_independent_task_branches(tmp_path, push_setting):
    from test_native_workspace import prepared_fixture
    prepared = prepared_fixture(tmp_path)
    for path in (Path(prepared["stage"]), Path(prepared["sources"]["vllm"])):
        copying.git(path, "remote", "add", "origin", "https://example.invalid/personal.git")
        if push_setting:
            copying.git(path, "config", "push.autoSetupRemote", push_setting)
    result = copying.create_prepared_workspace(prepared, tmp_path / "task")
    branches = {copying.git(Path(path), "branch", "--show-current").decode().strip() for path in result["sources"].values()}
    assert len(branches) == 1 and next(iter(branches)).startswith("codex/task-")
    assert all(value >= 0 for value in result["copy_seconds"].values())
    for path in result["sources"].values():
        assert copying.git(Path(path), "config", "push.autoSetupRemote").decode().strip() == (push_setting or "true")
        assert copying.git(Path(path), "remote", "get-url", "origin").decode().strip() == "https://example.invalid/personal.git"


@pytest.mark.parametrize("preferred, expected", [(None, "vllm-ascend"), ("workspace", "workspace")])
def test_new_focus_and_resume_use_the_selected_repo_without_moving_native_cwd(startup_workspace, monkeypatch, preferred, expected):
    project, stage, _, _, _, _, _, store = startup_workspace
    child = repository(stage / "vllm-ascend")
    original = start.WorkspaceUpdater.local_prepare
    def plan(self):
        update, prepared = original(self)
        return update, {**prepared, "sources": {"vllm-ascend": str(child)},
            "revisions": {**prepared["revisions"], "vllm-ascend": copying.git(child, "rev-parse", "HEAD").decode().strip()}}
    monkeypatch.setattr(start.WorkspaceUpdater, "local_prepare", plan)
    context = store.attach("codex", "focus", str(project))
    result = start.start("codex", project, context["context_file"], preferred=preferred)
    assert result["status"] == "ready", result
    assert result["repository"] == expected
    assert result["cwd"] == result["sources"][expected]
    assert result["native_cwd"] == str(project)
    repeated = start.start("codex", project, context["context_file"], preferred="workspace", latest=True)
    assert repeated["repository"] == expected and repeated["cwd"] == result["cwd"]
    record = Path(result["evidence"])
    legacy = json.loads(record.read_text(encoding="utf-8"))
    legacy.pop("cwd"); legacy.pop("repository")
    record.write_text(json.dumps(legacy), encoding="utf-8")
    old = start.start("codex", project, context["context_file"])
    assert old["status"] == "reused" and "cwd" not in old and "repository" not in old
    legacy.update(repository="vllm-ascend", cwd=str(project))
    record.write_text(json.dumps(legacy), encoding="utf-8")
    invalid = start.start("codex", project, context["context_file"])
    assert invalid["status"] == "failed" and invalid["phase"] == "reuse"


@pytest.mark.parametrize("preferred, expected", [(None, "vllm"), ("workspace", "workspace")])
def test_new_task_in_prepared_business_cwd_honors_actual_or_explicit_focus(startup_workspace, preferred, expected):
    project, stage, _, receipt, _, _, select, store = startup_workspace
    roots = {"workspace": str(stage)}
    for name in ("vllm", "vllm-ascend"):
        roots[name] = str(repository(stage / name))
    select(stage, receipt)
    preparation = start.write_preparation(stage, project_root=project, native_workspace=stage,
                                          workspace=stage, sources=roots)
    protected = [stage / ".vaws-local/native-workspace.json", Path(preparation["editor_workspace"])]
    before = {path: path.read_bytes() for path in protected}
    context = store.attach("codex", "new-child-task", str(stage / "vllm"))
    result = start.start("codex", project, context["context_file"], preferred=preferred)
    assert result["status"] == "ready" and result["preparation"] == "native", result
    assert result["repository"] == expected and result["cwd"] == roots[expected]
    view_path = Path(result["editor_workspace"])
    assert view_path.parent == stage / ".vaws-local/editor-workspaces"
    assert view_path != protected[1]
    view = json.loads(view_path.read_text(encoding="utf-8"))
    assert view["folders"][0]["name"] == expected
    assert (view_path.parent / view["folders"][0]["path"]).resolve() == Path(result["cwd"])
    assert {folder["name"] for folder in view["folders"]} == set(roots)
    assert view["settings"]["terminal.integrated.cwd"] == "${workspaceFolder:" + expected + "}"
    assert {path: path.read_bytes() for path in protected} == before
    assert store.context(context["attachment"]["id"])["attachment"]["cwd"] == str(stage / "vllm")


def test_two_native_tasks_keep_separate_editor_views_and_resume_their_original_focus(startup_workspace):
    project, stage, _, receipt, _, _, select, store = startup_workspace
    roots = {"workspace": str(stage)}
    for name in ("vllm", "vllm-ascend"):
        roots[name] = str(repository(stage / name))
    select(stage, receipt)
    preparation = start.write_preparation(stage, project_root=project, native_workspace=stage,
                                          workspace=stage, sources=roots)
    shared = [stage / ".vaws-local/native-workspace.json", Path(preparation["editor_workspace"])]
    before = {path: path.read_bytes() for path in shared}
    contexts = [store.attach("codex", "independent-focus-" + name, str(stage))
                for name in ("vllm", "workspace")]
    results = []
    for context, preferred in zip(contexts, ("vllm", "workspace")):
        result = start.start("codex", project, context["context_file"], preferred=preferred)
        assert result["status"] == "ready", result
        assert result["repository"] == preferred and result["cwd"] == roots[preferred]
        results.append(result)
    paths = [Path(result["editor_workspace"]) for result in results]
    assert paths[0] != paths[1]
    assert all(path.parent == stage / ".vaws-local/editor-workspaces" for path in paths)
    for path, result in zip(paths, results):
        view = json.loads(path.read_text(encoding="utf-8"))
        assert view["folders"][0]["name"] == result["repository"]
        assert (path.parent / view["folders"][0]["path"]).resolve() == Path(result["cwd"])
        assert view["settings"]["terminal.integrated.cwd"] == "${workspaceFolder:" + result["repository"] + "}"
    protected = [*shared, *paths, *(Path(result["evidence"]) for result in results)]
    saved = {path: path.read_bytes() for path in protected}
    assert {path: path.read_bytes() for path in shared} == before
    for context, first in zip(contexts, results):
        resumed = start.start("codex", project, context["context_file"], preferred="vllm-ascend", latest=True)
        assert resumed["status"] == "reused"
        for key in ("workspace", "repository", "cwd", "editor_workspace", "sources", "environment", "context_file"):
            assert resumed[key] == first[key]
    assert {path: path.read_bytes() for path in protected} == saved


@pytest.mark.parametrize("preferred", ["workspace", "vllm"])
def test_new_native_task_preserves_explicit_setup_focus_and_rejects_bad_receipt(startup_workspace, preferred):
    project, stage, _, receipt, _, _, select, store = startup_workspace
    roots = {"workspace": str(stage)}
    for name in ("vllm", "vllm-ascend"):
        roots[name] = str(repository(stage / name))
    select(stage, receipt)
    record = start.write_preparation(stage, project_root=project, native_workspace=stage, workspace=stage,
                                     sources=roots, preferred=preferred)
    context = store.attach("codex", "new-root-task", str(stage))
    result = start.start("codex", project, context["context_file"])
    assert result["status"] == "ready", result
    assert result["repository"] == preferred and result["cwd"] == roots[preferred]
    record.pop("cwd")
    (stage / ".vaws-local/native-workspace.json").write_text(json.dumps(record), encoding="utf-8")
    other = store.attach("codex", "another-root-task", str(stage))
    bad = start.start("codex", project, other["context_file"], preferred="workspace")
    assert bad["status"] == "failed" and "focus" in bad["error"]


@pytest.mark.parametrize("mode", ["reuse", "fork"])
@pytest.mark.parametrize("damage", ["partial", "mismatch", "legacy"])
def test_existing_and_forked_preparation_validate_saved_focus(native_fixture, mode, damage):
    f = native_fixture
    initial = setup.prepare_worktree("cursor", f.source, f.target)
    bundle = Path(initial["workspace"])
    receipt_root = f.target if mode == "reuse" else bundle
    path = receipt_root / ".vaws-local/native-workspace.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if damage == "mismatch":
        record["cwd"] = str(f.source)
    else:
        record.pop("cwd")
        if damage == "legacy":
            record.pop("repository")
    path.write_text(json.dumps(record), encoding="utf-8")
    target = f.target if mode == "reuse" else f.source.parent / "another-fork"
    def run():
        return setup.prepare_worktree("cursor", f.source if mode == "reuse" else bundle,
                                      target, preserve_source=mode == "fork")
    if damage == "legacy":
        result = run()
        assert result["repository"] == "workspace" and result["cwd"] == result["workspace"]
    else:
        with pytest.raises(ValueError, match="focus|cwd"):
            run()
        if mode == "fork":
            assert not target.exists()
