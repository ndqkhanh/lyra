"""
L2 Scenario Layer - Scene blocks stored as Markdown files.

Features:
- Human-readable Markdown storage
- Scene aggregation (15-scene limit)
- Scene navigation API
- Retention policy
- Version control friendly
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


@dataclass
class ScenarioBlock:
    """Single scenario/scene aggregated from L1 atoms."""

    id: Optional[str] = None
    session_id: str = ""
    title: str = ""
    content: str = ""
    timestamp: str = ""
    metadata: Optional[Dict[str, Any]] = None
    source_atom_ids: Optional[List[int]] = None  # Traceability to L1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioBlock":
        """Create from dictionary."""
        return cls(**data)

    def to_markdown(self) -> str:
        """
        Convert to Markdown format.

        Format:
            ---
            id: scene_001
            session_id: test-session-1
            timestamp: 2026-05-16T10:00:00
            source_atom_ids: [1, 2, 3]
            ---
            # Scene Title

            Scene content here...
        """
        # YAML frontmatter
        frontmatter = f"""---
id: {self.id}
session_id: {self.session_id}
timestamp: {self.timestamp}
source_atom_ids: {json.dumps(self.source_atom_ids) if self.source_atom_ids else '[]'}
---
"""

        # Markdown content
        markdown = f"{frontmatter}\n# {self.title}\n\n{self.content}\n"

        return markdown

    @classmethod
    def from_markdown(cls, markdown: str) -> "ScenarioBlock":
        """
        Parse from Markdown format.

        Args:
            markdown: Markdown string with YAML frontmatter

        Returns:
            ScenarioBlock instance
        """
        # Split frontmatter and content
        parts = markdown.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid markdown format: missing frontmatter")

        frontmatter_str = parts[1].strip()
        content_str = parts[2].strip()

        # Parse frontmatter (simple key: value parsing)
        frontmatter = {}
        for line in frontmatter_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Parse JSON arrays
                if value.startswith("["):
                    try:
                        value = json.loads(value)
                    except:
                        pass

                frontmatter[key] = value

        # Extract title from first heading
        title = ""
        content_lines = content_str.split("\n")
        for i, line in enumerate(content_lines):
            if line.startswith("# "):
                title = line[2:].strip()
                # Remove title line from content
                content_lines = content_lines[i + 1 :]
                break

        content = "\n".join(content_lines).strip()

        return cls(
            id=frontmatter.get("id"),
            session_id=frontmatter.get("session_id", ""),
            title=title,
            content=content,
            timestamp=frontmatter.get("timestamp", ""),
            source_atom_ids=frontmatter.get("source_atom_ids"),
        )


class ScenarioStore:
    """
    L2 storage layer using Markdown files.

    Directory structure:
        data/l2_scenarios/
            scene_001_authentication.md
            scene_002_database_design.md
            ...
    """

    def __init__(
        self,
        data_dir: str = "./data/l2_scenarios",
        max_scenes: int = 15,
    ):
        self.data_dir = Path(data_dir)
        self.max_scenes = max_scenes
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Initialized L2 ScenarioStore at {self.data_dir} "
            f"with max {max_scenes} scenes"
        )

    def _get_scene_path(self, scene_id: str) -> Path:
        """Get path for a scene file."""
        # Sanitize scene_id for filename
        safe_id = scene_id.replace("/", "_").replace("\\", "_")
        return self.data_dir / f"{safe_id}.md"

    def save(self, scene: ScenarioBlock) -> None:
        """
        Save a scenario block to Markdown file.

        Args:
            scene: ScenarioBlock to save
        """
        if not scene.id:
            raise ValueError("Scene must have an ID")

        scene_path = self._get_scene_path(scene.id)

        try:
            markdown = scene.to_markdown()
            scene_path.write_text(markdown, encoding="utf-8")

            logger.debug(f"Saved scene {scene.id} to {scene_path.name}")
        except Exception as e:
            logger.error(f"Failed to save scene {scene.id}: {e}")
            raise

    def load(self, scene_id: str) -> Optional[ScenarioBlock]:
        """
        Load a scenario block from Markdown file.

        Args:
            scene_id: Scene identifier

        Returns:
            ScenarioBlock or None if not found
        """
        scene_path = self._get_scene_path(scene_id)

        if not scene_path.exists():
            return None

        try:
            markdown = scene_path.read_text(encoding="utf-8")
            scene = ScenarioBlock.from_markdown(markdown)

            logger.debug(f"Loaded scene {scene_id} from {scene_path.name}")
            return scene
        except Exception as e:
            logger.error(f"Failed to load scene {scene_id}: {e}")
            return None

    def list_scenes(
        self, session_id: Optional[str] = None
    ) -> List[ScenarioBlock]:
        """
        List all scenes, optionally filtered by session.

        Args:
            session_id: Optional session filter

        Returns:
            List of ScenarioBlock entries, sorted by timestamp descending
        """
        scenes = []

        for scene_path in self.data_dir.glob("*.md"):
            try:
                markdown = scene_path.read_text(encoding="utf-8")
                scene = ScenarioBlock.from_markdown(markdown)

                # Filter by session if specified
                if session_id and scene.session_id != session_id:
                    continue

                scenes.append(scene)
            except Exception as e:
                logger.warning(f"Failed to load scene {scene_path.name}: {e}")

        # Sort by timestamp descending (most recent first)
        scenes.sort(key=lambda s: s.timestamp, reverse=True)

        logger.info(
            f"Listed {len(scenes)} scenes"
            + (f" for session {session_id}" if session_id else "")
        )
        return scenes

    def delete(self, scene_id: str) -> bool:
        """
        Delete a scene.

        Args:
            scene_id: Scene identifier

        Returns:
            True if deleted, False if not found
        """
        scene_path = self._get_scene_path(scene_id)

        if not scene_path.exists():
            return False

        try:
            scene_path.unlink()
            logger.info(f"Deleted scene {scene_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete scene {scene_id}: {e}")
            raise

    def enforce_max_scenes(self, session_id: Optional[str] = None) -> int:
        """
        Enforce maximum scene limit by deleting oldest scenes.

        Args:
            session_id: Optional session filter

        Returns:
            Number of scenes deleted
        """
        scenes = self.list_scenes(session_id)

        if len(scenes) <= self.max_scenes:
            return 0

        # Delete oldest scenes (already sorted by timestamp descending)
        scenes_to_delete = scenes[self.max_scenes :]
        deleted_count = 0

        for scene in scenes_to_delete:
            if scene.id and self.delete(scene.id):
                deleted_count += 1

        logger.info(
            f"Enforced max scenes limit: deleted {deleted_count} old scenes"
        )
        return deleted_count

    def count(self, session_id: Optional[str] = None) -> int:
        """
        Count total scenes, optionally filtered by session.

        Args:
            session_id: Optional session filter

        Returns:
            Count of scenes
        """
        return len(self.list_scenes(session_id))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with stats
        """
        all_scenes = self.list_scenes()
        total_size = sum(
            self._get_scene_path(s.id).stat().st_size
            for s in all_scenes
            if s.id
        )

        # Get unique sessions
        sessions = set(s.session_id for s in all_scenes)

        return {
            "total_scenes": len(all_scenes),
            "total_size_kb": round(total_size / 1024, 2),
            "unique_sessions": len(sessions),
            "max_scenes": self.max_scenes,
            "data_dir": str(self.data_dir),
        }
