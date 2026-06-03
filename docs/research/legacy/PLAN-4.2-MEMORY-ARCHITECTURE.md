# Workstream 4.2: Lyra Memory V4 — Breakthrough Memory Architecture Plan

**Version:** 4.0.0
**Date:** 2026-05-30
**Status:** PLAN — Comprehensive. Synthesis of STREAM-3, STREAM-4 (36 MemAgent papers), STREAM-9 (7 repos), MEMORY-ARCHITECTURE-V3, and GAP-ANALYSIS.
**Architecture Codename:** Mnemosyne v1.0

---

## 1. Executive Summary

Lyra Memory V4 ("Mnemosyne") is the core differentiator for the Lyra agent platform. Current V3 provides a 7-tier hierarchy targeting 3.5M effective context tokens with 30-50x compression. Research across 36 papers from the ICLR 2026 MemAgent Workshop and 7 open-source repositories reveals seven specific gaps that prevent V3 from reaching state-of-the-art performance. The V4 architecture closes all seven gaps through five integrated innovation layers:

1. **Bi-temporal multi-graph semantic core** — MAGMA-style 4 orthogonal graphs (Temporal/Causal/Entity/Semantic) replacing flat single-typed graph, with temporal validity windows on every edge (source: arXiv:2601.03236, LoCoMo 0.700 vs 0.481 full-context)
2. **RecMem subconscious memory monitor** — Embedding-based recurrence detector between T1 and T2, achieving 87% token savings by skipping LLM extraction when no new concepts surface (source: arXiv:2605.16045)
3. **RRF hybrid search with recall targets** — Reciprocal Rank Fusion combining BM25 keyword precision with vector semantic breadth, achieving 96.6% R@5 with zero API calls (source: MemPalace open-source)
4. **Thermodynamic consolidation with free-energy objectives** — Entropy-aware memory retention using simulated annealing, improving distractor robustness by +15% at 50% noise (source: Entropic Memory, MemAgent WS)
5. **Multi-agent shared memory with provenance** — Turn-level fact tracking enabling conflict resolution across the Lyra agent fleet (source: MemORAI arXiv:2605.01386, SOTA on LoCoMO)

**Key target metrics:**

| Metric | V4 Target | Source Paper/Repo |
|--------|-----------|-------------------|
| LongMemEval Recall@5 | >=96.6% | MemPalace (BENCHMARKS.md) |
| MemoryAgentBench avg | >=15% | MemoryAgentBench (ICLR 2026) |
| RRF Hybrid Recall@5 | >=96% | MemPalace hybrid v4 |
| Token savings (extraction) | 87% | RecMem arXiv:2605.16045 |
| Token reduction (compression) | 61% raw + 71.5x graph | TencentDB + graphify |
| Retrieval latency (p95) | <100ms | MAGMA 1.47s baseline improved |
| Effective context | >=3.5M tokens | MemAgent (ICLR 2026 Oral) |
| Cross-session forgetting | <=20% | Combined target |
| Distractor robustness | +15% at 50% noise | Entropic Memory |

**Implementation:** 5 phases over 14 weeks, prioritized by Impact x Effort. S-tier enhancements (bi-temporal edges, RecMem, RRF) deliver ~60% of total architecture value in the first 2 weeks.

---

## 2. Current State: Lyra Memory V3

### 2.1 Seven-Tier Architecture

Lyra V3 defines a 7-tier hierarchy targeting 3.5M token effective context:

```
T0: Working Memory (8K tokens, active context)
T1: Episodic Memory (compressed segments, 30-50x)
T2: Semantic Memory (graph-based, concepts + relationships)
T3: Procedural Memory (skills, workflows, error recovery)
T4: Persistent Memory (SQLite + Redis, cross-session)
T5: Vector Memory (embeddings, ANN search)
T6: Archive Memory (cold storage, analytics)
```

**Strengths:** Full 7-tier hierarchy, dream consolidation concept, cross-session persistence (SQLite+Chroma), symbolic compression (30x), graph-based semantic memory, hybrid retrieval concept, O(1) reconstructive consolidation, 437x context expansion target.

### 2.2 Known Gaps Before Research

- Single-typed semantic graph (no temporal/causal/entity separation)
- No temporal validity on knowledge graph edges
- No subconscious monitoring between tiers
- No evolutionary fleet memory for multi-agent
- Fixed threshold compression (not agent-initiated)
- Pure embedding retrieval (no hybrid RRF implemented)
- No provenance tracking for multi-agent conflict resolution

---

## 3. Research Gaps: What 36 Papers and 7 Repos Reveal

Seven specific gaps identified from the research synthesis, each with citations and metrics.

### Gap 1: Bi-temporal Knowledge Graph Edges
**Source:** MemAgent Workshop, Zep, MemPalace §4.5 | **Metric:** 15-point LongMemEval gap

The V3 semantic graph stores facts without temporal validity windows, so Lyra cannot answer "what did we know on date Y?" or "what changed between experiments A and B?". MemPalace demonstrates `valid_from`/`valid_to` on every triple with native `query_entity(as_of=date)` support. This accounts for a 15-point performance gap on LongMemEval temporal queries.

### Gap 2: RecMem Subconscious Memory Monitor
**Source:** arXiv:2605.16045 (RecMem), STREAM-4 §7 | **Metric:** 87% token savings

V3 runs LLM-based extraction on every episodic segment entering T2. RecMem inserts a lightweight embedding-based recurrence detector between T1 and T2. Only when the same concept appears across multiple episodes does it trigger expensive LLM extraction. Single-occurrence concepts are queued for batch processing or discarded. The 87% savings comes from the observation that most agent interactions are routine operations on known entities.

### Gap 3: MAGMA 4-Graph Architecture
**Source:** arXiv:2601.03236 (MAGMA, ACL 2026 Main), STREAM-4 §26 | **Metric:** +18.5% over single-graph, LoCoMo 0.700

V3's single semantic graph conflates temporal ordering, causal chains, entity relationships, and conceptual similarity. MAGMA's four orthogonal graphs with policy-guided traversal achieve 0.700 on LoCoMo (vs 0.481 full-context, 0.580 A-MEM), ~95% fewer tokens, 1.47s query latency. Ablation: removing adaptive traversal drops 0.700 to 0.637.

| Graph | Query Type | Purpose | V3 Status |
|-------|-----------|---------|-----------|
| Temporal | "When?" | Immutable event timeline | MISSING |
| Causal | "Why?" | Cause-and-effect chains | PARTIAL (not integrated) |
| Entity | "Who/What?" | Agent/tool/user/skill entities | MISSING |
| Semantic | "What's related?" | Conceptual similarity | EXISTS (single-typed) |

### Gap 4: Prism Evolutionary Fleet Memory
**Source:** arXiv:2604.19795 (Prism), MemORAI arXiv:2605.01386, GAP-ANALYSIS §1 | **Metric:** SOTA on LoCoMO

V3's multi-agent memory is package-based but has no substrate for evolutionary cross-agent experience sharing. Prism introduces fleet-tier memory with selection pressure. MemORAI provides the provenance infrastructure — turn-level tracking of which agent contributed which fact — enabling SOTA on LoCoMO and LongMemEval.

### Gap 5: Autonomous Compression Trigger
**Source:** arXiv:2601.07190 (Focus Agent), TencentDB §1.6 | **Metric:** 30-50% more efficient compaction

V3 uses fixed threshold-based compression (50% = mild offload, 85% = aggressive). Focus Agent demonstrates that agent-initiated compression yields substantially better preservation of task-relevant context because the agent knows which context is still needed.

### Gap 6: Experience Compression Spectrum
**Source:** arXiv:2604.15877, Acontext (skill-as-memory) | **Metric:** Unifies memory/skills/rules

V3 treats memory, skills, and rules as separate systems. The Experience Compression paper shows these are points on the same compression continuum — memory (low compression, high fidelity), skills (medium compression, patterns), rules (high compression, heuristics). Acontext's "skill-as-memory" philosophy validates this unification.

### Gap 7: RRF Hybrid Search (Not Yet Integrated)
**Source:** MemPalace §4.4 (96.6% R@5), TencentDB §1.5 | **Metric:** 96.6% R@5 zero API calls

V3's T5 vector memory uses pure embedding retrieval. MemPalace proves BM25 + vector via RRF achieves 96.6% R@5 without any LLM calls (hybrid v4: 98.4%, +LLM rerank: >=99%). BM25 captures exact token matches that vectors miss; vectors capture semantic similarity that BM25 misses. CodeGraph validates SQLite+FTS5 as a proven low-cost backend.

---

## 4. Proposed Enhancements: Impact x Effort Ranking

### S-Tier: Highest Value, Immediate Priority

| ID | Enhancement | Source | Impact | Effort | Timeline | Value |
|----|-------------|--------|--------|--------|----------|-------|
| S1 | Bi-temporal KG edges | MemPalace, Zep | 15pt LongMemEval | M (1w) | Wk 1-2 | V.HIGH |
| S2 | RecMem subconscious monitor | arXiv:2605.16045 | 87% token savings | M (1w) | Wk 1-2 | V.HIGH |
| S3 | RRF hybrid search | MemPalace, TencentDB | 96.6% R@5, zero API | L (3d) | Wk 1 | V.HIGH |

### A-Tier: High Value, Next Priority

| ID | Enhancement | Source | Impact | Effort | Timeline | Value |
|----|-------------|--------|--------|--------|----------|-------|
| A1 | MAGMA 4-graph split | arXiv:2601.03236 | +18.5% accuracy | H (2-3w) | Wk 3-5 | V.HIGH |
| A2 | Mermaid symbolic compression | TencentDB | 61% token reduction | L (2-3d) | Wk 2 | HIGH |
| A3 | L0-L3 semantic pyramid | TencentDB | Lossless drill-down | M (1-2w) | Wk 3-4 | HIGH |
| A4 | 3-layer search API | claude-mem | 10x token savings | L (2d) | Wk 1-2 | HIGH |
| A5 | Admission gate (A-MAC) | arXiv:2604.19795 | F1=0.583, 31% latency | M (1w) | Wk 3-4 | HIGH |

### B-Tier: Important but Deferrable

| ID | Enhancement | Source | Impact | Effort | Timeline | Value |
|----|-------------|--------|--------|--------|----------|-------|
| B1 | Thermodynamic consolidation | Entropic Memory | +15% robustness | H (2w) | Wk 6-8 | MEDIUM |
| B2 | Active reconstruction retrieval | MRAgent | +23% LoCoMo | V.H (3w) | Wk 6-9 | HIGH |
| B3 | Fleet shared memory + provenance | MemORAI, Prism | SOTA LoCoMO | H (2w) | Wk 8-11 | MEDIUM |
| B4 | Autonomous compaction trigger | Focus Agent | 30-50% more efficient | M (1w) | Wk 5-6 | MEDIUM |
| B5 | Auto-compaction pipeline | TencentDB, STREAM-9 §10 | Full lifecycle | M (2w) | Wk 7-9 | MEDIUM |
| B6 | Experience compression | arXiv:2604.15877 | Mem/skills unification | H (2w) | Wk 10-12 | MEDIUM |

---

## 5. Architecture: Lyra Memory V4

### 5.1 Seven-Tier V4 Hierarchy with Data Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     LYRA MEMORY V4 (MNEMOSYNE)                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  T0: WORKING MEMORY (8K tokens, active context)                           │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ Circular buffer, L2-norm importance tagging (Norm-Guided Eviction)│    │
│  │ Goal-conditioned gating (CraniMem), SABER mutation flags         │    │
│  └─────────────────────┬─────────────────────────────────────────────┘    │
│                         │ Mermaid symbolic compression (30-50x)            │
│                         ▼                                                  │
│  T1: EPISODIC MEMORY (Compressed segments, bounded, K=100 sessions)      │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ REMem gist+fact dual representation, utility-tagged, cue anchors   │    │
│  │ Memora-inspired retrieval access points, multi-granularity links   │    │
│  └─────────────────────┬─────────────────────────────────────────────┘    │
│                         │ RecMem Monitor (87% savings)  ← NEW              │
│  ┌──────────────────────┴──────────────────────────────────────────┐      │
│  │ Embedding recurrence detector: NOVEL → LLM extract;             │      │
│  │ FAMILIAR → skip (batch or discard)                              │      │
│  └──────────────────────┬──────────────────────────────────────────┘      │
│                         ▼                                                 │
│  T2: 4-GRAPH SEMANTIC MEMORY (MAGMA)  ← NEW                               │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐  │    │
│  │ │ TEMPORAL     │ │ CAUSAL       │ │ ENTITY       │ │ SEMANTIC │  │    │
│  │ │ (When?)      │ │ (Why?)       │ │ (Who/What?)  │ │ (Related)│  │    │
│  │ │ Immutable    │ │ Cause→effect │ │ Agent/Tool/  │ │ Concept  │  │    │
│  │ │ timeline     │ │ chains + slow│ │ User/Skill   │ │ simil.   │  │    │
│  │ └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘  │    │
│  │ All edges: bi-temporal (valid_from/valid_until) ← NEW             │    │
│  │ Retrieval: policy-guided traversal per graph type  ← NEW          │    │
│  └─────────────────────┬─────────────────────────────────────────────┘    │
│                         │ Skill extraction from successful patterns        │
│                         ▼                                                  │
│  T3: PROCEDURAL MEMORY (Skills, workflows, ERL heuristics)               │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ ERL-inspired heuristic extraction from trajectories              │    │
│  │ Selective retrieval (NOT blanket — ERL critical ablation finding) │    │
│  └─────────────────────┬─────────────────────────────────────────────┘    │
│                         │ Cross-session persistence                       │
│                         ▼                                                  │
│  T4: PERSISTENT MEMORY (SQLite FTS5 + Chroma)                            │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ L0: JSONL raw → L1: SQLite+vec atoms → L2: MD scenes → L3: MD    │    │
│  │ persona (TencentDB pyramid, lossless drill-down)                  │    │
│  │ Bi-temporal KG in SQLite (MemPalace), XML-tag context injection   │    │
│  └─────────────────────┬─────────────────────────────────────────────┘    │
│                         │ RRF hybrid search                               │
│                         ▼                                                  │
│  T5: VECTOR MEMORY (Embeddings, ANN)  ← RRF fusion                       │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ BM25 + Vector RRF (96.6% R@5, zero API)   3-layer search API     │    │
│  │ (index→timeline→details, 10x savings)  Pluggable: ChromaDB default│    │
│  └─────────────────────┬─────────────────────────────────────────────┘    │
│                         │ Archival via graph compression                  │
│                         ▼                                                  │
│  T6: ARCHIVE MEMORY (Cold storage, analytics)                            │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ graphify-inspired 71.5x token reduction, Leiden community detect. │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│  FLEET: Multi-Agent Shared Memory (MemORAI + Prism)  ← NEW                │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │ Provenance (who/what/when)  Conflict resolution  Gossip protocol  │    │
│  │ Belief/Opinion network (Hindsight-inspired)                       │    │
│  └───────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 MAGMA 4-Graph Split Detail

```
                    ┌─────────────────────────────┐
                    │   ADMISSION GATE (A-MAC)     │
                    │ 5 factors: future_utility +  │
                    │ factual_confidence + novelty +│
                    │ recency + content_type_prior  │
                    └──────────────┬──────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ FAST PATH         │  │ SLOW PATH          │  │ CONSOLIDATION     │
│ Immediate ingest  │  │ Async LLM infer    │  │ Batch dedup+prune │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          └──────────┬───────────┴───────────┬───────────┘
                     │                       │
                     ▼                       ▼
       ┌─────────────────────┐  ┌─────────────────────┐
       │ TEMPORAL GRAPH      │  │ CAUSAL GRAPH         │
       │ Nodes: Events       │  │ Nodes: Events        │
       │ Edges: before/after │  │ Edges: causes/enables │
       │   during/overlaps   │  │   prevents/contributes│
       │ Immutable timeline  │  │ Strength 0.0-1.0      │
       │ Operations:         │  │ discovered_by: fast/  │
       │   get_events_in_    │  │   slow_path           │
       │   window(start,end) │  │ Operations:           │
       │   get_timeline()    │  │   trace_causes(depth) │
       └─────────────────────┘  │   find_common_causes()│
                               └─────────────────────┘
       ┌─────────────────────┐  ┌─────────────────────┐
       │ ENTITY GRAPH        │  │ SEMANTIC GRAPH       │
       │ Nodes: Agent, Tool, │  │ Nodes: Concepts      │
       │   Skill, User, Pkg  │  │ Edges: similarity,   │
       │ Edges: uses/depends │  │   synonymous, spec.  │
       │   on/created_by     │  │ Cross-graph links    │
       │ temporal: first/    │  │ Granularities:       │
       │   last_observed     │  │   kw/summary/turn/s  │
       └─────────────────────┘  └─────────────────────┘
```

### 5.3 RecMem Subconscious Monitor Pipeline

```
T1 Episode arrives
       │
       ▼
┌──────────────────────────────┐
│ 1. EMBED episode (~2ms)     │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 2. RECURRENCE DETECTION      │
│    Cosine sim vs last 100    │
│    embeddings (O(n*d))       │
│    Threshold: 0.75           │
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
  SCORE < 0.75        SCORE >= 0.75
  (NOVEL)              (FAMILIAR)
       │                   │
       ▼                   ├─────────────────┐
┌─────────────────┐       │                 │
│ LLM EXTRACT     │       │ SKIP LLM        │
│ to T2 graphs    │       │ Episode store   │
│ ~200-500 tokens │       │ only (no T2)    │
│ per event       │       │ Update entity   │
│                  │       │ frequency       │
└─────────────────┘       │ count           │
                           │ SAVED: ~200-500 │
                           │ tokens/event    │
                           └─────────────────┘

TOTAL SAVINGS: 87% of extraction tokens
(4 of 5 episodes are recurrence-skipped in typical agent workflow)
```

### 5.4 Consolidation Cycle (Dream Phase)

```
FAST CONSOLIDATION (every N=10 turns, ~500ms)
├─ 1. L2-norm importance tagging on working memory items
├─ 2. Admission scoring on new episodic items (5-factor A-MAC)
├─ 3. Evict low-importance items from working memory
└─ 4. Write utility-tagged entries to episodic buffer

DEEP CONSOLIDATION (every session boundary, ~30s background)
├─ 1. FREE-ENERGY SCORING (Entropic Memory)
│     └─ Score = utility - temperature * embedding_entropy
├─ 2. STOCHASTIC ACCEPTANCE (simulated annealing)
│     └─ p = sigmoid(score / T); prune bottom 20%
├─ 3. SEMANTIC CONVERSION
│     └─ Episodes → TemporalGraph + CausalGraph + EntityGraph
├─ 4. MERGE & DEDUP (CraniMem)
│     └─ Similar episodes merged (threshold > 0.85)
└─ 5. UPDATE STATISTICS
      └─ Admission weights adjusted per recent performance

GLOBAL CONSOLIDATION (every M=50 sessions, ~2min offline)
├─ 1. Leiden community detection on entity graph
├─ 2. ERL heuristic extraction from successful patterns
├─ 3. Opinion network update (Hindsight)
└─ 4. Admission gate weight optimization (cross-validated)
```

### 5.5 Retrieval Orchestrator Flow

```
Query arrives
  │
  ▼
1. ENTROPY GRANULARITY ROUTER (MemGAS, +38.4% F1)
  │  → Optimal level: keyword | summary | turn | session
  ▼
2. COST-SENSITIVE STORE ROUTER (Gaikwad)
  │  → Stores selected by query type, budget, time pressure
  ▼
3. MULTI-STRATEGY PARALLEL RETRIEVAL (Hindsight TEMPR)
  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
  │  │SEMANTIC│ │ BM25   │ │ GRAPH  │ │TEMPORAL│
  │  │vectors │ │ FTS5   │ │ 4-graph│ │filter  │
  │  └────────┘ └────────┘ └────────┘ └────────┘
  ▼
4. RRF FUSION + CROSS-ENCODER RERANK
  │  score = α*BM25_rank + (1-α)*vector_rank (96.6% R@5)
  ▼
5. ACTIVE RECONSTRUCTION (if insufficient, MRAgent +23%)
  │  Iterative explore & prune guided by reasoning
  ▼
6. CALLBACK QUERY (if needs history, ReMemR1 82.8% HotpotQA)
  │  Cross-session recall from earlier sessions
  ▼
7. NARRATIVE SYNTHESIS + REDUNDANCY FILTER
  │  Topological order + LLM dedup (MemGAS)
  ▼
  FINAL CONTEXT (budget-capped)
```

---

## 6. Python Dataclass Interfaces

### 6.1 Core Data Types

```python
@dataclass
class WorkingMemoryItem:
    """T0 item with importance tagging + goal-conditioned gating."""
    id: str; content: str; embedding: ndarray
    l2_norm_score: float; goal_relevance: float
    timestamp: datetime; source: str
    mutating: bool                                 # SABER mutation flag
    ttl: int                                       # Turns until eviction

@dataclass
class Gist:
    """REMem human-readable event summary."""
    summary: str; participants: List[str]; location: str
    emotions: List[str]; outcome: str; lessons: List[str]

@dataclass
class Fact:
    """Time-scoped (S,P,O) triple with temporal qualifiers."""
    subject: str; predicate: str; object: str
    start_time: Optional[datetime]; end_time: Optional[datetime]
    point_in_time: Optional[datetime]; confidence: float; provenance: str

@dataclass
class EpisodicMemoryItem:
    """T1 item: gist+fact dual rep + consolidation metadata."""
    id: str; gist: Gist; facts: List[Fact]
    utility_score: float; embedding_entropy: float; valence_vector: ndarray
    session_id: str; timestamp: datetime; duration: timedelta
    source_agent: str; source_type: str
    confidence: float; granularities: Dict[str, str]; cue_anchors: List[str]
```

### 6.2 TemporalGraph (T2a)

```python
@dataclass
class TemporalNode:
    event_id: str; timestamp: datetime                     # Immutable
    event_type: str; session_id: str; pointer_to_episodic: str

@dataclass
class TemporalEdge:
    """Bi-temporal edge: source→target relation with validity window."""
    source_event: str; target_event: str
    relation: Literal['before','after','during','overlaps','contains']
    valid_from: datetime; valid_until: Optional[datetime]
    confidence: float; evidence: List[str]; timestamp_delta: timedelta

class TemporalGraph:
    def get_events_in_window(self, start: datetime, end: datetime) -> List[TemporalNode]: ...
    def get_timeline(self, entity_id: str, limit: int = 100) -> List[TemporalNode]: ...
    def find_cotemporaneous(self, event_id: str, window: timedelta) -> List[TemporalNode]: ...
    def query_at_time(self, entity_id: str, as_of: datetime) -> List[TemporalNode]: ...
```

### 6.3 CausalGraph (T2b)

```python
@dataclass
class CausalNode:
    event_id: str; description: str; is_root_cause: bool; is_observed_effect: bool

@dataclass
class CausalEdge:
    cause_event: str; effect_event: str
    relation: Literal['causes','enables','prevents','contributes_to','mitigates']
    strength: float; evidence: List[str]; discovered_by: str  # fast|slow path
    valid_from: datetime; valid_until: Optional[datetime]

class CausalGraph:
    def trace_causes(self, event_id: str, depth: int = 5) -> List[CausalNode]: ...
    def trace_effects(self, event_id: str, depth: int = 5) -> List[CausalNode]: ...
    def find_common_causes(self, event_a: str, event_b: str) -> List[CausalNode]: ...
    def slow_path_infer_causality(self, events: List[CausalNode]) -> List[CausalEdge]: ...
```

### 6.4 EntityGraph (T2c) and SemanticGraph (T2d)

```python
@dataclass
class EntityNode:
    entity_id: str; entity_type: Literal['agent','tool','skill','user','package','config','model']
    properties: Dict[str, Any]; created_at: datetime; last_updated: datetime

@dataclass
class EntityEdge:
    source_entity: str; target_entity: str; relation: str
    first_observed: datetime; last_observed: datetime
    valid_from: datetime; valid_until: Optional[datetime]; confidence: float

@dataclass
class SemanticNode:
    node_id: str; content_hash: str; embedding: ndarray
    granularity: Literal['keyword','summary','turn','session']
    chunk_text: str; synthetic_queries: List[str]

@dataclass
class SemanticEdge:
    source_node: str; target_node: str; similarity: float
    relation_type: str; cross_graph_links: Dict[str, str]

class EntityGraph:
    def get_entity_context(self, entity_id: str) -> EntityNode: ...
    def find_related(self, entity_id: str, types: List[str]) -> List[EntityNode]: ...
    def entity_timeline(self, entity_id: str) -> List[TemporalNode]: ...

class SemanticGraph:
    def semantic_search(self, q: ndarray, top_k: int, filters: dict) -> List[SemanticNode]: ...
    def expand_query(self, query: str, anchors: List[str]) -> List[str]: ...
    def induce_links(self, new: SemanticNode) -> List[SemanticEdge]: ...
```

### 6.5 RecMem Subconscious Monitor

```python
@dataclass
class RecMemResult:
    episode_id: str; recurrence_score: float; is_novel: bool
    similar_episodes: List[str]; concept_cluster: Optional[str]

class RecMemMonitor:
    """Embedding-based monitor between T1 and T2. Skips 87% of LLM extractions."""
    threshold: float = 0.75; window_size: int = 100

    def monitor(self, episode: EpisodicMemoryItem) -> RecMemResult: ...
    def compute_recurrence(self, embedding: ndarray) -> float: ...
    def should_extract(self, result: RecMemResult) -> bool:
        return result.recurrence_score < self.threshold  # Novel → extract
    def batch_process(self, queue: List[EpisodicMemoryItem]) -> None: ...
    def get_token_savings(self) -> float: ...
```

### 6.6 Admission Gate

```python
@dataclass
class AdmissionFactors:
    future_utility: float; factual_confidence: float
    semantic_novelty: float; temporal_recency: float; content_type_prior: float

class AdmissionGate:
    """A-MAC 5-factor admission control before any memory write."""
    WEIGHTS = {'future_utility': 0.25, 'factual_confidence': 0.25,
               'semantic_novelty': 0.20, 'temporal_recency': 0.10,
               'content_type_prior': 0.20}
    CONTENT_TYPE_PRIORS = {'user_input': 0.9, 'tool_output': 0.6,
                           'agent_inference': 0.7, 'system_event': 0.4}

    def evaluate(self, item: EpisodicMemoryItem, goals: List[str],
                 existing: List[EpisodicMemoryItem]) -> AdmissionFactors: ...
    def admit(self, item: EpisodicMemoryItem,
              noise_level: float = 0.0) -> bool: ...
    def adaptive_temperature(self, noise_level: float) -> float: ...
    def update_weights(self, recent_perf: Dict[str, float]) -> None: ...
```

### 6.7 Consolidation Engine

```python
@dataclass
class ConsolidationReport:
    episodes_processed: int; elements_retained: int; elements_pruned: int
    compression_ratio: float; retention_rate: float; temperature: float; duration_ms: float

class ConsolidationEngine:
    """Free-energy consolidation (Entropic Memory + CraniMem)."""
    def __init__(self, temperature: float = 1.0, annealing_rate: float = 0.95): ...

    def fast_consolidate(self, wm: WorkingMemory) -> List[EpisodicMemoryItem]: ...
    def deep_consolidate(self, buffer: EpisodicBuffer, graphs: Dict[str, Any],
                         budget: int) -> ConsolidationReport: ...
    def global_consolidate(self, buffers: Dict[str, Any]) -> ConsolidationReport: ...

    def _free_energy(self, utility: float, entropy: float) -> float:
        """F = U - T*S from Entropic Memory."""
        return utility - self.temperature * entropy

    def _stochastic_accept(self, fe: float) -> bool:
        p = 1.0 / (1.0 + math.exp(-fe / self.temperature))
        return random.random() < p
```

### 6.8 Fleet Shared Memory

```python
@dataclass
class ProvenanceRecord:
    """MemORAI turn-level fact origin tracking."""
    fact_id: str; source_agent: str; source_session: str; source_turn: int
    source_type: str; supporting_evidence: List[str]; contradicting_evidence: List[str]
    confidence: float; last_verified: datetime; verification_count: int

@dataclass
class Belief:
    """Hindsight belief with confidence + reinforcement tracking."""
    subject: str; predicate: str; value: Any; confidence: float
    formed_at: datetime; last_reinforced: datetime
    reinforcement_count: int; contradictory_evidence_count: int

class FleetSharedMemory:
    def record_provenance(self, record: ProvenanceRecord) -> None: ...
    def resolve_conflict(self, a: ProvenanceRecord, b: ProvenanceRecord) -> ProvenanceRecord: ...
    def update_belief(self, belief: Belief, evidence: ProvenanceRecord) -> None: ...
    def share_with_fleet(self, delta: Dict) -> None: ...
    def fleet_convergence(self, peer_state: Dict) -> Dict: ...
```

---

## 7. Implementation Phases

### Phase M1: Foundation (Week 1-2) — S-tier enhancements (60% of value)

| Task | Source | Effort | Owner |
|------|--------|--------|-------|
| RRF hybrid search (BM25 FTS5 + vector fusion) | MemPalace, TencentDB | 3 days | lyra-memory |
| Mermaid symbolic compression | TencentDB | 2-3 days | lyra-context-optimizer |
| XML-tag context injection | claude-mem | 1 day | lyra-context-optimizer |
| Bi-temporal edges on all T2 edges | MemPalace, Zep | 1 week | lyra-knowledge-graph |
| RecMem embedding monitor (T1→T2 gate) | arXiv:2605.16045 | 1 week | lyra-memory |
| 3-layer search API | claude-mem | 2 days | lyra-memory |

**Validation:** RRF >=90% R@5 internal, RecMem 87% savings confirmed, MemoryAgentBench baseline established.

### Phase M2: Multi-Graph Core (Week 3-5) — A-tier enhancements

| Task | Source | Effort | Owner |
|------|--------|--------|-------|
| Split T2 into Entity/Temporal/Causal/Semantic | MAGMA arXiv:2601.03236 | 2-3w | lyra-knowledge-graph + lyra-causal-graph |
| Policy-guided retrieval routing | MAGMA ablation (0.700→0.637 drop) | 1w | lyra-memory |
| L0-L3 pyramid with drill-down | TencentDB | 1-2w | lyra-memory-stack |
| Admission gate (A-MAC 5-factor) | arXiv:2604.19795 | 1w | lyra-memory |
| SpaCy NLP entity extraction | STREAM-9 §7, §12 | 1w | lyra-knowledge-graph |
| Autonomous compaction trigger | Focus Agent | 1w | lyra-context-optimizer |

**Validation:** 4 graphs operational, bi-temporal retrieval >=80% accuracy, admission F1>=0.55.

### Phase M3: Consolidation (Week 6-8) — B-tier high-value

| Task | Source | Effort | Owner |
|------|--------|--------|-------|
| Free-energy consolidation engine | Entropic Memory | 2w | lyra-continual |
| Fast/deep/global consolidation scheduling | CraniMem | 1w | lyra-cognitive |
| Modular compression with interference bounds | Inhar | 1.5w | lyra-context-optimizer |
| ERL heuristic extraction from trajectories | ERL (STREAM-4 §8) | 1w | lyra-skills |
| Auto-compaction pipeline with recovery | TencentDB + STREAM-9 §10 | 2w | lyra-context-optimizer |
| MemGAS entropy-driven granularity router | MemGAS +38.4% F1 | 1w | lyra-memory |

**Validation:** +15% distractor robustness at 50% noise, ERL +5% task success.

### Phase M4: Active Retrieval (Week 9-11) — B-tier high-value

| Task | Source | Effort | Owner |
|------|--------|--------|-------|
| Active reconstruction engine (Cue-Tag-Content) | MRAgent +23% LoCoMo | 2-3w | lyra-memory |
| Retrieval orchestrator + store routing | Gaikwad + Hindsight TEMPR | 2w | lyra-memory |
| Cross-session callback queries | ReMemR1 82.8% HotpotQA | 1.5w | lyra-context-optimizer |
| CoMem async compression pipeline | CoMem 1.4x latency | 1w | lyra-memory-stack |
| Cross-encoder reranking top-50 | Hindsight TEMPR | 1w | lyra-memory |

**Validation:** Active retrieval >=15% improvement over static, CoMem 1.4x latency gain.

### Phase M5: Fleet Memory (Week 12-14) — B-tier integration

| Task | Source | Effort | Owner |
|------|--------|--------|-------|
| Provenance tracking | MemORAI SOTA LoCoMO | 2w | lyra-gossip-memory |
| Conflict resolution | SABER + Hindsight | 1.5w | lyra-beliefs |
| Belief/opinion network | Hindsight 89.0% LongMemEval | 1.5w | lyra-beliefs |
| Fleet gossip protocol enhancement | Lyra existing + Prism | 1w | lyra-gossip-memory |
| Experience compression unification | arXiv:2604.15877 | 2w | lyra-skills |
| Memory Probe diagnostic integration | Memory Probe r=0.98 | 1w | lyra-eval-pipeline |

**Validation:** Conflict resolution >=80%, fleet convergence <30s, Memory Probe running continuously.

---

## 8. Benchmark Targets

### LongMemEval

| Sub-benchmark | V4 Target | Source Baseline |
|--------------|-----------|-----------------|
| Overall R@5 (RAW) | >=96.6% | MemPalace RAW: 96.6% |
| Overall R@5 (BRIDGE) | >=90% | Hindsight 20B: 83.6% |
| Temporal Recall | >=85% | Bi-temporal KG edges |
| Cross-session | >=80% | ReMemR1 callback queries |
| Multi-hop Reasoning | >=60% | Active reconstruction (MRAgent +23%) |

### MemoryAgentBench (4 Competencies)

| Competency | V4 Target | Notes |
|-----------|-----------|-------|
| Accurate Retrieval | >=90% | Single + multi-hop |
| Test-Time Learning | >=40% | New behaviors during deployment |
| Long-Range Understanding | >=60% | Cross >=100K tokens |
| Selective Forgetting | >=30% | Overwrite/revise contradictions |
| Multi-hop Conflict Resolution | >=15% | Hardest problem; current ceiling: 7% |

### Retrieval Quality

| Metric | Target | Source |
|--------|--------|--------|
| RRF Recall@5 | >=96% | MemPalace |
| Cross-encoder NDCG@10 | >=0.85 | Hindsight |
| Retrieval Precision | >=95% | Memory Probe (r=0.98) |
| Retrieval Latency (p95) | <100ms | MAGMA + CoMem |
| Memory Utilization Rate | >=90% | Memory Probe |

### Compression

| Metric | Target | Source |
|--------|--------|--------|
| Mermaid token reduction | >=61% | TencentDB |
| Graph query reduction | >=71.5x | graphify |
| Semantic pyramid savings | >=60% | TencentDB |
| KV-cache throughput | >=2x | R-KVHash |
| Memory growth rate | <1K tokens/hour | Compaction + admission |

### System

| Metric | Target | Notes |
|--------|--------|-------|
| Effective context | >=3.5M tokens | MemAgent-inspired |
| Cross-session retention | >=80% | Voting + refinement |
| Fleet convergence time | <30s | Gossip protocol |
| Admitted memory F1 | >=0.58 | A-MAC admission gate |

---

## 9. References

### Research Papers (with Key Metrics)

| # | Paper | Venue | Key Metric | Source |
|---|-------|-------|-----------|--------|
| 1 | MAGMA: Multi-Graph Memory | ACL 2026 | LoCoMo 0.700, -95% tokens, +18.5% | arXiv:2601.03236 |
| 2 | MRAgent: Memory Reconstructed | MemAgent WS | +23% LoCoMo/LongMemEval | STREAM-4 §14 |
| 3 | RecMem subconscious monitor | arXiv 2026 | 87% token savings | arXiv:2605.16045 |
| 4 | A-MAC admission control | MemAgent WS | F1=0.583, 31% latency reduction | STREAM-4 §22 |
| 5 | Entropic Memory consolidation | MemAgent WS | +15% survival at 50% noise | STREAM-4 §21 |
| 6 | MemoryAgentBench (4 comp.) | ICLR 2026 | 4-competency, 7% ceiling | arXiv:2507.05257 |
| 7 | Memory Probe diagnostic | MemAgent WS | r=0.98 retrieval->accuracy | arXiv:2603.02473 |
| 8 | Hindsight memory architecture | arXiv 2025 | 89.0% LongMemEval (OSS 120B) | arXiv:2512.12818 |
| 9 | MemGAS multi-granularity | ICLR 2026 | +38.4% F1 on LongMemEval | STREAM-4 §36 |
| 10 | MemORAI provenance tracking | arXiv 2026 | SOTA LoCoMO+LongMemEval | arXiv:2605.01386 |
| 11 | REMem episodic reasoning | ICLR 2026 | +13.4% episodic reasoning | arXiv:2602.13530 |
| 12 | ReMemR1 callback queries | MemAgent WS | 82.8% HotpotQA, <0.2% overhead | arXiv:2509.23040 |
| 13 | MemAgent RL compression | ICLR 2026 Oral | 8K->3.5M tokens, <5% degradation | arXiv:2507.02259 |
| 14 | ERL heuristic extraction | MemAgent WS | +7.8% success on Gaia2 | STREAM-4 §8 |
| 15 | SABER mutation safeguards | MemAgent WS | +28% relative on Airline | STREAM-4 §10 |
| 16 | CoMem async pipeline | MemAgent WS | 1.4x latency on SWE-Bench | STREAM-4 §20 |
| 17 | CraniMem gated memory | MemAgent WS | Smaller distractor drop | STREAM-4 §15 |
| 18 | Modular compression bounds | MemAgent WS | Formal interference bound proof | STREAM-4 §16 |
| 19 | Gaikwad store routing | MemAgent WS | Oracle > uniform retrieval | STREAM-4 §3 |
| 20 | R-KVHash KV cache | MemAgent WS | 2x decoding throughput | STREAM-4 §6 |
| 21 | Norm-Guided KV eviction | MemAgent WS | Heavy hitter + sliding window | STREAM-4 §9 |
| 22 | Feedback Descent | MemAgent WS | SOTA prompt optimization | STREAM-4 §18 |
| 23 | Curriculum curation | MemAgent WS | ~30% tasks match full-dataset | STREAM-4 §19 |
| 24 | Human-like lifelong memory | MemAgent WS | Cost converges to System 1 | STREAM-4 §23 |
| 25 | LP-RAG link prediction | MemAgent WS | Retrieval as link prediction | STREAM-4 §12 |
| 26 | MemGrad textual gradients | MemAgent WS | Retro+prospective dual memory | STREAM-4 §13 |
| 27 | AOI 3-layer memory | MemAgent WS | 72.4% compression, 94.2% success | STREAM-4 §11 |
| 28 | Memora harmonic memory | arXiv 2026 | RAG/KG as special cases | arXiv:2602.03315 |
| 29 | MGRetrieval reflective ret. | arXiv 2026 | +8.91% F1, +11.11% BLEU-1 | arXiv:2605.27437 |
| 30 | A-Mem Zettelkasten | NeurIPS 2025 | Agent-driven memory linking | STREAM-4 §2 |
| 31 | RMM reflective management | ACL 2025 | >10% over baseline | STREAM-4 §34 |
| 32 | LiCoMemory CogniGraph | ACL ARR 2026 | Semantics/topology decoupling | STREAM-4 §24 |
| 33 | Memory Transplants | MemAgent WS | 15pp gain for weaker models | STREAM-4 §1 |

### Open-Source Repositories

| # | Repository | Contribution | Key Metric | Source |
|---|-----------|-------------|-----------|--------|
| 34 | TencentDB Agent Memory | Mermaid + L0-L3 pyramid | 61.38% token reduction | STREAM-9 §1 |
| 35 | MemPalace | RRF hybrid + temporal KG | 96.6% R@5, zero API calls | STREAM-9 §4 |
| 36 | graphify | Graph-based compression | 71.5x token reduction/query | STREAM-9 §5 |
| 37 | claude-mem | 3-layer search + XML injection | 10x token savings | STREAM-9 §3 |
| 38 | CodeGraph | Pre-indexed code graph | 62% fewer tool calls, 25% cheaper | STREAM-9 §6 |
| 39 | Acontext | Skill-as-memory | Cross-framework portability | STREAM-9 §2 |
| 40 | spaCy | NER + dependency parsing | ~100K tokens/sec, 70+ languages | STREAM-9 §7 |

### Gap Analysis

| # | Document | Key Finding | Priority |
|---|---------|-------------|----------|
| 41 | GAP-ANALYSIS-2026-05-30 §1 | 7 specific memory gaps | CRITICAL |
| 42 | GAP-ANALYSIS-2026-05-30 §1.5 | Autonomous compression trigger missing | HIGH |
| 43 | GAP-ANALYSIS-2026-05-30 §1.6 | Experience compression spectrum missing | MEDIUM |

---

## 10. Risk and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 4-graph split increases retrieval complexity | MED | MED | Policy-guided traversal limits queries to relevant graph; async slow path |
| RecMem threshold calibration | MED | LOW | Conservative initial threshold (0.75), auto-tune via feedback |
| Temporal KG schema migration | HIGH | MED | Dual-write during migration; backward compatibility layer |
| RRF fusion at 10M+ scale | LOW | MED | Hybrid index sharding; approximate RRF via capped candidates |
| Fleet consensus with 100+ agents | MED | MED | Lyra's existing gossip protocol proven; scale test M5 |
| Cross-encoder adds 50-100ms | LOW | LOW | Optional; falls back to RRF-only |
| Multi-hop conflict 7% ceiling | HIGH | HIGH | Provenance + opinion network + SABER stack specifically targets this |

---

*Plan completed 2026-05-30. Incorporates findings from STREAM-4 (36 MemAgent Workshop papers across ICLR 2026, NeurIPS 2025, ACL 2025/2026), STREAM-9 (7 repos deep-analyzed), MEMORY-ARCHITECTURE-V3 (existing 7-tier design), and GAP-ANALYSIS-2026-05-30 (7 specific gaps mapped).*
