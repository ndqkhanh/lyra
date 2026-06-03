# Memory System -- Learning Path

> **Phase:** 3 (Knowledge) | **Dependencies:** Context Engine | **Used by:** Agent Loop, Plan Mode, Observability

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | 6+ memory packages, three-tier architecture (working/episodic/semantic/procedural), graph systems, consolidation |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Entropic consolidation, dream consolidation, AMAC admission, symbolic SSM, causal graphs |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Lyra memory system is a distributed multi-package memory fabric spanning 6+ packages: core engine (activation, importance, consolidation), memory stack (working/episodic/semantic/procedural tiers), gossip consensus for fleet deployments, knowledge graphs, causal graphs, and verifiable cache. It supports SQLite, pgvector, and file-system backends with three-layer progressive disclosure search (search -> context -> full fetch). Advanced mechanisms include entropic consolidation, dream consolidation (idle-period replay), and AMAC adaptive admission control.

## Quick Reference

- **Use case**: Persistent agent memory across sessions -- recalling past conversations, storing procedural knowledge, or sharing memory across a fleet of agents.
- **Key concept**: Memory operates in tiers (working -> episodic -> semantic) with automated consolidation. Search is three-layer progressive: cheap keyword search first, then vector search, then full content fetch.
- **Dependencies**: Context Engine (06).
- **Used by**: Agent Loop (01), Plan Mode (02), Observability (13).
- **Phase**: 3 (Knowledge).

## Related

- Concept doc: [Memory Tiers overview](../../concepts/memory-tiers.md)
- System doc: [Skills system](../../lyra-upgrade/plans/skills-system/)
- Upgrade plan: [Memory upgrades](../../lyra-upgrade/plans/agent-loop.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
