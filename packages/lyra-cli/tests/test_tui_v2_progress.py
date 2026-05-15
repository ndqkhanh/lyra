"""Tests for enhanced progress indicators."""

import time
from unittest.mock import MagicMock, patch

import pytest

from lyra_cli.tui_v2.progress import (
    LyraProgress,
    animated_spinner,
    streaming_output,
)


def test_animated_spinner():
    """Test animated spinner context manager."""
    with patch("lyra_cli.tui_v2.progress.alive_bar") as mock_bar:
        mock_bar.return_value.__enter__ = MagicMock(return_value=lambda: None)
        mock_bar.return_value.__exit__ = MagicMock(return_value=None)

        with animated_spinner(100, title="Test") as bar:
            bar()

        mock_bar.assert_called_once()


def test_lyra_progress_add_task():
    """Test adding tasks to progress tracker."""
    with patch("lyra_cli.tui_v2.progress.Progress") as mock_progress:
        mock_instance = MagicMock()
        mock_progress.return_value = mock_instance
        mock_instance.add_task.return_value = "task-1"

        progress = LyraProgress()
        task_id = progress.add_task("test", "Test task", total=100)

        assert task_id == "task-1"
        assert "test" in progress.tasks


def test_lyra_progress_update():
    """Test updating task progress."""
    with patch("lyra_cli.tui_v2.progress.Progress") as mock_progress:
        mock_instance = MagicMock()
        mock_progress.return_value = mock_instance
        mock_instance.add_task.return_value = "task-1"

        progress = LyraProgress()
        progress.add_task("test", "Test task")
        progress.update("test", advance=10)

        mock_instance.update.assert_called_with("task-1", advance=10)


def test_lyra_progress_complete():
    """Test completing a task."""
    with patch("lyra_cli.tui_v2.progress.Progress") as mock_progress:
        mock_instance = MagicMock()
        mock_progress.return_value = mock_instance
        mock_instance.add_task.return_value = "task-1"

        progress = LyraProgress()
        progress.add_task("test", "Test task")
        progress.complete("test")

        mock_instance.update.assert_called_with("task-1", completed=True)


def test_streaming_output():
    """Test streaming output context manager."""
    with patch("lyra_cli.tui_v2.progress.Live") as mock_live:
        mock_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=None)

        with streaming_output() as update:
            update("test content")

        mock_instance.update.assert_called_with("test content")


def test_lyra_progress_context_manager():
    """Test LyraProgress as context manager."""
    with patch("lyra_cli.tui_v2.progress.Progress") as mock_progress:
        mock_instance = MagicMock()
        mock_progress.return_value = mock_instance

        with LyraProgress() as progress:
            assert progress is not None

        mock_instance.__enter__.assert_called_once()
        mock_instance.__exit__.assert_called_once()
