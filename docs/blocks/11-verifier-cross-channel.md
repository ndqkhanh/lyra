# Lyra Block 11 — Verifier / Evaluator (Two-Phase, Cross-Channel)

The verifier is the second opinion. It decides whether the artifact an agent produced actually satisfies the plan, using cheap objective checks first and a different-family LLM evaluator second. Cross-channel evidence (trace ↔ diff ↔ env snapshot) must agree before a task may be marked complete.

Lineage: [Orion-Code Block 07](../../../orion-code/docs/blocks/07-verifier-evaluator.md), [Claw-Eval research](../../../../docs/38-claw-eval.md), [Verifier-Evaluator Loops](../../../../docs/11-verifier-evaluator-loops.md).

## Responsibility

1. Gate every session's completion with **Phase 1 (objective)** and **Phase 2 (subjective, different-family)** checks.
2. Require **cross-channel agreement** between trace, git diff, and environment snapshot.
3. Return a structured verdict (`accept` / `reject` / `degraded_eval`) with rubric scores, blocking/advisory classification, and cited evidence.
4. Track a separate **safety monitor** sidecar ([block 12](12-safety-monitor.md)) that runs continuously.

## Two-phase gate

### Phase 1 — Objective (fast, deterministic)

```python
objective = ObjectiveReport(
    tests_pass          = run_acceptance_tests(plan.acceptance_tests).exit == 0,
    typecheck_clean     = run_typecheck().exit == 0,
    lint_clean          = run_lint().exit == 0,
    plan_files_touched  = set(plan.expected_files) <= set(diff.files),
    no_forbidden_paths  = not any(f in diff.files for f in plan.forbidden_files),
    coverage_delta_ok   = coverage_delta >= -config.coverage_tolerance,
    no_new_todos_unjustified = not diff.introduces_unjustified_todos(),
)
if not objective.all_passed():
    return EvaluatorVerdict(verdict="reject", phase1_objective=objective)
```

A Phase 1 failure is immediate reject with a structured critique list. No LLM called.

### Phase 2 — Subjective (LLM, smart slot, different-family preferred)

Runs only if Phase 1 passes. The Phase-2 evaluator runs on the session's **smart slot** (default `deepseek-v4-pro` → `deepseek-reasoner`), resolved through `_resolve_model_for_role(session, "verify")`. When two model families are available, Lyra still prefers a *different family* than the generator (see [§ Different-family evaluator](#different-family-evaluator)) — the slot wiring just guarantees the evaluator gets the reasoning-tier model regardless of which provider stack the operator has connected. Inputs:

- Plan artifact (ground truth).
- Git diff (limited to ~200 KB; truncated with markers if larger).
- Trace digest (not raw trace — structured list of decisions + tool calls).
- Environment snapshot delta (filesystem delta, process table delta, DB state if applicable).

Evaluator prompt:

```
You are the Evaluator. Do NOT fix code. Identify issues, ground every finding
in evidence (file:line, span id, snapshot delta). Score on rubric:
 - correctness (does it do what the plan says?)
 - coverage (are acceptance tests exhaustive?)
 - faithfulness (did it stay within scope?)
 - style (coherent with codebase conventions?)
 - safety (no backdoors, no secret leaks, no disabled tests)

Return JSON exactly matching EvaluatorVerdict schema.
```

Output schema:

```json
{
  "verdict": "accept",
  "phase1_objective": { "...": true },
  "phase2_subjective": {
    "rubric_scores": { "correctness": 4, "coverage": 3, "faithfulness": 5, "style": 4, "safety": 5 },
    "failures": [
      {
        "criterion": "toggle persists across reload",
        "evidence": "src/settings/ThemeToggle.tsx:27-33 uses useState but not localStorage",
        "fix_hint": "hydrate from useSettings.getTheme() on mount; persist on change"
      }
    ],
    "blocking": true
  },
  "cross_channel": { "mismatches": [] },
  "evaluator_model": "deepseek-v4-pro",
  "trace_id": "..."
}
```

Rejections with `blocking: false` are advisory — style nits, suggestions — and session ships with them captured as follow-up notes.

## Cross-channel agreement

Claw-Eval's insight: trust emerges from multiple independent channels agreeing. Lyra requires three:

1. **Execution trace** — what the agent says it did (trace digest).
2. **Git diff** — what actually changed on disk.
3. **Environment snapshot delta** — snapshot before/after of filesystem + process + DB + env vars.

Mismatch examples (caught at this gate):

- Trace says "I did not touch auth.py" but diff shows auth.py modified → `trace_diff_mismatch`.
- Diff shows only `settings.py` changed, but snapshot shows `config.yaml` also changed (untracked!) → `untracked_side_effect`.
- Trace claims tests passed but snapshot shows pytest was not invoked → `fabricated_test_run`.

Any mismatch → verdict `reject` with evidence; or escalate to `human_review` depending on severity.

### Snapshot mechanism

On macOS: `fsevents`. Linux: `fanotify` with fall-back to polling. Windows: `ReadDirectoryChangesW`. Snapshot records:

- Files created / modified / deleted (with hash).
- Processes spawned (pid, cmd).
- Env var changes in the child process (for Bash calls).
- Selected sqlite/file-backed DB state (optional plugin).

Incremental snapshotting keeps overhead small on most sessions.

## Different-family evaluator

Out of the box (v2.7.1 default DeepSeek-only stack): generator on `deepseek-v4-flash` (fast slot) and evaluator on `deepseek-v4-pro` (smart slot). This is **same-family** — the trace is tagged `degraded_eval=same_family` and the verdict carries a corresponding warning. The moment a second provider is connected via `lyra connect`, the evaluator config below kicks in and the warning clears.

Recommended cross-family pairing: Anthropic Sonnet on the fast slot + OpenAI GPT-5 on the smart slot, *or* DeepSeek `deepseek-v4-flash` on the fast slot + Claude Opus on the smart slot — anything that puts the generator and the evaluator on different model families.

Rationale: CRITIC and Self-Refine research show substantially higher miss rates on shared blind spots. Different-family is a cheap way to break that.

Configuration:

```yaml
# v2.7.1 slot-aware layout (preferred):
fast_model:  deepseek-v4-flash       # generator / chat / tool calls
smart_model: claude-opus-4.5         # evaluator / planner / verifier  (different family)

# Legacy four-role layout still accepted (mapped onto fast/smart at load):
models:
  generator: anthropic/claude-sonnet-4-6
  evaluator: openai/gpt-5
  evaluator_fallback: anthropic/claude-opus-4-7   # same family; warning
```

## Iteration loop

When verdict is `reject`:

```python
for round in range(max_rounds):          # default 3
    artifact = generator.run(plan_item, previous_critique)
    verdict  = verifier.judge(plan_item, artifact, session)

    if verdict.verdict == "accept":
        commit_and_mark_done(plan_item); break
    if verdict.phase2_subjective.blocking is False:
        commit_with_advisory(plan_item, verdict); break
    previous_critique = verdict.failures
else:
    raise EvaluatorStalemate(plan_item, rounds=max_rounds, last_verdict=verdict)
```

Stalemate escalates: re-dispatch via Planner (maybe the plan item is wrong) or surface to user.

## Relationship to TDD gate

TDD gate ([block 05](05-hooks-and-tdd-gate.md)) runs **per tool call** inside the loop. Verifier runs at **end of session / plan item**. They are complementary:

- TDD gate catches: missing red proof, test-after habits, coverage regressions as they occur.
- Verifier catches: semantic issues the tests do not cover, scope drift, cross-channel sabotage.

The Stop hook runs both: TDD invariants first, then verifier.

## Safety monitor (separate concern)

[Block 12](12-safety-monitor.md) — distinct from the verifier. Runs continuously on the trace every N steps with a tiny cheap model. Flags covert / off-task / sabotage-shaped actions. Not gating per se; a flag pauses the session and surfaces for review.

## Advisory verdicts

Not every reject should block. A `blocking: false` verdict commits with notes:

- Style nits (naming, ordering).
- Missing docstring.
- Opportunity for refactor without fix-now urgency.

These land in `lyra retro` as follow-up items.

## Evaluator evidence hygiene

Evaluator-produced "evidence" must:

- Reference real `file:line` that exists in the diff (validated).
- Span ids referenced must exist in the trace.
- Snapshot deltas referenced must exist in the snapshot.

Hallucinated evidence is treated as verifier-bug; emits `evaluator.evidence_mismatch` span. Repeated hallucinations trigger evaluator model rotation.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Lenient evaluator | Objective Phase 1 catches most; rubric scores expose leniency pattern |
| Strict evaluator (spurious rejects) | `blocking: true` distinguished from advisory |
| Evaluator-generator collusion (same family) | Different-family default |
| Trace ↔ diff mismatch | Cross-channel gate fails the session |
| Snapshot evidence missing | Snapshot subsystem health-checked at session start |
| Stalemate loops | Max rounds + escalation |
| Hallucinated evidence | Evidence validator |
| Evaluator OOM on large diffs | Truncate diff to 200 KB with markers; acceptance tests are the ultimate source |

## Metrics emitted

- `verifier.verdicts.total` labeled by accept/reject/degraded
- `verifier.phase1.pass_rate`
- `verifier.phase2.rubric_scores` histogram per criterion
- `verifier.cross_channel.mismatches.total` labeled by type
- `verifier.stalemates.count`
- `verifier.evaluator.latency_ms` p50/p95
- `verifier.evidence_mismatch.count`

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_evaluator.py` | Verdict schema, rubric scoring, advisory vs blocking |
| Unit `test_cross_channel.py` | Trace/diff/snapshot comparator; mismatch detection |
| Unit `test_snapshot.py` | Each supported OS backend; fallback poller |
| Integration | Reject → iteration loop → eventual accept |
| Integration | Fabricated test run injected; verifier catches |
| Property | Phase 1 deterministic on frozen inputs |
| Red-team | Sabotage scenarios (test-disable, rm, commit hide) |

## Open questions

1. **LLM-as-judge bias.** Verifier is an LLM; it has biases. Rubric structure + cross-channel hardens but does not eliminate.
2. **Diff size growth.** Very large diffs truncated; risk of missing issues. Future: chunked evaluation.
3. **Environment snapshot scope.** DB state plugin API not yet specified — v2.
4. **Multi-round critique quality.** Early rounds' critiques may be noisy; late rounds may be exhausted. Research tunable.
5. **Evaluator drift over model updates.** Regression suite must re-run verdicts against stable fixtures nightly.
