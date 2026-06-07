"""
Skill registry for managing and retrieving skills.

Includes SkillGraph for dependency-based topological execution ordering.
"""

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .skill import Skill, SkillCategory, SkillSearchResult


class CycleError(Exception):
    """Raised when a cycle is detected in skill dependencies."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Cycle detected in skill dependencies: {' → '.join(cycle)}")


@dataclass
class SkillGraph:
    """
    Directed graph of skill dependencies.

    An edge ``skill_a -> skill_b`` means **skill_a depends on skill_b**,
    i.e. skill_b must execute before skill_a.
    """

    _edges: dict[str, set[str]] = field(default_factory=dict)
    _reverse: dict[str, set[str]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_dependency(self, skill_name: str, depends_on: str) -> None:
        """Record that ``skill_name`` depends on ``depends_on``."""
        if skill_name not in self._edges:
            self._edges[skill_name] = set()
        self._edges[skill_name].add(depends_on)

        if depends_on not in self._reverse:
            self._reverse[depends_on] = set()
        self._reverse[depends_on].add(skill_name)

    def add_node(self, skill_name: str) -> None:
        """Ensure a node exists in the graph (no-op if already present)."""
        self._edges.setdefault(skill_name, set())
        self._reverse.setdefault(skill_name, set())

    def remove_node(self, skill_name: str) -> None:
        """Remove a node and all incident edges."""
        self._edges.pop(skill_name, None)
        self._reverse.pop(skill_name, None)
        for deps in self._edges.values():
            deps.discard(skill_name)
        for rev in self._reverse.values():
            rev.discard(skill_name)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def dependencies(self, skill_name: str) -> set[str]:
        """Return the set of skills ``skill_name`` directly depends on."""
        return self._edges.get(skill_name, set())

    def dependents(self, skill_name: str) -> set[str]:
        """Return the set of skills that directly depend on ``skill_name``."""
        return self._reverse.get(skill_name, set())

    def has_cycle(self) -> bool:
        """Return True if the graph contains any cycle."""
        try:
            self._topological_sort()
            return False
        except CycleError:
            return True

    def detect_cycles(self) -> list[list[str]]:
        """Return a list of all cycles found in the graph (each as a node path)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colour: dict[str, int] = {n: WHITE for n in self._edges}
        parent: dict[str, str | None] = {}
        cycles: list[list[str]] = []

        def _dfs(node: str) -> None:
            colour[node] = GRAY
            for neighbour in self._edges.get(node, set()):
                if colour.get(neighbour, WHITE) == GRAY:
                    # Found a back-edge → reconstruct cycle
                    cycle: list[str] = [neighbour, node]
                    cur: str | None = node
                    while cur is not None and cur != neighbour:
                        cur = parent.get(cur)
                        if cur is not None:
                            cycle.append(cur)
                    cycle.reverse()
                    cycles.append(cycle)
                elif colour.get(neighbour, WHITE) == BLACK:
                    continue
                else:
                    parent[neighbour] = node
                    _dfs(neighbour)
            colour[node] = BLACK

        for n in list(colour):
            if colour[n] == WHITE:
                _dfs(n)
        return cycles

    # ------------------------------------------------------------------
    # Topological ordering
    # ------------------------------------------------------------------

    def get_execution_order(self) -> list[str]:
        """
        Return skills in topological order (dependencies first).

        Raises ``CycleError`` if a cycle is present.
        """
        return self._topological_sort()

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm."""
        # in-degree = how many skills this skill depends on
        in_degree: dict[str, int] = {}
        all_nodes: set[str] = set(self._edges.keys()) | set(self._reverse.keys())
        for n in all_nodes:
            in_degree[n] = len(self._edges.get(n, set()))

        queue: deque[str] = deque(n for n in all_nodes if in_degree[n] == 0)
        ordered: list[str] = []

        while queue:
            node = queue.popleft()
            ordered.append(node)
            for dependent in self._reverse.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(ordered) != len(all_nodes):
            remaining = all_nodes - set(ordered)
            # Reconstruct a cycle for the error message
            cycle_path = self._find_cycle_path(list(remaining))
            raise CycleError(cycle_path)

        return ordered

    @staticmethod
    def _find_cycle_path(remaining: list[str]) -> list[str]:
        """Heuristic: walk from the first remaining node following edges to reconstruct a cycle."""
        if not remaining:
            return []
        # Simple heuristic — just return the remaining nodes as the "cycle"
        return remaining

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph as adjacency dict."""
        return {
            name: sorted(deps)
            for name, deps in self._edges.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, list[str]]) -> "SkillGraph":
        """Build graph from adjacency dict."""
        g = cls()
        for name, deps in data.items():
            g.add_node(name)
            for dep in deps:
                g.add_dependency(name, dep)
        return g


class SkillRegistry:
    """
    Registry for managing skills.

    Provides CRUD operations and search functionality for skills.
    """

    def __init__(self):
        """Initialize skill registry."""
        self.skills: dict[str, Skill] = {}
        self._category_index: dict[SkillCategory, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}
        self._language_index: dict[str, set[str]] = {}
        self._graph: SkillGraph = SkillGraph()

    def register(self, skill: Skill) -> None:
        """
        Register a skill.

        Args:
            skill: Skill to register
        """
        self.skills[skill.name] = skill

        # Update category index
        if skill.category not in self._category_index:
            self._category_index[skill.category] = set()
        self._category_index[skill.category].add(skill.name)

        # Update tag index
        for tag in skill.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(skill.name)

        # Update language index
        if skill.language:
            if skill.language not in self._language_index:
                self._language_index[skill.language] = set()
            self._language_index[skill.language].add(skill.name)

        # Update dependency graph
        self._graph.add_node(skill.name)
        for dep in skill.dependencies:
            self._graph.add_dependency(skill.name, dep)

    def unregister(self, skill_name: str) -> bool:
        """
        Unregister a skill.

        Args:
            skill_name: Name of skill to unregister

        Returns:
            True if skill was unregistered, False if not found
        """
        if skill_name not in self.skills:
            return False

        skill = self.skills[skill_name]

        # Remove from category index
        if skill.category in self._category_index:
            self._category_index[skill.category].discard(skill_name)

        # Remove from tag index
        for tag in skill.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(skill_name)

        # Remove from language index
        if skill.language and skill.language in self._language_index:
            self._language_index[skill.language].discard(skill_name)

        self._graph.remove_node(skill_name)
        del self.skills[skill_name]
        return True

    def get(self, skill_name: str) -> Skill | None:
        """
        Get a skill by name.

        Args:
            skill_name: Name of skill

        Returns:
            Skill if found, None otherwise
        """
        return self.skills.get(skill_name)

    def find_by_trigger(self, text: str, limit: int = 10) -> list[SkillSearchResult]:
        """
        Find skills matching trigger patterns.

        Args:
            text: Text to match
            limit: Maximum number of results

        Returns:
            List of matching skills with scores
        """
        results = []
        for skill in self.skills.values():
            if skill.matches_trigger(text):
                # Calculate score based on number of matching patterns
                matches = sum(1 for p in skill.trigger_patterns if p.lower() in text.lower())
                score = matches / len(skill.trigger_patterns) if skill.trigger_patterns else 0
                results.append(SkillSearchResult(
                    skill=skill,
                    score=score,
                    match_reason=f"Matched {matches} trigger pattern(s)"
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def find_by_category(self, category: SkillCategory) -> list[Skill]:
        """
        Find skills by category.

        Args:
            category: Skill category

        Returns:
            List of skills in category
        """
        skill_names = self._category_index.get(category, set())
        return [self.skills[name] for name in skill_names]

    def find_by_tags(self, tags: set[str], match_all: bool = False) -> list[Skill]:
        """
        Find skills by tags.

        Args:
            tags: Tags to match
            match_all: If True, skill must match all tags. If False, any tag.

        Returns:
            List of matching skills
        """
        if not tags:
            return []

        if match_all:
            # Find skills that have all tags
            skill_sets = [self._tag_index.get(tag, set()) for tag in tags]
            if not skill_sets:
                return []
            matching_names = set.intersection(*skill_sets)
        else:
            # Find skills that have any tag
            matching_names = set()
            for tag in tags:
                matching_names.update(self._tag_index.get(tag, set()))

        return [self.skills[name] for name in matching_names]

    def find_by_language(self, language: str) -> list[Skill]:
        """
        Find skills by programming language.

        Args:
            language: Programming language

        Returns:
            List of skills for language
        """
        skill_names = self._language_index.get(language, set())
        return [self.skills[name] for name in skill_names]

    def search(
        self,
        query: str,
        category: SkillCategory | None = None,
        tags: set[str] | None = None,
        language: str | None = None,
        limit: int = 10,
    ) -> list[SkillSearchResult]:
        """
        Search for skills with multiple filters.

        Args:
            query: Search query (matches name, description, content)
            category: Filter by category
            tags: Filter by tags
            language: Filter by language
            limit: Maximum results

        Returns:
            List of matching skills with scores
        """
        candidates = list(self.skills.values())

        # Apply filters
        if category:
            candidates = [s for s in candidates if s.category == category]

        if tags:
            candidates = [s for s in candidates if s.matches_tags(tags)]

        if language:
            candidates = [s for s in candidates if s.language == language]

        # Score by query match
        results = []
        query_lower = query.lower()
        for skill in candidates:
            score = 0.0
            match_reasons = []

            # Name match (highest weight)
            if query_lower in skill.name.lower():
                score += 1.0
                match_reasons.append("name")

            # Description match
            if query_lower in skill.description.lower():
                score += 0.5
                match_reasons.append("description")

            # Content match (lowest weight)
            if query_lower in skill.content.lower():
                score += 0.2
                match_reasons.append("content")

            # Tag match
            if any(query_lower in tag.lower() for tag in skill.tags):
                score += 0.7
                match_reasons.append("tags")

            if score > 0:
                results.append(SkillSearchResult(
                    skill=skill,
                    score=score,
                    match_reason=f"Matched in: {', '.join(match_reasons)}"
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def get_statistics(self) -> dict[str, any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_skills": len(self.skills),
            "by_category": {
                cat.value: len(names)
                for cat, names in self._category_index.items()
            },
            "by_language": {
                lang: len(names)
                for lang, names in self._language_index.items()
            },
            "total_tags": len(self._tag_index),
            "sources": {
                "lyra": sum(1 for s in self.skills.values() if s.source == "lyra"),
                "ecc": sum(1 for s in self.skills.values() if s.source == "ecc"),
            },
        }

    def save(self, path: Path) -> None:
        """
        Save registry to JSON file.

        Args:
            path: Path to save file
        """
        data = {
            "skills": [skill.to_dict() for skill in self.skills.values()],
            "version": "1.0.0",
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path) -> int:
        """
        Load registry from JSON file.

        Args:
            path: Path to load file

        Returns:
            Number of skills loaded
        """
        with open(path) as f:
            data = json.load(f)

        count = 0
        for skill_data in data.get("skills", []):
            skill = Skill.from_dict(skill_data)
            self.register(skill)
            count += 1

        return count

    @property
    def graph(self) -> SkillGraph:
        """Return the internal dependency graph."""
        return self._graph

    def get_execution_order(self) -> list[str]:
        """
        Return skill names in topological order based on dependencies.

        Skills that are depended upon come first. Raises ``CycleError``
        if a dependency cycle is detected.
        """
        return self._graph.get_execution_order()

    def clear(self) -> None:
        """Clear all skills from registry."""
        self.skills.clear()
        self._category_index.clear()
        self._tag_index.clear()
        self._language_index.clear()
        self._graph = SkillGraph()
