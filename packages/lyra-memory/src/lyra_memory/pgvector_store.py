"""
Postgres Vector Store (pgvector + pgvectorscale).

Production-grade vector store abstraction with:
- Async pgvector-backed vector storage and ANN search
- IVF Flat and HNSW index support
- Embedding model wrapper (sentence-transformers or OpenAI)
- Graceful fallback to in-memory numpy store when Postgres is unavailable
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

try:
    import numpy as np

    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False
    logger.warning("numpy not available; vector similarity will be limited")


@dataclass(frozen=True)
class PgVectorConfig:
    """
    Configuration for Postgres pgvector connection.

    All connection values can be sourced from environment variables.
    """

    host: str = field(default_factory=lambda: os.environ.get("PGVECTOR_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.environ.get("PGVECTOR_PORT", "5432")))
    dbname: str = field(default_factory=lambda: os.environ.get("PGVECTOR_DBNAME", "lyra_memory"))
    user: str = field(default_factory=lambda: os.environ.get("PGVECTOR_USER", "postgres"))
    password: str = field(default_factory=lambda: os.environ.get("PGVECTOR_PASSWORD", ""))
    vector_dim: int = field(default_factory=lambda: int(os.environ.get("PGVECTOR_VECTOR_DIM", "384")))
    max_connections: int = 10
    connection_timeout: int = 10

    @property
    def dsn(self) -> str:
        """Build a connection DSN string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class PgVectorEmbedding:
    """
    Embedding model wrapper supporting sentence-transformers and OpenAI.

    Provides a unified ``encode(text) -> list[float]`` interface regardless
    of the underlying model provider.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        provider: str = "sentence-transformers",
        openai_api_key: str | None = None,
    ) -> None:
        """
        Initialize the embedding wrapper.

        Args:
            model_name: Model identifier
            provider: "sentence-transformers" or "openai"
            openai_api_key: API key for OpenAI (defaults to OPENAI_API_KEY env var)
        """
        self.model_name = model_name
        self.provider = provider
        self._model: Any | None = None

        if provider == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(model_name)
                logger.info("Loaded sentence-transformers model: %s", model_name)
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed; embeddings will be zero vectors"
                )
            except Exception:
                logger.exception("Failed to load model '%s'", model_name)
        elif provider == "openai":
            self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
            if not self._api_key:
                logger.warning("OPENAI_API_KEY not set; OpenAI embeddings unavailable")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def encode(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        if self.provider == "sentence-transformers" and self._model:
            return self._model.encode(text).tolist()
        elif self.provider == "openai" and self._api_key:
            return self._encode_openai(text)
        else:
            logger.debug("No embedding model available, returning zero vector")
            return [0.0] * 384

    async def encode_async(self, text: str) -> list[float]:
        """Async wrapper around encode for consistency with async store."""
        return self.encode(text)

    def _encode_openai(self, text: str) -> list[float]:
        """Call OpenAI embeddings API synchronously."""
        try:
            import openai

            client = openai.OpenAI(api_key=self._api_key)
            response = client.embeddings.create(input=[text], model=self.model_name)
            return response.data[0].embedding
        except ImportError:
            logger.warning("openai package not installed")
            return [0.0] * 384
        except Exception:
            logger.exception("OpenAI embedding failed")
            return [0.0] * 384

    @property
    def vector_dim(self) -> int:
        """Get the embedding dimension."""
        if self._model:
            if hasattr(self._model, "get_embedding_dimension"):
                return self._model.get_embedding_dimension()
            elif hasattr(self._model, "get_sentence_embedding_dimension"):
                return self._model.get_sentence_embedding_dimension()
        return 384


class InMemoryVectorStore:
    """
    In-memory vector store using numpy for cosine similarity.

    Used as a graceful fallback when Postgres/pgvector is unavailable.
    Provides the same interface as PgVectorStore for drop-in compatibility.
    """

    def __init__(self, vector_dim: int = 384) -> None:
        """
        Initialize in-memory store.

        Args:
            vector_dim: Dimension of stored vectors
        """
        self._vector_dim = vector_dim
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}
        logger.info("Initialized InMemoryVectorStore (dim=%d)", vector_dim)

    def insert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        Insert vectors into a collection.

        Args:
            collection: Collection name
            vectors: List of embedding vectors
            metadata: Optional list of metadata dicts, one per vector

        Returns:
            List of inserted record IDs
        """
        if collection not in self._collections:
            self._collections[collection] = {}

        ids: list[str] = []
        meta_list = metadata or [{}] * len(vectors)

        for vec, meta in zip(vectors, meta_list):
            record_id = meta.get("id", str(uuid4()))
            self._collections[collection][record_id] = {
                "vector": vec,
                "metadata": meta,
                "created_at": datetime.now().isoformat(),
            }
            ids.append(record_id)

        logger.debug("Inserted %d vectors into collection '%s'", len(ids), collection)
        return ids

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for nearest neighbors using cosine similarity.

        Args:
            collection: Collection name
            query_vector: Query embedding
            top_k: Maximum results
            filters: Optional metadata filter (key-value equality)

        Returns:
            List of result dicts with keys: id, metadata, score
        """
        if collection not in self._collections:
            return []

        if not _NUMPY_AVAILABLE:
            return list(self._collections[collection].values())[:top_k]

        query = np.array(query_vector, dtype=np.float64)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        scores: list[tuple[str, float, dict[str, Any]]] = []
        for rid, record in self._collections[collection].items():
            if filters and not self._matches_filters(record["metadata"], filters):
                continue
            vec = np.array(record["vector"], dtype=np.float64)
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            score = float(np.dot(query, vec) / (query_norm * vec_norm))
            scores.append((rid, score, record["metadata"]))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {"id": sid, "score": score, "metadata": meta}
            for sid, score, meta in scores[:top_k]
        ]

    def delete(self, collection: str, ids: list[str]) -> int:
        """
        Remove vectors by ID from a collection.

        Args:
            collection: Collection name
            ids: List of record IDs to remove

        Returns:
            Number of records deleted
        """
        if collection not in self._collections:
            return 0
        deleted = 0
        for rid in ids:
            if rid in self._collections[collection]:
                del self._collections[collection][rid]
                deleted += 1
        logger.debug("Deleted %d vectors from collection '%s'", deleted, collection)
        return deleted

    def get_collection(self, collection: str) -> dict[str, dict[str, Any]]:
        """Get all records in a collection."""
        return self._collections.get(collection, {})

    def list_collections(self) -> list[str]:
        """List all collection names."""
        return list(self._collections.keys())

    def collection_size(self, collection: str) -> int:
        """Get the number of records in a collection."""
        return len(self._collections.get(collection, {}))

    @staticmethod
    def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if metadata matches all filter key-value pairs."""
        return all(metadata.get(k) == v for k, v in filters.items())


class PgVectorStore:
    """
    Async Postgres vector store backed by pgvector/pgvectorscale.

    Provides ANN search via IVF Flat or HNSW indexes with graceful
    fallback to InMemoryVectorStore when Postgres is unavailable.

    Usage::

        store = PgVectorStore(config)
        await store.initialize()
        ids = await store.insert("docs", vectors, metadata)
        results = await store.search("docs", query_vector, top_k=5)
        await store.close()
    """

    def __init__(self, config: PgVectorConfig | None = None) -> None:
        """
        Initialize the vector store.

        Args:
            config: Connection configuration; uses defaults if not provided
        """
        self.config = config or PgVectorConfig()
        self._pool: Any | None = None
        self._fallback: InMemoryVectorStore | None = None
        self._using_postgres = False

    async def initialize(self) -> bool:
        """
        Initialize the store connection.

        Attempts to connect to Postgres with pgvector. Falls back to
        in-memory store if connection fails.

        Returns:
            True if using Postgres, False if using fallback
        """
        try:
            import asyncpg  # noqa: F401

            self._pool = await asyncio.wait_for(
                asyncpg.create_pool(
                    dsn=self.config.dsn,
                    min_size=1,
                    max_size=self.config.max_connections,
                    timeout=self.config.connection_timeout,
                ),
                timeout=self.config.connection_timeout,
            )
            await self._ensure_extension()
            self._using_postgres = True
            logger.info(
                "Connected to pgvector at %s:%d/%s",
                self.config.host,
                self.config.port,
                self.config.dbname,
            )
            return True
        except ImportError:
            logger.info("asyncpg not available; using in-memory vector store")
        except Exception:
            logger.warning(
                "Could not connect to Postgres at %s:%d; using in-memory fallback",
                self.config.host,
                self.config.port,
            )

        self._using_postgres = False
        self._fallback = InMemoryVectorStore(vector_dim=self.config.vector_dim)
        return False

    async def insert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        Insert vectors into a collection.

        Args:
            collection: Collection/table name
            vectors: List of embedding vectors
            metadata: Optional list of metadata dicts, one per vector

        Returns:
            List of inserted record IDs
        """
        if not self._using_postgres and self._fallback:
            return self._fallback.insert(collection, vectors, metadata)

        meta_list = metadata or [{}] * len(vectors)
        ids: list[str] = []
        async with self._pool.acquire() as conn:
            await conn.execute(self._ensure_table_sql(collection))
            for vec, meta in zip(vectors, meta_list):
                record_id = meta.get("id", str(uuid4()))
                await conn.execute(
                    f"INSERT INTO {collection} (id, embedding, metadata) VALUES ($1, $2, $3)",
                    record_id,
                    vec,
                    meta,
                )
                ids.append(record_id)
        logger.debug("Inserted %d vectors into pgvector table '%s'", len(ids), collection)
        return ids

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for nearest neighbors using cosine distance.

        Args:
            collection: Collection/table name
            query_vector: Query embedding
            top_k: Maximum results
            filters: Optional metadata filter (as JSONB containment)

        Returns:
            List of result dicts with keys: id, metadata, score
        """
        if not self._using_postgres and self._fallback:
            return self._fallback.search(collection, query_vector, top_k, filters)

        try:
            async with self._pool.acquire() as conn:
                if filters:
                    results = await conn.fetch(
                        f"""
                        SELECT id, metadata,
                               1 - (embedding <=> $1) AS score
                        FROM {collection}
                        WHERE metadata @> $2
                        ORDER BY embedding <=> $1
                        LIMIT $3
                        """,
                        query_vector,
                        filters,
                        top_k,
                    )
                else:
                    results = await conn.fetch(
                        f"""
                        SELECT id, metadata,
                               1 - (embedding <=> $1) AS score
                        FROM {collection}
                        ORDER BY embedding <=> $1
                        LIMIT $2
                        """,
                        query_vector,
                        top_k,
                    )
            return [
                {"id": row["id"], "metadata": row["metadata"], "score": float(row["score"])}
                for row in results
            ]
        except Exception:
            logger.exception("pgvector search failed")
            return []

    async def delete(self, collection: str, ids: list[str]) -> int:
        """
        Remove vectors by ID from a collection.

        Args:
            collection: Collection/table name
            ids: List of record IDs to remove

        Returns:
            Number of records deleted
        """
        if not self._using_postgres and self._fallback:
            return self._fallback.delete(collection, ids)

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {collection} WHERE id = ANY($1)", ids
                )
                deleted = int(result.split()[-1]) if result else 0
            logger.debug("Deleted %d vectors from pgvector table '%s'", deleted, collection)
            return deleted
        except Exception:
            logger.exception("pgvector delete failed")
            return 0

    async def create_index(
        self,
        collection: str,
        index_type: str = "ivfflat",
        num_lists: int = 100,
        m: int = 16,
    ) -> bool:
        """
        Create an ANN index on a collection.

        Args:
            collection: Collection/table name
            index_type: "ivfflat" or "hnsw"
            num_lists: Number of IVF lists (for ivfflat)
            m: HNSW parameter (for hnsw)

        Returns:
            True if index was created
        """
        if not self._using_postgres:
            logger.info("Index creation skipped: using in-memory fallback")
            return False

        try:
            index_name = f"{collection}_{index_type}_idx"
            async with self._pool.acquire() as conn:
                if index_type == "hnsw":
                    await conn.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {collection} "
                        f"USING hnsw (embedding vector_cosine_ops) WITH (m = {m})"
                    )
                else:
                    await conn.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {collection} "
                        f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = {num_lists})"
                    )
            logger.info("Created %s index on '%s'", index_type, collection)
            return True
        except Exception:
            logger.exception("Failed to create index on '%s'", collection)
            return False

    async def health_check(self) -> bool:
        """
        Verify the store connection is healthy.

        Returns:
            True if the connection is usable
        """
        if not self._using_postgres:
            return self._fallback is not None

        try:
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            logger.warning("Postgres health check failed")
            return False

    async def _ensure_extension(self) -> None:
        """Ensure pgvector extension is enabled."""
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    def _ensure_table_sql(self, collection: str) -> str:
        """Generate table creation SQL for a collection."""
        return (
            f"CREATE TABLE IF NOT EXISTS {collection} ("
            f"id TEXT PRIMARY KEY, "
            f"embedding vector({self.config.vector_dim}), "
            f"metadata JSONB DEFAULT '{{}}', "
            f"created_at TIMESTAMPTZ DEFAULT NOW()"
            f")"
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("PgVectorStore connection pool closed")

    @property
    def using_postgres(self) -> bool:
        """Whether the store is connected to Postgres."""
        return self._using_postgres


__all__ = [
    "PgVectorConfig",
    "PgVectorEmbedding",
    "InMemoryVectorStore",
    "PgVectorStore",
]
