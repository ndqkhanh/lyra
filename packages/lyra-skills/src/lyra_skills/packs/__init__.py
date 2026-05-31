"""Shipped skill packs. Roots resolved relative to this file."""
from __future__ import annotations

from pathlib import Path

_PACK_NAMES = [
    "ai-research",
    "atomic-skills",
    "ba",
    "brainstorming",
    "cloud-engineering",
    "data",
    "debugging",
    "design",
    "devops",
    "documentation",
    "engineering",
    "general",
    "karpathy",
    "migration",
    "optimization",
    "pm",
    "refactoring",
    "safety",
    "security",
    "solution-architecture",
    "sre",
    "tdd-sprint",
    "testing",
]


def shipped_pack_roots() -> list[Path]:
    here = Path(__file__).parent
    return [here / name for name in _PACK_NAMES]
