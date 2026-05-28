"""Rule registry for loading and managing rules."""
import re
from pathlib import Path

import yaml

from .rule_metadata import RuleCategory, RuleMetadata, RuleSeverity


class RuleRegistry:
    """Registry for loading and managing rules."""

    def __init__(self, rule_dirs: list[Path] | None = None):
        self.rule_dirs = rule_dirs or []
        self._rules: dict[str, RuleMetadata] = {}

    def _camel_to_kebab(self, name: str) -> str:
        """Convert camelCase to kebab-case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

    def load_rules(self) -> dict[str, RuleMetadata]:
        """Load all rules from configured directories."""
        self._rules.clear()

        for rule_dir in self.rule_dirs:
            if not rule_dir.exists():
                continue

            for rule_file in rule_dir.glob("*.md"):
                try:
                    metadata = self._parse_rule_file(rule_file)
                    if metadata:
                        self._rules[metadata.name] = metadata
                except Exception as e:
                    print(f"Error loading rule {rule_file}: {e}")

        return self._rules

    def _parse_rule_file(self, file_path: Path) -> RuleMetadata | None:
        """Parse rule file with YAML frontmatter."""
        content = file_path.read_text()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
            category_str = frontmatter.get("category", "")
            severity_str = frontmatter.get("severity", "medium")

            category = RuleCategory(self._camel_to_kebab(category_str))
            severity = RuleSeverity(severity_str.lower())

            return RuleMetadata(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                category=category,
                severity=severity,
                enabled=frontmatter.get("enabled", True),
                file_path=str(file_path)
            )
        except (yaml.YAMLError, ValueError):
            return None

    def get_rule(self, name: str) -> RuleMetadata | None:
        """Get rule by name."""
        return self._rules.get(name)

    def get_rules_by_category(self, category: RuleCategory) -> list[RuleMetadata]:
        """Get all rules of a specific category."""
        return [
            rule for rule in self._rules.values()
            if rule.category == category and rule.enabled
        ]

    def search_rules(self, query: str) -> list[RuleMetadata]:
        """Search rules by name or description."""
        query_lower = query.lower()
        return [
            rule for rule in self._rules.values()
            if query_lower in rule.name.lower() or query_lower in rule.description.lower()
        ]

    def list_rules(self) -> list[RuleMetadata]:
        """List all loaded rules."""
        return list(self._rules.values())
