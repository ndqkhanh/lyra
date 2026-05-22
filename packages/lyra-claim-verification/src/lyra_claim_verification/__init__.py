"""Claim Verification — Pramana-format claims with verification DAG lifecycle."""

from __future__ import annotations

import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Optional

from lyra_attestor import ClaimAttestation, ClaimType, VerificationStatus, AttestationGraph

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    id: str
    claim_type: ClaimType
    statement: str
    evidence: list[str]
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    parent_ids: list[str] = field(default_factory=list)


@dataclass
class MeasurementClaim(Claim):
    source: str = ""
    method: str = ""

    def __post_init__(self):
        self.claim_type = ClaimType.MEASUREMENT


@dataclass
class InferenceClaim(Claim):
    rule: str = ""
    premise_ids: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.claim_type = ClaimType.INFERENCE


@dataclass
class AnalogyClaim(Claim):
    past_situation: str = ""
    similarity: float = 0.0

    def __post_init__(self):
        self.claim_type = ClaimType.ANALOGY


@dataclass
class CitationClaim(Claim):
    paper_id: str = ""
    quote: str = ""

    def __post_init__(self):
        self.claim_type = ClaimType.CITATION


class ClaimDAG:
    """Verification DAG connecting claims in dependency order."""

    def __init__(self):
        self.claims: dict[str, Claim] = {}
        self.children: dict[str, list[str]] = {}

    def add_claim(self, claim: Claim) -> str:
        self.claims[claim.id] = claim
        if claim.id not in self.children:
            self.children[claim.id] = []
        for pid in claim.parent_ids:
            if pid not in self.children:
                self.children[pid] = []
            self.children[pid].append(claim.id)
        return claim.id

    def get_verification_order(self, claim_id: str) -> list[Claim]:
        topo = []
        visited = set()

        def _dfs(cid):
            if cid in visited:
                return
            visited.add(cid)
            claim = self.claims.get(cid)
            if claim:
                topo.append(claim)
                for child_id in self.children.get(cid, []):
                    _dfs(child_id)

        _dfs(claim_id)
        return topo


class ClaimVerifier:
    """Verifies claim chains by resolving dependencies bottom-up."""

    def __init__(self):
        self.dag = ClaimDAG()

    def verify_chain(self, claim_id: str) -> list[dict[str, Any]]:
        results = []
        order = self.dag.get_verification_order(claim_id)
        for claim in reversed(order):
            all_parents_verified = all(
                self.dag.claims[pid].status == VerificationStatus.PASSED
                for pid in claim.parent_ids if pid in self.dag.claims
            )
            if not claim.parent_ids or all_parents_verified:
                claim.status = VerificationStatus.PASSED
            else:
                claim.status = VerificationStatus.FAILED
            results.append({
                "claim_id": claim.id,
                "statement": claim.statement[:80],
                "status": claim.status.name,
                "parents_verified": all_parents_verified,
            })
        return results
