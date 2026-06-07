"""Tests for src/ingestion/pipeline.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra.ingestion.pipeline import (
    Chunk,
    DictMemoryStore,
    Document,
    DocumentType,
    IngestionPipeline,
    SimpleChunker,
    StubEmbedder,
)


class TestSimpleChunker:
    """Tests for SimpleChunker."""

    def test_chunk_single(self):
        """Chunking a short document produces one chunk."""
        doc = Document(path="test.md", doc_type=DocumentType.MARKDOWN, content="Hello world")
        chunker = SimpleChunker(chunk_size=1000)
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"

    def test_chunk_multiple(self):
        """Chunking a long document produces multiple chunks."""
        text = "A" * 2500
        doc = Document(path="long.txt", doc_type=DocumentType.TEXT, content=text)
        chunker = SimpleChunker(chunk_size=1000, chunk_overlap=50)
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2

    def test_chunk_overlap_validation(self):
        """Creating a chunker with overlap >= chunk_size raises."""
        with pytest.raises(ValueError):
            SimpleChunker(chunk_size=100, chunk_overlap=100)

    def test_chunk_ids_are_unique(self):
        """Each chunk gets a unique chunk_id."""
        text = "X" * 3000
        doc = Document(path="big.txt", doc_type=DocumentType.TEXT, content=text)
        chunker = SimpleChunker(chunk_size=1000, chunk_overlap=100)
        chunks = chunker.chunk(doc)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))


class TestStubEmbedder:
    """Tests for StubEmbedder."""

    def test_embed_returns_list(self):
        """embed returns a list of floats of correct dimension."""
        embedder = StubEmbedder(dimension=128)
        vec = embedder.embed("hello")
        assert len(vec) == 128
        assert all(isinstance(v, float) for v in vec)

    def test_embed_deterministic(self):
        """embed returns the same vector for the same text."""
        embedder = StubEmbedder()
        v1 = embedder.embed("same text")
        v2 = embedder.embed("same text")
        assert v1 == v2

    def test_embed_batch(self):
        """embed_batch returns one vector per text."""
        embedder = StubEmbedder(dimension=64)
        vecs = embedder.embed_batch(["a", "b", "c"])
        assert len(vecs) == 3
        assert all(len(v) == 64 for v in vecs)


class TestDictMemoryStore:
    """Tests for DictMemoryStore."""

    def test_store_and_count(self):
        """Storing chunks increments count."""
        store = DictMemoryStore()
        chunks = [Chunk(doc_id="doc1", index=0, text="hello")]
        assert store.store(chunks) == 1
        assert store.count() == 1

    def test_retrieve(self):
        """Stored chunks can be retrieved by chunk_id."""
        store = DictMemoryStore()
        chunk = Chunk(doc_id="doc1", index=0, text="hello")
        store.store([chunk])
        retrieved = store.get(chunk.chunk_id)
        assert retrieved is not None
        assert retrieved.text == "hello"

    def test_missing_returns_none(self):
        """Getting a nonexistent chunk returns None."""
        store = DictMemoryStore()
        assert store.get("nope") is None


class TestIngestionPipeline:
    """Tests for IngestionPipeline."""

    def test_detect_type_by_extension(self):
        """detect_type identifies file types from extension."""
        pipe = IngestionPipeline()
        assert pipe.detect_type("readme.md") == DocumentType.MARKDOWN
        assert pipe.detect_type("script.py") == DocumentType.CODE
        assert pipe.detect_type("doc.txt") == DocumentType.TEXT
        assert pipe.detect_type("unknown.xyz") == DocumentType.UNKNOWN

    def test_load_file_not_found(self):
        """load_document raises FileNotFoundError for missing file."""
        pipe = IngestionPipeline()
        with pytest.raises(FileNotFoundError):
            pipe.load_document("/nonexistent/file.txt")

    def test_process_document_full_pipeline(self, tmp_path):
        """Full pipeline processes a document end-to-end."""
        d = tmp_path / "test.md"
        d.write_text("Hello Lyra Ingestion Pipeline!")

        pipe = IngestionPipeline()
        count = pipe.process_file(str(d))
        assert count >= 1

    def test_process_document_embeds_chunks(self, tmp_path):
        """After processing, chunks have embeddings."""
        d = tmp_path / "doc.md"
        d.write_text("Word " * 500)  # long enough for multiple chunks

        pipe = IngestionPipeline(chunker=SimpleChunker(chunk_size=200, chunk_overlap=20))
        pipe.process_file(str(d))

        # Verify stored chunks have embeddings
        for chunk_id, chunk in pipe.store._data.items():
            assert len(chunk.embedding) > 0
