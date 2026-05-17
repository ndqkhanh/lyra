"""Skill loader for loading skill content and generating codemaps."""
from pathlib import Path
from typing import Optional

from .skill_metadata import SkillMetadata


class SkillLoader:
    """Loader for skill content and codemaps."""

    def load_skill_content(self, skill: SkillMetadata) -> str:
        """Load the full content of a skill."""
        if not skill.file_path:
            return ""

        file_path = Path(skill.file_path)
        if not file_path.exists():
            return ""

        return file_path.read_text()

    def generate_codemap(self, skill_name: str, skill_dir: Path) -> Optional[str]:
        """Generate a codemap for a skill directory."""
        # TODO: Implement codemap generation
        # For now, return None
        return None
