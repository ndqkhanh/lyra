"""Widgets package for Lyra TUI v2."""
from .slash_dropdown import SlashDropdown
from .welcome_card import WelcomeCard
from .compaction_banner import CompactionBanner
from .todo_panel import TodoPanel
from .evolution_status import EvolutionStatusWidget

# UX improvement widgets
from .progress_spinner import ProgressSpinner
from .agent_panel import AgentExecutionPanel, AgentStatus
from .metrics_tracker import MetricsTracker, OperationMetrics
from .expandable_tool import ExpandableToolOutput, ExpandableBlockManager
from .background_panel import BackgroundTaskPanel, BackgroundTask
from .thinking_indicator import ThinkingIndicator
from .phase_progress import PhaseProgress, Phase

__all__ = [
    # Original widgets
    "SlashDropdown",
    "WelcomeCard",
    "CompactionBanner",
    "TodoPanel",
    "EvolutionStatusWidget",

    # UX improvement widgets
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
]
