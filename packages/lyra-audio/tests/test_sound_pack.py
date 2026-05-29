"""Tests for sound pack functionality."""

import json
import tempfile
from pathlib import Path

from lyra_audio.sound_pack import SoundPack, SoundPackLoader, SoundPackMetadata

# Sound Pack Tests


def test_sound_pack_metadata():
    """Test sound pack metadata."""
    metadata = SoundPackMetadata(
        name="Test Pack",
        version="1.0.0",
        author="Test Author",
        description="Test description",
        game="Test Game",
        character="Test Character",
        tags=["test", "pack"],
    )

    assert metadata.name == "Test Pack"
    assert metadata.version == "1.0.0"
    assert "test" in metadata.tags


def test_sound_pack_get_sound_path():
    """Test getting sound path from pack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pack_dir = Path(tmpdir)
        sound_file = pack_dir / "test.mp3"
        sound_file.touch()

        metadata = SoundPackMetadata(
            name="Test", version="1.0.0", author="Test", description="Test"
        )

        pack = SoundPack(
            name="Test",
            version="1.0.0",
            author="Test",
            description="Test",
            sounds={"test_event": "test.mp3"},
            metadata=metadata,
            pack_dir=pack_dir,
        )

        path = pack.get_sound_path("test_event")
        assert path == sound_file


def test_sound_pack_list_events():
    """Test listing events in pack."""
    metadata = SoundPackMetadata(
        name="Test", version="1.0.0", author="Test", description="Test"
    )

    pack = SoundPack(
        name="Test",
        version="1.0.0",
        author="Test",
        description="Test",
        sounds={"event1": "sound1.mp3", "event2": "sound2.mp3"},
        metadata=metadata,
        pack_dir=Path("/tmp"),
    )

    events = pack.list_events()
    assert "event1" in events
    assert "event2" in events


# Sound Pack Loader Tests


def test_sound_pack_loader_init():
    """Test sound pack loader initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SoundPackLoader(sounds_dir=tmpdir)
        assert loader.sounds_dir == Path(tmpdir)


def test_sound_pack_loader_create_template():
    """Test creating pack template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SoundPackLoader(sounds_dir=tmpdir)

        pack_dir = loader.create_pack_template("test_pack")

        assert pack_dir.exists()
        assert (pack_dir / "manifest.json").exists()


def test_sound_pack_loader_load_pack():
    """Test loading sound pack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SoundPackLoader(sounds_dir=tmpdir)

        # Create test pack
        pack_dir = Path(tmpdir) / "test_pack"
        pack_dir.mkdir()

        manifest = {
            "name": "Test Pack",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test pack",
            "sounds": {"test_event": "test.mp3"},
            "metadata": {"game": "Test", "tags": ["test"]},
        }

        with open(pack_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        pack = loader.load_pack("test_pack")

        assert pack is not None
        assert pack.name == "Test Pack"
        assert pack.version == "1.0.0"


def test_sound_pack_loader_list_packs():
    """Test listing sound packs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SoundPackLoader(sounds_dir=tmpdir)

        # Create test packs
        for pack_name in ["pack1", "pack2"]:
            pack_dir = Path(tmpdir) / pack_name
            pack_dir.mkdir()
            manifest = {
                "name": pack_name,
                "version": "1.0.0",
                "author": "Test",
                "description": "Test",
                "sounds": {},
            }
            with open(pack_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)

        packs = loader.list_packs()
        assert "pack1" in packs
        assert "pack2" in packs


def test_sound_pack_loader_validate_pack():
    """Test validating sound pack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SoundPackLoader(sounds_dir=tmpdir)

        # Create valid pack
        pack_dir = Path(tmpdir) / "valid_pack"
        pack_dir.mkdir()

        manifest = {
            "name": "Valid Pack",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "sounds": {"test": "test.mp3"},
        }

        with open(pack_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Create sound file
        (pack_dir / "test.mp3").touch()

        is_valid, errors = loader.validate_pack("valid_pack")
        assert is_valid is True
        assert len(errors) == 0


def test_sound_pack_loader_validate_invalid_pack():
    """Test validating invalid pack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SoundPackLoader(sounds_dir=tmpdir)

        # Create invalid pack (missing sound file)
        pack_dir = Path(tmpdir) / "invalid_pack"
        pack_dir.mkdir()

        manifest = {
            "name": "Invalid Pack",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test",
            "sounds": {"test": "missing.mp3"},
        }

        with open(pack_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        is_valid, errors = loader.validate_pack("invalid_pack")
        assert is_valid is False
        assert len(errors) > 0
