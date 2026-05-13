"""Tests for lyra_cli.commands.research.handle_research_command (Phase 6)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch


from lyra_cli.commands.research import (
    _cmd_list,
    _cmd_related,
    _cmd_research,
    _cmd_show,
    handle_research_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CASE_BANK_PATH = "lyra_research.memory.SessionCaseBank"
_ORC_PATH = "lyra_research.orchestrator.ResearchOrchestrator"


def _capture() -> tuple[List[str], callable]:
    """Return (lines, output_fn) so tests can collect printed output."""
    lines: List[str] = []
    return lines, lines.append


def _make_mock_case(
    case_id: str,
    topic: str,
    quality: float = 0.8,
    sources: int = 10,
    report_path: str = "",
    summary: str = "summary text",
) -> MagicMock:
    """Build a MagicMock that behaves like ResearchCase."""
    case = MagicMock()
    case.id = case_id
    case.topic = topic
    case.quality_score = quality
    case.sources_found = sources
    case.report_path = report_path
    case.report_summary = summary
    case.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return case


def _make_mock_report(topic: str = "test topic") -> MagicMock:
    report = MagicMock()
    report.topic = topic
    report.quality_score = 0.75
    report.to_markdown.return_value = f"# Deep Research: {topic}\n\nContent here."
    return report


def _make_mock_progress(
    topic: str = "test",
    error: str | None = None,
    report=None,
    papers: int = 3,
    repos: int = 2,
    gaps: int = 1,
    elapsed: float = 5.0,
) -> MagicMock:
    p = MagicMock()
    p.error = error
    p.papers_analyzed = papers
    p.repos_analyzed = repos
    p.gaps_found = gaps
    p.elapsed_seconds = elapsed
    p.report = report if report is not None else _make_mock_report(topic)
    return p


def _make_bank(cases: list | None = None, related: list | None = None) -> MagicMock:
    """Return a mock SessionCaseBank."""
    bank = MagicMock()
    bank.get_all.return_value = cases or []
    bank.find_related.return_value = related or []
    return bank


# ---------------------------------------------------------------------------
# handle_research_command routing
# ---------------------------------------------------------------------------


class TestHandleResearchCommandRouting:
    def test_empty_args_returns_1(self) -> None:
        lines, out = _capture()
        code = handle_research_command("", output_fn=out)
        assert code == 1
        assert any("usage" in l.lower() for l in lines)

    def test_whitespace_args_returns_1(self) -> None:
        lines, out = _capture()
        code = handle_research_command("   ", output_fn=out)
        assert code == 1

    def test_list_subcommand_routes_to_list(self) -> None:
        with patch(_CASE_BANK_PATH, return_value=_make_bank()):
            lines, out = _capture()
            code = handle_research_command("list", output_fn=out)
        assert code == 0

    def test_show_subcommand_not_found(self) -> None:
        with patch(_CASE_BANK_PATH, return_value=_make_bank()):
            lines, out = _capture()
            code = handle_research_command("show nonexistent", output_fn=out)
        assert code == 1

    def test_related_subcommand_not_found(self) -> None:
        with patch(_CASE_BANK_PATH, return_value=_make_bank()):
            lines, out = _capture()
            code = handle_research_command("related nothing here", output_fn=out)
        assert code == 0  # related returns 0 even when empty

    def test_topic_routes_to_research(self) -> None:
        progress = _make_mock_progress("attention mechanism")
        mock_orc = MagicMock()
        mock_orc.research.return_value = progress
        with patch(_ORC_PATH, return_value=mock_orc):
            lines, out = _capture()
            code = handle_research_command("attention mechanism", output_fn=out)
        assert code == 0


# ---------------------------------------------------------------------------
# _cmd_list
# ---------------------------------------------------------------------------


class TestCmdList:
    def test_empty_case_bank(self) -> None:
        with patch(_CASE_BANK_PATH, return_value=_make_bank()):
            lines, out = _capture()
            code = _cmd_list(output_fn=out)
        assert code == 0
        assert any("no past" in l.lower() for l in lines)

    def test_list_with_cases(self) -> None:
        cases = [
            _make_mock_case("aaaa1111", "deep learning", quality=0.9, sources=20),
            _make_mock_case("bbbb2222", "transformers", quality=0.7, sources=15),
        ]
        with patch(_CASE_BANK_PATH, return_value=_make_bank(cases=cases)):
            lines, out = _capture()
            code = _cmd_list(output_fn=out)
        assert code == 0
        combined = "\n".join(lines)
        assert "aaaa1111" in combined
        assert "bbbb2222" in combined
        assert "deep learning" in combined

    def test_list_shows_quality_percentage(self) -> None:
        cases = [_make_mock_case("cccc3333", "rlhf", quality=0.85)]
        with patch(_CASE_BANK_PATH, return_value=_make_bank(cases=cases)):
            lines, out = _capture()
            _cmd_list(output_fn=out)
        combined = "\n".join(lines)
        assert "85%" in combined or "85" in combined


# ---------------------------------------------------------------------------
# _cmd_show
# ---------------------------------------------------------------------------


class TestCmdShow:
    def test_show_not_found_returns_1(self) -> None:
        with patch(_CASE_BANK_PATH, return_value=_make_bank()):
            lines, out = _capture()
            code = _cmd_show("nonexistent_xyz", output_fn=out)
        assert code == 1
        assert any("not found" in l.lower() or "no research" in l.lower() for l in lines)

    def test_show_by_partial_id(self) -> None:
        cases = [_make_mock_case("abcd1234", "lora fine-tuning", summary="Good summary")]
        with patch(_CASE_BANK_PATH, return_value=_make_bank(cases=cases)):
            lines, out = _capture()
            code = _cmd_show("abcd", output_fn=out)
        assert code == 0
        combined = "\n".join(lines)
        assert "lora fine-tuning" in combined

    def test_show_by_topic_keyword(self) -> None:
        cases = [_make_mock_case("zzzz9999", "mixture of experts")]
        with patch(_CASE_BANK_PATH, return_value=_make_bank(cases=cases)):
            lines, out = _capture()
            code = _cmd_show("experts", output_fn=out)
        assert code == 0

    def test_show_prints_summary_when_no_file(self) -> None:
        cases = [
            _make_mock_case(
                "ffff0000",
                "speculative decoding",
                report_path="/nonexistent/path/report.md",
                summary="Key finding: fast decoding.",
            )
        ]
        with patch(_CASE_BANK_PATH, return_value=_make_bank(cases=cases)):
            lines, out = _capture()
            _cmd_show("speculative", output_fn=out)
        combined = "\n".join(lines)
        assert "Key finding" in combined


# ---------------------------------------------------------------------------
# _cmd_related
# ---------------------------------------------------------------------------


class TestCmdRelated:
    def test_related_not_found(self) -> None:
        with patch(_CASE_BANK_PATH, return_value=_make_bank(related=[])):
            lines, out = _capture()
            code = _cmd_related("obscure topic xyz", output_fn=out)
        assert code == 0
        assert any("no related" in l.lower() for l in lines)

    def test_related_returns_cases(self) -> None:
        related = [
            _make_mock_case("aaaa0001", "attention mechanisms"),
            _make_mock_case("bbbb0002", "self-attention in nlp"),
        ]
        with patch(_CASE_BANK_PATH, return_value=_make_bank(related=related)):
            lines, out = _capture()
            code = _cmd_related("attention", output_fn=out)
        assert code == 0
        combined = "\n".join(lines)
        assert "attention mechanisms" in combined
        assert "self-attention" in combined


# ---------------------------------------------------------------------------
# _cmd_research (full pipeline mocked)
# ---------------------------------------------------------------------------


class TestCmdResearchMocked:
    def test_successful_research_returns_0(self) -> None:
        progress = _make_mock_progress("test topic")
        mock_orc = MagicMock()
        mock_orc.research.return_value = progress
        with patch(_ORC_PATH, return_value=mock_orc):
            lines, out = _capture()
            code = _cmd_research("test topic", output_fn=out)
        assert code == 0

    def test_research_prints_report_preview(self) -> None:
        report = _make_mock_report("llm agents")
        progress = _make_mock_progress("llm agents", report=report)
        mock_orc = MagicMock()
        mock_orc.research.return_value = progress
        with patch(_ORC_PATH, return_value=mock_orc):
            lines, out = _capture()
            _cmd_research("llm agents", output_fn=out)
        combined = "\n".join(lines)
        assert "Report Preview" in combined
        assert "Deep Research" in combined

    def test_research_failure_returns_1(self) -> None:
        progress = _make_mock_progress(error="network timeout")
        mock_orc = MagicMock()
        mock_orc.research.return_value = progress
        with patch(_ORC_PATH, return_value=mock_orc):
            lines, out = _capture()
            code = _cmd_research("broken topic", output_fn=out)
        assert code == 1
        combined = "\n".join(lines)
        assert "network timeout" in combined

    def test_research_prints_source_counts(self) -> None:
        progress = _make_mock_progress(papers=5, repos=3)
        mock_orc = MagicMock()
        mock_orc.research.return_value = progress
        with patch(_ORC_PATH, return_value=mock_orc):
            lines, out = _capture()
            _cmd_research("retrieval augmented generation", output_fn=out)
        combined = "\n".join(lines)
        assert "5 papers" in combined
        assert "3 repos" in combined

    def test_research_truncates_long_report(self) -> None:
        report = MagicMock()
        report.quality_score = 0.8
        report.to_markdown.return_value = "x" * 5000
        progress = _make_mock_progress(report=report)
        mock_orc = MagicMock()
        mock_orc.research.return_value = progress
        with patch(_ORC_PATH, return_value=mock_orc):
            lines, out = _capture()
            _cmd_research("long topic", output_fn=out)
        combined = "\n".join(lines)
        assert "truncated" in combined
