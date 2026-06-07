"""
Chat streaming endpoint.

Accepts a message, routes it through the appropriate provider backend,
and streams the response as Server-Sent Events (SSE).
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from aiohttp import web

from lyra.routing.provider.adapters import (
    AnthropicAdapter,
    DeepSeekAdapter,
    GoogleAdapter,
    OpenAIAdapter,
)
from lyra.routing.provider.config import get_api_key
from lyra.routing.provider.types import (
    CompletionRequest,
    EffortLevel,
    Message,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------

_ADAPTER_MAP: dict[str, type[Any]] = {
    "anthropic": AnthropicAdapter,
    "deepseek": DeepSeekAdapter,
    "openai": OpenAIAdapter,
    "google": GoogleAdapter,
}

# Default model per provider when none is specified in the request.
_DEFAULT_MODEL: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "google": "gemini-2-5-flash",
}


def _get_available_providers() -> list[str]:
    """Return provider names whose API key is present in the environment."""
    available: list[str] = []
    for name in _ADAPTER_MAP:
        if get_api_key(name):
            available.append(name)
    return available


def _create_adapter(provider_name: str) -> Any:
    """Create a provider adapter instance by name.

    Args:
        provider_name: One of ``"anthropic"``, ``"deepseek"``, ``"openai"``,
            ``"google"``.

    Returns:
        An instance of the corresponding ``ProviderBackend`` subclass.

    Raises:
        ValueError: If the provider is unknown or has no API key configured.
    """
    cls = _ADAPTER_MAP.get(provider_name)
    if cls is None:
        raise ValueError(f"Unknown provider: {provider_name!r}")
    api_key = get_api_key(provider_name)
    if not api_key:
        raise ValueError(
            f"No API key configured for {provider_name!r}. "
            f"Set {provider_name.upper()}_API_KEY environment variable.",
        )
    return cls(api_key=api_key)


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


async def _send_sse(
    response: web.StreamResponse,
    data: dict[str, Any],
) -> None:
    """Write a single SSE event to the stream."""
    payload = f"data: {json.dumps(data)}\n\n"
    await response.write(payload.encode("utf-8"))


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------


async def stream_chat(request: web.Request) -> web.StreamResponse:
    """Handle a streaming chat request.

    Expects a JSON body with:
        - ``message`` (str, required): The user's message.
        - ``model`` (str, optional): Model override.
        - ``provider`` (str, optional): Provider override (defaults to first
          available).

    Returns an SSE stream where each event is a JSON object with:
        - ``content`` (str): The incremental text content.
        - ``done`` (bool): ``True`` on the final event.
        - ``usage`` (dict, final event only): Token usage breakdown.
    """
    body = await request.json()
    user_text = body.get("message", "") if isinstance(body, dict) else ""
    model_override = body.get("model") if isinstance(body, dict) else None
    provider_override = body.get("provider") if isinstance(body, dict) else None

    if not user_text:
        raise web.HTTPBadRequest(text='{"error": "message is required"}')

    # Determine which provider to use
    available = _get_available_providers()
    if not available:
        raise web.HTTPServiceUnavailable(
            text='{"error": "No providers configured. Set at least one API key."}',
        )

    provider_name = provider_override if provider_override in available else available[0]
    model = model_override or _DEFAULT_MODEL.get(provider_name, "claude-sonnet-4-6")

    # Create adapter and build request
    adapter = _create_adapter(provider_name)
    messages = (Message(role="user", content=user_text),)

    completion_request = CompletionRequest(
        messages=messages,
        model=model,
        max_tokens=8192,
        temperature=0.7,
        effort=EffortLevel.MEDIUM,
    )

    # Set up SSE response
    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    await response.prepare(request)

    input_tokens = 0
    output_tokens = 0
    full_content = ""

    try:
        async for chunk in adapter.complete_stream(completion_request):
            if chunk.content_delta:
                full_content += chunk.content_delta
                await _send_sse(
                    response,
                    {"content": chunk.content_delta, "done": False},
                )

            if chunk.finish_reason:
                # Estimate token counts on the final chunk
                input_tokens = max(1, len(user_text) // 4)
                output_tokens = max(1, len(full_content) // 4)

        if not full_content and not input_tokens:
            # No content was streamed — try a non-streaming completion
            # to salvage the response
            try:
                complete_resp = await adapter.complete(completion_request)
                full_content = complete_resp.content
                input_tokens = complete_resp.usage.input_tokens
                output_tokens = complete_resp.usage.output_tokens
                if full_content:
                    await _send_sse(
                        response,
                        {"content": full_content, "done": False},
                    )
            except Exception as exc:
                logger.error("fallback completion failed", error=str(exc))

        # Send final event with usage
        await _send_sse(
            response,
            {
                "content": "",
                "done": True,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
            },
        )
    except Exception as exc:
        logger.error("chat stream error", error=str(exc))
        await _send_sse(
            response,
            {"content": f"\n\n[Error: {exc}]", "done": True},
        )

    return response
