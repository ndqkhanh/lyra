"""Tests for Feedback Descent Optimizer."""

import pytest

from lyra_memory.optimization.feedback_descent import (
    FeedbackDescentOptimizer,
    FeedbackPair,
)


class StubLLM:
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self._idx = 0
        self.prompts: list[str] = []

    @property
    def responses(self) -> list[str]:
        return self._responses

    @responses.setter
    def responses(self, value: list[str]) -> None:
        self._responses = value
        self._idx = 0

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return '{"winner": "a", "rationale": "default", "reset": false}'


class TestFeedbackPair:
    def test_default_values(self):
        p = FeedbackPair(candidate_a="a", candidate_b="b", winner="a", rationale="better")
        assert p.candidate_a == "a"
        assert p.candidate_b == "b"
        assert p.winner == "a"
        assert p.rationale == "better"
        assert p.reset is False

    def test_is_decisive(self):
        p1 = FeedbackPair(candidate_a="a", candidate_b="b", winner="a")
        assert p1.is_decisive is True

        p2 = FeedbackPair(candidate_a="a", candidate_b="b", winner="tie")
        assert p2.is_decisive is False

    def test_auto_id(self):
        p1 = FeedbackPair(candidate_a="a", candidate_b="b", winner="a")
        p2 = FeedbackPair(candidate_a="a", candidate_b="b", winner="a")
        assert p1.id != p2.id

    def test_with_reset(self):
        p = FeedbackPair(
            candidate_a="a", candidate_b="b", winner="b", rationale="breakthrough", reset=True,
        )
        assert p.winner == "b"
        assert p.reset is True


class TestFeedbackDescentOptimizer:
    def _make_optimizer(
        self, responses: list[str] | None = None, max_iterations: int = 3,
    ) -> FeedbackDescentOptimizer:
        llm = StubLLM(responses=responses)
        return FeedbackDescentOptimizer(llm=llm, max_iterations=max_iterations)

    async def test_optimize_returns_string(self):
        opt = self._make_optimizer(responses=[
            "improved version of the prompt",
            '{"winner": "b", "rationale": "proposal is clearer", "reset": false}',
        ])
        result = await opt.optimize("initial prompt", iterations=1)
        assert isinstance(result, str)
        assert result == "improved version of the prompt"

    async def test_optimize_uses_proposal_when_better(self):
        responses = [
            "proposal version",
            '{"winner": "b", "rationale": "proposal is better", "reset": false}',
        ]
        opt = self._make_optimizer(responses=responses)
        result = await opt.optimize("current version", iterations=1)
        assert result == "proposal version"

    async def test_optimize_keeps_current_when_worse(self):
        responses = [
            "worse version",
            '{"winner": "a", "rationale": "current is better", "reset": false}',
        ]
        opt = self._make_optimizer(responses=responses)
        result = await opt.optimize("current good version", iterations=1)
        assert result == "current good version"

    async def test_optimize_keeps_current_on_tie(self):
        responses = [
            "similar version",
            '{"winner": "tie", "rationale": "no clear winner", "reset": false}',
        ]
        opt = self._make_optimizer(responses=responses)
        result = await opt.optimize("original", iterations=1)
        assert result == "original"

    async def test_reset_clears_history_on_breakthrough(self):
        responses = [
            "breakthrough version",
            '{"winner": "b", "rationale": "radically different approach", "reset": true}',
            "further improvement",
            '{"winner": "b", "rationale": "even better", "reset": false}',
        ]
        opt = self._make_optimizer(responses=responses)
        result = await opt.optimize("start", iterations=2)
        assert result == "further improvement"

    async def test_zero_iterations_returns_original(self):
        opt = self._make_optimizer()
        result = await opt.optimize("original", iterations=0)
        assert result == "original"

    async def test_multiple_iterations_accumulate_history(self):
        responses = [
            "v1",
            '{"winner": "a", "rationale": "original better", "reset": false}',
            "v2",
            '{"winner": "b", "rationale": "v2 is better", "reset": false}',
        ]
        opt = self._make_optimizer(responses=responses)
        result = await opt.optimize("original", iterations=2)
        assert result == "v2"

    async def test_compare_parses_json_in_code_block(self):
        json_str = '{"winner": "b", "rationale": "better structured", "reset": false}'
        llm = StubLLM(responses=[f"```json\n{json_str}\n```"])
        opt = FeedbackDescentOptimizer(llm=llm)
        result = opt._parse_comparison(
            f"```json\n{json_str}\n```", "a_text", "b_text",
        )
        assert result.winner == "b"
        assert result.rationale == "better structured"

    async def test_parse_comparison_handles_invalid_json(self):
        llm = StubLLM()
        opt = FeedbackDescentOptimizer(llm=llm)
        result = opt._parse_comparison("garbage", "current", "proposal")
        assert result.winner == "a"
        assert "parse error" in result.rationale

    async def test_default_max_iterations(self):
        opt = FeedbackDescentOptimizer(llm=StubLLM())
        assert opt.max_iterations == 10
