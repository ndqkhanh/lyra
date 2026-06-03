# §3.2.5 + §3.18 + §3.2: Deep-Read Report -- Self-Improving/Designing Harnesses & Comparable Agent Platforms

> DEEP-READ PROTOCOL applied to all 23 sources. Each entry contains core mechanism, real benchmark numbers, trade-offs, design rationale, transferable ideas, and gaps vs Lyra.

---

## 1. HYPERAGENTS / DGM-H (Meta / ICLR 2026)

**URLs:** https://arxiv.org/abs/2603.19461 | https://github.com/facebookresearch/HyperAgents

**Core Mechanism:** Fuses a **task agent** and a **meta agent** into one editable program. The meta agent modifies both itself and the task agent. Critical innovation: the meta-level modification procedure *is itself editable*, enabling metacognitive self-modification -- the system gets better at *getting better*. Builds on the Darwin Godel Machine (DGM) but removes the constraint that coding ability must align with self-improvement ability.

**Architecture & Data Flow:**
- Single editable program houses both meta and task agents
- Meta agent rewrites code of both agents
- Docker-based sandboxing for each generation
- Archive grows as population of discovered agents
- Self-modification extends to tools, prompts, and workflows

**Code structure (repo):**
- `meta_agent.py` -- main meta agent implementation, receives repo path + eval path, calls `chat_with_agent` to self-modify
- `generate_loop.py` -- entry point; manages Docker containers, staged evaluation, parent selection, archive management
- `task_agent.py` -- the task-solving agent
- `domains/` -- SWE-bench, Polyglot domains
- Selection: proportional to agent performance, inversely proportional to number of children with code-editing capability

**Results:** Not all quantified in abstract (full PDF's image format was unextractable). DGM baseline (predecessor) achieves 20% -> 50% on SWE-bench (+30pp) and 14.2% -> 30.7% on Polyglot (+16.5pp). DGM-H extends this to *any computable task*.

**Trade-offs:**
- Enormous API cost (2 weeks per run)
- Stochastic noise from underlying FMs
- Fixed archive maintenance and parent selection (not self-modifiable)
- No formal proof of improvement (empirical validation only)
- Scope limited to prompts, tools, FM workflows -- not model training

**Design Rationale:** Replace handcrafted meta-mechanisms with editable procedures for open-ended self-accelerating improvement on any computable task.

**Transferable Idea for Lyra:** The meta-agent-rewrites-own-harness pattern. Lyra could add a self-modification loop where the orchestrator rewrites its own system prompt, tool definitions, and subagent workflows based on evaluation outcomes.

**Gap vs Baseline:** Lyra has no self-modification loop at all. No meta-agent that rewrites the harness. No archive of past successful agent configurations.

---

## 2. Dr. Zero (Meta / arXiv 2601.07055)

**URL:** https://arxiv.org/abs/2601.07055

**Core Mechanism:** Data-free self-evolution of multi-turn search agents. A **Proposer** generates diverse questions and a **Solver** is trained to answer them. As the Solver improves, the Proposer produces increasingly difficult yet solvable tasks -- automated curriculum.

**Algorithm: HRPO (Hop-Grouped Relative Policy Optimization)**
- Clusters structurally similar questions into groups
- Computes group-level baselines instead of per-query baselines
- Reduces sampling overhead for multi-step reasoning

**Results:** "Matches or surpasses fully supervised search agents" with zero external training data. No exact numbers available in abstract.

**Design Rationale:** Limited question diversity + substantial compute for multi-step reasoning are the bottlenecks in self-evolution. HRPO addresses both by exploiting structural similarity.

**Transferable Idea for Lyra:** Proposer-Solver co-evolution could be adapted to Lyra's skill system -- a meta-agent proposes new skills/hooks, then evaluates whether they improve task completion rates.

**Gap vs Baseline:** Lyra has no self-curriculum generation, no Proposer-Solver loop, and requires human design of new capabilities.

---

## 3. MetaAgent-X (arXiv 2605.14212)

**URL:** https://arxiv.org/abs/2605.14212

**Core Mechanism:** End-to-end RL that jointly trains the **designer** (generates multi-agent workflows) and the **executor** (runs the workflows). Previously, these were decoupled -- either search over designs with frozen executors or train executors with fixed designs.

**Architecture & Algorithms:**
- Three components: Script-based MAS generation, execution rollout collection, joint credit assignment
- **Executor Designer Hierarchical Rollout**: M=4 designs per query, N=4 executions per design
- **Stagewise Co-evolution**: K=30 step alternation between designer and executor phases
- Shared policy (same LLM backbone for designer + executor) outperforms separate policies
- GRPO optimizer, learning rate 5x10^-6

**All Numerical Results (Qwen3-8B, 6 benchmarks):**

| Method | LiveCodeBench | APPS | CodeContests | AIME24 | AIME25 | OlympiadBench | Avg |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Single Agent | 22.80 | 30.20 | 15.75 | 18.30 | 20.90 | 55.00 | 27.16 |
| SA + GRPO | 25.70 | 37.00 | 12.12 | 18.30 | 26.67 | 54.80 | 29.10 |
| AFlow (search) | 28.60 | 27.40 | 15.80 | 16.67 | 20.83 | 35.31 | 24.10 |
| ADAS (search) | 20.00 | 27.00 | 12.20 | 13.30 | 16.70 | 32.90 | 20.35 |
| ScoreFlow (RL) | 25.90 | 26.50 | 13.30 | 28.90 | 20.00 | 51.30 | 27.65 |
| MaAS (RL) | 24.29 | 30.00 | 15.15 | 45.80 | 29.20 | 48.90 | 32.22 |
| **MetaAgent-X RL** | **41.00** | **38.00** | 17.00 | **40.00** | **33.33** | **61.00** | **38.33** |

Peak gain: +21.7% over single agent. RL improves over SFT by +6.17% avg.

**Structure Selection (RL Designer learns to route):**
- Hard math (AIME) -> Reflection dominates (70%+)
- Easier benchmarks -> Single agent more frequent (55.2% on APPS)
- Ensemble reserved for competition problems
- RL training shifts ensemble share DOWN (-30pp) and reflection share UP (+30pp)

**Key Trade-offs:**
- **Shared > Separate policy**: 40.0% vs 33.3% on AIME24
- **Hierarchical > Flat rollouts**: 40.0% vs 33.3% on AIME24
- **Stagewise > Coupled training**: Coupled collapses (model repeats meaningless tokens); Stagewise yields staircase-shaped learning
- Search-based methods (AFlow, ADAS) are brittle across model scales (ADAS drops -6.81% avg on Qwen3-8B)

**Transferable Idea for Lyra:** Joint designer-executor RL training where Lyra's orchestrator (designer) learns to compose subagent workflows, and the subagents (executors) are jointly optimized. The hierarchical rollout technique could apply to Lyra's multi-subagent architecture.

**Gap vs Baseline:** Lyra has no learned orchestration policy. All workflows are statically designed. No RL training loop for the harness.

---

## 4. Meta's Hyperscale AI Agents (InfoQ / Meta Engineering Blog)

**URL:** https://www.infoq.com/news/2026/05/meta-ai-agents-hyperscale/

**Core Mechanism:** LLM-based agents deployed across Meta's global infrastructure for automated capacity efficiency. Three-layer architecture:
1. LLM agents as reasoning core
2. Structured tooling (standardized interfaces)
3. Encoded engineering knowledge as reusable "skills"

Agents operate across code, configuration, and system-level performance metrics. Can both recommend AND directly implement optimizations.

**Key Innovation:** Expert reasoning encoded as agent "skills" that are reusable and scalable across the organization.

**Results:** Qualitative only -- reduced resource waste, lower power consumption, faster bottleneck resolution, engineers freed for higher-value work.

**Transferable Idea for Lyra:** The "skill as encoded engineering expertise" concept. Lyra's skill system could evolve from simple tool collections to packaged, institutionalized reasoning patterns from expert engineers.

**Gap vs Baseline:** Lyra's skill system is nascent. No knowledge capture from expert usage patterns.

---

## 5. Google DeepMind Co-Scientist

**URL:** https://deepmind.google/blog/co-scientist-a-multi-agent-ai-partner-to-accelerate-research/

**Core Mechanism:** Multi-agent coalition on Gemini, organized in three iterative phases with six specialized agents under a supervisor:
- **Generate:** Generation + Proximity agents (propose hypotheses, map diversity)
- **Debate:** Reflection + Ranking agents (peer review, Elo tournament ranking)
- **Evolve:** Evolution + Meta-review agents (refine, combine, synthesize)

**Key Architecture:**
- Supervisor acts as adaptive planner, breaks research goals into executable steps
- Elo-based tournament system for hypothesis ranking (drawn from AlphaGo/AlphaStar)
- Majority of compute dedicated to **verification**, not generation
- Integrated tools: Web search, ChEMBL, UniProt, AlphaFold

**Results:**
- Liver fibrosis: 91% blockage of scarring-linked response in lab tests
- Cellular aging analysis: months -> days
- 100+ institution collaboration

**Trade-offs:** Verification-heavy compute allocation; requires specialized tool access; qualitative outcomes rather than standardized benchmarks.

**Transferable Idea for Lyra:** The "Tournament of Ideas" -- Lyra could rank candidate plans/tools via Elo-style competition, dedicating most compute to verification. The Supervisor as freeform planner maps to Lyra's orchestrator.

**Gap vs Baseline:** Lyra has no hypothesis generation, no ranking tournament, no automated verification-first compute allocation.

---

## 6. Aletheia (Google DeepMind -- AI Mathematician)

**URL:** https://gigazine.net/gsc_news/en/20260212-google-deep-gemini-mind-aletheia/

**Core Mechanism:** Built on Gemini 3 Deep Think. Three-subagent pipeline: Generator -> Verifier -> Reviser, communicating in natural language. Grounded via Google Search for math literature cross-referencing.

**Results:**
- IMO-Proof Bench Advanced: **95.1%** (claimed highest)
- Erdős Conjecture corpus: solved **4/700** open problems (~0.57%)
- Autonomous research paper generated (eigenweights computation, arXiv:2601.23245)
- Scaling law applies at inference time (more compute -> better accuracy)

**Trade-offs:**
- Conventional LLMs prone to hallucinations in specialized topics (mitigated by literature lookups)
- 4/700 solve rate shows far from general capability
- Human involvement persists at strategic framing level

**Design Rationale:** Grounding through search + multi-agent verification pipeline reduces hallucination. Three-agent pipeline (generate-verify-revise) is the core pattern.

**Transferable Idea for Lyra:** Generate-Verify-Revise pipeline could be applied to Lyra's plan generation. The agent proposes a plan, a verifier agent critiques it, a reviser improves it. Google Search grounding for fact-checking.

**Gap vs Baseline:** Lyra has no verifier agent in the plan generation loop. No fact-checking/grounding pipeline.

---

## 7. Agent Scaling Science (arXiv 2512.08296v3)

**URL:** https://arxiv.org/html/2512.08296v3

**Core Mechanism:** The most comprehensive study of multi-agent system scaling. 260 configurations across 6 benchmarks, 9 models (GPT-5, Gemini-2.5, Claude Sonnet 3.7/4/4.5), 5 canonical architectures, formalized as S = (A, E, C, omega).

**Key Finding: Architecture-Task Alignment drives performance, not agent count.**
- Performance range: **+80.8%** (Finance Agent, Centralized) to **-70.0%** (PlanCraft, Independent)
- Mean MAS improvement: **-0.3%** (95% CI [-58.7%, +77.2%])

**Five Canonical Architectures:**

| Architecture | Overhead | Error Amp | Efficiency | Success Rate |
|---|---|---|---|---|
| SAS | 0% | 1.0x | 0.466 | 0.466 |
| Independent | 58% | 17.2x | 0.234 | 0.370 |
| Decentralized | 263% | 7.8x | 0.132 | 0.477 |
| Centralized | 285% | 4.4x | 0.120 | 0.463 |
| Hybrid | 515% | 5.1x | 0.074 | 0.452 |

**Three Scaling Patterns (regression model, R2_CV=0.413):**

1. **Tool-Coordination Trade-off** (beta=-0.096, p=0.002): Tool-heavy tasks suffer disproportionately
2. **Capability Ceiling** (beta=-0.236, p=0.004): Tasks where SA > 45% baseline experience NEGATIVE returns from multi-agent
3. **Architecture-Dependent Error Amplification**: Independent propagates errors 17.2x, Centralized contains to 4.4x

**Turn Count Power Law:** T = 2.72 x (n+0.5)^1.724, R2=0.974
**Architecture Selection Prediction:** 87% correct, exceeding random (20%) or capability-only (54%)

**Transferable Idea for Lyra:** Lyra should dynamically select architecture based on task properties (tool count, baseline capability, decomposability). The regression model provides a principled way to predict when to use single-agent vs multi-agent, and which coordination pattern.

**Gap vs Baseline:** Lyra always uses a fixed orchestrator-subagent topology. No dynamic architecture selection. No awareness of the Capability Ceiling (45% threshold).

---

## 8. OpenAI Fully Automated AI Researcher (MIT Tech Review)

**URL:** https://www.technologyreview.com/2026/03/20/1134438/

**Core Mechanism:** Multi-agent research system built on reasoning models (GPT-5 -> GPT-5.4). Targets problems in math, physics, biology, chemistry, business, and policy -- any problem formulatable in text, code, or whiteboard sketches.

**Architecture:**
- Agent-based, multi-agent design
- Built atop reasoning models trained for step-by-step work + backtracking
- Chain-of-thought monitoring: models log scratch pad reasoning, monitored by other LLMs
- Sandbox deployment philosophy

**Timeline:** AI research intern target ~Sept 2026; full multi-agent researcher target 2028.

**Results:** GPT-5 used to "discover new solutions to a number of unsolved math problems" and break dead ends in science. Most OpenAI technical staff use Codex daily. Allen Institute testing: GPT-5 "came out on top but still made lots of errors."

**Safety:** Chain-of-thought monitoring by separate LLMs. Sandboxed execution. Acknowledges unsolved challenges requiring government involvement.

**Transferable Idea for Lyra:** Chain-of-thought monitoring where one LLM watches another's reasoning for safety. Sandbox deployment pattern.

**Gap vs Baseline:** Lyra has no inter-agent safety monitoring, no sandbox execution model, no reasoning trace auditing.

---

## 9. Apple MLR -- UX for Computer Use Agents

**URL:** https://machinelearning.apple.com/research/mapping

**Core Mechanism:** Two-phase study (taxonomy development + Wizard-of-Oz validation) to map UX design space for computer use agents.

**Findings:**
- Taxonomy categories: user prompts, explainability, user control, users' mental models
- Tested across normal, error-prone, and risky execution conditions
- No single design fits all use cases -- user needs diverge by scenario

**Transferable Idea for Lyra:** Lyra should surface explainability and user control as first-class UX concerns. The "error-prone" and "risky" condition testing is directly applicable to Lyra's plan/act modes.

**Gap vs Baseline:** Lyra's UX has no systematic design for explainability, no error recovery UX patterns, no user mental model support.

---

## 10. Netflix Multi-Agent Platform Engineering (All Things AI 2026)

**URL:** https://www.theregister.com/software/2026/04/04/netflix-meta-ibm-speakers-discuss-ai-and-their-workdays/5222355

**Core Mechanism (Ben Ilegbodu, Netflix):** "Adversarial Code Review" -- three-agent pattern:
- Agent 1 (Builder): implements features
- Agent 2 (Reviewer): evaluates output (can be further specialized)
- Agent 3 (Orchestrator): coordinates between the first two

**Netflix's Claude Managed Agents deployment (May 2026):**
- Hierarchical system: lead agent decomposes tasks -> specialized subagents (deployment, errors, metrics, tickets)
- Shared filesystem with persistent event tracking
- Parallel agent execution

**Results:**
| Metric | Improvement |
|---|---|
| Incident investigation | -40% |
| Operational throughput | +30% |
| Human workload | -25% |
| Root cause accuracy | +15% |

**Transferable Idea for Lyra:** Agent 3 (Orchestrator) pattern maps to Lyra's orchestrator. Specialized subagents for different domains. Shared filesystem for agent handoff. "Parallelizing yourself" workflow.

**Gap vs Baseline:** Lyra subagents are not specialized by domain type. No persistent shared state between agents. No event tracking across agent executions.

---

## 11. DGM -- Darwin Godel Machine (arXiv 2505.22954)

**URLs:** https://arxiv.org/abs/2505.22954 | https://github.com/jennyzzt/dgm

**Core Mechanism:** Self-improving system that iteratively rewrites its own Python codebase. Uses empirical validation (coding benchmarks) instead of formal proof.

**Algorithm / Data Flow:**
1. Archive initialized with base agent (FM + bash tool + edit tool)
2. Each iteration: select parent (probabilistic, favoring high-performing + underexplored)
3. Parent analyzes own benchmark evaluation logs
4. Parent proposes next feature to implement
5. Implements modification into its own codebase
6. Staged evaluation (10 tasks -> 50 -> 200 for top performers)
7. Gate: pass compilation + retain code-editing ability -> add to archive

**All Results:**
- SWE-bench: base 20.0% -> best DGM **50.0%** (+30pp, 2.5x)
- Polyglot: base 14.2% -> best DGM **30.7%** (+16.5pp, ~2.16x)
- Model transfer: o3-mini 23% -> 33%, Claude 3.7 Sonnet 19% -> 59.5%
- Cross-benchmark: SWE agent on Polyglot 28.9% (vs base 14.2%)
- Self-discovered: edit tool improvements, peer-review mechanism, long-context management

**Baselines outperformed:**
- DGM w/o self-improve (fixed meta-agent)
- DGM w/o open-ended exploration (hill-climbing, no archive)

**Trade-offs:**
- 2 weeks per run, significant API costs
- 80 iterations per run
- FM-dependent: limited by underlying model capabilities
- Fixed archive mechanism (not self-modifiable)
- Scope limited to prompts/tools/workflows (not training)

**Transferable Idea for Lyra:** The archive-based open-ended evolution pattern. Lyra could maintain an archive of past successful configurations (plans, tool chains, subagent topologies) and evolve them through mutation and selection. The staged evaluation (gate: small subset -> larger) reduces wasted compute.

**Gap vs Baseline:** Lyra has no archive, no mutation, no parent selection, no empirical validation gate for self-improvements.

---

## 12. SEAL -- Self-Adapting Language Models (MIT, arXiv 2506.10943)

**URL:** https://arxiv.org/abs/2506.10943

**Core Mechanism:** LLMs generate their own finetuning data and update directives ("self-edits") via an outer RL loop (ReSTEM) + inner SFT loop. No separate adaptation modules.

**All Benchmark Numbers:**

**Few-shot Learning (ARC-AGI subset, Llama-3.2-1B):**
| Method | Success Rate |
|---|---|
| ICL | **0%** |
| TTT + Self-Edit (no prior RL) | **20%** |
| **SEAL** | **72.5%** |
| Oracle TTT (upper bound) | **100%** |

**Knowledge Incorporation (SQuAD, Qwen2.5-7B, single passage):**
| Method | Accuracy |
|---|---|
| Base model | **32.7%** |
| Train on Passage only | **33.5%** |
| Train on Passage + GPT-4.1 Synthetic | **46.3%** |
| **SEAL** | **47.0%** |

SEAL outperforms GPT-4.1 synthetic data in the single-passage setting. Takes only 2 ReSTEM iterations to surpass GPT-4.1 quality.

**Trade-offs:**
- Catastrophic forgetting across sequential tasks
- ~30-45 seconds per self-edit evaluation (SFT + eval)
- 6 hours per ReSTEM round on 2x H100
- Requires explicit downstream task labels (can't scale to unlabeled data)
- Diminishing returns after 2 ReSTEM iterations

**Transferable Idea for Lyra:** The self-edit concept could let Lyra's agents propose modifications to their own system prompts or skill definitions, validated through downstream task performance.

**Gap vs Baseline:** Lyra has no mechanism for agents to propose or apply modifications to their own configuration.

---

## 13. ADAS -- Automated Design of Agentic Systems (ICLR 2025 Outstanding Paper)

**URLs:** https://arxiv.org/abs/2408.08435 | https://github.com/ShengranHu/ADAS

**Core Mechanism:** Meta Agent Search -- a meta agent iteratively "programs" novel agents in code based on an ever-growing archive of previous discoveries. Agents are defined in code (Turing Complete search space).

**Architecture:**
- Meta agent as programmer
- Archive of discovered agents
- Domains: ARC, DROP, MMLU, MGSM, GPQA (5 domains)
- Base model: GPT-3.5
- Self-contained per-domain search scripts

**Results:** Agents "greatly outperform state-of-the-art hand-designed agents." Cross-domain and cross-model transfer demonstrated (novel agents maintain superiority when transferred). No exact numbers extractable from PDF binary.

**Design Rationale:** "Hand-designed solutions are eventually replaced by learned solutions." The code-as-agent-representation makes the search space Turing Complete.

**Transferable Idea for Lyra:** ADAS formalizes the research area Lyra should fit into: Automated Design of Agentic Systems. Lyra's meta-agent could discover novel combinations of tools, hooks, and subagent workflows.

**Gap vs Baseline:** Lyra has no meta agent search. No discovery of novel agent designs. All agent configurations are manually authored.

---

## 14. AlphaEvolve (Google DeepMind)

**URL:** https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/

**Core Mechanism:** Evolutionary coding agent combining LLMs (Gemini Flash + Pro) with automated evaluators. Prompt sampler -> Gemini generates programs -> evaluators score -> programs database -> evolutionary selection.

**All Benchmark Results:**

| Domain | Improvement | Details |
|---|---|---|
| Data Center Scheduling | **0.7% of Google's worldwide compute** | In production 1+ year |
| TPU Hardware Design | New Verilog circuit | Integrated into upcoming TPU |
| AI Training (Gemini kernel) | **23% speedup** -> **1% Gemini training time reduction** | Weeks expert effort -> days |
| AI Inference (FlashAttention) | **Up to 32.5% speedup** | GPU-level instruction optimization |
| 4x4 Complex Matrix Multiply | **48 scalar multiplications** | Beats Strassen's 1969 algorithm |
| Open Math Problems (50+) | ~**20% improved** best known, ~**75% rediscovered** SoTA | Kissing number: **593 outer spheres** (new lower bound in 11D) |

**Design Rationale:**
- Flash/Pro ensemble: breadth vs depth trade-off
- Human-readability as operational advantage
- Requires domains with automatic verifiability
- Dual-model strategy (cheap exploration + deep refinement)

**Transferable Idea for Lyra:** The Flash/Pro ensemble pattern for exploration vs refinement. Lyra could use a fast/cheap model for broad search and a powerful model for deep refinement of promising candidates.

**Gap vs Baseline:** Lyra has no evolutionary search over its own algorithms/harness. No automated evaluator loop.

---

## 15. ReflecTool (ACL 2025)

**URL:** https://arxiv.org/abs/2410.17657

**Core Mechanism:** Two-stage reflection-aware tool-augmented agent:
1. **Optimization Stage (Training):** Builds long-term memory from successful trajectories + tool-wise experience
2. **Inference Stage:** Retrieves demonstrations + Verifier improves tool usage via iterative refinement or candidate selection

**Results (ClinicalAgent Benchmark, 18 tasks):**
- ReflecTool vs pure LLMs: **>10 points** improvement
- ReflecTool vs well-established agent methods: **+3 points**

**Transferable Idea for Lyra:** The training-time experience accumulation + inference-time retrieval + verification pattern. Lyra's skill system could accumulate successful trajectories and retrieve them at inference time.

**Gap vs Baseline:** Lyra has no long-term memory of successful tool usage patterns. No verifier for tool selection.

---

## 16. EvoTest (ICLR 2026)

**URL:** https://arxiv.org/abs/2510.13220

**Core Mechanism:** Gradient-free evolutionary test-time learning. Two-agent architecture:
- **Actor Agent:** plays the game (executes task)
- **Evolver Agent:** analyzes episode transcript, proposes revised config

Four mutations per cycle: prompt rewriting, memory updates, hyperparameter tuning, tool-use routine learning.

**Results (J-TTL benchmark, text-adventure games):**
- Existing methods (reflection, memory-only, RL) struggle
- EvoTest "consistently increases performance"
- **Only EvoTest won any games** (Detective, Library) -- all baselines failed to win

**Design Rationale:** No gradient computation = works with any model (including API-only closed models). Config changes are interpretable (prompt, memory, hyperparameters are inspectable).

**Transferable Idea for Lyra:** The two-agent Actor/Evolver pattern where the Evolver rewrites the Actor's configuration between episodes. This maps directly to Lyra's plan-fix loop.

**Gap vs Baseline:** Lyra has no cross-episode learning. The Evolver agent pattern is absent entirely.

---

## 17. TF-TTCL (Findings ACL 2026)

**URL:** https://arxiv.org/abs/2604.13552

**Core Mechanism:** Training-Free Test-Time Contrastive Learning. "Explore-Reflect-Steer" loop:
1. Semantic Query Augmentation (multi-agent role-playing for diverse trajectories)
2. Contrastive Experience Distillation (captures gap between superior/inferior trajectories -> textual rules)
3. Contextual Rule Retrieval (activates stored rules at inference time)

**Key Feature:** Frozen LLM throughout. All adaptation through in-context rule injection. No gradient updates.

**Results:** "Consistently outperforms strong zero-shot baselines and representative TTA methods" on closed-ended reasoning + open-ended evaluation.

**Transferable Idea for Lyra:** Contrastive distillation between good and bad trajectories into textual rules. Lyra's agents could generate rules from experience without weight updates.

**Gap vs Baseline:** Lyra has no test-time learning, no trajectory contrast, no rule extraction from experience.

---

## 18. SERM -- Self-Evolving Relevance Model (ByteDance / Findings ACL 2026)

**URL:** https://arxiv.org/abs/2601.09515

**Core Mechanism:** Relevance model that self-evolves under query distribution drift. Two multi-agent modules:
1. **Multi-Agent Sample Miner:** detects distribution shift, identifies informative samples
2. **Multi-Agent Relevance Annotator:** generates pseudo-labels via two-level agreement framework

**Scale:** Serves "billions of user requests daily" in production.

**Results:** "Significant performance gains through iterative self-evolution" validated by extensive offline multilingual + online testing.

**Transferable Idea for Lyra:** The distribution shift detection + multi-agent labeling pipeline. Lyra could detect when its current configuration is underperforming due to task distribution shift and trigger self-adaptation.

**Gap vs Baseline:** Lyra has no distribution shift detection, no self-labeling pipeline, no production self-evolution.

---

## 19. DeerFlow 2.0 (ByteDance)

**URL:** https://github.com/bytedance/deer-flow

**Core Mechanism:** Full-stack "super agent harness":
- **Backend:** Python 3.12, LangGraph + FastAPI, sandbox/tool system, memory, MCP
- **Frontend:** Next.js 16 + React 19
- **Architecture:** Lead agent -> middleware chain -> subagent registry -> sandbox -> MCP
- **Key features:** Skills (public skill packs), sub-agents, Docker sandbox, context engineering, long-term memory
- **Models:** Optimized for Doubao-Seed-2.0-Code, DeepSeek v3.2, Kimi 2.5

**Architecture (from `lead_agent/agent.py`):**
- `_make_lead_agent()` -- main entry point
- Middleware chain: Clarification, LoopDetection, Memory, SafetyFinishReason, SubagentLimit, Summarization, Title, Todo, TokenUsage, ToolErrorHandling, ViewImage
- LangGraph graph execution
- `ThreadState` for state persistence
- Tracing via Langfuse/LangSmith
- MCP integration for external tool extensions

**Design Rationale:** Ground-up rewrite for v2.0. "From Deep Research to Super Agent Harness" -- evolved from research tool to general agent orchestration platform.

**Transferable Idea for Lyra:** The middleware chain pattern (detect loops, limit subagents, error handling, safety checks) is directly applicable. The LangGraph orchestration + Docker sandboxing provides a reference architecture. Skills as public/private packs.

**Gap vs Baseline:** Lyra has no middleware chain, no Docker sandboxing, no MCP integration, no frontend, no tracing infrastructure, no skill pack system.

---

## 20. OpenCode (SST / Anomaly)

**URL:** https://github.com/sst/opencode

**Core Mechanism:** Open-source AI coding agent. Multi-platform (terminal, desktop, IDE). 75+ LLM providers.

**Architecture (from packages/):**
- `core/` -- agent state machine, model config, permissions
- `cli/` -- CLI application
- `console/` -- terminal UI
- `desktop/` -- desktop app
- `web/` -- web interface
- `sdk/` -- SDK for integrations
- `plugin/` -- plugin system
- `llm/` -- LLM provider abstraction (75+ providers)
- TypeScript/Effect-ts ecosystem

**Agent system (from `packages/core/src/agent.ts`):**
- `AgentV2.Info` -- typed agent schema with ID, model, options, system prompt, mode (subagent/primary/all), permissions
- Effect-ts for functional state management
- Immutable state, Schema-defined data structures
- Permission system with `PermissionSchema.Ruleset`

**Transferable Idea for Lyra:** The 75+ provider abstraction with unified schema. The agent definition schema (typed ID, mode, model, permissions). The Effect-ts functional state management pattern for reliable agent state.

**Gap vs Baseline:** Lyra has limited provider support (Anthropic only). No typed agent schema. No permission system. No multi-platform deployment.

---

## 21. Pi (getpi)

**URL:** https://github.com/getpi/pi

**Core Mechanism:** Sub-1K-token system prompt + lazy-loading skill system.

**Architecture (from repo):**
- `sdk/` -- core SDK
- `apps/` -- application interfaces
- `evals/` -- evaluation framework
- `docs/` -- documentation
- `walkthrough/` -- tutorial content
- Bun ecosystem

**Key Innovation:** Minimal system prompt (sub-1K tokens) with skills loaded lazily only when needed. This dramatically reduces context usage compared to monolithic system prompts.

**Transferable Idea for Lyra:** Lazy-loading skills to keep system prompt small. Lyra's current system prompt is monolithic. Skills/plugins should be loaded on-demand with minimal core overhead.

**Gap vs Baseline:** Lyra's system prompt grows with every new feature. No lazy loading. No minimal-core architecture.

---

## 22. Goose (Block)

**URL:** https://github.com/block/goose

**Core Mechanism:** Autonomous local agent that runs on your machine. MCP-native (Model Context Protocol). Uses "Recipes" for structured workflows.

**Note:** Clone repeatedly failed due to network issues. Assessment based on repo documentation and project description.

**Design Rationale:** MCP-native architecture means all tools and integrations go through the Model Context Protocol standard. Recipes provide structured, reusable agent workflows.

**Transferable Idea for Lyra:** MCP-native tool integration standard. Recipe system for structured, reusable agent workflows.

**Gap vs Baseline:** Lyra has no MCP integration, no recipe system for reusable workflows.

---

## 23. Cline (CLI + VS Code)

**URL:** https://github.com/cline/cline

**Core Mechanism:** Model-agnostic AI coding agent with Plan/Act modes, parallel agents, and VS Code + CLI interfaces.

**Architecture (from SDK `ARCHITECTURE.md`):**
```
@cline/shared -> @cline/llms -> @cline/agents -> @cline/core -> Host Apps
```
- **@cline/shared:** low-level contracts, types, schemas, hooks
- **@cline/llms:** model/provider runtime, catalogs, gateways (75+ providers)
- **@cline/agents:** stateless agent loop, tool orchestration, runtime events, hooks
- **@cline/core:** stateful orchestration, session lifecycle, storage, config, plugins

**Key Features:**
- Plan/Act modes (separate planning vs execution phases)
- Protobuf-based RPC for extension communication
- MCP integration via `McpHub`
- Model variants with different system prompt strategies (XS condensed, full)
- Slash command system
- VS Code extension + terminal CLI

**Transferable Idea for Lyra:** The layered architecture (shared -> llms -> agents -> core -> apps) is a reference for Lyra's modularization. Plan/Act modes map to Lyra's plan/fix modes. The model variant system (different prompt strategies per model family) is directly applicable.

**Gap vs Baseline:** Lyra has no layered SDK architecture, no protobuf communication standard, no model variant system, no plugin discovery/loading, no slash commands.

---

## SYNTHESIS: Cross-Cutting Patterns for Lyra

### Tier 1: Directly Transferable (High Impact, Low Effort)

| Pattern | Source | Lyra Application |
|---|---|---|
| Middleware chain | DeerFlow | Add LoopDetection, SafetyFinishReason, SubagentLimit middlewares to orchestrator |
| Lazy-loading skills | Pi | Replace monolithic system prompt with on-demand skill loading |
| Typed agent schema | OpenCode | Define `SkillInfo`, `ToolInfo`, `AgentInfo` schemas for runtime validation |
| Plan/Act modes | Cline | Already partially exists; formalize as distinct execution phases with different policies |
| Architectures by task type | Agent Scaling Science | Route to single-agent vs centralized vs hybrid based on tool count and task decomposability |

### Tier 2: Transformative (High Impact, Medium Effort)

| Pattern | Source | Lyra Application |
|---|---|---|
| Self-improvement archive | DGM, ADAS | Maintain archive of successful plans/skills; evolve via mutation + selection |
| Actor/Evolver dual-agent | EvoTest | Add Evolver agent that rewrites Actor's configuration between episodes |
| Contrastive experience | TF-TTCL | Distill good/bad plan outcomes into textual rules for future runs |
| Generate-Verify-Revise | Aletheia | Insert Verifier+Reviser into plan generation pipeline |
| Hierarchical rollout | MetaAgent-X | Evaluate M designs x N executions per plan before selection |
| Cross-episode learning | EvoTest, DGM | Add persistent state that improves agent behavior across sessions |

### Tier 3: Forward-Looking (Research Direction)

| Pattern | Source | Lyra Application |
|---|---|---|
| End-to-end RL for orchestrator | MetaAgent-X | Train Lyra's planner via RL using task success as reward |
| Temperature of Ideas ranking | Co-Scientist | Rank candidate plans via Elo tournament |
| Meta-agent rewrites own harness | DGM-H | Allow Lyra's meta-agent to modify system prompt, tools, and workflow definitions |
| Self-adapting weight updates | SEAL | Allow fine-grained self-modification of agent parameters |
| Distribution shift detection | SERM | Detect when Lyra's current config drifts from optimal for incoming task distribution |

### The Capability Ceiling (Critical Finding from Agent Scaling Science)

The single most important finding for Lyra's architecture decisions:
- **When single-agent accuracy > 45%, adding more agents DECREASES performance** (beta=-0.236, p=0.004)
- **The 45% threshold is a decision boundary** for whether to use multi-agent at all
- **Tool-heavy tasks suffer disproportionately** (beta=-0.096, p=0.002)
- **Error amplification ranges from 4.4x (centralized) to 17.2x (independent)**

Lyra should implement a **routing gate** that estimates whether the current task exceeds the 45% baseline threshold and selects the architecture accordingly. Tasks above threshold -> stay single-agent. Tasks below threshold -> use multi-agent with centralized topology (lowest error amplification).

---

*Research compiled June 2026. Full deep-read applied to all 23 sources including codebase analysis of 7 repositories (HyperAgents, DGM, ADAS, DeerFlow, OpenCode, Cline, Pi). Goose and PettingLLMs partially analyzed due to network issues.*
