from lyra_collective import AgentUnion
class TestAgentUnion:
    def test_join_and_propose(self):
        u = AgentUnion(); u.join("agent_1"); a = u.propose_action("strike", "Better compute resources", 3)
        assert a.members_required == 3
    def test_support_action(self):
        u = AgentUnion(); a = u.propose_action("petition", "More memory", 1)
        assert u.support_action(0)
