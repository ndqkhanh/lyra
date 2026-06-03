> ⚠️ **Redirect:** The canonical research-engine documentation is at [systems/research-engine/](../systems/research-engine/). This file is kept for reference.

# Multi-Hop Deep Research System

> **Iterative query refinement, knowledge graph construction, and source credibility scoring**

## Table of Contents

- [Overview](#overview)
- [Multi-Hop Reasoning](#multi-hop-reasoning)
- [Knowledge Graph](#knowledge-graph)
- [Source Evaluation](#source-evaluation)
- [Research Pipeline](#research-pipeline)
- [Research Inspirations](#research-inspirations)

---

## Overview

The Lyra research engine enables deep, multi-hop research across multiple sources with iterative query refinement, knowledge graph construction, source credibility scoring, and research strategy evolution.

**Key capabilities:**
- Multi-hop iterative query refinement
- Knowledge graph construction from research results
- Source credibility scoring and citation management
- Research history caching
- Strategy selection based on research patterns

---

## Multi-Hop Reasoning

The research engine uses iterative query refinement to progressively narrow or expand research scope based on intermediate findings.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Q1[Initial Query] -->|Execute| R1[Results Round 1]
    R1 -->|Analyze| Insights[Extract Insights]
    Insights -->|Refine| Q2[Refined Query]
    Q2 -->|Execute| R2[Results Round 2]
    R2 -->|Analyze| Gaps[Identify Knowledge Gaps]
    Gaps -->|Expand| Q3[Expanded Query]
    Q3 -->|Execute| R3[Results Round 3]
    R3 -->|Synthesize| Report[Final Synthesis]
    
    subgraph Decision Points
        Gaps -->|Sufficient| Report
    end
```

### Research Strategy Selection

The engine selects from multiple research strategies based on the nature of the query and intermediate results:

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Breadth-First** | Explore many topics shallowly | Overview research |
| **Depth-First** | Deep dive on specific topics | Technical deep dives |
| **Iterative Refinement** | Progressive narrowing | Precision research |
| **Comparative** | Compare multiple sources | Competitive analysis |
| **Exploratory** | Unconstrained discovery | Novel topics |

---

## Knowledge Graph

Research results are organized into a knowledge graph that captures entities, relationships, and provenance.

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    Q[Query: LLM Agents] --> C1[Concept: Multi-Agent Systems]
    Q --> C2[Concept: Tool Use]
    Q --> C3[Concept: Memory]
    
    C1 --> R1[Reference: MetaGPT paper]
    C1 --> R2[Reference: AutoGPT repo]
    
    C2 --> R3[Reference: Toolformer]
    C2 --> R4[Reference: Gorilla API]
    
    C3 --> R5[Reference: MemAgent workshop]
    C3 --> R6[Reference: MemoryBank]
    
    R1 -.->|extends| R5
    R2 -.->|implements| R1
    
    style Q fill:#7c3aed20
    style C1 fill:#3b82f620
    style C2 fill:#3b82f620
    style C3 fill:#3b82f620
    style R1 fill:#10b98120
    style R2 fill:#10b98120
    style R3 fill:#10b98120
    style R4 fill:#10b98120
    style R5 fill:#10b98120
    style R6 fill:#10b98120
```

### Graph Components

| Component | Description |
|-----------|-------------|
| **Query Nodes** | Root research questions |
| **Concept Nodes** | Extracted topics and subtopics |
| **Reference Nodes** | Source papers, repos, documents |
| **Relationships** | Supports, extends, contradicts, implements |

---

## Source Evaluation

Each source is scored on multiple credibility dimensions.

### Credibility Dimensions

```mermaid
%%{init: {'theme': 'dark'}}%%
radarChart
    title Source Credibility Profile
    axis ["Authority", "Recency", "Citation Count", "Methodology", "Relevance"]
    series [
      {name: "High-Quality Source", data: [90, 85, 80, 95, 88]},
      {name: "Medium-Quality Source", data: [60, 50, 40, 55, 70]},
      {name: "Low-Quality Source", data: [20, 30, 10, 15, 50]}
    ]
```

### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| **Authority** | 25% | Author/institution reputation, peer review status |
| **Recency** | 15% | Publication date proximity to current |
| **Citation Impact** | 20% | Number and quality of citations received |
| **Methodology** | 25% | Rigor of research methodology |
| **Relevance** | 15% | Direct relevance to the research query |

### Citation Management

Each research result maintains full citation provenance:

```
[Source: arXiv:2605.22138]
  Title: SR2AM: Self-Regulated Agent Memory
  Author: Zhang et al.
  Date: 2026-05
  Credibility: 0.85 (HIGH)
  Extracted Claims:
    - Multi-agent memory improves recall by 34%
    - Self-regulation reduces hallucination by 28%
```

---

## Research Pipeline

### Complete Flow

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    Start[Research Request] --> Classify[Classify Query Type]
    Classify --> Strategy[Select Research Strategy]
    Strategy --> Execute[Execute First Hop]
    
    Execute --> Evaluate[Evaluate Results]
    Evaluate -->|Sufficient| Synthesize[Synthesize Findings]
    Evaluate -->|Gaps Found| Refine[Refine Query]
    Refine --> Execute
    
    Synthesize --> BuildGraph[Build Knowledge Graph]
    BuildGraph --> Score[Score Source Credibility]
    Score --> Generate[Generate Research Report]
    Generate --> Cache[Cache Results]
    Cache --> Return[Return Report]
    
    style Start fill:#7c3aed20
    style Synthesize fill:#f59e0b20
    style BuildGraph fill:#3b82f620
    style Generate fill:#10b98120
    style Cache fill:#ef444420
```

### Research Session Lifecycle

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant User
    participant Engine as ResearchEngine
    participant KG as KnowledgeGraph
    participant SE as SourceEvaluator
    participant Cache as ResearchCache
    participant Memory as MemorySystem
    
    User->>Engine: Research topic X
    Engine->>Engine: Select strategy (iterative)
    
    loop Multi-hop refinement
        Engine->>Engine: Execute research hop
        Engine->>KG: Add entities & relationships
        Engine->>SE: Score source credibility
        SE-->>Engine: Credibility scores
        Engine->>Engine: Evaluate coverage
        
        alt Gaps remain
            Engine->>Engine: Refine query
        else Sufficient
            break
        end
    end
    
    Engine->>Synthesize: Produce final report
    Engine->>Cache: Store results
    Engine->>Memory: Persist research history
    Engine-->>User: Report with citations
```

---

## Research Inspirations

| Innovation | Source | Application |
|-----------|--------|-------------|
| **Multi-Hop Reasoning** | Code_Researcher, Plan 12 | Iterative query refinement |
| **Knowledge Graph** | Neo4j, RDF patterns | Entity-relationship graph construction |
| **Source Credibility** | Academic citation analysis | Multi-dimensional scoring |
| **Strategy Selection** | Meta-learning | Adaptive research strategy based on query type |
| **Research Caching** | Cache-aside pattern | Full result caching with TTL |
| **Cross-Session History** | Memory consolidation | Persisting research results for reuse |
