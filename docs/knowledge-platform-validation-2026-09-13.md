# VA reference platform integration

Status: dated installed integration evidence, 2026-09-13; not a runtime contract

This is engineering validation of the reference platform, kept outside the
vLLM/Ascend/NPU/AI/Infra knowledge library. The twelve requested capabilities
are implemented; their actual format conversion, Grok research, source maps,
curation, retrieval and scaling evidence is recorded in the package's
[capability acceptance](https://github.com/vllm-ascend-workspace/vaws-knowledge/blob/c57e7fb3322c8d83669e5c5f827446462892f113/docs/knowledge-platform-acceptance-2026-09-13.md).
The [consumer contract](knowledge-maintenance.md) keeps ordinary tasks at
three optional knowledge tools. External intake, Grok work and hourly feed
transport are independent of task startup and dependency sync.

## Final component selection

| Package | Version / consumed commit |
|---|---|
| vaws-knowledge | 0.7.0 / `c57e7fb3322c8d83669e5c5f827446462892f113` |
| vaws-coordinator | 0.5.0.dev1 / `9f94f27964437f962e6037529ccf2f0b1c709ede` |
| remote-dev | 0.8.0 / `a65362882a85b4d460be3e1d15e90de9fb507e70` |

The consumer selects the knowledge package's existing `code` extra so its
C++ parser uses the declared supported pair: tree-sitter 0.25.2 and
tree-sitter-cpp 0.23.4. This changes the already-present tree-sitter version
from 0.26.0; the installed package count remains 179, with no new model.
Coordinator and remote-dev pins remain unchanged. The locked immutable
environment synchronized successfully with the dev group;
doctor reported success with no warnings. This does not certify unrelated
older running daemons or change existing tasks' fixed environments.

## Exact component checks

[Package PR 34](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/34)
merged as `c57e7fb3322c8d83669e5c5f827446462892f113`. Its head was
`cca9c66ce2f958138eed8241a7fd43162872aa94`; the actual CI checkout was
`4f7eac7050cc46da5079d57b144595efa51c3409`. The tested and merged commits
have the same tree `de276435bf099c0bfb2c671a14e67fda8e137ecd` and parents
`778a7b6b6a6f1b8c541dbdc6a646bc033f5e2c0f` and
`cca9c66ce2f958138eed8241a7fd43162872aa94`.

| PR 34 package CI | Passed | Skipped | Passed subtests | Time |
|---|---:|---:|---:|---:|
| [Ubuntu / Python 3.11](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34749416066) | 541 | 4 | 12 | 25.96 s |
| [Windows / Python 3.13](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34749416072) | 543 | 2 | 12 | 216.72 s |
| macOS / Python 3.13, same native run | 543 | 2 | 12 | 192.34 s |

Each native XML has 545 actual `testcase` elements, including two skips;
the suite's `tests=557` includes twelve subtests. There are no failures or
errors. Windows JUnit SHA256 is
`08fdb6f746f52d1561d3fc761a482048fe33e4f8a7e32696f8064e074e5c80ed`;
macOS is `c45c043921e80ea006d52c084a6263f8151a5acbfd4d9185781294f46c16adb9`.
Ubuntu's count is from its log. The retained component
`.vaws-local/parser-guard-ci/acceptance.json` has SHA256
`686b0561066ceca4e25f00ccdcc6becd6a5b2a3e5b0100b5ec42b8030d587836`.
The native distribution-chain test retained its missing-model-cache skip;
the earlier actual native distribution experiment remains separate evidence.

### Earlier PR 33 stage

[Package PR 33](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/33)
merged after all three final checks passed. Its head was
`3a2e8707eed610f681f7941c0845353f8f46df02`; each CI job checked
`cea65a73ea1462a3b0c64cb07d195b61ad70694d`. Git confirmed that this merge-test
ref and consumed merge `778a7b6b` have the same tree
`0e855733d5b269e43df6b92258d4ea01bfbacf73` and parents.

| PR 33 package CI | Passed | Skipped | Passed subtests | Time |
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

At the earlier `778a7b6b` stage, eight affected consumer suites passed in 15.925 s: client wiring, capture/query
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
Windows 613 s). That CI identifies this earlier functional head. The final
`c57e7fb3` pin and `code` dependency selection are later changes;
[PR 169 checks](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/169/checks)
and the [PR state](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/169)
carry the final consumer commit's CI and merge outcome. This dated report does
not pre-certify that future outcome.

After the final `c57e7fb3` installation, the same eight consumer suites passed
in 18.118 s, with 75 retained JUnit entries and zero failures, errors or skips.
The archive checker reread the XML/log hashes. The new summary is
`.vaws-local/test-runs/20260913-173301-d055dda5/summary.json`, SHA256
`89ec2c57b56ba9164bd653c968a12f116ab588ed0d30873b993cbd4e32fd3a69`.
As before, the test summary does not embed runtime revisions; the final
selection and isolated installed probes establish the package identity.

The actual Grok export, fixed exporter, personal Git feed, independent wheel,
and natural 16:00 Windows synchronization are preserved in
[component and deployment evidence](validation/knowledge-component-2026-09-13.md).
The daily Grok PR routine is at 09:00 Asia/Shanghai and the weekly topic/digest
routine at Saturday 10:00. Local feed transport runs hourly and at user logon.
The natural local run took 1.357 s with zero source downloads and task result
zero. Future scheduled Grok execution is not counted as an elapsed run.

## Earlier installed preparation at 778a7b6b

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

## Earlier installed MCP acceptance at 778a7b6b

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

## Final installed preparation and MCP at c57e7fb3

The final immutable environment installed knowledge 0.7.0 at
`c57e7fb3322c8d83669e5c5f827446462892f113` with the supported `code` extra.
Selection, sync and doctor receipts are retained as
`final-parser-pin-sync.json` and `final-parser-pin-doctor.json`; doctor returned
success, exit zero and no warnings. Its report also explicitly identifies
older running daemons; it does not claim to have upgraded every live instance.

Actual final `prepare` returned ready with 94 documents. It took 25.224 s
including process startup while the eight consumer suites ran concurrently,
so this is not an isolated performance benchmark. The package bootstrap
revalidation parsed 65 documents and read 330,151 bytes once. This preparation
work is outside warm queries. The retained result is `final-parser-pin-prepare.json`.

A fresh isolated installed stdio MCP run at `c57e7fb3` passed all 20 unchanged
original-source questions in top8, four full-body/hash explanations and all
20 source-span checks. Both lexical and vector routes participated, with
exactly three tools, zero degraded/incomplete responses and no capture calls.
Configuration, source files, installed inputs and existing backend process
identities stayed unchanged. The 94-document catalog snapshot
`b1d318f2ef3f4f3c8b501eeac8686a5a:3` stayed unchanged across the run.

Initialize took 789.853 ms and the first query 1,402.685 ms. Nineteen warm
queries had p50 68.919 ms, p95 93.642 ms and maximum 99.054 ms. Maximum
structured content was 15,292 bytes and the full MCP serialization 35,362
bytes. These are bytes, not tokens, and the sample measures originating-source
retrieval, not held-out relevance or native 100k performance. The original
provisional 17/20 and the earlier `778a7b6b` 20/20 records remain separate.
The component's private `final-parser-pin-native-mcp.json` has SHA256
`19a1cf16d476bed4297c9ce6887cbba0d082667e44b3be26235b8a37dedbe294`.

## Installed C++ parser correction

A late actual code-map invocation in the base consumer environment exposed
a native crash: tree-sitter 0.26.0 with tree-sitter-cpp 0.23.4 exited
`3221225477` and produced no stdout/stderr. Earlier package CI selected the
declared 0.25.2 test/code extra and therefore did not establish this base
environment's native-parser compatibility. The failed subprocess result is
retained in `code-map-native-probe.json`.

After selecting the existing `code` extra, the same installed 0.7.0 component
at `778a7b6b` used 0.25.2/0.23.4 and actually mapped the three pinned
Python/C++ files at vllm-ascend
`b36dc06d8e1b914e7a1318ee32310ef1d502007a`. It read 83,590 bytes,
parsed three files in 419.65 ms (679.983 ms including subprocess startup),
and returned ready with two explicit static-scope gaps. This is source
navigation, not runtime dispatch or NPU evidence. The compatible-install
result and complete map are retained separately from the failed probe.

The package correction checks version metadata before either native import;
unverified versions produce a `parser_unavailable` gap and preserve the last
complete map. A C++ cache policy revision rejects old unverified parse entries
while retaining Python caches. Forty-eight affected tests passed, including
the legacy-cache regression that failed before this correction.

A complete CLI probe in the original 0.26.0 environment, explicitly loading
the corrected working-tree source, exited 2 with a partial map and neither
native module loaded. It read one pinned 51,192-byte C++ file; the process
took 471.992 ms. This source-override probe is distinct from installed-release
acceptance and is retained in `guard-code-map-cli-probe.json`.

The final installed `c57e7fb3` CLI was then tested without a source override,
using tree-sitter 0.25.2 and tree-sitter-cpp 0.23.4. It mapped the same three
pinned files and 83,590 bytes in 457.89 ms internally (851.216 ms including
process startup), returning ready and complete with the same two static-scope
gaps. An unchanged repeat reused all three files, parsed zero and read zero
source bytes: 246.06 ms internally and 432.633 ms with startup. This verifies
the installed supported parser and cache reuse, not runtime dispatch.
`final-pin-code-map-probe.json` retains both runs; the resulting map SHA256 is
`cf08d69d24a071adc4560c679f4d51a7c1e4489965f72dd395071933b6c1529b`.

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
