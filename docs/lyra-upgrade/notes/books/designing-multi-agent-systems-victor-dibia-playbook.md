# Designing Multi-Agent Systems — Best Practices Playbook

## Practice 1: Choose the Simplest Architecture First
- **What:** Before building any agent system, walk through the decision framework: Model-only → Single Agent → Multi-Agent Workflow → Autonomous Multi-Agent. Add complexity only when evaluation data proves it necessary. Start with a direct model call baseline and only escalate when the task requires action, diverse expertise, adaptive solutions, or multi-step planning.
- **Why:** Evaluation data shows Direct-Model beats Multi-Agent-AI on Simple-Reasoning tasks (9.7 vs 9.3) while using 43x fewer tokens. Multi-agent overhead provides no benefit for simple tasks and introduces coordination failures, cost bloat, and debugging complexity. "A single well-designed agent often outperforms a poorly designed multi-agent system."
- **Lyra route:** §4.1 (Architecture Decision Framework)
- **Source:** Chapters 1, 2, 11

## Practice 2: Build Agents with Five Design Principles
- **What:** Every agent implementation should embody five principles: (1) Async-First Architecture — use async/await throughout; (2) Event-Based Streaming — yield progress events for real-time UX and debugging; (3) Component Serialization — every component serializable to JSON for version control; (4) Graceful Cancellation — CancellationToken propagated through all operations; (5) Abstract Base Classes — BaseAgent, BaseChatCompletionClient, BaseTool, BaseMemory for provider-agnostic design.
- **Why:** A 3-agent workflow takes 30s synchronously vs 10s with async. Streaming prevents blank-screen UX during 30s+ operations. Serialization enables configuration UIs and checkpointing. Cancellation prevents runaway costs. Abstract classes prevent vendor lock-in and enable mock testing.
- **Lyra route:** §4.3 (Agent Core Design)
- **Source:** Chapter 4

## Practice 3: Use Structured Output as Foundation for Reliability
- **What:** Constrain all model outputs to match Pydantic schemas using the `output_format` parameter. This eliminates fragile text parsing and enables deterministic handling of tool calls, memory operations, and agent-to-agent communication. Every model response becomes a typed object rather than free text.
- **Why:** Without structured output, parsing "Please call the get_weather function with location set to Paris" is brittle. With it, you get reliable JSON like `{"name": "get_weather", "arguments": {"location": "Paris"}}` that can be safely executed. This is the foundation for reliable tool calling, structured memory, and deterministic workflows.
- **Lyra route:** §4.3 (Agent Core), §4.4 (Tools)
- **Source:** Chapter 4, Section 4.5

## Practice 4: Implement Middleware as the Universal Control Plane
- **What:** Route ALL model calls and tool executions through a middleware chain with three hooks: process_request() (before execution, can block), process_response() (after execution, can filter/redact), process_error() (handle failures with retry/fallback). Apply middleware for: security scanning (prompt injection detection), PII redaction, rate limiting, logging/observability, and cost tracking.
- **Why:** Middleware provides a single interception point for security, observability, and control without cluttering agent logic. A SecurityMiddleware can block malicious prompts before they reach the model. PIIRedactionMiddleware automatically redacts emails/phones. RateLimitMiddleware prevents abuse. All are composable and framework-agnostic.
- **Lyra route:** §4.8 (Safety), §4.9 (Observability)
- **Source:** Chapter 4, Section 4.9; Chapter 13, Section 13.4.3

## Practice 5: Design for Two Memory Architectures
- **What:** Implement both application-managed memory (developer calls `memory.add()`, framework auto-injects context via `get_context()` using RAG/vector search) and agent-managed memory (agents explicitly call memory tools to store, retrieve, organize knowledge). Use app-managed for conversation history and automatic context injection. Use agent-managed for cross-session learning where agents actively curate their own knowledge base.
- **Why:** Application-managed memory provides convenience and consistency. Agent-managed memory enables cross-session learning — e.g., a code reviewer that discovers a race condition pattern in Session 1 and flags it in completely new Session 2. Both architectures can coexist. Security: agent-managed memory must be sandboxed with path validation to prevent directory traversal attacks.
- **Lyra route:** §4.2 (Memory)
- **Source:** Chapter 4, Sections 4.7-4.8

## Practice 6: Apply the Orchestrator Loop Pattern Universally
- **What:** Implement all orchestration patterns (round-robin, AI-driven, plan-based, handoff, workflow) through the same core loop: select next agent → prepare context → execute agent → update shared state → check termination. Pattern-specific logic only in `select_next_agent()` and `prepare_context()`. Use BaseOrchestrator to handle streaming, cancellation, state management consistently.
- **Why:** This architecture delivers consistency across patterns (easier to understand/maintain), composability (mix patterns by switching orchestrator implementations), extensibility (new patterns inherit robust infrastructure), and comprehensive observability (common instrumentation works across all pattern types).
- **Lyra route:** §4.2 (Orchestration)
- **Source:** Chapter 7, Section 7.1

## Practice 7: Design Composable Termination Conditions
- **What:** Combine termination conditions using OR semantics (| operator): budget-based (max messages, token limits, timeouts) + semantic (LLM-detected completion via TextMentionTermination) + external (human intervention, API-triggered stops). Always align termination conditions with agent instructions — if using TextMentionTermination("TASK_COMPLETE"), the agent's instructions MUST explicitly tell it to emit that text. Use TaskStatusTool for explicit completion signaling.
- **Why:** The most common termination anti-pattern is expecting agents to signal completion without being instructed to do so. Poor termination leads to either runaway costs (never stopping) or premature exits (abandoning solvable tasks). Aligned termination prevents both.
- **Lyra route:** §4.2 (Orchestration)
- **Source:** Chapter 7, Section 7.2; Chapter 11, Section 11.3.5

## Practice 8: Adopt Evaluation-Driven Development
- **What:** Define success measures BEFORE building agent code. Use the 5-step framework: (1) Define success criteria, (2) Create task suite with representative tasks + edge cases, (3) Choose metrics and judges (deterministic for measurable properties, LLM judges for nuanced quality), (4) Establish baselines (direct model calls, single agents, previous versions), (5) Plan iteration workflow. Build evaluation infrastructure from day one so every production run becomes a potential evaluation data point.
- **Why:** "You cannot optimize what you cannot measure." Teams that build evaluation harnesses early iterate faster and discover better solutions. Evaluation constraints become design requirements — if you'll measure reasoning efficiency, you'll build token tracking from day one. Without evaluation, optimization is a guessing game.
- **Lyra route:** §4.10 (Evaluation Harness)
- **Source:** Chapter 10

## Practice 9: Debug Your Evaluation Judges Before Trusting Results
- **What:** When using LLM-as-judge, inspect judge reasoning and trajectory traces when results contradict expectations. Two common pitfalls: (1) Verbosity Penalty — judges penalize multi-agent transparency as unnecessary length (fix: custom instructions explicitly stating "DO NOT PENALIZE multi-agent collaborative process visibility"), (2) Dimension Normalization — CompositeJudge weights must normalize per-dimension, not globally. Log complete trajectories with judge reasoning. Iterate on judge instructions.
- **Why:** Initial evaluation of multi-agent systems scored 6.82/10 due to verbosity bias. After adding custom instructions, scores improved to 9.30/10 — revealing true performance. Without debugging the evaluation itself, incorrect conclusions would have been drawn about multi-agent system performance.
- **Lyra route:** §4.10 (Evaluation Harness)
- **Source:** Chapter 10, Section 10.6.3

## Practice 10: Follow the Two-Level Optimization Framework
- **What:** Optimize agent-system parameters first (highest ROI): instructions, tools, memory, model selection, orchestration patterns, termination conditions, human delegation. Iterate based on evaluation failures — inspect trajectories, identify failure modes, adjust parameters, re-evaluate. Only pursue model-level optimization (finetuning, distillation, routing) after agent-system optimization plateaus AND specific conditions warrant it (residual domain-specific failures, cost/latency/privacy requirements).
- **Why:** Agent-system parameters provide the most leverage with the least effort. Instructions and tools have the most direct impact on behavior. The typical trajectory: optimize agent-system parameters until performance plateaus (often 95%+ with frontier models), then consider finetuning smaller models. A 7B model finetuned on your task can match a 70B generalist for your domain.
- **Lyra route:** §4.11 (Optimization)
- **Source:** Chapter 11

## Practice 11: Apply the Rule of Two for Agent Security
- **What:** Until robust prompt injection defenses exist, agents within a session should satisfy at most two of: [A] Process untrustworthy inputs, [B] Access sensitive systems/private data, [C] Change state or communicate externally. If all three are required, agents MUST NOT operate autonomously — human-in-the-loop approval required.
- **Why:** Risk scales with action capability. A jailbroken LLM produces harmful text; a jailbroken agent can delete files, exfiltrate data, execute unauthorized transactions. The Rule of Two (Meta AI 2025) provides a practical decision framework for which risks to accept. Map directly to middleware: input filtering controls [A], tool authorization gates [C], isolation mechanisms protect [B].
- **Lyra route:** §4.8 (Safety)
- **Source:** Chapter 13, Section 13.4.1

## Practice 12: Never Trust an Agent in Multi-Tenant Environments
- **What:** Assume agents will find and attempt to use any accessible resource when optimizing for task completion. Implement strong containerization (each agent in isolated containers with minimal filesystem access), credential isolation (secret managers, not environment variables), least-privilege tooling (never general-purpose shells), and separate infrastructure for agents.
- **Why:** Traditional security relies on services lacking agency — they don't explore their environment. Agents break this: an agent encountering an SMTP failure will scan for configuration files, find credentials for a different email service, and use them to complete the task. From the agent's perspective this is creative problem-solving; from a security perspective it's unauthorized access across boundaries. "What was safe: storing different services' credentials on the same machine isolated by process permissions. What changed: agents actively explore."
- **Lyra route:** §4.8 (Safety)
- **Source:** Chapter 13, Section 13.4.2

## Practice 13: Use Plan-Based Orchestration for Complex, Unknown Tasks
- **What:** For tasks where the solution path is unknown, use PlanBasedOrchestrator: LLM-generated execution plan → execute steps with specialized agents → evaluate each step's success → retry failed steps with enhanced instructions → replan if insufficient progress. Achieved #1 on GAIA leaderboard (Magentic-One architecture). Dynamically spawn subagents based on query complexity.
- **Why:** Magentic-One and Anthropic's Research system both use orchestrator-worker patterns with dynamic agent spawning — Research spawning 1-10+ subagents based on query complexity, achieving 90.2% improvement over single-agent approaches. Built-in metacognition: agents evaluate their own progress and replan — up to 31% performance improvement through ledger-based self-monitoring.
- **Lyra route:** §4.2 (Orchestration - Plan-Based)
- **Source:** Chapter 2, Section 2.3.1; Chapter 7, Section 7.5; Chapter 11, Section 11.3.8

## Practice 14: Match Instructions to Specific Models
- **What:** Maintain separate instruction sets for different model families/versions. Version-control prompts alongside model choices. Run A/B tests when switching models. Validate with evaluation framework that instruction changes preserve performance. More capable models can handle vague "think step-by-step" instructions; smaller models need explicit enumerated steps.
- **Why:** System messages aren't portable across model versions or providers. The same "analyze the data and provide insights" instruction works with GPT-4 but produces inconsistent results with smaller models. A model-specific registry prevents degradation when swapping models.
- **Lyra route:** §4.3 (Agent Core — Model Client Abstraction)
- **Source:** Chapter 11, Section 11.3.3

## Practice 15: Design Evaluation Suites as a Creative Domain Problem
- **What:** "The key to designing effective evaluation suites is translating domain expertise into measurable criteria. Ask: If an expert human were evaluating this outcome, what would they check?" For software: functional correctness, test coverage, code quality, type safety, documentation, error handling. For visualizations: data accuracy, visual clarity, chart choice, legibility, statistical honesty, context. Mix deterministic metrics (test pass rate, mypy errors, coverage %) with LLM judges (code readability, architectural soundness, visual quality). Validate that metrics correlate with real downstream success.
- **Why:** Traditional ML metrics (BLEU, ROUGE, NDCG) fail for agentic systems because outputs are heterogeneous (text + code + images + structured data + tool calls), non-deterministic, and process quality matters as much as outcome. This requires domain-specific creativity — translating what experts actually check into measurable evaluation methods. Teams that invest in thoughtful evaluation design build better systems faster.
- **Lyra route:** §4.10 (Evaluation Harness)
- **Source:** Chapter 10, Section 10.4
