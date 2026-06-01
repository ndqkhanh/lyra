# Lyra Ultra Plan 30: Phoenix Breakthrough Memory Architecture

**Status**: RESEARCH COMPLETE → PLANNING
**Wave**: 3 — Ultra Deep Research
**Focus**: Memory Architecture Breakthrough
**Timeline**: 16 Weeks (4 Phases × 4 weeks)
**Inspiration**: 22 ICLR 2026 MemAgent Workshop Papers + Acontext + TencentDB-Agent-Memory + Graphify + MemPalace + Claude-Mem

---

## Executive Summary

Lyra's existing 8-Level Cognitive Memory Stack (Plan 27) is sophisticated but fragmented — components exist in isolation without unified orchestration. The Phoenix Memory System introduces a **cost-sensitive routing fabric** that dynamically selects the optimal memory strategy per query, a **symbolic short-term memory** layer that compresses verbose tool outputs into Mermaid graph representations (61% token reduction), and **entropic consolidation** that uses free-energy minimization for robust memory retention under noise.

This plan synthesizes techniques from 22 MemAgent workshop papers plus auxiliary systems (Acontext, TencentDB, Graphify, MemPalace, claude-mem) into a single breakthrough architecture upgrade.

---

## Architecture Overview

```
+=======================================================================+
|                    PHOENIX MEMORY ARCHITECTURE                        |
+=======================================================================+
|                                                                       |
|  [USER/TOOL INPUT STREAM]                                             |
|         |                                                             |
|         v                                                             |
|  +------------------+    +----------------------+                     |
|  | THALAMIC GATEWAY |--->| A-MAC ADMISSION GATE |                     |
|  | (cognitive/      |    | (amac_admission.py)  |                     |
|  |  thalamic.py)    |    | 5-factor scoring     |                     |
|  +------------------+    +----------+-----------+                     |
|         |                           |                                 |
|         |                  [ADMIT?] |                                 |
|         |                     |No   |Yes                              |
|         |                     v     v                                 |
|         |              +-----------+-----------+                      |
|         |              | SYMBOLIC COMPRESSOR   |                      |
|         |              | (Mermaid Canvas SSM)  |                      |
|         |              | Tool output -> graph  |                      |
|         |              | Full text -> refs/*   |                      |
|         |              +-----------+-----------+                      |
|         |                           |                                 |
|         v                           v                                 |
|  +=======================================================+            |
|  |           CORE MEMORY HIERARCHY (5-TIER)              |            |
|  |=======================================================|            |
|  |  L0: EPISODIC BUFFER (Working/Recent, 200 entries)   |            |
|  |     - Goal-conditioned write gating (CraniMem)       |            |
|  |     - Utility-tagged, bounded capacity               |            |
|  |                                                       |            |
|  |  L1: HOT CACHE (In-memory, current session)          |            |
|  |     - ACT-R activation & decay                       |            |
|  |     - Real-time retrieval strengthening              |            |
|  |                                                       |            |
|  |  L2: WARM STORE (SQLite, cross-session, 7d window)   |            |
|  |     - BM25 + vector hybrid retrieval                 |            |
|  |     - LP-RAG graph-based retrieval augmentation      |            |
|  |                                                       |            |
|  |  L3: COLD KNOWLEDGE GRAPH (Semantic + Causal)        |            |
|  |     - Zettelkasten agentic linking                   |            |
|  |     - MultiGraph: semantic/temporal/causal/entity    |            |
|  |     - Leiden community detection                     |            |
|  |                                                       |            |
|  |  L4: PERSONA + ABSTRACTION LAYER                    |            |
|  |     - Valence vectors & belief hierarchy             |            |
|  |     - Cross-trajectory skill heuristics (ERL)        |            |
|  +=======================================================+            |
|         |                           ^                                 |
|         v                           |                                 |
|  +-------------------+   +----------------------+                      |
|  | COST-SENSITIVE    |-->| COMem ASYNC CONTEXT  |                      |
|  | ROUTER            |   | MANAGER              |                      |
|  | Query -> Store(s) |   | Decoupled from LLM   |                      |
|  +-------------------+   +----------------------+                      |
|         |                           ^                                 |
|         v                           |                                 |
|  +=======================================================+            |
|  |           RETRIEVAL PIPELINE                             |          |
|  |======================================================   |           |
|  |  1. Query -> Router selects optimal store(s)            |           |
|  |  2. System 1: automatic spreading activation            |           |
|  |  3. System 2: MRAgent active reconstruction (if needed) |           |
|  |  4. MMR diversity reranking                            |           |
|  |  5. Result: ranked, dedup'd, temporally-filtered       |           |
|  +=======================================================+            |
|         |                                                             |
|         v                                                             |
|  +=======================================================+            |
|  |           CONSOLIDATION ENGINE (Dream Cycle)           |            |
|  |=======================================================|            |
|  |  Light (every N=10): Dedup + ACT-R recalc + promote   |            |
|  |  Deep (every N=50): Entropic filter + 4-phase Dream   |            |
|  |  Prospective (N=200): MemGrad textual gradients       |            |
|  +=======================================================+            |
+=======================================================================+
```

---

## Phase 30.1: Symbolic Short-Term Memory (Weeks 1-4)

### The Problem
Tool outputs (search results, code diffs, error traces) consume 40-70% of context window tokens. Lyra needs a way to compress these without losing retrieval fidelity.

### The Solution: Mermaid Canvas SSM (TencentDB-Agent-Memory)

Convert verbose tool outputs into compact Mermaid graph representations (~200 tokens), offload full text to `refs/*.md` files, and enable on-demand recall via `node_id`.

**Results from TencentDB paper:**
- 61.38% token reduction on WideSearch
- +51.52% pass rate improvement
- Full-text retrieval via `node_id` grep preserves accuracy

### Implementation

```python
class SymbolicShortTermMemory:
    """
    Converts verbose tool outputs into Mermaid graph representations.
    Full text offloaded to refs/*.md for on-demand recall.
    """

    def __init__(self, refs_dir: Path = Path("refs")):
        self.refs_dir = refs_dir
        self.refs_dir.mkdir(exist_ok=True)
        self._node_index: dict[str, Path] = {}  # node_id -> ref file

    def compress(self, tool_name: str, output: str) -> SymbolicRepresentation:
        """Compress tool output into symbolic graph + ref file."""
        node_id = f"{tool_name}-{uuid4().hex[:8]}"
        ref_path = self.refs_dir / f"{node_id}.md"

        # Write full text to ref file
        ref_path.write_text(f"# {tool_name} Output ({node_id})\n\n{output}")

        # Generate Mermaid graph representation via LLM
        graph = self._extract_graph(tool_name, output)

        # Index for on-demand recall
        self._node_index[node_id] = ref_path

        return SymbolicRepresentation(
            node_id=node_id,
            mermaid_graph=graph,       # ~200 tokens injected into context
            summary=self._summarize(output),  # ~100 token natural language summary
            token_savings=self._calculate_savings(output, graph)
        )

    def recall(self, node_id: str) -> str:
        """On-demand full-text recall by node_id."""
        if node_id in self._node_index:
            return self._node_index[node_id].read_text()
        return self._grep_refs(node_id)  # fallback: grep all refs

    def _extract_graph(self, tool_name: str, output: str) -> str:
        """Extract Mermaid graph from tool output using fast model (Haiku)."""
        prompt = f"""Convert this {tool_name} output into a Mermaid graph.
Focus on entities, relationships, and key data points.
Use flowchart TD for process outputs, graph LR for data relationships.

Output:
{output[:3000]}  # truncated for extraction

Return ONLY the Mermaid graph definition starting with ```mermaid."""
        # Route to Haiku for cost efficiency
        return self.haiku.complete(prompt)

    def _calculate_savings(self, original: str, graph: str) -> TokenSavings:
        orig_tokens = count_tokens(original)
        graph_tokens = count_tokens(graph)
        return TokenSavings(
            original=orig_tokens,
            compressed=graph_tokens,
            ratio=graph_tokens / orig_tokens,
            saved=orig_tokens - graph_tokens
        )
```

### Integration Point

```python
# In Agent loop, after tool execution:
tool_output = await execute_tool(tool_name, params)
if count_tokens(tool_output) > CONTEXT_BUDGET * 0.15:
    symbolic = ssm.compress(tool_name, tool_output)
    context.add(symbolic.mermaid_graph)  # ~200 tokens
    context.add(f"[Full output: refs/{symbolic.node_id}.md]")  # recall hint
else:
    context.add(tool_output)  # Small outputs added directly
```

### Key Design Decisions
1. **Threshold-based activation**: Only compress outputs exceeding 15% of context budget
2. **Haiku for extraction**: Fast, cheap model for graph generation
3. **Dual representation**: Graph in context + full text on disk = no information loss
4. **Node ID grep**: Enables partial recall without loading entire ref file

---

## Phase 30.2: A-MAC Admission Gate + CraniMem Gating (Weeks 5-8)

### The Problem
Memory systems accumulate noise — hallucinated facts, obsolete information, contextually irrelevant data. Writing everything degrades retrieval quality.

### The Solution: Dual-Gate Write Pipeline

**Gate 1: A-MAC 5-Factor Admission** (mandatory pre-write)
Evaluates every candidate memory on: Future Utility, Factual Confidence, Semantic Novelty, Temporal Recency, Content Type Prior (most influential factor).

**Gate 2: CraniMem Goal-Conditioned Gating**
Evaluates: "Is this information relevant to the agent's current goals?" Irrelevant content never enters the episodic buffer.

### Implementation

```python
class DualGateAdmissionController:
    """
    Two-stage admission: A-MAC scoring + CraniMem goal gating.
    Only memories passing both gates enter the memory hierarchy.
    """

    def __init__(self, goals: list[str], thresholds: AdmissionThresholds):
        self.goals = goals
        self.thresholds = thresholds
        self.amac = AMACAdmission()  # Existing: amac_admission.py
        self.cranimem = CraniMemGate()  # New: goal-conditioned

    async def evaluate(self, candidate: MemoryCandidate) -> AdmissionResult:
        # Stage 1: A-MAC 5-factor scoring
        amac_score = await self.amac.score(candidate)
        if amac_score.composite < self.thresholds.amac_min:
            return AdmissionResult.reject(
                f"A-MAC score {amac_score.composite:.2f} < {self.thresholds.amac_min}",
                scores=amac_score
            )

        # Stage 2: Goal-conditioned gating
        goal_relevance = await self.cranimem.evaluate(candidate, self.goals)
        if goal_relevance < self.thresholds.goal_min:
            return AdmissionResult.reject(
                f"Goal relevance {goal_relevance:.2f} < {self.thresholds.goal_min}",
                goal_relevance=goal_relevance
            )

        return AdmissionResult.accept(
            amac_score=amac_score,
            goal_relevance=goal_relevance,
            target_tier=self._route_tier(amac_score, goal_relevance)
        )

    def _route_tier(self, amac: AMACScores, goal_rel: float) -> MemoryTier:
        """Route admitted memory to appropriate tier based on scores."""
        composite = (amac.composite * 0.6 + goal_rel * 0.4)
        if composite > 0.8 and amac.utility > 0.7:
            return MemoryTier.L1_HOT
        elif composite > 0.5:
            return MemoryTier.L2_WARM
        else:
            return MemoryTier.L3_COLD
```

### A-MAC Factor Weights (from ablation studies)

| Factor | Weight | Key Insight |
|--------|--------|-------------|
| Content Type Prior | 0.30 | Most influential — code > convo > fact > opinion |
| Future Utility | 0.25 | Predicted usefulness for future tasks |
| Factual Confidence | 0.20 | Source reliability + cross-reference score |
| Semantic Novelty | 0.15 | Jaccard distance from existing memories |
| Temporal Recency | 0.10 | Exponential decay with 24h half-life |

### Integration

```python
# In UltraMemorySystem.write():
async def write(self, content: str, metadata: MemoryMetadata) -> WriteResult:
    candidate = MemoryCandidate(content=content, metadata=metadata)
    admission = await self.admission_gate.evaluate(candidate)

    if not admission.accepted:
        self.stats.rejected += 1
        return WriteResult.rejected(admission.reason)

    target_tier = admission.target_tier
    await self.tiers[target_tier].store(candidate)
    self.stats.admitted += 1
    return WriteResult.stored(tier=target_tier, scores=admission.scores)
```

---

## Phase 30.3: System 1/2 Cognitive Routing + Active Reconstruction (Weeks 9-12)

### The Problem
Every retrieval query hits all stores — wasteful for simple queries (high latency) and insufficient for complex ones (shallow retrieval).

### The Solution: Dual-Path Retrieval with Fallback

**System 1 (Fast Path)**: Automatic spreading activation via ACT-R. No LLM involvement. Completes in <50ms. Handles ~80% of queries.

**System 2 (Deep Path)**: MRAgent-style iterative active reconstruction. Agent explores the memory graph, adapts retrieval paths based on intermediate findings, and prunes exploration dynamically. Handles ~20% of queries.

### Implementation

```python
class CognitiveRouter:
    """
    System 1 / System 2 retrieval routing.
    Fast automatic path for routine queries,
    deliberate reconstruction path for complex ones.
    """

    def __init__(self, confidence_threshold: float = 0.8):
        self.threshold = confidence_threshold
        self.system1 = System1Retriever()  # ACT-R spreading activation
        self.system2 = System2Retriever()  # MRAgent active reconstruction

    async def retrieve(self, query: str, context: RetrievalContext) -> RetrievalResult:
        # Always try System 1 first (fast, cheap)
        result = await self.system1.retrieve(query, context)

        if result.confidence >= self.threshold:
            result.path = "system1"
            return result

        # Escalate to System 2 for complex queries
        result = await self.system2.retrieve(query, context)
        result.path = "system2"
        return result


class System1Retriever:
    """ACT-R based automatic spreading activation. No LLM calls."""

    async def retrieve(self, query: str, ctx: RetrievalContext) -> RetrievalResult:
        # Broadcast to L0-L1 with ACT-R activation ordering
        candidates = []
        for tier in [self.tiers.L0, self.tiers.L1]:
            activated = tier.get_by_activation(query, top_k=20)
            candidates.extend(activated)

        # BM25 + vector hybrid on L2
        l2_results = self.tiers.L2.hybrid_search(query, top_k=10)
        candidates.extend(l2_results)

        # Rank by ACT-R activation * recency
        ranked = self._rank_by_activation(candidates)

        # Compute confidence from top-K score distribution
        confidence = self._estimate_confidence(ranked)

        return RetrievalResult(items=ranked[:10], confidence=confidence)


class System2Retriever:
    """MRAgent-style iterative active reconstruction."""

    async def retrieve(self, query: str, ctx: RetrievalContext) -> RetrievalResult:
        graph = self._build_associative_graph(query)  # Cue -> Tag -> Content

        collected = []
        explored = set()
        horizon = 20  # max exploration steps

        for step in range(horizon):
            # Query LLM for reasoning about current findings
            reasoning = await self.llm.reason(
                query=query,
                findings=collected,
                available_paths=self._get_unexplored(graph, explored)
            )

            # Adapt retrieval based on intermediate findings
            next_nodes = reasoning.suggested_paths
            if not next_nodes:
                break  # Exploration complete

            # Fetch content for suggested nodes
            for node in next_nodes:
                content = await self._fetch_content(node)
                collected.append(Evidence(node=node, content=content))
                explored.add(node)

            # Prune low-value paths
            graph.prune(collected, threshold=0.3)

            # Check if answer confidence is sufficient
            if self._sufficient(collected):
                break

        return RetrievalResult(
            items=self._synthesize(collected),
            confidence=self._score(collected),
            exploration_steps=step + 1
        )
```

### Performance Targets

| Metric | System 1 | System 2 | Current Baseline |
|--------|----------|----------|-----------------|
| Latency | <50ms | 500-2000ms | 300-800ms |
| LLM Calls | 0 | 2-8 | 1-3 |
| Accuracy (routine) | 92% | 95% | 88% |
| Accuracy (complex) | 70% | 91% | 76% |
| Token Cost | ~0 | ~2K-8K | ~1K-4K |

---

## Phase 30.4: Entropic Consolidation + Dream Cycle Upgrade (Weeks 13-16)

### The Problem
Simple greedy importance sampling for memory eviction performs poorly under noise (50% noise → 15% survival rate drop vs. entropic approach).

### The Solution: Free-Energy Minimization Consolidation

Replace greedy eviction with entropy-aware consolidation:
```
Free Energy = Utility - Temperature × Entropy
```

At lower noise (<30%), both approaches perform similarly. At higher noise (50%+), the entropic approach yields 15% better survival rate. Temperature annealing converges to optimal memory sets over time.

### Implementation

```python
class EntropicConsolidator:
    """
    Memory consolidation using free-energy minimization.
    Temperature-controlled stochastic replacement prevents
    greedy suboptimal retention under noise.
    """

    def __init__(self, initial_temperature: float = 1.0, cooling_rate: float = 0.95):
        self.temperature = initial_temperature
        self.cooling_rate = cooling_rate

    def consolidate(self, memories: list[MemoryEntry]) -> ConsolidationResult:
        kept = []
        pruned = []

        for memory in memories:
            # Free energy = utility - T * entropy
            utility = self._compute_utility(memory)
            entropy = self._compute_entropy(memory)
            free_energy = utility - self.temperature * entropy

            # Stochastic acceptance (Metropolis-like)
            acceptance_prob = 1.0 / (1.0 + math.exp(-free_energy))

            if random.random() < acceptance_prob:
                kept.append(memory)
            else:
                pruned.append(memory)

        # Cool temperature (simulated annealing)
        self.temperature *= self.cooling_rate

        return ConsolidationResult(
            kept=kept,
            pruned=pruned,
            temperature=self.temperature,
            survival_rate=len(kept) / len(memories)
        )

    def _compute_utility(self, memory: MemoryEntry) -> float:
        """Multi-factor utility: access frequency, link degree, confidence."""
        return (
            0.35 * memory.access_frequency +
            0.25 * memory.link_degree +
            0.25 * memory.confidence +
            0.15 * memory.recency_score
        )

    def _compute_entropy(self, memory: MemoryEntry) -> float:
        """Information entropy from content distribution across clusters."""
        cluster_dist = self._cluster_similarity_distribution(memory)
        return -sum(p * math.log(p + 1e-10) for p in cluster_dist if p > 0)
```

### Dream 4-Phase + Prospective 5th Phase

```python
class DreamConsolidatorV2:
    """
    Enhanced Dream cycle with entropic filtering + MemGrad prospective phase.
    """

    async def run_full_cycle(self, session_traces: list[Trace]) -> DreamResult:
        # Phase 1: ORIENT — scan for novel signals
        signals = await self._orient(session_traces)
        # Detects: SEMANTIC, KEYWORD, ENTITY, TEMPORAL, CAUSAL, PROCEDURAL

        # Phase 2: GATHER — retrieve related memories
        related = await self._gather(signals)
        # Uses: semantic/temporal/entity links for multi-hop retrieval

        # Phase 3: CONSOLIDATE — entropic filtering + entity resolution
        consolidated = self.entropic_consolidator.consolidate(
            self._merge_candidates(session_traces, related)
        )

        # Phase 4: PRUNE — Ebbinghaus forgetting curve simulation
        pruned = self._prune_ebbinghaus(consolidated.kept)
        # Power-law decay with importance modulation

        # Phase 5 (NEW): PROSPECTIVE — MemGrad textual gradients
        prospective = await self._compute_prospective_gradients(
            session_traces, consolidated
        )
        # Behavioral feedback → natural language improvement directions
        # Updates system prompts without model fine-tuning

        return DreamResult(
            signals=signals,
            consolidated=consolidated,
            pruned=pruned,
            prospective=prospective,
            stats=self._compute_stats(signals, consolidated, pruned)
        )

    async def _compute_prospective_gradients(
        self, traces: list[Trace], consolidated: ConsolidationResult
    ) -> ProspectiveMemory:
        """MemGrad-style textual gradients from trajectory feedback."""
        failures = [t for t in traces if not t.success]
        successes = [t for t in traces if t.success]

        gradients = []

        for failure in failures:
            # Diagnose what went wrong
            diagnosis = await self.llm.analyze_failure(failure)
            # Generate improvement direction
            gradient = await self.llm.generate_gradient(
                diagnosis=diagnosis,
                similar_successes=self._find_similar(successes, failure)
            )
            gradients.append(gradient)

        # Merge gradients into prospective memory updates
        return ProspectiveMemory(
            gradients=gradients,
            prompt_updates=self._synthesize_prompt_updates(gradients),
            skill_suggestions=self._suggest_skill_updates(gradients)
        )
```

### Ebbinghaus Curve Simulation

```python
def ebbinghaus_retention(days: float, importance: float = 1.0) -> float:
    """
    Ebbinghaus forgetting curve with importance modulation.
    R = e^(-t/S) where S = base_strength * importance
    """
    base_strength = 7.0  # days for 50% retention at importance=1.0
    strength = base_strength * importance
    return math.exp(-days / strength)

def should_prune(memory: MemoryEntry, current_time: datetime) -> bool:
    age_days = (current_time - memory.created_at).days
    retention = ebbinghaus_retention(age_days, memory.importance)
    return retention < 0.1  # Prune when retention drops below 10%
```

---

## Cross-Cutting: LP-RAG Graph Retrieval + Leiden Communities

### LP-RAG Integration

```python
class LPRAGRetriever:
    """
    Link-prediction-based retrieval for graph memory (L3).
    Reframes retrieval as inductive link prediction on similarity graphs.
    """

    def retrieve(self, query: str, graph: KnowledgeGraph, top_k: int = 10) -> list[MemoryNode]:
        # Build query-induced subgraph
        query_node = self._embed_query(query)
        subgraph = graph.k_hop_subgraph(query_node, k=2)

        # Predict links between query and candidate memories
        predictions = self.link_predictor.predict_links(
            query_node, subgraph.nodes
        )

        # Rank by link probability
        ranked = sorted(predictions, key=lambda p: p.probability, reverse=True)
        return [graph.get_node(p.target_id) for p in ranked[:top_k]]
```

### Leiden Community Detection

```python
class LeidenCommunityDetector:
    """Discover structural patterns in knowledge graph."""

    def detect_communities(self, graph: KnowledgeGraph) -> CommunityReport:
        communities = leiden_clustering(graph.adjacency)

        surprising_connections = self._find_surprising_links(
            communities, graph
        )

        god_nodes = self._find_hub_nodes(communities, top_k=10)

        return CommunityReport(
            communities=communities,
            modularity=compute_modularity(graph, communities),
            surprising_connections=surprising_connections,
            god_nodes=god_nodes
        )
```

---

## Migration Path from Existing Architecture

Lyra already has substantial memory infrastructure. This plan upgrades rather than replaces:

| Existing Component | Action | Target |
|-------------------|--------|--------|
| `amac_admission.py` | Integrate as mandatory pre-write Gate 1 | Phase 30.2 |
| `cognitive/thalamic.py` | Extend with CraniMem goal gating (Gate 2) | Phase 30.2 |
| `cognitive/router.py` | Wire into System1/System2 routing fabric | Phase 30.3 |
| `reconstruction/engine.py` | Complete MRAgent active reconstruction pipeline | Phase 30.3 |
| `dream_consolidator.py` | Add entropic filtering + MemGrad Phase 5 | Phase 30.4 |
| `routing/lp_rag.py` | Activate as primary L3 graph retrieval backend | Phase 30.4 |
| `compression.py` | Extend with Mermaid Canvas SSM | Phase 30.1 |
| `multi_graph.py` | Add Leiden community detection metadata | Phase 30.4 |
| `graph_tier.py` | Integrate LP-RAG + community detection | Phase 30.4 |
| `optimization/memgrad.py` | Wire prospective memory into prompt generation | Phase 30.4 |

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Token reduction (tool outputs) | 0% | 60%+ | Count tokens before/after SSM compression |
| Memory admission precision | N/A | 0.583 F1 | LoCoMo benchmark |
| Routine query latency | 300-800ms | <50ms | System 1 path timing |
| Complex query accuracy | 76% | 91% | LongMemEval |
| Noise robustness (50% noise) | Baseline | +15% survival | Entropic vs greedy comparison |
| Consolidation throughput | Serial | 1.4x async | CoMem pipeline |
| Cross-session recall | Manual | Automatic | Session manifest verification |
| Graph community modularity | N/A | >0.3 | Leiden clustering score |

---

## Innovation Lineage

| Technique | Source | Paper/Repo |
|-----------|--------|------------|
| Symbolic SSM (Mermaid Canvas) | TencentDB-Agent-Memory | arxiv.org/abs/2504.15287 |
| A-MAC 5-Factor Admission | ICLR 2026 MemAgent Workshop | #78 |
| Goal-Conditioned Gating | CraniMem | ICLR 2026 MemAgent Workshop #62 |
| System 1/2 Cognitive Routing | Neuroscience-grounded | ICLR 2026 MemAgent Workshop #89 |
| Active Memory Reconstruction | MRAgent | ICLR 2026 MemAgent Workshop #31 |
| Entropic Consolidation | Entropic Memory | ICLR 2026 MemAgent Workshop #15 |
| Dream 4-Phase Cycle | Existing Lyra | `dream_consolidator.py` |
| MemGrad Textual Gradients | MemGrad | ICLR 2026 MemAgent Workshop #44 |
| LP-RAG Graph Retrieval | LP-RAG | ICLR 2026 MemAgent Workshop #103 |
| CoMem Async Pipeline | CoMem | ICLR 2026 MemAgent Workshop #52 |
| Leiden Communities | Graphify | github.com/graphify-ai/graphify |
| Ebbinghaus Forgetting Curve | Existing Lyra | `ebbinghaus.py` |
| Zettelkasten Agentic Memory | A-Mem (NeurIPS 2025) | arxiv.org/abs/2501.12336 |
| Cost-Sensitive Routing | ICLR 2026 MemAgent Workshop | #104 |
| Valence Vectors | Human-Like Memory | ICLR 2026 MemAgent Workshop #89 |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| SSM graph extraction quality varies | Medium | Medium | Haiku with validation prompt, fallback to raw output |
| A-MAC gate too aggressive | Low | High | Adjustable thresholds, A/B test on historical data |
| System 2 latency too high | Medium | Medium | Cap exploration steps, cache frequent reconstructions |
| Entropic pruning loses critical memories | Low | High | Soft-delete with 30-day grace period, recall audit |
| Cross-session recall breaks | Medium | Medium | Session manifest integrity checks, automated recovery |
