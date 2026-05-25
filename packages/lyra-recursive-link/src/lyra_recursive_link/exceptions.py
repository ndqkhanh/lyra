"""Custom exceptions for lyra-recursive-link."""

from __future__ import annotations


class EncodingError(Exception):
    """Raised when latent encoding fails."""


class DecodingError(Exception):
    """Raised when latent decoding fails."""


class LinkError(Exception):
    """Raised when recursive link operations fail."""


class CreditAssignmentError(Exception):
    """Raised when credit assignment computation fails."""


class CollaborationError(Exception):
    """Raised when collaboration pattern execution fails."""


class BusError(Exception):
    """Raised when communication bus operations fail."""


class MessageDeliveryError(BusError):
    """Raised when a message cannot be delivered on the bus."""
