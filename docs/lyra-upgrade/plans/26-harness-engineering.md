# Harness Engineering Discipline — Plan (§4.26)

> Run 1 — June 3, 2026

## Plain-Language Summary

Harness engineering is the meta-discipline that makes Lyra effective — designing the constraints, feedback loops, evals, and context management that turn a raw LLM into a reliable agent. Lyra formalizes this as a first-class subsystem with 5 pillars: Context Engineering, Evaluation Infrastructure, Safety Architecture, Methodology, and Platform Prerequisites.

## 5 Pillars

### 1. Context Engineering
- "Less is more" (Anthropic): start with 15-line system prompt, 3 tools, 2 canonical examples
- Every addition gated by eval: does it improve pass rate? If not, remove it.
- Context budget by component: system prompt (15%), skills (10%), conversation (50%), tool outputs (15%), memory (10%)
- Auto-compaction (§4.3) and memory (§4.2) are the implementation

### 2. Evaluation Infrastructure
- Capability evals (ceiling): SWE-bench Verified, τ-bench, Terminal-Bench, GAIA — weekly
- Regression evals (floor): Lyra-specific task suite — every commit
- Simulation personas: adversarial users (novice, malicious, ambiguous, expert)
- Continuous eval refresh: when eval saturates (100% pass rate = useless signal), replace with harder variant
- Anti-contamination: rotated tasks, held-out splits, benchmark leakage detection

### 3. Safety Architecture
- 5-layer defense-in-depth (§4.17): Prompt → Schema → Runtime → Tool → Lifecycle
- Every new capability ships with its safety counterpart
- Self-evolution gated behind safety validator

### 4. Methodology
- AI-native SDLC: spec-to-code pipelines, agent lanes in CI/CD
- Adversarial review gates: no code merges without adversarial verification (§4.25)
- BMAD Method: Behavior → Model → Adapt → Deploy

### 5. Platform Prerequisites
- CI/CD + IaC + observability + security scanning
- "Agents accelerate broken practices — fix foundations first" (Netflix)
- Lyra's own development uses Lyra (dogfooding)

**Impact:** 4 | **Effort:** 5 | **Tier:** (B) Breakthrough
