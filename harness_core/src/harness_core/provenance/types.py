"""Witness — typed content-addressed provenance record."""
from __future__ import annotations

import enum
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


class WitnessKind(str, enum.Enum):
    """Typed witness kinds — what event the witness records."""

    AGENT_DECISION = "agent_decision"
    TOOL_RESULT = "tool_result"
    VERIFIER_VERDICT = "verifier_verdict"
    HUMAN_APPROVAL = "human_approval"
    RETRIEVAL = "retrieval"
    INFERENCE = "inference"
    ROUTINE_FIRE = "routine_fire"
    PAGE_EDIT = "page_edit"
    CUSTOM = "custom"


def compute_witness_id(
    *,
    kind: WitnessKind,
    issued_by: str,
    issued_at: float,
    content: dict[str, Any],
    parent_witnesses: tuple[str, ...] = (),
) -> str:
    """SHA256 of the witness's stable serialisation.

    Two witnesses with identical kind + issuer + timestamp + content +
    parents produce identical IDs. Modifying any field produces a different
    ID — the basis of tamper-evidence.

    >>> wid1 = compute_witness_id(
    ...     kind=WitnessKind.AGENT_DECISION,
    ...     issued_by="agent-1",
    ...     issued_at=1.0,
    ...     content={"action": "search"},
    ... )
    >>> wid2 = compute_witness_id(
    ...     kind=WitnessKind.AGENT_DECISION,
    ...     issued_by="agent-1",
    ...     issued_at=1.0,
    ...     content={"action": "search"},
    ... )
    >>> wid1 == wid2
    True
    """
    payload = json.dumps(
        {
            "kind": kind.value,
            "issued_by": issued_by,
            "issued_at": issued_at,
            "content": content,
            "parents": sorted(parent_witnesses),
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Witness:
    """One immutable witness — content-addressed by SHA256.

    The ``witness_id`` field is computed from the other fields; if you
    construct a Witness directly, supply the correct id (use :func:`Witness.create`
    in normal code).
    """

    witness_id: str
    kind: WitnessKind
    issued_by: str
    issued_at: float
    content: dict[str, Any] = field(default_factory=dict)
    parent_witnesses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.witness_id:
            raise ValueError("witness_id must be non-empty")
        if not self.issued_by:
            raise ValueError("issued_by must be non-empty")
        if self.issued_at < 0:
            raise ValueError(f"issued_at must be >= 0, got {self.issued_at}")

    @classmethod
    def create(
        cls,
        *,
        kind: WitnessKind,
        issued_by: str,
        content: dict[str, Any] | None = None,
        parent_witnesses: tuple[str, ...] | list[str] = (),
        issued_at: float | None = None,
    ) -> "Witness":
        """Construct a Witness with auto-computed witness_id."""
        ts = issued_at if issued_at is not None else time.time()
        body = dict(content or {})
        parents = tuple(parent_witnesses)
        wid = compute_witness_id(
            kind=kind,
            issued_by=issued_by,
            issued_at=ts,
            content=body,
            parent_witnesses=parents,
        )
        return cls(
            witness_id=wid,
            kind=kind,
            issued_by=issued_by,
            issued_at=ts,
            content=body,
            parent_witnesses=parents,
        )

    def verify_integrity(self) -> bool:
        """Confirm ``witness_id`` matches the SHA256 of the content."""
        expected = compute_witness_id(
            kind=self.kind,
            issued_by=self.issued_by,
            issued_at=self.issued_at,
            content=self.content,
            parent_witnesses=self.parent_witnesses,
        )
        return expected == self.witness_id

    def short_id(self, *, length: int = 12) -> str:
        """Truncated id for display."""
        return self.witness_id[:length]


__all__ = ["Witness", "WitnessKind", "compute_witness_id"]
