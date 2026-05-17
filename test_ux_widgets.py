#!/usr/bin/env python3
"""Test UX widgets integration in LyraHarnessApp.

This script verifies that all UX improvement widgets are properly
integrated and functional.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))

from lyra_cli.tui_v2.app import LyraHarnessApp
from lyra_cli.tui_v2.widgets import (
    ProgressSpinner,
    AgentExecutionPanel,
    MetricsTracker,
    BackgroundTaskPanel,
    ThinkingIndicator,
    PhaseProgress,
)


def test_widget_initialization():
    """Test that all widgets are initialized in LyraHarnessApp."""
    print("Testing widget initialization...")

    # Create a minimal config
    from harness_tui.app import ProjectConfig
    cfg = ProjectConfig(
        name="test-project",
        working_dir=Path.cwd(),
        model="claude-sonnet-4-6",
    )

    # Create app instance
    app = LyraHarnessApp(cfg)

    # Verify all widgets are initialized
    assert hasattr(app, 'progress_spinner'), "ProgressSpinner not initialized"
    assert isinstance(app.progress_spinner, ProgressSpinner), "Wrong type for progress_spinner"

    assert hasattr(app, 'agent_panel'), "AgentExecutionPanel not initialized"
    assert isinstance(app.agent_panel, AgentExecutionPanel), "Wrong type for agent_panel"

    assert hasattr(app, 'metrics_tracker'), "MetricsTracker not initialized"
    assert isinstance(app.metrics_tracker, MetricsTracker), "Wrong type for metrics_tracker"

    assert hasattr(app, 'bg_panel'), "BackgroundTaskPanel not initialized"
    assert isinstance(app.bg_panel, BackgroundTaskPanel), "Wrong type for bg_panel"

    assert hasattr(app, 'thinking_indicator'), "ThinkingIndicator not initialized"
    assert isinstance(app.thinking_indicator, ThinkingIndicator), "Wrong type for thinking_indicator"

    assert hasattr(app, 'phase_progress'), "PhaseProgress not initialized"
    assert isinstance(app.phase_progress, PhaseProgress), "Wrong type for phase_progress"

    print("✓ All widgets initialized correctly")


def test_progress_spinner():
    """Test ProgressSpinner widget."""
    print("\nTesting ProgressSpinner...")

    spinner = ProgressSpinner()
    spinner.start()

    # Test frame generation
    frame1 = spinner.next_frame(tokens=1000)
    assert "⏺" in frame1 or "✶" in frame1, "Spinner frame not found"
    assert "Thinking" in frame1 or "Analyzing" in frame1, "Spinner verb not found"

    frame2 = spinner.next_frame(tokens=2000)
    assert frame1 != frame2, "Spinner should animate"

    spinner.stop()
    print("✓ ProgressSpinner works correctly")


def test_agent_panel():
    """Test AgentExecutionPanel widget."""
    print("\nTesting AgentExecutionPanel...")

    panel = AgentExecutionPanel()

    # Add agents
    panel.add_agent("agent1", "Test Agent 1")
    panel.add_agent("agent2", "Test Agent 2")

    # Update agent
    panel.update_agent("agent1", tool_uses=5, tokens=1000, status="running")

    # Render collapsed
    output = panel.render(expanded=False)
    assert "Running 2 agents" in output, "Agent count not shown"
    assert "ctrl+o to expand" in output, "Expand hint not shown"

    # Render expanded
    output = panel.render(expanded=True)
    assert "Test Agent 1" in output, "Agent 1 not shown"
    assert "Test Agent 2" in output, "Agent 2 not shown"
    assert "5 tool uses" in output, "Tool uses not shown"

    print("✓ AgentExecutionPanel works correctly")


def test_metrics_tracker():
    """Test MetricsTracker widget."""
    print("\nTesting MetricsTracker...")

    tracker = MetricsTracker()

    # Start operation
    tracker.start_operation("op1", "turn")

    # End operation
    tracker.end_operation("op1", tokens_in=500, tokens_out=1000, model="claude-sonnet-4-6")

    # Format summary
    summary = tracker.format_summary("op1")
    assert "tokens" in summary, "Tokens not in summary"
    assert "claude-sonnet-4-6" in summary, "Model not in summary"

    print("✓ MetricsTracker works correctly")


def test_background_panel():
    """Test BackgroundTaskPanel widget."""
    print("\nTesting BackgroundTaskPanel...")

    panel = BackgroundTaskPanel()

    # Add tasks
    panel.add_task("task1", "Background Task 1", "general-purpose")
    panel.add_task("task2", "Background Task 2", "executor")

    # Toggle visibility
    panel.toggle_visibility()
    assert panel.visible, "Panel should be visible"

    # Render
    output = panel.render()
    assert "background tasks" in output, "Task count not shown"
    assert "Background Task 1" in output, "Task 1 not shown"

    print("✓ BackgroundTaskPanel works correctly")


def test_thinking_indicator():
    """Test ThinkingIndicator widget."""
    print("\nTesting ThinkingIndicator...")

    indicator = ThinkingIndicator()

    # Start thinking
    indicator.start_thinking()
    assert indicator.is_thinking(), "Should be thinking"

    # End thinking
    import time
    time.sleep(0.1)
    indicator.end_thinking()
    elapsed = indicator.get_duration()
    assert elapsed > 0, "Elapsed time should be positive"
    assert not indicator.is_thinking(), "Should not be thinking"

    print("✓ ThinkingIndicator works correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("UX Widgets Integration Test Suite")
    print("=" * 60)

    try:
        test_widget_initialization()
        test_progress_spinner()
        test_agent_panel()
        test_metrics_tracker()
        test_background_panel()
        test_thinking_indicator()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
