"""
Episodic Memory Tier - MEMTIER Implementation

Append-only JSONL log of per-session events. This is the first tier
of the MEMTIER 3-tier memory architecture.

Based on research: docs/151-153 (MEMTIER papers)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import os


@dataclass
class EpisodicEntry:
    """Single episodic memory entry."""
    id: str
    timestamp: datetime
    session_id: str
    project: str
    event_type: str  # "user_input", "tool_call", "agent_response", "error"
    content: str
    tokens: int
    metadata: Dict[str, Any]
    promoted: bool = False  # Promoted to semantic tier
    cognitive_weight: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'EpisodicEntry':
        """Create from dictionary."""
        d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        return cls(**d)


class EpisodicMemory:
    """
    Episodic memory tier: append-only JSONL log.

    Stores per-session events in daily JSONL files for efficient
    append and sequential read operations.
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        """
        Initialize episodic memory.

        Args:
            memory_dir: Base directory for memory storage
                       (default: ~/.lyra/memory/episodic/)
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".lyra" / "memory" / "episodic"

        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _get_daily_file(self, date: Optional[datetime] = None) -> Path:
        """Get JSONL file path for a specific date."""
        if date is None:
            date = datetime.now()

        filename = date.strftime("%Y-%m-%d.jsonl")
        return self.memory_dir / filename

    def append(self, entry: EpisodicEntry) -> None:
        """
        Append an entry to episodic memory.

        Args:
            entry: EpisodicEntry to store
        """
        daily_file = self._get_daily_file(entry.timestamp)

        with open(daily_file, 'a') as f:
            json.dump(entry.to_dict(), f)
            f.write('\n')

    def append_event(
        self,
        session_id: str,
        project: str,
        event_type: str,
        content: str,
        tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EpisodicEntry:
        """
        Convenience method to create and append an event.

        Args:
            session_id: Session identifier
            project: Project name
            event_type: Type of event
            content: Event content
            tokens: Token count
            metadata: Additional metadata

        Returns:
            Created EpisodicEntry
        """
        import uuid

        entry = EpisodicEntry(
            id=f"ep_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            session_id=session_id,
            project=project,
            event_type=event_type,
            content=content,
            tokens=tokens,
            metadata=metadata or {},
            promoted=False,
            cognitive_weight=0.0
        )

        self.append(entry)
        return entry

    def read_day(self, date: datetime) -> List[EpisodicEntry]:
        """
        Read all entries for a specific day.

        Args:
            date: Date to read

        Returns:
            List of EpisodicEntry objects
        """
        daily_file = self._get_daily_file(date)

        if not daily_file.exists():
            return []

        entries = []
        with open(daily_file, 'r') as f:
            for line in f:
                if line.strip():
                    entry_dict = json.loads(line)
                    entries.append(EpisodicEntry.from_dict(entry_dict))

        return entries

    def read_session(self, session_id: str) -> List[EpisodicEntry]:
        """
        Read all entries for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            List of EpisodicEntry objects for this session
        """
        entries = []

        # Scan all daily files (could be optimized with index)
        for daily_file in sorted(self.memory_dir.glob("*.jsonl")):
            with open(daily_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry_dict = json.loads(line)
                        if entry_dict['session_id'] == session_id:
                            entries.append(EpisodicEntry.from_dict(entry_dict))

        return entries

    def read_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[EpisodicEntry]:
        """
        Read entries within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of EpisodicEntry objects
        """
        entries = []
        current_date = start_date

        while current_date <= end_date:
            entries.extend(self.read_day(current_date))
            current_date = current_date.replace(
                day=current_date.day + 1
            )

        return entries

    def mark_promoted(self, entry_id: str) -> bool:
        """
        Mark an entry as promoted to semantic tier.

        Note: This requires rewriting the daily file. For production,
        consider using a separate index file.

        Args:
            entry_id: Entry ID to mark

        Returns:
            True if entry was found and marked
        """
        # Find the entry
        for daily_file in self.memory_dir.glob("*.jsonl"):
            entries = []
            found = False

            with open(daily_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry_dict = json.loads(line)
                        if entry_dict['id'] == entry_id:
                            entry_dict['promoted'] = True
                            found = True
                        entries.append(entry_dict)

            if found:
                # Rewrite file
                with open(daily_file, 'w') as f:
                    for entry_dict in entries:
                        json.dump(entry_dict, f)
                        f.write('\n')
                return True

        return False

    def get_unpromoted_entries(
        self,
        limit: Optional[int] = None
    ) -> List[EpisodicEntry]:
        """
        Get entries that haven't been promoted to semantic tier.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of unpromoted EpisodicEntry objects
        """
        entries = []

        for daily_file in sorted(self.memory_dir.glob("*.jsonl")):
            with open(daily_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry_dict = json.loads(line)
                        if not entry_dict.get('promoted', False):
                            entries.append(EpisodicEntry.from_dict(entry_dict))

                            if limit and len(entries) >= limit:
                                return entries

        return entries

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about episodic memory."""
        total_entries = 0
        total_tokens = 0
        promoted_count = 0
        event_types = {}

        for daily_file in self.memory_dir.glob("*.jsonl"):
            with open(daily_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry_dict = json.loads(line)
                        total_entries += 1
                        total_tokens += entry_dict.get('tokens', 0)

                        if entry_dict.get('promoted', False):
                            promoted_count += 1

                        event_type = entry_dict.get('event_type', 'unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1

        return {
            'total_entries': total_entries,
            'total_tokens': total_tokens,
            'promoted_count': promoted_count,
            'unpromoted_count': total_entries - promoted_count,
            'event_types': event_types,
            'daily_files': len(list(self.memory_dir.glob("*.jsonl")))
        }
