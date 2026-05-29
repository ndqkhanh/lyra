"""Tests for memory operations tools."""
from __future__ import annotations

from lyra_tools.memory_ops import (
    memory_delete,
    memory_list,
    memory_retrieve,
    memory_save,
    memory_search,
)


class TestMemorySave:
    def test_save_with_all_fields(self):
        result = memory_save(
            content="Important project decision",
            title="Architecture Decision",
            tags=["architecture", "decision"],
            project="lyra",
            priority="high",
        )

        assert result["saved"] is True
        assert result["title"] == "Architecture Decision"
        assert result["content"] == "Important project decision"
        assert result["tags"] == ["architecture", "decision"]
        assert result["project"] == "lyra"
        assert result["priority"] == "high"
        assert "id" in result
        assert "created_at" in result

    def test_save_minimal(self):
        result = memory_save(content="Quick note")

        assert result["saved"] is True
        assert result["title"] == "Quick note"
        assert result["tags"] == []
        assert result["project"] == "default"
        assert result["priority"] == "normal"

    def test_save_auto_title_truncation(self):
        long_content = "a" * 100
        result = memory_save(content=long_content)

        assert result["saved"] is True
        assert len(result["title"]) == 53  # 50 chars + "..."
        assert result["title"].endswith("...")

    def test_save_empty_content_errors(self):
        result = memory_save(content="")

        assert result["saved"] is False
        assert "error" in result

    def test_save_whitespace_only_errors(self):
        result = memory_save(content="   ")

        assert result["saved"] is False
        assert "error" in result

    def test_save_invalid_priority_errors(self):
        result = memory_save(content="test", priority="invalid")

        assert result["saved"] is False
        assert "error" in result
        assert "priority" in result["error"]


class TestMemorySearch:
    def test_search_basic(self):
        result = memory_search(query="architecture decisions")

        assert "results" in result
        assert "query" in result
        assert result["query"] == "architecture decisions"
        assert "count" in result
        assert "limit" in result

    def test_search_with_filters(self):
        result = memory_search(
            query="test",
            project="lyra",
            tags=["bug", "fix"],
            limit=5,
            min_score=0.7,
        )

        assert result["project"] == "lyra"
        assert result["tags"] == ["bug", "fix"]
        assert result["limit"] == 5

    def test_search_empty_query_errors(self):
        result = memory_search(query="")

        assert "error" in result
        assert result["results"] == []

    def test_search_invalid_min_score_errors(self):
        result = memory_search(query="test", min_score=1.5)

        assert "error" in result
        assert "min_score" in result["error"]


class TestMemoryRetrieve:
    def test_retrieve_not_found(self):
        result = memory_retrieve(memory_id="nonexistent")

        assert result["found"] is False
        assert "error" in result

    def test_retrieve_empty_id_errors(self):
        result = memory_retrieve(memory_id="")

        assert result["found"] is False
        assert "error" in result


class TestMemoryDelete:
    def test_delete_requires_confirmation(self):
        result = memory_delete(memory_id="test_id")

        assert result["deleted"] is False
        assert "error" in result
        assert "confirm" in result["error"]

    def test_delete_with_confirmation(self):
        result = memory_delete(memory_id="test_id", confirm=True)

        # Will fail because memory doesn't exist, but confirmation passed
        assert "deleted" in result

    def test_delete_empty_id_errors(self):
        result = memory_delete(memory_id="", confirm=True)

        assert result["deleted"] is False
        assert "error" in result


class TestMemoryList:
    def test_list_no_filters(self):
        result = memory_list()

        assert "memories" in result
        assert "count" in result
        assert "limit" in result
        assert "offset" in result
        assert "total" in result

    def test_list_with_filters(self):
        result = memory_list(
            project="lyra",
            tags=["bug"],
            priority="high",
            limit=20,
            offset=10,
        )

        assert result["project"] == "lyra"
        assert result["tags"] == ["bug"]
        assert result["priority"] == "high"
        assert result["limit"] == 20
        assert result["offset"] == 10

    def test_list_invalid_priority_errors(self):
        result = memory_list(priority="invalid")

        assert "error" in result
        assert "priority" in result["error"]
