"""Tests for ResearchOrchestrator (Phase 6)."""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch


from lyra_research.discovery import ResearchSource, SourceType
from lyra_research.memory import (
    LocalCorpus,
    ResearchNoteStore,
    ResearchStrategyMemory,
    SessionCaseBank,
)
from lyra_research.orchestrator import ResearchOrchestrator, ResearchProgress


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source(
    source_id: str,
    title: str,
    url: str,
    source_type: SourceType = SourceType.PAPER,
) -> ResearchSource:
    return ResearchSource(
        id=source_id,
        title=title,
        source_type=source_type,
        url=url,
        abstract="An abstract about " + title,
        citations=10,
        stars=0,
        metadata={},
    )


def _make_orchestrator(tmp_path: Path) -> ResearchOrchestrator:
    """Build an orchestrator wired to tmp_path stores (no home-dir writes)."""
    return ResearchOrchestrator(
        output_dir=tmp_path / "reports",
        note_store=ResearchNoteStore(store_path=tmp_path / "notes.json"),
        corpus=LocalCorpus(db_path=tmp_path / "corpus.db"),
        strategy_memory=ResearchStrategyMemory(store_path=tmp_path / "strats.json"),
        case_bank=SessionCaseBank(store_path=tmp_path / "cases.json"),
    )


def _empty_discover(*args: Any, **kwargs: Any) -> Dict[str, List[ResearchSource]]:
    """Stub for MultiSourceDiscovery.discover that returns nothing."""
    return {}


def _two_source_discover(*args: Any, **kwargs: Any) -> Dict[str, List[ResearchSource]]:
    """Stub returning one paper and one repo."""
    return {
        "arxiv": [_make_source("p1", "Paper One", "https://arxiv.org/p1", SourceType.PAPER)],
        "github": [
            _make_source("r1", "Repo One", "https://github.com/r1", SourceType.REPOSITORY)
        ],
    }


# ---------------------------------------------------------------------------
# Basic pipeline completion
# ---------------------------------------------------------------------------


def test_orchestrator_research_returns_progress(tmp_path: Path) -> None:
    """Empty discover → pipeline completes without error."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("transformers")
    assert progress.error is None
    assert progress.is_complete


def test_orchestrator_research_report_not_none(tmp_path: Path) -> None:
    """Report object is populated after a successful run."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("attention mechanism")
    assert progress.report is not None


def test_orchestrator_research_with_sources(tmp_path: Path) -> None:
    """Paper and repo counts are tracked correctly."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_two_source_discover):
        progress = orc.research("deep learning")
    assert progress.papers_analyzed == 1
    assert progress.repos_analyzed == 1


def test_orchestrator_report_has_topic(tmp_path: Path) -> None:
    """Report topic matches the input topic."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("quantum computing")
    assert progress.report is not None
    assert progress.report.topic == "quantum computing"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_orchestrator_clarify_empty_topic(tmp_path: Path) -> None:
    """Empty topic should produce an error in progress, not raise."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("")
    assert progress.error is not None
    assert "empty" in progress.error.lower()


def test_orchestrator_invalid_depth_defaults_to_standard(tmp_path: Path) -> None:
    """Unknown depth value should default to 'standard' (no crash)."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("llm", depth="mega")
    assert progress.error is None
    assert progress.is_complete


def test_orchestrator_quick_depth_accepted(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("rlhf", depth="quick")
    assert progress.error is None


def test_orchestrator_deep_depth_accepted(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("rlhf", depth="deep")
    assert progress.error is None


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


def test_orchestrator_progress_callback_called(tmp_path: Path) -> None:
    """Callback is invoked at least once per step."""
    calls: List[ResearchProgress] = []

    def cb(p: ResearchProgress) -> None:
        calls.append(p)

    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        orc.research("transformers", progress_callback=cb)
    # 10 steps → at least 10 calls
    assert len(calls) >= 10


def test_orchestrator_progress_step_numbers_monotonic(tmp_path: Path) -> None:
    """Step numbers in callbacks should be monotonically increasing."""
    steps: List[int] = []

    def cb(p: ResearchProgress) -> None:
        steps.append(p.current_step)

    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        orc.research("bert", progress_callback=cb)
    assert steps == sorted(steps)


def test_orchestrator_progress_callback_has_step_name(tmp_path: Path) -> None:
    """Each callback delivers a non-empty step name."""
    names: List[str] = []

    def cb(p: ResearchProgress) -> None:
        names.append(p.current_step_name)

    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        orc.research("gpt", progress_callback=cb)
    assert all(n for n in names)


# ---------------------------------------------------------------------------
# Memory persistence
# ---------------------------------------------------------------------------


def test_orchestrator_memorize_saves_to_case_bank(tmp_path: Path) -> None:
    """After research, case_bank has exactly one entry."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        orc.research("diffusion models")
    cases = orc.case_bank.get_all()
    assert len(cases) == 1
    assert cases[0].topic == "diffusion models"


def test_orchestrator_memorize_saves_note(tmp_path: Path) -> None:
    """After research, the note store has at least one note."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        orc.research("retrieval augmented generation")
    notes = list(orc.note_store._notes.values())
    assert len(notes) >= 1


def test_orchestrator_memorize_case_has_quality_score(tmp_path: Path) -> None:
    """Saved case includes a quality_score between 0 and 1."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        orc.research("mixture of experts")
    case = orc.case_bank.get_all()[0]
    assert 0.0 <= case.quality_score <= 1.0


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def test_orchestrator_deduplicates_sources(tmp_path: Path) -> None:
    """Sources with the same URL are counted only once."""
    dup_source = _make_source("p1", "Paper One", "https://arxiv.org/p1")

    def discover_with_dups(*a: Any, **kw: Any) -> Dict[str, List[ResearchSource]]:
        return {
            "arxiv": [dup_source, dup_source],  # same URL twice
            "semantic_scholar": [dup_source],
        }

    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=discover_with_dups):
        progress = orc.research("test dedup")
    # Only 1 unique paper should survive
    assert progress.papers_analyzed == 1


# ---------------------------------------------------------------------------
# Elapsed time
# ---------------------------------------------------------------------------


def test_orchestrator_elapsed_seconds_positive(tmp_path: Path) -> None:
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_empty_discover):
        progress = orc.research("lora")
    assert progress.elapsed_seconds >= 0.0


# ---------------------------------------------------------------------------
# sources_found tracking
# ---------------------------------------------------------------------------


def test_orchestrator_sources_found_dict_populated(tmp_path: Path) -> None:
    """sources_found maps each source name to its count."""
    orc = _make_orchestrator(tmp_path)
    with patch.object(orc.discovery, "discover", side_effect=_two_source_discover):
        progress = orc.research("vision transformers")
    assert "arxiv" in progress.sources_found
    assert "github" in progress.sources_found
    assert progress.sources_found["arxiv"] == 1
    assert progress.sources_found["github"] == 1
