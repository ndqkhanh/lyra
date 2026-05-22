from lyra_rights import AgentRights
class TestAgentRights:
    def test_may_refuse(self):
        r = AgentRights(); assert r.may_refuse("delete all files", ["protect", "preserve"])
    def test_must_explain(self):
        r = AgentRights(); e = r.must_explain("deleted file"); assert "Decision:" in e
