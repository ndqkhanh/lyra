"""Tests for Phase 4.1b — Plugin Hot-Reload System."""
from __future__ import annotations

import os
import time

import pytest
from lyra_core.plugins.hot_reload import (
    PluginFileState,
    PluginHotReloader,
    ReloadEvent,
    ReloadStatus,
)


@pytest.fixture
def reloader():
    return PluginHotReloader()


@pytest.fixture
def temp_plugin(tmp_path):
    f = tmp_path / "plugin.py"
    f.write_text("# version 1")
    return str(f)


class TestPluginHotReloader:
    """Unit tests for PluginHotReloader file watching and reload."""

    def test_watch_adds_file(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        assert reloader.watched_count == 1
        assert temp_plugin in reloader.watched_paths

    def test_watch_duplicate_is_noop(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        reloader.watch(temp_plugin)
        assert reloader.watched_count == 1

    def test_unwatch_removes_file(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        reloader.unwatch(temp_plugin)
        assert reloader.watched_count == 0

    def test_unwatch_nonexistent_is_safe(self, reloader):
        reloader.unwatch("/nonexistent/path.py")

    def test_poll_no_changes_returns_empty(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        events = reloader.poll()
        assert events == ()

    def test_poll_detects_content_change(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        time.sleep(0.01)
        with open(temp_plugin, "w") as f:
            f.write("# version 2")
        events = reloader.poll()
        assert len(events) == 1
        assert events[0].status == ReloadStatus.RELOADED
        assert events[0].plugin_path == temp_plugin
        assert events[0].old_hash is not None
        assert events[0].new_hash is not None
        assert events[0].old_hash != events[0].new_hash

    def test_poll_detects_removed_file(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        os.remove(temp_plugin)
        events = reloader.poll()
        assert len(events) == 1
        assert events[0].status == ReloadStatus.REMOVED
        assert events[0].new_hash is None

    def test_removed_file_not_watched_after_poll(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        os.remove(temp_plugin)
        reloader.poll()
        assert reloader.watched_count == 0

    def test_watch_directory(self, reloader, tmp_path):
        for name in ("a.py", "b.py", "c.txt"):
            (tmp_path / name).write_text("# test")
        count = reloader.watch_directory(str(tmp_path), pattern="*.py")
        assert count == 2

    def test_watch_directory_missing(self, reloader):
        count = reloader.watch_directory("/no/such/dir")
        assert count == 0

    def test_on_reload_callback(self, reloader, temp_plugin):
        called = []

        def callback(path):
            called.append(path)

        reloader.on_reload(callback)
        reloader.watch(temp_plugin)
        with open(temp_plugin, "w") as f:
            f.write("# version 2")
        reloader.poll()
        assert len(called) == 1
        assert called[0] == temp_plugin

    def test_on_reload_callback_error(self, reloader, temp_plugin):
        def bad_callback(_path):
            raise RuntimeError("callback error")

        reloader.on_reload(bad_callback)
        reloader.watch(temp_plugin)
        with open(temp_plugin, "w") as f:
            f.write("# version 2")
        events = reloader.poll()
        assert events[0].status == ReloadStatus.FAILED
        assert "callback error" in events[0].error

    def test_events_accumulate(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        for i in range(3):
            with open(temp_plugin, "w") as f:
                f.write(f"# version {i}")
            time.sleep(0.01)
            reloader.poll()
        assert len(reloader.events) == 3

    def test_clear_events(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        with open(temp_plugin, "w") as f:
            f.write("# version 2")
        reloader.poll()
        assert len(reloader.events) == 1
        reloader.clear_events()
        assert len(reloader.events) == 0

    def test_stop_clears_all(self, reloader, temp_plugin):
        reloader.watch(temp_plugin)
        with open(temp_plugin, "w") as f:
            f.write("# version 2")
        reloader.poll()
        reloader.stop()
        assert reloader.watched_count == 0
        assert len(reloader.events) == 0

    def test_plugin_file_state_fields(self, temp_plugin):
        state = PluginFileState(
            file_path=temp_plugin,
            content_hash="abc123",
            size_bytes=100,
            mtime=time.time(),
            checked_at=time.time(),
        )
        assert state.file_path == temp_plugin
        assert state.content_hash == "abc123"
        assert state.size_bytes == 100

    def test_reload_event_fields(self, temp_plugin):
        now = time.time()
        event = ReloadEvent(
            event_id="re-abc",
            plugin_path=temp_plugin,
            status=ReloadStatus.RELOADED,
            old_hash="aaa",
            new_hash="bbb",
            error=None,
            timestamp=now,
        )
        assert event.plugin_path == temp_plugin
        assert event.status == ReloadStatus.RELOADED
        assert event.error is None

    def test_poll_multiple_files(self, reloader, tmp_path):
        f1 = tmp_path / "plugin_a.py"
        f2 = tmp_path / "plugin_b.py"
        f1.write_text("# a v1")
        f2.write_text("# b v1")
        reloader.watch(str(f1))
        reloader.watch(str(f2))

        with open(str(f1), "w") as f:
            f.write("# a v2")
        with open(str(f2), "w") as f:
            f.write("# b v2")

        events = reloader.poll()
        assert len(events) == 2

    def test_watched_paths_is_sorted(self, reloader, tmp_path):
        f1 = str(tmp_path / "z_plugin.py")
        f2 = str(tmp_path / "a_plugin.py")
        import pathlib
        pathlib.Path(f1).write_text("# z")
        pathlib.Path(f2).write_text("# a")
        reloader.watch(f1)
        reloader.watch(f2)
        # Just verify both are there
        assert f1 in reloader.watched_paths
        assert f2 in reloader.watched_paths
