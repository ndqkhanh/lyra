# Observability -- Learning Path

> **Phase:** 3 (Monitoring) | **Dependencies:** Agent Loop, Hooks, Permission Bridge | **Used by:** All blocks (cross-cutting)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | EventBus, HIR JSONL events, OTel export, Live Display, RetroEngine replay |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | HIR schema, streaming JSON parsing, secret redaction, cost attribution |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

Lyra's observability system is a dual-protocol telemetry infrastructure that emits both OpenTelemetry-compatible traces (for generic observability platforms) and Harness Intermediate Representation (HIR) events (for agent-specific analysis). It features a singleton EventBus with typed events, JSONL file emission with secret masking, a LiveDisplay terminal dashboard, a RetroEngine for trace replay and cost attribution, and OTLP export -- all with under 10us overhead per event emit.

## Quick Reference

- **Use case**: Instrumenting the agent loop, tracing tool calls, replaying sessions, attributing costs, or displaying real-time agent state.
- **Key concept**: Dual protocol -- HIR JSONL for agent-specific analysis (grepable, replayable), OTel for generic observability platforms. All emission is non-blocking with <10us overhead.
- **Dependencies**: Agent Loop (01), Hooks (05), Permission Bridge (04).
- **Used by**: All blocks (cross-cutting).
- **Phase**: 3 (Monitoring).

## Related

- Concept doc: [Observability overview](../../concepts/observability.md)
- System doc: [Index](../../concepts/index.md)
- Upgrade plan: [Voice mode observability](../../lyra-upgrade/plans/18-voice-mode.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
