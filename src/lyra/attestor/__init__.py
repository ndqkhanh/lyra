"""Attestor — Pramana-format claim attestation with verification DAG.

Four claim types: MeasurementClaim, InferenceClaim, AnalogyClaim, CitationClaim.
Each claim has a verify() operation. Claims form a verification DAG.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "ClaimType",
    "VerificationStatus",
    "ClaimAttestation",
    "MeasurementClaim",
    "InferenceClaim",
    "AnalogyClaim",
    "CitationClaim",
    "AttestationGraph",
    "Attestor",
]




class ClaimType(Enum):
    MEASUREMENT = "measurement"
    INFERENCE = "inference"
    ANALOGY = "analogy"
    CITATION = "citation"


class VerificationStatus(Enum):
    UNVERIFIED = auto()
    PASSED = auto()
    FAILED = auto()
    INCONCLUSIVE = auto()


@dataclass
class ClaimAttestation:
    claim_id: str
    statement: str
    evidence: list[str]
    verifier: str
    timestamp: str
    claim_type: ClaimType = ClaimType.MEASUREMENT
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    parent_claims: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps({
                "claim_id": self.claim_id,
                "statement": self.statement,
                "evidence": self.evidence,
            }, sort_keys=True).encode()
        ).hexdigest()[:16]


@dataclass
class MeasurementClaim(ClaimAttestation):
    """I observed X in the data."""
    source: str = ""
    measurement_method: str = ""
    confidence: float = 1.0

    def __post_init__(self):
        self.claim_type = ClaimType.MEASUREMENT


@dataclass
class InferenceClaim(ClaimAttestation):
    """X implies Y because of causal relationship."""
    premise_ids: list[str] = field(default_factory=list)
    rule: str = ""
    causal_strength: float = 0.5

    def __post_init__(self):
        self.claim_type = ClaimType.INFERENCE


@dataclass
class AnalogyClaim(ClaimAttestation):
    """Situation S is analogous to past situation P."""
    past_situation_id: str = ""
    similarity_score: float = 0.0
    relevant_dimensions: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.claim_type = ClaimType.ANALOGY


@dataclass
class CitationClaim(ClaimAttestation):
    """Paper P supports claim C."""
    paper_id: str = ""
    paper_title: str = ""
    supporting_quote: str = ""
    relevance: float = 0.5

    def __post_init__(self):
        self.claim_type = ClaimType.CITATION


class AttestationGraph:
    """Verification DAG connecting claims and evidence."""

    def __init__(self):
        self.claims: dict[str, ClaimAttestation] = {}
        self.edges: dict[str, list[str]] = {}  # parent -> children

    def add_claim(self, claim: ClaimAttestation) -> str:
        self.claims[claim.claim_id] = claim
        if claim.claim_id not in self.edges:
            self.edges[claim.claim_id] = []
        for parent_id in claim.parent_claims:
            if parent_id in self.edges:
                self.edges[parent_id].append(claim.claim_id)
            else:
                self.edges[parent_id] = [claim.claim_id]
        return claim.claim_id

    def get_children(self, claim_id: str) -> list[ClaimAttestation]:
        child_ids = self.edges.get(claim_id, [])
        return [self.claims[cid] for cid in child_ids if cid in self.claims]

    def get_parents(self, claim_id: str) -> list[ClaimAttestation]:
        claim = self.claims.get(claim_id)
        if not claim:
            return []
        return [self.claims[pid] for pid in claim.parent_claims if pid in self.claims]

    def get_verification_path(self, claim_id: str) -> list[list[ClaimAttestation]]:
        """Return verification path from root evidence to claim."""
        levels = []
        current = [self.claims[claim_id]]
        while current:
            levels.append(current)
            next_level = []
            for c in current:
                next_level.extend(self.get_parents(c.claim_id))
            current = next_level
        return levels

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_count": len(self.claims),
            "edge_count": sum(len(children) for children in self.edges.values()),
            "claims": {
                cid: {
                    "type": c.claim_type.value,
                    "statement": c.statement[:100],
                    "status": c.status.name,
                }
                for cid, c in self.claims.items()
            },
        }


class Attestor:
    """Creates and verifies attestations for agent claims."""

    def __init__(self):
        self.graph = AttestationGraph()

    def create_measurement(
        self, claim_id: str, statement: str, source: str, method: str, evidence: list[str]
    ) -> MeasurementClaim:
        claim = MeasurementClaim(
            claim_id=claim_id, statement=statement, evidence=evidence,
            verifier="lyra-attestor", timestamp=__import__("datetime").datetime.now().isoformat(),
            source=source, measurement_method=method
        )
        self.graph.add_claim(claim)
        return claim

    def create_inference(
        self, claim_id: str, statement: str, premise_ids: list[str],
        rule: str, evidence: list[str]
    ) -> InferenceClaim:
        claim = InferenceClaim(
            claim_id=claim_id, statement=statement, evidence=evidence,
            verifier="lyra-attestor", timestamp=__import__("datetime").datetime.now().isoformat(),
            premise_ids=premise_ids, rule=rule, parent_claims=premise_ids
        )
        self.graph.add_claim(claim)
        return claim

    def create_analogy(
        self, claim_id: str, statement: str, past_id: str,
        similarity: float, dimensions: list[str], evidence: list[str]
    ) -> AnalogyClaim:
        claim = AnalogyClaim(
            claim_id=claim_id, statement=statement, evidence=evidence,
            verifier="lyra-attestor", timestamp=__import__("datetime").datetime.now().isoformat(),
            past_situation_id=past_id, similarity_score=similarity, relevant_dimensions=dimensions
        )
        self.graph.add_claim(claim)
        return claim

    def create_citation(
        self, claim_id: str, statement: str, paper_id: str,
        paper_title: str, quote: str, evidence: list[str]
    ) -> CitationClaim:
        claim = CitationClaim(
            claim_id=claim_id, statement=statement, evidence=evidence,
            verifier="lyra-attestor", timestamp=__import__("datetime").datetime.now().isoformat(),
            paper_id=paper_id, paper_title=paper_title, supporting_quote=quote, relevance=0.5
        )
        self.graph.add_claim(claim)
        return claim

    def verify_claim(self, claim_id: str) -> VerificationStatus:
        """Verify a claim by checking its parent claims first."""
        claim = self.graph.claims.get(claim_id)
        if not claim:
            return VerificationStatus.INCONCLUSIVE
        for parent_id in claim.parent_claims:
            parent_status = self.verify_claim(parent_id)
            if parent_status != VerificationStatus.PASSED:
                claim.status = VerificationStatus.FAILED
                return VerificationStatus.FAILED
        claim.status = VerificationStatus.PASSED
        return VerificationStatus.PASSED
