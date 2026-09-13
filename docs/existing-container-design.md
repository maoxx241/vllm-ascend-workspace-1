# Existing-container work and lightweight sessions

Status: dated design, approved for implementation after Kimi K3 max review on 2026-09-13

## Goal and current evidence

A user may start a task with an existing container, a code directory in that
container, and a custom startup script. The task is to reproduce or investigate
that exact environment. The Agent should read, edit, run, observe and retrieve
artifacts there with ordinary remote-dev tools. Knowledge remains optional
reference. A simple PR review must remain ordinary local Git and file work.

This design follows the [nine principles](design-principles.md). It changes the
execution owner only when the requested operation changes; it adds no session
mode, resource checklist, per-task identity fields or required knowledge calls.

The inspected baseline is workspace `4a1f28e`, remote-dev `2de5cc32`, coordinator
`03b30474`, and knowledge `c9529383`. Current installed packages match those
component pins. Source locations and private live-test details stay in local
evidence, outside published documentation.

| Scenario | Current behavior | Gap |
|---|---|---|
| Container already exposes SSH | remote-dev accepts its SSH endpoint, cwd and shell command | Supported; make this route discoverable |
| User supplies a host and container name | Endpoint accepts host/port, not container | Tools require manual Docker wrapping and file/job workarounds |
| `vaws_run(sources={})` | Skips local Git capture content but still selects/prepares a managed runtime and command environment | Does not preserve the specified container, directory or interpreter |
| Local PR review | Native Git/files require no run, device reservation or knowledge query | Prompt hooks repeat context; knowledge MCP connection starts maintenance even when unused |
| First use without GitHub identity | AGENTS asks for an identity and all-client/fork setup even for otherwise independent work | Scope setup to an explicit initialization request or managed work that actually needs personal-container identity |
| Knowledge without a ready backend | Query can report pending without blocking native tools | Provider startup still forces verification and shared checks |

Evidence: remote-dev `core/endpoint.py`, `core/rpc_transport.py`,
`core/artifact_transport.py`, `core/ssh_transport.py`; coordinator
`task_client.py`, `placement.py`, `service.py`, `provision/task_environment.py`,
`backend.py`, `hooks/vaws_session.py`; knowledge `server/mcp_server.py`,
`maintenance.py`. `sources={}` still creates an execution root and selects an
interpreter, so documentation alone cannot call it an in-place reproduction mode.

## User and Agent interaction

The user can say: use container `repro-case` on the specified host, code in
`/work/vllm`, and run `/work/start-case.sh`. The Agent directly uses:

```json
{"host":"lab-host","port":22,"container":"repro-case","cwd":"/work/vllm","command":"bash /work/start-case.sh"}
```

The same endpoint arguments work on remote_read, remote_edit, remote_grep,
remote_apply_patch, artifact operations and process tools. Existing SSH access
to the container remains an ordinary host/port endpoint. Existing endpoint
aliases may retain these values if useful, but creating an alias is not required.
No preliminary session call, attach command, source synchronization, package
installation, service recipe, setup rerun or manual execution record is needed.
Missing personal-fork initialization is not a prerequisite for native review or
explicit endpoint/container work. The current broad first-use documentation is
narrowed accordingly: ask once and initialize when that setup is requested or a
managed operation actually needs the personal-container identity. Reuse an
already confirmed answer. Do not ask for GitHub identity merely because a local
session opened a workspace or a user supplied a remote container.

The command is the user's command. A startup script is not automatically sourced
as a profile, parsed, rewritten or registered. When an environment file must be
sourced, the Agent can use existing `runtime_env_file` or the explicit shell
command. Existing shell semantics, functions, non-exported variables, cwd and
argument handling must remain intact. `user` is the SSH user; Docker's existing
container user is retained. The API will not introduce a second user override in
this change.

Knowledge query/explain/capture work with the same local provider as other tasks;
remote code does not need to become a local checkout or knowledge source mount.
A missing or pending index remains unknown and does not prevent remote work.

## Ownership and scope

remote-dev owns explicit endpoint I/O, including execution within an existing
Docker container reached through SSH to its host. The container is an endpoint
coordinate, not a managed resource or source identity. It must already be running
and have the prerequisites needed by the requested operation (the existing
workers need Python 3 and shell operations need Bash). Missing requirements
produce an actionable error; tools do not install, restart or repair that user
environment. Docker access is the SSH account's existing access.

Coordinator remains the owner of explicitly requested managed environment
preparation, source publication, device/port allocation and managed execution.
There is no coordinator existing-runtime mode in this change. Direct execution
does not acquire or claim a managed lease. A specified container does not grant
control over another task's executions. For an original script using NPUs, the
Agent follows the user's explicit device/environment requirements and current
occupancy evidence; requests for allocation or managed topology use coordinator.
Ordinary file inspection does not trigger device observation or allocation.

remote-dev stops only jobs it created and can identify. It never stops/removes
the container, adopts all processes inside it, or cleans unrelated files or
worktrees. A user script's arbitrary side effects remain the script's behavior.

## Container transport

1. Extend the immutable Endpoint and the common MCP/CLI endpoint schema with
   optional `container`, accepting a Docker name or ID. Validate nonempty names,
   option-like values and control characters before invoking the host shell;
   serialize command arguments with shell quoting, never string interpolation.
2. Resolve the selected container to its full Docker ID and confirm it is running
   before any operation that can act on it. All retained job references and
   mutation ledgers must identify that exact container generation. A new explicit
   name-based operation may resolve a replacement container; an old job reference
   must never do so. Failure to resolve the old ID is an error, not host fallback.
   Name/short-ID resolution uses one read-only inspect through the existing host
   RPC before ledger/job/pool access. Full 64-hex IDs need no repeat inspect.
   Results return the full ID for ordinary endpoint reuse. Native Python entry
   points use the same idempotent resolver as MCP. There is no name cache, TTL
   or event watcher: renaming a live old container must not make a fresh name
   call target that old container. Measure name resolution separately.
3. A shared transport helper wraps the existing remote command with
   `docker exec -i <full-id> ...`. RPC workers and binary artifact workers run
   inside the container. Script, byte streaming and attached execution use the
   same boundary. RPC PTYs remain created inside the container by the worker.
4. Container identity participates in endpoint IDs, read ledgers, job state,
   RPC and artifact connection keys. Host SSH connection details retain their
   existing meaning. Endpoint cloning and job rehydration preserve every new
   coordinate. Two containers with the same root on one host must not share
   filesystem state, workers or concurrency checks.
5. Results show the requested selector and resolved container identity. Existing
   logs, timing fields and uncertain-submission behavior are reused. Do not retry
   a possibly submitted command, edit or stdin write after transport loss.
6. Every public entry accepting an Endpoint must implement the selected container
   semantics or explicitly reject that endpoint before executing anything. This
   includes low-level SSH argv construction, local forwarding and the interactive
   bootstrap (`interactive_ssh_command` / `run_interactive`), which currently
   build their own host commands. Helpers without container semantics reject it.
   They must not silently treat the host's localhost as the container's localhost.
   Verify preservation through `_as_long_stream`, resolver override allowlists,
   CLI `endpoint_payload`, MCP/JSON schemas, `to_result_target` and `endpoint.json`.
   Contract tests enumerate public entry points and their support/rejection.

The transport adds no daemon installation, container SSH server, new supervisor
or workspace resolver. Worker code and per-job scratch/log files are the existing
remote-dev overhead; they are not claimed to be zero filesystem writes. User
code, environment files, package installations and container configuration stay
unchanged unless the requested command explicitly changes them.

## Lightweight sessions and knowledge

Keep native task identity and cwd association local. Preserve SessionStart,
SessionEnd, subagent association and task-tool-only PreToolUse rewriting. Keep
prompt hooks where they refresh a changed native cwd. After that refresh, clients
with native context injection return an empty prompt-hook result; they do not
append the same task instructions on each turn. Legacy Kimi without native agent
metadata retains its required fallback. New sessions and explicit handoffs still
receive the context needed by their actual client.

The workspace's global Codex hook migration currently drops the local
PreToolUse matcher when creating its fixed adapter group. The installed global
hook therefore runs on ordinary tools too. Preserve the task-tool-only matcher
when generating/migrating owned entries, while retaining custom hooks and their
conditions. The fixed adapter must also return before Git scope checks or
environment forwarding for an unrelated PreToolUse event, so existing reviewed
definitions stay inexpensive even before configuration regeneration. The package
hook similarly rejects unrelated PreToolUse input before opening its registry.
Do not change native hook trust as part of this fix.

Knowledge MCP initialize, tools/list, ping, unused EOF and invalid requests must
not create a backend process, maintenance thread, model verification, index
reconciliation or shared-release network request. Activate one maintenance worker
on a valid query or successful capture when needed. Explain reads Markdown and
does not need embedding/index maintenance. Query immediately uses available data
or reports pending; background preparation must not become synchronous task work.
Capture wakes the active worker. Automatic final-response capture remains a
local non-indexing write and does not start a maintenance process.

Maintenance startup respects the shared `next_check` and `next_verify` receipt;
a new client is not itself a reason to force a full audit. Missing/expired state
can still recover on use. Explicit maintenance/prepare preserves its requested
force/verification behavior. Failures do not interrupt unrelated tools.

There is an explicit recovery tradeoff: current tests rely on each connection's
full audit to discover an index whose vectors vanished while its ledger remained.
Reusing an unexpired receipt can defer discovery to the existing verification
deadline or explicit prepare. Retain a regression for expired/explicit repair;
do not interpret an empty search as index loss. If the existing backend has a
reliable cheap generation signal, use it to invalidate readiness on replacement;
do not build a new monitoring system for this case. Report the resulting bound.

Baseline Windows diagnosis also reproduced a concrete startup fault: an embedding
child inheriting the MCP pipe can block in Python startup while the parent's
reader is active. Three controlled process pairs unblocked only after closing
the parent input; three pairs with child stdin set to DEVNULL completed while
that input stayed open. Package-owned background engines must detach stdin and
use the Windows no-window flag. This preserves the existing service owner and
fixes the observed unavailable index without creating a new lifecycle mechanism.

Ordinary Local/resume is distinct from an explicitly selected new native
worktree. Existing worktree preparation can check upstream and prepare a changed
dependency lock once before the Agent starts. This task does not claim that such
explicit creation has zero startup cost or remove its established isolation
contract. No additional procedure is introduced for either kind of PR review.

## Implementation sequence and review

The Kimi Code review used K3 with max thinking and Never Ask in one retained
native session. Its final verdict approved knowledge and lightweight hooks/policy
directly, and approved the container block after one required clarification:
every Endpoint-accepting public entry must honor the container or reject it,
including interactive bootstrap. Item 6 above incorporates that M1 finding.
Implementation may now proceed; the review does not assert completed validation.

1. Complete this design and have the installed Kimi Code K3 review it with max
   thinking and Never Ask behavior, including the actual package sources and
   nine principles. Retain the invocation settings and response as local evidence.
   Resolve actionable findings and obtain alignment before product changes.
2. Implement container transport in remote-dev, lazy maintenance in knowledge,
   and quiet repeated prompt context in coordinator. Update workspace contracts,
   examples, affected generated-client tests and dependency pins together.
3. Verify the public installed package APIs; isolate candidate environments so
   running sessions keep their fixed package versions and resources.
4. Run four-host acceptance, compare practical cost, and report actual limitations.
   Publishing or merging is distinct from local implementation/testing.

## Validation and acceptance

Local component tests cover argument validation and quoting, every transport,
ID pinning across replacement, two-container cache/ledger separation, job restore,
owned stop, binary transfer integrity, unsupported forwarding, no host fallback,
and no replay after unknown outcomes. Preserve ordinary SSH tests. Knowledge tests
count worker/backend/network operations for unused and used providers, including
reconnect, expired state, capture and shutdown. Native tests verify first context,
quiet subsequent prompts, cwd changes, subagents and task-tool input routing.

Four live configured remote machines are tested using their existing containers.
Use a unique test directory, controlled code fixture and custom startup script;
also inspect pre-existing code/import locations and environment facts without
altering them. Compare the same script through direct Docker execution and the
public remote-dev interface. Record:

- cwd, container ID/user, script/code hash, environment sentinel and Python import
  path; package/environment/container facts before and after;
- stdout, stderr and a deliberate nonzero exit; read/search/edit/patch and binary
  push/pull integrity; interactive stdin, tail and owned process stop;
- no container creation/restart, source checkout/sync, venv/pip install,
  coordinator runtime preparation, managed execution or knowledge requirement;
- original code/script/environment preservation and surviving unrelated work;
- cold connection and warm read/command timings, separate from payload time;
  direct SSH remains unchanged and container dispatch's real overhead is stated.

NPU smoke, if performed, runs only on an actually available or explicitly
authorized device, with the selected environment's existing installation. CPU
transport tests alone establish container workflow behavior, not model accuracy
or full serving performance. Device availability is reported rather than solved
by displacing another task.

For a simple local PR review, use a small Git diff and demonstrate native reads
and review with coordinator stopped/unavailable, unusable remote endpoints and
knowledge unready, without calling session/run/finish or knowledge tools. Record
provider initialization and repeated prompt output costs independently. Successful
completion means zero new required Agent workflow steps and no unused knowledge
maintenance, not a claim that native hooks or SSH have literally zero latency.

## Alignment with the nine principles

| Principle | Concrete choice |
|---|---|
| Total user-goal cost | Reuse exact container and script; remove unused maintenance and repetitive prompt context |
| Bounded tools | Container is an endpoint coordinate; transport and owned jobs remain closed operations |
| Agent understanding | Four task concepts already supplied by the user, no mode-binding or management records |
| Clear owner | remote-dev does I/O, coordinator manages requested resources, knowledge supplies reference |
| Informative skills | Small entry examples and routing guidance, no new mandatory skill sequence |
| Advisory knowledge | On-demand query/capture, plain Markdown, pending never a task verdict |
| Demand-driven participation | Native review and explicit container tasks do not require coordinator execution |
| Reuse valid work | Existing code, scripts, dependencies, container user and prepared index are reused |
| Observable tools | Actual ID, original errors, retained job evidence and measured timing/limitations |
