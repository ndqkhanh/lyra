"""Integration tests for production resource installation."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from lyra_skills.mcp_integration import install_production_mcp_servers
from lyra_skills.production_installer import install_production_skills


@pytest.fixture
def temp_install_dir(tmp_path):
    """Create temporary installation directory."""
    return tmp_path / "lyra_test"


@patch("subprocess.run")
@patch("lyra_skills.mcp_integration.MCPServerManager.install_mcp_package")
def test_install_production_mcp_servers_integration(
    mock_install, mock_run, temp_install_dir
):
    """Test installing production MCP servers."""
    mock_install.return_value = True
    mock_run.return_value = MagicMock(returncode=0)

    results = install_production_mcp_servers(
        servers=["filesystem"],
        config_dir=temp_install_dir,
    )

    assert "filesystem" in results
    assert results["filesystem"] is True


@patch("subprocess.run")
def test_install_production_skills_integration(mock_run, temp_install_dir):
    """Test installing production skills."""
    mock_run.return_value = MagicMock(returncode=0)

    # Mock git clone success
    results = install_production_skills(
        skills=["token-optimizer"],
        skills_dir=temp_install_dir / "skills",
    )

    assert "token-optimizer" in results


def test_skill_installer_list_installed(temp_install_dir):
    """Test listing installed skills."""
    from lyra_skills.production_installer import SkillInstaller

    installer = SkillInstaller(temp_install_dir / "skills")

    # Create mock skill directory
    skill_dir = temp_install_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)

    installed = installer.list_installed_skills()
    assert "test-skill" in installed


def test_mcp_server_manager_integration(temp_install_dir):
    """Test MCP server manager end-to-end."""
    from lyra_skills.mcp_integration import MCPServerManager

    manager = MCPServerManager(temp_install_dir)

    # Add server
    assert manager.add_server("test", "npx", ["test-pkg"])

    # List servers
    servers = manager.list_servers()
    assert "test" in servers

    # Remove server
    assert manager.remove_server("test")
    servers = manager.list_servers()
    assert "test" not in servers
