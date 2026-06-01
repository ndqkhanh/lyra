# 280 — Lyra × Seven-Layer Stack Apply Plan 2026

**Anchors.** Lyra — personal-assistant agent with three-tier memory ([projects/lyra/docs/blocks/07-memory-three-tier](../projects/lyra/docs/blocks/07-memory-three-tier.md)) and lyra-core / lyra-cli / lyra-mcp / lyra-skills packages. Extends [208-lyra-multi-hop-collaborative-apply-plan](208-lyra-multi-hop-collaborative-apply-plan.md). Per-layer source: [225](225-agent-era-scaling-synthesis.md), [258](258-agent-protocol-stack-synthesis-2026.md), [263](263-production-agent-runtime-synthesis-2026.md), [268](268-agent-operations-synthesis-2026.md), [273](273-agent-security-synthesis-2026.md), [276](276-local-first-privacy-first-agents.md).

**One-line definition.** A **per-layer apply plan** for Lyra adopting the seven-layer stack — Lyra is the **canonical local-first / privacy-first personal-assistant agent** ([276](276-local-first-privacy-first-agents.md)) with three-tier memory (procedural / episodic / semantic) plus SOUL.md persona partition; the apply plan **emphasizes local-first defaults** (ollama / MLX / Phoenix-local / SQLite + Chroma local), **privacy-first compliance** (right-to-erasure single-button, no cloud telemetry, opt-in-only cloud actions), **distributed deployment via Tailscale + NATS** ([253](253-tailscale-nats-mesh-for-distributed-agents.md)) for two-Lyra setups (home + laptop), and **lighter compliance burden** (no EU AI Act high-risk classification for personal use; GDPR for any EU users) — staged across four 90-day phases that complete the seven-layer stack while preserving Lyra's local-first identity.

## Lyra-specific shape

Lyra is a **personal-assistant agent** that lives on the user's device(s), running locally by default with optional cloud opt-in per action. The architecture (per [Lyra Block 07](../projects/lyra/docs/blocks/07-memory-three-tier.md)): SQLite + FTS5 + Chroma + .md files for memory; BGE-small embeddings local CPU; ollama / MLX for LLM; lyra-mcp for tool exposure; lyra-skills for procedural memory. Multi-channel (CLI, TUI, future GUI / iOS / Android). The seven-layer stack adopts naturally because Lyra is purpose-built for the personal-agent use case — local-first, privacy-first, modest scale.

## Per-layer plan

### L1 Foundation — adapt polaris primitives

Lyra-core borrows polaris primitives (Permission Bridge, Hooks, Bright-line Gates, Cost Router) but with **per-user scope** rather than per-research-program. **Action:** vendor `harness_core/foundation/` (subset of polaris-core); per-user permission contexts; bright-line escalation through user notification (push, email, voice).

### L2 Capability — local-tier defaults

[225-agent-era-scaling-synthesis](225-agent-era-scaling-synthesis.md). Lyra's capability budget is the user's hardware tier ([276-local-first-privacy-first-agents](276-local-first-privacy-first-agents.md)):

- **Pretraining (L1)**: pick R1-Distill-Qwen-32B as default (reasoning class on M4 Max 64GB+).
- **TTC (L2)**: difficulty router; thinking only for hard tasks.
- **Trajectory (L3)**: short-horizon by default; daemon for long-horizon.
- **Multi-agent (L4)**: rare for personal use; SOUL.md + Hermes skill loop is the default pattern.
- **Verifier (V)**: cross-channel via cloud opt-in for high-stakes.

**Phase:** P1 (foundation).

### L3 Protocol — full stack but local-first

[258-agent-protocol-stack-synthesis-2026](258-agent-protocol-stack-synthesis-2026.md).

- **MCP** ([256](256-mcp-2025-2026-evolution.md)): `lyra-mcp` package; expose user's local services (file, calendar, email, browser) as MCP tools.
- **A2A** ([254](254-a2a-protocol-deep-dive.md)): expose Lyra as A2A endpoint over Tailscale; cross-device Lyra-to-Lyra calls.
- **AGNTCY OASF** ([255](255-agntcy-oasf-acp-deep-dive.md)): OASF manifest published to user's tailnet; not public.
- **Tailscale + NATS** ([253](253-tailscale-nats-mesh-for-distributed-agents.md)): **load-bearing for Lyra** — two-Lyra deployment (home + laptop) via tailnet, NATS for memory delta sync, JetStream for offline replay.
- **SKILL.md + marketplace** ([257](257-agent-skill-marketplace-landscape.md)): vendored skills core; marketplace opt-in with min-trust-tier `audited`.
- **Routines + Agent Teams** ([250](250-anthropic-agent-teams.md), [252](252-routines-pattern-for-self-hosted-agents.md)): Routines for scheduled summaries + reflections; Agent Teams sparingly used.

**Phase:** P1-P2.

### L4 Runtime — LangGraph for state-machine reflection loops

[259-langgraph-deep-dive](259-langgraph-deep-dive.md). Lyra's reflection-and-consolidation loops (observation-stream → reflection → plan, per [Lyra Block 07](../projects/lyra/docs/blocks/07-memory-three-tier.md)) are state-machine shape; LangGraph fits naturally. Postgres or SQLite checkpointer.

**Alternative consideration:** OpenAI Agents SDK ([260](260-openai-agents-sdk-deep-dive.md)) for handoff workflows (voice agent → text specialist). Hybrid possible.

**Phase:** P2.

### L5 Security — privacy-first defaults

[273-agent-security-synthesis-2026](273-agent-security-synthesis-2026.md).

- **Prompt-injection defense.** Spotlight prompting on retrieved emails / web / docs; instruction hierarchy; classifier ensemble. Critical for email-summarization use case.
- **Supply chain.** Vendored skills primary; marketplace opt-in min-trust-tier `audited`. SBOM auto-maintained.
- **Isolation.** Container per agent run; cap_drop:ALL; network egress allowlist (specific user-approved services).
- **Memory provenance.** Already strong via [Lyra Block 07](../projects/lyra/docs/blocks/07-memory-three-tier.md) — `<private>` tag, redactor, citation-backed wiki.
- **Bright-line gates.** Send-email-external, post-to-social, transfer-money, share-with-cloud are bright-lined.

**Privacy-first overlay:** memory + traces never leave device by default; opt-in cloud per action. Right-to-erasure is `lyra mem wipe --confirm`.

**Phase:** P2.

### L6 Operations — local Phoenix + lighter SRE

[268-agent-operations-synthesis-2026](268-agent-operations-synthesis-2026.md).

- **Observability.** Phoenix runs locally; OTel spans; HIR-shape events; no cloud upload by default.
- **Evaluation.** Lighter eval suite (personal-task focused); growable from production traces.
- **Durability.** LangGraph SQLite checkpointer; idempotency keys; saga for multi-step user-action workflows.
- **SRE.** Simpler — one user, no on-call. Cost-runaway alert + quality-regression alert + bright-line escalation log.

**Phase:** P3.

### L7 Compliance — privacy-first by construction

[272-agent-compliance-and-audit](272-agent-compliance-and-audit.md).

- **EU AI Act:** personal use → minimal-risk tier; transparency obligation only.
- **GDPR:** user is data controller; Lyra implements right-to-erasure cascade.
- **HIPAA / financial regulations:** only relevant if deployed for regulated workflows.

**Phase:** P3-P4 (lower urgency than for enterprise agents).

## Phased rollout

| Phase | Scope | Duration |
|---|---|---|
| **P1** | L1 Foundation, L2 Capability (local tier), partial L3 Protocol | 90 days |
| **P2** | Complete L3 Protocol (Tailscale + NATS, A2A), L4 Runtime (LangGraph), L5 Security | 90 days |
| **P3** | L6 Operations (local Phoenix + SLO), L7 Compliance (privacy primitives) | 90 days |
| **P4** | Multi-device polish, marketplace integration, voice + text composition | 90 days |

## The two-Lyra deployment

[253-tailscale-nats-mesh-for-distributed-agents](253-tailscale-nats-mesh-for-distributed-agents.md). Production target:

```
Lyra-home (M4 Max 128GB) ─Tailscale─ Lyra-laptop (M3 Pro 36GB)
                                 │
                            Tiny VPS hub
                              ($5/mo)
                              NATS leaf
                              JetStream
```

Memory deltas sync via NATS subjects; JetStream durably replays for offline-then-online. SOUL.md persona shared. Skills replicate. The **defining Lyra deployment shape**.

## Cost economics for Lyra

[278-agent-unit-economics-2026](278-agent-unit-economics-2026.md). Personal-agent at zero marginal cost:

- M4 Max 128GB: ~$6K up-front, ~$0.35/day amortized over 2 years.
- $5/mo VPS for NATS hub.
- $0 marginal per query.

Total: ~$110/year vs $20-50/month cloud-personal-assistant subscriptions = ~$240-600/year.

## Lyra-specific implications

- **Privacy-by-construction** is the Lyra value prop — every layer respects it.
- **Single-user simplicity** allows lighter SRE, no on-call.
- **Offline-capable** via local-first stack.
- **Multi-channel UX** ([277-agent-ux-patterns-2026](277-agent-ux-patterns-2026.md)) — CLI, TUI, future iOS / web.
- **SOUL.md persona** anchors identity across devices.
- **Skill marketplace** opt-in with strict trust tier; vendored skills primary.
- **Cross-channel verifier** rare (latency, privacy); reserved for high-stakes via cloud opt-in.

## One-line takeaway

**Lyra adopts the seven-layer stack with local-first / privacy-first defaults across four 90-day phases — L1-L2 in P1 (foundation + local capability tier), L3-L5 in P2 (protocol stack including the load-bearing Tailscale + NATS two-Lyra mesh, LangGraph for state-machine reflection loops, privacy-first security), L6 in P3 (local Phoenix + lighter SRE), L7 in P4 (privacy-first compliance) — preserving Lyra's identity as the canonical local-first personal-assistant deployment shape, with two-Lyra mesh as the defining multi-device pattern at ~$110/year total cost.**
