"""Learning loop — closed feedback loop for continuous agent improvement.

Orchestrates the observe→extract→verify→integrate cycle:
1. Collect experience records from agent turns
2. Extract patterns when enough records accumulate
3. Evaluate patterns and distill skills
4. Register anti-patterns to prevent recurrence

Integrates with ``ExperienceExtractor``, ``AntiPatternRegistry``,
``SkillDistiller``, and the existing ``ReasoningBank``.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_core.events import EventBus, EventCategory
from lyra_core.experience.anti_pattern import AntiPattern, AntiPatternRegistry
from lyra_core.experience.extractor import (
    ExperienceExtractor,
    ExperienceRecord,
    PatternType,
)
from lyra_core.experience.skill_distiller import SkillDistiller


class LoopState(str, Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    EXTRACTING = "extracting"
    EVALUATING = "evaluating"
    INTEGRATING = "integrating"
    ERROR = "error"


@dataclass(frozen=True)
class LoopConfig:
    """Configuration for the learning loop."""

    min_records_before_extract: int = 10
    max_records_per_cycle: int = 100
    cycle_interval_seconds: float = 300.0
    auto_promote_threshold: float = 0.8
    require_approval_below: float = 0.6
    max_anti_patterns: int = 50
    prune_older_than_days: int = 30


@dataclass(frozen=True)
class ImprovementCycle:
    """Outcome of one learning loop cycle."""

    cycle_id: str
    state_before: LoopState
    state_after: LoopState
    records_processed: int
    patterns_extracted: int
    lessons_promoted: int
    skills_distilled: int
    anti_patterns_identified: int
    duration_ms: float
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class LearningLoop:
    """Continuous learning loop for agent improvement.

    Usage::

        loop = LearningLoop(extractor=ExperienceExtractor())
        await loop.start()
        await loop.submit_record(record)
        cycle = await loop.run_cycle()
    """

    config: LoopConfig = field(default_factory=LoopConfig)
    extractor: ExperienceExtractor | None = None
    anti_pattern_registry: AntiPatternRegistry | None = None
    skill_distiller: SkillDistiller | None = None
    bus: EventBus | None = None
    _state: LoopState = LoopState.IDLE
    _records: list[ExperienceRecord] = field(default_factory=list)
    _cycles: list[ImprovementCycle] = field(default_factory=list)
    _running: bool = False
    _last_cycle_at: float = 0.0

    async def start(self) -> None:
        self._running = True
        self._state = LoopState.COLLECTING
        self._publish("learning_loop.started", {"state": self._state.value})

    async def stop(self) -> None:
        self._running = False
        self._state = LoopState.IDLE
        self._publish("learning_loop.stopped", {})

    async def submit_record(self, record: ExperienceRecord) -> None:
        """Submit an experience record for learning."""
        self._records.append(record)
        self._publish("learning_loop.record_submitted", {
            "record_id": record.id,
            "outcome": record.outcome,
        })

    async def run_cycle(self) -> ImprovementCycle:
        """Run one complete learning cycle."""
        start = time.time()
        state_before = self._state

        if len(self._records) < self.config.min_records_before_extract:
            cycle = ImprovementCycle(
                cycle_id=uuid.uuid4().hex,
                state_before=state_before,
                state_after=self._state,
                records_processed=0,
                patterns_extracted=0,
                lessons_promoted=0,
                skills_distilled=0,
                anti_patterns_identified=0,
                duration_ms=(time.time() - start) * 1000,
                error="Insufficient records for extraction",
            )
            self._cycles.append(cycle)
            return cycle

        patterns_extracted = 0
        skills_distilled = 0
        anti_count = 0
        try:
            # Phase 1: Extract
            self._state = LoopState.EXTRACTING
            self._publish("learning_loop.cycle_started", {"state": self._state.value})

            batch = self._records[-self.config.max_records_per_cycle:]
            extractor = self.extractor or ExperienceExtractor()
            patterns = extractor.extract(batch)
            patterns_extracted = len(patterns)

            # Phase 2: Evaluate
            self._state = LoopState.EVALUATING
            if self.skill_distiller:
                candidates = self.skill_distiller.propose_candidates(patterns)
                result = self.skill_distiller.distill(candidates)
                skills_distilled = result.skills_distilled

            # Phase 3: Integrate
            self._state = LoopState.INTEGRATING
            if self.anti_pattern_registry:
                for pattern in patterns:
                    if pattern.pattern_type in (PatternType.FAILURE_MODE,
                                                PatternType.ANTI_PATTERN):
                        ap = AntiPattern(
                            id=uuid.uuid4().hex,
                            name=pattern.title[:80],
                            description=pattern.description,
                            severity="medium",
                            pattern_source="learning_loop",
                            detection_rule=pattern.title.lower(),
                            suggested_fix=pattern.suggested_action,
                            occurrence_count=1,
                            tags=pattern.tags,
                        )
                        self.anti_pattern_registry.register(ap)
                        anti_count += 1

            # Prune old records
            prune_before = time.time() - (self.config.prune_older_than_days * 86400)
            self._records = [r for r in self._records if r.created_at >= prune_before]

            self._last_cycle_at = time.time()
            self._state = LoopState.COLLECTING

            cycle = ImprovementCycle(
                cycle_id=uuid.uuid4().hex,
                state_before=state_before,
                state_after=self._state,
                records_processed=len(batch),
                patterns_extracted=patterns_extracted,
                lessons_promoted=0,
                skills_distilled=skills_distilled,
                anti_patterns_identified=anti_count,
                duration_ms=(time.time() - start) * 1000,
            )

        except Exception as exc:
            self._state = LoopState.ERROR
            cycle = ImprovementCycle(
                cycle_id=uuid.uuid4().hex,
                state_before=state_before,
                state_after=LoopState.ERROR,
                records_processed=0,
                patterns_extracted=0,
                lessons_promoted=0,
                skills_distilled=0,
                anti_patterns_identified=0,
                duration_ms=(time.time() - start) * 1000,
                error=str(exc),
            )

        self._cycles.append(cycle)
        self._publish("learning_loop.cycle_completed", {
            "cycle_id": cycle.cycle_id,
            "patterns_extracted": patterns_extracted,
            "skills_distilled": skills_distilled,
            "anti_patterns_identified": anti_count,
        })
        return cycle

    async def run_cycles(self, count: int = 1) -> tuple[ImprovementCycle, ...]:
        cycles: list[ImprovementCycle] = []
        for _ in range(count):
            cycle = await self.run_cycle()
            cycles.append(cycle)
        return tuple(cycles)

    def get_pending_records(self) -> tuple[ExperienceRecord, ...]:
        return tuple(self._records)

    def _publish(self, name: str, payload: dict[str, Any]) -> None:
        bus = self.bus or EventBus.get()
        bus.publish(
            category=EventCategory.TELEMETRY,
            name=name,
            origin="lyra_core.experience.learning_loop",
            payload=payload,
        )

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def cycle_history(self) -> tuple[ImprovementCycle, ...]:
        return tuple(self._cycles)

    @property
    def total_patterns_extracted(self) -> int:
        return sum(c.patterns_extracted for c in self._cycles)

    @property
    def is_running(self) -> bool:
        return self._running
