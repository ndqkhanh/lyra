# Designing AI Agents — Best Practices Playbook

## Practice 1: Budget-First Architecture
- **What:** Treat every architectural decision as a resource allocation decision. The model has a finite token window (its working memory and reasoning surface). Every decision — which file to load, whether to spawn a sub-agent, how deeply to reason — is a decision about how to spend that budget. Design the harness to budget, constrain, route, and verify the model's spending.
- **Why:** The core premise of the book: "The model spends; the harness budgets." This framing makes every pattern in the book a budgeting strategy rather than a technique the model executes. On TerminalBench 2.0, harness optimization alone moved the same model from below baseline to a top-five finish. Vercel found that removing 80% of tools produced fewer steps, fewer tokens, and faster responses.
- **Lyra route:** §4.1 (Harness Architecture), §4.3 (Context Window Management), §4.5 (Reasoning Engine)
- **Source:** Chapters 1, 2 (thesis statement and general agent architecture)

## Practice 2: Design the Specification, Not the Code
- **What:** Past a basic threshold of prompt competency (the "implementation plateau"), improving the agent's code yields diminishing returns. What determines output quality is the *specification* — the cognitive architecture, pattern composition, and constraints you design around the agent's decision space. The specification is no longer documentation of the code; the code is an execution of the specification. Adopt Spec-Driven Development (SDD): three structured documents (proposal, design, task list) serve as the "source code"; the agent is the "compiler."
- **Why:** Teams that adopted structured specifications before agent execution reported 3-5× reductions in rework cycles (GitHub Spec-Kit data). The best agent engineers spend 80% of time on specification and 20% on implementation — the exact inverse of traditional development. "The agent handles competent implementation. What it cannot do is decide which constraints will produce reliable behavior."
- **Lyra route:** §4.1 (Harness Architecture), §4.2 (Planner Module), §4.8 (Governance)
- **Source:** Chapter 1 (design inversion, SDD, implementation plateau)

## Practice 3: Never Compact or Discard Error Traces
- **What:** Error traces and failure information must be preserved at P1 priority (or higher), never compressed, never dropped. When an agent forgets that it tried approach A and it failed, it will try approach A again, burning cycles and compounding errors. This rule applies across perception (context triage), memory (hierarchical retention), and compaction.
- **Why:** Manus's production data proved this is critical for error recovery. The book states it as an absolute rule: "never triage away failure information." Failure journals cost fewer than 200 tokens per entry but prevent entire wasted PRA cycles costing thousands — a 10x token leverage return.
- **Lyra route:** §4.4 (Memory Module), §4.3 (Context Window Management)
- **Source:** Chapters 3 (Context Triage), 4 (Failure Journals), cross-referenced in Ch 2

## Practice 4: Use Complexity-Based Model Routing
- **What:** Place a lightweight classifier (<100 tokens) before the main reasoning pipeline. Classify each query into SIMPLE/MODERATE/COMPLEX tiers, then route to progressively more expensive models (Haiku → Sonnet → Sonnet+extended thinking). The router should err toward over-estimation (false-simple is catastrophic; false-complex merely wastes money).
- **Why:** At 100 reviews/day, always using full extended thinking (128K tokens) cost $570/day. Adding a $0.001 classifier call dropped the bill by 81% with no quality loss on complex PRs. RouteLLM (ICLR 2025) demonstrated 85% cost reduction. The Planner-Worker split (Opus plans, Haiku executes) yields 90% cost reduction. Token leverage ratio: 50 classification tokens saves 100K reasoning tokens (1:2,000).
- **Lyra route:** §4.5 (Reasoning Engine), §4.2 (Planner Module), §4.6 (Model Router)
- **Source:** Chapter 5 (Complexity-Based Routing pattern)

## Practice 5: Implement Perception Before Reasoning
- **What:** Perception — the process of selecting, prioritizing, and assembling information into the context window — is the highest-leverage investment in agent quality. A mediocre model with a well-curated 30K-token context outperforms the best model drowning in 180K tokens of noise. Design a perception pipeline with context triage (P0-P3 priority tiers), avoid iatrogenic context (information that "helps" but actually degrades), and aim the context window like a spotlight, not a bucket.
- **Why:** The book opens with a failure story where an agent hallucinated a SQL injection vulnerability in an irrelevant file while missing a real race condition. The root cause: the test file revealing the bug was buried in the "dead zone" (middle 30% of context, where attention is ~30% lower per Liu et al. 2024 U-shaped curve). "Intelligence without perception is not just useless; it is dangerous."
- **Lyra route:** §4.3 (Context Window Management), §4.4 (Memory Module)
- **Source:** Chapter 3 (Perception — all four patterns)

## Practice 6: Build a Tiered Memory Hierarchy with Explicit Eviction
- **What:** Implement three memory tiers: Tier 1 (working memory / context window, 150K budget), Tier 2 (session buffer), Tier 3 (persistent vector DB). Define explicit promotion and eviction policies with a scoring formula: importance (50%) + recency (30%) + access frequency (20%). Consolidate only important entries (>0.6 importance or from "reflection" source) at session end. Use timestamps on all entries and discount relevance for older entries to handle cache coherence.
- **Why:** A code review agent that stored full tool output across 40 sessions (2.3M tokens) suffered retrieval degradation worse than a fresh session. Strategic forgetting is a feature — aggressive eviction (keep only decisions, errors, conventions; discard raw tool output after 48 hours) dropped memory usage 85% and recovered reasoning quality. The "public-private knowledge principle": use point-light keywords for public knowledge (model already knows SOLID); write full specs only for private knowledge (your team's naming conventions).
- **Lyra route:** §4.4 (Memory Module), §4.3 (Context Window Management)
- **Source:** Chapter 4 (Hierarchical Retention pattern, Memory lifecycle)

## Practice 7: Isolate Sub-Agent Context (Delegate Context, Not Control)
- **What:** Sub-agents should get a fresh context window containing only their task prompt and basic environment. They must NOT inherit the parent's conversation history, CLAUDE.md, rules, or auto memory. The parent explicitly includes only the conventions the sub-agent needs. This ensures sub-agents operate with high signal-to-noise ratio (SNR).
- **Why:** In a bug-fix task measured in the book, the main conversation accumulated 180K tokens over 6 turns. With sub-agents handling search and testing, the main conversation stayed at 75K. The real win was information density: main context SNR stayed above 40% instead of degrading to 5%. The book's architecture principle: "delegate the context, not the control."
- **Lyra route:** §4.7 (Multi-Agent Collaboration), §4.3 (Context Window Management)
- **Source:** Chapters 2 (Agent + sub-agents architecture), 3 (Sub-agent context isolation), 4 (Memory transmission isolation)

## Practice 8: Structure Reasoning as an Escalation Ladder
- **What:** Reason through problems in escalating sophistication: (1) Chain-of-Thought — the simplest upgrade from direct response. (2) Complexity-Based Routing — decide whether to apply CoT at all. (3) Parallel Exploration — branch CoT into multiple paths when a single chain is insufficient. (4) Iterative Hypothesis Testing — add environmental interaction when pure reasoning cannot reach the answer. Move down only when the simpler pattern fails.
- **Why:** Not every problem deserves the same reasoning depth. Forcing step-by-step reasoning on simple lookups adds latency without improving accuracy. But skipping deep reasoning on complex problems causes silent failures. The book's escalation logic provides a decision cascade: simple queries get fast/cheap models, complex ones get the full thinking budget. SWE-bench evidence shows agents outperform via better iteration (hypothesize-test cycles), not deeper single-pass reasoning.
- **Lyra route:** §4.5 (Reasoning Engine), §4.2 (Planner Module)
- **Source:** Chapter 5 (all four reasoning patterns and their composition)

## Practice 9: Track and Measure Cognitive Quality
- **What:** Implement metrics for each cognitive function rather than relying on intuition. Perception: re-read ratio (target <5%), token spend per successful outcome, attention zone coverage. Memory: retrieval hit rate (>30%), repeated mistake rate, staleness scores, consolidation ratio (10-20%). Reasoning: reasoning step count per resolution, routing accuracy (false-simple rate), backtrack rate (15-35% healthy), confidence calibration. Use a ReasoningTrace dataclass to capture these per-query.
- **Why:** "Engineering an agent is mostly about making invisible things visible." Without these metrics, teams optimize based on anecdotes. The book provides specific measurement frameworks for each module. Token leverage (output quality / token cost) is the cross-cutting metric that ties all modules together. These metrics require no special infrastructure — just counts and ratios from existing tool call logs.
- **Lyra route:** §4.9 (Observability), §4.8 (Governance/Evaluation)
- **Source:** Chapters 3 (Perception metrics), 4 (Memory metrics), 5 (Reasoning metrics)

## Practice 10: Apply the Pattern Selection Card for Architecture Decisions
- **What:** Use a three-panel quick reference when designing agent architectures: Panel 1 (ASSESS) — rate each cognitive function's demand as None/Light/Heavy. Panel 2 (ROUTE) — if Collaboration is Heavy, choose multi-agent topologies; otherwise stay single-agent. Panel 3 (SELECT) — look up specific patterns from the 7×6 map using function-topology coordinates. As a tie-breaker (Panel 4), pick the pattern with higher token leverage when architecturally equivalent.
- **Why:** The book provides 27 named patterns — too many to hold in working memory. The pattern selection card condenses the framework into a 60-second workflow (ASSESS → ROUTE → SELECT) that gets teams from a blank page to a first sketch. It prevents the two common mistakes: topology-only thinking ("we're using orchestrator-workers" — but for what cognitive function?) and function-only thinking ("we need better reflection" — but with what topology?).
- **Lyra route:** §4.1 (Architecture Decisions), §4.2 (Planner), all sub-modules
- **Source:** Chapter 2 (Pattern Selection Card, two-dimensional map)

## Practice 11: Use the Single-Agent Sweet Spot Until You Hit a Wall
- **What:** Default to a single agent with rich tool access. Only add multi-agent coordination when you demonstrably hit one of four walls: (1) context overflow — task exceeds one context window, (2) expertise specialization — subtasks need different system prompts/tools/models, (3) parallelism — independent subtasks can run simultaneously, (4) adversarial verification — independent evaluation catches errors self-review misses. The burden of proof is on the multi-agent architecture.
- **Why:** Multi-agent systems carry concrete costs: coordination overhead (5 agents = 5 context-window loads), error amplification (DeepMind study: up to 17.2× error rate vs. single-agent in poorly orchestrated teams), and debugging opacity (super-linear scaling with agent count). "A multi-agent system should exist because a single agent demonstrably cannot solve the problem, because one of the four walls is real, not hypothetical."
- **Lyra route:** §4.7 (Multi-Agent Collaboration), §4.1 (Harness Architecture)
- **Source:** Chapter 2 (Single-agent vs. multi-agent decision framework, scaling spectrum)

## Practice 12: Implement Progressive Trust with Guardrails as Architecture
- **What:** Design governance as a cross-cutting constraint envelope that wraps every module — not as an after-launch feature. Implement four levels: Approval Gate (human confirms dangerous actions), Progressive Commitment (escalate autonomy as trust is earned), Blast Radius Control (sandboxing, minimal permissions, OS-level isolation), Observability Harness (audit trails for every action). Map to the read/write asymmetry: reads are safe/idempotent; writes require escalating scrutiny.
- **Why:** "When you deploy an agent that reads files, executes code, sends emails, or modifies databases, you enter into a contract with its users." By 2026, agents execute write actions autonomously. The EU AI Act mandates risk classification and human oversight. Singapore's Agentic AI Framework requires governance controls proportional to autonomy. Trust is a load-bearing wall in the architecture, not a feature to bolt on later.
- **Lyra route:** §4.8 (Governance, Safety), §4.1 (Harness Architecture)
- **Source:** Chapters 2 (Progressive trust spectrum), cross-cutting Governance theme

## Practice 13: Monitor Compound Error Across Iteration Cycles
- **What:** Calculate expected overall success rate as (per-step accuracy)^N where N is the number of PRA loop iterations. At 95% per-step accuracy, a 20-step task has only 36% overall success. Four mitigation strategies: (1) minimize loop iterations via better perception, (2) maximize per-step accuracy via better prompts/tools/memory, (3) add verification checkpoints (reflection) at intermediate steps, (4) fail fast — abort and re-plan on clearly wrong results. Treat this as the fundamental tension in agent architecture.
- **Why:** This is "why Anthropic's first principle is to use simple, composable patterns." More autonomy requires more steps, but more steps amplify errors. Moving from 95% to 99% per-step accuracy doubles success rate at 20 steps. Each unnecessary PRA iteration also wastes tokens — bad architecture compounds cost across thousands of daily invocations.
- **Lyra route:** §4.5 (Reasoning Engine), §4.3 (Context Window Management), §4.7 (Reflection/Self-Correction)
- **Source:** Chapter 2 (Compound error analysis, Chip Huyen's quantification)

## Practice 14: Use Spec-Driven Development (SDD) Over Vibe Coding
- **What:** Adopt structured specification documents before agent execution: a proposal (what and why), a design (how), and a task list (in what order). The specification is the "first creation" (mental); the running agent is the "second creation" (physical). Let the agent handle competent implementation; your job is to design the specification that constrains its decision space.
- **Why:** Vibe coding — giving agents loose natural-language instructions and hoping — skips the first creation. The SDD community's data: 3-5× reductions in rework cycles, with largest gains on tasks exceeding 10 files. The specification quality determines output quality past the implementation plateau. The SDD ecosystem has exploded: GitHub Spec-Kit (72.7K stars), Superpowers (42K stars), and a dozen other frameworks converge on this insight.
- **Lyra route:** §4.2 (Planner Module), §4.1 (Harness Architecture)
- **Source:** Chapter 1 (SDD, design inversion, "all things are created twice")

## Practice 15: Optimize for KV-Cache Economics
- **What:** Stable context prefixes enable 10× cheaper inference ($0.30 vs. $3.00 per MTok for Claude). Keep system prompts stable, use append-only context when possible, and set explicit cache breakpoints. Memory tier transitions that change the context prefix invalidate this cache. Treat KV-cache hit rate as a first-class production metric alongside latency and correctness.
- **Why:** Manus identified the KV-cache hit rate as the single most important production metric. At scale, the difference between cached and uncached inference is the difference between a cost-effective system and an expensive one. This is one instance of the broader principle: runtime-level decisions directly impact economics, and "good architecture is not just a quality decision; it is a financial one."
- **Lyra route:** §4.3 (Context Window Management), §4.1 (Harness Architecture)
- **Source:** Chapters 2 (Runtime VM, Manus case study), 4 (Memory tier economics)

---

## Quick-Reference Pattern-to-Lyra Mapping

| Book Pattern | Cognitive × Topology | Lyra Module |
|---|---|---|
| Context Triage | Perception × Route | §4.3 Context Management |
| Semantic Compaction | Perception × Chain | §4.3 Context Management |
| Progressive Discovery | Perception × Orchestrate | §4.3 Context Management |
| Hierarchical Retention | Memory × Route | §4.4 Memory |
| RAG Pipeline | Memory × Chain | §4.4 Memory |
| Failure Journals | Memory × Loop | §4.4 Memory |
| Progress Tracking | Memory × Orchestrate | §4.4 Memory |
| Chain-of-Thought | Reasoning × Chain | §4.5 Reasoning |
| Complexity-Based Routing | Reasoning × Route | §4.5 Reasoning / §4.6 Router |
| Parallel Exploration | Reasoning × Parallel | §4.5 Reasoning |
| Iterative Hypothesis Testing | Reasoning × Loop | §4.5 Reasoning |
| Plan-and-Execute | Action × Orchestrate | §4.2 Planner |
| Guardrail Sandwich | Action × Hierarchy | §4.8 Governance |
| Generator-Critic | Reflection × Loop | §4.7 Reflection |
| Handoff Chain | Collaboration × Chain | §4.7 Multi-Agent |
| Fan-Out/Gather | Collaboration × Parallel | §4.7 Multi-Agent |
| Adversarial Review | Collaboration × Loop | §4.7 Multi-Agent |
| Hierarchical Delegation | Collaboration × Hierarchy | §4.7 Multi-Agent |
| Approval Gate | Governance × Route | §4.8 Governance |
| Blast Radius Control | Governance × Hierarchy | §4.8 Governance |
| Observability Harness | Governance × Orchestrate | §4.9 Observability |
