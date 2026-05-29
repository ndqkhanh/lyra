"""
Cell-based deployment with Galileo circuit breakers.

Manages isolated deployment cells with independent lifecycle,
health monitoring, and circuit breaker patterns to prevent
cascade failures across the deployment fleet.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock

from lyra_production.models import (
    CellStatus,
    CircuitBreakerState,
    DeploymentCell,
    DeploymentConfig,
    HealthStatus,
)

logger = logging.getLogger(__name__)

# Type alias for health check callables
HealthCheckFn = Callable[[str], HealthStatus]


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a cell's circuit breaker is open and rejecting traffic."""


class CellNotFoundError(KeyError):
    """Raised when a requested cell does not exist."""


class CellManager:
    """Manages the lifecycle and health of deployment cells.

    Each cell is an independently deployable unit with its own
    circuit breaker, health monitoring, and scaling configuration.
    """

    def __init__(
        self,
        health_check_fn: HealthCheckFn | None = None,
        default_config: DeploymentConfig | None = None,
    ) -> None:
        self._cells: dict[str, DeploymentCell] = {}
        self._lock = Lock()
        self._health_check_fn = health_check_fn or self._default_health_check
        self._default_config = default_config or DeploymentConfig()

    def _default_health_check(self, cell_id: str) -> HealthStatus:
        """Default health check that always returns healthy."""
        return HealthStatus.HEALTHY

    def deploy_cell(
        self,
        version: str,
        config: DeploymentConfig | None = None,
    ) -> DeploymentCell:
        """Deploy a new cell with the given version and configuration.

        Args:
            version: Software version to deploy.
            config: Optional deployment configuration.

        Returns:
            The newly created DeploymentCell.
        """
        cell_id = f"cell-{uuid.uuid4().hex[:12]}"
        resolved_config = config or self._default_config

        cell = DeploymentCell(
            cell_id=cell_id,
            version=version,
            status=CellStatus.ACTIVE,
            health=HealthStatus.UNKNOWN,
            circuit_state=CircuitBreakerState.CLOSED,
            config=resolved_config,
            failure_count=0,
            created_at=datetime.now(timezone.utc),
            last_health_check=None,
        )

        with self._lock:
            self._cells[cell_id] = cell

        logger.info("Deployed cell %s version %s", cell_id, version)
        return cell

    def health_check(self, cell_id: str) -> HealthStatus:
        """Run a health check on a specific cell.

        Automatically opens the circuit breaker if the failure
        threshold is exceeded.

        Args:
            cell_id: The cell to check.

        Returns:
            The cell's current HealthStatus.

        Raises:
            CellNotFoundError: If the cell does not exist.
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                raise CellNotFoundError(f"Cell not found: {cell_id}")

            health = self._health_check_fn(cell_id)
            now = datetime.now(timezone.utc)

            if health == HealthStatus.HEALTHY:
                failure_count = 0
                circuit_state = CircuitBreakerState.CLOSED
            elif health == HealthStatus.UNHEALTHY:
                failure_count = cell.failure_count + 1
                threshold = cell.config.circuit_breaker_threshold
                if failure_count >= threshold:
                    circuit_state = CircuitBreakerState.OPEN
                    logger.warning(
                        "Circuit breaker OPEN for cell %s (%d failures)",
                        cell_id,
                        failure_count,
                    )
                else:
                    circuit_state = cell.circuit_state
            else:
                failure_count = cell.failure_count
                circuit_state = cell.circuit_state

            updated = DeploymentCell(
                cell_id=cell.cell_id,
                version=cell.version,
                status=cell.status,
                health=health,
                circuit_state=circuit_state,
                config=cell.config,
                failure_count=failure_count,
                created_at=cell.created_at,
                last_health_check=now,
            )
            self._cells[cell_id] = updated

        return health

    def toggle_circuit_breaker(
        self,
        cell_id: str,
        state: CircuitBreakerState,
    ) -> DeploymentCell:
        """Manually override the circuit breaker state for a cell.

        Args:
            cell_id: The target cell.
            state: The desired circuit breaker state.

        Returns:
            The updated DeploymentCell.

        Raises:
            CellNotFoundError: If the cell does not exist.
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                raise CellNotFoundError(f"Cell not found: {cell_id}")

            updated = DeploymentCell(
                cell_id=cell.cell_id,
                version=cell.version,
                status=cell.status,
                health=cell.health,
                circuit_state=state,
                config=cell.config,
                failure_count=0 if state == CircuitBreakerState.CLOSED else cell.failure_count,
                created_at=cell.created_at,
                last_health_check=cell.last_health_check,
            )
            self._cells[cell_id] = updated

        logger.info("Circuit breaker for cell %s set to %s", cell_id, state.name)
        return updated

    def get_active_cells(self) -> list[DeploymentCell]:
        """Return all currently active cells.

        Active cells are those with status ACTIVE and circuit
        breaker in CLOSED or HALF_OPEN state.
        """
        with self._lock:
            return [
                c
                for c in self._cells.values()
                if c.status == CellStatus.ACTIVE
                and c.circuit_state != CircuitBreakerState.OPEN
            ]

    def failover(self, cell_id: str) -> DeploymentCell | None:
        """Fail over traffic from a cell to the next healthy cell.

        Marks the source cell as DRAINING and returns a healthy
        alternative if one exists.

        Args:
            cell_id: The cell to fail over from.

        Returns:
            A healthy deployment cell, or None if no alternative exists.

        Raises:
            CellNotFoundError: If the source cell does not exist.
        """
        with self._lock:
            source = self._cells.get(cell_id)
            if source is None:
                raise CellNotFoundError(f"Cell not found: {cell_id}")

            # Mark source as draining
            drained = DeploymentCell(
                cell_id=source.cell_id,
                version=source.version,
                status=CellStatus.DRAINING,
                health=source.health,
                circuit_state=source.circuit_state,
                config=source.config,
                failure_count=source.failure_count,
                created_at=source.created_at,
                last_health_check=source.last_health_check,
            )
            self._cells[cell_id] = drained

            # Find a healthy alternative
            alternatives = [
                c
                for c in self._cells.values()
                if c.cell_id != cell_id
                and c.status == CellStatus.ACTIVE
                and c.health == HealthStatus.HEALTHY
                and c.circuit_state == CircuitBreakerState.CLOSED
            ]

        target = alternatives[0] if alternatives else None
        if target:
            logger.info(
                "Failed over from cell %s to cell %s", cell_id, target.cell_id
            )
        else:
            logger.warning("No healthy alternative found for failover from %s", cell_id)

        return target

    def scale_cell(self, cell_id: str, replicas: int) -> DeploymentCell:
        """Adjust the replica count for a deployment cell.

        Args:
            cell_id: The target cell.
            replicas: The desired number of replicas.

        Returns:
            The updated DeploymentCell.

        Raises:
            CellNotFoundError: If the cell does not exist.
            ValueError: If replicas is less than 1.
        """
        if replicas < 1:
            raise ValueError("Replicas must be at least 1")

        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                raise CellNotFoundError(f"Cell not found: {cell_id}")

            new_config = DeploymentConfig(
                replicas=replicas,
                max_retries=cell.config.max_retries,
                health_check_interval_sec=cell.config.health_check_interval_sec,
                circuit_breaker_threshold=cell.config.circuit_breaker_threshold,
                circuit_breaker_timeout_sec=cell.config.circuit_breaker_timeout_sec,
                resources=cell.config.resources,
                labels=cell.config.labels,
                env_vars=cell.config.env_vars,
            )

            updated = DeploymentCell(
                cell_id=cell.cell_id,
                version=cell.version,
                status=cell.status,
                health=cell.health,
                circuit_state=cell.circuit_state,
                config=new_config,
                failure_count=cell.failure_count,
                created_at=cell.created_at,
                last_health_check=cell.last_health_check,
            )
            self._cells[cell_id] = updated

        logger.info("Scaled cell %s to %d replicas", cell_id, replicas)
        return updated

    def get_cell(self, cell_id: str) -> DeploymentCell:
        """Get a deployment cell by ID.

        Args:
            cell_id: The cell identifier.

        Returns:
            The DeploymentCell.

        Raises:
            CellNotFoundError: If the cell does not exist.
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                raise CellNotFoundError(f"Cell not found: {cell_id}")
            return cell

    def list_cells(self) -> list[DeploymentCell]:
        """Return all cells regardless of status."""
        with self._lock:
            return list(self._cells.values())

    def run_health_checks(self) -> dict[str, HealthStatus]:
        """Run health checks on all active cells.

        Returns:
            A mapping of cell_id to HealthStatus for all cells.
        """
        results: dict[str, HealthStatus] = {}
        with self._lock:
            cell_ids = [c.cell_id for c in self._cells.values()]

        for cid in cell_ids:
            try:
                results[cid] = self.health_check(cid)
            except Exception:
                logger.exception("Health check failed for cell %s", cid)
                results[cid] = HealthStatus.UNKNOWN

        return results

    def attempt_recovery(self, cell_id: str) -> HealthStatus:
        """Attempt to recover a cell by moving to HALF_OPEN state.

        If the cell's circuit breaker is OPEN, this transitions it
        to HALF_OPEN and runs a health check.

        Args:
            cell_id: The cell to attempt recovery on.

        Returns:
            The HealthStatus after recovery attempt.
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                raise CellNotFoundError(f"Cell not found: {cell_id}")

            if cell.circuit_state != CircuitBreakerState.OPEN:
                return cell.health

            half_open = DeploymentCell(
                cell_id=cell.cell_id,
                version=cell.version,
                status=cell.status,
                health=cell.health,
                circuit_state=CircuitBreakerState.HALF_OPEN,
                config=cell.config,
                failure_count=cell.failure_count,
                created_at=cell.created_at,
                last_health_check=cell.last_health_check,
            )
            self._cells[cell_id] = half_open

        logger.info("Attempting recovery for cell %s (HALF_OPEN)", cell_id)
        time.sleep(0.1)  # Brief delay before probing
        return self.health_check(cell_id)


__all__ = [
    "CircuitBreakerOpenError",
    "CellNotFoundError",
    "CellManager",
]
