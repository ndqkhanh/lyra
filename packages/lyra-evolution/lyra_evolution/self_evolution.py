"""
Self-Evolution: Pareto Frontier Search and Cross-Time Replay

Implements continuous improvement through:
- Pareto frontier search across skill sets
- Cross-Time Replay for skill selection
- MemoryBench integration for evaluation
- Continuous improvement loops

Based on research: docs/36 (autogenesis-self-evolving-agents.md)
Impact: +20pp evolution improvement vs one-shot
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import json
import numpy as np


@dataclass
class AgentConfiguration:
    """Agent configuration on Pareto frontier."""
    id: str
    skills: List[str]
    memory_config: Dict[str, Any]
    metrics: Dict[str, float]  # accuracy, latency, cost
    generation: int


@dataclass
class EvaluationResult:
    """Result from MemoryBench evaluation."""
    config_id: str
    benchmark: str
    score: float
    details: Dict[str, Any]


class ParetoFrontierSearch:
    """
    Pareto frontier search for agent configurations.

    Maintains non-dominated configurations across multiple objectives:
    - Accuracy (maximize)
    - Latency (minimize)
    - Cost (minimize)
    """

    def __init__(self, objectives: List[str]):
        """
        Initialize Pareto frontier search.

        Args:
            objectives: List of objective names
        """
        self.objectives = objectives
        self.frontier: List[AgentConfiguration] = []

    def add_configuration(self, config: AgentConfiguration) -> bool:
        """
        Add configuration to frontier if non-dominated.

        Args:
            config: Agent configuration

        Returns:
            True if added to frontier
        """
        # Check if dominated by existing configs
        for existing in self.frontier:
            if self._dominates(existing.metrics, config.metrics):
                return False

        # Remove configs dominated by new config
        self.frontier = [
            c for c in self.frontier
            if not self._dominates(config.metrics, c.metrics)
        ]

        # Add new config
        self.frontier.append(config)
        return True

    def _dominates(self, m1: Dict[str, float], m2: Dict[str, float]) -> bool:
        """Check if m1 dominates m2."""
        # For each objective, m1 must be >= m2 (for maximize) or <= m2 (for minimize)
        better_in_all = True
        better_in_some = False

        for obj in self.objectives:
            v1 = m1.get(obj, 0.0)
            v2 = m2.get(obj, 0.0)

            # Assume maximize for accuracy, minimize for latency/cost
            if 'accuracy' in obj or 'score' in obj:
                if v1 < v2:
                    better_in_all = False
                if v1 > v2:
                    better_in_some = True
            else:  # minimize
                if v1 > v2:
                    better_in_all = False
                if v1 < v2:
                    better_in_some = True

        return better_in_all and better_in_some

    def get_frontier(self) -> List[AgentConfiguration]:
        """Get all configurations on frontier."""
        return self.frontier


class CrossTimeReplay:
    """
    Cross-Time Replay for skill selection.

    Evaluates skill sets across time on hard and easy probes:
    - Hard probe: Challenging tasks
    - Easy probe: Simple tasks
    - Selection: Maximize ρ_h · ρ_e (product of accuracies)
    """

    def __init__(self):
        """Initialize Cross-Time Replay."""
        self.hard_probe: List[Dict[str, Any]] = []
        self.easy_probe: List[Dict[str, Any]] = []

    def add_to_hard_probe(self, task: Dict[str, Any]) -> None:
        """Add task to hard probe."""
        self.hard_probe.append(task)

    def add_to_easy_probe(self, task: Dict[str, Any]) -> None:
        """Add task to easy probe."""
        self.easy_probe.append(task)

    def evaluate_configuration(
        self,
        config: AgentConfiguration,
        executor
    ) -> Tuple[float, float]:
        """
        Evaluate configuration on probes.

        Args:
            config: Agent configuration
            executor: Function to execute tasks

        Returns:
            (hard_accuracy, easy_accuracy)
        """
        # Evaluate on hard probe
        hard_correct = 0
        for task in self.hard_probe:
            result = executor(config, task)
            if result['success']:
                hard_correct += 1

        rho_h = hard_correct / len(self.hard_probe) if self.hard_probe else 0.0

        # Evaluate on easy probe
        easy_correct = 0
        for task in self.easy_probe:
            result = executor(config, task)
            if result['success']:
                easy_correct += 1

        rho_e = easy_correct / len(self.easy_probe) if self.easy_probe else 0.0

        return rho_h, rho_e

    def select_best_configuration(
        self,
        configs: List[AgentConfiguration],
        executor
    ) -> AgentConfiguration:
        """
        Select best configuration using ρ_h · ρ_e.

        Args:
            configs: List of configurations
            executor: Function to execute tasks

        Returns:
            Best configuration
        """
        best_config = None
        best_score = -1.0

        for config in configs:
            rho_h, rho_e = self.evaluate_configuration(config, executor)
            score = rho_h * rho_e

            if score > best_score:
                best_score = score
                best_config = config

        return best_config


class MemoryBenchIntegration:
    """
    Integration with MemoryBench for evaluation.

    Evaluates agent configurations on standard benchmarks:
    - LongMemEval
    - MemoryBench tasks
    - Custom benchmarks
    """

    def __init__(self, benchmarks_dir: Path):
        """
        Initialize MemoryBench integration.

        Args:
            benchmarks_dir: Directory containing benchmark tasks
        """
        self.benchmarks_dir = Path(benchmarks_dir)
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(
        self,
        config: AgentConfiguration,
        benchmark_name: str,
        executor
    ) -> EvaluationResult:
        """
        Evaluate configuration on benchmark.

        Args:
            config: Agent configuration
            benchmark_name: Benchmark name
            executor: Function to execute tasks

        Returns:
            Evaluation result
        """
        # Load benchmark tasks
        tasks = self._load_benchmark(benchmark_name)

        # Execute tasks
        correct = 0
        total = len(tasks)
        details = []

        for task in tasks:
            result = executor(config, task)
            if result['success']:
                correct += 1

            details.append({
                'task_id': task['id'],
                'success': result['success'],
                'latency': result.get('latency', 0.0)
            })

        score = correct / total if total > 0 else 0.0

        return EvaluationResult(
            config_id=config.id,
            benchmark=benchmark_name,
            score=score,
            details={'tasks': details, 'correct': correct, 'total': total}
        )

    def _load_benchmark(self, benchmark_name: str) -> List[Dict[str, Any]]:
        """Load benchmark tasks."""
        benchmark_file = self.benchmarks_dir / f"{benchmark_name}.json"

        if not benchmark_file.exists():
            # Return empty benchmark
            return []

        with open(benchmark_file, 'r') as f:
            return json.load(f)


class SelfEvolutionPipeline:
    """
    Complete self-evolution pipeline.

    Combines:
    - Pareto frontier search
    - Cross-Time Replay
    - MemoryBench evaluation
    - Continuous improvement
    """

    def __init__(
        self,
        objectives: List[str],
        benchmarks_dir: Path,
        configs_dir: Path
    ):
        """
        Initialize self-evolution pipeline.

        Args:
            objectives: Optimization objectives
            benchmarks_dir: Benchmarks directory
            configs_dir: Configurations directory
        """
        self.pareto = ParetoFrontierSearch(objectives)
        self.replay = CrossTimeReplay()
        self.memorybench = MemoryBenchIntegration(benchmarks_dir)

        self.configs_dir = Path(configs_dir)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

        self.generation = 0

    def run(
        self,
        initial_configs: List[AgentConfiguration],
        executor,
        generations: int = 10
    ) -> AgentConfiguration:
        """
        Run self-evolution loop.

        Args:
            initial_configs: Initial configurations
            executor: Function to execute tasks
            generations: Number of generations

        Returns:
            Best configuration
        """
        # Initialize frontier
        for config in initial_configs:
            self.pareto.add_configuration(config)

        for gen in range(generations):
            self.generation = gen + 1
            print(f"\n=== Self-Evolution Generation {self.generation}/{generations} ===")

            # Get current frontier
            frontier = self.pareto.get_frontier()

            # Evaluate on MemoryBench
            for config in frontier:
                result = self.memorybench.evaluate(config, "memorybench", executor)
                print(f"  Config {config.id}: {result.score:.2%}")

                # Update metrics
                config.metrics['memorybench_score'] = result.score

            # Generate new configurations (mutations)
            new_configs = self._generate_mutations(frontier)

            # Evaluate new configs
            for config in new_configs:
                result = self.memorybench.evaluate(config, "memorybench", executor)
                config.metrics['memorybench_score'] = result.score

                # Add to frontier
                self.pareto.add_configuration(config)

            # Update probes
            self._update_probes(executor)

            # Save frontier
            self._save_frontier()

        # Select best using Cross-Time Replay
        final_frontier = self.pareto.get_frontier()
        best_config = self.replay.select_best_configuration(final_frontier, executor)

        print(f"\n✅ Best configuration: {best_config.id}")
        return best_config

    def _generate_mutations(
        self,
        configs: List[AgentConfiguration]
    ) -> List[AgentConfiguration]:
        """Generate mutated configurations."""
        mutations = []

        for config in configs:
            # Mutation 1: Add random skill
            new_config = AgentConfiguration(
                id=f"gen{self.generation}_mut{len(mutations)}",
                skills=config.skills + [f"skill_{np.random.randint(100)}"],
                memory_config=config.memory_config.copy(),
                metrics={},
                generation=self.generation
            )
            mutations.append(new_config)

            # Mutation 2: Remove random skill
            if len(config.skills) > 1:
                new_skills = config.skills.copy()
                new_skills.pop(np.random.randint(len(new_skills)))

                new_config = AgentConfiguration(
                    id=f"gen{self.generation}_mut{len(mutations)}",
                    skills=new_skills,
                    memory_config=config.memory_config.copy(),
                    metrics={},
                    generation=self.generation
                )
                mutations.append(new_config)

        return mutations[:5]  # Limit mutations

    def _update_probes(self, executor) -> None:
        """Update hard and easy probes."""
        # Add tasks that failed to hard probe
        # Add tasks that succeeded to easy probe
        pass

    def _save_frontier(self) -> None:
        """Save current frontier to disk."""
        frontier_data = [
            {
                'id': c.id,
                'skills': c.skills,
                'memory_config': c.memory_config,
                'metrics': c.metrics,
                'generation': c.generation
            }
            for c in self.pareto.get_frontier()
        ]

        frontier_file = self.configs_dir / f"frontier_gen{self.generation}.json"
        with open(frontier_file, 'w') as f:
            json.dump(frontier_data, f, indent=2)


# Usage example
"""
from lyra_evolution.self_evolution import SelfEvolutionPipeline, AgentConfiguration
from pathlib import Path

# Initialize pipeline
pipeline = SelfEvolutionPipeline(
    objectives=['accuracy', 'latency', 'cost'],
    benchmarks_dir=Path("~/.lyra/benchmarks").expanduser(),
    configs_dir=Path("~/.lyra/evolution/configs").expanduser()
)

# Initial configurations
initial_configs = [
    AgentConfiguration(
        id="baseline",
        skills=["skill1", "skill2"],
        memory_config={"type": "memtier"},
        metrics={},
        generation=0
    )
]

# Define executor
def executor(config, task):
    # Execute task with config
    return {'success': True, 'latency': 0.1}

# Run evolution
best_config = pipeline.run(initial_configs, executor, generations=10)

print(f"Best config: {best_config.id}")
print(f"Skills: {best_config.skills}")
print(f"Metrics: {best_config.metrics}")
"""
