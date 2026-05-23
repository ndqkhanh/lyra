"""Skill manager - Core skills system"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import yaml
import re


@dataclass
class SkillDefinition:
    """Skill definition from YAML frontmatter"""
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    model: str = "sonnet"
    tools: List[str] = field(default_factory=list)
    prompt: str = ""


class SkillManager:
    """Manages skill definitions and execution"""

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or Path.home() / ".lyra" / "skills"
        self.skills: Dict[str, SkillDefinition] = {}

    def load_skills(self):
        """Load skill definitions from directory"""
        if not self.skills_dir.exists():
            return

        for skill_file in self.skills_dir.glob("*.md"):
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    self.skills[skill.name] = skill
            except Exception as e:
                print(f"Warning: Failed to load skill {skill_file}: {e}")

    def _parse_skill_file(self, file_path: Path) -> Optional[SkillDefinition]:
        """Parse skill file with YAML frontmatter"""
        content = file_path.read_text()

        # Extract YAML frontmatter
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        if not match:
            return None

        frontmatter_text, prompt = match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError:
            return None

        # Create skill definition
        return SkillDefinition(
            name=frontmatter.get("name", file_path.stem),
            description=frontmatter.get("description", ""),
            triggers=frontmatter.get("triggers", []),
            tags=frontmatter.get("tags", []),
            model=frontmatter.get("model", "sonnet"),
            tools=frontmatter.get("tools", []),
            prompt=prompt.strip(),
        )

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """Get skill by name"""
        return self.skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        """List all skills"""
        return list(self.skills.values())

    def find_by_trigger(self, trigger: str) -> List[SkillDefinition]:
        """Find skills matching a trigger"""
        matching = []
        trigger_lower = trigger.lower()

        for skill in self.skills.values():
            if any(t.lower() in trigger_lower for t in skill.triggers):
                matching.append(skill)

        return matching

    def find_by_tag(self, tag: str) -> List[SkillDefinition]:
        """Find skills by tag"""
        matching = []
        tag_lower = tag.lower()

        for skill in self.skills.values():
            if any(t.lower() == tag_lower for t in skill.tags):
                matching.append(skill)

        return matching

    def register_skill(self, skill: SkillDefinition):
        """Register a skill programmatically"""
        self.skills[skill.name] = skill

    def invoke_skill(self, skill_name: str, context: dict = None) -> str:
        """Invoke a skill and return the prompt"""
        skill = self.get_skill(skill_name)
        if not skill:
            return f"Skill '{skill_name}' not found"

        # Build prompt with context
        prompt = f"""# Skill: {skill.name}

{skill.description}

## Instructions

{skill.prompt}
"""

        if context:
            prompt += "\n## Context\n\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"

        return prompt


# Global skill manager
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Get or create global skill manager"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
        _skill_manager.load_skills()
    return _skill_manager
