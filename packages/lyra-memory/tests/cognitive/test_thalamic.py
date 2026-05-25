"""Tests for ThalamicGateway."""

import pytest

from lyra_memory.cognitive.thalamic import ThalamicGateway, ThalamicGateResult


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
        return "{}"


def _pass_json(average: float = 0.7) -> str:
    return f"""{{
        "scores": {{
            "relevance": 0.8,
            "emotion": 0.6,
            "urgency": 0.5,
            "novelty": 0.7,
            "trust": 0.9,
            "goal_affinity": 0.7
        }},
        "pass_through": true,
        "reason": "average of {average} exceeds threshold"
    }}"""


def _fail_json() -> str:
    return """{
        "scores": {
            "relevance": 0.2,
            "emotion": 0.1,
            "urgency": 0.1,
            "novelty": 0.2,
            "trust": 0.3,
            "goal_affinity": 0.1
        },
        "pass_through": false,
        "reason": "low salience across channels"
    }"""


class TestThalamicGateResult:
    def test_default_values(self):
        r = ThalamicGateResult(passed=False, channel_scores={}, average_score=0.0)
        assert r.passed is False
        assert r.average_score == 0.0
        assert r.reason == ""

    def test_passed_result(self):
        r = ThalamicGateResult(
            passed=True,
            channel_scores={"relevance": 0.9},
            average_score=0.75,
            reason="high quality",
        )
        assert r.passed is True
        assert r.reason == "high quality"


class TestThalamicGateway:
    def _make_gateway(self, responses: list[str] | None = None) -> ThalamicGateway:
        llm = StubLLM(responses=responses or [_pass_json()])
        return ThalamicGateway(llm=llm)

    async def test_filter_returns_thalamic_gate_result(self):
        gw = self._make_gateway()
        result = await gw.filter("important memory content")
        assert isinstance(result, ThalamicGateResult)

    async def test_filter_passes_high_salience_memory(self):
        gw = self._make_gateway()
        result = await gw.filter("critical task update")
        assert result.passed is True

    async def test_filter_rejects_low_salience_memory(self):
        gw = self._make_gateway(responses=[_fail_json()])
        result = await gw.filter("boring log line")
        assert result.passed is False

    async def test_filter_scores_all_six_channels(self):
        gw = self._make_gateway()
        result = await gw.filter("content")
        for ch in ThalamicGateway.CHANNELS:
            assert ch in result.channel_scores

    async def test_filter_computes_average_score(self):
        gw = self._make_gateway()
        result = await gw.filter("content")
        scores = result.channel_scores
        expected_avg = sum(scores.values()) / 6
        assert result.average_score == pytest.approx(expected_avg, rel=1e-9)

    async def test_filter_includes_content_in_prompt(self):
        llm = StubLLM(responses=[_pass_json()])
        gw = ThalamicGateway(llm=llm)
        await gw.filter("deploy pipeline failed in production")
        assert any("deploy pipeline" in p for p in llm.prompts)

    async def test_filter_includes_context_in_prompt(self):
        llm = StubLLM(responses=[_pass_json()])
        gw = ThalamicGateway(llm=llm)
        ctx = {"goals": "deploy safely", "source": "ci/cd", "identity": "DevOps agent"}
        await gw.filter("content", context=ctx)
        combined = " ".join(llm.prompts)
        assert "deploy safely" in combined
        assert "ci/cd" in combined
        assert "DevOps agent" in combined

    async def test_filter_handles_parse_failure(self):
        llm = StubLLM(responses=["garbage response not json"])
        gw = ThalamicGateway(llm=llm)
        result = await gw.filter("content")
        assert result.passed is False
        assert result.average_score == 0.0
        assert "failed to parse" in result.reason

    async def test_filter_uses_pass_through_field_when_below_threshold(self):
        json_str = """{
            "scores": {"relevance": 0.3, "emotion": 0.3, "urgency": 0.3, "novelty": 0.3, "trust": 0.3, "goal_affinity": 0.3},
            "pass_through": true,
            "reason": "explicit pass"
        }"""
        gw = self._make_gateway(responses=[json_str])
        result = await gw.filter("content")
        assert result.passed is True

    async def test_batch_filter_returns_one_result_per_input(self):
        gw = self._make_gateway(responses=[_pass_json(), _fail_json(), _pass_json()])
        memories = [("m1", None), ("m2", None), ("m3", None)]
        results = await gw.batch_filter(memories)
        assert len(results) == 3
        assert results[0].passed is True
        assert results[1].passed is False
        assert results[2].passed is True

    async def test_batch_filter_empty_list(self):
        gw = self._make_gateway()
        results = await gw.batch_filter([])
        assert results == []

    async def test_custom_pass_threshold(self):
        llm = StubLLM(responses=[_fail_json()])
        gw = ThalamicGateway(llm=llm, pass_threshold=0.1)
        result = await gw.filter("content")
        assert result.passed is False

    async def test_channels_constant(self):
        assert len(ThalamicGateway.CHANNELS) == 6
        assert "relevance" in ThalamicGateway.CHANNELS
        assert "goal_affinity" in ThalamicGateway.CHANNELS

    async def test_json_in_code_block(self):
        json_content = '{"scores":{"relevance":0.8,"emotion":0.6,"urgency":0.5,"novelty":0.7,"trust":0.9,"goal_affinity":0.7},"pass_through":true,"reason":"ok"}'
        llm = StubLLM(responses=[f"```json\n{json_content}\n```"])
        gw = ThalamicGateway(llm=llm)
        result = await gw.filter("content")
        assert result.passed is True

    async def test_json_in_plain_code_block(self):
        json_content = '{"scores":{"relevance":0.8,"emotion":0.6,"urgency":0.5,"novelty":0.7,"trust":0.9,"goal_affinity":0.7},"pass_through":true,"reason":"ok"}'
        llm = StubLLM(responses=[f"```\n{json_content}\n```"])
        gw = ThalamicGateway(llm=llm)
        result = await gw.filter("content")
        assert result.passed is True
