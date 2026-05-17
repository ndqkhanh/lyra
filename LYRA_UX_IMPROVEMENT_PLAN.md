# Lyra UX Improvement Plan
## Inspired by Claude Code's Progress Indicators

**Goal**: Make Lyra's internal processes visible and engaging like Claude Code

---

## Current State Analysis

### ✅ Already Implemented
- Status line with repo, turn, tokens segments
- Background task tracking (`_bg_tasks`)
- Active agent tracking (`_active_agents`)
- Active tool tracking (`_active_tools`)
- Expandable blocks (ctrl+o) via `ExpandableBlockManager`
- Welcome card, compaction banner, todo panel
- Keyboard shortcuts (ctrl+k, alt+p, alt+t, ctrl+t, ctrl+b, ctrl+o)

### ❌ Missing (Compared to Claude Code)
1. **Real-time progress spinners** (⏺, ✶, ✻, ✳, ✽, ✶)
2. **Parallel agent execution display** with live status
3. **Token usage per operation** (not just total)
4. **Time tracking per operation**
5. **Expandable tool output** with (ctrl+o to expand) hints
6. **Agent work summaries** (e.g., "12 tool uses · 46.8k tokens")
7. **Background task panel** with status indicators
8. **Thinking time display** (e.g., "thought for 28s")
9. **Model name in progress indicators**
10. **Phase/step progress** (e.g., "◻ Phase 3: Implement Research Pipeline")

---

## Phase 1: Real-Time Progress Spinners

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/progress_spinner.py`

```python
"""Real-time progress spinners like Claude Code."""
from rich.spinner import Spinner

SPINNER_FRAMES = ["⏺", "✶", "✻", "✳", "✽", "✶"]
SPINNER_VERBS = [
    "Thinking", "Analyzing", "Processing", "Computing",
    "Researching", "Implementing", "Verifying", "Optimizing",
    "Blanching", "Roosting", "Galloping", "Puttering", "Pollinating"
]

class ProgressSpinner:
    """Animated spinner with verb rotation."""
    def __init__(self):
        self.frame_index = 0
        self.verb_index = 0
    
    def next_frame(self) -> str:
        """Get next spinner frame with verb."""
        frame = SPINNER_FRAMES[self.frame_index % len(SPINNER_FRAMES)]
        verb = SPINNER_VERBS[self.verb_index % len(SPINNER_VERBS)]
        self.frame_index += 1
        return f"{frame} {verb}…"
```

### Integration Points
- `LyraHarnessApp._consume_events()` - Update spinner on each event
- `AgentIntegration.run_agent()` - Show spinner during LLM streaming
- Tool execution - Show spinner during tool calls

---

## Phase 2: Parallel Agent Execution Display

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/agent_panel.py`

```python
"""Display parallel agent execution like Claude Code."""

class AgentExecutionPanel:
    """Shows running agents with live status.
    
    Example:
    ⏺ Running 4 agents… (ctrl+o to expand)
       ├ oh-my-claudecode:executor (Wave A) · 12 tool uses · 46.8k tokens
       │ ⎿  Done
       ├ oh-my-claudecode:executor (Wave C) · 26 tool uses · 54.3k tokens
       │ ⎿  Read agent output: b62lxay8a
       ├ oh-my-claudecode:executor (Wave D+E) · 13 tool uses · 42.2k tokens
       │ ⎿  Write: src/lyra_cli/interactive/skills_lifecycle.py
       └ oh-my-claudecode:executor (Wave F+G) · 16 tool uses · 61.6k tokens
          ⎿  Searching for 1 pattern, reading 13 files…
    """
    
    def __init__(self):
        self.agents = {}  # agent_id -> AgentStatus
    
    def add_agent(self, agent_id: str, description: str):
        """Register new agent."""
        self.agents[agent_id] = {
            "description": description,
            "tool_uses": 0,
            "tokens": 0,
            "status": "running",
            "last_action": "",
        }
    
    def update_agent(self, agent_id: str, **kwargs):
        """Update agent status."""
        if agent_id in self.agents:
            self.agents[agent_id].update(kwargs)
    
    def render(self) -> str:
        """Render agent panel."""
        if not self.agents:
            return ""
        
        lines = [f"⏺ Running {len(self.agents)} agents… (ctrl+o to expand)"]
        for i, (agent_id, status) in enumerate(self.agents.items()):
            is_last = i == len(self.agents) - 1
            prefix = "└" if is_last else "├"
            
            line = f"   {prefix} {status['description']} · "
            line += f"{status['tool_uses']} tool uses · "
            line += f"{status['tokens']/1000:.1f}k tokens"
            lines.append(line)
            
            if status['last_action']:
                lines.append(f"   │ ⎿  {status['last_action']}")
        
        return "\n".join(lines)
```

### Integration Points
- `LyraHarnessApp._active_agents` - Track agent lifecycle
- Agent spawn events - Call `add_agent()`
- Agent tool use events - Call `update_agent(tool_uses=...)`
- Agent completion events - Call `update_agent(status="done")`

---

## Phase 3: Token & Time Tracking Per Operation

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/metrics.py`

```python
"""Per-operation metrics tracking."""
import time

class OperationMetrics:
    """Track tokens and time per operation."""
    
    def __init__(self):
        self.operations = {}  # op_id -> metrics
    
    def start_operation(self, op_id: str, op_type: str):
        """Start tracking an operation."""
        self.operations[op_id] = {
            "type": op_type,
            "start_time": time.time(),
            "tokens_in": 0,
            "tokens_out": 0,
            "model": "",
        }
    
    def end_operation(self, op_id: str, tokens_in: int, tokens_out: int, model: str):
        """End tracking and record metrics."""
        if op_id in self.operations:
            op = self.operations[op_id]
            op["duration"] = time.time() - op["start_time"]
            op["tokens_in"] = tokens_in
            op["tokens_out"] = tokens_out
            op["model"] = model
    
    def format_summary(self, op_id: str) -> str:
        """Format operation summary like Claude Code.
        
        Example: "3m 49s · ↑ 754 tokens · deepseek-chat"
        """
        if op_id not in self.operations:
            return ""
        
        op = self.operations[op_id]
        duration = op.get("duration", 0)
        tokens_total = op.get("tokens_in", 0) + op.get("tokens_out", 0)
        model = op.get("model", "")
        
        # Format duration
        if duration < 60:
            duration_str = f"{duration:.0f}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_str = f"{minutes}m {seconds}s"
        
        # Format tokens with direction arrow
        tokens_str = f"↑ {tokens_total:,} tokens" if tokens_total > 0 else ""
        
        parts = [duration_str, tokens_str, model]
        return " · ".join(filter(None, parts))
```

### Integration Points
- `AgentIntegration.run_agent()` - Start/end operation tracking
- Tool execution - Track tool-specific metrics
- Agent spawning - Track agent-specific metrics

---

## Phase 4: Expandable Tool Output

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/expandable_tool.py`

```python
"""Expandable tool output with ctrl+o hints."""

class ExpandableToolOutput:
    """Tool output that can be expanded/collapsed.
    
    Example (collapsed):
    ⎿  Searching for 1 pattern, reading 1 file… (ctrl+o to expand)
    
    Example (expanded):
    ⎿  $ grep -r "tool_use" packages/
       packages/lyra-cli/src/lyra_cli/cli/agent_integration.py:    tool_use
       packages/lyra-cli/src/lyra_cli/eager_tools/executor.py:    tool_use
    """
    
    def __init__(self, tool_name: str, output: str):
        self.tool_name = tool_name
        self.output = output
        self.expanded = False
        self.block_id = f"tool_{id(self)}"
    
    def render_collapsed(self) -> str:
        """Render collapsed view with hint."""
        summary = self._summarize_output()
        return f"⎿  {summary} (ctrl+o to expand)"
    
    def render_expanded(self) -> str:
        """Render full output."""
        lines = self.output.split("\n")
        if len(lines) > 20:
            lines = lines[:20] + ["... (truncated)"]
        return "\n".join(f"   {line}" for line in lines)
    
    def _summarize_output(self) -> str:
        """Create one-line summary of tool output."""
        lines = self.output.split("\n")
        if len(lines) == 1:
            return lines[0][:80]
        return f"{self.tool_name} ({len(lines)} lines)"
```

### Integration Points
- `ExpandableBlockManager` - Register tool outputs
- Tool execution completion - Create expandable block
- Ctrl+O handler - Toggle expansion

---

## Phase 5: Background Task Panel

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/background_panel.py`

```python
"""Background task panel like Claude Code."""

class BackgroundTaskPanel:
    """Shows background tasks with status.
    
    Example:
    ⏵⏵ bypass permissions on · 5 background tasks · esc to interrupt · ctrl+t
    
      ⏺ main                                           ↑/↓ to select · Enter to view
      ◯ general-purpose  Deep research: Kilo, Hermes…  3m 4s · ↓ 63.6k tokens
      ◯ general-purpose  Verify model diversity…       3m 3s · ↓ 102.2k tokens
    """
    
    def __init__(self):
        self.tasks = {}  # task_id -> TaskStatus
        self.selected_index = 0
    
    def add_task(self, task_id: str, description: str, agent_type: str):
        """Add background task."""
        self.tasks[task_id] = {
            "description": description,
            "agent_type": agent_type,
            "start_time": time.time(),
            "tokens": 0,
            "status": "running",
        }
    
    def render(self) -> str:
        """Render background task panel."""
        if not self.tasks:
            return ""
        
        header = f"⏵⏵ bypass permissions on · {len(self.tasks)} background tasks · "
        header += "esc to interrupt · ctrl+t"
        
        lines = [header, ""]
        lines.append("  ⏺ main                                           ↑/↓ to select · Enter to view")
        
        for i, (task_id, task) in enumerate(self.tasks.items()):
            selected = "⏺" if i == self.selected_index else "◯"
            duration = time.time() - task["start_time"]
            duration_str = f"{int(duration//60)}m {int(duration%60)}s"
            tokens_str = f"↓ {task['tokens']/1000:.1f}k tokens"
            
            line = f"  {selected} {task['agent_type']}  {task['description'][:40]}…  "
            line += f"{duration_str} · {tokens_str}"
            lines.append(line)
        
        return "\n".join(lines)
```

### Integration Points
- `LyraHarnessApp._bg_tasks` - Track background tasks
- Ctrl+B handler - Show/hide background panel
- Background task events - Update task status

---

## Phase 6: Thinking Time Display

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/thinking_indicator.py`

```python
"""Thinking time indicator."""

class ThinkingIndicator:
    """Shows thinking time like Claude Code.
    
    Example: "✶ Roosting… (2m 53s · ↓ 2.6k tokens · thought for 28s)"
    """
    
    def __init__(self):
        self.thinking_start = None
        self.thinking_duration = 0
    
    def start_thinking(self):
        """Mark start of thinking phase."""
        self.thinking_start = time.time()
    
    def end_thinking(self):
        """Mark end of thinking phase."""
        if self.thinking_start:
            self.thinking_duration = time.time() - self.thinking_start
            self.thinking_start = None
    
    def format(self, total_duration: float, tokens: int) -> str:
        """Format thinking indicator."""
        if self.thinking_duration == 0:
            return ""
        
        duration_str = f"{int(total_duration//60)}m {int(total_duration%60)}s"
        tokens_str = f"↓ {tokens/1000:.1f}k tokens"
        thinking_str = f"thought for {int(self.thinking_duration)}s"
        
        return f"✶ Roosting… ({duration_str} · {tokens_str} · {thinking_str})"
```

### Integration Points
- Extended thinking mode - Track thinking time
- LLM streaming - Detect thinking vs output phases
- Status line - Show thinking indicator

---

## Phase 7: Phase/Step Progress

### Implementation
**File**: `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/phase_progress.py`

```python
"""Phase/step progress tracking."""

class PhaseProgress:
    """Track multi-phase task progress.
    
    Example:
    ✶ Galloping… (32s · ↓ 20 tokens)
      ⎿  ◻ Phase 9: Production Readiness
         ◻ Phase 3: Implement Research Pipeline
         ◻ Phase 6: Interactive UI & Themes
         ◻ Phase 5: Memory Systems
         ◻ Phase 2: Integrate Real Agent Loop
          … +3 pending
    """
    
    def __init__(self):
        self.phases = []  # List of (name, status)
    
    def add_phase(self, name: str, status: str = "pending"):
        """Add a phase to track."""
        self.phases.append({"name": name, "status": status})
    
    def update_phase(self, name: str, status: str):
        """Update phase status."""
        for phase in self.phases:
            if phase["name"] == name:
                phase["status"] = status
                break
    
    def render(self, max_visible: int = 5) -> str:
        """Render phase progress."""
        if not self.phases:
            return ""
        
        lines = []
        visible_phases = self.phases[:max_visible]
        
        for phase in visible_phases:
            icon = "✓" if phase["status"] == "completed" else "◻"
            lines.append(f"     {icon} {phase['name']}")
        
        remaining = len(self.phases) - max_visible
        if remaining > 0:
            lines.append(f"      … +{remaining} pending")
        
        return "\n".join(lines)
```

### Integration Points
- Multi-phase tasks (research, implementation) - Track phases
- Task completion events - Update phase status
- Status display - Show phase progress

---

## Implementation Priority

### Week 1: Core Progress Indicators
1. ✅ Real-time progress spinners (Phase 1)
2. ✅ Token & time tracking per operation (Phase 3)
3. ✅ Thinking time display (Phase 6)

### Week 2: Agent & Task Visibility
4. ✅ Parallel agent execution display (Phase 2)
5. ✅ Background task panel (Phase 5)
6. ✅ Phase/step progress (Phase 7)

### Week 3: Polish & Integration
7. ✅ Expandable tool output (Phase 4)
8. ✅ Integration testing
9. ✅ Documentation

---

## Testing Plan

### E2E Test Scenarios
1. **Simple query** - Verify spinner, tokens, time display
2. **Multi-tool query** - Verify tool output expansion
3. **Parallel agents** - Verify agent panel display
4. **Background tasks** - Verify background panel
5. **Long-running task** - Verify phase progress
6. **Thinking mode** - Verify thinking time display

### Manual Testing Checklist
- [ ] Spinner animates smoothly
- [ ] Token counts update in real-time
- [ ] Time tracking accurate
- [ ] Ctrl+O expands/collapses tool output
- [ ] Agent panel shows all running agents
- [ ] Background panel accessible via Ctrl+B
- [ ] Phase progress updates correctly
- [ ] Thinking time displays when enabled

---

## Success Metrics

### User Experience
- **Visibility**: Users can see what Lyra is doing at all times
- **Engagement**: Progress indicators make waiting feel shorter
- **Control**: Users can expand/collapse details as needed
- **Confidence**: Clear status reduces uncertainty

### Performance
- **Spinner update**: <10ms per frame
- **Panel render**: <50ms per update
- **Memory overhead**: <10MB for all tracking

---

## Next Steps

1. Create widget files in `packages/lyra-cli/src/lyra_cli/tui_v2/widgets/`
2. Integrate widgets into `LyraHarnessApp`
3. Add event handlers for progress updates
4. Test with real workloads
5. Gather user feedback
6. Iterate based on feedback
