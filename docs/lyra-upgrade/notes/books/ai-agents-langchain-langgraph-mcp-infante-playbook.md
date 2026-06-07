# Best Practices Playbook
## From: AI Agents and Applications With LangChain, LangGraph, and MCP (Infante, 2026)

> **How to use this playbook:** Each practice is a concrete, actionable recommendation extracted from the book. The "Lyra route" field maps it to a specific Lyra upgrade workstream.

---

## Practice 1: Use Explicit State Graphs for Agent Workflows

**What:** Model every agent workflow as an explicit LangGraph `StateGraph` with typed state (`TypedDict`), named nodes (functions), and explicit edges (transitions). State accumulates via annotated reducers (e.g., `operator.add` for messages). Use conditional edges for LLM-driven routing decisions; use static edges for deterministic paths.

**Why:** Graph-based state machines provide rehydration, debugging, checkpointing, and human-in-the-loop capabilities that ad-hoc agent loops do not. Without explicit state, recovering from failures, branching conversations, or inspecting intermediate decisions is impossible. The graph structure also serves as living documentation of the agent's control flow.

**Lyra route:** §4.5 (Router) — implement graph-based workflow routing; §4.26 (Harness Engineering) — adopt StateGraph as the core orchestration primitive; §4.16 (Reliability) — enable state rehydration from checkpoints.

**Source:** Chapter 5 (Agentic Workflows with LangGraph), pp. 103–117; Chapter 12 (Multi-agent systems), pp. 293–307.

---

## Practice 2: Implement Layered Guardrails at Router, Agent, Pre-Model, and Post-Model Levels

**What:** Deploy guardrails at four insertion points: (1) router-level for fast domain relevance rejection, (2) agent-level for sub-domain scope enforcement (more restrictive than router), (3) pre-model hooks to intercept bad inputs before LLM invocation, (4) post-model hooks to validate outputs before user delivery. Each guardrail uses structured output (Pydantic model) for consistent classification results.

**Why:** A single guardrail layer creates a single point of failure. Router-level checks catch broad out-of-scope queries cheaply. Agent-level checks enforce specific capability boundaries (e.g., "only Cornwall, not all of UK"). Pre-model hooks prevent wasted LLM calls on invalid inputs. Post-model hooks catch hallucinations, biased language, leaked PII, and formatting errors that slip through input-side checks. Layered defense is the security principle applied to agent behavior.

**Lyra route:** §4.17 (Safety) — multi-layer safety architecture; §4.5 (Router) — router-level domain guardrails; §4.7 (Plugins) — tool-level action authorization; §4.16 (Reliability) — post-model output validation.

**Source:** Chapter 14, §14.2 (Guardrails), pp. 337–345.

---

## Practice 3: Use LangGraph Checkpoints for Short-Term Conversational Memory

**What:** Persist agent state at every graph node execution using a checkpointer. Assign a unique thread ID (UUID) per user session. Pass the thread config to every `invoke()` call. The checkpointer automatically saves snapshots after each super-step and rehydrates state on the next turn. Use `InMemorySaver` for development, `PostgresSaver` for production.

**Why:** Without checkpointing, each user turn is stateless — the agent cannot resolve anaphoric references ("same town," "that hotel"), handle follow-up questions, or recover from interruptions. Checkpoints also enable workflow pause/resume for human-in-the-loop, failure recovery from the last successful step, and conversation branching ("what if I chose option B?"). This is the foundation for any stateful agent experience.

**Lyra route:** §4.2 (Memory) — session-level short-term memory architecture; §4.3 (Context) — conversation history management; §4.16 (Reliability) — failure recovery via checkpoint rehydration.

**Source:** Chapter 14, §14.1 (Memory), pp. 328–337.

---

## Practice 4: Adopt the Supervisor Pattern for Multi-Agent Orchestration

**What:** Use a supervisor agent (a more powerful reasoning model like GPT-5) that orchestrates specialist agents as sub-tools. Each specialist agent is wrapped as a tool the supervisor can invoke via `transfer_to_<agent_name>`. The supervisor decomposes complex multi-part queries, invokes agents in sequence (potentially multiple times each), collects intermediate results, and synthesizes a final answer. Use `create_supervisor(agents=[...], model=...)` from `langgraph-supervisor`.

**Why:** The simpler router pattern only handles single-intent queries (one agent per turn). Real-world user requests often span multiple domains ("find a nice seaside town with good weather AND check hotel availability there"). The Supervisor pattern handles these multi-step, cross-domain queries by granting the orchestrator visibility into all agent capabilities and letting it sequence their invocation dynamically. The Supervisor is the architectural leap from single-purpose to general-purpose agent systems.

**Lyra route:** §4.26 (Harness Engineering) — supervisor as orchestration layer; §4.5 (Router) — upgrade from router to supervisor; §4.7 (Plugins) — agent-as-tool wrapping pattern.

**Source:** Chapter 12, §12.3 (Handling multi-agent requests with a Supervisor component), pp. 302–307.

---

## Practice 5: Standardize Tool Integration via MCP Protocol

**What:** Expose external capabilities (APIs, databases, file systems) through MCP servers using FastMCP 2. Define tools with the `@mcp.tool` decorator, automatic schema generation from Python type hints, and Streamable HTTP transport for production. Connect agents to MCP servers via `MultiServerMCPClient` which aggregates tools from multiple servers into a unified tool list. Combine MCP-provided tools with local tools seamlessly — they use identical interfaces.

**Why:** Without MCP, every team wraps every API as a custom tool, duplicating effort across the ecosystem. MCP shifts integration work to the source — providers expose tools once, all agents consume them. The growing MCP ecosystem (16,000+ community servers) means agents can increasingly draw on shared, pre-built tools rather than custom wrappers. MCP tools are protocol-identical to local tools in LangChain/LangGraph, requiring zero code changes to integrate.

**Lyra route:** §4.7 (Plugins) — MCP as the standardized plugin protocol; §4.3 (Context) — external data sources via MCP servers; §4.26 (Harness Engineering) — tool ecosystem strategy.

**Source:** Chapter 13 (Building and Consuming MCP Servers), pp. 308–326.

---

## Practice 6: Use Structured Output (Pydantic) for All Agent Decision Points

**What:** Every LLM decision point — router classification, guardrail decisions, tool argument schemas, agent output formats — should use Pydantic models with `with_structured_output()`. This eliminates manual string parsing, ensures consistent formats, and enables automated validation. Key decision models: `GuardrailDecision(is_in_scope: bool, reason: str)`, `AgentTypeOutput(agent: AgentType)`, and typed tool return schemas.

**Why:** String parsing is the #1 source of brittle, hard-to-debug agent failures. When the LLM returns a slightly different format than expected, string-based extraction silently breaks. Pydantic structured output guarantees the LLM produces valid, typed responses that flow through the system without parsing errors. This is especially critical in multi-agent systems where agents pass data to each other — unstructured inter-agent communication dramatically increases error rates.

**Lyra route:** §4.9 (Commands) — structured command output schemas; §4.5 (Router) — typed routing decisions; §4.7 (Plugins) — typed tool input/output; §4.17 (Safety) — structured guardrail classifications.

**Source:** Chapter 12, pp. 298–299 (AgentTypeOutput); Chapter 14, pp. 338–339 (GuardrailDecision); Throughout Part 5.

---

## Practice 7: Obsess Over Tool Descriptions — They Are the Agent's "API Documentation"

**What:** Every tool registered with an agent must have a precise, scoped description that tells the LLM exactly when and how to use it. Include: what the tool does, what inputs it requires, what it returns, and critically, when NOT to use it. Use the `@tool(description="...")` decorator or the `description` parameter. System prompts should additionally constrain tool usage with explicit rules ("Only use the weather tool when the user explicitly asks about weather").

**Why:** The LLM decides which tool to call based entirely on tool descriptions and system prompts. Vague descriptions cause the LLM to call the wrong tool, call a tool when it should not, or fail to call a tool when it should. Every misrouted tool call wastes tokens, increases latency, and degrades user trust. Precise tool descriptions are the single highest-leverage investment in agent reliability.

**Lyra route:** §4.7 (Plugins) — tool description standards; §4.9 (Commands) — command/function documentation quality; §4.5 (Router) — tool selection accuracy.

**Source:** Chapter 11, pp. 283–287 (improving tool usage with system guidance); Chapter 12, pp. 293–297 (tool descriptions for multi-agent systems).

---

## Practice 8: Build Evaluation Datasets Continuously from Production Traces

**What:** Maintain a labeled evaluation dataset of 100+ query-answer pairs with correct/incorrect annotations. Seed it from initial test cases, then continuously expand it from production LangSmith traces. Include edge cases, adversarial examples (prompt injections, out-of-scope requests), and multi-step queries. Run the agent against this dataset on every prompt change, tool update, or model version change. Track accuracy, precision, recall, and F1 scores across runs.

**Why:** Evaluation is the most overlooked step in agent development — and the one that causes the most production incidents. Without systematic evaluation, prompt changes, tool updates, or model swaps can silently degrade agent performance. A labeled dataset provides objective regression testing: you know immediately whether a change improved or degraded behavior. Continuous evaluation catches issues before users do.

**Lyra route:** §4.16 (Reliability) — evaluation framework and regression testing; §4.26 (Harness Engineering) — continuous evaluation pipeline; §4.17 (Safety) — safety evaluation datasets.

**Source:** Chapter 14, §14.3.4 (Evaluation of AI agents and applications), pp. 347–348; Chapter 14 Summary, pp. 349–350.

---

## Practice 9: Prefer the Prebuilt ReAct Agent, Customize Only When Necessary

**What:** Start agent development with LangGraph's `create_react_agent(model=..., tools=..., state_schema=..., prompt=...)`. This provides a battle-tested ReAct loop (LLM reasons -> selects tool -> tool executes -> LLM receives result -> repeats until final answer). Only customize the graph (custom nodes, custom routing) when the prebuilt agent's behavior is insufficient. When customizing, use `pre_model_hook` and `post_model_hook` before modifying the core agent loop.

**Why:** The ReAct pattern is the most well-understood and debugged agent architecture. The prebuilt implementation handles edge cases (no tool calls, malformed tool calls, tool call loops) that are tedious and error-prone to reimplement. Customizing prematurely adds complexity without commensurate benefit. The hook system provides extension points that cover most customization needs without touching the core loop.

**Lyra route:** §4.7 (Plugins) — agent initialization pattern; §4.5 (Router) — starting with prebuilt before custom routing; §4.16 (Reliability) — relying on tested agent loops.

**Source:** Chapter 11, §11.9 (Using prebuilt components for rapid development), pp. 288–291.

---

## Practice 10: Separate Local and Remote Tools Cleanly, Combine at the Agent Level

**What:** Implement remote capabilities as MCP servers (standalone processes). Implement local capabilities as standard LangChain tools or local functions. At the agent level, combine them into a single tool list: `tools = [local_tool_1, local_tool_2, *mcp_tools]`. The agent should not need to know or care whether a tool is local or remote — they use identical calling conventions. Use `MultiServerMCPClient` to aggregate MCP tools from multiple servers.

**Why:** This separation of concerns means: (1) remote tools can be developed, tested, and deployed independently using MCP Inspector, (2) local tools remain simple and fast without network overhead, (3) the agent gets a unified tool interface regardless of tool location, and (4) tool providers can update their MCP servers without requiring agent code changes. This is the architectural pattern that makes MCP so powerful.

**Lyra route:** §4.7 (Plugins) — plugin architecture with local + remote tools; §4.3 (Context) — external context sourcing; §4.26 (Harness Engineering) — tool aggregation strategy.

**Source:** Chapter 13, §13.4 (Integrating the Weather MCP tool into an agent), pp. 322–326; Listing 13.3 (Combining local and remote tools), p. 324.

---

## Practice 11: Implement Human-in-the-Loop for High-Stakes Agent Decisions

**What:** Pause agent workflows at decision points where the action has significant real-world impact (booking confirmations, financial transactions, data deletion, ambiguous safety-critical queries). Use LangGraph checkpoints to save state at the pause point, notify a human reviewer with context, and resume execution after approval or rejection. Log all human decisions to build a training dataset for improving automated guardrail thresholds over time.

**Why:** Even well-designed agents encounter situations where automated handling is insufficient — ambiguous queries, incomplete data, or high-stakes actions. Human-in-the-loop prevents reputational damage from agent errors, provides real-world feedback for system improvement, and satisfies compliance requirements for regulated domains. Over time, human review patterns inform better guardrails, reducing the escalation rate.

**Lyra route:** §4.17 (Safety) — human approval for sensitive operations; §4.16 (Reliability) — pause/resume via checkpoints; §4.26 (Harness Engineering) — human-in-the-loop workflow integration.

**Source:** Chapter 14, §14.3.2 (Human-in-the-loop), pp. 346–347; Chapter 14 Summary, pp. 349–350.

---

## Practice 12: Monitor Production Agent Metrics Continuously

**What:** Track these metrics for every production agent deployment: error rate (failed tool calls, LLM refusals), P95 latency (end-to-end response time), tokens per query (cost proxy), tool success rate (tool calls that returned valid results vs errors), and guardrail trigger rate (queries blocked/rejected). Set up automated alerts for anomaly detection. Use staged rollout (canary testing on 5-10% of traffic) before full deployment of any change.

**Why:** Agents are non-deterministic systems — their behavior can drift due to model updates, tool API changes, or shifting user query patterns. Without continuous monitoring, degradation goes undetected until users complain. Staged rollout catches issues before they affect all users. Token-per-query tracking directly ties agent behavior to cost, enabling optimization decisions based on real data.

**Lyra route:** §4.16 (Reliability) — monitoring and alerting; §4.26 (Harness Engineering) — production observability and staged deployment; §4.17 (Safety) — guardrail trigger monitoring.

**Source:** Chapter 14 Summary, pp. 349–350 (Production monitoring metrics, staged rollout); Chapter 7 (LangSmith observability), pp. 143–169.

---

## Practice 13: Design for Two Modes — Workflow (Deterministic) and Agent (LLM-Driven)

**What:** Architect agent systems with two distinct execution modes. Use deterministic workflows (static graph edges) for paths where the sequence of operations is known in advance. Use agent nodes (LLM-driven conditional routing) only where runtime reasoning is required to decide the next step. Compose them in the same graph: static edges for known flows, conditional edges for decision points. This minimizes LLM calls and maximizes predictability.

**Why:** Every unnecessary LLM call adds latency, cost, and non-determinism. Deterministic workflows are fast, cheap, and predictable. Agent nodes are flexible but expensive. The optimal architecture uses workflows for the "scaffolding" (data loading, formatting, known sequences) and agents only for the "reasoning" (which tool to call, how to interpret results, when to escalate). This is the core design philosophy of LangGraph and a direct lesson from the book's progression from chains to graphs to agents.

**Lyra route:** §4.5 (Router) — hybrid workflow + agent routing; §4.26 (Harness Engineering) — graph architecture design; §4.16 (Reliability) — deterministic paths for critical operations.

**Source:** Chapter 5, pp. 103–107 (workflows vs agents); Chapter 12, pp. 293–302 (router-based workflow + agent composition); Throughout Part 5.
