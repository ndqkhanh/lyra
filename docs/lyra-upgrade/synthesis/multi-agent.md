# Multi-Agent Orchestration & Collaboration -- Thematic Synthesis

**Synthesis date:** 2026-06-07
**Sources consulted:** 22 notes (18 papers + 2 books + 2 web)
**Method:** Grep across 545 notes for multi-agent keywords, deep-read 22 most relevant, cross-referenced papers against books/repos.

---

## 1. Frontier Techniques (ranked by evidence strength)

### 1.1 Orchestrator-Worker Pattern with External Memory Persistence

- **Technique:** LeadResearcher (Opus-tier) spawns specialized subagents (Sonnet-tier) in parallel with persistent memory surviving context truncation.
- **Sources:**
  - Anthropic Engineering Blog: "How we built our multi-agent research system" (web, June 2025). LeadResearcher + subagent pattern. +90.2% performance gain over single-agent Opus 4.
  - FS-Researcher (paper, 2602.01566v2): Dual-agent persistent file-system workspace. RACE 53.94 vs. OpenAI-DR 46.45 (+7.49). Ablation: removing dual-agent separation drops RACE by 10.35 points.
  - 30 Agents Every AI Engineer Must Build (book): Standardizes the orchestrator-worker decomposition as the foundational multi-agent pattern.
- **Mechanism:** Orchestrator saves research plan to external memory (not context window), spawns 3-5 parallel subagents that return compressed findings via artifact-based filesystem output. Lead synthesizes results and iterates if needed. Subagents use interleaved thinking after tool calls. CitationAgent runs as final post-processing step.
- **Evidence:**
  - Multi-agent outperforms single-agent by 90.2% (Anthropic internal eval)
  - Parallelization cuts latency by up to 90% for complex queries
  - FS-Researcher: +7.49 RACE over OpenAI Deep Research; +10.35 RACE drop when dual-agent is removed
  - Effort-scaling heuristics validated: 1 agent for simple, 2-4 for comparisons, >10 for complex
- **Maturity:** Production deployed (Anthropic's research system is live). FS-Researcher is lab-validated with released code.

### 1.2 MCTS-Driven Multi-Agent Workflow Search and Optimization

- **Technique:** Monte Carlo Tree Search where nodes are agentic workflow configurations, LLM is the optimizer (proposing modifications), and evaluation scores are the reward signal. Extensions include multi-agent tree search with Thompson sampling and tree-consistent credit assignment.
- **Sources:**
  - AFlow (paper, 2410.10762v4): MCTS over code-represented workflows. +5.7% over human-designed baselines. GPT-4o-mini + AFlow outperforms GPT-4o at 4.55% of cost.
  - SWE-Search (paper, 2410.20285v6): MCTS for software agents with hindsight feedback. +23% mean improvement across 5 models.
  - MARS\$^2\$ (paper, 2604.14564v1): Multi-agent tree search with tree-consistent reward shaping. Qwen3-8B + MARS\$^2\$ = 58.3% Pass@1 vs. base 50.3% (+8.0). AReaL-14B with MARS\$^2\$ (64.6%) surpasses O4-Mini Low (63.7%).
  - MetaAgent-X (paper, 2605.14212v1): Hierarchical rollout (M designs x N executions) with stagewise co-evolution. Qwen3-8B RL-trained average 38.33% across 6 benchmarks vs. single-agent 27.16% (+11.17).
- **Mechanism:**
  - AFlow: MCTS with soft mixed probability selection + LLM-based expansion + experience backpropagation (UCB1). Workflows represented as Python classes.
  - MARS\$^2\$: Two-level Thompson sampling over agent-node pairs. Reward shaping: b(v) = (1-\$\lambda\$)r_parent + \$\lambda\$ \cdot \mu_siblings. Agent-specific parameters \$\Theta = \{\theta_1, ..., \theta_m\}\$ prevent policy collapse.
  - SWE-Search: Modified UCT with early depth bonus and late depth penalty. Hybrid value function: scalar reward + NL explanation for hindsight feedback.
- **Evidence:**
  - AFlow: 80.3% average across 6 benchmarks; 19.5% over prior automated method (ADAS)
  - SWE-Search: GPT-4o 31.0% vs. baseline 25.7% (+17% relative); cost 5-14x higher
  - MARS\$^2\$: Best average diversity rank (1.3). Single-agent search saturates; multi-agent avoids collapse.
  - MetaAgent-X: Outperforms MaAS by +6.11% (38.33 vs. 32.22 avg). Ablation: hierarchical rollout (M=4,N=4) beats flat (M=8,N=1) by 6.7% on AIME24.
- **Maturity:** Lab-validated with released code for all four systems. MARS\$^2\$ and MetaAgent-X have production-grade RL training infrastructure. Cost (5-14x inference) limits production deployment for standard use.

### 1.3 Structured Evidence DAG for Multi-Agent Evidence Assembly

- **Technique:** Multiple searcher agents feed evidence into a shared DAG where nodes are evidence/claims and edges are support/contradiction. A Navigator agent orchestrates verification and synthesis over the graph.
- **Sources:**
  - Argus (paper, 2605.16217v3): Evidence DAG with verification loop. Qwen3.5-35B-A3B backbone. K=8 parallel: BrowseComp 74.5%, GAIA 93.2% (+12.6 over best proprietary). 1200:1 context compression ratio.
  - Anthropic Engineering Blog (web): Subagents as intelligent compressors returning only relevant tokens.
- **Mechanism:** Navigator rewrites query into angle-diverse sub-queries, dispatches to parallel Searchers (stateless ReAct agents). Evidence nodes deduplicated at source-URL level. Claims labeled as supported/contradicted/unverified. Batched verification queries target gaps. Final synthesis traces every factual claim to source evidence. Trained with GRPO + contrastive reward: R = clip(R_w/v + \$\lambda\$ (R_w/v - R_w/o v), 0, 1).
- **Evidence:**
  - K=64 scales to 86.2% BrowseComp with 25.6M Searcher tokens compressed to 21.5K context tokens (1200:1)
  - Structured graph representation alone contributes +5.2 points over flat text
  - Cross-backbone generalization: Navigator trained on Qwen-35B transfers zero-shot to DeepSeek-V4-Flash-Max (+3.0) and Seed-2.0-Pro (+3.8)
  - Log-linear accuracy scaling with no sign of flattening at K=64
- **Maturity:** Lab-validated (64x H200 GPUs for 1.5 days training). Production-grade scaling properties demonstrated. No public production deployment known.

### 1.4 Recursive Latent-Space Multi-Agent Communication

- **Technique:** Agents communicate through continuous latent vectors via lightweight adapter layers (RecursiveLink) rather than decoding to text, enabling gradient-stable recursive refinement.
- **Sources:**
  - RecursiveMAS (paper, 2604.25917v1): 2-layer residual MLP (~13M params, 0.31% of total) bridges embedding spaces between heterogeneous agents. Training-free text generation during recursion; only final round decodes text.
  - Latent Agents / IMAD (paper, 2604.24881v1): Internalizes multi-agent debate into single-model latent space via GRPO with dynamic reward scheduling.
- **Mechanism:**
  - RecursiveMAS: Inner RecursiveLink maps last-layer hidden state back to input embedding for auto-regressive latent thought generation. Outer RecursiveLink projects between heterogeneous model dimensions. Stages: inner-loop cosine similarity training, then outer-loop end-to-end CE loss through full recursion trace.
  - IMAD: 3-stage pipeline: dataset construction from explicit debate -> SFT on debate traces -> GRPO with decaying format reward + shrinking length clip. Model learns to internalize debate because externalizing becomes impossible under token budget.
- **Evidence:**
  - RecursiveMAS at r=3 recursion rounds: +8.3% average over strongest baselines. 2.4x speedup, 75.6% token reduction vs. text-based recursive MAS.
  - AIME2025: RecursiveMAS 86.7% vs. Recursive-TextMAS 73.3% (+13.4). Training cost \$4.27 vs. Full-SFT \$9.67 with lower GPU memory (15.29 GB).
  - IMAD: LLaMA-3.1 8B GSM8K 85.20% vs. Debate 83.03% (+2.17) using only 11% of tokens (644 vs. 5758). 5-16x efficiency gain.
  - Agent subspaces discovered: +15.41% avg ROUGE-L AUC improvement under activation steering. Malicious traits suppressible to zero.
- **Maturity:** Lab-validated. RecursiveMAS tested across 4 collaboration patterns, 5 model families, 6 benchmarks. IMAD tested on arithmetic + GSM8K + MMLU-Pro + BBH. Both release code. Not known to be production-deployed.

### 1.5 Plan-Code Co-Evolution with Collaborative Decision-Making

- **Technique:** Three-agent system (Planner, Coder, Debugger) where the Debugger contains a Collaborative Decision-Making module that diagnoses whether errors originate from the plan or the implementation before choosing what to fix.
- **Sources:**
  - CollabCoder (paper, 2604.13946v2): Plan-Code Co-Evolution. Clears the SOTA across all baselines. GPT-4o mini backbone: HumanEval 96.34%, MBPP 91.69%, LiveCodeBench 41.96% (+14.7-20.5% relative over best baseline).
  - Agentic Reasoning (paper, 2502.04644v2): Three specialized agents (Web-Search, Coding, Mind-Map) that outperform single-model approaches on GPQA (81.2% vs. o3-mini-high 79.7%).
- **Mechanism:** CDM runs three parallel analyses (plan-level, code-level, plan-code alignment) producing confidence scores \$\phi_{i,d} \in [0,1]\$ per decision. Trust-weighted fusion (w_plan=0.4, w_code=0.3, w_align=0.3) decides whether to revise strategy or execution. Reasoning Trajectory module maintains accumulated debugging history to avoid repeating failed fixes. Complexity reduced from O(nk) to O(t).
- **Evidence:**
  - CollabCoder: 82.50% avg on Qwen2.5-Coder-32B vs. CodeSIM 80.22%. 30-57% token reduction vs. MapCoder. 4-10 fewer API calls per problem.
  - Benefits persist and scale: GPT-5.2 + CollabCoder = 95.21% MBPP, 65.18% LCB with 12,048/4,294 tokens I/O.
  - Ablation: removing CDM drops avg by -4.59; removing RT drops by -1.76. Both complementary.
  - Difficulty scaling: gap vs. baselines widens at harder levels (7 solved at 1600-1800 vs. 3-5 for baselines).
- **Maturity:** Lab-validated across 3 backbone models (Seed-Coder-8B, Qwen2.5-Coder-32B, GPT-4o-mini, GPT-5.2). Code released. The pattern generalizes beyond code generation to any domain needing plan-execution error attribution.

### 1.6 Hypothesis-Based Self-Organizing Agent Teams with Peer-Review Gating

- **Technique:** Agents self-organize into hypothesis-based teams, critique proposals before spending compute, and propagate champions through multi-seed noise-gated promotion.
- **Sources:**
  - AutoScientists (web/repo, 2605.28655): Decentralized multi-agent scientific experimentation. BioML-Bench 74.4% (+8.33% over single-agent). 1.9x faster to target metric on nanoGPT. 7 accepted improvements vs. 0 for single-agent.
  - AI Auto-Research Roadmap (paper, 2605.18661v1): 270+ systems cataloged; lifecycle framework identifies phase-boundary verification as the central reliability challenge.
- **Mechanism:** Orchestrator as pure coordinator (never runs experiments). Agents post [PROPOSAL] messages requiring at least one non-author comment before GPU queue entry. HEARTBEAT state machine with 6-part lifecycle per agent. Multi-seed noise gating confirms improvements before champion propagation. Self-regulating discussion triggers detect stagnation (0 KEEPs in 3+ rotations). Meta-improvement edits role templates every 3 cycles using diagnosed failure patterns.
- **Evidence:**
  - +8.33% over single-agent baseline on BioML-Bench (24 biomedical ML tasks)
  - 1.9x faster convergence to target validation metric (nanoGPT)
  - +12.5% on ProteinGym ACE2-Spike binding assay
  - Known failure modes from production runs: 20-40% duplicate proposal rates, agent activation failures, stale champion propagation
- **Maturity:** Production-validated for research use (multiple runs documented). Template bloat (1300+ line ROLE-ANALYST.md) and agent reliability issues documented as live concerns. Not deployed as a product.

### 1.7 Adversarial Debate-Based Multi-Agent Verification

- **Technique:** Structured adversary (Opponent agent) generates counterfactual probes grounded in verifiable evidence (not hallucination), Proponent revises hypotheses, Mediator adjudicates via consensus graph.
- **Sources:**
  - Dialectic-Med (paper, 2604.11258v1): 3-agent dialectic with Visual Falsification Module. GPT-5.1 backbone: MIMIC-CXR-VQA 76.28% vs. CoT 68.10% (+8.18%). Hallucination reduction: CHAIR_I -46.3% vs. GPT-4o.
  - Conjunctive Prompt Attacks (paper, 2604.16543v1): Identifies topology-dependent attack surfaces. ASR_max = 1.0 after optimization. Existing guard models (PromptGuard, Llama-Guard) rendered nearly useless.
  - Trustworthy Agentic AI survey (paper, 2605.23989v1): Defense-in-depth across lifecycle stages. Recommends 3-tier release gating with process metrics.
- **Mechanism:** Opponent generates counterfactual probes targeting specific contradictory evidence. Visual Falsification Module (PubMedCLIP-based) computes falsification attention maps to ground counter-arguments in pixel regions. Dynamic Consensus Graph with path integration: \$\Phi(h) = \sum_{\pi} \exp((1/|\pi|) \sum \log(w_{uv}))\$. Attack strength gates termination when S_attack < \$\theta_{thresh}\$.
- **Evidence:**
  - Dialectic-Med: +8.18% diagnostic accuracy over CoT on MIMIC-CXR-VQA. -46.3% object-level hallucination (CHAIR_I).
  - VFM removal causes largest single degradation (-9.31%), proving text-only debate is fundamentally inadequate in high-stakes domains.
  - Small model (8B) with debate beats larger model (32B) with CoT (70.35% vs. 68.96%).
  - Attack paper: conjunctive attacks achieve ASR_max=1.0 while keeping false activations near zero (0.07-0.09). System-level controls only reduce ASR by 15-20%.
- **Maturity:** Lab-validated with expert radiologist evaluation. Attack surface analysis is simulation-based. Not deployed in production clinical settings.

### 1.8 Cluster-Based Collaborative Agent Profiling

- **Technique:** Group agents/users by behavioral similarity via density-based clustering, then retrieve interaction histories from similar agents to enrich context for sparse/cold-start agents.
- **Sources:**
  - ClusterRAG (paper, 2605.18769v1): HDBSCAN clustering + ColBERTv2 similarity for collaborative profile retrieval. SOTA across all 6 LaMP tasks.
  - Build Multi-Agent System from Scratch (book): Recommends standardized tool interfaces, structured result types, and complete trajectory capture.
- **Mechanism:** User embedding via mean-pooled ColBERTv2 over profile documents. HDBSCAN auto-discovers cohort count. Intra-cluster similarity ranking identifies top-k similar users. Two-stage retrieval: cluster centroid matching then within-cluster reranking. In-Prompt Augmentation with budget formula allocates profile tokens.
- **Evidence:**
  - ClusterRAG-H wins on every metric across all 6 LaMP tasks. Only 2 profile documents needed vs. 4+ for baselines.
  - HDBSCAN Silhouette 0.535-0.601 vs. k-means 0.274-0.389.
  - Optimal k=3 similar users, m=6-7 profile docs.
- **Maturity:** Lab-validated on LaMP benchmark suite. English-only, text-only. No production deployment evidence.

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy Gain | Latency/Cost | Memory/Context Efficiency | Implementation Complexity | Scalability | Evidence Strength |
|-----------|--------------|-------------|--------------------------|---------------------------|-------------|-------------------|
| **Orchestrator-Worker + Memory** | +90.2% (vs. single-agent); +7.49 RACE | 90% latency reduction (parallel); ~15x tokens vs. chat | External memory survives context truncation | Medium (2 agents, file I/O, memory store) | Very high (effort-scaling heuristics) | Production-deployed |
| **MCTS Workflow Search** | +5.7-23% (task-dependent) | 5-14x inference cost increase | High token cost (MCTS tree size); mitigated by compression | High (MCTS controller, reward shaping, agent-specific parameters) | Medium (max 10-100 node budget) | Lab-validated (4 systems) |
| **Evidence DAG Assembly** | +12.6 GAIA over best proprietary | Log-linear accuracy scaling with compute; 1200:1 compression | Excellent (21.5K context for 25.6M searched tokens) | High (DAG construction, GRPO training, verification loop) | Excellent (K=64 tested, no ceiling) | Lab-validated, strong scaling |
| **Recursive Latent Communication** | +8.3% avg (vs. text recursion); 5-16x token reduction | 2.4x speedup; $4.27 training cost | 75.6% token reduction; latent states are opaque | Medium-High (RecursiveLink MLP, inner/outer training loop) | Medium (sub-10B models only; r=3 max recursion) | Lab-validated, theoretical guarantees |
| **Plan-Code Co-Evolution** | +11-20% relative on competitive coding | 30-57% token reduction vs. baselines | O(t) complexity vs. O(nk) for prior methods | Medium (3 parallel analyses, trust-weighted fusion, RT module) | High (scales to GPT-5.2, Qwen3-Coder-Next) | Lab-validated (5 backbones) |
| **Self-Organizing Teams** | +8.33% (BioML-Bench) | High Claude Code API cost (9 agents continuously) | Template bloat problem (1300+ line instructions) | High (state machine, message-board, peer-review protocol) | Medium (9-agent demonstrated) | Production run evidence |
| **Adversarial Debate Verification** | +8.18% diagnostic accuracy; -46.3% hallucination | 3-5x token overhead; 2.6 avg debate turns | Structured graph memory prevents lost-in-middle | Medium-High (VFM module, consensus graph, 3-agent loop) | Low (single-domain validation) | Lab-validated with expert eval |
| **Cluster-Based Profiling** | Consistent SOTA (all 6 LaMP tasks) | Offline clustering cost; two-stage retrieval latency | 2 profile documents vs. 4+; efficient cold-start | Medium (HDBSCAN, ColBERTv2, two-stage retrieval) | Medium (English-only, text-limited) | Lab-validated |

---

## 3. Convergences

Where multiple independent sources agree -- these are the safe bets.

### 3.1 Multi-Agent Systems Radically Outperform Single-Agent Baselines

**Convergence strength: Very high (5+ independent sources)**

- Anthropic Engineering Blog: +90.2% multi-agent vs. single-agent on internal research eval
- Agentic Reasoning: 3-agent system (Web-Search + Coding + Mind-Map) on GAIA: 66.13 vs. direct API 47.18 (18.95-point gap)
- FS-Researcher: Dual-agent decoupling adds +10.35 RACE points (largest single ablation drop)
- MetaAgent-X: RL-trained multi-agent system gains +11.17% avg over single-agent baseline across 6 benchmarks
- AI Auto-Research Roadmap: "Effective systems converge on layered architectures -- exploration + execution + verification layers"
- Terminal-Bench 2.0: Agent scaffolding gap matters as much as model choice (Gemini 2.5 Pro sees 17pp lift from Terminus 2 vs. OpenHands)

**Consensus claim:** The multi-agent architecture itself provides a first-order performance gain, independent of model quality. The gap between "has multi-agent architecture" and "does not" often exceeds the gap between different LLM backbones. This is the strongest convergence signal in the entire corpus.

### 3.2 Parallelization is the Dominant Efficiency Lever

**Convergence strength: High (4+ independent sources)**

- Anthropic: Parallel subagent spawning cuts latency by up to 90%
- Argus: Parallel Searcher scaling (K=1 to K=64) yields log-linear accuracy improvement with no observed ceiling
- MARS\$^2\$: Multi-agent tree search avoids the exploration collapse of single-policy training
- AutoScientists: Parallel hypothesis teams enable sustained search across diverse directions (7 accepted improvements vs. 0 single-agent)
- Build Multi-Agent System from Scratch (book): Async-first design as critical pattern; sync execution blocks the processing loop

**Consensus claim:** Parallelism is the primary scaling axis for multi-agent systems. The evidence shows that parallel subagent spawning + parallel tool calling yields the largest latency and capability improvements. Systems bottlenecked on synchronous agent coordination hit fundamental performance ceilings.

### 3.3 External Memory is Non-Negotiable for Multi-Agent Coordination

**Convergence strength: High (5+ independent sources)**

- Anthropic: Memory stores research plan; survives 200K context truncation; subagent output to artifact system
- FS-Researcher: Persistent file-system workspace. Ablation removing it drops RACE by -4.07
- Memory Survey (2603.07670v1): Pattern B (Context + Retrieval Store) as pragmatic default; memory-vs-no-memory gap exceeds LLM-backbone gap
- AutoScientists: Stateless agents with discoverable context in shared workspace; agents have no memory between sessions
- Argus: Evidence DAG as structured memory; 1200:1 compression decouples context from search budget

**Consensus claim:** Context windows alone cannot support multi-agent coordination. Every production-grade multi-agent system uses some form of external memory -- file systems, DAGs, vector stores, or message boards. The three architecture patterns identified in the Memory Survey (Monolithic, Context+Retrieval, Tiered with Learned Control) provide a maturity ladder.

### 3.4 Structured Representations Beat Flat Aggregation

**Convergence strength: High (4+ independent sources)**

- Argus: Structured DAG +5.2 points over flat text evidence concatenation (BrowseComp, K=8)
- PosterForest: Heterogeneous Poster Tree representation (jointly encoding semantic + spatial attributes) yields 2.2x human preference
- Agentic Reasoning: Mind-Map (knowledge graph with community clustering) yields 66.13 GAIA vs. MemGPT 55.10 and Raw text 47.84
- RecursiveMAS: Latent-space tree enables clean gradient propagation vs. text-based communication that suffers gradient vanishing

**Consensus claim:** When multiple agents exchange information, structured representations (graphs, trees, DAGs) outperform flat text concatenation. The structure preserves relationships, supports compression, and enables principled retrieval. Flat aggregation saturates at modest scale.

### 3.5 Heuristic-Based Routing Beats Fixed Topologies

**Convergence strength: Medium-High (3+ independent sources)**

- Anthropic: Effort-scaling heuristics (1 agent for simple, 2-4 for comparisons, >10 for complex) rather than hard-coded rules
- MetaAgent-X: Designer learns task-dependent routing (reflection 70-73% for AIME, single-agent 46% for OlympiadBench)
- CollabCoder: CDM trust-weighted decision (plan vs. code update) adapts per error type rather than always patching code
- AFlow: MCTS discovers ensemble-like structures without operator specification (93.1% retention without operators)

**Consensus claim:** Static multi-agent topologies underperform adaptive ones. The ability to route task complexity to appropriate agent configurations -- whether through learned policies, heuristic rules, or search -- is a first-order performance driver.

---

## 4. Contradictions

Where sources disagree -- these need arbitration in Phase 4 plans.

### 4.1 Explicit vs. Latent Multi-Agent Communication

**The tension:**
- **Explicit camp** (Anthropic, FS-Researcher, Argus, CollabCoder): Agents should communicate through structured text/graphs that are interpretable, auditable, and debuggable.
- **Latent camp** (RecursiveMAS, IMAD): Agents should communicate through continuous latent vectors to avoid the text decode/re-encode bottleneck, achieving 2.4x speedup and 75.6% token reduction.

**Evidence on both sides:**
- Explicit: Argus achieves full auditability (every claim traces to source URL). Dialectic-Med shows text-only debate is "fundamentally inadequate" without visual grounding (-9.31% drop without VFM). Anthropic: "heuristics over rigid rules" as an explicit-text pattern.
- Latent: RecursiveMAS achieves stable gradient propagation where text-based recursion suffers vanishing gradients. IMAD: internalizing debate beats explicit debate (+2.17pp GSM8K) at 11% token cost.

**Resolution path:** These are not mutually exclusive. RecursiveMAS's intermediate rounds can be latent while the final round produces interpretable text output. The safety-critical question is whether the opacity of latent intermediate states is acceptable. For Lyra, the answer likely depends on the task tier: latent communication for throughput-optimized internal reasoning, explicit structured traces for audit-required outputs.

### 4.2 Search-Based vs. Learned Multi-Agent Optimization

**The tension:**
- **Search camp** (AFlow, SWE-Search, MARS\$^2\$): Use MCTS to search over agent configurations/topologies. Training-free or lightweight; better interpretability.
- **RL camp** (MetaAgent-X, Argus, IMAD): Use end-to-end RL (GRPO) to co-optimize designer and executor policies. Discovers non-obvious strategies.

**Evidence on both sides:**
- Search: AFlow achieves 80.3% avg across 6 benchmarks with zero agent training. SWE-Search: +23% relative with no model retraining. MARS\$^2\$: +8.0% Pass@1 on Qwen3-8B. Downside: 5-14x inference cost.
- RL: MetaAgent-X: +11.17% avg over single-agent across 6 benchmarks with 4B/8B models. Argus: contrastive RL isolates verification's causal contribution. IMAD: RL enables internalization that SFT alone cannot achieve. Downside: requires SFT cold start, 64x H200 GPUs, training instability.

**Resolution path:** Complementary, not contradictory. Search-based methods are appropriate for deployment-time optimization (inference-time compute scaling). RL-based methods are appropriate for training-time capability building. Lyra should use RL to train its orchestrator/executor policies offline, and search to allocate compute budget online. The MetaAgent-X result that 50% of RL gains come from better execution under the same structural pattern and 50% from designer flipping suggests both mechanisms contribute independently.

### 4.3 Centralized vs. Decentralized Coordination

**The tension:**
- **Centralized camp** (Anthropic, FS-Researcher, Argus, CollabCoder): A lead agent/orchestrator coordinates specialized subagents. Clear authority, easier debugging.
- **Decentralized camp** (AutoScientists, Dialectic-Med): Agents self-organize, peer-review each other, and coordinate through shared workspaces. No single point of failure or bottleneck.

**Evidence on both sides:**
- Centralized: Anthropic's system achieves +90.2% with clear orchestrator-worker structure. Argus scales to K=64 without degradation. CollabCoder's CDM makes explicit trust-weighted decisions.
- Decentralized: AutoScientists sustains parallel hypothesis teams. 7 accepted improvements vs. 0 single-agent. Dialectic-Med's mediator is impartial adjudicator, not central planner. Peer-review-before-compute prevents GPU waste.

**Resolution path:** Anthropic identifies the synchronous bottleneck as an acknowledged weakness: the lead waits for all subagents and cannot steer mid-flight. AutoScientists' decentralized approach eliminates this but introduces agent reliability problems (analysts writing local notes instead of posting, template bloat). The correct approach for Lyra is likely a hybrid: centralized orchestration for task decomposition and synthesis, decentralized peer-review for verification and consensus. This matches the Anthropic pattern with an added adversarial verification layer.

### 4.4 Specialized Agent Count: Few Deep vs. Many Shallow

**The tension:**
- **Few specialized agents** (Agentic Reasoning, CollabCoder): 3 carefully chosen agents outperform 109 LangChain tools. Explicit ablation: H-F's 7-tool agent and LangChain's 109-tool agent both *degrade* performance. External agents duplicate what reasoning models already do internally.
- **Many parallel agents** (Argus, Anthropic, AutoScientists): Argus scales to K=64 parallel searchers with no accuracy ceiling. Anthropic uses >10 subagents for complex queries. AutoScientists runs 9 agents continuously.

**Evidence on both sides:**
- Few: Agentic Reasoning explicitly tests tool count vs. performance. 3 agents (Web-Search, Coding, Mind-Map) outperform both 7-tool and 109-tool configurations. "Many capabilities already exist inside the reasoning model -- external duplicates introduce noise."
- Many: Argus' log-linear scaling (K=1 to K=64) proves more parallel searchers monotonically improve accuracy when the coordinator can effectively integrate. The key is evidence composition (DAG), not agent coordination.

**Resolution path:** The contradiction is domain-dependent, not fundamental. For tool-use tasks, agent specialization must complement (not duplicate) the backbone model's capabilities. For information retrieval tasks, parallel breadth scales with the coordinator's integration capacity. Lyra should follow the Agentic Reasoning rule: add agents only when they serve a capability the base model demonstrably lacks, and validate with ablation.

---

## 5. Open Problems

What problems does NO source solve yet? These are research opportunities.

### 5.1 Dynamic Agent Topology Adaptation

**Status:** Unsolved. All surveyed systems use static topologies (fixed orchestrator-worker, fixed 2-3 agent debate, pre-defined tree structures). MetaAgent-X's Designer generates scripts from pre-defined coordination templates (single, ensemble, reflection, solver-tester). AFlow's search is capped at 10 nodes. No system dynamically adds/removes agents, rewires communication, or changes coordination patterns mid-task based on execution feedback.

**Opportunity for Lyra:** A meta-controller that monitors execution and dynamically adjusts the agent topology (split overloaded agents, merge redundant ones, introduce verification agents when confidence drops) would be a genuine contribution.

### 5.2 Cross-Session Agent Identity and Memory

**Status:** Unsolved. AutoScientists explicitly states "Agents have no memory between sessions. All state comes from shared workspaces." The Memory Survey identifies multi-agent memory governance as "uncharted"--access control over shared stores, consensus protocols for concurrent writes, and principled boundaries between shared/private memory. MemoryAgentBench shows most systems fail on selective forgetting and most models plummet from near-perfect to 40-60% on multi-session MemoryArena tasks.

**Opportunity for Lyra:** A durable agent identity system that maintains consistent knowledge, skills, and behavioral patterns across sessions separated by hours/days, with principled forgetting and update mechanisms, would solve an open problem.

### 5.3 Adversarially Robust Multi-Agent Consensus

**Status:** Unsolved. Conjunctive Prompt Attacks (2604.16543v1) show that distributed attacks achieve ASR_max=1.0 while evading per-message guard models. Existing defenses (tool allowlists, least privilege) only reduce ASR by 15-20%. The Trustworthy Agentic AI survey identifies multi-agent attribution as unsolved: "Assigning responsibility requires protocol-aware traces, message authentication, and evaluation designs that separate individual from collective failure modes."

**Opportunity for Lyra:** Routing-trace-aware safety validation with cross-agent provenance tracking. This is not just a defense mechanism but a fundamental architectural property.

### 5.4 Multi-Agent Training at Scale (>10B parameters)

**Status:** Unsolved. RecursiveMAS capped at sub-10B models. MetaAgent-X only tested at 4B/8B. MARS\$^2\$ only tested at 8B/14B. IMAD only tested at 7B-12B. No system has demonstrated multi-agent co-training or recursive optimization at 70B+ scale. The computational requirements (MetaAgent-X: 8x H200 GPUs; Argus: 64x H200 for 1.5 days; MARS\$^2\$: 8 GPUs per model) are significant even at modest scale.

**Opportunity for Lyra:** Efficient multi-agent training methods that scale to larger models, potentially through modular training (train coordination layers while freezing agent backbones), distillation, or staged optimization.

### 5.5 Cost-Aware Multi-Agent Budget Allocation

**Status:** Partially addressed but unsolved as a general problem. Anthropic has effort-scaling heuristics (simple/comparison/complex). Argus demonstrates log-linear accuracy scaling with compute but no cost-aware truncation. SWE-Search costs 5-14x more than baseline. No system dynamically allocates budget across agents based on real-time cost/benefit analysis.

**Opportunity for Lyra:** A compute controller that monitors per-agent progress, estimates marginal value of additional compute, and reallocates budget from saturated agents to promising ones. This is directly motivated by the AFlow result that GPT-4o-mini + optimized workflow matches GPT-4o at 4.55% of cost.

### 5.6 Human-in-the-Loop Integration for Multi-Agent Systems

**Status:** Unsolved. The AI Auto-Research Roadmap identifies "human-governed collaboration is the most reliable deployment mode" as a cross-cutting insight but catalogs no system that does this well. Anthropic's system has no mid-flight human steering. AutoScientists has no human intervention protocol. Dialectic-Med's expert evaluation was retrospective, not integrated.

**Opportunity for Lyra:** Principled HITL integration points -- not just final approval but mid-execution steering, hypothesis injection, and override mechanisms -- designed for multi-agent workflows.

---

## 6. Recommendations for Lyra

Ranked list of techniques to adopt, with rationale and implementation priority.

### Tier 1: Foundational (Adopt Immediately)

**1. Orchestrator-Worker Pattern with External Memory Persistence**
- **Rationale:** Strongest convergence signal in the corpus. +90.2% performance gain. Production-validated. Solves Lyra's context-window binding constraint.
- **Implementation:** LeadResearcher agent (Opus-tier for complex tasks) saves plan to durable external memory. Spawns parallel subagents (Sonnet-tier) with file-system artifact output. Subagents return compressed findings. Citation verification as final pass.
- **Effort:** Medium. Requires memory store, subagent spawning infrastructure, artifact-based output system. Lyra already has agent infrastructure.
- **Sources:** Anthropic Engineering Blog, FS-Researcher (2602.01566v2), Build Multi-Agent System from Scratch (book), Memory Survey (2603.07670v1).

**2. Structured Evidence Representation (DAG or Knowledge Graph)**
- **Rationale:** Structured graph representation alone contributes +5.2 points over flat text (Argus). Mind-Map (knowledge graph with community clustering) yields 18-point GAIA improvement over flat memory.
- **Implementation:** Evidence nodes + claim nodes + support/contradict edges. Context compression at ~1000:1 ratio. Every output claim traces back to evidence.
- **Effort:** Medium. Requires DAG construction pipeline, community detection (Leiden algorithm), GraphRAG retrieval. All components have open-source implementations.
- **Sources:** Argus (2605.16217v3), Agentic Reasoning (2502.04644v2), PosterForest (2508.21720v2).

**3. Parallel Subagent Spawning with Effort-Scaling Heuristics**
- **Rationale:** 90% latency reduction. Log-linear accuracy scaling (Argus K=1 to K=64). Anthropic's heuristics are validated in production.
- **Implementation:** Query complexity assessment -> 1 agent (simple), 2-4 agents (comparisons), >10 agents (complex). Parallel dispatch with independent context windows. Merge via structured evidence representation.
- **Effort:** Low-Medium. Primarily routing logic + parallel execution infrastructure.
- **Sources:** Anthropic Engineering Blog, Argus (2605.16217v3), MARS\$^2\$ (2604.14564v1).

### Tier 2: Differentiating (Adopt in Phase 4)

**4. Collaborative Decision-Making for Error Attribution**
- **Rationale:** Plan-Code Co-Evolution reduces complexity from O(nk) to O(t). 30-57% token savings. The static-planning flaw CollabCoder identifies is universal in current agent frameworks including Lyra.
- **Implementation:** Three parallel analyses (plan-level, execution-level, alignment) with trust-weighted fusion. Reasoning Trajectory accumulation to avoid repeating failed approaches.
- **Effort:** Medium. Requires implementing 3 parallel analysis prompts, trust-weighted scoring, and trajectory accumulation. Prompt templates fully specified in the paper.
- **Sources:** CollabCoder (2604.13946v2), Agentic Reasoning (2502.04644v2).

**5. Stagewise Designer-Executor Co-Evolution (RL Training)**
- **Rationale:** Breaks the frozen-executor ceiling that limits all current Auto-MAS approaches. +11.17% avg over single-agent. Stagewise alternation prevents training collapse. Hierarchical rollout provides clean credit assignment.
- **Implementation:** SFT cold start from Lyra's existing agent traces -> hierarchical rollout (M candidate designs x N executions each) -> GRPO with stagewise alternation (K=30 steps per phase) -> shared policy optimization.
- **Effort:** High. Requires SFT pipeline, hierarchical rollout infrastructure, GRPO training, 8+ GPU setup, reward design. High-effort but high-reward.
- **Sources:** MetaAgent-X (2605.14212v1), MARS\$^2\$ (2604.14564v1).

**6. Adversarial Verification with Grounded Falsification**
- **Rationale:** Text-only verification is fundamentally inadequate (Dialectic-Med shows -9.31% drop without VFM). Per-message safety classifiers are architecturally insufficient for multi-agent systems (Conjunctive Prompt Attacks achieve ASR=1.0 while evading them).
- **Implementation:** Opponent agent generates counterfactual probes grounded in execution traces/AST diffs. Mediator adjudicates via consensus graph. Integration with Lyra's existing safety framework. Routing-trace-aware validation.
- **Effort:** Medium-High. Requires code-grounding falsification module (analogous to VFM but for code), multi-agent verification orchestrator, consensus graph infrastructure.
- **Sources:** Dialectic-Med (2604.11258v1), Conjunctive Prompt Attacks (2604.16543v1), Trustworthy Agentic AI survey (2605.23989v1).

### Tier 3: Research Bets (Investigate for Phase 5+)

**7. Latent Multi-Agent Communication (RecursiveLink)**
- **Rationale:** 2.4x speedup, 75.6% token reduction. Stable gradient propagation proven theoretically. But opacity of intermediate states is a safety concern for Lyra's audit requirements.
- **Implementation:** 2-layer residual MLP (~0.3% of total params) trained with inner-loop cosine similarity + outer-loop CE loss. Intermediate rounds in latent space, final round decodes text.
- **Effort:** Medium. Requires RecursiveLink modules, modified inference pipeline, training data curation.
- **Sources:** RecursiveMAS (2604.25917v1), IMAD / Latent Agents (2604.24881v1).

**8. Hypothesis-Based Self-Organizing Agent Teams**
- **Rationale:** Eliminates central planner bottleneck. Peer-review-before-compute prevents waste. 7 accepted improvements vs. 0 single-agent. But agent reliability issues and template bloat are documented concerns.
- **Implementation:** HEARTBEAT state machine, [PROPOSAL]-based peer review, multi-seed noise gating for champion propagation, self-regulating discussion triggers, meta-improvement loops.
- **Effort:** High. Requires message-board infrastructure, state machine per agent, peer review protocol, template management system.
- **Sources:** AutoScientists (2605.28655), AI Auto-Research Roadmap (2605.18661v1).

---

## Source Index

| ID | Type | Title | Key Evidence |
|----|------|-------|-------------|
| 2308.03688v3 | Paper | AgentBench | Multi-environment agent evaluation; failure taxonomy |
| 2410.10762v4 | Paper | AFlow | MCTS workflow optimization; +5.7% over human designs |
| 2410.20285v6 | Paper | SWE-Search | MCTS for coding agents; +23% mean improvement |
| 2502.04644v2 | Paper | Agentic Reasoning | Mind-Map structured memory; +18 GAIA points |
| 2508.21720v2 | Paper | PosterForest | Hierarchical tree representation; 2.2x human preference |
| 2510.18407v1 | Paper | HAP | Adversarial curriculum learning; minimax formulation |
| 2601.11868v1 | Paper | Terminal-Bench 2.0 | CLI agent benchmark; 62.9% ceiling |
| 2602.00428v2 | Paper | (not deeply read) | — |
| 2602.01566v2 | Paper | FS-Researcher | Dual-agent persistent workspace; +7.49 RACE |
| 2603.04855v3 | Paper | (not deeply read) | — |
| 2603.07670v1 | Paper | Memory Survey | POMDP formalization; 5 mechanism families |
| 2603.13686v1 | Paper | Tau-Voice | Tick-based voice orchestration |
| 2604.05514v1 | Paper | (not deeply read) | — |
| 2604.11258v1 | Paper | Dialectic-Med | Adversarial debate with visual grounding; -46.3% hallucination |
| 2604.13946v2 | Paper | CollabCoder | Plan-Code Co-Evolution; 82.50% avg |
| 2604.14362v1 | Paper | (not deeply read) | — |
| 2604.14564v1 | Paper | MARS\$^2\$ | Multi-agent tree search; +8.0% Pass@1 |
| 2604.16175v1 | Paper | (not deeply read) | — |
| 2604.16543v1 | Paper | Conjunctive Prompt Attacks | Topology-dependent attack surfaces; ASR=1.0 |
| 2604.16968v1 | Paper | (not deeply read) | — |
| 2604.21420v1 | Paper | (not deeply read) | — |
| 2604.24881v1 | Paper | Latent Agents (IMAD) | Internalized multi-agent debate; 5-16x efficiency |
| 2604.25917v1 | Paper | RecursiveMAS | Latent-space communication; +8.3% avg |
| 2605.06716v1 | Paper | (not deeply read) | — |
| 2605.14212v1 | Paper | MetaAgent-X | End-to-end RL for Auto-MAS; +11.17% avg |
| 2605.16217v3 | Paper | Argus | Evidence DAG; 1200:1 compression; +12.6 GAIA |
| 2605.18661v1 | Paper | AI Auto-Research Roadmap | 270+ systems; lifecycle framework |
| 2605.18747v1 | Paper | (not deeply read) | — |
| 2605.18769v1 | Paper | ClusterRAG | Collaborative profiling; SOTA on LaMP |
| 2605.23989v1 | Paper | Trustworthy Agentic AI | Defense-in-depth; release gating framework |
| 2605.24220v1 | Paper | (not deeply read) | — |
| 2605.24426v1 | Paper | (not deeply read) | — |
| — | Book | Build Multi-Agent System from Scratch (Fajardo 2026) | 12 best practices; 8 anti-patterns |
| — | Book | 30 Agents Every AI Engineer Must Build | Agent pattern catalog |
| — | Web | Anthropic Engineering Blog (June 2025) | +90.2% multi-agent gain; orchestrator-worker |
| — | Web | mims-harvard/AutoScientists | Self-organizing hypothesis teams; +8.33% BioML-Bench |
