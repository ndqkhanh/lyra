# Agentic AI for Engineers — Best Practices Playbook

**Source:** Dhivya Nagasubramanian, *Agentic AI for Engineers: Architecting Goal-Driven Systems* (Apress, 2026)

---

## Practice 1: Start with Architecture, Not the Model

- **What:** Large language models are powerful but on their own they are just very capable functions. What makes them agents is the architecture around them — reasoning loops, memory, planning, and tool interfaces working together in a deliberate design. Treat architecture as the real product, not an afterthought.
- **Why:** The difference between an impressive demo and a dependable system is the architecture — not model capability. Architecture determines reliability, safety, and maintainability.
- **Lyra route:** §5.1 (Architectural Design Patterns)
- **Source:** Chapter 5, Chapter 14

---

## Practice 2: Build the Perceive-Reason-Act-Reflect Loop as Your Agent's Operating System

- **What:** Every agentic system should be built around the four-phase loop: Perceive (parse input), Reason (LLM inference), Act (tool execution), Reflect (post-action evaluation). This loop is the heartbeat — it enables adaptive behavior that static workflows cannot achieve.
- **Why:** The loop turns ephemeral reasoning into a reproducible, auditable pipeline. Without reflection, agents have no mechanism to detect errors, adapt plans, or learn from outcomes.
- **Implementation:** Implement with structured state objects and event traces. The Reflect phase should explicitly ask: "Did this action succeed? Did it move us closer to the goal? What should we do differently?"
- **Lyra route:** §4.1 (Core Agent Loop)
- **Source:** Chapter 4

---

## Practice 3: Decompose Goals Hierarchically — One Agent, One Subgoal

- **What:** Break macro-goals into micro-goals dynamically. Assign each agent exactly one subgoal. Never build "super-agents" that try to handle everything — they become brittle and impossible to debug.
- **Why:** "The cleanest agentic systems behave like well-run project teams. Each person knows exactly what they're accountable for." Scoped agents are easier to test, debug, replace, and improve independently.
- **Lyra route:** §4.2 (Goal Decomposition), §12.1 (Multi-Agent Specialization)
- **Source:** Chapter 4, Chapter 12

---

## Practice 4: Make Tools Contract-First — Enforce Both Directions

- **What:** Define strict request/response schemas for every tool — data types, enumerations, valid ranges. Validate rigorously before sending AND after receiving. Schema mismatch = hard failure, not implicit correction. Write tool descriptions as API documentation: include "when to use," "when NOT to use," and argument guidance.
- **Why:** The quality of tool descriptions determines whether tools get used correctly. A description like "Gets customer data" is far less useful than "Retrieves customer profile including contact info, account status, and preferences. Use when you have a customer ID. For lookups by email, use search_customers instead."
- **Lyra route:** §4.4 (Tool Integration), §5.2 (Tool-Augmented Patterns)
- **Source:** Chapter 4, Chapter 5

---

## Practice 5: Put Guardrails Outside the Model — Infrastructure Layer

- **What:** Safety, alignment, and robustness belong in the infrastructure layer, not the model. Wrap every tool with scoped permissions (read vs. write), argument limits, allowlists. Sensitive operations require dry-run phase + human approval. Implement rate limiting, permission checks, action budgets, and audit logging from day one.
- **Why:** "Once you let an agent act on its own, mistakes don't just sit quietly in a log file — they spill out into the world." The model cannot be trusted to self-police; guardrails must be enforced at the system level.
- **Lyra route:** §8.1 (Safety Architecture), §8.2 (Guardrails)
- **Source:** Chapter 5, Chapter 8

---

## Practice 6: Implement Layered Monitoring — Diversity by Design

- **What:** Use monitoring agents to oversee primary agents, but prevent gaming through diversity: different models for monitor vs. primary, different prompting strategies (adversarial vs. helpful), isolated context (monitor sees sanitized output, not raw input). Use four patterns: Critic (output review), Parallel Panel (multi-concern), Supervisor (planning intervention), Audit Trail (post-hoc logging).
- **Why:** "If your monitor uses the same model, same prompts, same reasoning as the primary agent, you haven't added real oversight — just more of the same." When two independent systems agree, confidence rises. When they disagree, you've found something worth investigating.
- **Lyra route:** §8.3 (Monitoring Agents)
- **Source:** Chapter 8

---

## Practice 7: Build a 6-Layer Feedback Architecture

- **What:** Layer multiple feedback types from cheapest to most expensive:
  1. Self-critique (every interaction, ~1.3x cost) — catches obvious errors before users see them
  2. Implicit task feedback (continuous, automatic) — environment signals: test passes, API errors, latency, edit rates
  3. Peer agent review (sampled or low-confidence-triggered, ~2x cost) — cross-check against sources, policies
  4. Human rating (10-20% of interactions) — thumbs up/down, lightweight qualitative
  5. Human expert review (high-stakes only) — ground truth and training signal
  6. Red teaming (periodic) — adversarial stress testing

- **Why:** No single layer catches everything. Each layer catches what others miss. The architecture ensures feedback coverage scales with risk level.
- **Lyra route:** §11.1 (Feedback Loops), §11.2 (Self-Improvement)
- **Source:** Chapter 11

---

## Practice 8: Allocate Token Budgets Across Agents Explicitly

- **What:** Assign explicit token budgets per agent role based on task complexity. Reasoning/synthesis agents get larger budgets; retrieval/routing agents get smaller ones. Monitor actual usage to rebalance over time. Use model tiering: cheap models for classification/routing, expensive models only for complex reasoning.
- **Why:** Context windows are the hidden constraint on shared memory and multi-agent collaboration. A five-agent system with detailed outputs easily exceeds 50K tokens. Without explicit budgets, you get mysterious truncation, forgotten instructions, and runaway costs.
- **Lyra route:** §12.2 (Context Management), §12.3 (Routing)
- **Source:** Chapter 12

---

## Practice 9: Choose Multi-Agent Topology Based on Problem Shape

- **What:** Match topology to task structure:
  - Linear workflows → Sequential Pipeline (A → B → C)
  - Multiple perspectives needed → Parallel Fan-Out/Fan-In
  - Complex decomposition required → Hierarchical Manager-Worker
  - High-stakes decisions → Debate/Adversarial or Voting/Consensus
  - Evolving solutions → Blackboard (shared memory)
  - Variable agent capabilities → Market-Based (auction)
  - Mixed diverse workloads → Supervisor with Dynamic Routing

- **Why:** "The structure of teamwork must be designed, not assumed." Each topology optimizes for different trade-offs between speed, control, and reliability. Picking the wrong topology creates bottlenecks, error cascades, or coordination chaos.
- **Lyra route:** §12.1 (Multi-Agent Architectures), §12.3 (Routing)
- **Source:** Chapter 12

---

## Practice 10: Fail Gracefully with Structured Error Recovery

- **What:** Implement error handling as a decision tree: Retry → Fallback → Degrade → Ask User. Transient errors (timeouts, rate limits) get capped exponential backoff with jitter and idempotency keys. Non-transient errors trigger circuit breakers and fallback paths. Return structured errors with codes, severity levels, and recovery suggestions.
- **Why:** "The difference between a frustrating agent and a reliable one lies in how gracefully it handles inevitable failures." Real-world tasks rarely use just one tool — chains can fail at any junction. The goal is graceful failure, not perfect execution.
- **Lyra route:** §4.3 (Error Handling), §5.2 (Tool Reliability)
- **Source:** Chapter 4, Chapter 5

---

## Practice 11: Prevent Infinite Loops with Multiple Safeguards

- **What:** Layer three loop-prevention mechanisms: (1) Step counters with hard limits (20-30 for most tasks), (2) Repetition detection (same tool + same arguments 3x = stuck), (3) Progress tracking (are we getting closer to the goal?). When a loop is detected, backtrack to try a different approach, or escalate to the user with partial results.
- **Why:** Unproductive loops waste resources, frustrate users, and erode trust. Some iteration is natural — the goal is to detect unproductive loops quickly and recover gracefully, preserving whatever progress was made.
- **Lyra route:** §4.3 (Loop Control), §5.2 (Bounded Execution)
- **Source:** Chapter 4, Chapter 5

---

## Practice 12: Run the Pre-Deployment Safety Checklist

- **What:** Before any agent goes to production, verify:
  1. Guardrails defined for all high-risk actions
  2. Human approval required for irreversible actions
  3. Structured logging captures all reasoning steps
  4. Fail-safe behavior defined (timeout, handoff, freeze)
  5. Adversarial testing completed (PyRIT or equivalent)
  6. Bias audit run on representative test cases
  7. Least privilege enforced (minimal tool/data access)
  8. Monitoring dashboards configured
  9. Rollback procedure documented
  10. Red team exercise completed

- **Why:** Safety is a living system, not a launch checklist — but the checklist ensures you haven't missed critical protections. The cost of skipping any item compounds with autonomy.
- **Lyra route:** §8.2 (Safety Gates), §13.1 (Evaluation)
- **Source:** Chapter 8

---

## Practice 13: Test Behavior, Not Just Code

- **What:** Shift testing from "does the function return X?" to "does the agent act in ways we can trust across scenarios?" Use four testing modes: (1) Scenario-based tests simulating real-world tasks with edge cases, (2) Reasoning validation auditing Chain of Thought traces, (3) Prompt regression testing with golden examples to detect drift, (4) Adversarial testing with hostile inputs.
- **Why:** Agents produce different outputs for the same prompt depending on model updates, context, and sampling. Testing exact outputs is futile; testing behavioral bounds is essential.
- **Lyra route:** §13.1 (Testing), §13.2 (Evaluation)
- **Source:** Chapter 13

---

## Practice 14: Design for Progressive Autonomy

- **What:** Don't jump to full autonomy. Start with Tier 1 (manual oversight — all actions require human approval). Graduate to Tier 2 (conditional autonomy — auto-act for low-risk, request review for ambiguous/high-impact). Eventually reach Tier 3 (trusted autonomy — act independently with retrospective audit). The progression mirrors how we train new team members.
- **Why:** "Trust is earned, not assumed." Starting conservative and increasing autonomy as trust builds prevents catastrophic early failures and builds user confidence.
- **Lyra route:** §8.2 (Autonomy Calibration), §11.2 (Feedback-Driven Evolution)
- **Source:** Chapter 4, Chapter 11

---

## Practice 15: Instrument Everything — Observability Is Non-Negotiable

- **What:** Log every tool call, every decision point, every retry. Track latency, success rates, failure patterns across chains. Build dashboards for drift detection. Without structured, queryable logs, debugging multi-agent failures is nearly impossible.
- **Why:** "A system that works isn't necessarily a system you can trust. You need to see how the answer was reached, not just what the answer is." Structured logging turns the black box into a glass box — you can rewind, replay, and understand where logic went wrong.
- **Lyra route:** §13.2 (Observability), §8.3 (Monitoring)
- **Source:** Chapter 8, Chapter 13

---

## Summary Matrix

| # | Practice | Effort | Impact | Lyra § |
|---|----------|--------|--------|--------|
| 1 | Start with architecture, not model | Design | Critical | §5.1 |
| 2 | Perceive-Reason-Act-Reflect loop | High | Critical | §4.1 |
| 3 | Hierarchical goals, one agent one subgoal | Design | High | §4.2, §12.1 |
| 4 | Contract-first tools | Medium | High | §4.4, §5.2 |
| 5 | Guardrails in infrastructure layer | High | Critical | §8.1, §8.2 |
| 6 | Layered monitoring, diversity by design | Medium | High | §8.3 |
| 7 | 6-layer feedback architecture | High | High | §11.1, §11.2 |
| 8 | Explicit token budget allocation | Medium | Medium | §12.2, §12.3 |
| 9 | Topology matches problem shape | Design | High | §12.1, §12.3 |
| 10 | Structured error recovery tree | Medium | High | §4.3, §5.2 |
| 11 | Multiple loop-prevention safeguards | Low | High | §4.3, §5.2 |
| 12 | Pre-deployment safety checklist | Medium | Critical | §8.2, §13.1 |
| 13 | Behavioral testing, not output testing | Medium | High | §13.1, §13.2 |
| 14 | Progressive autonomy tiers | Design | Medium | §8.2, §11.2 |
| 15 | Instrument everything — observability | High | Critical | §13.2, §8.3 |
