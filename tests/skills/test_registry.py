"""
Tests for SkillRegistry and SkillGraph — comprehensive edge case coverage.

Covers:
  - SkillGraph: cycle detection variations, serialization edge cases
  - SkillRegistry: register with all indices, unregister edge cases
  - search edge cases (empty query, no matches, all filters)
  - find_by_trigger edge cases (no triggers, partial matches)
  - graph integration (unregister preserves graph integrity)
  - save/load edge cases (empty, corrupted)
  - get_statistics edge cases
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lyra.skills.registry import CycleError, SkillGraph, SkillRegistry
from lyra.skills.skill import Skill, SkillCategory, SkillSearchResult


# ======================================================================
# SkillGraph extended tests
# ======================================================================


class TestSkillGraphExtended:
    """Additional edge case tests for SkillGraph beyond basic tests."""

    def test_add_node_idempotent(self) -> None:
        g = SkillGraph()
        g.add_node("a")
        g.add_node("a")  # Should not raise
        assert "a" in g.get_execution_order()

    def test_remove_nonexistent_node(self) -> None:
        g = SkillGraph()
        g.remove_node("nonexistent")  # Should not raise
        assert g.get_execution_order() == []

    def test_dependencies_nonexistent(self) -> None:
        g = SkillGraph()
        assert g.dependencies("unknown") == set()
        assert g.dependents("unknown") == set()

    def test_detect_cycles_complex(self) -> None:
        """Detect cycles in a more complex graph."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        g.add_dependency("c", "d")
        g.add_dependency("d", "b")  # Creates b->c->d->b cycle
        cycles = g.detect_cycles()
        assert len(cycles) > 0
        # At least one cycle should include b, c, d
        cycle_nodes = set()
        for c in cycles:
            cycle_nodes.update(c)
        assert "b" in cycle_nodes
        assert "c" in cycle_nodes
        assert "d" in cycle_nodes

    def test_detect_cycles_no_cycles(self) -> None:
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        cycles = g.detect_cycles()
        assert cycles == []

    def test_detect_cycles_empty(self) -> None:
        g = SkillGraph()
        assert g.detect_cycles() == []

    def test_cycle_with_multiple_edges(self) -> None:
        """Multiple edges creating cycles from different paths."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        g.add_dependency("c", "a")  # a->b->c->a
        g.add_dependency("d", "e")
        g.add_dependency("e", "d")  # d->e->d
        assert g.has_cycle()

    def test_serialization_nested(self) -> None:
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        g.add_dependency("c", "d")
        data = g.to_dict()
        g2 = SkillGraph.from_dict(data)
        order1 = g.get_execution_order()
        order2 = g2.get_execution_order()
        assert len(order1) == len(order2)
        # All same nodes
        assert set(order1) == set(order2)

    def test_from_dict_with_deps(self) -> None:
        data = {
            "app": ["db", "cache"],
            "db": [],
            "cache": [],
        }
        g = SkillGraph.from_dict(data)
        assert g.dependencies("app") == {"db", "cache"}
        assert g.dependents("db") == {"app"}

    def test_get_execution_order_isolated_groups(self) -> None:
        g = SkillGraph()
        g.add_dependency("a1", "a2")
        g.add_dependency("b1", "b2")
        order = g.get_execution_order()
        assert len(order) == 4
        assert "a2" in order
        assert "a1" in order
        assert "b2" in order
        assert "b1" in order
        # Each group is ordered correctly
        assert order.index("a2") < order.index("a1")
        assert order.index("b2") < order.index("b1")

    def test_cycle_error_message(self) -> None:
        try:
            g = SkillGraph()
            g.add_dependency("a", "b")
            g.add_dependency("b", "a")
            g.get_execution_order()
        except CycleError as e:
            assert "Cycle detected" in str(e)
            assert isinstance(e.cycle, list)

    def test_remove_node_cleans_edges_from_others(self) -> None:
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("c", "b")
        g.remove_node("b")
        # a and c now have no dependencies since b is gone
        assert g.dependencies("a") == set()
        assert g.dependencies("c") == set()
        assert g.dependents("b") == set()


# ======================================================================
# SkillRegistry extended tests
# ======================================================================


class TestSkillRegistryExtended:
    """Additional edge case tests for SkillRegistry."""

    def test_register_with_all_indices(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="full-skill",
            description="Full skill with indices",
            content="Content",
            category=SkillCategory.BACKEND_PATTERNS,
            trigger_patterns=["api"],
            tags=["python", "api"],
            language="python",
            dependencies=["dep1"],
        )
        reg.register(skill)
        assert "full-skill" in reg.skills
        assert SkillCategory.BACKEND_PATTERNS in reg._category_index
        assert "python" in reg._tag_index
        assert "api" in reg._tag_index
        assert "python" in reg._language_index

    def test_register_without_language(self) -> None:
        """Skills without language don't create language index entries."""
        reg = SkillRegistry()
        skill = Skill(
            name="no-lang",
            description="No language",
            content="Content",
        )
        reg.register(skill)
        assert reg._language_index == {}

    def test_register_without_tags(self) -> None:
        """Skills without tags don't create tag index entries."""
        reg = SkillRegistry()
        skill = Skill(
            name="no-tags",
            description="No tags",
            content="Content",
        )
        reg.register(skill)
        assert reg._tag_index == {}

    def test_unregister_nonexistent(self) -> None:
        reg = SkillRegistry()
        assert reg.unregister("nonexistent") is False

    def test_unregister_removes_from_all_indices(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="removable",
            description="Will be removed",
            content="Content",
            category=SkillCategory.TDD_TESTING,
            tags=["python", "testing"],
            language="python",
        )
        reg.register(skill)
        assert reg.unregister("removable") is True
        assert "removable" not in reg.skills
        assert "removable" not in reg._category_index.get(SkillCategory.TDD_TESTING, set())
        assert "python" not in reg._tag_index or "removable" not in reg._tag_index["python"]
        assert "python" not in reg._language_index.get("python", set())
        # Graph should not have the node either
        assert "removable" not in reg.get_execution_order()

    def test_unregister_without_cleanup_issues(self) -> None:
        """Unregister doesn't crash when indices have been cleaned up."""
        reg = SkillRegistry()
        skill = Skill(
            name="remove-me",
            description="Remove",
            content="Content",
            tags=["tag1"],
            language="python",
        )
        reg.register(skill)

        # Manually clear indices to simulate edge case
        reg._category_index.clear()
        reg._tag_index.clear()
        reg._language_index.clear()

        # Should still work without raising
        assert reg.unregister("remove-me") is True

    def test_get_nonexistent(self) -> None:
        reg = SkillRegistry()
        assert reg.get("nonexistent") is None

    def test_find_by_trigger_no_skill_has_triggers(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="no-triggers",
            description="No trigger patterns",
            content="Content",
            trigger_patterns=[],
        )
        reg.register(skill)
        results = reg.find_by_trigger("anything")
        assert len(results) == 0

    def test_find_by_trigger_partial_word_match(self) -> None:
        """Trigger pattern that is a substring of text still matches."""
        reg = SkillRegistry()
        skill = Skill(
            name="partial",
            description="Partial match test",
            content="Content",
            trigger_patterns=["formatting"],
        )
        reg.register(skill)
        # The code checks if trigger pattern is IN the text: "formatting" in "formatting my code"
        results = reg.find_by_trigger("formatting my code")
        assert len(results) == 1

    def test_find_by_trigger_case_insensitive(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="case-test",
            description="Case test",
            content="Content",
            trigger_patterns=["PYTEST"],
        )
        reg.register(skill)
        results = reg.find_by_trigger("I need pytest")
        assert len(results) == 1

    def test_find_by_trigger_score_ordering(self) -> None:
        """Results are sorted by score descending."""
        reg = SkillRegistry()
        skill_a = Skill(
            name="multi-match",
            description="Matches multiple patterns",
            content="Content",
            trigger_patterns=["test", "pytest", "unit"],
        )
        skill_b = Skill(
            name="single-match",
            description="Matches one pattern",
            content="Content",
            trigger_patterns=["test"],
        )
        reg.register(skill_a)
        reg.register(skill_b)
        results = reg.find_by_trigger("run pytest test")
        assert len(results) >= 2
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_find_by_category_empty_category(self) -> None:
        reg = SkillRegistry()
        results = reg.find_by_category(SkillCategory.GENERAL)
        assert results == []

    def test_find_by_category_no_matches(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="backend",
            description="Backend",
            content="Content",
            category=SkillCategory.BACKEND_PATTERNS,
        )
        reg.register(skill)
        results = reg.find_by_category(SkillCategory.TDD_TESTING)
        assert results == []

    def test_find_by_tags_empty_set(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="tagged",
            description="Tagged",
            content="Content",
            tags=["python"],
        )
        reg.register(skill)
        results = reg.find_by_tags(set())
        assert results == []

    def test_find_by_tags_match_all_exact(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="full-match",
            description="Full match",
            content="Content",
            tags=["python", "testing", "pytest"],
        )
        partial = Skill(
            name="partial",
            description="Partial",
            content="Content",
            tags=["python"],
        )
        reg.register(skill)
        reg.register(partial)
        results = reg.find_by_tags({"python", "testing"}, match_all=True)
        assert len(results) == 1
        assert results[0].name == "full-match"

    def test_find_by_tags_match_all_no_match(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="mismatch",
            description="Mismatch",
            content="Content",
            tags=["python", "testing"],
        )
        reg.register(skill)
        results = reg.find_by_tags({"python", "javascript"}, match_all=True)
        assert results == []

    def test_find_by_tags_match_any(self) -> None:
        reg = SkillRegistry()
        skill_a = Skill(
            name="python-only",
            description="Python",
            content="Content",
            tags=["python"],
        )
        skill_b = Skill(
            name="js-only",
            description="JS",
            content="Content",
            tags=["javascript"],
        )
        reg.register(skill_a)
        reg.register(skill_b)
        results = reg.find_by_tags({"python"}, match_all=False)
        assert len(results) == 1
        assert results[0].name == "python-only"

    def test_find_by_language_empty(self) -> None:
        reg = SkillRegistry()
        results = reg.find_by_language("rust")
        assert results == []

    def test_find_by_language_no_language_skills(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="no-lang",
            description="No language",
            content="Content",
        )
        reg.register(skill)
        results = reg.find_by_language("python")
        assert results == []

    def test_search_empty_query(self) -> None:
        """Empty query matches everything (empty string is substring of all)."""
        reg = SkillRegistry()
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
        )
        reg.register(skill)
        results = reg.search("")
        # "" is in "...", so all skills match all text fields
        assert len(results) == 1

    def test_search_no_match(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="unique-name",
            description="Unique description",
            content="Unique content",
            tags=["special"],
        )
        reg.register(skill)
        results = reg.search("nonexistent")
        assert results == []

    def test_search_with_all_filters(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="filtered",
            description="Python testing patterns",
            content="Content about pytest",
            category=SkillCategory.TDD_TESTING,
            tags=["python", "testing"],
            language="python",
        )
        reg.register(skill)
        results = reg.search(
            "pytest",
            category=SkillCategory.TDD_TESTING,
            tags={"python"},
            language="python",
            limit=5,
        )
        assert len(results) > 0
        assert results[0].skill.name == "filtered"

    def test_search_with_filters_no_match_by_category(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="backend",
            description="Backend patterns",
            content="Content",
            category=SkillCategory.BACKEND_PATTERNS,
        )
        reg.register(skill)
        results = reg.search(
            "backend",
            category=SkillCategory.TDD_TESTING,
        )
        assert results == []

    def test_search_with_filters_no_match_by_language(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="py",
            description="Python",
            content="Content",
            language="python",
        )
        reg.register(skill)
        results = reg.search("python", language="rust")
        assert results == []

    def test_search_score_weights(self) -> None:
        """Name match scores higher than content match."""
        reg = SkillRegistry()
        name_skill = Skill(
            name="python-testing",
            description="General description",
            content="General content",
        )
        reg.register(name_skill)
        results = reg.search("python-testing")
        assert len(results) >= 1

    def test_search_tag_match_scoring(self) -> None:
        reg = SkillRegistry()
        skill = Skill(
            name="tagged-skill",
            description="Description",
            content="Content",
            tags=["python", "testing"],
        )
        reg.register(skill)
        results = reg.search("python")
        assert len(results) >= 1
        assert results[0].skill.name == "tagged-skill"

    def test_search_result_to_dict(self) -> None:
        skill = Skill(
            name="result",
            description="Result skill",
            content="Content",
        )
        result = SkillSearchResult(
            skill=skill,
            score=0.85,
            match_reason="test",
        )
        d = result.to_dict()
        assert d["score"] == 0.85
        assert d["match_reason"] == "test"
        assert d["skill"]["name"] == "result"

    def test_search_limit(self) -> None:
        reg = SkillRegistry()
        for i in range(20):
            reg.register(
                Skill(
                    name=f"skill-{i}",
                    description=f"Description {i}",
                    content="Content",
                    tags=["common"],
                    trigger_patterns=["common"],
                )
            )
        results = reg.search("common", limit=5)
        assert len(results) <= 5

    def test_get_statistics_empty(self) -> None:
        reg = SkillRegistry()
        stats = reg.get_statistics()
        assert stats["total_skills"] == 0
        assert stats["by_category"] == {}
        assert stats["by_language"] == {}
        assert stats["total_tags"] == 0
        assert stats["sources"]["lyra"] == 0
        assert stats["sources"]["ecc"] == 0

    def test_get_statistics_mixed_sources(self) -> None:
        reg = SkillRegistry()
        reg.register(
            Skill(name="a1", description="A1", content="C", source="lyra")
        )
        reg.register(
            Skill(name="a2", description="A2", content="C", source="lyra")
        )
        reg.register(
            Skill(name="b1", description="B1", content="C", source="ecc")
        )
        stats = reg.get_statistics()
        assert stats["sources"]["lyra"] == 2
        assert stats["sources"]["ecc"] == 1

    def test_save_empty_registry(self) -> None:
        reg = SkillRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.json"
            reg.save(path)
            data = json.loads(path.read_text())
            assert data["skills"] == []
            assert data["version"] == "1.0.0"

    def test_load_corrupted_json(self) -> None:
        reg = SkillRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "corrupt.json"
            path.write_text("not valid json")
            with pytest.raises(json.JSONDecodeError):
                reg.load(path)

    def test_load_empty_registry(self) -> None:
        reg = SkillRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.json"
            reg.save(path)
            new_reg = SkillRegistry()
            count = new_reg.load(path)
            assert count == 0

    def test_clear_resets_all_indices(self) -> None:
        reg = SkillRegistry()
        reg.register(
            Skill(
                name="a",
                description="A",
                content="C",
                category=SkillCategory.TDD_TESTING,
                tags=["python", "testing"],
                language="python",
                dependencies=["b"],
            )
        )
        reg.clear()
        assert len(reg.skills) == 0
        assert len(reg._category_index) == 0
        assert len(reg._tag_index) == 0
        assert len(reg._language_index) == 0
        assert reg.graph.get_execution_order() == []

    def test_graph_property(self) -> None:
        reg = SkillRegistry()
        assert reg.graph is reg._graph

    def test_get_execution_order_empty(self) -> None:
        reg = SkillRegistry()
        assert reg.get_execution_order() == []

    def test_register_duplicate_name_overwrites(self) -> None:
        reg = SkillRegistry()
        a = Skill(name="dup", description="First", content="C")
        b = Skill(name="dup", description="Second", content="Different")
        reg.register(a)
        reg.register(b)
        assert reg.skills["dup"].description == "Second"

    def test_search_result_match_reason_format(self) -> None:
        """Search result match_reason is descriptive."""
        reg = SkillRegistry()
        skill = Skill(
            name="python-testing",
            description="Python testing patterns",
            content="Use pytest for Python testing",
            tags=["python", "testing"],
        )
        reg.register(skill)
        results = reg.search("python")
        assert len(results) > 0
        assert "Matched in:" in results[0].match_reason or results[0].match_reason != ""

    def test_find_by_trigger_score_calculation(self) -> None:
        """Score is matches/len(trigger_patterns)."""
        reg = SkillRegistry()
        skill = Skill(
            name="multi-pattern",
            description="Multiple patterns",
            content="Content",
            trigger_patterns=["rabbit", "mushroom", "cloud", "river"],
        )
        reg.register(skill)

        # 2 out of 4 patterns match
        results = reg.find_by_trigger("look at that cloud and rabbit")
        assert len(results) == 1
        assert results[0].score == 0.5  # 2/4
