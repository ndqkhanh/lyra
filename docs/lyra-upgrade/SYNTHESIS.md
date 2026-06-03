# SYNTHESIS.md — Cross-Source State of the Field

> Last updated: 2026-06-03 Run 1 | Status: Under construction (awaiting batch 1 findings)

## How to Read This Synthesis

Each theme below captures:
- **Frontier** — what the newest/strongest work can do (cite sources + numbers)
- **Convergences** — where independent sources agree (strong signal)
- **Contradictions / Open Problems** — where they disagree (breakthroughs live here)
- **Trajectory** — where the theme is heading
- **Gap vs. Lyra Baseline** — behind / at parity / ahead
- **Micro-Debate** — 2-3-turn exchange between owning personas; winner recorded

---

## 1. Memory Architecture

### 1.1 Frontier

<!-- Populated from §3.4 Memory Papers findings -->

### 1.2 Convergences

### 1.3 Contradictions / Open Problems

### 1.4 Trajectory

### 1.5 Gap vs. Lyra Baseline

Lyra already has CraniMem (gated bounded memory), unified memory router (cost-sensitive store routing), and active reconstruction. Lyra is at or near parity with the MemAgent workshop frontier.

### 1.6 Micro-Debate

> **Participants:** Senior AI Researcher (AIR) + Senior Backend Engineer (BE) + Senior Data/Knowledge Engineer (DKE) + Adversarial Skeptic (AS)
>
> **Question:** What is the single most promising memory direction, and is it actually better than what Lyra already has?

**AIR:** The field-theoretic memory paper (Mitra 2026, 2602.21220) is genuinely novel. +116% F1 on multi-session reasoning is not incremental — it's a paradigm shift. Memories as continuous fields governed by PDEs, diffusing through semantic space, decaying thermodynamically by importance. This is the closest thing to "True Memory" — what Hassabis named as one of three missing AGI pieces. CraniMem is a gated discrete store; it's ICLR 2026-level work, but it's still the old paradigm. Field memory captures cross-session dependencies that discrete DBs fundamentally miss, because field diffusion naturally bridges semantically related but temporally distant context without engineered retrieval heuristics.

**BE:** Let me ground this. Field-theoretic memory computes PDEs over a semantic manifold. What's the actual computational cost? For N memories, field gradient computation is at minimum O(N²) — N×(N-1)/2 pairwise interactions for a naive diffusion kernel. CraniMem does O(log N) lookup. At 10,000 memories (a busy Lyra session over a month), that's 50 million pairwise computations for the field approach vs ~14 B-tree lookups for CraniMem. Where are we running these PDEs — on CPU between LLM calls? That adds seconds of latency per retrieval. On GPU? Now Lyra has a GPU dependency. And the paradigm is untested past 500 turns. What happens at 10,000 turns? Does the field saturate?

**DKE:** I'll add: field memory is theoretically beautiful but operationally opaque. If a user asks "why did Lyra recall X instead of Y?", CraniMem can point to the discrete entry, the retrieval score, the gate decision. Field memory can only say "the field gradient at this semantic point was X" — which is essentially unexplainable. For a tool users need to trust, explainability matters as much as accuracy. The +116% F1 is on LongMemEval's multi-session reasoning — that's a specific task. On simple fact retrieval, do we really need PDEs?

**AS:** Here's the boring alternative: don't implement either field memory or keep just CraniMem. Add ONE thing: a cross-session consolidation loop ("Dreaming", §4.24) that runs a cheap model during idle to replay recent conversations, merge duplicates, resolve contradictions, and surface patterns. Anthropic's Harvey saw ~6× task completion improvement with this pattern — no PDEs required. The consolidation output gets written back to CraniMem as structured entries. Field memory is a research bet; Dreaming consolidation is a proven pattern. Why build the research bet before the proven pattern?

**AIR responds:** The consolidation loop is complementary, not competing. You consolidate INTO what? CraniMem? That's still discrete entries. The consolidation is more powerful when the substrate supports continuous, graded relationships. And "proven" is relative — Anthropic's Dreaming is a blog post, not a peer-reviewed paper with ablations. Field memory has peer-reviewed numbers. As for computational cost: the PDE doesn't need to run on EVERY retrieval. Run it periodically during idle (during Dreaming consolidation), compute the field once, and snapshot the gradients as a precomputed index. Retrieval from the snapshot is O(log N) — same as CraniMem.

**BE:** If we're running the PDE during idle anyway, why not just run a cheaper discrete consolidation during idle and avoid the PDE complexity entirely? The Skeptic's point stands: consolidation + CraniMem gives you 80% of the gain at 20% of the complexity.

**AIR:** Because the 80/20 heuristic assumes the remaining 20% of gain isn't qualitatively different. +116% F1 on multi-session reasoning IS qualitatively different — that's the difference between "the agent remembers what we talked about yesterday" and "the agent connects something from three weeks ago to today's task without being explicitly told." CraniMem can't do the latter because it stores discrete entries — it can't bridge temporal gaps through continuous diffusion.

**Tentative Winner:** **Layered approach.** CraniMem remains the fast, explainable, discrete short-term store. Add a field-theoretic long-term layer that runs PDE-based consolidation during Dreaming idle cycles. The field layer doesn't replace CraniMem; it feeds consolidated, cross-session patterns back into CraniMem as enriched discrete entries. This gives the +116% cross-session benefit at idle-time compute cost, preserves CraniMem's O(log N) retrieval latency, and keeps discrete explainability for user-facing queries. The field layer is the "Dreaming engine" — it's what powers the consolidation, not what serves live queries.

**AS objection recorded:** "Layered" is still complex. The Skeptic maintains that CraniMem + cheap-model consolidation loop (no PDEs) should be built and benchmarked first, and field memory added only if CraniMem+consolidation doesn't close the gap. The debate is settled as: build consolidation first (baseline), add field layer next (breakthrough), measure both.

---

## 2. Context Optimization & Compaction

### 2.1 Frontier

<!-- Populated from §3.4 KV-Cache papers + §3.17 context sources -->

### 2.2 Convergences

### 2.3 Contradictions / Open Problems

**Key tension:** Three competing strategies for context scaling:
1. **Manage** — COMPASS-style hierarchical framework (meta-thinker overseeing context manager)
2. **Distribute** — ExtAgents-style distributed knowledge across agents (no long-context training needed)
3. **Field-Memory** — Field-theoretic continuous memory governed by PDEs (Mitra 2026)

Each claims superiority; none has been tested head-to-head.

### 2.4 Trajectory

### 2.5 Gap vs. Lyra Baseline

Lyra has auto_compaction.py (324L) and kv_cache.py — solid parity with standard compaction. Missing: COMPASS meta-thinker layer; field-theoretic approach.

### 2.6 Micro-Debate

> **Participants:** Senior AI Engineer/LLMOps (AIE) + Senior Performance/Cost Engineer (PCE) + Adversarial Skeptic (AS)
>
> **Question:** Best context-scaling strategy vs Lyra's auto-compaction?

**AIE:** Three strategies: COMPASS (2510.08790) hierarchical Meta-Thinker, ExtAgents (2505.21471) distributed knowledge, Field memory (2602.21220) PDE-governed. For Lyra: COMPASS-style structured progress briefs maintained by a cheap model are the most pragmatic. auto_compaction.py compresses raw output; COMPASS understands what matters semantically.

**PCE:** lean-ctx (§3.17) claims 89-99% token reduction via transparent shell hooks. Is COMPASS better than lean-ctx as a pre-processor? The Skeptic bets: lean-ctx + auto_compaction = 90% benefit at 10% complexity.

**AS:** Correct. The layers are complementary: lean-ctx compresses tool output (500→10 lines), auto_compaction compresses conversation history, COMPASS-style briefs track long-horizon task state. Ship lean-ctx first, measure, then add COMPASS if needed.

**Tentative Winner:** **Layered compression** — lean-ctx (CLI output) → auto_compaction (history) → structured briefs (task state).

---

## 3. Skills & Self-Evolution

### 3.1 Frontier

<!-- Populated from §3.7 + §3.18 -->

### 3.2 Convergences

### 3.3 Contradictions / Open Problems

**Key tension:** Prompt-only evolution vs. weight-level evolution vs. training-free evolution:
- **GEPA** (ICLR 2026 Oral): gradient-free prompt evolution beats GRPO
- **SEAL** (MIT): weight-level self-edits via RL
- **TF-TTCL**: training-free, any provider (Explore-Reflect-Steer)
- **Hyperagents/DGM-H**: self-rewriting harness, cross-domain transfer

### 3.4 Trajectory

### 3.5 Gap vs. Lyra Baseline

Lyra has lyra-skill-evolution, lyra-skill-generator, lyra-skill-weaver, lyra-meta-evolution, lyra-policy-optimizer — strong baseline. Gap: SkillNet graph model not integrated; GEPA-style gradient-free evolution not wired.

### 3.6 Micro-Debate

> **Participants:** Senior AI Researcher (AIR) + Senior Backend (BE) + Senior AI Safety Engineer (SAF) + Adversarial Skeptic (AS)

**AIR:** 2026 is the year of self-improving agents. Hyperagents/DGM-H (2603.19461) shows meta-skills transfer across 4 domains. GEPA (ICLR 2026 Oral) shows gradient-free prompt evolution beats GRPO. TF-TTCL (2604.13552) works on ANY provider via Explore-Reflect-Steer. SkillNet (2603.04448) auto-generates skill packages with 5-dimension quality scoring. Lyra's lyra-evolution package is well-positioned but the meta-modification procedure isn't itself editable.

**SAF:** "Your Agent May Misevolve" (2509.26354) documents three self-evolution failure pathways: safety-alignment decay, tool-creation vulnerabilities, regressive evolution. DGM-H was tested in sandboxes. Lyra runs on users' machines. The safety risk of self-modification is too high for v1. But GEPA-style prompt evolution (gradient-free, non-weight-modifying) is safe — it only changes prompts, not code. TF-TTCL is also safe (training-free). Ship the safe evolution paths; gate the dangerous ones.

**BE:** SkillNet's graph model (similarity/composition/dependency) is the highest-ROI. It auto-generates skill packages from GitHub repos, PDFs, conversation logs, or execution trajectories. That's an instant skill library bootstrap. No agent self-modification needed — just better skill curation.

**AS:** Ship SkillNet graph + GEPA prompt evolution. Self-modifying meta-agent parked (Round 1 already decided). The incremental path: better skill curation → prompt optimization → (future) meta-agent when safety guardrails mature.

**Tentative Winner:** **Safe evolution only.** SkillNet graph for curation (A), GEPA/TF-TTCL for prompt optimization (B), self-modification parked.

---

## 4. Model Routing & Economics

### 4.1 Frontier

<!-- Populated from §3.14 + §3.22 -->

### 4.2 Convergences

### 4.3 Contradictions / Open Problems

### 4.4 Trajectory

### 4.5 Gap vs. Lyra Baseline

Lyra has effort_router.py, phase_router.py, unified_memory_router.py, context_router.py, lyra-cost, lyra-sla — solid. Gap: DeepSeek reasoning budget mapping; Amdahl's law parallelism optimization.

### 4.6 Micro-Debate

> **Participants:** Senior AI Engineer/LLMOps (AIE) + Senior Performance/Cost Engineer (PCE) + Senior Software Architect (SA)

**AIE:** The router must solve: which model for which task, which provider for which effort level, when to escalate. RouteLLM (2406.18665, LMSYS/Berkeley) provides the reference architecture: a lightweight router model that predicts which LLM will perform best for a given prompt. BEST-Route (2506.22716, ICML 2025) adds dynamic difficulty estimation — route simple tasks to cheap models, hard tasks to expensive ones. "Knowledge Access Beats Model Size" (2603.23013) shows memory lets cheap models handle repeat queries. Lyra's effort_router.py (329L) exists but doesn't have difficulty estimation or memory-cache routing.

**PCE:** The economics: cheap model calls cost $0.0001-0.001/token; expensive models cost $0.01-0.05/token. A 100:1 cost ratio. If the router routes 80% of queries to the cheap model correctly, cost drops 80× with minimal accuracy loss. But misrouting 20% to the cheap model when the expensive was needed costs accuracy. The router's precision isn't the only thing — the cost of misrouting matters. BEST-Route's dynamic difficulty estimation is the key: it predicts not just "which model" but "how hard is this query." For Lyra: use the cheapest model for meta/monitoring (row summaries, health checks), mid-tier for routine tasks, top-tier for reasoning-heavy work.

**SA:** The provider × effort matrix is the multi-provider challenge. Anthropic supports low→max on Opus 4.8. DeepSeek's effort mechanism is different (prompt-level, not API-level). The router needs per-provider capability declarations (like Claude Code's `_SUPPORTED_CAPABILITIES` env vars). Define a `ProviderCapability` enum and a `CapabilityMap` per provider. Route based on: task_type → model → provider with capability. Fallback chain: try Anthropic → try DeepSeek → try cheapest that supports the capability.

**Tentative Winner:** **Cost-weighted routing with difficulty estimation.** Tier 0 (Haiku-class, meta/monitoring, <$0.001/call), Tier 1 (Sonnet-class, routine, $0.003/call), Tier 2 (Opus-class, reasoning, $0.015/call). Route by BEST-Route difficulty estimation + Knowledge Access memory cache for repeats.

---

## 5. Swarm / Orchestration / Fleet

### 5.1 Frontier

<!-- Populated from §3.12 + §3.1 Agent View -->

### 5.2 Convergences

### 5.3 Contradictions / Open Problems

**Key tensions:**
1. **Explicit vs. Internalized Debate** — Latent Agents (2604.24881) claims 93% fewer tokens by distilling debate INTO the model; our explicit adversarial panels are costly. When should Lyra internalize?
2. **Debate Reliability** — Multiple papers (Identity Skews, Actor-Observer Asymmetry, Lying with Truths, Preventing Rogue Agents, MATU) show debate is biased and fragile. Fixes exist (anonymization, ReTAS, monitoring) but add complexity.
3. **Fleet vs. Swarm** — Agent View manages independent top-level sessions; channels enable inter-agent messaging; subagents spawn within a session. The boundary matters for safety.

### 5.4 Trajectory

### 5.5 Gap vs. Lyra Baseline

Lyra has DAG workflow engine, adversarial verification, autonomy loop, fleet TUI, channels, colony patterns — strong for in-session orchestration. Gap: Agent View-style supervisor daemon (detached background sessions, two-axis state model, per-session autoscaling, cheap-model row summaries); worktree isolation auto-trigger.

### 5.6 Micro-Debate

> **Participants:** Senior Distributed-Systems Engineer (DSE) + Senior SRE + Senior Software Architect (SA) + Adversarial Skeptic (AS)
>
> **Question:** What is the single most impactful fleet/orchestration upgrade, and is it actually better than what Lyra already has?

**DSE:** The Agent View supervisor daemon is the single highest-leverage port. Right now Lyra can spawn subagents within a session (workflow.py DAG engine), but it can't run independent detached sessions that survive terminal close. The supervisor daemon is the spine — it enables everything else: unattended autonomy (§4.14), steer-by-exception UX (§4.22), and true fleet parallelism (§4.13). Without it, Lyra's "fleet" is really just in-session fan-out. Claude Code's supervisor design is well-documented: per-user daemon, per-session process isolation, state on disk (roster.json + jobs/<id>/state.json), survives sleep/restart/auto-update, respawns idle sessions on demand. The two-axis state model (task-state × process-liveness) is the right abstraction.

**SRE:** I want to stress-test the supervisor's failure modes. It's a single point of failure — if the supervisor goes down, ALL sessions go down. Claude Code handles this via daemon auto-restart with reconnection, but it's still a SPOF. Also: what happens when 50 background sessions each spawn 16 subagents? That's 800 processes — the supervisor needs backpressure. Lyra should build the supervisor with explicit resource governance: max concurrent sessions per user, per-session CPU/memory quotas, and graceful degradation when approaching limits. Claude Code's "stop idle after ~1h" is a start but it's reactive, not proactive.

**SA:** The boundary between supervisor (session lifecycle), rmux (§5.1, PTY/detach), git-worktrees (per-session file isolation), and swarm/channels (inter-agent comms) needs to be crystal clear. Claude Code's design resolves this as:
- Supervisor: owns session PROCESS lifecycle (spawn, stop, respawn, idle-timeout, memory-pressure eviction)
- Worktrees: owns FILE isolation (auto-create before first edit, per-session branch, cleanup)
- Terminal (implicit): PTY hosting for attached sessions; background sessions have no PTY
- Channels/Teams: inter-agent messaging (separate from supervisor — sessions message each other, supervisor doesn't mediate)

Lyra needs the same clean separation. The Skeptic will push the minimal-change alternative for each.

**AS:** Let me push each one: (1) Supervisor: tmux + a thin JSON status file per pane. You don't need a daemon — tmux already detaches sessions. The "status file" gets written by a hook on session end. A simple script reads status files to render the fleet view. (2) Worktrees: just `git worktree add` before starting a session. No auto-trigger needed — it's one command the user runs. Or use a temp directory with a copy-on-write overlay (unionfs) that's lighter than a full worktree. (3) Terminal: tmux already does PTY hosting. rmux rebuild is about making it pretty, not building a new PTY layer. (4) Channels: file-based message passing (write to a known directory). No need for a message broker.

My point: each of these "breakthroughs" has a 50-line shell script alternative. Prove the complexity of a daemon, a full worktree integration, and a message bus beats the shell script version on evidence.

**DSE responds:** (1) tmux + status file: tmux can't respawn a stopped session from disk state. When a session has been idle for an hour and its process was killed, tmux has no mechanism to restart it from the saved transcript. The supervisor does this automatically on next peek/attach — that's the core value, not just process hosting. (2) Temp dir + unionfs: a copy-on-write overlay doesn't give you git branches — you can't `git push` from it, can't open a PR from it, can't merge it. Worktrees share git history, so `git fetch` serves all of them. The branch IS the audit trail. (3) File-based channels: file polling for inter-agent messages in a 100-agent fleet means either polling latency (seconds) or inotify complexity (OS-specific). A lightweight pub/sub bus (even in-process) is simpler, faster, and more reliable than file-based message passing.

**SRE:** On the "50-line script" claim: a 50-line script that implements supervisor behavior (spawn, stop, respawn, idle-timeout, memory-pressure eviction, state persistence, reconnection across sleep/restart) doesn't exist in practice. The "simple" version grows to 500 lines the moment you handle edge cases: what if the status file is corrupt? What if two sessions write simultaneously? What if the machine sleeps mid-write? The daemon is 500 lines of careful state-machine code, not 50 lines of shell. The question is whether 500 lines of daemon is better than 500 lines of shell scripts that approximate it — and the daemon wins on reliability because it has a single-threaded event loop, not a flock of cron jobs.

**Tentative Winner:** **Build the supervisor daemon, but with Skeptic-driven minimalism.** Layer 1 (MVP): supervisor process that spawns/stops/respawns sessions, persists state to JSON on disk, survives sleep. No worktree auto-trigger yet — user runs `claude --worktree` manually. Fleet view reads from disk (no daemon protocol needed). Layer 2: auto-worktree isolation. Layer 3: cheap-model row summaries. The Skeptic's "do the simplest thing first" wins as the implementation strategy, but the daemon itself beats the shell-script alternative once you count edge cases.

**SA boundary resolution (carried into Architecture Debate Round 3):**
- **Supervisor:** Session process lifecycle (spawn, monitor, stop, idle-timeout, memory-pressure)
- **rmux (§5.1):** Terminal multiplexing (PTY hosting, detach/reattach, scrollback, tmux-like UI)
- **Worktrees:** Per-session file isolation (EnterWorktree tool, .worktreeinclude env propagation, non-destructive cleanup)
- **Channels/Swarm:** Inter-agent message passing (pub/sub, not mediated by supervisor)
- No two reimplement each other. rmux provides the attach surface; supervisor decides WHAT to attach to.
- **Non-destructive cleanup decision:** Lyra defaults to AUTO-STASH on dirty worktree removal, never silent-discard. User can configure to archive/confirm/prompt.
- **Per-session quota:** Governed via §4.5 router (cheapest model for meta/monitoring) + explicit session-count limits (default: 10 concurrent, configurable).

---

## 6. Voice & Audio

### 6.1 Frontier

<!-- Populated from §3.13 -->

### 6.2 Convergences

### 6.3 Contradictions / Open Problems

### 6.4 Trajectory

### 6.5 Gap vs. Lyra Baseline

Lyra has lyra-voice (pipeline, SFX, providers, hooks) and lyra-speech — partial. Gap: Full-duplex real-time pipeline (VAD→STT→LLM→TTS with barge-in); turn-taking; emotion/prosody; multilingual VI+EN; benchmark evaluation.

### 6.6 Micro-Debate

> **Participants:** Senior Voice/Audio Engineer (VAE) + Senior AI Engineer (AIE) + Senior UX Designer (UX)

**VAE:** The cascaded pipeline (Whisper→LLM→Kokoro) is proven but takes 800-2750ms end-to-end. Moshi (2410.00037) achieves 160ms theoretical with full-duplex speech-to-speech — no cascaded latency sum. The breakthrough is Moshi's Inner Monologue: predict text tokens before audio tokens → free streaming ASR/TTS. But Moshi's codec is CC BY-NC-SA 4.0 (non-commercial). For MIT Lyra: train our own codec or use an Apache-licensed alternative. Smart Turn (pipecat-ai) gives barge-in for cascaded pipeline in the meantime.

**AIE:** Training a speech-to-speech model is a 12+ week research project. Ship the cascaded pipeline first. Measure latency. If it feels sluggish (>1s E2E), invest in S2S. If <1s feels fine, the cascaded pipeline is good enough. Smart Turn barge-in makes latency less critical — users can interrupt.

**UX:** Push-to-talk default. Always-listening is opt-in. VI+EN support is table stakes (Lyra's target market). Whisper large-v3 supports both but VI accuracy is lower than EN — test with real VI speech. Voice packs (Warcraft peon, etc.) are a delight feature, not MVP — ship them last.

**Tentative Winner:** **Cascaded pipeline MVP, S2S gated on latency measurement.** Ship Smart Turn barge-in for natural interaction feel.

---

## 7. Reliability & Safety

### 7.1 Frontier

<!-- Populated from §3.15 + §3.16 + §3.12 reliability cluster -->

### 7.2 Convergences

### 7.3 Contradictions / Open Problems

### 7.4 Trajectory

### 7.5 Gap vs. Lyra Baseline

Lyra has adversarial verification, safety governance, tool gating, gates (chain_of_note, kg_fact, retraction, dual_use), sandbox — strong. Gap: Collusion detection (Lying with Truths); Actor-Observer bias correction; MATU tensor UQ; response anonymization.

### 7.6 Micro-Debate

> **Participants:** Senior Security Engineer (SEC) + Senior AI Researcher (AIR) + Senior SRE + Adversarial Skeptic (AS)
>
> **Question:** What's the single most important reliability/safety upgrade, and is it actually better than what Lyra already has?

**SEC:** The Lying with Truths attack (2601.01685) is the wake-up call. 74.4% attack success rate on proprietary models, >60% downstream deception cascade. Standard factuality checks are useless — every fragment is true. Lyra's channels are an open attack surface: any agent sharing a channel with other agents can be cognitively colluded. This isn't theoretical — it's an ACL 2026 Oral with a concrete Writer-Editor-Director framework. The fix: cross-source triangulation gate. Any claim synthesized from channel evidence must be verified against at least 2 independent sources before acceptance. Cost: 1-2 extra verification calls per claim. Benefit: breaks the single-channel collusion vector.

**AIR:** The attack is real, but focusing on collusion defense misses the bigger picture. The cluster of papers together — Identity Skews (ACL 2026 Main), Actor-Observer Asymmetry, Preventing Rogue Agents — all point to the same thing: multi-agent debate/review is SYSTEMATICALLY biased and fragile. The individual fixes are known (anonymization, ReTAS, monitoring), but nobody has integrated them. The breakthrough is integrating ALL FOUR: anonymize the debate, apply dialectical alignment, monitor for rogue actions, AND cross-source triangulate channel evidence. One integrated verification panel architecture, not four separate patches.

**SRE:** I'll add the operational angle. The Preventing Rogue Agents monitor (2502.05986) is a pre-execution guard — it watches agent confidence and intervenes BEFORE error propagation. The autonomy loop already has crash detection (reactive) but no confidence monitoring (predictive). Adding this is a 2-week task: wire the confidence signal from the model response into a gating decision. False positive = agent blocked unnecessarily (annoying). False negative = rogue action propagates (the current state). The 20% gain on GovSim suggests task interdependence amplifies the benefit — the more agents depend on each other, the more rogue prevention matters. Lyra's swarm IS interdependent.

**AS:** Let me push the minimal-change alternative. Anonymization (2510.07517) is a prompt-level fix — it costs nothing in architecture, just strip identity markers from verification round prompts. Estimate: 50 lines of code to add anonymization to the existing adversarial verifier. That alone fixes the dominant debate pathology (sycophancy). ReTAS dialectical alignment adds token cost per verification round. The rogue monitor adds latency per agent action. The cross-source triangulation adds API calls. Before building the integrated architecture, ship anonymization as a one-line prompt change and MEASURE whether it improves Lyra's verification accuracy. If it does, do ReTAS next. If ReTAS helps, add the monitor. Incremental, measured, evidence-driven. Don't design the integrated architecture before proving each component earns its cost.

**SEC responds to AS:** The incremental approach works for identity bias (anonymize → measure). It doesn't work for collusion defense — by the time you detect a collusion attack in production, the victim agent has already internalized the false belief AND propagated it to others (>60% cascade). You can't A/B test safety defenses the way you A/B test UX. Some defenses need to be in place BEFORE the attack, not measured after. Cross-source triangulation is one of those — it's a gate, not an optimization.

**Tentative Winner:** **Incremental hardening with one exception.** Ship anonymization first (cheapest, highest-impact — 50 lines, fixes sycophancy). Ship ReTAS dialectical alignment second (moderate cost, fixes perspective asymmetry). Ship the rogue monitor third (predictive, prevents cascading failures). BUT: ship cross-source triangulation alongside anonymization — it's a safety gate, not an optimization, and the 74.4% attack success rate means it can't wait for A/B validation. The integrated architecture emerges from these four components working together, not from an upfront design.

---

## 8. Autonomy & Self-Knowledge

### 8.1 Frontier

### 8.2 Convergences

### 8.3 Contradictions / Open Problems

### 8.4 Trajectory

### 8.5 Gap vs. Lyra Baseline

### 8.6 Micro-Debate

> **Participants:** Senior AI Researcher (AIR) + Senior SRE + Senior PM + Adversarial Skeptic (AS)

**AIR:** The autonomy stack needs three layers: (1) self-knowledge — Lyra knows when it's failing (MATU tensor UQ, 2604.08708; Q-DAPS difficulty estimation, 2605.12398), (2) continuous operation — the supervisor daemon enables unattended sessions, and (3) auto-orchestration — the ultracode toggle lets Lyra decide to run workflows. Self-knowledge is the prerequisite: you can't safely run unattended if you don't know when you're wrong.

**SRE:** Lyra's autonomy.py (449L) already has crash detection (3 crashes/300s window), watchdog health checks, and auto-repair. What's missing: calibrated confidence (the "I don't know" signal). MATU quantifies uncertainty for multi-agent systems via tensor decomposition of reasoning trajectories. Q-DAPS estimates question difficulty as entropy over candidate answers. These are usable uncertainty signals that don't require model internals (provider-agnostic). Add calibrated confidence → gate autonomy decisions.

**PM:** The ultracode auto-orchestration toggle ships in Phase 1 of the architecture. Self-knowledge ships in Phase 2. Continuous autonomy (unattended) ships in Phase 3 (supervisor). The sequencing is deliberate: you can't run unattended without the supervisor; you shouldn't run unattended without calibrated confidence.

**AS:** The simplest autonomy: a `/loop` command that runs a prompt every N minutes. No self-knowledge, no supervisor, no auto-orchestration. Just a cron-like trigger. Ship /loop first, measure whether users actually want unattended operation, THEN invest in the full autonomy stack.

**Tentative Winner:** **Sequenced autonomy.** `/loop` as MVP (Skeptic wins — cheap, immediate), confidence calibration from MATU/Q-DAPS, supervisor-powered unattended sessions gated on safety guardrails.

---

## 9. Planning & Reasoning

### 9.1 Frontier

### 9.2 Convergences

### 9.3 Contradictions / Open Problems

### 9.4 Trajectory

### 9.5 Gap vs. Lyra Baseline

### 9.6 Micro-Debate

> **Participants:** Senior Planning/Reasoning Specialist (PRS) + Senior AI Engineer (AIE) + Adversarial Skeptic (AS)

**PRS:** The planning frontier: MCTS over agent workflows (AFlow, ICLR 2025), MCTS + in-trial/cross-trial memory (MC-DML, ICLR 2025), MCTS with value agent for repo-level SWE tasks (SWE-Search, ICLR 2025). The key insight: explicit search (MCTS/ToT) beats single-pass reasoning on complex tasks BUT costs 3-10× more tokens. The question is WHEN to plan. Q-DAPS (2605.12398) estimates question difficulty as entropy — when entropy is high, invoke planning. When entropy is low, single-pass is cheaper and equally good. This is the "planning trigger."

**AIE:** MCTS costs tokens. AFlow's MCTS over workflows searches the space of agent compositions — each node evaluated by an agent roll-out. If each roll-out costs $0.50 and AFlow explores 20 nodes, that's $10 per plan. For a coding task that a single pass could solve for $0.50, the 20× cost is only justified if MCTS succeeds where single-pass fails. The trigger matters: plan only when difficulty warrants it.

**AS:** Q-DAPS difficulty estimation is still a model call (cheap, but not free). A simpler trigger: if Lyra has failed the same task twice, invoke planning. Reactive, not predictive, but zero-cost and simple. Ship the reactive trigger first; add predictive difficulty estimation when you have calibration data.

**Tentative Winner:** **Reactive planning trigger.** Fail twice → escalate to MCTS planning. Predictive trigger (Q-DAPS) added when calibration data exists. MCTS over workflows (AFlow pattern) as the planning engine.

---

## 10. Human Steering & UX

### 10.1 Frontier

### 10.2 Convergences

### 10.3 Contradictions / Open Problems

### 10.4 Trajectory

### 10.5 Gap vs. Lyra Baseline

### 10.6 Micro-Debate

> **Participants:** Senior UX Designer (UX) + Senior Product Manager (PM) + Senior SRE + Adversarial Skeptic (AS)

**UX:** The Agent View UX is the reference: peek without attach (Space), suggested reply (Tab), PR status indicators, state-grouped rows, filters (a:agent, s:state, #PR), Ctrl+T to pin. Lyra's fleet TUI (4 files) has none of this. The fleet view IS the steering surface — if users can't quickly see what needs them, they won't trust unattended operation. Ship the full peek/reply/attach/detach UX before shipping unattended sessions.

**PM:** Two UX tiers. Minimum viable fleet view: state-grouped rows, peek panel, attach/detach. Delight tier: filters, pin, rename, suggested reply, cost-per-session display. Ship minimum viable in Phase 4 of the architecture; iterate to delight based on usage data.

**SRE:** The "steer by exception" model (Claude Code's design) is the right one. Users shouldn't watch transcripts; they should watch states. When a session transitions to Needs-input or opens a PR, it surfaces. Otherwise, it stays out of the way. The cheap-model row summary is the enabler — users read one line, not 50 turns.

**AS:** The simplest steering: a `lyra fleet status` command that prints a text table. No TUI, no peek panel, no keyboard shortcuts. Just a table of sessions with state and last output line. Ship that first (1 day of work), get feedback, THEN build the fancy TUI. The Skeptic bets users will ask for the fancy TUI organically — don't build it without demand.

**Tentative Winner:** **Progressive disclosure of steering complexity.** Layer 1: `lyra fleet status` text table. Layer 2: state-grouped TUI with peek/attach. Layer 3: full Agent-View parity (filters, pin, suggested reply). Ship Layer 1 in Phase 3, Layer 2 in Phase 4.

---

## 11. Ingestion & Knowledge

### 11.1 Frontier

### 11.2 Convergences

### 11.3 Contradictions / Open Problems

### 11.4 Trajectory

### 11.5 Gap vs. Lyra Baseline

### 11.6 Micro-Debate

> **Participants:** Senior Data/Knowledge Engineer (DKE) + Senior AI Researcher (AIR) + Adversarial Skeptic (AS)

**DKE:** The ingestion stack needs: codebase indexing (repo-level retrieval), multimodal ingestion (PDF/image/audio), freshness tracking (when does indexed content become stale?), and incremental re-indexing. Lyra's knowledge graph (lyra-knowledge-graph) and ETL pipeline (lyra-etl-pipeline) exist but need hardening. Key sources: "Is Grep All You Need?" (2605.15184) — grep often beats vector retrieval for code search, so the harness matters more than the retriever. ClusterRAG (2605.18769) — two-level retrieval (cluster + document) for personalization. MASS-RAG (2604.18509, ACL 2026 Findings) — role-specialized agents for noisy/incomplete evidence.

**AIR:** The grep paper validates Lyra's harness-first thesis for the search surface. The harness (which tool is invoked, how results are formatted) matters more than the underlying retrieval algorithm. For code: grep + ripgrep + AST search. For docs: hybrid dense+sparse with freshness scoring. For conversations: CraniMem. The ingestion architecture is a pipeline, not a single retriever.

**AS:** The simplest ingestion: `grep` for code, file read for docs, CraniMem for memory. Ship that first. Add vector retrieval and multimodal only when grep fails. The Skeptic's bet: 80% of agent queries are answered by grep + file read + memory lookup.

**Tentative Winner:** **Harness-first ingestion.** grep/ripgrep for code, CraniMem for memory, file read for docs. Vector/graph retrieval added as fallback when grep fails, not as primary path.

---

## Cross-Cutting Insights

### The Harness > Model Consensus
Multiple independent sources (OpenAI, Netflix, Anthropic, ThoughtWorks, the grep paper) converge on: the harness quality matters more than model selection for agent success. This validates Lyra's harness-first thesis (§3.28).

### The Self-Evolution Frontier
2026 is the year of self-improving agents: Hyperagents, Dr. Zero, MetaAgent-X, MetaClaw, SOLAR, SEAL, GEPA, TF-TTCL. The field is moving from prompt engineering to autonomous optimization. Lyra's lyra-evolution package is well-positioned.

### The Memory Bottleneck
Hassabis (Google DeepMind) names "True Memory" as one of three remaining AGI gaps. The ICLR 2026 MemAgent workshop shows a Cambrian explosion of memory architectures — but no clear winner yet. This is where Lyra's breakthrough should land.

### The Multi-Agent Reliability Crisis
A cluster of 5+ papers from different groups all find that multi-agent debate/review is systematically biased and fragile. This is a real problem for Lyra's adversarial verification panels. The fixes (anonymization, ReTAS, monitoring) are known but not integrated.
