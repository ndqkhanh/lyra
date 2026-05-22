"""Gossip Memory — Decentralized memory gossip protocol for multi-agent memory federation."""

from __future__ import annotations

import logging
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryItem",
    "DualPoolMemory",
    "GossipProtocol",
]




@dataclass
class MemoryItem:
    id: str
    content: str
    source_agent: str
    importance: float
    timestamp: float
    context_tags: list[str] = field(default_factory=list)


@dataclass
class DualPoolMemory:
    """Each agent has an exploit (consolidated) and explore (experimental) pool."""
    exploit_pool: deque[MemoryItem] = field(default_factory=lambda: deque(maxlen=100))
    explore_pool: deque[MemoryItem] = field(default_factory=lambda: deque(maxlen=50))

    def add_exploit(self, item: MemoryItem) -> None:
        self.exploit_pool.append(item)

    def add_explore(self, item: MemoryItem) -> None:
        self.explore_pool.append(item)

    def promote_to_exploit(self, item_id: str) -> bool:
        for i, item in enumerate(self.explore_pool):
            if item.id == item_id:
                self.exploit_pool.append(item)
                self.explore_pool.remove(item)
                return True
        return False

    def query(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        results = []
        for pool in [self.exploit_pool, self.explore_pool]:
            scored = []
            for item in pool:
                score = sum(1 for tag in item.context_tags if tag in query.lower()) + item.importance
                scored.append((score, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            results.extend(item for _, item in scored[:top_k])
        return results[:top_k]


class GossipProtocol:
    """Peer-to-peer memory synchronization protocol."""

    def __init__(self):
        self.agent_memories: dict[str, DualPoolMemory] = {}
        self.message_count: int = 0
        self.peers: set[str] = set()

    def register_agent(self, agent_id: str) -> DualPoolMemory:
        if agent_id not in self.agent_memories:
            self.agent_memories[agent_id] = DualPoolMemory()
        return self.agent_memories[agent_id]

    def register_peer(self, peer_id: str) -> None:
        self.peers.add(peer_id)

    def share(self, agent_id: str, context: dict[str, Any]) -> list[MemoryItem]:
        memory = self.agent_memories.get(agent_id)
        if not memory:
            return []

        candidates = memory.exploit_pool
        if not candidates:
            return []

        shared = random.sample(list(candidates), min(3, len(candidates)))
        self.message_count += 1
        return shared

    def receive(self, agent_id: str, items: list[MemoryItem]) -> None:
        memory = self.register_agent(agent_id)
        for item in items:
            memory.add_explore(item)
