"""
Provider abstraction layer — unified interface for LLM API calls.

Exposes data types, the abstract ``ProviderBackend``, concrete adapters,
configuration, and the ``ModelRouter``.
"""

from lyra.routing.provider.base import ProviderBackend
from lyra.routing.provider.config import RouterConfig, get_api_key
from lyra.routing.provider.router import ModelRouter
from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    ModelInfo,
    RouteContext,
    RouteDecision,
    ToolCall,
    ToolDef,
    TokenUsage,
)

__all__ = [
    # Types
    "Capability",
    "CompletionChunk",
    "CompletionRequest",
    "CompletionResponse",
    "CostEstimate",
    "EffortLevel",
    "Message",
    "ModelInfo",
    "RouteContext",
    "RouteDecision",
    "ToolCall",
    "ToolDef",
    "TokenUsage",
    # Base
    "ProviderBackend",
    # Config
    "RouterConfig",
    "get_api_key",
    # Router
    "ModelRouter",
]
