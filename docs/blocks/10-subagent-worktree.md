# Lyra Block 10 — Subagent Orchestrator (with git worktree isolation)

Subagents are scoped agent instances that operate in isolated git worktrees. They let Lyra parallelize work across files/modules while keeping the parent's coherence invariant (no stomped edits, explicit merge points).

Upstream references: [Orion-Code Block 02](../../../orion-code/docs/blocks/02-subagent-orchestrator.md), [Subagent Delegation dive](../../../../docs/02-subagent-delegation.md), [`docs/46-gpt-5-harness-study.md`](../../../../docs/46-gpt-5-harness-study.md) for subagent patterns in production.

## Responsibility

1. Spawn a subagent with declared purpose, scope, and budget.
2. Allocate a git worktree on a session branch for the subagent.
3. Run the subagent's loop with narrowed tool allowlist and shared SOUL + plan context.
4. Collect a structured observation (not raw trace) back for the parent.
5. Merge the subagent's commit back into the session branch with conflict handling.
6. Clean up the worktree.

## When to use a subagent

- **Large observation reduction**: the work would produce a big observation (e.g., "read 40 files") that would blow the parent's context. The subagent keeps the details in its own context and returns a summary.
- **Parallel DAG nodes** ([block 03](03-dag-teams.md)).
- **Experimental branches**: try two approaches, pick the best (evaluator-driven).
- **Long-running sub-task** with its own budget needing separate cost attribution.

## When *not* to use

- The work is 3-5 steps (overhead > benefit).
- The result is needed inline; subagent is an async barrier.
- The scope overlaps with concurrent edits (risk of merge conflict).

## API

```python
@tool(name="Spawn", writes=False, risk="medium")
def spawn_subagent(
    purpose: str,
    scope: list[str],                  # file patterns / globs
    budgets: dict | None = None,       # max_steps, max_cost_usd
    allowed_tools: list[str] | None = None,
    return_shape: Literal["observation","artifact","raw_trace"] = "observation",
) -> str: ...
```

Parent calls `Spawn`. Orchestrator creates `Subagent`, runs it, returns a serialized `SubagentResult`.

Python SDK:

```python
sub = Subagent(
    parent=session,
    purpose="Reproduce issue #234 in a minimal test case",
    scope=["tests/**", "src/auth/**"],
    worktree_branch=f"sub-repro-234",
    budgets=Budgets(max_steps=20, max_cost_usd=1.00),
    allowed_tools=["Read","Grep","Glob","Edit","Write","Bash"],
)
result = sub.run()
```

## Worktree allocation

```
git worktree add -b <session-id>-sub-<n> \
    .lyra/worktrees/<session-id>/<n> \
    <session-branch>
```

Each worktree is a full working tree (shared `.git/` via git's native worktree support). Shallow clone is considered but v1 uses full worktrees because code-indexing tools expect native structure.

After run, worktree is removed:

```
git worktree remove .lyra/worktrees/<session-id>/<n>
git branch -D <session-id>-sub-<n>     # after successful merge
```

## Subagent lifecycle

As of **v2.7.1**, every `/spawn` opens the parent session's **smart slot** before constructing the subagent's `AgentLoop`. The CLI's `_loop_factory` (in `lyra_cli.interactive.session`) wraps `build_llm` with `_apply_role_model(session, "smart")`, which:

1. Resolves `session.smart_model` (default `deepseek-v4-pro`) through the alias registry → `deepseek-reasoner`.
2. Stamps `HARNESS_LLM_MODEL` and the provider-specific override (`DEEPSEEK_MODEL`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`).
3. Builds (or mutates the cached) provider so the subagent's first turn lands on the smart model.

Subagent budgets, trust banners, scope globs, and worktree allocation are unchanged — only the model that powers the inside-loop generator is upgraded. This mirrors Claude Code's "Sonnet for reasoning" pattern. The parent's own chat turns, meanwhile, drop back to the **fast slot** (`deepseek-v4-flash` → `deepseek-chat`) the moment the subagent returns.

```python
class SubagentLifecycle:
    def prepare(self):
        self.worktree = self._allocate_worktree()
        self.fs_sandbox = FSSandbox(root=self.worktree, scope_globs=self.scope)
        self.narrowed_tools = ToolRegistry.narrowed(self.allowed_tools, self.fs_sandbox)

    def run(self) -> SubagentResult:
        context_seed = self._seed_context()
        # v2.7.1: opens the smart slot before build_llm.
        # Equivalent to: _apply_role_model(parent_session, role="smart").
        self.llm = self._loop_factory_smart()
        loop = AgentLoop(
            llm=self.llm, tools=self.narrowed_tools,
            hooks=self.hooks, permission_mode=self.permission_mode,
            system_prompt=self._subagent_system_prompt(),
        )
        try:
            out = loop.run(task=self.purpose, initial_messages=context_seed)
        finally:
            self._emit_metrics()

        observation = self._summarize(out)
        return SubagentResult(
            status=out.stop_reason,
            summary=observation,
            commit=self._commit_changes(),
            cost_usd=loop.cost_usd,
            trace_hash=self._offload_trace(),
        )

    def cleanup(self):
        self._remove_worktree()
```

## Context seed

Subagents inherit a narrowed context to stay coherent with the parent:

- SOUL.md (full).
- Plan summary (first page; current feature item highlighted).
- Subagent purpose (verbatim).
- Scope globs (explicit).

Subagents do not inherit the parent's transcript by default — this would defeat the context-reduction benefit. If the subagent needs specific context, the parent can pass artifact hashes as references; subagent fetches via `View(hash)`.

## Return shape

`return_shape="observation"` (default): structured JSON observation to parent.

```json
{
  "subagent_id": "sub-4",
  "status": "success",
  "summary": "Reproduced issue #234 by calling authenticate() with token lacking 'sub' claim.",
  "files_touched": ["tests/auth/test_authenticate_issue_234.py"],
  "commit_hash": "ff4a2c...",
  "test_delta": {"added": 1, "passing_new": 0, "regressions": 0},
  "cost_usd": 0.43,
  "trace_hash": "sha256:..."
}
```

`return_shape="artifact"` returns a reference for the parent to `View`. `return_shape="raw_trace"` pipes the full trace (unusual; mostly for debug).

## Filesystem sandbox

`FSSandbox` wraps tool layer so that `Edit`/`Write`/`Bash` can only write paths within the worktree. Reads outside the worktree are allowed but logged. This is an additional defense layer beyond PermissionBridge scope restrictions.

## Merge strategy

When subagent completes:

1. Parent orchestrator fetches the commit on the subagent's branch.
2. Attempts fast-forward merge into session branch.
3. If not fast-forwardable:
    - Attempt 3-way merge.
    - On conflict: invoke conflict-resolver (single-agent loop with a scoped purpose "resolve this merge").
    - If conflict-resolver fails twice: raise `MergeConflict` → session pauses at `human_review`.
4. On success: record merge event, delete subagent branch, delete worktree.

Conflict-resolver is opt-out: some users prefer every conflict surfaced to them. Config flag.

## Parallel subagents

The DAG scheduler ([block 03](03-dag-teams.md)) can spawn multiple subagents concurrently. Orchestrator's concurrency limits:

- Default: `min(4, cpu_count)` simultaneous subagents.
- Disk capacity preflight: refuses to spawn when disk usage > 90%.
- Cost pacing: scaling concurrency down if cumulative cost approaches `max_cost_usd`.

## Subagent system prompt

```
You are a subagent. Your purpose: <purpose>.
Your scope is limited to: <scope globs>.
Do not edit files outside your scope.
Do not spawn subagents yourself (depth-limit).
Return a structured observation summarizing your work.
Honor the parent's SOUL and the plan item you were dispatched to.
```

Recursion depth is capped at 2 (subagent can invoke skills but not further subagents).

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Subagent writes outside scope | FSSandbox rejects + logs; test + lint catches at design time |
| Subagent returns raw trace flooding parent context | `return_shape="observation"` default; observation summarizer truncates |
| Merge conflict on session branch | Conflict-resolver loop → human review escalation |
| Subagent runs away on cost | Per-subagent budget cap; parent still controls aggregate |
| Subagent recurses (spawns subagent) | Depth limit = 2; violations rejected by Spawn tool |
| Worktree leak (cleanup failure) | Startup reconciler removes stale worktrees from `.lyra/worktrees/` |
| Same file edited by parent and subagent concurrently | Scope intersection check at dispatch; rejected if conflict |
| Subagent contradicts plan | Subagent system prompt pins plan item; verifier catches |

## Metrics emitted

- `subagent.spawn_count`, labeled by harness plugin
- `subagent.duration_ms` (histogram)
- `subagent.cost_usd`
- `subagent.outcome` labeled by success/partial/fail/blocked
- `subagent.merge_conflicts.count`
- `subagent.recursion_attempts.count`
- `subagent.concurrency` gauge

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_orchestrator.py` | Worktree alloc/cleanup, scope enforcement |
| Unit `test_fssandbox.py` | Write-outside-scope denial; read-allowed logging |
| Integration | Parent spawns subagent; merges result; verifies trace |
| Integration | Two parallel subagents on non-overlapping scopes complete and merge |
| Integration | Two parallel subagents with overlapping scope rejected at dispatch |
| Property | Cleanup invariant: no worktree or branch left after session end |

## Open questions

1. **Shallow worktrees.** Faster but some tools (indexers, LSPs) want full history. v2 opt-in shallow.
2. **Remote-runner subagents.** Burst subagent work to Modal / Fly. Latency vs parallelism trade; v2.
3. **Cross-subagent communication.** Currently none; each subagent is isolated. For some tasks, shared scratchpad would help. v2 with safety-verified sharing.
4. **Cost allocation.** Per-feature-item cost attribution with subagents: currently summed to parent plan item; finer-grained attribution requires feature tags on subagent dispatch.
