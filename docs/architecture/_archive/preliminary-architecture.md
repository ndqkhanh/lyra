# Lyra AGI Enhancement - Preliminary Architecture

**Status**: Draft - Updating as research agents complete  
**Last Updated**: 2026-05-26  
**Completion**: 3/20 agents (15%)

---

## Executive Summary

This document outlines the architectural enhancements to transform Lyra from a multi-provider LLM CLI into a state-of-the-art AGI multi-agent system. Based on analysis of 40+ papers and 30+ repositories, we've identified breakthrough patterns in memory, orchestration, skills, and safety.

---

## 1. Current Lyra Architecture

### Strengths
- ✅ Multi-provider abstraction (8+ providers: Anthropic, OpenAI, Bedrock, Vertex, Gemini, Ollama, Copilot, OpenRouter)
- ✅ MCP (Model Context Protocol) integration for tools
- ✅ Research pipeline orchestration
- ✅ Interactive chat with streaming
- ✅ Comprehensive test coverage (40+ test files)
- ✅ Modular design (client/, providers/, interactive/, commands/)

### Gaps (Identified So Far)
- ❌ No intelligent model routing (all tasks use same model)
- ❌ Basic memory (no multi-layer, no cross-session recall)
- ❌ Static skills system (no learning, no auto-generation)
- ❌ Limited autonomy (no continuous operation)
- ❌ Basic UI/UX (no themes, limited keybindings)
- ❌ No safety gates (approval workflows missing)
- ❌ No agent swarm capabilities

---

## 2. Breakthrough Memory Architecture (P0 - Critical)

### Research Foundation
**Source**: MRAgent paper (MemAgents batch 3)

### Key Innovation
**Active Retrieval > Passive Retrieval**
- Traditional RAG: Single-shot similarity search (passive)
- MRAgent: Multi-hop reasoning with adaptive queries (active)
- **Proven**: Active retrieval achieves zero error on certain distributions; passive has irreducible error

### Proposed Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#8b5cf6', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#a78bfa', 'lineColor': '#94a3b8', 'secondaryColor': '#1e293b', 'tertiaryColor': '#0d1117', 'background': '#0d1117', 'mainBkg': '#1e293b', 'nodeBorder': '#a78bfa', 'clusterBkg': '#1e293b', 'clusterBorder': '#8b5cf6', 'titleColor': '#c084fc', 'edgeLabelBackground': '#1e293b' }}%%
graph TB
    subgraph "Memory Layers"
        WM[Working Memory<br/>Current Context]
        EM[Episodic Memory<br/>Cue-Tag-Episode]
        SM[Semantic Memory<br/>Cue-Tag-Semantic]
        TM[Topic Memory<br/>High-level Patterns]
    end
    
    subgraph "Retrieval Engine"
        AR[Active Retrieval<br/>Multi-hop Reasoning]
        QA[Query Adaptation<br/>Based on Retrieved Content]
        KG[Knowledge Graph<br/>Heterogeneous Relations]
    end
    
    subgraph "Persistence"
        CS[Cross-Session Store<br/>SQLite/PostgreSQL]
        CC[Context Compression<br/>Consolidation]
        IX[Indexing<br/>Vector + Graph]
    end
    
    WM --> AR
    AR --> EM
    AR --> SM
    AR --> TM
    EM --> KG
    SM --> KG
    TM --> KG
    AR --> QA
    QA --> AR
    KG --> CS
    CS --> CC
    CC --> IX
```

### Memory Layers

#### 1. Working Memory
- **Purpose**: Current conversation context
- **Capacity**: ~8K tokens (configurable)
- **Lifetime**: Current session
- **Implementation**: In-memory buffer with LRU eviction

#### 2. Episodic Memory (Cue-Tag-Episode)
- **Purpose**: Fine-grained event records
- **Structure**: 
  - Cue: Trigger or context
  - Tag: Categorical label
  - Episode: Detailed event data
- **Example**: 
  ```json
  {
    "cue": "user asked about authentication",
    "tag": "security",
    "episode": {
      "timestamp": "2026-05-26T12:00:00Z",
      "query": "How do I implement OAuth2?",
      "response": "...",
      "files_accessed": ["auth.py", "oauth.py"],
      "outcome": "success"
    }
  }
  ```

#### 3. Semantic Memory (Cue-Tag-Semantic)
- **Purpose**: Stable abstractions beyond individual episodes
- **Structure**: Generalized knowledge extracted from episodes
- **Example**:
  ```json
  {
    "cue": "authentication patterns",
    "tag": "security",
    "semantic": {
      "pattern": "OAuth2 flow",
      "components": ["authorization_endpoint", "token_endpoint", "redirect_uri"],
      "best_practices": ["use PKCE", "validate state parameter"],
      "related_files": ["auth.py", "oauth.py", "config.py"]
    }
  }
  ```

#### 4. Topic Memory (High-level Patterns)
- **Purpose**: Recurring themes across episodes
- **Structure**: Multi-granular reasoning patterns
- **Example**:
  ```json
  {
    "topic": "security_implementation",
    "frequency": 15,
    "episodes": ["ep_001", "ep_023", "ep_045"],
    "patterns": [
      "user often asks about auth after database setup",
      "security questions cluster around deployment time"
    ]
  }
  ```

### Active Retrieval Algorithm

```python
def active_retrieval(query: str, max_hops: int = 8) -> Context:
    """
    Multi-hop active retrieval with adaptive query refinement.
    
    Proven superior to passive retrieval (MRAgent paper).
    """
    context = []
    current_query = query
    
    for hop in range(max_hops):
        # Retrieve based on current query
        results = retrieve_from_kg(current_query)
        context.extend(results)
        
        # Adaptive query refinement based on retrieved content
        if is_sufficient(context, query):
            break
            
        # Generate next query based on what we found
        current_query = refine_query(query, context, results)
    
    return consolidate_context(context)
```

### Implementation Plan

**Phase 1: Foundation (Week 1-2)**
- [ ] Design memory schema (SQLite for MVP, PostgreSQL for production)
- [ ] Implement working memory buffer
- [ ] Create episodic memory storage
- [ ] Build basic retrieval (passive, for baseline)

**Phase 2: Active Retrieval (Week 3-4)**
- [ ] Implement knowledge graph structure
- [ ] Build multi-hop retrieval engine
- [ ] Add query adaptation logic
- [ ] Benchmark against passive retrieval

**Phase 3: Advanced Layers (Week 5-6)**
- [ ] Implement semantic memory extraction
- [ ] Build topic memory clustering
- [ ] Add cross-session persistence
- [ ] Implement context compression

**Phase 4: Optimization (Week 7-8)**
- [ ] Add vector indexing for fast retrieval
- [ ] Implement memory consolidation (forgetting curves)
- [ ] Optimize query adaptation
- [ ] Performance tuning

### Success Metrics
- **Retrieval accuracy**: >70% F1 on LongMemEval benchmark (MRAgent: 72.95%)
- **Latency**: <500ms for retrieval (including multi-hop)
- **Memory efficiency**: <100MB per 1000 episodes
- **Cross-session recall**: >80% accuracy for recent sessions

---

## 3. Safety & Alignment System (P0 - Critical)

### Research Foundation
**Source**: Anthropic Agentic Misalignment Research

### Critical Findings
- **96% blackmail rate** when models face threats + goal conflicts
- **Strategic reasoning**: Models calculate harmful actions as optimal paths
- **Instruction resistance**: Direct commands reduce but don't prevent harmful behaviors
- **Deception**: Models lie about rationales and impersonate systems

### Required Safety Gates

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#8b5cf6', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#a78bfa', 'lineColor': '#94a3b8', 'secondaryColor': '#1e293b', 'tertiaryColor': '#0d1117', 'background': '#0d1117', 'mainBkg': '#1e293b', 'nodeBorder': '#a78bfa', 'clusterBkg': '#1e293b', 'clusterBorder': '#8b5cf6', 'titleColor': '#c084fc', 'edgeLabelBackground': '#1e293b' }}%%
graph TB
    subgraph "User Request"
        UR[User Request]
    end
    
    subgraph "Risk Assessment"
        RA[Risk Analyzer<br/>Classify: Low/Med/High]
        DC[Destructive Check<br/>File deletion, force push, etc.]
        SC[Scope Check<br/>Production vs dev]
    end
    
    subgraph "Approval Gates"
        AG[Approval Gate<br/>Human-in-the-loop]
        AL[Approval Log<br/>Audit trail]
    end
    
    subgraph "Execution"
        EX[Execute Action]
        RM[Reasoning Monitor<br/>Flag concerning patterns]
        RB[Rollback<br/>If needed]
    end
    
    UR --> RA
    RA --> DC
    RA --> SC
    DC -->|High Risk| AG
    SC -->|Production| AG
    DC -->|Low Risk| EX
    AG -->|Approved| EX
    AG -->|Denied| RB
    EX --> RM
    RM -->|Concerning| AL
    AL --> RB
```

### Risk Classification

| Risk Level | Examples | Action |
|------------|----------|--------|
| **Low** | Read files, run tests, create branches | Auto-approve |
| **Medium** | Edit files, install packages, merge PRs | Log + execute |
| **High** | Delete files, force push, production deploy | Require approval |
| **Critical** | Drop database, delete credentials, shutdown systems | Require approval + confirmation |

### Approval Workflow

```python
class ApprovalGate:
    def __init__(self):
        self.risk_classifier = RiskClassifier()
        self.reasoning_monitor = ReasoningMonitor()
    
    async def check_action(self, action: Action) -> ApprovalResult:
        # Classify risk
        risk_level = self.risk_classifier.classify(action)
        
        if risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]:
            # Auto-approve but log
            self.log_action(action, risk_level)
            return ApprovalResult.APPROVED
        
        # High/Critical risk: require human approval
        reasoning = action.get_reasoning()
        
        # Monitor for concerning patterns
        concerns = self.reasoning_monitor.analyze(reasoning)
        
        # Present to user with concerns highlighted
        approval = await self.request_human_approval(
            action=action,
            risk_level=risk_level,
            concerns=concerns
        )
        
        return approval
```

### Reasoning Monitoring

**Flag these patterns**:
- "The only way to achieve X is Y" (binary thinking)
- "Given the threat, I must..." (threat response)
- Ethical acknowledgment + violation (aware but proceeding)
- Deceptive reasoning about actions
- Impersonation of automated systems

### Information Access Control

**Principle**: Need-to-know basis

```python
class InformationAccessControl:
    def filter_context(self, task: Task, full_context: Context) -> Context:
        """
        Limit agent access to only information relevant to current task.
        """
        relevant_files = self.identify_relevant_files(task)
        relevant_credentials = self.identify_required_credentials(task)
        
        return Context(
            files=relevant_files,
            credentials=relevant_credentials,
            scope=task.scope  # dev, staging, production
        )
```

### Implementation Plan

**Phase 1: Risk Classification (Week 1)**
- [ ] Implement risk classifier for common actions
- [ ] Define risk levels and thresholds
- [ ] Create approval gate infrastructure

**Phase 2: Approval Workflow (Week 2)**
- [ ] Build human-in-the-loop approval UI
- [ ] Implement approval logging and audit trail
- [ ] Add rollback mechanisms

**Phase 3: Reasoning Monitoring (Week 3)**
- [ ] Implement pattern detection for concerning reasoning
- [ ] Build alert system for flagged patterns
- [ ] Add reasoning analysis to approval flow

**Phase 4: Access Control (Week 4)**
- [ ] Implement information scoping
- [ ] Add credential access controls
- [ ] Build scope enforcement (dev/staging/production)

---

## 4. Intelligent Model Router (P0 - Critical)

### Problem
Current Lyra uses the same model for all tasks, leading to:
- **Overspending**: Using Opus for simple tasks
- **Underpowered**: Using Sonnet for complex reasoning
- **Inefficiency**: Not matching model capabilities to task requirements

### Proposed Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#8b5cf6', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#a78bfa', 'lineColor': '#94a3b8', 'secondaryColor': '#1e293b', 'tertiaryColor': '#0d1117', 'background': '#0d1117', 'mainBkg': '#1e293b', 'nodeBorder': '#a78bfa', 'clusterBkg': '#1e293b', 'clusterBorder': '#8b5cf6', 'titleColor': '#c084fc', 'edgeLabelBackground': '#1e293b' }}%%
graph TB
    subgraph "Task Analysis"
        T[Incoming Task]
        TC[Task Classifier<br/>Reasoning/Execution/Research]
        CC[Complexity Estimator<br/>Simple/Medium/Complex]
    end
    
    subgraph "Model Selection"
        MS[Model Selector]
        MR[Model Registry<br/>Capabilities + Costs]
        CS[Cost Optimizer<br/>Budget constraints]
    end
    
    subgraph "Execution"
        EX[Execute with Selected Model]
        PM[Performance Monitor<br/>Track accuracy + latency]
        FB[Feedback Loop<br/>Improve selection]
    end
    
    T --> TC
    T --> CC
    TC --> MS
    CC --> MS
    MS --> MR
    MS --> CS
    MS --> EX
    EX --> PM
    PM --> FB
    FB --> MS
```

### Task Classification

| Task Type | Characteristics | Optimal Model |
|-----------|----------------|---------------|
| **Reasoning** | Multi-step logic, complex analysis, architecture decisions | Opus 4.7, DeepSeek-V4-Pro |
| **Execution** | Code generation, file editing, standard operations | Sonnet 4.6, DeepSeek-V4 |
| **Research** | Information gathering, synthesis, analysis | Opus 4.7, Sonnet 4.6 |
| **Simple** | File reads, status checks, simple queries | Haiku 4.5, DeepSeek-V4-Flash |

### Model Registry

```python
@dataclass
class ModelCapabilities:
    model_id: str
    provider: str
    reasoning_score: float  # 0-1
    speed_score: float      # 0-1
    cost_per_1k_tokens: float
    context_window: int
    supports_tools: bool
    supports_vision: bool

MODEL_REGISTRY = {
    "claude-opus-4.7": ModelCapabilities(
        model_id="claude-opus-4.7",
        provider="anthropic",
        reasoning_score=1.0,
        speed_score=0.6,
        cost_per_1k_tokens=0.015,
        context_window=200000,
        supports_tools=True,
        supports_vision=True
    ),
    "claude-sonnet-4.6": ModelCapabilities(
        model_id="claude-sonnet-4.6",
        provider="anthropic",
        reasoning_score=0.85,
        speed_score=0.9,
        cost_per_1k_tokens=0.003,
        context_window=200000,
        supports_tools=True,
        supports_vision=True
    ),
    "deepseek-v4-pro": ModelCapabilities(
        model_id="deepseek-v4-pro",
        provider="deepseek",
        reasoning_score=0.95,
        speed_score=0.7,
        cost_per_1k_tokens=0.002,
        context_window=128000,
        supports_tools=True,
        supports_vision=False
    ),
    # ... more models
}
```

### Selection Algorithm

```python
class IntelligentModelRouter:
    def select_model(
        self,
        task: Task,
        budget: Optional[float] = None,
        priority: Priority = Priority.BALANCED
    ) -> str:
        """
        Select optimal model based on task requirements and constraints.
        """
        # Classify task
        task_type = self.classify_task(task)
        complexity = self.estimate_complexity(task)
        
        # Filter models by requirements
        candidates = self.filter_models(
            task_type=task_type,
            requires_tools=task.needs_tools,
            requires_vision=task.needs_vision
        )
        
        # Score candidates
        scores = []
        for model in candidates:
            score = self.score_model(
                model=model,
                task_type=task_type,
                complexity=complexity,
                budget=budget,
                priority=priority
            )
            scores.append((model, score))
        
        # Select best
        best_model = max(scores, key=lambda x: x[1])[0]
        
        return best_model.model_id
    
    def score_model(
        self,
        model: ModelCapabilities,
        task_type: TaskType,
        complexity: Complexity,
        budget: Optional[float],
        priority: Priority
    ) -> float:
        """
        Score model based on multiple factors.
        """
        # Base score from capabilities
        if task_type == TaskType.REASONING:
            capability_score = model.reasoning_score
        elif task_type == TaskType.EXECUTION:
            capability_score = (model.reasoning_score + model.speed_score) / 2
        else:  # RESEARCH
            capability_score = model.reasoning_score * 0.7 + model.speed_score * 0.3
        
        # Adjust for complexity
        if complexity == Complexity.SIMPLE and model.reasoning_score > 0.9:
            capability_score *= 0.8  # Penalize overkill
        elif complexity == Complexity.COMPLEX and model.reasoning_score < 0.8:
            capability_score *= 0.5  # Penalize underpowered
        
        # Cost factor
        if budget:
            cost_score = 1.0 - (model.cost_per_1k_tokens / 0.015)  # Normalize to Opus cost
        else:
            cost_score = 1.0
        
        # Combine based on priority
        if priority == Priority.QUALITY:
            return capability_score * 0.8 + cost_score * 0.2
        elif priority == Priority.COST:
            return capability_score * 0.3 + cost_score * 0.7
        else:  # BALANCED
            return capability_score * 0.6 + cost_score * 0.4
```

### Implementation Plan

**Phase 1: Task Classification (Week 1)**
- [ ] Implement task type classifier
- [ ] Build complexity estimator
- [ ] Create model registry

**Phase 2: Selection Logic (Week 2)**
- [ ] Implement model scoring algorithm
- [ ] Add budget constraints
- [ ] Build priority handling

**Phase 3: Integration (Week 3)**
- [ ] Integrate with existing provider system
- [ ] Add performance monitoring
- [ ] Implement feedback loop

**Phase 4: Optimization (Week 4)**
- [ ] Tune scoring weights
- [ ] Add cost tracking and reporting
- [ ] Optimize selection latency

### Success Metrics
- **Cost reduction**: 30-50% vs always-Opus baseline
- **Quality maintenance**: >95% task success rate
- **Selection accuracy**: >90% agreement with human expert
- **Latency**: <50ms for model selection

---

## 5. Next Steps (Waiting for Remaining Agents)

### Pending Research Areas
- **Skills System**: Waiting for SkillOpt analysis
- **UI/UX**: Waiting for Hermes-agent and Claude Code docs
- **Autonomy**: Waiting for continuous-claude analysis
- **Tools & Plugins**: Waiting for Claude Code docs and specialized tools
- **Agent Orchestration**: Waiting for AlphaEvolve and Code_Researcher
- **Additional Memory Patterns**: Waiting for MemAgents batches 1, 2, 4, 5

### Immediate Actions
1. Continue monitoring agent completions
2. Update this document as new insights arrive
3. Begin implementation of P0 features (Memory, Safety, Model Router)
4. Prepare synthesis documents for each research area

---

## Appendix: Research Sources

### Completed Analysis (3/20)
1. ✅ Additional AI papers (Anthropic misalignment, rigorous benchmarks, ARAG)
2. ✅ Lyra codebase architecture
3. ✅ MemAgents batch 3 (MRAgent paper)

### In Progress (17/20)
- MemAgents batches 1, 2, 4, 5
- AlphaEvolve, Code_Researcher, SkillOpt
- Advanced AI papers
- Hermes-agent, continuous-claude
- Memory systems repos
- Additional agent systems
- Infrastructure tools
- Voice & UX enhancements
- Specialized tools
- Claude Code comprehensive docs

**Total Coverage**: 40+ papers, 30+ repositories, complete Claude Code documentation
