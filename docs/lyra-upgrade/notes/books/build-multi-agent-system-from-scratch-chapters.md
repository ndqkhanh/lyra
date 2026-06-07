# Build a Multi-Agent System (from Scratch) — Chapter Notes
**Author:** Val Andrei Fajardo, PhD | **Year:** 2026 (MEAP v4) | **Core Thesis:** Deep understanding of LLM agents and multi-agent systems comes from building them from scratch. By implementing your own framework — including the processing loop, tool interfaces, MCP integration, and Agent Skills support — you gain the internal knowledge needed to work effectively with any production framework or build specialized solutions.

---

## Chapter 1: What are LLM Agents and Multi-Agent Systems?

- **Key insight:** LLMs are text generators that can *express intent* to act, but cannot *execute* actions. An LLM agent is the orchestration system that bridges this gap — it turns the LLM's intentions (tool-call requests, plans) into actions by executing tools and feeding results back into the LLM's context.

- **Best practices:**
  - Define LLM agents as systems comprised of a backbone LLM + tools that act autonomously on tool-call requests.
  - Use **planning** capability (initial and adaptive) as core to the processing loop. The LLM creates an initial plan, then course-corrects at each sub-step based on previous results.
  - Use **tool calling** as the primary mechanism for LLM agents to interact with the world. Tools must be equipped with textual descriptions (name, description, JSON Schema of parameters).
  - Capture **trajectories/rollouts** for debugging and evaluating LLM agents even if not surfaced to end users.
  - Reasoning LLMs (fine-tuned for chain-of-thought) make better backbone LLMs.
  - Decompose complex tasks into sub-steps executed within a processing loop — each step plans → acts → observes.

- **Anti-patterns:**
  - Treating LLMs as agents (they are not — they can only generate text).
  - Relying on unstructured natural language for tool-call requests (use structured formats like JSON; always prefer provider SDK native tool-calling APIs).
  - Setting an incorrect initial plan without adaptive course-correction in subsequent sub-steps (leads to catastrophic task failure or timeout).
  - Confusing LLM agents with reinforcement learning (RL) agents — LLM agents don't learn optimal policies; they re-purpose pre-trained text generation.

- **Design patterns introduced:**
  - **Processing loop** (sub-step execution: plan → tool calls → synthesize → repeat).
  - **Human-in-the-loop** (pause for human validation at critical decision points).
  - **Memory** (store/load past trajectories and tool call results for future tasks).
  - **Multi-Agent Systems (MAS)** (specialized agents divide complex tasks).

- **Protocols/Standards:**
  - MCP (Anthropic): Standard for connecting LLM agents to third-party tools/resources.
  - Agent Skills (Anthropic-originated, now open): Standard for reusable, documented procedural workflows.
  - A2A (Google): Standard for agent-to-agent communication in MAS.

- **Relevant to Lyra §4.x:** This chapter grounds the entire Lyra architecture debate. The distinction between intent (LLM) and action (agent) is foundational. The processing loop mental model maps directly to Lyra's step-execution pipeline (§4.2).

---

## Chapter 2: Working with Tools

- **Key insight:** Standardizing tool interfaces through a base class (BaseTool/AsyncBaseTool) and associated data structures (ToolCall, ToolCallResult) enables reliable LLM-tool interaction regardless of tool functionality diversity. The JSON Schema specification for tool parameters maximizes compatibility across LLM providers.

- **Best practices:**
  - Define a **single, uniform interface** for all tools — name, description, parameters_json_schema, and __call__(). All LLM providers expect these same pieces of information.
  - Use **JSON Schema** for tool parameter descriptions — it is the industry standard supported by all major LLM providers.
  - Separate synchronous tools (BaseTool) from async tools (AsyncBaseTool) — async tools for external API calls avoid blocking the processing loop.
  - Wrap Python functions into tools automatically via SimpleFunctionTool (or PydanticFunctionTool for stronger validation) to reduce boilerplate.
  - Validate tool-call arguments against the parameters JSON Schema before executing tool logic. Return ToolCallResult with `error=True` on validation or execution failure — never let errors propagate silently.
  - Use `jsonschema` library for validation in SimpleFunctionTool; use Pydantic's `model_validate()` for PydanticFunctionTool (more robust).
  - Implement both `ToolCall` (input: id_, tool_name, arguments) and `ToolCallResult` (output: tool_call_id, content, error) as Pydantic BaseModels for strong typing.
  - Organize multiple tools in a **registry** with name-based dispatch for easy lookup during task execution.

- **Anti-patterns:**
  - Having each tool use a different invocation interface — this makes LLM tool-call generation error-prone.
  - Manually writing JSON Schemas for every tool — automate via function signature introspection or Pydantic's `model_json_schema()`.
  - Swallowing tool execution errors — always return them as structured ToolCallResult with error=True so the LLM can adapt.
  - Using unstructured text extraction for tool-call requests from LLM output — brittle and unreliable at scale.

- **Relevant to Lyra §4.x:** Lyra's tool/plugin interface should follow this exact pattern. Each Lyra tool should conform to a standardized BasePlugin interface with JSON Schema parameter definitions. The async/sync distinction is critical for Lyra tools making external API calls (web search, code execution, etc.) (§4.7).

---

## Chapter 3: Working with LLMs

- **Key insight:** A standard BaseLLM interface abstracts away provider-specific API differences and supports four essential interaction modes: complete(), chat(), continue_chat_with_tool_results(), and structured_output(). The async-first design (all methods are async) enables concurrent execution.

- **Best practices:**
  - Define BaseLLM with four modes: (1) simple text completion, (2) conversational chat with tool support, (3) tool-result continuation, (4) structured output.
  - Make BaseLLM **async-first** — all methods are async to enable non-blocking concurrent operations.
  - Use `continue_chat_with_tool_results()` as an explicit convenience method for submitting tool results back — clearer than manual ChatMessage construction.
  - Bind structured output to Pydantic BaseModel via generics (TypeVar bound=BaseModel) — this enables type-safe, validated structured outputs.
  - **Chat history management:** Return `(user_message, llm_response)` tuple pairs from chat() and `(tool_messages, llm_response)` from continue_chat_with_tool_results(). Append both to running history for multi-turn stateful conversations.
  - Standardize message roles: SYSTEM (context/instructions), USER (user input), ASSISTANT (LLM response), TOOL (tool results).
  - For tool calling within chat: the ASSISTANT message carries `tool_calls` (list of ToolCall), user extracts and executes them, then submits results via TOOL-role messages.
  - Build provider integrations by converting between framework data types and provider SDK types (e.g., ChatMessage ↔ Ollama message, BaseTool ↔ Ollama tool).

- **Anti-patterns:**
  - Relying on unstructured text outputs for downstream processing — use structured_output() with a Pydantic model schema instead.
  - Trying to implement tool-calling via structured_output() — use native tool-calling APIs from LLM providers; they have optimized prompt templates.
  - Blocking the processing loop with synchronous LLM calls — always use async.

- **Relevant to Lyra §4.x:** Lyra's LLM provider abstraction should follow this exact four-method interface. The chat() → tool extraction → continue pattern is fundamental to Lyra's processing loop (§4.3). Structured output support maps to Lyra's need for generating validated JSON configurations, planning steps, and evaluation results (§4.5).

---

## Chapter 4: The LLM Agent Class

- **Key insight:** The LLMAgent class orchestrates task execution through a **processing loop** of discrete sub-steps. Each sub-step involves: (a) getting the next step decision from the LLM, (b) executing that step (which may include tool calls), and (c) repeating until completion or max_steps. The run() method returns an awaitable Future (TaskHandler) for flexible concurrency.

- **Best practices:**
  - **Task → TaskResult model:** Tasks hold an instruction string + unique ID; TaskResults hold the completed content + task_id linkage.
  - **TaskHandler as asyncio.Future:** The processing loop runs as a background asyncio.Task. Users `await` the returned TaskHandler. This enables fire-and-forget patterns, concurrent task execution, and cancellation.
  - **Sub-step data structures:** TaskStep (instruction + plan), TaskStepResult (result + tool_calls), NextStepDecision (continue with new instruction OR complete).
  - **Prompt templates (LLMAgentTemplates):** Standardize all LLM interactions — system message, next-step decision, run-step — using format strings. Templates inject task instruction, tool list, chat history, and previous results into context.
  - **The processing loop pattern:** (1) get_next_step(system_msg, chat_history, tools) → NextStepDecision, (2) if next_step: run_step(next_step) → TaskStepResult, (3) append to chat_history, (4) repeat. Exit when decision says "done" or max_steps reached.
  - **Tool registry:** Maintain a dict[str, Tool] for O(1) lookup during tool-call execution. Populate from tools list at init.
  - **Rollout capture:** Store the complete trajectory (steps, plans, tool calls, results) for debugging and evaluation. Imperative for observability.
  - **Logging:** Use structured logging (console or file) to observe the processing loop in real-time — tool calls, step transitions, completions.

- **Anti-patterns:**
  - Letting LLMs rely on parametric knowledge instead of tools — use obfuscated tool names (e.g., "next_number" instead of "hailstone") in tests to verify actual tool usage.
  - Blocking the event loop — use asyncio.create_task() for background processing.
  - Not capturing rollouts/trajectories — essential for debugging why tasks fail.
  - Exceeding context window with long chat histories — manage context budget.
  - Having no max_steps limit — infinite loops on unresolvable tasks.

- **Relevant to Lyra §4.2:** This is the most directly applicable chapter. Lyra's processing loop should use TaskHandler-like async Future pattern. The get_next_step() / run_step() decomposition maps cleanly to Lyra's planning → acting → observing cycle. Rollout capture is essential for Lyra's observability dashboards.

---

## Chapter 5: MCP Tools

- **Key insight:** MCP (Model Context Protocol) standardizes how LLM agents connect to external tools via a server-client architecture. The key abstractions are MCPToolProvider (manages server connection + tool discovery) and MCPTool (client-side representation, subclass of AsyncBaseTool). The LLMAgentBuilder pattern simplifies constructing agents with MCP tools.

- **Best practices:**
  - **MCP architecture:** MCP clients connect to MCP servers via sessions. Tool-call requests are forwarded to the server for execution; results are returned to the client.
  - **Two transport types:** stdio (local servers, launched as subprocesses) and streamable HTTP (remote servers). Use `StdioServerParameters` for stdio; URL + headers for HTTP.
  - **MCPToolProvider responsibilities:** (1) establish + maintain connection via asyncio primitives (Event, Task), (2) discover server-side tools via `list_tools()`, (3) create MCPTool objects for each discovered tool.
  - **Tool discovery is one-time** — happen at agent construction time, unlike Skills which are re-discovered on each run.
  - **MCPTool is AsyncBaseTool** — the `__call__()` method forwards the tool-call request to the provider's session using `call_tool()`. All MCP interactions are async.
  - Use **LLMAgentBuilder** (builder pattern) to eliminate manual tool discovery boilerplate. Builder validates attributes, discovers all MCP tools, and constructs the agent in one `.build()` call.
  - **Session lifecycle:** Create session in background task, signal readiness via `asyncio.Event`, cache session, provide timeout protection, clean shutdown via close().
  - **Naming convention:** Prefix MCP tool names with provider name (e.g., `mcp__hailstone__hailstone_step_fn`) to avoid collisions.
  - **Tool annotations:** Preserve MCP-specific metadata (readOnlyHint, destructiveHint, etc.) from the server.

- **Anti-patterns:**
  - Blocking during tool discovery — always async.
  - Not handling session reconnection — sessions can drop; design for resilience.
  - Hardcoding MCP tool names — auto-discover them from the server.
  - Leaking MCP server sessions — always implement close() and clean up on shutdown.

- **Relevant to Lyra §4.7:** Lyra's plugin system should adopt MCP as the primary third-party integration standard. Every Lyra agent should be an MCP host capable of connecting to multiple MCP servers simultaneously. The builder pattern (LyraAgentBuilder) simplifies construction. The provider/tool separation is a clean design that Lyra should adopt.

---

## Chapter 6: Skills

- **Key insight:** Skills are documented procedural workflows (SKILL.md files) that teach an LLM agent *how* to perform specific tasks. While tools provide discrete *functionality*, skills define the *process* for completing a task. The Agent Skills open standard enables an ecosystem of shareable, framework-agnostic skills.

- **Best practices:**
  - **Skills vs. Tools:** Tools = discrete functionality (what); Skills = documented workflow (how). Skills reference tools within their procedural descriptions.
  - **SKILL.md structure:** YAML frontmatter (name + description required; license, compatibility, metadata, allowed-tools optional) followed by Markdown procedural workflow body.
  - **Skill bundles:** Directory named after the skill containing SKILL.md + optional `scripts/`, `references/`, `assets/` subdirectories. Keep resources only one level deep from SKILL.md.
  - **Three-step skill lifecycle:**
    1. **Discovery:** Scan `.agents/skills/` (project scope) and `$HOME/.agents/skills/` (user scope). Trigger on every task run via TaskHandler construction. Project scope overrides user scope on name collisions.
    2. **Activation:** Use a dedicated `UseSkillTool` that loads the full SKILL.md body + resource listing into context. Implemented as a BaseTool so activation appears in the rollout.
    3. **Execution:** LLM follows the procedural workflow, referencing tools and resources as instructed.
  - **Progressive disclosure:** At discovery phase, disclose only name + description (via `<available_skills>` XML block in system prompt). On activation, disclose full body + resources. This conserves context window.
  - **User-explicit activation:** Provide `run_with_skill()` method that bypasses LLM decision-making and forces a specific skill. Use case: skills marked as `explicit_only` (not listed in catalog).
  - **UseSkillTool implementation:** Accepts skill name parameter as enum (values = visible skill names). Validates skill exists. Returns formatted XML with skill body, resources, and directory path.
  - **Validation on discovery:** Validate SKILL.md frontmatter (non-empty name/description), warn on cosmetic issues (missing optional fields), skip fatally malformed bundles.
  - **Skills marketplaces:** Skills.sh, SkillsMP.com, ClawHub.ai, Pickaxe.co, Salesforce Agentforce, Microsoft Copilot Agent Store.

- **Anti-patterns:**
  - Disclosing full skill bodies at discovery time (floods context window).
  - Letting LLM use skills without activation (incomplete context leads to wrong execution).
  - Not re-discovering skills on each task run (stale skill content if user edits between runs).
  - Hardcoding skill activation logic in the processing loop instead of using a dedicated tool (UseSkillTool pattern is cleaner and traceable in rollouts).
  - Mixing user-scoped and project-scoped skills without clear precedence rules.

- **Relevant to Lyra §4.6:** This is a critical chapter for Lyra. The Agent Skills standard is the "layer above tools" that Lyra needs. Lyra should implement skill discovery (`.lyra/skills/` or use the cross-client `.agents/skills/`), UseSkillTool activation, and user-explicit invocation. This enables Lyra to consume the growing skills ecosystem and define its own reusable workflows (e.g., deep-research skill, code-review skill).

---

## Chapter 7: Memory (NOT YET AVAILABLE IN MEAP v4)

- **Key insight:** This chapter is listed in the Table of Contents but content is not published in the current MEAP edition. Based on Chapter 1's preview, it will cover memory modules for storing/loading past task trajectories and tool-call results into context during future tasks.

- **Anticipated topics (from Ch1 preview):**
  - Saving sub-step results and tool-call results to persistent memory.
  - Loading relevant memory into context at task execution start.
  - Design decisions: when/what to save/load.
  - Avoiding redundant tool calls across task executions.

- **Relevant to Lyra §4.3:** Lyra's memory system should learn from this chapter's patterns once available. The trajectory storage pattern maps to Lyra's conversation history and cross-session memory.

---

## Chapter 8: Human in the Loop (NOT YET AVAILABLE IN MEAP v4)

- **Key insight:** This chapter is listed in the Table of Contents but content is not published in the current MEAP edition. Based on Chapter 1's preview, it will implement human verification at sub-step boundaries within the processing loop.

- **Anticipated topics (from Ch1 preview):**
  - Pausing the processing loop for human input at each sub-step.
  - Human operators validating plans before execution.
  - Human review of final task results with retry-on-failure.
  - Trade-off: error reduction vs. increased execution time.

- **Relevant to Lyra §4.8:** Critical for Lyra's safety gating. Human approval at sensitive tool calls (code execution, file writes, API mutations) implements the safety boundary described in Lyra's safety plan (§17).

---

## Chapter 9: Multi-Agent Systems with A2A (NOT YET AVAILABLE IN MEAP v4)

- **Key insight:** This chapter is listed in the Table of Contents but content is not published in the current MEAP edition. It will cover assembling multiple LLM agents into multi-agent systems using Google's Agent2Agent (A2A) protocol.

- **Anticipated topics (from Ch1 preview):**
  - A2A protocol for standardized agent-to-agent communication.
  - Framework-agnostic agent collaboration (agents built with different frameworks).
  - Multi-agent coordination logic.
  - Failure modes of MAS and potential remedies.

- **Relevant to Lyra §4.9:** The holy grail of Lyra's architecture. A2A enables the "debate" pattern, specialized sub-agents, and orchestrated workflows. Lyra should build A2A-native from the ground up.

---

## Appendix A: Implementing the PydanticFunctionTool

- **Key insight:** PydanticFunctionTool provides more robust JSON Schema generation and validation than SimpleFunctionTool by leveraging Pydantic's built-in capabilities (`model_json_schema()`, `model_validate()`). The trade-off is a slightly different usage pattern — function parameters must be a Pydantic BaseModel.

- **Best practices:**
  - Define a `PydanticFunction` Protocol for type-checking functions with params BaseModel.
  - Use Pydantic's `model_json_schema()` for JSON Schema generation — more robust than manual introspection.
  - Use Pydantic's `model_validate()` for validation — handles type coercion, nested models, custom validators.
  - Prefer PydanticFunctionTool over SimpleFunctionTool when complex parameter types (nested objects, enums, discriminated unions) are needed.

- **Relevant to Lyra §4.7:** For complex Lyra tools with rich parameter structures, the Pydantic approach is superior. Lyra should support both SimpleFunctionTool-style (quick prototyping) and PydanticFunctionTool-style (production tools) patterns.

---

## Overall Framework Architecture

The book builds `llm-agents-from-scratch` with this module structure:

```
base/          → BaseTool, AsyncBaseTool, BaseLLM
tools/         → SimpleFunctionTool, AsyncSimpleFunctionTool, PydanticFunctionTool
tools/mcp/     → MCPTool, MCPToolProvider
llms/ollama/   → OllamaLLM (provider integration)
agent/         → LLMAgent, TaskHandler, LLMAgentBuilder
agent/templates/ → LLMAgentTemplates (prompt templates)
skills/        → Skill, UseSkillTool, discover_skills()
data_structures/ → ToolCall, ToolCallResult, ChatMessage, ChatRole, CompleteResult, Task, TaskResult, TaskStep, TaskStepResult, NextStepDecision, SkillFrontmatter, SkillScope
errors/        → Custom error types
logger/        → Structured logging utilities
```

**Key architectural patterns:**
1. **Base class → Implementation hierarchy:** Every major component has an abstract base class defining the interface, with concrete implementations adding provider-specific logic.
2. **Builder pattern:** LLMAgentBuilder separates construction complexity (tool discovery, validation) from the LLMAgent class.
3. **Future-based async orchestration:** TaskHandler extends asyncio.Future, enabling concurrent task execution and graceful cancellation.
4. **Provider abstraction:** Data type conversion utilities bridge framework types ↔ provider SDK types.
5. **Template-driven prompts:** All LLM interactions use format templates for consistency and testability.
