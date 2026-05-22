
from lyra_challenge import ChallengeEngine
class TestChallengeEngine:
    def test_generate(self):
        e = ChallengeEngine(); c = e.generate("math", 0.5)
        assert c.domain == "math"
    def test_evaluate(self):
        e = ChallengeEngine(); c = e.generate(); s = e.evaluate(type('s',(),{"agent_id":"a1","challenge_id":c.id,"result":{}})(), c)
        assert isinstance(s.passed, bool)
