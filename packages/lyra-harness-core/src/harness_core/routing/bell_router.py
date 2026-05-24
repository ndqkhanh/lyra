"""BELLE-style query-type router (without the bi-level debate).

BELLE (Zhang et al. ACL 2025, arXiv:2505.11811) routes multi-hop QA queries to
the right operator method per question type. Most of BELLE's empirical gain
comes from the routing; the bi-level debate adds compute that doesn't survive
the [docs/202] §3 equal-budget critique. This module ships the router cheaply.

Five default query types cover the canon:

    SINGLE_HOP — direct retrieval, no chain.
    MULTI_HOP_BRIDGE — IRCoT-style externalised chain on a bridge entity.
    FAN_OUT — parallel sub-question dispatch (5+ documents needed).
    GLOBAL_SENSEMAKING — GraphRAG community-summary scope.
    OPEN_BROWSE — agentic search; breadth/depth knobs.

Subclasses or alternative classifiers (LLM-backed, fine-tuned) plug in via
the :class:`Classifier` Protocol.
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Optional, Protocol


class QueryType(str, enum.Enum):
    """Five operator-shaped query types from the multi-hop canon."""

    SINGLE_HOP = "single_hop"
    MULTI_HOP_BRIDGE = "multi_hop_bridge"
    FAN_OUT = "fan_out"
    GLOBAL_SENSEMAKING = "global_sensemaking"
    OPEN_BROWSE = "open_browse"


@dataclass(frozen=True)
class RouteDecision:
    """The router's verdict for a query."""

    query: str
    query_type: QueryType
    confidence: float  # 0.0..1.0
    reason: str
    suggested_operators: tuple[str, ...] = ()  # e.g. ("ircot", "chain_of_note")

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


class Classifier(Protocol):
    """Pluggable classifier; production wires an LLM-backed one."""

    name: str

    def classify(self, query: str) -> RouteDecision: ...


# --- Rule-based default classifier ----------------------------------------


_FAN_OUT_HINTS = (
    re.compile(r"\b(all|every|each|both|several|multiple|list of)\b", re.I),
    re.compile(r"\b(top \d+|first \d+|\d+ best)\b", re.I),
    re.compile(r"\b(compare|contrast|vs\.?)\b", re.I),
)
_BRIDGE_HINTS = (
    re.compile(r"\b(of (?:the\s+)?\w+ of)\b", re.I),  # "the X of the Y of Z"
    re.compile(r"\b(who (?:directed|wrote|founded|invented|married|leads))\b", re.I),
    re.compile(r"\b(spouse|child|parent|teacher|mentor|director|founder) of\b", re.I),
)
_GLOBAL_HINTS = (
    re.compile(r"\b(overall|across the (?:corpus|literature)|main themes?|big picture)\b", re.I),
    re.compile(r"\b(summari[sz]e (?:the|all|everything))\b", re.I),
    re.compile(r"\b(landscape|state of the (?:art|field))\b", re.I),
)
_OPEN_BROWSE_HINTS = (
    re.compile(r"\b(latest|recent|today|news|current)\b", re.I),
    re.compile(r"\b(go (?:browse|find|look)|navigate|crawl)\b", re.I),
    re.compile(r"\bsearch (?:the )?web\b", re.I),
)


@dataclass
class RuleBasedClassifier:
    """Pattern-based fallback classifier — zero-dep, deterministic.

    Heuristic only; production should layer a small LM-backed classifier on
    top, falling back to this for cold-start. Used for tests + as a baseline
    against which an LM classifier's lift is measured.

    >>> RuleBasedClassifier().classify("who directed Casablanca").query_type
    <QueryType.MULTI_HOP_BRIDGE: 'multi_hop_bridge'>
    >>> RuleBasedClassifier().classify("list all G20 countries").query_type
    <QueryType.FAN_OUT: 'fan_out'>
    """

    name: str = "rule-based-classifier-v1"

    def classify(self, query: str) -> RouteDecision:
        if not query or not query.strip():
            return RouteDecision(
                query=query,
                query_type=QueryType.SINGLE_HOP,
                confidence=0.0,
                reason="empty query",
            )

        # Score each type; pick the highest.
        scores: dict[QueryType, int] = {qt: 0 for qt in QueryType}
        for pat in _FAN_OUT_HINTS:
            if pat.search(query):
                scores[QueryType.FAN_OUT] += 1
        for pat in _BRIDGE_HINTS:
            if pat.search(query):
                scores[QueryType.MULTI_HOP_BRIDGE] += 1
        for pat in _GLOBAL_HINTS:
            if pat.search(query):
                scores[QueryType.GLOBAL_SENSEMAKING] += 1
        for pat in _OPEN_BROWSE_HINTS:
            if pat.search(query):
                scores[QueryType.OPEN_BROWSE] += 1

        # Default fallback for short/declarative queries: SINGLE_HOP.
        max_score = max(scores.values())
        if max_score == 0:
            n_words = len(query.split())
            if n_words <= 6:
                return RouteDecision(
                    query=query,
                    query_type=QueryType.SINGLE_HOP,
                    confidence=0.6,
                    reason=f"no-hint short query ({n_words} words)",
                    suggested_operators=("direct_retrieve",),
                )
            return RouteDecision(
                query=query,
                query_type=QueryType.SINGLE_HOP,
                confidence=0.4,
                reason="no hint matched; default single-hop",
                suggested_operators=("direct_retrieve",),
            )

        # Tie-break order: BRIDGE > FAN_OUT > GLOBAL > BROWSE > SINGLE_HOP.
        # This reflects the cost-vs-payoff hierarchy (bridge is the most
        # specific signal; browse is the most expensive operator).
        priority = (
            QueryType.MULTI_HOP_BRIDGE,
            QueryType.FAN_OUT,
            QueryType.GLOBAL_SENSEMAKING,
            QueryType.OPEN_BROWSE,
        )
        chosen = next((qt for qt in priority if scores[qt] == max_score), QueryType.SINGLE_HOP)
        operators = _operators_for(chosen)
        # Confidence: 0.5 + 0.1 per matched hint, capped at 0.9.
        confidence = min(0.9, 0.5 + 0.1 * max_score)
        return RouteDecision(
            query=query,
            query_type=chosen,
            confidence=confidence,
            reason=f"matched {max_score} hint(s) for {chosen.value}",
            suggested_operators=operators,
        )


def _operators_for(qt: QueryType) -> tuple[str, ...]:
    return {
        QueryType.SINGLE_HOP: ("direct_retrieve", "chain_of_note"),
        QueryType.MULTI_HOP_BRIDGE: ("self_ask", "ircot", "chain_of_note", "hipporag"),
        QueryType.FAN_OUT: ("sub_question_fan_out", "chain_of_note"),
        QueryType.GLOBAL_SENSEMAKING: ("graphrag_community", "chain_of_note"),
        QueryType.OPEN_BROWSE: ("agentic_browse", "reason_in_documents"),
    }[qt]


@dataclass
class BELLERouter:
    """BELLE router — picks an operator chain per query type.

    Composes a :class:`Classifier` (rule-based by default) with an operator
    suggestion. Production wires an LM classifier; tests use the rule-based.
    """

    classifier: Classifier = field(default_factory=RuleBasedClassifier)
    confidence_threshold: float = 0.5

    def route(self, query: str) -> RouteDecision:
        decision = self.classifier.classify(query)
        if decision.confidence < self.confidence_threshold:
            # Low confidence — fall back to single-hop with a lower-cost operator.
            return RouteDecision(
                query=decision.query,
                query_type=QueryType.SINGLE_HOP,
                confidence=decision.confidence,
                reason=f"low confidence ({decision.confidence:.2f}); fell back from {decision.query_type.value}",
                suggested_operators=("direct_retrieve",),
            )
        return decision


__all__ = [
    "BELLERouter",
    "Classifier",
    "QueryType",
    "RouteDecision",
    "RuleBasedClassifier",
]
