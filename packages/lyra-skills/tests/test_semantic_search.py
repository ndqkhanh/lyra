"""Tests for semantic skill search."""
import numpy as np
import pytest
from pathlib import Path
from dataclasses import dataclass

from lyra_skills.semantic_search import (
    SkillEmbedder,
    EmbeddingCache,
    SemanticSkillSearch,
    SearchResult,
    is_semantic_search_available,
)


# Mock skill object
@dataclass
class MockSkill:
    id: str
    name: str
    description: str
    tags: list[str]
    category: str


@pytest.fixture
def sample_skills():
    """Sample skills for testing."""
    return [
        MockSkill(
            id="tdd-discipline",
            name="TDD Discipline",
            description="Test-driven development with red-green-refactor cycle",
            tags=["testing", "tdd", "unit-tests"],
            category="testing"
        ),
        MockSkill(
            id="code-review",
            name="Code Review",
            description="Systematic code review checklist for quality assurance",
            tags=["review", "quality", "checklist"],
            category="quality"
        ),
        MockSkill(
            id="refactoring",
            name="Safe Refactoring",
            description="Refactor code safely with tests as safety net",
            tags=["refactoring", "testing", "safety"],
            category="maintenance"
        ),
    ]


@pytest.fixture
def embedder():
    """Create embedder (skip if dependencies not installed)."""
    if not is_semantic_search_available():
        pytest.skip("sentence-transformers not installed")
    return SkillEmbedder()


@pytest.fixture
def cache(tmp_path):
    """Create temporary cache."""
    cache_path = tmp_path / "embeddings.json"
    return EmbeddingCache(cache_path)


@pytest.fixture
def searcher(embedder, cache):
    """Create search engine."""
    return SemanticSkillSearch(embedder, cache)


# ---------------------------------------------------------------------------
# Embedding Tests
# ---------------------------------------------------------------------------


def test_embedding_generation(embedder):
    """Test basic embedding generation."""
    text = "test description"
    embedding = embedder.encode(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)  # all-MiniLM-L6-v2 dimension
    assert embedding.dtype == np.float32


def test_batch_embedding(embedder):
    """Test batch embedding generation."""
    texts = ["first text", "second text", "third text"]
    embeddings = embedder.encode_batch(texts)

    assert embeddings.shape == (3, 384)
    assert embeddings.dtype == np.float32


def test_embedding_similarity(embedder):
    """Test that similar texts have high similarity."""
    emb1 = embedder.encode("write unit tests")
    emb2 = embedder.encode("create test cases")
    emb3 = embedder.encode("cook dinner")

    # Normalize
    emb1_norm = emb1 / np.linalg.norm(emb1)
    emb2_norm = emb2 / np.linalg.norm(emb2)
    emb3_norm = emb3 / np.linalg.norm(emb3)

    # Similar texts should have higher similarity
    sim_12 = np.dot(emb1_norm, emb2_norm)
    sim_13 = np.dot(emb1_norm, emb3_norm)

    assert sim_12 > sim_13


# ---------------------------------------------------------------------------
# Cache Tests
# ---------------------------------------------------------------------------


def test_cache_set_get(cache):
    """Test cache set and get."""
    skill_id = "test-skill"
    text = "test description"
    embedding = np.random.rand(384).astype(np.float32)

    # Set
    cache.set(skill_id, text, embedding)

    # Get
    cached = cache.get(skill_id, text)
    assert cached is not None
    np.testing.assert_array_almost_equal(cached, embedding)


def test_cache_invalidation(cache):
    """Test cache invalidation when text changes."""
    skill_id = "test-skill"
    text1 = "original text"
    text2 = "modified text"
    embedding = np.random.rand(384).astype(np.float32)

    # Set with original text
    cache.set(skill_id, text1, embedding)

    # Get with modified text should return None
    cached = cache.get(skill_id, text2)
    assert cached is None


def test_cache_persistence(tmp_path):
    """Test cache persists across instances."""
    cache_path = tmp_path / "embeddings.json"
    skill_id = "test-skill"
    text = "test description"
    embedding = np.random.rand(384).astype(np.float32)

    # Create cache and set
    cache1 = EmbeddingCache(cache_path)
    cache1.set(skill_id, text, embedding)

    # Create new cache instance
    cache2 = EmbeddingCache(cache_path)
    cached = cache2.get(skill_id, text)

    assert cached is not None
    np.testing.assert_array_almost_equal(cached, embedding)


def test_cache_stats(cache):
    """Test cache statistics."""
    # Empty cache
    stats = cache.stats()
    assert stats["count"] == 0

    # Add some embeddings
    for i in range(5):
        cache.set(f"skill-{i}", f"text {i}", np.random.rand(384).astype(np.float32))

    stats = cache.stats()
    assert stats["count"] == 5
    assert stats["size_mb"] > 0


# ---------------------------------------------------------------------------
# Search Tests
# ---------------------------------------------------------------------------


def test_semantic_search_basic(searcher, sample_skills):
    """Test basic semantic search."""
    results = searcher.search("write unit tests", sample_skills)

    assert len(results) > 0
    assert isinstance(results[0], SearchResult)

    # TDD skill should rank highest
    assert results[0].skill_id == "tdd-discipline"
    assert results[0].semantic_score > 0.5


def test_semantic_search_with_utility(searcher, sample_skills):
    """Test search with utility scores."""
    utility_scores = {
        "tdd-discipline": 0.9,
        "code-review": 0.7,
        "refactoring": 0.5,
    }

    results = searcher.search(
        "write tests",
        sample_skills,
        utility_scores=utility_scores
    )

    assert len(results) > 0
    # Hybrid score should consider utility
    assert results[0].utility_score > 0


def test_semantic_search_threshold(searcher, sample_skills):
    """Test search threshold filtering."""
    # High threshold should return fewer results
    searcher.threshold = 0.8
    results = searcher.search("completely unrelated query xyz", sample_skills)

    assert len(results) == 0


def test_semantic_search_top_k(searcher, sample_skills):
    """Test top_k limiting."""
    searcher.top_k = 2
    results = searcher.search("test", sample_skills)

    assert len(results) <= 2


def test_hybrid_scoring(searcher):
    """Test hybrid score calculation."""
    score = searcher._hybrid_score(
        semantic=0.8,
        utility=0.9,
        recency=0.1
    )

    # 0.5 * 0.8 + 0.3 * 0.9 + 0.2 * 0.1 = 0.4 + 0.27 + 0.02 = 0.69
    assert 0.68 < score < 0.70


def test_cosine_similarity_batch(searcher):
    """Test batch cosine similarity computation."""
    query = np.random.rand(384).astype(np.float32)
    embeddings = np.random.rand(5, 384).astype(np.float32)

    similarities = searcher._cosine_similarity_batch(query, embeddings)

    assert similarities.shape == (5,)
    assert all(-1 <= s <= 1 for s in similarities)


def test_skill_to_text(searcher, sample_skills):
    """Test skill to text conversion."""
    skill = sample_skills[0]
    text = searcher._skill_to_text(skill)

    assert "TDD Discipline" in text
    assert "Test-driven development" in text
    assert "testing" in text


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


def test_end_to_end_search(embedder, cache, sample_skills):
    """Test complete search workflow."""
    searcher = SemanticSkillSearch(embedder, cache)

    # First search (no cache)
    results1 = searcher.search("write unit tests", sample_skills)
    assert len(results1) > 0

    # Second search (with cache)
    results2 = searcher.search("write unit tests", sample_skills)
    assert len(results2) > 0

    # Results should be identical
    assert results1[0].skill_id == results2[0].skill_id


def test_search_with_empty_skills(searcher):
    """Test search with empty skill list."""
    results = searcher.search("test query", [])
    assert len(results) == 0


def test_search_with_no_matches(searcher, sample_skills):
    """Test search with no semantic matches."""
    searcher.threshold = 0.99  # Very high threshold
    results = searcher.search("xyz abc def", sample_skills)
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Availability Tests
# ---------------------------------------------------------------------------


def test_is_semantic_search_available():
    """Test availability check."""
    available = is_semantic_search_available()
    assert isinstance(available, bool)


# ---------------------------------------------------------------------------
# Performance Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_search_performance(searcher, sample_skills):
    """Test search performance."""
    import time

    # Warm up
    searcher.search("test", sample_skills)

    # Measure
    start = time.time()
    for _ in range(10):
        searcher.search("test query", sample_skills)
    duration = time.time() - start

    # Should be fast with cache
    assert duration < 1.0  # 10 searches in < 1 second


@pytest.mark.slow
def test_batch_encoding_performance(embedder):
    """Test batch encoding is faster than sequential."""
    import time

    texts = [f"test text {i}" for i in range(50)]

    # Sequential
    start = time.time()
    for text in texts:
        embedder.encode(text)
    sequential_time = time.time() - start

    # Batch
    start = time.time()
    embedder.encode_batch(texts)
    batch_time = time.time() - start

    # Batch should be significantly faster
    assert batch_time < sequential_time * 0.5
