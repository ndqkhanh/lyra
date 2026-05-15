"""Test multi-agent orchestration."""

import asyncio
from pathlib import Path

from lyra_cli.team import LyraTeam


async def test_team_orchestration():
    """Test team orchestration with lazy-spawn."""
    print("Testing team orchestration...")

    # Create team
    team = LyraTeam(blueprints_dir=Path(".lyra/blueprints"))

    # Create mock blueprints directory
    blueprints_dir = Path(".lyra/blueprints")
    blueprints_dir.mkdir(parents=True, exist_ok=True)

    # Create researcher blueprint
    researcher_bp = blueprints_dir / "researcher.md"
    researcher_bp.write_text(
        """# Researcher Agent

Specializes in web search and information gathering.
"""
    )

    # Reload blueprints
    team._load_blueprints()

    # Spawn researcher
    researcher = await team.spawn("researcher")
    print(f"✓ Spawned: {researcher.name}")

    # Spawn another researcher instance
    researcher2 = await team.spawn("researcher")
    print(f"✓ Spawned: {researcher2.name}")

    # Send message
    await team.send_message(
        to="researcher#1",
        content="Search for Claude Code documentation",
        from_agent="lead",
    )

    # Wait for processing
    await asyncio.sleep(0.1)

    # Verify
    assert len(team.list_members()) == 2
    assert "researcher#1" in team.list_members()
    assert "researcher#2" in team.list_members()

    print("✓ Team orchestration test passed")
    print(f"  Blueprints: {team.list_blueprints()}")
    print(f"  Members: {team.list_members()}")

    # Cleanup
    await team.shutdown()


if __name__ == "__main__":
    asyncio.run(test_team_orchestration())
