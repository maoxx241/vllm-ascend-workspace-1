# VAWS workspace

This repository contains project materials, client wiring and business skills.
Optimize the total cost of completing the user's actual goal, following the
[design principles](docs/design-principles.md). Use current evidence, reuse valid
work and choose capabilities as needed. User instructions take precedence over
Skill guidance; routine decisions stay with the Agent.

<!-- BEGIN VAWS session-start -->
Reuse a prepared workspace W and environment supplied by the native hook. Otherwise, make a new session's first repository action `uv run --no-project python .agents/scripts/vaws_start.py --client CLIENT`. CLIENT is codex, cursor, claude, grok or kimi. It checks initialization; follow its result without a separate probe. Pass `--context-file PATH` when the hook supplies context outside the client environment.

Use the returned `workspace` as W for every shell call and absolute paths under W for file, search and patch tools, even if the client UI shows the original project. Sources and environment are already bound. If a tool needs context, pass the existing `context_file`. Official Kimi also passes `context_file` to the task, remote-dev and knowledge MCP tools.

Resume reuses the earlier W, task and environment without preparation or updates.
<!-- END VAWS session-start -->

## First use

Only when startup reports this repository has never been initialized, read
[repo-init](.agents/bootstrap/repo-init/SKILL.md). It is a one-time setup reference
outside the automatic Skill catalog. Reuse the user's confirmed personal GitHub
choice; an authenticated login is only a suggestion. Once initialized, ordinary
work, updates and repairs use their specific tools and returned facts.

## Choose the capability

| Work | Entry |
|---|---|
| Local files, shell, Git and ordinary PR review | Native tools |
| Explicit remote endpoint I/O | remote-dev tools with host/port/user/cwd |
| Managed environment, NPU run or service | `vaws_run`, `vaws_execution`, `vaws_finish` |
| Knowledge lookup or capture | `knowledge_query`, `knowledge_explain`, `knowledge_capture` |
| Local fleet monitor lifecycle | [Monitor commands](docs/npu-fleet-monitor.md) |
| Domain development, measurement or debugging | The relevant business Skill |

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
Forks belong to personal GitHub users. Keep `.gitmodules` on community upstreams
`vllm-project/vllm` and `vllm-project/vllm-ascend`.

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
