# Brainstorm: rmux Clean-Room Rebuild (§5.1)

## Sources Reviewed

### Terminal Multiplexers (§3.8)
- **tmux**: Mature C-based multiplexer; client-server architecture; pane/window/session hierarchy; detached sessions; scripted commands via tmux CLI
- **cmux**: Modern multiplexer; AI-friendly APIs; structured output capture
- **rmux**: Rust-based modern alternative; focus on performance + extensibility; structured event stream
- **Warp**: GPU-rendered terminal; blocks (command + output groupings); Workflows feature; AI integration
- **alphaclaw**: Multi-agent terminal coordination; agent-per-pane model

### AgentsMesh (§3.8, also §5.2)
- Multi-tenant agent coordination over message bus
- Pane-as-agent paradigm
- Cross-agent event channels

### Dynamic Workflows (§3.12)
- Code-driven fan-out without round-trips
- Independent agents on same problem, then convergence
- Resumable long-runs

### Claude Code Agent Teams (§3.1)
- Parallel agents with shared task list
- Per-agent context isolation
- Team coordination via inter-agent messages

---

## Cross-Source Breakthrough Ideas

### Idea 1: **Agent-Aware Pane Lifecycle with Snapshot Replay**

**Sources Combined**:
- rmux structured event stream
- Warp blocks (command + output as discrete units)
- Claude Code background tasks + Monitor tool
- Memory architecture (§4.2 — episodic snapshots)
- Tool provenance (from §4.6 brainstorm)

**Mechanism**:
Each pane is a **typed agent runtime** with:
1. **Lifecycle events**: spawn, ready, working, idle, blocked, completed, crashed
2. **Block-level snapshots**: each command + output forms a discrete, replayable block
3. **State capture**: at any point, snapshot pane's full state (cwd, env, scrollback, running process)
4. **Cross-pane channels**: typed message passing between panes (typed = schema-validated)

```
Pane Spawn
    ↓
[Block 1] $ npm install ↓ output captured ↓ event: command_complete
    ↓
[Block 2] $ npm test    ↓ output captured ↓ event: tests_failed
    ↓ (snapshot taken automatically on failure)
[Block 3] $ /agent diagnose ↓ agent reads snapshot, fixes code
    ↓
[Block 4] $ npm test    ↓ output captured ↓ event: tests_passed
```

**Snapshot Replay**:
- Reproduce any past pane state for debugging
- Branch from a snapshot: "what if we had taken different path?"
- Share snapshots across machines (portable state)

**Why It Beats Individual Sources**:
- tmux: No snapshots, no event stream, no agent awareness
- Warp blocks: UI only, no programmatic replay
- rmux: Events but no agent lifecycle
- **Fusion**: Agent + block + snapshot + channels = debuggable, branchable, shareable agent terminals

**Impact × Effort**: 5×4 = BREAKTHROUGH

**Failure Modes**:
- Snapshot storage growth
- Replay across changing filesystem state
- Schema evolution for typed channels

---

### Idea 2: **Multi-Agent Pane Choreography via Workflow DSL**

**Sources Combined**:
- Dynamic Workflows (code-driven fan-out)
- Claude Code Agent Teams (parallel coordination)
- alphaclaw multi-agent terminal patterns
- AgentsMesh cross-agent channels
- Goose Recipes (saved workflows)

**Mechanism**:
A declarative **Pane Workflow DSL** (`.lyra/workflows/*.yaml`) that orchestrates multi-pane agent flows:

```yaml
workflow: parallel-research
description: 3 agents research same topic, converge to single report

panes:
  - id: researcher-academic
    agent: research-agent
    instructions: "Focus on academic sources (arxiv, scholar)"
    inputs: {topic: "${topic}"}

  - id: researcher-industry
    agent: research-agent
    instructions: "Focus on industry sources (blogs, repos, products)"
    inputs: {topic: "${topic}"}

  - id: researcher-community
    agent: research-agent
    instructions: "Focus on community discussions (forums, Discord)"
    inputs: {topic: "${topic}"}

  - id: synthesizer
    agent: writer-agent
    waits_for: [researcher-academic, researcher-industry, researcher-community]
    instructions: "Synthesize into single report, flag contradictions"
    inputs:
      academic: "${researcher-academic.report}"
      industry: "${researcher-industry.report}"
      community: "${researcher-community.report}"

  - id: critic
    agent: critic-agent
    waits_for: [synthesizer]
    instructions: "Find weak claims, demand citations"
    inputs: {report: "${synthesizer.output}"}

  - id: synthesizer-round2
    agent: writer-agent
    waits_for: [critic]
    instructions: "Address critic's concerns"
    inputs:
      report: "${synthesizer.output}"
      critique: "${critic.output}"

outputs:
  final_report: "${synthesizer-round2.output}"
  research_artifacts: ["${researcher-academic.report}", ...]
```

**Runtime**:
- Spawns 6 panes in coordinated sequence
- Manages dependencies and data flow
- Shows live progress in single dashboard pane
- Persists workflow state for resumption

**Why It Beats Individual Sources**:
- Dynamic Workflows: Code-driven but not pane-aware
- Agent Teams: No declarative DSL
- alphaclaw: Multi-agent but ad-hoc
- AgentsMesh: Channels but no workflow
- Goose Recipes: Single-pane recipes
- **Fusion**: Declarative + multi-pane + agent-aware + resumable

**Impact × Effort**: 5×4 = BREAKTHROUGH

**Failure Modes**:
- DSL complexity could rival full programming
- Workflow debugging is hard
- Resource exhaustion with many panes

---

### Idea 3: **Headless Pane API for Programmatic Agent Coordination**

**Sources Combined**:
- tmux CLI (scriptable command interface)
- rmux structured event stream
- AgentsMesh message bus
- Claude Code TaskCreate/SendMessage tools
- MCP tool exposure pattern

**Mechanism**:
Expose pane operations as **first-class MCP tools** so any agent (in any pane or external) can:

```
mcp://lyra-rmux/
  ├── pane_list                       # List all panes
  ├── pane_create(workflow=..., ...)  # Spawn new pane
  ├── pane_send_input(pane_id, text)  # Send keystrokes
  ├── pane_read_output(pane_id, since=...)  # Read scrollback
  ├── pane_snapshot(pane_id)          # Capture full state
  ├── pane_kill(pane_id)              # Terminate pane
  ├── channel_subscribe(name)         # Subscribe to typed channel
  ├── channel_publish(name, msg)      # Publish to typed channel
  └── workflow_run(name, inputs)      # Execute workflow DSL
```

**Use Cases**:
- External monitoring dashboards
- CI/CD that orchestrates Lyra panes
- Cross-machine pane management
- Programmatic regression testing of agent workflows

**Why It Beats Individual Sources**:
- tmux CLI: Bash-only, not structured
- rmux events: Read-only, no programmatic control
- AgentsMesh: Channels only, no full pane control
- **Fusion**: MCP-native pane API = any agent/external tool can orchestrate Lyra

**Impact × Effort**: 4×3 = HIGH

**Failure Modes**:
- Security concerns (who can spawn panes?)
- Permission model complexity
- Race conditions with multiple controllers

---

## Parked Ideas (Future Runs)

### Idea 4: **GPU-Accelerated Terminal Rendering**
Inspired by Warp — render terminal with GPU for smooth scrollback, semantic highlighting, agent status overlays. High effort, lower priority than functionality.

### Idea 5: **Distributed Panes Across Machines**
Panes that run on remote hosts but appear in local multiplexer. SSH-like but agent-aware. Useful for cloud GPU work.

### Idea 6: **Time-Travel Debugging**
Step backward/forward through any pane's history. Branch into "what-if" scenarios. Powerful but storage-heavy.

---

## Promoted to Plan (B) Breakthrough Tier

**Primary**: Idea 1 (Agent-Aware Pane Lifecycle with Snapshot Replay) — Foundation for all other improvements; uniquely enables debugging and reproducibility

**Secondary**: Idea 2 (Multi-Agent Pane Choreography DSL) — Highest leverage for power users; differentiates Lyra from any terminal multiplexer

These two fuse to make rmux a **first-class multi-agent orchestration platform** rather than just a terminal multiplexer.
