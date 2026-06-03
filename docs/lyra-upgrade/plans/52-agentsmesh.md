# Multi-Tenancy (AgentsMesh) — Plan (§5.2)

> Run 3, 2026-06-03

## Plain-Language Summary

AgentsMesh provides multi-tenant agent orchestration — multiple users/teams sharing a single agent infrastructure with namespace isolation, quota management, and access control. Evaluation: useful for enterprise deployments but adds complexity Lyra's v1 doesn't need. Recommendation: defer to v2; use supervisor-per-user isolation in v1.

## Evaluation

### Architecture (from https://github.com/AgentsMesh/AgentsMesh)
- Namespace isolation: each tenant gets isolated agent namespace, tool registry, memory store
- Quota management: per-tenant rate limits, token budgets, concurrency caps
- Access control: RBAC for agent creation, tool access, session management

### Pros
- Enterprise-ready multi-team deployments
- Shared infrastructure reduces per-tenant overhead
- Consistent security model across tenants

### Cons
- Significant complexity (namespace isolation, quota tracking, RBAC)
- Lyra's supervisor daemon already provides per-user process isolation
- Multi-tenancy conflicts with local-first design (Lyra runs on user's machine)

### Recommendation

**DEFER to v2.** Lyra v1 is local-first — one supervisor per user, sessions on the user's machine. Multi-tenancy is an enterprise feature that adds weeks of complexity without v1 user demand. When Lyra adds a server/cloud deployment model (v2), revisit AgentsMesh patterns for namespace isolation and quota management.

**Impact:** 2 (v1) | **Effort:** 5 | **Tier:** Deferred to v2

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code docs (§3.1). Breakthrough tier gated on evidence from batch research findings.

## Changelog

- Run 4 (2026-06-03): Added Expert Review section, Changelog
