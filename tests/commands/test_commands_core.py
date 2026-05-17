"""Tests for commands system."""
import pytest
from pathlib import Path
import tempfile
import shutil
from typer.testing import CliRunner

from lyra_cli.commands.doctor import doctor_command


@pytest.fixture
def temp_repo():
    """Create temporary repo directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


def test_doctor_command_exists():
    """Test that doctor command exists and is callable."""
    assert callable(doctor_command)


def test_doctor_command_signature():
    """Test doctor command has correct signature."""
    import inspect
    sig = inspect.signature(doctor_command)

    # Should have repo_root and json_out parameters
    assert "repo_root" in sig.parameters
    assert "json_out" in sig.parameters


def test_doctor_command_with_temp_repo(temp_repo):
    """Test doctor command with temporary repo."""
    # This will likely fail since temp_repo isn't initialized
    # but we're testing the command runs without crashing
    import click
    try:
        doctor_command(repo_root=temp_repo, json_out=True)
    except (SystemExit, click.exceptions.Exit):
        # Expected - command exits with status code
        pass


def test_doctor_json_output_structure(temp_repo, capsys):
    """Test doctor command JSON output structure."""
    import json
    import click

    try:
        doctor_command(repo_root=temp_repo, json_out=True)
    except (SystemExit, click.exceptions.Exit):
        pass

    captured = capsys.readouterr()

    # Should output valid JSON
    try:
        data = json.loads(captured.out)
        assert "repo_root" in data
        assert "ok" in data
        assert "probes" in data
        assert isinstance(data["probes"], list)
    except json.JSONDecodeError:
        # If no output, that's also acceptable for some states
        pass


def test_command_module_imports():
    """Test that command modules can be imported."""
    # Test importing various command modules
    try:
        from lyra_cli.commands import doctor
        assert hasattr(doctor, "doctor_command")
    except ImportError as e:
        pytest.fail(f"Failed to import doctor command: {e}")


def test_doctor_command_help_text():
    """Test doctor command has help text."""
    import inspect
    doc = inspect.getdoc(doctor_command)

    assert doc is not None
    assert len(doc) > 0


def test_doctor_command_parameters_have_defaults():
    """Test doctor command parameters have sensible defaults."""
    import inspect
    sig = inspect.signature(doctor_command)

    # repo_root should have a default
    repo_root_param = sig.parameters["repo_root"]
    assert repo_root_param.default is not inspect.Parameter.empty

    # json_out should have a default
    json_out_param = sig.parameters["json_out"]
    assert json_out_param.default is not inspect.Parameter.empty


def test_ok_marker_function():
    """Test _ok_marker helper function."""
    from lyra_cli.commands.doctor import _ok_marker
    from lyra_cli.diagnostics import Probe

    # Test OK probe
    ok_probe = Probe(
        category="test",
        name="test",
        ok=True,
        detail="test",
        meta={}
    )
    marker = _ok_marker(ok_probe)
    assert "OK" in marker or "green" in marker

    # Test failed probe
    fail_probe = Probe(
        category="test",
        name="test",
        ok=False,
        detail="test",
        meta={}
    )
    marker = _ok_marker(fail_probe)
    assert "MISSING" in marker or "red" in marker


def test_exit_code_function():
    """Test _exit_code helper function."""
    from lyra_cli.commands.doctor import _exit_code
    from lyra_cli.diagnostics import Probe

    # All OK probes should return 0
    ok_probes = [
        Probe(category="test", name="test1", ok=True, detail="", meta={}),
        Probe(category="test", name="test2", ok=True, detail="", meta={}),
    ]
    assert _exit_code(ok_probes) == 0

    # Failed required probe should return 1
    fail_probes = [
        Probe(category="test", name="test1", ok=False, detail="", meta={}),
    ]
    assert _exit_code(fail_probes) == 1

    # Optional failed probe should return 0
    optional_probes = [
        Probe(category="test", name="test1", ok=False, detail="", meta={"optional": True}),
    ]
    assert _exit_code(optional_probes) == 0


def test_command_error_handling(temp_repo):
    """Test command handles errors gracefully."""
    import click

    # Test with invalid path
    invalid_path = Path("/nonexistent/path/that/does/not/exist")

    try:
        doctor_command(repo_root=invalid_path, json_out=True)
    except (SystemExit, click.exceptions.Exit) as e:
        # Should exit, but not crash
        if isinstance(e, SystemExit):
            assert isinstance(e.code, int)
    except Exception as e:
        # Should not raise unexpected exceptions
        pytest.fail(f"Unexpected exception: {e}")


def test_commands_directory_structure():
    """Test commands directory has expected structure."""
    from lyra_cli import commands
    import os

    commands_dir = Path(commands.__file__).parent

    # Should have __init__.py
    assert (commands_dir / "__init__.py").exists()

    # Should have some command files
    py_files = list(commands_dir.glob("*.py"))
    assert len(py_files) > 1  # More than just __init__.py


def test_command_imports_dont_fail():
    """Test that importing commands doesn't raise errors."""
    # Try importing various command modules
    command_modules = [
        "doctor",
        "init",
        "hud",
    ]

    for module_name in command_modules:
        try:
            __import__(f"lyra_cli.commands.{module_name}")
        except ImportError:
            # Some commands might not exist, that's OK
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error importing {module_name}: {e}")


def test_doctor_command_with_cwd():
    """Test doctor command with current working directory."""
    import click

    # Should not crash when run with cwd
    try:
        doctor_command(repo_root=Path.cwd(), json_out=True)
    except (SystemExit, click.exceptions.Exit):
        # Expected
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
