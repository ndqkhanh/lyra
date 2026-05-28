"""Tests for model routing tools."""
from __future__ import annotations

import pytest

from lyra_tools.model_routing import estimate_cost, list_models, route_model


class TestRouteModel:
    def test_route_code_low_minimal(self):
        result = route_model(
            task_type="code",
            complexity="low",
            budget="minimal",
        )

        assert result["routed"] is True
        assert result["model"] == "claude-haiku-4"
        assert result["task_type"] == "code"
        assert result["complexity"] == "low"
        assert result["budget"] == "minimal"

    def test_route_code_high_premium(self):
        result = route_model(
            task_type="code",
            complexity="high",
            budget="premium",
        )

        assert result["routed"] is True
        assert result["model"] == "claude-opus-4"

    def test_route_analysis_medium_balanced(self):
        result = route_model(
            task_type="analysis",
            complexity="medium",
            budget="balanced",
        )

        assert result["routed"] is True
        assert result["model"] == "claude-sonnet-4"

    def test_route_with_capabilities(self):
        result = route_model(
            task_type="code",
            required_capabilities=["vision", "tools"],
        )

        assert result["routed"] is True
        assert result["required_capabilities"] == ["vision", "tools"]

    def test_route_invalid_task_type_errors(self):
        result = route_model(task_type="invalid")

        assert result["routed"] is False
        assert "error" in result
        assert "valid_types" in result

    def test_route_invalid_complexity_errors(self):
        result = route_model(task_type="code", complexity="invalid")

        assert result["routed"] is False
        assert "error" in result

    def test_route_invalid_budget_errors(self):
        result = route_model(task_type="code", budget="invalid")

        assert result["routed"] is False
        assert "error" in result


class TestListModels:
    def test_list_all_models(self):
        result = list_models()

        assert "models" in result
        assert "count" in result
        assert result["count"] > 0

        # Check model structure
        for model in result["models"]:
            assert "id" in model
            assert "name" in model
            assert "capabilities" in model
            assert "context_window" in model
            assert "cost_tier" in model
            assert "deprecated" in model

    def test_list_with_capability_filter(self):
        result = list_models(capability_filter=["vision", "tools"])

        assert "models" in result
        for model in result["models"]:
            assert "vision" in model["capabilities"]
            assert "tools" in model["capabilities"]

    def test_list_exclude_deprecated(self):
        result = list_models(include_deprecated=False)

        for model in result["models"]:
            assert model["deprecated"] is False

    def test_list_include_deprecated(self):
        result = list_models(include_deprecated=True)

        assert "models" in result


class TestEstimateCost:
    def test_estimate_opus_basic(self):
        result = estimate_cost(
            model="claude-opus-4",
            input_tokens=1000,
            output_tokens=500,
        )

        assert result["estimated"] is True
        assert result["model"] == "claude-opus-4"
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 500
        assert "costs" in result
        assert result["costs"]["total"] > 0
        assert result["currency"] == "USD"

    def test_estimate_sonnet_basic(self):
        result = estimate_cost(
            model="claude-sonnet-4",
            input_tokens=10000,
            output_tokens=2000,
        )

        assert result["estimated"] is True
        assert result["model"] == "claude-sonnet-4"
        assert result["costs"]["total"] > 0

    def test_estimate_haiku_basic(self):
        result = estimate_cost(
            model="claude-haiku-4",
            input_tokens=5000,
            output_tokens=1000,
        )

        assert result["estimated"] is True
        assert result["model"] == "claude-haiku-4"
        assert result["costs"]["total"] > 0

    def test_estimate_with_cache(self):
        result = estimate_cost(
            model="claude-sonnet-4",
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=5000,
            cache_write_tokens=1000,
        )

        assert result["estimated"] is True
        assert result["cache_read_tokens"] == 5000
        assert result["cache_write_tokens"] == 1000
        assert result["costs"]["cache_read"] > 0
        assert result["costs"]["cache_write"] > 0

    def test_estimate_cost_breakdown(self):
        result = estimate_cost(
            model="claude-opus-4",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )

        costs = result["costs"]
        assert costs["input"] == 15.0  # 1M tokens * $15/M
        assert costs["output"] == 37.5  # 500k tokens * $75/M
        assert costs["total"] == 52.5

    def test_estimate_unknown_model_errors(self):
        result = estimate_cost(
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )

        assert result["estimated"] is False
        assert "error" in result
