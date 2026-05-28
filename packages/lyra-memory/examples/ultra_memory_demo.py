#!/usr/bin/env python3
"""
Ultra Memory System - Comprehensive Example

Demonstrates all five components of the ultra memory system:
1. Importance scoring
2. ACT-R activation & decay
3. Multi-graph knowledge store
4. Offline consolidation
5. Budget management
"""

import time
from pathlib import Path

from lyra_memory import (
    MemoryScope,
    MemoryType,
    UltraMemoryConfig,
    UltraMemorySystem,
)


def main():
    print("=" * 70)
    print("Ultra Memory System - Comprehensive Demo")
    print("=" * 70)
    print()

    # Initialize system
    print("1. Initializing Ultra Memory System...")
    config = UltraMemoryConfig(
        capacity_limit=100,  # Small limit for demo
        decay_rate=0.5,
        importance_weight=2.0,
        retrieval_threshold=-1.0,
        consolidation_interval_hours=1,
        enable_auto_consolidation=True,
        enable_auto_pruning=True,
    )

    db_path = Path("/tmp/ultra_memory_demo.db")
    if db_path.exists():
        db_path.unlink()

    system = UltraMemorySystem(db_path=db_path, config=config)
    print(f"✓ System initialized with capacity limit: {config.capacity_limit}")
    print()

    # Write memories with different importance levels
    print("2. Writing memories with automatic importance scoring...")

    memories = [
        # Critical - User preference
        ("My name is Alice and I prefer Python over JavaScript",
         MemoryScope.GLOBAL, MemoryType.PREFERENCE, True),

        # High - Procedural knowledge
        ("To deploy: run npm build, then npm run deploy --prod",
         MemoryScope.GLOBAL, MemoryType.PROCEDURAL, False),

        # High - Failure memory
        ("Deployment failed due to missing DATABASE_URL environment variable",
         MemoryScope.SESSION, MemoryType.FAILURE, False),

        # Medium - Semantic knowledge
        ("The authentication system uses JWT tokens with 24-hour expiry",
         MemoryScope.GLOBAL, MemoryType.SEMANTIC, False),

        # Low - Episodic event
        ("Had a meeting about the new feature at 2pm",
         MemoryScope.SESSION, MemoryType.EPISODIC, False),

        # Noise - Greeting
        ("Hello! How are you doing today?",
         MemoryScope.SESSION, MemoryType.EPISODIC, False),
    ]

    written_memories = []
    for content, scope, mem_type, flagged in memories:
        memory = system.write(
            content=content,
            scope=scope,
            type=mem_type,
            user_flagged=flagged,
        )
        importance = memory.metadata.get('importance', 0.0)
        category = memory.metadata.get('importance_category', 'unknown')
        written_memories.append(memory)

        print(f"  [{category.upper():8s}] {importance:.2f} - {content[:50]}...")

    print()

    # Retrieve with activation-based ranking
    print("3. Retrieving memories (activation-based ranking)...")
    results = system.retrieve(
        query="deployment process",
        top_k=5,
        use_graph=False,
    )

    print(f"  Found {len(results)} accessible memories:")
    for i, memory in enumerate(results, 1):
        activation = memory.metadata.get('_activation', 0.0)
        importance = memory.metadata.get('importance', 0.0)
        print(f"  {i}. [A={activation:+.2f}, I={importance:.2f}] {memory.content[:50]}...")

    print()

    # Simulate time passing and retrieval patterns
    print("4. Simulating retrieval patterns over time...")

    # Retrieve deployment-related memories multiple times
    for _ in range(3):
        system.retrieve("deployment", top_k=3)
        time.sleep(0.1)

    print("  ✓ Retrieved deployment memories 3 times (strengthening activation)")

    # Wait a bit
    time.sleep(0.5)

    # Retrieve authentication memories once
    system.retrieve("authentication", top_k=3)
    print("  ✓ Retrieved authentication memories 1 time")
    print()

    # Check system statistics
    print("5. System Statistics...")
    stats = system.get_stats()

    print(f"  Total memories: {stats.total_memories}")
    print(f"  Active memories: {stats.active_memories}")
    print(f"  Dormant memories: {stats.dormant_memories}")
    print(f"  Average importance: {stats.avg_importance:.2f}")
    print(f"  Average activation: {stats.avg_activation:.2f}")
    print(f"  Budget tier: {stats.budget_status.tier.value}")
    print(f"  Usage: {stats.budget_status.usage_percent:.1%}")
    print()

    # Add more memories to trigger budget management
    print("6. Testing budget management...")
    print(f"  Adding memories to approach capacity limit ({config.capacity_limit})...")

    for i in range(50):
        system.write(
            content=f"Test memory {i} with some content to fill the database",
            scope=MemoryScope.SESSION,
            type=MemoryType.EPISODIC,
        )

    stats = system.get_stats()
    print(f"  Total memories: {stats.total_memories}")
    print(f"  Budget tier: {stats.budget_status.tier.value}")
    print(f"  Usage: {stats.budget_status.usage_percent:.1%}")

    if stats.budget_status.action_required:
        print(f"  ⚠ Action required: {stats.budget_status.memories_to_prune} memories to prune")

    print()

    # Run consolidation
    print("7. Running memory consolidation...")
    result = system.consolidate(deep=False)

    print(f"  Duplicates merged: {result.duplicates_merged}")
    print(f"  Contradictions resolved: {result.contradictions_resolved}")
    print(f"  Memories compressed: {result.memories_compressed}")
    print(f"  Processing time: {result.duration_seconds * 1000:.1f}ms")
    print()

    # Demonstrate multi-graph relationships
    print("8. Multi-graph knowledge store...")

    # In a real system, these would be built automatically
    # For demo, we show the concept
    from lyra_memory import GraphType, MultiGraphStore, SemanticRelation

    graph = MultiGraphStore()

    # Add semantic relationships
    if len(written_memories) >= 4:
        graph.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id=written_memories[1].id,  # Deployment procedure
            target_id=written_memories[2].id,  # Deployment failure
            relation=SemanticRelation.RELATED_TO.value,
        )

        graph.add_edge(
            graph_type=GraphType.SEMANTIC,
            source_id=written_memories[3].id,  # Auth system
            target_id=written_memories[1].id,  # Deployment
            relation=SemanticRelation.PART_OF.value,
        )

    print("  ✓ Added semantic relationships between memories")
    print(f"  Graph contains {len(graph._semantic_graph)} nodes with edges")
    print()

    # Prune low-value memories
    print("9. Pruning low-value memories...")
    pruned_count = system.prune()

    print(f"  Pruned {pruned_count} memories")

    stats = system.get_stats()
    print(f"  New total: {stats.total_memories}")
    print(f"  New usage: {stats.budget_status.usage_percent:.1%}")
    print()

    # Final statistics
    print("10. Final System State...")
    stats = system.get_stats()

    print(f"  Total memories: {stats.total_memories}")
    print(f"  Active: {stats.active_memories}, Dormant: {stats.dormant_memories}")
    print(f"  Budget tier: {stats.budget_status.tier.value}")
    print(f"  Avg importance: {stats.avg_importance:.2f}")
    print(f"  Avg activation: {stats.avg_activation:.2f}")
    print()

    # Cleanup
    system.close()

    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  • Importance scoring automatically categorizes memories")
    print("  • ACT-R activation tracks memory accessibility over time")
    print("  • Retrieval strengthens activation (spacing effect)")
    print("  • Budget controller autonomously manages capacity")
    print("  • Consolidation merges duplicates and resolves contradictions")
    print("  • Multi-graph store captures semantic relationships")


if __name__ == "__main__":
    main()
