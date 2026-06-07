# 30 Agents Every AI Engineer Must Build — Best Practices Playbook

## Practice 1: Design Agents Around the Cognitive Loop, Not Linear Pipelines
- **What:** Architect every agent with the five-phase cognitive loop: Perception → Reasoning → Planning → Action → Learning. Each phase feeds back into the others — it is a feedback-driven cycle, not a linear sequence. Use the loop as both a design tool and a runtime execution model.
- **Why:** Linear pipelines break under environmental change and cannot adapt to unforeseen inputs. The cognitive loop enables continuous situational awareness, dynamic replanning, and progressive improvement. Agents that close the learning loop accumulate capability over time; those that don't remain static.
- **Lyra route:** §4.1, §4.2 — Core agent architecture, cognitive loop implementation
- **Source:** Chapter 1 (Architecture of agents, The cognitive loop), Chapter 5 (Autonomous Decision-Making agent)

## Practice 2: Separate the Cognition Core from Execution, with Explicit Contracts
- **What:** Design the agent's cognition core as a dynamic broker that synthesizes input from reasoning, memory, planning, and persona layers — but never as a monolithic coordinator. Execution (tool calls, API invocations, actions) lives in a separate layer with explicit schema contracts (JSON/Pydantic). The reasoning component determines what to call and when; the execution layer handles how.
- **Why:** Separation of decision and execution improves traceability, allows both layers to evolve independently, and prevents reasoning failures from cascading into unsafe actions. Explicit schema contracts make interfaces predictable and enable safe tool discovery at runtime.
- **Lyra route:** §4.2, §4.7 — Cognition architecture, tool interface design
- **Source:** Chapter 1 (Communication patterns between components), Chapter 7 (Function-calling architecture patterns)

## Practice 3: Implement Three-Tier Memory: Working, Episodic, Semantic
- **What:** Every production agent needs three memory types: Working memory (immediate session context in the LLM prompt window), Episodic memory (historical interaction log with timestamps, retrieved via vector similarity search), Semantic memory (domain facts and world knowledge, continuously updated from authoritative sources). Use a dual-memory hierarchy for conversational agents: recent exchanges in raw format (RAM equivalent) + summarized gists in persistent stores (Disk equivalent).
- **Why:** Without all three memory tiers, agents exhibit: loss of immediate conversational coherence (no working memory), repeated history and broken personalization (no episodic memory), hallucinated or stale answers (no semantic memory). Memory is the difference between a stateless tool and a persistent, learning system.
- **Lyra route:** §4.2, §4.5 — Memory architecture design
- **Source:** Chapter 5 (The Memory-Augmented agent), Chapter 7 (Memory-augmented multi-agent systems), Chapter 10 (The dual-memory hierarchy)

## Practice 4: Use the Tool Selection Funnel for Safe, Scalable Tool Invocation
- **What:** Implement a three-stage tool selection funnel: (1) Intent classification — broad category filter to reduce search space, (2) Semantic search via embeddings — rank candidates by vector similarity, discard below confidence threshold (0.7), (3) Constraint filtering — deterministic checks for permissions, input compatibility, and historical failure status. Implement dynamic reranking: if a selected tool fails, re-enter the funnel with that tool temporarily blocked.
- **Why:** A single-stage selection breaks as tool count grows. The funnel provides defense-in-depth: classification eliminates irrelevant tools quickly, semantic search finds the best semantic match, and constraint filtering provides a final safety/sanity gate. Dynamic reranking enables graceful recovery without aborting the task.
- **Lyra route:** §4.7 — Tool discovery and invocation architecture
- **Source:** Chapter 7 (Tool discovery and selection algorithms)

## Practice 5: Implement Layered Error Recovery with Circuit Breakers
- **What:** Build a four-layer error recovery architecture: (1) Safe invocation wrappers — every tool call wrapped in try/except with targeted retry logic (exponential backoff for network errors), (2) Fallback tool chains — alternative tools that accomplish the same goal, (3) Failure memory/circuit breaker — if a tool fails N times in a window, temporarily mark it unavailable, (4) Human escalation — as a planned, first-class workflow branch, not a failure. Distinguish transient failures (retry) from permanent failures (dead-letter queue).
- **Why:** In any system relying on external components, failure is inevitable, not exceptional. Without layered recovery, a single tool failure cascades into task failure. Circuit breakers prevent wasted cycles on known-broken tools. Planned escalation paths transform human review from emergency intervention into governed oversight.
- **Lyra route:** §4.7, §4.16 — Tool error handling, reliability engineering
- **Source:** Chapter 7 (Error handling in tool integration)

## Practice 6: Build Agentic Workflows as State Machines with HITL Checkpoints
- **What:** Model long-running agent processes as state machines or directed graphs, not linear scripts. Each step is executed by a tool or specialized agent. Embed Human-in-the-Loop (HITL) checkpoints at decision boundaries — not as failure handlers but as planned, first-class branches. Use LangGraph's native checkpoint support to pause workflows, inspect reasoning traces, and provide corrective guidance before resuming.
- **Why:** Linear scripts cannot handle branching logic, error recovery, or conditional human intervention. State machines provide explicit modeling of all possible paths. First-class HITL checkpoints ensure human judgment is applied where it adds most value, while automation handles the rest.
- **Lyra route:** §4.7, §4.9 — Workflow orchestration, HITL coordination
- **Source:** Chapter 7 (The agentic workflow system, Case studies)

## Practice 7: Adopt Test-Driven Generation (TDG) for Code-Producing Agents
- **What:** Transform LLM code generation from probabilistic suggestion into deterministic verification: write the test suite first (executable specification), generate code against tests, run tests, analyze failures, regenerate until all assertions pass. Use multi-agent orchestration with specialized planner, coder, and critic roles coordinated through state graphs. Every generated artifact must demonstrably satisfy its test contract before being considered complete.
- **Why:** Standard one-shot LLM code generation is inherently unreliable — the output may be syntactically valid but logically wrong, hallucinated APIs, or convention-violating. TDG establishes an executable contract: correctness is proven by test passage, not assumed from generation confidence. This pattern applies beyond code to any structured output with verifiable correctness criteria.
- **Lyra route:** §4.9 — Code generation, verification-first patterns
- **Source:** Chapter 9 (Code-Generation agents, The TDG architecture and workflow)

## Practice 8: Embed Compliance as an Automated Gate in the Development Pipeline
- **What:** Treat compliance policies as executable code artifacts stored in version-controlled repositories (Policy-as-Code). Use formal policy engines (OPA/Rego) to evaluate every code change against regulatory requirements automatically. Integrate compliance gates alongside functional test gates in CI/CD pipelines. Policy rules function as executable tests for normative correctness — a policy violation fails the build and blocks the merge, just as a broken unit test would.
- **Why:** Manual compliance review creates a bottleneck and cannot scale with development velocity. Embedding compliance in the pipeline shifts governance from external audit to continuous enforcement. It trains developers through immediate, specific feedback — the PCI DSS case study showed 85% reduction in pre-deployment violations within 6 months.
- **Lyra route:** §4.9, §4.17 — Compliance-driven development, safety gates
- **Source:** Chapter 9 (Compliance-Driven agents, PCI DSS case study)

## Practice 9: Close the Self-Improvement Loop with Structured Feedback Translation
- **What:** Implement the full closed-loop control system: Task Execution → Sensing Layer (explicit user feedback, implicit behavioral telemetry, synthetic automated evaluation) → Critic Agent (evaluates against KPIs: task completion rate, error recovery ratio, latency distribution, user satisfaction, improvement velocity) → Planner Agent (generates structured ImprovementHypothesis objects with adaptation_type, confidence, evidence_count, rollback_safe flag) → HITL Checkpoint (for significant changes) → Learning Layer (LoRA adapters, prompt template updates, threshold adjustments) → Deploy & Test → back to Task Execution.
- **Why:** Static agents degrade as environments shift. Self-improvement without structure risks catastrophic changes. The structured feedback-to-adaptation pipeline ensures every change is traceable, evidence-based, and reversible. The HITL checkpoint gates significant changes while low-risk, high-confidence improvements proceed automatically.
- **Lyra route:** §4.9, §4.16 — Self-improvement architecture, continuous adaptation
- **Source:** Chapter 9 (The Self-Improving agent)

## Practice 10: Implement the PTCF Blueprint for Agent System Prompts
- **What:** Design system prompts using the PTCF framework: Persona (identity, tone, behavioral constraints), Task (core mission, capabilities, limitations), Context (operational boundaries, domain knowledge, tool access), Format (structured output expectations, response schemas). Treat the system prompt as the agent's constitution — it defines what the agent is, not just what it should do. The user prompt is the dynamic stimulus operating within that constitutional framework.
- **Why:** Ad-hoc prompts produce inconsistent agent behavior. PTCF provides a principled, repeatable framework for prompt design that aligns with the agent's cognitive architecture. The system prompt as constitution ensures that even as tasks vary, behavior stays within defined guardrails.
- **Lyra route:** §4.3 — System prompt design, agent constitution
- **Source:** Chapter 3 (The two-layer prompt architecture, The PTCF blueprint)

## Practice 11: Ground Agent Architectures in the Agent Development Lifecycle
- **What:** Follow the ADL: Conceptualization (define goals, map to sub-goals, set measurable success metrics including alignment and user trust) → Architecture & Design (choose cognitive models, document decisions with ADRs, integrate security/safety from the start) → Implementation (build modules, integrate into CI/CD with automated cognitive workflow testing) → Evaluation (measure task completion, decision quality, robustness under ambiguity using production shadows) → Governance (continuous monitoring, patching, compliance auditing, model versioning with rollback).
- **Why:** Agents are not traditional software — they require an adaptive, iterative lifecycle that accounts for non-deterministic behavior, continuous learning, and evolving goals. The ADL provides a structured framework that mirrors the operational complexity of modern agent systems while ensuring traceability and governance.
- **Lyra route:** §4.1, §4.4 — Development methodology, deployment lifecycle
- **Source:** Chapter 1 (The Agent Development Lifecycle)

## Practice 12: Design for Observability from Day One
- **What:** Instrument every agent subsystem: tool invocation latency, success/failure rates, memory retrieval relevance, reasoning trace depth, escalation frequency, user satisfaction signals. Use dedicated agent observability platforms (LangSmith, Prometheus/Grafana) for real-time monitoring. Log every action, error, and recovery attempt with structured metadata. For A/B testing, measure beyond latency: task completion rate, tool call frequency, escalation rate, and user satisfaction. Use canary deployments with automatic rollback on behavioral metric regression.
- **Why:** Agent behavior is non-deterministic — traditional service monitoring (CPU, memory, error rate) is insufficient. You cannot improve what you cannot measure. Observability data feeds the self-improvement loop and enables evidence-based governance. Without behavioral metrics, regressions go undetected until users complain.
- **Lyra route:** §4.4, §4.16 — Observability, monitoring, deployment patterns
- **Source:** Chapter 4 (A/B testing, Operational procedures), Chapter 9 (Observability platforms)

## Practice 13: Encode Ethics as Machine-Executable Constraints in the Decision Loop
- **What:** Interpose an ethical checkpoint between the reasoning and action phases of every agent. Use deontic logic operators (Obligatory O(φ), Permitted P(φ), Forbidden F(φ)) to make ethical rules machine-executable. Before executing any action, check consistency with the ethical rule set E — if E ∪ {action} is consistent, permit; if inconsistent, attempt automated mitigation or escalate to human. The ethical evaluation layer is a first-class architectural component, not a post-hoc filter.
- **Why:** Post-hoc content filtering does not produce ethical behavior — it produces filtered unethical behavior. True ethical reasoning must structure the entire decision pipeline around explicit value constraints. The separation of "how" (reasoning) from "if" (ethical evaluation) creates systems capable of complex decision-making without sacrificing safety or alignment.
- **Lyra route:** §4.17 — Ethical reasoning, safety guardrails, value alignment
- **Source:** Chapter 12 (The Ethical Reasoning agent, Value alignment frameworks)

## Practice 14: Implement Calibrated Confidence and Audience-Appropriate Explanations
- **What:** Every agent decision that affects users must carry a calibrated confidence score, not a raw probability. Provide structured explanations using multiple frameworks: LIME/SHAP for feature attribution, counterfactual analysis ("what would change the decision"), and reasoning trace visibility. Calibrate explanation depth and format to the audience — clinician gets primary assessment + SHAP values + differential; patient gets plain-language summary; regulator gets full audit trail with all intermediate decisions.
- **Why:** Unexplained decisions erode trust. Uncalibrated confidence leads to over-reliance (when confidence is falsely high) or unnecessary escalation (when falsely low). Audience-appropriate explanations ensure that transparency serves its purpose: enabling informed action by the recipient.
- **Lyra route:** §4.17 — Explainability, confidence communication
- **Source:** Chapter 12 (The Explainable agent, Confidence communication methods)

## Practice 15: Build for Evolution — Invest in Learning Infrastructure
- **What:** Establish the infrastructure for continuous agent improvement from the start: comprehensive interaction logging (full reasoning traces, not just outcomes), structured feedback collection (explicit ratings, implicit telemetry, synthetic benchmarks), governed adaptation pipelines (data filtering → training → multi-dimensional evaluation → versioned deployment with rollback). Start with memory consolidation (scheduled batch jobs reviewing recent episodes to extract generalizable patterns) before attempting architectural self-modification. The crawl-walk-run roadmap: automate high-volume tasks → add planning for complex workflows → enable learning and multi-agent coordination.
- **Why:** The improvement velocity metric (rate at which corrections lead to measurable gains) is the most important ROI indicator. Organizations that invest in learning infrastructure benefit from compounding returns; those that treat agents as static deployments see flat curves. The center-of-excellence model reduces ethical overhead from 30-40% for the first agent to 10-15% for subsequent ones.
- **Lyra route:** §4.9, §4.19 — Continuous improvement, learning architecture, strategic roadmap
- **Source:** Chapter 9 (Operationalizing continuous adaptation), Chapter 17 (Strategic implementation, Building agent capability roadmaps)
