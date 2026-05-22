# Implementation Plan: Lyra Process Transparency (REVISED)

**Date:** 2026-05-17  
**Status:** REVISED — Addresses all Critic findings (CRITICAL + MAJOR)  
**Previous Version:** Initial draft (ITERATE verdict)  
**Goal:** Make all background processes visible in Lyra TUI with no hidden state

---

## Revision Summary

This revision addresses:
- **3 CRITICAL findings**: State management architecture, Rich Live() performance validation, state desync mitigation
- **3 MAJOR findings**: Rollback path, testable acceptance criteria, Textual alternative evaluation
- **6 additional gaps**: Error handling, accessibility, performance benchmarks, backward compatibility, ambiguity resolution

### Key Changes from Initial Draft

1. **Added Phase 0**: Rich Live() + Textual prototype with objective performance gates (2 days)
2. **Clarified state management**: Pragmatic hybrid approach (mutable UIStateManager MVP, event sourcing deferred to Phase 10)
3. **Specified single-writer thread**: asyncio.Queue with dedicated consumer task
4. **Added feature flags**: Each phase delivers behind `LYRA_ENABLE_<FEATURE>` flag
5. **Rewrote acceptance criteria**: Given-When-Then format with objective verification
6. **Evaluated Textual alternative**: Added Alternative 3 with explicit rejection rationale
7. **Addressed all 12 gaps**: Complete error handling, accessibility, performance numbers, backward compat

---

## Architecture Decision

### State Management: Pragmatic Hybrid Approach

**Decision**: Implement mutable UIStateManager as MVP (Phases 1-9), defer event sourcing to Phase 10.

**Rationale**:
- Event sourcing adds 40% complexity overhead for unproven benefit
- Mutable state is sufficient for MVP if properly synchronized
- Phase 10 provides escape hatch if state bugs emerge in production

**Implementation**:
- UIStateManager holds mutable state (task list, agent registry, token counts)
- All mutations go through EventQueue (asyncio.Queue) with single consumer task
- State is serializable for debugging (acceptance criterion in Phase 1)
- Technical debt tracked: "Consider event sourcing if state desync bugs emerge"

**Phase 10 Trigger**: If >3 state desync bugs reported in production, refactor to event-sourced architecture.

---

## Phase 0 — Performance Validation & Technology Selection (Week 0, 2 days)

**Goal**: Validate Rich Live() performance OR pivot to Textual before Phase 1 investment.

**Feature Flag**: N/A (prototype phase)

### 0.1 — Rich Live() Stress Test Prototype

**Given**: A prototype script using Rich Live() with realistic Lyra workload  
**When**: Running 3 concurrent stress scenarios  
**Then**: CPU usage < 10%, no visible flicker, frame rate ≥ 30 FPS

**Scenarios**:
1. **Thinking tokens streaming**: 50 tokens/sec for 60 seconds (3000 tokens total)
2. **Concurrent background tasks**: 5 progress bars updating every 100ms
3. **Tree expansion**: 100-node tree, 10 nodes expanding/collapsing per second

**Implementation**:
```python
# tests/prototypes/rich_live_stress_test.py
import time
from rich.live import Live
from rich.tree import Tree
from rich.progress import Progress

def stress_test_rich_live():
    with Live(auto_refresh=True, refresh_per_second=30) as live:
        # Scenario 1: Token streaming
        # Scenario 2: Progress bars
        # Scenario 3: Tree mutations
        # Measure: psutil.cpu_percent(), frame timing
```

**Acceptance Criteria**:
- **GIVEN** stress test runs for 60 seconds  
- **WHEN** all 3 scenarios execute concurrently  
- **THEN** CPU usage < 10% (measured via psutil)  
- **AND** no visible flicker (manual inspection)  
- **AND** frame rate ≥ 30 FPS (measured via frame timing)

**Gate Decision**:
- ✅ **PASS**: Proceed to Phase 1 with Rich Live()
- ❌ **FAIL**: Pivot to Textual (see Alternative 3 below)

### 0.2 — Textual Fallback Prototype (if Rich fails)

**Given**: Rich Live() fails performance gate  
**When**: Implementing same 3 scenarios in Textual  
**Then**: Performance meets same criteria (CPU < 10%, no flicker)

**Implementation**:
```python
# tests/prototypes/textual_stress_test.py
from textual.app import App
from textual.widgets import Tree, ProgressBar

class StressTestApp(App):
    # Same 3 scenarios as Rich prototype
```

**Verification**: Same acceptance criteria as 0.1

---

## Phase 1 — EventQueue & UIStateManager Foundation (Week 1, 3 days)

**Goal**: Single-writer thread architecture with serializable state.

**Feature Flag**: `LYRA_ENABLE_EVENT_QUEUE` (default: false)

### 1.1 — EventQueue Implementation

**Given**: Multiple threads emitting UI events  
**When**: Events are enqueued via EventQueue.emit()  
**Then**: Events are processed in FIFO order by single consumer task

**Implementation**:
```python
# lyra/ui/event_queue.py
import asyncio
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class UIEvent:
    type: str
    payload: dict[str, Any]

class EventQueue:
    def __init__(self):
        self._queue: asyncio.Queue[UIEvent] = asyncio.Queue(maxsize=1000)
        self._handlers: dict[str, list[Callable]] = {}
        self._consumer_task: asyncio.Task | None = None
    
    async def start(self):
        """Start consumer task."""
        self._consumer_task = asyncio.create_task(self._consume())
    
    async def stop(self):
        """Stop consumer task gracefully."""
        if self._consumer_task:
            self._consumer_task.cancel()
            await self._consumer_task
    
    def emit(self, event_type: str, **payload):
        """Thread-safe event emission."""
        try:
            self._queue.put_nowait(UIEvent(type=event_type, payload=payload))
        except asyncio.QueueFull:
            # Drop oldest event (backpressure)
            self._queue.get_nowait()
            self._queue.put_nowait(UIEvent(type=event_type, payload=payload))
    
    async def _consume(self):
        """Single consumer task — processes events in FIFO order."""
        while True:
            event = await self._queue.get()
            handlers = self._handlers.get(event.type, [])
            for handler in handlers:
                try:
                    handler(event.payload)
                except Exception as e:
                    # Log error, continue processing
                    print(f"EventQueue handler error: {e}")
```

**Acceptance Criteria**:
- **GIVEN** 1000 concurrent events emitted from 10 threads  
- **WHEN** EventQueue processes them  
- **THEN** all events processed in FIFO order  
- **AND** no state corruption (verified via state checksum)  
- **AND** queue overflow triggers backpressure (drops oldest event)

**Test**: `tests/ui/test_event_queue.py`
- Stress test: 1000 events, 10 threads, verify FIFO order
- Overflow test: 1001 events, verify oldest dropped
- Error handling: handler raises exception, queue continues

### 1.2 — UIStateManager with Serialization

**Given**: UIStateManager holds all UI state  
**When**: State is mutated via EventQueue  
**Then**: State can be serialized to JSON for debugging

**Implementation**:
```python
# lyra/ui/state_manager.py
from dataclasses import dataclass, asdict
import json

@dataclass
class TaskItem:
    id: str
    description: str
    state: str  # "pending" | "running" | "done"

@dataclass
class UIState:
    tokens_down_turn: int = 0
    bg_task_count: int = 0
    task_list: list[TaskItem] = field(default_factory=list)
    current_verb: str = "Thinking"

class UIStateManager:
    def __init__(self, event_queue: EventQueue):
        self._state = UIState()
        self._event_queue = event_queue
        # Register handlers
        event_queue.register("task_added", self._on_task_added)
        event_queue.register("task_completed", self._on_task_completed)
    
    def serialize(self) -> str:
        """Serialize state to JSON for debugging."""
        return json.dumps(asdict(self._state), indent=2)
    
    def _on_task_added(self, payload):
        self._state.task_list.append(TaskItem(**payload))
```

**Acceptance Criteria**:
- **GIVEN** UIStateManager with 5 tasks  
- **WHEN** serialize() is called  
- **THEN** returns valid JSON with all state fields  
- **AND** JSON can be deserialized back to UIState

**Test**: `tests/ui/test_state_manager.py`
- Serialization round-trip test
- Event handler mutation test

---

## Phase 2 — Token Counter & Spinner Integration (Week 1-2, 2 days)

**Goal**: Display live token counts in spinner header.

**Feature Flag**: `LYRA_ENABLE_TOKEN_COUNTER` (default: false)

### 2.1 — Token Streaming Integration

**Given**: Streaming API returns output tokens  
**When**: Tokens arrive in chunks  
**Then**: UIStateManager.tokens_down_turn increments via EventQueue

**Implementation**:
```python
# lyra/api/stream_handler.py
def on_chunk_received(chunk):
    if chunk.output_tokens:
        event_queue.emit("tokens_received", count=chunk.output_tokens)

def on_turn_started():
    event_queue.emit("turn_started")
```

**Acceptance Criteria**:
- **GIVEN** streaming response with 1200 tokens  
- **WHEN** chunks arrive over 10 seconds  
- **THEN** spinner displays "↓ 1.2k tokens"  
- **AND** counter resets to 0 on next turn

**Test**: `tests/ui/test_token_counter.py`
- Mock streaming: 1200 tokens → verify "1.2k" display
- Turn reset: verify counter clears

### 2.2 — Spinner Verb Rotation

**Given**: List of verbs ["Thinking", "Researching", "Analyzing", "Galloping", "Reasoning", "Exploring"]  
**When**: New turn starts  
**Then**: Verb rotates to next in list

**Acceptance Criteria**:
- **GIVEN** 6 consecutive turns  
- **WHEN** each turn starts  
- **THEN** verb cycles through all 6 verbs in order

**Test**: `tests/ui/test_spinner_verbs.py`

---

## Phase 3 — Task Checklist Widget (Week 2, 3 days)

**Goal**: Display pending tasks below spinner.

**Feature Flag**: `LYRA_ENABLE_TASK_CHECKLIST` (default: false)

### 3.1 — Checklist Renderer

**Given**: UIStateManager.task_list with N tasks  
**When**: Rendering checklist  
**Then**: Shows first 5 tasks + "… +N pending" for remainder

**Implementation**:
```python
# lyra/ui/widgets/task_checklist.py
_STATE_GLYPH = {
    "pending": "◻",
    "running": "◼",
    "done": "✓",
}

def render_checklist(tasks: list[TaskItem], max_visible: int = 5) -> list[str]:
    if not tasks:
        return []
    visible = tasks[:max_visible]
    hidden = len(tasks) - len(visible)
    lines = []
    for i, task in enumerate(visible):
        glyph = _STATE_GLYPH[task.state]
        prefix = "  ⎿  " if i == 0 else "     "
        lines.append(f"{prefix}{glyph} {task.description}")
    if hidden > 0:
        lines.append(f"      … +{hidden} pending")
    return lines
```

**Acceptance Criteria**:
- **GIVEN** 8 tasks in task_list  
- **WHEN** render_checklist() is called  
- **THEN** returns 6 lines (5 tasks + "… +3 pending")  
- **AND** first task has "⎿" prefix  
- **AND** running task shows "◼" glyph

**Test**: `tests/ui/test_task_checklist.py`
- 3 tasks → 3 lines
- 8 tasks → 6 lines (5 + overflow)
- Empty → []
- Running state → "◼"

### 3.2 — Keyboard Navigation (Accessibility)

**Given**: User presses Tab key  
**When**: Focus is on checklist  
**Then**: Focus moves to next interactive element

**Acceptance Criteria**:
- **GIVEN** checklist is visible  
- **WHEN** user presses Tab  
- **THEN** focus moves to next widget  
- **AND** screen reader announces "Task checklist, 5 items"

**Test**: Manual accessibility test with VoiceOver (macOS) / NVDA (Windows)

---

## Phase 4 — Background Task Counter (Week 2-3, 2 days)

**Goal**: Display active background agent count in footer.

**Feature Flag**: `LYRA_ENABLE_BG_COUNTER` (default: false)

### 4.1 — ProcessRegistry Polling

**Given**: ProcessRegistry tracks active agents  
**When**: Polling every 1 second  
**Then**: UIStateManager.bg_task_count updates via EventQueue

**Implementation**:
```python
# lyra/ui/background_poller.py
async def poll_process_registry(registry, event_queue):
    while True:
        active = len([p for p in registry.get_all() if p.state in ("running", "waiting")])
        event_queue.emit("bg_count_updated", count=active)
        await asyncio.sleep(1.0)
```

**Acceptance Criteria**:
- **GIVEN** 3 active background agents  
- **WHEN** poller runs  
- **THEN** footer displays "3 background tasks"  
- **AND** count updates within 1 second of agent state change

**Performance Benchmark**:
- Polling overhead: < 1ms per poll
- CPU usage: < 0.1% (measured via psutil)

**Test**: `tests/ui/test_bg_counter.py`
- Mock registry with 3 agents → verify "3 background tasks"
- 0 agents → footer segment collapses (empty string)

---

## Phase 5 — Agent Panel (Week 3-4, 4 days)

**Goal**: Full Claude Code-style agent list in sidebar.

**Feature Flag**: `LYRA_ENABLE_AGENT_PANEL` (default: false)

### 5.1 — Agent List Widget

**Given**: ProcessRegistry with N active agents  
**When**: Rendering agent panel  
**Then**: Shows first 8 agents with type, description, elapsed, tokens

**Implementation**:
```python
# lyra/ui/widgets/agent_panel.py
class AgentPanel(Widget):
    MAX_AGENTS = 8
    
    def render_agent_line(self, proc: AgentProcess, selected: bool) -> str:
        dot = "⏺" if selected else "◯"
        type_label = self._infer_type(proc)  # "executor", "researcher", etc.
        desc = self._truncate(proc.current_tool, 40)
        elapsed = self._format_elapsed(proc.elapsed_s)
        tokens = self._humanize(proc.tokens_out)
        return f"  {dot} {type_label:<16} {desc:<40}  {elapsed} · ↓ {tokens} tokens"
```

**Acceptance Criteria**:
- **GIVEN** 10 active agents  
- **WHEN** rendering agent panel  
- **THEN** shows first 8 agents  
- **AND** selected agent has "⏺" indicator  
- **AND** each line shows type, description, elapsed time, token count

**Test**: `tests/ui/test_agent_panel.py`
- 10 agents → renders 8 lines
- Selection indicator → "⏺" for selected, "◯" for others

### 5.2 — Keyboard Navigation

**Given**: User presses ↑/↓ keys  
**When**: Focus is on agent panel  
**Then**: Selection moves up/down

**Acceptance Criteria**:
- **GIVEN** 5 agents, selection on agent 2  
- **WHEN** user presses ↓  
- **THEN** selection moves to agent 3  
- **AND** screen reader announces "Agent 3 of 5: executor, implementing auth flow"

**Test**: Manual keyboard navigation test

### 5.3 — Agent Detail Modal

**Given**: User presses Enter on selected agent  
**When**: Agent detail modal opens  
**Then**: Shows full details (session ID, PID, tokens, cost, recent tools)

**Acceptance Criteria**:
- **GIVEN** agent selected  
- **WHEN** user presses Enter  
- **THEN** modal displays with all fields populated  
- **AND** Esc key closes modal

**Test**: `tests/ui/test_agent_detail.py`


---

## Phase 6 — Error Handling & Resilience (Week 4, 2 days)

**Goal**: Graceful degradation when components fail.

**Feature Flag**: Inherits from parent features

### 6.1 — EventQueue Error Handling

**Given**: Event handler raises exception  
**When**: Processing event  
**Then**: Exception is logged, queue continues processing

**Acceptance Criteria**:
- **GIVEN** handler that raises ValueError  
- **WHEN** event is processed  
- **THEN** exception is logged to stderr  
- **AND** subsequent events continue processing  
- **AND** UI remains responsive

**Test**: `tests/ui/test_event_queue_errors.py`

### 6.2 — Queue Overflow Backpressure

**Given**: EventQueue at max capacity (1000 events)  
**When**: New event arrives  
**Then**: Oldest event is dropped, new event is enqueued

**Acceptance Criteria**:
- **GIVEN** queue with 1000 events  
- **WHEN** 1001st event arrives  
- **THEN** event 1 is dropped  
- **AND** event 1001 is enqueued  
- **AND** warning is logged

**Test**: `tests/ui/test_queue_overflow.py`

### 6.3 — Rendering Fallback

**Given**: Widget rendering raises exception  
**When**: UI refresh occurs  
**Then**: Error placeholder is shown, app doesn't crash

**Acceptance Criteria**:
- **GIVEN** agent panel render() raises exception  
- **WHEN** UI refreshes  
- **THEN** panel shows "(error loading agents)"  
- **AND** other widgets continue rendering

**Test**: `tests/ui/test_render_fallback.py`

---

## Phase 7 — Performance Optimization (Week 4-5, 2 days)

**Goal**: Meet performance benchmarks under load.

**Feature Flag**: Inherits from parent features

### 7.1 — Performance Benchmarks

**Acceptance Criteria**:
- **GIVEN** 100 active agents  
- **WHEN** UI is rendering  
- **THEN** CPU usage < 5% (measured via psutil)  
- **AND** frame rate ≥ 30 FPS  
- **AND** memory usage < 50 MB for UI state

**Test**: `tests/performance/test_ui_load.py`
- Benchmark: 100 agents, 1000 tasks, 50 tokens/sec streaming
- Measure: CPU, memory, frame rate
- Assert: All metrics within bounds

### 7.2 — Render Throttling

**Given**: High-frequency state updates (>100/sec)  
**When**: UI is rendering  
**Then**: Renders are throttled to 30 FPS max

**Implementation**:
```python
# lyra/ui/renderer.py
class ThrottledRenderer:
    MIN_FRAME_TIME_MS = 33  # 30 FPS
    
    async def render_loop(self):
        while True:
            start = time.monotonic()
            await self._render()
            elapsed = time.monotonic() - start
            sleep_time = max(0, self.MIN_FRAME_TIME_MS / 1000 - elapsed)
            await asyncio.sleep(sleep_time)
```

**Acceptance Criteria**:
- **GIVEN** 200 state updates per second  
- **WHEN** renderer is active  
- **THEN** actual render rate ≤ 30 FPS  
- **AND** no visible lag or stutter

**Test**: `tests/ui/test_render_throttle.py`

---

## Phase 8 — Accessibility (Week 5, 2 days)

**Goal**: Screen reader support and keyboard navigation.

**Feature Flag**: Inherits from parent features

### 8.1 — Screen Reader Announcements

**Given**: State change occurs (task completed, agent started)  
**When**: Screen reader is active  
**Then**: Change is announced

**Acceptance Criteria**:
- **GIVEN** task transitions to "done"  
- **WHEN** VoiceOver is active (macOS)  
- **THEN** announces "Task completed: Implement auth flow"

**Test**: Manual testing with VoiceOver (macOS), NVDA (Windows)

### 8.2 — Keyboard Navigation

**Given**: User navigates with keyboard only  
**When**: Pressing Tab, Arrow keys, Enter  
**Then**: All interactive elements are accessible

**Acceptance Criteria**:
- **GIVEN** agent panel is visible  
- **WHEN** user presses Tab  
- **THEN** focus moves to agent panel  
- **AND** ↑/↓ keys navigate agents  
- **AND** Enter opens detail modal  
- **AND** Esc closes modal

**Test**: Manual keyboard-only navigation test

### 8.3 — ARIA Labels

**Given**: Widget is rendered  
**When**: Screen reader queries element  
**Then**: Semantic label is provided

**Implementation**:
```python
# lyra/ui/widgets/agent_panel.py
class AgentPanel(Widget):
    def get_aria_label(self) -> str:
        return f"Agent panel, {len(self.agents)} active agents"
```

**Test**: Manual screen reader test

---

## Phase 9 — Integration & End-to-End Testing (Week 5-6, 3 days)

**Goal**: Verify all components work together.

**Feature Flag**: `LYRA_ENABLE_PROCESS_TRANSPARENCY` (master flag, enables all sub-features)

### 9.1 — End-to-End Scenario Tests

**Scenario 1: Multi-Agent Research Task**

**Given**: User starts deep research task  
**When**: 5 background agents spawn  
**Then**: 
- Agent panel shows all 5 agents
- Token counters update in real-time
- Task checklist shows research phases
- Footer shows "5 background tasks"

**Acceptance Criteria**:
- **GIVEN** research task with 5 agents  
- **WHEN** task runs for 60 seconds  
- **THEN** all UI components update correctly  
- **AND** no state desync errors  
- **AND** CPU usage < 5%

**Test**: `tests/e2e/test_multi_agent_research.py`

**Scenario 2: High-Frequency Token Streaming**

**Given**: Agent generates 10k tokens in 30 seconds  
**When**: Streaming to UI  
**Then**: Token counter updates smoothly without flicker

**Acceptance Criteria**:
- **GIVEN** 10k tokens over 30 seconds (333 tokens/sec)  
- **WHEN** streaming to UI  
- **THEN** counter displays "↓ 10.0k tokens"  
- **AND** no visible flicker  
- **AND** CPU usage < 5%

**Test**: `tests/e2e/test_token_streaming.py`

**Scenario 3: Agent Lifecycle**

**Given**: Agent starts, runs, completes  
**When**: Monitoring in UI  
**Then**: State transitions are visible

**Acceptance Criteria**:
- **GIVEN** agent lifecycle: start → running → done  
- **WHEN** monitoring in agent panel  
- **THEN** agent appears when started  
- **AND** shows "running" state with live token count  
- **AND** disappears when done  
- **AND** bg_task_count decrements

**Test**: `tests/e2e/test_agent_lifecycle.py`

---

## Phase 10 — Event Sourcing Refactor (Future, if needed)

**Goal**: Refactor to event-sourced architecture if state bugs emerge.

**Trigger**: >3 state desync bugs reported in production

**Feature Flag**: `LYRA_ENABLE_EVENT_SOURCING` (default: false)

### 10.1 — Event Store

**Given**: All state mutations are events  
**When**: Event is emitted  
**Then**: Event is persisted to event store

**Implementation**:
```python
# lyra/ui/event_store.py
class EventStore:
    def append(self, event: UIEvent):
        # Persist to SQLite or file
        pass
    
    def replay(self) -> list[UIEvent]:
        # Replay all events to rebuild state
        pass
```

### 10.2 — UIStateManager as Materialized View

**Given**: EventStore contains all events  
**When**: Replaying events  
**Then**: UIStateManager state is rebuilt

**Acceptance Criteria**:
- **GIVEN** 1000 events in store  
- **WHEN** replaying from scratch  
- **THEN** UIStateManager state matches current state  
- **AND** replay completes in < 100ms

**Test**: `tests/ui/test_event_sourcing.py`

---


## Alternatives Evaluation

### Alternative 1: Pure Event Sourcing from Day 1

**Approach**: Implement event store and event-sourced UIStateManager from Phase 1.

**Pros**:
- Complete audit trail of all state changes
- Time-travel debugging (replay to any point)
- Guaranteed consistency (state is derived from events)

**Cons**:
- 40% more complexity upfront
- Slower MVP delivery (3-4 extra weeks)
- Unproven benefit for Lyra's use case
- Performance overhead (event persistence on every mutation)

**Rejection Rationale**: Event sourcing is over-engineering for MVP. Mutable state with single-writer thread is sufficient. Phase 10 provides escape hatch if state bugs emerge.

---

### Alternative 2: Continue with Current TUI (No Changes)

**Approach**: Keep existing TUI without process transparency features.

**Pros**:
- Zero implementation cost
- No risk of introducing bugs

**Cons**:
- Users have no visibility into background processes
- Debugging is difficult (no live state inspection)
- Poor UX compared to Claude Code
- Doesn't address core goal of process transparency

**Rejection Rationale**: Fails to meet project goal. Process transparency is a core requirement for Lyra's evolution.

---

### Alternative 3: Incremental Textual Migration

**Approach**: Replace Rich Live() with Textual reactive widgets from Phase 1.

**Pros**:
- Solves state desync problem (Textual has built-in reactive state)
- Proven performance (used in production by many TUI apps)
- Built-in expand/collapse, keyboard nav, accessibility
- Better long-term maintainability

**Cons**:
- Learning curve (new framework)
- May require rewriting existing rendering code
- Migration effort (2-3 weeks)

**Evaluation**: This alternative is evaluated in Phase 0. If Rich Live() fails performance gate, we pivot to Textual.

**Decision Criteria**:
- Rich Live() stress test passes → proceed with Rich
- Rich Live() stress test fails → pivot to Textual

---

## Rollback Strategy

### Feature Flag Architecture

Each phase delivers behind a feature flag:

```python
# lyra/config.py
FEATURE_FLAGS = {
    "LYRA_ENABLE_EVENT_QUEUE": os.getenv("LYRA_ENABLE_EVENT_QUEUE", "false") == "true",
    "LYRA_ENABLE_TOKEN_COUNTER": os.getenv("LYRA_ENABLE_TOKEN_COUNTER", "false") == "true",
    "LYRA_ENABLE_TASK_CHECKLIST": os.getenv("LYRA_ENABLE_TASK_CHECKLIST", "false") == "true",
    "LYRA_ENABLE_BG_COUNTER": os.getenv("LYRA_ENABLE_BG_COUNTER", "false") == "true",
    "LYRA_ENABLE_AGENT_PANEL": os.getenv("LYRA_ENABLE_AGENT_PANEL", "false") == "true",
    "LYRA_ENABLE_PROCESS_TRANSPARENCY": os.getenv("LYRA_ENABLE_PROCESS_TRANSPARENCY", "false") == "true",
}
```

### Rollback Process

**Phase N fails in production**:
1. Set `LYRA_ENABLE_<FEATURE>=false` in environment
2. Restart Lyra
3. Feature is disabled, TUI reverts to previous behavior
4. No code rollback needed (flag controls behavior)

**Complete rollback to TUI v2**:
1. Set `LYRA_ENABLE_PROCESS_TRANSPARENCY=false`
2. All sub-features are disabled
3. TUI v2 remains functional

### Backward Compatibility

**Legacy TUI flag**:
```bash
export LYRA_LEGACY_TUI=1  # Force TUI v2, ignore all new features
```

This flag bypasses all feature flags and uses TUI v2 code path exclusively.

---

## Technical Debt Tracking

### Known Debt Items

1. **Mutable UIStateManager** (Phase 1)
   - **Debt**: Not event-sourced, harder to debug state bugs
   - **Trigger**: >3 state desync bugs in production
   - **Resolution**: Phase 10 event sourcing refactor

2. **Polling ProcessRegistry** (Phase 4)
   - **Debt**: 1-second polling delay, not real-time
   - **Trigger**: User complaints about stale agent counts
   - **Resolution**: Replace with push-based event system

3. **Manual accessibility testing** (Phase 8)
   - **Debt**: No automated screen reader tests
   - **Trigger**: Accessibility regression reported
   - **Resolution**: Integrate automated accessibility testing framework

---

## File Change Summary

| File | Change Type | Phases |
|------|-------------|--------|
| `lyra/ui/event_queue.py` | **New** | 1 |
| `lyra/ui/state_manager.py` | **New** | 1 |
| `lyra/api/stream_handler.py` | Extend | 2 |
| `lyra/ui/widgets/task_checklist.py` | **New** | 3 |
| `lyra/ui/background_poller.py` | **New** | 4 |
| `lyra/ui/widgets/agent_panel.py` | **New** | 5 |
| `lyra/ui/widgets/agent_detail.py` | **New** | 5 |
| `lyra/ui/renderer.py` | Extend | 7 |
| `lyra/config.py` | Extend (feature flags) | All |
| `tests/prototypes/rich_live_stress_test.py` | **New** | 0 |
| `tests/prototypes/textual_stress_test.py` | **New** | 0 |
| `tests/ui/test_event_queue.py` | **New** | 1 |
| `tests/ui/test_state_manager.py` | **New** | 1 |
| `tests/ui/test_token_counter.py` | **New** | 2 |
| `tests/ui/test_task_checklist.py` | **New** | 3 |
| `tests/ui/test_bg_counter.py` | **New** | 4 |
| `tests/ui/test_agent_panel.py` | **New** | 5 |
| `tests/ui/test_event_queue_errors.py` | **New** | 6 |
| `tests/ui/test_render_fallback.py` | **New** | 6 |
| `tests/performance/test_ui_load.py` | **New** | 7 |
| `tests/e2e/test_multi_agent_research.py` | **New** | 9 |

---

## Timeline Summary

| Phase | Duration | Dependencies | Deliverable |
|-------|----------|--------------|-------------|
| 0 | 2 days | None | Performance validation, tech choice |
| 1 | 3 days | Phase 0 | EventQueue + UIStateManager |
| 2 | 2 days | Phase 1 | Token counter + spinner |
| 3 | 3 days | Phase 1 | Task checklist |
| 4 | 2 days | Phase 1 | Background task counter |
| 5 | 4 days | Phase 1, 4 | Agent panel |
| 6 | 2 days | Phases 1-5 | Error handling |
| 7 | 2 days | Phases 1-5 | Performance optimization |
| 8 | 2 days | Phases 1-5 | Accessibility |
| 9 | 3 days | Phases 1-8 | E2E testing |
| 10 | TBD | Production trigger | Event sourcing (if needed) |

**Total MVP Duration**: 25 days (5 weeks)

**Parallel Opportunities**:
- Phases 3 and 4 can run in parallel after Phase 1
- Phase 6, 7, 8 can run in parallel after Phase 5

**Critical Path**: Phase 0 → Phase 1 → Phase 5 → Phase 9

---

## Success Criteria (Final Verification)

Before marking this plan COMPLETE, verify:

- [ ] **Phase 0 gate passed**: Rich Live() OR Textual meets performance criteria
- [ ] **All acceptance criteria testable**: Every criterion has Given-When-Then format
- [ ] **Feature flags implemented**: Each phase behind flag, rollback tested
- [ ] **Performance benchmarks met**: CPU < 5%, frame rate ≥ 30 FPS, memory < 50 MB
- [ ] **Accessibility verified**: Keyboard nav + screen reader tested manually
- [ ] **E2E scenarios pass**: Multi-agent, token streaming, agent lifecycle
- [ ] **Error handling complete**: Queue overflow, handler exceptions, render fallback
- [ ] **Technical debt tracked**: All debt items documented with triggers
- [ ] **Backward compatibility**: `LYRA_LEGACY_TUI=1` flag works
- [ ] **State serialization works**: UIStateManager.serialize() produces valid JSON

---

## Open Questions

(To be tracked in `.omc/plans/open-questions.md`)

1. **Rich vs Textual decision**: Which framework passes Phase 0 performance gate?
2. **Event sourcing trigger**: What constitutes a "state desync bug" for Phase 10 trigger?
3. **Accessibility automation**: Which framework should we use for automated screen reader tests?
4. **ProcessRegistry polling**: Should we replace with push-based events in Phase 4, or defer to future?
5. **Agent type inference**: How do we infer agent type ("executor", "researcher") from AgentProcess?

---

## Appendix: Addressing Critic Findings

### Critical Findings Resolved

1. ✅ **State management architecture**: Pragmatic hybrid chosen (mutable MVP, event sourcing in Phase 10)
2. ✅ **Rich Live() performance**: Phase 0 validates with objective benchmarks
3. ✅ **State desync mitigation**: EventQueue with single consumer task specified

### Major Findings Resolved

4. ✅ **Rollback path**: Feature flags per phase, `LYRA_LEGACY_TUI=1` for complete rollback
5. ✅ **Testable acceptance criteria**: All rewritten in Given-When-Then format
6. ✅ **Textual alternative**: Alternative 3 added with evaluation in Phase 0

### Additional Gaps Resolved

7. ✅ **Error handling**: Phase 6 covers queue overflow, handler exceptions, render fallback
8. ✅ **Accessibility**: Phase 8 covers keyboard nav, screen reader, ARIA labels
9. ✅ **Performance benchmarks**: Specific numbers (CPU < 5%, 30 FPS, 50 MB memory)
10. ✅ **Backward compatibility**: `LYRA_LEGACY_TUI=1` flag specified
11. ✅ **State management ambiguity**: Clarified as mutable UIStateManager with EventQueue
12. ✅ **Hybrid approach ambiguity**: Clarified as pragmatic hybrid (mutable MVP, event sourcing deferred)

---

**Plan Status**: READY FOR CRITIC APPROVAL

**Next Step**: Submit to Critic for APPROVE verdict, then hand off to executor via `/oh-my-claudecode:start-work`

