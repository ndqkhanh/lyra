"""Swarm exception hierarchy."""

from __future__ import annotations


class SwarmError(Exception):
    """Base exception for all swarm-related errors."""


class DispatchError(SwarmError):
    """Raised when task dispatch fails."""


class SprintError(SwarmError):
    """Raised when a sprint workflow phase transition fails."""


class SquadError(SwarmError):
    """Raised when squad operations fail."""


class CoalitionError(SwarmError):
    """Raised when coalition formation fails."""


class AutopilotError(SwarmError):
    """Raised when autonomous job scheduling fails."""


class MessagingError(SwarmError):
    """Raised when inter-agent messaging fails."""


class ConsensusError(SwarmError):
    """Raised when consensus building fails."""
