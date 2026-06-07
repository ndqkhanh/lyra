# garrytan/gbrain -- Deep-Read

## 1. Headline Feature & Mechanism

GBrain is a **personal knowledge brain** built by Y Combinator CEO Garry Tan, designed as the retrieval and memory layer for AI agents. Its headline feature is **synthesis + graph + gap analysis in one box**: where traditional RAG systems return ranked chunks, GBrain returns a well-cited synthesized answer with an explicit statement of what the brain does not know yet.

The core retrieval pipeline is a multi-stage hybrid search:

1. **Vector search** (HNSW on pgvector) for semantic similarity
2. **BM25 keyword search** for lexical matching
3. **Reciprocal Rank Fusion (RRF)** with k=60 to merge both lists
4. **Source-tier boost** to prefer authoritative pages
5. **Intent-aware query rewriting** (three named modes: conservative/balanced/tokenmax)
6. **ZeroEntropy reranker** for final re-scoring (default in tokenmax mode)
7. **Graph signal post-fusion** -- adjacency boost (+1.05x), cross-source boost (+1.10x), and session diversification demote (-0.95x)

The synthesis layer (`gbrain think`) runs a four-retriever parallel gather (hybrid pages, keyword takes, vector takes, graph traversal on an anchor entity), fuses via RRF, then feeds the results into an LLM call that produces a synthesized answer with citations and explicit gap analysis.

The **self-wiring knowledge graph** is the key differentiator: every `put_page` extracts entity references from wikilinks (`[[person/alice]]`) and typed edges (`works_at`, `founded`, `attended`, `invested_in`, `advises`, `mentions`) with **zero LLM calls** -- pure regex and markdown parsing. This enables queries like "who works at Acme AI?" or "what did Bob invest in this quarter?" that vector search alone cannot answer. Benchmarked: **P@5 49.1%, R@5 97.9%** on a 240-page Opus-generated rich-prose corpus, **+31.4 points P@5** over its graph-disabled variant and over ripgrep-BM25 + vector-only RAG.

The **dream cycle** is a 24/7 cron-driven enrichment loop that runs while the user sleeps: deduping people pages, fixing citations, scoring salience, finding contradictions, prepping tomorrow's tasks.

## 2. Architecture & Core Modules

GBrain uses a **contract-first, dual-engine** architecture:

### Entry Points
- **`src/cli.ts`** -- CLI entry point, builds operation lookup from `operations.ts`, dispatches to handlers
- **`src/mcp/server.ts`** -- MCP stdio server, generates 30+ tool definitions from operations, dispatches via `dispatch.ts`
- **`src/mcp/http-transport.ts`** -- HTTP MCP server with OAuth 2.1 + PKCE, admin dashboard at /admin

### Core Data Flow
```
CLI/MCP call → operations.ts (validate params, build OperationContext) → engine method → Postgres/PGLite
```

Every operation in `src/core/operations.ts` (~47 operations as of v0.29) is the single source of truth. Both CLI and MCP server are generated from it. Each operation carries: schema (Zod), handler, scope ('read'|'write'|'admin'), optional `localOnly` flag, and CLI hints.

### BrainEngine Interface (`src/core/engine.ts`)
Defines ~47 operations implemented by both engines:
- **`PGLiteEngine`** (`src/core/pglite-engine.ts`) -- Postgres 17 via WASM, zero-config, for personal brains up to ~50K pages. No Docker required.
- **`PostgresEngine`** (`src/core/postgres-engine.ts`) -- Full Postgres + pgvector for shared/large/multi-machine deployments (Supabase or self-hosted)

Engine factory (`src/core/engine-factory.ts`) uses dynamic imports so PGLite WASM is never loaded for Postgres users.

### Two Organizational Axes
- **Brain** = WHICH DATABASE (personal host, team mounts via `gbrain mounts add`)
- **Source** = WHICH REPO INSIDE THE DATABASE (wiki, gstack, essays, etc.)

Both follow a 6-tier resolution chain: per-call flag -> env var -> per-source DB key -> brain-wide DB key -> gbrain.yml -> ~/.gbrain/config.json -> default.

### Key Modules

| Module | Path | Purpose |
|--------|------|---------|
| Hybrid Search | `src/core/search/hybrid.ts` | Vector + BM25 + RRF + reranker pipeline |
| Think/Synthesis | `src/core/think/` | Gather -> Synthesize -> (optional Commit) pipeline |
| Link Extraction | `src/core/link-extraction.ts` | Zero-LLM entity ref extraction, typed edge creation |
| Minions (Job Queue) | `src/core/minions/` | BullMQ-shaped Postgres-native durable subagent queue with two-phase persistence |
| Schema Packs | `src/core/schema-pack/` | 15-type DRY/MECE taxonomy (gbrain-base-v2), custom pack authoring |
| Dream Cycle | `src/core/cycle/` | 24/7 cron-driven enrichment loop |
| AI Gateway | `src/core/ai/gateway.ts` | Provider-agnostic LLM routing (Anthropic, OpenAI, Google, OpenRouter, etc.) |
| Model Config | `src/core/model-config.ts` | 6-tier model resolution chain |
| Graph Signals | `src/core/search/graph-signals.ts` | Post-fusion adjacency/cross-source/session diversification boosts |
| Eval Framework | `src/core/eval/` | LongMemEval, NamedThingBench, cross-modal eval, contradiction detection |
| Ingestion | `src/core/ingestion/` | Third-party ingestion sources via versioned IngestionSource contract |

### Trust Boundary
`OperationContext.remote` distinguishes trusted local CLI callers (`remote: false`) from untrusted MCP callers (`remote: true`). Security ops like `file_upload` tighten filesystem confinement when `remote=true`.

## 3. Performance/Benchmarks

All numbers from the repo's BrainBench suite:

| Metric | Value | Corpus |
|--------|-------|--------|
| P@5 | 49.1% | 240-page Opus-generated rich-prose corpus |
| R@5 | 97.9% | Same corpus |
| P@5 lift vs graph-disabled variant | +31.4 points | Same corpus |
| P@5 lift vs ripgrep-BM25 + vector-only RAG | Similar margin | Same corpus |

GBrain ships three named search modes that bundle cost/quality knobs:

| Mode | Token Budget | Expansion | Search Limit | Cost (Haiku @10K/mo) | Cost (Sonnet @10K/mo) | Cost (Opus @10K/mo) |
|------|-------------|-----------|-------------|---------------------|---------------------|-------------------|
| conservative | 4K | off | 10 | $40/mo | $120/mo | $200/mo |
| balanced | 12K | off | 25 | $100/mo | $300/mo | $500/mo |
| tokenmax | off | on | 50 | $200/mo | $600/mo | $1,000/mo |

Real-world agent loops with prompt caching see 50-80% discount. Realistic single-power-user volume (~860 turns/mo): tokenmax+Opus ~$700/mo, balanced+Sonnet ~$430/mo.

## 4. Trade-offs

### Wins
- **Zero-LLM knowledge graph edge extraction** saves enormous cost vs LLM-based approaches while delivering +31.4 P@5 lift
- **Dual-engine architecture** (PGLite for local, Postgres for production) means the same codebase serves both personal and team-scale use cases
- **Contract-first design** prevents CLI/MCP drift -- a single `operations.ts` generates both surfaces
- **MCP-native** with OAuth 2.1 + PKCE support, 30+ tools, per-client adapters for Claude Code, Codex, Cursor, ChatGPT, Perplexity
- **Schema pack system** allows custom page types and extraction rules without code changes
- **Comprehensive CI** with 25+ check scripts covering privacy, JSONB patterns, source isolation, test isolation

### Losses
- **PGLite single-writer limitation** -- must stop `gbrain serve` before large sync on PGLite brains; MCP server and sync contend for write lock
- **Bun-only runtime** -- requires Bun >=1.3.10, no Node.js support
- **Supabase/Supavisor pooler fragility** -- batch writes can lose rows on pooler disconnects; requires retry wrappers and JSONL audit trails to self-heal
- **Large brain performance** -- recursive CTE for graph traversal can fan out on hub nodes; frontier cap needed to bound work
- **Tag reconciliation is add-only** -- removing a tag from frontmatter no longer removes it from DB; provenance column deferred to future release
- **Dream cycle link-loss bugs** on Supabase -- historically lost ~150 link rows per run; fixed with self-retry layer and batch retry audit

### Notable Limitations from CHANGELOG
- Reindex with `--markdown` previously wiped auto/dream/signal-detector tags; now add-only (v0.41.37.0)
- Brainstorm `judge_failed: true` with 0 scored ideas was caused by 4K-token output cap truncation (v0.41.21.0)
- Model pricing had drifted across 5 separate tables, causing budget gates to silently not fire on Opus 4.8 (v0.42.25.0)
- Minion workers wedged on Supabase pooler heartbeat drops (v0.42.24.0)

## 5. Design Rationale

GBrain's design is driven by a clear philosophy: **the brain layer is what makes the moat usable**. The key design decisions:

1. **Knowledge graph with zero LLM calls** -- Instead of using expensive LLM calls for entity extraction (typical in RAG systems), GBrain uses pure pattern matching on wikilink syntax `[[dir/entity]]` and typed link syntax. This is not only cheaper but also deterministic and reproducible. The graph enables multi-hop traversal that vector search alone cannot reach.

2. **Contract-first operations** -- Single source `operations.ts` generates CLI and MCP surfaces from one definition, preventing the CLI/MCP drift that plagued earlier versions (e.g., PR #483's reversed-args bug).

3. **Dual engine with dynamic imports** -- PGLite (WASM Postgres) for zero-config local use, Postgres for scale. Dynamic imports ensure PGLite's 2MB WASM binary is never loaded for Postgres-only installations.

4. **Markdown as system of record** -- Knowledge lives as regular markdown files in a git repo. Postgres is the retrieval index, not the source of truth. This enables git-based workflows, public subset publishing, and thin-client setups.

5. **Synthesis with gap analysis** -- The `gbrain think` pipeline doesn't just summarize; it explicitly states what the brain doesn't know yet. This changes how users interact with the system -- they know when to ask external sources rather than assuming a comprehensive answer.

6. **Schema packs over fixed taxonomy** -- Instead of one fixed page-type system, GBrain ships bundled schema packs and lets users author their own. The taxonomies thread through every read+write path, ensuring extraction, routing, and search all respect the same page-type definitions.

7. **Dream cycle for continuous enrichment** -- A 24/7 cron-driven loop that operates while the user sleeps. This is the key insight: it is easier to ship a daemon that runs 24/7 to ingest, enrich, and consolidate than it is to keep an agent in chat working hard.

8. **Minions for durable subagents** -- The job queue (BullMQ-shaped, Postgres-native) provides crash-safe two-phase persistence for subagent execution. This replaces fire-and-forget Promises with something that survives crashes and server restarts.

## 6. Transfer to Lyra

### Transferable Idea: Self-Wiring Knowledge Graph from Page Content

The single most impactful idea for Lyra is GBrain's **zero-LLM knowledge graph construction** from wikilink syntax and typed edge inference. GBrain achieves +31.4 P@5 lift purely through graph-traversal retrieval without spending a cent on LLM entity extraction.

**How it works in GBrain:** Every page write scans for `[[person/alice]]` / `[[company/acme]]` style references and `[Alice](works_at:acme)` typed link syntax. It creates typed edges (`founded`, `works_at`, `invested_in`, `advises`, `attended`, `mentions`) with zero LLM calls. The graph is queried via BFS traversal (`gbrain graph-query`), and results are fused into hybrid search via RRF.

**For Lyra:** Lyra already has a page/entity model. If Lyra adopts a similar wikilink syntax for cross-references (e.g., `[[person/alice-chen]]` in markdown bodies), it can build a typed knowledge graph entirely from deterministic parsing. This enables graph-retrieval routes (people connected to deals, deals connected to companies, etc.) that complement Lyra's existing vector-based retrieval. The key insight is NOT to use an LLM for this -- pure pattern matching is cheaper, deterministic, and auditable.

### Implementation Sketch for Lyra
1. Define a small set of typed edge verbs: `founded`, `works_at`, `invested_in`, `advises`, `attended`, `mentions`, `authored`
2. Parse every page write for `[[type/name]]` wikilinks and typed link syntax
3. Store edges in a simple adjacency table (from_slug, to_slug, link_type, source)
4. Add BFS graph traversal to the retrieval pipeline, fusing graph results with vector results via RRF
5. Use graph signals for post-fusion boosting (similar to GBrain's graph-signals.ts)

### Route

**Lyra Workstream Route: Section 4.3 (Knowledge Representation)**, with ties to 4.5 (Retrieval/Augmentation). This is primarily a knowledge representation change (adding typed edges to Lyra's entity model) that directly improves retrieval quality.

### Assessment

| Dimension | Value |
|-----------|-------|
| **Impact** | 8/10 -- Knowledge graph retrieval is a proven precision lift (+31 P@5). It enables multi-hop questions no LLM-only system handles well. Core differentiator vs other agent memory systems. |
| **Effort** | 5/10 -- Parsing infrastructure (wikilink scanner, typed edge inference), adjacency table schema, graph traversal BFS, RRF fusion in the search pipeline. Moderate. The hard part is the schema pack generalization that GBrain has; a simpler implementation for Lyra could skip that and hardcode a few entity types. |
| **Tier** | 1 -- Directly addresses Lyra's memory/retrieval gap. No dependency on other sections. Can be implemented incrementally: start with simple wikilink detection, add typed edges, then add graph fusion in search. |

### License Compatibility

MIT -- no restrictions. Full freedom to use, modify, and distribute.
