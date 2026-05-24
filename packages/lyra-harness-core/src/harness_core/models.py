"""LLM provider abstraction with MockLLM (always available) and AnthropicLLM (optional).

Selection: ``get_default_llm()`` returns AnthropicLLM when ANTHROPIC_API_KEY is set
and the ``anthropic`` package is importable; otherwise MockLLM with a no-op script.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from .messages import Message, StopReason, ToolCall


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        """Return one assistant Message (may contain tool_calls)."""
        raise NotImplementedError


class MockLLM(LLMProvider):
    """Deterministic mock provider driven by a scripted output list.

    Each element of ``scripted_outputs`` is either:
      - a string: emitted as assistant text, stop_reason=END_TURN
      - a dict {"text": "...", "tool_calls": [{"id": "...", "name": "...", "args": {...}}]}

    If the loop asks for more turns than outputs, MockLLM echoes a benign
    END_TURN "done" message so tests do not hang.
    """

    def __init__(self, scripted_outputs: Optional[Iterable[Any]] = None) -> None:
        self._script: list[Any] = list(scripted_outputs or [])
        self._idx = 0
        self.calls: list[list[Message]] = []

    def generate(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        self.calls.append(list(messages))
        if self._idx >= len(self._script):
            return Message.assistant(content="done", stop_reason=StopReason.END_TURN)

        out = self._script[self._idx]
        self._idx += 1

        if isinstance(out, str):
            return Message.assistant(content=out, stop_reason=StopReason.END_TURN)

        if isinstance(out, dict):
            text = out.get("text", "")
            raw_calls = out.get("tool_calls", [])
            tool_calls = [
                ToolCall(
                    id=c.get("id", f"call_{i}"),
                    name=c["name"],
                    args=c.get("args", {}),
                )
                for i, c in enumerate(raw_calls)
            ]
            stop_reason = (
                StopReason.TOOL_USE if tool_calls else StopReason.END_TURN
            )
            return Message.assistant(
                content=text,
                tool_calls=tool_calls,
                stop_reason=stop_reason,
            )

        raise TypeError(f"MockLLM script entry must be str or dict, got {type(out)}")


class AnthropicLLM(LLMProvider):  # pragma: no cover - requires external service
    """Thin adapter for the Anthropic Messages API.

    Requires the `anthropic` extra: `pip install -e 'harness_core[anthropic]'`.
    Activated automatically by ``get_default_llm()`` when ANTHROPIC_API_KEY is set.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install 'harness_core[anthropic]'"
            ) from e

        # Support custom base_url via parameter or environment variable
        # Priority: parameter > ANTHROPIC_BASE_URL > default
        effective_base_url = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL")
            or "https://api.anthropic.com"
        )

        # Initialize client with base_url support
        client_kwargs = {"api_key": api_key}
        if effective_base_url != "https://api.anthropic.com":
            client_kwargs["base_url"] = effective_base_url

        self._client = anthropic.Anthropic(**client_kwargs)
        self.model = model or os.environ.get(
            "HARNESS_LLM_MODEL", "claude-3-5-sonnet-latest"
        )

    def generate(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        system = ""
        user_turns: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                system = m.content
            elif m.role in ("user", "assistant", "tool"):
                user_turns.append(_msg_to_anthropic(m))

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_turns,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        resp = self._client.messages.create(**kwargs)
        return _anthropic_to_msg(resp)


def _msg_to_anthropic(m: Message) -> dict[str, Any]:  # pragma: no cover
    if m.role == "tool":
        content = [
            {
                "type": "tool_result",
                "tool_use_id": r.call_id,
                "content": r.content,
                "is_error": r.is_error,
            }
            for r in m.tool_results
        ]
        return {"role": "user", "content": content}
    parts: list[dict[str, Any]] = []
    if m.content:
        parts.append({"type": "text", "text": m.content})
    for c in m.tool_calls:
        parts.append(
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.args}
        )
    return {"role": m.role, "content": parts or m.content}


def _anthropic_to_msg(resp: Any) -> Message:  # pragma: no cover
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in getattr(resp, "content", []):
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
        elif getattr(block, "type", None) == "tool_use":
            tool_calls.append(
                ToolCall(id=block.id, name=block.name, args=dict(block.input or {}))
            )
    stop_raw = getattr(resp, "stop_reason", "end_turn")
    try:
        stop = StopReason(stop_raw)
    except ValueError:
        stop = StopReason.END_TURN
    return Message.assistant(
        content="\n".join(text_parts),
        tool_calls=tool_calls,
        stop_reason=stop,
    )


def get_default_llm() -> LLMProvider:
    """Return the appropriate LLM for the current environment.

    AnthropicLLM if ANTHROPIC_API_KEY is set and anthropic is installed,
    else MockLLM with an empty script (emits 'done' on every call).
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return MockLLM()
    try:
        return AnthropicLLM(api_key=key)
    except ImportError:
        return MockLLM()
