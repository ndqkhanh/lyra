# Building Agentic AI Systems — Best Practices Playbook
**Source:** Anjanava Biswas, _Building Agentic AI Systems_, Packt Publishing, 2025
**Purpose:** Concrete, actionable best practices extracted and mapped to Lyra subsystems.

---

## Practice 1: Adopt a Three-Tier Memory Architecture
- **What:** Design agents with three distinct memory stores: (1) Short-term/Working Memory (ephemeral, session-scoped, cleared on session end), (2) Long-term Memory/Knowledge Base (persistent across sessions — user profiles, domain knowledge, learned patterns), and (3) Episodic Memory (timestamped interaction history with similarity-based retrieval for pattern recognition).
- **Why:** A single flat memory store causes context pollution (irrelevant history degrades decisions), prevents pattern learning across sessions, and cannot distinguish transient preferences from persistent knowledge. Three tiers enable: coherent multi-turn interactions (working), personalized service without re-asking (long-term), and learning from past successes/failures (episodic).
- **Lyra route:** §3.1 (Memory Subsystem), §3.2 (Working Memory), §3.3 (Long-term Memory), §3.4 (Episodic Memory)
- **Source:** Chapter 7, pp. 203-208

## Practice 2: Separate Coordination, Delegation, and Execution (CWD Pattern)
- **What:** Structure multi-agent systems with three distinct roles: Coordinator (strategic oversight, task decomposition, progress monitoring), Delegator (capability matching, load balancing, resource optimization), and Worker (specialized domain execution). Never collapse Coordinator+Delegator into a single agent for non-trivial systems.
- **Why:** Separation of concerns prevents coordination chaos (every agent talking to every other agent), coordinator bottleneck (single point of failure), and inefficient task assignment (round-robin instead of capability-optimized). Organizational psychology research shows this three-role division optimizes throughput, latency, and resource utilization simultaneously.
- **Lyra route:** §4.1 (Orchestrator), §4.2 (Multi-Agent Architecture), §5.1 (Task Router)
- **Source:** Chapter 6, pp. 171-189

## Practice 3: Implement Reflective Loops for Agent Self-Improvement
- **What:** Build three reflection mechanisms into every agent: (1) Meta-reasoning — track reasoning chains and compare actual vs. expected outcomes to identify failure patterns, (2) Self-explanation — generate explanations both for users (transparency mode) and for internal critique (learning mode), (3) Self-modeling — maintain an updatable internal representation of goals, beliefs, and knowledge that evolves with experience.
- **Why:** Static agents repeat the same mistakes. Without reflection, an agent that consistently fails on a particular reasoning pattern has no mechanism to detect or correct the pattern. Meta-reasoning + self-explanation + self-modeling together create a continuous improvement loop analogous to human metacognition. This is what separates an adaptive agent from a deterministic pipeline.
- **Lyra route:** §5.2 (Meta-cognition), §6.3 (Audit/Explainability), §9.2 (Self-Improvement Loop)
- **Source:** Chapter 4, pp. 113-143

## Practice 4: Use HTN Decomposition for LLM Agent Planning
- **What:** Hierarchical Task Network (HTN) planning — decompose complex tasks into progressively simpler subtasks in a tree structure — is the recommended planning strategy for LLM-based agents. It mirrors how language models naturally process tasks: high-level intent → sub-goals → actionable steps.
- **Why:** Traditional planning algorithms (STRIPS, partial-order planning) are too brittle for the nuanced, contextual nature of language-based tasks. Direct LLM reasoning without decomposition leads to missed steps and incomplete plans. HTN provides both structure (guaranteed decomposition) and flexibility (LLM fills in the leaves). It outperforms flat planning on multi-step task completion rates.
- **Lyra route:** §5.1 (Task Decomposition), §4.4 (Workflow Engine)
- **Source:** Chapter 5, pp. 155-162

## Practice 5: Treat the LLM as a Tool Dispatcher, Not an Executor
- **What:** The LLM generates structured tool-call specifications (which tool, what parameters) — it never executes code directly. An external Agent Controller interprets these specifications and performs the actual execution. The LLM is the decision-maker; the harness is the doer.
- **Why:** Separating dispatch from execution provides: (1) sandboxing (LLM can't run arbitrary code), (2) audit trail (controller logs all actual executions), (3) retry/fallback logic (controller can retry failed tool calls without LLM involvement), (4) model agnosticism (same controller works with different LLMs).
- **Lyra route:** §4.3 (Tool Use), §4.5 (Plugin System), §7.2 (Execution Harness)
- **Source:** Chapter 5, pp. 145-148

## Practice 6: Define Tools with Full JSON Schema, Not Just Docstrings
- **What:** Every tool must expose: name, natural-language description of purpose, input_schema (JSON Schema with types, descriptions, required fields). When using multiple model providers, abstract tool definitions behind a framework layer to avoid per-provider duplication.
- **Why:** The LLM uses tool descriptions (not code) to decide whether, which, and how to call a tool. Poor descriptions → wrong tool selection. JSON Schema provides machine-verifiable contracts that the Agent Controller can validate before dispatch. Framework abstraction (CrewAI, LangGraph) prevents vendor lock-in when models have different tool definition formats.
- **Lyra route:** §4.5 (Plugin Schema), §7.1 (API Contracts)
- **Source:** Chapter 5, pp. 148-152

## Practice 7: Layer Safety, Don't Bolt It On
- **What:** Implement five safety layers that work together: (1) Action Boundaries (policy-based governance, RBAC, context-aware permissions), (2) Decision Verification (multi-step validation, constraint satisfaction, outcome simulation), (3) Rollback Capabilities (immutable event sourcing, state checkpointing), (4) Real-time Monitoring (anomaly detection, drift detection, XAI insights), (5) Human-in-the-Loop Escalation (RLHF feedback, mandatory approval for high-stakes actions). No single layer is sufficient.
- **Why:** Agentic systems don't just generate content — they act autonomously. A hallucination that leads to a bad recommendation is annoying; a hallucination that triggers a financial transaction is dangerous. Each safety layer catches failures that slip through others. Event sourcing enables deterministic rollback when a bad decision chain is detected mid-execution.
- **Lyra route:** §6.1 (Safety Subsystem), §6.2 (Guardrails), §6.3 (Action Verification), §6.4 (Rollback/Recovery), §7.3 (Monitoring/Observability)
- **Source:** Chapter 9, pp. 242-248

## Practice 8: Implement Progressive Autonomy with Reliability Gates
- **What:** Start agents with heavily restricted action capabilities. As the agent demonstrates reliability in production (measured by decision quality metrics, error rates, successful rollback counts), progressively expand its autonomous action space. Each expansion requires passing an explicit reliability gate with predefined metrics.
- **Why:** Full autonomy from day one is irresponsible. Progressive autonomy builds trust with users, provides a natural rollback path (restrict to previous autonomy level), and ensures the safety mechanisms are battle-tested at each level before expanding. This mirrors how human organizations grant increasing authority to employees.
- **Lyra route:** §6.5 (Autonomy Levels), §9.3 (Deployment Strategy)
- **Source:** Chapter 9, pp. 245-246

## Practice 9: Design Context Management with Explicit Save/Restore Protocols
- **What:** Context management operates at three nested levels: Global context (system-wide settings, constraints, operational status), Session context (current interaction state, active searches, temporary preferences), and Task context (specific step in multi-step process, related dependencies). Every context switch must follow: preserve current context → save history of changes → restore target context → rebuild operational environment → reestablish relevant connections. Never assume context survives a restart.
- **Why:** Agents operating across multiple sessions, users, or tasks without explicit context protocols lose coherence — they forget what they were doing, mix information from different users, or repeat completed steps. Context merging with conflict resolution is essential for multi-agent systems where different agents build overlapping context.
- **Lyra route:** §3.5 (Context Management), §3.6 (Session Persistence), §7.4 (State Management)
- **Source:** Chapter 7, pp. 206-208

## Practice 10: Use Semantic Networks for Domain Knowledge + Episodic Memory for Patterns
- **What:** For structured domain knowledge, use semantic network representations (graph-based, nodes as concepts with labeled edges as relationships). For interaction-based learning, use episodic memory stores with similarity retrieval. The two complement each other: semantic networks provide the stable knowledge backbone; episodic memory captures fluid patterns from experience.
- **Why:** Semantic networks naturally support inheritance reasoning (if X is-a Y and Y has property Z, then X has property Z) — critical for domains with hierarchical knowledge (medical, legal, travel). Episodic memory captures temporal patterns that semantic networks miss: "users who booked flights to Tokyo in April consistently complained about cherry blossom crowd prices" — this is an episodic pattern, not a semantic fact.
- **Lyra route:** §3.3 (Knowledge Representation), §3.4 (Episodic Memory), §5.3 (Pattern Recognition)
- **Source:** Chapters 3 and 7, pp. 89-94 and pp. 205-208

## Practice 11: Build Agent Communication on Bidirectional Information Flows
- **What:** Every agent-to-agent communication channel must support: downward flow (task assignments, priorities, constraints from coordinator to worker) and upward flow (progress updates, results, resource utilization from worker to coordinator). Implement explicit negotiation protocols for conflict resolution between agents with overlapping responsibilities.
- **Why:** One-directional command structures create blind spots — the coordinator cannot optimize if it doesn't know worker capacity/status. Bi-directional flows enable dynamic reallocation (coordinator sees worker A is overloaded, delegates to worker B), early failure detection (worker reports tool failure upstream), and continuous optimization. Negotiation protocols prevent deadlocks when two agents produce conflicting plans.
- **Lyra route:** §4.2 (Agent Communication Bus), §4.4 (Workflow Coordination)
- **Source:** Chapter 6, pp. 184-187

## Practice 12: Express Uncertainty Explicitly — Never Present AI Output as Infallible
- **What:** Every agent output that involves prediction, recommendation, or generation must include: (1) confidence level (quantitative or qualitative), (2) key assumptions made, (3) factors that would change the output. Provide users with override mechanisms for all automated decisions.
- **Why:** Users who discover one confidently wrong output lose trust in the entire system. Expressing uncertainty is trust-building, not trust-eroding — it signals that the system understands its limitations. Override mechanisms transform the user from passive consumer to active collaborator, which improves both trust and output quality through feedback loops.
- **Lyra route:** §6.2 (Guardrails/Confidence), §7.5 (User-Facing Explainability)
- **Source:** Chapter 8, pp. 224-227

## Practice 13: Optimize Workflows with Dependency-Aware Parallelism
- **What:** Not all tasks benefit from parallel execution. Before parallelizing: (1) perform dependency analysis to identify the critical path, (2) classify tasks as sequential-dependent (must wait for predecessor), parallel-independent (no shared state), or background (low-priority, no user visible). Implement backpressure mechanisms to prevent API rate limit violations when parallel fan-out is high.
- **Why:** Naively parallelizing everything causes: API rate limit failures, resource contention, and users waiting for the slowest parallel branch anyway (Amdahl's law). Dependency-aware scheduling maximizes throughput where it matters (concurrent searches) while preserving correctness where ordering matters (book flight → confirm → charge).
- **Lyra route:** §4.4 (Workflow Engine), §5.4 (Execution Optimizer)
- **Source:** Chapter 7, pp. 208-212

## Practice 14: Involve Diverse Stakeholders in Agent Design, Not Just Engineers
- **What:** Before deploying an agent in a domain: include domain experts (doctors, lawyers, travel agents), ethicists, affected user groups, and compliance/legal reviewers in the design process. Conduct red-teaming exercises that specifically target the agent's autonomous action capabilities, not just its output quality.
- **Why:** Engineers cannot anticipate all failure modes in domains they don't practice. A travel agent developer won't know that recommending hotels in a specific Bangkok neighborhood during monsoon season is dangerous. Diverse stakeholders catch domain-specific risks that technical testing misses. Red-teaming against autonomous actions (not just outputs) is essential because agentic failure modes are fundamentally different from generation failure modes.
- **Lyra route:** §6.6 (Ethical Review), §8.2 (Domain Adaptation)
- **Source:** Chapter 9, pp. 246-247

## Practice 15: Maintain an Immutable Audit Log of All Agent Decisions and Actions
- **What:** Every agent decision and action must be recorded in an append-only, immutable log with: timestamp, agent ID, decision context (inputs, state, tools available), decision made (tool called, parameters, action taken), and outcome. Use event sourcing patterns (Kafka, Temporal.io) for production systems.
- **Why:** Immutable logs enable: (1) deterministic rollback (replay state to any point), (2) root-cause analysis (trace a bad outcome to the specific decision that caused it), (3) compliance (regulatory auditors need decision trails), (4) learning (episodic memory is built from audited logs). Without immutable logs, you can't distinguish "the agent made a bad decision" from "the environment changed unexpectedly."
- **Lyra route:** §7.2 (Audit Trail), §7.3 (Observability), §6.3 (Decision Verification)
- **Source:** Chapter 9, pp. 243-244
