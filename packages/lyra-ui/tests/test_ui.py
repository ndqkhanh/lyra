"""Tests for Rich console and progress indicators."""

from lyra_ui import ProgressManager, RichConsole, Spinner, console
from rich.theme import Theme

# Console Tests


def test_rich_console_singleton():
    """Test console is singleton."""
    console1 = RichConsole()
    console2 = RichConsole()
    assert console1 is console2


def test_rich_console_has_console():
    """Test console has Rich console instance."""
    rich_console = RichConsole()
    assert rich_console.console is not None


def test_rich_console_print_success(capsys):
    """Test success message printing."""
    console.print_success("Test success")
    # Console output goes to stderr in Rich
    # Just verify no exceptions


def test_rich_console_print_error(capsys):
    """Test error message printing."""
    console.print_error("Test error")
    # Just verify no exceptions


def test_rich_console_print_warning(capsys):
    """Test warning message printing."""
    console.print_warning("Test warning")
    # Just verify no exceptions


def test_rich_console_print_info(capsys):
    """Test info message printing."""
    console.print_info("Test info")
    # Just verify no exceptions


def test_rich_console_set_theme():
    """Test theme setting."""
    custom_theme = Theme({"success": "bold green"})
    console.set_theme(custom_theme)
    assert console.console is not None


# Progress Manager Tests


def test_progress_manager_init():
    """Test progress manager initialization."""
    manager = ProgressManager()
    assert manager.progress is None
    assert len(manager.tasks) == 0


def test_progress_manager_start_stop():
    """Test starting and stopping progress."""
    manager = ProgressManager()
    manager.start()
    assert manager.progress is not None
    manager.stop()
    assert manager.progress is None


def test_progress_manager_add_task():
    """Test adding task."""
    manager = ProgressManager()
    task_name = manager.add_task("test", "Test task", total=100)
    assert task_name == "test"
    assert "test" in manager.tasks
    manager.stop()


def test_progress_manager_update_task():
    """Test updating task."""
    manager = ProgressManager()
    manager.add_task("test", "Test task", total=100)
    manager.update_task("test", advance=10)
    manager.stop()


def test_progress_manager_complete_task():
    """Test completing task."""
    manager = ProgressManager()
    manager.add_task("test", "Test task", total=100)
    manager.complete_task("test")
    manager.stop()


def test_progress_manager_remove_task():
    """Test removing task."""
    manager = ProgressManager()
    manager.add_task("test", "Test task", total=100)
    manager.remove_task("test")
    assert "test" not in manager.tasks
    manager.stop()


# Spinner Tests


def test_spinner_context_manager():
    """Test spinner as context manager."""
    with Spinner("Testing...") as spinner:
        assert spinner is not None


def test_spinner_update():
    """Test spinner update."""
    with Spinner("Testing...") as spinner:
        spinner.update("Still testing...")


def test_spinner_custom_description():
    """Test spinner with custom description."""
    with Spinner("Custom description") as spinner:
        assert spinner.description == "Custom description"


# Integration Tests


def test_multiple_progress_tasks():
    """Test multiple progress tasks."""
    manager = ProgressManager()
    manager.add_task("task1", "Task 1", total=100)
    manager.add_task("task2", "Task 2", total=50)
    manager.update_task("task1", advance=25)
    manager.update_task("task2", advance=10)
    manager.stop()

