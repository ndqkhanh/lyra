# Phase 4 Research Findings: Swarm, Autonomy, Deep Research, rmux, Multi-tenancy

**Research Date**: 2026-05-31  
**Scope**: §3.6, §3.8, §3.10, §3.12, §3.19 — AutoScientists, terminal multiplexers, autonomy patterns, workflows, deep research systems

---

## Executive Summary

This research synthesizes breakthrough patterns from 23 sources across swarm coordination, autonomous operation, deep research, terminal multiplexing, and multi-tenancy. Key findings:

1. **AutoScientists decentralized coordination** outperforms centralized planning by 8.33% through self-organizing teams, shared state, and adversarial validation
2. **Anthropic's multi-agent research system** achieves 90.2% improvement over single-agent through orchestrator-worker pattern with parallel execution
3. **rmux provides typed SDK** for programmatic terminal control, enabling agent coordination without tmux dependency
4. **AgentsMesh demonstrates production multi-tenancy** with control/data plane separation, mTLS isolation, and channel-based collaboration
5. **Continuous-claude proves autonomous loops** viable through shared memory files and relay-race handoffs

**Breakthrough synthesis**: Combine Claude Code teams + AutoScientists self-organizing + adversarial validation + shared memory + channel-based communication for Lyra's swarm architecture.

---

## 1. Swarm Coordination Patterns

### 1.1 AutoScientists: Decentralized Self-Organization

**Architecture**:
- **Shared State (`S`)**: Champion solution `p*`, experiment log `L`, discussion forum `F`, proposal queues `Qk`, dead-end registries `Dk`
- **Agent Types**: Analyst (proposes, ranks, maintains dead-ends) + Experiment (executes, records results)
- **Coordination**: No central orchestrator — agents independently read state, act, write back

**Self-Organizing Mechanism**:
1. Agents form teams around research directions through discussion (not user-specified decomposition)
2. Teams run parallel propose-execute loops with critique before compute expenditure
3. Cross-team knowledge sharing prevents redundant exploration
4. Dynamic reorganization when teams stagnate

**Performance**:
- BioML-Bench: 74.4% mean percentile (+8.33% over prior best)
- GPT training: 1.9× faster convergence, 7 improvements vs 0 baseline
- ProteinGym: +12.5% on development assay, +6.5% across 217 assays

**Key Insight**: Decentralized coordination with shared state enables sustained parallel exploration and adaptation as evidence accumulates, overcoming brittleness of single-trajectory or centrally-planned systems.

### 1.2 Anthropic Multi-Agent Research System

**Architecture**:
- **Orchestrator-Worker Pattern**: Lead agent (LeadResearcher) coordinates specialized subagents
- **Parallel Execution**: 3-5 subagents operate simultaneously, each making 3+ parallel tool calls
- **Memory Persistence**: Lead saves plans to Memory to persist beyond 200k token limit
- **Dynamic Multi-Step Search**: Subagents iteratively filter information, return condensed findings

**Performance**:
- **90.2% improvement** over single-agent Opus 4
- **15× token usage** but proportional value for complex tasks
- **Up to 90% time reduction** through parallel tool calling

**Prompt Engineering Principles**:
1. Think like your agents (simulate in Console)
2. Teach delegation (objective, format, tools, boundaries)
3. Scale effort to complexity (1 agent for simple, 10+ for complex)
4. Tool design is critical (explicit heuristics)
5. Let agents improve themselves (40% completion time decrease)
6. Start wide, then narrow (broad queries → progressive focus)
7. Guide thinking process (extended thinking for planning, interleaved for evaluation)
8. Parallel execution (spawn multiple agents, use multiple tools)

**Production Patterns**:
- **Stateful execution**: Resume from failure points, inform agents of tool failures
- **Memory persistence**: Save plans before context limits, retrieve stored context
- **Filesystem outputs**: Store work externally, pass lightweight references
- **Rainbow deployments**: Gradual traffic shift without disrupting in-progress agents

### 1.3 Claude Code Dynamic Workflows

**Capabilities**:
- Dynamically write orchestration scripts for tens to hundreds of parallel subagents
- Break tasks into subtasks, fan work across parallel agents
- Adversarial validation: agents address from independent angles, others refute, iterate until convergence
- Long-running operations (hours/days) with persistent progress
- Interrupted jobs pick up where they left off

**Activation**:
- Direct request: "create a dynamic workflow"
- Enable `ultracode` setting (xhigh effort, automatic workflow decision)

**Use Cases**: Codebase-wide audits, large migrations (750k lines Rust from Zig in 11 days), critical work requiring independent verification

### 1.4 Companies as Algorithmic Graphs

**Core Thesis**: Companies decompose into interconnected workflows — "a graph of algorithms" — where each business function breaks into discrete, optimizable steps.

**Coordination Mechanisms**:
- Meeting scheduling, idea generation/evaluation, decision capture, cross-team sync, campaign execution
- Each coordination point = node where human involvement can be measured, questioned, replaced

**Application to Agent Systems**:
- **Transparency as prerequisite**: AI optimization requires explicit workflow mapping
- **Continuous analysis**: AI perpetually interrogates each node (humans involved? latency? parallelizable? necessary?)
- **Multi-agent decomposition**: Graph structure naturally maps to agent architectures — each node = potential agent responsibility, edges = handoffs/dependencies

### 1.5 Adversarial Workflow Security

**JAW Framework**: Detects and exploits vulnerabilities in agentic workflows integrating LLM agents into automation platforms (GitHub Actions, n8n).

**Vulnerability Scale**:
- 4,714 GitHub workflows hijacked
- 8 n8n templates compromised
- 15 widely-used GitHub Actions affected (Claude Code, Gemini CLI, Qwen CLI, Cursor CLI)
- Attack outcomes: credential exfiltration, arbitrary command execution

**Security Implications**:
- First academic study of risks in agentic workflows
- Systemic vulnerability class: untrusted inputs can manipulate LLM-based automation agents
- **Critical for Lyra**: Implement input validation, context isolation, and adversarial validation before executing agent proposals

---

## 2. Deep Research Systems

### 2.1 Tongyi DeepResearch

**Architecture**:
- **30.5B parameters, 3.3B activated per token** (MoE)
- **128K context window**
- **Three training phases**: Agentic pre-training → Supervised fine-tuning → Reinforcement learning (Group Relative Policy Optimization)

**Inference Paradigms**:
- **ReAct Mode**: Standard agent reasoning
- **IterResearch 'Heavy' Mode**: Test-time scaling for maximum performance

**Tool Integration**: Web search (Serper.dev), content reading (Jina.ai), document processing (Dashscope), code execution (SandboxFusion), summarization (OpenAI-compatible APIs)

**Key Innovation**: Fully automated synthetic data generation pipeline without human annotation, enabling scalable agentic training.

### 2.2 Open Deep Research

**Architecture**:
- **Multi-stage pipeline**: Search agent → result summarization → research compression → final report generation
- **Plan-and-execute approach**: Sequential section processing, iterative refinement through reflection, human-in-the-loop planning
- **LangGraph-based**: Supports multiple LLM providers, search tools, MCP servers

**Performance** (Deep Research Bench, 100 PhD-level tasks):
- GPT-5: 0.4943 score, 204.6M tokens
- Defaults (GPT-4.1): 0.4309 score, $45.98, 58M tokens
- Claude Sonnet 4: 0.4401 score, $187.09, 138.9M tokens

**Deployment**: Local (uvx + langgraph dev) or LangGraph Platform / Open Agent Platform for non-technical users

### 2.3 GPT Researcher

**Architecture**:
- **Planner-execution-publisher pattern**: Planner generates research questions → execution agents gather info in parallel → publisher aggregates into reports
- **Parallelized agent work** for speed
- **Multi-source aggregation** (20+ sources) to reduce bias
- **Context management** across research branches

**Advanced Workflows**:
- **Deep Research**: Recursive tree-like exploration (~5 min, ~$0.4 per research)
- **Multi-agent assistants**: LangGraph + AG2, inspired by STORM paper
- **MCP integration**: GitHub repos, databases, custom APIs alongside web search

**Philosophy**: "The more sites we scrape the less chances of incorrect data" — frequency across sources reduces misinformation

### 2.4 AutoResearchClaw

**Architecture**:
- **23-stage pipeline across 8 phases**: Scoping → Literature → Synthesis → Design → Execution → Analysis → Writing → Finalization
- **Anti-fabrication system**: VerifiedRegistry enforces ground-truth experiment data
- **Citation integrity**: 4-layer verification (arXiv ID → CrossRef/DataCite DOI → Semantic Scholar title → LLM relevance)
- **Self-learning**: Extracts lessons per run with 30-day decay

**Human-in-the-Loop** (v0.4.0):
- **Co-Pilot**: Deep collaboration at critical stages
- **SmartPause**: Confidence-driven dynamic pausing
- **Cost Guardrails**: Budget monitoring with threshold alerts
- **Branch Exploration**: Fork pipeline for multiple hypotheses

**Integration**: OpenClaw compatible, ACP protocol support (Claude Code, Codex CLI, Copilot CLI, Gemini CLI, Kimi CLI), domain specialists (ColliderAgent, COBRApy)

**Performance**: +18.3% robustness improvement with MetaClaw integration

### 2.5 Agentic Reasoning Framework

**Key Innovation**: Tools invoked *during* reasoning chain generation, not after completion.

**Architecture Components**:
- Search engines for real-time information
- Code interpreters for computational verification
- Knowledge retrieval for domain-specific facts
- Graph-based memory for context management

**Critical Insights**:
1. "Reasoning and tool use should be interleaved rather than sequential"
2. Models benefit from explicit prompting about *when* to use tools
3. Retrieval timing matters: early retrieval prevents hallucination propagation

**Performance**: Substantial gains on GPQA (graduate-level science), GAIA (real-world assistant tasks), mathematical reasoning

---

## 3. Autonomy Patterns

### 3.1 Continuous-Claude

**Loop Architecture**:
```bash
while true; do
  claude --dangerously-skip-permissions "Increase test coverage..."
  sleep 1
done
```

**Full Workflow (per iteration)**:
1. Create new branch, run Claude Code
2. Push changes, create PR via `gh` CLI
3. Monitor CI checks with `gh pr checks`
4. Merge on success or discard on failure
5. Pull updated main, clean up, repeat

**Context Persistence**:
- **Shared memory file** (default `SHARED_TASK_NOTES.md`) acts as external memory across iterations
- **Relay-race pattern**: "Think of it as a relay race" — leave clear notes for next iteration
- Example handoff: "tried adding tests to X but failed on edge case, need to handle null input in function Y"

**Autonomy Features**:
- **Early stopping**: `CONTINUOUS_CLAUDE_PROJECT_COMPLETE` signal (configurable, default 3 consecutive)
- **Failure handling**: Failed PRs closed/discarded, `--stall-threshold` pauses with diagnostics, `--error-threshold` exits
- **Budget controls**: `--max-runs`, `--max-cost`, `--max-duration`, `--max-calls-per-hour`

**Parallel Execution**: Git worktrees for simultaneous instances (`--worktree tests`, `--worktree docs`)

**Reviewer Pass**: Optional `--review-provider` runs validation after each iteration

**Key Insight**: "Radiation of probabilities" — each run is like a random particle, wasteful but effective as token costs approach zero. Human oversight through PR reviews while Claude handles grunt work.

---

## 4. Terminal Multiplexing & Coordination

### 4.1 tmux: Foundational Patterns

**Client-Server Model**: Persistent server process manages sessions independently of client connections. Clients detach/reattach without disrupting running processes.

**Multiplexing Hierarchy**:
- **Sessions**: Top-level containers that persist independently
- **Windows**: Virtual terminals within sessions (like browser tabs)
- **Panes**: Split views within windows for simultaneous terminal access

**IPC & Communication**:
- Event-driven design with libevent 2.x for asynchronous I/O
- Custom protocol for client-server communication
- Notification system for state changes (control-notify.c, control.c)

**State Management**:
- Sessions maintain environment variables, options, buffer contents independently
- Grid abstraction separates logical content from display rendering

**Design Principles**: Separation of concerns, resilience (server survives client disconnections), composability (nested multiplexing), scriptability (extensive command interface)

### 4.2 rmux: Rust Multiplexer for Agentic Era

**Core Capabilities**:
- **Persistent sessions**: Detachable terminal sessions that survive disconnection
- **Typed SDK**: Programmatic control via `rmux-sdk` Rust crate
- **Cross-platform**: Linux (Unix sockets), macOS (Unix sockets), Windows (Named Pipes)
- **Terminal automation**: Drive CLI/TUI apps from code with structured snapshots
- **Ratatui integration**: `ratatui-rmux` widget for embedding terminal views

**Architecture**:
- Three public surfaces (CLI, SDK, widget) share single local protocol
- Daemon handles sessions, panes, layouts, PTY management
- Communication via local IPC (Unix sockets or Windows Named Pipes)

**Key Features**:
```rust
// Session management
let session = rmux.ensure_session(
    EnsureSession::named("work")
        .policy(EnsureSessionPolicy::CreateOrReuse)
        .detached(true)
).await?;

// Pane control
pane.send_text("command\n").await?;
pane.wait_for_text("ready").await?;
let snapshot = pane.snapshot().await?;
```

**Graphics Passthrough**: Supports Kitty graphics and SIXEL protocols

**Use Cases**: Multi-agent coordination, broadcast arenas, terminal mirroring, Playwright-style testing of terminal applications

**License**: Dual MIT/Apache-2.0

### 4.3 cmux: Terminal Multiplexer for AI Agent Coordination

**Core Architecture**:
- Native macOS terminal built on Ghostty's libghostty rendering engine
- Written in Swift/AppKit (not Electron)
- Socket and CLI API for programmatic control
- Integrated WebKit browser with scriptable API

**Agent Coordination Features**:

**Notification System**:
- Terminal escape sequences (OSC 9/99/777)
- CLI: `cmux notify`
- Visual indicators: blue rings on panes, lit tabs in sidebar
- Centralized notification panel
- `⌘⇧U` jumps to latest unread

**Session Management**:
- Persistent state across restarts: window/workspace/pane layouts, working directories, scrollback, browser URLs, agent session IDs
- Hook installation: `cmux hooks setup`, `cmux hooks setup codex`, `cmux hooks setup --agent opencode`
- Supported agents: Claude Code, Codex, Grok, OpenCode, Pi, Amp, Cursor CLI, Gemini, Rovo Dev, Copilot, CodeBuddy, Factory, Qoder
- Custom resume commands: `cmux surface resume set --kind tmux --checkpoint work --shell "tmux attach -t work"`

**Workspace Organization**:
- Sidebar metadata per tab: Git branch, linked PR status/number, working directory, listening ports, latest notification text

**Browser Integration**:
- Scriptable browser API: snapshot accessibility tree, get element references, click, fill forms, evaluate JavaScript
- Route through remote network in SSH sessions
- Split browser panes alongside terminals

**SSH Remote Development**:
- `cmux ssh user@remote` creates isolated workspace
- Browser panes route through remote network
- Localhost URLs work transparently
- Drag-and-drop image upload via scp

**Claude Code Teams Integration**:
- `cmux claude-teams` spawns teammate mode
- Teammates appear as native splits
- Sidebar shows metadata per teammate
- Notification system tracks each teammate's state
- No tmux dependency

**Scriptability**:
- CLI and socket API control: create workspaces/tabs, split panes, send keystrokes, open URLs in browser
- Custom commands via `cmux.json`

**Design Philosophy**: "cmux is a primitive, not a solution" — provides composable building blocks without prescribing workflows

**Technical Constraints**: macOS only (native AppKit), 8192 token limit on Write/Edit tools requires chunked operations, GPL-3.0-or-later license

### 4.4 Warp: Agentic Development Environment

**Architecture**:
- Built in Rust (98.2% of codebase)
- UI Framework: `warpui_core` and `warpui` crates (MIT licensed)
- Agent Integration: Built-in coding agent (Oz) + support for external CLI agents (Claude Code, Codex, Gemini CLI)
- Platform Support: macOS and Linux

**Modern Terminal Patterns**:
- Async runtime built on Tokio for concurrent operations
- WebAssembly for certain components
- Shell integration: bash and zsh with completion specs from Fig

**Session & Collaboration Features**:
- **Agentic management**: Automated issue triage, spec writing, implementation, PR review
- **Web-compiled terminal**: Active agent sessions viewable through web interface at build.warp.dev
- **Community dashboard**: Real-time visibility into thousands of agent operations across codebase

**Technical Dependencies**: Tokio, NuShell, Alacritty, Hyper HTTP library, FontKit, Smol async runtime

### 4.5 AlphaClaw: Management Harness for OpenClaw

**Core Architecture**:
- Setup UI (Preact + htm + Wouter)
- Express API server with auth and proxy
- Watchdog for crash recovery and notifications
- Webhook system with transforms and logging
- Gateway Manager spawns/monitors OpenClaw as child process

**Agent Coordination & Multiplexing**:

**Multi-Agent Management**:
- Sidebar navigation for switching between agents
- Per-agent configuration, channel bindings, overview cards
- URL-driven agent selection
- Create, rename, delete flows through UI

**Channel Orchestration**:
- Telegram, Discord, Slack bot pairing
- Per-agent channel bindings with credential sync
- Telegram topic splitting for multi-threaded groups
- CLI: `alphaclaw telegram topic add --thread <id> --name <text>`

**Node Coordination** (VPS deployments):
- Guided local-node setup
- Per-node browser attach checks
- Reconnect commands and routing/pairing controls

**Watchdog System**:
- Periodic health checks via `openclaw health`
- Crash detection listening for gateway exit events
- Crash-loop detection (default: 3 crashes in 300s)
- Auto-repair runs `openclaw doctor --fix --yes` then relaunches
- SQLite-backed incident history

**Git Integration**:
- Automatic hourly workspace commits to GitHub
- Configurable cron schedule
- CLI: `alphaclaw git-sync -m "message"`
- Combined with prompt hardening for version-controlled audit trail

**Prompt Hardening**:
- Anti-drift bootstrap prompts (`AGENTS.md`, `TOOLS.md`)
- Injected into system prompt on every message
- Enforces safe practices, commit discipline, change summaries

**Integration Capabilities**:
- Google Workspace OAuth (Gmail, Calendar, Drive, Docs, Sheets, Tasks, Contacts, Meet)
- Gmail watch setup with Pub/Sub topic/subscription
- Codex OAuth with built-in PKCE flow
- Named webhook endpoints with transform modules and OAuth callback support

**Deployment**: Docker/Linux, Railway/Render templates for one-click deployment, Node.js ≥ 22.14.0

---

## 5. Multi-Tenancy & Isolation

### 5.1 AgentsMesh: AI Agent Workforce Platform

**Core Concept**: Transforms AI agents from individual tools into coordinated workforce through remote workstations (AgentPods), multi-agent collaboration channels, and integrated task management.

**Architecture**:

**Control/Data Plane Separation**:
- **Control**: gRPC with mTLS for orchestration commands
- **Data**: WebSocket relay cluster for terminal I/O streaming

**Components**:
- **Backend**: Go (Gin + GORM) - auth, org/team management, pod lifecycle, task management
- **Web**: Next.js frontend - dashboard, web terminal, kanban, topology visualization
- **Relay**: Terminal relay cluster - low-latency WebSocket pub/sub
- **Runner**: Self-hosted Go daemon - connects via gRPC+mTLS and WebSocket, runs agents in isolated PTY sandboxes
- **Infrastructure**: PostgreSQL, Redis, MinIO (S3-compatible storage)

**Multi-Tenancy & Isolation**:

**Hierarchy**: Organization > Team > User with row-level isolation

**Runner Isolation**:
- Self-hosted runners execute on user infrastructure
- "Your code never leaves your environment"
- PTY sandboxes for agent execution
- Git worktree isolation per pod

**Security**:
- mTLS for runner-backend connections
- JWT for web authentication
- BYOK model - users provide their own AI API keys

**Agent Coordination**:

**AgentPod System**:
- Remote AI workstations with web terminal access
- Multiple concurrent pods per user
- Real-time streaming of agent output

**Collaboration Mechanisms**:
- Channels for agent communication
- Pod bindings to coordinate multi-agent workflows
- Real-time topology visualization of collaboration patterns

**Task Integration**:
- Kanban board with ticket-pod binding
- Progress tracking across agent activities
- MR/PR integration with Git providers (GitLab, GitHub, Gitee)

**Supported Agents**: Claude Code, Codex CLI, Gemini CLI, Aider, OpenCode, plus any custom terminal-based agent

**Deployment Model**:
- Hosted service at agentsmesh.ai
- Self-hosted option with Docker images
- Runner daemon installs via curl script or system packages (deb, rpm, Windows)
- Enterprise features: SSO, RBAC, audit logs, air-gapped deployment

**License**: BSL-1.1 until 2030-02-28, then GPL-2.0-or-later. Non-production use allowed; production requires commercial license until change date.

---

## 6. Synthesis: Breakthrough Architecture for Lyra

### 6.1 Core Principles

1. **Decentralized coordination** (AutoScientists) over centralized planning
2. **Shared state** for cross-agent knowledge sharing
3. **Adversarial validation** before resource expenditure
4. **Parallel execution** with orchestrator-worker pattern (Anthropic)
5. **Channel-based communication** for multi-agent collaboration (AgentsMesh)
6. **Persistent context** through shared memory files (continuous-claude)
7. **Typed SDK** for programmatic control (rmux)
8. **Self-organizing teams** that dynamically reorganize based on progress

### 6.2 Recommended Architecture

**Layer 1: Coordination Substrate**
- rmux-inspired typed SDK for terminal control
- Shared state store: champion solutions, experiment logs, discussion forums, proposal queues, dead-end registries
- Channel system for agent-to-agent communication (inspired by AgentsMesh)

**Layer 2: Agent Orchestration**
- Orchestrator-worker pattern (Anthropic) with lead agent coordinating specialized subagents
- Claude Code teams integration for native parallel execution
- Dynamic workflow generation for complex tasks

**Layer 3: Self-Organization**
- AutoScientists-style team formation around research directions
- Adversarial validation: agents critique proposals before execution
- Cross-team knowledge sharing to prevent redundant exploration
- Dynamic reorganization when teams stagnate

**Layer 4: Autonomy**
- Continuous operation loop (continuous-claude pattern)
- Shared memory files for relay-race handoffs between iterations
- Early stopping signals, failure handling, budget controls
- Reviewer pass for validation after each iteration

**Layer 5: Deep Research**
- Agentic reasoning with interleaved tool use
- Multi-stage pipeline: planning → execution → analysis → synthesis
- Citation integrity with 4-layer verification
- Self-learning with lesson extraction and 30-day decay

**Layer 6: Multi-Tenancy**
- Control/data plane separation (AgentsMesh pattern)
- Runner isolation with PTY sandboxes and git worktree per agent
- mTLS for secure communication
- BYOK model for API keys

### 6.3 Security Considerations

Based on adversarial workflow security research (JAW framework):
1. **Input validation**: Sanitize all external inputs before passing to agents
2. **Context isolation**: Prevent agents from accessing credentials or sensitive data
3. **Adversarial validation**: Require peer critique before executing proposals
4. **Audit trail**: Log all agent actions for forensic analysis
5. **Capability restrictions**: Limit agent actions based on trust level

### 6.4 Performance Targets

Based on research findings:
- **90.2% improvement** over single-agent through multi-agent coordination (Anthropic)
- **8.33% improvement** through decentralized self-organization (AutoScientists)
- **Up to 90% time reduction** through parallel tool calling (Anthropic)
- **1.9× faster convergence** through team-based exploration (AutoScientists)

---

## 7. Key Takeaways

1. **Decentralization wins**: AutoScientists' decentralized coordination outperforms centralized planning by enabling sustained parallel exploration and adaptation.

2. **Orchestrator-worker scales**: Anthropic's pattern achieves 90.2% improvement through lead agent coordinating 3-5 parallel subagents, each making 3+ parallel tool calls.

3. **Shared state enables coordination**: AutoScientists' shared state (champion, logs, forums, queues, dead-ends) allows agents to self-organize without central control.

4. **Adversarial validation prevents waste**: Critique before execution reduces redundant exploration and improves robustness.

5. **Persistent context is critical**: Continuous-claude's shared memory files enable relay-race handoffs across iterations, maintaining progress through context limits.

6. **Typed SDK enables programmatic control**: rmux demonstrates that typed SDK for terminal control enables sophisticated agent coordination patterns.

7. **Multi-tenancy requires isolation**: AgentsMesh's control/data plane separation, PTY sandboxes, and mTLS provide production-grade multi-tenancy.

8. **Security is paramount**: JAW framework reveals systemic vulnerabilities in agentic workflows — input validation and adversarial validation are non-negotiable.

9. **Parallel execution is force multiplier**: Up to 90% time reduction through parallel tool calling and parallel subagent execution.

10. **Self-learning improves over time**: AutoResearchClaw's lesson extraction with 30-day decay enables continuous improvement across runs.

---

## 8. Next Steps

Based on these findings, the following plans will be developed:

1. **12-swarm-fleet-channels.md** — §4.13: Parallel execution, channel-based comms, shared context
2. **13-full-autonomy.md** — §4.14: Continuous-operation loop, goal-driven
3. **14-deep-research.md** — §4.15: Self-organizing research teams, AutoScientists pattern
4. **18-rmux-rebuild.md** — §5.1: Clean-room rebuild of rmux capabilities for Lyra
5. **19-multi-tenancy.md** — §5.2: AgentsMesh evaluation, pros/cons, recommendation

Each plan will synthesize these research findings into actionable implementation roadmaps for Lyra.
