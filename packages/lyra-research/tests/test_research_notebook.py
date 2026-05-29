"""Tests for ResearchNotebook — Phase 21 Architecture Upgrade Module 2/4."""
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from lyra_research.research_notebook import NotebookEntry, ResearchNotebook


class TestNotebookEntry:
    def test_default_creation(self):
        entry = NotebookEntry()
        assert entry.entry_id
        assert entry.category == "note"
        assert entry.tags == []
        assert entry.sources == []
        assert entry.metrics == {}
        assert isinstance(entry.created_at, datetime)

    def test_full_creation(self):
        entry = NotebookEntry(
            title="Test Entry",
            content="Some content",
            category="finding",
            tags=["important", "verified"],
            sources=["arxiv:1234.5678"],
            metrics={"confidence": 0.95},
            session_id="session-1",
        )
        assert entry.title == "Test Entry"
        assert entry.content == "Some content"
        assert entry.category == "finding"
        assert "important" in entry.tags
        assert entry.metrics["confidence"] == 0.95

    def test_update_changes_content_and_timestamp(self):
        entry = NotebookEntry(content="Original")
        original_updated = entry.updated_at
        entry.update("Modified")
        assert entry.content == "Modified"
        assert entry.updated_at > original_updated

    def test_to_dict(self):
        entry = NotebookEntry(
            title="Serialization Test",
            content="Test content",
            category="decision",
            tags=["t1"],
            session_id="s1",
        )
        d = entry.to_dict()
        assert d["title"] == "Serialization Test"
        assert isinstance(d["created_at"], str)
        assert "t1" in d["tags"]

    def test_roundtrip(self):
        entry = NotebookEntry(
            title="Roundtrip",
            content="Content",
            category="finding",
            tags=["a", "b"],
            sources=["src1"],
            metrics={"m": 1.0},
            session_id="s1",
        )
        restored = NotebookEntry.from_dict(entry.to_dict())
        assert restored.entry_id == entry.entry_id
        assert restored.title == entry.title
        assert restored.category == entry.category
        assert restored.tags == entry.tags
        assert restored.metrics == entry.metrics

    def test_unique_ids(self):
        e1 = NotebookEntry()
        e2 = NotebookEntry()
        assert e1.entry_id != e2.entry_id


class TestResearchNotebookCRUD:
    def test_add_entry(self):
        nb = ResearchNotebook(name="test-nb")
        entry = nb.add_entry(
            title="Test",
            content="Hello",
            category="note",
            tags=["demo"],
        )
        assert nb.entry_count == 1
        assert entry.title == "Test"
        assert entry.content == "Hello"

    def test_get_entry(self):
        nb = ResearchNotebook()
        entry = nb.add_entry(title="Find Me", content="abc")
        found = nb.get_entry(entry.entry_id)
        assert found is not None
        assert found.title == "Find Me"

    def test_get_nonexistent(self):
        nb = ResearchNotebook()
        assert nb.get_entry("nonexistent") is None

    def test_update_entry(self):
        nb = ResearchNotebook()
        entry = nb.add_entry(title="Original", content="old")
        assert nb.update_entry(entry.entry_id, "new content")
        updated = nb.get_entry(entry.entry_id)
        assert updated.content == "new content"

    def test_update_nonexistent(self):
        nb = ResearchNotebook()
        assert nb.update_entry("bad-id", "stuff") is False

    def test_remove_entry(self):
        nb = ResearchNotebook()
        entry = nb.add_entry(title="Remove Me", content="bye")
        assert nb.entry_count == 1
        assert nb.remove_entry(entry.entry_id)
        assert nb.entry_count == 0
        assert nb.get_entry(entry.entry_id) is None

    def test_remove_nonexistent(self):
        nb = ResearchNotebook()
        assert nb.remove_entry("bad-id") is False

    def test_clear_all(self):
        nb = ResearchNotebook()
        nb.add_entry(title="E1", content="c1")
        nb.add_entry(title="E2", content="c2")
        nb.add_entry(title="E3", content="c3")
        assert nb.entry_count == 3
        nb.clear()
        assert nb.entry_count == 0


class TestResearchNotebookQuery:
    @pytest.fixture
    def populated(self):
        nb = ResearchNotebook()
        nb.add_entry(
            title="Finding A", content="Important result",
            category="finding", tags=["critical", "verified"],
            session_id="s1",
        )
        nb.add_entry(
            title="Note B", content="Just a note",
            category="note", tags=["minor"],
            session_id="s1",
        )
        nb.add_entry(
            title="Dead End C", content="Failed approach",
            category="dead_end", tags=["critical", "blocked"],
            session_id="s2",
        )
        nb.add_entry(
            title="Decision D", content="Use strategy X",
            category="decision", tags=["verified"],
            session_id="s2",
        )
        return nb

    def test_get_all(self, populated):
        assert len(populated.get_entries()) == 4

    def test_filter_by_category(self, populated):
        findings = populated.get_entries(category="finding")
        assert len(findings) == 1
        assert findings[0].title == "Finding A"

    def test_filter_by_single_tag(self, populated):
        critical = populated.get_entries(tags=["critical"])
        assert len(critical) == 2

    def test_filter_by_multiple_tags(self, populated):
        result = populated.get_entries(tags=["verified"])
        assert len(result) == 2

    def test_filter_by_session(self, populated):
        s1 = populated.get_entries(session_id="s1")
        assert len(s1) == 2

    def test_filter_by_date_range(self, populated):
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)
        assert len(populated.get_entries(since=past)) == 4
        assert len(populated.get_entries(until=future)) == 4
        assert len(populated.get_entries(since=future)) == 0

    def test_combined_filters(self, populated):
        result = populated.get_entries(
            category="dead_end",
            tags=["critical"],
            session_id="s2",
        )
        assert len(result) == 1
        assert result[0].title == "Dead End C"

    def test_sorted_by_date_desc(self, populated):
        entries = populated.get_entries()
        for i in range(len(entries) - 1):
            assert entries[i].created_at >= entries[i + 1].created_at


class TestResearchNotebookSearch:
    def test_search_title(self):
        nb = ResearchNotebook()
        nb.add_entry(title="Machine Learning Trends", content="...", category="note")
        nb.add_entry(title="Quantum Physics", content="...", category="note")
        results = nb.search("machine")
        assert len(results) == 1
        assert results[0].title == "Machine Learning Trends"

    def test_search_content(self):
        nb = ResearchNotebook()
        nb.add_entry(title="Entry 1", content="Deep reinforcement learning", category="note")
        nb.add_entry(title="Entry 2", content="Supervised classification", category="note")
        results = nb.search("reinforcement")
        assert len(results) == 1

    def test_search_tags(self):
        nb = ResearchNotebook()
        nb.add_entry(title="E1", content="...", tags=["transformer", "attention"])
        nb.add_entry(title="E2", content="...", tags=["cnn", "vision"])
        results = nb.search("transformer")
        assert len(results) == 1

    def test_search_case_insensitive(self):
        nb = ResearchNotebook()
        nb.add_entry(title="Neural Networks", content="...", category="note")
        assert len(nb.search("NEURAL")) == 1
        assert len(nb.search("neural")) == 1

    def test_search_no_match(self):
        nb = ResearchNotebook()
        nb.add_entry(title="Test", content="abc", category="note")
        assert len(nb.search("nonexistent")) == 0

    def test_search_multiple_matches(self):
        nb = ResearchNotebook()
        nb.add_entry(title="Python Guide", content="Python programming", category="note")
        nb.add_entry(title="Python Libraries", content="ML with Python", category="finding")
        assert len(nb.search("python")) == 2


class TestResearchNotebookStats:
    def test_categories(self):
        nb = ResearchNotebook()
        nb.add_entry(title="E1", content="...", category="finding")
        nb.add_entry(title="E2", content="...", category="note")
        nb.add_entry(title="E3", content="...", category="finding")
        cats = nb.get_categories()
        assert "finding" in cats
        assert "note" in cats
        assert len(cats) == 2

    def test_tags(self):
        nb = ResearchNotebook()
        nb.add_entry(title="E1", content="...", tags=["ml", "nlp"])
        nb.add_entry(title="E2", content="...", tags=["ml", "vision"])
        tags = nb.get_tags()
        assert "ml" in tags
        assert "nlp" in tags
        assert "vision" in tags

    def test_count_by_category(self):
        nb = ResearchNotebook()
        nb.add_entry(title="E1", content="...", category="finding")
        nb.add_entry(title="E2", content="...", category="finding")
        nb.add_entry(title="E3", content="...", category="dead_end")
        counts = nb.count_by_category()
        assert counts["finding"] == 2
        assert counts["dead_end"] == 1

    def test_count_by_tag(self):
        nb = ResearchNotebook()
        nb.add_entry(title="E1", content="...", tags=["ml", "nlp"])
        nb.add_entry(title="E2", content="...", tags=["ml"])
        counts = nb.count_by_tag()
        assert counts["ml"] == 2
        assert counts["nlp"] == 1

    def test_entry_count_property(self):
        nb = ResearchNotebook()
        assert nb.entry_count == 0
        nb.add_entry(title="Test", content="...")
        assert nb.entry_count == 1


class TestResearchNotebookExport:
    def test_export_json(self):
        nb = ResearchNotebook(name="test-nb")
        nb.add_entry(title="Entry 1", content="Content 1", category="note")
        data = json.loads(nb.export_json())
        assert data["name"] == "test-nb"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["title"] == "Entry 1"

    def test_export_markdown(self):
        nb = ResearchNotebook(name="research-journal")
        nb.add_entry(
            title="Key Finding",
            content="We discovered X leads to Y.",
            category="finding",
            tags=["important"],
            sources=["arxiv:9999.9999"],
        )
        md = nb.export_markdown()
        assert "# research-journal" in md
        assert "## Finding" in md
        assert "### Key Finding" in md
        assert "We discovered X leads to Y." in md
        assert "arxiv:9999.9999" in md

    def test_export_empty(self):
        nb = ResearchNotebook(name="empty")
        data = json.loads(nb.export_json())
        assert len(data["entries"]) == 0


class TestResearchNotebookPersistence:
    def test_save_and_load(self):
        nb = ResearchNotebook(name="persist-test")
        nb.add_entry(
            title="Persisted Entry",
            content="This should survive roundtrip.",
            category="finding",
            tags=["persist"],
            session_id="s1",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notebook.json"
            nb.save(path)
            assert path.exists()

            loaded = ResearchNotebook.load(path)
            assert loaded.name == "persist-test"
            assert loaded.entry_count == 1
            entry = loaded.get_entries()[0]
            assert entry.title == "Persisted Entry"
            assert entry.content == "This should survive roundtrip."
            assert "persist" in entry.tags

    def test_save_creates_parent_dirs(self):
        nb = ResearchNotebook(name="deep")
        nb.add_entry(title="Test", content="...")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a" / "b" / "c" / "notebook.json"
            nb.save(path)
            assert path.exists()

    def test_load_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonexistent.json"
            with pytest.raises(FileNotFoundError):
                ResearchNotebook.load(path)


class TestResearchNotebookMerge:
    def test_merge_combines_entries(self):
        nb1 = ResearchNotebook()
        e1 = nb1.add_entry(title="From NB1", content="...")

        nb2 = ResearchNotebook()
        e2 = nb2.add_entry(title="From NB2", content="...")

        nb1.merge(nb2)
        assert nb1.entry_count == 2
        assert nb1.get_entry(e1.entry_id) is not None
        assert nb1.get_entry(e2.entry_id) is not None

    def test_merge_deduplicates(self):
        nb1 = ResearchNotebook()
        e1 = nb1.add_entry(title="Shared", content="from nb1")

        nb2 = ResearchNotebook()
        nb2._entries[e1.entry_id] = e1  # Force same ID
        nb2.add_entry(title="Unique", content="from nb2")

        nb1.merge(nb2)
        assert nb1.entry_count == 2  # Shared + Unique


class TestResearchNotebookName:
    def test_default_name(self):
        nb = ResearchNotebook()
        assert nb.name == "research-notebook"

    def test_custom_name(self):
        nb = ResearchNotebook(name="my-journal")
        assert nb.name == "my-journal"
