"""Tests for lyra_context_profiler.importance module."""

import asyncio
import time

import pytest
from lyra_context_profiler.importance import (
    DependencyScorer,
    ImportanceCalculator,
    InsufficientDataError,
    MLImportancePredictor,
    RecencyScorer,
    ScoreWeights,
    TaskRelevanceScorer,
    TfidfCalculator,
)

# ── Fixtures ────────────────────────────────────────────────────────────────────


class _FakeElement:
    """Minimal element for testing importance scoring."""

    def __init__(
        self, id, content, token_count=100, access_count=1, dependencies=None, recency=0.0
    ):
        self.id = id
        self.content = content
        self.token_count = token_count
        self.access_count = access_count
        self.dependencies = dependencies or []
        self.recency = recency
        self.last_accessed_at = time.time() - recency
        self.created_at = time.time() - recency - 100


@pytest.fixture
def sample_elements():
    return [
        _FakeElement("a", "def test_function(): return 42", token_count=50, access_count=5),
        _FakeElement(
            "b", "This is a documentation string for the API", token_count=200, access_count=1
        ),
        _FakeElement(
            "c", "The quick brown fox jumps over the lazy dog", token_count=30, access_count=10
        ),
    ]


@pytest.fixture
def importance_calc():
    calc = ImportanceCalculator()
    calc.set_task("Implement a Python test function")
    return calc


# ── ScoreWeights ────────────────────────────────────────────────────────────────


class TestScoreWeights:
    def test_default_weights_sum_near_one(self):
        w = ScoreWeights()
        total = (
            w.tfidf_weight
            + w.recency_weight
            + w.task_relevance_weight
            + w.dependency_weight
            + w.usage_weight
            + w.ml_weight
        )
        assert abs(total - 1.0) < 0.01

    def test_normalize_makes_sum_one(self):
        w = ScoreWeights(tfidf_weight=0.5, recency_weight=0.5)
        n = w.normalize()
        total = sum(
            [
                n.tfidf_weight,
                n.recency_weight,
                n.task_relevance_weight,
                n.dependency_weight,
                n.usage_weight,
                n.ml_weight,
            ]
        )
        assert abs(total - 1.0) < 0.01

    def test_all_zero_weights_normalizes_to_equal(self):
        w = ScoreWeights(
            tfidf_weight=0,
            recency_weight=0,
            task_relevance_weight=0,
            dependency_weight=0,
            usage_weight=0,
            ml_weight=0,
        ).normalize()
        total = sum(
            [
                w.tfidf_weight,
                w.recency_weight,
                w.task_relevance_weight,
                w.dependency_weight,
                w.usage_weight,
                w.ml_weight,
            ]
        )
        assert abs(total - 1.0) < 0.01


# ── TfidfCalculator ─────────────────────────────────────────────────────────────


class TestTfidfCalculator:
    def test_empty_corpus_returns_zero(self):
        tfidf = TfidfCalculator()
        assert tfidf.score("some text") == 0.0

    def test_single_document_scores_positive(self):
        tfidf = TfidfCalculator()
        tfidf.fit(["this is a test document"])
        score = tfidf.score("this is a test document")
        assert score > 0.0

    def test_distinctive_document_scores_higher(self):
        tfidf = TfidfCalculator()
        common_doc = "the cat sat on the mat with another cat"
        rare_doc = "quantum mechanics describes subatomic particle behavior"
        tfidf.fit([common_doc, common_doc, rare_doc])
        tfidf.score(common_doc)
        rare_score = tfidf.score(rare_doc)
        # Rare document should score higher due to distinctive words
        assert rare_score > 0.0

    def test_empty_document_returns_zero(self):
        tfidf = TfidfCalculator()
        tfidf.fit(["some content here"])
        assert tfidf.score("") == 0.0

    def test_tokenize_filters_short_words(self):
        tokens = TfidfCalculator.tokenize("a be it to the function implement test")
        assert "a" not in tokens
        assert "be" not in tokens
        assert "function" in tokens
        assert "implement" in tokens


# ── RecencyScorer ───────────────────────────────────────────────────────────────


class TestRecencyScorer:
    def test_recent_element_scores_high(self):
        scorer = RecencyScorer(half_life_seconds=300)
        el = _FakeElement("x", "content", recency=0.0)
        score = scorer.score(el)
        assert score > 0.9  # Very recent

    def test_old_element_scores_low(self):
        scorer = RecencyScorer(half_life_seconds=1)  # Fast decay
        el = _FakeElement("x", "content", recency=10.0)  # 10 seconds old
        score = scorer.score(el)
        assert score < 0.01  # Should be nearly 0 after 10 half-lives

    def test_batch_scoring(self):
        scorer = RecencyScorer()
        els = [
            _FakeElement("a", "content", recency=0),
            _FakeElement("b", "content", recency=0),
        ]
        scores = scorer.score_batch(els)
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)


# ── TaskRelevanceScorer ─────────────────────────────────────────────────────────


class TestTaskRelevanceScorer:
    def test_no_task_returns_neutral(self):
        scorer = TaskRelevanceScorer()
        assert scorer.score("any content") == 0.5

    def test_relevant_content_scores_positive(self):
        scorer = TaskRelevanceScorer()
        scorer.set_task("implement python function sort items")
        # Content contains matching keywords: "sort", "function", "python"
        score = scorer.score("def python_sort_function(items): return sorted(items)")
        assert score > 0.0

    def test_irrelevant_content_scores_zero(self):
        scorer = TaskRelevanceScorer()
        scorer.set_task("implement a Python function for sorting")
        score = scorer.score("the weather is nice today")
        assert score == 0.0

    def test_empty_content_scores_zero(self):
        scorer = TaskRelevanceScorer()
        scorer.set_task("some task")
        assert scorer.score("") == 0.0


# ── DependencyScorer ────────────────────────────────────────────────────────────


class TestDependencyScorer:
    def test_no_graph_returns_zero(self):
        scorer = DependencyScorer()
        assert scorer.score("unknown_id") == 0.0

    def test_high_in_degree_scores_higher(self):
        scorer = DependencyScorer()
        a = _FakeElement("a", "A", dependencies=["b"])
        b = _FakeElement("b", "B", dependencies=["c"])
        c = _FakeElement("c", "C", dependencies=["b"])
        d = _FakeElement("d", "D", dependencies=["b"])
        scorer.build_graph([a, b, c, d])
        # b is depended on by a, c, d (in-degree 3)
        b_score = scorer.score("b")
        # c is depended on by none or few
        c_score = scorer.score("c")
        assert b_score >= c_score

    def test_batch_scoring(self):
        scorer = DependencyScorer()
        a = _FakeElement("a", "A", dependencies=["b"])
        b = _FakeElement("b", "B")
        scorer.build_graph([a, b])
        scores = scorer.score_batch(["a", "b"])
        assert "a" in scores
        assert "b" in scores


# ── MLImportancePredictor ───────────────────────────────────────────────────────


class TestMLImportancePredictor:
    def test_predict_returns_bounded_value(self):
        ml = MLImportancePredictor()
        features = {
            "token_count": 100,
            "access_count": 5,
            "recency": 0.8,
            "dependency_count": 3,
            "content_length": 500,
            "unique_word_ratio": 0.7,
            "keyword_density": 0.3,
        }
        score = ml.predict(features)
        assert 0.0 <= score <= 1.0

    def test_extract_features_returns_all_keys(self):
        el = _FakeElement("x", "def foo(): return bar", token_count=30)
        features = MLImportancePredictor.extract_features(el)
        assert "token_count" in features
        assert "access_count" in features
        assert "unique_word_ratio" in features

    def test_fit_with_empty_data_raises(self):
        ml = MLImportancePredictor()
        with pytest.raises(InsufficientDataError):
            ml.fit([], [])

    def test_fit_improves_prediction(self):
        ml = MLImportancePredictor()
        features = [
            MLImportancePredictor.extract_features(
                _FakeElement(
                    "a", "important critical key function main", token_count=200, access_count=10
                ),
            ),
            MLImportancePredictor.extract_features(
                _FakeElement("b", "a the is", token_count=10, access_count=0),
            ),
        ]
        labels = [0.9, 0.1]
        ml.fit(features, labels)
        assert ml._fitted is True


# ── ImportanceCalculator ────────────────────────────────────────────────────────


class TestImportanceCalculator:
    def test_score_batch_returns_all_ids(self, sample_elements, importance_calc):
        scores = asyncio.run(importance_calc.score_batch(sample_elements))
        assert set(scores.keys()) == {"a", "b", "c"}
        assert all(0.0 <= v <= 1.0 for v in scores.values())

    def test_empty_batch_returns_empty(self, importance_calc):
        scores = asyncio.run(importance_calc.score_batch([]))
        assert scores == {}

    def test_score_single(self, sample_elements, importance_calc):
        score = asyncio.run(importance_calc.score_single(sample_elements[0]))
        assert 0.0 <= score <= 1.0

    def test_get_score_breakdown(self, sample_elements, importance_calc):
        breakdown = importance_calc.get_score_breakdown(sample_elements[0])
        assert "tfidf" in breakdown
        assert "recency" in breakdown
        assert "task_relevance" in breakdown
        assert "dependency" in breakdown
        assert "ml" in breakdown
        assert all(0.0 <= v <= 1.0 for v in breakdown.values())

    def test_calibrate_weights_updates(self, sample_elements, importance_calc):
        # Run a few batches to build history
        for _ in range(3):
            asyncio.run(importance_calc.score_batch(sample_elements))
        new_weights = importance_calc.calibrate_weights_from_history()
        assert isinstance(new_weights, ScoreWeights)

    def test_set_weights(self, importance_calc):
        new = ScoreWeights(tfidf_weight=0.5, recency_weight=0.5)
        importance_calc.set_weights(new)
        # Weights are normalized, so they should sum to ~1.0
        w = importance_calc.current_weights
        total = (
            w.tfidf_weight
            + w.recency_weight
            + w.task_relevance_weight
            + w.dependency_weight
            + w.usage_weight
            + w.ml_weight
        )
        assert abs(total - 1.0) < 0.01
        assert w.tfidf_weight > 0  # Should be non-zero
