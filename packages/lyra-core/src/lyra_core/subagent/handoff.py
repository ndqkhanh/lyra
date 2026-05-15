"""Iterative-retrieval sub-agent handoff (Phase CE.2, P1-2).

The parent agent doesn't dump its 10k+ token context onto a spawned
sub-agent. Instead it gives a *seed* — task + acceptance test + a few
hints — capped at :data:`HANDOFF_SEED_CAP_BYTES`. When the sub-agent
needs more, it calls the ``RequestMoreContext`` tool, which delegates
to a parent-side :class:`ContextProvider` that proxies the parent's
L5 memory tools.

The handoff stays *pure* — it neither runs the sub-agent nor owns the
memory store; it is a contract between the two. The orchestrator
(``subagent.orchestrator``) is the natural integration site but the
contract is small enough that it stands alone for tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

HANDOFF_SEED_CAP_BYTES = 2048
RESPONSE_CHUNK_CAP_BYTES = 2048


class HandoffError(ValueError):
    pass


@dataclass(frozen=True)
class HandoffSeed:
    """The minimal context a sub-agent receives at spawn time."""

    task: str
    acceptance_test: str
    hints: tuple[str, ...] = ()
    cap_bytes: int = HANDOFF_SEED_CAP_BYTES

    def __post_init__(self) -> None:
        if not self.task or not self.task.strip():
            raise HandoffError("HandoffSeed.task must be non-empty")
        if not self.acceptance_test or not self.acceptance_test.strip():
            raise HandoffError("HandoffSeed.acceptance_test must be non-empty")
        if self.cap_bytes <= 0:
            raise HandoffError(
                f"cap_bytes must be > 0, got {self.cap_bytes}"
            )
        size = len(self.render().encode("utf-8"))
        if size > self.cap_bytes:
            raise HandoffError(
                f"HandoffSeed exceeds cap ({size} > {self.cap_bytes} bytes). "
                f"Trim hints or move detail behind RequestMoreContext."
            )

    def render(self) -> str:
        """Stable text rendering — what the sub-agent actually reads."""
        parts = [
            "# Task",
            self.task.strip(),
            "",
            "# Acceptance test",
            self.acceptance_test.strip(),
        ]
        if self.hints:
            parts += ["", "# Hints"]
            parts += [f"- {h.strip()}" for h in self.hints if h.strip()]
        return "\n".join(parts) + "\n"


@dataclass(frozen=True)
class ContextRequest:
    """A sub-agent's request for additional context."""

    query: str
    requested_by: str

    def __post_init__(self) -> None:
        if not self.query or not self.query.strip():
            raise HandoffError("ContextRequest.query must be non-empty")
        if not self.requested_by or not self.requested_by.strip():
            raise HandoffError("ContextRequest.requested_by must be non-empty")


@dataclass(frozen=True)
class ContextResponse:
    """The parent's reply to a :class:`ContextRequest`."""

    query: str
    chunks: tuple[str, ...] = ()
    truncated: bool = False
    cap_bytes: int = RESPONSE_CHUNK_CAP_BYTES

    def __post_init__(self) -> None:
        if self.cap_bytes <= 0:
            raise HandoffError(f"cap_bytes must be > 0, got {self.cap_bytes}")
        total = sum(len(c.encode("utf-8")) for c in self.chunks)
        if total > self.cap_bytes and not self.truncated:
            raise HandoffError(
                f"ContextResponse chunks total {total} bytes > cap "
                f"{self.cap_bytes}; flip truncated=True or shrink chunks."
            )


class ContextProvider(Protocol):
    """Parent-side adapter that knows how to satisfy a request.

    Typically backed by the parent's L5 memory tools (search, timeline,
    get) — see :mod:`lyra_core.memory.memory_tools` — but the protocol
    keeps the dependency at arms-length for testability.
    """

    def serve(self, request: ContextRequest) -> ContextResponse: ...


# ────────────────────────────────────────────────────────────────
# Handoff orchestration
# ────────────────────────────────────────────────────────────────


@dataclass
class SubagentHandoff:
    """One sub-agent's handoff lifecycle.

    Holds the seed, a provider that knows how to answer follow-up
    requests, and an audit log of every :class:`ContextRequest` made.
    The log is what lets a parent later inspect *whether* the
    sub-agent actually exercised the iterative-retrieval path or just
    ran off the seed alone.
    """

    seed: HandoffSeed
    provider: ContextProvider
    subagent_id: str
    requests: list[ContextRequest] = field(default_factory=list)

    def request_more(self, query: str) -> ContextResponse:
        """Issue a context request to the parent provider."""
        req = ContextRequest(query=query, requested_by=self.subagent_id)
        self.requests.append(req)
        return self.provider.serve(req)


def make_seed_from_parent(
    *,
    task: str,
    acceptance_test: str,
    parent_context: str,
    hints: tuple[str, ...] = (),
    cap_bytes: int = HANDOFF_SEED_CAP_BYTES,
) -> HandoffSeed:
    """Helper: build a capped seed from a possibly-huge parent context.

    ``parent_context`` is *not* embedded — that's exactly the
    anti-pattern this module exists to prevent. We accept it only so
    the helper can return diagnostics in the error path if the seed
    would already exceed the cap before any context is added.
    """
    del parent_context  # explicitly not embedded; documented arg
    seed = HandoffSeed(
        task=task,
        acceptance_test=acceptance_test,
        hints=hints,
        cap_bytes=cap_bytes,
    )
    return seed


# ────────────────────────────────────────────────────────────────
# RequestMoreContext tool — adapter for the sub-agent's tool registry
# ────────────────────────────────────────────────────────────────


REQUEST_MORE_CONTEXT_TOOL_NAME = "RequestMoreContext"
REQUEST_MORE_CONTEXT_TOOL_DESCRIPTION = (
    "Ask the parent agent for additional context. Pass a focused "
    "query string — the parent will search its memory and return up "
    "to ~2KB of relevant chunks. Use sparingly: the parent's "
    "context budget is shared."
)


def request_more_context_tool_handler(
    handoff: SubagentHandoff, *, query: str
) -> dict[str, object]:
    """Tool handler that surfaces the response as JSON-serialisable dict."""
    try:
        resp = handoff.request_more(query)
    except HandoffError as exc:
        return {"ok": False, "error": str(exc), "query": query}
    return {
        "ok": True,
        "query": resp.query,
        "chunks": list(resp.chunks),
        "truncated": resp.truncated,
    }


__all__ = [
    "ContextProvider",
    "ContextRequest",
    "ContextResponse",
    "HANDOFF_SEED_CAP_BYTES",
    "HandoffError",
    "HandoffSeed",
    "REQUEST_MORE_CONTEXT_TOOL_DESCRIPTION",
    "REQUEST_MORE_CONTEXT_TOOL_NAME",
    "RESPONSE_CHUNK_CAP_BYTES",
    "SubagentHandoff",
    "make_seed_from_parent",
    "request_more_context_tool_handler",
]
