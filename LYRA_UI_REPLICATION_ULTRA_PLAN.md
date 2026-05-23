# Lyra UI Replication Ultra Plan
**Goal**: Replicate Claude Code's complete UI response format patterns in Lyra

**Based on**: 
- `CLAUDE_CODE_RESPONSE_FORMAT_SPECIFICATION.md` (752 lines)
- `CLAUDE_CODE_UI_QUICK_REFERENCE.md` (184 lines)
- Current Lyra UI implementation analysis

---

## Current State Analysis

### ✅ Already Implemented
- Symbol registry with Unicode characters
- Color engine with ANSI codes
- Layout engine with responsive breakpoints
- Tree renderer with box-drawing characters
- Tool call formatter
- Welcome banner (basic)
- Expandable sections

### ❌ Missing Components
1. **Fixed bottom UI** (input + status line)
2. **Streaming response renderer** with proper symbols
3. **Agent tree display** (collapsed/expanded)
4. **Interactive selection menus** (model picker, etc.)
5. **Background tasks panel**
6. **Event-driven architecture** (AG-UI protocol)
7. **Stats line** with token/time tracking
8. **Proper scrollable area** management

---

## Phase 1: Event Protocol & Streaming Foundation
**Duration**: 2-3 hours

### 1.1 Event System
Create `packages/lyra-cli/src/lyra_cli/events/protocol.py`:

```python
from pydantic import BaseModel
from typing import Literal

class TurnStarted(BaseModel):
    type: Literal["turn.started"] = "turn.started"
    turn_id: str
    user_text: str

class ThinkingDelta(BaseModel):
    type: Literal["thinking.delta"] = "thinking.delta"
    turn_id: str
    text: str

class TextDelta(BaseModel):
    type: Literal["text.delta"] = "text.delta"
    turn_id: str
    text: str

class ToolStarted(BaseModel):
    type: Literal["tool.started"] = "tool.started"
    turn_id: str
    call_id: str
    name: str
    input: dict

class ToolFinished(BaseModel):
    type: Literal["tool.finished"] = "tool.finished"
    call_id: str
    status: Literal["ok", "error", "denied", "canceled"]
    duration_ms: int
    tokens_in: int
    tokens_out: int

class TurnFinished(BaseModel):
    type: Literal["turn.finished"] = "turn.finished"
    turn_id: str
    tokens_in: int
    tokens_out: int
    stop_reason: str
```

### 1.2 Streaming Renderer
Create `packages/lyra-cli/src/lyra_cli/ui/streaming.py`:

```python
class StreamingRenderer:
    """Append-only streaming renderer (no flicker)"""
    
    def __init__(self):
        self.buffer: list[str] = []
        self.current_line = ""
    
    def append_delta(self, text: str):
        """Append text without re-rendering entire buffer"""
        self.current_line += text
        print(text, end="", flush=True)
    
    def finalize_line(self):
        """Complete current line"""
        self.buffer.append(self.current_line)
        self.current_line = ""
        print()  # New line
```

**Deliverables**:
- [ ] Event protocol with Pydantic models
- [ ] Streaming renderer with append-only buffer
- [ ] Event dispatcher/consumer
- [ ] Unit tests for event flow

---

## Phase 2: Fixed Bottom UI (Input + Status)
**Duration**: 3-4 hours

### 2.1 Fixed Input Box
Create `packages/lyra-cli/src/lyra_cli/ui/fixed_input.py`:

```python
class FixedInputBox:
    """Input box that stays at bottom during streaming"""
    
    def __init__(self, console):
        self.console = console
        self.height = 4  # divider + input + divider + status
    
    def render(self, prompt_text: str = ""):
        """Render input box at bottom"""
        # Save cursor, move to bottom, render, restore cursor
        rows = self.console.height
        
        # Top divider
        print(f"\033[{rows - 3};1H" + "─" * self.console.width)
        
        # Input line
        print(f"\033[{rows - 2};1H❯ {prompt_text}")
        
        # Bottom divider
        print(f"\033[{rows - 1};1H" + "─" * self.console.width)
```

### 2.2 Status Line
Create `packages/lyra-cli/src/lyra_cli/ui/status_line.py`:

```python
class StatusLine:
    """Fixed status line below input"""
    
    def update(self, mode: str, hints: list[str]):
        """Update status line content"""
        status = f"  ⏵⏵ {mode}"
        if hints:
            status += " · " + " · ".join(hints)
        
        # Render with inverse colors
        print(f"\033[7m{status}\033[0m")
```

**Deliverables**:
- [ ] Fixed input box with ANSI positioning
- [ ] Status line with mode/hints
- [ ] Keyboard shortcut hints
- [ ] Integration with main REPL

---

## Phase 3: Response Format Patterns
**Duration**: 4-5 hours

### 3.1 Active Response Indicator
Update `packages/lyra-cli/src/lyra_cli/ui/renderer.py`:

```python
def render_active_response(self, message: str) -> str:
    """⏺ Active response indicator"""
    return f"{self.colors.yellow('⏺')} {message}"

def render_stats_line(
    self, 
    duration_s: float, 
    tool_count: int, 
    tokens: int
) -> str:
    """✻ Stats line after completion"""
    time_str = f"{duration_s:.1f}s"
    stats = f"{time_str} · {tool_count} tools · {tokens:,} tokens"
    return f"{self.colors.dim('✻')} {self.colors.dim(stats)}"
```

### 3.2 Tool Call Display
```python
def render_tool_call(
    self, 
    tool_name: str, 
    description: str,
    collapsed: bool = True
) -> str:
    """⎿ Tool call indicator"""
    line = f"  {self.colors.dim('⎿')}  {tool_name}"
    if description:
        line += f" {self.colors.dim(description)}"
    
    if not collapsed:
        line += f" {self.colors.dim('(ctrl+o to collapse)')}"
    
    return line
```

**Deliverables**:
- [ ] Active response indicator (⏺)
- [ ] Stats line formatter (✻)
- [ ] Tool call display (⎿)
- [ ] Thinking indicator (✶)
- [ ] Integration with streaming renderer

---

## Phase 4: Agent Tree Display
**Duration**: 3-4 hours

### 4.1 Agent Tree Renderer
Create `packages/lyra-cli/src/lyra_cli/ui/agent_tree.py`:

```python
class AgentTree:
    """Hierarchical agent display with collapse/expand"""
    
    def __init__(self):
        self.agents: dict[str, AgentNode] = {}
        self.expanded = False
    
    def render(self) -> str:
        if not self.expanded:
            count = len([a for a in self.agents.values() 
                        if a.status == "running"])
            return f"⏺ Running {count} agents… (ctrl+o to expand)"
        
        # Render tree with box-drawing
        lines = ["⏺ Running agents… (ctrl+o to collapse)"]
        for i, (agent_id, node) in enumerate(self.agents.items()):
            is_last = (i == len(self.agents) - 1)
            connector = "└" if is_last else "├"
            
            line = f"   {connector} {node.name} · "
            line += f"{node.tool_count} tool uses · "
            line += f"{node.tokens:,} tokens"
            lines.append(line)
            
            # Show latest tool call
            if node.latest_tool:
                tool_line = f"   │ ⎿  {node.latest_tool}"
                lines.append(tool_line)
        
        return "\n".join(lines)
```

**Deliverables**:
- [ ] Agent tree data structure
- [ ] Collapsed/expanded rendering
- [ ] Box-drawing connectors
- [ ] Token rollup display
- [ ] Keyboard toggle (ctrl+o)

---

## Phase 5: Interactive Selection Menus
**Duration**: 3-4 hours

### 5.1 Selection Menu Widget
Create `packages/lyra-cli/src/lyra_cli/ui/selection_menu.py`:

```python
class SelectionMenu:
    """Interactive selection menu (model picker, etc.)"""
    
    def __init__(self, title: str, options: list[MenuOption]):
        self.title = title
        self.options = options
        self.selected_index = 0
    
    def render(self) -> str:
        width = 80
        lines = []
        
        # Top divider
        lines.append("─" * width)
        
        # Title
        lines.append(f"  {self.title}")
        lines.append("")
        
        # Options
        for i, option in enumerate(self.options):
            prefix = "❯" if i == self.selected_index else " "
            suffix = "✔" if option.active else ""
            
            line = f"  {prefix} {i+1}. {option.label}"
            if suffix:
                line += f" {suffix}"
            
            lines.append(line)
        
        lines.append("")
        lines.append("  Enter to confirm · Esc to cancel")
        lines.append("─" * width)
        
        return "\n".join(lines)
    
    def handle_key(self, key: str):
        """Handle keyboard input"""
        if key == "up":
            self.selected_index = max(0, self.selected_index - 1)
        elif key == "down":
            self.selected_index = min(
                len(self.options) - 1, 
                self.selected_index + 1
            )
```

**Deliverables**:
- [ ] Selection menu widget
- [ ] Keyboard navigation (↑↓)
- [ ] Model picker implementation
- [ ] Background tasks panel
- [ ] Modal overlay system

---

## Phase 6: Scrollable Area Management
**Duration**: 2-3 hours

### 6.1 Scroll Manager
Create `packages/lyra-cli/src/lyra_cli/ui/scroll_manager.py`:

```python
class ScrollManager:
    """Manage scrollable content area above fixed UI"""
    
    def __init__(self, console):
        self.console = console
        self.fixed_height = 4  # Input + status
        self.scroll_offset = 0
        self.content_lines: list[str] = []
    
    def get_visible_height(self) -> int:
        """Calculate visible area height"""
        return self.console.height - self.fixed_height
    
    def append_line(self, line: str):
        """Append line and auto-scroll to bottom"""
        self.content_lines.append(line)
        
        # Auto-scroll to bottom
        visible_height = self.get_visible_height()
        if len(self.content_lines) > visible_height:
            self.scroll_offset = len(self.content_lines) - visible_height
    
    def render_visible_area(self):
        """Render only visible lines"""
        visible_height = self.get_visible_height()
        start = self.scroll_offset
        end = start + visible_height
        
        visible_lines = self.content_lines[start:end]
        
        for i, line in enumerate(visible_lines):
            print(f"\033[{i+1};1H{line}")
```

**Deliverables**:
- [ ] Scroll manager with offset tracking
- [ ] Auto-scroll to bottom on new content
- [ ] User scroll with preserved position
- [ ] Virtualized rendering (only visible lines)

---

## Phase 7: Welcome Banner Enhancement
**Duration**: 2 hours

### 7.1 Two-Column Layout
Update `packages/lyra-cli/src/lyra_cli/ui/welcome_banner.py`:

```python
def render_welcome_banner_wide(
    version: str,
    model: str,
    user_name: str,
    working_dir: str,
    width: int = 120
) -> str:
    """Two-column layout for wide terminals (>120 cols)"""
    
    # Left column: ASCII art + greeting
    left_col = [
        f"Welcome back {user_name}!",
        "",
        "  ╦  ╦ ╦ ╦═╗ ╔═╗",
        "  ║  ╚╦╝ ╠╦╝ ╠═╣",
        "  ╩═╝ ╩  ╩╚═ ╩ ╩",
        "",
        f"{model}",
        working_dir
    ]
    
    # Right column: Tips + What's new
    right_col = [
        "Tips for getting started",
        "Run /help for commands",
        "─" * 20,
        "What's new",
        "Beautiful responsive UI",
        "/release-notes for more"
    ]
    
    # Combine columns
    lines = []
    for i in range(max(len(left_col), len(right_col))):
        left = left_col[i] if i < len(left_col) else ""
        right = right_col[i] if i < len(right_col) else ""
        
        # Pad left column to 50 chars
        left_padded = left.ljust(50)
        line = f"│ {left_padded} │ {right}"
        lines.append(line)
    
    # Add borders
    top = f"╭{'─' * (width - 2)}╮"
    bottom = f"╰{'─' * (width - 2)}╯"
    
    return "\n".join([top] + lines + [bottom])
```

**Deliverables**:
- [ ] Two-column layout for wide terminals
- [ ] Single-column for narrow terminals
- [ ] Responsive breakpoints (80, 120 cols)
- [ ] Tips + What's new sections

---

## Phase 8: Integration & Testing
**Duration**: 3-4 hours

### 8.1 Main REPL Integration
Update `packages/lyra-cli/src/lyra_cli/cli.py`:

```python
from lyra_cli.ui import (
    StreamingRenderer,
    FixedInputBox,
    StatusLine,
    AgentTree,
    ScrollManager
)
from lyra_cli.events import EventDispatcher

class LyraREPL:
    """Main REPL with Claude Code-style UI"""
    
    def __init__(self):
        self.console = Console()
        self.streaming = StreamingRenderer()
        self.input_box = FixedInputBox(self.console)
        self.status_line = StatusLine(self.console)
        self.agent_tree = AgentTree()
        self.scroll_manager = ScrollManager(self.console)
        self.event_dispatcher = EventDispatcher()
    
    def run(self):
        """Main REPL loop"""
        # Show welcome banner
        self.show_welcome()
        
        while True:
            # Render fixed UI
            self.input_box.render()
            self.status_line.update("default", ["esc to exit"])
            
            # Get user input
            user_input = self.get_input()
            
            if user_input == "/exit":
                break
            
            # Process input and stream response
            self.process_input(user_input)
```

### 8.2 Testing Checklist
- [ ] Event flow: TurnStarted → TextDelta → TurnFinished
- [ ] Streaming without flicker
- [ ] Fixed input stays at bottom
- [ ] Status line updates correctly
- [ ] Agent tree collapse/expand
- [ ] Selection menu navigation
- [ ] Scroll behavior
- [ ] Terminal resize handling
- [ ] Welcome banner responsive layouts

---

## Phase 9: Performance Optimization
**Duration**: 2 hours

### 9.1 Optimizations
- [ ] Virtualized scrolling (only render visible lines)
- [ ] Diff-based updates (only changed regions)
- [ ] Debounced terminal resize (100ms)
- [ ] Buffer limits (cap at 10,000 lines)
- [ ] Lazy loading of old messages

### 9.2 Latency Targets
- First paint: ≤ 50ms
- Token-to-screen: ≤ 16ms
- Scroll repaint: ≤ 2ms per frame
- Input responsiveness: ≤ 10ms

---

## Phase 10: Documentation & Examples
**Duration**: 2 hours

### 10.1 Documentation
- [ ] API documentation for all UI components
- [ ] Event protocol specification
- [ ] Integration guide
- [ ] Performance tuning guide

### 10.2 Examples
- [ ] Simple streaming example
- [ ] Agent tree example
- [ ] Selection menu example
- [ ] Full REPL example

---

## Implementation Order

1. **Phase 1**: Event Protocol (foundation)
2. **Phase 2**: Fixed Bottom UI (critical UX)
3. **Phase 3**: Response Patterns (core formatting)
4. **Phase 6**: Scrollable Area (layout management)
5. **Phase 4**: Agent Tree (advanced feature)
6. **Phase 5**: Selection Menus (interactive)
7. **Phase 7**: Welcome Banner (polish)
8. **Phase 8**: Integration (bring it together)
9. **Phase 9**: Performance (optimization)
10. **Phase 10**: Documentation (finalize)

---

## Success Criteria

### Visual Parity
- [ ] Welcome banner matches Claude Code layout
- [ ] Response symbols match (⏺ ✻ ✶ ⎿ ❯)
- [ ] Agent tree rendering matches
- [ ] Selection menus match
- [ ] Status line matches
- [ ] Color scheme matches

### Functional Parity
- [ ] Streaming without flicker
- [ ] Fixed input at bottom
- [ ] Scrollable content area
- [ ] Agent tree collapse/expand
- [ ] Selection menu navigation
- [ ] Terminal resize handling

### Performance
- [ ] First paint < 50ms
- [ ] Token-to-screen < 16ms
- [ ] Smooth scrolling
- [ ] No memory leaks

---

## Estimated Total Time
**25-30 hours** (3-4 days of focused work)

---

## Next Steps

1. Review this plan with user
2. Get approval to proceed
3. Start with Phase 1 (Event Protocol)
4. Implement phases sequentially
5. Test after each phase
6. Push to main after each phase completion

---

**Ready to start implementation?**
