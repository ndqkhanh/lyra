"""Tests for lyra-personality."""
from lyra_personality import AgentPersonality, BigFiveTraits


class TestAgentPersonality:
    def test_default_traits(self):
        p = AgentPersonality()
        assert 0 <= p.traits.openness <= 1
        assert 0 <= p.traits.neuroticism <= 1

    def test_express(self):
        p = AgentPersonality(BigFiveTraits(conscientiousness=0.9))
        modifiers = p.express({"task": "code_review"})
        assert modifiers["thoroughness"] > 0.9
        assert "thoroughness" in modifiers

    def test_learn_from_positive_feedback(self):
        p = AgentPersonality(BigFiveTraits(conscientiousness=0.5))
        old = p.traits.conscientiousness
        p.learn_from_feedback(0.9, "Great work on the review")
        assert p.traits.conscientiousness > old

    def test_learn_from_negative_feedback(self):
        p = AgentPersonality(BigFiveTraits(neuroticism=0.3))
        old = p.traits.neuroticism
        p.learn_from_feedback(0.2, "This needs improvement")
        assert p.traits.neuroticism > old

    def test_describe(self):
        p = AgentPersonality(BigFiveTraits(openness=0.9, conscientiousness=0.9))
        desc = p.describe()
        assert "curious" in desc
        assert "organized" in desc
