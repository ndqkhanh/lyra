"""Tests for memory/encoder.py (Phase M2 — Encoder)."""
from __future__ import annotations

import pytest

from lyra_core.memory.encoder import LLMEncoder, RuleEncoder, Turn
from lyra_core.memory.schema import FragmentType, MemoryTier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _turn(user: str = "", assistant: str = "", tools: list | None = None) -> Turn:
    return Turn(
        user_message=user,
        assistant_response=assistant,
        tool_calls=tools or [],
    )


# ---------------------------------------------------------------------------
# RuleEncoder
# ---------------------------------------------------------------------------


def test_rule_encoder_decision_detected():
    enc = RuleEncoder()
    t = _turn(
        user="what db should we use?",
        assistant="We decided to use Clickhouse instead of Postgres because OLAP queries needed columnar storage.",
    )
    frags = enc.encode(t)
    assert len(frags) >= 1
    decision = next((f for f in frags if f.type is FragmentType.DECISION), None)
    assert decision is not None, "Expected a DECISION fragment"
    assert "rationale" in decision.structured
    assert decision.structured["rationale"]
    assert decision.tier is MemoryTier.T2_PROCEDURAL


def test_rule_encoder_preference_detected():
    enc = RuleEncoder()
    t = _turn(
        user="I always prefer async/await, not callbacks",
        assistant="Async/await is the standard approach here.",
    )
    frags = enc.encode(t)
    pref = next((f for f in frags if f.type is FragmentType.PREFERENCE), None)
    assert pref is not None
    assert pref.tier is MemoryTier.T3_USER
    assert pref.visibility == "private"


def test_rule_encoder_observation_detected():
    enc = RuleEncoder()
    t = _turn(
        assistant="I noticed the test is failing with a missing database mock error.",
    )
    frags = enc.encode(t)
    obs = next((f for f in frags if f.type is FragmentType.OBSERVATION), None)
    assert obs is not None
    assert obs.confidence == pytest.approx(0.5)
    assert obs.tier is MemoryTier.T1_SESSION


def test_rule_encoder_fact_fallback():
    enc = RuleEncoder()
    t = _turn(
        assistant="The authentication module is in src/auth.py and uses JWT for token validation.",
    )
    frags = enc.encode(t)
    assert len(frags) >= 1
    # Should produce a FACT (fallback path)
    fact = next((f for f in frags if f.type is FragmentType.FACT), None)
    assert fact is not None
    assert fact.tier is MemoryTier.T2_SEMANTIC


def test_rule_encoder_empty_turn_returns_nothing():
    enc = RuleEncoder()
    t = _turn(user="ok", assistant="")
    frags = enc.encode(t)
    assert frags == []


def test_rule_encoder_entities_extracted():
    enc = RuleEncoder()
    t = _turn(
        assistant="We decided to use `SQLAlchemy` instead of `psycopg2` because async support.",
    )
    frags = enc.encode(t)
    assert len(frags) >= 1
    entities = frags[0].entities
    assert any("SQLAlchemy" in e or "psycopg2" in e for e in entities)


def test_rule_encoder_content_truncated():
    enc = RuleEncoder()
    long_text = "We decided to use httpx. " + "x" * 500
    t = _turn(assistant=long_text)
    frags = enc.encode(t)
    for f in frags:
        assert len(f.content) <= 200


def test_rule_encoder_provenance_wired():
    enc = RuleEncoder()
    t = Turn(
        user_message="what db?",
        assistant_response="We decided to use Clickhouse because of speed.",
        agent_id="my-agent",
        session_id="sess-99",
    )
    frags = enc.encode(t)
    assert len(frags) >= 1
    assert frags[0].provenance.agent_id == "my-agent"
    assert frags[0].provenance.session_id == "sess-99"


def test_rule_encoder_decision_visibility_project():
    enc = RuleEncoder()
    t = _turn(assistant="We decided to adopt httpx over requests because async.")
    frags = enc.encode(t)
    decision = next((f for f in frags if f.type is FragmentType.DECISION), None)
    assert decision is not None
    assert decision.visibility == "project"


# ---------------------------------------------------------------------------
# LLMEncoder (no-LLM mode — uses RuleEncoder internally)
# ---------------------------------------------------------------------------


def test_llm_encoder_no_llm_falls_back_to_rules():
    enc = LLMEncoder(llm_fn=None)
    t = _turn(
        assistant="We decided to use httpx over requests because it supports async natively.",
    )
    frags = enc.encode(t)
    assert len(frags) >= 1


def test_llm_encoder_with_valid_json_output():
    import json

    def fake_llm(prompt: str) -> str:
        return json.dumps([
            {
                "type": "decision",
                "content": "use httpx over requests",
                "entities": ["httpx", "requests"],
                "confidence": 0.9,
                "structured": {"rationale": "async support"},
            }
        ])

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(user="which http client?", assistant="httpx is better")
    frags = enc.encode(t)
    assert len(frags) == 1
    f = frags[0]
    assert f.type is FragmentType.DECISION
    assert f.structured["rationale"] == "async support"
    assert f.confidence == pytest.approx(0.9)
    assert "httpx" in f.entities


def test_llm_encoder_decision_missing_rationale_gets_patched():
    import json

    def fake_llm(prompt: str) -> str:
        return json.dumps([
            {
                "type": "decision",
                "content": "use postgres",
                "structured": {},  # no rationale
            }
        ])

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(assistant="postgres is better")
    frags = enc.encode(t)
    # Should have patched rationale (content used as fallback)
    assert len(frags) == 1
    assert "rationale" in frags[0].structured


def test_llm_encoder_invalid_json_falls_back():
    def fake_llm(prompt: str) -> str:
        return "not json at all"

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(assistant="We decided to use httpx because async support.")
    frags = enc.encode(t)
    # falls back to RuleEncoder — should still produce something
    assert isinstance(frags, list)


def test_llm_encoder_empty_list_output():
    import json

    def fake_llm(prompt: str) -> str:
        return json.dumps([])

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(user="ok", assistant="got it")
    frags = enc.encode(t)
    assert frags == []


def test_llm_encoder_strips_markdown_fences():
    import json

    payload = json.dumps([{"type": "fact", "content": "auth in src/auth.py"}])

    def fake_llm(prompt: str) -> str:
        return f"```json\n{payload}\n```"

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(assistant="auth is in src/auth.py")
    frags = enc.encode(t)
    assert len(frags) == 1
    assert frags[0].type is FragmentType.FACT


def test_llm_encoder_observation_defaults_low_confidence():
    import json

    def fake_llm(prompt: str) -> str:
        return json.dumps([{"type": "observation", "content": "test seems flaky"}])

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(assistant="test seems flaky")
    frags = enc.encode(t)
    assert frags[0].confidence == pytest.approx(0.5)


def test_llm_encoder_unknown_type_skipped():
    import json

    def fake_llm(prompt: str) -> str:
        return json.dumps([{"type": "unknown_type", "content": "something"}])

    enc = LLMEncoder(llm_fn=fake_llm)
    t = _turn(assistant="something")
    frags = enc.encode(t)
    assert frags == []
