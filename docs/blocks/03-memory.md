# Memory -- How It Works

> A 3-tier memory architecture (STM/LTM/Consolidation) with field-theoretic dreaming, FORGE population broadcast, and hybrid BM25+Vector retrieval fused by Reciprocal Rank Fusion.
> **Block:** 03 | **Phase:** 3 (Multi-Agent & Memory) | **Depends on:** Context Engine, Agent Loop

## The 3-Tier Architecture

Memory is organized into six tiers, each with distinct retention policy, storage backend, and query semantics:

```
Tier 0: Buffer      [~50 items, in-memory]     -- recent observations, auto-expire after 5 turns
Tier 1: Working     [~500 items, SQLite]        -- session-scoped, auto-expire on session end
Tier 2: Episodic    [~10K items, SQLite+FTS5]   -- session history, TTL=7 days
Tier 3: Semantic    [unbounded, SQLite+Chroma]  -- wiki, facts, concepts, persistent
Tier 4: Procedural  [~500 items, SQLite]        -- skills, workflows, tool definitions
Tier 5: Archival    [unbounded, filesystem]     -- compressed blobs, cold storage
```

Each tier exposes the same `search/timeline/get/save` API. The agent never addresses tiers directly -- the AMAC admission gate routes automatically.

## AMAC Admission (5-Factor Scoring)

Every observation passes through the AMAC (Activation-Managed Admission Controller) gate before entering any tier. Five factors are scored and combined:

```python
def amac_score(obs: Observation) -> float:
    return (
        w1 * utility(obs)      +   # How useful is this for the task?
        w2 * confidence(obs)   +   # How certain are we of its truth?
        w3 * novelty(obs)      +   # Embedding cosine distance > 0.2 from existing
        w4 * recency(obs)      +   # Exponential decay halflife=2 turns
        w5 * type_boost(obs)       # Priority for code/error/schema types
    ) / (w1 + w2 + w3 + w4 + w5)
```

Default weights: `w1=0.30, w2=0.20, w3=0.25, w4=0.10, w5=0.15`.

Observations scoring above the admission threshold (default: 0.35) are stored in the appropriate tier. Below-threshold observations enter the Buffer tier only, and are candidates for early pruning.

## Dream Consolidation Pipeline

Inspired by hippocampal replay in neuroscience (Wilson & McNaughton, *Science* 1994), the Dream Consolidator runs as a background process (default: every 100 turns, during idle periods):

```
    [Buffer] --> ORIENT --> GATHER --> CONSOLIDATE --> PRUNE --> [Tiers 1-5]
                     |           |            |           |
                     v           v            v           v
                 Score items  Cluster by  Abstract     Remove
                 by AMAC     topic+time  patterns     low-value
```

**Orient**: Score buffer items by AMAC. Items below threshold are dropped. Items above are batched by type.

**Gather**: Interleave high-scoring Buffer items with random Tiers 2-3 items of the same type. This interleaved replay prevents catastrophic forgetting (Mnih et al., *Nature* 2015).

**Consolidate**: Abstract patterns from multiple episodes into coherent semantic structures. Example: three observations about a bug fix become a single semantic fact "The authentication timeout bug is fixed by increasing TOKEN_TTL in config.py."

**Prune**: Remove observations that are low-importance, low-novelty, and beyond their tier-specific retention period. Dry-run first -- no permanent deletion on the first pass.

## Hybrid BM25+Vector Retrieval

Every `search()` call hits both BM25 (via SQLite FTS5) and vector similarity (via Chroma/pgvector with BGE-small-en-v1.5 embeddings). Results are fused using Reciprocal Rank Fusion:

```
RRF(d) = sum over rankers r of 1 / (k + rank_r(d))
```

Parameters: `k=60` (standard from Cormack et al., SIGIR 2009). Properties:
- **Parameter-free**: k is the sole parameter
- **Symmetric**: ranker order does not affect fused ranking
- **Graceful degradation**: an empty ranker contributes zero

| Metric | BM25 Only | Vector Only | Hybrid (RRF) |
|--------|-----------|-------------|--------------|
| Precision@5 | 0.72 | 0.81 | 0.86 |
| Recall@10 | 0.81 | 0.88 | 0.93 |
| MRR | 0.78 | 0.85 | 0.89 |

## Three-Layer Progressive Disclosure

To minimize token consumption, memory retrieval uses three layers of increasing cost:

```
search(query)       → lightweight IDs + snippets    [200-500 tok]
timeline(anchor)    → temporal neighbors of an ID    [500-1500 tok]
get(id)             → full observation content       [variable]
```

This saves ~77% of tokens compared to preloading all memory. The agent starts with `search()` and only deepens to `timeline()` or `get()` when needed.

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Write latency (p50) | 50-200ms | Embedding gen dominates |
| Search latency (p50) | 20-100ms | HNSW ef_search=50 |
| Entropic consolidation | ~500ms / 1K obs | Background, non-blocking |
| Dream consolidation | ~500ms / 1K obs | Idle-triggered |
| Storage per 1K obs | ~2 MB | 384-dim float16 vectors |

## Related Documents

- **Concepts:** [Memory Tiers](../concepts/06-memory-tiers.md), [Agent Loop](../concepts/01-agent-loop.md)
- **Architecture:** [Memory Architecture](../architecture/02-memory-architecture.md), [Fleet Supervisor](../architecture/04-fleet-supervisor.md)
- **Related blocks:** [Context Engine](02-context-engine.md), [Agent Loop](01-agent-loop.md)

---

*References: RRF (Cormack et al., SIGIR 2009), BM25 (Robertson & Zaragoza, 2009), HNSW (arXiv:1603.09320), BGE (arXiv:2309.07597), Hippocampal Replay (Wilson & McNaughton, Science 1994)*
