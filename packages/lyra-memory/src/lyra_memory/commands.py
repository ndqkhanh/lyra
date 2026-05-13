"""
CLI commands for memory management.

Provides /memory command with subcommands:
- search: Search memories
- add: Add a memory manually
- edit: Edit an existing memory
- delete: Delete a memory
- stats: Show memory statistics
"""

from datetime import datetime
from typing import Optional

from lyra_memory.schema import MemoryScope, MemoryType
from lyra_memory.store import MemoryStore


class MemoryCommands:
    """CLI commands for memory management."""

    def __init__(self, store: MemoryStore):
        """
        Initialize memory commands.

        Args:
            store: Memory store instance
        """
        self.store = store

    def search(
        self,
        query: str,
        scope: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """
        Search memories.

        Args:
            query: Search query
            scope: Filter by scope (user/session/project/global)
            type: Filter by type (episodic/semantic/procedural/preference/failure)
            limit: Maximum results

        Returns:
            Formatted search results
        """
        # Parse scope and type
        scope_enum = MemoryScope(scope) if scope else None
        type_enum = MemoryType(type) if type else None

        # Search
        results = self.store.retrieve(
            query=query,
            scope=scope_enum,
            type=type_enum,
            limit=limit,
        )

        if not results:
            return f"No memories found for query: {query}"

        # Format results
        lines = [f"Found {len(results)} memories:\n"]
        for i, memory in enumerate(results, 1):
            lines.append(f"{i}. [{memory.scope.value}] {memory.content}")
            lines.append(f"   ID: {memory.id}")
            lines.append(f"   Type: {memory.type.value}")
            lines.append(f"   Confidence: {memory.confidence:.2f}")
            if memory.source_span:
                lines.append(f"   Source: {memory.source_span}")
            if memory.valid_from or memory.valid_until:
                valid_str = "Valid: "
                if memory.valid_from:
                    valid_str += f"from {memory.valid_from.strftime('%Y-%m-%d')}"
                if memory.valid_until:
                    valid_str += f" until {memory.valid_until.strftime('%Y-%m-%d')}"
                lines.append(f"   {valid_str}")
            lines.append("")

        return "\n".join(lines)

    def add(
        self,
        content: str,
        scope: str = "session",
        type: str = "semantic",
        confidence: float = 1.0,
    ) -> str:
        """
        Add a memory manually.

        Args:
            content: Memory content
            scope: Memory scope
            type: Memory type
            confidence: Confidence score

        Returns:
            Success message with memory ID
        """
        memory = self.store.write(
            content=content,
            scope=MemoryScope(scope),
            type=MemoryType(type),
            confidence=confidence,
            source_span="manual",
        )

        return f"Memory added successfully!\nID: {memory.id}\nStatus: {memory.verifier_status.value}"

    def edit(self, memory_id: str, content: str) -> str:
        """
        Edit an existing memory.

        Args:
            memory_id: Memory ID
            content: New content

        Returns:
            Success message
        """
        memory = self.store.get(memory_id)
        if not memory:
            return f"Memory not found: {memory_id}"

        memory.content = content
        self.store.update(memory)

        return f"Memory updated successfully!\nID: {memory_id}"

    def delete(self, memory_id: str) -> str:
        """
        Delete a memory.

        Args:
            memory_id: Memory ID

        Returns:
            Success message
        """
        memory = self.store.get(memory_id)
        if not memory:
            return f"Memory not found: {memory_id}"

        self.store.delete(memory_id)
        return f"Memory deleted successfully!\nID: {memory_id}"

    def stats(self) -> str:
        """
        Show memory statistics.

        Returns:
            Formatted statistics
        """
        stats = self.store.get_stats()

        lines = [
            "Memory Statistics:",
            "",
            f"Total memories: {stats['total']}",
            f"Active memories: {stats['active']}",
            f"Superseded: {stats['superseded']}",
            "",
            "By verification status:",
            f"  Verified: {stats['verified']}",
            f"  Unverified: {stats['unverified']}",
            f"  Quarantined: {stats['quarantined']}",
            "",
            f"Hot cache size: {stats['hot_cache_size']}",
        ]

        return "\n".join(lines)

    def list_recent(self, days: int = 7, limit: int = 20) -> str:
        """
        List recent memories.

        Args:
            days: Number of days to look back
            limit: Maximum results

        Returns:
            Formatted list of recent memories
        """
        memories = self.store.db.get_recent(days=days, limit=limit)

        if not memories:
            return f"No memories found in the last {days} days"

        lines = [f"Recent memories (last {days} days):\n"]
        for i, memory in enumerate(memories, 1):
            age = datetime.now() - memory.created_at
            age_str = f"{age.days}d" if age.days > 0 else f"{age.seconds // 3600}h"

            lines.append(f"{i}. [{age_str}] {memory.content[:80]}")
            lines.append(f"   ID: {memory.id} | Type: {memory.type.value}")
            lines.append("")

        return "\n".join(lines)

    def get(self, memory_id: str) -> str:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Formatted memory details
        """
        memory = self.store.get(memory_id)
        if not memory:
            return f"Memory not found: {memory_id}"

        lines = [
            "Memory Details:",
            "",
            f"ID: {memory.id}",
            f"Scope: {memory.scope.value}",
            f"Type: {memory.type.value}",
            f"Content: {memory.content}",
            f"Confidence: {memory.confidence:.2f}",
            f"Status: {memory.verifier_status.value}",
            f"Created: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if memory.source_span:
            lines.append(f"Source: {memory.source_span}")

        if memory.valid_from:
            lines.append(f"Valid from: {memory.valid_from.strftime('%Y-%m-%d')}")

        if memory.valid_until:
            lines.append(f"Valid until: {memory.valid_until.strftime('%Y-%m-%d')}")

        if memory.superseded_by:
            lines.append(f"Superseded by: {memory.superseded_by}")

        if memory.links:
            lines.append(f"Links: {', '.join(memory.links)}")

        if memory.metadata:
            lines.append(f"Metadata: {memory.metadata}")

        return "\n".join(lines)


def format_memory_command_help() -> str:
    """
    Format help text for /memory command.

    Returns:
        Formatted help text
    """
    return """
Memory Management Commands:

/memory search <query> [--scope=<scope>] [--type=<type>] [--limit=<n>]
    Search memories by query
    Options:
      --scope: user, session, project, global
      --type: episodic, semantic, procedural, preference, failure
      --limit: maximum results (default: 10)

/memory add <content> [--scope=<scope>] [--type=<type>] [--confidence=<n>]
    Add a memory manually
    Options:
      --scope: memory scope (default: session)
      --type: memory type (default: semantic)
      --confidence: 0.0-1.0 (default: 1.0)

/memory edit <id> <content>
    Edit an existing memory

/memory delete <id>
    Delete a memory

/memory get <id>
    Get details of a specific memory

/memory list [--days=<n>] [--limit=<n>]
    List recent memories
    Options:
      --days: days to look back (default: 7)
      --limit: maximum results (default: 20)

/memory stats
    Show memory statistics

Examples:
  /memory search "Python testing"
  /memory search "preferences" --scope=user --type=preference
  /memory add "User prefers pytest" --scope=user --type=preference
  /memory edit abc123 "Updated content"
  /memory delete abc123
  /memory list --days=30
  /memory stats
"""
