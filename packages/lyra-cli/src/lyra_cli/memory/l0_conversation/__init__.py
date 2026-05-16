"""
L0 Conversation Layer - Raw dialogue storage with JSONL shards.

Features:
- Daily partitioned JSONL files for append-only logs
- Full-text search over conversation history
- 90-day retention policy (configurable)
- Efficient drill-down for evidence retrieval
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationLog:
    """Single conversation turn."""

    session_id: str
    turn_id: int
    timestamp: str
    role: str  # 'user' or 'assistant'
    content: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationLog":
        """Create from dictionary."""
        return cls(**data)


class ConversationStore:
    """
    L0 storage layer using daily-partitioned JSONL shards.

    Directory structure:
        data/l0_conversations/
            2026-05-16.jsonl
            2026-05-17.jsonl
            ...
    """

    def __init__(
        self,
        data_dir: str = "./data/l0_conversations",
        retention_days: int = 90,
    ):
        self.data_dir = Path(data_dir)
        self.retention_days = retention_days
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Initialized L0 ConversationStore at {self.data_dir} "
            f"with {retention_days}-day retention"
        )

    def _get_shard_path(self, date: datetime) -> Path:
        """Get JSONL shard path for a given date."""
        return self.data_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"

    def append(self, log: ConversationLog) -> None:
        """
        Append a conversation log to today's shard.

        Args:
            log: ConversationLog to append
        """
        shard_path = self._get_shard_path(datetime.now())

        try:
            with open(shard_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log.to_dict(), ensure_ascii=False) + "\n")

            logger.debug(
                f"Appended turn {log.turn_id} to shard {shard_path.name}"
            )
        except Exception as e:
            logger.error(f"Failed to append to L0: {e}")
            raise

    def get_session(
        self,
        session_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[ConversationLog]:
        """
        Retrieve all logs for a session within date range.

        Args:
            session_id: Session identifier
            start_date: Start date (default: 90 days ago)
            end_date: End date (default: today)

        Returns:
            List of ConversationLog entries, sorted by turn_id
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=self.retention_days)
        if end_date is None:
            end_date = datetime.now()

        logs = []
        current_date = start_date

        while current_date <= end_date:
            shard_path = self._get_shard_path(current_date)

            if shard_path.exists():
                try:
                    with open(shard_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                if data.get("session_id") == session_id:
                                    logs.append(ConversationLog.from_dict(data))
                except Exception as e:
                    logger.warning(
                        f"Failed to read shard {shard_path.name}: {e}"
                    )

            current_date += timedelta(days=1)

        # Sort by turn_id
        logs.sort(key=lambda x: x.turn_id)

        logger.info(
            f"Retrieved {len(logs)} logs for session {session_id}"
        )
        return logs

    def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        max_results: int = 50,
    ) -> List[ConversationLog]:
        """
        Full-text search over conversation history.

        Args:
            query: Search query string
            session_id: Optional session filter
            max_results: Maximum results to return

        Returns:
            List of matching ConversationLog entries
        """
        query_lower = query.lower()
        matches = []

        # Search recent shards (last 30 days for performance)
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        current_date = start_date

        while current_date <= end_date and len(matches) < max_results:
            shard_path = self._get_shard_path(current_date)

            if shard_path.exists():
                try:
                    with open(shard_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)

                                # Session filter
                                if session_id and data.get("session_id") != session_id:
                                    continue

                                # Full-text match
                                content = data.get("content", "").lower()
                                if query_lower in content:
                                    matches.append(ConversationLog.from_dict(data))

                                    if len(matches) >= max_results:
                                        break
                except Exception as e:
                    logger.warning(
                        f"Failed to search shard {shard_path.name}: {e}"
                    )

            current_date += timedelta(days=1)

        logger.info(
            f"Found {len(matches)} matches for query: {query[:50]}..."
        )
        return matches

    def cleanup_old_shards(self) -> int:
        """
        Remove shards older than retention period.

        Returns:
            Number of shards deleted
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0

        for shard_path in self.data_dir.glob("*.jsonl"):
            try:
                # Parse date from filename (YYYY-MM-DD.jsonl)
                date_str = shard_path.stem
                shard_date = datetime.strptime(date_str, "%Y-%m-%d")

                if shard_date < cutoff_date:
                    shard_path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old shard: {shard_path.name}")
            except Exception as e:
                logger.warning(
                    f"Failed to process shard {shard_path.name}: {e}"
                )

        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} shards older than "
                f"{self.retention_days} days"
            )

        return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with stats (shard_count, total_size_mb, oldest_shard, etc.)
        """
        shards = list(self.data_dir.glob("*.jsonl"))
        total_size = sum(s.stat().st_size for s in shards)

        oldest_shard = None
        newest_shard = None

        if shards:
            shard_dates = []
            for shard in shards:
                try:
                    date_str = shard.stem
                    shard_date = datetime.strptime(date_str, "%Y-%m-%d")
                    shard_dates.append(shard_date)
                except:
                    pass

            if shard_dates:
                oldest_shard = min(shard_dates).strftime("%Y-%m-%d")
                newest_shard = max(shard_dates).strftime("%Y-%m-%d")

        return {
            "shard_count": len(shards),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_shard": oldest_shard,
            "newest_shard": newest_shard,
            "retention_days": self.retention_days,
            "data_dir": str(self.data_dir),
        }
