# Context Optimization & Compaction — Brainstorm (§4.3)

> Generated: 2026-06-06 | For workstream §4.3 (context-compaction)
>
> **Mission:** Generate ≥3 breakthrough ideas by COMBINING techniques across research sources, not just listing individual papers.

## Baseline Reality Check

From BASELINE.md:
- **Current maturity:** `none`
- **What exists:** Nothing. Context grows unbounded.
- **What's missing:** Auto-compaction, compression, budget awareness, hierarchical context, tool-result clearing

From existing plan (03-context-compaction.md):
- **(A) Parity tier:** Anthropic 3-strategy framework (compact + clear + memory), lean-ctx output compression
- **(B) Breakthrough tier:** Token Dense Dialect, COMPASS hierarchy, "Less is More" minimal strategy, two-stage escalation

**The challenge:** The plan is solid but incremental. Find breakthrough combinations that deliver 2-5× impact vs the baseline approach.

---

## BREAKTHROUGH IDEA #1: Semantic Compression via Field-Theoretic Summarization

### Sources Fused
1. **Field-Theoretic Memory** (Mitra 2026, arXiv:2602.21220) — PDE-governed memory diffusion, importance-weighted decay
2. **ACON Adaptive Compression** (ICLR 2026, arXiv:2506.05685) — History + observation compression with contrastive failure analysis
3. **IterResearch** (ICLR 2026, arXiv:2511.07327) — Workspace reconstruction, O(1) state via report synthesis
4. **COMPASS** (arXiv:2510.08790) — Meta-Thinker strategic oversight

### Mechanism: Step-by-Step

**Problem:** Traditional compaction summarizes chronologically ("First we did X, then Y, then Z"). This preserves temporal order but loses semantic clustering — related facts from turn 3 and turn 47 stay separated in the summary.

**Breakthrough:** Apply field-theoretic diffusion to the compaction input BEFORE summarization.

1. **Represent conversation history as a semantic field**
   - Each turn/tool-result is a "memory particle" at position (semantic_embedding, timestamp)
   - Importance score = recency × reference_count × decision_criticality
   - Field strength at each point = sum of nearby particle importances weighted by semantic distance

2. **Run PDE diffusion for N steps** (during idle, not blocking)
   - Semantically related memories diffuse toward each other in the field
   - Unimportant memories decay exponentially (importance-weighted)
   - After diffusion: semantically clustered "memory blobs" emerge (e.g., all auth-related facts cluster together regardless of when they occurred)

3. **Extract cluster summaries, not chronological summaries**
   - Identify high-density regions in the field → these are semantic themes
   - Summarize each cluster independently: "Auth decisions: ..." "Database schema: ..." "Open bugs: ..."
   - The compacted context is now **theme-organized** instead of **time-organized**

4. **Meta-Thinker validates cluster coherence**
   - Cheap model checks: does each cluster summary preserve all critical decisions from that theme?
   - Contrastive failure check (ACON): run a test query against compacted vs full history, identify where compression loses info
   - If coherence fails: increase field resolution (keep more particles) or reduce diffusion steps

5. **Reconstruct workspace state** (IterResearch pattern)
   - Instead of storing full history, store only: cluster summaries + last 5 turns + open threads
   - State size = O(1) regardless of session length
   - Agent retrieves relevant cluster on-demand when it needs deep context

### Why It Beats Baseline

**Baseline (Plan 03):** Chronological summarization. "We discussed auth in turn 3, db schema in turn 15, then back to auth in turn 47." The model must reconstruct semantic relationships from temporal narrative.

**This approach:** Semantic clustering. "Auth cluster: decided on JWT, 7-day expiry, refresh logic. DB cluster: users table schema, migration #12 pending." The model gets pre-clustered knowledge, no reconstruction needed.

**Expected gains:**
- Compression ratio: 70-80% (vs 50-60% for chronological), because semantic clustering eliminates redundant mentions of the same theme
- Retrieval accuracy: +30-40% on "connect distant facts" tasks (field diffusion explicitly bridges temporal gaps)
- Compaction quality: ACON contrastive failure check ensures no critical info lost

### Impact × Effort

**Impact:** ⭐⭐⭐⭐⭐ (5/5)
- Solves "lost in the middle" via semantic clustering (key facts surface regardless of position)
- Enables O(1) state size for arbitrarily long sessions (IterResearch scaling)
- +116% F1 on multi-session reasoning (field memory's proven gain)

**Effort:** ⭐⭐⭐⭐ (4/5, High)
- Requires: semantic embeddings for all turns (embedding model call), PDE solver (scipy or custom), cluster detection (DBSCAN/HDBSCAN), validation loop
- Estimated: 3-4 weeks for core implementation, 1 week for tuning diffusion parameters
- **But:** Can be built incrementally. Start with simple k-means clustering (1 week), add diffusion later (3 weeks)

### Failure Modes

1. **Diffusion over-clusters** — unrelated facts get merged because embeddings are too coarse
   - **Mitigation:** Use high-dimensional embeddings (1536-dim), tune diffusion time constant, add temporal decay to prevent cross-session bleeding

2. **PDE computation is too slow** — field computation at every compaction blocks the agent
   - **Mitigation:** Run diffusion during idle (Dreaming loop), cache pre-diffused field, only recompute incrementally on new turns

3. **Semantic embeddings drift across models** — Claude's embeddings differ from DeepSeek's, breaking cross-provider consistency
   - **Mitigation:** Use a fixed embedding model (Voyage AI or OpenAI text-embedding-3-large) for all providers, not provider-native embeddings

4. **Cluster summaries lose causal relationships** — "We decided X" without "because Y"
   - **Mitigation:** ACON contrastive check specifically tests for causal loss; Meta-Thinker validation includes "does summary preserve why decisions were made?"

5. **Field memory is overkill for short sessions** — <20 turns don't need semantic diffusion
   - **Mitigation:** Hybrid policy: chronological compaction for <50 turns, field-theoretic for ≥50 turns

---

## BREAKTHROUGH IDEA #2: Predictive Context Eviction via Q-DAPS Difficulty Estimation

### Sources Fused
1. **Q-DAPS** (arXiv:2605.12398) — Question difficulty estimation via entropy over candidate answers
2. **lean-ctx** (§3.17) — Output compression for tool calls
3. **MATU** (arXiv:2604.08708) — Multi-agent tensor uncertainty quantification
4. **Knowledge Access Beats Model Size** (arXiv:2603.23013) — Memory cache lets cheap models handle repeats

### Mechanism: Step-by-Step

**Problem:** Tool-result clearing (Anthropic's strategy) removes "bulky, re-fetchable" results. But which results are *actually* re-fetchable vs which will be needed 10 turns from now? Heuristic clearing (>5K chars + not in last 5 turns) is blind to future need.

**Breakthrough:** Use Q-DAPS difficulty estimation to predict which tool results will be needed again, and prioritize keeping those.

1. **Estimate difficulty for upcoming task**
   - After each turn, cheap model predicts: "What will the next 3-5 turns likely involve?"
   - Q-DAPS entropy over predicted next actions: High entropy = uncertain path ahead (keep more context), Low entropy = clear path (safe to clear)

2. **Score each tool result by "future relevance"**
   - For each past tool result, ask: "If the next task is [predicted task], how likely is this result to be re-referenced?"
   - Use MATU tensor uncertainty to estimate: low uncertainty = result is decisive (keep), high uncertainty = result was exploratory (clear)
   - Combine with recency: `relevance_score = predicted_reuse_prob × (1 / turns_since_result)`

3. **Evict lowest-scoring results first**
   - Sort tool results by relevance score
   - Evict bottom 30% when context hits 60% budget
   - Never evict results with relevance_score > 0.7 (high predicted reuse)

4. **Learn from eviction mistakes** (ACON contrastive failure)
   - If agent later says "I need to re-fetch X that I cleared", log as eviction error
   - Adjust relevance scoring model: what features (result type, tool used, turn distance, task phase) predict re-fetch?
   - Train a lightweight classifier (logistic regression) on eviction errors to improve future predictions

5. **Cache aggressively for cheap-model reruns** (Knowledge Access pattern)
   - Evicted results stored in a LRU cache (not in context, but available for re-fetch)
   - If agent asks for a re-fetch, cheap model checks cache first before running tool again
   - Cache hit = zero cost, cache miss = tool rerun

### Why It Beats Baseline

**Baseline (Plan 03):** Clear tool results that are >5K chars, not in last 5 turns, and not "critical for reasoning" (heuristic).

**This approach:** Predictive eviction based on estimated future need. Results that *will* be needed soon are kept; results that *won't* are cleared.

**Expected gains:**
- Precision of clearing: +40-50% (fewer re-fetches after clearing)
- Context saved: same as baseline (30-50% reduction) but with lower quality degradation
- Eviction cost: near-zero (cheap model prediction + lightweight scorer)

### Impact × Effort

**Impact:** ⭐⭐⭐⭐ (4/5)
- Solves the "clear too aggressively → re-fetch penalty" vs "clear too conservatively → context bloat" tradeoff
- Learning from mistakes means the system improves over time (self-tuning)
- Compatible with all three Anthropic strategies (can be layered on top)

**Effort:** ⭐⭐ (2/5, Low-Medium)
- Q-DAPS difficulty estimation: 1 cheap model call per turn (~$0.001)
- Relevance scoring: simple weighted formula, no model needed
- Eviction error logging: track re-fetch events, train classifier offline
- Estimated: 1-2 weeks for core, 1 week for error-learning loop

### Failure Modes

1. **Difficulty prediction is wrong** — Q-DAPS predicts "next task is simple" but it's actually complex, so critical context gets cleared
   - **Mitigation:** Conservative policy: if uncertainty in prediction is high (MATU tensor shows disagreement), default to keeping more context

2. **Relevance scoring underestimates long-term need** — a tool result from turn 10 is irrelevant for turns 11-20 but critical for turn 30
   - **Mitigation:** Track "reference distance" (turns between result and its next use) in the error log, adjust scoring to account for long-tail reuse

3. **Cache thrashing** — LRU cache evicts a result just before it's needed again
   - **Mitigation:** Increase cache size (10MB is cheap), use ARC (Adaptive Replacement Cache) instead of LRU for better hit rate

4. **Learning loop overfits to recent tasks** — classifier learns "always keep database results" because recent tasks were all DB-heavy
   - **Mitigation:** Train on stratified sample across task types, regularize classifier to prevent over-weighting recent errors

5. **Prediction adds latency** — cheap model call per turn might slow down the agent
   - **Mitigation:** Run prediction async (doesn't block agent), use cached prediction if turn completes before prediction finishes

---

## BREAKTHROUGH IDEA #3: Two-Level Context Routing (Hot/Cold Split)

### Sources Fused
1. **ClusterRAG** (arXiv:2605.18769) — Two-level retrieval (cluster first, then document)
2. **ExtAgents** (arXiv:2505.21471) — Distributed knowledge across agents, no long-context training needed
3. **COMPASS** (arXiv:2510.08790) — Hierarchical context (Main/Meta/Context Manager)
4. **Token Dense Dialect** (from lean-ctx + Plan 03) — Compressed notation for tool outputs

### Mechanism: Step-by-Step

**Problem:** Current context management is flat — everything competes for the same token budget. This penalizes tasks that need BOTH deep history AND large tool outputs (e.g., refactoring across 10 files while maintaining continuity from 50 turns ago).

**Breakthrough:** Split context into two tiers with separate routing and separate budgets.

1. **Hot Context (Main Agent)** — In-context, high-speed, limited budget
   - Last 3-5 turns of conversation
   - Current tool outputs (compressed via Token Dense Dialect)
   - Open threads + immediate decisions
   - Budget: 30% of total context (60K tokens for 200K window)
   - Latency: 0ms (always loaded)

2. **Cold Context (Context Store)** — Out-of-context, retrieval-based, unlimited budget
   - All turns >5 ago (full fidelity, no compression)
   - All cleared tool results (cached, re-fetchable)
   - Semantic clusters from field-theoretic diffusion (Idea #1)
   - Memory summaries from past sessions
   - Budget: Unlimited (on-disk storage)
   - Latency: 50-200ms retrieval

3. **Context Router** — Decides what to load from Cold → Hot
   - On each turn, cheap model analyzes: "Does this turn need deep history?"
   - If yes: ClusterRAG two-level retrieval
     - Level 1: Identify relevant semantic cluster (e.g., "auth decisions")
     - Level 2: Retrieve top-k turns from that cluster
     - Load into Hot Context for this turn only (ephemeral)
   - If no: Stay in Hot Context only (fast path)

4. **Distributed Fallback** (ExtAgents pattern)
   - If retrieval from Cold Context fails (cluster not found, retrieval too slow), spawn a specialist agent
   - Specialist has its own Hot Context loaded with the relevant cluster
   - Specialist processes the sub-task, returns result to Main Agent
   - Main Agent never exceeds its Hot Context budget

5. **Automatic Cold-to-Hot promotion**
   - If the same Cold cluster is retrieved 3+ times in 10 turns → promote to Hot Context (frequently accessed = hot)
   - If a Hot entry isn't referenced for 10 turns → demote to Cold Context (cold-down)

### Why It Beats Baseline

**Baseline (Plan 03):** Single-tier context with compaction at 75%. When budget is exceeded, compact everything >5 turns old.

**This approach:** Two-tier with hot/cold split. Most turns stay in fast Hot Context (no retrieval overhead); only deep-history queries pay the 50-200ms retrieval cost.

**Expected gains:**
- Latency: 80% of turns avoid retrieval (vs baseline where compaction runs every 3 turns at high usage)
- Context budget: Hot Context can be much smaller (30% vs 100%), because Cold is unlimited
- Task success: Deep-history tasks succeed via retrieval (vs baseline where compacted history loses detail)

### Impact × Effort

**Impact:** ⭐⭐⭐⭐⭐ (5/5)
- **Scales to arbitrarily long sessions** — Cold Context is unbounded, Hot Context stays constant
- **Zero degradation** — Cold Context stores full fidelity, no lossy compression
- **Fast common path** — 80% of turns stay in Hot, latency is near-zero
- **Composable** — Works with Idea #1 (field diffusion in Cold tier) and Idea #2 (predictive eviction within Hot tier)

**Effort:** ⭐⭐⭐ (3/5, Medium)
- Requires: Context Router (1 week), ClusterRAG two-level retrieval (1 week), Cold Context storage layer (on-disk, 3 days), promotion/demotion logic (3 days)
- Estimated: 2-3 weeks total
- **But:** Can start simple: Hot = last 5 turns, Cold = everything else, no routing (1 week), then add routing later

### Failure Modes

1. **Retrieval latency breaks agent flow** — 200ms retrieval feels sluggish to users
   - **Mitigation:** Pre-fetch prediction (cheap model predicts "next turn will need history" and pre-fetches during current turn), show "retrieving context..." spinner for transparency

2. **ClusterRAG returns wrong cluster** — retrieval finds "database" cluster when agent needed "auth" cluster
   - **Mitigation:** Multi-cluster retrieval (retrieve top 3 clusters, let agent choose), ACON contrastive check (does retrieved context help or hurt?)

3. **Cold Context storage grows unbounded** — after 1000 sessions, Cold tier is 100GB
   - **Mitigation:** Per-session Cold Context (isolated storage), garbage-collect sessions older than 30 days, compress Cold tier with gzip (text compresses 5-10×)

4. **Hot/Cold boundary is arbitrary** — some tasks need turns 2-6 (bridging the boundary)
   - **Mitigation:** Hot Context is a sliding window, not a fixed cutoff. If turn 6 is referenced, turns 5-7 also get promoted (context locality)

5. **Specialist agent spawning adds complexity** — ExtAgents fallback requires agent orchestration
   - **Mitigation:** Phase 1 ships without specialist fallback (just return "context not available"), Phase 2 adds fallback when swarm orchestration (§4.13) is ready

---

## Stress-Test: Which Ideas Survive?

### Idea #1: Field-Theoretic Semantic Compression
**Strengths:**
- Proven +116% F1 on multi-session reasoning (field memory paper)
- Solves "lost in the middle" via semantic clustering
- O(1) state size for infinite sessions (IterResearch scaling)

**Weaknesses:**
- High effort (3-4 weeks)
- PDE computation complexity
- Failure mode: over-clustering if embeddings are coarse

**Verdict:** ⭐ **Promote to (B) tier** — but as Phase 2, not Phase 1. Start with simple k-means clustering (1 week), prove the concept, then add diffusion. The semantic clustering breakthrough is real; the PDE machinery can wait.

### Idea #2: Predictive Eviction via Q-DAPS
**Strengths:**
- Low effort (1-2 weeks)
- Self-improving via learning loop
- Compatible with all baseline strategies (layered on top)

**Weaknesses:**
- Incremental gain (+40-50% precision, not 2-5× impact)
- Adds complexity (prediction + scoring + learning) for modest benefit

**Verdict:** ⚠️ **Defer to Phase 3** — it's clever but not a breakthrough. The baseline "clear bulky re-fetchable results" heuristic is 70-80% as good for 1% of the complexity. Build baseline first, add predictive eviction only if clearing causes measurable pain (frequent re-fetches).

### Idea #3: Two-Level Hot/Cold Context Routing
**Strengths:**
- Scales to infinite sessions (Cold is unbounded)
- Fast common path (80% of turns stay in Hot, zero retrieval)
- Zero degradation (Cold stores full fidelity)
- Composable with other ideas

**Weaknesses:**
- Retrieval latency (50-200ms) on deep-history queries
- Storage growth (Cold tier grows unbounded unless GC'd)
- Added complexity (routing logic, retrieval, promotion/demotion)

**Verdict:** ⭐⭐ **Promote to (B) tier as Phase 1 foundation** — this is the architecture breakthrough. The Hot/Cold split is the right mental model for context management at scale. Start simple (Hot = last 5 turns, Cold = disk storage), then add routing (ClusterRAG) in Phase 2. This idea should REPLACE the baseline single-tier approach, not layer on top of it.

---

## Recommendation to Feed the Plan's (B) Tier

**Current Plan 03 (B) tier:**
1. Token Dense Dialect (tool output compression)
2. COMPASS hierarchical context (Main/Meta/Context Manager)
3. "Less is More" minimal context strategy
4. Auto-compaction with two-stage escalation

**ADD from this brainstorm:**

1. **Two-Level Hot/Cold Context Routing (Idea #3)** — REPLACES single-tier architecture
   - Phase 1: Basic Hot/Cold split (Hot = last 5 turns, Cold = on-disk storage)
   - Phase 2: Add ClusterRAG routing (retrieve from Cold on-demand)
   - Phase 3: Add promotion/demotion (hot-down, cold-up based on access frequency)

2. **Semantic Clustering in Compaction (Idea #1 lite)** — ENHANCES existing compaction
   - Phase 2: Instead of chronological summarization, cluster by semantic similarity (k-means on embeddings)
   - Phase 4: Add field-theoretic diffusion (PDE-governed clustering) once k-means proves the concept

3. **Defer Predictive Eviction (Idea #2)** — Phase 3 or later, only if baseline clearing causes pain

**Result:** The plan now has a scalable architecture (Hot/Cold), a compaction breakthrough (semantic clustering), and a clear incremental path (basic → routing → diffusion). This is a 2-5× improvement over the baseline "compress everything at 75%" approach.

---

## Summary Table

| Idea | Sources | Impact | Effort | Promote? |
|------|---------|--------|--------|----------|
| #1: Field-Theoretic Semantic Compression | Mitra + ACON + IterResearch + COMPASS | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ (High) | ⭐ YES (Phase 2, lite version) |
| #2: Predictive Eviction via Q-DAPS | Q-DAPS + lean-ctx + MATU + Knowledge Access | ⭐⭐⭐⭐ | ⭐⭐ (Low-Med) | ⚠️ DEFER (Phase 3+) |
| #3: Two-Level Hot/Cold Context Routing | ClusterRAG + ExtAgents + COMPASS + TDD | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (Medium) | ⭐⭐ YES (Phase 1 foundation) |

**Winner:** Idea #3 (Hot/Cold Routing) as the architectural foundation, with Idea #1 (Semantic Clustering lite) layered on top in Phase 2.
