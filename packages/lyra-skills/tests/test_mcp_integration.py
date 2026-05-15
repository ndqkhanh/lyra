"""Tests for MCP server integration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra_skills.mcp_integration import (
    MCPServerManager,
    install_production_mcp_servers,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    return tmp_path / ".lyra"


def test_mcp_server_manager_init(temp_config_dir):
    """Test MCPServerManager initialization."""
    manager = MCPServerManager(temp_config_dir)
    assert manager.config_dir == temp_config_dir
    assert manager.config_file == temp_config_dir / "mcp_servers.json"


def test_load_config_empty(temp_config_dir):
    """Test loading config when file doesn't exist."""
    manager = MCPServerManager(temp_config_dir)
    config = manager.load_config()
    assert config == {"mcpServers": {}}


def test_save_and_load_config(temp_config_dir):
    """Test saving and loading configuration."""
    manager = MCPServerManager(temp_config_dir)
    config = {
        "mcpServers": {
            "test": {"command": "test-cmd", "args": ["arg1"]}
        }
    }
    assert manager.save_config(config)
    loaded = manager.load_config()
    assert loaded == config


def test_add_server(temp_config_dir):
    """Test adding an MCP server."""
    manager = MCPServerManager(temp_config_dir)
    assert manager.add_server(
        "test-server",
        "npx",
        ["test-package"],
        {"KEY": "value"},
    )

    config = manager.load_config()
    assert "test-server" in config["mcpServers"]
    assert config["mcpServers"]["test-server"]["command"] == "npx"
    assert config["mcpServers"]["test-server"]["args"] == ["test-package"]
    assert config["mcpServers"]["test-server"]["env"] == {"KEY": "value"}


def test_remove_server(temp_config_dir):
    """Test removing an MCP server."""
    manager = MCPServerManager(temp_config_dir)
    manager.add_server("test-server", "npx", ["test"])
    assert manager.remove_server("test-server")

    config = manager.load_config()
    assert "test-server" not in config["mcpServers"]


def test_list_servers(temp_config_dir):
    """Test listing MCP servers."""
    manager = MCPServerManager(temp_config_dir)
    manager.add_server("server1", "cmd1", [])
    manager.add_server("server2", "cmd2", [])

    servers = manager.list_servers()
    assert "server1" in servers
    assert "server2" in servers


@patch("subprocess.run")
def test_install_mcp_package_success(mock_run, temp_config_dir):
    """Test successful MCP package installation."""
    mock_run.return_value = MagicMock(returncode=0)
    manager = MCPServerManager(temp_config_dir)
    assert manager.install_mcp_package("test-package")
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_install_mcp_package_failure(mock_run, temp_config_dir):
    """Test failed MCP package installation."""
    mock_run.side_effect = Exception("Install failed")
    manager = MCPServerManager(temp_config_dir)
    assert not manager.install_mcp_package("test-package")
