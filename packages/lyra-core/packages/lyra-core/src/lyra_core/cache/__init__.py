"""
Multi-Level Caching System

Implements comprehensive caching with:
- L1: In-memory LRU cache
- L2: Disk-based cache
- TTL support
- Cache invalidation strategies
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Callable
from collections import OrderedDict
import time
import json
import hashlib
from pathlib import Path


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    ttl: Optional[float] = None
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """Update access time and count"""
        self.accessed_at = time.time()
        self.access_count += 1


class LRUCache:
    """
    LRU (Least Recently Used) Cache

    Features:
    - Fixed capacity
    - Automatic eviction of least recently used items
    - O(1) get and put operations
    """

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            del self.cache[key]
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.touch()

        return entry.value

    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in cache"""
        if key in self.cache:
            # Update existing entry
            entry = self.cache[key]
            entry.value = value
            entry.ttl = ttl
            entry.touch()
            self.cache.move_to_end(key)
        else:
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl
            )
            self.cache[key] = entry

            # Evict if over capacity
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "utilization": len(self.cache) / self.capacity if self.capacity > 0 else 0
        }


class DiskCache:
    """
    Disk-based cache for persistent storage

    Features:
    - Persistent across restarts
    - Larger capacity than memory cache
    - Automatic cleanup of expired entries
    """

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get file path for key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        path = self._get_path(key)

        if not path.exists():
            return None

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            # Check expiration
            if data.get('ttl') and time.time() - data['created_at'] > data['ttl']:
                path.unlink()
                return None

            return data['value']
        except (json.JSONDecodeError, KeyError):
            return None

    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in disk cache"""
        path = self._get_path(key)

        data = {
            'key': key,
            'value': value,
            'created_at': time.time(),
            'ttl': ttl
        }

        with open(path, 'w') as f:
            json.dump(data, f)

    def invalidate(self, key: str) -> bool:
        """Invalidate disk cache entry"""
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self):
        """Clear all disk cache entries"""
        for path in self.cache_dir.glob("*.json"):
            path.unlink()


class MultiLevelCache:
    """
    Multi-level cache with L1 (memory) and L2 (disk)

    Features:
    - Fast L1 memory cache
    - Persistent L2 disk cache
    - Automatic promotion from L2 to L1
    - TTL support
    - Cache invalidation
    """

    def __init__(self, l1_capacity: int = 1000, cache_dir: str = ".cache"):
        self.l1 = LRUCache(capacity=l1_capacity)
        self.l2 = DiskCache(cache_dir=cache_dir)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 then L2)"""
        # Try L1 first
        value = self.l1.get(key)
        if value is not None:
            return value

        # Try L2
        value = self.l2.get(key)
        if value is not None:
            # Promote to L1
            self.l1.put(key, value)
            return value

        return None

    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in cache (both L1 and L2)"""
        self.l1.put(key, value, ttl=ttl)
        self.l2.put(key, value, ttl=ttl)

    def invalidate(self, key: str):
        """Invalidate cache entry in both levels"""
        self.l1.invalidate(key)
        self.l2.invalidate(key)

    def clear(self):
        """Clear all cache entries"""
        self.l1.clear()
        self.l2.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "l1": self.l1.get_stats(),
            "l2": {"cache_dir": str(self.l2.cache_dir)}
        }


def cached(ttl: Optional[float] = None, cache: Optional[MultiLevelCache] = None):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        _cache = cache or MultiLevelCache()

        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try cache first
            result = _cache.get(key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            _cache.put(key, result, ttl=ttl)
            return result

        return wrapper
    return decorator
