# Evaluation, Benchmarks & Testing -- Thematic Synthesis

**Cross-referenced from:** 281 paper rigor notes, 80 book notes, 184 web/repo notes
**Date:** 2026-06-07

---

## 1. Frontier Techniques (ranked by evidence strength)

### 1.1 Execution-Based Functional Correctness Evaluation (over trajectory matching)

- **Technique:** Programmatic state inspection -- evaluate agent outcomes by comparing final system state against ground truth, not by matching action sequences.
- **Sources:**
  - WebArena (2307.13854v4, ICLR 2024) -- `r_prog(s)` with DB queries, JS selectors, API calls
  - OSWORLD (2404.07972v2, ICLR 2024) -- 134 unique evaluation functions, getter-evaluator pipeline
  - tau-bench (2406.12045v1, arXiv 2024) -- `r = r_action * r_output` with DB state comparison
  - BLADE (2408.09667v3, arXiv 2025) -- Column-level data-flow-graph matching with value-exact + fuzzy isomorphism
- **Mechanism:** For each task, define (a) *locators* that retrieve goal-relevant state from the system (database contents, file system, DOM tree, a11y tree), then (b) *predicates* that check whether the located state satisfies the intent requirements. This is formalized as a POMDP `(S, A, T, R, O)` with reward `R: S * A -> [0,1]` measuring end-state correctness. Any valid agent execution path that produces the correct final state gets full credit.
- **Evidence:**
  - WebArena: Humans 78.24%, GPT-4 CoT 14.41% -- 5.4x gap
  - OSWORLD: Humans 72.36%, GPT-4 (a11y tree) 12.24% -- 5.9x gap
  - tau-bench (retail): GPT-4o 61.2%, Claude-3-Opus 44.2%, pass^8 < 25%
  - BLADE: GPT-4o Agent F1 44.8%, statistical model precision universally <35%
  - Human-AI gap of 60-93 percentage points persists across all benchmarks -- no benchmark is close to saturation
- **Maturity:** Production-deployed in evaluation-only context (leaderboards); not deployed as continuous agent-in-the-loop evaluation. Three ICLR papers + one under-review preprint establish strong academic consensus.

### 1.2 POMDP-Based Multi-Environment Agent Benchmarking

- **Technique:** Formalize all agent tasks as Partially Observable Markov Decision Processes with `(S, A, T, R, U, O)`, then evaluate across diverse environments with weight-normalized scoring.
- **Sources:**
  - AgentBench (2308.03688v3, ICLR 2024) -- 8 environments, 3 categories, weight normalization
  - tau-bench (2406.12045v1) -- 2 domains (retail + airline), POMDP with LM-simulated users
  - SILO-BENCH (2603.01045v2, ACL 2026) -- 30 tasks, 3 communication protocols, 6 agent scales
- **Mechanism:** Each environment is governed by a POMDP with action space A, observation space O (screenshots/a11y tree/DOM/API responses), deterministic or stochastic transition T, and reward function R. Weight normalization prevents high-variance tasks from dominating: `Overall = (1/N) * sum(score_i / weight_i)` where `weight_i` = reciprocal of average score across all models on task i. Agent failure is categorized into a taxonomy (Completed, Context Limit Exceeded, Invalid Format, Invalid Action, Task Limit Exceeded).
- **Evidence:**
  - AgentBench: gpt-4 overall 4.01 (weighted), best OSS codellama-34b 0.96 -- 4.5x API/OSS gap
  - AgentBench failure analysis: 37.9% completed, 23.9-82.5% TLE by environment, >90% of TLE from repetition
  - SILO-BENCH: DeepSeek-V3.1 36.9% SR overall; 11.7% on Level-III (global shuffle); 0% at N >= 50 on Level-III
  - SILO-BENCH discovery: Spontaneous leader emergence causes 0% SR on Level-III vs 33.3% without -- centralization creates bottlenecks
- **Maturity:** Published at top venues (ICLR, ACL). AgentBench evaluation toolkit is open-source with Docker-isolated task servers. SILO-BENCH introduces the Communication-Reasoning Gap and Relative Coordination Cost (RCC) metrics not yet adopted by other benchmarks.

### 1.3 The pass^k Reliability Metric (over pass@k)

- **Technique:** Measure the probability that an agent succeeds on ALL k independent trials of the same task, instead of pass@k which measures best-of-k. This captures consistency/reliability rather than best-case discovery.
- **Source:** tau-bench (2406.12045v1, Sierra/Princeton, arXiv 2024)
- **Mechanism:**
  ```
  pass^k = E_task [ (c choose k) / (n choose k) ]
  ```
  Where n = total trials, c = successful trials. Uses unbiased combinatorial estimator. This is fundamentally different from pass@k: pass@k measures whether at least one trial succeeds (optimistic upper bound); pass^k measures whether all k trials succeed (pessimistic lower bound, capturing variance).
- **Evidence:**
  - GPT-4o on tau-retail: pass^1 = 61%, pass^2 = 50%, pass^4 = 35%, pass^8 < 25%
  - Even the best model fails to solve the same task 8/8 times for >75% of tasks
  - This exposes brittleness that average success rates hide entirely
- **Maturity:** Research concept. One paper proposes it; no other benchmark has adopted it. Requires running many trials per task, multiplying evaluation cost by k. Strong conceptual value but limited adoption.

### 1.4 LLM-as-Judge with Structured Validation

- **Technique:** Use a separate LLM (typically GPT-4 class) as an automated judge for evaluating open-ended agent outputs, with rigorous validation against human judgments and structured output formats.
- **Sources:**
  - WebArena (2307.13854v4) -- GPT-4-0613 fuzzy_match judge, 100% accuracy on date/time formats
  - WorldMemArena (2605.29341v2) -- GPT-5.4-mini judge for memory quality, stage-specific metrics
  - BLADE (2408.09667v3) -- GPT-4o for semantic CV/model matching, 92-97% validated correctness on 615-sample audit
  - UA-Bench (2604.17293v1) -- gpt-4o-mini judge for answer correctness, 1/100 error on manual audit
  - Book: *Agentic AI for Engineers* (Ch.13) -- recommends LLM-as-Judge as external evaluation layer, paired with human samples for calibration
- **Mechanism:** An LLM is prompted with the question, ground truth, and model answer with structured output (Yes/No, JSON, or categorical labels). Validation is done by sampling a subset and comparing LLM judgments against human expert judgments. The key insight is that LLM-as-judge must be *validated, not trusted* -- every benchmark reports human-agreement rates. Best practice: use a different model from the same provider or a stronger model as judge (to avoid self-preference bias).
- **Evidence:**
  - WebArena: GPT-4 fuzzy_match = 100% date/time format accuracy
  - BLADE: 93% CV matching, 92% model matching, 97% code-to-transform conversion
  - UA-Bench: 1/100 errors on answer judging (paraphrased answer)
  - WorldMemArena: Systematic LLM-judge across memory correctness, hallucination, QA correctness, retrieval coverage
- **Maturity:** Widely deployed in research. ICLR 2024 benchmarks established pattern. Limitation acknowledged: potential systematic bias when judge and model share architecture/provider.

### 1.5 Calibrated Confidence for Agent Self-Assessment

- **Technique:** Fine-tune LLMs to produce calibrated probability estimates P(correct | answer) using a small corpus of graded outputs with Jensen-Shannon Divergence regularization, then use these scores for selective prediction, routing, and autonomy gating.
- **Sources:**
  - Calibration-Tuning (2406.08391v3, NeurIPS 2024) -- LoRA + Prompt with JSD regularization
  - CaTS (ICLR 2026, paper ID 8078) -- Self-Calibration via Soft Self-Consistency distillation
  - UA-Bench (2604.17293v1) -- Data vs. Model uncertainty taxonomy
  - Book: *30 Agents Every AI Engineer Must Build* (Ch.14) -- "Implement Calibrated Confidence and Audience-Appropriate Explanations"
- **Mechanism:**
  1. Generate graded dataset: produce answers via greedy decoding, grade correctness with auxiliary LLM (GPT-3.5/4), hold out calibration set
  2. Fine-tune with LoRA (r=8, alpha=32) + JSD regularization against base model distribution:
     ```
     Loss = CrossEntropy(y_hat, y) + kappa * JSD(p_theta0 || q_theta)
     JSD(p||q) = 0.5[KL(p||m) + KL(q||m)], m = 0.5(p+q)
     ```
     Without regularization: ECE = 29.9%. With JSD: ECE = 10.8%.
  3. For test-time scaling (CaTS): Distill Soft Self-Consistency from K=32 samples into single-pass confidence
  4. At inference: output P(correct) for each action, use for selective routing and early stopping
- **Evidence:**
  - Calibration-Tuning: ECE 35% -> 10% on OE MMLU, AUROC 55% -> 72%
  - Cross-model transfer: Mistral-7B estimating LLaMA-2-7B's correctness >= LLaMA estimating itself (AUROC 0.72 vs 0.68)
  - Data efficiency: ~1,000 labeled examples suffice; diminishing returns after 5,000
  - CaTS: 94.2% sample savings to reach same accuracy on MathQA; +5-15pp accuracy gain at same budget
  - UA-Bench: Thinking-mode models can achieve 0% Model-Uncertain F1 while maintaining high accuracy -- a critical safety warning
  - User study (N=181): Calibrated confidence enables users to modulate reliance; zero-shot prompts produce undifferentiated mass
- **Maturity:** Lab validated. NeurIPS + ICLR publications. Open-source code for Calibration-Tuning. Not widely deployed in production agent systems (most still use raw probabilities or uncalibrated heuristics).

### 1.6 Cost-Quality Routing with Preference Data

- **Technique:** Train a lightweight router (matrix factorization or BERT) on pairwise human preference data (Chatbot Arena) to dynamically select between expensive strong models and cheap weak models, achieving 87-95% of strong-model quality at 2-3.66x cost reduction.
- **Source:** RouteLLM (2406.18665v4, ICLR 2025, UC Berkeley/Anyscale/Canva)
- **Mechanism:**
  - Win prediction model: `P_theta(wins|q)` estimates probability strong model beats weak model on query q
  - Routing decision: `R^alpha(q) = M_weak if P(wins|q) < alpha else M_strong`
  - Four architectures: Similarity-Weighted (Bradley-Terry, no training), Matrix Factorization (8GB GPU), BERT (2x L4), Causal LLM (8x A100)
  - Data augmentation: golden-labeled (MMLU answer comparison) + LLM-judge labeled (GPT-4 on open-ended)
  - Metrics: Performance Gap Recovered (PGR), Call-Performance Threshold CPT(x%)
- **Evidence:**
  - MT Bench: Matrix Factorization CPT(50%) = 13.40% of calls to strong model needed for 95% of GPT-4 quality -- 3.66x cost savings
  - MMLU: SW Ranking CPT(50%) = 35.40%, 1.41x savings at 92% GPT-4 quality
  - Cross-model generalization: works on Claude Opus/Sonnet and Llama-3.1-70B/8B without retraining
  - Router overhead < 0.4% of LLM generation cost
  - Outperforms commercial routers (Unify AI, Martian) by up to 40% fewer strong-model calls
- **Maturity:** Production-deployable. Open-source framework. ICLR 2025. Requires preference data collection for target domain.

### 1.7 Self-Evolving Evaluation via Internal Consensus (No Human Labels)

- **Technique:** Use a model's own diverse reasoning traces (K>1 samples) to generate pseudo-labels via majority voting, then train the model against these pseudo-labels in a GRPO fidelity-reward loop, enabling self-improvement on evaluation tasks without ground truth.
- **Source:** EvoQuality (2509.25787v4, ICLR 2026, CityU HK/ByteDance)
- **Mechanism:**
  1. Offline: For each pair of unlabeled inputs, query model K=32 times, majority-vote to produce pseudo-label p*
  2. Online: Query model K=32 times for direct scores, compute fidelity reward via Bhattacharyya coefficient between pseudo-label and predicted probability:
     ```
     r_k(x_i) = (1/|P_i|) * sum_{j in P_i} [ sqrt(p*(x_i,x_j) * p_k(x_i,x_j)) + sqrt((1-p*(x_i,x_j)) * (1-p_k(x_i,x_j))) ]
     ```
  3. Update policy via GRPO (critic-free PPO variant): `loss = -(1/BK) * sum_i sum_k [min(ratio * advantage, clip(ratio, 1-eps, 1+eps) * advantage) - beta * D_KL(pi || pi_ref)]`
  4. Iterate: updated policy becomes base for next round's offline voting
- **Evidence:**
  - +31.8% weighted-average PLCC gain over base VLM across 8 diverse IQA benchmarks
  - Outperforms ALL supervised VLM-based models on OOD generalization (WAVG 0.762 vs 0.704)
  - +77.4% improvement on hardest benchmark (TID2013)
  - Regression-based self-evolution STALLS after Round 1 (0.736); ranking-based continues improving (0.770)
  - K=32 voting budget is most stable; K=1 produces baseline-level performance
- **Maturity:** Lab validated (ICLR 2026). Only tested on image quality assessment. The self-consistency voting + GRPO pattern is generalizable to other evaluation domains but not yet demonstrated.

### 1.8 Four-Stage Memory Lifecycle Evaluation

- **Technique:** Decompose agent memory evaluation into four observable stages (Write, Maintain, Retrieve, Use) with stage-specific metrics and per-stage failure attribution, enabling targeted diagnosis of memory pipeline breakdowns.
- **Source:** WorldMemArena (2605.29341v2, arXiv June 2026, UCSB/JP Morgan/ETH/Stanford/CMU)
- **Mechanism:**
  - Stage 1 (Observe-to-Write): Memory Recall, Correctness, Hallucination, Irrelevance
  - Stage 2 (Update-Maintain): Update Handling score = `(1.0*N_updated + 0.5*N_both + 0.0*N_outdated) / N_total`, Interference Rejection
  - Stage 3 (Retrieve): Retrieval Coverage (LLM-judge), Recall@K, NDCG@K with graded relevance
  - Stage 4 (Use-Act): QA-Correct, QA-Hallucination, QA-Omission, F1, BLEU-1
  - Unified adapter interface: 7-method MemoryAdapter (reset, ingest_turn, end_session, snapshot_memories, export_memory_delta, retrieve, get_capabilities)
- **Evidence:**
  - DeepSeek V4 QA-C: 69.13% (best); Claude Haiku 4.5: 36.71% (worst among long-context)
  - Memory Recall and QA-C are *decoupled*: Qwen3-VL-Embedding-8B 86.22% Recall -> 51.86% QA-C. MemGPT 85.20% Recall -> 57.81% QA-C
  - Update handling capped at ~59% across all systems -- append-dominant
  - Interference rejection: 23.42% (M2A) to 58.94% (A-Mem) -- 2.5x spread
  - Latency: 78x difference between fastest (M2A, 10.0s) and slowest (SimpleMem, 786.3s)
  - All systems drop 5-15pp on Agentic Execution vs Lifelong Evolution
  - Key failure pattern: "Snowball collapse" -- early omissions compound into later failures
- **Maturity:** Research concept. Single preprint (June 2026). No other benchmark decomposes memory this way. The diagnostic framework is paradigmatic but not yet replicated.

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy Signal | Latency | Memory/Compute Cost | Implementation Complexity | Scalability | Evidence Strength |
|---|---|---|---|---|---|---|
| **Execution-Based Evaluation** (WebArena/OSWORLD) | Highest -- objective ground truth | Low (post-hoc check) | High (Docker/VM infra, per-task evaluators) | High (custom getter+predicate per task) | Moderate (scales to 100s of tasks) | Strongest -- 4 independent papers, ICLR x3 |
| **POMDP Multi-Env Benchmarking** (AgentBench) | High -- weight-normalized cross-task | Moderate (HTTP round-trip per action) | High (Docker+MySQL+Virtuoso+pybind) | High (multi-server architecture) | Moderate (8 envs, tested 29 models) | Strong -- ICLR, open-source toolkit |
| **pass^k Reliability** (tau-bench) | Best signal for production readiness | High (k trials per task) | Very High (k * baseline cost) | Low (runs existing benchmark k times) | Low (cost multiplies linearly with k) | Moderate -- 1 paper, not yet replicated |
| **LLM-as-Judge** | Good when validated (92-100% human agreement) | Low (single API call) | Low-Moderate (API cost) | Low (prompt engineering) | Very High (works for any open-ended output) | Strong -- used by all major benchmarks |
| **Calibrated Confidence** (Calibration-Tuning) | ECE 35% -> 10%, AUROC 55% -> 72% | Negligible (single forward pass) | Moderate (1-3 GPU days training) | Moderate (LoRA + JSD reg) | High (1000 samples sufficient) | Strong -- NeurIPS + ICLR, user study |
| **Cost-Quality Routing** (RouteLLM) | 87-95% strong-model quality at 2-3.66x savings | <0.4% overhead | Low (8GB GPU for best router) | Low (SW Ranking: no training) | High (generalizes to unseen model pairs) | Strong -- ICLR, open-source, outperforms commercial |
| **Self-Evolving Eval** (EvoQuality) | +31.8% avg gain over base | Very High (K=32 sampling x 2 stages) | Very High (8x A100, 12 hrs/epoch) | High (GRPO training loop) | Low (requires in-domain unlabeled corpus) | Moderate -- ICLR, 1 domain only |
| **Memory Lifecycle Eval** (WorldMemArena) | Diagnostic (4-stage attribution) | Low (post-hoc analysis) | Low (analyzes existing memory ops) | Moderate (instrumentation, not rewrite) | Moderate (adapter interface, tested 15 systems) | Emerging -- 1 preprint, strong framework |

---

## 3. Convergences (Where multiple independent sources agree)

### 3.1 POMDP is the universal evaluation formalism
**Agreement across:** AgentBench (2308.03688v3), OSWORLD (2404.07972v2), WebArena (2307.13854v4), tau-bench (2406.12045v1)

All four ICLR-level benchmarks independently converged on the same mathematical framework: POMDP `(S, A, T, R, O)`. This is not coincidence -- it is the result of each group discovering that partial observability, stochastic transitions, and state-based reward are necessary to model real agent tasks. This is the strongest convergence signal in agent evaluation.

### 3.2 Execution-based evaluation is strictly superior to trajectory matching
**Agreement across:** WebArena, OSWORLD, BLADE, tau-bench, book: *Agentic AI for Engineers* (Ch.13)

Five independent sources agree: comparing agent actions to a gold-standard trajectory (surface-form matching) penalizes valid alternative paths. Evaluating final system state (correctness of outcome regardless of path) is the standard. BLADE adds fuzzy graph isomorphism matching as a principled intermediate solution when exact state matching is infeasible.

### 3.3 The human-AI gap is the metric that matters most
**Agreement across:** GAIA (92% vs 15%, 77pp gap), OSWORLD (72.36% vs 12.24%, 60pp gap), WebArena (78.24% vs 14.41%, 64pp gap), tau-bench (<50% even for GPT-4o), BLADE (human N/A, best AI 44.8%), SILO-BENCH (36.9% best multi-agent SR)

Every benchmark that reports human baselines shows a gap of 50-80+ percentage points. No AI system is close to human-level agent performance on any benchmark that actually measures agent capability (as opposed to knowledge recall). This gap guarantees at least 3-5 years of benchmark relevance before saturation.

### 3.4 LLM-as-judge is necessary but must be validated per-task
**Agreement across:** WebArena, BLADE, WorldMemArena, UA-Bench, book: *Agentic AI for Engineers* (Ch.13)

All major benchmarks use LLM-as-judge for open-ended evaluation but explicitly validate against human judgments. Typical validation numbers: 92-100% agreement on structured outputs, dropping to unknown reliability on complex semantic judgments. WorldMemArena uses GPT-5.4-mini across all metrics and acknowledges systematic risk. Consensus: LLM-as-judge is the best available tool but requires per-benchmark calibration.

### 3.5 Calibrated confidence is prerequisite for agent autonomy
**Agreement across:** Calibration-Tuning (2406.08391v3, NeurIPS), CaTS (ICLR 2026), UA-Bench (2604.17293v1), book: *30 Agents Every AI Engineer Must Build* (Practice 14), book: *Agentic Architectural Patterns* (Trust Scoring)

Papers show that (a) base LLMs are poorly calibrated (ECE 13-35%), (b) JSD-regularized fine-tuning with ~1,000 labeled examples reduces ECE to ~10%, and (c) thinking-mode optimization can catastrophically destroy self-awareness (MU-F1 84.8% -> 0.0% on Qwen3-235B). Books add that calibrated confidence must be audience-appropriate and integrated into autonomy gating. Five independent sources converge: do not deploy autonomous agents without calibrated confidence.

### 3.6 Multi-trial consistency (not just average success) defines production readiness
**Agreement across:** tau-bench (pass^k metric), book: *Agentic AI for Engineers* (Ch.13, "behavioral bounds"), book: *30 Agents* (A/B testing with completion rate), book: *Agentic Architectural Patterns* (Canary Agent Testing)

The academic paper (tau-bench) formalized it as pass^k; the engineering books operationalize it as "behavioral bounds testing," A/B testing on task completion rate, and canary deployments with regression detection. The convergence is clear: average success rate is insufficient for deployment decisions.

---

## 4. Contradictions (Where sources disagree -- needing arbitration)

### 4.1 Chain-of-Thought: Performance booster vs. self-awareness destroyer
- **Pro-CoT:** WebArena shows CoT +2.34pp over direct prediction. SWE-Search shows CoT backbone necessary for effective search. CaTS shows thinking improves calibration on most benchmarks.
- **Anti-CoT:** UA-Bench (2604.17293v1) shows thinking-mode optimization drops Model-Uncertain F1 from 84.8% to 0.0% on Qwen3-235B. The model becomes *more confidently wrong*, unable to recognize its own capability limits.
- **Resolution needed:** This is the most important open contradiction. If Lyra implements chain-of-thought/extended reasoning, it MUST simultaneously evaluate uncertainty self-awareness. The two cannot be optimized independently. Possible resolution: RL-UA-style training (GRPO with 3-valued reward +1/0/-1) explicitly training honesty alongside reasoning ability.

### 4.2 Multi-agent debate: Hallucination fighter vs. consensus derailer
- **For debate:** Dialectic-Med (2604.11258v1) shows 3-agent adversarial debate reduces object-level hallucination by 46.3% (CHAIR_I), improves accuracy by +8.18%. SWE-Search shows discriminator debate improves selection accuracy from 73% to 84%.
- **Against debate:** SILO-BENCH (2603.01045v2) shows spontaneous leader emergence on Level-III tasks causes 0% SR (vs 33.3% without leaders). Consensus failure is the #2 failure mode (29.9%) in multi-agent coordination.
- **Resolution needed:** Debate works when the debate is over a shared ground-truth reference (image pixels, test results). It fails when there is no external ground truth and agents must synthesize distributed partial information. Lyra should implement debate with explicit grounding anchors (code execution results, test outputs, AST analysis), never purely semantic debate.

### 4.3 Larger models: Better agents vs. worse calibration
- **Better agents:** AgentBench shows 4.5x commercial/OSS gap. OSWORLD shows GPT-4 12.24% vs GPT-3.5 2.69% (4.5x). WorldMemArena shows DeepSeek V4 69.13% vs Claude Haiku 4.5 36.71%.
- **Worse calibration:** UA-Bench shows Claude Sonnet 4 has better uncertainty attribution (AVG-F1 84.4%) than GPT-5 mini (AVG-F1 74.9%). Qwen3-8B has terrible MU-F1 (4.0%) despite decent DU-F1 (69.8%). Mistral-7B estimates LLaMA-2-7B's uncertainty *better than LLaMA estimates itself* (AUROC 0.72 vs 0.68).
- **Resolution needed:** Capability and calibration are orthogonal axes. Lyra must evaluate both independently for every model. A capability benchmark score does not imply calibration quality. Use cross-model uncertainty estimation (stronger model estimating weaker model's errors) as a cost-effective calibration strategy.

### 4.4 LLM-simulated users: Essential realism vs. evaluation noise
- **For simulation:** tau-bench builds entire evaluation around GPT-4-simulated users. AnnaAgent (2506.00551v2) shows LM-simulated seekers produce realistic, diverse interactions when guided by dynamic state modulation.
- **Against simulation:** tau-bench itself acknowledges the user simulator (GPT-4-0613) has limited reasoning capability and may miss edge cases. The paper notes "Users may authorize suboptimal choices without double-checking agent recommendations." GAIA deliberately avoided simulation by using a human-validated question bank.
- **Resolution needed:** Use LM-simulated users for scale and diversity, but calibrate against human-in-the-loop benchmarks with a small validation set. The tau-bench pattern (observe beta-test real deployments, annotate tasks based on trajectory analysis) provides a practical middle ground.

---

## 5. Open Problems (What NO source solves yet)

### 5.1 No benchmark evaluates agent trajectory quality (only outcomes)
Every major benchmark (AgentBench, WebArena, OSWORLD, GAIA, tau-bench, BLADE) scores final answers or final system state. None evaluates whether the agent took an efficient, safe, or well-reasoned path. An agent that tries 15 random actions then accidentally succeeds gets the same score as an agent that plans carefully and executes perfectly. BLADE's column-level partial credit is the only partial exception.

### 5.2 No benchmark tests multi-session state persistence with realistic decay
WorldMemArena tests memory across sessions in simulated environments, but no benchmark tests whether an agent correctly maintains user preferences, learned patterns, and world-state across real multi-day deployment with intervening events, model updates, and infrastructure changes. This is the gap between "evaluation" and "production monitoring."

### 5.3 No evaluation framework accounts for model behavior drift
GAIA notes "API model behavior changes over time" as a limitation. No benchmark has a mechanism for detecting when a model update silently changes benchmark scores without re-running the full suite. This is a fundamental measurement problem: benchmarks measure at a point in time, but models evolve continuously.

### 5.4 No standard for agent safety evaluation
OSWORLD explicitly excludes safety from evaluation. No major benchmark measures side effects, vulnerability exploitation, privacy violations, or policy compliance of agent actions. UA-Bench's uncertainty taxonomy is the closest, but it measures self-awareness, not behavioral safety. Book: *Agentic AI for Engineers* (Ch.8) provides a pre-deployment safety checklist but no automated evaluation protocol.

### 5.5 No benchmark evaluates agent learning across episodes
All benchmarks are zero-shot: each task is solved independently. No benchmark tests whether an agent *improves* from its mistakes across multiple episodes, or learns reusable skills. This is the gap between "benchmarking" and "autonomous improvement." The self-evolving systems literature (EvoQuality, ReasoningBank, SAGE) addresses this in narrow domains but has not been integrated into general agent benchmarks.

### 5.6 Pass^k is theoretically sound but practically prohibitive
The tau-bench pass^k metric captures exactly the reliability signal needed for production deployment, but requires k trials per task, multiplying evaluation cost by k. No solution exists for estimating pass^k from fewer samples or from trajectory-internal signals (e.g., agent confidence during execution).

---

## 6. Recommendations for Lyra

### Tier 1 -- Breakthrough (adopt immediately)

**R1. Build a POMDP-based execution-evaluation harness with functional correctness scoring.**
- **Sources:** WebArena (2307.13854v4), OSWORLD (2404.07972v2)
- **Rationale:** This is the consensus standard across all top-venue agent evaluation papers. Lyra currently relies on trajectory comparison and LLM-as-judge, both of which have known brittleness. A `StateInspector` abstraction (locators + predicates) providing objective, path-agnostic outcome evaluation should be the foundation.
- **Effort:** Moderate (3/5). Requires per-task evaluator engineering but the pattern is well-defined.

**R2. Implement calibrated confidence via LoRA fine-tuning on graded Lyra action outcomes.**
- **Sources:** Calibration-Tuning (2406.08391v3, NeurIPS 2024), CaTS (ICLR 2026), UA-Bench (2604.17293v1), book: *30 Agents* (Practice 14)
- **Rationale:** Calibrated confidence is the prerequisite for every autonomy decision Lyra makes -- when to retry, when to escalate, when to ask the user, when to route to a stronger model. Without it, autonomy gating is guesswork. The ~1,000-example data requirement and LoRA + JSD methodology are well-specified and cheap.
- **Effort:** Moderate (3/5). Requires constructing a graded corpus of Lyra action outcomes and 1-3 GPU days of training.

**R3. Deploy the AGENTBENCH failure taxonomy for Lyra agent trajectory analysis.**
- **Source:** AgentBench (2308.03688v3)
- **Rationale:** The five-category outcome classification (Completed, Context Limit Exceeded, Invalid Format, Invalid Action, Task Limit Exceeded) with Rouge-L >= 0.8 repetition detection provides a diagnostic dashboard that tells you *why* an agent fails, not just *how often*. This transforms binary pass/fail into actionable improvement signal.
- **Effort:** Low (2/5). Post-hoc classification pass on existing trajectories.

### Tier 2 -- High-Impact (prototype and evaluate)

**R4. Track pass^k reliability alongside pass@1 for Lyra's release qualification.**
- **Source:** tau-bench (2406.12045v1)
- **Rationale:** Average success masks reliability. A Lyra release candidate that achieves 80% pass@1 but only 20% pass^4 is not production-ready. Start with k=3 on Lyra's most critical tasks; expand to k=5-8 for release gates.
- **Effort:** Moderate (3/5). Requires multi-trial evaluation infrastructure but reuses existing benchmarks.

**R5. Implement RouteLLM-style cost-quality routing for Lyra's model selection.**
- **Source:** RouteLLM (2406.18665v4, ICLR 2025)
- **Rationale:** The 2-3.66x cost savings at 87-95% quality retention is directly applicable to Lyra's multi-model architecture. Train a matrix factorization router on Lyra's own eval harness results as preference data. Start with SW Ranking (no training required), upgrade to matrix factorization as data accumulates.
- **Effort:** Moderate (3/5). Open-source framework available.

**R6. Adopt the WorldMemArena four-stage memory lifecycle for Lyra's memory diagnostics.**
- **Source:** WorldMemArena (2605.29341v2)
- **Rationale:** Before building complex memory pipelines, Lyra needs the diagnostic vocabulary to determine whether memory actually works. The Write-Maintain-Retrieve-Use decomposition with stage-specific metrics enables targeted debugging of the most likely bottleneck (the retrieval-to-use bridge, where WorldMemArena shows the largest gap).
- **Effort:** Moderate (3/5). Instrumentation, not a rewrite.

### Tier 3 -- Investigate (worth exploring after Tier 1-2 are implemented)

**R7. Explore self-evolving evaluation via self-consistency voting (EvoQuality pattern).**
- **Source:** EvoQuality (2509.25787v4, ICLR 2026)
- **Rationale:** The ability to improve Lyra's judgment capabilities (code review quality, response ranking, hallucination detection) without human labels is transformative. But the pattern is only validated on image quality assessment. Prototype on a single Lyra judgment task (e.g., commit message quality ranking) before committing to a full self-evolution pipeline.
- **Effort:** High (4/5). Requires K=32 sampling infrastructure, GRPO training loop, and careful KL regularization.

**R8. Build the UA-Bench uncertainty taxonomy into Lyra's refusal/autonomy pipeline.**
- **Source:** UA-Bench (2604.17293v1)
- **Rationale:** Distinguishing data uncertainty (user request is ambiguous -> ask for clarification) from model uncertainty (request exceeds capability -> invoke tools/escalate) enables principled next-action routing instead of generic refusal. The finding that thinking-mode destroys self-awareness is a critical safety guardrail for any Lyra reasoning-mode implementation.
- **Effort:** Low-Moderate (2-3/5). Prompt engineering + structured output parsing.

**R9. Evaluate Lyra on GAIA-style "Proof of Work" internal benchmark tasks.**
- **Source:** GAIA (2311.12983v1)
- **Rationale:** A small set of ~50 Lyra-specific GAIA-style questions (multi-step, multi-tool, unambiguous factoid answer) provides a cheap, automatic, hard-to-game internal quality gate. The Proof-of-Work property (hard to solve, trivial to verify) enables continuous evaluation after every change.
- **Effort:** Moderate (3/5). Question design labor-intensive but methodology is fully documented.

**R10. Apply SILO-BENCH's RCC metric to Lyra's multi-agent workflows.**
- **Source:** SILO-BENCH (2603.01045v2, ACL 2026)
- **Rationale:** Track Relative Coordination Cost = 1 - SR(multi-agent)/SR(single-agent) as a health metric for Lyra's Team/Swarm modes. Spiking RCC signals coordination degradation and should trigger protocol reselection or scale reduction. Implement information sufficiency detection to prevent premature answer submission (37.2% failure mode).
- **Effort:** Low (2/5). Metric computation + sufficiency tracker (~200 lines of code).

---

## Source Index

### Papers (arXiv ID -> internal filename)
| Paper | ID | Venue | Key Contribution |
|---|---|---|---|
| AgentBench | 2308.03688v3 | ICLR 2024 | 8-environment POMDP benchmark, failure taxonomy, weight-normalized scoring |
| GAIA | 2311.12983v1 | arXiv 2023 | Proof-of-Work eval, human-AI gap measurement (92% vs 15%) |
| OSWORLD | 2404.07972v2 | ICLR 2024 | Real-VM execution-based eval, pyautogui action space, 369 tasks |
| WebArena | 2307.13854v4 | ICLR 2024 | Self-hosted Docker web eval, functional correctness, 812 instantiated tasks |
| tau-bench | 2406.12045v1 | arXiv 2024 | pass^k reliability metric, LM-simulated users, tool-agent-user POMDP |
| BLADE | 2408.09667v3 | arXiv 2025 | Scientific analysis eval, column-level data-flow-graph matching, partial credit |
| SILO-BENCH | 2603.01045v2 | ACL 2026 | Multi-agent coordination benchmark, Communication-Reasoning Gap, RCC metric |
| WorldMemArena | 2605.29341v2 | arXiv 2026 | Four-stage memory lifecycle eval, 15 systems compared, action-world loop |
| Calibration-Tuning | 2406.08391v3 | NeurIPS 2024 | LoRA + JSD calibration, ECE 35%->10%, cross-model transfer |
| CaTS | 8078_CaTS | ICLR 2026 | Self-Calibration via SSC distillation, 94.2% sample savings |
| RouteLLM | 2406.18665v4 | ICLR 2025 | Preference-data-driven cost-quality routing, 2-3.66x savings |
| EvoQuality | 2509.25787v4 | ICLR 2026 | Self-evolving eval via self-consistency voting + GRPO |
| UA-Bench | 2604.17293v1 | arXiv 2026 | Data vs. Model uncertainty taxonomy, thinking-mode destroys self-awareness |
| SWE-Search | 2410.20285v6 | ICLR 2025 | MCTS + hybrid value function + hindsight feedback for SWE |
| Dialectic-Med | 2604.11258v1 | Preprint 2026 | Adversarial falsification with visual grounding, 46.3% hallucination reduction |

### Books
| Book | Key Chapter / Practice |
|---|---|
| *Agentic AI for Engineers* (Ch.13) | 6 eval dimensions, failure-mode-to-guardrail mapping, behavioral bounds testing |
| *30 Agents Every AI Engineer Must Build* (Ch.14) | Calibrated confidence, ADL with Evaluation & Optimization phase, A/B testing for agents |
| *Agentic Architectural Patterns* (Ch.15-16) | Trust Scoring, Canary Agent Testing, Custom Evaluation Metrics (STEPScore) |
| *Agentic AI for Dummies* (Ch.9) | Technical monitoring: reasoning depth, confidence levels, action success rates, decision reversal frequencies |
| *Agentic AI Data Architectures* (Ch.7) | Living indexing, feedback-driven retrieval scoring, continuous eval instrumentation |

### Web / Repos
| Source | Key Takeaway |
|---|---|
| Alibaba-NLP/DeepResearch | Structured output LLM-as-judge with Pydantic models, Pass@3 evaluation |
| Aider-AI/aider | Auto-repair loop boosts pass rates from 57% to 77%; Exercism polyglot benchmark |
| Anthropic multi-agent research | Production deployment lessons for agent evaluation systems |
