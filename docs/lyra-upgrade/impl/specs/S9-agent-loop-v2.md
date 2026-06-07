# S9: Agent Loop v2 (Real Execute, Not Simulated)

> Plan: §4.1 (01-ui-ux.md) | Depends on: S1, S2, S3, S8

## Scope
Replace asyncio.sleep() simulated agent execution with real LLM calls, tool use, memory operations.

## Key Design
1. **Real execute cycle**: think → act → observe → reflect (not sleep)
2. **Streaming output**: real-time token streaming to TUI
3. **Tool integration**: dispatch to ToolRegistry, validate inputs, capture outputs
4. **Memory integration**: read STM before each step, write after
5. **Hook integration**: pre/post hooks fire at each cycle boundary
6. **Error recovery**: retry with backoff, escalate on repeated failure
