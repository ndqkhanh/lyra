"""RED tests for v1.8 Wave-1 §3.3 — Skill-RAG hidden-state prober + 4-skill router."""
from __future__ import annotations

import pytest

from lyra_core.retrieval import (
    HiddenStateProber,
    ProberVerdict,
    RecoverySkill,
    RetrievalAttempt,
    RetrievalResult,
    SkillRagRouter,
)


class _StubProber(HiddenStateProber):
    def __init__(self, recommend: RecoverySkill, confidence: float = 0.9) -> None:
        self._recommend = recommend
        self._conf = confidence

    def diagnose(self, question, attempt, hidden_state) -> ProberVerdict:  # type: ignore[override]
        return ProberVerdict(
            recommended_skill=self._recommend,
            confidence=self._conf,
            rationale=f"stub: always {self._recommend.value}",
        )


class _StubHandler:
    def __init__(self, skill: RecoverySkill, *, answer: str | None) -> None:
        self.skill = skill
        self._answer = answer

    def recover(self, question, attempt) -> RetrievalResult:
        return RetrievalResult(
            answer=self._answer,
            used_skill=self.skill,
            rounds=(attempt,),
            verdict=ProberVerdict(
                recommended_skill=self.skill,
                confidence=1.0,
                rationale="stub handler",
            ),
            cost_tokens=10,
        )


def _all_handlers(answer: str | None = "ok"):
    return {
        s: _StubHandler(s, answer=(None if s is RecoverySkill.EXIT else answer))
        for s in RecoverySkill
    }


def test_recovery_skill_enum_has_exactly_four_options() -> None:
    """Skill-RAG's identity: four mutually exclusive recovery actions."""
    assert {s.value for s in RecoverySkill} == {
        "query_rewriting",
        "question_decomposition",
        "evidence_focusing",
        "exit",
    }


def test_router_rejects_handler_set_with_a_missing_skill() -> None:
    handlers = _all_handlers()
    handlers.pop(RecoverySkill.EXIT)
    with pytest.raises(ValueError, match="exit"):
        SkillRagRouter(prober=_StubProber(RecoverySkill.EXIT), handlers=handlers)


def test_retrieval_attempt_validates_aligned_lengths() -> None:
    with pytest.raises(ValueError):
        RetrievalAttempt(
            query="q",
            documents=("a", "b", "c"),
            scores=(0.9, 0.8),
        )


def test_router_dispatches_to_recommended_skill() -> None:
    """Prober → router → handler.recover wired correctly for each skill."""
    for skill in RecoverySkill:
        router = SkillRagRouter(
            prober=_StubProber(skill),
            handlers=_all_handlers(),
        )
        result = router.answer(
            question="anything",
            first_attempt=RetrievalAttempt(query="q", documents=("d",), scores=(0.1,)),
            hidden_state=[0.0, 1.0],
        )
        assert result.used_skill is skill


def test_exit_skill_yields_none_answer() -> None:
    """EXIT is the only path that returns ``None`` instead of hallucinating."""
    router = SkillRagRouter(
        prober=_StubProber(RecoverySkill.EXIT),
        handlers=_all_handlers(),
    )
    result = router.answer(
        question="unanswerable",
        first_attempt=RetrievalAttempt(query="q", documents=(), scores=()),
        hidden_state=[0.0],
    )
    assert result.answer is None
    assert result.used_skill is RecoverySkill.EXIT


def test_router_honours_max_rounds_cap() -> None:
    router = SkillRagRouter(
        prober=_StubProber(RecoverySkill.QUERY_REWRITING),
        handlers=_all_handlers(),
        max_rounds=2,
    )
    result = router.answer(
        question="loop forever?",
        first_attempt=RetrievalAttempt(query="q", documents=("d",), scores=(0.1,)),
        hidden_state=[0.0],
    )
    assert len(result.rounds) <= 2
