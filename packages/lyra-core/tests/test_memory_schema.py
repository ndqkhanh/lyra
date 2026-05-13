"""Tests for memory/schema.py (Phase M1 — Fragment schema unification)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from lyra_core.memory.schema import (
    AccessEdge,
    ConflictEvent,
    Fragment,
    FragmentType,
    MemoryTier,
    Provenance,
    SubAgentDigest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prov(**kw) -> Provenance:
    return Provenance(
        agent_id=kw.get("agent_id", "test-agent"),
        session_id=kw.get("session_id", "s1"),
        user_id=kw.get("user_id", "local"),
    )


def _fragment(**kw) -> Fragment:
    return Fragment.make(
        tier=kw.get("tier", MemoryTier.T2_SEMANTIC),
        type=kw.get("type", FragmentType.FACT),
        content=kw.get("content", "auth uses JWT"),
        provenance=kw.get("provenance", _prov()),
        structured=kw.get("structured", {}),
        confidence=kw.get("confidence", None),
        visibility=kw.get("visibility", "private"),
    )


# ---------------------------------------------------------------------------
# MemoryTier / FragmentType
# ---------------------------------------------------------------------------


def test_memory_tier_values():
    assert MemoryTier.T0_WORKING.value == "t0_working"
    assert MemoryTier.T3_TEAM.value == "t3_team"


def test_fragment_type_values():
    assert FragmentType.FACT.value == "fact"
    assert FragmentType.DECISION.value == "decision"
    assert FragmentType.SKILL.value == "skill"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_provenance_roundtrip():
    p = Provenance(
        agent_id="claude:orchestrator",
        session_id="sess-1",
        user_id="khanh",
        model="claude-sonnet-4-6",
        task_id="task-42",
        tool_calls=["read_file:src/auth.py"],
        resources=["src/auth.py"],
    )
    p2 = Provenance.from_dict(p.to_dict())
    assert p2.agent_id == p.agent_id
    assert p2.model == p.model
    assert p2.task_id == p.task_id
    assert p2.tool_calls == p.tool_calls


def test_provenance_defaults():
    p = Provenance(agent_id="a", session_id="s")
    assert p.user_id == "local"
    assert p.model is None
    assert p.tool_calls == []


# ---------------------------------------------------------------------------
# Fragment construction
# ---------------------------------------------------------------------------


def test_fragment_make_generates_id():
    f = _fragment()
    assert f.id
    assert len(f.id) == 36  # uuid4


def test_fragment_fact_defaults():
    f = _fragment(type=FragmentType.FACT)
    assert f.confidence == 0.7
    assert f.is_valid
    assert f.access_count == 0


def test_fragment_observation_lower_confidence():
    f = _fragment(type=FragmentType.OBSERVATION)
    assert f.confidence == 0.5


def test_fragment_empty_content_raises():
    with pytest.raises(ValueError, match="content"):
        Fragment(
            id=str(uuid.uuid4()),
            tier=MemoryTier.T1_SESSION,
            type=FragmentType.FACT,
            content="",
            provenance=_prov(),
        )


def test_fragment_bad_confidence_raises():
    with pytest.raises(ValueError, match="confidence"):
        Fragment(
            id=str(uuid.uuid4()),
            tier=MemoryTier.T1_SESSION,
            type=FragmentType.FACT,
            content="ok",
            provenance=_prov(),
            confidence=1.5,
        )


def test_fragment_decision_requires_rationale():
    with pytest.raises(ValueError, match="rationale"):
        Fragment(
            id=str(uuid.uuid4()),
            tier=MemoryTier.T2_PROCEDURAL,
            type=FragmentType.DECISION,
            content="chose Clickhouse",
            provenance=_prov(),
            structured={},  # missing "rationale"
        )


def test_fragment_decision_with_rationale_ok():
    f = Fragment(
        id=str(uuid.uuid4()),
        tier=MemoryTier.T2_PROCEDURAL,
        type=FragmentType.DECISION,
        content="chose Clickhouse over Postgres",
        provenance=_prov(),
        structured={"rationale": "OLAP queries; Postgres was too slow at 10M rows"},
    )
    assert f.type is FragmentType.DECISION
    assert f.structured["rationale"]


# ---------------------------------------------------------------------------
# Fragment operations
# ---------------------------------------------------------------------------


def test_fragment_invalidate():
    f = _fragment()
    assert f.is_valid
    f.invalidate()
    assert not f.is_valid
    assert f.invalid_at is not None


def test_fragment_touch():
    f = _fragment()
    assert f.access_count == 0
    f.touch()
    f.touch()
    assert f.access_count == 2
    assert f.last_accessed_at is not None


def test_fragment_pinned_default_false():
    f = _fragment()
    assert not f.pinned


def test_fragment_make_with_pinned():
    f = Fragment.make(
        tier=MemoryTier.T2_PROCEDURAL,
        type=FragmentType.DECISION,
        content="keep SQLAlchemy 2.0 async",
        provenance=_prov(),
        structured={"rationale": "entire stack uses async"},
        pinned=True,
    )
    assert f.pinned


# ---------------------------------------------------------------------------
# Serialization roundtrip
# ---------------------------------------------------------------------------


def test_fragment_roundtrip():
    f = Fragment.make(
        tier=MemoryTier.T2_PROCEDURAL,
        type=FragmentType.DECISION,
        content="chose httpx over requests",
        provenance=_prov(agent_id="agent-1", session_id="s99"),
        structured={"rationale": "async support; requests has no async"},
        entities=["httpx", "requests"],
        confidence=0.9,
        visibility="project",
    )
    f.touch()
    d = f.to_dict()
    f2 = Fragment.from_dict(d)

    assert f2.id == f.id
    assert f2.tier is MemoryTier.T2_PROCEDURAL
    assert f2.type is FragmentType.DECISION
    assert f2.structured["rationale"] == f.structured["rationale"]
    assert f2.entities == ["httpx", "requests"]
    assert f2.access_count == 1
    assert f2.provenance.agent_id == "agent-1"
    assert f2.visibility == "project"


def test_fragment_roundtrip_with_invalid_at():
    f = _fragment()
    f.invalidate()
    d = f.to_dict()
    f2 = Fragment.from_dict(d)
    assert not f2.is_valid


# ---------------------------------------------------------------------------
# Supersession chain
# ---------------------------------------------------------------------------


def test_fragment_supersedes_chain():
    old = _fragment(content="db = postgres")
    new = Fragment.make(
        tier=MemoryTier.T2_SEMANTIC,
        type=FragmentType.FACT,
        content="db = clickhouse",
        provenance=_prov(),
        structured={},
    )
    new.supersedes.append(old.id)
    old.invalidate()

    assert not old.is_valid
    assert old.id in new.supersedes


# ---------------------------------------------------------------------------
# ConflictEvent
# ---------------------------------------------------------------------------


def test_conflict_event_make():
    ev = ConflictEvent.make("old-id", "new-id", reason="contradiction")
    assert ev.old_fragment_id == "old-id"
    assert ev.new_fragment_id == "new-id"
    assert ev.reason == "contradiction"
    assert ev.resolution == "supersede"
    assert ev.id


def test_conflict_event_roundtrip():
    ev = ConflictEvent.make("a", "b", reason="agent_disagreement", resolution="branch")
    d = ev.to_dict()
    assert d["reason"] == "agent_disagreement"
    assert d["resolution"] == "branch"
    assert "created_at" in d


# ---------------------------------------------------------------------------
# AccessEdge
# ---------------------------------------------------------------------------


def test_access_edge_active_default():
    e = AccessEdge(user_id="u1", agent_id="a1", resource_glob="tier:t3_team")
    assert e.is_active()
    assert e.allows("read")


def test_access_edge_write_permission():
    e = AccessEdge(
        user_id="u1", agent_id="a1", resource_glob="repo:org/repo/**",
        perms={"read", "write"},
    )
    assert e.allows("write")


def test_access_edge_expired():
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    e = AccessEdge(
        user_id="u1", agent_id="a1", resource_glob="*",
        valid_to=past,
    )
    assert not e.is_active()
    assert not e.allows("read")


def test_access_edge_no_write_by_default():
    e = AccessEdge(user_id="u1", agent_id="a1", resource_glob="*")
    assert not e.allows("write")


# ---------------------------------------------------------------------------
# SubAgentDigest
# ---------------------------------------------------------------------------


def test_digest_to_dict():
    d = SubAgentDigest(
        agent_id="subagent:test-runner",
        task_id="task-1",
        step=3,
        last_action="ran pytest; 2 failures",
        findings=["auth test fails on line 42", "missing mock"],
        open_questions=["should we mock db?"],
        next_intent="fix mock setup",
        confidence=0.8,
    )
    out = d.to_dict()
    assert out["agent_id"] == "subagent:test-runner"
    assert out["step"] == 3
    assert len(out["findings"]) == 2


def test_digest_render_compact():
    d = SubAgentDigest(
        agent_id="agent-A",
        task_id="t1",
        step=1,
        last_action="searched for auth module",
        findings=["found in src/auth.py", "uses JWT"],
        next_intent="read auth.py",
    )
    text = d.render_compact()
    assert "[agent-A step=1]" in text
    assert "found in src/auth.py" in text
    assert len(text) <= 300


def test_digest_render_compact_truncates():
    d = SubAgentDigest(
        agent_id="a",
        task_id="t",
        step=0,
        last_action="x" * 400,
    )
    assert len(d.render_compact()) <= 300
