# Diagnostics, automatic issues and Grok diagnosis

Status: implemented; dated release and deployment evidence is recorded in
[diagnostics-validation-2026-09-13.md](diagnostics-validation-2026-09-13.md).

VAWS tools record their own operation and phase outcomes. A developer should be
able to locate a slow or failed operation from its returned diagnostic reference,
without repeating the task, inventing identifiers or collecting a report by hand.
The shared `vaws-diagnostics` package owns the format, logging, redaction and
publication queue; the component that performs an operation owns its meaning and
authoritative state.

## Components and coverage

| Owner | Boundaries and phases |
| --- | --- |
| workspace | Native attachment, CLI and business helper dispatch, MCP provider calls, bootstrap, dependency preparation, source copy, Git operations, validation, hooks and monitor lifecycle |
| remote-dev | Every public tool, connection/worker bootstrap, RPC transmission and response, jobs, file transfer, shell launch and process completion |
| coordinator | Every public tool, lock wait, preparation, resource selection, build and reuse decisions, submission, asynchronous stage transitions, observation, evidence and release |
| knowledge | Every public tool, maintenance workers, feed and index failures, subprocess launch and completion, optional/degraded results |
| top | HTTP/CLI boundaries, collection queue and host probes, persistence and retention, scheduler liveness and health |
| diagnostics | Bundle projection, outbox capacity and retries, issue reconciliation and Grok diagnosis |

Instrumentation belongs at common dispatch boundaries and at expensive internal
phases. New public tools inherit boundary instrumentation; tests enumerate the
tool catalog to detect uncovered additions. Logging does not run knowledge
queries, install packages on remote hosts or add task initialization gates.

## Record and timing contract

Use named Python loggers and JSONL files, following the
[Python logging design](https://docs.python.org/3/howto/logging.html). Event fields
follow the distinctions in the
[OpenTelemetry logs data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/):
UTC event time, severity, component, operation, trace and span association, event
name and structured attributes. Importing the package does not configure the root
logger. MCP stdout remains protocol-only.

| Level | Meaning |
| --- | --- |
| DEBUG | Bounded decision detail, cache checks, polling and transport diagnostics |
| INFO | Operation and phase start/end, selected reuse and normal completion |
| WARNING | Retry, fallback or degraded capability with its reason |
| ERROR | Failed operation or background step |
| CRITICAL | The component can no longer serve its required function |

An operation identifier and monotonic start are created at entry. Context travels
through internal thread/RPC metadata, never through mandatory user parameters.
Context identifies diagnostics, not a task or permission to join another task.
Each process records its own clock domain; durations never subtract timestamps
from different hosts. Parallel phase durations are displayed alongside their
parent elapsed time, not summed into a fictitious total. Caller wait, submitted
workload lifetime, business readiness and resource release are separate spans.

The original exception and category remain available locally. Public records
include only selected error classification, error type and code locations, with
submission certainty and retry safety when the transport knows them. Unknown
remains unknown. A wait timeout or cancellation does not prove a remote workload
stopped, and uncertain submissions are never automatically replayed.

## Storage and fault containment

Each process writes a separate rotated file. A shared multi-process
`RotatingFileHandler` is deliberately avoided, as described by the
[Python logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html).
Records, files, retention and export windows have explicit byte/count bounds.
File handlers are idempotent; logging failures use a bounded stderr fallback and
an observable failure flag. They cannot mask the original error or prevent
backend startup or resource cleanup. A failure of an authoritative state store
is still a control failure; this rule only applies to diagnostic copies.

Early bootstrap retains a stdlib fallback before dependencies are installed.
Remote helpers remain self-contained. Diagnostic output uses the existing
transport; it never causes a new remote installation or health-check round trip.

## Publication and bot boundary

Automatic contribution requires the workspace's explicit community choice. See
[community collaboration](community-collaboration.md) for the public policy and
first-use choices. Private events bind a workspace and its current consent
revision; this binding is omitted from public evidence. The reporter rechecks
the live policy before network actions. Missing, disabled, invalid or revoked
consent cannot upload; enabling later does not authorize earlier events.

The independent reporter reads bounded structured events, selects failed
operations and creates a durable local outbox entry. The operation never waits
for GitHub or a model. Outbox records carry a stable failure fingerprint, bounded
occurrence counts, retry state and immutable sanitized evidence. They are not a
second execution ledger. Repeated failures aggregate; unrelated failures are not
hidden behind one global issue.

Automatic export uses an allowlisted event schema, excludes arbitrary commands,
environment values, prompts, raw stdout, credentials, local paths and unbounded
state dumps, then applies the shared redactor and a final leak scan. A sanitizer
failure blocks publication while keeping the local incident visible. Public
bundles identify omitted data so absence is not mistaken for proof. Developers
can inspect a local bundle before manual submission as well.

Issues go to the configured VAWS repository with the sanitized JSON evidence
embedded in a bounded collapsible section and a content hash. GitHub REST has no
general exactly-once issue creation guarantee. Before posting, the reporter
looks for its stable marker. A timeout after POST is recorded as uncertain and
reconciled before another POST. Backoff, rate limits, queue bounds and worker
leases prevent a failure storm from becoming an issue storm.

Grok receives only the sanitized immutable issue evidence. The bot has no tool
execution authority derived from issue text. Its response separates observations,
hypotheses, missing evidence and proposed checks. Posting a diagnosis does not
merge code, close an issue, restart a service or change task state. Bot output is
bounded and scanned again before publishing. The model adapter, queue and GitHub
transport are separately replaceable and testable.

## Acceptance

Failure injection covers malformed/oversized events, disk and permissions
failures, concurrent writers and rotation, backend EOF, early bootstrap without
dependencies, RPC timeout before/after submission, cancellation, background
worker failure, scheduler persistence/prune failure, outbox overflow, concurrent
workers, GitHub rate limiting, accepted POST with lost response, duplicate
incidents, sanitizer failure and hostile issue content. A synthetic public issue
and bot reply validate the actual deployed path; mocked transport tests do not
prove deployment. Benchmarks report disabled, INFO and DEBUG recording overhead
separately from worker/network time.

## Developer operation

The default level is `INFO`; set `VAWS_LOG_LEVEL=DEBUG` before starting the
affected process to retain decision details. `WARN` is accepted as an alias for
`WARNING`. `VAWS_DIAGNOSTICS_ROOT` overrides the default user directory:
`%LOCALAPPDATA%/vaws/diagnostics` on Windows and
`${XDG_STATE_HOME:-~/.local/state}/vaws/diagnostics` on POSIX. The actual process
environment matters: a packaged desktop client and an ordinary shell can have
different `LOCALAPPDATA` roots.

Use the selected interpreter and the absolute workspace script path to inspect
existing evidence. These commands perform no managed preparation:

```text
python /path/to/W/.agents/scripts/vaws_diagnose.py bundle --root /path/to/logs --operation-id OPERATION_ID --output support.json
python /path/to/W/.agents/scripts/vaws_diagnose.py status --state /path/to/reporter-state
```

Each process segment rotates at 1 MiB with three backups; an individual record
is limited to 16 KiB. A support bundle defaults to 1 MiB and 1,000 events.
Worker retention targets seven days, 128 MiB and 512 files, preserving recently
written and unread segments. A full intake queue reports backpressure while
already queued issues and diagnoses continue draining. The queue permits 1,000
unpublished incidents and separately bounds published history to 1,000 entries;
published history and occurrence IDs expire after at most 30 days. Reporting and
model requests each have an independent maximum of ten submissions per hour.

## Install the independent worker

Install the released diagnostics worker in a permanent, non-editable Python
virtual environment. Library consumers may retain their exact compatible pin;
upgrading this worker does not rewrite task environments. This unreleased system
does not migrate old worker databases or retain old-process compatibility: stop
the old component and install the new version with fresh worker state. Enable the worker once
for the installation using the desired GitHub identity and explicit log roots:

The owner supervises a user service on Linux (systemd), Windows (Task Scheduler)
and macOS (launchd). `service status` and `remove` operate on the owned
installation. Token authentication may be stored with `--save-token` in the
owner's protected credential file; tokens never go in the service command.
Normal onboarding installs only the local reporter. A maintainer may install a
separate `--central-bot` service with Grok and an independent state directory,
without `--root`. It diagnoses validated, already-public automatic VAWS issues;
it cannot ingest or upload local logs. Revocation prevents new contributions,
and does not retract a public issue or remove it from central maintenance.

```sh
/path/to/venv/bin/vaws-diagnostics grok-profile --home /path/to/grok-bot-home
GROK_HOME=/path/to/grok-bot-home grok login
/path/to/venv/bin/vaws-diagnostics service install \
  --root /path/to/logs --state /path/to/reporter-state \
  --repository vllm-ascend-workspace/vllm-ascend-workspace \
  --grok /path/to/grok --grok-home /path/to/grok-bot-home \
  --grok-work /path/to/empty-bot-work
/path/to/venv/bin/vaws-diagnostics service status
```

Repeat `--root` for separate known log directories. The Linux/WSL installer
creates an owned systemd user service with restart-on-failure, a private umask
and isolated Python imports. It validates the staged unit with the actual
systemd parser when available and refuses unrelated units and drop-ins. A
separately supplied owned, regular mode-0600 `--environment-file` can provide
service authentication; its contents are never embedded in the unit or logs.
Reinstallation preserves the initial observation timestamp, credentials and
queues. `service remove` stops the owned service and preserves diagnostic data.

The service manager must be running. Linux user lingering and a Windows login
task starting the WSL user service are deployment choices; the built-in
installer does not claim native Windows/macOS service support. Those platforms
can schedule `worker --once` with their service manager. See the
[released package guide](https://github.com/vllm-ascend-workspace/vaws-diagnostics/blob/main/README.md)
for the worker CLI and authentication options.

The local `status` command exposes publication state and errors, a heartbeat
(stale after 60 seconds), the current stage and progress stalls. GitHub/model
failure does not block the original tool. A healthy process does not imply all
historical incidents were published: inspect blocked and uncertain queue entries
as well. An uncertain POST is reconciled without blindly replaying it.

This deployment uses a local Grok Build worker with a dedicated tool-disabled
profile. It does not create a Grok cloud Bot or a separate GitHub account;
comments use the configured GitHub identity. Model suggestions remain untrusted
hypotheses requiring evidence, and cannot change services, close issues or merge
code. The actual issue, comment and restart checks are recorded in the dated
validation report.
