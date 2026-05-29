"""Tests for LeaderboardManager."""

from __future__ import annotations

import pytest
from lyra_eval_pipeline import HistoricalEntry, Leaderboard, LeaderboardEntry, LeaderboardManager
from lyra_eval_pipeline.exceptions import LeaderboardError


class TestLeaderboardEntry:
    def test_entry_creation(self) -> None:
        entry = LeaderboardEntry(
            rank=1,
            name="Model-A",
            score=0.95,
            change=2,
            domain="math",
            num_evals=10,
        )
        assert entry.rank == 1
        assert entry.name == "Model-A"
        assert entry.score == 0.95
        assert entry.change == 2
        assert entry.domain == "math"

    def test_entry_defaults(self) -> None:
        entry = LeaderboardEntry(rank=1, name="M", score=0.5)
        assert entry.change == 0
        assert entry.domain == ""
        assert entry.num_evals == 0


class TestLeaderboard:
    def test_leaderboard_creation(self) -> None:
        lb = Leaderboard(
            entries=(),
            category="overall",
            updated_at=1000.0,
            total_entries=0,
        )
        assert lb.category == "overall"
        assert lb.total_entries == 0

    def test_leaderboard_with_entries(self) -> None:
        entries = (
            LeaderboardEntry(1, "A", 0.9),
            LeaderboardEntry(2, "B", 0.8),
        )
        lb = Leaderboard(
            entries=entries,
            category="code",
            updated_at=2000.0,
            total_entries=2,
        )
        assert len(lb.entries) == 2
        assert lb.entries[0].name == "A"


class TestHistoricalEntry:
    def test_history_creation(self) -> None:
        entry = HistoricalEntry(
            name="Model-A",
            scores=((1000.0, 0.8), (2000.0, 0.85)),
        )
        assert entry.name == "Model-A"
        assert len(entry.scores) == 2


class TestLeaderboardManager:
    @pytest.mark.asyncio
    async def test_update_entry_new(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry(name="Model-A", score=0.9, domain="math")
        lb = await manager.get_leaderboard("math")
        assert len(lb.entries) == 1
        assert lb.entries[0].name == "Model-A"
        assert lb.entries[0].score == 0.9

    @pytest.mark.asyncio
    async def test_update_entry_existing(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("Model-A", 0.8, "math")
        await manager.update_entry("Model-A", 0.9, "math")
        lb = await manager.get_leaderboard("math")
        assert lb.entries[0].score == 0.9
        # change should reflect increase
        assert lb.entries[0].change == 10  # (0.9 - 0.8) * 100

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty_category(self) -> None:
        manager = LeaderboardManager()
        lb = await manager.get_leaderboard("nonexistent")
        assert lb.total_entries == 0
        assert len(lb.entries) == 0

    @pytest.mark.asyncio
    async def test_get_leaderboard_sorted(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("Low", 0.5, "code")
        await manager.update_entry("High", 0.9, "code")
        lb = await manager.get_leaderboard("code")
        assert lb.entries[0].name == "High"
        assert lb.entries[1].name == "Low"

    @pytest.mark.asyncio
    async def test_get_leaderboard_top_k(self) -> None:
        manager = LeaderboardManager()
        for i in range(20):
            await manager.update_entry(f"Model-{i}", 0.5 + i * 0.02, "test")
        lb = await manager.get_leaderboard("test", top_k=3)
        assert len(lb.entries) == 3

    @pytest.mark.asyncio
    async def test_get_history(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("Model-A", 0.8, "math")
        await manager.update_entry("Model-A", 0.85, "math")
        history = await manager.get_history("Model-A")
        assert len(history.scores) == 2
        assert history.name == "Model-A"

    @pytest.mark.asyncio
    async def test_get_history_missing_raises(self) -> None:
        manager = LeaderboardManager()
        with pytest.raises(LeaderboardError, match="No history found"):
            await manager.get_history("nonexistent")

    @pytest.mark.asyncio
    async def test_compare_models(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("Model-A", 0.9, "math")
        await manager.update_entry("Model-B", 0.7, "math")
        await manager.update_entry("Model-A", 0.85, "code")
        await manager.update_entry("Model-B", 0.75, "code")
        result = await manager.compare_models(("Model-A", "Model-B"))
        assert result.entries[0].name == "Model-A"  # higher avg
        assert len(result.entries) == 2

    @pytest.mark.asyncio
    async def test_compare_models_empty_raises(self) -> None:
        manager = LeaderboardManager()
        with pytest.raises(LeaderboardError, match="No models specified"):
            await manager.compare_models(())

    @pytest.mark.asyncio
    async def test_compare_models_single_raises(self) -> None:
        manager = LeaderboardManager()
        with pytest.raises(LeaderboardError, match="at least 2 models"):
            await manager.compare_models(("Only-1",))

    @pytest.mark.asyncio
    async def test_compare_models_missing_scores_raises(self) -> None:
        manager = LeaderboardManager()
        with pytest.raises(LeaderboardError, match="No scores found"):
            await manager.compare_models(("Model-A", "Model-B"))

    @pytest.mark.asyncio
    async def test_update_entry_count(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("M", 0.5, "d")
        await manager.update_entry("M", 0.6, "d")
        await manager.update_entry("M", 0.7, "d")
        lb = await manager.get_leaderboard("d")
        assert lb.entries[0].num_evals == 3

    @pytest.mark.asyncio
    async def test_update_entry_empty_domain(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("Model-X", 0.8, "")
        lb = await manager.get_leaderboard("overall")
        assert len(lb.entries) == 1
        assert lb.entries[0].domain == "overall"

    @pytest.mark.asyncio
    async def test_leaderboard_updated_at_fresh(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("M", 0.5, "d")
        lb = await manager.get_leaderboard("d")
        assert lb.updated_at > 0

    @pytest.mark.asyncio
    async def test_leaderboard_total_entries(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("A", 0.5, "d")
        await manager.update_entry("B", 0.6, "d")
        await manager.update_entry("C", 0.7, "d")
        lb = await manager.get_leaderboard("d")
        assert lb.total_entries == 3

    @pytest.mark.asyncio
    async def test_multiple_categories(self) -> None:
        manager = LeaderboardManager()
        await manager.update_entry("M", 0.9, "math")
        await manager.update_entry("M", 0.8, "code")
        math_lb = await manager.get_leaderboard("math")
        code_lb = await manager.get_leaderboard("code")
        assert math_lb.entries[0].score == 0.9
        assert code_lb.entries[0].score == 0.8

    @pytest.mark.asyncio
    async def test_historical_entry_scores_tuple(self) -> None:
        entry = HistoricalEntry(name="M", scores=((1.0, 0.5), (2.0, 0.6)))
        first_ts, first_score = entry.scores[0]
        assert first_ts == 1.0
        assert first_score == 0.5
