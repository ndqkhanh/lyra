"""Shared sentinel for optional-dep guards."""
from __future__ import annotations


class FeatureUnavailable(RuntimeError):
    """Raised when an optional-dep backed feature is used but the
    underlying package / daemon / credential is missing.

    The message always includes an install or setup hint so the user
    can immediately unblock themselves.
    """


__all__ = ["FeatureUnavailable"]
