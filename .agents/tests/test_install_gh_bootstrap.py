"""The GitHub CLI installer loads before a component environment is prepared."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_install_gh_loads_without_prepared_runtime(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c",
         "import runpy,sys;runpy.run_path(sys.argv[1],run_name='bootstrap_import')",
         str(ROOT / ".agents/bootstrap/repo-init/scripts/install_gh_user.py")],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stdout and not result.stderr
