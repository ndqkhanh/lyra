"""Skill registry for loading and managing skills."""
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .skill_metadata import SkillMetadata


class SkillRegistry:
    """Registry for loading and managing skills."""

    def __init__(self, skill_dirs: Optional[List[Path]] = None):
        self.skill_dirs = skill_dirs or []
        self._skills: Dict[str, SkillMetadata] = {}

    def load_skills(self) -> Dict[str, SkillMetadata]:
        """Load all skills from configured directories."""
        self._skills.clear()

        for skill_dir in self.skill_dirs:
            if not skill_dir.exists():
                continue

            # Look for SKILL.md files in subdirectories
            for skill_path in skill_dir.glob("*/SKILL.md"):
                try:
                    metadata = self._parse_skill_file(skill_path)
                    if metadata:
                        self._skills[metadata.name] = metadata
                except Exception as e:
                    print(f"Error loading skill {skill_path}: {e}")

        return self._skills

    def _parse_skill_file(self, file_path: Path) -> Optional[SkillMetadata]:
        """Parse skill file with YAML frontmatter."""
        content = file_path.read_text()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
            return SkillMetadata(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                origin=frontmatter.get("origin", "ECC"),
                tags=frontmatter.get("tags", []),
                triggers=frontmatter.get("triggers", []),
                codemap=frontmatter.get("codemap"),
                file_path=str(file_path)
            )
        except yaml.YAMLError:
            return None

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Get skill by name."""
        return self._skills.get(name)

    def search_skills(self, query: str) -> List[SkillMetadata]:
        """Search skills by name, description, or tags."""
        query_lower = query.lower()
        return [
            skill for skill in self._skills.values()
            if query_lower in skill.name.lower()
            or query_lower in skill.description.lower()
            or any(query_lower in tag.lower() for tag in skill.tags)
        ]

    def get_by_trigger(self, keyword: str) -> List[SkillMetadata]:
        """Get skills by trigger keyword."""
        keyword_lower = keyword.lower()
        return [
            skill for skill in self._skills.values()
            if any(keyword_lower in trigger.lower() for trigger in skill.triggers)
        ]

    def list_skills(self) -> List[SkillMetadata]:
        """List all loaded skills."""
        return list(self._skills.values())
