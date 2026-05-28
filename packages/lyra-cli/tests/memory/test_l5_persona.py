"""Tests for L5 Persona memory layer — identity traits, style learner, preference accumulator, persona store."""

import time

import pytest
from lyra_cli.memory.l5_persona.identity_traits import (
    IdentityModel,
    IdentityTrait,
    TraitCategory,
)
from lyra_cli.memory.l5_persona.persona_store import PersonaSnapshot, PersonaStore
from lyra_cli.memory.l5_persona.preference_accumulator import (
    AccumulatedPreference,
    PreferenceAccumulator,
    PreferenceSource,
)
from lyra_cli.memory.l5_persona.style_learner import (
    StyleDimension,
    StyleLearner,
    StylePreference,
)


class TestIdentityTrait:
    def test_trait_creation(self):
        t = IdentityTrait(
            trait_id="t1",
            category=TraitCategory.COMMUNICATION,
            name="verbosity",
            value=0.7,
            confidence=0.5,
            evidence_count=3,
            last_updated=time.time(),
        )
        assert t.name == "verbosity"
        assert t.value == 0.7
        assert t.category == TraitCategory.COMMUNICATION

    def test_trait_not_stable_with_low_confidence(self):
        t = IdentityTrait(
            trait_id="t1",
            category=TraitCategory.COMMUNICATION,
            name="verbosity",
            value=0.7,
            confidence=0.5,
            evidence_count=3,
            last_updated=time.time(),
        )
        assert not t.is_stable

    def test_trait_stable_with_high_confidence(self):
        t = IdentityTrait(
            trait_id="t1",
            category=TraitCategory.COMMUNICATION,
            name="verbosity",
            value=0.7,
            confidence=0.9,
            evidence_count=10,
            last_updated=time.time(),
        )
        assert t.is_stable

    def test_trait_frozen(self):
        t = IdentityTrait(
            trait_id="t1",
            category=TraitCategory.COMMUNICATION,
            name="test",
            value=0.5,
            confidence=0.5,
            evidence_count=1,
            last_updated=time.time(),
        )
        with pytest.raises(Exception):
            t.value = 0.9  # type: ignore[misc]


class TestTraitCategory:
    def test_all_categories(self):
        assert TraitCategory.COMMUNICATION.value == "communication"
        assert TraitCategory.PROBLEM_SOLVING.value == "problem_solving"
        assert TraitCategory.RISK_TOLERANCE.value == "risk_tolerance"
        assert TraitCategory.AUTONOMY.value == "autonomy"
        assert TraitCategory.COLLABORATION.value == "collaboration"


class TestIdentityModel:
    def test_init(self):
        model = IdentityModel()
        assert model.stats()["total_traits"] == 0

    def test_observe_new_trait(self):
        model = IdentityModel()
        t = model.observe(TraitCategory.COMMUNICATION, "verbosity", 0.8)
        assert t.name == "verbosity"
        assert t.value == 0.8
        assert t.confidence == 0.3
        assert t.evidence_count == 1

    def test_observe_clamps_value(self):
        model = IdentityModel()
        t = model.observe(TraitCategory.COMMUNICATION, "high_val", 1.5)
        assert t.value == 1.0
        t2 = model.observe(TraitCategory.COMMUNICATION, "low_val", -0.5)
        assert t2.value == 0.0

    def test_observe_reinforces_existing(self):
        model = IdentityModel()
        model.observe(TraitCategory.COMMUNICATION, "verbosity", 0.8)
        t = model.observe(TraitCategory.COMMUNICATION, "verbosity", 0.6)
        assert t.evidence_count == 2
        assert t.confidence > 0.3

    def test_get_profile(self):
        model = IdentityModel()
        model.observe(TraitCategory.COMMUNICATION, "verbosity", 0.8)
        model.observe(TraitCategory.PROBLEM_SOLVING, "debugging", 0.9)
        profile = model.get_profile()
        assert TraitCategory.COMMUNICATION in profile
        assert TraitCategory.PROBLEM_SOLVING in profile

    def test_get_stable_traits(self):
        model = IdentityModel()
        for _ in range(30):
            model.observe(TraitCategory.COMMUNICATION, "verbosity", 0.8)
        stable = model.get_stable_traits()
        assert len(stable) >= 1
        assert all(t.is_stable for t in stable)

    def test_stats(self):
        model = IdentityModel()
        model.observe(TraitCategory.COMMUNICATION, "a", 0.5)
        model.observe(TraitCategory.COMMUNICATION, "b", 0.5)
        s = model.stats()
        assert s["total_traits"] == 2


class TestStyleDimension:
    def test_all_dimensions(self):
        assert StyleDimension.VERBOSITY.value == "verbosity"
        assert StyleDimension.FORMALITY.value == "formality"
        assert StyleDimension.TECHNICAL_DEPTH.value == "technical_depth"
        assert StyleDimension.CONCISENESS.value == "conciseness"
        assert StyleDimension.CODE_PREFERENCE.value == "code_preference"
        assert StyleDimension.EXPLANATION_STYLE.value == "explanation_style"


class TestStylePreference:
    def test_creation(self):
        sp = StylePreference(
            pref_id="p1",
            dimension=StyleDimension.VERBOSITY,
            value=0.7,
            sample_count=5,
            last_observed=time.time(),
        )
        assert sp.dimension == StyleDimension.VERBOSITY
        assert sp.value == 0.7
        assert sp.sample_count == 5

    def test_frozen(self):
        sp = StylePreference(
            pref_id="p1",
            dimension=StyleDimension.FORMALITY,
            value=0.5,
            sample_count=1,
            last_observed=time.time(),
        )
        with pytest.raises(Exception):
            sp.value = 0.9  # type: ignore[misc]


class TestStyleLearner:
    def test_init(self):
        learner = StyleLearner()
        vec = learner.get_style_vector()
        assert len(vec) == 6
        assert all(v == 0.5 for v in vec.values())

    def test_observe_dimension(self):
        learner = StyleLearner()
        sp = learner.observe(StyleDimension.VERBOSITY, 0.8)
        assert sp.dimension == StyleDimension.VERBOSITY
        assert sp.value == 0.8
        assert sp.sample_count == 1

    def test_observe_clamps_value(self):
        learner = StyleLearner()
        sp = learner.observe(StyleDimension.VERBOSITY, 2.0)
        assert sp.value == 1.0
        sp2 = learner.observe(StyleDimension.FORMALITY, -1.0)
        assert sp2.value == 0.0

    def test_repeated_observation_updates_value(self):
        learner = StyleLearner(learning_rate=0.5)
        learner.observe(StyleDimension.VERBOSITY, 0.0)
        sp = learner.observe(StyleDimension.VERBOSITY, 1.0)
        assert sp.sample_count == 2
        assert 0.4 < sp.value < 0.6

    def test_is_confident(self):
        learner = StyleLearner()
        for _ in range(8):
            learner.observe(StyleDimension.VERBOSITY, 0.7)
        assert learner.is_confident(StyleDimension.VERBOSITY, min_samples=5)
        assert not learner.is_confident(StyleDimension.FORMALITY, min_samples=5)

    def test_stats(self):
        learner = StyleLearner()
        learner.observe(StyleDimension.VERBOSITY, 0.8)
        learner.observe(StyleDimension.FORMALITY, 0.3)
        s = learner.stats()
        assert s["total_observations"] == 2


class TestPreferenceSource:
    def test_all_sources(self):
        assert PreferenceSource.EXPLICIT.value == "explicit"
        assert PreferenceSource.IMPLICIT_ACCEPT.value == "implicit_accept"
        assert PreferenceSource.IMPLICIT_REJECT.value == "implicit_reject"
        assert PreferenceSource.PATTERN.value == "pattern"


class TestAccumulatedPreference:
    def test_creation(self):
        ap = AccumulatedPreference(
            pref_id="p1",
            key="editor",
            value="vscode",
            source=PreferenceSource.EXPLICIT,
            weight=1.0,
            observation_count=3,
            first_seen=time.time(),
            last_seen=time.time(),
        )
        assert ap.key == "editor"
        assert ap.value == "vscode"
        assert ap.source == PreferenceSource.EXPLICIT

    def test_frozen(self):
        ap = AccumulatedPreference(
            pref_id="p1",
            key="editor",
            value="vim",
            source=PreferenceSource.PATTERN,
            weight=0.5,
            observation_count=1,
            first_seen=time.time(),
            last_seen=time.time(),
        )
        with pytest.raises(Exception):
            ap.weight = 1.0  # type: ignore[misc]


class TestPreferenceAccumulator:
    def test_init(self):
        acc = PreferenceAccumulator()
        assert acc.stats()["total_preferences"] == 0

    def test_record_new_preference(self):
        acc = PreferenceAccumulator()
        ap = acc.record("editor", "vscode", PreferenceSource.EXPLICIT)
        assert ap.key == "editor"
        assert ap.value == "vscode"
        assert ap.observation_count == 1

    def test_record_reinforces_existing(self):
        acc = PreferenceAccumulator()
        acc.record("editor", "vscode", PreferenceSource.EXPLICIT)
        ap = acc.record("editor", "vscode", PreferenceSource.EXPLICIT)
        assert ap.observation_count == 2
        assert ap.weight > 0.3

    def test_explicit_source_higher_weight(self):
        acc = PreferenceAccumulator()
        ap_explicit = acc.record("a", "x", PreferenceSource.EXPLICIT)
        ap_reject = acc.record("b", "y", PreferenceSource.IMPLICIT_REJECT)
        assert ap_explicit.weight > ap_reject.weight

    def test_get_top(self):
        acc = PreferenceAccumulator()
        acc.record("editor", "vscode", PreferenceSource.EXPLICIT)
        acc.record("editor", "vim", PreferenceSource.IMPLICIT_ACCEPT)
        top = acc.get_top(limit=10)
        assert len(top) >= 1

    def test_get_by_key(self):
        acc = PreferenceAccumulator()
        acc.record("editor", "vscode")
        acc.record("language", "python")
        results = acc.get("editor")
        assert len(results) >= 1
        assert all(p.key == "editor" for p in results)

    def test_stats(self):
        acc = PreferenceAccumulator()
        acc.record("a", "1")
        acc.record("b", "2")
        acc.record("a", "3")
        s = acc.stats()
        assert s["total_preferences"] == 3
        assert s["unique_keys"] == 2


class TestPersonaSnapshot:
    def test_creation(self):
        snap = PersonaSnapshot(
            snapshot_id="s1",
            agent_id="agent-1",
            traits={"verbosity": 0.8},
            style_vector={"verbosity": 0.7},
            preference_keys=["editor:vscode"],
            created_at=time.time(),
            version=1,
        )
        assert snap.agent_id == "agent-1"
        assert snap.version == 1
        assert snap.traits == {"verbosity": 0.8}

    def test_frozen(self):
        snap = PersonaSnapshot(
            snapshot_id="s1",
            agent_id="agent-1",
            traits={},
            style_vector={},
            preference_keys=[],
            created_at=time.time(),
            version=1,
        )
        with pytest.raises(Exception):
            snap.version = 2  # type: ignore[misc]


class TestPersonaStore:
    def test_init(self):
        store = PersonaStore(agent_id="test-agent")
        assert store.agent_id == "test-agent"

    def test_snapshot_creates_versioned_snapshot(self):
        store = PersonaStore()
        snap = store.snapshot()
        assert snap is not None
        assert snap.version == 1
        assert snap.agent_id == "default"

    def test_multiple_snapshots_increment_version(self):
        store = PersonaStore()
        s1 = store.snapshot()
        s2 = store.snapshot()
        assert s1.version == 1
        assert s2.version == 2

    def test_get_latest_snapshot(self):
        store = PersonaStore()
        assert store.get_latest_snapshot() is None
        store.snapshot()
        store.snapshot()
        latest = store.get_latest_snapshot()
        assert latest is not None
        assert latest.version == 2

    def test_compare_snapshots(self):
        store = PersonaStore()
        store.snapshot()
        store.identity.observe(TraitCategory.COMMUNICATION, "verbosity", 0.9)
        store.snapshot()
        deltas = store.compare_snapshots(1, 2)
        assert "traits" in deltas
        assert "style" in deltas

    def test_compare_nonexistent_snapshots(self):
        store = PersonaStore()
        result = store.compare_snapshots(99, 100)
        assert result == {}

    def test_stats(self):
        store = PersonaStore(agent_id="test")
        store.snapshot()
        store.snapshot()
        s = store.stats()
        assert s["agent_id"] == "test"
        assert s["snapshots"] == 2
        assert s["version"] == 2
