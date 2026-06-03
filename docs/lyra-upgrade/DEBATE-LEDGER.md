# Debate Ledger — Round-by-Round Log

> Run 1 — June 3, 2026 | Records every debate round: motion → arguments → outcome

---

## ROUND 1 — Candidates vs Baseline

**Motion:** "Each candidate architecture MUST prove it beats the baseline (BASELINE.md) on evidence. The baseline is a first-class contender — the 'do nothing / minimal change' option championed by the Adversarial Skeptic."

### Candidates on the Table

**Candidate A: Memory-Centric Architecture** — Build the breakthrough from memory outward. Field-theoretic memory as the foundation; graph + Zettelkasten storage; cost-sensitive routing; dreaming consolidation. Orchestration, skills, and fleet are layered on top but memory is the spine.

**Candidate B: Orchestration/Fleet-Centric Architecture** — Build the breakthrough from the fleet outward. Supervisor daemon + worktree isolation + dynamic workflow engine as the foundation. Memory, skills, and safety are capabilities the fleet USES. The "ultracode" primitives are the spine.

**Candidate C: Self-Evolution-Centric Architecture** — Build the breakthrough from self-improvement outward. GEPA-style skill evolution, DGM-style harness rewriting, MetaAgent-X co-evolution. The system gets better over time; everything else (memory, fleet, routing) is infrastructure to support evolution.

**Candidate D: Baseline / Minimal Change** — Improve the existing codebase incrementally. Add embedding search to memory. Add a basic model router. Port claude-skills' 330+ skills. Use tmux + status file for basic fleet. No supervisor daemon, no worktree isolation, no workflow engine, no field-theoretic memory.

### Per-Persona Critiques

**Senior AI Solutions Architect:** "Candidate A (memory-centric) has the strongest research foundation — 28 papers of evidence. Candidate B (fleet-centric) is the most immediately useful — Lyra without a fleet is a single-agent system. Candidate C (self-evolution) is the most ambitious but also the riskiest and depends on A and B existing. Candidate D (minimal change) gets Lyra to 'useful' fastest but hits a ceiling quickly."

**Senior Software Architect:** "Candidate B is the right spine. The system boundaries are clean: supervisor manages processes, worktrees manage files, workflow engine manages orchestration. Memory and skills plug in as capabilities. Candidate A makes memory the spine, but memory is a SERVICE — it shouldn't drive architecture. Candidate C puts evolution at the center, but evolution is a PROCESS, not an architecture."

**Senior Backend Engineer:** "Candidate D is the only one that ships in 2026. Supervisor daemon + worktree isolation + workflow engine is 6+ months of work for a team of 1-2. Embedding search + model router + skill port is 2 months. Ship D first, then build toward B."

**Senior AI Researcher:** "Candidate A has the genuine research novelty — field-theoretic memory is the only approach that could be called a 'breakthrough.' Everything else is engineering ports of existing systems. But novelty doesn't equal impact. Candidate B addresses Lyra's most visible gap: it can't run unattended or in parallel."

**Senior SRE:** "Candidate B's supervisor daemon is the highest operational risk. A daemon that manages processes, survives restarts, and doesn't leak resources is hard to get right. Candidate D's tmux approach is battle-tested — millions of developers use tmux daily."

**Senior Security Engineer:** "Candidate C (self-evolution) is the scariest from a safety perspective. 'Misevolve' shows 45% refusal rate drops, 76% tool vulnerability rates. Lyra can't safely self-evolve without safety infrastructure that doesn't exist yet. Candidate B's worktree isolation is the strongest safety primitive — it contains blast radius."

**Adversarial Skeptic (championing Candidate D):** "Candidate D is the only honest option. Candidates A-C are architecture astronaut fantasies — elegant designs that would take years to build. Lyra today has 5 partially-working subsystems. Adding a supervisor daemon to that is like adding a jet engine to a bicycle. Ship the bicycle first. Add embedding search. Add a model router. Ship the 330 skills. THEN decide if you need a daemon."

**Senior PM:** "The Skeptic has a point on sequencing. But we need to know where we're going even if we get there incrementally. Candidate B is the right destination. Ship it in phases: Phase 1 = embedding search + model router + skill port + tmux fleet (Candidate D). Phase 2 = supervisor daemon + worktree + basic workflows. Phase 3 = adversarial verification + dreaming + self-evolution."

### Outcome

**Surviving candidates after Round 1:**
- **Candidate B (Fleet-Centric):** Wins on architectural clarity, addresses Lyra's most visible gap, clean boundaries
- **Candidate D (Baseline):** Survives as the PHASE 1 of whatever wins — the immediate next step
- **Candidate A (Memory-Centric):** Absorbed into B — memory becomes the first major capability the fleet exercises
- **Candidate C (Self-Evolution):** Parked — gated behind safety infrastructure from B

**Key concession:** All candidates agreed Phase 1 = Candidate D's improvements (embedding search, model router, skill port). The debate is about Phase 2+.

---

## ROUND 2 — Candidates vs Each Other (B vs D-Absorbed-A)

**Motion:** "Candidate B (Fleet-Centric with absorbed memory innovations) vs the Skeptic's Phase-2-is-overengineered position. Head-to-head across ALL trade-off dimensions."

### Trade-Off Comparison Table

| Dimension | Candidate B (Fleet-Centric) | Candidate D (Minimal Change, Extended) | Winner |
|-----------|---------------------------|--------------------------------------|--------|
| **Capability ceiling** | Fleet of 100s, unattended, parallel-safe | Single-session, attended, no parallel safety | B |
| **Build effort** | 6-9 months (team of 2) | 2-3 months (team of 1) | D |
| **Operational complexity** | Daemon to maintain, worktrees to clean, workflow engine to debug | Standard Unix tools (tmux, git) | D |
| **Token economics** | Cheap row summaries + adversarial verification costs tokens but improves quality | No fleet overhead, but no quality improvement either | Tie |
| **Reliability** | Supervisor SPOF mitigated by disk persistence; rogue agent prevention built-in | No new SPOFs, but no reliability gains | B (long-term) |
| **Safety** | Worktree isolation + permission gates + collusion detection | No new safety, relies on existing (weak) safety | B |
| **Multi-provider** | Supervisor is provider-agnostic; subagents per-model | No change — single model per session | B |
| **Time to first value** | 6 months to full fleet | 2 months to embedding search + router + skills | D |
| **Maintenance burden** | Daemon, worktree cleanup, workflow engine — ongoing ops cost | No new infrastructure to maintain | D |
| **Failure modes** | Daemon crash orphans sessions; worktree proliferation; workflow script bugs | Same failure modes as today | D (fewer new) |

### Key Exchanges

**Senior Distributed-Systems Engineer (for B):** "The Skeptic's tmux approach breaks at scale. Tmux can't: query 'which sessions are stuck?', programmatically respawn a crashed session, enforce per-session quotas, or provide structured state for monitoring. These aren't nice-to-haves — they're what makes a fleet manageable beyond 5 sessions."

**Adversarial Skeptic (for D):** "How many Lyra users will ever run more than 5 concurrent sessions? The 'fleet of 100s' use case is a power user fantasy. The median developer runs ONE session. For them, the daemon is pure overhead. Ship the single-session improvements first, measure fleet demand, THEN build the daemon only if >10% of users run 3+ concurrent sessions."

**Senior SRE (split):** "The Skeptic is right about operational risk — daemons are hard. But the worktree isolation is valuable even for single-session use. An agent that isolates itself before editing, even in ONE session, is safer than one editing the main checkout. Ship worktree isolation as a standalone tool first; add the daemon when fleet demand materializes."

**Senior PM:** "Here's the compromise sequencing: Phase 1 (now): embedding search + model router + skill port + EnterWorktree tool (standalone isolation). Phase 2 (3 months): dynamic workflow engine (single-session — agent/parallel/pipeline primitives). Phase 3 (6 months): supervisor daemon + fleet view + background workflows. This ships value at every phase and validates demand before building the daemon."

### Outcome

**Converged winner:** Candidate B with PM's phased sequencing. The fleet-centric architecture is the destination; the immediate Phase 1 skips the daemon and ships: embedding search, model router, skill port, EnterWorktree tool. Phase 2 adds the workflow engine (single-session). Phase 3 adds the daemon and fleet view — gated behind Phase 1-2 usage data showing demand.

**Steelmanned loser:** Candidate D's "just use tmux" is preserved as a supported configuration for users who want fleet-like behavior without the daemon. Lyra ships a `lyra fleet --simple` mode that uses tmux + status file for ≤5 sessions.

---

## ROUND 3 — Red-Team the Converged Winner

**Motion:** "Attack the converged Fleet-Centric architecture with phased rollout. Find where it breaks, what it quietly assumes, stress the safety angles, and verify it still beats the baseline after revisions."

### Attacks & Rebuttals

**Attack 1 — "The worktree isolation breaks on monorepos."**
*Red Team:* Git worktrees in monorepos (Google-scale, 10GB+) are impractically slow and disk-heavy. Creating a worktree per session would take minutes and use gigabytes.

*Rebuttal (Senior Backend):* Use git worktrees with `--no-checkout` + sparse checkout. Only check out the files the agent actually edits. For non-git repos, the unionfs overlay is the primary path, not the fallback. Add a `worktree.strategy` config: `full` | `sparse` | `overlay`.

**Attack 2 — "The workflow engine's Python scripts are an injection vector."**
*Red Team:* User-provided workflow scripts have full Python access. A malicious skill could inject code into a workflow script.

*Rebuttal (Senior Security):* Workflow scripts run in a restricted Python sandbox (RestrictedPython or PyPy sandbox). No filesystem access except through Lyra tools. No network access except through approved channels. Workflow scripts from untrusted sources require explicit approval.

**Attack 3 — "Adversarial verification doesn't work with the same model."**
*Red Team:* If all verifiers are the same model (e.g., all Sonnet), they share the same biases. Anonymization helps with identity bias but not with model-level bias.

*Rebuttal (Senior AI Researcher):* Valid concern. Mitigation: (1) Cross-model verification — use different models for different verifier roles when available (§4.5 router capability map). (2) Temperature + prompt diversity — same model, different sampling. (3) Accept the limitation: same-model verification is weaker but still better than single-pass. Document this trade-off.

**Attack 4 — "The dreaming engine's PDE solver is overengineered."**
*Red Team:* Field-theoretic memory consolidation via PDEs is elegant but uses exotic infrastructure. The simpler Anthropic approach (LLM reviews N conversations, produces reorganized memory) is more interpretable and debuggable.

*Rebuttal (Senior AI Researcher):* Agreed — the PDE solver is the (B) breakthrough tier and should be gated behind a bake-off vs LLM-based dreaming. The bake-off runs both approaches on the same memory tasks and ships whichever wins on quality-per-dollar. If LLM-based dreaming wins, the field-theoretic approach is parked as a research bet.

**Attack 5 — "Phase 3 is 6+ months out. What if Lyra never gets there?"**
*Red Team:* Most ambitious open-source projects stall before Phase 3. If Lyra only ships Phase 1-2 (embedding, router, skills, single-session workflows), is that enough?

*Rebuttal (Senior PM):* Phase 1-2 alone makes Lyra a top-5 open-source agent harness — embedding search + model router + 330 skills + single-session workflows is more than most competitors have. Phase 3 is the breakthrough that takes Lyra to #1. But even without it, Phase 1-2 is worth building.

### Outcome

The converged architecture SURVIVES red-team with revisions:
1. Worktree strategy configurable (full/sparse/overlay) — addresses monorepo concern
2. Workflow script sandbox (RestrictedPython) — addresses injection concern
3. Cross-model verification where available — addresses same-model bias concern
4. PDE dreaming gated behind bake-off vs LLM-based dreaming — addresses overengineering concern
5. Phased value delivery ensures Lyra wins even if Phase 3 never ships — addresses stall concern

**No fundamental architecture change needed. The revisions are refinements, not redesigns.**

---

## ROUND 4 — Reserved for Resume Pass

(To be filled on next run if a fundamentally better challenger emerges.)
