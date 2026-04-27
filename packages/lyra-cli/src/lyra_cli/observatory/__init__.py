"""Lyra Token Observatory (Phase M, v3.3).

Read-only consumers of the JSONL transcripts that
:class:`lyra_cli.interactive.session.InteractiveSession` writes under
``<repo>/.lyra/sessions/<id>/turns.jsonl``. See
``docs/superpowers/plans/2026-04-27-v3.3-phase-m-token-observatory.md``
for the design.
"""
from __future__ import annotations

__all__ = [
    "classifier",
    "pricing",
    "aggregator",
    "dashboard",
    "compare",
    "optimize",
    "yield_tracker",
]
