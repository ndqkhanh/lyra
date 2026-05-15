"""Production skill installer for Lyra.

Downloads and installs production-ready skills from curated sources.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SkillInstaller:
    """Install production-ready skills for Lyra."""

    def __init__(self, skills_dir: Path | None = None):
        """Initialize skill installer.

        Args:
            skills_dir: Directory to install skills (default: ~/.lyra/skills)
        """
        if skills_dir is None:
            skills_dir = Path.home() / ".lyra" / "skills"
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def install_skill(
        self,
        name: str,
        source: str,
        skill_type: str = "github",
    ) -> bool:
        """Install a skill from source.

        Args:
            name: Skill name
            source: Source URL or path
            skill_type: Source type (github, local, url)

        Returns:
            True if installation successful
        """
        skill_path = self.skills_dir / name

        if skill_path.exists():
            logger.info(f"Skill {name} already installed at {skill_path}")
            return True

        try:
            if skill_type == "github":
                return self._install_from_github(name, source, skill_path)
            elif skill_type == "local":
                return self._install_from_local(name, source, skill_path)
            else:
                logger.error(f"Unsupported skill type: {skill_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to install skill {name}: {e}")
            return False

    def _install_from_github(
        self, name: str, repo: str, dest: Path
    ) -> bool:
        """Install skill from GitHub repository.

        Args:
            name: Skill name
            repo: GitHub repository (owner/repo or full URL)
            dest: Destination path

        Returns:
            True if successful
        """
        import subprocess

        # Handle both full URLs and owner/repo format
        if not repo.startswith("http"):
            repo = f"https://github.com/{repo}"

        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo, str(dest)],
                check=True,
                capture_output=True,
            )
            logger.info(f"Installed skill {name} from {repo}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr.decode()}")
            return False

    def _install_from_local(
        self, name: str, source: str, dest: Path
    ) -> bool:
        """Install skill from local directory.

        Args:
            name: Skill name
            source: Source directory path
            dest: Destination path

        Returns:
            True if successful
        """
        import shutil

        source_path = Path(source)
        if not source_path.exists():
            logger.error(f"Source path does not exist: {source}")
            return False

        try:
            shutil.copytree(source_path, dest)
            logger.info(f"Installed skill {name} from {source}")
            return True
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            return False

    def list_installed_skills(self) -> list[str]:
        """List all installed skills.

        Returns:
            List of skill names
        """
        if not self.skills_dir.exists():
            return []

        return [
            d.name
            for d in self.skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def get_skill_info(self, name: str) -> dict[str, Any] | None:
        """Get information about an installed skill.

        Args:
            name: Skill name

        Returns:
            Skill metadata or None if not found
        """
        skill_path = self.skills_dir / name
        if not skill_path.exists():
            return None

        # Look for SKILL.md or skill.json
        skill_md = skill_path / "SKILL.md"
        skill_json = skill_path / "skill.json"

        info: dict[str, Any] = {"name": name, "path": str(skill_path)}

        if skill_json.exists():
            try:
                with open(skill_json) as f:
                    info.update(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to read skill.json: {e}")

        if skill_md.exists():
            info["readme"] = skill_md.read_text()

        return info


# Production-ready skills catalog
PRODUCTION_SKILLS = {
    "token-optimizer": {
        "name": "Token Optimizer",
        "description": "65% token reduction through intelligent context management",
        "source": "https://github.com/example/caveman-skill",  # Placeholder
        "type": "github",
        "priority": "high",
    },
    "context-mode": {
        "name": "Context Mode",
        "description": "98% token reduction for long conversations",
        "source": "https://github.com/example/context-mode",  # Placeholder
        "type": "github",
        "priority": "high",
    },
    "research-agent": {
        "name": "Research Agent",
        "description": "Autonomous research with GPT Researcher",
        "source": "https://github.com/assafelovic/gpt-researcher",
        "type": "github",
        "priority": "medium",
    },
}


def install_production_skills(
    skills: list[str] | None = None,
    skills_dir: Path | None = None,
) -> dict[str, bool]:
    """Install production-ready skills.

    Args:
        skills: List of skill names to install (None = all)
        skills_dir: Installation directory

    Returns:
        Dict mapping skill names to installation success
    """
    installer = SkillInstaller(skills_dir)
    results = {}

    if skills is None:
        skills = list(PRODUCTION_SKILLS.keys())

    for skill_name in skills:
        if skill_name not in PRODUCTION_SKILLS:
            logger.warning(f"Unknown skill: {skill_name}")
            results[skill_name] = False
            continue

        skill_info = PRODUCTION_SKILLS[skill_name]
        success = installer.install_skill(
            skill_name,
            skill_info["source"],
            skill_info["type"],
        )
        results[skill_name] = success

    return results


__all__ = [
    "SkillInstaller",
    "PRODUCTION_SKILLS",
    "install_production_skills",
]
