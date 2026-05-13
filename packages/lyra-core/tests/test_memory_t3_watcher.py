"""Tests for T3 Memory Filesystem Watcher (Phase M8)."""
from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

import pytest

from lyra_core.memory.schema import Fragment
from lyra_core.memory.t3_watcher import WATCHDOG_AVAILABLE, start_t3_watcher


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_t3_watcher_detects_user_md_changes(tmp_path: Path):
    """Test that watcher detects changes to user.md."""
    memory_dir = tmp_path / ".lyra" / "memory"
    memory_dir.mkdir(parents=True)

    user_file = memory_dir / "user.md"
    user_file.write_text(
        dedent("""
        # Preferences
        I prefer pytest over unittest.
    """).strip()
    )

    # Track reload calls
    reload_count = 0
    last_fragments: list[Fragment] = []

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count, last_fragments
        reload_count += 1
        last_fragments = fragments

    # Start watcher
    watcher = start_t3_watcher(tmp_path, on_reload, debounce_seconds=0.1)
    assert watcher is not None

    try:
        # Modify user.md
        user_file.write_text(
            dedent("""
            # Preferences
            I prefer pytest over unittest.

            # Decisions

            ## Use TypeScript
            **Rationale:** Type safety reduces runtime errors.
            **Conclusion:** Use TypeScript for all new services.
        """).strip()
        )

        # Wait for debounce + reload
        time.sleep(0.3)

        # Should have triggered reload
        assert reload_count >= 1
        assert len(last_fragments) >= 1
        assert any("TypeScript" in f.content for f in last_fragments)

    finally:
        watcher.stop()


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_t3_watcher_debounces_rapid_changes(tmp_path: Path):
    """Test that watcher debounces rapid changes."""
    memory_dir = tmp_path / ".lyra" / "memory"
    memory_dir.mkdir(parents=True)

    user_file = memory_dir / "user.md"
    user_file.write_text("# Initial")

    reload_count = 0

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count
        reload_count += 1

    watcher = start_t3_watcher(tmp_path, on_reload, debounce_seconds=0.2)
    assert watcher is not None

    try:
        # Make 5 rapid changes
        for i in range(5):
            user_file.write_text(f"# Change {i}")
            time.sleep(0.05)  # 50ms between changes

        # Wait for debounce + reload
        time.sleep(0.4)

        # Should have only reloaded once (debounced)
        assert reload_count == 1

    finally:
        watcher.stop()


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_t3_watcher_ignores_other_files(tmp_path: Path):
    """Test that watcher ignores non-memory files."""
    memory_dir = tmp_path / ".lyra" / "memory"
    memory_dir.mkdir(parents=True)

    user_file = memory_dir / "user.md"
    user_file.write_text("# Initial")

    other_file = memory_dir / "other.txt"
    other_file.write_text("ignored")

    reload_count = 0

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count
        reload_count += 1

    watcher = start_t3_watcher(tmp_path, on_reload, debounce_seconds=0.1)
    assert watcher is not None

    try:
        # Modify other file
        other_file.write_text("still ignored")
        time.sleep(0.3)

        # Should not have triggered reload
        assert reload_count == 0

        # Modify user.md
        user_file.write_text("# Changed")
        time.sleep(0.3)

        # Should have triggered reload
        assert reload_count == 1

    finally:
        watcher.stop()


def test_start_t3_watcher_without_watchdog(tmp_path: Path, monkeypatch):
    """Test graceful degradation when watchdog is not available."""
    # Mock WATCHDOG_AVAILABLE to False
    import lyra_core.memory.t3_watcher as watcher_module

    monkeypatch.setattr(watcher_module, "WATCHDOG_AVAILABLE", False)

    def on_reload(fragments: list[Fragment]) -> None:
        pass

    watcher = start_t3_watcher(tmp_path, on_reload)
    assert watcher is None  # Should return None when watchdog unavailable


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_t3_watcher_handles_missing_directory(tmp_path: Path):
    """Test that watcher handles missing memory directory gracefully."""
    reload_count = 0

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count
        reload_count += 1

    # Start watcher with non-existent directory
    watcher = start_t3_watcher(tmp_path, on_reload, debounce_seconds=0.1)
    assert watcher is not None

    try:
        # Should not crash, just log warning
        time.sleep(0.2)
        assert reload_count == 0

    finally:
        watcher.stop()
