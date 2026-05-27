# Lyra v4.0 Memory System Design

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

The Memory System is the foundation of Lyra v4.0's intelligence. It provides persistent, contextual memory across sessions, enabling the agent to learn, remember, and improve over time.

---

## Design Goals

### 1. Persistence
- Memories survive across sessions
- No loss of context between restarts
- Long-term knowledge retention

### 2. Contextual Recall
- Retrieve relevant memories for current task
- Semantic search and similarity matching
- Temporal and spatial context

### 3. Efficiency
- Fast recall (<100ms)
- Efficient storage
- Scalable to millions of memories

### 4. Organization
- Structured memory networks
- Clear categorization
- Easy to query and manage

### 5. Privacy
- User control over memories
- Selective forgetting
- Data ownership

---

## Memory Architecture

### High-Level Structure

```
Memory System
│
├── Memoria (Long-term Memory)
│   ├── Beliefs Network
│   ├── Episodes Network
│   ├── Entities Network
│   ├── Procedures Network
│   └── Strategies Network
│
├── Session Store (Short-term Memory)
│   ├── Conversation History
│   ├── Tool Call History
│   └── Active Context
│
├── Working Memory (Active Context)
│   ├── Current Goal
│   ├── Recent Messages
│   ├── Active Skills
│   └── Loaded Context
│
└── Memory Manager
    ├── Recall Engine
    ├── Consolidation Engine
    ├── Forgetting Engine
    └── Query Optimizer
```

---

## Memory Networks

### 1. Beliefs Network

**Purpose**: Store facts, knowledge, and beliefs

**Schema**:
```python
class Belief:
    id: str                    # Unique identifier
    content: str               # The belief/fact
    confidence: float          # 0.0-1.0
    source: str                # Where it came from
    created_at: datetime
    updated_at: datetime
    valid_from: datetime       # Temporal validity
    valid_until: datetime | None
    tags: list[str]
    entities: list[str]        # Related entities
    evidence: list[str]        # Supporting evidence
    contradicts: list[str]     # Contradicting beliefs
```

**Examples**:
```python
Belief(
    content="User prefers JWT tokens over session cookies",
    confidence=0.9,
    source="user_explicit",
    tags=["authentication", "preferences"],
    entities=["JWT", "session_cookies"]
)

Belief(
    content="The auth service runs on port 8080",
    confidence=1.0,
    source="tool_result",
    tags=["infrastructure", "configuration"],
    entities=["auth_service"]
)
```

### 2. Episodes Network

**Purpose**: Store conversation history and events

**Schema**:
```python
class Episode:
    id: str
    session_id: str
    timestamp: datetime
    event_type: str            # "message", "tool_call", "goal", etc.
    content: str
    participants: list[str]    # ["user", "assistant"]
    context: dict              # Additional context
    outcome: str | None        # Success/failure
    duration: float | None     # Time taken
    cost: float | None         # API cost
    tags: list[str]
    related_episodes: list[str]
```

**Examples**:
```python
Episode(
    event_type="goal_completion",
    content="Fixed authentication bug in src/auth.py",
    participants=["user", "assistant"],
    outcome="success",
    duration=180.5,
    cost=0.42,
    tags=["bug_fix", "authentication"]
)
```

### 3. Entities Network

**Purpose**: Store information about entities (files, functions, concepts)

**Schema**:
```python
class Entity:
    id: str
    name: str
    type: str                  # "file", "function", "class", "concept"
    description: str
    properties: dict           # Type-specific properties
    relationships: list[Relationship]
    mentions: list[str]        # Episode IDs where mentioned
    created_at: datetime
    updated_at: datetime
    tags: list[str]
```

**Relationship Types**:
```python
class Relationship:
    type: str                  # "calls", "imports", "extends", "uses"
    target: str                # Target entity ID
    strength: float            # 0.0-1.0
    context: str | None
```

**Examples**:
```python
Entity(
    name="src/auth.py",
    type="file",
    description="Authentication module",
    properties={
        "path": "src/auth.py",
        "language": "python",
        "lines": 245,
        "last_modified": "2026-05-20"
    },
    relationships=[
        Relationship(type="imports", target="jwt_library", strength=1.0),
        Relationship(type="uses", target="user_model", strength=0.8)
    ]
)
```

### 4. Procedures Network

**Purpose**: Store skills, workflows, and procedures

**Schema**:
```python
class Procedure:
    id: str
    name: str
    description: str
    instructions: str          # How to execute
    prerequisites: list[str]   # Required conditions
    steps: list[Step]
    tools: list[str]           # Required tools
    success_criteria: str
    execution_count: int
    success_count: int
    avg_duration: float
    avg_cost: float
    tags: list[str]
    created_at: datetime
    last_used: datetime
```

**Examples**:
```python
Procedure(
    name="fix-authentication-bug",
    description="Debug and fix authentication issues",
    steps=[
        Step(order=1, action="Read error logs"),
        Step(order=2, action="Analyze auth code"),
        Step(order=3, action="Identify root cause"),
        Step(order=4, action="Implement fix"),
        Step(order=5, action="Test fix")
    ],
    tools=["read_file", "edit_file", "bash"],
    execution_count=5,
    success_count=4
)
```

### 5. Strategies Network

**Purpose**: Store high-level strategies and approaches

**Schema**:
```python
class Strategy:
    id: str
    name: str
    description: str
    context: str               # When to use
    approach: str              # How to apply
    examples: list[str]        # Example applications
    effectiveness: float       # 0.0-1.0
    usage_count: int
    success_rate: float
    tags: list[str]
    created_at: datetime
    last_used: datetime
```

**Examples**:
```python
Strategy(
    name="divide-and-conquer",
    description="Break complex problems into smaller sub-problems",
    context="When facing a large, complex task",
    approach="1. Identify sub-problems 2. Solve each independently 3. Combine solutions",
    effectiveness=0.85,
    usage_count=42,
    success_rate=0.81
)
```

---

## Memory Operations

### 1. Recall (Retrieval)

**Purpose**: Retrieve relevant memories for current context

**Query Types**:

```python
class MemoryQuery:
    # Semantic search
    query: str                 # Natural language query
    
    # Filters
    networks: list[str]        # Which networks to search
    tags: list[str]            # Filter by tags
    entities: list[str]        # Filter by entities
    time_range: tuple[datetime, datetime] | None
    
    # Ranking
    limit: int                 # Max results
    threshold: float           # Min relevance score
    rerank: bool               # Use cross-encoder reranking
    
    # Context
    session_id: str | None     # Current session
    goal_id: str | None        # Current goal
```

**Recall Algorithm**:

```python
def recall(query: MemoryQuery) -> list[Memory]:
    """
    Multi-stage recall process:
    1. Candidate retrieval (BM25 + semantic search)
    2. Filtering (tags, entities, time)
    3. Ranking (relevance + recency + importance)
    4. Reranking (cross-encoder, optional)
    5. Diversity (MMR, avoid redundancy)
    """
    
    # Stage 1: Candidate retrieval
    candidates = []
    
    # BM25 keyword search
    bm25_results = bm25_search(query.query, query.networks)
    candidates.extend(bm25_results)
    
    # Semantic search (embeddings)
    if has_embeddings():
        semantic_results = semantic_search(query.query, query.networks)
        candidates.extend(semantic_results)
    
    # Stage 2: Filtering
    filtered = apply_filters(candidates, query)
    
    # Stage 3: Ranking
    ranked = rank_memories(filtered, query)
    
    # Stage 4: Reranking (optional)
    if query.rerank:
        ranked = cross_encoder_rerank(ranked, query)
    
    # Stage 5: Diversity
    diverse = apply_mmr(ranked, query.limit)
    
    return diverse[:query.limit]
```

**Ranking Factors**:

```python
def calculate_relevance_score(memory: Memory, query: MemoryQuery) -> float:
    """
    Relevance = weighted sum of:
    - Semantic similarity (0.4)
    - Keyword match (0.2)
    - Recency (0.2)
    - Importance (0.1)
    - Usage frequency (0.1)
    """
    
    semantic = semantic_similarity(memory.embedding, query.embedding)
    keyword = bm25_score(memory.content, query.query)
    recency = recency_score(memory.updated_at)
    importance = memory.importance
    frequency = usage_frequency(memory.id)
    
    return (
        0.4 * semantic +
        0.2 * keyword +
        0.2 * recency +
        0.1 * importance +
        0.1 * frequency
    )
```

### 2. Consolidation (Storage)

**Purpose**: Store new memories and update existing ones

**Consolidation Process**:

```python
def consolidate(content: str, metadata: dict) -> Memory:
    """
    Multi-stage consolidation:
    1. Extract entities and relationships
    2. Check for duplicates
    3. Merge or create new memory
    4. Generate embeddings
    5. Update indices
    """
    
    # Stage 1: Entity extraction
    entities = extract_entities(content)
    relationships = extract_relationships(content, entities)
    
    # Stage 2: Duplicate detection
    similar = find_similar_memories(content, threshold=0.9)
    
    if similar:
        # Merge with existing memory
        memory = merge_memories(similar[0], content, metadata)
    else:
        # Create new memory
        memory = create_memory(content, metadata, entities, relationships)
    
    # Stage 3: Generate embeddings
    if should_embed(memory):
        memory.embedding = generate_embedding(memory.content)
    
    # Stage 4: Update indices
    update_indices(memory)
    
    return memory
```

**Deduplication**:

```python
def find_similar_memories(content: str, threshold: float = 0.9) -> list[Memory]:
    """
    Find similar memories to avoid duplicates
    """
    # Quick hash check
    content_hash = hash(content)
    exact_match = find_by_hash(content_hash)
    if exact_match:
        return [exact_match]
    
    # Semantic similarity
    embedding = generate_embedding(content)
    similar = semantic_search(embedding, threshold=threshold)
    
    return similar
```

### 3. Forgetting (Deletion)

**Purpose**: Remove outdated or irrelevant memories

**Forgetting Strategies**:

```python
class ForgettingStrategy:
    """
    Strategies for selective forgetting:
    1. Time-based: Remove old, unused memories
    2. Relevance-based: Remove low-importance memories
    3. Contradiction-based: Remove contradicted beliefs
    4. User-requested: Explicit deletion
    """
    
    def time_based_forgetting(self, max_age_days: int = 90):
        """Remove memories older than max_age_days that haven't been accessed"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        candidates = query_memories(
            updated_before=cutoff,
            accessed_before=cutoff,
            importance_below=0.3
        )
        
        for memory in candidates:
            if should_forget(memory):
                archive_memory(memory)  # Soft delete
    
    def relevance_based_forgetting(self, threshold: float = 0.2):
        """Remove low-importance, rarely-used memories"""
        candidates = query_memories(
            importance_below=threshold,
            usage_count_below=2
        )
        
        for memory in candidates:
            if should_forget(memory):
                archive_memory(memory)
    
    def contradiction_based_forgetting(self):
        """Remove beliefs that have been contradicted"""
        beliefs = query_beliefs(has_contradictions=True)
        
        for belief in beliefs:
            if belief.confidence < 0.5:
                invalidate_belief(belief)
```

**Soft Delete**:

```python
def archive_memory(memory: Memory):
    """
    Soft delete: Mark as archived but don't remove
    Allows recovery if needed
    """
    memory.archived = True
    memory.archived_at = datetime.now()
    update_memory(memory)
```

---

## Working Memory

### Purpose

Working memory holds the active context for the current task. It's a subset of long-term memory plus current session state.

### Structure

```python
class WorkingMemory:
    # Current context
    current_goal: Goal | None
    current_plan: Plan | None
    current_step: Step | None
    
    # Recent history
    recent_messages: list[Message]      # Last 10 messages
    recent_tool_calls: list[ToolCall]   # Last 20 tool calls
    
    # Active memories
    active_beliefs: list[Belief]        # Relevant beliefs
    active_entities: list[Entity]       # Relevant entities
    active_procedures: list[Procedure]  # Relevant procedures
    active_strategies: list[Strategy]   # Relevant strategies
    
    # Context window
    context_tokens: int                 # Current token count
    max_tokens: int                     # Max context size
    
    def load_context(self, query: str):
        """Load relevant memories into working memory"""
        # Recall relevant memories
        memories = recall(MemoryQuery(
            query=query,
            limit=20,
            threshold=0.7
        ))
        
        # Categorize by network
        for memory in memories:
            if isinstance(memory, Belief):
                self.active_beliefs.append(memory)
            elif isinstance(memory, Entity):
                self.active_entities.append(memory)
            elif isinstance(memory, Procedure):
                self.active_procedures.append(memory)
            elif isinstance(memory, Strategy):
                self.active_strategies.append(memory)
        
        # Update token count
        self.context_tokens = calculate_tokens(self)
    
    def prune_context(self):
        """Remove least relevant memories to fit context window"""
        while self.context_tokens > self.max_tokens:
            # Remove lowest relevance memory
            least_relevant = find_least_relevant(self)
            remove_memory(least_relevant)
            self.context_tokens = calculate_tokens(self)
```

---

## Memory Embeddings

### Purpose

Embeddings enable semantic search and similarity matching.

### Implementation

```python
class EmbeddingManager:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.dimension = 1536  # OpenAI embedding dimension
        self.cache = {}
    
    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text"""
        # Check cache
        cache_key = hash(text)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Generate embedding
        response = openai.embeddings.create(
            model=self.model,
            input=text
        )
        
        embedding = response.data[0].embedding
        
        # Cache result
        self.cache[cache_key] = embedding
        
        return embedding
    
    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def find_similar(
        self,
        query_embedding: list[float],
        candidates: list[Memory],
        top_k: int = 10
    ) -> list[tuple[Memory, float]]:
        """Find most similar memories"""
        similarities = []
        
        for memory in candidates:
            if memory.embedding:
                similarity = self.cosine_similarity(
                    query_embedding,
                    memory.embedding
                )
                similarities.append((memory, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
```

---

## Storage Layer

### Database Schema

```sql
-- Beliefs table
CREATE TABLE beliefs (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    confidence REAL NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    tags TEXT,  -- JSON array
    entities TEXT,  -- JSON array
    evidence TEXT,  -- JSON array
    contradicts TEXT,  -- JSON array
    embedding BLOB,  -- Vector embedding
    archived BOOLEAN DEFAULT FALSE
);

-- Episodes table
CREATE TABLE episodes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type TEXT NOT NULL,
    content TEXT NOT NULL,
    participants TEXT,  -- JSON array
    context TEXT,  -- JSON object
    outcome TEXT,
    duration REAL,
    cost REAL,
    tags TEXT,  -- JSON array
    related_episodes TEXT,  -- JSON array
    archived BOOLEAN DEFAULT FALSE
);

-- Entities table
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    properties TEXT,  -- JSON object
    relationships TEXT,  -- JSON array
    mentions TEXT,  -- JSON array
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    tags TEXT,  -- JSON array
    embedding BLOB,
    archived BOOLEAN DEFAULT FALSE
);

-- Procedures table
CREATE TABLE procedures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    instructions TEXT NOT NULL,
    prerequisites TEXT,  -- JSON array
    steps TEXT,  -- JSON array
    tools TEXT,  -- JSON array
    success_criteria TEXT,
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    avg_duration REAL,
    avg_cost REAL,
    tags TEXT,  -- JSON array
    created_at TIMESTAMP NOT NULL,
    last_used TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE
);

-- Strategies table
CREATE TABLE strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    context TEXT,
    approach TEXT NOT NULL,
    examples TEXT,  -- JSON array
    effectiveness REAL,
    usage_count INTEGER DEFAULT 0,
    success_rate REAL,
    tags TEXT,  -- JSON array
    created_at TIMESTAMP NOT NULL,
    last_used TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE
);

-- Indices for fast lookup
CREATE INDEX idx_beliefs_tags ON beliefs(tags);
CREATE INDEX idx_beliefs_created ON beliefs(created_at);
CREATE INDEX idx_episodes_session ON episodes(session_id);
CREATE INDEX idx_episodes_timestamp ON episodes(timestamp);
CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_procedures_name ON procedures(name);
CREATE INDEX idx_strategies_name ON strategies(name);
```

---

## Performance Optimization

### 1. Caching

```python
class MemoryCache:
    def __init__(self, max_size: int = 1000):
        self.cache: dict[str, Memory] = {}
        self.max_size = max_size
        self.access_count: dict[str, int] = {}
    
    def get(self, memory_id: str) -> Memory | None:
        """Get memory from cache"""
        if memory_id in self.cache:
            self.access_count[memory_id] += 1
            return self.cache[memory_id]
        return None
    
    def put(self, memory: Memory):
        """Add memory to cache"""
        if len(self.cache) >= self.max_size:
            # Evict least recently used
            lru_id = min(self.access_count, key=self.access_count.get)
            del self.cache[lru_id]
            del self.access_count[lru_id]
        
        self.cache[memory.id] = memory
        self.access_count[memory.id] = 1
```

### 2. Batch Operations

```python
def batch_consolidate(memories: list[tuple[str, dict]]) -> list[Memory]:
    """Consolidate multiple memories in a single transaction"""
    with database.transaction():
        results = []
        for content, metadata in memories:
            memory = consolidate(content, metadata)
            results.append(memory)
        return results
```

### 3. Lazy Loading

```python
class LazyMemory:
    """Load memory content only when accessed"""
    def __init__(self, memory_id: str):
        self.id = memory_id
        self._content = None
        self._embedding = None
    
    @property
    def content(self) -> str:
        if self._content is None:
            self._content = load_content(self.id)
        return self._content
    
    @property
    def embedding(self) -> list[float]:
        if self._embedding is None:
            self._embedding = load_embedding(self.id)
        return self._embedding
```

---

## Summary

The Memory System provides:
- ✅ **5 memory networks**: Beliefs, Episodes, Entities, Procedures, Strategies
- ✅ **3 memory operations**: Recall, Consolidation, Forgetting
- ✅ **Working memory**: Active context management
- ✅ **Semantic search**: Embedding-based similarity
- ✅ **Efficient storage**: SQLite with indices
- ✅ **Performance optimization**: Caching, batching, lazy loading

**Key Features**:
- Persistent across sessions
- Fast recall (<100ms)
- Contextual and relevant
- Organized and queryable
- Privacy-respecting

**Next**: See `03-MULTI_AGENT_ORCHESTRATION.md` for multi-agent coordination.
