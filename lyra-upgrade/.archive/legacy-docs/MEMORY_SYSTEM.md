# Memory System

A comprehensive memory management system for AI agents, providing short-term and long-term memory with intelligent retrieval and consolidation.

## Overview

The memory system consists of five main components:

1. **Memory Store** - Core storage and data structures
2. **Short-Term Memory** - Recent conversation context
3. **Long-Term Memory** - Persistent knowledge base
4. **Memory Retrieval** - Intelligent search and ranking
5. **Memory Consolidation** - STM → LTM transfer

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Interface                       │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Short-Term │  │  Long-Term   │  │   Retrieval  │
│    Memory    │  │    Memory    │  │    Engine    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                  ┌──────────────┐
                  │ Consolidation│
                  │    Engine    │
                  └──────────────┘
```

## Memory Types

### Episodic Memory
Records of specific events and experiences.

```python
memory = ltm.add(
    content="User asked about Python best practices",
    memory_type=MemoryType.EPISODIC,
    importance=0.7,
    tags=["python", "conversation"],
)
```

### Semantic Memory
General knowledge and facts.

```python
memory = ltm.add(
    content="Python uses indentation for code blocks",
    memory_type=MemoryType.SEMANTIC,
    importance=0.9,
    tags=["python", "syntax"],
)
```

### Procedural Memory
How-to knowledge and procedures.

```python
memory = ltm.add(
    content="To deploy: 1. Run tests 2. Build 3. Deploy",
    memory_type=MemoryType.PROCEDURAL,
    importance=0.8,
    tags=["deployment", "procedure"],
)
```

## Quick Start

### Basic Usage

```python
from src.memory import (
    ShortTermMemory,
    LongTermMemory,
    MemoryRetriever,
    MemoryConsolidator,
    MemoryType,
    ConsolidationPolicy,
)

# Initialize components
stm = ShortTermMemory(capacity=10)
ltm = LongTermMemory(storage_path="memories.json")
retriever = MemoryRetriever(ltm)
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.THRESHOLD
)

# Add conversation turns
stm.add_turn("user", "How do I use async/await in Python?")
stm.add_turn("agent", "Async/await is used for asynchronous programming...")

# Consolidate to long-term memory
if consolidator.should_consolidate():
    result = consolidator.consolidate()
    print(f"Created {result.memories_created} memories")

# Search memories
results = retriever.retrieve(
    query="async Python",
    limit=5,
    min_score=0.5,
)

for result in results:
    print(f"Score: {result.score:.2f}")
    print(f"Content: {result.memory.content}")
```

## Components

### 1. Memory Store

Core storage with support for different memory types.

```python
from src.memory import MemoryStore, MemoryType

store = MemoryStore(storage_path="memories.json")

# Add memory
memory = store.add(
    content="Important information",
    memory_type=MemoryType.SEMANTIC,
    importance=0.8,
    tags=["important", "knowledge"],
)

# Retrieve memory
retrieved = store.get(memory.memory_id)

# Search by type
semantic_memories = store.get_by_type(MemoryType.SEMANTIC)

# Search by tags
tagged = store.get_by_tags(["important"], match_all=False)

# Get recent memories
recent = store.get_recent(limit=10)

# Persistence
store.save()
store.load()
```

### 2. Short-Term Memory

Manages recent conversation context with automatic capacity management.

```python
from src.memory import ShortTermMemory

stm = ShortTermMemory(
    capacity=10,
    consolidation_threshold=5,
)

# Add conversation turns
stm.add_turn("user", "Hello!")
stm.add_turn("agent", "Hi! How can I help?")

# Get recent context
context = stm.get_context(max_turns=5)

# Working memory for temporary data
stm.set_working_memory("current_task", "code_review")
task = stm.get_working_memory("current_task")

# Check if consolidation needed
if stm.should_consolidate():
    turns = stm.prepare_for_consolidation()
```

### 3. Long-Term Memory

Persistent storage with indexed retrieval.

```python
from src.memory import LongTermMemory, MemoryType

ltm = LongTermMemory(storage_path="ltm.json")

# Add memories
ltm.add(
    content="Python uses duck typing",
    memory_type=MemoryType.SEMANTIC,
    importance=0.8,
    tags=["python", "typing"],
)

# Search by tags
results = ltm.search_by_tags(["python"], limit=10)

# Search by content
results = ltm.search_by_content("typing", limit=5)

# Search by time range
import time
results = ltm.search_by_time_range(
    start_time=time.time() - 86400,  # Last 24 hours
)

# Get important memories
important = ltm.get_important(threshold=0.7)

# Maintenance
ltm.apply_decay(decay_rate=0.01)
ltm.merge_similar()
ltm.prune(min_importance=0.1)
```

### 4. Memory Retrieval

Intelligent search with multiple strategies.

```python
from src.memory import MemoryRetriever, RetrievalStrategy

retriever = MemoryRetriever(ltm)

# Keyword search
results = retriever.retrieve(
    query="Python async",
    strategy=RetrievalStrategy.KEYWORD,
    limit=10,
)

# Temporal search (recent first)
results = retriever.retrieve(
    query="deployment",
    strategy=RetrievalStrategy.TEMPORAL,
)

# Importance-weighted search
results = retriever.retrieve(
    query="best practices",
    strategy=RetrievalStrategy.IMPORTANCE,
)

# Hybrid search (combines all strategies)
results = retriever.retrieve(
    query="Python patterns",
    strategy=RetrievalStrategy.HYBRID,
    min_score=0.5,
)

# Filtered search
results = retriever.retrieve(
    query="testing",
    filters={
        "type": MemoryType.PROCEDURAL,
        "tags": ["testing", "python"],
        "match_all_tags": False,
        "time_range": {
            "start": time.time() - 86400 * 7,  # Last week
        }
    }
)

# Find similar memories
similar = retriever.retrieve_similar(memory, limit=5)
```

### 5. Memory Consolidation

Transfers memories from short-term to long-term storage.

```python
from src.memory import MemoryConsolidator, ConsolidationPolicy

consolidator = MemoryConsolidator(
    short_term=stm,
    long_term=ltm,
    policy=ConsolidationPolicy.THRESHOLD,
    importance_threshold=0.5,
)

# Manual consolidation
result = consolidator.consolidate()
print(f"Created: {result.memories_created}")
print(f"Merged: {result.memories_merged}")
print(f"Patterns: {result.patterns_extracted}")

# Automatic consolidation
result = consolidator.auto_consolidate()

# Extract knowledge
knowledge = consolidator.extract_knowledge("Python")

# Create procedure
procedure = consolidator.create_procedure(
    name="Deploy to Production",
    steps=[
        "Run all tests",
        "Build Docker image",
        "Push to registry",
        "Update Kubernetes deployment",
    ],
)
```

## Consolidation Policies

### Immediate
Consolidate after every turn.

```python
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.IMMEDIATE,
)
```

### Threshold
Consolidate when buffer reaches threshold.

```python
stm = ShortTermMemory(consolidation_threshold=5)
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.THRESHOLD,
)
```

### Periodic
Consolidate at regular intervals.

```python
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.PERIODIC,  # Every 5 minutes
)
```

### Manual
Only consolidate when explicitly called.

```python
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.MANUAL,
)
```

## Retrieval Strategies

### Keyword
Simple keyword matching with relevance scoring.

```python
results = retriever.retrieve(
    "Python async",
    strategy=RetrievalStrategy.KEYWORD,
)
```

### Temporal
Prioritizes recent memories.

```python
results = retriever.retrieve(
    "recent changes",
    strategy=RetrievalStrategy.TEMPORAL,
)
```

### Importance
Prioritizes high-importance memories.

```python
results = retriever.retrieve(
    "critical information",
    strategy=RetrievalStrategy.IMPORTANCE,
)
```

### Hybrid
Combines all strategies for best results.

```python
results = retriever.retrieve(
    "Python best practices",
    strategy=RetrievalStrategy.HYBRID,
)
```

## Advanced Features

### Memory Decay

Importance naturally decays over time based on access patterns.

```python
# Apply decay to all memories
ltm.apply_decay(decay_rate=0.01)  # 1% per day

# Decay is automatic based on:
# - Time since last access
# - Access frequency
# - Initial importance
```

### Memory Merging

Automatically merge similar memories to reduce redundancy.

```python
# Merge memories with identical content
merged_count = ltm.merge_similar(similarity_threshold=0.8)
print(f"Merged {merged_count} memories")
```

### Memory Pruning

Remove low-importance memories to manage storage.

```python
# Remove memories below threshold
pruned_count = ltm.prune(min_importance=0.1)
print(f"Pruned {pruned_count} memories")
```

### Pattern Extraction

Automatically extract patterns from episodic memories.

```python
# Consolidation automatically extracts patterns
result = consolidator.consolidate()
print(f"Extracted {result.patterns_extracted} patterns")

# Patterns become semantic memories
patterns = ltm.search_by_tags(["pattern"])
```

### Working Memory

Temporary storage for current task context.

```python
# Store temporary data
stm.set_working_memory("current_file", "main.py")
stm.set_working_memory("line_number", 42)

# Retrieve temporary data
file = stm.get_working_memory("current_file")
line = stm.get_working_memory("line_number", default=1)

# Clear when done
stm.clear_working_memory()
```

## Statistics and Monitoring

### Memory Store Statistics

```python
stats = store.get_statistics()
print(f"Total memories: {stats['total_memories']}")
print(f"By type: {stats['by_type']}")
print(f"Average importance: {stats['average_importance']}")
```

### Short-Term Memory Statistics

```python
stats = stm.get_statistics()
print(f"Capacity: {stats['capacity']}")
print(f"Utilization: {stats['utilization']}")
print(f"Should consolidate: {stats['should_consolidate']}")
```

### Long-Term Memory Statistics

```python
stats = ltm.get_statistics()
print(f"Total memories: {stats['total_memories']}")
print(f"Indexed tags: {stats['indexed_tags']}")
print(f"Indexed types: {stats['indexed_types']}")
```

### Consolidation Statistics

```python
stats = consolidator.get_statistics()
print(f"Policy: {stats['policy']}")
print(f"Last consolidation: {stats['last_consolidation']}")
print(f"Should consolidate: {stats['should_consolidate']}")
```

## Best Practices

### 1. Set Appropriate Importance

```python
# Critical information
ltm.add("API key format", MemoryType.SEMANTIC, importance=0.9)

# Routine conversation
ltm.add("User said hello", MemoryType.EPISODIC, importance=0.3)

# Important procedures
ltm.add("Emergency rollback", MemoryType.PROCEDURAL, importance=0.95)
```

### 2. Use Meaningful Tags

```python
ltm.add(
    "Python uses GIL for thread safety",
    MemoryType.SEMANTIC,
    tags=["python", "concurrency", "threading", "gil"],
)
```

### 3. Regular Maintenance

```python
# Run periodically (e.g., daily)
ltm.apply_decay(decay_rate=0.01)
ltm.merge_similar()
ltm.prune(min_importance=0.1)
ltm.save()
```

### 4. Choose Right Consolidation Policy

```python
# For interactive agents
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.THRESHOLD,
)

# For batch processing
consolidator = MemoryConsolidator(
    stm, ltm,
    policy=ConsolidationPolicy.MANUAL,
)
```

### 5. Use Filters for Precise Retrieval

```python
results = retriever.retrieve(
    query="testing",
    filters={
        "type": MemoryType.PROCEDURAL,
        "tags": ["testing"],
        "time_range": {"start": recent_time},
    },
    min_score=0.6,
)
```

## Performance Considerations

### Memory Store
- O(1) access by ID
- O(n) search operations
- Indexed by tags and types

### Short-Term Memory
- O(1) add/remove
- O(n) search
- Automatic capacity management

### Long-Term Memory
- O(1) access by ID
- O(log n) indexed search
- O(n) content search

### Retrieval
- Keyword: O(n)
- Temporal: O(n log n)
- Importance: O(n)
- Hybrid: O(n log n)

## Testing

Run the test suite:

```bash
# All memory tests
pytest tests/memory/ -v

# Specific component
pytest tests/memory/test_memory_store.py -v
pytest tests/memory/test_short_term_memory.py -v
pytest tests/memory/test_long_term_memory.py -v
pytest tests/memory/test_memory_retrieval.py -v
pytest tests/memory/test_memory_consolidation.py -v

# With coverage
pytest tests/memory/ --cov=src/memory --cov-report=html
```

## Future Enhancements

- [ ] Semantic embeddings for better similarity
- [ ] Graph-based memory relationships
- [ ] Distributed memory storage
- [ ] Memory compression
- [ ] Advanced pattern recognition
- [ ] Memory visualization tools
- [ ] Multi-agent memory sharing
- [ ] Memory versioning and history

## License

MIT License - see LICENSE file for details.
