"""
Provider Bridge — wires lyra-provider into the tools ecosystem.

This is the integration seam between the Tier 1 provider abstraction layer
and the Tier 4 tool surface. All tool implementations that need LLM access
should go through this bridge rather than calling providers directly.

Design rationale: The scout audit found that zero packages above lyra-provider
import from it. This bridge is the first integration point. Tools call
`get_provider_bridge()` to access the provider layer without direct coupling.
"""

from __future__ import annotations

from typing import Any


class ProviderBridge:
    """
    Bridge between the tools layer and the provider abstraction layer.

    Tools use this bridge to:
    - Get the current provider/model configuration
    - Make LLM calls through the provider abstraction
    - Check provider capabilities
    - Translate tool schemas to provider-specific formats
    """

    def __init__(self) -> None:
        self._provider_name: str = "anthropic"
        self._model: str = "claude-sonnet-4-20250514"

    def configure(self, provider: str, model: str) -> None:
        """Configure which provider and model to use."""
        self._provider_name = provider
        self._model = model

    @property
    def provider(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    def supports(self, feature: str) -> bool:
        """Check if the current provider supports a feature."""
        try:
            from lyra_provider import get_capability_matrix
            return get_capability_matrix().supports(self._provider_name, feature)
        except ImportError:
            return feature in {"tool_calling", "streaming"}

    def get_context_window(self) -> int:
        """Get the context window size for the current model."""
        try:
            from lyra_provider import get_capability_matrix
            return get_capability_matrix().get_context_window(self._provider_name)
        except ImportError:
            return 128_000

    def to_tool_schema(self, name: str, description: str, parameters: dict[str, Any]) -> Any:
        """Convert a tool definition to provider-specific format."""
        try:
            from lyra_provider.interface import ToolSchema
            return ToolSchema(name=name, description=description, parameters=parameters)
        except ImportError:
            return {"name": name, "description": description, "input_schema": parameters}


# Module-level singleton
_bridge: ProviderBridge | None = None


def get_provider_bridge() -> ProviderBridge:
    """Return the global provider bridge singleton."""
    global _bridge
    if _bridge is None:
        _bridge = ProviderBridge()
    return _bridge
