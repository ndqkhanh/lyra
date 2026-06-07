# microsoft/ai-agents-for-beginners -- Deep-Read

Repository: https://github.com/microsoft/ai-agents-for-beginners
Clone path: /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/microsoft__ai-agents-for-beginners

## 1. Headline Feature & Mechanism

This is an **educational curriculum** (not a library or framework) teaching AI agent construction through 18 lesson directories. Each lesson pairs a README with Jupyter notebooks using the **Microsoft Agent Framework (MAF)** against **Azure AI Foundry Agent Service V2** (the Responses API on Azure).

The core mechanism taught is a **layered agent architecture**:

```
Client (AzureAIProjectAgentProvider)
  -> Agent (instructions + system prompt)
    -> Tools (@tool-decorated Python functions)
      -> Session (conversation history)
        -> WorkflowBuilder (graph-based orchestration)
```

Every notebook demonstrates the same travel-agent scenario (booking, destination lookup, itinerary planning) to show how each design pattern composes. The code is tutorial-grade -- clear, linear, and annotated with Pydantic models for structured output validation.

### What the repo is actually known for

This is part of Microsoft's "X for Beginners" series (generative-ai-for-beginners, mcp-for-beginners, etc.). It is the most comprehensive free walkthrough of Microsoft Agent Framework available, covering:

- Four core design patterns: Tool Use, Planning, Multi-Agent, Metacognition
- Agentic protocols: MCP (Model Context Protocol), A2A (Agent-to-Agent), NLWeb
- Agent memory: working, short-term, long-term, persona, episodic, entity (via Mem0, Cognee, Azure AI Search)
- Human-in-the-loop workflows via RequestInfoExecutor
- Function middleware pipelines (Lesson 14's priority-check middleware pattern)
- Cryptographic receipts for agent audit trails (Lesson 18)

## 2. Architecture & Core Modules

### Project Structure

```
00-course-setup/         -- Dev environment prerequisites
01-intro-to-ai-agents/   -- First agent: TravelAgent with @tool
02-explore-agentic-frameworks/ -- MAF architecture layers
03-agentic-design-patterns/ -- Instructions, structured output, single-responsibility
04-tool-use/             -- @tool decorator, approval_mode, multi-tool agents
05-agentic-rag/          -- Agentic RAG with Azure AI Search
06-building-trustworthy-agents/ -- System messages and safety
07-planning-design/      -- Task decomposition, iterative planning
08-multi-agent/          -- WorkflowBuilder + add_edge sequential pipelines
09-metacognition/        -- Primary/backup fallback, self-evaluation
10-ai-agents-production/ -- Deployment and monitoring
11-agentic-protocols/    -- MCP, A2A, NLWeb
12-context-engineering/  -- Chat summarization, scratchpad context
13-agent-memory/         -- Mem0, Cognee, knowledge graphs
14-microsoft-agent-framework/ -- **Core advanced patterns**:
  - Sequential orchestration
  - Concurrent fan-out/fan-in
  - Conditional edge routing
  - Handoff orchestration (dynamic specialist routing)
  - Middleware pipeline (function invocation interception)
  - Human-in-the-loop (RequestInfoExecutor)
15-browser-use/          -- Computer Use Agent (CUA) with Playwright
18-securing-ai-agents/   -- Cryptographic receipts via JCS + PyNaCl
```

### Core Abstractions (what actually matters for Lyra)

**Tool Definition Pattern** (`@tool` decorator):
```python
@tool(approval_mode="never_require")   # or "always_require" for safety
def check_availability(destination: Annotated[str, "The destination"]):
```
- Docstring = tool description the LLM sees
- Type annotations = tool schema for the LLM
- `approval_mode` controls human-in-the-loop gating

**Agent Creation**:
```python
provider = AzureAIProjectAgentProvider(credential=AzureCliCredential())
agent = await provider.create_agent(
    name="AgentName",
    instructions="system prompt here",
    tools=[list_of_tools],
    middleware=[list_of_middleware_functions],  # Lesson 14 key feature
)
```

**WorkflowBuilder Graph** (`Lesson 08` and `Lesson 14`):
```python
workflow = (
    WorkflowBuilder(start_executor=agent_a, output_executors=[agent_c])
    .add_edge(agent_a, agent_b, condition=some_condition)  # conditional routing
    .add_edge(agent_b, agent_c)
    .build()
)
```

**Middleware Pipeline** (`Lesson 14-middleware`):
```python
async def priority_check_middleware(context, next):
    await next(context)          # let tool execute
    if context.result:           # inspect/modify result
        context.result = new_val # override
```
Middleware wraps tool invocation, enabling cross-cutting concerns (auth, logging, result modification).

**Handoff Orchestration** (`Lesson 14-handoff`):
```python
workflow = (
    HandoffBuilder(name="support", participants=[agents...])
    .set_coordinator(customer_support_agent)
    .add_handoff(customer_support_agent, [booking_agent, disputes_agent, ...])
    .build()
)
```
Dynamic agent routing based on conversation intent -- triage agent hands to specialists.

**Human-in-the-Loop** (`Lesson 14-human-loop`):
```
Agent -> RequestInfoExecutor (pauses workflow) -> [human input] -> DecisionManager -> route
```
RequestInfoExecutor emits `RequestInfoEvent`; app collects input; workflow resumes via `send_responses_streaming()`.

### Dependencies (notable)

From `requirements.txt`:
- `agent-framework` -- the core Microsoft Agent Framework SDK
- `a2a-sdk` -- Agent-to-Agent protocol
- `mcp[cli]` -- Model Context Protocol support
- `azure-ai-inference`, `azure-ai-projects`, `azure-identity` -- Azure AI services
- `azure-search-documents` -- RAG backend
- `pydantic` -- structured output schemas
- `jcs`, `pynacl` -- cryptographic receipts (Lesson 18)

## 3. Performance / Benchmarks

This repository contains **no benchmarks**. It is a course, not a benchmarked system. The only performance data comes from Lesson 14-concurrent which includes an educational timing comparison:

```
Concurrent (3 agents fan-out):  ~X seconds (varies by model latency)
Sequential (3 agents chain):    ~3X seconds
Improvement:                    60-70% faster (theoretical, depends on backend)
```

These numbers are illustrative for students, not production benchmarks. No latency percentiles, no throughput, no cost data.

## 4. Trade-offs

### Wins

- **Comprehensive pedagogy**: Covers the full spectrum from one-function `@tool` to multi-agent DAGs to cryptographic signing. A developer working through all 18 lessons gets a genuine end-to-end understanding.
- **Consistent travel-agent scenario**: Every lesson reuses the same domain (booking, destinations, flights), so the student focuses on the pattern, not the domain.
- **Middleware pattern is genuinely novel**: The function invocation middleware (Lesson 14-middleware) -- intercepting `context.result` after `await next(context)` -- is a clean cross-cutting concern pattern not commonly seen in agent frameworks. This is the repo's most transferable architectural idea.
- **Human-in-the-loop is well-designed**: RequestInfoExecutor / RequestResponse correlation pattern is a pragmatic balance between automation and oversight.
- **54 language translations**: Automated via GitHub Actions (co-op translator), dramatically lowering the barrier for non-English learners.

### Losses

- **Not runnable without Azure**: The primary provider (`AzureAIProjectAgentProvider`) requires an Azure AI Foundry project, an Azure subscription, and `az login`. Lesson 14-handoff uses `OpenAIChatClient` directly (via GitHub Models), but this is the exception, not the rule.
- **API instability**: Two open GitHub issues (#544, #545) document that the current `agent-framework` package on PyPI has breaking API changes that prevent the Lesson 14 notebooks and the 08-multi-agent notebook from importing. The repo tracks a rapidly-moving SDK.
- **No test suite**: This is purely educational. No CI tests verify the notebooks execute. No unit tests for the code examples.
- **Shallow code depth**: Each notebook is ~50-100 lines of actual Python. The "complex" examples (conditional workflow with middleware) are still only ~200 lines. No production-grade error handling, retry logic, or observability.
- **Single-provider focus**: Despite mentioning alternative providers in the README (MiniMax, OpenAI-compatible), the actual code samples overwhelmingly use Azure-specific APIs. Porting to another backend requires reworking the provider layer.
- **No multi-turn persistence beyond session**: AgentSession lives in memory. No database-backed state management for long-running workflows.

### From GitHub Issues

- Two open import errors on `agent-framework` (Issues #544, #545) -- the framework's public API changed and the notebooks haven't caught up.
- Pip dependency resolution failures reported (#369, #372) due to conflicting transitive dependencies.
- `.NET` samples fail to compile (#434) due to API mismatch in the .NET MAF SDK.
- Large repo size (~3GB with translation blobs) was a recurring user complaint, leading to sparse-checkout documentation in the course setup.

## 5. Design Rationale

The design choices reflect the repo's primary goal: **teach concepts, not infrastructure**.

**Why a course, not a library?** Microsoft already ships `agent-framework` as a separate PyPI package. This repo exists to drive adoption of that SDK by showing it works end-to-end in a realistic (if simplified) travel-agent scenario. Each lesson layers on one new concept, from single-tool agents (Lesson 01) to cryptographic audit trails (Lesson 18).

**Why Pydantic for structured output?** Pydantic is the standard Python data-validation library, already widely adopted in the ML/AI ecosystem. Using `response_format=MyPydanticModel` lets the course demonstrate type-safe, validated agent output without introducing another DSL.

**Why WorkflowBuilder graph model?** A directed graph maps naturally to multi-agent orchestration. `add_edge(a, b, condition=fn)` is declarative -- the student specifies *what* should happen when, not *how* to implement the routing loop. This is the right level of abstraction for a beginner course.

**Why middleware as a first-class concept?** The middleware pattern (intercepting tool function calls) is positioned as a "Lesson 14 advanced topic," not Lesson 01. This is deliberate -- middleware is a cross-cutting concern that requires understanding the base agent loop first. But its inclusion signals that Microsoft believes function-level interception is architecturally important for production agents.

**Why no tests?** The repo is documentation, not software. Tests would add maintenance overhead without improving the learning experience for the target audience (beginners).

## 6. Transfer to Lyra

### The One Idea: Function-Level Middleware Pipeline for Tool Invocation

The `priority_check_middleware` pattern from Lesson 14-middleware is the most transferable architectural idea in this repo. It is a **function invocation middleware** that wraps every tool call in a pipeline:

```
Tool function -> middleware[0] -> middleware[1] -> ... -> actual execution -> middleware[1] post -> middleware[0] post
```

Each middleware can:
- Inspect arguments before execution
- Modify the return value after execution
- Skip execution entirely (return a cached/precomputed result)
- Log, audit, or transform the call

This is a direct architectural pattern for Lyra's **Safety** and **Verification** layers applied at the tool-call boundary, not just at the system-prompt level.

### How it applies to Lyra's architecture

Lyra's tool execution currently has no interception layer. Adding a middleware stack would enable:

1. **Safety gating**: A `safety_validator_middleware` intercepts every tool call, checks if the arguments create risk (file deletion, code execution, network access), and blocks or flags the call before it executes. This is far more reliable than safety via system prompt alone.

2. **Bias-corrected verification**: Per Lyra's §4.8 plan, an identity-anonymization middleware can strip PII from tool arguments before they reach external APIs, and a post-execution middleware can re-weigh results using ReTAS dialectical alignment.

3. **Cost-aware routing**: A `cost_middleware` checks prompt cache state before each tool invocation, routing cheap tools (grep, file read) immediately and expensive tools (LLM-based search) through a budget checker.

4. **Observability**: A `tracing_middleware` records every tool call with duration, argument hash, and result preview -- without changing any tool definition.

### Workstream Route: §4.8 Verification (Safety + Observability)

The middleware pattern maps to **§4.8 Verification** because:

- Function-level interception is the correct enforcement point for safety constraints (stronger than system prompt, lighter than full agent supervision)
- The pattern enables both pre-execution checks (block dangerous calls) and post-execution transforms (bias correction, anonymization)
- The existing §4.8 plan calls for "adversarial verification at every action boundary" -- middleware is the cleanest way to implement this

Route: Add an optional `middleware` parameter to Lyra's `execute_tool()` internal API, accepting an ordered list of async middleware functions. Each middleware receives `(tool_name, args, result)` context and can return a modified result or raise to abort. Wire this into the tool executor so that every user-defined tool and every built-in tool passes through the stack.

Impact: **8/10** -- Middleware fundamentally changes how safety and observability are implemented. Currently these are ad-hoc; middleware makes them systematic.

Effort: **4/10** -- The abstraction is simple (one async middleware protocol, one executor change). The harder part is writing the individual middleware implementations (safety validator with a rules engine, PII scrubber, etc.), but those can be added incrementally.

Tier: **P1** -- Should land in Phase 1 or early Phase 2. Without a safety middleware layer, adversarial tool misuse can only be caught by system prompt, which is unreliable. This is a prerequisite for the autonomy features planned in Phase 2.

### Note on Licensing

**MIT License** (Copyright Microsoft Corporation). Compatible with Lyra's MIT-licensed architecture. No restrictions on use, modification, or redistribution.

The memory lesson taxonomy (working / short-term / long-term / persona / episodic / entity) could also be referenced for Lyra's §4.1 Memory workstream, but the middleware pattern is more directly actionable.
