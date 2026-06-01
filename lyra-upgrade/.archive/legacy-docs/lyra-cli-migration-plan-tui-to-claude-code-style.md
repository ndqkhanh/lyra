---
title: "Lyra CLI Migration Plan: TUI to Claude Code Style"
tags: ["lyra", "cli", "migration", "architecture", "openagentd", "claude-code"]
created: 2026-05-15T03:57:13.296Z
updated: 2026-05-15T03:57:13.296Z
sources: []
links: []
category: architecture
confidence: medium
schemaVersion: 1
---

# Lyra CLI Migration Plan: TUI to Claude Code Style

# Lyra CLI Migration Plan: TUI to Claude Code Style

**Date:** 2026-05-15  
**Status:** Planning  
**Goal:** Migrate Lyra from Textual TUI to Claude Code-style streaming CLI with OpenAgentd multi-agent patterns

---

## Executive Summary

Migrate Lyra from the current Textual-based TUI (`tui_v2/`) to a **Claude Code-style streaming CLI** that incorporates **OpenAgentd's multi-agent orchestration patterns**. The new CLI will provide:

1. **Streaming agent loop** with real-time tool execution display
2. **Multi-agent orchestration** with lazy-spawn blueprints and mailbox-based communication
3. **Dual-mode operation**: Interactive REPL + one-shot commands
4. **Session persistence** with resume/continue support
5. **SSE streaming** for real-time progress updates (optional web UI)

---

## Current Architecture Analysis

### What Lyra Has Now

**Entry Points:**
- `lyra` (no args) → TUI v2 (Textual shell) or legacy prompt_toolkit REPL
- `lyra run` → One-shot task execution
- `lyra plan` → Plan-only mode
- Multiple subcommands: `init`, `doctor`, `session`, `mcp`, `brain`, etc.

**TUI v2 Structure:**
```
tui_v2/
├── app.py              # LyraHarnessApp (Textual subclass)
├── brand.py            # Welcome messages
├── status.py           # Status bar formatting
└── modals/             # Command palette, model picker
```

**Interactive Driver:**
```
interactive/
├── driver.py           # Legacy prompt_toolkit REPL
├── session.py          # Session management
└── ...                 # Various interactive components
```

**Problems with Current TUI:**
1. **Heavy dependency**: Textual adds complexity and startup overhead
2. **Limited portability**: Doesn't work well in non-TTY environments
3. **Inconsistent UX**: Different from Claude Code's familiar interface
4. **Hard to extend**: TUI widgets are harder to maintain than streaming text

---

## Target Architecture: Claude Code + OpenAgentd Patterns

### 1. Streaming CLI Core

**Inspired by:** Claude Code's agent loop architecture

```python
# New structure
lyra_cli/
├── cli/
│   ├── __init__.py
│   ├── repl.py              # Interactive REPL (streaming)
│   ├── oneshot.py           # One-shot command execution
│   ├── streaming.py         # SSE streaming output
│   └── formatter.py         # Output formatting (markdown, tool cards)
├── agent/
│   ├── loop.py              # Core agent loop (Claude Code style)
│   ├── hooks.py             # Hook system (before_model, after_model, etc.)
│   ├── checkpointer.py      # Session persistence
│   └── streaming.py         # Stream event publisher
├── team/
│   ├── orchestrator.py      # Multi-agent coordinator
│   ├── mailbox.py           # Asyncio-based message passing
│   ├── blueprints/          # Agent blueprint definitions
│   │   ├── researcher.md
│   │   ├── coder.md
│   │   ├── writer.md
│   │   └── reviewer.md
│   └── member.py            # Team member lifecycle
└── stream/
    ├── store.py             # In-memory SSE stream store
    └── events.py            # Stream event types
```

### 2. Message Types (Claude Code Pattern)

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class SystemMessage:
    """Initialization and context compaction messages."""
    content: str
    type: Literal["system"] = "system"

@dataclass
class AssistantMessage:
    """Agent responses with optional tool calls."""
    content: str
    tool_calls: list[ToolCall] | None = None
    type: Literal["assistant"] = "assistant"

@dataclass
class UserMessage:
    """User prompts and tool results."""
    content: str
    type: Literal["user"] = "user"

@dataclass
class StreamEvent:
    """Real-time streaming deltas."""
    event_type: Literal["text_delta", "tool_call", "tool_start", "tool_end", "thinking"]
    data: dict
    agent: str | None = None  # For multi-agent attribution

@dataclass
class ResultMessage:
    """Final turn summary with cost and token usage."""
    total_cost_usd: float
    tokens_in: int
    tokens_out: int
    type: Literal["result"] = "result"
```

### 3. Multi-Agent Orchestration (OpenAgentd Pattern)

**Lazy-Spawn Blueprint System:**

```python
# team/orchestrator.py
class LyraTeam:
    """Multi-agent research team with lazy-spawn members."""
    
    def __init__(self):
        self.lead: LeadAgent = LeadAgent()
        self.blueprints: dict[str, Blueprint] = self._load_blueprints()
        self.members: dict[str, TeamMember] = {}
        self.mailbox: TeamMailbox = TeamMailbox()
    
    async def spawn(self, blueprint_name: str) -> TeamMember:
        """Materialize a member instance from blueprint."""
        bp = self.blueprints[blueprint_name]
        instance_id = self._next_instance_id(blueprint_name)
        handle = f"{blueprint_name}#{instance_id}"
        
        # Build agent from .md file
        agent = rebuild_agent_from_disk(bp.source_path)
        agent.name = handle
        
        # Create member with mailbox registration
        member = TeamMember(agent, mailbox=self.mailbox)
        self.members[handle] = member
        
        return member
    
    async def send_message(self, to: str, content: str, from_agent: str):
        """Send message via mailbox (triggers activation)."""
        await self.mailbox.send(to=to, message=Message(
            content=content,
            from_agent=from_agent
        ))
```

**Mailbox-Based Activation:**

```python
# team/mailbox.py
class TeamMailbox:
    """Asyncio-based message passing with on-message activation."""
    
    def __init__(self):
        self._inboxes: dict[str, asyncio.Queue] = {}
        self._callbacks: dict[str, Callable] = {}
    
    def register(self, agent_name: str, on_message: Callable):
        """Register agent with activation callback."""
        self._inboxes[agent_name] = asyncio.Queue()
        self._callbacks[agent_name] = on_message
    
    async def send(self, to: str, message: Message):
        """Send message and trigger activation."""
        if to not in self._inboxes:
            raise ValueError(f"Agent {to} not registered")
        
        await self._inboxes[to].put(message)
        
        # Trigger activation callback
        if to in self._callbacks:
            asyncio.create_task(self._callbacks[to]())
```

### 4. Streaming Output (OpenAgentd Pattern)

**In-Memory SSE Store:**

```python
# stream/store.py
class StreamStore:
    """In-memory SSE streaming with mid-turn reconnect support."""
    
    def __init__(self):
        self._turns: dict[str, TurnState] = {}
    
    async def init_turn(self, session_id: str):
        """Initialize turn state before background task."""
        self._turns[session_id] = TurnState(
            is_streaming=True,
            content={},  # Per-agent text accumulator
            thinking={},  # Per-agent reasoning
            tool_calls=[],
            subscribers=[]
        )
    
    async def push_event(self, session_id: str, event: StreamEvent):
        """Update state + fan-out to subscribers."""
        state = self._turns[session_id]
        
        if event.event_type == "text_delta":
            state.content[event.agent] += event.data["text"]
        elif event.event_type == "thinking":
            state.thinking[event.agent] += event.data["text"]
        elif event.event_type == "tool_call":
            state.tool_calls.append(event.data)
        
        # Fan-out to all subscribers
        for q in state.subscribers:
            await q.put(event.to_wire())
    
    async def attach(self, session_id: str):
        """Subscribe to stream with replay support."""
        state = self._turns.get(session_id)
        if not state or not state.is_streaming:
            return  # DB is authoritative
        
        # Register queue BEFORE replaying (no gap window)
        q = asyncio.Queue()
        state.subscribers.append(q)
        
        # Replay accumulated state
        for agent, text in state.content.items():
            yield StreamEvent(
                event_type="text_delta",
                agent=agent,
                data={"text": text}
            ).to_wire()
        
        # Yield live events
        while True:
            item = await q.get()
            if item is SENTINEL:
                break
            yield item
```

### 5. Hook System (OpenAgentd Pattern)

```python
# agent/hooks.py
class BaseAgentHook:
    """Lifecycle hooks for agent execution."""
    
    async def before_agent(self, ctx: RunContext, state: AgentState):
        """Called once before agent loop starts."""
        pass
    
    async def before_model(
        self, 
        ctx: RunContext, 
        state: AgentState, 
        request: ModelRequest
    ) -> ModelRequest | None:
        """Called before each LLM call. Can modify request."""
        pass
    
    async def on_model_delta(
        self, 
        ctx: RunContext, 
        state: AgentState, 
        chunk: StreamChunk
    ):
        """Called for each streaming delta."""
        pass
    
    async def after_model(
        self, 
        ctx: RunContext, 
        state: AgentState, 
        assistant_msg: AssistantMessage
    ):
        """Called after LLM response assembled."""
        pass
    
    async def wrap_tool_call(
        self, 
        ctx: RunContext, 
        state: AgentState, 
        tool_call: ToolCall,
        next_handler: Callable
    ):
        """Wrap tool execution (middleware pattern)."""
        return await next_handler(ctx, state, tool_call)
    
    async def after_agent(
        self, 
        ctx: RunContext, 
        state: AgentState, 
        last_msg: AssistantMessage
    ):
        """Called once after agent loop completes."""
        pass
```

**Built-in Hooks:**
- `StreamPublisherHook`: Pushes SSE events to stream store
- `CheckpointerHook`: Persists messages at 4 sync points per turn
- `ResearchHook`: Injects research context and extracts citations
- `TeamInboxHook`: Drains mailbox before each LLM call (team mode)

### 6. Agent Loop (Claude Code Pattern)

```python
# agent/loop.py
async def run_agent_loop(
    messages: list[Message],
    config: AgentConfig,
    hooks: list[BaseAgentHook],
    checkpointer: Checkpointer,
    interrupt_event: asyncio.Event | None = None
) -> list[Message]:
    """Core agent loop with hook integration."""
    
    ctx = RunContext(
        session_id=config.session_id,
        run_id=str(uuid7()),
        agent_name=config.name
    )
    
    state = AgentState(
        messages=messages,
        system_prompt=config.system_prompt,
        capabilities=config.capabilities
    )
    
    # before_agent hooks
    for hook in hooks:
        await hook.before_agent(ctx, state)
    
    iteration = 0
    while iteration < config.max_iterations:
        iteration += 1
        
        # Build model request
        model_request = ModelRequest(
            messages=tuple(state.messages),
            system_prompt=state.system_prompt
        )
        
        # before_model hooks (can modify request)
        for hook in hooks:
            updated = await hook.before_model(ctx, state, model_request)
            if updated:
                model_request = updated
        
        await checkpointer.sync(ctx, state)  # Sync point 1
        
        # Stream LLM response
        assistant_msg = await stream_and_assemble(
            model_request, ctx, state, hooks, interrupt_event
        )
        messages.append(assistant_msg)
        
        # after_model hooks
        for hook in hooks:
            await hook.after_model(ctx, state, assistant_msg)
        
        await checkpointer.sync(ctx, state)  # Sync point 2
        
        if not assistant_msg.tool_calls:
            break  # Final answer
        
        # Check interrupt before tool execution
        if interrupt_event and interrupt_event.is_set():
            for tc in assistant_msg.tool_calls:
                messages.append(ToolMessage(
                    content="Cancelled by user.",
                    tool_call_id=tc.id
                ))
            break
        
        # Execute tools (with hook wrapping)
        tool_chain = build_tool_chain(hooks, execute_tool)
        results = await gather_or_cancel(
            [tool_chain(ctx, state, tc) for tc in assistant_msg.tool_calls],
            interrupt_event
        )
        
        for tc, result in results:
            messages.append(ToolMessage(
                content=result,
                tool_call_id=tc.id
            ))
        
        await checkpointer.sync(ctx, state)  # Sync point 3
    
    # after_agent hooks
    for hook in hooks:
        await hook.after_agent(ctx, state, assistant_msg)
    
    await checkpointer.sync(ctx, state)  # Sync point 4
    
    return messages
```

---

## Migration Strategy

### Phase 1: Core CLI Infrastructure (Week 1)

**Goal:** Build streaming CLI foundation without breaking existing functionality

**Tasks:**
1. Create `cli/repl.py` with streaming output
2. Implement message types (`SystemMessage`, `AssistantMessage`, etc.)
3. Build `cli/formatter.py` for markdown rendering and tool cards
4. Add `cli/oneshot.py` for non-interactive execution
5. Keep TUI as fallback option (`--tui` flag)

**Success Criteria:**
- `lyra` launches streaming REPL
- Tool execution displays in real-time
- Session persistence works
- `lyra --tui` still launches old TUI

### Phase 2: Agent Loop Refactor (Week 2)

**Goal:** Replace current agent execution with Claude Code-style loop

**Tasks:**
1. Implement `agent/loop.py` with hook system
2. Create `agent/hooks.py` base classes
3. Build `agent/checkpointer.py` with 4 sync points
4. Migrate existing agent logic to new loop
5. Add `agent/streaming.py` for stream event publishing

**Success Criteria:**
- Agent loop runs with hooks
- Checkpointing works (crash-safe)
- Streaming events flow correctly
- All existing tests pass

### Phase 3: Multi-Agent Orchestration (Week 3)

**Goal:** Add OpenAgentd-style team coordination

**Tasks:**
1. Create `team/orchestrator.py` with lazy-spawn
2. Implement `team/mailbox.py` with asyncio queues
3. Build `team/member.py` lifecycle management
4. Define agent blueprints in `team/blueprints/`
5. Add team mode to CLI (`/team spawn researcher`)

**Success Criteria:**
- Lead agent can spawn members
- Mailbox-based message passing works
- Multiple agents run in parallel
- Team state persists across restarts

### Phase 4: SSE Streaming (Optional, Week 4)

**Goal:** Add web UI support with real-time streaming

**Tasks:**
1. Implement `stream/store.py` in-memory SSE store
2. Create `stream/events.py` event types
3. Add FastAPI endpoint for SSE streaming
4. Build simple web UI for monitoring
5. Support mid-turn reconnect

**Success Criteria:**
- SSE endpoint streams events
- Web UI displays agent progress
- Reconnect works mid-turn
- Multiple clients can watch same session

### Phase 5: Cleanup & Documentation (Week 5)

**Goal:** Remove TUI, update docs, polish UX

**Tasks:**
1. Remove `tui_v2/` directory
2. Remove Textual dependency
3. Update all documentation
4. Add migration guide for users
5. Polish CLI output formatting

**Success Criteria:**
- TUI code removed
- Docs updated
- Migration guide published
- User feedback incorporated

---

## Implementation Details

### CLI Entry Point Changes

**Before:**
```python
# __main__.py
if not use_legacy:
    from .tui_v2 import launch_tui_v2
    raise typer.Exit(launch_tui_v2(repo_root=repo_root, model=model))
```

**After:**
```python
# __main__.py
from .cli.repl import launch_streaming_repl

raise typer.Exit(
    launch_streaming_repl(
        repo_root=repo_root,
        model=model,
        budget_cap_usd=budget,
        resume_id=resume_target,
        pin_session_id=pin_id,
        bare=bare
    )
)
```

### Streaming REPL Implementation

```python
# cli/repl.py
async def launch_streaming_repl(
    repo_root: Path,
    model: str,
    budget_cap_usd: float | None = None,
    resume_id: str | None = None,
    pin_session_id: str | None = None,
    bare: bool = False
) -> int:
    """Launch Claude Code-style streaming REPL."""
    
    # Initialize session
    session = await load_or_create_session(
        repo_root=repo_root,
        resume_id=resume_id,
        pin_session_id=pin_session_id
    )
    
    # Print welcome banner
    print_welcome(
        version=__version__,
        model=model,
        repo=repo_root.name,
        session_id=session.id
    )
    
    # Main REPL loop
    while True:
        try:
            # Read user input (with multi-line support)
            prompt = await read_prompt()
            
            if not prompt:
                continue
            
            # Handle slash commands
            if prompt.startswith("/"):
                await handle_slash_command(prompt, session)
                continue
            
            # Execute agent loop with streaming
            async for event in run_agent_turn(
                session=session,
                prompt=prompt,
                model=model,
                budget_cap=budget_cap_usd
            ):
                # Stream events to terminal
                if event.type == "text_delta":
                    print(event.data["text"], end="", flush=True)
                elif event.type == "tool_call":
                    print(f"\n[Using {event.data['name']}...]", end="", flush=True)
                elif event.type == "tool_end":
                    print(" done")
                elif event.type == "thinking":
                    # Show thinking in dim color
                    print_dim(event.data["text"])
            
            print()  # Newline after turn
            
        except KeyboardInterrupt:
            print("\n^C")
            continue
        except EOFError:
            print("\nBye!")
            break
        except Exception as exc:
            print_error(f"Error: {exc}")
            continue
    
    return 0
```

### Tool Execution Display

**Claude Code Style:**
```
[Using Read...] done
[Using Bash...] done
[Using Edit...] done
```

**Implementation:**
```python
# cli/formatter.py
def format_tool_execution(tool_name: str, status: str) -> str:
    """Format tool execution status."""
    if status == "start":
        return f"[Using {tool_name}...]"
    elif status == "end":
        return " done"
    elif status == "error":
        return " error"
```

---

## Benefits of New Architecture

### 1. Simplicity
- **No Textual dependency**: Reduces complexity and startup time
- **Plain text output**: Easier to debug and test
- **Familiar UX**: Matches Claude Code's interface

### 2. Performance
- **Faster startup**: No TUI initialization overhead
- **Lower memory**: No widget tree in memory
- **Better streaming**: Direct stdout writes

### 3. Portability
- **Works in any terminal**: No TTY requirements
- **CI/CD friendly**: Easy to script and automate
- **SSH compatible**: No rendering issues over slow connections

### 4. Extensibility
- **Hook system**: Clean extension points
- **Multi-agent ready**: Built-in team orchestration
- **SSE streaming**: Optional web UI support

### 5. Maintainability
- **Less code**: Remove ~2000 lines of TUI code
- **Standard patterns**: Follow Claude Code conventions
- **Better testing**: Easier to unit test CLI output

---

## Risks & Mitigations

### Risk 1: User Resistance
**Mitigation:** Keep TUI as optional flag (`--tui`) for 1-2 releases, provide migration guide

### Risk 2: Feature Parity
**Mitigation:** Ensure all TUI features work in CLI (command palette → slash commands, status bar → inline status)

### Risk 3: Performance Regression
**Mitigation:** Benchmark before/after, optimize streaming output

### Risk 4: Breaking Changes
**Mitigation:** Semantic versioning, deprecation warnings, backward compatibility layer

---

## Success Metrics

1. **Startup time**: < 500ms (vs ~2s with TUI)
2. **Memory usage**: < 100MB (vs ~200MB with TUI)
3. **User satisfaction**: 80%+ positive feedback
4. **Test coverage**: Maintain 80%+ coverage
5. **Bug reports**: < 5 critical bugs in first month

---

## Timeline

- **Week 1:** Core CLI infrastructure
- **Week 2:** Agent loop refactor
- **Week 3:** Multi-agent orchestration
- **Week 4:** SSE streaming (optional)
- **Week 5:** Cleanup & documentation

**Total:** 5 weeks for full migration

---

## References

- [OpenAgentd Repository](https://github.com/lthoangg/OpenAgentd)
- [Claude Code Documentation](https://code.claude.com/docs)
- [Agent Loop Architecture](https://code.claude.com/docs/en/agent-sdk/agent-loop)
- [Streaming Output Patterns](https://code.claude.com/docs/en/agent-sdk/streaming-output)

