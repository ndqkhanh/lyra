"""WitnessLattice — convenient wrappers over ProvenanceLedger.

The lattice is the *typed query layer* on top of the raw ledger. It offers
kind-aware constructors (``record_decision``, ``record_retrieval``,
``record_verdict``…) and human-readable provenance explanations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .ledger import ProvenanceLedger
from .types import Witness, WitnessKind


@dataclass
class WitnessLattice:
    """Typed wrappers + explanation queries over a :class:`ProvenanceLedger`."""

    ledger: ProvenanceLedger = field(default_factory=ProvenanceLedger)

    # --- Typed constructors ---------------------------------------------

    def record_decision(
        self,
        *,
        agent_id: str,
        action: str,
        fingerprint: str = "",
        parent_witnesses: Iterable[str] = (),
    ) -> Witness:
        """Record an agent decision (action + fingerprint)."""
        w = Witness.create(
            kind=WitnessKind.AGENT_DECISION,
            issued_by=agent_id,
            content={"action": action, "fingerprint": fingerprint},
            parent_witnesses=tuple(parent_witnesses),
        )
        return self.ledger.append(w)

    def record_tool_result(
        self,
        *,
        agent_id: str,
        tool_name: str,
        args: dict[str, Any],
        result_summary: str,
        parent_witnesses: Iterable[str] = (),
    ) -> Witness:
        """Record a tool invocation + result summary."""
        w = Witness.create(
            kind=WitnessKind.TOOL_RESULT,
            issued_by=agent_id,
            content={
                "tool_name": tool_name,
                "args": args,
                "result_summary": result_summary,
            },
            parent_witnesses=tuple(parent_witnesses),
        )
        return self.ledger.append(w)

    def record_verdict(
        self,
        *,
        verifier_name: str,
        passed: bool,
        severity: str,
        axes: dict[str, bool],
        parent_witnesses: Iterable[str] = (),
    ) -> Witness:
        """Record a verifier composer's composite verdict."""
        w = Witness.create(
            kind=WitnessKind.VERIFIER_VERDICT,
            issued_by=verifier_name,
            content={
                "passed": passed,
                "severity": severity,
                "axes": dict(axes),
            },
            parent_witnesses=tuple(parent_witnesses),
        )
        return self.ledger.append(w)

    def record_human_approval(
        self,
        *,
        user_id: str,
        approved: bool,
        scope: str,
        rationale: str = "",
        parent_witnesses: Iterable[str] = (),
    ) -> Witness:
        """Record a human-in-the-loop approval (or rejection)."""
        w = Witness.create(
            kind=WitnessKind.HUMAN_APPROVAL,
            issued_by=user_id,
            content={
                "approved": approved,
                "scope": scope,
                "rationale": rationale,
            },
            parent_witnesses=tuple(parent_witnesses),
        )
        return self.ledger.append(w)

    def record_retrieval(
        self,
        *,
        retriever_name: str,
        query: str,
        doc_ids: tuple[str, ...] | list[str],
        parent_witnesses: Iterable[str] = (),
    ) -> Witness:
        """Record a retrieval call + the doc IDs returned."""
        w = Witness.create(
            kind=WitnessKind.RETRIEVAL,
            issued_by=retriever_name,
            content={
                "query": query,
                "doc_ids": list(doc_ids),
            },
            parent_witnesses=tuple(parent_witnesses),
        )
        return self.ledger.append(w)

    def record_inference(
        self,
        *,
        agent_id: str,
        claim: str,
        supporting: Iterable[str],
    ) -> Witness:
        """Record an inference — must cite supporting witnesses."""
        supporting_tuple = tuple(supporting)
        if not supporting_tuple:
            raise ValueError(
                "INFERENCE witnesses must cite at least one supporting witness"
            )
        w = Witness.create(
            kind=WitnessKind.INFERENCE,
            issued_by=agent_id,
            content={"claim": claim},
            parent_witnesses=supporting_tuple,
        )
        return self.ledger.append(w)

    # --- Queries --------------------------------------------------------

    def explain(self, witness_id: str, *, max_depth: int = 10) -> str:
        """Render a human-readable provenance trace as bullet text."""
        chain = self.ledger.trace_provenance(witness_id, max_depth=max_depth)
        if not chain:
            return f"Witness {witness_id!r} not found."
        lines = []
        for i, w in enumerate(chain):
            indent = "  " * min(i, 8)
            summary = self._summarize(w)
            lines.append(f"{indent}- [{w.kind.value}] {w.short_id()} by {w.issued_by}: {summary}")
        return "\n".join(lines)

    def supporting_for(self, witness_id: str) -> list[Witness]:
        """Return the *direct* parent witnesses of a witness."""
        w = self.ledger.get(witness_id)
        if w is None:
            return []
        return [
            self.ledger.get(p)
            for p in w.parent_witnesses
            if self.ledger.get(p) is not None
        ]  # type: ignore[misc]

    def cited_by(self, witness_id: str) -> list[Witness]:
        """Reverse lookup: witnesses citing the given witness as a parent."""
        return [
            w
            for w in self.ledger.witnesses_for()
            if witness_id in w.parent_witnesses
        ]

    @staticmethod
    def _summarize(w: Witness) -> str:
        c = w.content
        if w.kind == WitnessKind.AGENT_DECISION:
            return f"action={c.get('action', '?')!r}"
        if w.kind == WitnessKind.TOOL_RESULT:
            return f"tool={c.get('tool_name', '?')!r}"
        if w.kind == WitnessKind.VERIFIER_VERDICT:
            return f"passed={c.get('passed')} severity={c.get('severity', '?')}"
        if w.kind == WitnessKind.HUMAN_APPROVAL:
            return f"approved={c.get('approved')} scope={c.get('scope', '?')!r}"
        if w.kind == WitnessKind.RETRIEVAL:
            n = len(c.get("doc_ids", []))
            return f"query={c.get('query', '')!r} n_docs={n}"
        if w.kind == WitnessKind.INFERENCE:
            return f"claim={c.get('claim', '')!r}"
        if w.kind == WitnessKind.ROUTINE_FIRE:
            return f"routine={c.get('routine_id', '?')!r}"
        if w.kind == WitnessKind.PAGE_EDIT:
            return f"page={c.get('page_id', '?')!r}"
        return ""


__all__ = ["WitnessLattice"]
