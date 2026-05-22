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
]
