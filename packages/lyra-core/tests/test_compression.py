"""
Tests for Context Compression System
"""

import pytest
from lyra_core.compression import (
    CompressionStrategy,
    CompressionResult,
    ContextCompressor
)


class TestCompressionResult:
    """Test CompressionResult"""

    def test_tokens_saved(self):
        """Test tokens saved calculation"""
        result = CompressionResult(
            original_content="test",
            compressed_content="t",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=0.5,
            strategy=CompressionStrategy.SUMMARIZE
        )
        assert result.tokens_saved == 50

    def test_reduction_percentage(self):
        """Test reduction percentage calculation"""
        result = CompressionResult(
            original_content="test",
            compressed_content="t",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=0.5,
            strategy=CompressionStrategy.SUMMARIZE
        )
        assert result.reduction_percentage == 50.0


class TestContextCompressor:
    """Test ContextCompressor"""

    def test_initialization(self):
        """Test compressor initialization"""
        compressor = ContextCompressor()
        assert len(compressor.compression_history) == 0

    def test_no_compression(self):
        """Test no compression strategy"""
        compressor = ContextCompressor()
        content = "This is a test sentence."

        result = compressor.compress(content, CompressionStrategy.NONE)

        assert result.compressed_content == content
        assert result.compression_ratio == 1.0

    def test_summarize_compression(self):
        """Test summarize compression"""
        compressor = ContextCompressor()
        content = "First sentence. Second sentence. Third sentence. Fourth sentence."

        result = compressor.compress(content, CompressionStrategy.SUMMARIZE, target_ratio=0.5)

        assert len(result.compressed_content) < len(content)
        assert result.compression_ratio < 1.0

    def test_extract_key_points(self):
        """Test key point extraction"""
        compressor = ContextCompressor()
        content = "This is important information. This is not important. This is critical data."

        result = compressor.compress(content, CompressionStrategy.EXTRACT_KEY_POINTS)

        assert "important" in result.compressed_content.lower()
        assert "critical" in result.compressed_content.lower()

    def test_remove_redundancy(self):
        """Test redundancy removal"""
        compressor = ContextCompressor()
        content = "The cat sat. The cat sat. The dog ran. The dog ran."

        result = compressor.compress(content, CompressionStrategy.REMOVE_REDUNDANCY)

        # Should remove duplicate sentences
        assert result.compressed_tokens < result.original_tokens

    def test_abbreviate_compression(self):
        """Test abbreviation compression"""
        compressor = ContextCompressor()
        content = "The quick brown fox jumps over the lazy dog very quickly."

        result = compressor.compress(content, CompressionStrategy.ABBREVIATE, target_ratio=0.5)

        assert result.compressed_tokens < result.original_tokens

    def test_compress_batch(self):
        """Test batch compression"""
        compressor = ContextCompressor()
        contents = [
            "First content block.",
            "Second content block.",
            "Third content block."
        ]

        results = compressor.compress_batch(contents, CompressionStrategy.SUMMARIZE)

        assert len(results) == 3
        assert all(isinstance(r, CompressionResult) for r in results)

    def test_get_stats(self):
        """Test statistics collection"""
        compressor = ContextCompressor()

        compressor.compress("Test content one.", CompressionStrategy.SUMMARIZE)
        compressor.compress("Test content two.", CompressionStrategy.ABBREVIATE)

        stats = compressor.get_stats()

        assert stats['total_compressions'] == 2
        assert 'total_tokens_saved' in stats
        assert 'avg_compression_ratio' in stats
        assert 'by_strategy' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
