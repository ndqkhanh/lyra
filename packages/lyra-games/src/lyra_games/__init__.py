"""Gaming/NPC Agent — autonomous game characters, procedural storytelling, game testing.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["NPCCharacter", "GameAgent"]

@dataclass
class NPCCharacter:
    name: str
    personality: str = "neutral"
    dialogue_trees: dict[str, list[str]] = field(default_factory=dict)

class GameAgent:
    def __init__(self):
        self.npcs: dict[str, NPCCharacter] = {}

    def create_npc(self, name: str, personality: str = "neutral") -> NPCCharacter:
        npc = NPCCharacter(name=name, personality=personality)
        self.npcs[name] = npc
        return npc

    def add_dialogue(self, npc_name: str, trigger: str, responses: list[str]) -> bool:
        npc = self.npcs.get(npc_name)
        if not npc: return False
        npc.dialogue_trees[trigger] = responses
        return True

    def get_response(self, npc_name: str, trigger: str) -> Optional[str]:
        npc = self.npcs.get(npc_name)
        if not npc or trigger not in npc.dialogue_trees: return None
        return npc.dialogue_trees[trigger][0]

    @property
    def stats(self) -> dict[str, Any]:
        return {"npcs": len(self.npcs), "total_dialogues": sum(len(d) for n in self.npcs.values() for d in n.dialogue_trees.values())}
