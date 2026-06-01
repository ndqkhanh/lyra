"""Capacity Planner Skill — capacity planning and resource optimization validation.

Analyzes systems for:
- Resource utilization trends
- Growth projections and forecasting
- Scaling thresholds and triggers
- Cost optimization opportunities
- Performance bottlenecks
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapacitySeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CapacityCategory(StrEnum):
    UTILIZATION = "utilization"
    FORECASTING = "forecasting"
    SCALING = "scaling"
    COST = "cost"
    PERFORMANCE = "performance"


@dataclass(frozen=True)
class CapacityIssue:
    category: CapacityCategory
    severity: CapacitySeverity
    resource: str
    message: str
    suggestion: str


class CapacityPlannerSkill:
    """Validates capacity planning and resource optimization strategies."""

    def __init__(self) -> None:
        self._issues: list[CapacityIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run capacity planning analysis.

        Args:
            input_data: Dictionary with keys:
                - resources: List of resources with utilization data
                - growth_rate: Expected monthly growth rate (%)
                - current_capacity: Current capacity metrics
                - scaling_config: Auto-scaling configuration
                - cost_data: Cost and budget information

        Returns:
            Dictionary with analysis report data.
        """
        resources = input_data.get("resources", [])
        growth_rate = input_data.get("growth_rate", 0)
        current_capacity = input_data.get("current_capacity", {})
        scaling_config = input_data.get("scaling_config", {})
        cost_data = input_data.get("cost_data", {})

        self._issues.clear()

        self._check_utilization(resources)
        self._check_growth_forecasting(growth_rate, current_capacity)
        self._check_scaling_strategy(scaling_config, resources)
        self._check_cost_optimization(cost_data, resources)
        self._check_performance_headroom(resources)

        score = self._compute_score()

        return {
            "resources_analyzed": len(resources),
            "growth_rate": growth_rate,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
        }

    def _check_utilization(self, resources: list) -> None:
        """Check current resource utilization levels."""
        if not resources:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.UTILIZATION,
                    severity=CapacitySeverity.CRITICAL,
                    resource="all",
                    message="No resource utilization data provided",
                    suggestion="Collect utilization metrics for CPU, memory, disk, network",
                )
            )
            return

        for resource in resources:
            resource_name = resource.get("name", "unknown")
            resource_type = resource.get("type", "unknown")
            utilization = resource.get("utilization_percent", 0)
            peak_utilization = resource.get("peak_utilization_percent", utilization)

            # Check for over-utilization
            if utilization > 80:
                self._issues.append(
                    CapacityIssue(
                        category=CapacityCategory.UTILIZATION,
                        severity=CapacitySeverity.CRITICAL,
                        resource=resource_name,
                        message=f"{resource_type} at {utilization}% utilization - capacity exhaustion risk",
                        suggestion="Scale up immediately or optimize resource usage",
                    )
                )
            elif utilization > 70:
                self._issues.append(
                    CapacityIssue(
                        category=CapacityCategory.UTILIZATION,
                        severity=CapacitySeverity.HIGH,
                        resource=resource_name,
                        message=f"{resource_type} at {utilization}% utilization - approaching limits",
                        suggestion="Plan capacity increase within 2-4 weeks",
                    )
                )

            # Check for under-utilization (cost waste)
            if utilization < 20 and resource.get("is_production", True):
                self._issues.append(
                    CapacityIssue(
                        category=CapacityCategory.COST,
                        severity=CapacitySeverity.MEDIUM,
                        resource=resource_name,
                        message=f"{resource_type} at {utilization}% utilization - underutilized",
                        suggestion="Consider downsizing or consolidating resources",
                    )
                )

            # Check peak vs average utilization
            if peak_utilization > utilization * 2:
                self._issues.append(
                    CapacityIssue(
                        category=CapacityCategory.PERFORMANCE,
                        severity=CapacitySeverity.MEDIUM,
                        resource=resource_name,
                        message=f"High variance: peak {peak_utilization}% vs avg {utilization}%",
                        suggestion="Implement auto-scaling or load balancing for traffic spikes",
                    )
                )

    def _check_growth_forecasting(self, growth_rate: float, current_capacity: dict) -> None:
        """Check growth forecasting and capacity planning."""
        if growth_rate == 0:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.FORECASTING,
                    severity=CapacitySeverity.HIGH,
                    resource="forecasting",
                    message="No growth rate defined",
                    suggestion="Analyze historical data to project future capacity needs",
                )
            )
            return

        # Check if growth rate is tracked
        has_historical_data = current_capacity.get("has_historical_data", False)
        if not has_historical_data:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.FORECASTING,
                    severity=CapacitySeverity.MEDIUM,
                    resource="forecasting",
                    message="No historical data for trend analysis",
                    suggestion="Collect at least 3 months of historical data for accurate forecasting",
                )
            )

        # Check forecast horizon
        forecast_months = current_capacity.get("forecast_horizon_months", 0)
        if forecast_months < 6:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.FORECASTING,
                    severity=CapacitySeverity.MEDIUM,
                    resource="forecasting",
                    message=f"Short forecast horizon ({forecast_months} months)",
                    suggestion="Forecast at least 6-12 months ahead for capacity planning",
                )
            )

        # Check for seasonal patterns
        has_seasonality_analysis = current_capacity.get("has_seasonality_analysis", False)
        if not has_seasonality_analysis and growth_rate > 10:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.FORECASTING,
                    severity=CapacitySeverity.LOW,
                    resource="forecasting",
                    message="No seasonality analysis for high-growth system",
                    suggestion="Analyze seasonal patterns to avoid over/under-provisioning",
                )
            )

        # Check capacity runway
        months_until_exhaustion = current_capacity.get("months_until_exhaustion", 999)
        if months_until_exhaustion < 3:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.FORECASTING,
                    severity=CapacitySeverity.CRITICAL,
                    resource="capacity_runway",
                    message=f"Only {months_until_exhaustion} months of capacity remaining",
                    suggestion="Urgent: Plan capacity expansion immediately",
                )
            )
        elif months_until_exhaustion < 6:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.FORECASTING,
                    severity=CapacitySeverity.HIGH,
                    resource="capacity_runway",
                    message=f"{months_until_exhaustion} months of capacity remaining",
                    suggestion="Plan capacity expansion within next quarter",
                )
            )

    def _check_scaling_strategy(self, scaling_config: dict, resources: list) -> None:
        """Check auto-scaling and scaling strategy."""
        if not scaling_config:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.SCALING,
                    severity=CapacitySeverity.HIGH,
                    resource="scaling",
                    message="No scaling strategy defined",
                    suggestion="Implement auto-scaling or define manual scaling procedures",
                )
            )
            return

        # Check auto-scaling configuration
        has_auto_scaling = scaling_config.get("has_auto_scaling", False)
        if not has_auto_scaling:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.SCALING,
                    severity=CapacitySeverity.MEDIUM,
                    resource="scaling",
                    message="No auto-scaling configured",
                    suggestion="Enable auto-scaling for dynamic workloads",
                )
            )

        # Check scaling thresholds
        scale_up_threshold = scaling_config.get("scale_up_threshold_percent", 0)
        scale_down_threshold = scaling_config.get("scale_down_threshold_percent", 0)

        if scale_up_threshold > 80:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.SCALING,
                    severity=CapacitySeverity.HIGH,
                    resource="scaling",
                    message=f"Scale-up threshold too high ({scale_up_threshold}%)",
                    suggestion="Set scale-up threshold to 60-70% to avoid performance degradation",
                )
            )

        if scale_down_threshold > scale_up_threshold - 20:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.SCALING,
                    severity=CapacitySeverity.MEDIUM,
                    resource="scaling",
                    message="Insufficient gap between scale-up and scale-down thresholds",
                    suggestion="Maintain 20%+ gap to prevent scaling oscillation",
                )
            )

        # Check cooldown periods
        has_cooldown = scaling_config.get("has_cooldown_period", False)
        if has_auto_scaling and not has_cooldown:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.SCALING,
                    severity=CapacitySeverity.MEDIUM,
                    resource="scaling",
                    message="No cooldown period for auto-scaling",
                    suggestion="Add cooldown period to prevent rapid scaling oscillation",
                )
            )

        # Check max capacity limits
        has_max_limit = scaling_config.get("has_max_capacity_limit", False)
        if has_auto_scaling and not has_max_limit:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.COST,
                    severity=CapacitySeverity.HIGH,
                    resource="scaling",
                    message="No maximum capacity limit - runaway scaling risk",
                    suggestion="Set maximum capacity limit to prevent unexpected costs",
                )
            )

    def _check_cost_optimization(self, cost_data: dict, resources: list) -> None:
        """Check cost optimization opportunities."""
        if not cost_data:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.COST,
                    severity=CapacitySeverity.MEDIUM,
                    resource="cost",
                    message="No cost data available",
                    suggestion="Track infrastructure costs for optimization opportunities",
                )
            )
            return

        # Check for reserved instances / savings plans
        has_reserved_capacity = cost_data.get("has_reserved_capacity", False)
        reserved_percent = cost_data.get("reserved_capacity_percent", 0)

        if not has_reserved_capacity:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.COST,
                    severity=CapacitySeverity.MEDIUM,
                    resource="cost",
                    message="No reserved capacity - paying on-demand rates",
                    suggestion="Purchase reserved instances for predictable workloads (30-70% savings)",
                )
            )
        elif reserved_percent < 50:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.COST,
                    severity=CapacitySeverity.LOW,
                    resource="cost",
                    message=f"Only {reserved_percent}% reserved capacity",
                    suggestion="Increase reserved capacity for baseline workload",
                )
            )

        # Check for spot/preemptible instances
        uses_spot_instances = cost_data.get("uses_spot_instances", False)
        if not uses_spot_instances:
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.COST,
                    severity=CapacitySeverity.LOW,
                    resource="cost",
                    message="Not using spot/preemptible instances",
                    suggestion="Use spot instances for fault-tolerant workloads (60-90% savings)",
                )
            )

        # Check cost per user/transaction
        cost_per_unit = cost_data.get("cost_per_unit", 0)
        cost_trend = cost_data.get("cost_trend", "stable")

        if cost_trend == "increasing":
            self._issues.append(
                CapacityIssue(
                    category=CapacityCategory.COST,
                    severity=CapacitySeverity.MEDIUM,
                    resource="cost",
                    message="Cost per unit is increasing",
                    suggestion="Investigate efficiency degradation and optimization opportunities",
                )
            )

    def _check_performance_headroom(self, resources: list) -> None:
        """Check performance headroom and buffer capacity."""
        for resource in resources:
            resource_name = resource.get("name", "unknown")
            has_performance_buffer = resource.get("has_performance_buffer", False)

            if not has_performance_buffer:
                self._issues.append(
                    CapacityIssue(
                        category=CapacityCategory.PERFORMANCE,
                        severity=CapacitySeverity.MEDIUM,
                        resource=resource_name,
                        message="No performance buffer for traffic spikes",
                        suggestion="Maintain 20-30% headroom for unexpected load",
                    )
                )

            # Check response time degradation
            response_time_p99 = resource.get("response_time_p99_ms", 0)
            response_time_target = resource.get("response_time_target_ms", 1000)

            if response_time_p99 > response_time_target * 1.5:
                self._issues.append(
                    CapacityIssue(
                        category=CapacityCategory.PERFORMANCE,
                        severity=CapacitySeverity.HIGH,
                        resource=resource_name,
                        message=f"P99 latency ({response_time_p99}ms) exceeds target by 50%",
                        suggestion="Scale up or optimize to meet performance targets",
                    )
                )

    def _compute_score(self) -> int:
        """Compute overall capacity planning maturity score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == CapacitySeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == CapacitySeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == CapacitySeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == CapacitySeverity.LOW]) * 3,
        )
