# Lyra Architecture Documentation

> **Complete architectural reference with diagrams, data flows, and design decisions**

## Table of Contents

- [Overview](#overview)
- [System Topology](#system-topology)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)
- [Documentation Index](#documentation-index)

---

## Overview

Lyra is a production-grade AI agent platform built on six architectural layers:

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph L0["Layer 0: Interface"]
        CLI[CLI Interface]
        TUI[Terminal UI]
        ACP[ACP Server]
        Voice[Voice System]
    end
    
    subgraph L1["Layer 1: Kernel"]
        Loop[AgentLoop]
        TDD[TDD Gate]
        Perms[Permissions]
        HIR[HIR Emitter]
    end
    
    subgraph L2["Layer 2: Intelligence"]
        Router[Model Router]
        Memory[Memory System]
        Skills[Skills System]
        Reasoning[Deep Reasoning]
    end
    
    subgraph L3["Layer 3: Coordination"]
        Orchestrator[Orchestrator]
        Fleet[Agent Fleet]
        Subagents[Subagents]
    end
    
    subgraph L4["Layer 4: Safety"]
        CogExec[Cognitive-Executive Split]
        Shield[AgentShield]
        Verifier[Multi-Agent Verifier]
    end
    
    subgraph L5["Layer 5: Providers"]
        Anthropic[Anthropic]
        DeepSeek[DeepSeek]
        OpenAI[OpenAI]
        Others[16+ Providers]
    end
    
    L0 --> L1
    L1 --> L2
    L1 --> L3
    L1 --> L4
    L2 --> L5
    L3 --> L5
    
    style L0 fill:#7c3aed20
    style L1 fill:#f59e0b20
    style L2 fill:#3b82f620
    style L3 fill:#10b98120
    style L4 fill:#ef444420
    style L5 fill:#ec489920
```

---

## System Topology

### High-Level Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    User[User] --> Interface
    
    subgraph Interface["🎯 Interface Layer"]
        CLI[CLI]
        TUI[Terminal UI]
        ACP[ACP Server]
    end
    
    subgraph Kernel["⚙️ Kernel Layer"]
        Loop[AgentLoop]
        TDD[TDD Gate]
        Perms[PermissionBridge]
        HIR[HIR Emitter]
    end
    
    subgraph Intelligence["🧠 Intelligence Layer"]
        Router[Model Router<br/>5-layer cascading]
        Memory[6-Layer Memory<br/>Dream consolidation]
        Skills[Skills System<br/>64+ skills]
        Reasoning[Deep Reasoning<br/>SR2AM · CoT]
    end
    
    subgraph Safety["🛡️ Safety Layer"]
        CogExec[Cognitive-Executive Split<br/>98.9% block rate]
        Shield[AgentShield<br/>5 scanners]
        Verifier[Multi-Agent Verifier<br/>3-stage pipeline]
    end
    
    subgraph Providers["☁️ LLM Providers"]
        P1[Anthropic]
        P2[DeepSeek]
        P3[OpenAI]
        P4[Google]
        P5[16+ Others]
    end
    
    Interface --> Kernel
    Kernel --> Intelligence
    Kernel --> Safety
    Intelligence --> Providers
    
    style Interface fill:#7c3aed20
    style Kernel fill:#f59e0b20
    style Intelligence fill:#3b82f620
    style Safety fill:#ef444420
    style Providers fill:#ec489920
```

### Package Dependencies

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    CLI[lyra-cli] --> Core[lyra-core]
    
    Core --> Agents[lyra-agents]
    Core --> Memory[lyra-memory]
    Core --> Skills[lyra-skills]
    Core --> Orchestration[lyra-orchestration]
    
    CLI --> Reasoning[lyra-reasoning]
    CLI --> Research[lyra-research]
    CLI --> Evolution[lyra-evolution]
    CLI --> Router[lyra-router]
    CLI --> Safety[lyra-safety]
    
    Agents --> RecLink[lyra-recursive-link]
    Memory --> Cognitive[lyra-cognitive]
    Orchestration --> Colony[lyra-colony]
    Evolution --> MetaEvol[lyra-meta-evolution]
    
    CLI --> UIC[ui-core]
    UIC --> UIT[ui-terminal]
    UIT --> UITR[ui-transport]
    
    style Core fill:#f59e0b20
    style CLI fill:#7c3aed20
    style Safety fill:#ef444420
    style UIT fill:#3b82f620
```

---

## Core Components

### 1. AgentLoop (Kernel)

The central execution engine that orchestrates all agent operations.

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> IDLE
    IDLE --> PLAN: Task received
    PLAN --> RED: Plan approved
    RED --> GREEN: Tests written
    GREEN --> REFACTOR: Tests passing
    REFACTOR --> VERIFY: Code refactored
    VERIFY --> SHIP: Verification passed
    SHIP --> [*]
    
    RED --> PLAN: Tests invalid
    GREEN --> RED: Tests failing
    REFACTOR --> GREEN: Refactor broke tests
    VERIFY --> REFACTOR: Verification failed
```

**Key Features**:
- TDD state machine enforcement
- Plan-gated execution
- Pivot/Refine recovery loop
- HIR event emission

### 2. Memory System (6-Layer NeuroMemory)

Hierarchical memory architecture with automatic consolidation.

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    L0[L0: Sensory<br/>~500 tokens<br/>ephemeral] --> L1[L1: Episodic<br/>Session traces<br/>temporal]
    L1 --> L2[L2: Semantic<br/>Facts & knowledge<br/>JSON indexed]
    L2 --> L3[L3: Procedural<br/>Skills & patterns<br/>action sequences]
    L3 --> L4[L4: Meta<br/>Learning traces<br/>what worked]
    L4 --> L5[L5: Collective<br/>Fleet knowledge<br/>cross-session]
    
    Dream[Dream Consolidator<br/>Orient→Gather→Consolidate→Prune]
    L1 -.-> Dream
    L2 -.-> Dream
    Dream -.-> L2
    Dream -.-> L3
    
    style L0 fill:#f59e0b20
    style L1 fill:#3b82f620
    style L2 fill:#3b82f620
    style L3 fill:#7c3aed20
    style L4 fill:#7c3aed20
    style L5 fill:#ec489920
    style Dream fill:#10b98120
```

**Key Features**:
- A-MAC 5-factor admission control
- CoMem async pipeline (1.4x latency improvement)
- Free-energy consolidation
- Hybrid BM25+Vector retrieval
- 61% token reduction

### 3. Model Router (5-Layer Intelligent Routing)

Cascading router that selects optimal model per task.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Task[Task Input] --> L1[Layer 1: Classify<br/>15 categories]
    L1 --> L2[Layer 2: Estimate<br/>Complexity 1-10]
    L2 --> L3[Layer 3: Match<br/>Capabilities]
    L3 --> L4[Layer 4: Optimize<br/>Cost cascade]
    L4 --> L5[Layer 5: History<br/>Learned routing]
    
    L5 --> Decision{Confidence<br/>≥ 0.75?}
    Decision -->|Yes| Execute[Execute]
    Decision -->|No| Escalate[Escalate to<br/>next tier]
    Escalate --> L4
    
    style Task fill:#7c3aed20
    style Execute fill:#10b98120
    style Escalate fill:#f59e0b20
```

**Key Features**:
- Task-aware classification
- Complexity estimation
- Capability matching
- Cost optimization
- Performance history learning

### 4. Safety Architecture (Parallax-Style)

Cognitive-executive separation with multi-agent validation.

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    Input[User Input] --> Reasoning[Reasoning Context<br/>READ-ONLY<br/>Planning · Analysis]
    
    Reasoning --> Barrier[=== STRUCTURAL BARRIER ===<br/>Multi-agent approval required]
    
    Barrier -->|Approved<br/>98.9%| Execution[Execution Context<br/>ACTION-CAPABLE<br/>Tools · Code · Deploy]
    Barrier -->|Blocked<br/>1.1%| Reject[BLOCKED<br/>+ Audit Log]
    
    Execution --> Validator[Validator Agent<br/>Different model family]
    Validator --> Critic[Critic Agent<br/>Reviews validator]
    Critic --> IntentMon[Intent Monitor<br/>Behavioral analysis]
    
    IntentMon -->|Anomaly| Reject
    IntentMon -->|Clean| Output[Safe Output]
    
    style Reasoning fill:#3b82f620
    style Barrier fill:#f59e0b20
    style Execution fill:#ef444420
    style Reject fill:#dc262620
    style Output fill:#10b98120
```

**Key Features**:
- Structural separation of reasoning and execution
- Multi-agent validation pipeline
- Intent-based behavioral monitoring
- 98.9% adversarial block rate

### 5. Self-Evolution Pipeline

Meta-optimization loop for continuous improvement.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    Observe[1. OBSERVE<br/>Traces · Metrics · Drift] --> Analyze[2. ANALYZE<br/>Bottlenecks · Patterns · Gaps]
    Analyze --> Propose[3. PROPOSE<br/>GEPA v2 · AEvo · Meta-Harness]
    Propose --> Verify[4. VERIFY<br/>ARIS · Cross-Model · Regression]
    Verify -->|Pass| Deploy[5. DEPLOY<br/>Canary · Monitor · Rollout]
    Verify -->|Fail| Refine[Refine & Retry]
    Refine --> Propose
    
    Deploy --> Monitor[PRISM Monitor]
    Monitor -->|Regression| Rollback[Auto-Rollback]
    Monitor -->|Drift| Refine
    
    style Observe fill:#3b82f620
    style Analyze fill:#f59e0b20
    style Propose fill:#7c3aed20
    style Verify fill:#ef444420
    style Deploy fill:#10b98120
```

**Key Features**:
- GEPA v2 prompt optimization
- Meta-Harness code optimization
- AEvo procedure editing
- ARIS adversarial review
- PRISM drift detection

---

## Data Flow

### Complete Execution Flow

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant User
    participant CLI
    participant Voice
    participant Engine as AgentLoop
    participant Router
    participant CogExec as Cognitive-Executive
    participant Memory
    participant Agent
    participant RecLink as RecursiveLink
    participant LLM
    participant Tools
    participant Verifier
    participant Dream
    
    User->>CLI: "Add Redis caching"
    CLI->>Voice: play(session.start)
    CLI->>Engine: run(task)
    
    Engine->>Memory: recall(context)
    Memory-->>Engine: history + skills
    
    Engine->>Router: route(task)
    Router-->>Engine: ModelSelection(sonnet)
    
    Engine->>CogExec: separate(reasoning, execution)
    CogExec-->>Engine: contexts
    
    Engine->>Engine: plan(steps)
    
    loop For each step
        Engine->>Agent: dispatch(step)
        Agent->>LLM: prompt + tools
        LLM-->>Agent: response
        Agent->>Tools: execute
        Tools-->>Agent: result
        
        Agent->>RecLink: share_latent_state
        RecLink-->>Agent: compressed (75.6% reduction)
        
        Agent-->>Engine: step_complete
    end
    
    Engine->>Verifier: verify(output)
    Verifier-->>Engine: pass ✓
    
    Engine->>Dream: consolidate
    Dream-->>Memory: enriched memories
    
    Engine->>Voice: play(task.complete)
    Engine-->>CLI: result
    CLI-->>User: "Done. 3 files changed ✓"
```

---

## Design Decisions

### Key Architectural Commitments

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Kernel separate from CLI** | Zero network deps, reusable by MCP/SDK | Two packages to version |
| **Monorepo with 99 packages** | Isolated deps, independent lifecycle | Build complexity |
| **TDD state machine** | Enforces test-first development | Slower initial iteration |
| **6-layer memory** | Mimics cognitive architecture | Consolidation tuning needed |
| **Cognitive-executive split** | Structural safety barrier | ~100ms latency overhead |
| **RecursiveLink latent comms** | 75.6% token reduction | Requires training |
| **5-layer router** | Optimal model per task | ~50ms routing latency |
| **HIR JSONL audit trail** | Full observability | ~1MB/hour disk usage |

### Innovation Lineage

Every Lyra innovation traces to research sources:

| Innovation | Source | Implementation |
|------------|--------|----------------|
| **Tournament TTS** | [Meta, 2026](https://arxiv.org/abs/2604.16529) | `lyra_core/tts/tournament.py` |
| **SR2AM Planning** | [SR2AM, 2026](https://arxiv.org/abs/2605.22138) | `lyra_reasoning/sr2am/` |
| **6-Layer Memory** | TencentDB + MemPalace + CraniMem | `lyra_memory/` |
| **A-MAC Admission** | [A-MAC, 2026](https://arxiv.org/abs/2605.20163) | `lyra_memory/admission.py` |
| **Dream Consolidation** | ICLR 2026 MemAgent Workshop | `lyra_memory/dream.py` |
| **RecursiveLink** | [RecursiveMAS, 2026](https://arxiv.org/abs/2505.23119) | `lyra_recursive_link/` |
| **Parallax Safety** | [Parallax, 2026](https://arxiv.org/abs/2604.12986) | `lyra_safety/parallax.py` |
| **GEPA v2** | [GEPA, ICLR 2026](https://arxiv.org/abs/2310.03714) | `lyra_evolution/gepa_v2.py` |
| **Meta-Harness** | [Meta-Harness, 2026](https://arxiv.org/abs/2603.28052) | `lyra_meta_evolution/` |
| **SkillOpt** | [Microsoft, 2026](https://arxiv.org/abs/2605.23904) | `lyra_skills/optimizer.py` |

---

## Documentation Index

### Core Architecture

- **[System Topology](topology.md)** — Layer-by-layer breakdown
- **[Commitments](commitments.md)** — Architectural guarantees
- **[Gap Analysis](gap-analysis.md)** — Current vs. target state

### Major Systems

- **[Memory Consolidation](memory-consolidation.md)** — Dream 4-phase design
- **[Safety Architecture](safety-architecture.md)** — Parallax cognitive-executive split
- **[Model Router](model-router.md)** — 5-layer intelligent routing
- **[Skills System](skills-system.md)** — 64-skill catalog + lifecycle
- **[Harness Evolution](harness-evolution.md)** — Meta-optimization loop

### Advanced Topics

- **[Breakthrough Architectures](breakthrough-architectures.md)** — Plan 13 innovations
- **[Implementation Roadmap](implementation-roadmap.md)** — Development timeline
- **[Preliminary Architecture](preliminary-architecture.md)** — Early design docs
- **[Harness Plugins](harness-plugins.md)** — Plugin system design

---

## Research Foundation

### Papers (100+)

Lyra is built on research from:
- **Reasoning**: Tournament TTS, SR2AM, ReasoningBank, SWE-Search
- **Memory**: A-MAC, CoMem, Dream consolidation, TencentDB-Agent-Memory
- **Self-Evolution**: GEPA v2, Meta-Harness, AEvo, PRISM, Trace2Skill
- **Skills**: SkillOpt, Ratchet, SkillGen, MIND-Skill
- **Safety**: Parallax, ARIS, Knowing-Doing Gap
- **Communication**: RecursiveMAS, SemaClaw

See [docs/research/papers.md](../research/papers.md) for complete absorption matrix.

### Repositories (80+)

Key repos studied:
- **Claude Code ecosystem**: superpowers, claude-mem, awesome-claude-code
- **Agent frameworks**: MetaGPT, ChatDev, AutoGPT, CrewAI
- **Memory systems**: TencentDB-Agent-Memory, MemPalace, CodeGraph
- **Infrastructure**: Hermes-agent, Continuous-Claude, Ruflo

See [docs/research/repos.md](../research/repos.md) for complete absorption matrix.

---

## Performance Characteristics

### Speed

- **Average task completion**: 45 seconds
- **Speedup vs baseline**: 2.3x faster
- **Parallel agent execution**: 2-3x speedup

### Cost

- **Average cost per task**: $0.12
- **Cost reduction**: 3x cheaper with DeepSeek
- **Token efficiency**: 75.6% reduction (RecursiveLink)

### Quality

- **Test coverage**: 80%+ enforced
- **Success rate**: 94.3%
- **Bug rate**: 2.1%
- **Safety block rate**: 98.9%

See [PERFORMANCE_BENCHMARKS.md](../PERFORMANCE_BENCHMARKS.md) for detailed analysis.

---

## Next Steps

- **[User Guide](../USER_GUIDE.md)** — Using Lyra
- **[Developer Guide](../DEVELOPER_GUIDE.md)** — Contributing to Lyra
- **[API Documentation](../API_DOCUMENTATION.md)** — Programmatic usage
- **[Performance Benchmarks](../PERFORMANCE_BENCHMARKS.md)** — Speed and cost analysis

---

<div align="center">

**Complete architectural reference for Lyra**

[README](../../README.md) · [User Guide](../USER_GUIDE.md) · [Developer Guide](../DEVELOPER_GUIDE.md)

</div>
