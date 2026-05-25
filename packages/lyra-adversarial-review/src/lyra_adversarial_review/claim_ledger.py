from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .claim_verifier import Claim, ClaimStatus
from .cross_model_reviewer import ModelFamily
from .exceptions import LedgerError


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    claim: Claim
    timestamp: datetime
    verification_status: ClaimStatus
    reviewer_family: ModelFamily | None = None


@dataclass(frozen=True)
class LedgerQuery:
    status: ClaimStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_confidence: float | None = None
    max_confidence: float | None = None
    reviewer_family: ModelFamily | None = None


@dataclass(frozen=True)
class LedgerStats:
    total: int = 0
    verified: int = 0
    rejected: int = 0
    unverified: int = 0
    verification_rate: float = 0.0


class ClaimLedger:
    """Immutable audit trail of all claims and their verification statuses."""

    def __init__(self) -> None:
        self._entries: dict[str, LedgerEntry] = {}
        self._lock_held = False

    async def record_claim(
        self,
        claim: Claim,
        reviewer_family: ModelFamily | None = None,
    ) -> str:
        entry_id = uuid.uuid4().hex[:12]
        entry = LedgerEntry(
            entry_id=entry_id,
            claim=claim,
            timestamp=datetime.now(timezone.utc),
            verification_status=claim.status,
            reviewer_family=reviewer_family,
        )
        self._entries[entry_id] = entry
        return entry_id

    async def update_status(self, entry_id: str, new_status: ClaimStatus) -> LedgerEntry:
        if entry_id not in self._entries:
            raise LedgerError(f"Entry not found: {entry_id}")
        original = self._entries[entry_id]
        updated = LedgerEntry(
            entry_id=original.entry_id,
            claim=original.claim,
            timestamp=datetime.now(timezone.utc),
            verification_status=new_status,
            reviewer_family=original.reviewer_family,
        )
        self._entries[entry_id] = updated
        return updated

    async def query(self, params: LedgerQuery) -> list[LedgerEntry]:
        results = list(self._entries.values())

        if params.status is not None:
            results = [e for e in results if e.verification_status == params.status]
        if params.date_from is not None:
            results = [e for e in results if e.timestamp >= params.date_from]
        if params.date_to is not None:
            results = [e for e in results if e.timestamp <= params.date_to]
        if params.min_confidence is not None:
            results = [e for e in results if e.claim.confidence >= params.min_confidence]
        if params.max_confidence is not None:
            results = [e for e in results if e.claim.confidence <= params.max_confidence]
        if params.reviewer_family is not None:
            results = [e for e in results if e.reviewer_family == params.reviewer_family]

        return sorted(results, key=lambda e: e.timestamp, reverse=True)

    async def get_unverified(self) -> list[LedgerEntry]:
        return [e for e in self._entries.values() if e.verification_status == ClaimStatus.UNVERIFIED]

    async def get_verified(self) -> list[LedgerEntry]:
        verified_statuses = {
            ClaimStatus.VERIFIED,
            ClaimStatus.INTEGRITY_PASS,
            ClaimStatus.MAPPING_PASS,
            ClaimStatus.AUDIT_PASS,
        }
        return [e for e in self._entries.values() if e.verification_status in verified_statuses]

    async def get_rejected(self) -> list[LedgerEntry]:
        rejected_statuses = {
            ClaimStatus.REJECTED,
            ClaimStatus.INTEGRITY_FAIL,
            ClaimStatus.MAPPING_FAIL,
            ClaimStatus.AUDIT_FAIL,
        }
        return [e for e in self._entries.values() if e.verification_status in rejected_statuses]

    async def get_stats(self) -> LedgerStats:
        total = len(self._entries)
        verified = len(await self.get_verified())
        rejected = len(await self.get_rejected())
        unverified = len(await self.get_unverified())
        verification_rate = verified / max(total, 1)
        return LedgerStats(
            total=total,
            verified=verified,
            rejected=rejected,
            unverified=unverified,
            verification_rate=round(verification_rate, 4),
        )

    async def export_ledger(self, fmt: str = "json") -> str:
        if fmt != "json":
            raise LedgerError(f"Unsupported format: {fmt!r}. Only 'json' is supported.")

        def serialize_entry(entry: LedgerEntry) -> dict:
            return {
                "entry_id": entry.entry_id,
                "claim_text": entry.claim.text,
                "claim_source": entry.claim.source,
                "claim_confidence": entry.claim.confidence,
                "claim_status": entry.claim.status.value,
                "verification_status": entry.verification_status.value,
                "timestamp": entry.timestamp.isoformat(),
                "reviewer_family": entry.reviewer_family.value if entry.reviewer_family else None,
            }

        data = {
            "entries": [serialize_entry(e) for e in self._entries.values()],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
