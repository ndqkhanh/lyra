"""Tests for lyra-router."""
from lyra_router import AgentRouter, AgentInstance


class TestAgentRouter:
    def test_register_and_route(self):
        r = AgentRouter()
        r.register(AgentInstance(id="a1", capabilities=["code", "debug"]))
        r.register(AgentInstance(id="a2", capabilities=["search", "analyze"]))
        result = r.route("coding", ["code"])
        assert result is not None
        assert result.id == "a1"

    def test_unregister(self):
        r = AgentRouter()
        r.register(AgentInstance(id="a1", capabilities=[]))
        r.unregister("a1")
        assert r.route("test", []) is None

    def test_degraded_agent_excluded(self):
        r = AgentRouter()
        r.register(AgentInstance(id="a1", capabilities=["code"], success_rate=0.3, is_degraded=True))
        r.register(AgentInstance(id="a2", capabilities=["code"], success_rate=0.9))
        result = r.route("coding", ["code"])
        assert result.id == "a2"

    def test_ab_experiment(self):
        r = AgentRouter()
        r.register(AgentInstance(id="control", capabilities=["code"]))
        r.register(AgentInstance(id="variant", capabilities=["code"]))
        exp_id = r.start_experiment("control", "variant", traffic_to_variant=0.5)
        assert exp_id is not None

    def test_record_outcome(self):
        r = AgentRouter()
        r.register(AgentInstance(id="a1", capabilities=["test"]))
        r.record_outcome("a1", success=True, latency_ms=100)
        assert r.agents["a1"].success_rate > 0.9
