# Diagnostics validation

Status: dated implementation, release and deployed-worker validation evidence,
2026-09-13. Test, dependency and deployment boundaries are distinguished below.

The diagnostics work adds automatic operation IDs, severity, phase timing and bounded diagnostic references at existing tool boundaries. It also preserves failures that happen before optional dependencies are available. Tools do not require an Agent to supply trace fields, collect a second summary or wait for the reporting worker. The contract is described in [diagnostics-system.md](diagnostics-system.md).

## Coverage

| Owner | Implemented and locally exercised boundaries |
| --- | --- |
| Workspace | Early CLI/parser failures, native hooks, persistent MCP provider calls, startup and source selection, lock wait, Git and clone work, environment installation and handoff, business helper envelopes, optional knowledge hooks and detached ModelScope workers |
| Diagnostics core | JSONL recording, levels, context propagation, rotation, redaction, exception classification, bounded collection and public projection, subprocess output capture, reporter state and Linux user-service installation |
| remote-dev | Every public tool, connection and RPC phases, file operations, owned jobs, shell launch and completion; transport certainty remains explicit |
| Coordinator | Every public tool, preparation and resource phases, asynchronous admission and background lifetime, observation, evidence and release |
| Knowledge | Public entries, optional/degraded results, maintenance and feed/index work, subprocess boundaries and output collection |
| Fleet monitor | CLI/HTTP boundaries, probe and collection work, persistence, scheduler liveness and health |

The runtime-owner catalog checks cover 23 public remote-dev/coordinator entries. Common dispatch supplies their boundary records; named internal phases expose work that a single outer duration would conceal. Diagnostic context travels through existing process/RPC metadata and owned records, without becoming task identity, resource authority or a second execution ledger.

Workspace stdout retains JSON or MCP protocol output. Human progress remains on stderr. Error details retain the owner's category, retryability and known submission state. Explicit parser and unsupported-capability errors are classified as caller errors; generic validation, permission and business exit codes are not automatically reclassified. A failed diagnostic sink does not establish that a submitted workload stopped.

## Local verification

These are overlapping test runs, not an additive count of unique tests. Windows and WSL results below are local evidence, not a claim that every platform or complete runtime suite was rerun.

| Test boundary | Recorded result |
| --- | --- |
| Workspace envelope, operator, hook, transport, MCP and leak regressions | 198 passed, 2 skipped, 103 subtests |
| Workspace bootstrap export/ingest, MCP and envelope follow-up | 109 passed, 13 subtests |
| Workspace observer, native copy and environment follow-up | 97 passed, 6 subtests |
| POSIX workspace adapter, including inherited-lock fork regression | 17 passed; 4 MCP-specific cases deselected |
| ModelScope download/verification and real detached Windows worker fixtures | 22 passed, 18 subtests |
| Benchmark helpers | 30 passed, 12 subtests |
| Serving helpers | 27 passed, 2 skipped, 23 subtests |
| Profiling collection / selected analysis boundaries | 17 passed, 5 subtests / 20 passed |
| Diagnostics core broad Windows run before the service-parser correction | 98 passed, 4 skipped |
| Core logging/context/redaction/bundle on WSL | 49 passed |
| Core actual process-output capture | 6 passed on Windows and 6 on WSL |
| Final service installer, including actual Linux parser validation | 23 passed on WSL; 20 passed and 3 POSIX skips on Windows |
| remote-dev broad Windows run | 467 passed, 102 platform skips, 152 subtests |
| Coordinator affected Windows / Linux runs | 153 passed, 1 skipped, 32 subtests / 94 passed, 20 subtests |
| Runtime asynchronous lifetime follow-up | 28 passed, 1 skipped |
| Knowledge affected broad Windows and WSL runs | Each: 127 passed, 1 skipped, 5 subtests |
| Knowledge later entry follow-up on WSL | 56 passed, 5 subtests |
| Knowledge final maintenance-worker follow-up on WSL | 32 passed, 1 skipped |
| Fleet monitor affected Windows and WSL runs | Each: 37 passed, 9 subtests |
| Fleet monitor final WSL follow-up / HTTP failure follow-up on both platforms | 38 passed, 9 subtests / each: 32 passed, 9 subtests |

Both runtime-owner MCP servers also passed real stdio round trips with the locked official MCP SDK 1.30.0 on Windows: two cases passed. An additional SDK 2.2.0 run passed two cases; Linux follow-ups included the actual 1.30.0 SDK. These checks exercise protocol framing with owned local child processes, rather than replacing the server with a JSON formatter stub.

The workspace skill catalog contained 18 skills with zero findings; generated Claude projections had no drift. The recorded tracked-file leak scan covered 503 files, with zero findings, 57 reviewed allowlist matches and no skipped files. These counts describe that candidate scan, before subsequent release/report additions. Diff whitespace checks passed. Workspace test processes used isolated diagnostic roots. A later owner test run exposed missing isolation in knowledge tests; the correction and exact handling of those synthetic events are recorded below.

The subsequent consumer check installed a new immutable developer environment through `vaws_deps.py sync --locked --group dev`, with no source overlay. The installed identities matched the lock: remote-dev 0.9.0 at `b68e6f28fce388ca34b6186ae0bf1d28727051b2`, coordinator 0.5.0.dev2 at `5adfbe1452c02811171a93e85d4afd9bbe51398d`, knowledge 0.7.1 at `e08ef0e3e2f5b35ae4f9842d69e012d6cd8d27c4`, diagnostics 0.1.1 at `3595e4e5ae776a1728099f237792ffb022ae12c8`, and MCP 1.30.0. Knowledge's catalog was generated from the matching installed package metadata, without starting its backend. Lock and catalog checks and the normal doctor command passed. This is an installed-source identity check, not a claim that every listed pull request had merged.

An initial dependency assertion still expected the old direct-dependency list and failed when shared diagnostics was added. The assertion now includes diagnostics and verifies its exact lock/source/version agreement, while retaining the separate three managed-capability names. The installed adapter/MCP/envelope/leak/hook/dependency run then passed 194 tests and 103 subtests, with one platform skip. It used the earlier knowledge commit `0ff431808b8f73af7b7555f1eeca45722af42ba2`; the final knowledge-only import correction prompted a fresh immutable environment and 51 passing dependency/catalog/knowledge tests plus five subtests, including the mainline removal of duplicate local knowledge bodies. These runs overlap and do not claim a full workspace suite. Diagnostic, remote and coordinator pins stayed fixed across them.

A later dependency refresh selected remote `8796b91e74f9968791176cd330fb110f269f0774`, coordinator `92264a28fcda5b0b85f9c36f2907fa91948760f9` and knowledge `0457d9d8cdb4d105d1d38820f9211fc0b73f42e7`, with unchanged package versions and diagnostics pin. Remote/coordinator changes in that refresh were limited to CI and test fixtures, including the final correction of a legacy cancellation fixture. Knowledge distinguished expected redaction findings and explicit parser errors from actual tool failures and isolated test logs. Its owner reported 80 passing tests and three subtests on each of Windows and WSL. The consumer created a separate immutable developer environment and rechecked installed commit identities, doctor, lock and catalog successfully; it did not rerun the earlier large consumer suites for this refresh.

## Failure and safety evidence

- A missing diagnostics package produces a bounded, static bootstrap failure event. The actual core collector and ingester accepted it, and repeated ingestion did not create another incident. Help and successful interpreter handoff did not generate false failure records.
- Unwritable diagnostic storage preserved business return values and original exceptions. Real workspace FD-capture tests wrote 1 MiB through a child with failed storage; both normal and failed-storage cases passed on Windows and WSL without a blocked pipe, recursive warnings or a replacement traceback.
- Collectors buffer complete lines before redaction. Split secret tokens, oversized lines and unfinished fragments have regression coverage; omitted content is recorded as a gap rather than saved as supposedly safe fragments. Rotation and a detached worker continuing after its launcher exits were exercised.
- A real POSIX fork while another thread held the adapter lock completed without inheriting a deadlock. Existing custom exception hooks remained callable. Captured output belongs to the long-lived worker, rather than relying on its short-lived launcher to drain it.
- Runtime tests covered disk faults, authoritative owned-state faults, cancellation and lost acknowledgements without unsafe replay. Diagnostic failure stays secondary; failure to persist execution authority remains a control failure.
- Scoped coordinator support artifacts refer to the requested owned execution and exact local events. Hashes describe the actual artifact bytes; omitted evidence is explicit. This is not a scan of every daemon or host log.

The first installed Linux user-service attempt exposed a real parser defect missed by the original stub-manager tests: systemd treated the quoted `WorkingDirectory` as a non-absolute path and refused the unit before worker startup. The correction uses `/`, since worker inputs and optional Grok directories are absolute. A real `systemd-analyze verify` test accepts the corrected generated unit and rejects the original form. When the analyzer is available, installation validates the staged unit before replacement; rejection retains the previous unit and does not reload or start it. Its absence is returned explicitly without installing another package. These tests do not themselves prove a deployed worker is healthy.

Service tests also preserve the first installation's observation start, unrelated units and drop-ins, reporting state and private configuration. Optional authentication uses a separately supplied regular, owned, mode-0600 environment file whose contents the installer does not read or embed in the unit. Unit journal rate limits do not replace the administrator's total journal-capacity policy.

A controlled diagnostic issue and Grok-comment exercise completed, and its [test issue](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues/173) was closed. This establishes that exercised publication path, not a guarantee of delivery during every network or service failure. Normal tools still finish independently of reporting.

## Measured logging overhead

| Measurement boundary | Control | Observed | Difference |
| --- | --- | --- | --- |
| Fresh synthetic Python CLI, complete process lifetime; 16 alternating pairs | Median 67.710350 ms | Median 173.935400 ms | Difference of medians: 106.225050 ms |
| Public remote listing formatter, INFO; 600 calls per arm, real local JSONL I/O, stubbed transport | Median 0.0101 ms | Median 0.2141 ms | 0.2040 ms per call |
| Same formatter with DEBUG | Median 0.0101 ms | Median 0.23925 ms | 0.22915 ms per call |

The synthetic CLI business JSON was identical. Its control range was 64.802700–93.212500 ms and observed range was 164.220700–213.547200 ms. A separate warm loop of 100 operations and 300 phases took 50.442200 ms in total. The CLI sample used development source, and minor output/error-boundary edits followed it; it is not an exact final-release performance measurement.

The runtime formatter sample used six alternating batches of 100 calls per arm. INFO's observed p95 was 0.2954 ms, while its first observed call took 2.5406 ms. It measures local instrumentation cost with real file I/O, not SSH latency, worker bootstrap, workspace startup or an NPU workload. Cold interpreter/import cost and steady-state recording cost must remain separate.

## Acceptance limits

This logging change did not rerun the remote NPU correctness/performance matrix, launch a real knowledge backend or model, or exercise every fleet host. Business helper tests preserve contracts and controlled process behavior; they do not replace device execution evidence. Existing performance reports retain their original versions and timing boundaries.

Phase durations may overlap, and child phases may be included in their parent. They cannot be summed into a new total or differenced across unrelated monotonic clocks. Admission receipt, background completion, readiness, quiet process state and resource release remain distinct events. Scoped support evidence does not claim a complete cross-host trace or a new hard watcher-shutdown deadline.

Early test attempts using an older developer environment failed on stale runtime APIs; the source-level passing runs used the intended developer interpreter with candidate overlays. The runtime-only environment correctly omitted pytest. The later installed check above separately establishes its exact package identities and lock/catalog agreement. The release CI and deployed-worker evidence below is independent of those source-overlay tests.

## Released and supervised worker acceptance

The independently installed worker is diagnostics **0.1.2**, built from
`ad90ac4edfb7294e65ecd1890b7e8c2b3cd2fdd7`. Its released wheel was downloaded,
SHA256 verified (`0771e915341a4cfa47deaabf816226f1d3fbdac5b35d52df7df86b90ebe4c176`)
and installed into a permanent non-editable WSL virtual environment. The
component libraries retain diagnostics **0.1.1** at their exact compatible pin;
0.1.2 corrects service installation and recovery without changing logging APIs.
The core release head passed all seven CI jobs, covering Python 3.11/3.13 on
Linux, Windows and macOS plus installed-wheel checks. The final local core suite
passed 102 tests with five POSIX skips on Windows, and 107 tests on WSL.

Actual installation found a second systemd parsing difference: unlike command
arguments, `EnvironmentFile` values must not be quoted as shell arguments.
The installer now validates literal paths, escapes systemd specifiers, rejects
parser warnings, and can repair an owned previous unit in `bad-setting` state.
It validates in an isolated sibling staging directory so a broken existing unit
does not contaminate validation of its replacement. Tests cover both real parser
defects and preservation of unrelated units and private state.

The released systemd user worker watches three explicit diagnostic roots:
ordinary Windows user state, the desktop client's distinct Windows user state,
and WSL user state. A fixed installation timestamp prevents accidental historical
backfill. Authentication is supplied through an owned private mode-0600 file;
credentials were not put in command arguments, repository files or issue data.
The service was observed active with a current heartbeat and completed cycles.
After deliberately killing its main process, systemd restarted it with a new
PID and `NRestarts=1`; its issue and model queues retained one publication attempt
each, without duplicate submissions.

One new synthetic operation exercised the supervised worker, with no manual
publication call. The failure event at 14:17:44 UTC produced
[acceptance issue #175](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues/175)
at approximately 14:18:09 UTC and a
[Grok diagnosis](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues/175#issuecomment-5653833364)
at approximately 14:19:52 UTC. This measures one polling/network/model example,
not a delivery SLA. An unknown private field and a fake password sentinel were
absent from the public evidence. The test issue was labelled in its title and
closed after inspection; the reporting worker remains enabled for new failures.

The diagnosis incorrectly located unattributed parent time after a child phase.
A [human validation correction](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues/175#issuecomment-5653846489)
records that phase subtraction alone cannot locate the remaining time or the
failure. This is direct evidence that model diagnoses need review, even when
the logging and publishing path works correctly. The bot has no tools enabled
and cannot execute its proposed checks. It uses a dedicated local Grok Build
profile and the configured existing GitHub identity, not a provisioned cloud Bot
or newly created bot account.

The knowledge scan tests initially emitted ten synthetic failures into two
default log roots. Their exact event IDs, timestamps, exit-code sequence and
test windows were matched to the queued incident before quarantine. That one
incident remains explicitly blocked with zero publication attempts; its original
logs and attribution evidence were retained. The test suite now isolates parent
and child log roots, treats expected scan findings as normal results and marks
explicit parser failures as caller errors. General business exit codes remain
unknown failures. A healthy current worker cycle does not hide that visible
historical blocked entry.

An additional 300-sample warm core measurement included one operation, six phases
and six DEBUG events per sample. Windows INFO median/p95 were 1.0698/1.4761 ms;
DEBUG was 1.18205/1.537 ms; CRITICAL filtering of normal events still cost
0.67525/0.7999 ms. WSL INFO median/p95 were 0.989796/1.302315 ms. These are local
recording costs and do not include GitHub or Grok work. The separately measured
cold CLI import cost above remains a limitation rather than being hidden by warm
measurements.

The published fleet-monitor **0.1.3** wheel was independently downloaded and
verified against SHA256
`bb4d7681ef8abf5eb4e5eeff64260cae04680c11d245546856f9155423cd57a7`.
A clean environment contained only top 0.1.3 and its pinned diagnostics 0.1.1;
the installed index and its referenced JavaScript/CSS assets were present.
Console help, offline bundle generation and dependency consistency checks
passed. This establishes the released artifact, without claiming that an
existing fleet service or every preserved task environment was restarted.
