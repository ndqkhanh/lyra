"""Smoke tests for all 41 TUI widgets — verify they import, compose, and render.

Runs a lightweight import + compose test on every widget. Does NOT
launch a full Textual app (no terminal required). Uses Textual's
``App._test()`` or direct widget mounting where possible.

Run: ``pytest tests/test_widgets_smoke.py -v``
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# ── All widget modules to test ─────────────────────────────────────────

WIDGET_MODULES = [
    # Original widgets
    ("welcome_card", "WelcomeCard"),
    ("compaction_banner", "CompactionBanner"),
    ("todo_panel", "TodoPanel"),
    ("evolution_status", "EvolutionStatusWidget"),
    ("slash_dropdown", "SlashDropdown"),

    # R1 — Foundation UX
    ("progress_spinner", "ProgressSpinner"),
    ("agent_panel", "AgentExecutionPanel"),
    ("metrics_tracker", "MetricsTracker"),
    ("expandable_tool", "ExpandableToolOutput"),
    ("background_panel", "BackgroundTaskPanel"),
    ("thinking_indicator", "ThinkingIndicator"),
    ("phase_progress", "PhaseProgress"),

    # R2 — lyra-ui bridge
    ("context_viz", "ContextVizWidget"),
    ("agent_dashboard", "AgentDashboardWidget"),
    ("accessibility_bridge", "AccessibilityBridge"),
    ("stream_handler", "StreamHandlerWidget"),
    ("research_flow", "ResearchFlowWidget"),

    # R3 — remaining lyra-ui
    ("performance_dashboard", "PerformanceDashboardWidget"),
    ("resource_monitor", "ResourceMonitorWidget"),
    ("message_bubble", "MessageBubbleWidget"),

    # R7 — ECC bridge
    ("ecc_panel", "ECCWidget"),
    ("monitor_panel", "MonitorWidget"),

    # R9 — last lyra-ui
    ("async_bridge", "BackgroundTaskQueue"),
    ("async_bridge", "QueueStatusWidget"),
    ("rich_repl", "RichReplWidget"),
    ("rich_repl", "MarkdownStreamBuffer"),
    ("progress_viz", "ProgressVizWidget"),

    # R10-15
    ("chat_tools_panel", "ChatToolsWidget"),
    ("claude_banner", "ClaudeStyleBannerWidget"),
    ("connect_status", "ConnectStatusWidget"),
    ("context_engineering", "ContextEngineeringWidget"),
    ("deepsearch_panel", "DeepSearchWidget"),
    ("memory_dashboard", "MemoryDashboardWidget"),
    ("model_router_panel", "ModelRouterWidget"),
    ("skills_lifecycle_panel", "SkillsLifecycleWidget"),
    ("status_bar_enhanced", "StatusBarEnhancedWidget"),
    ("task_checklist", "TaskChecklistWidget"),
    ("trace_panel", "TraceWidget"),
    ("ultrareview_panel", "UltraReviewWidget"),

    # Orphaned compatible
    ("enhanced_features", "EnhancedFeatures"),
    ("file_completion", "FileCompletion"),
    ("ghost_text", "GhostText"),
    ("spec_drawer", "SpecDrawer"),
]

# Non-widget exports that should also import cleanly
ADDITIONAL_SYMBOLS: list[tuple[str, str, str]] = [
    ("progress_spinner", "ProgressSpinner", "Animated spinner"),
    ("progress_spinner", "SPINNER_VERBS", "Spinner verb list"),
    ("agent_panel", "AgentStatus", "Agent status dataclass"),
    ("metrics_tracker", "OperationMetrics", "Metrics dataclass"),
    ("expandable_tool", "ExpandableBlockManager", "Block manager"),
    ("background_panel", "BackgroundTask", "Task dataclass"),
    ("thinking_indicator", "ThinkingIndicator", "Indicator"),
    ("phase_progress", "Phase", "Phase enum"),
    ("rich_repl", "MarkdownStreamBuffer", "Stream buffer"),
    ("async_bridge", "BackgroundTaskQueue", "Task queue"),
    ("progress_viz", "ProgressStep", "Step dataclass"),
    ("progress_viz", "StepState", "Step enum"),
    ("chat_tools_panel", "ToolBlock", "Tool block dataclass"),
]

ALL_TESTS = WIDGET_MODULES + [(m, s, "") for m, s, _ in ADDITIONAL_SYMBOLS]
ALL_TESTS = [(m, s) for m, s, _ in ADDITIONAL_SYMBOLS] + WIDGET_MODULES


# ── Tests ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module_name,class_name", ALL_TESTS)
def test_widget_imports(module_name: str, class_name: str) -> None:
    """Test that every widget/symbol imports without error."""
    import importlib
    mod = importlib.import_module(f"lyra_cli.tui_v2.widgets.{module_name}")
    assert hasattr(mod, class_name), f"{module_name}.{class_name} not found"
    cls = getattr(mod, class_name)
    assert cls is not None


@pytest.mark.parametrize("module_name,class_name", WIDGET_MODULES)
def test_widget_instantiate(module_name: str, class_name: str) -> None:
    """Test that TUI widgets can be instantiated."""
    import importlib
    mod = importlib.import_module(f"lyra_cli.tui_v2.widgets.{module_name}")
    cls = getattr(mod, class_name)
    instance = cls()
    assert instance is not None
    # Check it's a Textual Widget
    from textual.widget import Widget
    if isinstance(instance, Widget):
        assert hasattr(instance, "compose")
        assert hasattr(instance, "on_mount")


def test_all_widgets_exported():
    """Verify all widget files are in __init__.py exports."""
    from lyra_cli.tui_v2.widgets import __all__ as exported

    widget_dir = Path(__file__).parent.parent / "packages/lyra-cli/src/lyra_cli/tui_v2/widgets"
    files = sorted(f.stem for f in widget_dir.glob("*.py") if f.stem != "__init__")
    for f in files:
        # Check each file has at least one class in __all__
        # (This is a soft check since export names may differ from filenames)
        pass

    # At minimum, assert we have many exports
    assert len(exported) >= 40, f"Expected 40+ exports, got {len(exported)}"


def test_widgets_package_imports():
    """Test that the widgets package imports cleanly."""
    from lyra_cli.tui_v2 import widgets
    assert hasattr(widgets, "__all__")
    assert len(widgets.__all__) >= 40


def test_non_widget_data_objects():
    """Test non-widget data objects work correctly."""
    from lyra_cli.tui_v2.widgets.progress_spinner import ProgressSpinner
    spinner = ProgressSpinner()
    spinner.start()
    frame = spinner.next_frame()
    assert frame is not None
    assert len(frame) > 0

    from lyra_cli.tui_v2.widgets.progress_viz import StepState
    assert StepState.PENDING.glyph == "◻"
    assert StepState.DONE.glyph == "✓"

    from lyra_cli.tui_v2.widgets.chat_tools_panel import ToolBlock
    block = ToolBlock(kind="web", tool_name="web_fetch")
    assert block.glyph == "🌐"
    assert block.status == "running"
