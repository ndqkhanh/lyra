"""Cockpit exception hierarchy."""

from __future__ import annotations


class CockpitError(Exception):
    """Base exception for all cockpit-related errors."""


class IAAEngineError(CockpitError):
    """Raised when the IAA engine encounters an error."""


class TransparencyError(CockpitError):
    """Raised when the transparency dashboard encounters an error."""


class MonitorError(CockpitError):
    """Raised when the agent monitor encounters an error."""


class BudgetError(CockpitError):
    """Raised when the budget dashboard encounters an error."""


class VoiceNotifyError(CockpitError):
    """Raised when the voice notifier encounters an error."""


class ConfigError(CockpitError):
    """Raised when cockpit configuration encounters an error."""
