"""
Split-View Monitoring Dashboard for Real-Time Agent Observation.

Provides real-time monitoring of agent operations with metrics and visualizations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import deque


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class TimeSeriesMetric:
    """A time series metric."""

    name: str
    description: str
    unit: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a data point."""
        point = MetricPoint(
            timestamp=datetime.now().isoformat(),
            value=value,
            labels=labels or {},
        )
        self.points.append(point)

    def get_latest(self) -> Optional[float]:
        """Get latest value."""
        if not self.points:
            return None
        return self.points[-1].value

    def get_average(self, last_n: Optional[int] = None) -> Optional[float]:
        """Get average value."""
        if not self.points:
            return None

        points_to_avg = list(self.points)
        if last_n:
            points_to_avg = points_to_avg[-last_n:]

        return sum(p.value for p in points_to_avg) / len(points_to_avg)


@dataclass
class AgentStatus:
    """Current status of an agent."""

    agent_id: str
    status: str  # idle, active, error
    current_task: Optional[str]
    tasks_completed: int
    tasks_failed: int
    uptime_seconds: float
    last_activity: str


@dataclass
class SystemHealth:
    """Overall system health metrics."""

    status: str  # healthy, degraded, unhealthy
    active_agents: int
    total_tasks: int
    success_rate: float
    avg_response_time_ms: float
    error_count: int
    warnings: List[str] = field(default_factory=list)


class MonitoringDashboard:
    """
    Split-view monitoring dashboard for real-time observation.

    Features:
    - Real-time metrics collection
    - Agent status tracking
    - System health monitoring
    - Time series data
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history

        # Metrics
        self.metrics: Dict[str, TimeSeriesMetric] = {}

        # Agent statuses
        self.agent_statuses: Dict[str, AgentStatus] = {}

        # System health
        self.system_health = SystemHealth(
            status="healthy",
            active_agents=0,
            total_tasks=0,
            success_rate=1.0,
            avg_response_time_ms=0.0,
            error_count=0,
        )

        # Initialize default metrics
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize default metrics."""
        self.register_metric(
            "agent.tasks.completed",
            "Number of completed tasks",
            "count"
        )
        self.register_metric(
            "agent.tasks.failed",
            "Number of failed tasks",
            "count"
        )
        self.register_metric(
            "agent.response_time",
            "Agent response time",
            "ms"
        )
        self.register_metric(
            "system.active_agents",
            "Number of active agents",
            "count"
        )
        self.register_metric(
            "system.error_rate",
            "System error rate",
            "percent"
        )

    def register_metric(self, name: str, description: str, unit: str):
        """
        Register a new metric.

        Args:
            name: Metric name
            description: Metric description
            unit: Metric unit
        """
        if name not in self.metrics:
            self.metrics[name] = TimeSeriesMetric(
                name=name,
                description=description,
                unit=unit,
            )

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels
        """
        if name not in self.metrics:
            return

        self.metrics[name].add_point(value, labels)

    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        current_task: Optional[str] = None,
        tasks_completed: Optional[int] = None,
        tasks_failed: Optional[int] = None
    ):
        """
        Update agent status.

        Args:
            agent_id: Agent identifier
            status: Agent status
            current_task: Current task description
            tasks_completed: Number of completed tasks
            tasks_failed: Number of failed tasks
        """
        if agent_id not in self.agent_statuses:
            self.agent_statuses[agent_id] = AgentStatus(
                agent_id=agent_id,
                status=status,
                current_task=current_task,
                tasks_completed=0,
                tasks_failed=0,
                uptime_seconds=0.0,
                last_activity=datetime.now().isoformat(),
            )

        agent_status = self.agent_statuses[agent_id]
        agent_status.status = status
        agent_status.current_task = current_task
        agent_status.last_activity = datetime.now().isoformat()

        if tasks_completed is not None:
            agent_status.tasks_completed = tasks_completed

        if tasks_failed is not None:
            agent_status.tasks_failed = tasks_failed

    def update_system_health(self):
        """Update overall system health."""
        # Count active agents
        active_agents = sum(
            1 for status in self.agent_statuses.values()
            if status.status == "active"
        )

        # Calculate success rate
        total_completed = sum(s.tasks_completed for s in self.agent_statuses.values())
        total_failed = sum(s.tasks_failed for s in self.agent_statuses.values())
        total_tasks = total_completed + total_failed

        success_rate = (
            total_completed / total_tasks
            if total_tasks > 0
            else 1.0
        )

        # Get average response time
        response_time_metric = self.metrics.get("agent.response_time")
        avg_response_time = (
            response_time_metric.get_average(last_n=100)
            if response_time_metric
            else 0.0
        ) or 0.0

        # Count errors
        error_count = total_failed

        # Determine health status
        if success_rate < 0.5 or error_count > 10:
            health_status = "unhealthy"
        elif success_rate < 0.8 or error_count > 5:
            health_status = "degraded"
        else:
            health_status = "healthy"

        # Generate warnings
        warnings = []
        if success_rate < 0.8:
            warnings.append(f"Low success rate: {success_rate:.1%}")
        if error_count > 5:
            warnings.append(f"High error count: {error_count}")
        if avg_response_time > 1000:
            warnings.append(f"High response time: {avg_response_time:.0f}ms")

        # Update system health
        self.system_health = SystemHealth(
            status=health_status,
            active_agents=active_agents,
            total_tasks=total_tasks,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            error_count=error_count,
            warnings=warnings,
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get complete dashboard data.

        Returns:
            Dashboard data including metrics, agent statuses, and system health
        """
        # Update system health before returning
        self.update_system_health()

        return {
            "system_health": {
                "status": self.system_health.status,
                "active_agents": self.system_health.active_agents,
                "total_tasks": self.system_health.total_tasks,
                "success_rate": self.system_health.success_rate,
                "avg_response_time_ms": self.system_health.avg_response_time_ms,
                "error_count": self.system_health.error_count,
                "warnings": self.system_health.warnings,
            },
            "agents": {
                agent_id: {
                    "status": status.status,
                    "current_task": status.current_task,
                    "tasks_completed": status.tasks_completed,
                    "tasks_failed": status.tasks_failed,
                    "last_activity": status.last_activity,
                }
                for agent_id, status in self.agent_statuses.items()
            },
            "metrics": {
                name: {
                    "description": metric.description,
                    "unit": metric.unit,
                    "latest": metric.get_latest(),
                    "average": metric.get_average(last_n=100),
                    "data_points": len(metric.points),
                }
                for name, metric in self.metrics.items()
            },
        }

    def get_metric_history(
        self,
        metric_name: str,
        last_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get metric history.

        Args:
            metric_name: Metric name
            last_n: Number of recent points to return

        Returns:
            List of metric points
        """
        if metric_name not in self.metrics:
            return []

        metric = self.metrics[metric_name]
        points = list(metric.points)

        if last_n:
            points = points[-last_n:]

        return [
            {
                "timestamp": point.timestamp,
                "value": point.value,
                "labels": point.labels,
            }
            for point in points
        ]

    def get_agent_summary(self) -> Dict[str, Any]:
        """Get summary of all agents."""
        return {
            "total_agents": len(self.agent_statuses),
            "active_agents": sum(
                1 for s in self.agent_statuses.values()
                if s.status == "active"
            ),
            "idle_agents": sum(
                1 for s in self.agent_statuses.values()
                if s.status == "idle"
            ),
            "error_agents": sum(
                1 for s in self.agent_statuses.values()
                if s.status == "error"
            ),
        }
