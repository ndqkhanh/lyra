"""Tests for CLI integration."""

import tempfile
from pathlib import Path

from lyra_permissions.cli import PermissionCLI

# CLI Tests


def test_cli_init():
    """Test CLI initialization."""
    cli = PermissionCLI()
    assert cli.manager is not None
    assert cli.bypass_mode is not None


def test_cli_bypass_on():
    """Test bypass on command."""
    cli = PermissionCLI()
    cli.run(["bypass-on"])
    assert cli.bypass_mode.is_enabled() is True


def test_cli_bypass_off():
    """Test bypass off command."""
    cli = PermissionCLI()
    cli.run(["bypass-off"])
    assert cli.bypass_mode.is_enabled() is False


def test_cli_bypass_toggle():
    """Test bypass toggle command."""
    cli = PermissionCLI()
    initial_state = cli.bypass_mode.is_enabled()
    cli.run(["bypass-toggle"])
    assert cli.bypass_mode.is_enabled() != initial_state


def test_cli_bypass_status(capsys):
    """Test bypass status command."""
    cli = PermissionCLI()
    cli.bypass_mode.enable()
    cli.run(["bypass-status"])
    captured = capsys.readouterr()
    assert "ENABLED" in captured.out


def test_cli_profile_list(capsys):
    """Test profile list command."""
    cli = PermissionCLI()
    cli.run(["profile-list"])
    captured = capsys.readouterr()
    assert "default" in captured.out
    assert "development" in captured.out
    assert "production" in captured.out


def test_cli_profile_set():
    """Test profile set command."""
    cli = PermissionCLI()
    cli.run(["profile-set", "development"])
    assert cli.granular.current_profile == "development"


def test_cli_profile_show(capsys):
    """Test profile show command."""
    cli = PermissionCLI()
    cli.run(["profile-set", "development"])
    cli.run(["profile-show"])
    captured = capsys.readouterr()
    assert "development" in captured.out.lower()


def test_cli_audit_log(capsys):
    """Test audit log command."""
    cli = PermissionCLI()

    # Generate some audit entries
    cli.manager.check_permission("file_read", "read", {"path": "/tmp/test.txt"})

    cli.run(["audit-log", "--limit", "10"])
    captured = capsys.readouterr()
    assert "file_read" in captured.out or "No audit entries" in captured.out


def test_cli_audit_stats(capsys):
    """Test audit stats command."""
    cli = PermissionCLI()
    cli.run(["audit-stats"])
    captured = capsys.readouterr()
    assert "Total entries" in captured.out


def test_cli_audit_export():
    """Test audit export command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "audit.json"
        cli = PermissionCLI()

        # Generate audit entry
        cli.manager.check_permission("file_read", "read", {"path": "/tmp/test.txt"})

        cli.run(["audit-export", str(output_path), "--format", "json"])
        assert output_path.exists()


def test_cli_allow():
    """Test allow command."""
    cli = PermissionCLI()
    cli.run(["allow", "file_write", "write"])
    assert cli.store.is_allowed("file_write", "write") is True


def test_cli_deny():
    """Test deny command."""
    cli = PermissionCLI()
    cli.run(["deny", "file_delete", "delete"])
    assert cli.store.is_denied("file_delete", "delete") is True


def test_cli_remove():
    """Test remove command."""
    cli = PermissionCLI()
    cli.run(["allow", "file_write", "write"])
    cli.run(["remove", "file_write", "write"])
    assert cli.store.is_allowed("file_write", "write") is False


def test_cli_list(capsys):
    """Test list command."""
    cli = PermissionCLI()
    cli.run(["allow", "file_read", "read"])
    cli.run(["deny", "file_delete", "delete"])
    cli.run(["list"])
    captured = capsys.readouterr()
    assert "file_read:read" in captured.out
    assert "file_delete:delete" in captured.out


def test_cli_status(capsys):
    """Test status command."""
    cli = PermissionCLI()
    cli.run(["status"])
    captured = capsys.readouterr()
    assert "Permission System Status" in captured.out
    assert "Bypass mode" in captured.out
    assert "Current profile" in captured.out


def test_cli_no_command(capsys):
    """Test CLI with no command shows help."""
    cli = PermissionCLI()
    cli.run([])
    captured = capsys.readouterr()
    assert "usage:" in captured.out or "Lyra Permission Management" in captured.out
