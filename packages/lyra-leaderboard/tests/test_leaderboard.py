"""Tests for lyra-leaderboard."""
from lyra_leaderboard import AGILeaderboard


class TestAGILeaderboard:
    def test_record(self):
        lb = AGILeaderboard()
        lb.record("v0.1.0", 65.0, {"specbench": 70.0, "agentbench": 60.0})
        assert lb.stats["total_entries"] == 1

    def test_compare(self):
        lb = AGILeaderboard()
        lb.record("v0.1.0", 65.0, {"specbench": 70.0, "agentbench": 60.0})
        lb.record("v0.2.0", 80.0, {"specbench": 85.0, "agentbench": 75.0})
        comp = lb.compare("v0.1.0", "v0.2.0")
        assert comp is not None
        assert comp.improvement == 15.0

    def test_top_versions(self):
        lb = AGILeaderboard()
        lb.record("v0.1.0", 50.0, {"a": 50})
        lb.record("v0.2.0", 80.0, {"a": 80})
        lb.record("v0.3.0", 70.0, {"a": 70})
        top = lb.get_top_versions(2)
        assert top[0].version == "v0.2.0"
        assert len(top) == 2

    def test_stats_empty(self):
        lb = AGILeaderboard()
        assert lb.stats["entries"] == 0
