"""Audit Engine for Lyra's Safety Governance Framework.

Provides immutable audit trail with cryptographic verification using Ed25519
signatures and SHA-256 hash chains. Each audit record is cryptographically
signed and linked to the previous record, creating a tamper-evident chain.

Architecture:
    - Immutable audit records (frozen dataclasses)
    - Ed25519 signature for each record
    - SHA-256 hash chain linking records
    - Append-only storage
    - Chain verification
    - Query interface (time range, risk level, decision)
    - Export functionality (JSON, CSV)
"""

from __future__ import annotations

import csv
import hashlib
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .approval_gate import ReasoningFlag, RiskLevel

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    HAS_CRYPTOGRAPHY = True
except ImportError:
    # Graceful fallback if cryptography not installed
    HAS_CRYPTOGRAPHY = False
    ed25519 = None  # type: ignore
    serialization = None  # type: ignore


class Decision(Enum):
    """Final decision on an action after all checks."""

    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"


class Verdict(Enum):
    """Adversarial verification verdict from cross-model review."""

    UNANIMOUS_APPROVE = "unanimous_approve"
    UNANIMOUS_DENY = "unanimous_deny"
    MAJORITY_APPROVE = "majority_approve"
    MAJORITY_DENY = "majority_deny"
    SPLIT = "split"
    NOT_PERFORMED = "not_performed"


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit record with cryptographic verification.

    Each record contains:
        - Unique identifier (UUIDv7 for time-ordered IDs)
        - Timestamp (UTC)
        - Action hash (SHA-256 of the action description)
        - Risk assessment (level, reasoning flags)
        - Adversarial verdict (cross-model votes)
        - Final decision (approved/denied/escalated)
        - Cryptographic signature (Ed25519)
        - Previous record hash (chain link)

    Attributes:
        id: Unique identifier (UUIDv7 format).
        timestamp: When the action was evaluated (UTC).
        action_hash: SHA-256 hash of the action description.
        risk_level: Assessed risk level (LOW/MEDIUM/HIGH/CRITICAL).
        reasoning_flags: Detected reasoning patterns (deception, etc.).
        adversarial_verdict: Result of cross-model adversarial review.
        final_decision: Final decision after all checks.
        signature: Ed25519 signature of the record.
        prev_hash: SHA-256 hash of the previous record (chain link).
        action_description: Optional human-readable action description.
        metadata: Optional additional metadata.
    """

    id: str
    timestamp: datetime
    action_hash: str
    risk_level: RiskLevel
    reasoning_flags: tuple[ReasoningFlag, ...]
    adversarial_verdict: Verdict
    final_decision: Decision
    signature: bytes
    prev_hash: str
    action_description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action_hash": self.action_hash,
            "risk_level": self.risk_level.value,
            "reasoning_flags": [flag.value for flag in self.reasoning_flags],
            "adversarial_verdict": self.adversarial_verdict.value,
            "final_decision": self.final_decision.value,
            "signature": self.signature.hex(),
            "prev_hash": self.prev_hash,
            "action_description": self.action_description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditRecord:
        """Reconstruct record from dictionary."""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action_hash=data["action_hash"],
            risk_level=RiskLevel(data["risk_level"]),
            reasoning_flags=tuple(
                ReasoningFlag(flag) for flag in data["reasoning_flags"]
            ),
            adversarial_verdict=Verdict(data["adversarial_verdict"]),
            final_decision=Decision(data["final_decision"]),
            signature=bytes.fromhex(data["signature"]),
            prev_hash=data["prev_hash"],
            action_description=data.get("action_description", ""),
            metadata=data.get("metadata", {}),
        )

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this record (excluding signature).

        The hash includes all fields except the signature itself, as the
        signature is computed over the hash. This creates a deterministic
        hash that can be used for chain verification.

        Returns:
            Hex-encoded SHA-256 hash of the record.
        """
        hash_input = (
            f"{self.id}|{self.timestamp.isoformat()}|{self.action_hash}|"
            f"{self.risk_level.value}|"
            f"{','.join(flag.value for flag in self.reasoning_flags)}|"
            f"{self.adversarial_verdict.value}|{self.final_decision.value}|"
            f"{self.prev_hash}"
        )
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


class AuditLogger:
    """Cryptographically-signed audit logger with immutable storage.

    Maintains an append-only audit trail where each record is:
        1. Cryptographically signed with Ed25519
        2. Linked to the previous record via hash chain
        3. Stored immutably (no updates or deletes)

    The logger uses a private key for signing and provides the public key
    for verification. Records are stored in-memory and can be persisted
    to disk in JSON format.

    Attributes:
        private_key: Ed25519 private key for signing records.
        public_key: Ed25519 public key for verification.
        records: Immutable tuple of all audit records.
    """

    def __init__(self, private_key: bytes | None = None) -> None:
        """Initialize audit logger with optional private key.

        Args:
            private_key: Ed25519 private key bytes. If None, generates new key.

        Raises:
            ImportError: If cryptography library is not installed.
        """
        if ed25519 is None:
            raise ImportError(
                "cryptography library required for audit engine. "
                "Install with: pip install cryptography"
            )

        if private_key is None:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
                private_key
            )

        self._public_key = self._private_key.public_key()
        self._records: list[AuditRecord] = []

    @property
    def public_key(self) -> bytes:
        """Get public key for signature verification."""
        if not HAS_CRYPTOGRAPHY or serialization is None:
            raise ImportError("cryptography library required")
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def private_key_bytes(self) -> bytes:
        """Get private key bytes for persistence."""
        if not HAS_CRYPTOGRAPHY or serialization is None:
            raise ImportError("cryptography library required")
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    @property
    def records(self) -> tuple[AuditRecord, ...]:
        """Get immutable view of all audit records."""
        return tuple(self._records)

    def log(
        self,
        action_description: str,
        risk_level: RiskLevel,
        reasoning_flags: Sequence[ReasoningFlag],
        adversarial_verdict: Verdict,
        final_decision: Decision,
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Log an action with cryptographic signature.

        Creates a new audit record, signs it with Ed25519, and appends it
        to the immutable audit trail. The record is linked to the previous
        record via hash chain.

        Args:
            action_description: Human-readable description of the action.
            risk_level: Assessed risk level.
            reasoning_flags: Detected reasoning patterns.
            adversarial_verdict: Result of cross-model review.
            final_decision: Final decision after all checks.
            metadata: Optional additional metadata.

        Returns:
            The newly created and signed audit record.
        """
        # Generate UUIDv7 (time-ordered UUID)
        record_id = self._generate_uuidv7()

        # Compute action hash
        action_hash = hashlib.sha256(
            action_description.encode("utf-8")
        ).hexdigest()

        # Get previous record hash (or genesis hash)
        prev_hash = (
            self._records[-1].compute_hash()
            if self._records
            else "0" * 64  # Genesis hash
        )

        # Create unsigned record
        timestamp = datetime.now(timezone.utc)
        unsigned_record = AuditRecord(
            id=record_id,
            timestamp=timestamp,
            action_hash=action_hash,
            risk_level=risk_level,
            reasoning_flags=tuple(reasoning_flags),
            adversarial_verdict=adversarial_verdict,
            final_decision=final_decision,
            signature=b"",  # Placeholder
            prev_hash=prev_hash,
            action_description=action_description,
            metadata=metadata or {},
        )

        # Sign the record hash
        record_hash = unsigned_record.compute_hash()
        signature = self._private_key.sign(record_hash.encode("utf-8"))

        # Create final signed record
        signed_record = AuditRecord(
            id=record_id,
            timestamp=timestamp,
            action_hash=action_hash,
            risk_level=risk_level,
            reasoning_flags=tuple(reasoning_flags),
            adversarial_verdict=adversarial_verdict,
            final_decision=final_decision,
            signature=signature,
            prev_hash=prev_hash,
            action_description=action_description,
            metadata=metadata or {},
        )

        # Append to immutable trail
        self._records.append(signed_record)
        return signed_record

    def verify_record(self, record: AuditRecord) -> bool:
        """Verify cryptographic signature of a single record.

        Args:
            record: The audit record to verify.

        Returns:
            True if signature is valid, False otherwise.
        """
        try:
            record_hash = record.compute_hash()
            self._public_key.verify(record.signature, record_hash.encode("utf-8"))
            return True
        except Exception:
            return False

    def verify_chain(self) -> tuple[bool, list[str]]:
        """Verify integrity of the entire audit chain.

        Checks:
            1. Each record's signature is valid
            2. Each record's prev_hash matches the previous record's hash
            3. Genesis record has correct genesis hash

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors: list[str] = []

        if not self._records:
            return True, []

        # Verify genesis record
        if self._records[0].prev_hash != "0" * 64:
            errors.append(
                f"Genesis record {self._records[0].id} has invalid prev_hash"
            )

        # Verify each record
        for i, record in enumerate(self._records):
            # Verify signature
            if not self.verify_record(record):
                errors.append(f"Record {record.id} has invalid signature")

            # Verify chain link (skip genesis)
            if i > 0:
                expected_prev_hash = self._records[i - 1].compute_hash()
                if record.prev_hash != expected_prev_hash:
                    errors.append(
                        f"Record {record.id} has broken chain link: "
                        f"expected {expected_prev_hash}, got {record.prev_hash}"
                    )

        return len(errors) == 0, errors

    def query(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        risk_levels: Sequence[RiskLevel] | None = None,
        decisions: Sequence[Decision] | None = None,
        reasoning_flags: Sequence[ReasoningFlag] | None = None,
    ) -> tuple[AuditRecord, ...]:
        """Query audit records with filters.

        Args:
            start_time: Filter records after this time (inclusive).
            end_time: Filter records before this time (inclusive).
            risk_levels: Filter by risk levels.
            decisions: Filter by final decisions.
            reasoning_flags: Filter records containing any of these flags.

        Returns:
            Tuple of matching audit records.
        """
        results = self._records

        if start_time:
            results = [r for r in results if r.timestamp >= start_time]

        if end_time:
            results = [r for r in results if r.timestamp <= end_time]

        if risk_levels:
            risk_set = set(risk_levels)
            results = [r for r in results if r.risk_level in risk_set]

        if decisions:
            decision_set = set(decisions)
            results = [r for r in results if r.final_decision in decision_set]

        if reasoning_flags:
            flag_set = set(reasoning_flags)
            results = [
                r for r in results if any(flag in flag_set for flag in r.reasoning_flags)
            ]

        return tuple(results)

    def export_json(self, path: Path | str) -> None:
        """Export audit trail to JSON file.

        Args:
            path: Output file path.
        """
        path = Path(path)
        data = {
            "public_key": self.public_key.hex(),
            "records": [record.to_dict() for record in self._records],
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_csv(self, path: Path | str) -> None:
        """Export audit trail to CSV file.

        Args:
            path: Output file path.
        """
        path = Path(path)

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "id",
                "timestamp",
                "action_hash",
                "risk_level",
                "reasoning_flags",
                "adversarial_verdict",
                "final_decision",
                "signature",
                "prev_hash",
                "action_description",
            ])

            # Records
            for record in self._records:
                writer.writerow([
                    record.id,
                    record.timestamp.isoformat(),
                    record.action_hash,
                    record.risk_level.value,
                    ",".join(flag.value for flag in record.reasoning_flags),
                    record.adversarial_verdict.value,
                    record.final_decision.value,
                    record.signature.hex(),
                    record.prev_hash,
                    record.action_description,
                ])

    def load_json(self, path: Path | str) -> None:
        """Load audit trail from JSON file.

        Args:
            path: Input file path.

        Raises:
            ValueError: If loaded records fail verification.
        """
        path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Verify public key matches
        loaded_public_key = bytes.fromhex(data["public_key"])
        if loaded_public_key != self.public_key:
            raise ValueError(
                "Public key mismatch: loaded records were signed with different key"
            )

        # Load records
        loaded_records = [
            AuditRecord.from_dict(record_data) for record_data in data["records"]
        ]

        # Verify chain before accepting
        temp_records = self._records
        self._records = loaded_records
        is_valid, errors = self.verify_chain()

        if not is_valid:
            self._records = temp_records
            raise ValueError(f"Loaded audit chain is invalid: {errors}")

    @staticmethod
    def _generate_uuidv7() -> str:
        """Generate UUIDv7 (time-ordered UUID).

        UUIDv7 embeds a timestamp in the UUID, making it naturally sortable
        by creation time. This is useful for audit logs where chronological
        ordering is important.

        Returns:
            UUIDv7 string.
        """
        # UUIDv7 format: timestamp_ms (48 bits) + version (4 bits) +
        # random (12 bits) + variant (2 bits) + random (62 bits)
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        # Generate random bits
        random_bits = uuid.uuid4().bytes

        # Construct UUIDv7
        # First 6 bytes: timestamp_ms (big-endian)
        uuid_bytes = bytearray(timestamp_ms.to_bytes(6, "big"))

        # Bytes 6-7: version (0x7) in high nibble + random in low nibble
        uuid_bytes.extend([
            (0x70 | (random_bits[6] & 0x0F)),  # Version 7
            random_bits[7],
        ])

        # Bytes 8-9: variant (0b10) in high 2 bits + random in low 6 bits
        uuid_bytes.extend([
            (0x80 | (random_bits[8] & 0x3F)),  # Variant
            random_bits[9],
        ])

        # Bytes 10-15: random
        uuid_bytes.extend(random_bits[10:16])

        return str(uuid.UUID(bytes=bytes(uuid_bytes)))


__all__ = [
    "AuditLogger",
    "AuditRecord",
    "Decision",
    "Verdict",
]
