# Phase 1: Current State Analysis

**Date**: 2026-05-17  
**Status**: Complete

## Lyra's Current Tool Architecture

### Tool Registry (`interactive/tools.py`)

Lyra uses a simple tool registry with `ToolSpec` entries:
- **name**: Unique identifier (e.g., "Read", "Write", "Bash")
- **risk**: low/medium/high (affects permission gating)
- **summary**: One-line description
- **origin**: builtin/mcp/user
- **planned**: Milestone tag

**Built-in tools**: Read, Glob, Grep, Edit, Write, Bash, TodoWrite, ExecuteCode, WebSearch

### Streaming Architecture (`interactive/stream.py`)

Lyra uses `MarkdownStreamState` for fence-aware streaming:
- Buffers incoming deltas
- Defers flushing content inside unclosed code fences
- Flushes safe boundaries (outside fences)
- Final flush when stream completes

**Key insight**: Streaming is currently focused on markdown rendering, not tool dispatch.

### Tool Execution Flow

Based on code analysis:
1. **Session loop** (`interactive/session.py`): Dispatches tools after LLM response
2. **Agent integration** (`cli/agent_integration.py`): Handles streaming with `async for chunk in stream`
3. **Tool dispatch**: Currently happens AFTER `message_stop` (sequential with streaming)

## Current Performance Characteristics

**Sequential phases**:
```
[LLM streaming: 4s] → [Tool execution: 2.5s] = 6.5s total
```

**Bottleneck**: Tools wait for stream to complete before starting

## Tool Idempotency Analysis

### Safe for Eager Dispatch (Read-only)
- **Read**: File reading (idempotent)
- **Glob**: File pattern matching (idempotent)
- **Grep**: Code search (idempotent)
- **WebSearch**: Web queries (idempotent)

### Unsafe for Eager Dispatch (Write operations)
- **Edit**: File modification (non-idempotent)
- **Write**: File creation/overwrite (non-idempotent)
- **Bash**: Shell commands (potentially non-idempotent)
- **ExecuteCode**: Code execution (potentially non-idempotent)

### Conditional (Requires argument inspection)
- **TodoWrite**: Task list updates (idempotent if append-only)

## Integration Points for Eager Tools

### 1. Stream Handler
**Location**: `cli/agent_integration.py`
- Current: `async for chunk in stream:`
- **Modification needed**: Add seal detection in chunk loop

### 2. Tool Dispatcher
**Location**: `interactive/session.py`
- Current: Dispatches after stream completes
- **Modification needed**: Add eager executor pool

### 3. Tool Registry
**Location**: `interactive/tools.py`
- Current: `ToolSpec` with name, risk, summary
- **Modification needed**: Add `idempotent: bool` field

## Recommendations

1. **Start with Anthropic provider**: Most common, well-documented streaming format
2. **Mark read-only tools as idempotent**: Read, Glob, Grep, WebSearch
3. **Keep write tools non-eager by default**: Edit, Write, Bash require explicit opt-in
4. **Add seal detection to agent_integration.py**: Monitor `tool_call_id` transitions
5. **Create executor pool in session.py**: Background worker pool for eager dispatch

## Next Steps

- Phase 2: Implement seal detection engine
- Phase 3: Implement eager executor pool
- Phase 4: Wire into Lyra's agent loop
