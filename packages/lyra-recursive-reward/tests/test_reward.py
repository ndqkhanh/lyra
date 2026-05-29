"""Tests for Recursive Reward package."""

from lyra_recursive_reward import (
    InnerRewardLoop,
    MiddleRewardLoop,
    OuterRewardLoop,
    RecursiveReward,
)


class TestInnerRewardLoop:
    def test_track_success(self):
        loop = InnerRewardLoop(window=7)
        for _ in range(7):
            loop.record_day(0.9)
        assert loop.current_score > 0

    def test_reward_hacking_detection(self):
        loop = InnerRewardLoop()
        for _ in range(7):
            loop.record_day(0.95)
        # high visible score but low held-out = hacking
        assert not loop.detect_reward_hacking(0.9)


class TestMiddleRewardLoop:
    def test_acquisition_rate(self):
        loop = MiddleRewardLoop(window=30)
        for _ in range(30):
            loop.record_acquisition(5)
        assert loop.current_rate == 5.0


class TestOuterRewardLoop:
    def test_trend(self):
        loop = OuterRewardLoop(window=90)
        for i in range(90):
            loop.record_evolution_speed(0.1 + i * 0.001)
        assert loop.trend > 0


class TestRecursiveReward:
    def test_record_all(self):
        r = RecursiveReward()
        r.record_inner(0.9)
        r.record_middle(5)
        r.record_outer(0.5)
        s = r.summary
        assert "inner_task_success" in s
        assert "middle_skill_acquisition_rate" in s
        assert "outer_evolution_trend" in s
