# Orchestration System -- Learning Path

> **Phase:** 4 | **Composes blocks:** Agent Loop, DAG Teams, Subagent Worktree, Permission Bridge, Safety Monitor, Hooks & TDD Gate | **Architecture docs:** [05-workflow-engine.md](../../architecture/05-workflow-engine.md), [agent-orchestration.md](../../architecture/agent-orchestration.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- distributed task queues with priority scheduling, consensus protocols (majority/unanimous/weighted/quorum), typed event bus for inter-agent messaging, worktree isolation for safe concurrent editing |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | Priority-based scheduling (CRITICAL > HIGH > NORMAL > LOW), 4 voting strategies, event bus pub/sub model with Pydantic schema validation, two-axis state machine, security gate integration |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Code patterns for task queue with worker capability matching, event bus domain events, consensus protocol integration, fleet lifecycle management, worktree creation with copy-on-write |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | UDS vs gRPC for IPC, worktree vs container isolation, in-memory vs persistent state, Pydantic vs dataclass trade-offs, Redis vs JSON persistence |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | Task throughput (8,500/s peak), event delivery latency (<1ms), maintainability index (78.5), test coverage (91%+) |

## In 30 Seconds

The Orchestration system is Lyra's coordination backbone, combining a fleet supervisor daemon for background sessions, priority-based task queues with worker capability matching, a typed event bus for inter-agent messaging with zero serialization overhead, multi-strategy consensus voting, and git worktree isolation for safe concurrent file editing. It enables reliable parallel execution with full fault tolerance -- automatic retries (max 3), dead letter queues, and crash recovery via WAL replay. All components use pure Python asyncio with frozen dataclasses for immutable state.

## What This System Composes

| Block | Role |
|-------|------|
| [Agent Loop](../../blocks/agent-loop/) | Core execution cycle for dispatched tasks |
| [DAG Teams](../../blocks/03-dag-teams.md) | Dependency-driven task graph resolution |
| [Subagent Worktree](../../blocks/10-subagent-worktree.md) | Git worktree sandbox for safe concurrent editing |
| [Permission Bridge](../../blocks/04-permission-bridge.md) | Multi-layer authorization for agent actions (read/mutate/critical) |
| [Safety Monitor](../../blocks/safety-monitor/) | Rogue/stuck session detection via metrics analysis |
| [Hooks & TDD Gate](../../blocks/hooks-tdd/) | Pre/post-tool lifecycle hooks for validation and logging |

## Quick Reference

- **When you need this:** Running background agent sessions, distributing work across agents, building fault-tolerant multi-agent pipelines
- **Related architecture docs:** [05-workflow-engine.md](../../architecture/05-workflow-engine.md), [agent-orchestration.md](../../architecture/agent-orchestration.md)
- **Upgrade plan:** [13-swarm-fleet.md](../../lyra-upgrade/plans/13-swarm-fleet.md)
- **Concept docs:** [sessions-and-state.md](../../concepts/sessions-and-state.md), [agent-loop.md](../../concepts/agent-loop.md), [tools-and-hooks.md](../../concepts/tools-and-hooks.md)
- **Key packages:** `packages/lyra-orchestration/` (core), `packages/lyra-core/` (teams), `packages/lyra-agent-swarm/` (fleet)

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
