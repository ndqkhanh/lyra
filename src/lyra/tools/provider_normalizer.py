"""
Provider-normalized tool definitions — same logical tool, different providers.

Handles the translation between provider-specific tool formats
(Anthropic, OpenAI, DeepSeek) so that a single logical tool can be
registered once and called from any provider backend.

Classes
-------
ProviderType:
    Supported LLM provider types.
ToolFormat:
    The provider-specific format a tool definition is in.
ProviderToolDef:
    A tool definition in a specific provider format.
ToolFormatError:
    Raised when a tool cannot be converted to the requested format.
ProviderNormalizer:
    Normalize tools across Anthropic / OpenAI / DeepSeek formats.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"


class ToolFormat(str, Enum):
    """The provider-specific format a tool definition is in."""

    ANTHROPIC = "anthropic"  # {"name": ..., "description": ..., "input_schema": ...}
    OPENAI = "openai"  # {"type": "function", "function": {"name": ..., ...}}
    DEEPSEEK = "deepseek"  # Same structure as OpenAI
    LYRA = "lyra"  # Internal ToolDef format


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ToolFormatError(Exception):
    """Raised when a tool cannot be converted to the requested format."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderToolDef:
    """A tool definition in a specific provider format.

    Attributes
    ----------
    name:
        Tool name (canonical).
    description:
        Tool description.
    parameters:
        JSON Schema parameter definition.
    provider:
        The provider this tool definition targets.
    raw:
        The original provider-specific tool definition dict.
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    provider: ProviderType = ProviderType.ANTHROPIC
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ProviderNormalizer
# ---------------------------------------------------------------------------


class ProviderNormalizer:
    """Normalize tools across Anthropic / OpenAI / DeepSeek formats.

    Converts a canonical ``ProviderToolDef`` to any provider-specific
    format and back.  Detects the format of raw tool definitions and
    extracts a normalized representation.

    Usage::

        normalizer = ProviderNormalizer()

        # Detect provider from raw definition
        tool_def = normalizer.detect_and_normalize(raw_anthropic_tool)
        print(tool_def.provider, tool_def.name)

        # Convert to a different provider format
        openai_format = normalizer.to_provider(tool_def, ProviderType.OPENAI)
    """

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_format(self, raw: dict[str, Any]) -> ToolFormat:
        """Detect the provider format of a raw tool definition.

        Args:
            raw: The raw tool definition dict.

        Returns:
            The detected ``ToolFormat``.

        Raises:
            ToolFormatError: If the format cannot be determined.
        """
        # Anthropic: has "name", "input_schema" as top-level keys
        if "name" in raw and "input_schema" in raw:
            return ToolFormat.ANTHROPIC

        # OpenAI / DeepSeek: {"type": "function", "function": {...}}
        if raw.get("type") == "function" and "function" in raw:
            return ToolFormat.OPENAI

        # Lyra internal format: has "name", "description", "parameters"
        if "name" in raw and "parameters" in raw and "provider" not in raw:
            # If it also has "handler" it's a full Lyra ToolDef
            if "handler" in raw:
                return ToolFormat.LYRA
            return ToolFormat.LYRA

        raise ToolFormatError(
            f"Cannot detect tool format: unknown structure with keys {list(raw.keys())}"
        )

    def detect_and_normalize(self, raw: dict[str, Any]) -> ProviderToolDef:
        """Detect format and return a normalized ``ProviderToolDef``.

        Args:
            raw: Raw tool definition from any provider.

        Returns:
            A normalized ``ProviderToolDef``.

        Raises:
            ToolFormatError: If the format is unknown or parsing fails.
        """
        fmt = self.detect_format(raw)

        if fmt == ToolFormat.ANTHROPIC:
            return ProviderToolDef(
                name=raw["name"],
                description=raw.get("description", ""),
                parameters=raw.get("input_schema", {}),
                provider=ProviderType.ANTHROPIC,
                raw=raw,
            )

        if fmt == ToolFormat.OPENAI:
            func = raw["function"]
            return ProviderToolDef(
                name=func.get("name", ""),
                description=func.get("description", ""),
                parameters=func.get("parameters", {}),
                provider=ProviderType.OPENAI,
                raw=raw,
            )

        if fmt == ToolFormat.LYRA:
            params = raw.get("parameters", {})
            if isinstance(params, dict) and "properties" not in params:
                params = {"type": "object", "properties": params}
            return ProviderToolDef(
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                parameters=params,
                provider=ProviderType.ANTHROPIC,  # canonical format
                raw=raw,
            )

        raise ToolFormatError(f"Cannot normalize tool of format {fmt.value}")

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_provider(
        self,
        tool: ProviderToolDef,
        target: ProviderType,
    ) -> dict[str, Any]:
        """Convert a normalized tool to a target provider format.

        Args:
            tool: Normalized tool definition.
            target: Target provider format.

        Returns:
            Provider-specific tool definition dict.

        Raises:
            ToolFormatError: If conversion to the target format fails.
        """
        if tool.provider == target:
            return tool.raw

        if target == ProviderType.ANTHROPIC:
            return self._to_anthropic(tool)
        if target == ProviderType.OPENAI:
            return self._to_openai(tool)
        if target == ProviderType.DEEPSEEK:
            return self._to_deepseek(tool)
        if target == ProviderType.GOOGLE:
            return self._to_google(tool)

        raise ToolFormatError(f"Unsupported target provider: {target.value}")

    def to_anthropic(self, tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to Anthropic format.

        Args:
            tool: Normalized tool definition.

        Returns:
            Anthropic-compatible tool dict.
        """
        return self._to_anthropic(tool)

    def to_openai(self, tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to OpenAI format.

        Args:
            tool: Normalized tool definition.

        Returns:
            OpenAI-compatible tool dict.
        """
        return self._to_openai(tool)

    def to_deepseek(self, tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to DeepSeek format (same structure as OpenAI).

        Args:
            tool: Normalized tool definition.

        Returns:
            DeepSeek-compatible tool dict.
        """
        return self._to_deepseek(tool)

    def to_google(self, tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to Google AI format.

        Args:
            tool: Normalized tool definition.

        Returns:
            Google AI-compatible tool dict.
        """
        return self._to_google(tool)

    def convert_batch(
        self,
        tools: list[ProviderToolDef],
        target: ProviderType,
    ) -> list[dict[str, Any]]:
        """Convert a batch of tools to a target provider format.

        Args:
            tools: List of normalized tool definitions.
            target: Target provider format.

        Returns:
            List of provider-specific tool dicts.
        """
        return [self.to_provider(t, target) for t in tools]

    def normalize_batch(
        self,
        raw_tools: list[dict[str, Any]],
    ) -> list[ProviderToolDef]:
        """Detect and normalize a batch of raw tool definitions.

        Args:
            raw_tools: List of raw tool definition dicts.

        Returns:
            List of normalized ``ProviderToolDef``.
        """
        return [self.detect_and_normalize(t) for t in raw_tools]

    # ------------------------------------------------------------------
    # Format converters
    # ------------------------------------------------------------------

    @staticmethod
    def _to_anthropic(tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to Anthropic ``{"name": ..., "input_schema": ...}``."""
        params = tool.parameters
        if isinstance(params, dict) and "type" not in params:
            params = {"type": "object", "properties": params}
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": params,
        }

    @staticmethod
    def _to_openai(tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to OpenAI ``{"type": "function", "function": ...}``."""
        params = tool.parameters
        if isinstance(params, dict) and "type" not in params:
            params = {"type": "object", "properties": params}
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": params,
                "strict": True,
            },
        }

    @staticmethod
    def _to_deepseek(tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to DeepSeek format (identical to OpenAI)."""
        return ProviderNormalizer._to_openai(tool)

    @staticmethod
    def _to_google(tool: ProviderToolDef) -> dict[str, Any]:
        """Convert to Google AI ``function_declarations`` format."""
        params = tool.parameters
        if isinstance(params, dict) and "type" not in params:
            params = {"type": "object", "properties": params}
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": params,
        }
