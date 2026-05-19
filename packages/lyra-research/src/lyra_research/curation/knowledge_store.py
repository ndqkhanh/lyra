"""Knowledge Store — Persistent storage for curated knowledge."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from lyra_research.curation.knowledge_entry import EntryStatus, KnowledgeEntry


class KnowledgeStore:
    """
    Persistent storage for knowledge entries.

    Provides storage, retrieval, and search functionality for approved
    knowledge entries.
    """

    def __init__(self, storage_path: Path) -> None:
        """
        Initialize knowledge store.

        Args:
            storage_path: Path to storage directory
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self.entries: Dict[str, KnowledgeEntry] = {}

        # Load existing entries
        self._load_entries()

    def _load_entries(self) -> None:
        """Load entries from disk into memory."""
        for entry_file in self.storage_path.glob("*.json"):
            try:
                with open(entry_file, "r") as f:
                    data = json.load(f)
                    entry = KnowledgeEntry.from_dict(data)
                    self.entries[entry.id] = entry
            except Exception:
                # Skip corrupted files
                continue

    def _get_entry_path(self, entry_id: str) -> Path:
        """
        Get file path for entry.

        Args:
            entry_id: Entry ID

        Returns:
            Path to entry file
        """
        return self.storage_path / f"{entry_id}.json"

    def store(self, entry: KnowledgeEntry) -> None:
        """
        Store approved entry.

        Args:
            entry: Knowledge entry to store

        Raises:
            ValueError: If entry is not approved
        """
        if entry.status != EntryStatus.APPROVED:
            raise ValueError("Only approved entries can be stored")

        # Store in memory
        self.entries[entry.id] = entry

        # Persist to disk
        entry_path = self._get_entry_path(entry.id)
        with open(entry_path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

    def retrieve(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """
        Retrieve entry by ID.

        Args:
            entry_id: Entry ID

        Returns:
            KnowledgeEntry if found, None otherwise
        """
        return self.entries.get(entry_id)

    def search(
        self, query: str, category: Optional[str] = None
    ) -> List[KnowledgeEntry]:
        """
        Search entries by query and optional category.

        Args:
            query: Search query (matches content, source, tags)
            category: Optional category filter

        Returns:
            List of matching KnowledgeEntry
        """
        query_lower = query.lower()
        results = []

        for entry in self.entries.values():
            # Category filter
            if category and entry.category != category:
                continue

            # Search in content, source, and tags
            if (
                query_lower in entry.content.lower()
                or query_lower in entry.source.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)

        # Sort by quality score (descending)
        return sorted(results, key=lambda e: e.quality_score, reverse=True)

    def get_by_category(self, category: str) -> List[KnowledgeEntry]:
        """
        Get all entries in category.

        Args:
            category: Category name

        Returns:
            List of KnowledgeEntry in category
        """
        results = [e for e in self.entries.values() if e.category == category]

        # Sort by quality score (descending)
        return sorted(results, key=lambda e: e.quality_score, reverse=True)

    def get_by_tag(self, tag: str) -> List[KnowledgeEntry]:
        """
        Get all entries with tag.

        Args:
            tag: Tag name

        Returns:
            List of KnowledgeEntry with tag
        """
        results = [e for e in self.entries.values() if tag in e.tags]

        # Sort by quality score (descending)
        return sorted(results, key=lambda e: e.quality_score, reverse=True)

    def get_all(self) -> List[KnowledgeEntry]:
        """
        Get all entries.

        Returns:
            List of all KnowledgeEntry
        """
        return sorted(self.entries.values(), key=lambda e: e.quality_score, reverse=True)

    def delete(self, entry_id: str) -> bool:
        """
        Delete entry by ID.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted, False if not found
        """
        if entry_id not in self.entries:
            return False

        # Remove from memory
        del self.entries[entry_id]

        # Remove from disk
        entry_path = self._get_entry_path(entry_id)
        if entry_path.exists():
            entry_path.unlink()

        return True

    def count(self) -> int:
        """
        Get total number of entries.

        Returns:
            Number of entries
        """
        return len(self.entries)

    def get_categories(self) -> List[str]:
        """
        Get all unique categories.

        Returns:
            List of category names
        """
        return sorted(set(e.category for e in self.entries.values()))

    def get_tags(self) -> List[str]:
        """
        Get all unique tags.

        Returns:
            List of tag names
        """
        tags = set()
        for entry in self.entries.values():
            tags.update(entry.tags)
        return sorted(tags)
