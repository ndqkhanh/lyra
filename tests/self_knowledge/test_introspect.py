"""Tests for self-knowledge / introspection module."""
import pytest
from lyra.self_knowledge.introspect import IntrospectionEngine


class TestIntrospectionEngine:
    def test_initialization(self):
        engine = IntrospectionEngine()
        assert engine is not None

    def test_assess_capability(self):
        engine = IntrospectionEngine()
        result = engine.assess("code_generation")
        assert isinstance(result, dict)
        assert "confidence" in result or "level" in result

    def test_uncertainty_signal(self):
        engine = IntrospectionEngine()
        signal = engine.uncertainty_signal("What is the meaning of life?")
        assert isinstance(signal, float)
        assert 0 <= signal <= 1

    def test_should_abstain_low_confidence(self):
        engine = IntrospectionEngine()
        result = engine.should_abstain("complex quantum physics problem", threshold=0.95)
        assert isinstance(result, bool)

    def test_known_unknowns(self):
        engine = IntrospectionEngine()
        unknowns = engine.known_unknowns()
        assert isinstance(unknowns, list)
