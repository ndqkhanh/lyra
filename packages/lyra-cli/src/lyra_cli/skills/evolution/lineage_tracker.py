"""Lineage Tracker - Parent-child skill ancestry and inheritance tracking.

Tracks skill genealogies across generations, recording which skills
were derived from which parent skills and how traits were inherited.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SkillLineage:
    """Immutable record of a skill's ancestry."""

    skill_name: str
    parent_name: str | None  # None for original/root skills
    generation: int  # 0 = original, 1 = first derivative, etc.
    derived_at: str
    inheritance_mask: tuple[str, ...]  # Traits inherited from parent
    mutation_log: tuple[str, ...]  # Traits mutated from parent
    fitness_score: float = 0.0

    @property
    def is_root(self) -> bool:
        return self.parent_name is None

    @property
    def trait_count(self) -> int:
        return len(self.inheritance_mask) + len(self.mutation_log)


@dataclass(frozen=True)
class LineageGraph:
    """Snapshot of the full lineage graph at a point in time."""

    nodes: tuple[SkillLineage, ...]
    snapshot_at: str
    total_generations: int
    root_skills: tuple[str, ...]


class LineageTracker:
    """Tracks skill genealogies across generations of evolution.

    Features:
    - Parent-child ancestry recording
    - Multi-generational lineage chains
    - Inheritance/mutation tracking
    - Lineage graph export
    - Ancestor/descendant queries
    """

    def __init__(self):
        self._lineages: dict[str, SkillLineage] = {}

    def record_birth(
        self,
        skill_name: str,
        parent_name: str | None,
        inherited_traits: list[str] | None = None,
        mutated_traits: list[str] | None = None,
    ) -> SkillLineage:
        """Record the creation of a new skill with its lineage.

        Args:
            skill_name: Name of the new skill
            parent_name: Name of the parent skill (None for root)
            inherited_traits: Traits inherited from the parent
            mutated_traits: New traits mutated from parent

        Returns:
            The recorded SkillLineage
        """
        generation = 0
        if parent_name and parent_name in self._lineages:
            generation = self._lineages[parent_name].generation + 1

        lineage = SkillLineage(
            skill_name=skill_name,
            parent_name=parent_name,
            generation=generation,
            derived_at=datetime.now().isoformat(),
            inheritance_mask=tuple(inherited_traits or []),
            mutation_log=tuple(mutated_traits or []),
        )
        self._lineages[skill_name] = lineage
        return lineage

    def get_lineage(self, skill_name: str) -> SkillLineage | None:
        """Get the lineage record for a skill."""
        return self._lineages.get(skill_name)

    def get_ancestors(self, skill_name: str) -> list[SkillLineage]:
        """Get all ancestors of a skill up to the root."""
        ancestors = []
        current = self._lineages.get(skill_name)
        while current and current.parent_name:
            parent = self._lineages.get(current.parent_name)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break
        return ancestors

    def get_descendants(self, skill_name: str) -> list[SkillLineage]:
        """Get all direct descendants of a skill."""
        return [
            lin
            for lin in self._lineages.values()
            if lin.parent_name == skill_name
        ]

    def get_family_tree(self, root_name: str) -> dict:
        """Get the full family tree rooted at a skill.

        Args:
            root_name: Root skill name

        Returns:
            Nested dict representing the family tree
        """
        root = self._lineages.get(root_name)
        if not root:
            return {}

        def build_tree(name: str) -> dict:
            lineage = self._lineages[name]
            children = self.get_descendants(name)
            return {
                "name": name,
                "generation": lineage.generation,
                "inherited_traits": list(lineage.inheritance_mask),
                "mutated_traits": list(lineage.mutation_log),
                "children": [build_tree(c.skill_name) for c in children],
            }

        return build_tree(root_name)

    def get_generation(self, generation: int) -> list[SkillLineage]:
        """Get all skills at a specific generation."""
        return [lin for lin in self._lineages.values() if lin.generation == generation]

    def get_lineage_chain(self, skill_name: str) -> list[str]:
        """Get the chain of skill names from root to the given skill."""
        chain = [skill_name]
        current = self._lineages.get(skill_name)
        while current and current.parent_name:
            chain.append(current.parent_name)
            current = self._lineages.get(current.parent_name)
        return list(reversed(chain))

    def depth(self, skill_name: str) -> int:
        """Get the depth (distance from root) of a skill."""
        lineage = self._lineages.get(skill_name)
        return lineage.generation if lineage else 0

    def export_graph(self) -> LineageGraph:
        """Export the full lineage graph as a snapshot."""
        root_skills = tuple(
            lin.skill_name for lin in self._lineages.values() if lin.is_root
        )
        return LineageGraph(
            nodes=tuple(self._lineages.values()),
            snapshot_at=datetime.now().isoformat(),
            total_generations=max(
                (lin.generation for lin in self._lineages.values()), default=0
            ),
            root_skills=root_skills,
        )

    def find_common_ancestor(
        self, skill_a: str, skill_b: str
    ) -> SkillLineage | None:
        """Find the most recent common ancestor of two skills."""
        ancestors_a = {a.skill_name for a in self.get_ancestors(skill_a)}
        ancestors_a.add(skill_a)

        current = self._lineages.get(skill_b)
        while current:
            if current.skill_name in ancestors_a:
                return current
            current = (
                self._lineages.get(current.parent_name)
                if current.parent_name
                else None
            )
        return None

    def count_descendants(self, skill_name: str) -> int:
        """Count total descendants (direct and indirect) of a skill."""
        direct = self.get_descendants(skill_name)
        total = len(direct)
        for child in direct:
            total += self.count_descendants(child.skill_name)
        return total

    @property
    def total_skills(self) -> int:
        return len(self._lineages)

    @property
    def root_count(self) -> int:
        return sum(1 for lin in self._lineages.values() if lin.is_root)

    def clear(self) -> None:
        """Clear all lineage records."""
        self._lineages.clear()
