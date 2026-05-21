# Lyra Architecture Audit
**Phase 0: Foundation Assessment - Task #7**  
**Date**: 2026-05-14  
**Status**: Complete

---

## Executive Summary

Lyra is a **production-grade, general-purpose coding agent harness** (v3.14.0) with an integrated Deep Research AI system. It's built as a monorepo with 8 packages, 312+ Python files in core alone, and 2,200+ tests across all packages.

**Current State**: Lyra is a **mature, feature-complete agent** with:
- ✅ Multi-provider LLM support (16 providers)
- ✅ Full agent loop with tools, hooks, permissions
- ✅ Deep Research Agent (8-phase pipeline, 369+ tests)
- ✅ TDD-aware state machine (IDLE → PLAN → RED → GREEN → REFACTOR → SHIP)
- ✅ Subagent orchestration with git worktrees
- ✅ MCP server integration
- ✅ Evaluation harness
- ⚠️ **Self-evolution module exists but is minimal** (1 file, stub implementation)

**Gap Analysis**: The self-evolution capability is the **primary gap** between current state and the LYRA_EVOLUTION_PLAN.md vision. The `lyra-evolution` package exists but contains only a single file with Pareto frontier search scaffolding.

---

## Architecture Overview

### 1. Package Structure

```
projects/lyra/
├── packages/
│   ├── lyra-cli/          # Terminal UI, Typer CLI, 80+ slash commands
│   ├── lyra-core/         # Agent kernel (312 Python files)
│   ├── lyra-research/     # Deep Research Agent (8 phases, 369+ tests)
│   ├── lyra-skills/       # Skill management & evolution tracker
│   ├── lyra-memory/       # Long-term memory (MemoryRecord, store, extractor)
│   ├── lyra-evals/        # Evaluation harness (corpus-based drift gate)
│   ├── lyra-mcp/          # MCP server (exposes Lyra as MCP tool source)
│   └── lyra-evolution/    # Self-evolution engine (⚠️ MINIMAL - 1 file)
├── .lyra/                 # Session management
│   ├── cron/
│   ├── sessions/
│   ├── sessions.sqlite
│   └── interactive_history
└── docs/                  # Architecture docs, blocks/, design specs
```

### 2. Core Components

#### lyra-core (The Kernel)
- **AgentLoop**: Provider-agnostic orchestrator (plan → tools → verify)
- **ToolKernel**: Registry + dispatch for Read, Glob, Grep, Edit, Write, Run, Patch
- **State Machine**: TDD-aware IDLE → PLAN → RED → GREEN → REFACTOR → SHIP
- **Permissions**: plan / auto-edit / bypass-perms modes + hook engine
- **HIR (Harness IR)**: Event emitter writing JSONL to `.lyra/sessions/events.jsonl`
- **LifecycleBus**: Fan-out for chat.*, tool.*, plan.*, subagent.*, cron.* events
- **AliasRegistry**: Single source of truth for model name resolution
- **SubagentRegistry**: Git worktree-isolated subagent orchestration
- **Dependencies**: harness-core, pydantic>=2.0, typing-extensions>=4.5, watchdog>=3.0

#### lyra-research (Deep Research Agent)
**8-Phase Pipeline**:
1. **Discovery** (`sources.py`): Multi-source search (ArXiv, OpenReview, HuggingFace, PwC, ACL, Semantic Scholar, GitHub)
2. **Intelligence** (`intelligence.py`): VerifiableChecklist, EvidenceAudit, GapAnalyzer, FalsificationChecker
3. **Memory** (`memory.py`): Zettelkasten atomic notes, SQLite corpus with FTS, strategy memory, case bank
4. **Reporter** (`reporter.py`): CrossSourceSynthesizer, CitationBinder, ReportQualityChecker
5. **Skills** (`skills.py`): 7-tuple skill formalism, 4 built-in domain skills, evolution tracker
6. **Orchestrator** (`orchestrator.py`): 10-step pipeline (clarify → plan → search → filter → fetch → analyze → audit → synthesize → report → memorize)
7. **Evaluation** (`evaluation.py`): 6-axis quality metrics, SelfEvaluationAgent, quality trend tracker
8. **Learning** (`learning.py`): ResearchStrategyExtractor, CaseSelectionPolicy, DomainExpertiseAccumulator, SelfImprovementGate

**Key Modules**:
- `analysis.py`: Gap analysis, falsification checking
- `discovery.py`: Multi-source discovery
- `evaluation.py`: 6-axis quality metrics
- `fetchers.py`: PDF/HTML content fetchers
- `intelligence.py`: Evidence audit, verifiable checklists
- `learning.py`: Continual learning, self-improvement gate
- `memory.py`: Zettelkasten, corpus management
- `orchestrator.py`: End-to-end pipeline
- `reporter.py`: Cross-source synthesis, citation binding
- `skills.py`: 7-tuple skill formalism
- `sources.py`: Multi-source search
- `strategies.py`: Research strategies
- `synthesis.py`: Cross-source synthesis

**Dependencies**: requests, beautifulsoup4, PyMuPDF, pdfplumber, arxiv, semanticscholar, networkx, spacy, sentence-transformers

#### lyra-evolution (⚠️ MINIMAL)
**Current State**: Single file `self_evolution.py` with:
- `ParetoFrontierSearch`: Pareto frontier search for agent configurations
- `CrossTimeReplay`: Skill selection across time (hard/easy probes)
- `MemoryBenchIntegration`: Evaluation on standard benchmarks
- `SelfEvolutionPipeline`: Combines Pareto + CrossTime + MemoryBench

**Status**: Stub implementation with basic scaffolding. No integration with lyra-core or lyra-research. No tests. No CLI commands.

**Gap**: This is the **primary implementation gap** for the LYRA_EVOLUTION_PLAN.md vision.

#### lyra-skills
- SKILL.md loader
- BM25 router
- Semantic search
- Evolution tracker

#### lyra-memory
- MemoryRecord schema
- Store
- Extractor
- Compression

#### lyra-evals
- Corpus-based drift gate
- pass@k evaluation
- Golden set management

#### lyra-cli
- Typer CLI
- prompt_toolkit REPL
- 80+ slash commands
- Rich output formatting
- 4 interaction modes: agent, plan, debug, ask

#### lyra-mcp
- MCP server implementation
- Exposes Lyra as Model Context Protocol tool source

### 3. Model Routing

**Two-tier split**:
- **fast slot**: Cheap turns (chat, tool calls, summaries) - Default: `deepseek-v4-flash` → `deepseek-chat`
- **smart slot**: Reasoning-heavy work (planning, /spawn, cron, review) - Default: `deepseek-v4-pro` → `deepseek-reasoner`

**Supported Providers (16)**:
DeepSeek, Anthropic, OpenAI, Gemini, xAI, Groq, Cerebras, Mistral, Qwen, OpenRouter, AWS Bedrock, Google Vertex, GitHub Copilot, LM Studio, Ollama, OpenAI-compatible

### 4. Key Features

#### Interaction Modes
- `agent`: Full access (reads, writes, tools) - default
- `plan`: Read-only design, queues pending_task for approval
- `debug`: Hypothesis → experiment → fix loop
- `ask`: Read-only Q&A, no edits, no tools

#### Slash Commands (80+)
- `/help`: List all commands
- `/status`: Snapshot (repo, model, mode, turn, cost)
- `/model [fast|smart|<name>]`: Inspect/change active model
- `/research <topic>`: Run deep research session
- `/spawn <task>`: Spawn git-worktree-isolated subagent
- `/skills`: List loaded skills
- `/skill add <name>`: Install skill from registry
- `/evals`: Run eval harness
- `/burn`: Token observatory
- `/compact`: Compress context
- `/approve` / `/reject`: Accept/reject pending plan or tool call

#### TDD State Machine
```
IDLE → PLAN → RED → GREEN → REFACTOR → SHIP
```
- Opt-in TDD plugin (disabled by default in v3.0.0)
- `tdd-gate` PreToolUse / Stop hook
- RED-proof validator

#### Subagent Orchestration
- Git worktree isolation
- SubagentRegistry + SubagentRunner contract
- Parallel subagent execution

#### HIR (Harness IR)
- Event emitter writing JSONL to `.lyra/sessions/events.jsonl`
- Source of truth for all packages
- Replay capability

---

## Capabilities Assessment

### ✅ Mature Capabilities

1. **Agent Loop**: Production-grade orchestrator with plan → tools → verify cycle
2. **Tool Pool**: Comprehensive (Read, Glob, Grep, Edit, Write, Run, Patch + MCP)
3. **Multi-Provider**: 16 LLM providers with unified interface
4. **Deep Research**: 8-phase pipeline with 369+ tests, fully integrated
5. **Memory System**: Long-term memory with MemoryRecord, store, extractor, compression
6. **Evaluation**: Corpus-based drift gate, pass@k, golden set
7. **Permissions**: 3 modes (plan, auto-edit, bypass-perms) + hook engine
8. **Subagents**: Git worktree isolation + orchestration
9. **MCP Integration**: Exposes Lyra as MCP tool source
10. **TDD Support**: State machine + RED-proof validator (opt-in)

### ⚠️ Minimal/Stub Capabilities

1. **Self-Evolution**: `lyra-evolution` package exists but is minimal
   - Single file with Pareto frontier scaffolding
   - No integration with lyra-core or lyra-research
   - No tests
   - No CLI commands
   - **This is the primary gap for LYRA_EVOLUTION_PLAN.md**

### 🔴 Missing Capabilities (from LYRA_EVOLUTION_PLAN.md)

1. **Eternal Mode Runtime**: Not present in Lyra
   - Exists in `packages/harness-eternal/` (shared infrastructure)
   - Not integrated into Lyra
   - Lyra uses `.lyra/sessions/` for session management instead

2. **Restate Workflow**: Not present in Lyra
   - Exists in `packages/harness-eternal/` (shared infrastructure)
   - Not integrated into Lyra

3. **Skill Self-Evolution**: Minimal implementation
   - `lyra-skills` has evolution tracker
   - `lyra-evolution` has Pareto frontier scaffolding
   - No integration between them
   - No trust tiers (RED/YELLOW/GREEN)
   - No surrogate verification
   - No claim gate / trust gate hooks

4. **Budget Envelope**: Not present in Lyra
   - Exists in `packages/harness-eternal/` (shared infrastructure)
   - Not integrated into Lyra

5. **Heartbeat Scheduler**: Not present in Lyra
   - Exists in `packages/harness-eternal/` (shared infrastructure)
   - Not integrated into Lyra

6. **Darwin Gödel Machine**: Not implemented
7. **HyperAgents**: Not implemented
8. **Voyager-style Skill Library**: Partial (lyra-skills has loader + router, but no automatic curriculum)
9. **Reflexion**: Not implemented
10. **SkillFoundry**: Not implemented
11. **SEVerA**: Not implemented

---

## Integration with Shared Infrastructure

### Relationship to harness-* packages

Lyra is **one of the harness daemons** mentioned in `packages/harness-eternal/README.md` (along with Argus and Polaris).

**Shared Infrastructure Available**:
1. **harness-eternal**: Eternal Mode runtime (Restate workflow, Budget envelope, MemoryCap, Heartbeat scheduler)
2. **harness-skills**: Skill self-evolution module (extract, verify, store, retrieve, promote, hooks)
3. **harness-tui**: Shared TUI shell (14 brand-themed agent skins)

**Current Integration Status**:
- ❌ Lyra does NOT use harness-eternal
- ❌ Lyra does NOT use harness-skills (has its own lyra-skills package)
- ❌ Lyra does NOT use harness-tui (has its own lyra-cli package)
- ✅ Lyra depends on harness-core (base utilities)

**Implication**: Lyra is currently **independent** from the shared harness infrastructure. The LYRA_EVOLUTION_PLAN.md envisions integrating these shared packages.

---

## Dependency Analysis

### lyra-core Dependencies
```toml
dependencies = [
    "harness-core",
    "pydantic>=2.0",
    "typing-extensions>=4.5",
    "watchdog>=3.0",
]
```

### lyra-research Dependencies
```toml
dependencies = [
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0",
    "PyMuPDF>=1.23.0",
    "pdfplumber>=0.10.0",
    "arxiv>=2.1.0",
    "semanticscholar>=0.8.0",
    "networkx>=3.2",
    "spacy>=3.7.0",
    "sentence-transformers>=2.3.0",
]
```

### Shared Infrastructure Dependencies

**harness-eternal**:
```toml
dependencies = ["psutil>=5.9"]
optional = ["restate-sdk>=0.6"]
```

**harness-skills**:
```toml
dependencies = [] # minimal
```

**harness-tui**:
```toml
dependencies = [
    "textual>=0.85",
    "rich>=13.7",
    "pydantic>=2.6",
    "httpx>=0.27",
    "click>=8.1",
    "pyyaml>=6.0"
]
```

---

## Test Coverage

**Total Tests**: 2,200+ across all packages
- lyra-core: 796 tests (v3.0.0)
- lyra-research: 369+ tests
- Other packages: ~1,035 tests

**Test Organization**:
- Contract tests in `tests/`
- Load-bearing files: `test_agent_loop_*.py`, `test_state_machine.py`, `test_kernel.py`, `test_aliases.py`, `test_lifecycle_bus.py`, `test_providers_registry.py`

**Coverage**: High coverage in core and research packages

---

## Code Quality

### Linting & Formatting
- **ruff**: Line length 100, target Python 3.11
- **pyright**: Basic type checking mode
- **pre-commit**: Configured

### Code Organization
- Clean package boundaries
- Provider-agnostic core
- Clear separation: lyra-core (contracts) vs lyra-cli (implementations)

---

## Session Management

### .lyra/ Directory
```
.lyra/
├── cron/                    # Cron jobs
├── sessions/                # Session history
├── sessions.sqlite          # Session database
└── interactive_history      # REPL history
```

**HIR Events**: `.lyra/sessions/events.jsonl` - source of truth for all packages

---

## Documentation

### Available Docs
- `README.md`: Comprehensive overview
- `docs/blocks/`: Per-feature design specs
- `docs/architecture.md`: Topology
- `CHANGELOG.md`: Version history
- `CONTRIBUTING.md`: Contribution guidelines

---

## Comparison to LYRA_EVOLUTION_PLAN.md

### Phase 0 Requirements vs Current State

| Requirement | Status | Notes |
|-------------|--------|-------|
| Audit current architecture | ✅ Complete | This document |
| Identify core vs peripheral | ✅ Complete | Core: agent_loop, kernel, tools, hir, lifecycle. Peripheral: cli, mcp, evals |
| Map dependencies | ✅ Complete | See Dependency Analysis section |
| Document capabilities | ✅ Complete | See Capabilities Assessment section |
| Assess integration points | ✅ Complete | Currently independent from harness-* shared infrastructure |

### Key Findings

1. **Lyra is production-ready** as a general-purpose coding agent
2. **Deep Research Agent is mature** (8 phases, 369+ tests, fully integrated)
3. **Self-evolution is the primary gap** (minimal implementation in lyra-evolution)
4. **Shared infrastructure exists but is not integrated** (harness-eternal, harness-skills, harness-tui)
5. **Strong foundation for evolution** (clean architecture, high test coverage, extensible design)

---

## Recommendations for Phase 1+

### Priority 1: Self-Evolution Foundation
1. Integrate `harness-skills` into Lyra (replace/extend lyra-skills)
2. Implement trust tiers (RED/YELLOW/GREEN)
3. Add surrogate verification (cross-model adversarial pair)
4. Build claim gate / trust gate hooks

### Priority 2: Eternal Mode Integration
1. Integrate `harness-eternal` for infinite autonomous operation
2. Add Restate workflow for durable execution
3. Implement Budget envelope (token + $ + wallclock limits)
4. Add Heartbeat scheduler for cadenced cycles

### Priority 3: TUI Integration
1. Integrate `harness-tui` for brand-themed agent skins
2. Replace lyra-cli REPL with shared TUI shell
3. Add Transport layer for backend-to-TUI communication

### Priority 4: Advanced Self-Evolution
1. Implement Darwin Gödel Machine (iterative code self-modification)
2. Add HyperAgents (dual-function: solve_task + modify_self)
3. Build Voyager-style automatic curriculum
4. Implement Reflexion (verbal reinforcement learning)
5. Add SkillFoundry (tree-guided skill mining)
6. Implement SEVerA (formally verified self-evolution)

---

## Architecture Strengths

1. **Clean separation of concerns**: Core (contracts) vs CLI (implementations)
2. **Provider-agnostic design**: 16 providers with unified interface
3. **Extensible tool system**: ToolKernel with registry + dispatch
4. **Event-driven architecture**: HIR events as source of truth
5. **High test coverage**: 2,200+ tests
6. **Mature research capabilities**: 8-phase pipeline with 369+ tests
7. **Git worktree isolation**: Safe subagent orchestration
8. **TDD-aware**: Optional state machine for test-driven development

---

## Architecture Weaknesses

1. **Self-evolution is minimal**: lyra-evolution package is a stub
2. **Not integrated with shared infrastructure**: Independent from harness-eternal, harness-skills, harness-tui
3. **No Eternal Mode**: Cannot run as infinite autonomous daemon
4. **No budget controls**: No token/$/wallclock limits
5. **No trust tiers**: All skills treated equally
6. **No surrogate verification**: No cross-model adversarial validation
7. **No automatic curriculum**: Skill library exists but no automatic progression

---

## Conclusion

Lyra is a **mature, production-grade coding agent** with excellent research capabilities. The architecture is clean, extensible, and well-tested. The **primary gap** for the LYRA_EVOLUTION_PLAN.md vision is the **self-evolution capability**, which exists only as a minimal stub.

The path forward is clear:
1. Integrate shared infrastructure (harness-eternal, harness-skills, harness-tui)
2. Build out self-evolution capabilities (trust tiers, surrogate verification, skill promotion)
3. Implement advanced self-evolution patterns (DGM, HyperAgents, Voyager, Reflexion, SkillFoundry, SEVerA)

The foundation is strong. The next 27 weeks will transform Lyra from a **general-purpose coding agent** into a **self-improving AI agent that can rewrite its own code to grow and evolve over time**.

---

**Audit Complete**: 2026-05-14  
**Next Task**: #6 - Set up sandboxed execution environment
