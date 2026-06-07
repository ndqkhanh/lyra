# Self-Evolving Systems & Continual Learning — Thematic Synthesis

**Lyra Upgrade Phase 3 — Synthesis Document**
**Date:** 2026-06-07
**Sources consulted:** 24 papers, 2 books, 4 web repos, across 500+ note files
**Status:** Definitive synthesis, feeds Phase 4 workstream plans

---

## 1. Frontier Techniques (ranked by evidence strength)

### Technique 1: Validation-Gated Skill Text Optimization (SkillOpt)

- **Sources:** SkillOpt paper (arXiv:2605.23904v2, Microsoft Research + SJTU, May 2026); CODESKILL paper (arXiv:2605.25430v1, May 2026) — convergent validation
- **Mechanism:** A separate, stronger optimizer model (e.g., GPT-5.5) converts scored rollout trajectories into bounded add/delete/replace edits on a natural-language skill document. A held-out validation gate accepts edits only when they strictly improve task metrics. Key innovations: (a) textual learning rate (cosine-scheduled edit budget Lt, default 4→2), (b) rejected-edit buffer providing negative feedback at zero inference cost, (c) epoch-wise slow/meta update that writes protected longitudinal guidance, (d) hierarchical merge that deduplicates and resolves contradictions across failure/success minibatch reflections. The skill document is the trainable artifact — model weights are frozen.
- **Evidence:**
  - **+23.5 points avg gain** on GPT-5.5 across 6 direct-chat benchmarks (SkillOpt paper, Table 1)
  - **+17.6 points avg gain** across 7 diverse models (GPT-5.5 through Qwen3.5-4B) — SkillOpt paper, Table 1
  - **52/52 cells best or tied-best** against all baselines including GEPA, Trace2Skill, EvoSkill — SkillOpt paper, §2
  - **+24.8 avg gain on Codex CLI harness**, +19.1 on Claude Code — multi-harness validated
  - **Cross-harness transfer:** SpreadsheetBench skill from Codex→Claude Code yields **+59.7 points** — SkillOpt paper, Table 4
  - **Compact artifacts:** median final skill = 920 tokens, 1-4 accepted edits reach deployment
  - **Removing slow/meta update causes catastrophic 22.5-point drop** on SpreadsheetBench — SkillOpt paper, Table 3
  - CODESKILL independently validates the learnable-policy approach: **+32.8% relative pass rate** on coding benchmarks with RL-trained skill management policy (CODESKILL paper, arXiv:2605.25430v1)
  - **Zero inference-time overhead:** skills are static .md files injected into the prompt — no extra model calls
- **Maturity:** Lab validated (no known production deployment; Microsoft Research project)

### Technique 2: Gene Evolution Protocol (GEP) — Compact Control-Oriented Experience Objects

- **Sources:** EvoMap/skill2gep paper (arXiv:2604.15097v2, June 2026, 4,590 trials); EvoMap/evolver repo (deep-read, v1.88.3); Designing AI Agents book (Manning, 2026, Chapter 1 — "harness engineering" philosophy); EvoMap/awesome-agent-evolution repo
- **Mechanism:** Strategy Genes are compact (~230 tokens) structured objects: `g = (m, u, π, α, c, v)` where m = matching signals, u = one-sentence summary, π = strategic steps, α = AVOID cues, c = constraints, v = validation hooks. The GEP loop runs SCAN → SIGNAL → INTENT → MUTATE → VALIDATE → SOLIDIFY, evolving genes from execution traces. Three-layer object hierarchy: Genes (atomic capability units), Capsules (validated execution paths with audit trail), Events (immutable evolution logs). Critically distinct from documentation-oriented skills (~2,500 tokens, -1.1 pp vs no-guidance).
- **Evidence:**
  - **Genes (+3.0 pp) vs. Skills (-1.1 pp)** over no-guidance at 10x fewer tokens — skill2gep paper, Table 1
  - **Skill-Overview section alone: -4.7 pp** — most documentation is harmful — skill2gep paper, Table 12
  - **CritPt benchmark:** Gene evolution improved 9.1% → 18.57% (Feb 16) → 27.14% (Mar 26) — skill2gep paper, Figure 5
  - **~$0.81 per evolution run**, 32.1x cheaper than reported benchmark cost
  - **Structured genes outperform flattened prose by 3.5 pp** — structure is essential to control signal
  - **Failure encoded as compact warnings (+4.6 pp) outperforms additive history accumulation**
  - **Complementary gene collapse:** two complementary genes drop to 44.9% (-6.1 pp vs no-guidance) — multi-gene composition is unsolved — skill2gep paper, Table 4
  - Evolver repo: production-grade daemon with singleton lock, suicide-respawn, 45min cycle timeout, 500MB RSS cap, git-integrated rollback
- **Maturity:** Hybrid — protocol specification (skill2gep) + production daemon (evolver, installed via npm). Core engine obfuscated; licensing transitioning from GPL-3.0 to source-available.

### Technique 3: MCTS-Driven Agent Workflow/Architecture Search

- **Sources:** AFlow paper (arXiv:2410.10762v4, MetaGPT, ICLR-related); SWE-Search paper (arXiv:2410.20285v6, ICLR 2025); DITS paper (arXiv:2502.00955v2, CMU + USTC); CaTS paper (ICLR 2026)
- **Mechanism:** Monte Carlo Tree Search over code-represented agent architectures (AFlow) or over software engineering trajectory states (SWE-Search). Key innovations: (a) workflows as Python classes, enabling loops/conditionals/ensembles undiscoverable in graph representations (AFlow), (b) hybrid value function outputting both scalar reward AND natural-language critique for hindsight feedback (SWE-Search), (c) modified UCT with depth-aware bonus/penalty terms mirroring human exploration patterns (SWE-Search), (d) influence-score-guided data selection replacing Q-value-based selection for multi-agent training (DITS), (e) self-calibrated confidence for adaptive test-time compute allocation (CaTS).
- **Evidence:**
  - AFlow: **5.7% avg improvement over human-designed SOTA** workflows across 6 benchmarks; **19.5% over ADAS** prior automated method — AFlow paper
  - AFlow: GPT-4o-mini + AFlow **outperforms GPT-4o at 4.55% of inference cost** (Pareto frontier result)
  - SWE-Search: **+23% mean relative improvement** across 5 diverse models (GPT-4o: 25.7% → 31.0%) — SWE-Search paper, Table 1
  - DITS: **+2.5% avg over Optima** with **46% lower total GPU cost** — DITS paper, efficiency table
  - CaTS: **94.2% sample savings** to reach same accuracy on MathQA; 3 model families validated — CaTS paper, Figure 1
  - SWE-Search cost: 5-14x API cost multiplier — prohibitive for routine use without budget-aware truncation
- **Maturity:** Lab validated at ICLR level. AFlow and SWE-Search are open-source (MIT). DITS has code published. CaTS has theoretical guarantees (Bernstein inequality, Theorem 5).

### Technique 4: Self-Consistency Voting for Pseudo-Label RL (No Human Labels)

- **Sources:** EvoQuality paper (arXiv:2509.25787v4, ICLR 2026, CityU HK + ByteDance); CaTS paper (ICLR 2026); AgenticEval paper (arXiv:2509.26100v2, Fudan University, 2026)
- **Mechanism:** Prompt the model K=32 times with the same input; aggregate via majority voting to produce high-confidence pseudo-labels; define a fidelity reward measuring alignment between model's predicted probability distribution and the pseudo-label consensus; update via GRPO with KL regularization against frozen reference. No ground-truth labels needed. EvoQuality uses pairwise ranking (Thurstone model via Gaussian CDF) rather than score averaging — regression-based self-evolution STALLS after Round 1 while ranking-based continues improving.
- **Evidence:**
  - EvoQuality: **+31.8% WAVG PLCC** gain across 8 IQA benchmarks; **+46.2% on PIPAL** — EvoQuality paper, Table 2
  - **Outperforms ALL supervised VLM models on OOD generalization** (WAVG 0.762 vs. 0.704) without using any labels
  - EvoEstimate (regression-based) stalls at +0.1% Round 2; EvoQuality (ranking-based) continues improving — Table 5
  - AgenticEval: Self-evolving safety evaluation discovers **36.14 pp more failures** on GPT-5 vs. static benchmarks — AgenticEval paper, Figure 3
  - AgenticEval evaluator reliability: **88-91% accuracy vs. human annotators**, Cohen's κ = 0.77-0.81
  - CaTS: Self-calibrated confidence from SSC (Soft Self-Consistency) achieves **ECE 3.42-3.79** (vs. 12-28 vanilla) — CaTS paper, Table 4
  - K=32 voting budget required for stability; K=8 shows significant degradation — EvoQuality paper, Figure 3
- **Maturity:** ICLR 2026 validated. Not yet seen in production deployments. EvoQuality code not open-source.

### Technique 5: Dual-Source Memory Extraction from Successes AND Failures

- **Sources:** ReasoningBank paper (arXiv:2509.25140v2, Google Cloud AI Research + UIUC, 2025); CFGM paper (EMNLP 2025, CAS); Memory Survey paper (arXiv:2603.07670v1, March 2026); Designing AI Agents book (Manning, 2026, Chapters 2-3)
- **Mechanism:** After task completion, a binary LLM-as-a-Judge classifies trajectories as success/failure. Separate extraction prompts process each: success extraction distills validated strategies ("why did it work?"), failure extraction distills counterfactual guardrails ("why did it fail, what to avoid?"). Memory items use a structured 3-field schema (title + description + content) with explicit prohibitions against environment-specific references — forcing generalizable reasoning abstractions. Simple additive consolidation suffices (no complex pruning needed if content quality is high). At query time, top-k embedding-based retrieval injects relevant memories.
- **Evidence:**
  - ReasoningBank: **+20.5% relative SR improvement** over No Memory on WebArena; **+20% on SWE-Bench-Verified** (34.2% → 38.8%) — ReasoningBank paper, Tables 1-2
  - **4.3% token overhead** vs. 15-17% for Synapse/AWM — ReasoningBank paper, Table 5
  - **Failure learning:** +3.2 SR from adding failures (vs. AWM which degrades -2.2, Synapse +1.1) — Figure 7
  - CFGM: **+10.40 pp over ReAct** on AlfWorld (80.60% → 91.00%); **+20 pp on WebShop** — CFGM paper, Table 1
  - CFGM: **25% fewer online interaction turns** (14.32 vs. 19.01) — efficiency gain from memory
  - Memory Survey: "Memory-vs-no-memory gap exceeds the gap between different LLM backbones" — Du 2026, §3
  - **Robust to judge noise:** performance stable within 70-90% judge accuracy range — ReasoningBank paper, Figure 8
- **Maturity:** Lab validated (Google, EMNLP). ReasoningBank code open-source (Apache 2.0). Most immediately deployable technique — simplest architecture (prompt engineering + embedding DB).

### Technique 6: Adversarial Curriculum Self-Play for Agent Training

- **Sources:** HAP paper (NeurIPS 2025, arXiv:2510.18407v1, Peking University); Multi-Agent Cultural Debate paper (arXiv:2505.24671v2, University of Maryland, 2025)
- **Mechanism:** A teacher policy adversarially selects/generates tasks to MINIMIZE student success, while student maximizes reward. The minimax formulation `min_ϕ max_θ J(θ, ϕ)` creates a self-regulating equilibrium: as the student improves, the teacher is directly incentivized to find harder challenges. Three critical mitigations: (a) cold-start warm-up phase before adversarial dynamics engage, (b) entropy regularization preventing teacher collapse to uniform distribution, (c) probabilistic lower bounds on task selection preventing catastrophic forgetting. Teacher and student can be different model families — heterogeneous asymmetry is a feature, not a bug.
- **Evidence:**
  - HAP: **85% of human performance** on Crafter (0.723 vs 0.85 human) — HAP paper, Table Crafter
  - HAP: **Narrows human-algorithm gap by 30%** vs. prior SOTA on CRAFT — HAP paper
  - **Entropy regularization is most critical:** hard task performance drops from 0.20 → 0.11 without it — HAP paper, Ablation
  - **Lower bounds essential for stability:** models fail to converge 70% of time without them — HAP paper
  - Multi-Agent Debate: **+7.05% avg accuracy** over single-LLM; 7-9B model pairs match 27B model — Debate paper, Table 2
  - Debate: Single round sufficient — dead loops at >1 round; **best cultural parity (0.972)** — Debate paper, Table 3
  - HAP: Gains concentrated on hard/compositional tasks where baselines fail entirely; modest on easy tasks (ceiling effect)
- **Maturity:** NeurIPS 2025 (HAP), arXiv preprints (Debate). No known production agent deployment. Requires dual-network architecture and careful hyperparameter tuning.

### Technique 7: Retrieval-as-Reasoning with Self-Evolving Knowledge Structures

- **Sources:** LLM-Wiki paper (arXiv:2605.25480v2, Tencent WeChat, May 2026); SELF-RAG paper (arXiv:2310.11511v1, UW + AI2 + IBM, 2023); Memory Survey paper (arXiv:2603.07670v1)
- **Mechanism:** Pre-compile source documents into structured, bidirectionally-linked Wiki pages with YAML frontmatter (type, created, tags, aliases) and explicit `[[wikilinks]]`. At query time, the agent traverses this compiled structure via search → read → link-follow operations rather than one-shot embedding similarity lookup. A persistent Error Book drives self-evolution: detect errors → attribute root causes → formalize constraints → inject into future compilation → verify and close. Five-stage lifecycle: Discover → Attribute → Constrain → Inject → Verify/Close. Two-layer repair: deterministic code auto-fix for structural errors + LLM periodic fix for content errors.
- **Evidence:**
  - LLM-Wiki: **+8.1 F1 over LightRAG** on MuSiQue (compositional reasoning) — LLM-Wiki paper, Table 1
  - LLM-Wiki: **0.983 F1 on 4-hop questions** (Dense RAG: 0.924) — gap widens with depth — Figure 3
  - LLM-Wiki: **2.5x faster than LightRAG** in query latency (14.9-27.1s vs. 41.4-51.3s) — Table 10
  - **Error Book contributes +3.4-4.0 F1** across benchmarks — LLM-Wiki paper, Table 3 ablation
  - SELF-RAG: Adaptive retrieval (deciding WHEN to retrieve) boosts PopQA from 24.7 → 54.9 over always-retrieve — SELF-RAG paper, Ablation
  - SELF-RAG 7B beats ChatGPT (larger, proprietary, RLHF-trained) on PubHealth (72.4 vs 70.1) — SELF-RAG paper, §2.1
  - Single-doc disadvantage: Wikipedia-structured summarization can omit fine-grained local details (-2.3 AC vs. HippoRAG 2) — LLM-Wiki paper, Table 2
- **Maturity:** Lab validated (arXiv preprints). LLM-Wiki uses GPT-4o API (proprietary). SELF-RAG models open-source (Llama2-7B/13B). Error Book pattern is novel and underexplored.

### Technique 8: Evolutionary Prompt/Program Refinement with Automated Evaluators

- **Sources:** AlphaEvolve (Google DeepMind blog, May 2025); ChemAmp paper (arXiv:2505.21569v3, Fudan University, April 2026); AI for Auto-Research survey (arXiv:2605.18661v1, May 2026)
- **Mechanism:** Wrap an LLM agent in an evolutionary outer loop: generate N candidate solutions, evaluate each automatically, feed fittest candidates back as prompt context to seed next generation. AlphaEvolve uses Gemini Flash (breadth) + Gemini Pro (depth). ChemAmp uses bi-phase encapsulation: Stage 1 amplifies individual tools via self-stacking, Stage 2 discovers cross-tool synergies via hierarchical composition. Both avoid gradient updates — evolution happens via prompt context.
- **Evidence:**
  - AlphaEvolve: Borg scheduling heuristic **in production 1+ year**, recovering **~0.7% of Google's worldwide compute resources**
  - AlphaEvolve: **23% speedup on Gemini training matrix multiply kernel**, **1% reduction in total training time**
  - AlphaEvolve: **32.5% speedup on FlashAttention** GPU kernels
  - AlphaEvolve: Surpasses AlphaTensor on complex 4x4 matrix multiplication (48 scalar multiplications)
  - AlphaEvolve: **~75% rediscovered SOTA, ~20% improved SOTA** across 50+ open math problems
  - ChemAmp: **SOTA on 4 chemistry tasks 0-shot**; **94% inference token reduction** vs. vanilla MAS
  - ChemAmp: Emergent "Reserve" safety behavior — agent declines unanswerable queries
  - Auto-Research survey: **80% fabrication rate** in fully autonomous ML experiments; semantic errors are 58.6% of research code errors — survey paper, §3.3
- **Maturity:** Production deployed (AlphaEvolve at Google). ChemAmp lab validated (arXiv). Requires automated evaluators — limited to domains with computable metrics.

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy Gain | Latency Overhead | Memory/Token Cost | Engineering Complexity | Scalability | Evidence Strength |
|-----------|--------------|------------------|-------------------|------------------------|-------------|-------------------|
| **SkillOpt (validation-gated text opt)** | +17.6 avg (7 models), +23.5 best | Zero at inference (static .md) | 20-214M training tokens (one-time) | Medium (optimizer loop + validation gate) | High (cross-model, cross-harness) | Very High (52/52 dominance) |
| **GEP genes (compact control objects)** | +3.0 pp avg, +9.4 pp on CritPt | Zero at inference (230 tokens) | Negligible (230 tokens per gene) | High (SCAN→SOLIDIFY pipeline) | Medium (gene collapse with 2+ genes) | High (4,590 trials, 45 scenarios) |
| **MCTS workflow search (AFlow/SWE-Search)** | +5.7% avg (AFlow), +23% rel (SWE-Search) | 5-14x API cost multiplier | 100+ evals per search run | Very High (MCTS tree + state mgmt + value agent) | Medium (per-task optimization, no transfer) | High (ICLR validated) |
| **Self-consistency pseudo-label RL (EvoQuality)** | +31.8% avg PLCC, +46.2% best | K=32 forward passes per item | 12 hours/epoch on 8×A100 | High (GRPO training + K-sample voting) | Medium (requires in-domain corpus) | High (ICLR 2026) |
| **Dual-source memory (ReasoningBank/CFGM)** | +20.5% rel. SR, +10.4 pp | 4.3% token overhead | 2-4K tokens per task for judge/extraction | Low (prompt engineering + embedding DB) | High (3 model families, 5+ domains) | Very High (Google + EMNLP) |
| **Adversarial curriculum (HAP)** | +3-7% over strong baselines | Dual-network architecture | 2x parameter count during training | Medium (teacher MLP + entropy tuning) | Low (gains on hard tasks, modest on easy) | High (NeurIPS 2025) |
| **Retrieval-as-Reasoning (LLM-Wiki/SELF-RAG)** | +8.1 F1 (MuSiQue), +6.7 F1 (2WikiMHQA) | 2-8x faster than LightRAG | One-time compilation cost, amortized | Medium (compiler pipeline + Error Book) | Medium (tens of thousands page ceiling) | Medium (arXiv preprints) |
| **Evolutionary prompt refinement (AlphaEvolve/ChemAmp)** | 23-32.5% speedup on kernels; SOTA chemistry | N× generations (N=3-5) | Cost scales with N × model calls | Low-Medium (loop controller, evaluator exists) | High (multiple domains, production proven) | Very High (production @ Google) |

---

## 3. Convergences

Where do multiple independent sources agree? These are the safe bets for Phase 4 plans.

### Convergence 1: Validation gates are non-negotiable for autonomous evolution

**Evidence:**
- SkillOpt (Microsoft, 2026): Held-out D_sel strictly gates every candidate skill edit; ties rejected to prevent silent drift; rejected-edit buffer provides negative feedback
- CODESKILL (NTU, 2026): Hybrid reward R(u) = λ·R_Q + R_A·R_E, where R_A (alignment factor) gates execution reward — credit assignment for whether the agent actually followed the skill
- EvoQuality (ICLR 2026): Fidelity reward via Bhattacharyya coefficient between pseudo-label and predicted probability — regression-based evolution without this gate stalls within one round
- GEP Evolver (EvoMap, 2026): VALIDATE stage runs sandboxed execution against validation hooks before SOLIDIFY; failed cycles roll back via git stash/reset
- Designing AI Agents (Manning, 2026): "Agent architecture is bounded resource allocation under uncertainty" — verification is the harness's primary role; "Never triage away failure information"

**Consensus:** Every effective self-evolving system gates every proposed change through an automated validation step before accepting it. Systems without validation gates (unbounded self-editing, simple self-revision) degrade or stall. The gate must be: (a) independent of training data, (b) strict (ties rejected), (c) auditable.

### Convergence 2: Compact, structured representations outperform verbose documentation

**Evidence:**
- GEP paper: Genes (~230 tokens, structured as {signals, summary, strategy, AVOID, constraints, validation}) give +3.0 pp; Skills (~2,500 tokens, documentation-oriented) give -1.1 pp; Skill-Overview alone is -4.7 pp
- SkillOpt paper: Final skills are median 920 tokens; only 1-4 accepted edits reach deployment; unbounded rewrites erase useful rules
- LLM-Wiki paper: Structured wiki pages with YAML frontmatter + explicit `[[wikilinks]]` outperform flat embedding approaches by 3.4-8.1 F1 points
- CODESKILL paper: Multi-granularity bank (task-level + event-driven) with maintenance (add/merge/drop) shrinks bank by 46% with only ~2% cost
- CaTS paper: ~10 extra tokens per response enable confidence-weighted voting that saves 94.2% of samples
- Designing AI Agents book: "A mediocre model with a well-curated 30K-token context outperforms the best model drowning in 180K tokens of noise"

**Consensus:** The useful control signal in agent experience artifacts is sparse and concentrated. Surrounding material (overview, examples, API notes) imposes burden, not benefit. Structure (keywords + strategy + AVOID + constraints) is the first-order factor; format (compact, machine-actionable, evolution-friendly) matters more than completeness.

### Convergence 3: Learning from failures is the differentiator

**Evidence:**
- ReasoningBank (Google, 2025): +3.2 SR from adding failure extraction (vs. AWM -2.2, Synapse +1.1); failure extraction produces counterfactual guardrails
- CFGM (EMNLP 2025): Compare-based tip extraction (success vs. failure trajectories) enables error-prevention tips; removing Failure Trajectories degrades performance
- CODESKILL (2026): RL with hybrid reward (including execution failures) enables OOD generalization; SFT-only degrades on Terminal-Bench 2
- HAP (NeurIPS 2025): Adversarial teacher exploits student's failure patterns to discover harder tasks; without failure-driven curriculum, learning plateaus
- GEP Evolver: Auto-distill from failures — analyze failed Capsules, synthesize repair Genes
- Designing AI Agents book: "Never triage away failure information" — Claude Code/Manus critical rule

**Consensus:** Systems that convert failures into constructive signals (ReasoningBank, CFGM, CODESKILL) outperform those that only learn from successes or treat failures as noise (AWM, Synapse). Failure signals must be structured and abstracted — raw failure trajectory injection degrades performance (Gene+failure: -2.0 pp vs Gene alone — GEP paper, Table 5).

### Convergence 4: Learning rates and bounded updates prevent semantic drift

**Evidence:**
- SkillOpt: Cosine-scheduled edit budget Lt (starts at 4, decays to 2); "textual learning rate" prevents unbounded rewrites
- EvoQuality: KL regularization (β=0.05) against frozen reference policy prevents catastrophic drift during GRPO updates
- GEP Evolver: Signal de-duplication suppresses signals appearing 3+ times in last 8 events to prevent repair loops
- CODESKILL: Three-stage curriculum (extraction → evolution → maintenance) progressively introduces operations, preventing cold-start problems
- HAP: Entropy regularization prevents teacher collapse to uniform distribution; probabilistic lower bounds prevent catastrophic forgetting
- AFlow: Soft mixed probability selection with dynamic α prevents premature convergence to local optima

**Consensus:** Self-evolving systems need explicit stability controls mapped from ML training: learning rates, momentum, early stopping, curriculum progression, and regularization. Systems without these (one-shot generation, unbounded self-revision, evolutionary loops without convergence criteria) exhibit semantic drift, mode collapse, or repair loops.

### Convergence 5: Training-free methods are viable but reachable ceiling is limited

**Evidence:**
- ReasoningBank: All prompt-based (no fine-tuning); +20.5% SR improvement; ceiling limited by prompt quality and retrieval accuracy
- CFGM: All prompt-based; +10.4 pp on AlfWorld; ceiling limited by LLM reasoning quality and retrieval sensitivity (k=5 drops 5 pp)
- Multi-Agent Debate: All inference-only; +7.05% accuracy; dead loops at >1 round — further rounds produce zero or negative gain
- SkillOpt: Training-based; +23.5 avg; outperforms all prompt-based baselines
- CODESKILL: SFT-only achieves +4.72 avg; RL adds +4.72 more; SFT-only degrades on OOD tasks
- GEP paper: Genes (control-oriented) improve; Skills (documentation-oriented) degrade — representation, not training, is the first-order factor

**Consensus:** Training-free methods (prompt engineering, retrieval, debate, reflection) provide immediate gains with minimal implementation cost. But the ceiling is lower than methods that incorporate training (RL, GRPO, fine-tuning). The pragmatic path: training-free baseline → measure ceiling → graduated to training-based only when empirical data shows meaningful improvement over ceiling.

---

## 4. Contradictions

Where do sources disagree? These need arbitration in Phase 4 plans.

### Contradiction 1: Should memory be additive-only or managed with pruning?

- **Additive-only camp:** ReasoningBank (Google, 2025) intentionally uses simple additive consolidation with NO pruning or deduplication, arguing that "if content quality is high enough, even simple retrieval+addition suffices." This isolates the effect of memory content quality from management sophistication.
- **Managed/pruning camp:** CODESKILL (NTU, 2026) shows that full lifecycle maintenance (add+merge+drop) shrinks bank by 46% (1252→676) with only ~2% pass rate cost. LLM-Wiki (Tencent, 2026) uses Error Book to prevent recurrence of known errors and auto-fix structural issues. Memory Survey (Du, 2026) identifies that "no system masters selective forgetting" and "inability to discard outdated information gradually poisons retrieval precision."
- **Arbitration needed:** The contradiction may be one of scale — additive-only suffices for short streams (hundreds of tasks) but degrades on long streams (thousands). Phase 4 plans should include an empirical comparison: additive-only baseline vs. managed (add/merge/drop) on Lyra's expected session volumes, measuring retrieval precision, latency, and token cost as memory grows.

### Contradiction 2: Is simple retrieval sufficient, or do we need learned retrieval?

- **Simple retrieval camp:** ReasoningBank uses embedding-based similarity search only and achieves +20.5% SR improvement. CFGM uses Faiss with `all-mpnet-base-v2` and achieves +10.4 pp. Both argue that content quality dominates retrieval sophistication.
- **Learned retrieval camp:** CODESKILL uses dense semantic similarity but notes it as a limitation — "skills may be retrieved that are similar in embedding space but irrelevant in the current execution context." DITS paper shows Q-values and influence scores have only ~0.1 Pearson correlation — what is "similar" in embedding space does not correspond to what is "useful" for training. SELF-RAG trains the model itself to decide whether to retrieve (adaptive retrieval gating).
- **Arbitration needed:** Simple retrieval works well when embeddings capture task semantics adequately (web navigation, QA, structured environments). Learned retrieval becomes necessary when (a) embedding similarity misaligns with training utility (DITS), or (b) retrieval should be conditional on task state (SELF-RAG). Lyra should start with simple retrieval and measure the misalignment between embedding-similarity ranking and downstream-performance ranking before investing in learned retrieval.

### Contradiction 3: Should evolution be within-session (online) or across-sessions (offline)?

- **Online/within-session camp:** ReasoningBank evolves memory during the task stream, with bidirectional MaTTS synergy. AnnaAgent (arXiv:2506.00551v2) performs turn-level dynamic state modulation with dedicated emotion/complaint agents. HAP updates teacher and student adversarially during training.
- **Offline/across-session camp:** SkillOpt runs optimization offline with pre-collected rollout batches, cross-validated on held-out data. CODESKILL runs discrete batch episodes (3-stage curriculum). GEP Evolver runs as a background daemon with adaptive sleep (2s-5min), idle scheduling, and suicide-respawn.
- **Arbitration needed:** Online evolution risks self-reinforcing error (false beliefs never challenged) and requires careful gating. Offline evolution enables validation-gated improvement but introduces cold-start delay. The CODESKILL curriculum (extraction → evolution → maintenance) and SkillOpt's epoch-based slow update provide a template: within-session memory extraction (lightweight, inference-only), across-session consolidation and validation (gated, with RL). Lyra should implement both layers.

### Contradiction 4: Larger rollout batches vs. iterative mini-batches for evolution data

- **Larger batches camp:** AFlow uses 5 evaluations per iteration. SWE-Search uses max 100 iterations, 3 expansions/node. Larger batches reduce noise but increase cost.
- **Iterative mini-batches camp:** DITS shows 3 iterations of synthesis + training provide larger gains than 16x raw synthesis budget increase. CODESKILL uses group size 6 in GRPO. SkillOpt uses default batch B=40 but minibatch Bm=8 for reflection — "singletrajectory analysis produces anecdotal fixes, while minibatches expose reusable procedural errors."
- **Arbitration needed:** The SkillOpt finding that minibatches (Bm=8) surface reusable patterns is directly actionable. Phase 4 plans should use iterative small-batch evolution (collect 8-40 trajectories, reflect, update, repeat) rather than collecting large batches before any update.

### Contradiction 5: Does multi-agent composition help or hurt self-evolution?

- **Helps camp:** CFGM (EMNLP 2025): Multi-agent (Planner, Thought, Execution, Reflection) achieves 14-17 pp gains over single-agent GraphRAG. AgenticEval: Specialist + Generator + Evaluator + Analyst achieves 36.14 pp more vulnerability discovery. ChemAmp: Composing 2 tools hierarchically achieves SOTA.
- **Hurts camp:** GEP paper: Two complementary genes drop to 44.9% (-6.1 pp vs. no-guidance) — complementarity is more harmful than conflict. Multi-Agent Debate: Self-Reflect+Debate degrades individual accuracy in 14/21 settings. Designing AI Agents book: "Poorly orchestrated teams show up to 17.2x error amplification" (DeepMind finding).
- **Arbitration needed:** The pattern is consistent: multi-agent composition helps when agents have complementary capabilities and clear role boundaries (CFGM, AgenticEval, ChemAmp). It hurts when agents compete for the same attention budget or when composition produces ambiguity rather than diversity (GEP complementary genes, Self-Reflect+Debate). Lyra's Phase 4 plans must include ablations measuring: does adding an agent role improve or degrade downstream task completion? The default should be fewer agents, not more.

---

## 5. Open Problems

What problems does NO source solve yet? These are research opportunities.

### Open Problem 1: Selective forgetting and memory lifecycle management

**Status:** MemoryAgentBench [Hu et al., 2025] shows **no current system masters selective forgetting**. Current approaches are crude: hard time-based expiration, storage-limit eviction, or nothing. CODESKILL's maintenance (add/merge/drop) is the closest to a systematic solution but still relies on simple similarity heuristics, not principled forgetting. LLM-Wiki's Error Book tracks and fixes errors but does not address what to forget.

**Why it matters:** As agent lifespans extend (days → weeks → months), memory banks accumulate noise, contradictions, and stale information. Without selective forgetting, retrieval precision degrades and self-reinforcing errors compound.

**Prize:** A system that can (a) detect when a memory has been superseded by contradictory evidence, (b) identify when a memory encodes a pattern that no longer generalizes, (c) prune memories without performance regression, and (d) do this without ground-truth labels.

### Open Problem 2: Cross-domain evolution transfer

**Status:** SkillOpt shows positive transfer across models, harnesses, and benchmarks (SpreadsheetBench skill from Codex→Claude Code: +59.7). CODESKILL shows policy transfer from Qwen3.5 → GPT-5.4-mini (+8.93). But no system demonstrates transfer of entire evolution processes across fundamentally different domains (e.g., coding → dialogue → planning).

**Why it matters:** The dream of "learn once, deploy everywhere" is currently "optimize per domain, reuse if lucky." For Lyra to be a general agent, evolution that works in one domain must transfer to others.

### Open Problem 3: Multi-gene/strategy composition without collapse

**Status:** GEP paper shows catastrophic collapse with two complementary genes (44.9%, -6.1 pp vs. no-guidance). CODESKILL shows multi-granularity banks help (event-driven + task-level are complementary) but composition is implicit (similarity retrieval) not explicit. No paper solves the problem of how to compose multiple evolution products at test time without mutual interference.

**Why it matters:** Real agents accumulate hundreds of strategies over their lifetime. If composing more than 2 strategies degrades performance, the entire self-evolution pipeline is bounded by a strategy count ceiling that makes it useless at scale.

### Open Problem 4: Detecting and recovering from self-reinforcing errors

**Status:** Memory Survey (Du, 2026) identifies this as a central failure mode: "If the agent incorrectly concludes 'approach A always fails,' it avoids that path forever, never collecting disconfirming evidence. Severity scales with agent lifetime — catastrophic in long-running production agents." ReasoningBank's LLM-as-a-Judge achieves only 72.7% accuracy — systematic biases propagate into memory. No paper proposes a mechanism for detecting or recovering from these frozen false beliefs.

**Why it matters:** Self-reinforcing errors are not occasional glitches — they are the expected steady state of any system that learns from its own outputs without external correction. Lyna must be designed with the assumption that self-reinforcing errors WILL occur and require active remediation.

### Open Problem 5: Cost-efficient evolution at scale

**Status:** SWE-Search costs 5-14x more than single-pass inference. AFlow requires 100 evaluations per search. SkillOpt requires 20-214M training tokens. CODESKILL requires ~230 GPU-hours. Even ReasoningBank (cheapest technique) adds 4.3% token overhead. No paper proposes a budget-aware evolution strategy that allocates optimization compute proportionally to expected gain.

**Why it matters:** For production agents processing thousands of requests daily, a 5-14x cost multiplier for self-evolution is economically nonviable. Systematic cost-benefit analysis of evolution compute is entirely absent from the literature.

### Open Problem 6: Adversarial robustness of self-evolved artifacts

**Status:** AgenticEval shows self-evolution can discover vulnerabilities (36.14 pp more failures), but no paper tests whether evolved genes/memories/skills can themselves be poisoned. If an adversary can inject data that causes the evolution loop to learn a harmful strategy, the entire self-improvement pipeline becomes a liability. GEP Evolver has a comprehensive security model (command whitelisting, protected critical files) but only for the evolution infrastructure, not the evolved content.

### Open Problem 7: Multi-session coherence and long-horizon consistency

**Status:** MemoryArena [He et al., 2026]: "Models scoring near-perfectly on LoCoMo plummet to 40-60% in MemoryArena" — the gap between passive recall and active decision-relevant memory use. AnnaAgent implements tertiary memory but authors note it is "rudimentary." No system maintains consistent knowledge and behavior across sessions separated by hours/days without degradation.

---

## 6. Recommendations for Lyra

Ranked by expected impact-to-effort ratio, evidence strength, and architectural fit with Lyra's existing subsystems.

### Recommendation 1 (TIER: BREAKTHROUGH — DO FIRST): Dual-Source Memory Extraction with LLM-as-a-Judge

**Adopt:** ReasoningBank's 3-field memory schema (title + description + content) with separate success/failure extraction prompts + LLM-as-a-Judge binary classification.

**Why first:** This is the simplest technique (prompt engineering + embedding DB), has the strongest evidence (+20.5% SR, 3 model families, 4.3% overhead), maps directly to Lyra's existing session traces, and provides the foundation for all other self-evolution techniques. Without a memory substrate, higher-order evolution (genes, skills, MCTS) has nothing to operate on.

**Implementation path:**
1. Add post-session success/failure classification to Lyra's session pipeline
2. Implement 3-field extraction (success: "why did it work?"; failure: "why did it fail, what to avoid?")
3. Store in existing vector DB with metadata (timestamp, session ID, task label)
4. Add top-k retrieval injection to Lyra's system prompt
5. Log all memory operations (writes, reads, retrieval queries) for observability

**Sources:** ReasoningBank (Google, 2025); CFGM (EMNLP 2025); Memory Survey (Du, 2026)

### Recommendation 2 (TIER: BREAKTHROUGH): GEP-Style Structured Experience Encoding

**Adopt:** Compact, structured strategy objects replacing Lyra's documentation-heavy skill files. Schema: `{matching_signals, summary, strategy_steps, AVOID_cues, constraints, validation_hooks}` at ~200-300 tokens.

**Why second:** The GEP paper's core finding — that compact control objects (+3.0 pp) outperform verbose documentation (-1.1 pp) — is directly actionable and challenges Lyra's current approach. The 10x token reduction aligns with Lyra's context budget goals. Implementation does not require a full evolution pipeline — start with the representation, then add evolution.

**Implementation path:**
1. Design Lyra-specific gene schema (signals, summary, strategy, AVOID, constraints)
2. Write distillation prompts that convert Lyra's existing skill.md files to gene format
3. Run A/B test: existing skills vs. genes on Lyra's benchmark suite
4. If genes outperform, build SCAN→SIGNAL→MUTATE→VALIDATE loop adapted from GEP spec

**Sources:** GEP/skill2gep paper (EvoMap, 2026, 4,590 trials); SkillOpt paper (Microsoft, 2026); CODESKILL paper (NTU, 2026)

### Recommendation 3 (TIER: BREAKTHROUGH): Validation-Gated Skill/Prompt Optimization

**Adopt:** SkillOpt's bounded-edit-with-validation-gate pattern for Lyra's system prompt and tool-use policy documents.

**Why third:** After establishing the memory substrate (#1) and structured representation (#2), add systematic optimization. SkillOpt's +23.5 avg gain and cross-harness transfer (+59.7) make it the highest-impact technique in the survey. The bounded-edit approach is auditable and safe. CODESKILL's RL extension adds OOD generalization but requires ~230 GPU-hours — start with SkillOpt's SFT-based approach and graduate to RL only when SFT ceiling is measured.

**Implementation path:**
1. Split Lyra's evaluation benchmarks into D_train (rollout evidence), D_sel (validation gate), D_test (final reporting)
2. Implement optimizer loop: rollout batching → minibatch reflection (Bm=8) → hierarchical merge → bounded-edit clipping (Lt=4 cosine schedule) → validation gate (strict)
3. Run initial optimization on Lyra's tool-use policies and output format constraints
4. Measure gain; if ceiling is visible, graduate to CODESKILL-style RL with GRPO + hybrid reward

**Sources:** SkillOpt paper (Microsoft, 2026); CODESKILL paper (NTU, 2026); CaTS paper (ICLR 2026) for confidence-based resource allocation

### Recommendation 4 (TIER: INVESTIGATE): Evolutionary Outer Loop for High-Value Operations

**Adopt:** AlphaEvolve-style evolutionary refinement (generate N candidates → evaluate automatically → feed fittest back) for Lyra's high-stakes code generation and planning tasks.

**Why investigate (not breakthrough):** AlphaEvolve is production-proven at Google (0.7% compute recovery, 23% kernel speedup) but requires domain-specific automated evaluators. The 5-14x cost multiplier (SWE-Search) means this should be reserved for tasks where correctness premium justifies compute premium. Lyra's existing test suite and linter infrastructure provide the evaluator foundation.

**Implementation path:**
1. For non-trivial code tasks, generate 3-5 candidate implementations in parallel
2. Run each through Lyra's test suite + static analysis
3. Select best candidate(s) as context for a refinement pass
4. Repeat until convergence or budget exhaustion
5. Add CaTS-style self-calibrated confidence to decide how many refinement rounds to allocate per task

**Sources:** AlphaEvolve (Google DeepMind, 2025); ChemAmp (Fudan University, 2026); SWE-Search (ICLR 2025); CaTS (ICLR 2026)

### Recommendation 5 (TIER: INVESTIGATE): Self-Consistency Voting for Lyra's Evaluator Training

**Adopt:** EvoQuality's pairwise ranking + majority voting for pseudo-label generation, applied to Lyra's response quality evaluation and hallucination detection subsystems.

**Why investigate:** EvoQuality's +31.8% gain without ground-truth labels is compelling, but the technique is validated only on perceptual tasks (image quality assessment). Transfer to Lyra's domains (code quality ranking, response correctness scoring) is unproven. The K=32 sampling budget is expensive but could be run offline.

**Implementation path:**
1. Prototype on Lyra's code-review quality scoring: prompt Lyra K=32 times to rank 2 candidate code reviews
2. Compute pairwise pseudo-labels via majority voting
3. Train a fidelity reward using GRPO with KL regularization
4. Measure whether self-consistency voting improves alignment with human judgments

**Sources:** EvoQuality (ICLR 2026); CaTS (ICLR 2026); AgenticEval (Fudan, 2026)

### Recommendation 6 (TIER: ARCHITECTURAL PRINCIPLE): Observability-First Evolution Infrastructure

**Adopt:** The memory operation observability pattern from Memory Survey (Du, 2026) and the audit trail pattern from GEP Evolver.

**Why architectural:** Self-evolving systems silently fail in production. The Memory Survey's central argument — "memory operation logging, replay tools, and memory diff diagnostics are the primary reason demo-stage systems fail in production" — applies to all self-evolution, not just memory. Every evolution operation must be logged with timestamp, triggering context, before/after state, and outcome.

**Implementation path:**
1. Log every memory write, skill update, prompt modification, and gene evolution with full audit trail
2. Implement "evolution diffs" between cycles for debugging
3. Add git-backed rollback for any evolution-triggered file change (adapting from GEP Evolver's gitOps)
4. Build a replay/debug tool that can reconstruct the system state at any past evolution point

**Sources:** Memory Survey (Du, 2026); GEP Evolver (EvoMap, 2026); Designing AI Agents book (Manning, 2026, Chapter 2)

### Recommendation 7 (DO NOT ADOPT — RISK FLAGGED): Unbounded Evolutionary Loops Without Validation Gates

Several papers describe evolutionary approaches with unbounded generation, no validation gate, or weak selection criteria. These techniques are flagged as risks for Lyra adoption:

- **Raw self-reflection** (without external verification): Designing AI Agents book and GEP paper both document that single-model self-reflection suffers from confirmation bias and can produce "dead loops" (Multi-Agent Debate, Figure 2). Reflexion's +11 pp gain on HumanEval is real but ceiling-limited.
- **Random/unbounded prompt mutation** (without bounded edit budget): SkillOpt's ablation shows unbounded rewrites erase useful rules. GEP paper shows naively appending failure history dilutes genes by -2.0 pp.
- **Fully autonomous end-to-end research generation** (without phase-boundary verification): Auto-Research survey catalogs 80% fabrication rate in autonomous results, 58.6% semantic error rate in research code, and 95.8% rejection misclassification by AI reviewers. The lifecycle framework (verify at every phase boundary) is the paper's central recommendation.
- **Multi-agent debate without judge arbitration**: Multi-Agent Debate paper shows agents disagree in ~56% of initial decisions; without a judge, accuracy plateaus at ~60%. With a judge, accuracy reaches ~76%.

---

## Appendix: Source Index

### Papers (24 cited)

| ID | Title | Venue | Key Finding |
|----|-------|-------|-------------|
| 2605.23904v2 | SkillOpt: Executive Strategy for Self-Evolving Agent Skills | arXiv, Microsoft, May 2026 | +23.5 avg gain; 52/52 dominance; bounded edit budget |
| 2604.15097v2 | From Procedural Skills to Strategy Genes | arXiv, EvoMap/Tsinghua, June 2026 | Genes +3.0 pp vs Skills -1.1 pp; 4,590 trials |
| 2509.25140v2 | ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory | arXiv, Google, 2025 | +20.5% SR; 4.3% overhead; dual success/failure extraction |
| 2410.10762v4 | AFlow: Automating Agentic Workflow Generation | arXiv, MetaGPT, 2025 | +5.7% avg; MCTS over code-represented workflows |
| 2410.20285v6 | SWE-Search: Enhancing Software Agents with MCTS and Iterative Refinement | ICLR 2025 | +23% rel.; hybrid value function with hindsight feedback |
| 2502.00955v2 | DITS: Efficient Multi-Agent System Training with Data Influence-Oriented Tree Search | arXiv, CMU/USTC, 2026 | +2.5% avg; influence scores beat Q-values; 46% less GPU cost |
| 2509.25787v4 | EvoQuality: Self-Evolving VLMs for Image Quality Assessment | ICLR 2026 | +31.8% avg without ground-truth; ranking-based beats regression |
| 2605.25430v1 | CODESKILL: Learning Self-Evolving Skills for Coding Agents | arXiv, NTU, May 2026 | +32.8% rel. pass rate; RL-trained skill mgmt policy; 230 GPU-hrs |
| 2508.15305v2 | CFGM: Coarse-to-Fine Grounded Memory for LLM Agent Planning | EMNLP 2025 | +10.4 pp AlfWorld; 3-stage coarse-to-fine memory grounding |
| 2603.07670v1 | Memory for Autonomous LLM Agents | arXiv, March 2026 | POMDP formalization; write-manage-read loop; Pattern B recommendation |
| 2310.11511v1 | SELF-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | arXiv, UW/AI2/IBM, 2023 | Adaptive retrieval gating; 7B beats ChatGPT on 4/6 tasks |
| 2510.18407v1 | HAP: Heterogeneous Adversarial Play | NeurIPS 2025 | Adversarial curriculum; 85% human on Crafter; 30% gap narrowing |
| 2605.18661v1 | AI for Auto-Research: Roadmap & User Guide | arXiv, May 2026 | 4-phase lifecycle; 80% fabrication rate; verify-at-boundaries |
| 8078 | CaTS: Calibrated Test-Time Scaling | ICLR 2026 | 94.2% sample savings; self-calibrated confidence; LoRA fine-tuning |
| 2605.25480v2 | LLM-Wiki: Retrieval as Reasoning | arXiv, Tencent, May 2026 | +8.1 F1 MuSiQue; compile-once traverse-many; Error Book self-evolution |
| 2509.26100v2 | AgenticEval: Self-Evolving Safety Evaluation | arXiv, Fudan, 2026 | 36.14 pp more failures discovered; 88-91% human agreement |
| 2505.24671v2 | Multi-LLM Agents Debate for Equitable Cultural Alignment | arXiv, UMD, 2025 | +7.05% accuracy; 7-9B pairs match 27B; single round optimal |
| 2506.00551v2 | AnnaAgent: Dynamic Evolution Agent System | arXiv, NEU, 2025 | Tertiary memory; dynamic state modulation; turn-level evolution |
| 2605.21569v3 | ChemAmp: Amplified Chemistry Tools via Composable Agents | arXiv, Fudan, 2026 | 94% token reduction; tool amplification > orchestration |
| 2506.03939v1 | Graph Counselor: Adaptive Graph Exploration | arXiv, Shanghai AI Lab, 2025 | 9B+GC beats 70B+Graph-CoT by 10%+; multi-agent Plan→Thought→Execute |
| 2505.21569v3 | ChemAmp | arXiv, Fudan, 2026 | SOTA 4 chemistry 0-shot; bi-phase tool amplification |
| 2507.06908v1 | MI N D: Multi-agent Harmful Meme Detection | arXiv, BUPT, 2025 | Bidirectional insight derivation; debate+judge arbitration; training-free |
| 2502.13886v1 | Fill-Tuning: Refining Embeddings with Fill-Tuning | arXiv, IBM, 2025 | 100-point targeted pretraining; +0.75% avg; roughness-guided data selection |
| 2604.15097v2 | GEP/skill2gep (duplicate entry for completeness) | — | — |

### Books (2 cited)

| Title | Author/Publisher | Year | Key Contribution |
|-------|-----------------|------|-----------------|
| Designing AI Agents | Manning Publications (MEAP V01) | 2026 | "Harness engineering" philosophy; 27 named patterns; "never triage away failure information" |
| Architecting Generative AI Applications | (playbook) | 2026 | Self-evolving agent pattern recognition |

### Web Repos (4 cited)

| Repo | Source | Key Contribution |
|------|--------|-----------------|
| EvoMap/evolver | npm package + arXiv paper | Production daemon; GEP protocol implementation; SCAN→SOLIDIFY loop |
| EvoMap/awesome-agent-evolution | GitHub awesome-list | 80+ curated self-evolution projects across 9 categories |
| EvoMap/skill2gep | GitHub + arXiv paper | Gene representation specification; 4,590-trial experiment |
| AlphaEvolve (Google DeepMind Blog) | Blog post, May 2025 | Production evolutionary algorithm at Google; 0.7% compute recovery |
