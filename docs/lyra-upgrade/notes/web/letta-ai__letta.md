# letta-ai/letta — Deep-Read

**Repo**: https://github.com/letta-ai/letta (formerly MemGPT)
**Version**: 0.16.8 (latest tag)
**License**: Apache 2.0
**Language**: Python 3.11+
**Package**: `pip install letta` — a stateful LLM agent server with structured long-term memory

---

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: Long-term memory for LLM agents via structured, tool-editable memory blocks with automatic context window management.

The core innovation is a **three-tier memory architecture** that lets agents persist information across conversations without exceeding context limits:

### Three-Tier Memory

1. **Core Memory** (always in-context) — Typed, labeled blocks (`human`, `persona`, user-defined) that stay in the system prompt. Blocks have character limits and `read_only` flags. The agent can edit these blocks at runtime via the `memory()` built-in tool (with sub-commands: `create`, `str_replace`, `insert`, `delete`, `rename`). Implementation: `letta/schemas/block.py` (Block model), `letta/schemas/memory.py` (Memory class that compiles blocks into prompt text).

2. **Archival Memory** (vector-searchable external storage) — Documents split into passages, embedded, and stored in a vector DB (SQLite with sqlite-vec, PostgreSQL with pgvector, or Pinecone). Accessed via retrieval tools. Implementation: `letta/orm/passage.py`, `letta/services/archive_manager.py`, `letta/services/passage_manager.py`.

3. **Recall Memory** (conversation history with compaction) — Full message history stored in SQL. When the context window approaches its limit (configurable threshold, default 90% of context_window), the **summarizer** activates. Multiple compaction strategies exist (defined in `letta/services/summarizer/`): sliding window, partial evict, full summarization. The oldest messages get replaced by a summary injected as a `system_alert`. Implementation: `letta/services/message_manager.py`, `letta/services/summarizer/summarizer.py`, `letta/services/summarizer/summarizer_sliding_window.py`.

### Agent Loop

The execution loop (`letta/agents/letta_agent_v3.py` -> `_step()` method):
1. Receive user message(s)
2. Optionally compact/summarize in-context messages if over threshold
3. Call LLM with system prompt (containing Core Memory), tools, and in-context messages
4. Parse response: tool calls vs `send_message`
5. Execute tool calls (in sandbox: local, E2B, or Modal)
6. Append results as tool-role messages
7. If `request_heartbeat` flag is set, loop back to step 3 (auto-chaining)
8. Return response to caller

### Key mechanism: `send_message` tool

Rather than letting the LLM generate raw text, the agent MUST call the `send_message()` built-in tool to speak. This forces structured output through a function-call interface, making the agent's "speech" a tool return like any other function call.

---

## 2. Architecture & Core Modules (entry points, data flow, patterns)

### Entry Points

| Path | Purpose |
|------|---------|
| `letta/main.py` | Typer CLI app -> delegates to `letta.cli.cli.server` |
| `letta/cli/cli.py` | CLI server command (starts FastAPI + SyncServer) |
| `letta/server/server.py` | `SyncServer` class — single-threaded blocking server process |
| `letta/server/rest_api/app.py` | FastAPI REST application — agents, messages, tools, sources, jobs |
| `letta/server/rest_api/routers/` | Per-resource route modules (agents, blocks, groups, tools, etc.) |

### Core Data Flow

```
User -> REST API (FastAPI) -> SyncServer -> AgentLoop.factory -> LettaAgentV3.step()
                                                              -> LLMClient.create() -> provider-specific client
                                                              -> ToolExecutionSandbox -> isolated tool run
                                                              -> Summarizer (if context pressure)
                                                              -> MessageManager (persist messages)
                                                              -> BlockManager (update memory blocks)
```

### Module Map

| Module | Path | Responsibility |
|--------|------|----------------|
| **Agents** | `letta/agents/` | Agent loop V1/V2/V3, voice agents, ephemeral summary agent, bath processing, agent factory |
| **Core Agent** | `letta/agent.py` | Original abstract `BaseAgent` + `Agent` class (legacy), error handling, tool execution |
| **LLM Clients** | `letta/llm_api/` | Provider-specific LLM clients (OpenAI, Anthropic, Google, Bedrock, Together, Azure, xAI, Groq, etc.) |
| **Services** | `letta/services/` | Business logic layer: agent_manager, message_manager, block_manager, passage_manager, tool_manager, summarizer, MCP manager, conversation manager, routing |
| **ORM** | `letta/orm/` | SQLAlchemy models for all entities (Agent, Block, Message, Passage, Tool, Source, etc.) |
| **Schemas** | `letta/schemas/` | Pydantic models for API contracts, memory, messages, tools, blocks |
| **Functions/Tools** | `letta/functions/` | Built-in tool definitions (`base.py`, `multi_agent.py`, `files.py`, `voice.py`, `builtin.py`), tool parser, MCP client tools |
| **Config** | `letta/config.py`, `letta/conf.yaml`, `letta/settings.py` | Hierarchical config: YAML file + env vars + pydantic-settings |
| **Interfaces** | `letta/interface.py`, `letta/interfaces/` | Observer pattern for agent events (CLI, streaming, Anthropic streaming, OpenAI streaming) |
| **Adapters** | `letta/adapters/` | LLM request/response adapters for different provider formats |
| **Monitoring** | `letta/otel/`, `letta/monitoring/` | OpenTelemetry tracing, metrics, ClickHouse provider traces |
| **Local LLM** | `letta/local_llm/` | Support for local models (llama.cpp, Ollama, vLLM, web UI) |

### Architecture Patterns

- **Observer/Interface pattern**: `AgentInterface` abstract class with `user_message()`, `internal_monologue()`, `assistant_message()`, `function_message()` callbacks. Different implementations for CLI, streaming, etc.
- **Factory pattern**: `LLMClient.create()` creates provider-specific LLM clients; `AgentLoop.load()` creates the right agent version
- **Service layer**: All DB access goes through Manager classes (`AgentManager`, `MessageManager`, etc.) which wrap ORM operations
- **Repository pattern**: ORM layer (`letta/orm/`) as data access abstraction
- **Strategy pattern**: Summarizer modes (static buffer, partial evict, sliding window, full summarization) as interchangeable strategies

---

## 3. Performance/Benchmarks

**This repository contains NO in-repo benchmarks or performance numbers.** The README points to an external model leaderboard at https://leaderboard.letta.com/ for model quality rankings, but no latency, throughput, or cost benchmarks are included in the codebase.

What IS observable from the code:

- **Context window management**: Summarization triggers at 90% of context window (`SUMMARIZATION_TRIGGER_MULTIPLIER = 0.9` in `letta/constants.py`). Default context window: 128,000 tokens.
- **Maximum chaining steps**: Default 50 (`DEFAULT_MAX_STEPS = 50`) — the agent can auto-trigger re-entrant calls up to 50 times per user turn.
- **Embedding batch size**: 200 concurrent embedding requests (`EMBEDDING_BATCH_SIZE = 200`).
- **LLM timeout**: Request timeout 60s, stream timeout 600s (in `conf.yaml`).
- **Message buffer**: Default limit of 60 messages before compaction triggers, with a minimum of 15 messages retained.
- **Concurrent multi-agent sends**: 50 concurrent sends (`letta.multi_agent.concurrent_sends=50`).
- **Database pools**: PostgreSQL pool size 25, max overflow 10, pool timeout 30s.
- **Event loop**: Threadpool with 43 max workers for async operations.

The test suite has extensive integration tests (24+ integration test files) but no published performance regression tests.

---

## 4. Trade-offs (wins vs loses — from code, design decisions, complexity)

### Wins

1. **Persistence by default**: Every agent state is persisted to SQL (SQLite or PostgreSQL). You can kill and restart the server and agents resume exactly where they left off.
2. **Model agnosticism**: Supports 15+ LLM providers through a unified LLM client factory. Providers are pluggable via the Provider system.
3. **Tool sandbox safety**: Tools run in isolated sandboxes (local subprocess, E2B cloud sandbox, or Modal), preventing arbitrary code execution on the host.
4. **MCP support**: Full Model Context Protocol integration — agents can consume MCP servers as tool sources.
5. **Structured memory blocks**: Instead of dumping text into a system prompt, blocks are typed, labeled, and individually editable via tool calls. This enables precise memory surgery.
6. **Rich observability**: OpenTelemetry tracing, ClickHouse trace storage, Datadog integration, Sentry error tracking — enterprise-grade monitoring.
7. **Multi-agent & voice**: Sleeptime agents (background processing), voice agents, and group conversations are supported out of the box.

### Losses / Pain Points

1. **Massive dependency surface**: 60+ runtime Python dependencies including heavy packages like `llama-index`, `temporalio`, `matplotlib`, `tavily-python`, `anthropic`, `openai`, `sentry-sdk[fastapi]`, `ddtrace`. This is a heavy install.
2. **Architecture complexity**: The agent loop has evolved through V1, V2, V3 with different code paths (`letta/agent.py` base + `letta/agents/letta_agent.py` + `letta/agents/letta_agent_v2.py` + `letta/agents/letta_agent_v3.py`). Multiple generations of agent code coexist, increasing maintenance burden.
3. **Sync + async duality**: `SyncServer` uses synchronous code while agent loops are async. The codebase contains patterns like `safe_create_task_with_return` to bridge async tool execution into sync contexts — a sign of ongoing migration.
4. **Dual summarizer implementations**: There are both old-style summarizer code in `letta/memory.py` and new-style in `letta/services/summarizer/`. The `letta/services/summarizer/summarizer.py` has a comment `# NOTE: legacy, new version is functional` suggesting incomplete migration.
5. **Config sprawl**: Configuration is split across `conf.yaml`, `pyproject.toml`, `settings.py`, `config.py`, env vars, and `LettaConfig`. The `config.py` file has massive commented-out blocks suggesting ongoing refactoring.
6. **Heavy default system prompt**: The system prompt generation in `letta/prompts/` + agent initialization in `letta/services/helpers/agent_manager_helper.py` constructs a large system prompt with memory blocks, tool definitions, and tool rules — which consumes significant context window budget before any conversation happens.

---

## 5. Design Rationale (why this approach)

Letta (originally MemGPT) was designed to solve a fundamental problem with LLM agents: **the context window is finite and conversations overflow it**. The design choices flow from this constraint:

1. **Structured memory blocks over free-form text** — The `Block` model (label + value + limit + read_only) lets the system reason about what should stay in context vs. what should be archived. The `Memory` class compiles blocks into system prompt sections. This is more constrained than stuffing everything into a prompt, but gives the system explicit handles for memory management.

2. **`send_message` as a tool, not raw output** — Forcing the agent to call `send_message()` means all agent output goes through the tool call/return cycle. This makes streaming, tool rules (e.g., `RequiresApprovalToolRule` for human-in-the-loop), and output enforcement possible through a single mechanism.

3. **Summarizer with multiple strategies** — Not all conversations degrade the same way. Sliding window works for short exchanges; partial evict preserves recent messages while summarizing older ones; full summarization works for long-running agents. The configurable strategy lets deployers choose the right trade-off for their use case.

4. **Tool rules system** — The `ToolRule` (Continue, Terminal, RequiresApproval) system lets developers constrain agent behavior declaratively (e.g., "after searching the web, you must present results before searching again"). This is implemented via `ToolRulesSolver` which filters available tools at each step based on history.

5. **Sandboxed tool execution** — Running untrusted LLM-generated code (or even structured tool calls) on the host is dangerous. E2B and Modal sandboxes provide cloud isolation; the local sandbox uses a venv with configurable timeout and autoreload.

6. **Provider-agnostic LLM routing** — The `LLMRoutingClient` with circuit breaker pattern lets the system fall back between providers. This is critical for production reliability.

7. **ORM persistence for everything** — Every message, agent state, tool definition, and memory block is in SQL. This enables agent serialization/deserialization, audit trails, and historical analysis. The `OrmMetadataBase` mixin provides `created_by_id`, `last_updated_by_id`, timestamps across all entities.

---

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier + LICENSE)

### Transferable Idea: Block-Based Structured Memory with Automatic Compaction

Letta's core memory architecture — **typed, labeled memory blocks that the agent can edit via tools, combined with automatic context window compaction** — is directly applicable to Lyra.

The specific mechanism to adopt: instead of Lyra's current approach of stuffing conversation history and user preferences into a growing system prompt, implement a **block-based memory manager** where:
- Core identity blocks (always in context): persona, human profile, session goals
- Archival blocks (vector-retrieved as needed): past conversation summaries, learned patterns
- Compaction triggers when context exceeds configurable threshold (e.g., 85% of budget)
- Summarizer agent (a lightweight LLM call) compresses older messages into a summary block

### Lyra Route: **Section 4.2 — Memory & State Management**

This fits naturally into the Lyra memory subsystem:
- **4.2.x "Block-based structured memory"**: Add `MemoryBlock` class (label, value, limit, read_only) to Lyra's agent state. Let the agent edit blocks via a `memory()` tool (create/str_replace/insert/delete/rename).
- **4.2.x "Automatic context compaction"**: Add `SummarizerService` that monitors context pressure and triggers compaction via a lightweight summary agent, storing compressed history in a vector-accessible block.

### Impact: 8/10
- Dramatically improves Lyra's ability to sustain long conversations without context degradation
- Reduces token waste by preventing unbounded context growth
- Enables the agent to explicitly reason about what it remembers
- Solves the "agent forgets mid-conversation" problem without manual summarization

### Effort: 6/10
- Requires building MemoryBlock model, compile-to-prompt logic, and tool interface
- Requires an archival storage backend (vector DB or filtered SQL)
- Requires a summarization agent with configurable strategies
- Integration with existing Lyra agent loop is moderate (tool execution already exists)
- Reuses Lyra's existing LLM call infrastructure for the summarizer agent

### Tier: P1 (high impact, moderate effort)

### License Compatibility

**Apache 2.0** — Compatible with Lyra. Letta is Apache 2.0 licensed. Attribution required if copying significant portions of code. No copyleft restrictions. The `memory()` tool function signatures and block model patterns can be ported with proper attribution.

---

**File paths**: This note at `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/letta-ai__letta.md`
