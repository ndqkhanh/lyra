# Subagent Worktree -- Learning Path

> **Phase:** 2 (Workflow) | **Dependencies:** Agent Loop | **Used by:** DAG Teams, Fleet Supervisor

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | SubagentOrchestrator, WorktreeManager, FSSandbox, parallel execution with git worktrees |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | ThreadPoolExecutor with contextvars, scope collision detection, worktree lifecycle |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Subagent Worktree system provides isolated execution environments for concurrent agent operations using git worktrees as the native isolation boundary. The `SubagentOrchestrator` manages lifecycle across 13 files: worktree allocation via `WorktreeManager`, filesystem scope enforcement via `FSSandbox`, parallel execution via `ThreadPoolExecutor` with context-aware submission, result merging, and inter-agent handoff. Key safety properties include a recursion depth limit of 2, scope collision detection, and tool restriction.

## Quick Reference

- **Use case**: Running multiple agent instances in parallel with full filesystem isolation -- no context pollution, no file conflicts, safe experimentation.
- **Key concept**: Git worktrees as isolation boundaries -- each subagent gets its own working tree on a scoped branch. The FSSandbox enforces that all operations stay within declared scope globs.
- **Dependencies**: Agent Loop (01).
- **Used by**: DAG Teams (03), Fleet Supervisor.
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
