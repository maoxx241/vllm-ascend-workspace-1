"""The optional topology helper cannot bypass verified personal fork setup."""
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / ".agents/lib"), str(ROOT / ".agents/bootstrap/repo-init/scripts")]
import repo_topology as topology


def test_low_level_configure_cannot_bypass_verified_fork_setup():
    args = SimpleNamespace(repo=".", origin_url="https://github.com/an-org/vllm.git", upstream_url=None)
    with mock.patch.object(topology, "resolve_repo", return_value=Path("/unused")), \
         mock.patch.object(topology, "mutate_remote") as mutate:
        with pytest.raises(topology.RepoTopologyError, match="workspace_forks.py"):
            topology.cmd_configure(args)
        mutate.assert_not_called()


@pytest.mark.parametrize("script", ["install_gh_user.py", "repo_topology.py"])
def test_bootstrap_helpers_load_without_prepared_runtime(script, tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c",
         "import runpy,sys;runpy.run_path(sys.argv[1],run_name='bootstrap_import')",
         str(ROOT / ".agents/bootstrap/repo-init/scripts" / script)],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stdout and not result.stderr
