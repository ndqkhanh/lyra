"""Context-window preflight estimator.

**Status (v1.7.4):** library-only helper. The agent loop and provider
adapters do *not* yet call :func:`preflight` automatically — wiring it
into the execution path is tracked under Wave D
(``2026-04-24-full-parity-roadmap.md``). Today the function is
exported so plugins, evals, and pre-commit hooks can defensively
estimate request size, but a CLI invocation of ``lyra run`` still
relies on the provider to bounce oversized prompts. Until Wave D
ships, "preflight done" really means "preflight available".

Counts approximate input tokens *before* a chat completion is sent and
raises if the estimate plus the requested ``max_output`` would exceed
the target model's context window. Mirrors claw-code's preflight logic
so the caller never bills a request the provider will immediately
reject.

The estimator uses a deliberately-conservative ``len(text) / 4``
heuristic. Real tokenizers (tiktoken, sentencepiece) usually report a
*lower* token count than this estimate, which means we fail-closed:
we may occasionally refuse a call that would have squeaked through,
but we never silently issue a request that the API will reject for
being too large. Trade-off chosen because the cost of a refused
request (latency + per-token billing for the rejected prompt) is
strictly worse than the cost of suggesting a fresh ``/compact``.

Unknown models are intentionally passed through (``would_exceed=False``,
``context_window=None``) — the registry doesn't know every fine-tuned
or custom model and we'd rather defer to the provider's own error
handling than block a request we can't reason about.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional


CONTEXT_WINDOW: dict[str, int] = {
    "claude-opus-4.5": 200_000,
    "claude-sonnet-4.5": 200_000,
    "claude-haiku-4": 200_000,
    "gpt-5": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "o3": 200_000,
    "o3-mini": 200_000,
    "gemini-2.5-pro": 2_000_000,
    "gemini-2.5-flash": 1_000_000,
    "deepseek-chat": 128_000,
    "deepseek-reasoner": 128_000,
    "grok-4": 256_000,
    "grok-4-mini": 256_000,
    "kimi-k2.5": 128_000,
    "qwen-max": 128_000,
    "llama-3.3-70b-versatile": 128_000,
}


class ContextWindowExceeded(RuntimeError):
    """Raised when the estimated request would exceed the model window."""


@dataclass
class PreflightReport:
    model: str
    estimated_input_tokens: int
    max_output_tokens: int
    context_window: Optional[int]
    would_exceed: bool


def _estimate_text(text: str) -> int:
    """Return ``len(text) // 4`` (rounded up).

    The +3 / 4 floor matches the ``ceil(len/4)`` rule used by claw-code
    and tiktoken's "rough" mode. We avoid ``math.ceil`` to keep the
    function dependency-free and benchmark-fast.
    """
    return (len(text) + 3) // 4


def _estimate_content(content: Any) -> int:
    """Estimate tokens for a single message's *content* field.

    Supports the three shapes Lyra emits: plain ``str``, list of
    OpenAI-style content parts (dicts with ``type`` and either
    ``text`` or ``image_url``), or anything else (best-effort
    ``str(content)``).
    """
    if isinstance(content, str):
        return _estimate_text(content)
    if isinstance(content, list):
        total = 0
        for part in content:
            if isinstance(part, Mapping):
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    total += _estimate_text(part["text"])
                elif part.get("type") == "image_url":
                    # Image cost is roughly fixed (~85 tokens per image
                    # for OpenAI / Anthropic vision); we use 200 as a
                    # safe over-estimate so multi-image requests don't
                    # silently blow the budget.
                    total += 200
                else:
                    total += _estimate_text(str(part))
            else:
                total += _estimate_text(str(part))
        return total
    return _estimate_text(str(content))


def estimate_input_tokens(
    *,
    messages: Iterable[Mapping[str, Any]],
    system: str,
    tools: Iterable[Mapping[str, Any]],
) -> int:
    """Sum estimated tokens across messages, system prompt, and tools."""
    total = 0
    if system:
        total += _estimate_text(system)
    for msg in messages:
        if "content" in msg:
            total += _estimate_content(msg["content"])
        # role + name + role-overhead — small constant per message
        total += 4
    for tool in tools:
        total += _estimate_text(str(tool))
    return total


def preflight(
    *,
    model: str,
    messages: Iterable[Mapping[str, Any]],
    system: str = "",
    tools: Iterable[Mapping[str, Any]] = (),
    max_output: int = 0,
) -> PreflightReport:
    """Estimate input tokens and check against the model's window.

    Returns a :class:`PreflightReport` on success. Raises
    :class:`ContextWindowExceeded` when ``estimated_input + max_output
    > context_window`` for known models. Unknown models are passed
    through with ``would_exceed=False``.
    """
    msgs = list(messages)
    tls = list(tools)
    n_in = estimate_input_tokens(messages=msgs, system=system, tools=tls)
    cw = CONTEXT_WINDOW.get(model)
    if cw is None:
        return PreflightReport(
            model=model,
            estimated_input_tokens=n_in,
            max_output_tokens=max_output,
            context_window=None,
            would_exceed=False,
        )
    would_exceed = (n_in + max(0, max_output)) > cw
    if would_exceed:
        raise ContextWindowExceeded(
            f"context window exceeded for {model}: "
            f"~{n_in:,} input + {max_output:,} output > {cw:,} "
            "(run /compact or pick a larger-window model)"
        )
    return PreflightReport(
        model=model,
        estimated_input_tokens=n_in,
        max_output_tokens=max_output,
        context_window=cw,
        would_exceed=False,
    )


__all__ = [
    "CONTEXT_WINDOW",
    "ContextWindowExceeded",
    "PreflightReport",
    "estimate_input_tokens",
    "preflight",
]
