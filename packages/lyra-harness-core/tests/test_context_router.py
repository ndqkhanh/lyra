"""Tests for the Context Router (BREAKTHROUGH primitive)."""
from __future__ import annotations

import pytest

from lyra_harness_core.context_router import (
    ContextDecision,
    ContextRoute,
    ContextRouter,
    ContextSignal,
    RuleBasedContextClassifier,
)


# ---------------------------------------------------------------------------
# ContextRoute
# ---------------------------------------------------------------------------


class TestContextRoute:
    def test_enum_values(self):
        assert ContextRoute.MEMORY_RETRIEVAL.value == "memory_retrieval"
        assert ContextRoute.WORKING_MEMORY.value == "working_memory"
        assert ContextRoute.LONG_TERM_STORE.value == "long_term_store"
        assert ContextRoute.COMPACTION.value == "compaction"
        assert ContextRoute.DISCLOSURE.value == "disclosure"
        assert ContextRoute.DIRECT_PASS.value == "direct_pass"

    def test_six_routes(self):
        assert len(ContextRoute) == 6


# ---------------------------------------------------------------------------
# ContextDecision
# ---------------------------------------------------------------------------


class TestContextDecision:
    def test_defaults(self):
        cd = ContextDecision(
            signal="test", route=ContextRoute.DIRECT_PASS, confidence=0.5, reason="ok"
        )
        assert cd.signal == "test"
        assert cd.route == ContextRoute.DIRECT_PASS
        assert cd.confidence == 0.5
        assert cd.strategy_hints == ()

    def test_with_hints(self):
        cd = ContextDecision(
            signal="q",
            route=ContextRoute.MEMORY_RETRIEVAL,
            confidence=0.8,
            reason="matched",
            strategy_hints=("three_layer", "bm25"),
        )
        assert cd.strategy_hints == ("three_layer", "bm25")

    def test_confidence_clamped(self):
        with pytest.raises(ValueError):
            ContextDecision(signal="x", route=ContextRoute.DIRECT_PASS, confidence=1.5, reason="bad")

    def test_confidence_negative_raises(self):
        with pytest.raises(ValueError):
            ContextDecision(signal="x", route=ContextRoute.DIRECT_PASS, confidence=-0.1, reason="bad")

    def test_confidence_zero_is_valid(self):
        cd = ContextDecision(signal="x", route=ContextRoute.DIRECT_PASS, confidence=0.0, reason="none")
        assert cd.confidence == 0.0

    def test_confidence_one_is_valid(self):
        cd = ContextDecision(signal="x", route=ContextRoute.DIRECT_PASS, confidence=1.0, reason="full")
        assert cd.confidence == 1.0

    def test_frozen(self):
        cd = ContextDecision(signal="x", route=ContextRoute.DIRECT_PASS, confidence=0.5, reason="r")
        with pytest.raises(Exception):
            cd.confidence = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContextSignal
# ---------------------------------------------------------------------------


class TestContextSignal:
    def test_defaults(self):
        sig = ContextSignal(content="hello")
        assert sig.content == "hello"
        assert sig.urgency == 0.0
        assert sig.source == ""
        assert sig.tags == ()

    def test_token_count_auto_estimated(self):
        sig = ContextSignal(content="hello world " * 100)  # ~1200 chars → ~300 tokens
        assert sig.token_count > 0

    def test_token_count_explicit(self):
        sig = ContextSignal(content="x", token_count=42)
        assert sig.token_count == 42

    def test_urgency_default_zero(self):
        sig = ContextSignal(content="test")
        assert sig.urgency == 0.0

    def test_urgency_out_of_range_raises(self):
        with pytest.raises(ValueError):
            ContextSignal(content="x", urgency=2.0)

    def test_urgency_negative_raises(self):
        with pytest.raises(ValueError):
            ContextSignal(content="x", urgency=-0.5)

    def test_with_tags(self):
        sig = ContextSignal(content="test", tags=("memory", "retrieval"))
        assert sig.tags == ("memory", "retrieval")

    def test_with_source(self):
        sig = ContextSignal(content="x", source="claude-opus")
        assert sig.source == "claude-opus"


# ---------------------------------------------------------------------------
# RuleBasedContextClassifier
# ---------------------------------------------------------------------------


class TestRuleBasedContextClassifier:
    @pytest.fixture
    def classifier(self):
        return RuleBasedContextClassifier()

    def test_empty_signal_direct_pass(self, classifier):
        decision = classifier.classify(ContextSignal(content=""))
        assert decision.route == ContextRoute.DIRECT_PASS
        assert decision.confidence == 0.0

    def test_whitespace_only_direct_pass(self, classifier):
        decision = classifier.classify(ContextSignal(content="   \n\t  "))
        assert decision.route == ContextRoute.DIRECT_PASS

    def test_retrieval_hint_recall(self, classifier):
        decision = classifier.classify(ContextSignal(content="recall what we discussed about Python"))
        assert decision.route == ContextRoute.MEMORY_RETRIEVAL

    def test_retrieval_hint_find(self, classifier):
        decision = classifier.classify(ContextSignal(content="find the last time we talked about deployment"))
        assert decision.route == ContextRoute.MEMORY_RETRIEVAL

    def test_retrieval_hint_question(self, classifier):
        decision = classifier.classify(ContextSignal(content="what is the capital of France?"))
        assert decision.route == ContextRoute.MEMORY_RETRIEVAL

    def test_retrieval_hint_previous(self, classifier):
        decision = classifier.classify(ContextSignal(content="previous conversation about API design"))
        assert decision.route == ContextRoute.MEMORY_RETRIEVAL

    def test_store_hint_save(self, classifier):
        decision = classifier.classify(ContextSignal(content="save this important fact about memory"))
        assert decision.route == ContextRoute.LONG_TERM_STORE

    def test_store_hint_learned(self, classifier):
        decision = classifier.classify(ContextSignal(content="learned that Python 3.12 improved error messages"))
        assert decision.route == ContextRoute.LONG_TERM_STORE

    def test_store_hint_critical(self, classifier):
        # "critical ... fact" triggers _STORE_HINTS without hitting retrieval hints
        decision = classifier.classify(ContextSignal(content="critical fact about the system architecture"))
        assert decision.route == ContextRoute.LONG_TERM_STORE

    def test_compact_hint_summarize(self, classifier):
        decision = classifier.classify(ContextSignal(content="summarize the following conversation"))
        assert decision.route == ContextRoute.COMPACTION

    def test_compact_hint_too_long(self, classifier):
        decision = classifier.classify(ContextSignal(content="this is way too long and verbose"))
        assert decision.route == ContextRoute.COMPACTION

    def test_compact_large_content(self, classifier):
        long_text = "word " * 1500  # ~6000 chars → ~1500 tokens
        decision = classifier.classify(ContextSignal(content=long_text))
        # large content triggers compaction hint
        assert decision.route == ContextRoute.COMPACTION

    def test_disclosure_hint_progressive(self, classifier):
        decision = classifier.classify(ContextSignal(content="explain this progressively step by step"))
        assert decision.route == ContextRoute.DISCLOSURE

    def test_disclosure_hint_overview(self, classifier):
        decision = classifier.classify(ContextSignal(content="give me a high-level overview first"))
        assert decision.route == ContextRoute.DISCLOSURE

    def test_urgency_triggers_working_memory(self, classifier):
        decision = classifier.classify(ContextSignal(content="x", urgency=0.9))
        assert decision.route == ContextRoute.WORKING_MEMORY

    def test_short_content_defaults_working_memory(self, classifier):
        decision = classifier.classify(ContextSignal(content="a short message"))
        assert decision.route == ContextRoute.WORKING_MEMORY

    def test_long_content_defaults_compaction(self, classifier):
        long_msg = "the quick brown fox jumps over the lazy dog " * 30  # > 50 words
        decision = classifier.classify(ContextSignal(content=long_msg, token_count=100))
        assert decision.route == ContextRoute.COMPACTION

    def test_name_property(self, classifier):
        assert "rule-based" in classifier.name

    def test_confidence_in_range(self, classifier):
        decision = classifier.classify(ContextSignal(content="recall the memory system design"))
        assert 0.0 <= decision.confidence <= 1.0

    def test_strategy_hints_present(self, classifier):
        decision = classifier.classify(ContextSignal(content="find the user preferences"))
        assert len(decision.strategy_hints) > 0
        assert "three_layer" in decision.strategy_hints


# ---------------------------------------------------------------------------
# ContextRouter (composed)
# ---------------------------------------------------------------------------


class TestContextRouter:
    @pytest.fixture
    def router(self):
        return ContextRouter()

    def test_route_string_input(self, router):
        decision = router.route("find the last deployment log")
        assert decision.route == ContextRoute.MEMORY_RETRIEVAL

    def test_route_signal_input(self, router):
        sig = ContextSignal(content="summarize this document", token_count=100)
        decision = router.route(sig)
        assert decision.route == ContextRoute.COMPACTION

    def test_low_confidence_falls_back(self, router):
        router.confidence_threshold = 0.95
        decision = router.route("find x")
        # Rule-based classifier confidence for single-word retrieval may be low
        assert decision.route in (ContextRoute.MEMORY_RETRIEVAL, ContextRoute.DIRECT_PASS)

    def test_route_batch(self, router):
        signals = [
            ContextSignal(content="find the user database schema"),
            ContextSignal(content="save the API key rotation policy"),
            ContextSignal(content="summarize the last 10 messages"),
        ]
        decisions = router.route_batch(signals)
        assert len(decisions) == 3
        assert decisions[0].route == ContextRoute.MEMORY_RETRIEVAL
        assert decisions[1].route == ContextRoute.LONG_TERM_STORE
        assert decisions[2].route == ContextRoute.COMPACTION

    def test_empty_batch(self, router):
        decisions = router.route_batch([])
        assert decisions == []

    def test_confidence_threshold_default(self, router):
        assert router.confidence_threshold == 0.3

    def test_custom_classifier(self):
        class StubClassifier:
            name = "stub"

            def classify(self, signal):
                return ContextDecision(
                    signal=signal.content,
                    route=ContextRoute.LONG_TERM_STORE,
                    confidence=1.0,
                    reason="always store",
                )

        router = ContextRouter(classifier=StubClassifier())  # type: ignore[arg-type]
        decision = router.route("hello world")
        assert decision.route == ContextRoute.LONG_TERM_STORE
        assert decision.confidence == 1.0

    def test_urgency_hot_path(self, router):
        sig = ContextSignal(content="critical alert: disk full", urgency=0.95)
        decision = router.route(sig)
        assert decision.route == ContextRoute.WORKING_MEMORY

    def test_disclosure_for_very_large_content(self, router):
        # ~35000 chars → ~8750 tokens > DISCLOSURE_THRESHOLD (8000)
        huge_text = "data " * 7000
        decision = router.route(ContextSignal(content=huge_text))
        assert decision.route == ContextRoute.DISCLOSURE
