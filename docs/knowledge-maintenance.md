# VA reference maintenance

Status: current

The knowledge library supports vLLM-Ascend development through references about
vLLM, Ascend NPU, AI and inference infrastructure. Normal tasks retain optional
`knowledge_query`, `knowledge_explain` and `knowledge_capture`. A title and
Markdown body are enough. Maintenance is independent of development tasks.

General model, debugging and infrastructure notes belong to the canonical
[vaws-knowledge-corpus](https://github.com/vllm-ascend-workspace/vaws-knowledge-corpus),
with their sources, conditions and uncertainty retained. Shared releases supply
these references; the consumer keeps tool instructions, runtime contracts and
engineering validation. `.agents/knowledge/` is an optional project-specific
mount, not a second domain library. Its placeholder ignores local note content;
it may be absent or empty. Existing custom
mounts, intake output and candidate storage remain supported.

## Available capabilities

| Need | Owner and behavior |
|---|---|
| Import external material | The independently installable `knowledge-intake` tool handles selected local files, URLs, fixed Git sources and vLLM/vLLM-Ascend PR evidence; emits normal Markdown, original assets and source observations. |
| Reuse PR experience | An independent agent derives cases from pinned base/head and source evidence; merged state and CI labels do not prove runtime claims. VAWS PRs are outside automatic experience intake. |
| Maintain topics, aliases and digests | Grok Bot or another independent native agent reads bounded sources and existing summaries; produces source-linked Markdown and retains uncertainty. Package curation preserves history and rejects intervening source/target edits. |
| Navigate code and linked claims | Optional static Python/C++ maps retain source revisions and lines, PyTorch registration links, backlinks and affected-source hints. Dynamic or heuristic links remain labelled. |
| Retrieve useful context | A local catalog reuses extraction; source-bound aliases, optional topic selection and context spans keep conditions, table headers and code fences within bounded output. |
| Read images/scans | Agent-native vision or optional OCR in the independent intake tool produces hash-bound descriptions linked to the original image/page. No local multimodal model is required. |
| Evaluate retrieval | Explicit labelled-question evaluation reports ranking, citations, latency and incomplete state; synthetic regression fixtures do not certify production answer quality. |
| Inspect all VAWS tools | The separate [validation archive](validation/README.md) maps capabilities to retained PR/test/runtime evidence and gaps; it is not VA domain knowledge or a task checklist. |

The package CLI exposes `catalog`, `evaluate`, `code-map`, `relations`,
`curation` and `curation-export` for explicit maintenance. Detailed options
belong to its `--help` and optional `curate-knowledge` skill, available through
`python -m vaws_knowledge skill`. These commands are not additional MCP tools.
C++ parsing is an optional package extra. Intake and scheduled feed transport
are installed separately; dependency sync does not add them to task startup.

## Independent public-source maintenance

Grok Bot can keep public source material and previous summaries in its cloud
computer. A bounded daily PR routine and weekly topic/digest routine avoid
continuous polling and keep unchanged runs quiet. Each task uses its existing
GitHub authentication; authentication files are never knowledge inputs.

`curation-export` prepares a separate generation containing selected Markdown,
permitted retrieval metadata and a hash manifest. The shared redaction profile
is pattern based, not a classifier of arbitrary private prose. Automatic cloud
feeds therefore stay within selected public upstream sources. Raw source
snapshots, private sidecars, credentials and curation history are not feed
payloads. Canonical public corpus review and merge remain human.

A personal feed branch can hold the verified generation and its `current.json`
pointer. The independent `knowledge-feed` synchronizer resolves the branch to
one Git commit, validates the pointer and all file hashes, then updates only
its owned generated files. It preserves human edits and previous content on
failure. A Windows scheduled task can run that small synchronizer periodically;
it does not start the knowledge backend or a local model. The resulting normal
Markdown directory is an additional configured project mount. Knowledge's own
maintenance indexes it on real knowledge use.

## Resource and evidence boundaries

The target is a 16 GB Windows laptop without a discrete GPU. Ordinary queries
perform no document conversion, generation, OCR or whole-library rebuild.
Expensive scans back off according to measured duration. Explicit reports retain
bounded stdout and save detailed artifacts locally. Existing CPU text embeddings
remain optional reference infrastructure; no new multimodal embedding process
is introduced.

The package records native MCP, standalone conversion, static code extraction,
shared release and 10k/100k catalog measurements in its dated acceptance report.
Memory measurements were taken on a larger development host and describe
process requirements, not an end-to-end run on a physical 16 GB machine. Known
conditions, source hashes and incomplete findings remain visible; generated
topic pages and published notes do not gain decision authority.
