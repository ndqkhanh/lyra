# Multi-Agent System -- Learning Path

> **Phase:** 3 | **Composes blocks:** DAG Teams, Subagent Worktree, Agent Loop, Memory (Three-Tier), Plan Mode, Safety Monitor | **Architecture docs:** [agent-orchestration.md](../../architecture/agent-orchestration.md), [agent-swarm.md](../../architecture/agent-swarm.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- contract chains for formal agent agreements, consensus building with 4 vote methods, sprint pipelines with wave-based execution, self-claiming task model, fleet orchestration with 5 execution patterns |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | Wave-based execution algorithm, mailbox messaging pattern, hybrid routing (keyword + semantic), coalition formation via Shapley value, hierarchical team structures |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | `lyra_core/teams/` (10 modules), `lyra-agent-swarm` (33+ modules), subagent worktree lifecycle, event bus integration, byzantine fault tolerance patterns |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Consensus method selection (majority/weighted/unanimous/threshold), Shapley-value coalition formation, leader election algorithms, zero-trust federation |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | Agent concurrency scaling, consensus latency (<500ms in-memory), sprint pipeline throughput, fault tolerance overhead |

## In 30 Seconds

Lyra's multi-agent system enables sophisticated coordination through contract chains (formal agreements between agents with review and evidence), consensus building (4 vote aggregation methods), sprint pipelines (wave-based dependency execution), and self-claiming task models. It spans three packages (lyra_core/teams, lyra-agent-swarm, lyra-orchestration) with 5 execution patterns: fan-out, pipeline, map-reduce, tournament, and ensemble. Each subagent runs in an isolated git worktree sandbox.

## What This System Composes

| Block | Role |
|-------|------|
| [DAG Teams](../../blocks/03-dag-teams.md) | Dependency graph for parallel agent coordination |
| [Subagent Worktree](../../blocks/10-subagent-worktree.md) | Isolated git worktree sandboxes per agent |
| [Agent Loop](../../blocks/agent-loop/) | Core execution cycle for each agent |
| [Memory (Three-Tier)](../../blocks/memory/) | Episodic, semantic, and working memory across agents |
| [Plan Mode](../../blocks/02-plan-mode.md) | Multi-step planning and critique cycles for agent teams |
| [Safety Monitor](../../blocks/safety-monitor/) | Continuous security monitoring, byzantine fault tolerance |

## Quick Reference

- **When you need this:** Coordinating multiple AI agents on a shared task, building consensus-driven workflows, implementing parallel agent execution patterns
- **Related architecture docs:** [agent-orchestration.md](../../architecture/agent-orchestration.md), [agent-swarm.md](../../architecture/agent-swarm.md)
- **Upgrade plans:** [13-swarm-fleet.md](../../lyra-upgrade/plans/13-swarm-fleet.md), [14-autonomy.md](../../lyra-upgrade/plans/14-autonomy.md)
- **Concept docs:** [subagents.md](../../concepts/subagents.md), [agent-loop.md](../../concepts/agent-loop.md), [dag-teams.md](../../concepts/dag-teams.md)
- **Key packages:** `packages/lyra-core/src/lyra_core/teams/`, `packages/lyra-agent-swarm/`, `packages/lyra-orchestration/`

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
