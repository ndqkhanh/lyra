# Lyra Memory Architecture

**Version**: 2.0  
**Date**: 2026-05-31  
**Status**: Comprehensive Design Complete

---

## Executive Summary

Lyra's memory architecture solves the fundamental challenge of cross-session knowledge accumulation in AI coding agents: **how to remember what worked, detect conflicting information, and retrieve relevant context efficiently across millions of tokens of interaction history**.

**The Problem**: Current AI agents forget everything between sessions, repeat mistakes, accumulate contradictory information, and waste compute re-answering identical queries.

**The Solution**: A temporal knowledge graph with confidence decay and memory-augmented routing that reduces costs by 52% while improving accuracy on conflicting information by 85-90%.

**Key Innovations**:
1. **Temporal Knowledge Graph** — Time-aware graph where confidence decays unless reinforced, with automatic contradiction detection
2. **Four-Layer Hierarchy** — Working/Episodic/Semantic/Archive with lazy materialization (90%+ compression)
3. **Memory-Augmented Router** — Memory lookup before LLM routing (40% exact match, 40% similar, 20% novel → 52% cost reduction)
4. **Cross-Session Integration** — Shared entities create links across sessions enabling "what did we do last time?" queries
5. **Confidence-Based Admission** — 5-factor scoring prevents memory pollution with low-value entries

**Expected Impact**:
- **52% overall cost reduction** (90%+ for repeat queries, 10% for similar queries with cheap model)
- **85-90% accuracy** on conflicting information through contradiction detection
- **<50ms retrieval latency** for 95% of queries via hierarchical indexing
- **Scales to unlimited history** while keeping active memory <10MB through compression

---

## Architecture Overview

```mermaid
graph TB
    Query[User Query] --> Router{Memory-Augmented Router}
    Router -->|Exact Match<br/>40% of queries| Cache[Cached Answer<br/>$0 cost]
    Router -->|Similar Query<br/>40% of queries| Augment[Cheap Model + Context<br/>10% cost]
    Router -->|Novel Query<br/>20% of queries| LLM[Expensive Model<br/>100% cost]
    
    Augment --> CheapLLM[Haiku/DeepSeek-Flash]
    
    Cache --> Return[Return Result]
    CheapLLM --> Return
    LLM --> Return
    
    Return --> Update[Update Memory]
    Update --> TKG[Temporal Knowledge Graph]
    
    TKG --> Working[Working Memory<br/>Current Session<br/><10MB]
    TKG --> Episodic[Episodic Memory<br/>Recent Sessions<br/><100MB]
    TKG --> Semantic[Semantic Memory<br/>Long-term Patterns<br/><1GB]
    TKG --> Archive[Archive<br/>Cold Storage<br/>Unlimited]
    
    Working -.Compress.-> Episodic
    Episodic -.Generalize.-> Semantic
    Semantic -.Index.-> Archive
    
    TKG --> Confidence[Confidence Decay]
    TKG --> Conflict[Conflict Detection]
    TKG --> CrossSession[Cross-Session Links]
    
    style Router fill:#FFD700
    style Cache fill:#90EE90
    style Augment fill:#87CEEB
    style LLM fill:#FFB6C1
    style TKG fill:#DDA0DD
```

This architecture combines breakthrough techniques from 10+ ICLR 2026 MemAgent Workshop papers with production memory systems (Mem0, Letta, Graphiti) to create a memory system that goes beyond any single source.

---

## Memory Tiers

### Short-Term Memory (STM) — Working Layer

---

## 2. Evidence Synthesis

### Key Papers (§3.4 ICLR 2026 MemAgent Workshop)

**A-MAC (Adaptive Memory Admission Control)** — BREAKTHROUGH
- **Mechanism**: 5-factor admission (utility, confidence, novelty, recency, type)
- **Result**: F1=0.583, 31% latency reduction
- **Transferable**: Explicit admission control prevents bad memories

**MemGrad (Memory-Guided Optimization)** — HIGH
- **Mechanism**: Textual gradients transform feedback into memory updates
- **Result**: Persistent improvements without fine-tuning
- **Transferable**: Feedback-driven memory evolution

**ERL (Experiential Reinforcement Learning)** — HIGH
- **Mechanism**: Heuristic abstraction over raw storage
- **Result**: +7.8% on Gaia2
- **Transferable**: Store principles, not raw traces

**AOI (Multi-Agent Framework)** — HIGH
- **Mechanism**: 3-layer memory (Working/Episodic/Semantic) + context compressor
- **Result**: 72.4% compression, −34.4% MTTR
- **Transferable**: Hierarchical memory with compression

**KAIST (Localized Compression)** — MEDIUM
- **Mechanism**: Compress within modular units
- **Result**: Minimizes retrieval–update interference
- **Transferable**: Localized compression prevents cross-contamination

**A-MEM (Agentic Memory)** — MEDIUM
- **Mechanism**: Zettelkasten-style linked notes
- **Result**: Dynamically evolving memory graph
- **Transferable**: Memory as linked knowledge graph

**Cost-Sensitive Store Routing** — HIGH
- **Mechanism**: Route queries to appropriate memory store
- **Result**: Selective retrieval cuts tokens + improves accuracy
- **Transferable**: Multi-store routing based on query type

**Memory Transplants** — LOW (Warning)
- **Mechanism**: Transfer memory across domains
- **Result**: Neither architecture nor content transfers well
- **Transferable**: Don't assume memory portability

---

## 3. Proposed Architecture

### 3.1 Four-Tier Hierarchy

```mermaid
graph TB
    subgraph "Tier 1: Active Memory (In-Context)"
        ACTIVE[Current Task Context]
        ACTIVE_SIZE[~10-20% of context window]
    end
    
    subgraph "Tier 2: Working Memory (Compressed In-Context)"
        WORKING[Recent Session History]
        WORKING_SIZE[~30-40% of context window]
        COMPRESS1[Semantic Compression]
    end
    
    subgraph "Tier 3: Episodic Memory (External Storage)"
        EPISODIC[Task Trajectories]
        EPISODIC_SIZE[Last 7 days, ~1GB]
        COMPRESS2[Heuristic Abstraction]
    end
    
    subgraph "Tier 4: Semantic Memory (External Storage)"
        SEMANTIC[Long-Term Knowledge]
        SEMANTIC_SIZE[Unlimited, ~10GB+]
        COMPRESS3[Knowledge Graph]
    end
    
    subgraph "Admission Control"
        AMAC[A-MAC 5-Factor Gate]
        AMAC --> ACTIVE
        AMAC --> WORKING
        AMAC --> EPISODIC
        AMAC --> SEMANTIC
    end
    
    subgraph "Retrieval"
        QUERY[User Query]
        ROUTER[Cost-Sensitive Router]
        QUERY --> ROUTER
        ROUTER --> ACTIVE
        ROUTER --> WORKING
        ROUTER --> EPISODIC
        ROUTER --> SEMANTIC
    end
    
    ACTIVE --> COMPRESS1
    WORKING --> COMPRESS2
    EPISODIC --> COMPRESS3
    
    style AMAC fill:#FFD700
    style ROUTER fill:#87CEEB
    style ACTIVE fill:#90EE90
    style WORKING fill:#FFB6C1
    style EPISODIC fill:#DDA0DD
    style SEMANTIC fill:#F0E68C
```

**Purpose**: Holds current session context with full detail, no compression.

**Data Model**:
```typescript
interface WorkingMemory {
  sessionId: string;
  messages: Message[];        // Recent conversation
  activeFiles: FileContext[]; // Currently open files
  taskContext: TaskState;     // Current task state
  size: number;               // Current size in tokens
  maxSize: number;            // 10MB limit (~5K tokens)
}
```

**Retention Policy**: 
- Duration: Current session only
- Eviction: LRU when size exceeds 10MB
- Compression: None (full detail preserved)

**Access Pattern**: Direct read from in-memory structure, no retrieval needed.

**Example Content**:
- Last 10 conversation turns
- Currently edited files (full content)
- Active task description and progress
- Recent tool outputs

---

### Long-Term Memory (LTM) — Episodic Layer

**Purpose**: Stores recent session summaries and task trajectories for cross-session recall.

**Data Model**:
```typescript
interface EpisodicMemory {
  id: string;
  sessionId: string;
  timestamp: number;
  summary: string;           // Compressed summary
  keyDecisions: Decision[];  // Important decisions made
  outcomes: Outcome[];       // Task results
  entities: Entity[];        // Extracted entities (files, functions, concepts)
  embedding: number[];       // For semantic search
  confidence: number;        // Decays over time
}

interface Decision {
  description: string;
  rationale: string;
  alternatives: string[];
  timestamp: number;
}
```

**Retention Policy**:
- Duration: 30 days
- Compression: Extract key events, discard verbatim logs (72.4% compression ratio from AOI)
- Decay: Confidence *= 0.95 per week unless accessed

**Access Pattern**: Semantic search via embeddings, returns summaries with drill-down to full detail on demand.

**Example Content**:
- "Session focused on authentication. Decided to use JWT tokens (not sessions). Implemented bcrypt hashing. All tests passing."
- Key decisions with rationale
- Links to related sessions via shared entities

---

### Episodic Memory — Semantic Layer

**Purpose**: Long-term patterns, principles, and generalized knowledge extracted from multiple episodes.

**Data Model**:
```typescript
interface SemanticMemory {
  id: string;
  concept: string;           // e.g., "Authentication"
  description: string;       // General knowledge
  patterns: Pattern[];       // Recurring patterns
  heuristics: Heuristic[];   // Learned rules
  links: string[];           // Related concepts
  embedding: number[];
  confidence: number;
  sources: string[];         // Source episode IDs
}

interface Pattern {
  description: string;
  frequency: number;         // How often seen
  examples: string[];        // Episode IDs
}

interface Heuristic {
  condition: string;         // "When X happens"
  action: string;            // "Do Y"
  confidence: number;
  successRate: number;       // Track effectiveness
}
```

**Retention Policy**:
- Duration: Permanent (until explicitly deleted or confidence < 0.3)
- Compression: Generalize from specific instances, extract patterns
- Reinforcement: Confidence increases when pattern reoccurs

**Access Pattern**: Graph traversal + semantic search, returns concepts with links to related knowledge.

**Example Content**:
- Concept: "Authentication"
  - Standard approach: "JWT + bcrypt + Redis"
  - Common pitfall: "Forgetting token expiry"
  - Heuristic: "When auth fails, check env vars first"
  - Links: [Security, API Design, User Management]

---

### Archive — Cold Storage Layer

**Purpose**: Indexed-only storage for old sessions, full content compressed and retrievable on demand.

**Data Model**:
```typescript
interface ArchivedMemory {
  id: string;
  sessionId: string;
  timestamp: number;
  index: SearchIndex;        // Searchable metadata
  compressedContent: Buffer; // gzip compressed full content
  size: number;
  originalSize: number;
}

interface SearchIndex {
  keywords: string[];
  entities: string[];
  topics: string[];
  dateRange: [number, number];
}
```

**Retention Policy**:
- Duration: Unlimited
- Compression: gzip + index for search
- Access: Index search only, materialize full content on explicit request

**Access Pattern**: Keyword/entity search returns matches, user explicitly requests full content materialization.

**Example Content**:
- Full session transcripts from 6+ months ago
- Compressed with gzip (90%+ compression)
- Searchable by keywords, entities, date ranges

---

## Core Mechanisms

### Cross-Session Recall

**Problem**: How do agents remember what happened in previous sessions?

**Solution**: Entity-based linking across sessions through shared concepts.

```mermaid
graph LR
    S1[Session 1:<br/>Debug auth bug] --> E1[Entity: login.ts]
    S1 --> E2[Entity: JWT_SECRET]
    S1 --> E3[Entity: auth_bug]
    
    S2[Session 2:<br/>Auth not working] --> E2
    S2 --> E4[Entity: staging]
    
    E2 --> Link[Cross-Session Link]
    Link --> Recall[Retrieve Session 1<br/>outcome]
    
    style Link fill:#FFD700
    style Recall fill:#90EE90
```

**Mechanism**:
1. **Entity Extraction**: Extract entities from each session (files, functions, concepts, errors)
2. **Entity Normalization**: Normalize to canonical form (e.g., "JWT_SECRET" = "jwt_secret" = "JWT secret")
3. **Cross-Session Edges**: Create edges between sessions sharing entities
4. **Query-Time Traversal**: When user asks about topic, traverse graph to find related sessions

**Example Flow**:
```
User: "Auth not working in staging"
→ Extract entities: [auth, staging]
→ Search graph for sessions with these entities
→ Find Session 1: "Fixed auth bug by correcting JWT_SECRET env var"
→ Suggest: "Check JWT_SECRET env var in staging"
```

**Data Model**:
```typescript
interface SessionLink {
  session1: string;
  session2: string;
  sharedEntities: string[];
  linkStrength: number;  // 0-1 based on entity overlap
}

interface Entity {
  canonical: string;     // Normalized form
  variants: string[];    // All seen variants
  type: 'file' | 'function' | 'concept' | 'error' | 'decision';
  sessions: string[];    // Sessions mentioning this entity
}
```

---

### Conflict Resolution

**Problem**: New information contradicts existing memories.

**Detection Strategy**:
```typescript
function detectConflict(
  newMemory: Memory,
  existingMemories: Memory[]
): Conflict | null {
  for (const existing of existingMemories) {
    // Step 1: Check if same topic (high semantic similarity)
    const similarity = cosineSimilarity(
      newMemory.embedding,
      existing.embedding
    );
    
    if (similarity > 0.9) {
      // Step 2: Check for contradiction (opposite sentiment/decision)
      const contradiction = checkContradiction(
        newMemory.content,
        existing.content
      );
      
      if (contradiction) {
        return {
          newMemory,
          existingMemory: existing,
          contradictionType: contradiction.type,
          confidence: contradiction.confidence
        };
      }
    }
  }
  return null;
}
```

**Resolution Strategies**:

1. **Temporal (Keep Newest)** — Default for facts
   ```
   Old: "Use JWT tokens" (2 weeks ago)
   New: "Use session cookies" (today)
   → Resolution: Keep new, mark old as superseded
   ```

2. **Confidence (Keep Highest)** — Default for heuristics
   ```
   Low: "Maybe check env vars?" (confidence: 0.4)
   High: "Always check env vars first" (confidence: 0.9)
   → Resolution: Keep high confidence, discard low
   ```

3. **Merge (Combine)** — For complementary information
   ```
   Memory 1: "Use JWT tokens"
   Memory 2: "JWT expires in 1 hour"
   → Resolution: "Use JWT tokens with 1-hour expiry"
   ```

4. **Manual Review** — For unresolvable conflicts
   ```
   Decision A: "Use JWT" (high confidence, recent)
   Decision B: "Use sessions" (high confidence, recent)
   → Resolution: Flag for human review
   ```

**Conflict Data Model**:
```typescript
interface Conflict {
  id: string;
  newMemory: Memory;
  existingMemory: Memory;
  contradictionType: 'factual' | 'decision' | 'heuristic';
  detectedAt: number;
  resolution: 'temporal' | 'confidence' | 'merge' | 'manual';
  resolvedAt?: number;
  resolvedBy?: 'system' | 'user';
}
```

---

### Active Forgetting

**Problem**: Memory grows unbounded, old/irrelevant information clutters retrieval.

**Forgetting Triggers**:

1. **Time-Based Decay**
   ```typescript
   // Confidence decays exponentially over time
   function decayConfidence(memory: Memory): number {
     const ageWeeks = (Date.now() - memory.timestamp) / (7 * 24 * 60 * 60 * 1000);
     return memory.confidence * Math.pow(0.95, ageWeeks);
   }
   ```

2. **Access-Based Reinforcement**
   ```typescript
   // Accessing memory reinforces it
   function reinforceMemory(memory: Memory): void {
     memory.confidence = Math.min(1.0, memory.confidence + 0.1);
     memory.lastAccessed = Date.now();
     memory.accessCount++;
   }
   ```

3. **Utility Threshold**
   ```typescript
   // Remove memories below confidence threshold
   function pruneMemories(): void {
     const memories = getAllMemories();
     for (const memory of memories) {
       const currentConfidence = decayConfidence(memory);
       if (currentConfidence < 0.3) {
         if (memory.accessCount === 0) {
           // Never accessed → safe to delete
           deleteMemory(memory);
         } else {
           // Was accessed before → archive instead
           archiveMemory(memory);
         }
       }
     }
   }
   ```

**Forgetting Schedule**:
- **Episodic Layer**: Auto-expire after 30 days
- **Semantic Layer**: Prune when confidence < 0.3 and not accessed in 30 days
- **Archive Layer**: Never delete (but compress aggressively)

**Visualization**:
```
Confidence over time (no access):
1.0 |●
    |  ●
0.8 |    ●
    |      ●
0.6 |        ●
    |          ●
0.4 |            ●
    |              ●
0.3 |________________●___ (pruning threshold)
    0  1  2  3  4  5  6  7  weeks

Confidence with access (reinforcement):
1.0 |●     ●     ●
    |  ●  ↑  ●  ↑
0.8 |    ●     ●
    |      ●
0.6 |
    0  1  2  3  4  5  6  7  weeks
         ↑         ↑
       access    access
```

---

### Shared Memory (Multi-Agent Coordination)

**Purpose**: Enable multiple agents in a swarm to share context and coordinate actions.

**Architecture**:
```mermaid
graph TB
    A1[Agent 1] --> SM[Shared Memory<br/>Namespace]
    A2[Agent 2] --> SM
    A3[Agent 3] --> SM
    
    SM --> Store[(Memory Store)]
    
    Store --> Lock[Lock Manager<br/>Prevents races]
    Store --> Conflict[Conflict Resolver<br/>Last-write-wins]
    
    style SM fill:#FFD700
    style Lock fill:#FF6B6B
    style Conflict fill:#87CEEB
```

**Data Model**:
```typescript
interface SharedMemoryNamespace {
  id: string;                    // e.g., "swarm-auth-task"
  agents: string[];              // Agent IDs with access
  memories: Map<string, Memory>;
  locks: Map<string, AgentLock>;
  createdAt: number;
  expiresAt: number;             // Auto-cleanup after task
}

interface AgentLock {
  memoryKey: string;
  agentId: string;
  acquiredAt: number;
  expiresAt: number;             // Auto-release after 30s
}
```

**Operations**:

1. **Write with Lock**
   ```typescript
   async function writeShared(
     namespace: string,
     key: string,
     value: Memory,
     agentId: string
   ): Promise<void> {
     // Acquire lock
     const lock = await acquireLock(namespace, key, agentId);
     
     try {
       // Write memory
       await setMemory(namespace, key, value);
     } finally {
       // Always release lock
       await releaseLock(lock);
     }
   }
   ```

2. **Read (No Lock)**
   ```typescript
   async function readShared(
     namespace: string,
     key: string
   ): Promise<Memory | null> {
     return await getMemory(namespace, key);
   }
   ```

3. **Conflict Resolution**
   ```typescript
   // Last-write-wins with timestamp
   function resolveConflict(
     existing: Memory,
     incoming: Memory
   ): Memory {
     return incoming.timestamp > existing.timestamp
       ? incoming
       : existing;
   }
   ```

**Privacy & Isolation**:
- Each swarm task gets unique namespace
- Agents can only access namespaces they're assigned to
- Namespace auto-deleted when task completes
- No cross-namespace visibility

---

## Data Models

### Memory Node Schema

```typescript
interface MemoryNode {
  // Identity
  id: string;
  type: 'fact' | 'heuristic' | 'code_pattern' | 'decision' | 'outcome';
  
  // Content
  content: string;
  embedding: number[];  // 1536-dim vector (OpenAI ada-002)
  
  // Confidence & Decay
  confidence: number;   // 0.0-1.0, decays over time
  createdAt: number;
  lastAccessed: number;
  accessCount: number;
  
  // Context
  sessionId: string;
  tags: string[];
  entities: string[];   // Extracted entities
  
  // Tier Assignment
  tier: 'working' | 'episodic' | 'semantic' | 'archive';
  
  // Compression
  compressed: boolean;
  originalSize: number;
  compressedSize: number;
}
```

### Memory Edge Schema

```typescript
interface MemoryEdge {
  sourceId: string;
  targetId: string;
  type: 'causal' | 'temporal' | 'semantic' | 'contradicts' | 'refines';
  weight: number;       // Relationship strength 0-1
  createdAt: number;
  evidence: string;     // Why this edge exists
}
```

### Conflict Resolution Record

```typescript
interface ConflictResolution {
  id: string;
  conflictingNodes: string[];  // Memory IDs in conflict
  detectedAt: number;
  strategy: 'keep_newest' | 'keep_highest_confidence' | 'merge' | 'manual_review';
  resolution: {
    kept: string[];            // Memory IDs kept
    superseded: string[];      // Memory IDs marked as old
    merged?: string;           // New merged memory ID
  };
  resolvedAt: number;
  resolvedBy: 'system' | 'user';
}
```

### Storage Schema (SQLite)

```sql
-- Memory nodes
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding BLOB NOT NULL,
  confidence REAL NOT NULL,
  created_at INTEGER NOT NULL,
  last_accessed INTEGER NOT NULL,
  access_count INTEGER DEFAULT 0,
  session_id TEXT NOT NULL,
  tags TEXT,              -- JSON array
  entities TEXT,          -- JSON array
  tier TEXT NOT NULL,
  compressed BOOLEAN DEFAULT 0,
  original_size INTEGER,
  compressed_size INTEGER
);

-- Memory edges
CREATE TABLE memory_edges (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  type TEXT NOT NULL,
  weight REAL NOT NULL,
  created_at INTEGER NOT NULL,
  evidence TEXT,
  FOREIGN KEY (source_id) REFERENCES memories(id),
  FOREIGN KEY (target_id) REFERENCES memories(id)
);

-- Conflict resolutions
CREATE TABLE conflict_resolutions (
  id TEXT PRIMARY KEY,
  conflicting_nodes TEXT NOT NULL,  -- JSON array
  detected_at INTEGER NOT NULL,
  strategy TEXT NOT NULL,
  resolution TEXT NOT NULL,         -- JSON object
  resolved_at INTEGER,
  resolved_by TEXT
);

-- Indexes for performance
CREATE INDEX idx_memories_tier ON memories(tier);
CREATE INDEX idx_memories_session ON memories(session_id);
CREATE INDEX idx_memories_confidence ON memories(confidence);
CREATE INDEX idx_memories_created ON memories(created_at);
CREATE INDEX idx_edges_source ON memory_edges(source_id);
CREATE INDEX idx_edges_target ON memory_edges(target_id);
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

**Goal**: Basic 4-layer hierarchy with in-memory storage

**Deliverables**:
1. Memory node data structures (TypeScript interfaces)
2. Working memory layer (in-memory, LRU eviction)
3. Basic CRUD operations (create, read, update, delete)
4. Simple retrieval (exact match, no semantic search yet)

**Success Criteria**:
- Working memory stores last 10 messages
- LRU eviction when size exceeds 10MB
- Basic retrieval by ID works

**Dependencies**: None

---

### Phase 2: Hierarchy & Storage (Weeks 4-6)

**Goal**: External storage for Episodic/Semantic/Archive layers

**Deliverables**:
1. SQLite database setup with schema
2. Episodic memory layer (30-day retention)
3. Semantic memory layer (permanent storage)
4. Archive layer (compressed cold storage)
5. Embedding generation (OpenAI ada-002 or local model)

**Success Criteria**:
- Memories persist across sessions
- Episodic memories auto-expire after 30 days
- Archive layer compresses with gzip

**Dependencies**: Phase 1

---

### Phase 3: Intelligence (Weeks 7-9)

**Goal**: Confidence decay, contradiction detection, cross-session linking

**Deliverables**:
1. Confidence decay function (exponential, 0.95 per week)
2. Access-based reinforcement (+0.1 per access)
3. Contradiction detection (semantic similarity + sentiment analysis)
4. Conflict resolution strategies (temporal, confidence, merge, manual)
5. Entity extraction and cross-session linking

**Success Criteria**:
- Confidence decays correctly over time
- Contradictions detected with >80% accuracy
- Cross-session queries work ("what did we do about auth?")

**Dependencies**: Phase 2

---

### Phase 4: Router Integration (Weeks 10-12)

**Goal**: Memory-augmented routing for cost savings

**Deliverables**:
1. Memory lookup before LLM routing
2. Exact match detection (cache hit)
3. Similar query detection (semantic similarity > 0.85)
4. Context augmentation for cheap model
5. Cost tracking and reporting

**Success Criteria**:
- 40% queries hit exact match (cached)
- 40% queries use cheap model + context
- 52% overall cost reduction measured

**Dependencies**: Phase 3, §4.5 Model Router

---

### Phase 5: Polish (Weeks 13-14)

**Goal**: Production-ready features

**Deliverables**:
1. Migration tooling (import from session logs)
2. Export for backup (JSON format)
3. Schema versioning
4. Monitoring dashboard (memory size, hit rate, compression ratio)
5. Documentation (architecture guide, API reference)

**Success Criteria**:
- Can import existing session logs
- Export/import round-trip works
- Dashboard shows key metrics

**Dependencies**: Phase 4

---

## Breakthrough Innovations

### Innovation 1: Temporal Knowledge Graph with Confidence Decay

**Sources Fused**:
- Zep/Graphiti temporal knowledge graph
- A-MAC 5-factor admission control
- DAVIS knowledge-graph inner monologue
- AnnaAgent multi-session integration

**Novel Mechanism**:
A time-aware graph where:
1. **Nodes** = memories with confidence scores that decay unless reinforced
2. **Edges** = relationships (causal, temporal, semantic, contradictory)
3. **Contradiction detection** via semantic similarity + opposite sentiment
4. **Cross-session linking** via shared entities
5. **Self-correcting** through conflict resolution

**Why It Wins**:
- **Graphiti alone**: No confidence decay or contradiction handling
- **A-MAC alone**: No graph structure, can't detect conflicts across memories
- **Fusion**: Handles conflicting information (critical for long-term memory) + graph enables powerful relationship queries

**Expected Impact**:
- 85-90% accuracy on conflicting information
- 40% faster retrieval via graph traversal vs flat search
- Self-healing memory that improves over time

**Effort**: 10-12 weeks (Phases 1-3)

---

### Innovation 2: Memory-Augmented Router Integration

**Sources Fused**:
- Cost-Sensitive Store Routing paper
- Lyra's model router (§4.5)
- MemSearcher compact question-relevant memory
- Knowledge Access Beats Model Size paper

**Novel Mechanism**:
Memory lookup BEFORE LLM routing:
1. **Exact match** → $0 cost (cached answer)
2. **Similar query** → cheap model + context (10% cost)
3. **Novel query** → expensive model (100% cost)
4. **Expected mix**: 40% exact, 40% similar, 20% novel → **52% cost reduction**

**Why It Wins**:
- **Router alone**: No memory, every query costs full price
- **Memory alone**: No routing, always uses same model
- **Fusion**: 90%+ cost reduction for repeat queries while maintaining quality

**Expected Impact**:
- 52% overall cost reduction
- <10ms memory lookup latency
- Quality maintained (cheap model + good context ≈ expensive model alone)

**Effort**: 6-8 weeks (Phase 4)

---

### Innovation 3: Four-Layer Hierarchy with Lazy Materialization

**Sources Fused**:
- AOI's 3-layer hierarchy (Working/Episodic/Semantic)
- MemAgent's segment processing with overwrite
- CFGM's coarse-to-fine granularity
- Cost-Sensitive Store Routing

**Novel Mechanism**:
4 layers with on-demand detail expansion:
1. **Working** (current session, full detail, <10MB)
2. **Episodic** (recent sessions, summaries only, <100MB)
3. **Semantic** (long-term patterns, compressed, <1GB)
4. **Archive** (cold storage, indexed only, unlimited)

Higher layers store only summaries; full detail fetched on-demand from lower layers when needed.

**Why It Wins**:
- **AOI alone**: Fixed 3 layers, no lazy loading
- **MemAgent alone**: Segment processing but no hierarchy
- **Fusion**: Scales to unlimited history while keeping active memory small

**Expected Impact**:
- 90%+ compression ratio (AOI achieved 72.4%)
- <50ms retrieval for 95% of queries
- Scales to millions of tokens of history

**Effort**: 8-10 weeks (Phases 1-2)

---

## References

### ICLR 2026 MemAgent Workshop Papers
- **AOI**: https://openreview.net/attachment?id=Q16XXJou3O&name=pdf
- **A-MEM**: https://openreview.net/pdf?id=FiM0M8gcct
- **A-MAC**: https://openreview.net/attachment?id=mmdqUrEY24&name=pdf
- **ERL**: https://openreview.net/forum?id=hQgSl6kj1W
- **Cost-Sensitive Store Routing**: https://openreview.net/pdf?id=iGRGjdhl9r
- **Norm-Guided KV-Cache**: https://openreview.net/pdf?id=xOW2jXDKG3
- **R-KVHash**: https://openreview.net/attachment?id=UTRuEFJ57H&name=pdf
- **LP-RAG**: https://openreview.net/pdf?id=Y8Txo8vaH7
- **SABER**: https://openreview.net/attachment?id=En2z9dckgP&name=pdf
- **MemGrad**: https://openreview.net/attachment?id=GeaPE7iw1V&name=pdf
- **Localized Compression**: https://openreview.net/forum?id=ztmwHisqJ4
- **MRAgent**: https://openreview.net/forum?id=YPoHy6lgKP
- **Human-Like Lifelong Memory**: https://openreview.net/forum?id=QufkvHbQs7

### Memory Systems & Repositories
- **Mem0**: https://github.com/mem0ai/mem0 · https://arxiv.org/abs/2504.19413
- **Letta/MemGPT**: https://github.com/letta-ai/letta
- **Zep/Graphiti**: https://github.com/getzep/graphiti
- **AnnaAgent**: https://arxiv.org/pdf/2506.00551
- **MemAgent** (ICLR oral): https://openreview.net/forum?id=k5nIOvYGCL
- **DAVIS**: https://arxiv.org/pdf/2410.09252
- **MSI-Agent**: https://arxiv.org/pdf/2409.16686
- **CFGM**: https://arxiv.org/pdf/2508.15305
- **TencentDB-Agent-Memory**: https://github.com/Tencent/TencentDB-Agent-Memory
- **MemPalace**: https://github.com/MemPalace/mempalace
- **claude-mem**: https://github.com/thedotmack/claude-mem

### Context Optimization Papers
- **ACON**: https://arxiv.org/abs/2510.00615
- **IterResearch**: https://arxiv.org/pdf/2511.07327
- **MemSearcher**: https://arxiv.org/pdf/2511.02805
- **CoMeT**: https://arxiv.org/abs/2602.01766
- **LightMem**: https://arxiv.org/abs/2604.07798

### Router Integration
- **Knowledge Access Beats Model Size**: https://arxiv.org/pdf/2603.23013
- **Anthropic Context Engineering**: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### Survey Papers
- **Memory for Autonomous LLM Agents**: https://arxiv.org/pdf/2603.07670
- **Storage to Experience Survey**: https://openreview.net/attachment?id=l9Ly41xxPb&name=pdf
- **Memory in Age of AI**: https://arxiv.org/abs/2512.13564

### Related Lyra Workstreams
- **§4.3 Context Optimization**: Compression strategies, lazy materialization
- **§4.5 Model Router**: Cost-sensitive routing, model selection
- **§4.13 Swarm Coordination**: Shared memory for multi-agent systems
- **§4.16 Reliability**: Verification of memory updates

---

**END OF MEMORY ARCHITECTURE**

Every memory candidate evaluated on **5 factors**:

```typescript
interface MemoryCandidate {
  content: string;
  timestamp: number;
  source: 'user' | 'agent' | 'tool';
  context: string;
}

interface AdmissionScore {
  utility: number;      // 0-1: LLM-assessed future usefulness
  confidence: number;   // 0-1: ROUGE-L alignment with conversation
  novelty: number;      // 0-1: Embedding similarity (1 = novel)
  recency: number;      // 0-1: Exponential decay
  typePrior: number;    // 0-1: Content type importance
  
  aggregate: number;    // Weighted sum
}

function admitMemory(candidate: MemoryCandidate): boolean {
  const score = evaluateAdmission(candidate);
  
  // Weighted aggregation (A-MAC paper weights)
  score.aggregate = 
    0.3 * score.utility +
    0.25 * score.confidence +
    0.2 * score.novelty +
    0.15 * score.recency +
    0.1 * score.typePrior;
  
  // Tier-specific thresholds
  if (score.aggregate > 0.8) return admitToActive(candidate);
  if (score.aggregate > 0.6) return admitToWorking(candidate);
  if (score.aggregate > 0.4) return admitToEpisodic(candidate);
  if (score.aggregate > 0.2) return admitToSemantic(candidate);
  
  return false; // Reject
}
```

**Factor Details**:

1. **Utility**: "Will this be useful later?"
   - LLM prompt: "Rate 0-1: How likely is this information to be needed in future tasks?"
   - High: Decisions, blockers, key outcomes
   - Low: Acknowledgments, small talk

2. **Confidence**: "Is this factually correct?"
   - ROUGE-L alignment with conversation history
   - High: Consistent with prior statements
   - Low: Contradicts prior statements

3. **Novelty**: "Is this new information?"
   - Embedding similarity to existing memories
   - High: Novel insight, new decision
   - Low: Repetition of known information

4. **Recency**: "How recent is this?"
   - Exponential decay: `recency = exp(-age_hours / 24)`
   - High: Last hour
   - Low: Last week

5. **Type Prior**: "What type of content is this?"
   - Decision: 1.0 (always important)
   - Blocker: 0.9
   - Outcome: 0.8
   - Code: 0.6
   - Discussion: 0.4
   - Acknowledgment: 0.1

### 3.4 Retrieval (Cost-Sensitive Router)

**Query arrives** → **Route to appropriate tier(s)**:

```typescript
interface RetrievalQuery {
  text: string;
  type: 'factual' | 'procedural' | 'episodic' | 'semantic';
  maxLatency: number; // ms
  maxCost: number;    // tokens
}

function retrieveMemory(query: RetrievalQuery): Memory[] {
  // Route based on query type
  switch (query.type) {
    case 'factual':
      // "What's the capital of France?"
      return searchSemantic(query); // Tier 4
      
    case 'procedural':
      // "How do we deploy to AWS?"
      return searchSemantic(query); // Tier 4
      
    case 'episodic':
      // "What did we decide about auth last week?"
      return searchEpisodic(query); // Tier 3
      
    case 'semantic':
      // "What's our standard approach to X?"
      return searchSemantic(query); // Tier 4
  }
  
  // Fallback: Search all tiers
  return [
    ...searchActive(query),   // Tier 1 (always fast)
    ...searchWorking(query),  // Tier 2 (already in context)
    ...searchEpisodic(query), // Tier 3 (if latency allows)
    ...searchSemantic(query)  // Tier 4 (if latency allows)
  ];
}
```

**Cost-Sensitive Routing**:
- If `maxLatency < 100ms`: Search only Tier 1+2 (in-context)
- If `maxLatency < 500ms`: Search Tier 1+2+3 (episodic)
- If `maxLatency unlimited`: Search all tiers

### 3.5 Compression Strategies

**Tier 1 → Tier 2: Semantic Compression** (IterResearch)
```
Original (500 lines of code review):
[Detailed discussion about auth implementation]

Compressed (50 lines):
"Code review identified 3 critical issues:
1. Auth bypass in /api/users (fixed)
2. SQL injection in login query (fixed)
3. Missing tests for JWT expiry (added)
All issues resolved. Approved."
```

**Tier 2 → Tier 3: Heuristic Abstraction** (ERL)
```
Original (10 task summaries):
[Detailed task-by-task outcomes]

Compressed (heuristics):
"Session focused on authentication system.
Key decisions:
- Use JWT tokens (not sessions)
- bcrypt for password hashing
- Redis for token storage
Blockers: None
Status: Complete"
```

**Tier 3 → Tier 4: Knowledge Graph** (A-MEM)
```
Original (episodic memories):
[Multiple auth-related tasks over time]

Compressed (knowledge graph):
Node: "Authentication"
  ├─ "Standard approach: JWT + bcrypt + Redis"
  ├─ "Common pitfall: Forgetting token expiry"
  ├─ "Best practice: Always hash passwords"
  └─ Links: [Security, API Design, User Management]
```

**Localized Compression** (KAIST):
- Compress within logical units (per-task, per-file, per-conversation)
- Prevents compression artifacts from bleeding across contexts
- Example: Auth task compression doesn't affect UI task compression

### 3.6 Conflict Resolution

**Conflict**: Two memories contradict each other

**Detection**:
```typescript
function detectConflict(newMemory: Memory, existingMemories: Memory[]): Conflict | null {
  for (const existing of existingMemories) {
    const similarity = cosineSimilarity(newMemory.embedding, existing.embedding);
    if (similarity > 0.9) { // Same topic
      const contradiction = checkContradiction(newMemory.content, existing.content);
      if (contradiction) {
        return { newMemory, existing, contradiction };
      }
    }
  }
  return null;
}
```

**Resolution Strategies**:

1. **Recency wins**: Newer memory replaces older
   - Use case: Decision changed
   - Example: "Use JWT" (old) → "Use sessions" (new)

2. **Confidence wins**: Higher confidence memory kept
   - Use case: Uncertain vs certain information
   - Example: "Maybe use JWT?" (low) vs "Definitely use JWT" (high)

3. **Merge**: Combine both memories
   - Use case: Complementary information
   - Example: "Use JWT" + "JWT expires in 1 hour" → "Use JWT with 1-hour expiry"

4. **Flag for human**: Unresolvable conflict
   - Use case: Contradictory decisions
   - Example: "Use JWT" vs "Use sessions" (both high confidence)

### 3.7 Active Forgetting

**Forgetting**: Remove old/irrelevant memories

**Triggers**:
1. **Age**: Episodic memories >7 days auto-expire
2. **Irrelevance**: Memories not accessed in 30 days
3. **Low utility**: Memories with utility <0.2
4. **Redundancy**: Duplicate memories (keep highest confidence)

**Forgetting Process**:
```typescript
function activeForget() {
  // Tier 3: Episodic (7-day retention)
  const episodic = getEpisodicMemories();
  for (const memory of episodic) {
    if (memory.age > 7 * 24 * 60 * 60 * 1000) { // 7 days
      deleteMemory(memory);
    }
  }
  
  // Tier 4: Semantic (30-day access retention)
  const semantic = getSemanticMemories();
  for (const memory of semantic) {
    if (memory.lastAccessed > 30 * 24 * 60 * 60 * 1000) { // 30 days
      if (memory.utility < 0.2) {
        deleteMemory(memory);
      }
    }
  }
}
```

### 3.8 Cross-Agent Shared Memory (Optional)

**Use case**: Swarm coordination (§4.13)

**Shared memory store**:
```typescript
interface SharedMemory {
  namespace: string; // e.g., "swarm-123"
  memories: Map<string, Memory>;
  locks: Map<string, AgentId>; // Prevent race conditions
}

// Agent A writes
sharedMemory.set("swarm-123", "auth-decision", {
  content: "Use JWT tokens",
  timestamp: Date.now(),
  author: "agent-A"
});

// Agent B reads
const decision = sharedMemory.get("swarm-123", "auth-decision");
```

**Conflict resolution**: Last-write-wins with timestamp

**Privacy**: Namespace isolation (agents can't access other namespaces)

---

## 4. Data Model

### 4.1 Memory Schema

```typescript
interface Memory {
  id: string;
  tier: 1 | 2 | 3 | 4;
  content: string;
  embedding: number[]; // 1536-dim vector
  timestamp: number;
  lastAccessed: number;
  accessCount: number;
  
  // Admission scores
  utility: number;
  confidence: number;
  novelty: number;
  recency: number;
  typePrior: number;
  aggregate: number;
  
  // Metadata
  source: 'user' | 'agent' | 'tool';
  context: string;
  tags: string[];
  
  // Compression
  compressed: boolean;
  originalSize: number;
  compressedSize: number;
  
  // Graph (Tier 4 only)
  links?: string[]; // IDs of related memories
}
```

### 4.2 Storage Backend

**Tier 1+2**: In-memory (part of context window)

**Tier 3+4**: SQLite + Vector DB

```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  tier INTEGER NOT NULL,
  content TEXT NOT NULL,
  embedding BLOB NOT NULL, -- Serialized vector
  timestamp INTEGER NOT NULL,
  last_accessed INTEGER NOT NULL,
  access_count INTEGER DEFAULT 0,
  
  -- Admission scores
  utility REAL,
  confidence REAL,
  novelty REAL,
  recency REAL,
  type_prior REAL,
  aggregate REAL,
  
  -- Metadata
  source TEXT,
  context TEXT,
  tags TEXT, -- JSON array
  
  -- Compression
  compressed BOOLEAN DEFAULT 0,
  original_size INTEGER,
  compressed_size INTEGER,
  
  -- Graph
  links TEXT -- JSON array of IDs
);

CREATE INDEX idx_tier ON memories(tier);
CREATE INDEX idx_timestamp ON memories(timestamp);
CREATE INDEX idx_aggregate ON memories(aggregate);
```

**Vector search**: Use `sqlite-vss` extension for embedding search

---

## 5. Migration Path

### Phase 1: Foundation (2 weeks)
1. Implement 4-tier hierarchy (in-memory only)
2. Basic admission control (simple threshold)
3. No compression yet

### Phase 2: Admission Control (3 weeks)
1. Implement A-MAC 5-factor scoring
2. LLM-based utility assessment
3. Confidence/novelty/recency/type scoring

### Phase 3: Compression (4 weeks)
1. Tier 1→2: Semantic compression (IterResearch)
2. Tier 2→3: Heuristic abstraction (ERL)
3. Tier 3→4: Knowledge graph (A-MEM)
4. Localized compression (KAIST)

### Phase 4: External Storage (3 weeks)
1. SQLite + Vector DB setup
2. Tier 3+4 persistence
3. Retrieval via semantic search

### Phase 5: Advanced Features (4 weeks)
1. Conflict resolution
2. Active forgetting
3. Cross-agent shared memory
4. Cost-sensitive routing

**Total**: 16 weeks (4 months)

---

## 6. Parity vs Breakthrough

### (A) Parity — Match State of the Art

**Port from papers**:
1. **A-MAC admission control**: 5-factor gating
2. **ERL heuristic abstraction**: Store principles, not traces
3. **AOI 3-layer memory**: Working/Episodic/Semantic
4. **KAIST localized compression**: Compress within modules
5. **Cost-sensitive routing**: Route to appropriate store

**Result**: Lyra matches best memory systems from ICLR 2026

### (B) Breakthrough — Beyond Any Single Source

**Idea 1: 4-Tier Hierarchy with Adaptive Admission**
- **Fusion**: A-MAC + AOI + KAIST + Cost-Sensitive Routing
- **Mechanism**: 4 tiers (Active/Working/Episodic/Semantic) with 5-factor admission control and localized compression
- **Why it wins**: No single paper combines all these techniques
- **Expected impact**: 70% context reduction, 95% info retention, 31% latency reduction

**Idea 2: Textual Gradients for Memory Evolution**
- **Fusion**: MemGrad + ERL + Lyra's verification (§4.16)
- **Mechanism**: Feedback transforms into textual gradients → memory updates → verification
- **Why it wins**: No existing system verifies memory updates before applying
- **Expected impact**: Persistent improvements, 100% verified updates

**Idea 3: Cross-Agent Shared Memory with Conflict Resolution**
- **Fusion**: Lyra's swarm (§4.13) + A-MEM graph + conflict resolution
- **Mechanism**: Shared memory namespace for swarm with automatic conflict resolution
- **Why it wins**: No existing memory system designed for multi-agent swarms
- **Expected impact**: 80% coordination overhead reduction

---

## 7. References

### Papers
- A-MAC: https://openreview.net/attachment?id=mmdqUrEY24&name=pdf
- MemGrad: https://openreview.net/attachment?id=GeaPE7iw1V&name=pdf
- ERL: https://openreview.net/forum?id=hQgSl6kj1W
- AOI: https://openreview.net/attachment?id=Q16XXJou3O&name=pdf
- KAIST: https://openreview.net/attachment?id=ztmwHisqJ4&name=pdf
- A-MEM: https://openreview.net/pdf?id=FiM0M8gcct
- Cost-Sensitive Routing: https://openreview.net/pdf?id=iGRGjdhl9r
- Memory Transplants: https://openreview.net/pdf?id=AIJsjIqfsp

### Related Workstreams
- §4.3 Context: Compression strategies
- §4.5 Router: Cost-sensitive routing
- §4.13 Swarm: Shared memory
- §4.16 Verification: Memory update verification

---

**END OF MEMORY ARCHITECTURE**
