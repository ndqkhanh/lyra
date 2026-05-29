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
- Banner system
- Notification system
- Theme management
- Animation effects
- Session management and replay
- Team collaboration
- Integration system
- Performance optimization
- Async architecture
- Resource management
- Accessibility features
"""

from lyra_ui.accessibility import (
    AccessibilityAuditor,
    AccessibilityReport,
    AriaAttributes,
    AriaLive,
    AriaRole,
    FocusManager,
    KeyboardShortcut,
    KeyboardShortcutManager,
    ScreenReader,
)
from lyra_ui.agent_dashboard import (
    AgentFleetManager,
    AgentInfo,
    AgentMetrics,
    AgentStatus,
    MonitoringEvent,
    MonitoringPanel,
    Task,
    TaskBoard,
    WorkflowManager,
    WorkflowTemplate,
)
from lyra_ui.agent_dashboard import (
    TaskPriority as AgentTaskPriority,
)
from lyra_ui.agent_dashboard import (
    TaskStatus as AgentTaskStatus,
)
from lyra_ui.app import ConversationPane, DualPaneLayout, LyraApp, StatusPanel
from lyra_ui.async_arch import (
    AsyncFileIO,
    BackgroundTask,
    BackgroundTaskQueue,
    ConnectionPool,
    RequestBatcher,
    TaskPriority,
    TaskStatus,
    WorkerPool,
)
from lyra_ui.banner import (
    BannerStats,
    BannerStyle,
    BannerSystem,
    BannerTheme,
    ShutdownBanner,
    StartupBanner,
)
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
from lyra_ui.formatter import RichFormatter
from lyra_ui.integration import (
    GitHubIntegration,
    GitIntegration,
    IntegrationConfig,
    IntegrationManager,
    IntegrationType,
    Plugin,
    PluginSystem,
    SlackIntegration,
    WebhookIntegration,
)
from lyra_ui.keyboard import (
    CommandPalette,
    KeyBinding,
    NavigationMode,
    QuickActions,
    VimNavigator,
)
from lyra_ui.notifications import (
    Notification,
    NotificationHistory,
    NotificationLevel,
    NotificationSystem,
    ToastNotification,
)
from lyra_ui.performance import (
    Debouncer,
    LazyLoader,
    LRUCache,
    MemoryMonitor,
    PerformanceProfiler,
    VirtualScroller,
)
from lyra_ui.progress import ProgressManager, Spinner
from lyra_ui.progress_viz import (
    MultiTaskProgress,
    ProgressState,
    ProgressStep,
    ProgressVisualizer,
)
from lyra_ui.resource_mgmt import (
    BandwidthOptimizer,
    DiskSpaceManager,
    MemoryLeakDetector,
    ResourceCleaner,
    ResourceMonitor,
)
from lyra_ui.session import (
    SessionAnnotation,
    SessionEvent,
    SessionEventType,
    SessionManager,
    SessionMetadata,
    SessionReplay,
)
from lyra_ui.streaming import (
    LiveStreamDisplay,
    StreamHandler,
    StreamingProgress,
)
from lyra_ui.streaming_repl import (
    LyraCompleter,
    REPLConfig,
    REPLMode,
    StatusBar,
    StreamingREPL,
    ToolProgressDisplay,
)
from lyra_ui.team import (
    PromptTemplate,
    TeamConfig,
    TeamManager,
    TeamMember,
    UsageQuota,
    UserRole,
)
from lyra_ui.themes import (
    AnimationEffects,
    ThemeColors,
    ThemeManager,
    ThemeName,
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
    # Formatter
    "RichFormatter",
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
    # Streaming REPL
    "StreamingREPL",
    "REPLConfig",
    "REPLMode",
    "LyraCompleter",
    "StatusBar",
    "ToolProgressDisplay",
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
    "AgentTaskStatus",
    "AgentTaskPriority",
    "MonitoringPanel",
    "MonitoringEvent",
    "WorkflowManager",
    "WorkflowTemplate",
    # Dashboard Visualization
    "DashboardVisualizer",
    "AgentStatusWidget",
    "TaskSummaryWidget",
    # Banner System
    "BannerSystem",
    "BannerStyle",
    "BannerTheme",
    "BannerStats",
    "StartupBanner",
    "ShutdownBanner",
    # Notification System
    "NotificationSystem",
    "NotificationLevel",
    "Notification",
    "ToastNotification",
    "NotificationHistory",
    # Theme System
    "ThemeManager",
    "ThemeName",
    "ThemeColors",
    "AnimationEffects",
    # Session Management
    "SessionManager",
    "SessionMetadata",
    "SessionEvent",
    "SessionEventType",
    "SessionAnnotation",
    "SessionReplay",
    # Team Collaboration
    "TeamManager",
    "TeamConfig",
    "TeamMember",
    "UserRole",
    "UsageQuota",
    "PromptTemplate",
    # Integration System
    "IntegrationManager",
    "IntegrationType",
    "IntegrationConfig",
    "GitIntegration",
    "GitHubIntegration",
    "SlackIntegration",
    "WebhookIntegration",
    "PluginSystem",
    "Plugin",
    # Performance Optimization
    "LRUCache",
    "LazyLoader",
    "VirtualScroller",
    "Debouncer",
    "MemoryMonitor",
    "PerformanceProfiler",
    # Async Architecture
    "BackgroundTaskQueue",
    "BackgroundTask",
    "TaskPriority",
    "TaskStatus",
    "WorkerPool",
    "AsyncFileIO",
    "RequestBatcher",
    "ConnectionPool",
    # Resource Management
    "ResourceMonitor",
    "MemoryLeakDetector",
    "ResourceCleaner",
    "DiskSpaceManager",
    "BandwidthOptimizer",
    # Accessibility
    "AccessibilityAuditor",
    "AccessibilityReport",
    "AriaAttributes",
    "AriaRole",
    "AriaLive",
    "ScreenReader",
    "KeyboardShortcut",
    "KeyboardShortcutManager",
    "FocusManager",
]
