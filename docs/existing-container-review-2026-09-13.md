# Existing-container and lightweight-session design review

Status: dated design review evidence (2026-09-13)

This is a redacted summary of the independent review of
[the existing-container design](existing-container-design.md), checked against
the [nine design principles](design-principles.md) and the actual remote-dev,
coordinator, knowledge and workspace sources. It records design approval, not
implementation correctness, installed-package readiness or four-host acceptance.

## Reviewer and evidence boundary

The installed Kimi Code 0.42.0 ran model alias `kimi-code/k3`, actual model `k3`,
with max thinking and Never Ask behavior. Native request records verified the
effective model and thinking level. Headless prompt mode sets permission to
`auto`, which that client labels Never Ask; it rejects combining `--prompt`
with the separate interactive `--auto` flag.

The review used an isolated configuration and only local source-reading tools.
A long initial reading turn was interrupted, then the same native session was
resumed with its actual persisted history for a focused conclusion. This did not
replace source evidence with a summary or substitute another reviewer. Global
client configuration remained unchanged. The review itself performed no product
edits, remote execution or service lifecycle operations. Private transcripts,
machine coordinates, local paths and authentication material are not published.

## Findings and approval

The reviewer approved knowledge lazy maintenance, the Windows daemon stdin fix,
lightweight hook routing and the narrower first-use initialization policy. Those
independent blocks were allowed to proceed without waiting for a container-only
wording correction.

The sole required correction, M1, was to broaden the container boundary:
**every public entry accepting an Endpoint must implement container semantics or
explicitly reject it before acting.** The previous forwarding-only wording missed
interactive SSH bootstrap helpers that construct their own host command.

The accepted design now includes that invariant and explicitly covers local
forwarding, `interactive_ssh_command` and `run_interactive`. Its acceptance scope
also checks endpoint cloning, resolver overrides, CLI and MCP/JSON schemas,
result targets and persisted endpoint records. The review explicitly allowed
the container block to proceed after that design correction; no other required
correction was raised.

## Design choices retained

- Existing containers and custom scripts use remote-dev endpoint I/O directly.
  No new managed-runtime mode, binding procedure, source synchronization or
  identity/setup prerequisite is added to an explicit endpoint task.
- Names and short IDs resolve to a full Docker ID before worker, ledger and job
  access. Retained jobs cannot follow a replacement container with the same name.
  Unknown submission outcomes retain the existing no-replay behavior.
- Knowledge maintenance starts on actual use and respects persisted deadlines.
  The 3,600-second verification interval applies to active maintenance, not a
  promise of background repair while the provider is unused or unavailable.
- Windows daemon launch detaches stdin with `DEVNULL` and combines
  `CREATE_NO_WINDOW` with the existing process flags. The controlled baseline
  supports that repair; actual query/explain recovery still needs runtime evidence.
- Task-only hook routing and early exits remove work from ordinary native and
  remote-dev tools while preserving lifecycle identity, cwd refresh and legacy
  context fallback. Missing personal identity does not trigger setup for review
  or an explicit endpoint; managed ownership requirements remain.

Optional recommendations concerned explicit container-only inspect, separate
connection/inspect/dispatch timings, accurate diagnostic target information and
documenting use-driven shared synchronization. They add no Agent workflow steps.

Implementation tests and remote acceptance must establish their own results.
This design review does not claim model accuracy, NPU serving performance or
zero hook/SSH latency.
