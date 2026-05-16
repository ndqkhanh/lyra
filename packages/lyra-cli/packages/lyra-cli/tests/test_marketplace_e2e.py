"""End-to-end tests for skill marketplace workflows."""

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
def mock_registry_with_skills():
    """Mock registry with multiple skills."""
    return {
        "version": "1.0",
        "skills": {
            "auto-research": {
                "name": "auto-research",
                "version": "2.0.0",
                "description": "Automated research assistant",
                "author": "lyra-team",
                "repository": "https://github.com/lyra/auto-research",
                "tags": ["research", "automation"],
                "dependencies": {},
                "download_url": "https://registry.lyra.ai/skills/auto-research/2.0.0.json",
            },
            "code-review": {
                "name": "code-review",
                "version": "1.5.0",
                "description": "Automated code review",
                "author": "lyra-team",
                "repository": "https://github.com/lyra/code-review",
                "tags": ["code", "review"],
                "dependencies": {},
                "download_url": "https://registry.lyra.ai/skills/code-review/1.5.0.json",
            },
        },
    }


@pytest.fixture
def skill_packages():
    """Mock skill packages for download."""
    return {
        "auto-research": {
            "name": "auto-research",
            "version": "2.0.0",
            "description": "Automated research assistant",
            "author": "lyra-team",
            "category": "research",
            "execution": {"type": "prompt"},
            "args": {"hint": "<query>"},
        },
        "code-review": {
            "name": "code-review",
            "version": "1.5.0",
            "description": "Automated code review",
            "author": "lyra-team",
            "category": "development",
            "execution": {"type": "prompt"},
            "args": {"hint": "<file>"},
        },
    }


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_e2e_browse_install_workflow(
    mock_registry_client, mock_session, skill_packages
):
    """Test complete browse → install workflow."""
    mock_client = Mock()

    # Setup browse
    mock_client.search_skills.return_value = [
        Mock(
            name="auto-research",
            version="2.0.0",
            description="Automated research assistant",
            author="lyra-team",
            tags=["research", "automation"],
        )
    ]

    # Setup install
    mock_client.download_skill.return_value = skill_packages["auto-research"]
    mock_registry_client.return_value = mock_client

    # Step 1: Browse for research skills
    browse_result = _cmd_skill_browse(mock_session, "--tag research")
    assert browse_result.output is not None
    assert "auto-research" in browse_result.output

    # Step 2: Install the skill
    install_result = _cmd_skill_install(mock_session, "auto-research")
    assert install_result.output is not None
    assert "successfully installed" in install_result.output.lower()

    # Verify skill file was created
    skill_dir = Path.home() / ".lyra" / "skills"
    skill_file = skill_dir / "auto-research.json"
    assert skill_file.exists()

    # Cleanup
    if skill_file.exists():
        skill_file.unlink()


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_e2e_install_update_workflow(
    mock_registry_client, mock_session, skill_packages
):
    """Test complete install → update workflow."""
    mock_client = Mock()

    # Step 1: Install version 1.0.0
    old_package = skill_packages["auto-research"].copy()
    old_package["version"] = "1.0.0"
    mock_client.download_skill.return_value = old_package
    mock_registry_client.return_value = mock_client

    install_result = _cmd_skill_install(mock_session, "auto-research")
    assert "successfully installed" in install_result.output.lower()

    # Step 2: Check for updates
    mock_client.check_updates.return_value = {
        "auto-research": ("1.0.0", "2.0.0")
    }
    mock_client.download_skill.return_value = skill_packages["auto-research"]

    update_result = _cmd_skill_update(mock_session, "")
    assert "updated" in update_result.output.lower()
    assert "1.0.0" in update_result.output
    assert "2.0.0" in update_result.output

    # Cleanup
    skill_file = Path.home() / ".lyra" / "skills" / "auto-research.json"
    if skill_file.exists():
        skill_file.unlink()


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_e2e_install_uninstall_workflow(
    mock_registry_client, mock_session, skill_packages
):
    """Test complete install → uninstall workflow."""
    mock_client = Mock()
    mock_client.download_skill.return_value = skill_packages["code-review"]
    mock_registry_client.return_value = mock_client

    # Step 1: Install skill
    install_result = _cmd_skill_install(mock_session, "code-review")
    assert "successfully installed" in install_result.output.lower()

    skill_file = Path.home() / ".lyra" / "skills" / "code-review.json"
    assert skill_file.exists()

    # Step 2: Uninstall skill
    uninstall_result = _cmd_skill_uninstall(mock_session, "code-review")
    assert "uninstalled" in uninstall_result.output.lower()
    assert not skill_file.exists()


@patch("lyra_cli.cli.registry_client.RegistryClient")
def test_e2e_multiple_skills_workflow(
    mock_registry_client, mock_session, skill_packages
):
    """Test installing and managing multiple skills."""
    mock_client = Mock()
    mock_registry_client.return_value = mock_client

    # Install multiple skills
    for skill_name in ["auto-research", "code-review"]:
        mock_client.download_skill.return_value = skill_packages[skill_name]
        result = _cmd_skill_install(mock_session, skill_name)
        assert "successfully installed" in result.output.lower()

    # Verify both skills exist
    skill_dir = Path.home() / ".lyra" / "skills"
    assert (skill_dir / "auto-research.json").exists()
    assert (skill_dir / "code-review.json").exists()

    # Cleanup
    for skill_name in ["auto-research", "code-review"]:
        skill_file = skill_dir / f"{skill_name}.json"
        if skill_file.exists():
            skill_file.unlink()
