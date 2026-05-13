"""Tests for pinned_decisions.py and temporal_fact_store.py (Phase 3)."""
from __future__ import annotations

from lyra_core.memory.pinned_decisions import (
    DecisionExtractor,
    PinnedDecision,
    PinnedDecisionStore,
)
from lyra_core.memory.temporal_fact_store import (
    TemporalFact,
    TemporalFactStore,
)


# ---------------------------------------------------------------------------
# DecisionExtractor — basic extraction
# ---------------------------------------------------------------------------


def test_extract_decision_decided():
    extractor = DecisionExtractor()
    decisions = extractor.extract("We decided to use SQLite.", turn=1)
    assert len(decisions) == 1
    assert "SQLite" in decisions[0].text
    assert decisions[0].source_turn == 1


def test_extract_convention_pattern():
    extractor = DecisionExtractor()
    decisions = extractor.extract("The convention is to use snake_case.", turn=2)
    assert len(decisions) >= 1


def test_extract_never_rule():
    extractor = DecisionExtractor()
    decisions = extractor.extract("Never mock the database in tests.", turn=0)
    assert len(decisions) >= 1


def test_extract_always_rule():
    extractor = DecisionExtractor()
    decisions = extractor.extract("Always validate at system boundaries.", turn=0)
    assert len(decisions) >= 1


def test_extract_no_decision():
    extractor = DecisionExtractor()
    decisions = extractor.extract("The sky is blue.", turn=0)
    assert decisions == []


def test_extract_short_sentence_ignored():
    extractor = DecisionExtractor()
    decisions = extractor.extract("Go.", turn=0)
    assert decisions == []


def test_extract_multi_sentence():
    extractor = DecisionExtractor()
    text = "The sky is blue. We decided to use async IO. It will be faster."
    decisions = extractor.extract(text, turn=0)
    assert len(decisions) >= 1
    assert any("async IO" in d.text for d in decisions)


def test_extract_confidence_increases_with_markers():
    extractor = DecisionExtractor()
    # Multiple markers in one sentence → higher confidence
    single = extractor.extract("We decided on X.", turn=0)
    multi = extractor.extract(
        "We decided we should always use X and never use Y.", turn=0
    )
    assert multi[0].confidence >= single[0].confidence


def test_extract_tags_passed_through():
    extractor = DecisionExtractor()
    decisions = extractor.extract("We decided to use SQLite.", turn=0, tags=["db"])
    assert "db" in decisions[0].tags


def test_extract_returns_pinned_decision_instances():
    extractor = DecisionExtractor()
    decisions = extractor.extract("We decided to refactor auth.", turn=5)
    assert all(isinstance(d, PinnedDecision) for d in decisions)


# ---------------------------------------------------------------------------
# DecisionExtractor — extract_from_messages
# ---------------------------------------------------------------------------


def test_extract_from_messages_skips_user():
    extractor = DecisionExtractor()
    msgs = [
        {"role": "user", "content": "We decided to do something."},
        {"role": "assistant", "content": "We decided to use async."},
    ]
    decisions = extractor.extract_from_messages(msgs)
    assert all(d.source_turn == 1 for d in decisions)


def test_extract_from_messages_list_content():
    extractor = DecisionExtractor()
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "We decided to use OAuth2."}
            ],
        }
    ]
    decisions = extractor.extract_from_messages(msgs)
    assert len(decisions) >= 1


def test_extract_from_messages_min_confidence():
    extractor = DecisionExtractor()
    msgs = [
        {"role": "assistant", "content": "We decided it. Never do X. Always use Y."},
    ]
    all_d = extractor.extract_from_messages(msgs, min_confidence=0.0)
    high_d = extractor.extract_from_messages(msgs, min_confidence=0.9)
    assert len(all_d) >= len(high_d)


# ---------------------------------------------------------------------------
# PinnedDecisionStore
# ---------------------------------------------------------------------------


def _make_decision(
    *,
    id: str = "test-id",
    text: str = "We decided to use PostgreSQL.",
    source_turn: int = 1,
    confidence: float = 0.5,
    tags: list[str] | None = None,
) -> PinnedDecision:
    return PinnedDecision(
        id=id,
        text=text,
        source_turn=source_turn,
        confidence=confidence,
        tags=tags or [],
    )


def test_store_add_and_recall():
    store = PinnedDecisionStore()
    d = _make_decision(id="a1")
    store.add(d)
    results = store.recall()
    assert len(results) == 1
    assert results[0].id == "a1"


def test_store_recall_top_k():
    store = PinnedDecisionStore()
    for i in range(5):
        store.add(_make_decision(id=f"d{i}", text=f"Decision {i}."))
    results = store.recall(top_k=3)
    assert len(results) == 3


def test_store_recall_min_confidence():
    store = PinnedDecisionStore()
    store.add(_make_decision(id="low", confidence=0.2))
    store.add(_make_decision(id="high", confidence=0.8))
    results = store.recall(min_confidence=0.5)
    assert all(d.confidence >= 0.5 for d in results)
    assert len(results) == 1


def test_store_recall_by_tags():
    store = PinnedDecisionStore()
    store.add(_make_decision(id="db", tags=["database"]))
    store.add(_make_decision(id="api", tags=["api"]))
    results = store.recall(tags=["database"])
    assert len(results) == 1
    assert results[0].id == "db"


def test_store_remove():
    store = PinnedDecisionStore()
    store.add(_make_decision(id="x1"))
    assert store.remove("x1")
    assert store.recall() == []


def test_store_remove_nonexistent():
    store = PinnedDecisionStore()
    assert not store.remove("no-such-id")


def test_store_as_context_block_empty():
    store = PinnedDecisionStore()
    assert store.as_context_block() == ""


def test_store_as_context_block_content():
    store = PinnedDecisionStore()
    store.add(_make_decision(id="d1", text="Always use async."))
    block = store.as_context_block()
    assert "Pinned Decisions" in block
    assert "Always use async." in block


def test_store_persist_and_reload(tmp_path):
    path = tmp_path / "decisions.json"
    store = PinnedDecisionStore(store_path=path)
    store.add(_make_decision(id="p1", text="Use snake_case."))
    store2 = PinnedDecisionStore(store_path=path)
    assert len(store2.all()) == 1
    assert store2.all()[0].text == "Use snake_case."


def test_store_load_corrupt(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json")
    store = PinnedDecisionStore(store_path=path)
    assert store.all() == []


# ---------------------------------------------------------------------------
# TemporalFactStore — add & recall
# ---------------------------------------------------------------------------


def test_add_and_recall_valid():
    store = TemporalFactStore()
    fid = store.add("auth is at src/auth/", category="file_location")
    result = store.recall()
    assert result.total_stored == 1
    assert result.total_valid == 1
    assert result.total_invalid == 0
    assert result.facts[0].id == fid


def test_invalidate_removes_from_recall():
    store = TemporalFactStore()
    fid = store.add("old path", category="file_location")
    store.invalidate(fid)
    result = store.recall()
    assert result.total_valid == 0
    assert result.total_invalid == 1
    assert len(result.facts) == 0


def test_invalidate_with_superseded_by():
    store = TemporalFactStore()
    old_id = store.add("auth at src/auth/")
    new_id = store.add("auth at src/core/auth/")
    store.invalidate(old_id, superseded_by=new_id)
    old_fact = store.get(old_id)
    assert old_fact is not None
    assert not old_fact.is_valid
    assert old_fact.superseded_by == new_id


def test_invalidate_nonexistent_returns_false():
    store = TemporalFactStore()
    assert not store.invalidate("no-such-id")


def test_recall_include_invalid():
    store = TemporalFactStore()
    fid = store.add("old fact")
    store.invalidate(fid)
    result = store.recall(include_invalid=True)
    assert len(result.facts) == 1


def test_recall_by_category():
    store = TemporalFactStore()
    store.add("func in auth.py", category="function_name")
    store.add("db is postgres", category="convention")
    result = store.recall(category="function_name")
    assert len(result.facts) == 1
    assert result.facts[0].category == "function_name"


def test_fact_is_valid_property():
    fact = TemporalFact(
        id="x", fact="test", category="gen", valid_from="2026-01-01T00:00:00+00:00"
    )
    assert fact.is_valid
    invalid = TemporalFact(
        id="x", fact="test", category="gen",
        valid_from="2026-01-01T00:00:00+00:00",
        invalid_at="2026-05-01T00:00:00+00:00",
    )
    assert not invalid.is_valid


def test_as_context_block_empty():
    store = TemporalFactStore()
    assert store.as_context_block() == ""


def test_as_context_block_content():
    store = TemporalFactStore()
    store.add("auth is at src/core/auth/", category="file_location")
    block = store.as_context_block()
    assert "Codebase Facts" in block
    assert "src/core/auth/" in block


def test_invalidation_log():
    store = TemporalFactStore()
    fid1 = store.add("fact 1")
    fid2 = store.add("fact 2")
    store.invalidate(fid1)
    store.invalidate(fid2)
    log = store.invalidation_log()
    assert len(log) == 2
    assert all(not f.is_valid for f in log)


def test_persist_and_reload(tmp_path):
    path = tmp_path / "facts.json"
    store = TemporalFactStore(store_path=path)
    fid = store.add("test fact", category="convention")
    store.invalidate(fid)
    store2 = TemporalFactStore(store_path=path)
    result = store2.recall(include_invalid=True)
    assert result.total_stored == 1
    assert result.total_invalid == 1


def test_persist_load_corrupt(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[{bad json")
    store = TemporalFactStore(store_path=path)
    assert store.recall().total_stored == 0
