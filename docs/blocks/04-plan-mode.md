# Plan Mode -- How It Works

> Task planning that converts user requests into structured, approvable execution plans. Uses Opus extended thinking for generation, heuristic-based triviality detection, approval gates, plan-as-artifact persistence, step-level verification, and skip classification.
> **Block:** 04 | **Phase:** 2 (Quality & Planning) | **Depends on:** Agent Loop, Permission Bridge

## Plan Generation (Opus Extended Thinking)

When a non-trivial task arrives, Plan Mode switches to `LyraMode.PLAN` (read-only tools only) and spawns a planner agent using a capable model with extended thinking enabled (Opus-class, up to 31,999 thinking tokens).

The planner uses a structured prompt that produces a `PlanArtifact`:

```yaml
---
session_id: sess_abc123
title: "Add cursor-based pagination to /users endpoint"
created_at: 2026-06-01T10:00:00Z
---

## Acceptance Tests
1. GET /users?cursor=xyz returns next_page and data
2. Missing cursor returns first page
3. Empty result set returns null cursor

## Expected Files
- src/routes/users.py (modify)
- tests/test_users.py (create)

## Forbidden Files
- src/db/migrations/

## Feature Items
1. Add cursor param to /users handler
2. Implement cursor decoding/encoding
3. Add SQL ORDER BY + LIMIT + cursor WHERE clause

## Open Questions
- Should cursor be opaque or expose sort key?
```

The driving model uses extended thinking to explore the codebase, identify impact areas, and generate acceptance criteria. Read-only tools (`Read`, `Grep`, `Glob`, `LSP`, `WebFetch`) ensure no side effects during planning.

## Triviality Detection (Skip Classification)

Before planning, a heuristic engine scores task complexity in under 10ms:

| Signal | Condition | Weight |
|--------|-----------|--------|
| Length | Task string < 80 chars | +0.3 |
| Trivial keywords | "typo", "fix comment", "bump", "rename" | +0.4 |
| Single file mention | Exactly one filename | +0.2 |
| Recent edit | File modified in last 5 min | +0.1 |
| Complexity keyword | "refactor", "migrate", "redesign" | Forces 0.0 |

Score >= 0.7 = **trivial** (skip planning, route directly to Agent Loop). The ~15% false rate is acceptable: false negatives (planning a trivial task) cost only seconds of overhead; false positives are bounded by the length signal.

**Skip classification** also applies mid-execution: if a sub-task is marked trivial by its heuristic score, it bypasses the planning phase for that step.

## Approval Gate

Three approval paths with different trust models:

| Path | Trust Model | Mechanism | Use Case |
|------|-------------|-----------|----------|
| Interactive | Human-in-loop | User types `/approve` | Local development |
| Auto-approve | CI pipeline trust | CI run ID checked against known runners | Automated PRs |
| CI-signed | Cryptographic | HMAC-SHA256 JWT with plan hash + expiry | Production |

The CI-signed path includes the plan hash in the JWT, preventing plan substitution between approval and execution. The `PermissionBridge` verifies the signature before allowing the mode transition from PLAN to execution.

## Plan-as-Artifact Persistence

Plans are saved as Markdown files with YAML frontmatter in `.lyra/plans/<session-id>.md`. This format is human-readable, git-friendly, diffable in code review, and editable in any text editor.

```
.lyra/plans/
├── sess_abc123.md
├── sess_abc123.rev-1.md      (revision 1)
├── sess_abc123.rev-2.md      (revision 2)
└── sess_def456.md
```

Monotonic `.rev-N` naming establishes an automatic audit trail. Revisions are capped at 5 per session (hard limit).

## Step-Level Verification

After each step in the plan, the Verifier (Block 10) runs Phase 1 checks (deterministic: tests, file existence, forbidden files, coverage delta). Only if Phase 1 passes does the loop proceed to the next step. Step-level verification creates a tight feedback loop: a step that fails verification is immediately flagged, and the agent can correct before accumulating errors.

```python
for step in plan.steps:
    result = agent.execute(step)
    verdict = verifier.verify_step(result, step)
    if not verdict.passed:
        agent.replan(step, verdict.feedback)
```

## PlanCompressor

When the plan enters the execution context, it is compressed to ~300 tokens:

- Top 5 acceptance tests (by priority)
- Top 10 expected files (alphabetical)
- All forbidden files
- Feature item count
- Step count

Open questions and detailed descriptions are omitted. If no acceptance tests exist, the compressor falls back to the first 300 tokens of the feature items section.

## Performance

| Metric | P50 | Notes |
|--------|-----|-------|
| Heuristic evaluation | <1ms | Zero API cost |
| Plan generation (non-trivial) | 8s | Opus extended thinking |
| Approval (interactive) | 12s | User response time |
| Plan compression | <1ms | Truncation only |
| Cost savings vs smart-only | 73% | Two-tier model routing |

## Related Documents

- **Concepts:** [Plan Mode](../concepts/05-plan-mode.md), [Two-Tier Routing](../concepts/10-two-tier-routing.md), [Reasoning Bank](../concepts/15-reasoning-bank.md)
- **Architecture:** [Architecture Overview](../architecture/11-architecture-overview.md), [Gap Analysis](../architecture/13-gap-analysis.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Permission Bridge](05-permission-bridge.md), [Hooks and TDD Gate](06-hooks-tdd.md), [DAG Teams](07-dag-teams.md), [Verifier](10-verifier.md)

---

*References: ReAct (arXiv:2210.03629), Tree-of-Thought (arXiv:2305.10601), Plan-and-Solve (arXiv:2305.04091), AdaPlanner (arXiv:2305.16658)*
