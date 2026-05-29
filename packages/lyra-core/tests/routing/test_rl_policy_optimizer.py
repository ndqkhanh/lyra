"""Tests for the RL-based policy optimizer."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from lyra_core.routing.rl_policy_optimizer import (
    RLPriorityOptimizer,
    RLRouterConfig,
    RLRoutingDecision,
    TrainingMetrics,
)
from lyra_core.routing.state_encoder import StateEncoder, StateVector


def _make_state(turn_index: int = 0) -> StateVector:
    encoder = StateEncoder()
    return encoder.encode(turn_index=turn_index)


class TestRLRouterConfig:
    def test_defaults(self):
        cfg = RLRouterConfig()
        assert cfg.shadow_mode is True
        assert cfg.learning_rate == 0.01
        assert cfg.batch_size == 32
        assert cfg.replay_capacity == 10000

    def test_mutable_config(self):
        cfg = RLRouterConfig()
        cfg.shadow_mode = False
        assert cfg.shadow_mode is False


class TestRLRoutingDecision:
    def test_decision_contains_tier(self):
        sv = _make_state()
        decision = RLRoutingDecision(
            tier="fast",
            action_idx=0,
            confidence=0.85,
            state_vector=sv,
            shadow_mode=True,
            reason="test",
        )
        assert decision.tier == "fast"
        assert decision.confidence == 0.85

    def test_shadow_mode_reflected_in_reason(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        assert "[SHADOW]" in decision.reason


class TestRLPriorityOptimizer:
    def test_start_episode_returns_id(self):
        opt = RLPriorityOptimizer()
        ep_id = opt.start_episode()
        assert len(ep_id) > 0

    def test_select_tier_returns_valid_action(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        assert decision.tier in ("fast", "reasoning", "advisor")
        assert 0 <= decision.action_idx < 3
        assert decision.shadow_mode is True

    def test_record_outcome_returns_reward(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        reward = opt.record_outcome(
            decision, quality=1.0, cost_usd=0.01, latency_ms=300.0
        )
        assert isinstance(reward, float)

    def test_episode_tracks_rewards(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        for i in range(5):
            sv = _make_state(turn_index=i)
            decision = opt.select_tier(sv)
            opt.record_outcome(
                decision,
                quality=0.8 + i * 0.05,
                cost_usd=0.01,
                latency_ms=200.0,
                next_state=_make_state(turn_index=i + 1),
            )
        metrics = opt.end_episode()
        assert metrics.episodes_completed == 1
        # Buffer accumulates (training requires min_replay_size=128 which needs many episodes)
        assert opt.buffer_size == 5

    def test_end_episode_returns_metrics(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        opt.record_outcome(decision, quality=1.0, cost_usd=0.01)
        metrics = opt.end_episode()
        assert isinstance(metrics, TrainingMetrics)
        assert metrics.epoch == 1
        assert metrics.cost_savings_pct >= 0.0

    def test_action_distribution_tracked(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        for i in range(10):
            sv = _make_state(turn_index=i)
            decision = opt.select_tier(sv)
            opt.record_outcome(decision, quality=0.5, cost_usd=0.01)
        metrics = opt.end_episode()
        total = sum(metrics.action_distribution.values())
        assert abs(total - 1.0) < 0.01

    def test_should_promote_requires_episodes(self):
        opt = RLPriorityOptimizer()
        assert not opt.should_promote()

    def test_promote_disables_shadow_mode(self):
        opt = RLPriorityOptimizer()
        opt.promote()
        assert opt.config.shadow_mode is False

    def test_save_load_policy_roundtrip(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        opt.record_outcome(decision, quality=1.0, cost_usd=0.01)
        opt.end_episode()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            opt.save_policy(tmp_path)
            assert tmp_path.exists()

            data = json.loads(tmp_path.read_text())
            assert "weights" in data
            assert "episodes" in data

            opt2 = RLPriorityOptimizer()
            loaded = opt2.load_policy(tmp_path)
            assert loaded
        finally:
            tmp_path.unlink()

    def test_load_nonexistent_policy(self):
        opt = RLPriorityOptimizer()
        result = opt.load_policy("/nonexistent/path/policy.json")
        assert not result

    def test_reset_clears_all_state(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        opt.record_outcome(decision, quality=1.0, cost_usd=0.01)
        opt.end_episode()

        opt.reset()
        assert opt.total_steps == 0
        assert opt.episodes == 0
        assert opt.buffer_size == 0

    def test_buffer_accumulates_experiences(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        for i in range(5):
            sv = _make_state(turn_index=i)
            decision = opt.select_tier(sv)
            opt.record_outcome(
                decision, quality=0.8, cost_usd=0.01,
                next_state=_make_state(turn_index=i + 1),
            )
        assert opt.buffer_size == 5

    def test_multiple_episodes_accumulate(self):
        opt = RLPriorityOptimizer()
        for _ep in range(3):
            opt.start_episode()
            for i in range(3):
                sv = _make_state(turn_index=i)
                decision = opt.select_tier(sv)
                opt.record_outcome(decision, quality=0.7, cost_usd=0.01)
            opt.end_episode()
        assert opt.episodes == 3

    def test_select_tier_exploit_mode(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        d1 = opt.select_tier(sv, exploit=True)
        d2 = opt.select_tier(sv, exploit=True)
        assert d1.tier == d2.tier  # deterministic

    def test_done_flag_in_record(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        reward = opt.record_outcome(
            decision, quality=1.0, cost_usd=0.01, done=True
        )
        assert isinstance(reward, float)

    def test_reward_with_safety_flagged(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        sv = _make_state()
        decision = opt.select_tier(sv)
        safe_reward = opt.record_outcome(decision, quality=1.0, safety_flagged=False)
        flagged_reward = opt.record_outcome(decision, quality=1.0, safety_flagged=True)
        assert flagged_reward <= safe_reward

    def test_cost_history_used_in_savings(self):
        opt = RLPriorityOptimizer()
        opt.start_episode()
        for i in range(5):
            sv = _make_state(turn_index=i)
            decision = opt.select_tier(sv)
            opt.record_outcome(decision, quality=0.9, cost_usd=0.005)
        metrics = opt.end_episode()
        assert metrics.cost_savings_pct >= 0.0
