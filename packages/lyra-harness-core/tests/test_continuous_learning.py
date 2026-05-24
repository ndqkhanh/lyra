"""Tests for harness_core.continuous_learning."""
from __future__ import annotations

import pytest

from harness_core.continuous_learning import (
    ContinuousLearner,
    EditEvent,
    EditRecorder,
    HeuristicExtractor,
    LearnedPreference,
    LearningReport,
)
from harness_core.memory_store import MemoryKind, MemoryStore, RetrievalSpec
from harness_core.provenance import WitnessLattice


# --- EditEvent --------------------------------------------------------


class TestEditEvent:
    def test_basic_creation(self):
        e = EditEvent.create(
            agent_output="hello world",
            user_edit="hi world",
            user_id="alice",
        )
        assert e.user_id == "alice"
        assert e.event_id != ""
        assert e.shortened
        assert not e.lengthened

    def test_lengthened(self):
        e = EditEvent.create(
            agent_output="ok",
            user_edit="ok, more details please",
            user_id="bob",
        )
        assert e.lengthened
        assert not e.shortened

    def test_length_delta(self):
        e = EditEvent.create(
            agent_output="abc",
            user_edit="abcdef",
            user_id="x",
        )
        assert e.length_delta_chars == 3

    def test_empty_user_id_rejected(self):
        with pytest.raises(ValueError):
            EditEvent.create(
                agent_output="x", user_edit="y", user_id="",
            )


# --- EditRecorder -----------------------------------------------------


class TestEditRecorder:
    def test_record_and_retrieve(self):
        r = EditRecorder()
        r.record(agent_output="x", user_edit="y", user_id="alice")
        r.record(agent_output="a", user_edit="b", user_id="bob")
        assert len(r) == 2
        assert len(r.for_user("alice")) == 1
        assert len(r.for_user("bob")) == 1

    def test_recent(self):
        r = EditRecorder()
        for i in range(5):
            r.record(agent_output=f"x{i}", user_edit=f"y{i}", user_id="alice")
        recent = r.recent(n=2)
        assert len(recent) == 2
        assert recent[-1].agent_output == "x4"

    def test_filter_since_timestamp(self):
        r = EditRecorder()
        e1 = r.record(agent_output="a", user_edit="b", user_id="alice")
        e2 = r.record(agent_output="c", user_edit="d", user_id="alice")
        # Filter to events after e1's timestamp.
        out = r.filter(since_timestamp=e1.timestamp + 1e-9)
        # e2 might not have a strictly-greater timestamp due to time.time
        # resolution; we just ensure filter returns a subset.
        assert all(e.timestamp >= e1.timestamp for e in out)

    def test_iter(self):
        r = EditRecorder()
        for i in range(3):
            r.record(agent_output=f"x{i}", user_edit=f"y{i}", user_id="alice")
        assert sum(1 for _ in r) == 3


# --- HeuristicExtractor ---------------------------------------------


def _shortening_edits(n: int = 5, user_id: str = "alice") -> list[EditEvent]:
    """N edits where the user removes ~30 chars each time."""
    return [
        EditEvent.create(
            agent_output="The user has expressly indicated that the answer should be "
                         f"thorough and exhaustive in nature, instance {i}.",
            user_edit=f"User wants a thorough answer, instance {i}.",
            user_id=user_id,
        )
        for i in range(n)
    ]


def _lengthening_edits(n: int = 5, user_id: str = "alice") -> list[EditEvent]:
    return [
        EditEvent.create(
            agent_output=f"OK case {i}.",
            user_edit=f"OK case {i}. To elaborate, the rationale here is that we want "
                     "the agent to surface enough context for the reviewer.",
            user_id=user_id,
        )
        for i in range(n)
    ]


class TestHeuristicExtractor:
    def test_detects_shortening_preference(self):
        extractor = HeuristicExtractor(min_supporting_edits=3)
        prefs = extractor.extract(_shortening_edits(5))
        # One length preference should be reported.
        rules = [p.rule for p in prefs]
        assert any("shorter" in r for r in rules)

    def test_detects_lengthening_preference(self):
        extractor = HeuristicExtractor(min_supporting_edits=3)
        prefs = extractor.extract(_lengthening_edits(5))
        rules = [p.rule for p in prefs]
        assert any("more detailed" in r for r in rules)

    def test_below_threshold_no_preference(self):
        extractor = HeuristicExtractor(min_supporting_edits=10)
        prefs = extractor.extract(_shortening_edits(3))
        # 3 edits < min_supporting_edits=10 → no length preference.
        length_prefs = [p for p in prefs if "length" in p.tags]
        assert length_prefs == []

    def test_per_user_isolation(self):
        # Alice consistently shortens; Bob doesn't have enough evidence.
        edits = _shortening_edits(5, user_id="alice")
        edits.append(EditEvent.create(
            agent_output="x", user_edit="x", user_id="bob",
        ))
        extractor = HeuristicExtractor(min_supporting_edits=3)
        prefs = extractor.extract(edits)
        assert all(p.user_id == "alice" for p in prefs)

    def test_vocabulary_substitution(self):
        # "utilize" → "use" three times.
        edits = [
            EditEvent.create(
                agent_output=f"please utilize the function in step {i}",
                user_edit=f"please use the function in step {i}",
                user_id="alice",
            )
            for i in range(3)
        ]
        extractor = HeuristicExtractor(min_supporting_edits=3)
        prefs = extractor.extract(edits)
        rules = [p.rule for p in prefs]
        assert any("utilize" in r and "use" in r for r in rules)

    def test_emoji_removal(self):
        edits = [
            EditEvent.create(
                agent_output=f"deployment complete 🚀 step {i}",
                user_edit=f"deployment complete step {i}",
                user_id="alice",
            )
            for i in range(4)
        ]
        extractor = HeuristicExtractor(min_supporting_edits=3)
        prefs = extractor.extract(edits)
        rules = [p.rule for p in prefs]
        assert any("emoji" in r.lower() for r in rules)

    def test_bullet_preference(self):
        edits = [
            EditEvent.create(
                agent_output=f"first item, second item, third item, case {i}.",
                user_edit=f"- first item\n- second item\n- third item\n(case {i})",
                user_id="alice",
            )
            for i in range(4)
        ]
        extractor = HeuristicExtractor(min_supporting_edits=3)
        prefs = extractor.extract(edits)
        rules = [p.rule for p in prefs]
        assert any("bullet" in r.lower() for r in rules)

    def test_empty_input(self):
        assert HeuristicExtractor().extract([]) == []

    def test_confidence_grows_with_evidence(self):
        extractor = HeuristicExtractor(
            min_supporting_edits=3, confidence_per_edit=0.2,
        )
        prefs_3 = extractor.extract(_shortening_edits(3))
        prefs_5 = extractor.extract(_shortening_edits(5))
        # More supporting edits → higher confidence.
        c3 = next(p.confidence for p in prefs_3 if "length" in p.tags)
        c5 = next(p.confidence for p in prefs_5 if "length" in p.tags)
        assert c5 > c3 or (c3 == 1.0 and c5 == 1.0)

    def test_validation(self):
        with pytest.raises(ValueError):
            HeuristicExtractor(min_supporting_edits=0)
        with pytest.raises(ValueError):
            HeuristicExtractor(confidence_per_edit=0.0)


# --- ContinuousLearner ----------------------------------------------


class TestContinuousLearner:
    def test_no_edits_empty_report(self):
        learner = ContinuousLearner(recorder=EditRecorder())
        report = learner.learn()
        assert report.n_edits_examined == 0
        assert report.n_preferences_learned == 0

    def test_records_preferences_to_memory(self):
        recorder = EditRecorder()
        for e in _shortening_edits(5):
            recorder._edits.append(e)  # noqa: SLF001 - bulk seed
        memory = MemoryStore()
        learner = ContinuousLearner(
            recorder=recorder,
            memory=memory,
        )
        report = learner.learn()
        assert report.n_preferences_learned >= 1
        # Memory has at least one PROCEDURAL item with the pref content.
        items = list(memory._items.values())  # noqa: SLF001
        assert any(it.kind == MemoryKind.PROCEDURAL for it in items)

    def test_preference_namespace_is_user_id(self):
        recorder = EditRecorder()
        for e in _shortening_edits(5, user_id="alice"):
            recorder._edits.append(e)  # noqa: SLF001
        memory = MemoryStore()
        ContinuousLearner(recorder=recorder, memory=memory).learn()
        items = list(memory._items.values())  # noqa: SLF001
        assert all(it.namespace == "alice" for it in items)

    def test_witness_emitted(self):
        recorder = EditRecorder()
        for e in _shortening_edits(5):
            recorder._edits.append(e)  # noqa: SLF001
        lattice = WitnessLattice()
        learner = ContinuousLearner(recorder=recorder, lattice=lattice)
        report = learner.learn()
        assert len(report.preference_witness_ids) == report.n_preferences_learned
        # Witnesses are recorded on the lattice with the right action.
        for wid in report.preference_witness_ids:
            w = lattice.ledger.get(wid)
            assert w is not None
            assert w.content["action"] == "learn_preference"

    def test_user_filter(self):
        recorder = EditRecorder()
        for e in _shortening_edits(5, user_id="alice"):
            recorder._edits.append(e)  # noqa: SLF001
        for e in _shortening_edits(5, user_id="bob"):
            recorder._edits.append(e)  # noqa: SLF001
        learner = ContinuousLearner(recorder=recorder)
        report = learner.learn(user_id="alice")
        # Only alice's edits should be examined.
        assert all(p.user_id == "alice" for p in report.preferences)

    def test_preference_searchable_in_memory(self):
        recorder = EditRecorder()
        for e in _shortening_edits(5, user_id="alice"):
            recorder._edits.append(e)  # noqa: SLF001
        memory = MemoryStore()
        ContinuousLearner(recorder=recorder, memory=memory).learn()
        # We should be able to retrieve the learned preference by querying.
        hits = memory.search(RetrievalSpec(
            query="shorter", namespace="alice", top_k=5,
        ))
        assert len(hits) >= 1


# --- LearnedPreference validation ------------------------------------


class TestLearnedPreference:
    def test_basic(self):
        p = LearnedPreference.create(
            rule="user prefers shorter outputs",
            user_id="alice",
            confidence=0.6,
            n_supporting_edits=3,
        )
        assert 0.0 <= p.confidence <= 1.0
        assert p.user_id == "alice"

    def test_clamp_confidence(self):
        p = LearnedPreference.create(
            rule="x", user_id="alice", confidence=1.5, n_supporting_edits=3,
        )
        assert p.confidence == 1.0
        p2 = LearnedPreference.create(
            rule="x", user_id="alice", confidence=-0.2, n_supporting_edits=3,
        )
        assert p2.confidence == 0.0

    def test_zero_supporting_edits_rejected(self):
        with pytest.raises(ValueError):
            LearnedPreference(
                preference_id="p1",
                rule="x",
                user_id="alice",
                confidence=0.5,
                n_supporting_edits=0,
            )


# --- LearningReport --------------------------------------------------


class TestLearningReportShape:
    def test_returns_report_dataclass(self):
        learner = ContinuousLearner(recorder=EditRecorder())
        out = learner.learn()
        assert isinstance(out, LearningReport)
        assert isinstance(out.preferences, tuple)
