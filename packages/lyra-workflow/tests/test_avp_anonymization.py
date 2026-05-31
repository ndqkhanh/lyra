"""Tests for ReviewAnonymizer and RogueAgentMonitor (Run 17 additions).

Per SYNTHESIS.md §10.1 design decisions:
- Identity-Skews-Debate → anonymize claims before review
- Actor-Observer Asymmetry → shuffle critic assignments
- Preventing Rogue Agents → monitor confidence trajectories
"""

import pytest

from lyra_workflow.avp import (
    AdversarialVerifier,
    Claim,
    CriticVerdict,
    ReviewAnonymizer,
    RogueAgentMonitor,
    Verdict,
)


class TestReviewAnonymizer:
    """Tests for identity-marker stripping and claim anonymization."""

    def test_strips_agent_id_from_content(self) -> None:
        anonymizer = ReviewAnonymizer()
        claim = Claim(
            id="c1",
            content="agent_id: agent-7\nFixed auth middleware bug.",
            source="agent-7",
        )
        anon = anonymizer.anonymize(claim)
        assert "agent_id:" not in anon.content
        assert "Fixed auth middleware bug." in anon.content

    def test_strips_multiple_identity_markers(self) -> None:
        anonymizer = ReviewAnonymizer()
        claim = Claim(
            id="c2",
            content=(
                "created by: bob\n"
                "author: alice\n"
                "The database connection pool is properly configured.\n"
                "produced by: team-x"
            ),
            source="bob",
        )
        anon = anonymizer.anonymize(claim)
        assert "created by:" not in anon.content
        assert "author:" not in anon.content
        assert "produced by:" not in anon.content
        assert "database connection pool" in anon.content

    def test_preserves_claim_id(self) -> None:
        anonymizer = ReviewAnonymizer()
        claim = Claim(id="c42", content="test", source="agent-1")
        anon = anonymizer.anonymize(claim)
        assert anon.id == "c42"

    def test_deterministic_anonymized_source(self) -> None:
        """Same claim always gets the same anonymized source ID."""
        anonymizer = ReviewAnonymizer()
        claim = Claim(id="c3", content="test", source="agent-3")
        a1 = anonymizer.anonymize(claim)
        a2 = anonymizer.anonymize(claim)
        assert a1.source == a2.source

    def test_different_claims_get_different_sources(self) -> None:
        anonymizer = ReviewAnonymizer()
        c1 = Claim(id="c1", content="a", source="s1")
        c2 = Claim(id="c2", content="b", source="s1")
        a1 = anonymizer.anonymize(c1)
        a2 = anonymizer.anonymize(c2)
        assert a1.source != a2.source

    def test_shuffle_assignment_distributes_claims(self) -> None:
        anonymizer = ReviewAnonymizer()
        claims = [
            Claim(id=f"c{i}", content=f"claim {i}", source=f"agent-{i % 3}")
            for i in range(9)
        ]
        critic_ids = ["critic-a", "critic-b", "critic-c"]
        assignments = anonymizer.shuffle_assignment(claims, critic_ids)
        assert set(assignments.keys()) == set(critic_ids)
        total = sum(len(v) for v in assignments.values())
        assert total == len(claims)


class TestRogueAgentMonitor:
    """Tests for confidence-trajectory-based rogue agent detection."""

    def test_no_flag_on_stable_confidence(self) -> None:
        monitor = RogueAgentMonitor()
        for _ in range(5):
            flagged = monitor.record_and_check(
                "a1", Claim(id="x", content="test", severity="HIGH")
            )
            assert not flagged

    def test_flag_on_sudden_confidence_drop(self) -> None:
        monitor = RogueAgentMonitor()
        monitor.record_and_check("a2", Claim(id="x", content="t", severity="CRITICAL"))
        flagged = monitor.record_and_check(
            "a2", Claim(id="x", content="t", severity="INFO")
        )
        assert flagged  # 0.95 → 0.35 drop = 0.60 > 0.30 threshold

    def test_flag_on_sustained_low_confidence(self) -> None:
        monitor = RogueAgentMonitor()
        for _ in range(5):
            monitor.record_and_check(
                "a3", Claim(id="x", content="t", severity="INFO")
            )
        assert "a3" in monitor.flagged_agents

    def test_early_termination_tracking(self) -> None:
        monitor = RogueAgentMonitor()
        assert not monitor.record_early_termination("a4")
        assert not monitor.record_early_termination("a4")
        assert monitor.record_early_termination("a4")  # 3rd attempt → flagged

    def test_stats_include_tracked_agents(self) -> None:
        monitor = RogueAgentMonitor()
        monitor.record_and_check("a5", Claim(id="x", content="t", severity="MEDIUM"))
        stats = monitor.stats
        assert stats["agents_tracked"] == 1
        assert "a5" in stats["trajectories"]


class TestAdversarialVerifierAnonymization:
    """Integration tests for AVP with anonymization enabled."""

    def test_anonymization_default_on(self) -> None:
        av = AdversarialVerifier()
        assert av.anonymizer_enabled
        assert av.monitor_enabled

    def test_anonymization_can_be_disabled(self) -> None:
        av = AdversarialVerifier(anonymize=False, monitor_rogue_agents=False)
        assert not av.anonymizer_enabled
        assert not av.monitor_enabled

    def test_verify_returns_anonymized_flag(self) -> None:
        av = AdversarialVerifier()
        claim = Claim(id="c99", content="agent_id: agent-42 fixed something", source="agent-42")
        result = av.verify(claim, lambda c: [
            CriticVerdict("cr1", "anthropic", Verdict.ACCEPT, 0.9, "ok"),
            CriticVerdict("cr2", "deepseek", Verdict.ACCEPT, 0.85, "ok"),
            CriticVerdict("cr3", "openai", Verdict.ACCEPT, 0.8, "ok"),
        ], agent_id="agent-42")
        assert result["anonymized"] is True
        assert result["verified"] is True

    def test_verify_returns_rogue_flag(self) -> None:
        av = AdversarialVerifier()
        claim = Claim(id="c100", content="test claim", source="agent-99")
        result = av.verify(claim, lambda c: [
            CriticVerdict("cr1", "anthropic", Verdict.ACCEPT, 0.9, "ok"),
            CriticVerdict("cr2", "deepseek", Verdict.ACCEPT, 0.85, "ok"),
            CriticVerdict("cr3", "openai", Verdict.ACCEPT, 0.8, "ok"),
        ], agent_id="agent-99")
        assert result["rogue_flag"] is not None  # bool or None

    def test_anonymization_does_not_break_consensus(self) -> None:
        """Anonymization should be transparent to consensus logic."""
        av = AdversarialVerifier()
        claim = Claim(id="c101", content="created by: bob\nThe auth module is secure.", source="bob")
        result = av.verify(claim, lambda c: [
            CriticVerdict("cr1", "anthropic", Verdict.ACCEPT, 0.9, "ok"),
            CriticVerdict("cr2", "deepseek", Verdict.ACCEPT, 0.85, "ok"),
            CriticVerdict("cr3", "openai", Verdict.ACCEPT, 0.8, "ok"),
        ], agent_id="bob")
        assert result["consensus"] == "accept"
        assert result["confidence"] == pytest.approx(0.85)
