"""
Tests for Postgres Vector Store (pgvector + pgvectorscale).

Covers:
- PgVectorConfig from env vars
- PgVectorEmbedding model wrapper
- InMemoryVectorStore insert, search, delete, filtering
- PgVectorStore initialization and fallback behavior
- PgVectorEmbedding with various providers
"""


import pytest

from lyra_memory.pgvector_store import (
    InMemoryVectorStore,
    PgVectorConfig,
    PgVectorEmbedding,
    PgVectorStore,
)


class TestPgVectorConfig:
    """Tests for PgVectorConfig frozen dataclass."""

    def test_default_config(self):
        config = PgVectorConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.dbname == "lyra_memory"
        assert config.vector_dim == 384

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("PGVECTOR_HOST", "pg.example.com")
        monkeypatch.setenv("PGVECTOR_PORT", "6432")
        monkeypatch.setenv("PGVECTOR_DBNAME", "vectors")
        monkeypatch.setenv("PGVECTOR_USER", "admin")
        monkeypatch.setenv("PGVECTOR_PASSWORD", "secret")
        monkeypatch.setenv("PGVECTOR_VECTOR_DIM", "768")

        config = PgVectorConfig()
        assert config.host == "pg.example.com"
        assert config.port == 6432
        assert config.dbname == "vectors"
        assert config.user == "admin"
        assert config.password == "secret"
        assert config.vector_dim == 768

    def test_dsn_property(self):
        config = PgVectorConfig(
            host="db.local",
            port=5432,
            dbname="testdb",
            user="user",
            password="pass",
        )
        dsn = config.dsn
        assert "db.local" in dsn
        assert "5432" in dsn
        assert "testdb" in dsn

    def test_config_immutable(self):
        config = PgVectorConfig()
        with pytest.raises(Exception):
            config.host = "changed"  # type: ignore[misc]


class TestPgVectorEmbedding:
    """Tests for the embedding model wrapper."""

    def test_sentence_transformers_default(self):
        embedder = PgVectorEmbedding(provider="sentence-transformers")
        assert embedder.provider == "sentence-transformers"
        assert embedder.vector_dim == 384

    def test_sentence_transformers_encode(self):
        embedder = PgVectorEmbedding(provider="sentence-transformers")
        vec = embedder.encode("hello world")
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            PgVectorEmbedding(provider="unknown")

    def test_openai_provider_no_key(self):
        embedder = PgVectorEmbedding(provider="openai")
        vec = embedder.encode("test")
        assert isinstance(vec, list)
        # Returns zero vector when no API key configured
        assert len(vec) == 384

    def test_openai_provider_with_key(self):
        embedder = PgVectorEmbedding(
            provider="openai",
            openai_api_key="sk-test-key",
        )
        assert embedder._api_key == "sk-test-key"


class TestInMemoryVectorStore:
    """Tests for the InMemoryVectorStore fallback."""

    def setup_method(self):
        self.store = InMemoryVectorStore(vector_dim=3)

    def test_insert_and_search(self):
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        metadata = [
            {"label": "x"},
            {"label": "y"},
            {"label": "z"},
        ]
        ids = self.store.insert("test_collection", vectors, metadata)
        assert len(ids) == 3

        results = self.store.search("test_collection", [1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["metadata"]["label"] == "x"
        assert results[0]["score"] > 0.99

    def test_search_with_filters(self):
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        metadata = [
            {"label": "cat", "category": "animal"},
            {"label": "dog", "category": "animal"},
        ]
        self.store.insert("animals", vectors, metadata)

        results = self.store.search(
            "animals",
            [1.0, 0.0, 0.0],
            top_k=10,
            filters={"category": "animal"},
        )
        assert len(results) == 2

    def test_delete(self):
        vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        ids = self.store.insert("del_test", vectors)
        assert len(ids) == 2

        deleted = self.store.delete("del_test", [ids[0]])
        assert deleted == 1

        results = self.store.search("del_test", [1.0, 0.0, 0.0])
        assert len(results) == 1

    def test_delete_nonexistent(self):
        deleted = self.store.delete("nonexistent", ["id1"])
        assert deleted == 0

    def test_list_collections(self):
        self.store.insert("col_a", [[1.0, 2.0, 3.0]])
        self.store.insert("col_b", [[4.0, 5.0, 6.0]])
        cols = self.store.list_collections()
        assert "col_a" in cols
        assert "col_b" in cols

    def test_collection_size(self):
        vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        self.store.insert("sized", vectors)
        assert self.store.collection_size("sized") == 2
        assert self.store.collection_size("nonexistent") == 0

    def test_get_collection(self):
        vectors = [[1.0, 0.0, 0.0]]
        metadata = [{"name": "test"}]
        ids = self.store.insert("get_test", vectors, metadata)

        collection = self.store.get_collection("get_test")
        assert ids[0] in collection
        assert collection[ids[0]]["metadata"]["name"] == "test"

    def test_search_empty_collection(self):
        results = self.store.search("empty", [1.0, 0.0, 0.0])
        assert results == []

    def test_search_with_zero_query_vector(self):
        vectors = [[1.0, 0.0, 0.0]]
        self.store.insert("zq", vectors)
        results = self.store.search("zq", [0.0, 0.0, 0.0])
        assert results == []

    def test_insert_with_metadata_ids(self):
        vectors = [[1.0, 0.0, 0.0]]
        metadata = [{"id": "custom_id_123", "label": "custom"}]
        ids = self.store.insert("custom_ids", vectors, metadata)
        assert ids[0] == "custom_id_123"


class TestPgVectorStore:
    """Tests for PgVectorStore (primarily fallback behavior)."""

    @pytest.mark.asyncio
    async def test_initialize_fallback(self):
        store = PgVectorStore()
        pg_available = await store.initialize()
        assert pg_available is False
        assert store.using_postgres is False
        assert store._fallback is not None
        await store.close()

    @pytest.mark.asyncio
    async def test_insert_via_fallback(self):
        store = PgVectorStore()
        await store.initialize()
        ids = await store.insert(
            "test_coll",
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            [{"label": "a"}, {"label": "b"}],
        )
        assert len(ids) == 2
        await store.close()

    @pytest.mark.asyncio
    async def test_search_via_fallback(self):
        store = PgVectorStore()
        await store.initialize()
        await store.insert("search_coll", [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
        results = await store.search("search_coll", [1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0]["score"] > 0.99
        await store.close()

    @pytest.mark.asyncio
    async def test_delete_via_fallback(self):
        store = PgVectorStore()
        await store.initialize()
        ids = await store.insert("del_coll", [[1.0, 0.0, 0.0]])
        deleted = await store.delete("del_coll", ids)
        assert deleted == 1
        await store.close()

    @pytest.mark.asyncio
    async def test_health_check_fallback(self):
        store = PgVectorStore()
        await store.initialize()
        healthy = await store.health_check()
        assert healthy is True
        await store.close()

    @pytest.mark.asyncio
    async def test_create_index_fallback(self):
        store = PgVectorStore()
        await store.initialize()
        created = await store.create_index("test_coll", index_type="ivfflat")
        assert created is False  # index not created on fallback
        await store.close()

    @pytest.mark.asyncio
    async def test_custom_config(self):
        config = PgVectorConfig(host="unreachable.local", connection_timeout=1)
        store = PgVectorStore(config=config)
        result = await store.initialize()
        assert result is False
        await store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
