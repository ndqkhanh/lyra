# Fleet Supervisor -- Learning Path

> **Phase:** 3 | **Composes blocks:** Agent Loop, DAG Teams, Context Engine, Safety Monitor | **Architecture doc:** [04-fleet-supervisor.md](../../architecture/04-fleet-supervisor.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- per-user daemon for background AI agent sessions, two-axis state model (task-state x process-liveness), four-layer separation (supervisor, TUI, worktrees, channels) |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | Design decisions: UDS vs gRPC, atomic-write + WAL persistence, worktree isolation strategy, security gate risk-level expiry |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Supervisor lifecycle (466-line daemon), Fleet TUI widgets, IPC protocol (4-byte header + JSON), state persistence patterns, crash recovery |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Two-axis state innovations, idle-stop algorithms, crash recovery semantics, scaling limits |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | Startup latency (<200ms), tick overhead (<10ms), memory profiling, session density limits |

## In 30 Seconds

The Fleet Supervisor is a per-user daemon that manages background AI agent sessions. Each session is an isolated OS process with its own git worktree, surviving terminal close and machine sleep. A two-axis state model (task-state + process-liveness) lets users manage fleets by exception -- they only intervene when a session signals it needs attention. The daemon auto-starts on first background command, auto-stops idle sessions after ~1 hour, and self-exits after 24 hours of inactivity.

## What This System Composes

| Block | Role |
|-------|------|
| [Agent Loop](../../blocks/agent-loop/) | Core execution cycle driving each session |
| [DAG Teams](../../blocks/03-dag-teams.md) | Parallel agent coordination within a fleet |
| [Context Engine](../../blocks/06-context-engine.md) | Session context management and compaction |
| [Safety Monitor](../../blocks/safety-monitor/) | Rogue/stuck session detection and flagging |

## Quick Reference

- **When you need this:** Running agents in the background, managing multiple concurrent AI sessions, building a "steer-by-exception" UX
- **Related architecture doc:** [04-fleet-supervisor.md](../../architecture/04-fleet-supervisor.md)
- **Upgrade plan:** [13-swarm-fleet.md](../../lyra-upgrade/plans/13-swarm-fleet.md)
- **Concept docs:** [sessions-and-state.md](../../concepts/sessions-and-state.md), [agent-loop.md](../../concepts/agent-loop.md)
- **Key packages:** `packages/lyra-orchestration/` (supervisor), `packages/lyra-fleet-tui/` (dashboard)

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
