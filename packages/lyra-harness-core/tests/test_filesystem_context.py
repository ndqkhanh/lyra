"""Tests for Filesystem as Externalized Context (P2-X #19)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra_harness_core.filesystem_context import FilesystemContext, StoredItem


# ---------------------------------------------------------------------------
# StoredItem
# ---------------------------------------------------------------------------


class TestStoredItem:
    def test_minimal(self):
        si = StoredItem(key="k", path="/tmp/x", content_hash="abc123")
        assert si.key == "k"
        assert si.path == "/tmp/x"
        assert si.content_hash == "abc123"
        assert si.content_type == ""
        assert si.token_count == 0

    def test_with_metadata(self):
        si = StoredItem(key="k", path="/tmp/x", content_hash="abc", metadata={"lang": "en"})
        assert si.metadata == {"lang": "en"}

    def test_frozen(self):
        si = StoredItem(key="k", path="/tmp/x", content_hash="abc")
        with pytest.raises(Exception):
            si.key = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FilesystemContext
# ---------------------------------------------------------------------------


class TestFilesystemContext:
    @pytest.fixture
    def fctx(self):
        tmp = tempfile.mkdtemp(prefix="lyra-test-fctx-")
        ctx = FilesystemContext(cache_dir=tmp)
        yield ctx
        ctx.cleanup()

    # --- store ----------------------------------------------------------------

    def test_store_returns_path(self, fctx):
        path = fctx.store("doc1", "Hello world", content_type="text/plain")
        assert isinstance(path, str)
        assert Path(path).exists()

    def test_store_bytes(self, fctx):
        data = b"binary content here"
        path = fctx.store("binary1", data)
        assert Path(path).read_bytes() == data

    def test_store_creates_index_entry(self, fctx):
        fctx.store("doc1", "content", content_type="text/plain")
        item = fctx.get_item("doc1")
        assert item is not None
        assert item.key == "doc1"
        assert item.content_type == "text/plain"
        assert item.size_bytes > 0

    def test_store_deduplicates_by_hash(self, fctx):
        p1 = fctx.store("doc1", "same content")
        p2 = fctx.store("doc2", "same content")
        assert p1 == p2  # same content → same path

    def test_store_exceeds_max_size(self, fctx):
        fctx.max_file_size = 10
        with pytest.raises(ValueError, match="max_file_size"):
            fctx.store("big", "x" * 100)

    # --- retrieve -------------------------------------------------------------

    def test_retrieve_by_key(self, fctx):
        fctx.store("doc1", "Hello world")
        content = fctx.retrieve("doc1")
        assert content == "Hello world"

    def test_retrieve_by_path(self, fctx):
        path = fctx.store("doc1", "Hello world")
        content = fctx.retrieve(path)
        assert content == "Hello world"

    def test_retrieve_missing_key(self, fctx):
        with pytest.raises(KeyError, match="no stored item"):
            fctx.retrieve("nonexistent")

    def test_retrieve_truncates_to_budget(self, fctx):
        long_text = "word " * 500  # ~2500 chars
        fctx.store("long", long_text)
        content = fctx.retrieve("long", max_tokens=100)  # 400 chars budget
        assert len(content) <= 420  # 400 + truncation note
        assert "truncated" in content

    def test_retrieve_no_truncation_when_under_budget(self, fctx):
        fctx.store("short", "hello")
        content = fctx.retrieve("short", max_tokens=100)
        assert content == "hello"

    def test_retrieve_bytes(self, fctx):
        fctx.store("bin", b"binary\x00data")
        data = fctx.retrieve_bytes("bin")
        assert data == b"binary\x00data"

    # --- drop / purge ---------------------------------------------------------

    def test_drop_removes_file_keeps_index(self, fctx):
        path = fctx.store("doc1", "content")
        assert fctx.drop("doc1")
        assert not Path(path).exists()
        assert fctx.get_item("doc1") is not None  # index preserved

    def test_drop_retrieve_raises(self, fctx):
        fctx.store("doc1", "content")
        fctx.drop("doc1")
        with pytest.raises(FileNotFoundError, match="stored file missing"):
            fctx.retrieve("doc1")

    def test_drop_nonexistent(self, fctx):
        assert not fctx.drop("nope")

    def test_purge_removes_file_and_index(self, fctx):
        path = fctx.store("doc1", "content")
        assert fctx.purge("doc1")
        assert not Path(path).exists()
        assert fctx.get_item("doc1") is None

    def test_purge_nonexistent(self, fctx):
        assert not fctx.purge("nope")

    # --- truncate -------------------------------------------------------------

    def test_truncate_reduces_content(self, fctx):
        fctx.store("doc1", "word " * 200)
        result = fctx.truncate("doc1", max_tokens=50)
        assert result is not None
        assert len(result) < len("word " * 200)
        assert "truncated" in result

    def test_truncate_nonexistent(self, fctx):
        assert fctx.truncate("nope", 100) is None

    # --- introspection --------------------------------------------------------

    def test_list_keys(self, fctx):
        fctx.store("bbb", "content bbb")
        fctx.store("aaa", "content aaa")
        assert fctx.list_keys() == ["aaa", "bbb"]

    def test_item_count(self, fctx):
        assert fctx.item_count == 0
        fctx.store("a", "x")
        fctx.store("b", "different")  # different content → new entry
        assert fctx.item_count == 2

    def test_total_size_bytes(self, fctx):
        fctx.store("a", "hello world")  # 11 bytes
        assert fctx.total_size_bytes >= 11

    def test_get_item_missing(self, fctx):
        assert fctx.get_item("nope") is None

    # --- clear / cleanup ------------------------------------------------------

    def test_clear(self, fctx):
        path = fctx.store("doc1", "content")
        fctx.clear()
        assert fctx.item_count == 0
        assert not Path(path).exists()

    def test_cleanup_removes_directory(self, fctx):
        fctx.store("doc1", "content")
        cache_dir = fctx.cache_dir
        fctx.cleanup()
        assert not cache_dir.exists()

    # --- content types --------------------------------------------------------

    def test_html_content(self, fctx):
        html = "<html><body><p>Hello</p></body></html>"
        path = fctx.store("page1", html, content_type="text/html")
        item = fctx.get_item("page1")
        assert item.content_type == "text/html"
        assert Path(path).exists()

    def test_json_content(self, fctx):
        json_str = '{"key": "value", "items": [1, 2, 3]}'
        fctx.store("data", json_str, content_type="application/json")
        content = fctx.retrieve("data")
        assert "key" in content

    def test_token_count_estimate(self, fctx):
        # 40 chars ≈ 10 tokens
        fctx.store("doc", "a" * 40)
        item = fctx.get_item("doc")
        assert item.token_count == 10


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestFilesystemContextIntegration:
    def test_agent_workflow(self):
        tmp = tempfile.mkdtemp(prefix="lyra-int-fctx-")
        fctx = None
        try:
            fctx = FilesystemContext(cache_dir=tmp)

            # Agent stores web page content
            web_path = fctx.store(
                "web_page_1",
                "<html>" + ("<p>paragraph content here.</p>" * 100) + "</html>",
                content_type="text/html",
                metadata={"url": "https://example.com", "fetched_at": "2026-05-30"},
            )

            # Agent sees only the path
            assert "lyra" in web_path or "fctx" in web_path

            # Later, agent retrieves with token budget
            summary = fctx.retrieve("web_page_1", max_tokens=50)
            assert len(summary) <= 220  # 50 * 4 + note
            assert "paragraph" in summary

            # Agent can drop content to save disk
            assert fctx.drop("web_page_1")
            # Index entry still visible
            assert fctx.get_item("web_page_1") is not None
            assert fctx.get_item("web_page_1").content_type == "text/html"

            # Can still see the URL metadata
            item = fctx.get_item("web_page_1")
            assert item.metadata["url"] == "https://example.com"

            # Clean up fully
            fctx.purge("web_page_1")
            assert fctx.item_count == 0
        finally:
            fctx.cleanup()

    def test_multiple_documents(self):
        tmp = tempfile.mkdtemp(prefix="lyra-multi-fctx-")
        fctx = None
        try:
            fctx = FilesystemContext(cache_dir=tmp)

            for i in range(20):
                fctx.store(f"doc{i:03d}", f"Content of document {i} " * 20)

            assert fctx.item_count == 20
            assert len(fctx.list_keys()) == 20

            # Total size should be reasonable
            assert fctx.total_size_bytes > 0

            # Clear all
            fctx.clear()
            assert fctx.item_count == 0
        finally:
            fctx.cleanup()
