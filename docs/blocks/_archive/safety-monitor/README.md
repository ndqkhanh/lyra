# Safety Monitor -- Learning Path

> **Phase:** 4 (Safety/Advanced) | **Dependencies:** Permission Bridge, Agent Loop | **Used by:** All blocks (cross-cutting)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | v1 regex scanner (3 pattern sets), 5-layer defense-in-depth, SafetyFlag data model |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Collusion detection, misevolve safety gates, agent view permission guardrail, Z3 SMT confinement |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Safety Monitor is Lyra's integration point for a 5-layer defense-in-depth safety architecture. The v1 implementation is a synchronous, in-process regex scanner that detects prompt injection, sabotage patterns, and secret exposure within a rolling window. Beyond the v1 monitor, the broader safety module (20 files) covers alignment monitoring, adversarial verification, intent drift, forensic collection, governance, penetration testing, and spectral guardrails. Future layers include LLM classifier replacement and collusion detection across multi-agent channels.

> **Note:** The v1 SafetyMonitor is deliberately simple (91 lines, regex-based). The broader 20-file `lyra_core/safety/` module provides the comprehensive safety infrastructure.

## Quick Reference

- **Use case**: Runtime safety scanning for prompt injection, sabotage patterns (commented-out tests, skipped assertions), and secret exposure in agent output.
- **Key concept**: Defense in depth across 5 layers -- no single model or pattern catches everything. The v1 scanner is fast but simple; the broader module provides the deep safety infrastructure.
- **Dependencies**: Permission Bridge (04), Agent Loop (01).
- **Used by**: All blocks (cross-cutting).
- **Phase**: 4 (Safety/Advanced).

## Related

- Concept doc: [Safety Monitor overview](../../concepts/safety-monitor.md)
- System doc: [Index](../../concepts/index.md)
- Upgrade plan: [Safety evolution](../../lyra-upgrade/plans/17-safety.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
