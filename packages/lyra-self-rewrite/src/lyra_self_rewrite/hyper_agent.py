"""DGM (Differentiable Goal Model) HyperAgent core — genome, population, and evolution engine."""

from __future__ import annotations

import math
import secrets
from dataclasses import dataclass

from .exceptions import HyperAgentError


@dataclass(frozen=True)
class HyperAgentConfig:
    """Configuration governing HyperAgent evolution behaviour."""

    max_depth: int = 5
    population_size: int = 20
    mutation_rate: float = 0.15
    crossover_rate: float = 0.3
    elitism_count: int = 2


@dataclass(frozen=True)
class AgentGene:
    """A single gene in a HyperAgent genome representing a trait."""

    gene_id: str
    trait: str
    value: float
    min_bound: float
    max_bound: float


@dataclass(frozen=True)
class HyperAgent:
    """An individual agent in the DGM population with a genome and fitness."""

    agent_id: str
    genome: tuple[AgentGene, ...]
    fitness: float
    generation: int
    lineage: tuple[str, ...]


@dataclass(frozen=True)
class Population:
    """A snapshot of a generation in the evolutionary process."""

    agents: tuple[HyperAgent, ...]
    generation: int
    best_fitness: float
    avg_fitness: float
    diversity: float


def _random_gene(gene_id: str, trait: str) -> AgentGene:
    """Create a gene with a random value within [0.0, 1.0]."""
    return AgentGene(
        gene_id=gene_id,
        trait=trait,
        value=secrets.SystemRandom().random(),
        min_bound=0.0,
        max_bound=1.0,
    )


_DEFAULT_TRAITS: tuple[str, ...] = (
    "exploration",
    "exploitation",
    "creativity",
    "conservatism",
    "speed",
    "thoroughness",
)


def _generate_agent(
    agent_id: str,
    generation: int,
    lineage: tuple[str, ...],
    traits: tuple[str, ...] = _DEFAULT_TRAITS,
) -> HyperAgent:
    """Generate a single HyperAgent with random genome."""
    genes: list[AgentGene] = []
    for i, trait in enumerate(traits):
        genes.append(_random_gene(f"g-{agent_id}-{i}", trait))
    return HyperAgent(
        agent_id=agent_id,
        genome=tuple(genes),
        fitness=0.0,
        generation=generation,
        lineage=lineage,
    )


class HyperAgentEngine:
    """Manages population initialization, fitness evaluation, and evolution."""

    def __init__(self) -> None:
        self._random = secrets.SystemRandom()

    async def initialize_population(
        self, config: HyperAgentConfig
    ) -> Population:
        """Create an initial random population from config."""
        agents: list[HyperAgent] = []
        for i in range(config.population_size):
            agent_id = f"agent-{config.max_depth}-{i}"
            agent = _generate_agent(
                agent_id=agent_id,
                generation=0,
                lineage=(agent_id,),
            )
            agents.append(agent)

        pop = Population(
            agents=tuple(agents),
            generation=0,
            best_fitness=0.0,
            avg_fitness=0.0,
            diversity=_compute_diversity(tuple(agents)),
        )
        return pop

    async def evaluate_fitness(
        self, agent: HyperAgent, task: str
    ) -> float:
        """Evaluate a single agent on a task, returning a fitness score.

        Uses a simple heuristic based on gene values — real implementations
        would call an actual evaluation harness or LLM.
        """
        if not agent.genome:
            return 0.0

        task_hash = sum(ord(c) for c in task)
        score = 0.0
        for gene in agent.genome:
            contribution = gene.value * math.sin(task_hash * (hash(gene.gene_id) % 100) * 0.01)
            score += abs(contribution)
        return score / len(agent.genome)

    async def evolve_population(
        self, pop: Population, config: HyperAgentConfig
    ) -> Population:
        """Produce the next generation through selection, crossover and mutation."""
        if not pop.agents:
            raise HyperAgentError("Cannot evolve an empty population")

        agents = list(pop.agents)
        agents.sort(key=lambda a: a.fitness, reverse=True)

        next_gen: list[HyperAgent] = []
        generation = pop.generation + 1

        # Elitism: carry over top performers unchanged
        elite_count = min(config.elitism_count, len(agents))
        for elite in agents[:elite_count]:
            next_gen.append(HyperAgent(
                agent_id=elite.agent_id,
                genome=elite.genome,
                fitness=elite.fitness,
                generation=generation,
                lineage=elite.lineage + (elite.agent_id,),
            ))

        # Create offspring until population is full
        while len(next_gen) < config.population_size:
            parent_a = agents[self._random.randint(0, len(agents) - 1)]
            parent_b = agents[self._random.randint(0, len(agents) - 1)]

            if self._random.random() < config.crossover_rate:
                child_genome = self._crossover(parent_a.genome, parent_b.genome)
            else:
                child_genome = parent_a.genome

            child_genome = self._mutate(child_genome, config.mutation_rate)

            child_id = f"agent-{generation}-{len(next_gen)}"
            child = HyperAgent(
                agent_id=child_id,
                genome=child_genome,
                fitness=0.0,
                generation=generation,
                lineage=parent_a.lineage + (child_id,),
            )
            next_gen.append(child)

        next_pop_agents = tuple(next_gen[: config.population_size])
        pop_avg = sum(a.fitness for a in next_pop_agents) / len(next_pop_agents)

        return Population(
            agents=next_pop_agents,
            generation=generation,
            best_fitness=next_pop_agents[0].fitness,
            avg_fitness=pop_avg,
            diversity=_compute_diversity(next_pop_agents),
        )

    async def select_elite(
        self, pop: Population, k: int
    ) -> tuple[HyperAgent, ...]:
        """Return the top-k agents by fitness."""
        sorted_agents = sorted(pop.agents, key=lambda a: a.fitness, reverse=True)
        return tuple(sorted_agents[:k])

    def _crossover(
        self,
        genome_a: tuple[AgentGene, ...],
        genome_b: tuple[AgentGene, ...],
    ) -> tuple[AgentGene, ...]:
        """Single-point crossover between two genomes."""
        if len(genome_a) < 2 or len(genome_b) < 2:
            return genome_a

        point = self._random.randint(1, min(len(genome_a), len(genome_b)) - 1)
        return genome_a[:point] + genome_b[point:]

    def _mutate(
        self,
        genome: tuple[AgentGene, ...],
        rate: float,
    ) -> tuple[AgentGene, ...]:
        """Randomly perturb gene values with given probability."""
        mutated: list[AgentGene] = []
        for gene in genome:
            if self._random.random() < rate:
                delta = self._random.uniform(-0.1, 0.1)
                new_value = max(gene.min_bound, min(gene.max_bound, gene.value + delta))
                mutated.append(AgentGene(
                    gene_id=gene.gene_id,
                    trait=gene.trait,
                    value=new_value,
                    min_bound=gene.min_bound,
                    max_bound=gene.max_bound,
                ))
            else:
                mutated.append(gene)
        return tuple(mutated)


def _compute_diversity(agents: tuple[HyperAgent, ...]) -> float:
    """Compute population diversity as mean pairwise genome distance."""
    if len(agents) < 2:
        return 0.0

    total_distance = 0.0
    pair_count = 0
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            distance = _genome_distance(agents[i].genome, agents[j].genome)
            total_distance += distance
            pair_count += 1
    return total_distance / pair_count if pair_count > 0 else 0.0


def _genome_distance(
    g1: tuple[AgentGene, ...], g2: tuple[AgentGene, ...]
) -> float:
    """Euclidean distance between two genomes."""
    min_len = min(len(g1), len(g2))
    if min_len == 0:
        return 0.0
    squared_diff = 0.0
    for i in range(min_len):
        squared_diff += (g1[i].value - g2[i].value) ** 2
    return math.sqrt(squared_diff) / min_len
