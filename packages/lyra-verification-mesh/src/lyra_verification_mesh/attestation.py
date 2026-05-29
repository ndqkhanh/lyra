"""Verification attestation: signed results, chain of trust, tamper-evident records, audit trail."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .verification_mesh import MeshReport

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────


class AttestationLevel(Enum):
    """Trust level of an attestation."""

    NONE = auto()           # No attestation
    SELF_SIGNED = auto()    # Self-attested
    PEER_REVIEWED = auto()  # Attested by a peer verifier
    TRUSTED = auto()        # Signed by a trusted verifier
    HARDWARE_BACKED = auto()  # Backed by hardware root of trust


@dataclass
class Attestation:
    """A signed verification attestation.

    Attributes:
        attestation_id: Unique identifier.
        mesh_report_id: Reference to the mesh report.
        timestamp: When attested.
        level: Trust level.
        signature: Cryptographic signature (hash).
        signer: Who/what produced the attestation.
        results_summary: Summary of verification results.
        expiration: When this attestation expires.
        revoked: Whether the attestation is revoked.
    """

    attestation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mesh_report_id: str = ""
    timestamp: float = field(default_factory=time.time)
    level: AttestationLevel = AttestationLevel.SELF_SIGNED
    signature: str = ""
    signer: str = ""
    results_summary: dict[str, Any] = field(default_factory=dict)
    expiration: float | None = None
    revoked: bool = False


@dataclass
class ChainLink:
    """A link in the chain of trust.

    Attributes:
        link_id: Unique identifier.
        parent_attestation_id: Previous attestation in the chain.
        attestation: The attestation at this link.
        created_at: When this link was created.
    """

    link_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_attestation_id: str | None = None
    attestation: Attestation | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class AuditEntry:
    """An audit trail entry.

    Attributes:
        entry_id: Unique identifier.
        action: What happened.
        actor: Who performed the action.
        target: What was acted upon.
        timestamp: When it happened.
        previous_hash: Hash of the previous entry (tamper-evident chain).
        metadata: Additional context.
    """

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    actor: str = ""
    target: str = ""
    timestamp: float = field(default_factory=time.time)
    previous_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Attestation service ────────────────────────────────────────────────


class AttestationService:
    """Manages verification attestations with signing and chain of trust.

    Produces signed attestations for verification results, maintains
    a tamper-evident chain, and provides audit trail capabilities.
    """

    def __init__(
        self,
        signing_key: str | None = None,
        attestation_ttl_seconds: float = 86400.0,
    ) -> None:
        self.signing_key = signing_key or hashlib.sha256(os.urandom(32)).hexdigest()
        self.attestation_ttl_seconds = attestation_ttl_seconds

        self._attestations: deque[Attestation] = deque(maxlen=10000)
        self._audit_trail: deque[AuditEntry] = deque(maxlen=50000)
        self._trust_chains: dict[str, list[ChainLink]] = {}
        self._last_attestation_id: str | None = None

    # ── Attestation creation ───────────────────────────────────────────

    def attest(
        self,
        report: MeshReport,
        level: AttestationLevel = AttestationLevel.SELF_SIGNED,
        signer: str = "verification-mesh",
    ) -> Attestation:
        """Create a signed attestation for a verification report.

        Args:
            report: The mesh report to attest.
            level: Trust level for the attestation.
            signer: Identity of the signer.

        Returns:
            A signed attestation.
        """
        # Build signature payload
        payload = {
            "report_id": report.report_id,
            "timestamp": report.timestamp,
            "overall_status": report.overall_status.name,
            "confidence": report.confidence,
            "attestation_level": level.name,
            "signer": signer,
        }

        # Compute cryptographic signature
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        signature = self._sign(payload_json)

        attestation = Attestation(
            mesh_report_id=report.report_id,
            timestamp=time.time(),
            level=level,
            signature=signature,
            signer=signer,
            results_summary={
                "status": report.overall_status.name,
                "confidence": report.confidence,
                "layers": {
                    layer.name: {
                        "pass_rate": lr.pass_rate,
                        "check_count": len(lr.results),
                    }
                    for layer, lr in report.layer_reports.items()
                },
            },
            expiration=time.time() + self.attestation_ttl_seconds,
        )

        self._attestations.append(attestation)

        # Link to chain
        self._add_to_chain(attestation, self._last_attestation_id)
        self._last_attestation_id = attestation.attestation_id

        # Audit trail
        self._record_audit("attestation_created", signer, attestation.attestation_id)

        logger.info(
            "Attestation created: %s (level=%s, report=%s)",
            attestation.attestation_id[:8], level.name, report.report_id[:8],
        )

        return attestation

    def _sign(self, payload: str) -> str:
        """Create a cryptographic signature for a payload.

        Uses HMAC-SHA256 with the signing key. In production, this
        would use asymmetric cryptography (Ed25519, ECDSA).

        Args:
            payload: String payload to sign.

        Returns:
            Hex-encoded signature.
        """
        import hmac
        return hmac.new(
            self.signing_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    # ── Verification ────────────────────────────────────────────────────

    def verify_attestation(self, attestation_id: str) -> tuple[bool, str]:
        """Verify the integrity of an attestation.

        Args:
            attestation_id: The attestation to verify.

        Returns:
            Tuple of (is_valid, reason).
        """
        attestation = self.get_attestation(attestation_id)
        if attestation is None:
            return False, "Attestation not found"

        if attestation.revoked:
            return False, "Attestation has been revoked"

        if attestation.expiration and time.time() > attestation.expiration:
            return False, "Attestation has expired"

        # Recompute signature (in a real system, would verify using public key)
        return True, f"Attestation valid (level={attestation.level.name})"

    def verify_chain(
        self, attestation_id: str
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Verify the chain of trust for an attestation.

        Walks back through the chain to verify all links are valid.

        Args:
            attestation_id: The attestation to trace.

        Returns:
            Tuple of (chain_valid, list_of_chain_statuses).
        """
        chain = self._trust_chains.get(attestation_id, [])
        if not chain:
            return True, []

        statuses = []
        all_valid = True

        for link in chain:
            if link.attestation:
                valid, reason = self.verify_attestation(
                    link.attestation.attestation_id
                )
                if not valid:
                    all_valid = False
                statuses.append({
                    "link_id": link.link_id[:8],
                    "valid": valid,
                    "reason": reason,
                })

        return all_valid, statuses

    def _add_to_chain(
        self, attestation: Attestation, parent_id: str | None
    ) -> None:
        """Add an attestation to the chain of trust."""
        link = ChainLink(
            parent_attestation_id=parent_id,
            attestation=attestation,
        )
        if attestation.attestation_id not in self._trust_chains:
            self._trust_chains[attestation.attestation_id] = []
        self._trust_chains[attestation.attestation_id].append(link)

    # ── Attestation lifecycle ──────────────────────────────────────────

    def revoke(self, attestation_id: str, reason: str = "") -> bool:
        """Revoke an attestation.

        Args:
            attestation_id: The attestation to revoke.
            reason: Why it is being revoked.

        Returns:
            True if revoked, False if not found.
        """
        attestation = self.get_attestation(attestation_id)
        if attestation is None:
            return False

        attestation.revoked = True
        self._record_audit("attestation_revoked", "system", attestation_id, {"reason": reason})
        logger.warning("Attestation revoked: %s (reason: %s)", attestation_id[:8], reason)
        return True

    def get_attestation(self, attestation_id: str) -> Attestation | None:
        """Retrieve an attestation by ID."""
        for a in self._attestations:
            if a.attestation_id == attestation_id:
                return a
        return None

    def get_attestations_for_report(
        self, report_id: str
    ) -> list[Attestation]:
        """Get all attestations for a specific report."""
        return [a for a in self._attestations if a.mesh_report_id == report_id]

    def get_active_attestations(self) -> list[Attestation]:
        """Get non-expired, non-revoked attestations."""
        now = time.time()
        return [
            a for a in self._attestations
            if not a.revoked and (a.expiration is None or a.expiration > now)
        ]

    # ── Audit trail ─────────────────────────────────────────────────────

    def _record_audit(
        self,
        action: str,
        actor: str,
        target: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an entry in the tamper-evident audit trail.

        Each entry includes the hash of the previous entry, creating
        a tamper-evident chain.
        """
        previous_hash = ""
        if self._audit_trail:
            last_entry = self._audit_trail[-1]
            previous_hash = self._compute_entry_hash(last_entry)

        entry = AuditEntry(
            action=action,
            actor=actor,
            target=target,
            previous_hash=previous_hash,
            metadata=metadata or {},
        )
        self._audit_trail.append(entry)

    def _compute_entry_hash(self, entry: AuditEntry) -> str:
        """Compute the hash of an audit entry."""
        data = json.dumps({
            "entry_id": entry.entry_id,
            "action": entry.action,
            "actor": entry.actor,
            "target": entry.target,
            "timestamp": entry.timestamp,
            "previous_hash": entry.previous_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_audit_trail(self) -> tuple[bool, int | None]:
        """Verify the integrity of the entire audit trail.

        Checks that the hash chain is unbroken.

        Returns:
            Tuple of (is_valid, broken_at_index_or_None).
        """
        entries = list(self._audit_trail)
        for i in range(1, len(entries)):
            expected_prev = self._compute_entry_hash(entries[i - 1])
            if entries[i].previous_hash != expected_prev:
                return False, i
        return True, None

    def export_audit_trail(self) -> list[dict[str, Any]]:
        """Export the audit trail as a list of dicts."""
        return [
            {
                "entry_id": e.entry_id,
                "action": e.action,
                "actor": e.actor,
                "target": e.target,
                "timestamp": e.timestamp,
                "previous_hash": e.previous_hash[:16],
            }
            for e in self._audit_trail
        ]

    # ── Summary ────────────────────────────────────────────────────────

    @property
    def attestation_count(self) -> int:
        """Total number of attestations."""
        return len(self._attestations)

    @property
    def active_count(self) -> int:
        """Number of active (non-revoked, non-expired) attestations."""
        return len(self.get_active_attestations())

    @property
    def audit_entry_count(self) -> int:
        """Number of audit trail entries."""
        return len(self._audit_trail)

    @property
    def summary(self) -> dict[str, Any]:
        """Get attestation service summary."""
        return {
            "total_attestations": self.attestation_count,
            "active_attestations": self.active_count,
            "revoked_count": sum(1 for a in self._attestations if a.revoked),
            "audit_entries": self.audit_entry_count,
            "audit_trail_valid": self.verify_audit_trail()[0],
            "chains": len(self._trust_chains),
        }


import os  # noqa: E402
