"""Lineage tracker — tracks evolutionary lineage and ancestry of strategies.

Maintains the family tree of evolved strategies, recording parent-child
relationships, mutation events, and generational progression.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class EventType(StrEnum):
    BIRTH = "birth"
    MUTATION = "mutation"
    CROSSOVER = "crossover"
    SELECTION = "selection"
    EXTINCTION = "extinction"
    PROMOTION = "promotion"


@dataclass(frozen=True)
class EvolutionEvent:
    event_id: str
    event_type: EventType
    strategy_id: str
    generation: int
    parent_ids: list[str]
    fitness: float
    metadata: dict[str, str]
    timestamp: float


@dataclass(frozen=True)
class LineageTree:
    root_id: str
    generation_count: int
    total_strategies: int
    active_strategies: int
    avg_fitness: float
    max_fitness: float


class LineageTracker:
    """Tracks the evolutionary lineage of agent strategies.

    Records every evolutionary event (birth, mutation, crossover,
    selection, extinction, promotion) and can reconstruct the
    full ancestry tree for any strategy.
    """

    def __init__(self) -> None:
        self._events: list[EvolutionEvent] = []
        self._children: dict[str, list[str]] = {}
        self._counter = 0

    def record_birth(
        self,
        strategy_id: str,
        generation: int,
        parent_ids: list[str] | None = None,
    ) -> EvolutionEvent:
        return self._record(
            EventType.BIRTH, strategy_id, generation, 0.0, parent_ids or []
        )

    def record_mutation(
        self, strategy_id: str, generation: int, parent_id: str
    ) -> EvolutionEvent:
        return self._record(
            EventType.MUTATION, strategy_id, generation, 0.0, [parent_id]
        )

    def record_crossover(
        self,
        strategy_id: str,
        generation: int,
        parent_ids: list[str],
    ) -> EvolutionEvent:
        return self._record(
            EventType.CROSSOVER, strategy_id, generation, 0.0, parent_ids
        )

    def record_selection(
        self, strategy_id: str, generation: int, fitness: float
    ) -> EvolutionEvent:
        return self._record(
            EventType.SELECTION, strategy_id, generation, fitness, []
        )

    def record_extinction(self, strategy_id: str, generation: int) -> EvolutionEvent:
        return self._record(
            EventType.EXTINCTION, strategy_id, generation, 0.0, []
        )

    def record_promotion(
        self, strategy_id: str, generation: int, fitness: float
    ) -> EvolutionEvent:
        return self._record(
            EventType.PROMOTION, strategy_id, generation, fitness, []
        )

    def _record(
        self,
        event_type: EventType,
        strategy_id: str,
        generation: int,
        fitness: float,
        parent_ids: list[str],
    ) -> EvolutionEvent:
        self._counter += 1
        event = EvolutionEvent(
            event_id=f"evt-{self._counter:06d}",
            event_type=event_type,
            strategy_id=strategy_id,
            generation=generation,
            parent_ids=parent_ids,
            fitness=fitness,
            metadata={},
            timestamp=time.time(),
        )
        self._events.append(event)
        for pid in parent_ids:
            self._children.setdefault(pid, []).append(strategy_id)
        return event

    def get_ancestry(self, strategy_id: str) -> list[str]:
        ancestors: list[str] = []
        current = strategy_id
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            for event in reversed(self._events):
                if event.strategy_id == current and event.parent_ids:
                    ancestors.extend(event.parent_ids)
                    current = event.parent_ids[0]
                    break
            else:
                break

        return list(dict.fromkeys(ancestors))

    def get_children(self, strategy_id: str) -> list[str]:
        return self._children.get(strategy_id, [])

    def get_lineage_tree(self, root_id: str) -> LineageTree:
        generation_ids = {0: {root_id}}
        current_gen = [root_id]
        gen = 0

        while current_gen:
            next_gen = []
            for sid in current_gen:
                next_gen.extend(self.get_children(sid))
            if next_gen:
                gen += 1
                generation_ids[gen] = set(next_gen)
                current_gen = next_gen
            else:
                break

        all_ids = {sid for ids in generation_ids.values() for sid in ids}
        fitnesses = [
            e.fitness for e in self._events
            if e.strategy_id in all_ids and e.fitness > 0
        ]

        return LineageTree(
            root_id=root_id,
            generation_count=gen + 1,
            total_strategies=len(all_ids),
            active_strategies=sum(
                1 for sid in all_ids
                if not any(
                    e.event_type == EventType.EXTINCTION and e.strategy_id == sid
                    for e in self._events
                )
            ),
            avg_fitness=round(sum(fitnesses) / max(len(fitnesses), 1), 4),
            max_fitness=round(max(fitnesses) if fitnesses else 0.0, 4),
        )

    def stats(self) -> dict:
        return {
            "total_events": len(self._events),
            "by_type": {
                t.value: sum(1 for e in self._events if e.event_type == t)
                for t in EventType
            },
            "unique_strategies": len({e.strategy_id for e in self._events}),
        }
