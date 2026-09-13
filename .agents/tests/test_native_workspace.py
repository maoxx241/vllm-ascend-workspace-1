from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from vaws_native_workspace import WorkspaceCopyError, create_workspace, git
import vaws_native_workspace as workspace


def repository(path):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "Workspace Test")
    git(path, "config", "user.email", "workspace@example.invalid")
    (path / "file.txt").write_text("base\n", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-qm", "base")
    return path


def state(path):
    return (git(path, "rev-parse", "HEAD"), git(path, "diff", "--binary", "--cached"),
            git(path, "diff", "--binary"), git(path, "status", "--porcelain=v1", "-z"))


def test_explicit_business_roots_and_receipt_reuse_preserve_actual_edits(tmp_path):
    from vaws_workspace_entry import write_preparation
    source = repository(tmp_path / "project")
    (source / ".gitignore").write_text(".vaws-local/\nvllm/\n")
    git(source, "add", ".gitignore")
    git(source, "commit", "-qm", "source directories")
    child = repository(source / "vllm")
    (child / "file.txt").write_text("staged child\n")
    git(child, "add", "file.txt")
    (child / "file.txt").write_text("working child\n")
    (child / "untracked.txt").write_text("draft\n")
    write_preparation(source, project_root=source, native_workspace=source, workspace=source,
                      sources={"workspace": source, "vllm": child})
    copy = tmp_path / "copy"
    result = create_workspace(source, copy)
    assert result["sources"] == {"workspace": str(copy), "vllm": str(copy / "vllm")}
    assert state(copy / "vllm") == state(child)
    assert not (copy / ".vaws-local/native-workspace.json").exists()
    root_only = tmp_path / "root only"
    assert create_workspace(source, root_only, sources={})["sources"] == {"workspace": str(root_only)}
    assert not (root_only / "vllm").exists()


def test_locked_source_fetches_missing_commit_only_into_new_destination(tmp_path, monkeypatch):
    donor = repository(tmp_path / "canonical donor")
    source = tmp_path / "existing code"
    git(donor, "clone", "--local", str(donor), str(source))
    git(source, "remote", "set-url", "origin", "https://github.com/alice/vllm.git")
    before = state(source)
    (donor / "file.txt").write_text("new pinned version\n")
    git(donor, "commit", "-qam", "new version")
    revision = git(donor, "rev-parse", "HEAD").decode().strip()
    destination = tmp_path / "prepared"
    calls = []
    actual_git = workspace.git
    def local_git(root, *args, **options):
        if "fetch" in args:
            calls.append((root, args))
            assert root == destination
            args = tuple(str(donor) if value == "https://github.com/vllm-project/vllm.git" else value for value in args)
        return actual_git(root, *args, **options)
    monkeypatch.setattr(workspace, "git", local_git)
    workspace.prepare_source(destination, repository="vllm-project/vllm", revision=revision, local_source=source)
    assert len(calls) == 1 and calls[0][1][-1] == revision
    assert state(source) == before
    assert git(destination, "rev-parse", "HEAD").decode().strip() == revision
    assert git(destination, "remote", "get-url", "origin").strip() == b"https://github.com/alice/vllm.git"
    assert (destination / ".git").is_dir() and not (destination / ".git/objects/info/alternates").exists()


def test_locked_source_rejects_existing_destinations_and_object_alternates(tmp_path):
    source = repository(tmp_path / "source")
    revision = git(source, "rev-parse", "HEAD").decode().strip()
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "draft").write_text("keep")
    with pytest.raises(WorkspaceCopyError, match="already exists"):
        workspace.prepare_source(destination, repository="vllm-project/vllm", revision=revision, local_source=source)
    assert (destination / "draft").read_text() == "keep"
    alternate = tmp_path / "alternate"
    git(source, "clone", "--shared", str(source), str(alternate))
    with pytest.raises(WorkspaceCopyError, match="alternates"):
        workspace.prepare_source(tmp_path / "new", repository="vllm-project/vllm", revision=revision, local_source=alternate)
    assert not (tmp_path / "new").exists()


def test_clone_checkout_keeps_tracked_paths_longer_than_windows_max_path(tmp_path):
    source = repository(tmp_path / "source")
    relative = Path(*("long-header-path-" + str(i) * 32 for i in range(5))) / "tracked.h"
    header = source / relative
    header.parent.mkdir(parents=True)
    header.write_text("#define EXPECTED 1\n")
    git(source, "add", "--", relative.as_posix())
    git(source, "commit", "-qm", "long tracked header")
    target = tmp_path / "prepared checkout"
    revision = git(source, "rev-parse", "HEAD").decode().strip()
    workspace.prepare_source(target, repository="vllm-project/vllm", revision=revision, local_source=source)
    assert len(str(target / relative)) > 260
    assert (target / relative).read_text(encoding="utf-8") == header.read_text(encoding="utf-8")
    assert not git(target, "status", "--porcelain").strip()
    if os.name == "nt":
        assert git(target, "config", "--local", "core.longpaths").strip() == b"true"


def prepared_fixture(tmp_path):
    stage = repository(tmp_path / "stage")
    (stage / ".gitignore").write_text("vllm/\n.vaws-local/\n")
    git(stage, "add", ".gitignore")
    git(stage, "commit", "-qm", "source directories")
    child = repository(stage / "vllm")
    return {"stage": str(stage), "sources": {"vllm": str(child)},
            "revisions": {"workspace": git(stage, "rev-parse", "HEAD").decode().strip(),
                          "vllm": git(child, "rev-parse", "HEAD").decode().strip()}}


def test_prepared_copy_uses_fixed_commits_without_hashing_mutable_staging_files(tmp_path, monkeypatch):
    prepared = prepared_fixture(tmp_path)
    stage = Path(prepared["stage"])
    (stage / "file.txt").write_text("edited after validation\n")
    git(stage, "add", "file.txt")
    (stage / "vllm/file.txt").write_text("edited operator after validation\n")
    monkeypatch.setattr(workspace, "_capture", lambda _: pytest.fail("canonical clone scanned mutable editing state"))
    target = tmp_path / "task"
    result = workspace.create_prepared_workspace(prepared, target)
    assert result["head"] == prepared["revisions"]["workspace"]
    assert result["sources"] == {"workspace": str(target), "vllm": str(target / "vllm")}
    assert (target / "file.txt").read_text() == "base\n"
    assert (target / "vllm/file.txt").read_text() == "base\n"
    assert git(stage, "diff", "--cached") and git(stage / "vllm", "diff")
    assert (target / ".git").is_dir() and (target / "vllm/.git").is_dir()
    assert not (target / ".vaws-local/native-workspace.json").exists()


def test_prepared_clone_freezes_stage_checkout_policy_against_new_global_defaults(tmp_path, monkeypatch):
    prepared = prepared_fixture(tmp_path)
    stage = Path(prepared["stage"])
    for source in (stage, stage / "vllm"):
        git(source, "config", "--local", "core.autocrlf", "false")
        git(source, "config", "--local", "core.eol", "lf")
        git(source, "config", "--local", "core.safecrlf", "false")
        (source / "file.txt").write_bytes(b"base\n")
    global_config = tmp_path / "changed-global.gitconfig"
    global_config.write_text("[core]\n autocrlf = true\n eol = crlf\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    target = tmp_path / "task"
    workspace.create_prepared_workspace(prepared, target)
    for source, copied in ((stage, target), (stage / "vllm", target / "vllm")):
        assert (copied / "file.txt").read_bytes() == (source / "file.txt").read_bytes() == b"base\n"
        policy = workspace._checkout_configuration(workspace._configuration_entries(source))
        for key, value in policy.items():
            assert git(copied, "config", "--local", "--get", key).decode().strip() == value
        assert not git(copied, "status", "--porcelain").strip()


@pytest.mark.parametrize("failure", ["existing", "overlap", "missing_revision", "outside_source", "missing_source"])
def test_prepared_copy_rejects_incomplete_or_overlapping_inputs_before_clone(tmp_path, failure):
    prepared = prepared_fixture(tmp_path)
    target = tmp_path / "task"
    if failure == "existing":
        target.mkdir()
        (target / "keep.txt").write_text("keep")
    elif failure == "overlap":
        target = Path(prepared["stage"]) / ".vaws-local/task"
    elif failure == "missing_revision":
        prepared["revisions"].pop("vllm")
    elif failure == "outside_source":
        prepared["sources"]["vllm"] = str(repository(tmp_path / "other"))
    else:
        prepared["sources"]["vllm"] = str(tmp_path / "missing")
    with pytest.raises((WorkspaceCopyError, FileNotFoundError)):
        workspace.create_prepared_workspace(prepared, target)
    assert not (target / ".git").exists()
    if failure == "existing":
        assert (target / "keep.txt").read_text() == "keep"


def test_parallel_first_tools_have_independent_index_and_resume_cwd(tmp_path):
    source = repository(tmp_path / "source 空格")
    (source / "file.txt").write_text("staged\n", encoding="utf-8")
    git(source, "add", "file.txt")
    (source / "file.txt").write_text("working\n", encoding="utf-8")
    (source / "untracked 中文.txt").write_text("untracked\n", encoding="utf-8")
    (source / "intent.txt").write_text("intent\n", encoding="utf-8")
    git(source, "add", "-N", "intent.txt")
    before = state(source)
    index = (source / ".git/index").read_bytes()
    targets = [tmp_path / "one", tmp_path / "two"]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        receipts = list(executor.map(lambda path: create_workspace(source, path), targets))
    assert all(item["state"] == "ready" for item in receipts)
    assert all(state(path) == before for path in targets)
    assert (source / ".git/index").read_bytes() == index
    code = "from pathlib import Path; import subprocess,sys; p=Path('same-name.txt'); p.write_text(sys.argv[1]); subprocess.run(['git','add',str(p)],check=True); print(Path.cwd())"
    children = [subprocess.Popen([sys.executable, "-c", code, str(i)], cwd=path,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                for i, path in enumerate(targets)]
    for child, target in zip(children, targets):
        out, err = child.communicate(timeout=20)
        assert child.returncode == 0, err
        assert Path(os.fsdecode(out.strip())).resolve() == target.resolve()
    assert state(source) == before
    assert (source / ".git/index").read_bytes() == index
    assert [(path / "same-name.txt").read_text() for path in targets] == ["0", "1"]
    # Explicit directory resume starts in the same directory and retains edits.
    result = subprocess.check_output([sys.executable, "-c", "from pathlib import Path;print(Path('same-name.txt').read_text())"], cwd=targets[0])
    assert result.strip() == b"0"


def test_submodules_deleted_files_and_binary_stage_are_preserved(tmp_path):
    child = repository(tmp_path / "child")
    source = repository(tmp_path / "source")
    git(source, "-c", "protocol.file.allow=always", "submodule", "add", str(child), "nested")
    git(source, "commit", "-qam", "add child")
    (source / "file.txt").unlink()
    (source / "nested/file.txt").write_text("child staged\n")
    git(source / "nested", "add", "file.txt")
    (source / "nested/new.bin").write_bytes(bytes(range(256)))
    git(source / "nested", "add", "new.bin")
    (source / "nested/new.bin").write_bytes(b"working\x00\xff")
    before, child_before = state(source), state(source / "nested")
    target = tmp_path / "copy"
    create_workspace(source, target)
    assert (target / "nested/.git").is_dir()
    assert state(target) == before
    assert state(target / "nested") == child_before
    assert (target / "nested/new.bin").read_bytes() == b"working\x00\xff"
    assert state(source) == before
    assert state(source / "nested") == child_before


def test_existing_destination_is_untouched_and_missing_gitlink_is_preserved(tmp_path):
    source = repository(tmp_path / "source")
    target = tmp_path / "exists"
    target.mkdir()
    (target / "keep").write_text("keep")
    with pytest.raises(WorkspaceCopyError, match="already exists"):
        create_workspace(source, target)
    assert (target / "keep").read_text() == "keep"
    git(source, "update-index", "--add", "--cacheinfo", "160000", git(source, "rev-parse", "HEAD").decode().strip(), "missing")
    before = state(source)
    copy = tmp_path / "copy"
    assert create_workspace(source, copy)["state"] == "ready"
    assert state(copy) == state(source) == before
    assert not (copy / "missing").exists()
    assert git(copy, "ls-files", "--stage", "missing") == git(source, "ls-files", "--stage", "missing")


def test_nonrecursive_clone_keeps_uninitialized_gitlink_and_dirty_initialized_sibling(tmp_path):
    child = repository(tmp_path / "child")
    upstream = repository(tmp_path / "upstream")
    for name in ("uninitialized", "initialized"):
        git(upstream, "-c", "protocol.file.allow=always", "submodule", "add", str(child), name)
    git(upstream, "commit", "-qam", "add submodules")
    source = tmp_path / "source"
    git(upstream, "clone", "--no-recurse-submodules", str(upstream), str(source))
    git(source, "-c", "protocol.file.allow=always", "submodule", "update", "--init", "initialized")
    (source / "initialized/file.txt").write_text("staged child\n", encoding="utf-8")
    git(source / "initialized", "add", "file.txt")
    (source / "initialized/file.txt").write_text("working child\n", encoding="utf-8")
    (source / "file.txt").write_text("local docs edit\n", encoding="utf-8")
    before, child_before = state(source), state(source / "initialized")
    index = (source / ".git/index").read_bytes()
    target = tmp_path / "copy"
    assert create_workspace(source, target)["state"] == "ready"
    assert (target / "uninitialized").is_dir()
    assert list((target / "uninitialized").iterdir()) == []
    assert git(target, "submodule", "status", "uninitialized") == git(source, "submodule", "status", "uninitialized")
    assert git(target, "submodule", "status", "uninitialized").startswith(b"-")
    assert (target / "initialized/.git").is_dir()
    assert state(target) == state(source) == before
    assert state(target / "initialized") == state(source / "initialized") == child_before
    assert (source / ".git/index").read_bytes() == index


def test_copy_keeps_git_line_policy_and_deleted_intent_without_private_state(tmp_path, monkeypatch):
    inherited = tmp_path / "global.gitconfig"
    inherited.write_text("[core]\n    autocrlf = input\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(inherited))
    source = repository(tmp_path / "source")
    git(source, "config", "core.autocrlf", "false")
    (source / "file.txt").write_bytes(b"staged\r\n")
    git(source, "add", "file.txt")
    (source / "file.txt").write_bytes(b"working\r\n")
    (source / "intent.txt").write_bytes(b"intent\r\n")
    (source / "removed-intent.txt").write_bytes(b"removed\r\n")
    git(source, "add", "-N", "intent.txt", "removed-intent.txt")
    (source / "removed-intent.txt").unlink()
    (source / "ordinary.txt").write_bytes(b"ordinary\r\n")
    (source / ".vaws-local").mkdir()
    (source / ".vaws-local/private.json").write_text("private runtime state")

    def editing_state(path):
        return (git(path, "rev-parse", "HEAD"), git(path, "diff", "--binary", "--cached"),
                git(path, "diff", "--binary"),
                git(path, "status", "--porcelain=v1", "-z", "--", "file.txt", "intent.txt",
                    "removed-intent.txt", "ordinary.txt"))

    before, index = editing_state(source), (source / ".git/index").read_bytes()
    target = tmp_path / "copy"
    assert create_workspace(source, target)["state"] == "ready"
    assert (source / ".git/index").read_bytes() == index
    assert editing_state(source) == editing_state(target) == before
    assert not (target / "removed-intent.txt").exists()
    assert not (target / ".vaws-local/private.json").exists()
    assert (source / ".vaws-local/private.json").read_text() == "private runtime state"
    assert (target / ".git").is_dir()
    # A client with a different inherited Git configuration reads the same
    # staged/working state because the target retains the source's policy.
    inherited.write_text("[core]\n    autocrlf = true\n", encoding="utf-8")
    assert editing_state(target) == before


@pytest.mark.parametrize("failure", ["tracked_reserved", "case_variant", "concurrent_edit"])
def test_invalid_or_changing_source_never_publishes_a_ready_workspace(tmp_path, monkeypatch, failure):
    source = repository(tmp_path / "source")
    target = tmp_path / "copy"
    if failure != "concurrent_edit":
        directory = ".VAWS-LOCAL" if failure == "case_variant" else ".vaws-local"
        reserved = source / directory / "native-workspace.json"
        reserved.parent.mkdir()
        reserved.write_bytes(b'{"original":"tracked content"}\n')
        git(source, "add", str(reserved.relative_to(source)))
        git(source, "commit", "-qm", "tracked reserved state")
        before = state(source)
        with pytest.raises(WorkspaceCopyError, match="tracked .vaws-local"):
            create_workspace(source, target)
        assert not target.exists()
        assert state(source) == before
        assert reserved.read_bytes() == b'{"original":"tracked content"}\n'
    else:
        original = workspace.shutil.copy2
        changed = False

        def copy_then_edit(src, dst, *args, **kwargs):
            nonlocal changed
            result = original(src, dst, *args, **kwargs)
            if not changed:
                changed = True
                (source / "file.txt").write_bytes(b"concurrent edit\n")
            return result

        monkeypatch.setattr(workspace.shutil, "copy2", copy_then_edit)
        with pytest.raises(WorkspaceCopyError, match="source changed while copying"):
            create_workspace(source, target)
        assert not (target / ".vaws-local/native-workspace.json").exists()
        assert (source / "file.txt").read_bytes() == b"concurrent edit\n"


def test_directory_symlink_retains_directory_behavior_after_copy(tmp_path):
    source = repository(tmp_path / "source")
    directory = source / "z-directory"
    directory.mkdir()
    (directory / "payload").write_bytes(b"through directory link\n")
    link = source / "a-link"
    try:
        link.symlink_to("z-directory", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"native symlink creation is unavailable: {exc}")
    git(source, "add", ".")
    git(source, "commit", "-qm", "directory symlink")
    before, index = state(source), (source / ".git/index").read_bytes()
    target = tmp_path / "copy"
    assert create_workspace(source, target)["state"] == "ready"
    copied = target / "a-link"
    assert copied.is_symlink()
    assert copied.is_dir()
    assert (copied / "payload").read_bytes() == b"through directory link\n"
    if os.name == "nt":
        # Windows distinguishes file and directory reparse points even when
        # readlink text and Git mode/hash are otherwise identical.
        assert copied.lstat().st_file_attributes & 0x10
    assert state(source) == state(target) == before
    assert (source / ".git/index").read_bytes() == index
