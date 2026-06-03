# Guide: Fleet Orchestration

> 📖 Guide — Run multiple agents in parallel with DAG teams, worktree isolation, and the supervisor daemon. Learn to dispatch, monitor, and coordinate fleets.

When a task exceeds single-agent capacity, Lyra escalates to fleet orchestration -- a supervisor daemon that manages multi-agent DAG workflows with filesystem isolation.

---

## Dispatch

### How to Start a Fleet

```bash
# Background session (L3+ unattended)
lyra --bg "Analyze all modules for security vulnerabilities"

# During active session
# Use /bg to send current task to background
# Use /model deepseek-chat --effort ultracode to force fleet mode
```

The dispatcher creates subagents with worktree isolation:

```bash
git worktree add -b sess-abc123 .lyra/worktrees/sess-abc123 main
```

Each subagent runs in its own git worktree -- a lightweight linked copy of the repo. Concurrent sessions edit the same repo without conflicts. The worktree pool enforces a default max of 10 concurrent (configurable), reclaiming the oldest paused session when exhausted.

### DAG Teams

The fleet organizes work as a directed acyclic graph (DAG). Independent nodes run in parallel waves; dependent nodes sequence automatically:

| Topology | Use Case |
|---|---|
| Linear | Research -> Design -> Implement -> Test |
| Fan-out | Analyze 4 modules simultaneously |
| Map-reduce | Process chunks, merge results |
| Diamond | Two approaches, compare winners |
| Gate | If tests pass, deploy; else fix |

Each node is a worker with a role: Analyst, Experimenter, Critic, or Synthesizer. Nodes produce results stored in script variables (not the LLM context window), preventing context pollution.

---

## Monitor

### Fleet View

```bash
lyra fleet
```

Opens the fleet view TUI. Sessions are grouped by state:

```
ACTIVE      | sess-abc123 | auth-module-review     | 12 steps, $0.34
ACTIVE      | sess-abc456 | db-schema-audit        | 8 steps, $0.21
PAUSED      | sess-abc789 | cache-optimization     | budget checkpoint
COMPLETE    | sess-abc012 | logging-audit          | success, $0.18
```

### Peek, Attach, Detach

| Command | What It Does |
|---|---|
| `lyra peek <session-id>` | View current state + last K turns |
| `lyra attach <session-id>` | Surface interactive prompt for real-time control |
| `lyra detach <session-id>` | Return to parent without stopping subagent |

From attach mode, you can inject corrections at the next turn boundary: "Stop, that approach is wrong. Use async/await instead."

### Heartbeat and Recovery

The supervisor emits a heartbeat span every M turns. If a session crashes, the daemon discovers and restarts it on next start. Cleanup on graceful shutdowns; recovery on crashes.

---

## Coordinate

### Workflows

Complex tasks use the Workflow Engine. The agent loop calls `workflow.delegate(task)` when effort level is `ultracode`. The engine returns consolidated results as if they were a single tool call.

### Contract Chain

Every agent proposer creates a contract that must pass critic review:

```
Proposed -> UnderReview -> Accepted -> InProgress -> Completed -> Verified
```

Critics reject proposals with weak evidence and add them to a cross-team dead-end registry, reducing redundant experiments by 30-50%.

### Consensus Methods

| Method | Decision Rule | Best For |
|---|---|---|
| Majority | >50% agreement | Large swarms (10+) |
| Weighted | Sum(confidence * vote) | Mixed-expertise teams |
| Unanimous | 100% agreement | Safety-critical |
| Threshold | Configurable N% | Balanced speed/safety |

When consensus fails, escalation: re-vote with revealed reasoning -> weighted vote by historical accuracy -> human override.

---

## Isolate

Worktree isolation is the key safety mechanism. On session end:

```bash
# Safe cleanup (default)
lyra cleanup <session-id>   # stashes dirty files, does not destroy

# Quick cleanup (auto-stash)
lyra cleanup --force <session-id>

# Preserve for inspection
lyra cleanup --keep <session-id>
```

The worktree pool defaults to 10 concurrent. When exhausted, the oldest paused session is reclaimed. Beyond practical worktree limits (~10-20 concurrent), distributed execution across machines is needed.

---

## Related Docs

- [Architecture: Fleet Supervisor](../architecture/04-fleet-supervisor.md) -- daemon architecture, two-axis state model
- [Architecture: Workflow Engine](../architecture/05-workflow-engine.md) -- DAG planner, wave-based execution
- [Architecture: Worktree Isolation](../architecture/10-worktree-isolation.md) -- pool management, cleanup strategies
- [Block: DAG Teams](../blocks/07-dag-teams.md) -- team composition, role distribution
- [Guide: Agent Execution](01-agent-execution.md) -- single-agent loop that fleet orchestrates
- [Guide: Safety and Permissions](05-safety-and-permissions.md) -- subagent security, unwatched sessions
