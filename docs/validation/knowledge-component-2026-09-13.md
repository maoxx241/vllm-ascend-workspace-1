# Knowledge component verification

Status: dated component evidence, 2026-09-13; not final consumer deployment acceptance

This record separates package CI, retained local results and merge state.
It covers the catalog/context/shared-reference work in
[PR 30](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/30) and the
independent curation/public export/static-source-map work in
[PR 31](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/31).
At this cutoff both PRs are merged, and canonical package 0.7.0 is at
`24b652de235bae9ecfd08bbc29048cf7b59b4e90`.

PR 32 and the final consumer pin/deployment are subsequent work. No result in
this record is reassigned to that later code. This engineering archive is not
VA development-domain knowledge and adds no task-Agent validation step.

## Exact CI provenance

GitHub PR state and complete checkout/test-summary lines were reread for this
archive. The workflows use pull-request merge-test refs. A workflow's `headSha`
identifies the PR head; its actual checkout below is a different Git commit.

| PR | PR head | Actual CI checkout | Final squash commit / merged UTC |
|---|---|---|---|
| 30 | `b91a63fa9f44b5bd0a6618a2bc774921082fa504` | `956578fec736c0ea35370b3d8ac0cfb4c1c704b0` | `4bdc37571e0ddb9c7312aabf64eaa22aabea2b9d` / 07:21:34 |
| 31 | `cc91e1eb573f503f864633402781117d6f11dbc3` | `0623dc174e5479e2c1cd001942c8fa13526ef0a8` | `24b652de235bae9ecfd08bbc29048cf7b59b4e90` / 07:30:42 |

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
