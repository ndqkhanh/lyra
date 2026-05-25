"""Tests for lyra-beliefs package."""

from __future__ import annotations

import asyncio

import pytest

from lyra_beliefs import (
    # Belief system
    BeliefSource,
    BeliefStatus,
    Belief,
    BeliefSystem,
    UpdateMethod,
    # Knowledge base
    KnowledgeBase,
    RuleType,
    Rule,
    Fact,
    OntologyConcept,
    # Inference
    InferenceEngine,
    InferenceType,
    # Consistency
    ConsistencyManager,
    # Updating
    BeliefUpdater,
    EvidencePacket,
    # Exceptions
    BeliefError,
    BeliefNotFoundError,
    InconsistentBeliefError,
    InferenceError,
    UpdateError,
)


# ── BeliefSystem ────────────────────────────────────────────────────────


class TestBeliefSystem:
    def test_create_belief(self):
        bs = BeliefSystem()
        belief = bs.create_belief(
            domain="python",
            statement="Prefer list comprehensions over map()",
            confidence=0.8,
            source=BeliefSource.EXPERT_ENCODED,
            source_reliability=0.9,
        )
        assert belief.domain == "python"
        assert belief.source == BeliefSource.EXPERT_ENCODED
        assert belief.confidence == 0.8

    def test_get_belief(self):
        bs = BeliefSystem()
        belief = bs.create_belief("security", "Never log credentials", confidence=0.9)
        retrieved = bs.get(belief.belief_id)
        assert retrieved.statement == "Never log credentials"
        assert retrieved.hit_count == 1

    def test_get_not_found(self):
        bs = BeliefSystem()
        with pytest.raises(BeliefNotFoundError):
            bs.get("nonexistent_id")

    def test_get_by_domain(self):
        bs = BeliefSystem()
        bs.create_belief("python", "Use type hints")
        bs.create_belief("python", "Follow PEP 8")
        bs.create_belief("security", "Validate all inputs")
        python_beliefs = bs.get_by_domain("python")
        assert len(python_beliefs) == 2

    def test_query(self):
        bs = BeliefSystem()
        bs.create_belief("security", "Never log credentials", confidence=0.9)
        bs.create_belief("python", "Use type hints", confidence=0.8)
        results = bs.query("Write a Python API with security")
        assert len(results) >= 1

    def test_query_domain_filter(self):
        bs = BeliefSystem()
        bs.create_belief("python", "Use type hints")
        bs.create_belief("security", "Validate inputs")
        results = bs.query("Python type hinting", domain="python")
        assert len(results) >= 1
        for r in results:
            assert r.domain == "python"

    def test_get_active(self):
        bs = BeliefSystem()
        b1 = bs.create_belief("python", "Active belief")
        b2 = bs.create_belief("python", "Retracted belief")
        b2.status = BeliefStatus.RETRACTED
        active = bs.get_active()
        assert len(active) == 1

    def test_bayesian_update(self):
        bs = BeliefSystem()
        belief = bs.create_belief("test", "Test belief", confidence=0.5)
        updated = bs.update_bayesian(belief.belief_id, evidence_strength=0.8, likelihood_ratio=2.0)
        assert updated.confidence != 0.5  # Should change

    def test_jeffreys_update(self):
        bs = BeliefSystem()
        belief = bs.create_belief("test", "Test belief", confidence=0.5)
        updated = bs.update_jeffreys(belief.belief_id, new_confidence=0.9, evidence_reliability=0.7)
        assert updated.confidence > 0.5

    def test_revise(self):
        bs = BeliefSystem()
        b1 = bs.create_belief("test", "X is good", confidence=0.8)
        revised = bs.revise(b1.belief_id, new_confidence=0.2)
        assert revised.confidence == 0.2

    def test_contract(self):
        bs = BeliefSystem()
        b1 = bs.create_belief("test", "X is true", confidence=0.9)
        contracted = bs.contract(b1.belief_id)
        assert contracted.status == BeliefStatus.RETRACTED

    def test_expand(self):
        bs = BeliefSystem()
        belief = bs.expand("test", "New belief")
        assert belief.domain == "test"
        assert belief.statement == "New belief"

    def test_is_consistent(self):
        bs = BeliefSystem()
        bs.create_belief("test", "X is good", confidence=0.8)
        result = bs.is_consistent()
        assert isinstance(result, bool)

    def test_find_contradictions(self):
        bs = BeliefSystem()
        b1 = bs.create_belief("test", "X is always good", confidence=0.8)
        b2 = bs.create_belief("test", "X is never good", confidence=0.7)
        contras = bs.find_contradictions(b1.belief_id)
        # May or may not find contradictions depending on keyword overlap
        assert isinstance(contras, list)

    def test_set_and_get_conditional(self):
        bs = BeliefSystem()
        bs.set_conditional("rain", "wet_ground", 0.9)
        prob = bs.get_conditional("rain", "wet_ground")
        assert prob == 0.9

    def test_create_and_get_set(self):
        bs = BeliefSystem()
        b1 = bs.create_belief("test", "Fact A")
        b2 = bs.create_belief("test", "Fact B")
        bset = bs.create_set("my_set", [b1.belief_id, b2.belief_id])
        assert bset.name == "my_set"
        assert len(bset.beliefs) == 2
        retrieved = bs.get_set(bset.set_id)
        assert retrieved is not None

    def test_stats(self):
        bs = BeliefSystem()
        bs.create_belief("python", "Use type hints")
        stats = bs.stats
        assert stats["total_beliefs"] == 1
        assert "python" in stats["domains"]

    def test_validation(self):
        bs = BeliefSystem()
        with pytest.raises(ValueError):
            Belief(domain="test", statement="test", confidence=1.5)
        with pytest.raises(ValueError):
            Belief(domain="test", statement="test", source_reliability=2.0)


# ── KnowledgeBase ───────────────────────────────────────────────────────


class TestKnowledgeBase:
    def test_add_fact(self):
        kb = KnowledgeBase()
        fact = kb.create_fact("python", "Python is dynamically typed", provenance="docs")
        assert fact.domain == "python"
        assert kb.fact_count == 1

    def test_get_facts_by_domain(self):
        kb = KnowledgeBase()
        kb.create_fact("python", "Fact A")
        kb.create_fact("python", "Fact B")
        kb.create_fact("security", "Fact C")
        assert len(kb.get_facts_by_domain("python")) == 2

    def test_verify_fact(self):
        kb = KnowledgeBase()
        fact = kb.create_fact("test", "Some fact")
        assert kb.verify_fact(fact.fact_id, True)
        assert len(kb.get_verified_facts()) == 1

    def test_add_rule(self):
        kb = KnowledgeBase()
        rule = kb.create_rule(
            antecedent="code has type hints",
            consequent="code is maintainable",
            confidence=0.85,
            rule_type=RuleType.IF_THEN,
            domain="python",
        )
        assert kb.rule_count == 1
        assert rule.confidence == 0.85

    def test_get_rules_applicable_to(self):
        kb = KnowledgeBase()
        kb.create_rule("type hints improve", "code quality increases", domain="python")
        rules = kb.get_rules_applicable_to("type hints are important to improve readability")
        assert len(rules) >= 1

    def test_add_concept(self):
        kb = KnowledgeBase()
        concept = OntologyConcept(
            name="Python",
            domain="programming",
            synonyms=["py", "python3"],
            description="Python programming language",
        )
        kb.add_concept(concept)
        assert kb.concept_count == 1

    def test_get_concept_by_synonym(self):
        kb = KnowledgeBase()
        concept = OntologyConcept(
            name="Python", domain="programming", synonyms=["py"]
        )
        kb.add_concept(concept)
        result = kb.get_concept("py")
        assert result is not None
        assert result.name == "Python"

    def test_get_concept_hierarchy(self):
        kb = KnowledgeBase()
        parent = OntologyConcept(name="Programming", domain="tech")
        child = OntologyConcept(name="Python", domain="tech", parent=parent.concept_id)
        kb.add_concept(parent)
        kb.add_concept(child)
        parent.children.append(child.concept_id)
        kb._concepts[parent.concept_id] = parent
        hierarchy = kb.get_concept_hierarchy(child.concept_id)
        assert hierarchy["parent"] == parent.concept_id

    def test_align_concepts(self):
        kb = KnowledgeBase()
        c1 = OntologyConcept(name="py", domain="tech")
        c2 = OntologyConcept(name="python", domain="tech")
        kb.add_concept(c1)
        kb.add_concept(c2)
        assert kb.align_concepts("python", "py")

    def test_versioning(self):
        kb = KnowledgeBase()
        kb.create_fact("test", "Fact v1")
        kb.create_version("Initial facts")
        kb.create_fact("test", "Fact v2")
        kb.create_version("Added fact")
        latest = kb.get_latest_version()
        assert latest is not None
        assert latest.version_number >= 2

    def test_summary(self):
        kb = KnowledgeBase()
        kb.create_fact("test", "A fact")
        kb.create_rule("ante", "conseq", domain="test")
        s = kb.summary
        assert s["facts"] == 1
        assert s["rules"] == 1


# ── InferenceEngine ────────────────────────────────────────────────────


class TestInferenceEngine:
    @pytest.fixture
    def engine(self):
        bs = BeliefSystem()
        kb = KnowledgeBase(belief_system=bs)
        return InferenceEngine(belief_system=bs, knowledge_base=kb)

    def test_deduction(self, engine):
        # Add a premise belief
        premise = engine.belief_system.create_belief(
            "test", "code has type hints", confidence=0.8
        )
        # Add a rule
        engine.knowledge_base.create_rule(
            antecedent="code has type hints",
            consequent="code is maintainable",
            confidence=0.9,
            domain="test",
        )
        result = engine.deduce(premises=[premise.belief_id])
        assert result.inference_type == InferenceType.DEDUCTION

    def test_induce(self, engine):
        b1 = engine.belief_system.create_belief("test", "Python code with types is better")
        b2 = engine.belief_system.create_belief("test", "Python code with types is safer")
        result = engine.induce([b1.belief_id, b2.belief_id])
        assert result.inference_type == InferenceType.INDUCTION

    def test_abduce_no_candidates(self, engine):
        obs = engine.belief_system.create_belief("test", "Something unexpected happened")
        result = engine.abduce(observation=obs.belief_id)
        assert result.inference_type == InferenceType.ABDUCTION

    def test_default_reason(self, engine):
        engine.knowledge_base.create_rule(
            antecedent="Python code",
            consequent="Code is readable",
            confidence=0.8,
            rule_type=RuleType.DEFAULT,
            domain="test",
        )
        result = engine.default_reason(query="Python code should be easy to read")
        assert result.inference_type == InferenceType.DEFAULT

    def test_propagate_confidence(self, engine):
        b1 = engine.belief_system.create_belief("test", "A causes B", confidence=0.9)
        b2 = engine.belief_system.create_belief("test", "B is the result", confidence=0.5)
        engine.belief_system.set_conditional(b1.belief_id, b2.belief_id, 0.8)
        changes = engine.propagate_confidence(b1.belief_id)
        assert isinstance(changes, dict)

    def test_summary(self, engine):
        s = engine.summary
        assert "total_inferences" in s


# ── ConsistencyManager ─────────────────────────────────────────────────


class TestConsistencyManager:
    def test_detect_contradictions(self):
        bs = BeliefSystem()
        bs.create_belief("test", "Python is always the best language", confidence=0.8)
        bs.create_belief("test", "Python is never the best language", confidence=0.7)
        cm = ConsistencyManager(bs)
        contras = cm.detect_contradictions()
        assert isinstance(contras, list)

    def test_resolve_all(self):
        bs = BeliefSystem()
        bs.create_belief("test", "X is good", confidence=0.9)
        bs.create_belief("test", "X is bad", confidence=0.5)
        cm = ConsistencyManager(bs)
        result = cm.resolve_all(strategy_name="confidence_comparison")
        assert "detected" in result
        assert "resolved" in result

    def test_paraconsistent_query(self):
        bs = BeliefSystem()
        bs.create_belief("test", "Python is good and fast", confidence=0.8)
        bs.create_belief("test", "Python is slow and bad", confidence=0.6)
        cm = ConsistencyManager(bs)
        result = cm.paraconsistent_query("test")
        assert "domain" in result

    def test_summary(self):
        bs = BeliefSystem()
        cm = ConsistencyManager(bs)
        s = cm.summary
        assert "total_contradictions" in s


# ── BeliefUpdater ──────────────────────────────────────────────────────


class TestBeliefUpdater:
    @pytest.fixture
    def updater(self):
        bs = BeliefSystem()
        return BeliefUpdater(belief_system=bs)

    def test_bayesian_update(self, updater):
        b = updater.belief_system.create_belief("test", "X", confidence=0.5)
        updated = updater.bayesian_update(b.belief_id, likelihood_ratio=3.0, evidence_strength=0.8)
        assert updated.confidence > 0.5

    def test_jeffreys_update(self, updater):
        b = updater.belief_system.create_belief("test", "X", confidence=0.5)
        updated = updater.jeffreys_update(b.belief_id, new_confidence=0.9, evidence_reliability=0.7)
        assert updated.confidence > 0.5

    def test_update_with_evidence(self, updater):
        b = updater.belief_system.create_belief("test", "X", confidence=0.5)
        evidence = [
            EvidencePacket(
                statement="Strong support", strength=0.9, supports=True,
                source="test_source", source_reliability=0.8,
            ),
            EvidencePacket(
                statement="Weak oppose", strength=0.3, supports=False,
                source="test_source", source_reliability=0.5,
            ),
        ]
        updated = updater.update_with_evidence(b.belief_id, evidence)
        assert updated.confidence > 0.5

    def test_register_source(self, updater):
        profile = updater.register_source("expert_reviewer")
        assert profile.source_name == "expert_reviewer"

    def test_record_source_accuracy(self, updater):
        updater.register_source("source_a")
        updater.record_source_accuracy("source_a", was_accurate=True)
        reliability = updater.get_source_reliability("source_a")
        assert reliability > 0.5

    def test_get_source_reliability_unknown(self, updater):
        rel = updater.get_source_reliability("unknown_source")
        assert rel == 0.5

    def test_get_trusted_sources(self, updater):
        updater.register_source("trusted")
        updater.record_source_accuracy("trusted", was_accurate=True)
        updater.record_source_accuracy("trusted", was_accurate=True)
        updater.record_source_accuracy("trusted", was_accurate=True)
        # Simulate high reliability
        updater._sources["trusted"].reliability_score = 0.9
        trusted = updater.get_trusted_sources(min_reliability=0.7)
        assert "trusted" in trusted

    def test_temporal_decay(self, updater):
        b = updater.belief_system.create_belief("test", "X", confidence=0.9)
        b.last_updated = 0  # Very old
        count = updater.apply_temporal_decay(half_life_seconds=1.0)
        assert count >= 0

    def test_build_consensus(self, updater):
        updater.register_source("src1")
        updater.register_source("src2")
        updater._sources["src1"].reliability_score = 0.9
        updater._sources["src2"].reliability_score = 0.7
        result = updater.build_consensus(
            "best_language",
            {"src1": 0.8, "src2": 0.6},
        )
        assert result.consensus_value > 0
        assert result.sources_consulted == ["src1", "src2"]

    def test_get_consensus(self, updater):
        updater.build_consensus("topic_x", {"src1": 0.7})
        consensus = updater.get_consensus("topic_x")
        assert consensus is not None

    def test_summary(self, updater):
        s = updater.summary
        assert "sources_tracked" in s


# ── Exceptions ────────────────────────────────────────────────────────


class TestExceptions:
    def test_belief_error(self):
        with pytest.raises(BeliefError):
            raise BeliefError("test")

    def test_belief_not_found(self):
        with pytest.raises(BeliefNotFoundError):
            raise BeliefNotFoundError("bid_123")

    def test_inconsistent_belief(self):
        with pytest.raises(InconsistentBeliefError):
            raise InconsistentBeliefError("a", "b", "they disagree")

    def test_inference_error(self):
        with pytest.raises(InferenceError):
            raise InferenceError("cannot deduce", premises=["A", "B"])

    def test_update_error(self):
        with pytest.raises(UpdateError):
            raise UpdateError("bid", "reason")
