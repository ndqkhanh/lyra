"""Multi-Level Cache — L1 (memory) → L2 (disk) → L3 (remote) with TTL and LRU.

Provides a unified caching interface across three tiers:
  - L1: In-memory LRU cache (fastest, smallest)
  - L2: Disk-backed persistent cache (medium speed/size)
  - L3: Remote cache (slowest, largest — Redis/Memcached compatible)

Each level can have independent TTL and capacity constraints.
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CacheConfig:
    l1_max_items: int = 512
    l2_max_bytes: int = 100 * 1024 * 1024  # 100 MB
    l1_ttl_sec: float = 60.0
    l2_ttl_sec: float = 3600.0
    l3_ttl_sec: float = 86400.0
    disk_path: str = "/tmp/lyra_cache"
    l3_connection_url: str = ""


@dataclass
class CacheStats:
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    misses: int = 0
    l1_size: int = 0
    l2_size: int = 0

    @property
    def total_hits(self) -> int:
        return self.l1_hits + self.l2_hits + self.l3_hits

    @property
    def hit_rate(self) -> float:
        total = self.total_hits + self.misses
        return self.total_hits / total if total > 0 else 0.0


class MultiLevelCache:
    """Three-tier cache with LRU eviction at each level."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        self.config = config or CacheConfig()
        self._l1: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._l2_path = Path(self.config.disk_path) / "l2"
        self._l3: dict[str, object] = {}  # simplified in-memory L3
        self._stats = CacheStats()
        self._ensure_disk_path()

    def _ensure_disk_path(self) -> None:
        self._l2_path.mkdir(parents=True, exist_ok=True)

    @property
    def stats(self) -> CacheStats:
        self._stats.l1_size = len(self._l1)
        self._stats.l2_size = self._l2_item_count()
        return self._stats

    # ── public API ─────────────────────────────────────────────────

    def get(self, key: str) -> object | None:
        # L1 check
        if key in self._l1:
            value, expires = self._l1[key]
            if time.time() < expires:
                self._l1.move_to_end(key)
                self._stats.l1_hits += 1
                return value
            del self._l1[key]

        # L2 check
        disk_val, disk_exp = self._get_disk(key)
        if disk_val is not None and time.time() < disk_exp:
            self._stats.l2_hits += 1
            self._promote_to_l1(key, disk_val, self.config.l1_ttl_sec)
            return disk_val

        # L3 check
        if key in self._l3:
            val = self._l3[key]
            self._stats.l3_hits += 1
            self._promote_to_l1(key, val, self.config.l1_ttl_sec)
            return val

        self._stats.misses += 1
        return None

    def set(self, key: str, value: object, ttl_sec: float | None = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.config.l1_ttl_sec
        self._set_l1(key, value, ttl)
        self._set_disk(key, value, max(ttl, self.config.l2_ttl_sec))

    def set_l3(self, key: str, value: object) -> None:
        self._l3[key] = value

    def invalidate(self, key: str) -> None:
        self._l1.pop(key, None)
        self._delete_disk(key)
        self._l3.pop(key, None)

    def clear(self) -> None:
        self._l1.clear()
        self._l3.clear()
        for f in self._l2_path.glob("*.json"):
            f.unlink(missing_ok=True)
        self._stats = CacheStats()

    # ── L1 (memory) ────────────────────────────────────────────────

    def _set_l1(self, key: str, value: object, ttl_sec: float) -> None:
        if key in self._l1:
            self._l1.move_to_end(key)
        self._l1[key] = (value, time.time() + ttl_sec)
        while len(self._l1) > self.config.l1_max_items:
            self._l1.popitem(last=False)

    def _promote_to_l1(self, key: str, value: object, ttl_sec: float) -> None:
        self._set_l1(key, value, ttl_sec)

    # ── L2 (disk) ──────────────────────────────────────────────────

    def _disk_key_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(":", "_")
        return self._l2_path / f"{safe}.json"

    def _get_disk(self, key: str) -> tuple[object | None, float]:
        path = self._disk_key_path(key)
        if not path.exists():
            return None, 0.0
        try:
            data = json.loads(path.read_text())
            return data.get("value"), float(data.get("expires_at", 0))
        except (json.JSONDecodeError, OSError, ValueError):
            return None, 0.0

    def _set_disk(self, key: str, value: object, ttl_sec: float) -> None:
        try:
            data = {"value": value, "expires_at": time.time() + ttl_sec}
            path = self._disk_key_path(key)
            path.write_text(json.dumps(data))

            # Enforce L2 size limit
            total = sum(
                f.stat().st_size for f in self._l2_path.glob("*.json")
                if f.is_file()
            )
            if total > self.config.l2_max_bytes:
                files = sorted(self._l2_path.glob("*.json"), key=lambda f: f.stat().st_mtime)
                for f in files:
                    if total <= self.config.l2_max_bytes * 0.8:
                        break
                    total -= f.stat().st_size
                    f.unlink(missing_ok=True)
        except OSError:
            pass

    def _delete_disk(self, key: str) -> None:
        self._disk_key_path(key).unlink(missing_ok=True)

    def _l2_item_count(self) -> int:
        return len(list(self._l2_path.glob("*.json")))
