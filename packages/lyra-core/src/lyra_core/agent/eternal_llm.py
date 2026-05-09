"""L4.1 follow-through — journaled LLM proxy for mid-turn replay.

Pairs with :class:`lyra_core.agent.eternal_turn.JournaledTools` to give the
:class:`AgentLoop` deterministic mid-turn replay:

* ``JournaledLLM`` records each LLM call into the activity table keyed
  by ``(turn_id, llm_call_index)``. On replay (same turn_id), recorded
  results are returned without re-invoking the model.
* ``JournaledTools`` records each tool dispatch into the activity table
  keyed by ``(turn_id, tool_name, args_hash)``. On replay, tools opted
  in via ``__eternal_idempotent__ = True`` return recorded results.

The combination means the AgentLoop's *control flow* is deterministic on
replay — the same `messages` list reconstructs because each LLM call
returns the same result at the same position, and the same tool
dispatches happen at the same iterations. A turn killed after the 2nd
LLM call resumes from the 3rd LLM call without re-firing the prior two.

Why a counter, not content-hash
-------------------------------
Tools key on argument-hash because callers expect ``f(x=1)`` to memoize
across repeated invocations. LLMs key on a *position counter* because
the message list grows monotonically — its hash is unique per call
within a turn but identical positions across turns might collide if we
hashed content. Counter keying is unambiguous: 1st call, 2nd call, ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from harness_eternal.restate.journal import Journal


@dataclass
class JournaledLLM:
    """Proxy LLM with per-turn journaled call sequence.

    Attributes:
        inner: the underlying LLM (anything with ``.generate(messages=...,
            **kwargs)`` or callable ``(messages=..., **kwargs)``).
        journal: the Restate journal SQLite handle (sync API).
        turn_id: the Restate invocation_id for this turn — produced by
            :class:`EternalAgentLoop` and passed in.
        _counter: internal call counter, increments per ``generate``.

    The proxy intentionally does not hold the messages list — it relies on
    AgentLoop to call in deterministic order, which it does.
    """

    inner: Any
    journal: Journal
    turn_id: str
    _counter: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        # Resolve the call shape eagerly so we fail fast on construction
        # rather than partway through a turn.
        if not (
            hasattr(self.inner, "generate") or callable(self.inner)
        ):
            raise TypeError(
                "JournaledLLM.inner must expose .generate(...) or be callable"
            )

    def generate(self, *, messages: list[dict], **kwargs) -> Mapping[str, Any]:
        return self._call(messages=messages, **kwargs)

    def __call__(self, *, messages: list[dict], **kwargs) -> Mapping[str, Any]:
        return self._call(messages=messages, **kwargs)

    def _call(self, *, messages: list[dict], **kwargs) -> Mapping[str, Any]:
        self._counter += 1
        key = f"{self.turn_id}:llm:{self._counter}"

        recorded = self.journal.lookup_activity(key)
        if recorded is not None:
            return recorded

        # Resolve inner-call shape and invoke.
        call = getattr(self.inner, "generate", None) or self.inner
        result = call(messages=messages, **kwargs)
        if not isinstance(result, Mapping):
            raise TypeError(
                f"LLM returned {type(result).__name__}; expected Mapping"
            )
        # Activity table records JSON-friendly dicts. Coerce.
        result_dict = dict(result)
        self.journal.record_activity(idempotency_key=key, result=result_dict)
        return result_dict

    @property
    def call_count(self) -> int:
        return self._counter


__all__ = ["JournaledLLM"]
