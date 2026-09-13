# Bootstrap prerequisites

Read only the operation needed by a first-use failure. The normal sequence is in
[the initialization reference](../SKILL.md); no whole-repository probe is needed.

## GitHub CLI

The fork command reports whether `gh` or authentication is missing. Authenticate
with the user's chosen personal account through `gh auth login`. If `gh` is not
installed and a normal package install is unavailable, the user-local fallback
installers are:

```text
uv run --no-project python .agents/bootstrap/repo-init/scripts/install_gh_user.py
powershell -ExecutionPolicy Bypass -File .agents/bootstrap/repo-init/scripts/install-gh-user.ps1
```

Use the installer for the actual platform. It does not choose or authenticate a
GitHub user. Windows/WSL owner and offline dependency preparation details are in
[Windows installation](../../../../docs/windows-installation.md).

## Fork conflicts

`workspace_forks.py` without `--apply` reports its current plan. Review only the
reported conflict; preserve intentional refs, extra remotes and dirty work.
When replacing conflicting primary remote URLs is intended,
`--replace-primary-remotes` records their prior values before replacing them.
See [personal forks](../../../../docs/forks-and-updates.md#个人-fork).

Initialization preserves existing source revisions. To inspect the locked
development pair without network access, use
`uv run --no-project python .agents/scripts/workspace_sources.py show`.
The same command with `show --channel release` selects the declared vLLM release
baseline for the same Ascend commit. An explicit
`uv run --no-project python .agents/scripts/workspace_sources.py refresh`
updates only the committed source lock from upstream declarations; it does not
switch existing code. Later source selection, dependency repair and client changes use the
[maintenance commands](../../../../docs/forks-and-updates.md#显式维护与证据).
