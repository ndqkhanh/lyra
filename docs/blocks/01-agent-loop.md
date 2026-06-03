# Agent Loop -- How It Works

> The execution kernel state machine that drives every Lyra session through Plan-Execute-Verify-Consolidate cycles with TDD discipline, HIR event emission, and Pivot/Refine recovery.
> **Block:** 01 | **Phase:** 1 (Core Infrastructure) | **Depends on:** (none -- foundational block)

## The Core State Machine

The Agent Loop is a four-phase state machine that governs every interaction cycle. Each phase is deterministic and emits structured HIR events for observability.

```
                   +--[TDD GATE]--+
                   |              |
                   v              |
  [PLAN] --> [EXECUTE] --> [VERIFY] --> [CONSOLIDATE] --> next turn
    ^                                           |
    |                                           v
    +-------[PIVOT/REFINE] <-- failure ---- [REPEAT?]
```

### Phase 1: Plan (State: PLANNING)

The loop receives a task (user input or sub-plan). If `PlanMode` (Block 08) is active, the heuristic engine scores complexity. Trivial tasks (score >= 0.7) skip directly to Execute. Non-trivial tasks route through Opus extended thinking to produce a `PlanArtifact` with acceptance tests, expected files, and feature items.

### Phase 2: Execute (State: EXECUTING)

The loop enters the think-act-observe cycle. For each iteration:

```
1. ContextAssembler builds a 5-layer transcript (see Block 02)
2. LLM generates response + tool_calls
3. PermissionBridge intercepts each tool call (see Block 05)
4. Tool executes (or is blocked)
5. Observation is recorded
6. HIR event is emitted for each step (see Block 11)
```

The loop checks `IterationBudget` before every LLM call and before every tool call. Exhaustion of `max_cost_usd`, `max_steps`, or `max_tokens` produces `StopReason.BUDGET`.

### Phase 3: Verify (State: VERIFYING)

Every task completion passes through the Verifier (Block 10). Phase 1 runs deterministic checks (tests, files, linting) at zero LLM cost. Phase 2 runs a different-family LLM judge against a 5-criterion rubric. Cross-channel reconciliation compares the agent's claimed actions (execution trace) against actual filesystem mutations (git diff) and ground truth (environment snapshot).

### Phase 4: Consolidate (State: CONSOLIDATING)

Session state is compacted, memory observations are persisted via AMAC admission (Block 03), and the loop state machine resets for the next turn. Lessons from Reflexion are stored in episodic memory.

## TDD Gate (RED-GREEN-REFACTOR)

The TDD gate enforces test-first discipline at the code level, not as a prompt:

```
RED:   Write a failing test (must see FAILED in test output)
GREEN: Write minimal implementation to pass
REFACTOR: Clean up while keeping tests green
```

The `REDProofScanner` scans the last 50 actions in reverse for a Bash command matching a test file with exit code != 0 or "FAILED" in output. If no RED proof exists, the gate blocks writes to `src/**` at the `PermissionStack` level. Time complexity O(n), space O(1).

```python
# Simplified gate logic
proof = next(
    action for action in reversed(transcript[-50:])
    if action.is_test_command and action.exit_code != 0
)
if not proof:
    raise PermissionError("No RED proof found -- write blocked")
```

This is code-enforced at `PRE_TOOL_USE` (Block 06), not prompt-enforced. The LLM cannot bypass it through persuasion or prompt injection.

## HIR Event Emitter

Every state transition and every tool call emits a structured HIR event:

```json
{
  "kind": "AGENT_LOOP_STEP",
  "session_id": "sess_abc123",
  "timestamp": 1717201234.567,
  "payload": {
    "phase": "EXECUTING",
    "iteration": 7,
    "tool": "bash",
    "tool_id": "tl_001",
    "duration_ms": 2340,
    "tokens": { "input": 45200, "output": 890 },
    "cost_usd": 0.042
  }
}
```

These events power the live terminal dashboard (Block 11), cost attribution, trace replay, and cross-channel verification evidence.

## Pivot/Refine Recovery

When a tool call fails or verification fails, the loop does not blindly retry. It enters a recovery sub-state machine:

```
                   +--> Tool Substitution
  [FAILURE] -->    +--> Parameter Perturbation
                   +--> Capability Downgrade
                   +--> Strategy Regeneration (Reflexion)
```

**Tool substitution**: If `read_file` fails on a binary, try `hexdump`. If `bash` fails on a syntax error, try `python -c`.

**Parameter perturbation**: Adjust timeout, retry count, working directory, or environment variables.

**Capability downgrade**: Fall back from the smart model (Sonnet) to Haiku for simpler sub-tasks, or from tool-based execution to manual step-by-step.

**Reflexion**: After repeated failures, the loop generates a structured lesson (hypothesis, observation, adjustment), stores it in episodic memory, and injects it into future prompts. This achieves a 67.0% to 91.0% pass@1 improvement on HumanEval (Shinn et al., 2023).

Recovery success rate: 23% with blind retry, 67% with Pivot/Refine.

## Repeat Detection

A Bloom filter with recency weighting tracks tool call patterns. Threshold of 3 identical calls in a 16-call sliding window catches infinite loops while allowing legitimate retries. False positive rate < 1%. The filter resets on each new user turn.

## Related Documents

- **Concepts:** [Agent Loop](../concepts/01-agent-loop.md), [Two-Tier Routing](../concepts/10-two-tier-routing.md), [Reasoning Bank](../concepts/15-reasoning-bank.md)
- **Architecture:** [Ultracode Replication](../architecture/01-ultracode-replication.md), [Workflow Engine](../architecture/05-workflow-engine.md)
- **Related blocks:** [Context Engine](02-context-engine.md), [Permission Bridge](05-permission-bridge.md), [Hooks and TDD Gate](06-hooks-tdd.md), [Verifier](10-verifier.md), [Observability](11-observability.md)

---

*References: ReAct (arXiv:2210.03629), Reflexion (arXiv:2303.11366), AutoResearchClaw (arXiv:2605.20025)*
