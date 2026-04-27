"""Progressive-disclosure surface over memory tiers.

These three functions are what the CLI (and later the MCP server) expose so
an agent can see only the relevant slice of memory at a time:

    - ``list_topics`` — all known topic ids + names
    - ``get_topic``   — full record for one topic
    - ``search_topic`` — full-text match across topics

They delegate to the underlying memory backend (e.g.
``lyra_core.memory.procedural.ProceduralMemory``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .procedural import SkillRecord


class _MemoryBackend(Protocol):
    def all(self) -> list[SkillRecord]: ...
    def get(self, skill_id: str) -> SkillRecord | None: ...
    def search(self, query: str, *, max_tokens: int = ...) -> list[SkillRecord]: ...


@dataclass
class TopicRef:
    id: str
    name: str


def list_topics(mem: _MemoryBackend) -> list[TopicRef]:
    return [TopicRef(id=r.id, name=r.name) for r in mem.all()]


def get_topic(mem: _MemoryBackend, topic_id: str) -> SkillRecord | None:
    return mem.get(topic_id)


def search_topic(
    mem: _MemoryBackend, query: str, *, max_tokens: int = 2000
) -> list[SkillRecord]:
    return mem.search(query, max_tokens=max_tokens)
