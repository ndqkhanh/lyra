# Self-Evolving Optimizer: GEPA-Style Prompt Evolution with Validation-Gated Safety
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/27-rl-optimizer.md) | [Code](../../src/lyra/rl_optimizer/)

## Abstract

Lyra's self-evolving optimizer enables agents to improve their own skills, prompts, and memory without human intervention — while preventing the misevolution that degrades safety in 92% of self-improving systems. The design fuses three independently validated techniques: (1) GEPA-style reflective prompt evolution (ICLR 2026 Oral) — generate variant→evaluate→keep winner→mutate→repeat, gradient-free and working on any provider, (2) SkillOpt-style validation-gated text optimization (Microsoft) with cosine-scheduled edit budget achieving +23.5 avg gain across 7 diverse models, and (3) compact gene representations (~230 tokens, EvoMap/GEP) that outperform verbose documentation (-1.1pp) at 10× fewer tokens. Three misevolution guardrails are mandatory: gated promotion (no evolved artifact becomes default without ≥1% regression threshold), frozen evaluators (separate from the optimizer, never co-evolve), and human-approval gates before any evolved default swap.

## Introduction

**The problem.** Agents accumulate experience across thousands of sessions. Without self-evolution, every improvement requires a human to analyze failures, rewrite prompts, and redeploy. With self-evolution, agents improve autonomously — but 92% of optimization trials experience temporary performance drops, 14% fail entirely, and safety alignment decays by 45pp after memory accumulation [Godel Agent, 2410.04444v4; Misevolve, 2509.26354v2].

**Intuition.** Think of self-evolution as "agent practice, not agent redesign." After each task, the agent reflects: "What worked? What failed? What should I do differently next time?" It writes compact, testable lessons (~230 tokens, not long docs). Before any lesson becomes the new default, it must pass a frozen evaluator that checks: "Does this improve outcomes without making anything worse?" Only then does it get promoted. Human approval is the final gate.

**Contributions:**
1. Post-session success/failure classification with dual-source memory extraction (successes + failures)
2. Bounded-edit optimization: cosine-scheduled edit budget (4→2), strict validation gate (≤1% regression)
3. Compact gene representations: signals, summary, strategy, AVOID cues, constraints — outperforming SKILL.md
4. Three mandatory misevolution guardrails: gated promotion, frozen evaluators, human-approval gate
5. Training-free Explore-Reflect-Steer loop (TF-TTCL, 2604.13552v1) for closed-model providers

## Related Work

| System | Optimization | Safety Gates | Representation | Provider-Agnostic |
|--------|-------------|--------------|---------------|-------------------|
| **Lyra** | GEPA + SkillOpt + GEP | 3 mandatory guardrails | Genes (~230 tokens) | Yes (training-free path) |
| GEPA (ICLR 2026 Oral) | Reflective prompt evolution | No | Text prompts | Yes (gradient-free) |
| SkillOpt (Microsoft) | Validation-gated text opt | Validation gate only | Text | Yes |
| DGM-H (Meta) | Self-rewriting harness | No | Code-level | No (fine-tuning) |
| ReasoningBank (Google) | Dual-source extraction | No | Structured schema | Yes |
| EvoMap/GEP | Genome Evolution Protocol | Non-destructive rollback | Genes + Capsules + Events | Yes |
| Misevolve (ICLR 2026) | N/A (safety analysis) | N/A (documents failures) | N/A | N/A |

Lyra's key divergence: mandatory guardrails from day one. The Misevolve paper proved that safety decays across ALL self-evolution pathways. Most systems bolt on safety later — Lyra designs it in.

## Method

```mermaid
flowchart TD
    SESSION[Agent Session] --> CLASSIFY{Success/Failure?}
    CLASSIFY -->|Success| EXTRACT_S[Extract: why it worked]
    CLASSIFY -->|Failure| EXTRACT_F[Extract: why it failed]
    EXTRACT_S --> COMPACT[Compact Gene (~230 tokens)]
    EXTRACT_F --> COMPACT
    COMPACT --> VALIDATE{Frozen Evaluator}
    VALIDATE -->|≤1% regression| PROMOTE[Promote to Candidate]
    VALIDATE -->|>1% regression| DISCARD[Discard]
    PROMOTE --> HUMAN{Human Approval}
    HUMAN -->|Approve| DEFAULT[New Default]
    HUMAN -->|Reject| DISCARD
    DISCARD --> LOG[Log for analysis]
```

### Gene Representation

| Field | Type | Example |
|-------|------|---------|
| matching_signals | list[str] | ["file write with sudo", "production config edit"] |
| summary | str | "Always verify the target file exists before writing" |
| strategy_steps | list[str] | ["1. Run ls on target path", "2. Check file exists", "3. Proceed with write"] |
| AVOID_cues | list[str] | ["never assume file exists", "skip pre-check on /tmp only"] |
| constraints | list[str] | ["applies to: file_write, file_edit tools"] |
| validation_hooks | list[str] | ["pre_write_check.sh"] |

### Misevolution Guardrails

| Guardrail | Mechanism | Failure it Prevents |
|-----------|-----------|---------------------|
| Gated promotion | ≤1% regression on held-out eval set | Degradation from "optimistic" edits |
| Frozen evaluator | Evaluator model never co-evolves with optimizer | Evaluator drift, reward hacking |
| Human approval gate | No evolved default without explicit human accept | Silent safety-alignment decay |
| Non-destructive default | git stash, not reset --hard | Irreversible corruption |
| Execution-bias detector | Integrated gradients causal attribution | Benign experience increasing attack surface |

## Working Flow

After every task, Lyra reflects: did it succeed or fail? The lesson gets extracted as a compact "gene" -- about 230 tokens capturing the context, the mistake, and the fix.

**Example:** Lyra keeps failing because it writes files without checking if the parent directory exists:

1. Lyra completes a session and the classifier flags it as a **failure**. Extracted memory: "tried to write /etc/nginx/sites-enabled/default but the directory didn't exist."
2. The extractor produces a gene: signal = "file write to missing directory," strategy = "always run `ls` on parent path first," AVOID = "don't assume directories exist."
3. The **frozen evaluator** checks this gene against a held-out test suite. If performance drops more than 1%, the gene is discarded. If it passes, it enters SHADOW mode.
4. After N shadow trials with zero false positives, the gene requests **human approval**. Only then does it become Lyra's default behavior.

## Debate (Trade-offs)

| Alternative | Pro | Con | Decisive Factor |
|-------------|-----|-----|-----------------|
| No self-evolution | Safe, predictable | Agents never improve, human bottleneck | Self-evolution is a primary direction (§0) |
| Unrestricted evolution | Maximum improvement velocity | 45pp safety decay, 92% temporary regression | Misevolve paper: safety loss is guaranteed |
| Fine-tuning (SEAL, DGM-H) | Persistent weight updates | Requires white-box access, provider-dependent | Multi-provider constraint (§4.5) |
| Doc-style skills (SKILL.md) | Human-readable | -1.1pp vs genes at 10× tokens | Genes are more robust (GEP, 4600 trials) |

**Skeptic objection (Senior AI Safety Engineer):** "Frozen evaluators can drift if the task distribution shifts. Gated promotion with a fixed threshold doesn't detect slow, cumulative safety decay across many small edits."

**Resolution:** Add distribution-shift detection (KL divergence of task embeddings over time) as a Phase 2 guardrail. For now, the human-approval gate and periodic full-eval-suite runs catch cumulative drift.

## Conclusion

**Implemented**: Post-session classification, dual-source extraction, compact gene format, 3 mandatory guardrails (gated promotion, frozen evaluator, human-approval gate). Core: `src/lyra/rl_optimizer/` and `src/lyra/safety/evolution.py`.

**Limitations**: GEPA-style full evolution loop requires eval harness integration. SkillOpt bounded-edit requires per-module edit budget calibration. Distribution-shift detection deferred.

**Future work**: Full GEPA loop with automated variant generation and evaluation. GRPO-based Designer+Executor co-evolution (MetaAgent-X pattern). Cross-harness skill transfer.
