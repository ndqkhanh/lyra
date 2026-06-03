# Brainstorm — Self-Knowledge (§4.19) + Adversarial Panel (§4.25)

> Run 1 — June 3, 2026 | Combined brainstorm for closely related workstreams

---

## §4.19 Self-Knowledge / Uncertainty

### Breakthrough Idea #1: Entropy-Over-Candidates Uncertainty Gating

**Sources Fused:** Q-DAPS (2605.12398) + "Must Be Taught" (NeurIPS 2024) + MATU tensor UQ (2604.08708)

**Core Mechanism:**
- For every agent decision, sample N candidate answers (vary temperature, model, or prompt)
- Compute entropy over candidate plausibility scores (Q-DAPS method)
- Low entropy → high confidence → proceed autonomously
- High entropy → low confidence → escalate to stronger model (§4.5) or request human input (§4.22)
- MATU extension for multi-agent: stack reasoning-trajectory embedding matrices into higher-order tensor → decompose → uncertainty per agent per step
- "Must Be Taught" calibration: fine-tune on 1K graded examples to calibrate verbalized confidence
- Abstention gate: if ALL candidates have entropy above threshold → "I don't know"

**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

### Breakthrough Idea #2: Self-Consistency Loop with Automatic Escalation

**Sources Fused:** "Beyond I Don't Know" (2604.17293) + RouteLLM cascade

**Core Mechanism:**
- Generate 3-5 independent answers (self-consistency)
- If answers converge (agreement ≥ 80%) → return consensus, high confidence
- If answers diverge → distinguish data uncertainty (question is ambiguous, needs clarification) vs model uncertainty (model is uncertain, needs stronger model)
- Data uncertainty → ask clarifying question
- Model uncertainty → escalate to stronger model via §4.5 router
- Track per-task-type calibration over time → learn which tasks need which model

**Impact:** 4 | **Effort:** 3 | **Risk:** Low

---

## §4.25 Adversarial Verification Panel

### Breakthrough Idea #1: 4-Correction Bias-Immune Verification Pipeline

**Sources Fused:** Identity Skews (2510.07517) + ReTAS (2604.19548) + Lying with Truths (2601.01685) + Rogue Agents (2502.05986) + SABER (En2z9dckgP) + ErrorProbe (2604.17658) + RADAR (2604.19005)

**Core Mechanism (step-by-step):**
1. **Anonymization Layer:** Strip all identity markers from agent outputs before verification. Verifier sees: "Finding #7: The OAuth flow has a timing vulnerability..." — no agent name, no model name. Eliminates identity-weighted Bayesian update (IBC→0).

2. **ReTAS Dialectical Alignment:** When an agent switches role (actor→observer):
   - Thesis: agent's own output/claim
   - Antithesis: forced counter-argument generation (what if this is wrong?)
   - Synthesis: reconcile both into corrected output. Corrects >20% bias trigger rate.

3. **3-Verifier Panel:**
   - Verifier A (Correctness): Does this claim hold under scrutiny? Tests with counterexamples.
   - Verifier B (Security): Is this safe? What's the blast radius? Tests with adversarial inputs.
   - Verifier C (Reproducibility): Can this be independently reproduced? Tests with same inputs.
   - 1 Adversarial Skeptic: Tasked with REFUTING the claim by any legitimate means.
   - Voting: Claim survives ONLY if ≥2/3 verifiers confirm AFTER adversarial challenge.

4. **Mutation-Gated Verification (SABER):**
   - Non-mutating findings: standard verification
   - Mutating findings (would change code/config): TRIGGER full verification pipeline + predict expected effect

5. **Collusion Detection:**
   - Monitor for Lying-with-Truths patterns (sequential truthful evidence fragments steering beliefs)
   - Flag when ≥2 agents show coordinated evidence selection

6. **Rogue Agent Prevention:**
   - Monitor action prediction for each verifier
   - Intervene when future error likelihood exceeds threshold
   - WhoDunitEnv-style testing for intervention logic

7. **RADAR Dual-Threshold Termination:**
   - Debate ends when agreement threshold reached OR diminishing returns threshold (cost > expected info gain)

**Why It Beats Single-Source:** Claude Code has adversarial checking but NONE of the bias corrections. No existing system combines all 4 corrections.

**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Expert Check

**Senior AI Researcher:** "The 4-correction pipeline is the most thorough verification architecture I've seen designed. The key question: does each correction independently improve outcomes? Run ablation studies — ship the ones that matter, drop the ones that don't."

**Senior Security Engineer:** "The collusion detection (Lying with Truths) and rogue prevention are the most novel. But they need calibration data — false positives will erode trust. Start with logging-only mode, collect data, tune thresholds, then enable intervention."

**Adversarial Skeptic:** "4 corrections + 3 verifiers + skeptic + collusion detection + rogue prevention = enormous latency per verification. What's the simplest pipeline that beats single-pass verification? Start with anonymization + 2 verifiers + voting. Add the rest only if ablations show they improve outcomes."

**Resolution:** Start with anonymization + 2 verifiers (Correctness + Security) + voting as the minimum viable adversarial panel. Add ReTAS, the 3rd verifier, skeptic, collusion detection, and rogue prevention incrementally — each gated behind ablation data showing it improves verification quality beyond the simpler pipeline.
