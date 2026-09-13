# Consuming remote-dev

Status: current

Generic remote operations live in
[`vaws-remote-dev`](https://github.com/vllm-ascend-workspace/remote-dev).
This workspace installs the package and wires its MCP server with ordinary
configuration. remote-dev stays independently usable with explicit
`host` + `port`, with an optional existing Docker `container` on that host.
It needs no VAWS task binding or confirmed GitHub identity. See
[target-state.md](target-state.md).

## 1. Start from the user's endpoint

For "use container `repro-case`, code in `/work/vllm`, run the existing
`/work/start-case.sh`", call `remote_bash` directly:

```json
{
  "host": "lab-host",
  "port": 22,
  "container": "repro-case",
  "cwd": "/work/vllm",
  "command": "bash /work/start-case.sh"
}
```

`lab-host` and the paths above are example coordinates. Use the host, container,
directory and command supplied for the task. The same endpoint coordinates work
with remote reads, edits, search, patches, artifacts and owned jobs. A container
that already exposes SSH continues to use its ordinary host/port endpoint.

There is no preliminary session, mode switch, alias creation, source sync,
environment preparation or manual execution record. Local PR review continues
through native Git and file tools. Optional knowledge query/explain/capture use
the existing local provider; remote code does not need to be copied into a local
checkout. Neither task depends on coordinator or knowledge readiness.

## 2. Existing container semantics

`host`, `port` and `user` describe SSH access to the Docker host. `container`
selects an already-running Docker name or ID; `root` and `cwd` refer to paths
inside it. Docker retains the container's configured user. The selected operation
requires its existing prerequisites: Python 3 for workers, Bash for shell work
and Docker access for the SSH account. Missing prerequisites return an error;
remote-dev does not install packages, start/restart containers or rewrite scripts.
Jobs use the existing `root/.remote-dev` scratch convention, so that root must be
writable by the configured container user. For a non-root container, the Agent
can pass the existing writable code directory as `root`; no privilege override
or container repair is performed. Read-only file tools do not require job scratch.

The command remains the user's command. Existing code, interpreter selection,
shell initialization and environment files are reused. A custom startup script
is not automatically sourced as a profile or converted into a managed service
recipe. If the task needs shell setup, use the explicit command or the existing
`runtime_env_file` facility with its ordinary shell semantics.

Each name or short-ID operation resolves a running container to its full Docker
ID before opening workers, recording reads or submitting a job. The result's
`target.container` is that full ID; `target.container_selector` preserves the
original name/short ID for display when applicable. Reusing `target.container`
as the next call's `container` avoids another name lookup and keeps the same
container generation. This is ordinary endpoint reuse, not a required binding
step. A fresh name-based call can select a replacement container; a retained job
reference always stays on the original full ID and never follows a reused name.

RPC, binary artifact transfer, script/stream execution and worker-created PTYs
run inside that container. Endpoints for different containers keep separate
worker, read and job state. Transport loss after a possibly submitted mutation,
command or stdin write preserves the uncertain result; it does not cause replay.
remote-dev stops only jobs it created and can identify. Existing worker scratch
and job logs are normal remote-dev writes, not a claim of zero filesystem cost.

Every public Endpoint entry either implements container semantics or rejects the
endpoint before acting. Interactive SSH authentication/bootstrap
(`interactive_ssh_command` / `run_interactive`) rejects it; use the ordinary SSH
host endpoint for authentication and `remote_bash` with `tty: true` for a shell
inside the container. SSH local forwarding also rejects it: forwarding to a
published container port requires an explicit host endpoint and a host-reachable
port. Neither helper silently substitutes the host's localhost or filesystem.

Direct container execution does not allocate managed NPUs/ports or claim another
task's processes. Follow the user's device requirements and relevant occupancy
evidence when running their NPU script; file inspection needs no device query.
Managed allocation, preparation and topology remain with coordinator. In
particular, `vaws_run(sources={})` still selects a managed runtime; it does not
select the arbitrary existing container above.

## 3. Installation when requested

```bash
uv run --no-project python .agents/scripts/vaws_deps.py sync
uv run --no-project python .agents/scripts/vaws_deps.py status vaws-remote-dev
```

Client setup installs a stable MCP gateway. Direct calls use the configured
workspace's saved immutable environment without task preparation. Calls with
native or explicit context keep that task's selected environment; the gateway
starts `-m remote_dev.mcp.server` there.
A mutable workspace venv is not required.

## 4. What this workspace may inject

| Variable | Value | Why |
|---|---|---|
| `REMOTE_DEV_STATE_DIR` | `<repo>/.vaws-local/remote-dev-state` | Package-owned job records and logs |
| `REMOTE_DEV_SSH_MUX_DIR` | `~/.ssh/vaws-mux` | Shared multiplexed SSH directory |
| `REMOTE_DEV_DEFAULT_USER` | `root` | Ordinary default user |

Do **not** inject `REMOTE_DEV_RESOLVERS` or a global
`REMOTE_DEV_RUNTIME_ENV_FILE`. Coordinator supplies a complete launch
environment on managed executions. Ad-hoc remote-dev calls use the explicit
endpoint the caller already has.

## 5. Skill transport

Skills do not construct SSH options. For ordinary remote I/O they call
`.agents/lib/vaws_remote_dev.py` helpers that wrap `remote_dev.core.ssh_transport`
with an explicit endpoint mapping returned by coordinator or typed by the
user. They do not resolve `session_id` / `machine` through a consumer plugin.

## 6. Client wiring

`uv run --no-project python .agents/scripts/vaws_client_setup.py --client all --apply`
configures the remote-dev provider through `vaws_native_mcp.py`. The gateway
uses the configured workspace's saved environment for direct calls, or selects
the task's fixed environment from explicit context or actual native metadata.
It then forwards ordinary remote calls to the package and strips its
routing-only `context_file` before calling the remote-dev backend. It does not
resolve endpoints, allocate resources or implement a remote-dev resolver.

Supported client hooks provide context; official Kimi can pass the existing
`context_file` when selecting a prepared task environment. It is optional for
direct endpoints. New tasks can use newly prepared components without
manually reconnecting the client, while resumed tasks keep their earlier
selection. The package remains independently usable with explicit endpoints.

Generated configuration preserves user server fields and follows the existing
native interpreter/Windows owner rules, including required WSL environment
forwarding. This does not expand mixed Windows/WSL worktree support. See the
[platform contract](platform-contract.md) and
[native client contract](native-workspace-isolation.md) for those boundaries.
