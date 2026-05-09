"""Public dataclasses for :mod:`lyra_cli.client`.

These types are the contract embedded callers see. Keep them
JSON-serialisable (no live provider handles, no open files) so the
HTTP layer added in N.6 can pickle/marshal a :class:`ChatRequest`
straight to the wire without an adapter step.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ChatRequest:
    """A single chat turn the caller wants Lyra to handle.

    Mirrors the on-disk turn schema (``turns.jsonl``) closely so
    saving and replaying a request is a no-op. The only thing the
    client adds at persist time is the assistant reply.

    Attributes:
        prompt: The user message to send. Required.
        model: Model alias or canonical slug (e.g. ``opus``,
            ``claude-sonnet-4.5``). ``None`` falls back to the
            provider cascade in :func:`lyra_cli.llm_factory.build_llm`.
        session_id: Stable identifier of an existing session under
            ``<repo>/.lyra/sessions``. ``None`` creates a fresh
            session lazily on the first turn.
        system_prompt: Optional system message prepended to the
            conversation. ``None`` means *use whatever the provider
            defaults to*.
        metadata: Free-form caller metadata persisted alongside the
            user turn (e.g. ``{"trace_id": "abc"}``). Never sent to
            the provider — it's just a sidecar for downstream
            tooling.
    """

    prompt: str
    model: str | None = None
    session_id: str | None = None
    system_prompt: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatResponse:
    """The result of a completed chat turn.

    ``error`` is set (and ``text`` is empty) when the provider raised
    — callers who want exceptions can check ``error`` and re-raise.
    The fail-soft default keeps embedded scripts from blowing up
    on a transient API hiccup.

    Attributes:
        text: Assistant reply, possibly the empty string on error.
        session_id: The session id the turn was persisted under;
            stable across calls so a follow-up turn can pin it.
        model: The slug actually used (post-alias resolution).
        usage: Provider-reported usage block when available, else
            ``None``. Keys vary by provider — don't depend on a
            fixed schema here.
        error: ``None`` on success, otherwise a short human-readable
            diagnostic the caller can show the user / log.
    """

    text: str
    session_id: str
    model: str
    usage: Mapping[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class StreamEvent:
    """One event emitted by :meth:`LyraClient.stream`.

    Stream consumers iterate ``StreamEvent`` objects until the
    iterator ends — either with a ``"complete"`` event (success)
    or an ``"error"`` event (failure). ``"delta"`` events carry
    incremental text payloads. For non-streaming providers the
    iterator emits one ``delta`` followed by one ``complete`` so
    the call shape is identical regardless of backend.

    Attributes:
        kind: One of ``"delta"``, ``"complete"``, ``"error"``.
        payload: For ``delta`` and ``complete``, the (cumulative)
            text content. For ``error``, the diagnostic string.
    """

    kind: str
    payload: Any


__all__ = ["ChatRequest", "ChatResponse", "StreamEvent"]
