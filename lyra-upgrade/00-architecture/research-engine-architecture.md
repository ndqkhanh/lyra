# Research Engine Architecture

**Version:** 2.0  
**Date:** 2026-05-30  
**Status:** Production

---

## Executive Summary

Lyra's research engine implements multi-hop deep research with iterative query refinement, knowledge graph construction, source credibility scoring, and evidence synthesis. The system enables autonomous research across multiple sources with citation management and cross-session knowledge persistence.

### Key Capabilities

1. **Multi-Hop Reasoning**: Iterative query refinement across multiple research hops
2. **Knowledge Graph Construction**: Entity-relationship graph from research results
3. **Source Credibility Scoring**: Multi-dimensional evaluation of source quality
4. **Evidence Synthesis**: Aggregation and contradiction detection
5. **Citation Management**: Full provenance tracking with citation traversal

---

## Architecture Overview

### Research Engine Components

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
    Storage --> Input
    
    style Input fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Execution fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Knowledge fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Storage fill:#10b98120,stroke:#10b981,stroke-width:2px
```

---

## Multi-Hop Reasoning

### Iterative Query Refinement

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Start[Initial Query] --> Execute1[Execute Hop 1]
    Execute1 --> Analyze1[Analyze Results]
    Analyze1 --> Gaps1{Knowledge<br/>Gaps?}
    
    Gaps1 -->|Yes| Refine1[Refine Query]
    Gaps1 -->|No| Synthesize[Synthesize Findings]
    
    Refine1 --> Execute2[Execute Hop 2]
    Execute2 --> Analyze2[Analyze Results]
    Analyze2 --> Gaps2{Knowledge<br/>Gaps?}
    
    Gaps2 -->|Yes| Refine2[Refine Query]
    Gaps2 -->|No| Synthesize
    
    Refine2 --> Execute3[Execute Hop 3]
    Execute3 --> Analyze3[Analyze Results]
    Analyze3 --> Synthesize
    
    Synthesize --> Report[Generate Report]
    
    style Start fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Execute1 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Execute2 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Execute3 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Report fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### Research Strategies

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    Query[Research Query] --> Classify{Classify<br/>Query Type}
    
    Classify -->|Overview Needed| Breadth[Breadth-First<br/>Explore Many Topics]
    Classify -->|Deep Dive| Depth[Depth-First<br/>Deep on Specific Topics]
    Classify -->|Precision| Iterative[Iterative Refinement<br/>Progressive Narrowing]
    Classify -->|Comparison| Comparative[Comparative<br/>Multiple Sources]
    Classify -->|Discovery| Exploratory[Exploratory<br/>Unconstrained]
    
    Breadth --> Execute[Execute Strategy]
    Depth --> Execute
    Iterative --> Execute
    Comparative --> Execute
    Exploratory --> Execute
    
    Execute --> Results[Research Results]
    
    style Query fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Execute fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Results fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### Query Refinement Process

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant User
    participant Engine as Research Engine
    participant Analyzer as Result Analyzer
    participant Refiner as Query Refiner
    participant Sources
    
    User->>Engine: Submit query
    Engine->>Sources: Execute initial search
    Sources-->>Engine: Initial results
    
    Engine->>Analyzer: Analyze coverage
    Analyzer->>Analyzer: Identify gaps
    Analyzer->>Analyzer: Extract insights
    Analyzer-->>Engine: Gap analysis
    
    alt Gaps found
        Engine->>Refiner: Refine query
        Refiner->>Refiner: Narrow or expand scope
        Refiner-->>Engine: Refined query
        Engine->>Sources: Execute refined search
        Sources-->>Engine: Additional results
    else Sufficient coverage
        Engine->>Engine: Proceed to synthesis
    end
    
    Engine-->>User: Research report
```

---

## Knowledge Graph Construction

### Graph Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Queries["Query Nodes"]
        Q1[Query: LLM Agents]
    end
    
    subgraph Concepts["Concept Nodes"]
        C1[Multi-Agent Systems]
        C2[Tool Use]
        C3[Memory Architecture]
        C4[Reasoning]
    end
    
    subgraph References["Reference Nodes"]
        R1[arXiv:2605.28655<br/>AutoScientists]
        R2[GitHub:AutoGPT]
        R3[ICLR 2026 Workshop]
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
    
    style Q1 fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style C1 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style C2 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style C3 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style C4 fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style R1 fill:#10b98120,stroke:#10b981,stroke-width:2px
    style R2 fill:#10b98120,stroke:#10b981,stroke-width:2px
    style R3 fill:#10b98120,stroke:#10b981,stroke-width:2px
    style R4 fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### Entity Extraction

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Document[Research Document] --> Parse[Parse Content]
    Parse --> Extract[Extract Entities]
    
    Extract --> Entities[Identified Entities]
    Extract --> Relations[Identified Relations]
    
    Entities --> Classify{Entity Type}
    Classify -->|Concept| Concept[Concept Node]
    Classify -->|Person| Person[Person Node]
    Classify -->|Organization| Org[Organization Node]
    Classify -->|Method| Method[Method Node]
    
    Relations --> RelType{Relation Type}
    RelType -->|is-a| IsA[Inheritance Edge]
    RelType -->|part-of| PartOf[Composition Edge]
    RelType -->|uses| Uses[Usage Edge]
    RelType -->|extends| Extends[Extension Edge]
    
    Concept --> Graph[Knowledge Graph]
    Person --> Graph
    Org --> Graph
    Method --> Graph
    IsA --> Graph
    PartOf --> Graph
    Uses --> Graph
    Extends --> Graph
    
    style Document fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Extract fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Graph fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### Graph Operations

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    subgraph Operations["Graph Operations"]
        Add[Add Node/Edge]
        Query[Query Subgraph]
        Traverse[Traverse Paths]
        Merge[Merge Duplicates]
        Prune[Prune Low-Value]
    end
    
    subgraph Algorithms["Graph Algorithms"]
        BFS[Breadth-First Search]
        DFS[Depth-First Search]
        Shortest[Shortest Path]
        Community[Community Detection]
        Centrality[Centrality Analysis]
    end
    
    Operations --> Algorithms
    
    style Operations fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Algorithms fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
```

---

## Source Credibility Scoring

### Credibility Dimensions

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    Source[Research Source] --> Evaluate[Credibility Evaluator]
    
    Evaluate --> Authority[Authority<br/>Weight: 25%]
    Evaluate --> Recency[Recency<br/>Weight: 15%]
    Evaluate --> Citations[Citation Impact<br/>Weight: 20%]
    Evaluate --> Methodology[Methodology<br/>Weight: 25%]
    Evaluate --> Relevance[Relevance<br/>Weight: 15%]
    
    Authority --> Score[Weighted Score]
    Recency --> Score
    Citations --> Score
    Methodology --> Score
    Relevance --> Score
    
    Score --> Rating{Rating}
    Rating -->|0.8-1.0| High[HIGH Credibility]
    Rating -->|0.5-0.8| Medium[MEDIUM Credibility]
    Rating -->|0.0-0.5| Low[LOW Credibility]
    
    style Source fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Evaluate fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style High fill:#10b98120,stroke:#10b981,stroke-width:2px
    style Medium fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Low fill:#ef444420,stroke:#ef4444,stroke-width:2px
```

### Scoring Algorithm

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Source[Source] --> CheckType{Source Type}
    
    CheckType -->|Academic| Academic[Academic Scoring]
    CheckType -->|Industry| Industry[Industry Scoring]
    CheckType -->|Community| Community[Community Scoring]
    CheckType -->|News| News[News Scoring]
    
    Academic --> PeerReview{Peer Reviewed?}
    PeerReview -->|Yes| HighAuth[Authority: 0.9]
    PeerReview -->|No| MedAuth[Authority: 0.6]
    
    Industry --> Company{Reputable<br/>Company?}
    Company -->|Yes| HighAuth
    Company -->|No| MedAuth
    
    Community --> Stars{GitHub Stars<br/>> 1000?}
    Stars -->|Yes| MedAuth
    Stars -->|No| LowAuth[Authority: 0.3]
    
    News --> Outlet{Major Outlet?}
    Outlet -->|Yes| MedAuth
    Outlet -->|No| LowAuth
    
    HighAuth --> Combine[Combine Scores]
    MedAuth --> Combine
    LowAuth --> Combine
    
    Combine --> Final[Final Credibility]
    
    style Source fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Final fill:#10b98120,stroke:#10b981,stroke-width:2px
```

---

## Evidence Synthesis

### Synthesis Process

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Sources[Multiple Sources] --> Extract[Extract Claims]
    Extract --> Group[Group by Topic]
    Group --> Analyze[Analyze Agreement]
    
    Analyze --> Agreement{Agreement<br/>Level}
    
    Agreement -->|High| Consensus[Strong Consensus<br/>High Confidence]
    Agreement -->|Medium| Partial[Partial Agreement<br/>Medium Confidence]
    Agreement -->|Low| Conflict[Conflicting Evidence<br/>Low Confidence]
    
    Consensus --> Synthesize[Synthesize Findings]
    Partial --> Synthesize
    Conflict --> Flag[Flag Contradictions]
    
    Flag --> Synthesize
    Synthesize --> Report[Research Report]
    
    style Sources fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Consensus fill:#10b98120,stroke:#10b981,stroke-width:2px
    style Partial fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Conflict fill:#ef444420,stroke:#ef4444,stroke-width:2px
    style Report fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### Contradiction Detection

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant Synthesizer
    participant Claim1 as Claim 1
    participant Claim2 as Claim 2
    participant Resolver
    
    Synthesizer->>Claim1: Extract claim
    Synthesizer->>Claim2: Extract claim
    
    Synthesizer->>Synthesizer: Compare claims
    
    alt Claims contradict
        Synthesizer->>Resolver: Resolve contradiction
        Resolver->>Resolver: Check source credibility
        Resolver->>Resolver: Check evidence strength
        Resolver->>Resolver: Check recency
        Resolver-->>Synthesizer: Resolution
    else Claims agree
        Synthesizer->>Synthesizer: Strengthen confidence
    end
    
    Synthesizer->>Synthesizer: Update synthesis
```

### Evidence Aggregation

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Evidence["Evidence Collection"]
        E1[Evidence 1<br/>Credibility: 0.9]
        E2[Evidence 2<br/>Credibility: 0.8]
        E3[Evidence 3<br/>Credibility: 0.7]
        E4[Evidence 4<br/>Credibility: 0.6]
    end
    
    subgraph Aggregation["Aggregation Methods"]
        Weighted[Weighted Average<br/>By Credibility]
        Majority[Majority Vote<br/>Most Common]
        Bayesian[Bayesian Update<br/>Prior + Evidence]
    end
    
    Evidence --> Aggregation
    
    Aggregation --> Result[Aggregated Finding<br/>Confidence: 0.85]
    
    style Evidence fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Aggregation fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Result fill:#10b98120,stroke:#10b981,stroke-width:2px
```

---

## Citation Management

### Citation Structure

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    class Citation {
        +string id
        +string title
        +list~string~ authors
        +string source
        +date publication_date
        +float credibility
        +list~Claim~ claims
        +get_formatted() string
    }
    
    class Claim {
        +string text
        +float confidence
        +list~Evidence~ evidence
        +Citation source
        +verify() bool
    }
    
    class Evidence {
        +string type
        +string content
        +float strength
        +Citation source
    }
    
    class CitationGraph {
        +list~Citation~ citations
        +list~Edge~ references
        +traverse() list
        +find_path() list
    }
    
    Citation --> Claim
    Claim --> Evidence
    Evidence --> Citation
    CitationGraph --> Citation
    
    style Citation fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Claim fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Evidence fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style CitationGraph fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### Citation Traversal

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    Start[Start Citation] --> Follow[Follow References]
    Follow --> C1[Citation 1]
    Follow --> C2[Citation 2]
    
    C1 --> C1R1[Citation 1.1]
    C1 --> C1R2[Citation 1.2]
    
    C2 --> C2R1[Citation 2.1]
    C2 --> C2R2[Citation 2.2]
    
    C1R1 --> Collect[Collect All Citations]
    C1R2 --> Collect
    C2R1 --> Collect
    C2R2 --> Collect
    
    Collect --> Dedupe[Deduplicate]
    Dedupe --> Rank[Rank by Relevance]
    Rank --> Results[Citation Network]
    
    style Start fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Collect fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Results fill:#10b98120,stroke:#10b981,stroke-width:2px
```

---

## Research Pipeline

### Complete Research Flow

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant User
    participant Engine as Research Engine
    participant Strategy as Strategy Selector
    participant MultiHop as Multi-Hop Engine
    participant KG as Knowledge Graph
    participant Evaluator as Source Evaluator
    participant Synthesizer
    participant Cache
    
    User->>Engine: Submit research query
    Engine->>Strategy: Select strategy
    Strategy-->>Engine: Strategy selected
    
    Engine->>MultiHop: Execute research
    
    loop Multi-hop refinement
        MultiHop->>MultiHop: Execute hop
        MultiHop->>KG: Add entities & relations
        MultiHop->>Evaluator: Score sources
        Evaluator-->>MultiHop: Credibility scores
        MultiHop->>MultiHop: Evaluate coverage
        
        alt Gaps remain
            MultiHop->>MultiHop: Refine query
        else Sufficient
            break
        end
    end
    
    MultiHop->>Synthesizer: Synthesize findings
    Synthesizer->>Synthesizer: Aggregate evidence
    Synthesizer->>Synthesizer: Detect contradictions
    Synthesizer-->>Engine: Research report
    
    Engine->>Cache: Store results
    Engine->>KG: Persist graph
    Engine-->>User: Return report
```

---

## Performance Characteristics

### Research Metrics

| Metric | Target | Current |
|--------|--------|---------|
| **Query Refinement Hops** | 3-5 | 3-4 |
| **Source Coverage** | 20-50 sources | 15-30 |
| **Credibility Threshold** | >0.7 | >0.7 |
| **Synthesis Time** | <30s | <25s |
| **Cache Hit Rate** | >60% | 55% |
| **Knowledge Graph Size** | 1000+ nodes | 500+ |

### Research Quality

```mermaid
%%{init: {'theme': 'dark'}}%%
xychart-beta
    title "Research Quality by Strategy"
    x-axis [Breadth-First, Depth-First, Iterative, Comparative, Exploratory]
    y-axis "Quality Score" 0 --> 100
    bar [75, 85, 90, 88, 70]
```

---

## Integration Points

### With Memory System

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    Research[Research Engine] --> Findings[Research Findings]
    Findings --> Memory[Memory System]
    
    Memory --> Episodic[Episodic Memory<br/>Recent Research]
    Memory --> Semantic[Semantic Memory<br/>Knowledge Graph]
    
    Semantic --> Reuse[Reuse in Future<br/>Research]
    Reuse --> Research
    
    style Research fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Memory fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Reuse fill:#10b98120,stroke:#10b981,stroke-width:2px
```

### With Agent Swarm

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant Swarm as Agent Swarm
    participant Research as Research Engine
    participant KG as Knowledge Graph
    
    Swarm->>Research: Request research
    Research->>Research: Execute multi-hop
    Research->>KG: Build knowledge graph
    Research-->>Swarm: Research report
    
    Swarm->>Swarm: Use findings
    Swarm->>KG: Query related knowledge
    KG-->>Swarm: Related concepts
```

---

## Future Enhancements

### Phase 2: Advanced Features
- 📋 Real-time research monitoring
- 📋 Collaborative research sessions
- 📋 Automated literature reviews
- 📋 Research trend analysis

### Phase 3: Intelligence
- 🔬 Predictive research suggestions
- 🔬 Automated hypothesis generation
- 🔬 Cross-domain knowledge transfer
- 🔬 Research quality prediction

---

## Related Documentation

- [Research Engine Details](./research-engine.md) - Implementation details
- [Knowledge Graph](./MEMORY-ARCHITECTURE-V2.md) - Memory integration
- [Agent Swarm](./agent-swarm.md) - Multi-agent research
- [System Overview](./system-overview.md) - Overall architecture

---

<div align="center">

**Lyra Research Engine Architecture**

Version 2.0 | 2026-05-30 | Production

[System Overview](./system-overview.md) · [Research Engine](./research-engine.md)

</div>
