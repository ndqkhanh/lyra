"""Tests for Belief and CBTBeliefHierarchy."""

from datetime import datetime

import pytest

from lyra_memory.cognitive.beliefs import Belief, CBTBeliefHierarchy


class TestBelief:
    def test_default_values(self):
        b = Belief(content="I am capable")
        assert b.content == "I am capable"
        assert b.confidence == 1.0
        assert b.evidence_count == 0
        assert isinstance(b.last_updated, datetime)
        assert b.source_experiences == []

    def test_auto_generated_id(self):
        b1 = Belief(content="test")
        b2 = Belief(content="test")
        assert b1.id != b2.id
        assert len(b1.id) == 32

    def test_strengthen_increases_confidence(self):
        b = Belief(content="I am capable", confidence=0.5)
        b.strengthen("exp-1", delta=0.1)
        assert b.confidence == 0.6
        assert b.evidence_count == 1
        assert "exp-1" in b.source_experiences

    def test_strengthen_clamped_at_1(self):
        b = Belief(content="test", confidence=0.98)
        b.strengthen("exp-2", delta=0.1)
        assert b.confidence == 1.0

    def test_weaken_decreases_confidence(self):
        b = Belief(content="I am capable", confidence=0.8)
        b.weaken("exp-3", delta=0.2)
        assert b.confidence == pytest.approx(0.6)
        assert b.evidence_count == 1
        assert "exp-3" in b.source_experiences

    def test_weaken_clamped_at_0(self):
        b = Belief(content="test", confidence=0.05)
        b.weaken("exp-4", delta=0.2)
        assert b.confidence == 0.0

    def test_multiple_experiences(self):
        b = Belief(content="test", confidence=0.5)
        b.strengthen("e1", delta=0.1)
        b.strengthen("e2", delta=0.05)
        b.weaken("e3", delta=0.15)
        assert b.evidence_count == 3
        assert len(b.source_experiences) == 3

    def test_is_stable_requires_confidence_and_evidence(self):
        b = Belief(content="stable", confidence=0.9, evidence_count=5)
        assert b.is_stable is True

    def test_is_stable_false_when_low_confidence(self):
        b = Belief(content="unstable", confidence=0.7, evidence_count=5)
        assert b.is_stable is False

    def test_is_stable_false_when_few_evidence(self):
        b = Belief(content="unstable", confidence=0.95, evidence_count=1)
        assert b.is_stable is False

    def test_last_updated_changes_on_strengthen(self):
        b = Belief(content="test")
        before = b.last_updated
        b.strengthen("exp-5")
        assert b.last_updated >= before

    def test_last_updated_changes_on_weaken(self):
        b = Belief(content="test")
        before = b.last_updated
        b.weaken("exp-6")
        assert b.last_updated >= before


class TestCBTBeliefHierarchy:
    def _make_hierarchy(self) -> CBTBeliefHierarchy:
        h = CBTBeliefHierarchy()
        h.add_core_belief("I am capable", confidence=0.7)
        h.add_core_belief("The world is predictable", confidence=0.6)
        h.add_intermediate_belief("If I plan well, I succeed", confidence=0.5)
        h.add_intermediate_belief("If I fail, I can learn", confidence=0.8)
        h.add_automatic_thought("This task looks hard", confidence=0.4)
        h.add_automatic_thought("I have done this before", confidence=0.6)
        return h

    def test_add_core_belief(self):
        h = CBTBeliefHierarchy()
        b = h.add_core_belief("I am capable", confidence=0.7)
        assert b in h.core_beliefs
        assert b.content == "I am capable"

    def test_add_intermediate_belief(self):
        h = CBTBeliefHierarchy()
        b = h.add_intermediate_belief("If I plan well, I succeed")
        assert b in h.intermediate_beliefs

    def test_add_automatic_thought(self):
        h = CBTBeliefHierarchy()
        b = h.add_automatic_thought("This looks hard")
        assert b in h.automatic_thoughts

    def test_total_beliefs(self):
        h = self._make_hierarchy()
        assert h.total_beliefs == 6

    def test_stable_core_count(self):
        h = CBTBeliefHierarchy()
        h.add_core_belief("stable enough", confidence=0.9)
        h.core_beliefs[0].evidence_count = 5
        h.add_core_belief("unstable", confidence=0.5)
        assert h.stable_core_count == 1

    # ── Cathartic updates ──

    def test_weak_valence_does_not_modify_any_tier(self):
        h = self._make_hierarchy()
        modified = h.cathartic_update(
            experience_content="I planned well and succeeded",
            emotional_valence=0.3,
            experience_id="exp-low",
        )
        assert len(modified) == 0

    def test_moderate_valence_impacts_automatic_thoughts(self):
        h = self._make_hierarchy()
        modified = h.cathartic_update(
            experience_content="task hard fail",
            emotional_valence=-0.6,
            experience_id="exp-mod",
        )
        assert len(modified) > 0
        for b in modified:
            assert b in h.automatic_thoughts

    def test_moderate_valence_does_not_impact_core(self):
        h = self._make_hierarchy()
        original_confidences = [b.confidence for b in h.core_beliefs]
        h.cathartic_update(
            experience_content="planned well succeeded",
            emotional_valence=0.6,
        )
        assert [b.confidence for b in h.core_beliefs] == original_confidences

    def test_strong_valence_impacts_intermediate_beliefs(self):
        h = self._make_hierarchy()
        modified = h.cathartic_update(
            experience_content="plan well succeed learn fail",
            emotional_valence=-0.85,
            experience_id="exp-strong",
        )
        impacted_tiers = set()
        for b in modified:
            if b in h.automatic_thoughts:
                impacted_tiers.add("auto")
            elif b in h.intermediate_beliefs:
                impacted_tiers.add("intermediate")
        assert "intermediate" in impacted_tiers

    def test_transformative_valence_impacts_core_beliefs(self):
        h = self._make_hierarchy()
        modified = h.cathartic_update(
            experience_content="I am truly capable world predictable",
            emotional_valence=0.95,
            experience_id="exp-transform",
        )
        impacted_tiers = set()
        for b in modified:
            if b in h.core_beliefs:
                impacted_tiers.add("core")
            elif b in h.intermediate_beliefs:
                impacted_tiers.add("intermediate")
            elif b in h.automatic_thoughts:
                impacted_tiers.add("auto")
        assert "core" in impacted_tiers

    def test_positive_valence_strengthens_beliefs(self):
        h = CBTBeliefHierarchy()
        b = h.add_automatic_thought("I can handle complex tasks effectively")
        original_conf = b.confidence
        h.cathartic_update(
            experience_content="complex tasks handled effectively",
            emotional_valence=0.7,
        )
        assert b.confidence >= original_conf

    def test_negative_valence_weakens_beliefs(self):
        h = CBTBeliefHierarchy()
        b = h.add_automatic_thought("I can handle complex tasks effectively")
        original_conf = b.confidence
        h.cathartic_update(
            experience_content="complex tasks handled effectively",
            emotional_valence=-0.7,
        )
        assert b.confidence <= original_conf

    def test_irrelevant_experience_does_not_affect_belief(self):
        h = CBTBeliefHierarchy()
        b = h.add_automatic_thought("I am good at python programming tasks")
        original_conf = b.confidence
        h.cathartic_update(
            experience_content="javascript react components rendering slowly",
            emotional_valence=0.9,
        )
        assert b.confidence == original_conf

    # ── get_active_beliefs ──

    def test_get_active_beliefs_keyword_overlap(self):
        h = self._make_hierarchy()
        active = h.get_active_beliefs("I am planning a hard task")
        assert len(active) > 0
        contents = {b.content for b in active}
        assert any("plan" in c.lower() for c in contents)

    def test_get_active_beliefs_no_match(self):
        h = self._make_hierarchy()
        active = h.get_active_beliefs("xyzzy foobar qux")
        assert active == []

    def test_get_active_beliefs_includes_all_tiers(self):
        h = self._make_hierarchy()
        active = h.get_active_beliefs("I am capable of planning well for this task")
        tiers_found = set()
        for b in active:
            if b in h.core_beliefs:
                tiers_found.add("core")
            elif b in h.intermediate_beliefs:
                tiers_found.add("intermediate")
            elif b in h.automatic_thoughts:
                tiers_found.add("auto")
        assert len(tiers_found) >= 2

    def test_cathartic_update_uses_provided_experience_id(self):
        h = self._make_hierarchy()
        modified = h.cathartic_update(
            experience_content="fail plan",
            emotional_valence=-0.75,
            experience_id="custom-eid-42",
        )
        for b in modified:
            assert "custom-eid-42" in b.source_experiences

    def test_empty_hierarchy_cathartic_no_error(self):
        h = CBTBeliefHierarchy()
        modified = h.cathartic_update(
            experience_content="anything",
            emotional_valence=0.99,
        )
        assert modified == []

    def test_auto_generated_experience_id(self):
        h = self._make_hierarchy()
        modified = h.cathartic_update(
            experience_content="task plan hard fail",
            emotional_valence=-0.8,
        )
        if modified:
            assert len(modified[0].source_experiences) > 0
            eid = modified[0].source_experiences[-1]
            assert len(eid) == 32
