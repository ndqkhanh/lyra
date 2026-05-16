"""Integration tests for skill marketplace commands."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lyra_cli.interactive.session import (
    InteractiveSession,
    _cmd_skill_browse,
    _cmd_skill_install,
    _cmd_skill_update,
    _cmd_skill_uninstall,
)


@pytest.fixture
def mock_session(tmp_path):
    """Create a mock InteractiveSession."""
    session = Mock(spec=InteractiveSession)
    session.skill_manager = Mock()
    session.skill_manager.skills_dir = tmp_path / "skills"
    session.skill_manager.skills_dir.mkdir(parents=True, exist_ok=True)
    return session


@pytest.fixture
def mock_registry_index():
    """Mock registry index data."""
    return {
        "version": "1.0",
        "skills": {
            "test-skill": {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test skill for integration tests",
                "author": "test-author",
                "repository": "https://github.com/test/test-skill",
                "tags": ["test", "automation"],
                "dependencies": {},
                "download_url": "https://test.registry.com/skills/test-skill/1.0.0.json",
            },
        },
    }


@pytest.fixture
def mock_skill_package():
    """Mock skill package data."""
    return {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "Test skill for integration tests",
        "author": "test-author",
        "repository": "https://github.com/test/test-skill",
        "tags": ["test", "automation"],
        "dependencies": {},
        "trigger": {"keywords": ["test"], "patterns": []},
        "system_prompt": "Test prompt",
    }


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_browse_no_filter(mock_registry_client, mock_session):
    """Test /skill browse without filters."""
    mock_client = Mock()
    mock_client.search_skills.return_value = [
        Mock(
            name="test-skill",
            version="1.0.0",
            description="Test skill",
            author="test-author",
            tags=["test"],
        )
    ]
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_browse(mock_session, "")

    assert result.output is not None
    assert "test-skill" in result.output
    assert "1.0.0" in result.output
    mock_client.search_skills.assert_called_once_with(query=None, tag=None)


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_browse_with_query(mock_registry_client, mock_session):
    """Test /skill browse with query filter."""
    mock_client = Mock()
    mock_client.search_skills.return_value = []
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_browse(mock_session, "automation")

    assert result.output is not None
    mock_client.search_skills.assert_called_once_with(query="automation", tag=None)


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_browse_with_tag(mock_registry_client, mock_session):
    """Test /skill browse with tag filter."""
    mock_client = Mock()
    mock_client.search_skills.return_value = []
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_browse(mock_session, "--tag test")

    assert result.output is not None
    mock_client.search_skills.assert_called_once_with(query=None, tag="test")


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_install_success(mock_registry_client, mock_session, mock_skill_package):
    """Test /skill install with successful installation."""
    mock_client = Mock()
    mock_client.download_skill.return_value = mock_skill_package
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_install(mock_session, "test-skill")

    assert result.output is not None
    assert "successfully installed" in result.output.lower()
    mock_client.download_skill.assert_called_once_with("test-skill", version=None)

    # Verify skill file was created
    skill_dir = Path.home() / ".lyra" / "skills"
    skill_file = skill_dir / "test-skill.json"
    assert skill_file.exists()


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_install_with_version(mock_registry_client, mock_session, mock_skill_package):
    """Test /skill install with specific version."""
    mock_client = Mock()
    mock_client.download_skill.return_value = mock_skill_package
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_install(mock_session, "test-skill --version 1.0.0")

    assert result.output is not None
    mock_client.download_skill.assert_called_once_with("test-skill", version="1.0.0")


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_install_not_found(mock_registry_client, mock_session):
    """Test /skill install with non-existent skill."""
    mock_client = Mock()
    mock_client.download_skill.side_effect = ValueError("Skill 'nonexistent' not found")
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_install(mock_session, "nonexistent")

    assert result.output is not None
    assert "not found" in result.output.lower()


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_update_with_updates(mock_registry_client, mock_session):
    """Test /skill update when updates are available."""
    # Create an installed skill
    skill_file = mock_session.skill_manager.skills_dir / "test-skill.json"
    skill_file.write_text(json.dumps({"name": "test-skill", "version": "0.9.0"}))

    mock_client = Mock()
    mock_client.check_updates.return_value = {"test-skill": ("0.9.0", "1.0.0")}
    mock_client.download_skill.return_value = {
        "name": "test-skill",
        "version": "1.0.0",
    }
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_update(mock_session, "")

    assert result.output is not None
    assert "updated" in result.output.lower()


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_cmd_skill_update_no_updates(mock_registry_client, mock_session):
    """Test /skill update when no updates are available."""
    mock_client = Mock()
    mock_client.check_updates.return_value = {}
    mock_registry_client.return_value = mock_client

    result = _cmd_skill_update(mock_session, "")

    assert result.output is not None
    assert "up to date" in result.output.lower()


def test_cmd_skill_uninstall_success(mock_session):
    """Test /skill uninstall with successful removal."""
    # Create a valid skill file that passes SkillManager validation
    skill_dir = Path.home() / ".lyra" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "test-skill.json"

    # Create a complete skill package that passes validation
    valid_skill = {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "Test skill",
        "category": "test",
        "execution": {"type": "prompt"}
    }
    skill_file.write_text(json.dumps(valid_skill, indent=2))

    result = _cmd_skill_uninstall(mock_session, "test-skill")

    assert result.output is not None
    assert "uninstalled" in result.output.lower()
    assert not skill_file.exists()


def test_cmd_skill_uninstall_not_found(mock_session):
    """Test /skill uninstall with non-existent skill."""
    mock_session.skill_manager.skills = {}

    result = _cmd_skill_uninstall(mock_session, "nonexistent")

    assert result.output is not None
    assert "not installed" in result.output.lower()


