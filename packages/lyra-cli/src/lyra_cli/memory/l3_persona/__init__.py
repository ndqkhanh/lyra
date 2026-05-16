"""
L3 Persona Layer - User profile stored as single Markdown file.

Features:
- Single persona.md file (always loaded)
- Persona generation (every 50 atoms)
- Backup system (3 versions)
- Human-editable Markdown format
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import shutil

logger = logging.getLogger(__name__)


@dataclass
class UserPersona:
    """User profile/persona."""

    session_id: str = ""
    content: str = ""
    timestamp: str = ""
    metadata: Optional[Dict[str, Any]] = None
    atom_count: int = 0  # Number of atoms used to generate this persona

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPersona":
        """Create from dictionary."""
        return cls(**data)

    def to_markdown(self) -> str:
        """
        Convert to Markdown format.

        Format:
            ---
            session_id: test-session-1
            timestamp: 2026-05-16T10:00:00
            atom_count: 50
            ---
            # User Profile

            Persona content here...
        """
        # YAML frontmatter
        frontmatter = f"""---
session_id: {self.session_id}
timestamp: {self.timestamp}
atom_count: {self.atom_count}
---
"""

        # Markdown content
        markdown = f"{frontmatter}\n# User Profile\n\n{self.content}\n"

        return markdown

    @classmethod
    def from_markdown(cls, markdown: str) -> "UserPersona":
        """
        Parse from Markdown format.

        Args:
            markdown: Markdown string with YAML frontmatter

        Returns:
            UserPersona instance
        """
        # Split frontmatter and content
        parts = markdown.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid markdown format: missing frontmatter")

        frontmatter_str = parts[1].strip()
        content_str = parts[2].strip()

        # Parse frontmatter
        frontmatter = {}
        for line in frontmatter_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Convert atom_count to int
                if key == "atom_count":
                    try:
                        value = int(value)
                    except:
                        value = 0

                frontmatter[key] = value

        # Remove "# User Profile" heading if present
        content_lines = content_str.split("\n")
        if content_lines and content_lines[0].startswith("# "):
            content_lines = content_lines[1:]

        content = "\n".join(content_lines).strip()

        return cls(
            session_id=frontmatter.get("session_id", ""),
            content=content,
            timestamp=frontmatter.get("timestamp", ""),
            atom_count=frontmatter.get("atom_count", 0),
        )


class PersonaStore:
    """
    L3 storage layer using single Markdown file with backups.

    Directory structure:
        data/l3_persona/
            persona.md           ← Current profile
            persona.backup.1.md  ← Previous version
            persona.backup.2.md  ← Older version
            persona.backup.3.md  ← Oldest version
    """

    def __init__(
        self,
        data_dir: str = "./data/l3_persona",
        max_backups: int = 3,
        generation_threshold: int = 50,
    ):
        self.data_dir = Path(data_dir)
        self.max_backups = max_backups
        self.generation_threshold = generation_threshold
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.persona_path = self.data_dir / "persona.md"

        logger.info(
            f"Initialized L3 PersonaStore at {self.data_dir} "
            f"with {max_backups} backups, generation threshold {generation_threshold}"
        )

    def save(self, persona: UserPersona, create_backup: bool = True) -> None:
        """
        Save user persona to Markdown file.

        Args:
            persona: UserPersona to save
            create_backup: Whether to create backup of existing persona
        """
        try:
            # Create backup if requested and persona exists
            if create_backup and self.persona_path.exists():
                self._create_backup()

            # Save new persona
            markdown = persona.to_markdown()
            self.persona_path.write_text(markdown, encoding="utf-8")

            logger.info(
                f"Saved persona (atom_count={persona.atom_count}, "
                f"backup={create_backup})"
            )
        except Exception as e:
            logger.error(f"Failed to save persona: {e}")
            raise

    def load(self) -> Optional[UserPersona]:
        """
        Load user persona from Markdown file.

        Returns:
            UserPersona or None if not found
        """
        if not self.persona_path.exists():
            return None

        try:
            markdown = self.persona_path.read_text(encoding="utf-8")
            persona = UserPersona.from_markdown(markdown)

            logger.debug(f"Loaded persona (atom_count={persona.atom_count})")
            return persona
        except Exception as e:
            logger.error(f"Failed to load persona: {e}")
            return None

    def should_regenerate(self, current_atom_count: int) -> bool:
        """
        Check if persona should be regenerated based on atom count.

        Args:
            current_atom_count: Current number of L1 atoms

        Returns:
            True if regeneration is needed
        """
        persona = self.load()

        if persona is None:
            # No persona exists, should generate
            return True

        # Check if we've accumulated enough new atoms
        atoms_since_last = current_atom_count - persona.atom_count
        should_regen = atoms_since_last >= self.generation_threshold

        logger.debug(
            f"Regeneration check: current={current_atom_count}, "
            f"last={persona.atom_count}, delta={atoms_since_last}, "
            f"threshold={self.generation_threshold}, should_regen={should_regen}"
        )

        return should_regen

    def _create_backup(self) -> None:
        """Create backup of current persona."""
        if not self.persona_path.exists():
            return

        # Rotate existing backups
        for i in range(self.max_backups - 1, 0, -1):
            old_backup = self.data_dir / f"persona.backup.{i}.md"
            new_backup = self.data_dir / f"persona.backup.{i + 1}.md"

            if old_backup.exists():
                if new_backup.exists():
                    new_backup.unlink()
                old_backup.rename(new_backup)

        # Create new backup
        backup_path = self.data_dir / "persona.backup.1.md"
        shutil.copy2(self.persona_path, backup_path)

        logger.debug(f"Created persona backup")

    def list_backups(self) -> List[Path]:
        """
        List all backup files.

        Returns:
            List of backup file paths, sorted by version
        """
        backups = []
        for i in range(1, self.max_backups + 1):
            backup_path = self.data_dir / f"persona.backup.{i}.md"
            if backup_path.exists():
                backups.append(backup_path)

        return backups

    def restore_backup(self, backup_number: int) -> bool:
        """
        Restore a backup version.

        Args:
            backup_number: Backup version to restore (1-3)

        Returns:
            True if restored, False if backup not found
        """
        if backup_number < 1 or backup_number > self.max_backups:
            raise ValueError(
                f"Backup number must be between 1 and {self.max_backups}"
            )

        backup_path = self.data_dir / f"persona.backup.{backup_number}.md"

        if not backup_path.exists():
            return False

        try:
            # Restore backup (don't create backup of current to avoid overwriting)
            shutil.copy2(backup_path, self.persona_path)

            logger.info(f"Restored persona from backup {backup_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_number}: {e}")
            raise

    def delete(self) -> bool:
        """
        Delete current persona (keeps backups).

        Returns:
            True if deleted, False if not found
        """
        if not self.persona_path.exists():
            return False

        try:
            self.persona_path.unlink()
            logger.info("Deleted current persona")
            return True
        except Exception as e:
            logger.error(f"Failed to delete persona: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with stats
        """
        persona = self.load()
        backups = self.list_backups()

        total_size = 0
        if self.persona_path.exists():
            total_size += self.persona_path.stat().st_size
        for backup in backups:
            total_size += backup.stat().st_size

        return {
            "has_persona": persona is not None,
            "atom_count": persona.atom_count if persona else 0,
            "last_updated": persona.timestamp if persona else None,
            "backup_count": len(backups),
            "total_size_kb": round(total_size / 1024, 2),
            "generation_threshold": self.generation_threshold,
            "data_dir": str(self.data_dir),
        }
