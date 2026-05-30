# Lyra AGI System Architecture Overview

**Version:** 2.0  
**Date:** 2026-05-30  
**Status:** Production

---

## Executive Summary

Lyra is a production-grade autonomous AI system featuring multi-agent orchestration, intelligent model routing, advanced memory architecture, and self-evolution capabilities. The system consists of 99 packages organized into 8 major subsystems, designed for autonomous operation, cost optimization, and continuous improvement.

### Key Capabilities

- **Autonomous Operation**: Goal-driven execution with state machines and scheduling
- **Multi-Agent Swarm**: Parallel agent execution with consensus building
- **Intelligent Routing**: Task-complexity-based model selection (40-50% cost reduction)
- **Advanced Memory**: 4-tier memory hierarchy with automatic consolidation
- **Deep Research**: Multi-hop reasoning with knowledge graph construction
- **Self-Evolution**: Continuous learning and optimization
- **Voice Control**: Natural language interaction with wake word detection

---

## System Architecture

### High-Level Component Map

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Interface["🎯 Interface Layer"]
        CLI[lyra-cli<br/>Command Line Interface]
        TUI[TUI<br/>Terminal UI]
        Voice[Voice Interface<br/>Wake Word + VAD]
        ACP[ACP Server<br/>Agent Communication]
    end
    
    subgraph Core["⚙️ Core Engine (lyra-core)"]
        AgentLoop[Agent Loop<br/>Plan → Execute → Verify]
        Perms[Permission Bridge<br/>Safety Gates]
        TDD[TDD Gate<br/>Test-First Enforcement]
        Safety[Safety Systems<br/>Guardrails]
    end
    
    subgraph Autonomy["🤖 Autonomy System"]
        SM[State Machine<br/>8 States · 12 Transitions]
        GD[Goal Decomposer<br/>Dependency Resolution]
        AE[Automation Engine<br/>Cron Scheduling]
        BM[Budget Manager<br/>Cost Tracking]
        HM[Hooks Manager<br/>Lifecycle Events]
        SessM[Session Manager<br/>Checkpoints]
    end
    
    subgraph Swarm["🐝 Agent Swarm"]
        FO[Fleet Orchestrator<br/>5 Execution Patterns]
        CB[Consensus Builder<br/>4 Aggregation Methods]
        SV[Swarm Visualizer<br/>Real-time Dashboard]
        TeamForm[Team Formation<br/>Dynamic Organization]
    end
    
    subgraph Intelligence["🧠 Intelligence Layer"]
        Router[Model Router<br/>Task-Complexity Routing]
        Memory[Memory System<br/>4-Tier Hierarchy]
        Reasoning[Deep Reasoning<br/>SR2AM · CoT]
        Research[Research Engine<br/>Multi-Hop · KG]
    end
    
    subgraph Skills["🛠️ Skills Ecosystem"]
        SC[Skill Curator]
        SL[Skill Loader]
        SMgr[Skill Manager]
        SpecSkills[7 Specialized Skills<br/>Review · Audit · Test<br/>Profile · Deps · Refactor · Docs]
    end
    
    subgraph Infrastructure["📊 Infrastructure"]
        Mon[Monitoring<br/>18 Metrics]
        Trace[Distributed Tracing<br/>OpenTelemetry]
        Reliab[Reliability<br/>Circuit Breaker · Retry]
        Health[Health Checks<br/>Readiness · Liveness]
    end
    
    subgraph Evolution["🔄 Self-Evolution"]
        GEPA[GEPA v2<br/>Prompt Optimization]
        MetaH[Meta-Harness<br/>Code Optimization]
        PRISM[PRISM<br/>Drift Detection]
    end
    
    subgraph Providers["☁️ LLM Providers"]
        Anthropic[Anthropic<br/>Claude Family]
        DeepSeek[DeepSeek<br/>Cost-Optimized]
        OpenAI[OpenAI<br/>GPT Family]
        Others[16+ Providers]
    end
    
    Interface --> Core
    Core --> Autonomy
    Core --> Swarm
    Core --> Skills
    Core --> Intelligence
    
    Autonomy -->|schedules| Swarm
    Swarm -->|results| Autonomy
    Skills -->|capabilities| Autonomy
    Intelligence -->|routes| Providers
    Infrastructure -->|monitors| Autonomy
    Infrastructure -->|monitors| Swarm
    
    Evolution -->|optimizes| Autonomy
    Evolution -->|optimizes| Skills
    Evolution -->|optimizes| Intelligence
    
    style Interface fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Core fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Autonomy fill:#a78bfa20,stroke:#a78bfa,stroke-width:2px
    style Swarm fill:#818cf820,stroke:#818cf8,stroke-width:2px
    style Intelligence fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Skills fill:#10b98120,stroke:#10b981,stroke-width:2px
    style Infrastructure fill:#f9731620,stroke:#f97316,stroke-width:2px
    style Evolution fill:#ec489920,stroke:#ec4899,stroke-width:2px
    style Providers fill:#94a3b820,stroke:#94a3b8,stroke-width:2px
```

---

## Data Flow Architecture

### Complete Request Flow

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant User
    participant CLI
    participant Router as Model Router
    participant SM as State Machine
    participant GD as Goal Decomposer
    participant FO as Fleet Orchestrator
    participant Memory
    participant LLM as LLM Provider
    participant Monitor as Monitoring
    
    User->>CLI: Submit Goal
    CLI->>Router: Classify Task Type
    Router-->>CLI: Selected Model Tier
    
    CLI->>SM: Initialize Goal
    SM->>SM: IDLE → PLANNING
    SM->>Monitor: Record State Transition
    
    SM->>GD: Decompose Goal
    GD->>GD: Build Dependency Graph
    GD->>GD: Topological Sort
    GD-->>SM: Execution Order
    
    SM->>SM: PLANNING → EXECUTING
    
    loop For Each Subtask
        SM->>FO: Create Fleet
        FO->>FO: Spawn Agents
        
        par Parallel Execution
            FO->>LLM: Agent 1 Execute
            FO->>LLM: Agent 2 Execute
            FO->>LLM: Agent N Execute
        end
        
        FO->>FO: Build Consensus
        FO-->>SM: Consensus Result
        
        SM->>Memory: Store Experience
        SM->>Monitor: Record Metrics
    end
    
    SM->>SM: EXECUTING → VERIFYING
    SM->>SM: VERIFYING → COMPLETED
    SM->>SM: COMPLETED → IDLE
    
    SM-->>CLI: Final Result
    CLI-->>User: Display Output
```

---

## Core Subsystems

### 1. Autonomy System

**Purpose**: Goal-driven autonomous execution with state management

**Key Components**:
- **State Machine**: 8-state FSM with guarded transitions
- **Goal Decomposer**: Kahn's algorithm for dependency resolution
- **Session Manager**: JSON checkpoint persistence
- **Automation Engine**: Cron-like scheduling
- **Budget Manager**: Cost tracking with limits
- **Hooks Manager**: 5 lifecycle events

**Location**: `packages/lyra-cli/src/lyra_cli/autonomy/`

**Documentation**: [autonomy-system.md](./autonomy-system.md)

---

### 2. Agent Swarm

**Purpose**: Multi-agent parallel execution with consensus building

**Key Components**:
- **Fleet Orchestrator**: 5 execution patterns (fan-out, pipeline, map-reduce, tournament, ensemble)
- **Consensus Builder**: 4 aggregation methods (majority, weighted, unanimous, threshold)
- **Swarm Visualizer**: Real-time tmux dashboard
- **Team Formation**: Dynamic agent organization

**Location**: `packages/lyra-agent-swarm/`

**Documentation**: [agent-swarm.md](./agent-swarm.md)

---

### 3. Model Router

**Purpose**: Intelligent model selection for cost optimization

**Key Features**:
- Task-complexity assessment
- 5-tier model cascading (Haiku → Sonnet → Opus)
- Provider-family routing (11 providers)
- Cost tracking and optimization
- 40-50% cost reduction achieved

**Location**: `packages/lyra-cli/src/lyra_cli/llm_router.py`

**Documentation**: [model-router.md](./model-router.md)

---

### 4. Memory Architecture

**Purpose**: Multi-tier memory with automatic consolidation

**Key Features**:
- 4-tier hierarchy: Working → Episodic → Semantic → Procedural
- Retrieval-first design (20× impact)
- Thermodynamic arbitration
- Utility-based pruning
- Cross-session persistence

**Location**: `packages/lyra-memory/`

**Documentation**: [MEMORY-ARCHITECTURE-V2.md](./MEMORY-ARCHITECTURE-V2.md)

---

### 5. Research Engine

**Purpose**: Multi-hop deep research with knowledge graphs

**Key Features**:
- Iterative query refinement
- Knowledge graph construction
- Source credibility scoring
- 5 research strategies
- Citation management

**Location**: `packages/lyra-research/`

**Documentation**: [research-engine.md](./research-engine.md)

---

### 6. Skills System

**Purpose**: Extensible skill library with specialized capabilities

**Specialized Skills**:
1. **Code Reviewer**: AST-based code review (7 structural + 5 security checks)
2. **Security Auditor**: OWASP Top 10 scanning (8 scan types)
3. **Test Generator**: pytest skeleton generation
4. **Performance Profiler**: Complexity estimation
5. **Dependency Analyzer**: Import analysis with cycle detection
6. **Refactoring Advisor**: Code smell detection
7. **Documentation Writer**: Docstring generation

**Location**: `packages/lyra-cli/src/lyra_cli/skills/`

**Documentation**: [skills-system.md](./skills-system.md)

---

### 7. Infrastructure

**Purpose**: Monitoring, tracing, reliability, and health checks

**Key Components**:
- **Monitoring**: 18 default metrics (counter, gauge, histogram)
- **Tracing**: OpenTelemetry-compatible distributed tracing
- **Reliability**: Circuit breaker, retry with exponential backoff
- **Health Checks**: Readiness and liveness probes
- **Profiler**: cProfile + tracemalloc integration

**Location**: `packages/lyra-cli/src/lyra_cli/infrastructure/`

**Documentation**: [MONITORING-SYSTEM.md](./MONITORING-SYSTEM.md)

---

### 8. Self-Evolution

**Purpose**: Continuous learning and optimization

**Key Components**:
- **GEPA v2**: Prompt optimization through evolution
- **Meta-Harness**: Code optimization and refactoring
- **PRISM**: Performance drift detection
- **AEvo**: Procedure editing and improvement

**Location**: Various packages

**Documentation**: [autonomy-system.md](./autonomy-system.md#self-evolution)

---

## Technology Stack

### Core Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.11+ | Core implementation |
| **CLI Framework** | Click | Command-line interface |
| **TUI Framework** | Textual | Terminal user interface |
| **Async Runtime** | asyncio | Asynchronous execution |
| **Testing** | pytest | Unit and integration tests |
| **Type Checking** | mypy | Static type analysis |
| **Packaging** | uv | Fast Python package manager |

### LLM Providers

| Provider | Models | Use Case |
|----------|--------|----------|
| **Anthropic** | Claude Opus 4.7, Sonnet 4.6, Haiku 4.5 | Primary provider, all task types |
| **DeepSeek** | v4-pro, v4-flash, chat | Cost-optimized alternative |
| **OpenAI** | o3, GPT-4o, GPT-3.5-turbo | Reasoning and coding |
| **Gemini** | 2.5-pro-preview, 2.5-flash | Google ecosystem |
| **Others** | Mistral, Qwen, xAI, Groq, Cerebras, Ollama | Specialized use cases |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Monitoring** | Custom metrics + Prometheus-compatible | System observability |
| **Tracing** | OpenTelemetry | Distributed tracing |
| **Storage** | JSON files, SQLite | Persistence |
| **Voice** | Porcupine, WebRTC VAD | Wake word detection |
| **Speech** | Whisper, TTS engines | Speech processing |

---

## Performance Characteristics

### System Benchmarks

| Metric | Value | Target |
|--------|-------|--------|
| **Total Tests** | 550+ | 80%+ coverage |
| **Packages** | 99 | Modular architecture |
| **Cost Reduction** | 40-50% | vs. always-Opus baseline |
| **Memory Efficiency** | 30-50× | Token reduction |
| **Retrieval Accuracy** | >95% | Needle-in-haystack |
| **State Transition** | <1ms | Autonomy FSM |
| **Model Selection** | <2ms | Routing overhead |

### Scalability

| Dimension | Current | Target |
|-----------|---------|--------|
| **Concurrent Agents** | 10-20 | 100+ |
| **Context Window** | 8K-200K | 3.5M tokens |
| **Memory Growth** | Linear | Controlled |
| **Request Throughput** | 10-50 req/s | 1000+ req/s |

---

## Deployment Architecture

### Single-Process Deployment

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Process["Lyra Process"]
        subgraph Threads["Thread Pool"]
            Main[Main Thread<br/>CLI + Autonomy]
            Swarm[Swarm Thread<br/>Fleet Orchestrator]
            Mon[Monitoring Thread<br/>Metrics Collection]
            Voice[Voice Thread<br/>Audio Processing]
            Auto[Automation Thread<br/>Scheduler]
        end
        
        subgraph State["Shared State"]
            SM_State[StateMachine State]
            Budget[Budget Data]
            Metrics[Metrics Registry]
            Memory_Cache[Memory Cache]
        end
    end
    
    subgraph Storage["File System"]
        Checkpoints[~/.lyra/checkpoints/]
        Budget_File[~/.lyra/budget_data.json]
        Config[~/.lyra/config.yaml]
        Memory_Store[~/.lyra/memory/]
    end
    
    Threads -.->|shared memory| State
    State -.->|persist| Storage
    
    style Process fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Threads fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style State fill:#f59e0b20,stroke:#f59e0b,stroke-width:2px
    style Storage fill:#94a3b820,stroke:#94a3b8,stroke-width:2px
```

### File System Layout

```
~/.lyra/
├── checkpoints/              # Session checkpoints
│   ├── sess_abc-20260530T120000Z.json
│   └── sess_def-20260530T130000Z.json
├── budget_data.json          # Cost tracking journal
├── config.yaml               # User configuration
├── memory/                   # Memory persistence
│   ├── working/              # Working memory
│   ├── episodic/             # Episodic memory
│   ├── semantic/             # Semantic memory
│   └── procedural/           # Procedural memory
├── research/                 # Research artifacts
│   ├── knowledge_graph.json
│   └── research_cache/
└── logs/                     # System logs
    ├── autonomy.log
    ├── swarm.log
    └── monitoring.log
```

---

## Integration Points

### Internal Integration

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph A[Autonomy]
        SM[State Machine]
        BM[Budget Manager]
    end
    
    subgraph B[Swarm]
        FO[Fleet Orchestrator]
        CB[Consensus Builder]
    end
    
    subgraph C[Intelligence]
        Router[Model Router]
        Memory[Memory System]
    end
    
    subgraph D[Infrastructure]
        Mon[Monitoring]
        Trace[Tracing]
    end
    
    SM -->|spawns| FO
    FO -->|results| SM
    SM -->|checks| BM
    SM -->|routes via| Router
    FO -->|stores in| Memory
    SM -->|records to| Mon
    FO -->|traces to| Trace
    
    style A fill:#a78bfa20,stroke:#a78bfa,stroke-width:2px
    style B fill:#818cf820,stroke:#818cf8,stroke-width:2px
    style C fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style D fill:#f9731620,stroke:#f97316,stroke-width:2px
```

### External Integration

| Integration | Protocol | Purpose |
|-------------|----------|---------|
| **LLM Providers** | HTTP/HTTPS | Model inference |
| **File System** | OS calls | Persistence |
| **Tmux** | tmux CLI | Swarm dashboard |
| **Audio System** | OS audio APIs | Voice I/O |
| **MCP Servers** | MCP Protocol | Tool execution |
| **Plugin System** | Python imports | Skill extensions |

---

## Security & Safety

### Safety Mechanisms

1. **Permission Bridge**: Explicit user approval for sensitive operations
2. **Budget Limits**: Hard caps on API spending ($10/day, $200/month)
3. **TDD Gate**: Enforce test-first development
4. **Safety Guardrails**: Content filtering and ethical constraints
5. **Circuit Breaker**: Prevent cascading failures
6. **Audit Logging**: Track all system actions

### Security Features

1. **Input Validation**: Sanitize all user inputs
2. **Credential Management**: Secure API key storage
3. **Sandboxed Execution**: Isolated agent execution
4. **Rate Limiting**: Prevent abuse
5. **Error Handling**: Graceful degradation
6. **Security Auditor**: OWASP Top 10 scanning

---

## Development Workflow

### Standard Development Flow

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    Start[User Request] --> Classify[Task Classification]
    Classify --> Route[Model Selection]
    Route --> Plan[Goal Decomposition]
    Plan --> Execute[Agent Execution]
    Execute --> Verify[Verification]
    Verify -->|Pass| Complete[Complete]
    Verify -->|Fail| Recover[Recovery]
    Recover --> Plan
    Complete --> Store[Store Experience]
    Store --> Learn[Self-Evolution]
    
    style Start fill:#7c3aed20,stroke:#7c3aed,stroke-width:2px
    style Execute fill:#3b82f620,stroke:#3b82f6,stroke-width:2px
    style Complete fill:#10b98120,stroke:#10b981,stroke-width:2px
    style Learn fill:#ec489920,stroke:#ec4899,stroke-width:2px
```

---

## Future Roadmap

### Phase 1: Foundation (Complete)
- ✅ Core autonomy system
- ✅ Agent swarm orchestration
- ✅ Model routing
- ✅ Basic memory system
- ✅ Infrastructure monitoring

### Phase 2: Intelligence (In Progress)
- 🔄 Advanced memory architecture (4-tier)
- 🔄 Deep research engine
- 🔄 Self-evolution capabilities
- 🔄 Voice control integration

### Phase 3: Scale (Planned)
- 📋 Distributed execution
- 📋 Multi-tenant support
- 📋 Cloud deployment
- 📋 Enterprise features

### Phase 4: AGI (Research)
- 🔬 Emergent capabilities
- 🔬 Meta-learning
- 🔬 Recursive self-improvement
- 🔬 General intelligence

---

## Related Documentation

### Architecture Documents
- [Autonomy System](./autonomy-system.md) - State machines and goal decomposition
- [Agent Swarm](./agent-swarm.md) - Multi-agent orchestration
- [Model Router](./model-router.md) - Intelligent model selection
- [Memory Architecture](./MEMORY-ARCHITECTURE-V2.md) - 4-tier memory system
- [Research Engine](./research-engine.md) - Multi-hop research
- [Skills System](./skills-system.md) - Specialized capabilities
- [Monitoring System](./MONITORING-SYSTEM.md) - Infrastructure observability

### User Documentation
- [User Guide](../USER_GUIDE.md) - Getting started
- [API Documentation](../API_DOCUMENTATION.md) - API reference
- [Developer Guide](../DEVELOPER_GUIDE.md) - Development guide

### Research & Design
- [Research Summary](../RESEARCH_SUMMARY.md) - Research findings
- [Design Documents](../design/) - Design decisions
- [Performance Benchmarks](../PERFORMANCE_BENCHMARKS.md) - Performance data

---

<div align="center">

**Lyra AGI System Architecture**

Version 2.0 | 2026-05-30 | Production

[README](../../README.md) · [Architecture](./README.md) · [User Guide](../USER_GUIDE.md)

</div>
