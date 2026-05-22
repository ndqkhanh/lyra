"""Tests for lyra-negotiate."""
from lyra_negotiate import NegotiationEngine, Preference, Offer


class TestNegotiationEngine:
    def test_utility_computation(self):
        ne = NegotiationEngine()
        ne.set_preferences([
            Preference(dimension="quality", weight=2.0, ideal=1.0),
            Preference(dimension="speed", weight=1.0, ideal=1.0),
        ])
        offer = Offer(terms={"quality": 0.8, "speed": 0.6})
        utility = ne.compute_utility(offer)
        assert utility > 0

    def test_negotiation_round(self):
        ne = NegotiationEngine()
        ne.set_preferences([Preference(dimension="x", weight=1.0, ideal=1.0)])
        agent = Offer(terms={"x": 0.8})
        human = Offer(terms={"x": 0.4})
        round_ = ne.negotiate(agent, human)
        assert round_.round_number == 1
        assert round_.agreement_score > 0

    def test_compromise(self):
        ne = NegotiationEngine()
        ne.set_preferences([Preference(dimension="x", weight=1.0, ideal=1.0)])
        round_ = ne.negotiate(Offer(terms={"x": 0.8}), Offer(terms={"x": 0.4}))
        comp = ne.find_compromise(round_)
        assert comp["x"] == 0.6
