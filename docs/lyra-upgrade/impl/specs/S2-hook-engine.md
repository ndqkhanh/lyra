# S2: Hook Engine v2 (Interceptor Pipeline)

> Plan: §4.10 (10-hooks.md) | Depends on: S1 (Provider Abstraction)
> Book practices: Agentic Design Patterns Ch18 (Layered Guardrails), Principles of Building AI Agents Ch9 (Middleware Guardrails)

## Scope

Upgrade the existing hook engine (`src/hooks/`) into a production-grade interceptor pipeline that all agent operations pass through.

### Out of Scope
- Self-evolving hooks (Phase 2)
- MCP-based remote hooks (Phase 4)

## Key Design Decisions

1. **Synchronous hooks before async**: Pre-tool-use hooks run synchronously (can block), post-tool-use hooks run async (non-blocking)
2. **Chain of responsibility**: Hooks form a pipeline — each hook can pass, modify, or reject
3. **Priority ordering**: Security hooks (p0) always run first, then validation (p1), then observability (p2), then custom (p3+)
4. **HookResult is immutable**: Hooks return new state, never mutate

## Interfaces

```python
@dataclass(frozen=True)
class HookContext:
    hook_type: HookType  # PRE_TOOL_USE, POST_TOOL_USE, PRE_MODEL_CALL, POST_MODEL_CALL, SESSION_START, SESSION_END
    tool_name: str | None
    tool_input: dict | None
    model_request: CompletionRequest | None
    model_response: CompletionResponse | None
    session_id: str
    agent_id: str
    metadata: Mapping[str, Any]

@dataclass(frozen=True)
class HookResult:
    action: HookAction  # ALLOW, MODIFY, BLOCK, ASK_USER
    modified_context: HookContext | None  # Only if MODIFY
    reason: str
    hook_name: str
```

### HookEngine v2
```python
class HookEngine:
    def register(self, hook_type: HookType, handler: Callable, priority: int = 100): ...
    async def execute_pre_hooks(self, context: HookContext) -> HookResult: ...  # sequential, can block
    async def execute_post_hooks(self, context: HookContext) -> None: ...  # parallel, fire-and-forget
```

## Test Plan

1. `test_hook_engine.py` — Pipeline execution, priority ordering
2. `test_hook_blocking.py` — Pre-hook can block, post-hook cannot
3. `test_hook_modification.py` — MODIFY action produces new context
4. `test_hook_integration.py` — Hooks fire during agent loop
