"""
Lyra Parallel Exploration Engine: DGM-Inspired Agent Tree

Implements parallel exploration with metaproductivity tracking for
10× speedup over sequential evolution.

Based on: Darwin Gödel Machine (arXiv:2505.22954)
Phase: 1 - Speed Breakthrough
Task: T101 - Parallel Exploration Engine
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import hashlib
import copy


@dataclass
class AgentNode:
    """
    Agent variant in exploration tree.

    Tracks both immediate performance and long-term metaproductivity.
    """
    id: str
    config: Dict[str, Any]
    generation: int
    parent_id: Optional[str] = None

    # Performance metrics
    immediate_score: float = 0.0
    descendant_yield: float = 0.0  # Average score of descendants
    clade_diversity: float = 0.0   # Diversity of descendant tree

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    evaluated: bool = False
    children: List[str] = field(default_factory=list)

    def metaproductivity(self, diversity_weight: float = 0.1) -> float:
        """
        Combine immediate + long-term value + diversity.

        Avoids "high-score, low-descendant" trap by considering
        both immediate performance, future potential, and clade diversity.

        Args:
            diversity_weight: Weight for diversity component (default 0.1)

        Returns:
            Metaproductivity score balancing all three factors
        """
        base_score = 0.3 * self.immediate_score + 0.6 * self.descendant_yield
        diversity_bonus = diversity_weight * self.clade_diversity
        return base_score + diversity_bonus


class ParallelExplorationEngine:
    """
    Parallel exploration engine with agent tree.

    Features:
    - 10× parallel exploration (vs sequential)
    - Metaproductivity tracking (long-term quality)
    - Pareto frontier maintenance
    - Diversity preservation
    """

    def __init__(self, n_workers: int = 10):
        """
        Initialize parallel exploration engine.

        Args:
            n_workers: Number of parallel workers
        """
        self.n_workers = n_workers

        # Agent tree
        self.nodes: Dict[str, AgentNode] = {}
        self.root_id: Optional[str] = None

        # Pareto frontier (non-dominated solutions)
        self.frontier: List[str] = []

        # Statistics
        self.total_evaluations = 0
        self.generations_explored = 0

        # Cross-time replay history
        self.replay_history: List[Dict[str, Any]] = []

    def initialize(self, baseline_config: Dict[str, Any]) -> str:
        """
        Initialize with baseline configuration.

        Args:
            baseline_config: Starting configuration

        Returns:
            Root node ID
        """
        root_id = self._generate_node_id(baseline_config, 0)

        root = AgentNode(
            id=root_id,
            config=baseline_config,
            generation=0
        )

        self.nodes[root_id] = root
        self.root_id = root_id
        self.frontier = [root_id]

        return root_id

    def explore_generation(
        self,
        n_mutations: int = 10,
        mutation_rate: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        Explore one generation in parallel.

        Args:
            n_mutations: Number of mutations per frontier node
            mutation_rate: Mutation probability

        Returns:
            List of (node_id, score) for new nodes
        """
        # Generate mutations from frontier
        mutations = []
        for node_id in self.frontier:
            node = self.nodes[node_id]
            for _ in range(n_mutations):
                mutated_config = self._mutate_config(
                    node.config,
                    mutation_rate
                )
                mutations.append((node_id, mutated_config))

        # Evaluate in parallel
        results = self._evaluate_parallel(mutations)

        # Add to tree
        new_nodes = []
        for (parent_id, config), score in results:
            node_id = self._add_node(parent_id, config, score)
            new_nodes.append((node_id, score))

        # Update frontier (Pareto-based)
        self._update_frontier()

        # Update metaproductivity
        self._update_metaproductivity()

        # Update clade diversity
        self._update_clade_diversity()

        # Record generation for cross-time replay
        self._record_generation_snapshot()

        self.generations_explored += 1

        return new_nodes

    def _evaluate_parallel(
        self,
        mutations: List[Tuple[str, Dict[str, Any]]]
    ) -> List[Tuple[Tuple[str, Dict[str, Any]], float]]:
        """
        Evaluate mutations in parallel.

        Args:
            mutations: List of (parent_id, config) tuples

        Returns:
            List of ((parent_id, config), score) tuples
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all evaluations
            future_to_mutation = {
                executor.submit(self._evaluate_config, config): (parent_id, config)
                for parent_id, config in mutations
            }

            # Collect results as they complete
            for future in as_completed(future_to_mutation):
                parent_id, config = future_to_mutation[future]
                try:
                    score = future.result()
                    results.append(((parent_id, config), score))
                    self.total_evaluations += 1
                except Exception as e:
                    print(f"Evaluation failed: {e}")

        return results

    def _evaluate_config(self, config: Dict[str, Any]) -> float:
        """
        Evaluate agent configuration.

        Placeholder: In production, this would run actual benchmarks.

        Args:
            config: Agent configuration

        Returns:
            Performance score
        """
        # Placeholder: Simple heuristic based on config complexity
        # In production: Run actual evaluation on benchmark tasks

        complexity = len(json.dumps(config))
        skill_count = len(config.get("skills", []))

        # Dummy score: balance complexity and capability
        score = min(1.0, (skill_count * 0.1) + (complexity / 1000))

        return score

    def _add_node(
        self,
        parent_id: str,
        config: Dict[str, Any],
        score: float
    ) -> str:
        """
        Add node to tree.

        Args:
            parent_id: Parent node ID
            config: Agent configuration
            score: Performance score

        Returns:
            New node ID
        """
        parent = self.nodes[parent_id]
        generation = parent.generation + 1

        node_id = self._generate_node_id(config, generation)

        node = AgentNode(
            id=node_id,
            config=config,
            generation=generation,
            parent_id=parent_id,
            immediate_score=score,
            evaluated=True
        )

        self.nodes[node_id] = node
        parent.children.append(node_id)

        return node_id

    def _update_frontier(self):
        """
        Update Pareto frontier with non-dominated solutions.

        A solution dominates another if it's better in at least one
        objective and not worse in any objective.
        """
        # Get all evaluated nodes
        candidates = [
            node_id for node_id, node in self.nodes.items()
            if node.evaluated
        ]

        # Find non-dominated solutions
        frontier = []
        for candidate_id in candidates:
            candidate = self.nodes[candidate_id]

            dominated = False
            for other_id in candidates:
                if candidate_id == other_id:
                    continue

                other = self.nodes[other_id]

                # Check if other dominates candidate
                if (other.immediate_score >= candidate.immediate_score and
                    other.metaproductivity() >= candidate.metaproductivity() and
                    (other.immediate_score > candidate.immediate_score or
                     other.metaproductivity() > candidate.metaproductivity())):
                    dominated = True
                    break

            if not dominated:
                frontier.append(candidate_id)

        self.frontier = frontier

    def _update_metaproductivity(self):
        """
        Update metaproductivity for all nodes.

        Descendant yield = average score of all descendants.
        """
        # Process nodes in reverse generation order (leaves first)
        nodes_by_gen = {}
        for node_id, node in self.nodes.items():
            gen = node.generation
            if gen not in nodes_by_gen:
                nodes_by_gen[gen] = []
            nodes_by_gen[gen].append(node_id)

        # Update from leaves to root
        for gen in sorted(nodes_by_gen.keys(), reverse=True):
            for node_id in nodes_by_gen[gen]:
                node = self.nodes[node_id]

                if not node.children:
                    # Leaf: descendant yield = immediate score
                    node.descendant_yield = node.immediate_score
                else:
                    # Internal: average of children's yields
                    child_yields = [
                        self.nodes[child_id].descendant_yield
                        for child_id in node.children
                    ]
                    node.descendant_yield = sum(child_yields) / len(child_yields)

    def _update_clade_diversity(self):
        """
        Update clade diversity for all nodes.

        Clade diversity measures the variety of descendants in a node's subtree.
        Higher diversity indicates the node spawned varied exploration paths.
        """
        # Process nodes in reverse generation order (leaves first)
        nodes_by_gen = {}
        for node_id, node in self.nodes.items():
            gen = node.generation
            if gen not in nodes_by_gen:
                nodes_by_gen[gen] = []
            nodes_by_gen[gen].append(node_id)

        # Update from leaves to root
        for gen in sorted(nodes_by_gen.keys(), reverse=True):
            for node_id in nodes_by_gen[gen]:
                node = self.nodes[node_id]

                if not node.children:
                    # Leaf: no diversity (single point)
                    node.clade_diversity = 0.0
                else:
                    # Internal: measure config diversity among descendants
                    descendant_configs = self._get_descendant_configs(node_id)
                    node.clade_diversity = self._calculate_config_diversity(descendant_configs)

    def _get_descendant_configs(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get all descendant configurations for a node.

        Args:
            node_id: Node ID

        Returns:
            List of descendant configurations
        """
        configs = []
        node = self.nodes[node_id]

        # Add direct children
        for child_id in node.children:
            child = self.nodes[child_id]
            configs.append(child.config)
            # Recursively add descendants
            configs.extend(self._get_descendant_configs(child_id))

        return configs

    def _calculate_config_diversity(self, configs: List[Dict[str, Any]]) -> float:
        """
        Calculate diversity score for a set of configurations.

        Uses skill set diversity as a proxy for overall diversity.

        Args:
            configs: List of configurations

        Returns:
            Diversity score (0.0 to 1.0)
        """
        if not configs:
            return 0.0

        # Extract skill sets
        skill_sets = [set(config.get("skills", [])) for config in configs]

        if not skill_sets:
            return 0.0

        # Calculate pairwise Jaccard distances
        n = len(skill_sets)
        if n == 1:
            return 0.0

        total_distance = 0.0
        comparisons = 0

        for i in range(n):
            for j in range(i + 1, n):
                set_i = skill_sets[i]
                set_j = skill_sets[j]

                # Jaccard distance = 1 - Jaccard similarity
                if not set_i and not set_j:
                    distance = 0.0
                else:
                    intersection = len(set_i & set_j)
                    union = len(set_i | set_j)
                    jaccard_similarity = intersection / union if union > 0 else 0.0
                    distance = 1.0 - jaccard_similarity

                total_distance += distance
                comparisons += 1

        # Average distance
        return total_distance / comparisons if comparisons > 0 else 0.0

    def _record_generation_snapshot(self):
        """
        Record current generation state for cross-time replay.

        Enables analyzing evolution trajectories across time.
        """
        snapshot = {
            "generation": self.generations_explored,
            "timestamp": datetime.now().isoformat(),
            "frontier_size": len(self.frontier),
            "total_nodes": len(self.nodes),
            "best_score": max(
                (n.immediate_score for n in self.nodes.values() if n.evaluated),
                default=0.0
            ),
            "best_metaproductivity": max(
                (n.metaproductivity() for n in self.nodes.values() if n.evaluated),
                default=0.0
            ),
            "avg_diversity": sum(
                n.clade_diversity for n in self.nodes.values()
            ) / len(self.nodes) if self.nodes else 0.0,
            "frontier_nodes": list(self.frontier)
        }

        self.replay_history.append(snapshot)

    def replay_evolution(self, start_gen: int = 0, end_gen: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Replay evolution history between generations.

        Enables analyzing how the population evolved over time.

        Args:
            start_gen: Starting generation (inclusive)
            end_gen: Ending generation (inclusive), None for latest

        Returns:
            List of generation snapshots
        """
        if end_gen is None:
            end_gen = self.generations_explored

        return [
            snapshot for snapshot in self.replay_history
            if start_gen <= snapshot["generation"] <= end_gen
        ]

    def _mutate_config(
        self,
        config: Dict[str, Any],
        mutation_rate: float
    ) -> Dict[str, Any]:
        """
        Mutate configuration.

        Args:
            config: Original configuration
            mutation_rate: Probability of mutation

        Returns:
            Mutated configuration
        """
        mutated = copy.deepcopy(config)

        # Simple mutations: add/remove skills
        import random

        if random.random() < mutation_rate:
            skills = mutated.get("skills", [])

            if random.random() < 0.5 and skills:
                # Remove a skill
                skills.pop(random.randint(0, len(skills) - 1))
            else:
                # Add a skill
                new_skill = f"skill_{random.randint(1, 100)}"
                if new_skill not in skills:
                    skills.append(new_skill)

            mutated["skills"] = skills

        return mutated

    def get_best_nodes(self, n: int = 10) -> List[AgentNode]:
        """
        Get top N nodes by metaproductivity.

        Args:
            n: Number of nodes to return

        Returns:
            List of best nodes
        """
        evaluated = [
            node for node in self.nodes.values()
            if node.evaluated
        ]

        sorted_nodes = sorted(
            evaluated,
            key=lambda n: n.metaproductivity(),
            reverse=True
        )

        return sorted_nodes[:n]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get exploration statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_nodes": len(self.nodes),
            "total_evaluations": self.total_evaluations,
            "generations_explored": self.generations_explored,
            "frontier_size": len(self.frontier),
            "best_score": max(
                (n.immediate_score for n in self.nodes.values() if n.evaluated),
                default=0.0
            ),
            "best_metaproductivity": max(
                (n.metaproductivity() for n in self.nodes.values() if n.evaluated),
                default=0.0
            )
        }

    @staticmethod
    def _generate_node_id(config: Dict[str, Any], generation: int) -> str:
        """Generate unique node ID."""
        content = json.dumps(config, sort_keys=True) + str(generation)
        hash_obj = hashlib.sha256(content.encode())
        return f"node_g{generation:03d}_{hash_obj.hexdigest()[:8]}"


# Example usage
if __name__ == "__main__":
    # Create parallel exploration engine
    engine = ParallelExplorationEngine(n_workers=10)

    # Initialize with baseline
    baseline = {
        "skills": ["skill1", "skill2"],
        "memory_config": {"type": "memtier"}
    }

    root_id = engine.initialize(baseline)
    print(f"✅ Initialized with root: {root_id}")

    # Explore 3 generations
    for gen in range(3):
        print(f"\n🔄 Exploring generation {gen + 1}...")
        new_nodes = engine.explore_generation(n_mutations=5)
        print(f"✅ Created {len(new_nodes)} new nodes")

    # Get statistics
    stats = engine.get_statistics()
    print(f"\n📊 Exploration Statistics:")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total evaluations: {stats['total_evaluations']}")
    print(f"   Generations: {stats['generations_explored']}")
    print(f"   Frontier size: {stats['frontier_size']}")
    print(f"   Best score: {stats['best_score']:.3f}")
    print(f"   Best metaproductivity: {stats['best_metaproductivity']:.3f}")

    # Get best nodes
    best = engine.get_best_nodes(n=3)
    print(f"\n🏆 Top 3 nodes by metaproductivity:")
    for i, node in enumerate(best, 1):
        print(f"   {i}. {node.id}: score={node.immediate_score:.3f}, "
              f"meta={node.metaproductivity():.3f}")
