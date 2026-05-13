"""
Memory viewer UI for Lyra TUI sidebar.

Displays recent memories, search interface, and statistics.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from lyra_memory.store import MemoryStore
from lyra_memory.schema import MemoryScope, MemoryType


class MemoryViewerData:
    """Data provider for memory viewer UI."""

    def __init__(self, store: MemoryStore):
        """
        Initialize memory viewer.

        Args:
            store: Memory store instance
        """
        self.store = store

    def get_recent_memories(self, limit: int = 10) -> List[dict]:
        """
        Get recent memories for display.

        Args:
            limit: Maximum memories to return

        Returns:
            List of memory dictionaries
        """
        memories = self.store.db.get_recent(days=7, limit=limit)

        return [
            {
                "id": mem.id[:8],  # Short ID
                "content": mem.content[:60] + "..." if len(mem.content) > 60 else mem.content,
                "scope": mem.scope.value,
                "type": mem.type.value,
                "age": self._format_age(mem.created_at),
                "confidence": f"{mem.confidence:.1f}",
            }
            for mem in memories
        ]

    def get_stats(self) -> dict:
        """
        Get memory statistics for display.

        Returns:
            Statistics dictionary
        """
        stats = self.store.get_stats()

        return {
            "total": stats["total"],
            "active": stats["active"],
            "verified": stats["verified"],
            "hot_cache": stats["hot_cache_size"],
        }

    def search_memories(self, query: str, limit: int = 10) -> List[dict]:
        """
        Search memories.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memories
        """
        if not query.strip():
            return []

        results = self.store.retrieve(query, limit=limit)

        return [
            {
                "id": mem.id[:8],
                "content": mem.content[:80] + "..." if len(mem.content) > 80 else mem.content,
                "scope": mem.scope.value,
                "type": mem.type.value,
                "confidence": f"{mem.confidence:.1f}",
            }
            for mem in results
        ]

    def get_memory_by_scope(self, scope: str, limit: int = 10) -> List[dict]:
        """
        Get memories by scope.

        Args:
            scope: Memory scope (user/session/project/global)
            limit: Maximum results

        Returns:
            List of memories
        """
        try:
            scope_enum = MemoryScope(scope)
        except ValueError:
            return []

        memories = self.store.db.filter(scope=scope_enum, limit=limit)

        return [
            {
                "id": mem.id[:8],
                "content": mem.content[:60] + "..." if len(mem.content) > 60 else mem.content,
                "type": mem.type.value,
                "age": self._format_age(mem.created_at),
            }
            for mem in memories
        ]

    def _format_age(self, created_at: datetime) -> str:
        """Format age as human-readable string."""
        age = datetime.now() - created_at

        if age < timedelta(minutes=1):
            return "just now"
        elif age < timedelta(hours=1):
            minutes = int(age.total_seconds() / 60)
            return f"{minutes}m ago"
        elif age < timedelta(days=1):
            hours = int(age.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = age.days
            return f"{days}d ago"


def format_memory_sidebar(viewer: MemoryViewerData) -> str:
    """
    Format memory viewer for sidebar display.

    Args:
        viewer: Memory viewer data provider

    Returns:
        Formatted sidebar content
    """
    lines = []

    # Header
    lines.append("═══ MEMORY ═══\n")

    # Statistics
    stats = viewer.get_stats()
    lines.append(f"Total: {stats['total']}")
    lines.append(f"Active: {stats['active']}")
    lines.append(f"Cache: {stats['hot_cache']}\n")

    # Recent memories
    lines.append("Recent:")
    recent = viewer.get_recent_memories(limit=5)

    if recent:
        for mem in recent:
            lines.append(f"• [{mem['age']}] {mem['content']}")
            lines.append(f"  {mem['scope']}/{mem['type']}")
    else:
        lines.append("  (no memories)")

    return "\n".join(lines)


def format_memory_search_results(results: List[dict]) -> str:
    """
    Format search results for display.

    Args:
        results: Search results

    Returns:
        Formatted results
    """
    if not results:
        return "No results found"

    lines = [f"Found {len(results)} memories:\n"]

    for i, mem in enumerate(results, 1):
        lines.append(f"{i}. {mem['content']}")
        lines.append(f"   [{mem['scope']}] {mem['type']} (conf: {mem['confidence']})")
        lines.append("")

    return "\n".join(lines)


# Integration with Lyra TUI
def create_memory_tab(store_path: Path) -> tuple[str, str]:
    """
    Create memory tab for Lyra TUI sidebar.

    Args:
        store_path: Path to memory database

    Returns:
        Tuple of (tab_name, tab_content)
    """
    from lyra_memory.store import MemoryStore

    store = MemoryStore(store_path, enable_embeddings=False)
    viewer = MemoryViewerData(store)

    tab_name = "Memory"
    tab_content = format_memory_sidebar(viewer)

    return tab_name, tab_content


# CLI command for memory viewer
def memory_viewer_cli(store_path: Path, query: Optional[str] = None) -> None:
    """
    CLI interface for memory viewer.

    Args:
        store_path: Path to memory database
        query: Optional search query
    """
    from lyra_memory.store import MemoryStore

    store = MemoryStore(store_path, enable_embeddings=False)
    viewer = MemoryViewerData(store)

    if query:
        # Search mode
        results = viewer.search_memories(query)
        print(format_memory_search_results(results))
    else:
        # Browse mode
        print(format_memory_sidebar(viewer))
        print("\n" + "=" * 40)
        print("Commands:")
        print("  /memory search <query>  - Search memories")
        print("  /memory stats           - Show statistics")
        print("  /memory recent          - Show recent memories")

    store.close()
