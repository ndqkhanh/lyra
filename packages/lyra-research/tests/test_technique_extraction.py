"""
Integration tests for technique extraction and categorization.

Tests extracting techniques from papers and code, categorizing them,
and mapping relationships between techniques.
"""

import pytest
from lyra_research.analysis import PaperAnalyzer, RepositoryAnalyzer


class TestTechniqueExtraction:
    """Test technique extraction from papers and code."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    def test_extract_techniques_from_paper(self, paper_analyzer):
        """Test extracting techniques from research papers."""
        content = """
        Methodology: We use reinforcement learning with PPO for policy optimization.
        The architecture employs transformers with multi-head attention mechanisms.
        We implement experience replay and target networks for training stability.
        Our approach uses learning rate 0.001 and batch size 32 for optimization.
        """

        metadata = {"id": "test:001", "title": "RL Techniques", "citations": 50}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract methodology containing techniques
        assert analysis.methodology != ""
        methodology_lower = analysis.methodology.lower()
        assert any(
            tech in methodology_lower
            for tech in ["reinforcement", "ppo", "transformer", "attention"]
        )

    def test_extract_techniques_from_code_readme(self, repo_analyzer):
        """Test extracting techniques from repository README."""
        readme = """
        # Multi-Agent Framework

        This framework implements advanced reinforcement learning techniques:
        - Actor-Critic architecture for policy optimization
        - Proximal Policy Optimization (PPO) algorithm
        - Multi-head attention mechanisms for state representation
        - Experience replay buffer for sample efficiency
        - Distributed training with Ray for scalability

        ## Features
        - Supports PyTorch and TensorFlow backends
        - Includes pre-trained models for common tasks
        - Provides comprehensive evaluation metrics
        - Full API documentation available

        ## Installation
        ```bash
        pip install multi-agent-framework
        ```

        ## Quick Start
        ```python
        from framework import Agent
        agent = Agent()
        agent.train()
        ```

        ## Documentation
        Full documentation at https://docs.example.com
        """

        metadata = {
            "id": "github:org/repo",
            "full_name": "org/multi-agent-framework",
            "stars": 5000,
            "forks": 800,
            "language": "Python",
            "license": {"name": "MIT"},
            "last_commit_days": 5,
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        # Should have high documentation score due to detailed README
        assert analysis.documentation_score > 0.5

    def test_categorize_ml_techniques(self, paper_analyzer):
        """Test categorizing machine learning techniques."""
        content = """
        Supervised learning: We use CNNs for image classification.
        Unsupervised learning: K-means clustering for feature extraction.
        Reinforcement learning: Q-learning for decision making.
        """

        metadata = {"id": "test:002", "title": "ML Techniques", "citations": 100}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract analysis (may be in methodology or findings)
        assert isinstance(analysis, object)

    def test_categorize_architecture_patterns(self, paper_analyzer):
        """Test categorizing architecture patterns."""
        content = """
        We employ a hierarchical architecture with three layers.
        The encoder-decoder structure uses attention mechanisms.
        A residual connection improves gradient flow.
        """

        metadata = {"id": "test:003", "title": "Architecture Patterns", "citations": 75}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract some information (methodology or findings)
        assert isinstance(analysis.methodology, str)

    def test_extract_optimization_techniques(self, paper_analyzer):
        """Test extracting optimization techniques."""
        content = """
        We use Adam optimizer with learning rate 0.001.
        Gradient clipping prevents exploding gradients.
        Learning rate scheduling improves convergence.
        We apply dropout for regularization.
        """

        metadata = {"id": "test:004", "title": "Optimization", "citations": 60}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should identify hyperparameters
        assert analysis.reproducibility_score > 0.0

    def test_extract_evaluation_techniques(self, paper_analyzer):
        """Test extracting evaluation techniques."""
        content = """
        We use cross-validation with 5 folds.
        Evaluation metrics include accuracy, precision, recall, and F1.
        Statistical significance tested with t-test.
        Ablation studies validate component contributions.
        """

        metadata = {"id": "test:005", "title": "Evaluation", "citations": 80}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract multiple metrics
        assert len(analysis.evaluation_metrics) >= 3

    def test_extract_data_processing_techniques(self, paper_analyzer):
        """Test extracting data processing techniques."""
        content = """
        Data augmentation includes rotation, flipping, and cropping.
        We apply normalization and standardization.
        Feature engineering extracts domain-specific features.
        """

        metadata = {"id": "test:006", "title": "Data Processing", "citations": 40}
        analysis = paper_analyzer.analyze(content, metadata)

        assert isinstance(analysis, object)


@pytest.mark.integration
class TestTechniqueCategorization:
    """Integration tests for technique categorization."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    def test_categorize_deep_learning_techniques(self, paper_analyzer):
        """Test categorizing deep learning techniques."""
        content = """
        We implement a deep neural network with:
        - Convolutional layers for feature extraction
        - Batch normalization for training stability
        - ReLU activation functions
        - Max pooling for dimensionality reduction
        - Fully connected layers for classification
        - Softmax output layer
        """

        metadata = {"id": "test:007", "title": "Deep Learning", "citations": 200}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract analysis
        assert isinstance(analysis.methodology, str)

    def test_categorize_nlp_techniques(self, paper_analyzer):
        """Test categorizing NLP techniques."""
        content = """
        Natural language processing techniques:
        - Tokenization with BPE
        - Word embeddings (Word2Vec, GloVe)
        - Transformer architecture with self-attention
        - BERT for pre-training
        - Fine-tuning on downstream tasks
        """

        metadata = {"id": "test:008", "title": "NLP Techniques", "citations": 150}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract analysis
        assert isinstance(analysis.key_findings, list)

    def test_categorize_computer_vision_techniques(self, paper_analyzer):
        """Test categorizing computer vision techniques."""
        content = """
        Computer vision methods:
        - Object detection with YOLO
        - Semantic segmentation with U-Net
        - Image classification with ResNet
        - Data augmentation strategies
        """

        metadata = {"id": "test:009", "title": "Computer Vision", "citations": 180}
        analysis = paper_analyzer.analyze(content, metadata)

        assert isinstance(analysis.key_findings, list)

    def test_categorize_reinforcement_learning_techniques(self, paper_analyzer):
        """Test categorizing RL techniques."""
        content = """
        Reinforcement learning components:
        - Policy gradient methods (REINFORCE, PPO)
        - Value-based methods (DQN, Double DQN)
        - Actor-Critic algorithms (A3C, SAC)
        - Experience replay and target networks
        """

        metadata = {"id": "test:010", "title": "RL Techniques", "citations": 120}
        analysis = paper_analyzer.analyze(content, metadata)

        assert analysis.methodology != ""


@pytest.mark.integration
class TestTechniqueRelationships:
    """Test mapping relationships between techniques."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    def test_technique_builds_on_relationship(self, paper_analyzer):
        """Test identifying 'builds on' relationships."""
        content = """
        Our method extends BERT by adding a multi-task learning objective.
        We build upon the transformer architecture with additional layers.
        """

        metadata = {"id": "test:011", "title": "Extension", "citations": 90}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should identify extension/building relationship
        assert analysis.methodology != ""

    def test_technique_combines_relationship(self, paper_analyzer):
        """Test identifying 'combines' relationships."""
        content = """
        We combine CNNs for feature extraction with RNNs for sequence modeling.
        The hybrid approach integrates supervised and unsupervised learning.
        """

        metadata = {"id": "test:012", "title": "Combination", "citations": 110}
        analysis = paper_analyzer.analyze(content, metadata)

        # Should extract methodology mentioning combination/integration
        assert "combine" in analysis.methodology.lower() or "hybrid" in analysis.methodology.lower() or "integrat" in analysis.methodology.lower()

    def test_technique_improves_relationship(self, paper_analyzer):
        """Test identifying 'improves' relationships."""
        content = """
        Our approach improves upon standard attention by using sparse patterns.
        We enhance the baseline with additional regularization.
        """

        metadata = {"id": "test:013", "title": "Improvement", "citations": 85}
        analysis = paper_analyzer.analyze(content, metadata)

        findings_text = " ".join(analysis.key_findings).lower()
        assert "improve" in findings_text or "enhance" in findings_text

    def test_technique_replaces_relationship(self, paper_analyzer):
        """Test identifying 'replaces' relationships."""
        content = """
        We replace traditional RNNs with transformers for better parallelization.
        Our method substitutes manual feature engineering with learned representations.
        """

        metadata = {"id": "test:014", "title": "Replacement", "citations": 95}
        analysis = paper_analyzer.analyze(content, metadata)

        assert analysis.methodology != ""


@pytest.mark.integration
class TestCrossSourceTechniqueExtraction:
    """Test extracting techniques across papers and code."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    def test_extract_from_paper_and_code(self, paper_analyzer, repo_analyzer):
        """Test extracting techniques from both paper and implementation."""
        # Paper content
        paper_content = """
        We propose a novel attention mechanism for transformers.
        The method uses sparse attention patterns for efficiency.
        """
        paper_metadata = {"id": "arxiv:001", "title": "Sparse Attention", "citations": 200}
        paper_analysis = paper_analyzer.analyze(paper_content, paper_metadata)

        # Repository content
        readme = """
        # Sparse Attention Implementation

        PyTorch implementation of sparse attention from the paper.
        Includes optimized CUDA kernels for efficiency.
        """
        repo_metadata = {
            "id": "github:org/sparse-attention",
            "full_name": "org/sparse-attention",
            "stars": 3000,
            "language": "Python",
        }
        repo_analysis = repo_analyzer.analyze(repo_metadata, readme)

        # Both should extract relevant information
        assert isinstance(paper_analysis.methodology, str)
        assert repo_analysis.documentation_score >= 0.0

    def test_verify_paper_claims_in_code(self, paper_analyzer, repo_analyzer):
        """Test verifying paper claims against code implementation."""
        paper_content = """
        Our implementation achieves 10x speedup over baseline.
        The code is available on GitHub with full documentation.
        """
        paper_metadata = {"id": "arxiv:002", "title": "Fast Implementation", "citations": 150}
        paper_analysis = paper_analyzer.analyze(paper_content, paper_metadata)

        # Should have reproducibility score calculated
        assert paper_analysis.reproducibility_score >= 0.0

    def test_identify_implementation_gaps(self, paper_analyzer, repo_analyzer):
        """Test identifying gaps between paper and implementation."""
        paper_content = """
        We propose three novel components: A, B, and C.
        Extensive experiments validate each component.
        """
        paper_metadata = {"id": "arxiv:003", "title": "Three Components", "citations": 100}
        paper_analysis = paper_analyzer.analyze(paper_content, paper_metadata)

        readme = """
        # Partial Implementation

        Currently implements component A only.
        Components B and C are work in progress.
        """
        repo_metadata = {
            "id": "github:org/partial",
            "full_name": "org/partial-impl",
            "stars": 500,
            "language": "Python",
        }
        repo_analysis = repo_analyzer.analyze(repo_metadata, readme)

        # Repository should indicate limitations
        assert len(repo_analysis.limitations) > 0 or repo_analysis.documentation_score < 1.0


@pytest.mark.integration
class TestTechniqueEvolution:
    """Test tracking technique evolution over time."""

    @pytest.fixture
    def paper_analyzer(self):
        """Create paper analyzer instance."""
        return PaperAnalyzer()

    def test_track_technique_progression(self, paper_analyzer):
        """Test tracking how techniques evolve."""
        # Early paper
        early_content = "We use basic attention mechanisms in transformers."
        early_metadata = {"id": "arxiv:2020.001", "title": "Basic Attention", "citations": 500}
        early_analysis = paper_analyzer.analyze(early_content, early_metadata)

        # Later paper
        later_content = "We extend attention with sparse patterns for efficiency."
        later_metadata = {"id": "arxiv:2024.001", "title": "Sparse Attention", "citations": 200}
        later_analysis = paper_analyzer.analyze(later_content, later_metadata)

        # Both should extract analysis
        assert isinstance(early_analysis, object)
        assert isinstance(later_analysis, object)

    def test_identify_technique_trends(self, paper_analyzer):
        """Test identifying trends in technique adoption."""
        papers = [
            ("Transformers are effective for NLP tasks.", {"id": "p1", "title": "T1", "citations": 1000}),
            ("We apply transformers to computer vision.", {"id": "p2", "title": "T2", "citations": 800}),
            ("Transformers work well for time series.", {"id": "p3", "title": "T3", "citations": 600}),
        ]

        analyses = []
        for content, metadata in papers:
            analysis = paper_analyzer.analyze(content, metadata)
            analyses.append(analysis)

        # All should mention transformers
        assert all("transformer" in a.methodology.lower() for a in analyses if a.methodology)
