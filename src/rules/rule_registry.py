"""
Rule registry for managing rules.
"""

from typing import Any, Dict, List, Optional

from .rule import Rule, RuleCategory, RuleSeverity


class RuleRegistry:
    """
    Registry for managing rules.

    Stores and retrieves rules by category, language, and priority.
    """

    def __init__(self):
        """Initialize rule registry."""
        self.rules: Dict[str, Rule] = {}
        self._rules_by_category: Dict[RuleCategory, List[Rule]] = {
            category: [] for category in RuleCategory
        }
        self._rules_by_language: Dict[str, List[Rule]] = {}

    def register(self, rule: Rule) -> None:
        """
        Register a rule.

        Args:
            rule: Rule to register
        """
        if rule.rule_id in self.rules:
            raise ValueError(f"Rule {rule.rule_id} already registered")

        self.rules[rule.rule_id] = rule

        # Index by category
        self._rules_by_category[rule.category].append(rule)
        self._rules_by_category[rule.category].sort(
            key=lambda r: r.priority, reverse=True
        )

        # Index by language
        if rule.language:
            if rule.language not in self._rules_by_language:
                self._rules_by_language[rule.language] = []
            self._rules_by_language[rule.language].append(rule)
            self._rules_by_language[rule.language].sort(
                key=lambda r: r.priority, reverse=True
            )

    def unregister(self, rule_id: str) -> bool:
        """
        Unregister a rule.

        Args:
            rule_id: Rule ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        if rule_id not in self.rules:
            return False

        rule = self.rules[rule_id]
        del self.rules[rule_id]

        # Remove from category index
        self._rules_by_category[rule.category].remove(rule)

        # Remove from language index
        if rule.language and rule.language in self._rules_by_language:
            self._rules_by_language[rule.language].remove(rule)

        return True

    def get(self, rule_id: str) -> Optional[Rule]:
        """
        Get a rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule if found, None otherwise
        """
        return self.rules.get(rule_id)

    def find_rules_for_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        category: Optional[RuleCategory] = None,
    ) -> List[Rule]:
        """
        Find all rules that apply to a file.

        Args:
            file_path: File path
            language: Optional language filter
            category: Optional category filter

        Returns:
            List of applicable rules, sorted by priority
        """
        rules = []

        # Start with all rules or filtered by category
        if category:
            candidate_rules = self._rules_by_category.get(category, [])
        else:
            candidate_rules = list(self.rules.values())

        # Filter by language if specified
        if language:
            candidate_rules = [
                r for r in candidate_rules
                if r.matches_language(language)
            ]

        # Filter by file pattern
        rules = [
            r for r in candidate_rules
            if r.matches_file(file_path)
        ]

        # Sort by priority
        rules.sort(key=lambda r: r.priority, reverse=True)

        return rules

    def list_rules(
        self,
        category: Optional[RuleCategory] = None,
        language: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[Rule]:
        """
        List registered rules.

        Args:
            category: Filter by category
            language: Filter by language
            enabled_only: Only return enabled rules

        Returns:
            List of rules
        """
        if category:
            rules = self._rules_by_category.get(category, [])
        elif language:
            rules = self._rules_by_language.get(language, [])
        else:
            rules = list(self.rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def enable(self, rule_id: str) -> bool:
        """
        Enable a rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if enabled, False if not found
        """
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable(self, rule_id: str) -> bool:
        """
        Disable a rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if disabled, False if not found
        """
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def clear(self) -> None:
        """Clear all rules."""
        self.rules.clear()
        for category in RuleCategory:
            self._rules_by_category[category].clear()
        self._rules_by_language.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_rules": len(self.rules),
            "by_category": {
                category.value: len(rules)
                for category, rules in self._rules_by_category.items()
            },
            "by_language": {
                lang: len(rules)
                for lang, rules in self._rules_by_language.items()
            },
            "by_severity": {
                severity.value: sum(
                    1 for r in self.rules.values()
                    if r.severity == severity
                )
                for severity in RuleSeverity
            },
            "enabled": sum(1 for r in self.rules.values() if r.enabled),
            "disabled": sum(1 for r in self.rules.values() if not r.enabled),
        }
