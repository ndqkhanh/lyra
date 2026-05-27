# Lyra Block 03 — DAG Teams (SemaClaw two-phase orchestration)

A harness plugin that ports SemaClaw's DAG Teams pattern into Lyra's coding domain. Used when a task decomposes into parallelizable node-local sub-tasks with explicit dependencies. Opt-in via `--harness dag-teams` or auto-selected when the Planner produces a plan with ≥ 3 parallel-friendly branches.

Paper reference: SemaClaw, arXiv:2604.11548. Workspace deep-dive: [`docs/54-semaclaw-general-purpose-agent.md`](../../../../docs/54-semaclaw-general-purpose-agent.md).

## When to use DAG Teams

Coding tasks that fit:

- Multi-file refactors where each file's edits are independent.
- Polyglot features (e.g. add a field → update DB migration + backend model + frontend form) with clear dependency ordering.
- Bulk operations (run a codemod across 30 files → merge results).
- Research-plus-synthesis tasks where an explore phase feeds many concrete edits.

Does not fit:

- Linear single-file edits (overhead > benefit).
- Tasks where cross-file invariants require constant negotiation (single-agent handles better).
- High-churn repos where worktrees conflict more than they parallelize.

## Two-phase contract (SemaClaw core)

### Phase 1 — Dynamic decomposition (LLM Planner)

Planner produces a **task DAG**, not a linear list. Nodes have:

```yaml
nodes:
  - id: n1
    kind: localize
    description: Find all call sites of auth.authenticate.
    scope_files: [src/**]
    depends_on: []
    estimated_cost_usd: 0.08
  - id: n2
    kind: edit
    description: Rewrite auth.authenticate to use new JWT library.
    scope_files: [src/auth/authenticate.ts]
    depends_on: [n1]
    estimated_cost_usd: 0.40
  - id: n3
    kind: edit
    description: Update call sites returned by n1.
    scope_files: [src/**]
    depends_on: [n1, n2]
    estimated_cost_usd: 0.60
  - id: n4
    kind: test_gen
    description: Add tests for JWT failure modes.
    scope_files: [tests/auth/**]
    depends_on: [n2]
    estimated_cost_usd: 0.20
  - id: n5
    kind: review
    description: Full suite + security review of auth changes.
    scope_files: []
    depends_on: [n3, n4]
    estimated_cost_usd: 0.30
edges_are_explicit: true
```

### Phase 2 — Deterministic scheduling (DAG scheduler)

A non-LLM scheduler partitions the DAG into waves and dispatches independent nodes in parallel, each to a subagent in its own [git worktree](10-subagent-worktree.md).

```
wave 1: [n1]
wave 2: [n2]            (n1 complete)
wave 3: [n3, n4]        (parallel; both depend only on n2 / n1)
wave 4: [n5]            (final review after n3 and n4)
```

Each node runs the single-agent loop scoped to its files, budget, and allowed tools.

## DAG validation

Before scheduling, the DAG is validated:

| Check | Fail action |
|---|---|
| No cycles | Reject plan; ask Planner to revise |
| All `depends_on` references resolve | Reject |
| Union of `scope_files` covers all `plan.expected_files` | Warn (maybe intentional — planner sketched and scheduler fills in) |
| No two nodes with write scope intersect (same-wave) | Reject |
| All node budgets sum within session cost cap | Warn; may scale budgets down proportionally |
| DAG depth ≤ 10 | Warn; deep chains erode parallelism |
| Fan-out at any layer ≤ 8 | Warn (disk cost); user can override |

Invalid DAG → replan loop; counted in metrics.

## Subagent dispatch

For each scheduled node:

```python
sub = Subagent(
    parent_session=session,
    purpose=node.description,
    scope_files=node.scope_files,
    worktree_branch=f"dag-{session.id}-{node.id}",
    budgets=Budgets(
        max_steps=30, max_cost_usd=node.estimated_cost_usd * 1.5,
    ),
    allowed_tools=_tools_for_kind(node.kind),
    plan=single_node_plan(node),
    return_shape="observation",   # not raw trace
)
sub.run()
```

Subagent returns a structured observation:

```json
{
  "node_id": "n2",
  "status": "success",
  "commit_hash": "abc123...",
  "files_touched": ["src/auth/authenticate.ts"],
  "test_delta": {"added": 0, "passing_new": 0, "regressions": 0},
  "summary": "Migrated authenticate to JWT using jose library.",
  "artifacts": ["<hash>"],
  "evidence_refs": ["trace:span:..."],
  "cost_usd": 0.38
}
```

## Merge strategy

After all nodes in a wave complete:

1. Fetch each worktree's commit hash.
2. Attempt fast-forward merge onto session branch in declared node order.
3. On conflict:
    - Attempt 3-way auto-merge.
    - If that fails, emit `dag.merge_conflict` span and pause the wave.
    - Surface the conflict to the user via CLI prompt + web viewer.
    - User resolves manually, then scheduler resumes.
4. Success: update plan status, proceed to next wave.

Merge conflicts are the most common failure in v1 DAG Teams; scheduler tries to minimize them by validating scope intersections before dispatch.

## PermissionBridge parking in DAG Teams

From SemaClaw: a node requiring higher-than-session permission is **parked**. Downstream nodes that do **not** depend on the parked node proceed. User approves the parked node later; scheduler resumes its wave.

Example: `n3` wants to edit a forbidden file — parked. `n4` doesn't depend on `n3`; it proceeds. User reviews `n3`, denies it, plan marks `n3` rejected; wave 4 (`n5`) also rejects because it depends on `n3`.

## Failure semantics (fault-local)

SemaClaw's claim: DAG fault locality — a single node failure does not poison the whole DAG.

Lyra implements:

- **Retry policy** per node (default 2 retries with different random seed / nudge).
- **Soft-fail cascading**: if a node fails and downstream nodes have a fallback path marked (`on_fail: <alternate-node-id>`), scheduler dispatches the alternate.
- **Hard-fail cascading**: if no alternate, downstream nodes are marked `blocked_upstream` rather than attempted.
- **Final status**: session status reflects the pattern (complete / partial / failed).

## Diff vs three-agent plugin

| Aspect | `three-agent` | `dag-teams` |
|---|---|---|
| Parallelism | None (linear phases) | Within-wave |
| Overhead | 1.6× baseline | 2-3× baseline |
| Best for | High-assurance linear tasks | Decomposable wide tasks |
| User interaction | Approve plan once | Approve plan + resolve parked/conflict nodes |
| Failure containment | Evaluator rejects → retry Generator | Per-node fault isolation |

Plugin selection auto-routing heuristic:

```python
def choose_plugin(plan: Plan) -> str:
    if plan.max_parallel_width() >= 3 and plan.has_explicit_edges():
        return "dag-teams"
    if len(plan.feature_items) >= 5 or plan.has_refactor_kind():
        return "three-agent"
    return "single-agent"
```

## Integration with verifier

After all waves complete:

1. Each node's subagent has already run its internal verifier.
2. Parent session runs a **DAG-level verifier**: acceptance tests on the merged session branch, forbidden files check across all waves, and cross-channel consistency (each node's traces + diffs + env snapshots agree with parent's session record).
3. On all-pass, session marks complete; on any fail, session status `human_review` with detailed DAG-level report.

## Failure modes (DAG-specific)

| Mode | Defense |
|---|---|
| Planner emits DAG that is actually sequential (no parallelism) | Scheduler detects width=1 DAG; downgrades to single-agent with warning |
| DAG explosion (100+ nodes) | Soft cap on node count; refuse to dispatch beyond; recommend replan |
| Coordination drift across subagents (each makes an assumption that clashes) | Node scope pinned to specific files; parent provides shared plan artifact as context |
| Resource contention (too many worktrees) | Scheduler caps concurrent waves by system resources (CPU / disk) |
| Subagent leaks scope | `allowed_tools` narrows to node's declared needs; PermissionBridge blocks out-of-scope writes |
| Merge thrash | If same file touched by multiple nodes in different waves, ordering matters; Planner is prompted to flatten such structure |

## Metrics emitted

- `dag.node_count`, `dag.depth`, `dag.max_width`
- `dag.dispatch_wave_duration_ms` (histogram)
- `dag.merge_conflicts.count`
- `dag.parked_nodes.count`
- `dag.node_failures.count` labeled by retry-exhausted / soft-failover / blocked-upstream
- `dag.replans.count`
- `dag.subagent.cost_usd.total`

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_dag_teams.py` | DAG validator (cycles, missing deps, invalid scopes) |
| Unit `test_scheduler.py` | Wave partitioning, parking, fault-local failure |
| Integration | Multi-file refactor fixture; verify parallel commits + merge |
| Property | Schedule preserves partial-order invariant |
| E2E | Full DAG on a sample repo; measure wall-clock vs single-agent baseline |

## Open questions

1. **Cost of coordination.** When parallelism is shallow, DAG overhead dominates. Better heuristic needed.
2. **Dynamic DAG expansion.** Nodes may spawn children (localize uncovers new files). v1: expansion = replan; v2 may allow inline expansion under budget.
3. **Long-distance dependencies.** Wide, shallow DAGs work well; deep tall DAGs (sequential) lose parallelism. Planner must be coached to favor width when possible.
4. **Cross-wave observation sharing.** Currently each wave starts fresh; some knowledge from wave N-1 might accelerate wave N. v2: structured handoff observations.

## References

- SemaClaw paper arXiv:2604.11548
- [`docs/54-semaclaw-general-purpose-agent.md`](../../../../docs/54-semaclaw-general-purpose-agent.md)
- [`docs/23-multi-agent-systems.md`](../../../../docs/23-multi-agent-systems.md)
- [`docs/50-dont-build-multi-agents.md`](../../../../docs/50-dont-build-multi-agents.md) — rationale for *not* defaulting to multi-agent
