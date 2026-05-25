"""Tests for CostSensitiveRouter and QueryProfile."""

import pytest

from lyra_memory.routing.router import (
    CostSensitiveRouter,
    QueryProfile,
    RouteResult,
)
from lyra_memory.routing.store import MultiStoreRegistry


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
        return '{"match_difficulty": 0.5, "required_coverage": 0.5, "urgency": 0.5, "domain": "general"}'


class TestQueryProfile:
    def test_default_values(self):
        p = QueryProfile(query="test query")
        assert p.query == "test query"
        assert p.match_difficulty == 0.5
        assert p.required_coverage == 0.5
        assert p.urgency == 0.5
        assert p.domain == "general"

    def test_complexity_score(self):
        p = QueryProfile(
            query="hard query",
            match_difficulty=0.8,
            required_coverage=0.6,
            urgency=0.9,
        )
        expected = 0.4 * 0.8 + 0.3 * 0.6 + 0.3 * 0.9
        assert p.complexity_score == pytest.approx(expected)

    def test_custom_domain(self):
        p = QueryProfile(query="sre incident", domain="devops")
        assert p.domain == "devops"


class TestRouteResult:
    def test_default_values(self):
        r = RouteResult(
            query="q",
            selected_stores=["STM"],
            total_cost=200,
            expected_accuracy=0.9,
        )
        assert r.query == "q"
        assert r.selected_stores == ["STM"]
        assert r.total_cost == 200
        assert r.expected_accuracy == 0.9
        assert r.reason == ""


class TestCostSensitiveRouter:
    def _make_router(self, responses: list[str] | None = None) -> CostSensitiveRouter:
        reg = MultiStoreRegistry()
        llm = StubLLM(responses=responses)
        return CostSensitiveRouter(stores=reg, llm=llm)

    def _profile_json(self) -> str:
        return """{
            "match_difficulty": 0.3,
            "required_coverage": 0.4,
            "urgency": 0.2,
            "domain": "coding"
        }"""

    # ── route (async) ──

    async def test_route_returns_route_result(self):
        router = self._make_router(responses=[self._profile_json()])
        result = await router.route("how do I fix this bug")
        assert isinstance(result, RouteResult)
        assert len(result.selected_stores) > 0
        assert result.total_cost > 0

    async def test_route_respects_budget(self):
        router = self._make_router(responses=[self._profile_json()])
        result = await router.route("simple query", budget_tokens=200)
        assert result.total_cost <= 200

    async def test_route_selects_stm_for_tight_budget(self):
        router = self._make_router(responses=[self._profile_json()])
        result = await router.route("small query", budget_tokens=200)
        assert "STM" in result.selected_stores or "SUMMARY" in result.selected_stores

    async def test_route_includes_reason(self):
        router = self._make_router(responses=[self._profile_json()])
        result = await router.route("test query")
        assert len(result.reason) > 0

    # ── route_sync ──

    def test_route_sync_with_profile(self):
        router = self._make_router()
        profile = QueryProfile(query="simple", match_difficulty=0.2)
        result = router.route_sync("simple", profile, budget_tokens=300)
        assert isinstance(result, RouteResult)
        assert len(result.selected_stores) > 0

    def test_route_sync_respects_budget(self):
        router = self._make_router()
        profile = QueryProfile(query="simple")
        result = router.route_sync("simple", profile, budget_tokens=300)
        assert result.total_cost <= 300

    # ── utility computation ──

    def test_compute_utility_scores(self):
        router = self._make_router()
        reg = router.stores
        profile = QueryProfile(query="test", match_difficulty=0.5)

        stm_util = router._compute_utility(reg.stores["STM"], profile)
        epi_util = router._compute_utility(reg.stores["EPISODIC"], profile)
        assert stm_util > epi_util

    def test_estimate_accuracy_combines_stores(self):
        router = self._make_router()
        reg = router.stores
        profile = QueryProfile(query="test")
        acc = router._estimate_accuracy(["STM", "LTM"], profile, reg)
        assert 0.0 <= acc <= 1.0

    def test_estimate_accuracy_empty_stores(self):
        router = self._make_router()
        reg = router.stores
        profile = QueryProfile(query="test")
        acc = router._estimate_accuracy([], profile, reg)
        assert acc == 0.0

    # ── profile parsing ──

    def test_parse_profile_valid_json(self):
        router = self._make_router()
        json_str = '{"match_difficulty": 0.7, "required_coverage": 0.8, "urgency": 0.9, "domain": "math"}'
        profile = router._parse_profile(json_str, "math question")
        assert profile.match_difficulty == 0.7
        assert profile.required_coverage == 0.8
        assert profile.urgency == 0.9
        assert profile.domain == "math"

    def test_parse_profile_invalid_json(self):
        router = self._make_router()
        profile = router._parse_profile("not json", "test")
        assert profile.query == "test"
        assert profile.match_difficulty == 0.5

    async def test_route_stores_sorted_by_utility(self):
        router = self._make_router(responses=[self._profile_json()])
        result = await router.route("test", budget_tokens=3000)
        assert result.selected_stores[0] in ("STM", "SUMMARY")

    async def test_handle_invalid_llm_response(self):
        router = self._make_router(responses=["garbage"])
        result = await router.route("test query")
        assert isinstance(result, RouteResult)
        assert len(result.selected_stores) > 0
