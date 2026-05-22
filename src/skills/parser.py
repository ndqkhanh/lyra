"""
Parser for ECC skill files (Markdown with YAML frontmatter).
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from .skill import Skill, SkillCategory


class SkillParser:
    """
    Parser for skill files in Markdown format with YAML frontmatter.

    Expected format:
    ---
    name: skill-name
    description: Skill description
    category: coding-standards
    trigger_patterns: [pattern1, pattern2]
    tags: [tag1, tag2]
    language: python
    ---

    # Skill Content
    Markdown content here...
    """

    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$",
        re.DOTALL
    )

    def parse_file(self, path: Path) -> Optional[Skill]:
        """
        Parse a skill file.

        Args:
            path: Path to skill file

        Returns:
            Parsed Skill or None if parsing fails
        """
        try:
            content = path.read_text(encoding="utf-8")
            return self.parse_string(content, source_path=path)
        except Exception as e:
            print(f"Error parsing {path}: {e}")
            return None

    def parse_string(self, content: str, source_path: Optional[Path] = None) -> Optional[Skill]:
        """
        Parse skill from string content.

        Args:
            content: Skill file content
            source_path: Optional source file path

        Returns:
            Parsed Skill or None if parsing fails
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return None

        frontmatter_str, markdown_content = match.groups()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML frontmatter: {e}")
            return None

        # Extract required fields
        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not name or not description:
            print(f"Missing required fields: name={name}, description={description}")
            return None

        # Extract optional fields
        category_str = frontmatter.get("category", "general")
        try:
            category = SkillCategory(category_str)
        except ValueError:
            category = SkillCategory.GENERAL

        trigger_patterns = frontmatter.get("trigger_patterns", [])
        if isinstance(trigger_patterns, str):
            trigger_patterns = [trigger_patterns]

        tags = frontmatter.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        language = frontmatter.get("language")
        framework = frontmatter.get("framework")
        version = frontmatter.get("version", "1.0.0")
        source = frontmatter.get("source", "ecc")

        # Store source path in metadata
        metadata = frontmatter.get("metadata", {})
        if source_path:
            metadata["source_path"] = str(source_path)

        return Skill(
            name=name,
            description=description,
            content=markdown_content.strip(),
            category=category,
            trigger_patterns=trigger_patterns,
            tags=tags,
            language=language,
            framework=framework,
            version=version,
            source=source,
            metadata=metadata,
        )

    def parse_directory(self, directory: Path, recursive: bool = True) -> Dict[str, Skill]:
        """
        Parse all skill files in a directory.

        Args:
            directory: Directory containing skill files
            recursive: If True, search subdirectories

        Returns:
            Dictionary mapping skill names to Skill objects
        """
        skills = {}
        pattern = "**/*.md" if recursive else "*.md"

        for path in directory.glob(pattern):
            skill = self.parse_file(path)
            if skill:
                skills[skill.name] = skill

        return skills
