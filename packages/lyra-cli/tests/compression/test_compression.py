"""Tests for Phase 2 Context Compression modules."""

import pytest
import tempfile
import shutil
from pathlib import Path

from lyra_cli.compression.active_compressor import (
    ActiveCompressor,
    FocusRegion,
    KnowledgeBlock,
)
from lyra_cli.compression.hierarchical_compressor import (
    HierarchicalCompressor,
    SensoryItem,
    ShortTermItem,
    LongTermItem,
)
from lyra_cli.compression.observation_pruner import (
    ObservationPruner,
    SmartObservationPruner,
    PruningResult,
)


# ============================================================================
# Active Compressor Tests
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def active_compressor(temp_dir):
    """Create active compressor."""
    return ActiveCompressor(data_dir=temp_dir)


def test_active_add_observation(active_compressor):
    """Test adding observations."""
    active_compressor.add_observation("Test observation 1", phase="exploration")
    active_compressor.add_observation("Test observation 2", phase="exploration")

    assert active_compressor.current_step == 2
    assert active_compressor.total_observations == 2
    assert len(active_compressor.focus_regions) == 1


def test_active_should_compress(active_compressor):
    """Test compression trigger."""
    # Add many observations
    for i in range(25):
        active_compressor.add_observation(f"Observation {i}", phase="exploration")

    assert active_compressor.should_compress() is True


def test_active_compress_region(active_compressor):
    """Test region compression."""
    # Add observations
    for i in range(10):
        active_compressor.add_observation(f"Observation {i}")

    region_id = active_compressor.focus_regions[0].region_id

    # Compress
    kb_id = active_compressor.compress_region(
        region_id,
        knowledge="Learned that X causes Y"
    )

    assert kb_id in active_compressor.knowledge_blocks
    assert active_compressor.focus_regions[0].compressed is True
    assert active_compressor.total_compressed == 10


def test_active_compression_ratio(active_compressor):
    """Test compression ratio calculation."""
    # Add and compress
    for i in range(20):
        active_compressor.add_observation(f"Observation {i}")

    region_id = active_compressor.focus_regions[0].region_id
    active_compressor.compress_region(region_id, "Knowledge extracted")

    ratio = active_compressor.get_compression_ratio()
    assert ratio > 0.5  # Should compress >50%


def test_active_persistence(temp_dir):
    """Test state persistence."""
    comp1 = ActiveCompressor(data_dir=temp_dir)
    comp1.add_observation("Test observation")

    # Create new instance
    comp2 = ActiveCompressor(data_dir=temp_dir)
    assert comp2.total_observations == 1


# ============================================================================
# Hierarchical Compressor Tests
# ============================================================================

@pytest.fixture
def hierarchical_compressor():
    """Create hierarchical compressor."""
    return HierarchicalCompressor()


def test_hierarchical_add_sensory(hierarchical_compressor):
    """Test adding sensory observations."""
    result = hierarchical_compressor.add_sensory("This is a valid observation")
    assert result is True
    assert len(hierarchical_compressor.sensory) == 1


def test_hierarchical_filter_sensory(hierarchical_compressor):
    """Test sensory filtering."""
    # Too short - should be filtered
    result = hierarchical_compressor.add_sensory("Hi")
    assert result is False

    # System noise - should be filtered
    result = hierarchical_compressor.add_sensory("Loading...")
    assert result is False


def test_hierarchical_promote_shortterm(hierarchical_compressor):
    """Test promotion to short-term."""
    item_id = hierarchical_compressor.promote_to_shortterm(
        topic="python",
        observations=["Obs 1", "Obs 2", "Obs 3"]
    )

    assert item_id is not None
    assert len(hierarchical_compressor.short_term) == 1


def test_hierarchical_consolidate_longterm(hierarchical_compressor):
    """Test consolidation to long-term."""
    item_id = hierarchical_compressor.consolidate_to_longterm(
        content="Consolidated knowledge about Python",
        source_topics=["topic1", "topic2"],
        importance=0.8
    )

    assert item_id is not None
    assert len(hierarchical_compressor.long_term) == 1


def test_hierarchical_compression_ratio(hierarchical_compressor):
    """Test compression ratio."""
    # Add many sensory items
    for i in range(100):
        hierarchical_compressor.add_sensory(f"Valid observation number {i}")

    # Promote some to short-term
    hierarchical_compressor.promote_to_shortterm(
        topic="test",
        observations=["Obs 1", "Obs 2"]
    )

    # Consolidate to long-term
    hierarchical_compressor.consolidate_to_longterm(
        content="Summary",
        source_topics=["test"]
    )

    ratio = hierarchical_compressor.get_compression_ratio()
    assert ratio > 1.0  # Should achieve compression


def test_hierarchical_sleep_consolidation(hierarchical_compressor):
    """Test sleep-time consolidation."""
    # Add multiple short-term items with same topic
    for i in range(5):
        hierarchical_compressor.promote_to_shortterm(
            topic="python",
            observations=[f"Obs {i}"]
        )

    # Perform consolidation
    hierarchical_compressor.sleep_consolidation()

    # Should have created long-term memory
    assert len(hierarchical_compressor.long_term) > 0


# ============================================================================
# Observation Pruner Tests
# ============================================================================

@pytest.fixture
def observation_pruner():
    """Create observation pruner."""
    return ObservationPruner(max_output_lines=10)


def test_pruner_basic(observation_pruner):
    """Test basic pruning."""
    observation = "\n".join([f"Line {i}" for i in range(100)])
    goal = "Find errors in the output"

    result = observation_pruner.prune(observation, goal)

    assert result.original_lines == 100
    assert result.pruned_lines <= 10
    assert result.compression_ratio > 0.8


def test_pruner_keyword_matching(observation_pruner):
    """Test keyword-based relevance."""
    observation = """
    Line 1: Normal output
    Line 2: Error occurred in module X
    Line 3: Normal output
    Line 4: Warning: deprecated function
    Line 5: Normal output
    """

    goal = "Find errors and warnings"

    result = observation_pruner.prune(observation, goal)

    # Should prioritize lines with "error" and "warning"
    assert "Error" in result.relevant_content or "error" in result.relevant_content
    assert "Warning" in result.relevant_content or "warning" in result.relevant_content


def test_pruner_extract_keywords(observation_pruner):
    """Test keyword extraction."""
    keywords = observation_pruner._extract_keywords(
        "Find all error messages in the log file"
    )

    assert "find" in keywords
    assert "error" in keywords
    assert "messages" in keywords
    # Stop words should be filtered
    assert "the" not in keywords


def test_pruner_stats(observation_pruner):
    """Test statistics tracking."""
    observation = "\n".join([f"Line {i}" for i in range(50)])
    goal = "Test goal"

    observation_pruner.prune(observation, goal)
    observation_pruner.prune(observation, goal)

    stats = observation_pruner.get_stats()
    assert stats["total_original_lines"] == 100
    assert stats["overall_compression_ratio"] > 0.5


def test_smart_pruner():
    """Test smart pruner with model support."""
    pruner = SmartObservationPruner(use_model=False)

    observation = "\n".join([f"Line {i}" for i in range(100)])
    goal = "Find important information"

    result = pruner.prune(observation, goal)

    assert result.original_lines == 100
    assert result.compression_ratio > 0.8


def test_pruner_empty_observation(observation_pruner):
    """Test pruning empty observation."""
    result = observation_pruner.prune("", "goal")

    assert result.original_lines == 1  # Empty string splits to 1 line
    assert result.pruned_lines == 0


def test_pruner_context_keywords(observation_pruner):
    """Test context-based scoring."""
    observation = """
    Line about Python programming
    Line about JavaScript
    Line about Python libraries
    """

    goal = "Python information"
    context = {"keywords": ["python", "libraries"]}

    result = observation_pruner.prune(observation, goal, context)

    # Should prioritize Python-related lines
    assert "Python" in result.relevant_content
