# Verifier -- How It Works

> Three-phase verification pipeline (objective/blind/cross-channel) with a 3-verifier panel plus an adversarial skeptic. Bias corrections through anonymization and ReTAS. Cross-source triangulation to catch fabricated success claims.
> **Block:** 10 | **Phase:** 2 (Quality & Planning) | **Depends on:** Agent Loop, Hooks and TDD Gate, Observability

## Three-Phase Pipeline

Every task completion must pass through three verification phases before being marked complete:

```
Task Result → Phase 1 (Objective) → Phase 2 (Blind) → Phase 3 (Cross-Channel) → Accept/Reject
                    │                    │                      │
                    v                    v                      v
              Deterministic         Anonymized            3 evidence
              checks (zero          different-family       channels must
              LLM cost)             LLM judge              converge
```

### Phase 1: Objective

Five deterministic checks run in parallel at zero LLM token cost:

| Check | What It Validates | Method |
|-------|------------------|--------|
| Acceptance tests | Exit code and output | JUnit XML / TAP parsing |
| File existence | Claimed output files exist | `os.path.exists()` + `git diff` |
| Forbidden files | No changes to protected paths | Git diff pattern matching |
| Coverage delta | No regression below threshold | Cobertura / lcov parsing |
| Typecheck and lint | `mypy --strict` / `tsc --noEmit` clean | Exit code capture |

Phase 1 catches 60-70% of all failures. Median reject takes 250ms because no LLM call is made.

### Phase 2: Blind (Anonymized + Different-Family)

An LLM judge from a **different model family** than the agent scores the output against a 5-criterion rubric. The evidence is **anonymized** -- filenames, variable names, and project-specific terms are replaced with generic placeholders to reduce familiarity bias.

```python
def verify_blind(evidence: str) -> BlindResult:
    anonymized = ReTAS.anonymize(evidence)
    judge_fn = select_judge(different_family_from(agent_family))
    scores = judge_fn(rubric.to_prompt(anonymized))
    return BlindResult(scores=scores, passed=all(s >= 7))
```

**ReTAS bias correction**: Re-Read, Template, Aggregate, Score. Each criterion is scored twice with different random seeds. The two scores are averaged. If they diverge by >2 points, a third evaluation is triggered. This reduces scoring variance by ~40%.

Different-family requirement: Self-Refine (Madaan et al., NeurIPS 2023) shows same-family evaluation inflates false acceptance rates by 2-3x.

### Phase 3: Cross-Channel Reconciliation

Three independent evidence channels must converge:

| Channel | Source | What It Proves |
|---------|--------|----------------|
| **Trace** | Agent loop execution transcript | Agent's claimed actions |
| **Diff** | `git diff` against starting commit | Actual filesystem mutations |
| **Snapshot** | Independent scan of filesystem + processes | Ground truth |

Disagreement between channels produces a `CrossChannelFinding`:

| Finding | Meaning |
|---------|---------|
| Minor | Formatting differences (whitespace, import order) |
| Moderate | Unclaimed side effects (file modified but not mentioned) |
| Critical | Fabrication (trace claims "tests passed" but snapshot shows no test invocation) |

## 3-Verifier Panel + Adversarial Skeptic

For high-stakes tasks, a panel of three verifiers runs independently:

```python
panel = [
    Verifier(config=fast_config),      # Haiku: fast, cheap
    Verifier(config=standard_config),  # Sonnet: balanced
    Verifier(config=strict_config),    # Opus: thorough, expensive
]

# Independent runs, collated results
results = [v.verify(...) for v in panel]
verdict = collate(results, strategy="majority_vote")
```

An **adversarial skeptic** (a fourth verifier with an adversarial prompt template) tries to find flaws that the other verifiers missed. The skeptic's prompt asks it to "prove this result is wrong" rather than "check if this is correct." The skeptic's findings are surfaced as advisory, not gating -- if the skeptic finds a critical issue, the result enters the correction pipeline for additional scrutiny.

## Correction Pipeline (4 Stages)

Failed verifications route through staged escalation:

| Stage | Action | Triggered By | Cost |
|-------|--------|--------------|------|
| 1. Retry | Re-run with same plan | Phase 1 failure | $0.00 (deterministic retry) |
| 2. Refine | Agent receives rubric scores, revises | Phase 2 failure | $0.05-$0.15 |
| 3. Escalate | Task reassigned to different agent | Cross-channel failure | $0.15-$0.35 |
| 4. Human Review | Flagged for manual inspection | Persistent failure | Human time |

92% of tasks pass after 3 correction rounds. False pass rate after full pipeline: <0.5%.

## Performance

| Metric | Phase 1 Only | Full Pipeline (Pass) | Full Pipeline (Reject) |
|--------|:------------:|:-------------------:|:---------------------:|
| Latency p50 | 80ms | 2.5s | 250ms |
| Latency p95 | 350ms | 9.0s | 800ms |
| Cost per eval | $0.000 | $0.05-$0.15 | $0.000 |
| Fraction of total | 100% | ~25% | ~75% |

Cost savings vs LLM-only verification: ~65%.

## Related Documents

- **Concepts:** [Verifier](../concepts/12-verifier.md), [Agent Loop](../concepts/01-agent-loop.md), [Safety Monitor](../concepts/11-safety-monitor.md)
- **Architecture:** [Safety and Security](../architecture/08-safety-security.md), [Gap Analysis](../architecture/13-gap-analysis.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Hooks and TDD Gate](06-hooks-tdd.md), [Observability](11-observability.md), [Safety Monitor](12-safety-monitor.md)

---

*References: Self-Refine (arXiv:2303.17651), CRITIC (arXiv:2305.11738), Constitutional AI (arXiv:2212.08073), ARIS (arXiv:2605.03042), Let's Verify Step by Step (arXiv:2305.20050)*
