# Lyra Interactive Features Roadmap

**Version**: 1.0  
**Date**: 2026-05-29  
**Status**: Design Proposal

## Overview

This document defines interactive features for Lyra's terminal interface, inspired by Hermes Agent's progressive disclosure philosophy and modern TUI best practices. Features are organized by priority and implementation complexity.

## Design Principles

1. **Instant responsiveness** - First frame paints before app finishes loading
2. **Non-blocking input** - Type and queue messages before session ready
3. **Progressive disclosure** - Show relevant info, hide noise
4. **Mouse-friendly** - Drag-to-select, click-to-toggle, scroll-to-navigate
5. **Keyboard-first** - All features accessible via keyboard

## Priority 1: Core Interactive Features (MVP)

### 1.1 Status Bar with Live Updates

**Description**: Persistent status bar showing real-time session information

**Layout**:
```
⚕ claude-sonnet-4 │ 12.4K/200K │ [██████░░░░] 6% │ $0.06 │ 15m │ 🗜️ 2 │ ▶ 1
```

**Elements**:
- **Model icon + name**: Click to open model picker
- **Token usage**: Current/total with click for detailed breakdown
- **Progress bar**: Visual indicator with color coding
  - Green: <50% context usage
  - Yellow: 50-80%
  - Orange: 80-95%
  - Red: ≥95%
- **Cost estimate**: Click for cost breakdown by model/operation
- **Duration**: Session elapsed time
- **Compression count**: `🗜️ N` - Number of context compressions
- **Background tasks**: `▶ N` - Active background tasks
- **Special indicators**: `⚠ YOLO` when auto-approve enabled

**Implementation**:
```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn

class StatusBar:
    def __init__(self):
        self.console = Console()
        self.model = "claude-sonnet-4"
        self.tokens_used = 12400
        self.tokens_total = 200000
        self.cost = 0.06
        self.duration = 900  # seconds
        self.compressions = 2
        self.background_tasks = 1
    
    def render(self) -> Table:
        """Render status bar as Rich table"""
        table = Table.grid(padding=(0, 1))
        
        # Model
        table.add_column(style="bold cyan")
        table.add_row(f"⚕ {self.model}")
        
        # Token usage
        usage_pct = (self.tokens_used / self.tokens_total) * 100
        color = self._get_usage_color(usage_pct)
        table.add_column(style=color)
        table.add_row(f"{self.tokens_used/1000:.1f}K/{self.tokens_total/1000}K")
        
        # Progress bar
        table.add_column()
        progress = self._render_progress_bar(usage_pct)
        table.add_row(progress)
        
        # Cost
        table.add_column(style="green")
        table.add_row(f"${self.cost:.2f}")
        
        # Duration
        table.add_column(style="yellow")
        table.add_row(self._format_duration(self.duration))
        
        # Indicators
        if self.compressions > 0:
            table.add_column()
            table.add_row(f"🗜️ {self.compressions}")
        
        if self.background_tasks > 0:
            table.add_column()
            table.add_row(f"▶ {self.background_tasks}")
        
        return table
    
    def _get_usage_color(self, pct: float) -> str:
        if pct < 50: return "green"
        if pct < 80: return "yellow"
        if pct < 95: return "orange"
        return "red"
    
    def _render_progress_bar(self, pct: float) -> str:
        filled = int(pct / 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}] {pct:.0f}%"
    
    def _format_duration(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        else:
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
```

### 1.2 Multiline Input with Editor Integration

**Description**: Rich text input with multiline support and external editor

**Features**:
- `Alt+Enter` / `Ctrl+J` / `Shift+Enter` for newlines
- Backslash continuation: end line with `\`
- `Ctrl+G` or `Ctrl+X Ctrl+E` opens `$EDITOR`
- Paste preview: `[pasted: 47 lines, 1,842 chars — press Enter to send]`
- Syntax highlighting for code blocks
- Auto-indent for code

**Implementation**:
```python
from textual.widgets import TextArea
from textual.binding import Binding

class LyraInput(TextArea):
    BINDINGS = [
        Binding("alt+enter", "newline", "Newline"),
        Binding("ctrl+j", "newline", "Newline"),
        Binding("ctrl+g", "open_editor", "Editor"),
        Binding("ctrl+x,ctrl+e", "open_editor", "Editor"),
    ]
    
    def action_newline(self):
        """Insert newline without submitting"""
        self.insert("\n")
    
    def action_open_editor(self):
        """Open input in external editor"""
        import tempfile
        import subprocess
        import os
        
        editor = os.environ.get("EDITOR", "vim")
        
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as f:
            f.write(self.text)
            f.flush()
            
            subprocess.run([editor, f.name])
            
            with open(f.name) as edited:
                self.text = edited.read()
            
            os.unlink(f.name)
    
    def on_paste(self, event):
        """Handle paste with preview"""
        text = event.text
        lines = text.count('\n') + 1
        chars = len(text)
        
        if lines > 5 or chars > 200:
            self.app.notify(
                f"[pasted: {lines} lines, {chars} chars — press Enter to send]",
                severity="information"
            )
```

### 1.3 Collapsible Sections

**Description**: Accordion-style sections for tools, thinking, activity

**Sections**:
- **Tools** (expanded by default)
- **Thinking** (collapsed by default)
- **Activity** (collapsed by default)
- **System Prompt** (collapsed by default)
- **MCP Servers** (collapsed by default)

**Interaction**:
- Click header or chevron (`▸/▾`) to toggle
- Keyboard: `Tab` to focus, `Space` to toggle
- Slash command: `/details tools expanded`

**Implementation**:
```python
from textual.widgets import Collapsible
from textual.containers import Container

class CollapsibleSection(Collapsible):
    def __init__(self, title: str, content: str, collapsed: bool = False):
        super().__init__(title=title, collapsed=collapsed)
        self.content = content
    
    def compose(self):
        yield Container(self.content)

class LyraApp(App):
    def compose(self):
        yield CollapsibleSection("🛠️ Tools", self.render_tools(), collapsed=False)
        yield CollapsibleSection("🧠 Thinking", self.render_thinking(), collapsed=True)
        yield CollapsibleSection("📊 Activity", self.render_activity(), collapsed=True)
        yield CollapsibleSection("📝 System Prompt", self.render_prompt(), collapsed=True)
        yield CollapsibleSection("🔌 MCP Servers", self.render_mcp(), collapsed=True)
```

### 1.4 Live Session Switcher

**Description**: Modal overlay for switching between sessions

**Features**:
- `Ctrl+X` to open
- `↑/↓` or `j/k` for navigation
- `Enter` to switch
- `Ctrl+D` to close session
- `Ctrl+N` to create new
- `+new` row at bottom
- Shows session metadata: title, duration, message count, model

**Implementation**:
```python
from textual.screen import ModalScreen
from textual.widgets import ListView, ListItem, Label

class SessionSwitcher(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
        Binding("ctrl+d", "close_session", "Close"),
        Binding("ctrl+n", "new_session", "New"),
    ]
    
    def compose(self):
        sessions = self.app.session_manager.list_sessions()
        
        items = []
        for session in sessions:
            label = f"{session.title} │ {session.duration} │ {session.messages} msgs │ {session.model}"
            items.append(ListItem(Label(label), id=session.id))
        
        items.append(ListItem(Label("+ New Session"), id="new"))
        
        yield ListView(*items)
    
    def on_list_view_selected(self, event):
        if event.item.id == "new":
            self.app.create_session()
        else:
            self.app.switch_session(event.item.id)
        self.dismiss()
```

### 1.5 Busy Indicators with Kaomoji

**Description**: Cute animated indicators during agent activity

**Styles**: `kaomoji | emoji | unicode | ascii`

**Kaomoji rotation** (every 2.5 seconds):
```python
KAOMOJI_FRAMES = [
    "(｡◕‿◕｡)",      # Happy
    "(づ｡◕‿‿◕｡)づ",  # Excited
    "( ˶ˆᗜˆ˵ )",    # Cute
    "ʕ •ᴥ•ʔ",       # Bear
    "(っ◔◡◔)っ",     # Hug
    "( ´ ▽ ` )",    # Pleased
    "(◕‿◕)",        # Simple smile
    "ヾ(＾-＾)ノ",     # Wave
]

class BusyIndicator:
    def __init__(self, style: str = "kaomoji"):
        self.style = style
        self.frame = 0
        self.start_time = time.time()
    
    def render(self) -> str:
        elapsed = time.time() - self.start_time
        
        if self.style == "kaomoji":
            self.frame = int(elapsed / 2.5) % len(KAOMOJI_FRAMES)
            return KAOMOJI_FRAMES[self.frame]
        elif self.style == "emoji":
            return "🤔💭✨🎯"[self.frame % 4]
        elif self.style == "unicode":
            return "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[self.frame % 10]
        else:  # ascii
            return "|/-\\"[self.frame % 4]
```

## Priority 2: Enhanced UX Features

### 2.1 Tool Execution Feed

**Description**: Real-time feed of tool executions with timing

**Format**:
```
┊ 💻 terminal `ls -la` (0.3s)
┊ 🔍 web_search "Python async patterns" (1.2s)
┊ 📝 write_file src/main.py (0.1s)
┊ ✅ test_runner pytest (5.4s)
```

**Features**:
- Icon per tool type
- Command preview (truncated if long)
- Execution time
- Click to expand full output
- Color coding: green (success), red (error), yellow (warning)

### 2.2 Context Compression Visualization

**Description**: Visual indicator when context is compressed

**Features**:
- Warning before compression: "Context at 85%, compression in 15%"
- Progress bar during compression
- Summary after: "Compressed 50K → 15K tokens (70% reduction)"
- `🗜️ N` indicator in status bar
- Click to see compression details

### 2.3 Background Task Manager

**Description**: Panel showing active background tasks

**Features**:
- List of running tasks with progress
- Click to view output
- Click to cancel
- Notification when complete
- `▶ N` indicator in status bar

**Implementation**:
```python
from textual.widgets import DataTable

class BackgroundTaskPanel(DataTable):
    def __init__(self):
        super().__init__()
        self.add_columns("Task", "Progress", "Duration", "Actions")
    
    def add_task(self, task_id: str, description: str):
        self.add_row(
            description,
            "[░░░░░░░░░░] 0%",
            "0s",
            "Cancel"
        )
    
    def update_task(self, task_id: str, progress: float, duration: int):
        # Update row with new progress
        pass
    
    def on_row_selected(self, event):
        # Show task output
        pass
```

### 2.4 Slash Command Autocomplete

**Description**: Fuzzy autocomplete for slash commands

**Features**:
- Type `/` to trigger
- Fuzzy matching: `/mod` → `/model`
- Show command description
- Show recent commands
- Arrow keys to navigate
- `Tab` to complete
- `Enter` to execute

**Implementation**:
```python
from textual.widgets import Input
from textual.suggester import Suggester

class SlashCommandSuggester(Suggester):
    def __init__(self, commands: List[str]):
        self.commands = commands
    
    async def get_suggestion(self, value: str) -> str | None:
        if not value.startswith('/'):
            return None
        
        query = value[1:].lower()
        for cmd in self.commands:
            if cmd.startswith(query):
                return '/' + cmd
        
        return None

class LyraInput(Input):
    def __init__(self):
        commands = [
            "help", "model", "tools", "skills", "background",
            "voice", "reasoning", "title", "status", "sessions"
        ]
        super().__init__(suggester=SlashCommandSuggester(commands))
```

### 2.5 Model Picker Modal

**Description**: Interactive model selection overlay

**Features**:
- `Alt+M` or click model name to open
- List of available models with metadata
- Show cost per 1M tokens
- Show context window size
- Show capabilities (vision, tools, thinking)
- Arrow keys to navigate
- `Enter` to select
- Preview mode: see model info before switching

### 2.6 Search in Transcript

**Description**: Full-text search in current session

**Features**:
- `Ctrl+F` to open search bar
- Fuzzy matching
- Highlight all matches
- `n/N` for next/previous
- Show match count: "3 of 15"
- Regex support with `/regex/` syntax
- Case-sensitive toggle

### 2.7 History Browser

**Description**: Browse and reuse previous prompts

**Features**:
- `Ctrl+H` to open
- List of last 50 prompts
- Fuzzy search
- Click to insert into input
- Show timestamp and session
- Star favorites
- Delete unwanted entries

### 2.8 LaTeX Math Rendering

**Description**: Render LaTeX math as Unicode

**Features**:
- Inline: `$E = mc^2$` → E = mc²
- Block: `$$\frac{a}{b}$$` → formatted fraction
- Fallback to code span if unsupported
- Click to copy LaTeX source

## Priority 3: Advanced Features

### 3.1 Split View Mode

**Description**: Side-by-side view of code and chat

**Features**:
- `Ctrl+\` to toggle split
- Left: code editor
- Right: chat transcript
- Synchronized scrolling
- Click file path to open in editor
- Diff view for code changes

### 3.2 Agent Activity Timeline

**Description**: Visual timeline of agent actions

**Features**:
- Horizontal timeline with events
- Color-coded by type (thinking, tool, response)
- Hover for details
- Click to jump to message
- Zoom in/out
- Export as image

### 3.3 Token Usage Breakdown

**Description**: Detailed token usage analytics

**Features**:
- Click token count in status bar
- Pie chart: input vs output vs thinking
- Bar chart: tokens per message
- Cost breakdown by model
- Projection: "At this rate, session will cost $X"
- Export as CSV

### 3.4 Quick Commands System

**Description**: User-defined command shortcuts

**Features**:
- Define in `~/.lyra/config.yaml`
- Execute with `Ctrl+Q` or `/quick`
- Shell commands or slash command aliases
- Variables: `{session_id}`, `{model}`, `{date}`
- Confirmation prompt for destructive commands

**Example**:
```yaml
quick_commands:
  status:
    type: exec
    command: "systemctl status lyra-agent"
  restart:
    type: alias
    target: "/gateway restart"
  backup:
    type: exec
    command: "tar -czf backup-{date}.tar.gz ~/.lyra/"
    confirm: true
```

### 3.5 Session Templates

**Description**: Pre-configured session setups

**Features**:
- Create template from current session
- Save model, skills, system prompt, settings
- Load template when creating new session
- Share templates with team
- Template marketplace

### 3.6 Collaborative Sessions

**Description**: Share session with other users

**Features**:
- Generate shareable link
- Real-time collaboration
- See other users' cursors
- Chat sidebar
- Permission levels: view, comment, edit
- Session recording and playback

### 3.7 Plugin System

**Description**: Extend Lyra with custom plugins

**Features**:
- Python-based plugin API
- Hooks for all lifecycle events
- Custom slash commands
- Custom UI widgets
- Plugin marketplace
- Hot reload during development

### 3.8 Workspace Management

**Description**: Organize sessions into workspaces

**Features**:
- Create workspace per project
- Switch between workspaces
- Workspace-specific settings
- Shared context across sessions in workspace
- Workspace templates

## Implementation Roadmap

### Phase 1: MVP (Weeks 1-2)
- Status bar with live updates
- Multiline input with editor
- Collapsible sections
- Live session switcher
- Busy indicators

### Phase 2: Enhanced UX (Weeks 3-4)
- Tool execution feed
- Context compression visualization
- Background task manager
- Slash command autocomplete
- Model picker modal

### Phase 3: Power User (Weeks 5-6)
- Search in transcript
- History browser
- LaTeX math rendering
- Token usage breakdown
- Quick commands system

### Phase 4: Advanced (Weeks 7-8)
- Split view mode
- Agent activity timeline
- Session templates
- Workspace management

### Phase 5: Collaboration (Weeks 9-10)
- Collaborative sessions
- Plugin system

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies
- Test keyboard and mouse interactions
- Test edge cases (empty input, long text, special characters)

### Integration Tests
- Test component interactions
- Test state management
- Test session persistence
- Test theme switching

### E2E Tests
- Test complete user workflows
- Test across different terminals (iTerm2, Terminal.app, Alacritty)
- Test on different platforms (macOS, Linux, Windows)
- Test with different screen sizes

### Performance Tests
- Measure render time for large transcripts
- Test memory usage with long sessions
- Test responsiveness with many background tasks
- Profile CPU usage during heavy operations

## Accessibility Checklist

- [ ] All features keyboard-accessible
- [ ] Focus indicators visible
- [ ] Screen reader support
- [ ] High contrast mode
- [ ] Customizable font sizes
- [ ] Color-blind friendly themes
- [ ] Reduced motion option
- [ ] Text alternatives for icons

## Documentation Requirements

- User guide with screenshots
- Video tutorials for complex features
- Keyboard shortcut reference card
- Developer API documentation
- Plugin development guide
- Troubleshooting guide
- FAQ

---

**Design by**: Document Specialist Agent  
**Date**: 2026-05-29  
**Status**: Ready for implementation  
**Estimated effort**: 10 weeks (2 developers)
