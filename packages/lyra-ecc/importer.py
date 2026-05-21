"""
ECC Importer

Imports ECC skills, agents, rules, and hooks into Lyra.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportResult:
    """Result of an import operation."""
    success: bool
    items_imported: int
    items_failed: int
    errors: List[str]


@dataclass(frozen=True)
class ECCSkill:
    """ECC skill representation."""
    name: str
    description: str
    trigger_patterns: List[str]
    implementation: str
    source_path: Path


@dataclass(frozen=True)
class ECCAgent:
    """ECC agent representation."""
    name: str
    description: str
    model: str
    tools: List[str]
    source_path: Path


class ECCImporter:
    """Imports ECC components into Lyra."""

    def __init__(self, ecc_path: Optional[Path] = None):
        """
        Initialize ECC importer.

        Args:
            ecc_path: Path to ECC installation
        """
        self.ecc_path = ecc_path or Path.home() / ".claude"
        self.skills_path = self.ecc_path / "skills"
        self.agents_path = self.ecc_path / "agents"
        self.rules_path = self.ecc_path / "rules"

    def import_skills(self) -> ImportResult:
        """
        Import ECC skills.

        Returns:
            ImportResult with import statistics
        """
        if not self.skills_path.exists():
            logger.warning(f"Skills path not found: {self.skills_path}")
            return ImportResult(
                success=False,
                items_imported=0,
                items_failed=0,
                errors=[f"Skills path not found: {self.skills_path}"]
            )

        skills: List[ECCSkill] = []
        errors: List[str] = []

        for skill_file in self.skills_path.glob("**/*.md"):
            try:
                skill = self._parse_skill_file(skill_file)
                skills.append(skill)
            except Exception as e:
                error_msg = f"Failed to parse {skill_file}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Imported {len(skills)} skills from ECC")
        return ImportResult(
            success=len(errors) == 0,
            items_imported=len(skills),
            items_failed=len(errors),
            errors=errors
        )

    def import_agents(self) -> ImportResult:
        """
        Import ECC agents.

        Returns:
            ImportResult with import statistics
        """
        if not self.agents_path.exists():
            logger.warning(f"Agents path not found: {self.agents_path}")
            return ImportResult(
                success=False,
                items_imported=0,
                items_failed=0,
                errors=[f"Agents path not found: {self.agents_path}"]
            )

        agents: List[ECCAgent] = []
        errors: List[str] = []

        for agent_file in self.agents_path.glob("*.md"):
            try:
                agent = self._parse_agent_file(agent_file)
                agents.append(agent)
            except Exception as e:
                error_msg = f"Failed to parse {agent_file}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Imported {len(agents)} agents from ECC")
        return ImportResult(
            success=len(errors) == 0,
            items_imported=len(agents),
            items_failed=len(errors),
            errors=errors
        )

    def _parse_skill_file(self, skill_file: Path) -> ECCSkill:
        """Parse ECC skill file."""
        content = skill_file.read_text()

        # Extract frontmatter
        lines = content.split('\n')
        name = skill_file.stem
        description = ""
        trigger_patterns: List[str] = []

        # Simple parsing (would be more sophisticated in production)
        for line in lines:
            if line.startswith('# '):
                description = line[2:].strip()
            elif 'trigger' in line.lower():
                trigger_patterns.append(line.strip())

        return ECCSkill(
            name=name,
            description=description or name,
            trigger_patterns=trigger_patterns,
            implementation=content,
            source_path=skill_file
        )

    def _parse_agent_file(self, agent_file: Path) -> ECCAgent:
        """Parse ECC agent file."""
        content = agent_file.read_text()

        lines = content.split('\n')
        name = agent_file.stem
        description = ""
        model = "claude-sonnet-4.6"
        tools: List[str] = []

        for line in lines:
            if line.startswith('# '):
                description = line[2:].strip()
            elif 'model:' in line.lower():
                model = line.split(':')[1].strip()
            elif 'tools:' in line.lower():
                tools.append(line.strip())

        return ECCAgent(
            name=name,
            description=description or name,
            model=model,
            tools=tools,
            source_path=agent_file
        )

    def get_import_summary(self) -> Dict[str, Any]:
        """
        Get summary of what can be imported.

        Returns:
            Dictionary with import summary
        """
        summary = {
            "skills_available": len(list(self.skills_path.glob("**/*.md"))) if self.skills_path.exists() else 0,
            "agents_available": len(list(self.agents_path.glob("*.md"))) if self.agents_path.exists() else 0,
            "rules_available": len(list(self.rules_path.glob("**/*.md"))) if self.rules_path.exists() else 0,
        }
        return summary
