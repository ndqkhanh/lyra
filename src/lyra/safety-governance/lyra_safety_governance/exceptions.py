from __future__ import annotations


class GovernanceError(Exception):
    """Base exception for all governance-related errors."""


class RuleViolationError(GovernanceError):
    """Raised when a static safety rule is violated."""


class PrivilegeError(GovernanceError):
    """Raised when a privilege-related operation fails."""


class AnomalyDetectedError(GovernanceError):
    """Raised when a behavioral anomaly is detected."""


class IsolationError(GovernanceError):
    """Raised when hardware isolation fails."""


class PolicyError(GovernanceError):
    """Raised when a policy operation fails."""


class AuditError(GovernanceError):
    """Raised when an audit operation fails."""


class RiskAssessmentError(GovernanceError):
    """Raised when risk assessment encounters an error."""
