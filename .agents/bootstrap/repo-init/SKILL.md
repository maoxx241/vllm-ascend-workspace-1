---
name: repo-init
description: Initialize this repository once when explicitly requested or required preparation reports missing first-use setup. Read through AGENTS.md; established repositories use the relevant maintenance command directly.
---

# First repository setup

This reference lives outside automatic skill discovery. Use it only for a
repository that has not completed first-use setup, when the user requests it or
required preparation reports missing setup. Ordinary local work, PR review and
explicit remote endpoints, including existing containers, need no initialization
or identity confirmation. Later sessions, updates and repairs use their specific
entries without loading this reference again.

Ask once for the user's personal GitHub username, explaining that setup creates
personal development forks and configures installed clients for upstream updates
and worktree sessions. Reuse an explicit answer. The authenticated `gh` login is
a suggestion, not the user's choice; OS accounts and remotes do not establish it.
Independent local/read-only work can continue while the answer is pending.

After the user accepts setup, run the following from the repository:

```text
uv run --no-project python .agents/scripts/workspace_forks.py --github-user USER --apply
uv run --no-project python .agents/scripts/vaws_deps.py sync
uv run --no-project python .agents/scripts/vaws_client_setup.py --client all --apply
```

The fork tool initializes missing source repositories at their locked revisions, creates
or reuses verified personal forks, and preserves existing work. It reports any
conflicting remote configuration for judgment. Dependency setup installs or
reuses package environments; knowledge activates on actual use. Client setup
detects installed clients, preserves unrelated
configuration and records its result in the shared repository state.

The committed `sources.lock.json` records both upstream-declared vLLM baselines
for one Ascend commit. Initialization uses the development baseline; existing
source repositories retain their current work and intentional revisions. These
source declarations do not establish NPU runtime validation. Read the selected
pair without network access using `.agents/scripts/workspace_sources.py show`.
Refreshing the lock is explicit repository maintenance, never a first-use or
per-task prerequisite.

Complete the running client's native trust prompts. If it has not loaded the
new providers/hooks, reopen the project or start a new native session once.
Configuration alone is not proof that a client has loaded it. Prepare through
`vaws_start.py` when independent editing or managed preparation is needed; reuse
a workspace already supplied by native setup. Resume keeps its existing workspace
and environment. Official Kimi passes the hook context to startup and task tools;
remote-dev and knowledge accept it optionally to select that task's environment.

For missing installer prerequisites, see [bootstrap prerequisites](references/command-recipes.md).
Fork behavior and targeted later repairs are documented in
[forks and updates](../../../docs/forks-and-updates.md).
