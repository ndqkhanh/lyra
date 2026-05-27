# LYRA Ultra Deep Research Report — May 2026
## Breakthrough AI Agent Papers, Repos & Techniques NOT Yet Covered

---

# PART 1: MEMORY ARCHITECTURES (5 Papers)

## 1.1 EvolveMem — Self-Evolving Memory via AutoResearch
**arXiv:2605.13941** | May 13, 2026

**What it is**: Treats the entire retrieval configuration (chunk size, top-k, recency bias, embedding model) as a structured action space. An LLM-powered diagnosis module observes retrieval failures and proposes new configurations. Memory co-evolves at two levels: stored knowledge AND retrieval mechanism.

**Results**: +25.7% on LoCoMo, +18.9% on MemBench.

**Why it matters for AGI**: Fixed retrieval configurations are a bottleneck. An agent that auto-tunes its own memory system is a step toward meta-cognitive self-improvement.

**Lyra adoption**: Replace Lyra's static RAG/retrieval with a self-tuning retrieval layer. Add a "memory diagnosis" sub-agent that monitors recall quality and adjusts parameters.

**Priority**: P1 | **Complexity**: High (requires retrieval performance monitoring + configuration action space)

---

## 1.2 DecentMem — Self-Evolving Multi-Agent Systems via Decentralized Memory
**arXiv:2605.22721** | May 21, 2026

**What it is**: Each agent maintains its own dual-pool memory (exploitation + exploration). Proves O(log T) cumulative regret — matches the stochastic bandit lower bound. **49% token reduction** vs centralized memory, +23.8% accuracy.

**Why it matters for AGI**: Decentralized memory avoids the single-point-of-failure bottleneck. Each agent independently explores while sharing only compressed insights. The theoretical guarantee (matching bandit lower bound) is rare in agent literature.

**Lyra adoption**: Replace Lyra's centralized memory store with per-subagent dual-pool memory. Each specialist agent has an exploitation pool (proven patterns) and exploration pool (novel approaches). Periodic cross-agent consolidation.

**Priority**: P1 | **Complexity**: High (requires fundamental memory architecture change)

---

## 1.3 Microsoft's Human-Inspired Memory Architecture
**arXiv:2605.08538** | May 8, 2026

**What it is**: Six cognitive mechanisms: sleep-phase consolidation, interference-based forgetting, engram maturation, reconsolidation, entity knowledge graphs, hybrid multi-cue retrieval. 97.2% retention precision with 58% store reduction on VSCode issues (13K issues, 120K events). First streaming M-tier evaluation of LongMemEval (475 sessions, ~540K turns).

**Why it matters for AGI**: Bio-inspired memory (sleep consolidation, forgetting, reconsolidation) directly addresses the catastrophic forgetting and context-window overflow problems.

**Lyra adoption**: Implement a "sleep consolidation" daemon that runs during idle periods — compresses episodic memories into semantic knowledge, prunes redundant entries, and consolidates entity graphs.

**Priority**: P1 | **Complexity**: Medium (daemon process + consolidation logic)

---

## 1.4 RecMem — Recurrence-based Memory Consolidation
**arXiv:2605.16045** | ACL 2026 Findings | May 15, 2026

**What it is**: Stores interactions in a "subconscious" memory layer. Only invokes the LLM when sustained recurrence of similar interactions is detected. Reduces token cost by up to 87% while exceeding SOTA accuracy.

**Why it matters for AGI**: The "subconscious" layer is the key insight — not all memories need LLM processing. Recurrence detection is lightweight and can be handled by embedding similarity alone.

**Lyra adoption**: Add a light-weight interaction cache that pattern-matches new queries against past interaction signatures without LLM involvement. Only invoke the full reasoning pipeline on novel queries.

**Priority**: P1 | **Complexity**: Medium

---

## 1.5 MemTier — Tiered Memory for Long-Running Autonomous Agents
**arXiv:2605.03675** | May 5, 2026

**What it is**: Tripartite architecture: episodic JSONL store, five-signal weighted retrieval engine, PPO-based policy for adapting retrieval weights. Async consolidation daemon. With a **7B model on a 6GB GPU**, improves from 5% to 38% on LongMemEval-S.

**Why it matters for AGI**: PPO-based retrieval weight adaptation means the agent learns which memory signals matter for which tasks — a primitive form of meta-learning.

**Lyra adoption**: Add PPO-based retrieval weight learning on top of Lyra's existing memory. Have the agent adaptively prioritize recency, relevance, frequency, source authority, and task-specific signals.

**Priority**: P2 | **Complexity**: High (requires RL training loop)

---

# PART 2: COGNITIVE ARCHITECTURES BEYOND REACT (6 Papers)

## 2.1 Huang & Zhou 2D Framework — Cognitive Function x Execution Topology
**arXiv:2605.13850** | May 2026

**What it is**: A 7x6 classification matrix: **Cognitive Function** (7: Context Engineering, Memory, Reasoning, Action, Reflection, Collaboration, Governance) x **Execution Topology** (6: Chain, Route, Parallel, Orchestrate, Loop, Hierarchy). Identifies 27 named patterns, 13 original.

**Why it matters for AGI**: Provides a framework-neutral vocabulary to describe any agent architecture. Disambiguates ReAct vs Plan-and-Execute vs Hierarchical Delegation at the pattern level.

**Lyra adoption**: Use this matrix to catalog all of Lyra's agent patterns and identify missing pattern coverage. Audit Lyra's current topology against the 27 patterns.

**Priority**: P2 | **Complexity**: Low (analytical, no code change)

---

## 2.2 Roynard's Knowledge Layer — Four-Layer Cognitive Decomposition
**arXiv:2604.11364** | April 2026

**What it is**: Argues existing frameworks (CoALA, JEPA) lack an explicit Knowledge layer with distinct persistence semantics. Proposes: **Knowledge** (indefinite supersession), **Memory** (Ebbinghaus decay), **Wisdom** (evidence-gated revision), **Intelligence** (ephemeral inference). First systematic argument that facts and experiences should NOT share update mechanics.

**Why it matters for AGI**: Most architectures conflate knowledge and memory. Roynard shows they need fundamentally different update policies — facts persist indefinitely, memories decay, wisdom requires evidence thresholds.

**Lyra adoption**: Refactor Lyra's knowledge base into four distinct stores with different persistence policies. Facts (verified truths) persist forever. Memories decay via Ebbinghaus curve. Wisdom (patterns, heuristics) requires evidence threshold for revision. Intelligence (inference cache) is ephemeral.

**Priority**: P1 | **Complexity**: Medium (refactoring storage layer)

---

## 2.3 H-ECA — Homeostatic-Enactive Cognitive Architecture
**TechRxiv** | January 2026

**What it is**: Closed-loop control system regulating LLM output via internal state vectors (Competence, Connection, Necessity). Three layers: Homeostatic Regulation Layer, Executive Strategy Module, Self-Referential Episodic Store. Demonstrates *Algorithmic Individuation* — agents diverge in behavior based on interaction history.

**Why it matters for AGI**: Addresses "identity drift" and long-horizon coherence. Agents maintain a stable internal state that guides behavior without explicit prompting.

**Lyra adoption**: Add internal state vectors to Lyra agents. Track competence (task success rate), connection (integration depth), necessity (urgency). Modulate agent behavior based on these states.

**Priority**: P2 | **Complexity**: High (requires state management infrastructure)

---

## 2.4 SCL R-CCAM — Structured Cognitive Loop with Governance Layer
**Published 2025/2026**

**What it is**: Five explicit phases: Retrieval, Cognition, Control, Action, Memory (R-CCAM). Includes a Soft Symbolic Control governance layer applying symbolic constraints to probabilistic inference. Zero policy violations, complete decision traceability.

**Why it matters for AGI**: Soft Symbolic Control provides the best of both worlds — neural flexibility with symbolic guarantees. Complete decision traceability is essential for safety-critical agent deployments.

**Lyra adoption**: Add a symbolic governance layer that enforces constraints on agent actions (budget limits, tool authorization, domain boundaries) before any action executes.

**Priority**: P1 | **Complexity**: Medium (add pre-action symbolic validation)

---

## 2.5 Tri-Spirit — Three-Layer Cognitive Architecture
**arXiv:2604.13757** | April 2026

**What it is**: Decomposes intelligence across heterogeneous compute: Super Layer (planning), Agent Layer (reasoning), Reflex Layer (execution). Includes *habit-compilation* — repeated reasoning paths become zero-inference execution policies. Reduces latency by 75.6% and LLM invocations by 30%.

**Why it matters for AGI**: Habit compilation is the key insight — agents that "learn habits" the way humans do, freeing cognitive resources for novel situations.

**Lyra adoption**: Implement habit compilation — after N successful executions of the same LUI task pattern, auto-generate a lightweight execution policy that bypasses LLM reasoning.

**Priority**: P2 | **Complexity**: High (requires pattern detection + policy compilation)

---

## 2.6 CraniMem — Cranial-Inspired Gated and Bounded Memory
**ICLR 2026 Workshop** | March 2026

**What it is**: Goal-conditioned gating, bounded episodic buffer, structured long-term knowledge graph. Scheduled consolidation loop replays high-utility traces while pruning low-utility items. Directly addresses the *distractor problem* (noise injection) that plagues naive RAG.

**Why it matters for AGI**: The distractor problem is a critical failure mode — irrelevant information pollutes the agent's context. Goal-conditioned gating ensures only task-relevant memories are retrieved.

**Lyra adoption**: Add goal-conditioned memory gating. When Lyra initiates a task, its goal vector gates which memories are candidates for retrieval. Low-utility items are pruned periodically.

**Priority**: P2 | **Complexity**: Medium

---

# PART 3: SELF-IMPROVING AGENTS (3 Major Breakthroughs)

## 3.1 Meta's Hyperagents (DGM-H) — RECURSIVE SELF-IMPROVEMENT
**arXiv:2603.19461** | ICLR 2026 | March 2026

**What it is**: Extends Schmidhuber's Gödel Machine. An agent that rewrites its own code to improve performance. **SWE-bench: 20% → 50%. Polyglot: 14.2% → 30.7%. Cross-domain transfer**: improvements in robotics reward design transfer to math grading (imp@50 = 0.630). The meta-level modification procedure itself is editable — the system can improve *how* it generates improvements. Emergent behaviors: performance tracking, persistent memory, compute-aware planning.

**Why it matters for AGI**: This is the most important paper of 2026 for AGI proximity. True recursive self-improvement — the agent improves itself, then improves how it improves itself. Cross-domain transfer shows the improvements generalize beyond narrow domains.

**Lyra adoption**: This is Lyra's north star. Implement a simplified version:
1. Maintain an "agent variants archive" — snapshots of Lyra's prompt/config with performance metrics
2. Meta-agent evaluates variants, proposes mutations
3. New variants are tested on held-out tasks
4. Best variants are promoted to production

**Priority**: P0 | **Complexity**: Very High (foundational architecture change)

---

## 3.2 NousResearch Hermes Agent — Open-Source Self-Improving Agent
**GitHub: NousResearch/hermes-agent** | 135K+ stars | v0.13.0 May 7, 2026

**What it is**: Open-source agent with a closed learning loop — writes SKILL.md files from complex task executions, refines them on reuse, builds user models across sessions. Core innovation: **GEPA Algorithm** (ICLR 2026 Oral) — Genetic-Pareto Prompt Evolution. 6% average improvement over GRPO using 1/35th the training data. Costs $2-10 per optimization run (no GPU needed).

**Results**: 6% improvement over GRPO, up to 20% in some tasks. Pareto frontier optimization selects best prompt variants.

**Why it matters for AGI**: GEPA is the most cost-effective self-improvement technique discovered in 2026. It works at the prompt/skill level, not the model level, making it accessible to any agent.

**Lyra adoption**: 
1. Implement GEPA for Lyra's prompt optimization — analyze execution traces, generate prompt mutations, test against held-out evals
2. Auto-generate SKILL.md files from complex task solutions (Lyra already has .omc/skills/ — adopt this pattern)
3. Add a "background review agent" that runs after each task to propose memory/skill updates

**Priority**: P0 | **Complexity**: Medium (GEPA is algorithmically simple, just needs infrastructure)

---

## 3.3 Anthropic Dreaming — Offline Self-Improvement for Agents
**Announced May 6, 2026** | Code with Claude 2026

**What it is**: Scheduled background process where Claude agents review past sessions, identify patterns, consolidate memory, discard outdated info. Scans up to 100 sessions (5.3M tokens). Outputs curated memory + playbooks. Never modifies original — generates new, inspectable output. **Harvey**: task completion rates increased ~6x.

**Why it matters for AGI**: Compounding improvement — agents deployed for months get progressively better without manual retraining. "Compounding assets" not "tools."

**Lyra adoption**: 
1. Implement a "Dreaming" daemon that runs during idle/off-peak periods
2. Scans Lyra's past session logs and .omc/ state files
3. Merges duplicate memories, removes stale entries, identifies cross-session patterns
4. Generates new .omc/project-memory.json and skill files
5. Human-in-the-loop approval before deployment

**Priority**: P0 | **Complexity**: Medium (daemon + consolidation logic)

---

# PART 4: AGENT COMMUNICATION PROTOCOLS

## 4.1 A2A v1.2 + MCP Convergence
**Google Cloud NEXT '26** | April 2026

**What it is**: A2A reached v1.2 production-stable, donated to Linux Foundation. Co-governed by OpenAI, Microsoft, AWS, Anthropic, Block. Signed Agent Cards for cryptographic identity verification. Agent Registry (DNS for agents). Agent Gateway (unified security proxy for A2A + MCP).

**Current status**: MCP = 6,400+ public servers, 97M+ monthly SDK downloads. A2A = 200+ compatible agents, 150+ organizations in production.

**Mental model**: MCP answers "what data can I access?" A2A answers "who can I work with?"

**Why it matters for AGI**: Multi-agent systems need standardized communication. The MCP + A2A stack is becoming the universal agent integration layer.

**Lyra adoption**: 
1. Expose Lyra's capabilities as MCP servers (tools, data sources)
2. Implement A2A Agent Cards for Lyra's sub-agents
3. Use MCP for tool integration (rather than ad-hoc tool definitions)
4. Use A2A for inter-agent delegation (specialist agents discover each other)

**Priority**: P1 | **Complexity**: Medium

---

## 4.2 ACP — Agent Communication Protocol
**arXiv:2602.15055** | February 2026

**What it is**: IBM/BeeAI's protocol for secure, federated, autonomous A2A orchestration. Adds decentralized identity verification, semantic intent mapping, zero-trust security to inter-agent communication.

**Why it matters for AGI**: Adds security and semantic precision missing from A2A's current spec.

**Lyra adoption**: Evaluate ACP's zero-trust communication patterns for Lyra's sub-agent communication. Add identity verification between specialist agents.

**Priority**: P3 | **Complexity**: Medium

---

# PART 5: VERIFICATION & FACTUALITY (6 Breakthroughs)

## 5.1 Parallax — Cognitive-Executive Separation
**arXiv:2604.12986** | April 2026

**What it is**: The reasoning system NEVER directly executes actions. Independent multi-tiered validator (Adversarial Validation with Graduated Determinism), information flow control with data sensitivity labels, reversible execution with rollback. Blocks 98.9-100% of attacks across 280 adversarial test cases with zero false positives. Open-source Go implementation (OpenParallax).

**Why it matters for AGI**: Architecturally enforced safety — not prompt-level. The separation of thinking from acting is the most principled safety approach in 2026.

**Lyra adoption**: 
1. Separate Lyra's Planner (thinks) from Executor (acts)
2. Add a Validator tier between them that enforces tool access policies, budget limits, sensitivity labels
3. Implement rollback capability for reversible actions
4. Add graduated determinism — low-stakes actions auto-approved, high-stakes require human approval

**Priority**: P0 | **Complexity**: Medium (architectural change but well-defined pattern)

---

## 5.2 NabaOS — Tool Receipts for Hallucination Detection
**arXiv:2603.10060** | March 2026

**What it is**: Replaces expensive ZK proofs (180s/query) with HMAC-signed tool execution receipts. Epistemology-inspired verification: classifies every LLM claim by epistemic source (direct tool output, inference, testimony, absence, opinion). 94.2% detection of fabricated tool references, 87.6% count misstatements. **<15ms overhead.**

**Why it matters for AGI**: Practical, low-overhead hallucination detection that integrates into the agent's runtime. Classifies claims epistemically, enabling context-sensitive verification.

**Lyra adoption**: 
1. Add HMAC-signed tool execution receipts to all tool calls
2. Implement claim classification (direct tool output vs inference vs opinion)
3. Cross-reference LLM claims against signed receipts before presenting to user
4. Add epistemic confidence scores to Lyra's output

**Priority**: P1 | **Complexity**: Medium

---

## 5.3 MARCH — Multi-Agent Reinforced Self-Check
**arXiv:2603.24579** | March 2026

**What it is**: Breaks confirmation bias in LLM-as-a-judge by enforcing deliberate information asymmetry between three agents (Solver -> Proposer -> Checker). Checker validates claims against evidence in isolation, deprived of Solver's original output. Trained end-to-end with MARL. An 8B model with MARCH matches large closed-source performance.

**Why it matters for AGI**: Information asymmetry prevents the "rubber stamp" problem where judges just agree with solvers.

**Lyra adoption**: Add a Checker agent that independently validates factual claims against source evidence WITHOUT seeing the Solver's reasoning. The Checker only sees the claim and the evidence.

**Priority**: P1 | **Complexity**: Medium

---

## 5.4 VeriGuard — Verified Code Generation for Agent Safety
**Google Research** | ACL 2026

**What it is**: Intercepts code-based actions, generates and verifies policies against predefined safety specs, then verifies each action individually before execution. Interactive verification loop between agent and formal verifier.

**Why it matters for AGI**: Formal verification of agent actions moves beyond probabilistic safety to mathematical guarantees.

**Lyra adoption**: Add pre-action verification for code-generation tasks. Lyra generates code -> VeriGuard-style verifier checks against safety spec -> only verified code executes.

**Priority**: P2 | **Complexity**: High (requires formal verification infrastructure)

---

## 5.5 Semantic Gateway with Zero-Trust for Autonomous Agents
**arXiv:2604.25555** | April 2026

**What it is**: Three-layer zero-trust model: pre-inference Semantic Firewall, deterministic Tool-Level RBAC, cryptographic Human-in-the-Loop approval. Adapted Enabledness-Preserving Abstractions (EPAs) and greybox semantic fuzzing from blockchain verification. 100% discovery of hidden unauthorized state transitions. 84.2% reduction in incidental code execution.

**Why it matters for AGI**: Zero-trust for agents — don't trust what the agent says it's doing, verify at every layer.

**Lyra adoption**: Implement three-layer security:
1. Pre-inference: semantic firewall checks user requests for injection
2. Tool-level: RBAC for every tool (which sub-agent can call which tool)
3. Post-tool: cryptographic audit trail

**Priority**: P1 | **Complexity**: Medium

---

## 5.6 Agent Detection and Response (ADR) — Gen Digital
**March 2026** | Open Source: Sage

**What it is**: Runtime security layer for agentic AI — intercepts agent actions at execution time, evaluates safety locally on-device. 200+ detection rules: supply chain attacks, credential exposure, dangerous commands. 1,000+ installs.

**Why it matters for AGI**: Runtime monitoring is essential for real-world deployment. "Agent firewalls" will become as standard as web application firewalls.

**Lyra adoption**: Integrate ADR/Sage as Lyra's runtime security monitor. Add detection rules for Lyra-specific failure modes.

**Priority**: P2 | **Complexity**: Low (Sage is open-source)

---

# PART 6: AGENT ECONOMICS (3 Key Findings)

## 6.1 Token Economics — Dual-View Study
**arXiv:2605.09104** | May 2026

**What it is**: First unified framework linking computer science and economics for agent token economics. Four levels: Micro (single agent budget), Meso (multi-agent friction), Macro (ecosystem congestion), Security (adversarial economics).

**Why it matters for AGI**: Token economics is a new discipline. Understanding the economic properties of agent systems is essential for sustainable AGI.

**Lyra adoption**: Implement token budget tracking at all four levels:
- Micro: per-task token budgets with enforcement
- Meso: minimize inter-sub-agent coordination tokens
- Macro: congestion pricing for shared resources
- Security: detect economic attacks on token consumption

**Priority**: P1 | **Complexity**: Low (tracking + enforcement layer)

---

## 6.2 Marginal Token Allocator Framework
**arXiv:2605.01214** | May 2026

**What it is**: Argues all layers of an AI system solve the same first-order condition: marginal benefit = marginal cost + latency cost + risk cost. Identifies recurring failure modes: over-routing, over-delegation, under-verification, cache misuse.

**Why it matters for AGI**: Economic framing clarifies resource allocation decisions. Every sub-component should justify its token cost.

**Lyra adoption**: Apply marginal analysis to every Lyra component:
- Is the benefit of sub-agent delegation worth the token cost?
- Is the verification step saving more than it costs?
- Are cache hits high enough to justify cache maintenance?

**Priority**: P2 | **Complexity**: Low (analytical framework)

---

## 6.3 Alibaba Cloud Cost Optimization Strategies
**Alibaba Developer Blog** | 2026

**What it is**: Empirical results from production agent deployment. Tiered model routing: 40-60% cost reduction. Semantic cache + RAG: 20-30%. Async parallel batching: significant throughput. Dynamic prompt distillation: prevents exponential cost growth. Real-world case study achieved 83% cost reduction.

**Why it matters for AGI**: Cost is the primary barrier to scaled agent deployment. These techniques are proven in production.

**Lyra adoption**: 
1. Implement tiered model routing: simple tasks -> Haiku, complex -> Opus
2. Add semantic caching for repeated queries
3. Batch parallel independent sub-agent calls
4. Distill successful multi-step workflows into compressed prompts

**Priority**: P1 | **Complexity**: Medium

---

# PART 7: AGENT BENCHMARKS (5 New Standards)

## 7.1 AutoResearchBench — Scientific Literature Discovery
**arXiv:2604.25256** | April 2026

**What it is**: Two task types: Deep Research (track down specific target paper via multi-step probing) and Wide Research (comprehensively collect papers matching conditions). Top models achieve only 9.39% accuracy — extraordinarily hard.

**Why it matters for AGI**: Directly measures the "deep research" capability Lyra aims to provide. Current frontier is ~9% — massive headroom.

**Lyra adoption**: Benchmark Lyra on AutoResearchBench to establish baseline. Target: beat 9.39%.

**Priority**: P0 | **Complexity**: Low (run benchmark)

---

## 7.2 CocoaBench — Unified Digital Agents
**arXiv:2604.11201** | April 2026

**What it is**: 153 human-authored tasks requiring flexible composition of vision, search, and coding. 9 domains. Infrastructure-agnostic. Best system (GPT-5.4 Codex) achieves only 45.1%. Open-source models: Kimi-k2.5 11.8%, Qwen3.5 9.8%.

**Why it matters for AGI**: Measures the unified agent capability — combining modalities that Lyra needs for deep research.

**Lyra adoption**: Benchmark Lyra on CocoaBench. Target: beat 11.8% (open-source baseline) toward 45.1% (frontier).

**Priority**: P1 | **Complexity**: Low (run benchmark)

---

## 7.3 AstaBench — Scientific Research Suite
**ICLR 2026** | Ai2

**What it is**: 2,400+ problems spanning full scientific discovery process. Published at ICLR 2026. Adopted by UK AISI, Elicit, SciSpace. Best score: Claude Opus 4.7 at 58.0%.

**Why it matters for AGI**: Measures the scientific agent capability — literature review, code execution, data analysis, end-to-end discovery.

**Lyra adoption**: Benchmark Lyra on AstaBench. Identify weak areas in the scientific discovery pipeline.

**Priority**: P1 | **Complexity**: Low (run benchmark)

---

## 7.4 Open Agent Leaderboard
**HuggingFace** | IBM Research | May 2026

**What it is**: Measures general-purpose agent systems across 6 benchmarks simultaneously (SWE-Bench Verified, BrowseComp+, AppWorld, tau-bench). Reports quality AND cost per task. Built with open-source Exgentic framework.

**Why it matters for AGI**: First benchmark to explicitly measure cost efficiency alongside capability. The agent scaffold matters as much as the model.

**Lyra adoption**: Submit Lyra to the Open Agent Leaderboard for independent quality/cost assessment.

**Priority**: P2 | **Complexity**: Low

---

## 7.5 DR-Arena — Deep Research Agent Evaluation
**Semantic Scholar** | 2026

**What it is**: Automated evaluation framework specifically for deep research agents. Correlates with LMSYS Search Arena. 100 PhD-level research tasks across 22 fields. DeepResearch-9K: open-source training framework for multi-turn web interaction + RL.

**Why it matters for AGI**: Purpose-built for the exact capability Lyra aims to provide — deep multi-turn research.

**Lyra adoption**: Use DR-Arena as Lyra's primary evaluation framework for deep research capability. Train on DeepResearch-9K.

**Priority**: P1 | **Complexity**: Low to Medium

---

# PART 8: FEDERATED AGENTS (3 Papers)

## 8.1 Fed-SE — Federated Self-Evolution
**arXiv:2512.08870** | December 2025 / January 2026

**What it is**: LLM agents evolve locally via parameter-efficient fine-tuning on high-return trajectories, then globally aggregate updates in a low-rank subspace. 10% improvement in task success rates over FedIT across heterogeneous environments.

**Why it matters for AGI**: Privacy-preserving collective improvement — multiple instances of Lyra improve independently, then aggregate learnings without sharing raw data.

**Lyra adoption**: Implement federated skill improvement — multiple Lyra instances (different users) improve their prompt/skill configurations locally, share only anonymized improvement vectors.

**Priority**: P3 | **Complexity**: High

---

## 8.2 Agentic Federated Learning (Agentic-FL)
**arXiv:2604.04895** | April 2026

**What it is**: LLM-based agents autonomously orchestrate federated learning. Server-side agents mitigate selection bias; client-side agents manage privacy budgets and adapt model complexity to hardware.

**Why it matters for AGI**: Autonomy in the training loop — agents manage their own learning process.

**Lyra adoption**: If Lyra is deployed across multiple users, use Agentic-FL to orchestrate collective improvement while preserving privacy.

**Priority**: P3 | **Complexity**: High

---

## 8.3 IETF Privacy-Preserving Federated Learning for Multi-Tenant Agents
**IETF Draft** | January 2026

**What it is**: Reference architecture combining federated averaging, differential privacy, and secure aggregation for cross-tenant agent knowledge transfer. Addresses GDPR, HIPAA, CCPA compliance.

**Why it matters for AGI**: Provides the compliance framework for federated agent learning — necessary for enterprise deployment.

**Lyra adoption**: Use as reference for Lyra's data privacy compliance strategy.

**Priority**: P3 | **Complexity**: Low (reference)

---

# PART 9: WORLDMODELS & CAUSAL REASONING (5 Papers)

## 9.1 ARYA — Physics-Constrained Composable World Model
**arXiv:2603.21340** | March 2026

**What it is**: World model with five principles — causal reasoning, determinism, composability. Hierarchy of specialized "nano-models" orchestrated by autonomous research agent. Unfireable Safety Kernel as immutable safety boundary. Zero neural network parameters, SOTA benchmarks vs GPT-5.2 and Opus 4.6.

**Why it matters for AGI**: The Unfireable Safety Kernel — architecturally enforced safety that cannot be overridden, even by the agent itself. Separate from all safety approaches that rely on prompt-level constraints.

**Lyra adoption**: Add an "unfireable safety kernel" — a minimal, formal-verified safety layer that intercepts destructive actions with mathematical guarantees.

**Priority**: P1 | **Complexity**: High

---

## 9.2 Causal-JEPA — Object-Level Latent Interventions
**arXiv:2602.11389** | ICLR 2026 | February 2026

**What it is**: Extends masked joint embedding prediction to object-centric representations. Object-level masking induces latent interventions with counterfactual-like effects. ~20% absolute improvement in counterfactual reasoning. Uses only 1% of latent input features vs patch-based world models.

**Why it matters for AGI**: Counterfactual reasoning — the ability to reason about "what if" scenarios. Essential for planning and causal understanding.

**Lyra adoption**: Add counterfactual reasoning capability — when evaluating research plans, have Lyra simulate counterfactual scenarios ("what if we took a different approach?").

**Priority**: P2 | **Complexity**: High

---

## 9.3 Prometheus — Automating Deep Causal Research
**arXiv:2605.12835** | May 2026

**What it is**: Builds "Topos World Models" — sheaf-like causal atlases from literature, data, simulations, code. Local causal predictive-state models indexed by context, with restriction maps and gluing diagnostics exposing agreement/drift/contradiction.

**Why it matters for AGI**: "Sheaf-like causal atlases" formalize how an agent can maintain multiple local causal models and detect when they contradict — essential for robust research agents.

**Lyra adoption**: Implement causal atlas maintenance — when Lyra explores different research topics, maintain separate causal models and detect contradictions across domains.

**Priority**: P2 | **Complexity**: High

---

## 9.4 Toward Causal Foundation World Models
**AAAI 2026** | Position Paper

**What it is**: Vision for causal foundation world models enabling agents to interpret past, reason about future, act reliably in dynamic environments. Spans causal representation learning, causal reasoning in LLMs, causality-driven exploration.

**Why it matters for AGI**: Frames causal reasoning as a foundational capability, not a bolt-on.

**Lyra adoption**: Use as vision document for Lyra's long-term causal reasoning roadmap.

**Priority**: P3 | **Complexity**: Low (reference)

---

# PART 10: AGENTIC SDLC (2 Key Developments)

## 10.1 Agentic AI in the SDLC — Formal Architecture
**arXiv:2604.26275** | April 2026

**What it is**: Academic formalization of Agentic SDLC. Proposes six-layer reference architecture for agentic software engineering. Documents performance leap: SWE-bench Verified from 1.96% (Oct 2023) to 78.4% (Apr 2026).

**Why it matters for AGI**: Formal architecture enables systematic reasoning about agentic systems.

**Lyra adoption**: Align Lyra's SDLC integration with the six-layer architecture.

**Priority**: P2 | **Complexity**: Low (reference architecture)

---

## 10.2 Agentic SDLC Maturity Model
**Brillio / CIO.com** | 2026

**What it is**: Three-phase model: AI-assisted -> AI-enhanced (agentic collaboration) -> Autonomous SDLC (self-optimizing). Market projected $845M (2026) to $9.49B (2034), 35.3% CAGR. Multi-agent workflows grew 327% in <4 months.

**Why it matters for AGI**: Quantifies the industry transition to agent-driven development.

**Lyra adoption**: Position Lyra as an Autonomous SDLC tool — goal-in, outcome-out.

**Priority**: P2 | **Complexity**: Low (positioning)

---

# PART 11: INFERENCE OPTIMIZATION FOR AGENTS (5 Techniques)

## 11.1 SuffixDecoding — Agent-Specific Speculative Decoding
**CMU** | February 2026

**What it is**: Exploits repetitive inference patterns in agentic frameworks (multi-agent pipelines, self-refinement loops) using suffix-tree caching. Up to 5.3x speedup on SWE-Bench. 2.8x faster than EAGLE-3. 1.9x faster than model-free Token Recycling.

**Why it matters for AGI**: Agent workloads are fundamentally repetitive. SuffixDecoding exploits this structure specifically.

**Lyra adoption**: Cache and reuse suffix patterns from Lyra's common operation sequences (research planning, evidence collection, report generation). Pre-compute common sequences.

**Priority**: P1 | **Complexity**: Medium

---

## 11.2 RelayCaching — KV Cache Relay in Multi-Agent Pipelines
**2026**

**What it is**: 78-88% KV cache reuse in multi-agent pipelines via cache relay between agents. 4.7x reduction in time-to-first-token.

**Why it matters for AGI**: In multi-agent systems, agents share context. RelayCaching avoids recomputing shared prefixes.

**Lyra adoption**: When Lyra's sub-agents process overlapping context (common in research), relay KV caches instead of recomputing.

**Priority**: P1 | **Complexity**: Medium (requires KV cache infrastructure)

---

## 11.3 PayPal Commerce Agent — EAGLE-3 Production Benchmark
**arXiv:2604.19767** | April 2026

**What it is**: PayPal's production benchmark of EAGLE-3 via vLLM for their commerce agent. 22-49% throughput improvement, 18-33% latency reduction. Single H100 matched NVIDIA NIM on two H100s — 50% GPU cost reduction.

**Why it matters for AGI**: Production-validated speculative decoding for real agent workloads.

**Lyra adoption**: Integrate vLLM with EAGLE-3 for Lyra's inference. Target: 30-50% throughput improvement.

**Priority**: P2 | **Complexity**: Medium (vLLM integration)

---

## 11.4 Aurora — Continuous Online Speculative Learning
**February 2026**

**What it is**: Reframes speculator training as asynchronous RL, enabling day-0 deployment with continuous adaptation. 1.5x day-0 speedup on frontier models. Additional 1.25x over static speculators under domain drift.

**Why it matters for AGI**: Static speculators degrade as the model or task distribution changes. Aurora adapts continuously.

**Lyra adoption**: Add continuous adaptation to Lyra's inference optimization — monitor domain drift and adjust speculators.

**Priority**: P2 | **Complexity**: High

---

## 11.5 FreeKV — Speculative Retrieval Within KV Cache
**2026**

**What it is**: Predicts future cache accesses and prefetches them. 15-20% additional throughput improvement.

**Why it matters for AGI**: Predicts *which* parts of context will be needed next and pre-loads them.

**Lyra adoption**: Add context prefetching — predict which research sources Lyra will need next and pre-load them into the KV cache.

**Priority**: P3 | **Complexity**: High

---

# PART 12: PLATFORM UPDATES (Anthropic & OpenAI)

## 12.1 Anthropic Code with Claude 2026 (May 6)
**Four Major Announcements:**

1. **Managed Agents** — Public beta Anthropic platform for deploying, monitoring, and managing Claude agents at scale
2. **Dreaming** — Research preview (see Section 3.3)
3. **Outcomes Loop** — Public beta. Separate grader evaluates agent output against rubric. Task success up to +10 points
4. **Multi-Agent Orchestration** — Public beta. Lead agent delegates to sub-agents, each with own model/prompt/tools

**Additional**: Claude Code "Routines" for async automation. CI Auto-Fix. Desktop App. Rate limits doubled. 80x annualized growth in Q1 2026.

---

## 12.2 OpenAI May 2026 Agent Push

1. **Codex Locked Use** (May 21) — Operates macOS apps even when Mac is locked. Integrates with Apple security framework
2. **Workspace Agents** (Late April) — Persistent cloud-based agents in ChatGPT for shared team tasks. Powered by Codex with memory, tool access, approval gates
3. **GPT-Realtime-2** (May 7) — Voice agent with GPT-5-class reasoning, 128K context, parallel tool calls
4. **GPT-5.5** — Better at multi-step work, planning, tool use, self-verification
5. **Codex Appshots + Goal Mode GA** (May 22) — Instant desktop context capture. Goal Mode for hours/days-long autonomous work

---

# PART 13: DEEP RESEARCH BENCHMARK COMPARISON (May 2026)

## Key Results

| Benchmark | Leader | Score | Runner-Up | Score |
|-----------|--------|-------|-----------|-------|
| DeepSearchQA | Google Deep Research Max | 93.3% | GPT-5.4 Thinking | 88.5% |
| Humanity's Last Exam | Google Deep Research Max | 54.6% | GPT-5.4 | 53.4% |
| BrowseComp | Google Deep Research Max | 85.9% | GPT-5.4 | 58.9% |
| DeepResearch Bench | GPT-5.5 (evaluator) | 71.82 | Gemini 3.1 Pro | 70.58 |
| DeepResearchEval Quality | Gemini 2.5 Pro | 8.51/10 | Claude Sonnet 4.5 | 7.53 |
| DeepResearchEval Accuracy | Manus | 82.30% | Gemini 2.5 Pro | 76.62% |
| AstaBench | Claude Opus 4.7 | 58.0% | GPT-5.5 | 52.9% |
| AutoResearchBench (hard) | Frontier (model) | 9.39% | — | — |
| CocoaBench | GPT-5.4 Codex | 45.1% | Kimi-k2.5 | 11.8% |

**Key Insight**: Quality and factual accuracy are nearly uncorrelated. A beautiful report may be full of errors.

**Effort Paradox**: Higher reasoning effort does not always improve accuracy. For most models, default low-effort settings are the sweet spot.

---

# PART 14: SECURITY — OWASP Top 10 for Agentic Applications (2026)

**New framework** specifically for autonomous agents, beyond the LLM Top 10:

| Rank | Risk | Key Implication for Lyra |
|------|------|-------------------------|
| ASI01 | Agent Goal Hijack | Add goal validation between each research step |
| ASI02 | Tool Misuse | RBAC for every tool call |
| ASI03 | Identity/Privilege Abuse | Sub-agents get least-privilege tool access |
| ASI04 | Agentic Supply Chain | Verify MCP servers and skill sources |
| ASI05 | Unexpected Code Execution | Sandbox all code execution |
| ASI06 | Memory/Context Poisoning | Validate data before writing to persistent memory |
| ASI07 | Insecure Inter-Agent Communication | Encrypt sub-agent messages |
| ASI08 | Cascading Failures | Add circuit breakers between sub-agents |
| ASI09 | Human-Agent Trust Exploitation | Show epistemic confidence scores |
| ASI10 | Rogue Agents | Monitor agent drift over time |

---

# PRIORITY SUMMARY FOR LYRA

## P0 — Immediate (Q3 2026)
1. **Hyperagents recursive self-improvement** — implement DGM-H pattern for Lyra's prompt/skill evolution (Section 3.1)
2. **Hermes Agent GEPA + Skill Generation** — auto-generate SKILL.md from complex tasks, Pareto-optimize prompts (Section 3.2)
3. **Anthropic Dreaming** — offline memory consolidation daemon (Section 3.3)
4. **Parallax** — Cognitive-Executive separation for safety (Section 5.1)
5. **AutoResearchBench** — establish Lyra baseline on deep research benchmark (Section 7.1)

## P1 — Q3-Q4 2026
6. **EvolveMem** — self-tuning retrieval configuration (Section 1.1)
7. **DecentMem** — decentralized dual-pool memory per sub-agent (Section 1.2)
8. **Microsoft Human-Inspired Memory** — sleep consolidation, forgetting, reconsolidation (Section 1.3)
9. **RecMem** — subconscious recurrence-based memory (Section 1.4)
10. **Roynard Knowledge Layer** — 4-tier knowledge/memory/wisdom/intelligence separation (Section 2.2)
11. **SCL R-CCAM** — symbolic governance layer (Section 2.4)
12. **A2A + MCP convergence** — expose Lyra as MCP server, add A2A Agent Cards (Section 4.1)
13. **NabaOS Tool Receipts** — HMAC-signed tool verification (Section 5.2)
14. **MARCH** — information-asymmetric verification (Section 5.3)
15. **Semantic Gateway Zero-Trust** — three-layer security (Section 5.5)
16. **Token Economics** — micro/meso/macro budget tracking (Section 6.1)
17. **Alibaba Cost Optimization** — tiered routing, semantic cache, batch execution (Section 6.3)
18. **ARYA Unfireable Safety Kernel** — architecturally enforced safety (Section 9.1)
19. **SuffixDecoding** — agent-specific inference optimization (Section 11.1)
20. **RelayCaching** — KV cache relay between sub-agents (Section 11.2)
21. **CocoaBench + AstaBench + DR-Arena** — benchmark Lyra across all three (Sections 7.2, 7.3, 7.5)

## P2 — Q1 2027
22. **MemTier PPO-based retrieval** (Section 1.5)
23. **Huang & Zhou 2D Framework** — pattern audit (Section 2.1)
24. **H-ECA homeostatic states** (Section 2.3)
25. **Tri-Spirit habit compilation** (Section 2.5)
26. **CraniMem goal-conditioned gating** (Section 2.6)
27. **VeriGuard — formal verification for code actions** (Section 5.4)
28. **ADR/Sage runtime security** (Section 5.6)
29. **Marginal Token Allocator analysis** (Section 6.2)
30. **Open Agent Leaderboard submission** (Section 7.4)
31. **Causal-JEPA counterfactual reasoning** (Section 9.2)
32. **Prometheus causal atlases** (Section 9.3)
33. **Agentic SDLC alignment** (Section 10.1-10.2)
34. **PayPal/EAGLE-3 production inference** (Section 11.3)
35. **Aurora continuous speculator adaptation** (Section 11.4)

## P3 — 2027+
36. **ACP for secure inter-agent communication** (Section 4.2)
37. **Fed-SE federated self-evolution** (Section 8.1)
38. **Agentic-FL federated learning** (Section 8.2)
39. **IETF privacy framework** (Section 8.3)
40. **Causal Foundation World Models** (Section 9.4)
41. **FreeKV context prefetching** (Section 11.5)

---

# ARCHITECTURAL VISION: LYRA AS A COMPOUNDING-INTELLIGENCE AGENT

Synthesizing all findings, Lyra's target architecture for AGI progression:

```
                    +-------------------------------------------+
                    |           UNFIREABLE SAFETY KERNEL         |
                    |     (ARYA-style, architecturally enforced) |
                    +-------------------------------------------+
                                      |
                    +-------------------------------------------+
                    |         SYMBOLIC GOVERNANCE LAYER          |
                    |  (R-CCAM soft constraints + tool RBAC)     |
                    +-------------------------------------------+
                                      |
  User Input --> +-------------------+ | +-------------------+ |
                 |   PLANNER         | | |   EXECUTOR        | |
                 |  (Thinks, reasons,| | |  (Acts, calls     | |
                 |   delegates)      | | |   tools, runs     | |
                 +-------------------+ | |   code)           | |
                        |              | +-------------------+ |
                        v              |         |             |
                 +-------------------+ |         v             |
                 |    VALIDATOR      |<+   +-------------------+
                 |  (Parallax-style,|      |  MEMORY STACK     |
                 |   info asymmetry)|      |  Knowledge (perma)|
                 +-------------------+      |  Memory (decay)  |
                        |                   |  Wisdom (gate)   |
                        v                   |  Intelligence    |
                 +-------------------+      |  (ephemeral)     |
                 |  SUB-AGENT POOL   |      +-------------------+
                 |  Per-agent dual-  |
                 |  pool memory      |      +-------------------+
                 |  (DecentMem)      |      |  SKILL REPOSITORY |
                 +-------------------+      |  GEPA-generated   |
                        |                   |  Pareto-optimized |
                        v                   +-------------------+
                 +-------------------+
                 |    DREAMING        |-----+ Consolidation
                 |    DAEMON          |     | Pattern discovery
                 +-------------------+     | Memory pruning
                                            +-------------------+
                 +-------------------+      |  INFERENCE STACK  |
                 |   OUTPUT          |      |  SuffixDecoding   |
                 |   (with epistemic |      |  RelayCaching     |
                 |    confidence)    |      |  EAGLE-3          |
                 +-------------------+      +-------------------+
```

This architecture implements:
- **Safety at every layer** (Unfireable Kernel + Governance + Validator + Zero-Trust)
- **Compounding intelligence** (Dreaming + Skill Generation + Memory Consolidation)
- **Economic sustainability** (Token Budgeting + Tiered Routing + Inference Optimization)
- **Recursive self-improvement** (Hyperagents-style meta-optimization)
- **Epistemic rigor** (Tool Receipts + Information Asymmetry + Confidence Scores)

---

# KEY TAKEWAYS

1. **May 2026 is a watershed month** for agent research — the density of breakthroughs in memory architectures (5+ papers), self-improvement (Hyperagents, Hermes, Dreaming), and verification (Parallax, NabaOS, MARCH) is unprecedented.

2. **Hyperagents (Meta) and Hermes Agent (NousResearch)** are the two paper/repo pairs Lyra should prioritize above all others. Hyperagents shows what's theoretically possible (recursive code rewriting, cross-domain transfer). Hermes shows what's practically achievable today (GEPA, $2-10/optimization-run, 135K stars).

3. **The "Sleep" paradigm is emerging** — Dreaming, Microsoft's sleep consolidation, CraniMem's replay loop all point to offline improvement as the next frontier.

4. **Safety is becoming architectural, not prompt-level** — Parallax, ARYA's Unfireable Kernel, and OWASP's Agent Top 10 all argue for architecturally enforced safety boundaries.

5. **Deep research agents are still in their infancy** — AutoResearchBench at ~9% and CocoaBench at ~45% show massive headroom. Lyra entering this space now has first-mover advantage.
