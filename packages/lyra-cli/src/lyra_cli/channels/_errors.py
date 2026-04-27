"""Shared exception types for channel adapters.

Adapters depend on these in the import-time path so the rest of the
codebase can `except FeatureUnavailable` uniformly without dragging
each adapter's optional dep along.
"""
from __future__ import annotations


class ChannelError(Exception):
    """Base class for every channel-adapter error."""


class FeatureUnavailable(ChannelError):
    """Raised when an adapter's optional dependency or required
    credential is missing. Carries the exact `pip install lyra[<name>]`
    or env-var fix the user needs."""


class AdapterAuthError(ChannelError):
    """Raised when the adapter cannot authenticate with the provider."""


class AdapterRateLimited(ChannelError):
    """Raised when the provider asks us to back off."""

    def __init__(self, *, retry_after: float = 0.0) -> None:
        super().__init__(f"rate limited; retry after {retry_after}s")
        self.retry_after = retry_after


__all__ = [
    "AdapterAuthError",
    "AdapterRateLimited",
    "ChannelError",
    "FeatureUnavailable",
]
