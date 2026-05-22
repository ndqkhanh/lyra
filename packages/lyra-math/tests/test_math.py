"""Tests for lyra-math."""
from lyra_math import MathAgent
class TestMathAgent:
    def test_solve(self):
        m = MathAgent(); e = m.solve("2 + 2")
        assert e.result == 4.0
    def test_check_proof(self):
        m = MathAgent(); r = m.check_proof("Pythagoras", ["step1", "step2", "step3"])
        assert r["valid"]
