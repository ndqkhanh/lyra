"""Custom exceptions for verification mesh."""

from __future__ import annotations


class VerificationError(Exception):
    """Base exception for verification errors."""


class VerificationFailedError(VerificationError):
    """Raised when verification fails with specific details."""

    def __init__(self, verifier: str, message: str, details: dict | None = None) -> None:
        self.verifier = verifier
        self.details = details or {}
        super().__init__(f"[{verifier}] {message}")


class CPLVerificationError(VerificationError):
    """Raised when continuous prompt-level verification fails."""

    def __init__(self, check_name: str, token_index: int, message: str) -> None:
        self.check_name = check_name
        self.token_index = token_index
        super().__init__(f"CPL check '{check_name}' at token {token_index}: {message}")


class FormalVerificationError(VerificationError):
    """Raised when pseudo-formal verification fails."""

    def __init__(self, property_name: str, violation: str) -> None:
        self.property_name = property_name
        self.violation = violation
        super().__init__(f"Formal property '{property_name}' violated: {violation}")


class RuntimeVerificationError(VerificationError):
    """Raised when runtime behavior verification fails."""

    def __init__(self, behavior: str, message: str) -> None:
        self.behavior = behavior
        super().__init__(f"Runtime behavior '{behavior}' failed: {message}")


class AttestationError(VerificationError):
    """Raised when verification attestation fails."""

    def __init__(self, attestation_id: str, reason: str) -> None:
        self.attestation_id = attestation_id
        super().__init__(f"Attestation '{attestation_id}' invalid: {reason}")


class MeshConfigurationError(VerificationError):
    """Raised when the verification mesh is misconfigured."""

    def __init__(self, component: str, message: str) -> None:
        self.component = component
        super().__init__(f"Mesh configuration error in '{component}': {message}")
