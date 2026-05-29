"""Skill distillation — convert extracted patterns into verified, reusable skills.

Takes patterns from ``ExperienceExtractor``, proposes skill candidates,
evaluates them, and distills verified skills ready for deployment into the
skill registry.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from lyra_core.experience.extractor import ExtractedPattern, PatternType


@dataclass(frozen=True)
class SkillCandidate:
    """A candidate skill identified from experience patterns."""

    id: str
    name: str
    description: str
    trigger_condition: str
    source_patterns: tuple[str, ...]
    confidence: float
    usage_estimate: int = 0


@dataclass(frozen=True)
class DistilledSkill:
    """A fully distilled, verified skill ready for deployment."""

    id: str
    name: str
    description: str
    body: str
    source_candidates: tuple[str, ...]
    verification_score: float
    verified: bool
    deployed: bool = False
    created_at: float = field(default_factory=time.time)
    deployed_at: float | None = None

    def deploy(self) -> DistilledSkill:
        return DistilledSkill(
            id=self.id, name=self.name, description=self.description,
            body=self.body, source_candidates=self.source_candidates,
            verification_score=self.verification_score, verified=self.verified,
            deployed=True, created_at=self.created_at,
            deployed_at=time.time(),
        )

    def undeploy(self) -> DistilledSkill:
        return DistilledSkill(
            id=self.id, name=self.name, description=self.description,
            body=self.body, source_candidates=self.source_candidates,
            verification_score=self.verification_score, verified=self.verified,
            deployed=False, created_at=self.created_at, deployed_at=None,
        )


@dataclass(frozen=True)
class DistillationResult:
    """Outcome of a distillation run."""

    run_id: str
    candidates_evaluated: int
    skills_distilled: int
    skills_deployed: int
    skills_rejected: int
    rejection_reasons: tuple[str, ...]
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SkillDistiller:
    """Converts extracted patterns into reusable, verified skills.

    Usage::

        distiller = SkillDistiller(min_confidence=0.7)
        candidates = distiller.propose_candidates(patterns)
        result = distiller.distill(candidates)
        distiller.deploy(skill_id)
    """

    min_confidence: float = 0.7
    require_verification: bool = True
    max_skills_per_run: int = 5
    _candidates: list[SkillCandidate] = field(default_factory=list)
    _skills: dict[str, DistilledSkill] = field(default_factory=dict)
    _results: list[DistillationResult] = field(default_factory=list)

    def propose_candidates(self,
                           patterns: Sequence[ExtractedPattern]) -> tuple[SkillCandidate, ...]:
        """Propose skill candidates from extracted patterns."""
        candidates: list[SkillCandidate] = []
        for pattern in patterns:
            if pattern.confidence < self.min_confidence:
                continue
            if pattern.pattern_type not in (PatternType.SUCCESS_STRATEGY,
                                            PatternType.OPTIMIZATION,
                                            PatternType.WORKAROUND):
                continue

            candidate = SkillCandidate(
                id=uuid.uuid4().hex,
                name=_candidate_name(pattern),
                description=pattern.description,
                trigger_condition=f"When task matches: {pattern.title}",
                source_patterns=(pattern.id,),
                confidence=pattern.confidence,
                usage_estimate=max(1, len(pattern.tags)),
            )
            candidates.append(candidate)

        self._candidates.extend(candidates)
        return tuple(candidates[: self.max_skills_per_run])

    def evaluate_candidate(self, candidate: SkillCandidate) -> float:
        """Evaluate a skill candidate. Returns a verification score 0.0-1.0."""
        score = candidate.confidence
        if candidate.usage_estimate >= 3:
            score += 0.1
        if len(candidate.source_patterns) >= 2:
            score += 0.1
        return min(score, 1.0)

    def distill(self, candidates: Sequence[SkillCandidate]) -> DistillationResult:
        """Distill candidates into verified skills."""
        start = time.time()
        distilled = 0
        deployed = 0
        rejected = 0
        reasons: list[str] = []

        for candidate in candidates:
            score = self.evaluate_candidate(candidate)

            if self.require_verification and score < self.min_confidence:
                rejected += 1
                reasons.append(f"{candidate.name}: score {score:.2f} below threshold")
                continue

            skill = DistilledSkill(
                id=uuid.uuid4().hex,
                name=candidate.name,
                description=candidate.description,
                body=f"# {candidate.name}\n\n{candidate.description}\n\n"
                     f"Trigger: {candidate.trigger_condition}",
                source_candidates=(candidate.id,),
                verification_score=score,
                verified=score >= self.min_confidence,
            )
            self._skills[skill.id] = skill
            distilled += 1

            if skill.verified and score >= 0.85:
                self._skills[skill.id] = skill.deploy()
                deployed += 1

        result = DistillationResult(
            run_id=uuid.uuid4().hex,
            candidates_evaluated=len(candidates),
            skills_distilled=distilled,
            skills_deployed=deployed,
            skills_rejected=rejected,
            rejection_reasons=tuple(reasons),
            duration_ms=(time.time() - start) * 1000,
        )
        self._results.append(result)
        return result

    def deploy(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if skill and skill.verified and not skill.deployed:
            self._skills[skill_id] = skill.deploy()
            return True
        return False

    def undeploy(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if skill and skill.deployed:
            self._skills[skill_id] = skill.undeploy()
            return True
        return False

    def get_deployed(self) -> tuple[DistilledSkill, ...]:
        return tuple(s for s in self._skills.values() if s.deployed)

    def get_by_name(self, name: str) -> DistilledSkill | None:
        for s in self._skills.values():
            if s.name == name:
                return s
        return None

    @property
    def deployed_count(self) -> int:
        return sum(1 for s in self._skills.values() if s.deployed)

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)


def _candidate_name(pattern: ExtractedPattern) -> str:
    """Derive a skill name from a pattern title."""
    name = pattern.title.replace(":", "").replace("  ", " ")
    if len(name) > 80:
        name = name[:77] + "..."
    return name
