"""Health check system for monitoring service health and diagnostics.

Provides comprehensive health checking:
- Individual health checks for components
- Health check registry and aggregation
- Readiness and liveness probes
- Diagnostic information collection
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from lyra_cli.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    message: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None

    def is_healthy(self) -> bool:
        """Check if status is healthy."""
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
            "duration_ms": self.duration_ms,
        }


class HealthCheck:
    """A health check for a system component.

    Health checks should be fast (<100ms) and not have side effects.
    """

    def __init__(
        self,
        name: str,
        check_func: Callable[[], HealthCheckResult],
        critical: bool = True,
        timeout_seconds: float = 5.0,
    ):
        """Initialize health check.

        Args:
            name: Health check name
            check_func: Function that performs the check
            critical: Whether this check is critical for overall health
            timeout_seconds: Maximum time allowed for check
        """
        self.name = name
        self.check_func = check_func
        self.critical = critical
        self.timeout_seconds = timeout_seconds
        self._last_result: Optional[HealthCheckResult] = None

    def execute(self) -> HealthCheckResult:
        """Execute the health check.

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            result = self.check_func()
            result.duration_ms = (time.time() - start_time) * 1000
            self._last_result = result
            return result
        except Exception as e:
            logger.error(f"Health check {self.name} failed: {e}")
            result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {e}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=(time.time() - start_time) * 1000,
            )
            self._last_result = result
            return result

    def get_last_result(self) -> Optional[HealthCheckResult]:
        """Get the last check result."""
        return self._last_result


class HealthCheckRegistry:
    """Registry for managing health checks.

    Features:
    - Register multiple health checks
    - Execute all checks
    - Aggregate results
    - Separate readiness and liveness checks
    """

    def __init__(self):
        """Initialize health check registry."""
        self._checks: Dict[str, HealthCheck] = {}
        self._readiness_checks: List[str] = []
        self._liveness_checks: List[str] = []

    def register(
        self,
        check: HealthCheck,
        readiness: bool = True,
        liveness: bool = True,
    ) -> None:
        """Register a health check.

        Args:
            check: Health check to register
            readiness: Include in readiness checks
            liveness: Include in liveness checks
        """
        self._checks[check.name] = check

        if readiness:
            self._readiness_checks.append(check.name)
        if liveness:
            self._liveness_checks.append(check.name)

        logger.debug(f"Registered health check: {check.name}")

    def register_simple(
        self,
        name: str,
        check_func: Callable[[], bool],
        critical: bool = True,
        readiness: bool = True,
        liveness: bool = True,
    ) -> None:
        """Register a simple boolean health check.

        Args:
            name: Check name
            check_func: Function returning True if healthy
            critical: Whether check is critical
            readiness: Include in readiness checks
            liveness: Include in liveness checks
        """
        def wrapped_check() -> HealthCheckResult:
            is_healthy = check_func()
            return HealthCheckResult(
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message=f"{name}: {'OK' if is_healthy else 'Failed'}",
            )

        check = HealthCheck(name, wrapped_check, critical)
        self.register(check, readiness, liveness)

    def check_all(self) -> Dict[str, HealthCheckResult]:
        """Execute all health checks.

        Returns:
            Dictionary of check results
        """
        results = {}
        for name, check in self._checks.items():
            results[name] = check.execute()
        return results

    def check_readiness(self) -> Dict[str, HealthCheckResult]:
        """Execute readiness checks.

        Readiness checks determine if the service is ready to accept traffic.

        Returns:
            Dictionary of check results
        """
        results = {}
        for name in self._readiness_checks:
            if name in self._checks:
                results[name] = self._checks[name].execute()
        return results

    def check_liveness(self) -> Dict[str, HealthCheckResult]:
        """Execute liveness checks.

        Liveness checks determine if the service is alive and should not be restarted.

        Returns:
            Dictionary of check results
        """
        results = {}
        for name in self._liveness_checks:
            if name in self._checks:
                results[name] = self._checks[name].execute()
        return results

    def get_overall_status(
        self,
        results: Optional[Dict[str, HealthCheckResult]] = None,
    ) -> HealthStatus:
        """Get overall health status from check results.

        Args:
            results: Check results (executes all checks if not provided)

        Returns:
            Overall health status
        """
        if results is None:
            results = self.check_all()

        if not results:
            return HealthStatus.UNKNOWN

        # Check critical checks first
        critical_checks = [
            name for name, check in self._checks.items()
            if check.critical and name in results
        ]

        for name in critical_checks:
            result = results[name]
            if result.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY

        # Check for degraded status
        for result in results.values():
            if result.status == HealthStatus.DEGRADED:
                return HealthStatus.DEGRADED
            if result.status == HealthStatus.UNHEALTHY:
                return HealthStatus.DEGRADED  # Non-critical unhealthy = degraded

        return HealthStatus.HEALTHY

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report.

        Returns:
            Health report with all check results and overall status
        """
        results = self.check_all()
        overall_status = self.get_overall_status(results)

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "checks": {
                name: result.to_dict()
                for name, result in results.items()
            },
            "summary": {
                "total": len(results),
                "healthy": sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY),
            },
        }

    def get_readiness_report(self) -> Dict[str, Any]:
        """Get readiness report.

        Returns:
            Readiness report
        """
        results = self.check_readiness()
        overall_status = self.get_overall_status(results)

        return {
            "ready": overall_status == HealthStatus.HEALTHY,
            "status": overall_status.value,
            "timestamp": time.time(),
            "checks": {
                name: result.to_dict()
                for name, result in results.items()
            },
        }

    def get_liveness_report(self) -> Dict[str, Any]:
        """Get liveness report.

        Returns:
            Liveness report
        """
        results = self.check_liveness()
        overall_status = self.get_overall_status(results)

        return {
            "alive": overall_status != HealthStatus.UNHEALTHY,
            "status": overall_status.value,
            "timestamp": time.time(),
            "checks": {
                name: result.to_dict()
                for name, result in results.items()
            },
        }


def create_default_health_checks() -> HealthCheckRegistry:
    """Create registry with default health checks.

    Returns:
        Health check registry with default checks
    """
    registry = HealthCheckRegistry()

    # System health check
    def check_system() -> HealthCheckResult:
        """Check basic system health."""
        import psutil

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            status = HealthStatus.HEALTHY
            message = "System healthy"

            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent:.1f}%"
            elif cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High CPU usage: {cpu_percent:.1f}%"

            return HealthCheckResult(
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / (1024 * 1024),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Could not check system health: {e}",
            )

    registry.register(
        HealthCheck("system", check_system, critical=False),
        readiness=True,
        liveness=True,
    )

    # Disk space check
    def check_disk() -> HealthCheckResult:
        """Check disk space."""
        import psutil

        try:
            disk = psutil.disk_usage("/")
            status = HealthStatus.HEALTHY
            message = "Disk space OK"

            if disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk space: {disk.percent:.1f}% used"
            elif disk.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Low disk space: {disk.percent:.1f}% used"

            return HealthCheckResult(
                status=status,
                message=message,
                details={
                    "percent_used": disk.percent,
                    "free_gb": disk.free / (1024 ** 3),
                    "total_gb": disk.total / (1024 ** 3),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Could not check disk space: {e}",
            )

    registry.register(
        HealthCheck("disk", check_disk, critical=False),
        readiness=True,
        liveness=False,
    )

    return registry


__all__ = [
    "HealthStatus",
    "HealthCheckResult",
    "HealthCheck",
    "HealthCheckRegistry",
    "create_default_health_checks",
]
