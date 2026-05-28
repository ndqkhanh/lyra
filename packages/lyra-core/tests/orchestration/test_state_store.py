"""Tests for state store module."""

import pytest
from lyra_core.orchestration.state_store import InMemoryStateStore


@pytest.fixture
def state_store() -> InMemoryStateStore:
    """Create a state store for testing."""
    return InMemoryStateStore()


class TestInMemoryStateStore:
    """Tests for InMemoryStateStore."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, state_store: InMemoryStateStore) -> None:
        """Test setting and getting values."""
        await state_store.set("key1", "value1")
        value = await state_store.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, state_store: InMemoryStateStore) -> None:
        """Test getting a non-existent key returns None."""
        value = await state_store.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_overwrites(self, state_store: InMemoryStateStore) -> None:
        """Test that setting a key overwrites previous value."""
        await state_store.set("key1", "value1")
        await state_store.set("key1", "value2")
        value = await state_store.get("key1")
        assert value == "value2"

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, state_store: InMemoryStateStore) -> None:
        """Test deleting an existing key."""
        await state_store.set("key1", "value1")
        result = await state_store.delete("key1")
        assert result is True
        value = await state_store.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(
        self, state_store: InMemoryStateStore
    ) -> None:
        """Test deleting a non-existent key returns False."""
        result = await state_store.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, state_store: InMemoryStateStore) -> None:
        """Test checking if key exists."""
        assert await state_store.exists("key1") is False

        await state_store.set("key1", "value1")
        assert await state_store.exists("key1") is True

        await state_store.delete("key1")
        assert await state_store.exists("key1") is False

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, state_store: InMemoryStateStore) -> None:
        """Test listing keys when store is empty."""
        keys = await state_store.list_keys()
        assert keys == []

    @pytest.mark.asyncio
    async def test_list_keys_all(self, state_store: InMemoryStateStore) -> None:
        """Test listing all keys."""
        await state_store.set("key1", "value1")
        await state_store.set("key2", "value2")
        await state_store.set("key3", "value3")

        keys = await state_store.list_keys()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    @pytest.mark.asyncio
    async def test_list_keys_with_prefix(
        self, state_store: InMemoryStateStore
    ) -> None:
        """Test listing keys with prefix filter."""
        await state_store.set("team:1:agent:1", "data1")
        await state_store.set("team:1:agent:2", "data2")
        await state_store.set("team:2:agent:1", "data3")
        await state_store.set("config:setting", "data4")

        # List keys with team:1 prefix
        keys = await state_store.list_keys("team:1")
        assert len(keys) == 2
        assert "team:1:agent:1" in keys
        assert "team:1:agent:2" in keys

        # List keys with team:2 prefix
        keys = await state_store.list_keys("team:2")
        assert len(keys) == 1
        assert "team:2:agent:1" in keys

        # List keys with config prefix
        keys = await state_store.list_keys("config")
        assert len(keys) == 1
        assert "config:setting" in keys

    @pytest.mark.asyncio
    async def test_clear(self, state_store: InMemoryStateStore) -> None:
        """Test clearing all keys."""
        await state_store.set("key1", "value1")
        await state_store.set("key2", "value2")
        await state_store.set("key3", "value3")

        assert await state_store.size() == 3

        await state_store.clear()

        assert await state_store.size() == 0
        keys = await state_store.list_keys()
        assert keys == []

    @pytest.mark.asyncio
    async def test_get_all(self, state_store: InMemoryStateStore) -> None:
        """Test getting all key-value pairs."""
        await state_store.set("key1", "value1")
        await state_store.set("key2", "value2")
        await state_store.set("key3", "value3")

        all_data = await state_store.get_all()

        assert len(all_data) == 3
        assert all_data["key1"] == "value1"
        assert all_data["key2"] == "value2"
        assert all_data["key3"] == "value3"

    @pytest.mark.asyncio
    async def test_size(self, state_store: InMemoryStateStore) -> None:
        """Test getting the size of the store."""
        assert await state_store.size() == 0

        await state_store.set("key1", "value1")
        assert await state_store.size() == 1

        await state_store.set("key2", "value2")
        assert await state_store.size() == 2

        await state_store.delete("key1")
        assert await state_store.size() == 1

        await state_store.clear()
        assert await state_store.size() == 0

    @pytest.mark.asyncio
    async def test_store_complex_values(
        self, state_store: InMemoryStateStore
    ) -> None:
        """Test storing complex data structures."""
        # Store dictionary
        data = {"name": "Agent 1", "role": "engineer", "capabilities": ["coding"]}
        await state_store.set("agent:1", data)
        retrieved = await state_store.get("agent:1")
        assert retrieved == data

        # Store list
        tasks = ["task1", "task2", "task3"]
        await state_store.set("tasks", tasks)
        retrieved = await state_store.get("tasks")
        assert retrieved == tasks

        # Store nested structure
        nested = {
            "team": {
                "id": "team-1",
                "agents": [{"id": "agent-1"}, {"id": "agent-2"}],
            }
        }
        await state_store.set("team:1:data", nested)
        retrieved = await state_store.get("team:1:data")
        assert retrieved == nested

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self, state_store: InMemoryStateStore
    ) -> None:
        """Test concurrent set/get operations."""
        import asyncio

        async def set_value(key: str, value: str) -> None:
            await state_store.set(key, value)

        async def get_value(key: str) -> str | None:
            return await state_store.get(key)

        # Set multiple values concurrently
        await asyncio.gather(
            set_value("key1", "value1"),
            set_value("key2", "value2"),
            set_value("key3", "value3"),
        )

        # Get multiple values concurrently
        results = await asyncio.gather(
            get_value("key1"),
            get_value("key2"),
            get_value("key3"),
        )

        assert results == ["value1", "value2", "value3"]
