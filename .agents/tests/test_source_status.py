"""Real Git contracts for optional multi-repository inspection."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import vaws_source_status as status
from vaws_native_workspace import git
from vaws_workspace_entry import write_preparation

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / ".agents/scripts/workspace_sources.py"


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


def repository(path):
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Source Test")
    git(path, "config", "user.email", "source@example.invalid")
    git(path, "config", "core.autocrlf", "false")
    (path / "file.txt").write_text("base\n", encoding="utf-8")
    git(path, "add", "file.txt")
    git(path, "commit", "-qm", "base")
    return path.resolve()


@pytest.fixture
def bundle(tmp_path):
    root = repository(tmp_path / "workspace 中文 space")
    (root / ".gitignore").write_text(".vaws-local/\n/vllm/\n/vllm-ascend/\n", encoding="utf-8")
    git(root, "add", ".gitignore")
    git(root, "commit", "-qm", "source layout")
    children = {name: repository(root / name) for name in status.BUSINESS_REPOS}
    write_preparation(root, project_root=root, native_workspace=root, workspace=root, sources=children)
    return root, children


def dirty(path):
    (path / "file.txt").write_text("staged\n", encoding="utf-8")
    git(path, "add", "file.txt")
    (path / "file.txt").write_text("working\n", encoding="utf-8")
    (path / "new 中文 file.txt").write_text("untracked\n", encoding="utf-8")


def test_parent_clean_cannot_hide_child_staged_working_and_untracked(bundle):
    root, children = bundle
    dirty(children["vllm-ascend"])
    before = {name: ((path / ".git/index").read_bytes(), (path / ".git/config").read_bytes())
              for name, path in {"workspace": root, **children}.items()}
    assert git(root, "status", "--porcelain") == b""
    result = status.workspace_status(root)
    assert result["complete"] and not result["worktree_clean"]
    row = result["repositories"]["vllm-ascend"]
    assert row["branch"] == "main" and row["head"] == git(children["vllm-ascend"], "rev-parse", "HEAD").decode().strip()
    assert row["staged"] == row["working"] == [{"path": "file.txt", "code": "MM"}]
    assert row["untracked"] == ["new 中文 file.txt"]
    assert result["repositories"]["workspace"]["worktree_clean"]
    for name, path in {"workspace": root, **children}.items():
        assert before[name] == ((path / ".git/index").read_bytes(), (path / ".git/config").read_bytes())


@pytest.mark.parametrize("failure", ["missing", "empty", "bad_gitfile", "parent_gitfile"])
def test_missing_or_wrong_child_never_reports_aggregate_clean(bundle, failure):
    root, children = bundle
    child = children["vllm"]
    child.rename(root / "saved-child")
    if failure != "missing":
        child.mkdir()
    if failure == "bad_gitfile":
        (child / ".git").write_text("gitdir: does-not-exist\n", encoding="utf-8")
    elif failure == "parent_gitfile":
        (child / ".git").write_text("gitdir: ../.git\n", encoding="utf-8")
    result = status.workspace_status(root)
    assert result["complete"] is False and result["worktree_clean"] is None
    assert result["repositories"]["vllm"]["error"]
    assert result["repositories"]["workspace"]["complete"]
    selected = status.workspace_status(root, repo="vllm")
    assert selected["complete"] is False and selected["worktree_clean"] is None
    healthy = status.workspace_status(root, repo="vllm-ascend")
    assert healthy["complete"] and healthy["worktree_clean"]


@pytest.mark.parametrize("operation", [status.workspace_status, status.workspace_diff])
def test_single_repository_inspection_never_scans_other_workfiles(bundle, monkeypatch, operation):
    root, children = bundle
    for child in children.values():
        dirty(child)
    commands = []
    original = status.git
    def observed_git(path, *args, **kwargs):
        commands.append((path, args))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(status, "git", observed_git)
    result = operation(root, repo="vllm-ascend")
    assert result["complete"] and set(result["repositories"]) == {"vllm-ascend"}
    assert [path for path, args in commands if args[0] == "status"] == [children["vllm-ascend"]]
    assert all(path == children["vllm-ascend"] or args[0] == "rev-parse" for path, args in commands)
    assert {path for path, _ in commands} == {root, *children.values()}


def test_selected_child_cannot_alias_a_later_declared_sibling_repository(bundle):
    root, children = bundle
    child = children["vllm"]
    (child / ".git").rename(child / "saved-git")
    (child / ".git").write_text("gitdir: ../vllm-ascend/.git\n", encoding="utf-8")
    result = status.workspace_status(root, repo="vllm")
    assert result["complete"] is False and result["worktree_clean"] is None
    assert "shares" in result["repositories"]["vllm"]["error"]


def test_subdirectory_routes_bundle_but_foreign_nested_repository_is_not_selected(bundle):
    root, children = bundle
    directory = children["vllm-ascend"] / "some" / "module"
    directory.mkdir(parents=True)
    result = status.workspace_status(directory)
    assert result["workspace"] == str(root)
    assert set(result["repositories"]) == {"workspace", "vllm", "vllm-ascend"}
    foreign = repository(directory / "unrelated")
    result = status.workspace_status(foreign)
    assert not result["complete"] and result["worktree_clean"] is None
    assert "not selected" in result["error"]


def test_root_only_receipt_does_not_scan_existing_business_or_read_lock(bundle, monkeypatch):
    root, children = bundle
    dirty(children["vllm"])
    write_preparation(root, project_root=root, native_workspace=root, workspace=root, sources={})
    (root / "sources.lock.json").write_text("invalid lock", encoding="utf-8")
    observed = []
    original = status.git
    def observed_git(path, *args, **kwargs):
        observed.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(status, "git", observed_git)
    result = status.workspace_status(root)
    assert result["complete"] and set(result["repositories"]) == {"workspace"}
    assert set(observed) == {root}


def test_without_receipt_only_existing_known_children_are_inspected(tmp_path):
    root = repository(tmp_path / "plain")
    child = repository(root / "vllm-ascend")
    repository(root / "unrelated")
    result = status.workspace_status(child)
    assert result["selection"] == "existing"
    assert set(result["repositories"]) == {"workspace", "vllm-ascend"}
    assert not (root / "vllm").exists() and not (root / ".vaws-local").exists()


def test_corrupt_receipt_fails_instead_of_falling_back_to_directory_scan(bundle):
    root, _ = bundle
    (root / ".vaws-local/native-workspace.json").write_text("{}", encoding="utf-8")
    result = status.workspace_status(root)
    assert not result["complete"] and result["worktree_clean"] is None
    assert result["repositories"] == {}


def test_ordinary_git_commit_in_ascend_does_not_commit_other_repositories(bundle):
    root, children = bundle
    all_roots = {"workspace": root, **children}
    before = {name: git(path, "rev-parse", "HEAD") for name, path in all_roots.items()}
    child = children["vllm-ascend"]
    (child / "file.txt").write_text("ordinary task edit\n", encoding="utf-8")
    result = subprocess.run(["git", "commit", "-qam", "Ascend task"], cwd=child, capture_output=True)
    assert result.returncode == 0, result.stderr
    for name, path in all_roots.items():
        assert (git(path, "rev-parse", "HEAD") != before[name]) == (name == "vllm-ascend")


def test_parent_git_clean_single_force_preserves_dirty_unpushed_child_repositories(bundle, tmp_path):
    root, children = bundle
    assert root.is_relative_to(tmp_path.resolve()) and root != tmp_path.resolve()
    for child in children.values():
        (child / "file.txt").write_text("local commit\n", encoding="utf-8")
        git(child, "commit", "-qam", "not pushed")
        dirty(child)
    before = {name: {str(path.relative_to(child)): path.read_bytes()
                     for path in child.rglob("*") if path.is_file()}
              for name, child in children.items()}
    # Exactly this isolated fixture, ordinary single-force Git clean only.
    # This does not promise protection against double force or shell deletion.
    git(root, "clean", "-fdx")
    for name, child in children.items():
        assert {str(path.relative_to(child)): path.read_bytes()
                for path in child.rglob("*") if path.is_file()} == before[name]


def test_local_upstream_comparison_and_detached_head_are_explicit(tmp_path):
    source = repository(tmp_path / "source")
    child = tmp_path / "clone"
    git(source, "clone", "-q", "--", str(source), str(child))
    git(child, "config", "user.name", "Source Test")
    git(child, "config", "user.email", "source@example.invalid")
    (child / "file.txt").write_text("unpushed\n", encoding="utf-8")
    git(child, "commit", "-qam", "local commit")
    row = status.workspace_status(child)["repositories"]["workspace"]
    assert (row["upstream"], row["ahead"], row["behind"]) == ("origin/main", 1, 0)
    assert row["worktree_clean"] and row["upstream_comparison"] == "local_tracking_ref"
    git(child, "checkout", "--detach", "HEAD")
    row = status.workspace_status(child)["repositories"]["workspace"]
    assert row["branch"] is None and row["upstream"] is None and row["ahead"] is None


@pytest.mark.parametrize("newline", [False, True])
def test_nul_status_preserves_rename_and_unicode_names(tmp_path, newline):
    if newline and os.name == "nt":
        pytest.skip("Windows filenames cannot contain newlines; raw parser is covered separately")
    root = repository(tmp_path / "names 中文")
    name = "renamed 中文" + ("\n" if newline else " ") + "file.txt"
    git(root, "mv", "file.txt", name)
    row = status.workspace_status(root)["repositories"]["workspace"]
    assert row["staged"] == [{"path": name, "original_path": "file.txt", "code": "R."}]
    assert row["working"] == []


def test_raw_rename_record_keeps_newlines_without_splitlines():
    raw = b"# branch.oid " + b"a" * 40 + b"\0# branch.head main\0"
    raw += b"2 R. N... 100644 100644 100644 " + b"a" * 40 + b" " + b"a" * 40
    raw += b" R100 new\nname\0old\nname\0? other\nname\0"
    row = status._parse_status(raw)
    assert row["staged"][0]["path"] == "new\nname"
    assert row["staged"][0]["original_path"] == "old\nname"
    assert row["untracked"] == ["other\nname"]


def test_diff_selects_index_or_working_and_limits_total_patch_bytes(bundle):
    root, children = bundle
    dirty(children["vllm-ascend"])
    working = status.workspace_diff(root, repo="vllm-ascend")
    staged = status.workspace_diff(root, repo="vllm-ascend", staged=True)
    assert "+working" in working["repositories"]["vllm-ascend"]["diff"]
    assert "+staged" in staged["repositories"]["vllm-ascend"]["diff"]
    assert working["repositories"]["vllm-ascend"]["untracked_count"] == 1
    dirty(children["vllm"])
    bounded = status.workspace_diff(root, max_bytes=25)
    assert bounded["truncated"] and bounded["complete"]
    assert sum(len(row.get("diff", "").encode("utf-8")) for row in bounded["repositories"].values()) <= 25
    assert not status.workspace_diff(root, repo="unknown")["complete"]
    with pytest.raises(ValueError, match="max_bytes"):
        status.workspace_diff(root, max_bytes=0)


def test_cli_uses_current_child_directory_without_packages_or_setup(bundle):
    root, children = bundle
    dirty(children["vllm-ascend"])
    result = subprocess.run([sys.executable, "-S", str(CLI), "status"], cwd=children["vllm-ascend"],
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] and payload["workspace"] == str(root) and not payload["worktree_clean"]
    result = subprocess.run([sys.executable, "-S", str(CLI), "--root", str(root), "diff", "--repo", "missing"],
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 1 and json.loads(result.stdout)["ok"] is False
