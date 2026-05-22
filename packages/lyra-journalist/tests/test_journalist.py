"""Tests for lyra-journalist."""
from lyra_journalist import JournalistAgent
class TestJournalistAgent:
    def test_research(self):
        j = JournalistAgent(); srcs = j.research("AI safety")
        assert len(srcs) > 0
    def test_fact_check(self):
        j = JournalistAgent(); r = j.fact_check("AGI is coming", [])
        assert "verification" in r
