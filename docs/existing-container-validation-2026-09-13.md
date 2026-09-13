# Existing-container and lightweight-session validation

Status: dated validation evidence (2026-09-13); final installed four-machine acceptance passed

The implemented path lets an Agent use an existing container's code and startup
script through remote-dev, with optional knowledge tools and no managed-session
setup step. The completed installed checks below establish container I/O,
script/environment preservation, usable knowledge and lightweight native review.
Final four-machine execution used the exact locked remote-dev revision below.
The [design](existing-container-design.md) and
[independent Kimi review](existing-container-review-2026-09-13.md) record the
intended contract and its approval separately.

## Revisions and evidence boundary

| Component | Final selected version | Final selected commit |
|---|---|---|
| remote-dev | 0.8.0 | `6996e5756d8e81a7842173f34837d649be77b10c` |
| vaws-coordinator | 0.4.1.dev2 | `0d14525b9711f5a38e2036c87e9221982add7a7a` |
| vaws-knowledge | 0.5.1 | `dac5572b7887e4435fab35fb1a72a38c23d55b33` |

An immutable Windows CPython 3.13.12 environment was successfully prepared from
the final workspace lock. Its receipt key begins `ae5c963342bd`; package-only
preparation skipped knowledge maintenance. Final execution and aggregate checks
then passed using that installed environment.

The implementation was fast-forwarded into the current checkout, which then
selected this environment. Explicit client setup updated the installed clients.
Reading the actual Codex/Kimi provider commands and resolving all three Cursor
stable-provider entries confirmed that all nine select this saved environment.
This prepares new connections; it does not hot-update existing MCP processes or
replace unrelated running coordinator services. An older knowledge provider's
successful owner reuse does not give that process the new lazy-activation code.

This round did not grant or re-certify native UI hook trust or default Worktree
selection. The installed Kimi 0.42.0 client still lacks the native SessionSetup
extension. Provider configuration and direct container tools work independently
of that missing new-worktree preparation capability. Setup reports these
boundaries explicitly; writing configuration does not establish native trust.

Earlier live functional, knowledge and performance probes loaded built wheels
from an independent environment's `site-packages`, without source injection.
The remote-dev performance samples precede the final shell-quoting adjustment.
They describe that 0.8.0 candidate's existing read/RPC path; they must not be
attributed to a complete performance rerun at final commit `6996e575`.
Private records retain exact loaded module paths and relevant hashes.

The four real machines are identified only as A–D. Their addresses, container
names/IDs, authentication data and actual user paths are omitted. Raw evidence
remains under the untracked local directory
`.vaws-local/existing-container-20260913`; filenames below are evidence labels,
not published download links.

## Existing-container functional acceptance

The first installed-candidate round passed on A, B and D. Machine C encountered
an SSH handshake/startup timeout explicitly reporting that the request had not
been sent. A subsequent independent call passed the same acceptance case on C.
This was a new call after a known pre-submission failure, not automatic replay
of an operation with an unknown outcome. Both outcomes remain in the evidence.

The final installed round passed all four machines in one run. It additionally
compared container ID, image, configured user, start time, restart count and
configuration hash before and after. Installed Python/JSON file hashes were
retained; the package code-set hash was
`140f2ec6ec198762973df0fbb6b43d61e75398026d94d222437e73421c307e44`.
All four completed final cases established:

- An existing repository file could be read by container name, with the result
  returning its fixed full Docker ID.
- A custom script retained its arguments, working directory, Python interpreter,
  sourced environment, shell function and non-exported variable behavior. Output
  matched direct execution in the same container. A separate case preserved a
  nonzero exit and stderr.
- Read, edit, patch, list, glob and grep operated on owned test files.
  Binary push/pull preserved the payload exactly.
- Owned interactive jobs supported stdin, tail/status and stop, and became quiet
  before their marked test directories were removed.
- Original repository revisions, dirty-state fingerprints, package inventory,
  environment and original script/code contents were preserved. Only isolated,
  owned acceptance fixtures and normal remote-dev job state were written.
- Container identity, configuration and lifecycle were unchanged; every owned
  job was quiet and each marked acceptance fixture was removed.

The first round used root-configured containers. Local WSL protocol tests also
checked uid 1000 without a Docker user override. That is useful non-root command
evidence, not a separate real-container non-root acceptance claim. Existing jobs
still need an endpoint `root` writable by the configured container user for
scratch/log files; an existing writable code directory can be selected. Read-only
file tools do not require job scratch. Missing Python, Bash, Docker access or
write permission is reported; the tools do not repair or recreate the container.

Evidence labels: `four-host-live.txt`, `four-host-155-retest.txt`, and the two
completed first-round `live-*` summaries; final evidence is `four-host-final.txt`
and `live-20260913-023608-6abf0759/summary.json` with per-machine results.
Five final warm reads per machine had medians A 347.98, B 348.00, C 352.53 and
D 344.01 ms. This final functional run is separate from the paired comparison below.

## Four-machine read performance

Both routes used the same installed `remote.read` API, the same existing
`vllm_ascend/__init__.py` file, offset 1, limit 200, content verification and a
private local read ledger. Direct container SSH was compared with host SSH plus
the fixed full Docker ID. Mount namespace, hostname, resolved file path,
SHA256 and file metadata agreed between the routes. All four containers used
host networking and all four direct SSH endpoints were reachable.

Each route had one cold call after closing only the benchmark's own preflight
connections, followed by five alternating warm pairs per machine. Machines ran
sequentially; the first route alternated by machine and pair. Local interpreter
startup/import and preflight are excluded from these call timings.

| Machine | Direct cold, ms | Full-ID cold, ms | Direct warm median, ms (range) | Full-ID warm median, ms (range) |
|---|---:|---:|---:|---:|
| A | 3947.63 | 5129.97 | 341.96 (332.15–342.20) | 353.99 (349.75–362.03) |
| B | 4177.87 | 4241.04 | 336.23 (331.75–345.82) | 352.18 (347.93–913.96) |
| C | 4532.76 | 4115.98 | 614.06 (333.93–621.88) | 346.26 (341.97–371.99) |
| D | 3951.90 | 4094.30 | 335.97 (333.82–338.09) | 353.95 (349.97–355.94) |

On A, B and D, fixed-ID warm medians were 12–18 ms higher. B retained one
913.96 ms fixed-ID sample; C's last three direct samples rose to 614–622 ms.
No sample was discarded. C's result does not establish that Docker itself
improves performance. These small samples are not an SLA, an isolated estimate
of Docker overhead or proof of universal zero latency cost.

Client-side phase instrumentation distinguished connection acquisition/process
construction, waiting for SSH/remote RPC readiness, send-to-reply time and local
API/ledger work. Cold readiness was approximately 3.60–4.75 seconds. Send-to-reply
includes transport, remote Python subprocess startup, read/hash and serialization;
it is not a measurement of disk I/O alone. The private records retain each phase
and every sample.

One separate name/fixed-ID pair per machine kept name resolution out of the
primary comparison. Each name call performed exactly one inspect. Its host-only
lookup connection was cold: readiness took 3.61–4.62 seconds and inspect
send-to-reply took 358.99–409.31 ms, followed by the already-warm container read.
The fixed-ID comparison took 345.89–354.09 ms with no inspect. The cold lookup
total must not be presented as warm inspect latency.

All 48 primary reads and eight separate name/ID reads succeeded with matching
file hashes. Every fixed-ID primary call had **zero inspect RPCs**; all 40 warm
primary calls had **zero new connections**. File hash/stat and container
identity, running/start/restart state and network configuration were unchanged
before and after. This probe performed no remote fixture edits, network changes,
package setup, managed operation or NPU execution.

Evidence labels: `four_host_read_performance.py` and the completed
`read-performance-20260913-023246-f10c05b6` metadata, results, per-machine records
and report. An earlier retained preflight incorrectly assumed published Docker
ports; it stopped after read-only inspect and contains no performance samples.
The completed probe verified the actual mount namespace instead.

## Knowledge availability and unused-provider cost

The Windows baseline reproduced a blocked daemon launch when a child inherited
stdin while the parent was reading its MCP pipe. Three isolated pairs remained
blocked after approximately 0.81 seconds with inherited stdin; their children
finished after the fixture pipe was closed. With `stdin=DEVNULL`, children
finished in 55.73–59.05 ms while the parent was still reading. Fixture processes
exited cleanly. This supports the child-stdin repair; it does not substitute for
real service readiness.

The installed 0.5.1 wheel was then exercised against the real knowledge owner.
The recovery used its maintenance API and waited for the existing instance lock.
It did not bypass the lock, stop unrelated MCP clients or modify their immutable
environments. The owner moved from unavailable to live embedding/OpenViking
services, local indexing became ready and shared synchronization was unchanged.
A real stdio query returned eight hits with `unavailable=false` and
`degraded=false`; explaining a returned reference found its 1,538-character
Markdown body. Project/candidate Markdown and service configuration remained
unchanged. An already-connected older provider also successfully reused the
restored owner for query/explain. Retrieved knowledge remains optional reference,
not verified evidence about a current model run.

Three fresh installed-wheel MCP processes received only initialize,
notifications, tools/list, ping and EOF. Instrumented fail-on-use boundaries
recorded **zero maintenance workers, backend initialization, child processes,
network calls, worker threads, reconciliation and shared synchronization** in
each process. First-response times were 919.80, 812.41 and 793.93 ms; complete
process lifetimes were 972.26, 860.28 and 841.09 ms. These include local Python
startup/import and demonstrate absence of unused backend work, not zero provider
startup time.

Package tests additionally cover invalid requests, successful capture and query
activation, explain/summary non-activation, durable maintenance deadlines,
expired verification and explicit repair. The 3,600-second verification interval
applies while maintenance is active and the backend is available; unused or
stopped providers resume maintenance on actual use or explicit preparation.

Evidence labels: `knowledge-stdin-baseline`, `knowledge-real-restoration`,
`knowledge-unused-real-mcp.json`, `knowledge_acceptance.py` and
`knowledge_unused_mcp.py`.

## Native PR-review cost

An installed-package harness read a real temporary Git diff and source file and
identified a changed boundary condition while unused remote, knowledge and
coordinator-service imports were forbidden. It required no managed setup or
personal identity. The observed Agent workflow call counts for session, run,
execution, finish and knowledge were all zero; no unused capability state
directories were created.

The necessary native attachment remained intact. The package's in-process
SessionStart handler took 140.48 ms. Five repeated prompt handlers had a 2.91 ms
median and emitted zero additional context bytes. Five separate invocations of
the candidate Python adapter returned silent success with a 116.64 ms median,
including Python process startup. The harness launched the candidate interpreter
directly; that timing excludes the generated PowerShell wrapper and native-client
event dispatch.

The current installed Codex global hook had a legacy VAWS-only PreToolUse group
without a matcher. Explicit setup added the task-tool matcher while preserving
every command object and every other group. The actual resulting matcher
excluded eight ordinary/remote/knowledge names and included 15 task-tool names
across unqualified and MCP-qualified forms. Ordinary tools therefore do not
dispatch this group under the configured matching contract.

Three forced calls to the actual configured PowerShell command also tested the
fallback if a client still dispatches an ordinary tool. They returned silent
success in 530.09, 238.12 and 241.40 ms, including the wrapper and Python startup.
A loaded fail-on-use probe recorded zero VAWS/remote/knowledge runtime imports
and zero subsequent child processes, including Git or hook forwarding. These
forced-dispatch timings are separate from the direct-Python samples above and
do not describe normal filtered tool calls.

This is an actual local package/hook and Git/file harness, not a new end-to-end
native client UI certification. It supports no additional Agent workflow steps,
remote dependency or knowledge gate for ordinary review. It does not imply zero
hook cost or change the separate native new-worktree preparation contract.

Evidence labels: `lightweight_acceptance.py`, `lightweight-review-result.json`,
`current_entry_acceptance.py`, `current-entry-acceptance.json` and
`current-client-setup.json`.

## Local checks and final acceptance

| Scope | Completed evidence |
|---|---|
| remote-dev native Windows full suite | 439 passed, 97 skipped, 152 subtests passed |
| remote-dev Linux/WSL full suite | 522 passed, 2 skipped, 189 subtests passed |
| remote-dev follow-up container tests | 74 passed, including the explicit uid-1000 assertion |
| Knowledge full suite | 339 passed, 4 skipped, 6 subtests passed |
| Coordinator final native Windows full suite | 652 passed, 29 skipped, 52 subtests passed |
| Coordinator WSL affected checks | 101 passed |
| Workspace final affected checks | 137 passed, 58 subtests passed |
| Explicit legacy global-matcher repair checks | 33 passed |
| Final installed four-machine acceptance | 4 passed, all preservation and owned-cleanup checks passed |

The initial coordinator Windows full-suite attempt recorded 652 passed,
28 skipped and 52 subtests passed, with one POSIX Bash fixture failure caused by
a Windows-path/shell mismatch. The corresponding WSL affected set passed. The
initial Windows run is retained as a failure, not counted as a clean full pass.
The same failure was reproduced on the unchanged baseline; that POSIX-only
fixture now explicitly skips Windows and passes on WSL. The subsequent complete
Windows run passed with 29 explicit platform skips as listed above.

Raw JUnit/log evidence includes `remote-dev-windows.xml`, `remote-dev-posix.xml`,
`container-posix.xml`, `knowledge-full-tests.xml`, `coordinator-tests.txt`,
`coordinator-posix-tests.xml`, `coordinator-final-tests.xml` and
`workspace-final-tests.xml` and `global-matcher-repair-tests.xml`, with their
complete logs. The remote-dev owner's validation record documents its follow-up
container/endpoint checks, distinct
from the earlier full-suite runs. A dependency doctor also confirmed the final
installed package selection.

The completed work validates CPU tools, transport, script semantics and reuse of
an existing environment. It does **not** establish NPU model accuracy, serving
throughput, resource admission or an absence of hardware-specific regressions.

## Mainline integration follow-up

The follow-up integrates current canonical main, including cross-root remote RPC
reuse, native kernel preparation, official-client startup and the task-selected
MCP gateway. Explicit setup replaces generated Codex routing with the current
matcher; it does not classify old matcher versions. Missing selected-workspace
hooks now report an error instead of executing an entry from another checkout.
Existing task ownership and user-authored hook siblings remain intact.

Ordinary review and direct endpoints bypass workspace preparation in both the
generated project guidance and real native startup hints. Remote-dev and
knowledge accept calls without task context, using the configured workspace's
saved environment without registry or Git discovery. Explicit/native context
retains task-specific selection, while managed task calls still require it.
Current clients' native context channels remain supported. This supersedes the
earlier task-only matcher and mandatory Kimi-extension boundaries above; the
earlier measurements remain evidence of their stated revisions.

All component PR checks passed before merge:
[remote-dev #14](https://github.com/vllm-ascend-workspace/remote-dev/pull/14),
[coordinator #30](https://github.com/vllm-ascend-workspace/vaws-coordinator/pull/30)
and [knowledge #28](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/28).
The workspace lock now selects canonical repositories at remote-dev `a6536288`,
coordinator `921ce2af` and knowledge `3a65926d`. The coordinator selection is an
ancestor of its mainline merge `66dde4b6`. Installed preparation produced receipt
`561d729f659f`; no source injection was used in the final four-machine run.

That final run passed all eight checks on each of A–D: **32/32**. All twelve
owned jobs were quiet, all four marked fixtures were absent, and cleanup reported
no errors. Original code, packages, environment, container configuration and
lifecycle were preserved. Loaded remote-dev was 0.8.0 at `a6536288`; its installed
code-set SHA256 was
`04f3ef6d0a21350d86bcd1e17409c87311330d6e1575b0c9ee1ba16f295278ef`.
The five warm-read medians were A 337.573, B 335.831, C 333.718 and D 339.613 ms.
These are functional-run timings, not a new paired comparison or an NPU result.

Private follow-up evidence is under `.vaws-local/existing-container-merge-20260913`,
including `installed-sync.json`, `four-host-final-summary.json` and
`four-host-final.txt`. Full raw operation results remain in
`live-20260913-083159-a5587722/summary.json` under the original evidence directory.

The actual installed stdio gateway was also exercised without request metadata,
task context or inherited GitHub identity. Its catalog exposed 18 remote tools,
including the container coordinate and optional context. A real container source
read succeeded, returned the full container ID and selected receipt `561d729f659f`;
the dedicated task-registry path remained absent. This read-only entry acceptance
is recorded in follow-up directory `gateway-20260913-083908-2f684950`.
