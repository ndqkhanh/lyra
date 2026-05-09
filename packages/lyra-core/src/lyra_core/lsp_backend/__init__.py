"""Concrete LSP backends (v1.7.3).

Two implementations of the :class:`lyra_core.tools.lsp.LSPBackend`
adapter surface:

- :class:`MockLSPBackend` — canned payloads for unit tests.
- :class:`MultilspyBackend` — real bridge to ``multilspy`` (optional
  dep, ``pip install lyra[lsp]``).

:class:`FeatureUnavailable` is the shared sentinel raised when an
optional backend is requested but its dependency isn't installed.
"""
from __future__ import annotations

from .errors import FeatureUnavailable
from .mock import MockLSPBackend
from .multilspy_backend import MultilspyBackend

__all__ = [
    "FeatureUnavailable",
    "MockLSPBackend",
    "MultilspyBackend",
]
