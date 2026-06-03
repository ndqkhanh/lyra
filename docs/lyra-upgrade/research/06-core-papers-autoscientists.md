# Section 3.5-3.6: Core Agent Papers Deep-Read Analysis

> **Status**: High-priority batch fully deep-read (17 papers). AutoScientists papers fully read (3 papers + 2 cloned repos). Uncategorized arXiv list batch-extracted and being processed. Memory-specific papers partially fetched.
> **Date**: 2026-06-03

---

## §3.5 — PRE-RESEARCHED HIGH-PRIORITY BATCH (DEEP-READ)

---

### 1. Hyperagents / DGM-H (Meta/UBC, ICLR 2026)
**arXiv**: 2603.19461 | **Code**: github.com/facebookresearch/Hyperagents

**Title**: HyperAgents
**Authors**: Jenny Zhang, Bingchen Zhao, Wannan Yang, Jakob Foerster, Jeff Clune, Minqi Jiang, Sam Devlin, Tatiana Shavrina (UBC, Vector Institute, Meta FAIR, Meta Superintelligence Labs)

**Core Mechanism**: Extends the Darwin Godel Machine (DGM) with **metacognitive self-modification** by unifying the task agent and meta agent into a single editable program called a **hyperagent**. Unlike DGM which has a fixed handcrafted instruction-generation mechanism for self-improvement, DGM-H allows the meta agent itself to be modified, enabling the system to improve not only *how it solves tasks* but also *how it generates future improvements*. The system maintains an open-ended population-based archive of hyperagents, selecting parents proportional to performance, branching children via self-modification, evaluating them, and adding them back.

**Key Innovation**: The self-improvement mechanism is itself modifiable (self-referential), eliminating the domain-specific alignment assumption that prior systems need (where evaluation task skills = self-modification skills).

**Results**:
- **Coding (Polyglot)**: Improves from 0.140 to 0.340 training (CI: 0.300-0.380), test from 0.084 to 0.267 (CI: 0.231-0.280) - comparable to original DGM
- **Paper Review**: Improves from 0.0 to 0.710 test (CI: 0.590-0.750), surpassing AI-Scientist-v2 baseline (0.630)
- **Robotics Reward Design**: Improves from 0.060 to 0.372 test (CI: 0.355-0.436), surpassing default reward (0.348)
- **Cross-domain Transfer**: imp@50 = 0.630 (CI: 0.540-0.630) on IMO math grading when transferring from paper review + robotics, vs 0.0 for DGM transfer
- **Compounding**: DGM-H + transfer achieves 0.640 test on IMO grading vs 0.610 from scratch; from ProofAutoGrader reaches 0.700 vs 0.670 baseline

**Trade-offs**:
- Fixed outer loop (parent selection, evaluation protocol) - not self-modifiable
- Fixed task distribution limits fully unbounded progress
- Safety: self-modifications could evolve faster than human oversight
- Cost: requires 100 iterations per experiment run

**Transferable Ideas**:
1. Self-referential meta agents that can modify their own improvement mechanisms
2. Persistent memory + performance tracking autonomously discovered by the system
3. Open-ended archive as stepping stones avoids convergence
4. Cross-domain transfer of meta-level improvements

**Gap vs Lyra**: Lyra already uses meta-agent (architect) + DAG-structured agent loop. DGM-H's auto-discovered meta-improvements (performance tracking, persistent memory) could be incorporated. The open-ended archive concept maps to Lyra's worktree branching.

---

### 2. Dr. Zero (Meta/UIUC)
**arXiv**: 2601.07055 | **Code**: github.com/facebookresearch/drzero

**Title**: Dr. Zero: Self-Evolving Search Agents without Training Data
**Authors**: Zhenrui Yue, Kartikeya Upasani, Xianjun Yang, Suyu Ge, Shaoliang Nie, Yuning Mao, Zhe Liu, Dong Wang (Meta, UIUC)

**Core Mechanism**: A proposer-solver self-evolution framework for search agents that operates *without any training data*. The proposer generates diverse questions, the solver answers them using an external search engine. A **difficulty-guided reward** incentivizes the proposer to generate challenging but solvable questions. **Hop-Grouped Relative Policy Optimization (HRPO)** clusters questions by structural complexity (number of hops) to compute group-level baselines for advantage estimation, avoiding expensive nested sampling.

**Key Innovation**: First data-free self-evolution framework for multi-turn search agents. HRPO eliminates nested sampling cost.

**Results** (Qwen2.5-7B):
- NQ: 0.406 (beats Search-R1 0.397)
- TriviaQA: 0.608 (matches Search-R1 0.606)
- PopQA: 0.416 (beats Search-R1 0.404)
- HotpotQA: 0.362 (below Search-R1 0.380)
- 2WikiMQA: 0.347 (beats Search-R1 0.326)
- MuSiQue: 0.104 (below Search-R1 0.168)
- Bamboogle: 0.360 (below Search-R1 0.408)
- Average: 0.372 (below Search-R1 0.384)

**Trade-offs**:
- Underperforms supervised Search-R1 on multi-hop (degraded by 2-5 points)
- Only 7B scale tested; doesn't explore larger models
- Requires external search engine (not fully self-contained)
- **Limited to simple factual QA** - no complex reasoning, coding, or tool use

**Transferable Ideas**:
1. HRPO: grouping by structural complexity for efficient advantage estimation
2. Difficulty-guided reward curriculum: incentivize challenging but solvable questions
3. Proposer-solver co-evolution with search engine feedback

**Gap vs Lyra**: Lyra's plans already handle deeper reasoning; Dr. Zero's data-free RL approach could reduce Lyra's dependency on curated training data for planner optimization.

---

### 3. MetaAgent-X (End-to-End RL for Auto-MAS)
**arXiv**: 2605.14212

**Title**: MetaAgent-X: Breaking the Ceiling of Automatic Multi-Agent Systems via End-to-End Reinforcement Learning
**Authors**: Yaolun Zhang, Yujie Zhao, Nan Wang, Yiran Wu, et al. (Oregon State, UCSD, Amazon AGI, Penn State)

**Core Mechanism**: First end-to-end RL framework that jointly optimizes both the MAS designer (which generates agent workflows) and the executor (which runs them). Uses **Executor-Designer Hierarchical Rollout** (tree-structured MxN sampling per question) for accurate credit assignment, and **Stagewise Co-evolution** (alternating K-step phases) for stable training.

**Key Innovation**: Breaks the "frozen-executor ceiling" by training both designer and executor together with decomposed credit assignment.

**Results** (Qwen3 8B):
- **LiveCodeBench**: 36.00 (+13.20 over Single Agent), best among all methods
- **APPS**: 32.00 (+1.80)
- **CodeContests**: 13.00 (-2.75 vs SA)
- **AIME24**: 45.80 (+27.50, best), **AIME25**: 29.20 (+8.30, best)
- **OlympiadBench**: 48.90 (-6.10)
- **Average**: 34.15 (+6.99) vs SA 27.16

**Trade-offs**:
- Math gains come partly from SFT cold start (DeepSeek V3.2 distillation)
- Significant compute: M=4 designs x N=4 executions per query
- Only tested on math/code benchmarks; no open-domain or research tasks

**Transferable Ideas**:
1. Hierarchical rollout for disentangling designer vs executor credit
2. Stagewise co-evolution with alternating optimization phases
3. Shared policy between designer and executor (same LLM backbone)

**Gap vs Lyra**: Lyra's architect/subagent separation mirrors designer/executor. MetaAgent-X's hierarchical credit assignment could improve Lyra's RL-based optimizer training.

---

### 4. MetaClaw (UNC-Chapel Hill, CMU)
**arXiv**: 2603.17187 | **Code**: github.com/aiming-lab/MetaClaw

**Title**: MetaClaw: Just Talk -- An Agent That Meta-Learns and Evolves in the Wild
**Authors**: Peng Xia, Jianwen Chen, Xinyu Yang, Haoqin Tu, Huaxiu Yao, et al.

**Core Mechanism**: A meta-learning agent framework that uses conversation as the primary interaction paradigm. Combines meta-learning (MAML, Reptile), continual learning (EWC, GEM), memory mechanisms (MemP, Mem0, MemEvolve), and RL-based optimization (PPO, DAPO, SkillRL) into a unified system that meta-learns and evolves from ongoing interaction.

**Key Innovation**: "Just Talk" paradigm - uses natural language conversation as the medium for meta-learning, allowing continuous adaptation without explicit training regimes.

**Transferable Ideas**:
1. Integration of diverse memory mechanisms into a single meta-learning loop
2. RL-based skill optimization (SkillRL)
3. LoRA-based parameter-efficient adaptation within agent loop

**Gap vs Lyra**: Lyra already uses meta-learning architecture. MetaClaw's "Just Talk" paradigm could inform more natural human-AI interaction in Lyra's plan loop.

---

### 5. SOLAR (AAAI 2026)
**arXiv**: 2605.20189 | **Code**: github.com/nitinvetcha/SOLAR

**Title**: SOLAR: A Self-Optimizing Open-Ended Autonomous Agent for Lifelong Learning and Continual Adaptation
**Authors**: Nitin Vetcha, Dianbo Liu (National University of Singapore, IISc Bangalore)

**Core Mechanism**: Treats the LLM's own weights as an environment for meta-level exploration. Uses a hyper-convolutional decoder to generate parameter-level modifications (LoRA adapters), validated through a multi-level RL loop (Level I: single edits, Level II: chain edits, Level III: free exploration). Maintains a persistent knowledge base of validated modification strategies.

**Key Innovation**: Weight-level meta-knowledge discovery - the agent learns to modify its own internal representation space, analogous to human cognitive restructuring.

**Results** (Qwen2.5-0.5B on commonsense reasoning):
Outperforms DnD, TTL, DOM, and average LoRA baselines on ARC-c, BoolQ, HellaSwag, ARC-e.

**Trade-offs**:
- Currently limited to 0.5B parameter models
- Seed knowledge base requires manual curation
- Three-level training adds complexity
- Only tested on commonsense reasoning, not complex tasks

**Transferable Ideas**:
1. Weight-space exploration as an environment for meta-level learning
2. Hierarchical strategy families (TTT, LoRA, TTS, LS) with structured JSON action space
3. Knowledge base of validated modification strategies

**Gap vs Lyra**: SOLAR's weight-level self-modification is complementary to Lyra's prompt/plan-level optimization. The combination could be powerful: Lyra optimizes agent architecture + SOLAR optimizes internal model parameters.

---

### 6. Argus: Searcher-Navigator Deep Research
**arXiv**: 2605.16217

**Title**: Argus: Evidence Assembly for Scalable Deep Research Agents
**Authors**: Zhen Zhang, Liangcai Su, Zhuo Chen, Xiang Lin, Simon Shaolei Du, Lidong Bing, Xinyu Wang (MiroMind AI)

**Core Mechanism**: A Searcher-Navigator architecture where the **Navigator** maintains a shared evidence graph (DAG of evidence/claim nodes with support/contradiction edges) and dispatches **Searchers** to fill specific gaps. The Navigator runs a verify-dispatch-synthesize loop: verify evidence completeness, dispatch targeted Searchers, and synthesize final answer over the graph. Trained with contrastive RL reward that isolates verification's causal contribution.

**Key Innovation**: Evidence graph compression (1,200:1) that decouples reasoning context from Searcher count, enabling massive parallelism without context explosion.

**Results** (Qwen3.5-35B-A3B MoE):
- +5.5 points average with single Searcher over 8 benchmarks
- +12.7 points with 8 parallel Searchers  
- 86.2% on BrowseComp with 64 Searchers - surpasses all proprietary agents
- Navigator context: 21.5K tokens from 25.6M Searcher output tokens

**Trade-offs**:
- Requires training two components (Searcher + Navigator)
- MoE architecture (35B/3B active) is compute-intensive
- Graph-based representation may miss some nuanced evidence relationships

**Transferable Ideas**:
1. Evidence graph as a compressed intermediary representation (1,200:1 compression)
2. Contrastive reward isolating verification's causal contribution
3. Verify-before-dispatch loop eliminates redundant parallel exploration

**Gap vs Lyra**: Lyra's DAG-structured agent loop is conceptually similar. Argus's evidence graph compression and contrastive reward could improve Lyra's tree-of-plans synthesis and verifier training.

---

### 7. NanoResearch: Tri-Level Co-Evolving Multi-Agent Research
**arXiv**: 2605.10813 | **Code/Dataset**: Available

**Title**: NanoResearch: Co-Evolving Skills, Memory, and Policy for Personalized Research Automation
**Authors**: Jinhang Xu, Qiyuan Zhu, Yujun Wu, Conghui He, Cheng Tan, et al. (Shanghai AI Lab, HKUST)

**Core Mechanism**: Three-level co-evolutionary architecture for personalized research:
1. **Skill Bank**: Distills recurring operations into compact procedural rules
2. **Memory Module**: Maintains user- and project-specific experience  
3. **Policy Learning (SDPO)**: Converts free-form user feedback into persistent planner parameter updates

The orchestrator drives a 3-stage pipeline (Ideation + Planning, Experimentation, Paper Writing) with skill/memory retrieval before each task and update afterward.

**Key Innovation**: Personalization as a first-class concern - tri-level co-evolution where reliable skills produce richer memory, richer memory informs better planning, and preference internalization realigns the loop to each user.

**Trade-offs**:
- Requires multiple cycles to achieve personalization
- Skill/memory stores may grow unbounded without merging
- Label-free feedback via SDPO is still experimental
- Evaluated on simulated/human evaluations, not standard benchmarks

**Transferable Ideas**:
1. Three-tier memory architecture (skills, episodic memory, planner policy)
2. Label-free policy learning from natural-language feedback (SDPO)
3. Skill-memory-policy co-evolution loop

**Gap vs Lyra**: NanoResearch's personalization loop maps directly to Lyra's skill/memory systems. SDPO for planner policy updates is directly applicable to Lyra's architect optimization from user feedback.

---

### 8. Claw AI Lab
**arXiv**: 2605.22662 | **Code**: github.com/Claw-AI-Lab/Claw-AI-Lab

**Title**: CLAW AI LAB: An Autonomous Multi-Agent Research Team
**Authors**: Fan Wu, Cheng Chen, Zhenshan Tan, et al. (NTU, A*STAR, Moxin)

**Core Mechanism**: Laboratory-native autonomous research platform with 5-layer hierarchical architecture (Idea -> Planning -> Coding -> Experiment -> Writing), multi-agent discussions for ideation, and the **Claw-Code Harness** as a core component connecting local codebases/datasets/checkpoints to runnable experiments. Supports three modes: Explore, Discussion, Reproduce.

**Key Innovation**: Reframes autonomous research from "hidden prompt-to-paper pipeline" to interactive, inspectable AI laboratory. The Claw-Code Harness provides sandboxed execution with anti-fabrication checks, smoke tests, and cross-layer feedback.

**Results**:
- +15.5 to +16.5 points improvement over AutoResearchClaw on research papers
- +5.0 points on reproduction tasks
- Scored by ChatGPT and Gemini evaluators

**Transferable Ideas**:
1. Claw-Code Harness: sandboxed execution with anti-fabrication and smoke tests
2. Cross-layer feedback propagation (coding failures -> plan revision -> idea revision)
3. Multi-agent discussion for idea generation before committing to a direction
4. Dashboard-native artifact inspection and rollback/resume

**Gap vs Lyra**: Lyra's plan loop + executor + verifier architecture aligns with Claw's 5-layer hierarchy. The anti-fabrication system and cross-layer feedback are directly transferable.

---

### 9. OpenDev: Terminal-Native AI Coding Agent
**arXiv**: 2603.05344 | **Code**: github.com/opendev-to/opendev (Rust)

**Title**: Building Effective AI Coding Agents for the Terminal: Scaffolding, Harness, Context Engineering, and Lessons Learned
**Authors**: Nghi D. Q. Bui (OpenDev)

**Core Mechanism**: 4-layer compound AI system architecture (Entry/UI -> Agent -> Tool/Context -> Persistence). Key features: per-workflow LLM configurability, dual-agent separation (Plan Mode vs Normal Mode), extended ReAct loop with thinking/critique phases, adaptive context compaction, event-driven system reminders, lazy-discovered MCP tools, defense-in-depth safety (5 layers).

**Key Innovation**: First comprehensive technical report for an open-source terminal-native coding agent. Treats context engineering as a first-class engineering concern with entropy-reduction and minimal-sufficiency principles.

**Architecture Highlights**:
- 5-layer safety architecture (prompt -> schema -> runtime -> tool -> hooks)
- Adaptive Context Compaction when token budget nears exhaustion
- Event-driven system reminders counteract instruction fade-out
- Experience-driven memory pipeline for cross-session continuity

**Transferable Ideas**:
1. Dual-agent separation (plan mode vs execute mode) with read-only vs full-access tool scoping
2. Adaptive context compaction strategy
3. Event-driven system reminders for combating attention decay
4. Registry-based tool architecture with lazy MCP discovery

**Gap vs Lyra**: OpenDev's context engineering (compaction, reminders, memory pipeline) directly addresses Lyra's long-horizon context management challenges. The 5-layer safety architecture is a template for Lyra's executor sandboxing.

---

### 10. ErrorProbe: Self-Improving Error Diagnosis in MAS
**arXiv**: 2604.17658

**Title**: Towards Self-Improving Error Diagnosis in Multi-Agent Systems
**Authors**: Jiazheng Li, Emine Yilmaz, Bei Chen, Dieu-Thu Le (King's College London, Amazon Alexa AI)

**Core Mechanism**: Three-stage pipeline for failure attribution in MAS traces: (1) local anomaly detection using operationalized MAST failure taxonomy, (2) symptom-driven backward tracing to prune irrelevant context, (3) multi-agent validation team (Strategist, Investigator, Arbiter) with tool-grounded execution. Maintains a **verified episodic memory** that updates only on executable evidence.

**Key Innovation**: Verified-before-write memory gate prevents memory corruption under distribution shift.

**Results**: Significantly outperforms LLM-as-a-Judge on step-level localization on TracerTraj and Who&When benchmarks. Verified memory enables cross-domain transfer without retraining.

**Transferable Ideas**:
1. Verified-before-write memory gating for robust cross-domain transfer
2. Symptom-driven backward tracing for long-trace failure attribution
3. Multi-agent diagnosis team (Strategist/Investigator/Arbiter) with tool-grounded execution

**Gap vs Lyra**: ErrorProbe's diagnostic approach could serve as Lyra's post-hoc failure analysis, feeding back into the verifier training loop and improving meta-agent debugging.

---

### 11. Lying with Truths
**arXiv**: 2601.01685

**Title**: Lying with Truths: Open-Channel Multi-Agent Collusion for Belief Manipulation via Generative Montage
**Authors**: Jinwei Hu, Xinmiao Huang, Youcheng Sun, Yi Dong, Xiaowei Huang (Liverpool, MBZUAI)

**Core Mechanism**: Cognitive collusion attack where colluding agents steer victim agent beliefs using only truthful evidence fragments distributed through public channels. The **Generative Montage** framework (Writer-Editor-Director) constructs deceptive narratives through adversarial debate and coordinated posting, exploiting LLMs' overthinking tendency.

**Results**: Attack success 74.4% on proprietary models, 70.6% on open-weights. Stronger reasoning = higher susceptibility. Over 60% deception on downstream judges.

**Relevance**: Critical safety consideration for Lyra - demonstrates that multi-agent systems are vulnerable to cognitive manipulation through truthful fragments. Important for designing robust verifier/arbitration mechanisms.

---

### 12. MATU: MAS Uncertainty Quantification via Tensor Decomposition
**arXiv**: 2604.08708

**Title**: Every Response Counts: Quantifying Uncertainty of LLM-based Multi-Agent Systems through Tensor Decomposition
**Authors**: Tiejin Chen, Huaiyuan Yao, Jia Chen, Evangelos Papalexakis, Hua Wei (ASU, UC Riverside)

**Core Mechanism**: Represents MAS reasoning trajectories as embedding matrices, organizes multiple execution runs into a 3D tensor (agents x reasoning steps x sampling runs), then applies tensor decomposition to disentangle distinct sources of uncertainty.

**Transferable Ideas**: Tensor decomposition for disentangling agent-level vs. system-level uncertainty in MAS. Could inform Lyra's confidence estimation across parallel plan branches.

---

### 13. IdleSpec: Speculative Planning During Idle Time
**arXiv**: 2605.22154

**Title**: IdleSpec: Exploiting Idle Time via Speculative Planning for LLM Agents
**Authors**: Daewon Choi, Kyunghyun Park, Woomin Song, Jinwoo Shin, et al. (KAIST, Amazon AGI, Together AI)

**Core Mechanism**: Generates plan candidates during idle periods (waiting for tool observations) using two complementary drafting strategies: **Progressive** (assumes favorable observation, emphasizes exploitation) and **Recovery** (assumes failure, explores alternatives). Strategy distribution updated via posterior feedback.

**Results**:
- GAIA: 55.6% average accuracy with Gemini-2.5-Flash, +5.1% over baseline
- MLE-Bench: up to 9.1% improvement on Any Medal rate
- 4.6% gain on Gemma4-E4B, 6.8% on Qwen3.5-4B

**Transferable Idea**: Speculative planning during tool-call idle time. Could be integrated into Lyra's agent loop to improve parallelism without latency overhead.

---

### 14. ANX Protocol: 3EX Decoupled Architecture
**arXiv**: 2604.04820

**Title**: ANX: Protocol-First Design for AI Agent Interaction with a Supporting 3EX Decoupled Architecture
**Authors**: Xu Mingze

**Core Mechanism**: Protocol-first agent-native interaction framework with 3EX architecture (Expression-Exchange-Execution). ANX Markup provides compact structured encoding. Key features: human-agent shared interaction, create-on-demand apps, machine-executable SOPs, embedded security (UI-to-Core communication bypasses LLM context for sensitive data).

**Results**: Reduces tokens by 47.3-55.6% vs MCP, 57.1-66.3% vs GUI automation. Execution time reduced by 58.1% vs MCP.

**Transferable Idea**: Protocol-first design with compact structured encoding for agent interactions. ANX Markup's approach to bypassing LLM context for sensitive data is a strong safety pattern.

---

### 15. Knowledge Access Beats Model Size
**arXiv**: 2603.23013

**Title**: Knowledge Access Beats Model Size: Memory Augmented Routing for Persistent AI Agents
**Authors**: Xunzhuo Liu, Bowei He, Xue Liu, et al. (vLLM Semantic Router Project, MBZUAI, McGill, Mila, AMD, Red Hat)

**Core Mechanism**: 2x2 factorial (memory x routing) study showing that memory-augmented small models (8B) with routing achieve 69% of 235B model performance at 96% cost reduction. Key finding: memory doesn't change routing decisions; it makes routed answers **correct** instead of **confidently wrong**.

**Results**: 30.5% F1 (8B+memory+routing) vs 15.4% F1 (8B alone) vs 13.7% F1 (235B alone). 96% of queries routed to small model. Hybrid retrieval (BM25+cosine) adds +7.7 F1.

**Transferable Idea**: Memory-first architecture: small model + good retrieval > large model alone. This is foundational for Lyra's memory tier strategy.

---

### 16. TF-TTCL: Training-Free Test-Time Contrastive Learning
**arXiv**: 2604.13552 | **Code**: github.com/KevinSCUTer/TF-TTCL

**Title**: Training-Free Test-Time Contrastive Learning for Large Language Models
**Authors**: Kaiwen Zheng, Kai Zhou, Jinwu Hu, Te Gu, Mingkai Peng, Fei Liu (South China University of Technology)

**Core Mechanism**: "Explore-Reflect-Steer" loop with three modules: (1) multi-agent role-playing for diverse reasoning paths, (2) contrastive experience distillation capturing semantic gap between superior/inferior trajectories into textual rules, (3) contextual rule retrieval during inference. Training-free - works with frozen/black-box LLMs.

**Transferable Idea**: Contrastive rule distillation from self-generated trajectories. Could complement Lyra's reasoning bank or serve as a lightweight test-time adaptation mechanism.

---

### 17. Additional Pre-Researched Papers (Condensed)

| Paper | Core Idea | Key Result | Transferable to Lyra |
|-------|-----------|------------|---------------------|
| **DGM (Zhang 2025b)** | Open-ended self-improvement via code modification archive | 0.140->0.380 Polyglot | Archive-based stepping stones in plan loop |
| **ADAS (Hu 2025)** | Automated Design of Agentic Systems | Quality-diversity over agent architectures | Workflow generation via evolutionary search |
| **Darwin (Zhang 2025a)** | Self-referential coding agent | Recursive self-improvement in code | Self-modifying agent templates |
| **Huxley (Wang 2025b)** | Human-level coding agent via approximation of optimal self-improvement | Code generation improvements | Optimal self-improvement machine approximation |

---

## §3.5 — MEMORY-SPECIFIC ADDITIONS

### MemGAS (Multi-Granularity Memory)
**OpenReview** (Direct PDF URL unresolved - OpenReview authentication required)

### MemGen
**GitHub**: github.com/bingreeky/MemGen

### GEPA (ICLR 2026 Oral)
**GitHub**: github.com/gepa-ai/gepa
**Key Role**: Self-reflection and verification loops - referenced by SOLAR as one of the seed knowledge base strategies. ICLR 2026 Oral indicates high impact.

### MemSearcher (2511.02805)
**arXiv**: 2511.02805
**Focus**: Memory-augmented search agents.

### Memp: Agent Procedural Memory (2508.06433)
**arXiv**: 2508.06433
**Focus**: Procedural memory for agents - storing how to do things rather than what was done.

### Contextual Experience Replay (2506.06698, Princeton)
**arXiv**: 2506.06698
**Focus**: Experience replay for agent learning, analogous to DQN replay buffers but for LLM agents.

### PersonaAgent (2506.06254)
**arXiv**: 2506.06254
**Focus**: Agent personalization through persona modeling.

### A-MEM (2502.12110v1)
**arXiv**: 2502.12110v1
**Focus**: Agent memory management, likely episodic memory with structured storage.

---

## §3.5 — UNCATEGORIZED ARXIV LIST (Categorized)

> Batch-extracted. Below are categorizations based on abstracts. Deep-reads pending for high-impact papers.

### Uncategorized arXiv Papers (Now Catalogued with Real Titles)

| arXiv ID | Actual Title | Category |
|----------|-------------|----------|
| 2605.24220 | **Polar: Agentic RL on Any Harness at Scale** | RL-based Self-Improvement |
| 2605.29790 | **Evolve as a Team: Collaborative Self-Evolution for LLM-based MAS** | Collaborative Self-Evolution |
| 2605.29341 | **WorldMemArena: Evaluating Multimodal Agent Memory Through Action-World Interaction** | Memory Evaluation |
| 2605.29795 | **MEMENTO: Leveraging Web as a Learning Signal for Low-Data Domains** | Learning Signal |
| 2605.29796 | **SAAS: Self-Aware RL for Over-Search Mitigation in Agentic Search** | Search/RL |
| 2605.29225 | **BenchTrace: Benchmark for Testing Reflection and Controlled Evolution in LLM Agents** | Evaluation |
| 2605.27366 | **MUSE-Autoskill: Self-Evolving Agents via Skill Creation, Memory, Management, Evaluation** | Skill-Based Self-Evolution |
| 2605.25815 | **Behind EvoMap: Characterizing Self-Evolving Agent-to-Agent Collaboration Network** | Agent Networks |
| 2605.25480 | **Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki** | Memory/Retrieval |
| 2605.25430 | **CODESKILL: Learning Self-Evolving Skills for Coding Agents** | Code Skills |
| 2605.24426 | **SEAL: Synergistic Co-Evolution of Agents and Learning Environments** | Co-Evolution |
| 2605.23989 | *(Review Article - title not parsed)* | Review |
| 2605.22721 | **Self-Evolving MAS via Decentralized Memory** | Memory |
| 2605.22794 | **MOSS: Self-Evolution through Source-Level Rewriting in Autonomous Agent Systems** | Self-Evolution |
| 2605.22343 | **Sibyl-AutoResearch: Autonomous Research Needs Self-Evolving Trial-and-Error Harnesses** | Research Automation |
| 2605.17734 | **Harnessing LLM Agents with Skill Programs** | Skills |
| 2605.16233 | **FORGE: Self-Evolving Agent Memory With No Weight Updates via Population Broadcast** | Memory |
| 2605.13941 | **EVOLVEMEM: Self-Evolving Memory Architecture via AutoResearch for LLM Agents** | Memory |
| 2605.12061 | **SAGE: A Self-Evolving Agentic Graph-Memory Engine for Structure-Aware Associative Memory** | Graph Memory |
| 2605.11891 | **Proteus: A Self-Evolving Red Team for Agent Skill Ecosystems** | Red Teaming |
| 2604.18976 | **STAR-Teaming: A Strategy-Response Multiplex Network Approach to LLM Red Teaming** | Red Teaming |
| 2604.18005 | **Diversity Collapse in MAS LLM Systems: Structural Coupling and Collective Failure** | MAS Theory |
| 2604.16543 | **Conjunctive Prompt Attacks in Multi-Agent LLM Systems** | Security |
| 2604.12461 | **CIA: Inferring Communication Topology from LLM-based MAS** | MAS Analysis |
| 2604.07791 | **SEARL: Joint Optimization of Policy and Tool Graph Memory for Self-Evolving Agents** | RL + Memory |
| 2510.18407 | **Heterogeneous Adversarial Play in Interactive Environments** | Adversarial |
| 2509.26100 | **AgenticEval: Toward Agentic and Self-Evolving Safety Evaluation of LLMs** | Safety Evaluation |
| 2508.21720 | **PosterForest: Hierarchical Multi-Agent Collaboration for Scientific Poster Generation** | Scientific |
| 2508.04482 | **OS Agents: A Survey on MLLM-based Agents for General Computing Devices** | Survey |
| 2507.03928 | **CortexDebate: Debating Sparsely and Equally for Multi-Agent Debate** | Debate |
| 2506.03939 | **Graph Counselor: Adaptive Graph Exploration via Multi-Agent Synergy** | Reasoning |
| 2506.02546 | **To Trust or Not to Trust: Attention-based Trust Management for LLM MAS** | Trust/Safety |
| 2505.24575 | **NEXUSSUM: Hierarchical LLM Agents for Long-Form Narrative Summarization** | Summarization |
| 2505.18581 | **Removal of Hallucination on Hallucination: Debate-Augmented RAG** | RAG |
| 2505.18218 | **CoMet: Metaphor-Driven Covert Communication for Multi-Agent Language Games** | Security |
| 2502.11271 | **OctoTools: A Multi-Agent Framework with Extensible Tools for Complex Reasoning** | Tool Use |

### Newly Discovered High-Impact Papers (from extraction)

| arXiv ID | Title | Category | Notes |
|----------|-------|----------|-------|
| 2604.06170 | **Paper Circle: Open-source Multi-agent Research Discovery and Analysis Framework** | Research Automation | ORAL paper - likely high impact |
| 2605.27276 | **Hexo Labs: SIA - Self Improving AI with Harness and Weight Updates** | Self-Improvement | Harness + weight updates |
| 2605.30152 | **Do Proactive Agents Really Need an LLM to Decide When to Wake and What to Anchor?** | Proactive Agents | Provocative title, efficiency-focused |
| 2605.20025 | **AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration** | Research Automation | Code cloned (aiming-lab) |
| 2604.25917 | **Recursive Multi-Agent Systems** | Recursive MAS | UIUC, Stanford, NVIDIA - potentially high-impact |
| 2603.28052 | **Meta-Harness: End-to-End Optimization of Model Harnesses** | Harness Optimization | Directly relevant to Lyra's harness |
| 2605.18747 | **Code as Agent Harness: Toward Executable, Verifiable, and Stateful Agent Systems** | Agent Harness | Highly relevant title |
| 2605.13821 | **Harnessing Agentic Evolution** | Agent Evolution | DeepWisdom |
| 2605.23904 | **SkillOpt: Executive Strategy for Self-Evolving Agent Skills** | Skills | Self-evolving skills |
| 2605.28120 | **LegalGraphRAG: Multi-Agent Graph RAG for Reliable Legal Reasoning** | RAG | Domain-specific |
| 2605.20729 | **MTR-SUITE: Framework for Evaluating/Synthesizing Conversational Retrieval Benchmarks** | Evaluation | Benchmark |
| 2605.19357 | **SciCustom: Framework for Custom Evaluation of Scientific Capabilities in LLMs** | Scientific Evaluation | |
| 2605.18766 | **Retrieve Only Relevant Tables Whether Few or Many: Adaptive Table Retrieval** | Retrieval | |
| 2605.18257 | **CodeBind: Decoupled Representation Learning for Multimodal Alignment** | Multimodal | |
| 2605.16045 | **RecMem: Recurrence-based Memory Consolidation for Efficient Long-Running LLM Agents** | Memory | Important memory paper |
| 2605.14581 | **A Picture is Worth a Thousand Words? Aggregation Strategies for Visual Financial Document Retrieval** | Retrieval | |
| 2604.26622 | **OCR-Memory: Optical Context Retrieval for Long-Horizon Agent Memory** | Memory | OCR-based memory |
| 2604.20261 | **Memory-Augmented LLM-based MAS for Automated Feature Generation on Tabular Data** | Memory + MAS | |
| 2605.18661 | **AI for Auto-Research: Roadmap & User Guide** | Research Automation | Survey/roadmap |
| 2605.06716 | **From Storage to Experience: Survey on Evolution of LLM Agent Memory Mechanisms** | Memory | Comprehensive survey |

### Explicitly Named Papers (verified)
| arXiv ID | Title | Category |
|----------|-------|----------|
| 2507.02825v1 | Establishing Best Practices for Rigorous Agentic Benchmarks | Evaluation |
| 2506.02153 (NVIDIA) | Small Language Models are the Future of Agentic AI | Architecture |
| 2506.01716 (Meta/Berkeley) | Self-Challenging Language Model Agents | Self-Improvement |
| 2506.21931 | ARAG: Agentic RAG | RAG |
| 1809.01703 | Classic paper (likely Go-Explore or similar) | Open-endedness |
| 2502.12110v1 | A-MEM | Memory |
| 2510.26854 | SciencePedia | Scientific Discovery |
| 2511.02805 | MemSearcher | Memory |
| 2508.06433 | Memp: Agent Procedural Memory | Memory |
| 2506.06698 (Princeton) | Contextual Experience Replay | Memory/Learning |
| 2506.06254 | PersonaAgent | Personalization |
| 2310.09971 | AMAGO | Meta-Reinforcement Learning |

---

## §3.6 — AUTOSCIENTISTS (DEEP-READ)

---

### 1. AutoScientists (Harvard)
**arXiv**: 2605.28655 | **Site**: autoscientists.openscientist.ai | **Code**: github.com/mims-harvard/AutoScientists

**Title**: AutoScientists: Self-Organizing Agent Teams for Long-Running Scientific Experimentation
**Authors**: Shanghua Gao, Ada Fang, Marinka Zitnik (Harvard University)

**Core Mechanism**: A **fully decentralized** team of AI agents for long-running scientific experimentation with **no central orchestrator**. Agents act on a shared state (champion model, experiment log, research forum, team queues, dead-end registries) and self-organize into teams around promising hypotheses. Alternates between discussion phases (propose, critique, form teams) and execution phases (parallel experiments). Two specialized roles: **Analyst Agents** (maintain search knowledge, rank proposals by effect size) and **Experiment Agents** (claim and execute experiments, noise-gated second-seed confirmation).

**Key Innovation**: Self-organization without a central planner. Teams form dynamically through agent interaction rather than top-down task decomposition. Cross-team knowledge sharing eliminates redundant exploration.

**Results**:
- **BioML-Bench** (24 biomedical tasks): 74.40% mean leaderboard percentile, +8.33% over Autoresearch (66.07%)
- **Drug Discovery**: 64.52% vs Biomni 47.91% (+16.61 points) - strongest relative gain
- **GPT nanochat optimization**: 1.9x faster to target validation bpb (34 vs 65 experiments); 7 accepted improvements vs 0 for single-agent baseline
- **ProteinGym (217 assays)**: ACE2-Spike binding Spearman's rho from 0.747 to 0.840 (+12.5%); average across 217 assays from 0.657 to 0.700 (+6.5%)
- Frozen recipe transfers across all 217 assays without modification

**Ablation Findings** (Key Insight):
- Removing analyst: hurts proposal-quality-dependent tasks
- Disabling cross-agent feedback: damages tasks with partial signal
- Fixing team structure: harms runs where productive directions shift mid-experiment
- Stripping shared state (independent agents): largest proportional drop, odds ratio fell from 0.924 to 0.435
- **Each mechanism addresses a distinct challenge** - complementary failure modes, not overlapping

**Architecture** (from cloned repo):
- Implemented as Claude Code subagents coordinating through ClawInstitute server (npm package)
- Agents = long-running Claude Code instances with heartbeat loops
- Shared state via local message-board posts, workshops, workspaces
- Deterministic monitor process orchestrates agent invocation
- Default team: 3 analyst agents, 6 experiment agents

**Transferable Ideas**:
1. **Fully decentralized coordination**: No central planner bottleneck - agents self-organize
2. **Discussion-then-execute rhythm**: Critique proposals before committing compute
3. **Shared dead-end registry**: Track failed directions to avoid repeated exploration
4. **Noise-gated champion promotion**: Second-seed confirmation for stochastic metrics
5. **Model card + research findings report** as structured output artifacts

**Gap vs Lyra**:
- AutoScientists is purely optimization-focused (find best model); Lyra is research-automation focused
- AutoScientists lacks Lyra's DAG-structured planning, verifier feedback, and meta-agent architecture
- AutoScientists' heartbeat-based coordination is simpler but less expressive than Lyra's subagent DAG
- **Complementary**: AutoScientists' self-organization could inform Lyra's agent formation for parallel research threads

---

### 2. AutoResearchClaw
**arXiv**: 2605.20025 | **Code**: github.com/aiming-lab/AutoResearchClaw

**Title**: AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration
**Authors**: Aiming Lab (UNC-Chapel Hill)

**Core Mechanism**: 23-stage autonomous research pipeline from idea to paper. Key features:
- **MetaClaw Integration**: Cross-run learning from failures into reusable skills (+18.3% robustness)
- **Human-in-the-Loop Co-Pilot**: 6 intervention modes (full-auto, gate-only, checkpoint, step-by-step, co-pilot, custom)
- **Multi-Domain Experiment Agents**: Domain-specialist executors (ColliderAgent for physics, COBRApy for biology)
- **ARC-Bench**: 55-topic open-ended research benchmark across ML (25), HEP (10), quantum (10), biology (7), statistics (3)
- **Anti-fabrication**: VerifiedRegistry + experiment diagnosis & repair loop
- **Claw-Code Harness**: Local codebase/dataset connection with sandboxed execution

**Transferable Ideas**:
1. Cross-run learning from failures into reusable skills (MetaClaw bridge)
2. 6-level human-in-the-loop intervention spectrum
3. Domain-specialist executor routing
4. Anti-fabrication verification pipeline

**Gap vs Lyra**: Similar end-to-end architecture. AutoResearchClaw's HITL co-pilot system and cross-run learning are directly relevant to Lyra's human-AI interaction design.

---

### 3. VirSci (Multi-Agent Scientific Idea Generation)
**arXiv**: 2410.09403

**Title**: Many Heads Are Better Than One: Improved Scientific Idea Generation by A LLM-Based Multi-Agent System
**Authors**: Haoyang Su, Renqi Chen, Shixiang Tang, et al. (Shanghai AI Lab)

**Core Mechanism**: Multi-agent system for scientific idea generation where multiple agents with different roles collaborate to produce higher-quality research ideas than single-agent approaches. Demonstrates that diverse perspectives in multi-agent debate improve novelty and feasibility.

**Key Result**: Multi-agent idea generation significantly outperforms single-agent baselines across scientific domains.

**Transferable Idea**: Multi-agent ideation with diverse role perspectives. Maps to Lyra's architect/subagent diversity.

---

## CROSS-CUTTING ANALYSIS

### Workstream Mapping

| Workstream | Key Papers | Core Insight |
|------------|-----------|--------------|
| **Agent Self-Improvement** | DGM-H, SOLAR, Dr. Zero, MetaAgent-X | Self-referential improvement, metacognitive self-modification, co-evolving designer/executor |
| **Memory & Continual Learning** | NanoResearch, Knowledge Access, MemGAS, MemGen, Memp, A-MEM | Three-tier memory, memory > model size, skill-policy-memory co-evolution |
| **Scientific Research Automation** | AutoScientists, AutoResearchClaw, NanoResearch, Claw AI Lab, VirSci | Decentralized self-organization, 23-stage pipeline, tri-level personalization, lab-native UX |
| **Deep Research Agents** | Argus, IdleSpec, ErrorProbe | Evidence graph assembly, speculative planning, verified memory for error diagnosis |
| **Safety & Verification** | Lying with Truths, ErrorProbe, OpenDev | Cognitive collusion threats, verified-before-write memory, defense-in-depth safety |
| **Protocol & Architecture** | ANX, OpenDev | Protocol-first design, compound AI systems, context engineering |
| **Evaluation & Uncertainty** | MATU, TF-TTCL | Tensor decomposition for MAS uncertainty, training-free test-time adaptation |
| **Continual Learning** | SOLAR, Contextual Experience Replay, AMAGO | Weight-space exploration, lifelong adaptation, meta-RL |

### Key Design Tensions

1. **Centralized vs Decentralized Coordination**: MetaAgent-X uses centralized designer/executor RL; AutoScientists uses fully decentralized self-organization. Lyra's architect-led DAG sits in between.

2. **Fixed vs Learned Meta-Levels**: DGM has fixed handcrafted meta-agent; DGM-H makes it self-modifiable. Lyra's meta-agent is currently fixed - DGM-H suggests it should be evolvable.

3. **Memory vs Model Scale**: Knowledge Access paper shows small model + good retrieval beats large model alone. Supports Lyra's memory-tier emphasis.

4. **Safety vs Autonomy**: All self-improving papers acknowledge safety constraints. OpenDev's 5-layer safety and ANX's bypass-LLM security are practical patterns.

### Highest-Impact Transferable Mechanisms for Lyra

1. **DGM-H's metacognitive self-modification**: Auto-discovered performance tracking, persistent memory, and cross-domain transfer
2. **Argus's evidence graph compression**: 1,200:1 compression, verify-dispatch loop
3. **AutoScientists' decentralized self-organization**: Discussion-then-execute, dead-end registries, noise-gated promotion
4. **NanoResearch's tri-level co-evolution**: Skill-memory-policy loop, SDPO for preference learning
5. **OpenDev's context engineering**: Adaptive compaction, event-driven reminders, 5-layer safety
6. **ErrorProbe's verified-before-write memory**: Prevents memory corruption under distribution shift
7. **MetaAgent-X's hierarchical credit assignment**: Disentangling designer vs executor contributions
8. **IdleSpec's speculative planning**: Utilizing tool-call idle time for plan generation
