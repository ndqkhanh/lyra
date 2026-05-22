# Memory System Integration Guide

## Overview

This guide shows how to use the memory system in your agents and applications.

## Quick Start

### Basic Agent with Memory

```python
from src.agents.base import Agent, AgentCapability
from src.core.task import Task, TaskType
from src.memory import MemoryType, RetrievalStrategy

class MyAgent(Agent):
    async def execute(self, task: Task):
        # Get relevant context from memory
        context = self.recall(
            query=task.description,
            limit=5,
            strategy=RetrievalStrategy.HYBRID
        )
        
        # Use context to inform execution
        for result in context:
            print(f"Relevant memory: {result.memory.content}")
        
        # Execute task...
        result = await self.do_work(task)
        
        # Remember the outcome
        self.remember(
            f"Completed {task.type.value}: {task.description}",
            memory_type=MemoryType.EPISODIC,
            importance=0.7,
            tags=[task.type.value, "completed"]
        )
        
        return result
```

## Memory Operations

### Storing Memories

#### Episodic Memory (Events)
```python
# Remember a specific event
agent.remember(
    "User asked about Python async/await at 2pm",
    memory_type=MemoryType.EPISODIC,
    importance=0.6,
    tags=["conversation", "python", "async"]
)
```

#### Semantic Memory (Facts)
```python
# Store general knowledge
agent.remember(
    "Python uses indentation to define code blocks",
    memory_type=MemoryType.SEMANTIC,
    importance=0.9,
    tags=["python", "syntax", "knowledge"]
)
```

#### Procedural Memory (How-to)
```python
# Store procedures
agent.remember(
    "To debug: 1. Check logs 2. Reproduce error 3. Isolate cause",
    memory_type=MemoryType.PROCEDURAL,
    importance=0.8,
    tags=["debugging", "procedure"]
)
```

### Retrieving Memories

#### Basic Retrieval
```python
# Simple search
results = agent.recall("Python async")

for result in results:
    print(f"Score: {result.score:.2f}")
    print(f"Content: {result.memory.content}")
    print(f"Type: {result.memory.memory_type.value}")
```

#### Filtered Retrieval
```python
# Filter by type
results = agent.recall(
    "Python",
    filters={"type": MemoryType.SEMANTIC}
)

# Filter by tags
results = agent.recall(
    "debugging",
    filters={
        "tags": ["python", "debugging"],
        "match_all_tags": True
    }
)

# Filter by time range
from datetime import datetime, timedelta
yesterday = datetime.now() - timedelta(days=1)

results = agent.recall(
    "recent events",
    filters={
        "time_range": {
            "start": yesterday.timestamp(),
            "end": datetime.now().timestamp()
        }
    }
)
```

#### Retrieval Strategies
```python
# Keyword-based (fast, exact matching)
results = agent.recall(
    "Python",
    strategy=RetrievalStrategy.KEYWORD
)

# Temporal (recent memories first)
results = agent.recall(
    "Python",
    strategy=RetrievalStrategy.TEMPORAL
)

# Importance-weighted (important memories first)
results = agent.recall(
    "Python",
    strategy=RetrievalStrategy.IMPORTANCE
)

# Hybrid (combines all strategies)
results = agent.recall(
    "Python",
    strategy=RetrievalStrategy.HYBRID
)
```

### Conversation Tracking

```python
# Add conversation turns
agent.add_conversation_turn("user", "How do I use async/await?")
agent.add_conversation_turn("agent", "Here's how to use async/await...")

# Get recent context
context = agent.get_conversation_context(max_turns=5)
print(context)

# Manually consolidate if needed
result = agent.consolidate_memories()
if result:
    print(f"Consolidated {result.memories_created} memories")
```

### Working Memory

```python
# Store temporary task context
agent.set_working_memory("current_file", "main.py")
agent.set_working_memory("current_line", 42)
agent.set_working_memory("task_id", "task_123")

# Retrieve working memory
file = agent.get_working_memory("current_file")
line = agent.get_working_memory("current_line")

# With default value
status = agent.get_working_memory("status", default="idle")
```

### Persistence

```python
# Save memories to disk
agent.save_memories()

# Load memories from disk
agent.load_memories()

# Memories are automatically saved to:
# data/memory/{agent_id}_ltm.json
```

## Advanced Usage

### Custom Consolidation Policy

```python
from src.memory import ConsolidationPolicy

# Change consolidation policy
agent.memory_consolidator.policy = ConsolidationPolicy.IMMEDIATE

# Or configure at initialization
from src.agents.base import Agent
from src.memory import MemoryConsolidator, ConsolidationPolicy

class MyAgent(Agent):
    def __init__(self, agent_id, capabilities=None):
        super().__init__(agent_id, capabilities)
        
        # Reconfigure consolidator
        self.memory_consolidator = MemoryConsolidator(
            self.short_term_memory,
            self.long_term_memory,
            policy=ConsolidationPolicy.PERIODIC,
            importance_threshold=0.7,
            consolidation_interval=300  # 5 minutes
        )
```

### Memory Statistics

```python
# Get comprehensive statistics
stats = agent.get_memory_statistics()

print("Short-term memory:")
print(f"  Total turns: {stats['short_term']['total_turns']}")
print(f"  Capacity: {stats['short_term']['capacity']}")

print("\nLong-term memory:")
print(f"  Total memories: {stats['long_term']['total_memories']}")
print(f"  By type: {stats['long_term']['by_type']}")
print(f"  Average importance: {stats['long_term']['average_importance']:.2f}")

print("\nConsolidation:")
print(f"  Total consolidations: {stats['consolidation']['total_consolidations']}")
print(f"  Memories created: {stats['consolidation']['total_memories_created']}")
```

### Memory Maintenance

```python
# Prune low-importance memories
pruned = agent.long_term_memory.prune(min_importance=0.3)
print(f"Pruned {pruned} low-importance memories")

# Apply importance decay
agent.long_term_memory.apply_decay(decay_rate=0.1)

# Rebuild index for better performance
agent.long_term_memory.rebuild_index()
```

## Best Practices

### 1. Choose Appropriate Memory Types

- **Episodic**: Specific events, user interactions, task executions
- **Semantic**: General knowledge, facts, learned information
- **Procedural**: Step-by-step procedures, workflows, algorithms

### 2. Set Meaningful Importance Scores

```python
# Critical information
importance=0.9  # User preferences, security info

# Important information
importance=0.7  # Task results, learned patterns

# Normal information
importance=0.5  # Regular interactions

# Low importance
importance=0.3  # Routine events
```

### 3. Use Descriptive Tags

```python
# Good tags
tags=["python", "async", "debugging", "error-handling"]

# Less useful tags
tags=["code", "stuff", "thing"]
```

### 4. Leverage Retrieval Strategies

```python
# For exact matches
strategy=RetrievalStrategy.KEYWORD

# For recent context
strategy=RetrievalStrategy.TEMPORAL

# For critical information
strategy=RetrievalStrategy.IMPORTANCE

# For general use (recommended)
strategy=RetrievalStrategy.HYBRID
```

### 5. Regular Maintenance

```python
# Periodically prune and decay
if agent.long_term_memory.get_statistics()["total_memories"] > 1000:
    agent.long_term_memory.prune(min_importance=0.3)
    agent.long_term_memory.apply_decay(decay_rate=0.05)
```

## Common Patterns

### Pattern 1: Context-Aware Task Execution

```python
async def execute(self, task: Task):
    # Recall relevant context
    context = self.recall(
        task.description,
        limit=5,
        strategy=RetrievalStrategy.HYBRID
    )
    
    # Use context to inform execution
    context_str = "\n".join([r.memory.content for r in context])
    
    # Execute with context
    result = await self.execute_with_context(task, context_str)
    
    # Remember the outcome
    self.remember(
        f"Task {task.task_id}: {result.data}",
        memory_type=MemoryType.EPISODIC,
        importance=0.7 if result.success else 0.9,
        tags=[task.type.value, "success" if result.success else "failure"]
    )
    
    return result
```

### Pattern 2: Learning from Failures

```python
async def execute(self, task: Task):
    try:
        result = await self.do_work(task)
        
        # Remember success
        self.remember(
            f"Successfully completed {task.type.value}",
            memory_type=MemoryType.EPISODIC,
            importance=0.6,
            tags=[task.type.value, "success"]
        )
        
    except Exception as e:
        # Remember failure with high importance
        self.remember(
            f"Failed {task.type.value}: {str(e)}",
            memory_type=MemoryType.EPISODIC,
            importance=0.9,  # High importance for failures
            tags=[task.type.value, "failure", "error"]
        )
        
        # Check for similar past failures
        similar_failures = self.recall(
            f"{task.type.value} failure",
            filters={"tags": ["failure"]},
            limit=3
        )
        
        # Learn from past failures
        if similar_failures:
            print("Similar failures found:")
            for failure in similar_failures:
                print(f"  - {failure.memory.content}")
        
        raise
```

### Pattern 3: Building Knowledge Base

```python
def learn_fact(self, fact: str, category: str, importance: float = 0.8):
    """Store a fact in semantic memory."""
    self.remember(
        fact,
        memory_type=MemoryType.SEMANTIC,
        importance=importance,
        tags=["knowledge", category]
    )

def learn_procedure(self, procedure: str, category: str, importance: float = 0.8):
    """Store a procedure in procedural memory."""
    self.remember(
        procedure,
        memory_type=MemoryType.PROCEDURAL,
        importance=importance,
        tags=["procedure", category]
    )

# Usage
agent.learn_fact(
    "Python 3.11 introduced exception groups",
    category="python"
)

agent.learn_procedure(
    "To handle exception groups: use except* syntax",
    category="python"
)
```

### Pattern 4: Conversation Context

```python
async def handle_message(self, user_message: str):
    # Add to conversation
    self.add_conversation_turn("user", user_message)
    
    # Get recent context
    context = self.get_conversation_context(max_turns=5)
    
    # Recall relevant knowledge
    knowledge = self.recall(
        user_message,
        filters={"type": MemoryType.SEMANTIC},
        limit=3
    )
    
    # Generate response with context and knowledge
    response = await self.generate_response(
        message=user_message,
        context=context,
        knowledge=knowledge
    )
    
    # Add response to conversation
    self.add_conversation_turn("agent", response)
    
    return response
```

## Troubleshooting

### Memory Not Persisting

```python
# Ensure you call save_memories()
agent.save_memories()

# Or enable auto-save in your agent
class MyAgent(Agent):
    async def execute(self, task: Task):
        result = await super().execute(task)
        self.save_memories()  # Auto-save after each task
        return result
```

### Retrieval Returns No Results

```python
# Lower the minimum score threshold
results = agent.recall("query", min_score=0.3)  # Default is 0.5

# Try different strategies
results = agent.recall("query", strategy=RetrievalStrategy.KEYWORD)

# Check if memories exist
stats = agent.long_term_memory.get_statistics()
print(f"Total memories: {stats['total_memories']}")
```

### Consolidation Not Happening

```python
# Check consolidation threshold
print(f"Threshold: {agent.short_term_memory.consolidation_threshold}")
print(f"Current turns: {len(agent.short_term_memory.turns)}")

# Manually trigger consolidation
result = agent.consolidate_memories()

# Or lower the threshold
agent.short_term_memory.consolidation_threshold = 3
```

## Performance Tips

1. **Use appropriate limits**: Don't retrieve more memories than needed
2. **Filter early**: Use filters to reduce search space
3. **Prune regularly**: Remove low-importance memories periodically
4. **Use keyword strategy for exact matches**: Faster than hybrid
5. **Rebuild index after bulk operations**: Improves search performance

## Next Steps

- Explore the [Memory System API Reference](MEMORY_SYSTEM.md)
- See [examples/memory_demo.py](../examples/memory_demo.py) for more examples
- Check out the test suite in `tests/memory/` for advanced usage patterns
