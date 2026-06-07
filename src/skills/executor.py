"""
Skill executor — load skills by trigger, execute them with an agent loop,
and support skill chaining.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from .registry import CycleError, SkillRegistry
from .skill import Skill


class ExecutionStatus(str, Enum):
    """Status of a skill execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionResult:
    """Result of a single skill execution."""

    skill_name: str
    status: ExecutionStatus
    output: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    triggered_by: str | None = None
    chained_from: str | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_name": self.skill_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "triggered_by": self.triggered_by,
            "chained_from": self.chained_from,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionPlan:
    """Plan describing which skills to execute and in what order."""

    skills: list[Skill] = field(default_factory=list)
    order: list[str] = field(default_factory=list)
    results: dict[str, ExecutionResult] = field(default_factory=dict)
    chain_depth: int = 0

    @property
    def succeeded(self) -> bool:
        """True if all skills in the plan succeeded."""
        return all(
            r.status == ExecutionStatus.SUCCESS for r in self.results.values()
        )

    @property
    def summary(self) -> dict[str, Any]:
        """Return a concise execution summary."""
        statuses = [r.status.value for r in self.results.values()]
        return {
            "total": len(self.order),
            "succeeded": statuses.count("success"),
            "failed": statuses.count("failed"),
            "skipped": statuses.count("skipped"),
            "pending": statuses.count("pending"),
        }


SkillHook = Callable[[Skill, ExecutionResult], ExecutionResult]
"""
Type alias for before/after execution hooks.

A hook receives the Skill being executed and the current ExecutionResult,
and should return a (possibly modified) ExecutionResult.
"""


class SkillExecutor:
    """
    Load skills by trigger pattern and execute them with an agent loop.

    Supports:
    * Matching skills against trigger text
    * Executing skills in topological order (dependencies first)
    * Skill chaining — running dependent skills after a skill succeeds
    * Before/after hooks for custom instrumentation
    """

    def __init__(
        self,
        registry: SkillRegistry,
        execute_skill_fn: Callable[[Skill], str] | None = None,
    ):
        """
        Args:
            registry: SkillRegistry to look up skills from.
            execute_skill_fn: Optional callable that actually runs a skill
                (e.g., sends the skill content to an LLM agent). Defaults
                to a simple pass-through that returns the skill content.
        """
        self.registry = registry
        self._execute_fn = execute_skill_fn or self._default_execute
        self._before_hooks: list[SkillHook] = []
        self._after_hooks: list[SkillHook] = []
        self._history: list[ExecutionPlan] = []

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def add_before_hook(self, hook: SkillHook) -> None:
        """Register a hook called *before* each skill executes."""
        self._before_hooks.append(hook)

    def add_after_hook(self, hook: SkillHook) -> None:
        """Register a hook called *after* each skill executes."""
        self._after_hooks.append(hook)

    # ------------------------------------------------------------------
    # Trigger matching
    # ------------------------------------------------------------------

    def find_skills(self, text: str) -> list[Skill]:
        """
        Find skills whose triggers match *text*, sorted by match score.
        """
        results = self.registry.find_by_trigger(text)
        return [r.skill for r in results]

    def find_best_skill(self, text: str) -> Skill | None:
        """
        Return the single best-matching skill, or None.
        """
        skills = self.find_skills(text)
        return skills[0] if skills else None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        skill_name: str,
        trigger_text: str | None = None,
        chain: bool = False,
        max_chain_depth: int = 3,
    ) -> ExecutionPlan:
        """
        Execute a skill and (optionally) its dependent skills.

        Args:
            skill_name: Name of the skill to execute.
            trigger_text: Original trigger text (for logging / hooks).
            chain: If True, also execute skills that depend on this one.
            max_chain_depth: Maximum depth for chaining.

        Returns:
            ExecutionPlan containing all results.
        """
        plan = ExecutionPlan()

        if skill_name not in self.registry.skills:
            plan.results[skill_name] = ExecutionResult(
                skill_name=skill_name,
                status=ExecutionStatus.FAILED,
                error=f"Skill '{skill_name}' not found in registry",
            )
            return plan

        # Determine execution order
        try:
            order = self._resolve_order(skill_name, chain)
        except CycleError as e:
            skill = self.registry.get(skill_name)
            plan.results[skill_name] = ExecutionResult(
                skill_name=skill_name,
                status=ExecutionStatus.FAILED,
                error=f"Dependency cycle detected: {e}",
            )
            return plan

        plan.order = order
        plan.chain_depth = self._compute_chain_depth(order, skill_name)

        # Cap chain depth
        if plan.chain_depth > max_chain_depth:
            plan.order = self._slice_to_depth(order, skill_name, max_chain_depth)

        # Execute in topological order
        prev_skill: str | None = None
        for name in plan.order:
            skill = self.registry.get(name)
            if skill is None:
                plan.results[name] = ExecutionResult(
                    skill_name=name,
                    status=ExecutionStatus.SKIPPED,
                    error=f"Skill '{name}' not found in registry during execution",
                    chained_from=prev_skill,
                )
                continue

            # If a dependency failed, skip dependents
            if self._should_skip(name, plan):
                plan.results[name] = ExecutionResult(
                    skill_name=name,
                    status=ExecutionStatus.SKIPPED,
                    output="Skipped because a dependency failed",
                    chained_from=prev_skill,
                )
                continue

            result = ExecutionResult(
                skill_name=name,
                status=ExecutionStatus.PENDING,
                triggered_by=trigger_text,
                chained_from=prev_skill,
            )

            # Before hooks
            for hook in self._before_hooks:
                result = hook(skill, result)

            # Execute
            result.status = ExecutionStatus.RUNNING
            start = datetime.now()
            try:
                output = self._execute_fn(skill)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                result.status = ExecutionStatus.SUCCESS
                result.output = output
                result.duration_ms = elapsed
            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds() * 1000
                result.status = ExecutionStatus.FAILED
                result.error = str(e)
                result.duration_ms = elapsed

            # After hooks
            for hook in self._after_hooks:
                result = hook(skill, result)

            plan.results[name] = result
            prev_skill = name

        self._history.append(plan)
        return plan

    def execute_multi(
        self,
        texts: list[str],
        chain: bool = False,
        max_chain_depth: int = 3,
    ) -> list[ExecutionPlan]:
        """
        Execute skills matching multiple trigger texts.

        Returns a list of ExecutionPlans, one per text.
        """
        plans: list[ExecutionPlan] = []
        seen: set[str] = set()

        for text in texts:
            skill = self.find_best_skill(text)
            if skill and skill.name not in seen:
                plan = self.execute(
                    skill.name,
                    trigger_text=text,
                    chain=chain,
                    max_chain_depth=max_chain_depth,
                )
                plans.append(plan)
                seen.add(skill.name)

        return plans

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[ExecutionPlan]:
        """Return all execution plans so far."""
        return list(self._history)

    def last_execution(self) -> ExecutionPlan | None:
        """Return the most recent execution plan."""
        return self._history[-1] if self._history else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_execute(skill: Skill) -> str:
        """Pass-through execution: just return the skill content."""
        return skill.content

    def _resolve_order(self, skill_name: str, chain: bool) -> list[str]:
        """
        Resolve the topological execution order.

        If *chain* is False, only return the single skill name.
        Otherwise, return the skill together with all its transitive
        dependencies, ordered so that dependencies come first.
        """
        if not chain:
            return [skill_name]

        # Collect the transitive dependencies of skill_name
        all_needed = self._collect_dependencies(skill_name)
        all_needed.add(skill_name)

        # Get topological order from registry
        try:
            full_order = self.registry.get_execution_order()
        except CycleError:
            raise

        return [n for n in full_order if n in all_needed]

    def _compute_chain_depth(self, order: list[str], root: str) -> int:
        """Compute depth of the chain starting from *root*."""
        try:
            return len(order)
        except ValueError:
            return 0

    @staticmethod
    def _slice_to_depth(
        order: list[str], root: str, max_depth: int
    ) -> list[str]:
        """Keep at most *max_depth* items, keeping the root and its nearest deps."""
        # Topological order puts deps first, root last.
        # We want the root and its closest dependencies, i.e. the last max_depth items.
        if max_depth >= len(order):
            return order
        return order[-max_depth:]

    def _should_skip(self, skill_name: str, plan: ExecutionPlan) -> bool:
        """
        Return True if any dependency of *skill_name* has failed.
        """
        deps = self.registry.graph.dependencies(skill_name)
        for dep_name in deps:
            result = plan.results.get(dep_name)
            if result and result.status == ExecutionStatus.FAILED:
                return True
        return False

    def _collect_dependents(self, skill_name: str) -> set[str]:
        """Return all transitive dependents of a skill."""
        visited: set[str] = set()
        queue: list[str] = [skill_name]
        while queue:
            current = queue.pop(0)
            for dep in self.registry.graph.dependents(current):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        return visited

    def _collect_dependencies(self, skill_name: str) -> set[str]:
        """Return all transitive dependencies of a skill."""
        visited: set[str] = set()
        queue: list[str] = [skill_name]
        while queue:
            current = queue.pop(0)
            for dep in self.registry.graph.dependencies(current):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        return visited
