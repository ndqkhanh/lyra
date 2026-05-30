# Context Engineering Architecture for Lyra

**Version:** 1.0  
**Date:** 2026-05-29  
**Status:** Proposal  
**Authors:** Research Team

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Components](#system-components)
4. [Context Hierarchy](#context-hierarchy)
5. [Context Operations](#context-operations)
6. [Implementation Details](#implementation-details)
7. [Integration Points](#integration-points)
8. [Performance Considerations](#performance-considerations)
9. [Security & Privacy](#security--privacy)
10. [Monitoring & Observability](#monitoring--observability)

---

## Overview

### Purpose

This document defines the context engineering architecture for Lyra, a multi-agent AI system. Context engineering is the systematic optimization of information payloads for LLMs, ensuring agents have the right information at the right time while managing token efficiency, cost, and performance.

### Goals

1. **Efficiency:** Minimize token usage while maximizing information value
2. **Performance:** Optimize for low latency and high cache hit rates
3. **Intelligence:** Adaptive context management based on task requirements
4. **Scalability:** Support long-running tasks and cross-session persistence
5. **Reliability:** Prevent context failure modes (poisoning, distraction, confusion, clash)

### Key Metrics

- **Token Utilization:** <80% of context window at any time
- **Cache Hit Rate:** >70% for production workloads
- **Information Density:** >60% relevant tokens
- **Task Success Rate:** >90% for standard tasks
- **Cost Efficiency:** <50% token usage vs. naive approach

---

## Architecture Principles

### 1. Context is Not Free

Every token in the context window influences model behavior. We treat context as a precious, limited resource that must be carefully curated.

### 2. Hierarchical Organization

Context is organized in layers with different stability, caching, and retrieval characteristics:
- **System Layer:** Stable, heavily cached
- **Session Layer:** Medium-term, pruned periodically
- **Memory Layer:** Cross-session, selectively retrieved
- **Dynamic Layer:** Just-in-time, compressed aggressively

### 3. Progressive Disclosure

Agents discover context incrementally through exploration rather than receiving everything upfront. This mimics human cognitive patterns and prevents information overload.

### 4. Append-Only by Default

Context modifications break KV-cache. We prefer append-only operations with periodic compression over in-place modifications.

### 5. Error Preservation

Failed actions remain in context to enable learning and adaptation. Error recovery is a key indicator of agentic behavior.

### 6. Diversity Over Uniformity

Introduce structured variation to prevent pattern mimicry and few-shot traps that lead to model drift.

---

## System Components

### 1. Context Manager

**Responsibilities:**
- Orchestrate context lifecycle (create, update, compress, archive)
- Enforce context window limits
- Trigger compression and pruning
- Monitor context quality metrics

**Interface:**
```python
class ContextManager:
    def create_context(self, session_id: str, config: ContextConfig) -> Context
    def get_context(self, session_id: str) -> Context
    def update_context(self, session_id: str, updates: ContextUpdate) -> None
    def compress_context(self, session_id: str, strategy: CompressionStrategy) -> None
    def archive_context(self, session_id: str) -> None
    def get_metrics(self, session_id: str) -> ContextMetrics
```

### 2. Context Store

**Responsibilities:**
- Persist context across sessions
- Support efficient retrieval by session, user, project
- Handle context versioning and rollback
- Manage context expiration and cleanup

**Storage Schema:**
```
contexts/
├── sessions/
│   └── {session_id}/
│       ├── system.json          # Layer 1: System instructions
│       ├── session.json         # Layer 2: Session state
│       ├── memory.json          # Layer 3: Long-term memory refs
│       └── dynamic.json         # Layer 4: Dynamic context
├── memories/
│   ├── episodic/               # Past interactions
│   ├── procedural/             # How-to knowledge
│   └── semantic/               # Facts and relationships
└── scratchpads/
    └── {session_id}/
        ├── working_memory.json
        ├── todo.md
        └── notes.md
```

### 3. Retrieval Engine

**Responsibilities:**
- Semantic search over documents and memories
- Tool description retrieval for dynamic loadout
- Context quality scoring and ranking
- Progressive disclosure support

**Components:**
- **Embedding Service:** Generate embeddings for semantic search
- **Vector Store:** Efficient similarity search (Qdrant, Chroma, etc.)
- **Ranking Service:** Score and rank retrieved context
- **Cache:** LRU cache for frequently accessed context

### 4. Compression Engine

**Responsibilities:**
- Summarize long contexts
- Prune irrelevant information
- Clear verbose tool outputs
- Maintain structured compression metadata

**Strategies:**
```python
class CompressionStrategy(Enum):
    TOOL_RESULT_CLEARING = "clear_tool_results"
    RECURSIVE_SUMMARIZATION = "recursive_summary"
    PROVENCE_PRUNING = "provence_prune"
    MESSAGE_TRIMMING = "trim_messages"
    HIERARCHICAL_SUMMARY = "hierarchical_summary"
```

### 5. Memory System

**Responsibilities:**
- Store and retrieve cross-session memories
- Manage memory types (episodic, procedural, semantic)
- Support memory updates and merges
- Prune outdated or low-value memories

**Memory Types:**
```python
@dataclass
class Memory:
    id: str
    type: MemoryType  # EPISODIC, PROCEDURAL, SEMANTIC
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]]
    created_at: datetime
    accessed_at: datetime
    importance: float  # 0.0 to 1.0
    tags: List[str]
```

### 6. Tool Selector

**Responsibilities:**
- Select relevant tools for current task
- Maintain tool description embeddings
- Support tool masking (not removal)
- Enforce tool count limits (<30 tools)

**Selection Algorithm:**
```python
def select_tools(
    task_description: str,
    available_tools: List[Tool],
    max_tools: int = 20
) -> List[Tool]:
    # Embed task and tool descriptions
    task_emb = embed(task_description)
    tool_embs = [embed(tool.description) for tool in available_tools]
    
    # Semantic search
    scores = cosine_similarity(task_emb, tool_embs)
    
    # Select top-k
    top_indices = np.argsort(scores)[-max_tools:]
    return [available_tools[i] for i in top_indices]
```

---

## Context Hierarchy

### Layer 1: System Instructions (Stable, Cached)

**Characteristics:**
- Rarely changes (days to weeks)
- Heavily cached (>95% cache hit rate)
- Loaded at session start
- ~2K-5K tokens

**Contents:**
- Core agent identity and capabilities
- Safety guidelines and ethical boundaries
- High-level behavioral patterns
- Universal constraints and rules

**Optimization:**
- Stable prefix for maximum cache reuse
- No timestamps or dynamic data
- Deterministic serialization

**Example:**
```json
{
  "identity": "You are Lyra, an AI research assistant...",
  "capabilities": ["research", "analysis", "synthesis", "coding"],
  "safety_guidelines": [...],
  "behavioral_patterns": [...]
}
```

### Layer 2: Session Context (Medium-Term)

**Characteristics:**
- Changes frequently (minutes to hours)
- Pruned periodically (every 50-100 turns)
- Append-only with compression
- ~10K-30K tokens

**Contents:**
- Current task objectives and plan
- Active tool loadout (RAG-selected)
- Working memory / scratchpad
- Recent interaction history (last 20-50 turns)

**Optimization:**
- Append-only to preserve cache
- Periodic pruning of old messages
- Tool result clearing for verbose outputs
- Scratchpad for externalized reasoning

**Example:**
```json
{
  "task": {
    "objective": "Research context engineering techniques",
    "plan": ["Analyze papers", "Extract techniques", "Create architecture"],
    "current_phase": "analysis"
  },
  "tools": ["web_search", "read_file", "write_file", "embed_text"],
  "scratchpad": {
    "notes": "Found 16 key papers on arXiv...",
    "todo": ["Extract techniques", "Categorize by approach"]
  },
  "history": [...]  # Last 20-50 messages
}
```

### Layer 3: Long-Term Memory (Cross-Session)

**Characteristics:**
- Persists across sessions (weeks to months)
- Selectively retrieved via embeddings
- Updated incrementally
- ~5K-20K tokens (retrieved subset)

**Contents:**
- User preferences and patterns
- Domain knowledge and facts
- Procedural memories (how-to)
- Episodic memories (examples)

**Optimization:**
- Embedding-based retrieval
- Importance scoring for prioritization
- Periodic pruning of low-value memories
- Incremental updates (not full replacement)

**Example:**
```json
{
  "user_preferences": {
    "communication_style": "concise",
    "preferred_languages": ["Python", "TypeScript"],
    "work_hours": "9am-5pm PST"
  },
  "domain_knowledge": [
    {
      "topic": "context_engineering",
      "facts": ["KV-cache optimization critical", "Tool count <30 optimal"],
      "importance": 0.9
    }
  ],
  "procedural_memories": [...],
  "episodic_memories": [...]
}
```

### Layer 4: Dynamic Context (Just-in-Time)

**Characteristics:**
- Retrieved on-demand
- Compressed aggressively
- Short-lived (single turn or phase)
- ~5K-50K tokens (varies widely)

**Contents:**
- Retrieved documents (RAG)
- Tool outputs (compressed)
- Subagent results (summarized)
- File system state (on-demand)

**Optimization:**
- Aggressive compression (summaries, not full text)
- Provence-style pruning for relevance
- Sandboxing for token-heavy objects
- Progressive disclosure for exploration

**Example:**
```json
{
  "retrieved_docs": [
    {
      "source": "arxiv:2507.13334",
      "summary": "Survey of 1400+ papers on context engineering...",
      "relevance": 0.95
    }
  ],
  "tool_outputs": [
    {
      "tool": "web_search",
      "summary": "Found 10 relevant papers on context compression",
      "full_output_ref": "s3://outputs/session_123/search_001.json"
    }
  ],
  "subagent_results": [...]
}
```

---

## Context Operations

### 1. Context Creation

**Trigger:** New session start

**Process:**
1. Load Layer 1 (System Instructions) from template
2. Initialize Layer 2 (Session Context) with task
3. Retrieve relevant Layer 3 (Long-Term Memory)
4. Prepare Layer 4 (Dynamic Context) infrastructure

**Pseudocode:**
```python
def create_context(session_id: str, task: Task, user_id: str) -> Context:
    # Layer 1: System instructions (cached)
    system = load_system_instructions()
    
    # Layer 2: Session context
    session = SessionContext(
        task=task,
        tools=select_tools(task.description),
        scratchpad=Scratchpad(),
        history=[]
    )
    
    # Layer 3: Long-term memory (retrieved)
    memory = retrieve_memories(
        user_id=user_id,
        query=task.description,
        top_k=10
    )
    
    # Layer 4: Dynamic context (empty initially)
    dynamic = DynamicContext()
    
    return Context(
        session_id=session_id,
        system=system,
        session=session,
        memory=memory,
        dynamic=dynamic
    )
```

### 2. Context Update

**Trigger:** Agent action, tool call, user input

**Process:**
1. Append new information to appropriate layer
2. Check context window utilization
3. Trigger compression if needed (>70% utilization)
4. Update context metrics

**Pseudocode:**
```python
def update_context(
    context: Context,
    update: ContextUpdate
) -> Context:
    # Append to session history (Layer 2)
    context.session.history.append(update.message)
    
    # Update scratchpad if needed
    if update.scratchpad_update:
        context.session.scratchpad.update(update.scratchpad_update)
    
    # Add dynamic context if needed
    if update.retrieved_docs:
        context.dynamic.docs.extend(update.retrieved_docs)
    
    # Check utilization
    utilization = calculate_token_utilization(context)
    
    if utilization > 0.70:
        context = compress_context(context, strategy="light")
    elif utilization > 0.85:
        context = compress_context(context, strategy="aggressive")
    
    return context
```

### 3. Context Compression

**Trigger:** High utilization (>70%), phase completion, subagent handoff

**Strategies:**

**Light Compression (70-85% utilization):**
- Clear verbose tool outputs
- Trim old messages (keep last 30)
- Prune low-relevance dynamic context

**Aggressive Compression (>85% utilization):**
- Recursive summarization of history
- Provence-style pruning
- Archive to long-term memory
- Reset dynamic context

**Pseudocode:**
```python
def compress_context(
    context: Context,
    strategy: str
) -> Context:
    if strategy == "light":
        # Clear tool results
        context.session.history = clear_tool_results(
            context.session.history
        )
        
        # Trim old messages
        context.session.history = context.session.history[-30:]
        
        # Prune dynamic context
        context.dynamic = prune_dynamic_context(
            context.dynamic,
            threshold=0.6
        )
    
    elif strategy == "aggressive":
        # Summarize history
        summary = summarize_history(context.session.history)
        
        # Archive important memories
        archive_to_memory(
            context.session.history,
            context.memory
        )
        
        # Reset session history with summary
        context.session.history = [
            Message(role="system", content=summary)
        ]
        
        # Clear dynamic context
        context.dynamic = DynamicContext()
    
    return context
```

### 4. Context Retrieval

**Trigger:** Agent needs information, tool selection, memory recall

**Process:**
1. Embed query
2. Semantic search over relevant stores
3. Score and rank results
4. Return top-k with metadata

**Pseudocode:**
```python
def retrieve_context(
    query: str,
    context_type: ContextType,
    top_k: int = 10
) -> List[ContextItem]:
    # Embed query
    query_emb = embed(query)
    
    # Select appropriate store
    if context_type == ContextType.DOCUMENT:
        store = document_store
    elif context_type == ContextType.MEMORY:
        store = memory_store
    elif context_type == ContextType.TOOL:
        store = tool_store
    
    # Semantic search
    results = store.search(query_emb, top_k=top_k * 2)
    
    # Score and rank
    scored_results = [
        (item, score_context_quality(item, query))
        for item in results
    ]
    
    # Sort by score and return top-k
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return [item for item, score in scored_results[:top_k]]
```

### 5. Context Isolation

**Trigger:** Multi-agent task, parallel exploration, context quarantine

**Process:**
1. Create isolated context for subagent
2. Provide focused tool loadout
3. Execute subagent task
4. Compress result to summary
5. Return summary to main agent

**Pseudocode:**
```python
def isolate_context(
    parent_context: Context,
    subtask: Task
) -> Context:
    # Create isolated context
    subcontext = Context(
        session_id=f"{parent_context.session_id}_sub_{uuid4()}",
        system=parent_context.system,  # Reuse system layer
        session=SessionContext(
            task=subtask,
            tools=select_tools(subtask.description),
            scratchpad=Scratchpad(),
            history=[]
        ),
        memory=parent_context.memory,  # Share memory
        dynamic=DynamicContext()  # Fresh dynamic context
    )
    
    return subcontext

def merge_subagent_result(
    parent_context: Context,
    subagent_result: SubagentResult
) -> Context:
    # Compress subagent result to summary
    summary = summarize_subagent_result(subagent_result)
    
    # Add to parent dynamic context
    parent_context.dynamic.subagent_results.append(summary)
    
    return parent_context
```

---

## Implementation Details

### Technology Stack

**Core Components:**
- **Language:** Python 3.11+
- **Framework:** LangGraph for orchestration
- **Vector Store:** Qdrant for embeddings
- **Cache:** Redis for KV-cache simulation
- **Storage:** PostgreSQL for structured data, S3 for blobs
- **Monitoring:** Prometheus + Grafana

**Libraries:**
- **Embeddings:** sentence-transformers, OpenAI embeddings
- **Compression:** Provence (context pruning), custom summarization
- **Serialization:** Pydantic for schemas, msgpack for efficiency

### Data Models

**Context Schema:**
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class MemoryType(str, Enum):
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    SEMANTIC = "semantic"

class Message(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime

class Scratchpad(BaseModel):
    notes: str = ""
    todo: List[str] = []
    working_memory: Dict[str, Any] = {}

class SessionContext(BaseModel):
    task: Task
    tools: List[Tool]
    scratchpad: Scratchpad
    history: List[Message]

class Memory(BaseModel):
    id: str
    type: MemoryType
    content: str
    embedding: Optional[List[float]]
    metadata: Dict[str, Any]
    importance: float
    created_at: datetime
    accessed_at: datetime

class DynamicContext(BaseModel):
    retrieved_docs: List[Document] = []
    tool_outputs: List[ToolOutput] = []
    subagent_results: List[SubagentResult] = []

class Context(BaseModel):
    session_id: str
    system: SystemInstructions
    session: SessionContext
    memory: List[Memory]
    dynamic: DynamicContext
    metadata: ContextMetadata
```

### API Design

**REST API:**
```
POST   /api/v1/contexts                    # Create context
GET    /api/v1/contexts/{session_id}       # Get context
PUT    /api/v1/contexts/{session_id}       # Update context
DELETE /api/v1/contexts/{session_id}       # Archive context

POST   /api/v1/contexts/{session_id}/compress  # Compress context
GET    /api/v1/contexts/{session_id}/metrics   # Get metrics

POST   /api/v1/memories                    # Create memory
GET    /api/v1/memories/search             # Search memories
PUT    /api/v1/memories/{memory_id}        # Update memory
DELETE /api/v1/memories/{memory_id}        # Delete memory

POST   /api/v1/retrieval/documents         # Retrieve documents
POST   /api/v1/retrieval/tools             # Select tools
POST   /api/v1/retrieval/memories          # Retrieve memories
```

**Python SDK:**
```python
from lyra.context import ContextManager, Context, ContextConfig

# Initialize
manager = ContextManager(config=ContextConfig(...))

# Create context
context = manager.create_context(
    session_id="session_123",
    task=Task(description="Research context engineering"),
    user_id="user_456"
)

# Update context
manager.update_context(
    session_id="session_123",
    update=ContextUpdate(
        message=Message(role="user", content="Find papers on RAG"),
        scratchpad_update={"notes": "Searching for RAG papers..."}
    )
)

# Compress context
manager.compress_context(
    session_id="session_123",
    strategy=CompressionStrategy.RECURSIVE_SUMMARIZATION
)

# Get metrics
metrics = manager.get_metrics(session_id="session_123")
print(f"Token utilization: {metrics.token_utilization:.2%}")
print(f"Cache hit rate: {metrics.cache_hit_rate:.2%}")
```

---

## Integration Points

### 1. Agent System Integration

**Lyra Agent → Context Manager:**
- Agent requests context at each decision point
- Context Manager returns appropriate layers
- Agent updates context after actions
- Context Manager triggers compression as needed

**Flow:**
```
Agent Decision Loop:
1. Get context from Context Manager
2. Select action based on context
3. Execute action
4. Update context with result
5. Repeat
```

### 2. Model Router Integration

**Context Manager → Model Router:**
- Context Manager provides context size and complexity
- Model Router selects appropriate model
- Triggers compression if context exceeds model limits

**Logic:**
```python
def route_model(context: Context, task: Task) -> Model:
    size = calculate_token_count(context)
    complexity = estimate_complexity(task)
    
    if size < 10_000 and complexity == "low":
        return Model.HAIKU
    elif size < 50_000 and complexity == "medium":
        return Model.SONNET
    elif size > 100_000:
        # Trigger compression first
        context = compress_context(context, "aggressive")
        return Model.OPUS
    else:
        return Model.OPUS
```

### 3. Research Engine Integration

**Research Engine → Context Manager:**
- Research tasks create isolated contexts
- Subagents explore with own contexts
- Results compressed and merged to main context

**Pattern:**
```python
# Main research agent
main_context = context_manager.get_context(session_id)

# Create subagents for parallel exploration
subagents = [
    create_subagent(main_context, subtask)
    for subtask in decompose_task(task)
]

# Execute in parallel
results = await asyncio.gather(*[
    subagent.execute() for subagent in subagents
])

# Merge results
for result in results:
    main_context = merge_subagent_result(main_context, result)
```

### 4. Skills System Integration

**Skills → Context Manager:**
- Skills can read/write to scratchpad
- Skills can retrieve memories
- Skills can trigger compression

**Example:**
```python
@skill
def research_skill(context: Context, query: str) -> str:
    # Retrieve relevant documents
    docs = context_manager.retrieve_context(
        query=query,
        context_type=ContextType.DOCUMENT,
        top_k=5
    )
    
    # Update scratchpad
    context.session.scratchpad.notes += f"\nFound {len(docs)} docs"
    
    # Return summary
    return summarize_documents(docs)
```

---

## Performance Considerations

### 1. KV-Cache Optimization

**Goal:** Maximize cache hit rate to reduce latency and cost

**Techniques:**
- Stable system prompt prefix (no timestamps)
- Append-only context updates
- Deterministic JSON serialization (sorted keys)
- Explicit cache breakpoints

**Expected Impact:**
- 10x cost reduction (cached: 0.30 USD/MTok vs. uncached: 3 USD/MTok)
- 5-10x latency reduction for TTFT

### 2. Token Efficiency

**Goal:** Minimize token usage while preserving information value

**Techniques:**
- Tool result clearing (remove verbose outputs)
- Provence-style pruning (95% reduction)
- Recursive summarization (10:1 compression)
- Progressive disclosure (load on-demand)

**Expected Impact:**
- 50-70% token reduction vs. naive approach
- Maintained or improved task success rate

### 3. Retrieval Performance

**Goal:** Sub-100ms retrieval latency for context

**Techniques:**
- Vector store optimization (HNSW index)
- LRU cache for frequent queries
- Batch embedding generation
- Async retrieval for parallel queries

**Expected Impact:**
- <50ms p50 retrieval latency
- <200ms p99 retrieval latency

### 4. Compression Performance

**Goal:** Fast compression without blocking agent

**Techniques:**
- Async compression in background
- Incremental compression (not full rewrite)
- Cached summaries (reuse when possible)
- Parallel compression for large contexts

**Expected Impact:**
- <1s compression time for typical contexts
- <5s compression time for large contexts (>100K tokens)

---

## Security & Privacy

### 1. Data Protection

**Sensitive Data Handling:**
- PII detection and masking in context
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Access control (RBAC)

**Context Isolation:**
- User contexts isolated by user_id
- Project contexts isolated by project_id
- No cross-user context leakage

### 2. Memory Privacy

**User Control:**
- Users can view all stored memories
- Users can delete specific memories
- Users can export memory data
- Users can opt-out of memory storage

**Retention Policies:**
- Session contexts: 30 days
- Long-term memories: 1 year (or user-specified)
- Archived contexts: 90 days
- Automatic cleanup of expired data

### 3. Audit Logging

**Logged Events:**
- Context creation, update, deletion
- Memory creation, retrieval, deletion
- Compression operations
- Retrieval queries

**Log Retention:**
- Audit logs: 1 year
- Performance logs: 30 days
- Debug logs: 7 days

---

## Monitoring & Observability

### 1. Context Metrics

**Real-Time Metrics:**
- Token utilization (gauge)
- Cache hit rate (gauge)
- Context operations/sec (counter)
- Compression operations/sec (counter)
- Retrieval latency (histogram)

**Dashboards:**
- Context health dashboard (utilization, cache hits)
- Performance dashboard (latency, throughput)
- Cost dashboard (token usage, cache savings)

### 2. Alerting

**Critical Alerts:**
- Token utilization >90% (immediate compression needed)
- Cache hit rate <50% (cache optimization needed)
- Retrieval latency >500ms (performance degradation)
- Compression failures (data loss risk)

**Warning Alerts:**
- Token utilization >70% (compression recommended)
- Cache hit rate <70% (suboptimal performance)
- Memory storage >80% capacity (cleanup needed)

### 3. Tracing

**Distributed Tracing:**
- OpenTelemetry integration
- Trace context operations end-to-end
- Correlate with agent decisions
- Debug context-related issues

**Trace Attributes:**
- session_id, user_id, task_id
- context_size, token_count
- compression_strategy, retrieval_query
- cache_hit, latency

---

## Appendix

### A. Glossary

- **Context Window:** The maximum number of tokens an LLM can process in a single inference
- **KV-Cache:** Key-Value cache that stores attention computations for reuse
- **Token Utilization:** Percentage of context window currently in use
- **Cache Hit Rate:** Percentage of tokens served from cache vs. recomputed
- **Information Density:** Ratio of relevant tokens to total tokens
- **Context Poisoning:** Hallucinations or errors that persist in context
- **Context Distraction:** Over-focus on context at expense of training knowledge
- **Context Confusion:** Irrelevant information influencing model behavior
- **Context Clash:** Conflicting information within context

### B. References

See US-001-context-engineering-analysis.md for full reference list.

### C. Change Log

- **2026-05-29:** Initial version (v1.0)

---

**Document Status:** Proposal  
**Next Review:** 2026-06-15  
**Approval Required:** Architecture Team, Engineering Lead
