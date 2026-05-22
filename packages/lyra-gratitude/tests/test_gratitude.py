"""Tests for lyra-gratitude."""
from lyra_gratitude import GratitudeSystem

class TestGratitudeSystem:
    def test_express(self):
        g = GratitudeSystem()
        r = g.express_gratitude("a1", "a2", "helped with review")
        assert r.from_agent == "a1"
        assert g.stats["total_gratitude"] == 1

    def test_relationship(self):
        g = GratitudeSystem()
        g.express_gratitude("a1", "a2", "great work")
        g.express_gratitude("a2", "a1", "thanks")
        assert g.get_relationship("a1", "a2") > 0
