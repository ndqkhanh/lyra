"""Lightweight structured stores (TodoStore, …).

These are small, single-purpose stores that don't warrant a SQLite
schema migration. :class:`TodoStore` backs the ``TodoWrite`` tool with
atomic JSON persistence.
"""
from __future__ import annotations

from .todo_store import TodoStore

__all__ = ["TodoStore"]
