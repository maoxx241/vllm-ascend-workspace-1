"""Configuration targets and their stable owners survive cross-worktree invocation."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from client_setup_fixtures import selected_runtime

SOURCE = Path(__file__).resolve().parents[2]


def git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def family(tmp_path, monkeypatch):
    primary = tmp_path / "primary 用户"
    primary.mkdir()
    relative = Path(".agents/scripts/vaws_client_setup.py")
    (primary / relative).parent.mkdir(parents=True)
    shutil.copyfile(SOURCE / relative, primary / relative)
    (primary / ".agents/scripts/vaws_native_mcp.py").write_text("# native gateway fixture\n")
    git(primary, "init")
    git(primary, "add", ".agents")
    git(primary, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-m", "setup fixture")
    linked = tmp_path / "task worktree"
    git(primary, "worktree", "add", "-b", "fixture-task", str(linked))
    user = tmp_path / "user"
    user.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: user))
    monkeypatch.setenv("KIMI_CODE_HOME", str(user / ".kimi-code"))
    monkeypatch.setenv("GROK_HOME", str(user / ".grok"))
    monkeypatch.setenv("CODEX_HOME", str(user / ".codex"))
    monkeypatch.delenv("VAWS_AGENT_SESSIONS_DIR", raising=False)
    monkeypatch.delenv("VAWS_GITHUB_IDENTITY_FILE", raising=False)
    modules = []
    for root in (primary, linked):
        spec = importlib.util.spec_from_file_location("setup_owner_" + str(len(modules)), root / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        receipt = selected_runtime(monkeypatch, module, tmp_path)
        monkeypatch.setattr(module, "read_receipt", lambda _, value=receipt: value)
        modules.append(module)
    import vaws_codex_config
    monkeypatch.setattr(vaws_codex_config, "managed_receipt", lambda _: receipt)
    return primary, linked, user, modules, receipt


@pytest.mark.parametrize("client", ["cursor", "codex", "claude", "grok", "kimi"])
@pytest.mark.parametrize("target_linked", [False, True])
def test_script_copies_generate_same_scoped_plan_and_stable_owner(family, client, target_linked):
    primary, linked, user, modules, receipt = family
    target = linked if target_linked else primary
    options = {"cursor_global_mcp": client == "cursor", "codex_global_hooks": client == "codex"}
    first = modules[0].build_plan(client, target, **options)
    second = modules[1].build_plan(client, target, **options)
    assert first == second
    assert second["configuration_owner"] == str(primary)
    assert second["launch_cwd"] == str(target)
    assert second["task_registry"] == str(primary / ".vaws-local/agent-sessions")
    assert second["backup_dir"] == str(primary / ".vaws-local/client-setup-backups")
    for arguments in second["mcp_servers"].values():
        assert arguments[0] == str(primary / ".agents/scripts/vaws_native_mcp.py")
    assert target / "AGENTS.md" in second["files"]
    for output, text in second["files"].items():
        assert output.is_relative_to(target) or output.is_relative_to(user) or output.is_relative_to(primary / ".git")
    # Apply only to this temporary Git family and temporary client home. A
    # repeat from the other script copy cannot add hooks or require rewrites.
    modules[1].apply_plan(second)
    repeated = modules[0].build_plan(client, target, **options)
    assert modules[0].apply_plan(repeated) == []
    assert modules[1].ROOT == linked  # Planning does not change its caller.


@pytest.mark.parametrize("target_linked", [False, True])
def test_cli_selects_target_owner_before_bootstrap(family, monkeypatch, target_linked):
    primary, linked, _, modules, _ = family
    target = linked if target_linked else primary
    observed = []

    class BootstrapObserved(Exception):
        pass

    def bootstrap(**kwargs):
        observed.append(kwargs)
        raise BootstrapObserved

    for module in modules:
        monkeypatch.setattr(module, "ensure_workspace_interpreter", bootstrap)
        with pytest.raises(BootstrapObserved):
            module.main(["--client", "cursor", "--project", str(target)])
    assert observed == [{"repo_root": primary, "use_saved": False}] * 2


def test_other_git_project_uses_installed_source_without_losing_target_scope(family):
    primary, linked, _, modules, _ = family
    target = linked.parent / "other project"
    target.mkdir()
    git(target, "init")
    first, second = [module.build_plan("cursor", target) for module in modules]
    assert first == second
    assert first["configuration_owner"] == str(primary)
    assert first["launch_cwd"] == str(target)
    assert target / ".cursor/hooks.json" in first["files"]
    assert first["mcp_servers"]["vaws-task"][0] == str(primary / ".agents/scripts/vaws_native_mcp.py")


@pytest.mark.parametrize("client", ["codex", "cursor", "claude", "grok", "kimi"])
def test_independent_copy_configures_shared_owner_before_publishing_ready(family, client):
    primary, _, _, modules, _ = family
    target = primary.parent / "independent copy"
    git(primary, "clone", "--local", "--no-hardlinks", str(primary), str(target))
    assert not (target / ".vaws-local/native-workspace.json").exists()
    plan = modules[0].build_plan(client, target, owner_project=primary)
    assert plan["configuration_owner"] == str(primary)
    assert plan["task_registry"] == str(primary / ".vaws-local/agent-sessions")
    assert plan["launch_cwd"] == str(target)
    assert not (target / ".vaws-local/native-workspace.json").exists()
    assert modules[0]._CONFIGURATION_OWNER is None


def test_old_linked_hook_is_replaced_once_and_foreign_hook_is_preserved(family):
    primary, linked, _, modules, _ = family
    setup = modules[1]
    hooks_path = primary / ".cursor/hooks.json"
    old = setup.hook_groups("cursor", primary)
    foreign = linked.parent / "unrelated/.agents/hooks/vaws_session.py"
    old_command = old["sessionStart"][0]["command"]
    foreign_arguments = setup.hook_argv(old_command)
    foreign_arguments[1] = str(foreign)
    foreign_command = setup.local_hook_command(foreign_arguments)
    assert foreign_command != old_command
    assert setup.hook_argv(foreign_command)[1] == str(foreign)
    old["sessionStart"] += [{"command": old_command}, {"command": foreign_command}]
    hooks_path.parent.mkdir()
    hooks_path.write_text(json.dumps({"hooks": old}))
    plan = setup.build_plan("cursor", primary)
    hooks = json.loads(plan["files"][hooks_path])["hooks"]["sessionStart"]
    assert len(hooks) == 2
    assert hooks[1]["command"] == foreign_command
    arguments = setup.hook_argv(hooks[0]["command"])
    assert arguments[1] == str(primary / ".agents/hooks/vaws_session.py")
    assert arguments[arguments.index("--project") + 1] == str(primary)
    setup.apply_plan(plan)
    assert modules[0].apply_plan(modules[0].build_plan("cursor", primary)) == []
