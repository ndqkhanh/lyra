"""Tests for lyra-games."""
from lyra_games import GameAgent

class TestGameAgent:
    def test_create_npc(self):
        g = GameAgent()
        npc = g.create_npc("Merchant", "friendly")
        assert npc.name == "Merchant"

    def test_dialogue(self):
        g = GameAgent()
        g.create_npc("Guard", "stern")
        g.add_dialogue("Guard", "greeting", ["Halt!", "Who goes there?"])
        response = g.get_response("Guard", "greeting")
        assert response == "Halt!"
