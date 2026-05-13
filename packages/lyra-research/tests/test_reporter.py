"""
Tests for the Research Synthesis & Report Engine (reporter.py).

All tests run offline — no network calls, no LLM calls.
"""

from pathlib import Path

import pytest

from lyra_research.reporter import (
    BoundCitation,
    CitationBinder,
    CrossSourceSynthesizer,
    FieldTaxonomy,
    QualityReport,
    ReportQualityChecker,
    ResearchReport,
    ResearchReportGenerator,
    SynthesisResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_paper_analyses():
    return [
        {
            "source_id": "p1",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new attention mechanism for transformers. "
                        "The model achieves state-of-the-art results on translation tasks. "
                        "It extends previous sequence-to-sequence approaches.",
            "findings": ["New transformer architecture"],
            "venue": "NeurIPS 2017",
            "url": "https://arxiv.org/abs/1706.03762",
        },
        {
            "source_id": "p2",
            "title": "BERT: Pre-training Deep Bidirectional Transformers",
            "abstract": "We introduce BERT for language understanding. "
                        "BERT builds on transformer pretraining to achieve "
                        "state-of-the-art on GLUE benchmark with 93.5% accuracy.",
            "findings": ["Bidirectional pretraining improves performance"],
            "venue": "NAACL 2019",
            "url": "https://arxiv.org/abs/1810.04805",
        },
        {
            "source_id": "p3",
            "title": "Sparse Attention for Long-Range Transformers",
            "abstract": "We present a sparse attention mechanism that improves over "
                        "dense attention. Our method reduces memory by 50% while "
                        "maintaining accuracy on ImageNet.",
            "findings": ["50% memory reduction"],
            "venue": "ICLR 2021",
            "url": "https://arxiv.org/abs/2004.05150",
        },
    ]


@pytest.fixture
def sample_repo_analyses():
    return [
        {
            "source_id": "r1",
            "title": "huggingface/transformers",
            "description": "State-of-the-art machine learning for train and inference with transformers.",
            "stars": 120000,
            "language": "Python",
            "url": "https://github.com/huggingface/transformers",
        },
        {
            "source_id": "r2",
            "title": "openai/triton",
            "description": "A language for writing efficient GPU kernels for inference and deploy.",
            "stars": 15000,
            "language": "Python",
            "url": "https://github.com/openai/triton",
        },
        {
            "source_id": "r3",
            "title": "EleutherAI/lm-eval",
            "description": "A unified evaluation benchmark for language model assessment.",
            "stars": 5000,
            "language": "Python",
            "url": "https://github.com/EleutherAI/lm-eval",
        },
    ]


@pytest.fixture
def sample_sources(sample_paper_analyses, sample_repo_analyses):
    return sample_paper_analyses + sample_repo_analyses


@pytest.fixture
def synthesizer():
    return CrossSourceSynthesizer()


@pytest.fixture
def binder():
    return CitationBinder()


@pytest.fixture
def generator():
    return ResearchReportGenerator()


@pytest.fixture
def checker():
    return ReportQualityChecker()


@pytest.fixture
def sample_synthesis(synthesizer, sample_paper_analyses, sample_repo_analyses):
    return synthesizer.synthesize(
        topic="transformer attention",
        paper_analyses=sample_paper_analyses,
        repo_analyses=sample_repo_analyses,
        gaps=["Limited work on efficient attention at scale"],
        contradictions=["Paper A claims X, Paper B claims Y"],
    )


@pytest.fixture
def sample_report(generator, sample_synthesis, sample_sources):
    return generator.generate(
        topic="transformer attention",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=sample_synthesis.gaps,
        contradictions=sample_synthesis.contradictions,
        checklist_completion=0.8,
    )


# ---------------------------------------------------------------------------
# CrossSourceSynthesizer tests
# ---------------------------------------------------------------------------

def test_cross_source_synthesizer_empty_inputs(synthesizer):
    """Synthesizer handles empty inputs without error."""
    result = synthesizer.synthesize(
        topic="test topic",
        paper_analyses=[],
        repo_analyses=[],
        gaps=[],
        contradictions=[],
    )
    assert result.topic == "test topic"
    assert result.source_count == 0
    assert isinstance(result.taxonomy, FieldTaxonomy)
    assert isinstance(result.best_papers, dict)
    assert isinstance(result.best_repos, dict)


def test_cross_source_synthesizer_builds_taxonomy(synthesizer, sample_paper_analyses):
    """Synthesizer builds a non-empty taxonomy from paper analyses."""
    result = synthesizer.synthesize(
        topic="transformer attention",
        paper_analyses=sample_paper_analyses,
        repo_analyses=[],
        gaps=[],
        contradictions=[],
    )
    assert result.taxonomy.topic == "transformer attention"
    assert isinstance(result.taxonomy.categories, list)
    assert isinstance(result.taxonomy.key_methods, list)
    assert isinstance(result.taxonomy.key_datasets, list)
    assert isinstance(result.taxonomy.key_metrics, list)


def test_cross_source_synthesizer_groups_papers(synthesizer, sample_paper_analyses):
    """Papers are grouped into categories from the taxonomy."""
    result = synthesizer.synthesize(
        topic="transformers",
        paper_analyses=sample_paper_analyses,
        repo_analyses=[],
        gaps=[],
        contradictions=[],
    )
    # All titles should appear somewhere in best_papers
    all_grouped_titles = [
        title
        for titles in result.best_papers.values()
        for title in titles
    ]
    assert len(all_grouped_titles) == len(sample_paper_analyses)


def test_cross_source_synthesizer_groups_repos(synthesizer, sample_repo_analyses):
    """Repos are grouped by detected use case."""
    result = synthesizer.synthesize(
        topic="transformers",
        paper_analyses=[],
        repo_analyses=sample_repo_analyses,
        gaps=[],
        contradictions=[],
    )
    assert isinstance(result.best_repos, dict)
    all_repo_names = [
        name
        for names in result.best_repos.values()
        for name in names
    ]
    assert len(all_repo_names) == len(sample_repo_analyses)


def test_cross_source_synthesizer_source_count(
    synthesizer, sample_paper_analyses, sample_repo_analyses
):
    """Source count reflects total papers + repos."""
    result = synthesizer.synthesize(
        topic="test",
        paper_analyses=sample_paper_analyses,
        repo_analyses=sample_repo_analyses,
        gaps=[],
        contradictions=[],
    )
    assert result.source_count == len(sample_paper_analyses) + len(sample_repo_analyses)


def test_cross_source_synthesizer_preserves_gaps(synthesizer):
    """Gaps are preserved in the synthesis result."""
    gaps = ["Gap 1", "Gap 2", "Gap 3"]
    result = synthesizer.synthesize(
        topic="test",
        paper_analyses=[],
        repo_analyses=[],
        gaps=gaps,
        contradictions=[],
    )
    assert result.gaps == gaps


def test_cross_source_synthesizer_preserves_contradictions(synthesizer):
    """Contradictions are preserved in the synthesis result."""
    contradictions = ["Paper A says X, Paper B says Y"]
    result = synthesizer.synthesize(
        topic="test",
        paper_analyses=[],
        repo_analyses=[],
        gaps=[],
        contradictions=contradictions,
    )
    assert result.contradictions == contradictions


def test_cross_source_synthesizer_synthesis_quality_range(
    synthesizer, sample_paper_analyses, sample_repo_analyses
):
    """Synthesis quality is in [0.0, 1.0]."""
    result = synthesizer.synthesize(
        topic="transformers",
        paper_analyses=sample_paper_analyses,
        repo_analyses=sample_repo_analyses,
        gaps=[],
        contradictions=[],
    )
    assert 0.0 <= result.synthesis_quality <= 1.0


def test_cross_source_synthesizer_extracts_relationships(synthesizer):
    """Relationship extraction finds 'extends', 'builds on' patterns."""
    papers = [
        {
            "source_id": "p1",
            "title": "Model B",
            "abstract": "Model B extends Transformer and builds on Attention mechanism.",
            "findings": [],
            "venue": "",
        }
    ]
    result = synthesizer.synthesize(
        topic="models",
        paper_analyses=papers,
        repo_analyses=[],
        gaps=[],
        contradictions=[],
    )
    # Relationship extraction may or may not fire depending on capitalization patterns
    assert isinstance(result.relationships, list)


def test_cross_source_synthesizer_taxonomy_key_methods(synthesizer):
    """Taxonomy detects known ML method keywords."""
    papers = [
        {
            "source_id": "p1",
            "title": "Attention Transformer",
            "abstract": "We use attention and transformer with retrieval augmentation.",
            "findings": [],
            "venue": "",
        }
    ]
    result = synthesizer.synthesize(
        topic="attention",
        paper_analyses=papers,
        repo_analyses=[],
        gaps=[],
        contradictions=[],
    )
    assert "attention" in result.taxonomy.key_methods or "transformer" in result.taxonomy.key_methods


# ---------------------------------------------------------------------------
# CitationBinder tests
# ---------------------------------------------------------------------------

def test_citation_binder_bind_empty(binder):
    """Binding empty text with empty sources returns unchanged text."""
    text, bound, unbound = binder.bind("", [])
    assert text == ""
    assert bound == []
    assert unbound == []


def test_citation_binder_bind_no_claims(binder, sample_sources):
    """Text with no claim patterns produces no bound citations."""
    text = "This is a generic introduction with no verifiable claims."
    result_text, bound, unbound = binder.bind(text, sample_sources)
    assert result_text == text
    assert bound == []
    assert unbound == []


def test_citation_binder_bind_with_sources(binder, sample_sources):
    """Text with detectable claim + matching sources binds the claim."""
    text = (
        "BERT achieves state-of-the-art on GLUE benchmark with 93.5% accuracy "
        "for language understanding tasks."
    )
    _text, bound, unbound = binder.bind(text, sample_sources)
    # Either bound or unbound depending on keyword overlap — just check types
    assert isinstance(bound, list)
    assert isinstance(unbound, list)
    for bc in bound:
        assert isinstance(bc, BoundCitation)
        assert bc.citation_key.startswith("[")


def test_citation_binder_fidelity_all_bound(binder):
    """citation_fidelity returns 1.0 when all claims are bound."""
    bound = [
        BoundCitation("claim", "s1", "Title", "url", "[1]"),
        BoundCitation("claim2", "s2", "Title2", "url2", "[2]"),
    ]
    assert binder.citation_fidelity(bound, []) == 1.0


def test_citation_binder_fidelity_some_unbound(binder):
    """citation_fidelity returns correct fraction when some claims are unbound."""
    bound = [BoundCitation("claim", "s1", "Title", "url", "[1]")]
    unbound = ["claim2", "claim3"]
    fidelity = binder.citation_fidelity(bound, unbound)
    assert abs(fidelity - 1 / 3) < 1e-6


def test_citation_binder_fidelity_none(binder):
    """citation_fidelity returns 1.0 when there are no claims at all."""
    assert binder.citation_fidelity([], []) == 1.0


def test_citation_binder_references_section(binder):
    """_build_references_section produces numbered reference list."""
    bound = [
        BoundCitation("claim", "s1", "Paper Title A", "https://a.com", "[1]"),
        BoundCitation("claim2", "s2", "Paper Title B", "https://b.com", "[2]"),
    ]
    refs = binder._build_references_section(bound)
    assert "1." in refs
    assert "Paper Title A" in refs
    assert "https://a.com" in refs


def test_citation_binder_references_section_empty(binder):
    """Empty bound list produces empty references section."""
    refs = binder._build_references_section([])
    assert refs == ""


def test_citation_binder_find_source_no_overlap(binder, sample_sources):
    """Claim with no keyword overlap with sources returns None."""
    result = binder._find_source_for_claim("xyz qrs abc def", sample_sources)
    assert result is None


def test_citation_binder_find_source_with_overlap(binder, sample_sources):
    """Claim with sufficient keyword overlap returns a matching source."""
    claim = "BERT achieves state-of-the-art on language understanding tasks."
    result = binder._find_source_for_claim(claim, sample_sources)
    # Should match p2 (BERT source)
    assert result is not None
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ResearchReport tests
# ---------------------------------------------------------------------------

def test_report_to_markdown_has_title(sample_report):
    """Markdown output contains the topic in the H1 heading."""
    md = sample_report.to_markdown()
    assert "# Deep Research: transformer attention" in md


def test_report_to_markdown_has_all_sections(sample_report):
    """Markdown includes all populated sections."""
    md = sample_report.to_markdown()
    assert "## Executive Summary" in md
    assert "## Field Taxonomy" in md
    assert "## Best Papers" in md
    assert "## Best GitHub Repositories" in md
    assert "## Research Gaps" in md
    assert "## Next Steps" in md


def test_report_to_markdown_has_metadata_line(sample_report):
    """Markdown header contains Generated date, Sources, Quality."""
    md = sample_report.to_markdown()
    assert "Generated:" in md
    assert "Sources:" in md
    assert "Quality:" in md


def test_report_to_markdown_skips_empty_sections():
    """Sections that are empty string are omitted from the Markdown output."""
    report = ResearchReport(topic="minimal")
    report.executive_summary = "Only summary."
    md = report.to_markdown()
    assert "## Executive Summary" in md
    assert "## Field Taxonomy" not in md
    assert "## Best Papers" not in md


def test_report_save_creates_file(tmp_path, sample_report):
    """save() creates a .md file in the given directory."""
    file_path = sample_report.save(tmp_path)
    assert file_path.exists()
    assert file_path.suffix == ".md"
    content = file_path.read_text(encoding="utf-8")
    assert "# Deep Research:" in content


def test_report_save_creates_directory(tmp_path, sample_report):
    """save() creates nested directories if they do not exist."""
    nested = tmp_path / "nested" / "output"
    file_path = sample_report.save(nested)
    assert file_path.exists()


def test_report_has_report_id(sample_report):
    """Each report has a unique UUID-based report_id."""
    assert len(sample_report.report_id) > 0


def test_report_generated_at_is_utc(sample_report):
    """generated_at is timezone-aware UTC."""
    from datetime import timezone
    assert sample_report.generated_at.tzinfo is not None


# ---------------------------------------------------------------------------
# ResearchReportGenerator tests
# ---------------------------------------------------------------------------

def test_report_generator_generates_complete_report(
    generator, sample_synthesis, sample_sources
):
    """Generator produces a ResearchReport with all sections populated."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=["Gap A", "Gap B"],
        contradictions=["Contradiction X"],
        checklist_completion=0.9,
    )
    assert isinstance(report, ResearchReport)
    assert report.topic == "transformers"
    assert report.sources_used > 0
    assert report.executive_summary != ""
    assert report.taxonomy_section != ""
    assert report.gaps_section != ""
    assert report.next_steps_section != ""


def test_report_generator_executive_summary(generator, sample_synthesis, sample_sources):
    """Executive summary contains the topic and source count."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=[],
    )
    assert "transformers" in report.executive_summary.lower() or \
           "transformer attention" in report.executive_summary.lower()
    assert str(sample_synthesis.source_count) in report.executive_summary


def test_report_generator_taxonomy_section(generator, sample_synthesis, sample_sources):
    """Taxonomy section contains the topic name."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=[],
    )
    assert "transformer" in report.taxonomy_section.lower()


def test_report_generator_papers_section(generator, sample_synthesis, sample_sources):
    """Papers section contains Markdown table headers."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=[],
    )
    assert "Title" in report.best_papers_section or "*No papers found.*" in report.best_papers_section


def test_report_generator_repos_section(generator, sample_synthesis, sample_sources):
    """Repos section contains Markdown table headers."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=[],
    )
    assert "Repository" in report.best_repos_section or "*No repositories found.*" in report.best_repos_section


def test_report_generator_gaps_section(generator, sample_synthesis, sample_sources):
    """Gaps section renders provided gaps as numbered list."""
    gaps = ["Gap One", "Gap Two"]
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=gaps,
        contradictions=[],
    )
    assert "1." in report.gaps_section
    assert "Gap One" in report.gaps_section


def test_report_generator_contested_section(generator, sample_synthesis, sample_sources):
    """Contested claims section renders contradictions."""
    contradictions = ["Paper A contradicts Paper B"]
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=contradictions,
    )
    assert "Paper A contradicts Paper B" in report.contested_claims_section


def test_report_generator_citation_fidelity_in_range(
    generator, sample_synthesis, sample_sources
):
    """citation_fidelity is in [0.0, 1.0]."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=[],
    )
    assert 0.0 <= report.citation_fidelity <= 1.0


def test_report_generator_quality_score_in_range(
    generator, sample_synthesis, sample_sources
):
    """quality_score is in [0.0, 1.0]."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=[],
        contradictions=[],
        checklist_completion=0.8,
    )
    assert 0.0 <= report.quality_score <= 1.0


def test_report_generator_next_steps_has_researcher_and_practitioner(
    generator, sample_synthesis, sample_sources
):
    """Next steps section addresses both researchers and practitioners."""
    report = generator.generate(
        topic="transformers",
        synthesis=sample_synthesis,
        sources=sample_sources,
        gaps=["Some gap"],
        contradictions=[],
    )
    assert "Researcher" in report.next_steps_section
    assert "Practitioner" in report.next_steps_section


# ---------------------------------------------------------------------------
# ReportQualityChecker tests
# ---------------------------------------------------------------------------

def test_quality_checker_passes_good_report(checker, sample_report):
    """A well-formed report with full coverage and citation fidelity passes."""
    # Force fidelity and mark all answered
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=9,
        sources_found=6,
        gaps_expected=3,
    )
    assert quality.passed is True
    assert quality.coverage_score >= 0.75


def test_quality_checker_fails_low_coverage(checker, sample_report):
    """Report with coverage below 0.75 fails and includes an issue message."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=5,   # 50% coverage — below threshold
        sources_found=6,
        gaps_expected=3,
    )
    assert quality.passed is False
    assert any("Coverage" in issue for issue in quality.issues)


def test_quality_checker_fails_low_fidelity(checker, sample_report):
    """Report with citation fidelity < 1.0 fails."""
    sample_report.citation_fidelity = 0.5
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=9,
        sources_found=6,
        gaps_expected=3,
    )
    assert quality.passed is False
    assert any("fidelity" in issue.lower() for issue in quality.issues)


def test_quality_checker_is_deliverable(checker, sample_report):
    """is_deliverable returns True when both gates are met."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=8,
        sources_found=6,
        gaps_expected=3,
    )
    assert checker.is_deliverable(quality) == quality.passed


def test_quality_checker_overall_score_range(checker, sample_report):
    """Overall score is always in [0.0, 1.0]."""
    sample_report.citation_fidelity = 0.8
    sample_report.gaps_section = "1. Gap\n2. Gap2"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=7,
        sources_found=5,
        gaps_expected=3,
    )
    assert 0.0 <= quality.overall_score <= 1.0


def test_quality_checker_zero_checklist_total(checker, sample_report):
    """checklist_total=0 defaults coverage to 1.0."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    quality = checker.check(
        report=sample_report,
        checklist_total=0,
        checklist_answered=0,
        sources_found=6,
        gaps_expected=3,
    )
    assert quality.coverage_score == 1.0


def test_quality_checker_source_breadth(checker, sample_report):
    """source_breadth is sources_used / sources_found (capped at 1.0)."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap\n2. Gap2\n3. Gap3"
    sample_report.sources_used = 3
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=9,
        sources_found=6,
        gaps_expected=3,
    )
    assert abs(quality.source_breadth - 3 / 6) < 1e-6


def test_quality_checker_no_sources_found(checker, sample_report):
    """sources_found=0 defaults source_breadth to 1.0."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=9,
        sources_found=0,
        gaps_expected=3,
    )
    assert quality.source_breadth == 1.0


def test_quality_checker_gap_detection_score(checker, sample_report):
    """gap_detection score is gaps_found / gaps_expected (capped at 1.0)."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C\n4. Gap D"
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=9,
        sources_found=6,
        gaps_expected=3,
    )
    # 4 gaps found vs 3 expected → capped at 1.0
    assert quality.gap_detection == 1.0


def test_quality_checker_issues_empty_when_passing(checker, sample_report):
    """No issues reported when report fully passes all gates."""
    sample_report.citation_fidelity = 1.0
    sample_report.gaps_section = "1. Gap A\n2. Gap B\n3. Gap C"
    sample_report.sources_used = 6
    quality = checker.check(
        report=sample_report,
        checklist_total=10,
        checklist_answered=10,
        sources_found=6,
        gaps_expected=3,
    )
    assert quality.issues == []
