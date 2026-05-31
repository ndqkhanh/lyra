"""Filesystem as Externalized Context — P2-X #19 (HIGH, LOW).

Store bulky data (web pages, PDFs, logs) outside the context window.
Agents interact through filenames and paths, not raw content.
Restorable compression: drop content but preserve retrieval path.

See: plan-phase2-memory.md §Strategy 3
Ref: Manus Context Engineering §6.3
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Stored Item
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StoredItem:
    """Metadata for an item stored on the filesystem."""

    key: str
    path: str              # absolute path on filesystem
    content_hash: str       # SHA-256 for integrity verification
    content_type: str = ""  # mime type or category
    token_count: int = 0    # estimated token count
    size_bytes: int = 0
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Filesystem Context
# ---------------------------------------------------------------------------


@dataclass
class FilesystemContext:
    """External context that agents navigate via paths.

    Instead of loading all content into the context window, bulky data
    is stored on the filesystem. Agents reference it by path and retrieve
    on demand with token budgets.

    Usage::

        fctx = FilesystemContext(cache_dir="/tmp/lyra-context")
        path = fctx.store("page1", html_content, content_type="text/html")
        # Agent sees only the path, not the raw content
        content = fctx.retrieve(path, max_tokens=4000)
    """

    cache_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="lyra-fctx-")))
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    _index: dict[str, StoredItem] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # --- Store -----------------------------------------------------------------

    def store(
        self,
        key: str,
        data: str | bytes,
        *,
        content_type: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store data on the filesystem and return the retrieval path.

        The returned path is what agents see and use for later retrieval.
        Content is NOT loaded into context — only the path is visible.
        """
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        if len(data_bytes) > self.max_file_size:
            raise ValueError(
                f"data size {len(data_bytes)} exceeds max_file_size {self.max_file_size}"
            )

        content_hash = hashlib.sha256(data_bytes).hexdigest()

        # Deduplicate by hash
        for existing in self._index.values():
            if existing.content_hash == content_hash:
                return existing.path

        # Write to filesystem
        safe_key = _safe_filename(key)
        file_path = self.cache_dir / f"{safe_key}_{content_hash[:12]}"
        file_path.write_bytes(data_bytes)

        token_estimate = len(data_bytes) // 4  # rough: 4 chars ≈ 1 token

        item = StoredItem(
            key=key,
            path=str(file_path),
            content_hash=content_hash,
            content_type=content_type,
            token_count=token_estimate,
            size_bytes=len(data_bytes),
            created_at=file_path.stat().st_ctime,
            metadata=metadata or {},
        )
        self._index[key] = item
        return str(file_path)

    # --- Retrieve -------------------------------------------------------------

    def retrieve(
        self,
        path_or_key: str,
        *,
        max_tokens: int = 4000,
        encoding: str = "utf-8",
    ) -> str:
        """Retrieve content by path or key with a token budget.

        Content is truncated to *max_tokens* (rough char estimate:
        4 chars per token).
        """
        item = self._resolve(path_or_key)
        if item is None:
            raise KeyError(f"no stored item for: {path_or_key!r}")

        file_path = Path(item.path)
        if not file_path.exists():
            raise FileNotFoundError(f"stored file missing: {item.path}")

        content = file_path.read_text(encoding=encoding)
        return self._truncate_to_budget(content, max_tokens)

    def retrieve_bytes(self, path_or_key: str) -> bytes:
        """Retrieve raw bytes by path or key."""
        item = self._resolve(path_or_key)
        if item is None:
            raise KeyError(f"no stored item for: {path_or_key!r}")

        file_path = Path(item.path)
        if not file_path.exists():
            raise FileNotFoundError(f"stored file missing: {item.path}")

        return file_path.read_bytes()

    # --- Drop / Compress ------------------------------------------------------

    def drop(self, key: str) -> bool:
        """Drop content but preserve the retrieval path (restorable compression).

        The StoredItem metadata remains in the index so agents still see the
        path, but the file content is removed. A subsequent retrieve on the
        same key will raise FileNotFoundError.
        """
        item = self._index.get(key)
        if item is None:
            return False

        file_path = Path(item.path)
        if file_path.exists():
            file_path.unlink()
        return True

    def purge(self, key: str) -> bool:
        """Remove both the data file and the index entry."""
        item = self._index.pop(key, None)
        if item is None:
            return False

        file_path = Path(item.path)
        if file_path.exists():
            file_path.unlink()
        return True

    def truncate(self, path_or_key: str, max_tokens: int) -> str | None:
        """Truncate a stored file to a token budget in-place.

        Returns the truncated content, or None if the item doesn't exist.
        """
        item = self._resolve(path_or_key)
        if item is None:
            return None

        file_path = Path(item.path)
        if not file_path.exists():
            return None

        content = file_path.read_text()
        truncated = self._truncate_to_budget(content, max_tokens)
        file_path.write_text(truncated)
        return truncated

    # --- Introspection --------------------------------------------------------

    def get_item(self, key: str) -> StoredItem | None:
        """Get metadata for a stored item."""
        return self._index.get(key)

    def list_keys(self) -> list[str]:
        """List all stored item keys."""
        return sorted(self._index)

    @property
    def total_size_bytes(self) -> int:
        """Total size of all stored files."""
        total = 0
        for item in self._index.values():
            p = Path(item.path)
            if p.exists():
                total += p.stat().st_size
        return total

    @property
    def item_count(self) -> int:
        return len(self._index)

    # --- Cleanup --------------------------------------------------------------

    def clear(self) -> None:
        """Remove all stored files and clear the index."""
        for item in list(self._index.values()):
            p = Path(item.path)
            if p.exists():
                p.unlink()
        self._index.clear()

    def cleanup(self) -> None:
        """Remove the entire cache directory and its contents."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self._index.clear()

    # --- Helpers --------------------------------------------------------------

    def _resolve(self, path_or_key: str) -> StoredItem | None:
        """Resolve a path or key to a StoredItem."""
        # Try key lookup first
        item = self._index.get(path_or_key)
        if item is not None:
            return item
        # Try matching by path
        for item in self._index.values():
            if item.path == path_or_key:
                return item
        return None

    @staticmethod
    def _truncate_to_budget(content: str, max_tokens: int) -> str:
        """Truncate string content to a token budget."""
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content
        # Keep first 80% of budget for content, add truncation note
        cutoff = int(max_chars * 0.8)
        return content[:cutoff] + f"\n\n... [truncated to {max_tokens} tokens]"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_filename(key: str) -> str:
    """Sanitize a key into a safe filename component."""
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
    return safe[:64] if safe else "unnamed"


__all__ = [
    "FilesystemContext",
    "StoredItem",
]
