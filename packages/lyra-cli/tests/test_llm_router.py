"""Unit tests for provider-based model routing (v6.0.0).

Tests the new single-provider routing system that replaced the
cross-provider fallback chain.
"""

import pytest
from lyra_cli.llm_router import (
    PROVIDER_FAMILIES,
    ProviderModelFamily,
    detect_task_type,
    get_provider_default_model,
    get_provider_family,
    route_model_for_task,
)


class TestTaskDetection:
    """Test task type detection from prompts."""

    def test_detect_reasoning_task(self):
        assert detect_task_type("Explain quantum computing") == "reasoning"
        assert detect_task_type("Why does this happen?") == "reasoning"
        assert detect_task_type("Analyze the implications") == "reasoning"

    def test_detect_coding_task(self):
        assert detect_task_type("Write a function to parse JSON") == "coding"
        assert detect_task_type("Fix this bug") == "coding"
        assert detect_task_type("Implement user authentication") == "coding"

    def test_detect_quick_task(self):
        assert detect_task_type("What is Python?") == "quick"
        assert detect_task_type("List all files") == "quick"
        assert detect_task_type("Show me the status") == "quick"

    def test_detect_creative_task(self):
        assert detect_task_type("Write a blog post") == "creative"
        assert detect_task_type("Draft an email") == "creative"
        assert detect_task_type("Brainstorm ideas") == "creative"

    def test_detect_planning_task(self):
        assert detect_task_type("Design the system architecture") == "planning"
        assert detect_task_type("Plan the implementation") == "planning"
        assert detect_task_type("Organize the workflow") == "planning"

    def test_empty_prompt_defaults_to_coding(self):
        assert detect_task_type("") == "coding"
        assert detect_task_type("   ") == "coding"

    def test_ambiguous_prompt_defaults_to_coding(self):
        # No clear keywords → defaults to coding
        assert detect_task_type("Hello") == "coding"
        assert detect_task_type("Random text") == "coding"


class TestProviderFamilies:
    """Test provider model family definitions."""

    def test_all_providers_have_families(self):
        """Ensure all major providers are defined."""
        expected_providers = [
            "anthropic",
            "deepseek",
            "openai",
            "openai-reasoning",
            "gemini",
            "xai",
            "groq",
            "cerebras",
            "mistral",
            "qwen",
            "ollama",
        ]
        for provider in expected_providers:
            assert provider in PROVIDER_FAMILIES, f"Missing provider: {provider}"

    def test_anthropic_family(self):
        family = PROVIDER_FAMILIES["anthropic"]
        assert family.provider == "anthropic"
        assert family.reasoning == "claude-opus-4.7"
        assert family.coding == "claude-sonnet-4.6"
        assert family.quick == "claude-haiku-4.5"
        assert family.creative == "claude-opus-4.7"
        assert family.planning == "claude-opus-4.7"

    def test_deepseek_family(self):
        family = PROVIDER_FAMILIES["deepseek"]
        assert family.provider == "deepseek"
        assert family.reasoning == "deepseek-v4-pro"
        assert family.coding == "deepseek-v4-flash"
        assert family.quick == "deepseek-chat"

    def test_openai_family(self):
        family = PROVIDER_FAMILIES["openai"]
        assert family.provider == "openai"
        assert family.reasoning == "o3"
        assert family.coding == "gpt-4o"
        assert family.quick == "gpt-3.5-turbo"

    def test_all_families_have_required_fields(self):
        """Ensure every family has all 5 task types defined."""
        for provider, family in PROVIDER_FAMILIES.items():
            assert family.reasoning, f"{provider} missing reasoning model"
            assert family.coding, f"{provider} missing coding model"
            assert family.quick, f"{provider} missing quick model"
            assert family.creative, f"{provider} missing creative model"
            assert family.planning, f"{provider} missing planning model"


class TestModelRouting:
    """Test routing to models within provider families."""

    def test_route_anthropic_reasoning(self):
        model = route_model_for_task("Explain quantum computing", "anthropic")
        assert model == "claude-opus-4.7"

    def test_route_anthropic_coding(self):
        model = route_model_for_task("Write a function", "anthropic")
        assert model == "claude-sonnet-4.6"

    def test_route_anthropic_quick(self):
        model = route_model_for_task("What is Python?", "anthropic")
        assert model == "claude-haiku-4.5"

    def test_route_deepseek_reasoning(self):
        model = route_model_for_task("Analyze this code", "deepseek")
        assert model == "deepseek-v4-pro"

    def test_route_deepseek_coding(self):
        model = route_model_for_task("Fix this bug", "deepseek")
        assert model == "deepseek-v4-flash"

    def test_route_deepseek_quick(self):
        model = route_model_for_task("List files", "deepseek")
        assert model == "deepseek-chat"

    def test_route_unknown_provider_returns_none(self):
        model = route_model_for_task("Hello", "unknown-provider")
        assert model is None

    def test_route_empty_prompt_uses_coding_tier(self):
        # Empty prompt → coding task → sonnet for Anthropic
        model = route_model_for_task("", "anthropic")
        assert model == "claude-sonnet-4.6"


class TestProviderHelpers:
    """Test helper functions for provider families."""

    def test_get_provider_family(self):
        family = get_provider_family("anthropic")
        assert isinstance(family, ProviderModelFamily)
        assert family.provider == "anthropic"

    def test_get_provider_family_unknown(self):
        family = get_provider_family("unknown")
        assert family is None

    def test_get_provider_default_model(self):
        # Default is coding tier
        assert get_provider_default_model("anthropic") == "claude-sonnet-4.6"
        assert get_provider_default_model("deepseek") == "deepseek-v4-flash"
        assert get_provider_default_model("openai") == "gpt-4o"

    def test_get_provider_default_model_unknown(self):
        assert get_provider_default_model("unknown") is None


class TestCrossProviderIsolation:
    """Test that routing stays within a single provider."""

    def test_anthropic_never_routes_to_deepseek(self):
        """Ensure Anthropic tasks never return DeepSeek models."""
        prompts = [
            "Explain quantum computing",
            "Write a function",
            "What is Python?",
            "Draft an email",
            "Design the architecture",
        ]
        for prompt in prompts:
            model = route_model_for_task(prompt, "anthropic")
            assert model is not None
            assert "claude" in model
            assert "deepseek" not in model

    def test_deepseek_never_routes_to_anthropic(self):
        """Ensure DeepSeek tasks never return Anthropic models."""
        prompts = [
            "Explain quantum computing",
            "Write a function",
            "What is Python?",
            "Draft an email",
            "Design the architecture",
        ]
        for prompt in prompts:
            model = route_model_for_task(prompt, "deepseek")
            assert model is not None
            assert "deepseek" in model
            assert "claude" not in model

    def test_openai_never_routes_to_other_providers(self):
        """Ensure OpenAI tasks never return other provider models."""
        prompts = [
            "Explain quantum computing",
            "Write a function",
            "What is Python?",
        ]
        for prompt in prompts:
            model = route_model_for_task(prompt, "openai")
            assert model is not None
            assert model in ["o3", "gpt-4o", "gpt-3.5-turbo"]
            assert "claude" not in model
            assert "deepseek" not in model
            assert "gemini" not in model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
