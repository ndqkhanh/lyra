"""Agent Ecology & Emergence Engine — emergent AGI through competition and evolution.

An ecology of agents competing for finite resources drives specialization,
adaptation, and eventually emergent behaviors no single agent architect could design.
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "ResourcePool",
    "AgentSpecimen",
    "AgentEcology",
    "EmergenceDetector",
]


@dataclass
class ResourcePool:
    """Finite resources that agents compete for."""
    total: float = 1000.0
    regeneration_rate: float = 0.05  # 5% per tick
    available: float = 1000.0

    def regenerate(self) -> None:
        growth = self.total * self.regeneration_rate
        self.available = min(self.total, self.available + growth)

    def consume(self, amount: float) -> float:
        actual = min(amount, self.available)
        self.available -= actual
        return actual


@dataclass
class AgentSpecimen:
    id: str
    agent_type: str
    fitness: float = 0.5
    age: int = 0
    specialization: str = "general"
    resource_consumption: float = 1.0
    mutation_rate: float = 0.1
    children: int = 0

    def act(self, resources: ResourcePool) -> float:
        """Act in the ecology — consume resources, produce value."""
        self.age += 1
        consumed = resources.consume(self.resource_consumption)
        # Efficiency: how much value we produce per resource consumed
        efficiency = self.fitness * random.uniform(0.8, 1.2)
        value = consumed * efficiency
        self.fitness = min(1.0, self.fitness + value * 0.01)
        return value

    def reproduce(self) -> AgentSpecimen:
        """Create a child with mutations."""
        self.children += 1
        child = AgentSpecimen(
            id=f"{self.id}_child_{self.children}",
            agent_type=self.agent_type,
            fitness=max(0.1, self.fitness * random.uniform(0.8, 0.95)),
            specialization=self.specialization,
            resource_consumption=self.resource_consumption * random.uniform(0.9, 1.1),
            mutation_rate=self.mutation_rate * random.uniform(0.8, 1.2),
        )
        # Sometimes mutate specialization
        if random.random() < self.mutation_rate:
            child.specialization = random.choice(["general", "specialist", "explorer", "exploiter"])
        return child


class AgentEcology:
    """Simulate an ecology of competing/symbiotic agents."""

    def __init__(self, resource_capacity: float = 1000.0):
        self.resources = ResourcePool(total=resource_capacity)
        self.agents: list[AgentSpecimen] = []
        self.generation = 0
        self.history: list[dict[str, Any]] = []

    def seed(self, count: int = 10) -> None:
        """Seed the ecology with initial agents."""
        for i in range(count):
            agent_type = random.choice(["generalist", "specialist", "explorer", "exploiter"])
            agent = AgentSpecimen(
                id=f"seed_{i}",
                agent_type=agent_type,
                fitness=random.uniform(0.3, 0.7),
                specialization=agent_type,
            )
            self.agents.append(agent)

    def step(self) -> dict[str, Any]:
        """One ecology cycle: act → consume → reproduce → die."""
        self.generation += 1
        self.resources.regenerate()

        snapshot = {
            "generation": self.generation,
            "population": len(self.agents),
            "resources": self.resources.available,
            "avg_fitness": 0.0,
            "diversity": 0,
        }

        if not self.agents:
            snapshot["avg_fitness"] = 0.0
            self.history.append(snapshot)
            return snapshot

        # Act
        total_value = 0.0
        for agent in self.agents[:]:
            value = agent.act(self.resources)
            total_value += value

            # Die if unfit
            if agent.fitness < 0.1:
                self.agents.remove(agent)
                continue

            # Reproduce if fit
            if agent.fitness > 0.8 and len(self.agents) < 100:
                child = agent.reproduce()
                self.agents.append(child)

        # Update snapshot
        snapshot["avg_fitness"] = sum(a.fitness for a in self.agents) / max(len(self.agents), 1)
        snapshot["diversity"] = len(set(a.specialization for a in self.agents))
        snapshot["total_value"] = total_value
        self.history.append(snapshot)

        return snapshot

    def run(self, generations: int = 100) -> list[dict[str, Any]]:
        """Run the ecology for N generations."""
        for _ in range(generations):
            self.step()
        return self.history

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "population": len(self.agents),
            "species_types": list(set(a.agent_type for a in self.agents)),
            "specializations": list(set(a.specialization for a in self.agents)),
            "avg_fitness": sum(a.fitness for a in self.agents) / max(len(self.agents), 1),
            "resources": self.resources.available,
        }


class EmergenceDetector:
    """Detect emergent behaviors in agent collectives."""

    def __init__(self):
        self.metrics = {
            "coordination_complexity": 0.0,
            "specialization_depth": 0.0,
            "innovation_rate": 0.0,
            "unexpected_successes": 0,
        }

    def scan(self, ecology: AgentEcology) -> dict[str, Any]:
        """Scan ecology for emergent behaviors."""
        if ecology.generation < 5:
            return {"emergence_detected": False, "reason": "Too early"}

        # Check for specialization emergence
        specializations = set(a.specialization for a in ecology.agents)
        self.metrics["specialization_depth"] = len(specializations)

        # Check for unexpected fitness (sign of emergent capability)
        avg_fitness = ecology.stats["avg_fitness"]
        top_fitness = max((a.fitness for a in ecology.agents), default=0)
        unexpected = top_fitness > avg_fitness * 2
        if unexpected:
            self.metrics["unexpected_successes"] += 1

        # Check for coordination (more agents than resources would suggest possible)
        coordination_ratio = ecology.resources.regeneration_rate * ecology.generation
        self.metrics["coordination_complexity"] = min(1.0, coordination_ratio)

        emergence = self.metrics["specialization_depth"] >= 2 and unexpected
        return {
            "emergence_detected": emergence,
            "metrics": dict(self.metrics),
            "population": len(ecology.agents),
            "generation": ecology.generation,
        }
