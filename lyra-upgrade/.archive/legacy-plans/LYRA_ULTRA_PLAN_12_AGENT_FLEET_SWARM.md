# LYRA ULTRA PLAN 12: Agent Fleet & Swarm v2 — Complete Blueprint

**Version:** 1.0.0 | **Status:** In Progress | **Created:** 2026-05-25
**Parent Plan:** [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md)

---

## Overview

Scale Lyra from single-agent execution to massive parallel agent fleets with squad organization, recursive latent-space communication, DAG-based orchestration, and zero-trust federation. Target: coordinate 1000+ concurrent agents across multiple machines while maintaining coherence.

---

## Part 1: Fleet Architecture

### 1.1 Fleet Topology

```
Fleet (1-N)
├── Lead Orchestrator
│   ├── Task Decomposer
│   ├── Dependency Resolver (DAG builder)
│   ├── Resource Allocator
│   └── Result Aggregator
│
├── Squads (1-N per Fleet)
│   ├── Squad Lead (specialist orchestrator)
│   ├── Agents (3-12 per Squad)
│   │   ├── PM Agent
│   │   ├── Architect Agent
│   │   ├── Engineer Agents
│   │   ├── Test Agent
│   │   └── Review Agent
│   └── Squad Memory (shared context)
│
└── Worker Pool
    ├── Idle agents waiting for task assignment
    ├── Pre-warmed worktrees
    └── Model slot reservations
```

### 1.2 Fleet Commands

```bash
# Fleet management
lyra fleet create --agents 12 --squads 3     # Create fleet
lyra fleet add-squad --agents 4 --role "api-refactor"
lyra fleet status                             # Fleet overview dashboard
lyra fleet list                               # List all active fleets
lyra fleet destroy <id>                       # Destroy fleet

# Task execution
lyra fleet run "Refactor all microservices to async"  # Dispatch to fleet
lyra fleet fan-out "Write unit tests for:" --files "src/**/*.py"  # Fan-out
lyra fleet map-reduce --map "analyze_file" --reduce "synthesize" --files "**/*.ts"

# Monitoring
lyra fleet dashboard              # Real-time fleet dashboard (TUI)
lyra fleet metrics                # Fleet performance metrics
lyra fleet timeline               # Agent execution timeline
lyra fleet bottlenecks            # Identify bottlenecks

# Agent communication
lyra fleet broadcast "Switching to Opus for all reasoning slots"
lyra fleet handoff <agent-a> <agent-b>  # Handoff context between agents
```

### 1.3 Fleet Dashboard (TUI)

```
┌─ Lyra Fleet Dashboard ─────────────────────────────────────────────┐
│ Fleet: refactor-fleet-01  │  Uptime: 02:34:12  │  Status: ACTIVE  │
├────────────────────────────────────────────────────────────────────┤
│ ╔══════════════════════╗  ╔══════════════════════════════════════╗ │
│ ║     FLEET STATS      ║  ║         TASK PROGRESS               ║ │
│ ╠══════════════════════╣  ╠══════════════════════════════════════╣ │
│ ║ Agents:   24/32      ║  ║ ████████████░░░░░░  62% (186/300)  ║ │
│ ║ Active:   18         ║  ║ Completed:  156     Failed:   8     ║ │
│ ║ Idle:      6         ║  ║ Running:     22     Queued:  114   ║ │
│ ║ Squads:    4         ║  ║                                      ║ │
│ ╚══════════════════════╝  ╚══════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────────┤
│ SQUAD STATUS                                                        │
│ ┌──────────────┬──────────┬────────┬─────────┬────────┬──────────┐ │
│ │ Squad        │ Lead     │ Agents │ Tasks   │ Budget │ Status   │ │
│ ├──────────────┼──────────┼────────┼─────────┼────────┼──────────┤ │
│ │ api-refactor │ opus-4.7 │ 8      │ 45/72   │ $4.20  │ RUNNING  │ │
│ │ test-coverage│ sonnet   │ 6      │ 89/112  │ $1.80  │ RUNNING  │ │
│ │ docs-update  │ haiku    │ 4      │ 52/52   │ $0.30  │ DONE     │ │
│ │ perf-optimize│ opus-4.7 │ 6      │ 0/64    │ $0.00  │ QUEUED   │ │
│ └──────────────┴──────────┴────────┴─────────┴────────┴──────────┘ │
├────────────────────────────────────────────────────────────────────┤
│ COST: $8.45 this session │ TOKENS: 2.4M │ AGENT-HOURS: 47.2       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Squad Organization

### 2.1 Squad Roles (MetaGPT-Inspired)

| Role | Model Slot | Responsibilities | Tools |
|------|-----------|-----------------|-------|
| **PM Agent** | reasoning | Task decomposition, priority, dependencies | `agent_delegate`, `goal_set` |
| **Architect Agent** | reasoning | System design, trade-off analysis, patterns | `code_analyze`, `search_code` |
| **Engineer Agent** | coding | Implementation, refactoring, debugging | Full code + shell tools |
| **Test Agent** | coding | Test writing, coverage, regression | `code_test`, `code_lint` |
| **Review Agent** | coding | Code review, security scan, quality gates | `code_lsp_*`, `sec_*` |
| **QA Agent** | fast | Integration testing, E2E, edge cases | `browser_*`, `db_*` |
| **Docs Agent** | fast | Documentation, changelog, API docs | `doc_*`, `file_*` |
| **SRE Agent** | coding | Reliability, monitoring, incident response | `net_*`, `obs_*` |

### 2.2 Squad Formation

```python
class SquadBuilder:
    def from_template(self, template: str) -> Squad:
        """Build squad from predefined templates."""
        ...
    
    def from_task(self, task: Task) -> Squad:
        """Auto-compose squad based on task requirements."""
        roles_needed = self.analyze_task_requirements(task)
        return Squad(
            roles=roles_needed,
            size=min(len(roles_needed) * 3, MAX_SQUAD_SIZE),
            lead_model="claude-opus-4-7",
        )

SQUAD_TEMPLATES = {
    "full-stack-feature": ["PM", "Architect", "Engineer", "Test", "Review", "QA"],
    "api-refactor": ["Architect", "Engineer", "Test", "Review"],
    "bug-hunt": ["Engineer", "Test", "QA"],
    "research-sprint": ["PM", "Architect", "Engineer(×2)", "Test", "Review"],
    "security-audit": ["Architect", "Review", "QA"],
    "docs-sprint": ["PM", "Docs(×2)", "Review"],
    "performance": ["Architect", "Engineer(×2)", "Test", "SRE"],
}
```

### 2.3 Squad Communication

**RecursiveMAS Integration**: Squads communicate via latent-space RecursiveLink modules, reducing inter-agent token usage by 75.6%:

```
Traditional: Agent A → text → Agent B → text → Agent C  (~3000 tokens/msg)
RecursiveMAS: Agent A → latent → Agent B → latent → Agent C  (~730 tokens/msg)
```

---

## Part 3: Parallel Execution Patterns

### 3.1 Fan-Out Pattern

```python
async def fan_out(task: Task, items: list, agent_type: str = "coding"):
    """Map: Distribute N items to M parallel agents. Reduce: Aggregate results."""
    
    # Split items across agents
    batches = chunk(items, len(items) // fleet.active_agents)
    
    # Parallel dispatch
    results = await asyncio.gather(*[
        agent.execute(task.with_context(items=batch))
        for agent, batch in zip(fleet.idle_agents, batches)
    ])
    
    # Aggregate and verify
    aggregated = await lead_agent.synthesize(results)
    verified = await verifier.verify(aggregated)
    
    return verified
```

### 3.2 Map-Reduce Pattern

```python
async def map_reduce(map_fn: str, reduce_fn: str, files: list):
    """Map: Apply fn to each file in parallel. Reduce: Synthesize findings."""
    
    # MAP phase — parallel per file
    map_results = await asyncio.gather(*[
        agent.run(f"{map_fn}: {file}")
        for agent, file in zip(fleet.idle_agents, files)
    ])
    
    # REDUCE phase — single agent synthesizes
    synthesis = await reasoning_agent.run(
        f"{reduce_fn}: Synthesize these findings:\n" +
        "\n".join(map_results)
    )
    
    return synthesis
```

### 3.3 DAG Execution

```python
class DAGOrchestrator:
    """Execute tasks respecting DAG dependency constraints."""
    
    def execute(self, dag: DAG[Task]) -> dict[str, Result]:
        results = {}
        
        for level in dag.topological_levels():
            # All tasks at same level run in parallel
            level_results = asyncio.gather(*[
                agent.execute(task, context=results)
                for task, agent in zip(level, self.assign_agents(level))
            ])
            results.update(level_results)
        
        return results
```

### 3.4 Debate Pattern (K=3)

```python
async def debate(proposal: str, k: int = 3):
    """K-agent debate with pivot/refine loop."""
    
    # Round 1: Independent proposals
    proposals = await asyncio.gather(*[
        agent.propose(proposal) for agent in debate_agents[:k]
    ])
    
    # Round 2: Cross-review
    critiques = await asyncio.gather(*[
        agent.critique(proposals[i], [p for j, p in enumerate(proposals) if j != i])
        for i, agent in enumerate(debate_agents[:k])
    ])
    
    # Round 3: Refine based on critiques
    refined = await asyncio.gather(*[
        agent.refine(proposals[i], critiques[i])
        for i, agent in enumerate(debate_agents[:k])
    ])
    
    # Final: Vote + synthesize
    winner = await lead_agent.synthesize(refined)
    return winner
```

---

## Part 4: Colony Mode — Persistent Agent Swarm

### 4.1 Colony Architecture

```
Colony (persistent, cross-session)
├── Queen Agent (global orchestrator)
│   ├── Strategic memory (colony-level goals)
│   ├── Resource allocation (budget + model slots)
│   └── Health monitoring (all worker agents)
│
├── Nest Memory (shared, append-only)
│   ├── Colony Knowledge Graph
│   ├── Task execution history
│   ├── Lesson store (successes + failures)
│   └── Gossip log (inter-agent communication)
│
└── Workers (specialized, long-lived)
    ├── Builder agents (coding)
    ├── Explorer agents (research)
    ├── Guardian agents (security/review)
    └── Courier agents (external communication)
```

### 4.2 Gossip Memory

Inspired by ant colony stigmergy — agents leave "pheromone trails" in shared memory:

```python
class GossipMemory:
    """Decentralized agent communication via shared memory."""
    
    def deposit(self, agent_id: str, topic: str, content: dict, confidence: float):
        """Leave a memory trace that other agents can discover."""
        ...
    
    def sniff(self, topic: str, min_confidence: float = 0.5) -> list[MemoryTrace]:
        """Discover relevant traces left by other agents."""
        ...
    
    def evaporate(self, ttl_days: int = 7):
        """Remove old, low-confidence traces (pheromone evaporation)."""
        ...
```

### 4.3 Colony Commands

```bash
lyra colony create --workers 24 --squads 6
lyra colony status
lyra colony deploy --goal "Maintain and improve the entire codebase"
lyra colony pause
lyra colony resume
lyra colony destroy
```

---

## Part 5: Cross-Machine Federation

### 5.1 Federation Architecture

```
Machine A (primary)          Machine B (worker)         Machine C (worker)
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ Lead Orchestrator│◄──────►│ Squad Lead       │◄──────►│ Squad Lead       │
│ Fleet Memory     │  gRPC  │ Workers (×8)     │  gRPC  │ Workers (×8)     │
│ Task Queue       │        │ Local worktrees  │        │ Local worktrees  │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

### 5.2 Federation Protocol

```protobuf
service FleetService {
  rpc AssignTask(TaskRequest) returns (TaskResponse);
  rpc ReportStatus(StatusRequest) returns (StatusResponse);
  rpc HandoffContext(ContextHandoff) returns (HandoffResponse);
  rpc HealthCheck(HealthRequest) returns (HealthResponse);
  rpc StreamEvents(stream EventRequest) returns (stream EventResponse);
}
```

---

## Part 6: Implementation Roadmap

### Phase 12.1: Fleet Core (Weeks 1-3)
- [ ] Fleet data model + orchestrator
- [ ] Squad formation + templates
- [ ] Fan-out pattern implementation
- [ ] Fleet dashboard TUI

### Phase 12.2: Parallel Patterns (Weeks 4-6)
- [ ] Map-reduce pattern
- [ ] DAG-based execution
- [ ] K-agent debate pattern
- [ ] RecursiveMAS latent communication

### Phase 12.3: Colony Mode (Weeks 7-10)
- [ ] Colony architecture (Queen + Workers)
- [ ] Gossip memory with stigmergy
- [ ] Nest-level knowledge graph
- [ ] Persistent colony lifecycle

### Phase 12.4: Federation (Weeks 11-14)
- [ ] Cross-machine gRPC protocol
- [ ] Distributed task queue
- [ ] Federation security (mTLS)
- [ ] Multi-machine fleet dashboard

---

## Part 7: Reference & Inspiration

| Source | Key Ideas Adopted |
|--------|------------------|
| [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) | Agent team orchestration, subagent spawning |
| [MetaGPT](https://arxiv.org/abs/2308.00352) | SOP-driven role topology, PM/Architect/Engineer/QA roles |
| [ChatDev](https://arxiv.org/abs/2307.07924) | Waterfall multi-agent SDLC |
| [SemaClaw](https://arxiv.org/abs/2604.11548) | DAG teams, PermissionBridge, task orchestration |
| [RecursiveMAS](https://arxiv.org/abs/2604.25917) | Latent-space communication, 75.6% token reduction |
| [AutoResearchClaw](https://arxiv.org/abs/2605.20025) | K=3 debate + pivot/refine, self-healing executors |
| [Continuous-Claude](https://github.com/AnandChowdhary/continuous-claude) | Long-running agent loop, sleep/wake pattern |
| [Sakana Conductor](https://sakana.ai/) | RL-trained orchestrator replacing hand-engineered pipelines |
