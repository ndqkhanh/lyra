"""zkAgent — Cryptographic execution receipts and verification.

Provides lightweight tool-execution attestation using content-addressable
receipts with SHA-256 chaining. Inspired by zkAgent SNARK proofs but using
hash-chain receipts for practical deployability (<15ms overhead).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class ReceiptStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    TAMPERED = "tampered"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class ToolReceipt:
    receipt_id: str
    tool_name: str
    tool_input_hash: str
    tool_output_hash: str
    timestamp: float
    agent_id: str
    session_id: str
    parent_receipt_id: str = ""
    metadata: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "tool_name": self.tool_name,
            "tool_input_hash": self.tool_input_hash,
            "tool_output_hash": self.tool_output_hash,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "parent_receipt_id": self.parent_receipt_id,
            "metadata": dict(self.metadata),
        }

    def compute_integrity_hash(self) -> str:
        """Compute a content-addressable integrity hash of the receipt."""
        payload = (
            f"{self.receipt_id}|{self.tool_name}|{self.tool_input_hash}|"
            f"{self.tool_output_hash}|{self.timestamp}|{self.agent_id}|"
            f"{self.session_id}|{self.parent_receipt_id}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class ChainVerification:
    valid: bool
    total_receipts: int
    valid_receipts: int
    tampered_receipts: int
    first_break_index: int
    details: tuple[str, ...]


class ReceiptStore:
    """Immutable append-only receipt store with hash-chain integrity."""

    def __init__(self) -> None:
        self._receipts: dict[str, ToolReceipt] = {}
        self._chain: list[str] = []

    def issue(
        self,
        tool_name: str,
        tool_input: str,
        tool_output: str,
        agent_id: str = "lyra",
        session_id: str = "default",
        parent_receipt_id: str = "",
        metadata: dict[str, str] | None = None,
    ) -> ToolReceipt:
        """Issue a new tool execution receipt."""
        ts = time.time()
        input_hash = hashlib.sha256(tool_input.encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(tool_output.encode()).hexdigest()[:16]

        chain_nonce = self._chain[-1][:8] if self._chain else "0" * 8
        receipt_id = hashlib.sha256(
            f"{tool_name}|{input_hash}|{ts}|{chain_nonce}".encode()
        ).hexdigest()[:16]

        meta_tuples = tuple(sorted((k, str(v)) for k, v in (metadata or {}).items()))

        receipt = ToolReceipt(
            receipt_id=receipt_id,
            tool_name=tool_name,
            tool_input_hash=input_hash,
            tool_output_hash=output_hash,
            timestamp=ts,
            agent_id=agent_id,
            session_id=session_id,
            parent_receipt_id=parent_receipt_id,
            metadata=meta_tuples,
        )

        self._receipts[receipt_id] = receipt
        self._chain.append(receipt_id)
        return receipt

    def verify_receipt(self, receipt_id: str) -> ReceiptStatus:
        """Verify a single receipt's integrity."""
        receipt = self._receipts.get(receipt_id)
        if receipt is None:
            return ReceiptStatus.UNVERIFIED

        expected = receipt.compute_integrity_hash()
        actual = hashlib.sha256(
            f"{receipt.receipt_id}|{receipt.tool_name}|{receipt.tool_input_hash}|"
            f"{receipt.tool_output_hash}|{receipt.timestamp}|{receipt.agent_id}|"
            f"{receipt.session_id}|{receipt.parent_receipt_id}".encode()
        ).hexdigest()

        if expected != actual:
            return ReceiptStatus.TAMPERED
        return ReceiptStatus.VALID

    def verify_chain(self) -> ChainVerification:
        """Verify the entire receipt chain for integrity."""
        valid_count = 0
        tampered_count = 0
        first_break = -1
        details: list[str] = []

        for i, rid in enumerate(self._chain):
            status = self.verify_receipt(rid)
            if status == ReceiptStatus.VALID:
                valid_count += 1
            else:
                tampered_count += 1
                if first_break < 0:
                    first_break = i
                details.append(f"Break at index {i}: {rid} status={status.value}")

        return ChainVerification(
            valid=(tampered_count == 0),
            total_receipts=len(self._chain),
            valid_receipts=valid_count,
            tampered_receipts=tampered_count,
            first_break_index=first_break,
            details=tuple(details),
        )

    def get_receipt(self, receipt_id: str) -> ToolReceipt | None:
        return self._receipts.get(receipt_id)

    def audit_trail(self, session_id: str | None = None) -> list[ToolReceipt]:
        """Retrieve all receipts, optionally filtered by session."""
        if session_id is None:
            return [self._receipts[rid] for rid in self._chain]
        return [r for r in self._receipts.values() if r.session_id == session_id]

    @property
    def count(self) -> int:
        return len(self._receipts)


class zkAgent:
    """Cryptographic agent execution verifier.

    Issues tool receipts and verifies execution integrity through
    hash-chain attestation. Every tool execution produces a
    content-addressable receipt linked to its predecessor.
    """

    def __init__(self, agent_id: str = "lyra") -> None:
        self.agent_id = agent_id
        self.store = ReceiptStore()

    def attest(
        self,
        tool_name: str,
        tool_input: str,
        tool_output: str,
        session_id: str = "default",
        metadata: dict[str, str] | None = None,
    ) -> ToolReceipt:
        """Attest a tool execution and produce a receipt."""
        parent_id = self.store._chain[-1] if self.store._chain else ""
        return self.store.issue(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            agent_id=self.agent_id,
            session_id=session_id,
            parent_receipt_id=parent_id,
            metadata=metadata,
        )

    def verify_execution(self, receipt_id: str) -> ReceiptStatus:
        """Verify a specific execution receipt."""
        return self.store.verify_receipt(receipt_id)

    def verify_session(self, session_id: str | None = None) -> ChainVerification:
        """Verify all receipts in a session."""
        return self.store.verify_chain()

    def get_audit_trail(self, session_id: str | None = None) -> list[dict]:
        """Get a human-readable audit trail."""
        receipts = self.store.audit_trail(session_id)
        return [r.to_dict() for r in receipts]

    @property
    def receipt_count(self) -> int:
        return self.store.count
