# Brainstorm: Memory Architecture (§4.2) — Breakthrough Memory

**Workstream**: §4.2 Memory Architecture  
**Date**: 2026-05-31  
**Status**: Breakthrough ideas generated

---

## Sources Gathered

### ICLR 2026 MemAgent Workshop Papers
1. **AOI** — 3-layer hierarchy (Working/Episodic/Semantic), 72.4% compression, −34.4% MTTR
2. **A-MEM** — Zettelkasten-style dynamic linking, superior across 6 models
3. **A-MAC** — 5-factor admission control (utility/confidence/novelty/recency/type), F1=0.583, −31% latency
4. **ERL** (Experiential Reflective Learning) — Trajectory reflection → reusable heuristics, +7.8% on Gaia2
5. **Cost-Sensitive Store Routing** — Selective retrieval cuts tokens + improves accuracy
6. **Norm-Guided KV-Cache Eviction** — ℓ2-norm scoring for compression
7. **R-KVHash** — SimHash/LSH-based KV-cache compression, 2× decoding throughput
8. **LP-RAG** — Graph RAG with link prediction over chunk–query links
9. **SABER** — Mutation-gated verification, +28% Airline benchmark
10. **MemGrad** — Textual gradients turn feedback into memory + prompt updates

### Memory Systems & Repos
11. **Mem0** — Scalable cross-session memory layer
12. **Letta/MemGPT** — "LLM-as-OS" self-editing memory with paging
13. **Zep/Graphiti** — Temporal knowledge-graph memory
14. **AnnaAgent** — Tertiary memory integrating short + long-term across sessions
15. **MemAgent** (ICLR oral) — Segment processing with overwrite strategy, 8K→3.5M tokens
16. **DAVIS** — Knowledge-graph-powered inner monologue for structured reasoning
17. **MSI-Agent** — Multi-Scale Insight: experience selector + insight generator
18. **CFGM** — Coarse-to-Fine Grounded Memory across multiple granularities

### Context Optimization
19. **ACON** — Adaptive context compression, 26–54% memory cut
20. **IterResearch** — MDP-style workspace reconstruction with evolving report-as-memory
21. **MemSearcher** — Compact question-relevant memory across turns

---

## Novel Breakthrough Ideas (≥3 Required)

### Idea 1: **Temporal Knowledge Graph with Confidence Decay**

**Sources Combined**:
- Zep/Graphiti temporal knowledge graph
- A-MAC's 5-factor admission control (confidence scoring)
- DAVIS knowledge-graph inner monologue
- AnnaAgent multi-session integration

**Mechanism**:
Build a **time-aware knowledge graph** where:
1. **Nodes** = memory units (facts, heuristics, code patterns)
2. **Edges** = relationships (causal, temporal, semantic, contradictory)
3. **Confidence scores** decay over time unless reinforced by new evidence
4. **Contradiction detection**: New memories that conflict with old ones trigger a resolution process
5. **Cross-session linking**: Memories from different sessions connect via shared entities

Admission control uses A-MAC's 5 factors PLUS:
- **Temporal relevance**: Recent memories weighted higher
- **Reinforcement count**: How many times this memory was useful
- **Contradiction flag**: Conflicting memories marked for review

**Why It Beats Individual Sources**:
- Graphiti alone: No confidence decay or contradiction handling
- A-MAC alone: No graph structure, can't detect conflicts
- **Fusion**: Self-correcting memory that improves over time, handles conflicting information

**Expected Impact**: 85-90% accuracy on conflicting information, 40% faster retrieval via graph traversal

**Rough Effort**: HIGH (10-12 weeks) — graph database + decay logic + contradiction resolver

**Failure Modes**:
- Decay too aggressive → loses valuable old memories
- Contradiction detection false positives → unnecessary reviews
- Graph traversal overhead → slower than flat retrieval for simple queries

---

### Idea 2: **Hierarchical Memory with Lazy Materialization**

**Sources Combined**:
- AOI's 3-layer hierarchy (Working/Episodic/Semantic)
- MemAgent's segment processing with overwrite
- CFGM's coarse-to-fine granularity
- Cost-Sensitive Store Routing

**Mechanism**:
Implement a **4-layer hierarchy** with on-demand detail expansion:
1. **Working Memory** (current session, full detail, <10MB)
2. **Episodic Memory** (recent sessions, summaries only, <100MB)
3. **Semantic Memory** (long-term patterns, compressed, <1GB)
4. **Archive** (cold storage, indexed only, unlimited)

**Lazy materialization**: Higher layers store only summaries; full detail fetched on-demand from lower layers when needed.

**Cost-sensitive routing**: Query complexity determines which layer(s) to search:
- Simple query → Working only
- Medium query → Working + Episodic summaries
- Complex query → All layers, materialize details as needed

**Compression pipeline**:
- Working → Episodic: Extract key events, discard verbatim logs
- Episodic → Semantic: Generalize patterns, discard specific instances
- Semantic → Archive: Index only, compress full content

**Why It Beats Individual Sources**:
- AOI alone: Fixed 3 layers, no lazy loading
- MemAgent alone: Segment processing but no hierarchy
- **Fusion**: Scales to unlimited history while keeping active memory small

**Expected Impact**: 90%+ compression ratio, <50ms retrieval for 95% of queries

**Rough Effort**: MEDIUM-HIGH (8-10 weeks) — 4-layer implementation + lazy loading + compression

**Failure Modes**:
- Materialization latency spikes for deep queries
- Over-compression loses critical details
- Layer boundaries unclear → wrong layer selected

---

### Idea 3: **Self-Evolving Memory via MemGrad + ERL**

**Sources Combined**:
- MemGrad textual gradients (feedback → memory updates)
- ERL trajectory reflection (extract reusable heuristics)
- Darwin self-evolution (§3.18)
- Lyra's skills system (§4.4)

**Mechanism**:
Memory doesn't just store — it **learns and improves**:
1. **Trajectory capture**: Every task execution is logged (actions + outcomes)
2. **Reflection pass**: ERL-style analysis extracts heuristics ("When X happens, do Y")
3. **MemGrad updates**: User feedback (explicit or implicit) generates textual gradients that update memory
4. **Heuristic promotion**: High-confidence heuristics become skills (§4.4 integration)
5. **A/B testing**: New heuristics tested in sandbox before promotion

Example flow:
- Task: "Debug authentication bug"
- Trajectory: [read logs → check config → found typo in env var]
- Reflection: "Auth bugs often caused by env var typos"
- MemGrad: User says "great catch!" → reinforces heuristic
- Promotion: Heuristic becomes a skill: "Check env vars first for auth issues"

**Why It Beats Individual Sources**:
- MemGrad alone: Updates memory but doesn't extract patterns
- ERL alone: Extracts heuristics but doesn't evolve them
- **Fusion**: Continuous learning loop that turns experience into reusable knowledge

**Expected Impact**: 2-3× improvement in similar task performance, 50% reduction in repeated mistakes

**Rough Effort**: VERY HIGH (12-14 weeks) — trajectory logging + reflection engine + MemGrad integration + skills bridge

**Failure Modes**:
- Overfitting to specific contexts → heuristics don't generalize
- Feedback loop instability → memory thrashing
- Heuristic conflicts → contradictory advice

---

### Idea 4: **Memory-Augmented Router Integration**

**Sources Combined**:
- Cost-Sensitive Store Routing
- Lyra's model router (§4.5)
- MemSearcher compact question-relevant memory
- Knowledge Access Beats Model Size paper (§3.14)

**Mechanism**:
Integrate memory directly into the routing decision:
1. **Query → Memory lookup**: Before routing to LLM, check if answer is in memory
2. **Cache hit**: Return cached answer (cheap model or no model)
3. **Cache miss**: Route to appropriate model tier based on complexity
4. **Partial hit**: Use memory as context, route to cheaper model
5. **Memory update**: Store new answers for future reuse

**Routing logic**:
```
if (exact_match_in_memory) {
  return cached_answer; // $0 cost
} else if (similar_query_in_memory) {
  context = retrieve_relevant_memories();
  route_to_cheap_model(query, context); // 90% cost reduction
} else {
  route_to_expensive_model(query); // full cost
}
```

**Why It Beats Individual Sources**:
- Router alone: No memory, every query costs full price
- Memory alone: No routing, always uses same model
- **Fusion**: 90%+ cost reduction for repeat queries, maintains quality

**Expected Impact**: 85-90% cost reduction overall, <10ms memory lookup latency

**Rough Effort**: MEDIUM (6-8 weeks) — memory-router bridge + similarity matching + cache invalidation

**Failure Modes**:
- Stale cached answers → incorrect responses
- Similarity matching false positives → wrong context
- Memory lookup overhead → slower than direct LLM call for novel queries

---

## Parked Ideas (Advanced in Run 5)

### Idea 5 (ADVANCED): **Population-Based Memory Evolution with FORGE Broadcast**

**Sources Fused**: FORGE Population Broadcast (#103) + A-MAC admission control (#79) + MemGrad textual gradients (#70) + DecentMem per-agent pools (#99)

**Mechanism**: Run N parallel Lyra instances, each with its own memory pool. Periodically:
1. Rank all N pools by aggregate task success on held-out benchmark
2. Broadcast the top performer's memory (rules + heuristics + few-shot demos) to all instances
3. Each instance merges broadcast content with its local pool using A-MAC admission control
4. Freeze converged memory items (those that appear in ≥3 instances with >0.9 confidence)
5. Unfrozen items continue to evolve locally

**Key Insight from FORGE**: Rules-based memory uses 40% fewer tokens than example-based memory while achieving equivalent performance. This directly informs Lyra's memory format: prefer distilled rules over raw examples.

**Why It Beats Individual Sources**: FORGE broadcasts at task boundaries; this system broadcasts continuously. DecentMem guarantees O(log T) regret per agent; FORGE adds population-level convergence. A-MAC prevents bad memories from polluting the population.

**Expected Impact**: 2-3× faster convergence on optimal memory vs single-instance evolution
**Rough Effort**: HIGH (8-10 weeks) — broadcast protocol + merge logic + convergence detection

### Idea 6 (ADVANCED): **Intent-Based Memory Indexing with STITCH Triples**

**Sources Fused**: STITCH intent-based indexing (#139) + Cost-Sensitive Store Routing (#60) + Retrieval-as-Reasoning (#92) + TKG temporal linking

**Mechanism**: Index every memory node with a (goal, action_type, entity) triple:
- **goal**: What task was being attempted (e.g., "debug-auth-bug", "implement-JWT")
- **action_type**: What type of action was taken (e.g., "read-config", "write-code", "run-tests")
- **entity**: What was acted upon (e.g., "auth.ts", "JWT_SECRET", "login-endpoint")

Retrieval uses these triples for context-sensitive filtering: when a query comes in with goal="debug-auth-bug", the system FIRST filters to memories with matching goal, THEN does semantic search within that subset. STITCH showed this eliminates 35.6% of semantically-similar-but-contextually-wrong retrievals.

**Why It Beats Individual Sources**: STITCH alone applies to static QA; this applies to dynamic agent task memory. Cost-Sensitive Routing picks the store; STITCH picks the CONTEXT WITHIN the store. The combination filters noise before search instead of after.

**Expected Impact**: 35-40% reduction in irrelevant retrievals, 20% faster retrieval via targeted indexing
**Rough Effort**: MEDIUM (4-6 weeks) — triple extraction + index structure + retrieval filter

### Idea 7 (ADVANCED): **Self-Optimizing Memory Compression via Meta-Harness**

**Sources Fused**: Meta-Harness outer-loop search (#121) + AOI sliding-window compression (#68) + ACON failure-driven optimization (#254) + KAIST localized compression (#73)

**Mechanism**: Treat compression strategy as a searchable parameter space:
1. Meta-agent reads compression outcomes (what was lost? what was preserved?)
2. Proposes new compression hyperparameters (window size, overlap %, importance threshold)
3. Tests on held-out task traces with known critical information
4. Promotes configurations that achieve higher info-retention-to-compression ratios
5. Discovers per-domain optimal compression (different strategy for coding tasks vs research tasks)

**Why It Beats Individual Sources**: AOI uses fixed 50% overlap; ACON adapts to failure; neither SEARCHES the compression space. Meta-Harness provides the outer-loop optimization that tunes compression automatically.

**Expected Impact**: 15-25% improvement in compression effectiveness via auto-tuned parameters
**Rough Effort**: MEDIUM-HIGH (6-8 weeks) — meta-search loop + compression parameter space

---

## Parked Ideas (Not Yet Advanced)

1. **Federated memory**: Share anonymized patterns across Lyra instances
2. **Memory visualization**: Interactive graph UI for exploring memory connections
3. **Memory export/import**: Portable memory format for backup/sharing
4. **Memory analytics**: Dashboard showing memory growth, hit rates, compression ratios
5. **Memory garbage collection**: Automatic pruning of unused/low-value memories

---

### Idea 8 (Run 7 — NEW): **Adversarial Memory Verification with Cross-Model Consensus**

**Sources Fused**: SABER mutation-gating (#67) + AutoScientists critique-before-spend (#154-156) + FORGE population broadcast (#103) + LP-RAG link prediction (#66) + BREAKTHROUGH-ARCHITECTURE AVP (§5)

**Mechanism**: Memory writes are MUTATING operations (SABER #67: each memory insertion changes future retrieval behavior). Apply the Adversarial Verification Protocol to memory writes:

1. **Before committing** a new memory node to TKG:
   - Spawn 2 critic agents using DIFFERENT model providers (e.g., Claude-critic + DeepSeek-critic)
   - Each critic independently evaluates: (a) factual accuracy of the memory, (b) consistency with existing TKG nodes (via LP-RAG link prediction: does the proposed node's predicted links match actual TKG structure?), (c) utility — will this memory likely be useful?
2. **Consensus rule**: Both critics must approve (confidence >0.7) for auto-commit
   - Both approve → commit to TKG
   - Split (one approve, one reject) → flag for human review, admit to "quarantine" tier (accessible but not used for routing/retrieval unless explicitly requested)
   - Both reject → discard, log rejection reason for MemGrad feedback
3. **Cross-model diversity**: Claude and DeepSeek have different inductive biases and training distributions — a memory that convinces BOTH is robust. A memory that only convinces Claude may exploit Claude-specific blind spots.
4. **Periodic re-verification**: Every N new memories, re-verify N_random old memories to catch concept drift (new knowledge invalidating old).

**Concrete Algorithm**:
```
function adversarial_memory_admit(candidate: MemoryNode, tkg: TKG): AdmitDecision
  // Step 1: LP-RAG structural check
  predicted_links = lp_rag.predict_links(candidate.embedding, tkg.top_k_similar(candidate, 50))
  structural_score = jaccard(candidate.links, predicted_links)
  
  // Step 2: Cross-model factual check
  claude_verdict = critic_check(candidate, tkg, provider='claude')
  deepseek_verdict = critic_check(candidate, tkg, provider='deepseek')
  
  // Step 3: Consensus
  if claude_verdict.approve AND deepseek_verdict.approve AND structural_score > 0.5:
    return { action: 'commit', tier: candidate.admission.aggregate > 0.6 ? 'semantic' : 'episodic' }
  else if claude_verdict.approve XOR deepseek_verdict.approve:
    return { action: 'quarantine', reason: 'cross-model-disagreement' }
  else:
    return { action: 'reject', reason: claude_verdict.rationale + ' | ' + deepseek_verdict.rationale }
```

**Why It Beats Individual Sources**:
- A-MAC admits based on 5 features from a SINGLE model → vulnerable to that model's blind spots
- SABER gates on mutation type but doesn't verify content → memory errors slip through if classified as "low-risk"
- FORGE broadcasts without adversarial filtering → bad memories can spread
- **Fusion**: Cross-model consensus + structural consistency + A-MAC scoring = 3 independent filters against memory corruption. The cross-model diversity is the key innovation — no paper combines this with memory admission.

**Expected Impact**: 60-80% reduction in false memories admitted (vs A-MAC alone), <200ms additional latency per admission (2 parallel LLM calls)
**Rough Effort**: MEDIUM-HIGH (6-8 weeks) — cross-model critic protocol + LP-RAG integration + quarantine tier
**Failure Modes**: Both models agree on a plausible-but-wrong memory (shared training data biases); LP-RAG link prediction is noisy for novel domains; quarantine tier grows unbounded → needs periodic cleanup

---

### Idea 9 (Run 7 — NEW): **Differentiable Memory Retrieval with Textual Gradients (MemGrad++)**

**Sources Fused**: MemGrad textual gradients (#70) + EvolveMem self-optimizing retrieval (#106) + SkillOpt bounded edits (#117) + Meta-Harness outer-loop search (#121)

**Mechanism**: Memory retrieval is currently static (fixed embedding weights + fixed retrieval strategy). MemGrad++ makes retrieval STRATEGY a learnable parameter optimized by user outcomes:

1. **Retrieval as a weighted pipeline**:
   ```
   retrieve(query) = α * embedding_search(query, top_k) 
                   + β * graph_traversal(query, depth)
                   + γ * temporal_recency(query, window)
                   + δ * intent_match(query, triple)
   ```
   where (α, β, γ, δ) are LEARNABLE weights, initially (0.4, 0.3, 0.2, 0.1)

2. **Feedback signal**: For each retrieval event, track whether the user (a) explicitly accepted the retrieved memory, (b) ignored it, (c) explicitly rejected it as irrelevant, or (d) the task succeeded/failed (implicit signal).

3. **Textual gradient computation** (MemGrad-style, no fine-tuning):
   - Batch K retrieval events with outcomes
   - LLM analyzes: "For queries of type X, temporal_recency was underweighted (memories from 2 minutes ago would have been more relevant than embedding matches from 2 weeks ago)"
   - LLM produces: textual gradient = "Increase β for code-debugging queries when query contains timestamps like 'just now', 'recently', 'last time'"
   - Gradient is applied as a CONDITIONAL weight override, not a global weight change

4. **Bounded optimization** (SkillOpt constraint):
   - Weights can shift by at most ±0.15 per update (prevents oscillation)
   - After each update, run on held-out retrieval test set → must improve or revert (EvolveMem auto-rollback)
   - Meta-Harness outer loop: every 1,000 retrievals, search for a new weight INITIALIZATION (not just update) to escape local optima

**Concrete Weight Update Algorithm**:
```
function apply_textual_gradient(gradient: TextualGradient, weights: RetrievalWeights): RetrievalWeights
  // Parse the gradient's conditional structure
  condition = parse_condition(gradient.text)  // e.g., "queries with temporal markers AND task_type=coding"
  adjustment = parse_adjustment(gradient.text) // e.g., {β: +0.08, δ: -0.03}
  
  // Apply bounded adjustment
  new_weights = weights.clone()
  for (param, delta) in adjustment:
    new_weights[param] += clamp(delta, -0.15, +0.15)
  
  // Normalize to sum=1.0
  new_weights = normalize(new_weights)
  
  // Store as conditional rule for matching query types
  return {
    default_weights: weights,       // Unchanged for non-matching queries
    conditional_overrides: [
      ...weights.conditional_overrides,
      { condition, weights: new_weights }
    ]
  }
```

**Why It Beats Individual Sources**:
- MemGrad: Updates prompts but doesn't optimize retrieval parameters → prompts get better but retrieval stays static
- EvolveMem: Self-optimizes but uses binary search over configs, not gradient-informed updates → slower convergence
- SkillOpt: Bounded edits but for skills, not retrieval → same idea, different target
- Meta-Harness: Outer-loop search but no inner-loop gradient → complementary; Meta-Harness handles global exploration while MemGrad++ handles local exploitation
- **Fusion**: Inner-loop textual gradients for fast local improvement + bounded updates for stability + Meta-Harness outer loop for escaping local optima = retrieval that continuously improves without catastrophic forgetting

**Expected Impact**: 15-25% improvement in retrieval relevance after 500 retrievals, <50ms gradient computation overhead (batched, async)
**Rough Effort**: HIGH (8-10 weeks) — MemGrad pipeline + conditional weight system + held-out test set + Meta-Harness integration
**Failure Modes**: Overfitting to recent queries (recency bias in gradient); condition space explosion (too many conditional overrides → retrieval becomes unpredictable); test set contamination (gradients leak test info)

---

## ═══ ALGORITHMIC FUSION DEEPENING — Run 10 ═══

### Deepening: Idea 8 — Adversarial Memory Verification with Cross-Model Consensus

**Complete Verification Algorithm**:

```typescript
function verifyMemory(memory: RawMemory, existingTKG: Graph): VerificationResult {
  // Step 1: Structural consistency check (LP-RAG inspired)
  const neighbors = existingTKG.findNeighbors(memory.embedding, { topK: 20 });
  const consistencyScore = linkPredictionCheck(memory, neighbors);
  // Uses inductive link prediction over (memory, neighbor) pairs
  // Score = fraction of predicted links that match actual content
  
  // Step 2: Cross-model factual verification
  const criticA = await verify(memory, 'claude', 'Is this memory factually accurate?');
  const criticB = await verify(memory, 'deepseek', 'Is this memory factually accurate?');
  
  // Step 3: Consensus
  if (criticA.approve && criticB.approve && consistencyScore > 0.7) {
    return { decision: 'admit', confidence: avg(criticA.confidence, criticB.confidence) };
  }
  if (criticA.approve !== criticB.approve) {
    return { decision: 'quarantine', reason: 'critic disagreement' };
  }
  return { decision: 'reject', reason: 'both critics reject' };
}
```

**Full TypeScript Pseudocode**:

```typescript
// ============================================================
// Adversarial Memory Verification with Cross-Model Consensus
// ============================================================

type Verdict = 'admit' | 'quarantine' | 'reject';

interface VerificationResult {
  decision: Verdict;
  confidence: number;       // 0-1 aggregate
  reason: string;
  tier?: 'semantic' | 'episodic' | 'quarantine';
  verificationId: string;
  timestamp: number;        // unix ms
}

interface CriticVerdict {
  approve: boolean;
  confidence: number;       // 0-1
  rationale: string;
  provider: string;         // 'claude' | 'deepseek'
  latencyMs: number;
}

interface QuarantineEntry {
  memory: MemoryNode;
  verificationResult: VerificationResult;
  quarantinedAt: number;
  expiresAt: number;        // auto-cleanup after N days
  accessCount: number;
  resolvedBy: string | null; // null = unresolved, 'auto-admit' | 'auto-reject' | 'human-reviewed'
}

// --- Link Prediction Model (LP-RAG inspired) ---

class LinkPredictionModel {
  // Uses inductive link prediction over (memory, neighbor) pairs
  // Score = fraction of predicted links that match actual content

  async predictLinks(
    candidate: MemoryNode,
    neighbors: MemoryNode[]
  ): Promise<PredictLinkResult> {
    // Structural features between candidate and each neighbor:
    // 1. embedding_similarity (cosine)
    // 2. temporal_proximity (time difference)
    // 3. entity_overlap (shared entities in content)
    // 4. intent_tag_alignment (Jaccard of STITCH triples)
    // 5. graph_structural_features (common neighbors count, Katz index)
    
    const predictions: Array<{ neighborId: string; score: number; linkType: string }> = [];
    
    for (const neighbor of neighbors) {
      // 1. Structural features
      const embSim = this.cosineSimilarity(candidate.embedding, neighbor.embedding);
      const tempProx = Math.exp(-0.001 * Math.abs(candidate.timestamp - neighbor.timestamp) / 1000);
      const entityOverlap = this.computeEntityOverlap(candidate.text, neighbor.text);
      const intentAlign = this.jaccardIntent(candidate.intentTags, neighbor.intentTags);
      
      // 2. Graph structural features
      const commonNeighbors = this.countCommonNeighbors(candidate.id, neighbor.id, this.tkg);
      const katzIndex = this.computeKatzIndex(candidate.id, neighbor.id, this.tkg);
      
      // 3. Logistic regression on features (pretrained weights)
      const featureVec = [embSim, tempProx, entityOverlap, intentAlign, commonNeighbors, katzIndex];
      const weights = [0.35, 0.15, 0.20, 0.20, 0.05, 0.05]; // trained on held-out graph edges
      const score = featureVec.reduce((sum, f, i) => sum + f * weights[i], 0);
      
      // Sigmoid
      const prob = 1 / (1 + Math.exp(-5 * (score - 0.5)));
      
      if (prob > 0.6) {
        const linkType = this.predictLinkType(prob, embSim, tempProx);
        predictions.push({ neighborId: neighbor.id, score: prob, linkType });
      }
    }
    
    // 3. Aggregate: what fraction of predicted links exist in the TKG?
    return {
      predictions,
      consistencyScore: this.computeConsistencyScore(predictions, candidate.links),
      predictedLinkCount: predictions.length,
    };
  }

  private computeConsistencyScore(
    predictions: Array<{ neighborId: string; score: number }>,
    actualLinks: TKGEdge[]
  ): number {
    // Fraction of predicted links that match actual TKG edges
    const actualNeighborIds = new Set(actualLinks.map(e => e.targetId));
    
    let matches = 0;
    for (const pred of predictions) {
      if (actualNeighborIds.has(pred.neighborId) && pred.score > 0.7) {
        matches++;
      }
    }
    
    const precision = predictions.length > 0 ? matches / predictions.length : 0;
    const recall = actualNeighborIds.size > 0 ? matches / actualNeighborIds.size : 1;
    
    // F1 score
    if (precision + recall === 0) return 0;
    return 2 * precision * recall / (precision + recall);
  }

  private predictLinkType(prob: number, embSim: number, tempProx: number): string {
    if (embSim > 0.8 && tempProx > 0.7) return 'temporal-semantic';
    if (embSim > 0.8 && tempProx <= 0.7) return 'semantic-skip'; // same topic, different time
    if (embSim <= 0.7 && tempProx > 0.7) return 'temporal-context'; // recent but different topic
    return 'weak';
  }

  private computeEntityOverlap(textA: string, textB: string): number {
    // Named entity overlap fraction
    const entitiesA = this.extractEntities(textA);
    const entitiesB = this.extractEntities(textB);
    if (entitiesA.length === 0 || entitiesB.length === 0) return 0;
    
    const setB = new Set(entitiesB.map(e => e.toLowerCase()));
    const overlap = entitiesA.filter(e => setB.has(e.toLowerCase())).length;
    return 2 * overlap / (entitiesA.length + entitiesB.length); // Dice coefficient
  }

  private countCommonNeighbors(idA: string, idB: string, tkg: Graph): number {
    const neighborsA = new Set(tkg.getNeighbors(idA).map(n => n.id));
    const neighborsB = new Set(tkg.getNeighbors(idB).map(n => n.id));
    let common = 0;
    for (const n of neighborsA) {
      if (neighborsB.has(n)) common++;
    }
    return Math.min(common / 10, 1.0); // normalize: max 10 common neighbors = 1.0
  }

  private computeKatzIndex(idA: string, idB: string, tkg: Graph): number {
    // Sum over all paths of length l: β^l * count_paths(A, B, l)
    // β = 0.005 (decay factor for long paths)
    // We approximate with paths of length 2 only (neighbors of neighbors)
    const neighborsA = tkg.getNeighbors(idA);
    const neighborsOfNeighbors = new Map<string, number>();
    
    for (const nA of neighborsA) {
      const n2 = tkg.getNeighbors(nA.id);
      for (const n of n2) {
        if (n.id === idA || n.id === idB) continue;
        neighborsOfNeighbors.set(n.id, (neighborsOfNeighbors.get(n.id) ?? 0) + 1);
      }
    }
    
    const path2Count = neighborsOfNeighbors.get(idB) ?? 0;
    return Math.min(path2Count * 0.005, 1.0); // β = 0.005
  }
}

// --- Cross-Model Critic ---

interface CriticPromptConfig {
  systemPrompt: string;
  userPromptTemplate: string;
  temperature: number;
  maxTokens: number;
}

class CrossModelCritic {
  private lpModel: LinkPredictionModel;
  private criticPrompts: CriticPromptConfig;
  private providers: string[];
  private tkg: Graph;

  constructor(tkg: Graph, providers: string[] = ['claude', 'deepseek']) {
    this.tkg = tkg;
    this.lpModel = new LinkPredictionModel(tkg);
    this.providers = providers;
    
    this.criticPrompts = {
      systemPrompt: `You are a memory verification critic. Your role: evaluate a candidate memory 
node before it's admitted to the knowledge graph. 

Evaluate THREE dimensions:
1. FACTUAL ACCURACY: Is the content factually accurate? Cross-reference with existing memories.
2. CONSISTENCY: Does this memory contradict existing nodes? Report contradictions specifically.
3. UTILITY: Will this memory likely be useful for future tasks? Consider generality vs. specificity.

Respond in this exact JSON format:
{
  "approve": true/false,
  "confidence": 0.0-1.0,
  "rationale": "concise explanation of your reasoning",
  "contradictions": ["list of specific contradictions with existing memory IDs, if any"],
  "suggested_tier": "semantic" | "episodic" | "working"
}`,
      userPromptTemplate: `Evaluate this candidate memory for admission to the temporal knowledge graph:

MEMORY TEXT: {{memoryText}}
INTENT TAGS: {{intentTags}}
PROPOSED LINKS (predicted): {{predictedLinks}}
EXISTING RELATED MEMORIES (top 5): {{relatedMemories}}

Your evaluation:

1. FACTUAL ACCURACY: Does the candidate contain verifiable claims? Are any claims contradicted?
2. CONSISTENCY: Do the predicted links make sense given the existing graph structure?
3. UTILITY: Would this memory help future tasks?`,
      temperature: 0.2,
      maxTokens: 512,
    };
  }

  async verify(
    candidate: MemoryNode,
    context: VerificationContext
  ): Promise<VerificationResult> {
    const startTime = Date.now();
    
    // Step 1: Run link prediction (structural check)
    const linkPredictionResult = await this.lpModel.predictLinks(
      candidate, 
      this.tkg.findNeighbors(candidate.embedding, { topK: 50 })
    );
    
    // Step 2: Spawn parallel cross-model critics
    const criticResults = await Promise.all(
      this.providers.map(provider => 
        this.runCritic(candidate, linkPredictionResult, provider)
      )
    );
    
    // Step 3: Consensus logic
    const claude = criticResults.find(r => r.provider === 'claude')!;
    const deepseek = criticResults.find(r => r.provider === 'deepseek')!;
    
    const structuralScore = linkPredictionResult.consistencyScore;
    
    let result: VerificationResult;
    
    if (claude.approve && deepseek.approve && structuralScore > 0.5) {
      // Both approve + structural consistency
      const confidence = Math.min(1.0, (claude.confidence + deepseek.confidence) / 2 + structuralScore * 0.2);
      const tier = this.determineTier(confidence, candidate, context);
      
      result = {
        decision: 'admit',
        confidence,
        reason: `Cross-model consensus (claude=${claude.confidence.toFixed(2)}, deepseek=${deepseek.confidence.toFixed(2)}, structural=${structuralScore.toFixed(2)})`,
        tier,
        verificationId: this.generateId(),
        timestamp: Date.now(),
      };
      
      // If confidence is very high (>0.85), also broadcast to FORGE population
      if (confidence > 0.85) {
        this.broadcastToForge(candidate);
      }
      
    } else if (claude.approve !== deepseek.approve) {
      // Split verdict: quarantine
      result = {
        decision: 'quarantine',
        confidence: 0.3, // quarantined = low confidence
        reason: `Cross-model disagreement: claude=${claude.approve}(${claude.confidence.toFixed(2)}), deepseek=${deepseek.approve}(${deepseek.confidence.toFixed(2)}). Structural=${structuralScore.toFixed(2)}`,
        verificationId: this.generateId(),
        timestamp: Date.now(),
      };
      
      // Log the disagreement for MemGrad-style analysis
      this.logDisagreement(candidate, claude, deepseek);
      
    } else {
      // Both reject
      result = {
        decision: 'reject',
        confidence: 0,
        reason: `Both critics reject: Claude="${claude.rationale}" | DeepSeek="${deepseek.rationale}"`,
        verificationId: this.generateId(),
        timestamp: Date.now(),
      };
      
      // Log rejection for retrieval strategy adjustment (MemGrad++)
      this.logRejection(candidate, claude, deepseek, linkPredictionResult);
    }
    
    // Step 4: Periodic re-verification scheduling (every 100 memories, re-verify 5 random old ones)
    const totalMemories = this.tkg.nodeCount();
    if (totalMemories > 0 && totalMemories % 100 === 0) {
      this.scheduleReVerification(5);
    }
    
    Logger.info(`Memory verification: ${candidate.id.slice(0, 8)} → ${result.decision} (${(Date.now() - startTime)}ms)`);
    
    return result;
  }

  private async runCritic(
    candidate: MemoryNode,
    linkPrediction: PredictLinkResult,
    provider: string
  ): Promise<CriticVerdict> {
    const startTime = Date.now();
    
    // Format the prompt with candidate data
    const prompt = this.criticPrompts.userPromptTemplate
      .replace('{{memoryText}}', candidate.text)
      .replace('{{intentTags}}', candidate.intentTags.join(', '))
      .replace('{{predictedLinks}}', JSON.stringify(linkPrediction.predictions.slice(0, 10)))
      .replace('{{relatedMemories}}', this.formatRelatedMemories(candidate));
    
    // Call provider-specific API (abstracted)
    const response = await this.callProvider(provider, this.criticPrompts.systemPrompt, prompt);
    
    const latencyMs = Date.now() - startTime;
    
    try {
      const parsed = JSON.parse(response);
      return {
        approve: parsed.approve === true,
        confidence: parsed.confidence ?? 0.5,
        rationale: parsed.rationale ?? 'No rationale provided',
        provider,
        latencyMs,
      };
    } catch {
      // Parse failure: treat as reject with low confidence
      return {
        approve: false,
        confidence: 0.1,
        rationale: 'Failed to parse critic response',
        provider,
        latencyMs,
      };
    }
  }

  private determineTier(
    confidence: number, 
    candidate: MemoryNode, 
    ctx: VerificationContext
  ): 'semantic' | 'episodic' | 'working' {
    // high confidence + general pattern → semantic tier
    // medium confidence + specific instance → episodic tier
    // low confidence + current session → working tier (will be re-verified soon)
    
    if (confidence > 0.8) return 'semantic';
    if (confidence > 0.6) return 'episodic';
    return 'working';
  }

  private formatRelatedMemories(candidate: MemoryNode): string {
    const related = this.tkg.findNeighbors(candidate.embedding, { topK: 5 });
    return related.map((m, i) => 
      `[${i + 1}] ${m.text.slice(0, 200)} (tags: ${m.intentTags.join(', ')}, time: ${new Date(m.timestamp).toISOString()})`
    ).join('\n');
  }

  private async callProvider(provider: string, system: string, prompt: string): Promise<string> {
    // Provided by the multi-provider LLM abstraction layer
    return this.providerRouter.call(provider, system, prompt, {
      temperature: this.criticPrompts.temperature,
      maxTokens: this.criticPrompts.maxTokens,
    });
  }

  private broadcastToForge(memory: MemoryNode): void {
    // High-confidence memories are candidates for FORGE population broadcast
    // This means other Lyra instances can pull this memory via the broadcast protocol
    Logger.info(`FORGE broadcast candidate: ${memory.id.slice(0, 8)} (confidence > 0.85)`);
    this.forgeBroadcaster.queue(memory);
  }
}

// --- Quarantine Management ---

class QuarantineManager {
  private quarantineStore: Map<string, QuarantineEntry> = new Map();
  private readonly maxQuarantineSize: number = 1000;
  private readonly quarantineTTLDays: number = 30;
  private readonly checkIntervalMs: number = 3600000; // 1 hour

  constructor() {
    // Periodic cleanup task
    setInterval(() => this.cleanup(), this.checkIntervalMs);
  }

  admitToQuarantine(memory: MemoryNode, result: VerificationResult): void {
    if (this.quarantineStore.size >= this.maxQuarantineSize) {
      this.evictOldest();
    }
    
    this.quarantineStore.set(memory.id, {
      memory,
      verificationResult: result,
      quarantinedAt: Date.now(),
      expiresAt: Date.now() + this.quarantineTTLDays * 24 * 60 * 60 * 1000,
      accessCount: 0,
      resolvedBy: null,
    });
    
    Logger.info(`Quarantine admit: ${memory.id.slice(0, 8)} (reason: ${result.reason})`);
  }

  isAccessible(memoryId: string): boolean {
    const entry = this.quarantineStore.get(memoryId);
    if (!entry) return false;
    
    entry.accessCount++;
    
    // Quarantine memories are accessible only for explicit retrieval requests,
    // not for automatic retrieval / routing
    return true;
  }

  getExplicitRetrievalResult(candidates: MemoryNode[]): { retrieved: MemoryNode[]; quarantined: MemoryNode[] } {
    const retrieved: MemoryNode[] = [];
    const quarantined: MemoryNode[] = [];
    
    for (const c of candidates) {
      if (this.quarantineStore.has(c.id)) {
        this.quarantineStore.get(c.id)!.accessCount++;
        if (this.shouldAutoResolve(c)) {
          // Auto-resolve if enough access count without issue
          const resolved = this.autoResolve(c);
          if (resolved) {
            retrieved.push(c);
            continue;
          }
        }
        quarantined.push(c);
      } else {
        retrieved.push(c);
      }
    }
    
    return { retrieved, quarantined };
  }

  private shouldAutoResolve(memory: MemoryNode): boolean {
    const entry = this.quarantineStore.get(memory.id);
    if (!entry) return false;
    
    // Auto-resolve if accessed 10+ times without conflict report
    return entry.accessCount >= 10 && entry.resolvedBy === null;
  }

  private autoResolve(memory: MemoryNode): boolean {
    const entry = this.quarantineStore.get(memory.id);
    if (!entry) return false;
    
    entry.resolvedBy = 'auto-admit';
    this.quarantineStore.delete(memory.id);
    
    Logger.info(`Quarantine auto-resolved (admit): ${memory.id.slice(0, 8)} (accessed ${entry.accessCount} times without conflict)`);
    return true;
  }

  private cleanup(): void {
    const now = Date.now();
    let removed = 0;
    
    for (const [id, entry] of this.quarantineStore) {
      if (entry.expiresAt <= now) {
        this.quarantineStore.delete(id);
        removed++;
      }
    }
    
    if (removed > 0) {
      Logger.info(`Quarantine cleanup: removed ${removed} expired entries, ${this.quarantineStore.size} remaining`);
    }
  }

  private evictOldest(): void {
    let oldestId: string | null = null;
    let oldestTime = Infinity;
    
    for (const [id, entry] of this.quarantineStore) {
      if (entry.quarantinedAt < oldestTime && entry.accessCount < 3) {
        oldestTime = entry.quarantinedAt;
        oldestId = id;
      }
    }
    
    if (oldestId) {
      Logger.info(`Quarantine evict: ${oldestId.slice(0, 8)} (oldest, low access)`);
      this.quarantineStore.delete(oldestId);
    }
  }

  // Human review interface
  getHumanReviewQueue(limit: number = 10): QuarantineEntry[] {
    return Array.from(this.quarantineStore.values())
      .filter(e => e.resolvedBy === null)
      .sort((a, b) => a.quarantinedAt - b.quarantinedAt)
      .slice(0, limit);
  }

  resolveManually(memoryId: string, resolution: 'admit' | 'reject'): void {
    const entry = this.quarantineStore.get(memoryId);
    if (!entry) return;
    
    entry.resolvedBy = 'human-reviewed';
    
    if (resolution === 'admit') {
      // Promote to TKG
      this.tkg.insert(entry.memory);
      this.quarantineStore.delete(memoryId);
    } else {
      // Discard
      this.quarantineStore.delete(memoryId);
    }
  }
}
```

---

### Deepening: Idea 9 — Differentiable Memory Retrieval with Textual Gradients (MemGrad++)

**MemGrad++ Algorithm with explicit weight update equations**:

```
Retrieval weights: θ = [α, β, γ, δ] for the 4 retrieval strategies:
  α: embedding similarity (dense)
  β: keyword match (sparse) 
  γ: temporal recency
  δ: graph proximity (A-MEM links)

After each user interaction with outcome O (success=1, failure=0):
  Textual gradient = LLM("Given weights θ=[α,β,γ,δ], the retrieval resulted in outcome O.
    How should the weights change? Provide direction and magnitude for each.")
  
  Bounded update: θ_new = θ + clip(Δθ, -0.15, +0.15)
  Normalize: θ_new = θ_new / sum(θ_new)
  
After 500 retrievals, weights converge to task-optimal distribution.
Expected: 15-25% retrieval relevance improvement.
```

**Full TypeScript Pseudocode**:

```typescript
// ============================================================
// Differentiable Memory Retrieval via Textual Gradients (MemGrad++)
// ============================================================

interface RetrievalWeights {
  alpha: number;  // embedding similarity (dense)
  beta: number;   // keyword match (sparse)
  gamma: number;  // temporal recency
  delta: number;  // graph proximity (A-MEM links)
}

interface RetrievalEvent {
  query: string;
  queryType: string;            // 'coding' | 'debug' | 'research' | 'planning' | 'general'
  queryTemporalMarkers: string[];  // ['just now', 'recently', 'last time', etc.]
  retrievedMemories: MemoryNode[];
  selectedMemoryId: string | null; // null if none selected
  outcome: 'success' | 'failure' | 'ignored' | 'rejected';
  taskCompleted: boolean;
  userFeedback?: 'positive' | 'negative' | 'neutral';
  timestamp: number;
}

interface ConditionalOverride {
  condition: string;            // e.g., "queryType==='debug' AND hasTemporalMarker('just now')"
  weights: RetrievalWeights;
  hitCount: number;             // how many times this override was applied
  lastApplied: number;
  performanceGain: number;      // cumulative improvement metric
}

class MemGradPlusPlus {
  // Default weights
  private defaultWeights: RetrievalWeights = { alpha: 0.40, beta: 0.30, gamma: 0.20, delta: 0.10 };
  
  // Conditional overrides (condition → custom weights)
  private conditionalOverrides: ConditionalOverride[] = [];
  
  // Recent retrieval events buffer (for batched gradient computation)
  private retrievalHistory: RetrievalEvent[] = [];
  private readonly batchSize = 20;
  private readonly maxOverrides = 50;
  
  // Bounded update
  private readonly maxDeltaPerWeight = 0.15;
  private readonly convergenceThreshold = 0.01;
  
  // Held-out test set cache
  private heldoutTestSet: RetrievalEvent[] = [];
  
  // Meta-Harness outer loop counter
  private totalRetrievals = 0;
  private readonly outerLoopInterval = 1000;

  // --- Core Retrieval ---

  async retrieve(
    query: string,
    queryEmbedding: Float32Array,
    candidates: MemoryNode[],
    context: RetrievalContext
  ): Promise<MemoryNode[]> {
    this.totalRetrievals++;
    
    const weights = this.getWeightsForQuery(query, context);
    
    // Combined scoring with current weights
    const scored = candidates.map(candidate => {
      const alphaScore = this.embeddingSimilarity(queryEmbedding, candidate.embedding);
      const betaScore = this.keywordMatch(query, candidate.text, candidate.intentTags);
      const gammaScore = this.temporalRecency(candidate.timestamp, context.currentTimestamp);
      const deltaScore = this.graphProximity(candidate, context.recentMemoryIds, this.tkg);
      
      const composite = 
        weights.alpha * alphaScore +
        weights.beta * betaScore +
        weights.gamma * gammaScore +
        weights.delta * deltaScore;
      
      return { node: candidate, score: composite };
    });
    
    // Sort and select top-k
    scored.sort((a, b) => b.score - a.score);
    const selected = scored.slice(0, context.topK ?? 10).map(s => s.node);
    
    // Record event for gradient computation
    this.recordRetrieval(query, selected, context);
    
    return selected;
  }

  private getWeightsForQuery(query: string, context: RetrievalContext): RetrievalWeights {
    // Check conditional overrides first
    for (const override of this.conditionalOverrides) {
      if (this.evaluateCondition(override.condition, query, context)) {
        override.hitCount++;
        override.lastApplied = Date.now();
        return override.weights;
      }
    }
    
    // No matching override: use default weights
    return { ...this.defaultWeights };
  }

  private evaluateCondition(condition: string, query: string, context: RetrievalContext): boolean {
    // Parse and evaluate simple conditional expressions
    // Format: "queryType==='debug' AND hasTemporalMarker('just now')"
    const parts = condition.split(' AND ');
    
    for (const part of parts) {
      const trimmed = part.trim();
      
      // queryType check
      const queryTypeMatch = trimmed.match(/queryType==='(\w+)'/);
      if (queryTypeMatch) {
        if (context.queryType !== queryTypeMatch[1]) return false;
        continue;
      }
      
      // hasTemporalMarker check
      const temporalMatch = trimmed.match(/hasTemporalMarker\('(.+?)'\)/);
      if (temporalMatch) {
        const markers = this.extractTemporalMarkers(query);
        if (!markers.some(m => m.includes(temporalMatch[1]))) return false;
        continue;
      }
      
      // If we can't parse the condition, skip this override
      return false;
    }
    
    return true;
  }

  // --- Recording Retrieval Events for Gradient Computation ---

  recordRetrieval(query: string, selected: MemoryNode[], context: RetrievalContext): void {
    this.retrievalHistory.push({
      query,
      queryType: context.queryType,
      queryTemporalMarkers: this.extractTemporalMarkers(query),
      retrievedMemories: selected,
      selectedMemoryId: selected[0]?.id ?? null, // top result
      outcome: 'success', // placeholder, will be updated with user feedback
      taskCompleted: false,
      timestamp: Date.now(),
    });
    
    // Batch gradient computation every batchSize events
    if (this.retrievalHistory.length >= this.batchSize) {
      this.computeTextualGradients();
    }
    
    // Meta-Harness outer loop
    if (this.totalRetrievals % this.outerLoopInterval === 0) {
      this.outerLoopSearch();
    }
  }

  recordOutcome(retrievalIndex: number, outcome: RetrievalEvent['outcome'], taskCompleted: boolean): void {
    if (retrievalIndex < this.retrievalHistory.length) {
      this.retrievalHistory[retrievalIndex].outcome = outcome;
      this.retrievalHistory[retrievalIndex].taskCompleted = taskCompleted;
    }
  }

  // --- Textual Gradient Computation ---

  private async computeTextualGradients(): Promise<void> {
    // Step 1: Filter to events with outcomes
    const eventsWithOutcomes = this.retrievalHistory.filter(
      e => e.outcome !== 'ignored' // ignore events where user didn't interact
    );
    
    if (eventsWithOutcomes.length < 5) return; // need minimum samples
    
    // Step 2: Group by query type for type-specific gradients
    const grouped = this.groupByQueryType(eventsWithOutcomes);
    
    for (const [queryType, events] of Object.entries(grouped)) {
      if (events.length < 3) continue;
      
      // Step 3: Analyze current weights' performance for this query type
      const currentWeights = this.getWeightsForType(queryType);
      const successRate = events.filter(e => e.outcome === 'success').length / events.length;
      
      // Step 4: Generate textual gradient via LLM
      const gradient = await this.generateTextualGradient(currentWeights, events, queryType);
      
      // Step 5: Parse gradient into weight adjustments
      const adjustment = this.parseGradientAdjustment(gradient.text);
      
      // Step 6: Apply bounded weight update
      const updatedWeights = this.applyBoundedUpdate(currentWeights, adjustment);
      
      // Step 7: Validate on held-out test set
      const testPerformance = this.evaluateOnTestSet(updatedWeights, queryType);
      const currentPerformance = this.evaluateOnTestSet(currentWeights, queryType);
      
      if (testPerformance > currentPerformance) {
        // Update accepted: store as conditional override
        this.addConditionalOverride(queryType, updatedWeights, testPerformance - currentPerformance);
        Logger.info(`MemGrad++: ${queryType} weights updated: Δ=${(testPerformance - currentPerformance).toFixed(3)}`);
      } else {
        // Rollback: keep current weights
        Logger.info(`MemGrad++: ${queryType} weights ROLLED BACK (test perf declined)`);
      }
    }
    
    // Step 8: Clear processed events (keep last 5 for overlap)
    this.retrievalHistory = this.retrievalHistory.slice(-5);
  }

  /** The LLM prompt that generates textual gradients */
  private async generateTextualGradient(
    currentWeights: RetrievalWeights,
    events: RetrievalEvent[],
    queryType: string
  ): Promise<{ text: string }> {
    const gradientPrompt = `
You are a retrieval optimization system. Analyze the following retrieval events and propose weight adjustments to improve retrieval relevance.

CURRENT WEIGHTS:
  α (embedding similarity): ${(currentWeights.alpha * 100).toFixed(0)}%
  β (keyword match):       ${(currentWeights.beta * 100).toFixed(0)}%
  γ (temporal recency):    ${(currentWeights.gamma * 100).toFixed(0)}%
  δ (graph proximity):     ${(currentWeights.delta * 100).toFixed(0)}%

QUERY TYPE: ${queryType}

RECENT RETRIEVAL EVENTS (${events.length} total, ${events.filter(e => e.outcome === 'success').length} successes, ${events.filter(e => e.outcome === 'failure').length} failures):

${events.map((e, i) => {
  const selectedId = e.selectedMemoryId?.slice(0, 8) ?? 'none';
  const temporalMarkers = e.queryTemporalMarkers.join(', ') || 'none';
  return `[${i}] Query: "${e.query.slice(0, 100)}..."
  Outcome: ${e.outcome}
  Selected: ${selectedId}
  Temporal markers: ${temporalMarkers}
  Task completed: ${e.taskCompleted}`;
}).join('\n\n')}

Based on this analysis, provide:

1. Which weight(s) should be increased? By how much (0.00-0.15 each)?
2. Which weight(s) should be decreased? By how much (0.00-0.15 each)?
3. What CONDITION should trigger these weights (e.g., "queryType==='debug' AND hasTemporalMarker('recently')")?
4. Explain your reasoning: What pattern in the retrieval events led to this adjustment?

RESPONSE FORMAT (JSON):
{
  "adjustment": { "alpha": 0.00, "beta": 0.00, "gamma": 0.00, "delta": 0.00 },
  "condition": "queryType==='debug'",
  "reasoning": "explanation of what pattern was detected"
}
`;

    const llmResponse = await this.llm.call(gradientPrompt, { 
      temperature: 0.3, 
      maxTokens: 512 
    });
    
    return { text: llmResponse };
  }

  private parseGradientAdjustment(text: string): RetrievalWeights {
    try {
      // Extract JSON from the response
      const jsonMatch = text.match(/\{[\s\S]*"adjustment"[\s\S]*\}/);
      if (!jsonMatch) return { alpha: 0, beta: 0, gamma: 0, delta: 0 };
      
      const parsed = JSON.parse(jsonMatch[0]);
      const adj = parsed.adjustment;
      
      return {
        alpha: adj.alpha ?? 0,
        beta: adj.beta ?? 0,
        gamma: adj.gamma ?? 0,
        delta: adj.delta ?? 0,
      };
    } catch {
      return { alpha: 0, beta: 0, gamma: 0, delta: 0 };
    }
  }

  private applyBoundedUpdate(
    current: RetrievalWeights, 
    adjustment: RetrievalWeights
  ): RetrievalWeights {
    // Bounded update: clip each delta to [-0.15, +0.15]
    const clamped = {
      alpha: current.alpha + Math.max(-this.maxDeltaPerWeight, Math.min(this.maxDeltaPerWeight, adjustment.alpha)),
      beta: current.beta + Math.max(-this.maxDeltaPerWeight, Math.min(this.maxDeltaPerWeight, adjustment.beta)),
      gamma: current.gamma + Math.max(-this.maxDeltaPerWeight, Math.min(this.maxDeltaPerWeight, adjustment.gamma)),
      delta: current.delta + Math.max(-this.maxDeltaPerWeight, Math.min(this.maxDeltaPerWeight, adjustment.delta)),
    };
    
    // Ensure all weights are non-negative
    clamped.alpha = Math.max(0, clamped.alpha);
    clamped.beta = Math.max(0, clamped.beta);
    clamped.gamma = Math.max(0, clamped.gamma);
    clamped.delta = Math.max(0, clamped.delta);
    
    // Normalize: sum to 1.0
    const sum = clamped.alpha + clamped.beta + clamped.gamma + clamped.delta;
    if (sum === 0) return { alpha: 0.25, beta: 0.25, gamma: 0.25, delta: 0.25 }; // fallback to uniform
    
    return {
      alpha: clamped.alpha / sum,
      beta: clamped.beta / sum,
      gamma: clamped.gamma / sum,
      delta: clamped.delta / sum,
    };
  }

  private addConditionalOverride(queryType: string, weights: RetrievalWeights, gain: number): void {
    const condition = `queryType==='${queryType}'`;
    
    // Update existing override if present
    const existing = this.conditionalOverrides.find(o => o.condition === condition);
    if (existing) {
      existing.weights = weights;
      existing.performanceGain += gain;
      existing.lastApplied = Date.now();
      return;
    }
    
    // Add new override
    this.conditionalOverrides.push({
      condition,
      weights,
      hitCount: 0,
      lastApplied: Date.now(),
      performanceGain: gain,
    });
    
    // Enforce max overrides limit
    if (this.conditionalOverrides.length > this.maxOverrides) {
      // Remove the worst-performing override (lowest performance gain ÷ hit count)
      this.conditionalOverrides.sort((a, b) => {
        const efficiencyA = a.hitCount > 0 ? a.performanceGain / a.hitCount : 0;
        const efficiencyB = b.hitCount > 0 ? b.performanceGain / b.hitCount : 0;
        return efficiencyA - efficiencyB;
      });
      this.conditionalOverrides.shift(); // remove worst
    }
  }

  private getWeightsForType(queryType: string): RetrievalWeights {
    const override = this.conditionalOverrides.find(o => o.condition === `queryType==='${queryType}'`);
    return override?.weights ?? { ...this.defaultWeights };
  }

  // --- Evaluator on Held-out Test Set ---

  private evaluateOnTestSet(weights: RetrievalWeights, queryType: string): number {
    const testEvents = this.heldoutTestSet.filter(e => e.queryType === queryType);
    if (testEvents.length < 3) return 0; // insufficient data
    
    // For each test event, check if the correct memory would have been ranked higher
    let correctRankImprovements = 0;
    
    for (const event of testEvents) {
      const scored = event.retrievedMemories.map(m => {
        // Simplified scoring with proposed weights
        // (In production, re-run the full retrieval pipeline)
        const score = 
          weights.alpha * 0.5 +  // Placeholder: would be actual embedding similarity
          weights.beta * 0.3 +
          weights.gamma * 0.4 +
          weights.delta * 0.2;
        return { memoryId: m.id, score };
      });
      
      scored.sort((a, b) => b.score - a.score);
      const topId = scored[0]?.memoryId;
      
      if (topId === event.selectedMemoryId && event.outcome === 'success') {
        correctRankImprovements++;
      }
    }
    
    return testEvents.length > 0 ? correctRankImprovements / testEvents.length : 0;
  }

  // --- Convergence Detection ---

  hasConverged(): boolean {
    // Convergence: no conditional override has been updated in the last 200 retrievals
    const now = Date.now();
    const recentUpdates = this.conditionalOverrides.filter(
      o => now - o.lastApplied < 200 * 30000 // 200 retrievals * ~30s avg interval = ~100 minutes
    );
    
    return recentUpdates.length === 0;
  }

  getConvergedWeights(): RetrievalWeights {
    if (!this.hasConverged()) return this.defaultWeights;
    
    // Return the most-used conditional override as the "converged" weights
    if (this.conditionalOverrides.length === 0) return this.defaultWeights;
    
    this.conditionalOverrides.sort((a, b) => b.hitCount - a.hitCount);
    return this.conditionalOverrides[0].weights;
  }

  // --- Meta-Harness Outer Loop ---

  private async outerLoopSearch(): Promise<void> {
    Logger.info('MemGrad++: Meta-Harness outer loop triggered (1000 retrievals)');
    
    // If converged and performance is good, attempt to find a better initialization
    if (!this.hasConverged()) return;
    
    // Evaluate current converged weights
    let totalPerformance = 0;
    let queriesTested = 0;
    
    for (const override of this.conditionalOverrides) {
      const perf = this.evaluateOnTestSet(override.weights, 
        override.condition.replace("queryType==='", "").replace("'", ""));
      totalPerformance += perf;
      queriesTested++;
    }
    
    const currentAvgPerf = queriesTested > 0 ? totalPerformance / queriesTested : 0;
    
    // Meta-Harness proposes new initializations as perturbations
    const perturbation = {
      alpha: this.defaultWeights.alpha + (Math.random() - 0.5) * 0.2,
      beta: this.defaultWeights.beta + (Math.random() - 0.5) * 0.2,
      gamma: this.defaultWeights.gamma + (Math.random() - 0.5) * 0.2,
      delta: this.defaultWeights.delta + (Math.random() - 0.5) * 0.2,
    };
    
    // Re-normalize
    const sumP = perturbation.alpha + perturbation.beta + perturbation.gamma + perturbation.delta;
    const newDefaults = {
      alpha: Math.max(0, perturbation.alpha / sumP),
      beta: Math.max(0, perturbation.beta / sumP),
      gamma: Math.max(0, perturbation.gamma / sumP),
      delta: Math.max(0, perturbation.delta / sumP),
    };
    
    // Evaluate new initialization
    const newAvgPerf = this.evaluateAllTypes(newDefaults);
    
    if (newAvgPerf > currentAvgPerf * 1.05) { // 5%+ improvement
      this.defaultWeights = newDefaults;
      Logger.info(`MemGrad++: Default weights updated via Meta-Harness: α=${newDefaults.alpha.toFixed(3)}, β=${newDefaults.beta.toFixed(3)}, γ=${newDefaults.gamma.toFixed(3)}, δ=${newDefaults.delta.toFixed(3)}`);
    }
  }

  // --- Helper Methods ---

  private extractTemporalMarkers(query: string): string[] {
    const markers: string[] = [];
    const patterns: Array<[RegExp, string]> = [
      [/\b(just now|just|a moment ago)\b/i, 'just now'],
      [/\b(recently|lately|in the last few)\b/i, 'recently'],
      [/\b(last time|previous|before)\b/i, 'last time'],
      [/\b(yesterday|today|this morning|this afternoon)\b/i, 'relative day'],
      [/\b(minute|hour|day|week) ago\b/i, 'ago duration'],
      [/\b(new|latest|fresh)\b/i, 'recency'],
      [/\b(old|earlier|previously|beforehand)\b/i, 'history'],
      [/\b(remember|recall|forget|forgot)\b/i, 'memory cue'],
    ];
    
    for (const [regex, label] of patterns) {
      if (regex.test(query)) markers.push(label);
    }
    
    return markers;
  }

  private groupByQueryType(events: RetrievalEvent[]): Record<string, RetrievalEvent[]> {
    const groups: Record<string, RetrievalEvent[]> = {};
    for (const event of events) {
      if (!groups[event.queryType]) groups[event.queryType] = [];
      groups[event.queryType].push(event);
    }
    return groups;
  }

  private embeddingSimilarity(a: Float32Array, b: Float32Array): number {
    let dot = 0, magA = 0, magB = 0;
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      magA += a[i] * a[i];
      magB += b[i] * b[i];
    }
    return magA * magB > 0 ? dot / (Math.sqrt(magA) * Math.sqrt(magB)) : 0;
  }

  private keywordMatch(query: string, text: string, tags: string[]): number {
    // TF-IDF style keyword overlap
    const queryWords = new Set(query.toLowerCase().split(/\s+/).filter(w => w.length > 2));
    const textWords = new Set(text.toLowerCase().split(/\s+/).filter(w => w.length > 2));
    const tagWords = new Set(tags.flatMap(t => t.split(/[-_]/)));
    
    let overlap = 0;
    for (const word of queryWords) {
      if (textWords.has(word)) overlap++;
      else if (tagWords.has(word)) overlap += 0.7;
    }
    
    return queryWords.size > 0 ? overlap / queryWords.size : 0;
  }

  private temporalRecency(timestamp: number, now: number): number {
    const diffMs = Math.abs(now - timestamp);
    const diffHours = diffMs / (1000 * 60 * 60);
    return Math.exp(-0.05 * diffHours); // decays to ~0.37 after 20 hours
  }

  private graphProximity(candidate: MemoryNode, recentIds: string[], tkg: Graph): number {
    if (recentIds.length === 0) return 0;
    
    // Average graph distance from candidate to recently accessed nodes
    let totalProximity = 0;
    for (const recentId of recentIds) {
      const distance = tkg.shortestPathLength(candidate.id, recentId);
      // Convert distance to proximity: 1 / (1 + distance)
      // Direct neighbor = 1.0, distance 2 = 0.5, distance 5 = 0.17
      totalProximity += 1 / (1 + distance);
    }
    
    return totalProximity / recentIds.length;
  }
}
```

---

### Deepening: TOP Idea — Fusion Memory Architecture

The Fusion Memory Architecture integrates all 6 techniques into one pipeline: **A-MAC admission → A-MEM linking → AOI compression → MemGrad evolution → Cost-sensitive retrieval → Cross-model verification**. This section presents the complete write/read data flow with complexity analysis at each stage.

**Fusion Architecture Data Flow**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MEMORY WRITE PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SESSION EVENT                                                     │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────────────────┐    O(1)    Stage 1: A-MAC Admission      │
│  │ 5-factor admission    │──────────► ───────────────────────       │
│  │ utility = Σ(w_i·f_i)  │            Score > 0.3?                 │
│  │ confidence (0-1)      │            ├── YES: Continue             │
│  │ novelty (0-1)         │            └── NO:  Discard              │
│  │ recency (0-1)         │                                          │
│  │ type (working/epi/sem)│                                          │
│  └──────────────────────┘                                          │
│       │ (if admitted)                                               │
│       ▼                                                            │
│  ┌──────────────────────┐    O(k·log n) Stage 2: Cross-Model        │
│  │ ADMISSION VERIFICATION  │──────────► Verification               │
│  │ LP-RAG: link prediction │            ┌───────────────────────┐   │
│  │ Claude + DeepSeek       │            │ Both approve?         │   │
│  │ Consensus?              │            │ ├── YES: commit to TKG │   │
│  └──────────────────────┘            │ ├── SPLIT: quarantine   │   │
│       │                              │ └── NO: reject           │   │
│       ▼                              └───────────────────────┘   │
│  ┌──────────────────────┐    O(k)     Stage 3: A-MEM Dynamic       │
│  │ ZETTELKASTEN LINKING  │──────────► Linking                     │
│  │ embedding → link pred │            ├── finds similar nodes      │
│  │ Jaccard intent match   │            ├── creates causal edges    │
│  │ temporal proximity     │            ├── creates temporal edges   │
│  └──────────────────────┘            └── creates contradictory edges│
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    O(c·n)   Stage 4: AOI Compression      │
│  │ HIERARCHICAL COMPRESS  │──────────►                             │
│  │ Working → Episodic    │            ├── Extract key events       │
│  │ Episodic → Semantic   │            ├── Discard verbatim logs    │
│  │ Semantic → Archive    │            ├── Apply 72.4% compression  │
│  └──────────────────────┘            └── -34.4% MTTR              │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    O(1)     Stage 5: MemGrad Evolution    │
│  │ RETRIEVAL WEIGHT UPDATE│──────────► Schedule                    │
│  │ Textual gradient?     │            ├── Buffer retrieval events  │
│  │ Batch of 20 events?   │            ├── Compute textual gradient │
│  │ Update conditional    │            ├── Bounded weight update    │
│  │ overrides             │            └── Validate on held-out set │
│  └──────────────────────┘                                          │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    Eventual Stage 6: FORGE Broadcast      │
│  │ POPULATION BROADCAST  │──────────► (when confidence > 0.85)     │
│  │ Cross-instance sync   │                                          │
│  └──────────────────────┘                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      MEMORY READ PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  USER QUERY                                                        │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────────────────┐    O(log n)  Stage 1: Query Analysis      │
│  │ INTENT + TYPE EXTRACT  │──────────►                             │
│  │ STITCH triple extract  │            ├── query_type: code/debug/  │
│  │ Complexity scoring     │            │     research/planning      │
│  └──────────────────────┘            ├── temporal_markers           │
│       │                              ├── intent_triple              │
│       ▼                              └── complexity_score           │
│  ┌──────────────────────┐    O(1)     Stage 2: Retrieval Weights    │
│  │ MemGrad WEIGHT LOOKUP  │──────────► Lookup                      │
│  │ Match query_type to    │            ├── Default weights?         │
│  │ conditional override   │            └── Conditional override?    │
│  └──────────────────────┘                                          │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    O(log n + k) Stage 3: Cost-Sensitive   │
│  │ RETRIEVAL STRATEGY    │──────────► Store Selection               │
│  │ Simple→Working only   │            ├── Working ( <10MB)         │
│  │ Medium→Working+Epi    │            ├── Episodic (<100MB)         │
│  │ Complex→All layers    │            ├── Semantic (<1GB)          │
│  └──────────────────────┘            └── Archive (unlimited)       │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    O(n·d + k log k) Stage 4: Multi-       │
│  │ COMPOSITE SCORING     │──────────► strategy Retrieval            │
│  │ α·embedding_sim +     │            ├── FAISS dense search      │
│  │ β·keyword_match +     │            ├── Inverted index sparse    │
│  │ γ·temporal_recency +  │            ├── Graph traversal          │
│  │ δ·graph_proximity     │            └── Hybrid scoring           │
│  └──────────────────────┘                                          │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    O(k)     Stage 5: Quarantine Filter    │
│  │ ADVERSARIAL FILTER    │──────────►                              │
│  │ Check quarantine tier │            ├── Remove quarantined items │
│  └──────────────────────┘            └── Unless explicit request   │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐    O(1)     Stage 6: AOI Materialize     │
│  │ LAZY MATERIALIZATION  │──────────►                              │
│  │ Expand summary → full │            ├── Fetch from lower layer   │
│  └──────────────────────┘            └── Return full content       │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────────┐                                           │
│  │ RANKED MEMORIES      │  ← Final output to LLM                   │
│  └──────────────────────┘                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Complexity Analysis Per Stage**:

| Stage | Operation | Time Complexity | Space Complexity | Bottleneck | Mitigation |
|-------|-----------|----------------|-----------------|------------|------------|
| 1. A-MAC Admission | 5-factor scoring | O(1) | O(1) | None | Inline, no I/O |
| 2. Cross-Model Verification | 2 parallel LLM calls + LP-RAG | O(k + LLM) | O(k) | LLM latency (~100ms) | Async parallel, can skip if confidence > 0.95 |
| 3. A-MEM Linking | KNN over embedding index + link prediction | O(k·d + k log k) | O(k) | FAISS search (~5ms for 10K nodes) | Use HNSW index (O(log n)) |
| 4. AOI Compression | Sliding window compression | O(c·n) | O(n) | Large corpus initial pass | Batch during idle; incremental updates |
| 5. MemGrad Evolution | Batch gradient computation (LLM call) | O(m·LLM) | O(m) | LLM call per batch | Idle-time async, batch of 20 |
| 6. Cost-Sensitive Retrieval | Multi-layered search routing | O(log n + log m) | O(1) | None | Pre-computed layer metadata |
| 7. Composite Scoring | 4-strategy weighted scoring | O(n·d + k log k) | O(k) | Embedding similarity (FAISS) | HNSW approximate, top-100 followed by re-rank |
| 8. Quarantine Filter | Hash set membership check | O(k) | O(m_quarantine) | None | Memory-resident hash set |
| 9. Lazy Materialization | Expand from summary | O(l) | O(l) | I/O to lower layer | Pre-fetch hints |

**Total steady-state read latency**: O(log n + n·d + k log k) ~ normally <50ms for typical queries.

**Total write latency**: O(k·log n + 2×LLM + c·n) ~ 200-500ms, acceptable for background memory consolidation.

**Data Flow Through All 6 Stages (Concrete Trace)**:

```typescript
// ============================================================
// Fusion Memory Architecture — Full Write/Read Pipeline
// ============================================================

class FusionMemoryPipeline {
  private amacAdmission: AMACAdmissionControl;
  private crossModelVerifier: CrossModelCritic;
  private tkg: TemporalKnowledgeGraph;
  private aoiCompressor: AOICompressionEngine;
  private memGradOptimizer: MemGradPlusPlus;
  private quarantineMgr: QuarantineManager;
  private costSensitiveRouter: CostSensitiveStoreRouter;

  // === WRITE PATH ===

  async writeMemory(event: SessionEvent): Promise<WriteResult> {
    const startTime = performance.now();
    const trace: string[] = [];

    // Stage 1: A-MAC Admission (fast, mandatory)
    const admissionResult = this.amacAdmission.evaluate(event);
    trace.push(`A-MAC: utility=${admissionResult.utilityScore.toFixed(3)}`);
    
    if (admissionResult.utilityScore < 0.3) {
      return { 
        admitted: false, 
        reason: 'low-utility', 
        latencyMs: performance.now() - startTime,
        trace
      };
    }

    const candidateNode = this.buildCandidateNode(event, admissionResult);

    // Stage 2: Cross-Model Verification (parallel LLM calls)
    const verificationCtx = { sessionId: event.sessionId, turnIndex: event.turnIndex };
    const verificationResult = await this.crossModelVerifier.verify(candidateNode, verificationCtx);
    trace.push(`Verification: ${verificationResult.decision} (confidence=${verificationResult.confidence.toFixed(3)})`);
    
    if (verificationResult.decision === 'reject') {
      return { 
        admitted: false, 
        reason: verificationResult.reason, 
        latencyMs: performance.now() - startTime,
        trace
      };
    }
    
    if (verificationResult.decision === 'quarantine') {
      this.quarantineMgr.admitToQuarantine(candidateNode, verificationResult);
      return {
        admitted: true,
        tier: 'quarantine',
        memoryId: candidateNode.id,
        latencyMs: performance.now() - startTime,
        trace: [...trace, 'quarantined'],
      };
    }

    // Stage 3: A-MEM Dynamic Linking (graph structure)
    const linkingResult = this.tkg.insertWithLinking(candidateNode);
    trace.push(`A-MEM: ${linkingResult.newEdges} edges created (${linkingResult.linkingLatencyMs}ms)`);

    // Stage 4: AOI Compression (hierarchical consolidation)
    this.aoiCompressor.maybeConsolidate(this.tkg);
    // Note: Compression runs asynchronously/batched; trace is approximate
    trace.push(`AOI: compression scheduled`);

    // Stage 5: MemGrad Evolution (batched gradient update)
    this.memGradOptimizer.recordRetrieval(event.query, [candidateNode], event.context);
    // Gradient is computed asynchronously on batch completion
    trace.push(`MemGrad: event recorded for next gradient batch`);

    // Stage 6: FORGE Broadcast (if high confidence)
    if (verificationResult.confidence > 0.85) {
      this.forgeBroadcaster.queue(candidateNode);
      trace.push('FORGE: broadcast queued');
    }

    const totalLatency = performance.now() - startTime;
    
    return {
      admitted: true,
      tier: verificationResult.tier ?? 'episodic',
      memoryId: candidateNode.id,
      latencyMs: totalLatency,
      trace,
    };
  }

  // === READ PATH ===

  async readMemories(
    query: string,
    context: RetrievalContext
  ): Promise<MemoryNode[]> {
    const startTime = performance.now();
    
    // Stage 1: Query analysis (intent extraction, complexity scoring)
    const queryAnalysis = this.analyzeQuery(query, context.audioContext);
    // Returns: { queryType, temporalMarkers, intentTriple, complexityScore }
    
    // Stage 2: MemGrad weight lookup (conditional or default)
    const weights = this.memGradOptimizer.getWeightsForQuery(query, context);
    
    // Stage 3: Cost-sensitive store routing
    const storesToSearch = this.costSensitiveRouter.selectStores(
      queryAnalysis.complexityScore,
      queryAnalysis.queryType
    );
    // Returns: ['working'] or ['working', 'episodic'] or all layers
    
    // Stage 4: Multi-strategy retrieval with composite scoring
    const allCandidates: MemoryNode[] = [];
    
    for (const store of storesToSearch) {
      const candidates = await this.searchStore(store, query, queryAnalysis, weights);
      allCandidates.push(...candidates);
    }
    
    // Deduplicate and sort by composite score
    const unique = this.deduplicate(allCandidates);
    unique.sort((a, b) => b._compositeScore - a._compositeScore);
    const topK = unique.slice(0, context.topK ?? 10);
    
    // Stage 5: Quarantine filter
    const { retrieved, quarantined } = this.quarantineMgr.getExplicitRetrievalResult(topK);
    
    // Stage 6: Lazy materialization (expand summaries to full content)
    const materialized = await Promise.all(
      retrieved.map(m => this.materializeIfNeeded(m, queryAnalysis.complexityScore))
    );
    
    Logger.info(`Fusion read: ${materialized.length} from ${quarantined.length} quarantined (${(performance.now() - startTime).toFixed(0)}ms)`);
    
    return materialized;
  }

  private analyzeQuery(query: string, audioCtx: AudioContext | null): QueryAnalysis {
    return {
      queryType: this.classifyQueryType(query),
      temporalMarkers: this.memGradOptimizer.extractTemporalMarkers(query),
      intentTriple: this.intentExtractor.extract(query),
      complexityScore: this.computeComplexity(query, audioCtx),
    };
  }

  private classifyQueryType(query: string): string {
    const patterns: Array<[RegExp, string]> = [
      [/\b(debug|fix|error|bug|broken|fail|crash)\b/i, 'debug'],
      [/\b(code|implement|write|function|class|method|api|endpoint)\b/i, 'coding'],
      [/\b(research|paper|study|find|search|lookup|document)\b/i, 'research'],
      [/\b(plan|strategy|roadmap|schedule|milestone|next)\b/i, 'planning'],
    ];
    
    for (const [regex, type] of patterns) {
      if (regex.test(query)) return type;
    }
    return 'general';
  }

  private computeComplexity(query: string, audioCtx: AudioContext | null): number {
    const tokenCount = query.split(/\s+/).length;
    const tokenScore = Math.min(1.0, tokenCount / 100);
    
    const questionScore = /\b(why|how|explain|compare|analyze|evaluate|what.*difference)\b/i.test(query) ? 0.6 : 0.2;
    
    const sttScore = audioCtx?.sttConfidence !== undefined
      ? 1 - audioCtx.sttConfidence
      : 0.5; // text input → medium complexity default
    
    return 0.4 * tokenScore + 0.4 * questionScore + 0.2 * sttScore;
  }

  private async searchStore(
    store: string,
    query: string,
    analysis: QueryAnalysis,
    weights: RetrievalWeights
  ): Promise<MemoryNode[]> {
    const storeIndex = this.getStoreIndex(store);
    
    // Parallel search across 4 strategies
    const [denseResults, sparseResults, temporalResults, graphResults] = await Promise.all([
      storeIndex.denseSearch(query, 50),      // FAISS: α
      storeIndex.sparseSearch(query, 50),      // BM25: β
      storeIndex.temporalSearch(analysis.temporalMarkers, 50), // γ
      storeIndex.graphSearch(analysis.intentTriple, 50),       // δ
    ]);
    
    // Merge and composite score
    const merged = this.mergeResults(denseResults, sparseResults, temporalResults, graphResults);
    
    for (const candidate of merged) {
      candidate._compositeScore = 
        weights.alpha * (denseResults.getScore(candidate.id) ?? 0) +
        weights.beta * (sparseResults.getScore(candidate.id) ?? 0) +
        weights.gamma * (temporalResults.getScore(candidate.id) ?? 0) +
        weights.delta * (graphResults.getScore(candidate.id) ?? 0);
    }
    
    return merged;
  }

  private async materializeIfNeeded(memory: MemoryNode, complexity: number): Promise<MemoryNode> {
    // If the memory is currently stored as a summary (AOI-compressed),
    // fetch the full content from the appropriate storage layer.
    if (memory.isSummary && complexity > 0.5) {
      return this.aoiCompressor.materialize(memory);
    }
    return memory;
  }

  private deduplicate(memories: MemoryNode[]): MemoryNode[] {
    const seen = new Set<string>();
    return memories.filter(m => {
      if (seen.has(m.id)) return false;
      seen.add(m.id);
      return true;
    });
  }
}
```

---

## Changelog

**Run 10 (2026-05-31)**: Algorithmic Fusion Deepening for Ideas 8, 9, and the TOP Fusion Memory Architecture:
- Idea 8: Added complete adversarial memory verification pipeline with LP-RAG link prediction model (entity overlap, Katz index, common neighbors), CrossModelCritic with structured verification prompts, and QuarantineManager with auto-resolve, TTL-based eviction, and human review interface. Full TypeScript pseudocode for all components.
- Idea 9: Added MemGrad++ implementation with explicit weight update equations, batch textual gradient computation via LLM prompt template, bounded update + normalization, conditional override system, held-out test set validation with auto-rollback, convergence detection, and Meta-Harness outer-loop search. Full TypeScript pseudocode with all helper methods.
- TOP Idea (Fusion Memory Architecture): Added complete 6-stage write pipeline (A-MAC → Cross-Model → A-MEM → AOI → MemGrad → FORGE) and 6-stage read pipeline (Query Analysis → Weight Lookup → Cost-Sensitive → Composite Scoring → Quarantine Filter → Lazy Materialization). Includes ASCII data flow diagram, complexity analysis table per stage (9 operations), and complete FusionMemoryPipeline TypeScript pseudocode.

---

## Promoted to Plan (B) Breakthrough Tier

**Selected**: Idea 1 (Temporal Knowledge Graph) + Idea 4 (Memory-Augmented Router)

**Rationale**:
- Idea 1: Handles conflicting information (critical for long-term memory), graph structure enables powerful queries
- Idea 4: Direct cost savings (90%+ for repeats), integrates with existing router (§4.5)
- Idea 2: Good but overlaps with existing AOI 3-layer design
- Idea 3: Too high effort for initial release, defer to v2

---

**END OF BRAINSTORM**
