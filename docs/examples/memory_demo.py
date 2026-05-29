#!/usr/bin/env python3
"""
Memory System Demo

Demonstrates the key features of the memory system.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory import (
    ConsolidationPolicy,
    LongTermMemory,
    MemoryConsolidator,
    MemoryRetriever,
    MemoryType,
    RetrievalStrategy,
    ShortTermMemory,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def demo_basic_usage():
    """Demo basic memory operations."""
    print_section("1. Basic Memory Operations")

    # Create long-term memory
    ltm = LongTermMemory()

    # Add different types of memories
    print("\nAdding memories...")

    episodic = ltm.add(
        "User asked about Python async/await",
        MemoryType.EPISODIC,
        importance=0.7,
        tags=["python", "conversation", "async"],
    )
    print(f"✓ Added episodic memory: {episodic.memory_id[:8]}...")

    semantic = ltm.add(
        "Python uses async/await for asynchronous programming",
        MemoryType.SEMANTIC,
        importance=0.9,
        tags=["python", "async", "knowledge"],
    )
    print(f"✓ Added semantic memory: {semantic.memory_id[:8]}...")

    procedural = ltm.add(
        "To use async: 1. Define with 'async def' 2. Call with 'await'",
        MemoryType.PROCEDURAL,
        importance=0.8,
        tags=["python", "async", "howto"],
    )
    print(f"✓ Added procedural memory: {procedural.memory_id[:8]}...")

    # Retrieve memory
    print(f"\nRetrieving memory {episodic.memory_id[:8]}...")
    retrieved = ltm.get(episodic.memory_id)
    print(f"✓ Content: {retrieved.content}")
    print(f"✓ Type: {retrieved.memory_type.value}")
    print(f"✓ Importance: {retrieved.importance}")


def demo_short_term_memory():
    """Demo short-term memory and consolidation."""
    print_section("2. Short-Term Memory & Consolidation")

    stm = ShortTermMemory(capacity=5, consolidation_threshold=3)
    ltm = LongTermMemory()

    print("\nAdding conversation turns...")
    stm.add_turn("user", "How do I handle errors in Python?")
    stm.add_turn("agent", "You can use try/except blocks to handle errors.")
    stm.add_turn("user", "Can you show me an example?")
    print("✓ Added 3 turns")

    # Show context
    print("\nConversation context:")
    context = stm.get_context(max_turns=3)
    for line in context.split('\n'):
        if line.strip():
            print(f"  {line}")

    # Consolidate
    print(f"\nShould consolidate? {stm.should_consolidate()}")

    consolidator = MemoryConsolidator(
        stm, ltm,
        policy=ConsolidationPolicy.THRESHOLD,
        importance_threshold=0.5,
    )

    if consolidator.should_consolidate():
        print("\nConsolidating to long-term memory...")
        result = consolidator.consolidate()
        print(f"✓ Created {result.memories_created} memories")
        print(f"✓ Merged {result.memories_merged} similar memories")
        print(f"✓ Extracted {result.patterns_extracted} patterns")
        print(f"✓ Duration: {result.duration:.3f}s")


def demo_retrieval():
    """Demo memory retrieval strategies."""
    print_section("3. Memory Retrieval Strategies")

    ltm = LongTermMemory()

    # Add sample memories
    print("\nPopulating memory with Python knowledge...")
    memories = [
        ("Python uses indentation for code blocks", 0.9, ["python", "syntax"]),
        ("Python has dynamic typing", 0.8, ["python", "typing"]),
        ("Python supports multiple paradigms", 0.7, ["python", "paradigms"]),
        ("Use list comprehensions for concise code", 0.8, ["python", "best-practices"]),
        ("Python has a large standard library", 0.7, ["python", "stdlib"]),
    ]

    for content, importance, tags in memories:
        ltm.add(content, MemoryType.SEMANTIC, importance=importance, tags=tags)

    print(f"✓ Added {len(memories)} memories")

    # Create retriever
    retriever = MemoryRetriever(ltm)

    # Keyword search
    print("\n--- Keyword Search ---")
    results = retriever.retrieve(
        "Python typing",
        strategy=RetrievalStrategy.KEYWORD,
        limit=3,
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.score:.2f}] {result.memory.content[:50]}...")

    # Importance search
    print("\n--- Importance-Based Search ---")
    results = retriever.retrieve(
        "Python",
        strategy=RetrievalStrategy.IMPORTANCE,
        limit=3,
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.score:.2f}] {result.memory.content[:50]}...")

    # Hybrid search
    print("\n--- Hybrid Search ---")
    results = retriever.retrieve(
        "Python best practices",
        strategy=RetrievalStrategy.HYBRID,
        limit=3,
    )
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.score:.2f}] {result.memory.content[:50]}...")


def demo_filtering():
    """Demo advanced filtering."""
    print_section("4. Advanced Filtering")

    ltm = LongTermMemory()

    # Add memories with different types and tags
    print("\nAdding diverse memories...")
    ltm.add("Python syntax basics", MemoryType.SEMANTIC, tags=["python", "basics"])
    ltm.add("User learned about decorators", MemoryType.EPISODIC, tags=["python", "decorators"])
    ltm.add("How to write a decorator", MemoryType.PROCEDURAL, tags=["python", "decorators"])
    ltm.add("JavaScript async patterns", MemoryType.SEMANTIC, tags=["javascript", "async"])
    print("✓ Added 4 memories")

    retriever = MemoryRetriever(ltm)

    # Filter by type
    print("\n--- Filter by Type (PROCEDURAL) ---")
    results = retriever.retrieve(
        "python",
        filters={"type": MemoryType.PROCEDURAL},
    )
    print(f"Found {len(results)} procedural memories")
    for result in results:
        print(f"  • {result.memory.content}")

    # Filter by tags
    print("\n--- Filter by Tags (python + decorators) ---")
    results = retriever.retrieve(
        "decorators",
        filters={
            "tags": ["python", "decorators"],
            "match_all_tags": True,
        },
    )
    print(f"Found {len(results)} memories with both tags")
    for result in results:
        print(f"  • {result.memory.content}")


def demo_maintenance():
    """Demo memory maintenance operations."""
    print_section("5. Memory Maintenance")

    ltm = LongTermMemory()

    # Add memories with varying importance
    print("\nAdding memories with different importance levels...")
    ltm.add("Critical information", MemoryType.SEMANTIC, importance=0.95)
    ltm.add("Important information", MemoryType.SEMANTIC, importance=0.75)
    ltm.add("Routine information", MemoryType.SEMANTIC, importance=0.50)
    ltm.add("Low importance", MemoryType.SEMANTIC, importance=0.15)
    ltm.add("Very low importance", MemoryType.SEMANTIC, importance=0.05)

    print(f"✓ Total memories: {len(ltm.store.memories)}")

    # Show statistics
    print("\n--- Memory Statistics ---")
    stats = ltm.get_statistics()
    print(f"Total memories: {stats['total_memories']}")
    print(f"Average importance: {stats['average_importance']:.2f}")
    print(f"By type: {stats['by_type']}")

    # Prune low-importance memories
    print("\n--- Pruning Low-Importance Memories ---")
    pruned = ltm.prune(min_importance=0.2)
    print(f"✓ Pruned {pruned} memories")
    print(f"✓ Remaining: {len(ltm.store.memories)}")

    # Apply decay
    print("\n--- Applying Importance Decay ---")
    # Simulate old access times
    for memory in ltm.store.memories.values():
        memory.last_accessed = time.time() - 86400  # 1 day ago

    ltm.apply_decay(decay_rate=0.1)
    print("✓ Applied decay to all memories")

    stats = ltm.get_statistics()
    print(f"✓ New average importance: {stats['average_importance']:.2f}")


def demo_working_memory():
    """Demo working memory for temporary data."""
    print_section("6. Working Memory")

    stm = ShortTermMemory()

    print("\nStoring temporary task context...")
    stm.set_working_memory("current_file", "main.py")
    stm.set_working_memory("current_line", 42)
    stm.set_working_memory("task", "refactoring")
    print("✓ Stored 3 working memory items")

    print("\nRetrieving working memory...")
    file = stm.get_working_memory("current_file")
    line = stm.get_working_memory("current_line")
    task = stm.get_working_memory("task")

    print(f"  Current file: {file}")
    print(f"  Current line: {line}")
    print(f"  Current task: {task}")

    print("\nClearing working memory...")
    stm.clear_working_memory()
    print("✓ Working memory cleared")

    # Verify cleared
    file = stm.get_working_memory("current_file", default="<none>")
    print(f"  Current file: {file}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  MEMORY SYSTEM DEMONSTRATION")
    print("=" * 60)

    try:
        demo_basic_usage()
        demo_short_term_memory()
        demo_retrieval()
        demo_filtering()
        demo_maintenance()
        demo_working_memory()

        print("\n" + "=" * 60)
        print("  Demo completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
