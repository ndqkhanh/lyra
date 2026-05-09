"""Wave-F Task 14 — KLong checkpoint & resume across model generations.

KLong = "long-horizon checkpoint". The idea: a session may run
for hours across multiple model generations (e.g. GPT-5 Monday,
GPT-6 Friday). We snapshot the session's serialisable state to
disk in a forward-compatible envelope, and a loader rehydrates
the envelope even when a future generation adds new fields.

Forward compatibility is enforced by versioning: each checkpoint
declares a ``schema_version``. The loader refuses newer versions
than it knows about (with a clear message telling the user to
upgrade) and transparently upgrades older ones through migrators.
"""
from __future__ import annotations

from .checkpoint import (
    KLongCheckpoint,
    KLongError,
    KLongStore,
    Migrator,
    resume,
    snapshot,
)

__all__ = [
    "KLongCheckpoint",
    "KLongError",
    "KLongStore",
    "Migrator",
    "resume",
    "snapshot",
]
