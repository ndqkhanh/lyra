"""Tests for the Phase 1 Cryptographic Audit Engine."""
from __future__ import annotations

from datetime import datetime, timezone

from lyra_safety_governance.crypto_audit import ChainVerification, CryptoAuditEngine
from lyra_safety_governance.governance_engine import (
    ActionRequest,
    ActionType,
    Decision,
    GovernanceDecision,
    GovernanceLayer,
)

# ── Helpers ────────────────────────────────────────────────────────────

def _make_decision(
    action_type: ActionType = ActionType.READ_FILE,
    decision: Decision = Decision.ALLOW,
    agent_id: str = "agent-001",
    risk_score: float = 0.1,
) -> GovernanceDecision:
    return GovernanceDecision(
        action_request=ActionRequest(
            request_id="req-001",
            agent_id=agent_id,
            action_type=action_type,
            target="/tmp/test.txt",
            parameters={"path": "/tmp/test.txt"},
            context={"source": "test"},
        ),
        decision=decision,
        layer=GovernanceLayer.STATIC_RULES,
        reasoning="Test reasoning",
        risk_score=risk_score,
        timestamp=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )


class TestCryptoAuditEngine:
    """Core cryptographic audit engine behaviour."""

    def test_log_decision_returns_entry_id(self):
        engine = CryptoAuditEngine()
        entry_id = engine.log_decision(_make_decision())
        assert entry_id.startswith("caudit-")
        assert len(entry_id) > 10

    def test_chain_length_increases(self):
        engine = CryptoAuditEngine()
        assert engine.chain_length == 0
        engine.log_decision(_make_decision())
        assert engine.chain_length == 1
        engine.log_decision(_make_decision())
        assert engine.chain_length == 2

    def test_latest_hash_updates(self):
        engine = CryptoAuditEngine()
        initial = engine.latest_hash
        engine.log_decision(_make_decision())
        assert engine.latest_hash != initial

    def test_verify_empty_chain(self):
        engine = CryptoAuditEngine()
        result = engine.verify_chain()
        assert result.valid
        assert result.entries_checked == 0

    def test_verify_clean_chain(self):
        engine = CryptoAuditEngine()
        for _ in range(5):
            engine.log_decision(_make_decision())
        result = engine.verify_chain()
        assert result.valid
        assert result.entries_checked == 5
        assert len(result.tampered_entries) == 0

    def test_verify_detects_tampering(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision())
        engine.log_decision(_make_decision())

        engine._signed_entries[0]["decision"] = "tampered_value"
        result = engine.verify_chain()
        assert not result.valid

    def test_verify_detects_prev_hash_break(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision())
        engine.log_decision(_make_decision())

        engine._signed_entries[1]["prev_hash"] = "0" * 64
        result = engine.verify_chain()
        assert not result.valid

    def test_query_delegates_to_base_logger(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision(agent_id="agent-42"))
        from lyra_safety_governance.audit_logger import AuditQuery

        results = engine.query_audit_log(AuditQuery(agent_id="agent-42"))
        assert len(results) == 1
        assert results[0].agent_id == "agent-42"

    def test_get_agent_audit_trail(self):
        engine = CryptoAuditEngine()
        for _i in range(3):
            engine.log_decision(_make_decision(agent_id="agent-007"))
        trail = engine.get_agent_audit_trail("agent-007")
        assert len(trail) == 3

    def test_export_returns_json(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision())
        result = engine.export_audit_log("json")
        import json
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_export_chain_returns_tuple(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision())
        chain = engine.export_chain()
        assert isinstance(chain, tuple)
        assert len(chain) == 1

    def test_import_chain_restores_entries(self):
        engine1 = CryptoAuditEngine()
        engine1.log_decision(_make_decision())
        chain = engine1.export_chain()

        engine2 = CryptoAuditEngine()
        engine2.import_chain(chain)
        assert engine2.chain_length == 1

    def test_multiple_decisions_have_unique_hashes(self):
        engine = CryptoAuditEngine()
        ids = set()
        for _ in range(10):
            eid = engine.log_decision(_make_decision())
            ids.add(eid)
        assert len(ids) == 10

    def test_different_agents_produce_different_hashes(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision(agent_id="agent-a"))
        hash_a = engine.latest_hash
        engine.log_decision(_make_decision(agent_id="agent-b"))
        hash_b = engine.latest_hash
        assert hash_a != hash_b

    def test_compute_stats_works(self):
        engine = CryptoAuditEngine()
        engine.log_decision(_make_decision(decision=Decision.DENY))
        engine.log_decision(_make_decision(decision=Decision.ALLOW))
        stats = engine.compute_stats()
        assert stats.total_entries == 2
        assert stats.deny_rate == 0.5


class TestChainVerification:
    def test_valid_chain_properties(self):
        cv = ChainVerification(
            valid=True,
            entries_checked=10,
            tampered_entries=(),
            summary="All good.",
        )
        assert cv.valid
        assert cv.entries_checked == 10
        assert len(cv.tampered_entries) == 0
        assert "All good" in cv.summary

    def test_tampered_chain_properties(self):
        cv = ChainVerification(
            valid=False,
            entries_checked=10,
            tampered_entries=(3, 7),
            summary="Tampered!",
        )
        assert not cv.valid
        assert cv.tampered_entries == (3, 7)
