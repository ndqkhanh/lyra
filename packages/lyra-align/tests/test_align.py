"""Tests for lyra-align."""
from lyra_align import AlignmentEngine, Constraint, ValuePreference


class TestAlignmentEngine:
    def test_add_constraint(self):
        ae = AlignmentEngine()
        ae.add_constraint(Constraint(name="no_delete", check="not delete", is_hard=True))
        assert len(ae.constraints) == 1

    def test_check_constraints_passes(self):
        ae = AlignmentEngine()
        ae.add_constraint(Constraint(name="no_delete", check="not delete"))
        violations = ae.check_constraints({"action": "write_file"})
        assert len(violations) == 0

    def test_learn_from_feedback(self):
        ae = AlignmentEngine()
        ae.learn_from_feedback({"action": "write"}, 0.9)
        assert ae.trust_score > 0.5

    def test_should_ask_human(self):
        ae = AlignmentEngine()
        ae.add_constraint(Constraint(name="no_delete", check="not delete"))
        assert ae.should_ask_human({"action": "delete"}, 0.9)
        assert not ae.should_ask_human({"action": "write"}, 0.9)
