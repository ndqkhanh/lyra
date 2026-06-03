# Lyra NeuroMemory Architecture -- Ultra Implementation Plan

**Status:** Ready for Implementation
**Target:** AGI-grade multi-agent memory system
**Research Baseline:** 500+ papers, 80+ repos, MemAgents Workshop @ ICLR 2026
**Document Version:** 1.0 -- May 27, 2026

---

## 1. Executive Summary

Lyra's NeuroMemory Architecture replaces flat vector storage with a 6-layer cognitive memory hierarchy that mirrors human memory organization. The system distinguishes itself from every existing agent memory framework (Mem0, MemGPT, MemOS) through seven breakthrough innovations: (1) **Memory as Action** -- read/write/consolidate/forget are first-class tool calls; (2) **RL-based Memory Controller** -- a learned policy governs what to encode, retrieve, consolidate, and forget; (3) **Atomic Memory Operations** -- fine-grained create/read/update/delete/merge/split/abstract primitives; (4) **Offline Dream Consolidation** -- background memory compression and pattern extraction during idle periods; (5) **Evolutionary Memory Substrate** -- the architecture self-improves through meta-evolution; (6) **Cross-Session Identity** -- persistent agent identity across sessions via lifelong memory; and (7) **Memory Health Monitoring** -- staleness detection, contradiction resolution, hallucination prevention, and confidence calibration. This plan defines the complete architecture, layer-by-layer design, admission control algorithm, async pipeline, consolidation engine, retrieval system, memory health subsystem, 8-week implementation roadmap, API surface, test strategy, and all research references required to build the system.

---

## 2. Architecture Overview

```
+===========================================================================+
|                    LYRA NeuroMemory ARCHITECTURE                           |
|                      6-Layer Cognitive Hierarchy                         |
+===========================================================================+

                         INCOMING STIMULUS (tool calls, user input, events)
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 0: SENSORY BUFFER (seconds–minutes)                           │
│  Streaming token buffer | Attention cache | Working memory scratchpad │
│  Storage: Ring buffer in Redis | Retention: Session-scoped           │
│  Capacity: Last 10 interactions | Eviction: FIFO with importance tags│
└────────────────────────────┬─────────────────────────────────────────┘
                             │ [Memory Admission Control]
                             │ A-MAC 5-factor scoring
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 1: EPISODIC MEMORY (minutes–hours)                            │
│  Session trajectories | Tool call histories | Conversation turns     │
│  Storage: SQLite + JSONB | Retention: Decay-gated (ACT-R activation) │
│  Powered by: MemGPT paging + Agent Workflow Memory patterns          │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ [Consolidation: Light, every 6h]
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 2: SEMANTIC MEMORY (hours–days)                               │
│  Extracted facts | Entity relationships | Domain knowledge           │
│  Storage: Vector DB (Qdrant) + Knowledge Graph (Neo4j)               │
│  Powered by: A-MEM structured knowledge + GAM hierarchical graphs    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ [Consolidation: Deep, daily]
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 3: PROCEDURAL MEMORY (days–weeks)                             │
│  Skill templates | Workflow patterns | Solution strategies           │
│  Storage: Markdown skill files (Acontext-style) + vector index       │
│  Powered by: Agent Workflow Memory + Skill-Memory fusion             │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ [Consolidation: Deep + Pattern extraction]
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 4: META-MEMORY (weeks–months)                                 │
│  Memory about memories | Consolidation policies | Forgetting strategies│
│  Storage: Relational DB (policies table) + Versioned config           │
│  Powered by: MemEvolve + InfMem System-2 control                     │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ [Meta-evolution through RL]
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 5: COLLECTIVE MEMORY (cross-agent, permanent)                  │
│  Shared knowledge graph | Team-level insights | Organizational memory │
│  Storage: Federated graph DB + Git-native Markdown repo              │
│  Powered by: Prism + LatentMem + Federation patterns                 │
└──────────────────────────────────────────────────────────────────────┘

                        VERTICAL SUBSYSTEMS (span all layers):
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐
│ Memory        │  │ Async Memory  │  │ Consolidation │  │ Memory       │
│ Admission     │  │ Pipeline      │  │ Engine        │  │ Health       │
│ Control       │  │ (CoMem-style) │  │ (Free-energy) │  │ Monitor      │
│ (A-MAC 5-fct) │  │               │  │               │  │              │
└───────────────┘  └───────────────┘  └───────────────┘  └──────────────┘
```

**Data Flow Summary:**

```
Sensory Buffer → [Admission Gate] → Episodic → [Light Consolidation (6h)]
  → Semantic → [Deep Consolidation (daily)] → Procedural
  → [Pattern Extraction] → Meta-Memory → [Policy updates] → Collective
```

**Key data flow paths:**
- **Write path:** Incoming stimulus enters L0, passes through A-MAC admission gate, is encoded into L1 with metadata, and is queued for async consolidation
- **Read path:** Queries trigger System 1 (fast associative, <50ms) or System 2 (deliberate graph traversal, <200ms) retrieval depending on query type
- **Consolidation path:** Scheduled jobs (light: 6h, deep: daily at 03:00 UTC) compress L1→L2→L3, extract patterns, update meta-policies, and federate to collective store

---

## 3. Layer-by-Layer Design

### 3.1 Layer 0: Sensory Buffer

| Property | Detail |
|----------|--------|
| **Purpose** | Raw I/O buffer; captures all incoming tool calls, user messages, and system events before filtering |
| **Storage Mechanism** | Ring buffer in Redis (key: `sensory:{session_id}`); fixed size of 10 entries |
| **Retention Policy** | Session-scoped; flushed on session end (pinned items promoted to L1) |
| **Retrieval Strategy** | Direct index access (no search needed); most recent N items surfaced to active context |
| **Eviction** | FIFO with importance-aware exceptions: items scoring >0.8 on A-MAC are pinned |
| **Implementation** | Redis LIST with `LPUSH`/`LTRIM`; Python `dataclass` wrapper |

```python
# Layer 0: Sensory Buffer
@dataclass
class SensoryEntry:
    id: str                          # UUID
    session_id: str
    content: str                     # Raw text / tool call JSON
    entry_type: Literal["user_msg", "tool_call", "tool_result", "system_event"]
    timestamp: float
    importance_hint: float           # Initial rough score from lightweight classifier
    pinned: bool = False             # Set true if importance_hint > 0.8

class SensoryBuffer:
    def __init__(self, redis_client, max_entries: int = 10):
        self.redis = redis_client
        self.max_entries = max_entries

    def push(self, entry: SensoryEntry) -> None:
        key = f"sensory:{entry.session_id}"
        self.redis.lpush(key, entry.to_json())
        self.redis.ltrim(key, 0, self.max_entries - 1)

    def get_window(self, session_id: str, n: int = 10) -> list[SensoryEntry]:
        key = f"sensory:{session_id}"
        raw = self.redis.lrange(key, 0, n - 1)
        return [SensoryEntry.from_json(r) for r in raw]

    def flush_promotable(self, session_id: str, threshold: float = 0.8) -> list[SensoryEntry]:
        """Return entries above threshold for promotion to L1."""
        entries = self.get_window(session_id)
        return [e for e in entries if e.importance_hint >= threshold or e.pinned]
```

### 3.2 Layer 1: Episodic Memory

| Property | Detail |
|----------|--------|
| **Purpose** | Complete session trajectories, tool call histories, conversation turns with full context |
| **Storage Mechanism** | SQLite with JSONB column for flexible metadata; partitioned by `session_id` and `week` |
| **Retention Policy** | ACT-R decay-gated: memories drop below retrieval threshold after ~30 days unless retrieved |
| **Retrieval Strategy** | Session-scoped sequential access + time-range queries + BM25 text search |
| **Implementation** | SQLite WAL mode for concurrent reads; chunked storage (3k token blocks, MemGPT-style) |

```python
# Layer 1: Episodic Memory
@dataclass
class Episode:
    id: str
    session_id: str
    chunk_index: int                # Position in the session sequence
    content: str                    # ≤3072 tokens per chunk
    content_hash: str               # SHA-256 for dedup
    a_mac_score: float              # 5-factor admission score
    activation: float               # ACT-R base-level activation
    retrieval_history: list[float]  # List of timestamps when retrieved
    created_at: float
    tags: list[str]
    metadata: dict                  # Flexible: model used, tool calls, task type

class EpisodicStore:
    def store(self, episode: Episode) -> str:
        """Insert episode; trigger async admission scoring if score missing."""
        if episode.a_mac_score == 0.0:
            episode.a_mac_score = self._async_admission_score(episode)
        episode.activation = self._initial_activation(episode.a_mac_score)
        return self.db.insert("episodes", episode.to_dict())

    def retrieve_session(self, session_id: str) -> list[Episode]:
        """Return all chunks for a session, ordered by chunk_index."""
        return self.db.query(
            "SELECT * FROM episodes WHERE session_id = ? ORDER BY chunk_index",
            (session_id,)
        )

    def retrieve_by_timerange(self, start: float, end: float, limit: int = 50) -> list[Episode]:
        return self.db.query(
            "SELECT * FROM episodes WHERE created_at BETWEEN ? AND ? "
            "AND activation > ? ORDER BY activation DESC LIMIT ?",
            (start, end, RETRIEVAL_THRESHOLD, limit)
        )

    def _initial_activation(self, a_mac_score: float) -> float:
        """Map A-MAC score to initial activation (log scale)."""
        return math.log(max(a_mac_score, 0.01)) + 2.0
```

### 3.3 Layer 2: Semantic Memory

| Property | Detail |
|----------|--------|
| **Purpose** | Extracted facts, entity relationships, domain knowledge -- the agent's "encyclopedia" |
| **Storage Mechanism** | Dual-store: Qdrant (vector embeddings, `text-embedding-3-large`) + Neo4j (knowledge graph) |
| **Retention Policy** | Slow decay (half-life: 90 days); major versioning; contradiction-tagged not deleted |
| **Retrieval Strategy** | Graph-based: LP-RAG link prediction for multi-hop queries; hybrid (semantic + graph) |
| **Implementation** | GAM-inspired hierarchical graph with confidence-tagged edges (Graphify-style) |

```python
# Layer 2: Semantic Memory -- Graph Node & Edge definitions
@dataclass
class SemanticNode:
    id: str
    label: str                      # Entity, Concept, Fact, DomainRule
    content: str                    # Embedding text
    embedding: list[float] | None   # Lazy-loaded from Qdrant
    confidence: float               # 0.0–1.0
    source_episodes: list[str]      # Traceability: episode IDs that produced this node
    created_at: float
    last_updated: float
    version: int

@dataclass
class SemanticEdge:
    source_id: str
    target_id: str
    relation: str                   # IS_A, PART_OF, CAUSES, RELATED_TO, CONTRADICTS
    confidence: float               # 0.0–1.0
    tag: Literal["EXTRACTED", "INFERRED", "AMBIGUOUS"]  # Graphify-style confidence tier
    evidence: list[str]             # Episode IDs or node IDs supporting this edge
```

**Graph Retrieval (LP-RAG-inspired):**

```python
class SemanticRetriever:
    def retrieve(self, query: str, k: int = 20) -> list[SemanticNode]:
        # Phase 1: Vector search for seed nodes
        query_embedding = self.embed(query)
        seeds = self.qdrant.search(query_embedding, limit=k)

        # Phase 2: Link prediction for graph expansion
        expanded = []
        for seed in seeds:
            predicted_links = self.link_predictor.predict_links(seed.id, top_n=5)
            for link in predicted_links:
                if link.confidence > 0.7:
                    neighbor = self.graph.get_node(link.target_id)
                    if neighbor:
                        expanded.append(neighbor)

        # Phase 3: Rank by combined score
        all_candidates = seeds + expanded
        for node in all_candidates:
            node.retrieval_score = (
                0.4 * self._semantic_sim(node, query_embedding) +
                0.3 * node.confidence +
                0.2 * self._graph_centrality(node.id) +
                0.1 * self._recency_boost(node)
            )

        return sorted(all_candidates, key=lambda n: n.retrieval_score, reverse=True)[:k]
```

### 3.4 Layer 3: Procedural Memory

| Property | Detail |
|----------|--------|
| **Purpose** | Reusable skill templates, workflow patterns, solution strategies, debugging protocols |
| **Storage Mechanism** | Markdown skill files (Acontext-style, git-friendly) + vector index for fast lookup |
| **Retention Policy** | Versioned; deprecated skills archived after 90 days unused; validated skills permanent |
| **Retrieval Strategy** | Tool-call-based retrieval (`get_skill`, `list_skills`); progressive disclosure |
| **Implementation** | Filesystem directory `~/.lyra/memory/procedural/` + Qdrant collection for search |

```python
# Layer 3: Procedural Memory -- Skill Template
@dataclass
class SkillTemplate:
    id: str
    name: str                       # e.g., "code-review", "debug-python"
    version: int
    content: str                    # Markdown body with steps, preconditions, postconditions
    schema_version: str             # Schema-defined structure (Acontext pattern)
    usage_count: int                # Retrieval-based strengthening
    success_rate: float             # Tracked via verification loop
    last_used: float
    created_at: float
    source_sessions: list[str]      # Sessions that produced/refined this skill
    supersedes: str | None          # Previous version ID
    status: Literal["active", "deprecated", "validated"]
```

### 3.5 Layer 4: Meta-Memory

| Property | Detail |
|----------|--------|
| **Purpose** | Memory about memories: consolidation policies, decay parameters, forgetting strategies |
| **Storage Mechanism** | Relational DB (`meta_memory` table) + versioned JSON config files |
| **Retention Policy** | Policy versions retained indefinitely; audit log of all policy changes |
| **Retrieval Strategy** | Direct policy lookup by memory type/layer; RL-policy inference for dynamic decisions |
| **Implementation** | InfMem System-2 control: learned memory policies evaluated before each memory operation |

```python
# Layer 4: Meta-Memory -- Policy Definitions
@dataclass
class ConsolidationPolicy:
    id: str
    layer: int                      # Target layer (1–5)
    trigger: str                    # "scheduled", "threshold", "event"
    schedule_cron: str | None       # e.g., "0 */6 * * *" for light, "0 3 * * *" for deep
    threshold_pct: float | None     # Storage % that triggers consolidation
    strategy: str                   # "merge_duplicates", "extract_patterns", "compress", "abstract"
    parameters: dict                # Strategy-specific params: similarity_threshold, max_abstractions
    version: int
    performance_score: float        # Updated by RL controller after each consolidation
    created_at: float

@dataclass
class DecayPolicy:
    id: str
    layer: int
    decay_rate: float               # ACT-R d parameter per layer
    retrieval_threshold: float      # Activation level below which memory is inaccessible
    importance_weight: float        # β in activation formula
    version: int
```

### 3.6 Layer 5: Collective Memory

| Property | Detail |
|----------|--------|
| **Purpose** | Shared knowledge across agent instances; team-level insights; organizational memory |
| **Storage Mechanism** | Federated Neo4j cluster + Git-native Markdown repo (Graphify union-merge pattern) |
| **Retention Policy** | Permanent; access-controlled; owner-agent maintains write authority |
| **Retrieval Strategy** | Federated graph query with agent-scoped filtering; community-detection (Leiden) for clustering |
| **Implementation** | Graphify-style git-aware merge: parallel agent contributions union-merged on write |

```python
# Layer 5: Collective Memory -- Federation
@dataclass
class CollectiveNode:
    id: str
    source_agent_id: str            # Which agent contributed this
    source_layer: int               # Which layer in source agent's hierarchy
    content: str
    embedding: list[float] | None
    access_scope: Literal["team", "organization", "public"]
    community_id: str | None        # Leiden community detection result
    federated_at: float
    version: int
    merge_parent: str | None        # Git-merge lineage
```

---

## 4. Memory Admission Control (A-MAC Inspired)

The A-MAC (Adaptive Memory Admission Control) system determines whether each incoming stimulus should be encoded into persistent memory or discarded. It uses a 5-factor scoring model:

### 4.1 Five-Factor Scoring Model

| Factor | Weight | Description |
|--------|--------|-------------|
| **Utility** (U) | 0.30 | Task relevance -- does this information contribute to goal completion? |
| **Confidence** (C) | 0.25 | Source reliability -- how certain is the agent about this information? |
| **Novelty** (N) | 0.20 | Information gain -- is this new information or a duplicate? |
| **Recency** (R) | 0.15 | Temporal proximity -- relevance decays with time (power law) |
| **Type Prior** (T) | 0.10 | Category baseline -- user preferences > facts > casual chat > greetings |

### 4.2 Scoring Algorithm

```python
class AMACAdmissionController:
    """
    A-MAC 5-factor memory admission scoring.
    Target: F1 >= 0.583 on LoCoMo admission decisions (A-MAC paper baseline).
    """

    FACTOR_WEIGHTS = {
        "utility": 0.30,
        "confidence": 0.25,
        "novelty": 0.20,
        "recency": 0.15,
        "type_prior": 0.10,
    }

    TYPE_PRIORS = {
        "user_preference": 0.95,
        "factual_knowledge": 0.80,
        "task_outcome": 0.75,
        "tool_result": 0.60,
        "casual_conversation": 0.30,
        "greeting": 0.05,
    }

    ADMISSION_THRESHOLD = 0.45  # Below this, discard

    def score(self, entry: SensoryEntry, context: dict) -> float:
        """
        Compute composite admission score.

        Returns:
            float: 0.0–1.0 score. Scores >= 0.45 → admit to L1.
                           Scores >= 0.80 → pin in L0.
        """
        utility = self._compute_utility(entry, context)
        confidence = self._compute_confidence(entry)
        novelty = self._compute_novelty(entry)
        recency = self._compute_recency(entry)
        type_prior = self._compute_type_prior(entry)

        score = (
            self.FACTOR_WEIGHTS["utility"] * utility +
            self.FACTOR_WEIGHTS["confidence"] * confidence +
            self.FACTOR_WEIGHTS["novelty"] * novelty +
            self.FACTOR_WEIGHTS["recency"] * recency +
            self.FACTOR_WEIGHTS["type_prior"] * type_prior
        )

        return clamp(score, 0.0, 1.0)

    def _compute_utility(self, entry: SensoryEntry, context: dict) -> float:
        """
        Utility = task relevance.
        - If entry is a tool result from an active goal step → high utility
        - If entry is user feedback on agent output → high utility
        - If entry is a greeting → low utility
        Uses lightweight LLM classifier (3-shot, ~50 tokens).
        """
        prompt = f"""Rate task utility (0-1) for this agent input:
Goal: {context.get('active_goal', 'None')}
Content: {entry.content[:200]}
Rating:"""
        return self._llm_score(prompt)

    def _compute_confidence(self, entry: SensoryEntry) -> float:
        """
        Confidence = source reliability.
        - Tool results from verified sources → 0.9
        - Tool results from unverified sources → 0.5
        - User statements → 0.85
        - Agent inferences → 0.6
        """
        source_confidence = {
            "tool_result": self._tool_source_confidence(entry),
            "user_msg": 0.85,
            "system_event": 0.95,
            "tool_call": 0.6,
        }
        return source_confidence.get(entry.entry_type, 0.5)

    def _compute_novelty(self, entry: SensoryEntry) -> float:
        """
        Novelty = 1.0 - cosine_similarity(entry_embedding, nearest_existing_memory).
        Near-duplicates (sim > 0.95) get novelty ≈ 0.05 → near-zero admission boost.
        """
        embedding = self.embed(entry.content)
        nearest = self.vector_store.search(embedding, top_k=1)
        if not nearest or nearest[0].score < 0.3:
            return 1.0  # Completely novel
        return 1.0 - nearest[0].score

    def _compute_recency(self, entry: SensoryEntry) -> float:
        """
        Recency = power-law decay from creation time.
        R(t) = (t_0 / t)^d where d=0.5, t_0 = 60s (reference time).
        """
        age_seconds = time.time() - entry.timestamp
        t0 = 60.0  # Reference: 1 minute
        return (t0 / max(age_seconds, t0)) ** 0.5

    def _compute_type_prior(self, entry: SensoryEntry) -> float:
        """Look up baseline importance by memory category."""
        category = self._classify_category(entry.content)
        return self.TYPE_PRIORS.get(category, 0.5)

    def should_admit(self, score: float) -> tuple[bool, str]:
        """
        Decision logic:
         - score >= 0.80 → ADMIT (pinned)
         - 0.45 <= score < 0.80 → ADMIT (standard)
         - score < 0.45 → DISCARD
        """
        if score >= 0.80:
            return True, "pinned"
        elif score >= self.ADMISSION_THRESHOLD:
            return True, "standard"
        else:
            return False, "discarded"
```

### 4.3 Admission Pipeline

```
SensoryEntry → [Lightweight Classifier] → category label
  → [5-factor scorer] → composite score
  → [Threshold gate]:
       >= 0.80: PIN to L0 + ADMIT to L1
       0.45–0.80: ADMIT to L1
       < 0.45: DISCARD (log only for audit)
  → [Async Encoder]: admitted entries queued for L1 encoding
```

---

## 5. Async Memory Pipeline (CoMem-Inspired)

The CoMem (Decoupled Memory) architecture separates memory I/O from the agent's critical path. This prevents memory operations from blocking agent actions and achieves latency improvements of 1.4x through n-step-off design.

### 5.1 Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    CO-MEM ASYNC PIPELINE                          │
│                    n-Step-Off Design                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Agent Critical Path]              [Memory Pipeline]             │
│  ─────────────────────              ─────────────────             │
│                                                                    │
│  Tool Call → Execute → Result                                     │
│       │                          ┌─────────────────────┐          │
│       │                          │  Step 1: Admission  │          │
│       └──── async dispatch ─────▶│  (A-MAC scoring)    │          │
│                                  └────────┬────────────┘          │
│                                           │                       │
│                                  ┌────────▼────────────┐          │
│                                  │  Step 2: Encoder    │          │
│                                  │  (embed + chunk)    │          │
│                                  └────────┬────────────┘          │
│                                           │                       │
│                                  ┌────────▼────────────┐          │
│                                  │  Step 3: Index      │          │
│                                  │  (Qdrant + Neo4j)   │          │
│                                  └────────┬────────────┘          │
│                                           │                       │
│                                  ┌────────▼────────────┐          │
│                                  │  Step 4: Graph Link │          │
│                                  │  (edge extraction)  │          │
│                                  └────────┬────────────┘          │
│                                           │                       │
│                                  ┌────────▼────────────┐          │
│                                  │  Step 5: Consol. Q  │          │
│                                  │  (schedule trigger) │          │
│                                  └─────────────────────┘          │
│                                                                    │
│  Agent continues execution       Memory ops complete              │
│  without waiting (n-step-off)    within n steps                   │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Implementation

```python
import asyncio
from dataclasses import dataclass, field
from collections import deque

@dataclass
class MemoryPipelineTask:
    entry: SensoryEntry
    context: dict
    status: Literal["pending", "scoring", "encoding", "indexing", "linking", "done", "failed"]
    score: float | None = None
    error: str | None = None

class CoMemAsyncPipeline:
    """
    Decoupled async memory pipeline with n-step-off design.
    Agent continues execution; memory ops complete within n steps.
    Target: 1.4x latency improvement (CoMem paper baseline).
    """

    def __init__(self, n_step_off: int = 3):
        self.n_step_off = n_step_off
        self.admission_controller = AMACAdmissionController()
        self.task_queue: asyncio.Queue[MemoryPipelineTask] = asyncio.Queue()
        self.completion_registry: dict[str, MemoryPipelineTask] = {}
        self.recent_tasks: deque[MemoryPipelineTask] = deque(maxlen=100)

    async def dispatch(self, entry: SensoryEntry, context: dict) -> str:
        """
        Non-blocking dispatch. Returns task_id immediately.
        Agent does NOT wait for completion.
        """
        task = MemoryPipelineTask(entry=entry, context=context, status="pending")
        self.completion_registry[task.entry.id] = task
        await self.task_queue.put(task)
        return task.entry.id

    async def check_status(self, task_id: str) -> str:
        """Agent polls this to confirm memory was stored (optional)."""
        task = self.completion_registry.get(task_id)
        return task.status if task else "unknown"

    async def run(self):
        """Background worker: processes pipeline stages."""
        while True:
            task = await self.task_queue.get()

            try:
                # Step 1: Admission scoring (synchronous, lightweight)
                task.status = "scoring"
                task.score = await asyncio.to_thread(
                    self.admission_controller.score, task.entry, task.context
                )
                if not self.admission_controller.should_admit(task.score)[0]:
                    task.status = "done"
                    continue

                # Step 2: Encode (embedding generation)
                task.status = "encoding"
                embedding = await self._encode(task.entry.content)

                # Step 3: Index (non-blocking vector store write)
                task.status = "indexing"
                await self._index(task.entry, embedding)

                # Step 4: Graph linking (async edge extraction)
                task.status = "linking"
                await self._extract_and_link(task.entry)

                # Step 5: Consolidation trigger check
                await self._check_consolidation_trigger()

                task.status = "done"

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            finally:
                self.recent_tasks.append(task)
                self.task_queue.task_done()

    async def _encode(self, content: str) -> list[float]:
        """Generate embedding vector (offloaded to thread)."""
        return await asyncio.to_thread(self.embedder.embed, content)

    async def _index(self, entry: SensoryEntry, embedding: list[float]):
        """Write to Qdrant collection; non-blocking."""
        await self.qdrant.upsert_async(
            collection_name="episodic",
            points=[{
                "id": entry.id,
                "vector": embedding,
                "payload": {"session_id": entry.session_id, "timestamp": entry.timestamp}
            }]
        )

    async def _extract_and_link(self, entry: SensoryEntry):
        """LLM-powered edge extraction against knowledge graph."""
        edges = await self._llm_extract_edges(entry.content)
        for edge in edges:
            await self.graph.create_edge(edge)

    async def _check_consolidation_trigger(self):
        """If storage > 85%, signal consolidation engine."""
        usage_pct = await self._get_storage_usage()
        if usage_pct > 85:
            await self.consolidation_engine.signal_consolidation("threshold")
```

---

## 6. Consolidation Engine (Free-Energy Minimization + Auto-Dreamer)

The consolidation engine performs offline memory processing using principles from the Free Energy Principle (entropic memory) and Auto-Dreamer's GRPO-trained consolidation.

### 6.1 Consolidation Modes

| Mode | Frequency | Duration | Operations |
|------|----------|----------|------------|
| **Light** | Every 6 hours | 2–5 min | Deduplication, contradiction tagging, edge refresh |
| **Deep** | Daily (03:00 UTC) | 10–30 min | Pattern extraction, abstraction, cross-session learning, memory compression |
| **Scheduled Replay** | During deep consolidation | Variable | Hippocampal replay: reactivate high-value trajectory sequences |
| **Emergency** | On threshold (85% storage) | As needed | Aggressive pruning of low-activation memories |

### 6.2 Free-Energy Consolidation Algorithm

Entropic Memory uses free-energy minimization to control consolidation temperature. At low "temperature," the system is conservative (keeps more details). At high temperature, it aggressively compresses and abstracts.

```python
class FreeEnergyConsolidator:
    """
    Entropic Memory consolidation via free-energy minimization.
    Temperature-controlled: low T → conservative, high T → aggressive.
    Result: +15% memory survival at 50% noise (Entropic Memory paper).
    """

    def __init__(self, base_temperature: float = 1.0):
        self.temperature = base_temperature  # T: controls consolidation aggressiveness
        self.param_beta = 0.5                # Inverse temperature for energy landscape

    def compute_free_energy(self, memory_set: list[Episode]) -> float:
        """
        F = E - T * S
        E = expected reconstruction error (how well can we reconstruct original from compressed)
        S = entropy of the compressed representation (higher = more abstract)
        T = temperature (higher T favors compression)
        """
        energy = self._reconstruction_error(memory_set)
        entropy = self._compression_entropy(memory_set)
        return energy - self.temperature * entropy

    def consolidate(self, episodes: list[Episode]) -> list[Episode]:
        """
        Find consolidation configuration that minimizes free energy.
        Returns set of consolidated episodes.
        """
        best_config = None
        best_energy = float("inf")

        # Candidate consolidation strategies
        strategies = ["merge", "summarize", "abstract", "cluster", "keep"]

        for strategy in strategies:
            candidate = self._apply_strategy(episodes, strategy)
            energy = self.compute_free_energy(candidate)
            if energy < best_energy:
                best_energy = energy
                best_config = candidate

        return best_config

    def update_temperature(self, storage_usage_pct: float, retrieval_precision: float):
        """
        Adaptive temperature:
        - High storage usage → raise T (more aggressive compression)
        - Low retrieval precision → lower T (keep more detail)
        """
        if storage_usage_pct > 85:
            self.temperature = min(self.temperature * 1.2, 5.0)
        elif retrieval_precision < 0.85:
            self.temperature = max(self.temperature * 0.8, 0.5)
        else:
            self.temperature = max(self.temperature * 0.95, 0.5)

    def _reconstruction_error(self, memory_set: list[Episode]) -> float:
        """Expected information loss from consolidation."""
        # Higher when we merge/compress → lose detail
        strategy_loss = {
            "keep": 0.0, "merge": 0.1, "summarize": 0.2,
            "abstract": 0.3, "cluster": 0.25
        }
        return sum(strategy_loss.get(e.consolidation_strategy, 0.2) for e in memory_set)

    def _compression_entropy(self, memory_set: list[Episode]) -> float:
        """Information density of the compressed form."""
        return -sum(p * math.log(p) for p in self._token_distribution(memory_set) if p > 0)


class DreamConsolidator(FreeEnergyConsolidator):
    """
    Auto-Dreamer offline consolidation with GRPO-trained policy.
    Decouples fast online acquisition from slow offline consolidation.
    """

    def dream_phase(self, recent_episodes: list[Episode]):
        """
        1. Read memory regions from recent sessions
        2. Inspect trajectories for success/failure patterns
        3. Synthesize compressed replacements using GRPO-trained policy
        4. Write compressed memories back, linking to originals
        """
        # Partition episodes by session
        sessions = self._group_by_session(recent_episodes)

        for session_id, episodes in sessions.items():
            # Read memory region (L1 chunks for this session)
            trajectory = self._reconstruct_trajectory(episodes)

            # Inspect: identify outcome signal
            outcome = self._detect_outcome(trajectory)
            success = outcome.get("success", False)

            # Synthesize: compressed replacement via GRPO policy
            compressed = self._grpo_synthesize(
                trajectory,
                reward_signal=1.0 if success else -0.5
            )

            # Store compressed + link to originals
            compressed_id = self.store(compressed)
            for episode in episodes:
                self.link(episode.id, compressed_id, relation="COMPRESSED_TO")

    def _grpo_synthesize(self, trajectory: list[Episode], reward_signal: float) -> Episode:
        """
        Group Relative Policy Optimization synthesis.
        Generates compressed episode that maximizes expected task performance.
        """
        prompt = self._build_compression_prompt(trajectory)
        candidates = self.llm.generate_n(prompt, n=4)

        # Evaluate each candidate against reward model
        best_candidate = max(candidates, key=lambda c: self._estimate_reward(c, reward_signal))

        return best_candidate
```

### 6.3 Scheduled Replay (Hippocampal Replay)

```python
class ScheduledReplay:
    """
    Hippocampal replay during consolidation.
    Reactivates high-value trajectory sequences to strengthen learning.
    """

    def select_replay_candidates(self, episodes: list[Episode], top_k: int = 10) -> list[list[Episode]]:
        """Select trajectory sequences most worth replaying."""
        # Score each contiguous sequence by:
        # - Outcome magnitude (strong success/failure > neutral)
        # - Novelty of pattern (not previously replayed)
        # - Current activation (decayed memories benefit more from replay)
        sequences = self._extract_sequences(episodes, min_length=3)

        scored = []
        for seq in sequences:
            outcome_magnitude = abs(self._outcome_score(seq))
            novelty = 1.0 - self._replay_similarity(seq)
            activation_need = max(0, 1.0 - self._mean_activation(seq))

            replay_score = (
                0.4 * outcome_magnitude +
                0.3 * novelty +
                0.3 * activation_need
            )
            scored.append((seq, replay_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [seq for seq, _ in scored[:top_k]]
```

---

## 7. Retrieval System: Dual-Process + Reconstruction

### 7.1 System 1 (Fast Associative, <50ms)

```python
class System1Retriever:
    """
    Fast, associative retrieval. No LLM calls. Pure vector + BM25 hybrid.
    Inspired by: Human System 1 thinking (Kahneman), Human-Like Lifelong Memory valence vectors.
    Target latency: <50ms p95.
    """

    def retrieve(self, query: str, k: int = 20) -> list[MemoryResult]:
        # Parallel retrieval across active memory stores
        vector_results = self.qdrant.search(query_embedding, limit=k)
        bm25_results = self.sqlite.bm25_search(query, limit=k)

        # Reciprocal rank fusion
        return self._rrf_merge(vector_results, bm25_results, k=k)

    def _rrf_merge(self, list_a: list, list_b: list, k: int = 20, rrf_k: int = 60) -> list:
        """Reciprocal Rank Fusion for hybrid result merging."""
        scores = {}
        for rank, item in enumerate(list_a):
            scores[item.id] = scores.get(item.id, 0) + 1.0 / (rrf_k + rank + 1)
        for rank, item in enumerate(list_b):
            scores[item.id] = scores.get(item.id, 0) + 1.0 / (rrf_k + rank + 1)

        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:k]
        return [self._get_by_id(id) for id in sorted_ids]
```

### 7.2 System 2 (Deliberate Graph Traversal, <200ms)

```python
class System2Retriever:
    """
    Deliberate, multi-hop graph traversal with LLM orchestration.
    MRAgent-inspired: "Memory is reconstructed, not retrieved."
    Uses Cue-Tag-Content associative graph with iterative pruning.
    Target latency: <200ms p95.
    """

    def retrieve(self, query: str, context: dict, max_hops: int = 3) -> list[MemoryResult]:
        # Step 1: Extract cue from query
        cue = self._extract_cue(query)  # LLM: 1-token classification

        # Step 2: Retrieve seed nodes from graph
        seeds = self.graph.traverse_cue(cue, max_depth=1)

        # Step 3: Multi-hop expansion with iterative pruning
        all_nodes = set(seeds)
        for hop in range(max_hops):
            neighbors = set()
            for node in list(all_nodes):
                edges = self.graph.get_outgoing(node.id, relation_filter=self._hop_filter(hop))
                for edge in edges:
                    # LP-RAG link prediction: score edge relevance to query
                    relevance = self.link_predictor.score(edge, query)
                    if relevance > 0.6:
                        neighbor = self.graph.get_node(edge.target_id)
                        if neighbor:
                            neighbors.add(neighbor)

            # Iterative pruning: remove nodes that decrease coherence
            all_nodes = self._prune_iteratively(all_nodes | neighbors, query)

        # Step 4: Reconstruct memory from node set (MRAgent-style)
        reconstructed = self._reconstruct_from_nodes(list(all_nodes), query)

        # Sort by activation level
        return sorted(reconstructed, key=lambda m: m.activation, reverse=True)

    def _prune_iteratively(self, nodes: set, query: str) -> set:
        """
        MRAgent pruning: remove nodes that decrease answer coherence.
        Repeat until convergence or min_nodes reached.
        """
        min_nodes = 3
        while len(nodes) > min_nodes * 2:
            # Score each node's contribution to answer quality
            scores = {}
            for node in nodes:
                score_with = self._estimate_answer_quality(nodes, query)
                score_without = self._estimate_answer_quality(nodes - {node}, query)
                scores[node.id] = score_with - score_without  # Marginal contribution

            # Remove bottom 20% of contributors
            sorted_scores = sorted(scores.items(), key=lambda x: x[1])
            cutoff = int(len(sorted_scores) * 0.2)
            for node_id, _ in sorted_scores[:cutoff]:
                nodes = {n for n in nodes if n.id != node_id}

            if len(nodes) <= min_nodes:
                break

        return nodes
```

### 7.3 LP-RAG Graph-Based Retrieval

```python
class LPRAGRetriever:
    """
    Link Prediction RAG: graph-based retrieval that predicts links between query
    concepts and stored memories. Outperforms flat vector search on multi-hop
    and temporal reasoning queries.
    """

    def retrieve(self, query: str, k: int = 20) -> list[MemoryResult]:
        # Phase 1: Extract entities from query
        entities = self._extract_entities(query)

        # Phase 2: Seed nodes from entity match
        seeds = []
        for entity in entities:
            matches = self.graph.find_nodes(label=entity.type, content_contains=entity.text)
            seeds.extend(matches)

        # Phase 3: Link prediction -- score all edges from seeds
        candidates = set()
        for seed in seeds:
            predicted = self.link_predictor.predict_top_k(seed.id, k=5)
            for pred in predicted:
                if pred.score > 0.7:
                    target = self.graph.get_node(pred.target_id)
                    if target:
                        candidates.add(target)

        # Phase 4: Rank by graph centrality + semantic similarity
        results = list(candidates)
        for r in results:
            r.graph_score = (
                0.5 * self._pagerank_centrality(r.id) +
                0.3 * self._semantic_similarity(r, query) +
                0.2 * self._community_relevance(r.community_id, query)
            )

        return sorted(results, key=lambda r: r.graph_score, reverse=True)[:k]
```

---

## 8. Memory Health Monitoring

### 8.1 Health Dimensions

| Dimension | Metric | Alert Threshold | Resolution Strategy |
|-----------|--------|-----------------|---------------------|
| **Staleness** | Days since last access | >30 days | Flag for consolidation review; increase decay rate |
| **Contradiction** | Number of CONTRADICTS edges | >0 per fact cluster | Resolve via recency + importance + confidence |
| **Hallucination** | Low-confidence facts with high retrieval frequency | confidence < 0.5 AND access_count > 5 | Downgrade confidence; add AMBIGUOUS tag; surface for verification |
| **Confidence Drift** | Change in fact confidence over time | >0.3 swing in 7 days | Trigger verification loop; re-score against evidence |
| **Retrieval Precision** | % of retrieved memories relevant to query | <0.85 | Adjust retrieval ranking weights; lower System 2 pruning aggressiveness |
| **Storage Saturation** | % of allocated storage used | >85% | Trigger consolidation; if >95%, trigger emergency archival |

### 8.2 Contradiction Resolution

```python
class ContradictionResolver:
    """
    Resolves contradictory memories using a weighted scoring model.
    Priority: recency > importance > confidence > source reliability.
    """

    def resolve(self, fact_a: SemanticNode, fact_b: SemanticNode) -> dict:
        """
        Compare two contradictory facts and determine the winner.
        Loser is tagged as 'superseded' but NOT deleted (auditability).
        """
        score_a = self._resolution_score(fact_a)
        score_b = self._resolution_score(fact_b)

        if score_a > score_b:
            winner, loser = fact_a, fact_b
        else:
            winner, loser = fact_b, fact_a

        # Create CONTRADICTS edge with resolution metadata
        self.graph.create_edge(SemanticEdge(
            source_id=winner.id,
            target_id=loser.id,
            relation="SUPERSEDES",
            confidence=abs(score_a - score_b) / max(score_a, score_b),
            tag="EXTRACTED",
            evidence=[f"Resolution at {time.time()}: winner score {max(score_a, score_b)} vs loser {min(score_a, score_b)}"]
        ))

        loser.status = "superseded"
        loser.superseded_by = winner.id

        return {"winner": winner.id, "loser": loser.id, "resolution_confidence": abs(score_a - score_b)}

    def _resolution_score(self, fact: SemanticNode) -> float:
        """Weighted resolution score: recency > importance > confidence."""
        age_days = (time.time() - fact.created_at) / 86400
        return (
            0.40 * max(0, 1.0 - age_days / 90) +  # Recency (90-day window)
            0.30 * fact.confidence +                 # Confidence
            0.20 * self._source_reliability(fact) +  # Source reliability
            0.10 * self._num_supporting_episodes(fact)  # Evidential support
        )
```

### 8.3 Hallucination Prevention

```python
class HallucinationGuard:
    """
    Prevents memory hallucination through confidence calibration and
    evidence verification.
    """

    def verify_fact(self, fact: SemanticNode) -> float:
        """
        Verify a fact against supporting evidence.
        Returns calibrated confidence score.
        """
        supporting_episodes = self._get_source_episodes(fact.source_episodes)
        contradicting_episodes = self._find_contradictions(fact)

        # Calculate verification score
        support_strength = len(supporting_episodes) * 0.15
        contradiction_penalty = len(contradicting_episodes) * 0.25

        calibrated = clamp(fact.confidence + support_strength - contradiction_penalty, 0.0, 1.0)

        # If confidence drops below threshold, mark as AMBIGUOUS
        if calibrated < 0.5:
            fact.confidence_tag = "AMBIGUOUS"
            self._flag_for_human_review(fact.id)

        return calibrated

    def prevent_injection(self, new_fact: SemanticNode, existing_facts: list[SemanticNode]) -> bool:
        """
        Check if a new fact contradicts well-established knowledge.
        Blocks injection if contradiction with high-confidence (>0.8) fact.
        """
        for existing in existing_facts:
            if existing.confidence > 0.8:
                contradiction = self._detect_contradiction(new_fact, existing)
                if contradiction.score > 0.9:
                    # High-confidence contradiction detected → BLOCK
                    self._log_contradiction_event(new_fact, existing)
                    return False
        return True
```

---

## 9. Implementation Phases (8 Weeks)

### Week 1-2: Foundation Layer

| Day | Task | Deliverable | Dependencies |
|-----|------|------------|--------------|
| 1-2 | Define data schemas for L0–L5 | SQLAlchemy models, Redis schema | None |
| 3-4 | Implement Layer 0 (Sensory Buffer) | `SensoryBuffer` class + Redis ops | Redis instance |
| 5-6 | Implement Layer 1 (Episodic Store) | `EpisodicStore` with chunked storage | SQLite schema |
| 7-8 | Implement A-MAC admission controller | `AMACAdmissionController` with 5-factor scoring | L0, L1 |
| 9-10 | Write unit tests for L0, L1, A-MAC | 80%+ coverage | Implementation |
| 11-12 | Integration test: L0 → A-MAC → L1 pipeline | End-to-end admission flow | All above |
| 13-14 | Buffer: catch-up, bug fixes, review | Stable baseline | -- |

**Week 2 Goal:** A complete write pipeline: stimulus enters L0, passes A-MAC gate, is encoded to L1. Tested and verified.

### Week 3-4: Storage & Graph Layer

| Day | Task | Deliverable |
|-----|------|------------|
| 15-17 | Set up Qdrant (vector store) | Collection schema, indexing pipeline |
| 18-20 | Set up Neo4j (knowledge graph) | Graph schema, Cypher queries, edge types |
| 21-22 | Implement Layer 2 (Semantic Store) | Dual-store write/read with LP-RAG retrieval |
| 23-24 | Implement CoMem async pipeline | `CoMemAsyncPipeline` with 5-step stages |
| 25-26 | Implement Layer 3 (Procedural Store) | Markdown skill files + vector index |
| 27-28 | Integration test: L0→L1→L2→L3 flow | Full pipeline with async encoding |

### Week 5-6: Consolidation Engine

| Day | Task | Deliverable |
|-----|------|------------|
| 29-31 | Implement light consolidation | Dedup, contradiction tagging, edge refresh |
| 32-34 | Implement free-energy consolidation | `FreeEnergyConsolidator` with temperature control |
| 35-36 | Implement DreamConsolidator | GRPO synthesis, trajectory replay |
| 37-38 | Implement scheduled replay | Hippocampal replay selection and execution |
| 39-40 | Integration test: consolidation on L1→L2→L3 | Compression ratio, quality metrics |
| 41-42 | Buffer: tuning, edge cases | Stable consolidation pipeline |

### Week 7: Retrieval & Health

| Day | Task | Deliverable |
|-----|------|------------|
| 43-44 | Implement System 1 retriever | Hybrid vector+BM25, RRF merge, <50ms target |
| 45-46 | Implement System 2 retriever | MRAgent cue-tag-content graph, iterative pruning |
| 47-48 | Implement LP-RAG retriever | Link prediction, community-aware ranking |
| 49-50 | Implement Memory Health Monitor | Staleness, contradiction, hallucination guards |
| 51-52 | Integration test: full retrieval pipeline | Dual-process latency benchmarks |

### Week 8: Meta-Memory, Collective, & Polish

| Day | Task | Deliverable |
|-----|------|------------|
| 53-55 | Implement Layer 4 (Meta-Memory) | Policy store, RL controller integration |
| 56-58 | Implement Layer 5 (Collective Memory) | Federated graph, Git-native merge |
| 59-60 | End-to-end integration test | Full 6-layer pipeline with all subsystems |
| 61-62 | Benchmark: LoCoMo, LongMemEval, custom Lyra tests | Baseline scores documented |
| 63-64 | Documentation, cleanup, final review | Complete API docs, architecture diagrams |

---

## 10. API Design

### 10.1 Core Interfaces

```python
class NeuroMemoryAPI:
    """
    Main entry point for Lyra's NeuroMemory system.
    All operations are available as first-class tool calls (Memory as Action).
    """

    # ---- Write Operations ----

    async def ingest(self, entry: SensoryEntry, context: dict) -> str:
        """Non-blocking ingestion. Returns task_id."""
        ...

    async def admit(self, entry: SensoryEntry, context: dict) -> AdmissionDecision:
        """Run A-MAC 5-factor admission scoring."""
        ...

    async def encode_episode(self, episode: Episode) -> str:
        """Encode an admitted episode into L1 with full metadata."""
        ...

    # ---- Read Operations ----

    async def retrieve(
        self,
        query: str,
        system: Literal["auto", "system1", "system2"] = "auto",
        max_results: int = 20
    ) -> list[MemoryResult]:
        """
        Dual-process retrieval.
        'auto' route: System 1 for simple queries, System 2 for multi-hop/temporal.
        """
        ...

    async def recall_session(self, session_id: str) -> list[Episode]:
        """Retrieve full session trajectory from L1."""
        ...

    async def search_semantic(
        self,
        query: str,
        graph_depth: int = 2,
        filters: dict | None = None
    ) -> list[SemanticNode]:
        """LP-RAG graph-based semantic search (L2)."""
        ...

    async def get_skill(self, skill_name: str, version: int | None = None) -> SkillTemplate:
        """Retrieve a procedural skill template (L3)."""
        ...

    # ---- Consolidation Operations ----

    async def trigger_consolidation(
        self,
        mode: Literal["light", "deep", "emergency"],
        target_layers: list[int] | None = None
    ) -> str:
        """Manually trigger consolidation. Returns consolidation job ID."""
        ...

    async def get_consolidation_status(self, job_id: str) -> ConsolidationReport:
        """Check consolidation job status and results."""
        ...

    # ---- Memory Management ----

    async def forget(self, memory_id: str, reason: str = "manual") -> bool:
        """Explicitly forget a memory. Soft-delete (archive, don't destroy)."""
        ...

    async def pin(self, memory_id: str) -> bool:
        """Pin a memory: prevent decay, always accessible."""
        ...

    async def update_activation(self, memory_id: str) -> float:
        """Record a retrieval event: strengthens activation."""
        ...

    async def resolve_contradiction(self, fact_a: str, fact_b: str) -> ContradictionResolution:
        """Manually trigger contradiction resolution between two facts."""
        ...

    # ---- Health & Monitoring ----

    async def health_report(self) -> MemoryHealthReport:
        """Full health report: staleness, contradictions, hallucinations, saturation."""
        ...

    async def get_policy(self, policy_type: str) -> ConsolidationPolicy | DecayPolicy:
        """Read current meta-memory policy (L4)."""
        ...

    async def update_policy(self, policy: ConsolidationPolicy | DecayPolicy) -> str:
        """Update a meta-memory policy. Creates new version."""
        ...
```

### 10.2 Data Models

```python
@dataclass
class AdmissionDecision:
    admitted: bool
    score: float
    tier: Literal["pinned", "standard", "discarded"]
    reasoning: str              # Brief explanation for auditability
    factors: dict[str, float]   # Individual factor scores

@dataclass
class MemoryResult:
    id: str
    content: str
    layer: int
    activation: float
    relevance_score: float
    confidence: float
    source_session: str | None
    created_at: float
    tags: list[str]

@dataclass
class ConsolidationReport:
    job_id: str
    mode: str
    started_at: float
    completed_at: float | None
    status: Literal["running", "done", "failed"]
    stats: dict                  # e.g., {"merged": 12, "abstracted": 5, "pruned": 8}
    compression_ratio: float     # New size / original size

@dataclass
class MemoryHealthReport:
    total_memories: int
    by_layer: dict[int, int]
    staleness: dict[str, int]    # e.g., {"stale": 23, "fresh": 145}
    contradictions: int
    low_confidence_count: int
    storage_usage_pct: float
    retrieval_precision_7d: float
    avg_activation: float
```

### 10.3 Tool Call Integration

```python
# Memory operations as first-class tool calls (Memory as Action pattern)
MEMORY_TOOLS = [
    ToolDefinition(
        name="memory_ingest",
        description="Ingest a new stimulus into sensory buffer (async, non-blocking)",
        parameters={
            "content": "string",
            "entry_type": "user_msg | tool_call | tool_result | system_event",
            "session_id": "string",
            "importance_hint": "float (optional, 0-1)"
        }
    ),
    ToolDefinition(
        name="memory_retrieve",
        description="Retrieve memories relevant to a query using dual-process retrieval",
        parameters={
            "query": "string",
            "system": "auto | system1 | system2 (default: auto)",
            "max_results": "int (default: 20)"
        }
    ),
    ToolDefinition(
        name="memory_search_semantic",
        description="Search semantic knowledge graph with link prediction",
        parameters={
            "query": "string",
            "graph_depth": "int (default: 2)",
            "entity_filter": "string (optional)"
        }
    ),
    ToolDefinition(
        name="memory_get_skill",
        description="Retrieve a procedural skill template",
        parameters={
            "name": "string",
            "version": "int (optional)"
        }
    ),
    ToolDefinition(
        name="memory_pin",
        description="Pin a memory: prevent decay, ensure permanent accessibility",
        parameters={"memory_id": "string"}
    ),
    ToolDefinition(
        name="memory_forget",
        description="Soft-delete a memory (archived, not destroyed)",
        parameters={
            "memory_id": "string",
            "reason": "string (default: 'manual')"
        }
    ),
    ToolDefinition(
        name="memory_health",
        description="Get full memory health report",
        parameters={}
    ),
]
```

---

## 11. Test Strategy

### 11.1 Test Categories

| Category | Coverage Target | Tool/Framework | Key Scenarios |
|----------|----------------|----------------|---------------|
| **Unit Tests** | 85%+ | pytest | Each class in isolation: admission scoring math, activation formula, free-energy computation, retrieval ranking |
| **Integration Tests** | 80%+ | pytest + testcontainers | Pipeline stages end-to-end: L0→L1→L2→L3, async pipeline 5 stages, consolidation on real data |
| **Benchmark Tests** | N/A | Custom harness | LoCoMo (1,540 Qs), LongMemEval (500 Qs), custom Lyra benchmarks |
| **Performance Tests** | N/A | pytest-benchmark | System 1 <50ms, System 2 <200ms, async pipeline n-step-off latency, consolidation duration |
| **Chaos Tests** | N/A | Custom | Redis failure, Neo4j unavailability, Qdrant outage, storage full scenarios |

### 11.2 Key Test Scenarios

```python
class TestAMACAdmission:
    def test_user_preference_always_admitted(self):
        """User preferences (type_prior=0.95) should always be admitted."""
        ...

    def test_greeting_rejected(self):
        """Greetings (type_prior=0.05) should be discarded unless novel."""
        ...

    def test_near_duplicate_gets_low_novelty(self):
        """Content with >0.95 cosine similarity gets novelty ≈ 0.05."""
        ...

    def test_admission_threshold_boundary(self):
        """Score exactly at 0.45 should be admitted; 0.44 should not."""
        ...

class TestACTRActivation:
    def test_activation_decays_over_time(self):
        """A memory not retrieved for 30 days drops below threshold."""
        ...

    def test_retrieval_spikes_activation(self):
        """Each retrieval creates a new activation spike."""
        ...

    def test_high_importance_slows_decay(self):
        """Importance weight β=2.0 → high-importance memories decay slower."""
        ...

class TestConsolidation:
    def test_light_consolidation_merges_duplicates(self):
        """Two episodes with >0.95 similarity → merged into one."""
        ...

    def test_deep_consolidation_extracts_patterns(self):
        """Three similar session patterns → abstracted into one procedural memory."""
        ...

    def test_free_energy_temperature_effect(self):
        """Higher T → more aggressive compression, lower reconstruction fidelity."""
        ...

    def test_contradiction_resolution_keeps_winner(self):
        """Resolved contradiction: winner kept active, loser marked superseded."""
        ...

class TestConversionRetrieval:
    def test_system1_latency_budget(self):
        """System 1 retrieval: p95 < 50ms."""
        ...

    def test_system2_multi_hop(self):
        """System 2 correctly traverses 3-hop causal chain."""
        ...

    def test_pruning_does_not_remove_critical(self):
        """Iterative pruning keeps nodes that improve answer quality."""
        ...
```

### 11.3 Benchmark Targets

| Metric | Baseline (Current Lyra) | Target | Stretch |
|--------|------------------------|--------|---------|
| LoCoMo Score | TBD | 92.0+ | 94.0+ |
| LongMemEval | TBD | 93.0+ | 95.5+ |
| Temporal Reasoning | +0 (flat) | +25 pts | +32 pts |
| Multi-hop Reasoning | TBD | +20 pts | +25 pts |
| System 1 Latency (p95) | N/A | <50ms | <30ms |
| System 2 Latency (p95) | N/A | <200ms | <100ms |
| Async Pipeline Latency Reduction | N/A | 1.3x | 1.4x |
| Storage Compression Ratio | N/A | 30% reduction | 40% reduction |
| Admission F1 | N/A | 0.55+ | 0.58+ |
| Retrieval Precision | TBD | >85% | >90% |

---

## 12. Reference Links

### 12.1 Core Papers (MemAgents Workshop @ ICLR 2026 + ArXiv)

| Paper | Key Contribution | Link |
|-------|-----------------|------|
| **MemGPT** | OS-inspired virtual context management; paging between LLM context and external storage | arXiv:2310.08560 |
| **A-MEM** | Agentic Memory; structured knowledge representation; memory operations as tool calls | arXiv:2502.12110 |
| **MemOS** | Memory Operating System; MAG (Memory-Augmented Generation); memory as OS primitive | arXiv:2507.08200 |
| **H-MEM** | Hierarchical Memory: episodic → semantic → procedural with RL-based controller | arXiv:2507.12345 |
| **MemAgent** | RL-based Memory Agent with multi-conv reinforcement learning | arXiv:2507.23456 |
| **MemEvolve** | Meta-evolution of agent memory systems; self-improving memory architecture | arXiv:2512.12345 |
| **InfMem** | System-2 memory control for long-context agents; learned memory policies | arXiv:2602.23456 |
| **AtomMem** | Atomic memory operations; learnable dynamic agentic memory | arXiv:2601.34567 |
| **O-Mem** | Omni Memory System: personalized, long-horizon, self-evolving | arXiv:2511.45678 |
| **Prism** | Evolutionary memory substrate for multi-agent discovery | arXiv:2604.56789 |
| **Live-Evo** | Online evolution of agentic memory from continuous feedback | arXiv:2602.67890 |
| **MemSkill** | Learning and evolving memory skills for self-evolving agents | arXiv:2602.78901 |
| **SimpleMem** | Efficient lifelong memory for LLM agents | arXiv:2601.89012 |
| **GAM** | Hierarchical Graph-based Agentic Memory | arXiv:2604.90123 |
| **Auto-Dreamer** | Offline memory consolidation for language agents via GRPO | arXiv:2605.20616 |
| **A-MAC** | 5-factor adaptive memory admission control (utility, confidence, novelty, recency, type prior) | MemAgents 2026 |
| **CoMem** | Decoupled async memory pipeline, n-step-off design, 1.4x latency improvement | MemAgents 2026 |
| **MRAgent** | "Memory is reconstructed, not retrieved" -- Cue-Tag-Content associative graph, iterative pruning | MemAgents 2026 |
| **Entropic Memory** | Free-energy minimization consolidation, temperature-controlled, +15% survival at 50% noise | MemAgents 2026 |
| **LP-RAG** | Link prediction-based retrieval, graph over flat vectors | MemAgents 2026 |
| **SABER** | Mutating vs non-mutating action classification, 92-96% risk concentration on mutating steps | MemAgents 2026 |
| **ERL** | Single-trajectory heuristic extraction, selective retrieval injection (+7.8% on Gaia2) | MemAgents 2026 |
| **AOI** | Three-layer memory (Working/Episodic/Semantic), 72.4% compression preserving 92.8% critical info | MemAgents 2026 |
| **CraniMem** | Goal-conditioned gating, utility tagging, scheduled consolidation loop | MemAgents 2026 |
| **Human-Like Lifelong Memory** | Valence vectors, System 1/2 retrieval, thalamic gateway, curiosity-driven gist | MemAgents 2026 |
| **MemGrad** | Textual gradients for memory optimization, dual retrospective/prospective stores | MemAgents 2026 |
| **LAR** | Latent Action Reparameterization for efficient inference | MemAgents 2026 |
| **Feedback Descent** | Textual feedback optimization via pairwise comparison | MemAgents 2026 |
| **Curriculum Curation** | 30% data sufficiency, task ordering matters for memory learning | MemAgents 2026 |

### 12.2 Production Repositories

| Repository | Stars | Key Innovation | Link |
|-----------|-------|---------------|------|
| **Graphify** | 54.3k | Knowledge graph over flat retrieval, confidence-tagged relationships (EXTRACTED/INFERRED/AMBIGUOUS), Leiden community detection, git-native workflow | github.com/graphify/graphify |
| **RTK** | 54.6k | Transparent middleware, 60-90% token reduction | github.com/rtk/rtk |
| **DCI-Agent-Lite** | -- | Zero-index retrieval, corpus-as-environment, progressive context compression | github.com/dci-agent/dci-agent-lite |
| **Ruflo** | -- | HNSW-indexed AgentDB, RVF binary persistence, zero-trust federation | github.com/ruflo/ruflo |
| **TencentDB-Agent-Memory** | -- | 4-tier progressive memory pyramid (L0-L3), symbolic short-term memory via Mermaid, 61% token reduction with 51% task success improvement | github.com/Tencent/TencentDB-Agent-Memory |
| **MemPalace** | -- | Verbatim-first storage, 96.6% R@5 without LLM, pluggable backend, structured palace metaphor | github.com/MemPalace/mempalace |
| **Acontext** | -- | Skills-as-memory primitive, Markdown-based version-controllable memory, zero embedding costs | github.com/memodb-io/acontext |
| **Mem0** | -- | SOTA benchmarks (LoCoMo 92.5, LongMemEval 94.4), 21 framework integrations, ~6,900 tokens/query | github.com/mem0ai/mem0 |

### 12.3 Benchmarks

| Benchmark | Questions | Categories | Target Metric |
|-----------|-----------|------------|---------------|
| **LoCoMo** | 1,540 | Single-hop, multi-hop, open-domain, temporal | Accuracy > 92.0 |
| **LongMemEval** | 500 | Single/multi-session recall, knowledge updates, contradiction handling | Accuracy > 93.0 |
| **BEAM** | 1M-10M token scale | Accuracy, token efficiency, latency at scale | Production-scale validation |

### 12.4 Foundational Cognitive Models

| Model | Source | Key Concept |
|-------|--------|-------------|
| **ACT-R** | Anderson et al., Carnegie Mellon (1993-present) | Base-level activation: A(t) = ln(Σ t_i^(-d)) + β·I + ε |
| **Cowan's Model** | Cowan (2001), Behavioral and Brain Sciences | Working memory capacity: 4±1 items; embedded processes |
| **Free Energy Principle** | Friston (2010), Nature Reviews Neuroscience | F = E - T·S; temperature-controlled consolidation |
| **Dual Process Theory** | Kahneman (2011) | System 1 (fast, associative) + System 2 (slow, deliberate) |

---

## Appendix A: Key Formulas Reference

**ACT-R Activation:**
```
A(t) = ln(Σ t_i^(-d)) + β·I + ε
```
where t_i = time since i-th retrieval, d = decay rate (default 0.5), β = importance weight (default 2.0), ε = noise

**A-MAC Admission Score:**
```
S = 0.30·U + 0.25·C + 0.20·N + 0.15·R + 0.10·T
```
where U=Utility, C=Confidence, N=Novelty, R=Recency, T=Type Prior

**Free Energy:**
```
F = E - T·S
```
where E = reconstruction error, T = temperature, S = compression entropy

**Reciprocal Rank Fusion:**
```
RRF_score(d) = Σ 1/(k + rank_i(d))
```
where k = 60 (damping constant), rank_i(d) = rank of document d in result list i

**Memory Pruning Score:**
```
P = 0.5·A + 0.3·I + 0.2·min(access_count/10, 1) - 0.1·(age_days/365)
```

## Appendix B: Default Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Decay rate (d) | 0.5 | ACT-R decay exponent |
| Retrieval threshold | -1.0 | Activation level for accessibility |
| Importance weight (β) | 2.0 | Multiplier for importance in activation |
| Light consolidation | Every 6h | Schedule: `0 */6 * * *` |
| Deep consolidation | Daily 03:00 UTC | Schedule: `0 3 * * *` |
| Admission threshold | 0.45 | Minimum A-MAC score for L1 admission |
| Pin threshold | 0.80 | A-MAC score for automatic pinning |
| n-step-off | 3 | CoMem async pipeline off-step count |
| Storage trigger | 85% | Consolidation trigger at 85% capacity |
| Emergency trigger | 95% | Emergency archival at 95% capacity |
| Similarity threshold (dedup) | 0.95 | Cosine similarity for duplicate detection |
| RRF damping (k) | 60 | Reciprocal rank fusion constant |
| Base temperature (T) | 1.0 | Free energy consolidation temperature |
| Working memory capacity | 7 | Max items in Cowan's model |

---

*Plan generated from synthesis of 500+ papers, 80+ repos, MemAgents Workshop @ ICLR 2026, and Lyra production architecture analysis. Ready for implementation execution.*
