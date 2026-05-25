"""Tests for ValenceVector and ValenceEstimator."""

import pytest

from lyra_memory.cognitive.valence import ValenceEstimator, ValenceVector


class StubLLM:
    """Stub LLM that returns a fixed JSON response."""

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


class TestValenceVector:
    def test_default_values(self):
        v = ValenceVector()
        assert v.emotional_valence == 0.0
        assert v.associative_strength == 0.5
        assert v.contextual_richness == 0.5
        assert v.density == 0.5
        assert v.precision == 0.5

    def test_custom_values(self):
        v = ValenceVector(
            emotional_valence=0.8,
            associative_strength=0.9,
            contextual_richness=0.7,
            density=0.6,
            precision=0.85,
        )
        assert v.emotional_valence == 0.8
        assert v.associative_strength == 0.9
        assert v.precision == 0.85

    def test_emotional_valence_clamped_to_range(self):
        v = ValenceVector(emotional_valence=1.5)
        assert v.emotional_valence == 1.0

        v2 = ValenceVector(emotional_valence=-2.0)
        assert v2.emotional_valence == -1.0

    def test_positive_components_clamped_0_to_1(self):
        v = ValenceVector(associative_strength=1.5, precision=-0.5)
        assert v.associative_strength == 1.0
        assert v.precision == 0.0

    def test_salience_composite_score(self):
        v = ValenceVector(
            emotional_valence=0.5,
            associative_strength=0.8,
            contextual_richness=0.6,
            density=0.4,
            precision=0.9,
        )
        expected = (
            0.30 * 0.5
            + 0.20 * 0.8
            + 0.15 * 0.6
            + 0.15 * 0.4
            + 0.20 * 0.9
        )
        assert v.salience == pytest.approx(expected, rel=1e-9)

    def test_salience_uses_abs_emotional_valence(self):
        v_neg = ValenceVector(emotional_valence=-0.8)
        v_pos = ValenceVector(emotional_valence=0.8)
        assert v_neg.salience == pytest.approx(v_pos.salience, rel=1e-9)

    def test_is_significant_threshold(self):
        high = ValenceVector(
            emotional_valence=1.0,
            associative_strength=1.0,
            contextual_richness=1.0,
            density=1.0,
            precision=1.0,
        )
        assert high.is_significant is True

        low = ValenceVector(
            emotional_valence=0.1,
            associative_strength=0.2,
            contextual_richness=0.1,
            density=0.1,
            precision=0.1,
        )
        assert low.is_significant is False

    def test_frozen_dataclass(self):
        v = ValenceVector()
        with pytest.raises(Exception):
            v.emotional_valence = 0.5

    def test_to_dict(self):
        v = ValenceVector(emotional_valence=0.7, precision=0.9)
        d = v.to_dict()
        assert d["emotional_valence"] == 0.7
        assert d["precision"] == 0.9
        assert "salience" in d

    def test_equality(self):
        v1 = ValenceVector(emotional_valence=0.5)
        v2 = ValenceVector(emotional_valence=0.5)
        assert v1 == v2

    def test_different_values_not_equal(self):
        v1 = ValenceVector(emotional_valence=0.5)
        v2 = ValenceVector(emotional_valence=0.3)
        assert v1 != v2


class TestValenceEstimator:
    def _valid_json(self) -> str:
        return """{
            "emotional_valence": 0.7,
            "associative_strength": 0.8,
            "contextual_richness": 0.6,
            "density": 0.5,
            "precision": 0.9
        }"""

    async def test_estimate_returns_valence_vector(self):
        llm = StubLLM(responses=[self._valid_json()])
        estimator = ValenceEstimator(llm=llm)
        result = await estimator.estimate("some content")
        assert isinstance(result, ValenceVector)
        assert result.emotional_valence == 0.7
        assert result.associative_strength == 0.8
        assert result.contextual_richness == 0.6
        assert result.density == 0.5
        assert result.precision == 0.9

    async def test_estimate_includes_content_in_prompt(self):
        llm = StubLLM(responses=[self._valid_json()])
        estimator = ValenceEstimator(llm=llm)
        await estimator.estimate("important task result")
        assert any("important task result" in p for p in llm.prompts)

    async def test_estimate_passes_context(self):
        llm = StubLLM(responses=[self._valid_json()])
        estimator = ValenceEstimator(llm=llm)
        ctx = {"source": "user", "goals": "build agent"}
        await estimator.estimate("content", context=ctx)
        assert any("source" in p for p in llm.prompts)

    async def test_estimate_defaults_on_invalid_json(self):
        llm = StubLLM(responses=["not valid json at all"])
        estimator = ValenceEstimator(llm=llm)
        result = await estimator.estimate("content")
        assert result == ValenceVector()

    async def test_estimate_defaults_on_missing_fields(self):
        llm = StubLLM(responses=['{"emotional_valence": 0.5}'])
        estimator = ValenceEstimator(llm=llm)
        result = await estimator.estimate("content")
        assert result.emotional_valence == 0.5
        assert result.associative_strength == 0.5

    async def test_parse_valence_with_json_code_block(self):
        json_str = '{"emotional_valence": 0.4, "associative_strength": 0.6, "contextual_richness": 0.5, "density": 0.7, "precision": 0.8}'
        response = f"```json\n{json_str}\n```"
        result = ValenceEstimator._parse_valence(response)
        assert result.emotional_valence == 0.4
        assert result.precision == 0.8

    async def test_parse_valence_with_plain_code_block(self):
        json_str = '{"emotional_valence": 0.3, "associative_strength": 0.7, "contextual_richness": 0.4, "density": 0.6, "precision": 0.9}'
        response = f"```\n{json_str}\n```"
        result = ValenceEstimator._parse_valence(response)
        assert result.emotional_valence == 0.3
        assert result.precision == 0.9
