"""
Global test fixtures and configuration for lyra-research tests.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone


@pytest.fixture
def tmp_research_dir(tmp_path):
    """Temporary directory for research outputs."""
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    (research_dir / "reports").mkdir()
    (research_dir / "corpus").mkdir()
    return research_dir


@pytest.fixture
def mock_deepseek_client():
    """Mock DeepSeek API client."""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = MagicMock(
        return_value={
            "id": "chatcmpl-deepseek-123",
            "model": "deepseek-v4-pro",
            "choices": [{
                "message": {"content": "Test response from DeepSeek"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
        }
    )
    return client


@pytest.fixture
def mock_research_sources():
    """Mock research sources for testing."""
    return [
        {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw: Autonomous Research System",
            "abstract": "We present AutoResearchClaw...",
            "url": "https://arxiv.org/abs/2605.20025",
            "source_type": "arxiv",
        },
        {
            "id": "github:org/multi-agent-framework",
            "title": "Multi-Agent Research Framework",
            "abstract": "Framework for building multi-agent systems...",
            "url": "https://github.com/org/multi-agent-framework",
            "source_type": "github",
        },
    ]


class MockCostTracker:
    """Mock cost tracking for testing."""

    def __init__(self):
        self.total_cost = 0.0
        self.requests = []
        self.total_requests = 0

    def track_request(self, model, input_tokens, output_tokens):
        """Track request cost."""
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        self.total_cost += cost
        self.total_requests += 1
        self.requests.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
        })
        return cost

    def calculate_cost(self, model, input_tokens, output_tokens):
        """Calculate cost without tracking."""
        return self._calculate_cost(model, input_tokens, output_tokens)

    def _calculate_cost(self, model, input_tokens, output_tokens):
        """Calculate cost based on model pricing."""
        pricing = {
            "deepseek-v4-pro": {"input": 0.50, "output": 2.00},
            "deepseek-v4-flash": {"input": 0.14, "output": 0.55},
            "deepseek-chat": {"input": 0.07, "output": 0.28},
            "claude-opus-4.7": {"input": 15.00, "output": 75.00},
        }
        if model not in pricing:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing[model]["input"]
        output_cost = (output_tokens / 1_000_000) * pricing[model]["output"]
        return input_cost + output_cost

    def is_budget_exceeded(self):
        """Check if budget exceeded."""
        return False

    def should_alert(self):
        """Check if should alert."""
        return False

    def get_cost_breakdown(self):
        """Get cost breakdown by model."""
        breakdown = {}
        for req in self.requests:
            model = req["model"]
            if model not in breakdown:
                breakdown[model] = {"requests": 0, "cost": 0.0}
            breakdown[model]["requests"] += 1
            breakdown[model]["cost"] += req["cost"]
        return breakdown


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker fixture."""
    return MockCostTracker()
