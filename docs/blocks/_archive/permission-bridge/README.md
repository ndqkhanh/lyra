# Permission Bridge -- Learning Path

> **Phase:** 1 (Foundation) | **Dependencies:** Hooks | **Used by:** Agent Loop, Plan Mode, Safety Monitor

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | PermissionStack, LyraMode enum, resolve_lyra_decision(), guard pipeline, injection guard |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | Guard composition, security properties, mode-based decision logic |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The Permission system is Lyra's code-enforced runtime authorization primitive that intercepts every tool call before execution. Built around `PermissionStack`, `LyraMode` (9 modes from PLAN to BYPASS), and `resolve_lyra_decision()`, it runs a three-guard pipeline (destructive pattern detection, secrets scan, prompt injection detection) on every tool call. Unlike prompt-based safety, the LLM cannot bypass or reason around these checks. Security properties include fail-closed behavior, defense in depth, monotonic security, and no TOCTOU.

## Quick Reference

- **Use case**: Authorizing tool calls at runtime based on mode, blocking destructive commands, detecting secrets leakage, or enforcing read-only planning mode.
- **Key concept**: The LLM is *unprivileged* -- it never sees approval logic and cannot manipulate it. All authorization is code-enforced in a monotonic guard pipeline.
- **Dependencies**: Hooks (05).
- **Used by**: Agent Loop (01), Plan Mode (02), Safety Monitor (12).
- **Phase**: 1 (Foundation).

## Related

- Concept doc: [Permission Bridge overview](../../concepts/permission-bridge.md)
- System doc: [Index](../../concepts/index.md)
- Upgrade plan: [Permissions evolution](../../lyra-upgrade/plans/12-permissions.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
