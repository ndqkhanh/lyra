"""Tests for memory/writer.py (Phase M2 — Writer + ConflictResolver)."""
from __future__ import annotations

import pytest

from lyra_core.memory.schema import Fragment, FragmentType, MemoryTier, Provenance
from lyra_core.memory.writer import (
    ConflictResolver,
    FragmentStore,
    WriteAction,
    Writer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prov(agent: str = "agent-A", session: str = "s1") -> Provenance:
    return Provenance(agent_id=agent, session_id=session)


def _fact(content: str, entities: list[str] | None = None, confidence: float = 0.7,
          agent: str = "agent-A") -> Fragment:
    return Fragment.make(
        tier=MemoryTier.T2_SEMANTIC,
        type=FragmentType.FACT,
        content=content,
        provenance=_prov(agent=agent),
        entities=entities or [],
        confidence=confidence,
    )


def _decision(content: str, rationale: str = "because reasons",
              entities: list[str] | None = None, confidence: float = 0.7,
              agent: str = "agent-A") -> Fragment:
    return Fragment.make(
        tier=MemoryTier.T2_PROCEDURAL,
        type=FragmentType.DECISION,
        content=content,
        provenance=_prov(agent=agent),
        structured={"rationale": rationale},
        entities=entities or [],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# FragmentStore
# ---------------------------------------------------------------------------


def test_store_put_and_get():
    store = FragmentStore()
    f = _fact("db = postgres")
    store.put(f)
    assert store.get(f.id) is f
    assert len(store) == 1


def test_store_active_excludes_invalidated():
    store = FragmentStore()
    f1 = _fact("old fact")
    f2 = _fact("new fact")
    store.put(f1)
    store.put(f2)
    f1.invalidate()
    assert len(store.active()) == 1
    assert store.active()[0].id == f2.id


def test_store_all_includes_invalidated():
    store = FragmentStore()
    f = _fact("gone")
    store.put(f)
    f.invalidate()
    assert len(store.all_fragments()) == 1


# ---------------------------------------------------------------------------
# Writer — ADD
# ---------------------------------------------------------------------------


def test_writer_add_new_fragment():
    w = Writer()
    f = _fact("auth uses JWT")
    result = w.write(f)
    assert result.action is WriteAction.ADD
    assert result.fragment.id == f.id
    assert len(w.store.active()) == 1


def test_writer_add_different_types_both_stored():
    w = Writer()
    w.write(_fact("auth uses JWT", entities=["JWT"]))
    w.write(_decision("chose Clickhouse", entities=["Clickhouse"]))
    assert len(w.store.active()) == 2


# ---------------------------------------------------------------------------
# Writer — DEDUPE
# ---------------------------------------------------------------------------


def test_writer_dedupe_near_identical_content():
    w = Writer()
    f1 = _fact("authentication module is located in src/auth.py uses JWT")
    f2 = _fact("authentication module is located in src/auth.py uses JWT")
    w.write(f1)
    result = w.write(f2)
    # Very similar — should dedupe into existing
    assert result.action is WriteAction.DEDUPE
    assert result.merged_into == f1.id
    assert len(w.store.active()) == 1


def test_writer_dedupe_increments_access_count():
    w = Writer()
    f1 = _fact("auth module in src/auth.py uses JWT validation token")
    f2 = _fact("auth module in src/auth.py uses JWT validation token")
    w.write(f1)
    w.write(f2)
    surviving = w.store.active()[0]
    assert surviving.access_count >= 1


# ---------------------------------------------------------------------------
# Writer — UPDATE
# ---------------------------------------------------------------------------


def test_writer_update_higher_confidence():
    w = Writer()
    low = _fact("auth module uses jwt tokens", confidence=0.6)
    high = _fact("the auth module uses jwt bearer tokens", confidence=0.85)
    w.write(low)
    result = w.write(high)
    assert result.action is WriteAction.UPDATE
    assert result.fragment.confidence == pytest.approx(0.85)
    assert len(w.store.active()) == 1


# ---------------------------------------------------------------------------
# Writer — SUPERSEDE
# ---------------------------------------------------------------------------


def test_writer_supersede_contradiction():
    w = Writer()
    old = _fact("db = postgres", entities=["postgres", "db"])
    new = _fact("db = clickhouse", entities=["clickhouse", "db"], confidence=0.9)
    w.write(old)
    result = w.write(new)
    assert result.action is WriteAction.SUPERSEDE
    assert result.conflict is not None
    assert result.conflict.reason == "contradiction"
    assert result.conflict.old_fragment_id == old.id
    # Old fragment should be invalidated
    assert not w.store.get(old.id).is_valid
    assert new.id in [f.id for f in w.store.all_fragments()]


def test_writer_supersede_links_new_to_old():
    w = Writer()
    old = _fact("framework = django", entities=["django", "framework"])
    new = _fact("framework = fastapi", entities=["fastapi", "framework"], confidence=0.9)
    w.write(old)
    result = w.write(new)
    assert old.id in result.fragment.supersedes


def test_writer_supersede_conflict_logged():
    w = Writer()
    old = _fact("cache = redis", entities=["redis", "cache"])
    new = _fact("cache = memcached", entities=["memcached", "cache"], confidence=0.9)
    w.write(old)
    w.write(new)
    assert len(w.conflicts) == 1
    assert w.conflicts[0].reason == "contradiction"


# ---------------------------------------------------------------------------
# Writer — NOOP (same agent, lower confidence)
# ---------------------------------------------------------------------------


def test_writer_noop_lower_confidence_same_agent():
    w = Writer()
    high = _fact("db = postgres", entities=["postgres", "db"], confidence=0.9)
    low = _fact("db = mysql", entities=["mysql", "db"], confidence=0.5)
    w.write(high)
    result = w.write(low)
    assert result.action is WriteAction.NOOP
    # Original high-confidence fragment unchanged
    assert w.store.active()[0].id == high.id


# ---------------------------------------------------------------------------
# ConflictResolver — agent disagreement
# ---------------------------------------------------------------------------


def test_conflict_resolver_agent_disagreement_branches():
    resolver = ConflictResolver()
    existing = _fact("db = postgres", entities=["postgres", "db"], agent="agent-A")
    incoming = _fact("db = clickhouse", entities=["clickhouse", "db"], agent="agent-B")
    action, conflict = resolver.resolve(existing, incoming)
    assert action is WriteAction.SUPERSEDE
    assert conflict is not None
    assert conflict.reason == "agent_disagreement"
    assert conflict.resolution == "branch"


def test_writer_agent_disagreement_both_kept_valid():
    w = Writer()
    old = _fact("db = postgres", entities=["postgres", "db"], agent="agent-A")
    new = _fact("db = clickhouse", entities=["clickhouse", "db"], agent="agent-B")
    w.write(old)
    result = w.write(new)
    assert result.action is WriteAction.SUPERSEDE
    assert result.conflict.resolution == "branch"
    # Both should remain valid (branch = human resolves)
    assert w.store.get(old.id).is_valid
    assert w.store.get(new.id).is_valid


# ---------------------------------------------------------------------------
# Multi-write pipeline
# ---------------------------------------------------------------------------


def test_writer_multiple_rounds_correct_active_count():
    w = Writer()
    w.write(_fact("auth in src/auth.py", entities=["auth"]))
    w.write(_fact("db = postgres", entities=["postgres", "db"]))
    w.write(_fact("db = clickhouse", entities=["clickhouse", "db"], confidence=0.9))
    # Last write supersedes postgres → 2 active: auth + clickhouse
    active = w.store.active()
    assert len(active) == 2
    contents = {f.content for f in active}
    assert any("clickhouse" in c for c in contents)
    assert any("auth" in c for c in contents)
