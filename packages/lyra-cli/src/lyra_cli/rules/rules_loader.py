"""Rules loader - Load and parse rule files"""

from pathlib import Path
from typing import List, Dict
from .rules_manager import Rule


class RulesLoader:
    """Loads rules from various sources"""

    @staticmethod
    def load_from_file(file_path: Path, language: str = "common") -> Rule:
        """Load a single rule file"""
        content = file_path.read_text()
        category = file_path.stem

        return Rule(
            name=f"{language}/{category}",
            category=category,
            language=language,
            content=content,
            priority=1 if language != "common" else 0
        )

    @staticmethod
    def load_from_directory(directory: Path, language: str = "common") -> List[Rule]:
        """Load all rules from a directory"""
        rules = []

        if not directory.exists():
            return rules

        for rule_file in directory.glob("*.md"):
            try:
                rule = RulesLoader.load_from_file(rule_file, language)
                rules.append(rule)
            except Exception as e:
                print(f"Warning: Failed to load {rule_file}: {e}")

        return rules

    @staticmethod
    def create_default_rules(rules_dir: Path):
        """Create default rule files"""
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Common rules
        common_dir = rules_dir / "common"
        common_dir.mkdir(exist_ok=True)

        # Coding style
        (common_dir / "coding-style.md").write_text("""# Coding Style

## General Principles
- Write clear, readable code
- Use meaningful variable names
- Keep functions small and focused
- Follow DRY (Don't Repeat Yourself)
- Comment complex logic

## Formatting
- Consistent indentation
- Proper spacing
- Line length limits
- Organize imports
""")

        # Git workflow
        (common_dir / "git-workflow.md").write_text("""# Git Workflow

## Commit Messages
- Use conventional commits format
- Present tense ("Add feature" not "Added feature")
- Imperative mood ("Move cursor" not "Moves cursor")
- First line under 50 characters
- Body wraps at 72 characters

## Branching
- feature/* for new features
- fix/* for bug fixes
- refactor/* for refactoring
- docs/* for documentation

## Pull Requests
- Clear description
- Link to issues
- Request reviews
- Keep PRs focused
""")

        # Testing
        (common_dir / "testing.md").write_text("""# Testing

## Test Coverage
- Minimum 80% coverage
- Test edge cases
- Test error handling
- Test happy path

## Test Structure
- Arrange-Act-Assert pattern
- One assertion per test
- Clear test names
- Fast, isolated tests

## TDD Workflow
1. Write failing test (red)
2. Write minimal code (green)
3. Refactor for quality
4. Repeat
""")

        # Python-specific rules
        python_dir = rules_dir / "python"
        python_dir.mkdir(exist_ok=True)

        (python_dir / "coding-style.md").write_text("""# Python Coding Style

## PEP 8 Compliance
- 4 spaces for indentation
- 79 characters per line
- snake_case for functions/variables
- PascalCase for classes
- UPPER_CASE for constants

## Type Hints
- Use type hints for function signatures
- Use Optional for nullable types
- Use Union for multiple types
- Use List, Dict, Set from typing

## Imports
- Standard library first
- Third-party packages second
- Local imports last
- Alphabetical within groups
""")

        # TypeScript-specific rules
        typescript_dir = rules_dir / "typescript"
        typescript_dir.mkdir(exist_ok=True)

        (typescript_dir / "coding-style.md").write_text("""# TypeScript Coding Style

## Naming Conventions
- camelCase for variables/functions
- PascalCase for classes/interfaces
- UPPER_CASE for constants
- Prefix interfaces with 'I' (optional)

## Type Safety
- Enable strict mode
- Avoid 'any' type
- Use interfaces for objects
- Use enums for constants
- Prefer const over let

## Modern Features
- Use arrow functions
- Use async/await over promises
- Use destructuring
- Use template literals
- Use optional chaining
""")

        print(f"✓ Created default rules in {rules_dir}")


# Helper function
def create_default_rules():
    """Create default rules in ~/.lyra/rules"""
    rules_dir = Path.home() / ".lyra" / "rules"
    RulesLoader.create_default_rules(rules_dir)
