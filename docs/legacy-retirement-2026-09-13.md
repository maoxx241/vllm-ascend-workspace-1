# Legacy consumer implementation retirement

Status: dated audit and validation evidence, 2026-09-13

The audit starts from workspace `eb30d0690edef67e26505a5332cc569de1ed6c59`.
It covers consumer bootstrap/helpers, client projections, non-analysis business
Skills and shared knowledge publishing. Profiling analysis internals are outside
this follow-up. This is bounded source and regression evidence, not a claim that
all unused code in every component has been proven absent.

## Retired or corrected

| Finding | Result and actual owner |
| --- | --- |
| An old repository-topology CLI duplicated remote mutation, branch selection and update behavior, with no production caller. | Removed the CLI and its wrapper tests. Current fork/source/update tools remain; the GitHub installer still has a dependency-free import smoke test. |
| A consumer query facade inferred project roots from a path and had only test callers. Two validator helpers also had no production callers. | Removed the unused helpers and their implementation-mirroring tests. The installed knowledge MCP keeps lookup/failure behavior; current configuration and real knowledge CLI tests remain. |
| Cursor retained an always-applied submodule rule and an outdated startup projection; English setup text described automatic main updates. | Removed the duplicate rule and aligned existing projections and documentation with the current source contract. A tracked projection regression uses the existing generator. No new per-task instructions or setup step were added. |
| The summary hook could prepare knowledge dependencies before inspecting invalid, foreign or empty native events. | Reject those inputs before owner preparation and replay the original bounded input on a required interpreter hop. Reuse the installed capture operation exactly once. |
| PD start required connector/proxy/smoke fields that did not configure its submitted services; per-service health timeout also did nothing. | Validate only each operation's consumed inputs. KV arguments, role environment and coordinator environment still pass through the existing topology operation. |
| Memory collection imported an unused msprof availability helper. | Removed the dead helper/import; the real execution wrapper retains its executable check. |
| Tensor dump guidance overstated first-nonfinite/stride observations, numerical equality, graph disabling and comparison memory limits. | Corrected those claims to the implemented boundaries without changing comparison algorithms. |
| Existing-evidence report examples looked like the primary operator/Triton execution inputs. | Label the supported report paths explicitly and point to the existing callable entry. Reports remain optional. |
| A useful parallel profiling-collection self-test lived under scripts and was absent from test discovery. | Move it into the existing Skill test suite. Native POSIX parallel/archive checks and the actual GNU timeout check have separate platform boundaries; Windows does not substitute its unrelated timeout command. |
| Skill text embedded unverified memory ranges/allocation heuristics and an old model-specific speculative-method failure account. | Preserve both as ordinary historical domain notes in the [knowledge corpus PR](https://github.com/vllm-ascend-workspace/vaws-knowledge-corpus/pull/5), with fixed source links and missing-evidence boundaries. Keep field formats and active CLI semantics in Skills. |
| The corpus release workflow still pinned the pre-reference knowledge engine. | Pin checks and publishing to reviewed knowledge commit `c57e7fb3322c8d83669e5c5f827446462892f113`, so a new immutable release includes a hash-bound reference asset. Pure Markdown does not thereby gain authored aliases or topics. |

## Retained deliberately

The packaged 65-note offline bootstrap is consumed by packaging and shared
search. Copying it into the remote corpus without identity/deduplication handling
would create duplicate references; removing it would lose offline material.
Dynamic serving entries, model presets, supported existing-evidence report paths,
runtime adapters and migration recognition all have current consumers.

Result-envelope helper candidates overlap the concurrently implemented diagnostics
work. They require reassessment against that merged implementation. No resource,
execution or knowledge owner is reimplemented in the consumer as part of this work.

## Verification scope

Targeted native Windows tests exercise the changed consumer and Skill behavior.
The summary regression uses two actual interpreter environments and the installed
knowledge capture implementation; it checks original input preservation and one
saved note. Invalid/foreign/empty public hook invocations also run without site
packages or an existing receipt. Skill test directories run in separate processes
to preserve their actual import boundaries.

The encoding regression preserves a failing direct launch with a CP936 pipe and
its corrected UTF-8 result. Generated Windows client launchers already set UTF-8;
this checks the direct/bootstrap boundary. Claude's Stop wrapper must reach the
shared event filter through its existing runtime before preparing knowledge.

The PR's existing Linux, Windows and macOS CI runs the full local suite and tracked
path checks. Corpus export verification and the installed 0.7.0 corpus check pass
for 26 Markdown documents. Installed release acceptance separately checks actual
shared retrieval and text identity. These are control-plane and reference checks;
they do not establish current NPU, model, connector or performance correctness.

This retirement does not implement Grok Bot review/merge of canonical knowledge
PRs. Public contribution review remains the existing separate maintenance boundary.
