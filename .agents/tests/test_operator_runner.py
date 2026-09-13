"""Actual local child execution of the business payload; no daemon or network."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents/lib'))
import vaws_operator_runner as runner


def inputs(tmp_path, *, kernel='def run(x):\n    return [v * 2 for v in x]\n', cases=None, **options):
    source = tmp_path / 'original source'
    source.mkdir()
    files = {'kernel.py': kernel, 'reference.py': 'def ref(x):\n    return [v + v for v in x]\n',
             'cases.py': cases or "def cases(device):\n    yield {'id': 'simple', 'args': ([1, 2, 3],)}\n"}
    for name, text in files.items():
        (source / name).write_text(text, encoding='utf-8')
    payload, origins = runner.bundle_inputs(str(source/'kernel.py')+':run', str(source/'reference.py')+':ref',
        str(source/'cases.py')+':cases', device='cpu', atol=1e-5, rtol=1e-5,
        warmups=options.get('warmups', 0), repeats=options.get('repeats', 0), max_cases=options.get('max_cases', 64))
    return payload, origins, source


def child(tmp_path, payload):
    owned = tmp_path / 'owned execution'
    owned.mkdir(exist_ok=True)
    script = runner.render_script(payload)
    if os.name == 'posix':
        path = owned / 'case.sh'
        path.write_text(script, encoding='utf-8')
        command = ['bash', str(path)]
    else:
        # Run exactly the rendered heredoc body on Windows; POSIX runs Bash.
        path = owned / 'case.py'
        path.write_text(script.split("<<'VAWS_OPERATOR_PY'\n", 1)[1].rsplit('\nVAWS_OPERATOR_PY\n', 1)[0], encoding='utf-8')
        command = [sys.executable, '-X', 'utf8', str(path)]
    process = subprocess.run(command, cwd=owned, env={**os.environ, 'VAWS_PYTHON':sys.executable},
                             capture_output=True, text=True, encoding='utf-8', timeout=45)
    business = runner.decode_business({'stdout':process.stdout})
    assert business is not None, process.stderr
    return process, business, owned


def test_actual_child_calls_fixed_candidate_and_preserves_owned_artifacts(tmp_path):
    payload, origins, source = inputs(tmp_path, repeats=4, warmups=1)
    (source/'kernel.py').write_text('raise AssertionError("later local edit")\n')
    process, business, owned = child(tmp_path, payload)
    assert process.returncode == 0
    assert business['status'] == 'passed' and business['candidate_invocations'] == 6
    assert business['cases'][0]['timings']['candidate']['median_seconds'] >= 0
    assert str(source) not in runner.render_script(payload)
    record_path = Path(business['record_path'])
    assert record_path.is_relative_to(owned)
    record = json.loads(record_path.read_text())
    assert record['cases'][0]['inputs']
    assert len(record['cases'][0]['timings']['candidate']['samples_seconds']) == 4
    assert business['source_hashes']['kernel.py'] == origins['kernel']['sha256']
    assert (source/'kernel.py').read_text().startswith('raise AssertionError')


@pytest.mark.parametrize('kernel', [
    'def run(x):\n    return [999 for v in x]\n',
    'def run(x):\n    raise RuntimeError("candidate crash")\n',
    'def run(x):\n    return None\n',
])
def test_mismatch_crash_and_empty_output_cannot_pass(tmp_path, kernel):
    payload, _, _ = inputs(tmp_path, kernel=kernel)
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 1 and business['status'] == 'failed'
    assert business['cases'][0]['candidate_invoked'] is True
    assert business['cases'][0]['error']
    assert Path(business['record_path']).is_file()


def test_reference_and_candidate_receive_independent_mutable_inputs(tmp_path):
    payload, _, _ = inputs(tmp_path, kernel='def run(x):\n    for i in range(len(x)): x[i] *= 2\n    return x\n')
    payload['files']['reference.py'] = 'def ref(x):\n    x[:] = [v * 2 for v in x]\n    return x\n'
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 0 and business['status'] == 'passed'


def test_same_file_entry_points_share_module_identity_and_import_once(tmp_path):
    path = tmp_path/'all_cases.py'
    path.write_text('''from pathlib import Path
counter = Path(__file__).with_suffix('.count')
counter.write_text(counter.read_text() + 'x' if counter.exists() else 'x')
class Box:
    def __init__(self, value): self.value = value
def kernel(x):
    assert isinstance(x, Box)
    return x.value * 2
def reference(x):
    assert isinstance(x, Box)
    return x.value + x.value
def cases(device):
    yield {'id':'same-class', 'args':(Box(2),)}
''', encoding='utf-8')
    payload, _ = runner.bundle_inputs(str(path)+':kernel', str(path)+':reference', str(path)+':cases',
        device='cpu', atol=0, rtol=0, warmups=0, repeats=0, max_cases=1)
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 0 and business['status'] == 'passed'
    assert (Path(business['bundle_dir'])/'all_cases.count').read_text() == 'x'
    assert not path.with_suffix('.count').exists()


def test_matching_empty_output_trees_are_not_comparison_evidence(tmp_path):
    payload, _, _ = inputs(tmp_path, kernel='def run(x): return {"output": []}\n')
    payload['files']['reference.py'] = 'def ref(x): return {"output": []}\n'
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 1 and business['status'] == 'failed'
    assert 'empty output tree' in business['cases'][0]['error']


@pytest.mark.parametrize('cases', [
    'def cases(device):\n    return []\n',
    "def cases(device):\n    return [{'id':'x','args':([1],)}, {'id':'x','args':([2],)}]\n",
    "def cases(device):\n    return [{'id':'x','args':([1],),'atol':float('nan')}]\n",
])
def test_invalid_business_cases_keep_partial_evidence(tmp_path, cases):
    payload, _, _ = inputs(tmp_path, cases=cases)
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 1 and business['status'] == 'failed'
    assert Path(business['record_path']).is_file()


def test_cpu_cannot_silently_replace_requested_npu(tmp_path):
    payload, _, _ = inputs(tmp_path)
    payload['device'] = 'npu'
    # Deliberately shadow the NPU extension in this private bundle.
    payload['files']['torch_npu.py'] = 'raise ImportError("test NPU unavailable")\n'
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 1 and business['candidate_invocations'] == 0
    assert 'NPU unavailable' in business['error']


def test_submit_uses_one_owned_script_call_and_does_not_replay_timeout(tmp_path):
    payload, origins, _ = inputs(tmp_path)
    client = Mock()
    client.run.return_value = {'execution_id':'same-id','state':'preparing','resources_released':False,'wait_timed_out':True}
    options = {'wait_until':'released','wait_timeout_seconds':30,'resources':{'npu_count':0}}
    result, code = runner.submit(payload, origins, client=client, output_dir=tmp_path/'record', run_options=options)
    assert client.run.call_count == 1
    assert client.run.call_args.kwargs['wait_until'] == 'released'
    assert Path(client.run.call_args.kwargs['script_file']).is_file()
    assert 'sources' not in client.run.call_args.kwargs
    assert result['execution_id'] == 'same-id' and result['status'] == 'pending' and code == 0
    client.observe.assert_not_called()
    client.wait.assert_not_called()


def test_success_requires_matching_callable_evidence(tmp_path):
    payload, origins, _ = inputs(tmp_path)
    process, business, _ = child(tmp_path, payload)
    client = Mock()
    client.run.return_value = {'execution_id':'done','state':'succeeded','resources_released':True,'stdout':process.stdout}
    result, code = runner.submit(payload, origins, client=client, output_dir=tmp_path/'ok', run_options={})
    assert code == 0 and result['status'] == 'passed'
    assert json.loads(Path(result['record_ref']).read_text())['business']['source_hashes'] == business['source_hashes']
    payload['files']['kernel.py'] += '# changed\n'
    result, code = runner.submit(payload, origins, client=client, output_dir=tmp_path/'wrong', run_options={})
    assert code == 1 and result['state'] == 'succeeded' and result['status'] == 'failed'
    assert 'hashes differ' in result['evidence_error']


def test_bundle_does_not_execute_input_and_rejects_ambiguous_filenames(tmp_path):
    payload, _, source = inputs(tmp_path, kernel='raise AssertionError("must run remotely")\ndef run(x): return x\n')
    assert payload['files']['kernel.py'].startswith('raise')
    second = tmp_path/'kernel.py'
    second.write_text('def ref(x): return x\n')
    with pytest.raises(ValueError, match='same basename'):
        runner.bundle_inputs(str(source/'kernel.py')+':run', str(second)+':ref', str(source/'cases.py')+':cases')


def test_local_record_failure_does_not_change_completed_business(tmp_path, monkeypatch):
    payload, origins, _ = inputs(tmp_path)
    process, _, _ = child(tmp_path, payload)
    client = Mock()
    client.run.return_value = {'execution_id':'done','state':'succeeded','resources_released':True,'stdout':process.stdout}
    original = Path.write_text
    def fail_record(path, *args, **kwargs):
        if path.name == 'result.json':
            raise OSError('test full local disk')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', fail_record)
    result, code = runner.submit(payload, origins, client=client, output_dir=tmp_path/'record', run_options={})
    assert code == 0 and result['status'] == 'passed' and result['state'] == 'succeeded'
    assert result['record_ref'] is None and 'full local disk' in result['warning']
    assert client.run.call_count == 1


@pytest.mark.parametrize('stdout', ['', runner.MARKER + 'invalid!'])
def test_missing_or_malformed_business_evidence_preserves_owner_state(tmp_path, stdout):
    payload, origins, _ = inputs(tmp_path)
    client = Mock()
    client.run.return_value = {'execution_id':'done','state':'succeeded','resources_released':True,'stdout':stdout}
    result, code = runner.submit(payload, origins, client=client, output_dir=tmp_path/'record', run_options={})
    assert code == 1 and result['status'] == 'failed' and result['state'] == 'succeeded'
    assert result['resources_released'] is True and result['evidence_error']
    assert client.run.call_count == 1


def test_cli_uses_official_context_resolution_without_guessing(tmp_path, monkeypatch, capsys):
    import vaws_task_target
    _, _, source = inputs(tmp_path)
    resolve = Mock(side_effect=RuntimeError('No associated native context'))
    monkeypatch.setattr(vaws_task_target, 'task_client', resolve)
    code = runner.main(['--kernel', str(source/'kernel.py')+':run',
                        '--reference', str(source/'reference.py')+':ref',
                        '--cases', str(source/'cases.py')+':cases'], workspace_root=tmp_path)
    assert code == 1 and 'No associated native context' in json.loads(capsys.readouterr().out)['error']
    resolve.assert_called_once_with(None)
    assert not (tmp_path/'.vaws-local/operator-runs').exists()


def test_owner_argv_preserves_drive_colon_callable_and_unicode_path():
    from vaws_managed_entry import managed_invocation
    arguments = ['python', '/mnt/d/project/operator_debug.py', 'run', '--kernel',
                 '/mnt/d/中文 space/kernel.py:Module.run', '--reference=C:/reference dir/ref.py:run',
                 '--cases', 'cases.py:cases', '--source', 'vllm-ascend=/mnt/d/业务 source',
                 '--source=project=C:/already native', '--output-dir', '/mnt/d/results dir']
    convert = lambda path: 'D:/' + path.removeprefix('/mnt/d/')
    normalized = runner.owner_arguments(arguments, convert)
    assert normalized[4] == 'D:/中文 space/kernel.py:Module.run'
    assert normalized[5] == '--reference=C:/reference dir/ref.py:run'
    assert normalized[7] == 'cases.py:cases'
    assert normalized[9] == 'vllm-ascend=D:/业务 source'
    assert normalized[10] == '--source=project=C:/already native'
    # The existing platform boundary still owns interpreter/env and plain paths.
    command, _ = managed_invocation('/mnt/d/project/operator_debug.py',
        {'python':'C:/env/python.exe','receipt':'C:/env/receipt.json'},
        original=normalized, local_options=('--output-dir',), environment={})
    assert 'D:/中文 space/kernel.py:Module.run' in command
    assert command[-1].replace('\\','/').lower() == 'd:/results dir'


def test_actual_process_argv_preserves_unicode_spaces_and_callable_colons():
    code = '''import json, sys
sys.path.insert(0, sys.argv[1])
from vaws_operator_runner import owner_arguments
print(json.dumps(owner_arguments(sys.argv[2:], lambda path: 'D:/' + path.removeprefix('/mnt/d/')), ensure_ascii=False))
'''
    arguments = ['--kernel', '/mnt/d/中文 space/kernel.py:Module.run',
                 '--reference=C:/reference dir/ref.py:run', '--cases', 'cases.py:cases',
                 '--source', 'vllm-ascend=/mnt/d/业务 source']
    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code, str(ROOT/'.agents/lib'), *arguments],
                            capture_output=True, text=True, encoding='utf-8', check=True)
    actual = json.loads(result.stdout)
    assert actual == ['--kernel', 'D:/中文 space/kernel.py:Module.run',
                      '--reference=C:/reference dir/ref.py:run', '--cases', 'cases.py:cases',
                      '--source', 'vllm-ascend=D:/业务 source']


def test_tensor_error_metrics_promote_narrow_values_and_keep_large_integer_precision():
    # A small arithmetic stand-in makes the promotion requirement executable
    # on control-plane environments without torch. Real tensors are below.
    from types import SimpleNamespace
    from vaws_operator_payload import _maximum_difference
    class Dtype:
        def __init__(self, name):
            self.name = name
            self.is_complex = name.startswith('complex')
            self.is_floating_point = name.startswith('float')
    types = {name:Dtype(name) for name in ['bool', 'uint8', 'int64', 'uint64', 'float16', 'float64', 'complex64', 'complex128']}
    torch = SimpleNamespace(**types)
    class Values:
        def __init__(self, values, dtype): self.values, self.dtype = values, dtype
        def to(self, dtype): return Values(self.values, dtype)
        def __sub__(self, other):
            assert self.dtype.name in {'int64', 'float64', 'complex128'}, 'unsafe narrow arithmetic'
            return Values([a-b for a,b in zip(self.values, other.values)], self.dtype)
        def __ne__(self, other): return Values([a != b for a,b in zip(self.values,other.values)], types['bool'])
        def abs(self): return Values([abs(x) for x in self.values], self.dtype)
        def numel(self): return len(self.values)
        def max(self): return SimpleNamespace(item=lambda:max(self.values))
        def reshape(self, _): return self
        def tolist(self): return self.values
    for name, left, right, expected in [('uint8',0,255,255), ('float16',65504.,-65504.,131008.),
            ('complex64',3+4j,0j,5.), ('int64',2**63-1,-2**63,2**64-1),
            ('uint64',2**64-1,2**64-2,1), ('bool',True,False,True)]:
        assert _maximum_difference(Values([left],types[name]), Values([right],types[name]),torch) == expected


def test_error_metrics_with_real_cpu_torch_when_available():
    torch = pytest.importorskip('torch')
    from vaws_operator_payload import _maximum_difference
    assert _maximum_difference(torch.tensor([0],dtype=torch.uint8), torch.tensor([255],dtype=torch.uint8),torch) == 255
    assert _maximum_difference(torch.tensor([65504.],dtype=torch.float16), torch.tensor([-65504.],dtype=torch.float16),torch) == 131008
    assert _maximum_difference(torch.tensor([2**63-1],dtype=torch.int64), torch.tensor([-2**63],dtype=torch.int64),torch) == 2**64-1


def test_tensor_stride_and_alias_with_real_cpu_torch_when_available(tmp_path):
    pytest.importorskip('torch')
    payload, _, _ = inputs(tmp_path, kernel='def run(x):\n    assert x.stride() == (1, 3)\n    return x + x\n',
        cases="import torch\ndef cases(device):\n    yield {'id':'transposed','args':(torch.arange(6., device=device).reshape(2,3).t(),)}\n")
    payload['files']['reference.py'] = 'def ref(x): return x * 2\n'
    process, business, _ = child(tmp_path, payload)
    assert process.returncode == 0 and business['status'] == 'passed'


@pytest.mark.parametrize('skill,module,benchmark', [
    ('ascend-operator-debug','operator_debug',False),
    ('ascend-triton-kernel-validation','triton_validation',False),
    ('ascend-triton-kernel-optimization','triton_optimization',True),
])
def test_skill_entry_reaches_shared_runner_without_report_forms(monkeypatch, skill, module, benchmark):
    monkeypatch.setenv('VAWS_SKIP_VENV_REEXEC','1')
    path = ROOT/'.agents/skills'/skill/'scripts'/f'{module}.py'
    spec = importlib.util.spec_from_file_location('_runner_entry_'+module, path)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    called = Mock(return_value=0)
    monkeypatch.setattr(runner, 'main', called)
    assert entry.main(['run','--kernel','a.py:f','--reference','b.py:f','--cases','c.py:f']) == 0
    assert called.call_args.args[0][0] == '--kernel'
    assert called.call_args.kwargs.get('benchmark', False) == benchmark
