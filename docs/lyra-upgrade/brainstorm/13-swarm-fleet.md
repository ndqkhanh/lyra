# Brainstorm — Swarm/Fleet/Channels (§4.13)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required
> **Context:** This workstream must replicate Claude Code's "ultracode" stack: supervisor daemon + fleet view + worktree isolation + dynamic workflow engine

## Source Techniques Gathered

| Technique | Source | Core Idea |
|-----------|--------|-----------|
| Agent View Supervisor | Claude Code §3.1 | Per-user daemon, job roster on disk, two-axis state model, cheap row summaries |
| Worktree Isolation | Claude Code §3.1 | Per-session git worktree, .worktreeinclude env propagation, base-ref policy |
| Dynamic Workflows | Claude Code §3.1 | Code-driven orchestration, script variables (not context), resumable, progress view |
| Identity Skews Debate | Choi/Zhu/Li (2510.07517) | Anonymize responses to fix identity bias in multi-agent debate |
| Actor-Observer Asymmetry | Li et al. (2604.19548) | ReTAS dialectical alignment to fix role-induced bias |
| Lying with Truths | Hu et al. (2601.01685) | Collusion attack detection on public channels |
| Preventing Rogue Agents | Barbi et al. (2502.05986) | Monitor + intervene when agent likely to fail |
| Latent Agents | Boston U (2604.24881) | Internalize multi-agent debate into single LLM (93% fewer tokens) |
| GTD Topology Diffusion | Jiang et al. (2510.07799) | Task-adaptive communication topologies via graph diffusion |
| ETI Trait Inference | USC/Amazon (2604.19278) | Infer partner traits for coordination |
| ErrorProbe | KCL/Amazon (2604.17658) | 3-stage failure attribution pipeline |
| RADAR Omission-Aware | (2604.19005) | Dual-threshold early termination for debate |
| Tree-of-Debate | (2502.14767) | Structured debate trees for novelty assessment |
| CollabCoder | (2604.13946) | Plan-Code co-evolution |
| MARS² Tree Search | (2604.14564) | Learnable tree-structured multi-agent search |
| Netflix Adversarial Review | Netflix (May 2026) | Agent A writes → Agent B evaluates → Agent C orchestrates |
| COMPASS Hierarchical | Wan (2510.08790) | Main Agent + Meta-Thinker + Context Manager |
| AOI Multi-Agent IT | (Q16XXJou3O) | 3 agents + context compressor + 3-layer memory |

---

## Breakthrough Idea #1: The Lyra Supervisor — Universal Fleet Daemon with Worktree-Isolated Sessions

**Sources Fused:** Claude Code Agent View (supervisor + fleet view + state model) + Claude Code Worktrees + AOI 3-layer monitoring + COMPASS hierarchical oversight

**Core Mechanism:**
- **Supervisor Daemon (`lyra-daemon`):** A per-user background process (launched on first `lyra fleet` use) that:
  1. Owns all session lifecycle: spawn, monitor, pause, resume, kill, cleanup
  2. Persists state to disk: `~/.lyra/jobs/<id>/state.json` + `roster.json`
  3. Survives terminal close, machine sleep, daemon restart
  4. Hosts each session as its OWN process (not thread — true isolation)
  5. Stops idle unattached sessions after configurable timeout (default 1h)
  6. Self-exits when nothing is live

- **Two-Axis State Model (adopted from Agent View):**
  - **Task-State:** Working / Needs-Input / Idle / Completed / Failed / Stopped
  - **Process-Liveness:** Alive / Exited-But-Resumable / Loop-Sleeping
  - Rows group by: Ready-for-Review / Needs-Input / Working / Completed

- **Worktree Isolation Substrate:**
  1. BEFORE first edit, the session auto-moves into a git worktree under `.lyra/worktrees/<session-id>/`
  2. `.lyrainclude` file (analog of `.worktreeinclude`): copies gitignored-but-needed files (`.env`, secrets, configs)
  3. Base-ref policy: `fresh` (from origin/HEAD) vs `head` (carries unpushed state) — user-configurable
  4. NON-DESTRUCTIVE CLEANUP (Lyra improvement over Claude Code): dirty worktree → auto-stash + archive, NEVER silent-destroy; prompt only as last resort
  5. Non-git fallback: copy-on-write overlay (unionfs/btrfs snapshot) or `WorktreeCreate` hook

- **Fleet View (TUI):**
  - Single-screen terminal view: rows = sessions, grouped by state
  - Cheap-model row summaries (Haiku-class, refreshed ≤ 1/15s or at turn end)
  - Peek panel: latest output / current question / PRs with hotkeys
  - Tab-suggested replies, `!`-prefixed bash, attach/detach that never stops session
  - Filters: by agent, state, PR#
  - Pin/reorder/rename rows

- **Dispatch Surface:**
  - From fleet view input: `lyra fleet --bg "fix the auth bug" --model sonnet --effort high`
  - From inside session: `/bg "run the tests while I think"`
  - Shell: `lyra --bg "deploy to staging" --name deploy-staging --permission-mode ask`

- **Monitoring Hierarchy (COMPASS-inspired):**
  - **Row Summarizer (cheap model):** "What is this session doing/needs/produced" — refreshed per-turn
  - **Meta-Monitor (mid model):** Periodic review of row summaries for anomalies, stuck sessions, collisions
  - **Human (expensive attention):** Steers by exception through fleet view

**Multi-Provider Note:** The supervisor itself is provider-agnostic (it manages processes, not models). Row summaries route through §4.5 router to the cheapest model. Session models are per-session configurable.

**Why It Beats Individual Sources:**
- Claude Code's Agent View doesn't have COMPASS-style hierarchical monitoring
- Claude Code's worktrees silently destroy dirty worktrees — Lyra's are non-destructive
- AOI has 3-layer memory but no fleet view
- COMPASS has hierarchical context but no worktree isolation
- No existing system combines all four: supervisor daemon + worktree isolation + hierarchical monitoring + non-destructive cleanup

**Why It Beats Baseline:**
- Lyra currently has NO fleet layer, NO supervisor, NO worktree isolation, NO monitoring hierarchy
- Agents run in-process — no detached sessions, no concurrent edit safety

**Failure Modes:**
- Supervisor daemon is a single point of failure (mitigation: restart-resumes-from-disk, session processes are independent)
- Worktree setup cost per session (~200-500ms + disk) adds latency (mitigation: lazy worktree creation — only when first edit detected)
- Row summaries may misrepresent state (mitigation: stale-after-15s indicator, manual refresh)

**Impact:** 5 | **Effort:** 5 | **Risk:** Medium-High

---

## Breakthrough Idea #2: Anonymized Adversarial Workflow Engine with Bias-Corrected Voting

**Sources Fused:** Dynamic Workflows (Claude Code) + Identity Skews Anonymization (2510.07517) + Actor-Observer ReTAS (2604.19548) + Lying-with-Truths Detection (2601.01685) + Preventing Rogue Agents (2502.05986) + ErrorProbe Failure Attribution (2604.17658) + RADAR Omission-Aware (2604.19005)

**Core Mechanism:**
Core workflow engine that runs code-driven orchestration scripts. Key differences from Claude Code's engine:

1. **Anonymized Agents:** All inter-agent messages strip identity markers (per 2510.07517) — agents cannot tell if a message came from themselves or a peer. This eliminates identity-weighted Bayesian update bias (IBC → 0).

2. **ReTAS Dialectical Alignment:** When an agent switches from actor to observer role (e.g., after writing code → reviewing it), apply Thesis-Antithesis-Synthesis alignment:
   - Thesis: agent's own output
   - Antithesis: forced counter-argument generation
   - Synthesis: agent reconciles both into a corrected output
   This corrects the >20% bias trigger rate found in Actor-Observer experiments.

3. **Collusion Detection:** Monitor public channels for Lying-with-Truths patterns:
   - Writer-Editor-Director framework detection: sequential truthful evidence fragments that steer beliefs
   - Flag when ≥2 agents' messages show coordinated evidence selection
   - Intervention: isolate flagged agents, re-run with different agent pool

4. **Rogue Agent Prevention:** Per Barbi et al. (2502.05986):
   - Monitor each agent during action prediction
   - Intervene when future error likelihood exceeds threshold
   - WhoDunitEnv-style environment for testing intervention logic

5. **ErrorProbe Failure Attribution:** 3-stage pipeline:
   - Stage 1: Failure-taxonomy anomaly detection
   - Stage 2: Symptom-driven backward tracing
   - Stage 3: Strategist/Investigator/Arbiter team validates via tool-grounded execution

6. **RADAR Dual-Threshold Early Termination:** Debate ends when:
   - Agreement threshold reached OR
   - Diminishing returns threshold reached (additional rounds cost > expected information gain)

7. **Voting with Skeptic:** 3-Verifier Panel (Correctness + Security + Reproducibility) + 1 Adversarial Skeptic. Claim survives only if ≥2/3 confirm AFTER adversarial challenge.

**Why It Beats Individual Sources:**
- Claude Code's workflow verification is a single adversarial check — Lyra's is a multi-layered bias-corrected panel
- Identity Skews paper fixes ONE bias — Lyra combines 4 bias/failure mitigations
- No existing system combines: anonymization + ReTAS + collusion detection + rogue prevention + ErrorProbe + RADAR

**Why It Beats Baseline:**
- Lyra has NO verification, NO debate, NO adversarial checking, NO bias correction

**Failure Modes:**
- Anonymization may reduce useful context (e.g., "the Python expert says...") — mitigation: allow typed-but-not-named attribution
- Collusion detection may have false positives — mitigation: threshold tuning, human review
- Multiple correction layers add latency — mitigation: parallelize, use cheap models for detection

**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Latent Debate — Internalize When Cheap, Externalize When Complex

**Sources Fused:** Latent Agents (2604.24881) + GTD Topology Diffusion (2510.07799) + ETI Trait Inference (2604.19278) + Tree-of-Debate (2502.14767)

**Core Mechanism:**
- **Debate Mode Selector:** For each task, decide: internalize (single-model latent debate) or externalize (multi-agent live debate)?
  - **Internalize when:** Task is well-defined, ambiguity is low, expected benefit of external debate is marginal
  - **Externalize when:** Task is novel, high-stakes, requires diverse perspectives, or has known failure modes
- **Latent Debate (Internalized):** When internalizing, use the 2-stage fine-tuning from Latent Agents to produce a single model that internally simulates multi-agent debate. 93% token savings vs explicit debate.
- **GTD Topology (Externalized):** When externalizing, generate a task-adaptive communication topology via guided discrete graph diffusion:
  - Proxy predicts multi-objective rewards (accuracy/utility/cost)
  - Diffusion generates optimal agent connectivity graph
  - Gradient-free, real-time, balances performance vs token cost vs robustness
- **ETI Coordination:** Agents infer partner traits (warmth/trust, competence/skill) from interaction history to coordinate more effectively (cuts payoff loss 45-77%, +3-29% on MultiAgentBench)
- **Tree-of-Debate Structure:** For novelty/intellectual-property assessment (e.g., "is this idea novel?"), decompose into a structured debate tree where each node is a specific novelty claim argued by a paper-persona agent

**Why It Beats Baseline:**
- Lyra has no debate system at all
- The internalize-vs-externalize decision saves 93% of tokens when debate isn't needed
- GTD adapts topology per task instead of fixed all-to-all or hub-and-spoke

**Failure Modes:**
- Mode selector may choose wrong mode (mitigation: conservative default = externalize for high-stakes)
- Latent debate fine-tuning requires training data from explicit debates (bootstrapping problem)
- GTD topology generation adds latency per task (mitigation: cache common topologies)

**Impact:** 4 | **Effort:** 5 | **Risk:** High

---

## Expert Check (Swarm/Fleet Personas)

**Senior Distributed-Systems Engineer:** "Idea #1 (Supervisor Daemon) is the right architecture — process-per-session, disk-persisted state, survive restarts. But the worktree setup cost per session is real. I'd recommend lazy worktree creation: only `git worktree add` when the first file write is detected, not at session start. And the non-git fallback (unionfs/overlay) needs a concrete implementation — that's the hard part."

**Senior SRE:** "Supervisor daemon as single point of failure — but it's mitigated by disk persistence. The real ops concern is worktree proliferation: 100 sessions = 100 checkouts = potentially 100× disk. Need a cleanup cron and disk quota monitoring. The non-destructive cleanup policy (auto-stash) is the right default — Claude Code's silent-destroy is a data-loss disaster waiting to happen."

**Senior Security Engineer:** "The security guardrail from Agent View — unwatched sessions can't use bypass/auto permissions without prior human accept — is non-negotiable. Also: each worktree needs its own credential scope. A session should NOT inherit the user's full `~/.env` — it gets only the credentials it's explicitly granted."

**Senior AI Engineer:** "The cheap-model row summaries are brilliant economics. A Haiku-class model at $0.25/M tokens for monitoring vs an Opus at $15/M is a 60× cost difference. But the summary quality needs eval — a bad summary may miss a stuck/failing session."

**Adversarial Skeptic:** "Idea #1 is good but it's essentially a port of Claude Code's Agent View with one improvement (non-destructive cleanup). Where's the genuine breakthrough? Idea #2 (anonymized adversarial workflow) is more novel but adds 6+ layers of complexity. The simplest alternative: just use tmux + a status file. Why is the supervisor daemon better than that?"

**Resolution:** Idea #1 (Supervisor) is the foundation — build it as the (A) parity tier. Idea #2 (Anonymized Adversarial Workflow) is the (B) breakthrough tier. The Skeptic's tmux+status alternative is valid for simple cases but breaks on: cross-machine sessions, programmatic fleet management, structured state queries, session resumption after daemon restart, and quota governance. The supervisor daemon earns its complexity when fleet size > 5 sessions. Under 5, tmux is fine — so ship both: tmux integration for small-scale, daemon for fleet scale.
