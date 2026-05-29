# Lyra Upgrade Architecture: Research Synthesis

> Deep research across tmux, cmux, rmux, alphaclaw, AgentsMesh, AutoScientists, and Claude Code Dynamic Workflows.
> Goal: Extract architectural patterns to upgrade Lyra into a production-grade multi-agent orchestration system.

---

## Table of Contents

1. [Current State: Lyra's Architecture Today](#1-current-state-lyras-architecture-today)
2. [What We Can Learn from tmux](#2-what-we-can-learn-from-tmux)
3. [What We Can Learn from cmux / rmux / alphaclaw](#3-what-we-can-learn-from-cmux--rmux--alphaclaw)
4. [Multi-Tenancy Analysis: AgentsMesh + Keyword Model](#4-multi-tenancy-analysis-agentsmesh--keyword-model)
5. [Self-Organizing Teams: AutoScientists](#5-self-organizing-teams-autoscientists)
6. [Claude Code Dynamic Workflows: The Convergence Model](#6-claude-code-dynamic-workflows-the-convergence-model)
7. [Synthesized Upgrade Architecture](#7-synthesized-upgrade-architecture)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Risk Analysis & Tradeoffs](#9-risk-analysis--tradeoffs)

---

## 1. Current State: Lyra's Architecture Today

### Strengths

| Dimension | Status |
|-----------|--------|
| **Vision** | Comprehensive AGI system spanning 96 packages across agent orchestration, memory, reasoning, safety, self-evolution |
| **Core loop** | Production-quality `AgentLoop` (Hermes-inspired) with plugin hooks, budget enforcement, HIR observability |
| **Memory** | 50+ modules: ultra-memory, dream consolidation, graph stores, symbolic SSM, dual encoding, gossip consensus |
| **Safety** | 6-layer Parallax, ContinuousGuard, PermissionBridge, HIR audit trail, AgentShield (102 rules) |
| **UI** | Dual-language: Python runtime + TypeScript/React/Ink TUI with 40+ components, 25 themes |
| **Self-evolution** | GEPA v2, Meta-Harness, AEvo, PRISM pipeline with research paper citations |

### Critical Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| **5 duplicate agent hierarchies** | CRITICAL | No shared Agent base class across `src/agents/`, `lyra-core`, `lyra-agent-swarm`, `lyra-pentest`, `lyra-orchestration` |
| **Vision-reality gap** | HIGH | ARCHITECTURE.md describes a system far beyond what's implemented |
| **No real multi-agent parallelism** | HIGH | Fleet/colony patterns are dataclass simulations, not actual parallel execution |
| **Pentest isolation** | HIGH | lyra-pentest is completely standalone, shares no abstractions with core |
| **Python/JS boundary complexity** | MEDIUM | TUI requires both runtimes; startup latency and failure modes are complex |
| **No integration testing** | MEDIUM | 96 packages with no cross-package integration verification |
| **Package sprawl** | MEDIUM | Many packages are skeletal (egg-info/PYcache without substantive implementation) |

---

## 2. What We Can Learn from tmux

### Pattern 2.1: Session/Window/Pane Containment Hierarchy

**tmux model:**
```
SERVER → SESSIONS (RB-tree) → WINLINKS → WINDOWS → PANES → SCREEN
```

Key innovations:
- **Winlink indirection**: A window can belong to multiple sessions via lightweight winlink references. The window is a shared resource; the winlink holds session-specific positioning.
- **Layout tree**: Panes are arranged in a recursive tree of layout cells (horizontal/vertical splits), not a flat list.
- **Options cascade**: Options inherit pane → window → session → global via parent pointers. Copy-on-write semantics.
- **Reference counting**: Windows and sessions are refcounted. Shared ownership is safe.

**Lyra adoption:**

```
PROJECT (session) → TEAM_MEMBERSHIPS (winlinks) → TEAMS (windows) → AGENTS (panes)
```

1. **Team membership as winlink**: A team (e.g., "Security Review Team") can participate in multiple projects. Each project has a lightweight membership record with project-specific configuration. The team's actual agent composition is independent.
2. **Topology tree for team coordination**: Replace flat agent lists with recursive coordination topology — parallel branches, sequential pipelines, fan-out/fan-in, hierarchical decomposition.
3. **Configuration inheritance**: Global defaults → Project → Team → Agent with copy-on-write. Override at any level without mutating parent defaults.
4. **MRU agent tracking**: Track most-recently-interacted agents per team via MRU stack for fast context switching.

### Pattern 2.2: Client-Server with Session Persistence

**tmux model:**
- Server daemon persists independently of clients
- Clients attach/detach via Unix socket
- Sessions survive all clients disconnecting
- Re-attachment restores full context

**Lyra adoption:**
- **Agent execution decoupled from client connections.** An agent run continues even if the human disconnects. Reconnect and resume monitoring.
- **Server-wide shared resources**: Global clipboard for inter-agent data, central event log for audit, job manager for long-running tasks.
- **Graceful shutdown**: flush → notify → disconnect → destroy → exit. No data loss on shutdown.

### Pattern 2.3: Command Queue with Deferral

**tmux model:**
- FIFO command queue (`cmdq_item`)
- `CMD_RETURN_WAIT` defers execution until external event (user input, I/O)
- `cmdq_continue()` unblocks when event arrives
- Command groups with atomic failure semantics

**Lyra adoption:**
- **Task queue with wait/continue for human-in-the-loop**: Agent emits tool-call → queue item enters WAITING → human approves → `continue()` unblocks
- **Transactional agent workflows**: Multi-step plans where step-N failure cancels steps N+1..M

### Pattern 2.4: Mode Stack for Agent Interaction Layers

**tmux model:**
- Panes have a mode stack (`TAILQ of window_mode_entry`)
- Topmost mode intercepts keys and renders its own view
- Modes stack: base → copy-mode → search-mode
- `window_mode` vtable: init, free, resize, key, key_table, command, formats

**Lyra adoption:**
- **Agent interaction layers**: Base conversation mode → Edit mode (intercept tool calls) → Review mode (audit accumulated context)
- **Pluggable agent modes**: Define an `AgentMode` protocol. New modes (debug, visualize, audit) implement the protocol without modifying agent core.

### Pattern 2.5: Control Mode as Canonical API

**tmux model:**
- `control.c` provides structured line-based protocol (`%output`, `%extended-output`, `%subscription-changed`)
- Reuses the same command dispatch as interactive use
- Per-pane output queues with fair write scheduling and backpressure (pause at 8192 bytes, resume at 512)

**Lyra adoption:**
- **API and CLI share the same command dispatch.** No separate "API layer" — the API is how the system works internally. The CLI and TUI are just clients.
- **Streaming backpressure**: Pause agent output streams when clients fall behind. Buffer recent output. Resume when caught up.

### Pattern 2.6: Format String DSL

**tmux model:**
- `#{variable}` expansion with conditionals (`#{?cond,true,false}`), comparisons, regex substitution
- Lazy-evaluated callbacks (`format_add_cb`)
- Shell command substitution via `#()` with 1s timeout and caching

**Lyra adoption:**
- **Dashboard templates**: Status bars and notifications use format strings with lazy evaluation
- **Live metric injection**: External monitoring commands run as subprocesses, output injected into format context

### Pattern 2.7: Lifecycle Hooks

**tmux model:**
- 14 built-in hook names: `after-new-session`, `before-kill-pane`, `client-attached`, etc.
- Hooks stored as array options
- `CMDQ_STATE_NOHOOKS` flag prevents recursive firing

**Lyra adoption:**
- **Agent lifecycle hooks**: `on_project_created`, `on_agent_joined_team`, `on_task_complete`, `on_client_disconnected`, `on_error`, `on_timeout`
- **User-defined hooks** stored as configuration, executed via command queue

---

## 3. What We Can Learn from cmux / rmux / alphaclaw

### Pattern 3.1: Event Bus with JSONL Persistence (cmux)

**cmux model:**
- Thread-safe singleton `CmuxEventBus`
- Bounded circular buffer (4096 events)
- Boot-scoped IDs, sequence numbers
- Subscription filtering by name/category
- Backpressure via per-subscriber queue limits (1024)
- JSONL file persistence for crash recovery
- Every event carries `origin` field

**Lyra adoption:**
- Replace fragmented event systems (HIR JSONL, orchestration event bus, colony pub/sub) with a unified `EventBus`
- JSONL persistence enables crash recovery and replay
- Boot-scoped IDs enable deterministic debugging
- Subscription filtering reduces noise for consumers

### Pattern 3.2: Workstream Items (cmux)

**cmux model:**
- Two-tier storage: in-memory ring buffer (2000) + JSONL append-only
- Items track: kind, status (pending/resolved/expired/telemetry), source, PPID, context
- `WorkstreamTransport` protocol for pluggable backends

**Lyra adoption:**
- **Unified action model**: Every agent action (tool call, permission request, question, exit plan) is a WorkstreamItem
- PPID-based auto-expiry: pending items expire when originating agent process dies
- Pluggable transport for human approval flows

### Pattern 3.3: Agent Hooks Architecture (cmux)

**cmux model:**
- Each supported agent gets an `AgentHookDef` mapping agent events → CLI subcommands
- Hook commands are generated as shell wrappers: `cmux hooks <agent> <subcommand>`
- Feed hooks with 120s timeout decouple agent event timeouts from user response time

**Lyra adoption:**
- **Third-party agent integration**: Define a hook protocol. External agents emit events. Lyra routes them to internal command dispatch.
- Timeout decoupling: long-running agent operations don't block user interaction

### Pattern 3.4: SDK-First Design (rmux)

**rmux model:**
- Three surfaces (CLI, Rust SDK, Ratatui widget) share one protocol to one daemon
- `Rmux::builder().connect_or_start()` — idempotent connection
- `EnsureSession::named(...).policy(CreateOrReuse)` — declarative session management
- `pane.wait_for_text("pattern")` with 25ms polling
- `broadcast(Input::Text(...))` with daemon-side batch + client-side fan-out fallback

**Lyra adoption:**
- **Three-surface architecture**: CLI + Python SDK + TUI widget all share one protocol
- **EnsureSession/CreateOrReuse**: Idempotent project/session management
- **`wait_for_text` pattern**: Async observation of agent output with snapshot-polling
- **Dual-path broadcast**: Daemon-side batch for homogeneous agents, client-side fan-out for heterogeneous

### Pattern 3.5: Watchdog State Machine (alphaclaw)

**alphaclaw model:**
- Lifecycle × Health state matrix:
  - `running/healthy`, `running/degraded`, `running/unknown`
  - `crashed/unhealthy`, `crash_loop/unhealthy`
  - `restarting/unknown`, `stopped/unknown`
- Startup grace period (30s), expected restart window (15s)
- Crash-loop detection: 3 crashes in 300s
- Auto-repair: `doctor --fix --yes`

**Lyra adoption:**
- **Agent process monitoring**: Every agent gets a watchdog with lifecycle×health state
- **Crash-loop detection**: 3 crashes in 5 minutes → escalate, don't restart
- **Auto-repair pipeline**: detect → diagnose → fix → verify → notify
- **Grace periods**: Distinguish intentional restarts from actual crashes

### Pattern 3.6: Incident-Based Notification Deduplication (alphaclaw)

**alphaclaw model:**
- `openIncident`/`closeIncident` prevents duplicate notifications
- `notifyOncePerIncident` suppresses repeats during active incident

**Lyra adoption:**
- Agent alerts that persist across cycles get deduplicated via incident scoping
- Incident lifecycle: open → notify → track → resolve → close

### Pattern 3.7: Agent Hibernation Lifecycle (cmux)

**cmux model:**
- States: `unknown → running → idle → needsInput → hibernating`
- Only `idle` state allows hibernation
- 16 recognized agent keys in whitelist

**Lyra adoption:**
- Resource-aware agent lifecycle: idle agents hibernate to free compute
- Whitelist gating: only recognized agent types can report lifecycle status
- Wake-on-input: hibernated agents resume when work arrives

---

## 4. Multi-Tenancy Analysis: AgentsMesh + Keyword Model

### Key Finding: "Keyword Multi-Tenant" Does Not Exist in AgentsMesh

After exhaustive analysis of the AgentsMesh codebase (1,059+ commits, 86 releases), the term "keyword multi-tenant" appears nowhere. AgentsMesh uses **hierarchical organization-level isolation** with X.509 certificate-based identity, not keyword-based routing.

### How AgentsMesh Actually Works

| Layer | Mechanism |
|-------|-----------|
| **Tenant isolation** | `Organization > Team > User` hierarchy with row-level PostgreSQL isolation |
| **Request routing** | Consistent hashing on `X-Organization-ID` header |
| **Runner identity** | X.509 certificates with Org slug in Subject Organization field, mTLS for all gRPC |
| **Agent discovery** | Centralized `ListAgents` RPC — built-in agents (platform-wide) + custom agents (org-scoped) |
| **Agent communication** | Centralized `MeshMessageService` with `correlation_id` chains, no P2P routing |
| **"Mesh" topology** | Logical projection, not network mesh. Cross-instance communication = 0 by design |

### The "Keyword" Part: Agentfile DSL

Keywords in AgentsMesh are purely about **per-pod runtime configuration**:
```
AGENT claude-code
CONFIG model = "opus"
PROMPT "Fix the login bug"
MODE acp
```

These keywords configure individual agent pods at creation time. They are NOT used for routing, partitioning, or tenant isolation.

### Recommendation: Two-Layer Model for Lyra

**Do NOT implement keyword-based multi-tenancy for isolation. DO implement keyword-based capability routing.**

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| **Hard isolation** | Project-level scoping (hierarchical ID) | Security, data isolation, billing, audit |
| **Soft routing** | Keyword-based capability labels | Agent discovery, task routing, team formation |

**Hard isolation layer:**
```
Project → Team → Agent
```
- Every agent context explicitly scoped to a Project
- Data stores use project-scoped row-level isolation
- Scheduling uses project ID for cache affinity
- Each project gets its own key namespace

**Soft routing layer (within a project):**
```yaml
agent:
  id: "agent-frontend-01"
  project: "lyra"           # Hard boundary
  capabilities:              # Soft routing keywords
    - "skill:code-review"
    - "skill:django-migration"
    - "domain:auth-ui"
```

### Pros/Cons of Keyword Multi-Tenancy

#### Pros
- Dynamic team formation via capability matching
- Multi-dimensional routing (project, capability, priority)
- Simplified provisioning (one instance, many projects)
- Natural capability advertising by agents
- Resource pooling across keyword-scoped teams

#### Cons (Why NOT for isolation)
- **Keywords are advisory, not cryptographic.** A bug in keyword matching leaks data between tenants.
- **Keyword collision is inevitable.** `project:lyra` could mean multiple things at scale.
- **No natural revocation model.** Removing a keyword badge doesn't terminate existing connections.
- **Matching complexity.** Simple equality → regex → glob → priority-based matching, each with edge cases.
- **Observability debt.** Debugging "why did this message go to THAT agent?" becomes keyword tree traversal.
- **No natural sharding.** Multi-keyword agents exist in multiple virtual partitions simultaneously.
- **Performance contention.** All keyword matches compete for the same routing table and cache.

**Verdict:** Strong NO on keyword-based isolation. Strong YES on keyword-based capability routing within hard project boundaries.

---

## 5. Self-Organizing Teams: AutoScientists

AutoScientists (Gao, Fang, Zitnik, Harvard 2026) is the most architecturally significant reference. It demonstrates that decentralized agent teams outperform hierarchical ones for long-running scientific research.

### Core Architecture

```
Shared State S = {
    champion: p*           (current best config)
    experiment_log: L      (all experiments, immutable)
    discussion_forum: F    (structured posts with states)
    per_team_queues: Qk    (proposed experiments)
    dead_end_registries: Dk (failed directions, cross-team readable)
}

Heartbeat: agents read S → act → write back
```

### Pattern 5.1: Hypothesis-Based Team Formation

**Not axis-based, not role-based.** Teams form around falsifiable hypotheses about system bottlenecks.

Example from GPT training optimization:
- Team A: "Throughput is the bottleneck" (H-throughput)
- Team B: "Gradient quality is degrading" (H-gradient-quality)
- Team C: "Model capacity is saturated" (H-capacity)

Every team can propose experiments on any axis. Only the evaluative lens differs. When hypothesis is falsified (3+ DISCARDs, 0 KEEPs, age ≥ 3 rotations), the team reforms.

**Ablation result:** Removing self-organization degrades performance significantly (GPT nanochat val_bpb: 0.9777 → 0.9833).

**Lyra adoption:**
- Replace fixed agent roles with hypothesis-driven team formation
- Teams form around competing hypotheses about the current bottleneck
- Every agent can propose on any dimension; teams differ in evaluative lens
- Falsified hypotheses trigger automatic team reformation

### Pattern 5.2: Discussion-Before-Queuing Gate

Every experiment MUST start as a `[PROPOSAL]` post. At least 1 team member must comment before it enters the work queue. This is peer review before resource allocation.

Proposal must include: axis/direction/value, prior results, why it's different from prior work, confidence with delta range.

**Lyra adoption:**
- Every significant agent action requires a proposal with ≥1 non-author review before execution
- Prevents wasted compute on poorly-thought-out tasks
- Proposal template enforces structured reasoning

### Pattern 5.3: Collective Failure Memory (Dead-End Registry)

All teams share `dead_ends.md`. When a direction reaches 3+ DISCARDs and 0 KEEPs, it's formally ruled out. Noise-contaminated entries are flagged (`NOISE-CONTAMINATED`) rather than discarded.

**Ablation result:** Removing shared state produced "the largest proportional drop" — Cell-Cell Communication odds ratio 0.924 → 0.435. This is the single most critical architectural component.

**Lyra adoption:**
- Cross-team dead-end registry prevents redundant exploration
- Noise-contaminated failures are flagged, not discarded
- Patterns extracted from both successes AND failures

### Pattern 5.4: Noise-Gated Confirmation

Every KEEP (successful result) requires confirmation at a different random seed before promotion. Noise floor is empirically calibrated from accumulated data, not hardcoded.

**Lyra adoption:**
- Multi-seed confirmation for agent outputs before promotion to "verified"
- Empirical noise calibration from accumulated results
- Near-delta results without second confirmation are demoted

### Pattern 5.5: Self-Triggered Reorganization

Agents detect stagnation themselves:
- `rotations_since_keep >= 3`
- Concentrated axis-mining (8+ DISCARDs in ≤3 axes)
- All hypotheses falsified

Agents vote `[DISCUSS-MORE]` or `[DISCUSS-DONE]`. When ≥5 vote DONE, the alphabetically-last analyst writes a new team roster.

**Lyra adoption:**
- Agents autonomously detect stagnation and trigger reorganization
- Voting-based consensus for structural changes
- No central planner needed for rebalancing

### Pattern 5.6: Meta-Improvement Loop

Every 3 cycles, the orchestrator pauses, examines evidence, forms a diagnosis, and makes **exactly one targeted change** to agent role templates.

Rules:
- Must edit a real file (not just write a report)
- Root cause must be identified from evidence
- Pattern library: high_duplicates, low_activation, slow_propagation, low_keep_rate
- Off-limits: agent workspaces, logs, champion code

**Lyra adoption:**
- Periodic self-improvement cycles
- One targeted change per cycle (prevents thrashing)
- Pattern library for common failure modes
- Evidence-gated: no change without diagnosis

### Pattern 5.7: Atomic Claim-Based Coordination

Use `If-Match` for safe concurrent queue access. Never use PATCH on nested YAML (corrupts lists). Baseline runs use `If-None-Match: *` for atomic first-claimer coordination.

**Lyra adoption:**
- Optimistic concurrency for shared agent queues
- `If-Match` / `If-None-Match` for safe concurrent state access
- Avoid nested YAML/JSON mutations

### Pattern 5.8: Discovery-Based File Access

Agents LIST workspace file metadata (~50 tokens) and decide what to read. No hardcoded file checklists. Self-documenting paths so filename alone tells agents if it's relevant.

**Lyra adoption:**
- Agents discover context via cheap metadata listing, not rigid checklists
- Self-documenting file paths reduce need for directory documentation
- Reduces token waste on reading irrelevant context

---

## 6. Claude Code Dynamic Workflows: The Convergence Model

Anthropic's April 2026 dynamic workflows represent the industrial-scale version of multi-agent orchestration:

### Key Patterns

1. **Task → Workflow Decomposition**: The system generates workflow scripts that divide a problem into subtasks, then spawns 10s-100s of parallel subagents.
2. **Adversarial Verification**: Some agents attempt fixes. Others act adversarially, trying to break the proposed solution. The system iterates until answers "converge."
3. **Cross-Checking**: Multiple independent attempts at the same problem, then cross-validation. This is how senior engineering teams work.
4. **Resumability**: Workflows that get interrupted pick up where they left off. Work can run for days, not sessions.
5. **Managerial Automation**: The human defines goals and constraints. The AI plans, delegates, verifies, retries, and coordinates internally.

### Bun Migration Case Study
- 750,000 lines of code (Zig → Rust)
- Hundreds of parallel agents
- 99.8% of existing test suite still passed
- Work that would take a team months, done in days

### Implications for Lyra

- **Adversarial review as first-class primitive.** Every agent output should face an adversarial reviewer before acceptance.
- **Convergence as stopping condition.** Not "agent finished" but "independent agents agree."
- **Resumability by default.** Long-running agent workflows must survive process restarts.
- **Scale economics.** Token burn is high, but timeline compression justifies it for high-value tasks.

---

## 7. Synthesized Upgrade Architecture

### 7.1 Unified Containment Hierarchy

```
LYRA_SERVER (daemon)
  └── PROJECTS (isolated workspaces)
        └── TEAM_MEMBERSHIPS (winlink indirection)
              └── TEAMS (shared agent groups)
                    └── TOPOLOGY_TREE (coordination structure)
                          └── AGENTS (individual agents)
                                └── MODE_STACK (interaction layers)
```

**Key properties:**
- **Projects are hard isolation boundaries** (separate keys, data stores, audit logs)
- **Teams are reusable across projects** via membership indirection
- **Topology tree** defines coordination pattern (parallel, sequential, DAG, debate)
- **Mode stack** allows per-agent interaction layer customization

### 7.2 Unified Agent Protocol

Replace 5 duplicate agent hierarchies with ONE protocol:

```python
class AgentProtocol(Protocol):
    """Every agent in Lyra implements this protocol."""

    # Identity
    agent_id: str
    project_id: str
    capabilities: set[str]  # keyword labels for soft routing

    # Lifecycle
    async def initialize(self, config: AgentConfig) -> None: ...
    async def run(self, task: Task) -> TaskResult: ...
    async def shutdown(self) -> None: ...

    # Interaction modes
    def push_mode(self, mode: AgentMode) -> None: ...
    def pop_mode(self) -> AgentMode: ...

    # Observation
    @property
    def state(self) -> AgentState: ...  # lifecycle × health
    @property
    def metrics(self) -> AgentMetrics: ...
```

**Migration path:**
1. Define `AgentProtocol` in `lyra-core`
2. Implement adapter wrappers for existing agent systems
3. New agents implement the protocol directly
4. Deprecate old ABCs over time

### 7.3 Event-Driven Architecture

Inspired by cmux's event bus:

```
┌──────────────────────────────────────────────────┐
│                  EVENT BUS                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Publisher │  │ Publisher │  │ Publisher     │   │
│  │ (Agent A) │  │ (Agent B) │  │ (Watchdog)    │   │
│  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘   │
│        │               │               │           │
│  ┌─────▼───────────────▼───────────────▼───────┐   │
│  │         Circular Buffer (4096 events)        │   │
│  │         + JSONL Crash Recovery              │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                               │
│  ┌──────────────────▼──────────────────────────┐   │
│  │         Subscription Router                  │   │
│  │   (filter by event_type, agent_id, project)  │   │
│  └─────┬──────────────┬──────────────┬─────────┘   │
│        │              │              │              │
│  ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐      │
│  │Subscriber │  │Subscriber │  │Subscriber │       │
│  │ (TUI)     │  │ (Webhook) │  │ (Audit)   │       │
│  └───────────┘  └───────────┘  └───────────┘       │
└──────────────────────────────────────────────────┘
```

### 7.4 Workstream-Based Action Model

Inspired by cmux's workstream items:

```python
@dataclass
class WorkstreamItem:
    id: str
    kind: ItemKind  # TOOL_CALL, PERMISSION, QUESTION, EXIT_PLAN, TELEMETRY
    status: ItemStatus  # PENDING, APPROVED, REJECTED, EXPIRED, RESOLVED
    source: AgentRef
    ppid: int  # auto-expire on process death
    context: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None
```

### 7.5 Command Queue with Deferral

Inspired by tmux's command queue:

```
┌─────────────────────────────────────────┐
│           COMMAND QUEUE (FIFO)           │
│                                          │
│  [cmd_1] → [cmd_2] → [WAITING] → [cmd_4]│
│                          │               │
│                     Human approves       │
│                          │               │
│  [cmd_1] → [cmd_2] → [cmd_3] → [cmd_4]  │
│                                          │
│  Group: [cmd_2, cmd_3, cmd_4]            │
│  If cmd_3 fails → cmd_4 cancelled        │
└─────────────────────────────────────────┘
```

### 7.6 Agent Watchdog

Inspired by alphaclaw's watchdog:

```
Lifecycle × Health State Matrix:

                    healthy    degraded    unknown
    running           ✓           ⚠           ?
    idle              ✓           ⚠           ?
    needs_input       ✓           -           ?
    hibernating       ✓           -           ?
    restarting        -           -           ?
    crashed            ✗          ✗           ✗
    crash_loop         ✗✗         ✗✗          ✗✗
    stopped           --          --          --

Crash-loop detection: 3 crashes in 300s → escalate
Auto-repair: detect → diagnose → fix → verify → notify
```

### 7.7 Self-Organizing Team System

Inspired by AutoScientists:

```
┌─────────────────────────────────────────────────────┐
│                  SHARED STATE S                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Champion │ │Experiment│ │   Discussion Forum   │ │
│  │   p*     │ │  Log L   │ │         F            │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────┐ ┌──────────────────────────────────┐  │
│  │  Queues  │ │     Dead-End Registries Dk       │  │
│  │    Qk    │ │   (cross-team readable)           │  │
│  └──────────┘ └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         ▲              ▲              ▲
         │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ Team A  │    │ Team B  │    │ Team C  │
    │H-thruput│    │H-grad   │    │H-capacity│
    └─────────┘    └─────────┘    └─────────┘

Heartbeat: read S → act → write back
```

**Team lifecycle:**
1. **Bootstrap**: Cold-start `[DISCUSSION-TRIGGER]` post
2. **Discuss**: Agents propose, critique, rank hypotheses
3. **Form**: ≥5 `[DISCUSS-DONE]` votes → write roster.md
4. **Execute**: Teams propose experiments via `[PROPOSAL]` posts with ≥1 review
5. **Adapt**: Stagnation detected → self-triggered re-discussion
6. **Falsify**: Hypothesis falsified (3+ DISCARDs, 0 KEEPs, age ≥3) → team reforms
7. **Meta-Improve**: Every 3 cycles, one targeted change to agent templates

### 7.8 Adversarial Review Gate

Inspired by AutoScientists + Claude Code Dynamic Workflows:

```
Agent Output → [Adversarial Reviewer] → [Validator] → [Convergence Check]
                    │                      │                │
                    ▼                      ▼                ▼
              Finds weaknesses      Checks correctness   Are 3 agents
              Attacks assumptions    Runs tests          in agreement?
                    │                      │                │
                    └──────────────────────┴────────────────┘
                                           │
                                     All pass → Accept
                                     Any fail → Revise
```

### 7.9 Three-Surface Interface

Inspired by rmux:

```
┌──────────────────────────────────────┐
│            LYRA PROTOCOL              │
│    (typed messages over WebSocket     │
│     + gRPC for performance paths)     │
└────────┬──────────┬──────────┬────────┘
         │          │          │
    ┌────▼────┐ ┌───▼───┐ ┌───▼──────┐
    │   CLI   │ │  SDK  │ │ TUI/Web  │
    │ (Typer) │ │(Python│ │ (Ink/    │
    │         │ │ async)│ │  React)  │
    └─────────┘ └───────┘ └──────────┘
```

**Key principle:** CLI, SDK, and UI share the same protocol. Anything one surface can do, the others can replicate.

### 7.10 Resumable Workflows

Inspired by tmux session persistence + Claude Code Dynamic Workflows:

- Agent state checkpointed every N steps (configurable, default 10)
- Checkpoint includes: conversation history, tool results, agent state, queue position
- On restart: restore from latest checkpoint, replay events since checkpoint
- Stale claims auto-released after timeout
- Heartbeat-based liveness detection

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)

**Goal:** Unify agent abstractions and establish event-driven architecture.

| Step | Description | Source Pattern |
|------|-------------|---------------|
| 1.1 | Define `AgentProtocol` in `lyra-core` | tmux pane model + cmux hooks |
| 1.2 | Implement unified `EventBus` with JSONL persistence | cmux |
| 1.3 | Build adapter wrappers for existing agent systems | — |
| 1.4 | Implement `WorkstreamItem` model | cmux |
| 1.5 | Deprecate duplicate ABCs, migrate to Protocol | — |

### Phase 2: Containment Hierarchy (Weeks 5-8)

**Goal:** Implement tmux-inspired project/team/agent hierarchy.

| Step | Description | Source Pattern |
|------|-------------|---------------|
| 2.1 | `Project` as hard isolation boundary | AgentsMesh |
| 2.2 | `Team` as reusable agent group with winlink indirection | tmux |
| 2.3 | `TopologyTree` for coordination structure | tmux layout tree |
| 2.4 | Configuration inheritance (Project → Team → Agent) | tmux options cascade |
| 2.5 | `ModeStack` for agent interaction layers | tmux mode stack |

### Phase 3: Command & Control (Weeks 9-12)

**Goal:** Implement command queue, deferral, and three-surface interface.

| Step | Description | Source Pattern |
|------|-------------|---------------|
| 3.1 | FIFO command queue with `CMD_RETURN_WAIT` | tmux |
| 3.2 | Command groups with atomic failure | tmux |
| 3.3 | Unified protocol (CLI + SDK + UI) | rmux |
| 3.4 | Agent Watchdog with lifecycle×health matrix | alphaclaw |
| 3.5 | Crash-loop detection and auto-repair | alphaclaw |

### Phase 4: Self-Organizing Teams (Weeks 13-18)

**Goal:** Implement AutoScientists-inspired decentralized team system.

| Step | Description | Source Pattern |
|------|-------------|---------------|
| 4.1 | Shared state S (champion, log, forum, queues, dead-ends) | AutoScientists |
| 4.2 | Discussion forum with structured posts | AutoScientists |
| 4.3 | Hypothesis-based team formation | AutoScientists |
| 4.4 | Discussion-before-queuing gate | AutoScientists |
| 4.5 | Collective failure memory (dead-end registry) | AutoScientists |
| 4.6 | Noise-gated confirmation | AutoScientists |
| 4.7 | Self-triggered reorganization | AutoScientists |
| 4.8 | Meta-improvement loop (every 3 cycles) | AutoScientists |

### Phase 5: Adversarial Review & Convergence (Weeks 19-22)

**Goal:** Implement multi-agent verification and convergence.

| Step | Description | Source Pattern |
|------|-------------|---------------|
| 5.1 | Adversarial reviewer agent role | AutoScientists + Claude DW |
| 5.2 | Validator agent role | Claude DW |
| 5.3 | Convergence check (N independent agents agree) | Claude DW |
| 5.4 | Resumable workflows with checkpointing | Claude DW + tmux |

### Phase 6: Production Hardening (Weeks 23-26)

**Goal:** Production readiness.

| Step | Description | Source Pattern |
|------|-------------|---------------|
| 6.1 | Streaming backpressure (pause/resume) | tmux control mode |
| 6.2 | Incident-based notification deduplication | alphaclaw |
| 6.3 | Agent hibernation for resource management | cmux |
| 6.4 | Integration tests across all packages | — |
| 6.5 | Performance benchmarks and optimization | — |

---

## 9. Risk Analysis & Tradeoffs

### Risk 1: Migration Complexity

**Risk:** 5 existing agent hierarchies must be migrated to `AgentProtocol`.
**Mitigation:** Adapter pattern — wrap existing agents, don't rewrite them. Deprecate old ABCs over multiple releases.
**Severity:** MEDIUM

### Risk 2: Event Bus Performance

**Risk:** Unified event bus becomes bottleneck at scale (100s of agents).
**Mitigation:** shard by project_id, use consistent hashing. Per-project event buses for isolation.
**Severity:** LOW (addressable with standard scaling patterns)

### Risk 3: Self-Organization Instability

**Risk:** Decentralized teams may thrash (form/reform endlessly) or converge on local optima.
**Mitigation:** Minimum team lifetime (≥3 cycles before reformation allowed). Meta-improvement loop detects thrashing patterns. Human override for team structure.
**Severity:** MEDIUM

### Risk 4: Token Economics

**Risk:** Adversarial review and multi-agent convergence multiply token usage by 3-5x.
**Mitigation:** Tiered review depth (quick for low-risk, deep for critical). Model routing: haiku for initial review, sonnet for depth, opus for convergence arbitration.
**Severity:** MEDIUM (manageable with tiered routing)

### Risk 5: Complexity Budget

**Risk:** Adding tmux hierarchy + cmux event bus + AutoScientists teams + Claude DW convergence simultaneously creates integration complexity.
**Mitigation:** Phased rollout (see Roadmap). Each phase is independently valuable and testable. No phase depends on future phases being perfect.
**Severity:** HIGH (requires disciplined phasing)

---

## Appendix A: Key Files Referenced

### tmux
- `tmux.h` — Core data structures (session, window, pane, client, options, etc.)
- `server.c` — Event loop, accept, signal handling, shutdown
- `client.c` — Client connect, identification, attach/detach
- `cmd-queue.c` — FIFO command queue, CMD_RETURN_WAIT, group semantics
- `control.c` — Control mode protocol, fair write scheduling, backpressure
- `session.c` — Session lifecycle, last-window stack
- `window.c` — Window/pane management, active tracking, reference counting
- `options.c` — Options RB-tree, parent-pointer inheritance, copy-on-write
- `layout.c` — Recursive layout tree, resize propagation
- `key-bindings.c` — Key tables, mode switching, prefix key
- `notify.c` — 14 lifecycle hooks, control mode notifications
- `format.c` — Format DSL, conditionals, lazy callbacks

### cmux (manaflow-ai)
- `CmuxEventBus` — Thread-safe pub/sub with JSONL persistence
- `WorkstreamSystem` — Two-tier item storage (ring buffer + JSONL)
- `AgentHookDef` — Third-party agent integration protocol
- `AgentHibernationLifecycle` — Resource-aware lifecycle states

### rmux (Helvesec)
- `rmux-proto` — Wire protocol (70+ request/response variants)
- `rmux-sdk` — Async/await SDK with `EnsureSession` policies
- `rmux-ipc` — Unix socket + Windows Named Pipe transport
- `rmux-core` — Session, pane, layout, hooks, buffers, formats

### alphaclaw (chrysb)
- Gateway manager — Child process lifecycle with watchdog
- Watchdog state machine — Lifecycle × Health matrix
- Incident deduplication — `openIncident`/`closeIncident` pattern
- Prompt hardening — Anti-drift system prompt injection

### AgentsMesh
- Proto definitions — `Organization > Team > User` hierarchy
- Backend consistent hashing — `X-Organization-ID` routing
- Runner X.509 identity — Certificate-based mTLS auth
- Agentfile DSL — Keyword-based per-pod configuration
- MeshMessageService — Centralized agent communication

### AutoScientists (Harvard)
- `HEARTBEAT.md` — Master agent boot protocol (5 branches)
- `ROLE-ANALYST.md` — Propose, discuss, prune, stagnate-detect
- `ROLE-GPU.md` — Claim, train, confirm, record
- `ROLE-TEAM.md` — LIST→DECIDE→READ, queue management
- `runbook.md` — Orchestrator loop (6 steps, 13 hooks)
- `SKILL.md` — Multi-agent coordination mechanics
- `META-IMPROVEMENT.md` — Self-improvement protocol

---

## Appendix B: Anti-Patterns to Avoid

1. **Axis-based team partitioning** (from AutoScientists ablation): Assigning teams to fixed axes (arch/optim/sched) causes the highest-leverage experiment to sit in the wrong queue. Always use hypothesis-based team formation.

2. **Pure keyword tenancy** (from AgentsMesh analysis): Keywords are advisory labels, not security boundaries. Always use hierarchical scoping for isolation.

3. **Separate API layer** (from tmux design philosophy): The control mode IS the command dispatch. Don't build a separate API — make the API the native protocol.

4. **Fixed agent roles** (from AutoScientists): Fixed roles prevent adaptation when the productive research direction shifts. Use self-organizing teams with periodic reformation.

5. **Central planner as science director** (from AutoScientists): The orchestrator should be a pure lifecycle manager (launch, harvest, promote, release). Never let it decide what to research.
