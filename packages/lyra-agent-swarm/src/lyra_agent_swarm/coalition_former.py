"""Shapley value-based coalition formation for optimal agent team assembly."""

from __future__ import annotations

import itertools
import math
import time
from dataclasses import dataclass, field

from lyra_agent_swarm.discipline_agents import Capability, DisciplineAgent
from lyra_agent_swarm.dispatcher import TaskTicket
from lyra_agent_swarm.exceptions import CoalitionError


@dataclass(frozen=True)
class AgentContribution:
    """Shapley-value based contribution measurement of a single agent in a coalition."""

    agent_id: str
    marginal_contribution: float
    shapley_value: float


@dataclass(frozen=True)
class Coalition:
    """A team of agents formed for a specific task with computed Shapley values."""

    coalition_id: str
    agents: tuple[DisciplineAgent, ...]
    task: TaskTicket
    shapley_values: tuple[AgentContribution, ...]
    formed_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class CoalitionConfig:
    """Configuration governing coalition formation behaviour."""

    max_coalition_size: int = 5
    min_shapley_threshold: float = 0.01


class CoalitionFormer:
    """Forms optimal agent teams using Shapley value computation and evaluates outcomes."""

    def __init__(self, config: CoalitionConfig | None = None) -> None:
        self._config = config or CoalitionConfig()

    @property
    def config(self) -> CoalitionConfig:
        return self._config

    def form_coalition(
        self,
        task: TaskTicket,
        available_agents: list[DisciplineAgent],
    ) -> Coalition:
        """Select the best subset of agents and compute their Shapley values."""
        if not available_agents:
            raise CoalitionError("No available agents for coalition formation")

        contributions = self.compute_shapley_values(available_agents, task)

        # Filter agents below the threshold
        filtered = [
            (c, a)
            for c, a in zip(contributions, available_agents)
            if c.shapley_value >= self._config.min_shapley_threshold
        ]

        if not filtered:
            raise CoalitionError(
                f"No agents meet the minimum Shapley threshold "
                f"({self._config.min_shapley_threshold}) for task '{task.task_id}'"
            )

        filtered.sort(key=lambda x: -x[0].shapley_value)

        max_size = min(self._config.max_coalition_size, len(filtered))
        selected_agents = tuple(a for _, a in filtered[:max_size])
        selected_contributions = tuple(c for c, _ in filtered[:max_size])

        coalition_id = f"coalition-{int(time.time())}"

        return Coalition(
            coalition_id=coalition_id,
            agents=selected_agents,
            task=task,
            shapley_values=selected_contributions,
        )

    def compute_shapley_values(
        self,
        agents: list[DisciplineAgent],
        task: TaskTicket,
    ) -> list[AgentContribution]:
        """Compute Shapley values for all agents given a task's capability requirements."""
        n = len(agents)
        required_caps: set[Capability] = set(task.required_capabilities)

        def coalition_value(subset: list[DisciplineAgent]) -> float:
            covered: set[Capability] = set()
            for a in subset:
                covered.update(a.capabilities)
            return float(len(covered & required_caps))

        contributions: list[AgentContribution] = []
        agent_ids = [a.agent_id for a in agents]

        for i, agent in enumerate(agents):
            shapley_sum = 0.0
            other_indices = [j for j in range(n) if j != i]

            for k in range(n):
                for subset in itertools.combinations(other_indices, k):
                    subset_agents = [agents[j] for j in subset]
                    v_without = coalition_value(subset_agents)
                    v_with = coalition_value(subset_agents + [agent])
                    marginal = v_with - v_without
                    weight = (math.factorial(k) * math.factorial(n - k - 1)) / math.factorial(n)
                    shapley_sum += marginal * weight

            contributions.append(AgentContribution(
                agent_id=agent_ids[i],
                marginal_contribution=shapley_sum,
                shapley_value=shapley_sum,
            ))

        total = sum(c.shapley_value for c in contributions)
        if total > 0:
            contributions = [
                AgentContribution(
                    agent_id=c.agent_id,
                    marginal_contribution=c.marginal_contribution,
                    shapley_value=c.shapley_value / total,
                )
                for c in contributions
            ]

        return contributions

    def evaluate_coalition(self, coalition: Coalition, outcome: float) -> float:
        """Score how well a coalition performed given an outcome reward (higher is better)."""
        if not coalition.shapley_values:
            return 0.0
        # Reward proportional to how well Shapley values predicted contribution
        predicted = sum(c.shapley_value for c in coalition.shapley_values)
        if predicted == 0:
            return 0.0
        return outcome / predicted
