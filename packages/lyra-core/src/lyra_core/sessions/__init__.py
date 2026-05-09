"""SQLite-backed session persistence for lyra.

The store is the canonical home of every turn's transcript, backed by a
single ``.lyra/state.db`` SQLite file with an FTS5 virtual table
for fast recall. This mirrors NousResearch/hermes-agent's state layer
while remaining small enough to embed in-process.
"""

from .store import SessionStore

__all__ = ["SessionStore"]
