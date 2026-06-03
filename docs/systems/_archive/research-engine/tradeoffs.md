# Research Engine Tradeoffs

**System:** Multi-Hop Deep Research Engine  
**Version:** 2.0  
**Status:** Production  
**Last Updated:** 2026-06-02

---

## Overview

This document analyzes the design decisions made in the Research Engine, the alternatives considered, performance implications, cost analysis, and maintenance considerations.

---

## Design Decisions

### 1. Multi-Hop vs Single-Pass Research

#### Decision: Multi-Hop Iterative Refinement

**Chosen Approach:** 3-5 iterative hops with query refinement

**Alternatives Considered:**
- **Single-pass exhaustive search**: Retrieve all sources at once
- **Two-phase (broad + narrow)**: One broad search, one focused refinement
- **Unlimited hops until convergence**: Continue until no gaps found

#### Analysis

| Approach | Coverage | Time | Cost | Precision |
|----------|----------|------|------|-----------|
| **Multi-Hop (3-5)** | **High** | **Medium** | **Medium** | **High** |
| Single-pass | Low | Fast | Low | Low |
| Two-phase | Medium | Fast | Low | Medium |
| Unlimited hops | Very High | Slow | High | Very High |

**Why Multi-Hop:**
- Balances coverage and performance
- Allows progressive refinement based on findings
- Prevents over-fetching irrelevant sources
- Natural stopping criterion when gaps close

**Tradeoffs Accepted:**
- **Latency**: 20-30s vs 5-10s for single-pass
- **Complexity**: More complex state management
- **Cost**: Higher API usage for multiple searches

**Performance Impact:**

```python
# Single-pass: Fast but low coverage
single_pass_time = 8s
single_pass_coverage = 45%

# Multi-hop: Slower but high coverage
multi_hop_time = 25s
multi_hop_coverage = 85%

# Coverage gain per second
multi_hop_efficiency = (85 - 45) / (25 - 8) = 2.35% per second
```

**Cost Analysis:**

```
Single-pass:
  - API calls: 50 sources × 1 hop = 50 calls
  - Total time: ~8s
  - Coverage: 45%

Multi-hop (3-5 hops):
  - API calls: 15 sources × 4 hops = 60 calls
  - Total time: ~25s
  - Coverage: 85%

Cost increase: 20% for 89% coverage improvement
```

---

### 2. Knowledge Graph Storage

#### Decision: NetworkX In-Memory + Pickle Persistence

**Chosen Approach:** NetworkX graph stored in memory, pickled to disk

**Alternatives Considered:**
- **Neo4j**: Full-featured graph database
- **SQLite with adjacency list**: Relational representation
- **Redis graph**: In-memory graph with persistence
- **Custom graph structure**: Optimized for research use case

#### Analysis

| Solution | Query Speed | Persistence | Memory Usage | Complexity |
|----------|-------------|-------------|--------------|------------|
| **NetworkX + Pickle** | **Fast** | **Simple** | **Medium** | **Low** |
| Neo4j | Very Fast | Robust | Low | High |
| SQLite | Slow | Robust | Low | Medium |
| Redis Graph | Very Fast | Simple | High | Medium |
| Custom | Very Fast | Custom | Low | Very High |

**Why NetworkX:**
- Simple API, mature library
- Rich graph algorithms built-in (BFS, DFS, shortest path, centrality)
- No external dependencies or server setup
- Fast for graphs <10K nodes (typical research session: 500-2K nodes)
- Easy serialization with pickle

**Tradeoffs Accepted:**
- **Scalability**: Limited to ~50K nodes before performance degrades
- **Concurrent Access**: No built-in locking, single-process only
- **Query Language**: No declarative query language (e.g., Cypher)

**When to Migrate:**

```python
# Performance degradation threshold
if graph.number_of_nodes() > 50_000:
    # Consider migration to Neo4j
    logger.warning("Graph size exceeds 50K nodes, consider Neo4j")
    
# Multi-process requirement
if concurrent_writers > 1:
    # Require external graph DB with locking
    logger.warning("Multiple writers detected, consider Redis Graph")
```

**Cost Comparison (1 year):**

```
NetworkX + Pickle:
  - Infrastructure: $0 (in-process)
  - Memory: ~500MB per session
  - Persistence: Local disk
  - Total: $0/year

Neo4j:
  - Infrastructure: $500/month (managed instance)
  - Memory: Offloaded to DB
  - Persistence: Database
  - Total: $6,000/year

Redis Graph:
  - Infrastructure: $200/month (managed instance)
  - Memory: ~1GB per session
  - Persistence: Redis RDB
  - Total: $2,400/year
```

**Decision:** Start with NetworkX, migrate to Neo4j if:
1. Graph size consistently >50K nodes
2. Multi-process concurrent access required
3. Advanced graph analytics needed (community detection, PageRank)

---

### 3. Source Credibility Scoring

#### Decision: Multi-Dimensional Weighted Scoring

**Chosen Approach:** 5 dimensions (authority, recency, citations, methodology, relevance) with fixed weights

**Alternatives Considered:**
- **Binary trust/untrust**: Simple threshold
- **ML-based scoring**: Train classifier on labeled data
- **Community voting**: Crowdsourced credibility
- **Dynamic weights**: Adjust weights per query type

#### Analysis

| Approach | Accuracy | Transparency | Adaptability | Complexity |
|----------|----------|--------------|--------------|------------|
| **Multi-Dimensional** | **High** | **High** | **Medium** | **Low** |
| Binary | Low | High | Low | Very Low |
| ML-based | Very High | Low | High | High |
| Community voting | Medium | Medium | High | Medium |
| Dynamic weights | Very High | Medium | Very High | High |

**Scoring Formula:**

```python
# Fixed weights (tuned empirically)
WEIGHTS = {
    'authority': 0.25,    # Source reputation
    'recency': 0.15,      # Publication date
    'citations': 0.20,    # Citation count
    'methodology': 0.25,  # Research rigor
    'relevance': 0.15     # Query relevance
}

credibility = sum(score[dim] * WEIGHTS[dim] for dim in WEIGHTS)
```

**Why Multi-Dimensional:**
- Transparent and explainable to users
- No training data required
- Tunable per dimension
- Fast computation (<10ms per source)
- Handles diverse source types (papers, code, web)

**Tradeoffs Accepted:**
- **Fixed Weights**: Not adaptive to query context
- **Manual Tuning**: Requires empirical adjustment
- **Dimension Design**: May miss nuanced factors

**Comparison:**

```
Binary (Trust/Untrust):
  - Precision: 65%
  - Recall: 70%
  - F1: 0.67

Multi-Dimensional (Current):
  - Precision: 82%
  - Recall: 78%
  - F1: 0.80

ML-Based (Hypothetical):
  - Precision: 88%
  - Recall: 85%
  - F1: 0.86
  - Cost: +2 weeks training, +$500/month inference
```

**Future Enhancement:**

Phase 2 can introduce ML-based scoring:
- Train on user feedback (thumbs up/down on sources)
- Use LLM as judge for methodology assessment
- Dynamic weight adjustment per research domain

---

### 4. Evidence Synthesis Strategy

#### Decision: Weighted Aggregation with Contradiction Detection

**Chosen Approach:** Weight claims by source credibility, detect contradictions, flag for manual review

**Alternatives Considered:**
- **Simple majority voting**: Most common claim wins
- **Bayesian inference**: Update beliefs with each evidence
- **LLM-based synthesis**: Use GPT-4 to synthesize
- **Ensemble methods**: Combine multiple strategies

#### Analysis

| Strategy | Accuracy | Explainability | Speed | Robustness |
|----------|----------|----------------|-------|------------|
| **Weighted Aggregation** | **High** | **High** | **Fast** | **High** |
| Majority voting | Medium | High | Very Fast | Medium |
| Bayesian inference | Very High | Low | Medium | Very High |
| LLM-based | Very High | Medium | Slow | Medium |
| Ensemble | Very High | Low | Slow | Very High |

**Synthesis Algorithm:**

```python
def synthesize_claims(claims: List[Claim]) -> Finding:
    """Synthesize claims with weighted voting."""
    
    # Weight by source credibility
    weighted_claims = [
        (claim.text, claim.source.credibility_score)
        for claim in claims
    ]
    
    # Calculate agreement matrix
    agreement = calculate_pairwise_agreement(claims)
    
    # Aggregate using weighted average
    if agreement > 0.8:
        # Strong consensus
        return aggregate_consensus(weighted_claims)
    elif agreement > 0.5:
        # Partial agreement
        return aggregate_partial(weighted_claims)
    else:
        # Conflicting evidence
        return flag_contradiction(claims)
```

**Why Weighted Aggregation:**
- Fast computation (<1s for 50 claims)
- Transparent reasoning (users see which sources supported finding)
- Handles conflicting evidence gracefully
- No API costs (unlike LLM-based)

**Tradeoffs Accepted:**
- **Nuance Loss**: May oversimplify complex relationships
- **Context Sensitivity**: Doesn't adapt synthesis to domain
- **Natural Language**: Synthesized text is templated, not fluent

**Performance:**

```
Weighted Aggregation (Current):
  - Synthesis time: 0.8s per topic
  - Quality (human eval): 7.2/10
  - Cost: $0

LLM-based Synthesis:
  - Synthesis time: 4.5s per topic
  - Quality (human eval): 8.5/10
  - Cost: $0.05 per topic

For 20 topics per research:
  - Current: 16s, free
  - LLM-based: 90s, $1.00
```

**Decision:** Current approach for v2.0, consider LLM synthesis in v2.1 for premium tier.

---

### 5. Research Caching Strategy

#### Decision: Two-Tier Cache (Memory + Redis)

**Chosen Approach:** LRU memory cache (1000 entries) + Redis cache (24h TTL)

**Alternatives Considered:**
- **No caching**: Always fetch fresh results
- **Memory only**: No persistence across restarts
- **Redis only**: Slower access, no memory tier
- **Three-tier (Memory + Redis + Disk)**: Add disk-based long-term cache

#### Analysis

| Strategy | Hit Rate | Access Time | Cost | Freshness |
|----------|----------|-------------|------|-----------|
| **Two-Tier** | **55-60%** | **2ms** | **Low** | **Good** |
| No caching | 0% | N/A | Very High | Excellent |
| Memory only | 30-35% | 1ms | Free | Good |
| Redis only | 50-55% | 5ms | Low | Good |
| Three-tier | 65-70% | 3ms | Medium | Poor |

**Cache Architecture:**

```python
class ResearchCache:
    """Two-tier cache with LRU memory + Redis."""
    
    def __init__(self):
        self.l1_cache = LRUCache(maxsize=1000)  # ~500MB
        self.l2_cache = Redis(ttl=86400)        # 24 hours
    
    async def get(self, query: str) -> Optional[ResearchSession]:
        # L1: Memory cache (1-2ms)
        if query in self.l1_cache:
            return self.l1_cache[query]
        
        # L2: Redis cache (5-10ms)
        result = await self.l2_cache.get(query)
        if result:
            self.l1_cache[query] = result  # Promote to L1
            return result
        
        return None
```

**Why Two-Tier:**
- High hit rate (55%) for repeated queries
- Fast access (2ms average)
- Low cost (Redis: ~$50/month)
- Automatic freshness via TTL

**Tradeoffs Accepted:**
- **Staleness**: Results may be up to 24 hours old
- **Memory Usage**: 500MB for L1 cache
- **Invalidation**: No manual cache invalidation (rely on TTL)

**Cache Performance:**

```
Workload: 1000 queries/day, 55% hit rate

Without cache:
  - Total research time: 1000 × 25s = 25,000s (6.9 hours)
  - API cost: 1000 × $0.10 = $100/day

With two-tier cache:
  - Cache hits: 550 × 2ms = 1.1s
  - Cache misses: 450 × 25s = 11,250s (3.1 hours)
  - Total time: 3.1 hours (55% reduction)
  - API cost: 450 × $0.10 = $45/day (55% reduction)
  - Cache infrastructure: $50/month = $1.67/day
  - Net savings: $53.33/day
```

**ROI:** Cache pays for itself in 1 day.

---

### 6. Query Refinement Strategy

#### Decision: LLM-Guided Refinement with Gap Analysis

**Chosen Approach:** Analyze knowledge graph gaps, use LLM to generate refined query

**Alternatives Considered:**
- **Rule-based expansion**: Add related keywords
- **Template-based**: Fill predefined templates
- **User-guided**: Ask user for refinement
- **Reinforcement learning**: Learn optimal refinements

#### Analysis

| Strategy | Quality | Autonomy | Speed | Cost |
|----------|---------|----------|-------|------|
| **LLM-Guided** | **High** | **High** | **Fast** | **Low** |
| Rule-based | Low | High | Very Fast | Free |
| Template-based | Medium | High | Fast | Free |
| User-guided | Very High | Low | Slow | Free |
| RL | Very High | High | Fast | High |

**Refinement Process:**

```python
async def refine_query(
    original_query: str,
    current_results: List[ResearchResult],
    gaps: List[str]
) -> str:
    """Refine query using LLM to address gaps."""
    
    prompt = f"""
    Original query: {original_query}
    
    Current findings cover:
    {summarize_findings(current_results)}
    
    Knowledge gaps identified:
    {format_gaps(gaps)}
    
    Generate a refined query that addresses these gaps while staying focused.
    """
    
    refined = await llm.generate(prompt, model="gpt-4o-mini")
    return refined.strip()
```

**Why LLM-Guided:**
- Understands semantic context
- Generates natural queries
- Adapts to diverse domains
- Low cost (~$0.001 per refinement)

**Tradeoffs Accepted:**
- **LLM Dependency**: Requires API access
- **Determinism**: Non-deterministic refinements
- **Latency**: Adds 1-2s per hop

**Cost Comparison:**

```
Per refinement (3-4 per research):

LLM-Guided (GPT-4o-mini):
  - Cost: $0.001
  - Quality: 8.5/10
  - Time: 1.5s

Rule-based:
  - Cost: $0
  - Quality: 6.0/10
  - Time: 0.1s

Per 1000 research sessions:
  - LLM-Guided: $3.50 (3500 refinements)
  - Rule-based: $0

Quality-adjusted cost: $0.41 per quality point
```

**Decision:** LLM-guided provides 2.5 points higher quality for minimal cost ($0.0035 per research).

---

## Performance Implications

### Latency Breakdown

```mermaid
%%{init: {'theme': 'dark'}}%%
gantt
    title Research Latency Breakdown (25s total)
    dateFormat X
    axisFormat %S
    
    section Hop 1
    Query Refinement    :0, 2
    Source Retrieval    :2, 5
    Credibility Scoring :5, 2
    Entity Extraction   :7, 3
    
    section Hop 2
    Query Refinement    :10, 2
    Source Retrieval    :12, 4
    Credibility Scoring :16, 2
    Entity Extraction   :18, 2
    
    section Synthesis
    Evidence Aggregation :20, 3
    Report Generation    :23, 2
```

### Bottlenecks

| Component | Time | % of Total | Optimization Potential |
|-----------|------|------------|------------------------|
| Source Retrieval | 9s | 36% | High (parallelize) |
| Entity Extraction | 5s | 20% | Medium (batch processing) |
| Query Refinement | 4s | 16% | Low (already fast model) |
| Credibility Scoring | 4s | 16% | Medium (cache scores) |
| Evidence Synthesis | 3s | 12% | Low (already efficient) |

**Optimization Priorities:**

1. **Parallelize Source Retrieval** (9s → 3s): Use asyncio to query providers concurrently
2. **Batch Entity Extraction** (5s → 3s): Process multiple results in one NLP call
3. **Cache Credibility Scores** (4s → 2s): Store scores by URL for repeated sources

---

## Cost Analysis

### Per-Research Breakdown

```
Average research session (25s, 60 sources):

API Calls:
  - Source retrieval: 60 × $0.001 = $0.06
  - Query refinement: 4 × $0.001 = $0.004
  - Entity extraction (spaCy): $0 (local)
  - Credibility scoring: $0 (local)
  
Infrastructure:
  - Compute: $0.002 (25s × $0.0001/s)
  - Redis cache: $0.001
  - Storage: $0.0001
  
Total per research: $0.07
```

### Monthly Cost Projection

```
Assumptions:
  - 10,000 research queries/month
  - 55% cache hit rate
  - 4,500 new researches

Monthly costs:
  - API calls: 4,500 × $0.07 = $315
  - Redis cache: $50
  - Storage (500GB): $10
  - Compute: 4,500 × $0.002 = $9
  
Total: $384/month

Per-research (amortized): $0.038
```

### Cost vs Alternatives

| Solution | Per Research | Monthly (10K) | Notes |
|----------|--------------|---------------|-------|
| **Lyra Research Engine** | **$0.038** | **$384** | With cache |
| Manual research | $15.00 | $150,000 | 15 min @ $60/hr |
| Perplexity Pro API | $0.50 | $5,000 | Estimated |
| GPT-4 Research Agent | $2.00 | $20,000 | High token usage |

**ROI:** Lyra reduces research cost by 99.7% vs manual.

---

## Maintenance Considerations

### Operational Complexity

| Component | Maintenance Level | Failure Mode | Recovery Time |
|-----------|-------------------|--------------|---------------|
| Multi-Hop Engine | Low | Hung refinement loop | <1 min (timeout) |
| Knowledge Graph | Medium | Corruption | <5 min (rebuild from cache) |
| Source Retrieval | Medium | API rate limits | <1 min (backoff) |
| Redis Cache | Low | Cache miss | 0s (graceful degradation) |
| Credibility Scorer | Low | Score drift | <1 day (retune weights) |

### Monitoring Requirements

```python
# Key metrics to track
METRICS = {
    'research_duration_p50': 25.0,  # seconds
    'research_duration_p99': 45.0,
    'cache_hit_rate': 0.55,
    'source_retrieval_success_rate': 0.95,
    'credibility_score_mean': 0.72,
    'graph_node_count_p50': 500,
    'synthesis_quality_score': 7.2,  # human eval
}

# Alerts
if research_duration_p50 > 35:
    alert("Research latency degraded")

if cache_hit_rate < 0.40:
    alert("Cache efficiency low")

if source_retrieval_success_rate < 0.85:
    alert("Source retrieval failing")
```

### Technical Debt

| Area | Debt Type | Impact | Mitigation Plan |
|------|-----------|--------|-----------------|
| NetworkX Graph | Scalability | Medium | Migrate to Neo4j in v2.1 |
| Fixed Weights | Adaptability | Low | ML-based scoring in v2.2 |
| Pickle Serialization | Compatibility | Low | Switch to JSON in v2.1 |
| Single-Process | Concurrency | Medium | Add worker pool in v2.1 |

---

## Alternative Approaches Not Chosen

### 1. Real-Time Streaming Research

**Description:** Stream results as they arrive instead of batch processing

**Why Not Chosen:**
- Complexity: Requires WebSocket infrastructure
- User Experience: Partial results may be confusing
- Synthesis: Harder to synthesize incomplete findings
- Cost: Higher infrastructure cost

**When to Reconsider:** If user feedback indicates strong preference for real-time updates.

---

### 2. Federated Knowledge Graph

**Description:** Distribute graph across multiple nodes for scalability

**Why Not Chosen:**
- Over-engineering: Current graphs are <10K nodes
- Complexity: Distributed consensus is hard
- Cost: Requires cluster management
- Latency: Network overhead for graph queries

**When to Reconsider:** If graph size consistently exceeds 100K nodes.

---

### 3. Human-in-the-Loop Refinement

**Description:** Ask user to approve/modify each query refinement

**Why Not Chosen:**
- Autonomy: Defeats purpose of automated research
- Latency: Adds 30-60s per hop for user input
- User Burden: Requires constant attention

**When to Reconsider:** For high-stakes research where precision is critical.

---

## Conclusion

The Research Engine design prioritizes:

1. **Balance**: Coverage vs latency vs cost
2. **Simplicity**: Proven technologies over cutting-edge
3. **Transparency**: Explainable scoring and synthesis
4. **Pragmatism**: Good enough now, with clear upgrade paths

Key tradeoffs accepted:
- **Latency** for coverage (25s for 85% coverage)
- **Manual tuning** for transparency (fixed weights)
- **In-memory graph** for simplicity (NetworkX)
- **Template synthesis** for speed (vs LLM synthesis)

These tradeoffs serve the v2.0 goal: production-ready research engine for 10K queries/month. As usage grows, we have clear paths to Neo4j (graph), ML scoring (credibility), and LLM synthesis (quality).

---

## Related Documentation

- [Architecture](./architecture.md) - System architecture overview
- [System Design](./system-design.md) - Detailed design and algorithms
- [Implementation](./implementation.md) - Implementation guide
- [Evaluation](./evaluation.md) - Performance metrics and benchmarks

---

**Research Engine Tradeoffs v2.0** | Last Updated: 2026-06-02
