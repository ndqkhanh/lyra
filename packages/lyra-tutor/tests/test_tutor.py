"""Tests for lyra-tutor."""
from lyra_tutor import TutorAgent

class TestTutorAgent:
    def test_register(self):
        t = TutorAgent()
        m = t.register_learner("alice", "visual")
        assert m.preferred_style == "visual"

    def test_assess(self):
        t = TutorAgent()
        t.register_learner("bob")
        r = t.assess("bob", 0.9)
        assert r["difficulty"] == "intermediate"
