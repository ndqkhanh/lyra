"""Phase 4.1b — Plugin Hot-Reload System.

Watches plugin directories for file changes and automatically
reloads plugins without restarting the agent process.

Uses polling-based file watching with hash-based change detection
for cross-platform compatibility.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class ReloadStatus(Enum):
    LOADED = "loaded"
    RELOADED = "reloaded"
    FAILED = "failed"
    UNCHANGED = "unchanged"
    REMOVED = "removed"


@dataclass(frozen=True)
class PluginFileState:
    """Hash-based snapshot of a plugin file at a point in time."""

    file_path: str
    content_hash: str
    size_bytes: int
    mtime: float
    checked_at: float


@dataclass(frozen=True)
class ReloadEvent:
    """A single plugin reload event."""

    event_id: str
    plugin_path: str
    status: ReloadStatus
    old_hash: str | None
    new_hash: str | None
    error: str | None
    timestamp: float


def _file_hash(path: str) -> str:
    """SHA-256 hash of a file's contents."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, PermissionError):
        return ""


def _safe_stat(path: str) -> tuple[int, float]:
    """Get file size and mtime, or (0, 0) on error."""
    try:
        stat = os.stat(path)
        return stat.st_size, stat.st_mtime
    except (OSError, PermissionError):
        return 0, 0.0


@dataclass
class PluginHotReloader:
    """Watches plugin files and reloads them on change.

    Usage::

        reloader = PluginHotReloader()
        reloader.watch("/path/to/plugins/my_plugin.py")

        # In your main loop:
        events = reloader.poll()
        for event in events:
            if event.status == ReloadStatus.RELOADED:
                print(f"Reloaded: {event.plugin_path}")
    """

    _watched: dict[str, PluginFileState] = field(default_factory=dict)
    _on_reload: Callable[[str], None] | None = None
    _events: list[ReloadEvent] = field(default_factory=list)
    poll_interval_ms: float = 1000.0

    def watch(self, plugin_path: str) -> None:
        """Start watching a plugin file for changes."""
        abs_path = os.path.abspath(plugin_path)
        if abs_path in self._watched:
            return

        content_hash = _file_hash(abs_path)
        size, mtime = _safe_stat(abs_path)

        self._watched[abs_path] = PluginFileState(
            file_path=abs_path,
            content_hash=content_hash,
            size_bytes=size,
            mtime=mtime,
            checked_at=time.time(),
        )

    def unwatch(self, plugin_path: str) -> None:
        """Stop watching a plugin file."""
        abs_path = os.path.abspath(plugin_path)
        self._watched.pop(abs_path, None)

    def watch_directory(
        self, directory: str, pattern: str = "*.py"
    ) -> int:
        """Watch all matching files in a directory.

        Returns the number of files added to watch.
        """
        import fnmatch

        count = 0
        abs_dir = os.path.abspath(directory)
        if not os.path.isdir(abs_dir):
            return 0

        for entry in os.listdir(abs_dir):
            full_path = os.path.join(abs_dir, entry)
            if os.path.isfile(full_path) and fnmatch.fnmatch(entry, pattern):
                self.watch(full_path)
                count += 1

        return count

    def poll(self) -> tuple[ReloadEvent, ...]:
        """Check all watched files for changes.

        Returns a tuple of reload events for files that changed,
        were added, or were removed since the last poll.
        """
        events: list[ReloadEvent] = []
        now = time.time()

        removed: list[str] = []
        for abs_path, state in self._watched.items():
            if not os.path.exists(abs_path):
                event = ReloadEvent(
                    event_id=f"re-{uuid.uuid4().hex[:12]}",
                    plugin_path=abs_path,
                    status=ReloadStatus.REMOVED,
                    old_hash=state.content_hash,
                    new_hash=None,
                    error=None,
                    timestamp=now,
                )
                events.append(event)
                removed.append(abs_path)
                continue

            new_hash = _file_hash(abs_path)
            if new_hash and new_hash != state.content_hash:
                try:
                    if self._on_reload:
                        self._on_reload(abs_path)
                    status = ReloadStatus.RELOADED
                    error = None
                except Exception as e:
                    status = ReloadStatus.FAILED
                    error = str(e)

                event = ReloadEvent(
                    event_id=f"re-{uuid.uuid4().hex[:12]}",
                    plugin_path=abs_path,
                    status=status,
                    old_hash=state.content_hash,
                    new_hash=new_hash,
                    error=error,
                    timestamp=now,
                )
                events.append(event)

                size, mtime = _safe_stat(abs_path)
                self._watched[abs_path] = PluginFileState(
                    file_path=abs_path,
                    content_hash=new_hash,
                    size_bytes=size,
                    mtime=mtime,
                    checked_at=now,
                )

        for path in removed:
            del self._watched[path]

        self._events.extend(events)
        return tuple(events)

    def on_reload(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when a plugin is reloaded.

        The callback receives the absolute path of the reloaded file.
        """
        self._on_reload = callback

    @property
    def watched_count(self) -> int:
        return len(self._watched)

    @property
    def watched_paths(self) -> tuple[str, ...]:
        return tuple(self._watched.keys())

    @property
    def events(self) -> tuple[ReloadEvent, ...]:
        return tuple(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    def stop(self) -> None:
        """Stop watching all files."""
        self._watched.clear()
        self._events.clear()


__all__ = [
    "PluginFileState",
    "PluginHotReloader",
    "ReloadEvent",
    "ReloadStatus",
]
