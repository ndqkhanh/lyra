"""
Lyra UI - Beautiful terminal UI using Rich and Textual.

This package provides:
- Rich console with themes
- Progress indicators
- Textual TUI framework
- Dual-pane interface
- Custom widgets
- Streaming output
- Progress visualization
- Context window visualization
- Keyboard navigation
- Multi-agent orchestration dashboard
"""

from lyra_ui.agent_dashboard import (
    AgentFleetManager,
    AgentInfo,
    AgentMetrics,
    AgentStatus,
    MonitoringEvent,
    MonitoringPanel,
    Task,
    TaskBoard,
    TaskPriority,
    TaskStatus,
    WorkflowManager,
    WorkflowTemplate,
)
from lyra_ui.app import ConversationPane, DualPaneLayout, LyraApp, StatusPanel
from lyra_ui.console import RichConsole, console
from lyra_ui.context_viz import (
    ContextComponent,
    ContextManager,
    ContextRingVisualizer,
    ContextTracker,
    ContextUsage,
)
from lyra_ui.dashboard_viz import (
    AgentStatusWidget,
    DashboardVisualizer,
    TaskSummaryWidget,
)
from lyra_ui.keyboard import (
    CommandPalette,
    KeyBinding,
    NavigationMode,
    QuickActions,
    VimNavigator,
)
from lyra_ui.progress import ProgressManager, Spinner
from lyra_ui.progress_viz import (
    MultiTaskProgress,
    ProgressState,
    ProgressStep,
    ProgressVisualizer,
)
from lyra_ui.streaming import (
    LiveStreamDisplay,
    StreamHandler,
    StreamingProgress,
)
from lyra_ui.widgets import (
    AgentStatusIndicator,
    ContextUsageRing,
    MessageBubble,
    TokenUsageIndicator,
)

__version__ = "0.1.0"

__all__ = [
    # Console
    "RichConsole",
    "console",
    # Progress
    "ProgressManager",
    "Spinner",
    # App
    "LyraApp",
    "DualPaneLayout",
    "ConversationPane",
    "StatusPanel",
    # Widgets
    "MessageBubble",
    "TokenUsageIndicator",
    "AgentStatusIndicator",
    "ContextUsageRing",
    # Streaming
    "StreamHandler",
    "LiveStreamDisplay",
    "StreamingProgress",
    # Progress Visualization
    "MultiTaskProgress",
    "ProgressStep",
    "ProgressState",
    "ProgressVisualizer",
    # Context Visualization
    "ContextTracker",
    "ContextComponent",
    "ContextUsage",
    "ContextRingVisualizer",
    "ContextManager",
    # Keyboard Navigation
    "VimNavigator",
    "NavigationMode",
    "KeyBinding",
    "CommandPalette",
    "QuickActions",
    # Agent Dashboard
    "AgentFleetManager",
    "AgentInfo",
    "AgentMetrics",
    "AgentStatus",
    "TaskBoard",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "MonitoringPanel",
    "MonitoringEvent",
    "WorkflowManager",
    "WorkflowTemplate",
    # Dashboard Visualization
    "DashboardVisualizer",
    "AgentStatusWidget",
    "TaskSummaryWidget",
]
