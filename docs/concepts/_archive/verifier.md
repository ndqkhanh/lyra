---
title: Verifier
description: Two-phase verification with cross-channel evidence — cheap objective checks gate an expensive different-family LLM judge.
---

# Verifier <span class="lyra-badge advanced">advanced</span>

## What is the verifier

The verifier is the discipline that catches **fabricated success** —
the failure mode where an agent confidently reports the task is done
but the tests don't actually pass, the file isn't actually written,
or the diff doesn't match the plan. Lyra's verifier is **two-phase**
with **cross-channel evidence** because each phase, alone, can be
fooled.

Source: [`lyra_core/verifier/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier) ·
canonical spec: [`docs/blocks/11-verifier-cross-channel.md`](../blocks/11-verifier-cross-channel.md).

## Two phases

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#8b5cf6', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#a78bfa', 'lineColor': '#94a3b8', 'secondaryColor': '#1e293b', 'tertiaryColor': '#0d1117', 'background': '#0d1117', 'mainBkg': '#1e293b', 'nodeBorder': '#a78bfa', 'clusterBkg': '#1e293b', 'clusterBorder': '#8b5cf6', 'titleColor': '#c084fc', 'edgeLabelBackground': '#1e293b' }}%%
flowchart TD
    A[Task complete claim] --> P1{Phase 1: Objective}
    P1 -->|fail| Reject1[Reject<br/>concrete reason]
    P1 -->|pass| P2{Phase 2: Subjective<br/>different-family judge}
    P2 -->|fail| Reject2[Reject<br/>rubric scores]
    P2 -->|pass| CC{Cross-channel<br/>trace ↔ diff ↔ env snapshot agree?}
    CC -->|disagree| Reject3[Reject<br/>fabrication suspected]
    CC -->|agree| Accept[Accept<br/>task done]
```

| Phase | Cost | What it checks |
|---|---|---|
| **1 · Objective** | Cheap | Tests / types / lint / expected-files exist with correct content roles |
| **2 · Subjective** | Expensive | A different-family LLM judges quality against a rubric |
| **Cross-channel** | ~zero | Trace + diff + environment snapshot must agree on what happened |

## Phase 1 — objective

Source: [`lyra_core/verifier/objective.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/objective.py).

Every check is a **fast, deterministic** Python function that returns
`pass / fail / not-applicable`. Examples:

```python
@check(name="acceptance-tests-pass")
def acceptance_tests_pass(plan: Plan, env: Env) -> Verdict:
    failures = run_pytest(plan.acceptance_tests)
    return Verdict.fail(f"{len(failures)} failures") if failures else Verdict.pass_()

@check(name="expected-files-exist")
def expected_files_exist(plan: Plan, env: Env) -> Verdict:
    missing = [f for f in plan.expected_files if not env.fs.exists(f)]
    return Verdict.fail(f"missing: {missing}") if missing else Verdict.pass_()

@check(name="forbidden-files-untouched")
def forbidden_untouched(plan: Plan, env: Env) -> Verdict:
    touched = env.git.diff_files()
    bad = [f for f in plan.forbidden_files if f in touched]
    return Verdict.fail(f"touched: {bad}") if bad else Verdict.pass_()

@check(name="coverage-non-regressing")
def coverage_non_regressing(plan: Plan, env: Env) -> Verdict:
    delta = env.coverage.delta_since(plan.baseline_ref)
    return Verdict.fail(f"delta={delta:+.2%}") if delta < 0 else Verdict.pass_()
```

Phase 1 is **cheap** — no model calls, just real subprocesses. If any
single check fails, the verifier rejects with a concrete reason and
**Phase 2 doesn't run**. This is the cost-shaping choice that lets
the expensive subjective phase exist at all.

## Phase 2 — subjective (different-family judge)

Source: [`lyra_core/verifier/subjective.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/subjective.py).

Only runs if Phase 1 passes. The evaluator must be a **different
model family** than the generator — this is the load-bearing check
against narrative fluency.

```python
class EvaluatorFamily(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    XAI = "xai"
    # …

def must_differ(generator_family: EvaluatorFamily, evaluator_family: EvaluatorFamily) -> None:
    if generator_family == evaluator_family:
        raise FamilyConflictError(
            f"evaluator {evaluator_family} is same family as generator; "
            "configure a different family in [harness.three_agent.evaluator]"
        )
```

The judge gets:

- The plan
- The diff
- The HIR trace (action stream, not text-stream)
- The Phase 1 results

It produces a **rubric-scored verdict**:

```python
@dataclass
class SubjectiveVerdict:
    decision: Literal["accept", "reject", "needs-revision"]
    rubric: dict[str, float]    # 0.0–1.0 per criterion
    rationale: str
    revision_advice: str | None = None
```

Default rubric criteria: `correctness`, `style`, `simplicity`,
`testability`, `does-the-diff-match-the-plan`. Customize in
`~/.lyra/config.toml`.

## Cross-channel evidence

Source: [`lyra_core/verifier/cross_channel.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/cross_channel.py).

Three independent records of "what happened":

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#8b5cf6', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#a78bfa', 'lineColor': '#94a3b8', 'secondaryColor': '#1e293b', 'tertiaryColor': '#0d1117', 'background': '#0d1117', 'mainBkg': '#1e293b', 'nodeBorder': '#a78bfa', 'clusterBkg': '#1e293b', 'clusterBorder': '#8b5cf6', 'titleColor': '#c084fc', 'edgeLabelBackground': '#1e293b' }}%%
graph LR
    Trace[Trace<br/>tool calls + args]
    Diff[Diff<br/>git working tree]
    Env[Env snapshot<br/>filesystem hash + tests]

    Trace -->|implies| Expected[Expected post-state]
    Diff  -->|is| Actual[Actual post-state]
    Env   -->|attests| Independent[Independent post-state]

    Expected --> Compare{All 3 agree?}
    Actual --> Compare
    Independent --> Compare
    Compare -->|yes| OK[Accept]
    Compare -->|no| Reject[Reject: fabrication suspected]
```

If the trace says "wrote 50 lines to `src/foo.py`" but the diff shows
no change to that file, the verifier rejects — the model lied (or the
filesystem lied; either way, don't trust the result).

Cross-channel disagreement is the verifier's most powerful signal
against test-disable tricks and `chmod 000` hacks.

## Process Reward Model (PRM)

Source: [`lyra_core/verifier/prm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/prm.py).

For long horizons, end-of-task verification is too late. The PRM is
a small reward signal computed every step that estimates "is this
step moving towards the plan?" — used to prune obviously-divergent
trajectories early.

The PRM is **advisory**, not gating: it surfaces in the trace and the
HUD, and a hook can act on it (e.g. abort if PRM stays negative for
N steps), but the kernel doesn't terminate based on it alone.

## Upcoming: anonymized bias-corrected adversarial verification (Phase 4)

The Phase 4 verifier upgrade adds **anonymized, bias-corrected,
multi-agent verification** — a panel where identity markers are
stripped and cognitive biases are corrected before voting:

```mermaid
flowchart TD
    A[Task complete claim] --> B[Step 1: Objective checks<br/>same as today]
    B -->|pass| C[Step 2: Anonymize<br/>strip identity markers]
    C --> D[Step 3: Panel<br/>3 verifiers + 1 skeptic]
    D --> E[Step 4: Bias correction<br/>ReTAS dialectical alignment]
    E --> F[Step 5: Collusion check<br/>channel monitor]
    F --> G[Step 6: Vote<br/>>>= 2/3 confirm?]
    G -->|yes| H[Accept]
    G -->|no| I[Reject + evidence]
```

The **4-correction pipeline** addresses each known multi-agent
failure mode independently:

| Correction | Failure mode | Paper | What it does |
|---|---|---|---|
| **Anonymization** | Identity skew (IBC->0) | 2510.07517 | Strips agent identity from
  justifications before other agents evaluate them |
| **ReTAS alignment** | Actor-observer asymmetry | 2604.19548 | Requires each verifier to
  explain reasoning; another verifier critiques it dialectically |
| **Collusion detection** | Lying with Truths | 2601.01685 | Monitors evidence overlap
  and voting pattern similarity across agents |
| **Rogue prevention** | Early termination with uncertainty | 2502.05986 | Monitors prediction
  likelihood; intervenes when uncertainty is high |

Voting: **>= 2/3 verifiers must confirm** after adversarial challenge.
The skeptic verifier is tasked with finding flaws — their disagreement
is a feature, not a failure. If the skeptic finds a valid flaw, the
result is rejected regardless of other votes.

See [lyra-upgrade/plans/25-adversarial-panel.md](../lyra-upgrade/plans/25-adversarial-panel.md).

## Upcoming: mutation-gated verification — SABER (Phase 4)

SABER (En2z9dckgP) distinguishes **mutating vs non-mutating actions**
and gates verification accordingly:

| Action type | Verification strategy | Example |
|---|---|---|
| **Mutating** (changes state) | Full cross-channel check + Phase 2 | `write`, `edit`, `bash` with side effects |
| **Non-mutating** (read-only) | Lightweight Phase 1 only | `read`, `grep`, `glob` |
| **Ambiguous** (unknown effect) | Apply mutation test: run in sandbox, check for state change | `bash` without clear effect |

This is the load-bearing insight from SABER (+28% Airline metric):
most agent actions are non-mutating and don't need expensive verification.
By identifying mutation at the tool call level, the verifier saves cost
on the 70%+ of calls that are read-only.

## Upcoming: ErrorProbe failure attribution (Phase 4)

ErrorProbe (2604.17658) provides **3-stage semantic failure
attribution** for failed verification:

1. **Localise**: which agent + which step caused the failure?
2. **Classify**: is it a planning error, execution error, or
   verification false-positive?
3. **Recommend**: rollback, re-run with modified prompt, or skip
   and flag for human review?

ErrorProbe runs automatically when the verifier rejects — it's the
first step toward autonomous failure recovery in the fleet.

## TDD reward integration

Source: [`lyra_core/verifier/tdd_reward.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/tdd_reward.py).

When the [TDD gate](../howto/tdd-gate.md) is on, the verifier
incorporates the gate's RED→GREEN→REFACTOR phase signal into the
final accept decision. A task that passes Phase 1 and Phase 2 but
never went through a RED phase is downgraded to `needs-revision`
(with the message "no failing test was ever written; coverage of new
behaviour is suspect").

## Why the verifier

The verifier exists because models confidently report fabricated success. A model will say "task complete" when the file was never written, the tests are a different version, or the diff doesn't match the plan. The two-phase design with cross-channel evidence catches this: objective checks are cheap and gating, the subjective judge must be a different model family (preventing narrative collusion), and the cross-channel reconciler compares the trace against the actual filesystem state.

## When to use the verifier

- The verifier runs automatically after task completion, especially when plan mode was used. No manual action is needed.
- Enable the TDD gate integration for tasks where test-driven development discipline is required — it downgrades results that never went through a RED phase.
- Use the Process Reward Model (PRM) signal in the HUD to detect divergent trajectories early.

## When NOT to use the verifier

- Do not use the same model family for generation and verification. The family-conflict guard enforces this, but configure your evaluator model in a different provider family.
- The subjective Phase 2 is expensive; it only fires when Phase 1 passes. Do not skip Phase 1 for subjective-only verification.
- For read-only explorations where no state change occurred, the verifier may not add value — consider whether verification is needed at all.

## Next steps

1. Read [Safety monitor](safety-monitor.md) to see how continuous monitoring complements verification.
2. Explore the canonical block spec at [`docs/blocks/11-verifier-cross-channel.md`](../blocks/11-verifier-cross-channel.md).
3. For the adversarial panel upgrade (Phase 4), see [lyra-upgrade/plans/25-adversarial-panel.md](../lyra-upgrade/plans/25-adversarial-panel.md).
4. For integration with the TDD gate, see [the TDD how-to](../howto/tdd-gate.md).

## Where to look in the source

| File | What lives there |
|---|---|
| `lyra_core/verifier/objective.py` | Phase 1 deterministic checks |
| `lyra_core/verifier/subjective.py` | Phase 2 LLM judge with rubric |
| `lyra_core/verifier/cross_channel.py` | Trace ↔ diff ↔ env-snapshot reconciler |
| `lyra_core/verifier/evaluator_family.py` | Family-conflict guard |
| `lyra_core/verifier/evidence.py` | Evidence collection harness |
| `lyra_core/verifier/prm.py` | Per-step Process Reward Model |
| `lyra_core/verifier/tdd_reward.py` | TDD-phase signal merging |
| `lyra_core/verifier/adversarial_panel.py` | Anonymized 3+1 verifier panel with voting *(Phase 4)* |
| `lyra_core/verifier/bias_correction.py` | ReTAS dialectical alignment and identity anonymization *(Phase 4)* |
| `lyra_core/verifier/collusion.py` | Collusion detection on verifier channel traces *(Phase 4)* |
| `lyra_core/verifier/saber.py` | Mutation-gated verification (SABER pattern) *(Phase 4)* |
| `lyra_core/verifier/error_probe.py` | ErrorProbe 3-stage failure attribution *(Phase 4)* |

[← Plan mode](plan-mode.md){ .md-button }
[Continue to Safety monitor →](safety-monitor.md){ .md-button .md-button--primary }
