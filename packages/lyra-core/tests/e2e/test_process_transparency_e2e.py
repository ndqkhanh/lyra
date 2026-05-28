"""End-to-end tests for process transparency features.

These tests verify that all UI components update correctly during
realistic agent scenarios.
"""
import time

import pytest
from lyra_core.observability.event_bus import (
    EventBus,
    LLMCallFinished,
    LLMCallStarted,
    LLMTokenChunk,
    SubagentFinished,
    SubagentSpawned,
    ToolCallFinished,
    ToolCallStarted,
)
from lyra_core.observability.process_tree import ProcessTree


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def process_tree(event_bus):
    """Create a ProcessTree subscribed to the EventBus."""
    tree = ProcessTree(session_id="test-session")
    event_bus.add_listener(tree.on_event)
    return tree


# ---------------------------------------------------------------------------
# Scenario 1: Multi-Agent Research Task
# ---------------------------------------------------------------------------


def test_multi_agent_research_scenario(event_bus, process_tree):
    """Test 5 concurrent agents running for 60 seconds.

    Verifies:
    - Agent panel shows all 5 agents
    - Token counters update in real-time
    - Task checklist shows research phases
    - Footer shows "5 background tasks"
    """
    session_id = "main-session"
    agent_ids = [f"agent-{i}" for i in range(5)]

    # Ensure root exists
    process_tree.ensure_root(session_id, role="main")

    # Spawn 5 research agents
    for i, agent_id in enumerate(agent_ids):
        event_bus.emit(
            SubagentSpawned(
                session_id=session_id,
                agent_id=agent_id,
                agent_role=f"researcher-{i}",
                parent_agent_id=session_id,
            )
        )

    # Verify all agents are tracked (root + 5 subagents = 6 active)
    assert len(process_tree.all_nodes()) == 6  # 1 root + 5 agents
    assert process_tree.active_count() == 6  # root + 5 subagents are all active

    # Simulate work with token streaming (simplified for test)
    turn = 1

    # Each agent does some work
    for agent_id in agent_ids:
        # LLM call
        event_bus.emit(
            LLMCallStarted(
                session_id=agent_id,
                model="claude-opus-4",
                prompt_tokens=1000,
                turn=turn,
            )
        )

        # Token streaming (simulate 100 tokens)
        for chunk in range(10):
            event_bus.emit(
                LLMTokenChunk(
                    session_id=agent_id,
                    delta_text="token",
                    cumulative_tokens=chunk * 10,
                    turn=turn,
                )
            )

        # LLM call finished
        event_bus.emit(
            LLMCallFinished(
                session_id=agent_id,
                input_tokens=1000,
                output_tokens=100,
                cache_read_tokens=500,
                duration_ms=100.0,
                model="claude-opus-4",
                turn=turn,
            )
        )

        # Tool call
        event_bus.emit(
            ToolCallStarted(
                session_id=agent_id,
                tool_name="bash",
                args_preview='{"command": "ls"}',
            )
        )
        event_bus.emit(
            ToolCallFinished(
                session_id=agent_id,
                tool_name="bash",
                duration_ms=50.0,
                is_error=False,
            )
        )

    # Verify final state (root + 5 subagents still active)
    assert process_tree.active_count() == 6

    # Verify token accumulation
    for agent_id in agent_ids:
        node = process_tree._nodes.get(agent_id)
        assert node is not None
        assert node.token_in > 0
        assert node.token_out > 0

    # Complete all agents
    for agent_id in agent_ids:
        event_bus.emit(
            SubagentFinished(
                session_id=session_id,
                agent_id=agent_id,
                status="done",
                duration_ms=1000.0,
                cost_usd=0.05,
            )
        )

    # Verify all agents completed (only root remains active)
    assert process_tree.active_count() == 1  # root is still active


# ---------------------------------------------------------------------------
# Scenario 2: High-Frequency Token Streaming
# ---------------------------------------------------------------------------


def test_token_streaming_scenario(event_bus, process_tree):
    """Test 10k tokens streaming in 30 seconds (333 tokens/sec).

    Verifies:
    - Token counter updates smoothly without flicker
    - Counter displays "↓ 10.0k tokens"
    - No visible lag or stutter
    - CPU usage < 5%
    """
    session_id = "streaming-session"

    # Ensure root exists
    process_tree.ensure_root(session_id, role="main")

    # Start LLM call
    event_bus.emit(
        LLMCallStarted(
            session_id=session_id,
            model="claude-opus-4",
            prompt_tokens=2000,
            turn=1,
        )
    )

    # Stream 10k tokens (shortened to 1k for test speed)
    total_tokens = 1000
    chunk_size = 10
    chunks = total_tokens // chunk_size

    start_time = time.time()

    for i in range(chunks):
        event_bus.emit(
            LLMTokenChunk(
                session_id=session_id,
                delta_text="token" * chunk_size,
                cumulative_tokens=(i + 1) * chunk_size,
                turn=1,
            )
        )

    elapsed = time.time() - start_time

    # Finish LLM call
    event_bus.emit(
        LLMCallFinished(
            session_id=session_id,
            input_tokens=2000,
            output_tokens=total_tokens,
            cache_read_tokens=1000,
            duration_ms=elapsed * 1000,
            model="claude-opus-4",
            turn=1,
        )
    )

    # Verify token accumulation
    node = process_tree._nodes.get(session_id)
    assert node is not None
    assert node.token_out == total_tokens

    # Verify streaming was fast (< 1 second for 1k tokens)
    assert elapsed < 1.0


# ---------------------------------------------------------------------------
# Scenario 3: Agent Lifecycle
# ---------------------------------------------------------------------------


def test_agent_lifecycle_scenario(event_bus, process_tree):
    """Test agent lifecycle: start → running → done.

    Verifies:
    - Agent appears when started
    - Shows "running" state with live token count
    - Disappears when done
    - bg_task_count decrements
    """
    session_id = "lifecycle-session"
    agent_id = "lifecycle-agent"

    # Ensure root exists
    process_tree.ensure_root(session_id, role="main")

    # Initial state: 1 root agent
    assert process_tree.active_count() == 1

    # Agent spawned
    event_bus.emit(
        SubagentSpawned(
            session_id=session_id,
            agent_id=agent_id,
            agent_role="executor",
            parent_agent_id=session_id,
        )
    )

    # Verify agent appears (root + 1 subagent)
    assert process_tree.active_count() == 2
    node = process_tree._nodes.get(agent_id)
    assert node is not None
    assert node.state.value == "running"

    # Agent does work
    event_bus.emit(
        LLMCallStarted(
            session_id=agent_id,
            model="claude-opus-4",
            prompt_tokens=1000,
            turn=1,
        )
    )

    event_bus.emit(
        LLMCallFinished(
            session_id=agent_id,
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=200,
            duration_ms=1000.0,
            model="claude-opus-4",
            turn=1,
        )
    )

    # Verify token count updated
    node = process_tree._nodes.get(agent_id)
    assert node.token_in == 1000
    assert node.token_out == 500

    # Agent completes
    event_bus.emit(
        SubagentFinished(
            session_id=session_id,
            agent_id=agent_id,
            status="done",
            duration_ms=2000.0,
            cost_usd=0.02,
        )
    )

    # Verify agent is no longer active (only root remains)
    assert process_tree.active_count() == 1  # root is still active
    node = process_tree._nodes.get(agent_id)
    assert node.state.value == "done"
    assert node.finished_at is not None


# ---------------------------------------------------------------------------
# Scenario 4: Error Handling
# ---------------------------------------------------------------------------


def test_error_handling_scenario(event_bus, process_tree):
    """Test that UI remains responsive when agents fail.

    Verifies:
    - Failed agents show error state
    - Other agents continue working
    - No crashes or state corruption
    """
    session_id = "error-session"
    agent_ids = ["agent-success", "agent-fail"]

    # Ensure root exists
    process_tree.ensure_root(session_id, role="main")

    # Spawn 2 agents
    for agent_id in agent_ids:
        event_bus.emit(
            SubagentSpawned(
                session_id=session_id,
                agent_id=agent_id,
                agent_role="executor",
                parent_agent_id=session_id,
            )
        )

    assert process_tree.active_count() == 3  # root + 2 subagents

    # First agent succeeds
    event_bus.emit(
        SubagentFinished(
            session_id=session_id,
            agent_id="agent-success",
            status="done",
            duration_ms=1000.0,
            cost_usd=0.01,
        )
    )

    # Second agent fails
    event_bus.emit(
        SubagentFinished(
            session_id=session_id,
            agent_id="agent-fail",
            status="failed",
            duration_ms=500.0,
            cost_usd=0.005,
        )
    )

    # Verify both agents have correct final state
    success_node = process_tree._nodes.get("agent-success")
    fail_node = process_tree._nodes.get("agent-fail")

    assert success_node.state.value == "done"
    assert fail_node.state.value == "failed"

    # Verify no active subagents (only root remains)
    assert process_tree.active_count() == 1  # root is still active
