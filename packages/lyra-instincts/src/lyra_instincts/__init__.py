"""Instincts Layer — pre-wired behavioral patterns between raw skills and the agent loop.

ECC's instinct-cli.py (72KB, most-used feature) proves instincts are critical.
Project-scoped + global instincts. TTL-based pruning. Evolution into skills/commands.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "InstinctScope",
    "Instinct",
    "InstinctEngine",
    "EvolutionResult",
]


class InstinctScope(Enum):
    PROJECT = auto()
    GLOBAL = auto()


@dataclass
class Instinct:
    id: str
    trigger: str
    pattern: str
    scope: InstinctScope = InstinctScope.PROJECT
    ttl_days: int = 30
    created_at: float = 0.0
    promoted_from: str | None = None
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.scope == InstinctScope.GLOBAL:
            return False
        age_seconds = time.time() - self.created_at
        return age_seconds > self.ttl_days * 86400


@dataclass
class EvolutionResult:
    skills: list[str]
    commands: list[str]
    agents: list[str]


class InstinctEngine:
    """Collects, evolves, prunes, and promotes instincts."""

    def __init__(self):
        self._project_instincts: dict[str, Instinct] = {}
        self._global_instincts: dict[str, Instinct] = {}
        self._counter = 0

    # ── Collection ────────────────────────────────────────────

    def collect(self, trigger: str, pattern: str) -> Instinct:
        """Extract instinct from an agent execution trace."""
        self._counter += 1
        instinct = Instinct(
            id=f"instinct_{self._counter}",
            trigger=trigger,
            pattern=pattern,
            created_at=time.time(),
        )
        self._project_instincts[instinct.id] = instinct
        logger.info(f"Collected instinct {instinct.id}: {trigger}")
        return instinct

    # ── Evolution ────────────────────────────────────────────

    def evolve(self, instincts: list[Instinct] | None = None) -> EvolutionResult:
        """Cluster raw instincts into structured skills/commands/agents."""
        targets = instincts or list(self._project_instincts.values())
        skills = []
        commands = []
        agents = []

        for inst in targets:
            if inst.hit_count >= 10:
                skills.append(f"skill_from_{inst.id}")
            elif inst.hit_count >= 5:
                commands.append(f"cmd_from_{inst.id}")
            if inst.hit_count >= 20:
                agents.append(f"agent_from_{inst.id}")

        return EvolutionResult(skills=skills, commands=commands, agents=agents)

    # ── Pruning ──────────────────────────────────────────────

    def prune(self) -> int:
        """Delete expired pending instincts. Returns count removed."""
        expired = [
            iid for iid, inst in self._project_instincts.items()
            if inst.is_expired
        ]
        for iid in expired:
            del self._project_instincts[iid]
        if expired:
            logger.info(f"Pruned {len(expired)} expired instincts")
        return len(expired)

    # ── Promotion ────────────────────────────────────────────

    def promote(self, instinct_id: str) -> Instinct | None:
        """Promote project instinct to global scope."""
        if instinct_id not in self._project_instincts:
            return None
        inst = self._project_instincts[instinct_id]
        promoted = Instinct(
            id=f"global_{instinct_id}",
            trigger=inst.trigger,
            pattern=inst.pattern,
            scope=InstinctScope.GLOBAL,
            created_at=time.time(),
            promoted_from=instinct_id,
            hit_count=inst.hit_count,
        )
        self._global_instincts[promoted.id] = promoted
        return promoted

    # ── Status ───────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "project_instincts": len(self._project_instincts),
            "global_instincts": len(self._global_instincts),
            "total": len(self._project_instincts) + len(self._global_instincts),
        }
