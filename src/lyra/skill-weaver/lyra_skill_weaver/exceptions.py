"""Custom exceptions for the skill weaver package."""

from __future__ import annotations


class SkillWeaverError(Exception):
    """Base exception for all skill weaver errors."""


class SkillNotFoundError(SkillWeaverError):
    """Raised when a required skill is not found in the registry."""

    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id
        super().__init__(f"Skill '{skill_id}' not found in registry")


class SkillConflictError(SkillWeaverError):
    """Raised when two skills have incompatible requirements."""

    def __init__(self, skill_a: str, skill_b: str, reason: str) -> None:
        self.skill_a = skill_a
        self.skill_b = skill_b
        super().__init__(f"Conflict between '{skill_a}' and '{skill_b}': {reason}")


class CompositionError(SkillWeaverError):
    """Raised when skill composition fails."""

    def __init__(self, message: str, partial_plan: object | None = None) -> None:
        self.partial_plan = partial_plan
        super().__init__(f"Composition failed: {message}")


class CircularDependencyError(SkillWeaverError):
    """Raised when a circular dependency is detected in the skill graph."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        path = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {path}")


class DiscoveryError(SkillWeaverError):
    """Raised when skill discovery fails."""

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        super().__init__(f"Skill discovery failed for '{source}': {reason}")


class OptimizationError(SkillWeaverError):
    """Raised when composition optimization fails."""

    def __init__(self, composition_id: str, reason: str) -> None:
        self.composition_id = composition_id
        super().__init__(f"Optimization failed for composition '{composition_id}': {reason}")


class ValidationError(SkillWeaverError):
    """Raised when a skill or composition fails validation."""

    def __init__(self, entity: str, message: str) -> None:
        self.entity = entity
        super().__init__(f"Validation failed for '{entity}': {message}")
