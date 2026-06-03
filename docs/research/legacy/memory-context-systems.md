# AGI-Level Memory Architecture: Cross-Repository Analysis

> Research completed: 2026-05-25 | Sources: 7 repos deep-analyzed

## Repositories Analyzed

| Repo | Language | License | Focus |
|------|----------|---------|-------|
| Graphify | Python | MIT | Knowledge graph extraction |
| TencentDB-Agent-Memory | TypeScript | MIT | 4-tier progressive memory pyramid |
| Acontext | JS/TS/Go/Python | Apache 2.0 | Skills as memory primitive |
| CodeGraph | TypeScript | - | Pre-indexed semantic knowledge graph |
| claude-mem | TypeScript | Apache 2.0 | Event-driven 3-layer memory |
| MemPalace | Python | MIT | Palace metaphor + 4 memory layers |
| abtop | Rust | MIT | Multi-agent TUI monitor |

---

## Top 10 Most Impactful Innovations

### 1. Symbolic Short-Term Memory (TencentDB-Agent-Memory)

Compressing verbatim tool logs into Mermaid syntax with `node_id` drill-down replaces flat context accumulation. **-61% tokens with +51% task success on WideSearch.** Symbolization preserves auditability unlike summarization.

| Benchmark | Token Reduction | Task Success Improvement |
|---|---|---|
| WideSearch | -61.38% (221M → 85M) | +51.52% (33% → 50%) |
| SWE-bench (50 tasks) | -33.09% (3474M → 2375M) | +9.93% (58.4% → 64.2%) |
| AA-LCR | -30.98% (112M → 77M) | +7.95% (44.0% → 47.5%) |
| PersonaMem | N/A | +59% (48% → 76%) |

### 2. Pre-Indexing as Agent Optimization (CodeGraph)

Shifting from discovery-at-query-time to discovery-at-index-time. Agents spend disproportionate budget on *discovery* (finding code), not *analysis* (reading it). **~71% fewer tool calls, ~35% fewer tokens, ~46% less wall-clock time.**

### 3. Verbatim-First Philosophy (MemPalace)

Store everything verbatim, retrieve via semantic search. **96.6% R@5 with zero LLM calls.** Compression is not always necessary and can introduce loss.

### 4. Progressive Disclosure Pyramid (TencentDB-Agent-Memory, claude-mem)

L0-L3 layering with clear token budgets per layer. Agent attends to top layer, drills down via `node_id` only when needed. claude-mem's 3-step workflow (search → timeline → fetch) achieves **~10x token savings**.

### 5. Skills as Memory Primitive (Acontext)

Opaque vector embeddings replaced with version-controllable Markdown skill files. Memory becomes inspectable, editable, shareable, framework-agnostic. No embedding costs. Skill-memory equivalence: downloaded and self-learned memory are identical.

### 6. Confidence-Tagged Knowledge Graphs (Graphify)

Three-tier relationship labeling: EXTRACTED (direct AST evidence), INFERRED (heuristic resolution), AMBIGUOUS (flagged for review). Design rationale extraction (`# NOTE:`, `# WHY:`, `# HACK:`) preserves developer intent as first-class graph nodes.

### 7. Temporal Knowledge Graph (MemPalace)

Time-bounded entity relationships with `valid_from`/`valid_to` windows, inverted interval rejection, timeline queries, and invalidation. All local via SQLite WAL.

### 8. Watermark-Based Incremental Sync (claude-mem)

Per-doc-type watermarks with non-contiguous failure guard. Only confirmed writes advance watermarks. Atomic file operations. Backfill pipeline with concurrency limits.

### 9. Dual-Layer Heterogeneous Storage (TencentDB-Agent-Memory)

Database for bottom-layer evidence (robust retrieval), human-readable Markdown for top-layer structure (white-box inspectable). Deterministic traceability: Persona → Scenario → Atom → Conversation.

### 10. Adaptive Extraction Cadence (TencentDB-Agent-Memory)

Warm-up mode: extraction frequency doubles with session maturity (1→2→4→... turns between triggers). Idle timeout triggers extraction after user inactivity.

---

## Architectural Patterns

| Pattern | Leader | Why It Matters |
|----------|--------|----------------|
| Ports-and-adapters memory core | TencentDB-Agent-Memory | Same memory engine runs across OpenClaw, Hermes Gateway, and standalone |
| MCP as universal protocol | CodeGraph, MemPalace, claude-mem | Any MCP-compatible agent can use the memory system |
| Multi-agent isolation | MemPalace | Each agent gets own wing + diary, avoiding prompt contamination |
| Git-aware graph merge | Graphify | Union-merging graphs on parallel commits for team-scale KM |
| LLM-optional retrieval | MemPalace | 96.6% R@5 with no LLM; works without API costs |
| Schema-driven memory | Acontext | Users define memory structure, not the system |
| Multi-agent unified dashboard | abtop | Monitor Claude Code, Codex, OpenCode simultaneously |

---

## Detailed Analysis Per Repository

### Graphify (safishamsi/graphify)

Knowledge graph extraction pipeline: detect → extract → build_graph → cluster → analyze → report → export.

- 19 Python modules, 14 tree-sitter extractors
- SHA256 content-addressable caching per file
- Leiden community detection (graspologic)
- 7 relationship types: contains, method, inherits, imports, imports_from, calls, uses
- God nodes + surprising connections detection
- Global cross-project graph via `graphify global` → `~/.graphify/global.json`
- Git merge driver for union-merging `graph.json`
- PR impact analysis with community-aware conflict detection

### TencentDB-Agent-Memory (Tencent/TencentDB-Agent-Memory)

4-tier progressive pyramid with dual-layer heterogeneous storage.

**Short-Term Context Layering:**
| Layer | Content | Purpose |
|-------|---------|---------|
| Bottom | Raw tool outputs (`refs/*.md`) | Archival evidence |
| Middle | Step-level summaries (JSONL) | Extracted structure |
| Top | Mermaid state canvas | Lightweight in-context (~few hundred tokens) |

**Long-Term Personalization:** L0 Conversation → L1 Atom → L2 Scenario → L3 Persona

**Compression Triggers:**
- `mildOffloadRatio`: 0.5 (50% context window)
- `aggressiveCompressRatio`: 0.85 (85% context window)
- `mmdMaxTokenRatio`: 0.2 (Mermaid token budget ceiling)

**Extraction Cadence:** `pipeline.everyNConversations: 5`, warm-up doubling (1→2→4→...), idle timeout (600s), L2 min interval (900s)

**Recall:** BM25 keyword, embedding vector, RRF hybrid fusion

### Acontext (memodb-io/Acontext)

**Philosophy:** "Skill is Memory, Memory is Skill."

Store Pipeline: Session messages → Task outcome detection → Distillation (LLM pass) → Skill Agent (routing decision) → Update Skills (SKILL.md)

Recall: Agents use `get_skill` and `get_skill_file` tools — no embedding search, no semantic top-k.

- Skills persist as Markdown files in structured directory
- Download as ZIP, no vendor lock-in
- Schema-driven: users define SKILL.md structure
- Mountable skills for isolated execution environments

### CodeGraph (colbymchenry/codegraph)

Pre-indexed semantic knowledge graph via MCP protocol.

- 22 node kinds, 12 edge kinds, 26 languages
- SQLite FTS5 + tree-sitter AST parsing
- 14 web framework-aware route detection
- Dynamic dispatch tracing (callbacks, re-renders, interface→impl hops)
- `.gitignore` as sole configuration
- `affected` command for selective CI

### claude-mem (thedotmack/claude-mem)

Event-driven 3-layer memory with 5 lifecycle hooks.

**3-Layer Retrieval Workflow:**
| Layer | Tool | Token Cost |
|-------|------|------------|
| 1 | search → compact index | ~50-100 tokens/result |
| 2 | timeline → context | Variable |
| 3 | get_observations → full details | ~500-1000 tokens/result |

- SQLite (8 tables) + Chroma vector DB + PostgreSQL backend
- ChromaSync: watermark-based incremental sync
- ContextBuilder: 7-section context injection
- 21 MCP tools, multi-agent plugin architecture
- Language-aware mode system: `CLAUDE_MEM_MODE` with ISO 639-1 localization

### MemPalace (MemPalace/mempalace)

Palace metaphor with 4 memory layers.

**Spatial Hierarchy:** Wings (people/projects) → Rooms (topics) → Drawers (verbatim content)

**4-Layer Stack:**
| Layer | Name | Token Cost | Always Loaded? |
|-------|------|------------|-----------------|
| L0 | Identity | ~100 | Yes |
| L1 | Essential Story | ~500-800 | Yes |
| L2 | On-Demand | ~200-500 | No (triggered) |
| L3 | Deep Search | Unlimited | No (triggered) |

- Wake-up cost: ~600-900 tokens (95%+ of context free)
- Closet boost mechanism: rank-based boost [0.40, 0.25, 0.15, 0.08, 0.04]
- Matryoshka dimensionality reduction: first 384 dims of 768-dim EmbeddingGemma
- ONNX quantization (q8) for local inference
- BM25-only fallback reads ChromaDB SQLite FTS5 directly
- 29 MCP tools

### abtop (graykode/abtop)

Read-only TUI monitor for AI coding agent sessions.

- Monitors Claude Code, Codex CLI, OpenCode simultaneously
- Context window gauges with compaction detection
- Subagent tree views
- Orphan port detection + cleanup
- tmux session jumping
- 12 themes including 4 colorblind-friendly

Sources:
- [Graphify](https://github.com/safishamsi/graphify)
- [TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory)
- [Acontext](https://github.com/memodb-io/Acontext)
- [CodeGraph](https://github.com/colbymchenry/codegraph)
- [claude-mem](https://github.com/thedotmack/claude-mem)
- [MemPalace](https://github.com/MemPalace/mempalace)
- [abtop](https://github.com/graykode/abtop)
