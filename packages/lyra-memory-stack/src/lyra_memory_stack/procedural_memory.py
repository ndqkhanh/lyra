"""L3 Procedural Memory — Skills, workflows, and knowledge graph for agent procedures.

Stores agent skills (reusable capabilities), workflow templates with
dependency graphs, and a lightweight knowledge graph with temporal
validity windows.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from lyra_memory_stack.exceptions import MemoryNotFoundError


@dataclass(frozen=True)
class Skill:
    """A reusable agent skill with trigger conditions."""

    skill_id: str
    name: str
    description: str
    triggers: tuple[str, ...] = ()
    content: str = ""
    version: str = "1.0.0"
    domain: str = "general"
    author: str = "agent"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_version(self, new_version: str) -> Skill:
        """Return a new Skill with an updated version (immutable)."""
        return Skill(
            skill_id=self.skill_id,
            name=self.name,
            description=self.description,
            triggers=self.triggers,
            content=self.content,
            version=new_version,
            domain=self.domain,
            author=self.author,
            timestamp=time.time(),
            metadata=self.metadata,
        )

    def with_content(self, new_content: str) -> Skill:
        """Return a new Skill with updated content (immutable)."""
        return Skill(
            skill_id=self.skill_id,
            name=self.name,
            description=self.description,
            triggers=self.triggers,
            content=new_content,
            version=self.version,
            domain=self.domain,
            author=self.author,
            timestamp=time.time(),
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class WorkflowStep:
    """A single step in a workflow template."""

    step_id: str
    name: str
    description: str = ""
    depends_on: tuple[str, ...] = ()  # step_ids this step depends on
    skill_ref: str | None = None  # skill_id to invoke
    timeout_seconds: float = 300.0
    retry_count: int = 3


@dataclass(frozen=True)
class WorkflowTemplate:
    """A reusable workflow template with dependency DAG."""

    workflow_id: str
    name: str
    description: str = ""
    steps: tuple[WorkflowStep, ...] = ()
    domain: str = "general"
    version: str = "1.0.0"
    timestamp: float = field(default_factory=time.time)

    def dependency_graph(self) -> dict[str, list[str]]:
        """Build adjacency list of step dependencies.

        Returns dict mapping step_id -> list of step_ids that depend on it.
        """
        graph: dict[str, list[str]] = {s.step_id: [] for s in self.steps}
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id in graph:
                    graph[dep_id].append(step.step_id)
        return graph

    def execution_order(self) -> list[WorkflowStep]:
        """Return steps in topological order (dependencies first)."""
        visited: set[str] = set()
        result: list[WorkflowStep] = []
        steps_map = {s.step_id: s for s in self.steps}

        def _visit(step_id: str) -> None:
            if step_id in visited:
                return
            visited.add(step_id)
            step = steps_map.get(step_id)
            if step is not None:
                for dep_id in step.depends_on:
                    _visit(dep_id)
                result.append(step)

        for step in self.steps:
            _visit(step.step_id)

        return result

    def validate(self) -> list[str]:
        """Validate the workflow. Returns list of error messages (empty = valid)."""
        errors: list[str] = []
        step_ids = {s.step_id for s in self.steps}
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    errors.append(
                        f"Step '{step.step_id}' depends on unknown step '{dep_id}'"
                    )
        return errors


@dataclass(frozen=True)
class KnowledgeEdge:
    """An edge in the procedural knowledge graph."""

    edge_id: str
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    valid_from: float = 0.0
    valid_until: float = float("inf")
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_valid(self, at_time: float | None = None) -> bool:
        """Check whether this edge is temporally valid."""
        t = at_time if at_time is not None else time.time()
        return self.valid_from <= t <= self.valid_until


class ProceduralMemory:
    """Manages skills, workflows, and knowledge graph for agent procedures."""

    _skills: dict[str, Skill]
    _workflows: dict[str, WorkflowTemplate]
    _kg_edges: dict[str, KnowledgeEdge]

    def __init__(self) -> None:
        self._skills = {}
        self._workflows = {}
        self._kg_edges = {}

    # ── Skills ──────────────────────────────────────────────────────────

    def store_skill(self, skill: Skill) -> str:
        """Store a skill. Returns the skill_id."""
        self._skills[skill.skill_id] = skill
        return skill.skill_id

    def load_skill(self, skill_id: str) -> Skill:
        """Load a skill by ID. Raises MemoryNotFoundError if missing."""
        skill = self._skills.get(skill_id)
        if skill is None:
            raise MemoryNotFoundError(skill_id, "procedural/skill")
        return skill

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill by ID. Returns True if deleted."""
        return self._skills.pop(skill_id, None) is not None

    def list_skills(self, domain: str | None = None) -> list[Skill]:
        """List all skills, optionally filtered by domain."""
        if domain is None:
            return list(self._skills.values())
        return [s for s in self._skills.values() if s.domain == domain]

    def find_skills_by_trigger(self, trigger: str) -> list[Skill]:
        """Find skills whose trigger patterns match the given input."""
        trigger_lower = trigger.lower()
        return [
            s for s in self._skills.values()
            if any(trigger_lower in t.lower() for t in s.triggers)
        ]

    def skill_count(self) -> int:
        """Number of stored skills."""
        return len(self._skills)

    # ── Workflows ───────────────────────────────────────────────────────

    def store_workflow(self, workflow: WorkflowTemplate) -> str:
        """Store a workflow template. Returns the workflow_id."""
        self._workflows[workflow.workflow_id] = workflow
        return workflow.workflow_id

    def load_workflow(self, workflow_id: str) -> WorkflowTemplate:
        """Load a workflow by ID. Raises MemoryNotFoundError if missing."""
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise MemoryNotFoundError(workflow_id, "procedural/workflow")
        return wf

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow by ID. Returns True if deleted."""
        return self._workflows.pop(workflow_id, None) is not None

    def list_workflows(self, domain: str | None = None) -> list[WorkflowTemplate]:
        """List all workflows, optionally filtered by domain."""
        if domain is None:
            return list(self._workflows.values())
        return [w for w in self._workflows.values() if w.domain == domain]

    def workflow_count(self) -> int:
        """Number of stored workflows."""
        return len(self._workflows)

    # ── Knowledge Graph ────────────────────────────────────────────────

    def add_edge(self, edge: KnowledgeEdge) -> str:
        """Add a knowledge graph edge. Returns the edge_id."""
        self._kg_edges[edge.edge_id] = edge
        return edge.edge_id

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge by ID. Returns True if removed."""
        return self._kg_edges.pop(edge_id, None) is not None

    def query_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        relation: str | None = None,
        valid_at: float | None = None,
    ) -> list[KnowledgeEdge]:
        """Query knowledge graph edges with optional filters."""
        results = list(self._kg_edges.values())

        if source_id is not None:
            results = [e for e in results if e.source_id == source_id]
        if target_id is not None:
            results = [e for e in results if e.target_id == target_id]
        if relation is not None:
            results = [e for e in results if e.relation == relation]
        if valid_at is not None:
            results = [e for e in results if e.is_valid(valid_at)]

        return results

    def edge_count(self) -> int:
        """Number of stored knowledge graph edges."""
        return len(self._kg_edges)

    # ── General ─────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all procedural memory."""
        self._skills.clear()
        self._workflows.clear()
        self._kg_edges.clear()

    def summary(self) -> dict[str, Any]:
        """Produce a summary of procedural memory state."""
        return {
            "skills": self.skill_count(),
            "workflows": self.workflow_count(),
            "knowledge_edges": self.edge_count(),
        }
