"""
Ingestion pipeline — documents (PDF, markdown, code) -> chunk -> embed -> store.

Provides Document and Chunk models, a SimpleChunker for text splitting,
an Embedder stub for vector representation, and an IngestionPipeline
that orchestrates the full flow with configurable storage backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Protocol


class DocumentType(Enum):
    """Supported document types."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    CODE = "code"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class Document:
    """A source document to be ingested.

    Attributes:
        path: Source file path.
        doc_type: Detected document type.
        content: Raw document text.
        metadata: Arbitrary metadata key-value pairs.
        doc_id: Unique document identifier (auto-generated if empty).
        ingested_at: Timestamp of ingestion.
    """

    path: str
    doc_type: DocumentType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str = ""
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Auto-generate doc_id if empty."""
        if not self.doc_id:
            raw = (self.path + self.content[:256]).encode()
            self.doc_id = sha256(raw).hexdigest()[:16]


@dataclass
class Chunk:
    """A text chunk produced by chunking a Document.

    Attributes:
        doc_id: Parent document identifier.
        index: Chunk index within the document.
        text: Chunk text content.
        embedding: Vector embedding (populated after embed stage).
        metadata: Chunk-level metadata (e.g. page number, section).
    """

    doc_id: str
    index: int
    text: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        """Unique chunk identifier."""
        raw = (self.doc_id + str(self.index)).encode()
        return sha256(raw).hexdigest()[:16]


class SimpleChunker:
    """Splits document text into fixed-size chunks with optional overlap.

    Attributes:
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        """Initialize SimpleChunker.

        Args:
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Overlap between chunks.
        """
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than "
                f"chunk_size ({chunk_size})"
            )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        """Split a Document into chunks.

        Args:
            document: Document to chunk.

        Returns:
            List of Chunk objects.
        """
        text = document.content
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            segment = text[start:end]
            chunk = Chunk(
                doc_id=document.doc_id,
                index=index,
                text=segment,
                metadata={"doc_type": document.doc_type.value, "path": document.path},
            )
            chunks.append(chunk)
            index += 1
            if end >= len(text):
                break
            start = end - self.chunk_overlap

        return chunks


class Embedder(Protocol):
    """Protocol for embedding models.

    Implementations should convert text chunks to vector embeddings.
    """

    def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as a list of floats.
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings.

        Args:
            texts: Texts to embed.

        Returns:
            List of embedding vectors.
        """
        ...


class StubEmbedder:
    """Stub embedder for testing — returns deterministic dummy vectors."""

    def __init__(self, dimension: int = 128):
        """Initialize stub embedder.

        Args:
            dimension: Embedding vector dimension.
        """
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        """Return a deterministic dummy embedding based on text hash."""
        h = sha256(text.encode()).digest()
        vec = [b / 255.0 for b in h[: self.dimension]]
        # Pad or truncate to dimension
        while len(vec) < self.dimension:
            vec.append(0.0)
        return vec[: self.dimension]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        return [self.embed(t) for t in texts]


class MemoryStore(Protocol):
    """Protocol for vector/document stores.

    Implementations store chunk vectors and support search.
    """

    def store(self, chunks: list[Chunk]) -> int:
        """Store chunks in memory.

        Args:
            chunks: Chunks to store.

        Returns:
            Number of chunks stored.
        """
        ...


class DictMemoryStore:
    """Simple in-memory dictionary store for testing.

    Stores chunks keyed by chunk_id.
    """

    def __init__(self):
        """Initialize empty store."""
        self._data: dict[str, Chunk] = {}

    def store(self, chunks: list[Chunk]) -> int:
        """Store chunks in memory.

        Args:
            chunks: Chunks to store.

        Returns:
            Number of chunks stored.
        """
        count = 0
        for chunk in chunks:
            self._data[chunk.chunk_id] = chunk
            count += 1
        return count

    def get(self, chunk_id: str) -> Chunk | None:
        """Retrieve a chunk by ID."""
        return self._data.get(chunk_id)

    def count(self) -> int:
        """Number of stored chunks."""
        return len(self._data)


class IngestionPipeline:
    """End-to-end ingestion pipeline: documents -> chunks -> embeddings -> store.

    Orchestrates document loading, chunking, embedding, and storage
    with configurable components at each stage.
    """

    def __init__(
        self,
        chunker: SimpleChunker | None = None,
        embedder: Embedder | StubEmbedder | None = None,
        store: MemoryStore | None = None,
    ):
        """Initialize IngestionPipeline.

        Args:
            chunker: Text chunker (uses SimpleChunker if None).
            embedder: Embedding model (uses StubEmbedder if None).
            store: Storage backend (uses DictMemoryStore if None).
        """
        self.chunker = chunker or SimpleChunker()
        self.embedder = embedder or StubEmbedder()
        self.store = store or DictMemoryStore()

    def detect_type(self, path: str) -> DocumentType:
        """Detect document type from file extension.

        Args:
            path: File path.

        Returns:
            Detected DocumentType.
        """
        ext = Path(path).suffix.lower()
        mapping: dict[str, DocumentType] = {
            ".pdf": DocumentType.PDF,
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".mdown": DocumentType.MARKDOWN,
            ".py": DocumentType.CODE,
            ".js": DocumentType.CODE,
            ".ts": DocumentType.CODE,
            ".tsx": DocumentType.CODE,
            ".jsx": DocumentType.CODE,
            ".go": DocumentType.CODE,
            ".rs": DocumentType.CODE,
            ".java": DocumentType.CODE,
            ".c": DocumentType.CODE,
            ".cpp": DocumentType.CODE,
            ".h": DocumentType.CODE,
            ".hpp": DocumentType.CODE,
            ".rb": DocumentType.CODE,
            ".php": DocumentType.CODE,
            ".sql": DocumentType.CODE,
            ".yaml": DocumentType.CODE,
            ".yml": DocumentType.CODE,
            ".json": DocumentType.CODE,
            ".toml": DocumentType.CODE,
            ".txt": DocumentType.TEXT,
            ".rst": DocumentType.TEXT,
        }
        return mapping.get(ext, DocumentType.UNKNOWN)

    def load_document(self, path: str | Path, **metadata: Any) -> Document:
        """Load a document from file.

        Args:
            path: File path to load.
            metadata: Additional metadata to attach.

        Returns:
            Loaded Document.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        content = path_obj.read_text(encoding="utf-8", errors="replace")
        doc_type = self.detect_type(str(path_obj))

        return Document(
            path=str(path_obj),
            doc_type=doc_type,
            content=content,
            metadata=metadata,
        )

    def process_document(self, document: Document) -> int:
        """Run the full pipeline on a single document.

        Steps:
            1. Chunk the document.
            2. Embed each chunk.
            3. Store chunks.

        Args:
            document: Document to process.

        Returns:
            Number of chunks stored.
        """
        # Step 1: Chunk
        chunks = self.chunker.chunk(document)

        # Step 2: Embed
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed_batch(texts)
        for chunk, emb in zip(chunks, embeddings, strict=False):
            chunk.embedding = emb

        # Step 3: Store
        return self.store.store(chunks)

    def process_file(self, path: str | Path, **metadata: Any) -> int:
        """Load a file and run the full pipeline.

        Convenience wrapper around load_document + process_document.

        Args:
            path: File path to process.
            metadata: Additional document metadata.

        Returns:
            Number of chunks stored.
        """
        document = self.load_document(path, **metadata)
        return self.process_document(document)
