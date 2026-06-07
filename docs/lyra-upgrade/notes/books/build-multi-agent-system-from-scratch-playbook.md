# Build a Multi-Agent System (from Scratch) — Best Practices Playbook
**Source:** *Build a Multi-Agent System (from Scratch) v4 MEAP* by Val Andrei Fajardo, PhD (2026)
**Scope:** 12 actionable practices extracted across chapters 1–6 (chapters 7–9 not yet published in MEAP v4)

---

## Practice 1: Standardize All Tool Interfaces via a Base Class

- **What:** Every tool the agent uses MUST conform to a single abstract base class interface providing: `name` (str), `description` (str), `parameters_json_schema` (dict), and `__call__(ToolCall) -> ToolCallResult`. No exceptions.

- **Why:** Without standardization, the LLM cannot reliably generate tool-call requests. Different invocation interfaces cause LLM confusion, parameter mismatches, and execution failures. A single interface also enables a unified tool registry for O(1) dispatch.

- **Lyra route:** §4.7 (Plugins) — Lyra's plugin interface should define exactly this four-attribute contract. Every Lyra plugin (web search, code interpreter, file system, etc.) should be a subclass of `LyraBasePlugin`.

- **Source:** Chapter 2, Section 2.1

---

## Practice 2: Use JSON Schema as the Universal Tool Parameter Format

- **What:** Tool parameters must be described using JSON Schema (type: object, properties, required). Use either automated introspection (`function_signature_to_json_schema()`) or Pydantic's `model_json_schema()` — never write schemas manually.

- **Why:** JSON Schema is the industry standard supported by all major LLM providers (OpenAI, Anthropic, Google, Ollama). It enables LLMs to generate valid parameter values reliably. Manual schema writing is error-prone and creates inconsistency between the schema and actual function signatures.

- **Lyra route:** §4.7 (Plugins) — every Lyra tool definition should auto-generate JSON Schema from type annotations. For complex tools, require a Pydantic BaseModel params class.

- **Source:** Chapter 2, Sections 2.1-2.3

---

## Practice 3: Separate Synchronous and Asynchronous Tools

- **What:** Provide two base classes: `BaseTool` (sync) and `AsyncBaseTool` (async). Async tools should be used for I/O-bound operations (API calls, file reads, web requests). Sync tools for CPU-bound operations (math, data transformation).

- **Why:** Synchronous execution blocks the processing loop while waiting on external resources. Async tools enable concurrent execution and significantly better resource utilization. The distinction also self-documents which tools may be slow.

- **Lyra route:** §4.2 (Processing Loop) + §4.7 (Plugins) — Lyra's processing loop should be async-first. Tools making external API calls (web search, database queries) MUST be async.

- **Source:** Chapter 2, Section 2.1.3; Chapter 3, Section 3.1

---

## Practice 4: Implement Tool-Call Results as Structured Error-Carrying Types

- **What:** Every tool execution MUST return a `ToolCallResult` object with three fields: `tool_call_id` (links back to request), `content` (result data), and `error` (bool). On validation or execution failure, return `error=True` with error details in content — NEVER raise unhandled exceptions.

- **Why:** The LLM needs structured information about tool outcomes to adapt its plan. Silent failures cause cascading errors in the processing loop. Returning errors as structured results lets the LLM course-correct (retry, use different tool, ask user for help).

- **Lyra route:** §4.2 (Processing Loop) + §16 (Reliability) — all Lyra tool results must follow this error contract. The processing loop should inspect `error` flags and adjust behavior accordingly.

- **Source:** Chapter 2, Section 2.1.1

---

## Practice 5: Design the Processing Loop as an Async Future

- **What:** The agent's `run()` method should return an awaitable `TaskHandler` (subclass of `asyncio.Future`) rather than blocking synchronously. The processing loop executes as a background `asyncio.Task`. Users `await` the returned handler.

- **Why:** This pattern enables (a) fire-and-forget task submission, (b) concurrent execution of multiple tasks, (c) graceful cancellation via Future cancellation, (d) result retrieval when needed. It is the most flexible concurrency model for agent systems.

- **Lyra route:** §4.2 (Processing Loop) — this should be the cornerstone of Lyra's async architecture. Enables Lyra to run multiple tasks in parallel, cancel stuck executions, and support streaming task progress.

- **Source:** Chapter 4, Section 4.2

---

## Practice 6: Execute Tasks Through Discrete Sub-Steps with Planning + Tool-Calling

- **What:** Break task execution into iterated sub-steps. Each sub-step: (1) LLM synthesizes previous results and plans the next step, (2) LLM may make tool calls, (3) tool results feed back. Continue until the LLM decides the task is complete or `max_steps` is reached. Use `NextStepDecision` to formalize the continue-vs-complete choice.

- **Why:** Complex tasks cannot be completed in a single LLM call. Sub-stepping enables adaptive planning (course-correction when tools return unexpected results) and prevents infinite loops. The `max_steps` limit bounds worst-case cost and latency.

- **Lyra route:** §4.2 (Processing Loop) — directly applicable. Lyra should decompose every task into plan→act→observe sub-steps with explicit continue/complete decisions.

- **Source:** Chapter 4, Section 4.2; Chapter 1, Section 1.3

---

## Practice 7: Use Prompt Templates for All LLM Interactions

- **What:** Define all LLM prompts through templates (Python format strings) — system message, next-step decision, sub-step execution, skill catalog. Templates take placeholder variables (task instruction, tool list, chat history, previous results) and produce the final prompt.

- **Why:** Templates ensure consistency across all LLM interactions. They separate prompt engineering from orchestration logic. They make prompts testable (unit test the template output). They enable A/B testing of different prompt strategies.

- **Lyra route:** §4.3 (Context/LLM) — Lyra should maintain a `LyraAgentTemplates` structure with templates for all interaction modes. Enables Lyra to swap prompt strategies without changing orchestration code.

- **Source:** Chapter 4, Section 4.1.2

---

## Practice 8: Capture Complete Rollouts/Trajectories

- **What:** Record the full execution trace of every task — every sub-step's plan, every tool call request, every tool call result, and every LLM response. Store the trajectory in a structured format (list of step records).

- **Why:** Trajectories are essential for (a) debugging why a task failed, (b) evaluating agent performance, (c) auditing agent behavior, (d) fine-tuning backbone LLMs on successful trajectories, and (e) building memory systems that learn from past executions.

- **Lyra route:** §4.5 (Evaluation/Observability) — trajectory capture should be built into Lyra's processing loop from day one. Store trajectories in the observability pipeline for replay and analysis.

- **Source:** Chapter 4, Section 4.3; Chapter 1, Section 1.3

---

## Practice 9: Integrate MCP as the Standard for Third-Party Tool Access

- **What:** Make every Lyra agent an MCP host. Use `MCPToolProvider` to manage connections to MCP servers (both stdio and streamable HTTP). Auto-discover tools from connected servers. Use the builder pattern to simplify MCP agent construction.

- **Why:** MCP is the emerging industry standard for AI-tool integration. It enables Lyra to tap into the vast and growing ecosystem of MCP-compatible tools without writing custom integrations. MCP also standardizes tool discovery, execution forwarding, and session management.

- **Lyra route:** §4.7 (Plugins) — Lyra should ship with MCP host capabilities. Accept MCP server configurations in Lyra's config. Enable connecting to multiple MCP servers simultaneously. The builder pattern (`LyraAgentBuilder`) should handle MCP tool discovery.

- **Source:** Chapter 5

---

## Practice 10: Implement Skills as Reusable Procedural Workflows

- **What:** Support the Agent Skills open standard. Discover skills from `.agents/skills/` (project + user scope) at every task run. Disclose skills progressively — names + descriptions first, full body only on activation. Use a dedicated `UseSkillTool` for activation. Support user-explicit skill invocation.

- **Why:** Skills are the layer above tools — they teach the agent *how* to perform multi-step tasks. The open standard enables an ecosystem of shareable, framework-agnostic skills. Progressive disclosure conserves context window budget. User-explicit activation provides deterministic control over agent behavior.

- **Lyra route:** §4.6 (Skills/Router) — this is essential for Lyra. Lyra should integrate the Agent Skills standard to consume community skills and define its own (deep-research, code-review, verification). Skill activation via a dedicated tool provides clean rollout traces.

- **Source:** Chapter 6

---

## Practice 11: Build Async-First, Provider-Agnostic LLM Integration

- **What:** Define a `BaseLLM` abstract class with four async methods: `complete()`, `chat()`, `continue_chat_with_tool_results()`, and `structured_output()`. Implement provider-specific subclasses (OllamaLLM, AnthropicLLM, etc.) that convert between framework data types and provider SDK types. Never expose provider-specific types to application code.

- **Why:** Async-first design enables non-blocking, concurrent LLM interactions. Provider-agnostic interface lets Lyra swap LLM backends without changing any orchestration code. Type conversion utilities centralize integration complexity.

- **Lyra route:** §4.3 (Context/LLM) — Lyra should implement this exact four-method BaseLLM interface. Add provider implementations for Anthropic, OpenAI, Google, and Ollama. This enables model-agnostic Lyra operation.

- **Source:** Chapter 3

---

## Practice 12: Validate and Handle Errors at Every Boundary

- **What:** (1) Validate tool-call arguments against JSON Schema before execution. (2) Validate structured LLM outputs against Pydantic models before processing. (3) Validate MCP server connections with timeouts and readiness signals. (4) Validate skill bundles on discovery (required fields, naming conventions). Return structured error types at every boundary — never propagate raw exceptions.

- **Why:** LLMs are probabilistic systems that will produce malformed outputs. External systems (MCP servers, APIs) are unreliable. Without systematic validation at every boundary, these failures cascade silently. Structured errors enable the processing loop to adapt and the human operator to understand what went wrong.

- **Lyra route:** §16 (Reliability) + §17 (Safety) — validation at boundaries is the foundation of Lyra's reliability. Implement the "never propagate raw exceptions" rule throughout Lyra's codebase.

- **Source:** Chapter 2 (tool validation), Chapter 3 (structured output validation), Chapter 5 (MCP session validation), Chapter 6 (skill bundle validation)

---

## Practice Summary Matrix

| # | Practice | Difficulty | Impact | Ch. | Lyra § |
|---|----------|-----------|--------|-----|--------|
| 1 | Standardize tool interfaces via base class | Low | High | 2 | §4.7 |
| 2 | JSON Schema for all tool parameters | Low | High | 2 | §4.7 |
| 3 | Separate sync/async tool classes | Low | Medium | 2 | §4.2 |
| 4 | Structured error-carrying tool results | Medium | High | 2 | §16 |
| 5 | Async Future processing loop return | Medium | High | 4 | §4.2 |
| 6 | Sub-step execution with planning + tools | High | Critical | 4 | §4.2 |
| 7 | Template-driven prompts | Low | Medium | 4 | §4.3 |
| 8 | Capture complete rollouts | Medium | High | 4 | §4.5 |
| 9 | MCP as standard third-party tool access | Medium | High | 5 | §4.7 |
| 10 | Skills as reusable procedural workflows | High | High | 6 | §4.6 |
| 11 | Async-first provider-agnostic LLM | Medium | Critical | 3 | §4.3 |
| 12 | Validate at every boundary | Medium | Critical | 2-6 | §16-17 |

---

## Key Anti-Patterns to Avoid

1. **Unstructured tool-call parsing** — always use native provider tool-calling APIs with structured JSON outputs.
2. **Blocking sync execution** — all I/O must be async; never block the processing loop.
3. **Raw exception propagation** — wrap all errors in structured result types.
4. **Hardcoded tool/LLM/plugin names** — use registries and auto-discovery.
5. **Disclosing everything at once** — use progressive disclosure (first name+description, then full body on activation).
6. **No trajectory capture** — you cannot debug or improve what you cannot observe.
7. **No max_steps limit** — bounded execution is a safety and cost requirement.
8. **Manually constructing agents** — use builder patterns for complex construction with validation.
