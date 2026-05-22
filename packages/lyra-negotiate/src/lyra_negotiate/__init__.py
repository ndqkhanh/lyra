"""Negotiation Engine — multi-round bargaining, trade-off optimization, disagreement resolution.

Enables Lyra to negotiate with humans over resources, priorities, and decisions.
Models preferences, finds Pareto-optimal trade-offs, and resolves disagreements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "Preference",
    "Offer",
    "NegotiationRound",
    "NegotiationEngine",
]


@dataclass
class Preference:
    dimension: str
    weight: float = 1.0
    ideal: float = 1.0


@dataclass
class Offer:
    terms: dict[str, float]
    utility: float = 0.0


@dataclass
class NegotiationRound:
    round_number: int
    agent_offer: Offer
    human_offer: Offer
    agreement_score: float = 0.0


class NegotiationEngine:
    """Multi-round negotiation with utility-based agreement finding."""

    def __init__(self):
        self.preferences: list[Preference] = []
        self.rounds: list[NegotiationRound] = []
        self._round = 0

    def set_preferences(self, preferences: list[Preference]) -> None:
        self.preferences = preferences

    def compute_utility(self, offer: Offer) -> float:
        utility = 0.0
        total_weight = sum(p.weight for p in self.preferences) or 1.0
        for pref in self.preferences:
            value = offer.terms.get(pref.dimension, 0.0)
            utility += pref.weight * (value / max(pref.ideal, 0.01))
        return utility / total_weight

    def generate_offer(self, constraints: dict[str, float]) -> Offer:
        self._round += 1
        terms = {}
        for pref in self.preferences:
            terms[pref.dimension] = min(pref.ideal, constraints.get(pref.dimension, pref.ideal))
        offer = Offer(terms=terms)
        offer.utility = self.compute_utility(offer)
        return offer

    def negotiate(self, agent_offer: Offer, human_offer: Offer) -> NegotiationRound:
        self._round += 1
        agent_offer.utility = self.compute_utility(agent_offer)
        human_offer.utility = self.compute_utility(human_offer)
        agreement = 1.0 - abs(agent_offer.utility - human_offer.utility)
        round_ = NegotiationRound(
            round_number=self._round,
            agent_offer=agent_offer,
            human_offer=human_offer,
            agreement_score=agreement,
        )
        self.rounds.append(round_)
        return round_

    def find_compromise(self, round_: NegotiationRound) -> dict[str, float]:
        compromise = {}
        for key in round_.agent_offer.terms:
            compromise[key] = (
                round_.agent_offer.terms[key] + round_.human_offer.terms[key]
            ) / 2
        return compromise

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "rounds": len(self.rounds),
            "active_preferences": len(self.preferences),
        }
