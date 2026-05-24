"""Tests for harness_core.routing — BELLE-style query-type router."""
from __future__ import annotations

import pytest

from harness_core.routing import (
    BELLERouter,
    QueryType,
    RouteDecision,
    RuleBasedClassifier,
)


class TestRouteDecision:
    def test_valid(self):
        d = RouteDecision(query="q", query_type=QueryType.SINGLE_HOP, confidence=0.5, reason="r")
        assert d.confidence == 0.5

    def test_invalid_confidence(self):
        with pytest.raises(ValueError):
            RouteDecision(query="q", query_type=QueryType.SINGLE_HOP, confidence=1.5, reason="r")
        with pytest.raises(ValueError):
            RouteDecision(query="q", query_type=QueryType.SINGLE_HOP, confidence=-0.1, reason="r")

    def test_frozen(self):
        d = RouteDecision(query="q", query_type=QueryType.SINGLE_HOP, confidence=0.5, reason="r")
        with pytest.raises(Exception):
            d.confidence = 0.8  # type: ignore[misc]


class TestRuleBasedClassifier:
    def test_empty_query(self):
        d = RuleBasedClassifier().classify("")
        assert d.query_type == QueryType.SINGLE_HOP
        assert d.confidence == 0.0

    def test_short_factual_single_hop(self):
        d = RuleBasedClassifier().classify("paris france capital")
        assert d.query_type == QueryType.SINGLE_HOP

    def test_bridge_pattern_who_directed(self):
        d = RuleBasedClassifier().classify("who directed Casablanca")
        assert d.query_type == QueryType.MULTI_HOP_BRIDGE
        assert "self_ask" in d.suggested_operators
        assert "ircot" in d.suggested_operators

    def test_bridge_pattern_spouse_of(self):
        d = RuleBasedClassifier().classify("spouse of the director of Casablanca")
        assert d.query_type == QueryType.MULTI_HOP_BRIDGE

    def test_fan_out_list_all(self):
        d = RuleBasedClassifier().classify("list all G20 countries by population")
        assert d.query_type == QueryType.FAN_OUT
        assert "sub_question_fan_out" in d.suggested_operators

    def test_fan_out_compare(self):
        d = RuleBasedClassifier().classify("compare Python vs Rust performance")
        assert d.query_type == QueryType.FAN_OUT

    def test_global_sensemaking(self):
        d = RuleBasedClassifier().classify("summarize the main themes across the corpus")
        assert d.query_type == QueryType.GLOBAL_SENSEMAKING
        assert "graphrag_community" in d.suggested_operators

    def test_global_state_of_field(self):
        d = RuleBasedClassifier().classify("what is the state of the art in robotics")
        assert d.query_type == QueryType.GLOBAL_SENSEMAKING

    def test_open_browse_latest(self):
        d = RuleBasedClassifier().classify("latest news on the federal reserve")
        assert d.query_type == QueryType.OPEN_BROWSE
        assert "agentic_browse" in d.suggested_operators

    def test_open_browse_search_web(self):
        d = RuleBasedClassifier().classify("search the web for SWE-Bench leaderboard")
        assert d.query_type == QueryType.OPEN_BROWSE

    def test_priority_bridge_over_fanout(self):
        # Both 'who directed' (bridge) and 'all' (fan-out) match; bridge wins.
        d = RuleBasedClassifier().classify("who directed all of these movies")
        assert d.query_type == QueryType.MULTI_HOP_BRIDGE


class TestBELLERouter:
    def test_high_confidence_passes_through(self):
        router = BELLERouter(confidence_threshold=0.5)
        d = router.route("who directed Casablanca")
        assert d.query_type == QueryType.MULTI_HOP_BRIDGE
        assert d.confidence >= 0.5

    def test_low_confidence_falls_back_to_single_hop(self):
        # A high threshold forces fall-back even on positive matches.
        router = BELLERouter(confidence_threshold=0.99)
        d = router.route("who directed Casablanca")
        assert d.query_type == QueryType.SINGLE_HOP
        assert "fell back" in d.reason

    def test_default_classifier_is_rule_based(self):
        router = BELLERouter()
        assert isinstance(router.classifier, RuleBasedClassifier)

    def test_custom_classifier(self):
        from dataclasses import dataclass

        @dataclass
        class StubClassifier:
            name: str = "stub"

            def classify(self, query):
                return RouteDecision(
                    query=query,
                    query_type=QueryType.OPEN_BROWSE,
                    confidence=0.95,
                    reason="stub",
                    suggested_operators=("agentic_browse",),
                )

        router = BELLERouter(classifier=StubClassifier())
        d = router.route("anything")
        assert d.query_type == QueryType.OPEN_BROWSE


class TestSuggestedOperators:
    def test_all_query_types_have_operators(self):
        for qt in QueryType:
            classifier = RuleBasedClassifier()
            # Trigger each branch with a synthetic query.
            d = classifier.classify({
                QueryType.SINGLE_HOP: "paris",
                QueryType.MULTI_HOP_BRIDGE: "who directed Casablanca",
                QueryType.FAN_OUT: "list all countries",
                QueryType.GLOBAL_SENSEMAKING: "summarize the main themes",
                QueryType.OPEN_BROWSE: "search the web today",
            }[qt])
            assert d.suggested_operators, f"no operators for {qt}"
