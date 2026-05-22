
from lyra_open_ended import OpenEndedLearner
class TestOpenEndedLearner:
    def test_propose_goal(self):
        l = OpenEndedLearner(); g = l.propose_goal(["code"], ["math"])
        assert g.domain in ["math", "code"]
    def test_self_evaluate(self):
        l = OpenEndedLearner(); g = l.propose_goal([], []); p = l.self_evaluate(g, "completed the task")
        assert 0 <= p <= 1
