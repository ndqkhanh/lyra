# Harness Evolution: Self-Optimizing Agent Infrastructure

> **Inspiration:** [Meta-Harness (2026)](https://arxiv.org/abs/2603.28052), [AEvo (2026)](https://arxiv.org/abs/2605.13821), [GEPA (ICLR 2026 Oral)](https://arxiv.org/abs/2310.03714), [Code as Harness (2026)](https://arxiv.org/abs/2605.18747)
> **Status:** Phase 13.4 — Implementation target: Weeks 7-8

## Overview

Lyra's self-evolution goes beyond prompt optimization — the **harness itself evolves**. A meta-agent observes execution traces, identifies bottlenecks in the orchestration code, proposes improvements, and deploys them through a rigorous adversarial verification pipeline. The research is clear: the harness, not the model, is the decisive factor in agent capability.

## The Harness is the Differentiator

Research from [Code as Harness (2026)](https://arxiv.org/abs/2605.18747) establishes a three-layer framework:

1. **Interface** — How users interact with the agent (CLI, TUI, API)
2. **Mechanisms** — What the agent can do (tools, memory, reasoning, coordination)
3. **Scaling** — How the agent handles growth (fleet, routing, scheduling, safety)

The key insight: **optimizing the mechanisms layer yields the highest ROI**. Meta-Harness proved this empirically — optimizing harness code produced +7.7pts improvement with 4x fewer tokens than model upgrades alone.

## The Self-Evolution Pipeline

```
┌────────────────────────────────────────────────────────────┐
│                    1. OBSERVE                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ HIR Traces   │  │ Performance  │  │ Drift        │     │
│  │ (tool calls, │  │ Metrics      │  │ Signals      │     │
│  │  outcomes,   │  │ (success %,  │  │ (prompt deg, │     │
│  │  errors)     │  │  latency,    │  │  pattern     │     │
│  │              │  │  token use)  │  │  shifts)     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         └─────────────────┼─────────────────┘              │
│                           ▼                                 │
├────────────────────────────────────────────────────────────┤
│                    2. ANALYZE                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Bottleneck Detection                             │      │
│  │ • Which harness paths consume most tokens?       │      │
│  │ • Where do failures cluster?                     │      │
│  │ • Which operations have highest latency?         │      │
│  └────────────────────┬─────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Pattern Mining                                   │      │
│  │ • What strategies correlate with success?        │      │
│  │ • Which prompt patterns generalize best?         │      │
│  │ • What failure modes repeat across tasks?        │      │
│  └────────────────────┬─────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Gap Analysis                                     │      │
│  │ • Benchmark target vs actual performance         │      │
│  │ • Per-category breakdown (coding, research, etc) │      │
│  │ • Regression from previous harness versions      │      │
│  └────────────────────┬─────────────────────────────┘      │
│                       ▼                                     │
├────────────────────────────────────────────────────────────┤
│                    3. PROPOSE (Meta-Agent)                   │
│  ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ GEPA v2          │ │ AEvo         │ │ Meta-Harness │   │
│  │ Prompt Evolution │ │ Meta-Editing │ │ Code Search  │   │
│  │                  │ │              │ │              │   │
│  │ • Multi-agent    │ │ • Edit       │ │ • Search     │   │
│  │   parallel search│ │   procedures │ │   harness    │   │
│  │ • Pareto frontier│ │ • Stable     │ │   code for   │   │
│  │ • Combee 17x     │ │   interfaces │ │   patterns   │   │
│  │   speedup        │ │ • 26% rel.   │ │ • Agentic    │   │
│  │ • $2-10/run      │ │   improvement│ │   proposer   │   │
│  └────────┬─────────┘ └──────┬───────┘ └──────┬───────┘   │
│           └──────────────────┼────────────────┘            │
│                              ▼                              │
│              Candidate Improvements                         │
│              (prompts + code + procedures)                   │
├────────────────────────────────────────────────────────────┤
│                    4. VERIFY (Adversarial)                   │
│  ┌──────────────────────────────────────────────────┐      │
│  │ ARIS 3-Stage Review                              │      │
│  │ 1. Evidence integrity — are claimed facts real?   │      │
│  │ 2. Result-to-claim — does evidence support output?│      │
│  │ 3. Claim auditing — are all intermediate claims   │      │
│  │    consistent with the final output?             │      │
│  └────────────────────┬─────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Cross-Model Generalization Testing               │      │
│  │ • Test on different model families               │      │
│  │ • Verify improvement isn't model-specific        │      │
│  │ • Minimum 3 provider families                    │      │
│  └────────────────────┬─────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Regression Testing                               │      │
│  │ • Holdout task suite                             │      │
│  │ • No degradation on any category                 │      │
│  │ • Performance must be strictly >= baseline       │      │
│  └────────────────────┬─────────────────────────────┘      │
│                       ▼                                     │
├────────────────────────────────────────────────────────────┤
│                    5. DEPLOY                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Canary       │  │ Monitor      │  │ Full Rollout │     │
│  │ 10% traffic  │──│ PRISM drift  │──│ Sustained    │     │
│  │ 24h observe  │  │ detection    │  │ improvement  │     │
│  └──────────────┘  └──────┬───────┘  └──────────────┘     │
│                           │                                 │
│              Regression → Auto-Rollback                     │
│              Drift → Back to PROPOSE                        │
└────────────────────────────────────────────────────────────┘
```

## Three Optimization Engines

### GEPA v2: Multi-Agent Prompt Evolution

The original GEPA (Generate → Evaluate → Preserve → Apply) optimizer is upgraded to v2 with:

- **Parallel multi-agent search** — Multiple agents explore the prompt space simultaneously (Combee-inspired, 17x speedup over sequential)
- **Pareto frontier selection** — Choose complementary improvements rather than a single "best"
- **Joint optimization** — Optimize prompts AND harness code together, not independently
- **Cost efficiency** — $2-10 per evolution run vs $50-200 for manual prompt engineering

**Files:** `lyra_evolution/gepa_v2.py`

### AEvo: Meta-Agent Procedure Editing

AEvo introduces a meta-agent that observes accumulated execution state and edits the agent's procedures:

- **Harnessed meta-editing** — Stable, typed interfaces for the meta-agent to propose edits through
- **Evidence-based proposals** — Every suggested edit must cite which execution traces support it
- **Drift prevention** — Long-horizon evolution without degradation (26% relative improvement)
- **Scope control** — Meta-agent can only edit procedures within declared safety boundaries

**Files:** `lyra_meta_evolution/aevo_meta.py`

### Meta-Harness: Outer-Loop Code Optimization

The most ambitious engine — an outer loop that searches over Lyra's own harness code:

- **Agentic proposer** — Full filesystem access to read harness code and prior candidates
- **Pattern library** — Known optimization patterns from successful harness modifications
- **Cross-model testing** — Verify improvements generalize across model families
- **Target:** +5-8pts on coding benchmarks, 4x fewer tokens for equivalent performance

**Files:** `lyra_meta_evolution/harness_opt.py`

## What Gets Optimized?

| Component | Optimization | Engine | Frequency |
|-----------|-------------|--------|-----------|
| System prompts | GEPA v2 prompt search | GEPA v2 | Daily (PRISM-triggered) |
| Tool descriptions | Format + ordering optimization | GEPA v2 | Weekly |
| Agent procedures | Step sequences, decision trees | AEvo | Weekly |
| Routing rules | Threshold tuning, model assignment | Meta-Harness | Continuous |
| Memory consolidation params | Forgetting curves, TTL values | Meta-Harness | Monthly |
| Fleet orchestration | Squad composition, task allocation | Meta-Harness | Per-task learning |
| Safety thresholds | Anomaly scores, rate limits | Meta-Harness | Monthly (conservative) |

## Safety Guardrails for Self-Evolution

Self-modification is the riskiest operation an agent can perform. These guardrails are **mandatory and non-bypassable**:

1. **ARIS 3-stage adversarial review** — Every proposed change must pass evidence integrity, result-to-claim, and claim auditing checks
2. **Cross-model testing** — Changes must improve performance across ≥3 model families, not just the one that proposed them
3. **Canary deployment** — 10% traffic for 24 hours before full rollout
4. **Auto-rollback** — Instant reversion to last-known-good if performance degrades
5. **Human approval for harness structure changes** — Prompt optimization can be automatic; code structure changes require human sign-off
6. **Immutable audit log** — Every self-modification is permanently recorded in HIR

## Implementation Reference

- **GEPA v2:** `lyra_evolution/gepa_v2.py` — Multi-agent prompt evolution
- **AEvo:** `lyra_meta_evolution/aevo_meta.py` — Procedure meta-editing
- **Meta-Harness:** `lyra_meta_evolution/harness_opt.py` — Outer-loop code optimization
- **PRISM:** `lyra_evolution/drift_detector.py` — Prompt reliability monitoring
- **ARIS:** `lyra_verification/adversarial.py` — 3-stage adversarial review
- **Canary deployer:** `lyra_core/evolve/canary.py` — Safe rollout management

## Research Basis

| Source | Key Finding | Adoption |
|--------|-------------|----------|
| [Meta-Harness (2026)](https://arxiv.org/abs/2603.28052) | Outer-loop harness optimization: +7.7pts, 4x fewer tokens | Core architecture |
| [AEvo (2026)](https://arxiv.org/abs/2605.13821) | Meta-agent procedure editing: 26% relative improvement | Procedure evolution |
| [GEPA (ICLR 2026 Oral)](https://arxiv.org/abs/2310.03714) | Prompt evolution with Pareto frontier: $2-10/run | Prompt optimization |
| [Code as Harness (2026)](https://arxiv.org/abs/2605.18747) | Three-layer framework: interface, mechanisms, scaling | Architectural reference |
| [Combee (2026)](https://arxiv.org/abs/2604.15771) | Parallel prompt learning: 17x speedup | GEPA v2 parallelism |
| [ARIS (2026)](https://arxiv.org/abs/2605.03042) | Cross-model adversarial verification | Safety gate |
| [PRISM (2026)](https://arxiv.org/abs/2605.14454) | Prompt drift detection with auto-repair | Continuous monitoring |
| [HyperAgents](https://arxiv.org/abs/2506.09870) | Self-code-rewriting improved SWE-bench from 20%→50% | Proof of concept |

## Success Metrics

| Metric | Baseline | Target | Timeline |
|--------|----------|--------|----------|
| SWE-bench Pro | Current | 60%+ | Week 10 |
| Harness efficiency | 1x | 4x fewer tokens for equivalent performance | Week 8 |
| Prompt reliability | Current | 99% (PRISM-monitored) | Week 6 |
| Cross-model generalization | N/A | Improvement on ≥3 model families | Week 8 |
| Evolution safety | N/A | Zero regressions in canary phase | Continuous |
| Auto-rollback speed | N/A | <30s from regression detection | Week 6 |
