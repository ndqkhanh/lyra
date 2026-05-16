"""Tests for L4 Procedural Memory Layer."""

import pytest
import tempfile
import shutil
from pathlib import Path

from lyra_cli.memory.l4_procedural import ProceduralSkill, ProceduralMemoryStore


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def store(temp_dir):
    """Create a procedural memory store."""
    return ProceduralMemoryStore(data_dir=temp_dir)


def test_add_skill(store):
    """Test adding a skill."""
    skill = ProceduralSkill(
        skill_id="skill_001",
        skill_name="parse_json",
        code="import json\ndef parse(s): return json.loads(s)",
        interface={"input": "str", "output": "dict"},
        verifier_test="assert parse('{\"a\":1}') == {'a': 1}",
        success_rate=0.95,
    )

    skill_id = store.add_skill(skill)
    assert skill_id == "skill_001"

    retrieved = store.get_skill("skill_001")
    assert retrieved is not None
    assert retrieved.skill_name == "parse_json"
    assert retrieved.success_rate == 0.95


def test_search_skills(store):
    """Test searching for skills."""
    # Add multiple skills
    skills = [
        ProceduralSkill(
            skill_id="skill_001",
            skill_name="parse_json",
            code="import json\ndef parse(s): return json.loads(s)",
            interface={},
            verifier_test="",
            success_rate=0.95,
        ),
        ProceduralSkill(
            skill_id="skill_002",
            skill_name="parse_xml",
            code="import xml\ndef parse(s): return xml.parse(s)",
            interface={},
            verifier_test="",
            success_rate=0.85,
        ),
        ProceduralSkill(
            skill_id="skill_003",
            skill_name="format_json",
            code="import json\ndef format(d): return json.dumps(d)",
            interface={},
            verifier_test="",
            success_rate=0.90,
        ),
    ]

    for skill in skills:
        store.add_skill(skill)

    # Search for "json"
    results = store.search_skills("json")
    assert len(results) == 2
    assert results[0].skill_name == "parse_json"  # Higher success rate


def test_record_usage(store):
    """Test recording skill usage."""
    skill = ProceduralSkill(
        skill_id="skill_001",
        skill_name="test_skill",
        code="def test(): pass",
        interface={},
        verifier_test="",
        success_rate=0.5,
        usage_count=0,
    )

    store.add_skill(skill)

    # Record successful usage
    store.record_usage("skill_001", success=True, cost=0.01, latency=0.5)

    updated = store.get_skill("skill_001")
    assert updated.usage_count == 1
    assert updated.success_rate > 0.5  # Should increase
    assert updated.last_used is not None


def test_get_top_skills(store):
    """Test getting top skills."""
    skills = [
        ProceduralSkill(
            skill_id=f"skill_{i:03d}",
            skill_name=f"skill_{i}",
            code="",
            interface={},
            verifier_test="",
            success_rate=0.5 + i * 0.1,
            usage_count=i,
        )
        for i in range(5)
    ]

    for skill in skills:
        store.add_skill(skill)

    top = store.get_top_skills(limit=3)
    assert len(top) == 3
    assert top[0].skill_id == "skill_004"  # Highest success rate


def test_persistence(temp_dir):
    """Test that skills persist across store instances."""
    store1 = ProceduralMemoryStore(data_dir=temp_dir)

    skill = ProceduralSkill(
        skill_id="skill_001",
        skill_name="test_skill",
        code="def test(): pass",
        interface={},
        verifier_test="",
    )

    store1.add_skill(skill)

    # Create new store instance
    store2 = ProceduralMemoryStore(data_dir=temp_dir)

    retrieved = store2.get_skill("skill_001")
    assert retrieved is not None
    assert retrieved.skill_name == "test_skill"


def test_update_skill(store):
    """Test updating skill metrics."""
    skill = ProceduralSkill(
        skill_id="skill_001",
        skill_name="test_skill",
        code="def test(): pass",
        interface={},
        verifier_test="",
        success_rate=0.5,
    )

    store.add_skill(skill)

    store.update_skill("skill_001", success_rate=0.9, cost=0.05)

    updated = store.get_skill("skill_001")
    assert updated.success_rate == 0.9
    assert updated.cost == 0.05


def test_min_success_rate_filter(store):
    """Test filtering by minimum success rate."""
    skills = [
        ProceduralSkill(
            skill_id="skill_001",
            skill_name="low_success",
            code="",
            interface={},
            verifier_test="",
            success_rate=0.3,
        ),
        ProceduralSkill(
            skill_id="skill_002",
            skill_name="high_success",
            code="",
            interface={},
            verifier_test="",
            success_rate=0.9,
        ),
    ]

    for skill in skills:
        store.add_skill(skill)

    results = store.search_skills("success", min_success_rate=0.5)
    assert len(results) == 1
    assert results[0].skill_id == "skill_002"
