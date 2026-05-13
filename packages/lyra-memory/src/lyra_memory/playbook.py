"""
ACE-style evolving playbook for context management.

Implements the generate-reflect-curate loop:
1. Generate: Try to solve task with current playbook
2. Reflect: Extract lessons from attempt
3. Curate: Update playbook with new entries
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class PlaybookEntry:
    """
    A single entry in the context playbook.

    Represents a reusable pattern, strategy, or lesson.
    """
    id: str
    title: str
    content: str
    category: str  # "pattern", "strategy", "lesson", "constraint"
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0
    success_rate: float = 1.0
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
            "success_rate": self.success_rate,
            "confidence": self.confidence,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybookEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            category=data["category"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            use_count=data.get("use_count", 0),
            success_rate=data.get("success_rate", 1.0),
            confidence=data.get("confidence", 1.0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class ContextPlaybook:
    """
    ACE-style evolving playbook for context management.

    Maintains a collection of reusable patterns, strategies, and lessons
    that improve over time through the generate-reflect-curate loop.
    """

    def __init__(self, playbook_path: Path):
        """
        Initialize playbook.

        Args:
            playbook_path: Path to playbook JSON file
        """
        self.playbook_path = playbook_path
        self.entries: Dict[str, PlaybookEntry] = {}
        self._load()

    def generate_context(self, task: str, max_entries: int = 5) -> str:
        """
        Generate context for a task using relevant playbook entries.

        Args:
            task: Task description
            max_entries: Maximum entries to include

        Returns:
            Formatted context string
        """
        # Find relevant entries
        relevant = self._find_relevant(task, limit=max_entries)

        if not relevant:
            return ""

        # Format context
        lines = ["# Context Playbook\n"]
        for entry in relevant:
            lines.append(f"## {entry.title}")
            lines.append(f"{entry.content}\n")

            # Update usage stats
            entry.last_used = datetime.now()
            entry.use_count += 1

        self._save()
        return "\n".join(lines)

    def reflect(self, task: str, attempt: str, outcome: Dict[str, Any]) -> List[PlaybookEntry]:
        """
        Reflect on an attempt and extract lessons.

        Args:
            task: Task description
            attempt: What was attempted
            outcome: Result (success, error, metrics, etc.)

        Returns:
            List of extracted playbook entries
        """
        entries = []

        # Extract success patterns
        if outcome.get("success"):
            entry = self._extract_success_pattern(task, attempt, outcome)
            if entry:
                entries.append(entry)

        # Extract failure lessons
        else:
            entry = self._extract_failure_lesson(task, attempt, outcome)
            if entry:
                entries.append(entry)

        return entries

    def curate(self, new_entries: List[PlaybookEntry]) -> None:
        """
        Curate playbook by adding or updating entries.

        Args:
            new_entries: New entries to add
        """
        for entry in new_entries:
            # Check if similar entry exists
            similar = self._find_similar(entry)

            if similar:
                # Update existing entry
                self._merge_entries(similar, entry)
            else:
                # Add new entry
                self.entries[entry.id] = entry

        # Prune low-quality entries
        self._prune()

        # Save
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get playbook statistics."""
        return {
            "total_entries": len(self.entries),
            "by_category": self._count_by_category(),
            "avg_success_rate": self._avg_success_rate(),
            "most_used": self._most_used(5),
        }

    def _find_relevant(self, task: str, limit: int) -> List[PlaybookEntry]:
        """Find relevant entries for a task."""
        # Simple keyword matching (can be enhanced with embeddings)
        task_lower = task.lower()
        scored = []

        for entry in self.entries.values():
            score = 0.0

            # Match tags
            for tag in entry.tags:
                if tag.lower() in task_lower:
                    score += 2.0

            # Match title
            if any(word in task_lower for word in entry.title.lower().split()):
                score += 1.0

            # Weight by success rate and confidence
            score *= entry.success_rate * entry.confidence

            if score > 0:
                scored.append((entry, score))

        # Sort by score and return top-k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored[:limit]]

    def _find_similar(self, entry: PlaybookEntry) -> Optional[PlaybookEntry]:
        """Find similar existing entry."""
        for existing in self.entries.values():
            # Same category and overlapping tags
            if existing.category == entry.category:
                common_tags = set(existing.tags) & set(entry.tags)
                if len(common_tags) >= 2:
                    return existing
        return None

    def _merge_entries(self, existing: PlaybookEntry, new: PlaybookEntry) -> None:
        """Merge new entry into existing."""
        # Update success rate (weighted average)
        total_uses = existing.use_count + 1
        existing.success_rate = (
            existing.success_rate * existing.use_count + new.success_rate
        ) / total_uses

        # Merge tags
        existing.tags = list(set(existing.tags + new.tags))

        # Update confidence
        existing.confidence = max(existing.confidence, new.confidence)

    def _extract_success_pattern(
        self,
        task: str,
        attempt: str,
        outcome: Dict[str, Any]
    ) -> Optional[PlaybookEntry]:
        """Extract a success pattern from a successful attempt."""
        # Simple extraction (can be enhanced with LLM)
        return PlaybookEntry(
            id=f"success_{datetime.now().timestamp()}",
            title=f"Success: {task[:50]}",
            content=f"Approach: {attempt[:200]}\nResult: {outcome.get('result', 'Success')}",
            category="pattern",
            created_at=datetime.now(),
            tags=self._extract_tags(task),
            confidence=0.8,
        )

    def _extract_failure_lesson(
        self,
        task: str,
        attempt: str,
        outcome: Dict[str, Any]
    ) -> Optional[PlaybookEntry]:
        """Extract a lesson from a failed attempt."""
        error = outcome.get("error", "Unknown error")
        return PlaybookEntry(
            id=f"failure_{datetime.now().timestamp()}",
            title=f"Avoid: {error[:50]}",
            content=f"Task: {task[:100]}\nAttempt: {attempt[:200]}\nError: {error}",
            category="lesson",
            created_at=datetime.now(),
            tags=self._extract_tags(task) + ["failure"],
            confidence=0.9,  # High confidence for failures
        )

    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text."""
        # Simple keyword extraction
        keywords = ["python", "test", "file", "api", "database", "memory", "skill"]
        return [kw for kw in keywords if kw in text.lower()]

    def _prune(self) -> None:
        """Remove low-quality entries."""
        to_remove = []

        for entry_id, entry in self.entries.items():
            # Remove if:
            # - Low success rate and high use count
            # - Very low confidence
            if (entry.success_rate < 0.3 and entry.use_count > 5) or entry.confidence < 0.2:
                to_remove.append(entry_id)

        for entry_id in to_remove:
            del self.entries[entry_id]

    def _count_by_category(self) -> Dict[str, int]:
        """Count entries by category."""
        counts = {}
        for entry in self.entries.values():
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    def _avg_success_rate(self) -> float:
        """Calculate average success rate."""
        if not self.entries:
            return 0.0
        return sum(e.success_rate for e in self.entries.values()) / len(self.entries)

    def _most_used(self, limit: int) -> List[Dict[str, Any]]:
        """Get most used entries."""
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.use_count,
            reverse=True
        )[:limit]

        return [
            {"title": e.title, "use_count": e.use_count, "success_rate": e.success_rate}
            for e in sorted_entries
        ]

    def _load(self) -> None:
        """Load playbook from disk."""
        if not self.playbook_path.exists():
            return

        with open(self.playbook_path) as f:
            data = json.load(f)

        self.entries = {
            entry_id: PlaybookEntry.from_dict(entry_data)
            for entry_id, entry_data in data.items()
        }

    def _save(self) -> None:
        """Save playbook to disk."""
        self.playbook_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            entry_id: entry.to_dict()
            for entry_id, entry in self.entries.items()
        }

        with open(self.playbook_path, "w") as f:
            json.dump(data, f, indent=2)
