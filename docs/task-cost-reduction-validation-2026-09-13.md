# Task cost reduction validation

Status: measured engineering evidence, 2026-09-13.

This records package and workspace changes in [coordinator PR #34](https://github.com/vllm-ascend-workspace/vaws-coordinator/pull/34)
and [workspace PR #171](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/171).
It is not a business-task checklist or an additional reporting requirement.

## Changed behavior

- New local tasks use the current local workspace commit and fixed cached inputs.
  Upstream discovery and personal-fork synchronization require explicit `--latest`.
  Missing fixed objects or packages can still require downloads.
- Child source preparation runs independently. Repeated Git repository discovery
  is reduced, while full three-repository tasks retain independent Git stores,
  exact source commits and no alternates.
- The selected Ascend repository is the default editing directory. Explicit
  `--repo` overrides, per-repository status/diff, normal first push, and preserved
  branches, stash and dirty state are supported. Task-specific editor views do not
  overwrite shared workspace defaults. An explicit source task context can carry
  its repository choice into a fork; clients without that association retain the
  source preparation's choice.
- Core task preparation installs a 41-package runtime on the tested Windows
  interpreter. The separate 171-package knowledge environment is prepared only
  by valid knowledge use or explicit prewarming. Tool discovery reads a generated
  official catalog frozen with the original lock and starts no knowledge worker.
  Existing tasks retain their original package selections.
- Managed native preparation combines owned-root creation, source materialization
  and native publication where the bounded command fits. Compilation alone holds
  the host compiler lock. Valid Python import evidence is reused only when the
  captured import closure and dependencies still match; native outputs remain
  checked and changed kernels still compile.
- Completion observation wakes from supervisor evidence. Complete drained logs
  for the same terminal job can satisfy the final log request without another RPC.
  Incomplete or uncertain observations retain the existing fallback.
- Provider recovery does not replay an uncertain business call. Fixed task schema
  validation prevents a current tool catalog from silently upgrading an old task.
- Operator and Triton helpers accept an actual candidate callable and reference.
  Profiling collection returns a compact analysis handoff. Their affected skills,
  metadata and generated client projections were updated together.

## Local source startup

Windows production `vaws_start.py` ran serially with the same fixed vLLM and
Ascend source seed, available package caches, and no simultaneous local test run.
The old mechanism used workspace `6bf22b6`; the candidate used `a5bce10` with
coordinator `0105b223`. The later coordinator change only corrects selection of
timing fields in appended remote logs and does not change local source startup.

| Complete CLI operation | Baseline | Candidate |
|---|---:|---:|
| First new independent three-repository task | 26.253 s | 12.176 s |
| Another new task using preparation cache | 17.081 s | 7.551 s |
| Resume the existing task/context | 0.202 s | 0.226 s |

New-task samples were 53.6% and 55.8% shorter. Resume was 24 ms slower in this
single pair, with no evidence of a meaningful resume improvement. All six calls
passed source identity, independent Git directory, no-alternates and task context
checks. Candidate defaults selected Ascend and preserved the original repositories.

The candidate cached path spent 0.728 s selecting preparation, 4.720 s creating
the source copies and 1.526 s configuring the client. Copying included 2.244 s
for the root followed by parallel children: vLLM 2.476 s and Ascend 1.907 s.
Those clone stages include checkout, refs, configuration and validation; they
are not a measurement of disk I/O alone. First preparation instead spent
5.228 s preparing its shared inputs. Dependencies and exact source objects were
already available; this is not a network-cold installation or a statistical SLO.
The baseline personal-fork fast-forward occurred before measurement and is
recorded separately, not charged to its timed startup.

The historical 45.287 s first preparation and 0.621 s resume are documented in
[the earlier source validation](source-workspace-validation-2026-09-13.md).
Those historical numbers included upstream checks and are not a controlled
comparison against this candidate.

## Installed dependency and provider acceptance

With installed coordinator `5b83148` and unchanged locked remote-dev and
knowledge revisions, a new immutable core bundle took 6.125 s to
prepare. This included fetching and building the new coordinator revision and
installing 41 packages; package installation itself took 0.740 s. The existing
knowledge component was neither installed again nor modified.

| Read-only operation | Measured seconds |
|---|---:|
| Warm dependency preparation | 0.249 |
| Task backend tool discovery | 0.684 |
| Remote-dev backend tool discovery | 0.246 |
| Knowledge catalog discovery, no backend | 0.193 |

These are individual local API samples, not complete native-client startup times.
The three providers exposed 5, 18 and 3 tools. Core imports, exact installed Git
identity, selected interpreter routing and unchanged immutable receipts passed.
The already-installed knowledge component means this sample does not by itself
prove behavior when knowledge is absent. Real tiny-wheel tests separately cover
absence, first-use installation, concurrent installers, original-lock reuse after
a checkout update, cancellation, corrupted inputs and legacy ready receipts.

An explicitly installed leak-scanning Git hook still needs the knowledge package's
redactor. Its first actual check can prepare that optional environment. Ordinary
Git does not install that hook automatically. No scan rule or failure check was
bypassed to obtain these timings.

## Managed NPU observations

Installed baseline `9f94f279` has the same tree as coordinator `262272bb`.
The first candidate was installed immutable `3cfab05`. Public owner ping confirmed
the loaded revision before each serial sample. Both used the same existing private
fixture, source inputs, device and remote-dev version. Unrelated live services,
native task selections and source roots were preserved.

| Initial sample | Run call through observed release | Inner business timer | Outcome |
|---|---:|---:|---|
| Baseline, same native source | 34.418 s | 7.612 s | succeeded, quiet, released |
| First candidate, same native source | 31.207 s | 7.395 s | succeeded, quiet, released |
| Baseline, CPP-only change | 88.067 s | 7.454 s | succeeded, quiet, released |
| First candidate, CPP-only change | 76.686 s | not started | failed preflight, resources released |

The failed sample is retained and is not counted as a speedup. Compilation and
native smoke passed, but a metadata probe omitted the captured CANN launch path
and could not find a recorded distribution. The correction applies the bound
launch environment before both probe interpreters start; it still verifies
distribution version and origin. The corrected installed `5b83148` completed
the same business validation and released its resources. Its first CPP run took
89.030 s with a cold owner. Actual three-variant compilation took 40.138 s;
the compatible import-proof check took 0.420 s with `native_smoke_executed=false`,
compared with the baseline's 7.812 s native import. Finalization's inner work fell
from 9.875 s to 3.023 s. Cold materialization and transport offset that saving in
the whole first-run sample, so 89.030 s is not reported as an end-to-end speedup.

The same installed owner then completed an unchanged-source run in 22.980 s,
including 7.594 s inside the business timer. Combined preparation took 5.776 s:
its receipt reports source materialization 1.789 s and native publication 1.947 s.
Source metadata was 0.043 s within publication and must not be added again.
This sample reused warm connections, unlike the initial 34.418 s baseline;
it is an observed warm cost, not a controlled 11-second improvement claim.

One final new CPP-only input was then compiled under the same warm owner. It
completed, became quiet and released resources in **77.872 s**, compared with
the baseline warm CPP sample's **88.067 s**. Actual three-variant compilation
took 40.349 s, import-proof verification 0.416 s, finalization inner work 2.997 s
and the inner business timer 7.549 s. The 10.195 s difference is 11.6% for this
ordered pair, not a variance-adjusted performance guarantee. A new comment-only
source revision ensured this was actual compilation rather than a native cache
hit. The private owner stopped through its official idle-stop operation after
all three final runs, with its IPC endpoint removed and no owned execution left.

The same-source difference is one ordered pair with cold owner connections, not
a statistical claim. Candidate launch took 8.014 s, including startup context
4.560 s, verification 1.286 s and admission 0.910 s. A subsequent startup context
took 0.409 s, supporting a cold-transport explanation without proving its individual
handshake phases. The fenced release itself took 1.472 s. The business timer
excludes an audit-helper compiler invocation and Python/NPU teardown, so its
difference from the running interval cannot all be assigned to VAWS observation.

A separate real NPU callable run passed contiguous and transposed strided inputs,
with maximum absolute difference zero and two recorded candidate invocations.
Submission through released reply took 20.280 s. This covers the shared submission
helper and actual payload, not native-client UI, all CLI arguments or a Triton
kernel. No Triton NPU run was performed in this round.

## Validation and limits

The repository editing and fork behavior passed Windows and WSL functional
acceptance with private bare Git remotes, preserving original refs and index bytes.
Local callable, source, provider, environment, completion and preparation tests
passed at their recorded component revisions. Coordinator `5b83148` passed
1,239 Linux tests and 1,213 macOS tests, with 52 subtests on each; their respective
2 and 28 skipped tests are retained as skips. Its remaining Windows CI and the
final workspace three-platform CI are checked on the PR before merge. The first
workspace macOS run found a new test fixture's unresolved temporary-directory
alias; the fixture now matches production's canonical owner paths, without
weakening workspace association checks.

Raw timings, per-sample failures, JUnit files, owner records and private test
drivers remain under untracked local validation directories. Private infrastructure
coordinates and complete raw logs are not published here. Receipt paths do not
prove that a native client's UI switched directories, and these measurements do
not claim model serving throughput or an entire task below one second.
