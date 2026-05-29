"""Tests for the policy_search module."""

from __future__ import annotations

import pytest
from lyra_policy_optimizer.exceptions import PolicySearchError
from lyra_policy_optimizer.policy_search import (
    PolicyCandidate,
    PolicySearch,
    SearchConfig,
    SearchResult,
)


class TestSearchConfig:
    """Test SearchConfig dataclass."""

    def test_default_config(self) -> None:
        """SearchConfig should have sensible defaults."""
        config = SearchConfig()
        assert config.search_algorithm == "bayesian"
        assert config.max_iterations == 100
        assert config.exploration_rate == 0.1
        assert config.convergence_threshold == 0.001

    def test_custom_config(self) -> None:
        """SearchConfig should accept custom values."""
        config = SearchConfig(
            search_algorithm="grid",
            max_iterations=50,
            exploration_rate=0.2,
            convergence_threshold=0.01,
        )
        assert config.search_algorithm == "grid"
        assert config.max_iterations == 50
        assert config.exploration_rate == 0.2
        assert config.convergence_threshold == 0.01


class TestPolicyCandidate:
    """Test PolicyCandidate dataclass."""

    def test_create_candidate(self) -> None:
        """PolicyCandidate should store parameters correctly."""
        params = (("learning_rate", 0.01), ("batch_size", 64.0))
        candidate = PolicyCandidate(
            candidate_id="test_1",
            parameters=params,
            score=0.85,
            uncertainty=0.1,
            iteration_found=5,
        )
        assert candidate.candidate_id == "test_1"
        assert candidate.parameters == params
        assert candidate.score == 0.85
        assert candidate.iteration_found == 5

    def test_candidate_immutability(self) -> None:
        """PolicyCandidate should be frozen."""
        params = (("lr", 0.01),)
        candidate = PolicyCandidate("test", params, 0.9, 0.05, 1)
        with pytest.raises(AttributeError):
            candidate.score = 0.5  # type: ignore[misc]


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_create_result(self) -> None:
        """SearchResult should store search output correctly."""
        params = (("lr", 0.01),)
        best = PolicyCandidate("best", params, 0.95, 0.02, 10)
        candidates = (
            PolicyCandidate("c1", params, 0.8, 0.1, 1),
            PolicyCandidate("c2", params, 0.85, 0.08, 5),
            best,
        )
        result = SearchResult(
            best_policy=best,
            candidates=candidates,
            iterations=10,
            converged=True,
            search_time_ms=123.45,
        )
        assert result.best_policy.candidate_id == "best"
        assert len(result.candidates) == 3
        assert result.iterations == 10
        assert result.converged is True
        assert result.search_time_ms == 123.45


class TestPolicySearch:
    """Test PolicySearch class."""

    @pytest.fixture
    def searcher(self) -> PolicySearch:
        return PolicySearch(seed=42)

    @pytest.mark.asyncio
    async def test_search_policy_basic(self, searcher: PolicySearch) -> None:
        """Basic policy search should return a valid result."""
        config = SearchConfig(max_iterations=10, exploration_rate=0.2)
        result = await searcher.search_policy(config, "test_objective")
        assert isinstance(result, SearchResult)
        assert len(result.candidates) > 0
        assert result.best_policy.score >= 0
        assert result.search_time_ms >= 0

    @pytest.mark.asyncio
    async def test_search_policy_convergence(self, searcher: PolicySearch) -> None:
        """Search with tight threshold should converge."""
        config = SearchConfig(
            max_iterations=100,
            convergence_threshold=0.5,
            exploration_rate=0.0,
        )
        result = await searcher.search_policy(config, "test")
        assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_search_policy_invalid_max_iterations(
        self, searcher: PolicySearch
    ) -> None:
        """Search should reject invalid max_iterations."""
        config = SearchConfig(max_iterations=0)
        with pytest.raises(PolicySearchError, match="max_iterations"):
            await searcher.search_policy(config, "test")

    @pytest.mark.asyncio
    async def test_search_policy_invalid_exploration_rate(
        self, searcher: PolicySearch
    ) -> None:
        """Search should reject invalid exploration_rate."""
        config = SearchConfig(exploration_rate=1.5)
        with pytest.raises(PolicySearchError, match="exploration_rate"):
            await searcher.search_policy(config, "test")

    @pytest.mark.asyncio
    async def test_search_policy_negative_exploration_rate(
        self, searcher: PolicySearch
    ) -> None:
        """Search should reject negative exploration_rate."""
        config = SearchConfig(exploration_rate=-0.1)
        with pytest.raises(PolicySearchError, match="exploration_rate"):
            await searcher.search_policy(config, "test")

    @pytest.mark.asyncio
    async def test_search_policy_negative_threshold(
        self, searcher: PolicySearch
    ) -> None:
        """Search should reject negative convergence_threshold."""
        config = SearchConfig(convergence_threshold=-0.01)
        with pytest.raises(PolicySearchError, match="convergence_threshold"):
            await searcher.search_policy(config, "test")

    @pytest.mark.asyncio
    async def test_refine_search(self, searcher: PolicySearch) -> None:
        """Refine search should add candidates."""
        config = SearchConfig(max_iterations=5)
        initial = await searcher.search_policy(config, "test")
        refined = await searcher.refine_search(initial, 3)
        assert len(refined.candidates) >= len(initial.candidates)
        assert isinstance(refined, SearchResult)

    @pytest.mark.asyncio
    async def test_refine_search_invalid_iterations(
        self, searcher: PolicySearch
    ) -> None:
        """Refine search should reject invalid iterations."""
        config = SearchConfig(max_iterations=3)
        result = await searcher.search_policy(config, "test")
        with pytest.raises(PolicySearchError, match="iterations"):
            await searcher.refine_search(result, 0)

    @pytest.mark.asyncio
    async def test_explore_parameter_space(
        self, searcher: PolicySearch
    ) -> None:
        """Explore parameter space should return candidates for each bound."""
        bounds = ((0.0, 1.0), (-5.0, 5.0))
        candidates = await searcher.explore_parameter_space(bounds)
        assert len(candidates) == len(bounds)
        assert all(isinstance(c, PolicyCandidate) for c in candidates)

    @pytest.mark.asyncio
    async def test_explore_parameter_space_empty(
        self, searcher: PolicySearch
    ) -> None:
        """Explore should reject empty bounds."""
        with pytest.raises(PolicySearchError, match="bounds"):
            await searcher.explore_parameter_space(())

    @pytest.mark.asyncio
    async def test_explore_parameter_space_invalid_bounds(
        self, searcher: PolicySearch
    ) -> None:
        """Explore should reject invalid bounds."""
        with pytest.raises(PolicySearchError, match="invalid bound"):
            await searcher.explore_parameter_space(((5.0, 1.0),))

    @pytest.mark.asyncio
    async def test_select_best(self, searcher: PolicySearch) -> None:
        """Select best should return top-k by score."""
        candidates = (
            PolicyCandidate("c1", (("p", 0.5),), 0.5, 0.1, 0),
            PolicyCandidate("c2", (("p", 0.5),), 0.9, 0.1, 0),
            PolicyCandidate("c3", (("p", 0.5),), 0.7, 0.1, 0),
        )
        selected = await searcher.select_best(candidates, top_k=2)
        assert len(selected) == 2
        assert selected[0].candidate_id == "c2"
        assert selected[1].candidate_id == "c3"

    @pytest.mark.asyncio
    async def test_select_best_empty(
        self, searcher: PolicySearch
    ) -> None:
        """Select best should reject empty candidates."""
        with pytest.raises(PolicySearchError, match="candidates"):
            await searcher.select_best(())

    @pytest.mark.asyncio
    async def test_select_best_invalid_top_k(
        self, searcher: PolicySearch
    ) -> None:
        """Select best should reject invalid top_k."""
        candidates = (PolicyCandidate("c1", (("p", 0.5),), 0.5, 0.1, 0),)
        with pytest.raises(PolicySearchError, match="top_k"):
            await searcher.select_best(candidates, top_k=0)

    @pytest.mark.asyncio
    async def test_select_best_fewer_than_top_k(
        self, searcher: PolicySearch
    ) -> None:
        """Select best should handle fewer candidates than top_k."""
        candidates = (PolicyCandidate("c1", (("p", 0.5),), 0.5, 0.1, 0),)
        selected = await searcher.select_best(candidates, top_k=10)
        assert len(selected) == 1

    @pytest.mark.asyncio
    async def test_exploration_objective(self, searcher: PolicySearch) -> None:
        """Search with exploration objective should include explore_bonus."""
        config = SearchConfig(max_iterations=5)
        result = await searcher.search_policy(config, "exploration")
        param_names = [p[0] for p in result.best_policy.parameters]
        assert "explore_bonus" in param_names

    def test_search_config_frozen(self) -> None:
        """SearchConfig should be frozen."""
        config = SearchConfig()
        with pytest.raises(AttributeError):
            config.max_iterations = 50  # type: ignore[misc]
