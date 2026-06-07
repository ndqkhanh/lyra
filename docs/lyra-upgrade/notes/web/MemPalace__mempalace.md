# MemPalace/mempalace — Deep-Read

**URL**: https://github.com/MemPalace/mempalace  
**Version**: 3.4.0 (semver, MIT license)  
**Author**: milla-jovovich  
**Language**: Python 3.9+  
**Dependencies**: chromadb (default vector store), huggingface_hub, tokenizers, numpy, python-dateutil, onnxruntime (for embedding)

---

## Top-Level Structure

```
AGENTS.md         assets/            benchmarks/        CHANGELOG.md
CLAUDE.md         CONTRIBUTING.md    docker-compose.yml docker-entrypoint.sh
Dockerfile        Dockerfile.gpu     docs/              examples/
hooks/            integrations/      landing/           LICENSE
mempalace/        MISSION.md         openarena-claim.txt pyproject.toml
README.md         ROADMAP.md         SECURITY.md        tests/
tools/            uv.lock            website/
```

Core package (`mempalace/`):
```
cli.py              mcp_server.py       searcher.py        config.py
miner.py            convo_miner.py      palace.py          palace_graph.py
layers.py           knowledge_graph.py  embedding.py       entity_detector.py
entity_registry.py  dialect.py          normalize.py       repair.py
migrate.py          dedup.py            spellcheck.py      exporter.py
hooks_cli.py        query_sanitizer.py  split_mega_files.py version.py
onboarding.py       corpus_origin.py    llm_client.py      format_miner.py
collision_scan.py   ids.py              hallways.py        sweeper.py
sync.py             instructions_cli.py
backends/
  base.py           chroma.py           pgvector.py        qdrant.py
  sqlite_exact.py   embedding_wrapper.py
i18n/               (locale JSON files)
```

---

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: Local-first AI memory that stores text verbatim and retrieves it with semantic search -- no API key, no summarization, no LLM required for the core pipeline. Achieves 96.6% R@5 on LongMemEval with zero external calls.

**The core mechanism in three steps:**

1. **Ingest (Mine)**: `miner.py` / `convo_miner.py` walk filesystem directories (project files, conversation JSONL transcripts, or binary office docs via MarkItDown). Text is chunked deterministically, embedded with a local ONNX model (either `all-MiniLM-L6-v2` English-only or the newer `embeddinggemma-300m` multilingual), and upserted into a ChromaDB (default) collection. Every chunk is stored with its full verbatim text plus metadata (wing, room, source_file, chunk_index, agent, filed_at). No summarization, no extraction, no paraphrasing -- the contract is "return your exact words."

2. **Structure (Palace)** : The palace is a 3-tier hierarchy: **Wing** (category: person, project, topic) -> **Room** (time-based: day, session, or concept-based) -> **Drawer** (verbatim text chunk). A parallel index layer called **closets** (AAAK compression dialect) stores compact, LLM-scanable pointers to drawers. Hallways (within-wing entity connections) and tunnels (cross-wing entity connections) form a navigation graph. A temporal entity-relationship graph (SQLite-backed `knowledge_graph.py`) tracks facts with validity windows.

3. **Retrieve (Search)** : `searcher.py` implements a hybrid BM25 + vector similarity rank. The vector path (ChromaDB cosine distance) is always the floor; closet hits add a rank-based boost (never a gate). An optional LLM rerank step promotes the best candidate from top-20 results. The **4-layer memory stack** (`layers.py`) provides tiered recall: L0 (identity, ~100 tokens, always loaded), L1 (essential story, ~500-800 tokens, always loaded), L2 (on-demand wing/room filtered, ~200-500 tokens each), L3 (deep search, unlimited).

**Key code paths**:
- Entry: `cli.py:main()` dispatches to subcommands. `mcp_server.py:main()` starts the MCP stdio server.
- Ingest: `cli.cmd_mine()` -> `miner.mine()` or `convo_miner.mine_convos()` or `format_miner.mine_formats()` -> chunk -> embed -> `palace.get_collection()` -> ChromaDB `upsert`.
- Search: `mcp_server.tool_search()` -> `searcher.search_memories()` -> vector query (ChromaDB) + closet query + BM25 rerank + optional LLM rerank.
- Wake-up: `MemoryStack.wake_up()` -> L0 (identity.txt) + L1 (top-15 highest-weight drawers).

---

## 2. Architecture & Core Modules (entry points, data flow, patterns)

### Entry Points
- **`mempalace.cli:main()`** -- Console script for the CLI. Argparse dispatches to `cmd_init`, `cmd_mine`, `cmd_search`, `cmd_wakeup`, etc.
- **`mempalace.mcp_server:main()`** -- Console script for the MCP server. 29 MCP tools (read/write/maintenance) plus knowledge-graph tools and agent diary tools. Stdio transport, JSON-RPC.
- **`mempalace.hooks_cli:run_hook()`** -- Called by Claude Code hooks (Stop, PreCompact, SessionStart) to auto-save conversation state.

### Architecture Pattern
**Layered hexagonal with pluggable backends.**

- **Interface layer** (CLI / MCP / Hooks) surfaces user-facing commands.
- **Domain layer** (`searcher.py`, `miner.py`, `layers.py`, `knowledge_graph.py`, `palace_graph.py`) implements search, ingest, memory hierarchy, entity graph.
- **Storage adapter layer** (`backends/base.py` defines `BaseCollection` and `BaseBackend` ABCs) with implementations: ChromaDB (default), sqlite_exact (local exact vector), Qdrant (REST), pgvector (Postgres). Registered via `pyproject.toml` entry points for third-party plugins.
- **Embedding layer** (`embedding.py`) -- ONNX runtime with pluggable execution providers (CPU, CUDA, CoreML, DirectML).

### Data Flow (Mine -> Search)
```
Filesystem -> miner.py (chunk) -> embedding.py (vectorize) -> backends/chroma.py (store)
                                                           -> knowledge_graph.py (entity triples)
                                                           -> palace_graph.py (hallways/tunnels)

User query -> searcher.py -> backends (vector search)
                          -> searcher._hybrid_rank (BM25 + cosine)
                          -> closets (rank boost)
                          -> optional LLM rerank
                          -> verbatim text returned
```

### Key Patterns
- **Immutable typed results**: `QueryResult` and `GetResult` frozen dataclasses in `backends/base.py` replace ChromaDB's raw dicts.
- **Capability advertising**: Backends declare `supports_namespace_isolation`, `supports_lexical_search`, etc. via `frozenset` capabilities.
- **Deterministic IDs**: Drawer IDs are content hashes, enabling idempotent upserts.
- **Lock-based concurrency**: `mine_lock` and `mine_palace_lock` use PID files with stale-PID timeout and cross-platform liveness checks.
- **Versioned normalization**: `NORMALIZE_VERSION` on drawers triggers automatic rebuild when normalization pipeline changes.
- **Temporal entity graph**: SQLite-backed with `valid_from`/`valid_to` windows, FTS5 full-text search, timeline queries.

---

## 3. Performance/Benchmarks (real numbers from the repo)

All numbers from `benchmarks/BENCHMARKS.md`. Raw JSONL result files committed to the repo. Fully reproducible.

### LongMemEval (500 questions, R@5)
| Mode | R@5 | LLM |
|---|---|---|
| Raw (semantic search, no heuristics) | **96.6%** | None |
| Hybrid v4, held-out 450q | **98.4%** | None |
| Hybrid v4 + Haiku rerank | **100%** | Haiku (~$0.001/q) |
| Hybrid v4 + Sonnet rerank | **100%** | Sonnet (~$0.003/q) |

### LoCoMo (1,986 multi-hop QA pairs)
| Mode | R@10 | LLM |
|---|---|---|
| Session baseline, no rerank | **60.3%** | None |
| Hybrid v5, top-10, no rerank | **88.9%** | None |
| Hybrid v5 + Sonnet rerank, top-50 | **100%** | Sonnet |

### Other Benchmarks
| Benchmark | Score | Notes |
|---|---|---|
| ConvoMem (250 items) | **92.9%** avg recall across 5 categories |
| MemBench (ACL 2025, 8,500 items) | **80.3%** R@5 overall |
| MemBench noisy category | **43.4%** R@5 | Weakest -- distractors mixed in |

### Performance Budgets
- Hooks under 500ms target. Startup injection under 100ms.
- L0+L1 wake-up: ~600-900 tokens. Leaves 95%+ of context free.
- Embedding model: ~300 MB disk (embeddinggemma) or ~30 MB (MiniLM). lazy-downloaded on first use.
- LoCoMo 100% caveat: top-k=50 exceeds session count per conversation, so the rerank bypasses retrieval. Honest number is 88.9% R@10 at top-10.

---

## 4. Trade-offs (wins vs loses -- from issues, design decisions, complexity)

### Wins
- **Zero-API baseline**: 96.6% LongMemEval R@5 with no API key, no cloud, no LLM. This is the project's central finding: the field is over-engineering memory extraction. Raw verbatim text with good embeddings beats systems that use LLMs to extract structured facts.
- **Privacy by architecture**: Data never leaves the machine by default. No telemetry, no phone-home, no external service dependencies for core operations.
- **Pluggable backends**: ChromaDB default, but Qdrant, pgvector, and sqlite_exact all implement the same contract. Third-party backends can register via entry points.
- **Idempotent ingest**: Deterministic drawer IDs (content hash + chunk index) mean re-mining is safe -- existing drawers are upserted, never duplicated.
- **Comprehensive error recovery**: `repair` command with multiple modes (legacy, max-seq-id, from-sqlite). HNSW quarantine, stale-PID reclamation, FTS5 integrity validation, SQLite integrity preflight.

### Losses / Known Limitations
- **Teaching to the test**: The final 0.6% improvement (96.6% -> 100%) was three targeted fixes for three specific wrong answers. The authors openly disclose this in BENCHMARKS.md as a methodological caveat. The honest generalizable figure is 98.4% R@5 on held-out 450 questions.
- **LoCoMo 100% structurally inflated**: top-k=50 exceeds session count, making the rerank essentially reading comprehension. Honest LoCoMo number is 88.9% R@10 at top-10.
- **Noisy category weakness**: MemBench noisy category at 43.4% R@5 -- deliberate distractors still fool the system. This is acknowledged as the designed hard case for verbatim storage.
- **ChromaDB coupling**: Despite pluggable backends, repair, migrate, and several maintenance paths are Chroma-only. Non-Chroma backends get less tooling.
- **HNSW reliability**: ChromaDB's HNSW segment issues (link_lists.bin bloat, stale PIDs, max_seq_id corruption) required extensive workarounds including `quarantine_stale_hnsw`, `repair --mode from-sqlite`, and per-call HNSW capacity probes.
- **Multilingual ONNX model is 300 MB**: Though lazy-downloaded, this is a significant first-use barrier. Backward-compat with MiniLM is maintained but switching requires re-embedding the entire palace.
- **Windows issues**: Hook subprocess deadlock, ANSI codepage mojibake, ONNX bad_alloc, file-lock lifecycle -- all required specific fixes documented in CHANGELOG.
- **Startup latency**: ONNX model load on first query can be slow. MCP cold-start diagnostics and opt-in warmup were added to address visibility (issue #1495).

---

## 5. Design Rationale (why this approach)

From CLAUDE.md, MISSION.md, ARCHITECTURE-DEBATE.md, and code comments:

**"Verbatim always" is the foundational promise.** Never summarize, never paraphrase, never lossy-compress user data. The system searches the index and returns the original words. This is a deliberate rejection of the Mem0/Mastra approach (LLM extracts facts, discards context). The 96.6% LongMemEval result validates the bet: raw text with embeddings is a stronger baseline than anyone realized because it doesn't lose information.

**Incremental-only ingest.** Append-only after initial build. Never destroy existing data to rebuild. A crash mid-operation must leave the existing palace untouched. This drives the deterministic-ID + upsert pattern, the PID-file locking, and the careful backup-before-repair in `cmd_repair`.

**Entity-first architecture.** Everything is keyed by real names with disambiguation. People matter more than topics. The entity detection pipeline runs multiple passes: manifest scanning (package.json, pyproject.toml for project names), git author extraction (for people names), regex-based prose detection (with i18n support for 14+ languages), and optional LLM refinement.

**Local-first, zero external API by default.** All extraction, chunking, embedding, and LLM-assisted refinement happens on the user's machine. External providers (Anthropic, OpenAI, Google) are supported via BYOK but never required and never enabled silently. The system physically cannot send your data because it never leaves your machine.

**Background everything.** Filing, indexing, timestamps, and pipeline work happen via hooks. Nothing interrupts the user's conversation. Zero tokens spent on bookkeeping in the chat window. This was a hard-learned lesson from v3 where hooks fired in the chat window, consuming tokens and user attention.

**Palace as memory palace + Zettelkasten.** The architectural metaphor (wings, rooms, drawers) comes from the ancient method of loci. The cross-referencing (hallways, tunnels, closets) is inspired by Luhmann's Zettelkasten. The AAAK compression dialect creates LLM-scanable index cards pointing to verbatim drawers.

---

## 6. Transfer to Lyra (one idea + workstream route + Impact/Effort/Tier + LICENSE)

### Transferable Idea: The 4-Layer Memory Stack (L0-L3)

MemPalace's `layers.py` implements a tiered recall architecture that decides **what to pre-load vs. what to fetch on-demand**:

- **L0 (Identity)** : ~100 tokens, always loaded. "Who am I?" -- agent identity, traits, key people, core project.
- **L1 (Essential Story)** : ~500-800 tokens, always loaded. Auto-generated from highest-weight/recent memories. Top moments from the palace.
- **L2 (On-Demand)** : ~200-500 tokens per retrieval. Loaded when a topic or wing comes up in conversation. Wing/room filtered.
- **L3 (Deep Search)** : Unlimited. Full semantic search against the entire store.

Total wake-up cost: ~600-900 tokens (L0+L1), leaving 95%+ of context free for the actual conversation.

**How this maps to Lyra**: Lyra's context management system currently lacks a tiered loading strategy. MemPalace provides a production-validated pattern for:
1. Pre-loading agent identity and essential context on every turn (L0/L1 analog).
2. Loading project-specific context on demand via wing/room routing (L2 analog).
3. Fallback to full semantic search when on-demand misses (L3 analog).
4. Automatic compaction of L1 from the most salient stored memories.

### Workstream Route
Map to **Section 4.x -- Context Management Workstream** (specifically, the context-windowing / memory-retrieval subsection). The 4-layer stack is a drop-in architectural pattern for Lyra's `context.py` / `memory.py` modules.

### Assessment
- **Impact**: 7/10 (Medium-High). A tiered memory stack would solve Lyra's context-pressure problem for multi-session agent persistence. The L0 identity concept maps directly to Lyra's agent persona system. The L1 essential-story generation could replace the current flat context reload.
- **Effort**: 6/10 (Medium). Requires: (1) implementing local embedding and vector storage (or wrapping an existing one), (2) building the L0-L3 retrieval hierarchy, (3) integrating with Lyra's existing memory subsystem, (4) tuning the L1 generation for Lyra's domain.
- **Tier**: Tier 2 (recommended for v2.0). The 4-layer approach is already validated in production (MemPalace 3.4.0) and solves a well-understood problem. It does not require fundamental research, just careful integration.

### LICENSE
MIT -- compatible with Lyra's licensing. Full attribution required per the MIT terms (Copyright (c) 2026 MemPalace Contributors).
