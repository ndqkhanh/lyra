"""State store for team-level shared memory.

Provides abstract interface and in-memory implementation for storing
and retrieving team state, artifacts, and shared data.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any


class StateStore(ABC):
    """Abstract base class for state store implementations.

    The state store manages team-level shared memory, including
    requirements, architecture decisions, code artifacts, and
    coordination state.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value from the state store.

        Args:
            key: Key to retrieve

        Returns:
            Value associated with key, or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        """Set a value in the state store.

        Args:
            key: Key to set
            value: Value to store
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from the state store.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys in the state store.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of keys matching the prefix
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the state store.

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all keys from the state store.

        Warning: This operation is destructive and cannot be undone.
        """
        pass


class InMemoryStateStore(StateStore):
    """In-memory implementation of state store for testing.

    Uses a dictionary for storage with asyncio locks for thread safety.
    Not suitable for production (no persistence, no distribution), but
    useful for testing and development.
    """

    def __init__(self) -> None:
        """Initialize in-memory state store."""
        self._store: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get a value from the state store.

        Args:
            key: Key to retrieve

        Returns:
            Value associated with key, or None if not found
        """
        async with self._lock:
            return self._store.get(key)

    async def set(self, key: str, value: Any) -> None:
        """Set a value in the state store.

        Args:
            key: Key to set
            value: Value to store
        """
        async with self._lock:
            self._store[key] = value

    async def delete(self, key: str) -> bool:
        """Delete a key from the state store.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys in the state store.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of keys matching the prefix
        """
        async with self._lock:
            if prefix:
                return [k for k in self._store.keys() if k.startswith(prefix)]
            return list(self._store.keys())

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the state store.

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        async with self._lock:
            return key in self._store

    async def clear(self) -> None:
        """Clear all keys from the state store.

        Warning: This operation is destructive and cannot be undone.
        """
        async with self._lock:
            self._store.clear()

    async def get_all(self) -> dict[str, Any]:
        """Get all key-value pairs from the state store.

        Returns:
            Dictionary of all key-value pairs
        """
        async with self._lock:
            return dict(self._store)

    async def size(self) -> int:
        """Get the number of keys in the state store.

        Returns:
            Number of keys
        """
        async with self._lock:
            return len(self._store)


__all__ = ["StateStore", "InMemoryStateStore"]
