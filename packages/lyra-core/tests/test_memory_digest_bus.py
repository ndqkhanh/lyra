"""Tests for SubAgentDigest broadcast bus (Phase M5)."""
import pytest

from lyra_core.memory.digest_bus import (
    DigestBus,
    DigestStore,
    DigestSummary,
    get_digest_bus,
    reset_digest_bus,
)
from lyra_core.memory.schema import (
    Fragment,
    FragmentType,
    MemoryTier,
    Provenance,
    SubAgentDigest,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    return DigestStore()


@pytest.fixture
def bus():
    return DigestBus()


@pytest.fixture
def sample_digest():
    return SubAgentDigest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="ran pytest tests/test_auth.py; 3 failures",
        findings=["JWT secret not set", "Mock user missing email"],
        open_questions=["Should we use test fixtures?"],
        next_intent="Fix JWT configuration",
        confidence=0.8,
    )


# ---------------------------------------------------------------------------
# DigestStore tests
# ---------------------------------------------------------------------------


def test_store_write_and_get_latest(store, sample_digest):
    store.write(sample_digest)
    latest = store.get_latest("task-123", "agent-1")
    assert latest is not None
    assert latest.agent_id == "agent-1"
    assert latest.step == 1
    assert latest.last_action == "ran pytest tests/test_auth.py; 3 failures"


def test_store_get_latest_returns_highest_step(store):
    for step in [1, 3, 2]:
        digest = SubAgentDigest(
            agent_id="agent-1",
            task_id="task-123",
            step=step,
            last_action=f"step {step}",
        )
        store.write(digest)

    latest = store.get_latest("task-123", "agent-1")
    assert latest is not None
    assert latest.step == 3


def test_store_get_latest_returns_none_when_empty(store):
    latest = store.get_latest("task-999", "agent-999")
    assert latest is None


def test_store_get_all_latest_multiple_agents(store):
    for agent_id in ["agent-1", "agent-2", "agent-3"]:
        for step in [1, 2]:
            digest = SubAgentDigest(
                agent_id=agent_id,
                task_id="task-123",
                step=step,
                last_action=f"{agent_id} step {step}",
            )
            store.write(digest)

    all_latest = store.get_all_latest("task-123")
    assert len(all_latest) == 3
    assert all_latest[0].agent_id == "agent-1"
    assert all_latest[0].step == 2
    assert all_latest[1].agent_id == "agent-2"
    assert all_latest[2].agent_id == "agent-3"


def test_store_get_all_latest_empty_task(store):
    all_latest = store.get_all_latest("task-999")
    assert all_latest == []


def test_store_get_history(store):
    for step in [1, 3, 2, 4]:
        digest = SubAgentDigest(
            agent_id="agent-1",
            task_id="task-123",
            step=step,
            last_action=f"step {step}",
        )
        store.write(digest)

    history = store.get_history("task-123", "agent-1")
    assert len(history) == 4
    assert [d.step for d in history] == [1, 2, 3, 4]


def test_store_get_history_empty(store):
    history = store.get_history("task-999", "agent-999")
    assert history == []


def test_store_clear_task(store):
    # Write digests for two tasks
    for task_id in ["task-1", "task-2"]:
        for agent_id in ["agent-1", "agent-2"]:
            digest = SubAgentDigest(
                agent_id=agent_id,
                task_id=task_id,
                step=1,
                last_action="action",
            )
            store.write(digest)

    assert len(store) == 4

    store.clear_task("task-1")
    assert len(store) == 2

    # task-1 should be gone
    assert store.get_all_latest("task-1") == []
    # task-2 should remain
    assert len(store.get_all_latest("task-2")) == 2


def test_store_overwrite_same_step(store):
    digest1 = SubAgentDigest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="first action",
    )
    digest2 = SubAgentDigest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="second action",
    )

    store.write(digest1)
    store.write(digest2)

    latest = store.get_latest("task-123", "agent-1")
    assert latest is not None
    assert latest.last_action == "second action"
    assert len(store) == 1


# ---------------------------------------------------------------------------
# DigestBus tests
# ---------------------------------------------------------------------------


def test_bus_emit_and_recall(bus, sample_digest):
    bus.emit(sample_digest)
    summary = bus.recall_digests("task-123")
    assert len(summary.digests) == 1
    assert summary.digests[0].agent_id == "agent-1"


def test_bus_recall_multiple_agents(bus):
    for agent_id in ["agent-1", "agent-2", "agent-3"]:
        digest = SubAgentDigest(
            agent_id=agent_id,
            task_id="task-123",
            step=1,
            last_action=f"{agent_id} action",
        )
        bus.emit(digest)

    summary = bus.recall_digests("task-123")
    assert len(summary.digests) == 3


def test_bus_recall_empty_task(bus):
    summary = bus.recall_digests("task-999")
    assert len(summary.digests) == 0
    assert summary.render() == ""


def test_bus_get_agent_history(bus):
    for step in [1, 2, 3]:
        digest = SubAgentDigest(
            agent_id="agent-1",
            task_id="task-123",
            step=step,
            last_action=f"step {step}",
        )
        bus.emit(digest)

    history = bus.get_agent_history("task-123", "agent-1")
    assert len(history) == 3
    assert [d.step for d in history] == [1, 2, 3]


def test_bus_clear_task(bus):
    for agent_id in ["agent-1", "agent-2"]:
        digest = SubAgentDigest(
            agent_id=agent_id,
            task_id="task-123",
            step=1,
            last_action="action",
        )
        bus.emit(digest)

    bus.clear_task("task-123")
    summary = bus.recall_digests("task-123")
    assert len(summary.digests) == 0


# ---------------------------------------------------------------------------
# DigestSummary rendering tests
# ---------------------------------------------------------------------------


def test_summary_render_single_digest():
    digest = SubAgentDigest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="ran tests",
        findings=["3 failures"],
        next_intent="fix tests",
    )
    summary = DigestSummary(task_id="task-123", digests=[digest])
    rendered = summary.render(max_chars=600)

    assert "[Peer Agent Digests]" in rendered
    assert "agent-1" in rendered
    assert "ran tests" in rendered
    assert "3 failures" in rendered
    assert "fix tests" in rendered


def test_summary_render_multiple_digests():
    digests = [
        SubAgentDigest(
            agent_id=f"agent-{i}",
            task_id="task-123",
            step=1,
            last_action=f"action {i}",
        )
        for i in range(3)
    ]
    summary = DigestSummary(task_id="task-123", digests=digests)
    rendered = summary.render(max_chars=600)

    assert "agent-0" in rendered
    assert "agent-1" in rendered
    assert "agent-2" in rendered


def test_summary_render_truncation():
    # Create many digests that exceed max_chars
    digests = [
        SubAgentDigest(
            agent_id=f"agent-{i}",
            task_id="task-123",
            step=1,
            last_action="x" * 100,  # long action
            findings=["finding 1", "finding 2", "finding 3"],
        )
        for i in range(10)
    ]
    summary = DigestSummary(task_id="task-123", digests=digests)
    rendered = summary.render(max_chars=300)

    assert len(rendered) <= 300
    assert summary.truncated is True
    assert "... (truncated)" in rendered


def test_summary_render_empty():
    summary = DigestSummary(task_id="task-123", digests=[])
    rendered = summary.render()
    assert rendered == ""


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------


def test_detect_conflicts_no_conflicts(bus):
    prov1 = Provenance(agent_id="agent-1", session_id="s1", task_id="task-123")
    prov2 = Provenance(agent_id="agent-2", session_id="s1", task_id="task-123")

    # Same content, no conflict
    frag1 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov1,
        entities=["auth", "JWT"],
    )
    frag2 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov2,
        entities=["auth", "JWT"],
    )

    conflicts = bus.detect_conflicts([frag1, frag2], "task-123")
    assert len(conflicts) == 0


def test_detect_conflicts_different_agents_diverging_content(bus):
    prov1 = Provenance(agent_id="agent-1", session_id="s1", task_id="task-123")
    prov2 = Provenance(agent_id="agent-2", session_id="s1", task_id="task-123")

    # Same entities, different content
    frag1 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov1,
        entities=["auth", "JWT"],
    )
    frag2 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses OAuth2 flow",
        provenance=prov2,
        entities=["auth", "OAuth2"],
    )

    conflicts = bus.detect_conflicts([frag1, frag2], "task-123")
    assert len(conflicts) == 1
    assert conflicts[0].reason == "agent_disagreement"
    assert conflicts[0].resolution == "human_required"


def test_detect_conflicts_same_agent_no_conflict(bus):
    prov = Provenance(agent_id="agent-1", session_id="s1", task_id="task-123")

    # Same agent, different content — not a cross-agent conflict
    frag1 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov,
        entities=["auth", "JWT"],
    )
    frag2 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses OAuth2 flow",
        provenance=prov,
        entities=["auth", "OAuth2"],
    )

    conflicts = bus.detect_conflicts([frag1, frag2], "task-123")
    assert len(conflicts) == 0


def test_detect_conflicts_different_tasks_no_conflict(bus):
    prov1 = Provenance(agent_id="agent-1", session_id="s1", task_id="task-123")
    prov2 = Provenance(agent_id="agent-2", session_id="s1", task_id="task-456")

    frag1 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov1,
        entities=["auth", "JWT"],
    )
    frag2 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses OAuth2 flow",
        provenance=prov2,
        entities=["auth", "OAuth2"],
    )

    # Only check task-123
    conflicts = bus.detect_conflicts([frag1, frag2], "task-123")
    assert len(conflicts) == 0


def test_detect_conflicts_no_entity_overlap(bus):
    prov1 = Provenance(agent_id="agent-1", session_id="s1", task_id="task-123")
    prov2 = Provenance(agent_id="agent-2", session_id="s1", task_id="task-123")

    # Different entities, no conflict
    frag1 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov1,
        entities=["auth", "JWT"],
    )
    frag2 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="database uses postgres",
        provenance=prov2,
        entities=["database", "postgres"],
    )

    conflicts = bus.detect_conflicts([frag1, frag2], "task-123")
    assert len(conflicts) == 0


def test_detect_conflicts_logged_in_bus(bus):
    prov1 = Provenance(agent_id="agent-1", session_id="s1", task_id="task-123")
    prov2 = Provenance(agent_id="agent-2", session_id="s1", task_id="task-123")

    frag1 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses JWT tokens",
        provenance=prov1,
        entities=["auth", "JWT"],
    )
    frag2 = Fragment.make(
        tier=MemoryTier.T1_SESSION,
        type=FragmentType.FACT,
        content="auth uses OAuth2 flow",
        provenance=prov2,
        entities=["auth", "OAuth2"],
    )

    assert len(bus.conflicts) == 0
    bus.detect_conflicts([frag1, frag2], "task-123")
    assert len(bus.conflicts) == 1


# ---------------------------------------------------------------------------
# Global singleton tests
# ---------------------------------------------------------------------------


def test_get_digest_bus_singleton():
    reset_digest_bus()
    bus1 = get_digest_bus()
    bus2 = get_digest_bus()
    assert bus1 is bus2


def test_reset_digest_bus():
    reset_digest_bus()
    bus1 = get_digest_bus()
    reset_digest_bus()
    bus2 = get_digest_bus()
    assert bus1 is not bus2


# ---------------------------------------------------------------------------
# Integration test: orchestrator workflow
# ---------------------------------------------------------------------------


def test_orchestrator_workflow(bus):
    """Simulate a multi-agent task with orchestrator digest retrieval."""
    task_id = "task-orchestrator-test"

    # Step 1: Three agents spawn and emit initial digests
    for i, agent_id in enumerate(["agent-1", "agent-2", "agent-3"]):
        digest = SubAgentDigest(
            agent_id=agent_id,
            task_id=task_id,
            step=1,
            last_action=f"initialized {agent_id}",
            findings=[f"ready to work on subtask {i+1}"],
            next_intent=f"start subtask {i+1}",
        )
        bus.emit(digest)

    # Step 2: Orchestrator retrieves all digests
    summary = bus.recall_digests(task_id, max_chars=600)
    assert len(summary.digests) == 3
    rendered = summary.render()
    assert "agent-1" in rendered
    assert "agent-2" in rendered
    assert "agent-3" in rendered

    # Step 3: Agents emit step 2 digests
    for i, agent_id in enumerate(["agent-1", "agent-2", "agent-3"]):
        digest = SubAgentDigest(
            agent_id=agent_id,
            task_id=task_id,
            step=2,
            last_action=f"completed subtask {i+1}",
            findings=[f"subtask {i+1} done"],
            confidence=0.9,
        )
        bus.emit(digest)

    # Step 4: Orchestrator retrieves updated digests (should get step 2)
    summary = bus.recall_digests(task_id)
    assert len(summary.digests) == 3
    assert all(d.step == 2 for d in summary.digests)

    # Step 5: Task completes, cleanup
    bus.clear_task(task_id)
    summary = bus.recall_digests(task_id)
    assert len(summary.digests) == 0
