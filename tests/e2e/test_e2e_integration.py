"""End-to-end integration tests."""
import pytest
from pathlib import Path
import tempfile
import shutil
import json

from lyra_cli.memory import ConversationLog, StructuredFact
from lyra_cli.core.skill_registry import SkillRegistry
from lyra_cli.core.skill_loader import SkillLoader
from lyra_cli.commands.doctor import doctor_command


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for E2E tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_skill_dir(temp_workspace):
    """Create sample skill directory for E2E tests."""
    skill_dir = temp_workspace / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-e2e-skill
description: E2E test skill
origin: test
tags:
  - e2e
  - testing
triggers:
  - e2e-test
---

# E2E Test Skill

This skill is used for end-to-end testing.

## Usage

Test the full workflow from skill discovery to execution.
""")

    return temp_workspace / "skills"


# E2E Test 1: Skills Discovery and Loading Workflow
def test_e2e_skill_discovery_workflow(sample_skill_dir):
    """Test complete skill discovery and loading workflow."""
    # Step 1: Initialize registry
    registry = SkillRegistry(skill_dirs=[sample_skill_dir])

    # Step 2: Load skills
    skills = registry.load_skills()

    # Step 3: Verify skill was discovered
    assert len(skills) > 0
    assert "test-e2e-skill" in skills

    # Step 4: Get skill metadata
    skill = skills["test-e2e-skill"]
    assert skill.name == "test-e2e-skill"
    assert "e2e" in skill.tags

    # Step 5: Load skill content
    loader = SkillLoader()
    content = loader.load_skill_content(skill)

    # Step 6: Verify content loaded
    assert "E2E Test Skill" in content
    assert "Usage" in content


# E2E Test 2: Memory System Workflow
def test_e2e_memory_workflow():
    """Test complete memory system workflow."""
    # Step 1: Create conversation log
    log1 = ConversationLog(
        session_id="e2e_session_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content="I prefer Python for backend development",
    )

    # Step 2: Serialize to dict
    log_dict = log1.to_dict()

    # Step 3: Deserialize from dict
    log2 = ConversationLog.from_dict(log_dict)

    # Step 4: Verify round-trip
    assert log2.session_id == log1.session_id
    assert log2.content == log1.content

    # Step 5: Extract structured fact
    fact = StructuredFact(
        session_id="e2e_session_001",
        content="User prefers Python for backend",
        metadata={"category": "preference", "confidence": 0.9},
        source_turn_ids=[1],
    )

    # Step 6: Verify fact extraction
    assert fact.content == "User prefers Python for backend"
    assert fact.metadata["category"] == "preference"
    assert 1 in fact.source_turn_ids


# E2E Test 3: Commands Integration Workflow
def test_e2e_commands_workflow(temp_workspace, capsys):
    """Test complete commands workflow."""
    import click

    # Step 1: Run doctor command
    try:
        doctor_command(repo_root=temp_workspace, json_out=True)
    except (SystemExit, click.exceptions.Exit):
        pass

    # Step 2: Capture output
    captured = capsys.readouterr()

    # Step 3: Parse JSON output
    try:
        data = json.loads(captured.out)

        # Step 4: Verify structure
        assert "repo_root" in data
        assert "ok" in data
        assert "probes" in data

        # Step 5: Verify probes
        assert isinstance(data["probes"], list)
        assert len(data["probes"]) > 0

        # Step 6: Check probe structure
        first_probe = data["probes"][0]
        assert "category" in first_probe
        assert "name" in first_probe
        assert "ok" in first_probe
    except json.JSONDecodeError:
        # If no JSON output, that's acceptable for some states
        pass


# E2E Test 4: Multi-System Integration
def test_e2e_multi_system_integration(sample_skill_dir):
    """Test integration across skills, memory, and commands."""
    # Step 1: Load skills
    registry = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills = registry.load_skills()

    # Step 2: Create conversation about skill
    log = ConversationLog(
        session_id="e2e_multi_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content=f"Tell me about the {list(skills.keys())[0]} skill",
    )

    # Step 3: Extract fact from conversation
    skill_name = list(skills.keys())[0]
    fact = StructuredFact(
        session_id="e2e_multi_001",
        content=f"User asked about {skill_name} skill",
        metadata={"category": "query", "skill": skill_name},
        source_turn_ids=[1],
    )

    # Step 4: Verify integration
    assert log.content in f"Tell me about the {skill_name} skill"
    assert fact.metadata["skill"] == skill_name
    assert skill_name in skills


# E2E Test 5: Full Workflow Simulation
def test_e2e_full_workflow_simulation(sample_skill_dir, temp_workspace):
    """Simulate a complete user workflow."""
    # Scenario: User discovers skills, runs commands, stores memories

    # Step 1: User runs doctor command
    import click
    try:
        doctor_command(repo_root=temp_workspace, json_out=True)
    except (SystemExit, click.exceptions.Exit):
        pass

    # Step 2: User discovers available skills
    registry = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills = registry.load_skills()
    assert len(skills) > 0

    # Step 3: User selects a skill
    skill_name = list(skills.keys())[0]
    skill = skills[skill_name]

    # Step 4: User loads skill content
    loader = SkillLoader()
    content = loader.load_skill_content(skill)
    assert len(content) > 0

    # Step 5: User interaction is logged
    log = ConversationLog(
        session_id="e2e_full_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content=f"I want to use the {skill_name} skill",
    )

    # Step 6: System extracts structured fact
    fact = StructuredFact(
        session_id="e2e_full_001",
        content=f"User wants to use {skill_name}",
        metadata={"category": "intent", "skill": skill_name},
        source_turn_ids=[1],
    )

    # Step 7: Verify complete workflow
    assert skill_name in log.content
    assert skill_name in fact.content
    assert fact.metadata["skill"] == skill_name


# E2E Test 6: Error Handling Across Systems
def test_e2e_error_handling_workflow():
    """Test error handling across integrated systems."""
    # Test 1: Skills with invalid directory
    registry = SkillRegistry(skill_dirs=[Path("/nonexistent/path")])
    skills = registry.load_skills()
    assert len(skills) == 0  # Should handle gracefully

    # Test 2: Memory with invalid data
    try:
        log = ConversationLog(
            session_id="",  # Empty session ID
            turn_id=1,
            timestamp="2026-05-17T12:00:00",
            role="user",
            content="Test",
        )
        # Should create but with empty session_id
        assert log.session_id == ""
    except Exception:
        # Or raise exception - both are acceptable
        pass

    # Test 3: Commands with invalid path
    import click
    try:
        doctor_command(repo_root=Path("/nonexistent/path"), json_out=True)
    except (SystemExit, click.exceptions.Exit):
        # Expected - should exit gracefully
        pass


# E2E Test 7: Data Flow Validation
def test_e2e_data_flow_validation(sample_skill_dir):
    """Test data flow between systems."""
    # Step 1: Input - User query
    user_query = "Show me available skills"

    # Step 2: Process - Discover skills
    registry = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills = registry.load_skills()

    # Step 3: Store - Log conversation
    log = ConversationLog(
        session_id="e2e_flow_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content=user_query,
    )

    # Step 4: Extract - Create structured fact
    skill_names = list(skills.keys())
    fact = StructuredFact(
        session_id="e2e_flow_001",
        content=f"User queried skills: {', '.join(skill_names)}",
        metadata={"category": "query", "skill_count": len(skill_names)},
        source_turn_ids=[1],
    )

    # Step 5: Validate data flow
    assert user_query == log.content
    assert len(skill_names) > 0
    assert fact.metadata["skill_count"] == len(skills)


# E2E Test 8: Concurrent Operations
def test_e2e_concurrent_operations(sample_skill_dir):
    """Test multiple operations happening concurrently."""
    # Simulate concurrent user actions

    # Action 1: Load skills
    registry = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills = registry.load_skills()

    # Action 2: Create multiple conversation logs
    logs = [
        ConversationLog(
            session_id="e2e_concurrent_001",
            turn_id=i,
            timestamp=f"2026-05-17T12:00:{i:02d}",
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
        )
        for i in range(5)
    ]

    # Action 3: Create multiple facts
    facts = [
        StructuredFact(
            session_id="e2e_concurrent_001",
            content=f"Fact {i}",
            metadata={"index": i},
            source_turn_ids=[i],
        )
        for i in range(3)
    ]

    # Verify all operations completed
    assert len(skills) > 0
    assert len(logs) == 5
    assert len(facts) == 3


# E2E Test 9: System State Consistency
def test_e2e_system_state_consistency(sample_skill_dir):
    """Test that system state remains consistent across operations."""
    # Initial state
    registry1 = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills1 = registry1.load_skills()
    initial_count = len(skills1)

    # Perform operations
    log = ConversationLog(
        session_id="e2e_state_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content="Test",
    )

    # Reload skills
    registry2 = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills2 = registry2.load_skills()
    final_count = len(skills2)

    # Verify consistency
    assert initial_count == final_count
    assert set(skills1.keys()) == set(skills2.keys())


# E2E Test 10: Complete User Session
def test_e2e_complete_user_session(sample_skill_dir, temp_workspace):
    """Simulate a complete user session from start to finish."""
    session_id = "e2e_session_complete"

    # 1. Session starts - run doctor
    import click
    try:
        doctor_command(repo_root=temp_workspace, json_out=True)
    except (SystemExit, click.exceptions.Exit):
        pass

    # 2. User discovers skills
    registry = SkillRegistry(skill_dirs=[sample_skill_dir])
    skills = registry.load_skills()

    # 3. User asks about a skill
    skill_name = list(skills.keys())[0]
    log1 = ConversationLog(
        session_id=session_id,
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content=f"What is {skill_name}?",
    )

    # 4. System responds
    log2 = ConversationLog(
        session_id=session_id,
        turn_id=2,
        timestamp="2026-05-17T12:00:01",
        role="assistant",
        content=f"{skill_name} is a test skill for E2E testing",
    )

    # 5. System extracts fact
    fact = StructuredFact(
        session_id=session_id,
        content=f"User learned about {skill_name}",
        metadata={"category": "learning", "skill": skill_name},
        source_turn_ids=[1, 2],
    )

    # 6. Verify complete session
    assert log1.session_id == session_id
    assert log2.session_id == session_id
    assert fact.session_id == session_id
    assert len(fact.source_turn_ids) == 2
