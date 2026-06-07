"""Tests for src/rl_optimizer/stub.py."""
from __future__ import annotations

import pytest

from src.rl_optimizer.stub import OptimizerStatus, RLOptimizer, RLOptimizerConfig


class TestRLOptimizerConfig:
    """Tests for RLOptimizerConfig."""

    def test_default_config(self):
        """Default config has enabled=False and default reward weights."""
        config = RLOptimizerConfig()
        assert config.enabled is False
        assert "task_completion" in config.reward_weights
        assert "cost_efficiency" in config.reward_weights

    def test_custom_config(self):
        """Custom values override defaults."""
        config = RLOptimizerConfig(enabled=True, learning_rate=1e-3)
        assert config.enabled is True
        assert config.learning_rate == 1e-3


class TestRLOptimizer:
    """Tests for RLOptimizer."""

    def test_default_status_disabled(self):
        """Default optimizer status is DISABLED when config.enabled=False."""
        opt = RLOptimizer()
        assert opt.status == OptimizerStatus.DISABLED

    def test_enable_changes_status(self):
        """Enabling the optimizer changes status to READY."""
        opt = RLOptimizer()
        opt.enable()
        assert opt.status == OptimizerStatus.READY
        assert opt.config.enabled is True

    def test_disable_changes_status(self):
        """Disabling the optimizer changes status back to DISABLED."""
        opt = RLOptimizer(RLOptimizerConfig(enabled=True))
        assert opt.status == OptimizerStatus.READY
        opt.disable()
        assert opt.status == OptimizerStatus.DISABLED
        assert opt.config.enabled is False

    def test_train_raises_not_implemented(self):
        """train() always raises NotImplementedError (deferred to v2)."""
        opt = RLOptimizer()
        opt.enable()
        with pytest.raises(NotImplementedError):
            opt.train()

    def test_record_reward_updates_metrics(self):
        """Recording rewards updates the metrics dictionary."""
        opt = RLOptimizer()
        opt.record_reward(1.0, "task_completion")
        opt.record_reward(0.5, "cost_efficiency")
        metrics = opt.get_metrics()
        assert "avg_reward_task_completion" in metrics
        assert "avg_reward_cost_efficiency" in metrics
        assert "total_rewards" in metrics
        assert metrics["total_rewards"] == 1.5

    def test_to_dict(self):
        """to_dict serialises optimizer state."""
        opt = RLOptimizer()
        opt.enable()
        opt.record_reward(1.0)
        d = opt.to_dict()
        assert d["status"] == "ready"
        assert d["enabled"] is True
        assert "metrics" in d
        assert "config" in d
