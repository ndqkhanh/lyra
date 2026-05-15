"""
Memory-as-Tool-Calls: Letta-style memory management

Exposes memory operations as explicit tool calls, making memory management
auditable, replayable, and agent-controlled.

Based on Letta research (docs/182-memory-frontiers-2026.md)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import sqlite3


def write_to_archival(
    text: str,
    tags: Optional[List[str]] = None,
    source: str = "agent_explicit",
    cognitive_weight: float = 0.5
) -> str:
    """
    Store information in long-term archival memory.

    This is an explicit memory write operation that the agent controls.
    Use this when you want to remember important information for future sessions.

    Args:
        text: The information to store (fact, decision, preference, etc.)
        tags: Optional tags for categorization (e.g., ["preference", "language"])
        source: Source of this memory (default: "agent_explicit")
        cognitive_weight: Initial weight (default: 0.5 for explicit writes)

    Returns:
        Entry ID of the stored memory

    Example:
        >>> write_to_archival(
        ...     "User prefers TypeScript over JavaScript",
        ...     tags=["preference", "language"]
        ... )
        "mem_abc123"
    """
    from lyra_core.memory.procedural import ProceduralMemory

    memory = ProceduralMemory()

    entry_id = memory.store_semantic_fact(
        fact=text,
        tags=tags or [],
        source=source,
        cognitive_weight=cognitive_weight,
        timestamp=datetime.now()
    )

    return f"Stored in archival memory: {entry_id}"


def search_archival(
    query: str,
    k: int = 5,
    min_score: float = 0.0,
    tags: Optional[List[str]] = None
) -> str:
    """
    Search long-term archival memory.

    Retrieves relevant information from past sessions based on semantic similarity.

    Args:
        query: Search query (natural language)
        k: Number of results to return (default: 5)
        min_score: Minimum relevance score (default: 0.0)
        tags: Optional tag filter (only return entries with these tags)

    Returns:
        Formatted search results with relevance scores

    Example:
        >>> search_archival("programming language preferences")
        '''
        Found 2 results:

        [1] Score: 0.89 | Tags: preference, language
        User prefers TypeScript over JavaScript

        [2] Score: 0.76 | Tags: preference, tooling
        User prefers VS Code for TypeScript development
        '''
    """
    from lyra_core.memory.procedural import ProceduralMemory

    memory = ProceduralMemory()

    results = memory.search_semantic(
        query=query,
        k=k,
        min_score=min_score,
        tag_filter=tags
    )

    if not results:
        return "No results found in archival memory."

    # Format results
    output = [f"Found {len(results)} result(s):\n"]

    for i, result in enumerate(results, 1):
        tags_str = ", ".join(result.get('tags', []))
        output.append(
            f"[{i}] Score: {result['score']:.2f} | Tags: {tags_str}\n"
            f"{result['content']}\n"
        )

    return "\n".join(output)


def update_core_memory(label: str, value: str) -> str:
    """
    Update a core memory block (persona, preferences, context).

    Core memory is always loaded and represents the agent's persistent identity.

    Args:
        label: Memory block label (e.g., "persona", "user_preferences", "project_context")
        value: New value for this memory block

    Returns:
        Confirmation message

    Example:
        >>> update_core_memory("user_preferences", "Prefers concise responses")
        "Updated core memory: user_preferences"
    """
    from lyra_core.memory.procedural import ProceduralMemory

    memory = ProceduralMemory()

    memory.update_core_block(label=label, value=value)

    return f"Updated core memory: {label}"


def read_core_memory(label: Optional[str] = None) -> str:
    """
    Read core memory blocks.

    Args:
        label: Optional specific block to read (if None, returns all blocks)

    Returns:
        Core memory content

    Example:
        >>> read_core_memory("persona")
        '''
        [persona]
        I am Lyra, a coding agent focused on helping users build software.
        I prefer clear, concise communication and always verify my work.
        '''
    """
    from lyra_core.memory.procedural import ProceduralMemory

    memory = ProceduralMemory()

    if label:
        value = memory.get_core_block(label)
        if value is None:
            return f"Core memory block '{label}' not found."
        return f"[{label}]\n{value}"
    else:
        blocks = memory.get_all_core_blocks()
        if not blocks:
            return "No core memory blocks found."

        output = []
        for block_label, block_value in blocks.items():
            output.append(f"[{block_label}]\n{block_value}\n")

        return "\n".join(output)


def forget_memory(entry_id: str) -> str:
    """
    Explicitly forget a memory entry.

    Removes an entry from archival memory. Use this when information
    becomes outdated, incorrect, or no longer relevant.

    Args:
        entry_id: ID of the memory entry to forget

    Returns:
        Confirmation message

    Example:
        >>> forget_memory("mem_abc123")
        "Forgot: mem_abc123"
    """
    from lyra_core.memory.procedural import ProceduralMemory

    memory = ProceduralMemory()

    success = memory.delete_entry(entry_id)

    if success:
        return f"Forgot: {entry_id}"
    else:
        return f"Entry not found: {entry_id}"


def list_recent_memories(limit: int = 10, tags: Optional[List[str]] = None) -> str:
    """
    List recent memory entries.

    Args:
        limit: Number of entries to return (default: 10)
        tags: Optional tag filter

    Returns:
        Formatted list of recent memories

    Example:
        >>> list_recent_memories(limit=5, tags=["preference"])
        '''
        Recent memories (5):

        [1] mem_abc123 | 2026-05-12 14:30 | Tags: preference, language
        User prefers TypeScript over JavaScript

        [2] mem_def456 | 2026-05-12 14:25 | Tags: preference, tooling
        User prefers VS Code for development
        ...
        '''
    """
    from lyra_core.memory.procedural import ProceduralMemory

    memory = ProceduralMemory()

    entries = memory.get_recent_entries(limit=limit, tag_filter=tags)

    if not entries:
        return "No recent memories found."

    output = [f"Recent memories ({len(entries)}):\n"]

    for i, entry in enumerate(entries, 1):
        tags_str = ", ".join(entry.get('tags', []))
        timestamp = entry['timestamp'].strftime("%Y-%m-%d %H:%M")
        output.append(
            f"[{i}] {entry['id']} | {timestamp} | Tags: {tags_str}\n"
            f"{entry['content'][:100]}{'...' if len(entry['content']) > 100 else ''}\n"
        )

    return "\n".join(output)


# Tool definitions for agent registration
MEMORY_TOOLS = [
    {
        "name": "write_to_archival",
        "description": "Store information in long-term archival memory",
        "function": write_to_archival,
        "parameters": {
            "text": {"type": "string", "required": True},
            "tags": {"type": "array", "items": {"type": "string"}, "required": False},
            "source": {"type": "string", "required": False},
            "cognitive_weight": {"type": "number", "required": False}
        }
    },
    {
        "name": "search_archival",
        "description": "Search long-term archival memory",
        "function": search_archival,
        "parameters": {
            "query": {"type": "string", "required": True},
            "k": {"type": "integer", "required": False},
            "min_score": {"type": "number", "required": False},
            "tags": {"type": "array", "items": {"type": "string"}, "required": False}
        }
    },
    {
        "name": "update_core_memory",
        "description": "Update a core memory block (persona, preferences, context)",
        "function": update_core_memory,
        "parameters": {
            "label": {"type": "string", "required": True},
            "value": {"type": "string", "required": True}
        }
    },
    {
        "name": "read_core_memory",
        "description": "Read core memory blocks",
        "function": read_core_memory,
        "parameters": {
            "label": {"type": "string", "required": False}
        }
    },
    {
        "name": "forget_memory",
        "description": "Explicitly forget a memory entry",
        "function": forget_memory,
        "parameters": {
            "entry_id": {"type": "string", "required": True}
        }
    },
    {
        "name": "list_recent_memories",
        "description": "List recent memory entries",
        "function": list_recent_memories,
        "parameters": {
            "limit": {"type": "integer", "required": False},
            "tags": {"type": "array", "items": {"type": "string"}, "required": False}
        }
    }
]
