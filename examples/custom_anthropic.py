"""Custom Anthropic provider with base_url override support.

This provider extends Lyra's AnthropicLLM to support custom endpoints
via ANTHROPIC_BASE_URL environment variable.

Usage:
    1. Save this file to ~/.lyra/custom_anthropic.py
    2. Add to ~/.lyra/settings.json:
       {
         "providers": {
           "custom-anthropic": "custom_anthropic:CustomAnthropicProvider"
         }
       }
    3. Set environment variables:
       export ANTHROPIC_AUTH_TOKEN="your-token"
       export ANTHROPIC_BASE_URL="https://claude.aishopacc.com"
    4. Use: lyra run --llm custom-anthropic
"""

from __future__ import annotations

import os
from typing import Any, Optional

from anthropic import Anthropic
from harness_core.messages import Message
from lyra_cli.providers.anthropic import LyraAnthropicLLM


class CustomAnthropicProvider(LyraAnthropicLLM):
    """Anthropic provider with custom base_url support.

    Supports environment variables:
    - ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY: API key
    - ANTHROPIC_BASE_URL: Custom endpoint (default: https://api.anthropic.com)
    - ANTHROPIC_MODEL: Model name (default: claude-opus-4.5)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize with custom base_url support.

        Args:
            model: Model name (overrides ANTHROPIC_MODEL)
            api_key: API key (overrides ANTHROPIC_AUTH_TOKEN/ANTHROPIC_API_KEY)
            base_url: Custom base URL (overrides ANTHROPIC_BASE_URL)
        """
        # Get API key from parameters or environment
        self._api_key = (
            api_key
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or os.environ.get("ANTHROPIC_API_KEY")
        )

        if not self._api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"
            )

        # Get base URL from parameters or environment
        self._base_url = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL")
            or "https://api.anthropic.com"
        )

        # Get model from parameters or environment
        self.model = (
            model
            or os.environ.get("ANTHROPIC_MODEL")
            or "claude-opus-4.5"
        )

        # Initialize Anthropic client with custom base_url
        # This overrides the parent's _client initialization
        self._client = Anthropic(
            api_key=self._api_key,
            base_url=self._base_url,
        )

        # Initialize usage tracking (from LyraAnthropicLLM)
        self.last_usage: dict[str, int] = {}
        self.provider_name = "custom-anthropic"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CustomAnthropicProvider("
            f"model={self.model!r}, "
            f"base_url={self._base_url!r})"
        )


# Alias for backward compatibility
CustomAnthropicLLM = CustomAnthropicProvider
