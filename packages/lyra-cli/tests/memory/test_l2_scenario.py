"""
Tests for L2 Scenario Layer.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from lyra_cli.memory.l2_scenario import ScenarioStore, ScenarioBlock


class TestScenarioBlock:
    """Test ScenarioBlock dataclass."""

    def test_create_block(self):
        """Test creating a scenario block."""
        block = ScenarioBlock(
            id="scene_001",
            session_id="test-session-1",
            title="User Authentication Flow",
            content="User prefers JWT-based authentication with refresh tokens.",
            timestamp=datetime.now().isoformat(),
            source_atom_ids=[1, 2, 3],
        )

        assert block.id == "scene_001"
        assert block.title == "User Authentication Flow"
        assert block.source_atom_ids == [1, 2, 3]

    def test_to_markdown(self):
        """Test conversion to Markdown."""
        block = ScenarioBlock(
            id="scene_001",
            session_id="test-session-1",
            title="Authentication",
            content="JWT-based auth with refresh tokens.",
            timestamp="2026-05-16T10:00:00",
            source_atom_ids=[1, 2],
        )

        markdown = block.to_markdown()

        assert "---" in markdown
        assert "id: scene_001" in markdown
        assert "# Authentication" in markdown
        assert "JWT-based auth" in markdown

    def test_from_markdown(self):
        """Test parsing from Markdown."""
        markdown = """---
id: scene_001
session_id: test-session-1
timestamp: 2026-05-16T10:00:00
source_atom_ids: [1, 2, 3]
---

# Authentication Flow

User prefers JWT-based authentication.
"""

        block = ScenarioBlock.from_markdown(markdown)

        assert block.id == "scene_001"
        assert block.session_id == "test-session-1"
        assert block.title == "Authentication Flow"
        assert "JWT-based" in block.content
        assert block.source_atom_ids == [1, 2, 3]

    def test_roundtrip(self):
        """Test Markdown roundtrip conversion."""
        original = ScenarioBlock(
            id="scene_001",
            session_id="test-session-1",
            title="Test Scene",
            content="Test content here.",
            timestamp="2026-05-16T10:00:00",
            source_atom_ids=[1, 2],
        )

        markdown = original.to_markdown()
        restored = ScenarioBlock.from_markdown(markdown)

        assert restored.id == original.id
        assert restored.session_id == original.session_id
        assert restored.title == original.title
        assert restored.content == original.content


class TestScenarioStore:
    """Test ScenarioStore."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def store(self, temp_dir):
        """Create ScenarioStore instance."""
        return ScenarioStore(data_dir=temp_dir, max_scenes=15)

    def test_init(self, store, temp_dir):
        """Test store initialization."""
        assert store.data_dir == Path(temp_dir)
        assert store.max_scenes == 15
        assert store.data_dir.exists()

    def test_save_and_load(self, store):
        """Test saving and loading a scene."""
        scene = ScenarioBlock(
            id="scene_001",
            session_id="test-session-1",
            title="Authentication",
            content="JWT-based auth implementation.",
            timestamp=datetime.now().isoformat(),
            source_atom_ids=[1, 2, 3],
        )

        # Save
        store.save(scene)

        # Load
        loaded = store.load("scene_001")

        assert loaded is not None
        assert loaded.id == scene.id
        assert loaded.title == scene.title
        assert loaded.content == scene.content

    def test_list_scenes(self, store):
        """Test listing scenes."""
        # Create multiple scenes
        for i in range(5):
            scene = ScenarioBlock(
                id=f"scene_{i:03d}",
                session_id="test-session-1",
                title=f"Scene {i}",
                content=f"Content {i}",
                timestamp=datetime.now().isoformat(),
            )
            store.save(scene)

        # List all scenes
        scenes = store.list_scenes()
        assert len(scenes) == 5

        # List by session
        scenes = store.list_scenes("test-session-1")
        assert len(scenes) == 5

        scenes = store.list_scenes("other-session")
        assert len(scenes) == 0

    def test_delete(self, store):
        """Test deleting a scene."""
        scene = ScenarioBlock(
            id="scene_001",
            session_id="test-session-1",
            title="Test",
            content="Test content",
            timestamp=datetime.now().isoformat(),
        )

        store.save(scene)
        assert store.load("scene_001") is not None

        # Delete
        result = store.delete("scene_001")
        assert result is True
        assert store.load("scene_001") is None

        # Delete non-existent
        result = store.delete("scene_999")
        assert result is False

    def test_enforce_max_scenes(self, store):
        """Test enforcing maximum scene limit."""
        # Create more scenes than the limit
        for i in range(20):
            scene = ScenarioBlock(
                id=f"scene_{i:03d}",
                session_id="test-session-1",
                title=f"Scene {i}",
                content=f"Content {i}",
                timestamp=f"2026-05-16T{i:02d}:00:00",
            )
            store.save(scene)

        # Enforce limit
        deleted = store.enforce_max_scenes()
        assert deleted == 5  # 20 - 15 = 5

        # Verify only 15 scenes remain
        scenes = store.list_scenes()
        assert len(scenes) == 15

    def test_count(self, store):
        """Test counting scenes."""
        # Create scenes for different sessions
        for i in range(3):
            scene = ScenarioBlock(
                id=f"scene_1_{i:03d}",
                session_id="session-1",
                title=f"Scene {i}",
                content=f"Content {i}",
                timestamp=datetime.now().isoformat(),
            )
            store.save(scene)

        for i in range(2):
            scene = ScenarioBlock(
                id=f"scene_2_{i:03d}",
                session_id="session-2",
                title=f"Scene {i}",
                content=f"Content {i}",
                timestamp=datetime.now().isoformat(),
            )
            store.save(scene)

        # Count all
        assert store.count() == 5

        # Count by session
        assert store.count("session-1") == 3
        assert store.count("session-2") == 2

    def test_get_stats(self, store):
        """Test getting storage statistics."""
        # Create some scenes
        for i in range(5):
            scene = ScenarioBlock(
                id=f"scene_{i:03d}",
                session_id=f"session-{i % 2}",
                title=f"Scene {i}",
                content=f"Content {i}",
                timestamp=datetime.now().isoformat(),
            )
            store.save(scene)

        stats = store.get_stats()

        assert stats["total_scenes"] == 5
        assert stats["total_size_kb"] > 0
        assert stats["unique_sessions"] == 2
        assert stats["max_scenes"] == 15

    def test_human_readable_format(self, store):
        """Test that saved files are human-readable."""
        scene = ScenarioBlock(
            id="scene_001_auth",
            session_id="test-session-1",
            title="Authentication System",
            content="The user prefers JWT-based authentication with refresh tokens.",
            timestamp="2026-05-16T10:00:00",
            source_atom_ids=[1, 2, 3],
        )

        store.save(scene)

        # Read the file directly
        scene_path = store._get_scene_path("scene_001_auth")
        content = scene_path.read_text()

        # Verify it's readable Markdown
        assert content.startswith("---")
        assert "# Authentication System" in content
        assert "JWT-based authentication" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
