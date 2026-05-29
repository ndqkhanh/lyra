"""Tests for RecursiveLink — latent-space inter-agent communication."""

import pytest
from lyra_agent_swarm.recursive_link import (
    LatentMessage,
    LatentState,
    LinkMode,
    LinkStatus,
    RecursiveLink,
)


class TestLinkMode:
    def test_mode_values(self):
        assert LinkMode.TEXT.value == "text"
        assert LinkMode.LATENT.value == "latent"
        assert LinkMode.HYBRID.value == "hybrid"


class TestLinkStatus:
    def test_status_values(self):
        assert LinkStatus.IDLE.value == "idle"
        assert LinkStatus.CONNECTED.value == "connected"
        assert LinkStatus.DEGRADED.value == "degraded"
        assert LinkStatus.DISCONNECTED.value == "disconnected"


class TestLatentState:
    def test_compress_produces_vector(self):
        state = LatentState.compress("agent-1", "This is a test message for compression")
        assert state.source_agent == "agent-1"
        assert len(state.compressed_vector) == 128
        assert 0.0 <= state.compression_ratio <= 1.0

    def test_compress_small_text(self):
        state = LatentState.compress("a", "hi")
        assert state.dimension == 128

    def test_cosine_similarity_identical(self):
        s1 = LatentState.compress("a", "hello world")
        similarity = s1.cosine_similarity(s1)
        assert pytest.approx(similarity, abs=0.001) == 1.0

    def test_cosine_similarity_different_dimensions(self):
        s1 = LatentState.compress("a", "hello", target_dimension=64)
        s2 = LatentState.compress("b", "hello", target_dimension=128)
        assert s1.cosine_similarity(s2) == 0.0

    def test_immutable(self):
        state = LatentState.compress("a", "test")
        with pytest.raises(Exception):
            state.compression_ratio = 0.5


class TestRecursiveLink:
    def test_register_agent(self):
        link = RecursiveLink()
        link.register_agent("orchestrator")
        assert link.stats()["registered_agents"] == 1

    def test_establish_link(self):
        link = RecursiveLink()
        ctx = link.establish("orchestrator", "specialist")
        assert ctx.agent_a == "orchestrator"
        assert ctx.agent_b == "specialist"
        assert ctx.mode == LinkMode.HYBRID
        assert ctx.status == LinkStatus.CONNECTED
        assert link.active_links == 1

    def test_establish_idempotent(self):
        link = RecursiveLink()
        ctx1 = link.establish("a", "b")
        ctx2 = link.establish("a", "b")
        assert ctx1.link_id == ctx2.link_id

    def test_send_message(self):
        link = RecursiveLink()
        link.establish("orchestrator", "specialist")
        msg = link.send("orchestrator", "specialist", "Run analysis on file X")
        assert isinstance(msg, LatentMessage)
        assert msg.sender == "orchestrator"
        assert msg.receiver == "specialist"

    def test_send_auto_establishes_link(self):
        link = RecursiveLink()
        link.send("a", "b", "test message here")
        assert link.active_links >= 1

    def test_receive_message(self):
        link = RecursiveLink()
        msg = link.send("a", "b", "test message")
        received = link.receive(msg.message_id)
        assert received is not None
        assert received.message_id == msg.message_id
        assert received.text_fallback == "test message"

    def test_check_alignment(self):
        link = RecursiveLink()
        link.establish("a", "b")
        alignment = link.check_alignment("a", "b")
        assert alignment > 0.0

    def test_degrade_to_text(self):
        link = RecursiveLink()
        link.establish("a", "b")
        degraded = link.degrade_to_text("a", "b")
        assert degraded is not None
        assert degraded.mode == LinkMode.TEXT
        assert degraded.status == LinkStatus.DEGRADED

    def test_degrade_nonexistent(self):
        link = RecursiveLink()
        assert link.degrade_to_text("x", "y") is None

    def test_token_savings_tracked(self):
        link = RecursiveLink()
        # Need a message longer than 128 tokens for compression to save tokens
        long_msg = " ".join(["word"] * 200)
        link.send("a", "b", long_msg)
        assert link.total_tokens_saved > 0

    def test_exchange_count_increments(self):
        link = RecursiveLink()
        link.send("a", "b", "msg 1")
        link.send("a", "b", "msg 2")
        link.send("b", "a", "msg 3")
        assert link.total_exchanges == 3

    def test_stats(self):
        link = RecursiveLink()
        link.establish("a", "b")
        link.establish("c", "d")
        stats = link.stats()
        assert stats["active_links"] == 2
        assert stats["total_links"] == 2
        assert "registered_agents" in stats

    def test_link_key_order_independent(self):
        link = RecursiveLink()
        link.establish("a", "b")
        ctx1 = link.get_context("a", "b")
        ctx2 = link.get_context("b", "a")
        assert ctx1 is not None
        assert ctx2 is not None
        assert ctx1.link_id == ctx2.link_id

    def test_hybrid_mode_message_has_fallback(self):
        link = RecursiveLink()
        msg = link.send("a", "b", "critical operation", mode=LinkMode.HYBRID)
        assert msg.text_fallback == "critical operation"
        assert msg.mode == LinkMode.HYBRID
