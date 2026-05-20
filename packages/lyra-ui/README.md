# Lyra UI - Phases 1-6: Complete UI Foundation + Multi-Agent Dashboard

## Overview

Phases 1-6 implement a complete UI foundation with Rich/Textual frameworks, dual-pane interface, streaming capabilities, context visualization, advanced keyboard navigation, and multi-agent orchestration dashboard.

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

### Phase 6: Multi-Agent Orchestration Dashboard

#### 8. Agent Dashboard (`agent_dashboard.py`)

Multi-agent fleet management and task orchestration:

```python
from lyra_ui import (
    AgentFleetManager,
    AgentInfo,
    AgentStatus,
    TaskBoard,
    TaskPriority,
    MonitoringPanel,
    WorkflowManager,
)

# Agent fleet management
fleet = AgentFleetManager()
agent = AgentInfo(id="agent1", name="Research Agent", status=AgentStatus.IDLE)
fleet.register_agent(agent)

# Assign task to agent
fleet.assign_task("agent1", "task1")
fleet.complete_task("agent1", success=True)

# Get agent metrics
metrics = fleet.get_metrics("agent1")
print(f"Success rate: {metrics.success_rate * 100}%")

# Task board (Kanban-style)
board = TaskBoard()
task = board.create_task(
    task_id="task1",
    title="Research AI agents",
    description="Survey open-source AI agent frameworks",
    priority=TaskPriority.HIGH,
)

# Task dependencies
board.add_dependency("task2", "task1")  # task2 depends on task1
ready_tasks = board.get_ready_tasks()  # Tasks with no blocking dependencies

# Monitoring panel
monitor = MonitoringPanel()
monitor.log_event("agent1", "task_start", "Started research task")
monitor.add_cost(0.05)  # Track API costs

# Get alerts
alerts = monitor.get_alerts(level="error")

# Workflow automation
workflow_mgr = WorkflowManager()
tasks = [
    {"title": "Research", "description": "Research phase", "priority": "high"},
    {"title": "Implement", "description": "Implementation phase", "priority": "medium"},
]
workflow_mgr.create_template("research_workflow", "Research Workflow", "Description", tasks)
workflow_mgr.start_workflow("workflow1", "research_workflow", board)
```

**Features**:
- Agent fleet management (register, status tracking, metrics)
- Task board with Kanban-style organization
- Task dependencies and blocking
- Real-time monitoring and event logging
- Cost tracking
- Alert system (warnings, errors)
- Workflow templates and automation

#### 9. Dashboard Visualization (`dashboard_viz.py`)

Rich visualizations for the agent dashboard:

```python
from lyra_ui import DashboardVisualizer, AgentStatusWidget, TaskSummaryWidget

# Dashboard visualizer
viz = DashboardVisualizer()

# Render agent fleet table
agent_table = viz.render_agent_table(fleet)

# Render task board
task_table = viz.render_task_board(board)

# Render monitoring feed
feed = viz.render_monitoring_feed(monitor, limit=20)

# Render complete dashboard
layout = viz.render_dashboard(fleet, board, monitor)
viz.display_dashboard(fleet, board, monitor)

# Live dashboard (auto-refreshing)
with viz.live_dashboard(fleet, board, monitor, refresh_rate=1.0) as live:
    # Dashboard updates automatically
    pass

# Status panel widgets
agent_widget = AgentStatusWidget()
agent_panel = agent_widget.render(fleet.list_agents())

task_widget = TaskSummaryWidget()
task_panel = task_widget.render(board)
```

**Features**:
- Agent fleet table with status indicators
- Task board visualization (Kanban-style)
- Real-time monitoring feed
- Performance metrics table
- Alert panel with color coding
- Complete dashboard layout
- Live auto-refreshing dashboard
- Compact status widgets for panels

**Components**:
- `AgentFleetManager`: Manage fleet of agents
- `TaskBoard`: Kanban-style task management
- `MonitoringPanel`: Real-time event logging and alerts
- `WorkflowManager`: Workflow templates and automation
- `DashboardVisualizer`: Rich dashboard visualizations
- `AgentStatusWidget`: Compact agent status display
- `TaskSummaryWidget`: Task progress summary

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

**Results**: 187 tests, 67% coverage

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

Phase 7 will implement:
- Enhanced visual feedback (banner system, notifications, animations)
- Multiple color themes
- Toast notifications with sound integration
- Smooth animations and transitions
- Theme customization and sharing

## References

- [Rich Documentation](https://rich.readthedocs.io/)
- [Textual Documentation](https://textual.textualize.io/)
- Lyra UI/UX Plan: `.omc/plans/LYRA_UI_UX_ULTIMATE_UPGRADE_PLAN.md`
