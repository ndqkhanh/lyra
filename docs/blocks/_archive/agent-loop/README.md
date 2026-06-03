# Agent Loop -- Learning Path

> **Phase:** 1 (Foundation) | **Dependencies:** None | **Used by:** All blocks

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | Core purpose, 4 autonomy modes, turn lifecycle, plugin hooks |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Algorithms, data structures, edge cases |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The agent loop is Lyra's kernel -- the core execution primitive that orchestrates the think-act-observe cycle. It owns the LLM/tool/store interaction shape, supports four autonomy levels (interactive to full autonomy), and exposes duck-typed plugin hooks for lifecycle observation. It does not hardcode any specific model, tool, or persistence layer.

## Quick Reference

- **Use case**: Execution driver for LLM-based agents supporting turn management, budget control, and plugin extensibility.
- **Key concept**: The agent loop is a *driver*, not a semantic engine -- it provides the skeleton for agent execution; all meaning comes from plugins.
- **Dependencies**: None (foundation block).
- **Used by**: All other blocks.
- **Phase**: 1 (Foundation).

## Related

- Concept doc: [Agent Loop overview](../../concepts/agent-loop.md)
- System doc: [Fleet supervisor](../../lyra-upgrade/plans/fleet-supervisor/)
- Upgrade plan: [Agent loop evolution](../../lyra-upgrade/plans/agent-loop.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
