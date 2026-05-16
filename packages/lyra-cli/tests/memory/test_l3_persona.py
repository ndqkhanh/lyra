"""
Tests for L3 Persona Layer.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from lyra_cli.memory.l3_persona import PersonaStore, UserPersona


class TestUserPersona:
    """Test UserPersona dataclass."""

    def test_create_persona(self):
        """Test creating a user persona."""
        persona = UserPersona(
            session_id="test-session-1",
            content="User is a Python developer interested in AI and machine learning.",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )

        assert persona.session_id == "test-session-1"
        assert "Python developer" in persona.content
        assert persona.atom_count == 50

    def test_to_markdown(self):
        """Test conversion to Markdown."""
        persona = UserPersona(
            session_id="test-session-1",
            content="User prefers Python and TypeScript.",
            timestamp="2026-05-16T10:00:00",
            atom_count=50,
        )

        markdown = persona.to_markdown()

        assert "---" in markdown
        assert "session_id: test-session-1" in markdown
        assert "atom_count: 50" in markdown
        assert "# User Profile" in markdown
        assert "Python and TypeScript" in markdown

    def test_from_markdown(self):
        """Test parsing from Markdown."""
        markdown = """---
session_id: test-session-1
timestamp: 2026-05-16T10:00:00
atom_count: 50
---

# User Profile

User is a Python developer interested in AI.
"""

        persona = UserPersona.from_markdown(markdown)

        assert persona.session_id == "test-session-1"
        assert persona.atom_count == 50
        assert "Python developer" in persona.content

    def test_roundtrip(self):
        """Test Markdown roundtrip conversion."""
        original = UserPersona(
            session_id="test-session-1",
            content="User prefers functional programming.",
            timestamp="2026-05-16T10:00:00",
            atom_count=50,
        )

        markdown = original.to_markdown()
        restored = UserPersona.from_markdown(markdown)

        assert restored.session_id == original.session_id
        assert restored.content == original.content
        assert restored.atom_count == original.atom_count


class TestPersonaStore:
    """Test PersonaStore."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def store(self, temp_dir):
        """Create PersonaStore instance."""
        return PersonaStore(
            data_dir=temp_dir,
            max_backups=3,
            generation_threshold=50,
        )

    def test_init(self, store, temp_dir):
        """Test store initialization."""
        assert store.data_dir == Path(temp_dir)
        assert store.max_backups == 3
        assert store.generation_threshold == 50
        assert store.data_dir.exists()

    def test_save_and_load(self, store):
        """Test saving and loading persona."""
        persona = UserPersona(
            session_id="test-session-1",
            content="User is a Python developer.",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )

        # Save
        store.save(persona, create_backup=False)

        # Load
        loaded = store.load()

        assert loaded is not None
        assert loaded.session_id == persona.session_id
        assert loaded.content == persona.content
        assert loaded.atom_count == persona.atom_count

    def test_backup_creation(self, store):
        """Test backup creation."""
        # Save first persona
        persona1 = UserPersona(
            session_id="test-session-1",
            content="Version 1",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )
        store.save(persona1, create_backup=False)

        # Save second persona with backup
        persona2 = UserPersona(
            session_id="test-session-1",
            content="Version 2",
            timestamp=datetime.now().isoformat(),
            atom_count=100,
        )
        store.save(persona2, create_backup=True)

        # Check backup was created
        backups = store.list_backups()
        assert len(backups) == 1

        # Current should be version 2
        current = store.load()
        assert current.content == "Version 2"

    def test_backup_rotation(self, store):
        """Test backup rotation (max 3 backups)."""
        # Save 5 versions
        for i in range(5):
            persona = UserPersona(
                session_id="test-session-1",
                content=f"Version {i + 1}",
                timestamp=datetime.now().isoformat(),
                atom_count=(i + 1) * 50,
            )
            store.save(persona, create_backup=(i > 0))

        # Should have max 3 backups
        backups = store.list_backups()
        assert len(backups) <= 3

    def test_restore_backup(self, store):
        """Test restoring from backup."""
        # Save two versions
        persona1 = UserPersona(
            session_id="test-session-1",
            content="Version 1",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )
        store.save(persona1, create_backup=False)

        persona2 = UserPersona(
            session_id="test-session-1",
            content="Version 2",
            timestamp=datetime.now().isoformat(),
            atom_count=100,
        )
        store.save(persona2, create_backup=True)

        # Restore backup
        result = store.restore_backup(1)
        assert result is True

        # Should be back to version 1
        current = store.load()
        assert current.content == "Version 1"

    def test_should_regenerate(self, store):
        """Test regeneration logic."""
        # No persona exists
        assert store.should_regenerate(50) is True

        # Save persona with 50 atoms
        persona = UserPersona(
            session_id="test-session-1",
            content="Initial persona",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )
        store.save(persona, create_backup=False)

        # Not enough new atoms (threshold is 50)
        assert store.should_regenerate(75) is False

        # Enough new atoms
        assert store.should_regenerate(100) is True
        assert store.should_regenerate(150) is True

    def test_delete(self, store):
        """Test deleting persona."""
        persona = UserPersona(
            session_id="test-session-1",
            content="Test persona",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )

        store.save(persona, create_backup=False)
        assert store.load() is not None

        # Delete
        result = store.delete()
        assert result is True
        assert store.load() is None

        # Delete non-existent
        result = store.delete()
        assert result is False

    def test_get_stats(self, store):
        """Test getting storage statistics."""
        # No persona
        stats = store.get_stats()
        assert stats["has_persona"] is False
        assert stats["atom_count"] == 0

        # Save persona
        persona = UserPersona(
            session_id="test-session-1",
            content="Test persona",
            timestamp=datetime.now().isoformat(),
            atom_count=50,
        )
        store.save(persona, create_backup=False)

        stats = store.get_stats()
        assert stats["has_persona"] is True
        assert stats["atom_count"] == 50
        assert stats["backup_count"] == 0
        assert stats["total_size_kb"] > 0

    def test_human_readable_format(self, store):
        """Test that saved file is human-readable."""
        persona = UserPersona(
            session_id="test-session-1",
            content="User is a Python developer interested in AI and machine learning.",
            timestamp="2026-05-16T10:00:00",
            atom_count=50,
        )

        store.save(persona, create_backup=False)

        # Read the file directly
        content = store.persona_path.read_text()

        # Verify it's readable Markdown
        assert content.startswith("---")
        assert "# User Profile" in content
        assert "Python developer" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
