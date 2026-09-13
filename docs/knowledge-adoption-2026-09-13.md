# TeamAI / WeKnora mechanisms adopted for VAWS knowledge

Status: dated implementation and validation evidence (2026-09-13)

## Decision and scope

Retain the existing three optional Agent tools: `knowledge_query(text, limit)`,
`knowledge_explain(ref)` and `knowledge_capture(title, content)`. Improve their
internal retrieval and give a separate maintainer a bounded local worklist.
No task receives a new checklist, contribution reminder, required citation
declaration, model call, knowledge approval or completion step.

The reviewed VAWS knowledge baseline is `3a65926db4be36f39bf5efb516d1f74bd37702c5`
(0.5.1), and the consumer baseline is `60c49fffd7038e316daf3124ffebc93a1303b184`.
This implementation belongs to `vaws-knowledge`; the consumer only pins the
package and documents the behavior. Parallel work owns coordinator performance
and source workspace preparation. This change does not modify those owners or
their startup/client selection code.

## Upstream research

Research read current source, not just feature lists. Neither upstream service
was installed or benchmarked. These are source observations, not upstream
runtime acceptance results. Both repositories use MIT licenses; the VAWS code
is a small original implementation of the selected ideas, with no new upstream
runtime dependency.

| Repository and fixed revision | Useful source mechanisms | VAWS decision |
|---|---|---|
| [TeamAI `6dc1b991`](https://github.com/Tencent/teamai-cli/tree/6dc1b9919ef1856717c381d6559bb7738089075e) | [Source hashes and incremental changes](https://github.com/Tencent/teamai-cli/blob/6dc1b9919ef1856717c381d6559bb7738089075e/src/wiki-engine/code-knowledge/code-incremental.ts#L15-L57), [deduplication before result truncation](https://github.com/Tencent/teamai-cli/blob/6dc1b9919ef1856717c381d6559bb7738089075e/src/utils/search-index.ts#L854-L872), [separate maintenance drafts](https://github.com/Tencent/teamai-cli/blob/6dc1b9919ef1856717c381d6559bb7738089075e/src/index.ts#L1051-L1075) | Reuse existing hash-based indexing; suppress duplicate summary writes; deduplicate retrieval routes by source URI; expose mechanical findings to a maintainer. |
| [WeKnora `17f89386`](https://github.com/Tencent/WeKnora/tree/17f893865d4d8337f7e0bf942c6931a8ce7a08c1) | [Source positions and original content](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/types/chunk.go#L107-L166), [RRF fusion](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/application/service/knowledgebase_search_fusion.go#L31-L141), [content-change revisions](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/application/service/wiki_page.go#L111-L188) | Return matching Markdown excerpts and line positions; fuse lexical and existing semantic rankings; separate source changes from management activity. |

WeKnora's [RSS hash check](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/datasource/connector/rss/connector.go#L247-L270)
skips unchanged Markdown. Its [sync failure semantics](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/datasource/connector/feishu/core/engine.go#L20-L27)
retain the cursor after fetch failure. VAWS already records content hashes and
embedding fingerprints only after successful indexing, and preserves previous
records when sources are unreadable. That valid work is reused, not replaced.

WeKnora also [coalesces queued operations](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/application/service/wiki_ingest.go#L1081-L1140).
VAWS already has an owner lock, persisted maintenance deadlines and capture
wakeups. Extending this owner avoids a new queue service or orchestration API.

## Implemented behavior

### Retrieval

The existing vector backend remains in place. BM25 over already mounted
Markdown adds code identifiers and Chinese character bigrams that semantic
retrieval can miss. Reciprocal rank fusion combines route rankings without
comparing incompatible raw scores. Each URI contributes once per route, before
the requested limit. Rank is relevance, never factual confidence; review status,
popularity and age do not determine it.

Local hits carry a query-related excerpt, one-based source lines, a starting
column when a long line is clipped, and a SHA256 of UTF-8 source text with
normalized newlines. It identifies the text observed during that query, not a
permanent promise that the file is unchanged. Shared-pack results identify the
indexed snapshot and its source Git revision when known. Original content is
still available through `knowledge_explain`.

If vectors are pending or unavailable, readable mounted Markdown can still
match lexically; output retains the actual degraded/unavailable state. Missing
mounts and unreadable sources remain incomplete/unknown. Shared documents only
inside a remote index cannot receive a local lexical scan during an outage.
Queries do not start a model, embed documents or rewrite the index. Existing
valid MCP use can request the package's normal background preparation.

### Maintenance and repeated capture

`python -m vaws_knowledge health --config PATH` returns at most 50 findings by
default and the full count. It requires no backend, network or model. It writes
only a rebuildable local cache. Its automatic invocation belongs to active
knowledge maintenance: at its health deadline or an explicit verification/change
wakeup. Unused MCP connections and ordinary task summaries do not run it.

The worklist reports exact duplicate Markdown with compatible recorded context,
age as a review hint, unreadable/missing sources as unknown, and byte changes to
relative linked sources inside the mounted roots since observation. It does not
fetch external links, reconstruct absent provenance, infer a semantic conflict,
or automatically delete, merge, publish or promote notes. Unchanged records reuse
parsed content and the cached report. Age does not mean a claim is wrong.

An independent maintainer can use the existing `curate-knowledge` skill and this
worklist, compare available evidence, and edit ordinary Markdown within its
authorized scope. Open judgment stays there. This implementation does not launch
an unattended LLM, consume model credits, or establish a recurring Codex task.

Native summary hooks retain the first capture's timestamp and provenance on a
replayed final response. Duplicate events no longer rewrite Markdown or queue
another contribution. A maintainer's revision is preserved. The hook remains
silent and uses only the already available final response, not a full transcript.

### Deliberately not adopted

- TeamAI's [main-Agent recall and referenced-document requirements](https://github.com/Tencent/teamai-cli/blob/6dc1b9919ef1856717c381d6559bb7738089075e/src/builtin-rules.ts#L123-L168)
  and [contribution reminders](https://github.com/Tencent/teamai-cli/blob/6dc1b9919ef1856717c381d6559bb7738089075e/src/contribute-check.ts#L481-L498).
- Turning [usage-derived confidence](https://github.com/Tencent/teamai-cli/blob/6dc1b9919ef1856717c381d6559bb7738089075e/src/maintenance/confidence.ts#L16-L42)
  into stronger knowledge authority or unconditional rules.
- Full code graphs, Auto-Wiki entity extraction, tenant administration, new
  databases/queue services and speculative semantic conflict detection.
- WeKnora's [source lookup error treated as deletion](https://github.com/Tencent/WeKnora/blob/17f893865d4d8337f7e0bf942c6931a8ce7a08c1/internal/application/service/wiki_lint.go#L207-L218).
  VAWS retains unknown on failures.
- Automatic friction extraction from private transcripts or PR ingestion. Those
  need separate source authorization and demonstrated benefit; the existing final
  summary already supplies a cheap observation path. TeamAI's local-agent is a
  reporting/configuration client, not evidence of a deployed independent curator.

## Nine-principle assessment

| Principle | Concrete effect |
|---|---|
| 1. Total goal cost | Avoid another search method during an index outage, opening whole long notes for a small fact, and duplicate summary writes. |
| 2. Bounded automation | Hash, tokenize, rank, locate excerpts and find mechanical differences in tools; semantic decisions stay with the maintainer. |
| 3. Agent understanding | Keep the three existing tool signatures; no retrieval weight, worklist or source-form input for ordinary tasks. |
| 4. Clear ownership | Retrieval and local maintenance remain inside the knowledge package; no workspace knowledge engine. |
| 5. Informational skills | Add one optional maintenance entry to the existing skill; no compulsory research path or new mandatory skill. |
| 6. Reference only | Age, duplicates, review and source-change observations neither prove truth nor authorize execution. |
| 7. On demand | Unused connections remain idle; maintenance failure does not block query fallback or independent work. |
| 8. Reuse | Retain existing embedding signatures/repair logic; reuse health parses and capture identity. |
| 9. Observable | Return actual route/degradation, source positions/hash, and maintenance scope/findings. |

## Validation record

The package implementation is
[`485ddc0d`](https://github.com/vllm-ascend-workspace/vaws-knowledge/commit/485ddc0d71e86915487a1204032426a3d874ba0e),
submitted in [package PR 29](https://github.com/vllm-ascend-workspace/vaws-knowledge/pull/29).
The consumer lock selects this exact revision as version 0.6.0 and preserves
the other package pins. PR and deployment state should be checked live; this
document records executed evidence rather than asserting that a review merged.

- Final local package suite: **394 passed, 4 skipped, 10 subtests**.
- Native Windows/OpenViking run: **394 passed, 2 skipped, 10 subtests**,
  including capture, update, deletion, restart and pending recovery. Final cache
  and excerpt refinements were then covered by affected tests and the complete
  local suite. Native distribution release-pack tests remain separately opt-in.
- Consumer knowledge wiring: **71 passed** across eight existing test files,
  covering setup, shared ownership, preparation, summary adapters, MCP and startup.
- An installed 0.6.0 wheel outside its source checkout queried the existing
  OpenViking owner for ACLGraph replay, SSH ControlMaster streams and dump row
  limits. All **3/3** found the expected source in the first five results and
  expanded it successfully; all hits carried evidence and none were degraded.
- A second health pass reused the same snapshot with **zero reparsed records**.
- Public packaged Markdown scan: **65 documents, zero problems**. Diff checks
  passed. Private runtime measurements and source paths remain in local evidence.

Source-code review of upstream features does not establish a measured VAWS
throughput or retrieval-quality improvement. These synthetic regression and
small live smoke cases exercise exact identifiers, Chinese text, long evidence,
fusion, outages, missing mounts, repeated summaries, source changes and reuse.
They do not measure a broad production retrieval-quality gain.

The first local health inspection saw 88 mounted Markdown documents and no
mechanical findings. This is a dated scoped observation, not a quality score,
proof of completeness, or a claim that all corpus content is current.
