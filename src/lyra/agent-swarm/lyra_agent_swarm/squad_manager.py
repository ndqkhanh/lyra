"""Agent group (squad) management under a designated leader for domain-specific work."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto

from lyra.agent_swarm.exceptions import SquadError


class SquadDomain(Enum):
    """Domain focus of a squad."""

    BACKEND = auto()
    FRONTEND = auto()
    DEVOPS = auto()
    DATA = auto()
    SECURITY = auto()
    RESEARCH = auto()
    GENERAL = auto()


@dataclass(frozen=True)
class SquadMetrics:
    """Performance data for a squad."""

    tasks_completed: int = 0
    avg_completion_time: float = 0.0
    success_rate: float = 1.0


@dataclass(frozen=True)
class Squad:
    """Immutable definition of an agent squad."""

    squad_id: str
    name: str
    leader: str
    members: tuple[str, ...]
    domain: SquadDomain
    active_sprint: str | None = None
    metrics: SquadMetrics = field(default_factory=SquadMetrics)
    created_at: float = field(default_factory=time.time)


class SquadManager:
    """Creates, assigns, and rebalances agent squads."""

    def __init__(self) -> None:
        self._squads: dict[str, Squad] = {}

    @property
    def squads(self) -> dict[str, Squad]:
        return dict(self._squads)

    def create_squad(
        self,
        leader: str,
        members: list[str],
        domain: SquadDomain,
        name: str | None = None,
    ) -> Squad:
        if leader in members:
            raise SquadError("Leader must not be in members list")
        if not members:
            raise SquadError("Squad must have at least one member")
        squad_id = f"squad-{int(time.time())}"
        squad = Squad(
            squad_id=squad_id,
            name=name or f"Squad-{domain.name.lower()}-{len(self._squads) + 1}",
            leader=leader,
            members=tuple(members),
            domain=domain,
        )
        self._squads[squad_id] = squad
        return squad

    def get_squad(self, squad_id: str) -> Squad | None:
        return self._squads.get(squad_id)

    def assign_task(self, squad: Squad, task_id: str) -> Squad:
        updated = Squad(
            squad_id=squad.squad_id,
            name=squad.name,
            leader=squad.leader,
            members=squad.members,
            domain=squad.domain,
            active_sprint=task_id,
            metrics=squad.metrics,
            created_at=squad.created_at,
        )
        self._squads[squad.squad_id] = updated
        return updated

    def rebalance_squads(self) -> list[Squad]:
        """Redistribute squad composition based on current load (trivial round-robin for now)."""
        if len(self._squads) < 2:
            return list(self._squads.values())

        all_members: list[str] = []
        leader_map: dict[str, str] = {}
        for squad in self._squads.values():
            all_members.append(squad.leader)
            leader_map[squad.leader] = squad.squad_id
            all_members.extend(squad.members)

        # Group agents by squad domain
        domains: dict[SquadDomain, list[str]] = {}
        for squad in self._squads.values():
            if squad.domain not in domains:
                domains[squad.domain] = []
            domains[squad.domain].append(squad.leader)
            domains[squad.domain].extend(squad.members)

        # Rebuild squads with balanced membership
        new_squads: list[Squad] = []
        for squad in self._squads.values():
            domain_members = domains.get(squad.domain, [])
            if len(domain_members) > 1:
                new_members: list[str] = []
                for m in domain_members:
                    if m != squad.leader and len(new_members) < 3:
                        new_members.append(m)
                rebalanced = Squad(
                    squad_id=squad.squad_id,
                    name=squad.name,
                    leader=squad.leader,
                    members=tuple(new_members),
                    domain=squad.domain,
                    active_sprint=squad.active_sprint,
                    metrics=squad.metrics,
                    created_at=squad.created_at,
                )
                new_squads.append(rebalanced)
            else:
                new_squads.append(squad)

        # Update internal state
        self._squads = {s.squad_id: s for s in new_squads}
        return new_squads

    def record_completion(self, squad: Squad, success: bool, duration: float) -> Squad:
        old = squad.metrics
        new_tasks = old.tasks_completed + 1
        new_rate = (
            (old.success_rate * old.tasks_completed) + (1.0 if success else 0.0)
        ) / new_tasks
        new_avg = ((old.avg_completion_time * old.tasks_completed) + duration) / new_tasks
        updated = Squad(
            squad_id=squad.squad_id,
            name=squad.name,
            leader=squad.leader,
            members=squad.members,
            domain=squad.domain,
            active_sprint=None,
            metrics=SquadMetrics(
                tasks_completed=new_tasks,
                avg_completion_time=new_avg,
                success_rate=new_rate,
            ),
            created_at=squad.created_at,
        )
        self._squads[squad.squad_id] = updated
        return updated

    def remove_squad(self, squad_id: str) -> None:
        if squad_id not in self._squads:
            raise SquadError(f"Squad '{squad_id}' not found")
        del self._squads[squad_id]
