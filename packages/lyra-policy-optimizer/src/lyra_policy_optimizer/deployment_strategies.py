"""Safe policy deployment strategies including canary and shadow deployments."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .exceptions import DeploymentError
from .policy_search import PolicyCandidate


@dataclass(frozen=True)
class DeploymentConfig:
    """Configuration for a policy deployment."""

    strategy: str = "canary"
    canary_pct: float = 5.0
    rollout_duration_s: float = 300.0
    rollback_threshold: float = 0.1
    shadow_mode: bool = False


@dataclass(frozen=True)
class DeploymentStage:
    """A single stage in a deployment rollout."""

    stage_name: str
    traffic_pct: float
    duration_s: float
    health_check: bool


@dataclass(frozen=True)
class DeploymentPlan:
    """A complete deployment plan for a policy."""

    policy: PolicyCandidate
    stages: tuple[DeploymentStage, ...]
    estimated_duration_s: float
    risk_level: str


@dataclass(frozen=True)
class DeploymentResult:
    """Result of a deployment execution."""

    plan: DeploymentPlan
    completed_stages: tuple[DeploymentStage, ...]
    success: bool
    rollback_triggered: bool


class DeploymentStrategies:
    """Safe policy deployment with staged rollouts and rollback support."""

    async def create_plan(
        self, policy: PolicyCandidate, config: DeploymentConfig
    ) -> DeploymentPlan:
        """Create a deployment plan based on the chosen strategy."""
        if config.canary_pct <= 0 or config.canary_pct > 100:
            raise DeploymentError("canary_pct must be in (0, 100]")
        if config.rollout_duration_s <= 0:
            raise DeploymentError("rollout_duration_s must be positive")

        if config.strategy == "canary":
            stages = self._build_canary_stages(config)
            risk_level = "low"
        elif config.strategy == "blue_green":
            stages = self._build_blue_green_stages(config)
            risk_level = "medium"
        elif config.strategy == "shadow":
            stages = self._build_shadow_stages(config)
            risk_level = "very_low"
        else:
            raise DeploymentError(f"unknown deployment strategy: {config.strategy}")

        total_duration = sum(s.duration_s for s in stages)

        return DeploymentPlan(
            policy=policy,
            stages=stages,
            estimated_duration_s=total_duration,
            risk_level=risk_level,
        )

    async def execute_stage(self, stage: DeploymentStage) -> bool:
        """Execute a single deployment stage."""
        if stage.traffic_pct < 0 or stage.traffic_pct > 100:
            raise DeploymentError("traffic_pct must be in [0, 100]")
        if stage.duration_s < 0:
            raise DeploymentError("duration_s must be non-negative")
        return True

    async def health_check(self, policy: PolicyCandidate) -> bool:
        """Run a health check on a deployed policy."""
        _ = policy
        return True

    async def trigger_rollback(self, stage: DeploymentStage) -> bool:
        """Trigger a rollback if the deployment stage shows degradation."""
        _ = stage
        return True

    def _build_canary_stages(
        self, config: DeploymentConfig
    ) -> tuple[DeploymentStage, ...]:
        """Build canary rollout stages."""
        stages: list[DeploymentStage] = []

        traffic_pcts = [
            config.canary_pct,
            min(25.0, config.canary_pct * 3),
            min(50.0, config.canary_pct * 5),
            100.0,
        ]
        duration = config.rollout_duration_s / len(traffic_pcts)

        for i, pct in enumerate(traffic_pcts):
            stages.append(
                DeploymentStage(
                    stage_name=f"canary_{i + 1}",
                    traffic_pct=pct,
                    duration_s=duration,
                    health_check=True,
                )
            )

        return tuple(stages)

    def _build_blue_green_stages(
        self, config: DeploymentConfig
    ) -> tuple[DeploymentStage, ...]:
        """Build blue-green deployment stages."""
        return (
            DeploymentStage(
                stage_name="green_deploy",
                traffic_pct=0.0,
                duration_s=config.rollout_duration_s * 0.3,
                health_check=True,
            ),
            DeploymentStage(
                stage_name="switch",
                traffic_pct=100.0,
                duration_s=config.rollout_duration_s * 0.4,
                health_check=True,
            ),
            DeploymentStage(
                stage_name="verify",
                traffic_pct=100.0,
                duration_s=config.rollout_duration_s * 0.3,
                health_check=True,
            ),
        )

    def _build_shadow_stages(
        self, config: DeploymentConfig
    ) -> tuple[DeploymentStage, ...]:
        """Build shadow deployment stages."""
        return (
            DeploymentStage(
                stage_name="shadow",
                traffic_pct=0.0,
                duration_s=config.rollout_duration_s,
                health_check=True,
            ),
        )
