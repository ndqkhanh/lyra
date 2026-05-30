"""
DeepSeek API integration wrapper classes.

Provides ModelRouter and CostTracker for DeepSeek model routing and cost tracking.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RoutingDecision:
    """Decision about which model to use."""

    selected_model: str
    cost_tier: str  # "low", "mid", "high"
    reasoning_depth: str  # "simple", "standard", "deep"
    estimated_cost: float
    fallback_models: List[str] = None

    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = []


class ModelRouter:
    """Routes tasks to appropriate DeepSeek models based on complexity."""

    # DeepSeek model pricing (per million tokens)
    PRICING = {
        "deepseek-chat": {"input": 0.14, "output": 0.28},
        "deepseek-v4-flash": {"input": 0.27, "output": 1.10},
        "deepseek-v4-pro": {"input": 0.50, "output": 2.00},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_cost_per_request: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
        timeout: int = 30,
        enable_fallback: bool = False,
    ):
        self.api_key = api_key
        self.max_cost_per_request = max_cost_per_request
        self.max_latency_ms = max_latency_ms
        self.timeout = timeout
        self.enable_fallback = enable_fallback

        if api_key and not self._validate_api_key(api_key):
            raise ValueError("Invalid API key")

    def _validate_api_key(self, key: str) -> bool:
        """Validate API key format."""
        return key and isinstance(key, str) and key.startswith("sk-")

    def _load_deepseek_key(self) -> Optional[str]:
        """Load DeepSeek API key from settings."""
        import os
        return os.environ.get("DEEPSEEK_API_KEY")

    def _get_deepseek_config(self) -> Dict[str, str]:
        """Get DeepSeek endpoint configuration."""
        return {
            "base_url": "https://api.deepseek.com",
            "api_version": "v1",
        }

    def route_task(
        self,
        task_description: str,
        provider: str = "deepseek",
    ) -> RoutingDecision:
        """Route task to appropriate model based on complexity."""
        # Simple heuristic: task length and keywords
        task_lower = task_description.lower()
        task_len = len(task_description)

        # Detect complexity
        complex_keywords = ["analyze", "complex", "synthesis", "comprehensive", "deep"]
        is_complex = any(kw in task_lower for kw in complex_keywords) or task_len > 200

        simple_keywords = ["what", "status", "list", "show"]
        is_simple = any(kw in task_lower for kw in simple_keywords) and task_len < 50

        # Route based on complexity
        if is_simple:
            model = "deepseek-chat"
            cost_tier = "low"
            reasoning_depth = "simple"
            estimated_tokens = 500
        elif is_complex:
            model = "deepseek-v4-pro"
            cost_tier = "high"
            reasoning_depth = "deep"
            estimated_tokens = 2000
        else:
            model = "deepseek-v4-flash"
            cost_tier = "mid"
            reasoning_depth = "standard"
            estimated_tokens = 1000

        # Apply cost constraint
        if self.max_cost_per_request:
            estimated_cost = self._estimate_cost(model, estimated_tokens)
            if estimated_cost > self.max_cost_per_request:
                # Downgrade to cheaper model
                model = "deepseek-chat"
                cost_tier = "low"
                estimated_tokens = 500

        # Apply latency constraint
        if self.max_latency_ms and self.max_latency_ms < 500:
            # Use faster model
            if model == "deepseek-v4-pro":
                model = "deepseek-v4-flash"
                cost_tier = "mid"

        estimated_cost = self._estimate_cost(model, estimated_tokens)

        return RoutingDecision(
            selected_model=model,
            cost_tier=cost_tier,
            reasoning_depth=reasoning_depth,
            estimated_cost=estimated_cost,
            fallback_models=self._get_fallback_models(model),
        )

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for a request."""
        pricing = self.PRICING.get(model, self.PRICING["deepseek-chat"])
        # Assume 70% input, 30% output
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        return (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]

    def _get_fallback_models(self, model: str) -> List[str]:
        """Get fallback models for a given model."""
        fallbacks = {
            "deepseek-v4-pro": ["deepseek-v4-flash", "deepseek-chat"],
            "deepseek-v4-flash": ["deepseek-chat"],
            "deepseek-chat": [],
        }
        return fallbacks.get(model, [])

    def execute_request(self, decision: RoutingDecision, query: str):
        """Execute request with selected model (mock implementation)."""
        # This would make actual API call in production
        return {"response": f"Mock response from {decision.selected_model}"}

    def execute_request_with_fallback(self, decision: RoutingDecision, query: str):
        """Execute request with fallback on error."""
        try:
            return self.execute_request(decision, query)
        except Exception:
            if decision.fallback_models:
                fallback_decision = RoutingDecision(
                    selected_model=decision.fallback_models[0],
                    cost_tier="low",
                    reasoning_depth="simple",
                    estimated_cost=0.01,
                )
                return self.execute_request(fallback_decision, query)
            raise


class CostTracker:
    """Track costs for DeepSeek API usage."""

    # DeepSeek model pricing (per million tokens)
    PRICING = ModelRouter.PRICING

    def __init__(
        self,
        budget_limit: Optional[float] = None,
        alert_threshold: float = 0.8,
    ):
        self.budget_limit = budget_limit
        self.alert_threshold = alert_threshold
        self.total_cost = 0.0
        self.total_requests = 0
        self.costs_by_model: Dict[str, Dict] = {}

    def track_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Track cost for a single request."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        self.total_cost += cost
        self.total_requests += 1

        # Track by model
        if model not in self.costs_by_model:
            self.costs_by_model[model] = {
                "requests": 0,
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            }

        self.costs_by_model[model]["requests"] += 1
        self.costs_by_model[model]["total_cost"] += cost
        self.costs_by_model[model]["input_tokens"] += input_tokens
        self.costs_by_model[model]["output_tokens"] += output_tokens

        return cost

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for given token counts."""
        pricing = self.PRICING.get(model, self.PRICING["deepseek-chat"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def is_budget_exceeded(self) -> bool:
        """Check if budget limit is exceeded."""
        if self.budget_limit is None:
            return False
        return self.total_cost > self.budget_limit

    def should_alert(self) -> bool:
        """Check if alert threshold is reached."""
        if self.budget_limit is None:
            return False
        return self.total_cost >= (self.budget_limit * self.alert_threshold)

    def get_cost_breakdown(self) -> Dict[str, Dict]:
        """Get cost breakdown by model."""
        return self.costs_by_model
