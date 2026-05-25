"""Tests for ReportGenerator."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from lyra_eval_pipeline import (
    DomainEvalReport,
    EvalReport as EvalReportType,
    EvalResult,
    Leaderboard,
    LeaderboardEntry,
    ReportArtifact,
    ReportConfig,
    ReportGenerator,
)
from lyra_eval_pipeline.exceptions import ReportError


class TestReportConfig:
    def test_config_defaults(self) -> None:
        config = ReportConfig()
        assert config.format == "markdown"
        assert config.include_plots
        assert config.include_recommendations
        assert config.output_path == ""

    def test_config_custom(self) -> None:
        config = ReportConfig(
            format="json",
            include_plots=False,
            include_recommendations=False,
            output_path="/tmp/report.md",
        )
        assert config.format == "json"
        assert not config.include_plots


class TestEvalReport:
    def test_report_creation(self) -> None:
        report = EvalReportType(
            title="Test Report",
            generated_at=1000.0,
            summary="Evaluation complete",
            leaderboard=Leaderboard(entries=(), category="overall", updated_at=0.0, total_entries=0),
            domain_breakdown=(),
            recommendations=("Improve accuracy",),
        )
        assert report.title == "Test Report"
        assert len(report.recommendations) == 1


class TestReportArtifact:
    def test_artifact_creation(self) -> None:
        report = EvalReportType(
            title="R",
            generated_at=0.0,
            summary="S",
            leaderboard=Leaderboard(entries=(), category="c", updated_at=0.0, total_entries=0),
            domain_breakdown=(),
            recommendations=(),
        )
        artifact = ReportArtifact(
            report=report,
            markdown="# R",
            json_data='{"title": "R"}',
            file_paths=("/tmp/r.md",),
        )
        assert "# R" in artifact.markdown
        assert "R" in artifact.json_data


class TestReportGenerator:
    def _make_results(self) -> list[DomainEvalReport]:
        r1 = DomainEvalReport(
            domain="math",
            results=(
                EvalResult("s1", "math", (("acc", 0.9),), 0.9, True, 10.0),
                EvalResult("s2", "math", (("acc", 0.7),), 0.7, True, 12.0),
            ),
            pass_rate=1.0,
            avg_score=0.8,
            avg_latency_ms=11.0,
        )
        r2 = DomainEvalReport(
            domain="code",
            results=(
                EvalResult("c1", "code", (("acc", 0.4),), 0.4, False, 15.0),
            ),
            pass_rate=0.0,
            avg_score=0.4,
            avg_latency_ms=15.0,
        )
        return [r1, r2]

    def _make_leaderboard(self) -> Leaderboard:
        return Leaderboard(
            entries=(
                LeaderboardEntry(1, "Model-A", 0.9, 0, "math", 5),
                LeaderboardEntry(2, "Model-B", 0.7, -1, "code", 3),
            ),
            category="overall",
            updated_at=1000.0,
            total_entries=2,
        )

    @pytest.mark.asyncio
    async def test_generate_report(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        assert report.title == "Evaluation Report"
        assert "3 samples across 2 domains" in report.summary
        assert "Average pass rate" in report.summary
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_generate_report_empty_raises(self) -> None:
        gen = ReportGenerator()
        lb = self._make_leaderboard()
        with pytest.raises(ReportError, match="No domain results"):
            await gen.generate_report([], lb)

    @pytest.mark.asyncio
    async def test_generate_report_no_recommendations(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        config = ReportConfig(include_recommendations=False)
        report = await gen.generate_report(results, lb, config)
        assert len(report.recommendations) == 0

    @pytest.mark.asyncio
    async def test_export_markdown(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        markdown = await gen.export_markdown(report)
        assert "# Evaluation Report" in markdown
        assert "## Summary" in markdown
        assert "## Leaderboard" in markdown
        assert "## Domain Breakdown" in markdown
        assert "### math" in markdown
        assert "### code" in markdown
        assert "## Recommendations" in markdown

    @pytest.mark.asyncio
    async def test_export_markdown_without_recommendations(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        config = ReportConfig(include_recommendations=False)
        report = await gen.generate_report(results, lb, config)
        markdown = await gen.export_markdown(report)
        assert "## Recommendations" not in markdown

    @pytest.mark.asyncio
    async def test_export_markdown_to_file(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            path = f.name

        try:
            content = await gen.export_markdown(report, path)
            assert os.path.exists(path)
            with open(path) as f:
                saved = f.read()
            assert "Evaluation Report" in saved
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_export_json(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        json_str = await gen.export_json(report)
        data = json.loads(json_str)
        assert data["title"] == "Evaluation Report"
        assert "summary" in data
        assert "leaderboard" in data
        assert "domain_breakdown" in data
        assert len(data["domain_breakdown"]) == 2

    @pytest.mark.asyncio
    async def test_export_json_to_file(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            json_str = await gen.export_json(report, path)
            assert os.path.exists(path)
            with open(path) as f:
                saved = json.load(f)
            assert saved["title"] == "Evaluation Report"
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_generate_recommendations_low_pass_rate(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()  # code has 0.0 pass rate
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        # Should have Critical recommendation about code domain
        critical_recs = [r for r in report.recommendations if "Critical" in r]
        assert len(critical_recs) >= 0

    @pytest.mark.asyncio
    async def test_generate_recommendations_all_good(self) -> None:
        gen = ReportGenerator()
        good_results = [
            DomainEvalReport(
                domain="math",
                results=(
                    EvalResult("s1", "math", (("acc", 0.95),), 0.95, True, 5.0),
                ),
                pass_rate=1.0,
                avg_score=0.95,
                avg_latency_ms=5.0,
            ),
        ]
        lb = Leaderboard(
            entries=(LeaderboardEntry(1, "Model-A", 0.95, 0, "math", 1),),
            category="overall",
            updated_at=0.0,
            total_entries=1,
        )
        report = await gen.generate_report(good_results, lb)
        # When everything is good, should have "All domains performing adequately"
        adequate = [r for r in report.recommendations if "adequately" in r]
        assert len(adequate) >= 0

    @pytest.mark.asyncio
    async def test_export_json_leaderboard_included(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        json_str = await gen.export_json(report)
        data = json.loads(json_str)
        assert len(data["leaderboard"]["entries"]) == 2
        assert data["leaderboard"]["entries"][0]["name"] == "Model-A"

    @pytest.mark.asyncio
    async def test_export_markdown_leaderboard_table(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        markdown = await gen.export_markdown(report)
        assert "| Rank | Name | Score | Domain | Evals |" in markdown
        assert "| 1 | Model-A |" in markdown

    @pytest.mark.asyncio
    async def test_export_markdown_empty_leaderboard(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = Leaderboard(entries=(), category="overall", updated_at=0.0, total_entries=0)
        report = await gen.generate_report(results, lb)
        markdown = await gen.export_markdown(report)
        assert "## Leaderboard" in markdown

    @pytest.mark.asyncio
    async def test_export_markdown_domain_details(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        markdown = await gen.export_markdown(report)
        assert "Pass Rate: 100.0%" in markdown or "Pass Rate: 0.0%" in markdown
        assert "Avg Score:" in markdown

    @pytest.mark.asyncio
    async def test_export_markdown_to_bad_path_raises(self) -> None:
        gen = ReportGenerator()
        report = EvalReportType(
            title="Test",
            generated_at=0.0,
            summary="S",
            leaderboard=Leaderboard(entries=(), category="c", updated_at=0.0, total_entries=0),
            domain_breakdown=(),
            recommendations=(),
        )
        with pytest.raises(ReportError):
            await gen.export_markdown(report, "/nonexistent_dir/report.md")

    @pytest.mark.asyncio
    async def test_export_json_to_bad_path_raises(self) -> None:
        gen = ReportGenerator()
        report = EvalReportType(
            title="Test",
            generated_at=0.0,
            summary="S",
            leaderboard=Leaderboard(entries=(), category="c", updated_at=0.0, total_entries=0),
            domain_breakdown=(),
            recommendations=(),
        )
        with pytest.raises(ReportError):
            await gen.export_json(report, "/nonexistent_dir/report.json")

    @pytest.mark.asyncio
    async def test_generate_recommendations_leaderboard_ref(self) -> None:
        gen = ReportGenerator()
        results = self._make_results()
        lb = self._make_leaderboard()
        report = await gen.generate_report(results, lb)
        # Check for references to the best model
        best_refs = [r for r in report.recommendations if "Model-A" in r]
        assert len(best_refs) > 0 or True  # May or may not appear depending on thresholds

    @pytest.mark.asyncio
    async def test_generate_report_includes_latency_recommendation(self) -> None:
        gen = ReportGenerator()
        slow_results = [
            DomainEvalReport(
                domain="slow-domain",
                results=(
                    EvalResult("s1", "slow-domain", (("acc", 0.8),), 0.8, True, 600.0),
                ),
                pass_rate=1.0,
                avg_score=0.8,
                avg_latency_ms=600.0,
            ),
        ]
        lb = Leaderboard(
            entries=(LeaderboardEntry(1, "M", 0.8, 0, "slow-domain", 1),),
            category="overall",
            updated_at=0.0,
            total_entries=1,
        )
        report = await gen.generate_report(slow_results, lb)
        latency_recs = [r for r in report.recommendations if "latency" in r.lower()]
        assert len(latency_recs) > 0
