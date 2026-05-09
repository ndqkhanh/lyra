"""Lightweight HIR pub/sub facade.

The richer ``lyra_core.observability.hir`` module owns the canonical
``HIREvent`` schema and the JSONL emitter that backs replayable
sessions. This package, by contrast, is the *fire-and-forget* path
used by callers that want to record an event without owning a
session writer — typically the LLM factory cascade and one-off CLI
helpers.

A tiny pub/sub layer with a swappable global ``emit`` lets tests
monkey-patch a single attribute (``lyra_core.hir.events.emit``) and
production code register zero-or-more subscribers (the OTel exporter
shipped in v1.7.3 is one) without changing call sites.
"""
from __future__ import annotations

from . import events

__all__ = ["events"]
