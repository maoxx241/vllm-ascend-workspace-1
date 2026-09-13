# Knowledge component verification

Status: dated component evidence, 2026-09-13; not final consumer deployment acceptance

This record separates package CI, retained local results and merge state.
It covers the catalog/context/shared-reference work in
[PR 30](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/30) and the
independent curation/public export/static-source-map work in
[PR 31](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/31),
plus independent intake/feed transport in
[PR 32](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/32).
All three are merged. PR 31's canonical package 0.7.0 commit was
`24b652de235bae9ecfd08bbc29048cf7b59b4e90`; PR 32 subsequently merged at
`52754b5e5a714b9c60b4fa840daba5ecde97cb37`.

PR 33 and the final consumer pin/installed acceptance are subsequent work.
No result in this record is reassigned to that later code. This archive is not
VA development-domain knowledge and adds no task-Agent validation step.

## Exact CI provenance

GitHub PR state and complete checkout/test-summary lines were reread for this
archive. The workflows use pull-request merge-test refs. A workflow's `headSha`
identifies the PR head; its actual checkout below is a different Git commit.

| PR | PR head | Actual CI checkout | Final squash commit / merged UTC |
|---|---|---|---|
| 30 | `b91a63fa9f44b5bd0a6618a2bc774921082fa504` | `956578fec736c0ea35370b3d8ac0cfb4c1c704b0` | `4bdc37571e0ddb9c7312aabf64eaa22aabea2b9d` / 07:21:34 |
| 31 | `cc91e1eb573f503f864633402781117d6f11dbc3` | `0623dc174e5479e2c1cd001942c8fa13526ef0a8` | `24b652de235bae9ecfd08bbc29048cf7b59b4e90` / 07:30:42 |
| 32 | `b3eb681ef3ca5d20fb66ed56113b6968d3965cdc` | `2a135380f4cb77aba83316cff5df85454acf8c07` (independent intake CI) | `52754b5e5a714b9c60b4fa840daba5ecde97cb37` / 08:02:26 |

PR 30's merge-test parent was `e16d87287f7db51ca96efc945a9514e4146131d6`;
PR 31's was `4bdc37571e0ddb9c7312aabf64eaa22aabea2b9d`.
Every job below completed successfully. Passed tests, skips and pytest subtests
are separate columns and are not added together as independent test functions.

| PR / actual CI run | Platform / Python | Passed | Skipped | Subtests passed | Pytest elapsed |
|---|---|---:|---:|---:|---:|
| 30 [Package checks 34744780622](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34744780622) | Ubuntu / 3.11 | 440 | 4 | 12 | 12.86 s |
| 30 [Native contracts 34744780620](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34744780620) | Windows / 3.13 | 442 | 2 | 12 | 181.55 s |
| 30 same native run | macOS / 3.13 | 442 | 2 | 12 | 175.18 s |
| 31 [Package checks 34745112761](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34745112761) | Ubuntu / 3.11 | 501 | 4 | 12 | 27.35 s |
| 31 [Native contracts 34745112768](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34745112768) | Windows / 3.13 | 503 | 2 | 12 | 186.63 s |
| 31 same native run | macOS / 3.13 | 503 | 2 | 12 | 188.03 s |

The package workflow runs `pytest -q tests` and the public-corpus check.
Native jobs install the complete backend and enable
`VAWS_KNOWLEDGE_LIVE_OV=1` for the test suite, including real OpenViking lifecycle
cases. These are their selected contract tests, not arbitrary model/NPU runs,
production load or general performance benchmarks. The elapsed column is test
process time, not query latency or complete CI job duration. This archive did
not rerun the workflows or assert post-squash execution at the canonical SHA.

## Independent intake and feed: PR 32

PR state and all seven successful checks were reread: package checks,
Windows/macOS native contracts, and the four independent-intake jobs below.
[Independent CI 34746454502](https://github.com/vllm-ascend-workspace/vaws-knowledge/actions/runs/34746454502)
checked out the merge-test commit recorded above, combining head `b3eb681e`
with base `24b652de`. Its complete checkout and unittest summary lines were
independently reread; the matrix is not a post-squash rerun.

| Platform / Python | Tests reported | Passed | Skipped | Unittest elapsed |
|---|---:|---:|---:|---:|
| Ubuntu / 3.11 | 45 | 41 | 4 | 9.129 s |
| Ubuntu / 3.13 | 45 | 41 | 4 | 9.859 s |
| Windows / 3.13 | 45 | 43 | 2 | 43.194 s |
| macOS / 3.13 | 45 | 42 | 3 | 53.981 s |

Each job built and installed the independent wheel and checked both CLI entries
without the VAWS runtime. Native Windows OCR and macOS RSS checks ran on their
respective hosts; absent providers and foreign-platform capabilities stayed
skipped. macOS samples process RSS every 10 ms, permitting brief overshoot;
Windows/Linux use their operating-system process limits. These checks concern
format conversion, transport and feed integrity, not NPU execution or knowledge
answer quality.

## Executed cloud export and local scheduled return

The retained cloud observation records actual Grok Bot research/export,
verification and publication of four public-source Markdown notes. The personal
[feed commit](https://github.com/maoxx241/vaws-knowledge/tree/4ca634c8d0e54f07d831feffaaec633adb5eca9b)
is `4ca634c8d0e54f07d831feffaaec633adb5eca9b`, with manifest SHA256
`5b66c3ce0032d43a3ff53cdb0110d69dd836469ccf4d5166e485a704d5a82ce7`.
Its verified tree contains ten ordinary files: pointer, prepared manifest,
four notes and four permitted metadata sidecars. Raw source snapshots, private
sidecars and run archives were excluded. The cloud exporter and saved routines
were upgraded to `cc1a1d76fdee2c90b129f6ba56c171d500c158af`; actual export/verify
remained unchanged without a second feed commit.

The saved Grok routines were observed active: daily PR checks at 09:00
Asia/Shanghai, bounded to 20 minutes, and Saturday topic/digest work at 10:00,
bounded to 30 minutes. They use selected public vLLM/vLLM-Ascend sources and
retain uncertainty. This is an observation of saved instructions plus actual
manually dispatched cloud runs; a later scheduled Grok execution had not elapsed.
Canonical public corpus review/merge remains human. Pattern-based redaction is
not a classifier of arbitrary private prose.

Retained installed-wheel evidence shows a real live-feed import in 14.266 s,
then unchanged replay in 1.140 s with zero downloads and unchanged local bytes
and modification times. A separate 80-note local Git chain took 12.467 s;
one changed note took 2.211 s, reading pointer, manifest and two changed files
while reusing the other 158. These are separate transport observations, not
latency guarantees or production relevance measurements. The 1,024-note / 32 MiB
limit does not establish a maximum-size remote import within 120 seconds.

The persistent Windows reader used source `b3eb681e` and wheel SHA256
`f346bcbdb1d7973fca19b550dbedfed9791282ba6af628e9d5f8330794512e5e`.
Its actual per-user task has hourly and logon triggers, isolated windowless
Python, least privilege and an interactive-login requirement. An initial run
failed when terminal GitHub authentication was absent and preserved the old
notes. Public-API fallback resolved that failure without copying credentials.
A manual trigger succeeded in 1.304 s. The natural hourly run at
**2026-09-13 16:00:01 Asia/Shanghai** returned `LastTaskResult=0` and recorded
unchanged feed, zero downloads and 1.357 s. This archive reread the deployment
record, last-run receipt and actual Windows task information; the task still
reported that successful natural run and a 17:00 next trigger.

Transport is independent of model/backend startup, and the generated directory
is an ordinary additional project mount. The retained deployment record reports
that workspace refresh preserved it. This establishes actual local scheduling
and cloud-to-local transport; final PR 33/consumer installation and subsequent
Grok schedule executions retain their separate gaps.

Selected private records were reread and hashed. They remain local; this archive
omits task names, local paths, accounts and credentials. Cloud UI observations
are attributed to the retained owner record, not a second UI run in this audit.

| Artifact label | SHA256 |
|---|---|
| `cloud-feed.json` | `0cb8bb0fd035587ee2ccfa9179fa76eef45b493bd4fa1a7dacbc274b9077160c` |
| `feed-native/acceptance.json` | `8b8dd76e568f8ad39ce271e914f6dc5bfe4f23f1ff63d0ee81270da04682ea7c` |
| `feed-growth/acceptance.json` | `73936f1ef84225e8b0a897b69dccb5961ba6b313f7afffcac1ce3eb79454cae5` |
| `reference-intake/deployment.json` | `42c5bb2f176cac5ffdd153a6b9ad0c72f7cd5df409811b98bd3102e9178efeb0` |
| `reference-intake/state/last-run.json` | `3e9a8d1052554f483f1e8377d2734ea46edb8c175bdfbe320541448de9732bfb` |

## Retained local result integrity

Three existing JUnit files were reread and hashed. The two preserved source
copies were also compared to all tracked `vaws_knowledge/`, `tests/` and
`pyproject.toml` blobs in their stated commits: 108 files matched for the catalog
snapshot and 127 for the curation snapshot, with no mismatch. The snapshots are
ordinary directories, not separate Git checkouts; Git discovery from within
them must not be mistaken for their historical source revision.

| Artifact label | Preserved source association | JUnit entries | Skips | Failures / errors |
|---|---|---:|---:|---:|
| `catalog-pr-tests.xml` | `catalog-pr-snapshot`, matching `7105a2cc8b488948a14475891f25cbfacd85cdd3` | 455 | 4 | 0 / 0 |
| `curation-pr-tests.xml` | `curation-pr-snapshot`, matching `95185f3cf71984a39c22f18d1caf14d56f1edc18` | 517 | 4 | 0 / 0 |
| `catalog-native-fix.xml` | Historical local OpenViking run; exact revision not embedded in XML | 2 | 0 | 0 / 0 |

The complete-suite counts correspond to the retained run reports of
439 passed / 4 skipped / 12 subtests and 501 passed / 4 skipped / 12 subtests.
The JUnit totals include those subtests. The native file currently contains only
`test_capture_query_update_delete_and_restart` and
`test_project_add_edit_delete_and_pending_recovery`; it does not retain an
earlier 36-test affected-suite run. That earlier count is not attached to this
file. No XML embeds loaded package/dependency revisions, so the retained-source
comparison does not establish every runtime dependency or relabel a local run
as either PR's final CI checkout.

| Artifact label | SHA256 |
|---|---|
| `catalog-pr-tests.xml` | `a927afcfed7d762180cd15850ddbe05663f7e49d5c1043b30f51c9f211e3ff20` |
| `curation-pr-tests.xml` | `25495b64914dc2f12ead4feec452277135ede95bdff7e7de83a8d4395ae0fe3c` |
| `catalog-native-fix.xml` | `a59e0e149d2a7113992b5502ecbc90e3c685c13a28012089b9a27e20393aa4b6` |

The XML and snapshot copies remain in their owning task's private local state.
They contain local machine/path fields and are not published here. Hashes prove
the identity of the reviewed files, not the truth or freshness of unrelated
claims. The older knowledge 0.6.0 consumer evidence and the 90-suite workspace
summary keep their original provenance limits in the [archive](README.md).
