"""Persistent Research Notebook — chronological research journal with search and export.

Tracks research sessions over time with entries categorized by type, taggable,
full-text searchable, and exportable to JSON/Markdown.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class NotebookEntry:
    """A single notebook entry documenting a research observation or result."""

    entry_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    title: str = ""
    content: str = ""
    category: str = "note"  # note, finding, gap, dead_end, decision, summary
    tags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, content: str) -> None:
        """Update the entry content and timestamp."""
        self.content = content
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "entry_id": self.entry_id,
            "session_id": self.session_id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "sources": self.sources,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotebookEntry:
        """Create from dict."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class ResearchNotebook:
    """Persistent research journal with full-text search and export.

    Features:
    - Chronological entries with categories and tags
    - Full-text search across titles and content
    - Filter by category, tags, date range, session
    - Export to JSON or Markdown
    - Persist/load to/from disk
    """

    def __init__(self, name: str = "research-notebook") -> None:
        self.name = name
        self._entries: dict[str, NotebookEntry] = {}
        self._created_at = datetime.now(timezone.utc)

    # ── CRUD ──────────────────────────────────────────────────────────────

    def add_entry(
        self,
        title: str,
        content: str,
        category: str = "note",
        tags: list[str] | None = None,
        sources: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        session_id: str = "",
    ) -> NotebookEntry:
        """Add a new entry to the notebook."""
        entry = NotebookEntry(
            session_id=session_id,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            sources=sources or [],
            metrics=metrics or {},
        )
        self._entries[entry.entry_id] = entry
        return entry

    def get_entry(self, entry_id: str) -> NotebookEntry | None:
        """Get an entry by ID."""
        return self._entries.get(entry_id)

    def update_entry(self, entry_id: str, content: str) -> bool:
        """Update an existing entry. Returns True if found."""
        entry = self._entries.get(entry_id)
        if entry is None:
            return False
        entry.update(content)
        return True

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry. Returns True if found and removed."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    # ── Query ──────────────────────────────────────────────────────────────

    def get_entries(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[NotebookEntry]:
        """Get entries filtered by criteria."""
        results = list(self._entries.values())

        if category:
            results = [e for e in results if e.category == category]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        if session_id:
            results = [e for e in results if e.session_id == session_id]
        if since:
            results = [e for e in results if e.created_at >= since]
        if until:
            results = [e for e in results if e.created_at <= until]

        return sorted(results, key=lambda e: e.created_at, reverse=True)

    def search(self, query: str) -> list[NotebookEntry]:
        """Full-text search across titles and content."""
        query_lower = query.lower()
        results = []
        for entry in self._entries.values():
            if (query_lower in entry.title.lower()
                    or query_lower in entry.content.lower()
                    or any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)
        return sorted(results, key=lambda e: e.created_at, reverse=True)

    def get_categories(self) -> list[str]:
        """Get all unique categories used in the notebook."""
        return sorted({e.category for e in self._entries.values()})

    def get_tags(self) -> list[str]:
        """Get all unique tags used in the notebook."""
        all_tags: set[str] = set()
        for entry in self._entries.values():
            all_tags.update(entry.tags)
        return sorted(all_tags)

    # ── Stats ──────────────────────────────────────────────────────────────

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def count_by_category(self) -> dict[str, int]:
        """Count entries by category."""
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    def count_by_tag(self) -> dict[str, int]:
        """Count entries by tag."""
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            for tag in entry.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    # ── Export ─────────────────────────────────────────────────────────────

    def export_json(self) -> str:
        """Export notebook as JSON string."""
        data = {
            "name": self.name,
            "created_at": self._created_at.isoformat(),
            "entries": [e.to_dict() for e in sorted(
                self._entries.values(), key=lambda e: e.created_at,
            )],
        }
        return json.dumps(data, indent=2)

    def export_markdown(self) -> str:
        """Export notebook as Markdown string."""
        lines = [f"# {self.name}", "",
                 f"Created: {self._created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                 f"Entries: {self.entry_count}", ""]

        current_category = None
        for entry in sorted(self._entries.values(), key=lambda e: e.created_at):
            if entry.category != current_category:
                current_category = entry.category
                lines.append(f"## {current_category.title()}")
                lines.append("")

            lines.append(f"### {entry.title}")
            lines.append(f"*{entry.created_at.strftime('%Y-%m-%d %H:%M')}*")
            if entry.tags:
                lines.append(f"Tags: {', '.join(entry.tags)}")
            lines.append("")
            lines.append(entry.content)
            lines.append("")
            if entry.sources:
                lines.append("Sources:")
                for src in entry.sources:
                    lines.append(f"- {src}")
                lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    # ── Persistence ────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """Save notebook to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.export_json())

    @classmethod
    def load(cls, path: Path) -> ResearchNotebook:
        """Load notebook from a JSON file."""
        data = json.loads(path.read_text())
        nb = cls(name=data["name"])
        nb._created_at = datetime.fromisoformat(data["created_at"])
        for entry_data in data.get("entries", []):
            entry = NotebookEntry.from_dict(entry_data)
            nb._entries[entry.entry_id] = entry
        return nb

    # ── Merge ──────────────────────────────────────────────────────────────

    def merge(self, other: ResearchNotebook) -> None:
        """Merge entries from another notebook (deduplicates by entry_id)."""
        for entry_id, entry in other._entries.items():
            if entry_id not in self._entries:
                self._entries[entry_id] = entry

    def clear(self) -> None:
        """Remove all entries."""
        self._entries.clear()


__all__ = [
    "NotebookEntry",
    "ResearchNotebook",
]
