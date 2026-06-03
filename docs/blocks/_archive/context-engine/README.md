# Context Engine -- Learning Path

> **Phase:** 1 (Foundation) | **Dependencies:** None | **Used by:** Agent Loop, Memory, Plan Mode

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | 5-layer context (SOUL, STATIC_CACHED, DYNAMIC, COMPACTED, MEMORY_REFS), assembly, compaction |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Token compression, compaction strategies, cache telemetry |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Context Engine assembles, manages, and optimizes what the LLM sees on every turn using a five-layer architecture (SOUL, STATIC_CACHED, DYNAMIC, COMPACTED, MEMORY_REFS). It handles compaction when sessions grow long, truncates bulky tool outputs, provides cache-optimized prefix stability, and uses relevance scoring to keep context lean. With 25 files across assembly, compaction, token compression, repository mapping, and altitude tracking, it is one of Lyra's largest subsystems.

## Quick Reference

- **Use case**: Controlling what the LLM sees in its context window -- layering, compaction, token budgets, and cache optimization.
- **Key concept**: Context has layers. The SOUL layer is never compacted; the STATIC_CACHED layer is optimized for prompt cache hits; old turns are summarized into the COMPACTED layer.
- **Dependencies**: None (foundation block).
- **Used by**: Agent Loop, Memory, Plan Mode.
- **Phase**: 1 (Foundation).

## Related

- Concept doc: [Context Engine overview](../../concepts/context-engine.md)
- System doc: [Prompt Cache Coordination](../../concepts/prompt-cache-coordination.md)
- Upgrade plan: [Context compaction](../../lyra-upgrade/plans/03-context-compaction.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
