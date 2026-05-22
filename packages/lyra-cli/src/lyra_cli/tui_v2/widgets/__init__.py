"""Widgets package for Lyra TUI v2."""
from .slash_dropdown import SlashDropdown
from .welcome_card import WelcomeCard
from .compaction_banner import CompactionBanner
from .todo_panel import TodoPanel
from .evolution_status import EvolutionStatusWidget

# UX improvement widgets (Round 1)
from .progress_spinner import ProgressSpinner
from .agent_panel import AgentExecutionPanel, AgentStatus
from .metrics_tracker import MetricsTracker, OperationMetrics
from .expandable_tool import ExpandableToolOutput, ExpandableBlockManager
from .background_panel import BackgroundTaskPanel, BackgroundTask
from .thinking_indicator import ThinkingIndicator
from .phase_progress import PhaseProgress, Phase

# UX improvement widgets (Round 2 — lyra-ui bridge)
from .context_viz import ContextVizWidget
from .agent_dashboard import AgentDashboardWidget
from .accessibility_bridge import AccessibilityBridge
from .stream_handler import StreamHandlerWidget
from .research_flow import ResearchFlowWidget

# UX improvement widgets (Round 3 — remaining lyra-ui ports)
from .performance_dashboard import PerformanceDashboardWidget
from .resource_monitor import ResourceMonitorWidget
from .message_bubble import MessageBubbleWidget

# UX improvement widgets (Round 7 — ECC bridge + final)
from .ecc_panel import ECCWidget
from .monitor_panel import MonitorWidget

# UX improvement widgets (Round 9 — last 3 lyra_ui ports)
from .async_bridge import BackgroundTaskQueue, QueueStatusWidget
from .rich_repl import RichReplWidget, MarkdownStreamBuffer
from .progress_viz import ProgressVizWidget, ProgressStep, StepState

# UX improvement widgets (Round 10-15 — wired from disk)
from .chat_tools_panel import ChatToolsWidget, ToolBlock
from .claude_banner import ClaudeStyleBannerWidget
from .onboarding_panel import OnboardingWidget
from .effort_app_panel import EffortAppWidget
from .cron_dashboard import CronDashboardWidget
from .connect_status import ConnectStatusWidget
from .context_engineering import ContextEngineeringWidget
from .deepsearch_panel import DeepSearchWidget
from .memory_dashboard import MemoryDashboardWidget
from .model_router_panel import ModelRouterWidget
from .skills_lifecycle_panel import SkillsLifecycleWidget
from .status_bar_enhanced import StatusBarEnhancedWidget
from .task_checklist import TaskChecklistWidget
from .trace_panel import TraceWidget
from .ultrareview_panel import UltraReviewWidget

# Orphaned compatible widgets (existing files, no new code)
from .enhanced_features import EnhancedFeatures
from .file_completion import FileCompletion
from .ghost_text import GhostText
from .spec_drawer import SpecDrawer

__all__ = [
    # Original widgets
    "SlashDropdown",
    "WelcomeCard",
    "CompactionBanner",
    "TodoPanel",
    "EvolutionStatusWidget",

    # UX improvement widgets (Round 1)
    "ProgressSpinner",
    "AgentExecutionPanel",
    "AgentStatus",
    "MetricsTracker",
    "OperationMetrics",
    "ExpandableToolOutput",
    "ExpandableBlockManager",
    "BackgroundTaskPanel",
    "BackgroundTask",
    "ThinkingIndicator",
    "PhaseProgress",
    "Phase",

    # UX improvement widgets (Round 2 — lyra-ui bridge)
    "ContextVizWidget",
    "AgentDashboardWidget",
    "AccessibilityBridge",
    "StreamHandlerWidget",
    "ResearchFlowWidget",

    # UX improvement widgets (Round 3 — remaining lyra-ui ports)
    "PerformanceDashboardWidget",
    "ResourceMonitorWidget",
    "MessageBubbleWidget",

    # UX improvement widgets (Round 7 — ECC bridge + final)
    "ECCWidget",
    "MonitorWidget",

    # UX improvement widgets (Round 9 — last 3 lyra_ui ports)
    "BackgroundTaskQueue",
    "QueueStatusWidget",
    "RichReplWidget",
    "MarkdownStreamBuffer",
    "ProgressVizWidget",
    "ProgressStep",
    "StepState",

    # UX improvement widgets (Round 10-15 — wired from disk)
    "ClaudeStyleBannerWidget",
    "ConnectStatusWidget",
    "ContextEngineeringWidget",
    "DeepSearchWidget",
    "MemoryDashboardWidget",
    "ModelRouterWidget",
    "SkillsLifecycleWidget",
    "StatusBarEnhancedWidget",
    "TaskChecklistWidget",
    "TraceWidget",
    "UltraReviewWidget",
    "OnboardingWidget",
    "EffortAppWidget",
    "CronDashboardWidget",

    # Orphaned compatible widgets
    "EnhancedFeatures",
    "FileCompletion",
    "GhostText",
    "SpecDrawer",
]
