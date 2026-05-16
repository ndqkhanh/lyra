"""Tests for Phase A Multimodal Enhancement."""

import pytest

from lyra_cli.multimodal_enhanced.hop_trace import (
    MultimodalHopTracer,
    MultimodalFrame,
)
from lyra_cli.multimodal_enhanced.mer import (
    MultimodalAERSystem,
)


# ============================================================================
# Hop Trace Tests
# ============================================================================

@pytest.fixture
def hop_tracer():
    """Create hop tracer."""
    return MultimodalHopTracer()


def test_hop_start_chain(hop_tracer):
    """Test starting a hop trace chain."""
    chain_id = hop_tracer.start_chain("Test task")

    assert chain_id is not None
    assert hop_tracer.stats["total_chains"] == 1


def test_hop_add_hop(hop_tracer):
    """Test adding a hop to chain."""
    chain_id = hop_tracer.start_chain("Test task")

    hop_id = hop_tracer.add_hop(
        chain_id=chain_id,
        reasoning_step="Step 1: Analyze input",
        input_query="What is X?",
        output_answer="X is Y",
        confidence=0.9,
    )

    assert hop_id is not None
    assert hop_tracer.stats["total_hops"] == 1


def test_hop_add_frame(hop_tracer):
    """Test adding a frame to hop."""
    chain_id = hop_tracer.start_chain("Test task")
    hop_id = hop_tracer.add_hop(chain_id, "Step 1")

    frame_id = hop_tracer.add_frame(
        chain_id=chain_id,
        hop_id=hop_id,
        screenshot="screenshot_data",
        dom_snapshot={"html": "<div>Test</div>"},
    )

    assert frame_id is not None
    assert hop_tracer.stats["total_frames"] == 1


def test_hop_add_region_evidence(hop_tracer):
    """Test adding region evidence."""
    chain_id = hop_tracer.start_chain("Test task")
    hop_id = hop_tracer.add_hop(chain_id, "Step 1")
    frame_id = hop_tracer.add_frame(chain_id, hop_id, screenshot="data")

    region_id = hop_tracer.add_region_evidence(
        frame_id=frame_id,
        bounding_box={"x": 10, "y": 10, "width": 100, "height": 50},
        evidence_type="text",
        content="Sample text",
        confidence=0.95,
    )

    assert region_id is not None
    assert hop_tracer.stats["total_regions"] == 1


def test_hop_complete_chain(hop_tracer):
    """Test completing a chain."""
    chain_id = hop_tracer.start_chain("Test task")
    hop_tracer.add_hop(chain_id, "Step 1")

    hop_tracer.complete_chain(chain_id, final_answer="Final result")

    chain = hop_tracer.get_chain(chain_id)
    assert chain.completed_at is not None
    assert chain.final_answer == "Final result"


def test_hop_export_chain(hop_tracer):
    """Test exporting chain."""
    chain_id = hop_tracer.start_chain("Test task")
    hop_id = hop_tracer.add_hop(chain_id, "Step 1")
    hop_tracer.add_frame(chain_id, hop_id, screenshot="data")

    exported = hop_tracer.export_chain(chain_id)

    assert exported is not None
    assert exported["chain_id"] == chain_id
    assert exported["hop_count"] == 1


# ============================================================================
# Multimodal AER Tests
# ============================================================================

@pytest.fixture
def mer_system():
    """Create MER system."""
    return MultimodalAERSystem()


def test_mer_start_execution(mer_system):
    """Test starting multimodal execution."""
    record_id = mer_system.start_execution(
        agent_id="agent_001",
        session_id="session_001",
        task_description="Test task",
    )

    assert record_id is not None
    assert mer_system.stats["total_records"] == 1


def test_mer_record_action_with_frames(mer_system):
    """Test recording action with frames."""
    record_id = mer_system.start_execution(
        "agent_001", "session_001", "Test task"
    )

    frame = MultimodalFrame(
        frame_id="frame_001",
        timestamp="2026-05-16T12:00:00",
        screenshot="screenshot_data",
    )

    action_id = mer_system.record_action_with_frames(
        agent_id="agent_001",
        action_type="tool_call",
        description="Test action",
        frames=[frame],
    )

    assert action_id is not None
    assert mer_system.stats["total_actions"] == 1
    assert mer_system.stats["total_frames"] == 1


def test_mer_add_frame(mer_system):
    """Test adding frame to record."""
    mer_system.start_execution("agent_001", "session_001", "Test task")

    frame = MultimodalFrame(
        frame_id="frame_001",
        timestamp="2026-05-16T12:00:00",
    )

    mer_system.add_frame_to_record("agent_001", frame)

    assert mer_system.stats["total_frames"] == 1


def test_mer_end_execution(mer_system):
    """Test ending execution."""
    record_id = mer_system.start_execution(
        "agent_001", "session_001", "Test task"
    )

    mer_system.end_execution("agent_001", "success", "Result")

    record = mer_system.get_record(record_id)
    assert record.end_time is not None
    assert record.final_status == "success"


def test_mer_export_record(mer_system):
    """Test exporting record."""
    record_id = mer_system.start_execution(
        "agent_001", "session_001", "Test task"
    )

    mer_system.record_action_with_frames(
        "agent_001", "tool_call", "Test action"
    )

    exported = mer_system.export_record(record_id)

    assert exported is not None
    assert exported["record_id"] == record_id
    assert exported["action_count"] == 1
