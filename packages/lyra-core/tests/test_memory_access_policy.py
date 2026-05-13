"""Tests for Access Policy Graph (Phase M6)."""
import pytest

from lyra_core.memory.access_policy import (
    ACLEntry,
    Permission,
    PolicyGraph,
    PromotionGate,
    PromotionRequest,
    Resource,
    Subject,
    get_policy_graph,
    get_promotion_gate,
    reset_policy_graph,
    reset_promotion_gate,
)
from lyra_core.memory.schema import MemoryTier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph():
    return PolicyGraph()


@pytest.fixture
def gate():
    return PromotionGate()


@pytest.fixture
def user_subject():
    return Subject.user("user-1")


@pytest.fixture
def agent_subject():
    return Subject.agent("agent-1")


@pytest.fixture
def fragment_resource():
    return Resource.fragment("t1:fact:fragment-123")


@pytest.fixture
def tier_resource():
    return Resource.tier(MemoryTier.T1_SESSION)


# ---------------------------------------------------------------------------
# Subject tests
# ---------------------------------------------------------------------------


def test_subject_user():
    subj = Subject.user("user-1")
    assert subj.type == "user"
    assert subj.id == "user-1"


def test_subject_agent():
    subj = Subject.agent("agent-1")
    assert subj.type == "agent"
    assert subj.id == "agent-1"


def test_subject_role():
    subj = Subject.role("orchestrator")
    assert subj.type == "role"
    assert subj.id == "orchestrator"


# ---------------------------------------------------------------------------
# Resource tests
# ---------------------------------------------------------------------------


def test_resource_fragment():
    res = Resource.fragment("fragment-123")
    assert res.type == "fragment"
    assert res.id == "fragment-123"


def test_resource_tier():
    res = Resource.tier(MemoryTier.T1_SESSION)
    assert res.type == "tier"
    assert res.id == "t1_session"


def test_resource_pattern():
    res = Resource.pattern("task:123:*")
    assert res.type == "pattern"
    assert res.id == "task:123:*"


# ---------------------------------------------------------------------------
# ACLEntry tests
# ---------------------------------------------------------------------------


def test_acl_entry_has_permission():
    entry = ACLEntry(
        subject=Subject.user("user-1"),
        resource=Resource.fragment("fragment-123"),
        permissions={Permission.READ, Permission.WRITE},
    )
    assert entry.has_permission(Permission.READ)
    assert entry.has_permission(Permission.WRITE)
    assert not entry.has_permission(Permission.DELETE)


# ---------------------------------------------------------------------------
# PolicyGraph grant/revoke tests
# ---------------------------------------------------------------------------


def test_graph_grant_permissions(graph, user_subject, fragment_resource):
    graph.grant(user_subject, fragment_resource, {Permission.READ})
    assert graph.check_access(user_subject, fragment_resource, Permission.READ)


def test_graph_grant_merge_permissions(graph, user_subject, fragment_resource):
    graph.grant(user_subject, fragment_resource, {Permission.READ})
    graph.grant(user_subject, fragment_resource, {Permission.WRITE})
    assert graph.check_access(user_subject, fragment_resource, Permission.READ)
    assert graph.check_access(user_subject, fragment_resource, Permission.WRITE)


def test_graph_revoke_specific_permissions(graph, user_subject, fragment_resource):
    graph.grant(
        user_subject, fragment_resource, {Permission.READ, Permission.WRITE}
    )
    graph.revoke(user_subject, fragment_resource, {Permission.WRITE})
    assert graph.check_access(user_subject, fragment_resource, Permission.READ)
    assert not graph.check_access(user_subject, fragment_resource, Permission.WRITE)


def test_graph_revoke_all_permissions(graph, user_subject, fragment_resource):
    graph.grant(
        user_subject, fragment_resource, {Permission.READ, Permission.WRITE}
    )
    graph.revoke(user_subject, fragment_resource, None)
    assert not graph.check_access(user_subject, fragment_resource, Permission.READ)
    assert not graph.check_access(user_subject, fragment_resource, Permission.WRITE)


# ---------------------------------------------------------------------------
# PolicyGraph check_access tests
# ---------------------------------------------------------------------------


def test_graph_check_access_direct_match(graph, user_subject, fragment_resource):
    graph.grant(user_subject, fragment_resource, {Permission.READ})
    assert graph.check_access(user_subject, fragment_resource, Permission.READ)
    assert not graph.check_access(user_subject, fragment_resource, Permission.WRITE)


def test_graph_check_access_tier_level(graph, user_subject):
    # Grant tier-level permission
    tier_resource = Resource.tier(MemoryTier.T1_SESSION)
    graph.grant(user_subject, tier_resource, {Permission.READ})

    # Check fragment in that tier
    fragment_resource = Resource.fragment("t1:fact:fragment-123")
    assert graph.check_access(user_subject, fragment_resource, Permission.READ)


def test_graph_check_access_pattern_match(graph, user_subject):
    # Grant pattern-based permission
    pattern_resource = Resource.pattern("task:123:*")
    graph.grant(user_subject, pattern_resource, {Permission.READ})

    # Check fragment matching pattern
    fragment_resource = Resource.fragment("task:123:fragment-1")
    assert graph.check_access(user_subject, fragment_resource, Permission.READ)

    # Check fragment not matching pattern
    other_fragment = Resource.fragment("task:456:fragment-2")
    assert not graph.check_access(user_subject, other_fragment, Permission.READ)


def test_graph_check_access_no_permission(graph, user_subject, fragment_resource):
    assert not graph.check_access(user_subject, fragment_resource, Permission.READ)


def test_graph_check_access_different_subject(
    graph, user_subject, agent_subject, fragment_resource
):
    graph.grant(user_subject, fragment_resource, {Permission.READ})
    assert not graph.check_access(agent_subject, fragment_resource, Permission.READ)


# ---------------------------------------------------------------------------
# PolicyGraph list operations tests
# ---------------------------------------------------------------------------


def test_graph_list_permissions(graph, user_subject):
    frag1 = Resource.fragment("fragment-1")
    frag2 = Resource.fragment("fragment-2")
    graph.grant(user_subject, frag1, {Permission.READ})
    graph.grant(user_subject, frag2, {Permission.WRITE})

    perms = graph.list_permissions(user_subject)
    assert len(perms) == 2
    assert any(p.resource == frag1 for p in perms)
    assert any(p.resource == frag2 for p in perms)


def test_graph_list_subjects(graph, user_subject, agent_subject, fragment_resource):
    graph.grant(user_subject, fragment_resource, {Permission.READ})
    graph.grant(agent_subject, fragment_resource, {Permission.WRITE})

    subjects = graph.list_subjects(fragment_resource)
    assert len(subjects) == 2
    assert user_subject in subjects
    assert agent_subject in subjects


def test_graph_clear(graph, user_subject, fragment_resource):
    graph.grant(user_subject, fragment_resource, {Permission.READ})
    graph.clear()
    assert not graph.check_access(user_subject, fragment_resource, Permission.READ)


# ---------------------------------------------------------------------------
# Pattern matching tests
# ---------------------------------------------------------------------------


def test_pattern_wildcard_all():
    assert PolicyGraph._matches_pattern("anything", "*")


def test_pattern_exact_match():
    assert PolicyGraph._matches_pattern("task:123", "task:123")
    assert not PolicyGraph._matches_pattern("task:456", "task:123")


def test_pattern_prefix_wildcard():
    assert PolicyGraph._matches_pattern("task:123:fragment-1", "task:123:*")
    assert PolicyGraph._matches_pattern("task:123:fragment-2", "task:123:*")
    assert not PolicyGraph._matches_pattern("task:456:fragment-1", "task:123:*")


def test_pattern_agent_wildcard():
    assert PolicyGraph._matches_pattern("agent:1", "agent:*")
    assert PolicyGraph._matches_pattern("agent:2", "agent:*")
    assert not PolicyGraph._matches_pattern("user:1", "agent:*")


# ---------------------------------------------------------------------------
# PromotionGate tests
# ---------------------------------------------------------------------------


def test_gate_request_promotion(gate):
    request = gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    assert request.fragment_id == "fragment-123"
    assert request.from_tier == MemoryTier.T1_SESSION
    assert request.to_tier == MemoryTier.T2_SEMANTIC
    assert request.requested_by == "agent-1"
    assert request.status == "pending"


def test_gate_approve_promotion(gate):
    gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    approved = gate.approve("fragment-123", "user-1")
    assert approved is not None
    assert approved.status == "approved"
    assert approved.approved_by == "user-1"
    assert approved.approved_at is not None


def test_gate_reject_promotion(gate):
    gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    rejected = gate.reject("fragment-123", "user-1", "Not ready for promotion")
    assert rejected is not None
    assert rejected.status == "rejected"
    assert rejected.approved_by == "user-1"
    assert rejected.rejection_reason == "Not ready for promotion"


def test_gate_approve_nonexistent(gate):
    approved = gate.approve("nonexistent", "user-1")
    assert approved is None


def test_gate_approve_already_approved(gate):
    gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    gate.approve("fragment-123", "user-1")
    # Try to approve again
    approved = gate.approve("fragment-123", "user-2")
    assert approved is None


def test_gate_get_request(gate):
    gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    request = gate.get_request("fragment-123")
    assert request is not None
    assert request.fragment_id == "fragment-123"


def test_gate_get_nonexistent_request(gate):
    request = gate.get_request("nonexistent")
    assert request is None


def test_gate_list_pending(gate):
    gate.request_promotion(
        fragment_id="fragment-1",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    gate.request_promotion(
        fragment_id="fragment-2",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-2",
    )
    gate.approve("fragment-1", "user-1")

    pending = gate.list_pending()
    assert len(pending) == 1
    assert pending[0].fragment_id == "fragment-2"


def test_gate_clear(gate):
    gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    gate.clear()
    request = gate.get_request("fragment-123")
    assert request is None


# ---------------------------------------------------------------------------
# Global singleton tests
# ---------------------------------------------------------------------------


def test_get_policy_graph_singleton():
    reset_policy_graph()
    graph1 = get_policy_graph()
    graph2 = get_policy_graph()
    assert graph1 is graph2


def test_reset_policy_graph():
    reset_policy_graph()
    graph1 = get_policy_graph()
    reset_policy_graph()
    graph2 = get_policy_graph()
    assert graph1 is not graph2


def test_get_promotion_gate_singleton():
    reset_promotion_gate()
    gate1 = get_promotion_gate()
    gate2 = get_promotion_gate()
    assert gate1 is gate2


def test_reset_promotion_gate():
    reset_promotion_gate()
    gate1 = get_promotion_gate()
    reset_promotion_gate()
    gate2 = get_promotion_gate()
    assert gate1 is not gate2


# ---------------------------------------------------------------------------
# Integration test: multi-agent access control
# ---------------------------------------------------------------------------


def test_multi_agent_access_control(graph):
    """Simulate multi-agent task with access control."""
    # Setup: orchestrator has full access, sub-agents have limited access
    orchestrator = Subject.agent("orchestrator")
    agent1 = Subject.agent("agent-1")
    agent2 = Subject.agent("agent-2")

    task_pattern = Resource.pattern("task:123:*")
    frag1 = Resource.fragment("task:123:fragment-1")
    frag2 = Resource.fragment("task:123:fragment-2")

    # Grant orchestrator full access to task
    graph.grant(
        orchestrator,
        task_pattern,
        {Permission.READ, Permission.WRITE, Permission.PROMOTE},
    )

    # Grant agent1 read/write to fragment-1
    graph.grant(agent1, frag1, {Permission.READ, Permission.WRITE})

    # Grant agent2 read/write to fragment-2
    graph.grant(agent2, frag2, {Permission.READ, Permission.WRITE})

    # Verify orchestrator has access to everything
    assert graph.check_access(orchestrator, frag1, Permission.READ)
    assert graph.check_access(orchestrator, frag1, Permission.WRITE)
    assert graph.check_access(orchestrator, frag1, Permission.PROMOTE)
    assert graph.check_access(orchestrator, frag2, Permission.READ)

    # Verify agent1 has access to fragment-1 only
    assert graph.check_access(agent1, frag1, Permission.READ)
    assert graph.check_access(agent1, frag1, Permission.WRITE)
    assert not graph.check_access(agent1, frag1, Permission.PROMOTE)
    assert not graph.check_access(agent1, frag2, Permission.READ)

    # Verify agent2 has access to fragment-2 only
    assert graph.check_access(agent2, frag2, Permission.READ)
    assert graph.check_access(agent2, frag2, Permission.WRITE)
    assert not graph.check_access(agent2, frag1, Permission.READ)


# ---------------------------------------------------------------------------
# Integration test: promotion workflow
# ---------------------------------------------------------------------------


def test_promotion_workflow(gate):
    """Simulate T1→T2 promotion workflow."""
    # Step 1: Agent requests promotion
    request = gate.request_promotion(
        fragment_id="fragment-123",
        from_tier=MemoryTier.T1_SESSION,
        to_tier=MemoryTier.T2_SEMANTIC,
        requested_by="agent-1",
    )
    assert request.status == "pending"

    # Step 2: List pending requests
    pending = gate.list_pending()
    assert len(pending) == 1
    assert pending[0].fragment_id == "fragment-123"

    # Step 3: User approves
    approved = gate.approve("fragment-123", "user-1")
    assert approved is not None
    assert approved.status == "approved"

    # Step 4: No more pending requests
    pending = gate.list_pending()
    assert len(pending) == 0


