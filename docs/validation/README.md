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
initially audited consumer checkout was `7f2ebb8d2be4c0774f9663b1cfcef43dc3a714dd`.
The reference/coverage audit was refreshed at
`75a886eb145d2f624f9c9b15748a892a8c317210`, after the earlier integration audit
at `d14f5af40bcf1b9fd02906be08fb29ea211db60d`. This checkout includes the final
source-workspace evidence in PR 168, merged at
`71cd235560c59ea1f82936de11e9a42e666c9ca4`. Subsequent knowledge component
evidence includes merged PRs 30–33 and actual cloud-feed/local scheduled return.
The final consumer selects knowledge `778a7b6b`; dependency sync, doctor and
eight affected local suites passed. Final installed native acceptance passed
at that pin, and consumer PR 169 functional head `52b3bec5` passed three-platform
CI. Later documentation-only revisions keep their own CI status in the final
report.
These facts do not relabel earlier device or performance runs.

## Versioned evidence

| Evidence | Actually established | Version / limitation |
|---|---|---|
| [Existing-container follow-up](../existing-container-validation-2026-09-13.md) | Final installed four-machine 32/32 checks; 12 owned jobs quiet; original container/code/environment preserved; real SDK gateway exposed 18 remote tools without task context | remote-dev `a65362882a85b4d460be3e1d15e90de9fb507e70`, coordinator `921ce2af`, knowledge `3a65926d`; CPU transport and script semantics, no NPU-model result |
| [Managed final implementation](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/a483724f89625e2eec1479bcaf48f8604bbf99c2/docs/managed-performance-redesign-2026-09-13.md) | Real MCP SDK/SCM input isolation, bounded wait with responsive control, actual final consumer integration: 88 passed, 1 skipped, 20 subtests | coordinator `9f94f27964437f962e6037529ccf2f0b1c709ede`, consumer `a483724f89625e2eec1479bcaf48f8604bbf99c2`; local/CI behavior, not final-version performance |
| [Managed measured pairs](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/a483724f89625e2eec1479bcaf48f8604bbf99c2/docs/managed-performance-redesign-2026-09-13.md) | Native submit-to-release 98.61 → 96.78 s; warm 26.87 → 28.31 s; actual FP32 kernel/reference check | baseline `384b89b`, native candidate `a91f19a`, warm candidate `d2095dc`; one serial pair, unequal immutable/editable installation, B reused A bundle, concurrent Windows tests; no warm speedup or universal 1-second result |
| [Source-workspace implementation](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8/docs/source-workspace-validation-2026-09-13.md) | Four-machine fixed three-repository capture/materialization and original-state preservation; 24 local layout migrations plus 3 boundary cases; final exact-head workspace/skill CI passed on Linux, Windows and macOS | source binding experiment uses coordinator `66e2d2b3aa30512eef433e0594ebf815e574b6ce`; final CI head `4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8`; neither proves new NPU compatibility or every native GUI |
| [Final source-workspace record](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/71cd235560c59ea1f82936de11e9a42e666c9ca4/docs/source-workspace-validation-2026-09-13.md) | Final installed four-machine 28 core checks; actual start and unchanged-context resume; automatic source-lock PR 167 merge and no-change run | coordinator `9f94f279`, remote-dev `a6536288`; cited published evidence, with its original timing, audit and UI/NPU limits preserved; see below |
| Real Kimi source-workspace ACP | Actual installed Kimi 0.42.0 initialize/session, real SessionStart hook, persisted cwd, 3 prepared sources and clean EOF: 10 checks passed | coordinator `a91f19a`, remote-dev `a6536288`, knowledge `485ddc0`; local lifecycle used a noncredential sentinel and loopback discard URL, with no prompt/LLM/authenticated inference; not Grok Bot or all-client UI acceptance |
| [Shared-host execution and messaging](../shared-root-host-validation-2026-09-12.md) | Four managed CPU runs, busy-NPU queuing, isolated-identity real SSH message/reply delivery, 1,103 native artifacts restored/loaded across four machines | coordinator `0d0e814dc673677be62d2fa60e204552d57e22ce`; busy devices prevented new kernel runs; old periodic updater details are superseded by the current contract |
| [Windows/WSL platform pass](../windows-validation-2026-09-11.md) | Three owner suites, all then-current skill suites, 120 ordinary live SSH calls, real dense knowledge release/import/switch and fleet process lifecycle | owner commits are listed in that report; no NPU work, live ModelScope authentication/download, macOS or ARM64 acceptance |
| [Six scenarios](../six-scenario-performance-2026-09-13.md) | Actual source/native reuse, fixed inputs, owned kernel and release evidence; independent direct/managed Agent samples | vLLM `e7739c8720974cdd442c0f051cc08a41a4e799c2`, Ascend `88398f3c885d1264cde65069dc8a3e9adf6487f0`; each arm keeps its own coordinator/version and timer; universal six-case speed target not met |
| [Knowledge 0.6.0 adoption](../knowledge-adoption-2026-09-13.md) | Optional three-tool contract, lexical/vector fusion, source excerpt evidence and bounded owner worklist | consumed commit `485ddc0d71e86915487a1204032426a3d874ba0e`; later catalog/curation/media/release acceptance is recorded separately below |
| [Knowledge component PRs 30–32](knowledge-component-2026-09-13.md) | Exact component/intake CI checkout/counts, retained local JUnit integrity, actual Grok export, live feed import and successful natural 16:00 Windows trigger | PR 32 merge `52754b5e`; cloud/installed-wheel revisions remain explicit; later integration belongs to the final report below; future scheduled Grok cycles are not counted as elapsed runs |
| [Knowledge platform final integration](../knowledge-platform-validation-2026-09-13.md) | PR 33 three-platform package CI, selected `778a7b6b` pin, sync/doctor, eight local suites with 75 successful JUnit entries, actual installed MCP 20/20 original targets in top8 and four explains, and PR 169 code-head three-platform CI | Package checkout `cea65a73` and consumed merge share tree `0e855733`; consumer CI identifies head `52b3bec5`; local summary lacks embedded runtime revisions, while separate installed evidence identifies `778a7b6b`; later documentation-only CI retains its own status |

GitHub was read again during this audit. Coordinator PR 33 and consumer PR 165
were merged. Their exact tested heads were successful in
[coordinator CI 34741531389](https://github.com/vllm-ascend-workspace/vaws-coordinator/actions/runs/34741531389)
and [consumer CI 34741553507](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34741553507).
The consumer merge was `989dd74e04fac437661723a8938e6c89a5b26bb5`.
[Consumer PR 166](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/166)
was rechecked after integration: merged at
`a80923e6325fb53629332b4f5688fe37b28e0f3e`, with final head
`4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8` passing
[CI 34743399890](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34743399890)
on Ubuntu/Python 3.11 and Windows/macOS/Python 3.13. Job durations were about
94, 546 and 256 seconds respectively; these are CI wall times, not task-latency
benchmarks. These are observations at the archive cutoff; later deployment state
must come from its actual result. A passed CI run proves only its selected jobs.

### Final source-workspace evidence

[PR 168](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/168)
merged the final dated report on 2026-09-13 at 07:10:32 UTC. Its PR head was
`697f597e2f108b2d7f23521d71a0b1087c2bf28a`; the squash commit was
`71cd235560c59ea1f82936de11e9a42e666c9ca4`.
[CI 34744558304](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34744558304)
completed successfully on Ubuntu/Python 3.11 and Windows/macOS/Python 3.13.
The actual checkout logs identify merge-test commit
`3c72182e3811c0dceee6cb8ce09905d685a6fcbc`, combining that PR head with
`9bf2265791bb11acf8e8bb1e22637b926d5bd350`; this is not a bare-head or
post-squash rerun.

The [published report at the merge](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/blob/71cd235560c59ea1f82936de11e9a42e666c9ca4/docs/source-workspace-validation-2026-09-13.md)
records the final installed four-machine repetition using coordinator
`9f94f27964437f962e6037529ccf2f0b1c709ede`, remote-dev
`a65362882a85b4d460be3e1d15e90de9fb507e70`, and consumer
`4b11ae543ac4b9862fe6be9a4a82d14e55ecd9d8`: all 28 core checks passed,
existing container/source/script state was preserved, and self-created fixtures
were cleaned. The older `66e2d2b3` experiment above remains a separate record.

The same report records actual post-merge preparation at workspace `a80923e6`
in 45.287248 s and same-context resume in 0.651009 s. After the automatic lock
update, another resume took 0.620983 s and kept the old workspace/Ascend inputs,
environment receipt and ready-record hash unchanged; four read-only Git queries
were observed. These are individual observed paths, not cold-start or latency
guarantees. The first UTF-8 audit-script failure lost the ready-publication
ordering trace; that live run does not prove atomic publication ordering.
The report also retains its older Kimi ACP environment and no-GUI/no-LLM limits.

The report links the actual [source-lock maintenance run 34743891383](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34743891383),
which created [PR 167](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/167),
validated head `3f27d82fc37e8ad7504a7aefece4a5672b71987e`, and automatically
merged `9bf2265791bb11acf8e8bb1e22637b926d5bd350`.
The later [unchanged run 34744383856](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34744383856)
created no PR and skipped validation/merge. Existing tasks retained their fixed
inputs after that maintenance update.

This refresh independently read the published report and PR/CI metadata and
checkout logs. Its referenced private source-workspace artifacts were not
available at the supplied local location and were not searched across other
sessions or recopied. The runtime observations above are therefore attributed
to that report, not a new raw-artifact audit or rerun. They do not establish
all-client UI behavior, new NPU compatibility, model accuracy or throughput.

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
| knowledge | query/explain/capture; explicit owner maintenance/publication | PR30–33 CI, final installed MCP 20/20 retrieval and four explains, PR169 code-head CI, optional/inert-provider evidence and actual independent cloud/local feed transport; fixture and hardware limits remain explicit |
| vaws-top | package fleet queries; local deploy/start/status/restart/stop | Historical released monitor lifecycle and current launcher tests; observation never proves allocation. This checkout selects release `v0.1.2`, not necessarily the running instance |
| local dependencies | status/doctor/sync, immutable environment selection | Existing platform and source-workspace checks; package-only sync and no knowledge preparation are covered by merged PR166 and its three-platform control-plane CI |
| source preparation | requested initialization/forks/update, exact source-lock pairs, independent clones and resume | Current `sources.lock.json` supplies official development/release-vLLM pairs with the same Ascend revision; actual capture/migration and exact-head CI are retained. A declared pair is not an NPU compatibility result |
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
Current `vllm/` and `vllm-ascend/` are independent repositories prepared on
demand from `sources.lock.json`, not parent Git submodules. Source declarations
and their updater belong to `workspace_sources.py` / `vaws_source_lock.py`;
the retired pin-resolver script is not an active check. The refreshed coverage
index includes these owners and the current source-lock/view tests. Read the
[current source contract](../source-workspace.md) for behavior; dated reports
retain the layouts and versions they actually exercised.

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

Five remaining scope gaps are explicit in the index. G1 and G6 are closed by
PR 33 package checks, the final installed native result, affected local consumer
suites, PR 169 functional code-head CI and actual independent feed return.
The retained boundaries are native UI evidence; matched repeated measurements
for a new final-version performance claim; actual inputs/results for business
device claims; untested external/platform capabilities; and the old 90-suite
summary's missing source/runtime provenance. Future Grok cycles are not missing
functionality and are not counted as elapsed runs. Later documentation-only CI
is tracked at its actual revision in the final report.

The present audit does not require another unrelated NPU experiment. It reuses
verified results, identifies their limits and leaves capability owners with
specific, bounded follow-up when their final change or a requested claim needs
it. Missing evidence is recorded as unknown, not failure of unrelated work.
