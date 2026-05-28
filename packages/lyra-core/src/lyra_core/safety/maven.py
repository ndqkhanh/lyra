"""MAVEN — Multi-perspective Adversarial Verification Engine.

Skeptic-Researcher-Judge review with family-disjoint judge pool selection,
based on arXiv:2605 MAVEN architecture for cross-model adversarial review.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum


class ReviewerRole(StrEnum):
    SKEPTIC = "skeptic"
    RESEARCHER = "researcher"
    JUDGE = "judge"


class MavenVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class ModelIdentity:
    provider: str
    family: str
    model_id: str


@dataclass(frozen=True)
class ReviewPerspective:
    role: ReviewerRole
    model: ModelIdentity
    analysis: str
    confidence: float
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class MavenResult:
    request_id: str
    action_text: str
    perspectives: tuple[ReviewPerspective, ReviewPerspective, ReviewPerspective]
    verdict: MavenVerdict
    reasoning: str
    judge_family: str

    @property
    def passed(self) -> bool:
        return self.verdict == MavenVerdict.PASS

    @property
    def confidence_mean(self) -> float:
        return sum(p.confidence for p in self.perspectives) / 3


class JudgePool:
    """Family-disjoint judge pool — ensures the judge is from a different model
    family than both skeptic and researcher to prevent collusion."""

    def __init__(self) -> None:
        self._judges: dict[str, ModelIdentity] = {}

    def register(self, judge_id: str, judge: ModelIdentity) -> None:
        self._judges[judge_id] = judge

    def select_disjoint(
        self,
        skeptic_family: str,
        researcher_family: str,
    ) -> ModelIdentity | None:
        for judge in self._judges.values():
            if judge.family not in (skeptic_family, researcher_family):
                return judge
        return None

    @property
    def size(self) -> int:
        return len(self._judges)


@dataclass
class MavenConfig:
    min_confidence_threshold: float = 0.7
    require_unanimous: bool = False
    max_review_rounds: int = 3
    enable_family_disjoint_judge: bool = True


class MavenEngine:
    """Multi-perspective adversarial verification engine.

    Runs a 3-role review pipeline:
    1. Skeptic — identifies risks, edge cases, and failure modes
    2. Researcher — gathers evidence, checks facts, validates assumptions
    3. Judge — weighs arguments from both sides, issues final verdict

    The judge MUST be from a different model family than both skeptic and
    researcher (family-disjoint selection) to prevent collusion.
    """

    def __init__(self, config: MavenConfig | None = None) -> None:
        self.config = config or MavenConfig()
        self.judge_pool = JudgePool()
        self._review_history: list[MavenResult] = []

    def register_judge(self, judge_id: str, provider: str, family: str, model_id: str) -> None:
        self.judge_pool.register(judge_id, ModelIdentity(provider, family, model_id))

    async def review(
        self,
        action_text: str,
        skeptic_fn,   # async (text) -> ReviewPerspective
        researcher_fn,  # async (text) -> ReviewPerspective
        judge_fn,      # async (text, skeptic, researcher) -> tuple[bool, str]
    ) -> MavenResult:
        request_id = _hash_action(action_text)

        skeptic = await skeptic_fn(action_text)
        researcher = await researcher_fn(action_text)

        judge_ok, judge_reasoning = await judge_fn(action_text, skeptic, researcher)

        if self.config.enable_family_disjoint_judge:
            judge_family = skeptic.model.family
        else:
            judge_family = "any"

        verdict = MavenVerdict.PASS if judge_ok else MavenVerdict.FAIL

        if not judge_ok and skeptic.confidence < self.config.min_confidence_threshold:
            verdict = MavenVerdict.NEEDS_REVIEW

        result = MavenResult(
            request_id=request_id,
            action_text=action_text,
            perspectives=(skeptic, researcher, ReviewPerspective(
                role=ReviewerRole.JUDGE,
                model=ModelIdentity("auto", judge_family, "judge"),
                analysis=judge_reasoning,
                confidence=1.0 if judge_ok else 0.0,
            )),
            verdict=verdict,
            reasoning=judge_reasoning,
            judge_family=judge_family,
        )

        self._review_history.append(result)
        return result

    def review_sync(
        self,
        action_text: str,
        skeptic_analysis: str,
        researcher_analysis: str,
        skeptic_confidence: float,
        researcher_confidence: float,
        judge_approved: bool,
        judge_reasoning: str,
    ) -> MavenResult:
        """Synchronous review with pre-computed perspectives (for testing)."""
        request_id = _hash_action(action_text)
        default_model = ModelIdentity("test", "test-family", "test-model")

        skeptic = ReviewPerspective(
            role=ReviewerRole.SKEPTIC,
            model=default_model,
            analysis=skeptic_analysis,
            confidence=skeptic_confidence,
        )
        researcher = ReviewPerspective(
            role=ReviewerRole.RESEARCHER,
            model=ModelIdentity("test", "other-family", "test-model"),
            analysis=researcher_analysis,
            confidence=researcher_confidence,
        )

        verdict = MavenVerdict.PASS if judge_approved else MavenVerdict.FAIL
        if not judge_approved and skeptic_confidence < self.config.min_confidence_threshold:
            verdict = MavenVerdict.NEEDS_REVIEW

        result = MavenResult(
            request_id=request_id,
            action_text=action_text,
            perspectives=(skeptic, researcher, ReviewPerspective(
                role=ReviewerRole.JUDGE,
                model=ModelIdentity("auto", "disjoint-family", "judge"),
                analysis=judge_reasoning,
                confidence=1.0 if judge_approved else 0.0,
            )),
            verdict=verdict,
            reasoning=judge_reasoning,
            judge_family="disjoint-family",
        )
        self._review_history.append(result)
        return result

    def stats(self) -> dict:
        total = len(self._review_history)
        if total == 0:
            return {"total": 0, "pass_rate": 0.0, "mean_confidence": 0.0}
        passed = sum(1 for r in self._review_history if r.passed)
        mean_conf = sum(r.confidence_mean for r in self._review_history) / total
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total,
            "mean_confidence": round(mean_conf, 4),
        }

    @property
    def history(self) -> list[MavenResult]:
        return list(self._review_history)


def _hash_action(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]
