# Hooks and TDD Gate -- Learning Path

> **Phase:** 2 (Workflow) | **Dependencies:** Agent Loop | **Used by:** Permission Bridge, Verifier, Observability

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | LifecycleBus pub/sub, guard functions (destructive pattern, secrets scan), TDD gate |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Guard composition patterns, event-driven architecture |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Hooks system provides lifecycle event hooks and quality gate enforcement via a LifecycleBus pub/sub pattern. Guard functions (destructive pattern detection, secrets scanning) protect the agent loop at tool-call time. The TDD gate (currently Phase 1 stub) blocks edits to `src/` without a RED test proof. The bus emits typed events (SESSION_START, TURN_START, SKILLS_ACTIVATED, etc.) that subscribers can observe.

> **Note:** This block is notably thin. 6 files exist vs. the 20+ originally documented. The TDD gate is a Phase 1 stub only -- full RED-GREEN-REFACTOR enforcement, test runner integration, and coverage analysis are documented as future work.

## Quick Reference

- **Use case**: Lifecycle observability in the agent loop, tool-call guard functions, or TDD enforcement.
- **Key concept**: LifecycleBus is a per-process singleton pub/sub with typed enum events; guard functions are composable callables, not decorator-registered hooks.
- **Dependencies**: Agent Loop (01).
- **Used by**: Permission Bridge (04), Verifier (11), Observability (13).
- **Phase**: 2 (Workflow).

## Related

- Concept doc: [Tools and Hooks overview](../../concepts/tools-and-hooks.md)
- System doc: [Index](../../lyra-upgrade/plans/index.md)
- Upgrade plan: [Hooks evolution](../../lyra-upgrade/plans/10-hooks.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
