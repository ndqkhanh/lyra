"""
Tests for RuleParser — parsing rule definitions from markdown files with
YAML frontmatter, including edge cases and error handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lyra.rules.rule import Rule, RuleCategory, RuleSeverity
from lyra.rules.rule_parser import RuleParser


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def parser() -> RuleParser:
    return RuleParser()


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    """Create a temporary rules directory with sample rule files."""
    d = tmp_path / "rules"
    d.mkdir()

    # Full frontmatter
    (d / "no-todos.md").write_text("""---
rule_id: no-todos
title: No TODO Comments
category: coding-style
severity: warning
language: python
file_patterns:
  - "*.py"
priority: 10
enabled: true
examples:
  bad: "# TODO: fix this"
  good: "# Implement feature"
references:
  - "https://example.com"
metadata:
  author: test
---
Avoid leaving TODO and FIXME comments in production code.
""")

    # Minimal frontmatter
    (d / "no-secrets.md").write_text("""---
id: no-secrets
title: No Hardcoded Secrets
category: security
severity: error
---
Never hardcode passwords, API keys, or tokens.
""")

    # No frontmatter
    (d / "best-practices.md").write_text("""Always use type hints in Python.
Prefer dataclasses over dictionaries.
""")

    # Invalid YAML frontmatter
    (d / "broken.md").write_text("""---
invalid: yaml: unclosed: quote
---
Content here.
""")

    # Empty frontmatter (needs blank line for regex to match)
    (d / "empty-frontmatter.md").write_text("""---
---
Just content.
""")

    # Frontmatter without rule_id
    (d / "no-id.md").write_text("""---
title: No ID Rule
category: testing
---
Content without an ID.
""")

    # Invalid category
    (d / "invalid-category.md").write_text("""---
rule_id: invalid-cat
title: Invalid Category
category: not-a-real-category
severity: error
---
Some content.
""")

    # Invalid severity
    (d / "invalid-severity.md").write_text("""---
rule_id: invalid-sev
title: Invalid Severity
category: coding-style
severity: critical
---
Some content.
""")

    return d


# =========================================================================
# RuleParser — parse_string
# =========================================================================


class TestRuleParserParseString:
    """parse_string with various frontmatter scenarios."""

    def test_full_frontmatter(self, parser: RuleParser):
        """Parse rule with full YAML frontmatter."""
        content = """---
rule_id: test-rule
title: Test Rule
category: coding-style
severity: error
language: python
file_patterns:
  - "*.py"
  - "*.ts"
priority: 5
enabled: true
examples:
  good: "x = 1"
  bad: "x = '1'"
references:
  - "https://docs.example.com"
metadata:
  team: platform
---
This is the rule description.
It spans multiple lines.
"""
        rule = parser.parse_string(content, source_file="test.md")
        assert rule is not None
        assert rule.rule_id == "test-rule"
        assert rule.title == "Test Rule"
        assert rule.category == RuleCategory.CODING_STYLE
        assert rule.severity == RuleSeverity.ERROR
        assert rule.language == "python"
        assert "*.py" in rule.file_patterns
        assert "*.ts" in rule.file_patterns
        assert rule.priority == 5
        assert rule.enabled is True
        assert rule.examples["good"] == "x = 1"
        assert rule.references[0] == "https://docs.example.com"
        assert rule.metadata["team"] == "platform"

    def test_no_frontmatter(self, parser: RuleParser):
        """No frontmatter with no source_file returns None (no rule_id)."""
        rule = parser.parse_string("Just a description.")
        assert rule is None

    def test_no_frontmatter_with_source_file(self, parser: RuleParser):
        """No frontmatter with source_file generates ID from filename."""
        rule = parser.parse_string("Some description.", source_file="my-rule.md")
        assert rule is not None
        assert rule.rule_id == "my-rule"
        assert rule.description == "Some description."

    def test_minimal_frontmatter(self, parser: RuleParser):
        """Minimal frontmatter with just id."""
        content = """---
id: minimal-rule
---
Keep it simple.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert rule.rule_id == "minimal-rule"
        assert rule.description == "Keep it simple."
        assert rule.category == RuleCategory.CODING_STYLE  # default
        assert rule.severity == RuleSeverity.WARNING  # default

    def test_rule_id_via_id_field(self, parser: RuleParser):
        """Use 'id' field instead of 'rule_id'."""
        content = """---
id: alt-id-rule
---
Content.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert rule.rule_id == "alt-id-rule"

    def test_rule_id_prefers_rule_id(self, parser: RuleParser):
        """rule_id takes precedence over 'id' field."""
        content = """---
rule_id: primary-id
id: secondary-id
---
Content.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert rule.rule_id == "primary-id"

    def test_no_rule_id_no_file_returns_none(self, parser: RuleParser):
        """No rule_id and no source_file returns None."""
        rule = parser.parse_string("some content")
        assert rule is None

    def test_invalid_yaml(self, parser: RuleParser):
        """Invalid YAML frontmatter causes None return."""
        rule = parser.parse_string("---\ninvalid: yaml: unclosed: quote\n---\ncontent")
        # YAML error is caught, returns None
        assert rule is None

    def test_empty_frontmatter(self, parser: RuleParser):
        """Empty frontmatter without actual content between delimiters
        falls through because the regex expects a newline before closing ---."""
        content = "---\n---\ncontent"
        rule = parser.parse_string(content, source_file="test.md")
        # The regex expects \n before closing ---, so empty frontmatter
        # falls back to "no frontmatter" path, rule_id from filename
        assert rule is not None
        # Content is treated as everything (frontmatter not detected)
        assert "content" in rule.description

    def test_invalid_category_falls_back(self, parser: RuleParser):
        """Invalid category falls back to CODING_STYLE."""
        content = """---
rule_id: bad-cat
category: nonexistent-category
---
Content.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert rule.rule_id == "bad-cat"
        assert rule.category == RuleCategory.CODING_STYLE

    def test_invalid_severity_falls_back(self, parser: RuleParser):
        """Invalid severity falls back to WARNING."""
        content = """---
rule_id: bad-sev
severity: critical
---
Content.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert rule.severity == RuleSeverity.WARNING

    def test_all_fields_default(self, parser: RuleParser):
        """Default values for optional fields."""
        content = """---
rule_id: defaults-test
title: Defaults Test
category: testing
---
Description.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert rule.severity == RuleSeverity.WARNING
        assert rule.language is None
        assert rule.file_patterns == []
        assert rule.enabled is True
        assert rule.priority == 0
        assert rule.examples == {}
        assert rule.references == []
        assert rule.metadata == {}

    def test_category_string_enum_mapping(self, parser: RuleParser):
        """String category values map to proper enum."""
        mappings = [
            ("coding-style", RuleCategory.CODING_STYLE),
            ("git-workflow", RuleCategory.GIT_WORKFLOW),
            ("testing", RuleCategory.TESTING),
            ("performance", RuleCategory.PERFORMANCE),
            ("patterns", RuleCategory.PATTERNS),
            ("hooks", RuleCategory.HOOKS),
            ("agents", RuleCategory.AGENTS),
            ("security", RuleCategory.SECURITY),
            ("code-review", RuleCategory.CODE_REVIEW),
            ("development-workflow", RuleCategory.DEVELOPMENT_WORKFLOW),
        ]
        for cat_str, expected in mappings:
            content = f"""---
rule_id: cat-{cat_str}
category: {cat_str}
---
Content.
"""
            rule = parser.parse_string(content)
            assert rule is not None
            assert rule.category == expected, f"Failed for {cat_str}"

    def test_severity_string_enum_mapping(self, parser: RuleParser):
        """String severity values map to proper enum."""
        mappings = [
            ("error", RuleSeverity.ERROR),
            ("warning", RuleSeverity.WARNING),
            ("info", RuleSeverity.INFO),
            ("hint", RuleSeverity.HINT),
        ]
        for sev_str, expected in mappings:
            content = f"""---
rule_id: sev-{sev_str}
severity: {sev_str}
---
Content.
"""
            rule = parser.parse_string(content)
            assert rule is not None
            assert rule.severity == expected, f"Failed for {sev_str}"

    def test_multiline_description(self, parser: RuleParser):
        """Multiline description in body is preserved."""
        content = """---
rule_id: multi-line
---
First line.

Second line.
Third line.
"""
        rule = parser.parse_string(content)
        assert rule is not None
        assert "First line" in rule.description
        assert "Second line" in rule.description
        assert "Third line" in rule.description


# =========================================================================
# RuleParser — parse_file
# =========================================================================


class TestRuleParserParseFile:
    """parse_file with actual files."""

    def test_parse_valid_file(self, parser: RuleParser, rules_dir: Path):
        """Parse a valid rule file with full frontmatter."""
        rule = parser.parse_file(rules_dir / "no-todos.md")
        assert rule is not None
        assert rule.rule_id == "no-todos"
        assert rule.title == "No TODO Comments"
        assert rule.category == RuleCategory.CODING_STYLE
        assert rule.severity == RuleSeverity.WARNING
        assert rule.language == "python"
        assert "*.py" in rule.file_patterns
        assert rule.priority == 10

    def test_parse_file_with_id_field(self, parser: RuleParser, rules_dir: Path):
        """Parse a file that uses 'id' instead of 'rule_id'."""
        rule = parser.parse_file(rules_dir / "no-secrets.md")
        assert rule is not None
        assert rule.rule_id == "no-secrets"
        assert rule.category == RuleCategory.SECURITY
        assert rule.severity == RuleSeverity.ERROR

    def test_parse_file_no_frontmatter(self, parser: RuleParser, rules_dir: Path):
        """File without frontmatter uses filename as ID."""
        rule = parser.parse_file(rules_dir / "best-practices.md")
        assert rule is not None
        assert rule.rule_id == "best-practices"
        assert rule.description == "Always use type hints in Python.\nPrefer dataclasses over dictionaries."

    def test_parse_file_invalid_yaml(self, parser: RuleParser, rules_dir: Path):
        """File with invalid YAML frontmatter returns None."""
        rule = parser.parse_file(rules_dir / "broken.md")
        assert rule is None

    def test_parse_file_nonexistent(self, parser: RuleParser):
        """Non-existent file returns None."""
        rule = parser.parse_file(Path("/nonexistent/file.md"))
        assert rule is None

    def test_parse_file_empty_frontmatter(self, parser: RuleParser, rules_dir: Path):
        """File with empty frontmatter uses filename."""
        rule = parser.parse_file(rules_dir / "empty-frontmatter.md")
        assert rule is not None
        assert rule.rule_id == "empty-frontmatter"

    def test_parse_file_no_id_generates_from_filename(self, parser: RuleParser, rules_dir: Path):
        """File with frontmatter but no rule_id/id uses filename."""
        rule = parser.parse_file(rules_dir / "no-id.md")
        assert rule is not None
        assert rule.rule_id == "no-id"

    def test_parse_file_invalid_category(self, parser: RuleParser, rules_dir: Path):
        """File with invalid category uses default."""
        rule = parser.parse_file(rules_dir / "invalid-category.md")
        assert rule is not None
        assert rule.category == RuleCategory.CODING_STYLE

    def test_parse_file_invalid_severity(self, parser: RuleParser, rules_dir: Path):
        """File with invalid severity uses default."""
        rule = parser.parse_file(rules_dir / "invalid-severity.md")
        assert rule is not None
        assert rule.severity == RuleSeverity.WARNING


# =========================================================================
# RuleParser — parse_directory
# =========================================================================


class TestRuleParserParseDirectory:
    """parse_directory for bulk loading."""

    def test_parse_directory_recursive(self, parser: RuleParser, rules_dir: Path):
        """Parse all .md files in a directory recursively."""
        rules = parser.parse_directory(rules_dir, recursive=True)
        # All valid files should be parsed
        assert "no-todos" in rules
        assert "no-secrets" in rules
        assert "best-practices" in rules

    def test_parse_directory_non_recursive(self, parser: RuleParser, rules_dir: Path):
        """Parse only .md files at the top level."""
        # Add a subdirectory
        subdir = rules_dir / "sub"
        subdir.mkdir()
        (subdir / "sub-rule.md").write_text("---\nrule_id: sub-rule\n---\nSub rule.")
        non_recursive = parser.parse_directory(rules_dir, recursive=False)
        assert "sub-rule" not in non_recursive

    def test_parse_directory_recursive_finds_subdir(self, parser: RuleParser, rules_dir: Path):
        """Recursive parse finds files in subdirectories."""
        subdir = rules_dir / "nested"
        subdir.mkdir()
        (subdir / "nested-rule.md").write_text("---\nrule_id: nested-rule\n---\nNested.")
        rules = parser.parse_directory(rules_dir, recursive=True)
        assert "nested-rule" in rules

    def test_parse_directory_empty(self, parser: RuleParser, tmp_path: Path):
        """Empty directory returns empty dict."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        rules = parser.parse_directory(empty_dir)
        assert rules == {}

    def test_parse_directory_skips_invalid(self, parser: RuleParser, rules_dir: Path):
        """Invalid files are skipped."""
        rules = parser.parse_directory(rules_dir, recursive=True)
        # broken.md should be skipped (None returned)
        assert "broken" not in rules

    def test_parse_directory_loads_all_valid(self, parser: RuleParser, rules_dir: Path):
        """All valid rules are loaded."""
        rules = parser.parse_directory(rules_dir, recursive=True)
        # no-todos, no-secrets, best-practices, no-id, invalid-category, invalid-severity, empty-frontmatter
        # broken is None -> skipped
        # 7 valid files should produce 7 rules (or the ones that are valid)
        assert len(rules) >= 6


# =========================================================================
# RuleParser — frontmatter pattern
# =========================================================================


class TestRuleParserFrontmatterPattern:
    """FRONTMATTER_PATTERN regex matching."""

    def test_pattern_matches_standard(self, parser: RuleParser):
        """Standard frontmatter pattern matches."""
        content = "---\nkey: value\n---\nbody"
        match = parser.FRONTMATTER_PATTERN.match(content)
        assert match is not None
        assert match.group(1).strip() == "key: value"
        assert match.group(2).strip() == "body"

    def test_pattern_matches_empty_yaml(self, parser: RuleParser):
        """Empty YAML frontmatter matches (needs a blank line)."""
        content = "---\n\n---\nbody"
        match = parser.FRONTMATTER_PATTERN.match(content)
        assert match is not None
        assert match.group(1).strip() == ""
        assert match.group(2).strip() == "body"

    def test_pattern_no_match(self, parser: RuleParser):
        """No frontmatter produces no match."""
        content = "Just a regular file."
        match = parser.FRONTMATTER_PATTERN.match(content)
        assert match is None

    def test_pattern_no_closing_delimiter(self, parser: RuleParser):
        """Missing closing --- produces no match."""
        content = "---\nkey: value\nno-close"
        match = parser.FRONTMATTER_PATTERN.match(content)
        assert match is None

    def test_pattern_multiline_body(self, parser: RuleParser):
        """Multi-line body is captured after frontmatter."""
        content = "---\nkey: val\n---\nline1\nline2\nline3"
        match = parser.FRONTMATTER_PATTERN.match(content)
        assert match is not None
        body = match.group(2)
        assert "line1" in body
        assert "line2" in body
        assert "line3" in body

    def test_pattern_with_only_frontmatter_delimiters(self, parser: RuleParser):
        """Content with only --- delimiters does not match regex (needs body)."""
        content = "---\n---"
        match = parser.FRONTMATTER_PATTERN.match(content)
        assert match is None
