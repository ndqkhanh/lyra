"""
Unit tests for SkillExtractor and SkillTemplate modules.
Mocks FindingsMemory, SkillRegistry, SkillNet, and file I/O.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from lyra.research.findings_memory import FindingRecord, FindingStage, ValuationScores
from lyra.research.evidence_graph import VerificationStatus
from lyra.research.skill_extractor import (
    SkillExtractor,
    SkillTemplate,
    MIN_CONFIDENCE_FOR_EXTRACTION,
    DEFAULT_SKILL_CATEGORY,
    SKILL_FILE_EXTENSION,
    _STOP_WORDS,
)
from lyra.skills.skill import Skill, SkillCategory


# =============================================================================
# Sample finding records
# =============================================================================

SAMPLE_FINDING = FindingRecord(
    finding_id="f-001",
    quest_id="q-001",
    hypothesis="Attention sparsity reduces inference cost by 40 percent",
    stage=FindingStage.PROGRESS,
    valuation=ValuationScores(utility=0.9, quality=0.8, efficiency=0.85),
    experiment_logs=[{"delta": 0.4, "metric_before": 1.0, "metric_after": 1.4}],
    analysis="Results show significant improvement in throughput",
    implementation_ref="git:abc123",
    metadata={"tags": ["attention", "efficiency"], "language": "python"},
)

IDEA_FINDING = FindingRecord(
    finding_id="f-002",
    quest_id="q-001",
    hypothesis="A new hypothesis that needs testing",
    stage=FindingStage.IDEA,
    valuation=ValuationScores(utility=0.6, quality=0.5, efficiency=0.5),
    experiment_logs=[],
    analysis="",
)

LOW_VALUATION_FINDING = FindingRecord(
    finding_id="f-003",
    quest_id="q-001",
    hypothesis="Low confidence hypothesis",
    stage=FindingStage.IDEA,
    valuation=ValuationScores(utility=0.1, quality=0.1, efficiency=0.1),
    experiment_logs=[],
    analysis="",
)

EMPTY_HYPOTHESIS_FINDING = FindingRecord(
    finding_id="f-004",
    quest_id="q-001",
    hypothesis="",
    stage=FindingStage.IDEA,
    valuation=ValuationScores(utility=0.9, quality=0.9, efficiency=0.9),
    experiment_logs=[],
    analysis="",
)


# =============================================================================
# SkillTemplate
# =============================================================================

class TestSkillTemplate:
    def test_defaults(self) -> None:
        tmpl = SkillTemplate()
        assert tmpl.name == ""
        assert tmpl.description == ""
        assert tmpl.category == DEFAULT_SKILL_CATEGORY
        assert tmpl.trigger_patterns == []
        assert tmpl.tags == []
        assert tmpl.language is None
        assert tmpl.content == ""
        assert tmpl.source_ref == ""

    def test_from_finding_basic(self) -> None:
        tmpl = SkillTemplate.from_finding(SAMPLE_FINDING)
        assert "attention" in tmpl.name
        assert "sparsity" in tmpl.name
        assert "inference" in tmpl.description
        assert len(tmpl.trigger_patterns) > 0
        assert tmpl.language == "python"
        assert "verified" in tmpl.tags
        assert "progress" in tmpl.tags

    def test_from_finding_with_custom_content(self) -> None:
        tmpl = SkillTemplate.from_finding(SAMPLE_FINDING, content="Custom content")
        assert tmpl.content == "Custom content"

    def test_from_finding_empty_hypothesis(self) -> None:
        tmpl = SkillTemplate.from_finding(EMPTY_HYPOTHESIS_FINDING)
        assert tmpl.name == "extracted-finding"

    def test_render(self) -> None:
        tmpl = SkillTemplate(
            name="test-skill",
            description="Test description",
            category=SkillCategory.BACKEND_PATTERNS,
            trigger_patterns=["attention", "sparsity"],
            tags=["test", "python"],
            language="python",
            content="## Content\n\nBody text",
            source_ref="f-001",
        )
        rendered = tmpl.render()
        assert "name: test-skill" in rendered
        assert "description: Test description" in rendered
        assert "category: backend-patterns" in rendered
        assert "trigger_patterns:" in rendered
        assert "language: python" in rendered
        assert "source: finding-f-001" in rendered
        assert "## Content" in rendered
        assert rendered.strip().endswith("---") is False  # content after ---

    def test_render_no_language(self) -> None:
        tmpl = SkillTemplate(
            name="no-lang",
            description="No lang",
            content="Some content",
        )
        rendered = tmpl.render()
        assert "language:" not in rendered

    def test_render_no_source_ref(self) -> None:
        tmpl = SkillTemplate(
            name="no-src",
            description="No source",
            content="Body",
            source_ref="",
        )
        rendered = tmpl.render()
        assert "source:" not in rendered

    def test_to_skill(self) -> None:
        tmpl = SkillTemplate(
            name="my-skill",
            description="My description",
            category=SkillCategory.TDD_TESTING,
            trigger_patterns=["pytest"],
            tags=["test"],
            language="python",
            content="## Body",
            source_ref="f-001",
        )
        skill = tmpl.to_skill()
        assert skill.name == "my-skill"
        assert skill.description == "My description"
        assert skill.category == SkillCategory.TDD_TESTING
        assert skill.trigger_patterns == ["pytest"]
        assert skill.tags == ["test"]
        assert skill.language == "python"
        assert skill.source == "lyra"
        assert skill.metadata["source_type"] == "research_finding"
        assert skill.metadata["source_ref"] == "f-001"

    def test_auto_content(self) -> None:
        content = SkillTemplate._auto_content(SAMPLE_FINDING)
        assert "Attention sparsity" in content
        assert "## Evidence" in content
        assert "1 experiment" in content
        assert "git:abc123" in content

    def test_auto_content_no_experiments(self) -> None:
        content = SkillTemplate._auto_content(IDEA_FINDING)
        assert "A new hypothesis" in content
        assert "## Evidence" not in content

    def test_slugify(self) -> None:
        assert SkillTemplate._slugify("Hello World!") == "hello-world"
        assert SkillTemplate._slugify("  Leading and trailing  ") == "leading-and-trailing"
        assert SkillTemplate._slugify("") == ""
        assert SkillTemplate._slugify("a-b_c d") == "a-b_c-d"

    def test_from_finding_stage_tags_progress(self) -> None:
        """PROGRESS stage adds 'verified' tag."""
        tmpl = SkillTemplate.from_finding(SAMPLE_FINDING)
        assert "verified" in tmpl.tags
        assert "progress" in tmpl.tags

    def test_from_finding_stage_tags_idea(self) -> None:
        tmpl = SkillTemplate.from_finding(IDEA_FINDING)
        assert "idea" in tmpl.tags
        assert "verified" not in tmpl.tags


# =============================================================================
# SkillExtractor
# =============================================================================

class TestSkillExtractorInit:
    def test_default(self) -> None:
        ex = SkillExtractor()
        assert ex._registry is None
        assert ex._skill_net is None
        assert ex._output_dir is None

    def test_with_registry(self) -> None:
        registry = MagicMock()
        ex = SkillExtractor(registry=registry)
        assert ex._registry is registry

    def test_with_output_dir(self) -> None:
        ex = SkillExtractor(output_dir="/tmp/skills")
        assert ex._output_dir == Path("/tmp/skills")


class TestSkillExtractorFromFinding:
    def test_extract_success(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.CONFIRMED,
            auto_register=False,
            write_file=False,
        )
        assert skill is not None
        assert isinstance(skill, Skill)
        assert "attention" in skill.name

    def test_extract_with_verified_status(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.VERIFIED,
            auto_register=False,
            write_file=False,
        )
        assert skill is not None

    def test_extract_rejected_by_quality_gate_low_valuation(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            LOW_VALUATION_FINDING,
            verification_status=None,
            auto_register=False,
            write_file=False,
        )
        assert skill is None

    def test_extract_rejected_by_quality_gate_empty_hypothesis(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            EMPTY_HYPOTHESIS_FINDING,
            verification_status=None,
            auto_register=False,
            write_file=False,
        )
        assert skill is None

    def test_extract_rejected_by_verification_status(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.UNVERIFIED,
            auto_register=False,
            write_file=False,
        )
        assert skill is None

    def test_extract_rejected_by_disputed_status(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.DISPUTED,
            auto_register=False,
            write_file=False,
        )
        assert skill is None

    def test_extract_rejected_by_refuted_status(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.REFUTED,
            auto_register=False,
            write_file=False,
        )
        assert skill is None

    def test_extract_with_auto_register(self) -> None:
        registry = MagicMock()
        ex = SkillExtractor(registry=registry)
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.CONFIRMED,
            auto_register=True,
            write_file=False,
        )
        assert skill is not None
        registry.register.assert_called_once()

    def test_extract_with_skill_net(self) -> None:
        skill_net = MagicMock()
        ex = SkillExtractor(skill_net=skill_net)
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.CONFIRMED,
            auto_register=False,
            write_file=False,
        )
        assert skill is not None
        skill_net.add_skill.assert_called_once()

    def test_extract_with_write_file(self) -> None:
        ex = SkillExtractor(output_dir="/tmp/skills")
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.CONFIRMED,
            auto_register=False,
            write_file=True,
        )
        assert skill is not None

    def test_extract_idea_without_verification(self) -> None:
        """Should extract IDEA finding when verification_status is None."""
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            IDEA_FINDING,
            verification_status=None,
            auto_register=False,
            write_file=False,
        )
        assert skill is not None

    def test_extract_no_output_dir_skips_write(self) -> None:
        ex = SkillExtractor()
        skill = ex.extract_from_finding(
            SAMPLE_FINDING,
            verification_status=VerificationStatus.CONFIRMED,
            auto_register=False,
            write_file=True,
        )
        assert skill is not None


class TestSkillExtractorExtractMultiple:
    def test_multiple_all_valid(self) -> None:
        ex = SkillExtractor()
        skills = ex.extract_multiple(
            [SAMPLE_FINDING, SAMPLE_FINDING],
            verification_statuses={"f-001": VerificationStatus.CONFIRMED},
            auto_register=False,
            write_file=False,
        )
        assert len(skills) == 2

    def test_multiple_some_rejected(self) -> None:
        ex = SkillExtractor()
        skills = ex.extract_multiple(
            [SAMPLE_FINDING, LOW_VALUATION_FINDING],
            verification_statuses={
                "f-001": VerificationStatus.CONFIRMED,
                "f-003": VerificationStatus.CONFIRMED,
            },
            auto_register=False,
            write_file=False,
        )
        assert len(skills) == 1  # only the valid one

    def test_multiple_no_verification_map(self) -> None:
        ex = SkillExtractor()
        skills = ex.extract_multiple(
            [SAMPLE_FINDING, IDEA_FINDING],
            verification_statuses=None,
            auto_register=False,
            write_file=False,
        )
        assert len(skills) == 2


class TestSkillExtractorFromPaper:
    def test_file_not_found(self) -> None:
        ex = SkillExtractor()
        with pytest.raises(FileNotFoundError, match="Paper not found"):
            ex.extract_from_paper("/nonexistent/paper.md")

    def test_extract_markdown_paper(self) -> None:
        ex = SkillExtractor()
        mock_path = MagicMock(spec=Path)
        mock_path.resolve.return_value = mock_path
        mock_path.is_file.return_value = True
        mock_path.suffix = ".md"
        mock_path.name = "paper.md"
        mock_path.read_text.return_value = (
            "## Introduction\n\nThis paper covers new methods.\n"
            "## Methodology\n\nWe used deep learning.\n"
            "## Results\n\nAccuracy improved by 20%.\n"
        )
        with patch("lyra.research.skill_extractor.Path", return_value=mock_path):
            skills = ex.extract_from_paper("paper.md", auto_register=False, write_file=False)
        assert len(skills) >= 2

    def test_extract_paper_with_auto_register(self) -> None:
        registry = MagicMock()
        ex = SkillExtractor(registry=registry)
        mock_path = MagicMock(spec=Path)
        mock_path.resolve.return_value = mock_path
        mock_path.is_file.return_value = True
        mock_path.suffix = ".md"
        mock_path.name = "paper.md"
        mock_path.read_text.return_value = "## Method\n\nNew method."
        with patch("lyra.research.skill_extractor.Path", return_value=mock_path):
            skills = ex.extract_from_paper("paper.md", auto_register=True, write_file=False)
        assert len(skills) >= 1
        assert registry.register.called

    def test_extract_pdf_pymupdf(self) -> None:
        ex = SkillExtractor()
        mock_path = MagicMock(spec=Path)
        mock_path.resolve.return_value = mock_path
        mock_path.is_file.return_value = True
        mock_path.suffix = ".pdf"
        mock_path.name = "paper.pdf"
        with patch("lyra.research.skill_extractor.Path", return_value=mock_path):
            with patch("fitz.open") as mock_fitz:
                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_page.get_text.return_value = "## Method\n\nDeep learning approach."
                mock_doc.__iter__.return_value = [mock_page]
                mock_fitz.return_value = mock_doc
                skills = ex.extract_from_paper("paper.pdf", auto_register=False, write_file=False)
        assert len(skills) >= 1

    def test_extract_pdf_fallback(self) -> None:
        ex = SkillExtractor()
        mock_path = MagicMock(spec=Path)
        mock_path.resolve.return_value = mock_path
        mock_path.is_file.return_value = True
        mock_path.suffix = ".pdf"
        mock_path.name = "paper.pdf"
        mock_path.read_bytes.return_value = b"(Some raw text content)"
        with patch("lyra.research.skill_extractor.Path", return_value=mock_path):
            with patch("builtins.__import__", side_effect=ImportError("no fitz")):
                skills = ex.extract_from_paper("paper.pdf", auto_register=False, write_file=False)
        assert len(skills) >= 1


class TestSkillExtractorQualityGate:
    def test_passes_valid(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            SAMPLE_FINDING, VerificationStatus.CONFIRMED,
        ) is True

    def test_passes_no_verification_status(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            SAMPLE_FINDING, None,
        ) is True

    def test_fails_empty_hypothesis(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            EMPTY_HYPOTHESIS_FINDING, None,
        ) is False

    def test_fails_low_valuation(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            LOW_VALUATION_FINDING, None,
        ) is False

    def test_fails_disputed(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            SAMPLE_FINDING, VerificationStatus.DISPUTED,
        ) is False

    def test_fails_refuted(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            SAMPLE_FINDING, VerificationStatus.REFUTED,
        ) is False

    def test_fails_unverified(self) -> None:
        assert SkillExtractor._passes_quality_gate(
            SAMPLE_FINDING, VerificationStatus.UNVERIFIED,
        ) is False


class TestSkillExtractorPaperParsing:
    def test_read_markdown(self) -> None:
        mock_path = MagicMock(spec=Path)
        mock_path.suffix = ".md"
        mock_path.read_text.return_value = "# Title\n\nBody"
        text = SkillExtractor._read_paper(mock_path)
        assert "Body" in text

    def test_read_txt(self) -> None:
        mock_path = MagicMock(spec=Path)
        mock_path.suffix = ".txt"
        mock_path.read_text.return_value = "Plain text content"
        text = SkillExtractor._read_paper(mock_path)
        assert "Plain text" in text

    def test_read_unknown_extension(self) -> None:
        mock_path = MagicMock(spec=Path)
        mock_path.suffix = ".rst"
        mock_path.read_text.return_value = "RST content"
        text = SkillExtractor._read_paper(mock_path)
        assert "RST content" in text

    def test_parse_sections(self) -> None:
        text = (
            "## Intro\n\nIntro body\n\n"
            "## Method\n\nMethod body\n\n"
            "### Sub\n\nSub body\n"
        )
        sections = SkillExtractor._parse_sections(text)
        assert len(sections) == 3
        assert sections[0]["heading"] == "Intro"
        assert sections[1]["heading"] == "Method"
        assert sections[2]["heading"] == "Sub"

    def test_parse_sections_no_headings(self) -> None:
        text = "Just plain text with no markdown headings at all."
        sections = SkillExtractor._parse_sections(text)
        assert len(sections) == 1
        assert sections[0]["heading"] == "Abstract"


class TestSkillExtractorLinkToSkillNet:
    def test_link_to_skillnet_no_net(self) -> None:
        ex = SkillExtractor()
        skill1 = Skill(name="a", description="", content="hello world", tags=["test"])
        skill2 = Skill(name="b", description="", content="hello world", tags=["test"])
        net = ex.link_to_skillnet([skill1, skill2], similarity_threshold=0.01)
        assert len(net.skills) == 2
        assert len(net.links) >= 2  # bidirectional

    def test_link_to_skillnet_existing_net(self) -> None:
        from lyra.skills.skillnet import SkillNet
        existing = SkillNet()
        ex = SkillExtractor(skill_net=existing)
        skill = Skill(name="c", description="", content="unique content xyz", tags=["unique"])
        net = ex.link_to_skillnet([skill], similarity_threshold=0.9)
        assert net is existing

    def test_jaccard_similarity(self) -> None:
        skill_a = Skill(
            name="a", description="", content="hello world test alpha",
            tags=["tag1", "tag2"],
        )
        skill_b = Skill(
            name="b", description="", content="hello world test beta",
            tags=["tag1", "tag3"],
        )
        sim = SkillExtractor._jaccard(skill_a, skill_b)
        assert sim > 0

    def test_jaccard_no_overlap(self) -> None:
        skill_a = Skill(name="a", description="", content="aaaa bbbb", tags=["x"])
        skill_b = Skill(name="b", description="", content="cccc dddd", tags=["y"])
        sim = SkillExtractor._jaccard(skill_a, skill_b)
        assert sim == 0.0


class TestSkillExtractorDetectCategory:
    def test_methodology_heading(self) -> None:
        section = {"heading": "Methodology Details", "body": "body"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.BACKEND_PATTERNS

    def test_results_heading(self) -> None:
        section = {"heading": "Results and Evaluation", "body": "body"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.TDD_TESTING

    def test_security_heading(self) -> None:
        section = {"heading": "Security Analysis", "body": "body"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.SECURITY_REVIEW

    def test_api_heading(self) -> None:
        section = {"heading": "API Design", "body": "body"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.API_DESIGN

    def test_frontend_heading(self) -> None:
        section = {"heading": "Frontend Components", "body": "body"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.FRONTEND_PATTERNS

    def test_deployment_body(self) -> None:
        section = {"heading": "Infrastructure", "body": "docker and deploy pipelines"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == SkillCategory.DEPLOYMENT

    def test_default_category(self) -> None:
        section = {"heading": "Introduction", "body": "body"}
        cat = SkillExtractor._detect_category_from_section(section)
        assert cat == DEFAULT_SKILL_CATEGORY


class TestSkillExtractorHelpers:
    def test_extract_trigger_words(self) -> None:
        section = {"heading": "Method", "body": "deep learning neural network training accuracy"}
        words = SkillExtractor._extract_trigger_words(section)
        assert len(words) > 0
        assert "deep" in words
        assert "learning" in words

    def test_extract_tags_from_section(self) -> None:
        section = {"heading": "Experiment Results"}
        tags = SkillExtractor._extract_tags_from_section(section)
        assert "experiment" in tags or "evaluation" in tags

    def test_extract_tags_from_section_abstract(self) -> None:
        section = {"heading": "Abstract"}
        tags = SkillExtractor._extract_tags_from_section(section)
        assert "overview" in tags

    def test_detect_language_from_code_block(self) -> None:
        text = "Some text\n\n```python\nprint('hello')\n```"
        lang = SkillExtractor._detect_language_from_text(text)
        assert lang == "python"

    def test_detect_language_python_keywords(self) -> None:
        text = "the function def my_func(): class MyClass: import os"
        lang = SkillExtractor._detect_language_from_text(text)
        assert lang == "python"

    def test_detect_language_javascript_keywords(self) -> None:
        text = "function foo() { const x = 1; let y = 2; var z = 3; }"
        lang = SkillExtractor._detect_language_from_text(text)
        assert lang == "javascript"

    def test_detect_language_go_keywords(self) -> None:
        text = "func main() { package main }"
        lang = SkillExtractor._detect_language_from_text(text)
        assert lang == "go"

    def test_detect_language_rust_keywords(self) -> None:
        text = "use std::collections::HashMap;"
        lang = SkillExtractor._detect_language_from_text(text)
        assert lang == "rust"

    def test_detect_language_none(self) -> None:
        text = "Just some plain English text without any code keywords."
        lang = SkillExtractor._detect_language_from_text(text)
        assert lang is None

    def test_slugify_section(self) -> None:
        slug = SkillExtractor._slugify_section("My New Skill!")
        assert slug == "my-new-skill"

    def test_slugify_section_empty(self) -> None:
        slug = SkillExtractor._slugify_section("")
        assert slug == ""


class TestSkillExtractorWriteFile:
    def test_write_skill_file_no_output_dir(self) -> None:
        ex = SkillExtractor()
        skill = MagicMock(spec=Skill)
        skill.name = "test"
        template = MagicMock(spec=SkillTemplate)
        template.name = "test-skill"
        template.render.return_value = "---\nname: test\n---\n\ncontent"
        path = ex._write_skill_file(skill, template)
        assert path == Path()

    def test_write_skill_file_with_output_dir(self, tmp_path) -> None:
        ex = SkillExtractor(output_dir=str(tmp_path))
        skill = MagicMock(spec=Skill)
        skill.name = "test"
        template = MagicMock(spec=SkillTemplate)
        template.name = "test-skill"
        template.render.return_value = "---\nname: test\n---\n\ncontent"
        path = ex._write_skill_file(skill, template)
        assert path.exists()
        assert path.read_text() == "---\nname: test\n---\n\ncontent"

    def test_write_skill_file_creates_output_dir(self, tmp_path) -> None:
        subdir = tmp_path / "sub" / "dir"
        ex = SkillExtractor(output_dir=str(subdir))
        skill = MagicMock(spec=Skill)
        skill.name = "test"
        template = MagicMock(spec=SkillTemplate)
        template.name = "nested-skill"
        template.render.return_value = "content"
        path = ex._write_skill_file(skill, template)
        assert path.exists()
