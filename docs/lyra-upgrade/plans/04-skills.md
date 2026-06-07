# Skills System — Plan (§4.4)

> Run 3, 2026-06-03 | Enhanced with deep-read evidence 2026-06-07

## Plain-Language Summary

Lyra's skills system loads markdown skill files from the filesystem using progressive disclosure (metadata first, body on selection, resources on demand). It auto-generates skill packages from GitHub repos, PDFs, and conversation logs, organizes them into a similarity/composition/dependency graph, rates them on 5 quality dimensions, and optimizes them via validation-gated text optimization (SkillOpt) or gradient-free prompt evolution (GEPA, TF-TTCL). Works across ALL providers — the loader is harness-level, not API-level. The system additionally supports (a) compact "strategy gene" representations for test-time control where documentation-heavy skills degrade performance, (b) a learned skill-management policy (CODESKILL) for automated bank maintenance, (c) anti-rationalization tables to prevent agents from skipping verification steps, and (d) a GEP protocol for auditable, git-integrated evolution.

## Evidence Synthesis

### Core Technique Papers

| Source | Key Insight | Evidence |
|--------|------------|----------|
| SkillNet (arXiv:2603.04448v1, Feb 2026) | Full-lifecycle skill infra: auto-create from 4 sources (trajectories, GitHub repos, PDFs, prompts), 5-D quality scoring (Safety, Completeness, Executability, Maintainability, Cost-awareness), typed relation graph (similar_to, belong_to, compose_with, depend_on) | **+40% avg reward** improvement across 3 benchmarks (ALFWorld, WebShop, ScienceWorld); **~30% reduction in interaction steps** vs. ReAct; Gemini-2.5-Pro + SkillNet: 91.43 reward on ALFWorld (vs. 60.00 ReAct); evaluator MAE < 0.03 vs. 3 PhD annotators; QWK at near-perfect 1.000 |
| SkillOpt (arXiv:2605.23904v2, Microsoft Research, May 2026) | Validation-gated text optimization: stronger optimizer model proposes bounded add/delete/replace edits under cosine-scheduled edit budget Lt (4 to 2); held-out validation gate accepts edits only on strict improvement; rejected-edit buffer + epoch-wise slow/meta update | **52/52 cells best or tied-best** vs. all baselines (GEPA, Trace2Skill, EvoSkill); **+23.5 avg gain** on GPT-5.5 across 6 benchmarks (SearchQA +9.6, SpreadsheetBench +38.9, OfficeQA +39.0, DocVQA +12.4, LiveMath +29.3, ALFWorld +11.9); **+17.6 avg across 7 models** (GPT-5.5 through Qwen3.5-4B); cross-harness transfer: SpreadsheetBench skill Codex to Claude Code yields **+59.7 points** |
| GEP / skill2gep (arXiv:2604.15097v2, EvoMap/Tsinghua, June 2026) | Compact Strategy Genes (~230 tokens, structured `{signals, summary, strategy, AVOID, constraints, validation}`) outperform documentation-heavy Skills (~2,500 tokens). 6-stage GEP loop: SCAN -> SIGNAL -> INTENT -> MUTATE -> VALIDATE -> SOLIDIFY. Three-layer object hierarchy: Genes, Capsules, Events | **Genes +3.0 pp vs. Skills -1.1 pp** over no-guidance at 10x fewer tokens; Skill-Overview alone: **-4.7 pp** (most docs are harmful); failure warnings as compact signals +4.6 pp; structured beats flattened prose by +3.5 pp; **4,590 trials** across 45 scenarios; CritPt benchmark 9.1% to 27.14% via gene evolution |
| CODESKILL (arXiv:2605.25430v1, NTU, May 2026) | RL-learned skill-management policy (Qwen3.5-4B with GRPO + LoRA) decides what to extract, evolve, merge, or drop. Hybrid reward: R = lambda*R_Q + R_A*R_E. Three-stage curriculum: extraction -> evolution -> maintenance | **+32.8% relative pass rate** over no-skill (29.57 to 39.26 avg success); **+11.4% over strongest prompt-based baseline**; 46% bank size reduction (1252 to 676) with only ~2% pass rate cost; RL enables OOD generalization on Terminal-Bench 2 while SFT-only degrades; **230 GPU-hours** training; policy transfers to GPT-5.4-mini coding agent |
| TF-TTCL (arXiv:2604.13552v1, SCUT, Apr 2026) | Training-free "Explore-Reflect-Steer" loop: multi-agent role-playing (TEACHER/TUTOR/STUDENT) generates candidates, contrastive experience distillation extracts positive + negative rules, retrieved into context as semantic anchors. Experience Rule Repository R persisting across queries | **+5.86 avg absolute gain** on Llama-3.1-8B across 4 math benchmarks (AIME24: 3.33 to 13.33, 4x improvement); **+26.7% on open-ended tasks** (Finance ROUGE-L: 0.2251 to 0.2863); works on black-box APIs (Qwen-Plus, DeepSeek-V3.2); pruning caps latency at 2.01x single call |

### Skill Representation & Quality

| Source | Key Insight | Evidence |
|--------|------------|----------|
| SkillNet (2603.04448v1) | 5-D evaluation rubric: Safety, Completeness, Executability, Maintainability, Cost-awareness | MAE < 0.03 vs. 3 PhD annotators; QWK 1.000; 200-skill blind sample |
| GEP/skill2gep (2604.15097v2) | Structured control-oriented representation beats flat documentation at 10x fewer tokens | Genes +3.0 pp; flattened prose -0.5 pp; Skill-Overview -4.7 pp; Skill-Workflow +1.5 pp |
| SkillOpt (2605.23904v2) | Cosine-scheduled edit budget prevents unbounded rewrites | Median final skill: 920 tokens; 1-4 accepted edits reach deployment; removing slow/meta update causes 22.5-point drop on SpreadsheetBench |
| CODESKILL (2605.25430v1) | Multi-granularity bank: task-level + event-driven skills; maintenance (add/merge/drop) | Event-driven only 34.51; task-level only 32.35; full lifecycle 39.26 with 46% bank reduction |
| SELF-RAG (2310.11511v1, UW/AI2/IBM, 2023) | Adaptive retrieval gating: train model to decide WHEN to retrieve | 7B beats ChatGPT on 4/6 tasks; PopQA: 24.7 (always-retrieve) to 54.9 (adaptive); segment-level beam search B=2 |

### Evolution & Learning Methods

| Source | Key Insight | Evidence |
|--------|------------|----------|
| ReasoningBank (arXiv:2509.25140v2, Google, 2025) | Dual-source memory extraction from successes AND failures; 3-field schema (title + description + content) | **+20.5% relative SR** improvement over No Memory on WebArena; +20% on SWE-Bench-Verified (34.2 to 38.8); 4.3% token overhead vs. 15-17% for Synapse/AWM; failure learning +3.2 SR (vs. AWM -2.2) |
| GEPA (ICLR 2026 Oral) | Gradient-free prompt evolution; works on any provider | Outperforms GRPO; no gradient access needed |
| EvoQuality (arXiv:2509.25787v4, ICLR 2026) | Self-consistency voting (K=32) for pseudo-label RL; pairwise ranking (Thurstone model via Gaussian CDF) beats regression | **+31.8% WAVG PLCC** across 8 IQA benchmarks; outperforms ALL supervised VLM models on OOD (0.762 vs 0.704) without labels |
| AFlow (arXiv:2410.10762v4, MetaGPT, 2025) | MCTS over code-represented agent workflows (Python classes) | **+5.7% avg improvement** over human-designed SOTA; GPT-4o-mini + AFlow outperforms GPT-4o at 4.55% inference cost |
| SWE-Search (arXiv:2410.20285v6, ICLR 2025) | MCTS + hybrid value function (scalar reward + NL critique for hindsight feedback) | **+23% mean relative improvement** across 5 models (GPT-4o: 25.7% to 31.0%); 5-14x API cost multiplier |
| AlphaEvolve (Google DeepMind Blog, May 2025) | Evolutionary outer loop: generate N candidates, evaluate automatically, feed fittest back | **~0.7% of Google's worldwide compute resources** recovered; 23% speedup on Gemini training kernel; 32.5% speedup on FlashAttention; production deployed 1+ year |

### Production Skill Infrastructure

| Source | Key Insight | Evidence |
|--------|------------|----------|
| alirezarezvani/claude-skills (GitHub) | 343 skills, 593 stdlib Python tools, 691+ reference docs, 64 plugins, 90+ commands; cross-compiled to 13 platforms | 9-phase pipeline (Intent -> Research -> Draft -> Eval -> Iterate -> Compliance -> Package -> Deploy -> Verify); Tessl quality gate min 85%; evals >= 85% pass rate, delta >= +30%; audit scores 79-91/100 |
| addyosani/agent-skills (GitHub) | 23 progressive-disclosure skills; anti-rationalization tables; 3-layered (skills/personas/commands); SDD cache hooks (ETag/304 revalidation) | ~280 mean lines per skill; 6500 total lines; session-start hook injects meta-skill as decision tree; forcing-question discipline prevents vague-input runs |
| EvoMap/evolver (npm, GitHub) | Production GEP daemon with singleton lock (atomic link(2)), adaptive sleep (2s-5min), suicide-respawn, 45min cycle timeout, 500MB RSS cap | 4,590 controlled trials; CritPt 9.1% to 27.14% lift; signal de-duplication suppresses 3+ appearances in last 8 events; git stash rollback; blast radius cap 60 files/20k lines |

## Trade-off Analysis

### Representation Format Trade-offs

| Format | Size | Performance | When to Use |
|--------|------|-------------|-------------|
| Documentation Skill (~2,500 tokens) | High | -1.1 pp (degrades) | Never — GEP paper shows systematic degradation. Exception: Skill-Workflow section alone (+1.5 pp) |
| Strategy Gene (~230 tokens) | Very Low | +3.0 pp | Default representation for all new Lyra skills; structured `{signals, strategy, AVOID, constraints}` |
| Fail-Only Warnings (~100 tokens) | Minimal | +4.6 pp | Best for reactive/failure-based guidance; highest per-token impact |
| SkillOpt artifact (379-1,995 tokens) | Low-Medium | +23.5 avg (GPT-5.5) | Production deployments after offline optimization; higher impact but requires training run |
| CODESKILL bank (676 skills) | Variable | +32.8% relative | Scenarios with many heterogeneous tasks; requires RL training pipeline |

### Evolution Method Trade-offs

| Method | Training Cost | Inference Overhead | Lift | Best For |
|--------|-------------|-------------------|------|----------|
| SkillOpt (bounded edits) | 20-214M tokens (one-time) | Zero (static .md) | +17.6-23.5 avg | Domains with scored trajectories + automatic verifiers |
| GEP (gene evolution) | ~$0.81/run | Zero (230 tokens) | +3.0 pp avg | Budget-constrained, no-training-needed scenarios |
| CODESKILL (RL policy) | ~230 GPU-hours | Retrieval latency | +32.8% relative | Long-running agents with many heterogeneous task types |
| ReasoningBank (extraction) | 4.3% token overhead | Retrieval latency | +20.5% relative | Simplest deployable option; immediate gains with embedding DB |
| TF-TTCL (contrastive rules) | Zero (training-free) | 2.01x single-call latency | +5.86 abs | Black-box API models; open-ended tasks without verifiers |
| AlphaEvolve (evolution loop) | N x generation cost | Zero (final artifact) | ~20-32% speedup | High-stakes code/planning tasks with automated evaluators |

### Composition Trade-offs

- **GEP finding (critical):** Two complementary genes drop to 44.9% (-6.1 pp vs. no-guidance) — complementary composition is more harmful than conflicting composition. Multi-gene composition is unsolved.
- **CODESKILL finding:** Full lifecycle maintenance (add/merge/drop) shrinks bank 46% with only ~2% pass rate cost — maintenance controls unbounded growth without catastrophic degradation.
- **SkillNet finding:** Typed ontology (similar_to, compose_with, depend_on) enables agents to navigate skill dependencies and alternatives. Missing ablation comparing graph-informed vs. flat semantic retrieval — gain from relation typing not isolated.
- **addyosani finding:** Anti-rationalization tables prevent agents from skipping steps. The dual-persons parallel fan-out (/ship) demonstrates a safe multi-agent composition pattern.
- **Multi-agent debate (UMD, 2025):** +7.05% accuracy; 7-9B model pairs match 27B model. Single round sufficient — dead loops at >1 round. Self-Reflect+Debate degrades individual accuracy in 14/21 settings.

### Key Ablations to Watch

| Ablation | Effect | Source |
|----------|--------|--------|
| Remove slow/meta update from SkillOpt | -22.5 points on SpreadsheetBench (catastrophic) | SkillOpt Table 3 |
| SFT-only without RL in CODESKILL | +4.72 avg vs. RL +4.72 avg; Terminal-Bench 2 degrades vs. no-skill | CODESKILL §2.3 |
| Remove rejected-edit buffer from SkillOpt | -1.6 to -4.6 points depending on benchmark | SkillOpt Table 3 |
| Unbounded rewrites (no edit budget) | SkillOpt ablation shows erasure of useful rules | SkillOpt §3.4 |
| Complementary multi-gene composition | -6.1 pp vs. no-guidance (worst result) | GEP Table 4 |
| Remove validation gate from any evolution method | Semantic drift, mode collapse, repair loops | Convergence 1 (§4 synthesis doc) |

## Proposed Lyra Design

### (A) Parity — Harness-Level Skills Loader

1. **Progressive disclosure loader (grounding: addyosani/agent-skills session-start hook; SkillNet 3-phase lifecycle):**
   - Level 1: YAML frontmatter (name + description + tags + trigger keywords) -> pre-loaded at session start in a compact meta-skill index (~200t for the index)
   - Level 2: SKILL.md body -> loaded on invocation when the meta-skill decision tree matches
   - Level 3: referenced files (scripts, references, assets, sub-agent definitions) -> loaded on demand via sibling-directory convention

2. **Provider-agnostic injection (grounding: SkillNet OpenClaw integration patterns):** Read SKILL.md from filesystem, inject into messages array. Never depend on provider-specific "skills" endpoint. Strip/translate Claude-only frontmatter fields (model: pin, dynamic-injection extensions) for non-Claude providers. Use addyosani's cross-tool conversion pattern: single SKILL.md, compile to 13 tool-native formats.

3. **Skill selection (grounding: SkillNet 3-phase lifecycle; SELF-RAG adaptive retrieval):**
   - Deterministic keyword/embedding match as fallback for providers with unreliable auto-trigger
   - Per-provider trigger strategy (Claude: auto-trigger, DeepSeek: keyword-based deterministic)
   - Consider SELF-RAG's adaptive retrieval gating (soft constraint delta=0.2) as future upgrade: train Lyra to decide WHEN to search for a skill vs. proceed without

4. **Forcing-question discipline (grounding: addyosani/agent-skills Matt Pocock pattern; claude-skills pipeline):** Before executing any skill, Lyra must ask 1-2 clarifying questions with recommended answer options. Prevents running on vague input. Estimated 50-80 token cost per skill execution.

5. **Bundled starter skills (grounding: claude-skills 8 POWERFUL skills; addyosani 23 lifecycle skills):** Port 8-10 vetted skills from superpowers/oh-my-claude/claude-skills: code-review, debug, tdd, plan, verify, loop, brainstorm, deep-research. Each starter skill includes an anti-rationalization table (4-6 rows) at ~60 token cost.

### (B) Breakthrough — SkillNet Graph + Validation-Gated Evolution

6. **SkillNet graph (grounding: SkillNet 2603.04448v1, typed 3-layer ontology):**
   - Similarity/composition/dependency edges between skills
   - Three-layer: Skill Taxonomy (category->tag), Skill Relation Graph (similar_to, belong_to, compose_with, depend_on), Skill Package Library (packaged_in)
   - Auto-generated from GitHub/PDFs/trajectories via 5-stage pipeline: deduplication (MD5 + dir structure) -> filtering (rule + LLM quality) -> categorization (10 functional categories + semantic tags) -> 5-D evaluation -> consolidation (ontology relation inference)
   - **"Install skill X and get Y, Z recommended"** via compose_with and belong_to edges
   - LLM-driven graph construction with implicit risk of hallucinated relations — need periodic manual spot-checking

7. **5-D quality scoring (grounding: SkillNet 5-D rubric, MAE < 0.03):**
   - Safety: prompt injection resistance, hazardous operation detection, adversarial manipulation resistance
   - Completeness: critical procedural steps, prerequisites, dependencies, execution constraints
   - Executability: sandbox-validated execution success; detects hallucinated tool calls, ambiguous instructions
   - Maintainability: modularity and composability; local updates don't disrupt global dependencies
   - Cost-awareness: execution overhead (time latency, compute, API usage)
   - Implementation: LLM-based scoring against fine-grained rubrics, calibrated with human annotator MAE target < 0.03 (per SkillNet methodology)

8. **GEP strategy gene canonicalization (grounding: GEP/skill2gep 2604.15097v2):**
   - ADD: Convert existing Lyra skill .md files to compact gene representations: `{matching_signals, one-sentence_summary, strategic_steps, AVOID_cues, constraints, validation_hooks}` at ~200-300 tokens
   - ADD: Run A/B test: existing skills vs. genes on Lyra's benchmark suite
   - **CRITICAL GEP FINDING:** If A/B test confirms GEP results (genes +3.0 pp, skills -1.1 pp), deprecate documentation-heavy skills in favor of genes
   - **RISK: multi-gene composition unsolved.** GEP shows two complementary genes degrade to 44.9% (-6.1 pp vs. no-guidance). Lyra must start with single-gene-per-task and measure composition degradation before deploying multi-gene agents.

9. **Validation-gated skill optimization (grounding: SkillOpt 2605.23904v2):**
   - Implement SkillOpt's optimizer loop: rollout batching (B=40) -> minibatch reflection (Bm=8) -> hierarchical merge -> bounded-edit clipping (Lt=4 cosine schedule) -> held-out validation gate (strict, ties rejected)
   - ADD: Rejected-edit buffer for negative feedback without inference-time cost
   - ADD: Epoch-wise slow/meta update in protected section (`<!-- SLOW_UPDATE_START -->`)
   - Cross-harness transfer validated: SpreadsheetBench skill Codex to Claude Code yields +59.7 points above baseline
   - Training cost: 20-214M tokens per skill (one-time); deployment overhead: zero
   - Use GPT-5.5 as optimizer model for Lyra's target models (separation of concerns per SkillOpt §6)

10. **Learned skill management policy (grounding: CODESKILL 2605.25430v1):**
    - After SkillOpt ceiling measured, graduate to CODESKILL-style RL with GRPO + hybrid reward
    - Multi-granularity bank: task-level (high-level strategies) + event-driven (local guidance for recurring patterns)
    - Hybrid reward: R = lambda*R_Q + R_A*R_E — rubric quality, alignment factor, execution reward
    - Maintenance operations: add/merge/drop to prevent unbounded growth (demonstrated 46% bank reduction)
    - **DOWNSIDE:** ~230 GPU-hours training on 4xH100; relies on strong teacher model (GPT-5.4-mini)

11. **Anti-rationalization tables for safety (grounding: addyosani/agent-skills):**
    - Every Lyra skill ends with a table pairing common agent rationalizations with documented counter-arguments
    - Example: "I ran the tests locally" -> "Local != CI. Trigger the CI pipeline and verify the green check."
    - Zero code change (documentation-only), ~50-80 token cost per table

## Build Outline

### Phase 1: Foundation (weeks 1-2)

| Milestone | Details | Evidenced Estimate |
|-----------|---------|-------------------|
| SKILL.md parser + frontmatter extractor | Parse YAML frontmatter, extract name/description/tags/keywords | From SkillNet and addyosani open-source SKILL.md format |
| Progressive disclosure loader | 3-phase: Level 1 (metadata preload in index), Level 2 (body on match), Level 3 (references on demand) | Modeled on addyosani's session-start hook + SkillNet 3-phase lifecycle |
| Provider-agnostic injection | Read from filesystem, inject into messages array; strip/translate Claude-only fields | Validated by SkillNet's OpenClaw integration (3 behavioral patterns) |
| Deterministic skill matching | Keyword/embedding fallback for non-Claude providers | Adapts SELF-RAG's adaptive retrieval gating concept for condition-based trigger |

### Phase 2: Starter Kit (week 2-3)

| Milestone | Details | Evidenced Estimate |
|-----------|---------|-------------------|
| 8-10 bundled starter skills | code-review, debug, tdd, plan, verify, loop, brainstorm, deep-research | Ported from claude-skills (343 available) and addyosani (23 lifecycle) |
| Anti-rationalization tables | 4-6 rows per skill, ~60 tokens each | Direct port from addyosani pattern; zero code change |
| Forcing-question template | Pre-execution clarifying question + recommended answers | From addyosani/agent-skills Matt Pocock discipline |
| Per-provider trigger config | Claude: auto, DeepSeek: keyword-based | Config-driven switch |
| A/B test: genes vs. skills | Convert 5 skills to gene format, measure pass rate delta | Predict: genes +3.0 pp per GEP (4590 trials) |

### Phase 3: Quality & Graph (weeks 3-5)

| Milestone | Details | Evidenced Estimate |
|-----------|---------|-------------------|
| 5-D quality scorer | Safety, Completeness, Executability, Maintainability, Cost-awareness | SkillNet methodology; MAE target < 0.03 (validated with 3 PhD annotators) |
| Evaluator calibration | 50-skill blind annotation study with 2 annotators | Required per SkillNet; achieves QWK ~1.000 with 200-sample annotator study |
| SkillNet graph builder | Taxonomy (category->tag) + relation graph (similar_to, belong_to, compose_with, depend_on) + package library | SkillNet ontology; LLM-driven relation inference with periodic manual spot-check |
| Skill deduplication pipeline | MD5 hash + directory structure comparison | SkillNet pipeline filters 250K+ candidates to 150K+ curated |

### Phase 4: Evolution (weeks 4-7)

| Milestone | Details | Evidenced Estimate |
|-----------|---------|-------------------|
| GEP gene distillation | Convert skills to genes (230 tokens); run SCAN->SIGNAL->INTENT->MUTATE->VALIDATE->SOLIDIFY | GEP protocol specification; 4,590 trials validation |
| SkillOpt validation-gate loop | B=40 rollouts; Bm=8 minibatch reflection; hierarchical merge; Lt=4 cosine schedule; strict validation gate | SkillOpt architecture; 52/52 cell dominance; +23.5 avg gain |
| Rejected-edit buffer | Store rejected edits + failure patterns; feed back as negative feedback | SkillOpt §3.5; -1.6 to -4.6 impact without it |
| Slow/meta update | Cross-epoch comparison; protected section for longitudinal guidance | SkillOpt §3.6; -22.5 drop on SpreadsheetBench without it |
| Cross-harness transfer test | Train on Codex, deploy on Claude Code | SkillOpt §3.7; +59.7 points transfer validated |

### Phase 5: Learned Management (weeks 7-10, optional)

| Milestone | Details | Evidenced Estimate |
|-----------|---------|-------------------|
| CODESKILL RL policy training | GRPO + LoRA on Qwen3.5-4B; 3-stage curriculum | ~230 GPU-hours on 4xH100; 12,856 SFT examples |
| Multi-granularity bank | Task-level + event-driven skill types | CODESKILL §1.2; both types are complementary |
| Hybrid reward pipeline | lambda*R_Q + R_A*R_E with LLM-as-judge rubric | CODESKILL §1.5; R_A (alignment) gates execution reward |

## Multi-Provider Note

Skill loading is harness-level (filesystem -> messages array). On DeepSeek: deterministic matching preferred (keyword/embedding) over auto-trigger. Claude-only frontmatter (model: pin, dynamic-injection extensions) stripped/translated for non-Claude providers. Provider x skill compatibility matrix documented.

**Cross-model optimization transfer (validated):**
- SkillOpt: SpreadsheetBench skill GPT-5.4 -> GPT-5.4-mini: +9.4 (82% of in-domain gain retained)
- SkillOpt: OlympiadBench -> Omni-MATH: +3.7 (GPT-5.4), +1.8 (mini), +1.3 (nano)
- CODESKILL: Policy trained on Qwen3.5-35B-A3B feedback transfers to GPT-5.4-mini: +8.93 (+41.0% relative)

**Black-box API compatibility (validated):**
- TF-TTCL: Works on Qwen-Plus, DeepSeek-V3.2 without gradients or logit access
- GEPA: Gradient-free evolution works on any provider (ICLR 2026 Oral)
- SkillOpt: Harness-agnostic adapter works across direct chat, Codex CLI, Claude Code CLI

## Baseline Delta

| Component | Change | Migration Cost | Evidence |
|-----------|--------|---------------|----------|
| skill_format.py (421L) | KEEP — already solid | None | — |
| lyra-skills (package) | EXTEND: progressive disclosure loader with 3-phase lifecycle | Medium | addyosani session-start hook; SkillNet 3-phase; claude-skills 9-phase pipeline |
| lyra-skill-loader | EXTEND: per-provider trigger config + forcing-question pattern | Low | SELF-RAG adaptive gating concept; addyosani forcing-question discipline |
| lyra-skill-evolution | EXTEND: SkillOpt validation-gate loop + GEP gene canonicalization + CODESKILL RL (Phase 5) | High | SkillOpt 52/52 dominance; GEP 4590 trials; CODESKILL 32.8% relative |
| lyra-skill-quality (NEW) | ADD: 5-D quality scorer with MAE-calibrated evaluator | Medium | SkillNet evaluator MAE < 0.03; SkillNet 5-D rubric |
| lyra-skill-graph (NEW) | ADD: SkillNet-style typed relation graph builder | Medium | SkillNet 3-layer ontology; 250K+ candidate pipeline |
| lyra-gene-store (NEW) | ADD: GEP gene/capsule/event triad with audit trail + git rollback | Medium | GEP protocol; EvoMap/evolver production daemon |
| lyra-anti-rationalization (NEW) | ADD: anti-rationalization tables in skill manifests | Low | addyosani pattern; 50-80 tokens per table |

## Evidence Base

### Papers Cited

| ID | Title / Venue | Key Contribution |
|----|--------------|-----------------|
| 2603.04448v1 | SkillNet: Create, Evaluate, and Connect AI Skills — arXiv, Feb 2026 | Full-lifecycle skill infra; 5-D evaluation (MAE < 0.03); typed ontology graph; +40% avg reward, -30% steps |
| 2605.23904v2 | SkillOpt: Executive Strategy for Self-Evolving Agent Skills — Microsoft Research, May 2026 | Validation-gated text optimization; bounded edit budget; rejected-edit buffer; slow/meta update; 52/52 dominance; +23.5 avg |
| 2604.15097v2 | From Procedural Skills to Strategy Genes — EvoMap/Tsinghua, June 2026 | Strategy Genes (+3.0 pp) vs. Skills (-1.1 pp); 4,590 trials; GEP 6-stage protocol; gene composition collapse |
| 2605.25430v1 | CODESKILL: Learning Self-Evolving Skills for Coding Agents — NTU, May 2026 | RL-learned skill management policy; hybrid reward; 3-stage curriculum; +32.8% relative pass rate; 46% bank reduction |
| 2604.13552v1 | TF-TTCL: Training-Free Test-Time Contrastive Learning — SCUT, Apr 2026 | Explore-Reflect-Steer loop; Experience Rule Repository; +5.86 abs avg; black-box compatible |
| 2509.25140v2 | ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory — Google, 2025 | Dual success/failure extraction; 3-field schema; +20.5% SR; 4.3% token overhead |
| 2310.11511v1 | SELF-RAG: Learning to Retrieve, Generate, and Critique — UW/AI2/IBM, 2023 | Adaptive retrieval gating; reflection token vocabulary; 7B beats ChatGPT |
| 2509.25787v4 | EvoQuality — ICLR 2026 | Self-consistency voting (K=32); pairwise ranking; +31.8% PLCC without labels |
| 2410.10762v4 | AFlow: Automating Agentic Workflow Generation — MetaGPT, 2025 | MCTS over code-represented workflows; +5.7% avg; GPT-4o-mini outperforms GPT-4o at 4.55% cost |
| 2410.20285v6 | SWE-Search — ICLR 2025 | MCTS + hybrid value function; +23% rel improvement; 5-14x cost multiplier |
| 2502.00955v2 | DITS — CMU/USTC, 2026 | Influence scores beat Q-values for multi-agent; 46% less GPU cost |
| 8078 | CaTS — ICLR 2026 | Self-calibrated confidence; 94.2% sample savings; ECE 3.42-3.79 |
| 2509.26100v2 | AgenticEval — Fudan, 2026 | Self-evolving evaluation discovers 36.14 pp more failures; 88-91% human agreement |
| 2508.15305v2 | CFGM — EMNLP 2025 | Coarse-to-fine memory; +10.4 pp AlfWorld; 25% fewer turns |
| 2510.18407v1 | HAP — NeurIPS 2025 | Adversarial curriculum; 85% human on Crafter; 30% gap narrowing |
| 2605.25480v2 | LLM-Wiki — Tencent, May 2026 | Retrieval-as-reasoning via wiki traversal; +8.1 F1 MuSiQue; 2.5x faster than LightRAG |
| 2605.21569v3 | ChemAmp — Fudan, 2026 | Bi-phase tool amplification; 94% inference token reduction; emergent safety |
| AlphaEvolve | Google DeepMind Blog, May 2025 | Production evolutionary algorithm; 0.7% Google compute recovery; 23% kernel speedup |
| 2603.07670v1 | Memory Survey — Du, 2026 | POMDP formalization; "Memory-vs-no-memory gap exceeds model gap" |

### Books Cited

| Title | Publisher | Year | Key Contribution |
|-------|-----------|------|-----------------|
| Designing AI Agents | Manning (MEAP V01) | 2026 | "Harness engineering" philosophy; "never triage away failure information"; "skilled model with 30K-token context beats best model drowning in 180K tokens" |
| Architecting Generative AI Applications | (playbook) | 2026 | Self-evolving agent pattern recognition |

### Web Repos / Projects Cited

| Source | Key Contribution |
|--------|-----------------|
| alirezarezvani/claude-skills (GitHub) | 343 skills production pipeline; 9-phase SKILL_PIPELINE; Tessl quality gates; cross-compile to 13 platforms |
| addyosani/agent-skills (GitHub) | Progressive disclosure skill loading; anti-rationalization tables; 23 lifecycle skills; session-start hooks |
| EvoMap/evolver (npm, GitHub) | Production GEP daemon; singleton lock; git stash rollback; 45min cycle; 500MB RSS cap; signal de-duplication |
| EvoMap/skill2gep (GitHub) | Gene representation specification; GEP protocol canonicalization |
| EvoMap/awesome-agent-evolution (GitHub) | 80+ curated self-evolution projects across 9 categories |
| SkillNet (skillnet.openkg.cn) | 150K+ curated skills; Python SDK + CLI + REST API; OpenClaw integration demo |

## Expert Review

**Adversarial Skeptic:** "330+ skills from claude-skills is a bootstrap goldmine but also a quality risk. The GEP paper shows that even two complementary skills degrade performance by 6.1 pp — composition is not harmless. Ship with 8-10 vetted genes, not skills; let users install more individually. Never deploy multi-gene agents without measuring composition degradation per the GEP findings."

**Senior AI Engineer:** "SkillOpt is the right evolution approach for Lyra — it's the only technique with 52/52 cell dominance and cross-harness transfer (+59.7 points). But the 20-214M training token cost per skill is real. Start with ReasoningBank's simple extraction (+20.5% SR at 4.3% overhead) as a training-free baseline, then graduate to SkillOpt's validation-gated optimization. The GEP gene representation should be the intermediate artifact — not documentation skills."

**Safety Reviewer:** "The 5-D quality evaluator from SkillNet is essential for Lyra's plugin/skill marketplace. MAE < 0.03 with PhD annotators is achievable but requires budget for annotation study. The anti-rationalization tables from addyosani are the lowest-effort safety intervention — add them immediately to all bundled skills. The CODESKILL alignment factor R_A (does the agent actually follow the skill?) is a critical gate that Lyra must implement before any autonomous skill evolution."

**Impact:** 5 | **Effort:** 4 | **Tier:** (A) Parity + (B) Breakthrough
