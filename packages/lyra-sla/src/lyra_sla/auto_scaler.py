"""Auto-scaling based on SLA metrics: predictive scaling, reactive scaling, resource optimization, cost-quality tradeoff management."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

import numpy as np

from .sla_manager import SLAManager, SLIMetric, BudgetType, Budget
from .metrics import MetricsCollector, RollingStats
from .exceptions import AutoScalerError

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class ScalingDirection(Enum):
    """Direction of scaling action."""

    UP = auto()
    DOWN = auto()
    NONE = auto()


class ScalingStrategy(Enum):
    """Scaling approach."""

    REACTIVE = auto()       # Threshold-based
    PREDICTIVE = auto()     # ML/statistical prediction
    HYBRID = auto()         # Combined
    SCHEDULE_BASED = auto()  # Time-based schedule


@dataclass
class ResourceConfig:
    """Resource configuration for scaling.

    Attributes:
        min_replicas: Minimum number of replicas.
        max_replicas: Maximum number of replicas.
        current_replicas: Current active replicas.
        target_replicas: Desired replica count.
        cpu_per_replica: CPU units per replica.
        memory_mb_per_replica: Memory per replica.
        cost_per_replica_hour: Cost per replica per hour.
    """

    min_replicas: int = 1
    max_replicas: int = 10
    current_replicas: int = 1
    target_replicas: int = 1
    cpu_per_replica: float = 1.0
    memory_mb_per_replica: int = 512
    cost_per_replica_hour: float = 0.01


@dataclass
class ScalingDecision:
    """A scaling decision with rationale.

    Attributes:
        agent_id: Which agent to scale.
        direction: Up, down, or none.
        from_replicas: Current replica count.
        to_replicas: Target replica count.
        confidence: Confidence in this decision (0-1).
        reason: Human-readable rationale.
        strategy: Which strategy produced this decision.
        timestamp: When the decision was made.
    """

    agent_id: str
    direction: ScalingDirection = ScalingDirection.NONE
    from_replicas: int = 1
    to_replicas: int = 1
    confidence: float = 0.5
    reason: str = ""
    strategy: ScalingStrategy = ScalingStrategy.REACTIVE
    timestamp: float = field(default_factory=time.time)


@dataclass
class CostQualityTradeoff:
    """Analysis of cost vs quality tradeoffs for scaling.

    Attributes:
        agent_id: Agent identifier.
        current_cost_hour: Current cost per hour.
        projected_cost_hour: Projected cost after scaling.
        quality_gain: Expected quality improvement.
        cost_per_quality_point: Cost per unit of quality improvement.
        is_worthwhile: Whether the tradeoff is favorable.
    """

    agent_id: str
    current_cost_hour: float = 0.0
    projected_cost_hour: float = 0.0
    quality_gain: float = 0.0
    cost_per_quality_point: float = 0.0
    is_worthwhile: bool = False


# ── Reactive Scaler ────────────────────────────────────────────────────


class ReactiveScaler:
    """Threshold-based reactive auto-scaler.

    Scales up when metrics exceed thresholds and scales down when
    metrics are well below thresholds for a sustained period.
    """

    def __init__(
        self,
        scale_up_threshold: float = 0.8,    # Utilization threshold to scale up
        scale_down_threshold: float = 0.3,   # Utilization to scale down
        cooldown_seconds: float = 60.0,
        step_size: int = 1,
    ) -> None:
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown_seconds = cooldown_seconds
        self.step_size = step_size
        self._last_scale_time: dict[str, float] = {}

    def evaluate(
        self,
        agent_id: str,
        stats: dict[str, RollingStats],
        config: ResourceConfig,
    ) -> ScalingDecision:
        """Evaluate whether to scale based on current metric stats.

        Args:
            agent_id: Agent identifier.
            stats: Current metric statistics.
            config: Resource configuration.

        Returns:
            Scaling decision.
        """
        now = time.time()
        if agent_id in self._last_scale_time:
            if now - self._last_scale_time[agent_id] < self.cooldown_seconds:
                return ScalingDecision(
                    agent_id=agent_id,
                    direction=ScalingDirection.NONE,
                    from_replicas=config.current_replicas,
                    to_replicas=config.current_replicas,
                    reason="Cooldown period active",
                    strategy=ScalingStrategy.REACTIVE,
                )

        # Check multiple indicators
        scale_up_votes = 0
        scale_down_votes = 0

        # Check latency
        if "latency_p95" in stats:
            p95 = stats["latency_p95"].p95
            if p95 > 5000:  # 5s p95
                scale_up_votes += 1
            elif p95 < 1000:  # 1s p95
                scale_down_votes += 1

        # Check error rate
        if "error_rate" in stats:
            error_rate = stats["error_rate"].mean
            if error_rate > 0.05:  # >5% errors
                scale_up_votes += 1
            elif error_rate < 0.01:  # <1% errors
                scale_down_votes += 1

        # Check throughput saturation
        if "throughput" in stats:
            # If throughput is at max and latency is rising = need more capacity
            pass

        if scale_up_votes >= 1 and config.current_replicas < config.max_replicas:
            new_count = min(config.current_replicas + self.step_size, config.max_replicas)
            self._last_scale_time[agent_id] = now
            return ScalingDecision(
                agent_id=agent_id,
                direction=ScalingDirection.UP,
                from_replicas=config.current_replicas,
                to_replicas=new_count,
                confidence=0.7,
                reason=f"Scale up: P95 latency or error rate exceeded thresholds",
                strategy=ScalingStrategy.REACTIVE,
            )

        if scale_down_votes >= 2 and config.current_replicas > config.min_replicas:
            new_count = max(config.current_replicas - self.step_size, config.min_replicas)
            self._last_scale_time[agent_id] = now
            return ScalingDecision(
                agent_id=agent_id,
                direction=ScalingDirection.DOWN,
                from_replicas=config.current_replicas,
                to_replicas=new_count,
                confidence=0.6,
                reason="Scale down: metrics well below thresholds",
                strategy=ScalingStrategy.REACTIVE,
            )

        return ScalingDecision(
            agent_id=agent_id,
            direction=ScalingDirection.NONE,
            from_replicas=config.current_replicas,
            to_replicas=config.current_replicas,
            reason="Within acceptable range",
            strategy=ScalingStrategy.REACTIVE,
        )


# ── Predictive Scaler ──────────────────────────────────────────────────


class PredictiveScaler:
    """ML-based predictive auto-scaler using historical patterns.

    Analyzes historical metric trends to predict future demand
    and proactively scale before thresholds are breached.
    """

    def __init__(
        self,
        prediction_window_seconds: float = 300.0,
        trend_threshold: float = 0.1,
        min_history_points: int = 30,
    ) -> None:
        self.prediction_window_seconds = prediction_window_seconds
        self.trend_threshold = trend_threshold
        self.min_history_points = min_history_points
        self._prediction_cache: dict[str, dict[str, float]] = {}

    def predict_demand(
        self,
        agent_id: str,
        timeseries: list[tuple[float, float]],
        horizon_seconds: float = 300.0,
    ) -> float:
        """Predict future demand using linear trend extrapolation.

        Args:
            agent_id: Agent identifier.
            timeseries: Historical (timestamp, value) data.
            horizon_seconds: How far ahead to predict.

        Returns:
            Predicted value at horizon.
        """
        if len(timeseries) < self.min_history_points:
            return float(np.mean([v for _, v in timeseries])) if timeseries else 0.0

        ts = np.array([t for t, _ in timeseries], dtype=np.float64)
        vals = np.array([v for _, v in timeseries], dtype=np.float64)

        # Normalize timestamps relative to first observation
        ts_norm = ts - ts[0]

        # Simple linear regression
        n = len(ts_norm)
        sum_x = np.sum(ts_norm)
        sum_y = np.sum(vals)
        sum_xy = np.sum(ts_norm * vals)
        sum_xx = np.sum(ts_norm * ts_norm)

        denom = n * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-10:
            return float(np.mean(vals))

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # Predict at horizon
        future_offset = ts[-1] - ts[0] + horizon_seconds
        predicted = intercept + slope * future_offset

        return max(0.0, float(predicted))

    def evaluate(
        self,
        agent_id: str,
        stats: dict[str, RollingStats],
        metrics_collector: MetricsCollector,
        config: ResourceConfig,
    ) -> ScalingDecision:
        """Evaluate scaling based on predictive analysis.

        Args:
            agent_id: Agent identifier.
            stats: Current statistics.
            metrics_collector: Collector for historical data.
            config: Resource configuration.

        Returns:
            Scaling decision.
        """
        if "latency_p95" not in stats:
            return ScalingDecision(
                agent_id=agent_id,
                direction=ScalingDirection.NONE,
                from_replicas=config.current_replicas,
                to_replicas=config.current_replicas,
                reason="Insufficient data for prediction",
                strategy=ScalingStrategy.PREDICTIVE,
            )

        # Get historical latency data
        timeseries = metrics_collector.query_timeseries(
            agent_id, "latency_p95", window_seconds=3600.0
        )
        if len(timeseries) < self.min_history_points:
            return ScalingDecision(
                agent_id=agent_id,
                direction=ScalingDirection.NONE,
                from_replicas=config.current_replicas,
                to_replicas=config.current_replicas,
                reason=f"Need {self.min_history_points} data points, have {len(timeseries)}",
                strategy=ScalingStrategy.PREDICTIVE,
            )

        predicted_p95 = self.predict_demand(agent_id, timeseries, self.prediction_window_seconds)
        current_p95 = stats["latency_p95"].p95

        # Check if the trend is upward (>10% increase predicted)
        if predicted_p95 > current_p95 * (1 + self.trend_threshold):
            if config.current_replicas < config.max_replicas:
                needed_replicas = int(
                    config.current_replicas
                    * (predicted_p95 / max(current_p95, 1.0))
                )
                new_count = min(needed_replicas, config.max_replicas)

                confidence = min(0.9, max(0.5, (predicted_p95 - current_p95) / max(current_p95, 1.0)))

                return ScalingDecision(
                    agent_id=agent_id,
                    direction=ScalingDirection.UP,
                    from_replicas=config.current_replicas,
                    to_replicas=new_count,
                    confidence=confidence,
                    reason=f"Predictive scale up: latency trending up "
                           f"(current={current_p95:.0f}ms, predicted={predicted_p95:.0f}ms)",
                    strategy=ScalingStrategy.PREDICTIVE,
                )

        # Check if trend is declining
        if predicted_p95 < current_p95 * (1 - self.trend_threshold * 2):
            if config.current_replicas > config.min_replicas:
                new_count = max(config.current_replicas - 1, config.min_replicas)
                return ScalingDecision(
                    agent_id=agent_id,
                    direction=ScalingDirection.DOWN,
                    from_replicas=config.current_replicas,
                    to_replicas=new_count,
                    confidence=0.5,
                    reason=f"Predictive scale down: latency trending down",
                    strategy=ScalingStrategy.PREDICTIVE,
                )

        return ScalingDecision(
            agent_id=agent_id,
            direction=ScalingDirection.NONE,
            from_replicas=config.current_replicas,
            to_replicas=config.current_replicas,
            reason="Stable prediction",
            strategy=ScalingStrategy.PREDICTIVE,
            confidence=0.8,
        )


# ── Auto-scaler engine ─────────────────────────────────────────────────


class AutoScaler:
    """Unified auto-scaler combining reactive and predictive strategies.

    Manages resource configurations, evaluates scaling decisions,
    and optimizes for cost-quality tradeoffs.
    """

    def __init__(
        self,
        sla_manager: SLAManager,
        metrics_collector: MetricsCollector,
        strategy: ScalingStrategy = ScalingStrategy.HYBRID,
    ) -> None:
        self.sla_manager = sla_manager
        self.metrics = metrics_collector
        self.strategy = strategy

        self._reactive = ReactiveScaler()
        self._predictive = PredictiveScaler()
        self._configs: dict[str, ResourceConfig] = {}
        self._decisions: deque[ScalingDecision] = deque(maxlen=500)
        self._tradeoffs: dict[str, CostQualityTradeoff] = {}

    def configure(self, agent_id: str, config: ResourceConfig) -> None:
        """Set resource configuration for an agent.

        Args:
            agent_id: Agent identifier.
            config: Resource configuration.
        """
        self._configs[agent_id] = config
        logger.info("Resource config set for '%s': %d-%d replicas",
                    agent_id, config.min_replicas, config.max_replicas)

    def get_config(self, agent_id: str) -> ResourceConfig:
        """Get resource config, creating a default if none exists."""
        if agent_id not in self._configs:
            self._configs[agent_id] = ResourceConfig()
        return self._configs[agent_id]

    async def evaluate_scaling(self, agent_id: str) -> ScalingDecision:
        """Evaluate whether to scale an agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            Scaling decision.
        """
        config = self.get_config(agent_id)
        stats = self.metrics.get_all_stats(agent_id)

        if self.strategy == ScalingStrategy.REACTIVE:
            decision = self._reactive.evaluate(agent_id, stats, config)
        elif self.strategy == ScalingStrategy.PREDICTIVE:
            decision = self._predictive.evaluate(agent_id, stats, self.metrics, config)
        else:  # HYBRID
            react_decision = self._reactive.evaluate(agent_id, stats, config)
            pred_decision = self._predictive.evaluate(agent_id, stats, self.metrics, config)

            if react_decision.direction == ScalingDirection.UP or pred_decision.direction == ScalingDirection.UP:
                # Prefer the more aggressive scale-up
                if (
                    pred_decision.direction == ScalingDirection.UP
                    and pred_decision.to_replicas >= react_decision.to_replicas
                ):
                    decision = pred_decision
                else:
                    decision = react_decision
            elif react_decision.direction == ScalingDirection.DOWN and pred_decision.direction == ScalingDirection.DOWN:
                decision = react_decision  # Prefer reactive for scale-down
            else:
                decision = ScalingDecision(
                    agent_id=agent_id,
                    direction=ScalingDirection.NONE,
                    from_replicas=config.current_replicas,
                    to_replicas=config.current_replicas,
                    reason="Hybrid: no consensus for scaling",
                    strategy=ScalingStrategy.HYBRID,
                    confidence=0.3,
                )

        self._decisions.append(decision)

        if decision.direction != ScalingDirection.NONE:
            logger.info("Scaling decision for '%s': %s %d->%d (%s)",
                        agent_id, decision.direction.name,
                        decision.from_replicas, decision.to_replicas,
                        decision.reason)

        return decision

    async def apply_scaling(
        self, agent_id: str, decision: Optional[ScalingDecision] = None
    ) -> ScalingDecision:
        """Evaluate and apply scaling for an agent.

        Args:
            agent_id: Agent identifier.
            decision: Pre-computed decision, or None to evaluate.

        Returns:
            The applied decision.
        """
        if decision is None:
            decision = await self.evaluate_scaling(agent_id)

        if decision.direction != ScalingDirection.NONE:
            config = self.get_config(agent_id)
            config.current_replicas = decision.to_replicas
            self._configs[agent_id] = config

        return decision

    def evaluate_cost_quality(self, agent_id: str) -> CostQualityTradeoff:
        """Analyze cost-quality tradeoff for scaling.

        Args:
            agent_id: Agent identifier.

        Returns:
            Tradeoff analysis.
        """
        config = self.get_config(agent_id)
        stats = self.metrics.get_all_stats(agent_id)

        current_cost = config.current_replicas * config.cost_per_replica_hour
        projected_cost = (config.current_replicas + 1) * config.cost_per_replica_hour

        # Estimate quality gain from one more replica
        current_quality = stats.get("quality_score", RollingStats()).mean if "quality_score" in stats else 0.7
        # Rough heuristic: each additional replica improves quality by some fraction
        quality_gain = 0.05 / max(config.current_replicas, 1)

        cost_per_quality = (
            (projected_cost - current_cost) / quality_gain if quality_gain > 0 else float("inf")
        )
        is_worthwhile = cost_per_quality < 0.10  # Less than $0.10 per quality point

        tradeoff = CostQualityTradeoff(
            agent_id=agent_id,
            current_cost_hour=current_cost,
            projected_cost_hour=projected_cost,
            quality_gain=quality_gain,
            cost_per_quality_point=cost_per_quality,
            is_worthwhile=is_worthwhile,
        )
        self._tradeoffs[agent_id] = tradeoff
        return tradeoff

    @property
    def scaling_history(self) -> list[ScalingDecision]:
        """Get all scaling decisions."""
        return list(self._decisions)

    @property
    def summary(self) -> dict[str, Any]:
        """Get auto-scaler summary."""
        recent = list(self._decisions)[-10:]
        return {
            "strategy": self.strategy.name,
            "managed_agents": len(self._configs),
            "total_decisions": len(self._decisions),
            "recent_decisions": [
                {
                    "agent": d.agent_id,
                    "direction": d.direction.name,
                    "from": d.from_replicas,
                    "to": d.to_replicas,
                    "reason": d.reason[:80],
                }
                for d in recent
            ],
            "agent_configs": {
                aid: {
                    "replicas": cfg.current_replicas,
                    "range": f"{cfg.min_replicas}-{cfg.max_replicas}",
                    "cost_hour": cfg.current_replicas * cfg.cost_per_replica_hour,
                }
                for aid, cfg in self._configs.items()
            },
        }
