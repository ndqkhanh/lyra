"""
Tests for research analysis engines.
"""

from lyra_research.analysis import (
    PaperAnalyzer,
    QualityScorer,
    RepositoryAnalyzer,
)


def test_paper_analyzer():
    """Test paper analysis."""
    analyzer = PaperAnalyzer()

    paper_content = """
    We propose a novel transformer architecture for natural language processing.
    Our method achieves state-of-the-art results on the GLUE benchmark.
    We evaluate using accuracy, F1 score, and BLEU metrics.
    The code is available on GitHub.
    However, our approach has limitations in low-resource settings.
    """

    metadata = {
        'id': 'test123',
        'title': 'Novel Transformer Architecture',
        'citations': 150,
    }

    analysis = analyzer.analyze(paper_content, metadata)

    assert analysis.paper_id == 'test123'
    assert analysis.title == 'Novel Transformer Architecture'
    assert analysis.citation_count == 150
    assert len(analysis.evaluation_metrics) > 0
    assert analysis.reproducibility_score > 0.0
    assert len(analysis.strengths) > 0


def test_repository_analyzer():
    """Test repository analysis."""
    analyzer = RepositoryAnalyzer()

    repo_metadata = {
        'id': 12345,
        'full_name': 'user/awesome-ml',
        'stars': 5000,
        'forks': 500,
        'open_issues': 20,
        'license': 'MIT',
        'last_commit_days': 15,
    }

    readme = """
    # Awesome ML Library

    ## Installation
    pip install awesome-ml

    ## Usage
    ```python
    import awesome_ml
    model = awesome_ml.Model()
    ```

    ## API Documentation
    See docs/ for full API reference.
    """

    analysis = analyzer.analyze(repo_metadata, readme)

    assert analysis.repo_id == '12345'
    assert analysis.stars == 5000
    assert analysis.has_license
    assert analysis.has_docs
    assert analysis.code_quality_score > 0.0
    assert analysis.documentation_score > 0.0
    assert analysis.is_maintained


def test_quality_scorer_paper():
    """Test quality scoring for papers."""
    from lyra_research.analysis import PaperAnalysis

    scorer = QualityScorer()

    paper = PaperAnalysis(
        paper_id='test',
        title='Deep Learning for NLP',
        citation_count=500,
        reproducibility_score=0.8,
    )

    score = scorer.score_paper(paper, "deep learning NLP")

    assert 0.0 <= score.overall <= 1.0
    assert 0.0 <= score.relevance <= 1.0
    assert 0.0 <= score.authority <= 1.0
    assert score.relevance > 0.5  # Should match query well


def test_quality_scorer_repository():
    """Test quality scoring for repositories."""
    from lyra_research.analysis import RepositoryAnalysis

    scorer = QualityScorer()

    repo = RepositoryAnalysis(
        repo_id='test',
        full_name='user/machine-learning-toolkit',
        stars=10000,
        forks=1000,
        code_quality_score=0.8,
        maintenance_score=0.9,
        last_commit_days=10,
    )

    score = scorer.score_repository(repo, "machine learning")

    assert 0.0 <= score.overall <= 1.0
    assert 0.0 <= score.relevance <= 1.0
    assert 0.0 <= score.authority <= 1.0
    assert score.relevance > 0.5  # Should match query


def test_paper_methodology_extraction():
    """Test methodology extraction."""
    analyzer = PaperAnalyzer()

    content = """
    Methodology: We use a transformer-based approach with attention mechanisms.
    The model is trained on 1M examples using Adam optimizer.
    """

    methodology = analyzer._extract_methodology(content)
    assert len(methodology) > 0
    assert 'methodology' in methodology.lower() or 'transformer' in methodology.lower()


def test_paper_dataset_extraction():
    """Test dataset extraction."""
    analyzer = PaperAnalyzer()

    content = """
    We evaluate on ImageNet, COCO, and MNIST datasets.
    The training dataset contains 100k samples.
    """

    datasets = analyzer._extract_datasets(content)
    assert len(datasets) > 0
    # Should find at least one dataset name


def test_repository_maintenance_score():
    """Test maintenance score calculation."""
    analyzer = RepositoryAnalyzer()

    # Well-maintained repo
    metadata_good = {
        'last_commit_days': 5,
        'open_issues': 10,
        'stars': 1000,
        'contributors': 20,
    }

    score_good = analyzer._calculate_maintenance_score(metadata_good)
    assert score_good > 0.7

    # Poorly maintained repo
    metadata_bad = {
        'last_commit_days': 400,
        'open_issues': 500,
        'stars': 100,
        'contributors': 1,
    }

    score_bad = analyzer._calculate_maintenance_score(metadata_bad)
    assert score_bad < 0.3
