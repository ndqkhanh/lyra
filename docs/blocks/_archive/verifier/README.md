# Verifier Cross-Channel -- Learning Path

> **Phase:** 3 (Validation) | **Dependencies:** Agent Loop, Hooks/TDD Gate, Observability | **Used by:** Plan Mode, Safety Monitor

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | Two-phase verification, cross-channel reconciler, evaluator family detector, PRM |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Anonymized adversarial panel, 4-correction pipeline, mutation gating, ErrorProbe attribution, Pass^k metrics |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Verifier is Lyra's trust layer -- a two-phase verification system with cross-channel evidence reconciliation that catches fabricated success claims. Phase 1 runs fast deterministic checks (acceptance tests, expected files, coverage non-regression) with zero LLM cost. Phase 2 invokes an independent different-family LLM judge with a rubric. A cross-channel reconciler requires three independent evidence sources (execution trace, git diff, environment snapshot) to agree before accepting a result. Cost: $0 for Phase 1 failures, ~$0.05-0.15 for a full pass.

## Quick Reference

- **Use case**: Verifying that a task completion is genuine -- not a fabricated success -- by cross-referencing what the agent claims, what actually changed on disk, and the environment state.
- **Key concept**: Trust through triangulation -- three independent evidence channels (trace, diff, snapshot) must agree. Same-family evaluation is detected and prevented via `is_degraded_eval()`.
- **Dependencies**: Agent Loop (01), Hooks/TDD Gate (05), Observability (13).
- **Used by**: Plan Mode (02), Safety Monitor (12).
- **Phase**: 3 (Validation).

## Related

- Concept doc: [Verifier overview](../../concepts/verifier.md)
- System doc: [Index](../../concepts/index.md)
- Upgrade plan: [Adversarial panel](../../lyra-upgrade/plans/25-adversarial-panel.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
