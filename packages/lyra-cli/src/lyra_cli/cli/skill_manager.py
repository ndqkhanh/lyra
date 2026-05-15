"""Skill Manager for Lyra.

Manages installation and usage of skills.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class SkillManager:
    """Manages Lyra skills."""

    def __init__(self):
        self.skills_dir = Path("~/.lyra/skills").expanduser()
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills = {}
        self._load_skills()

    def _load_skills(self):
        """Load installed skills."""
        index_file = self.skills_dir / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                self.skills = json.load(f)

    def _save_skills(self):
        """Save skills index."""
        with open(self.skills_dir / "index.json", "w") as f:
            json.dump(self.skills, f, indent=2)

    def install_skill(self, source: str, name: Optional[str] = None) -> str:
        """Install a skill from git or local path."""
        if source.startswith("http"):
            # Git repository
            skill_name = name or source.split("/")[-1].replace(".git", "")
            # Clone skill (simplified)
            self.skills[skill_name] = {
                "source": source,
                "type": "git",
                "installed": True,
            }
        else:
            # Local path
            skill_name = name or Path(source).name
            self.skills[skill_name] = {
                "source": source,
                "type": "local",
                "installed": True,
            }

        self._save_skills()
        return skill_name

    def list_skills(self) -> list[dict]:
        """List installed skills."""
        return [
            {"name": name, **info}
            for name, info in self.skills.items()
        ]

    def get_skill(self, name: str) -> Optional[dict]:
        """Get skill by name."""
        return self.skills.get(name)

    def remove_skill(self, name: str) -> bool:
        """Remove a skill."""
        if name in self.skills:
            del self.skills[name]
            self._save_skills()
            return True
        return False
