"""
Importer for ECC skills into Lyra skill system.
"""

from dataclasses import dataclass
from pathlib import Path

from .parser import SkillParser
from .registry import SkillRegistry
from .skill import Skill


@dataclass
class ImportResult:
    """Result of skill import operation."""

    total_files: int
    parsed_successfully: int
    registered_successfully: int
    failed: list[str]
    skills: dict[str, Skill]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_files == 0:
            return 0.0
        return self.registered_successfully / self.total_files


class ECCSkillImporter:
    """
    Import ECC skills into Lyra skill system.

    Handles parsing ECC skill files and registering them
    in the Lyra skill registry.
    """

    def __init__(self, registry: SkillRegistry):
        """
        Initialize importer.

        Args:
            registry: Skill registry to import into
        """
        self.registry = registry
        self.parser = SkillParser()

    def import_file(self, path: Path) -> bool:
        """
        Import a single skill file.

        Args:
            path: Path to skill file

        Returns:
            True if imported successfully
        """
        skill = self.parser.parse_file(path)
        if skill:
            self.registry.register(skill)
            return True
        return False

    def import_directory(
        self,
        directory: Path,
        recursive: bool = True,
    ) -> ImportResult:
        """
        Import all skills from a directory.

        Args:
            directory: Directory containing skill files
            recursive: If True, search subdirectories

        Returns:
            Import result with statistics
        """
        pattern = "**/*.md" if recursive else "*.md"
        skill_files = list(directory.glob(pattern))

        total_files = len(skill_files)
        parsed_successfully = 0
        registered_successfully = 0
        failed = []
        skills = {}

        for path in skill_files:
            try:
                skill = self.parser.parse_file(path)
                if skill:
                    parsed_successfully += 1
                    self.registry.register(skill)
                    registered_successfully += 1
                    skills[skill.name] = skill
                else:
                    failed.append(str(path))
            except Exception as e:
                failed.append(f"{path}: {e}")

        return ImportResult(
            total_files=total_files,
            parsed_successfully=parsed_successfully,
            registered_successfully=registered_successfully,
            failed=failed,
            skills=skills,
        )

    def import_all(self, ecc_skills_path: Path) -> ImportResult:
        """
        Import all ECC skills from the standard directory structure.

        Expected structure:
        ecc_skills_path/
        ├── coding-standards/
        ├── backend-patterns/
        ├── frontend-patterns/
        └── ...

        Args:
            ecc_skills_path: Root path to ECC skills

        Returns:
            Import result with statistics
        """
        return self.import_directory(ecc_skills_path, recursive=True)
