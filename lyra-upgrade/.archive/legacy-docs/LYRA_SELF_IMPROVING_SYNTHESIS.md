# Lyra Self-Improving Agent: Research Synthesis

**Date:** 2026-05-14  
**Goal:** Transform Lyra into a personal super-intelligent AI agent that can rewrite its own code to grow and evolve over time

---

## Executive Summary

This synthesis combines insights from 5 advanced agent architecture documents with cutting-edge 2026 research on self-improving AI agents. The goal is to design a comprehensive architecture for Lyra that enables autonomous evolution through code self-modification, skill library expansion, and closed-loop learning.

**Key Finding:** The 2025-2026 frontier converges on three pillars:
1. **Self-modifying code** with empirical validation (Darwin Gödel Machine, HyperAgents, SICA)
2. **Skill libraries** with automatic expansion (Voyager, SkillFoundry, AgentSkillOS)
3. **Closed-loop control** with reflection and meta-learning (Reflexion, Agent Q, AWS evaluator loops)

---

## Part 1: Foundation Documents Analysis

### 1. Multi-Hop Reasoning Agents (Doc 324)

**Core Insight:** RL-trained agentic search + graph-structured memory + multi-agent orchestration

**Key Techniques:**
- **Search-R1 / R1-Searcher / DeepDive:** Multi-hop reasoning with RL-trained search policies
- **GraphRAG / LightRAG / HippoRAG:** Graph-structured retrieval and memory systems
- **Hop-level provenance:** Track reasoning chains with faithfulness verification
- **MultiHopAgentTraceBench:** Evaluate trajectories, not just final answers

**Application to Lyra:**
- Implement graph-based memory for research findings and code patterns
- Add RL-trained search for multi-hop reasoning during research tasks
- Track provenance of all reasoning steps for self-reflection

### 2. Agent Model Routing (Doc 323)

**Core Insight:** Dynamic model switching based on task state, step type, evidence state, risk state, and budget

**Key Patterns:**
- **Fast/Reasoning/Advisor Strategy:** Fast executor asks stronger model for guidance when needed
- **FrugalGPT Cascades:** Route through model tiers based on confidence
- **RouteLLM:** Preference-based routing with learned policies
- **AutoMix:** Draft-verify-escalate pattern

**Task Slots:**
- Intent classification, local search, evidence extraction, planning, tool execution, synthesis, verification, final review

**Application to Lyra:**
- Implement adaptive model routing: Haiku for simple tasks, Sonnet for standard work, Opus for architecture/deep reasoning
- Add confidence-based escalation: if Haiku uncertain, escalate to Sonnet
- Track cost and performance metrics for routing optimization

### 3. Agent Split-View Monitoring (Doc 322)

**Core Insight:** Multi-panel interfaces for monitoring AI-agent sessions with real-time observability

**Key Components:**
- **Operator UX:** Split-view TUI with process list, resource graphs, trace viewer, log tail
- **Semantic Execution Record:** Structured trace with tool calls, reasoning steps, state transitions
- **Telemetry Wire Format:** OpenTelemetry GenAI semantic conventions
- **Multimodal Agent Execution Record (MAER):** References to text/tool/visual/audio/video/local state

**Application to Lyra:**
- Build split-view monitoring dashboard for observing Lyra's self-improvement process
- Implement MAER for tracking all execution artifacts
- Add real-time telemetry for debugging self-modification attempts

### 4. Agent View for Fleet Management (Doc 325)

**Core Insight:** Supervise many AI-agent sessions from one screen with state machine and UX primitives

**Session State Machine:**
- Created → Working → NeedsInput/ReadyForReview/Completed/Failed/Stopped

**UX Primitives:**
- Dispatch, Peek, Reply, Attach, Detach, Pin/reorder, Filter, Stop/delete, Review/merge

**Application to Lyra:**
- Implement session management for parallel self-improvement experiments
- Track multiple evolution branches simultaneously
- Enable human oversight and intervention at key decision points

### 5. Closed-Loop Agent Control (Doc 326)

**Core Insight:** Observe → Compare → Decide → Intervene → Learn

**Key Systems:**
- **AWS Evaluator Loop:** Generate → Evaluate → Revise until criteria/approval/retry limit/escalation/timeout
- **Reflexion:** Verbal reinforcement learning with persistent memory
- **Voyager:** Skill library with environment feedback and automatic curriculum
- **Agent Q:** MCTS + self-critique + DPO for policy optimization
- **LangGraph:** Checkpoints and human-in-the-loop interrupts

**Application to Lyra:**
- Implement closed-loop control for all self-modification attempts
- Add evaluator that validates code changes before applying
- Build skill library that grows through successful task completions
- Implement reflection mechanism for learning from failures

---

## Part 2: Self-Improving Agent Research (2026)

### A. Self-Modifying Code Architectures

#### 1. Darwin Gödel Machine (DGM)
**Source:** [Open-Ended Evolution of Self-Improving Agents](https://arxiv.org/abs/2505.22954)

**Architecture:**
- Maintains archive of generated coding agents in growing tree structure
- Iteratively modifies own code AND ability to modify codebase
- Population-based search with parent selection biased toward high performers

**Results:**
- SWE-bench: 20.0% → 50.0%
- Polyglot: 14.2% → 30.7%
- Autonomously discovered: memory infrastructure, performance logging, prompt templates, bias detection

**Safety:**
- Sandboxing and human oversight
- Empirical validation using coding benchmarks (not mathematical proofs)

#### 2. HyperAgents (Meta, 2026)
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Architecture:**
- Two editable functions sharing codebase: `solve_task()` and `modify_self()`
- Foundation model stays frozen; all learning through discrete code edits
- Archive of hyperagent programs selected via probability distributions

**Key Finding:**
- Meta-level skills transfer across domains (paper review → robotics → Olympiad math)
- Transferable capabilities: memory management, exploration strategies, prompt templates, performance tracking

#### 3. SICA (Self-Improving Coding Agent)
**Source:** [When Your AI Can Rewrite Its Own Code](https://tianpan.co/blog/2026-04-10-self-modifying-agent-horizon)

**Architecture:**
- Agent modifies own source files directly
- Write access to own codebase with improvement instructions

**Results:**
- SWE-bench: 17% → 53%

#### 4. Godel Agent
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Architecture:**
- Runtime monkey-patching with safety verification
- Changes verified before applying

### B. Skill Library Systems

#### 1. Voyager
**Source:** [An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291)

**Three Key Components:**
1. Automatic curriculum that maximizes exploration
2. Ever-growing skill library of executable code
3. Iterative prompting mechanism with environment feedback

**Skills:**
- Temporally extended, interpretable, compositional
- Compounds agent abilities rapidly
- Alleviates catastrophic forgetting

#### 2. SkillFoundry
**Source:** [Building Self-Evolving Agent Skill Libraries from Heterogeneous Scientific Resources](https://arxiv.org/html/2604.03964v1)

**Architecture:**
- Tree-guided, closed-loop system
- Transforms heterogeneous resources into structured agent skills
- Domain knowledge tree as search prior and evolving refinement object

**Pipeline:**
1. Domain Tree Initialization
2. Tree-Guided Resource Mining
3. Skill Extraction & Packaging
4. Multi-Stage Validation (execution, system, synthetic-data testing)
5. Tree Refinement

**Self-Evolution:**
- Feedback-driven updates reshape search structure
- Novelty assessment prevents redundancy
- Adaptive prioritization for under-covered branches
- Hierarchical repair loops for failed skills

#### 3. AgentSkillOS
**Source:** [Organizing, Orchestrating, and Benchmarking Agent Skills at Ecosystem Scale](https://arxiv.org/html/2603.02176v1)

**Key Insight:**
- Skill quality control, offline refinement, skill evolution
- Semantic matching to utility-aware skill retrieval
- Tree-based retrieval approximates oracle selection

#### 4. SAGE (Skill Library + RL)
**Source:** [Reinforcement Learning for Self-Improving Agent with Skill Library](https://arxiv.org/html/2512.17102)

**Architecture:**
- Four-agent system with curriculum drift prevention
- Accumulates reusable code artifacts from past tasks
- RL-driven skill selection and composition

### C. Reflection and Meta-Learning

#### 1. Reflexion
**Source:** [Reflexion: Language Agents with Verbal Reinforcement Learning](https://github.com/noahshinn/reflexion)

**Mechanism:**
- Maintains verbal self-reflection in persistent memory
- Learns from failures without parameter updates
- Multi-agent variant: multiple agents reflect on shared failures from different perspectives

**Results:**
- GPT-3.5: 48% → significantly higher accuracy

#### 2. ExpeL
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Mechanism:**
- Autonomously gathers experiences through trial-and-error
- No parameter updates required
- Experience-based learning

#### 3. Agent Q
**Source:** [Closed-Loop Agent Control (Doc 326)](file:///Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/326-closed-loop-agent-control-2026-deep-synthesis.md)

**Mechanism:**
- Monte Carlo Tree Search (MCTS)
- Self-critique
- Direct Preference Optimization (DPO)

### D. Memory Systems

#### 1. Mem0
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Status:**
- Commercial leader with $24M Series A
- 186 million API calls quarterly
- Exclusive AWS Agent SDK provider

#### 2. MemOS
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Architecture:**
- Treats memory as manageable system resource
- "MemCubes" with provenance tracking

#### 3. SimpleMem
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Results:**
- Semantic structured compression
- +26.4% F1 improvement
- 30x token reduction

### E. Safe Self-Modification Patterns

#### 1. SEVerA (Verified Synthesis of Self-Evolving Agents)
**Source:** [Verified Synthesis of Self-Evolving Agents](https://arxiv.org/html/2603.25111)

**Three-Stage Framework:**
1. **Search:** Planner LLM generates candidate parametric programs
2. **Verify:** Check FGGM definitions for correctness, verify against behavioral specs using Dafny
3. **Learn:** Gradient-based optimization while preserving formal correctness

**Formally Guarded Generative Models (FGGM):**
- Bind each generative model call to local input-output contracts (first-order logic)
- Automatic rejection sampler with verified fallback
- Parameter-independent correctness guarantees

**Results:**
- **Zero constraint violations** across all tasks
- HumanEvalDafny: 97.0% verification vs 86.9% baseline

#### 2. Continuity and Governance
**Source:** [Continuity and Governance in Persistent Self-Modifying Agents](https://arxiv.org/html/2604.14717v1)

**Key Insight:**
- Behavior shaped by mutable internal conditions
- Governance frameworks for persistent agents
- Continuity across self-modifications

#### 3. Safety Constraints (Industry Standard)
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Current Practices:**
- Frozen foundation model weights (only code/prompts modify)
- Sandboxed execution with resource limits
- Fixed human-set evaluation criteria
- Explicit oversight requirements

**Emerging Standards:**
- NIST formal standards initiative
- GUARDRAILS.md protocol with persistent "Signs"
- Linux Foundation's Agentic AI Foundation (MCP and A2A protocols)
- Variance Inequality framework: strong verifiers with weaker generators

### F. Evolutionary and RL Approaches

#### 1. AlphaEvolve (Google DeepMind)
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Results:**
- Recovered 0.7% of Google's worldwide compute through optimization
- Discovered matrix multiplication algorithms surpassing Strassen's 1969 breakthrough

#### 2. SWE-RL
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Mechanism:**
- Agents alternate between bug injection and solving roles
- +10.4 points on SWE-bench

#### 3. Multi-Agent Evolve
**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

**Architecture:**
- Three co-evolving agents: Proposer, Solver, Judge
- Optimized via RL

---

## Part 3: Cross-Cutting Themes

### Theme 1: Code as the Learning Substrate

**Consensus:** All major 2026 systems learn through code modification, not weight updates
- DGM: Modifies own codebase iteratively
- HyperAgents: Two editable functions (`solve_task`, `modify_self`)
- SICA: Direct source file modification
- Godel Agent: Runtime monkey-patching

**Why Code?**
- Interpretable and debuggable
- Compositional and modular
- Transferable across domains
- Preserves foundation model stability

### Theme 2: Empirical Validation Over Formal Proof

**Consensus:** Validate changes through benchmarks, not mathematical proofs
- DGM: "Impossible in practice" to prove benefit mathematically
- HyperAgents: Archive selection via performance distributions
- Exception: SEVerA uses formal verification for safety-critical constraints

**Validation Approaches:**
- Coding benchmarks (SWE-bench, HumanEval, Polyglot)
- Task-specific metrics
- Multi-stage testing (execution, system, synthetic-data)
- Human oversight at key decision points

### Theme 3: Skill Libraries as Memory

**Consensus:** Accumulate reusable code artifacts, not just episodic memory
- Voyager: Ever-growing skill library of executable code
- SkillFoundry: Structured skill cards with scope, dependencies, provenance
- SAGE: Reusable code artifacts from past tasks
- AgentSkillOS: Ecosystem-scale skill organization

**Benefits:**
- Alleviates catastrophic forgetting
- Enables compositional reasoning
- Accelerates learning through reuse
- Provides interpretable capability inventory

### Theme 4: Closed-Loop Control

**Consensus:** Observe → Compare → Decide → Intervene → Learn
- AWS: Generate → Evaluate → Revise loop
- Reflexion: Verbal reinforcement with persistent memory
- Agent Q: MCTS + self-critique + DPO
- SkillFoundry: Feedback-driven tree refinement

**Key Components:**
- Evaluator that validates outputs
- Reflection mechanism for learning from failures
- Curriculum that adapts based on performance
- Human-in-the-loop interrupts for oversight

### Theme 5: Multi-Agent Orchestration

**Consensus:** Specialized agents collaborate, don't monoliths
- Multi-Agent Evolve: Proposer, Solver, Judge
- SAGE: Four-agent system
- Multi-Agent Reflexion: Multiple perspectives on shared failures
- SkillFoundry: Separate agents for mining, extraction, validation

**Benefits:**
- Specialization improves performance
- Parallel exploration of solution space
- Diverse perspectives reduce blind spots
- Modular architecture enables targeted improvements

### Theme 6: Safety Through Constraints

**Consensus:** Multiple layers of safety constraints
- Frozen foundation models (only code/prompts modify)
- Sandboxed execution environments
- Human oversight requirements
- Formal verification for critical paths (SEVerA)
- Empirical validation before deployment

**Emerging Standards:**
- NIST formal standards
- GUARDRAILS.md protocol
- Linux Foundation governance
- Variance Inequality framework

---

## Part 4: Market and Benchmark Context

### Performance Trends

**SWE-bench Evolution:**
- Devin launch: 13.86%
- DGM: 20.0% → 50.0%
- SICA: 17% → 53%
- DeepSWE with scaling: 59%

**METR Time Horizon:**
- Task length agents complete autonomously doubled every 7 months (6 years)
- Accelerated to every 4 months in 2024-2025

**OSWorld:**
- Claude: <15% → 72.5% in 18 months

### Market Size

**Source:** [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)

- Global AI agent market: $7.84B (2025) → $52.62B (2030)
- Gartner: 40% of enterprise applications will feature task-specific agents by end of 2026
- IDC: AI agent use among Global 2000 increasing 10x by 2027; token volumes spiking 1,000x
- Only 95 of 1,837 surveyed organizations had agents live in production

### Production Deployments

**Meta's Ranking Engineer Agent (REA):**
- Doubled average model accuracy
- Three engineers improved eight models simultaneously

**Cognition's Devin:**
- $73M ARR
- 67% of PRs now merged
- Nubank: 8x efficiency gains

**Anthropic's Claude Agents:**
- 910 experiments in 8 hours
- 16 agents wrote C compiler in Rust

---

## Part 5: Synthesis for Lyra

### Core Architecture Principles

1. **Code-Based Learning:** Lyra learns by modifying its own source code, not through weight updates
2. **Skill Library:** Accumulate validated, reusable code artifacts from successful tasks
3. **Closed-Loop Control:** Every self-modification goes through evaluate → verify → apply loop
4. **Multi-Agent Orchestration:** Specialized sub-agents for different aspects of self-improvement
5. **Graph Memory:** Store research findings, code patterns, and reasoning chains in graph structure
6. **Adaptive Model Routing:** Dynamic switching between Haiku/Sonnet/Opus based on task complexity
7. **Split-View Monitoring:** Real-time observability of self-improvement process
8. **Formal Verification:** Safety-critical changes verified using FGGM pattern
9. **Human Oversight:** Key decision points require human approval
10. **Empirical Validation:** All changes validated through benchmarks before deployment

### Key Capabilities to Build

#### 1. Self-Modification Engine
- `solve_task()`: Execute research and coding tasks
- `modify_self()`: Propose and apply code improvements
- Sandboxed execution environment
- Version control integration
- Rollback mechanism for failed changes

#### 2. Skill Library System
- Structured skill cards (scope, dependencies, inputs, outputs, provenance, examples)
- Multi-stage validation (execution, system, synthetic-data testing)
- Novelty assessment to prevent redundancy
- Tree-based organization by domain
- Automatic skill composition

#### 3. Reflection and Meta-Learning
- Verbal self-reflection after each task
- Persistent memory of successes and failures
- Multi-perspective analysis (factual, engineering, security, consistency)
- Experience-based learning without parameter updates
- Curriculum adaptation based on performance

#### 4. Evaluator and Verifier
- Pre-modification validation
- Post-modification testing
- Formal verification for safety-critical changes
- Benchmark-based performance measurement
- Human-in-the-loop approval gates

#### 5. Graph Memory System
- Store research findings in graph structure
- Multi-hop reasoning with RL-trained search
- Provenance tracking for all reasoning steps
- Faithfulness verification
- Semantic compression for efficiency

#### 6. Model Router
- Task classification (simple/standard/complex)
- Confidence-based escalation
- Cost and performance tracking
- Adaptive routing policy
- Budget management

#### 7. Monitoring Dashboard
- Split-view TUI with process list, resource graphs, trace viewer, log tail
- Multimodal Agent Execution Record (MAER)
- Real-time telemetry
- Session state machine
- Fleet management for parallel experiments

#### 8. Safety Framework
- Sandboxed execution
- Resource limits
- Human oversight requirements
- Formal verification for critical paths
- Empirical validation gates
- Rollback and recovery mechanisms

---

## Sources

### Foundation Documents
- [Multi-Hop Reasoning Agents (Doc 324)](file:///Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/324-multi-hop-reasoning-agents-2026-deep-synthesis.md)
- [Agent Model Routing (Doc 323)](file:///Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/323-agent-model-routing-2026-deep-synthesis.md)
- [Agent Split-View Monitoring (Doc 322)](file:///Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/322-agent-split-view-monitoring-2026-deep-synthesis.md)
- [Agent View for Fleet Management (Doc 325)](file:///Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/325-agent-view-ai-agents-2026-deep-synthesis.md)
- [Closed-Loop Agent Control (Doc 326)](file:///Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/docs/326-closed-loop-agent-control-2026-deep-synthesis.md)

### Self-Improving Agents Research
- [Self-Improving AI Agents: The 2026 Guide](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)
- [Open-Ended Evolution of Self-Improving Agents (Darwin Gödel Machine)](https://arxiv.org/abs/2505.22954)
- [When Your AI Can Rewrite Its Own Code](https://tianpan.co/blog/2026-04-10-self-modifying-agent-horizon)
- [An Open-Ended Embodied Agent with Large Language Models (Voyager)](https://arxiv.org/abs/2305.16291)
- [Voyager Project Page](https://voyager.minedojo.org/)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://github.com/noahshinn/reflexion)
- [Building Self-Evolving Agent Skill Libraries (SkillFoundry)](https://arxiv.org/html/2604.03964v1)
- [Reinforcement Learning for Self-Improving Agent with Skill Library](https://arxiv.org/html/2512.17102)
- [Organizing, Orchestrating, and Benchmarking Agent Skills at Ecosystem Scale](https://arxiv.org/html/2603.02176v1)
- [Verified Synthesis of Self-Evolving Agents (SEVerA)](https://arxiv.org/html/2603.25111)
- [Continuity and Governance in Persistent Self-Modifying Agents](https://arxiv.org/html/2604.14717v1)
- [Just Talk – An Agent That Meta-Learns and Evolves in the Wild](https://arxiv.org/html/2603.17187v1)
- [Architecture, Acquisition, Security, and the Path Forward](https://arxiv.org/html/2602.12430)
- [Skill Retrieval Augmentation for Agentic AI](https://arxiv.org/html/2604.24594v1)
- [When AI agents learn to engineer themselves](https://alphasignalai.substack.com/p/when-ai-agents-learn-to-engineer)
- [Self-Improving AI: Hyperagents and Control](https://innobu.com/en/articles/self-improving-ai-agents-hyperagents-control.html)

---

**Next Step:** Create comprehensive phased implementation plan for transforming Lyra into a self-improving AI agent.
