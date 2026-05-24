"""SkillPromoter — gate candidates with held-out eval + surrogate verifier.

Per [docs/169-coevoskills-co-evolutionary-verification.md] — the *info-isolated
surrogate verifier* gives +30pp ablation lift over LLM-as-judge alone. The
promoter runs both gates: held-out eval (does the candidate beat baseline?) +
surrogate verifier (does an information-isolated judge agree the pattern is
sound?). Both must pass for promotion.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..marketplace import PromotedSkill
from ..provenance import Witness, WitnessKind, WitnessLattice
from .types import PromotionVerdict, SkillCandidate


_HeldOutEvaluator = Callable[[SkillCandidate], float]
_SurrogateVerifier = Callable[[SkillCandidate], bool]


@dataclass
class SkillPromoter:
    """Promote (or reject) skill candidates with two gates.

    1. ``held_out_evaluator(candidate) -> float`` returns a score in [0, 1]
       representing how well the candidate generalises to held-out tasks.
       Production wires this to a real eval harness; tests use a stub.
    2. ``surrogate_verifier(candidate) -> bool`` is the info-isolated co-eval
       judge from [docs/169]. Production wires a separate-context LLM that
       sees the candidate but NOT the source trajectories.
    3. Optional ``provenance_lattice`` records the verdict + cites source
       trajectories as parent witnesses.

    >>> def fake_eval(c): return 0.9
    >>> def fake_verifier(c): return True
    >>> promoter = SkillPromoter(
    ...     held_out_evaluator=fake_eval,
    ...     surrogate_verifier=fake_verifier,
    ...     min_eval_score=0.7,
    ... )
    >>> from harness_core.skill_auto import SkillCandidate
    >>> candidate = SkillCandidate.create(
    ...     name="x", task_signature_pattern="t", action_template=("a",),
    ...     source_trajectories=("t1",), occurrence_count=1, success_rate=1.0,
    ... )
    >>> verdict = promoter.evaluate(candidate)
    >>> verdict.promoted
    True
    """

    held_out_evaluator: _HeldOutEvaluator
    surrogate_verifier: _SurrogateVerifier
    min_eval_score: float = 0.7
    provenance_lattice: Optional[WitnessLattice] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_eval_score <= 1.0:
            raise ValueError(
                f"min_eval_score must be in [0, 1], got {self.min_eval_score}"
            )

    def evaluate(self, candidate: SkillCandidate) -> PromotionVerdict:
        """Run both gates; return a typed verdict."""
        # 1. Held-out eval.
        try:
            score = self.held_out_evaluator(candidate)
        except Exception as exc:
            verdict = PromotionVerdict(
                candidate=candidate,
                promoted=False,
                eval_score=0.0,
                surrogate_passed=False,
                reason=f"eval raised {exc.__class__.__name__}: {exc}",
            )
            self._record_witness(verdict)
            return verdict

        if not 0.0 <= score <= 1.0:
            verdict = PromotionVerdict(
                candidate=candidate,
                promoted=False,
                eval_score=0.0,
                surrogate_passed=False,
                reason=f"eval returned out-of-range score: {score}",
            )
            self._record_witness(verdict)
            return verdict

        # 2. Surrogate verifier.
        try:
            surrogate_passed = bool(self.surrogate_verifier(candidate))
        except Exception as exc:
            verdict = PromotionVerdict(
                candidate=candidate,
                promoted=False,
                eval_score=score,
                surrogate_passed=False,
                reason=f"surrogate raised {exc.__class__.__name__}: {exc}",
            )
            self._record_witness(verdict)
            return verdict

        # 3. Combined decision.
        eval_passed = score >= self.min_eval_score
        promoted = eval_passed and surrogate_passed
        if promoted:
            reason = (
                f"promoted: eval_score={score:.3f} >= {self.min_eval_score:.3f}; "
                f"surrogate verifier passed"
            )
        elif not eval_passed:
            reason = f"rejected: eval_score={score:.3f} < {self.min_eval_score:.3f}"
        else:
            reason = "rejected: surrogate verifier failed"

        verdict = PromotionVerdict(
            candidate=candidate,
            promoted=promoted,
            eval_score=score,
            surrogate_passed=surrogate_passed,
            reason=reason,
        )
        self._record_witness(verdict)
        return verdict

    def promote(self, candidate: SkillCandidate) -> Optional[PromotedSkill]:
        """Run :meth:`evaluate` and produce a :class:`PromotedSkill` on success."""
        verdict = self.evaluate(candidate)
        if not verdict.promoted:
            return None
        return PromotedSkill(
            name=candidate.name,
            description=(
                f"Auto-promoted skill: {candidate.task_signature_pattern} task class. "
                f"Action template: {' → '.join(candidate.action_template)}. "
                f"Observed in {candidate.occurrence_count} trajectories with "
                f"{candidate.success_rate:.0%} success rate."
            ),
            source_project="auto_creator",
            promoted_at=time.time(),
            occurrence_count=candidate.occurrence_count,
            eval_score=verdict.eval_score,
        )

    def _record_witness(self, verdict: PromotionVerdict) -> Optional[Witness]:
        """If a provenance lattice is wired, record the verdict + cite source
        trajectories. Returns the Witness or None."""
        if self.provenance_lattice is None:
            return None
        # Source-trajectory witnesses don't necessarily exist in the ledger;
        # we record the IDs as content rather than as parent witnesses to
        # avoid the parent-must-exist constraint failing on external IDs.
        witness = Witness.create(
            kind=WitnessKind.CUSTOM,
            issued_by="skill_promoter",
            content={
                "candidate_id": verdict.candidate.candidate_id,
                "candidate_name": verdict.candidate.name,
                "promoted": verdict.promoted,
                "eval_score": verdict.eval_score,
                "surrogate_passed": verdict.surrogate_passed,
                "source_trajectories": list(verdict.candidate.source_trajectories),
                "reason": verdict.reason,
            },
        )
        return self.provenance_lattice.ledger.append(witness)


__all__ = ["SkillPromoter"]
