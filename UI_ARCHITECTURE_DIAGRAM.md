# Lyra UI Architecture Diagram

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Purpose**: Visual reference for UI rebuild  

---

## Current State: Three Competing Implementations

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Lyra CLI Entry Point                         │
│                      (lyra_cli/__main__.py)                          │
│                                                                       │
│  Decision Logic:                                                     │
│  • --tui flag → tui_v2 (opt-in)                                     │
│  • LYRA_USE_STREAMING=true → streaming CLI                          │
│  • Default → Legacy TUI (prompt_toolkit) ⚠️ BACKWARDS               │
└────────────────────────┬────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│  Legacy TUI │  │   tui_v2     │  │  Streaming   │
│ (DEPRECATED)│  │  (PARTIAL)   │  │     CLI      │
│             │  │              │  │              │
│ prompt_tk   │  │  Textual     │  │   Rich       │
│ 1,221 lines │  │  2,207 lines │  │   Minimal    │
│             │  │              │  │              │
│ ✅ Complete │  │ ⚠️ Missing:  │  │ ✅ Works     │
│ ❌ Not Spec │  │  - Welcome   │  │ ❌ No TUI    │
│ ❌ Hard to  │  │  - Compact   │  │              │
│    Extend   │  │  - BG Switch │  │              │
│             │  │  - Todo      │  │              │
└─────────────┘  └──────┬───────┘  └──────────────┘
                        │
                        │ extends
                        ▼
                 ┌──────────────────┐
                 │   harness-tui    │
                 │  (SHARED LIB)    │
                 │                  │
                 │  Textual-based   │
                 │  4,946 lines     │
                 │                  │
                 │  ✅ Production   │
                 │  ✅ 12+ projects │
                 │  ✅ Well-tested  │
                 │  ⚠️ Generic      │
                 └──────────────────┘
```

---

## Target State: Single Unified Implementation

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Lyra CLI Entry Point                         │
│                      (lyra_cli/__main__.py)                          │
│                                                                       │
│  Decision Logic (AFTER REBUILD):                                    │
│  • Default → tui_v2 (Textual) ✅ CORRECT                            │
│  • LYRA_USE_STREAMING=true → streaming CLI                          │
│  • --legacy-tui → Legacy TUI (deprecated, removed in v1.0.0)       │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
                 ┌──────────────────┐
                 │      tui_v2      │
                 │   (COMPLETE)     │
                 │                  │
                 │  Textual-based   │
                 │  ~2,700 lines    │
                 │                  │
                 │  ✅ 24/24 FRs    │
                 │  ✅ Spec-aligned │
                 │  ✅ Extensible   │
                 │  ✅ Tested       │
                 └──────┬───────────┘
                        │
                        │ extends
                        ▼
                 ┌──────────────────┐
                 │   harness-tui    │
                 │  (SHARED LIB)    │
                 │                  │
                 │  Textual-based   │
                 │  4,946 lines     │
                 │                  │
                 │  ✅ Production   │
                 │  ✅ 12+ projects │
                 │  ✅ Well-tested  │
                 └──────────────────┘
```

---

## Detailed Component Architecture

### tui_v2 Structure (Target State)

```
lyra_cli/tui_v2/
│
├── app.py                          # LyraHarnessApp (extends HarnessApp)
│   ├── Bindings: Ctrl+P, Ctrl+T, Ctrl+B, Ctrl+O, Esc
│   ├── State: SessionState (single source of truth)
│   └── Composition: Welcome + Shell + Sidebar + Footer
│
├── transport.py                    # Event bus consumer
│   ├── Consumes: asyncio.Queue[AgentEvent]
│   ├── Dispatches: _handle_<event_type>()
│   └── Updates: SessionState reactives
│
├── events.py                       # AgentEvent typed union
│   ├── TokenDelta, ThoughtUpdate
│   ├── SubAgentSpawned, SubAgentProgress, SubAgentDone
│   ├── ToolCallStart, ToolCallChunk, ToolCallEnd
│   ├── CompactionStart, CompactionRestored
│   └── TodoUpdate, ModelChanged, PermissionModeChanged
│
├── widgets/
│   ├── welcome_card.py             # ✅ NEW (Phase 1)
│   │   ├── 2-column grid (mascot + tips)
│   │   ├── Collapse on first message
│   │   └── Reactive: model, cwd, account
│   │
│   ├── compaction_banner.py        # ✅ NEW (Phase 1)
│   │   ├── Checklist of restored items
│   │   ├── Ctrl+O for detail pane
│   │   └── Auto-collapse after 30s
│   │
│   ├── todo_panel.py               # ✅ NEW (Phase 1)
│   │   ├── 5 visible + overflow
│   │   ├── Glyphs: ◻ ◼ ⚠
│   │   └── Animation on transition
│   │
│   ├── status.py                   # ✅ Implemented
│   ├── expandable.py               # ✅ Implemented
│   ├── progress.py                 # ✅ Implemented
│   └── brand.py                    # ✅ Implemented
│
├── modals/
│   ├── background_switcher.py      # ✅ NEW (Phase 1)
│   │   ├── ListView of background tasks
│   │   ├── Ctrl+T to open
│   │   └── Enter to bring to foreground
│   │
│   ├── command_palette.py          # ✅ Implemented
│   ├── model.py                    # ✅ Implemented
│   ├── skill.py                    # ✅ Implemented
│   ├── mcp.py                      # ✅ Implemented
│   └── task_panel.py               # ✅ Implemented
│
├── sidebar/
│   ├── tabs.py                     # ✅ Implemented
│   ├── agents_tab.py               # ✅ Implemented
│   ├── process_tab.py              # ✅ Implemented
│   └── agent_detail.py             # ✅ Implemented
│
└── commands/
    ├── sessions.py                 # ✅ Implemented
    ├── escape.py                   # ✅ Implemented
    └── budget.py                   # ✅ Implemented
```

---

## Data Flow Architecture

### Event Flow (Agent → UI)

```
┌─────────────────┐
│  Agent Loop     │
│  (Background)   │
│                 │
│  • LLM calls    │
│  • Tool exec    │
│  • Sub-agents   │
│  • Compaction   │
└────────┬────────┘
         │
         │ emits
         ▼
┌─────────────────────────┐
│  asyncio.Queue          │
│  [AgentEvent]           │
│                         │
│  • TokenDelta           │
│  • SubAgentSpawned      │
│  • ToolCallChunk        │
│  • CompactionRestored   │
│  • TodoUpdate           │
└────────┬────────────────┘
         │
         │ consumed by
         ▼
┌─────────────────────────┐
│  Transport Bus Worker   │
│  (tui_v2/transport.py)  │
│                         │
│  @work(group="bus")     │
│  • Reads queue          │
│  • Dispatches handlers  │
│  • Updates state        │
└────────┬────────────────┘
         │
         │ mutates
         ▼
┌─────────────────────────┐
│  SessionState           │
│  (Single Source)        │
│                         │
│  Reactives:             │
│  • model                │
│  • sub_agents           │
│  • background_tasks     │
│  • todos                │
│  • compaction_history   │
└────────┬────────────────┘
         │
         │ watched by
         ▼
┌─────────────────────────┐
│  Widgets                │
│  (Textual)              │
│                         │
│  watch_* handlers:      │
│  • watch_model()        │
│  • watch_sub_agents()   │
│  • watch_todos()        │
│  • Auto re-render       │
└─────────────────────────┘
```

---

## Widget Hierarchy

```
LyraHarnessApp
│
├── WelcomeCard (NEW)
│   ├── Grid
│   │   ├── Static (mascot + title)
│   │   └── Static (tips + news)
│   └── Collapsed: Static (one-line)
│
├── Shell (from harness-tui)
│   ├── Header
│   │   └── StatusLine
│   │       ├── Animated verb spinner
│   │       ├── Token counter
│   │       └── Thought summary
│   │
│   ├── ChatLog (scrollable)
│   │   ├── MessageBlock (user)
│   │   ├── MessageBlock (assistant)
│   │   ├── ToolCard (expandable)
│   │   ├── CompactionBanner (NEW)
│   │   └── SubAgentTree
│   │
│   ├── Composer
│   │   ├── PromptInput (slash suggester)
│   │   └── ContextBar
│   │
│   └── Footer
│       ├── PermissionPill
│       ├── BackgroundTaskCounter
│       └── KeyBindings
│
└── Sidebar (tabbed)
    ├── AgentsTab
    │   └── SubAgentTree (hierarchical)
    │
    ├── ProcessTab
    │   └── ProcessList
    │
    └── TasksTab (NEW)
        └── TodoPanel (NEW)
```

---

## State Management

### SessionState Schema

```python
@dataclass
class SessionState:
    """Single source of truth for all UI state."""
    
    # Model & Config
    model: reactive[str] = reactive("claude-sonnet-4-6")
    permission_mode: reactive[PermissionMode] = reactive("ask")
    cwd: reactive[str] = reactive("")
    
    # Sub-Agents
    sub_agents: reactive[dict[str, SubAgentState]] = reactive({})
    
    # Background Tasks
    background_tasks: reactive[dict[str, BackgroundTask]] = reactive({})
    
    # To-Do List
    todos: reactive[list[TodoItem]] = reactive([])
    
    # Compaction History
    compaction_history: reactive[list[CompactionEvent]] = reactive([])
    
    # Active Work
    active_worker_count: reactive[int] = reactive(0)
    last_token_delta: reactive[int] = reactive(0)
    elapsed_seconds: reactive[float] = reactive(0.0)
    current_thought: reactive[str] = reactive("")
```

### SubAgentState Schema

```python
@dataclass
class SubAgentState:
    id: str
    name: str                    # e.g., "oh-my-claudecode:executor"
    label: str                   # Short task summary
    task_summary: str            # Full description
    status: Literal["pending", "running", "done", "failed"]
    tool_uses: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    started_at: float = 0.0
    last_log_line: str = ""
    expanded: bool = False
    error: str | None = None
```

---

## Dependency Graph

### Build-Time Dependencies

```
tui_v2
  ├── harness-tui (>=0.5.0)
  │   ├── textual (>=0.86)
  │   │   └── rich (>=13.7)
  │   └── structlog
  │
  ├── lyra-core
  │   └── harness-core
  │
  └── lyra_cli/core/  (NEW - refactored shared code)
      ├── skill_manager.py
      ├── memory_manager.py
      └── (agent_integration.py - TBD)
```

### Runtime Dependencies

```
LyraHarnessApp
  ├── HarnessApp (base class from harness-tui)
  │   ├── Shell
  │   ├── ChatLog
  │   ├── ToolCard
  │   ├── StatusLine
  │   └── Sidebar
  │
  ├── Lyra-specific widgets (tui_v2/widgets/)
  │   ├── WelcomeCard
  │   ├── CompactionBanner
  │   └── TodoPanel
  │
  ├── Lyra-specific modals (tui_v2/modals/)
  │   ├── BackgroundSwitcher
  │   ├── CommandPalette
  │   ├── ModelPicker
  │   └── TaskPanel
  │
  └── Transport (tui_v2/transport.py)
      └── Agent Loop (background process)
```

---

## File Size Comparison

### Before Cleanup

```
Legacy TUI:
  cli/tui.py              1,221 lines
  cli/input.py           11,735 bytes
  cli/banner.py           6,278 bytes
  cli/spinner.py          3,434 bytes
  cli/agent_integration   ~4,800 bytes
  ─────────────────────────────────
  Total:                 ~2,000 lines

tui_v2 (incomplete):
  tui_v2/                 2,207 lines
  
harness-tui:
  harness_tui/            4,946 lines
```

### After Cleanup

```
tui_v2 (complete):
  tui_v2/                 ~2,700 lines
  (+ 4 new widgets:       ~450 lines)
  
harness-tui:
  harness_tui/            4,946 lines
  (unchanged)

Legacy TUI:
  REMOVED                 -2,000 lines
```

**Net Change**: +450 lines (new features), -2,000 lines (legacy removal) = **-1,550 lines total**

---

## Migration Path

### Phase 0-1: Preparation (Weeks 1-3)
```
Current State          Add Missing Widgets
     │                        │
     ▼                        ▼
┌─────────┐            ┌─────────┐
│ Legacy  │            │ Legacy  │
│   +     │    ───>    │   +     │
│ tui_v2  │            │ tui_v2  │
│(partial)│            │(complete)│
└─────────┘            └─────────┘
```

### Phase 2-3: Transition (Weeks 4-5)
```
Add Missing Widgets    Make tui_v2 Default
     │                        │
     ▼                        ▼
┌─────────┐            ┌─────────┐
│ Legacy  │            │ tui_v2  │
│   +     │    ───>    │   +     │
│ tui_v2  │            │ Legacy  │
│(complete)│           │(fallback)│
└─────────┘            └─────────┘
```

### Phase 4-5: Cleanup (Weeks 7+, after 2-3 months)
```
Make tui_v2 Default    Remove Legacy
     │                        │
     ▼                        ▼
┌─────────┐            ┌─────────┐
│ tui_v2  │            │ tui_v2  │
│   +     │    ───>    │  ONLY   │
│ Legacy  │            │         │
│(fallback)│           │         │
└─────────┘            └─────────┘
```

---

## Performance Characteristics

### Legacy TUI (prompt_toolkit)
- **Render**: ~60 fps (terminal-native)
- **Memory**: ~80 MB RSS
- **Startup**: ~200 ms
- **Streaming**: Synchronous (blocks on I/O)

### tui_v2 (Textual)
- **Render**: ~30-60 fps (Textual compositor)
- **Memory**: ~150 MB RSS (target: <200 MB)
- **Startup**: ~300 ms
- **Streaming**: Asynchronous (non-blocking)

### harness-tui (Textual)
- **Render**: ~30-60 fps
- **Memory**: ~120 MB RSS
- **Startup**: ~250 ms
- **Streaming**: Asynchronous

---

## Testing Strategy

### Unit Tests
```
tests/tui_v2/
├── test_welcome_card.py        # NEW
├── test_compaction_banner.py   # NEW
├── test_background_switcher.py # NEW
├── test_todo_panel.py          # NEW
├── test_transport.py           # Existing
├── test_status.py              # Existing
└── test_modals.py              # Existing
```

### Snapshot Tests
```
tests/tui_v2/snapshots/
├── welcome_card_120cols.svg
├── welcome_card_60cols.svg
├── compaction_banner.svg
├── background_switcher_3tasks.svg
└── todo_panel_8items.svg
```

### Integration Tests
```
tests/tui_v2/
├── test_event_bus_integration.py
├── test_cancellation_timing.py
└── test_resize_handling.py
```

---

## Key Metrics

### Spec Compliance
- **Before**: 20/24 FRs (83%)
- **After Phase 1**: 24/24 FRs (100%)

### Code Quality
- **Test Coverage**: 100% for new widgets
- **Constitution**: 7/7 principles compliant
- **Performance**: ≥30 fps, <200 MB RSS

### Maintenance Burden
- **Before**: 3 implementations, ~8,000 lines
- **After**: 1 implementation, ~7,600 lines
- **Reduction**: -400 lines, -2 implementations

---

**End of Architecture Diagram**
