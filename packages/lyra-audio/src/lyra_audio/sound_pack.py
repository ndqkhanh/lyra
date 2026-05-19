"""
Sound Pack - Sound pack loading and management.

Features:
- Sound pack manifest format
- Sound pack validation
- Sound pack loading
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SoundPackMetadata:
    """Sound pack metadata."""

    name: str
    version: str
    author: str
    description: str
    game: Optional[str] = None
    character: Optional[str] = None
    language: str = "en"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class SoundPack:
    """Sound pack definition."""

    name: str
    version: str
    author: str
    description: str
    sounds: Dict[str, str]
    metadata: SoundPackMetadata
    pack_dir: Path

    def get_sound_path(self, event: str) -> Optional[Path]:
        """
        Get sound file path for event.

        Args:
            event: Event name

        Returns:
            Path to sound file or None
        """
        if event not in self.sounds:
            return None

        sound_file = self.pack_dir / self.sounds[event]
        if sound_file.exists():
            return sound_file

        return None

    def list_events(self) -> List[str]:
        """List all events in this pack."""
        return list(self.sounds.keys())


class SoundPackLoader:
    """
    Sound pack loader.

    Features:
    - Load sound packs from directories
    - Validate sound pack manifests
    - List available sound packs
    """

    def __init__(self, sounds_dir: Optional[str] = None):
        """Initialize sound pack loader."""
        if sounds_dir:
            self.sounds_dir = Path(sounds_dir).expanduser()
        else:
            self.sounds_dir = Path("~/.lyra/sounds").expanduser()

        self.sounds_dir.mkdir(parents=True, exist_ok=True)

    def load_pack(self, pack_name: str) -> Optional[SoundPack]:
        """
        Load sound pack.

        Args:
            pack_name: Pack name

        Returns:
            SoundPack or None if not found
        """
        pack_dir = self.sounds_dir / pack_name
        manifest_path = pack_dir / "manifest.json"

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            return self._parse_manifest(manifest, pack_dir)
        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def _parse_manifest(self, manifest: Dict[str, Any], pack_dir: Path) -> SoundPack:
        """Parse manifest into SoundPack."""
        metadata = SoundPackMetadata(
            name=manifest["name"],
            version=manifest["version"],
            author=manifest["author"],
            description=manifest["description"],
            game=manifest.get("metadata", {}).get("game"),
            character=manifest.get("metadata", {}).get("character"),
            language=manifest.get("metadata", {}).get("language", "en"),
            tags=manifest.get("metadata", {}).get("tags", []),
        )

        return SoundPack(
            name=manifest["name"],
            version=manifest["version"],
            author=manifest["author"],
            description=manifest["description"],
            sounds=manifest["sounds"],
            metadata=metadata,
            pack_dir=pack_dir,
        )

    def list_packs(self) -> List[str]:
        """List available sound packs."""
        if not self.sounds_dir.exists():
            return []

        packs = []
        for item in self.sounds_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                packs.append(item.name)

        return sorted(packs)

    def validate_pack(self, pack_name: str) -> tuple[bool, List[str]]:
        """
        Validate sound pack.

        Args:
            pack_name: Pack name

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        pack_dir = self.sounds_dir / pack_name
        if not pack_dir.exists():
            errors.append(f"Pack directory not found: {pack_dir}")
            return False, errors

        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.exists():
            errors.append("manifest.json not found")
            return False, errors

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            # Check required fields
            required_fields = ["name", "version", "author", "description", "sounds"]
            for field in required_fields:
                if field not in manifest:
                    errors.append(f"Missing required field: {field}")

            # Check sound files exist
            if "sounds" in manifest:
                for event, sound_file in manifest["sounds"].items():
                    sound_path = pack_dir / sound_file
                    if not sound_path.exists():
                        errors.append(f"Sound file not found: {sound_file}")

        except json.JSONDecodeError:
            errors.append("Invalid JSON in manifest.json")
        except IOError:
            errors.append("Could not read manifest.json")

        return len(errors) == 0, errors

    def create_pack_template(self, pack_name: str) -> Path:
        """
        Create sound pack template.

        Args:
            pack_name: Pack name

        Returns:
            Path to created pack directory
        """
        pack_dir = self.sounds_dir / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest template
        manifest = {
            "name": pack_name,
            "version": "1.0.0",
            "author": "Your Name",
            "description": "Description of your sound pack",
            "sounds": {
                "session_start": "session_start.mp3",
                "task_complete": "task_complete.mp3",
                "error_general": "error_general.mp3",
            },
            "metadata": {
                "game": "Game Name",
                "character": "Character Name",
                "language": "en",
                "tags": ["custom"],
            },
        }

        manifest_path = pack_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return pack_dir
