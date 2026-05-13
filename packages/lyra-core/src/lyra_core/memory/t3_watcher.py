"""T3 Memory Filesystem Watcher (Phase M8).

Watches user.md and team.md for changes and automatically reloads T3 memory.
Uses watchdog for cross-platform filesystem monitoring.

Research grounding:
  - CoALA T3 procedural memory (markdown-first, git-synced)
  - Filesystem watcher pattern for hot-reload
  - Debouncing to avoid reload storms during rapid edits
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from threading import Lock, Thread
from typing import Callable

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

    class FileSystemEventHandler:  # type: ignore
        """Stub for when watchdog is not available."""

        pass

    class Observer:  # type: ignore
        """Stub for when watchdog is not available."""

        pass

    class FileSystemEvent:  # type: ignore
        """Stub for when watchdog is not available."""

        pass

from .schema import Fragment
from .t3_git_sync import GitSyncConfig, T3GitSync

logger = logging.getLogger(__name__)


class T3MemoryWatcher(FileSystemEventHandler):
    """Watches T3 memory files and triggers reload on changes.

    Features:
      - Debouncing: waits 500ms after last change before reloading
      - Thread-safe: uses lock to prevent concurrent reloads
      - Selective: only watches user.md and team.md
      - Git sync: optional pull before reload, commit/push after changes
    """

    def __init__(
        self,
        memory_dir: Path,
        on_reload: Callable[[list[Fragment]], None],
        debounce_seconds: float = 0.5,
        git_sync: T3GitSync | None = None,
    ):
        """Initialize T3 memory watcher.

        Args:
            memory_dir: Directory containing user.md and team.md
            on_reload: Callback invoked with new fragments after reload
            debounce_seconds: Wait time after last change before reloading
            git_sync: Optional git sync manager for version control
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog is required for T3 memory watching. "
                "Install with: pip install watchdog"
            )

        self.memory_dir = memory_dir
        self.on_reload = on_reload
        self.debounce_seconds = debounce_seconds
        self.git_sync = git_sync

        self._lock = Lock()
        self._pending_reload = False
        self._last_change_time: float | None = None
        self._debounce_thread: Thread | None = None
        self._observer: "Observer | None" = None
        self._last_modified_file: str | None = None

    def start(self) -> None:
        """Start watching T3 memory files."""
        if not self.memory_dir.exists():
            logger.warning(f"T3 memory directory does not exist: {self.memory_dir}")
            return

        observer = Observer()
        observer.schedule(self, str(self.memory_dir), recursive=False)
        observer.start()
        self._observer = observer
        logger.info(f"T3 memory watcher started: {self.memory_dir}")

    def stop(self) -> None:
        """Stop watching T3 memory files."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("T3 memory watcher stopped")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.name not in ("user.md", "team.md"):
            return

        logger.debug(f"T3 memory file changed: {file_path.name}")

        # Track which file was modified for git sync
        self._last_modified_file = file_path.stem  # "user" or "team"

        self._schedule_reload()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self.on_modified(event)

    def _schedule_reload(self) -> None:
        """Schedule a debounced reload."""
        with self._lock:
            self._last_change_time = time.time()
            if not self._pending_reload:
                self._pending_reload = True
                self._debounce_thread = Thread(target=self._debounce_and_reload)
                self._debounce_thread.daemon = True
                self._debounce_thread.start()

    def _debounce_and_reload(self) -> None:
        """Wait for debounce period, then reload if no new changes."""
        while True:
            time.sleep(self.debounce_seconds)

            with self._lock:
                if self._last_change_time is None:
                    break

                elapsed = time.time() - self._last_change_time
                if elapsed >= self.debounce_seconds:
                    self._pending_reload = False
                    self._last_change_time = None
                    break

        # Reload outside lock to avoid blocking file events
        self._reload_memory()

    def _reload_memory(self) -> None:
        """Reload T3 memory from disk and invoke callback."""
        try:
            from .t3_loader import load_team_memory, load_user_memory

            repo_root = self.memory_dir.parent.parent  # .lyra/memory -> repo root

            # Git sync: pull before reload to get team updates
            if self.git_sync:
                pull_result = self.git_sync.sync_before_reload()
                if not pull_result.success:
                    logger.warning(f"Git pull failed: {pull_result.message}")
                    if pull_result.conflicts:
                        logger.error(f"Conflicts detected: {pull_result.conflicts}")
                        # TODO: Implement conflict resolution UI

            fragments: list[Fragment] = []

            user_file = self.memory_dir / "user.md"
            if user_file.exists():
                fragments.extend(load_user_memory(repo_root))

            team_file = self.memory_dir / "team.md"
            if team_file.exists():
                fragments.extend(load_team_memory(repo_root))

            logger.info(f"T3 memory reloaded: {len(fragments)} fragments")
            self.on_reload(fragments)

            # Git sync: commit and push after reload
            if self.git_sync and self._last_modified_file:
                file_type = self._last_modified_file  # "user" or "team"
                sync_results = self.git_sync.sync_after_change(file_type)  # type: ignore
                for result in sync_results:
                    if not result.success:
                        logger.warning(
                            f"Git {result.operation} failed: {result.message}"
                        )
                    else:
                        logger.debug(f"Git {result.operation}: {result.message}")

        except Exception as e:
            logger.error(f"Failed to reload T3 memory: {e}", exc_info=True)


def start_t3_watcher(
    repo_root: Path,
    on_reload: Callable[[list[Fragment]], None],
    debounce_seconds: float = 0.5,
    git_sync: T3GitSync | None = None,
) -> T3MemoryWatcher | None:
    """Start watching T3 memory files.

    Args:
        repo_root: Repository root directory
        on_reload: Callback invoked with new fragments after reload
        debounce_seconds: Wait time after last change before reloading
        git_sync: Optional git sync manager for version control

    Returns:
        T3MemoryWatcher instance if watchdog is available, None otherwise
    """
    if not WATCHDOG_AVAILABLE:
        logger.warning(
            "watchdog not available, T3 memory watching disabled. "
            "Install with: pip install watchdog"
        )
        return None

    memory_dir = repo_root / ".lyra" / "memory"
    watcher = T3MemoryWatcher(memory_dir, on_reload, debounce_seconds, git_sync)
    watcher.start()
    return watcher


__all__ = [
    "T3MemoryWatcher",
    "start_t3_watcher",
    "WATCHDOG_AVAILABLE",
]
