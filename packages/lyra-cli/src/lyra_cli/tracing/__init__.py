"""Pluggable tracing callbacks for Lyra turns.

Phase N.2 introduces a *protocol* (:class:`TracingCallback`) that
observers implement, plus two soft-dependent concrete observers
(``LangSmithCallback`` and ``LangfuseCallback``) for the two
production tracing platforms most LLM apps standardise on.

Soft-dependent because Lyra ships in environments where neither
library is installed (sandbox, air-gapped lab, CI) — the
callbacks must degrade to no-ops rather than blow up the chat
loop. The :class:`TracingHub` aggregates registered callbacks and
catches per-callback exceptions so a flaky tracing backend can
never break a real turn.

Usage from :class:`lyra_cli.client.LyraClient`::

    from lyra_cli.tracing import LangSmithCallback, TracingHub

    hub = TracingHub()
    hub.add(LangSmithCallback(project="lyra-eval"))
    client = LyraClient(repo_root=repo, tracing=hub)

The hub is also reachable from the REPL via ``/trace on`` (Phase D),
so embedded and interactive sessions share the same observability
spine.
"""
from __future__ import annotations

from .base import TracingCallback, TracingHub, TurnTrace
from .langfuse_cb import LangfuseCallback
from .langsmith_cb import LangSmithCallback

__all__ = [
    "LangSmithCallback",
    "LangfuseCallback",
    "TracingCallback",
    "TracingHub",
    "TurnTrace",
]
