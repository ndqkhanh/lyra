"""Tests for harness_core.skill_auto — extract + promote skills from trajectories."""
from __future__ import annotations

import pytest

from harness_core.forensic import Trajectory, TrajectoryOutcome
from harness_core.marketplace import PromotedSkill
from harness_core.orchestration import AgentDecision
from harness_core.provenance import WitnessLattice
from harness_core.skill_auto import (
    PromotionVerdict,
    SkillCandidate,
    SkillExtractor,
    SkillPromoter,
)


def _make_traj(
    *,
    tid: str,
    task: str,
    actions: list[str],
    outcome: TrajectoryOutcome = TrajectoryOutcome.SUCCESS,
) -> Trajectory:
    decisions = tuple(
        AgentDecision(action=a, fingerprint=f"{tid}-{i}")
        for i, a in enumerate(actions)
    )
    return Trajectory(
        trajectory_id=tid,
        task_signature=task,
        decisions=decisions,
        outcome=outcome,
    )


# --- SkillCandidate -----------------------------------------------------


class TestSkillCandidate:
    def test_create_auto_id(self):
        c = SkillCandidate.create(
            name="x",
            task_signature_pattern="t",
            action_template=("a", "b"),
            source_trajectories=("t1",),
            occurrence_count=1,
            success_rate=1.0,
        )
        assert c.candidate_id  # non-empty hash
        assert len(c.candidate_id) == 16

    def test_same_inputs_same_id(self):
        c1 = SkillCandidate.create(
            name="x", task_signature_pattern="t", action_template=("a", "b"),
            source_trajectories=("t1",), occurrence_count=1, success_rate=1.0,
        )
        c2 = SkillCandidate.create(
            name="x", task_signature_pattern="different_pattern", action_template=("a", "b"),
            source_trajectories=("t99",), occurrence_count=5, success_rate=0.5,
        )
        # ID is determined by name + action_template only.
        assert c1.candidate_id == c2.candidate_id

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            SkillCandidate.create(
                name="", task_signature_pattern="t", action_template=("a",),
                source_trajectories=(), occurrence_count=1, success_rate=1.0,
            )

    def test_empty_action_template_rejected(self):
        with pytest.raises(ValueError):
            SkillCandidate.create(
                name="x", task_signature_pattern="t", action_template=(),
                source_trajectories=(), occurrence_count=1, success_rate=1.0,
            )

    def test_invalid_success_rate(self):
        with pytest.raises(ValueError):
            SkillCandidate.create(
                name="x", task_signature_pattern="t", action_template=("a",),
                source_trajectories=(), occurrence_count=1, success_rate=1.5,
            )

    def test_zero_occurrence_rejected(self):
        with pytest.raises(ValueError):
            SkillCandidate.create(
                name="x", task_signature_pattern="t", action_template=("a",),
                source_trajectories=(), occurrence_count=0, success_rate=1.0,
            )


class TestPromotionVerdict:
    def test_invalid_eval_score(self):
        c = SkillCandidate.create(
            name="x", task_signature_pattern="t", action_template=("a",),
            source_trajectories=(), occurrence_count=1, success_rate=1.0,
        )
        with pytest.raises(ValueError):
            PromotionVerdict(
                candidate=c, promoted=True,
                eval_score=1.5, surrogate_passed=True,
            )


# --- SkillExtractor -----------------------------------------------------


class TestSkillExtractor:
    def test_finds_repeated_pattern(self):
        trajs = [
            _make_traj(tid="t1", task="refactor", actions=["read", "edit", "test"]),
            _make_traj(tid="t2", task="refactor", actions=["read", "edit", "test"]),
            _make_traj(tid="t3", task="refactor", actions=["read", "edit", "test"]),
        ]
        candidates = SkillExtractor(min_occurrences=2).extract(trajs)
        assert len(candidates) == 1
        assert candidates[0].action_template == ("read", "edit", "test")
        assert candidates[0].occurrence_count == 3
        assert candidates[0].success_rate == 1.0

    def test_filters_below_min_occurrences(self):
        trajs = [_make_traj(tid="t1", task="x", actions=["a", "b"])]  # only 1
        candidates = SkillExtractor(min_occurrences=2).extract(trajs)
        assert candidates == []

    def test_filters_below_success_rate(self):
        # 3 trajectories with same template but only 1 success.
        trajs = [
            _make_traj(tid="t1", task="x", actions=["a"], outcome=TrajectoryOutcome.SUCCESS),
            _make_traj(tid="t2", task="x", actions=["a"], outcome=TrajectoryOutcome.FAILURE),
            _make_traj(tid="t3", task="x", actions=["a"], outcome=TrajectoryOutcome.FAILURE),
        ]
        # Success rate = 1/3 ≈ 0.33; below 0.7 default.
        candidates = SkillExtractor(min_success_rate=0.7).extract(trajs)
        assert candidates == []

    def test_passes_when_success_rate_meets(self):
        trajs = [
            _make_traj(tid="t1", task="x", actions=["a"], outcome=TrajectoryOutcome.SUCCESS),
            _make_traj(tid="t2", task="x", actions=["a"], outcome=TrajectoryOutcome.SUCCESS),
            _make_traj(tid="t3", task="x", actions=["a"], outcome=TrajectoryOutcome.FAILURE),
        ]
        # Success rate = 2/3 ≈ 0.67. With threshold 0.5, passes.
        candidates = SkillExtractor(min_success_rate=0.5).extract(trajs)
        assert len(candidates) == 1
        assert candidates[0].success_rate == pytest.approx(2 / 3, abs=1e-3)

    def test_groups_by_task_signature(self):
        # Same actions, different task signatures → two separate candidates.
        trajs = [
            _make_traj(tid="t1", task="A", actions=["x"]),
            _make_traj(tid="t2", task="A", actions=["x"]),
            _make_traj(tid="t3", task="B", actions=["x"]),
            _make_traj(tid="t4", task="B", actions=["x"]),
        ]
        candidates = SkillExtractor(min_occurrences=2).extract(trajs)
        task_sigs = {c.task_signature_pattern for c in candidates}
        assert task_sigs == {"A", "B"}

    def test_skips_empty_trajectories(self):
        # Trajectory with no decisions should be skipped, not crash.
        trajs = [
            _make_traj(tid="t1", task="x", actions=[]),
            _make_traj(tid="t2", task="x", actions=[]),
        ]
        candidates = SkillExtractor(min_occurrences=2).extract(trajs)
        assert candidates == []

    def test_empty_corpus_returns_empty(self):
        assert SkillExtractor().extract([]) == []

    def test_invalid_min_occurrences_rejected(self):
        with pytest.raises(ValueError):
            SkillExtractor(min_occurrences=1)
        with pytest.raises(ValueError):
            SkillExtractor(min_occurrences=0)

    def test_invalid_min_success_rate_rejected(self):
        with pytest.raises(ValueError):
            SkillExtractor(min_success_rate=1.5)
        with pytest.raises(ValueError):
            SkillExtractor(min_success_rate=-0.1)

    def test_orders_by_occurrence_desc(self):
        trajs = [
            _make_traj(tid=f"t{i}", task="A", actions=["x"]) for i in range(5)
        ] + [
            _make_traj(tid=f"u{i}", task="B", actions=["y"]) for i in range(2)
        ]
        candidates = SkillExtractor(min_occurrences=2).extract(trajs)
        assert candidates[0].task_signature_pattern == "A"
        assert candidates[0].occurrence_count > candidates[1].occurrence_count

    def test_custom_name_generator(self):
        def custom(task_sig, template):
            return f"custom:{task_sig}:{len(template)}"

        trajs = [
            _make_traj(tid=f"t{i}", task="refactor", actions=["a", "b"])
            for i in range(2)
        ]
        candidates = SkillExtractor(
            min_occurrences=2,
            name_generator=custom,
        ).extract(trajs)
        assert candidates[0].name == "custom:refactor:2"


# --- SkillPromoter ------------------------------------------------------


def _candidate(name: str = "x") -> SkillCandidate:
    return SkillCandidate.create(
        name=name,
        task_signature_pattern="t",
        action_template=("a",),
        source_trajectories=("t1",),
        occurrence_count=2,
        success_rate=1.0,
    )


class TestSkillPromoter:
    def test_both_gates_pass_promotes(self):
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.9,
            surrogate_verifier=lambda c: True,
            min_eval_score=0.7,
        )
        verdict = promoter.evaluate(_candidate())
        assert verdict.promoted is True
        assert "promoted" in verdict.reason

    def test_eval_below_threshold_rejects(self):
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.5,
            surrogate_verifier=lambda c: True,
            min_eval_score=0.7,
        )
        verdict = promoter.evaluate(_candidate())
        assert verdict.promoted is False
        assert verdict.eval_score == 0.5

    def test_surrogate_fail_rejects(self):
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.95,
            surrogate_verifier=lambda c: False,
            min_eval_score=0.7,
        )
        verdict = promoter.evaluate(_candidate())
        assert verdict.promoted is False
        assert "surrogate" in verdict.reason
        assert verdict.surrogate_passed is False

    def test_eval_raises_recorded_as_failure(self):
        def broken_eval(c):
            raise RuntimeError("eval down")

        promoter = SkillPromoter(
            held_out_evaluator=broken_eval,
            surrogate_verifier=lambda c: True,
        )
        verdict = promoter.evaluate(_candidate())
        assert verdict.promoted is False
        assert "eval down" in verdict.reason

    def test_surrogate_raises_recorded_as_failure(self):
        def broken_surrogate(c):
            raise RuntimeError("surrogate down")

        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.9,
            surrogate_verifier=broken_surrogate,
        )
        verdict = promoter.evaluate(_candidate())
        assert verdict.promoted is False
        assert "surrogate down" in verdict.reason

    def test_eval_out_of_range_recorded_as_failure(self):
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 1.5,  # out of range
            surrogate_verifier=lambda c: True,
        )
        verdict = promoter.evaluate(_candidate())
        assert verdict.promoted is False
        assert "out-of-range" in verdict.reason

    def test_promote_returns_promoted_skill_on_success(self):
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.9,
            surrogate_verifier=lambda c: True,
        )
        candidate = _candidate(name="fix-imports")
        skill = promoter.promote(candidate)
        assert skill is not None
        assert isinstance(skill, PromotedSkill)
        assert skill.name == "fix-imports"
        assert skill.eval_score == 0.9
        assert skill.source_project == "auto_creator"

    def test_promote_returns_none_on_rejection(self):
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.5,
            surrogate_verifier=lambda c: True,
        )
        skill = promoter.promote(_candidate())
        assert skill is None

    def test_invalid_min_eval_score_rejected(self):
        with pytest.raises(ValueError):
            SkillPromoter(
                held_out_evaluator=lambda c: 0.5,
                surrogate_verifier=lambda c: True,
                min_eval_score=1.5,
            )

    def test_provenance_lattice_records_witness(self):
        lattice = WitnessLattice()
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.9,
            surrogate_verifier=lambda c: True,
            provenance_lattice=lattice,
        )
        promoter.evaluate(_candidate())
        # A witness should have been recorded.
        witnesses = lattice.ledger.witnesses_for(issued_by="skill_promoter")
        assert len(witnesses) == 1
        # Content includes the candidate id + verdict.
        w = witnesses[0]
        assert w.content["promoted"] is True

    def test_provenance_records_rejection_too(self):
        lattice = WitnessLattice()
        promoter = SkillPromoter(
            held_out_evaluator=lambda c: 0.1,  # below threshold
            surrogate_verifier=lambda c: True,
            provenance_lattice=lattice,
        )
        promoter.evaluate(_candidate())
        witnesses = lattice.ledger.witnesses_for(issued_by="skill_promoter")
        assert len(witnesses) == 1
        assert witnesses[0].content["promoted"] is False


# --- End-to-end --------------------------------------------------------


class TestEndToEndSkillAutoCreation:
    """Realistic scenario: corpus of 6 trajectories → extract → promote."""

    def test_full_pipeline(self):
        # 4 trajectories of the 'refactor' pattern, 3 successful + 1 failed.
        # 2 trajectories of 'one-shot' pattern, both successful.
        # Refactor: 3/4 success = 0.75 → passes 0.7 threshold.
        # One-shot: only 2 trajectories, both successful → passes.
        trajs = [
            _make_traj(tid="r1", task="refactor", actions=["read", "edit", "test"]),
            _make_traj(tid="r2", task="refactor", actions=["read", "edit", "test"]),
            _make_traj(tid="r3", task="refactor", actions=["read", "edit", "test"]),
            _make_traj(tid="r4", task="refactor", actions=["read", "edit", "test"],
                        outcome=TrajectoryOutcome.FAILURE),
            _make_traj(tid="o1", task="one-shot", actions=["compute"]),
            _make_traj(tid="o2", task="one-shot", actions=["compute"]),
        ]
        # Extract candidates.
        extractor = SkillExtractor(min_occurrences=2, min_success_rate=0.7)
        candidates = extractor.extract(trajs)
        assert len(candidates) == 2
        assert {c.task_signature_pattern for c in candidates} == {"refactor", "one-shot"}

        # Promote with a stub eval that scores higher for richer templates.
        def evaluator(c):
            # Reward longer templates (more nuanced skills).
            return min(0.95, 0.5 + 0.15 * len(c.action_template))

        def surrogate(c):
            # Surrogate accepts both.
            return True

        lattice = WitnessLattice()
        promoter = SkillPromoter(
            held_out_evaluator=evaluator,
            surrogate_verifier=surrogate,
            min_eval_score=0.7,
            provenance_lattice=lattice,
        )
        promoted = []
        for c in candidates:
            skill = promoter.promote(c)
            if skill is not None:
                promoted.append(skill)
        # Refactor (3 actions, score=0.95) passes; one-shot (1 action, score=0.65) fails.
        assert len(promoted) == 1
        assert promoted[0].name.startswith("refactor")
        # Both verdicts (1 promote + 1 reject) recorded.
        assert len(lattice.ledger.witnesses_for(issued_by="skill_promoter")) == 2
