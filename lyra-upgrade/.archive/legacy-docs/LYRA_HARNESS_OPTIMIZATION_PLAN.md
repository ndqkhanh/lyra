# Lyra Harness Optimization Plan
## Building the Operational AI Layer

**Goal:** Transform Lyra from a capable AI assistant into a fully operational AI harness that executes workflows, not just answers questions.

**Research Grounding:** 
- Article: "Most people think AI is about prompts. It's actually about the harness around the model."
- Existing Plans: Evolution (322-326), Context Optimization, Process Transparency, Deep Research
- Key Insight: The model is the CPU; the harness is the operating system

**Date:** 2026-05-17
**Status:** Master Plan — Builds on Existing Plans

---

## Executive Summary

The article identifies 6 layers that transform AI from "impressive" to "operational":

```
Layer 6: APIs & Agents        → Workflow execution (transformational)
Layer 5: MCP Integration      → Universal connectivity (enterprise-ready)
Layer 4: Tools & Plugins      → Action capability (doing vs thinking)
Layer 3: Skills               → Reusable playbooks (operational)
Layer 2: Context              → Relevance (productivity gains)
Layer 1: Prompts              → Conversation (starting point)
```

**Current Lyra State:**
- ✅ Strong Layer 1-2: Prompts, Context (Context Optimization Plan)
- ✅ Strong Layer 3: Skills (Research Skills, Evolution Skills)
- ✅ Strong Layer 4: Tools (60+ tools, 12 hooks)
- ⚠️ Partial Layer 5: MCP (14 servers, but not deeply integrated)
- ⚠️ Partial Layer 6: Agents (60 agents, but workflow orchestration gaps)

**This Plan Addresses:**
1. **Context as Operating System** — organizational memory, not just session memory
2. **Skills as Business Logic** — domain playbooks that reflect operational models
3. **MCP as Integration Fabric** — universal connectivity across systems
4. **Workflow Orchestration** — multi-step, multi-agent, multi-system execution
5. **Operational Intelligence** — learning from execution, not just research

---

## Phase 0: Current State Analysis

### What Lyra Already Has (Strong Foundation)

| Layer | Component | Status | File/Module |
|-------|-----------|--------|-------------|
| Context | Memory System | ✅ Strong | lyra-memory/* |
| Context | Session Persistence | ✅ Strong | lyra-core/context/* |
| Context | NGC Compaction | ✅ Strong | Context Optimization Plan |
| Skills | Research Skills | ✅ Strong | Deep Research Plan Phase 5 |
| Skills | Evolution Skills | ✅ Strong | Evolution Plan Phase E |
| Tools | 60+ Tools | ✅ Strong | lyra-cli/commands/* |
| Tools | 12 Hooks | ✅ Strong | lyra-core/hooks/* |
| MCP | 14 Servers | ⚠️ Partial | lyra-mcp/* |
| Agents | 60 Agents | ✅ Strong | Evolution Plan |
| Agents | Fleet View | 🔄 Planned | Evolution Plan Phase D |
| Workflow | Research Pipeline | ✅ Strong | Deep Research Plan |
| Workflow | Self-Modification | 🔄 Planned | Evolution Plan Phase E |

### Critical Gaps (Article Framework vs Lyra)

| Gap | Article Insight | Current Lyra State | Impact |
|-----|-----------------|-------------------|--------|
| **Organizational Context** | "Context is where relevance happens" | Session-scoped only | Each session starts cold |
| **Domain Playbooks** | "Skills reflect operating models" | Research-focused only | No business domain skills |
| **MCP Integration Depth** | "Universal connector standard" | 14 servers, shallow integration | Manual tool selection |
| **Workflow Templates** | "AI executing workflows" | Research pipeline only | One-off tasks, no reuse |
| **Cross-Agent Learning** | "Compounding intelligence" | Per-agent learning only | Agents don't share lessons |
| **Execution Memory** | "What worked, what failed" | Research memory only | No operational memory |
| **Tool Orchestration** | "Coordinating across platforms" | Independent tools | No tool chains |
| **Permission Intelligence** | "Context-aware gates" | Static rules | No learning from decisions |

---

## Phase 1: Organizational Context Layer (Weeks 1-3)
**Goal:** Transform context from session memory to organizational operating system

**Article Quote:** "The output quality changes dramatically once the AI consistently understands: who you are, how you work, what your priorities are, and what 'good output' looks like in your environment."

### 1.1 User Profile & Work Patterns

**New Module:** `packages/lyra-memory/src/lyra_memory/user_profile.py`

**What to Build:**

```python
@dataclass
class UserProfile:
    """Persistent user identity and work patterns."""
    
    # Identity
    user_id: str
    role: str                    # "ML Engineer", "Researcher", "PM"
    domains: List[str]           # ["NLP", "distributed systems"]
    expertise_level: Dict[str, str]  # {"Python": "expert", "Rust": "beginner"}
    
    # Work Patterns
    preferred_tools: List[str]   # tools user reaches for most
    work_hours: TimeWindow       # when user is typically active
    session_patterns: Dict       # typical session length, frequency
    
    # Preferences
    communication_style: str     # "concise", "detailed", "technical"
    output_format: str           # "markdown", "code-first", "visual"
    verification_level: str      # "paranoid", "balanced", "trusting"
    
    # Context
    current_projects: List[Project]
    active_goals: List[Goal]
    recent_decisions: List[Decision]
```

**UserProfileBuilder** — learns from session history:
- Extracts role from conversation patterns
- Infers domains from research topics and code
- Tracks tool usage frequency
- Detects communication preferences

**ProfileMemoryBridge** — injects profile into every session:
- Loads user profile at session start
- Updates context with relevant profile sections
- Adapts agent behavior to user preferences

### 1.2 Project Context Memory

**New Module:** `packages/lyra-memory/src/lyra_memory/project_context.py`

**What to Build:**

```python
@dataclass
class ProjectContext:
    """Persistent project-level context."""
    
    project_id: str
    project_name: str
    project_type: str            # "research", "engineering", "analysis"
    
    # Architecture
    tech_stack: List[str]
    architecture_decisions: List[Decision]
    coding_conventions: List[Convention]
    
    # State
    current_phase: str
    active_tasks: List[Task]
    blockers: List[Blocker]
    
    # Knowledge
    key_files: List[str]         # most important files
    key_concepts: List[Concept]  # domain concepts
    external_deps: List[Dependency]
    
    # History
    major_milestones: List[Milestone]
    lessons_learned: List[Lesson]
```

**ProjectContextDetector** — auto-detects project from working directory:
- Scans for project markers (package.json, pyproject.toml, etc.)
- Loads existing project context or creates new
- Updates context as project evolves

**ProjectMemoryPersistence** — survives across sessions:
- Stores in `.lyra/project_context.json`
- Version-controlled alongside code
- Shareable across team members

### 1.3 Organizational Memory

**New Module:** `packages/lyra-memory/src/lyra_memory/org_memory.py`

**What to Build:**

```python
@dataclass
class OrganizationalMemory:
    """Company/team-level context and conventions."""
    
    # Standards
    coding_standards: Dict[str, Standard]
    review_checklist: List[CheckItem]
    deployment_procedures: List[Procedure]
    
    # Knowledge
    internal_tools: List[Tool]
    internal_apis: List[API]
    team_conventions: List[Convention]
    
    # Contacts
    subject_matter_experts: Dict[str, List[Person]]
    escalation_paths: Dict[str, Path]
```

**Success Criteria:**
- Second session in same project loads context in <2s
- User profile adapts after 5 sessions (measurable preference detection)
- Project context includes ≥10 architecture decisions after 10 sessions
- Zero "explain this again" moments for established conventions

---

## Phase 2: Domain Skills Library (Weeks 3-5)
**Goal:** Skills that reflect operational models, not just research

**Article Quote:** "At this stage, AI begins reflecting organizational operating models instead of just generating text creatively."

### 2.1 Business Domain Skills

**New Module:** `packages/lyra-skills/src/lyra_skills/domains/`

**Domain Skill Categories:**

```
domains/
├── engineering/
│   ├── code_review.skill          → PR review with team standards
│   ├── architecture_decision.skill → ADR generation
│   ├── incident_response.skill    → on-call playbook
│   ├── deployment_checklist.skill → pre-deploy verification
│   └── technical_debt_audit.skill → debt identification
│
├── product/
│   ├── feature_spec.skill         → PRD generation
│   ├── user_story.skill           → story writing
│   ├── roadmap_planning.skill     → quarterly planning
│   └── stakeholder_update.skill   → status reporting
│
├── data_science/
│   ├── experiment_design.skill    → A/B test design
│   ├── model_evaluation.skill     → model quality assessment
│   ├── data_quality_audit.skill   → data validation
│   └── metric_definition.skill    → metric specification
│
├── operations/
│   ├── runbook_generation.skill   → operational procedures
│   ├── postmortem.skill           → incident analysis
│   ├── capacity_planning.skill    → resource forecasting
│   └── sla_monitoring.skill       → SLA tracking
│
└── compliance/
    ├── security_review.skill      → security checklist
    ├── privacy_audit.skill        → GDPR/privacy check
    ├── license_compliance.skill   → OSS license audit
    └── audit_trail.skill          → compliance documentation
```

### 2.2 Skill Composition Engine

**New Module:** `packages/lyra-skills/src/lyra_skills/composition.py`

**What to Build:**

```python
class SkillComposer:
    """Compose complex workflows from atomic skills."""
    
    def compose(self, skills: List[Skill], strategy: str) -> CompositeSkill:
        """
        Strategies:
        - SEQUENTIAL: skill1 → skill2 → skill3
        - PARALLEL: skill1 || skill2 || skill3
        - CONDITIONAL: if skill1.result.success then skill2 else skill3
        - LOOP: while condition: skill
        """
        ...
    
    def validate_composition(self, composite: CompositeSkill) -> ValidationResult:
        """Check input/output type compatibility."""
        ...
```

**Example Composite Skill:**

```yaml
name: "full_feature_implementation"
description: "End-to-end feature delivery"
composition:
  - skill: feature_spec.skill
    output: spec
  - skill: architecture_decision.skill
    input: spec
    output: architecture
  - skill: code_implementation.skill
    input: [spec, architecture]
    output: code
  - skill: code_review.skill
    input: code
    output: review
  - skill: deployment_checklist.skill
    input: [code, review]
    output: deployment_plan
```

### 2.3 Skill Performance Analytics

**New Module:** `packages/lyra-skills/src/lyra_skills/analytics.py`

**What to Build:**

```python
@dataclass
class SkillMetrics:
    skill_id: str
    invocation_count: int
    success_rate: float
    avg_duration_ms: float
    avg_quality_score: float
    user_satisfaction: float
    last_used: datetime
    
    # Performance by context
    performance_by_domain: Dict[str, float]
    performance_by_user: Dict[str, float]
```

**SkillRecommender** — suggests skills based on context:
- Analyzes current task
- Matches to skill library
- Ranks by relevance × past performance
- Suggests skill compositions

**Success Criteria:**
- ≥20 domain skills across 5 categories
- Skill composition creates ≥5 end-to-end workflows
- Skill recommender suggests correct skill 80%+ of time
- Skill performance tracked for all invocations

---

## Phase 3: MCP Integration Fabric (Weeks 5-7)
**Goal:** Universal connectivity across systems via MCP

**Article Quote:** "MCP acts more like a universal connector standard — almost like USB-C for AI ecosystems."

### 3.1 MCP Server Registry

**New Module:** `packages/lyra-mcp/src/lyra_mcp/registry.py`

**What to Build:**

```python
@dataclass
class MCPServerCapability:
    server_id: str
    server_name: str
    capabilities: List[str]      # ["read_files", "search", "execute"]
    resources: List[Resource]    # what it can access
    tools: List[Tool]            # what actions it provides
    prompts: List[Prompt]        # what templates it offers
    
    # Metadata
    reliability_score: float
    avg_latency_ms: float
    cost_per_call: float
    auth_required: bool

class MCPRegistry:
    """Central registry of all MCP servers."""
    
    def discover_servers(self) -> List[MCPServerCapability]:
        """Auto-discover available MCP servers."""
        ...
    
    def find_server_for_task(self, task: str) -> List[MCPServerCapability]:
        """Find best MCP server(s) for a task."""
        ...
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all registered servers."""
        ...
```

### 3.2 MCP Capability Discovery

**New Module:** `packages/lyra-mcp/src/lyra_mcp/discovery.py`

**What to Build:**

**MCPCapabilityMatcher** — intelligent routing to MCP servers:
- Analyzes user intent
- Maps to MCP server capabilities
- Selects optimal server(s)
- Handles fallbacks

**Example:**
```
User: "Search my Notion workspace for project plans"
→ MCPCapabilityMatcher detects: search + Notion
→ Routes to: notion-mcp-server
→ Fallback: If Notion unavailable, suggest alternatives
```

### 3.3 MCP Integration Patterns

**New Module:** `packages/lyra-mcp/src/lyra_mcp/patterns.py`

**Integration Patterns:**

```python
class MCPIntegrationPatterns:
    """Common MCP integration patterns."""
    
    def read_transform_write(self, source_mcp: str, dest_mcp: str):
        """Read from one system, transform, write to another."""
        # Example: Read from GitHub → Transform → Write to Notion
        ...
    
    def aggregate_search(self, mcp_servers: List[str], query: str):
        """Search across multiple MCP servers, aggregate results."""
        # Example: Search GitHub + Notion + Slack simultaneously
        ...
    
    def sync_bidirectional(self, mcp_a: str, mcp_b: str):
        """Keep two systems in sync via MCP."""
        # Example: Sync Linear issues ↔ GitHub issues
        ...
    
    def event_driven_workflow(self, trigger_mcp: str, action_mcps: List[str]):
        """Trigger workflow when event occurs in one system."""
        # Example: GitHub PR merged → Update Notion → Post to Slack
        ...
```

### 3.4 MCP Performance Monitoring

**New Module:** `packages/lyra-mcp/src/lyra_mcp/monitoring.py`

**What to Build:**

```python
@dataclass
class MCPCallMetrics:
    server_id: str
    call_timestamp: datetime
    latency_ms: float
    success: bool
    error: Optional[str]
    tokens_used: int
    cost_usd: float

class MCPMonitor:
    """Monitor MCP server performance."""
    
    def track_call(self, metrics: MCPCallMetrics):
        """Record MCP call metrics."""
        ...
    
    def get_server_health(self, server_id: str) -> HealthStatus:
        """Get server health: latency, success rate, uptime."""
        ...
    
    def recommend_server(self, capability: str) -> str:
        """Recommend best server based on performance history."""
        ...
```

**Success Criteria:**
- MCP registry auto-discovers all 14+ servers
- Capability matcher routes correctly 90%+ of time
- ≥3 integration patterns implemented and tested
- MCP performance tracked for all calls
- Server health visible in `/mcp status` command

---

## Phase 4: Workflow Orchestration Engine (Weeks 7-10)
**Goal:** Multi-step, multi-agent, multi-system workflow execution

**Article Quote:** "Once AI can access systems, retrieve data, trigger actions, orchestrate workflows, and coordinate across platforms, it starts behaving less like a chatbot and more like an operational layer sitting across the business."

### 4.1 Workflow Definition Language

**New Module:** `packages/lyra-core/src/lyra_core/workflows/definition.py`

**What to Build:**

```yaml
# Example: Feature Implementation Workflow
workflow:
  name: "feature_implementation"
  description: "End-to-end feature delivery"
  
  inputs:
    - feature_description: string
    - priority: enum[high, medium, low]
  
  steps:
    - id: "clarify"
      agent: "planner"
      skill: "feature_spec.skill"
      input: ${feature_description}
      output: spec
      
    - id: "design"
      agent: "architect"
      skill: "architecture_decision.skill"
      input: ${spec}
      output: architecture
      depends_on: ["clarify"]
      
    - id: "implement"
      agent: "executor"
      skill: "code_implementation.skill"
      input: [${spec}, ${architecture}]
      output: code
      depends_on: ["design"]
      parallel: true  # Can run multiple files in parallel
      
    - id: "review"
      agent: "code-reviewer"
      skill: "code_review.skill"
      input: ${code}
      output: review
      depends_on: ["implement"]
      
    - id: "test"
      agent: "tdd-guide"
      skill: "test_generation.skill"
      input: ${code}
      output: tests
      depends_on: ["implement"]
      parallel_with: ["review"]
      
    - id: "deploy_check"
      agent: "verifier"
      skill: "deployment_checklist.skill"
      input: [${code}, ${review}, ${tests}]
      output: deployment_plan
      depends_on: ["review", "test"]
      
  outputs:
    - deployment_plan
    - code
    - tests
  
  error_handling:
    - on_failure: "review"
      action: "retry_with_feedback"
      max_retries: 2
```

### 4.2 Workflow Execution Engine

**New Module:** `packages/lyra-core/src/lyra_core/workflows/executor.py`

**What to Build:**

```python
class WorkflowExecutor:
    """Execute multi-step workflows with dependency management."""
    
    def execute(self, workflow: Workflow, inputs: Dict) -> WorkflowResult:
        """
        Execute workflow:
        1. Build execution DAG from dependencies
        2. Execute steps in topological order
        3. Handle parallel execution
        4. Manage state across steps
        5. Handle errors and retries
        """
        ...
    
    def pause_for_approval(self, step_id: str, context: Dict):
        """Pause workflow for human approval."""
        ...
    
    def resume(self, workflow_id: str, approval: bool):
        """Resume paused workflow."""
        ...
    
    def rollback(self, workflow_id: str, to_step: str):
        """Rollback workflow to previous step."""
        ...
```

### 4.3 Workflow Template Library

**New Module:** `packages/lyra-core/src/lyra_core/workflows/templates/`

**Workflow Templates:**

```
templates/
├── engineering/
│   ├── feature_implementation.yaml
│   ├── bug_fix.yaml
│   ├── refactoring.yaml
│   ├── code_review.yaml
│   └── deployment.yaml
│
├── research/
│   ├── literature_review.yaml
│   ├── experiment_design.yaml
│   ├── paper_writing.yaml
│   └── benchmark_analysis.yaml
│
├── data/
│   ├── data_pipeline.yaml
│   ├── model_training.yaml
│   ├── model_evaluation.yaml
│   └── data_quality_audit.yaml
│
└── operations/
    ├── incident_response.yaml
    ├── capacity_planning.yaml
    ├── security_audit.yaml
    └── compliance_check.yaml
```

### 4.4 Workflow State Management

**New Module:** `packages/lyra-core/src/lyra_core/workflows/state.py`

**What to Build:**

```python
@dataclass
class WorkflowState:
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus  # RUNNING, PAUSED, COMPLETED, FAILED
    
    # Execution
    current_step: str
    completed_steps: List[str]
    failed_steps: List[str]
    
    # Data
    inputs: Dict
    step_outputs: Dict[str, Any]
    final_outputs: Dict
    
    # Metadata
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # Resources
    agents_used: List[str]
    tools_used: List[str]
    mcp_servers_used: List[str]
    
    # Cost
    total_cost_usd: float
    total_tokens: int
    total_duration_ms: int

class WorkflowStateManager:
    """Manage workflow state persistence and recovery."""
    
    def save_checkpoint(self, state: WorkflowState):
        """Save workflow state for recovery."""
        ...
    
    def restore(self, workflow_id: str) -> WorkflowState:
        """Restore workflow from checkpoint."""
        ...
    
    def list_active_workflows(self) -> List[WorkflowState]:
        """List all active workflows."""
        ...
```

**Success Criteria:**
- ≥10 workflow templates across 4 categories
- Workflow executor handles parallel steps correctly
- Workflow state persists across Lyra restarts
- Human approval gates work correctly
- Rollback restores to previous step successfully

---

## Phase 5: Operational Intelligence (Weeks 10-13)
**Goal:** Learn from execution, not just research

**Article Quote:** "The future belongs to those who learn how to build the harness around the model."

### 5.1 Execution Memory System

**New Module:** `packages/lyra-memory/src/lyra_memory/execution_memory.py`

**What to Build:**

```python
@dataclass
class ExecutionRecord:
    """Record of a workflow/task execution."""
    
    execution_id: str
    execution_type: str          # "workflow", "skill", "tool", "agent"
    
    # Context
    user_intent: str
    domain: str
    project_context: str
    
    # Execution
    steps_taken: List[Step]
    decisions_made: List[Decision]
    tools_used: List[str]
    agents_involved: List[str]
    
    # Outcome
    success: bool
    quality_score: float
    user_satisfaction: float
    
    # Learning
    what_worked: List[str]
    what_failed: List[str]
    lessons_learned: List[Lesson]
    
    # Metadata
    duration_ms: int
    cost_usd: float
    timestamp: datetime

class ExecutionMemoryStore:
    """Store and retrieve execution patterns."""
    
    def record_execution(self, record: ExecutionRecord):
        """Save execution record."""
        ...
    
    def find_similar_executions(self, intent: str, domain: str) -> List[ExecutionRecord]:
        """Find similar past executions."""
        ...
    
    def extract_patterns(self, domain: str) -> List[Pattern]:
        """Extract successful patterns from execution history."""
        ...
```

### 5.2 Tool Chain Learning

**New Module:** `packages/lyra-core/src/lyra_core/tools/chain_learning.py`

**What to Build:**

```python
@dataclass
class ToolChain:
    """Sequence of tools that work well together."""
    
    chain_id: str
    tools: List[str]             # Ordered sequence
    success_rate: float
    avg_duration_ms: float
    use_count: int
    
    # Context
    typical_intent: str
    typical_domain: str
    
    # Performance
    performance_by_context: Dict[str, float]

class ToolChainLearner:
    """Learn effective tool sequences from execution history."""
    
    def discover_chains(self, min_frequency: int = 3) -> List[ToolChain]:
        """Discover frequently used tool sequences."""
        ...
    
    def recommend_next_tool(self, current_tools: List[str], intent: str) -> List[str]:
        """Recommend next tool based on successful chains."""
        ...
    
    def optimize_chain(self, chain: ToolChain) -> ToolChain:
        """Suggest optimizations for a tool chain."""
        ...
```

### 5.3 Permission Intelligence

**New Module:** `packages/lyra-core/src/lyra_core/permissions/intelligence.py`

**What to Build:**

```python
@dataclass
class PermissionDecisionRecord:
    """Record of a permission decision."""
    
    tool_name: str
    action: str
    context: Dict
    
    # Decision
    decision: str                # "allow", "deny", "ask"
    reason: str
    user_override: Optional[bool]
    
    # Outcome
    was_safe: bool
    user_regretted: bool
    
    timestamp: datetime

class PermissionLearner:
    """Learn from permission decisions to improve future gates."""
    
    def record_decision(self, record: PermissionDecisionRecord):
        """Record permission decision and outcome."""
        ...
    
    def suggest_permission_level(self, tool: str, context: Dict) -> str:
        """Suggest permission level based on history."""
        ...
    
    def detect_safe_patterns(self) -> List[Pattern]:
        """Identify consistently safe tool usage patterns."""
        ...
    
    def detect_risky_patterns(self) -> List[Pattern]:
        """Identify patterns that led to user regret."""
        ...
```

### 5.4 Cross-Agent Learning

**New Module:** `packages/lyra-core/src/lyra_core/agents/cross_learning.py`

**What to Build:**

```python
class AgentKnowledgeSharing:
    """Enable agents to learn from each other's experiences."""
    
    def share_lesson(self, agent_id: str, lesson: Lesson):
        """Agent shares a lesson with the collective."""
        ...
    
    def query_collective_knowledge(self, query: str, domain: str) -> List[Lesson]:
        """Query lessons learned by any agent."""
        ...
    
    def synthesize_best_practices(self, domain: str) -> List[BestPractice]:
        """Synthesize best practices from all agent experiences."""
        ...

@dataclass
class CollectiveLearning:
    """Shared learning across all agents."""
    
    # Patterns
    successful_patterns: Dict[str, List[Pattern]]
    failed_patterns: Dict[str, List[Pattern]]
    
    # Best Practices
    best_practices: Dict[str, List[BestPractice]]
    
    # Warnings
    known_pitfalls: Dict[str, List[Pitfall]]
    
    # Performance
    agent_specializations: Dict[str, List[str]]  # Which agents excel at what
```

**Success Criteria:**
- Execution memory records ≥100 executions after 20 sessions
- Tool chain learner discovers ≥5 effective chains
- Permission learner reduces "ask" rate by 30% after 50 decisions
- Cross-agent learning shares ≥10 lessons across agents
- Collective best practices improve task success rate by 15%

---

## Phase 6: Integration & Orchestration Layer (Weeks 13-16)
**Goal:** Tie all layers together into cohesive operational system

### 6.1 Unified Harness Controller

**New Module:** `packages/lyra-core/src/lyra_core/harness/controller.py`

**What to Build:**

```python
class LyraHarnessController:
    """Central controller for the entire Lyra harness."""
    
    def __init__(self):
        self.user_profile = UserProfileManager()
        self.project_context = ProjectContextManager()
        self.skill_library = SkillLibrary()
        self.mcp_registry = MCPRegistry()
        self.workflow_executor = WorkflowExecutor()
        self.execution_memory = ExecutionMemoryStore()
        self.agent_fleet = AgentFleetManager()
    
    def process_intent(self, user_intent: str) -> ExecutionPlan:
        """
        Process user intent through the full harness:
        1. Load user profile + project context
        2. Classify intent (research, coding, workflow, etc.)
        3. Select appropriate skills/workflows
        4. Route to MCP servers if needed
        5. Orchestrate agents
        6. Execute with monitoring
        7. Learn from execution
        """
        ...
    
    def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute the plan with full harness support."""
        ...
    
    def learn_from_execution(self, result: ExecutionResult):
        """Update all learning systems from execution."""
        ...
```

### 6.2 Harness Telemetry Dashboard

**New Module:** `packages/lyra-cli/src/lyra_cli/commands/harness.py`

**What to Build:**

**`/harness status`** — Overall harness health:
```
┌─ Lyra Harness Status ─────────────────────────────────────┐
│ Context Layer                                              │
│   User Profile:        ✓ Loaded (ML Engineer, 5 domains)  │
│   Project Context:     ✓ Active (lyra-research)           │
│   Org Memory:          ✓ 47 conventions loaded            │
│                                                            │
│ Skills Layer                                               │
│   Skills Loaded:       ✓ 42 skills (5 domains)            │
│   Compositions:        ✓ 8 workflows                      │
│   Performance:         ✓ 87% avg success rate             │
│                                                            │
│ MCP Layer                                                  │
│   Servers Active:      ✓ 14/14 healthy                    │
│   Avg Latency:         ✓ 234ms                            │
│   Integration Patterns: ✓ 3 active                        │
│                                                            │
│ Workflow Layer                                             │
│   Active Workflows:    2 running, 5 completed today       │
│   Success Rate:        ✓ 92%                              │
│   Avg Duration:        4.2 minutes                        │
│                                                            │
│ Intelligence Layer                                         │
│   Execution Records:   247 total                          │
│   Tool Chains:         12 discovered                      │
│   Lessons Learned:     34 shared across agents            │
│   Permission Accuracy: ✓ 94%                              │
└────────────────────────────────────────────────────────────┘
```

**`/harness optimize`** — Optimization recommendations:
- Suggests underutilized skills
- Identifies slow MCP servers
- Recommends workflow improvements
- Highlights learning opportunities

### 6.3 Harness Configuration

**New Module:** `packages/lyra-core/src/lyra_core/harness/config.py`

**What to Build:**

```yaml
# .lyra/harness_config.yaml
harness:
  # Context Layer
  context:
    user_profile_enabled: true
    project_context_enabled: true
    org_memory_enabled: true
    context_refresh_interval: 300  # seconds
  
  # Skills Layer
  skills:
    auto_recommend: true
    composition_enabled: true
    performance_tracking: true
    min_quality_threshold: 0.75
  
  # MCP Layer
  mcp:
    auto_discovery: true
    health_check_interval: 60
    capability_matching: "intelligent"  # or "manual"
    integration_patterns_enabled: true
  
  # Workflow Layer
  workflows:
    parallel_execution: true
    max_parallel_steps: 5
    approval_gates_enabled: true
    state_persistence: true
  
  # Intelligence Layer
  intelligence:
    execution_memory_enabled: true
    tool_chain_learning: true
    permission_learning: true
    cross_agent_learning: true
    min_confidence_threshold: 0.80
```

**Success Criteria:**
- Harness controller processes intent end-to-end
- Telemetry dashboard shows all layer health
- Configuration changes take effect without restart
- All layers communicate through unified interfaces

---

## Phase 7: Evaluation & Continuous Improvement (Weeks 16-18)
**Goal:** Measure harness effectiveness and improve continuously

### 7.1 Harness Effectiveness Metrics

**New Module:** `packages/lyra-evals/src/lyra_evals/harness_metrics.py`

**What to Build:**

```python
@dataclass
class HarnessMetrics:
    """Comprehensive harness effectiveness metrics."""
    
    # Context Layer
    context_hit_rate: float          # How often context was relevant
    context_load_time_ms: float
    context_accuracy: float          # User corrections needed
    
    # Skills Layer
    skill_recommendation_accuracy: float
    skill_success_rate: float
    skill_composition_success: float
    
    # MCP Layer
    mcp_routing_accuracy: float
    mcp_avg_latency_ms: float
    mcp_success_rate: float
    
    # Workflow Layer
    workflow_completion_rate: float
    workflow_avg_duration_ms: float
    workflow_user_satisfaction: float
    
    # Intelligence Layer
    learning_improvement_rate: float  # How much better over time
    pattern_discovery_rate: float
    cross_agent_knowledge_reuse: float
    
    # Overall
    task_success_rate: float
    user_productivity_gain: float    # vs baseline without harness
    cost_efficiency: float           # value delivered per dollar

class HarnessEvaluator:
    """Evaluate harness effectiveness."""
    
    def compute_metrics(self, period: str = "week") -> HarnessMetrics:
        """Compute metrics for a time period."""
        ...
    
    def compare_to_baseline(self) -> ComparisonReport:
        """Compare current performance to baseline (no harness)."""
        ...
    
    def identify_bottlenecks(self) -> List[Bottleneck]:
        """Identify performance bottlenecks in the harness."""
        ...
    
    def recommend_improvements(self) -> List[Improvement]:
        """Recommend specific improvements based on metrics."""
        ...
```

### 7.2 A/B Testing Framework

**New Module:** `packages/lyra-evals/src/lyra_evals/ab_testing.py`

**What to Build:**

```python
class HarnessABTest:
    """A/B test harness improvements."""
    
    def create_experiment(self, 
                         name: str,
                         control: HarnessConfig,
                         treatment: HarnessConfig,
                         metric: str) -> Experiment:
        """Create A/B test experiment."""
        ...
    
    def run_experiment(self, experiment: Experiment, n_trials: int) -> ExperimentResult:
        """Run experiment with statistical significance testing."""
        ...
    
    def analyze_results(self, result: ExperimentResult) -> Analysis:
        """Analyze experiment results with confidence intervals."""
        ...
```

### 7.3 Continuous Improvement Loop

**New Module:** `packages/lyra-core/src/lyra_core/harness/improvement.py`

**What to Build:**

```python
class ContinuousImprovementEngine:
    """Automatically improve harness based on metrics."""
    
    def analyze_performance(self) -> PerformanceReport:
        """Analyze current harness performance."""
        ...
    
    def propose_improvements(self) -> List[Improvement]:
        """Propose specific improvements with expected impact."""
        ...
    
    def test_improvement(self, improvement: Improvement) -> TestResult:
        """Test improvement in sandbox before applying."""
        ...
    
    def apply_improvement(self, improvement: Improvement):
        """Apply improvement if test successful."""
        ...
    
    def rollback_if_regression(self, improvement: Improvement):
        """Rollback if improvement causes regression."""
        ...
```

**Success Criteria:**
- All harness metrics computed automatically
- Baseline comparison shows ≥30% productivity gain
- A/B testing framework validates ≥3 improvements
- Continuous improvement proposes ≥1 improvement per week
- Zero regressions from automatic improvements

---

## Implementation Timeline (18 Weeks)

```
Weeks 1-3    Phase 1: Organizational Context Layer
             - User profile & work patterns
             - Project context memory
             - Organizational memory

Weeks 3-5    Phase 2: Domain Skills Library
             - Business domain skills (20+ skills)
             - Skill composition engine
             - Skill performance analytics

Weeks 5-7    Phase 3: MCP Integration Fabric
             - MCP server registry
             - Capability discovery & routing
             - Integration patterns
             - Performance monitoring

Weeks 7-10   Phase 4: Workflow Orchestration Engine
             - Workflow definition language
             - Workflow executor with DAG
             - Workflow template library (10+ templates)
             - State management & recovery

Weeks 10-13  Phase 5: Operational Intelligence
             - Execution memory system
             - Tool chain learning
             - Permission intelligence
             - Cross-agent learning

Weeks 13-16  Phase 6: Integration & Orchestration
             - Unified harness controller
             - Telemetry dashboard
             - Configuration system

Weeks 16-18  Phase 7: Evaluation & Improvement
             - Harness effectiveness metrics
             - A/B testing framework
             - Continuous improvement loop
```

---

## Integration with Existing Plans

This plan **complements and extends** existing plans:

| Existing Plan | Relationship | Integration Points |
|---------------|--------------|-------------------|
| **Evolution Plan (322-326)** | Provides agent infrastructure | Phase 6 uses Agent Fleet (Phase D), Phase 5 uses AER (Phase A) |
| **Context Optimization** | Provides context foundation | Phase 1 builds on context system, adds organizational layer |
| **Process Transparency** | Provides observability | Phase 6 telemetry uses EventBus, Phase 7 uses metrics |
| **Deep Research** | Provides research capability | Phase 2 skills include research skills, Phase 4 workflows include research workflows |

**Key Differences:**
- Existing plans focus on **research and self-evolution**
- This plan focuses on **operational execution and business workflows**
- Together they create a complete AI harness: research + operations

---

## Success Metrics (Overall)

### Short-term (After Phase 3)
- [ ] User profile adapts after 5 sessions
- [ ] ≥20 domain skills across 5 categories
- [ ] MCP routing accuracy ≥90%
- [ ] Context hit rate ≥80%

### Medium-term (After Phase 5)
- [ ] ≥10 workflow templates operational
- [ ] Tool chain learner discovers ≥5 effective chains
- [ ] Cross-agent learning shares ≥10 lessons
- [ ] Workflow success rate ≥85%

### Long-term (After Phase 7)
- [ ] User productivity gain ≥30% vs baseline
- [ ] Task success rate ≥90%
- [ ] Cost efficiency improves by ≥20%
- [ ] Continuous improvement proposes ≥1 improvement/week
- [ ] Zero regressions from automatic improvements

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Context layer too slow | Medium | High | Cache aggressively, lazy load, profile performance |
| Skill composition complexity | High | Medium | Start simple (sequential only), add complexity gradually |
| MCP server instability | Medium | Medium | Health checks, circuit breakers, graceful degradation |
| Workflow state corruption | Low | Critical | Atomic checkpoints, validation, rollback capability |
| Learning system drift | Medium | High | Quality gates on all updates, A/B testing, rollback |
| Integration complexity | High | High | Phased rollout, feature flags, extensive testing |

---

## Relationship to Article Framework

| Article Layer | Lyra Implementation | Plan Phase |
|---------------|-------------------|------------|
| **Layer 1: Prompts** | ✅ Already strong | N/A |
| **Layer 2: Context** | ✅ Enhanced | Phase 1 |
| **Layer 3: Skills** | ✅ Expanded | Phase 2 |
| **Layer 4: Tools & Plugins** | ✅ Already strong | N/A |
| **Layer 5: MCP** | ⚠️ Deepened | Phase 3 |
| **Layer 6: APIs & Agents** | ⚠️ Orchestrated | Phase 4-6 |

**Article's Key Insight Applied:**
> "The real shift happening right now is not the model itself. The bigger transformation is happening in the layers surrounding the model."

This plan transforms Lyra's surrounding layers from **research-focused** to **operationally-complete**, enabling it to:
- Understand organizational context (not just session context)
- Execute business workflows (not just research workflows)
- Learn from operations (not just research)
- Orchestrate across systems (not just within Lyra)

---

## Next Steps

1. **Review & Approve** this plan
2. **Prioritize phases** based on immediate needs
3. **Begin Phase 1** (Organizational Context Layer)
4. **Parallel track** with existing plans where possible
5. **Measure continuously** against success metrics

---

**Document Status:** Master Plan v1.0
**Last Updated:** 2026-05-17
**Relationship:** Additive to all existing plans (Evolution, Context, Transparency, Research)
**Implementation Start:** Phase 1, Week 1 (pending approval)
