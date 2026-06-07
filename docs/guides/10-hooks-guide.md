# Hooks Guide — Extending Lyra with Lifecycle Events

> How to write, configure, and debug hooks. Hooks are the extensibility spine: permissions, verification, logging, and custom behavior all plug in through the hook system.

## Quickstart

```python
from lyra.hooks import Hook, HookType, HookEngine

engine = HookEngine()

hook = Hook(
    hook_id="my-pre-tool-check",
    hook_type=HookType.PRE_TOOL_USE,
    fn=lambda ctx: print(f"About to run: {ctx.tool_name}"),
)
engine.register(hook)
```

## Lifecycle Events

| Event | When | Use For |
|-------|------|---------|
| `PRE_TOOL_USE` | Before any tool call | Permission checks, input validation |
| `POST_TOOL_USE` | After tool completes | Logging, cost tracking, verification |
| `POST_TOOL_USE_FAILURE` | Tool call fails | Error recovery, alerting |
| `SESSION_START` | Session begins | Setup, env validation |
| `SESSION_END` | Session ends | Cleanup, consolidation |
| `USER_PROMPT_SUBMIT` | User sends message | Input filtering, pre-processing |
| `STOP` | Agent stopping | Final checks, audit log |

## Exit Code Protocol

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success — continue |
| 2 | Blocking error — stop the agent |
| Other | Non-blocking error — log and continue |

## → Dive Deeper

- [Hooks Plan](../lyra-upgrade/plans/10-hooks.md)
- [Hooks Architecture](../architecture/11-architecture-overview.md)
