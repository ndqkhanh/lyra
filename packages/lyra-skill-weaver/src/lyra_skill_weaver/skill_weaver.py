"""Dynamic skill composition engine.

Constructs skill graphs, chains skills automatically for complex tasks,
checks compatibility, and manages skill versions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Protocol

from .exceptions import (
    SkillNotFoundError,
    SkillConflictError,
    CompositionError,
    CircularDependencyError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class SkillType(Enum):
    """Classification of skill types."""

    PRIMITIVE = auto()      # Single-step, atomic operation
    COMPOSITE = auto()      # Built from other skills
    ADAPTIVE = auto()       # Behavior changes based on context
    GENERATIVE = auto()     # Produces new skills or code
    VALIDATOR = auto()      # Checks or verifies outputs
    TRANSFORMER = auto()    # Transforms input to output
    ORCHESTRATOR = auto()   # Coordinates other skills


class CompositionPattern(Enum):
    """Known composition patterns for chaining skills."""

    SEQUENTIAL = auto()     # A -> B -> C
    PARALLEL = auto()       # A, B, C run concurrently
    CONDITIONAL = auto()    # if X then A else B
    ITERATIVE = auto()      # Repeat until convergence
    HYBRID = auto()         # Mix of patterns
    FANOUT = auto()         # One-to-many
    FANIN = auto()          # Many-to-one
    PIPELINE = auto()       # Staged pipeline with queuing


class SkillStatus(Enum):
    """Lifecycle status of a skill."""

    REGISTERED = auto()
    ACTIVE = auto()
    DEPRECATED = auto()
    DISABLED = auto()
    EXPERIMENTAL = auto()


@dataclass
class SkillMetadata:
    """Metadata for a skill.

    Attributes:
        skill_id: Unique identifier.
        name: Human-readable name.
        version: Semantic version string.
        description: What the skill does.
        author: Who created it.
        tags: Searchable tags.
        created_at: Unix timestamp of creation.
        updated_at: Last modification timestamp.
        status: Current lifecycle status.
    """

    skill_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: SkillStatus = SkillStatus.REGISTERED


@dataclass
class SkillIO:
    """Input/output specification for a skill.

    Attributes:
        name: Parameter/output name.
        type_hint: Python type name.
        required: Whether this is required.
        default: Default value if not provided.
        description: Human-readable description.
    """

    name: str
    type_hint: str = "Any"
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class SkillDefinition:
    """Full definition of a composable skill.

    Attributes:
        metadata: Skill metadata.
        skill_type: Type classification.
        inputs: Required inputs.
        outputs: Produced outputs.
        dependencies: IDs of skills this depends on.
        conflicts: IDs of incompatible skills.
        context_requirements: Required context features with minimum values.
        quality_score: Estimated quality (0.0 to 1.0).
        estimated_cost: Estimated cost per invocation.
        avg_latency_ms: Average latency in milliseconds.
        source_code: Optional reference to implementation.
        config_schema: JSON Schema for configuration.
        examples: Example usage patterns.
    """

    metadata: SkillMetadata
    skill_type: SkillType = SkillType.PRIMITIVE
    inputs: list[SkillIO] = field(default_factory=list)
    outputs: list[SkillIO] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    context_requirements: dict[str, float] = field(default_factory=dict)
    quality_score: float = 0.5
    estimated_cost: float = 0.0
    avg_latency_ms: float = 0.0
    source_code: str = ""
    config_schema: dict[str, Any] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)

    @property
    def skill_id(self) -> str:
        """Convenience accessor for the skill ID."""
        return self.metadata.skill_id

    @property
    def name(self) -> str:
        """Convenience accessor for the skill name."""
        return self.metadata.name


@dataclass
class SkillEdge:
    """An edge in the skill dependency graph.

    Attributes:
        source_id: Source skill ID.
        target_id: Target skill ID.
        edge_type: Relationship type.
        weight: Edge weight (used for optimization).
        metadata: Additional edge data.
    """

    source_id: str
    target_id: str
    edge_type: str = "depends_on"  # depends_on, conflicts_with, enhances, replaces
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Skill graph ────────────────────────────────────────────────────────


class SkillGraph:
    """Directed graph representing skill dependencies, conflicts, and compatibilities.

    Supports topological sorting, cycle detection, and shortest path for
    composing skill chains.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, SkillDefinition] = {}
        self._edges: dict[str, list[SkillEdge]] = defaultdict(list)
        self._reverse_edges: dict[str, list[SkillEdge]] = defaultdict(list)

    def add_node(self, skill: SkillDefinition) -> None:
        """Add a skill node to the graph."""
        self._nodes[skill.skill_id] = skill
        logger.debug("Skill node added: %s", skill.skill_id)

    def remove_node(self, skill_id: str) -> None:
        """Remove a skill node and all its edges."""
        self._nodes.pop(skill_id, None)
        self._edges.pop(skill_id, None)
        self._reverse_edges.pop(skill_id, None)
        for edges in self._edges.values():
            edges[:] = [e for e in edges if e.target_id != skill_id and e.source_id != skill_id]
        for edges in self._reverse_edges.values():
            edges[:] = [e for e in edges if e.target_id != skill_id and e.source_id != skill_id]

    def add_edge(self, edge: SkillEdge) -> None:
        """Add a directed edge between two skills."""
        if edge.source_id not in self._nodes:
            raise SkillNotFoundError(edge.source_id)
        if edge.target_id not in self._nodes:
            raise SkillNotFoundError(edge.target_id)
        self._edges[edge.source_id].append(edge)
        self._reverse_edges[edge.target_id].append(edge)

    def get_node(self, skill_id: str) -> SkillDefinition:
        """Get a skill node by ID.

        Raises:
            SkillNotFoundError: If not found.
        """
        if skill_id not in self._nodes:
            raise SkillNotFoundError(skill_id)
        return self._nodes[skill_id]

    def has_node(self, skill_id: str) -> bool:
        """Check if a skill exists in the graph."""
        return skill_id in self._nodes

    def get_dependencies(self, skill_id: str) -> list[str]:
        """Get direct dependencies of a skill."""
        return [e.target_id for e in self._edges.get(skill_id, []) if e.edge_type == "depends_on"]

    def get_dependents(self, skill_id: str) -> list[str]:
        """Get skills that depend on the given skill."""
        return [e.source_id for e in self._reverse_edges.get(skill_id, []) if e.edge_type == "depends_on"]

    def get_conflicts(self, skill_id: str) -> list[str]:
        """Get skills that conflict with the given skill."""
        conflicts = [e.target_id for e in self._edges.get(skill_id, []) if e.edge_type == "conflicts_with"]
        conflicts.extend(
            e.source_id for e in self._reverse_edges.get(skill_id, []) if e.edge_type == "conflicts_with"
        )
        return list(set(conflicts))

    def topological_sort(self) -> list[str]:
        """Return skills in dependency order (topological sort).

        Returns:
            List of skill IDs in dependency-respecting order.

        Raises:
            CircularDependencyError: If a cycle is detected.
        """
        in_degree: dict[str, int] = {sid: 0 for sid in self._nodes}
        for edges in self._edges.values():
            for e in edges:
                if e.edge_type == "depends_on":
                    in_degree[e.source_id] = in_degree.get(e.source_id, 0) + 1

        queue: deque[str] = deque(sid for sid, deg in in_degree.items() if deg == 0)
        result: list[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for dep_skill_id in self.get_dependencies(node):
                in_degree[dep_skill_id] -= 1
                if in_degree[dep_skill_id] == 0:
                    queue.append(dep_skill_id)

        if len(result) != len(self._nodes):
            # Find the cycle
            remaining = set(self._nodes) - set(result)
            cycle = self._find_cycle(remaining)
            raise CircularDependencyError(cycle)

        return result

    def _find_cycle(self, nodes: set[str]) -> list[str]:
        """Find a cycle in the remaining nodes."""
        visited: set[str] = set()
        stack: list[str] = []
        cycle_path: list[str] = []

        def dfs(node: str) -> bool:
            if node in stack:
                cycle_path.extend(stack[stack.index(node):] + [node])
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.append(node)
            for dep in self.get_dependencies(node):
                if dep in nodes and dfs(dep):
                    return True
            stack.pop()
            return False

        for node in nodes:
            if dfs(node):
                break

        return cycle_path if cycle_path else list(nodes)[:2]

    def shortest_path(
        self, source_id: str, target_id: str
    ) -> Optional[list[str]]:
        """Find shortest dependency path between two skills (BFS).

        Returns:
            List of skill IDs in path, or None if no path exists.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        queue: deque[tuple[str, list[str]]] = deque([(source_id, [source_id])])
        visited: set[str] = {source_id}

        while queue:
            current, path = queue.popleft()
            if current == target_id:
                return path

            for dep in self.get_dependencies(current):
                if dep not in visited:
                    visited.add(dep)
                    queue.append((dep, path + [dep]))

        return None

    def find_skills_by_output(
        self, required_outputs: set[str]
    ) -> list[SkillDefinition]:
        """Find skills that produce the given outputs.

        Args:
            required_outputs: Names of required outputs.

        Returns:
            Skills that produce at least one of the required outputs.
        """
        return [
            skill for skill in self._nodes.values()
            if set(o.name for o in skill.outputs) & required_outputs
        ]

    def validate_compatibility(
        self, skill_a: str, skill_b: str
    ) -> tuple[bool, Optional[str]]:
        """Check if two skills are compatible for composition.

        Args:
            skill_a: First skill ID.
            skill_b: Second skill ID.

        Returns:
            Tuple of (is_compatible, conflict_reason).
        """
        if skill_a not in self._nodes or skill_b not in self._nodes:
            return False, "One or both skills not found"

        sk_a = self._nodes[skill_a]
        sk_b = self._nodes[skill_b]

        # Check explicit conflicts
        if skill_b in sk_a.conflicts or skill_a in sk_b.conflicts:
            return False, f"Explicit conflict between {skill_a} and {skill_b}"

        # Check IO compatibility (rough type matching)
        for a_out in sk_a.outputs:
            for b_in in sk_b.inputs:
                if a_out.name == b_in.name and a_out.type_hint != b_in.type_hint:
                    return False, (
                        f"Type mismatch on '{a_out.name}': "
                        f"{a_out.type_hint} vs {b_in.type_hint}"
                    )

        return True, None

    @property
    def node_count(self) -> int:
        """Number of skills in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return sum(len(edges) for edges in self._edges.values())

    @property
    def nodes(self) -> dict[str, SkillDefinition]:
        """All nodes in the graph."""
        return dict(self._nodes)


# ── Skill Registry ─────────────────────────────────────────────────────


class SkillRegistry:
    """Central registry for skill management with versioning and discovery.

    Maintains a catalog of all available skills, supports version-aware
    lookups, and provides querying by capability, output, and compatibility.
    """

    def __init__(self) -> None:
        self._skills: dict[str, list[SkillDefinition]] = defaultdict(list)  # name -> versions
        self._by_id: dict[str, SkillDefinition] = {}
        self._by_tag: dict[str, list[str]] = defaultdict(list)
        self._by_output: dict[str, list[str]] = defaultdict(list)
        self._graph = SkillGraph()

    def register(self, skill: SkillDefinition) -> None:
        """Register a skill in the registry.

        Args:
            skill: The skill definition to register.

        Raises:
            ValidationError: If the skill fails validation.
        """
        self._validate_skill(skill)

        name = skill.metadata.name
        self._skills[name].append(skill)
        self._by_id[skill.skill_id] = skill

        for tag in skill.metadata.tags:
            self._by_tag[tag].append(skill.skill_id)

        for output in skill.outputs:
            self._by_output[output.name].append(skill.skill_id)

        # Add to graph
        self._graph.add_node(skill)
        for dep_id in skill.dependencies:
            self._graph.add_edge(SkillEdge(
                source_id=skill.skill_id,
                target_id=dep_id,
                edge_type="depends_on",
            ))
        for conflict_id in skill.conflicts:
            self._graph.add_edge(SkillEdge(
                source_id=skill.skill_id,
                target_id=conflict_id,
                edge_type="conflicts_with",
            ))

        logger.info("Skill registered: %s v%s (id=%s)", name, skill.metadata.version, skill.skill_id)

    def _validate_skill(self, skill: SkillDefinition) -> None:
        """Validate a skill before registration."""
        if not skill.metadata.skill_id:
            raise ValidationError(skill.metadata.name, "skill_id cannot be empty")
        if not skill.metadata.name:
            raise ValidationError(skill.metadata.skill_id, "name cannot be empty")
        if skill.metadata.skill_id in self._by_id:
            existing = self._by_id[skill.metadata.skill_id]
            raise ValidationError(
                skill.metadata.skill_id,
                f"Skill ID already registered (existing: {existing.name} v{existing.metadata.version})",
            )

    def unregister(self, skill_id: str) -> bool:
        """Remove a skill from the registry.

        Returns:
            True if the skill was removed.
        """
        skill = self._by_id.pop(skill_id, None)
        if skill is None:
            return False

        name = skill.metadata.name
        self._skills[name] = [s for s in self._skills.get(name, []) if s.skill_id != skill_id]

        for tag in skill.metadata.tags:
            self._by_tag[tag] = [sid for sid in self._by_tag[tag] if sid != skill_id]

        for output in skill.outputs:
            self._by_output[output.name] = [sid for sid in self._by_output[output.name] if sid != skill_id]

        self._graph.remove_node(skill_id)
        logger.info("Skill unregistered: %s (id=%s)", name, skill_id)
        return True

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill by ID."""
        return self._by_id.get(skill_id)

    def get_latest(self, name: str) -> Optional[SkillDefinition]:
        """Get the latest version of a skill by name."""
        versions = self._skills.get(name, [])
        if not versions:
            return None
        return versions[-1]  # Last registered is latest

    def get_version(self, name: str, version: str) -> Optional[SkillDefinition]:
        """Get a specific version of a skill."""
        for skill in self._skills.get(name, []):
            if skill.metadata.version == version:
                return skill
        return None

    def list_versions(self, name: str) -> list[str]:
        """List all versions of a skill."""
        return [s.metadata.version for s in self._skills.get(name, [])]

    def find_by_tag(self, tag: str) -> list[SkillDefinition]:
        """Find skills by tag."""
        return [self._by_id[sid] for sid in self._by_tag.get(tag, []) if sid in self._by_id]

    def find_by_output(self, output_name: str) -> list[SkillDefinition]:
        """Find skills that produce a specific output."""
        return [self._by_id[sid] for sid in self._by_output.get(output_name, []) if sid in self._by_id]

    def find_by_capability(self, required_inputs: set[str], required_outputs: set[str]) -> list[SkillDefinition]:
        """Find skills that match input/output requirements."""
        candidates = set()
        for output_name in required_outputs:
            candidates.update(self._by_output.get(output_name, []))

        results = []
        for sid in candidates:
            skill = self._by_id[sid]
            produces = {o.name for o in skill.outputs}
            if produces & required_outputs:
                results.append(skill)

        # Sort by quality
        results.sort(key=lambda s: -s.quality_score)
        return results

    @property
    def graph(self) -> SkillGraph:
        """Get the skill dependency graph."""
        return self._graph

    @property
    def skill_count(self) -> int:
        """Total number of registered skills."""
        return len(self._by_id)

    @property
    def unique_skill_names(self) -> int:
        """Number of unique skill names."""
        return len(self._skills)

    @property
    def summary(self) -> dict[str, Any]:
        """Get registry summary."""
        by_type: dict[str, int] = {}
        for skill in self._by_id.values():
            st = skill.skill_type.name
            by_type[st] = by_type.get(st, 0) + 1

        return {
            "total_skills": self.skill_count,
            "unique_names": self.unique_skill_names,
            "by_type": by_type,
            "by_status": {},
            "tags": list(self._by_tag.keys()),
            "tags_count": len(self._by_tag),
        }


# ── Skill Weaver Engine ────────────────────────────────────────────────


@dataclass
class CompositionPlan:
    """A plan for composing skills to achieve a task.

    Attributes:
        plan_id: Unique identifier.
        modules: Ordered list of skill IDs in the composition.
        expected_outputs: Outputs the composition should produce.
        estimated_cost: Total estimated cost.
        estimated_latency_ms: Total estimated latency.
        pattern: Composition pattern used.
        quality_score: Estimated quality of the composition.
        metadata: Additional plan data.
    """

    plan_id: str = ""
    modules: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    pattern: CompositionPattern = CompositionPattern.SEQUENTIAL
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillWeaver:
    """Dynamic skill composition engine that builds execution plans.

    The weaver analyzes task requirements, checks skill compatibility,
    and constructs optimized composition plans using various patterns
    (sequential, parallel, conditional, iterative).
    """

    def __init__(self, registry: Optional[SkillRegistry] = None) -> None:
        self.registry = registry or SkillRegistry()
        self._active_plans: dict[str, CompositionPlan] = {}
        self._plan_history: deque[CompositionPlan] = deque(maxlen=100)
        self._task_type_patterns: dict[str, CompositionPattern] = {}

    # ── Skill management ───────────────────────────────────────────────

    def register_skill(self, skill: SkillDefinition) -> None:
        """Register a skill (convenience method)."""
        self.registry.register(skill)

    def register_skills(self, skills: list[SkillDefinition]) -> None:
        """Register multiple skills at once."""
        for skill in skills:
            self.registry.register(skill)

    # ── Composition ────────────────────────────────────────────────────

    async def weave(
        self,
        task_type: str,
        context: Optional[dict[str, float]] = None,
        pattern: Optional[CompositionPattern] = None,
        max_skills: int = 10,
    ) -> CompositionPlan:
        """Build a skill composition plan for a task.

        Args:
            task_type: Type of task to compose for.
            context: Current context features with values.
            pattern: Desired composition pattern (auto-selected if None).
            max_skills: Maximum number of skills in the plan.

        Returns:
            A composition plan.

        Raises:
            CompositionError: If composition fails.
        """
        context = context or {}
        required_outputs = self._get_required_outputs(task_type)
        pattern = pattern or self._select_pattern(task_type)

        if pattern == CompositionPattern.SEQUENTIAL:
            plan = self._compose_sequential(required_outputs, context, max_skills)
        elif pattern == CompositionPattern.PARALLEL:
            plan = self._compose_parallel(required_outputs, context, max_skills)
        elif pattern == CompositionPattern.FANOUT:
            plan = self._compose_fanout(required_outputs, context, max_skills)
        else:
            plan = self._compose_sequential(required_outputs, context, max_skills)

        plan.pattern = pattern
        self._record_plan(plan)
        return plan

    def _select_pattern(self, task_type: str) -> CompositionPattern:
        """Select the best composition pattern for a task type."""
        if task_type in self._task_type_patterns:
            return self._task_type_patterns[task_type]

        # Heuristic selection
        parallel_tasks = {"analysis", "evaluation", "generation"}
        sequential_tasks = {"pipeline", "transformation", "processing"}

        if task_type in parallel_tasks:
            return CompositionPattern.PARALLEL
        return CompositionPattern.SEQUENTIAL

    def _get_required_outputs(self, task_type: str) -> list[str]:
        """Get the outputs required for a task type."""
        mapping: dict[str, list[str]] = {
            "code_generation": ["code", "tests", "documentation"],
            "research": ["summary", "citations", "analysis", "references"],
            "debugging": ["diagnosis", "fix", "verification"],
            "planning": ["plan", "steps", "timeline", "risks"],
            "analysis": ["insights", "metrics", "recommendations"],
            "transformation": ["transformed_data", "validation_report"],
            "generation": ["generated_content", "quality_score"],
            "evaluation": ["evaluation_result", "score", "feedback"],
            "pipeline": ["final_output", "intermediate_results"],
        }
        return mapping.get(task_type, ["result"])

    def _compose_sequential(
        self,
        required_outputs: list[str],
        context: dict[str, float],
        max_skills: int,
    ) -> CompositionPlan:
        """Build a sequential composition (pipeline) of skills.

        Each skill's outputs feed into the next skill's inputs.
        """
        needed = set(required_outputs)
        chain: list[str] = []
        used: set[str] = set()
        satisfied: set[str] = set()
        plan_id = f"seq_{int(time.time() * 1000)}"

        while needed and len(chain) < max_skills:
            candidates = self.registry.find_by_capability(
                required_inputs=needed,
                required_outputs=needed & needed,
            )

            # Re-score with context matching
            best_skill: Optional[str] = None
            best_score = -1.0

            for skill in candidates:
                if skill.skill_id in used:
                    continue
                if skill.metadata.status in (SkillStatus.DISABLED, SkillStatus.DEPRECATED):
                    continue

                # Check conflicts with already selected skills
                has_conflict = any(
                    c in used for c in skill.conflicts
                )
                if has_conflict:
                    continue

                output_match = len(set(o.name for o in skill.outputs) & needed)
                dependency_satisfaction = len(set(skill.dependencies) & set(chain))

                context_score = sum(
                    1 for k, v in context.items()
                    if skill.context_requirements.get(k, 0) <= v + 0.1
                ) / max(len(skill.context_requirements), 1) if skill.context_requirements else 0.5

                # Weighted scoring
                score = (
                    output_match * 3.0
                    + dependency_satisfaction * 1.0
                    + context_score * 1.5
                    + skill.quality_score * 2.0
                    - skill.estimated_cost * 0.5
                    - (skill.avg_latency_ms / 1000.0) * 0.3
                )

                if score > best_score:
                    best_score = score
                    best_skill = skill.skill_id

            if best_skill is None:
                # Could not find a suitable next skill
                if not chain:
                    raise CompositionError(
                        f"No skills found for outputs: {needed}"
                    )
                break

            skill = self.registry.get(best_skill)
            if skill is None:
                raise SkillNotFoundError(best_skill)

            chain.append(best_skill)
            used.add(best_skill)
            satisfied |= {o.name for o in skill.outputs}
            needed -= satisfied

        total_cost = sum(
            self.registry.get(sid).estimated_cost
            for sid in chain if self.registry.get(sid)
        )
        total_latency = sum(
            self.registry.get(sid).avg_latency_ms
            for sid in chain if self.registry.get(sid)
        )
        avg_quality = sum(
            self.registry.get(sid).quality_score
            for sid in chain if self.registry.get(sid)
        ) / max(len(chain), 1)

        return CompositionPlan(
            plan_id=plan_id,
            modules=chain,
            expected_outputs=required_outputs,
            estimated_cost=total_cost,
            estimated_latency_ms=total_latency,
            quality_score=avg_quality,
            pattern=CompositionPattern.SEQUENTIAL,
            metadata={"satisfied_outputs": list(satisfied), "remaining_needs": list(needed)},
        )

    def _compose_parallel(
        self,
        required_outputs: list[str],
        context: dict[str, float],
        max_skills: int,
    ) -> CompositionPlan:
        """Build a parallel composition with fan-out/fan-in."""
        needed = set(required_outputs)
        selected: list[str] = []
        used: set[str] = set()

        for output_name in required_outputs:
            if len(selected) >= max_skills:
                break
            producers = self.registry.find_by_output(output_name)
            for skill in producers:
                if skill.skill_id not in used and skill.metadata.status == SkillStatus.ACTIVE:
                    selected.append(skill.skill_id)
                    used.add(skill.skill_id)
                    break

        total_cost = sum(
            self.registry.get(sid).estimated_cost
            for sid in selected if self.registry.get(sid)
        )
        max_latency = max(
            (self.registry.get(sid).avg_latency_ms for sid in selected if self.registry.get(sid)),
            default=0,
        )
        avg_quality = sum(
            self.registry.get(sid).quality_score
            for sid in selected if self.registry.get(sid)
        ) / max(len(selected), 1)

        return CompositionPlan(
            plan_id=f"par_{int(time.time() * 1000)}",
            modules=selected,
            expected_outputs=required_outputs,
            estimated_cost=total_cost,
            estimated_latency_ms=max_latency,
            quality_score=avg_quality,
            pattern=CompositionPattern.PARALLEL,
        )

    def _compose_fanout(
        self,
        required_outputs: list[str],
        context: dict[str, float],
        max_skills: int,
    ) -> CompositionPlan:
        """Build a fan-out composition (one skill feeds many)."""
        # Find a single source skill that covers many outputs
        candidates = self.registry.find_by_capability(
            required_inputs=set(),
            required_outputs=set(required_outputs),
        )
        if not candidates:
            return self._compose_parallel(required_outputs, context, max_skills)

        best = max(candidates, key=lambda s: s.quality_score)
        return CompositionPlan(
            plan_id=f"fan_{int(time.time() * 1000)}",
            modules=[best.skill_id],
            expected_outputs=required_outputs,
            estimated_cost=best.estimated_cost,
            estimated_latency_ms=best.avg_latency_ms,
            quality_score=best.quality_score,
            pattern=CompositionPattern.FANOUT,
        )

    def _record_plan(self, plan: CompositionPlan) -> None:
        """Store a composition plan for reference."""
        self._active_plans[plan.plan_id] = plan
        self._plan_history.append(plan)

    # ── Plan management ────────────────────────────────────────────────

    def get_plan(self, plan_id: str) -> Optional[CompositionPlan]:
        """Retrieve a composition plan by ID."""
        return self._active_plans.get(plan_id)

    def validate_plan(self, plan: CompositionPlan) -> tuple[bool, list[str]]:
        """Validate a composition plan for correctness.

        Returns:
            Tuple of (is_valid, list_of_issues).
        """
        issues: list[str] = []

        if not plan.modules:
            issues.append("Plan has no modules")

        for i, sid in enumerate(plan.modules):
            skill = self.registry.get(sid)
            if skill is None:
                issues.append(f"Module {i}: skill '{sid}' not found")
                continue

            # Check for conflicts with other modules
            for j, other_sid in enumerate(plan.modules):
                if i >= j:
                    continue
                other = self.registry.get(other_sid)
                if other and (
                    sid in other.conflicts or other_sid in skill.conflicts
                ):
                    issues.append(f"Conflict: {sid} <-> {other_sid}")

        return len(issues) == 0, issues

    @property
    def active_plan_count(self) -> int:
        """Number of active composition plans."""
        return len(self._active_plans)

    @property
    def summary(self) -> dict[str, Any]:
        """Get weaver summary."""
        return {
            "registry": self.registry.summary,
            "active_plans": self.active_plan_count,
            "total_plans_executed": len(self._plan_history),
            "task_type_patterns": {k: v.name for k, v in self._task_type_patterns.items()},
        }
