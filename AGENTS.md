# VAWS workspace

This repository contains project materials, client wiring and business skills.
Optimize the total cost of completing the user's actual goal, following the
[design principles](docs/design-principles.md). Use current evidence, reuse valid
work and choose capabilities as needed. User instructions take precedence over
Skill guidance; routine decisions stay with the Agent.

<!-- BEGIN VAWS session-start -->
Reuse a prepared workspace W and environment supplied by the native hook. Ordinary local review uses native tools; explicit remote endpoint or existing-container work uses remote-dev directly. These tasks need no startup, identity or knowledge preparation.

For first-use setup or independent editing without prepared task facts, reuse a valid completed `.vaws-local/onboarding.json` from this workspace or its explicitly recorded owner. Otherwise read `.agents/bootstrap/repo-init/SKILL.md` and offer only missing setup choices. A saved `.vaws-local/github.json` confirms a username, not Fork, Star or community choices. Reuse explicit answers and saved progress; a new task is not a new user. Existing setup needs no authentication or network probe.

When independent local editing or managed preparation is needed and no W is prepared, run `uv run --no-project python .agents/scripts/vaws_start.py --client CLIENT` once. CLIENT is codex, cursor, claude, grok or kimi. Follow its result without a separate initialization probe. Pass `--context-file PATH` when the hook supplies context outside the client environment. New tasks select the local fixed commit and a matching ready cache; `--latest` explicitly checks upstream. The default operation directory is the selected Ascend repository; use `--repo workspace` or `--repo vllm` for an explicit alternative.

Keep the returned `workspace` as W, the root for task configuration, Skills and environment. Use returned `cwd` and `repository` for business shell/Git operations and their commit target, even if the client UI shows the original project. Use absolute paths under W for VAWS scripts and Skills; a business cwd does not contain W's `.agents` directory. Sources and environment are bound. Pass the existing `context_file` to tools that need task context. Official Kimi task tools require `context_file`; companion tools accept it when reusing the task's selected environment. Resume reuses the earlier W, task and environment without preparation or updates.
<!-- END VAWS session-start -->

## First use

On first entry to a fresh clone, for explicitly requested setup, or when preparation
reports incomplete initialization, read
[repo-init](.agents/bootstrap/repo-init/SKILL.md). It is a one-time setup reference
outside the automatic Skill catalog. Reuse the user's confirmed personal GitHub
choice; an authenticated login or connector is only a suggestion. Confirm the
independent Fork, optional Star and community collaboration choices once and
persist them with `vaws_init.py`. Once initialized, ordinary work, updates and
repairs use their specific tools and returned facts without repeating these choices.

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
