# Hooks and TDD Gate -- How It Works

> 27+ hook events across 5 categories, fired by a lifecycle engine at deterministic seams in the agent loop. The TDD state machine (RED-GREEN-REFACTOR) is code-enforced at PRE_TOOL_USE. Hook abort on critical failure propagates without crashing the loop.
> **Block:** 06 | **Phase:** 2 (Quality & Planning) | **Depends on:** Agent Loop, Permission Bridge

## 27+ Hook Events Across 5 Categories

The lifecycle engine fires events at deterministic seams. Each event has a category, a type, and structured context:

| Category | Events | Firing Point |
|----------|--------|-------------|
| **Session** | `SESSION_START`, `SESSION_END`, `SESSION_INTERRUPT` | Session open/close |
| **Turn** | `TURN_START`, `TURN_COMPLETE`, `TURN_ERROR` | Each agent loop iteration |
| **Tool** | `PRE_TOOL_USE`, `POST_TOOL_USE`, `TOOL_ERROR` | Before/after each tool call |
| **LLM** | `PRE_LLM_CALL`, `POST_LLM_CALL`, `LLM_ERROR` | Before/after each LLM API call |
| **System** | `STOP`, `PLAN_CREATED`, `PLAN_APPROVED`, `MEMORY_SAVE`, `SUBAGENT_SPAWNED`, `SUBAGENT_COMPLETED`, `SKILL_ACTIVATED`, `VERIFICATION_PASS`, `VERIFICATION_FAIL`, `PERMISSION_BLOCK`, `SAFETY_FLAG` | Cross-cutting system events |

Each event carries a `LifecycleContext` with session_id, turn_index, timestamp, and category-specific payload (tool name, arguments, duration_ms, result, error).

## Hook Lifecycle Engine

The `LifecycleBus` implements a pub/sub pattern with typed events:

```python
bus = LifecycleBus()

@bus.subscribe(LifecycleEvent.TOOL_CALL)
def telemetry_collector(event):
    metrics.record_tool_call(event.tool_name, event.duration_ms)

# Event dispatch
bus.emit(LifecycleEvent(
    kind=LifecycleEventKind.PRE_TOOL_USE,
    session_id="sess_abc",
    tool_name="bash",
    payload={"command": "pytest tests/"},
))
```

**Hook ordering**: `pre_*` hooks fire in registration order (safety first, then TDD gate, then telemetry). `post_*` hooks fire in reverse order (telemetry first, TDD gate last). This guarantees safety has first look at inputs and last look at outputs.

**Exception isolation**: A hook exception does not crash the loop. The failing hook is removed from the active list, and the loop continues with remaining hooks. An error event is emitted for observability.

**Async with timeout**: Hooks can be async. A 5-second timeout prevents slow hooks from blocking the loop. Configurable per guard.

## TDD State Machine (RED-GREEN-REFACTOR)

The TDD gate enforces test-first discipline through a three-state machine:

```
       write failing test           write implementation
[RED] ──────────────────► [GREEN] ─────────────────────► [REFACTOR]
  ▲                            │                              │
  │                            │ (failing)                     │ (refactored)
  └────────────────────────────┘                              │
       back to RED                                              │
                                                                v
                                                           [COMPLETE]
```

**RED Proof Detection**: The `REDProofScanner` scans the last 50 actions in reverse for a Bash command matching a test file and showing failure (exit code != 0 or "FAILED" in output):

```python
class REDProofScanner:
    def check(self, transcript: list[Action]) -> bool:
        for action in reversed(transcript[-50:]):
            if self._is_test_command(action) and action.exit_code != 0:
                return True  # RED proof found
        return False
```

If no RED proof exists, the gate blocks writes to `src/**` by returning a block decision at the `PermissionStack` level. The LLM cannot bypass this through persuasion or prompt injection.

**TDD Guard at PRE_TOOL_USE**: The TDD gate registers as the highest-priority guard (priority 5) on `PRE_TOOL_USE`. It intercepts `Write` and `Edit` tools targeting `src/**` paths. Only the `Write` tool is relevant for the RED phase -- `Edit` is allowed during GREEN and REFACTOR.

## Hook Abort on Critical Failure

Hooks can return an abort decision that propagates without crashing the loop:

```python
def safety_hook(event) -> HookDecision:
    if event.kind == SafetyKind.SECRET_EXPOSURE:
        return HookDecision(
            action="abort",
            reason="Sensitive credential detected in tool output",
        )
    return HookDecision(action="continue")
```

An `abort` decision:
1. Emits an `AGENT_LOOP_INTERRUPT` HIR event
2. Persists current state for recovery
3. Returns control to the user with the abort reason

This is distinct from an exception: the loop remains healthy and can resume on the next turn. Only unrecoverable errors (out of memory, API unavailability after retries) trigger hard stop.

## Guard Pipeline Composition

The guard pipeline is a `PermissionStack` with priority-ordered named guards:

| Guard | Priority | Blocks |
|-------|----------|--------|
| `tdd_gate` | 5 | Source writes without RED proof |
| `destructive` | 10 | File destruction patterns |
| `secrets` | 20 | Credential exposure |
| `injection` | 30 | Prompt injection |

First block wins: `tdd_gate` fires first (priority 5), then destructive (10), secrets (20), injection (30). Lower-priority hooks can assume higher-priority checks have passed.

## Performance

| Guard | P50 | P95 |
|-------|-----|-----|
| destructive_pattern | 5ms | 12ms |
| secrets_scan | 5ms | 12ms |
| injection_guard | 3ms | 8ms |
| tdd_gate | 3ms | 8ms |
| Full 4-guard pipeline | 16ms | 40ms |

All guards are local heuristics -- zero LLM calls. Cost per tool call: ~0.0001 CPU-seconds.

## Related Documents

- **Concepts:** [Tools and Hooks](../concepts/02-tools-and-hooks.md), [Agent Loop](../concepts/01-agent-loop.md)
- **Architecture:** [Architecture Overview](../architecture/11-architecture-overview.md), [Safety and Security](../architecture/08-safety-security.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Permission Bridge](05-permission-bridge.md), [Verifier](10-verifier.md), [Safety Monitor](12-safety-monitor.md)

---

*References: TDD (Beck, 2003), Bloom Filters (Bloom, CACM 1970), Incremental Test Selection (Rothermel & Harrold, ACM TOSEM 1997)*
