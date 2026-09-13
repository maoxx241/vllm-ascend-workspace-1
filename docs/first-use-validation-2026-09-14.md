# First-use and community acceptance — 2026-09-14

Status: passed Windows/GitHub acceptance; the measurements below identify the
candidate and boundaries actually tested.

## Fresh clone and actual Agent

The final native candidate was workspace commit
`9b5bcae57bd15a6538182995f47497caa1bdea10`, with diagnostics 0.2.1,
remote-dev 0.9.3 and coordinator 0.5.0.dev5 installed from its exact lock.
Fresh HTTPS clones used independent user directories, Codex state, Git settings,
environment stores, logs and service state. Existing authentication was securely
reused; no identity snapshot, onboarding record, task or context was pre-created.

The real Agent discovered missing initialization, read repo-init, called
`vaws_init.py status --detect-auth`, suggested the authenticated account and asked
once for username, Fork, Star and community choices. The isolated acceptance
reply used the confirmed personal account, Fork yes, Star no and community
disabled. It did not change the main workspace's contribution choices.

The client was Codex CLI `0.154.0-alpha.6.2`, using `gpt-6-astra` / `xhigh`.
Reviewed project hooks were allowed through the CLI's explicit hook-trust option.
This proves CLI hook loading; it does not prove a desktop trust dialog, editor
directory switch or another client's native behavior. The first task edited a
file in an independent root repository, without business repositories or NPU work.

Single observations follow, not percentiles or latency guarantees. The package
download cache already existed; the selected immutable environment did not.
Nested phases must not be added again to their parent's duration.

| Operation | Seconds | Boundary |
| --- | ---: | --- |
| HTTPS clone and commit verification | 3.72 | Git |
| Initialization with Fork, no Star or contributions | 14.12 | Formal apply command |
| Fork verification and remote configuration | 5.34 | Nested initialization phase |
| Fresh locked production environment | 6.87 | Nested initialization phase |
| Codex configuration | 0.85 | Nested initialization phase |
| Declined knowledge contribution configuration | 0.07 | Local only; owner not prepared |
| Declined automatic reporting | 0.03 | Local only; no worker installed |
| First independent root task preparation | 3.60 | Internal preparation timer |
| Independent root clone | 1.12 | Nested task preparation phase |
| Resume read, edit and verification | 0.53 | Sum of observable native tool intervals |

| Agent turn | Whole CLI turn, seconds | Sum of observable tool intervals, seconds |
| --- | ---: | ---: |
| Discover first-use choices | 50.90 | 1.95 |
| Apply the answers | 54.43 | 14.60 |
| First independent task | 130.88 | 6.30 |
| Resume the same task | 71.69 | 0.53 |

Whole turns include model inference, native hooks, subprocess orchestration,
service startup and response generation. Observable tool intervals do not account
for all of that time; the difference cannot be assigned entirely to the model.
This does not establish a one-second end-to-end Agent interaction.

An earlier candidate exposed a stale generated knowledge catalog during cold
initialization. The operation remained pending instead of treating a saved
identity as successful setup. The catalog was regenerated and initialization
was repeated from a separate fresh clone.

Independent native-registry assertions then caught a resume defect: the Agent
edited the correct independent directory, but the attachment's source pointed
back to the original clone after SessionEnd. The fix belongs to coordinator:
the same native session revalidates its prepared sources after detachment. A
changed native directory clears the previous automatic selection; an explicit
empty source selection remains explicit, and invalid sources remain an error.
Consumer tests exercise actual detached/resume transitions for all five clients.
The final fresh native run passed: after the first task, before resume, and after
resume, the actual registry kept `native-prepared` and the same independent
workspace, native attachment, session and immutable environment receipt. Both
CLI exits actually detached the attachment. File contents were independently
verified; the original clone was unchanged and no second task was created.

## Contribution choices and authentication

A separate real matrix at workspace `01e2d6da2513d70c91ffb27bf17c77e46c61fb28`
used diagnostics 0.2.0 and knowledge 0.7.4. Formal initialization with Fork no,
Star no and community enabled took 44.68 seconds: runtime dependencies 6.97,
client wiring 0.98, first knowledge environment/corpus setup 27.43, and Windows
reporter installation 8.37. Optional setup stages are still sequential. The
reporter had a healthy heartbeat, with no knowledge or incident awaiting upload.

Disabling that workspace took 0.75 seconds. Reapplying the same choices with
HTTP and Git network access forbidden reused setup in 0.45 seconds. A separate
fresh clone without a token or gh login completed local-only setup in 3.77
seconds using an already installed runtime, then reused it in 0.44 seconds.
It installed neither a knowledge owner nor a reporter. A single long-lived
knowledge process observed disabled, enabled, disabled without restarting.
Later knowledge 0.7.5 changes only version and the exact diagnostics dependency;
the live-consent behavior is unchanged and tested with diagnostics 0.2.1.

The final native candidate also passed a real token-only fixture with gh
unavailable: account lookup, independent HTTPS clone, personal Fork verification,
local commit, push and remote SHA verification, in 19.87 seconds. Its temporary
branch was deleted and verified absent. Tokens were absent from remote URLs,
Git configuration and identity records. A real Git regression enabled TRACE2
environment dumping with a fake token; the adapter prevented creation of the
trace file. Tests cover both GH_TOKEN and GITHUB_TOKEN selection.

## Supervised reporter and central diagnosis

The official diagnostics 0.2.0 worker created the explicitly synthetic
[acceptance issue #178](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues/178)
in 4.60 seconds. The separate supervised central Grok service posted its
[diagnosis](https://github.com/vllm-ascend-workspace/vllm-ascend-workspace/issues/178#issuecomment-5654443131)
49 seconds after creation, correctly identifying an intentional fixture. The
issue was closed and the fixture consent revoked. Diagnostics 0.2.1 changes
service reuse and bounded file handling; this reporting path is unchanged.

Disabled events and events queued before revocation made zero GitHub calls and
zero upload attempts. Public content passed the leak scan, without private
policy paths or workspace identity. Already-public issues remain eligible for
central maintenance. Automatic code changes, merges and deployment are not
implemented.

Official diagnostics 0.2.1 wheel SHA256:
`812bf063177295befb5d364055a92390c9739ad0e2261f72f757214061d8d755`.
Non-editable Windows acceptance used a locally built 0.2.1 candidate wheel from
the same released source and verified the new `service ensure` operation:
two clones merge log roots while retaining the existing state, credentials and
gh login. Owner tests separately cover preserving optional bot configuration.
An unchanged setup retains the running process;
a real configuration change restarts it. A new caller token does not replace
the established token or gh login. Converting a central bot to a local reporter
is rejected in the no-start case. Packaged-client paths are resolved to physical
Windows paths.

Permanent Windows reporting and the WSL central service now run this official
0.2.1 wheel with fresh state. Both have healthy worker heartbeats; old 0.2.0
processes exited. WSL central runs without local roots or local ingestion and
has its own protected authentication file. Its Windows login bridge was
triggered successfully and reached the new process. No old database or process
compatibility layer is retained. Per-event live workspace consent is still
required for local automatic publication.
Retired Windows and WSL worker credential copies were removed after confirming
that the new services use independent protected files; original authentication
profiles and historical diagnostic evidence were preserved.

## Verification and evidence

| Component | Selected version | Reviewed change |
| --- | --- | --- |
| diagnostics | 0.2.1 | [PR #6](https://github.com/vllm-ascend-workspace/vaws-diagnostics/pull/6), `96fcdfaa0f25fa59f12e948eb4e17ead775f3287` |
| remote-dev | 0.9.3 | [PR #18](https://github.com/vllm-ascend-workspace/remote-dev/pull/18), `89d197ef13bcae46f7bea809c22bbb058c4edfbf` |
| coordinator | 0.5.0.dev5 | [PR #38](https://github.com/vllm-ascend-workspace/vaws-coordinator/pull/38), `1b1ad5a558283307794801e778330c03b1c52cc2` |
| knowledge | 0.7.5 | [PR #39](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/39), `8a5ef8abad99011c16a309133c4fb82b03c9cfbe` |
| top | 0.1.6 | [PR #9](https://github.com/vllm-ascend-workspace/vaws-top/pull/9), `d8c0e062620fd314f0502c091703839c42df27d1` |

The locked dependency closure additionally includes remote-dev commit
`89d197ef13bcae46f7bea809c22bbb058c4edfbf` and coordinator commit
`1b1ad5a558283307794801e778330c03b1c52cc2`. Compared with the native candidate,
these add a Darwin process-group exit fix and corresponding dependency metadata;
the tested native source-binding implementation is unchanged. On Darwin, a
permission error during group cleanup is accepted only after a bounded check
proves there are no live members; live or unknown status preserves the error.
Final local-state review also added targeted regressions after the full native
run: explicit revocation precedes parsing damaged onboarding progress, a saved
identity or client configuration alone does not imply completed setup, and a
missing identity cannot produce a false successful reuse. Saved confirmed
identity labels can be restored locally without inventing fork or numeric-ID
facts. These exceptional-state changes were verified separately; the full native
timing above remains evidence for the named candidate.
Concurrency regressions block the actual setup runner while another caller
revokes consent: the switch returns without waiting for installation, and the
older initializer cannot restore enabled consent after it resumes. Concurrent
first choices retain one workspace identity. A missing policy requires an
explicit new choice instead of recovering authorization from setup history.
The reverse interleaving is covered too: a delayed local disable cannot overwrite
a newer enabled knowledge configuration or leave a false ready setup record.
The local configuration update shares the short policy lock; no network work
holds that lock. Upload checks still read the live consent independently.

The final native fixture's copied Codex/GitHub authentication caches were removed,
as were copies from both failed earlier candidates. All three owned test process
sets were empty. The four original personal client/authentication files retained
their original hashes. All owned service-acceptance tasks and processes were
removed; the authorized permanent reporters remain running. The contribution
matrix ended with no pending contribution, no owned worker and no copied worker
credential file. No Star was performed.

Retained local evidence is under the untracked workspace state. These identifiers
locate engineering records, not public knowledge or portable runtime inputs:

- `first-use-native-20260914/20260913T164538-66e9b927/acceptance-result.json`:
  final native assertions, exact components, timing, token fixture and cleanup.
  `record.json` and stage `.timeline.jsonl` files retain the observed transitions.
- `e2e-community-20260914/result.json` and
  `cleanup-system-verification.json`: enabled, disabled, offline reuse and cleanup.
- Diagnostics owner `native-service-ensure-20260914/acceptance-result.json`:
  0.2.1 candidate-wheel native Windows worker reuse and removal; the official
  release wheel was used for the subsequent permanent deployment.
- Diagnostics owner `automatic-acceptance-result.json` and
  `central-acceptance-0.2.1.json`: actual issue/bot fixture and final deployment.

The workspace and component pull requests retain the exact three-platform CI
results. Local owner/consumer tests also cover revocation, cross-workspace policy
selection, missing-core diagnostic fallback, credentials, bounded file reads,
process cleanup and failed setup retries.
Device execution, native macOS launchd installation and deployment on a
non-WSL Linux host were not part of this Windows/GitHub acceptance.
