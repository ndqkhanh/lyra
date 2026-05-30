"""Health Command — user-facing `/health` CLI command for component health checks.

Provides component registration, health status tracking, dependency
health scoring, and actionable recommendations for degraded systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DependencyStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: DependencyStatus
    message: str = ""
    last_checked: float = 0.0
    dependencies: tuple[str, ...] = ()

    @property
    def is_healthy(self) -> bool:
        return self.status == DependencyStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        return self.status == DependencyStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        return self.status in (DependencyStatus.UNHEALTHY, DependencyStatus.DEAD)


@dataclass(frozen=True)
class HealthScore:
    overall: float
    component_scores: dict[str, float] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.overall >= 0.75


class HealthCommand:
    """User-facing `/health` command for checking system component health.

    Tracks component status, computes aggregate health scores,
    and generates recommendations for unhealthy or degraded components.

    Usage::

        cmd = HealthCommand()
        cmd.register_component("router", status=DependencyStatus.HEALTHY)
        cmd.register_component("database", status=DependencyStatus.DEGRADED,
                               message="Connection pool at 90%")
        score = cmd.check_all()
        for rec in cmd.get_recommendations():
            print(rec)
    """

    _STATUS_WEIGHTS = {
        DependencyStatus.HEALTHY: 1.0,
        DependencyStatus.DEGRADED: 0.5,
        DependencyStatus.UNHEALTHY: 0.0,
        DependencyStatus.DEAD: 0.0,
        DependencyStatus.UNKNOWN: 0.25,
    }

    def __init__(self) -> None:
        self._components: dict[str, ComponentHealth] = {}

    @property
    def component_count(self) -> int:
        return len(self._components)

    def register_component(
        self,
        name: str,
        status: DependencyStatus = DependencyStatus.UNKNOWN,
        message: str = "",
        dependencies: tuple[str, ...] = (),
    ) -> ComponentHealth:
        import time

        c = ComponentHealth(
            name=name,
            status=status,
            message=message,
            last_checked=time.monotonic(),
            dependencies=dependencies,
        )
        self._components[name] = c
        return c

    def get_component(self, name: str) -> ComponentHealth | None:
        return self._components.get(name)

    def update_component(
        self,
        name: str,
        status: DependencyStatus | None = None,
        message: str | None = None,
    ) -> ComponentHealth | None:
        c = self._components.get(name)
        if c is None:
            return None
        import time

        new_c = ComponentHealth(
            name=c.name,
            status=status if status is not None else c.status,
            message=message if message is not None else c.message,
            last_checked=time.monotonic(),
            dependencies=c.dependencies,
        )
        self._components[name] = new_c
        return new_c

    def check_all(self) -> HealthScore:
        if not self._components:
            return HealthScore(overall=1.0, component_scores={})

        scores: dict[str, float] = {}
        for name, c in self._components.items():
            weight = self._STATUS_WEIGHTS.get(c.status, 0.0)
            # Penalize if dependencies are unhealthy
            if c.dependencies:
                dep_scores = []
                for dep in c.dependencies:
                    dep_c = self._components.get(dep)
                    if dep_c is not None:
                        dep_scores.append(
                            self._STATUS_WEIGHTS.get(dep_c.status, 0.0)
                        )
                if dep_scores:
                    dep_factor = sum(dep_scores) / len(dep_scores)
                    weight = weight * (0.7 + 0.3 * dep_factor)
            scores[name] = weight

        overall = sum(scores.values()) / len(scores) if scores else 1.0
        return HealthScore(overall=overall, component_scores=scores)

    def get_recommendations(self) -> list[str]:
        recs: list[str] = []
        for name, c in self._components.items():
            if c.status == DependencyStatus.DEAD:
                recs.append(f"CRITICAL: Component '{name}' is dead — restart required")
            elif c.status == DependencyStatus.UNHEALTHY:
                recs.append(
                    f"HIGH: Component '{name}' is unhealthy"
                    + (f" — {c.message}" if c.message else "")
                )
            elif c.status == DependencyStatus.DEGRADED:
                recs.append(
                    f"MEDIUM: Component '{name}' is degraded"
                    + (f" — {c.message}" if c.message else "")
                )
            elif c.status == DependencyStatus.UNKNOWN:
                recs.append(f"INFO: Component '{name}' status is unknown — run health check")
        return recs

    def reset(self) -> None:
        self._components.clear()
