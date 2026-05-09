"""L4.2 — automatic context compaction for the AgentLoop.

The :class:`AutoCompactingLLM` proxies the underlying LLM and, before each
call, estimates the message-token count. When the estimate exceeds
``compact_threshold_pct * model_window``, it invokes
:func:`compact_messages` (already in :mod:`lyra_core.context.compactor`)
to fold older turns into a summary in-place, then proceeds with the call.

If compaction fails or the post-compaction count is *still* over
``ralph_threshold_pct * model_window``, the proxy raises
:class:`ContextOverflow`. The caller (the EternalLoop wrapper or the
turn-runner) is expected to abandon the turn and re-enter with a fresh
context — the Ralph fallback (`docs/165-ralph-autonomous-loop.md`).

The proxy is *additive* — it does not change the LLM contract beyond
maybe-mutating the message list before each call. AgentLoop is unaware.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .compactor import CompactResult, compact_messages


def _tok_estimate(messages: list[dict]) -> int:
    """Cheap token estimator — char-count / 4. Same heuristic the
    Lyra compactor uses internally, kept consistent so the threshold
    comparison is apples-to-apples.
    """
    total_chars = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text", "")
                    if isinstance(text, str):
                        total_chars += len(text)
        # tool_calls / other fields contribute negligible tokens.
    return total_chars // 4


class ContextOverflow(RuntimeError):
    """Raised when context exceeds the Ralph fallback threshold even
    after compaction. Caller is expected to drop this turn and re-enter
    with a fresh context."""


@dataclass
class AutoCompactingLLM:
    """Proxies an LLM. Auto-compacts when message tokens exceed
    ``compact_threshold_pct * model_window`` before each call.

    Production wires this in by replacing ``AgentLoop.llm`` with this
    proxy. The proxy delegates everything to ``inner_llm`` and only
    interposes when the message list is about to overflow.

    Attributes:
        inner_llm: the underlying model handle.
        model_window: total tokens the model accepts.
        compact_threshold_pct: trigger compaction at or above this ratio.
        ralph_threshold_pct: if still over this ratio after compaction,
            raise :class:`ContextOverflow` so the caller can abandon the
            turn.
        compactor_llm: the LLM used to summarise. Defaults to
            ``inner_llm``; production may want a cheaper / faster model
            here so compaction does not cost as much as the turn itself.
        keep_last: messages to keep verbatim after compaction.
    """

    inner_llm: Any
    model_window: int = 200_000
    compact_threshold_pct: float = 0.60
    ralph_threshold_pct: float = 0.85
    compactor_llm: Any | None = None
    keep_last: int = 4
    _last_compact: CompactResult | None = field(default=None, init=False, repr=False)
    _compact_count: int = field(default=0, init=False)

    @property
    def compact_count(self) -> int:
        return self._compact_count

    # --- AgentLoop talks to the LLM through ``generate(messages=..., **kw)``
    #     or as a bare callable. Support both shapes.

    def generate(self, *, messages: list[dict], **kwargs):  # noqa: D401
        messages = self._maybe_compact(messages)
        return self.inner_llm.generate(messages=messages, **kwargs)

    def __call__(self, *, messages: list[dict], **kwargs):
        messages = self._maybe_compact(messages)
        return self.inner_llm(messages=messages, **kwargs)

    # --- compaction --------------------------------------------------

    def _maybe_compact(self, messages: list[dict]) -> list[dict]:
        tokens = _tok_estimate(messages)
        compact_threshold = int(self.compact_threshold_pct * self.model_window)
        ralph_threshold = int(self.ralph_threshold_pct * self.model_window)

        if tokens < compact_threshold:
            return messages

        compactor = self.compactor_llm or self.inner_llm
        try:
            result = compact_messages(
                messages, llm=compactor, keep_last=self.keep_last
            )
            self._last_compact = result
            self._compact_count += 1
            new_messages = (
                result.summarised_messages
                if result.dropped_count > 0
                else messages
            )
        except Exception:
            # Compaction itself failed — fall through to the ralph check.
            new_messages = messages

        new_tokens = _tok_estimate(new_messages)
        if new_tokens >= ralph_threshold:
            raise ContextOverflow(
                f"context still over {self.ralph_threshold_pct:.0%} of "
                f"window after compaction: {new_tokens} >= {ralph_threshold}"
                f" (was {tokens}); abandon turn and re-enter with fresh "
                "context (Ralph fallback)"
            )
        # Mutate the caller's list in-place so AgentLoop's bookkeeping
        # stays consistent across the call boundary.
        if new_messages is not messages:
            messages.clear()
            messages.extend(new_messages)
        return messages


__all__ = [
    "AutoCompactingLLM",
    "ContextOverflow",
]
