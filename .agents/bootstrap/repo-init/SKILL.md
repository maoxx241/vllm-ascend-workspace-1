---
name: repo-init
description: Initialize this repository once when its startup entry reports needs_setup. Read through the first-use pointer in AGENTS.md; established repositories use the relevant maintenance command directly.
---

# First repository setup

This reference lives outside automatic skill discovery. Use it only for a
repository that has not completed first-use setup. New sessions, updates and
repairs use their existing entries without loading this reference again.

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

The fork tool initializes missing submodules at their recorded gitlinks, creates
or reuses verified personal forks, and preserves existing work. It reports any
conflicting remote configuration for judgment. Dependency setup reuses prepared
environments and also prepares knowledge; pending knowledge does not block
ordinary tools. Client setup detects installed clients, preserves unrelated
configuration and records its result in the shared repository state.

Complete the running client's native trust prompts. If it has not loaded the
new providers/hooks, reopen the project or start a new native session once.
That session follows the normal startup entry; configuration alone is not proof
that a client has loaded it. No further initialization checks belong to ordinary
tasks, and resume keeps its existing workspace and environment.

For missing installer prerequisites, see [bootstrap prerequisites](references/command-recipes.md).
Fork behavior and targeted later repairs are documented in
[forks and updates](../../../docs/forks-and-updates.md).
