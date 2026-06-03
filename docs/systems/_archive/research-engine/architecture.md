# Research Engine Architecture

**System:** Multi-Hop Deep Research Engine  
**Version:** 2.0  
**Status:** Active Development  
**Last Updated:** 2026-06-02

---

## Executive Summary

The Lyra Research Engine is a sophisticated multi-hop research system that combines iterative query refinement, knowledge graph construction, source credibility scoring, and evidence synthesis. It enables autonomous deep research across diverse sources with full citation provenance and cross-session knowledge persistence.

### Core Capabilities

1. **Multi-Hop Reasoning**: Iterative query refinement across 3-5 research hops
2. **Knowledge Graph**: Entity-relationship graph with 500+ nodes
3. **Source Credibility**: Multi-dimensional evaluation (authority, recency, citations, methodology, relevance)
4. **Evidence Synthesis**: Aggregation with contradiction detection
5. **Citation Management**: Full provenance tracking with citation traversal

---

## System Overview

### High-Level Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Input["🎯 Input Layer"]
        Query[Research Query]
        Context[Research Context]
        Strategy[Strategy Selection]
    end
    
    subgraph Execution["⚡ Execution Layer"]
        MultiHop[Multi-Hop Engine<br/>Iterative Refinement]
        Sources[Source Retrieval<br/>Multiple Providers]
        Evaluator[Source Evaluator<br/>Credibility Scoring]
    end
    
    subgraph Knowledge["🧠 Knowledge Layer"]
        KG[Knowledge Graph<br/>Entity-Relationship]
        Synthesis[Evidence Synthesis<br/>Aggregation]
        Citations[Citation Manager<br/>Provenance Tracking]
    end
    
    subgraph Storage["💾 Storage Layer"]
        Cache[Research Cache<br/>Result Caching]
        History[Research History<br/>Cross-Session]
        Memory[Memory Integration<br/>Semantic Storage]
    end
    
    Input --> Execution
    Execution --> Knowledge
    Knowledge --> Storage
    Storage -.->|Feedback| Input
    
    style Input fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Execution fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Knowledge fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Storage fill:#10b98120,stroke:#10b981,stroke-width:2px
```

---

## Component Architecture

### 1. Input Layer

The Input Layer handles query ingestion, context preparation, and strategy selection.

#### Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Query Parser** | Parse and normalize research queries | Python NLP, regex |
| **Context Builder** | Assemble research context from prior sessions | SQLite, JSON |
| **Strategy Selector** | Choose optimal research strategy based on query type | ML classifier, rule-based |

#### Query Classification

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Query[Research Query] --> Analyze[Analyze Query]
    Analyze --> Type{Query Type}
    
    Type -->|Overview| Breadth[Breadth-First<br/>Strategy]
    Type -->|Deep Dive| Depth[Depth-First<br/>Strategy]
    Type -->|Precision| Iterative[Iterative Refinement<br/>Strategy]
    Type -->|Comparison| Comparative[Comparative<br/>Strategy]
    Type -->|Discovery| Exploratory[Exploratory<br/>Strategy]
    
    Breadth --> Execute[Execute Research]
    Depth --> Execute
    Iterative --> Execute
    Comparative --> Execute
    Exploratory --> Execute
    
    style Query fill:#7c3aed20
    style Execute fill:#10b98120
```

---

### 2. Execution Layer

The Execution Layer orchestrates multi-hop research, retrieves sources, and evaluates credibility.

#### Multi-Hop Engine

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant User
    participant Engine as Multi-Hop Engine
    participant Sources as Source Retrieval
    participant Analyzer as Result Analyzer
    participant Refiner as Query Refiner
    
    User->>Engine: Submit query
    Engine->>Sources: Execute hop 1
    Sources-->>Engine: Results
    Engine->>Analyzer: Analyze coverage
    Analyzer-->>Engine: Gap analysis
    
    alt Gaps found
        Engine->>Refiner: Refine query
        Refiner-->>Engine: Refined query
        Engine->>Sources: Execute hop 2
        Sources-->>Engine: Additional results
    else Sufficient
        Engine->>Engine: Proceed to synthesis
    end
    
    Engine-->>User: Research complete
```

#### Source Retrieval Providers

| Provider | Type | Use Case |
|----------|------|----------|
| **arXiv** | Academic papers | Scientific research |
| **GitHub** | Code repositories | Implementation examples |
| **Web Search** | General web | Broad coverage |
| **Academic DBs** | Papers, journals | Peer-reviewed research |
| **Documentation** | API docs, guides | Technical references |

---

### 3. Knowledge Layer

The Knowledge Layer constructs the knowledge graph, synthesizes evidence, and manages citations.

#### Knowledge Graph Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Queries["Query Nodes"]
        Q1[Query: LLM Agents]
    end
    
    subgraph Concepts["Concept Nodes"]
        C1[Multi-Agent<br/>Systems]
        C2[Tool Use]
        C3[Memory<br/>Architecture]
        C4[Reasoning]
    end
    
    subgraph References["Reference Nodes"]
        R1[arXiv:2605.28655<br/>AutoScientists]
        R2[GitHub:AutoGPT<br/>12.3k stars]
        R3[ICLR 2026<br/>Workshop]
        R4[arXiv:2605.24220<br/>Polar]
    end
    
    Q1 --> C1
    Q1 --> C2
    Q1 --> C3
    Q1 --> C4
    
    C1 --> R1
    C1 --> R2
    C2 --> R2
    C3 --> R3
    C4 --> R1
    C4 --> R4
    
    R1 -.->|extends| R3
    R2 -.->|implements| R1
    R4 -.->|supports| R1
    
    style Q1 fill:#7c3aed20
    style C1 fill:#3b82f620
    style C2 fill:#3b82f620
    style C3 fill:#3b82f620
    style C4 fill:#3b82f620
    style R1 fill:#10b98120
    style R2 fill:#10b98120
    style R3 fill:#10b98120
    style R4 fill:#10b98120
```

#### Graph Operations

| Operation | Description | Complexity |
|-----------|-------------|------------|
| **Add Node** | Insert entity or reference | O(1) |
| **Add Edge** | Create relationship | O(1) |
| **Query Subgraph** | Find related nodes | O(n + m) |
| **Traverse Paths** | Find paths between nodes | O(n²) |
| **Merge Duplicates** | Deduplicate entities | O(n log n) |
| **Community Detection** | Identify clusters | O(n²) |

---

### 4. Storage Layer

The Storage Layer persists research results, manages cache, and integrates with memory systems.

#### Storage Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    subgraph Cache["Research Cache"]
        QueryCache[Query Cache<br/>TTL: 24h]
        ResultCache[Result Cache<br/>TTL: 7d]
    end
    
    subgraph History["Research History"]
        SessionDB[(SQLite<br/>Sessions)]
        GraphDB[(NetworkX<br/>Knowledge Graph)]
    end
    
    subgraph Memory["Memory Integration"]
        Episodic[Episodic Memory<br/>Recent Research]
        Semantic[Semantic Memory<br/>Knowledge Graph]
    end
    
    Cache --> History
    History --> Memory
    Memory -.->|Reuse| Cache
    
    style Cache fill:#7c3aed20
    style History fill:#3b82f620
    style Memory fill:#10b98120
```

#### Data Persistence

| Store | Technology | Purpose | Retention |
|-------|------------|---------|-----------|
| **Query Cache** | In-memory | Fast repeated queries | 24 hours |
| **Result Cache** | SQLite + JSON | Cached research results | 7 days |
| **Session History** | SQLite | Research sessions | 30 days |
| **Knowledge Graph** | NetworkX + pickle | Entity-relationship graph | Persistent |
| **Memory Store** | SQLite FTS5 + sentence-transformers | Semantic search | Persistent |

---

## Integration Points

### Integration with Core Systems

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    Research[Research Engine] --> Gateway[Lyra Gateway]
    Research --> Memory[Memory System]
    Research --> Swarm[Agent Swarm]
    
    Gateway --> Tools[Tool Layer]
    Memory --> Episodic[Episodic Memory]
    Memory --> Semantic[Semantic Memory]
    Swarm --> MultiAgent[Multi-Agent<br/>Coordination]
    
    Tools --> WebFetch[WebFetch]
    Tools --> MCP[MCP Servers]
    
    style Research fill:#7c3aed20
    style Gateway fill:#3b82f620
    style Memory fill:#f59e0b20
    style Swarm fill:#10b98120
```

### External Integrations

| System | Interface | Purpose |
|--------|-----------|---------|
| **Lyra Gateway** | Python API | Task routing, session management |
| **Memory System** | SQLite + NetworkX | Knowledge persistence |
| **Agent Swarm** | Python objects + EventBus | Multi-agent research coordination |
| **Tool Layer** | Python functions | Web fetch, MCP servers |
| **Context Engine** | Shared memory | Context assembly |

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Language** | Python | 3.11+ | Core implementation |
| **Graph** | NetworkX | 3.2+ | Knowledge graph |
| **NLP** | spaCy | 3.7+ | Entity extraction |
| **Embeddings** | sentence-transformers | 2.3+ | Semantic search |
| **Database** | SQLite | 3.40+ | Structured storage |
| **Cache** | In-memory | - | Result caching |
| **HTTP** | requests | 2.31+ | Web requests |
| **PDF** | PyMuPDF, pdfplumber | - | Document parsing |

### Supporting Libraries

```python
# Core dependencies (from lyra-research pyproject.toml)
requests>=2.31.0             # HTTP requests
beautifulsoup4>=4.12.0       # HTML parsing
PyMuPDF>=1.23.0              # PDF parsing
pdfplumber>=0.10.0           # PDF table extraction
arxiv>=2.1.0                 # arXiv API
semanticscholar>=0.8.0       # Semantic Scholar API
networkx>=3.2                # Knowledge graph
spacy>=3.7.0                 # Entity extraction
sentence-transformers>=2.3.0 # Semantic embeddings
```

---

## Data Flow

### Complete Research Flow

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    Start[Research Request] --> Parse[Parse Query]
    Parse --> Strategy[Select Strategy]
    Strategy --> Hop1[Execute Hop 1]
    
    Hop1 --> Retrieve1[Retrieve Sources]
    Retrieve1 --> Score1[Score Credibility]
    Score1 --> Extract1[Extract Entities]
    Extract1 --> Build1[Update Knowledge Graph]
    
    Build1 --> Evaluate{Coverage<br/>Sufficient?}
    
    Evaluate -->|No| Refine[Refine Query]
    Refine --> Hop2[Execute Hop 2]
    Hop2 --> Retrieve2[Retrieve Sources]
    Retrieve2 --> Score2[Score Credibility]
    Score2 --> Extract2[Extract Entities]
    Extract2 --> Build2[Update Knowledge Graph]
    Build2 --> Evaluate
    
    Evaluate -->|Yes| Synthesize[Synthesize Evidence]
    Synthesize --> Detect[Detect Contradictions]
    Detect --> Generate[Generate Report]
    Generate --> Cache[Cache Results]
    Cache --> Persist[Persist to Memory]
    Persist --> Return[Return Report]
    
    style Start fill:#7c3aed20
    style Synthesize fill:#f59e0b20
    style Generate fill:#10b98120
```

---

## Performance Characteristics

### Throughput Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| **Query Processing** | <5s | 3-4s | Single hop |
| **Multi-Hop Research** | <30s | 20-25s | 3-4 hops |
| **Graph Construction** | <10s | 8s | 50 entities |
| **Evidence Synthesis** | <15s | 12s | 20 sources |
| **Cache Hit Rate** | >60% | 55% | Improving |

### Scalability

```mermaid
%%{init: {'theme': 'dark'}}%%
xychart-beta
    title "Research Time by Source Count"
    x-axis [10, 20, 30, 40, 50]
    y-axis "Time (seconds)" 0 --> 60
    line [5, 12, 20, 32, 45]
```

---

## Security & Reliability

### Security Measures

1. **Input Validation**: Sanitize all research queries
2. **Source Verification**: Validate URLs and domains
3. **Rate Limiting**: Prevent abuse of external APIs
4. **Content Filtering**: Block malicious content
5. **Credential Management**: Secure API key storage

### Error Handling

| Error Type | Strategy | Recovery |
|------------|----------|----------|
| **Source Unavailable** | Fallback to alternate sources | Automatic |
| **API Rate Limit** | Exponential backoff | Automatic |
| **Parse Error** | Skip source, log error | Automatic |
| **Graph Corruption** | Rebuild from cache | Manual |
| **Memory Overflow** | Prune old entries | Automatic |

---

## Future Enhancements

### Phase 2 (Q3 2026)
- Real-time research monitoring
- Collaborative research sessions
- Automated literature reviews
- Research trend analysis

### Phase 3 (Q4 2026)
- Predictive research suggestions
- Automated hypothesis generation
- Cross-domain knowledge transfer
- Research quality prediction

---

## Related Documentation

- [System Design](./system-design.md) - Detailed design and algorithms
- [Tradeoffs](./tradeoffs.md) - Design decisions and alternatives
- [Implementation](./implementation.md) - Implementation guide
- [Evaluation](./evaluation.md) - Performance metrics and benchmarks

---

**Research Engine Architecture v2.0** | Last Updated: 2026-06-02
