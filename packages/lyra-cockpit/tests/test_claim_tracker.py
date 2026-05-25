"""Tests for the claim tracker module."""

from __future__ import annotations

import pytest

from lyra_cockpit.claim_tracker import (
    ClaimTimeline,
    ClaimTracker,
    TrackedClaim,
)
from lyra_cockpit.exceptions import CockpitError


class TestTrackedClaim:
    def test_creation(self) -> None:
        claim = TrackedClaim(
            claim_id="claim-001",
            text="The model achieves 95% accuracy",
            source="evaluation",
            status="registered",
            verification_rounds=0,
            last_updated=1000.0,
        )
        assert claim.claim_id == "claim-001"
        assert claim.text == "The model achieves 95% accuracy"
        assert claim.source == "evaluation"
        assert claim.status == "registered"

    def test_frozen(self) -> None:
        claim = TrackedClaim("c1", "text", "src", "registered", 0, 0.0)
        with pytest.raises(AttributeError):
            claim.status = "verified"  # type: ignore[misc]


class TestClaimTimeline:
    def test_creation(self) -> None:
        claim = TrackedClaim("c1", "text", "src", "registered", 0, 0.0)
        timeline = ClaimTimeline(
            claim=claim,
            events=((1000.0, "Claim registered"), (1005.0, "Status changed to: verifying")),
        )
        assert timeline.claim.claim_id == "c1"
        assert len(timeline.events) == 2

    def test_empty_events(self) -> None:
        claim = TrackedClaim("c1", "text", "src", "registered", 0, 0.0)
        timeline = ClaimTimeline(claim=claim, events=())
        assert timeline.events == ()


class TestClaimTracker:
    @pytest.mark.asyncio
    async def test_register_claim(self) -> None:
        tracker = ClaimTracker()
        claim_id = await tracker.register_claim("Model is 95% accurate", "test_runner")
        assert claim_id.startswith("claim-")
        assert claim_id in tracker._claims

    @pytest.mark.asyncio
    async def test_register_empty_text_raises(self) -> None:
        tracker = ClaimTracker()
        with pytest.raises(CockpitError, match="cannot be empty"):
            await tracker.register_claim("", "source")

    @pytest.mark.asyncio
    async def test_register_empty_source_raises(self) -> None:
        tracker = ClaimTracker()
        with pytest.raises(CockpitError, match="cannot be empty"):
            await tracker.register_claim("text", "")

    @pytest.mark.asyncio
    async def test_register_whitespace_text_raises(self) -> None:
        tracker = ClaimTracker()
        with pytest.raises(CockpitError, match="cannot be empty"):
            await tracker.register_claim("   ", "source")

    @pytest.mark.asyncio
    async def test_update_status(self) -> None:
        tracker = ClaimTracker()
        claim_id = await tracker.register_claim("Claim text", "source")
        await tracker.update_status(claim_id, "verifying")
        assert tracker._claims[claim_id].status == "verifying"

    @pytest.mark.asyncio
    async def test_update_status_unknown_raises(self) -> None:
        tracker = ClaimTracker()
        with pytest.raises(CockpitError, match="Unknown claim"):
            await tracker.update_status("nonexistent", "verified")

    @pytest.mark.asyncio
    async def test_update_status_increments_rounds_on_verified(self) -> None:
        tracker = ClaimTracker()
        claim_id = await tracker.register_claim("Claim text", "source")
        await tracker.update_status(claim_id, "verifying")
        await tracker.update_status(claim_id, "verified")
        assert tracker._claims[claim_id].verification_rounds == 1
        assert tracker._claims[claim_id].status == "verified"

    @pytest.mark.asyncio
    async def test_update_status_increments_rounds_on_disputed(self) -> None:
        tracker = ClaimTracker()
        claim_id = await tracker.register_claim("Claim text", "source")
        await tracker.update_status(claim_id, "disputed")
        assert tracker._claims[claim_id].verification_rounds == 1

    @pytest.mark.asyncio
    async def test_get_timeline(self) -> None:
        tracker = ClaimTracker()
        claim_id = await tracker.register_claim("Timeline test", "source")
        timeline = await tracker.get_timeline(claim_id)
        assert timeline.claim.claim_id == claim_id
        assert len(timeline.events) == 1
        assert timeline.events[0][1] == "Claim registered"

    @pytest.mark.asyncio
    async def test_get_timeline_unknown_raises(self) -> None:
        tracker = ClaimTracker()
        with pytest.raises(CockpitError, match="Unknown claim"):
            await tracker.get_timeline("nonexistent")

    @pytest.mark.asyncio
    async def test_get_pending_empty(self) -> None:
        tracker = ClaimTracker()
        pending = await tracker.get_pending()
        assert pending == ()

    @pytest.mark.asyncio
    async def test_get_pending(self) -> None:
        tracker = ClaimTracker()
        c1 = await tracker.register_claim("Claim 1", "src1")
        c2 = await tracker.register_claim("Claim 2", "src2")
        await tracker.update_status(c2, "verified")
        pending = await tracker.get_pending()
        assert len(pending) == 1
        assert pending[0].claim_id == c1

    @pytest.mark.asyncio
    async def test_get_statistics_empty(self) -> None:
        tracker = ClaimTracker()
        stats = await tracker.get_statistics()
        assert stats["total"] == 0
        assert stats["avg_verification_rounds"] == 0.0

    @pytest.mark.asyncio
    async def test_get_statistics(self) -> None:
        tracker = ClaimTracker()
        await tracker.register_claim("Claim 1", "src1")
        c2 = await tracker.register_claim("Claim 2", "src2")
        await tracker.update_status(c2, "verified")
        stats = await tracker.get_statistics()
        assert stats["total"] == 2
        assert stats["registered"] == 1
        assert stats["verified"] == 1
        assert stats["avg_verification_rounds"] == 0.5

    @pytest.mark.asyncio
    async def test_timeline_tracks_multiple_events(self) -> None:
        tracker = ClaimTracker()
        claim_id = await tracker.register_claim("Multi-event", "source")
        await tracker.update_status(claim_id, "verifying")
        await tracker.update_status(claim_id, "verified")
        timeline = await tracker.get_timeline(claim_id)
        assert len(timeline.events) == 3
