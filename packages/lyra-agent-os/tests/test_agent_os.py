"""Tests for lyra-agent-os."""
from lyra_agent_os import AgentOS
class TestAgentOS:
    def test_spawn(self):
        os = AgentOS(); p = os.spawn("test_agent", 64)
        assert p is not None
    def test_spawn_oom(self):
        os = AgentOS(total_memory_mb=64); p = os.spawn("big_agent", 128)
        assert p is None
    def test_kill(self):
        os = AgentOS(); p = os.spawn("agent", 64)
        assert os.kill(p.pid)
