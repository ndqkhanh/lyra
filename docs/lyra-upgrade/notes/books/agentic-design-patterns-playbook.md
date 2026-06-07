# Agentic Design Patterns — Best Practices Playbook
**Source:** *Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems* by Antonio Gulli (2025, Springer)
**For:** Lyra agent harness engineering

---

## Practice 1: Adopt the Producer-Critic Model for Output Quality
- **What:** Separate content generation (Producer agent) from evaluation (Critic agent) with distinct system prompts and personas. The Critic evaluates against specific criteria — accuracy, coherence, completeness, style — and feeds structured feedback back to the Producer for refinement.
- **Why:** Self-review creates cognitive bias; a dedicated Critic with a fresh perspective finds errors the Producer misses. This two-agent model consistently produces higher-quality outputs than single-agent self-reflection. The Critic's feedback should be structured (e.g., bulleted issues or `CODE_IS_PERFECT` signal).
- **Lyra route:** §4.4 (Reflection/Verification). Lyra's Verify agent should be a separate agent from the Research/Write agent, with its own system prompt defining evaluation criteria. Implement a stopping condition (`QUALITY_MET` or `max_iterations`) to prevent infinite loops.
- **Source:** Chapter 4 (Reflection)

---

## Practice 2: Design for Dual Memory Architecture from Day One
- **What:** Implement separate short-term and long-term memory systems. Short-term = session-scoped state with prefix-keyed organization (`user:`, `app:`, `temp:`). Long-term = searchable external store (vector DB) with three categories: Semantic (facts/preferences as JSON documents), Episodic (past interaction sequences for few-shot prompting), Procedural (system instructions that can self-modify via reflection).
- **Why:** LLM context windows alone are ephemeral, costly to reprocess, and limited. A dual-memory architecture enables true persistence, cross-session personalization, and learning from past interactions. The key design rule: NEVER directly mutate state — always use event-driven state_delta or output_key mechanisms.
- **Lyra route:** §3.2 (Memory). Lyra needs: (a) Session state for conversation continuity, (b) User profile store for preferences/context, (c) Episodic store of past research queries and their outcomes, (d) Procedural memory that evolves Lyra's own instructions based on reflection.
- **Source:** Chapter 8 (Memory Management)

---

## Practice 3: Use Model Routing with Complexity-Based Tiering
- **What:** Implement a Router agent that classifies queries by complexity and routes to the appropriate model tier — cheap/fast model (Haiku/Flash) for simple lookups, mid-tier (Sonnet) for standard tasks, expensive/powerful (Opus/Pro) for complex reasoning. The routing decision should use multiple signals: query length, domain, required tools, historical performance on similar queries.
- **Why:** Dramatically reduces costs while maintaining quality. The book's travel planner example: Gemini Pro for the planning phase (complex reasoning), Gemini Flash for individual tool calls (simple API queries). A fallback mechanism ensures graceful degradation when primary models are unavailable or throttled.
- **Lyra route:** §4.5 (Router). Lyra's model routing should: (a) classify user intent + complexity before model selection, (b) use Haiku for simple retrieval/classification, Sonnet for standard research, Opus for deep analysis/architecture, (c) implement a fallback chain if the primary model is overloaded.
- **Source:** Chapter 2 (Routing), Chapter 16 (Resource-Aware Optimization)

---

## Practice 4: Apply Context Engineering — Not Just Prompt Engineering
- **What:** Context Engineering is the systematic discipline of building the complete informational environment for the model before token generation. It encompasses: system prompt, retrieved documents, tool outputs, user identity, interaction history, and environmental state. The core principle: quality of output depends more on context richness than model architecture.
- **Why:** Even advanced models underperform with limited context. Context Engineering treats what the agent knows, when it knows it, and how it uses that information as first-class concerns. This transforms stateless chatbots into situationally-aware systems.
- **Lyra route:** §4.1 (Context Assembly). Before every Lyra action, assemble: system instructions, relevant retrieved documents, tool results from previous steps, user profile, conversation history, and current task state. Keep context focused — curate, don't dump.
- **Source:** Chapter 1 (Prompt Chaining, Context Engineering section)

---

## Practice 5: Implement Structured Inter-Step Data Transfer
- **What:** Every step in a multi-step agent workflow should output structured data (JSON/Pydantic models), not free-form text. The next step receives this structured data as typed input. Use schema validation (Pydantic) at each step boundary to catch malformed outputs before they propagate.
- **Why:** Free-text handoffs are ambiguous and error-prone. Structured output ensures machine-readable, precisely parseable data that downstream steps can consume reliably. This is the foundation of robust multi-step agent pipelines.
- **Lyra route:** §4.1 (Pipeline). All Lyra workflow steps should define output schemas. For example: Search step → `{query, results: [{url, title, snippet}]}`, Read step → `{url, extracted_text, key_claims}`, Synthesize step → `{report, citations, confidence}`.
- **Source:** Chapter 1 (Prompt Chaining), Chapter 18 (Guardrails — Pydantic validation)

---

## Practice 6: Deploy Layered Guardrails, Not a Single Filter
- **What:** Implement seven guardrail layers: (1) Input Validation/Sanitization — screen prompts before processing, (2) Behavioral Constraints — system prompt rules, (3) Tool Use Restrictions — allowlist approach, (4) Output Filtering — post-process responses for policy violations, (5) External Moderation APIs — third-party content checks, (6) Monitoring/Observability — log all decisions for auditing, (7) Human Oversight — escalation paths for ambiguous cases. Use a fast/cheap model (Flash/Haiku) as the guardrail enforcer.
- **Why:** Single-layer security is brittle. A dedicated Policy Enforcer agent with structured output (Pydantic) that screens inputs for jailbreaking, prohibited content, off-domain discussions, and proprietary information before the primary agent processes them provides defense in depth.
- **Lyra route:** §3.1 (Safety). Lyra should: (a) run a lightweight Haiku-based Policy Enforcer before every Opus/Sonnet call, (b) use Pydantic models for compliance decisions with explicit `triggered_policies` tracking, (c) log all guardrail decisions for audit trails.
- **Source:** Chapter 18 (Guardrails/Safety Patterns)

---

## Practice 7: Choose the Right Multi-Agent Topology for Your Task
- **What:** Six collaboration models exist on a spectrum: Single Agent (simple tasks) → Network (resilient, decentralized) → Supervisor (clear authority, possible bottleneck) → Supervisor-as-Tool (guidance without rigid control) → Hierarchical (multi-layered for complex decomposition) → Custom (hybrid for specific needs). The choice depends on: task complexity, number of domains, desired robustness, communication overhead tolerance.
- **Why:** The wrong topology creates bottlenecks, excessive communication overhead, or insufficient coordination. The book's guidance: use Sequential for pipelines, Parallel for independent work, Hierarchical for complex decomposition, and Critic-Reviewer for quality-critical outputs.
- **Lyra route:** §4.7 (Multi-Agent). Lyra's architecture should use: Hierarchical topology — Orchestrator (plans, delegates) → Researcher/Executor agents (do work) → Verifier/Critic agent (reviews output). Use `AgentTool` pattern to wrap specialized agents as callable tools by higher-level agents.
- **Source:** Chapter 7 (Multi-Agent Collaboration)

---

## Practice 8: Build Exception Handling as a Three-Phase Pipeline
- **What:** Phase 1 — Error Detection: validate tool outputs, check API codes, set timeouts, deploy monitoring agents. Phase 2 — Error Handling: log errors, retry with exponential backoff, activate fallback handlers, degrade gracefully, notify operators. Phase 3 — Recovery: roll back state if needed, diagnose root cause, self-correct via plan adjustment, escalate to human if unrecoverable.
- **Why:** Real-world agents inevitably hit failures. The `primary_handler → fallback_handler → response_agent` pattern in ADK's SequentialAgent provides a clean implementation. Agents should never crash silently — they should always produce a meaningful response even in degraded mode.
- **Lyra route:** §3.3 (Reliability). Every Lyra tool call should be wrapped with: try/except → structured error → fallback path. Research failures should cascade: retry with different query → use cached results → report partial findings → escalate.
- **Source:** Chapter 12 (Exception Handling and Recovery)

---

## Practice 9: Evaluate Agents with LLM-as-a-Judge + Structured Rubrics
- **What:** Beyond exact-match accuracy, use an LLM-as-a-Judge with structured rubrics to evaluate subjective qualities: helpfulness, clarity, neutrality, completeness, audience appropriateness. Define multi-criteria scoring (1-5 scale) with explicit descriptors for each level. Require structured JSON output with: `overall_score`, `rationale`, `detailed_feedback` per criterion, `concerns`, `recommended_action`.
- **Why:** Exact-match evaluation fails on semantically equivalent but differently worded answers. LLM-as-a-Judge provides nuanced, human-like evaluation at scale. Track: accuracy, latency, token usage/cost, drift detection, anomaly detection.
- **Lyra route:** §5.3 (Evaluation). Lyra's eval framework should: (a) use a dedicated evaluator agent (separate from the research agent), (b) define structured rubrics for research quality, (c) track cost/latency/accuracy over time, (d) detect concept drift in research outputs.
- **Source:** Chapter 19 (Evaluation and Monitoring)

---

## Practice 10: Design Tools with Agent-Friendly APIs
- **What:** Tools should return typed structured data (not PDFs, not unstructured text), have clear parameter schemas with descriptions, support filtering/sorting for efficient access, and return agent-friendly formats (Markdown, not raw PDF). When wrapping legacy APIs via MCP, add deterministic features (filtering, pagination) that help the non-deterministic agent work efficiently.
- **Why:** "MCP can wrap an API whose input or output is still not inherently understandable by the agent. An API is only useful if its data format is agent-friendly, a guarantee that MCP itself does not enforce." The agent's effectiveness is gated by tool API quality.
- **Lyra route:** §4.2 (Tools). Every Lyra tool should: (a) return structured output with typed fields, (b) have clear docstrings the LLM can understand, (c) support filtering parameters, (d) return text-based formats (Markdown) rather than binary formats.
- **Source:** Chapter 10 (MCP — critical warning section)

---

## Practice 11: Use Chain-of-Thought with Explicit Stopping Criteria
- **What:** For complex tasks, instruct agents to think step-by-step with explicit thought stages (Analyze → Formulate → Simulate → Synthesize → Review). Each stage produces a visible intermediate output. The final Review stage acts as an internal self-correction gate before external output.
- **Why:** CoT significantly improves accuracy on multi-step reasoning tasks. Making reasoning explicit enables debugging, auditing, and trust. The five-stage structure provides a template that works across domains.
- **Lyra route:** §4.4 (Reasoning). Lyra's research queries should use structured CoT: (1) Analyze query requirements, (2) Formulate search strategy, (3) Simulate expected findings, (4) Synthesize from retrieved sources, (5) Review for accuracy/completeness before final output.
- **Source:** Chapter 17 (Reasoning Techniques)

---

## Practice 12: Define an Agent Card for Every Agent
- **What:** Each agent should have a standardized JSON manifest (Agent Card) describing: identity (name, description, version), capabilities (streaming, push notifications, state tracking), skills (with examples and tags), input/output modes, authentication requirements, endpoint URL.
- **Why:** Agent Cards enable dynamic discovery, automated composition, and cross-framework interoperability. They are the foundation of the A2A protocol, supported across LangChain, CrewAI, Google ADK, and Microsoft's ecosystem.
- **Lyra route:** §4.7 (Multi-Agent). Every Lyra sub-agent should have an Agent Card specifying its capabilities, tools, and expected input/output formats. This enables the Orchestrator to dynamically discover and route to appropriate agents.
- **Source:** Chapter 15 (Inter-Agent Communication A2A)

---

## Practice 13: Cache Model Responses with TTL-Based Invalidation
- **What:** For repeated or similar queries (especially in research loops), cache LLM responses with content-hash keys and TTL-based invalidation. Distinguish between: factual lookups (long TTL), real-time data queries (short/no TTL), and synthesized analysis (medium TTL).
- **Why:** Dramatically reduces costs for repeated operations (e.g., re-reading the same document, re-running the same search). The book emphasizes tracking token usage for cost optimization — caching is the most effective optimization.
- **Lyra route:** §4.3 (Research Pipeline). Lyra's research workflow should cache: search results (TTL: hours), document contents (TTL: days), LLM analysis of documents (TTL: days, invalidated on document change).
- **Source:** Chapter 16 (Resource-Aware Optimization), Chapter 19 (Token Usage Tracking)

---

## Practice 14: Implement Procedural Memory Self-Modification
- **What:** Store agent instructions in long-term memory (procedural memory). Periodically prompt the agent to reflect on its recent interactions and propose improved instructions. The updated instructions are stored and used in subsequent sessions. This is the LangGraph pattern: read instructions from store → use for current turn → periodically reflect and update.
- **Why:** Static system prompts degrade over time as tasks and environments evolve. Self-modifying procedural memory enables continuous improvement without manual prompt engineering. The book's pseudo-code demonstrates this with `store.get("agent_instructions")` → use → `store.put(updated_instructions)`.
- **Lyra route:** §5.1 (Self-Improvement). Lyra should: (a) store system instructions in long-term memory, (b) periodically reflect on interaction quality and propose instruction improvements, (c) A/B test new vs. old instructions using the evaluation framework.
- **Source:** Chapter 8 (Memory — Procedural Memory section), Chapter 9 (Learning and Adaptation — SICA case study)

---

## Practice 15: Standardize on MCP for Tool Ecosystem Interoperability
- **What:** Use the Model Context Protocol (MCP) as the standard for all tool connections, rather than proprietary function calling per provider. MCP provides: dynamic tool discovery, client-server architecture, reusable tool servers across frameworks, standardized error handling, and a federated ecosystem model.
- **Why:** MCP decouples tools from specific LLM providers and frameworks. Tools become reusable, composable building blocks. The book argues: for simple apps, function calling suffices; for complex, evolving agent systems, a universal standard like MCP is essential.
- **Lyra route:** §4.2 (Tools). Lyra's tool ecosystem should: (a) wrap all tools as MCP servers (use FastMCP for Python tools), (b) enable dynamic tool discovery by the Orchestrator, (c) support both local (STDIO) and remote (HTTP/SSE) tool servers, (d) implement tool_filter for security-scoped access.
- **Source:** Chapter 10 (Model Context Protocol)
