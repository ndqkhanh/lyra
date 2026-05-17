"""Tests for enhanced commands."""

import pytest

from lyra_cli.commands.enhanced import CommandEnhancer


@pytest.mark.anyio
async def test_model_command_list():
    """Model command lists available models."""
    cmd = CommandEnhancer.create_model_command()
    context = {"model": "sonnet"}

    result = await cmd.handler("", context)

    assert "sonnet" in result.lower()
    assert "haiku" in result.lower()
    assert "opus" in result.lower()


@pytest.mark.anyio
async def test_model_command_switch():
    """Model command switches models."""
    cmd = CommandEnhancer.create_model_command()
    context = {"model": "sonnet"}

    result = await cmd.handler("opus", context)

    assert context["model"] == "opus"
    assert "opus" in result.lower()


@pytest.mark.anyio
async def test_skills_command_list():
    """Skills command lists available skills."""
    cmd = CommandEnhancer.create_skills_command()
    context = {
        "skills_registry": {
            "skill1": {"description": "Test skill 1"},
            "skill2": {"description": "Test skill 2"},
        }
    }

    result = await cmd.handler("", context)

    assert "skill1" in result
    assert "skill2" in result


@pytest.mark.anyio
async def test_mcp_command_list():
    """MCP command lists connected servers."""
    cmd = CommandEnhancer.create_mcp_command()
    context = {"mcp_servers": {"github": "connected", "memory": "connected"}}

    result = await cmd.handler("", context)

    assert "github" in result
    assert "memory" in result
