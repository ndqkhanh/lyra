"""Lyra core kernel.

Public surface:
    - TDD state machine (``tdd.state``)
    - LyraMode + resolve_lyra_decision (``permissions``)
    - Shipped hooks (``hooks``)
    - Native tools (``tools.builtin``)
    - HIR event emitter (``observability.hir``)

Re-exports harness_core primitives under ``lyra_core.core`` for ergonomic
imports downstream.
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
