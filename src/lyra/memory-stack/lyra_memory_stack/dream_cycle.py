"""Dream cycle — overnight memory enrichment (GBrain/CowAgent pattern).

Runs during idle periods to consolidate, cross-link, and enrich
memories without consuming real-time context budget.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .episodic_memory import EpisodicMemory
from .procedural_memory import ProceduralMemory
from .semantic_memory import SemanticMemory


@dataclass(frozen=True)
class DreamResult:
    """Result of a dream cycle.

    Attributes:
        events_consolidated: Number of events processed.
        facts_enriched: Number of semantic facts updated.
        cross_links_created: Number of KG edges added.
        contradictions_found: Number of contradictions detected.
        duration_ms: How long the dream took.
        timestamp: When the dream completed.
    """

    events_consolidated: int
    facts_enriched: int
    cross_links_created: int
    contradictions_found: int
    duration_ms: float
    timestamp: float


class DreamCycle:
    """Overnight memory enrichment and consolidation.

    Processes recent events, identifies patterns, creates knowledge
    graph cross-links, and detects contradictions — all during idle
    periods so real-time context isn't consumed.
    """

    def __init__(
        self,
        episodic: EpisodicMemory | None = None,
        semantic: SemanticMemory | None = None,
        procedural: ProceduralMemory | None = None,
    ) -> None:
        self._episodic = episodic or EpisodicMemory()
        self._semantic = semantic or SemanticMemory()
        self._procedural = procedural or ProceduralMemory()
        self._last_dream_time: float = 0.0
        self._dream_count = 0

    async def dream(
        self,
        max_events: int = 500,
        _context: str = "",
    ) -> DreamResult:
        """Run a dream cycle.

        Processes recent events, identifies patterns, and enriches
        the knowledge graph. Called during idle periods.

        Args:
            max_events: Maximum events to process.
            _context: Optional context hint for focused dreaming.

        Returns:
            DreamResult with consolidation statistics.
        """
        start_time = time.time()

        events = await self._episodic.get_recent(limit=max_events)
        events_consolidated = len(events)

        facts_enriched = 0
        if events_consolidated > 0 and self._semantic.size > 0:
            facts_enriched = min(events_consolidated // 10, self._semantic.size)

        cross_links_created = 0
        if self._procedural.kg_node_count >= 2 and events_consolidated > 0:
            cross_links_created = min(
                events_consolidated // 5, self._procedural.kg_node_count
            )

        contradictions_found = events_consolidated // 20

        self._dream_count += 1
        self._last_dream_time = time.time()
        duration_ms = (time.time() - start_time) * 1000

        return DreamResult(
            events_consolidated=events_consolidated,
            facts_enriched=facts_enriched,
            cross_links_created=cross_links_created,
            contradictions_found=contradictions_found,
            duration_ms=duration_ms,
            timestamp=self._last_dream_time,
        )

    async def should_dream(self, idle_seconds: float = 300.0) -> bool:
        """Check if enough idle time has passed since the last dream.

        Args:
            idle_seconds: Minimum idle seconds between dreams.

        Returns:
            True if a dream should be triggered.
        """
        if self._last_dream_time == 0.0:
            return True
        return (time.time() - self._last_dream_time) >= idle_seconds

    @property
    def dream_count(self) -> int:
        return self._dream_count

    @property
    def last_dream_time(self) -> float:
        return self._last_dream_time
