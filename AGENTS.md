# VAWS workspace

This repository contains project materials, client wiring and business skills.
Optimize the total cost of completing the user's actual goal, following the
[design principles](docs/design-principles.md). Use current evidence, reuse valid
work and choose capabilities as needed. User instructions take precedence over
Skill guidance; routine decisions stay with the Agent.

<!-- BEGIN VAWS session-start -->
Reuse a prepared workspace W and environment supplied by the native hook. Ordinary local review uses native tools; explicit remote endpoint or existing-container work uses remote-dev directly. These tasks need no startup, identity or knowledge preparation.

When independent local editing or managed preparation is needed and no W is prepared, run `uv run --no-project python .agents/scripts/vaws_start.py --client CLIENT` once. CLIENT is codex, cursor, claude, grok or kimi. Follow its result without a separate initialization probe. Pass `--context-file PATH` when the hook supplies context outside the client environment.

Use the returned `workspace` as W for shell calls and absolute paths under W for file, search and patch tools, even if the client UI shows the original project. Sources and environment are bound. Pass the existing `context_file` to tools that need task context. Official Kimi task tools require `context_file`; companion tools accept it when reusing the task's selected environment. Resume reuses the earlier W, task and environment without preparation or updates.
<!-- END VAWS session-start -->

## First use

For explicitly requested first-time setup, or when needed preparation reports
this repository has never been initialized, read
[repo-init](.agents/bootstrap/repo-init/SKILL.md). It is a one-time setup reference
outside the automatic Skill catalog. Reuse the user's confirmed personal GitHub
choice; an authenticated login is only a suggestion. Once initialized, ordinary
work, updates and repairs use their specific tools and returned facts.

## Choose the capability

| Work | Entry |
|---|---|
| Local files, shell, Git and ordinary PR review | Native tools |
| Explicit remote endpoint or existing container | remote-dev with host/port/user/cwd and optional container |
| Managed environment, NPU run or service | `vaws_run`, `vaws_execution`, `vaws_finish` |
| Knowledge lookup or capture | `knowledge_query`, `knowledge_explain`, `knowledge_capture` |
| Local fleet monitor lifecycle | [Monitor commands](docs/npu-fleet-monitor.md) |
| Domain development, measurement or debugging | The relevant business Skill |

For an existing container, preserve the supplied code, environment and command;
see [remote-dev consumption](docs/remote-dev-consumption.md).

`vaws_run` prepares its sources and resources; `vaws_session` is optional for
inspection or source overrides. Task identity comes from the native attachment's
`context_file` or `VAWS_CONTEXT_FILE`, never cwd, recent chats or reports. Joining
another task requires explicit association. Preserve unrelated worktrees, live
services and other tasks' resources. Tools handle ownership, reuse and records.

Read a selected Skill and only the references needed for the task. Knowledge is
optional reference; missing knowledge does not block work or prove absence.
Normal hooks reuse the final summary for capture, with no extra report required.

## Repository facts

Canonical upstream is `vllm-ascend-workspace/vllm-ascend-workspace`. Development
Forks belong to personal GitHub users. `vllm/` and `vllm-ascend/` are ordinary
independent repositories prepared on demand from the exact official pair in
`sources.lock.json`. The default development baseline and the release-vLLM baseline
use the same Ascend commit; the latter is not a complete stable Ascend stack.
Full multi-repository task directories use independent clones for the root and
children, without alternates. Existing sources and resumed tasks keep their
actual code. Native attachments expand prepared source roots automatically;
explicit task/run `sources={}` takes precedence. See the
[source workspace contract](docs/source-workspace.md).

People can open the returned workspace and inspect each repository with
`git -C vllm` or `git -C vllm-ascend`. Parent status does not report all child
changes. A returned native setup path or preparation receipt does not prove
that a client's UI switched directories; report actual paths and tested client
capabilities without claiming unverified UI behavior.

Runtime behavior belongs to remote-dev, vaws-coordinator, vaws-knowledge and
vaws-top; this workspace owns consumption and client wiring. Shared root servers
reuse compatible builds, weights and environments regardless of creator.

Control-plane checks run locally; torch/torch_npu/vLLM device execution runs in
remote Ascend containers. Validate affected behavior and callers, reusing useful
existing evidence. Keep runtime state under untracked `.vaws-local/` and never
commit credentials. Public knowledge export uses the package's redacted copy.

For architecture, maintenance or platform-specific work, use the relevant entry
in [docs/README.md](docs/README.md). Skill changes include their affected helpers,
metadata and generated client projections.
