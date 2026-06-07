# Brainstorm: §4.15 Deep Research

> **Generated:** 2026-06-06  
> **Workstream:** §4.15 (research)  
> **Status:** Breakthrough ideation phase

## Context Review

### From SYNTHESIS.md
- No dedicated research section found in current synthesis
- Related patterns in Memory Architecture (§1): Field-theoretic memory, cross-session consolidation
- Related patterns in Ingestion (§11): "Is Grep All You Need?" — harness matters more than retriever
- Multi-agent orchestration patterns (§5): adversarial verification, debate reliability concerns
- Self-evolution patterns (§3): GEPA, TF-TTCL, SkillNet auto-generation

### From BASELINE.md
**§4.15 Deep Research:**
- **What Exists:** ResearchAgent exists but is a stub
- **Maturity:** `none`
- **Known Pain:** No multi-hop research; no AutoScientists pattern

### Current Lyra Research Capabilities
- ResearchAgent class exists (`src/agents/research_agent.py`) but unimplemented
- No multi-source verification
- No claim triangulation
- No adversarial fact-checking
- No research memory/knowledge graph
- No iterative refinement loops

---

## Breakthrough Idea #1: Adversarial Research Swarm with Field-Memory Consolidation

### Sources Fused
1. **Field-theoretic memory** (Mitra 2026, §1.6 SYNTHESIS) — PDEs for cross-session semantic diffusion
2. **Lying with Truths attack defense** (§7.6 SYNTHESIS) — cross-source triangulation gate
3. **MASS-RAG** (2604.18509, ACL 2026 Findings) — role-specialized agents for noisy evidence
4. **AutoScientists multi-hop pattern** (implied from "no AutoScientists pattern" in BASELINE)
5. **Harness-first thesis** (§11.6 SYNTHESIS, "Is Grep All You Need?") — retrieval harness > algorithm

### Mechanism: Step-by-Step

**Phase 1: Research Swarm Initialization**
```python
# User query: "What are the latest breakthroughs in context optimization?"

1. QueryDecomposer agent breaks query into sub-questions:
   - Q1: "What are SOTA context window compression techniques?"
   - Q2: "How do KV-cache optimizations work?"
   - Q3: "What is the state of hierarchical context management?"

2. Spawn role-specialized research agents (MASS-RAG pattern):
   - Searcher-A: Academic papers (arXiv, ACL, ICLR)
   - Searcher-B: GitHub repos (code implementations)
   - Searcher-C: Industry blogs (engineering practices)
   - Skeptic: Adversarial fact-checker (triangulates claims)
```

**Phase 2: Multi-Hop Research with Triangulation**
```python
3. Each Searcher fetches evidence for Q1-Q3:
   - Uses harness-first approach (grep code, structured API calls, not just vector search)
   - Returns claims with source citations

4. Skeptic agent applies cross-source triangulation (§7.6):
   - For each claim: "Method X achieves Y% improvement"
   - Verify: Does source A + independent source B agree?
   - Flag: Single-source claims as "UNVERIFIED"
   - Block: Contradictory claims (74.4% collusion attack prevention)

5. Multi-hop iteration:
   - If Q1 reveals new technique "COMPASS meta-thinker":
     - Spawn Q1.1: "How does COMPASS work?"
     - Spawn Q1.2: "Is COMPASS implemented anywhere?"
   - Recursively research up to MAX_DEPTH=3 hops
```

**Phase 3: Field-Memory Consolidation (Dreaming)**
```python
6. During idle time (after research session):
   - Field-theoretic consolidation runs PDEs over all gathered claims
   - Semantic diffusion connects:
     * "COMPASS uses meta-thinker" (from Q1.1)
     * "Meta-agent pattern in DGM-H" (from earlier session)
     * → Field gradient surfaces: "COMPASS is a meta-agent instance"
   
7. Consolidated insights written back to CraniMem as enriched entries:
   - Discrete entry: "COMPASS meta-thinker pattern"
   - Field-derived links: [related: "DGM-H", "meta-evolution"]
   - Cross-session bridge: Connects today's research to 3-week-old discussion
```

**Phase 4: Synthesis with Adversarial Review**
```python
8. Synthesizer agent drafts research report:
   - Cites all VERIFIED claims (≥2 sources)
   - Flags UNVERIFIED claims with [single-source] marker
   - Lists contradictions explicitly

9. Adversarial panel reviews synthesis:
   - Anonymized debate (§7.6) — strips identity to prevent sycophancy
   - Dialectical alignment (ReTAS) — forces opposing perspectives
   - Confidence monitor (§8.1) — blocks if synthesizer uncertainty >threshold

10. Final report output with citation graph
```

### Why It Beats Baseline

**Baseline (ResearchAgent stub):**
- Single-pass search
- No source verification
- No multi-hop depth
- No cross-session learning
- No adversarial review

**This Approach:**
- **Multi-source triangulation** defeats 74.4% collusion attack (§7.6)
- **Field-memory consolidation** achieves +116% F1 on multi-session reasoning (§1.6)
- **Role-specialized agents** handle noisy evidence better than single retriever (MASS-RAG)
- **Adversarial review** prevents bias (anonymization + ReTAS from §7.6)
- **Harness-first search** outperforms vector retrieval for code (§11.6)
- **Multi-hop depth** enables AutoScientists-style iterative refinement

### Impact × Effort

**Impact: HIGH (9/10)**
- Unlocks research-intensive workflows (architecture review, SOTA survey, competitive analysis)
- Cross-session learning enables "agent remembers 3-week-old context" (§1.6 quote)
- Collusion defense prevents misinformation cascade (>60% downstream deception in baseline)

**Effort: MEDIUM-HIGH (7/10)**
- **Week 1-2:** Implement research swarm (Searcher × 3, Skeptic, Synthesizer) — ~1200 LOC
- **Week 3:** Cross-source triangulation gate — ~300 LOC
- **Week 4:** Multi-hop recursion logic — ~400 LOC
- **Week 5-6:** Field-memory consolidation (PDE layer) — ~800 LOC (can reuse §1.6 architecture)
- **Week 7:** Adversarial review integration — ~200 LOC (reuse existing anonymization)
- **Total: 7 weeks, ~2900 LOC**

### Failure Modes

1. **PDE computational cost blowup**
   - **Risk:** Field-memory PDEs are O(N²) for N claims; 1000 claims = 500K pairwise computations
   - **Mitigation:** Run PDEs during idle only (Dreaming mode); snapshot gradients for O(log N) retrieval
   - **Fallback:** Skip field layer; use discrete CraniMem with explicit cross-reference links

2. **Triangulation false negatives**
   - **Risk:** Legitimate single-source breakthroughs flagged as unverified
   - **Mitigation:** Add confidence decay: fresh single-source claims flagged "[NEW]", not "[UNVERIFIED]"
   - **Human-in-loop:** User can override triangulation gate for trusted sources

3. **Multi-hop explosion**
   - **Risk:** MAX_DEPTH=3 with branching_factor=2 → 8 sub-queries → token budget exhaustion
   - **Mitigation:** Budget-aware recursion; cheap model (Haiku) for sub-query generation; halt if cost >$5/query
   - **Adaptive depth:** Start MAX_DEPTH=1, escalate to 2 only if Q1 answer is "insufficient"

4. **Adversarial panel deadlock**
   - **Risk:** Anonymized debate reaches no consensus; synthesis blocked
   - **Mitigation:** Tiebreaker via user or confidence-weighted voting (MATU tensor UQ from §8.1)
   - **Timeout:** If debate exceeds 3 rounds, synthesize with "CONTESTED" markers on disputed claims

5. **Cross-session drift**
   - **Risk:** Field-memory connects semantically similar but contextually different claims
   - **Mitigation:** Field decay parameter; old claims (>30 days) weighted down in diffusion
   - **Namespace isolation:** Per-project field memories; cross-project diffusion opt-in only

---

## Breakthrough Idea #2: Lazy-Evaluated Research Graph with Uncertainty Quantification

### Sources Fused
1. **Q-DAPS difficulty estimation** (2605.12398, §9.6 SYNTHESIS) — entropy-based question difficulty
2. **MATU tensor UQ** (2604.08708, §8.1 SYNTHESIS) — multi-agent uncertainty quantification
3. **SkillNet graph model** (2603.04448, §3.6 SYNTHESIS) — similarity/composition/dependency graphs
4. **MCTS planning trigger** (§9.6 SYNTHESIS) — reactive: fail twice → escalate to MCTS
5. **Preventing Rogue Agents monitor** (2502.05986, §7.6 SYNTHESIS) — pre-execution confidence gating

### Mechanism: Step-by-Step

**Phase 1: Research Graph Construction**
```python
# User query: "Compare COMPASS vs ExtAgents for context scaling"

1. Build lazy-evaluated research graph:
   Node("COMPASS", children=[
     Node("COMPASS architecture", status=PENDING),
     Node("COMPASS benchmarks", status=PENDING),
     Node("COMPASS limitations", status=PENDING)
   ])
   Node("ExtAgents", children=[...])
   Node("Comparison", depends_on=["COMPASS", "ExtAgents"], status=BLOCKED)

2. Estimate node difficulty (Q-DAPS):
   - "COMPASS architecture" → entropy=0.3 (low, likely well-documented)
   - "COMPASS limitations" → entropy=0.8 (high, requires synthesis)
   - Difficulty score determines search strategy
```

**Phase 2: Lazy Evaluation with Confidence Gating**
```python
3. Traverse graph depth-first:
   - Eval("COMPASS architecture"):
     * Single-pass search (entropy <0.5)
     * Cheap model (Haiku) for summarization
     * Confidence = 0.92 (MATU tensor UQ)
     * Status = COMPLETE

   - Eval("COMPASS limitations"):
     * High entropy (0.8) → multi-pass search
     * Adversarial panel (Proponent + Skeptic)
     * Confidence = 0.65 (below threshold 0.7)
     * Status = UNCERTAIN → flag for human review

4. Confidence-gated synthesis:
   - If all child nodes have confidence ≥0.7: proceed to synthesis
   - If any node <0.7: BLOCK synthesis, surface uncertain nodes to user
   - User can: (a) accept uncertainty, (b) request deeper research, (c) provide input
```

**Phase 3: Incremental Refinement**
```python
5. User selects "request deeper research" for "COMPASS limitations":
   - Escalate to MCTS planning (§9.6 reactive trigger)
   - Spawn 3 alternative search strategies:
     * A: GitHub issues/discussions (pain points)
     * B: Academic paper "Future Work" sections
     * C: Reddit/HN discussions (practitioner feedback)
   - Re-evaluate node confidence after each strategy
   - Stop when confidence ≥0.7 OR budget exhausted

6. Final synthesis only when ALL nodes ≥0.7 confidence
```

**Phase 4: Graph Reuse & Caching**
```python
7. Persist research graph to SkillNet-style index:
   - Nodes with high confidence (≥0.8) cached for 7 days
   - Similarity links: "COMPASS" ↔ "meta-thinker pattern" (cosine similarity)
   - Dependency links: "Comparison" depends_on ["COMPASS", "ExtAgents"]

8. Next research query: "How does COMPASS compare to GRPO?"
   - Graph reuse: "COMPASS" node already cached (confidence=0.92)
   - Only research new node: "GRPO"
   - Synthesis compares cached COMPASS + fresh GRPO
   - 2× speedup, 50% cost reduction
```

### Why It Beats Baseline

**Baseline (ResearchAgent stub):**
- No uncertainty estimation
- No confidence gating
- No graph reuse
- No lazy evaluation
- All-or-nothing research (complete everything or nothing)

**This Approach:**
- **Confidence gating** prevents hallucination cascade (§7.6, §8.1)
- **Lazy evaluation** reduces token waste (only research what's needed)
- **Q-DAPS entropy** optimizes search strategy per sub-question
- **Graph reuse** enables 50% cost reduction on repeat queries
- **Incremental refinement** allows human steering at uncertainty boundaries
- **MCTS escalation** only for high-difficulty nodes (cost-aware)

### Impact × Effort

**Impact: MEDIUM-HIGH (7/10)**
- Uncertainty quantification unlocks safe autonomous research
- Graph reuse is major cost savings (50% on repeat queries)
- Enables human-in-loop at precise points (uncertain nodes only)
- Generalizes to planning/reasoning beyond research

**Effort: MEDIUM (5/10)**
- **Week 1:** Research graph data structure + lazy evaluation — ~500 LOC
- **Week 2:** Q-DAPS entropy estimation integration — ~300 LOC
- **Week 3:** MATU tensor UQ wrapper — ~400 LOC (may require model API extensions)
- **Week 4:** Confidence gating + escalation logic — ~300 LOC
- **Week 5:** SkillNet-style graph persistence — ~400 LOC (reuse §3.6 architecture)
- **Total: 5 weeks, ~1900 LOC**

### Failure Modes

1. **Entropy estimation inaccuracy**
   - **Risk:** Q-DAPS predicts low difficulty (entropy=0.3) but question is actually hard → under-researched
   - **Mitigation:** Calibration loop; track entropy prediction vs actual confidence post-research
   - **Fallback:** If confidence <0.7 despite low entropy, re-estimate entropy and escalate

2. **Confidence score gaming**
   - **Risk:** Model reports high confidence on wrong answers (overconfidence)
   - **Mitigation:** MATU tensor UQ aggregates multiple agents; overconfidence in one agent diluted by others
   - **Calibration:** Temperature scaling on confidence scores (standard ML calibration technique)

3. **Graph cache staleness**
   - **Risk:** Cached "COMPASS architecture" (7 days old) outdated by new paper
   - **Mitigation:** Freshness scoring (§11.6 ingestion); cache invalidation on new sources
   - **User control:** `--no-cache` flag forces fresh research

4. **Dependency deadlock**
   - **Risk:** Node A depends_on B, B depends_on C, C uncertain → entire graph blocked
   - **Mitigation:** Partial synthesis; synthesize A+B with "[C incomplete]" marker
   - **Topological sort:** Detect circular dependencies at graph construction; fail early

5. **MCTS cost explosion**
   - **Risk:** High-entropy node escalates to MCTS → 20× cost (§9.6 concern)
   - **Mitigation:** Budget cap ($5/node); halt MCTS after N iterations
   - **User prompt:** "Node X uncertain, MCTS would cost $10. Proceed? [y/N]"

---

## Breakthrough Idea #3: Streaming Research Pipeline with Interruptible Checkpoints

### Sources Fused
1. **Supervisor daemon architecture** (§5.6 SYNTHESIS) — detached background sessions, state persistence
2. **Steer-by-exception UX** (§10.6 SYNTHESIS) — users intervene only when needed
3. **Autonomy loop crash detection** (§8.6 SYNTHESIS) — 3 crashes/300s window
4. **Worktree isolation** (§5.6 SYNTHESIS) — per-session file isolation
5. **Cheap-model row summaries** (§5.6 SYNTHESIS) — Haiku for meta/monitoring

### Mechanism: Step-by-Step

**Phase 1: Research as Background Job**
```python
# User command: `lyra research --bg "Survey SOTA multi-agent orchestration"`

1. Supervisor spawns detached research session:
   - Session ID: research-abc123
   - Worktree: .lyra/research/research-abc123/
   - State file: research-abc123/state.json
   - Output log: research-abc123/transcript.jsonl

2. Research pipeline stages (streaming):
   Stage 1: Query decomposition → [Q1, Q2, Q3] (30s)
   Stage 2: Source search for Q1-Q3 → [20 sources] (2 min)
   Stage 3: Evidence extraction → [50 claims] (5 min)
   Stage 4: Triangulation → [35 verified claims] (3 min)
   Stage 5: Synthesis → [draft report] (2 min)
   Stage 6: Adversarial review → [final report] (4 min)
   Total: ~16 minutes
```

**Phase 2: Interruptible Checkpoints**
```python
3. After each stage, checkpoint state:
   state.json = {
     "session_id": "research-abc123",
     "stage": "Stage 3: Evidence extraction",
     "progress": "Q1: complete (10/10), Q2: in-progress (3/8), Q3: pending",
     "checkpoint": "stage3_q1_complete.pkl",
     "cost_so_far": "$0.42",
     "confidence": 0.68
   }

4. Supervisor monitors session health:
   - If 3 crashes in 300s → PAUSE, notify user
   - If confidence drops <0.5 mid-stream → PAUSE, notify user
   - If cost exceeds budget ($5 default) → PAUSE, prompt user
```

**Phase 3: Steer-by-Exception**
```python
5. Fleet view (§10.6 pattern):
   Research Sessions:
   ┌─────────────────────────────────────────────────┐
   │ [Stage 3/6] research-abc123                     │
   │ Progress: Q2 in-progress (3/8) | $0.42 | 0.68   │
   │ Last: "Extracting claims from arXiv:2603.04448" │
   └─────────────────────────────────────────────────┘
   
   User presses Space → peek panel:
   ┌─────────────────────────────────────────────────┐
   │ Q1: SOTA orchestration frameworks (COMPLETE)    │
   │   - Agent View (Berkeley)                       │
   │   - Swarm (OpenAI)                              │
   │   - Hyperagents (DeepMind)                      │
   │ Q2: Reliability patterns (IN-PROGRESS)          │
   │   - Lying with Truths defense [verifying...]    │
   │ Q3: Cost optimization (PENDING)                 │
   └─────────────────────────────────────────────────┘

6. User intervention (if needed):
   - Press 'i' → interrupt, add steering instruction:
     "Skip Q3, focus on Q2 verification"
   - Session reloads from Stage 3 checkpoint, adjusts plan
   - Continues in background
```

**Phase 4: Resumable on Failure**
```python
7. If machine sleeps or crashes:
   - state.json persists to disk
   - On `lyra resume research-abc123`:
     * Reload checkpoint: stage3_q1_complete.pkl
     * Skip completed stages (1-3 Q1)
     * Resume from Stage 3 Q2 extraction
   - No token re-spend on completed work

8. Completion notification:
   - Supervisor detects Stage 6 complete
   - Updates fleet view: [DONE] research-abc123
   - Pushes system notification (macOS: osascript)
   - Report written to: research-abc123/report.md
```

**Phase 5: Cheap-Model Monitoring**
```python
9. Row summary (§5.6 pattern):
   - Every 60s, Haiku reads transcript tail (last 20 lines)
   - Generates one-line summary: "Extracting claims from SkillNet paper"
   - Updates fleet view in real-time
   - Cost: $0.0001/summary = $0.01 for 16-min session
```

### Why It Beats Baseline

**Baseline (ResearchAgent stub):**
- Foreground-only (blocks terminal)
- No checkpointing (crash = start over)
- No progress visibility
- No interruption (must cancel entirely or wait)
- No cost tracking

**This Approach:**
- **Background execution** enables parallel work (user codes while research runs)
- **Interruptible checkpoints** prevent token waste on crashes (resume from Stage N)
- **Steer-by-exception** allows mid-flight correction without full restart
- **Cheap-model monitoring** gives real-time progress for <$0.01 overhead
- **Supervisor daemon** survives machine sleep (§5.6)
- **Worktree isolation** prevents file conflicts if user edits during research

### Impact × Effort

**Impact: MEDIUM (6/10)**
- Unlocks long-running research (16+ minutes) without blocking terminal
- Checkpoint recovery saves cost on flaky networks/crashes
- Steer-by-exception improves accuracy (user corrects mid-flight)
- Depends on supervisor daemon (§5.6) being built first

**Effort: MEDIUM (6/10)**
- **Dependency:** Supervisor daemon (~500 LOC, §5.6) must exist first
- **Week 1:** Research pipeline stage decomposition — ~400 LOC
- **Week 2:** Checkpoint/resume logic — ~500 LOC
- **Week 3:** State persistence + recovery — ~300 LOC
- **Week 4:** Fleet view integration — ~300 LOC (reuse §10.6 TUI)
- **Week 5:** Cheap-model row summary hook — ~200 LOC
- **Total: 5 weeks, ~1700 LOC + supervisor dependency**

### Failure Modes

1. **Checkpoint bloat**
   - **Risk:** stage3_q1_complete.pkl is 100MB (serialized embeddings, large search results)
   - **Mitigation:** Checkpoint only essential state (query results IDs, not full text); lazy-load on resume
   - **Cleanup:** Auto-delete checkpoints >7 days old

2. **Resume inconsistency**
   - **Risk:** Resume from Stage 3, but external state changed (API changed, source disappeared)
   - **Mitigation:** Versioned checkpoints; include source hashes; detect staleness on resume
   - **Fallback:** If resume fails validation, restart from Stage 1 (notify user)

3. **Fleet view clutter**
   - **Risk:** 10 background research sessions → TUI unreadable
   - **Mitigation:** Auto-collapse completed sessions; filters (s:running, s:done, s:paused)
   - **Limits:** Max 5 concurrent research sessions (configurable)

4. **Notification fatigue**
   - **Risk:** 5 research sessions complete simultaneously → 5 system notifications
   - **Mitigation:** Batch notifications (one per minute); TUI badge instead of system alert
   - **User control:** `--silent` flag disables notifications

5. **Interruption data loss**
   - **Risk:** User presses 'i' to interrupt, types instruction, but session crashes before saving
   - **Mitigation:** Write steering instruction to disk BEFORE applying to session
   - **Atomic writes:** Use temp file + rename pattern (POSIX atomic)

---

## Stress-Testing & Comparison

### Stress Test: Adversarial Research Swarm (Idea #1)

**Attack Vector 1: Collusion via Shared Channels**
- **Scenario:** Searcher-A and Searcher-B both read same biased source, converge on wrong claim
- **Defense:** Skeptic requires ≥2 INDEPENDENT sources; if A+B cite same origin, flag as single-source
- **Result:** PASS (collusion blocked by triangulation)

**Attack Vector 2: PDE Computation Deadlock**
- **Scenario:** 5000 claims from deep research → 12.5M pairwise PDE calculations → 30+ seconds
- **Defense:** Run PDEs during idle (Dreaming mode); snapshot gradients; live queries use snapshot (O(log N))
- **Result:** PASS (latency <100ms on live queries)

**Attack Vector 3: Multi-Hop Budget Explosion**
- **Scenario:** MAX_DEPTH=3, branching=3 → 27 leaf queries → $50 cost
- **Defense:** Budget cap ($5 default); adaptive depth (start 1, escalate on-demand); cheap model for sub-queries
- **Result:** PASS (cost capped, user prompted before exceeding)

**Verdict:** Idea #1 is **resilient** but **complex** (7 weeks, PDE dependency). Best for high-stakes research (architecture decisions, competitive analysis).

---

### Stress Test: Lazy-Evaluated Research Graph (Idea #2)

**Attack Vector 1: Entropy Miscalibration**
- **Scenario:** Q-DAPS predicts entropy=0.2 (trivial) but question is actually hard → under-researched → low confidence
- **Defense:** Confidence gating; if final confidence <0.7, escalate despite low entropy prediction
- **Result:** PASS (self-correcting via confidence feedback loop)

**Attack Vector 2: Cache Poisoning**
- **Scenario:** Cached "COMPASS" node from 6 days ago; new paper invalidates cached claims
- **Defense:** Freshness scoring; cache TTL (7 days); user `--no-cache` override
- **Result:** PARTIAL (depends on freshness detection accuracy — needs testing)

**Attack Vector 3: Dependency Chain Blocking**
- **Scenario:** Node A depends_on B depends_on C; C has confidence=0.5 (uncertain) → entire chain blocked
- **Defense:** Partial synthesis with "[C incomplete]" markers; topological sort detects circular deps
- **Result:** PASS (graceful degradation)

**Verdict:** Idea #2 is **practical** and **modular** (5 weeks, no exotic dependencies). Best for iterative/exploratory research.

---

### Stress Test: Streaming Research Pipeline (Idea #3)

**Attack Vector 1: State Corruption on Crash**
- **Scenario:** Machine crashes mid-Stage 3; state.json half-written → corrupted → unrecoverable
- **Defense:** Atomic writes (temp file + rename); checksum validation on resume
- **Result:** PASS (standard POSIX reliability pattern)

**Attack Vector 2: Supervisor Daemon SPOF**
- **Scenario:** Supervisor crashes → all 5 background research sessions lost
- **Defense:** Daemon auto-restart (§5.6); session state on disk, not in-memory; respawn on supervisor reboot
- **Result:** PASS (inherited from §5.6 supervisor design)

**Attack Vector 3: Checkpoint Staleness**
- **Scenario:** Resume from Stage 3 checkpoint after 2 days; API changed, sources 404 → resume fails
- **Defense:** Versioned checkpoints; staleness detection; fallback to restart from Stage 1 (notify user)
- **Result:** PASS (graceful fallback)

**Verdict:** Idea #3 is **dependent** on supervisor daemon (§5.6) but otherwise **robust** (5 weeks). Best for long-running/unattended research.

---

## Recommendation: Which Ideas to Promote?

### Tier A (Highest Confidence)
**Idea #2: Lazy-Evaluated Research Graph with Uncertainty Quantification**
- **Why:** Practical, modular, no exotic dependencies, self-correcting via confidence feedback
- **ROI:** 50% cost savings on repeat queries; safe autonomous research via confidence gating
- **Effort:** 5 weeks, ~1900 LOC
- **Promote to Plan (B) tier:** YES

### Tier B (High Potential, Gated on Dependency)
**Idea #3: Streaming Research Pipeline with Interruptible Checkpoints**
- **Why:** Unlocks long-running research; excellent UX (steer-by-exception); robust checkpoint recovery
- **Blocker:** Requires supervisor daemon (§5.6) to be built first
- **Effort:** 5 weeks, ~1700 LOC + supervisor
- **Promote to Plan (B) tier:** YES, but sequence AFTER §5.6 supervisor in roadmap

### Tier C (Research Bet, High Complexity)
**Idea #1: Adversarial Research Swarm with Field-Memory Consolidation**
- **Why:** Most powerful (defeats collusion, cross-session learning), but highest complexity
- **Risk:** PDE layer is research-grade (§1.6 debate shows skepticism); 7-week build
- **When:** After Idea #2 is working; treat field-memory as upgrade, not MVP
- **Promote to Plan (B) tier:** NO for Round 1; park as (C) "future breakthrough" tier

---

## Final Synthesis for Plan Feed

**Recommended additions to `plans/15-research.md` (B) tier:**

1. **Lazy-Evaluated Research Graph** (Idea #2)
   - Q-DAPS entropy-based search strategy routing
   - MATU tensor UQ confidence gating
   - SkillNet-style graph persistence for reuse
   - Incremental refinement with human-in-loop at uncertainty boundaries
   - MCTS escalation only for high-difficulty nodes

2. **Streaming Research Pipeline** (Idea #3, post-supervisor)
   - Background execution via supervisor daemon (depends on §5.6)
   - Interruptible checkpoints (6 stages: decompose → search → extract → verify → synthesize → review)
   - Steer-by-exception UX (fleet view with peek/interrupt)
   - Cheap-model row summaries (Haiku monitoring)
   - Resumable on crash/sleep (state persistence)

**Additional pattern to consider (from Idea #1, cherry-picked):**
- **Cross-source triangulation gate** (from §7.6 collusion defense) — low complexity, high safety impact
- **Role-specialized searchers** (MASS-RAG pattern) — academic/code/industry specialization

These patterns can be integrated into Idea #2's research graph as node evaluation strategies.

---

## Cross-Reference to Other Workstreams

- **§4.2 Memory:** Field-memory consolidation (Idea #1) depends on field-theoretic layer from §1.6
- **§4.5 Router:** Q-DAPS difficulty estimation (Idea #2) requires cheap-model routing for sub-queries
- **§4.13 Swarm:** Role-specialized agents (Ideas #1, #2) leverage TaskAllocator for work distribution
- **§4.16 Reliability:** MATU tensor UQ (Idea #2) crosscuts to verification/monitoring
- **§4.22 Steering:** Steer-by-exception (Idea #3) depends on §10.6 fleet UX patterns
- **§5.6 Supervisor:** Streaming pipeline (Idea #3) is BLOCKED until supervisor daemon ships

---

**End of Brainstorm**
