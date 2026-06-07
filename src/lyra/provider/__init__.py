"""
Lyra Provider Abstraction Layer — canonical interface across all AI providers.

Every provider (Anthropic, DeepSeek, OpenAI, Google, open-weights) is wrapped
behind a single :class:`AbstractProvider` protocol so the rest of Lyra (router,
skills, tools, memory, swarm) is written once and runs against any backend.

Key normalizations:
- **Message format**: Provider-specific message schemas → Lyra canonical format
- **Tool calling**: Provider-specific tool schemas → Lyra canonical tool interface
- **Streaming**: Provider-specific SSE/stream events → unified async iterator
- **Token accounting**: Provider-specific usage fields → unified usage model
- **Error handling**: Provider-specific error codes → Lyra error taxonomy

Usage::

    from lyra.provider import ProviderRegistry, get_provider

    provider = get_provider("anthropic", api_key="sk-...")
    response = await provider.chat(messages=[{"role": "user", "content": "Hello"}])
"""

from __future__ import annotations

from .capability import (
    CapabilityMatrix,
    ProviderCapability,
    ProviderCapability as ProviderCapabilityRecord,
    get_capability_matrix,
)
from .interface import (
    AbstractProvider,
    ChatRequest,
    ChatResponse,
    ErrorCode,
    LLMUsage,
    Message,
    MessageRole,
    ProviderConfig,
    ProviderError,
    StreamEvent,
    ToolCall,
    ToolResult,
    ToolSchema,
)

__all__ = [
    "AbstractProvider",
    "CapabilityMatrix",
    "ChatRequest",
    "ChatResponse",
    "ErrorCode",
    "LLMUsage",
    "Message",
    "MessageRole",
    "ProviderCapability",
    "ProviderCapabilityRecord",
    "ProviderConfig",
    "ProviderError",
    "StreamEvent",
    "ToolCall",
    "ToolResult",
    "ToolSchema",
    "get_capability_matrix",
]
