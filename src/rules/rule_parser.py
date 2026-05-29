"""
Rule parser for loading rules from markdown files.
"""

import re
from pathlib import Path

import yaml

from .rule import Rule, RuleCategory, RuleSeverity


class RuleParser:
    """
    Parser for rule definition files.

    Parses markdown files with YAML frontmatter containing rule definitions.
    """

    # Pattern to match YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$",
        re.DOTALL
    )

    def parse_file(self, path: Path) -> Rule | None:
        """
        Parse a rule definition file.

        Args:
            path: Path to rule file

        Returns:
            Parsed rule or None if parsing fails
        """
        try:
            with open(path) as f:
                content = f.read()

            return self.parse_string(content, source_file=str(path))

        except Exception as e:
            print(f"Error parsing {path}: {e}")
            return None

    def parse_string(
        self,
        content: str,
        source_file: str | None = None,
    ) -> Rule | None:
        """
        Parse a rule from string content.

        Args:
            content: Rule content
            source_file: Optional source file path

        Returns:
            Parsed rule or None if parsing fails
        """
        try:
            # Try to extract frontmatter
            match = self.FRONTMATTER_PATTERN.match(content)

            if match:
                frontmatter_str = match.group(1)
                description = match.group(2).strip()
                frontmatter = yaml.safe_load(frontmatter_str)
            else:
                # No frontmatter, treat entire content as description
                frontmatter = {}
                description = content.strip()

            # Extract required fields
            rule_id = frontmatter.get("rule_id") or frontmatter.get("id")
            if not rule_id and source_file:
                # Generate ID from filename
                rule_id = Path(source_file).stem

            if not rule_id:
                return None

            # Extract category
            category_str = frontmatter.get("category", "coding-style")
            try:
                category = RuleCategory(category_str)
            except ValueError:
                category = RuleCategory.CODING_STYLE

            # Extract severity
            severity_str = frontmatter.get("severity", "warning")
            try:
                severity = RuleSeverity(severity_str)
            except ValueError:
                severity = RuleSeverity.WARNING

            # Create rule
            rule = Rule(
                rule_id=rule_id,
                category=category,
                title=frontmatter.get("title", rule_id),
                description=description,
                severity=severity,
                language=frontmatter.get("language"),
                file_patterns=frontmatter.get("file_patterns", []),
                enabled=frontmatter.get("enabled", True),
                priority=frontmatter.get("priority", 0),
                examples=frontmatter.get("examples", {}),
                references=frontmatter.get("references", []),
                metadata=frontmatter.get("metadata", {}),
            )

            return rule

        except Exception as e:
            print(f"Error parsing rule content: {e}")
            return None

    def parse_directory(
        self,
        directory: Path,
        recursive: bool = True,
    ) -> dict[str, Rule]:
        """
        Parse all rule files in a directory.

        Args:
            directory: Directory containing rule files
            recursive: Whether to search recursively

        Returns:
            Dictionary mapping rule IDs to rules
        """
        rules = {}

        pattern = "**/*.md" if recursive else "*.md"
        for path in directory.glob(pattern):
            rule = self.parse_file(path)
            if rule:
                rules[rule.rule_id] = rule

        return rules
