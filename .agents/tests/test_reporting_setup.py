"""Onboarding delegates durable reporter reuse to the diagnostics owner."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import vaws_onboarding as onboarding


@pytest.mark.parametrize('token', [None, 'private-test-token'])
def test_reporting_uses_atomic_owner_ensure_and_never_places_token_in_arguments(tmp_path, monkeypatch, token):
    calls = []
    monkeypatch.setattr(onboarding, 'run_json', lambda *args: calls.append(args) or {'status': 'installed'})
    environment = {'VAWS_DIAGNOSTICS_ROOT': str(tmp_path / 'logs')}
    if token:
        environment['GH_TOKEN'] = token
    receipt = {'python': str(tmp_path / 'installed-runtime/python')}
    result = onboarding.configure_reporting(tmp_path, receipt, environment)
    command, cwd, child_environment = calls[0]
    assert command[:5] == [receipt['python'], '-m', 'vaws_diagnostics.cli', 'service', 'ensure']
    assert command[command.index('--root') + 1] == str(tmp_path / 'logs')
    assert ('--save-token' in command) == bool(token)
    assert 'private-test-token' not in ' '.join(command)
    assert cwd == tmp_path and child_environment is environment
    assert result['status'] == 'installed'
