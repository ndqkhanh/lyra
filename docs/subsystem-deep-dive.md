# Lyra Subsystem Deep Dive

**Version:** 7.2.1-Ultra | **Last Updated:** 2026-06-04

> Technical deep-dives into each major subsystem with implementation details, diagrams, and research citations.

## Table of Contents

1. [Memory System Architecture](#memory-system-architecture)
2. [Intelligent Router](#intelligent-router)
3. [Skills Ecosystem](#skills-ecosystem)
4. [Safety & Verification](#safety--verification)
5. [Agent Fleet Coordination](#agent-fleet-coordination)
6. [Self-Evolution Pipeline](#self-evolution-pipeline)

---

## Memory System Architecture

### Overview

The Phoenix Memory system implements a 7-tier cognitive architecture inspired by human memory systems and enhanced with techniques from 22 ICLR 2026 MemAgent Workshop papers.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│ L0: SENSORY BUFFER (~500 tokens)                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Current turn context                            │ │
│ │ Immediate perceptual input                      │ │
│ └─────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │ A-MAC Gate (5 factors)
                   ↓
┌─────────────────────────────────────────────────────┐
│ L1: EPISODIC MEMORY (~2K tokens)                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Session traces with temporal context            │ │
│ │ Who-What-When-Where structure                   │ │
│ └─────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │ CoMem Async Pipeline
                   ↓
┌─────────────────────────────────────────────────────┐
│ L2: SEMANTIC MEMORY (JSON indexed)                  │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Facts, concepts, relationships                  │ │
│ │ BM25 + Vector + RRF hybrid retrieval            │ │
│ └─────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│ L3: PROCEDURAL MEMORY (skills library)              │
│ ┌─────────────────────────────────────────────────┐ │
│ │ SKILL.md files with action patterns             │ │
│ │ Progressive disclosure (L1→L2→L3)               │ │
│ └─────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│ L4-L6: META, COLLECTIVE, ETERNAL                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Learning traces, fleet knowledge, permanent     │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘

        ┌─────────────────────────────────────┐
        │ DREAM CONSOLIDATION (Background)    │
        │ Orient → Gather → Consolidate → Prune│
        └─────────────────────────────────────┘
```

### A-MAC Admission Control

**Paper:** [CoMem: Improving Memory in LLM Agents](https://arxiv.org/abs/2605.20163)

5-factor scoring for memory admission:

```python
def admission_score(memory: Memory) -> float:
    """Compute admission score using 5 factors"""
    return (
        0.3 * utility_score(memory)         # Task relevance
        + 0.25 * confidence_score(memory)   # Factual certainty
        + 0.2 * novelty_score(memory)       # Semantic distance
        + 0.15 * recency_score(memory)      # Temporal decay
        + 0.1 * content_type_score(memory)  # Structural weighting
    )

# Admit if score > threshold (default: 0.5)
```

**Performance:**
- F1 = 0.583 on LongMemEval
- 31% latency reduction
- 87% token savings via early filtering

### Dream Consolidation Pipeline

**Phase 1: Orient (Identify New Knowledge)**

```python
def orient_phase(session_traces: List[Trace]) -> List[Knowledge]:
    """Extract novel knowledge from session"""
    candidates = []
    for trace in session_traces:
        # Extract entities and relationships
        entities = extract_entities(trace)
        relationships = extract_relationships(trace)
        
        # Check novelty against existing memory
        for entity in entities:
            if is_novel(entity, semantic_memory):
                candidates.append(entity)
    
    return candidates
```

**Phase 2: Gather (Collect Related Memories)**

```python
def gather_phase(knowledge: Knowledge) -> MemoryCluster:
    """Collect related memories across all tiers"""
    related = []
    
    # Query each memory tier
    for tier in [L1, L2, L3, L4, L5, L6]:
        matches = tier.query(
            embedding=knowledge.embedding,
            threshold=0.7
        )
        related.extend(matches)
    
    return MemoryCluster(anchor=knowledge, related=related)
```

**Phase 3: Consolidate (ADD-only extraction)**

```python
def consolidate_phase(cluster: MemoryCluster) -> ConsolidatedMemory:
    """Consolidate with ADD-only (no deletion)"""
    # Free-energy minimization
    utility = compute_utility(cluster)
    entropy = compute_entropy(cluster.embedding)
    free_energy = utility - entropy
    
    # Extract consolidated representation
    consolidated = extract_consolidated(cluster)
    
    # Entity linking and deduplication
    consolidated = link_entities(consolidated)
    consolidated = deduplicate(consolidated)
    
    # Auto-Dreamer GRPO optimization
    consolidated = grpo_optimize(consolidated)
    
    return consolidated
```

**Phase 4: Prune (Ebbinghaus forgetting)**

```python
def prune_phase(memory_tier: MemoryTier) -> None:
    """Prune based on Ebbinghaus curve"""
    now = time.time()
    
    for memory in memory_tier:
        # Compute forgetting score
        age_days = (now - memory.timestamp) / 86400
        access_count = memory.access_count
        
        # Ebbinghaus forgetting curve
        retention = math.exp(-age_days / (access_count + 1))
        
        if retention < THRESHOLD:
            # Check for contradictions first
            if has_contradiction(memory):
                resolve_contradiction(memory)
            
            # Prune if stale and not critical
            if not memory.is_critical:
                memory_tier.remove(memory)
```

### Hybrid Retrieval (RRF)

**Papers:** 
- TencentDB-Agent-Memory
- [MemPalace](https://github.com/MemPalace/mempalace)

Reciprocal Rank Fusion combines multiple ranking signals:

```python
def rrf_retrieve(query: str, k: int = 10) -> List[Memory]:
    """Hybrid retrieval with RRF fusion"""
    
    # 1. BM25 keyword search
    bm25_results = bm25_index.search(query, k=k*2)
    
    # 2. Vector semantic search
    query_embedding = embed(query)
    vector_results = vector_index.search(query_embedding, k=k*2)
    
    # 3. MRAgent memory reconstruction
    mragent_results = mragent.reconstruct(query, k=k*2)
    
    # RRF fusion
    scores = defaultdict(float)
    for rank, result in enumerate(bm25_results):
        scores[result.id] += 1.0 / (rank + 60)
    for rank, result in enumerate(vector_results):
        scores[result.id] += 1.0 / (rank + 60)
    for rank, result in enumerate(mragent_results):
        scores[result.id] += 1.0 / (rank + 60)
    
    # Return top-k by fused score
    top_ids = sorted(scores, key=scores.get, reverse=True)[:k]
    return [memory_store[id] for id in top_ids]
```

**Performance:** 96.6% R@5 on LongMemEval with zero API calls

### Dual-Process Retrieval

Inspired by human cognitive systems:

**System 1 (Fast Path):** <50ms
- Recent memories (last 10 turns)
- Hot memories (frequently accessed)
- Direct hash lookup

**System 2 (Deliberate Path):** <200ms
- Full RRF hybrid search
- Graph traversal for related memories
- Reconstruction via MRAgent

```python
def retrieve(query: str, mode: str = "auto") -> List[Memory]:
    """Dual-process retrieval"""
    if mode == "auto":
        # Try System 1 first
        fast_results = system1_retrieve(query)
        if len(fast_results) >= 3 and confidence(fast_results) > 0.8:
            return fast_results
        
        # Fall back to System 2
        return system2_retrieve(query)
    elif mode == "fast":
        return system1_retrieve(query)
    else:
        return system2_retrieve(query)
```

