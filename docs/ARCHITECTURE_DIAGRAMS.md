# Lyra Architecture Diagrams

Comprehensive visual documentation of Lyra's innovative architecture.

---

## 1. Self-Evolution System (12 Phases)

```mermaid
graph TB
    subgraph "Phase A-E: Observability & Control"
        A[A: AER + SLO<br/>SQLite Execution Traces<br/>7 Service-Level Objectives]
        B[B: BAAR Routing<br/>3-Tier Selection<br/>Fast • Reasoning • Advisor]
        C[C: IRCoT + Graph<br/>Multi-hop Retrieval<br/>Codebase Impact Analysis]
        D[D: Fleet View<br/>P0-P4 Priorities<br/>Background Supervisor]
        E[E: Closed-Loop Control<br/>Voyager + Reflexion<br/>8-Timescale Learning]
    end
    
    subgraph "Phase F-J: Skill Management"
        F[F: SLIM Lifecycle<br/>RETAIN • RETIRE • EXPAND<br/>+12.5pp Accuracy]
        G[G: SSL Representation<br/>Scheduling • Structural • Logical<br/>+12.3% MRR@50]
        H[H: Ctx2Skill Extraction<br/>5-Agent Loop<br/>Cross-Time Replay]
        I[I: SkillOS Curator<br/>INSERT • UPDATE • DELETE<br/>+9.8% Improvement]
        J[J: DCI Retrieval<br/>BM25 + Grep + Semantic<br/>Hybrid Search]
    end
    
    subgraph "Phase K-L: Verification & Compression"
        K[K: EvoVerify<br/>Co-evolutionary Gate<br/>+17.6pp Accuracy]
        L[L: Adaptive Compression<br/>Trace → Episodic → Skill → Rule<br/>Memory Efficiency]
    end
    
    A --> B --> C --> D --> E
    E --> F & G & H
    H --> I --> J
    F & G & J --> K --> L
    L -.Improved Skills.-> B
    
    style A fill:#14532d,stroke:#4ade80,color:#fff
    style B fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style C fill:#3b0764,stroke:#c084fc,color:#fff
    style D fill:#164e63,stroke:#22d3ee,color:#fff
    style E fill:#422006,stroke:#f97316,color:#fff
    style F fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style G fill:#1c1917,stroke:#a8a29e,color:#fff
    style H fill:#064e3b,stroke:#34d399,color:#fff
    style I fill:#7c2d12,stroke:#fb923c,color:#fff
    style J fill:#1e293b,stroke:#94a3b8,color:#fff
    style K fill:#581c87,stroke:#a78bfa,color:#fff
    style L fill:#831843,stroke:#f472b6,color:#fff
```

**Key Innovation:** Lyra learns from every session, automatically extracting and curating reusable skills with co-evolutionary verification.

---

## 2. Skill Intelligence System

```mermaid
graph LR
    subgraph "Skill Representation (SSL)"
        S1[Scheduling Layer<br/>When to use skill]
        S2[Structural Layer<br/>How skill is organized]
        S3[Logical Layer<br/>What skill does]
    end
    
    subgraph "Skill Lifecycle (SLIM)"
        L1[RETAIN<br/>Keep valuable skills]
        L2[RETIRE<br/>Remove obsolete skills]
        L3[EXPAND<br/>Generalize successful skills]
    end
    
    subgraph "Skill Retrieval"
        R1[BM25<br/>Keyword Search<br/>α=0.40]
        R2[DCI Grep<br/>Code Pattern<br/>β=0.40]
        R3[Semantic<br/>Embedding Search<br/>γ=0.20]
    end
    
    TRACE[Session Trace] --> EXTRACT[Ctx2Skill<br/>Extraction]
    EXTRACT --> S1 & S2 & S3
    S1 & S2 & S3 --> CURATOR[SkillOS Curator]
    CURATOR --> INSERT{INSERT?}
    CURATOR --> UPDATE{UPDATE?}
    CURATOR --> DELETE{DELETE?}
    
    INSERT --> VERIFY[EvoVerify Gate]
    UPDATE --> VERIFY
    VERIFY --> LIBRARY[(Skill Library)]
    
    QUERY[User Query] --> R1 & R2 & R3
    R1 & R2 & R3 --> FUSION[Hybrid Fusion]
    FUSION --> LIBRARY
    LIBRARY --> MATCHED[Matched Skills]
    
    MATCHED --> L1 & L2 & L3
    L1 --> ACTIVE[Active Skills]
    L2 --> ARCHIVE[Archived]
    L3 --> GENERALIZED[Generalized Skills]
    
    style TRACE fill:#14532d,stroke:#4ade80,color:#fff
    style EXTRACT fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style CURATOR fill:#422006,stroke:#f97316,color:#fff
    style VERIFY fill:#581c87,stroke:#a78bfa,color:#fff
    style LIBRARY fill:#064e3b,stroke:#34d399,color:#fff
    style FUSION fill:#3b0764,stroke:#c084fc,color:#fff
```

**Key Innovation:** Three-layer skill representation with hybrid retrieval and lifecycle management ensures skills stay relevant and valuable.

---

## 3. Tool System Architecture

```mermaid
graph TB
    subgraph "Built-in Tools"
        T1[Read<br/>File reading with<br/>line ranges]
        T2[Write<br/>File creation<br/>with chunking]
        T3[Edit<br/>Precise string<br/>replacement]
        T4[Bash<br/>Shell command<br/>execution]
        T5[WebSearch<br/>Internet search<br/>with citations]
        T6[WebFetch<br/>URL content<br/>extraction]
    end
    
    subgraph "MCP Tools"
        M1[Filesystem MCP<br/>Advanced file ops]
        M2[GitHub MCP<br/>Repository access]
        M3[PostgreSQL MCP<br/>Database queries]
        M4[Custom MCP<br/>User-defined tools]
    end
    
    subgraph "Tool Execution"
        E1[Permission System<br/>Allow/Deny lists]
        E2[Hooks<br/>Pre/Post execution]
        E3[Error Handling<br/>Retry + Circuit Breaker]
        E4[Usage Tracking<br/>Cost + Performance]
    end
    
    USER[User Query] --> ROUTER[Tool Router]
    ROUTER --> SELECTOR{Tool Selection}
    
    SELECTOR --> T1 & T2 & T3 & T4 & T5 & T6
    SELECTOR --> M1 & M2 & M3 & M4
    
    T1 & T2 & T3 & T4 & T5 & T6 --> E1
    M1 & M2 & M3 & M4 --> E1
    
    E1 --> E2 --> E3 --> E4
    E4 --> RESULT[Tool Result]
    RESULT --> AER[AER Trace<br/>Logged for learning]
    
    style USER fill:#14532d,stroke:#4ade80,color:#fff
    style ROUTER fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style SELECTOR fill:#422006,stroke:#f97316,color:#fff
    style E1 fill:#581c87,stroke:#a78bfa,color:#fff
    style E2 fill:#3b0764,stroke:#c084fc,color:#fff
    style E3 fill:#164e63,stroke:#22d3ee,color:#fff
    style E4 fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style AER fill:#064e3b,stroke:#34d399,color:#fff
```

**Key Innovation:** Extensible tool system with MCP protocol support, permission management, and automatic usage tracking for learning.

---

## 4. Memory System

```mermaid
graph TB
    subgraph "Short-term Memory"
        ST1[Conversation Context<br/>Current session messages]
        ST2[Working Memory<br/>Active variables & state]
        ST3[Tool Results<br/>Recent execution outputs]
    end
    
    subgraph "Long-term Memory"
        LT1[Codebase Graph<br/>Files • Functions • Dependencies]
        LT2[Memory Records<br/>FTS5 full-text search]
        LT3[Skill Library<br/>Learned strategies]
        LT4[Execution Traces<br/>AER SQLite database]
    end
    
    subgraph "Memory Operations"
        OP1[Store<br/>Save to memory]
        OP2[Retrieve<br/>Search & recall]
        OP3[Update<br/>Modify existing]
        OP4[Compress<br/>Summarize old data]
    end
    
    QUERY[User Query] --> ST1
    ST1 --> CONTEXT[Context Builder]
    
    CONTEXT --> OP2
    OP2 --> LT1 & LT2 & LT3 & LT4
    
    LT1 --> IMPACT[Impact Analysis<br/>BFS traversal]
    LT2 --> SEARCH[Semantic Search]
    LT3 --> SKILLS[Skill Matching]
    LT4 --> PATTERNS[Pattern Recognition]
    
    IMPACT & SEARCH & SKILLS & PATTERNS --> RELEVANT[Relevant Context]
    RELEVANT --> ST1
    
    RESULT[Execution Result] --> OP1
    OP1 --> LT1 & LT2 & LT3 & LT4
    
    TIME[Time-based Trigger] --> OP4
    OP4 --> LT2 & LT4
    
    style QUERY fill:#14532d,stroke:#4ade80,color:#fff
    style CONTEXT fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style OP2 fill:#422006,stroke:#f97316,color:#fff
    style IMPACT fill:#581c87,stroke:#a78bfa,color:#fff
    style SEARCH fill:#3b0764,stroke:#c084fc,color:#fff
    style SKILLS fill:#164e63,stroke:#22d3ee,color:#fff
    style PATTERNS fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style OP4 fill:#831843,stroke:#f472b6,color:#fff
```

**Key Innovation:** Hybrid memory system combining short-term context with long-term codebase knowledge and adaptive compression.

---

## 5. Deep Research Pipeline

```mermaid
graph TB
    START([Research Query]) --> CLARIFY[1. Clarify<br/>Parse intent<br/>Extract keywords]
    
    CLARIFY --> PLAN[2. Plan<br/>Search strategy<br/>Source selection]
    
    PLAN --> DISCOVER[3. Discover]
    
    subgraph "Discovery Sources"
        D1[ArXiv<br/>Academic papers]
        D2[OpenReview<br/>Peer reviews]
        D3[HuggingFace<br/>Models & datasets]
        D4[GitHub<br/>Code repositories]
        D5[Semantic Scholar<br/>Citations]
        D6[Papers with Code<br/>Benchmarks]
    end
    
    DISCOVER --> D1 & D2 & D3 & D4 & D5 & D6
    D1 & D2 & D3 & D4 & D5 & D6 --> ANALYZE[4. Analyze]
    
    subgraph "Intelligence Layer"
        I1[Evidence Audit<br/>Verify claims]
        I2[Gap Analyzer<br/>Find missing info]
        I3[Falsification Check<br/>Test hypotheses]
    end
    
    ANALYZE --> I1 & I2 & I3
    I1 & I2 & I3 --> SYNTHESIZE[5. Synthesize<br/>Combine findings]
    
    SYNTHESIZE --> VERIFY[6. Verify<br/>Cross-reference sources]
    VERIFY --> REPORT[7. Report<br/>Generate markdown]
    
    REPORT --> LEARN[8. Learn<br/>Extract strategies]
    LEARN --> EVALUATE[9. Evaluate<br/>Quality assessment]
    EVALUATE --> IMPROVE[10. Improve<br/>Self-improvement gate]
    
    IMPROVE --> OUTPUT([Research Report<br/>with Citations])
    
    style START fill:#14532d,stroke:#4ade80,color:#fff
    style CLARIFY fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style PLAN fill:#3b0764,stroke:#c084fc,color:#fff
    style DISCOVER fill:#164e63,stroke:#22d3ee,color:#fff
    style ANALYZE fill:#422006,stroke:#f97316,color:#fff
    style SYNTHESIZE fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style VERIFY fill:#1c1917,stroke:#a8a29e,color:#fff
    style REPORT fill:#064e3b,stroke:#34d399,color:#fff
    style LEARN fill:#7c2d12,stroke:#fb923c,color:#fff
    style EVALUATE fill:#581c87,stroke:#a78bfa,color:#fff
    style IMPROVE fill:#831843,stroke:#f472b6,color:#fff
    style OUTPUT fill:#14532d,stroke:#4ade80,color:#fff
```

**Key Innovation:** 10-step research pipeline with academic source integration, evidence auditing, and self-improvement feedback loop.

---

## 6. Provider Routing System

```mermaid
graph TB
    QUERY[User Query] --> COMPLEXITY[Complexity<br/>Analyzer]
    
    COMPLEXITY --> SIMPLE{Simple?}
    COMPLEXITY --> COMPLEX{Complex?}
    COMPLEXITY --> STRATEGIC{Strategic?}
    
    subgraph "Fast Tier (Simple Queries)"
        F1[DeepSeek Chat<br/>Cost: $$$]
        F2[Claude Haiku<br/>Cost: $$$$]
        F3[GPT-4o-mini<br/>Cost: $$$]
    end
    
    subgraph "Reasoning Tier (Complex Tasks)"
        R1[Claude Opus<br/>Cost: $$$$$$]
        R2[OpenAI o1<br/>Cost: $$$$$$$]
        R3[DeepSeek V4 Pro<br/>Cost: $$$$]
    end
    
    subgraph "Advisor Tier (Strategic Decisions)"
        A1[Claude Opus 4.7<br/>Architecture]
        A2[Gemini 2.5 Pro<br/>Multi-modal]
        A3[GPT-5<br/>Latest capabilities]
    end
    
    SIMPLE --> F1
    F1 -.Fallback.-> F2
    F2 -.Fallback.-> F3
    
    COMPLEX --> R1
    R1 -.Fallback.-> R2
    R2 -.Fallback.-> R3
    
    STRATEGIC --> A1
    A1 -.Fallback.-> A2
    A2 -.Fallback.-> A3
    
    F1 & F2 & F3 --> RESULT[Response]
    R1 & R2 & R3 --> RESULT
    A1 & A2 & A3 --> RESULT
    
    RESULT --> COST[Cost Tracking]
    RESULT --> QUALITY[Quality Assessment]
    
    COST --> LEARN[Learn Routing<br/>Patterns]
    QUALITY --> LEARN
    LEARN -.Update.-> COMPLEXITY
    
    style QUERY fill:#14532d,stroke:#4ade80,color:#fff
    style COMPLEXITY fill:#422006,stroke:#f97316,color:#fff
    style F1 fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style F2 fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style F3 fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style R1 fill:#3b0764,stroke:#c084fc,color:#fff
    style R2 fill:#3b0764,stroke:#c084fc,color:#fff
    style R3 fill:#3b0764,stroke:#c084fc,color:#fff
    style A1 fill:#164e63,stroke:#22d3ee,color:#fff
    style A2 fill:#164e63,stroke:#22d3ee,color:#fff
    style A3 fill:#164e63,stroke:#22d3ee,color:#fff
    style LEARN fill:#064e3b,stroke:#34d399,color:#fff
```

**Key Innovation:** 3-tier BAAR routing with automatic complexity analysis, cost optimization, and learned routing patterns.

---

## 7. Observability System (AER + SLO)

```mermaid
graph LR
    subgraph "Agent Execution Record (AER)"
        A1[Turn Start<br/>Timestamp + Context]
        A2[Tool Calls<br/>Input + Output]
        A3[LLM Requests<br/>Prompt + Response]
        A4[Errors<br/>Stack traces]
        A5[Turn End<br/>Result + Metrics]
    end
    
    subgraph "Service-Level Objectives (SLO)"
        S1[Latency<br/>< 5s per turn]
        S2[Success Rate<br/>> 95%]
        S3[Cost<br/>< $0.10 per turn]
        S4[Quality<br/>> 4.0/5.0]
        S5[Context Usage<br/>< 80% window]
        S6[Tool Success<br/>> 90%]
        S7[Memory Hit Rate<br/>> 70%]
    end
    
    TURN[Agent Turn] --> A1
    A1 --> A2 --> A3 --> A4 --> A5
    
    A5 --> SQLITE[(SQLite<br/>AER Database)]
    
    SQLITE --> METRICS[Metrics<br/>Calculator]
    METRICS --> S1 & S2 & S3 & S4 & S5 & S6 & S7
    
    S1 & S2 & S3 & S4 & S5 & S6 & S7 --> BREACH{SLO<br/>Breach?}
    
    BREACH -->|Yes| ALERT[Alert +<br/>Auto-adjust]
    BREACH -->|No| CONTINUE[Continue]
    
    ALERT --> ROUTING[Update Routing]
    ALERT --> CACHING[Increase Caching]
    ALERT --> FALLBACK[Enable Fallback]
    
    SQLITE --> ANALYSIS[Offline Analysis]
    ANALYSIS --> PATTERNS[Pattern Detection]
    PATTERNS --> IMPROVE[Improvement<br/>Suggestions]
    
    style TURN fill:#14532d,stroke:#4ade80,color:#fff
    style SQLITE fill:#064e3b,stroke:#34d399,color:#fff
    style METRICS fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style BREACH fill:#422006,stroke:#f97316,color:#fff
    style ALERT fill:#831843,stroke:#f472b6,color:#fff
    style ANALYSIS fill:#3b0764,stroke:#c084fc,color:#fff
    style IMPROVE fill:#164e63,stroke:#22d3ee,color:#fff
```

**Key Innovation:** SQLite-backed execution traces with 7 SLO metrics, automatic breach detection, and self-adjusting behavior.

---

## 8. Context Management

```mermaid
graph TB
    INPUT[User Input] --> PROFILE[Context Profiler<br/>Analyze requirements]
    
    PROFILE --> BUDGET[Budget Calculator<br/>Available tokens]
    
    BUDGET --> PRIORITY[Priority Ranker]
    
    subgraph "Context Sources (Ranked)"
        P0[P0: Critical<br/>Current task + errors]
        P1[P1: High<br/>Recent context]
        P2[P2: Medium<br/>Relevant files]
        P3[P3: Low<br/>Related code]
        P4[P4: Background<br/>General knowledge]
    end
    
    PRIORITY --> P0 & P1 & P2 & P3 & P4
    
    P0 --> INCLUDE{Fits<br/>budget?}
    P1 --> INCLUDE
    P2 --> INCLUDE
    P3 --> INCLUDE
    P4 --> INCLUDE
    
    INCLUDE -->|Yes| CONTEXT[Final Context]
    INCLUDE -->|No| COMPRESS[Compress<br/>or Drop]
    
    COMPRESS --> SUMMARY[Summarize]
    SUMMARY --> CONTEXT
    
    CONTEXT --> VALIDATE[Validate<br/>Completeness]
    VALIDATE --> SEND[Send to LLM]
    
    SEND --> RESPONSE[LLM Response]
    RESPONSE --> CACHE[Prompt Cache<br/>Save for reuse]
    
    CACHE --> NEXT[Next Turn]
    NEXT -.Reuse.-> CONTEXT
    
    style INPUT fill:#14532d,stroke:#4ade80,color:#fff
    style PROFILE fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style BUDGET fill:#422006,stroke:#f97316,color:#fff
    style PRIORITY fill:#3b0764,stroke:#c084fc,color:#fff
    style P0 fill:#831843,stroke:#f472b6,color:#fff
    style P1 fill:#7c2d12,stroke:#fb923c,color:#fff
    style P2 fill:#164e63,stroke:#22d3ee,color:#fff
    style P3 fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style P4 fill:#1c1917,stroke:#a8a29e,color:#fff
    style COMPRESS fill:#581c87,stroke:#a78bfa,color:#fff
    style CACHE fill:#064e3b,stroke:#34d399,color:#fff
```

**Key Innovation:** Priority-based context management with P0-P4 ranking, adaptive compression, and prompt caching for efficiency.

---

## Summary of Innovations

| System | Key Innovation | Impact |
|--------|---------------|--------|
| **Self-Evolution** | 12-phase learning pipeline | Agent improves without retraining |
| **Skills** | SSL representation + SLIM lifecycle | +12.5pp accuracy, automatic curation |
| **Tools** | MCP protocol + permission system | Extensible, secure, tracked |
| **Memory** | Hybrid short/long-term + compression | Efficient context management |
| **Research** | 10-step academic pipeline | Cited, verified research reports |
| **Routing** | 3-tier BAAR with learning | Cost-optimized, quality-aware |
| **Observability** | AER traces + 7 SLO metrics | Full visibility, auto-adjustment |
| **Context** | P0-P4 priority ranking | Optimal token usage |

---

*These diagrams illustrate Lyra's novel architecture that enables continuous learning and improvement.*
