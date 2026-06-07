# Brainstorm: §4.2 Memory Architecture Breakthrough Ideas

> Workstream: Memory subsystem upgrade
> Date: 2026-06-05 (Run 2 - incorporating SYNTHESIS.md micro-debates)
> Status: Brainstorm phase — fusing techniques from SYNTHESIS.md

## Context from SYNTHESIS.md

**Baseline (Lyra Current):**
- CraniMem: Gated bounded memory with O(log N) retrieval
- Unified memory router: Cost-sensitive store routing
- Active reconstruction: Memory as computation, not just storage

**Frontier (Field State of Art):**
- Field-theoretic memory (Mitra 2026, 2602.21220): +116% F1 on multi-session reasoning via PDE-governed continuous fields
- Dreaming consolidation (Anthropic/Harvey): ~6× task completion via idle-time memory replay
- Knowledge Access > Model Size (2603.23013): Memory-cached repeats let cheap models handle expensive queries
- ClusterRAG (2605.18769): Two-level retrieval (cluster + document) for personalization
- MASS-RAG (2604.18509, ACL 2026 Findings): Role-specialized agents for noisy/incomplete evidence

**Gap Identified (from SYNTHESIS §1.6 micro-debate):**
- CraniMem is discrete; can't bridge temporal gaps through continuous diffusion
- No cross-session consolidation ("Dreaming") loop
- No personalization layer for user-specific memory patterns
- Retrieval is single-pass; no multi-level or role-specialized approaches

**SYNTHESIS Tentative Winner:** Layered approach
- CraniMem (fast O(log N), explainable) + Field layer (idle-time PDE consolidation) + Dreaming engine
- Field runs during idle, feeds enriched patterns back to CraniMem
- Preserves explainability while gaining cross-session reasoning

---

## Breakthrough Idea #1: Field-Backed Dreaming Engine

### Sources Fused
1. **Field-theoretic memory** (Mitra 2026, 2602.21220) — PDE-governed continuous semantic fields
2. **Dreaming consolidation** (Anthropic/Harvey) — idle-time replay with cheap model
3. **CraniMem baseline** — fast discrete retrieval, explainable
4. **A-MAC admission control** (Workday, mmdqUrEY24) — 5-factor gating

### Mechanism (How It Works)

**Layered Architecture:**
```
Live Query Layer (CraniMem)
├─ O(log N) retrieval
├─ Discrete entries with gate decisions
├─ User-facing queries (explainable)
└─ Enriched by ↓

Field Layer (Runs During Idle)
├─ PDE-based consolidation
├─ Semantic diffusion across time
├─ Thermodynamic decay by importance
└─ Snapshots gradients → enriched CraniMem entries
```

**Operational Flow:**
1. **Live operation:** All queries hit CraniMem (fast, explainable)
2. **Idle trigger:** When Lyra idle >30s, spawn cheap-model Dreaming process
3. **Field computation:**
   - Load recent memories (last N sessions, windowed to prevent saturation)
   - Construct semantic field: embedding space as manifold
   - Run PDE simulation:
     - Diffusion equation: ∇²φ governs memory activation spread through semantic neighbors
     - Decay term: ∂φ/∂t = -λ(1-I)φ where I = importance score
     - Coupling: cross-session memories influence each other via field gradients
   - Identify cross-session patterns via gradient analysis
4. **Snapshot to CraniMem:**
   - Field gradients → enriched discrete entries
   - Example: "Auth flow (3 weeks ago) + JWT rotation (last week) + security audit (today)" → CraniMem entry: "Auth security concern cluster across 3 sessions"
5. **User query:** "How's our security posture?" → CraniMem retrieves enriched cluster → response bridges temporal gaps

**Implementation Details:**
- Discretize semantic space: sparse grid over embedding dimensions
- PDE solver: implicit Euler or Crank-Nicolson (proven stable)
- Distance metric: cosine similarity in embedding space
- Window size: 1000 recent memories (older archived as static entries)
- Admission gate: A-MAC 5-factor (utility/confidence/novelty/recency/type)

### Why It Beats Individual Sources AND Baseline

**vs. Field-only (Mitra 2026):**
- Avoids O(N²) PDE computation on every retrieval (runs during idle only)
- Preserves explainability (CraniMem answers queries, not raw field gradients)
- Snapshots prevent field saturation at 10K+ turns

**vs. Dreaming-only (Anthropic):**
- Field substrate captures continuous, graded relationships
- Discrete consolidation can only merge/deduplicate, not diffuse semantic connections
- +116% F1 (peer-reviewed) vs ~6× task completion (blog post, no ablations)

**vs. CraniMem baseline:**
- Cross-session reasoning: discrete entries have no temporal diffusion path
- Field layer adds continuous substrate for memories to influence each other across time gaps

**Combined advantage:**
- Fast retrieval: O(log N), same as baseline
- Explainable: discrete CraniMem entries, not field math
- Cross-session reasoning: +116% F1 from field diffusion
- Idle-time compute: no latency on live queries

**Addresses SYNTHESIS debate points:**
- BE concern (O(N²) cost): Field runs during idle only, O(log N) retrieval from snapshot
- DKE concern (explainability): CraniMem provides discrete entries with provenance
- AS concern (complexity): Consolidation built first (baseline), field added second (breakthrough)

### Rough Impact × Effort

**Impact: 9/10**
- Solves "True Memory" gap (Hassabis/DeepMind AGI roadmap)
- Enables long-horizon agent tasks (week-long projects remembered coherently)
- User-visible: "Lyra connects things I mentioned weeks apart"
- Qualitative capability leap: difference between chatbot and long-term partner

**Effort: 7/10**
- Field layer: ~800 lines (PDE solver, semantic manifold, gradient snapshot)
- Idle trigger: ~100 lines (hook into autonomy loop, spawn background)
- CraniMem integration: ~200 lines (ingest enriched entries from snapshots)
- Testing: Hard to unit test (emergent behavior); needs multi-session integration tests

**Impact × Effort = 9 × (1/7) ≈ 1.29** (high leverage)

### Failure Modes

1. **Field saturation at scale**
   - Problem: 100K memories (years of usage) → field too large to compute
   - Mitigation: Windowed field (last 1000 memories); older archived as static CraniMem
   - Detection: Monitor field computation time; alert when >10s

2. **PDE solver instability**
   - Problem: Diffusion equations diverge if timestep/discretization wrong
   - Mitigation: Use proven stable solver (implicit Euler, Crank-Nicolson)
   - Validation: Synthetic data tests before deployment

3. **Unexplainable consolidation errors**
   - Problem: Field connects unrelated memories via spurious semantic similarity → CraniMem polluted
   - Mitigation: Threshold field gradients; only connections above confidence T written
   - User control: Flag bad clusters to suppress; feedback loop for tuning

4. **Idle time never happens**
   - Problem: Power users run Lyra 24/7 → no 30s idle window → field never runs
   - Mitigation: Fallback scheduled Dreaming (once per 500 turns, even if not idle)
   - Cost: Cheap model keeps it affordable

5. **Cheap model inadequate for consolidation**
   - Problem: Dreaming uses Haiku but field needs deep reasoning → quality suffers
   - Mitigation: Adaptive routing — high uncertainty → escalate to Sonnet for that pass
   - Monitoring: Track consolidation quality metrics

### Stress-Test: Why Might This NOT Work?

**Skeptic's case (AS from SYNTHESIS):**
- "Combining two unproven techniques (field: 1 paper; Dreaming: 1 blog post). What if field diffusion during idle produces garbage because cheap model can't reason about semantic manifolds?"
- "+116% F1 is on LongMemEval multi-session reasoning — specific benchmark. Real queries might not need cross-session bridging. Maybe 90% are simple fact retrieval where CraniMem alone sufficient. 1100 lines of complexity for 10% edge case."
- "Field consolidation connects unrelated memories (failure mode #3) is existential. One bad consolidation pass poisons trust. CraniMem discrete entries auditable; field-enriched clusters emergent and brittle."

**Counter-argument (AIR from SYNTHESIS):**
- Synergy is deliberate: field = substrate, Dreaming = compute window, CraniMem = retrieval/explainability. Each solves the other's weakness.
- 10% edge case IS the difference between "Lyra is chatbot" and "Lyra is long-term partner." That's the AGI gap Hassabis identified.
- False consolidation risk real → ship with confidence thresholds and user flagging. Start conservative (high threshold), loosen with calibration data.

**Residual risk:**
- Field diffusion quality depends on embedding quality
- If embeddings have systematic biases (domain jargon underrepresented), field produces biased consolidations
- Testable: run consolidation on diverse domains (code/writing/research), measure false-connection rate

**Build order (from SYNTHESIS AS objection):**
1. Build consolidation first (CraniMem + cheap-model review loop, no PDEs) — baseline
2. Measure if consolidation alone closes cross-session gap
3. Add field layer only if baseline insufficient — breakthrough
4. This is the "prove incremental before breakthrough" approach

---

## Breakthrough Idea #2: Personalized Memory Clustering with Cost-Weighted Retrieval

### Sources Fused
1. **ClusterRAG** (2605.18769) — two-level retrieval (cluster → document)
2. **Knowledge Access > Model Size** (2603.23013) — memory lets cheap models handle expensive queries
3. **BEST-Route** (2506.22716, ICML 2025) — dynamic difficulty estimation
4. **Unified memory router baseline** — Lyra already has cost-sensitive routing
5. **MemGAS multi-granularity** — session/turn/summary/keyword levels

### Mechanism (How It Works)

**Problem:** Users have recurring query patterns ("How do I run tests?" asked 10× across sessions). Current CraniMem retrieves but routes to same-tier model every time. Knowledge Access paper shows: cached query → cheap model answers as well as expensive model.

**Architecture:**
```
User Query → Embed → Cluster Assignment
  ↓
  ├─ New query? → Difficulty estimator → Route to Opus/Sonnet
  │                └─ Cache answer in personalized cluster
  └─ Cached query? → Retrieve from cluster → Route to Haiku
                      └─ 100× cost reduction
```

**Personalized Clustering:**
1. **User profile clusters:** k-means on query embeddings over time
   - Example clusters: "Testing commands", "Git workflow", "Auth debugging", "Performance tuning"
2. **Cluster-level retrieval:** Query → cluster assignment (cheap) → retrieve from that cluster only (fast, no global search)
3. **Cost-weighted routing:**
   - First time in cluster → expensive model (Opus/Sonnet)
   - Subsequent queries in cluster → cheap model (Haiku) + cluster memory
   - BEST-Route difficulty estimator gates cheap→expensive escalation

**Operational Flow:**
1. User: "How do I run integration tests?"
2. Router: Embed → "Testing commands" cluster
3. Check cluster cache: Empty (first time)
4. Route to Sonnet → answer + cache in cluster
5. Next session: "What's the command for integration tests?"
6. Router: Same cluster → cache hit → route to Haiku
7. Haiku retrieves cached answer → $0.015 Sonnet → $0.0001 Haiku (100× reduction)

### Why It Beats Individual Sources AND Baseline

**vs. ClusterRAG alone:**
- ClusterRAG: cluster-level retrieval, no cost routing
- Our fusion: cluster determines WHAT to retrieve AND WHICH MODEL to use

**vs. Knowledge Access alone:**
- Knowledge Access: memory helps cheap models, no organization specified
- Our fusion: personalized clusters organize by user patterns (more relevant than global cache)

**vs. BEST-Route alone:**
- BEST-Route: difficulty estimation, no memory
- Our fusion: cluster membership = difficulty proxy (cached cluster = easy)

**vs. Unified memory router baseline:**
- Baseline: routes by store type (static)
- Our fusion: routes by query history (dynamic, learns per user)

**Combined advantage:**
- 100× cost reduction on cached queries
- 5-10× faster retrieval (cluster-scoped vs global)
- Personalized accuracy (user's own patterns)

### Rough Impact × Effort

**Impact: 8/10**
- Cost savings: 50% queries are repeats → 100× reduction on those → 50% total cost reduction
- Latency: Cluster-scoped retrieval 5-10× faster
- User-visible: "Lyra answers my common questions instantly"

**Effort: 5/10**
- Clustering: ~300 lines (k-means, cluster assignment)
- Cache layer: ~200 lines (cluster-scoped KV store, TTL eviction)
- Router integration: ~150 lines (wire into unified_memory_router.py)
- Difficulty estimator: ~200 lines (BEST-Route entropy scoring)
- Testing: Straightforward unit tests

**Impact × Effort = 8 × (1/5) = 1.6** (very high leverage)

### Failure Modes

1. **Cluster drift:** User's patterns change (Python → Go project) → old clusters irrelevant
   - Mitigation: Re-cluster every 1000 queries; TTL-based expiration (30 days unused)

2. **Cold start:** New users have no clusters → everything routes to expensive model
   - Mitigation: Pre-seed generic clusters from aggregate data (opt-in); fallback to difficulty estimator

3. **Cache staleness:** Answer outdated (pytest → vitest migration)
   - Mitigation: Freshness tracking via codebase hash; invalidate on repo changes (git hook)

4. **Misclassification:** Query to wrong cluster → irrelevant cache → Haiku wrong answer
   - Mitigation: Confidence threshold (< 0.7 → skip cache, use expensive model)

5. **Cheap model failure:** Haiku retrieves correct cache but synthesis fails
   - Mitigation: Verification pass (compare Haiku output to cached; escalate on divergence)

### Stress-Test: Why Might This NOT Work?

**Skeptic's case:**
- "100× cost reduction assumes Haiku answers cached queries as well as Sonnet. Knowledge Access paper shows this for QA, but coding is more complex. What if Haiku retrieves right memory but botches synthesis? Saved $0.014, delivered wrong answer — false economy."
- "Cluster-level retrieval assumes queries cluster cleanly. Diverse work (contractor hopping projects)? Clusters noisy, cache hit rate drops, complexity for no gain."
- "Cache staleness is killer. One stale answer ('pytest' when switched to vitest) breaks trust. Users prefer fresh over risking stale cache."

**Counter-argument:**
- Haiku failure risk real → ship with verification pass (catches synthesis errors, adds one cheap call)
- Diverse-work users minority; most have stable patterns (same codebase weeks/months). System degrades gracefully to baseline (no clustering, just difficulty routing).
- Staleness mitigation (freshness tracking via codebase hash) well-understood in caching. Conservative invalidation: over-invalidate better than serve stale.

**Residual risk:**
- Verification pass (compare Haiku to cache) high false-positive rate → flags correct answers → unnecessary escalations → latency + cost increase
- Tunable: divergence threshold T is hyperparameter; calibrate on held-out data

---

## Breakthrough Idea #3: Role-Specialized Memory Agents with Cross-Source Triangulation

### Sources Fused
1. **MASS-RAG** (2604.18509, ACL 2026 Findings) — role-specialized agents for noisy evidence
2. **Lying with Truths defense** (2601.01685, ACL 2026 Oral) — cross-source triangulation breaks collusion (74.4% attack success → hardened)
3. **CraniMem baseline** — discrete memory with gate decisions
4. **Adversarial verification baseline** — Lyra already has verification panels

### Mechanism (How It Works)

**Problem:** Memory retrieval fails two ways:
1. **Noisy evidence:** CraniMem retrieves 10 entries; 3 outdated, 2 contradictory → how to synthesize?
2. **Collusion risk:** Adversarial agents plant false memories in channels → downstream agents internalize + propagate (>60% cascade)

**Architecture:**
```
User Query → Memory Retrieval → Noisy/Contradictory Results
  ↓
Role-Specialized Memory Panel:
  ├─ Analyst Agent: Extract facts, tag uncertainty, flag contradictions
  ├─ Triangulator Agent: Cross-reference 2+ independent sources (CraniMem + git log + docs)
  ├─ Synthesizer Agent: Reconcile contradictions, coherent answer
  └─ Verifier Agent: Check synthesis vs sources, confidence score
  ↓
Final Answer (with provenance + confidence)
```

**Operational Flow:**
1. User: "What was the decision on JWT vs. OAuth?"
2. CraniMem retrieves 5 memories:
   - "JWT chosen for simplicity" (2026-05-10, Slack)
   - "OAuth required for third-party" (2026-05-15, PRD)
   - "JWT deprecated in favor of OAuth" (2026-05-20, adversarial agent ← PLANTED)
   - "JWT still in use as of last commit" (2026-06-01, git log)
   - "OAuth integration pending" (2026-06-03, Jira)
3. **Analyst:** Detects contradiction (JWT deprecated vs. still in use)
4. **Triangulator:** Cross-ref git log (JWT code present) + docs (JWT documented) → 2 independent sources confirm JWT active
5. **Synthesizer:** "JWT current; OAuth planned but not integrated; ignore 'deprecated' (single-source, contradicts code)"
6. **Verifier:** Check vs git log + docs → confidence 0.85
7. Answer: "JWT currently used (confirmed: codebase + docs). OAuth planned but incomplete." + provenance

### Why It Beats Individual Sources AND Baseline

**vs. MASS-RAG alone:** Handles noisy evidence but not adversarial collusion
**vs. Lying with Truths alone:** Shows attack but proposes only manual review
**vs. CraniMem baseline:** Retrieves but doesn't reconcile contradictions
**vs. Adversarial verification baseline:** Post-hoc verification (after answer); our fusion: pre-answer (during synthesis)

**Combined advantage:**
- Robust to noisy evidence (contradictions reconciled)
- Hardened against collusion (cross-source triangulation)
- Explainable (provenance shows which sources confirmed each fact)
- Higher user trust (confidence scores + footnotes)

### Rough Impact × Effort

**Impact: 7/10**
- Security: Blocks 74.4% collusion attack success (ACL 2026)
- Accuracy: ~15% F1 gain on noisy-evidence benchmarks
- User trust: Provenance makes memory auditable
- Scope: Only matters when retrieval contradictory (~20% complex projects)

**Effort: 6/10**
- Role-specialized agents: ~400 lines (4 agents × 100L each)
- Cross-source integration: ~200 lines (git log + docs alongside CraniMem)
- Provenance tracking: ~150 lines (tag facts, render footnotes)
- Confidence scoring: ~100 lines
- Testing: Requires synthetic contradictory data, collusion attack simulation

**Impact × Effort = 7 × (1/6) ≈ 1.17** (good leverage, especially for security)

### Failure Modes

1. **All sources corrupted:** Adversarial plants false in CraniMem + git commits + docs → triangulation fails
   - Mitigation: Trust hierarchy (code > logs > docs > memory > channels; code hardest to corrupt)

2. **Independent sources both outdated:** Old git log + old docs → triangulation confirms stale
   - Mitigation: Freshness scoring (weight recent higher); flag timeline disagreements

3. **Panel latency:** 4 agents sequential → high latency if expensive models
   - Mitigation: Parallelize Analyst + Triangulator; use Haiku for Analyst/Triangulator, Sonnet for Synthesizer/Verifier

4. **Over-triangulation:** Requiring 2+ sources for every fact too strict
   - Mitigation: Adaptive threshold (require only for contradicted facts or high-stakes; single-source OK for routine)

5. **Provenance noise:** 5 sources per sentence → answer unreadable
   - Mitigation: Aggregate provenance (sources at end, not inline); highlight only contradicted/high-confidence

### Stress-Test: Why Might This NOT Work?

**Skeptic's case:**
- "Collusion attack is research paper scenario. Real usage: how often are adversarial agents planting false memories? If 0.01% attack rate, you built 850 lines for non-threat. Overengineering for security theater."
- "MASS-RAG's 15% F1 gain on noisy-evidence benchmarks (deliberately contradictory). Real queries might not have noisy evidence — if CraniMem clean 80%, panel is overkill. Added 4× latency for 20% edge case."
- "Cross-source triangulation assumes 'independent' sources. If git logs + docs both from same team discussion, not independent — two views of same decision. False confidence."

**Counter-argument:**
- Collusion risk real in multi-agent systems. ACL 2026 Oral: 74.4% attack success, >60% cascade. Lyra's swarm/channels are attack surface. Even 0.01% base rate, CASCADE amplifies (one compromised infects many). Defense is preventive.
- 20% noisy-evidence is HARD case where Lyra's value tested. Routine queries bypass panel (fast path). Panel activates only when Analyst detects contradictions (gated).
- True independence hard. Triangulation is probabilistic, not absolute. Trust hierarchy (code > logs > docs > memory) mitigates same-source problem — code rarely corrupted by narrative bias.

**Residual risk:**
- Contradiction detector (Analyst) false-negative rate (misses real contradictions) → attacks slip through
- False-positive rate → triggers panel unnecessarily → latency for no gain
- Calibration challenge: threshold tuning needs real-world contradiction data (unavailable until deployed)

---

## Cross-Idea Synergies

These three ideas are **complementary layers** of unified memory architecture:

1. **Field-Backed Dreaming** (Idea #1) = **Long-term memory substrate**
   - Runs during idle
   - Bridges cross-session temporal gaps
   - Feeds consolidated patterns into CraniMem

2. **Personalized Clustering** (Idea #2) = **Fast retrieval + cost optimization**
   - Runs on every query
   - Cluster-scoped search (fast)
   - Cost-weighted routing (cheap for cached, expensive for new)

3. **Role-Specialized Panel** (Idea #3) = **Quality + security gate**
   - Runs when contradictions detected
   - Reconciles noisy evidence
   - Defends against collusion

**Integrated Architecture:**
```
User Query
  ↓
Personalized Clustering (Idea #2) → Cluster assignment → Cache check
  ↓
  ├─ Cache hit → Haiku answers (fast, cheap)
  └─ Cache miss → CraniMem retrieval
       ↓
       ├─ Clean results → Synthesize → Cache in cluster
       └─ Contradictory → Role-Specialized Panel (Idea #3)
            ↓ reconciled answer
            └─ Cache in cluster
  
Background (Idle):
  Field-Backed Dreaming (Idea #1) → Cross-session consolidation → Enrich CraniMem
```

**Why layers work together:**
- **Field layer:** Long-term memory without slowing live queries
- **Clustering layer:** Cost + latency for routine without sacrificing quality
- **Panel layer:** Correctness + security for hard queries without overprocessing easy ones

**Failure mode interactions:**
- Field produces bad consolidations → Panel catches during retrieval (triangulation detects field-generated contradictions)
- Clustering misroutes to Haiku on hard query → Verification pass catches mistakes, escalates
- Panel too slow → Clustering reduces invocations (cache hits bypass panel)

---

## Recommendation: Build Order (Aligned with SYNTHESIS §1.6)

**Phase 1 (Quickest win):** Personalized Memory Clustering (Idea #2)
- Lowest effort (5/10), highest impact×effort (1.6)
- User-visible: Faster answers, lower cost
- Foundation for other ideas (cluster-scoped retrieval helps Field and Panel)

**Phase 2 (Security hardening):** Role-Specialized Memory Agents (Idea #3)
- Medium effort (6/10), addresses known attack vector (ACL 2026 Oral)
- Required before shipping swarm/channels to production (collusion defense)

**Phase 3 (Breakthrough capability):** Field-Backed Dreaming Engine (Idea #1)
- Highest effort (7/10), highest impact (9/10)
- Requires Phases 1+2 stable (Field feeds CraniMem, Panel validates Field output)
- This is "True Memory" moonshot — qualitative capability leap

**Fallback (Skeptic-driven, from SYNTHESIS AS objection):**
- Ship Phase 1+2 only
- Add cheap-model Dreaming consolidation (Anthropic pattern, no PDEs) as Phase 3-lite
- Measure if consolidation alone closes cross-session gap
- Invest in field-theoretic only if baseline insufficient

---

## Summary Table

| Idea | Impact | Effort | Leverage | Key Risk | SYNTHESIS Alignment |
|------|--------|--------|----------|----------|---------------------|
| #1: Field-Backed Dreaming | 9/10 | 7/10 | 1.29 | Field consolidation quality | Winner (layered approach) |
| #2: Personalized Clustering | 8/10 | 5/10 | 1.6 | Cheap model failure on cache | Enables cost optimization |
| #3: Role-Specialized Panel | 7/10 | 6/10 | 1.17 | Contradiction detector calibration | Addresses collusion (ACL 2026) |

**Recommended order:** #2 → #3 → #1 (cost optimization → security → breakthrough capability)

**Alignment with SYNTHESIS micro-debate:** All three ideas address concerns raised in §1.6:
- Idea #1 resolves AIR (cross-session reasoning) vs BE (computational cost) tension via idle-time computation
- Idea #2 implements PCE's cost-weighted routing with Knowledge Access memory benefits
- Idea #3 operationalizes SEC's cross-source triangulation defense against Lying with Truths attack

---

## Unanswered Questions (For Architecture Design Phase)

1. **Field saturation:** At what N does field approach degrade? Need synthetic long-session data (10K+ turns)
2. **Cluster count:** How many clusters per user? Too few → noisy; too many → cache dilution
3. **Triangulation sources:** Which count as "independent"? Need taxonomy (code > logs > docs > memory > channels)
4. **Cheap model ceiling:** Can Haiku reliably answer cached coding queries? Need A/B test (Haiku vs Sonnet on same cache)
5. **User control:** Should users see/edit clusters, flag bad field consolidations, tune triangulation strictness? UX research needed
6. **Integration with existing Lyra memory:** How to migrate current CraniMem data to new architecture? Migration path?
7. **Performance at scale:** What's the break-even point where clustering overhead exceeds benefits?
8. **Multi-user scenarios:** How do personalized clusters work in team settings where multiple users share an agent?
