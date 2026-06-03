# Memory Consolidation: Dream-Style 4-Phase Architecture

> **Inspiration:** Claude Code "Dream" system, [Mem0](https://github.com/mem0ai/mem0) (91.6 LoCoMo, 93.4 LongMemEval), [TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory)
> **Status:** Phase 13.1 — Foundation (Weeks 1-2)

## Overview

Lyra's memory system goes beyond simple storage and retrieval. The **Dream Consolidator** is a background process that runs after each session, transforming raw conversation traces into structured, linked, deduplicated knowledge that improves over time.

## The Problem with Flat Memory

Traditional agent memory is append-only — each conversation just adds more entries. This leads to:

1. **Knowledge fragmentation** — Related facts scattered across sessions with no links
2. **Stale information** — Outdated facts never pruned, cluttering retrieval
3. **No synthesis** — Raw conversations stored verbatim, no extraction of principles
4. **Retrieval degradation** — More entries = noisier retrieval results over time

## Dream 4-Phase Consolidation

```
Session End
    │
    ▼
┌─────────────────────────────────────────────┐
│  PHASE 1: ORIENT                            │
│  • Scan session traces for new knowledge    │
│  • Classify: fact / pattern / skill / lesson│
│  • Score novelty vs existing memories       │
│  • Schedule consolidation priority          │
└──────────────────┬──────────────────────────┘
                   │ Candidate memories
                   ▼
┌─────────────────────────────────────────────┐
│  PHASE 2: GATHER                            │
│  • Retrieve related memories across layers  │
│  • Semantic similarity clustering           │
│  • Temporal context anchoring               │
│  • Cross-session entity resolution          │
└──────────────────┬──────────────────────────┘
                   │ Clustered context
                   ▼
┌─────────────────────────────────────────────┐
│  PHASE 3: CONSOLIDATE                       │
│  • ADD-only extraction (never overwrite)    │
│  • Entity linking across memory layers      │
│  • Deduplication with semantic merge        │
│  • Principle extraction from patterns       │
│  • Confidence scoring per extracted memory  │
└──────────────────┬──────────────────────────┘
                   │ Enriched memories
                   ▼
┌─────────────────────────────────────────────┐
│  PHASE 4: PRUNE                             │
│  • Ebbinghaus forgetting curve simulation   │
│  • Staleness scoring (last access, age)     │
│  • Redundancy detection (near-duplicates)   │
│  • TTL-based expiration per memory type     │
│  • Archival (compress, don't delete)        │
└─────────────────────────────────────────────┘
                   │
                   ▼
            Updated Memory Store
```

### Phase 1: Orient — Identify What's New

The Orient phase scans the just-completed session's HIR trace and identifies candidate knowledge:

- **Facts:** Specific findings, configurations, decisions ("Redis connection string is at `REDIS_URL`")
- **Patterns:** Repeated successful/failed strategies ("always run migrations before schema changes")
- **Skills:** Reusable procedural knowledge extracted via Trace2Skill
- **Lessons:** What worked, what failed, and why (ReasoningBank-compatible format)

Each candidate receives a **novelty score** (0-1) against existing memories to avoid re-storing known information.

### Phase 2: Gather — Build Context

For each high-novelty candidate, the Gather phase collects related memories:

- **Semantic neighbors** — Vector similarity search across all memory layers
- **Temporal context** — Memories from the same time period or related sessions
- **Entity links** — Same files, same functions, same error types
- **Causal chains** — What led to this knowledge? What did it lead to?

This clustering ensures consolidation has full context, not isolated snippets.

### Phase 3: Consolidate — ADD-Only Extraction

The core innovation. Consolidation follows an **ADD-only** policy inspired by Mem0:

- **Never overwrite** existing memories — always add new, enriched versions
- **Entity resolution** — Link mentions of the same entity across layers (e.g., "Redis" in semantic memory ↔ Redis connection in procedural memory)
- **Deduplication** — When two memories express the same fact, merge them with combined confidence and dual provenance
- **Principle extraction** — When 3+ related facts form a pattern, extract a higher-level principle
- **Confidence scoring** — Each consolidated memory receives a confidence score based on repetition, source reliability, and verification status

**ADD-only rationale:** Overwriting memories risks losing context. If a "fact" changes (e.g., Redis URL migrates), the old fact remains with a `superseded_by` link to the new one — preserving the full evolution trail.

### Phase 4: Prune — Ebbinghaus Forgetting

Not all memories should persist forever. The Prune phase applies:

- **Ebbinghaus forgetting curve** — Memory strength decays exponentially without reinforcement. Each access "boosts" the curve
- **Staleness scoring** — `score = last_access_age * (1 / access_count) * memory_type_weight`
- **TTL per type**:
  - Sensory: 1 session
  - Episodic: 7 days
  - Semantic: 30 days (then archive)
  - Procedural: 90 days (unless skill is actively used)
  - Strategic: Until goal completion
  - Meta: 180 days
  - Collective: Permanent (gossip-verified)
  - Eternal: Permanent
- **Archival, not deletion** — Pruned memories are compressed and archived for 1 year before permanent deletion

## Multi-Signal Retrieval

Dream consolidation enables **multi-signal retrieval** — memories are indexed by multiple signals:

| Signal | Description | Example Query |
|--------|-------------|---------------|
| **Semantic** | Vector embedding similarity | "How do we handle auth?" |
| **Keyword** | BM25 text matching | "Redis connection timeout" |
| **Entity** | Named entity linking | All memories about `UserService` |
| **Temporal** | Time-based retrieval | "What did we change last week?" |
| **Causal** | What led to what | "Why did we add the cache layer?" |
| **Procedural** | Skill/pattern matching | "How do we deploy?" |

Retrieval uses **RRF (Reciprocal Rank Fusion)** to merge results from all signals, with **verbatim-first** ranking (inspired by MemPalace) — exact matches rank above semantic matches.

## Memory Type Lifecycle

```
Sensory (500 tokens, 1 session)
    │ Consolidation (every 10 turns)
    ▼
Working / Episodic (2K tokens, 7 days)
    │ Dream Consolidation (session end)
    ▼
Semantic (JSON indexed, 30 days)
    │ Pattern extraction
    ▼
Procedural (Skills, 90 days)
    │ Meta-learning
    ▼
Meta (Learning traces, 180 days)
    │ Fleet aggregation
    ▼
Collective (Fleet knowledge, permanent)
    │ Eternal persistence
    ▼
Eternal (Cross-session, never expires)
```

## Implementation Reference

- **Primary module:** `lyra_memory/dream_consolidator.py` — 4-phase consolidation engine
- **ADD-only extraction:** `lyra_memory/add_extractor.py` — Safe memory addition
- **Entity linker:** `lyra_memory/entity_linker.py` — Cross-layer entity resolution
- **Pruning engine:** `lyra_memory/pruning_engine.py` — Ebbinghaus curves + TTL
- **Multi-signal retrieval:** `lyra_memory/multi_signal_retriever.py` — RRF fusion

## Research Basis

| Source | Key Finding | Adoption |
|--------|-------------|----------|
| Claude Code Dream | 4-phase background consolidation (Orient→Gather→Consolidate→Prune) | Architecture blueprint |
| [Mem0](https://github.com/mem0ai/mem0) | ADD-only extraction, 91.6 LoCoMo, 93.4 LongMemEval | Phase 3 design |
| [TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory) | 8-level hierarchy, hybrid BM25+vector, symbolic STM | Memory topology |
| [MemPalace](https://github.com/MemPalace/mempalace) | Verbatim-first retrieval, temporal anchoring | Retrieval ranking |
| [claude-mem](https://github.com/thedotmack/claude-mem) | Progressive disclosure, memory-as-files | Memory storage format |
| [NGC (Stanford, 2026)](https://arxiv.org/abs/2604.18002) | Block-level context eviction, budget-aware interoception | Context compaction |
| Ebbinghaus (1885) | Forgetting curve: exponential decay without reinforcement | Phase 4 pruning model |

## Benchmark Targets

| Metric | Current | Target | Lever |
|--------|---------|--------|-------|
| LoCoMo | Baseline | 93%+ | Dream consolidation + multi-signal retrieval |
| LongMemEval | Baseline | 95%+ | ADD-only extraction + entity linking |
| Retrieval Precision@5 | 96.6% (BM25+vector) | 98%+ | Multi-signal RRF fusion |
| Consolidation Latency | N/A | <2s per session | Background processing |
| Knowledge Retention (30d) | N/A | >90% | Ebbinghaus-optimized pruning |
