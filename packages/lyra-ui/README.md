# Lyra UI - Phases 1-8: Complete UI Foundation + Multi-Agent Dashboard + Visual Feedback + Collaboration

## Overview

Phases 1-8 implement a complete UI foundation with Rich/Textual frameworks, dual-pane interface, streaming capabilities, context visualization, advanced keyboard navigation, multi-agent orchestration dashboard, enhanced visual feedback system, and collaboration & sharing features.

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

### Phase 7: Enhanced Visual Feedback

#### 10. Banner System (`banner.py`)

Adaptive banners with themes and animations:

```python
from lyra_ui import BannerSystem, BannerStyle, BannerTheme, BannerStats

# Banner system
banner = BannerSystem(
    style=BannerStyle.FULL,
    theme=BannerTheme.DRACULA,
)

# Display banner with stats
stats = BannerStats(
    tokens_used=10000,
    total_cost=0.50,
    elapsed_time=60.0,
    agents_active=3,
)
banner.display(
    title="Lyra",
    subtitle="AI Research Agent",
    status="Processing",
    stats=stats,
)

# Startup banner
from lyra_ui import StartupBanner
startup = StartupBanner()
startup.display(version="1.0.0", loading_message="Initializing...")

# Shutdown banner
from lyra_ui import ShutdownBanner
shutdown = ShutdownBanner()
shutdown.display(tasks_completed=10, total_time=120.5)
```

**Features**:
- Adaptive width (36-100 cols)
- Multiple styles (minimal, standard, full)
- Theme support (default, dark, light, solarized, dracula)
- Status indicators
- Quick stats display (tokens, cost, time, agents)
- Startup/shutdown animations

#### 11. Notification System (`notifications.py`)

Toast notifications with sound integration:

```python
from lyra_ui import NotificationSystem, NotificationLevel

# Notification system
notif_system = NotificationSystem(
    max_history=100,
    enable_sound=True,
)

# Create notifications
notif_system.info("Task Started", "Research task has started")
notif_system.success("Task Completed", "Research completed successfully")
notif_system.warning("Low Memory", "Memory usage is high")
notif_system.error("Task Failed", "Analysis task failed")

# Display toast
notif = notif_system.info("Update", "New data available")
notif_system.display_toast(notif)

# Get notification history
history = notif_system.get_history(level=NotificationLevel.ERROR, limit=10)
unread = notif_system.get_history(unread_only=True)

# Mark as read
notif_system.mark_read(notif.id)
notif_system.mark_all_read()

# Get unread count
count = notif_system.get_unread_count()

# Toast notification
from lyra_ui import ToastNotification
toast = ToastNotification()
toast.show("Quick message", level=NotificationLevel.SUCCESS)

# Notification history viewer
from lyra_ui import NotificationHistory
history_viewer = NotificationHistory()
history_viewer.display(notif_system.notifications)
```

**Features**:
- Toast notifications (non-blocking)
- Notification levels (info, success, warning, error)
- Notification history with filtering
- Read/unread tracking
- Sound integration (lyra-audio)
- Notification persistence
- Action support

#### 12. Theme System (`themes.py`)

Customizable color themes and animations:

```python
from lyra_ui import ThemeManager, ThemeName, ThemeColors

# Theme manager
theme_mgr = ThemeManager()

# Set theme
theme_mgr.set_theme(ThemeName.DRACULA)

# Get current theme
theme = theme_mgr.get_current_theme()
print(f"Primary: {theme.primary}")

# Create custom theme
colors = ThemeColors(
    primary="cyan",
    secondary="blue",
    success="green",
    warning="yellow",
    error="red",
    info="cyan",
    background="black",
    foreground="white",
    dim="dim white",
    bright="bright_white",
)
theme_mgr.create_custom_theme("my_theme", colors)

# Preview theme
theme_mgr.preview_theme(ThemeName.NORD)

# Export/import themes
theme_dict = theme_mgr.export_theme(ThemeName.DRACULA)
theme_mgr.import_theme("imported_theme", theme_dict)

# List all themes
themes = theme_mgr.list_themes()

# Animation effects
from lyra_ui import AnimationEffects
effects = AnimationEffects()

effects.typing_indicator("Agent is thinking")
effects.pulse_effect("Processing", color="cyan")
effects.loading_spinner("Loading data")
effects.success_animation("Task completed")
effects.error_animation("Task failed")
```

**Features**:
- 9 built-in themes (default, dark, light, solarized, dracula, monokai, nord, gruvbox)
- Custom theme creation
- Theme preview
- Theme import/export
- Animation effects (typing, pulse, loading, success, error)
- Per-component styling

**Components**:
- `BannerSystem`: Adaptive banner with themes
- `StartupBanner`: Startup animation
- `ShutdownBanner`: Shutdown summary
- `NotificationSystem`: Toast notifications with history
- `ToastNotification`: Quick toast display
- `NotificationHistory`: History viewer
- `ThemeManager`: Theme management
- `AnimationEffects`: Visual animations

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

**Results**: 257 tests, 56% coverage

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

## Phase 8: Collaboration & Sharing

### 13. Session Management (`session.py`)

Session export/import and replay functionality:

```python
from lyra_ui import SessionManager, SessionEventType, SessionReplay

# Session manager
manager = SessionManager()

# Create session
session = manager.create_session(
    session_id="research-session",
    author="user@example.com",
    title="AI Research Session",
    description="Researching AI agent frameworks",
    tags=["ai", "research"],
)

# Add events
manager.add_event(
    event_id="e1",
    event_type=SessionEventType.MESSAGE,
    data={"role": "user", "content": "What are the best AI frameworks?"},
)
manager.add_event(
    event_id="e2",
    event_type=SessionEventType.TOOL_CALL,
    data={"tool": "search", "query": "AI frameworks"},
)

# Add annotations
manager.add_annotation(
    annotation_id="a1",
    event_id="e1",
    author="reviewer",
    text="Good question",
)

# Save session
manager.save_session()

# Export session
exported = manager.export_session()

# Import session
manager.import_session(exported)

# Search sessions
results = manager.search_sessions(query="AI", tags=["research"])

# Get analytics
analytics = manager.get_analytics()
print(f"Total events: {analytics['total_events']}")
print(f"Total tokens: {analytics['total_tokens']}")

# Session replay
replay = SessionReplay(manager)
replay.start()
while True:
    event = replay.next_event()
    if event is None:
        break
    print(f"Event: {event.type.value}")
```

**Features**:
- Session export/import to JSON
- Event types: MESSAGE, TOOL_CALL, TOOL_RESULT, ERROR, ANNOTATION
- Session annotations for collaboration
- Session search by query, author, tags
- Session analytics (events, tokens, cost)
- Session replay with next/previous/goto controls
- Progress tracking during replay

### 14. Team Collaboration (`team.py`)

Team management with role-based access control:

```python
from lyra_ui import TeamManager, UserRole

# Team manager
manager = TeamManager()

# Create team
team = manager.create_team(
    team_id="engineering",
    team_name="Engineering Team",
    settings={"theme": "dark", "notifications": True},
)

# Add members
manager.add_member(
    user_id="alice",
    username="Alice",
    email="alice@example.com",
    role=UserRole.ADMIN,
)
manager.add_member(
    user_id="bob",
    username="Bob",
    email="bob@example.com",
    role=UserRole.MEMBER,
)

# Update member role
manager.update_member_role("bob", UserRole.ADMIN)

# Set usage quotas
manager.set_quota("alice", tokens_limit=200000, cost_limit=20.0)
manager.set_quota("bob", tokens_limit=100000, cost_limit=10.0)

# Update usage
manager.update_usage("alice", tokens=50000, cost=5.0)

# Check quota
if manager.check_quota("alice"):
    print("Within quota")

# Add shared templates
manager.add_template(
    template_id="code-review",
    name="Code Review",
    description="Template for code reviews",
    template="Review the following code:\n{code}",
    variables=["code"],
    created_by="alice",
)

# Get template
template = manager.get_template("code-review")

# Save team
manager.save_team()

# Get analytics
analytics = manager.get_team_analytics()
print(f"Total members: {analytics['total_members']}")
print(f"Total tokens used: {analytics['total_tokens_used']}")
print(f"Total cost: {analytics['total_cost']}")
```

**Features**:
- Team configuration and settings
- Role-based access control (ADMIN, MEMBER, VIEWER)
- Usage quotas (tokens and cost limits)
- Shared prompt templates with variables
- Team analytics (members, usage, cost)
- Member management (add, remove, update role)
- Storage in ~/.lyra/teams/

### 15. Integration System (`integration.py`)

External tool integrations:

```python
from lyra_ui import (
    IntegrationManager,
    IntegrationType,
    GitIntegration,
    GitHubIntegration,
    SlackIntegration,
    WebhookIntegration,
    PluginSystem,
    Plugin,
)

# Integration manager
manager = IntegrationManager()

# Configure integrations
manager.configure_integration(
    IntegrationType.GIT,
    enabled=True,
    settings={"repo_path": "/path/to/repo"},
)
manager.configure_integration(
    IntegrationType.GITHUB,
    enabled=True,
    settings={"token": "ghp_xxx"},
)

# Git integration
git = manager.git
git.commit("feat: add new feature", files=["src/main.py"])
git.push(branch="main")
git.create_branch("feature/new-feature")

# GitHub integration
github = manager.github
pr_url = github.create_pull_request(
    repo="owner/repo",
    title="Add new feature",
    body="This PR adds...",
    head="feature/new-feature",
    base="main",
)

# Slack integration
slack = manager.slack
slack.send_notification(
    title="Build Complete",
    message="Build #123 completed successfully",
    level="success",
)

# Webhook integration
webhook = manager.webhook
webhook.register_webhook("task.completed", "https://example.com/webhook")
webhook.trigger_webhook("task.completed", {"task_id": "123", "status": "done"})

# Plugin system
plugins = manager.plugins
plugin = Plugin(
    id="custom-plugin",
    name="Custom Plugin",
    version="1.0.0",
    description="A custom plugin",
)
plugins.register_plugin(plugin)

# Register hooks
def on_task_complete(task_id):
    print(f"Task {task_id} completed")

plugins.register_hook("task.complete", on_task_complete)
plugins.trigger_hook("task.complete", "task-123")

# Save config
manager.save_config()
```

**Features**:
- Git integration (commit, push, branch)
- GitHub/GitLab integration (PR, issues)
- Slack notifications
- Webhook support
- Plugin system with hooks
- Integration configuration management
- Enable/disable integrations

**Components**:
- `SessionManager`: Session export/import and replay
- `SessionReplay`: Step-by-step session playback
- `TeamManager`: Team collaboration with RBAC
- `IntegrationManager`: External tool integrations
- `GitIntegration`: Git operations
- `GitHubIntegration`: GitHub API
- `SlackIntegration`: Slack notifications
- `WebhookIntegration`: Webhook management
- `PluginSystem`: Plugin and hook system

## Next Phase

Phase 9 will implement:
- Performance optimization
- Caching strategies
- Lazy loading
- Memory management
- Response time optimization

## References

- [Rich Documentation](https://rich.readthedocs.io/)
- [Textual Documentation](https://textual.textualize.io/)
- Lyra UI/UX Plan: `.omc/plans/LYRA_UI_UX_ULTIMATE_UPGRADE_PLAN.md`
