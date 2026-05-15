"""Tests for ANTHROPIC_BASE_URL support."""

import os
from unittest.mock import MagicMock, patch

import pytest


def test_anthropic_base_url_from_env():
    """Test that ANTHROPIC_BASE_URL is read from environment."""
    with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://custom.example.com"}):
        with patch("anthropic.Anthropic") as mock_anthropic:
            from harness_core.models import AnthropicLLM

            llm = AnthropicLLM(api_key="test-key")

            # Verify Anthropic client was initialized with custom base_url
            mock_anthropic.assert_called_once()
            call_kwargs = mock_anthropic.call_args[1]
            assert call_kwargs.get("base_url") == "https://custom.example.com"


def test_anthropic_base_url_parameter():
    """Test that base_url parameter takes precedence over environment."""
    with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://env.example.com"}):
        with patch("anthropic.Anthropic") as mock_anthropic:
            from harness_core.models import AnthropicLLM

            llm = AnthropicLLM(
                api_key="test-key",
                base_url="https://param.example.com"
            )

            # Verify parameter takes precedence
            mock_anthropic.assert_called_once()
            call_kwargs = mock_anthropic.call_args[1]
            assert call_kwargs.get("base_url") == "https://param.example.com"


def test_anthropic_default_base_url():
    """Test that default base_url is not passed when using official API."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("anthropic.Anthropic") as mock_anthropic:
            from harness_core.models import AnthropicLLM

            llm = AnthropicLLM(api_key="test-key")

            # Verify default base_url is not passed (SDK uses its own default)
            mock_anthropic.assert_called_once()
            call_kwargs = mock_anthropic.call_args[1]
            assert "base_url" not in call_kwargs


def test_lyra_anthropic_base_url():
    """Test that LyraAnthropicLLM passes base_url to parent."""
    with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://lyra.example.com"}):
        with patch("anthropic.Anthropic") as mock_anthropic:
            from lyra_cli.providers.anthropic import LyraAnthropicLLM

            llm = LyraAnthropicLLM(api_key="test-key")

            # Verify base_url was passed through
            mock_anthropic.assert_called_once()
            call_kwargs = mock_anthropic.call_args[1]
            assert call_kwargs.get("base_url") == "https://lyra.example.com"
