"""
Unit tests for paper parsing and structure extraction.

Tests paper analysis, methodology extraction, dataset identification,
and technique extraction from research papers.
"""

import pytest
from lyra_research.analysis import PaperAnalyzer, PaperAnalysis


class TestPaperParsing:
    """Test paper parsing and structure extraction."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    @pytest.fixture
    def sample_paper_content(self):
        """Sample paper content for testing."""
        return """
        Abstract: We present a novel approach to multi-agent coordination
        using reinforcement learning. Our method achieves state-of-the-art
        performance on benchmark tasks.

        Methodology: We propose a hierarchical multi-agent system where
        agents learn to coordinate through shared rewards. The approach
        uses PPO for policy optimization with learning rate 0.001 and
        batch size 32.

        Experiments: We evaluate on ImageNet and COCO datasets using
        accuracy, precision, and F1 metrics. The dataset split is 80/10/10
        for training, validation, and test sets. Results show our method
        outperforms baselines by 15%. We achieve 92% accuracy on ImageNet.

        Implementation: Our code is available on GitHub with full documentation.
        We provide hyperparameters and experimental setup details in the appendix.

        Limitations: However, our approach does not scale well to more
        than 10 agents. The method cannot handle dynamic environments.
        """

    @pytest.fixture
    def sample_metadata(self):
        """Sample paper metadata."""
        return {
            "id": "arxiv:2605.20025",
            "title": "Multi-Agent Coordination via RL",
            "authors": ["Smith, J.", "Doe, A."],
            "citations": 150,
            "year": 2026,
            "venue": "NeurIPS",
        }

    def test_parse_paper_basic(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test basic paper parsing."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert isinstance(analysis, PaperAnalysis)
        assert analysis.paper_id == "arxiv:2605.20025"
        assert analysis.title == "Multi-Agent Coordination via RL"
        assert analysis.citation_count == 150

    def test_extract_methodology(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test methodology extraction."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert analysis.methodology != ""
        assert "hierarchical" in analysis.methodology.lower() or "multi-agent" in analysis.methodology.lower()

    def test_extract_datasets(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test dataset extraction."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert len(analysis.datasets_used) > 0
        assert any("imagenet" in d.lower() for d in analysis.datasets_used) or \
               any("coco" in d.lower() for d in analysis.datasets_used)

    def test_extract_metrics(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test evaluation metrics extraction."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert len(analysis.evaluation_metrics) > 0
        # Should find accuracy, precision, or F1
        metrics_lower = [m.lower() for m in analysis.evaluation_metrics]
        assert any(m in ["accuracy", "precision", "f1"] for m in metrics_lower)

    def test_extract_findings(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test key findings extraction."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert len(analysis.key_findings) > 0
        # Should extract result statements
        findings_text = " ".join(analysis.key_findings).lower()
        assert "outperform" in findings_text or "achieve" in findings_text

    def test_assess_reproducibility(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test reproducibility assessment."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert 0.0 <= analysis.reproducibility_score <= 1.0
        # Sample content has hyperparameters and dataset details, should score > 0
        assert analysis.reproducibility_score > 0.0

    def test_identify_strengths(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test strength identification."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert len(analysis.strengths) > 0
        # High citation count should be identified
        strengths_text = " ".join(analysis.strengths).lower()
        assert "cited" in strengths_text or "performance" in strengths_text

    def test_identify_limitations(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test limitation identification."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        assert len(analysis.limitations) > 0
        # Should extract limitation statements
        limitations_text = " ".join(analysis.limitations).lower()
        assert "does not" in limitations_text or "cannot" in limitations_text

    def test_detect_biases(self, paper_analyzer, sample_paper_content, sample_metadata):
        """Test bias detection."""
        analysis = paper_analyzer.analyze(sample_paper_content, sample_metadata)

        # May or may not detect biases depending on content
        assert isinstance(analysis.potential_biases, list)
        assert len(analysis.potential_biases) <= 3

    def test_parse_paper_empty_content(self, paper_analyzer, sample_metadata):
        """Test parsing with empty content."""
        analysis = paper_analyzer.analyze("", sample_metadata)

        assert isinstance(analysis, PaperAnalysis)
        assert analysis.paper_id == sample_metadata["id"]
        # Should handle gracefully with empty lists
        assert isinstance(analysis.key_findings, list)

    def test_parse_paper_minimal_metadata(self, paper_analyzer, sample_paper_content):
        """Test parsing with minimal metadata."""
        minimal_metadata = {"id": "test:001", "title": "Test Paper"}
        analysis = paper_analyzer.analyze(sample_paper_content, minimal_metadata)

        assert analysis.paper_id == "test:001"
        assert analysis.citation_count == 0  # Default value

    def test_extract_multiple_datasets(self, paper_analyzer, sample_metadata):
        """Test extracting multiple datasets."""
        content = """
        We evaluate on ImageNet, COCO, MNIST, CIFAR-10, and SQuAD datasets.
        Additional experiments use GLUE and SuperGLUE benchmarks.
        """
        analysis = paper_analyzer.analyze(content, sample_metadata)

        assert len(analysis.datasets_used) >= 3
        # Should extract at least some of the mentioned datasets

    def test_extract_multiple_metrics(self, paper_analyzer, sample_metadata):
        """Test extracting multiple metrics."""
        content = """
        We measure accuracy, precision, recall, F1 score, BLEU, ROUGE,
        perplexity, AUC, top-1, top-5, mAP, and IoU.
        """
        analysis = paper_analyzer.analyze(content, sample_metadata)

        assert len(analysis.evaluation_metrics) >= 5

    def test_reproducibility_with_code(self, paper_analyzer, sample_metadata):
        """Test reproducibility score with code availability."""
        content = """
        Our code is available on GitHub at github.com/org/repo.
        We provide hyperparameters: learning rate 0.001, batch size 32.
        The dataset split is 80/10/10 for train/val/test.
        Implementation details are in the appendix.
        """
        analysis = paper_analyzer.analyze(content, sample_metadata)

        # Should have high reproducibility score
        assert analysis.reproducibility_score >= 0.8

    def test_reproducibility_without_code(self, paper_analyzer, sample_metadata):
        """Test reproducibility score without code."""
        content = """
        We present a novel approach. Results are shown in Table 1.
        """
        analysis = paper_analyzer.analyze(content, sample_metadata)

        # Should have low reproducibility score
        assert analysis.reproducibility_score < 0.5

    def test_strength_high_citations(self, paper_analyzer, sample_metadata):
        """Test strength identification for highly cited papers."""
        sample_metadata["citations"] = 500
        content = "Novel approach with state-of-the-art results."
        analysis = paper_analyzer.analyze(content, sample_metadata)

        strengths_text = " ".join(analysis.strengths).lower()
        assert "cited" in strengths_text

    def test_limitation_extraction_from_section(self, paper_analyzer, sample_metadata):
        """Test extracting limitations from dedicated section."""
        content = """
        Limitations: Our approach has several limitations. First, it requires
        large amounts of training data. Second, it does not generalize well
        to out-of-distribution examples.
        """
        analysis = paper_analyzer.analyze(content, sample_metadata)

        assert len(analysis.limitations) > 0
        limitations_text = " ".join(analysis.limitations).lower()
        assert "limitation" in limitations_text or "does not" in limitations_text


class TestPaperStructureExtraction:
    """Test extracting structured information from papers."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    def test_extract_methodology_patterns(self, paper_analyzer):
        """Test methodology extraction with various patterns."""
        test_cases = [
            ("Methodology: We propose a novel architecture for deep learning.", True),
            ("We present a new method using transformers for NLP tasks.", True),
            ("The approach is based on reinforcement learning principles.", True),
            ("Random text without methodology keywords here.", False),
        ]

        for content, should_extract in test_cases:
            metadata = {"id": "test", "title": "Test"}
            analysis = paper_analyzer.analyze(content, metadata)

            if should_extract:
                assert analysis.methodology != "", f"Failed to extract from: {content}"

    def test_extract_dataset_patterns(self, paper_analyzer):
        """Test dataset extraction with various patterns."""
        content = """
        We use the ImageNet dataset for classification.
        Experiments on COCO show improvements.
        The MNIST corpus is used for validation.
        """
        metadata = {"id": "test", "title": "Test"}
        analysis = paper_analyzer.analyze(content, metadata)

        datasets_lower = [d.lower() for d in analysis.datasets_used]
        assert any("imagenet" in d for d in datasets_lower)

    def test_extract_findings_patterns(self, paper_analyzer):
        """Test findings extraction with various patterns."""
        content = """
        We find that our method improves accuracy by 10%.
        Results show significant improvements over baselines.
        Our approach achieves 95% accuracy on the test set.
        The system outperforms all prior work.
        """
        metadata = {"id": "test", "title": "Test"}
        analysis = paper_analyzer.analyze(content, metadata)

        assert len(analysis.key_findings) > 0
        findings_text = " ".join(analysis.key_findings).lower()
        assert any(keyword in findings_text for keyword in ["find", "show", "achieve", "outperform"])


@pytest.mark.integration
class TestPaperParsingIntegration:
    """Integration tests for paper parsing with real-world scenarios."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    def test_parse_complete_paper(self, paper_analyzer):
        """Test parsing a complete paper structure."""
        content = """
        Abstract: We present AutoResearchClaw, an autonomous research system
        that uses multi-agent coordination for literature review.

        Introduction: Research automation is crucial for handling the growing
        volume of scientific literature.

        Methodology: We propose a hierarchical multi-agent system with three
        specialized agents: discovery, analysis, and synthesis. Each agent
        uses GPT-4 with temperature 0.7 and learning rate 0.001. We implement
        self-healing mechanisms using pivot-refine loops with batch size 32.

        Experiments: We evaluate on 1000 research papers from ImageNet, COCO,
        and MNIST datasets using accuracy, precision, recall, and F1 metrics.
        The dataset split is 70/15/15 for train/val/test with 50000 training
        samples. Our code is available on GitHub with full implementation details.

        Results: We find that AutoResearchClaw achieves 92% accuracy on
        paper classification. The system outperforms baselines by 15%.
        Results show significant improvements in synthesis quality.

        Limitations: However, our approach does not scale well beyond 100
        papers per session. The method cannot handle non-English papers.
        Although we achieve high accuracy, generalization to other domains
        is limited.

        Conclusion: We demonstrate the effectiveness of multi-agent systems
        for research automation.
        """

        metadata = {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw: Autonomous Research System",
            "citations": 150,
            "year": 2026,
            "venue": "NeurIPS",
        }

        analysis = paper_analyzer.analyze(content, metadata)

        # Verify all components extracted
        assert analysis.methodology != ""
        assert len(analysis.datasets_used) > 0
        assert len(analysis.evaluation_metrics) >= 3
        assert len(analysis.key_findings) > 0
        assert analysis.reproducibility_score > 0.5
        assert len(analysis.strengths) > 0
        assert len(analysis.limitations) > 0

    def test_parse_paper_with_missing_sections(self, paper_analyzer):
        """Test parsing paper with missing sections."""
        content = """
        Abstract: A novel approach to machine learning.

        Results: We achieve 85% accuracy.
        """

        metadata = {"id": "test:001", "title": "Test Paper", "citations": 10}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should handle gracefully
        assert isinstance(analysis, PaperAnalysis)
        assert len(analysis.key_findings) > 0
        # Methodology may be empty or extracted from abstract
        assert isinstance(analysis.methodology, str)
