# VA reference platform integration

Status: dated installed integration evidence, 2026-09-13; not a runtime contract

This is engineering validation of the reference platform, kept outside the
vLLM/Ascend/NPU/AI/Infra knowledge library. The twelve requested capabilities
are implemented; their actual format conversion, Grok research, source maps,
curation, retrieval and scaling evidence is recorded in the package's
[capability acceptance](https://github.com/vllm-ascend-workspace/vaws-knowledge/blob/778a7b6b6a6f1b8c541dbdc6a646bc033f5e2c0f/docs/knowledge-platform-acceptance-2026-09-13.md).
The [consumer contract](knowledge-maintenance.md) keeps ordinary tasks at
three optional knowledge tools. External intake, Grok work and hourly feed
transport are independent of task startup and dependency sync.

## Final component selection

| Package | Version / consumed commit |
|---|---|
| vaws-knowledge | 0.7.0 / `778a7b6b6a6f1b8c541dbdc6a646bc033f5e2c0f` |
| vaws-coordinator | 0.5.0.dev1 / `9f94f27964437f962e6037529ccf2f0b1c709ede` |
| remote-dev | 0.8.0 / `a65362882a85b4d460be3e1d15e90de9fb507e70` |

Only the knowledge version and its Git source changed in the dependency files.
The locked immutable environment synchronized successfully with the dev group;
doctor reported success with no warnings. This does not certify unrelated
older running daemons or change existing tasks' fixed environments.

## Exact component checks

[Package PR 33](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/33)
merged after all three final checks passed. Its head was
`3a2e8707eed610f681f7941c0845353f8f46df02`; each CI job checked
`cea65a73ea1462a3b0c64cb07d195b61ad70694d`. Git confirmed that this merge-test
ref and consumed merge `778a7b6b` have the same tree
`0e855733d5b269e43df6b92258d4ea01bfbacf73` and parents.

| Final package CI | Passed | Skipped | Passed subtests | Time |
|---|---:|---:|---:|---:|
| [Ubuntu / Python 3.11](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34747646848) | 531 | 4 | 12 | 20.50 s |
| [Windows / Python 3.13](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34747646837) | 533 | 2 | 12 | 220.61 s |
| macOS / Python 3.13, same native run | 533 | 2 | 12 | 165.68 s |

Each native JUnit suite reports 547 tests including twelve subtests; it has
535 `testcase` elements including two skipped cases, with no failure/error.
Windows SHA256 is
`e79ac44d802670b2a18726280b52ac91eb9832ddf12ab43617bc08248b17acf6`;
macOS is `09aac9082ff77a514a558b279e0113c1b25681fc8ba995a7ad161a72b9ccfd61`.
Ubuntu records its count in the job log and did not produce JUnit. The native
distribution model-cache test was skipped when its required cache was absent;
the earlier actually executed distribution chain remains separate evidence.

The last combined local affected group passed 114 tests and nine subtests.
The intermediate full local group passed 517 tests, four skips and twelve
subtests before the final fusion/save changes; it is not relabelled as final.
Old-algorithm regression probes reproduced the four fusion failures and three
save-preservation failures before their fixes. Two independent final reviews
found no blocking issue.

## Consumer checks and deployed maintenance

Eight affected consumer suites passed in 15.925 s: client wiring, capture/query
flow, actual MCP initialize/list, preparation, setup, installed shared corpus,
native summary hooks and shared startup. Their eight retained JUnit files
contain 75 entries, zero skips and no errors/failures. The bounded archive
checker reread all JUnit/log hashes. The summary SHA256 is
`996f9757dc7660528c939c2683c01ea94ab214d8c476517666ecd377cd64e50e`.
This local runner summary does not embed its own runtime revision; the
separate selection/sync/doctor and installed MCP evidence identify the
consumed package. Consumer [CI 34748066882](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/actions/runs/34748066882)
passed all three platforms for functional head
`52b3bec5d17371447c6902ef1c0c24a011e17836` (Ubuntu 82 s, macOS 200 s,
Windows 613 s). This report and the final archive updates are subsequent
documentation; [PR 169](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/169)
retains the final documentation-head CI and merge status separately.

The actual Grok export, fixed exporter, personal Git feed, independent wheel,
and natural 16:00 Windows synchronization are preserved in
[component and deployment evidence](validation/knowledge-component-2026-09-13.md).
The daily Grok PR routine is at 09:00 Asia/Shanghai and the weekly topic/digest
routine at Saturday 10:00. Local feed transport runs hourly and at user logon.
The natural local run took 1.357 s with zero source downloads and task result
zero. Future scheduled Grok execution is not counted as an elapsed run.

## Actual installed preparation

The first final-version preparation found a busy lock and a historical ready
record without a catalog. It was not accepted as successful final preparation.
Six obsolete knowledge MCP workers were still writing this instance's old
maintenance state and repeatedly indexing the same bootstrap notes. A bounded
one-time upgrade used Windows Restart Manager's resource-owner observations,
exact old MCP commands and matching process creation times to retire only the
actual holders of the knowledge locks. No recursive process-tree stop was used.

The operation retained hashes/bytes for all 35 selected notes, metadata and
configuration files. All three existing model/backend process identities were
unchanged; native clients and unrelated task runtimes were preserved. For
21.26 seconds afterward, the maintenance file stayed unchanged and the three
knowledge locks had no owner. This is an executed local upgrade operation,
not a new per-task check or a general promise of mixed-version compatibility.

Final installed `prepare` then returned `status=ready`, `ready=true` in
27.720 s, with 94 catalog documents and the shared prepared source identity
aligned. Local reconciliation checked 92 notes, upserted 87, reused five and
reported no errors. Its shared pack remains Git revision
`f21e048537a9f6de52760fad97fccb5c4da32be2`; the existing vectors were retained.
The initial busy result, exact process-owner audit and completed preparation
are retained separately in private deployment evidence.

## Final installed MCP acceptance

The isolated interpreter probe verified the installed 0.7.0 distribution and
Git commit `778a7b6b6a6f1b8c541dbdc6a646bc033f5e2c0f`, rather than importing
the component worktree. Its actual stdio MCP server used the real configured
project mounts, CPU embedding service and shared references. All twenty
unchanged source-bound questions retrieved their designated source within
eight results; all four Grok pages were found. Four explanations matched
original bodies/hashes, and all twenty selected citation spans passed their
line/column/text/hash checks. Lexical and vector retrieval both participated,
with zero degraded or incomplete responses and exactly three listed tools.
Maximum query structured content was 15,292 bytes; the full MCP result also
carries a text representation and reached 35,362 bytes. These are distinct
serialization measurements, not token counts.

The first query took 1,583.029 ms. Nineteen warm queries had p50 69.020 ms,
p95 85.843 ms and maximum 87.699 ms. This measures a 94-document real catalog,
not the 100k fixture. Original-source recall was 20/20; the relevance of every
other returned page was not labelled or scored. The failed provisional 17/20
run is retained, with its original questions and outputs; the final run did
not expand relevance labels or lower its threshold.

No capture, explicit maintenance, source/config edit or backend stop occurred
in the final MCP test. Source files, package inputs, configuration and existing
backend PIDs remained unchanged, and its own stdio server exited cleanly.
Private evidence includes `final-installed-native-mcp.json` and the separate
preparation, immutable selection, test-run and old-provider retirement records.
The final MCP report SHA256 is
`84f23b330b0b3bdbacfb50581a87a8674ab3bec88206ff9e854ff5203d42376e`.

## Measurement boundaries

The library is optional reference. Generated notes and ranking scores do not
establish truth, applicability or NPU correctness. The 13 authored retrieval
questions are regression fixtures, not held-out quality labels. Real new
Grok material currently covers selected NPU platform and ACLGraph sources,
not a complete AI/Infra corpus.

The development host has about 64 GiB RAM. Native CPU embedding processes
were measured separately; no new local multimodal model is added. The
10k/100k file-capacity runs use fixture vectors and cannot certify native
100k embedding throughput or execution on a physical 16 GiB laptop. The
100k final lexical query p95 was 269.32 ms and first verified maintenance
543.71 s at the separately recorded implementation, with maintenance outside
the query path. Static whole-tree C++ maps remain partial where syntax,
macros or dynamic dispatch cannot be resolved.
