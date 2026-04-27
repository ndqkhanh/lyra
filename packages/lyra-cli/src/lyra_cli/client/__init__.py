"""Embedded Python client for Lyra.

The :class:`LyraClient` is the in-process equivalent of the ``lyra chat``
CLI: a Python program imports it once and gets the same chat → assistant
pipeline (provider routing, session persistence under
``<repo>/.lyra/sessions``, skill discovery) without spawning a
subprocess. Phase N.1 ships the synchronous slice; N.6 layers an HTTP
``lyra serve`` and a streaming SSE wrapper on top of the same primitives.

Use :class:`LyraClient` from notebooks, evaluation scripts, or
agent harnesses that want to drive Lyra with the *Python* call shape
the rest of the ecosystem (LangChain, autogen, DeerFlow) already
expects, instead of shelling out per turn.
"""
from __future__ import annotations

from .client import LyraClient
from .types import ChatRequest, ChatResponse, StreamEvent

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "LyraClient",
    "StreamEvent",
]
