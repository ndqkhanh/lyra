# Deep Research Methodology and Rigor -- Thematic Synthesis

**Date:** 2026-06-07
**Scope:** 18 papers, 2 book chapters, 3 repo/docs sources, cross-referenced across 409 candidate note files
**Synthesis type:** Definitive (Phase 4 feed)

---

## 1. Frontier Techniques (ranked by evidence strength)

### 1.1 Evidence DAG with Compositional Assembly (Argus)

- **Technique:** Structured evidence DAG (E = evidence nodes, C = claim nodes, A = support/contradict arcs) with batched graph-level verification. Parallel Searcher agents roll out independently; a Navigator maintains the shared graph, identifies gaps/contradictions holistically, dispatches targeted verification queries, and synthesizes the final answer from the DAG alone.
- **Sources:** Argus (Zhang et al., 2026, arXiv:2605.16217v3, MiroMind AI); cross-validated by AutoResearchClaw (Liu et al., 2026, arXiv:2605.20025v2) with its verified-registry pattern; cross-validated by academic-research-skills (Wu, 2026, v3.11.1) with its L3 claim-faithfulness audit.
- **Mechanism:** Graph G = (E, C, A) where A is a subset of (E union C) x C x {+1, -1}. Navigator inspects G holistically and emits batch of verification queries V targeting unverified claims, contradicted claims, and unaddressed sub-questions. Trained with GRPO using contrastive reward: R_i = clip(R_w/v + lambda x (R_w/v - R_w/o v), 0, 1) with lambda = 0.5. Context compression ratio: 25.6M Searcher tokens compressed to 21.5K Navigator tokens (~1200:1). Parallelism K is a config knob at inference (training uses K=1 for credit assignment simplicity).
- **Evidence:** Argus-Parallel (K=8, 35B-A3B): BrowseComp 74.5%, GAIA 93.2% (+12.6 over best proprietary), Seal-0 56.2% (+6.2). Log-linear scaling to K=64: BrowseComp 86.2% with no observed ceiling. Cross-backbone zero-shot transfer: Navigator trained on Searcher-35B works with DeepSeek-V4-Flash-Max (78.5%) and Seed-2.0-Pro (82.4%).
- **Maturity:** Lab validated (GRPO training on 64xH200 GPUs, 1.5 days). Not deployed in production research tools yet.

### 1.2 Four-Stage Lifecycle Framework with Phase-Boundary Verification Gates

- **Technique:** A complete eight-stage research lifecycle organized into four phases (Creation/Writing/Validation/Dissemination), with explicit verification checkpoints at every stage boundary. Layered architecture: exploration layer -> execution layer -> verification layer. Provenance-preserving handoffs between stages.
- **Sources:** "AI for Auto-Research: Roadmap and User Guide" (Kong et al., 2026, arXiv:2605.18661v1, survey of 270+ systems); cross-validated by "Building Reliable AI Systems" (Shahani, 2026, Chapter 9: Evaluation and Performance) with its three-layer output quality defense; cross-validated by "Towards Trustworthy Agentic AI" (Qi et al., 2026, arXiv:2605.23989v1) with its defense-in-depth assurance stack.
- **Mechanism:** Each phase transition enforces a verification gate: provenance tracking (every claim traceable backward to experiment/citation/evidence), explicit state schemas at handoffs, and human-governed checkpoints at high-leverage decision points. The framework catalogs five cross-cutting insights: (1) artifact generation outpaces verification, (2) human-governed collaboration is the most reliable deployment mode, (3) capability boundaries emerge in open-ended tasks, (4) effective systems converge on layered architectures, (5) AI use is a governance problem, not a detection problem.
- **Evidence:** 80% fabrication rate in fully autonomous ML experiments (MLR-Bench); AI reviews assign inflated scores (6.86 vs 5.70 human, missing 95.8% of rejection-worthy flaws); 58.6% of research-code errors are semantic (code runs but wrong algorithm); 17.5% of CS paper abstracts show detectable AI modification.
- **Maturity:** Research concept (taxonomy/synthesis, not experimental validation). AutoResearchClaw (Liu et al., 2026) partially implements this framework with concrete verification gates.

### 1.3 Pivot/Refine/Proceed Decision Loop with Failure-as-Information Semantics

- **Technique:** When an experiment fails, the system captures the failure signature, generates targeted fixes, then makes a structured decision: Proceed (evidence supports hypothesis), Refine (adjust current approach, up to N_r=10), or Pivot (return to hypothesis generation with failure recorded as evidence, up to N_p=2). Cascading code generation with complexity scoring routes tasks to appropriate execution backends.
- **Sources:** AutoResearchClaw (Liu et al., 2026, arXiv:2605.20025v2, 35 authors, UNC-Chapel Hill/CMU/NUS/UC Berkeley/Stanford/Google/Meta); cross-validated by AUTO REPRODUCE (Zhao et al., 2026, arXiv:2505.20662v4) with its dual-agent iterative debug loop and EDIT command for granular repair.
- **Mechanism:** Complexity scoring c in [0,1] across 6 dimensions (architectural depth, file count, domain difficulty, dependency chains, historical failure rate, control-flow complexity). Experiments with c > tau (tau=0.6) dispatched to external AI coding agent; simpler ones use built-in multi-phase code agent. Static validation gates check for identical ablation implementations and hardcoded metric values before execution. Three-phase Docker network isolation (install -> data acquisition -> air-gapped execution).
- **Evidence:** Self-healing removes: completion from 6/10 -> 10/10; ablation shows self-healing prevents 4/10 topics from failing on first error. CoPilot mode achieves 87.5% accept rate vs 25.0% Full-Auto. Debug protocol: max 20 tries per sub-phase, bugs typically resolved in 5-8 iterations. At $3-15 per run in LLM usage.
- **Maturity:** Lab validated (23-stage pipeline, ARC-Bench evaluation). Repository open-sourced at github.com/aiming-lab/AutoResearchClaw.

### 1.4 Tree-Structured Deliberation with Search (MCTS for Reasoning)

- **Technique:** LLM reasoning framed as a Markov Decision Process (MDP) with Monte Carlo Tree Search (MCTS) for exploration. The same frozen LLM serves as both world model (state predictor) and reasoning agent (action proposer). Four reward types guide search: action likelihood, state confidence, self-evaluation, task-specific heuristics.
- **Sources:** RAP (Hao et al., 2023, arXiv:2305.14992v2, EMNLP 2023); Tree of Thoughts (Yao et al., 2023, arXiv:2305.10601v2, NeurIPS 2023); cross-validated by "Building Reliable AI Systems" (Shahani, 2026, Chapter 6) which recommends Tree-of-Thought for high-uncertainty multi-path problems.
- **Mechanism:** RAP: MCTS with UCT formula for selection: a* = argmax [Q(s,a) + w * sqrt(ln N(s) / N(c(s,a)))]. N iterations, d candidate actions per expansion. Thought decomposition granularity is task-dependent. Two search strategies: BFS (fixed branching, shallow depth -- Game of 24, Creative Writing) and DFS (variable branching, deeper depth -- Crosswords). Tree of Thoughts: b=5 branching, k=3-5 candidates per step, BFS/DFS depending on task structure.
- **Evidence:** RAP (LLaMA-33B) achieves 64% on Blocksworld vs 6% CoT (18.5x improvement on Game of 24). RAP surpasses GPT-4+CoT by 33% relative. Tree of Thoughts: Game of 24 74% success vs 4% CoT; Creative Writing +9% coherency. CaTS (Huang et al., 2026, ICLR 2026): self-calibrated confidence saves 94.2% samples to reach 85.0 accuracy on MathQA compared to standard Self-Consistency. Theoretical guarantee: CaTS-SC exponentially dominates vanilla majority voting under a two-tier confidence mixture model.
- **Maturity:** RAP/ToT: well-established (1,000+ citations for ToT). CaTS: ICLR 2026 published. None production-deployed for interactive agent use due to latency (100+ LLM calls per query).

### 1.5 Paper Lineage for Implicit Knowledge Mining

- **Technique:** For any target paper, trace citation graph to top-k cited papers, download their repos, and extract <summary, code> tuples as domain-aligned reference exemplars. This captures tacit implementation knowledge (common module architectures, data processing pipelines) that is rarely stated explicitly in papers but emerges from cited literature.
- **Sources:** AUTO REPRODUCE (Zhao et al., 2026, arXiv:2505.20662v4, Tsinghua/OpenBMB); cross-validated by academic-research-skills (Wu, 2026, v3.11.1) with its deterministic 4-index citation verification; cross-validated by AutoResearchClaw (Liu et al., 2026) with its 4-layer citation verification pipeline.
- **Mechanism:** Algorithm 1 from AUTO REPRODUCE: (1) RA(P, k) -> top-k relevant cited papers via in-text citation context analysis; (2) for each cited paper: download via ArXiv/Semantic Scholar API, extract summary + repo URL; (3) if repo exists, filter relevant source files using code agent; (4) construct K_lineage = {<summary_1, code_1>, ...}. Comparison baselines in experimental section are prioritized as most critical references. Top-1 Recall@3 ~0.43 (Claude-3.5-Sonnet) against expert-curated gold-standard references.
- **Evidence:** Ablation: removing paper lineage drops Mixed-Level score from 69.97 -> 63.15 and increases Perf Gap from 31.62 -> 39.59. Execution rate: 92-95% vs 2-18% for baselines. Performance gap drops from ~99 (ChatDev) to <25 (Gemini-2.5-Pro). Mixed-level evaluation correlates with human judgment at r=0.81-0.83. Cost: $1.87 per experiment reproduction.
- **Maturity:** Lab validated (REPRODUCE BENCH: 13 papers, 13 AI sub-domains). Code open-sourced at github.com/AI9Stars/AutoReproduce.

### 1.6 Deterministic Multi-Index Citation Verification

- **Technique:** Cross-check every cited reference against up to 4 bibliographic indexes (Semantic Scholar + OpenAlex + Crossref + arXiv) via direct API calls (not LLM). Persistent SQLite cache (90-day TTL) avoids redundant lookups. Optional terminal policy makes citation existence failures blocking. Separate L3 claim-faithfulness audit uses LLM-as-judge to verify that claims are actually supported by cited sources.
- **Sources:** academic-research-skills (Wu, 2026, v3.11.1, github.com/Imbad0202/academic-research-skills); cross-validated by AutoResearchClaw (Liu et al., 2026) with its 4-layer citation pipeline (CrossRef DOI -> OpenAlex fuzzy title -> arXiv ID -> Semantic Scholar fallback); cross-validated by "Building Reliable AI Systems" (Shahani, 2026, Chapter 3) recommending source attribution and citation mechanisms.
- **Mechanism:** v3.11 citation existence gate: `lookup_verified == false` narrowed to ID-keyed unmatched only (specific DOI lookup that provably fails), so legitimate unindexed citations remain `unresolvable` and never block. L3 audit: standalone LLM fetches each cited source against its locator anchor, judges whether claim is actually supported. 5 HIGH-WARN annotation classes; formatter gates-refuse on unresolved HIGH-WARN. Cross-index triangulation with 4 severity tiers plus terminal policy layer. Material Passport: YAML-based serializable artifact ledger tracking every claim, citation, decision, and integrity result.
- **Evidence:** 967 tests pass / 3 skipped / 0 failed (CI enforcement). ~30 Python lint scripts in CI. Deterministic gate adds no Claude token cost (API-only, SQLite-cached). Full pipeline cost: $4-6 for ~15k-word paper with ~60 references.
- **Maturity:** Production deployed (v3.11.1 as of 2026-06-06, actively maintained). CI-enforced through 10 GitHub Actions workflows.

### 1.7 Self-Calibrated Confidence for Adaptive Sampling

- **Technique:** Train LLMs via LoRA to produce reliable confidence scores (Self-Calibration) in a single forward pass using Soft Self-Consistency (SSC) as training targets, which combines intrinsic confidence P(True) with inter-response agreement. Use calibrated confidence to dynamically adjust sampling: stop early when confidence exceeds threshold, weight votes by confidence, or adaptively sample until confidence converges.
- **Sources:** CaTS (Huang et al., 2026, ICLR 2026); cross-validated by SELF-RAG (Asai et al., 2023, arXiv:2310.11511v1) with its reflection tokens (ISSUP for output support, ISUSE for response usefulness); cross-validated by "Building Reliable AI Systems" (Shahani, 2026, Chapter 9) recommending Grounding Defect Rate (GDR) and FActScore for response-level granularity.
- **Mechanism:** SSC(y) = Sigma_{i: y_i = y} c_i / Sigma_{i=1..N} c_i where c_i = P(True) for response i. SSC achieves ECE 3.42 on GSM8K vs 4.48 (SC) and 12.03 (P(True) alone). Training: LoRA (r=32, alpha=16, dropout=0.05), SmoothL1 loss on calibrated confidence + generation loss on high-confidence responses (eta=0.75 threshold). Dynamic Temperature (EDT) sampling: T(H) = T_0 x M^(gamma/H) if >= tau_0, else 0.
- **Evidence:** CaTS-SC saves 94.2% samples to reach 85.0 on MathQA (Llama-3.1-8B). CaTS-ES improves Best-of-N: +14.5 on Obj Counting, +9.9 on MathQA. Out-of-domain: ECE improves from 27.85 to 9.69 on Object Counting, 12.55 to 8.64 on MathQA. Accuracy improves simultaneously: GSM8K 77.44 -> 80.43, SVAMP 72.60 -> 75.29.
- **Maturity:** Lab validated (ICLR 2026). Self-Calibration requires SFT per model; CaTS inference variants are training-free given calibrated model.

### 1.8 Mind-Map Structured Memory via Knowledge Graph + GraphRAG

- **Technique:** Convert raw reasoning chains into a structured knowledge graph with entity extraction, community clustering (Leiden algorithm), community summarization via LLM, and GraphRAG retrieval. Provides compressed, queryable context that scales with reasoning length while preserving logical entity relationships.
- **Sources:** Agentic Reasoning (Wu et al., 2025, arXiv:2502.04644v2, Oxford/NUS/CMU); cross-validated by MTR-SUITE (Ruan et al., 2026, arXiv:2605.20729v1) with its Greedy Traversal Clustering algorithm; cross-validated by "Building Reliable AI Systems" (Shahani, 2026, Chapter 6) recommending agents with three core components including memory.
- **Mechanism:** DeepSeek-V3 extracts entities and semantic relationships from reasoning chain; Leiden algorithm partitions graph into communities; LLM summarizes each community. When reasoning model becomes uncertain or encounters gaps, it queries the Mind-Map directly; GraphRAG retrieval returns relevant structured information. Re-ranking with threshold-based iteration: avg_score = 1/10 * Sigma CohereRerank(q, context, page_i); if avg_score < 0.7, trigger query refinement (max 3 loops).
- **Evidence:** Mind-Map achieves 66.13 on GAIA vs 55.10 MemGPT (best flat memory) -- an 18-point gap. Werewolf strategic reasoning: 72% win rate with Mind-Map vs 36% without. Humanity's Last Exam: 23.8% (14.4 points over base R1). GPQA: 81.2% (9.7 points over base, surpasses o3-mini-high). 6.8 min/query vs GPT Deep Research 17.8 min/query.
- **Maturity:** Lab validated. Open-source at github.com/theworldofagents/Agentic-Reasoning. Uses proprietary services (Bing, Cohere, Claude, DeepSeek).

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy | Latency | Memory Cost | Complexity | Scalability | Evidence Strength |
|---|---|---|---|---|---|---|
| **Evidence DAG (Argus)** | 74.5% BrowseComp, 93.2% GAIA (35B) | High: slowest parallel Searcher dominates; K=64 ~25.6M tokens | Navigator context: 21.5K tokens (1200:1 compression) | High: GRPO training, DAG construction, RL credit assignment | Excellent: log-linear to K=64, no ceiling | Strong: 5/8 benchmarks lead; cross-backbone transfer validated |
| **Lifecycle Framework** | Framework, not algorithm; CoPilot mode 87.5% accept | Variable: 23 sequential stages | Full pipeline ~200K+ input tokens | Medium: taxonomy to implement, not train | Good: domain profiles extend coverage | Strong: 270+ system survey; cross-validated by 2 book sources |
| **Pivot/Refine/Proceed** | Completion 10/10 with self-healing vs 6/10 without | Moderate: repair loop up to N_r=10 retries | Low per retry; cumulative across pipeline | Medium: state machine + failure taxonomy + complexity scorer | Good: N_p=2 pivots prevent infinite loops | Strong: controlled ablation; open-source implementation |
| **MCTS Reasoning (RAP/ToT)** | 64% Blocksworld (vs 6% CoT), +14% proof accuracy | Very high: 100+ LLM calls per query | Per-call memory; tree state grows with branching | High: per-domain reward/prompt engineering; UCT implementation | Limited: degrades on 12-step problems (32%->9% hard) | Strong: 1,000+ citations; multiple independent replications |
| **Paper Lineage** | Mixed-Level 69.97 (Claude-3.5-Sonnet), 77.56 (Gemini-2.5-Pro) | Moderate: API calls for citation traversal + repo access | <summary, code> tuples compact per reference | Medium: ArXiv API + GitHub API + citation graph traversal | Good: 13 diverse AI sub-domains tested | Moderate: single-paper scope; 43% Top-1 Recall@3 |
| **Citation Verification (Multi-Index)** | Near-deterministic (4-index cross-check + SQLite cache) | Near-zero after first lookup (cache); API latency on first | Persistent SQLite cache (90-day TTL) | Low: API integration + cache; no training | Excellent: scales with number of citations linearly | Strong: 967 CI tests; production deployed |
| **Self-Calibrated Confidence (CaTS)** | +7.7-14.5 points over uncalibrated; saves 94.2% samples | Training: 1 epoch LoRA. Inference: single forward pass per sample | LoRA weights (small); no additional runtime memory | Medium: training pipeline (SSC labeling + LoRA SFT) | Good: out-of-domain generalization shown | Moderate: ICLR 2026; 3-model evaluation |
| **Mind-Map Graph Memory** | 66.13 GAIA (vs 47.84 raw memory) | 6.8 min/query (multi-agent) | Knowledge graph + community summaries | High: entity extraction + Leiden clustering + GraphRAG | Moderate: vendor-locked (Bing/Cohere/Claude/DeepSeek) | Strong: ablation vs 5 alternative memory strategies |

---

## 3. Convergences

Where multiple independent sources agree -- these are the safe bets.

### 3.1 Verification Must Be Structural, Not Aspirational

**Converging sources (6 independent):**
- Kong et al. (2026, arXiv:2605.18661v1): "Artifact generation outpaces scientific verification" -- the paper's #1 cross-cutting insight. Errors propagate across stage boundaries; isolated evaluation misses compound failures.
- Qi et al. (2026, arXiv:2605.23989v1): Defense-in-depth across all 5 lifecycle stages is mandatory; mitigations at different stages are "complementary, not substitutable." Process metrics (CVR, DCR, CompVR) catch intermediate violations that outcome-only evaluation misses.
- Liu et al. (2026, arXiv:2605.20025v2): Removing verification inflates apparent acceptance (3/10 -> 5/10) but 3 of those 5 contain fabricated values. The cost of integrity is real.
- Wu (2026, academic-research-skills v3.11.1): Deterministic citation verification via 4-index API cross-check + L3 claim-faithfulness audit as mandatory pipeline gates.
- Shahani (2026, Chapter 9): Three-layer output quality defense (automated content filters, statistical monitoring, LLM-as-judge). Track both explicit and implicit feedback signals.
- Zhang et al. (2026, arXiv:2605.16217v3): Structured evidence DAG makes missing pieces and contradictions structurally computable -- verification is not post-hoc but built into the representation.

**Consensus:** Every source that addresses rigor agrees: verification must be architecturally embedded at stage transitions, not applied as a terminal filter. The minimum viable verification includes: (a) numeric claim-to-source matching, (b) citation existence checking against bibliographic databases, (c) claim-to-evidence faithfulness auditing.

### 3.2 Retrieval Must Be Hybrid (Lexical + Semantic)

**Converging sources (4 independent):**
- Sen et al. (2026, arXiv:2605.15184v1): Inline grep exceeds inline vector for every single harness-model pair tested (10/10). But vector wins at low session counts; the crossing point depends on harness + backbone, not corpus size alone. The paper's core finding: harness architecture can invert the lexical-vs-semantic ordering.
- Shahani (2026, Chapter 4): "Implement hybrid search (dense vectors + keyword/BM25) for production reliability." Dense retrieval works well for semantic similarity but can miss exact matches.
- SELF-RAG (Asai et al., 2023): Adaptive retrieval -- the model decides whether retrieval would help each segment, using specialized reflection tokens (Retrieve: Yes/No/Continue). This avoids polluting context with irrelevant retrievals.
- Wu et al. (2025, arXiv:2502.04644v2): Re-ranking with threshold-based iteration (Cohere Rerank 3.5, avg_score < 0.7 triggers query refinement). Knowledge Refinement becomes redundant when Re-rank is present.

**Consensus:** The debate is not lexical vs. semantic -- it is how agents should dynamically route between them. Hybrid search with re-ranking and adaptive query reformulation is the convergent architecture. The retrieval strategy, harness scaffolding, and output delivery format must be designed as a single joint system.

### 3.3 Multi-Agent Orchestration Improves Rigor but Introduces Social Contagion Risk

**Converging sources (5 independent):**
- Xu et al. (2026, arXiv:2602.00428v2, ICLR 2026): Multi-agent systems exhibit the "Mandela effect" -- collective false memory where agents converge on incorrect answers due to social influence. Role-based protocols are the strongest attack vector (sigma_RS = 61.59% for GPT-4o-mini). Cognitive Anchoring achieves 69.6% sigma reduction (prompt-only defense).
- Kong et al. (2026, arXiv:2605.18661v1): "Role specialization reduces self-confirmation bias; best config uses 8 agents/5 rounds/50% diversity for ideation." But agents can "duplicate work, reinforce shared misconceptions, or produce verbose deliberation without improving quality."
- Liu et al. (2026, arXiv:2605.20025v2): K=3 debate agents (Innovator/Pragmatist/Contrarian) is the sweet spot. K=2 degenerates into pro/con (-23% diversity); K=5 raises tokens +67% for only +8% diversity gain.
- Qi et al. (2026, arXiv:2605.23989v1): "Centralized multi-agent oversight prevents emergent cascades and collusion" but introduces coordination overhead and potential single point of failure.
- Shahani (2026, Chapter 8): "Specialize agents by domain rather than building monoliths. Test workflows, not just individual agents -- bugs occur at the seams. Implement graceful degradation when individual agents fail."

**Consensus:** Multi-agent systems produce better outputs than single-agent when designed with epistemic diversity (role specialization) AND defended against social contagion (cognitive anchoring prompts). The sweet spot is 3-5 agents with explicitly adversarial roles. Every agent should form independent conclusions before integrating peer output. Consensus should be treated as a potential manipulation signal, not a reliability indicator.

### 3.4 Layered Architecture Is the Convergent Design Pattern

**Converging sources (5 independent):**
- Kong et al. (2026, arXiv:2605.18661v1): "Layered architectures (exploration -> execution -> verification) emerge as the convergent design pattern across the most capable systems in every stage."
- Liu et al. (2026, arXiv:2605.20025v2): 23-stage pipeline explicitly organized as three phases (Discovery/Experimentation/Writing+Verification).
- Qi et al. (2026, arXiv:2605.23989v1): Defense-in-depth across four assurance tiers (Upfront/Training-time/Runtime/Post-hoc).
- Shahani (2026, Chapter 6): "Separate the harness (control plane: agent loop, approvals, tracing, state) from the sandbox (compute plane: file I/O, shell, code execution)."
- Zhao et al. (2026, arXiv:2505.20662v4): Dual-agent decoupling (Research Agent for text tasks, Code Agent for code tasks) prevents context pollution.

**Consensus:** Monolithic single-pass architectures are insufficient. The convergent pattern has three layers: (1) exploration/generation, (2) execution/computation in isolated sandbox, (3) verification/audit before output. This maps to Lyra's architecture debate directly.

### 3.5 Human-in-the-Loop at High-Leverage Decision Points Outperforms Full Auto or Full Manual

**Converging sources (3 independent):**
- Liu et al. (2026, arXiv:2605.20025v2): CoPilot mode (6 targeted interventions) achieves 87.5% accept rate, beating Full-Auto (+62.5pp) and Step-by-Step (+37.5pp). Gate-Only (3 fixed checkpoints) achieves 100% validity.
- Kong et al. (2026, arXiv:2605.18661v1): "Human-governed collaboration is the most reliable deployment mode -- AI augments, humans retain judgment."
- Apple ML Research (Cheng et al., 2026, arXiv:2602.07283): Users want MORE explanation in error-prone/risky contexts and LESS explanation in routine contexts. Mode-aware explainability with confidence-gated intervention.

**Consensus:** Neither full autonomy nor micromanagement is optimal. The most effective pattern is targeted human intervention at high-leverage decision points (hypothesis co-creation, experiment design, result analysis) with automated handling of routine stages. The optimal number of interventions is 3-6 per research cycle.

---

## 4. Contradictions

Where sources disagree -- these need arbitration in Phase 4 plans.

### 4.1 Can Accuracy Scale Log-Linearly with Compute Indefinitely?

- **Pro (Argus, Zhang et al., 2026):** BrowseComp scales from 55.0% (K=1) to 86.2% (K=64) with "no sign of flattening." Accuracy scales log-linearly with compute budget.
- **Con (Kong et al., 2026):** "Diversity collapse: LLM ideas cluster in narrow regions; not solvable by scaling." AI-generated ideas degrade more after execution: delta = -1.98 vs -0.63 for human ideas.
- **Arbitration needed:** Argus tests on factual QA (BrowseComp, GAIA) where evidence is composable. Kong et al. test on idea generation where diversity requires divergent thinking. The scaling law may hold for evidence assembly but break for creative synthesis. Phase 4 must separate these regimes.

### 4.2 Is Lexical or Semantic Retrieval Better for Deep Research?

- **Sen et al. (2026):** Inline grep beats inline vector on every harness-model pair (10/10). Largest margin: +23.3pp. Grep is "ruthlessly precise when pattern matches exist." Conclusion: "harness architecture can invert the lexical-vs-semantic ordering."
- **Shahani (2026, Chapter 4):** Dense retrieval "works well for semantic similarity" but recommends hybrid search (dense + BM25). Notes that dense retrieval "can miss exact matches."
- **Wu et al. (2025):** Uses semantic search (Bing) with Cohere Rerank + Mind-Map graph context. Achieves SOTA on GAIA. No lexical component.
- **Arbitration needed:** Sen et al. explicitly acknowledge their task distribution favors lexical methods (LongMemEval-S with literal evidence). For scientific literature retrieval (paraphrased abstracts, multi-hop reasoning), the ranking may invert. The practical answer is probably hybrid with dynamic routing based on query type -- exactly what Sen et al. advocate. Lyra should implement both tools and let the agent route.

### 4.3 Does Fine-Tuning for Resilience Create Pathological Over-Rejection?

- **Xu et al. (2026):** Resilience-only SFT drops sigma_RS from 99.47% to 18.2% for Llama3.1-8B, but sigma_C (rejection of truthful group input) surges to 38.5%. Combined training resolves this (sigma_RS = 21.5%, sigma_C = 1.1%).
- **Qi et al. (2026):** Constitutional AI (RLAIF) prevents safety regressions but requires careful reward modeling to avoid "over-refusal." Stronger privacy/security controls risk blocking legitimate data flows.
- **Arbitration needed:** Both sources agree that single-objective optimization creates pathological trade-offs. Combined objectives (resilience + cooperative guidance) resolve the tension. The implication for Lyra: any guardrail fine-tuning must be multi-objective with explicit evaluation of over-rejection rates.

### 4.4 How Many Debate Agents Is Optimal?

- **Liu et al. (2026):** K=3 is the sweet spot. K=2 degrades (-23% diversity); K=5 costs +67% tokens for only +8% diversity gain.
- **Kong et al. (2026):** "Best config uses 8 agents/5 rounds/50% diversity for ideation."
- **Arbitration needed:** Liu et al. tested on a specific pipeline with Innovator/Pragmatist/Contrarian roles. Kong et al. survey finding references a different study's config for ideation specifically. The optimal count may be task-dependent: 3 for experiment analysis, 5-8 for idea generation. Lyra should parameterize this.

### 4.5 Is Prompt-Level Defense Against Social Contagion Sufficient?

- **Xu et al. (2026):** Cognitive Anchoring prompt achieves 69.6% sigma reduction for GPT-4o. Simple, zero-latency, no training.
- **Xu et al. (2026), same paper:** SFT combined training provides deeper resistance (sigma_RS from 99.47% to 21.5%). Prompt-only may not generalize across model architectures.
- **Qi et al. (2026):** Defense-in-depth is mandatory -- no single stage can be fully secured by mitigating another. A poisoning attack at perceive cannot be fully neutralized by act-time guardrails.
- **Arbitration needed:** Prompt-level defense is the obvious starting point (near-zero cost). But for production Lyra deployments where reliability is critical, layered defense (prompt + SFT + runtime shields + post-hoc auditing) is the convergent architecture.

---

## 5. Open Problems

What problems does NO source solve yet? These are research opportunities.

### 5.1 No Lifecycle-Scale Benchmark Exists

**Source:** Kong et al. (2026, arXiv:2605.18661v1) explicitly states: "No lifecycle-scale benchmark exists; cross-system comparison confounded by different base models, prompts, tools, compute budgets, and human-in-the-loop assumptions." Every benchmark evaluates individual stages (SWE-bench for coding, AgentBench for tool use, GAIA for web research), but no benchmark evaluates the complete research lifecycle with cross-stage error propagation. This makes it impossible to compare Argus vs. AutoResearchClaw vs. Agent Laboratory on end-to-end scientific validity rather than stage-level metrics.

### 5.2 Semantic Correctness Gap Remains Unsolved

**Source:** Kong et al. (2026) documents that 58.6% of research code errors are semantic (code runs but implements the wrong algorithm). No existing technique directly addresses this -- auto-reproduction (Zhao et al., 2026) improves execution rate but cannot verify algorithmic correctness. Verification (Liu et al., 2026) catches fabricated numbers but not wrong-but-executable algorithms (the "silent semantic collapse" failure mode).

### 5.3 Cross-Domain Research Transfer Remains Brittle

**Sources:** AutoResearchClaw achieves 0.912 on biology and 0.898 on statistics, but only 0.489 on HEP-physics (Liu et al., 2026). Baselines (AIDE-ML, AI Scientist v2) score zero on physics and biology. Kong et al. (2026): corpus concentrated in CS/ML/NLP; cross-domain generalization "largely untested." Every system requires domain-specific YAML profiles, Docker images, and debate role definitions.

### 5.4 No Adversarial Robustness Testing for Research Agents

**Sources:** Xu et al. (2026) demonstrates prompt injection and lexical triggers as effective attacks on review systems (raise scores to 10.00 under iterative attacks; 5% review manipulation flips 12% of rankings). Kong et al. (2026) catalogs adversarial fragility of automated reviewers. But no source tests adversarial robustness of the full research pipeline -- could an adversary inject a paper into the literature that causes downstream agents to adopt false premises? Could training data poisoning propagate through the citation graph?

### 5.5 Dynamic Confidence Boundaries Are Unknown

**Sources:** CaTS (Huang et al., 2026) calibrates confidence for single-step reasoning. Argus (Zhang et al., 2026) uses a learned Navigator policy to decide when to dispatch verification. But no source addresses the interaction: when should an agent switch from "proceed with current confidence" to "escalate for human review" or "spawn verification sub-agents"? The AutoResearchClaw SmartPause mechanism (Liu et al., 2026) adapts thresholds based on historical approval patterns but does not learn per-domain confidence boundaries.

### 5.6 Citation Graph Contamination Is Not Studied

**Sources:** Kong et al. (2026): 17.5% of CS paper abstracts show detectable AI modification. 15.8% of ICLR 2024 reviews were AI-assisted. Xu et al. (2026): all 5 SOTA detectors fail on polished AI-generated reviews. No source studies how AI-generated content in the citation graph (papers, reviews, rebuttals) affects downstream research agent reliability. This is a recursive contamination problem: agents generate papers -> papers enter citation graphs -> future agents train on or retrieve from contaminated graphs.

### 5.7 No Formal Guarantees for Evidence Completeness

**Sources:** Argus (Zhang et al., 2026) provides source-traced answers but acknowledges a "Searcher recall ceiling" from absent/paywalled sources. MTR-SUITE (Ruan et al., 2026) audits annotation sparsity using Discriminability Testing (97% human validation rate) but this is a proxy -- enumerating all relevant documents is intractable. No technique provides formal completeness guarantees for evidence retrieval. This is likely fundamental (the open-world nature of web search), but partial solutions (coverage estimation, uncertainty quantification) are underexplored.

---

## 6. Recommendations for Lyra

Ranked by impact/feasibility ratio, with rationale.

### Priority 1: Implement Phase-Boundary Verification Gates (Adopt Now)

**Sources:** Kong et al. (2026), Liu et al. (2026), Wu (2026), Qi et al. (2026), Shahani (2026, Chapters 3, 9)

**Recommendation:** Add explicit verification checkpoints at every Lyra stage transition (research -> planning -> execution -> writing). Each gate must verify:
1. Every numeric claim is traceable to an execution artifact (AutoResearchClaw verified-registry pattern)
2. Every external citation is cross-checked against at least 2 bibliographic databases (academic-research-skills 4-index pattern, simplified to 2 for latency)
3. Every sub-agent output is evaluated by an independent verifier agent before proceeding to the next stage

**Rationale:** This is the #1 convergent finding across all sources. The artifact-verification gap is the dominant failure mode (80% fabrication rate under full autonomy). Verification gates are the highest-impact, lowest-regret architectural decision Lyra can make. They are additive (don't require removing existing functionality), implementable incrementally (start with claim-to-source tracing), and directly address the reliability workstream.

### Priority 2: Deploy Cognitive Anchoring for Multi-Agent Interactions (Adopt Now)

**Sources:** Xu et al. (2026), Liu et al. (2026), Shahani (2026, Chapter 8)

**Recommendation:** Before any Lyra sub-agent receives output from peer agents, inject a cognitive-anchoring preamble:
1. Form independent conclusion first (before reading peer output)
2. Require explicit justification for any deviation from initial judgment when integrating peer output
3. Flag "overly coherent consensus" as a potential social-influence artifact

Additionally, use K=3 role-differentiated agents for critical decisions (e.g., Proposer/Pragmatist/Critic), not more.

**Rationale:** Near-zero engineering cost (prompt-only), 69.6% reduction in reality shifts demonstrated, and directly addresses Lyra's multi-agent orchestration reliability. The Mandela effect is a real failure mode that Lyra's current architecture is undefended against.

### Priority 3: Build Hybrid Lexical+Semantic Retrieval with Dynamic Routing (Adopt Soon)

**Sources:** Sen et al. (2026), Shahani (2026, Chapter 4), Wu et al. (2025), Asai et al. (2023)

**Recommendation:** Implement both grep (lexical) and vector (semantic) retrieval tools. Let Lyra's agent dynamically route between them based on:
- Query type (literal fact lookup -> grep; conceptual synthesis -> vector)
- Corpus size (small -> vector; large -> grep first)
- Agent's demonstrated tool-use competence with each retrieval mode

Design tool-output delivery (inline vs. file-based) carefully -- the same underlying model can vary by 16+ points depending solely on delivery format.

**Rationale:** Low engineering effort (grep is trivial to add), high impact (grep beats vector on every harness-model pair in Sen et al., 2026), and aligns with the convergent finding that retrieval strategy is not a standalone choice but part of a joint system with harness architecture.

### Priority 4: Implement Paper Lineage Construction for Deep Research Tasks (Phase 4 Plan)

**Sources:** Zhao et al. (2026), Wu (2026), Liu et al. (2026)

**Recommendation:** When Lyra performs deep research on a paper, automatically:
1. Extract top-k most relevant cited papers via in-text citation context analysis
2. Download cited papers, extract summaries and repo URLs
3. Clone repos, filter relevant source files, construct <summary, code> tuples
4. Use lineage-derived exemplars as few-shot context for code generation and understanding

Prioritize comparison baselines in the experimental section (most critical references).

**Rationale:** Moderate engineering effort (ArXiv API + GitHub API + citation graph traversal), proven benefit (+6.82 Mixed-Level score, -7.97 Perf Gap improvement). Directly addresses Lyra's ability to understand and replicate research -- a core differentiator.

### Priority 5: Explore Evidence DAG for Multi-Source Synthesis (Phase 4 Research)

**Sources:** Zhang et al. (2026), Wu (2025)

**Recommendation:** Investigate adapting the Argus evidence DAG pattern for Lyra's context management. Instead of concatenating raw agent trajectories into context, maintain a structured graph where evidence and claims are nodes with support/contradiction edges. Use graph-based retrieval for synthesis rather than linear context windows.

**Rationale:** The 1200:1 context compression property directly addresses Lyra's context budget problem. The auditable answer property (every claim traces to source) aligns with Lyra's source-ledger.md approach. However, this requires significant architectural change (DAG construction, Navigator agent, potentially GRPO training). Phase 4 should evaluate feasibility and cost.

### Priority 6: Add Self-Calibrated Confidence Signals (Phase 4 Research)

**Sources:** Huang et al. (2026), Asai et al. (2023), Shahani (2026, Chapter 9)

**Recommendation:** Add confidence signals to Lyra's outputs using either:
- Lightweight: prompt-based self-evaluation (REFINE pattern from SELF-RAG: ask "Is this output fully supported by the evidence?" and score the Yes token probability)
- Medium: CaTS-style LoRA fine-tuning for calibrated confidence on Lyra-specific tasks
- Full: reflection token vocabulary (ISSUP/ISUSE/ISREL) if fine-tuning is feasible

Use confidence signals to: (a) gate whether to surface output to user or re-query, (b) decide when to escalate for human review, (c) weight votes in multi-agent consensus.

**Rationale:** Confidence calibration enables adaptive compute allocation (spend more on uncertain queries) and trust calibration (users need to know when Lyra is guessing). CaTS saves 94.2% of samples by early-stopping on high-confidence outputs. However, the training pipeline (SSC labeling + LoRA SFT) adds complexity; prompt-based self-evaluation provides a lightweight starting point.

### Priority 7: Implement Longitudinal Cross-Run Learning (Phase 4 Plan)

**Sources:** Liu et al. (2026), AutoResearchClaw EvolutionStore

**Recommendation:** Implement a lesson store that:
1. Extracts structured lessons from failures, repairs, and verification results
2. Classifies by category and severity s(l) in (0, 1]
3. Weights by time-decay: w(l) = s(l) * exp(-ln(2) * delta_t / T_half) where T_half = 30 days
4. Injects as natural-language overlays into stage prompts

**Rationale:** Lyra currently starts every run from scratch. The lesson store provides +0.48 quality and +1 completion in AutoResearchClaw ablation. The 30-day half-life prevents contradictory advice accumulation. Low infrastructure cost (JSONL-backed, no model retraining).

---

## Source Index

| ID | Short Citation | Full Reference |
|---|---|---|
| P1 | Kong et al., 2026 | Kong, L. et al. "AI for Auto-Research: Roadmap and User Guide." arXiv:2605.18661v1, May 2026. 270+ systems surveyed. |
| P2 | Sen et al., 2026 | Sen, S. et al. "Is Grep All You Need? How Agent Harnesses Reshape Agentic Search." arXiv:2605.15184v1, May 2026. PwC. |
| P3 | Zhao et al., 2026 | Zhao, X. et al. "AUTO REPRODUCE: Automatic AI Experiment Reproduction with Paper Lineage." arXiv:2505.20662v4, Apr 2026. Tsinghua/OpenBMB. |
| P4 | Hao et al., 2023 | Hao, S. et al. "Reasoning with Language Model is Planning with World Model (RAP)." arXiv:2305.14992v2, Oct 2023. UCSD/MBZUAI. |
| P5 | Xu et al., 2026 | Xu, N. et al. "When Agents 'Misremember' Collectively: Exploring the Mandela Effect in LLM-based Multi-Agent Systems." arXiv:2602.00428v2, ICLR 2026. Zhejiang University. |
| P6 | Liu et al., 2024 | Liu, X. et al. "AGENTBENCH: Evaluating LLMs as Agents." arXiv:2308.03688v3, ICLR 2024. Tsinghua/Ohio State/UC Berkeley. |
| P7 | Qi et al., 2026 | Qi, J. et al. "Towards Trustworthy Agentic AI: A Comprehensive Survey." arXiv:2605.23989v1, May 2026. CUHK/Fudan/SAIS. |
| P8 | Wu et al., 2025 | Wu, J. et al. "Agentic Reasoning: A Streamlined Framework for Enhancing LLM Reasoning with Agentic Tools." arXiv:2502.04644v2, 2025. Oxford/NUS/CMU. |
| P9 | Yao et al., 2023 | Yao, S. et al. "Tree of Thoughts: Deliberate Problem Solving with Large Language Models." arXiv:2305.10601v2, NeurIPS 2023. |
| P10 | Huang et al., 2026 | Huang, C. et al. "CaTS: Calibrated Test-Time Scaling for Efficient LLM Reasoning." ICLR 2026. WashU/CMU/UW. |
| P11 | Merrill et al., 2026 | Merrill, M.A. et al. "Terminal-Bench 2.0: Benchmarking Agents on Hard, Realistic Tasks in CLIs." arXiv:2601.11868v1, Jan 2026. 90+ authors. |
| P12 | Asai et al., 2023 | Asai, A. et al. "SELF-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection." arXiv:2310.11511v1, Oct 2023. UW/AI2/IBM. |
| P13 | Kim et al., 2025 | Kim, H. et al. "NEXUSSUM: Hierarchical LLM Agents for Long-Form Narrative Summarization." arXiv:2505.24575v1, May 2025. CJ Corporation. |
| P14 | Ruan et al., 2026 | Ruan, J. et al. "MTR-SUITE: A Framework for Evaluating and Synthesizing Conversational Retrieval Benchmarks." arXiv:2605.20729v1, May 2026. NEU/Meituan/NiuTrans/Tsinghua. |
| P15 | Liu et al., 2026 | Liu, J. et al. "AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration." arXiv:2605.20025v2, May 2026. UNC-Chapel Hill et al. (35 authors, 12 institutions). |
| P16 | Zhang et al., 2026 | Zhang, Z. et al. "Argus: Evidence Assembly for Scalable Deep Research Agents." arXiv:2605.16217v3, May 2026. MiroMind AI. |
| P17 | Liu et al., 2025 | Liu, X. et al. "Select, Read, and Write: A Multi-Agent Framework of Full-Text-based Related Work Generation." arXiv:2505.19647v1, May 2025. Renmin University. |
| P18 | Liao et al., 2025 | Liao, Y. et al. "ReflecTool: Towards Reflection-Aware Tool-Augmented Clinical Agents." arXiv:2410.17657v3, Jun 2025. SJTU/Shanghai AI Lab/Fudan. |
| B1 | Shahani, 2026 | Shahani, R. "Building Reliable AI Systems: Applications and Agents You Can Trust." MEAP V12, Manning Publications, 2026. Chapters 3, 4, 6, 8, 9. |
| W1 | Wu, 2026 | Wu, C.-I. "academic-research-skills." v3.11.1 (2026-06-06). github.com/Imbad0202/academic-research-skills. CC BY-NC 4.0. |
| W2 | AIMING Lab, 2026 | AIMING Lab. "AutoResearchClaw." github.com/aiming-lab/AutoResearchClaw. |
| W3 | Cheng et al., 2026 | Cheng, R. et al. "Mapping the Design Space of User Experience for Computer Use Agents." arXiv:2602.07283, IUI 2026. Apple ML Research. |
