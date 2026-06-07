# Designing Multi-Agent Systems — Chapter Notes

**Author:** Victor Dibia | **Year:** 2025 | **Pages:** 526 | **Code companion:** picoagents (Python, built from scratch)

**Core Thesis:** Multi-agent systems are not a silver bullet. They should be chosen deliberately based on task characteristics (planning, diverse expertise, extensive context, adaptive solutions), built from first principles with async-first streaming architecture, middleware-based safety, and systematic trajectory-based evaluation. The book provides an architecture-agnostic, fundamentals-first approach — building the picoagents library from scratch to teach design decisions rather than framework-specific tutorials. Key message: "Start with the simplest architecture that could work. Add complexity only when evaluation demonstrates clear benefits."

**Target Audience:** System architects, AI engineers, technical leaders transitioning from single LLM calls to orchestrated agent systems. Prerequisites: basic Python, CLI familiarity.

---

## Chapter 1: Understanding Multi-Agent Systems

- **Key insight:** Tasks exist on a complexity spectrum — Model-Level (direct info retrieval) → Agent-Level (planning + tool use) → Multi-Agent (diverse expertise + iterative development). Choose the right level. 47.7% of Y Combinator startups in 2025 are building AI agents (7.8x increase from 2020).
- **Core definition:** Agent = entity that can Reason, Act, Communicate, Adapt. Multi-Agent System = collection of specialized agents collaborating through orchestration mechanisms.
- **Best practices:**
  - Always ask: "Does this task require action beyond text generation?" If not, direct model calls suffice.
  - Decompose complex tasks via four characteristics: Planning, Diverse Expertise, Extensive Context, Adaptive Solutions
  - Multi-agent systems benefit most when tasks require exploration and adaptation — not when the solution path is fully known
- **Anti-patterns:** Using multi-agent systems for simple QA tasks; premature distribution (vast majority of use cases are well-served by single process/thread applications)
- **Decision framework:** Model-only → Single Agent → Multi-Agent Workflow → Autonomous Multi-Agent. Progress only when task characteristics demand it.
- **Relevant to Lyra §4.x:** §4.1 (Architecture) — The task-complexity spectrum directly informs when Lyra should use single-agent vs multi-agent orchestration.

---

## Chapter 2: Multi-Agent Patterns

- **Key insight:** Orchestration patterns exist on a spectrum: Workflow (explicit control) ↔ Autonomous (emergent control). The right choice depends on whether the solution path is known or must be discovered.
- **Workflow Patterns (Explicit Control):**
  - Sequential: A→B→C, predictable execution, easy debugging
  - Conditional: Branching via logic-based edges (supervisor variant: central node routes to specialists)
  - Parallel: DAG execution with fan-out/fan-in, automatic dependency detection
  - Key benefit: reliability and predictability; key cost: rigidity
- **Autonomous Patterns (Emergent Control):**
  - Plan-Based: Orchestrator agent creates plans, assigns tasks, monitors progress (Magentic-One architecture — achieved #1 on GAIA leaderboard)
  - Handoff: Peer-to-peer delegation, agents see each other as tools, local decision-making
  - Conversation-Driven: Shared conversation, orchestration emerges from dialogue
    - Round-Robin: Fixed turn order, simple but effective
    - AI-Driven: LLM selects next speaker dynamically based on context (enables natural retry loops)
- **"Agents All the Way Down" Design Principle:** Any agent may itself be a multi-agent system internally. Composite agents present as single entities to the broader system while internal conversations remain private. This provides clear boundaries and reduces communication noise.
- **Hybrid approach (recommended):** Use workflows for predictable components, autonomous patterns for exploratory components, within a single system
- **Task Management Patterns (cross-cutting):**
  - Termination: Budget-based (time/cost/iterations) + Semantic (LLM-detected completion) + External signals (human intervention). Combine with OR semantics.
  - Human Delegation: LLM-based (agent reasoning) vs Rule-based (code-defined thresholds)
- **Pattern-Selection Guideline:** "Match the pattern to the task's inherent characteristics and your system's reliability requirements, rather than forcing all orchestration through a single pattern type."
- **Relevant to Lyra §4.x:** §4.2 (Orchestration) — The full pattern taxonomy maps directly to Lyra's orchestration layer design.

---

## Chapter 3: UX Principles for Multi-Agent Systems

- **Key insight:** Four essential UX principles: Capability Discovery, Cost-Aware Delegation, Observability & Provenance, Interruptibility.
- **The shift:** Software 1.0 (direct manipulation) → Software 3.0+ (delegation design). Users set goals, agents determine execution paths.
- **Best practices:**
  - Make agent capabilities visible before invocation (capability discovery)
  - Show cost/consequence of actions — not all tool calls are equal risk (cost-aware delegation)
  - Full conversation traces with agent identities visible (observability)
  - Always provide Stop/Cancel buttons connected to cancellation tokens (interruptibility)
- **Relevant to Lyra §4.x:** §4.9 (UX/Interface) — Core UX patterns for Lyra's web interface.

---

## Chapter 4: Building Your First Agent

- **Key insight:** Agent = model + tools + memory, with middleware as the control plane. The execution loop is: Prepare Context → Call Model → Handle Response (text or tool calls) → Iterate → Return.
- **5 Design Principles:**
  1. Async-First Architecture: 3-agent workflow: 30s synchronous → 10s async
  2. Event-Based Streaming: Real-time progress for UX + debugging
  3. Component Serialization: Every component serializable to JSON (version control, configuration UIs)
  4. Graceful Cancellation: CancellationToken propagates through LLM calls, tool executions, etc.
  5. Abstract Base Classes: BaseAgent, BaseChatCompletionClient, BaseTool, BaseMemory — prevent vendor lock-in
- **Structured Output (Critical):** The "key to reliable agents." Constrain models to generate JSON matching Pydantic schemas. Enables reliable tool calling (eliminating fragile text parsing), structured memory storage, and deterministic agent-to-agent communication.
- **Tool Architecture:**
  - BaseTool abstract class with `parameters` (JSON schema) and `execute()` — extensible to REST APIs, MCP tools, databases
  - FunctionTool: Automatic conversion of Python functions with type hints → LLM-compatible tool schemas
  - Agent tool integration: process_tools() → get_tools_for_llm() → execute_tool_call() with graceful error handling
- **Memory Architecture (Two Approaches):**
  - Application-Managed (BaseMemory): Developer stores via `memory.add()`, framework auto-injects via `get_context()`. Uses RAG with vector databases. Three operations: add(), query(), get_context().
  - Agent-Managed (MemoryTool): Agents explicitly control what to store/retrieve via tool calls. Enables cross-session learning. Six operations: view, create, str_replace, insert, delete, rename.
  - Hybrid coexistence: Use app-managed for conversation history, agent-managed for organizing learned patterns.
  - Separation: AgentContext (transient session state, serializable for stateless deployments) vs BaseMemory (persistent knowledge)
- **Middleware System (Security + Observability):**
  - Three hooks: process_request() (before, can block), process_response() (after, can filter), process_error() (handle failures)
  - SecurityMiddleware: Pattern-based detection of prompt injection, hex encoding, script injection
  - PIIRedactionMiddleware: Regex-based detection/redaction of emails, phones, etc.
  - RateLimitMiddleware: Usage tracking per user/session
  - LoggingMiddleware: Capture every model call with timing
  - All model calls and tool executions are routed through the middleware chain
- **Agent Execution Loop (pseudocode):**
  ```
  async def agent_execution_loop(task):
      context = prepare_context(task, instructions, memory, history)
      while not done:
          response = await model_client.create(context)  # via middleware
          if response.has_tool_calls:
              for tool_call in response.tool_calls:
                  result = await execute_tool(tool_call)  # via middleware
                  context.append(result)
          else:
              done = True
      update_memory(context)
      return response
  ```
- **Relevant to Lyra §4.x:** §4.3 (Agent Core), §4.4 (Tools/Plugins), §4.2 (Memory), §4.8 (Safety) — The picoagents architecture is the most directly applicable model for Lyra's agent core.

---

## Chapter 5: Building Computer Use Agents

- **Key insight:** Computer use agents extend agents to interact with UIs through three components: action sequence generation, interface representation, action execution. Implicit vs explicit planning for action sequences.
- **Best practices:** Security sandboxing is critical when agents control UIs. Hierarchical agent composition: computer-use agents can be tools within larger multi-agent systems.
- **Relevant to Lyra §4.x:** §4.7 (Computer Use) — If Lyra needs UI automation capabilities.

---

## Chapter 6: Building Multi-Agent Workflows

- **Key insight:** Workflows as computational graphs (DAGs) with typed steps, conditional edges, parallel execution, streaming observability. Automatic checkpointing with structure-hash validation for safe resume after failures.
- **Best practices:**
  - Build phase (graph construction) vs Run phase (graph execution)
  - Type-safe steps with validated inputs/outputs
  - Fan-in detection: when multiple edges point to same step with "always" conditions, runner waits for all
  - Serialization enables pause/resume, debugging, and version-controlled workflow definitions
- **Relevant to Lyra §4.x:** §4.2 (Orchestration Workflows)

---

## Chapter 7: Building Autonomous Multi-Agent Orchestration

- **Key insight:** Every orchestration pattern follows the same core loop: select agent → prepare context → execute agent → update shared state → check termination. Pattern-specific logic only in select_next_agent() and prepare_context().
- **BaseOrchestrator:** Handles streaming, cancellation, state management; enforces unique agent names, max_iterations safety limit
- **RoundRobinOrchestrator:** Fixed-order turn-taking, simple but effective for structured collaboration
- **AIOrchestrator:** LLM dynamically selects next speaker based on conversation context and agent capabilities
- **PlanBasedOrchestrator:** LLM-generated execution plans with step evaluation, retry with enhanced instructions on failure (max_step_retries), replanning on insufficient progress — built-in metacognition
- **Termination System:** Composable conditions using | operator (OR semantics). Types: MaxMessageTermination, TextMentionTermination, TokenUsageTermination, TimeoutTermination, CompositeTermination.
- **Relevant to Lyra §4.x:** §4.2 (Orchestration), §4.2 (Plan-Based) — The orchestrator loop pattern is the foundation for Lyra's autonomous coordination.

---

## Chapter 8: Building Modern Web Experiences for Agent Applications

- **Key insight:** Two-component architecture: backend (FastAPI + Server-Sent Events) + frontend (vanilla JS/React). SSE preferred over WebSockets for stateless, horizontally-scalable deployments.
- **Best practices:** Streaming events from backend to frontend for real-time observability; cancellation token connected to UI stop buttons; agent state serialized as Pydantic models for stateless resume.
- **Relevant to Lyra §4.x:** §4.9 (UX/Web Interface)

---

## Chapter 9: Multi-Agent Frameworks

- **Key insight:** Ten core capabilities distinguish effective frameworks: intuitive developer experience, async-first architecture, observability, state management, declarative configuration, guardrails/middleware, pattern support, evaluation integration, human-in-the-loop, and protocol support.
- **Anti-pattern:** Choosing a framework before understanding the fundamentals. "Understanding these core concepts prepares you to work effectively with any multi-agent framework."
- **Relevant to Lyra §4.x:** Framework evaluation criteria for Lyra's technology selection.

---

## Chapter 10: Evaluating Multi-Agent Systems

- **Key insight:** Evaluation-driven development — define success measures before building. Whether evaluating model, agent, or multi-agent workflow, you're fundamentally evaluating a trajectory (sequence of reasoning messages + actions). This unified view enables consistent evaluation across complexity levels.
- **5-Step Evaluation Planning Framework (BEFORE writing agent code):**
  1. Define success criteria (accuracy, speed, UX)
  2. Create task suite (representative tasks, edge cases)
  3. Choose metrics and judges (deterministic vs LLM judges)
  4. Establish baselines (direct model calls, single agents, previous versions)
  5. Plan iteration workflow (when to run evals, regression detection)
- **Answer Extraction Challenge:** Which message contains the actual answer? Strategies: last_non_empty (default), last_assistant, all_assistant. Critical for reliable evaluation.
- **Trajectory Representation (picoagents):** RunTrajectory = task + messages + success + error + usage + metadata. Works for single model calls through complex workflows.
- **Numeric Metrics vs LLM Judges:**
  - Prefer deterministic when: ground truth available, measurable property (test coverage, error rates), consistency critical, cost-sensitive
  - Prefer LLM judges when: nuanced reasoning needed, multiple valid solutions, subjective assessment, unstructured/multimodal output
  - Use both strategically: filter with cheap metrics first, expensive LLM evaluation for remaining
- **Real Evaluation Results (GPT-4.1-mini):**
  - Simple-Reasoning: Direct-Model 9.7/10, Multi-Agent-AI 9.3/10 (multi-agent provides no benefit, slight degradation)
  - Tool-Heavy: Direct-Model 6.8/10, Multi-Agent-AI 9.2/10 (43x more tokens but justified)
  - Podcast Research: Direct-Model 3.2/10 vs tool-enabled agents 9.0/10
  - Token efficiency: Direct-Model ~355 tokens/task, Multi-Agent-AI ~15,343 tokens/task (43x increase)
- **Critical Evaluation Debugging Issues Found:**
  - Verbosity Penalty: Judge penalized multi-agent transparency as verbosity (scores improved from 6.82→9.30 after adding custom instructions to not penalize collaboration visibility)
  - Dimension Normalization: CompositeJudge weights must normalize per-dimension, not globally
- **Contamination Challenge:** Public benchmarks ≠ your task. Build domain-specific evaluation suites.
- **Related Benchmarks:** GAIA (466 questions, 92% human vs 15% GPT-4+plugins), SWE-bench (2,294 real GitHub issues, 1.96% solved by Claude 2), GPQA (448 graduate-level "Google-proof" questions)
- **Relevant to Lyra §4.x:** §4.10 (Evaluation Harness) — This chapter is the blueprint for Lyra's evaluation infrastructure.

---

## Chapter 11: Optimizing Multi-Agent Systems

- **Key insight:** Two-level optimization: agent-system parameters (high leverage, start here) vs model-level parameters (resource-intensive, pursue last). Optimization loop: Measure → Analyze → Modify → Validate → Repeat.
- **Agent-System Parameters (optimize first, highest ROI):**
  1. Instructions — most direct impact. Expand iteratively based on evaluation failures. "Great agent prompts can be pages long!"
  2. Tools — reliability over breadth. 10 excellent tools > 50 mediocre ones.
  3. Memory — evaluate whether memory improves success rate enough to justify overhead
  4. Model selection — frontier models (GPT-5, Claude 4.5) for capability, route simple queries to small models
  5. Orchestration patterns — start with simplest that could work
  6. Termination conditions — align with agent capabilities; data-driven threshold calibration
  7. Human delegation — risk-based approval strategies
- **Model-Level Optimization (pursue last, only when):**
  1. Residual domain-specific failures that agent-system tuning can't fix
  2. Cost/latency/privacy requirements demand smaller models
  - Strategies: Routing (simple→small, complex→large: 90% performance at 15% cost), Distillation, Cascading
  - SFT/RL finetuning: 7B finetuned on your task can match 70B generalist for your domain
- **10 Failure Modes (checklist for diagnosis):**
  1. Lack detailed instructions → Expand iteratively based on failure analysis
  2. Using small models without optimization → Strategic model selection, routing, distillation
  3. Instructions don't match LLM → Model-specific instruction registry; A/B test when switching models
  4. Lack good tools → Invest in curated, battle-tested tool catalog; reliability over breadth
  5. Don't know when to stop → Align termination with agent capabilities; use TaskStatusTool
  6. Wrong multi-agent pattern → Start with simplest; use evaluation to validate complexity
  7. Aren't learning (no memory) → Strategic memory: not every agent needs memory
  8. Lack metacognition → PlanBasedOrchestrator provides built-in metacognition (plan→execute→evaluate→replan)
  9. Don't have evals → Minimum viable: 5-10 tasks, ExactMatchJudge, EvalRunner
  10. Don't know when to delegate to humans → Risk-based approval: low-risk auto-execute, high-risk ALWAYS require
- **Bonus #11: You Probably Don't Need a Multi-Agent System.** Decision checklist: decomposability, diverse expertise, extensive context, adaptive requirements all needed.
- **Relevant to Lyra §4.x:** §4.11 (Optimization), §4.10 (Evaluation) — The failure mode checklist is directly applicable to Lyra's reliability roadmap.

---

## Chapter 12: Protocols for Distributed Agents

- **Key insight:** MCP (Model Context Protocol) standardizes tool/context integration; A2A (Agent-to-Agent Protocol) standardizes cross-organizational agent collaboration. Most use cases are well-served by single-process before needing distribution.
- **MCP Three-Layer Architecture:** Hosts (user-facing apps like Claude Desktop, Cursor) → Clients (1:1 protocol connections) → Servers (expose tools, resources, prompts)
- **MCP Advanced Features (agentic capabilities):** Elicitation (servers request user input mid-execution), Sampling (servers ask client's LLM for completions), Resumable streams (survive disconnections), Progress notifications (real-time status), Resource links (durable result references)
- **MCP Transports:** stdio (local, subprocess) vs Streamable HTTP (remote, distributed)
- **A2A Core:** Agent Card (capability metadata for discovery), Task abstraction (long-running, resumable), Events (Streaming + progress)
- **Security for Distributed Agents:** Authentication (OAuth 2.0), Authorization (fine-grained scopes), Data isolation, Input validation at protocol boundaries
- **Relevant to Lyra §4.x:** §4.5 (Protocols/Integration) — MCP is the primary protocol for Lyra's tool integration.

---

## Chapter 13: Ethics and Responsible AI for Multi-Agent Systems

- **Key insight:** Agentic ethics differ fundamentally from traditional AI ethics across 4 dimensions: Controllability (behavioral uncertainty, alignment faking), Action Capability (multi-step autonomy), Domain Scope (broad generalist agents), Verification (emergent system behavior)
- **Critical Security Principle — The Rule of Two (Meta AI 2025):** Until robust defenses against prompt injection exist, agents should satisfy no more than two of: [A] Process untrustworthy inputs, [B] Access sensitive systems, [C] Change state/communicate externally. If all three needed → human-in-the-loop required.
- **The Sycophant Problem:** OpenAI GPT-4o update rolled back after model became excessively agreeable. Root cause: naive incorporation of user feedback signals into optimization. Product signals ≠ quality signals.
- **Exponential Task Completion Growth:** 50% time horizon doubling every 7 months since 2019. GPT-2 (2019): ~2-3 seconds → GPT-5 (2025): >2 hours (3,000x improvement in 6 years).
- **Agentic Noise:** AI agents accelerate one side of platforms while the other remains human-paced, breaking equilibrium. Even symmetric acceleration may not improve welfare.
- **Distributed Responsibility:** "Many hands problem" intensifies with autonomous agents — outcomes cannot be traced to specific decisions.
- **Security Paradigm Shift:** Traditional LLM jailbreak → harmful text. Agent jailbreak → deleted files, exfiltrated data, unauthorized API calls, manipulated production systems. Risk scales with action capability.
- **Defense Layers:** Middleware (input filtering, tool authorization, output validation) + Strong containerization + Credential isolation + Least privilege tooling
- **Ethical Deployment Checklist:** Bias assessment, Transparency disclosure, Privacy protection, Human oversight mechanisms, Security hardening, Accountability assignment
- **Relevant to Lyra §4.x:** §4.8 (Safety), §4.13 (Ethics) — The Rule of Two is directly applicable to Lyra's safety architecture.

---

## Chapter 14: Answering Business Questions from Unstructured Data

- **Key insight:** Complete case study using the Y Combinator startup analysis (5,622 companies). 4-stage workflow: Data Loading with Intelligent Caching → Cost-Effective Pre-Filtering → Structured LLM Analysis → Insight Generation.
- **Results pattern:** Real-time data shows 47.7% of YC 2025 startups building AI agents (6.1% in 2020).
- **Relevant to Lyra §4.x:** §4.13 (Case Studies/Applications)

---

## Chapter 15: Building a Software Engineering Agent

- **Key insight:** Three pillars: Tools (file operations, code execution, search), Prompts (detailed, multi-page instructions with examples), Memory (cross-session learning via agent-managed memory). Complete example: code review agent.
- **Best practices:**
  - Provide detailed, comprehensive prompts (pages long) with concrete examples
  - Implement memory for pattern learning across sessions
  - Sandbox code execution; validate tool outputs
  - Test each component independently before integration
- **Relevant to Lyra §4.x:** §4.13 (SWE Agent use case), §4.4 (Code tools)
