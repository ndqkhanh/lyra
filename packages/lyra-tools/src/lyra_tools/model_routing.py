"""Model routing tools — intelligent model selection and routing.

Implements cost-aware, capability-aware model routing with fallback chains.
"""
from __future__ import annotations

from typing import Any


def route_model(
    task_type: str,
    *,
    complexity: str = "medium",
    budget: str = "balanced",
    required_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Route to the optimal model for a given task.

    Args:
        task_type: Type of task (code, analysis, research, chat, etc.).
        complexity: Task complexity: "low", "medium", "high" (default: "medium").
        budget: Budget preference: "minimal", "balanced", "premium" (default: "balanced").
        required_capabilities: Required model capabilities (vision, tools, etc.).

    Returns:
        Dict with recommended model and routing metadata.
    """
    valid_task_types = {
        "code", "analysis", "research", "chat", "review",
        "refactor", "debug", "test", "documentation",
    }

    if task_type not in valid_task_types:
        return {
            "error": f"invalid task_type: {task_type}",
            "valid_types": sorted(valid_task_types),
            "routed": False,
        }

    if complexity not in ("low", "medium", "high"):
        return {"error": f"invalid complexity: {complexity}", "routed": False}

    if budget not in ("minimal", "balanced", "premium"):
        return {"error": f"invalid budget: {budget}", "routed": False}

    # Provider-agnostic tier aliases — resolved per active provider at dispatch time
    model_map = {
        ("code", "low", "minimal"): "fast",        # → Haiku / GPT-4o-mini / DeepSeek Flash / Flash
        ("code", "medium", "balanced"): "standard", # → Sonnet / GPT-4o / DeepSeek Pro / Pro
        ("code", "high", "premium"): "deep",        # → Opus / o1 / DeepSeek Reasoner / Pro (thinking)
        ("analysis", "low", "minimal"): "fast",
        ("analysis", "medium", "balanced"): "standard",
        ("analysis", "high", "premium"): "deep",
    }

    key = (task_type, complexity, budget)
    model_tier = model_map.get(key, "standard")

    return {
        "model_tier": model_tier,
        "task_type": task_type,
        "complexity": complexity,
        "budget": budget,
        "required_capabilities": required_capabilities or [],
        "routed": True,
        "reasoning": f"Selected {model_tier} tier for {complexity} {task_type} with {budget} budget",
    }


def list_models(
    *,
    capability_filter: list[str] | None = None,
    include_deprecated: bool = False,
) -> dict[str, Any]:
    """List available models with capabilities.

    Args:
        capability_filter: Filter by required capabilities.
        include_deprecated: Include deprecated models (default: False).

    Returns:
        Dict with model catalog.
    """
    models = [
        # Anthropic
        {"id": "anthropic:claude-opus-4", "name": "Claude Opus 4", "tier": "deep",
         "capabilities": ["code", "vision", "tools", "extended_thinking"],
         "context_window": 200000, "cost_tier": "premium", "deprecated": False},
        {"id": "anthropic:claude-sonnet-4", "name": "Claude Sonnet 4", "tier": "standard",
         "capabilities": ["code", "vision", "tools", "extended_thinking"],
         "context_window": 200000, "cost_tier": "balanced", "deprecated": False},
        {"id": "anthropic:claude-haiku-4", "name": "Claude Haiku 4", "tier": "fast",
         "capabilities": ["code", "vision", "tools"],
         "context_window": 200000, "cost_tier": "minimal", "deprecated": False},
        # OpenAI
        {"id": "openai:gpt-4o", "name": "GPT-4o", "tier": "standard",
         "capabilities": ["code", "vision", "tools"],
         "context_window": 128000, "cost_tier": "balanced", "deprecated": False},
        {"id": "openai:gpt-4o-mini", "name": "GPT-4o Mini", "tier": "fast",
         "capabilities": ["code", "vision", "tools"],
         "context_window": 128000, "cost_tier": "minimal", "deprecated": False},
        # DeepSeek
        {"id": "deepseek:deepseek-chat", "name": "DeepSeek V4", "tier": "standard",
         "capabilities": ["code", "tools"],
         "context_window": 64000, "cost_tier": "balanced", "deprecated": False},
        {"id": "deepseek:deepseek-reasoner", "name": "DeepSeek Reasoner", "tier": "deep",
         "capabilities": ["code", "tools"],
         "context_window": 64000, "cost_tier": "premium", "deprecated": False},
        # Google
        {"id": "google:gemini-2.5-flash", "name": "Gemini Flash", "tier": "fast",
         "capabilities": ["code", "vision", "tools"],
         "context_window": 2000000, "cost_tier": "minimal", "deprecated": False},
        {"id": "google:gemini-2.5-pro", "name": "Gemini Pro", "tier": "deep",
         "capabilities": ["code", "vision", "tools", "extended_thinking"],
         "context_window": 2000000, "cost_tier": "premium", "deprecated": False},
    ]

    # Filter by capabilities
    if capability_filter:
        models = [
            m for m in models
            if all(cap in m["capabilities"] for cap in capability_filter)
        ]

    # Filter deprecated
    if not include_deprecated:
        models = [m for m in models if not m["deprecated"]]

    return {
        "models": models,
        "count": len(models),
        "capability_filter": capability_filter,
    }


def estimate_cost(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> dict[str, Any]:
    """Estimate cost for a model invocation.

    Args:
        model: Model ID.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        cache_read_tokens: Cached tokens read (default: 0).
        cache_write_tokens: Cached tokens written (default: 0).

    Returns:
        Dict with cost breakdown.
    """
    # Pricing per million tokens (as of 2026-05)
    pricing = {
        "claude-opus-4": {
            "input": 15.00,
            "output": 75.00,
            "cache_read": 1.50,
            "cache_write": 18.75,
        },
        "claude-sonnet-4": {
            "input": 3.00,
            "output": 15.00,
            "cache_read": 0.30,
            "cache_write": 3.75,
        },
        "claude-haiku-4": {
            "input": 0.80,
            "output": 4.00,
            "cache_read": 0.08,
            "cache_write": 1.00,
        },
    }

    if model not in pricing:
        return {"error": f"unknown model: {model}", "estimated": False}

    rates = pricing[model]

    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    cache_read_cost = (cache_read_tokens / 1_000_000) * rates["cache_read"]
    cache_write_cost = (cache_write_tokens / 1_000_000) * rates["cache_write"]

    total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "costs": {
            "input": round(input_cost, 6),
            "output": round(output_cost, 6),
            "cache_read": round(cache_read_cost, 6),
            "cache_write": round(cache_write_cost, 6),
            "total": round(total_cost, 6),
        },
        "currency": "USD",
        "estimated": True,
    }


__all__ = [
    "route_model",
    "list_models",
    "estimate_cost",
]
