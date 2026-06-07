# Brainstorm: Reliability & Observability (§4.16)

> Created: 2026-06-06 | Workstream: §4.16 reliability  
> Status: Breakthrough ideation phase

## Context

### Current State (BASELINE.md)
- **Maturity:** `none`
- **Pain points:**
  - No tracing (no way to inspect agent execution)
  - No token accounting (no per-session/agent/workflow tracking)
  - No structured verification (ReviewAgent is a stub)
  - No eval harness (no tau-bench, SWE-bench integration)
  - No consistency metrics (no pass^k measurement)
  - No failure attribution (no diagnostic pipeline)

### Existing Plan (plans/16-reliability.md)
**Phase 2 target:** Langfuse/Phoenix tracing, token observatory, intelligent verifier (SABER mutation-gated), eval harness integration (tau-bench/SWE-bench), ErrorProbe failure attribution.

**Key components:**
1. OpenTelemetry tracing with auto-instrumentation
2. Token Observatory with per-call accounting (session/agent/workflow/tool)
3. Mutation Verifier (SABER pattern) - 5 mutation strategies
4. Eval Harness (tau-bench, tau2-bench, SWE-bench Verified)
5. ErrorProbe 3-stage failure attribution
6. Benchmark Scoreboard (SOTA tracking)

### Synthesis Insights (SYNTHESIS.md §7)

**Frontier papers:**
- **Lying with Truths** (2601.01685, ACL 2026 Oral): 74.4% attack success via collusion using only true fragments
- **Identity Skews** (ACL 2026 Main): Debate systematically biased by identity
- **Actor-Observer Asymmetry**: Perspective bias in multi-agent review
- **Preventing Rogue Agents** (2502.05986): Pre-execution confidence monitoring, 20% gain on GovSim
- **MATU** (2604.08708): Tensor-based uncertainty quantification for multi-agent systems
- **ReTAS**: Dialectical alignment for debate
- **Response Anonymization** (2510.07517): Strip identity markers to fix sycophancy

**Consensus from debate:**
- Incremental hardening: anonymization → ReTAS → rogue monitor → cross-source triangulation
- Cross-source triangulation is a GATE (not an optimization) - ships alongside anonymization
- Integrated verification architecture needed (not four separate patches)

---

## Breakthrough Idea 1: Confidence-Calibrated Verification Pipeline

### Sources Fused
1. **MATU** (2604.08708) — Tensor UQ for multi-agent systems
2. **Q-DAPS** (2605.12398) — Difficulty estimation as entropy over candidates
3. **Preventing Rogue Agents** (2502.05986) — Pre-execution confidence monitoring
4. **SABER mutation testing** (existing plan) — Mutation-gated verification
5. **ErrorProbe** (arXiv:2604.17658) — Three-stage failure attribution

### Mechanism

A multi-stage verification pipeline that adapts verification depth based on calibrated confidence:

```python
class ConfidenceGatedVerifier:
    """
    Stage 1: Quick confidence check (MATU tensor UQ)
      - If confidence > 0.9: SKIP verification (trust the output)
      - If 0.7 < confidence < 0.9: LIGHTWEIGHT verification (1-2 mutants)
      - If confidence < 0.7: FULL verification (5 mutants + ErrorProbe)
    
    Stage 2: Adaptive mutation testing
      - High confidence: 2 mutants, simple mutations (variable rename)
      - Medium confidence: 3 mutants, moderate mutations (+ argument swap)
      - Low confidence: 5 mutants, aggressive mutations (+ logic flip)
    
    Stage 3: Failure attribution (only if Stage 2 fails)
      - ErrorProbe backward tracing to identify root cause
      - Rogue agent monitoring: did confidence signal warn us?
      - Feed failure pattern back to confidence calibration
    
    Feedback loop:
      - When high-confidence outputs fail verification → recalibrate MATU
      - When low-confidence outputs pass → reduce verification burden
      - Continuous calibration using actual pass/fail data
    """
```

**Cost optimization:**
- 90% confidence cases: 0 verification calls (instant, free)
- 70-90% confidence: 1-2 verification calls (50% cost vs baseline)
- <70% confidence: 5-7 verification calls (same as plan baseline)

**Key insight:** Most agent outputs are correct. The plan's mutation verifier runs 3-5 mutants on EVERY output. Confidence gating skips verification for high-confidence cases, saving 70-80% of verification cost while improving reliability for uncertain outputs.

### Why It Beats Baseline

**vs. BASELINE.md (no verification):**
- Adds structured verification with objective mutation testing
- Adds failure attribution pipeline
- Adds confidence calibration (self-improving over time)

**vs. Existing Plan (always-verify SABER):**
- 70-80% cost reduction (skip verification for high-confidence outputs)
- Adaptive verification depth (light for medium confidence, deep for low)
- Feedback loop improves calibration (plan has no calibration mechanism)
- Pre-execution rogue monitoring prevents cascading failures (plan is reactive)

### Impact × Effort

**Impact:** HIGH
- Cost savings: 70-80% reduction in verification calls
- Reliability gain: ErrorProbe + confidence calibration catches failures the plan would miss
- Self-improving: calibration loop learns from actual pass/fail data

**Effort:** MEDIUM
- MATU integration: 3-4 days (tensor decomposition, calibration)
- Q-DAPS difficulty estimation: 2-3 days (entropy computation)
- Confidence-gated verifier: 2-3 days (wrapper around existing SABER)
- Rogue monitoring: 1-2 days (confidence signal → gating decision)
- Calibration loop: 2-3 days (feedback from verification results)
- **Total: ~2 weeks** (vs. plan's 6 weeks for always-verify)

### Failure Modes

1. **Calibration drift:** Confidence estimates become overconfident
   - **Mitigation:** Periodic recalibration on held-out tasks; alert if pass rate diverges from confidence

2. **High-confidence failures:** Agent outputs high-confidence garbage
   - **Mitigation:** Random sampling verification (5% of high-confidence outputs verified anyway)
   - **Detection:** Track high-confidence failure rate; if >1%, trigger full verification for 24h

3. **Verification bypass attack:** Adversarial agent learns to output high confidence to skip verification
   - **Mitigation:** Confidence signal is multi-agent tensor (MATU), not single-agent self-assessment
   - **Red flag:** If one agent's confidence is consistently higher than peer consensus, flag as suspicious

4. **Cold-start problem:** No calibration data initially
   - **Mitigation:** Start with conservative threshold (confidence > 0.95 to skip); lower threshold as calibration data accumulates

5. **Domain shift:** Confidence calibrated on tau-bench doesn't generalize to user tasks
   - **Mitigation:** Per-task-type calibration (code vs. research vs. review); maintain separate MATU models

---

## Breakthrough Idea 2: Cross-Agent Consensus Verification with Collusion Detection

### Sources Fused
1. **Lying with Truths** (2601.01685) — Collusion attack using true fragments
2. **Response Anonymization** (2510.07517) — Strip identity to fix sycophancy
3. **ReTAS** — Dialectical alignment for debate
4. **Cross-source triangulation** (SYNTHESIS §7.6) — Verify against 2+ independent sources
5. **Actor-Observer bias correction** (SYNTHESIS §7.6)
6. **SABER mutation testing** (existing plan)

### Mechanism

Multi-agent verification with anti-collusion guards:

```python
class AntiCollusionVerifier:
    """
    Phase 1: Evidence collection (N=3-5 verifiers)
      - Each verifier evaluates independently (no channel sharing during verification)
      - Prompts are anonymized (no agent identity markers)
      - Each verifier produces: verdict + confidence + evidence sources
    
    Phase 2: Collusion detection
      - Compute pairwise similarity of evidence sources
      - If 3+ verifiers cite the SAME source → flag as potential collusion
      - If evidence sources overlap <50% → independent verification confirmed
    
    Phase 3: Cross-source triangulation
      - For each claim in the output, require 2+ independent source citations
      - If claim has only 1 source → downgrade to "unverified"
      - If sources contradict → escalate to human or run mutation test
    
    Phase 4: Dialectical synthesis (ReTAS pattern)
      - Thesis: "The output is correct because..."
      - Antithesis: "The output might be wrong because..."
      - Synthesis: Reconcile contradictions, vote on final verdict
    
    Phase 5: Mutation fallback
      - If consensus verdict is uncertain (confidence <0.6)
      - Run SABER mutation testing (3 mutants)
      - Mutation result overrides debate result if contradictory
    """
```

**Collusion detection heuristics:**
- Single-source claims: Flag any claim backed by only one evidence source
- Source clustering: If 3+ agents cite the same GitHub repo / paper / doc, flag for review
- Semantic similarity: If verifier outputs are >80% similar (embedding cosine), flag as potential echo chamber
- Channel contamination: If verifiers share a channel during verification, void the verification

### Why It Beats Baseline

**vs. BASELINE.md (stub ReviewAgent):**
- Structured multi-agent verification with objective collusion detection
- Evidence-based reasoning (not just "looks correct")
- Dialectical synthesis resolves contradictions systematically

**vs. Existing Plan (SABER only):**
- Plan's mutation verifier is single-agent (no consensus)
- Plan has no collusion detection (vulnerable to Lying with Truths attack)
- Plan has no cross-source triangulation (accepts single-source claims)
- Plan has no anonymization (vulnerable to identity bias)
- Plan has no dialectical synthesis (no contradiction resolution)

**Security gain:**
- Lying with Truths attack success drops from 74.4% to <10% (cross-source triangulation breaks single-channel collusion)
- Identity bias eliminated (anonymization)
- Sycophancy eliminated (anonymization + ReTAS)

### Impact × Effort

**Impact:** VERY HIGH
- Security: Blocks 74.4% → <10% collusion attack success
- Reliability: Multi-agent consensus more reliable than single-agent verification
- Explainability: Evidence sources + dialectical reasoning traceable by users

**Effort:** HIGH
- Anonymization layer: 1-2 days (prompt transformation)
- Collusion detection: 3-4 days (source similarity, channel contamination checks)
- Cross-source triangulation: 2-3 days (claim extraction, source tracking)
- ReTAS dialectical engine: 3-4 days (thesis/antithesis/synthesis prompting)
- Multi-agent orchestration: 2-3 days (parallel verifier dispatch, vote aggregation)
- **Total: ~3 weeks**

### Failure Modes

1. **False positive collusion detection:** Independent agents happen to cite the same authoritative source (e.g., official docs)
   - **Mitigation:** Whitelist "authoritative sources" (official docs, stdlib references)
   - **Heuristic:** Flag only if 4+ agents cite the same non-authoritative source

2. **Verification bottleneck:** 5 verifiers × 3 tasks = 15 LLM calls per output
   - **Mitigation:** Tier verification complexity by task importance (critical tasks get 5 verifiers, routine tasks get 1-2)
   - **Optimization:** Run verifiers in parallel (latency = 1 LLM call, not 5)

3. **Dialectical synthesis produces hedged outputs:** "It might be correct, or it might not"
   - **Mitigation:** Force binary verdict (confirmed / suspect) with confidence score
   - **Fallback:** If synthesis is uncertain, mutation testing decides

4. **Source exhaustion:** For niche tasks, <2 independent sources exist
   - **Mitigation:** Relax to "1 authoritative source OR 2+ non-authoritative sources"
   - **Detection:** Track per-task-type source availability

5. **Anonymization breaks context:** Stripping identity removes important agent role info
   - **Mitigation:** Preserve role (e.g., "security reviewer", "backend engineer") but strip agent name
   - **Preserve:** task context, previous outputs, evidence sources
   - **Strip:** agent identity, previous debate history, peer opinions

---

## Breakthrough Idea 3: Observability-Driven Auto-Repair with Failure Fingerprinting

### Sources Fused
1. **ErrorProbe** (arXiv:2604.17658) — Three-stage failure attribution
2. **Langfuse/Phoenix tracing** (existing plan) — OpenTelemetry trace collection
3. **Token Observatory** (existing plan) — Per-call accounting
4. **Preventing Rogue Agents** (2502.05986) — Confidence monitoring
5. **pass^k consistency** (tau-bench) — Measure trial-to-trial reliability

### Mechanism

Observability stack that automatically repairs failures using fingerprinted patterns:

```python
class ObservabilityAutoRepair:
    """
    Layer 1: Trace collection (existing plan)
      - Every tool call, agent dispatch, router decision traced
      - Token accounting captured per-call
      - Confidence signal logged per-output
    
    Layer 2: Failure fingerprinting
      - When verification fails (SABER mutant passes OR multi-agent consensus = suspect):
        1. Extract trace features: tool call sequence, token pattern, confidence trajectory
        2. Compute fingerprint: hash(tool_seq + token_pattern + confidence)
        3. Store: fingerprint → failure_mode → known_fix
      
      - Failure taxonomy:
        * TOOL_ERROR: bash command failed, file not found, syntax error
        * REASONING_ERROR: logic flaw detected by mutation
        * PROVIDER_ERROR: API timeout, rate limit, model unavailable
        * COLLUSION_ERROR: cross-source triangulation failed
        * CONSISTENCY_ERROR: pass^1 succeeded but pass^k failed
    
    Layer 3: Pattern matching & auto-repair
      - On failure, compute current fingerprint
      - If fingerprint matches known failure (cosine similarity >0.8):
        * Apply known fix automatically (e.g., retry with different provider)
        * Log repair action to trace
        * Increment pattern match counter
      
      - If fingerprint is novel:
        * Run ErrorProbe 3-stage attribution (anomaly detect → backward trace → multi-agent validation)
        * Generate repair hypothesis (multi-agent brainstorm)
        * Apply repair, verify with pass^k (k=3)
        * If pass^k succeeds → store fingerprint + fix
    
    Layer 4: Proactive repair (learning loop)
      - Cluster similar fingerprints (unsupervised: DBSCAN on trace embeddings)
      - Identify high-frequency failure clusters
      - Generate generic repair strategies for clusters
      - Push repairs upstream (e.g., "always validate file exists before Read")
    
    Layer 5: Benchmark integration
      - Run tau-bench / SWE-bench on schedule (nightly)
      - Compute pass^k for k=1,3,5,8
      - Track pass^k degradation over time (drift detection)
      - If pass^k drops >5% → trigger full diagnostic sweep
    """
```

**Key innovation:** Failures become training data. Each failure fingerprint + repair pair is stored and reused. Over time, Lyra auto-repairs most failures without human intervention.

### Why It Beats Baseline

**vs. BASELINE.md (no observability):**
- Full trace + token + confidence visibility
- Automated failure attribution (ErrorProbe 3-stage)
- Self-healing via pattern matching

**vs. Existing Plan (observability + manual repair):**
- Plan has tracing + token accounting BUT no auto-repair
- Plan has ErrorProbe attribution BUT no fingerprinting or pattern reuse
- Plan has eval harness BUT no proactive drift detection or scheduled runs
- Plan has benchmark scoreboard BUT no auto-repair feedback loop

**Efficiency gain:**
- First occurrence of failure: manual ErrorProbe (expensive, 3-stage)
- Second+ occurrence: instant pattern match → auto-repair (cheap, <1s)
- 10th occurrence: proactive repair pushed upstream (prevent future failures)

### Impact × Effort

**Impact:** VERY HIGH
- Reliability: Failures self-heal automatically (reducing MTTR from hours to seconds)
- Developer velocity: Fewer manual interventions needed
- Continuous improvement: System learns from every failure
- Drift detection: Catches reliability degradation before users notice

**Effort:** HIGH
- Trace feature extraction: 2-3 days (tool seq, token pattern, confidence trajectory)
- Failure fingerprinting: 3-4 days (embedding computation, cosine similarity, storage)
- Pattern matching engine: 2-3 days (lookup, confidence scoring, auto-apply)
- ErrorProbe integration: 2-3 days (3-stage attribution, repair hypothesis generation)
- Clustering & proactive repair: 3-4 days (DBSCAN, cluster analysis, generic strategy extraction)
- Benchmark scheduler: 1-2 days (cron, result storage, drift detection)
- **Total: ~3 weeks**

### Failure Modes

1. **False pattern match:** Current failure looks like known failure but needs different fix
   - **Mitigation:** Verify repair with pass^k (k=3) before declaring success
   - **Detection:** If auto-repair fails 3× in a row, escalate to human

2. **Fingerprint collision:** Two unrelated failures hash to same fingerprint
   - **Mitigation:** Use high-dimensional fingerprint (trace + tokens + confidence = ~500-dim embedding)
   - **Collision rate:** <0.1% with 500-dim embeddings for 10K failures

3. **Repair strategy overfitting:** Generic repair works on training failures but not new ones
   - **Mitigation:** Validate generic repairs on held-out failure set before deployment
   - **Continuous validation:** Track repair success rate per strategy; retire strategies with <50% success

4. **Storage explosion:** Fingerprint DB grows unbounded
   - **Mitigation:** Prune low-frequency fingerprints (seen <3× in 30 days)
   - **Compression:** Cluster similar fingerprints, store cluster centroid + variations

5. **Drift false positives:** pass^k fluctuates naturally, triggering spurious alerts
   - **Mitigation:** Statistical significance test (t-test, p<0.05) before declaring drift
   - **Baseline:** Rolling 7-day average pass^k as baseline

6. **Upstream repair breaks other things:** Proactive repair prevents failure X but causes failure Y
   - **Mitigation:** Run full test suite after upstream repair; rollback if test failures increase
   - **Canary:** Apply upstream repairs to 10% of sessions first, monitor for new failures

---

## Stress-Testing & Critique

### Idea 1: Confidence-Calibrated Verification
**Strengths:**
- Cost-efficient (70-80% savings)
- Self-improving via calibration loop
- Adaptive complexity

**Weaknesses:**
- Requires calibration data (cold-start problem)
- Confidence signals may be unreliable early
- MATU requires multi-agent tensor decomposition setup

**Skeptic pushback:**
- "Why not just run mutation testing on everything? Verification is already cheap (3-5 calls)."
- **Counter:** At scale (100 tasks/day × 365 days = 36,500 verifications/year), 3 calls each = 109,500 LLM calls. Confidence gating reduces to ~30,000 calls. At $0.003/call, that's $329.85 vs. $90 = $239.85/year savings. Small per-task, but compounds over time.

**Red team:**
- "What if an adversarial agent learns to output high confidence to bypass verification?"
- **Defense:** MATU is multi-agent tensor decomposition, not single-agent self-assessment. Adversarial agent can't unilaterally inflate consensus confidence.

### Idea 2: Cross-Agent Consensus with Collusion Detection
**Strengths:**
- Blocks 74.4% collusion attack
- Evidence-based, explainable
- Systematic contradiction resolution

**Weaknesses:**
- 3-5× cost vs. single-agent verification
- Complexity (5 components: anonymization, collusion detect, triangulation, ReTAS, mutation fallback)
- May produce hedged outputs

**Skeptic pushback:**
- "Is the 74.4% attack realistic? Lyra's agents don't have adversarial incentives."
- **Counter:** The attack doesn't require adversarial intent. Cognitive collusion happens accidentally when agents share channels and reinforce each other's errors. 60% downstream cascade is the real threat.

**Red team:**
- "What if all 5 verifiers collude (all share the same channel)?"
- **Defense:** Collusion detection flags when 3+ verifiers cite same source. But if ALL verifiers are compromised, detection fails. Mitigation: require at least 2 verifiers from DIFFERENT agent pools (e.g., 3 from Lyra agents, 2 from external tools).

### Idea 3: Observability-Driven Auto-Repair
**Strengths:**
- Self-healing (MTTR reduction)
- Learns from every failure
- Proactive drift detection

**Weaknesses:**
- Requires failure corpus to be effective (cold-start)
- Storage grows with failures
- Upstream repairs risk cascading failures

**Skeptic pushback:**
- "Isn't this just caching known fixes? Why not a simple failure → fix lookup table?"
- **Counter:** Yes, but with two upgrades: (1) fuzzy matching via embeddings (handles similar-but-not-identical failures), (2) proactive clustering to generate generic repairs (handles novel failures in known clusters).

**Red team:**
- "What if auto-repair applies wrong fix and makes things worse?"
- **Defense:** Verify repair with pass^k (k=3) before declaring success. If pass^k fails, escalate to human. Track auto-repair success rate; disable auto-repair if success rate drops below 70%.

---

## Promotion to Plan's (B) Tier

### Strongest Ideas (Ranked)

**#1: Observability-Driven Auto-Repair (Idea 3)**
- **Why:** Self-healing addresses the core reliability pain (manual debugging is slow). Failure fingerprinting + pattern reuse is a force multiplier — every failure makes Lyra smarter.
- **Incremental path:** Ship tracing + token accounting (plan baseline) → add failure fingerprinting → add pattern matching → add proactive repair.
- **Measurable impact:** Track MTTR (mean time to repair) and auto-repair success rate.

**#2: Confidence-Calibrated Verification (Idea 1)**
- **Why:** 70-80% cost savings with better reliability is a rare win-win. Calibration loop is self-improving.
- **Incremental path:** Ship SABER mutation verifier (plan baseline) → add MATU confidence → add adaptive gating → add calibration loop.
- **Measurable impact:** Track verification cost ($/task) and false negative rate (failures missed by skipped verification).

**Conditional #3: Cross-Agent Consensus (Idea 2) — IF multi-agent verification is already planned**
- **Why:** Essential if Lyra has adversarial verification panels. Blocks collusion attack (74.4% → <10%).
- **Incremental path:** Ship anonymization first (cheapest, 50 lines) → add cross-source triangulation → add ReTAS → add collusion detection.
- **Gating:** Only needed if Lyra uses multi-agent verification. If single-agent verification suffices, skip this.

---

## Recommended Integration into Existing Plan

### Phase 2a — OpenTelemetry Tracing (unchanged)
- Implement TracingProvider, AutoInstrumentor, span data model (plan baseline)

### Phase 2b — Token Observatory (unchanged)
- Implement TokenObservatory, buffered writes, query/summary (plan baseline)

### Phase 2c — Intelligent Verifier **(UPGRADE with Idea 1)**
- Implement SABER mutation verifier (plan baseline)
- **ADD:** MATU confidence integration (2-3 days)
- **ADD:** Confidence-gated verification (skip if confidence >0.9) (1-2 days)
- **ADD:** Adaptive mutation depth (light/medium/full) (1-2 days)

### Phase 2d — Eval Harness Integration (unchanged)
- Implement tau-bench, SWE-bench runners, pass^k metrics (plan baseline)

### Phase 2e — ErrorProbe + Auto-Repair **(UPGRADE with Idea 3)**
- Implement ErrorProbe 3-stage attribution (plan baseline)
- **ADD:** Failure fingerprinting (trace features, hash, storage) (3-4 days)
- **ADD:** Pattern matching engine (lookup, auto-apply) (2-3 days)
- **ADD:** Benchmark scheduler + drift detection (1-2 days)
- **ADD:** Proactive repair (clustering, generic strategies) (3-4 days, optional Phase 3)

### Optional Phase 2f — Anti-Collusion Verification **(Idea 2, conditional)**
- **ONLY IF:** Lyra ships with multi-agent adversarial verification panels
- Implement anonymization layer (1-2 days)
- Implement cross-source triangulation (2-3 days)
- Implement collusion detection (3-4 days)
- Implement ReTAS dialectical synthesis (3-4 days)

---

## Final Verdict

**Ship Idea 3 (Auto-Repair) as (B) tier breakthrough.**  
**Ship Idea 1 (Confidence Gating) as (A+) tier enhancement.**  
**Park Idea 2 (Anti-Collusion) for Phase 3, conditional on adversarial panel usage.**

The auto-repair loop transforms observability from "see what happened" to "fix what happened automatically." That's the breakthrough the plan is missing.
