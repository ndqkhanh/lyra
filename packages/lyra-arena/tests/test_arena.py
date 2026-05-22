
import asyncio
from lyra_arena import AgentArena
class TestAgentArena:
    def test_register_and_match(self):
        a = AgentArena(); a.register("agent_A"); a.register("agent_B")
        m = asyncio.run(a.run_match("agent_A", "agent_B"))
        assert m.winner in ["agent_A", "agent_B"]
    def test_ratings_update(self):
        a = AgentArena(); a.register("pro", 1500); a.register("novice", 1000)
        for _ in range(10): asyncio.run(a.run_match("pro", "novice"))
        assert a.ratings["pro"] > 1400
