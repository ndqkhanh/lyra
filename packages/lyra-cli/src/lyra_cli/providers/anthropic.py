"""Lyra-side Anthropic provider with token-usage capture.

The upstream :class:`harness_core.models.AnthropicLLM` is a thin
wrapper around the ``anthropic`` SDK that targets the agent loop and
deliberately stays minimal — it has no concept of session billing
because the harness layer it lives in doesn't bill turns. The
Lyra REPL *does* bill, and treats every provider's ``last_usage``
dict as the ground truth for cost calculation
(:func:`lyra_cli.interactive.session._bill_turn`).

Subclassing here, rather than mutating ``harness_core``, has three
practical benefits:

1. We don't push session-mode concerns into a package shared with
   other harness consumers.
2. Tests can target the Lyra subclass without dragging in the SDK.
3. Adding fresh capture points (cache-read tokens, server-tool tokens
   when Anthropic ships them) only touches this file.

The class is a *strict* superset of the upstream behaviour: every
existing call path keeps working, the only change is a populated
``last_usage`` dict on the instance after each ``generate``.
"""
from __future__ import annotations

from typing import Any, Optional

from harness_core.messages import Message
from harness_core.models import AnthropicLLM as _UpstreamAnthropicLLM


class LyraAnthropicLLM(_UpstreamAnthropicLLM):
    """Anthropic adapter that records ``usage`` on every turn.

    Implementation: rather than re-implement the upstream request
    shape (system-prompt routing, tool-call translation, multi-block
    content) and risk drifting if the upstream evolves, we install a
    one-call spy on :attr:`self._client.messages.create` that captures
    the response object as it flies past. The upstream
    :meth:`generate` runs unchanged and returns its parsed
    :class:`Message`; we lift ``response.usage`` afterwards.

    The spy is restored in a ``finally`` so an exception inside the
    SDK can't leave a wrapper installed across calls. ``last_usage``
    is reset to ``{}`` at the start of every turn so a partial /
    failed call cannot leak old numbers into the next turn's billing.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize Anthropic provider with optional custom base_url.

        Args:
            model: Model name (defaults to HARNESS_LLM_MODEL or claude-3-5-sonnet-latest)
            api_key: API key (defaults to ANTHROPIC_API_KEY env var)
            base_url: Custom base URL (defaults to ANTHROPIC_BASE_URL env var)
        """
        super().__init__(model=model, api_key=api_key, base_url=base_url)
        self.last_usage: dict[str, int] = {}
        self.provider_name = "anthropic"

    def generate(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        # Reset before every turn so a failed call can't leak numbers
        # from the prior turn into the cost meter.
        self.last_usage = {}

        # Spy on ``client.messages.create`` so we can keep the raw
        # response after the parent has parsed it. We patch on the
        # *instance attribute* of ``self._client.messages`` (not the
        # class) so other consumers of the same SDK installation
        # remain unaffected — important when several providers share
        # one ``anthropic.Anthropic`` instance via a process-wide
        # cache.
        messages_obj = self._client.messages
        real_create = messages_obj.create
        captured: dict[str, Any] = {}

        def _capturing_create(**kwargs: Any) -> Any:
            resp = real_create(**kwargs)
            captured["resp"] = resp
            return resp

        try:
            messages_obj.create = _capturing_create  # type: ignore[assignment]
            reply = super().generate(
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        finally:
            # Always restore — exception or not.
            messages_obj.create = real_create  # type: ignore[assignment]

        self._record_usage(captured.get("resp"))
        return reply

    def _record_usage(self, resp: Any) -> None:
        """Lift the SDK's ``response.usage`` onto :attr:`last_usage`.

        The Anthropic SDK exposes ``resp.usage`` as a small dataclass
        with ``input_tokens`` and ``output_tokens`` (and ``cache_*``
        fields on prompt-caching responses). We surface only the two
        primary fields plus a synthesised ``total_tokens`` so the
        cost calculator sees the same dict shape every other provider
        emits.

        Best-effort: if the SDK ever omits ``usage`` (e.g. on a tool-
        only response under prompt caching), we leave ``last_usage``
        empty rather than guess; under-billing one turn is preferable
        to fabricating a number.
        """
        if resp is None:
            return
        usage = getattr(resp, "usage", None)
        if usage is None:
            return
        try:
            prompt = int(getattr(usage, "input_tokens", 0) or 0)
            completion = int(getattr(usage, "output_tokens", 0) or 0)
        except (TypeError, ValueError):
            return
        total = prompt + completion
        if total <= 0:
            return
        self.last_usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }


__all__ = ["LyraAnthropicLLM"]
