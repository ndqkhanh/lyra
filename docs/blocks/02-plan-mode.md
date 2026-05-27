# Lyra Block 02 — Plan Mode

Plan Mode is Lyra's default entry point: every non-trivial task first becomes a human-readable plan artifact. This front-loads misunderstandings and creates the hand-off contract used by [verifier](11-verifier-cross-channel.md), [skill extractor](09-skill-engine-and-extractor.md), and multi-session continuity.

Upstream references: [Orion-Code Block 03](../../../orion-code/docs/blocks/03-plan-mode.md), [Plan-Mode deep-dive](../../../../docs/03-plan-mode.md).

## Responsibility

1. Accept a user task.
2. Run the Planner with read-only permissions on the repo. The Planner runs on the **smart slot** (default `deepseek-v4-pro` → `deepseek-reasoner`; legacy installs may pin `claude-opus-4.5` or `gpt-5`), resolved through `_resolve_model_for_role(session, "plan")`.
3. Produce a plan artifact (`plans/<session-id>.md`) containing: feature items, acceptance tests, expected files, forbidden files, estimated cost.
4. Hold execution until the plan is approved (interactive user, `--auto-approve`, or CI-signed approval).
5. Exit Plan Mode into the appropriate execution permission mode (subsequent in-loop chat turns drop back to the **fast slot**, default `deepseek-v4-flash` → `deepseek-chat`).

## The plan artifact (schema)

```markdown
---
session_id: 01HXK2N…
created_at: 2026-04-22T14:23:00Z
planner_model: deepseek-v4-pro                    # smart slot; resolves to deepseek-reasoner
estimated_cost_usd: 1.20
goal_hash: sha256:abcdef…
---

# Plan: Add dark mode toggle that persists across reloads

## Acceptance tests
- tests/settings/test_theme_toggle.py::test_toggle_visible
- tests/settings/test_theme_toggle.py::test_persists_across_reload
- e2e/test_theme_persistence.spec.ts::persists_in_localStorage

## Expected files
- src/settings/ThemeToggle.tsx
- src/settings/useTheme.ts
- src/settings/__tests__/useTheme.test.ts
- src/App.tsx (1 import, 1 mount)

## Forbidden files
- package.json      # no new deps needed
- .github/**

## Feature items
1. **(localize)** Identify where theme is currently read/written in codebase.
2. **(test_gen)** Write failing tests for ThemeToggle component + useTheme hook.
3. **(edit)** Implement useTheme hook reading/writing localStorage.
4. **(edit)** Implement ThemeToggle component wired to useTheme.
5. **(edit)** Mount ThemeToggle in App.tsx.
6. **(review)** Run full suite + a11y check + cross-browser snapshot.

## Open questions
- Which storage key to use? (default: `app.theme`)
- System-preference default when no stored value? (default: `prefers-color-scheme`)

## Notes
Referenced skills: atomic-skills/localize, atomic-skills/test-gen, atomic-skills/edit, atomic-skills/review
```

Schema is Markdown + YAML frontmatter so it is:

- Human-readable (user reviews by eye).
- Machine-parseable (harness parses for feature items / acceptance tests).
- Git-commitable (plan becomes history alongside code).
- Diffable on revision (if plan changes mid-session, diff is an event).

## Permission mode during Plan Mode

`PermissionMode.PLAN`:

- Reads allowed (Read / Grep / Glob / WebFetch on allowlisted domains).
- Writes denied (Edit / Write / Bash mutating).
- `AskUser` allowed for clarifying questions.
- Skill invocations allowed if skill itself is read-only.

Attempts to mutate during Plan Mode are **deny**, not `ask` — planner should not be the one proposing mutations without user approval of the whole plan.

## Planner prompt contract

The planner's system prompt:

```
You are the Planner. Your job is to produce a structured plan for the task.
You cannot mutate the repository; your tools are read-only.

Produce a plan artifact in the specified schema. Requirements:
- Feature items are small, each tied to an acceptance test.
- Every expected file must exist or be clearly new.
- Forbidden files list anything the plan must NOT touch.
- Acceptance tests should exist OR the plan must include a test_gen item.
- Estimate cost honestly based on complexity.
- Ask questions only when truly ambiguous; do not over-consult.

Output format: Markdown with YAML frontmatter, exactly matching schema.
```

## Plan complexity heuristic (auto-skip)

Plan Mode default-on except for tasks the heuristic marks `trivial`:

```python
def is_trivial(task: str, repo: Repo) -> bool:
    signals = []
    if len(task) < 80: signals.append("short_task")
    if re.search(r"\b(typo|fix comment|rename variable|add log)\b", task, re.I):
        signals.append("low_stakes_keywords")
    if "plan" in task.lower():
        return False
    if len(repo.recent_edits(hours=24)) > 20:
        signals.append("already_in_flow")
    return len(signals) >= 2
```

When `is_trivial` is true, the CLI prompts (`Skip plan? [Y/n]`) or obeys `--no-plan`. Heuristic is tunable, logged for audit.

## Approval surfaces

1. **Interactive (default).** CLI prints the plan artifact with color rendering; user responds `y` / `n` / `e` (edit) / `q` (question). `e` opens `$EDITOR`; edits are saved to the artifact.
2. **`--auto-approve`.** CI flag; logs approval by CI run id.
3. **`--auto-approve-if-same-as` `<hash>`.** Only approves if plan hash equals a user-presigned value; otherwise falls back to interactive or fails. Useful for replay-driven automation.
4. **Web viewer approval.** Plan renders in the web viewer; user clicks Approve; WebSocket notifies daemon.

Approval emits a `plan.approved` trace event, pinning the plan hash and approver.

## Plan revision

If the agent mid-execution concludes the plan is wrong, it calls a dedicated `ReplanTool` which:

1. Pauses execution.
2. Passes current state + diagnosed issue to the Planner.
3. Emits a revised plan artifact (`plans/<session-id>.rev-<n>.md`).
4. User re-approves (or auto-approve).
5. Execution resumes from the first changed feature item.

Replans are telemetered; frequent replans on the same session signal a poor initial plan.

## Interaction with multi-agent plugins

- `single-agent`: Planner runs before the loop; its plan is the loop's north star.
- `three-agent`: Planner runs, produces plan, Generator uses it, Evaluator verifies against it.
- `dag-teams`: Planner produces a DAG-shaped plan (nodes have `depends_on`); see [block 03](03-dag-teams.md).

## Failure modes

| Mode | Defense |
|---|---|
| Planner over-engineers (50 feature items for a trivial task) | Planner prompt enforces "minimum items to satisfy task"; user can trim in approval |
| Planner misses acceptance tests | Lint: if no `acceptance_tests` and no `test_gen` item, plan is rejected with a specific critique |
| User ignores plan | Acceptance tests still enforced by verifier; forbidden files still enforced by permission bridge |
| Plan drifts silently | Session end verifier checks `expected_files` touched + `forbidden_files` untouched + acceptance_tests all green |
| Planner hallucinates files | Plan linter verifies every listed file exists in the repo tree or is flagged as new |

## Metrics emitted

- `plan.generated_count`
- `plan.duration_ms`
- `plan.cost_usd`
- `plan.feature_items.count` (histogram)
- `plan.revisions.count` per session
- `plan.auto_skip.count` (heuristic triggered)
- `plan.approval_source` labeled (interactive / auto / presigned)

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_planner.py` | Plan schema validation, trivial heuristic |
| Integration | Plan → approval → first step of loop execution |
| Property | Plan hash is deterministic for same (task, repo state, model, temp=0) |
| Replay | Pre-recorded planner traces produce identical plan |

## Open questions

1. **Chunking large tasks.** Tasks spanning > 30 feature items become unmanageable. Split into sub-plans? Require user to narrow? v1 soft-caps at 30 with a warning.
2. **Plan library reuse.** Should frequent plans become skills? The skill extractor decides; a plan is a candidate seed.
3. **Plan templates per domain.** Backend refactor, new feature, bug fix — each has a distinct shape. v2 opt-in templates.
4. **Non-English plans.** Planner prompt is English; task may be other languages. Round-trip fidelity needs study.
