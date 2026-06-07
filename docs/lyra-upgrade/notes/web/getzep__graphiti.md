# getzep/graphiti — Deep-Read

**URL:** https://github.com/getzep/graphiti  
**Arxiv:** https://arxiv.org/abs/2501.13956 ("Zep: A Temporal Knowledge Graph Architecture for Agent Memory")  
**Deep-read date:** 2026-06-07  
**Version:** 0.29.2  

---

## 1. Headline Feature & Mechanism

**Graphiti is a framework for building temporal context graphs for AI agents.** Unlike static knowledge graphs (like GraphRAG), Graphiti tracks how facts change over time with bi-temporal validity windows, maintains full provenance to source episodes, and supports both prescribed and learned ontology. Its purpose is to give agents rich structured context instead of flat document chunks or raw chat history.

### Core mechanism — the episode ingestion pipeline

The system works through a continuous, incremental pipeline:

1. **Episodes arrive** — raw data (messages, JSON, text) with a reference time (`valid_at`).
2. **Entity extraction** — LLM extracts entity nodes from episode content. Entities have labels (e.g., "Person", "Product"), summaries that evolve over time, and embeddings.
3. **Edge extraction** — LLM extracts relationship edges (entity-entity triplets) with facts, relation types, and temporal data (`valid_at`, `invalid_at`).
4. **Node deduplication** — extracted nodes are resolved against existing graph. Duplicates are merged via LLM-based semantic comparison.
5. **Edge deduplication** — edges are searched (hybrid semantic+BM25) and resolved. Duplicate edges recycled; contradicting edges invalidated (set `invalid_at` + `expired_at`).
6. **Episodic edges** — MENTIONS edges connect episodes to their extracted entities, preserving provenance.
7. **Community detection** — optional clustering of entity nodes into communities with summary nodes.

### Temporal fact management

Each edge carries a **bi-temporal model**:
- `valid_at` / `invalid_at` — when the fact became/stops being true (event time)
- `created_at` — when the fact was ingested (processing time)
- `expired_at` — when the system determined the fact is no longer valid

When new information contradicts existing facts, old edges are **invalidated** (not deleted) — temporal history is preserved. Queries are time-aware: "what was true at any point in time" vs "what is true now."

### Hybrid search

Search combines up to **four scopes** (edges, nodes, episodes, communities) × **three methods** (BM25 full-text, cosine similarity on embeddings, BFS graph traversal) × **four rerankers** (RRF, MMR, cross-encoder, node-distance). This is configured via `SearchConfig` recipes — the default `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` uses BM25 + cosine similarity + BFS with cross-encoder reranking.

---

## 2. Architecture & Core Modules

### Entry point: `Graphiti` class (`graphiti_core/graphiti.py`)

The main class orchestrates everything:
```python
graphiti = Graphiti(uri, user, password, llm_client=None, embedder=None, 
                    cross_encoder=None, graph_driver=None)
```

Key methods:
- `add_episode()` — single-episode ingestion pipeline (extract → resolve → process → save)
- `add_episode_bulk()` — batch version for multiple episodes
- `search()` / `search_()` — hybrid retrieval with configurable strategies
- `build_communities()` — community detection via clustering
- `summarize_saga()` — incremental saga summarization with dual watermarks

### Module map

```
graphiti_core/
├── graphiti.py              # Main orchestrator
├── graphiti_types.py        # GraphitiClients container (driver+LLM+embedder+cross_encoder)
├── nodes.py                 # Node models: EntityNode, EpisodicNode, CommunityNode, SagaNode
├── edges.py                 # Edge models: EntityEdge, EpisodicEdge, CommunityEdge, HasEpisodeEdge, NextEpisodeEdge
├── driver/                  # Graph database abstraction layer
│   ├── driver.py            # Abstract GraphDriver, GraphProvider enum
│   ├── neo4j_driver.py      # Neo4j 5.26+
│   ├── falkordb_driver.py   # FalkorDB 1.1.2+
│   ├── kuzu_driver.py       # Kuzu 0.11.2+
│   ├── neptune_driver.py    # Amazon Neptune
│   └── operations/          # Per-provider operation modules
├── llm_client/              # LLM provider abstraction
│   ├── openai_client.py     # Default client
│   ├── anthropic_client.py  # Claude support
│   ├── gemini_client.py     # Gemini support
│   ├── groq_client.py       # Groq support
│   ├── openai_generic_client.py  # Ollama / LM Studio
│   └── azure_openai_client.py
├── embedder/                # Embedding providers
├── cross_encoder/           # Re-ranker providers (OpenAI, Gemini, BGE)
├── search/                  # Hybrid search engine
│   ├── search.py            # Main search + 4 scope-specific search funcs
│   ├── search_config.py     # Config models + 4 enums per scope
│   ├── search_config_recipes.py  # 15 pre-built config recipes
│   ├── search_filters.py    # Filter system
│   └── search_utils.py      # Similarity, BFS, full-text, MMR, RRF
├── prompts/                 # Versioned LLM prompts
│   ├── extract_nodes.py     # Entity extraction prompts
│   ├── extract_edges.py     # Edge extraction prompts  
│   ├── dedupe_nodes.py      # Node dedup prompts
│   ├── dedupe_edges.py      # Edge dedup + contradiction prompts
│   ├── summarize_nodes.py   # Node summarization prompts
│   └── summarize_sagas.py   # Saga summarization prompts
├── utils/                   # Maintenance & utilities
│   ├── maintenance/         # Edge/node/community operations, bulk processing
│   └── ontology_utils/      # Entity type validation
├── namespaces/              # Convenience API (graphiti.nodes.save(), etc.)
└── telemetry/               # Anonymous usage stats (PostHog)
```

### Architecture pattern: **Pluggable adapter pattern + Pipeline orchestration**

Graphiti uses three key patterns:
1. **Strategy pattern** for graph backends — four drivers implementing the same abstract interface
2. **Strategy pattern** for LLM providers — five clients with unified `generate_response()`
3. **Pipeline orchestration** — the `add_episode()` method is a sequential pipeline of extract → resolve → save steps, with `semaphore_gather()` for internal parallelism

The driver layer has a newer "operations interface" (`graph_operations_interface`) that provides per-provider implementations of CRUD operations, with fallback to generic Cypher/sparql queries. This allows backends to opt into optimized implementations.

---

## 3. Performance / Benchmarks

### From README — vs GraphRAG comparison:

| Metric | GraphRAG | Graphiti |
|--------|----------|----------|
| Query latency | Seconds to tens of seconds | Typically sub-second |
| Data handling | Batch-oriented | Continuous incremental updates |
| Temporal | Basic timestamp tracking | Explicit bi-temporal with automatic fact invalidation |
| Contradiction | LLM-driven summarization | Automatic invalidation with history preserved |
| Scaling | Moderate | High, optimized for large datasets |

### From paper (arxiv 2501.13956):

Graphiti is described as "State of the Art in Agent Memory" — Zep (the managed service built on Graphiti) demonstrated SotA results on agent memory benchmarks. Specific numbers not published in README but referenced from the Zep blog.

### Evaluation framework (`tests/evals/`):

The repo includes an end-to-end graph building evaluation using the **longmemeval** dataset (oracle variant). The eval:
1. Builds baseline graph with gpt-4.1-mini via `add_episode()` pipeline
2. Builds candidate graph with same data
3. LLM judges per-episode quality: "is candidate worse than baseline?"
4. Score = fraction of episodes where candidate is NOT worse

### Concurrency:

- Default `SEMAPHORE_LIMIT=10` concurrent operations (to avoid 429 rate limits)
- Uses `asyncio.gather` / `semaphore_gather` for concurrent LLM calls, DB queries, embedding generation
- Multiple parallel search strategies execute concurrently before fusion

---

## 4. Trade-offs (Wins vs Losses)

### Wins:

1. **Incremental updates** — no batch recomputation needed. New episodes integrate immediately. This is the key differentiator vs GraphRAG.

2. **Full temporal history** — old facts are invalidated, not deleted. Time-travel queries work. This is critical for agent memory where facts have a shelf life.

3. **Hybrid retrieval** — combining semantic + BM25 + graph traversal + cross-encoder is substantially more robust than any single method. The `SearchConfig` system makes this configurable.

4. **Four graph backends** — Neo4j, FalkorDB, Kuzu, Neptune. Not locked into any single database vendor.

5. **Five LLM providers** — OpenAI, Anthropic, Gemini, Groq, local (Ollama). Plus Azure OpenAI. Structured Output support required for best results.

6. **Versioned prompts** — prompts are versioned and the prompt library supports multiple versions, enabling A/B testing.

7. **Bulk ingestion** — `add_episode_bulk()` parallelizes extraction across episodes, then deduplicates and resolves in batch. Critical for production throughput.

### Losses / Caveats:

1. **LLM-dependent extraction** — entity and edge extraction relies on LLM structured output. Smaller models produce incorrect schemas and ingestion failures (documented in README). This means quality is tied to model capability.

2. **Neo4j-centric default** — Neo4j is the default and best-tested backend. Kuzu requires special handling (edges are nodes), Neptune requires OpenSearch, FalkorDB is newer. The driver interface has "graph_operations_interface" for per-provider optimization, but not all backends implement all operations.

3. **OpenAI default client** — defaults to OpenAI for both LLM and embeddings. To use Anthropic/Gemini/Groq, you must explicitly pass custom clients. This creates a mild vendor lock-in for quick-start users.

4. **Community feature is optional** — `update_communities=False` by default. Building communities requires an additional explicit call. This means community-based retrieval is opt-in and adds latency.

5. **Single-episode sequential constraint** — `add_episode()` must be called sequentially per episode (documented: "each episode must be added sequentially and awaited before adding the next one"). Bulk mode exists but has different internal flow.

6. **Evaluation is LLM-as-judge** — the e2e eval uses LLM to compare baseline vs candidate graph building. This inherits all LLM-as-judge biases (position bias, self-enhancement bias, etc.).

7. **Telemetry is opt-out** — PostHog anonymous usage collection enabled by default. Privacy-conscious deployments must explicitly disable it.

8. **No built-in caching** — The `llm_client/cache.py` exists but is minimal. No embedding cache, no prompt result cache. Each extraction calls the LLM fresh.

---

## 5. Design Rationale

### Why temporal graphs instead of vector-only RAG?

The README's "Why Graphiti?" section is explicit: traditional RAG uses batch processing and static summarization, making it inefficient for frequently changing data. The temporal graph model solves three specific problems:

1. **Staleness problem** — vector stores don't capture "this fact is no longer true." Temporal edges with `invalid_at` do.
2. **Provenance problem** — vector chunks lose source attribution. Episodic edges (MENTIONS) maintain full lineage from derived fact to source episode.
3. **Contradiction problem** — new facts must invalidate old ones. Graphiti's edge deduplication includes contradiction detection: "does this new fact contradict any existing fact?" If yes, the old fact gets `invalid_at` set and `expired_at` timestamped.

### Why hybrid retrieval?

Pure semantic search fails on entity names (embedding collision), temporal queries ("events from March"), and multi-hop relationships. BM25 handles exact keyword matches. Graph traversal handles multi-hop relationships. The reranker stack (RRF → MMR → cross-encoder → node-distance) provides a configurable precision-recall knob.

### Why pluggable backends?

Organizations have entrenched graph database choices. Neo4j is the most popular property graph DB, but FalkorDB offers Redis-compatible deployment, Kuzu offers embedded deployment (no server), and Neptune is required for AWS-native deployments. The abstract driver interface allows each.

### Why LLM-powered extraction?

The "learned ontology" design is a deliberate choice: instead of requiring users to define all entity/edge types upfront (prescribed ontology), the system can also infer structure from data (learned ontology). This reduces setup burden. The trade-off is LLM cost and latency per episode.

### The "Saga" abstraction

Sagas provide a session/topic grouping mechanism on top of episodes. Consecutive episodes in a saga are linked via NEXT_EPISODE edges, and the saga itself gets an incremental summary with dual watermarks:
- `last_summarized_at` (wall-clock) — filter watermark for next run
- `last_summarized_episode_valid_at` (event-time) — temporal watermark for consumers

This design handles the "backfilled episode" problem: episodes added today with `valid_at` in the past are still picked up by the incremental summarizer because the filter uses `created_at` (monotonic), not `valid_at` (which can regress).

---

## 6. Transfer to Lyra

### Transferable idea: Temporal fact graph for agent memory

Graphiti's core innovation — bi-temporal fact tracking with automatic invalidation and provenance — directly addresses Lyra's **stale context** problem. Currently, Lyra's memory system (CraniMem + field-theoretic layer) handles episodic and semantic memory but lacks explicit **factual knowledge graph** capabilities with:
- Entity-relationship extraction from conversations
- Temporal validity tracking ("Kendra loved Adidas shoes as of March 2026")
- Automatic contradiction resolution
- Hybrid retrieval over facts (semantic + keyword + graph)

### How to transfer

Rather than importing Graphiti as a dependency (which would require Neo4j/FalkorDB), Lyra should **adopt the temporal fact graph abstraction**:

1. **Entity/edge extraction pipeline** — re-use Graphiti's prompt patterns for entity and edge extraction from episodes, adapted to Lyra's `llm_client` abstraction.
2. **Bi-temporal edge model** — add `valid_at`/`invalid_at`/`expired_at` fields to Lyra's edge data model. Implement the contradiction detection algorithm from `edge_operations.py`.
3. **Hybrid search strategy** — adopt Graphiti's multi-strategy search pattern (BM25 + embedding + graph traversal) with configurable reranking (RRF -> cross-encoder), but adapt to use Lyra's existing vector store and search infrastructure.
4. **Incremental graph maintenance** — use Graphiti's pattern of per-episode incremental construction (extract -> deduplicate -> merge) instead of batch graph rebuilds.

### Keep: the full pipeline is complex

Graphiti has 15K+ lines of well-tested extraction, deduplication, and resolution code. Lyra should:
- **Reuse the data model** (EntityNode, EntityEdge, EpisodicNode) — these are clean Pydantic models
- **Reuse prompt templates** (extract_nodes, extract_edges, dedupe_edges) — these are battle-tested
- **NOT copy the database drivers** — Lyra has different storage requirements
- **NOT copy the build system** — Lyra uses uv, Graphiti uses hatchling

### Workstream route

| Dimension | Value |
|-----------|-------|
| Lyra workstream | **§4.2 Memory** — specifically, the temporal factual knowledge subgraph within Lyra's memory plane |
| Secondary route | **§4.15 Research** — cross-session fact tracking for research agents |
| Impact | 5 (Breakthrough) — temporal fact graph is the missing piece between Lyra's episodic memory (raw) and semantic memory (abstracted). It provides the intermediate "factual" layer with explicit time-awareness |
| Effort | 5 (Major) — requires adapting extraction prompts, edge model, contradiction logic, and hybrid search. Core pipeline is 3-4 week implementation |
| Tier | (B) Breakthrough — Lyra has episodic and semantic memory but lacks explicit temporal fact tracking. This fills a critical gap in the memory architecture |
| License compatibility | **Apache 2.0** — fully compatible with Lyra's MIT license. No copyleft concerns |
| Note path | `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/getzep__graphiti.md` |
