# Research Engine -- Learning Path

> **Phase:** 2 | **Composes blocks:** Agent Loop, Context Engine, Memory (Three-Tier), Verifier Cross-Channel, MCP Adapter | **Architecture docs:** [research-engine-architecture.md](../../architecture/research-engine-architecture.md), [RESEARCH-ENGINE-V2.md](../../architecture/RESEARCH-ENGINE-V2.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- multi-hop deep research with iterative query refinement (3-5 hops), knowledge graph construction (500+ nodes), source credibility scoring (5 dimensions), evidence synthesis with contradiction detection |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | 5 research strategies (breadth-first, depth-first, iterative refinement, comparative, exploratory), knowledge graph structure (query/concept/reference nodes), evidence aggregation pipeline, storage architecture (SQLite + NetworkX + sentence-transformers) |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Multi-hop engine pipeline (query -> retrieve -> score -> extract -> build -> evaluate -> refine), source retrieval providers (arXiv, GitHub, web, academic DBs, docs), credibility scoring algorithm, citation traversal |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Hop count vs cost trade-off, breadth-first vs depth-first strategy selection, cache invalidation strategies, graph merge semantics |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | Per-hop latency (3-4s), multi-hop research time (20-25s for 3-4 hops), 55% cache hit rate, knowledge graph construction time |

## In 30 Seconds

The Research Engine is Lyra's autonomous deep research system that iteratively refines queries across 3-5 research hops, retrieves from multiple sources (arXiv, GitHub, web, academic DBs), scores source credibility on 5 dimensions (authority, recency, citations, methodology, relevance), builds entity-relationship knowledge graphs using NetworkX, and synthesizes evidence with full citation provenance. Results persist across sessions via the memory system (episodic + semantic). Cache hit rate targets 60%+.

## What This System Composes

| Block | Role |
|-------|------|
| [Agent Loop](../../blocks/agent-loop/) | Turn-by-turn execution of each research hop |
| [Context Engine](../../blocks/06-context-engine.md) | Research context assembly and hop-by-hop state management |
| [Memory (Three-Tier)](../../blocks/memory/) | Episodic (session history), semantic (knowledge graph), working (active research context) |
| [Verifier Cross-Channel](../../blocks/11-verifier-cross-channel.md) | Cross-source claim verification and contradiction detection |
| [MCP Adapter](../../blocks/mcp-adapter/) | External tool integration (web fetch, academic APIs, code search) |

## Quick Reference

- **When you need this:** Autonomous multi-source research, literature reviews, evidence-based report generation, knowledge graph construction from search
- **Related architecture docs:** [research-engine-architecture.md](../../architecture/research-engine-architecture.md), [RESEARCH-ENGINE-V2.md](../../architecture/RESEARCH-ENGINE-V2.md)
- **Upgrade plan:** [15-deep-research.md](../../lyra-upgrade/plans/15-deep-research.md)
- **Concept doc:** [reasoning-bank.md](../../concepts/reasoning-bank.md)
- **Key packages:** `packages/lyra-research/` (multi-hop engine, knowledge graph, synthesis)

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
