"""Native creation advances only a fresh linked worktree; no network or agents."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agents/lib"))
spec = importlib.util.spec_from_file_location("native_worktree_setup", ROOT / ".agents/scripts/vaws_worktree_setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def git(root, *args):
    result = subprocess.run(["git", "-c", "core.longpaths=true", "-C", str(root), *args], capture_output=True, text=True,
                            encoding="utf-8", env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"})
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def commit(root, message):
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts}


def make_repository(tmp_path, monkeypatch, *, submodule=False, detached=False, mock_update=True):
    source, target, stage = [tmp_path / name for name in ("source 用户", "native worktree", "prepared")]
    source.mkdir()
    git(source, "init", "-b", "main")
    (source / ".gitignore").write_text(".vaws-local/\nvllm/\nvllm-ascend/\n.claude/settings.local.json\n.mcp.json\n")
    (source / "README").write_text("old code\n")
    (source / "pyproject.toml").write_text("[tool.uv]\npackage = false\n")
    (source / "uv.lock").write_text("version = 1\n")
    old = commit(source, "old workspace")
    git(source, "worktree", "add", *(["--detach"] if detached else ["-b", "cursor/new-task"]), str(target), old)
    git(source, "clone", "--local", str(source), str(stage))
    (stage / "README").write_text("new code\n")
    (stage / "uv.lock").write_text("version = 1\n# new pinned components\n")
    new = commit(stage, "upstream workspace update")
    module_old = module_new = None
    if submodule:
        child = source / "vllm"
        child.mkdir()
        git(child, "init", "-b", "operator-work")
        (child / "operator.py").write_text("old operator\n")
        module_old = commit(child, "old operator")
        git(child, "clone", "--local", str(child), str(stage / "vllm"))
        (stage / "vllm/operator.py").write_text("new operator\n")
        module_new = commit(stage / "vllm", "new operator")
    receipt_old = {"key": "old-environment", "input_id": setup._inputs(source)[3],
                   "python": sys.executable, "receipt": str(tmp_path / "old-receipt.json")}
    receipt_new = {"key": "new-environment", "input_id": setup._inputs(stage)[3],
                   "python": sys.executable, "receipt": str(tmp_path / "new-receipt.json")}
    calls = {"prepare": [], "configure": [], "select": []}

    def prepare(path, baseline=None, **kwargs):
        calls["prepare"].append(path)
        return {"status": "ready", "target": new}, {"stage": str(stage),
            "sources": {"vllm": str(stage / "vllm")} if submodule else {},
            "revisions": {"workspace": new, **({"vllm": module_new} if submodule else {})}}

    def native(path):
        return receipt_new if setup._inputs(path)[3] == receipt_new["input_id"] else receipt_old

    def configure(client, path, receipt, environment, **options):
        calls["configure"].append({"client": client, "path": path, "receipt": receipt,
                                   "head": git(path, "rev-parse", "HEAD"), "env": environment, **options})

    def select(path, receipt):
        calls["select"].append((path, receipt))
        selection = path / ".vaws-local/environment-selection" / f"{sys.platform}.json"
        selection.parent.mkdir(parents=True, exist_ok=True)
        selection.write_text(json.dumps(receipt))

    def saved(path):
        selection = path / ".vaws-local/environment-selection" / f"{sys.platform}.json"
        if not selection.is_file():
            raise setup.EnvironmentError("not selected")
        return json.loads(selection.read_text())

    if mock_update:
        monkeypatch.setattr(setup, "prepare_canonical", prepare)
    monkeypatch.setattr(setup, "native_ready", native)
    monkeypatch.setattr(setup, "saved_ready", saved)
    monkeypatch.setattr(setup, "configure_target", configure)
    monkeypatch.setattr(setup, "select_environment", select)
    monkeypatch.setattr("vaws_local_owner.windows_mounted_workspace", lambda _: False)
    return SimpleNamespace(source=source, target=target, stage=stage, old=old, new=new,
                           module_old=module_old, module_new=module_new,
                           receipt_old=receipt_old, receipt_new=receipt_new, calls=calls)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    return make_repository(tmp_path, monkeypatch)


@pytest.mark.parametrize("client", ["codex", "cursor", "claude", "grok", "kimi"])
def test_native_parent_is_unchanged_and_actual_bundle_is_independent(tmp_path, monkeypatch, client):
    f = make_repository(tmp_path, monkeypatch, submodule=True)
    index = (f.source / ".git/index").read_bytes()
    result = setup.prepare_worktree(client, f.source, f.target)
    bundle = Path(result["workspace"])
    assert bundle != f.target and f.target not in bundle.parents
    assert result["native_workspace"] == str(f.target)
    assert result["project_root"] == str(f.source)
    assert result["native_cwd_changed"] is False
    assert result["head"] == f.new and result["environment"] == "new-environment"
    assert git(bundle, "branch", "--show-current") == git(f.target, "branch", "--show-current")
    assert git(f.target, "rev-parse", "HEAD") == git(f.source, "rev-parse", "HEAD") == f.old
    assert (f.source / ".git/index").read_bytes() == index
    assert git(bundle / "vllm", "rev-parse", "HEAD") == f.module_new
    assert git(f.source / "vllm", "rev-parse", "HEAD") == f.module_old
    assert result["sources"] == {"workspace": str(bundle), "vllm": str(bundle / "vllm")}
    assert all((Path(path) / ".git").is_dir() for path in result["sources"].values())
    assert f.calls["configure"][0]["path"] == bundle
    assert f.calls["select"] == [(bundle, f.receipt_new)]
    assert setup.read_preparation(f.target)["workspace"] == str(bundle)


def test_bundle_survives_native_remove_and_preparation_cache_removal(tmp_path, monkeypatch):
    import shutil
    f = make_repository(tmp_path, monkeypatch, submodule=True)
    result = setup.prepare_worktree("codex", f.source, f.target)
    bundle = Path(result["workspace"])
    git(f.source, "worktree", "remove", str(f.target))
    assert f.stage.resolve().parent == tmp_path.resolve()
    def writable_remove(function, path, error):
        os.chmod(path, 0o700)
        function(path)
    shutil.rmtree(f.stage, onerror=writable_remove)
    assert git(bundle, "rev-parse", "HEAD") == f.new
    assert git(bundle / "vllm", "rev-parse", "HEAD") == f.module_new
    (bundle / "vllm/operator.py").write_text("task operator edit\n")
    git(bundle / "vllm", "add", "operator.py")
    assert git(bundle / "vllm", "diff", "--cached")


def test_missing_native_target_is_direct_bundle_and_inherits_native_settings(fixture):
    f = fixture
    for name in (".claude/settings.local.json", ".mcp.json"):
        path = f.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"custom":true}')
    target = f.source.parent / "direct task"
    result = setup.prepare_worktree("claude", f.source, target)
    assert result["workspace"] == result["native_workspace"] == str(target)
    assert (target / ".git").is_dir()
    assert (target / ".claude/settings.local.json").read_text() == '{"custom":true}'
    assert (target / ".mcp.json").read_text() == '{"custom":true}'
    assert not (target / ".vaws-local/context.json").exists()


def test_new_missing_target_checks_canonical_despite_initialized_source_pin(fixture):
    f = fixture
    setup.select_environment(f.source, f.receipt_old)
    result = setup.prepare_worktree("kimi", f.source, f.source.parent / "new task")
    assert result["head"] == f.new and result["environment"] == "new-environment"
    assert f.calls["prepare"] == [f.source]
    assert f.calls["configure"][-1]["receipt"] == f.receipt_new
    assert setup.saved_ready(f.source) == f.receipt_old


def test_repeat_is_read_only_and_keeps_selected_environment(fixture, monkeypatch):
    f = fixture
    first = setup.prepare_worktree("cursor", f.source, f.target)
    bundle = Path(first["workspace"])
    (bundle / "uv.lock").write_text("invalid user draft\n")
    monkeypatch.setattr(setup, "prepare_canonical", lambda *a, **k: pytest.fail("resume checked upstream"))
    monkeypatch.setattr(setup, "configure_target", lambda *a: pytest.fail("resume reconfigured client"))
    monkeypatch.setattr(setup, "native_ready", lambda *a: pytest.fail("resume resolved package inputs"))
    monkeypatch.setattr(setup, "select_environment", lambda *a: pytest.fail("resume wrote selection"))
    second = setup.prepare_worktree("cursor", f.source, f.target)
    assert second["status"] == "reused" and second["workspace"] == str(bundle)
    assert second["environment"] == "new-environment"


@pytest.mark.parametrize("phase", ["copy_child", "configure", "select"])
def test_partial_preparation_never_publishes_ready(tmp_path, monkeypatch, phase):
    import vaws_native_workspace as copy
    f = make_repository(tmp_path, monkeypatch, submodule=True)
    if phase == "copy_child":
        original = copy.prepare_source
        def fail(destination, **options):
            if destination.name == "vllm":
                raise RuntimeError("injected child failure")
            return original(destination, **options)
        monkeypatch.setattr(copy, "prepare_source", fail)
    else:
        monkeypatch.setattr(setup, "configure_target" if phase == "configure" else "select_environment",
                            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("injected failure")))
    with pytest.raises(RuntimeError, match="injected"):
        setup.prepare_worktree("cursor", f.source, f.target)
    assert setup.read_preparation(f.target) is None
    assert git(f.target, "rev-parse", "HEAD") == f.old
    assert git(f.source / "vllm", "rev-parse", "HEAD") == f.module_old
    assert not list(tmp_path.glob("*-vaws-*/.vaws-local/native-workspace.json"))


def test_failed_independent_target_is_preserved_and_cannot_become_native_input(fixture, monkeypatch):
    f = fixture
    target = f.source.parent / "failed task"
    monkeypatch.setattr(setup, "configure_target", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("wiring failed")))
    with pytest.raises(RuntimeError, match="wiring failed"):
        setup.prepare_worktree("claude", f.source, target)
    (target / "user-draft.txt").write_text("keep this failed preparation for diagnosis")
    with pytest.raises(ValueError, match="choose a new target"):
        setup.prepare_worktree("claude", f.source, target)
    assert (target / "user-draft.txt").read_text() == "keep this failed preparation for diagnosis"
    assert not (target / ".vaws-local/native-workspace.json").exists()


def test_dirty_native_tree_is_copied_with_existing_business_roots(tmp_path, monkeypatch):
    f = make_repository(tmp_path, monkeypatch, submodule=True)
    (f.target / "README").write_text("staged draft\n")
    git(f.target, "add", "README")
    (f.target / "README").write_text("working draft\n")
    result = setup.prepare_worktree("cursor", f.source, f.target)
    bundle = Path(result["workspace"])
    assert result["update"]["reason"] == "dirty_checkout"
    assert not f.calls["prepare"]
    assert git(bundle, "diff", "--cached") == git(f.target, "diff", "--cached")
    assert git(bundle, "diff") == git(f.target, "diff")
    assert git(bundle / "vllm", "rev-parse", "HEAD") == f.module_old
    assert result["environment"] == "old-environment"


def test_fork_uses_actual_selected_sources_and_saved_pin(tmp_path, monkeypatch):
    f = make_repository(tmp_path, monkeypatch, submodule=True)
    setup.write_preparation(f.source, project_root=f.source, native_workspace=f.source, workspace=f.source,
                            sources={"workspace": f.source, "vllm": f.source / "vllm"})
    f.calls["select"].clear()
    setup.select_environment(f.source, f.receipt_old)
    (f.source / "uv.lock").write_text("user changed lock, not a new runtime\n")
    (f.source / "vllm/operator.py").write_text("staged operator\n")
    git(f.source / "vllm", "add", "operator.py")
    (f.source / "vllm/operator.py").write_text("working operator\n")
    result = setup.prepare_worktree("kimi", f.source, tmp_path / "fork", preserve_source=True)
    bundle = Path(result["workspace"])
    assert result["head"] == f.old and result["environment"] == "old-environment"
    assert git(bundle / "vllm", "diff", "--cached") == git(f.source / "vllm", "diff", "--cached")
    assert git(bundle / "vllm", "diff") == git(f.source / "vllm", "diff")
    assert not f.calls["prepare"]


def test_root_only_selection_stays_root_only_even_if_ignored_repository_exists(tmp_path, monkeypatch):
    f = make_repository(tmp_path, monkeypatch, submodule=True)
    setup.write_preparation(f.source, project_root=f.source, native_workspace=f.source, workspace=f.source,
                            sources={"workspace": f.source})
    result = setup.prepare_worktree("kimi", f.source, tmp_path / "root only", preserve_source=True)
    assert list(result["sources"]) == ["workspace"]
    assert not (Path(result["workspace"]) / "vllm").exists()


def test_intervening_edit_keeps_old_code_and_environment(fixture, monkeypatch):
    f = fixture
    def prepare(*args, **kwargs):
        (f.target / "README").write_text("edited during preparation\n")
        return {"status": "ready"}, f.stage
    monkeypatch.setattr(setup, "prepare_canonical", prepare)
    result = setup.prepare_worktree("cursor", f.source, f.target)
    assert result["head"] == f.old and result["environment"] == "old-environment"
    assert result["update"]["reason"] == "dirty_checkout"
    assert (Path(result["workspace"]) / "README").read_text() == "edited during preparation\n"


def test_explicit_older_native_revision_keeps_actual_code(fixture):
    f = fixture
    result = setup.prepare_worktree("codex", f.stage, f.target)
    assert result["head"] == f.old and not f.calls["prepare"]


def test_canonical_preparation_uses_durable_owner_and_explicit_source_selection(fixture, monkeypatch):
    from contextlib import contextmanager
    f = fixture
    setup.write_preparation(f.stage, project_root=f.source, native_workspace=f.stage, workspace=f.stage,
                            sources={"workspace": f.stage})
    calls = []
    @contextmanager
    def lock(root, **options):
        calls.append(("lock", root))
        yield
    class Updater:
        def __init__(self, root, **options):
            calls.append(("updater", root, options))
            self.state = {"phase": "ready", "prepared": {"stage": str(f.stage), "sources": {},
                          "revisions": {"workspace": f.new}}}
        def step(self, **options):
            return {"status": "ready", "branch": "main"}
        def validate_prepared(self, *_):
            return f.stage
    monkeypatch.setattr(setup, "workspace_entry", lambda root: {"state": "configured"})
    monkeypatch.setattr(setup, "update_lock", lock)
    monkeypatch.setattr(setup, "WorkspaceUpdater", Updater)
    # Call the implementation; the shared fixture normally stubs canonical I/O.
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    monkeypatch.setattr(original, "workspace_entry", setup.workspace_entry)
    monkeypatch.setattr(original, "update_lock", lock)
    monkeypatch.setattr(original, "WorkspaceUpdater", Updater)
    result, prepared = original.prepare_canonical(f.stage, source_channel="release")
    assert result["status"] == "ready" and prepared["sources"] == {}
    assert calls == [("lock", f.source), ("updater", f.source, {"source_root": f.stage, "source_channel": "release"})]


def test_malformed_optional_identity_is_reported_without_losing_copy(fixture):
    f = fixture
    path = f.source / ".vaws-local/github.json"
    path.parent.mkdir()
    path.write_text("{invalid JSON")
    result = setup.prepare_worktree("cursor", f.source, f.target)
    assert result["status"] == "ready" and result["identity"]["status"] == "unavailable"


@pytest.mark.parametrize("client", ["codex", "cursor"])
def test_native_paths_accept_actual_linked_worktree(fixture, client):
    f = fixture
    env = ({"CODEX_SOURCE_TREE_PATH": str(f.source), "CODEX_WORKTREE_PATH": str(f.target)}
           if client == "codex" else {"ROOT_WORKTREE_PATH": str(f.source)})
    assert setup.native_paths(client, env, f.target) == (f.source, f.target)


@pytest.mark.parametrize("client,env", [("codex", {}), ("cursor", {}),
                                        ("codex", {"CODEX_SOURCE_TREE_PATH": "source"})])
def test_native_paths_require_native_environment(fixture, client, env):
    with pytest.raises(ValueError, match="missing"):
        setup.native_paths(client, env, fixture.target)


def test_main_checkout_cannot_be_native_target(fixture):
    f = fixture
    with pytest.raises(ValueError, match="main checkout"):
        setup.native_paths("cursor", {"ROOT_WORKTREE_PATH": str(f.target)}, f.source)
    with pytest.raises(ValueError, match="separate"):
        setup.native_paths("cursor", {"ROOT_WORKTREE_PATH": str(f.source)}, f.source)


def test_native_paths_reject_different_repository(fixture, tmp_path):
    other = tmp_path / "unrelated"
    other.mkdir()
    git(other, "init", "-b", "main")
    with pytest.raises(ValueError, match="same Git"):
        setup.native_paths("cursor", {"ROOT_WORKTREE_PATH": str(other)}, fixture.target)


def test_mounted_windows_worktree_requires_native_owner(fixture, monkeypatch):
    monkeypatch.setattr("vaws_local_owner.windows_mounted_workspace", lambda _: True)
    with pytest.raises(ValueError, match="Windows owner"):
        setup.prepare_worktree("cursor", fixture.source, fixture.target)
    assert not fixture.calls["prepare"]


def test_ready_fallback_prepares_packages_only_without_parent_pins(fixture, monkeypatch):
    f = fixture
    monkeypatch.setenv(setup.PIN_ENV, "parent-environment")
    monkeypatch.setenv("VAWS_CONTEXT_FILE", "parent-task")
    monkeypatch.setattr(setup, "native_ready", lambda _: (_ for _ in ()).throw(setup.EnvironmentError("missing")))
    calls = []
    monkeypatch.setattr(setup, "run", lambda argv, **kwargs: calls.append((argv, kwargs)) or
                        SimpleNamespace(stdout=json.dumps({"receipt": f.receipt_old})))
    assert setup.ready_for_target(f.source, f.target, setup.unpinned_environment()) == f.receipt_old
    argv, options = calls[0]
    assert argv[-2:] == ["sync", "--locked"]
    assert options["cwd"] == f.target
    assert setup.PIN_ENV not in options["env"] and "VAWS_CONTEXT_FILE" not in options["env"]
