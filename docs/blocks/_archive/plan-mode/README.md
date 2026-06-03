# Plan Mode -- Learning Path

> **Phase:** 1 (Foundation) | **Dependencies:** Permission Bridge | **Used by:** Agent Loop, DAG Teams, Verifier

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | Heuristics engine, LyraMode.PLAN, Planner Agent, PlanArtifact, approval workflow |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Task complexity heuristics, plan validation, plan drift detection |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

Plan Mode converts user tasks into structured, approvable execution plans before any code changes occur. A heuristics engine determines if a task is trivial (skip planning) or non-trivial (enter LyraMode.PLAN). In plan mode, the Planner Agent uses read-only tools to produce a PlanArtifact with acceptance tests, expected files, feature items, and open questions. Plans are validated, stored in `.lyra/plans/`, and must pass interactive or auto-approval before execution begins.

## Quick Reference

- **Use case**: Structured planning before any code changes -- especially for complex or multi-file tasks where approval gates are needed.
- **Key concept**: Plan mode is enforced by the permission stack (read-only). The heuristics engine separates trivial tasks (typo fixes, renames) from non-trivial work that needs a plan artifact.
- **Dependencies**: Permission Bridge (04).
- **Used by**: Agent Loop (01), DAG Teams (03), Verifier (11).
- **Phase**: 1 (Foundation).

## Related

- Concept doc: [Plan Mode overview](../../concepts/plan-mode.md)
- System doc: [Index](../../concepts/index.md)
- Upgrade plan: [Planning evolution](../../lyra-upgrade/plans/20-planning.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
