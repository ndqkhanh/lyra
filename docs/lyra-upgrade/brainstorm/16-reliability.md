# Brainstorm — Reliability & Verification (§4.16)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea | Key Numbers |
|-----------|--------|-----------|-------------|
| SABER | Amazon AGI | Mutation-gated verification + context cleaning | +28% Airline |
| ErrorProbe | KCL/Amazon | 3-stage semantic failure attribution | Pinpoints agent + step |
| AOI Multi-Agent IT | (Q16XXJou3O) | 3-agent + context compressor + 3-layer memory | 72.4% compression, −34.4% MTTR |
| τ-bench | Sierra | pass^k metric for tool-agent reliability | Best agents <50% |
| Langfuse | Langfuse | Open LLM observability (tracing, evals, prompt mgmt) | — |
| Phoenix | Arize | OpenTelemetry-based agent tracing + eval | — |
| Agentic Benchmark Checklist | (2507.02825v1) | Reward/setup flaws in SWE-bench & τ-bench | — |
| SWE-bench Verified | — | Human-validated coding-agent benchmark | — |
| Terminal-Bench | Laude Institute | Containerized CLI agent tasks | Most Lyra-relevant |

---

## Breakthrough Idea #1: Mutation-Gated Verification Pipeline

**Sources Fused:** SABER mutation-gating + ErrorProbe failure attribution + τ-bench pass^k metric

**Core Mechanism:**
- Classify every agent action as MUTATING (changes external state: write, delete, deploy) or NON-MUTATING (read, search, analyze)
- Non-mutating actions: standard verification (check output correctness)
- Mutating actions: TRIGGER mutation-gated verification — a separate verifier agent predicts the expected effect, the action executes, actual effect is compared to prediction
- Mismatch → rollback + investigation
- ErrorProbe attribution: when failure occurs, 3-stage pipeline:
  1. Failure-taxonomy anomaly detection (what type of failure?)
  2. Symptom-driven backward tracing (which agent? which step?)
  3. Strategist/Investigator/Arbiter validation (is this attribution correct?)
- Measure with pass^k: task must succeed k consecutive times to be "reliable"
- Target: pass³ ≥ 0.95 for critical mutating actions

**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #2: AOI-Inspired SRE Agent Swarm

**Sources Fused:** AOI 3-agent + 3-layer memory + ErrorProbe + Terminal-Bench

**Core Mechanism:**
- **3 SRE Agents:** Monitor (watches system metrics) + Diagnostician (investigates anomalies) + Responder (executes fixes)
- **3-Layer Memory:** Working (current incident) + Episodic (past incidents) + Semantic (SRE knowledge)
- **Context Compressor:** 72.4% compression of monitoring data before it reaches agent context
- **MTTR Target:** −34.4% reduction in mean time to resolve
- **Terminal-Bench Evaluation:** Use containerized CLI tasks as the reliability benchmark
- Self-improving: past incident resolutions become procedural memories

**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Continuous Eval Refresh with Anti-Contamination

**Sources Fused:** Agentic Benchmark Checklist + Anthropic Context Cookbook + SWE-bench Verified methodology

**Core Mechanism:**
- Capability evals (ceiling): SWE-bench Verified, τ-bench, Terminal-Bench, GAIA — run weekly, track vs SOTA
- Regression evals (floor): Lyra-specific task suite — run on every commit
- Simulation personas: adversarial user personas that test edge cases (novice, malicious, ambiguous)
- Anti-contamination: rotate eval tasks, use held-out splits, detect benchmark leakage
- "100% pass rate = useless signal" (Anthropic): when an eval saturates, replace with harder variant
- Continuous eval refresh: every N runs, generate new eval cases from recent failures
- Integration with §4.25 adversarial panel: verification failures → new eval cases

**Impact:** 4 | **Effort:** 3 | **Risk:** Low

---

## Expert Check

**Senior SRE:** "Idea #1 (mutation-gating) is the highest-impact. The distinction between mutating and non-mutating actions is clean and implementable. The pass³ metric for mutating actions is the right bar."

**Senior Evaluation Scientist:** "Idea #3 (continuous eval refresh) is essential. The Agentic Benchmark Checklist paper shows that even SWE-bench Verified has reward hacking vulnerabilities. Lyra needs its own eval suite that evolves faster than the model can overfit."

**Adversarial Skeptic:** "pass³ ≥ 0.95 for mutating actions — that's an extremely high bar. Most human engineers don't pass³ at 0.95. Is this a realistic target or aspirational? Set a phased target: pass¹ ≥ 0.9 first, then pass², then pass³."

**Resolution:** Idea #1 (mutation-gating) as the (B) breakthrough. Phased pass^k targets: pass¹ ≥ 0.9 (Phase 1), pass² ≥ 0.9 (Phase 2), pass³ ≥ 0.95 (Phase 3). Idea #3 (eval refresh) ships with the observability infrastructure.
