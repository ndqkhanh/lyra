"""Tests for context visualization."""


from lyra_ui import (
    ContextComponent,
    ContextManager,
    ContextRingVisualizer,
    ContextTracker,
    ContextUsage,
)

# Context Tracker Tests


def test_context_tracker_init():
    """Test context tracker initialization."""
    tracker = ContextTracker(total_tokens=200000)
    assert tracker.total_tokens == 200000
    assert len(tracker.components) == len(ContextComponent)


def test_context_tracker_add_tokens():
    """Test adding tokens."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    assert tracker.get_tokens(ContextComponent.SYSTEM_PROMPT) == 1000

    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 500)
    assert tracker.get_tokens(ContextComponent.SYSTEM_PROMPT) == 1500


def test_context_tracker_set_tokens():
    """Test setting tokens."""
    tracker = ContextTracker()
    tracker.set_tokens(ContextComponent.CONVERSATION, 5000)
    assert tracker.get_tokens(ContextComponent.CONVERSATION) == 5000


def test_context_tracker_get_total_used():
    """Test getting total tokens used."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 5000)
    tracker.add_tokens(ContextComponent.TOOL_RESULTS, 2000)
    assert tracker.get_total_used() == 8000


def test_context_tracker_get_percentage():
    """Test getting component percentage."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 4000)
    # Total = 5000, conversation = 4000
    assert tracker.get_percentage(ContextComponent.CONVERSATION) == 80.0


def test_context_tracker_get_total_percentage():
    """Test getting total percentage."""
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 10000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 40000)
    # Total used = 50000, total = 100000
    assert tracker.get_total_percentage() == 50.0


def test_context_tracker_get_breakdown():
    """Test getting usage breakdown."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 5000)

    breakdown = tracker.get_breakdown()
    assert len(breakdown) == 2
    assert all(isinstance(usage, ContextUsage) for usage in breakdown)


def test_context_tracker_clear_component():
    """Test clearing component."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.clear_component(ContextComponent.SYSTEM_PROMPT)
    assert tracker.get_tokens(ContextComponent.SYSTEM_PROMPT) == 0


def test_context_tracker_clear_all():
    """Test clearing all components."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 5000)
    tracker.clear_all()
    assert tracker.get_total_used() == 0


# Context Ring Visualizer Tests


def test_context_ring_visualizer_init():
    """Test context ring visualizer initialization."""
    viz = ContextRingVisualizer()
    assert viz.console is not None


def test_context_ring_visualizer_render_ring():
    """Test rendering context ring."""
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 10000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 40000)

    viz = ContextRingVisualizer()
    ring = viz.render_ring(tracker)
    assert "50,000" in ring
    assert "100,000" in ring
    assert "50.0%" in ring


def test_context_ring_visualizer_color_coding():
    """Test color coding in ring."""
    viz = ContextRingVisualizer()

    # Green (< 50%)
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 30000)
    ring = viz.render_ring(tracker)
    assert "green" in ring

    # Yellow (50-80%)
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 60000)
    ring = viz.render_ring(tracker)
    assert "yellow" in ring

    # Red (> 80%)
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 90000)
    ring = viz.render_ring(tracker)
    assert "red" in ring


def test_context_ring_visualizer_render_breakdown():
    """Test rendering breakdown table."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 5000)

    viz = ContextRingVisualizer()
    table = viz.render_breakdown(tracker)
    assert table is not None


def test_context_ring_visualizer_display():
    """Test displaying visualization."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 5000)

    viz = ContextRingVisualizer()
    viz.display(tracker)  # Should not raise error


# Context Manager Tests


def test_context_manager_init():
    """Test context manager initialization."""
    tracker = ContextTracker()
    manager = ContextManager(tracker)
    assert manager.tracker is tracker


def test_context_manager_export():
    """Test exporting context."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 5000)

    manager = ContextManager(tracker)
    data = manager.export_context()

    assert data["system_prompt"] == 1000
    assert data["conversation"] == 5000


def test_context_manager_import():
    """Test importing context."""
    tracker = ContextTracker()
    manager = ContextManager(tracker)

    data = {
        "system_prompt": 1000,
        "conversation": 5000,
        "tool_results": 2000,
    }

    manager.import_context(data)

    assert tracker.get_tokens(ContextComponent.SYSTEM_PROMPT) == 1000
    assert tracker.get_tokens(ContextComponent.CONVERSATION) == 5000
    assert tracker.get_tokens(ContextComponent.TOOL_RESULTS) == 2000


def test_context_manager_prune():
    """Test pruning component."""
    tracker = ContextTracker()
    tracker.add_tokens(ContextComponent.CONVERSATION, 10000)

    manager = ContextManager(tracker)
    manager.prune_component(ContextComponent.CONVERSATION, 5000)

    assert tracker.get_tokens(ContextComponent.CONVERSATION) == 5000


def test_context_manager_recommendations_healthy():
    """Test recommendations for healthy usage."""
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 8000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 10000)
    tracker.add_tokens(ContextComponent.TOOL_RESULTS, 7000)
    tracker.add_tokens(ContextComponent.CODE_CONTEXT, 5000)

    manager = ContextManager(tracker)
    recommendations = manager.get_recommendations()

    assert len(recommendations) > 0
    # With 30% total usage and no component >40%, should be healthy
    assert recommendations[0] == "✓ Context usage is healthy."


def test_context_manager_recommendations_high_usage():
    """Test recommendations for high usage."""
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 85000)

    manager = ContextManager(tracker)
    recommendations = manager.get_recommendations()

    assert len(recommendations) > 0
    assert any("high" in rec.lower() for rec in recommendations)


def test_context_manager_recommendations_component_heavy():
    """Test recommendations for component-heavy usage."""
    tracker = ContextTracker(total_tokens=100000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 50000)

    manager = ContextManager(tracker)
    recommendations = manager.get_recommendations()

    assert len(recommendations) > 0
    assert any("Conversation" in rec for rec in recommendations)


# Integration Tests


def test_full_context_workflow():
    """Test complete context workflow."""
    # Create tracker
    tracker = ContextTracker(total_tokens=200000)

    # Add tokens
    tracker.add_tokens(ContextComponent.SYSTEM_PROMPT, 5000)
    tracker.add_tokens(ContextComponent.CONVERSATION, 50000)
    tracker.add_tokens(ContextComponent.TOOL_RESULTS, 20000)
    tracker.add_tokens(ContextComponent.CODE_CONTEXT, 15000)

    # Check totals
    assert tracker.get_total_used() == 90000
    assert tracker.get_total_percentage() == 45.0

    # Visualize
    viz = ContextRingVisualizer()
    ring = viz.render_ring(tracker)
    assert "90,000" in ring

    # Get breakdown
    breakdown = tracker.get_breakdown()
    assert len(breakdown) == 4

    # Export
    manager = ContextManager(tracker)
    data = manager.export_context()
    assert data["conversation"] == 50000

    # Get recommendations
    recommendations = manager.get_recommendations()
    assert len(recommendations) > 0


def test_context_export_import_roundtrip():
    """Test export/import roundtrip."""
    # Create and populate tracker
    tracker1 = ContextTracker()
    tracker1.add_tokens(ContextComponent.SYSTEM_PROMPT, 1000)
    tracker1.add_tokens(ContextComponent.CONVERSATION, 5000)
    tracker1.add_tokens(ContextComponent.TOOL_RESULTS, 2000)

    # Export
    manager1 = ContextManager(tracker1)
    data = manager1.export_context()

    # Import to new tracker
    tracker2 = ContextTracker()
    manager2 = ContextManager(tracker2)
    manager2.import_context(data)

    # Verify
    assert tracker2.get_tokens(ContextComponent.SYSTEM_PROMPT) == 1000
    assert tracker2.get_tokens(ContextComponent.CONVERSATION) == 5000
    assert tracker2.get_tokens(ContextComponent.TOOL_RESULTS) == 2000
    assert tracker2.get_total_used() == tracker1.get_total_used()


def test_context_usage_dataclass():
    """Test ContextUsage dataclass."""
    usage = ContextUsage(
        component=ContextComponent.CONVERSATION,
        tokens=5000,
        percentage=50.0,
        description="Conversation History",
    )

    assert usage.component == ContextComponent.CONVERSATION
    assert usage.tokens == 5000
    assert usage.percentage == 50.0
    assert usage.description == "Conversation History"
