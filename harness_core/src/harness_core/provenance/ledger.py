"""ProvenanceLedger — append-only typed-witness store.

Witnesses are appended once and never mutated. Lookups are by witness_id,
kind, or issuer. Trace-provenance walks the parent chain to show *why* a
witness exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from .types import Witness, WitnessKind


@dataclass
class ProvenanceLedger:
    """Append-only witness store.

    >>> ledger = ProvenanceLedger()
    >>> w1 = ledger.append(Witness.create(
    ...     kind=WitnessKind.RETRIEVAL,
    ...     issued_by="retriever-1",
    ...     content={"query": "X", "n_docs": 3},
    ... ))
    >>> w2 = ledger.append(Witness.create(
    ...     kind=WitnessKind.INFERENCE,
    ...     issued_by="agent-1",
    ...     content={"claim": "X is true"},
    ...     parent_witnesses=[w1.witness_id],
    ... ))
    >>> chain = ledger.trace_provenance(w2.witness_id)
    >>> [w.kind for w in chain] == [WitnessKind.INFERENCE, WitnessKind.RETRIEVAL]
    True
    """

    _witnesses: dict[str, Witness] = field(default_factory=dict)

    def append(self, witness: Witness) -> Witness:
        """Append a witness. Idempotent on identical witness_id; rejects
        collision with different content (shouldn't happen if SHA256 holds)."""
        existing = self._witnesses.get(witness.witness_id)
        if existing is not None:
            if existing != witness:
                raise ValueError(
                    f"witness_id collision with different content: {witness.witness_id!r}"
                )
            return existing
        # Verify integrity at insert.
        if not witness.verify_integrity():
            raise ValueError(
                f"witness_id mismatch: stored id doesn't match content SHA256"
            )
        # Verify parent witnesses exist.
        for parent_id in witness.parent_witnesses:
            if parent_id not in self._witnesses:
                raise KeyError(
                    f"parent witness {parent_id!r} not in ledger; "
                    f"append parents before children"
                )
        self._witnesses[witness.witness_id] = witness
        return witness

    def get(self, witness_id: str) -> Optional[Witness]:
        return self._witnesses.get(witness_id)

    def __contains__(self, witness_id: object) -> bool:
        return isinstance(witness_id, str) and witness_id in self._witnesses

    def __len__(self) -> int:
        return len(self._witnesses)

    def witnesses_for(
        self,
        *,
        kind: Optional[WitnessKind] = None,
        issued_by: Optional[str] = None,
    ) -> list[Witness]:
        """Filter witnesses by kind and/or issuer."""
        out = list(self._witnesses.values())
        if kind is not None:
            out = [w for w in out if w.kind == kind]
        if issued_by is not None:
            out = [w for w in out if w.issued_by == issued_by]
        # Stable order: by issued_at ascending.
        out.sort(key=lambda w: (w.issued_at, w.witness_id))
        return out

    def trace_provenance(
        self,
        witness_id: str,
        *,
        max_depth: int = 100,
    ) -> list[Witness]:
        """BFS over parent_witnesses; return ancestors deepest-first.

        The returned list starts with the requested witness, then walks parent
        chains. Identical ancestors are deduplicated (a witness can be cited
        by multiple descendants but only appears once in the trace).
        """
        target = self._witnesses.get(witness_id)
        if target is None:
            return []
        seen: dict[str, int] = {witness_id: 0}
        order: list[Witness] = [target]
        # BFS frontier.
        frontier: list[tuple[str, int]] = [(witness_id, 0)]
        while frontier:
            current_id, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            current = self._witnesses[current_id]
            for parent_id in current.parent_witnesses:
                if parent_id in seen:
                    continue
                parent = self._witnesses.get(parent_id)
                if parent is None:
                    continue  # dangling parent (shouldn't happen due to append check)
                seen[parent_id] = depth + 1
                order.append(parent)
                frontier.append((parent_id, depth + 1))
        return order

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """Verify every witness's SHA256 is consistent.

        Returns ``(all_valid, list_of_invalid_witness_ids)``. Useful as a
        periodic audit to detect tampering.
        """
        invalid: list[str] = []
        for wid, w in self._witnesses.items():
            if not w.verify_integrity():
                invalid.append(wid)
        return (len(invalid) == 0), invalid

    def stats(self) -> dict[str, int]:
        c = {k.value: 0 for k in WitnessKind}
        issuers: set[str] = set()
        for w in self._witnesses.values():
            c[w.kind.value] += 1
            issuers.add(w.issued_by)
        c["total"] = len(self._witnesses)
        c["issuers"] = len(issuers)
        return c


__all__ = ["ProvenanceLedger"]
