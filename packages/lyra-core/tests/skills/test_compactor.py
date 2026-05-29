"""Tests for SkillCompactor — 6-phase skill lifecycle compaction."""

from lyra_core.skills.compactor import (
    SkillCompactor,
    _estimate_tokens,
    _split_paragraphs,
)

SAMPLE_SKILL = """## Purpose
Refactor a Python module from procedural to clean architecture.

## Procedure
1. Identify current module responsibilities
2. Split into entities, use-cases, repositories, and interfaces
3. Apply dependency inversion
4. Verify all existing tests still pass
5. Run coverage check

## Examples
Here is a very long example showing the before state of a module with hundreds of lines of code
that demonstrates the problem clearly and concisely.

Another example showing the after state with all the refactored components properly separated into
clean architecture layers following the dependency inversion principle.

A third example demonstrating edge cases with circular dependencies and how to resolve them.

A fourth example with async patterns and how they fit into the clean architecture.

## Changelog
- v3.0: Added async pattern support
- v2.0: Switched to protocol-based interfaces
- v1.0: Initial version

## Appendix
Additional notes about compatibility with older Python versions and special considerations for
large codebases with many modules.
"""


class TestSkillCompactor:
    def test_compact_removes_changelog_section(self):
        compactor = SkillCompactor(max_tokens=5000)
        result, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert "Changelog" not in result
        assert report.sections_removed >= 1

    def test_compact_preserves_purpose_and_procedure(self):
        compactor = SkillCompactor(max_tokens=5000)
        result, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert "Purpose" in result
        assert "Procedure" in result
        assert report.sections_preserved >= 2

    def test_compact_compacts_examples_section(self):
        compactor = SkillCompactor(max_tokens=5000)
        result, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert "compacted" in result.lower() or report.sections_compacted >= 1

    def test_compact_reduces_token_count(self):
        compactor = SkillCompactor(max_tokens=5000)
        _, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert report.compacted_tokens < report.original_tokens

    def test_compact_when_already_under_budget(self):
        compactor = SkillCompactor(max_tokens=50000)
        _, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert report.compacted_tokens <= report.original_tokens

    def test_compact_truncates_when_over_budget(self):
        compactor = SkillCompactor(max_tokens=50)
        result, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert _estimate_tokens(result) <= 55  # allow small rounding margin

    def test_report_has_token_savings(self):
        compactor = SkillCompactor(max_tokens=5000)
        _, report = compactor.compact("test-skill", SAMPLE_SKILL)
        assert report.token_savings >= 0
        assert 0.0 <= report.savings_pct <= 1.0

    def test_empty_skill(self):
        compactor = SkillCompactor()
        result, report = compactor.compact("empty", "")
        assert isinstance(result, str)
        assert report.original_tokens == 1


class TestHelpers:
    def test_split_paragraphs(self):
        lines = ["para 1 line 1", "para 1 line 2", "", "para 2"]
        paras = _split_paragraphs(lines)
        assert len(paras) == 2
        assert "para 1 line 1" in paras[0]
        assert "para 2" in paras[1]

    def test_split_paragraphs_single(self):
        lines = ["only one paragraph", "with two lines"]
        paras = _split_paragraphs(lines)
        assert len(paras) == 1

    def test_estimate_tokens(self):
        assert _estimate_tokens("") == 1
        assert _estimate_tokens("a" * 40) == 10
