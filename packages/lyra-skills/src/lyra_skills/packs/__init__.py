"""Shipped skill packs. Roots resolved relative to this file."""
from __future__ import annotations

from pathlib import Path

_PACK_NAMES = ["atomic-skills", "tdd-sprint", "karpathy", "safety"]


def shipped_pack_roots() -> list[Path]:
    here = Path(__file__).parent
    return [here / name for name in _PACK_NAMES]
