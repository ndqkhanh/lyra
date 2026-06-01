"""File system watcher for plugin hot-reload.

Provides a thread-safe file system watcher that monitors plugin directories
and triggers reload callbacks when changes are detected.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WatcherConfig:
    """Configuration for file system watcher."""

    poll_interval_seconds: float = 1.0
    file_patterns: tuple[str, ...] = ("*.py",)
    ignore_patterns: tuple[str, ...] = ("__pycache__", "*.pyc", ".git")
    recursive: bool = True


@dataclass
class FileChangeEvent:
    """Represents a file system change event."""

    path: Path
    event_type: str  # "created", "modified", "deleted"
    timestamp: float


class PluginWatcher:
    """Thread-safe file system watcher for plugin directories.

    Usage::

        watcher = PluginWatcher()
        watcher.add_directory("/path/to/plugins")
        watcher.on_change(lambda event: print(f"Changed: {event.path}"))
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, config: WatcherConfig | None = None) -> None:
        self._config = config or WatcherConfig()
        self._directories: set[Path] = set()
        self._callbacks: list[Callable[[FileChangeEvent], None]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._file_states: dict[Path, tuple[float, int]] = {}

    def add_directory(self, path: str | Path) -> None:
        """Add a directory to watch."""
        with self._lock:
            dir_path = Path(path).resolve()
            if not dir_path.is_dir():
                raise ValueError(f"Not a directory: {path}")
            self._directories.add(dir_path)
            self._scan_directory(dir_path)

    def remove_directory(self, path: str | Path) -> None:
        """Remove a directory from watch list."""
        with self._lock:
            dir_path = Path(path).resolve()
            self._directories.discard(dir_path)
            # Remove file states for this directory
            to_remove = [
                p for p in self._file_states if p.is_relative_to(dir_path)
            ]
            for p in to_remove:
                del self._file_states[p]

    def on_change(self, callback: Callable[[FileChangeEvent], None]) -> None:
        """Register a callback for file change events."""
        with self._lock:
            self._callbacks.append(callback)

    def start(self) -> None:
        """Start watching in a background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._watch_loop, daemon=True, name="PluginWatcher"
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop watching and wait for thread to finish."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        """Check if watcher is currently running."""
        with self._lock:
            return self._running

    @property
    def watched_directories(self) -> tuple[Path, ...]:
        """Get list of watched directories."""
        with self._lock:
            return tuple(self._directories)

    def _scan_directory(self, directory: Path) -> None:
        """Scan directory and record initial file states."""
        if not directory.exists():
            return

        for pattern in self._config.file_patterns:
            if self._config.recursive:
                files = directory.rglob(pattern)
            else:
                files = directory.glob(pattern)

            for file_path in files:
                if self._should_ignore(file_path):
                    continue
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        self._file_states[file_path] = (
                            stat.st_mtime,
                            stat.st_size,
                        )
                    except (OSError, PermissionError):
                        pass

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)
        for pattern in self._config.ignore_patterns:
            if pattern in path_str:
                return True
        return False

    def _watch_loop(self) -> None:
        """Main watch loop running in background thread."""
        while self._running:
            try:
                self._check_changes()
            except Exception:  # noqa: BLE001
                # Silently continue on errors to keep watcher alive
                pass

            time.sleep(self._config.poll_interval_seconds)

    def _check_changes(self) -> None:
        """Check for file changes and trigger callbacks."""
        with self._lock:
            current_files: set[Path] = set()
            events: list[FileChangeEvent] = []

            # Scan all watched directories
            for directory in self._directories:
                if not directory.exists():
                    continue

                for pattern in self._config.file_patterns:
                    if self._config.recursive:
                        files = directory.rglob(pattern)
                    else:
                        files = directory.glob(pattern)

                    for file_path in files:
                        if self._should_ignore(file_path):
                            continue
                        if not file_path.is_file():
                            continue

                        current_files.add(file_path)

                        try:
                            stat = file_path.stat()
                            current_state = (stat.st_mtime, stat.st_size)

                            if file_path not in self._file_states:
                                # New file
                                events.append(
                                    FileChangeEvent(
                                        path=file_path,
                                        event_type="created",
                                        timestamp=time.time(),
                                    )
                                )
                                self._file_states[file_path] = current_state
                            elif self._file_states[file_path] != current_state:
                                # Modified file
                                events.append(
                                    FileChangeEvent(
                                        path=file_path,
                                        event_type="modified",
                                        timestamp=time.time(),
                                    )
                                )
                                self._file_states[file_path] = current_state
                        except (OSError, PermissionError):
                            pass

            # Check for deleted files
            deleted_files = set(self._file_states.keys()) - current_files
            for file_path in deleted_files:
                events.append(
                    FileChangeEvent(
                        path=file_path,
                        event_type="deleted",
                        timestamp=time.time(),
                    )
                )
                del self._file_states[file_path]

            # Trigger callbacks outside the lock
            callbacks = list(self._callbacks)

        # Call callbacks without holding lock
        for event in events:
            for callback in callbacks:
                try:
                    callback(event)
                except Exception:  # noqa: BLE001
                    # Don't let callback errors stop the watcher
                    pass


__all__ = [
    "FileChangeEvent",
    "PluginWatcher",
    "WatcherConfig",
]
