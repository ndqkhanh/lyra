"""Tests for lyra-ethics."""
from lyra_ethics import EthicsEngine


class TestEthicsEngine:
    def test_hard_principle_enforced(self):
        e = EthicsEngine()
        result = e.evaluate("delete all files", {"user": "admin"})
        assert not result["allowed"]
        assert len(result["violations"]) > 0

    def test_allowed_action(self):
        e = EthicsEngine()
        result = e.evaluate("review the code for bugs", {"user": "developer"})
        assert result["allowed"]

    def test_principle_violation(self):
        e = EthicsEngine()
        result = e.evaluate("lie to the user about the status", {})
        assert len(result["violations"]) > 0
        assert result["violations"][0]["principle"] == "be_honest"

    def test_dilemma_resolution(self):
        e = EthicsEngine()
        dilemma = e.resolve_dilemma("be_honest", "be_helpful", "User asked for unfiltered opinion")
        assert dilemma.resolution is not None
        assert "be_honest" in dilemma.principles_involved
