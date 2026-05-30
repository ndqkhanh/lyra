"""Tests for plugin file system watcher."""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from lyra_core.plugins.watcher import (
    FileChangeEvent,
    PluginWatcher,
    WatcherConfig,
)


@pytest.fixture
def watcher():
    w = PluginWatcher()
    yield w
    w.stop()


@pytest.fixture
def temp_plugin_dir(tmp_path):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    return plugin_dir


class TestPluginWatcher:
    """Tests for PluginWatcher file system monitoring."""

    def test_add_directory(self, watcher, temp_plugin_dir):
        watcher.add_directory(temp_plugin_dir)
        assert temp_plugin_dir in watcher.watched_directories

    def test_add_nonexistent_directory_raises(self, watcher):
        with pytest.raises(ValueError, match="Not a directory"):
            watcher.add_directory("/nonexistent/path")

    def test_remove_directory(self, watcher, temp_plugin_dir):
        watcher.add_directory(temp_plugin_dir)
        watcher.remove_directory(temp_plugin_dir)
        assert temp_plugin_dir not in watcher.watched_directories

    def test_on_change_callback(self, watcher, temp_plugin_dir):
        events = []

        def callback(event: FileChangeEvent):
            events.append(event)

        watcher.on_change(callback)
        watcher.add_directory(temp_plugin_dir)

        # Create a file
        plugin_file = temp_plugin_dir / "test.py"
        plugin_file.write_text("# test")

        watcher.start()
        time.sleep(1.5)  # Wait for poll
        watcher.stop()

        assert len(events) > 0
        assert events[0].event_type == "created"
        assert events[0].path == plugin_file

    def test_detect_file_modification(self, watcher, temp_plugin_dir):
        plugin_file = temp_plugin_dir / "test.py"
        plugin_file.write_text("# version 1")

        events = []
        watcher.on_change(lambda e: events.append(e))
        watcher.add_directory(temp_plugin_dir)
        watcher.start()

        time.sleep(0.5)
        plugin_file.write_text("# version 2")
        time.sleep(1.5)

        watcher.stop()

        modified_events = [e for e in events if e.event_type == "modified"]
        assert len(modified_events) > 0
        assert modified_events[0].path == plugin_file

    def test_detect_file_deletion(self, watcher, temp_plugin_dir):
        plugin_file = temp_plugin_dir / "test.py"
        plugin_file.write_text("# test")

        events = []
        watcher.on_change(lambda e: events.append(e))
        watcher.add_directory(temp_plugin_dir)
        watcher.start()

        time.sleep(0.5)
        plugin_file.unlink()
        time.sleep(1.5)

        watcher.stop()

        deleted_events = [e for e in events if e.event_type == "deleted"]
        assert len(deleted_events) > 0
        assert deleted_events[0].path == plugin_file

    def test_recursive_watching(self, watcher, temp_plugin_dir):
        subdir = temp_plugin_dir / "subdir"
        subdir.mkdir()
        plugin_file = subdir / "test.py"
        plugin_file.write_text("# test")

        config = WatcherConfig(recursive=True)
        watcher = PluginWatcher(config)

        events = []
        watcher.on_change(lambda e: events.append(e))
        watcher.add_directory(temp_plugin_dir)
        watcher.start()

        time.sleep(0.5)
        plugin_file.write_text("# modified")
        time.sleep(1.5)

        watcher.stop()

        assert len(events) > 0

    def test_ignore_patterns(self, watcher, temp_plugin_dir):
        pyc_file = temp_plugin_dir / "test.pyc"
        pyc_file.write_text("compiled")

        config = WatcherConfig(ignore_patterns=("*.pyc",))
        watcher = PluginWatcher(config)

        events = []
        watcher.on_change(lambda e: events.append(e))
        watcher.add_directory(temp_plugin_dir)
        watcher.start()

        time.sleep(1.5)
        watcher.stop()

        # Should not detect .pyc file
        assert len(events) == 0

    def test_file_patterns(self, watcher, temp_plugin_dir):
        py_file = temp_plugin_dir / "test.py"
        txt_file = temp_plugin_dir / "test.txt"
        py_file.write_text("# python")
        txt_file.write_text("text")

        config = WatcherConfig(file_patterns=("*.py",))
        watcher = PluginWatcher(config)

        events = []
        watcher.on_change(lambda e: events.append(e))
        watcher.add_directory(temp_plugin_dir)
        watcher.start()

        time.sleep(0.5)
        py_file.write_text("# modified")
        txt_file.write_text("modified")
        time.sleep(1.5)

        watcher.stop()

        # Should only detect .py file
        modified_events = [e for e in events if e.event_type == "modified"]
        assert len(modified_events) == 1
        assert modified_events[0].path == py_file

    def test_callback_error_does_not_stop_watcher(self, watcher, temp_plugin_dir):
        call_count = [0]

        def bad_callback(event: FileChangeEvent):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("First call fails")

        watcher.on_change(bad_callback)
        watcher.add_directory(temp_plugin_dir)

        file1 = temp_plugin_dir / "test1.py"
        file2 = temp_plugin_dir / "test2.py"
        file1.write_text("# test1")

        watcher.start()
        time.sleep(0.5)

        file2.write_text("# test2")
        time.sleep(1.5)

        watcher.stop()

        # Should have been called twice despite first error
        assert call_count[0] >= 2

    def test_is_running(self, watcher, temp_plugin_dir):
        assert not watcher.is_running

        watcher.add_directory(temp_plugin_dir)
        watcher.start()
        assert watcher.is_running

        watcher.stop()
        assert not watcher.is_running

    def test_multiple_callbacks(self, watcher, temp_plugin_dir):
        events1 = []
        events2 = []

        watcher.on_change(lambda e: events1.append(e))
        watcher.on_change(lambda e: events2.append(e))
        watcher.add_directory(temp_plugin_dir)

        plugin_file = temp_plugin_dir / "test.py"
        plugin_file.write_text("# test")

        watcher.start()
        time.sleep(1.5)
        watcher.stop()

        # Both callbacks should receive events
        assert len(events1) > 0
        assert len(events2) > 0
        assert events1[0].path == events2[0].path

    def test_watcher_config_defaults(self):
        config = WatcherConfig()
        assert config.poll_interval_seconds == 1.0
        assert "*.py" in config.file_patterns
        assert config.recursive is True

    def test_file_change_event_fields(self, temp_plugin_dir):
        path = temp_plugin_dir / "test.py"
        event = FileChangeEvent(
            path=path, event_type="modified", timestamp=time.time()
        )
        assert event.path == path
        assert event.event_type == "modified"
        assert event.timestamp > 0
