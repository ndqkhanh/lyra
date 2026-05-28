"""Tests for Hybrid Communication Router (Plan 29.2)."""

from lyra_core.teams.hybrid_router import (
    Channel,
    HybridCommunicationRouter,
    MessageCategory,
    RoutedMessage,
)


class TestHybridCommunicationRouter:
    def test_short_message_routed_to_text(self):
        router = HybridCommunicationRouter()
        result = router.route("short msg", "coordination")
        assert result.channel == Channel.TEXT
        assert result.message is not None
        assert result.message["content"] == "short msg"

    def test_alert_always_text(self):
        router = HybridCommunicationRouter()
        long_alert = "x" * 1000
        result = router.route(long_alert, "alert")
        assert result.channel == Channel.TEXT

    def test_question_always_text(self):
        router = HybridCommunicationRouter()
        long_question = "x" * 1000
        result = router.route(long_question, "question")
        assert result.channel == Channel.TEXT

    def test_plan_approval_always_text(self):
        router = HybridCommunicationRouter()
        long_plan = "x" * 1000
        result = router.route(long_plan, "plan_approval")
        assert result.channel == Channel.TEXT

    def test_large_finding_routed_to_latent(self):
        router = HybridCommunicationRouter()
        large_finding = "x" * 600
        result = router.route(large_finding, "finding")
        assert result.channel == Channel.LATENT
        assert result.latent_vector is not None
        assert len(result.latent_vector) == 16

    def test_large_context_share_routed_to_latent(self):
        router = HybridCommunicationRouter()
        large_context = "y" * 800
        result = router.route(large_context, "context_share")
        assert result.channel == Channel.LATENT

    def test_latent_saves_tokens(self):
        router = HybridCommunicationRouter()
        large = "data " * 500
        result = router.route(large, "finding")
        assert result.channel == Channel.LATENT
        assert result.token_savings > 0.0

    def test_coordination_goes_text_even_if_long(self):
        router = HybridCommunicationRouter()
        long_coord = "x" * 600
        result = router.route(long_coord, "coordination")
        assert result.channel == Channel.TEXT

    def test_routing_stats_counts(self):
        router = HybridCommunicationRouter()
        router.route("short", "coordination")
        router.route("x" * 600, "finding")
        router.route("x" * 600, "context_share")

        stats = router.routing_stats
        assert stats["text_routes"] == 1
        assert stats["latent_routes"] == 2
        assert stats["total_routes"] == 3

    def test_custom_latent_compressor(self):
        class FakeCompressor:
            def encode(self, text):
                return [0.1, 0.2, 0.3]

        router = HybridCommunicationRouter(latent_compressor=FakeCompressor())
        result = router.route("x" * 600, "finding")
        assert result.latent_vector == [0.1, 0.2, 0.3]

    def test_latent_fallback_on_error(self):
        class BrokenCompressor:
            def encode(self, text):
                raise RuntimeError("boom")

        router = HybridCommunicationRouter(latent_compressor=BrokenCompressor())
        result = router.route("x" * 600, "finding")
        assert result.channel == Channel.TEXT

    def test_clear_log(self):
        router = HybridCommunicationRouter()
        router.route("a", "coordination")
        router.route("b", "coordination")
        assert router.routing_stats["total_routes"] == 2
        router.clear_log()
        assert router.routing_stats["total_routes"] == 0

    def test_message_category_enum(self):
        assert MessageCategory.COORDINATION == "coordination"
        assert MessageCategory.FINDING == "finding"
        assert MessageCategory.CONTEXT_SHARE == "context_share"
        assert MessageCategory.ALERT == "alert"
        assert MessageCategory.QUESTION == "question"
        assert MessageCategory.PLAN_APPROVAL == "plan_approval"

    def test_channel_enum(self):
        assert Channel.TEXT == "text"
        assert Channel.LATENT == "latent"

    def test_routed_message_defaults(self):
        msg = RoutedMessage(channel=Channel.TEXT)
        assert msg.latent_vector is None
        assert msg.token_savings == 0.0

    def test_metadata_passed_through(self):
        router = HybridCommunicationRouter()
        result = router.route("hello", "coordination", metadata={"source": "agent-1"})
        assert result.message is not None
        assert result.message["metadata"]["source"] == "agent-1"

    def test_below_threshold_stays_text(self):
        router = HybridCommunicationRouter()
        borderline = "x" * 499
        result = router.route(borderline, "finding")
        assert result.channel == Channel.TEXT
