"""
Cost optimization for model selection.

Tracks pricing, estimates costs, and recommends models based on
budget constraints and quality requirements.
"""



class CostOptimizer:
    """Optimize model selection for cost efficiency."""

    def __init__(self):
        """Initialize cost optimizer with pricing data."""
        # Pricing per 1M tokens (USD)
        self.pricing: dict[str, dict[str, float]] = {
            "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
            "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
            "claude-opus-4-7": {"input": 15.0, "output": 75.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.5, "output": 10.0}
        }

        # Quality scores (0.0-1.0) based on benchmarks
        self.quality_scores: dict[str, float] = {
            "claude-haiku-4-5": 0.75,
            "claude-sonnet-4-6": 0.90,
            "claude-opus-4-7": 0.98,
            "gpt-4o-mini": 0.70,
            "gpt-4o": 0.88
        }

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost for model usage.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD

        Raises:
            ValueError: If model is not recognized
        """
        if model not in self.pricing:
            raise ValueError(f"Unknown model: {model}")

        pricing = self.pricing[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def recommend_model(
        self,
        role: str,
        budget: float,
        quality_requirement: float
    ) -> str:
        """
        Recommend model based on budget and quality needs.

        Args:
            role: The role performing the task
            budget: Maximum budget in USD
            quality_requirement: Minimum quality score (0.0-1.0)

        Returns:
            Recommended model identifier
        """
        # Filter models by quality requirement
        candidates = [
            model for model, quality in self.quality_scores.items()
            if quality >= quality_requirement
        ]

        if not candidates:
            # If no model meets quality requirement, return highest quality
            return max(self.quality_scores.items(), key=lambda x: x[1])[0]

        # Estimate cost for typical usage (10k input, 2k output tokens)
        costs = {
            model: self.estimate_cost(model, 10_000, 2_000)
            for model in candidates
        }

        # Filter by budget
        affordable = [
            model for model, cost in costs.items()
            if cost <= budget
        ]

        if not affordable:
            # Return cheapest candidate if none are affordable
            return min(costs.items(), key=lambda x: x[1])[0]

        # Return highest quality affordable model
        return max(
            affordable,
            key=lambda m: self.quality_scores[m]
        )

    def compare_costs(
        self,
        models: list[str],
        input_tokens: int,
        output_tokens: int
    ) -> dict[str, float]:
        """
        Compare costs across multiple models.

        Args:
            models: List of model identifiers
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Dictionary mapping model to estimated cost
        """
        return {
            model: self.estimate_cost(model, input_tokens, output_tokens)
            for model in models
            if model in self.pricing
        }

    def get_cost_per_quality(self, model: str) -> float:
        """
        Calculate cost-per-quality ratio for a model.

        Args:
            model: Model identifier

        Returns:
            Cost per quality point (lower is better)
        """
        if model not in self.pricing or model not in self.quality_scores:
            return float('inf')

        # Use typical usage for comparison
        cost = self.estimate_cost(model, 10_000, 2_000)
        quality = self.quality_scores[model]

        return cost / quality if quality > 0 else float('inf')
