# Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems — Chapter Notes
**Author:** Antonio Gulli (Google OCTO) | **Year:** 2025 | **Publisher:** Springer
**Core Thesis:** Building intelligent agentic systems requires proven, reusable design patterns — just as software engineering adopted design patterns. The book presents 21 patterns across four parts (foundational patterns, memory/adaptation, reliability, advanced orchestration), providing a comprehensive "canvas" for developers to construct systems that can reason, plan, use tools, collaborate, and self-improve. The central metaphor is the "agentic canvas" — the underlying infrastructure that provides environment and tools for agents to operate.

**Target Audience:** Software engineers and AI practitioners building production AI agents. Code examples in LangChain/LangGraph, Google ADK, and CrewAI.

---

## What Makes an AI System an "Agent"? (Introduction)
- **Key insight:** The book defines four levels of agent complexity: Level 0 (Core Reasoning Engine — LLM alone, no tools), Level 1 (Connected Problem-Solver — uses external tools), Level 2 (Strategic Problem-Solver — multi-step planning, context engineering, self-improvement). This maturity model is the backbone of the entire book.
- **Key concept: Context Engineering** — the strategic discipline of selecting, packaging, and managing the most relevant information for each step. "To achieve maximum accuracy from an AI, it must be given a short, focused, and powerful context." This is more systematic than prompt engineering alone and is central to Lyra's context management.
- **Agent definition:** An AI agent perceives its environment, makes decisions, and executes actions to achieve goals autonomously. Five-step loop: Get the Mission → Scan the Scene → Think It Through → Take Action → Learn and Get Better.
- **Market context:** $2B+ raised by AI agent startups by end of 2024, market valued at $5.2B, projected $200B by 2034.
- **Relevant to Lyra §2.1:** The agent maturity model directly mirrors Lyra's architectural ambition — the transition from reactive tool-user to strategic self-improving agent.

---

## Chapter 1: Prompt Chaining
- **Key insight:** Complex tasks overwhelm single-prompt LLMs — the pattern decomposes problems into sequential sub-tasks with structured inter-step data transfer. Also known as the Pipeline pattern.
- **Best practices:** Always use structured output (JSON) between steps to ensure machine-readable data handoff. Assign distinct roles to the model at each stage (e.g., "Market Analyst" → "Trade Analyst" → "Documentation Writer"). Add deterministic logic between LLM calls for validation and conditional branching.
- **Anti-patterns:** Monolithic prompts that cause instruction neglect (model overlooks parts), contextual drift (loses track), error propagation (early errors amplify), and hallucination from cognitive overload.
- **Framework support:** LangChain Expression Language (LCEL) `|` operator; LangGraph for stateful chains; Google ADK SequentialAgent.
- **Relevant to Lyra §4.1:** Lyra's multi-step research pipeline (search → read → synthesize → verify) is essentially prompt chaining with tool calls between steps.

---

## Chapter 2: Routing
- **Key insight:** Real agents must arbitrate between multiple potential actions based on context. Four routing mechanisms: LLM-based (prompt classifier), embedding-based (semantic similarity), rule-based (deterministic), and ML-classifier-based (trained discriminative model).
- **Best practices:** Use `RunnableBranch` in LangChain for conditional execution. In Google ADK, the Auto-Flow mechanism with `sub_agents` enables LLM-driven delegation automatically. For high-throughput systems, use rule-based or embedding routing — cheaper and faster than LLM classification.
- **Anti-patterns:** Building monolithic agents that handle every type of query. Without routing, agents become rigid scripts incapable of adapting to input variability.
- **Framework patterns:** LangGraph's state-based graph nodes with conditional edges; Google ADK's Coordinator agent with sub_agents and Auto-Flow.
- **Relevant to Lyra §4.5:** Lyra's intent classification and tool-selection routing (which tool/agent handles which user request).

---

## Chapter 3: Parallelization
- **Key insight:** Independent sub-tasks should execute concurrently to reduce latency, especially for I/O-bound operations (API calls, database queries, web searches). The pattern is fundamental for scalable agents.
- **Best practices:** Use `RunnableParallel` in LangChain (LCEL), `ParallelAgent` in Google ADK, and `asyncio.gather()` for proper async execution. Identify dependency-free tasks before parallelizing — the synthesis step is typically sequential (waits for all parallel branches).
- **Anti-patterns:** Sequential execution of I/O-bound tasks when parallel would work — adds unnecessary latency. Over-parallelizing with shared mutable state causing race conditions.
- **Warning:** "The adoption of a concurrent or parallel architecture introduces substantial complexity and cost, impacting key development phases such as design, debugging, and system logging."
- **Relevant to Lyra §4.3:** Multi-source parallel web search in Lyra's research mode; parallel validation checks.

---

## Chapter 4: Reflection
- **Key insight:** The Producer-Critic (Generator-Reviewer) separation is a powerful implementation — having a dedicated Critic agent prevents the cognitive bias of self-review. The pattern introduces a feedback loop for iterative self-improvement.
- **Best practices:** Use separate system prompts (distinct personas) for Producer and Critic roles. Set a stopping condition (e.g., `CODE_IS_PERFECT` signal) and max_iterations to prevent infinite loops. For high-objectivity tasks, always use a separate agent rather than self-reflection.
- **Anti-patterns:** Single-agent self-reflection producing biased evaluation. Ignoring the trade-offs: "higher costs and latency, memory-intensive, context window expands with each iteration."
- **Critical design decision:** "Does the 'how' need to be discovered, or is it already known?" — dynamic planning vs. fixed workflow.
- **Relevant to Lyra §4.4:** Lyra's self-critique, verification loops, and quality gates. The Produce→Critique→Refine loop is the core engine behind Lyra's research reports.

---

## Chapter 5: Tool Use (Function Calling)
- **Key insight:** Tool Use bridges LLM reasoning to external action. The six-step process: Tool Definition → LLM Decision → Function Call Generation → Tool Execution → Observation/Result → LLM Processing. Tool calling (broader concept) encompasses function calling + API endpoints + sub-agent delegation.
- **Best practices:** Define tools with clear descriptions and typed parameters (function signatures become LLM-visible schemas). Wrap fallible operations in try/except to return structured error messages the LLM can reason about. Use `@tool` decorators in LangChain, `FunctionTool` in CrewAI, pre-built tools in ADK (Google Search, Code Execution, Vertex AI Search).
- **Key distinction:** Vertex AI Extensions (auto-executed by Vertex AI) vs. Function Calls (require manual execution by client). Extensions provide enterprise-grade security.
- **Anti-patterns:** Tools returning unstructured natural language instead of typed structured data. Tools with poorly scoped descriptions that confuse the LLM's selection logic.
- **Relevant to Lyra §4.2:** Lyra's entire tool ecosystem — web search, file I/O, code execution, API calls.

---

## Chapter 6: Planning
- **Key insight:** Planning agents discover the "how" for a given "what." The critical design decision: use dynamic planning when the solution path is unknown, use fixed workflows when it is known. Adaptability is the hallmark — plans are starting points, not rigid scripts.
- **Best practices:** Present plans to users for review/modification before execution (Google DeepResearch pattern). Use separate agents for plan creation and plan execution. Integrate real-time feedback for plan adaptation when obstacles arise.
- **Notable examples:** Google Gemini DeepResearch (multi-step agentic pipeline, iterative search-and-analysis, asynchronous processing, structured multi-page reports with citations); OpenAI Deep Research API (`o3-deep-research`, programmatic access with exposed intermediate steps).
- **Anti-patterns:** Using dynamic planning when the problem is well-understood — introduces unnecessary uncertainty. Failing to constrain the agent when predictability matters.
- **Relevant to Lyra §4.6:** Lyra's research planning — decomposing complex queries into sub-questions, then executing a research plan.

---

## Chapter 7: Multi-Agent Collaboration
- **Key insight:** Six collaboration models form a spectrum: Single Agent → Network (decentralized peer-to-peer) → Supervisor (central hub) → Supervisor-as-Tool → Hierarchical (multi-layered) → Custom (hybrid). The choice of model critically depends on task complexity, desired autonomy, robustness needs, and communication overhead tolerance.
- **Best practices:** Combine sequential handoffs (for dependent steps) with parallel processing (for independent work) and debate/consensus (for high-stakes decisions). Use `AgentTool` (ADK) to wrap one agent as a tool callable by another. The Critic-Reviewer multi-agent pattern (creators + reviewers) is particularly effective for code generation, research writing, and ethical alignment.
- **Key framework primitives:** Google ADK's `SequentialAgent`, `ParallelAgent`, `LoopAgent`, `AgentTool`. CrewAI's role-based agents with `Process.sequential`.
- **Anti-patterns:** Over-engineering with too many agents when a single agent suffices. Failing to define clear communication protocols between agents. Supervisor bottleneck in hierarchical systems.
- **Relevant to Lyra §4.7:** Lyra's multi-agent architecture — Researcher, Planner, Executor, Critic/Verifier agents collaborating.

---

## Chapter 8: Memory Management
- **Key insight:** A dual-component memory system (short-term + long-term) is the standard solution. Three types of long-term memory: Semantic (facts/preferences), Episodic (past experiences/examples), Procedural (rules/instructions that can self-modify via reflection).
- **Best practices for Google ADK:** Use `Session` (chat thread), `State` (temporary key-value scratchpad with `user:`, `app:`, `temp:` prefixes), and `MemoryService` (searchable long-term knowledge). NEVER modify `session.state` directly — always use `EventActions.state_delta` or `output_key`.
- **Best practices for LangGraph:** Short-term = thread-scoped state via checkpointer; Long-term = cross-session JSON documents in `BaseStore` with namespace + key organization.
- **Anti-patterns:** Direct mutation of session state bypassing event processing. Relying solely on the LLM's context window for memory (ephemeral, costly, inefficient for repeated lookups).
- **Memory Bank:** Vertex AI managed service that uses Gemini to asynchronously extract key facts from conversations, store persistently, and retrieve via full recall or embedding similarity search.
- **Relevant to Lyra §3.2:** Lyra's conversation memory, state management, and persistent knowledge across sessions.

---

## Chapter 9: Learning and Adaptation
- **Key insight:** The chapter distinguishes six learning paradigms: Reinforcement Learning (PPO), Supervised, Unsupervised, Few-Shot/Zero-Shot (LLM-based), Online, and Memory-Based. Two landmark systems are presented as case studies.
- **SICA (Self-Improving Coding Agent):** An agent that modifies its own source code based on past benchmark performance. Key architectural features: modular sub-agents (coding, problem-solving, reasoning), an async overseer to detect loops/stagnation, Docker containerization for security, structured context window organization. Evolved from basic file overwriting → Smart Editor → Diff-Enhanced Smart Editor → AST-based code navigation.
- **AlphaEvolve:** Google's LLM + evolutionary algorithm system. Concrete results: 0.7% reduction in global compute usage, 23% speed improvement in Gemini kernel, 32.5% GPU instruction optimization for FlashAttention, new matrix multiplication algorithms.
- **DPO vs PPO:** DPO skips the separate reward model entirely, directly optimizing on human preference data — simpler, more stable.
- **Anti-patterns:** Expecting LLM agents to independently propose novel, innovative modifications during self-improvement — remains an open research challenge.
- **Relevant to Lyra §5.1:** Self-improvement mechanisms, learning from past interactions, adaptation of strategies.

---

## Chapter 10: Model Context Protocol (MCP)
- **Key insight:** MCP is a standardized client-server protocol (vs. proprietary function calling). Critical warning: "MCP is a contract for an agentic interface, and its effectiveness depends heavily on the design of the underlying APIs." Simply wrapping legacy APIs is suboptimal — agents need agent-friendly data formats (Markdown, not PDF), filtering, and sorting.
- **MCP vs. Function Calling:** Function calling = direct, proprietary, one-to-one, tightly coupled. MCP = open standard, client-server, dynamic discovery, reusable servers, federated ecosystem.
- **Security considerations:** Authentication, authorization, mTLS, network restrictions. The MCP standard must define error handling so the LLM can understand failures and try alternatives.
- **Transport:** Local = JSON-RPC over STDIO; Remote = Streamable HTTP + SSE.
- **FastMCP:** Python framework for rapid MCP server creation with decorator-based tool registration and automatic schema generation from type hints.
- **Relevant to Lyra §4.2:** Lyra's tool integration strategy — whether to use MCP as the standard for all tool connections.

---

## Chapter 11: Goal Setting and Monitoring
- **Key insight:** Agents need explicit goal states and continuous progress monitoring. The pattern involves defining objectives, decomposing into sub-goals, tracking progress metrics, and adapting when goals are at risk.
- **Best practices:** Use iterative generation-evaluation-refinement cycles. Define clear success criteria before execution. Monitor intermediate states, not just final output.
- **Relevant to Lyra §4.6:** How Lyra defines and tracks research objectives, adjusting plans when results are insufficient.

---

## Chapter 12: Exception Handling and Recovery
- **Key insight:** Three-phase pattern: Error Detection (validate tool outputs, API codes, timeouts, monitoring agents) → Error Handling (logging, retries with backoff, fallbacks, graceful degradation, notification) → Recovery (state rollback, diagnosis, self-correction, escalation).
- **Best practices:** Use `SequentialAgent` with primary_handler → fallback_handler → response_agent chain. Combine with Reflection: if initial attempt fails, analyze the failure and retry with a refined approach.
- **Anti-patterns:** Agents that crash silently. Missing timeout configurations. No fallback paths for tool failures.
- **Relevant to Lyra §3.3:** Lyra's error recovery, retry logic, and graceful degradation patterns.

---

## Chapter 13: Human-in-the-Loop (HITL)
- **Key insight:** HITL is not optional for high-stakes domains. Six aspects: Human Oversight, Intervention/Correction, Human Feedback for Learning, Decision Augmentation, Human-Agent Collaboration, Escalation Policies.
- **Critical caveats:** "Lack of scalability" — operators cannot manage millions of tasks, creating a fundamental accuracy-vs-volume trade-off. Effectiveness depends heavily on human operator expertise. Privacy concerns require anonymization before human review.
- **"Human-on-the-Loop" variant:** Humans define policy/rules; AI handles immediate execution within those bounds (e.g., trading rules, call routing policies).
- **Relevant to Lyra §3.4:** Lyra's escalation paths, user confirmation gates, and human approval for critical operations.

---

## Chapter 14: Knowledge Retrieval (RAG)
- **Key insight:** RAG grounds LLM responses in external, verifiable data, reducing hallucination risk. Core components: chunking, embeddings, vector databases, semantic search. The chapter also covers citation generation for trustworthiness.
- **Advanced techniques:** Hybrid search (vector + BM25 keyword). Query-dependent information extraction that goes beyond document retrieval to extract precise clauses/figures.
- **Relevant to Lyra §4.3:** Lyra's RAG pipeline for research — document ingestion, chunking, semantic retrieval, citation-backed synthesis.

---

## Chapter 15: Inter-Agent Communication (A2A)
- **Key insight:** Google's A2A is an open protocol for universal agent-to-agent communication across frameworks (LangGraph, CrewAI, ADK). Supported by Atlassian, Box, MongoDB, Salesforce, SAP, ServiceNow, and Microsoft.
- **Core concepts:** Agent Card (JSON identity/skills manifest), Agent Discovery (well-known URI, curated registries, direct configuration), Tasks (async units of work with state machine), Communication (JSON-RPC 2.0 over HTTP/S, contextId for session continuity).
- **Interaction mechanisms:** Synchronous request/response → Asynchronous polling → Streaming (SSE) → Push notifications (webhooks).
- **Relevant to Lyra §4.7:** How Lyra's agents communicate — A2A as potential standard vs. custom protocols.

---

## Chapter 16: Resource-Aware Optimization
- **Key insight:** Agents must dynamically choose between accuracy and cost. Pattern: simple/cheap model for routine queries, powerful/expensive model for complex analysis. Fallback mechanisms ensure graceful degradation when preferred models are unavailable.
- **Best practices:** Route based on query complexity (length, domain, required reasoning depth). Use prompt tuning and fine-tuning for the router itself. The travel planner example: Gemini Pro for planning, Gemini Flash for individual tool calls.
- **Relevant to Lyra §4.5:** Lyra's model routing strategy — Haiku for simple lookups, Sonnet for standard work, Opus for architecture/analysis.

---

## Chapter 17: Reasoning Techniques
- **Key insight:** Advanced reasoning goes beyond sequential operations by making internal reasoning explicit and allocating increased inference-time compute. Three core techniques form a progression.
- **Chain-of-Thought (CoT):** Step-by-step reasoning mimicking human thought. Transforms single-step problems into series of simpler steps. Can be prompted via few-shot examples or "think step by step" instruction. Increases transparency and auditability.
- **Tree-of-Thought (ToT):** Extends CoT by exploring multiple reasoning paths in a tree structure, enabling backtracking and comparison of alternatives.
- **Self-Correction:** Internal evaluation cycle within the reasoning process — identify gaps, inaccuracies, and refine before final output.
- **Relevant to Lyra §4.4:** Lyra's reasoning strategies for complex research queries, debate-based consensus, and multi-path exploration.

---

## Chapter 18: Guardrails/Safety Patterns
- **Key insight:** Guardrails are a layered defense, not a single solution. Seven layers: Input Validation/Sanitization → Behavioral Constraints (prompt-level) → Tool Use Restrictions → Output Filtering/Post-processing → External Moderation APIs → Monitoring/Observability → Human Oversight.
- **Best practices:** Use a fast, cost-effective model (Gemini Flash) as the guardrail enforcer. Implement structured output validation with Pydantic models. Define explicit safety policy directives (jailbreaking attempts, prohibited content, off-domain discussions, proprietary information). Log all guardrail decisions for auditing.
- **Key technique:** A dedicated Policy Enforcer agent screens all inputs before they reach the primary agent, with Pydantic-based output validation.
- **Anti-patterns:** No guardrails at all. Single-layer security. Using the same expensive model for guardrails as for primary tasks.
- **Relevant to Lyra §3.1:** Lyra's safety architecture — jailbreak prevention, content filtering, tool restriction policies.

---

## Chapter 19: Evaluation and Monitoring
- **Key insight:** Comprehensive agent evaluation requires multiple dimensions: accuracy (exact match → semantic similarity → LLM-as-a-Judge), latency, token usage/cost, helpfulness, safety compliance. The "AI Contract" concept is proposed for enterprise governance — a dynamic agreement codifying objectives, rules, and controls for AI-delegated tasks.
- **Best practices:** Use LLM-as-a-Judge for subjective qualities (helpfulness, tone, nuance). Log metrics to persistent storage (time-series DBs, observability platforms). Track token usage for cost optimization. Implement drift detection and anomaly detection. Use structured rubrics with multi-criteria scoring.
- **Anti-patterns:** Simple exact-match evaluation (fails on paraphrased correct answers). No monitoring beyond console output. Missing cost tracking.
- **Relevant to Lyra §5.3:** Lyra's evaluation framework — quality scoring, cost/latency tracking, drift detection, A/B testing of agent versions.

---

## Chapter 20: Prioritization
- **Key insight:** Agents must rank tasks by urgency, importance, dependencies, resource availability, and cost/benefit. Prioritization occurs at three levels: goal prioritization, sub-task prioritization, and action selection. Dynamic re-prioritization is essential for adaptability.
- **Best practices:** Define explicit criteria for task evaluation. Use LLM-based scoring for nuanced prioritization, rule-based for speed. Implement deadline-aware scheduling.
- **Relevant to Lyra §4.8:** Lyra's task queue management, resource allocation, and dynamic reprioritization of research sub-tasks.

---

## Chapter 21: Exploration and Discovery
- **Key insight:** Agents need mechanisms for open-ended exploration — discovering novel solutions, generating hypotheses, and navigating unknown problem spaces. This complements exploitation (executing known strategies).
- **Best practices:** Balance exploration vs. exploitation. Use evolutionary algorithms (as in AlphaEvolve) for discovering novel solutions. Maintain diversity in generated options.
- **Relevant to Lyra §5.2:** Lyra's research discovery mode — hypothesis generation, novel connection identification, creative exploration of the problem space.
