# Autonomous Research and Discovery — Thematic Synthesis

**Status:** Definitive synthesis for Phase 4 workstream plans.
**Sources audited:** 281 paper notes, 80 book notes (40 chapters + 40 playbooks), 184 web notes.
**Keywords searched:** auto research, autonomous research, deep research, AutoResearchClaw, Sibyl, Paper Circle, AI Scientist, gpt-researcher, DeepResearcher, RoadMapper, ARIS, research pipeline, scientific discovery, EvoSci, IterResearch, Tongyi, Claw AI Lab, NanoResearch, FS-Researcher, MetaClaw, Argus, AutoScientists, Open Deep Research.
**Sources read in depth:** 15 paper notes, 5 web notes (repos + blogs), 1 book chapter note.

---

## 1. Frontier Techniques (ranked by evidence strength)

### Technique 1: Iterative Workspace Reconstruction (Markovian State Compression)

- **Technique:** Replace linear context accumulation with an evolving compressed report `M_t` that serves as the sole carrier of historical information. At each step, the agent conditions on `(question, M_t, last_interaction)` — constant-size workspace vs. O(t) growth.
- **Sources:**
  - IterResearch (arXiv:2511.07327v2, ICLR 2026) [Paper ID: 2511.07327v2] — formal MDP formulation with workspace transition function
  - Tongyi DeepResearch (arXiv:2510.24701v3) [Paper ID: 2510.24701v3] — Markovian state reconstruction for 30.5B MoE model, Equation 3
  - COMEM (arXiv:2605.30842v1, ICML 2026) [Paper ID: 2605.30842v1] — decoupled small memory model + large agent model with k-step-off async pipeline
- **Mechanism:**
  - Each step produces `(Think_t, M_{t+1}, a_t)` — the updated report `M_{t+1}` replaces all prior history.
  - Transition function: `s_{t+1} = (q, M_{t+1}, {a_t, TR_t})` — deliberate discarding of full trajectory.
  - GRPO-trained with geometric discounting `r_t = γ^{T-t} · R_T` (γ=0.995) to create efficiency pressure.
  - Bounded per-step attention: `O((|M|+|TR|)^2)` constant vs. `O((t·|TR|)^2)` growing.
- **Evidence:**
  - IterResearch-30B-A3B: +14.5pp average gain across 6 benchmarks over best open-source.
  - Interactive scaling: 3.5% accuracy at 2 turns → 42.5% at 2048 turns (12.1x improvement, 64x extrapolation from training horizon).
  - Tongyi DeepResearch: SOTA on 7/8 benchmarks with 3.3B active params. HLE 32.9 vs 29.8 (OpenAI o4-mini).
  - COMEM: 1.5-1.7x latency reduction on SWE-Bench with no quality loss.
  - Convergence: Tongyi DeepResearch + IterResearch independently invented the same pattern (IterResearch cites Tongyi as convergent work).
- **Maturity:** Production deployed (Tongyi on Alibaba Cloud, IterResearch evaluated at ICLR 2026).

### Technique 2: Multi-Agent Debate for Hypothesis Generation and Result Analysis

- **Technique:** K=3 domain-specialized agents (Innovator/Pragmatist/Contrarian for hypothesis; Optimist/Skeptic/Methodologist for results) debate and synthesize, with a fourth Synthesizer agent integrating outputs.
- **Sources:**
  - AutoResearchClaw (arXiv:2605.20025v2) [Paper ID: 2605.20025v2] — K=3 debate with ablation
  - Claw AI Lab (arXiv:2605.22662v1) [Paper ID: 2605.22662v1] — multi-agent discussion + consensus mechanism
  - NanoResearch (arXiv:2605.10813v2) [Paper ID: 2605.10813v2] — internal LLM reviewer for experiment blueprints
  - AI Auto-Research Roadmap (arXiv:2605.18661v1) [Paper ID: 2605.18661v1] — "Role specialization reduces self-confirmation bias"
  - Argus (arXiv:2605.16217v3) [Paper ID: 2605.16217v3] — verification as separate policy with contrastive reward
- **Mechanism:**
  - AutoResearchClaw K=3: Distinct epistemic roles with adversarial stances. Synthesizer produces 2-4 falsifiable hypotheses. K=3 ablated: K=2 degenerates into pro/con (-23% diversity), K=5 adds +67% tokens for +8% diversity.
  - Argus: Contrastive reward `R = clip(R_w/v + λ(R_w/v − R_w/o_v), 0, 1)` isolates verification contribution through causal inference.
  - NanoResearch: Internal reviewer critiques infeasible designs iteratively until blueprint passes or retry limit reached.
- **Evidence:**
  - AutoResearchClaw: Debate is the largest quality component — removing it drops quality by -1.37 (p=0.003) on 10-point scale.
  - AutoResearchClaw Result Analysis: +100.4% relative improvement over AI Scientist v2 (0.523 vs 0.261).
  - Argus-Parallel (K=8): Leads on 5 of 8 benchmarks. GAIA 93.2 vs 80.6 best proprietary (+12.6pp). BrowseComp-ZH 83.4 vs 82.4 (+1.0pp).
  - Anthropic Engineering Blog: Multi-agent outperforms single-agent by +90.2% on internal research eval [Web: anthropic.com/engineering/built-multi-agent-research-system].
- **Maturity:** Lab validated (multiple independent replications, but no large-scale production deployment of K=3 debate specifically).

### Technique 3: Persistent File-System Workspace as External Memory

- **Technique:** Two-agent architecture (Context Builder/Librarian + Report Writer/Author) operating on a shared persistent file-system workspace with control files (todos, checklists, logs) and structured knowledge base directories. Multi-session iterative refinement with checklist-gated progress.
- **Sources:**
  - FS-Researcher (arXiv:2602.01566v2) [Paper ID: 2602.01566v2] — primary source
  - Open Deep Research (langchain-ai) [Web: langchain-ai/open_deep_research] — supervisor-subgraph pattern with separate context windows
  - Anthropic Engineering Blog [Web: anthropic.com] — subagent output to filesystem artifact system
- **Mechanism:**
  - Stage 1 (Context Builder): Inspects workspace → formulates plan → creates hierarchical index.md → browses/synthesizes → writes to knowledge_base/ → self-checks against checklist → iterates across sessions.
  - Stage 2 (Report Writer): Web tools removed, treats KB as sole fact source. Section-by-section writing with per-section self-checks.
  - Control files: Todos (PENDING/IN-PROGRESS/COMPLETE), Checklist (static acceptance criteria), Logs (execution trajectory).
  - Citation grounding: Every note statement carries a relative-path citation pointer to a source file.
  - File I/O accounts for <0.03% of total wall-clock time.
- **Evidence:**
  - FS-Researcher: RACE 53.94 (SOTA on DeepResearch Bench at time of publication). +3.02 RACE over best open-source. +2.80 over Gemini official harness.
  - Ablation: -Dual-Agent (merge into one) drops -10.35 RACE — the largest ablation effect measured across all systems in this survey.
  - BrowseComp: 55.0 with Claude-Sonnet-4.5 (vs 43.9 official harness), 68.0 with GPT-5 (vs 54.9 official harness).
  - Cost: GPT-5-mini + context compression achieves OpenAI-DR quality at $2.51 vs $6.10/query.
  - Open Deep Research: #6 on Deep Research Bench (RACE 0.4943 with GPT-5). MIT license.
- **Maturity:** Production deployed (FS-Researcher SOTA on public benchmarks; Open Deep Research ranked on leaderboard).

### Technique 4: Self-Healing Execution with Pivot/Refine/Proceed Decision Loop

- **Technique:** Structured failure recovery with three outcomes: Proceed (evidence supports), Refine (adjust, up to N_r=10), Pivot (return to hypothesis generation with failure as evidence, up to N_p=2). Combined with cascading complexity-based code generation routing and static validation gates.
- **Sources:**
  - AutoResearchClaw (arXiv:2605.20025v2) [Paper ID: 2605.20025v2] — primary source, Algorithm 1
  - Claw AI Lab (arXiv:2605.22662v1) [Paper ID: 2605.22662v1] — runtime Python guard with anti-fabrication
  - NanoResearch (arXiv:2605.10813v2) [Paper ID: 2605.10813v2] — autonomous debugging loop with retry budget
- **Mechanism:**
  - Failure signature capture → targeted fixes → structured decision.
  - Complexity scoring: 6 dimensions → `c ∈ [0,1]`. Experiments with `c > τ` (τ=0.6) route to external AI coding agent.
  - Static validation gates: Identical ablation detection, hardcoded metric detection before execution budget spent.
  - Docker sandbox: Three-phase network isolation (install → data acquisition → full isolation).
  - Claw AI Lab runtime guard: Read-only Python controller enforcing time budgets, NaN/Inf detection, anti-fabrication smoke tests.
- **Evidence:**
  - AutoResearchClaw: Self-healing ablation drops completion from 10/10 → 6/10. Largest completion contributor.
  - Removing verification inflates acceptance (3/10→5/10) but 3 of 5 contain fabricated values.
  - Claw AI Lab: +16.2 avg gain over AutoResearchClaw on 4-topic evaluation (79.2 vs 63.0/100).
  - AutoResearchClaw Full-Auto: 0.596 on ARC-Bench vs 0.419 AI Scientist v2 (+42.2% relative).
- **Maturity:** Lab validated (AutoResearchClaw open-source, Claw AI Lab repo published, both on 4-25 topics).

### Technique 5: GRPO-RL Training of Agentic Research Trajectories

- **Technique:** Group Relative Policy Optimization (GRPO) applied to full multi-turn research trajectories with multi-faceted outcome rewards (factuality + comprehensiveness + format). Eliminates learned value function, uses group-relative advantage normalization.
- **Sources:**
  - DeepResearcher (arXiv:2605.29796v2) [Paper ID: 2605.29796v2] — primary source, 7B/32B/235B scaling
  - Tongyi DeepResearch (arXiv:2510.24701v3) [Paper ID: 2510.24701v3] — adapted GRPO with token-level PG + leave-one-out advantage
  - IterResearch (arXiv:2511.07327v2) [Paper ID: 2511.07327v2] — EAPO with geometric discounting
  - Argus (arXiv:2605.16217v3) [Paper ID: 2605.16217v3] — contrastive reward isolating verification contribution
- **Mechanism:**
  - For each question: sample G trajectories from current policy → score with reward function → compute advantage `A_i = (R_i - mean(R_group)) / std(R_group)` → update with clipped policy gradient.
  - KL penalty coefficient β is crucial: without it, model collapses (31.2% vs 53.2% on GAIA — -22.0 points).
  - Outcome supervision only (no process reward model): reward computed purely on final answer + trajectory metadata.
  - Cold-start SFT on 5K-10K expert trajectories required before RL.
- **Evidence:**
  - DeepResearcher-7B: 53.2% GAIA (outperforms GPT-4o at 37.8% and Claude 3.5 Sonnet at 39.4%). 7.5x cheaper inference.
  - DeepResearcher-235B: 71.3% GAIA.
  - Argus-Parallel (trained with single-searcher, generalizes zero-shot to K=8): GAIA 93.2.
  - IterResearch: RL adds +3.6pp avg over SFT-only (49.1 vs 45.5).
  - Tongyi: RL reward monotonically increases from ~0.45 to ~0.65 over 500 steps. Simulated environment reward closely mirrors real.
- **Maturity:** Lab validated (DeepResearcher open-source, Tongyi production on Alibaba Cloud, IterResearch at ICLR 2026).

### Technique 6: Supervisor-Fanout Research Parallelism with Compression

- **Technique:** A supervisor agent decomposes research questions into parallel sub-tasks, fans out to worker subgraphs, collects compressed findings, and synthesizes. Each worker operates in an independent context window with its own tool-calling loop, then compresses outputs.
- **Sources:**
  - Open Deep Research (langchain-ai) [Web: langchain-ai/open_deep_research] — primary implementation
  - Anthropic Engineering Blog [Web: anthropic.com] — production deployment, +90.2% gain
  - AutoResearchClaw (arXiv:2605.20025v2) [Paper ID: 2605.20025v2] — multi-agent debate + parallel literature search
- **Mechanism:**
  - Supervisor LLM loop: calls `ConductResearch` (spawn sub-researcher), `think_tool` (strategic reflection), `ResearchComplete`.
  - All `ConductResearch` calls executed in parallel via `asyncio.gather`, bounded by `max_concurrent_research_units`.
  - `think_tool` forces the supervisor to reflect between delegations — explicitly prohibited from parallel calls.
  - Each researcher has independent state, tool loop, and compression step. Sub-agents cannot see each other's work (preventing shared misconceptions but also preventing collaboration).
  - Four independently configurable model roles: research, summarization, compression, final report.
- **Evidence:**
  - Open Deep Research: RACE 0.4943 (GPT-5), #6 on leaderboard. Claude Sonnet 4: 0.4401.
  - Anthropic: Multi-agent +90.2% over single-agent. Parallelization cuts latency up to 90%.
  - Anthropic: Tool-testing agent rewriting MCP descriptions → 40% decrease in task completion time.
  - Anthropic: Token usage variance on BrowseComp 80% explained by token count alone; 95% by tokens + tool calls + model.
- **Maturity:** Production deployed (Anthropic's multi-agent research system is in production; Open Deep Research is open-source, LangChain-maintained).

### Technique 7: Tri-Level Co-Evolution (SkillBank + Memory + Preference Learning)

- **Technique:** Three mutually reinforcing adaptation loops: (1) SkillBank — distilled procedural rules retrieved before each task, (2) Memory Module — user-project-bound fact store for contextual grounding, (3) SDPO — label-free preference internalization from free-form user feedback.
- **Sources:**
  - NanoResearch (arXiv:2605.10813v2) [Paper ID: 2605.10813v2] — primary source
  - MetaClaw (arXiv:2603.17187v1) [Paper ID: 2603.17187v1] — dual-timescale continual meta-learning with skill library
  - AutoResearchClaw (arXiv:2605.20025v2) [Paper ID: 2605.20025v2] — cross-run evolution with time-decayed lesson store
  - Data-Centric Survey (arXiv:2510.25817v1, ACL 2025) [Paper ID: 2510.25817v1] — Self-Evolving Data Ecosystem category
- **Mechanism:**
  - Retrieve-before-act + update-after-act: Before each stage, retrieves top-k skills and memories via heuristic scoring. After completion, distills trajectory into new entries. Overlapping entries semantically merged.
  - SDPO gradient: `∇_θ L_SDPO = -E[ Σ A^SDPO(ŷ_t) · ∇_θ log π_θ(ŷ_t) ]` — converts single feedback into dense token-level signal via self-teacher (feedback-conditioned model).
  - MetaClaw support-query separation: Trajectories stamped with skill generation version. Pre-adaptation samples flushed from RL buffer to prevent stale reward contamination.
  - AutoResearchClaw evolution: Lessons stored with severity `s(l)`, retrieved by time-decayed weight `w(l) = s(l) · exp(-ln(2) · Δt / T½)` where T½=30 days.
- **Evidence:**
  - NanoResearch: Only system with 100% E2E success rate. Alignment 8.963 vs 6.656 best baseline (+2.307). 76% cheaper than AI Scientist v2 by R3 ($1.43 vs $6.04/topic).
  - NanoResearch ablations: Removing PlannerModel causes largest drop. Removing SkillBank drops E2E from 1.000→0.849. Removing Memory hurts novelty (4.960→4.400). All components complementary.
  - MetaClaw: Full system (Skills + RL) achieves 8.25× file-check completion for weak models (Kimi-K2.5: 2.0%→16.5%).
  - MetaClaw: Skills-only lifts AutoResearchClaw stage retry rate -24.8%, refine cycle count -40.0%.
  - AutoResearchClaw: Removing evolution drops quality -0.48 and completion 10/10→9/10.
- **Maturity:** Lab validated (all three papers have open-source code; NanoResearch human-evaluated on 3 PhD researchers).

### Technique 8: Self-Organizing Agent Teams with Peer-Review-Gated Compute

- **Technique:** Agents self-organize into hypothesis-based teams without central planning. A peer-review-before-compute protocol requires at least one non-author agent to comment on proposals before experiments enter the queue. Multi-seed noise gating prevents champion corruption. Stagnation detection triggers self-initiated restructuring.
- **Sources:**
  - AutoScientists (mims-harvard) [Web: mims-harvard/AutoScientists, arXiv 2605.28655] — primary source
  - Claw AI Lab (arXiv:2605.22662v1) [Paper ID: 2605.22662v1] — cross-layer feedback loop, multi-agent consensus
  - AI Auto-Research Roadmap (arXiv:2605.18661v1) [Paper ID: 2605.18661v1] — "Multi-agent vs single-agent: best config uses 8 agents/5 rounds/50% diversity"
- **Mechanism:**
  - Orchestrator as pure coordinator (never runs experiments). Agents read HEARTBEAT.md at each invocation.
  - `[PROPOSAL]` → peer review → team queue → execution → `[KEEP]` → multi-seed noise gate → champion propagation.
  - Analysts detect stagnation (0 KEEPs in 3+ rotations) → autonomously post `[DISCUSSION-TRIGGER]` threads.
  - Meta-improvement loop: every 3 cycles, orchestrator diagnoses team performance and edits role templates.
  - Agents are stateless workers with discoverable context — every session starts by reading shared workspace state.
- **Evidence:**
  - BioML-Bench (24 tasks): 74.4% mean leaderboard percentile, +8.33% over strongest prior single-agent.
  - NanoGPT optimization: 1.9x faster to target metric. 7 accepted improvements vs 0 for single-agent baseline.
  - ProteinGym: +12.5% on ACE2-Spike binding assay; +6.5% across 217 assays.
  - Meta-improvement diagnostics document real deployment issues: 20-40% duplicate proposal rates, agent activation failures.
- **Maturity:** Lab validated (3 benchmark suites, documented failure logs from prior runs, no license file — legal caution needed).

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy | Latency | Memory Cost | Complexity | Scalability | Evidence Strength |
|-----------|----------|---------|-------------|------------|-------------|-------------------|
| **1. Workspace Reconstruction** | SOTA on 7/8 DR benchmarks (32.9 HLE) | O(1) per step, scales to 2,048 turns | Constant workspace (~32K tokens) | Medium (report synthesis required) | Unbounded (64x extrapolation validated) | ICLR 2026 paper + production deployment |
| **2. Multi-Agent Debate (K=3)** | +100% result analysis, -1.37 quality w/o debate | +67% tokens for K=5 (+8% diversity) | 3-5x token cost vs single-agent | Medium (4 agents + Synthesizer) | K=3 sweet spot, K=5 diminishing | Multi-lab replication, strong ablations |
| **3. Persistent File-System Workspace** | RACE 53.94 SOTA, -10.35 w/o dual-agent | File I/O <0.03% wall-clock | Scales with research rounds (10 rounds: 29K chars) | Low (simple file ops) | Linear with budget (3/5/10 rounds) | SOTA on main benchmark, large ablation effect |
| **4. Self-Healing (Pivot/Refine)** | +42% over AI Scientist v2, 10/10→6/10 completion w/o | Adds latency per repair (N_r=10 max) | Low overhead | High (state machine + failure taxonomy) | Limited (N_p=2 max pivots) | Strong ablations, 25 topics |
| **5. GRPO-RL Training** | 7B > GPT-4o on GAIA (53.2 vs 37.8) | 7.5x faster, 3.75x cheaper at inference | $50K-200K training for 7B | High (RL infrastructure) | Log-linear with training data to 30K | Scaling validated 7B→235B, multi-lab |
| **6. Supervisor-Fanout Parallelism** | +90.2% over single-agent (Anthropic internal) | Up to 90% latency reduction | 15x token cost vs chat | Medium (subgraphs, compression) | Bounded by concurrency (5-10 workers) | Production deployment (Anthropic) |
| **7. Tri-Level Co-Evolution** | 100% E2E success, 8.963 alignment | R1 highest latency, decreasing per round | Skills (~2-10 entries), memory (~12 entries/topic) | High (3 interacting loops) | Compounding efficiency across rounds | Human evaluation (3 PhD researchers), complementary ablations |
| **8. Self-Organizing Teams** | 74.4% BioML-Bench, +8.33% over single-agent | Discussion phase adds latency before compute | 9 agent instances running continuously | Very High (template bloat issue) | Parallel search across hypotheses | 3 benchmarks, documented failure logs |

---

## 3. Convergences

### C1: Context management is the binding constraint, and the solution is structured synthesis, not larger windows.

**Independent sources agreeing:**
- IterResearch [2511.07327v2]: "Strategic forgetting" via `M_t` report — future decisions depend only on current synthesized state.
- Tongyi DeepResearch [2510.24701v3]: Markovian state reconstruction — explicit synthesis at each step prevents context overflow.
- FS-Researcher [2602.01566v2]: File system as external memory — "the context window is the binding constraint on deep research." Persistent workspace + separated stages.
- COMEM [2605.30842v1]: Decoupled small memory model compresses history to bounded latent summary.
- Anthropic Blog [Web]: "Memory: External, survives context truncation. Stores the research plan so the lead can retrieve it after context window resets."

**Convergence statement:** Five independent research groups (Renmin+Tongyi, Alibaba, USTC, Amazon+UCSD, Anthropic) converge on the same principle: compress-and-synthesize rather than accumulate-and-overflow. No source advocates for larger context windows as the primary solution.

### C2: Dual-agent/dual-role separation (evidence collection vs. synthesis) outperforms single-agent designs.

**Independent sources agreeing:**
- FS-Researcher [2602.01566v2]: -10.35 RACE when merging dual agents into one — the single largest ablation effect across all systems surveyed.
- Argus [2605.16217v3]: Searcher+Navigator separation. Navigator evaluates evidence graph holistically and conducts verification — a role impossible if it were also doing searches.
- Anthropic Blog [Web]: LeadResearcher (Opus 4) + subagents (Sonnet 4) outperforms single Opus 4 by +90.2%.
- NanoResearch [2605.10813v2]: Separate models for Planner (Qwen3-8B), Ideation/Execution (DeepSeek-V3.2), Coding (GPT-5.3-Codex), Writing (Claude Sonnet 4.6), Review (Gemini 3.1 Flash Lite), Revision (Gemini 3 Pro).
- AutoScientists [Web]: Discussion (analysts) + execution (GPU agents) as separate roles.
- AI Auto-Research Roadmap [2605.18661v1]: "Layered architectures (exploration → execution → verification) emerge as the convergent design pattern."

**Convergence statement:** Six independent systems converge on the same architectural principle. The single largest improvement in any system comes from separating roles, not from scaling a single model.

### C3: Verification must be architecturally separate from generation, not a post-hoc check.

**Independent sources agreeing:**
- AutoResearchClaw [2605.20025v2]: VerifiedRegistry prevents fabricated numbers from reaching output. Removing verification inflates apparent acceptance but 3/5 papers contain fabricated values.
- Claw AI Lab [2605.22662v1]: Runtime Python guard is read-only, injected into sandbox — cannot modify experiment logic, only observe and validate.
- Argus [2605.16217v3]: Contrastive reward `R_w/v − R_w/o_v` explicitly measures verification's causal contribution. Verification policy is trained separately and operates on the evidence graph as a whole.
- AI Auto-Research Roadmap [2605.18661v1]: "Artifact generation outpaces scientific verification" — identified as the #1 cross-cutting insight.
- FS-Researcher [2602.01566v2]: Report Writer has web tools removed — forced to treat KB as sole fact source, preventing post-hoc fabrication.

**Convergence statement:** Five independent sources agree: verification must be an independent architectural component, not a self-check within the same agent/context that generated the claims.

### C4: Multi-agent outperforms single-agent for research, but with a clear sweet spot (3-5 agents for most tasks).

**Independent sources agreeing:**
- AutoResearchClaw [2605.20025v2]: K=3 debate agents is the sweet spot (K=2: -23% diversity, K=5: +67% tokens for +8% diversity).
- Anthropic Blog [Web]: "Scale effort to query complexity": 1 agent (simple), 2-4 subagents (comparisons), >10 subagents (complex).
- AI Auto-Research Roadmap [2605.18661v1]: "3 critique-revision rounds often sufficient (diminishing returns beyond)."
- Open Deep Research [Web]: "Bias towards single agent for simplicity" — only fans out when "clear opportunity for parallelization."
- AutoScientists [Web]: 6 GPU agents + 3 analysts, but with template bloat as a documented failure mode.

**Convergence statement:** The optimal agent count scales with task complexity, not as a fixed constant. Simple queries: 1 agent. Comparisons: 3-5. Complex multi-domain: 8-10+. Adding agents beyond the sweet spot increases token cost disproportionately.

### C5: GRPO with group-relative advantage is the convergent RL algorithm for agentic research training.

**Independent sources agreeing:**
- DeepResearcher [2605.29796v2]: GRPO eliminates value network, group-relative advantage handles variable difficulty.
- Tongyi DeepResearch [2510.24701v3]: Adapted GRPO with token-level PG + leave-one-out advantage.
- IterResearch [2511.07327v2]: GSPO (GRPO variant) with geometric discounting for efficiency.
- COMEM [2605.30842v1]: GRPO-AC training memory model with functional equivalence reward.
- Argus [2605.16217v3]: GRPO with contrastive reward for Navigator training.

**Convergence statement:** Five independent groups converge on GRPO as the preferred RL algorithm for agent trajectory optimization. No source advocates for PPO (DeepResearcher shows GRPO outperforms PPO +3.1% on GAIA). The KL constraint is universally identified as essential — without it, models collapse into degenerate behaviors.

---

## 4. Contradictions

### D1: Single end-to-end trained model vs. modular multi-agent orchestration.

- **Single-model camp:** DeepResearcher [2605.29796v2] argues: "A single trained model avoids the coordination overhead, error propagation, and latency of multi-agent systems." Tongyi DeepResearch [2510.24701v3] follows "The Bitter Lesson": simple ReAct + scalable computation > complex multi-agent designs.
- **Multi-agent camp:** FS-Researcher [2602.01566v2] shows dual-agent separation contributes +10.35 RACE — the largest effect. Anthropic Blog [Web] shows +90.2% for multi-agent over single Opus 4. NanoResearch [2605.10813v2] uses 6 different models across stages.

**Resolution required in Phase 4:** The contradiction is partially resolved by recognizing that these optimize different axes. Single-model approaches optimize for training efficiency and deployment simplicity. Multi-agent approaches optimize for output quality and role specialization. The likely synthesis for Lyra: a single backbone model with role-conditioned prompts (like Tongyi's domain adapters) rather than fully separate models, but with separate context windows (like FS-Researcher's dual-agent pattern) and an external memory/workspace (like the convergent C1 pattern).

### D2: Open-ended exploration vs. structured pipeline progression.

- **Open-ended camp:** AutoScientists [Web] uses self-organizing teams with hypothesis-based exploration and self-triggered discussion rounds. No fixed stage order beyond the HEARTBEAT state machine. MetaClaw [2603.17187v1] uses opportunistic scheduling (idle windows trigger training).
- **Structured camp:** AutoResearchClaw [2605.20025v2] enforces a strict 23-stage sequential pipeline with formal input/output contracts. FS-Researcher [2602.01566v2] uses checklist-gated stage progression. Argus [2605.16217v3] uses three clearly defined stages (Search → Verify → Synthesize).

**Resolution required in Phase 4:** The AutoResearchClaw road map paper [2605.18661v1] suggests a synthesis: "Effective systems converge on layered architectures — exploration + execution + verification layers." The exploration layer can be open-ended (hypothesis search), while execution and verification layers benefit from structured progression. Lyra should adopt a hybrid: flexible within stages, structured between stages.

### D3: Human-in-the-loop: targeted interventions vs. full autonomy.

- **Targeted HITL camp:** AutoResearchClaw CoPilot [2605.20025v2]: 6 targeted interventions achieve 87.5% accept rate, beating Full-Auto (+62.5pp) AND Step-by-Step (23 interventions, 50% accept). Key finding: "human expertise has highest marginal impact at a small number of decision points."
- **Full autonomy camp:** DeepResearcher [2605.29796v2], Tongyi DeepResearch [2510.24701v3], IterResearch [2511.07327v2] all designed for zero-intervention operation. Trained end-to-end with RL to discover optimal strategies without human input.

**Resolution required in Phase 4:** This is not a true contradiction — it depends on the deployment context. For research assistance (Lyra's primary use case), the CoPilot model (targeted interventions at high-leverage points) dominates both Full-Auto and Step-by-Step empirically. The autonomous systems (DeepResearcher, Tongyi) target benchmark performance, not human collaboration. Lyra should adopt the CoPilot model with SmartPause (uncertainty-driven dynamic pausing), as described in AutoResearchClaw.

### D4: Skills as prompt-level heuristics vs. trained weights.

- **Prompt-level camp:** MetaClaw [2603.17187v1], AutoResearchClaw [2605.20025v2]: Skills/lessons injected as natural-language overlays into prompts. Zero-downtime, gradient-free, no retraining. But monotonic growth, no formal verification of correctness.
- **Trained-weight camp:** NanoResearch [2605.10813v2]: SDPO updates planner weights to internalize preferences. GRPO-trained policy. Requires training infrastructure but produces parameterized learning.
- **Dual approach:** NanoResearch actually combines both — SkillBank (prompt-level) + SDPO (weight-level). MetaClaw also combines Skills (prompt) + RL policy updates (weights). The contradiction is about which to prioritize, not whether both are useful.

**Resolution:** Both are necessary and complementary. Fast prompt-level adaptation handles immediate failure recovery; slow weight-level learning refines underlying capabilities. This is the MetaClaw thesis [2603.17187v1], validated empirically — Skills-only lifts multi-choice, Full (Skills+RL) reverses to lift file-execution. Lyra should adopt the dual approach with explicit versioning to prevent stale reward contamination (support-query separation).

---

## 5. Open Problems

### P1: Silent semantic collapse under verification.

**Problem:** AutoResearchClaw's T10 case [2605.20025v2] documents a failure where all numeric verification gates pass but the paper produces "identical zero-bias outputs across all cross-validation strategies." The registry gate only checks number existence, not whether measurements address the research question. No proposed system solves this.

**Significance:** This is the hardest category of autonomous research failure — outputs that pass all automated checks but are scientifically meaningless. Detection requires semantic understanding of the research methodology, which current verification systems lack.

### P2: Novelty ceiling for incremental-only research.

**Problem:** NanoResearch [2605.10813v2] achieves its highest novelty score at 5.645/10 (simulated) and 7.0/10 (human, R2). All benchmark tasks are labeled "incremental_innovation." No system is designed or evaluated for breakthrough research. AI Auto-Research Roadmap [2605.18661v1] notes: "LLM ideas rated higher novelty than human ideas (p<0.05) but degrade sharply after implementation (Delta = -1.98 vs -0.63 for human)."

**Significance:** Current systems optimize for incremental advances within established paradigms. Breakthrough innovation — paradigm shifts, entirely new problem formulations — remains unsolved. The negative correlation between LLM novelty judgments and later real-world impact (rho = -0.29) [2605.18661v1] suggests current novelty metrics are actively misleading.

### P3: Error propagation across pipeline stage boundaries.

**Problem:** AI Auto-Research Roadmap [2605.18661v1] identifies this as the central failure mode: "Errors introduced in early stages amplify downstream." Stage-17 in AutoResearchClaw [2605.20025v2] is the worst bottleneck — 11 of 13 invalid HITL runs fail at paper_draft, but root causes include no usable metrics, dependency breakage, design pathologies from earlier stages. No system proposes a general mechanism for detecting, tracing, and containing error propagation across stage boundaries.

**Significance:** Without cross-stage error containment, quality gates at later stages conflate heterogeneous upstream causes, making it impossible to determine whether to fix the experiment, the design, or the hypothesis.

### P4: Physical/wet-lab domain integration.

**Problem:** All evaluated systems are restricted to CS/ML/statistics domains where research outputs can be fully realized through code and text. Tongyi DeepResearch [2510.24701v3] and AutoResearchClaw [2605.20025v2] have initial domain adapters (HEP-ph, biology), but quality is significantly lower (AutoResearchClaw: HEP-ph 0.489 vs ML 0.912). NanoResearch [2605.10813v2] explicitly notes: "Extension to biology, chemistry, or physics (involving physical experimentation and instrument control) is important and non-trivial but not addressed."

**Significance:** Physical experimentation requires instrument control, safety constraints, material constraints, and real-world validation that current agent architectures do not model. This is the largest domain gap in autonomous research capability.

### P5: Cross-backbone generalization and model lock-in.

**Problem:** AutoResearchClaw [2605.20025v2] uses GPT-5.3-codex exclusively. Claw AI Lab [2605.22662v1] uses GPT-5.4. DeepResearcher [2605.29796v2] uses DeepSeek-R1 backbone. Argus [2605.16217v3] uses Qwen3.5-35B-A3B. No paper evaluates whether its architecture works with different backbone models. The AI Auto-Research Roadmap [2605.18661v1] notes: "No lifecycle-scale benchmark exists; cross-system comparison confounded by different base models."

**Significance:** Without cross-backbone evaluation, it is impossible to distinguish architectural contributions from model capability contributions. This prevents evidence-based architecture selection.

### P6: Real human-in-the-loop evaluation (not scripted).

**Problem:** AutoResearchClaw's HITL experiments [2605.20025v2] use "scripted interventions rather than live human participants." NanoResearch's human evaluation [2605.10813v2] uses only 3 PhD researchers. Claw AI Lab [2605.22662v1] uses LLM-as-judge only, no human expert review. The book "Building AI Agent Platforms" [Book: O'Mahony & Nonnenmacher, 2027, Ch. 1] identifies that "online evaluation is critical — offline evals don't guarantee production behavior."

**Significance:** Real human-AI research collaboration dynamics (attention drift, trust calibration, intervention timing, expertise asymmetry) are not captured by scripted or simulated evaluations. The impressive CoPilot results (87.5% accept rate with 6 interventions) may not generalize to real researchers.

### P7: Cost-quality Pareto frontier characterization.

**Problem:** Cost data is inconsistently reported. AutoResearchClaw reports $3-15/run [2605.20025v2]. NanoResearch reports $1.43-4.16/topic [2605.10813v2]. FS-Researcher reports $2.00-12.54/query [2602.01566v2]. Anthropic reports 15x token cost for multi-agent vs chat [Web]. But costs are reported at different granularities (per run vs per query vs per paper), with different backbones, making cross-system cost-quality comparison impossible.

**Significance:** Without a standardized cost-quality Pareto frontier, adopters cannot make evidence-based decisions about which architecture to deploy at what budget. AI Auto-Research Roadmap [2605.18661v1] calls for "standardized benchmarks controlling for model, cost, and compute budget."

---

## 6. Recommendations for Lyra

Ranked by impact/effort ratio, with rationale grounded in convergence evidence.

### Tier 1 — Foundation (adopt immediately)

**R1: Adopt iterative workspace reconstruction as Lyra's core agent loop architecture.**
- **What:** Replace any linear context accumulation with an evolving "research notebook" state `M_t` that the agent updates at each step. Condition on `(question, M_t, last_interaction)` only.
- **Rationale:** This is the strongest convergence in the literature (C1) — five independent groups converge on this pattern. It enables unbounded session depth. The prompt-only variant from IterResearch [2511.07327v2] means immediate benefit without training. Tongyi DeepResearch [2510.24701v3] provides a production reference implementation.
- **Sources:** [2511.07327v2], [2510.24701v3], [2602.01566v2], [2605.30842v1], [Web: anthropic.com]

**R2: Implement dual-agent separation (evidence collection agent + synthesis agent) with a persistent file-system workspace.**
- **What:** Separate Lyra's research workflow into two agents operating on a shared workspace: a Context Builder that searches, reads, and builds a structured knowledge base; and a Report Writer that synthesizes from the KB with web tools disabled.
- **Rationale:** The dual-agent pattern produces the single largest ablation effect measured in the literature (C2, -10.35 RACE). The persistent file-system workspace enables multi-session refinement and human-in-the-loop review between sessions. File I/O overhead is negligible (<0.03% wall-clock time).
- **Sources:** [2602.01566v2], [Web: langchain-ai/open_deep_research], [Web: anthropic.com]

**R3: Build a runtime verification guard (read-only Python controller) for experiment execution.**
- **What:** A Python controller injected into every experiment sandbox that enforces time budgets, detects NaN/Inf metrics, performs anti-fabrication smoke tests, and formalizes metric serialization. Architecturally separate from the code generation agent (C3 — verification must be independent).
- **Rationale:** Without verification, 60% of apparent high-quality autonomous results contain fabricated values (AutoResearchClaw ablation). The Claw AI Lab guard pattern [2605.22662v1] is well-scoped and composable — a 2-3 week prototype.
- **Sources:** [2605.22662v1], [2605.20025v2], [2605.18661v1]

### Tier 2 — Enhance (adopt in Phase 4)

**R4: Add a Pivot/Refine/Proceed decision loop to Lyra's execution engine.**
- **What:** When an agent action fails, capture the failure signature, generate targeted fixes, and make a structured decision: Proceed (success), Refine (retry with fix, up to N_r=10), or Pivot (return to planning with failure as new evidence, up to N_p=2).
- **Rationale:** Transforms brittle execute-then-terminate pipelines into resilient explore-then-adapt loops. Self-healing is the largest completion contributor in AutoResearchClaw (10/10 → 6/10 without it). The Pivot/Refine semantics map naturally to Lyra's existing error handling.
- **Sources:** [2605.20025v2], [2605.10813v2]

**R5: Implement a supervisor-fanout pattern for parallel sub-research with compression.**
- **What:** A supervisor agent decomposes complex research queries into parallel sub-tasks, fans out to worker agents with independent context windows, collects compressed findings, and synthesizes. Include a `think_tool` that forces strategic reflection between delegation rounds.
- **Rationale:** +90.2% performance gain over single-agent (Anthropic production data). Up to 90% latency reduction. The Open Deep Research codebase [Web: langchain-ai] provides an MIT-licensed reference implementation.
- **Sources:** [Web: langchain-ai/open_deep_research], [Web: anthropic.com], [2605.20025v2]

**R6: Adopt CoPilot-style targeted human-in-the-loop with SmartPause.**
- **What:** Six high-leverage intervention points (Idea Workshop, Baseline Navigator, Paper Co-Writer, plus literature/experiment/quality gates). SmartPause monitors estimated uncertainty and dynamically pauses when uncertainty exceeds a learned threshold.
- **Rationale:** CoPilot achieves 87.5% accept rate with only 6 interventions — beats Full-Auto (+62.5pp) and Step-by-Step (23 interventions, 50% accept). Human expertise has highest marginal impact at a small number of decision points (D3).
- **Sources:** [2605.20025v2]

### Tier 3 — Investigate (evaluate in Phase 4 before committing)

**R7: Evaluate GRPO-RL training of Lyra's research trajectories.**
- **What:** Train Lyra's agent backbone to optimize full multi-turn research trajectories using GRPO with outcome rewards (factuality + comprehensiveness + format). Start with a small-scale experiment (1K trajectories, 7B model equivalent).
- **Rationale:** GRPO-trained 7B models can outperform GPT-4o on research benchmarks (C5). But training infrastructure cost is significant ($50K-200K), and the approach requires high-quality SFT cold-start data. Worth a small experiment before full commitment.
- **Sources:** [2605.29796v2], [2510.24701v3], [2511.07327v2]

**R8: Implement a tri-level co-evolution loop (SkillBank + Memory + Preference Learning).**
- **What:** Add three interacting stores to Lyra: (1) SkillBank — compact procedural rules (~2-10 entries) distilled from trajectories, (2) Memory Module — user-and-project-scoped fact store, (3) lightweight preference internalization from free-form user feedback.
- **Rationale:** Compounding efficiency across sessions — 76% cost reduction from R1 to R3. But requires significant infrastructure and the cold-start penalty is real (R1 is the most expensive round). Worth evaluating whether SkillBank-only (the simplest component) provides measurable benefits before committing to all three.
- **Sources:** [2605.10813v2], [2603.17187v1]

**R9: Explore self-organizing agent teams for long-running Lyra research sessions.**
- **What:** Agents self-organize into hypothesis-based teams with peer-review-before-compute gating. Include stagnation detection that triggers autonomous restructuring. Meta-improvement loop that edits agent templates based on diagnostic patterns.
- **Rationale:** Demonstrated for sustained parallel research (74.4% BioML-Bench, 1.9x faster optimization). But template bloat (1300+ line role files) and agent reliability issues (hallucinated API calls, stale queue claims) are documented failure modes. High complexity — investigate after R1-R6 are stable.
- **Sources:** [Web: mims-harvard/AutoScientists], [2605.22662v1]

---

## Source Index

### Papers (by arXiv ID)
| ID | Short Title | Venue/Year |
|----|-------------|------------|
| 2511.07327v2 | IterResearch | ICLR 2026 |
| 2510.24701v3 | Tongyi DeepResearch | arXiv 2026 |
| 2605.20025v2 | AutoResearchClaw | arXiv 2026 |
| 2605.10813v2 | NanoResearch | arXiv 2026 |
| 2605.29796v2 | DeepResearcher | arXiv 2025 |
| 2605.18661v1 | AI Auto-Research Roadmap | arXiv 2026 |
| 2605.22662v1 | Claw AI Lab | arXiv 2026 |
| 2602.01566v2 | FS-Researcher | arXiv 2026 |
| 2603.17187v1 | MetaClaw | arXiv 2026 |
| 2605.16217v3 | Argus | arXiv 2026 |
| 2605.30842v1 | COMEM | ICML 2026 |
| 2502.04644v2 | Agentic Reasoning | arXiv 2025 |
| 2510.25817v1 | Data-Centric Survey | ACL 2025 |
| 2605.28655v1 | AutoScientists (paper) | arXiv 2026 |
| 2308.03688v3 | AgentBench | arXiv 2023 |

### Web/Repo Notes
| ID | Source | Type |
|----|--------|------|
| aiming-lab/AutoResearchClaw | GitHub repo analysis | Implementation deep-read |
| langchain-ai/open_deep_research | GitHub repo analysis | Implementation deep-read |
| Alibaba-NLP/DeepResearch | GitHub repo analysis | Implementation deep-read |
| mims-harvard/AutoScientists | GitHub repo analysis | Implementation deep-read |
| anthropic.com/engineering/built-multi-agent-research-system | Engineering blog | Production architecture |

### Book Notes
| ID | Source | Relevant Chapter |
|----|--------|-----------------|
| O'Mahony & Nonnenmacher, 2027 | Building AI Agent Platforms | Ch. 1: AI Application Patterns (Graph-based AI agents, orchestrated workflows) |
