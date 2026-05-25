"""Tests for the deployment_strategies module."""

from __future__ import annotations

import pytest

from lyra_policy_optimizer.deployment_strategies import (
    DeploymentConfig,
    DeploymentPlan,
    DeploymentResult,
    DeploymentStage,
    DeploymentStrategies,
)
from lyra_policy_optimizer.exceptions import DeploymentError
from lyra_policy_optimizer.policy_search import PolicyCandidate


class TestDeploymentConfig:
    """Test DeploymentConfig dataclass."""

    def test_default_config(self) -> None:
        """DeploymentConfig should have sensible defaults."""
        config = DeploymentConfig()
        assert config.strategy == "canary"
        assert config.canary_pct == 5.0
        assert config.rollout_duration_s == 300.0
        assert config.rollback_threshold == 0.1
        assert config.shadow_mode is False

    def test_frozen(self) -> None:
        """DeploymentConfig should be frozen."""
        config = DeploymentConfig()
        with pytest.raises(AttributeError):
            config.strategy = "blue_green"  # type: ignore[misc]


class TestDeploymentStage:
    """Test DeploymentStage dataclass."""

    def test_create_stage(self) -> None:
        """DeploymentStage should store stage data correctly."""
        stage = DeploymentStage(
            stage_name="canary_1",
            traffic_pct=5.0,
            duration_s=60.0,
            health_check=True,
        )
        assert stage.stage_name == "canary_1"
        assert stage.traffic_pct == 5.0
        assert stage.duration_s == 60.0
        assert stage.health_check is True


class TestDeploymentPlan:
    """Test DeploymentPlan dataclass."""

    def test_create_plan(self) -> None:
        """DeploymentPlan should store plan details."""
        policy = PolicyCandidate("p1", (), 0.9, 0.1, 0)
        stages = (DeploymentStage("s1", 5.0, 60.0, True),)
        plan = DeploymentPlan(
            policy=policy,
            stages=stages,
            estimated_duration_s=60.0,
            risk_level="low",
        )
        assert plan.estimated_duration_s == 60.0
        assert plan.risk_level == "low"
        assert plan.policy.candidate_id == "p1"


class TestDeploymentResult:
    """Test DeploymentResult dataclass."""

    def test_create_result(self) -> None:
        """DeploymentResult should store execution result."""
        policy = PolicyCandidate("p1", (), 0.9, 0.1, 0)
        stages = (DeploymentStage("s1", 5.0, 60.0, True),)
        plan = DeploymentPlan(policy, stages, 60.0, "low")
        result = DeploymentResult(
            plan=plan,
            completed_stages=stages,
            success=True,
            rollback_triggered=False,
        )
        assert result.success is True
        assert result.rollback_triggered is False


class TestDeploymentStrategies:
    """Test DeploymentStrategies class."""

    @pytest.fixture
    def strategies(self) -> DeploymentStrategies:
        return DeploymentStrategies()

    @pytest.fixture
    def policy(self) -> PolicyCandidate:
        return PolicyCandidate("p1", (("lr", 0.01),), 0.9, 0.1, 0)

    @pytest.mark.asyncio
    async def test_create_canary_plan(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create canary plan should return valid plan."""
        config = DeploymentConfig(strategy="canary", canary_pct=10.0)
        plan = await strategies.create_plan(policy, config)
        assert isinstance(plan, DeploymentPlan)
        assert len(plan.stages) == 4
        assert plan.risk_level == "low"
        assert plan.estimated_duration_s > 0

    @pytest.mark.asyncio
    async def test_create_blue_green_plan(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create blue-green plan should return valid plan."""
        config = DeploymentConfig(strategy="blue_green")
        plan = await strategies.create_plan(policy, config)
        assert isinstance(plan, DeploymentPlan)
        assert len(plan.stages) == 3
        assert plan.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_create_shadow_plan(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create shadow plan should return valid plan."""
        config = DeploymentConfig(strategy="shadow")
        plan = await strategies.create_plan(policy, config)
        assert isinstance(plan, DeploymentPlan)
        assert len(plan.stages) == 1
        assert plan.risk_level == "very_low"

    @pytest.mark.asyncio
    async def test_create_plan_invalid_strategy(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create plan should reject unknown strategy."""
        config = DeploymentConfig(strategy="unknown")
        with pytest.raises(DeploymentError, match="unknown deployment"):
            await strategies.create_plan(policy, config)

    @pytest.mark.asyncio
    async def test_create_plan_invalid_canary_pct(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create plan should reject invalid canary_pct."""
        config = DeploymentConfig(canary_pct=0.0)
        with pytest.raises(DeploymentError, match="canary_pct"):
            await strategies.create_plan(policy, config)

    @pytest.mark.asyncio
    async def test_create_plan_negative_canary_pct(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create plan should reject negative canary_pct."""
        config = DeploymentConfig(canary_pct=-5.0)
        with pytest.raises(DeploymentError, match="canary_pct"):
            await strategies.create_plan(policy, config)

    @pytest.mark.asyncio
    async def test_create_plan_invalid_duration(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Create plan should reject invalid duration."""
        config = DeploymentConfig(rollout_duration_s=0.0)
        with pytest.raises(DeploymentError, match="rollout_duration_s"):
            await strategies.create_plan(policy, config)

    @pytest.mark.asyncio
    async def test_execute_stage(
        self, strategies: DeploymentStrategies
    ) -> None:
        """Execute stage should return True on success."""
        stage = DeploymentStage("test", 50.0, 30.0, True)
        result = await strategies.execute_stage(stage)
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_stage_invalid_traffic(
        self, strategies: DeploymentStrategies
    ) -> None:
        """Execute stage should reject invalid traffic_pct."""
        stage = DeploymentStage("test", 150.0, 30.0, True)
        with pytest.raises(DeploymentError, match="traffic_pct"):
            await strategies.execute_stage(stage)

    @pytest.mark.asyncio
    async def test_execute_stage_negative_duration(
        self, strategies: DeploymentStrategies
    ) -> None:
        """Execute stage should reject negative duration."""
        stage = DeploymentStage("test", 50.0, -1.0, True)
        with pytest.raises(DeploymentError, match="duration_s"):
            await strategies.execute_stage(stage)

    @pytest.mark.asyncio
    async def test_health_check(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Health check should return True."""
        result = await strategies.health_check(policy)
        assert result is True

    @pytest.mark.asyncio
    async def test_trigger_rollback(
        self, strategies: DeploymentStrategies
    ) -> None:
        """Trigger rollback should return True."""
        stage = DeploymentStage("test", 50.0, 30.0, True)
        result = await strategies.trigger_rollback(stage)
        assert result is True

    @pytest.mark.asyncio
    async def test_canary_stage_traffic_increases(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Canary stages should have increasing traffic."""
        config = DeploymentConfig(strategy="canary", canary_pct=5.0)
        plan = await strategies.create_plan(policy, config)
        traffic_pcts = [s.traffic_pct for s in plan.stages]
        assert traffic_pcts == sorted(traffic_pcts)

    @pytest.mark.asyncio
    async def test_final_stage_full_traffic(
        self, strategies: DeploymentStrategies, policy: PolicyCandidate
    ) -> None:
        """Final canary stage should be 100%."""
        config = DeploymentConfig(strategy="canary", canary_pct=5.0)
        plan = await strategies.create_plan(policy, config)
        assert plan.stages[-1].traffic_pct == 100.0
