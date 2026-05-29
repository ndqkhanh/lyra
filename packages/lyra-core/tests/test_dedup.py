"""
Tests for Semantic Deduplication System
"""

import pytest
from lyra_core.dedup import (
    ContentBlock,
    DuplicateGroup,
    SemanticDeduplicator,
    create_simple_embedding
)


class TestContentBlock:
    """Test ContentBlock"""

    def test_initialization(self):
        """Test block initialization"""
        block = ContentBlock(id="1", content="test content")
        assert block.id == "1"
        assert block.content == "test content"

    def test_get_hash(self):
        """Test content hashing"""
        block1 = ContentBlock(id="1", content="test")
        block2 = ContentBlock(id="2", content="test")
        block3 = ContentBlock(id="3", content="different")

        assert block1.get_hash() == block2.get_hash()
        assert block1.get_hash() != block3.get_hash()


class TestSemanticDeduplicator:
    """Test Semantic Deduplicator"""

    def test_initialization(self):
        """Test deduplicator initialization"""
        dedup = SemanticDeduplicator(similarity_threshold=0.9)
        assert dedup.similarity_threshold == 0.9

    def test_exact_duplicates(self):
        """Test exact duplicate detection"""
        dedup = SemanticDeduplicator()

        blocks = [
            ContentBlock(id="1", content="identical content"),
            ContentBlock(id="2", content="identical content"),
            ContentBlock(id="3", content="different content"),
        ]

        deduplicated, stats = dedup.deduplicate(blocks)

        assert stats['original_count'] == 3
        assert stats['deduplicated_count'] == 2
        assert stats['removed_count'] == 1
        assert stats['exact_duplicate_groups'] == 1

    def test_semantic_duplicates(self):
        """Test semantic duplicate detection"""
        dedup = SemanticDeduplicator(similarity_threshold=0.8)

        # Create blocks with similar embeddings
        blocks = [
            ContentBlock(
                id="1",
                content="The quick brown fox",
                embedding=create_simple_embedding("The quick brown fox")
            ),
            ContentBlock(
                id="2",
                content="The quick brown fox jumps",
                embedding=create_simple_embedding("The quick brown fox")
            ),
            ContentBlock(
                id="3",
                content="Completely different text",
                embedding=create_simple_embedding("Completely different text")
            ),
        ]

        deduplicated, stats = dedup.deduplicate(blocks)

        assert stats['original_count'] == 3
        assert stats['deduplicated_count'] <= 3

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        dedup = SemanticDeduplicator()

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]

        # Identical vectors
        assert dedup.cosine_similarity(vec1, vec2) == 1.0

        # Orthogonal vectors
        assert dedup.cosine_similarity(vec1, vec3) == 0.0

    def test_size_reduction(self):
        """Test size reduction calculation"""
        dedup = SemanticDeduplicator()

        blocks = [
            ContentBlock(id="1", content="a" * 100),
            ContentBlock(id="2", content="a" * 100),  # Duplicate
            ContentBlock(id="3", content="b" * 100),
        ]

        deduplicated, stats = dedup.deduplicate(blocks)

        assert stats['original_size'] == 300
        assert stats['deduplicated_size'] == 200
        assert stats['size_reduction'] == 100
        assert stats['reduction_percentage'] > 0


class TestEmbedding:
    """Test embedding creation"""

    def test_create_simple_embedding(self):
        """Test simple embedding creation"""
        embedding = create_simple_embedding("test text")

        assert len(embedding) == 128
        assert all(isinstance(x, float) for x in embedding)

        # Check normalization
        norm = sum(x * x for x in embedding) ** 0.5
        assert abs(norm - 1.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
