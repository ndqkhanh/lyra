"""Tests for MCP Server Surface (Phase M7)."""
import pytest

from lyra_core.memory.access_policy import (
    Permission,
    Resource,
    Subject,
    get_policy_graph,
    reset_policy_graph,
)
from lyra_core.memory.digest_bus import get_digest_bus, reset_digest_bus
from lyra_core.memory.mcp_tools import (
    mcp_digest,
    mcp_forget,
    mcp_list_decisions,
    mcp_pin,
    mcp_recall,
    mcp_recall_digests,
    mcp_skill_invoke,
    mcp_write,
)
from lyra_core.memory.schema import MemoryTier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset global singletons before each test."""
    reset_policy_graph()
    reset_digest_bus()
    yield
    reset_policy_graph()
    reset_digest_bus()


# ---------------------------------------------------------------------------
# mcp_recall tests
# ---------------------------------------------------------------------------


def test_mcp_recall_empty():
    result = mcp_recall(query="test query")
    assert result["count"] == 0
    assert result["fragments"] == []
    assert result["query"] == "test query"


def test_mcp_recall_with_filters():
    result = mcp_recall(
        query="test query",
        tier="t1_session",
        fragment_type="fact",
        limit=5,
    )
    assert result["count"] == 0
    assert result["filters"]["tier"] == "t1_session"
    assert result["filters"]["fragment_type"] == "fact"
    assert result["filters"]["limit"] == 5


# ---------------------------------------------------------------------------
# mcp_write tests
# ---------------------------------------------------------------------------


def test_mcp_write_success():
    # Grant write permission
    graph = get_policy_graph()
    subject = Subject.agent("agent-1")
    resource = Resource.tier(MemoryTier.T1_SESSION)
    graph.grant(subject, resource, {Permission.WRITE})

    result = mcp_write(
        content="Test fact",
        fragment_type="fact",
        tier="t1_session",
        agent_id="agent-1",
    )

    assert result["status"] == "created"
    assert result["tier"] == "t1_session"
    assert result["type"] == "fact"
    assert "fragment_id" in result


def test_mcp_write_invalid_fragment_type():
    result = mcp_write(
        content="Test fact",
        fragment_type="invalid_type",
        tier="t1_session",
    )

    assert "error" in result
    assert "Invalid fragment_type" in result["error"]


def test_mcp_write_invalid_tier():
    result = mcp_write(
        content="Test fact",
        fragment_type="fact",
        tier="invalid_tier",
    )

    assert "error" in result
    assert "Invalid tier" in result["error"]


def test_mcp_write_access_denied():
    result = mcp_write(
        content="Test fact",
        fragment_type="fact",
        tier="t1_session",
        agent_id="agent-1",
    )

    assert "error" in result
    assert "Access denied" in result["error"]


# ---------------------------------------------------------------------------
# mcp_pin tests
# ---------------------------------------------------------------------------


def test_mcp_pin_access_denied():
    result = mcp_pin(fragment_id="t1:fact:123", user_id="user-1")

    assert "error" in result
    assert "Access denied" in result["error"]


def test_mcp_pin_success():
    # Grant write permission
    graph = get_policy_graph()
    subject = Subject.user("user-1")
    resource = Resource.fragment("t1:fact:123")
    graph.grant(subject, resource, {Permission.WRITE})

    result = mcp_pin(fragment_id="t1:fact:123", user_id="user-1")

    assert result["status"] == "pinned"
    assert result["fragment_id"] == "t1:fact:123"


# ---------------------------------------------------------------------------
# mcp_forget tests
# ---------------------------------------------------------------------------


def test_mcp_forget_access_denied():
    result = mcp_forget(fragment_id="t1:fact:123", user_id="user-1")

    assert "error" in result
    assert "Access denied" in result["error"]


def test_mcp_forget_success():
    # Grant delete permission
    graph = get_policy_graph()
    subject = Subject.user("user-1")
    resource = Resource.fragment("t1:fact:123")
    graph.grant(subject, resource, {Permission.DELETE})

    result = mcp_forget(fragment_id="t1:fact:123", user_id="user-1")

    assert result["status"] == "forgotten"
    assert result["fragment_id"] == "t1:fact:123"
    assert "invalid_at" in result


# ---------------------------------------------------------------------------
# mcp_list_decisions tests
# ---------------------------------------------------------------------------


def test_mcp_list_decisions_empty():
    result = mcp_list_decisions()
    assert result["count"] == 0
    assert result["decisions"] == []


def test_mcp_list_decisions_with_filters():
    result = mcp_list_decisions(tier="t2_semantic", limit=20)
    assert result["count"] == 0
    assert result["filters"]["tier"] == "t2_semantic"
    assert result["filters"]["limit"] == 20


# ---------------------------------------------------------------------------
# mcp_skill_invoke tests
# ---------------------------------------------------------------------------


def test_mcp_skill_invoke_not_found():
    result = mcp_skill_invoke(skill_name="test_skill")
    assert result["skill_name"] == "test_skill"
    assert result["executable"] is False
    assert "not found" in result["content"]


# ---------------------------------------------------------------------------
# mcp_digest tests
# ---------------------------------------------------------------------------


def test_mcp_digest_success():
    result = mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="Ran tests",
        findings=["Test passed"],
        open_questions=["Should we add more tests?"],
        next_intent="Add more tests",
        confidence=0.8,
    )

    assert result["status"] == "recorded"
    assert result["digest_id"] == "task-123:agent-1:1"
    assert result["last_action"] == "Ran tests"


def test_mcp_digest_minimal():
    result = mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="Ran tests",
    )

    assert result["status"] == "recorded"
    assert result["digest_id"] == "task-123:agent-1:1"


# ---------------------------------------------------------------------------
# mcp_recall_digests tests
# ---------------------------------------------------------------------------


def test_mcp_recall_digests_empty():
    result = mcp_recall_digests(task_id="task-123")
    assert result["count"] == 0
    assert result["digests"] == []
    assert result["summary"] == ""


def test_mcp_recall_digests_with_data():
    # Emit some digests
    mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="Action 1",
    )
    mcp_digest(
        agent_id="agent-2",
        task_id="task-123",
        step=1,
        last_action="Action 2",
    )

    result = mcp_recall_digests(task_id="task-123")

    assert result["count"] == 2
    assert len(result["digests"]) == 2
    assert result["summary"] == "agent-1: Action 1; agent-2: Action 2"


def test_mcp_recall_digests_filter_by_agent():
    # Emit digests from multiple agents
    mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="Action 1",
    )
    mcp_digest(
        agent_id="agent-2",
        task_id="task-123",
        step=1,
        last_action="Action 2",
    )

    result = mcp_recall_digests(task_id="task-123", agent_id="agent-1")

    assert result["count"] == 1
    assert result["digests"][0]["agent_id"] == "agent-1"


def test_mcp_recall_digests_limit():
    # Emit multiple digests
    for i in range(5):
        mcp_digest(
            agent_id=f"agent-{i}",
            task_id="task-123",
            step=1,
            last_action=f"Action {i}",
        )

    result = mcp_recall_digests(task_id="task-123", limit=3)

    assert result["count"] == 3
    assert len(result["digests"]) == 3


def test_mcp_recall_digests_latest_only():
    # Emit multiple steps from same agent
    mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=1,
        last_action="Action 1",
    )
    mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=2,
        last_action="Action 2",
    )
    mcp_digest(
        agent_id="agent-1",
        task_id="task-123",
        step=3,
        last_action="Action 3",
    )

    result = mcp_recall_digests(task_id="task-123")

    # Should only get latest digest (step 3)
    assert result["count"] == 1
    assert result["digests"][0]["step"] == 3
    assert result["digests"][0]["last_action"] == "Action 3"
