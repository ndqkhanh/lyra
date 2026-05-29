"""Tests for Gossip Memory package."""

from lyra_gossip_memory import DualPoolMemory, GossipProtocol, MemoryItem


class TestDualPoolMemory:
    def test_add_and_query(self):
        m = DualPoolMemory()
        m.add_exploit(MemoryItem(id="m1", content="data", source_agent="a1", importance=0.8, timestamp=100.0, context_tags=["code"]))
        results = m.query("code")
        assert len(results) > 0

    def test_promote_to_exploit(self):
        m = DualPoolMemory()
        m.add_explore(MemoryItem(id="m1", content="test", source_agent="a1", importance=0.5, timestamp=100.0))
        assert m.promote_to_exploit("m1")
        assert len(m.exploit_pool) == 1


class TestGossipProtocol:
    def test_register_agent(self):
        g = GossipProtocol()
        m = g.register_agent("agent_1")
        assert isinstance(m, DualPoolMemory)

    def test_share_and_receive(self):
        g = GossipProtocol()
        g.register_agent("agent_1")
        g.register_agent("agent_2")
        m1 = g.agent_memories["agent_1"]
        m1.add_exploit(MemoryItem(id="m1", content="shared", source_agent="agent_1", importance=0.9, timestamp=200.0))
        shared = g.share("agent_1", {"task_type": "general"})
        g.receive("agent_2", shared)
        assert g.message_count > 0
