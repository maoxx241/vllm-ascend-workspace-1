# VAWS engineering validation archive

Status: dated evidence and coverage index, 2026-09-13; not a runtime contract

This archive answers which VAWS capability has evidence, what actually ran,
which version it describes, and which claim remains unverified. It reuses the
existing reports and raw checks. It does not add a validation step to ordinary
Agent work or promote passing tests into authority over current observations.

VAWS implementation and tool validation belong here. The development knowledge
library instead concerns vLLM, vLLM-Ascend, Ascend NPU, AI and infrastructure.
This archive is not a default knowledge import, topic or generated experience
source. Private raw logs retain their original ownership; addresses, machine
names, user directories, native identities and container coordinates are not
copied into this public archive.

The [nine principles](../design-principles.md) and
[runtime ownership](../target-state.md) remain the governing contracts. The
audited consumer checkout was `7f2ebb8d2be4c0774f9663b1cfcef43dc3a714dd`.
The source-workspace and knowledge tasks were still integrating newer changes,
so its dependency pins are not presented as the final deployed platform.

## Versioned evidence

| Evidence | Actually established | Version / limitation |
|---|---|---|
| [Existing-container follow-up](../existing-container-validation-2026-09-13.md) | Final installed four-machine 32/32 checks; 12 owned jobs quiet; original container/code/environment preserved; real SDK gateway exposed 18 remote tools without task context | remote-dev `a65362882a85b4d460be3e1d15e90de9fb507e70`, coordinator `921ce2af`, knowledge `3a65926d`; CPU transport and script semantics, no NPU-model result |
| [Managed final implementation](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/a483724f89625e2eec1479bcaf48f8604bbf99c2/docs/managed-performance-redesign-2026-09-13.md) | Real MCP SDK/SCM input isolation, bounded wait with responsive control, actual final consumer integration: 88 passed, 1 skipped, 20 subtests | coordinator `9f94f27964437f962e6037529ccf2f0b1c709ede`, consumer `a483724f89625e2eec1479bcaf48f8604bbf99c2`; local/CI behavior, not final-version performance |
| [Managed measured pairs](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/a483724f89625e2eec1479bcaf48f8604bbf99c2/docs/managed-performance-redesign-2026-09-13.md) | Native submit-to-release 98.61 → 96.78 s; warm 26.87 → 28.31 s; actual FP32 kernel/reference check | baseline `384b89b`, native candidate `a91f19a`, warm candidate `d2095dc`; one serial pair, unequal immutable/editable installation, B reused A bundle, concurrent Windows tests; no warm speedup or universal 1-second result |
| [Source-workspace candidate](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/340769d826ab64b78ab840317c74bc6709716f08/docs/source-workspace-validation-2026-09-13.md) | Four-machine fixed three-repository capture/materialization and original-state preservation; 24 local layout migrations plus 3 boundary cases | source binding coordinator `66e2d2b3aa30512eef433e0594ebf815e574b6ce`; not a full newer managed lifecycle, current NPU dependency validation or native GUI result |
| Real Kimi source-workspace ACP | Actual installed Kimi 0.42.0 initialize/session, real SessionStart hook, persisted cwd, 3 prepared sources and clean EOF: 10 checks passed | coordinator `a91f19a`, remote-dev `a6536288`, knowledge `485ddc0`; local lifecycle used a noncredential sentinel and loopback discard URL, with no prompt/LLM/authenticated inference; not Grok Bot or all-client UI acceptance |
| [Shared-host execution and messaging](../shared-root-host-validation-2026-09-12.md) | Four managed CPU runs, busy-NPU queuing, isolated-identity real SSH message/reply delivery, 1,103 native artifacts restored/loaded across four machines | coordinator `0d0e814dc673677be62d2fa60e204552d57e22ce`; busy devices prevented new kernel runs; old periodic updater details are superseded by the current contract |
| [Windows/WSL platform pass](../windows-validation-2026-09-11.md) | Three owner suites, all then-current skill suites, 120 ordinary live SSH calls, real dense knowledge release/import/switch and fleet process lifecycle | owner commits are listed in that report; no NPU work, live ModelScope authentication/download, macOS or ARM64 acceptance |
| [Six scenarios](../six-scenario-performance-2026-09-13.md) | Actual source/native reuse, fixed inputs, owned kernel and release evidence; independent direct/managed Agent samples | vLLM `e7739c8720974cdd442c0f051cc08a41a4e799c2`, Ascend `88398f3c885d1264cde65069dc8a3e9adf6487f0`; each arm keeps its own coordinator/version and timer; universal six-case speed target not met |
| [Knowledge 0.6.0 adoption](../knowledge-adoption-2026-09-13.md) | Optional three-tool contract, lexical/vector fusion, source excerpt evidence and bounded owner worklist | consumed commit `485ddc0d71e86915487a1204032426a3d874ba0e`; current catalog/curation/media/release work needs its own final-revision acceptance |

GitHub was read again during this audit. Coordinator PR 33 and consumer PR 165
were merged. Their exact tested heads were successful in
[coordinator CI 34741531389](https://github.com/vllm-ascend-workspace/vaws-coordinator/actions/runs/34741531389)
and [consumer CI 34741553507](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34741553507).
The consumer merge was `989dd74e04fac437661723a8938e6c89a5b26bb5`.
[Consumer PR 166](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/166)
was still open at head `340769d826ab64b78ab840317c74bc6709716f08`.
These are observations at the archive cutoff; later merge or deployment state
must come from its actual result. A passed CI run proves only its selected jobs.

### Verified local suite snapshot

The existing `20260913-140033-8f72c342` run completed **90 local suites** in
319.699 seconds. All 90 JUnit files were reread and their recorded SHA256 values
matched. Recounting the XML yielded **2,187 JUnit entries, 6 skips, 0 failures
and 0 errors**. Entries include subtests and must not be reported as 2,187
independent pytest test functions. All current 18 business-skill suites are
present. This was an integrity audit of existing results, not a fresh execution.

The result summary does not embed the exact source HEAD and loaded package
revisions. Its directory label and verified hashes cannot fill that gap. The
coverage is therefore historical local-test evidence. Use the exact-head CI or
a targeted rerun when a later change requires current applicability. The raw
run remains with its original source-workspace task; it is not copied here.

Retained raw-evidence fingerprints:

| Original artifact label | SHA256 |
|---|---|
| `20260913-140033-8f72c342/summary.json` | `83428fa8fb396628a6da225a3bac544986620c422cd679cad10707f1c88a2302` |
| `consumer-final-9f94-integration.xml` | `ec08991e16c2b8519740393ea563fa8e6889dea08fd1904cad501c821baad84d` |
| `consumer-output-review.json` | `8aa21f688c9539d522fefb275f7b2c626b1739443aa88a3f8ef98c945932620f` |
| `native-ab-report.md` | `94d74b9ab22eae2252f7550d369abf2002b50ae9400e96e5d9c9d5e93a82fd6d` |
| `warm-phase-attribution.json` | `c064b356fa6fb8fb07d40b9162441e6aa82ce46689f2848072e3edb46a641527` |
| `mcp-stdio-investigation.md` | `5ffea7c353796366ae65cb35f78be8ae1631506c6958f87bd502babb622449fc` |

Fingerprints establish file identity, not truth, freshness or an approval.

## Complete capability map

The checked [coverage index](coverage.json) contains 26 families: the four
runtime owners, four consumer/support families and all 18 current business
skills. It maps each to concrete source/help locations, runnable existing tests,
versioned evidence and remaining gaps. The older reports counted 20 skills;
repo initialization and fleet lifecycle are now workspace/package entries and
remain covered below. Counts describe this audit, not an API quota.

| Family | Current surface | Evidence / remaining boundary |
|---|---|---|
| remote-dev | 8 read/write/search/patch tools; Bash and 4 job tools; 3 artifact tools; probe/context | Actual 18-tool gateway and four-container tests; endpoint transport, process/stream and byte preservation. No implied device admission |
| coordinator | `vaws_session`, `vaws_run`, `vaws_execution`, `vaws_finish`, `vaws_message` | Fixed input, resource ownership, wait/control, quiet/release, real isolated messaging; final correctness and measured candidates remain separate |
| knowledge | query/explain/capture; explicit owner maintenance/publication | Earlier optional/inert-provider and dense distribution evidence; current knowledge task owns final catalog/context/curation/media/shared-release validation |
| vaws-top | package fleet queries; local deploy/start/status/restart/stop | Historical released monitor lifecycle and current launcher tests; observation never proves allocation. This checkout selects release `v0.1.2`, not necessarily the running instance |
| local dependencies | status/doctor/sync, immutable environment selection | Existing platform and source-workspace checks; new sync no-knowledge behavior belongs to the integrating source-workspace revision |
| source preparation | requested initialization/forks/update, independent bundles and resume | Actual fixed capture, materialization and controlled layout migration; new source-lock workflow/final head remains its owner's acceptance |
| native clients and routing | Codex, Cursor, Claude, Grok Build, Kimi Code hooks/attachments/gateways | Real selected client/ACP cases plus configuration fixtures; Grok Build evidence does not establish Grok Bot behavior; no blanket GUI certification |
| engineering support | manifests, output envelope, comparability, local runner, projections, path/leak guards | Existing local test cases and actual retained results; no additional Agent-authored record or completion gate |

| Business skill | Reused local JUnit entries | Additional real evidence / limit |
|---|---:|---|
| ascend-memory-profiling | 13 | Attribution logic/fixtures; no new production HBM decomposition |
| ascend-operator-debug | 6 | Case/reference logic; the recorded FP32 operator case covers that case, not all operators |
| ascend-profiling-analysis | 458, including 1 skip | Existing database/report fixtures and analysis logic; no newly captured production profile |
| ascend-profiling-collection | 20 | Collector protocol/readiness/manifest tests; actual new trace collection is separate |
| ascend-tensor-dump | 83 | Dump/comparison/replay fixtures; no new large-model tensor dump |
| ascend-triton-kernel-optimization | 2 | Report/decision logic; no general kernel speedup from these tests |
| ascend-triton-kernel-validation | 6 | Case matrix/report checks; no all-shape/dtype NPU proof |
| ascend-triton-operator-development | 2 | Development evidence logic; not a newly developed device kernel |
| ascend-triton-workflow | 5 | Stage orchestration/report logic; actual stages retain their own device evidence |
| modelscope | 25 | Resume/background/integrity fixtures; no fresh hosted authentication or model download |
| vllm-ascend-benchmark | 42 | Request/metric/report logic; no new throughput measurement |
| vllm-ascend-change-validation | 8 | Evidence/report consolidation; not execution of a supplied patch |
| vllm-ascend-correctness-validation | 29 | Comparison/report logic; no new model-wide accuracy run |
| vllm-ascend-distributed-debug | 9 | Topology/event diagnosis fixtures; no new multi-node failure reproduction |
| vllm-ascend-graph-debug | 9 | Graph/eager evidence analysis; historical actual ACL replay is source/version-specific |
| vllm-ascend-pd-serving | 9 | Topology/role/readiness behavior; no full new PD model deployment |
| vllm-ascend-performance-regression | 27 | Collection/comparability/report logic; managed tool timings are not serving throughput |
| vllm-ascend-serving | 45, including 1 skip | Historical actual Qwen3-0.6B health/models/first-token and ACL replay; no current-pin model validation |

The tests column refers only to the verified historical local snapshot above.
A script being present, help succeeding, a mock returning ready, or an existing
model process is never substituted for an actual claimed device operation.

## Runnable checks and proportionate follow-up

This read-only maintainer command checks the archive's source/test references,
all current skill coverage and evidence/gap references. It imports no runtime
owner, accesses no network, starts no services and scans no business repositories:

```sh
uv run --no-project python docs/validation/check_archive.py
```

It can also verify an existing local-test summary with its contained JUnit/log
files, using bounded reads and matching recorded hashes:

```sh
uv run --no-project python docs/validation/check_archive.py --verify-run-summary PATH
```

`PATH` is a real local summary selected by the maintainer. The command reports
the verified counts and provenance limitation; it does not rerun tests, copy
private logs or manufacture a source revision. The archive checker itself can
be tested with `python -m unittest discover -s docs/validation -p 'test_*.py'`.

When a changed capability needs a new local run, reuse the existing
[bounded runner](../local-tests.md) and select the exact test path from
`coverage.json`, for example:

```sh
uv run --no-project python .agents/scripts/local_tests.py .agents/tests/test_remote_dev_consumer.py --jobs 1 --timeout 120
uv run --no-project python .agents/scripts/local_tests.py .agents/skills/ascend-tensor-dump/tests --jobs 1 --timeout 120
```

This preserves the existing separate-process skill suites, including their
logs and JUnit results. It does not install packages or alter pins. Whole-suite
or device reruns are chosen only when the change and intended claim justify
them; an archive audit by itself does not justify another NPU allocation.

Seven remaining gaps are explicit in the index. Final integrated pins need
their affected checks; native UI needs actual client evidence; a final-version
performance claim needs matched repeated measurements; business device claims
need their actual inputs/results; untested external/platform capabilities stay
unknown; the new knowledge platform has its own final acceptance; and the old
90-suite summary cannot acquire an exact source version retrospectively.

The present audit does not require another unrelated NPU experiment. It reuses
verified results, identifies their limits and leaves capability owners with
specific, bounded follow-up when their final change or a requested claim needs
it. Missing evidence is recorded as unknown, not failure of unrelated work.
