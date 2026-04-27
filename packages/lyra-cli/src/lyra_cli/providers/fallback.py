"""Fallback provider cascade.

Wrap a list of LLM providers and try them in order. On *transient*
errors (HTTP 5xx, 429, network timeouts) we advance to the next
provider; on *fatal* errors (auth, bad-request, missing config) we
re-raise immediately because retrying with a different provider
won't fix a missing API key or a malformed prompt.

Why a separate module instead of baking this into the factory:

* The factory's selection cascade picks ONE provider at startup. The
  fallback chain is a *runtime* cascade — we want to keep using the
  primary if it's healthy and only roll over on actual failures.
* Tests can construct chains from fake providers without booting the
  whole CLI configuration system.
* Future work (Phase D) will let plugins inject a fallback chain
  scoped to a particular agent or task.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

from harness_core.messages import Message
from harness_core.models import LLMProvider

from lyra_cli.providers.openai_compatible import (
    ProviderHTTPError,
    ProviderNotConfigured,
)


# 5xx + 429 are the canonical transient failures. We also retry on
# timeouts and connection errors, which the OpenAI-compat adapter
# wraps in ProviderHTTPError messages containing "unreachable" or
# "timed out".
_RETRYABLE_HTTP_PATTERN = re.compile(r"\bHTTP (5\d\d|429)\b")
_RETRYABLE_KEYWORDS = ("unreachable", "timed out", "timeout", "connection reset")


def classify_error(exc: BaseException) -> str:
    """Return ``"retryable"``, ``"fatal"``, or ``"unknown"``.

    The classifier is deliberately conservative: when in doubt, we
    treat the error as fatal so the user sees a real exception
    instead of silently advancing through every provider in the
    chain.
    """
    if isinstance(exc, ProviderNotConfigured):
        return "fatal"
    if isinstance(exc, ProviderHTTPError):
        msg = str(exc)
        if _RETRYABLE_HTTP_PATTERN.search(msg):
            return "retryable"
        if any(k in msg.lower() for k in _RETRYABLE_KEYWORDS):
            return "retryable"
        # 4xx that isn't 429 → fatal
        if re.search(r"\bHTTP 4\d\d\b", msg):
            return "fatal"
        return "fatal"  # unknown HTTP wrapper text → don't paper over
    return "unknown"


def is_retryable_error(exc: BaseException) -> bool:
    """Convenience wrapper around :func:`classify_error`."""
    return classify_error(exc) == "retryable"


@dataclass
class _ProviderError:
    provider_name: str
    exc: BaseException


class FallbackExhausted(RuntimeError):
    """Raised when every provider in the chain has been tried and failed."""

    def __init__(self, errors: List[_ProviderError]) -> None:
        self.errors = errors
        bullets = "\n".join(
            f"  - {e.provider_name}: {type(e.exc).__name__}: {e.exc}"
            for e in errors
        ) if errors else "  (chain was empty)"
        super().__init__(
            f"all {len(errors)} provider(s) failed:\n{bullets}"
        )


class FallbackChain(LLMProvider):
    """LLMProvider that delegates to the first healthy member of a chain."""

    def __init__(self, providers: Sequence[LLMProvider]) -> None:
        self._providers: List[LLMProvider] = list(providers)

    @staticmethod
    def _provider_label(p: LLMProvider) -> str:
        return getattr(p, "provider_name", None) or getattr(p, "name", None) \
            or type(p).__name__

    def generate(
        self,
        messages: List[Message],
        tools: Optional[List[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        errors: List[_ProviderError] = []
        for provider in self._providers:
            try:
                return provider.generate(
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except (ProviderHTTPError, ProviderNotConfigured) as exc:
                cls = classify_error(exc)
                if cls == "fatal":
                    raise
                errors.append(_ProviderError(self._provider_label(provider), exc))
                continue
            except Exception as exc:  # noqa: BLE001
                # Anything else (TypeError, network library quirks…) is
                # treated as fatal — we can't reason about it and the
                # user deserves a real traceback rather than silent
                # cascade.
                raise
        raise FallbackExhausted(errors)


__all__ = [
    "FallbackChain",
    "FallbackExhausted",
    "classify_error",
    "is_retryable_error",
]
