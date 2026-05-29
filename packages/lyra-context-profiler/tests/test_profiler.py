"""Tests for lyra_context_profiler.profiler module."""

import asyncio

import pytest
from lyra_context_profiler.profiler import (
    CompactionRecommendation,
    ContextAnalyzer,
    ContextDashboard,
    ContextElement,
    ContextElementType,
    ContextHealth,
    ContextProfile,
    ContextProfiler,
    InvalidContextElementError,
    ProfileAnalysisError,
    ProfileMatcher,
    TokenBudget,
)

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def profiler():
    return ContextProfiler(token_budget=10000, health_warning_pct=70, health_critical_pct=90)


@pytest.fixture
def sample_elements():
    return [
        ContextElement(
            id="code_1",
            content="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            element_type=ContextElementType.CODE,
            token_count=50,
        ),
        ContextElement(
            id="docs_1",
            content="This module implements mathematical utility functions for the Lyra AGI system.",
            element_type=ContextElementType.DOCUMENTATION,
            token_count=200,
        ),
        ContextElement(
            id="conv_1",
            content="User: Can you help with a bug? Assistant: Sure, what's the issue?",
            element_type=ContextElementType.CONVERSATION,
            token_count=30,
        ),
    ]


@pytest.fixture
async def populated_profiler(profiler, sample_elements):
    for el in sample_elements:
        await profiler.add_element(el)
    return profiler


# ── TokenBudget ─────────────────────────────────────────────────────────────────


class TestTokenBudget:
    def test_default_initialization(self):
        budget = TokenBudget(total_limit=1000)
        assert budget.total_limit == 1000
        assert budget.used == 0
        assert budget.remaining == 1000

    def test_utilization_pct(self):
        budget = TokenBudget(total_limit=1000, used=500)
        assert budget.utilization_pct == 50.0

    def test_zero_limit_utilization(self):
        budget = TokenBudget(total_limit=0)
        assert budget.utilization_pct == 0.0


# ── ContextElement ──────────────────────────────────────────────────────────────


class TestContextElement:
    def test_creation_defaults(self):
        el = ContextElement(id="test", content="hello world", element_type=ContextElementType.CODE, token_count=10)
        assert el.id == "test"
        assert el.token_count == 10
        assert el.importance_score == 0.0
        assert el.dependencies == []

    def test_hash_and_eq(self):
        a = ContextElement(id="a", content="x", element_type=ContextElementType.CODE, token_count=10)
        b = ContextElement(id="a", content="y", element_type=ContextElementType.DOCUMENTATION, token_count=20)
        c = ContextElement(id="c", content="z", element_type=ContextElementType.CODE, token_count=10)
        assert a == b  # Same ID
        assert a != c  # Different ID
        assert hash(a) == hash(b)


# ── ContextProfiler ─────────────────────────────────────────────────────────────


class TestContextProfiler:
    def test_add_element_increases_count(self, profiler, sample_elements):
        el = sample_elements[0]
        asyncio.run(profiler.add_element(el))
        assert profiler.element_count == 1

    def test_add_element_updates_budget(self, profiler, sample_elements):
        el = sample_elements[0]
        asyncio.run(profiler.add_element(el))
        assert profiler.budget.used > 0

    def test_add_empty_id_raises(self, profiler):
        el = ContextElement(id="", content="x", element_type=ContextElementType.CODE, token_count=10)
        with pytest.raises(InvalidContextElementError):
            asyncio.run(profiler.add_element(el))

    def test_add_empty_content_raises(self, profiler):
        el = ContextElement(id="x", content="", element_type=ContextElementType.CODE, token_count=10)
        with pytest.raises(InvalidContextElementError):
            asyncio.run(profiler.add_element(el))

    def test_remove_element(self, profiler, sample_elements):
        el = sample_elements[0]
        asyncio.run(profiler.add_element(el))
        removed = asyncio.run(profiler.remove_element(el.id))
        assert removed is not None
        assert profiler.element_count == 0

    def test_remove_nonexistent(self, profiler):
        removed = asyncio.run(profiler.remove_element("nonexistent"))
        assert removed is None

    def test_update_element(self, profiler, sample_elements):
        el = sample_elements[0]
        asyncio.run(profiler.add_element(el))
        updated = asyncio.run(profiler.update_element(el.id, token_count=100))
        assert updated.token_count == 100

    def test_update_nonexistent_raises(self, profiler):
        with pytest.raises(InvalidContextElementError):
            asyncio.run(profiler.update_element("nonexistent", token_count=100))

    def test_get_element(self, profiler, sample_elements):
        el = sample_elements[0]
        asyncio.run(profiler.add_element(el))
        retrieved = profiler.get_element(el.id)
        assert retrieved is not None
        assert retrieved.id == el.id

    def test_add_dependency(self, profiler, sample_elements):
        asyncio.run(profiler.add_element(sample_elements[0]))
        asyncio.run(profiler.add_element(sample_elements[1]))
        asyncio.run(profiler.add_dependency("code_1", "docs_1"))

    def test_add_dependency_nonexistent_raises(self, profiler, sample_elements):
        asyncio.run(profiler.add_element(sample_elements[0]))
        with pytest.raises(InvalidContextElementError):
            asyncio.run(profiler.add_dependency("code_1", "nonexistent"))

    def test_analyze_returns_dashboard(self, profiler, sample_elements):
        for el in sample_elements:
            asyncio.run(profiler.add_element(el))
        dashboard = asyncio.run(profiler.analyze())
        assert isinstance(dashboard, ContextDashboard)
        assert dashboard.total_tokens > 0
        assert dashboard.health in ContextHealth

    def test_analyze_empty_context(self, profiler):
        dashboard = asyncio.run(profiler.analyze())
        assert isinstance(dashboard, ContextDashboard)

    def test_last_dashboard_property(self, profiler, sample_elements):
        for el in sample_elements:
            asyncio.run(profiler.add_element(el))
        asyncio.run(profiler.analyze())
        assert profiler.last_dashboard is not None

    def test_optimize_at_high_utilization(self, sample_elements):
        # Create profiler with tiny budget to force high utilization
        profiler = ContextProfiler(token_budget=100, health_critical_pct=50)
        el = ContextElement(id="big", content="x" * 500, element_type=ContextElementType.CODE, token_count=90)
        asyncio.run(profiler.add_element(el))
        result = asyncio.run(profiler.optimize())
        assert isinstance(result, CompactionRecommendation)

    def test_error_count_increments(self, profiler):
        # Force an analysis error by removing internal state
        profiler._importance = None
        with pytest.raises(ProfileAnalysisError):
            asyncio.run(profiler.analyze())
        assert profiler.error_count == 1

    def test_element_count_property(self, profiler, sample_elements):
        for el in sample_elements:
            asyncio.run(profiler.add_element(el))
        assert profiler.element_count == len(sample_elements)


# ── ContextAnalyzer ─────────────────────────────────────────────────────────────


class TestContextAnalyzer:
    def test_analyze_snapshot_returns_dashboard(self, sample_elements):
        analyzer = ContextAnalyzer(model_context_limit=10000)
        dashboard = asyncio.run(analyzer.analyze_snapshot(sample_elements))
        assert isinstance(dashboard, ContextDashboard)

    def test_analyze_snapshot_with_high_utilization(self):
        analyzer = ContextAnalyzer(model_context_limit=100)
        els = [
            ContextElement(
                id="big", content="x" * 500,
                element_type=ContextElementType.CODE, token_count=95,
            )
        ]
        dashboard = asyncio.run(analyzer.analyze_snapshot(els))
        assert dashboard.health in (ContextHealth.CRITICAL, ContextHealth.EXCEEDED)


# ── ProfileMatcher ──────────────────────────────────────────────────────────────


class TestProfileMatcher:
    def test_register_and_match(self):
        matcher = ProfileMatcher()
        matcher.register_pattern("code", {"complexity": 0.5})
        profile = ContextProfile(
            task_type="code", complexity=0.6,
            tools_available=[], user_preferences={}, environment_tags=[],
        )
        result = matcher.match(profile)
        assert isinstance(result, str)

    def test_empty_patterns_returns_general(self):
        matcher = ProfileMatcher()
        profile = ContextProfile(
            task_type="unknown", complexity=0.0,
            tools_available=[], user_preferences={}, environment_tags=[],
        )
        result = matcher.match(profile)
        assert result == "general"

    def test_match_with_scores(self):
        matcher = ProfileMatcher()
        matcher.register_pattern("code", {"complexity": 0.5})
        matcher.register_pattern("debug", {"complexity": 0.7})
        profile = ContextProfile(
            task_type="code", complexity=0.55,
            tools_available=[], user_preferences={}, environment_tags=[],
        )
        results = matcher.match_with_scores(profile)
        assert len(results) == 2
        assert results[0][1] >= results[1][1]  # First has highest score

    def test_deregister_pattern(self):
        matcher = ProfileMatcher()
        matcher.register_pattern("code", {"complexity": 0.5})
        assert matcher.deregister_pattern("code") is True
        assert matcher.deregister_pattern("code") is False

    def test_register_empty_task_type_raises(self):
        matcher = ProfileMatcher()
        with pytest.raises(ValueError):
            matcher.register_pattern("", {"complexity": 0.5})

    def test_pattern_count_and_types(self):
        matcher = ProfileMatcher()
        matcher.register_pattern("code", {"complexity": 0.5})
        matcher.register_pattern("debug", {"complexity": 0.7})
        assert matcher.pattern_count == 2
        assert "code" in matcher.registered_types
        assert "debug" in matcher.registered_types


# ── ContextDashboard ────────────────────────────────────────────────────────────


class TestContextDashboard:
    def test_default_creation(self):
        dashboard = ContextDashboard(
            total_tokens=1000,
            budget_remaining=9000,
            utilization_pct=10.0,
            health=ContextHealth.HEALTHY,
            element_counts={},
            top_elements_by_importance=[],
            compression_ratio=1.0,
            estimated_freeable_tokens=0,
            recommendations=[],
        )
        assert dashboard.health == ContextHealth.HEALTHY
        assert dashboard.timestamp > 0
