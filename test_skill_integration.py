#!/usr/bin/env python3
"""Integration test for Phase 1 skill system implementation."""

from lyra_cli.cli.skill_manager import SkillManager
from lyra_cli.commands.registry import COMMAND_REGISTRY


def test_skill_discovery():
    """Test that skills are discovered from both global and local directories."""
    sm = SkillManager()
    skills = sm.list_skills()

    print(f"✓ Discovered {len(skills)} skills")
    assert len(skills) >= 2, "Should find at least 2 skills (tdd-guide, auto-research)"

    assert "tdd-guide" in skills, "Should find tdd-guide skill"
    assert "auto-research" in skills, "Should find auto-research skill"
    print("✓ Found expected skills: tdd-guide, auto-research")


def test_command_specs_generation():
    """Test that command specs are generated correctly."""
    sm = SkillManager()
    specs = sm.get_command_specs()

    print(f"✓ Generated {len(specs)} command specs")
    assert len(specs) >= 2, "Should generate at least 2 command specs"

    # Check tdd-guide spec
    tdd_spec = next((s for s in specs if s.name == "tdd-guide"), None)
    assert tdd_spec is not None, "Should have tdd-guide command spec"
    assert "tdd" in tdd_spec.aliases, "Should have 'tdd' alias"
    assert "test-first" in tdd_spec.aliases, "Should have 'test-first' alias"
    print("✓ tdd-guide spec has correct aliases")

    # Check auto-research spec
    research_spec = next((s for s in specs if s.name == "auto-research"), None)
    assert research_spec is not None, "Should have auto-research command spec"
    assert "research" in research_spec.aliases, "Should have 'research' alias"
    assert "deep-research" in research_spec.aliases, "Should have 'deep-research' alias"
    print("✓ auto-research spec has correct aliases")


def test_skill_command_registered():
    """Test that /skill command is registered in COMMAND_REGISTRY."""
    skill_cmd = next((cmd for cmd in COMMAND_REGISTRY if cmd.name == "skill"), None)

    assert skill_cmd is not None, "/skill command should be registered"
    assert skill_cmd.handler.__name__ == "_cmd_skill", "Handler should be _cmd_skill dispatcher"
    assert skill_cmd.subcommands == ("list", "search", "reload", "info"), "Should have correct subcommands"
    print("✓ /skill command registered with correct handler and subcommands")


def test_skill_search():
    """Test skill search functionality."""
    sm = SkillManager()

    # Search for "research"
    results = sm.search_skills("research")
    assert len(results) > 0, "Should find skills matching 'research'"
    assert "auto-research" in results, "Should find auto-research"
    print("✓ Search for 'research' found auto-research")

    # Search for "tdd"
    results = sm.search_skills("tdd")
    assert len(results) > 0, "Should find skills matching 'tdd'"
    assert "tdd-guide" in results, "Should find tdd-guide"
    print("✓ Search for 'tdd' found tdd-guide")


def test_get_skill():
    """Test getting individual skill details."""
    sm = SkillManager()

    # Get tdd-guide
    skill = sm.get_skill("tdd-guide")
    assert skill is not None, "Should find tdd-guide skill"
    assert skill["name"] == "tdd-guide", "Should have correct name"
    assert skill["category"] == "development", "Should have correct category"
    assert "tdd" in skill["aliases"], "Should have tdd alias"
    print("✓ get_skill('tdd-guide') returns correct data")

    # Get auto-research
    skill = sm.get_skill("auto-research")
    assert skill is not None, "Should find auto-research skill"
    assert skill["name"] == "auto-research", "Should have correct name"
    assert skill["category"] == "research", "Should have correct category"
    print("✓ get_skill('auto-research') returns correct data")


if __name__ == "__main__":
    print("Running Phase 1 Skill System Integration Tests\n")
    print("=" * 60)

    try:
        test_skill_discovery()
        print()
        test_command_specs_generation()
        print()
        test_skill_command_registered()
        print()
        test_skill_search()
        print()
        test_get_skill()
        print()
        print("=" * 60)
        print("✓ All integration tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
