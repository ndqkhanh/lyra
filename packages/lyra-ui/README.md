# Lyra UI - Phases 1-5: Complete UI Foundation

## Overview

Phases 1-5 implement a complete UI foundation with Rich/Textual frameworks, dual-pane interface, streaming capabilities, context visualization, and advanced keyboard navigation.

## Features

### Phase 1: Rich Console & Progress

#### 1. Rich Console (`console.py`)

Singleton console with theme support:

```python
from lyra_ui import console

# Print styled messages
console.print_success("Operation successful!")
console.print_error("Error occurred")
console.print_warning("Warning message")
console.print_info("Information")

# Custom printing
console.print("[bold blue]Custom styled text[/bold blue]")
```

**Features**:
- Singleton pattern for consistent styling
- Built-in themes (success, error, warning, info)
- Agent status colors
- Context indicator colors
- Custom theme support

#### 2. Progress Indicators (`progress.py`)

Progress bars and spinners:

```python
from lyra_ui import ProgressManager, Spinner

# Progress bar
manager = ProgressManager()
manager.add_task("download", "Downloading...", total=100)
manager.update_task("download", advance=10)
manager.complete_task("download")
manager.stop()

# Spinner
with Spinner("Processing...") as spinner:
    # Do work
    spinner.update("Still processing...")
```

**Features**:
- Multiple progress bars
- Spinners for indeterminate tasks
- Time tracking (elapsed, remaining)
- Task management (add, update, complete, remove)

### Phase 2: Dual-Pane Interface

#### 3. Textual App (`app.py`)

Full TUI application with dual-pane layout:

```python
from lyra_ui import LyraApp

# Run the app
app = LyraApp()
app.run()
```

**Features**:
- Split-screen layout (70% conversation, 30% status)
- Conversation pane with message history
- Status panel with real-time indicators
- Keyboard shortcuts (q=quit, Ctrl+W=switch pane, Ctrl+N=new chat)
- CSS-like styling

#### 4. Custom Widgets (`widgets.py`)

Rich widgets for UI components:

```python
from lyra_ui import (
    MessageBubble,
    TokenUsageIndicator,
    AgentStatusIndicator,
    ContextUsageRing
)

# Message bubble
bubble = MessageBubble("user", "Hello world")

# Token usage
token_indicator = TokenUsageIndicator(used=50000, total=200000)
token_indicator.update_usage(75000)

# Agent status
agent_status = AgentStatusIndicator("working")
agent_status.update_status("success")

# Context usage
context_ring = ContextUsageRing(45.0)
context_ring.update_percentage(60.0)
```

**Widgets**:
- `MessageBubble`: User/assistant messages with timestamps
- `TokenUsageIndicator`: Visual token usage bar with color coding
- `AgentStatusIndicator`: Agent status (idle/working/success/error)
- `ContextUsageRing`: Context window usage percentage

### Phase 3: Streaming & Progress Visualization

#### 5. Streaming System (`streaming.py`)

Async streaming with progressive rendering:

```python
from lyra_ui import StreamHandler, LiveStreamDisplay, StreamingProgress

# Stream handler
handler = StreamHandler()

async def my_stream():
    for token in ["Hello", " ", "world"]:
        yield token

result = await handler.stream_response(my_stream())

# With callback
def on_token(token):
    print(token, end="", flush=True)

await handler.stream_response(my_stream(), on_token=on_token)

# Cancellation
handler.cancel()

# Pause/resume
handler.pause()
handler.resume()

# Live display
display = LiveStreamDisplay()
display.start()
display.append_token("Hello")
display.stop()

# Progress tracking
progress = StreamingProgress()
progress.start()
progress.increment(10)
rate = progress.get_rate()  # tokens/second
elapsed = progress.get_elapsed()
progress.stop()
```

**Features**:
- Token-by-token streaming
- Cancellation support (Ctrl+C)
- Pause/resume functionality
- Backpressure handling
- Live display with Rich
- Streaming rate tracking

#### 6. Progress Visualization (`progress_viz.py`)

Multi-task progress tracking:

```python
from lyra_ui import MultiTaskProgress, ProgressVisualizer, ProgressState

# Multi-task tracker
tracker = MultiTaskProgress()

# Add tasks
tracker.add_task("download", "Download", "Downloading files", total=100)
tracker.add_task("process", "Process", "Processing data", total=50)

# Start and update
tracker.start_task("download")
tracker.update_task("download", 50)
tracker.complete_task("download", success=True)

# Cancel task
tracker.cancel_task("process")

# Get summary
summary = tracker.get_summary()
print(f"Completed: {summary['completed']}/{summary['total']}")

# Visualize
viz = ProgressVisualizer()
viz.display_summary(tracker)
```

**Features**:
- Multi-task progress tracking
- Step-by-step progress
- Status indicators (pending/running/completed/failed/cancelled)
- Time estimates
- Visual progress bars
- Summary statistics

### Phase 4: Context Window Visualization

#### 7. Context Visualization (`context_viz.py`)

Context window tracking and visualization:

```python
from lyra_ui import (
    ContextTracker,
    ContextComponent,
    ContextRingVisualizer,
    ContextManager
)

# Track context usage
tracker = ContextTracker(total_tokens=200000)

# Add tokens by component
tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 5000)
tracker.add_tokens(ContextComponent.CONVERSATION, 50000)
tracker.add_tokens(ContextComponent.TOOL_RESULTS, 20000)
tracker.add_tokens(ContextComponent.CODE_CONTEXT, 15000)

# Get usage stats
total_used = tracker.get_total_used()  # 90000
total_percentage = tracker.get_total_percentage()  # 45.0%

# Visualize
viz = ContextRingVisualizer()
viz.display(tracker)  # Shows ring chart + breakdown table

# Context management
manager = ContextManager(tracker)
recommendations = manager.get_recommendations()
```

**Features**:
- Component-level token tracking
- Context ring visualization with color coding
- Breakdown table with percentages
- Context export/import
- Component pruning
- Optimization recommendations

### Phase 5: Advanced Keyboard Navigation

#### 8. Keyboard Navigation (`keyboard.py`)

Vim-style keyboard navigation and command palette:

```python
from lyra_ui import (
    VimNavigator,
    NavigationMode,
    KeyBinding,
    CommandPalette,
    QuickActions
)

# Vim-style navigation
nav = VimNavigator()

# Check bindings
binding = nav.get_binding("h")  # Move left
print(f"{binding.key}: {binding.description}")

# Add custom binding
custom = KeyBinding("ctrl+s", "save", "Save file")
nav.add_binding(custom)

# Switch modes
nav.set_mode(NavigationMode.INSERT)

# Command palette
palette = CommandPalette()

# Register commands
def save_file():
    return "File saved"

palette.register_command("save", save_file, category="file")

# Search commands
results = palette.search_commands("save")

# Execute command
result = palette.execute_command("save")

# Quick actions
actions = QuickActions()
action = actions.get_action("@")  # file_picker
action = actions.get_action("#")  # skill_picker
action = actions.get_action("/")  # command_picker
```

**Features**:
- Vim-style navigation (hjkl, gg/G, Ctrl+D/U, w/b)
- Navigation modes (normal, insert, visual, command)
- Custom keybindings
- Command palette with fuzzy search
- Command history
- Command categories
- Quick actions (@, #, /)

**Components**:
- `VimNavigator`: Vim-style keyboard navigation
- `NavigationMode`: Navigation mode enum
- `KeyBinding`: Key binding definition
- `CommandPalette`: Command palette with fuzzy search
- `QuickActions`: Quick action shortcuts

**Widgets**:
- `MessageBubble`: User/assistant messages with timestamps
- `TokenUsageIndicator`: Visual token usage bar with color coding
- `AgentStatusIndicator`: Agent status (idle/working/success/error)
- `ContextUsageRing`: Context window usage percentage

## Installation

```bash
cd packages/lyra-ui
pip install -e .
```

## Testing

Run tests:
```bash
pytest tests/ -v
```

**Results**: 118 tests, 94% coverage

## Architecture

```
┌─────────────────────────────────────────┐
│    Lyra Textual App                     │
│  (Main Application)                     │
│                                         │
│  ┌─────────────┬─────────────────────┐ │
│  │ Conversation│  Status Panel       │ │
│  │ Pane (70%)  │  (30%)              │ │
│  │             │                     │ │
│  │ Messages    │  Agent Status       │ │
│  │ History     │  Token Usage        │ │
│  │ Code blocks │  Context Usage      │ │
│  │             │  Progress           │ │
│  └─────────────┴─────────────────────┘ │
│                                         │
│  Keyboard: q, Ctrl+W, Ctrl+N           │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Rich Console                         │
│  (Styled Output)                        │
│                                         │
│  • Singleton instance                  │
│  • Theme management                    │
│  • Status messages                     │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Progress Manager                     │
│  (Progress Tracking)                    │
│                                         │
│  • Multiple progress bars              │
│  • Spinners                            │
│  • Time tracking                       │
└─────────────────────────────────────────┘
```

## Usage Examples

### Running the TUI App

```python
from lyra_ui import LyraApp

app = LyraApp()
app.run()
```

### Adding Messages to Conversation

```python
from lyra_ui import ConversationPane

pane = ConversationPane()
pane.add_message("user", "What is Python?")
pane.add_message("assistant", "Python is a programming language...")
```

### Status Indicators

```python
from lyra_ui import (
    TokenUsageIndicator,
    AgentStatusIndicator,
    ContextUsageRing
)

# Token usage with color coding
tokens = TokenUsageIndicator(used=100000, total=200000)
print(tokens.render())  # Shows bar with 50% (yellow)

# Agent status
status = AgentStatusIndicator("working")
print(status.render())  # Shows 🟡 Working

# Context usage
context = ContextUsageRing(75.0)
print(context.render())  # Shows Context: 75.0% (yellow)
```

## Version

Current version: **0.1.0**

## Next Phase

Phase 6 will implement:
- Multi-agent orchestration dashboard
- Agent status visualization
- Task queue management
- Agent communication logs
- Performance metrics per agent

## References

- [Rich Documentation](https://rich.readthedocs.io/)
- [Textual Documentation](https://textual.textualize.io/)
- Lyra UI/UX Plan: `.omc/plans/LYRA_UI_UX_ULTIMATE_UPGRADE_PLAN.md`
