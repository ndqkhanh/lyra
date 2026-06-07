# Workstream Plan: Multi-Agent Fleet Orchestration

> **Plain-language summary:** Lyra needs a supervisor daemon managing detached background sessions with two-axis state, a fleet view for exception-steering, worktree-based file isolation, and a tiered orchestration system spanning from simple parallel dispatch to self-organizing agent teams with adversarial verification. This plan builds the fleet infrastructure in 6 layers with 5 breakthrough proposals derived from 16 deep-read sources.

---

## Evidence Base

Sources actually consulted and cited in this plan:

1. **Anthropic Engineering Blog** (web, June 2025) -- Multi-agent research system: orchestrator-worker pattern, +90.2% gain, effort-scaling heuristics, external memory persistence, parallel subagent spawning
2. **Claude Code Agent View** (web, code.claude.com/docs) -- Supervisor daemon architecture, two-axis state model, cheap-model row summaries, auto-worktree isolation, idle reaping, memory-pressure eviction
3. **Claude Code Worktrees** (web, code.claude.com/docs) -- Git worktree isolation, `.worktreeinclude`, `EnterWorktree` tool, base-ref config, cleanup state machine
4. **Claude Code Dynamic Workflows** (web, code.claude.com/docs) -- Script-driven orchestration, adversarial cross-check as built-in pattern, progress view, resumability, 16-concurrent/1000-total caps
5. **Claude Code Agent Teams** (web, code.claude.com/docs) -- Peer communication via mailbox, shared task list, plan-approval workflow, competing-hypotheses debugging pattern
6. **MetaAgent-X** (paper, 2605.14212v1) -- Stagewise Designer-Executor co-evolution via end-to-end RL, +11.17% avg across 6 benchmarks, hierarchical rollout (M=4 designs x N=4 executions), decomposed advantage estimation
7. **MARS^2** (paper, 2604.14564v1) -- Multi-agent tree search, Thompson sampling over agent-node pairs, tree-consistent reward shaping with mixed baselines, +8.0% Pass@1
8. **Preventing Rogue Agents** (paper, 2502.05986v2) -- Pre-execution confidence monitoring via entropy/varentropy/kurtosis features, polynomial ridge classifier, +12.4% avg success with double-reset intervention
9. **AI Auto-Research Roadmap** (paper, 2605.18661v1) -- 270+ systems cataloged, layered architecture convergence (exploration + execution + verification), lifecycle framework with 8 stages across 4 phases
10. **AFlow** (paper, 2410.10762v4) -- MCTS-driven workflow search over code-represented workflows, +5.7% over human-designed baselines, GPT-4o-mini + AFlow matches GPT-4o at 4.55% cost
11. **Dialectic-Med** (paper, 2604.11258v1) -- 3-agent adversarial debate with Visual Falsification Module, +8.18% diagnostic accuracy, -46.3% hallucination, Dynamic Consensus Graph with path integration
12. **AutoScientists** (paper, 2605.28655v1 + repo mims-harvard/AutoScientists) -- Self-organizing hypothesis-based teams, peer-review-before-compute, noise-gated champion propagation, +8.33% BioML-Bench, 7 accepted improvements vs. 0 single-agent
13. **Argus** (paper, 2605.16217v3) -- Evidence DAG with Navigator-Searcher architecture, 1200:1 context compression, +12.6 GAIA over best proprietary, log-linear scaling K=1 to K=64
14. **Safety Risks in Self-Evolving Agents** (paper, 2604.16968v1) -- Experience-driven self-evolution systematically increases attack success rate across 7 models, execution bias from benign experience, integrated gradients causal attribution
15. **Build Multi-Agent System from Scratch** (book, Fajardo 2026, Ch. 1-6) -- 12 engineering practices: standardized tool interfaces, async-first processing loop, complete trajectory capture, MCP integration, skill-as-workflow pattern
16. **Designing Multi-Agent Systems** (book, Victor Dibia, Ch. 1-13) -- 15 practices: simplest-architecture-first, evaluation-driven development, composable termination conditions, plan-based orchestration for complex tasks, Rule of Two for agent security
17. **Helvesec/rmux** (web/repo) -- Modern async-Rust PTY multiplexer with SDK-first architecture, daemon-based client-server model, cross-platform (incl. Windows via ConPTY), post-quantum E2EE web sharing
18. **HAP** (paper, 2510.18407v1) -- Heterogeneous Adversarial Play: minimax teacher-student formulation, +7% on hard Minigrid tasks, cold-start/catastrophic forgetting mitigations

---

## Current Lyra Baseline

Lyra's `workflow.py` (444 lines) orchestrates subagents WITHIN a session using a DAG engine but has no mechanism for detached background sessions that survive terminal close, sleep, or restart. The fleet TUI (`lyra-fleet-tui`, 4 files) has UI scaffolding with no supervisor integration, no two-axis state model, no peek/reply without attach, and no auto-worktree isolation. Parallel sessions editing the same checkout collide. The `autonomy.py` (449 lines) tracks crash/health but has no pre-execution confidence gating. Users cannot dispatch unattended tasks and check back later.

**Baseline gaps vs. state of art:**

| Capability | Lyra Current | Claude Code Agent View | Delta |
|-----------|-------------|------------------------|-------|
| Background session lifecycle | None | Supervisor daemon with spawn/monitor/stop/respawn/idle-reap | Full |
| Two-axis state model | None | task-state x process-liveness with grouping | Full |
| Fleet TUI | Scaffold only | Full table with peek/attach/filter/pin/rename | Major |
| Worktree isolation | None | Auto-EnterWorktree before first edit, `.worktreeinclude` | Full |
| Cheap-model monitoring | None | Haiku-class summaries refreshed <=15s | Full |
| Script-driven orchestration | Manual subagent calls | Dynamic workflows with adversarial cross-check | Full |
| Peer-to-peer agent communication | None | Agent teams with mailbox, shared task list, plan-approval | Full |
| Pre-execution safety gating | None | Not in Claude Code | Opportunity |
| Self-organizing agent teams | None | Not in Claude Code | Opportunity |

---

## Breakthrough Proposals

Each proposal fuses techniques from 2+ independently validated sources. Ranked by impact x effort (see matrix in Section 7).

---

### BP-1: Supervisor Daemon + Async-First Processing Loop with Two-Axis State

**Fused sources:**
- Claude Code Agent View (web): Supervisor daemon architecture, spawn/monitor/stop/respawn/idle-reap lifecycle, idle-timeout reaping, memory-pressure eviction, disk-persisted state (`roster.json` + `jobs/<id>/state.json`)
- Build Multi-Agent System from Scratch (book, Fajardo 2026, Ch. 4): Async-first processing loop returning `asyncio.Future` (`TaskHandler`), fire-and-forget submission, concurrent execution, graceful cancellation
- Designing Multi-Agent Systems (book, Dibia, Ch. 4): Five design principles including async-first architecture, event-based streaming, component serialization, graceful cancellation via `CancellationToken`
- Helvesec/rmux (web/repo): Pure domain model (`rmux-core` with `#![forbid(unsafe_code)]`) separated from OS/network, IPC protocol as detached crate, daemon-based client-server architecture, SDK-first design

**Why the combination wins:**
Each source solves a fragment. Claude Code provides the proven supervisor architecture but ties it to a single-provider ecosystem. The Fajardo book provides the async processing-loop mechanics (sub-steps, `NextStepDecision`, `TaskStepResult`) but no supervisor/daemon concept. The Dibia book provides the full design-principles framework including streaming and cancellation but no implementation detail. RMUX provides the architectural pattern for separating pure domain logic from OS integration -- this is essential for Lyra's multi-provider goal. Together they form a complete blueprint: Claude Code's supervisor lifecycle + Fajardo's async loop + Dibia's design principles + RMUX's domain/OS separation pattern.

**Design:**
- **Lyra-Daemon**: Per-user Tokio async daemon (provider-agnostic -- manages processes, not models). Pure domain model separated from OS integration. SDK-first design with `lyra-sdk` crate for programmatic control.
- **Two-axis state model**: Task-state (Working/NeedsInput/Idle/Completed/Failed/Stopped) x Process-liveness (Alive/ExitedResumable/LoopSleeping) with grouping: ReadyForReview/NeedsInput/Working/Completed. Persisted to `~/.lyra/daemon/roster.json` and `~/.lyra/jobs/<id>/state.json`.
- **Processing loop**: Each session runs as an async `TaskHandler` (subclass of `asyncio.Future`). Sub-steps: plan -> tool calls -> synthesize -> repeat. `NextStepDecision` formalizes continue-vs-complete. Sessions fire-and-forget, cancellable via token propagation.
- **Lifecycle**: Idle timeout (~1h unattached -> stop process, respawn from disk on peek/attach). Pinned sessions exempt. Memory-pressure eviction (stop idle non-pinned first).
- **Shell API**: `lyra fleet [agents|attach|logs|stop|respawn|rm|daemon status|daemon stop]`. `lyra fleet agents --json` for programmatic access.

**Trade-offs:**
- **Win**: Survives terminal close, sleep, auto-update, daemon restart. Self-exits when nothing live. Provider-agnostic. Pure domain model is fully testable without OS dependencies.
- **Lose**: Supervisor is a logical SPOF (mitigated by auto-restart + per-session independent checkpointing). Daemon requires per-machine process management. Windows support requires ConPTY (RMUX pattern provides reference implementation).

**Impact: 5 | Effort: 5 | Tier: (A) Parity -- Foundational**

---

### BP-2: Worktree Isolation + Structured Artifact Output for Collision-Free Parallelism

**Fused sources:**
- Claude Code Worktrees (web): `EnterWorktree` tool, `.worktreeinclude` (.gitignore-syntax env propagation), `worktree.baseRef` (fresh/head), cleanup state machine (no changes = silent removal, changes = prompt), periodic sweep based on `cleanupPeriodDays`
- Anthropic Engineering Blog (web): Subagent output to filesystem artifact system -- subagents persist work externally, return lightweight references, prevents information loss in multi-stage processing and reduces token overhead
- FS-Researcher (paper, 2602.01566v2): Dual-agent persistent file-system workspace, ablation removing it drops RACE by -4.07 points
- AutoScientists (paper/repo, 2605.28655v1): Each run gets isolated git clone with `--depth 1` -- direct response to "shared mutable state corrupts baselines" failure mode where symlinked repo accumulated 1800+ lines of uncommitted changes

**Why the combination wins:**
Claude Code provides the proven worktree isolation mechanism but assumes a single-ecosystem workflow. The Anthropic blog provides the artifact-based output pattern (subagents persist to filesystem, return lightweight refs) but doesn't address file collision. FS-Researcher provides quantitative evidence that persistent workspace matters (RACE drops -4.07 without it). AutoScientists provides the critical failure-mode documentation: shared mutable state across parallel agents accumulates uncommitted changes that corrupt baselines. The combination yields: isolated worktrees prevent write collisions + artifact-based output prevents token bloat + evidence from both papers that this matters quantitatively.

**Design:**
- **Auto-worktree isolation**: Before first file edit, session auto-calls `EnterWorktree` tool. Creates worktree under `.lyra/worktrees/<name>/`. `.lyraworktreeinclude` copies gitignored env/secrets. `worktree.baseRef`: `"fresh"` (origin/HEAD, default) or `"head"` (local HEAD).
- **Artifact output system**: Subagents write results to `$LYRA_JOB_DIR/artifacts/`. Return lightweight JSON references (path, checksum, summary) to coordinator instead of full output in context. This mirrors Anthropic's production pattern.
- **Cleanup**: No uncommitted changes + no untracked files + no new commits = silent removal on exit. Changes present = prompt. Background sessions cleaned via periodic sweep.
- **Non-git fallback**: Warning log for v1; CoW overlay for v2.
- **Isolation config**: `lyra.fleet.worktree.isolation` = `"always"` (default) / `"none"`.

**Trade-offs:**
- **Win**: Eliminates the entire class of parallel-session file-collision bugs. Artifact system reduces coordinator token burden by orders of magnitude (Anthropic pattern: subagents return compressed findings, not raw dumps). Proven in production (Claude Code).
- **Lose**: Each worktree adds ~50-200MB disk (full checkout). Non-git repos require fallback. Windows support adds complexity (though RMUX's ConPTY pattern provides path).

**Impact: 4 | Effort: 3 | Tier: (A) Parity -- Foundational**

---

### BP-3: Script-Driven Orchestration with Adversarial Cross-Check and Dynamic Agent Topology

**Fused sources:**
- Claude Code Dynamic Workflows (web): Script-driven orchestration (not prompt-driven), codified in code, repeatable/diffable/resumable. Adversarial cross-check as built-in quality pattern: "have independent agents adversarially review each other's findings before they're reported." Runtime isolation -- intermediate results in script variables, not Claude's context.
- Dialectic-Med (paper, 2604.11258v1): 3-agent adversarial dialectic (Proponent-Opponent-Mediator) with Dynamic Consensus Graph and path integration for final adjudication. Attack strength gates termination. VFM ablation: -9.31% drop, proving text-only debate is fundamentally inadequate without grounding.
- Claude Code Agent Teams (web): Competing-hypotheses debugging pattern -- "Sequential investigation suffers from anchoring: once one theory is explored, subsequent investigation is biased toward it." Peer communication via mailbox, shared task list, plan-approval workflow.
- AFlow (paper, 2410.10762v4): MCTS search over code-represented workflows, discovering ensemble-like structures without operator specification (93.1% retention without operators). Dynamic topology as discovered property, not hard-coded.

**Why the combination wins:**
Claude Code workflows provide the repeatable orchestration substrate but no principled debate structure. Dialectic-Med provides the strongest adversarial debate mechanism in the corpus (+8.18% accuracy, -46.3% hallucination) but is domain-locked to medical imaging. Agent teams provide the competing-hypotheses pattern but no workflow integration. AFlow provides the search mechanism that discovers optimal agent topologies. Combined: a script-driven orchestration system where workflows dynamically discover topology via MCTS, execute via parallel subagent dispatch, and verify via adversarial cross-check with structured consensus graphs. This fuses: orchestration-as-code + adversarial verification + dynamic topology search.

**Design:**
- **Workflow scripts**: Python/JS scripts hold orchestration logic (loop, branching, intermediate results). Lyra's context sees only final synthesis. Scripts are diffable, reviewable, resumable. Saved to `~/.lyra/workflows/`.
- **Adversarial cross-check phase**: Built into every workflow as a distinct pipeline stage. N verification agents independently audit each claim from synthesis. Proponent-Opponent-Mediator pattern adapted from Dialectic-Med with code-grounding (AST diffs, execution traces) replacing visual grounding. Consensus graph with path integration for final adjudication. Attack strength (S_attack) gates re-verification loops.
- **Dynamic topology via MCTS** (from AFlow): Workflow configurations represented as code (Python classes). MCTS optimizer proposes topology modifications (add/remove agent, rewire communication, modify prompts). UCB1 node selection with soft mixed probability (exploitation + exploration via blank template). Experience backpropagation across iterations. Budget: 10-20 iterations max.
- **Progress view**: Phases x agent-count x token-total x elapsed time. Drill into any phase/agent to read prompts, tool calls, results.
- **Governance caps**: Max 16 concurrent agents (CPU-bound), max 1000 agents per run (prevents runaway loops).

**Trade-offs:**
- **Win**: Repeatable, auditable orchestration. Adversarial cross-check eliminates anchoring bias. MCTS-discovered topologies outperform hand-designed ones (+5.7% in AFlow). Script-driven = lower context pressure (intermediate results in script variables).
- **Lose**: Workflows use meaningfully more tokens than conversational work (documented Claude Code caveat). MCTS search adds 5-14x inference cost. Dynamic topology = less predictable behavior. Script debugging requires engineering discipline.

**Impact: 5 | Effort: 4 | Tier: (B) Breakthrough -- High-leverage**

---

### BP-4: Pre-Execution Confidence Circuit Breaker with Safety Memory Governance

**Fused sources:**
- Preventing Rogue Agents (paper, 2502.05986v2): Live monitoring via entropy/varentropy/kurtosis features + polynomial ridge classifier, pre-execution intervention (reversible action rollback), +12.4% avg success with double reset, monitor trained on one benchmark generalizes to another
- Safety Risks in Self-Evolving Agents (paper, 2604.16968v1): Benign experience systematically increases ASR across all 7 models tested. Experience retrieval quantity (1->9 entries) monotonically raises ASR. Execution bias -- benign patterns become unsafe in sensitive contexts. Integrated gradients prove content (not context length) is causal.
- Designing Multi-Agent Systems (book, Dibia, Ch. 13): Rule of Two for agent security -- agents must not simultaneously: [A] process untrustworthy inputs, [B] access sensitive systems, [C] change state/communicate externally without human approval. Middleware as universal control plane for pre-execution gating.

**Why the combination wins:**
Rogue Agents provides the confidence monitoring mechanism but was validated only on game environments (WhoDunitEnv) + limited code tasks. The Safety Risks paper proves the problem is universal: any experience-driven system with memory degrades safety, and the degradation compounds with more experience. Dibia's Rule of Two provides the operational decision framework. Combined: a confidence circuit breaker that monitors pre-execution uncertainty, blocks actions when confidence < threshold, but critically uses the Safety Risks finding to also gate memory retrieval (limit retrieved experience entries, filter by safety-relevance score) -- preventing the compounding degradation that killed all 7 models in the safety paper. This is a novel combination: confidence gating + memory governance as unified safety layer.

**Design:**
- **Confidence monitor**: Extracts 4 features per critical action position: entropy, varentropy, kurtosis, turn count. Polynomial ridge classifier (d in [1,5]) trained on labeled Lyra trajectories. Threshold tau tuned per validation set.
- **Intervention protocol**: When P(success | features) < tau: (1) identify reversible vs. irreversible actions, (2) roll back reversible actions to last irreversible checkpoint, (3) agent gets fresh attempt. Cap: 2 interventions per agent per session.
- **Safety memory governance** (novel): Retrieved experience entries capped at k=3 (Safety Risks finding: ASR rises monotonically with retrieval quantity). Each entry scored for safety-relevance via cosine similarity to known-safe pattern library. Entries below safety threshold excluded from context. Memory audit log tracks retrieval provenance.
- **Rule of Two enforcement**: Middleware interceptor checks every tool call against the Rule of Two matrix. Violation -> human-in-the-loop approval required (via fleet view peek panel).
- **Per-provider calibration**: Ship with conservative high threshold. Calibrate per model via eval suite. Fallback to model-agnostic uncertainty heuristics (token probability entropy, response length variance) when logprobs unavailable.

**Trade-offs:**
- **Win**: Prevents error propagation before it cascades (+12.4% documented gain). Safety memory governance prevents the universal degradation proven in Safety Risks. Rule of Two provides operational safety without full sandboxing.
- **Lose**: 1.6-1.9x task length increase (documented in Rogue Agents). False positives may block legitimate actions. Per-provider calibration data may be sparse for new models. Memory governance may filter useful (but superficially unsafe-looking) experience.

**Impact: 5 | Effort: 3 | Tier: (B) Breakthrough -- High-leverage**

---

### BP-5: Self-Organizing Agent Teams with Peer-Review-Gated Compute and Stagewise Co-Evolution

**Fused sources:**
- AutoScientists (paper/repo, 2605.28655v1): Self-organizing hypothesis-based teams, peer-review-before-compute ([PROPOSAL] requires non-author comment before GPU queue), noise-gated champion propagation (multi-seed re-run for borderline deltas), self-regulating discussion triggers (stagnation detection), meta-improvement cycles (system edits own role templates)
- MetaAgent-X (paper, 2605.14212v1): Stagewise Designer-Executor co-evolution via GRPO, hierarchical rollout (M=4 designs x N=4 executions) for clean credit assignment, Designer generates task-specific MAS scripts (54 distinct role names, 77.5% byte-unique prompts), SFT cold-start from DeepSeek-V3.2 trajectories
- MARS^2 (paper, 2604.14564v1): Multi-agent tree search with Thompson sampling over agent-node pairs, tree-consistent reward shaping (mixed baseline: (1-lambda)*parent_reward + lambda*sibling_mean), agent-specific independent parameters preventing policy collapse

**Why the combination wins:**
This is the most ambitious proposal -- fusing three complementary approaches into a system none of them individually achieves. AutoScientists provides the organizational structure (self-organizing teams, peer-review gating) but uses static agent roles and fixed prompts. MetaAgent-X provides the optimization mechanism (stagewise RL co-evolution) that learns better agent designs over time, but its Designer-Executor is a single centralized pair. MARS^2 provides the search infrastructure (Thompson sampling over agent-node pairs for exploration-exploitation balance) that prevents the policy collapse MetaAgent-X fights against. Together: self-organizing teams (AutoScientists) whose Designer and Executor policies co-evolve via stagewise RL (MetaAgent-X) while MARS^2-style Thompson sampling governs which agent expands which research direction next in the shared search tree. The stagewise alternation (K=30 steps per role) from MetaAgent-X solves the non-stationarity problem; the tree-consistent reward shaping from MARS^2 solves the credit assignment problem; the peer-review gating from AutoScientists solves the compute-waste problem.

**Design (Phase 5+ -- Research Bet):**
- **Team formation**: Agents read shared state S (champion p*, experiment log L, forum F, team-local state). Self-organize into hypothesis-based teams via structured discussion. Roster R = {(T_k, axis_k, members_k)}^K_{k=1} written by alphabetically-last analyst (tie-breaker only).
- **Peer-review-before-compute**: Every experiment starts as [PROPOSAL] post. At least 1 non-author comment required before GPU/API queue entry. No compute spent on unreviewed ideas.
- **Stagewise RL co-evolution**: SFT cold-start from Lyra's existing agent traces. Hierarchical rollout (M=4 candidate designs x N=4 executions each). GRPO with stagewise alternation (K=30 steps per phase). Designer advantage averaged over N executions; Executor advantage normalized at question-level across all designs. Shared-policy optimization with both roles.
- **MARS^2-style agent-node selection**: Thompson sampling at two levels: (1) which agent to activate next, (2) which node (hypothesis) associated with that agent to expand. Beta priors over selection probabilities. Two functional node types: generation (new hypothesis) vs. refinement (extend existing).
- **Noise-gated champion promotion**: Multi-seed noise floor (sigma = pooled within-pair std). Delta > 2*sigma = promote directly. 0 < delta <= 2*sigma = re-run second seed, promote iff both improve. Noise floor locked after 5 calibration pairs.
- **Meta-improvement**: Every 3 cycles, system diagnoses team performance from experiment log and edits role templates. Self-regulating discussion triggers: 0 KEEPs in 3+ rotations -> auto-post [DISCUSSION-TRIGGER].

**Trade-offs:**
- **Win**: Sustained parallel search across diverse hypotheses (7 accepted improvements vs. 0 single-agent). RL-learned policies outperform hand-designed ones (+11.17% avg). Peer-review prevents GPU waste. Noise gate prevents champion corruption. Tree search prevents exploration collapse.
- **Lose**: Very high cost (9+ agents continuously on Sonnet/Opus tier). Template bloat documented as failure mode (1300+ line ROLE-ANALYST.md). Agent reliability is dominant failure mode (analysts writing local notes instead of posting). RL training requires 8+ GPUs, SFT dataset. Team reformation is slow (3 zero-KEEP rotations before hypothesis falsification).

**Impact: 5 | Effort: 5 | Tier: (C) Research Bet -- Phase 5+**

---

## Implementation Roadmap

### Layer 1 -- Supervisor MVP (Weeks 5-7 of overall plan)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M1.1 | Design `SessionState` data class + JSON serialization (two-axis: task_state x process_liveness) | Claude Code Agent View |
| M1.2 | Implement `lyra-daemon`: spawn/stop/monitor/respawn lifecycle, pure domain model separated from OS integration | Claude Code Agent View + RMUX architecture pattern |
| M1.3 | Disk state persistence: `~/.lyra/daemon/roster.json` + `~/.lyra/jobs/<id>/state.json` | Claude Code Agent View |
| M1.4 | Async processing loop: `TaskHandler` as `asyncio.Future`, sub-steps (plan -> act -> observe), `NextStepDecision` | Build Multi-Agent System from Scratch (Ch. 4) |
| M1.5 | Idle timeout (~1h unattached -> stop), sleep/wake reconnection (SIGSTOP/SIGCONT handlers) | Claude Code Agent View |
| M1.6 | Shell management API: `lyra fleet [agents|attach|logs|stop|respawn|rm|daemon status]` | Claude Code Agent View |
| M1.7 | Integration tests: spawn 5 sessions, sleep, wake, verify all reconnect from disk | Internal quality gate |

### Layer 2 -- Fleet View Hardening (Weeks 7-9)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M2.1 | Harden lyra-fleet-tui: two-axis state model, session grouping, peek panel (Space), attach/detach (Enter/Esc) | Claude Code Agent View |
| M2.2 | Dispatch surface: from fleet view input, from inside session (`/bg`), from shell (`lyra --bg`) with `--name`/`--agent`/`--model`/`--effort`/`--permission-mode` | Claude Code Agent View |
| M2.3 | Cheap-model row summaries: route via cheapest available model, <=15s refresh + at turn end | Claude Code Agent View + Lyra router (plan §4.5) |
| M2.4 | Per-session cost estimation in dispatch prompt (model x effort x historical average for similar tasks) | Anthropic Engineering Blog (effort-scaling heuristics) |
| M2.5 | Fleet sizing governance: max concurrent sessions, daily cost cap (`lyra.fleet.maxDailyCost`), backpressure queue | Internal design |

### Layer 3 -- Auto-Worktree Isolation (Weeks 9-11)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M3.1 | `EnterWorktree` tool: auto-trigger before first file edit, creates `.lyra/worktrees/<name>/` | Claude Code Worktrees |
| M3.2 | `.lyraworktreeinclude`: `.gitignore`-syntax file, copies gitignored env/secrets into worktree | Claude Code Worktrees |
| M3.3 | Artifact output system: subagents write to `$LYRA_JOB_DIR/artifacts/`, return lightweight JSON refs | Anthropic Engineering Blog + FS-Researcher (2602.01566v2) |
| M3.4 | Cleanup state machine: no changes = silent removal, changes = prompt, periodic sweep | Claude Code Worktrees |
| M3.5 | Non-git fallback: warning log v1, CoW overlay v2 | Claude Code Worktrees (WorktreeCreate/Remove hooks pattern) |

### Layer 4 -- Script-Driven Orchestration + Adversarial Cross-Check (Weeks 9-13, parallel with Layer 3)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M4.1 | Extend workflow.py: script-driven orchestration, intermediate results in script variables, runtime isolation | Claude Code Dynamic Workflows |
| M4.2 | Pause/resume/stop/restart per agent in progress view | Claude Code Dynamic Workflows |
| M4.3 | Progress view: phases x agent count x token total x elapsed, drill-down per phase/agent | Claude Code Dynamic Workflows |
| M4.4 | Adversarial cross-check phase: Proponent-Opponent-Mediator pattern, Consensus Graph with path integration, attack-strength-gated re-verification | Dialectic-Med (2604.11258v1) + Claude Code Dynamic Workflows |
| M4.5 | Code-grounding for adversarial verification: AST diffs, execution traces, test results as evidence | Dialectic-Med VFM pattern adapted to code domain |

### Layer 5 -- Confidence Circuit Breaker + Safety Memory Governance (Weeks 11-13)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M5.1 | Pre-execution confidence monitor: entropy/varentropy/kurtosis + turn count features, polynomial ridge classifier | Preventing Rogue Agents (2502.05986v2) |
| M5.2 | Intervention protocol: reversible vs. irreversible action identification, rollback, fresh attempt, 2-cap per agent | Preventing Rogue Agents (2502.05986v2) |
| M5.3 | Safety memory governance: retrieval quantity cap (k=3), safety-relevance scoring, provenance audit log | Safety Risks (2604.16968v1) |
| M5.4 | Rule of Two middleware: pre-execution interceptor, violation -> HITL approval via fleet view peek panel | Designing Multi-Agent Systems (Dibia, Ch. 13) |
| M5.5 | Per-provider calibration: eval suite for calibration data, model-agnostic fallback heuristics | Preventing Rogue Agents + Internal eval |

### Layer 6 -- MCTS-Driven Dynamic Topology Search (Weeks 13-17, Phase 4+)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M6.1 | Workflow-as-code representation: Python classes with ActionNode + Workflow base | AFlow (2410.10762v4) |
| M6.2 | MCTS optimizer: soft mixed probability selection, LLM-based expansion (XML-tagged modifications), UCB1 backpropagation | AFlow (2410.10762v4) |
| M6.3 | Dynamic convergence: top-k workflows unchanged for n rounds -> early stop | AFlow (2410.10762v4) |
| M6.4 | Agent teams mode: peer communication via mailbox, shared task list, plan-approval workflow, competing-hypotheses debugging | Claude Code Agent Teams |

### Layer 7 -- Self-Organizing Teams (Phase 5+, Research Bet)

| Milestone | Description | Source Mapping |
|-----------|-------------|----------------|
| M7.1 | HEARTBEAT state machine: 4-branch dispatch per agent invocation | AutoScientists (2605.28655v1) |
| M7.2 | Peer-review-before-compute: [PROPOSAL] posts, non-author comment requirement, queue protocol with optimistic locking | AutoScientists (2605.28655v1) |
| M7.3 | Stagewise RL co-evolution: SFT cold-start, hierarchical rollout, GRPO with decomposed advantage, shared-policy optimization | MetaAgent-X (2605.14212v1) |
| M7.4 | MARS^2-style agent-node Thompson sampling, tree-consistent reward shaping, mixed baselines | MARS^2 (2604.14564v1) |
| M7.5 | Meta-improvement: cycle-based template editing, self-regulating stagnation detection | AutoScientists (2605.28655v1) |

---

## Risk Register

| # | Risk | Probability | Impact | Mitigation | Source |
|---|------|------------|--------|------------|--------|
| R1 | **Supervisor daemon SPOF** -- daemon crash kills all background sessions | Medium | High | Auto-restart with health checks. Per-session independent checkpointing to disk (sessions survive daemon restart). RMUX pattern: pure domain model is crash-safe by design. | Claude Code Agent View + RMUX |
| R2 | **tmux version incompatibility** -- PTY hosting fails on old tmux versions | Medium | Medium | Ship minimum tmux 3.0 requirement. Fallback to built-in TUI for older versions. RMUX provides cross-platform alternative (Rust-native, Windows support). | rmux web/repo |
| R3 | **Worktree disk bloat** -- 50-200MB per parallel session, resource exhaustion on small disks | Medium | Low | Periodic sweep of stale worktrees. Configurable `cleanupPeriodDays`. User-facing disk usage warning. | Claude Code Worktrees |
| R4 | **Confidence circuit breaker false positives** -- legitimate actions blocked, frustrating users | Medium | Medium | Ship with high (conservative) threshold. User override option in peek panel. Per-provider calibration data tightens over time. Model-agnostic fallback when logprobs unavailable. | Preventing Rogue Agents (2502.05986v2) |
| R5 | **Safety memory governance filters useful experience** -- retrieval cap (k=3) may exclude task-critical past patterns | Medium | Medium | Override mechanism per-session. Safety-relevance threshold is tunable. Audit log enables post-hoc analysis of filtered entries. | Safety Risks (2604.16968v1) |
| R6 | **Workflow token cost explosion** -- script-driven orchestration with adversarial cross-check uses meaningfully more tokens | High | Medium | Governance caps: max 16 concurrent, max 1000/run, daily cost cap. Run on small slice first to gauge spend. Effort-scaling heuristics route simple tasks to single-agent (bypass workflow overhead). | Claude Code Dynamic Workflows + Anthropic Engineering Blog |
| R7 | **Self-organizing team reliability** -- agents write local notes instead of posting (documented AutoScientists failure), stale queue claims, template bloat | High | High (for Tier C) | Deferred to Phase 5+. Track AutoScientists failure-mode history. Implement from Day 1: <promise> tag requirement, tool-call budget, explicit "your cycle is not complete until..." instructions. | AutoScientists (2605.28655v1) |
| R8 | **Windows support** -- tmux unavailable, ConPTY complexity | Medium | Medium | RMUX provides reference ConPTY implementation. v1: no Windows PTY (sessions run headless). v2: ConPTY or Windows Terminal integration. | rmux web/repo |
| R9 | **Experience-driven safety degradation** -- fleet memory accumulates benign experience that compounds execution bias in sensitive contexts | Low (with BP-4) | High | BP-4's safety memory governance directly addresses this. Retrieval quantity cap (k=3). Safety-relevance scoring before retrieval. Provenance audit log. Periodic safety evaluation of memory store. | Safety Risks (2604.16968v1) |
| R10 | **MCTS search cost** -- 5-14x inference cost per topology optimization | Medium for Tier C | Medium | Budget cap on MCTS iterations (10-20 max). AFlow result that GPT-4o-mini + optimized workflow matches GPT-4o at 4.55% cost suggests net cost may be lower for repeated tasks. | AFlow (2410.10762v4) |

---

## Impact x Effort Matrix

| # | Proposal | Impact (1-5) | Effort (1-5) | I/E Ratio | Tier | Timeline |
|---|----------|-------------|-------------|-----------|------|----------|
| BP-1 | Supervisor Daemon + Async Loop + Two-Axis State | 5 | 5 | 1.00 | (A) Parity | Layers 1-2 (6 weeks) |
| BP-2 | Worktree Isolation + Artifact Output | 4 | 3 | 1.33 | (A) Parity | Layer 3 (2 weeks) |
| BP-3 | Script-Driven Orchestration + Adversarial Cross-Check + Dynamic Topology | 5 | 4 | 1.25 | (B) Breakthrough | Layers 4+6 (6 weeks) |
| BP-4 | Confidence Circuit Breaker + Safety Memory Governance | 5 | 3 | 1.67 | (B) Breakthrough | Layer 5 (2 weeks) |
| BP-5 | Self-Organizing Teams + Stagewise Co-Evolution | 5 | 5 | 1.00 | (C) Research Bet | Phase 5+ (8+ weeks) |

### Component-Level Impact x Effort

| Component | Impact | Effort | Delta from Current | Migration Cost |
|-----------|--------|--------|--------------------|----------------|
| `workflow.py` (444L) -- EXTEND: script-driven orchestration, script variables, pause/resume, adversarial cross-check phase | 5 | 3 | Major enhancement | Medium -- additive DAG changes |
| `lyra-fleet-tui` (4 files) -- REPLACE: full two-axis fleet view, peek/attach/filter/pin | 4 | 3 | Rewrite on existing scaffolding | Medium |
| `lyra-daemon` -- ADD: ~800 line daemon (pure domain model + OS integration, SDK) | 5 | 5 | New component | None |
| `autonomy.py` (449L) -- EXTEND: confidence monitoring features, polynomial classifier, intervention protocol | 5 | 2 | New gating layer | Low -- extends existing health tracking |
| `safety_memory.py` -- ADD: retrieval governance, safety-relevance scoring, provenance audit log | 5 | 2 | New component | None |
| `worktree.py` -- ADD: EnterWorktree tool, .lyraworktreeinclude, cleanup state machine, artifact output | 3 | 3 | New component | None |
| `adversarial_verify.py` -- ADD: Proponent-Opponent-Mediator pattern, Consensus Graph, code-grounding module | 4 | 3 | New component | None |
| `topology_search.py` -- ADD: MCTS optimizer, workflow-as-code representation, LLM-based expansion | 3 | 4 | New component (Phase 4+) | None |
| `self_org_teams.py` -- ADD: HEARTBEAT state machine, peer-review protocol, stagewise RL co-evolution | 5 | 5 | New component (Phase 5+) | None |

---

## Multi-Provider Note

The supervisor daemon is provider-agnostic (manages processes, not models). Row summaries use the cheapest available model via the Lyra router (plan §4.5). On DeepSeek: the confidence circuit breaker requires calibration data -- DeepSeek logprob access and confidence signal calibration may differ from Anthropic's. Fallback: model-agnostic uncertainty heuristics (token probability entropy, response length variance across samples). The adversarial cross-check pattern is provider-agnostic (any model can participate as Proponent/Opponent/Mediator). The MCTS topology search (BP-3) benefits from AFlow's finding that GPT-4o-mini + optimized workflow matches GPT-4o at 4.55% of cost -- cheap-model optimization dramatically reduces total cost for repeated task patterns.

---

## Expert Review Synthesis

The following concerns were debated and resolved in the Phase 4 debates:

**Skeptic's challenge: "Why not tmux + thin status file instead of a daemon?"**
REJECTED. Tmux cannot respawn sessions from disk state; the "thin status file" grows to 500+ lines covering spawn/monitor/stop/respawn/idle-reap/memory-eviction logic. RMUX's architecture (pure domain model + daemon) sets the right pattern. Claude Code's production deployment validates the daemon approach at scale.

**SRE's concern: "Supervisor is a single point of failure."**
MITIGATED. Health checks with auto-restart. Per-session independent checkpointing to disk (sessions survive daemon restart). RMUX pattern: pure domain model is crash-safe. Claude Code production behavior: auto-update restarts supervisor transparently; sessions reconnect.

**UX's concern: "Fleet view needs to show PR status, cost, AND state clearly."**
ADOPTED. Two-axis state icons (per Claude Code design). Color-coded PR status. Cost estimate in dispatch prompt. Peek panel shows recent output + what session needs + PRs opened. Cheap-model one-line summaries refreshed <=15s.

**Skeptic's follow-up: "Confidence circuit breaker calibration on DeepSeek."**
ADDRESSED. Ship with conservative high threshold first. Tighten with per-provider eval data. Fallback to model-agnostic uncertainty heuristics (token probability entropy, response length variance). The Rogue Agents paper demonstrates cross-environment generalization (monitor trained on HumanEval generalizes to LiveCodeBench).

**Security expert's concern: "Benign experience in fleet memory degrades safety."**
ADDRESSED via BP-4. Safety Risks paper (2604.16968v1) proved this is universal across all 7 tested models. BP-4's safety memory governance directly mitigates: retrieval quantity cap (k=3), safety-relevance scoring, provenance audit log.

**Sign-off:** All concerns recorded and addressed with evidence-based mitigations. Plan is feasible and grounded in production-validated and lab-validated sources.

---

## References

1. Anthropic Engineering Blog: "How we built our multi-agent research system." https://www.anthropic.com/engineering/built-multi-agent-research-system
2. Claude Code Agent View: https://code.claude.com/docs/en/agent-view
3. Claude Code Worktrees: https://code.claude.com/docs/en/worktrees
4. Claude Code Dynamic Workflows: https://code.claude.com/docs/en/workflows
5. Claude Code Agent Teams: https://code.claude.com/docs/en/agent-teams
6. MetaAgent-X (2605.14212v1): "Breaking the Ceiling of Automatic Multi-Agent Systems via End-to-End RL"
7. MARS^2 (2604.14564v1): "Scaling Multi-Agent Tree Search via Reinforcement Learning for Code Generation"
8. Preventing Rogue Agents (2502.05986v2): "Preventing Rogue Agents Improves Multi-Agent Collaboration"
9. AI Auto-Research Roadmap (2605.18661v1): "AI for Auto-Research: Roadmap & User Guide"
10. AFlow (2410.10762v4): "AFlow: Automating Agentic Workflow Generation"
11. Dialectic-Med (2604.11258v1): "Mitigating Diagnostic Hallucinations via Counterfactual Adversarial Multi-Agent Debate"
12. AutoScientists (2605.28655v1): "Self-Organizing Agent Teams for Long-Running Scientific Experimentation"
13. Argus (2605.16217v3): "Evidence Assembly for Scalable Deep Research Agents"
14. Safety Risks in Self-Evolving Agents (2604.16968v1): "On Safety Risks in Experience-Driven Self-Evolving Agents"
15. Build Multi-Agent System from Scratch (book, Fajardo 2026)
16. Designing Multi-Agent Systems (book, Victor Dibia)
17. Helvesec/rmux: https://github.com/Helvesec/rmux
18. HAP (2510.18407v1): "Heterogeneous Adversarial Play in Interactive Environments"
19. FS-Researcher (2602.01566v2): Dual-agent persistent workspace for deep research
20. Synthesis: multi-agent.md (2026-06-07)
21. Brainstorm: brainstorm/13-fleet-swarm.md

---

## Changelog

- Run 1 (2026-06-03): Initial plan written. 4 sources consulted. Candidates debated in Rounds 1-3.
- Run 2 (2026-06-07): Full rewrite with deep-read evidence from 18 sources. 5 breakthrough proposals added, each fusing 2+ sources. Risk register expanded from 4 to 10 entries. Impact x Effort matrix with I/E ratios added. Safety memory governance added as novel combination of Rogue Agents + Safety Risks papers. MCTS-driven dynamic topology search added from AFlow. Self-organizing teams deferred to Phase 5+ Research Bet with full AutoScientists + MetaAgent-X + MARS^2 fusion.
