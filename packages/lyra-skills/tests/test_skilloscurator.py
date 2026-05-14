"""Tests for Phase I — SkillOS curator."""
import pytest

from lyra_skills.skilloscurator import (
    CurationAction,
    CurationDecision,
    CurationReward,
    CurationRewardConfig,
    SkillOSCurator,
    TaskGroup,
)


def _decision(action: CurationAction, skill_id="skill-1", content="body") -> CurationDecision:
    return CurationDecision(action=action, skill_id=skill_id, content=content)


def _reward(task=0.8, validity=1.0, quality=0.7, compression=0.5) -> CurationReward:
    return CurationReward(
        task_outcome=task,
        operation_validity=validity,
        content_quality=quality,
        compression_ratio=compression,
    )


class TestCurationReward:
    def test_total_default_weights(self):
        r = _reward(task=1.0, validity=1.0, quality=1.0, compression=1.0)
        assert r.total() == pytest.approx(1.0)

    def test_total_partial(self):
        r = CurationReward(task_outcome=0.5, operation_validity=0.0, content_quality=0.0, compression_ratio=0.0)
        cfg = CurationRewardConfig()
        assert r.total(cfg) == pytest.approx(0.50 * 0.5)

    def test_compression_capped_at_one(self):
        r = CurationReward(task_outcome=0.0, operation_validity=0.0, content_quality=0.0, compression_ratio=5.0)
        cfg = CurationRewardConfig(compression_weight=1.0, task_outcome_weight=0, operation_validity_weight=0, content_quality_weight=0)
        assert r.total(cfg) == pytest.approx(1.0)

    def test_custom_weights(self):
        cfg = CurationRewardConfig(
            task_outcome_weight=1.0,
            operation_validity_weight=0.0,
            content_quality_weight=0.0,
            compression_weight=0.0,
        )
        r = CurationReward(task_outcome=0.6)
        assert r.total(cfg) == pytest.approx(0.6)


class TestSkillOSCuratorInsert:
    def test_insert_adds_skill(self):
        curator = SkillOSCurator()
        d = _decision(CurationAction.INSERT, "new-skill", "content")
        assert curator.submit(d)
        assert "new-skill" in curator.list_skills()

    def test_insert_collision_returns_false(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s"))
        result = curator.submit(_decision(CurationAction.INSERT, "s"))
        assert not result

    def test_skill_count_increments(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s1"))
        curator.submit(_decision(CurationAction.INSERT, "s2"))
        assert curator.skill_count == 2


class TestSkillOSCuratorUpdate:
    def test_update_existing_skill(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s", "v1"))
        result = curator.submit(_decision(CurationAction.UPDATE, "s", "v2"))
        assert result
        assert curator.get_skill("s") == "v2"

    def test_update_unknown_skill_returns_false(self):
        curator = SkillOSCurator()
        result = curator.submit(_decision(CurationAction.UPDATE, "unknown", "content"))
        assert not result


class TestSkillOSCuratorDelete:
    def test_delete_removes_skill(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s"))
        curator.submit(_decision(CurationAction.DELETE, "s"))
        assert "s" not in curator.list_skills()

    def test_delete_nonexistent_still_returns_true(self):
        curator = SkillOSCurator()
        result = curator.submit(_decision(CurationAction.DELETE, "ghost"))
        assert result  # pop is idempotent

    def test_skill_count_decrements(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s"))
        assert curator.skill_count == 1
        curator.submit(_decision(CurationAction.DELETE, "s"))
        assert curator.skill_count == 0


class TestSkillOSCuratorNoop:
    def test_noop_changes_nothing(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s"))
        result = curator.submit(_decision(CurationAction.NOOP, "s"))
        assert result
        assert curator.skill_count == 1


class TestRewardTracking:
    def test_mean_reward_empty(self):
        assert SkillOSCurator().mean_reward() == 0.0

    def test_mean_reward_single(self):
        curator = SkillOSCurator()
        d = _decision(CurationAction.INSERT)
        curator.submit(d)
        r = _reward(task=1.0, validity=1.0, quality=1.0, compression=1.0)
        curator.record_reward(d, r)
        assert curator.mean_reward() == pytest.approx(1.0)

    def test_mean_reward_average(self):
        curator = SkillOSCurator()
        cfg = CurationRewardConfig()
        d1 = _decision(CurationAction.INSERT, "s1")
        d2 = _decision(CurationAction.INSERT, "s2")
        curator.submit(d1)
        curator.submit(d2)
        r1 = CurationReward(task_outcome=1.0)
        r2 = CurationReward(task_outcome=0.0)
        curator.record_reward(d1, r1)
        curator.record_reward(d2, r2)
        expected = (r1.total(cfg) + r2.total(cfg)) / 2
        assert curator.mean_reward() == pytest.approx(expected)


class TestActionDistribution:
    def test_distribution_counts(self):
        curator = SkillOSCurator()
        curator.submit(_decision(CurationAction.INSERT, "s1"))
        curator.submit(_decision(CurationAction.INSERT, "s2"))
        curator.submit(_decision(CurationAction.DELETE, "s1"))
        dist = curator.action_distribution()
        assert dist["insert"] == 2
        assert dist["delete"] == 1
        assert dist["update"] == 0
        assert dist["noop"] == 0

    def test_distribution_all_keys_present(self):
        curator = SkillOSCurator()
        dist = curator.action_distribution()
        for action in CurationAction:
            assert action.value in dist


class TestTaskGroup:
    def test_task_group_fields(self):
        tg = TaskGroup(
            group_id="g1",
            training_tasks=["t1", "t2"],
            evaluation_tasks=["e1"],
        )
        assert tg.group_id == "g1"
        assert len(tg.training_tasks) == 2
        assert len(tg.evaluation_tasks) == 1
