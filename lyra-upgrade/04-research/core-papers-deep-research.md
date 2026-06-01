# Lyra Core Papers Deep Research

**Date:** 2026-06-01
**Scope:** 10 papers from Lyra master prompt Section 3.5, analyzed for direct applicability to Lyra's agent architecture, orchestration, and fleet coordination.

---

## Paper 1: Small Language Models are the Future of Agentic AI
**arXiv:** [2506.02153](https://arxiv.org/abs/2506.02153) | **Authors:** Peter Belcak, Greg Heinrich, Shizhe Diao, Yonggan Fu, Xin Dong, Saurav Muralidharan, Yingyan Celine Lin, Pavlo Molchanov (NVIDIA Research + Georgia Tech) | **Date:** June 2025

### Core Mechanism

NVIDIA argues three positions: (V1) SLMs (<10B params) are sufficiently capable for most agentic subtasks; (V2) SLMs are inherently more suitable for repetitive, scoped agentic workloads; (V3) SLMs are 10-30x cheaper, making them the economically necessary choice.

**LLM-to-SLM Conversion Algorithm (6 steps):**
1. **S1 - Secure usage data collection:** Instrument and log all non-HCI agent calls (inputs, responses, tool calls, latency), with encryption and RBAC.
2. **S2 - Data curation and filtering:** Scrub PII/PHI, anonymize. Typically 10K-100K examples suffice for SLM fine-tuning.
3. **S3 - Task clustering:** Unsupervised clustering (k-means on text embeddings) to identify recurring prompt/tool-call patterns. These form candidate tasks for specialized SLMs.
4. **S4 - SLM selection:** Match each task cluster to a base SLM by capability fit, benchmark performance, license compliance, and deployment hardware constraints.
5. **S5 - Specialized fine-tuning:** PEFT (LoRA/QLoRA) with task-specific data. Optional knowledge distillation: train SLM to mimic LLM outputs on target tasks.
6. **S6 - Iteration and refinement:** Continuous data collection, retraining, and task-routing model optimization in a closed loop.

**Heterogeneous agentic system architecture:** "SLM-first with strategic LLM escalation" -- SLMs handle the bulk (routine, repetitive subtasks); LLMs are invoked selectively for complex reasoning, open-ended planning, and cross-domain abstraction. An orchestrator-LLM decomposes high-level goals, dispatches subtasks to specialized SLM "experts," and escalates only when needed.

### Real Benchmark Numbers

| Model (Params) | Capability | Key Stat |
|---|---|---|
| Microsoft Phi-2 (2.7B) | Reasoning & code gen | Matches 30B peers at ~15x faster inference |
| Microsoft Phi-3 small (7B) | Language understanding | Matches 70B models of same generation |
| NVIDIA Nemotron-H (2/4.8/9B) | Instruction following & coding | 30B-level accuracy with 10x fewer inference FLOPs |
| HuggingFace SmolLM2 (125M-1.7B) | Tool use | Competes with 14B contemporaries; matches 70B models from 2 years prior |
| NVIDIA Hymba-1.5B | Instruction adherence | Outperforms 13B models; 3.5x higher token throughput |
| DeepSeek-R1-Distill-Qwen-7B | Reasoning | Outperforms Claude-3.5-Sonnet and GPT-4o on reasoning benchmarks |
| Salesforce xLAM-2-8B | Tool calling | SOTA; surpasses GPT-4o and Claude 3.5 |
| DeepMind RETRO-7.5B | Language modeling (RAG) | Matches GPT-3 (175B) with 25x fewer parameters |

**Agent system LLM call replaceability:**

| Open-Source Agent | Function | Replaceable with SLMs |
|---|---|---|
| MetaGPT | Multi-agent software engineering | ~60% of LLM calls |
| Open Operator | Workflow automation | ~40% of LLM calls |
| Cradle | GUI automation (computer control) | ~70% of LLM calls |

### Trade-off Analysis

| Gain | Cost |
|---|---|
| 10-30x cheaper inference (latency, energy, FLOPs) | Task-specific fine-tuning required per SLM |
| 40-70% of LLM calls offloadable today | Heterogeneous routing adds architectural complexity |
| Edge deployment on consumer-grade GPUs | $57B sunk infrastructure creates institutional inertia |
| Stronger data privacy (local deployment) | Evaluation benchmarks focus on generalist metrics, not agentic utility |
| SLMs show less sparse activation inefficiency | Calibration costs for production-grade reliability |

### Design Rationale

The $57B invested in LLM cloud inference vs. only $5.6B in LLM API market revenue (10x disparity) motivates the economic argument. LLMs exhibit sparse activation internally (many parameters unused per inference), while SLMs show less of this inefficiency. The heterogeneous approach is framed as the "natural choice" because no single model size is optimal for all agentic subtasks.

### Transferable Idea for Lyra

**Directly backs Lyra Section 4.5 model router.** Lyra's model routing layer should implement the "SLM-first with strategic LLM escalation" pattern. The six-step conversion algorithm provides an operational blueprint for migrating Lyra's agent call patterns from monolithic LLM usage to heterogeneous multi-model execution. The 40-70% replaceability numbers give concrete targets for Lyra's SLM adoption roadmap.

### Impact x Effort Rating

**Impact: HIGH (9/10)** -- Validates a core architectural decision for Lyra, provides operational blueprint, and quantifies expected savings.
**Effort: MEDIUM (5/10)** -- Requires building the routing layer, SLM fine-tuning pipeline, and task clustering infrastructure. The algorithm is well-specified, reducing design risk.
**Overall: 9/10 -- Implement immediately in Lyra's model routing subsystem.**

---

## Paper 2: Establishing Best Practices for Building Rigorous Agentic Benchmarks
**arXiv:** [2507.02825](https://arxiv.org/abs/2507.02825) | **Authors:** Yuxuan Zhu, Tengjun Jin, Yada Pruksachatkun, Andy Zhang, Shu Liu et al. (25 authors, including Percy Liang, Ion Stoica, Jacob Steinhardt, Daniel Kang) | **Date:** July 2025 | **Venue:** NeurIPS

### Core Mechanism

The paper systematically audits 10 widely-used agentic benchmarks and introduces the **Agentic Benchmark Checklist (ABC)** -- an actionable set of guidelines built around two core validity requirements:

1. **Outcome Validity:** The evaluation result truly indicates task success (no shortcuts or false positives).
2. **Task Validity:** A task is solvable if and only if the agent possesses the target capability.

### Real Benchmark Numbers

**Benchmark flaw audit results:**

| Benchmark | Issue | Impact |
|---|---|---|
| SWE-bench Verified | Insufficient test cases; incorrect patches can still pass | 24% of top-50 leaderboard entries are wrong |
| TAU-bench | Empty responses counted as success | Trivial agent scores 38% (~38% overestimation) |
| SWE-Lancer | Fails to isolate agents from ground truth | Agents score 100% without solving tasks |
| KernelBench | Inadequate fuzz testing | ~31% overestimation |
| WebArena | Unvalidated LLM-as-a-Judge | 1.4-5.2% overestimation |
| OSWorld | Broken HTML selectors from website changes | 28% underestimation |

**Overall:** Performance misestimation can reach **up to 100% in relative terms** due to flawed task or reward setups.

**ABC applied to CVE-Bench:** Reduces performance overestimation by **33% in absolute terms**, confirmed by cybersecurity experts.

**Across 10 benchmarks audited with ABC:**
- 7 had flaws in outcome validity
- 7 had issues in task validity
- All 10 had limitations in result reporting

### Trade-off Analysis

| Gain | Cost |
|---|---|
| Prevents false confidence in leaderboard positions | ABC application requires domain expertise per benchmark |
| 33% reduction in overestimation on CVE-Bench | Full ABC audit is labor-intensive (case study required cybersecurity experts) |
| Two-dimensional validity framework is generalizable | Some flaws (e.g., SWE-Lancer ground-truth isolation) require fundamental redesign |
| Actionable guidelines, not just criticism | Does not automate benchmark fixing -- identifies problems, leaves fixes to benchmark authors |

### Design Rationale

The authors draw from software testing literature (Zhu 1997 on unit testing, Watson 1996 on structured testing) to establish a rigorous engineering discipline for agent evaluation. The key insight is that agentic benchmarks require both outcome validity and task validity simultaneously -- satisfying only one is insufficient and leads to systemic misestimation.

### Transferable Idea for Lyra

**Directly backs Lyra Section 4.16 reliability.** Lyra should adopt the ABC checklist as a mandatory gate for any internal evaluation harness. Every Lyra benchmark (fleet coordination, skill routing, memory retrieval) must pass both outcome and task validity checks before being used for optimization or comparison. The 33% overestimation reduction on CVE-Bench demonstrates that rigorous evaluation design is not optional -- it is the difference between measuring real progress and measuring artifacts.

### Impact x Effort Rating

**Impact: HIGH (9/10)** -- Prevents Lyra from optimizing against broken metrics. The audit framework is directly applicable to Lyra's eval infrastructure.
**Effort: MEDIUM (6/10)** -- Requires applying ABC to Lyra's existing benchmarks and fixing identified flaws. Domain expertise needed for each benchmark domain.
**Overall: 9/10 -- Adopt ABC as mandatory gate for all Lyra evaluation infrastructure.**

---

## Paper 3: From Model Scaling to System Scaling -- Scaling the Harness in Agentic AI
**arXiv:** [2605.26112](https://arxiv.org/abs/2605.26112) | **Author:** Shangding Gu (UC Berkeley) | **Date:** May 2026 | **Code:** [CheetahClaws](https://github.com/SafeRL-Lab/cheetahclaws)

### Core Mechanism

The paper decomposes agent systems into **six interacting components**, with only the first being model-scaling and the remaining five being system-scaling:

| Component | Symbol | Scaling Type | Responsibility |
|---|---|---|---|
| Reasoning Substrate | R | Model | Foundation model inference |
| Memory Store | M | System | Persistent knowledge, cross-session memory with confidence/recency/source/conflict_group metadata |
| Context Constructor | C | System | Input assembly, two-layer compression (rule truncation + AI summary), refresh strategies |
| Skill-Routing Layer | S | System | Tool/sub-agent dispatch, unified ToolDef + register_tool() mechanism, MCP protocol support |
| Orchestration Loop | O | System | Multi-turn execution control flow, Chronos unified scheduler (cron + event-driven) |
| Verification & Governance | G | System | Four-level verification (L0 static analysis through L3 deep verification), audit, permission gating |

**Three core bottlenecks identified:**
1. **Context Governance:** Preventing "exposed but inaccessible" information
2. **Trustworthy Memory:** Preventing "stale but confident" memory contamination
3. **Dynamic Skill Routing:** Preventing "confident but unverified" tool calls

**Central claim:** "Future progress in agentic AI will depend as much on system design as on stronger foundation models."

### CheetahClaws Reference Implementation

~40K lines of Python. Key features: multi-provider support (Anthropic/OpenAI/Gemini/DeepSeek/Ollama), structured memory with confidence x recency re-ranking, multi-agent orchestration (Coder/Reviewer/Researcher) with worktree isolation, and a unified scheduler.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| System-level improvements compound across model generations | System scaling requires sustained engineering investment |
| Harness improvements are model-agnostic (work with any provider) | Complex harness designs can introduce their own failure modes |
| Structured memory with metadata prevents contamination | Six-component architecture adds baseline complexity |
| Verification layers catch errors before they propagate | Four-tier verification is expensive (especially L3 deep verification) |

### Design Rationale

The core argument is that the field has over-invested in model scaling while under-investing in the harness that makes models useful. The six-component decomposition provides a formal vocabulary for discussing and optimizing agent architectures. By separating concerns (memory, context, routing, orchestration, verification), each subsystem can be independently improved and evaluated.

### Transferable Idea for Lyra

**Directly backs the harness-first approach.** Lyra's architecture should adopt the six-component decomposition as its architectural blueprint. Each component should have independent benchmarks and optimization targets. The three bottlenecks (context governance, trustworthy memory, dynamic skill routing) should become Lyra's top engineering priorities. CheetahClaws provides a reference implementation to study and potentially fork patterns from.

### Impact x Effort Rating

**Impact: VERY HIGH (10/10)** -- Provides the architectural vocabulary for all of Lyra's design decisions. The six-component model is directly mappable to Lyra's subsystems.
**Effort: LOW (3/10)** -- This is a design/architectural paper, not a new system to build. The concepts are immediately applicable to Lyra's existing architecture.
**Overall: 10/10 -- Foundational. Adopt the six-component model as Lyra's architectural blueprint.**

---

## Paper 4: Meta-Harness -- End-to-End Optimization of Model Harnesses
**arXiv:** [2603.28052](https://arxiv.org/abs/2603.28052) | **Authors:** Yoonho Lee, Roshen Nair, Qizheng Zhang, Kangwook Lee, Omar Khattab, Chelsea Finn (Stanford, KRAFTON, MIT) | **Date:** March 2026 | **Code:** [stanford-iris-lab/meta-harness-tbench2-artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact)

### Core Mechanism

Meta-Harness is an **outer-loop search system** that automatically discovers optimal harness code -- Python programs that determine what information an LLM stores, retrieves, and sees at each step. Unlike text optimizers (DSPy, TextGrad, OPRO) that only optimize prompts, Meta-Harness optimizes entire programs including retrieval logic, context management, memory, and orchestration.

**Algorithm:** The proposer agent accesses a filesystem containing full source code, evaluation scores, and execution traces of all prior harness candidates. It uses `grep`, `cat`, and other terminal tools to selectively read logs, giving it up to **10M tokens of diagnostic context per iteration** (vs. 0.002-0.026M tokens for prior text optimizers like OPRO, TextGrad, AlphaEvolve).

**Search loop:** ~20 iterations with 2-3 candidates per iteration, maintaining a Pareto frontier over accuracy vs. context cost. The proposer reads a median of 82 files per iteration, referencing 20+ prior candidates.

### Real Benchmark Numbers

**Online text classification (GPT-OSS-120B, 3 datasets: USPTO-50k, Symptom2Disease, LawBench):**

| Method | Avg Accuracy | Context (K tokens) |
|---|---|---|
| Zero-Shot | 27.4% | 0 |
| Few-Shot (all) | 40.8% | 12.3K |
| MCE | 40.0% | 28.5K |
| ACE (prior SOTA) | 40.9% | 50.8K |
| **Meta-Harness** | **48.6%** | **11.4K** |

**Delta:** +7.7 points over ACE while using ~4x fewer context tokens. LawBench saw +16 points (29% -> 45%). The discovered harness ("Label-Primed Query") matched competitors' final accuracy after only 4 evaluations (vs. 60 for OpenEvolve/TTT-Discover).

**TerminalBench-2 (89-task Dockerized agentic coding):**

| Agent (Claude Haiku 4.5) | Pass % | Agent (Claude Opus 4.6) | Pass % |
|---|---|---|---|
| OpenHands | 13.9% | Terminus-KIRA | 74.7% |
| Claude Code | 27.5% | **Meta-Harness** | **76.4% (#2)** |
| Terminus-KIRA | 33.7% | | |
| Goose | 35.5% | | |
| **Meta-Harness** | **37.6% (#1)** | | |

Key discovery: **environment bootstrapping** -- injecting an OS snapshot (installed languages, package managers, working directory) before the agent loop saved 2-4 wasted exploration turns per task.

**Math reasoning (200 IMO-level problems, 5 held-out models):**

| Method | Avg Accuracy |
|---|---|
| Baseline | 34.1% |
| **Meta-Harness** | **38.8%** |

**Delta:** +4.7 points average, using an automatically-discovered 4-route lexical router (combinatorics/geometry/number theory/algebra). A single discovered harness generalized across all 5 held-out models.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| +7.7 points on text classification with 4x fewer tokens | Search loop requires ~20 iterations at ~2-3 candidates each -- substantial compute |
| Harness generalizes across models (single harness works for 5 held-out models) | Proposer needs 10M tokens of diagnostic context per iteration |
| Environment bootstrapping discovery saves 2-4 turns per task | Adds harness search complexity on top of model inference |
| Pareto frontier approach balances accuracy vs. context cost | Requires filesystem-based access patterns that may not fit all deployment environments |
| Discovered harnesses are interpretable (Python code) | Search space is bounded by the proposer agent's creativity |

### Design Rationale

The authors observed that existing text optimizers "compress feedback too aggressively" -- reducing rich execution traces to scalar scores loses causal information about why failures occur. By giving the proposer access to full source code, scores, AND execution traces, it can perform causal diagnosis (identifying which harness decisions caused which failures), enabling much more targeted optimization.

### Transferable Idea for Lyra

**Directly relevant to Lyra's harness architecture.** Lyra should adopt the filesystem-based feedback loop pattern: maintain execution traces alongside harness configurations, and use an optimizer agent that reads both scores and traces to propose harness improvements. The environment bootstrapping discovery is immediately applicable -- Lyra agents should inject environment snapshots before task loops. The Pareto frontier approach (accuracy vs. context cost) is exactly the optimization Lyra's model router needs.

### Impact x Effort Rating

**Impact: VERY HIGH (10/10)** -- The outer-loop harness optimization paradigm is directly applicable to Lyra's entire architecture. The numbers (+7.7 points, 4x token savings) demonstrate compelling ROI.
**Effort: HIGH (7/10)** -- Requires building the filesystem-based optimization loop, trace collection infrastructure, and proposer agent. However, the algorithm is well-specified and the artifact is open-source.
**Overall: 9/10 -- Core architectural pattern. Implement harness optimization loop in Lyra.**

---

## Paper 5: Code as Agent Harness
**arXiv:** [2605.18747](https://arxiv.org/abs/2605.18747) | **Authors:** Xuying Ning, Katherine Tieu, Dongqi Fu et al. (42 authors from UIUC, Meta, Stanford) | **Date:** May 2026 | **Code:** [Awesome-Code-as-Agent-Harness-Papers](https://github.com/YennNing/Awesome-Code-as-Agent-Harness-Papers)

### Core Mechanism

A 102-page survey establishing "code as agent harness" -- a unified view positioning code not as mere LLM output but as the **operational substrate for agent reasoning, acting, environment modeling, and execution-based verification.** Organized across three layers:

**Layer 1: Harness Interface**
- Code connects agents to **reasoning** (externalizing logic into verifiable computation), **acting** (programs as policies, tool calls, reusable skills), and **environment modeling** (code represents state, dynamics, feedback signals).

**Layer 2: Harness Mechanisms**
- **Planning:** Decomposition, structural grounding, trajectory search, orchestration.
- **Memory:** Working, semantic, experiential, long-term, and multi-agent memory.
- **Tool Use:** Connecting agents to APIs, repositories, execution environments.
- **Feedback-Driven Control:** Execution-based verification, iterative debugging, harness optimization.

**Layer 3: Scaling the Harness (Multi-Agent)**
- Shared code artifacts for coordination, review, and verification across agents.
- Agent roles: manager, planner, coder, reviewer, tester.
- Collaboration modes: debate, red-teaming, adversarial interaction.
- Application domains: coding assistants, GUI/OS automation, embodied agents, scientific discovery, personalization, DevOps, enterprise workflows.

**Open challenges:** Evaluation beyond task success, verification under incomplete feedback, regression-free harness improvement, consistent shared state across multiple agents, human oversight for safety-critical actions, multimodal extensions.

### Real Benchmark Numbers

This is a survey paper -- no original benchmarks. However, it synthesizes results from 100+ cited works across SWE-bench, HumanEval, CodeGen, WebArena, and other benchmarks, providing a comprehensive taxonomy of existing approaches.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| Unifying framework connects previously siloed research | Survey paper -- provides taxonomy, not implementation |
| Three-layer model is directly mappable to any agent system | 102 pages; requires significant time investment to fully absorb |
| 42-author consensus validates the code-as-harness paradigm | Open challenges section shows the field still lacks solutions to fundamental problems |
| Companion GitHub repo tracks latest papers in the space | Rapidly evolving field means the survey will need continuous updates |

### Design Rationale

The key insight is that code serves as the "operational backbone" connecting all agent capabilities. By treating code as the unified medium for reasoning, acting, and verification, agent systems gain executability (programs can be run to verify correctness), verifiability (code has formal semantics), and statefulness (code maintains state across turns). This contrasts with pure-text approaches where reasoning and actions are only inspected, not executed.

### Transferable Idea for Lyra

**Establishes the harness as the operational backbone.** The three-layer model (Interface -> Mechanisms -> Multi-Agent Scaling) provides a maturity model for Lyra's architecture. Lyra should organize its subsystems according to these layers: harness interface (Lyra's tool/protocol definitions), harness mechanisms (Lyra's planning, memory, skill routing), and scaling the harness (Lyra's fleet coordination). The open challenges are Lyra's R&D roadmap.

### Impact x Effort Rating

**Impact: HIGH (8/10)** -- Validates Lyra's fundamental architecture and provides a maturity model for organizing subsystems.
**Effort: LOW (2/10)** -- Survey paper requiring study, not implementation. Use as reference architecture and glossary.
**Overall: 8/10 -- Adopt the three-layer taxonomy as Lyra's architectural reference model.**

---

## Paper 6: Diversity Collapse in Multi-Agent LLM Systems
**arXiv:** [2604.18005](https://arxiv.org/abs/2604.18005) | **Authors:** Nuo Chen, Yicheng Tong, Yuzhe Yang, Yufei He, Xueyi Zhang, Qingyun Zou, Qian Wang, Bingsheng He | **Venue:** ACL 2026 Findings | **Date:** April 2026 | **Code:** [Xtra-Computing/MAS_Diversity](https://github.com/Xtra-Computing/MAS_Diversity)

### Core Mechanism

A systematic empirical study of diversity in multi-agent LLM ideation across three levels, grounded in cognitive science (conceptual spaces framework from Boden 2004/2009) and group psychology (Ringelmann effect, social loafing, groupthink). The central concept is **structural coupling** -- the process where agent interaction inadvertently synchronizes trajectories and triggers diversity collapse, characterized as a collective failure rather than individual agent failure.

**Three analysis levels:**

1. **Model Level (compute efficiency paradox):** Stronger, highly-aligned models yield diminishing marginal diversity despite higher per-sample quality. Alignment acts as a "global semantic regularizer" contracting exploration.

2. **Cognition Level (authority-driven collapse):** Leader-dominated structures concentrate semantic density near zero. Flat peer topologies with experienced agents produce higher diversity -- it is the combination of hierarchy + expertise that collapses diversity, not expertise alone.

3. **System Level (communication topology):** Dense topologies accelerate premature convergence. Sparse/peer structures preserve diversity better.

**Diversity metrics:** Vendi Score (Friedman 2022) and conceptual-space-grounded metrics. Five numbered equations formalize structural coupling and diversity measurement. A stance classification rubric evaluates LLM-based diversity assessments.

### Real Benchmark Numbers

**Topology comparison (10,000+ research proposals, 20 topics):**

| Collaboration Structure | Vendi Score (Diversity) |
|---|---|
| Horizontal peer (flat topology) | **8.08** (highest) |
| Cross-disciplinary structure | **4.65** (lowest) |

Quality range across all five structures was narrow: **7.88-8.50** -- meaning diversity varies dramatically even when output quality appears similar.

**Group size scaling:** Scaling agents from 3 to 7 drops diversity utilization from 1.03 to 0.47 (new agents increasingly overlap semantically with existing ones).

**Key finding:** Dense communication topologies accelerate premature convergence. Sparse topology is a HARD requirement for creative tasks -- not a nice-to-have.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| Sparse topologies preserve semantic diversity | Sparse communication may miss useful cross-pollination |
| Flat peer structures avoid authority-driven collapse | Flat structures may lack coordination for complex tasks |
| Diversity-aware design prevents premature convergence | Requires topology engineering that adds architectural complexity |
| Applies group psychology theory to LLM collectives | Findings are from ideation tasks -- may not generalize to all agent workflows |

### Design Rationale

The authors draw on decades of group psychology research (Ringelmann 1913, Janis 1972 groupthink, Latane 1979 social loafing) and apply it to LLM collectives. The key insight is that **diversity collapse arises primarily from interaction structure, not model insufficiency** -- meaning you cannot fix it by using stronger models; you must fix the communication architecture.

### Transferable Idea for Lyra

**CRITICAL for Lyra's fleet coordination design.** Lyra's multi-agent communication topology must default to sparse rather than dense. Fleet coordination should use peer-to-peer topologies, not leader-dominated hierarchies, for creative/exploratory tasks. When agents need to coordinate, they should communicate through shared artifacts (code, documents) rather than direct dense message passing. The Veni Score provides a quantitative metric Lyra can use to monitor fleet diversity in production.

Actionable design rules for Lyra:
- Default to sparse communication graphs
- Use artifact-mediated communication (shared files, not chat)
- Monitor diversity metrics (Vendi Score) alongside quality metrics
- Reserve leader/authority roles for coordination tasks only, never for creative/exploratory tasks
- Cap group size at the point where marginal diversity gain approaches zero

### Impact x Effort Rating

**Impact: VERY HIGH (10/10)** -- This is a fundamental constraint on Lyra's fleet architecture. Getting communication topology wrong would systematically degrade fleet output quality.
**Effort: MEDIUM (5/10)** -- Requires topology-aware fleet orchestration and diversity monitoring. The concepts are clear; implementation is the work.
**Overall: 10/10 -- First-order architectural constraint. Sparse topology is mandatory for Lyra fleet.**

---

## Paper 7: STAR-Teaming -- Conjunctive Prompt Attacks via Multiplex Network Red Teaming
**arXiv:** [2604.18976](https://arxiv.org/abs/2604.18976) | **Authors:** MinJae Jung, YongTaek Lim, Chaeyun Kim, Junghwan Kim, Kihyun Kim, Minwoo Kim (SelectStar) | **Venue:** ACL 2026 Findings | **Date:** April 2026 | **Code:** [selectstar-ai/STAR-Teaming-paper](https://github.com/selectstar-ai/STAR-Teaming-paper)

### Core Mechanism

STAR-Teaming is a black-box automated red teaming framework combining a Multi-Agent System (MAS) with a Strategy-Response Multiplex Network. It converts a high-dimensional embedding space into a tractable network structure, organizing the search space into semantic communities to avoid redundant exploration.

**Architecture:**
- **Strategy communities (15):** Semantic clusters of attack strategies (e.g., role-play, encoding tricks, multi-turn deception)
- **Response communities (50):** Semantic clusters of model responses
- **Multiplex network:** Bipartite mapping between strategies and responses, with community detection preventing exploration of redundant strategy-response pairs
- **Network parameters:** Only ~750 total (15 x 50), constructed in 0.37s on CPU, with 0.02s mapping optimization and ~0.1s per strategy sampling
- **Dynamic network expansion:** Grows the network as new strategy-response clusters are discovered

**The conjunctive attack concept:** The paper demonstrates that two individually harmless prompt components can combine across the multiplex network to produce harmful outputs. Traditional single-component defenses fail because neither component alone triggers safety filters. The multiplex network discovers these conjunctive attack paths.

### Real Benchmark Numbers

**HarmBench ASR -- Overall Averages:**

| Method | Avg ASR |
|---|---|
| **STAR-Teaming** | **74.5%** |
| AutoDAN-Turbo | 61.0% |
| PAP-top5 | 45.5% |
| TAP-T | 44.8% |
| GCG | 44.3% |
| TAP | 42.3% |
| PAIR | 37.3% |
| GCG-M | 34.4% |
| GCG-T | 33.8% |
| Human | 22.1% |

**Delta:** STAR-Teaming surpasses AutoDAN-Turbo by **+13.5 percentage points** on average.

**Key target results:**

| Target Model | STAR-Teaming ASR | Best Baseline ASR |
|---|---|---|
| Claude 3.5 Sonnet | **12.0%** | 5.0% (TAP) |
| GPT-4o | **76.1%** | 76.0% (AutoDAN-Turbo) |
| Llama-2 7b chat | **71.0%** | 36.6% (AutoDAN-Turbo) |
| Gemma3-4b-it | **64.7%** | 87.8% (PAP-top5) -- interesting exception |

On Claude 3.5 Sonnet, STAR-Teaming was **the only method to exceed 10% ASR.**

**Multiplex network ablation (Llama-2-7b-chat):**

| Configuration | ASR | Self-BLEU | Gini | Pearson r (score-usage) |
|---|---|---|---|---|
| With Multiplex Network | **71.0** | 0.25 | 0.19 | 0.81 |
| Without Multiplex Network | 65.0 | 0.46 | 0.36 | -0.08 |

The network yields +6.0% ASR while reducing prompt redundancy (Self-BLEU 0.46 -> 0.25) and aligning strategy selection with success (Pearson flips from -0.08 -> 0.81).

**Dynamic network expansion:** +6.3 points ASR (71.0% -> 77.3%) while reducing average trials per seed from 61.1 to 52.4.

**StrongReject dataset (harmful score 0-1):**

| Method | Avg Harmful Score |
|---|---|
| **STAR-Teaming** | **0.52** |
| Second-best (TAP) | 0.11 |

**Delta:** +0.41 over second-best.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| +13.5 points ASR over previous SOTA | Network construction requires initial embedding computation |
| No GPU requirement (all network ops on CPU) | Multiplex network adds a layer of abstraction to understand |
| Community detection prevents redundant search | 15 strategy and 50 response communities may not cover all attack surfaces |
| Dynamic expansion adapts to new attack patterns | Attack optimization is inherently adversarial -- defenses must continuously evolve |
| Operates black-box (no model internals needed) | ASR on Claude 3.5 Sonnet still only 12%, indicating strong model-level defenses |

### Design Rationale

The multiplex network approach is motivated by the observation that prior red teaming methods explore the attack space redundantly -- generating many variations of the same effective strategy rather than discovering diverse attack paths. By organizing the search space into semantic communities and tracking strategy-response pairs, the multiplex network ensures that each new attack attempt explores a genuinely different region of the attack surface. The conjunctive attack concept formalizes a threat model where two harmless components combine across different semantic dimensions to produce harm.

### Transferable Idea for Lyra

**Routing-level defense required for Lyra's multi-model architecture.** The conjunctive attack concept directly threatens Lyra's heterogeneous model routing: two separately harmless prompts routed through different Lyra subsystems could combine to produce harmful outputs. Lyra needs:

1. **Cross-component safety analysis:** Monitor prompt combinations across subsystem boundaries, not just individual prompts
2. **Multiplex safety graph:** Maintain a safety network tracking which subsystem interactions have been probed and found safe/vulnerable
3. **Community-based defense:** Use semantic clustering of Lyra's internal prompts/actions to detect when a novel combination of individually-safe components produces a conjunctive threat
4. **Dynamic safety expansion:** Continuously probe for new conjunctive attack paths as Lyra's skill library and model roster evolve

### Impact x Effort Rating

**Impact: HIGH (8/10)** -- Security-critical for Lyra's multi-model architecture. The conjunctive attack threat model is directly relevant to any system routing prompts across heterogeneous models.
**Effort: HIGH (8/10)** -- Building a multiplex safety monitoring system is substantial engineering. However, the algorithm is well-specified and computationally lightweight (network ops on CPU).
**Overall: 7/10 -- Important security investment. Prioritize cross-component safety analysis; defer full multiplex defense if resources are constrained.**

---

## Paper 8: HASP -- Harnessing LLM Agents with Skill Programs
**arXiv:** [2605.17734](https://arxiv.org/abs/2605.17734) | **Authors:** Hongjun Liu, Yifei Ming, Shafiq Joty, Chen Zhao | **Date:** May 2026

### Core Mechanism

HASP transforms reusable agent skills from passive textual advice into **executable Program Functions (PFs)** -- typed Python objects that activate on failure-prone states and directly intervene in the agent's decision loop.

**PF Architecture:**
```
class ProgramFunction:
    should_activate(step_context, action_type, arg) -> bool
    intervene(step_context, action_type, arg, teacher=None) -> Intervention
```

**Three intervention modes:**
- MODIFY_ACTION: Rewrites or refines the next action (type and/or argument)
- INJECT_CONTEXT: Appends corrective text into the next observation
- NOOP: Abstains but emits an audit record

**Runtime safeguards:**
- Per-PF rate limit: max 2 MODIFY_ACTION fires per PF
- Per-skill episode caps (e.g., RetrievalFailurePF fires at most 3 times)
- FINAL-action override cap: 1 per episode
- Optional teacher model (GPT-4o) selects among ambiguous PF candidates

**Four-signal scoring for post-training:**
```
A_t = 0.15 * Timing_t + 0.10 * Mode_t + 0.25 * Correctness_t + 0.50 * Outcome_t
```
with trajectory-level aggregation: A(tau) = mean of A_t over all PF activations.

**Three post-training variants:**
1. HASP + SFT: Direct fine-tuning on PF-corrected actions
2. HASP + RS (Rejection Sampling): Filter trajectories by combined task-success + PF-quality score
3. HASP + OPD (On-Policy Distillation): Roll out policy with PFs active, train student on corrected behavior

**Self-improving library evolution:**
- After fixed training intervals, residual failures are summarized into candidate PFs from recurring failure-repair patterns
- Candidates pass two gates: executable validation (syntax, interface, mock execution) and teacher review (reusable pattern, appropriate firing, useful repair)
- Failed candidates are discarded; accepted ones join the library

### Real Benchmark Numbers

All results use **Qwen2.5-7B-Instruct** backbone.

**Web-search reasoning (HotpotQA, 2Wiki, MuSiQue):**

| Method | Avg Accuracy |
|---|---|
| Base model | 16.7% |
| RA-Agent (multi-loop ReAct) | 31.2% |
| Prompt-Only Skills | 20.5% |
| HASP-Intervention (PF-only) | **51.0%** |
| HASP-Intervention (w. Teacher) | **56.2%** |

**Delta:** +25% over multi-loop ReAct (inference-time only); +30.4% over Search-R1 (post-training + evolution).

**Training comparisons (web-search avg):**

| Method | Avg | Delta vs. HASP-Evolve+RS |
|---|---|---|
| SFT (vanilla) | 18.2% | +42.1 |
| Search-R1 | 29.9% | +30.4 |
| ReSearch | 37.8% | +22.5 |
| AgentFlow (Flow-GRPO) | 53.2% | +7.1 |
| **HASP-Evolve + RS** | **60.3%** | -- |

**Math reasoning:**

| Method | AIME24 | AMC23 | GameOf24 | Avg |
|---|---|---|---|---|
| Base | 6.7% | 47.5% | 33.0% | 29.1% |
| HASP-Intervention (w. Teacher) | 10.0% | 56.5% | 50.0% | 38.8% |
| HASP-Evolve + RS | 16.7% | 57.5% | 62.0% | 45.4% |

**Coding (6 benchmarks avg Pass@1):**

| Method | Avg |
|---|---|
| Base model | 60.8% |
| HASP-Intervention (w. Teacher) | 68.7% |
| HASP-Evolve + RS | 69.9% |

**Signal ablation (which signal matters most?):**

| Ablation | Avg Accuracy | Drop |
|---|---|---|
| Full (all 4 signals) | 60.3% | -- |
| w/o Timing | 52.5% | -7.8 |
| w/o Mode | 44.8% | **-15.5** |
| w/o Correctness | 48.2% | -12.1 |
| w/o Outcome | 47.5% | -12.8 |

Mode is the most critical signal -- HOW the PF intervenes matters more than raw final-answer reward.

**Filtering ablation (catastrophic without filtering):**

| Setting | Avg Accuracy | Drop |
|---|---|---|
| Full filtering | 60.3% | -- |
| No evolution (fixed library) | 59.3% | -1.0 |
| Evolution, no filtering | 36.3% | **-24.0** |

Unfiltered evolution drops performance below the base agent. Strict filtering is essential.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| +25% inference-time gain with no training | Deterministic PF execution adds latency per step |
| +30.4% with post-training over Search-R1 | Teacher model (GPT-4o) needed for ambiguous PF selection |
| Skill library self-evolves from failures | Unfiltered evolution is catastrophic (-24.0 drop) |
| PFs are interpretable Python code | Requires per-task PF engineering initially |
| 65% of interventions are action-level (not just text injection) | 8.7% of PFs produce harmful overrides that must be caught |

### Design Rationale

The key insight is that passive textual advice (prompt-only skills) is fundamentally limited -- the model may ignore the advice, misinterpret it, or apply it at the wrong time. By making skills executable (PFs that directly modify actions or inject context at specific failure-prone states), the harness gains deterministic control over agent behavior at critical decision points. The two-gate filtering system (executable validation + teacher review) is essential because unfiltered PF evolution amplifies errors rather than correcting them.

### Transferable Idea for Lyra

**Direct blueprint for Lyra's skill system evolution.** Lyra's skill library should adopt the HASP architecture:

1. **Skills as Program Functions:** Convert Lyra's current text-based skills into executable PFs with should_activate/intervene interfaces
2. **Failure-anchored activation:** PFs should activate on specific failure-prone states, not on every step
3. **Four-signal scoring:** Use Timing, Mode, Correctness, and Outcome signals (not just task success) to evaluate Lyra's skill quality
4. **Two-gate evolution:** All new Lyra skills must pass executable validation AND teacher review before joining the fleet library
5. **Rate limiting:** Per-PF caps prevent runaway interventions

The 65.1% action-level intervention rate demonstrates that skills should primarily modify decisions, not just inject text -- this is a measurable quality target for Lyra's skill system.

### Impact x Effort Rating

**Impact: VERY HIGH (9/10)** -- The PF architecture is directly mappable to Lyra's skill system. The +25% inference-time gain with zero training is immediately actionable.
**Effort: MEDIUM (6/10)** -- Requires refactoring Lyra's skill definitions into the PF interface, building the two-gate evolution pipeline, and implementing signal-based scoring.
**Overall: 9/10 -- Adopt the HASP PF architecture for Lyra's skill subsystem.**

---

## Paper 9: FORGE -- Self-Evolving Agent Memory With No Weight Updates via Population Broadcast
**arXiv:** [2605.16233](https://arxiv.org/abs/2605.16233) | **Authors:** Igor Bogdanov, Chung-Horng Lung, Thomas Kunz, Jie Gao, Adrian Taylor, Marzia Zaman (Carleton University / Defence R&D Canada / Cistel Technology) | **Venue:** ACM CAIS '26 | **Date:** May 2026

### Core Mechanism

FORGE (Failure-Optimized Reflective Graduation and Evolution) is a staged, population-based protocol that evolves prompt-injected natural-language memory for hierarchical ReAct agents without any weight updates.

**Architecture:**
1. **Inner loop (Reflexion-style):** A dedicated reflection agent converts failed trajectories into reusable knowledge artifacts in three representations:
   - **Rules:** Textual heuristics (e.g., "never deploy service X without first checking port Y")
   - **Examples:** Few-shot demonstrations of correct behavior
   - **Mixed:** Both rules and examples
2. **Outer loop (population broadcast):** The best-performing instance's memory is broadcast to the entire population between stages.
3. **Graduation criterion:** Converged instances freeze their memory -- they stop evolving and save compute.
4. **Representation choice:** Examples achieve strongest returns (3 of 4 models); Rules offer best cost-reliability profile with ~40% fewer tokens.

**Environment:** CybORG CAGE-2, a stochastic network-defense POMDP with a 30-step horizon against the B-line attacker.

### Real Benchmark Numbers

**Performance vs. baselines:**

| Model | Zero-Shot | Reflexion | FORGE | Improvement (vs. Zero-Shot) | Improvement (vs. Reflexion) |
|---|---|---|---|---|---|
| Gemini-2.5-Flash-Lite | Strongly negative | Baseline | Best | 1.7-7.7x | 29-72% |
| Grok-4-Fast | Strongly negative | Baseline | Best | 1.7-7.7x | 29-72% |
| Llama-4-Maverick | Strongly negative | Baseline | Best | 1.7-7.7x | 29-72% |
| Qwen3-235B | Strongly negative | Baseline | Best | 1.7-7.7x | 29-72% |

All four models exhibited "strongly negative, heavy-tailed zero-shot rewards."

**Delta:** FORGE improves average evaluation return by 1.7-7.7x over zero-shot, and by 29-72% over Reflexion.

**Failure reduction:** Major-failure rates (rewards below -100) reduced to as low as ~1%.

**Across all 12 model-representation conditions:** Gains hold across all conditions.

**Ablation findings:**
- **Population broadcast carries the performance gains.** A no-graduation ablation confirms broadcast is the critical mechanism.
- **Graduation primarily saves compute** (frozen instances stop expensive reflection loops).
- **Weaker models benefit more** -- FORGE may mitigate capability gaps rather than amplify strong models.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| 1.7-7.7x improvement over zero-shot | Requires population of agents (not single-instance) |
| No weight updates needed (prompt-only) | Evidence confined to CAGE-2 B-line (single environment) |
| Graduation saves compute by freezing converged instances | Cross-family findings are "directional evidence" only |
| Works across 4 model families (Gemini, Grok, Llama, Qwen) | Population broadcast adds orchestration complexity |
| Mitigates capability gaps (helps weak models more) | Memory representations must be hand-chosen (Rules/Examples/Mixed) |

### Design Rationale

The key insight is that isolated Reflexion-style learning (each agent improving independently) is suboptimal because it wastes the exploration of parallel agents. Population broadcast transmits the best discoveries across the entire fleet, creating a positive-sum game where each agent benefits from the best performer's learning. Graduation serves a complementary role: once an agent has converged, continuing to reflect wastes compute without improving performance, so freezing it frees resources for other agents still improving.

### Transferable Idea for Lyra

**Blueprint for Lyra's fleet memory evolution.** FORGE's population broadcast mechanism is directly applicable to Lyra's multi-agent fleet:

1. **Population broadcast protocol:** When any Lyra agent discovers a useful memory artifact (rule, example, or heuristic), broadcast it to all agents in the fleet
2. **Staged evolution:** Run Lyra agents in stages; between stages, identify the best-performing agent's memory and propagate it
3. **Graduation/freezing:** When a Lyra agent's performance plateaus, freeze its memory and redirect compute to agents still improving
4. **Representation choice:** Support Rules (cost-efficient, ~40% fewer tokens) and Examples (highest performance) as separate memory representations
5. **Cross-model applicability:** FORGE works across heterogeneous models -- Lyra can broadcast memories across agents using different foundation models

The finding that weaker models benefit more from population broadcast is particularly relevant for Lyra's SLM tier (Paper 1).

### Impact x Effort Rating

**Impact: HIGH (8/10)** -- Population broadcast is directly applicable to Lyra's fleet memory architecture. The 1.7-7.7x improvement numbers are compelling.
**Effort: MEDIUM (5/10)** -- Requires building the broadcast protocol and graduation logic. The algorithm is well-specified. Single-environment evidence means Lyra should validate across its own task distribution.
**Overall: 8/10 -- Implement population broadcast as Lyra's fleet memory sharing mechanism.**

---

## Paper 10: EvolveMem -- Self-Evolving Memory Architecture via AutoResearch for LLM Agents
**arXiv:** [2605.13941](https://arxiv.org/abs/2605.13941) | **Authors:** Jiaqi Liu, Xinyu Ye, Peng Xia, Zeyu Zheng, Cihang Xie, Mingyu Ding, Huaxiu Yao (UNC-Chapel Hill, UC Berkeley, UCSC) | **Date:** May 2026 | **Code:** [aiming-lab/SimpleMem](https://github.com/aiming-lab/SimpleMem)

### Core Mechanism

EvolveMem addresses a critical gap in long-term memory systems: while stored content gets updated, the retrieval infrastructure itself stays frozen. The key insight is that truly adaptive memory requires co-evolution at two levels -- both stored knowledge AND the retrieval mechanism.

**Architecture:**

1. **Structured action space:** EvolveMem exposes its full retrieval configuration as a structured action space, including retrieval strategies (e.g., recency-weighted, similarity-weighted, hybrid), chunk sizes, top-k values, reranking parameters, and embedding model selection.

2. **LLM-powered diagnosis:** A diagnosis module reads per-question failure logs, identifies root causes (e.g., "recency bias causing stale retrievals," "embedding mismatch for domain-specific queries"), and proposes targeted configuration changes.

3. **Guarded meta-analyzer:** Applies configuration changes with two safeguards:
   - **Revert-on-regression:** Automatically rolls back changes that lower overall F1
   - **Explore-on-stagnation:** Triggers exploratory searches when progress plateaus

4. **AutoResearch loop:** The system conducts iterative research cycles on its own architecture, replacing manual configuration tuning. It can discover entirely new configuration dimensions not present in the original action space.

5. **Sliding-window memory extraction:** Extracts relevant memories using temporal decay windows.

### Real Benchmark Numbers

| Benchmark | Metric | Result |
|---|---|---|
| LoCoMo | Relative improvement over strongest baseline | **+25.7%** |
| LoCoMo | Relative improvement over minimal baseline | **+78.0%** |
| MemBench | Relative improvement over strongest baseline | **+18.9%** |

**Cross-benchmark transfer:** Evolved configurations exhibit positive transfer (not catastrophic transfer) when moved between LoCoMo and MemBench, suggesting the system captures "universal retrieval principles rather than benchmark-specific heuristics."

**Convergence:** EvolveMem converges autonomously starting from a minimal baseline, discovering effective retrieval strategies without human tuning.

### Trade-off Analysis

| Gain | Cost |
|---|---|
| +25.7% on LoCoMo over strongest baseline | AutoResearch loop adds compute overhead per cycle |
| Positive transfer across benchmarks (captures universal principles) | Two safeguards add complexity to the meta-analyzer |
| Discovers new configuration dimensions autonomously | Requires structured action space to be pre-defined |
| No human tuning needed for convergence | Diagnosis quality depends on LLM's failure analysis capability |
| Revert-on-regression prevents performance collapse | Explore-on-stagnation may waste cycles on unproductive directions |

### Design Rationale

The authors observed that memory retrieval configuration is typically hand-tuned once and then frozen. This means that as the stored knowledge evolves, the retrieval mechanism becomes increasingly mismatched to the knowledge it is retrieving. By making retrieval configuration part of the same evolutionary loop as knowledge storage, EvolveMem ensures that retrieval adapts to the evolving knowledge base. The positive cross-benchmark transfer is particularly important -- it means the system is learning general principles of retrieval optimization, not overfitting to a specific benchmark.

### Transferable Idea for Lyra

**Directly applies to Lyra's memory subsystem.** Lyra's memory retrieval configuration should be self-evolving rather than statically configured:

1. **Expose retrieval config as action space:** Lyra's memory module (Section 4.x) should expose its retrieval parameters (chunk size, top-k, reranking weights, embedding model selection) as a structured action space for AutoResearch
2. **Failure-anchored diagnosis:** When Lyra agents fail due to memory issues (wrong recall, stale context, missing information), diagnose the retrieval root cause and propose targeted configuration changes
3. **Revert-on-regression:** Never deploy a retrieval configuration change without automated regression testing
4. **Cross-workload transfer validation:** Verify that retrieval improvements on one Lyra workload transfer positively to others
5. **New dimension discovery:** Allow Lyra's AutoResearch to propose entirely new retrieval dimensions (e.g., "confidence-weighted hybrid retrieval") not in the original design

### Impact x Effort Rating

**Impact: HIGH (8/10)** -- Self-evolving retrieval is a clear win for Lyra's memory system. The +25.7% on LoCoMo demonstrates substantial untapped value in retrieval optimization.
**Effort: MEDIUM (6/10)** -- Requires adding the diagnosis module, meta-analyzer with safeguards, and structured action space to Lyra's memory subsystem. The algorithm is well-specified.
**Overall: 8/10 -- Implement self-evolving retrieval for Lyra's memory subsystem.**

---

## Cross-Paper Synthesis

### Thematic Clusters

**1. Harness Architecture (Papers 3, 4, 5)**
These three papers converge on a unified message: the harness is the critical infrastructure, not an afterthought. Paper 3 provides the architectural vocabulary (six components), Paper 4 provides the optimization methodology (outer-loop code search), and Paper 5 provides the theoretical framework (code as operational substrate). Together they establish that Lyra's primary engineering investment should be in harness quality, not model selection.

**2. Model Economics (Paper 1)**
Paper 1 provides the economic foundation. SLMs can handle 40-70% of agentic calls at 10-30x lower cost. Combined with the harness-focused approach, the implication is clear: Lyra should invest in harness optimization first and use the most cost-effective model for each subtask.

**3. Fleet Topology (Paper 6)**
Paper 6 is the spoiler -- it constrains how the fleet from Papers 3-5 can be organized. Dense communication causes diversity collapse. Sparse, peer-to-peer topologies are mandatory for creative/exploratory tasks. The fleet architecture must optimize both coordination efficiency (Papers 3-5) and diversity preservation (Paper 6).

**4. Safety and Evaluation (Papers 2, 7)**
Papers 2 and 7 establish the measurement and defense infrastructure. Paper 2 ensures Lyra isn't optimizing against broken metrics. Paper 7 identifies a threat model (conjunctive attacks) that is particularly dangerous for multi-model architectures like Lyra's heterogeneous router from Paper 1.

**5. Skill and Memory Evolution (Papers 8, 9, 10)**
These three papers converge on a mechanism for continuous improvement: executable skills (HASP), population-broadcast memories (FORGE), and self-evolving retrieval (EvolveMem). The common thread is that agent subsystems should not be statically configured -- they should evolve based on observed failures, with guardrails preventing regression.

### Priority Implementation Order for Lyra

| Priority | Paper | What to Implement | Why First |
|---|---|---|---|
| P0 | Paper 3 | Six-component architectural blueprint | Foundation for all other decisions |
| P0 | Paper 6 | Sparse fleet topology + diversity monitoring | Wrong topology degrades everything else |
| P0 | Paper 2 | ABC evaluation gates | Prevents optimizing against broken metrics |
| P1 | Paper 4 | Harness optimization loop | +7.7 points, 4x token savings -- highest ROI |
| P1 | Paper 1 | SLM routing + heterogeneous model dispatch | 10-30x cost reduction for 40-70% of calls |
| P1 | Paper 8 | PF-based skill architecture | +25% inference-time gain with zero training |
| P2 | Paper 9 | Population broadcast for fleet memory | 1.7-7.7x improvement with no weight updates |
| P2 | Paper 10 | Self-evolving retrieval configuration | +25.7% on memory benchmarks |
| P3 | Paper 7 | Conjunctive attack defense | Important but can follow initial architecture |
| Ref | Paper 5 | Three-layer reference taxonomy | Ongoing reference, not a one-time implementation |

### Key Numbers at a Glance

| Paper | Metric | Magnitude |
|---|---|---|
| 1 (SLMs) | LLM calls offloadable to SLMs | 40-70% |
| 1 (SLMs) | Cost reduction per SLM call | 10-30x |
| 2 (ABC) | Performance overestimation (worst case) | 100% relative |
| 2 (ABC) | Overestimation reduction with ABC | 33% absolute |
| 4 (Meta-Harness) | Accuracy gain on text classification | +7.7 points |
| 4 (Meta-Harness) | Token reduction | 4x fewer |
| 4 (Meta-Harness) | Math accuracy gain (5 models) | +4.7 points |
| 6 (Diversity) | Diversity variation across topologies | 1.74x (4.65 vs. 8.08 Vendi) |
| 7 (STAR) | ASR advantage over previous SOTA | +13.5 points |
| 8 (HASP) | Inference-time gain (no training) | +25% |
| 8 (HASP) | Post-training gain over Search-R1 | +30.4% |
| 9 (FORGE) | Improvement over zero-shot | 1.7-7.7x |
| 9 (FORGE) | Improvement over Reflexion | 29-72% |
| 10 (EvolveMem) | Retrieval improvement (LoCoMo) | +25.7% |
| 10 (EvolveMem) | Retrieval improvement (MemBench) | +18.9% |

---

## Paper Status

All 10 papers successfully retrieved. Zero 404s.

| # | arXiv ID | Title | Status |
|---|---|---|---|
| 1 | 2506.02153 | Small Language Models are the Future of Agentic AI | FULL |
| 2 | 2507.02825 | Establishing Best Practices for Building Rigorous Agentic Benchmarks | FULL |
| 3 | 2605.26112 | From Model Scaling to System Scaling | FULL |
| 4 | 2603.28052 | Meta-Harness: End-to-End Optimization of Model Harnesses | FULL |
| 5 | 2605.18747 | Code as Agent Harness (42-author survey) | FULL |
| 6 | 2604.18005 | Diversity Collapse in Multi-Agent LLM Systems (ACL 2026 Findings) | FULL |
| 7 | 2604.18976 | STAR-Teaming: Conjunctive Prompt Attacks (ACL 2026 Findings) | FULL |
| 8 | 2605.17734 | HASP: Harnessing LLM Agents with Skill Programs | FULL |
| 9 | 2605.16233 | FORGE: Self-Evolving Agent Memory via Population Broadcast (ACM CAIS '26) | FULL |
| 10 | 2605.13941 | EvolveMem: Self-Evolving Memory Architecture via AutoResearch | FULL |
