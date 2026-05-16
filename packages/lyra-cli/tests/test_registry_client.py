"""Tests for registry client."""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from lyra_cli.cli.registry_client import RegistryClient, SkillMetadata


@pytest.fixture
def temp_registry_config(tmp_path):
    """Create a temporary registry configuration."""
    config_path = tmp_path / "registry.json"
    config = {
        "registries": [
            {
                "name": "test-registry",
                "url": "https://test.registry.com/index.json",
                "enabled": True,
                "priority": 1,
            }
        ],
        "cache_ttl": 3600,
        "auto_update_check": True,
    }
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def mock_registry_index():
    """Mock registry index data."""
    return {
        "version": "1.0",
        "skills": {
            "test-skill": {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test skill for unit tests",
                "author": "test-author",
                "repository": "https://github.com/test/test-skill",
                "tags": ["test", "automation"],
                "dependencies": {},
                "download_url": "https://test.registry.com/skills/test-skill/1.0.0.json",
            },
            "another-skill": {
                "name": "another-skill",
                "version": "2.1.0",
                "description": "Another test skill",
                "author": "test-author",
                "repository": "https://github.com/test/another-skill",
                "tags": ["research"],
                "dependencies": {},
                "download_url": "https://test.registry.com/skills/another-skill/2.1.0.json",
            },
        },
    }


@pytest.fixture
def mock_skill_package():
    """Mock skill package data."""
    return {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "Test skill for unit tests",
        "author": "test-author",
        "repository": "https://github.com/test/test-skill",
        "tags": ["test", "automation"],
        "dependencies": {},
        "trigger": {"keywords": ["test"], "patterns": []},
        "system_prompt": "Test prompt",
    }


def test_registry_client_init_with_existing_config(temp_registry_config):
    """Test RegistryClient initialization with existing config."""
    client = RegistryClient(temp_registry_config)

    assert client.config_path == temp_registry_config
    assert len(client.config["registries"]) == 1
    assert client.config["registries"][0]["name"] == "test-registry"
    assert client.cache_dir.exists()


def test_registry_client_init_with_default_config(tmp_path):
    """Test RegistryClient initialization with default config."""
    config_path = tmp_path / "nonexistent.json"
    client = RegistryClient(config_path)

    assert len(client.config["registries"]) == 1
    assert client.config["registries"][0]["name"] == "official"
    assert client.config["cache_ttl"] == 3600


@patch("lyra_cli.cli.registry_client.requests.get")
def test_fetch_index_from_remote(mock_get, temp_registry_config, mock_registry_index):
    """Test fetching registry index from remote."""
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RegistryClient(temp_registry_config)
    index = client.fetch_index("test-registry")

    assert index == mock_registry_index
    assert "test-skill" in index["skills"]
    mock_get.assert_called_once()


@patch("lyra_cli.cli.registry_client.requests.get")
def test_fetch_index_from_cache(mock_get, temp_registry_config, mock_registry_index):
    """Test fetching registry index from cache."""
    # Create cache file
    client = RegistryClient(temp_registry_config)
    cache_file = client.cache_dir / "test-registry-index.json"
    cache_file.write_text(json.dumps(mock_registry_index, indent=2))

    # Fetch should use cache
    index = client.fetch_index("test-registry")

    assert index == mock_registry_index
    mock_get.assert_not_called()


@patch("lyra_cli.cli.registry_client.requests.get")
def test_fetch_index_cache_expired(mock_get, temp_registry_config, mock_registry_index):
    """Test fetching registry index when cache is expired."""
    # Create old cache file
    client = RegistryClient(temp_registry_config)
    cache_file = client.cache_dir / "test-registry-index.json"
    cache_file.write_text(json.dumps(mock_registry_index, indent=2))

    # Make cache old
    old_time = time.time() - 7200  # 2 hours ago
    cache_file.touch()
    import os

    os.utime(cache_file, (old_time, old_time))

    # Mock remote fetch
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Fetch should hit remote
    index = client.fetch_index("test-registry")

    assert index == mock_registry_index
    mock_get.assert_called_once()


def test_fetch_index_registry_not_found(temp_registry_config):
    """Test fetching index for non-existent registry."""
    client = RegistryClient(temp_registry_config)

    with pytest.raises(ValueError, match="Registry 'nonexistent' not found"):
        client.fetch_index("nonexistent")


@patch("lyra_cli.cli.registry_client.requests.get")
def test_search_skills_no_filter(mock_get, temp_registry_config, mock_registry_index):
    """Test searching skills without filters."""
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RegistryClient(temp_registry_config)
    results = client.search_skills()

    assert len(results) == 2
    assert all(isinstance(r, SkillMetadata) for r in results)


@patch("lyra_cli.cli.registry_client.requests.get")
def test_search_skills_with_query(mock_get, temp_registry_config, mock_registry_index):
    """Test searching skills with query filter."""
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RegistryClient(temp_registry_config)
    results = client.search_skills(query="another")

    assert len(results) == 1
    assert results[0].name == "another-skill"


@patch("lyra_cli.cli.registry_client.requests.get")
def test_search_skills_with_tag(mock_get, temp_registry_config, mock_registry_index):
    """Test searching skills with tag filter."""
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RegistryClient(temp_registry_config)
    results = client.search_skills(tag="research")

    assert len(results) == 1
    assert results[0].name == "another-skill"


@patch("lyra_cli.cli.registry_client.requests.get")
def test_download_skill(
    mock_get, temp_registry_config, mock_registry_index, mock_skill_package
):
    """Test downloading skill package."""
    # Mock index fetch
    mock_index_response = Mock()
    mock_index_response.json.return_value = mock_registry_index
    mock_index_response.raise_for_status = Mock()

    # Mock package download
    mock_package_response = Mock()
    mock_package_response.json.return_value = mock_skill_package
    mock_package_response.raise_for_status = Mock()

    mock_get.side_effect = [mock_index_response, mock_package_response]

    client = RegistryClient(temp_registry_config)
    package = client.download_skill("test-skill")

    assert package == mock_skill_package
    assert package["name"] == "test-skill"
    assert package["version"] == "1.0.0"


@patch("lyra_cli.cli.registry_client.requests.get")
def test_download_skill_not_found(mock_get, temp_registry_config, mock_registry_index):
    """Test downloading non-existent skill."""
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RegistryClient(temp_registry_config)

    with pytest.raises(ValueError, match="Skill 'nonexistent' not found"):
        client.download_skill("nonexistent")


@patch("lyra_cli.cli.registry_client.requests.get")
def test_check_updates(mock_get, temp_registry_config, mock_registry_index):
    """Test checking for skill updates."""
    mock_response = Mock()
    mock_response.json.return_value = mock_registry_index
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = RegistryClient(temp_registry_config)
    installed = {"test-skill": "0.9.0", "another-skill": "2.1.0"}

    updates = client.check_updates(installed)

    assert len(updates) == 1
    assert "test-skill" in updates
    assert updates["test-skill"] == ("0.9.0", "1.0.0")


def test_is_newer_version(temp_registry_config):
    """Test semantic version comparison."""
    client = RegistryClient(temp_registry_config)

    assert client._is_newer_version("1.0.1", "1.0.0")
    assert client._is_newer_version("1.1.0", "1.0.9")
    assert client._is_newer_version("2.0.0", "1.9.9")
    assert not client._is_newer_version("1.0.0", "1.0.0")
    assert not client._is_newer_version("1.0.0", "1.0.1")
