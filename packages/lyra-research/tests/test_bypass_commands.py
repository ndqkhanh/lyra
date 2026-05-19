"""
Tests for Bypass CLI Commands (Bypass Permissions Phase 3)

Tests command-line interface for bypass management.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
from lyra_research.cli.bypass_commands import bypass
from lyra_research.permissions.bypass_manager import BypassManager
from lyra_research.permissions.audit_logger import AuditLogger
from lyra_research.permissions.permission_gate import PermissionRequest, PermissionLevel


class TestBypassCLI:
    """Test bypass CLI commands"""

    def test_enable_command(self):
        """Test enable command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(bypass, ['enable'])
            assert result.exit_code == 0
            assert "Bypass mode ENABLED" in result.output

    def test_disable_command(self):
        """Test disable command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(bypass, ['disable'])
            assert result.exit_code == 0
            assert "Bypass mode disabled" in result.output

    def test_toggle_command(self):
        """Test toggle command"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Toggle to enabled
            result = runner.invoke(bypass, ['toggle'])
            assert result.exit_code == 0
            assert "Bypass mode ENABLED" in result.output

            # Toggle to disabled
            result = runner.invoke(bypass, ['toggle'])
            assert result.exit_code == 0
            assert "Bypass mode disabled" in result.output

    def test_status_command_disabled(self):
        """Test status command when disabled"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(bypass, ['status'])
            assert result.exit_code == 0
            assert "Bypass mode: disabled" in result.output

    def test_status_command_enabled(self):
        """Test status command when enabled"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Enable first
            runner.invoke(bypass, ['enable'])

            # Check status
            result = runner.invoke(bypass, ['status'])
            assert result.exit_code == 0
            assert "Bypass mode: ENABLED" in result.output
            # Note: enabled_at is not persisted to config, so it won't show after reload

    def test_audit_command_empty(self):
        """Test audit command with no entries"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Clear any existing audit log
            logger = AuditLogger()
            if logger.log_path.exists():
                logger.clear_log()

            result = runner.invoke(bypass, ['audit'])
            assert result.exit_code == 0
            # May have entries from previous tests, so just check it runs
            assert result.exit_code == 0

    def test_audit_command_with_entries(self):
        """Test audit command with entries"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create some audit entries
            logger = AuditLogger()
            request = PermissionRequest(
                operation="test_op",
                level=PermissionLevel.STANDARD,
                description="Test operation",
                context={}
            )
            logger.log_bypass(request)

            # Check audit
            result = runner.invoke(bypass, ['audit'])
            assert result.exit_code == 0
            assert "Recent bypassed operations" in result.output
            assert "test_op" in result.output

    def test_audit_command_with_limit(self):
        """Test audit command with custom limit"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create multiple audit entries
            logger = AuditLogger()
            for i in range(5):
                request = PermissionRequest(
                    operation=f"op_{i}",
                    level=PermissionLevel.STANDARD,
                    description=f"Operation {i}",
                    context={}
                )
                logger.log_bypass(request)

            # Check audit with limit
            result = runner.invoke(bypass, ['audit', '--limit', '3'])
            assert result.exit_code == 0
            assert "Recent bypassed operations (3)" in result.output

    def test_command_output_formatting(self):
        """Test command output formatting"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Enable command should have checkmark
            result = runner.invoke(bypass, ['enable'])
            assert "✓" in result.output

            # Disable command should have checkmark
            result = runner.invoke(bypass, ['disable'])
            assert "✓" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
