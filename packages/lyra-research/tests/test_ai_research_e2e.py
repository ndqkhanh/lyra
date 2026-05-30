"""
End-to-end tests for complete AI research workflows.

Tests complete paper analysis workflows, code analysis workflows,
and multi-source synthesis workflows.
"""

import pytest
from lyra_research.analysis import PaperAnalyzer, RepositoryAnalyzer, QualityScorer


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteResearchWorkflows:
    """E2E tests for complete research workflows."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    @pytest.fixture
    def quality_scorer(self):
        """Create quality scorer instance."""
        return QualityScorer()

    def test_complete_paper_analysis_workflow(self, paper_analyzer, quality_scorer):
        """Test complete paper analysis workflow from discovery to scoring."""
        # Simulate discovered paper
        paper_content = """
        Abstract: We present AutoResearchClaw, an autonomous research system
        that combines multi-agent coordination with self-healing mechanisms.
        Our approach achieves 92% accuracy on literature review tasks.

        Introduction: Research automation is crucial for handling the growing
        volume of scientific publications. We propose a hierarchical system
        with specialized agents for discovery, analysis, and synthesis.

        Methodology: Our system uses three specialized agents powered by GPT-4
        with learning rate 0.001 and batch size 32. The discovery agent searches
        arXiv, GitHub, and HuggingFace. The analysis agent extracts key findings
        using structured prompts with temperature 0.7. The synthesis agent builds
        knowledge graphs from extracted information. We implement self-healing
        through pivot-refine loops with max 3 iterations and hyperparameters
        tuned on validation set.

        Experiments: We evaluate on 1000 papers from ImageNet, COCO, and MNIST
        datasets across 10 domains. Datasets include CS papers from 2020-2026
        with 70000 training samples. Evaluation metrics are accuracy, precision,
        recall, F1, and synthesis quality score. The dataset split is 70/15/15
        for train/validation/test. Our code is available on GitHub with full
        documentation and reproducible experiments. Implementation details are
        provided in the appendix.

        Results: We find that AutoResearchClaw achieves 92% accuracy on paper
        classification, 88% on key finding extraction, and 85% on synthesis quality.
        The system outperforms GPT-4 baseline by 15%, LangChain by 12%, and
        AutoGPT by 18%. Results show significant improvements in multi-hop reasoning.

        Limitations: However, our approach does not scale well beyond 100 papers
        per session due to context window constraints. The method cannot handle
        non-English papers or papers without abstracts. Although we achieve high
        accuracy, generalization to non-CS domains is limited.

        Conclusion: We demonstrate the effectiveness of multi-agent systems with
        self-healing for autonomous research. Future work includes scaling to
        larger paper collections and supporting multilingual content.
        """

        paper_metadata = {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw: Autonomous Research with Multi-Agent Systems",
            "authors": ["Smith, J.", "Doe, A.", "Johnson, B."],
            "citations": 150,
            "year": 2026,
            "venue": "NeurIPS",
        }

        # Step 1: Analyze paper
        analysis = paper_analyzer.analyze(paper_content, paper_metadata)

        # Verify analysis completeness
        assert analysis.paper_id == "arxiv:2605.20025"
        assert analysis.title != ""
        assert analysis.methodology != ""
        assert len(analysis.datasets_used) > 0
        assert len(analysis.evaluation_metrics) >= 3
        assert len(analysis.key_findings) > 0
        assert 0.0 <= analysis.reproducibility_score <= 1.0
        assert len(analysis.strengths) > 0
        assert len(analysis.limitations) > 0

        # Step 2: Score quality
        quality_score = quality_scorer.score_paper(analysis, "autonomous research")

        # Verify quality scoring
        assert 0.0 <= quality_score.overall <= 1.0
        assert 0.0 <= quality_score.relevance <= 1.0
        assert 0.0 <= quality_score.authority <= 1.0
        assert 0.0 <= quality_score.credibility <= 1.0

        # High-quality paper should have good scores
        assert quality_score.overall > 0.5
        assert quality_score.authority > 0.1  # 150 citations
        assert quality_score.credibility > 0.5  # Has code, details

    def test_complete_code_analysis_workflow(self, repo_analyzer, quality_scorer):
        """Test complete code analysis workflow from discovery to scoring."""
        # Simulate discovered repository
        readme_content = """
        # AutoResearchClaw

        Autonomous research system with multi-agent coordination and self-healing.

        ## Features

        - **Multi-Agent System**: Specialized agents for discovery, analysis, synthesis
        - **Self-Healing**: Automatic error recovery with pivot-refine loops
        - **Multi-Source**: Searches arXiv, GitHub, HuggingFace, Semantic Scholar
        - **Knowledge Graphs**: Builds structured knowledge from papers
        - **Cost Optimization**: Intelligent model routing (DeepSeek, Claude, GPT-4)

        ## Installation

        ```bash
        pip install autoresearchclaw
        ```

        ## Quick Start

        ```python
        from autoresearchclaw import ResearchOrchestrator

        orchestrator = ResearchOrchestrator()
        results = orchestrator.research("LLM agents", depth="deep")
        ```

        ## Architecture

        The system consists of:
        - Discovery Agent: Multi-source paper/repo discovery
        - Analysis Agent: Extract findings and techniques
        - Synthesis Agent: Build knowledge graphs
        - Orchestrator: Coordinate agents and handle errors

        ## Documentation

        Full API documentation available at docs.autoresearchclaw.com

        ## Testing

        ```bash
        pytest tests/ --cov=src --cov-report=html
        ```

        ## License

        MIT License - see LICENSE file for details.
        """

        repo_metadata = {
            "id": "12345",
            "full_name": "org/autoresearchclaw",
            "stars": 5000,
            "forks": 800,
            "open_issues": 45,
            "language": "Python",
            "license": {"name": "MIT"},
            "has_wiki": True,
            "has_pages": True,
            "contributors": 25,
            "last_commit_days": 5,
        }

        # Step 1: Analyze repository
        analysis = repo_analyzer.analyze(repo_metadata, readme_content)

        # Verify analysis completeness
        assert analysis.repo_id == "12345"
        assert analysis.full_name == "org/autoresearchclaw"
        assert analysis.stars == 5000
        assert analysis.has_license is True
        assert analysis.has_docs is True
        assert 0.0 <= analysis.code_quality_score <= 1.0
        assert 0.0 <= analysis.documentation_score <= 1.0
        assert 0.0 <= analysis.maintenance_score <= 1.0
        assert len(analysis.strengths) > 0

        # Step 2: Score quality
        quality_score = quality_scorer.score_repository(analysis, "autonomous research")

        # Verify quality scoring
        assert 0.0 <= quality_score.overall <= 1.0
        assert 0.0 <= quality_score.relevance <= 1.0
        assert 0.0 <= quality_score.authority <= 1.0
        assert 0.0 <= quality_score.credibility <= 1.0

        # High-quality repo should have good scores
        assert quality_score.overall > 0.5
        assert quality_score.authority > 0.3  # 5000 stars
        assert quality_score.recency > 0.9  # Recent commit

    def test_multi_source_synthesis_workflow(self, paper_analyzer, repo_analyzer, quality_scorer):
        """Test synthesizing insights from multiple papers and repositories."""
        # Paper 1: Theoretical foundation
        paper1_content = """
        We propose a theoretical framework for multi-agent coordination.
        The approach uses game theory and reinforcement learning.
        """
        paper1_metadata = {
            "id": "arxiv:001",
            "title": "Multi-Agent Coordination Theory",
            "citations": 300,
        }

        # Paper 2: Practical implementation
        paper2_content = """
        We implement multi-agent systems using actor-critic methods.
        Experiments show 85% success rate on coordination tasks.
        """
        paper2_metadata = {
            "id": "arxiv:002",
            "title": "Practical Multi-Agent Systems",
            "citations": 200,
        }

        # Repository: Open-source implementation
        readme = """
        # Multi-Agent Framework

        Production-ready implementation of multi-agent coordination.
        Includes pre-trained models and evaluation benchmarks.
        """
        repo_metadata = {
            "id": "repo001",
            "full_name": "org/multi-agent-framework",
            "stars": 3000,
            "language": "Python",
        }

        # Analyze all sources
        paper1_analysis = paper_analyzer.analyze(paper1_content, paper1_metadata)
        paper2_analysis = paper_analyzer.analyze(paper2_content, paper2_metadata)
        repo_analysis = repo_analyzer.analyze(repo_metadata, readme)

        # Score all sources
        paper1_score = quality_scorer.score_paper(paper1_analysis, "multi-agent coordination")
        paper2_score = quality_scorer.score_paper(paper2_analysis, "multi-agent coordination")
        repo_score = quality_scorer.score_repository(repo_analysis, "multi-agent coordination")

        # Verify all sources analyzed
        assert paper1_analysis.paper_id == "arxiv:001"
        assert paper2_analysis.paper_id == "arxiv:002"
        assert repo_analysis.repo_id == "repo001"

        # Verify quality scores
        assert paper1_score.overall > 0.0
        assert paper2_score.overall > 0.0
        assert repo_score.overall > 0.0

        # Paper 1 should have higher authority (more citations)
        assert paper1_score.authority > paper2_score.authority


@pytest.mark.e2e
@pytest.mark.slow
class TestResearchQualityAssessment:
    """E2E tests for research quality assessment."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    @pytest.fixture
    def quality_scorer(self):
        """Create quality scorer instance."""
        return QualityScorer()

    def test_assess_high_quality_paper(self, paper_analyzer, quality_scorer):
        """Test assessing a high-quality research paper."""
        content = """
        We present a novel approach published at NeurIPS 2026.
        Our code is available on GitHub with full documentation.
        We provide hyperparameters, dataset splits, and evaluation protocols.
        Experiments on ImageNet, COCO, and MNIST show state-of-the-art results.
        We achieve 95% accuracy, outperforming all baselines by 10%.
        """

        metadata = {
            "id": "arxiv:high-quality",
            "title": "High Quality Research",
            "citations": 500,
            "venue": "NeurIPS",
        }

        analysis = paper_analyzer.analyze(content, metadata)
        score = quality_scorer.score_paper(analysis, "machine learning")

        # High-quality indicators
        assert analysis.reproducibility_score >= 0.5
        assert len(analysis.strengths) >= 2
        assert score.overall > 0.4
        assert score.authority > 0.3  # High citations
        assert score.credibility > 0.5  # High reproducibility

    def test_assess_low_quality_paper(self, paper_analyzer, quality_scorer):
        """Test assessing a low-quality research paper."""
        content = """
        We propose a method. Results are good.
        """

        metadata = {
            "id": "arxiv:low-quality",
            "title": "Low Quality Research",
            "citations": 5,
        }

        analysis = paper_analyzer.analyze(content, metadata)
        score = quality_scorer.score_paper(analysis, "machine learning")

        # Low-quality indicators
        assert analysis.reproducibility_score < 0.3
        assert len(analysis.key_findings) <= 2
        assert score.overall < 0.5
        assert score.authority < 0.1  # Low citations
        assert score.credibility < 0.3  # Low reproducibility

    def test_assess_reproducibility_spectrum(self, paper_analyzer):
        """Test assessing papers across reproducibility spectrum."""
        # High reproducibility
        high_repro = """
        Code: github.com/org/repo
        Hyperparameters: lr=0.001, batch=32
        Dataset split: 80/10/10
        Implementation details in appendix
        """
        high_metadata = {"id": "high", "title": "High Repro", "citations": 100}
        high_analysis = paper_analyzer.analyze(high_repro, high_metadata)

        # Low reproducibility
        low_repro = "We trained a model and got good results."
        low_metadata = {"id": "low", "title": "Low Repro", "citations": 100}
        low_analysis = paper_analyzer.analyze(low_repro, low_metadata)

        # Verify reproducibility scores
        assert high_analysis.reproducibility_score > 0.7
        assert low_analysis.reproducibility_score < 0.3
        assert high_analysis.reproducibility_score > low_analysis.reproducibility_score


@pytest.mark.e2e
@pytest.mark.slow
class TestCrossSourceValidation:
    """E2E tests for validating claims across sources."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    def test_validate_paper_claims_with_code(self, paper_analyzer, repo_analyzer):
        """Test validating paper claims against code implementation."""
        # Paper claims
        paper_content = """
        Our method achieves 95% accuracy on ImageNet.
        The implementation is available on GitHub.
        We provide pre-trained models and evaluation scripts.
        """
        paper_metadata = {
            "id": "arxiv:claims",
            "title": "High Accuracy Method",
            "citations": 200,
        }

        # Repository implementation
        readme = """
        # High Accuracy Method Implementation

        Reproduces results from the paper.
        Pre-trained models available.
        Evaluation scripts included.

        ## Results
        - ImageNet accuracy: 94.8% (paper reports 95%)
        """
        repo_metadata = {
            "id": "repo:impl",
            "full_name": "org/high-accuracy",
            "stars": 2000,
            "language": "Python",
        }

        paper_analysis = paper_analyzer.analyze(paper_content, paper_metadata)
        repo_analysis = repo_analyzer.analyze(repo_metadata, readme)

        # Paper should have reproducibility score calculated
        assert paper_analysis.reproducibility_score >= 0.0

        # Repository should be analyzed
        assert repo_analysis.code_quality_score >= 0.0

    def test_identify_missing_implementations(self, paper_analyzer, repo_analyzer):
        """Test identifying papers without code implementations."""
        # Paper without code
        paper_content = """
        We propose a novel architecture with three components.
        Experiments show promising results.
        """
        paper_metadata = {
            "id": "arxiv:no-code",
            "title": "Novel Architecture",
            "citations": 50,
        }

        paper_analysis = paper_analyzer.analyze(paper_content, paper_metadata)

        # Should have low reproducibility
        assert paper_analysis.reproducibility_score < 0.5

    def test_compare_multiple_implementations(self, repo_analyzer):
        """Test comparing multiple implementations of same paper."""
        # Official implementation
        official_readme = """
        # Official Implementation

        Authors' implementation with pre-trained models.
        Reproduces all paper results.
        """
        official_metadata = {
            "id": "official",
            "full_name": "authors/official",
            "stars": 5000,
            "language": "Python",
        }

        # Community implementation
        community_readme = """
        # Community Implementation

        Unofficial PyTorch implementation.
        Partial results reproduction.
        """
        community_metadata = {
            "id": "community",
            "full_name": "community/unofficial",
            "stars": 1000,
            "language": "Python",
        }

        official_analysis = repo_analyzer.analyze(official_metadata, official_readme)
        community_analysis = repo_analyzer.analyze(community_metadata, community_readme)

        # Official should have higher quality scores
        assert official_analysis.stars > community_analysis.stars
        assert official_analysis.code_quality_score >= community_analysis.code_quality_score
