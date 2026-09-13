# Managed execution performance redesign

Status: dated implementation and measured evidence, 2026-09-13.

## Changes delivered

The coordinator owns preparation and execution observations; the consumer owns
HTTP readiness and useful business output. This change removes repeated work and
Agent round trips from those paths without introducing another task checklist.

| Previous work | Implemented behavior | Required boundary retained |
| --- | --- | --- |
| Separate native marker, profile validation and cache publication jobs | One supervised finalization job | Actual final runtime load, artifact identity and quiet process family |
| Repeated source artifact hash passes within one finalization | Reuse that invocation's captured hashes; hash copied destination bytes | Corrupt or incomplete copies cannot establish readiness |
| Client-side status polling, followed by another log call | Bounded owner wait; terminal logs returned and retained after confirmed release | Timeout preserves the execution ID and does not cancel or resubmit |
| Long wait monopolizes the MCP request loop | Separate wait and control workers with serialized output | Status and stop requests remain available while waiting |
| Agent decodes compressed preparation evidence | Owner returns recorded source/build facts and bounded artifact matches | Evidence must match the admitted source identity; no new remote probe |
| Repeated remote calls for health, models and token readiness | One bounded remote command with conditional HTTP probes | A timed-out response is not successful readiness, even after HTTP 200 headers |
| Repeated logs during successful service startup | Cached owner state plus current HTTP readiness; diagnostics on failure | Current model/token readiness cannot be inferred from old logs |
| Full envelope repeated in serving output | Business result and reference to the retained full record | Record-write failure is explicit and preserves the business outcome |
| Service implementation loaded just to validate input | Shared lightweight request validation | Local-only invalid requests do not initialize the service runtime |

`TaskClient.run` accepts a bounded UTF-8 `script_file` and optional
`wait_until`/`wait_timeout_seconds`. `wait` no longer accepts `poll_interval`.
These are coordinator 0.5.0.dev1 interface changes. Consumer callers and help
were updated together. Remote completion supervision still uses its existing
approximately two-second interval; owner notification removes client polling,
not the remote supervisor's detection delay.

Independent source/workspace work owns repository preparation, startup lock
scope and removing optional knowledge/monitor preparation from ordinary startup.
Those changes are not counted in the measurements below. The knowledge 0.6.0
update from main is retained independently.

## Measured result

Both real-machine pairs used coordinator baseline `384b89b71078bcad49212d3f6104ccc847485cec`
and remote-dev `a65362882a85b4d460be3e1d15e90de9fb507e70`.
The native candidate was frozen at `a91f19a9d7c63d8fe1228ad91aa02eecc6cd82ab`;
the warm candidate used `d2095dca08c5c06052596798e5d3c02ae640ed5f`.
Later local-input validation and Git stdin repairs do not change the measured finalizer.
These are controlled task-submission measurements, not new fresh-Agent trials.

| Boundary | Baseline | Candidate | Interpretation |
| --- | ---: | ---: | --- |
| Native change: submit to observed quiet/released | 98.61 s | 96.78 s | 1.83 s reduction in one serial pair |
| Incremental compile job, same remote clock | 39.58 s | 39.58 s | Compilation cost unchanged |
| Finalization job execution, same remote clock | 11.69 s in three jobs | 10.21 s in one job | 1.48 s less execution, excluding observation gaps |
| Business operator test | 7.35 s | 7.69 s | Both actual kernel and numerical checks passed |
| Warm unchanged-source entry through necessary logs | 26.87 s | 28.31 s | This pair does not demonstrate a warm speedup |

Native preparation job count fell from eight to six, including the missing-object
probe. The candidate returned terminal logs with the wait result; the baseline
used a separate tail call. The optional recorded build-evidence query took 39 ms.
An owned offline serving status serialized to 1,002 bytes instead of 3,273 bytes
(69% smaller), with equivalent business facts and a readable full-record reference.
These are serialized JSON bytes, not network-transfer measurements.

Candidate finalization measured a real runtime smoke/load of 7.42 s, source
hashing of 0.41 s, destination copy of 0.49 s and destination verification of
0.37 s. Its cache-store total of 0.87 s includes copy and verification; these
numbers must not be added twice. The in-process total was 9.47 s, excluding
launch/preamble and observation. Tests establish one source hash pass and one
destination hash pass for 1,104 artifacts, replacing four total passes.

Both native arms really compiled all three FP32/FP16/BF16 recipe variants from
distinct comment-only changes. Captured manifests retained all variants.
The FP32 16 by 128 operator case checked an independent CPU reference and the
actual opened owned kernel object. Both produced maximum absolute errors of
9.54e-7 for the output and 5.96e-8 for reciprocal standard deviation. FP16/BF16
were compiled, but this pair does not establish their numerical validation.

## Limits and remaining performance work

The 1.86% native difference is not a statistical speedup guarantee. Candidate B
could reuse A's newly published bundle as an incremental base; A used an earlier
compatible bundle. Both performed actual compilation. A used an immutable
installed package; B used an editable installation whose actual source path,
module hashes and clean Git commit were verified. That distinction is retained.

Warm inputs and command were identical, but local Windows tests overlapped the
candidate window. The observed startup-context host operation increased from
0.39 s to 4.69 s. Its existing trace does not separate local scheduling, transport
and remote processing, so the extra time is not attributed to vLLM or to a
specific transport phase. All durations subtract timestamps from the same clock.

The one-second total goal is not met. The measured compiler job alone takes
about 40 seconds, and final actual loading takes about seven seconds. The next
runtime work should measure the host-operation subphases and reduce stable
preparation and launch boundaries through owner-managed reuse. Eliminating
unnecessary Agent calls and returning useful evidence already removes separate
orchestration work, but it does not justify claiming the remaining execution
latency has disappeared.

All measured business and preparation jobs became quiet and released their owned
resources. Fixture daemons stopped through the official idle operation. Existing
containers, unrelated workloads and historical source worktrees were preserved.

## Verification

Owner checks cover actual destination corruption, failed runtime smoke,
publication races, cancellation and quiet ownership, script encoding, bounded
waits with concurrent control requests, terminal log completeness and local-only
input rejection. Consumer checks cover compact/full equivalence, record-write
failure and an actual loopback HTTP response that times out after sending 200
headers. The official MCP SDK exercises local session, invalid run, ownership,
finish and clean subprocess exit. Platform CI is required for both linked PRs.

Implementation and exact platform results:
[coordinator PR 33](https://github.com/vllm-ascend-workspace/vaws-coordinator/pull/33)
and [consumer PR 165](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/pull/165).
Detailed private logs and fixed-input audits remain local; internal endpoints,
container identifiers and user paths are intentionally absent from this report.
