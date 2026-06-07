# safishamsi/graphify -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: A `/graphify` slash-command skill for 20+ AI coding assistants (Claude Code, Codex, Cursor, Gemini CLI, Aider, OpenCode, Kilo Code, Copilot CLI, VS Code Copilot Chat, Devin CLI, and more) that maps an entire project folder -- code, docs, PDFs, images, videos -- into a queryable knowledge graph.

**How it works (end-to-end pipeline)**:

1. **detect()** -- walks the directory tree respecting `.graphifyignore` / `.gitignore`, classifies files by extension into CODE (28 tree-sitter grammars), DOCUMENT, PAPER (PDF), IMAGE, VIDEO buckets. Extensions span Python, JS/TS/JSX, Go, Rust, Java, C/C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir, Julia, Verilog, Fortran, Pascal, Groovy/Gradle, Dart, R, Bash, JSON, SQL, Terraform/HCL, BYOND DreamMaker, and Visual Studio solution/project files.

2. **extract()** -- Two-phase extraction per file:
   - **AST pass** (local, zero API calls): Uses 28 tree-sitter grammars to parse every code file. Walks each CST to extract symbols (functions, classes, variables, interfaces, types, imports, calls, inheritance edges). Every extracted edge gets a confidence label: `EXTRACTED` (explicit in source, e.g. an import statement), `INFERRED` (call-graph second pass / heuristic), or `AMBIGUOUS` (uncertain).
   - **Semantic pass** (LLM, only for non-code files): For docs, PDFs, images, videos, the file content is sent to a configured LLM backend (Gemini, Kimi, Claude, OpenAI, DeepSeek, Ollama, Bedrock, or claude-cli) with a strict JSON schema prompt that demands `{"nodes": [...], "edges": [...]}` with the same confidence tag system. Supports `--mode deep` for richer extraction. The semantic pass uses adaptive retry: if `finish_reason="length"` surfaces, the chunk is bisected recursively up to 3 levels deep.

3. **build()** -- Merges all extraction dicts into a single `networkx.Graph` (or DiGraph). Three layers of deduplication: within-file (seen_ids), between-file (NetworkX add_node idempotency), and semantic merge (explicit seen set). Runs `deduplicate_entities()` which uses a pipeline of exact normalization -> entropy gate -> MinHash/LSH blocking -> Jaro-Winkler verification -> same-community boost -> union-find merge. Optional LLM tiebreaker (`--dedup-llm`) for ambiguous pairs in the 75-92 Jaro-Winkler zone. Ghost-duplicate auto-merge for AST vs semantic collisions on `(source_file basename, label)`.

4. **cluster()** -- Community detection via Leiden algorithm (graspologic) with Louvain fallback (networkx). Communities larger than 25% of the graph are recursively split. A second cohesion pass re-splits communities with cohesion < 0.05 and >= 50 nodes. Configurable resolution parameter. Optional hub-exclusion percentile (`--exclude-hubs 99`) for utility super-hubs.

5. **analyze()** -- Computes: god nodes (top-N most-connected real entities, excluding file-hubs, concept nodes, JSON noise labels, and builtin noise like `str`/`int`/`Mock`); surprising connections (cross-file or cross-community edges ranked by a composite surprise score accounting for confidence, cross-file-type, cross-repo, cross-community, and peripheral-to-hub patterns); suggested questions (from AMBIGUOUS edges, bridge nodes with high betweenness, god nodes with many INFERRED edges, isolated nodes, low-cohesion communities); and import cycle detection via Johnson's algorithm on a file-level directed import graph.

6. **report()** -- Renders `GRAPH_REPORT.md` with corpus check, god nodes, surprising connections, import cycles, community breakdown with cohesion scores, confidence audit, suggested questions, and token-cost summary.

7. **export()** -- Outputs `graph.json` (full graph in node-link format), `graph.html` (interactive browser visualization), optional Obsidian vault, markdown wiki, SVG, GraphML (for Gephi/yEd), Neo4j Cypher, and Mermaid call-flow HTML.

**The key innovation**: Every relationship edge carries a confidence tag (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`), so the consumer always knows what was found in source versus guessed by the model. This is analogous to Lyra's source-tagging ambition.

## 2. Architecture & Core Modules

**Entry point**: `graphify/__main__.py` -- the CLI entry. `graphify/__init__.py` uses lazy `__getattr__` to defer heavy imports. The CLI handles: graph building (all-in-one `/graphify .`), incremental update, reclustering, headless extraction, query, path explain, PR triage, hook install, platform skill install (20+ platforms), export, merge, clone, and the benchmark runner.

**Pipeline modules** (each a single function, zero shared state, communicate via plain dicts and NetworkX graphs):

| Module | Function | Purpose |
|--------|----------|---------|
| `detect.py` | `collect_files(root)` | File discovery, type classification, `.graphifyignore`/`.gitignore` resolution |
| `extract.py` | `extract(path)` | Tree-sitter AST extraction for code; MCP config extraction |
| `build.py` | `build_from_json(extraction)` / `build(extractions)` | Merge extraction dicts into `nx.Graph`, deduplicate, normalize IDs |
| `cluster.py` | `cluster(G)` | Leiden community detection with oversized-community splitting |
| `analyze.py` | `god_nodes(G)`, `surprising_connections(G, communities)`, `suggest_questions(...)` | Graph analysis |
| `report.py` | `generate(...)` | GRAPH_REPORT.md rendering |
| `export.py` | `to_json`, `to_html`, `to_obsidian`, `to_wiki`, etc. | Multi-format export |
| `llm.py` | `extract_files_direct()`, `extract_corpus_parallel()` | Multi-backend LLM extraction with token-aware chunking and adaptive retry |
| `dedup.py` | `deduplicate_entities()` | Entity deduplication pipeline (MinHash/LSH + Jaro-Winkler + union-find) |
| `serve.py` | `serve(graph_path)` | MCP stdio server with 10 tools and 6 resources |
| `cache.py` | `check_semantic_cache / save_semantic_cache` | Semantic extraction cache |
| `security.py` | URL validation, path validation, label sanitization, size caps | Input validation layer |
| `benchmark.py` | `run_benchmark(graph_path)` | Token-reduction benchmark |
| `cache.py` | `check_semantic_cache / save_semantic_cache` | Semantic extraction cache |
| `watch.py` | `watch(root, flag_path)` | File watcher for auto-rebuild |
| `callflow_html.py` | `write_callflow_html(...)` | Mermaid architecture/call-flow HTML |
| `prs.py` | PR dashboard, triage, impact analysis | GitHub PR integration |
| `hooks.py` | Post-commit / post-checkout git hooks | Git integration |
| `manifest.py` | `manifest.json` read/write | Portable manifest tracking |
| `querylog.py` | Query logging | JSON Lines query audit trail |
| `transcribe.py` | Video/audio transcription (faster-whisper) | Media support |
| `wiki.py` | Markdown wiki export | Wiki generation |
| `scip_ingest.py` | SCIP index import | SCIP/lsif interoperability |
| `mcp_ingest.py` | MCP config extraction | `.mcp.json` parsing |
| `google_workspace.py` | Google Workspace export | `.gdoc`/`.gsheet`/`.gslides` support |
| `graph_global.py` | Cross-project global graph | Multi-repo graph merging |
| `semantic_cleanup.py` | Semantic post-processing | Cleanup of semantic extraction results |
| `symbol_resolution.py` | Cross-file symbol resolution | Resolve imports to file nodes |
| `multigraph_compat.py` | MultiGraph compatibility | Backward compat for legacy graphs |
| `validate.py` | `validate_extraction(data)` | Schema enforcement for extraction dicts |
| `affected.py` | Affected-file analysis | Determine which files changed |
| `diagnostics.py` | Diagnostic checks | Health checks for graph state |
| `tree_html.py` | HTML tree view | Alternate HTML visualization |

**Dependencies**: networkx (core graph), datasketch (MinHash/LSH), rapidfuzz (Jaro-Winkler), tree-sitter (28 language grammars as core deps), optional: graspologic (Leiden), mcp, neo4j, anthropic, openai, boto3, pypdf, faster-whisper, yt-dlp, jieba (Chinese), matplotlib (SVG), python-docx, openpyxl.

**Architecture pattern**: Functional pipeline -- each pipeline stage is a pure function. No shared state, no classes. Communicates via plain dicts and NetworkX graphs. Tested with pytest (82 test files). The skill/install system uses a platform-config-driven installer that supports 20+ AI assistant platforms with progressive-disclosure skill files.

## 3. Performance / Benchmarks

The repo ships a built-in benchmark (`graphify/benchmark.py`) and benchmark CLI (`graphify benchmark`):

- **Token reduction**: Measures tokens in full corpus vs tokens in BFS-derived subgraph for 5 sample questions. Typical reduction ratios are 25-50x (e.g., a 50k-token corpus yields ~1-2k token subgraph per query).
- **Corpus sizing guidance** (built into `detect.py`):
  - Below 50,000 words: "you may not need a graph" warning.
  - Above 500,000 words or 500 files: token cost warning.
- **AST extraction parallelism**: Controlled by `--max-workers` / `GRAPHIFY_MAX_WORKERS` (default auto).
- **LLM extraction parallelism**: `--max-concurrency` (default 4; forced to 1 for Ollama and claude-cli unless explicitly opted in).
- **Cost tracking**: Every extraction run tracks `input_tokens` and `output_tokens`. Built-in cost estimation in `llm.py` using published pricing per backend (e.g., Claude Sonnet 4.6: $3/M input, $15/M output; Kimi K2.6: $0.74/M input, $4.66/M output; Gemini 3 Flash: $0.50/M input, $3.00/M output; DeepSeek v4 Flash: $0.14/M input, $0.28/M output; Ollama: free/local).
- **Adaptive retry**: When `finish_reason="length"` or context-window-exceeded error surfaces, the chunk is bisected recursively up to 3 levels deep (max 8x expansion per chunk). Hollow responses (HTTP 200 with empty/null content) from overloaded local models are also re-labeled as truncation and retried.
- **Size caps**: Single-node graph files rejected at 50MB+ (configurable). Office files screened for zip bombs via on-disk cap (50MB), decompressed cap (512MB), and compression ratio (200x).

## 4. Trade-offs

**Wins:**

1. **Zero-shot project onboarding**: Type `/graphify .` and you get three files (graph.html, GRAPH_REPORT.md, graph.json). No configuration, no database, no API key for code-only corpora.
2. **Confidence-tagged edges**: Every relationship is EXTRACTED, INFERRED, or AMBIGUOUS. This is a significant improvement over opaque embedding-similarity approaches -- the user always knows what was found vs guessed.
3. **Local-first for code**: 28 tree-sitter grammars run locally. No API calls for code files. Only docs/PDFs/images need an LLM backend.
4. **Multi-backend LLM**: Supports Gemini, Kimi, Claude, OpenAI, DeepSeek, Ollama, Bedrock, and custom OpenAI-compatible providers. No vendor lock-in.
5. **20+ platform support**: Installs as a skill on every major AI coding assistant, with platform-specific hooks (PreToolUse for Claude Code/Gemini CLI, AGENTS.md for Codex/Aider/OpenClaw, .cursor/rules for Cursor, SKILL.md for Copilot/Kilo/Pi/Devin).
6. **Entity deduplication pipeline**: 3-pass approach (exact normalization -> fuzzy via MinHash/Jaro-Winkler -> optional LLM) with same-community boost and cross-repo guard. Thorough and well-tested.
7. **Progressive-disclosure skill files**: Monolithic SKILL.md was ~1156 lines (always loaded). Now ~615 lines with on-demand references sidecar -- 47% less always-loaded context for every conversation.
8. **PR integration**: `graphify prs` gives a dashboard with CI state, review status, worktree mapping, and graph-community impact analysis including merge-order risk detection via shared communities.
9. **Query-first agent nudging**: Platform hooks fire before grep/search/Read tool calls, nudging the agent toward `graphify query` instead of raw file grepping.

**Losses:**

1. **No persistent storage**: The graph is just JSON files on disk. No built-in vector database, no incremental update at the node level (only file-level via `--update`). Re-running `/graphify .` rebuilds from scratch.
2. **Limited directed-graph support**: Directed graphs are accepted but the pipeline naturally treats edges as undirected for community detection (Louvain/Leiden require undirected input). Direction is preserved in `_src`/`_tgt` attrs but the display functions default to undirected.
3. **Single-root scoping**: The graph is scoped to one directory tree. Cross-project graph merging (`graphify global add/remove`) exists but is a post-hoc operation, not a first-class design pattern.
4. **No streaming / live updates**: `--watch` exists (writes a flag file on change, triggers rebuild) but there is no live-update streaming of graph changes. The post-commit hook rebuilds the full AST graph, not an incremental delta.
5. **Ollama local inference fragility**: Auto-sized KV-cache often exceeds GPU VRAM, requiring manual tuning with `GRAPHIFY_OLLAMA_NUM_CTX`. Hollow responses (HTTP 200 with empty content) from overloaded local models are caught by adaptive retry but the error surface is noisy.
6. **No vector embeddings**: The graph is purely symbolic (nodes + edges + labels). There is no text-embedding similarity layer, so "semantically similar" edges are LLM-generated during extraction, not computed from embeddings.
7. **Community labeling is LLM-dependent**: Community names are generated by an LLM batch call (or by the orchestrating agent). Without an API key, communities stay as `Community 0/1/2...`.
8. **Test limitation**: The test suite includes both `sample.f90` and `sample.F90` fixtures that collide on case-insensitive macOS APFS, requiring Linux or Docker for full Fortran testing.

## 5. Design Rationale

The repo's design philosophy is captured in a few repeated patterns:

1. **"No shared state, no side effects outside graphify-out/"** -- Each pipeline stage is a single function. Communication is through plain dicts and NetworkX graphs. This makes the pipeline testable, composable, and debuggable. The output directory is the only persistent state.

2. **"Pure unit tests -- no network calls, no file system side effects outside tmp_path"** -- The test suite (82 test files across `tests/`) follows strict isolation.

3. **"You always know what was found vs guessed"** -- The EXTRACTED/INFERRED/AMBIGUOUS confidence system runs through every stage of the pipeline. This is the central design choice that distinguishes graphify from black-box embedding approaches.

4. **"Code is extracted locally with no API calls"** -- Tree-sitter AST parsing for 28 languages means a code-only corpus needs zero API keys. LLM backends are only needed for docs, PDFs, images, and video. This is both a privacy guarantee and a cost-control measure.

5. **"Progressive disclosure"** -- The skill files were recently refactored from a monolithic ~1156 lines to a lean ~615-line core with an on-demand references sidecar. The agent only loads the references it needs for the specific operation, keeping the always-loaded context footprint small.

6. **"Fail safe on security"** -- Multiple layers of input validation: URL validation (http/https only, blocks `file://` redirects), file size caps at multiple stages (on-disk, decompressed, compression ratio for zip bombs), Ollama URL validation (block link-local/metadata addresses), label sanitization (control chars stripped, capped at 256 chars, HTML-escaped), provdiders.json protection (project-local providers not loaded without opt-in).

7. **"Atomic installs, crash-safe writes"** -- Skill files are written via `os.replace` (atomic on the same filesystem), references sidecar is staged as `.tmp` then renamed, SKILL.md is the last artifact laid down. An interrupted install never leaves a half-written state visible to the agent.

8. **"Determinism across runs"** -- File traversal is sorted lexicographically to make `os.walk` filesystem-dependent order consistent. Community IDs are assigned by a total order `(-size, sorted node IDs)`. Edge iteration in `build_from_json` is sorted by `(source, target, relation)`. Node ID normalization uses NFKC + casefold.

9. **"Adaptive retry, never silent failure"** -- The LLM extraction layer handles three failure modes (context exceeded, truncation, hollow response) through a single bisection-recurse path. Hollow responses from overloaded local models are re-labeled as truncation so they enter the recovery path. Single-file chunks that exceed context are warned but not retried.

10. **"The confidence tag is the contract"** -- The extraction schema requires `confidence` on every edge. `validate.py` enforces it before `build_graph()` consumes it. This is the most transferable idea: never let an inference be used without communicating its provenance.

## 6. Transfer to Lyra

**One transferable idea**: **Confidence-tagged inference edges** -- Every relationship the system infers carries a tag: `EXTRACTED` (found in source), `INFERRED` (model guess), or `AMBIGUOUS` (uncertain). This maps directly to Lyra's need for source-traceability in its knowledge graph. Lyra's tool-call results and memory entries could be tagged the same way: tool outputs that explicitly state X are `EXTRACTED`; derived facts from context combination are `INFERRED`; contradictory signals are `AMBIGUOUS`. The consumer (another agent, the planner, the user) always knows the provenance.

**Secondary transferable ideas**:
- **Progressive-disclosure skill files** (lean core with on-demand references sidecar) -- Lyra's agent skills and documentation should follow the same pattern: always-loaded instructions stay lean, detailed reference material loads on demand.
- **Pipeline-as-functions pattern** -- Lyra's knowledge-graph construction should follow the same pipeline pattern (detect -> extract -> build -> cluster -> analyze -> report -> export), with each stage a pure function communicating through typed dicts and NetworkX graphs, zero shared state.

**Workstream route**: section 4.3 (Knowledge Graph / Memory Layer). The confidence-tagging system is a direct fit for the Knowledge Graph workstream in the Lyra upgrade plan (section 4.3 of MASTER-PLAN.md). The progressive-disclosure skill pattern maps to section 7 (Plugins) / section 9 (Commands).

**Impact**: 8/10 -- Adds source-traceability to every inferred relationship, which is Lyra's single most important gap vs prior work (MemoRAG, MemGPT). Enables Lyra to distinguish "found in source" from "inferred by model" from "contradictory".

**Effort**: 4/10 -- Adding a `confidence` field to edge metadata is a schema change, not an algorithmic one. The harder part is instrumenting Lyra's existing inference paths to set the right tag. AST parsing (extraction) is done; semantic inference paths (LLM calls, context combination) need the tagging. Implementation: add `confidence` to edge schema, tag existing edges with `INFERRED`, tag tool-returned edges with `EXTRACTED`, surface the breakdown in the graph report and query responses.

**Tier**: A (immediate). Schema-level addition, no new infrastructure, minimum risk.

**LICENSE**: MIT License (Copyright 2026 Safi Shamsi). Fully compatible with Lyra's license.

**Note path**: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/safishamsi__graphify.md`
