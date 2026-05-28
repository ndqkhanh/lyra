"""Rules manager - Core rules system with language override"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Rule:
    """A coding rule"""
    name: str
    category: str
    language: str  # "common" or specific language
    content: str
    priority: int = 0  # Higher priority overrides lower


class RulesManager:
    """Manages coding rules with language-specific overrides"""

    def __init__(self, rules_dir: Path | None = None):
        self.rules_dir = rules_dir or Path.home() / ".lyra" / "rules"
        self.rules: dict[str, list[Rule]] = {}  # category -> rules
        self.language_rules: dict[str, dict[str, list[Rule]]] = {}  # lang -> category -> rules

    def load_rules(self):
        """Load all rules from directory"""
        if not self.rules_dir.exists():
            return

        # Load common rules first
        common_dir = self.rules_dir / "common"
        if common_dir.exists():
            self._load_rules_from_dir(common_dir, "common")

        # Load language-specific rules
        for lang_dir in self.rules_dir.iterdir():
            if lang_dir.is_dir() and lang_dir.name != "common":
                language = lang_dir.name
                self._load_rules_from_dir(lang_dir, language)

    def _load_rules_from_dir(self, directory: Path, language: str):
        """Load rules from a directory"""
        for rule_file in directory.glob("*.md"):
            try:
                content = rule_file.read_text()
                category = rule_file.stem

                rule = Rule(
                    name=f"{language}/{category}",
                    category=category,
                    language=language,
                    content=content,
                    priority=1 if language != "common" else 0
                )

                # Store in appropriate structure
                if language == "common":
                    if category not in self.rules:
                        self.rules[category] = []
                    self.rules[category].append(rule)
                else:
                    if language not in self.language_rules:
                        self.language_rules[language] = {}
                    if category not in self.language_rules[language]:
                        self.language_rules[language][category] = []
                    self.language_rules[language][category].append(rule)

            except Exception as e:
                print(f"Warning: Failed to load rule {rule_file}: {e}")

    def get_rules(self, language: str | None = None, category: str | None = None) -> list[Rule]:
        """Get rules with language-specific override

        Language-specific rules override common rules (CSS specificity model)
        """
        result = []

        # Get common rules
        if category:
            result.extend(self.rules.get(category, []))
        else:
            for rules_list in self.rules.values():
                result.extend(rules_list)

        # Override with language-specific rules
        if language and language in self.language_rules:
            if category:
                result.extend(self.language_rules[language].get(category, []))
            else:
                for rules_list in self.language_rules[language].values():
                    result.extend(rules_list)

        # Sort by priority (higher priority first)
        result.sort(key=lambda r: r.priority, reverse=True)

        return result

    def get_rules_text(self, language: str | None = None) -> str:
        """Get all rules as formatted text"""
        rules = self.get_rules(language)

        if not rules:
            return "No rules loaded."

        text = []
        current_category = None

        for rule in rules:
            if rule.category != current_category:
                current_category = rule.category
                text.append(f"\n## {current_category.replace('-', ' ').title()}\n")

            text.append(rule.content)
            text.append("\n")

        return "\n".join(text)

    def list_categories(self) -> list[str]:
        """List all rule categories"""
        categories = set(self.rules.keys())
        for lang_rules in self.language_rules.values():
            categories.update(lang_rules.keys())
        return sorted(categories)

    def list_languages(self) -> list[str]:
        """List all supported languages"""
        return ["common"] + sorted(self.language_rules.keys())


# Global rules manager
_rules_manager: RulesManager | None = None


def get_rules_manager() -> RulesManager:
    """Get or create global rules manager"""
    global _rules_manager
    if _rules_manager is None:
        _rules_manager = RulesManager()
        _rules_manager.load_rules()
    return _rules_manager
