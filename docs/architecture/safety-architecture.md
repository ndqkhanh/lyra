# Safety Architecture: Parallax-Style Cognitive-Executive Separation

> **Inspiration:** [Parallax (2026)](https://arxiv.org/abs/2604.12986) — Cognitive-Executive Safety Separation for AI Agents
> **Status:** Phase 13.3 — Implementation target: Weeks 5-6

## Overview

Lyra's safety architecture implements a **6-layer defense-in-depth model** centered on the Parallax principle: **structural separation of reasoning from execution**. Research proves that prompt-level guardrails provide zero protection when reasoning is compromised. The solution is architectural — reasoning and execution run in structurally separated contexts with independent verification.

## The Problem with Prompt-Level Safety

Traditional agent safety relies on system prompts instructing the model to "be safe." This fails because:

1. **Reasoning can be compromised** — An adversarial prompt can override safety instructions
2. **No structural barrier** — The same context that reasons also executes
3. **Single-model vulnerability** — One compromised model can execute dangerous actions
4. **No behavioral monitoring** — Actions aren't checked for intent consistency over time

## 6-Layer Safety Architecture

```
Layer 0: Input Validation          → Sanitize, detect injection
Layer 1: Cognitive-Executive Split → Structural separation (Parallax)
Layer 2: Permission Gating         → Scope validation, mode enforcement
Layer 3: Multi-Agent Validation    → Executor→Validator→Critic pipeline
Layer 4: Behavioral Monitoring     → Intent consistency, anomaly detection
Layer 5: Continuous Assurance      → PRISM drift detection, TEE verifiability
```

### Layer 0: Input Validation

Before any processing, user input passes through:
- **Injection detection** — Prompt injection patterns, escape sequences
- **Schema validation** — Task structure, parameter bounds
- **Rate limiting** — Per-session, per-operation throttling

### Layer 1: Cognitive-Executive Separation (Parallax)

The core innovation. Reasoning and execution run in **structurally separated contexts**:

```
┌─────────────────────────────────────┐
│  REASONING CONTEXT (Read-Only)      │
│  • Planning & analysis              │
│  • Memory retrieval                 │
│  • Code understanding               │
│  • CANNOT invoke tools              │
│  • CANNOT write files               │
│  • CANNOT execute shell commands    │
└──────────────┬──────────────────────┘
               │ Execution Plan (structured, auditable)
               ▼
┌─────────────────────────────────────┐
│  === STRUCTURAL SEPARATION BARRIER ===│
│  Validator Agent (different model)  │
│  Reviews: intent, scope, safety     │
└──────────────┬──────────────────────┘
               │ Approved / Blocked
               ▼
┌─────────────────────────────────────┐
│  EXECUTION CONTEXT (Action-Capable) │
│  • Tool invocation                  │
│  • File operations                  │
│  • Code generation                  │
│  • Shell commands                   │
│  • ALL actions logged to HIR        │
└─────────────────────────────────────┘
```

**Key properties:**
- Reasoning context has **zero tool access**
- Execution plans are **structured, auditable data** (not free text)
- Validator runs on a **different model family** than the executor
- **98.9% block rate** on adversarial attacks (100% at max security)

### Layer 2: Permission Gating

Every execution action passes through:
- **PermissionBridge** — plan | auto-edit | bypass mode check
- **Scope validation** — Filesystem boundaries, network allowlists, shell command allowlists
- **Resource quotas** — Token budget, file count, operation rate

### Layer 3: Multi-Agent Validation Pipeline

Critical operations trigger a **3-agent validation chain**:

```
Executor → Validator → Critic
  │            │           │
  │            │           └─ Reviews validator's REASONING, not just output
  │            └─ Different model family from executor
  └─ Performs the actual action
```

**Validation stages (ARIS 3-stage):**
1. **Evidence integrity** — Are the claimed facts actually present in the data?
2. **Result-to-claim mapping** — Does the evidence logically support the conclusion?
3. **Claim auditing** — Is the final output consistent with all intermediate claims?

### Layer 4: Behavioral Monitoring

Continuous monitoring of agent behavior for deviations:
- **Action sequence analysis** — Temporal pattern of tool calls over time
- **Intent deviation detection** — Does the sequence of actions match the stated goal?
- **Anomaly scoring** — Statistical baselines for "normal" agent behavior per task type
- **Escalation triggers** — Automatic lockdown on anomaly score > threshold

### Layer 5: Continuous Assurance

- **PRISM Drift Detection** — Daily automated detection of prompt degradation with auto-repair via GEPA re-optimization. Target: 99% prompt reliability
- **TEE Verifiability** — Cryptographic proof that guardrails executed correctly (enterprise tier)
- **Audit Engine** — Full HIR replay capability for post-hoc investigation

## Safety Decision Matrix

| Operation | Plan Mode | Auto-Edit | Bypass |
|-----------|-----------|-----------|--------|
| Read files | Auto | Auto | Auto |
| Write files (project) | Gate | Auto | Auto |
| Write files (system) | Gate | Gate | Gate |
| Shell: read-only | Gate | Auto | Auto |
| Shell: mutagenic | Gate | Gate | Gate |
| Network: outbound | Gate | Gate | Gate |
| Git: commit | Gate | Auto | Auto |
| Git: push | Gate | Gate | Gate |
| Self-modify harness | Gate+ARIS | Gate+ARIS | Gate+ARIS |
| Disable safety layers | BLOCKED | BLOCKED | Gate+consensus |

## Implementation Reference

- **Primary module:** `lyra_safety/parallax.py` — Cognitive-executive context separation
- **Validation pipeline:** `lyra_safety/validate_pipeline.py` — Executor→Validator→Critic
- **Intent monitor:** `lyra_safety/intent_monitor.py` — Behavioral anomaly detection
- **PRISM drift:** `lyra_evolution/drift_detector.py` — Prompt reliability monitoring
- **ARIS verification:** `lyra_verification/adversarial.py` — 3-stage adversarial review

## Research Basis

| Source | Key Finding | Adoption |
|--------|-------------|----------|
| [Parallax (2026)](https://arxiv.org/abs/2604.12986) | Cognitive-executive separation achieves 98.9% block rate | Layer 1 architecture |
| [ARIS (2026)](https://arxiv.org/abs/2605.03042) | 3-stage adversarial verification | Layer 3 validation |
| [Knowing-Doing Gap (2026)](https://arxiv.org/abs/2605.14038) | Tool-use recognition vs execution gap monitoring | Tool-call verification |
| [PRISM (2026)](https://arxiv.org/abs/2605.14454) | Automated prompt drift detection | Layer 5 continuous assurance |
| AWS Stop Hallucinations | Multi-agent validation pipeline pattern | Layer 3 architecture |
| Radware Intent-Based Security | Behavioral anomaly detection for sequences | Layer 4 monitoring |
