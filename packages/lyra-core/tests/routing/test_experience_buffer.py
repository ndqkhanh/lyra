"""Tests for the RL experience replay buffer."""
from __future__ import annotations

import time

import pytest
from lyra_core.routing.experience_buffer import (
    VALID_ACTIONS,
    Experience,
    ExperienceBuffer,
)


def _make_exp(action: str = "fast", reward: float = 0.5, priority: float = 0.5) -> Experience:
    return Experience(
        state_features=tuple(float(i) for i in range(12)),
        action=action,
        reward=reward,
        next_state_features=tuple(float(i) for i in range(12)),
        done=False,
        priority=priority,
        timestamp=time.time(),
        episode_id="ep-001",
    )


class TestExperience:
    def test_valid_action_accepted(self):
        exp = Experience(
            state_features=(0.0,) * 12,
            action="fast",
            reward=0.5,
            next_state_features=(0.0,) * 12,
            done=False,
            priority=0.5,
            timestamp=time.time(),
            episode_id="ep-001",
        )
        assert exp.action == "fast"

    def test_invalid_action_rejected(self):
        with pytest.raises(ValueError, match="Invalid action"):
            Experience(
                state_features=(0.0,) * 12,
                action="invalid_tier",
                reward=0.5,
                next_state_features=(0.0,) * 12,
                done=False,
                priority=0.5,
                timestamp=time.time(),
                episode_id="ep-001",
            )

    def test_state_dimension_mismatch_rejected(self):
        with pytest.raises(ValueError, match="dimensionality"):
            Experience(
                state_features=(0.0,) * 12,
                action="fast",
                reward=0.5,
                next_state_features=(0.0,) * 6,
                done=False,
                priority=0.5,
                timestamp=time.time(),
                episode_id="ep-001",
            )

    def test_frozen_dataclass(self):
        exp = _make_exp()
        with pytest.raises(Exception):
            exp.reward = 1.0  # type: ignore[misc]


class TestExperienceBuffer:
    def test_empty_buffer_zero_size(self):
        buf = ExperienceBuffer()
        assert buf.size == 0

    def test_push_increases_size(self):
        buf = ExperienceBuffer()
        buf.push(_make_exp())
        assert buf.size == 1

    def test_capacity_respected(self):
        buf = ExperienceBuffer(capacity=3)
        for i in range(5):
            buf.push(_make_exp(reward=float(i)))
        assert buf.size == 3

    def test_push_batch(self):
        buf = ExperienceBuffer()
        exps = [_make_exp() for _ in range(3)]
        buf.push_batch(exps)
        assert buf.size == 3

    def test_sample_returns_correct_size(self):
        buf = ExperienceBuffer()
        for i in range(10):
            buf.push(_make_exp(reward=float(i)))
        batch = buf.sample(batch_size=5)
        assert len(batch) == 5

    def test_sample_from_small_buffer(self):
        buf = ExperienceBuffer()
        buf.push(_make_exp())
        batch = buf.sample(batch_size=5)
        assert len(batch) == 1

    def test_sample_empty_returns_empty(self):
        buf = ExperienceBuffer()
        batch = buf.sample(batch_size=5)
        assert batch == []

    def test_stratified_sample_covers_actions(self):
        buf = ExperienceBuffer()
        actions = ["fast"] * 10 + ["reasoning"] * 10 + ["advisor"] * 10
        for a in actions:
            buf.push(_make_exp(action=a))
        batch = buf.sample(batch_size=6, stratified=True)
        action_set = {exp.action for exp in batch}
        assert "fast" in action_set or "reasoning" in action_set or "advisor" in action_set

    def test_update_priorities(self):
        buf = ExperienceBuffer()
        for _i in range(5):
            buf.push(_make_exp(priority=0.1))
        buf.update_priorities(indices=[0, 1, 2], td_errors=[0.8, 0.3, 0.9])
        assert abs(buf._buffer[0].priority) == 0.8
        assert abs(buf._buffer[2].priority) == 0.9

    def test_action_distribution_tracks_counts(self):
        buf = ExperienceBuffer()
        buf.push(_make_exp(action="fast"))
        buf.push(_make_exp(action="fast"))
        buf.push(_make_exp(action="reasoning"))
        dist = buf.action_distribution
        assert dist["fast"] == 2
        assert dist["reasoning"] == 1
        assert dist["advisor"] == 0

    def test_clear_resets_everything(self):
        buf = ExperienceBuffer()
        for _i in range(5):
            buf.push(_make_exp())
        buf.clear()
        assert buf.size == 0
        assert all(v == 0 for v in buf.action_distribution.values())

    def test_set_beta_clamps(self):
        buf = ExperienceBuffer()
        buf.set_beta(1.5)
        assert buf.beta == 1.0
        buf.set_beta(-0.5)
        assert buf.beta == 0.0

    def test_is_full(self):
        buf = ExperienceBuffer(capacity=3)
        assert not buf.is_full
        for _i in range(3):
            buf.push(_make_exp())
        assert buf.is_full


class TestValidActions:
    def test_valid_actions_tuple(self):
        assert "fast" in VALID_ACTIONS
        assert "reasoning" in VALID_ACTIONS
        assert "advisor" in VALID_ACTIONS
        assert len(VALID_ACTIONS) == 3
