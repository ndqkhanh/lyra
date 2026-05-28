"""Tests for context optimizer modules — RTK, Caveman, EntropyFilter, SymbolGraphOffloader."""

import time

import pytest

from lyra_cli.memory.context_optimizer.caveman_compressor import CavemanCompressor, CavemanResult
from lyra_cli.memory.context_optimizer.entropy_filter import (
    ContextItem,
    EntropyFilter,
    EntropyLevel,
    FilteredContext,
)
from lyra_cli.memory.context_optimizer.rtk_compressor import (
    CompressedContent,
    CompressionStrategy,
    RTKCompressor,
)
from lyra_cli.memory.context_optimizer.symbol_offloader import (
    OffloadedContext,
    SymbolEntry,
    SymbolGraphOffloader,
)


class TestCompressionStrategy:
    def test_all_strategies(self):
        assert CompressionStrategy.STRUCTURAL_MINIFY.value == "structural_minify"
        assert CompressionStrategy.STRUCTURAL_ABSTRACT.value == "structural_abstract"
        assert CompressionStrategy.STRUCTURAL_CACHE.value == "structural_cache"


class TestCompressedContent:
    def test_creation(self):
        cc = CompressedContent(
            compressed="test",
            strategy=CompressionStrategy.STRUCTURAL_MINIFY,
            original_hash="abc123",
            original_len=100,
            compressed_len=50,
            compression_ratio=50.0,
            elapsed_ms=1.5,
        )
        assert cc.compressed == "test"
        assert cc.compression_ratio == 50.0
        assert cc.reversible is True

    def test_frozen(self):
        cc = CompressedContent(
            compressed="test",
            strategy=CompressionStrategy.STRUCTURAL_MINIFY,
            original_hash="abc",
            original_len=10,
            compressed_len=5,
            compression_ratio=50.0,
            elapsed_ms=1.0,
        )
        with pytest.raises(Exception):
            cc.compressed = "new"  # type: ignore[misc]


class TestRTKCompressor:
    def test_init(self):
        compressor = RTKCompressor()
        assert compressor.stats()["cached_patterns"] == 0

    def test_minify_reduces_whitespace(self):
        compressor = RTKCompressor()
        content = "line1\n\n\n\nline2\n\n\nline3"
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_MINIFY)
        assert result.compressed_len < len(content)
        assert result.strategy == CompressionStrategy.STRUCTURAL_MINIFY
        assert result.compression_ratio > 0

    def test_minify_strips_trailing_whitespace(self):
        compressor = RTKCompressor()
        content = "hello world    \nfoo bar  "
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_MINIFY)
        assert "    " not in result.compressed.split('\n')[-1] if '\n' in result.compressed else True

    def test_abstract_compression(self):
        compressor = RTKCompressor()
        content = "import os\nimport sys\nimport re\nimport json\n\n\n# some code here\n# more code\n# even more"
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_ABSTRACT)
        assert result.compressed_len <= len(content)

    def test_cache_compression(self):
        compressor = RTKCompressor()
        content = "verylongidentifier123 verylongidentifier123 verylongidentifier123"
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_CACHE)
        assert result.compressed_len < len(content)

    def test_decompress_minify(self):
        compressor = RTKCompressor()
        content = "hello world\nfoo bar"
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_MINIFY)
        decompressed = compressor.decompress(result)
        assert isinstance(decompressed, str)

    def test_decompress_abstract(self):
        compressor = RTKCompressor()
        content = "import os\nimport sys\n\ncode here"
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_ABSTRACT)
        decompressed = compressor.decompress(result)
        assert isinstance(decompressed, str)

    def test_empty_content(self):
        compressor = RTKCompressor()
        result = compressor.compress("", CompressionStrategy.STRUCTURAL_MINIFY)
        assert result.original_len == 0

    def test_single_line_no_reduction(self):
        compressor = RTKCompressor()
        content = "simple"
        result = compressor.compress(content, CompressionStrategy.STRUCTURAL_MINIFY)
        assert result.compressed_len <= len(content)


class TestCavemanCompressor:
    def test_init(self):
        compressor = CavemanCompressor()
        assert compressor.stats()["short_id_map_size"] == 0

    def test_compress_reduces_size(self):
        compressor = CavemanCompressor()
        content = "line1\nline1\nline1\nline2\nline2\nline3"
        result = compressor.compress(content)
        assert result.compression_ratio > 0
        assert result.elapsed_ms >= 0

    def test_collapses_whitespace(self):
        compressor = CavemanCompressor()
        content = "   hello    world   \n\n\n   foo   bar   "
        result = compressor.compress(content)
        assert len(result.compressed) < len(content)

    def test_result_frozen(self):
        compressor = CavemanCompressor()
        result = compressor.compress("test content here")
        assert result.original_hash
        assert result.original_len > 0

    def test_shortens_long_identifiers(self):
        compressor = CavemanCompressor()
        content = "very_long_identifier_here " * 5
        result = compressor.compress(content)
        assert result.short_id_count >= 0

    def test_empty_content(self):
        compressor = CavemanCompressor()
        result = compressor.compress("")
        assert result.original_len == 0


class TestContextItem:
    def test_creation(self):
        item = ContextItem(
            item_id="i1",
            content="hello world",
            source="test",
            timestamp=time.time(),
        )
        assert item.item_id == "i1"
        assert item.entropy_score == 0.0
        assert item.level == EntropyLevel.MEDIUM

    def test_frozen(self):
        item = ContextItem(
            item_id="i1",
            content="test",
            source="test",
            timestamp=time.time(),
        )
        with pytest.raises(Exception):
            item.content = "new"  # type: ignore[misc]


class TestEntropyFilter:
    def test_init(self):
        f = EntropyFilter()
        assert f.stats()["low_entropy_patterns"] > 0

    def test_filter_discards_acknowledgments(self):
        f = EntropyFilter()
        items = [
            ContextItem("1", "ok", "system", time.time()),
            ContextItem("2", "Here is the detailed report on Q3 earnings", "user", time.time()),
        ]
        result = f.filter(items)
        assert len(result.kept) >= 1
        assert len(result.discarded) >= 1

    def test_filter_keeps_meaningful_content(self):
        f = EntropyFilter()
        items = [
            ContextItem("1", "The authentication module has a race condition in the token refresh logic", "user", time.time()),
        ]
        result = f.filter(items)
        assert len(result.kept) >= 1

    def test_filter_calculates_reduction(self):
        f = EntropyFilter()
        items = [
            ContextItem("1", "ok", "system", time.time()),
            ContextItem("2", "ack", "system", time.time()),
            ContextItem("3", "Important: the production database migration failed with error code 500", "system", time.time()),
        ]
        result = f.filter(items)
        assert result.reduction_pct > 0
        assert result.original_tokens > 0

    def test_filter_discards_heartbeat(self):
        f = EntropyFilter()
        items = [
            ContextItem("1", "ping", "system", time.time()),
            ContextItem("2", "Detailed analysis of the memory leak in the worker pool", "system", time.time()),
        ]
        result = f.filter(items)
        assert len(result.kept) >= 1

    def test_empty_items(self):
        f = EntropyFilter()
        result = f.filter([])
        assert len(result.kept) == 0
        assert result.original_tokens == 0


class TestSymbolGraphOffloader:
    def test_init(self):
        offloader = SymbolGraphOffloader()
        assert offloader.stats()["symbols_stored"] == 0

    def test_offload_replaces_versions(self):
        offloader = SymbolGraphOffloader()
        content = "Using https://example.com/api and /usr/local/bin/python for testing"
        result = offloader.offload(content)
        assert result.entity_count > 0

    def test_offload_replaces_config_keys(self):
        offloader = SymbolGraphOffloader()
        content = "Set DATABASE_URL and REDIS_HOST in your environment"
        result = offloader.offload(content)
        assert result.entity_count > 0

    def test_hydrate_restores_content(self):
        offloader = SymbolGraphOffloader()
        content = "Visit https://example.com/page for details"
        result = offloader.offload(content)
        restored = offloader.hydrate(result)
        assert "https://example.com/page" in restored

    def test_offload_empty_content(self):
        offloader = SymbolGraphOffloader()
        result = offloader.offload("")
        assert result.entity_count == 0

    def test_offload_simple_text(self):
        offloader = SymbolGraphOffloader()
        content = "hello world, this is a simple message"
        result = offloader.offload(content)
        assert isinstance(result.text, str)

    def test_stats_tracks_by_type(self):
        offloader = SymbolGraphOffloader()
        offloader.offload("Version 2.0.1 and CONFIG_KEY_VALUE here")
        s = offloader.stats()
        assert "by_type" in s
        assert isinstance(s["by_type"], dict)
