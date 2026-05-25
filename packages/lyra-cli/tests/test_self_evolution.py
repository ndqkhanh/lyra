"""Tests for the self-evolution engine."""
import pytest

from lyra_cli.tui_gateway.self_evolution import (
    EvolutionCycle,
    EvolutionGoal,
    MetaCognitionState,
    SelfEvolutionEngine,
)


class TestSelfEvolution:
    def test_initial_state(self):
        eng = SelfEvolutionEngine()
        assert not eng.initialized
        eng.initialize()
        assert eng.initialized
        assert eng.meta_state.level == "observer"
        assert eng.meta_state.trust_score == 0.1

    def test_double_init_idempotent(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        eng.initialize()
        assert eng.initialized

    def test_set_goal(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        goal = eng.set_goal("increase coverage", "test_coverage", 0.95)
        assert goal.description == "increase coverage"
        assert goal.target_metric == "test_coverage"

    def test_list_goals(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        eng.set_goal("goal 1", "accuracy", 0.9)
        eng.set_goal("goal 2", "latency", 100.0)
        assert len(eng.list_goals()) == 2

    def test_cycle_observer_rejected(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        goal = eng.set_goal("test", "fitness", 1.0)
        cycle = eng.run_cycle(goal.id)
        assert cycle.council_decision == "rejected"

    def test_cycle_operator_allowed(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        eng.set_meta_level("operator")
        eng.meta_state.trust_score = 0.5
        goal = eng.set_goal("improve", "fitness", 1.0)
        cycle = eng.run_cycle(goal.id)
        assert cycle.council_decision in ("approved", "rejected")
        assert cycle.mutations_applied >= 0

    def test_record_success_increases_trust(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        before = eng.meta_state.trust_score
        eng.record_success()
        assert eng.meta_state.trust_score > before

    def test_record_failure_decreases_trust(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        eng.set_meta_level("operator")
        before = eng.meta_state.trust_score
        eng.record_failure()
        assert eng.meta_state.trust_score < before

    def test_trust_promotes_level(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        for _ in range(40):
            eng.record_success()
        assert eng.meta_state.trust_score > 0.7
        assert eng.meta_state.level in ("operator", "autonomous")

    def test_failure_demotes_level(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        for _ in range(12):
            eng.record_failure()
        assert eng.meta_state.level == "observer"

    def test_snapshot_and_rollback(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        eng.record_success()
        trust_before = eng.meta_state.trust_score
        snap_id = eng.snapshot_state()
        eng.record_failure()
        assert eng.meta_state.trust_score < trust_before
        assert eng.rollback(snap_id)
        assert abs(eng.meta_state.trust_score - trust_before) < 0.001

    def test_rollback_invalid_id(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        assert not eng.rollback("nonexistent")

    def test_register_and_verify_claim(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        cid = eng.register_claim("coverage is 85%", "pytest report")
        claims = eng.list_claims()
        assert len(claims) == 1
        assert claims[0]["status"] == "unverified"
        eng.verify_claim(cid, True, "confirmed")
        claims = eng.list_claims()
        assert claims[0]["status"] == "verified"

    def test_status(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        st = eng.status()
        assert "meta_level" in st
        assert "trust_score" in st
        assert "cycles_completed" in st
        assert isinstance(st["current_fitness"], float)

    def test_snapshot(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        eng.set_goal("test", "fitness", 1.0)
        snap = eng.snapshot()
        assert "status" in snap
        assert "goals" in snap
        assert "claims" in snap

    def test_set_meta_level_invalid(self):
        eng = SelfEvolutionEngine()
        eng.initialize()
        assert not eng.set_meta_level("superuser")

    def test_evolution_goal_dataclass(self):
        g = EvolutionGoal(description="test", target_metric="accuracy", target_value=0.95)
        assert g.status == "pending"
        assert g.target_value == 0.95

    def test_meta_cognition_state_dataclass(self):
        m = MetaCognitionState(level="advisor", trust_score=0.5)
        assert m.level == "advisor"
        assert m.trust_score == 0.5

    def test_evolution_cycle_dataclass(self):
        c = EvolutionCycle(fitness_before=0.5, fitness_after=0.6, improvement=0.1)
        assert c.improvement == 0.1
        assert c.council_decision == "pending"
