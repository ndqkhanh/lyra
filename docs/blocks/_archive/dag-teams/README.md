# DAG Teams -- Learning Path

> **Phase:** 2 (Workflow) | **Dependencies:** Agent Loop, Subagent Worktree | **Used by:** Multi-agent orchestration, Fleet Supervisor

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | Agent teams, hybrid routing, sprint pipeline, mailbox inter-agent communication |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Sprint pipeline algorithms, hybrid routing strategies |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

DAG Teams is Lyra's team orchestration subsystem that coordinates multi-agent workflows. It implements agent team management, hybrid LLM-plus-deterministic routing, sprint-based execution pipelines, shared task coordination, and mailbox-based inter-agent communication. Built on 11 files, it bridges from a user request through a hybrid router and sprint pipeline into parallel subagent execution, then collects and merges results.

## Quick Reference

- **Use case**: Multiple agents collaborating on a complex task with parallel execution waves, inter-agent communication, and plan approval workflows.
- **Key concept**: Sprint pipelines decompose work into parallel waves; the hybrid router combines LLM planning with deterministic scheduling; inter-agent communication uses a decoupled mailbox pattern.
- **Dependencies**: Agent Loop (01), Subagent Worktree (10).
- **Used by**: Multi-agent orchestration, Fleet Supervisor.
- **Phase**: 2 (Workflow).

## Related

- Concept doc: [Subagents overview](../../concepts/subagents.md)
- System doc: [Fleet supervisor](../../lyra-upgrade/plans/fleet-supervisor/)
- Upgrade plan: [Multi-agent orchestration](../../lyra-upgrade/plans/multi-agent/)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
