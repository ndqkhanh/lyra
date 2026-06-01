# Harness Architecture Deep-Dive: DeerFlow 2.0, OpenCode, and PI

> Deep-read of three closest analogs to Lyra, focused on architecture, provider abstraction, and skill systems.

---

## 1. DeerFlow 2.0 (bytedance/deer-flow)

**License**: MIT  
**Language**: Python (backend harness), TypeScript/React (frontend)  
**Status**: Actively maintained, #1 GitHub Trending Feb 2026  
**Repo**: https://github.com/bytedance/deer-flow

### 1.1 Entry Points

The system has two entry layers:

1. **Gateway** (`backend/app/gateway/`) — FastAPI application that serves the LangGraph Server API. Routes live in `gateway/routers/` (auth, threads, runs, skills, MCP, feedback, channels). The gateway creates LangGraph runs via `run_agent()` in `runtime/runs/worker.py`.

2. **Harness** (`backend/packages/harness/deerflow/`) — The core orchestration library. Its public API entry point is `client.py` (a `DeerFlowClient` that wraps the harness for programmatic use).

### 1.2 Core Modules

```
deerflow/
  agents/lead_agent/agent.py   # LangGraph graph factory: make_lead_agent()
  agents/middlewares/           # 17 middleware classes (pipeline pattern)
  agents/memory/                # Long-term memory (queue + LLM summarization)
  agents/thread_state.py        # ThreadState schema (messages, sandbox, thread_data)
  runtime/                      # Checkpointer, Store, StreamBridge, RunJournal
  runtime/runs/                 # RunManager (in-memory + persistence), worker.py
  models/                       # Model factory + provider classes (Claude, OpenAI, vLLM, MindIE, Codex)
  tools/                        # Tool registry + builtin tools (task, clarification, present_file)
  subagents/                    # SubagentExecutor, registry, config, token_collector
  sandbox/                      # SandboxProvider ABC + LocalSandbox + AioSandbox
  skills/                       # Skill types, parser, installer, storage, validation
  mcp/                          # MCP client, session pool, tools
  config/                       # ~20 config modules (YAML-driven)
  reflection/                   # Dynamic class resolution from config strings
```

### 1.3 Data Structures

- **ThreadState** — LangGraph state schema with `messages`, `sandbox_state`, `thread_data`
- **RunRecord** — In-memory run registry with status tracking, token counters, abort events
- **Skill** dataclass — name, description, license, skill_dir, skill_file, relative_path, category (public/custom), allowed_tools, enabled
- **SubagentConfig** — name, description, system_prompt, tools, disallowed_tools, skills, model, max_turns, timeout_seconds
- **SubagentResult** — task_id, trace_id, status, result, error, timestamps, ai_messages, token_usage

### 1.4 Provider Abstraction

DeerFlow uses a **config-driven factory pattern**:

```python
# models/__init__.py
from .factory import create_chat_model
```

`create_chat_model(name, thinking_enabled, app_config)` works as follows:
1. Looks up model config from `config.yaml` by name
2. Resolves the class via `resolve_class(model_config.use, BaseChatModel)` (dynamic import from dotted path like `deerflow.models.claude_provider:ClaudeChatModel`)
3. Dumps config fields, excluding internal keys (`use`, `name`, `supports_thinking`, etc.)
4. Applies thinking/disabling logic per-provider (Claude, OpenAI, vLLM, Codex)
5. Instantiates the model class with remaining kwargs

Each provider extends LangChain's `BaseChatModel`. Built-in providers: `ClaudeChatModel` (ChatAnthropic with OAuth Bearer auth, prompt caching, auto-thinking-budget), `OpenAI-based`, `vLLM`, `MindIE`, `Codex`.

The sandbox system uses the same pattern: `resolve_class(config.sandbox.use, SandboxProvider)`.

### 1.5 Middleware Architecture (Pipeline Pattern)

DeerFlow has the most sophisticated middleware system of the three. Middlewares are LangChain `AgentMiddleware` subclasses. The chain is ordered with explicit dependency comments (lines 256-265 of `agent.py`):

1. `ToolErrorHandlingMiddleware` — catches tool exceptions
2. `DynamicContextMiddleware` — injects `<system-reminder>` (date, memory) into first HumanMessage
3. `SummarizationMiddleware` — reduces context via LLM summarization
4. `TodoMiddleware` — plan mode task tracking
5. `TokenUsageMiddleware`
6. `TitleMiddleware`
7. `MemoryMiddleware` — queues conversation for async memory update
8. `ViewImageMiddleware`
9. `DeferredToolFilterMiddleware`
10. `SubagentLimitMiddleware`
11. `LoopDetectionMiddleware`
12. `SafetyFinishReasonMiddleware`
13. `ClarificationMiddleware`

### 1.6 Most Transferable Idea for Lyra

**The middleware pipeline as a configurable ordered chain.** DeerFlow's middleware system is its architectural backbone — 17 pluggable middlewares that wrap every agent turn without the agent knowing. The key insight is explicit ordering with documented dependency reasoning, combined with the ability to inject custom middlewares at specific points in the chain. Lyra could adopt this exactly: define an `AgentMiddleware` ABC, build a `_build_middlewares()` factory, and let each middleware modify `state` before/after model calls via `before_agent`/`after_agent` hooks.

---

## 2. OpenCode (sst/opencode)

**License**: MIT  
**Language**: TypeScript (Effect-TS ecosystem)  
**Status**: Actively maintained, npm package `opencode-ai`  
**Repo**: https://github.com/anomalyco/opencode (was sst/opencode)

### 2.1 Entry Points

- **CLI** (`packages/cli/src/index.ts`) — entry point
- **LLM package** (`packages/llm/`) — standalone multi-provider LLM client
- **Core package** (`packages/core/`) — session management, config, providers, plugins

### 2.2 Core Modules

```
packages/llm/src/
  llm.ts              # Public API: generate, stream, generateObject
  provider.ts         # Provider.Definition type + make() helper
  providers/          # Provider facade implementations (Anthropic, OpenAI, Bedrock, Google, etc.)
  protocols/          # Wire protocol implementations (openai-chat, anthropic-messages, gemini, etc.)
  route/              # Route abstraction: client.ts, endpoint.ts, auth.ts, framing.ts, transport/
  schema/             # LLMRequest, LLMResponse, Message, events, errors
  tool.ts             # Tool schema + execution
  tool-runtime.ts     # Tool execution runtime for streaming

packages/core/src/
  config/provider.ts  # Provider config schema (V2)
  plugin/             # Plugin system with provider sub-plugins
  plugin/provider/    # ~20 provider plugins (anthropic, bedrock, google, xai, etc.)
  session/            # Session management
  agent.ts            # Agent abstraction
```

### 2.3 Data Structures

- **Model** — provider + route + id + limits + capabilities
- **Route<Body, Prepared>** — id, provider, protocol, endpoint, auth, transport, defaults, body
- **LLMRequest** — normalized request across all providers: system, messages, tools, toolChoice, generation, http, providerOptions
- **Provider.Definition** — id + model factory + optional apis map
- **RouteDefaults** — headers, limits, generation, providerOptions, http

### 2.4 Provider Abstraction

OpenCode's provider abstraction is **the most sophisticated of the three** and is already effectively the industry standard. The architecture is layered:

**Layer 1: Protocol** — What API am I speaking?
- Defines body schema, fromRequest (common -> native), stream event schema, and stream parsing state machine.
- Examples: `openai-chat`, `anthropic-messages`, `gemini`, `bedrock-converse`, `openai-responses`

**Layer 2: Transport** — How do I send the request?
- HTTP + SSE framing (json, sse, sseJson) or WebSocket

**Layer 3: Auth** — How do I authenticate?
- Bearer token, API key header, custom auth functions, OAuth

**Layer 4: Endpoint** — Where do I send it?
- baseURL + path + optional overrides

These four layers compose into a **Route**:

```typescript
const route = Route.make({
  id: "openai-chat",
  provider: "openai",
  protocol: OpenAIChat.protocol,     // body schema + fromRequest + stream parsing
  endpoint: Endpoint.path("/chat/completions", { baseURL: "https://api.openai.com/v1" }),
  auth: Auth.bearer({ apiKey: "..." }),
  framing: Framing.sseJson,          // SSE with JSON event parsing
});
```

Provider facades then wrap this:

```typescript
// providers/anthropic.ts
export const configure = (options) => {
  const route = AnthropicMessages.route.with({ ...options, endpoint: ... });
  return {
    id: "anthropic",
    model: (id: string) => route.model({ id, provider: "anthropic" }),
    configure,  // fluent chaining
  };
};
```

### 2.5 LLM Client

The `LLMClient` (route/client.ts) is a Service in Effect-TS. Its public surface:

- **`prepare(request)`** — Compile request through protocol body construction + validation + HTTP preparation without sending
- **`stream(request)`** — Stream LLM events
- **`generate(request)`** — Collect stream into a single response

The client compiles `LLMRequest` by: resolving model -> getting route -> building provider-native body via `from()` -> validating with schema -> preparing transport -> executing.

### 2.6 Most Transferable Idea for Lyra

**The Protocol-Transport-Auth-Endpoint separation.** This is the cleanest architectural decomposition of LLM provider abstraction that exists. Lyra should adopt this four-axis model:

- **Protocol**: owns body construction, body schema, and stream parsing. One per API dialect (OpenAI Chat, Anthropic Messages, Gemini, etc.)
- **Transport**: owns byte-level communication (HTTP, SSE, WebSocket). The protocol tells the transport what frames to expect.
- **Auth**: owns credential resolution and injection. Separate from transport so it can be layered independently.
- **Endpoint**: owns URL resolution.

This orthogonal separation means adding a new provider is just composing four independent pieces, most of which already exist.

---

## 3. PI (badlogic/pi-mono)

**License**: MIT  
**Language**: TypeScript  
**Status**: Actively maintained, npm package `@earendil-works/pi-coding-agent`  
**Repo**: https://github.com/badlogic/pi-mono

### 3.1 Entry Points

- **CLI** (`packages/coding-agent/src/cli.ts`) — interactive coding agent
- **Agent SDK** (`packages/agent/src/`) — reusable agent harness library
- **AI SDK** (`packages/ai/src/`) — multi-provider LLM API

### 3.2 Core Modules

```
packages/agent/src/
  agent-harness.ts      # AgentHarness — the main loop orchestrator
  skills.ts             # Skill loading + formatSkillsForSystemPrompt + formatSkillInvocation
  system-prompt.ts      # Skill → system prompt formatting
  prompt-templates.ts   # Prompt template loading/invocation
  session/              # Session management (JSONL storage, memory repo)
  compaction/           # Context window compaction

packages/coding-agent/src/
  core/skills.ts        # Skill loading (production version with ignore-file support)
  core/system-prompt.ts # System prompt assembly
  core/compaction/      # Branch summarization + compaction
  core/extensions/      # Plugin/extension system
```

### 3.3 Skill System Architecture (Lazy-Loading / Progressive Disclosure)

This is PI's signature feature and the most relevant to Lyra.

**Design Principle**: "Progressive disclosure" — only skill names and descriptions are injected into the system prompt; full instructions are loaded on demand when the agent decides they're needed.

**Skill Format** (AgentSkills.io open standard):

```
my-skill/
  SKILL.md             # YAML frontmatter + Markdown body
  scripts/             # Optional executable scripts
  references/          # Optional reference files
  assets/              # Optional assets
```

**SKILL.md format**:
```markdown
---
name: my-skill
description: Use when the task involves X
disable-model-invocation: false
---

# Full Instructions
... actual skill content ...
```

**Loading Flow**:

1. **Discovery**: `loadSkillsFromDir()` scans `~/.pi/agent/skills/`, `.pi/skills/`, and explicit paths. Each `SKILL.md` file becomes a `Skill` object with name, description, filePath, baseDir.

2. **System Prompt Injection**: Only the name and description are listed in `<available_skills>` XML format. The formatSkillsForSystemPrompt() function produces:
   ```
   <available_skills>
     <skill>
       <name>typescript-guidelines</name>
       <description>TypeScript coding standards</description>
       <location>/home/user/.pi/agent/skills/typescript-guidelines/SKILL.md</location>
     </skill>
   </available_skills>
   ```

3. **On-Demand Loading**: When the agent decides a task matches a skill's description, it uses the `read` tool to load the full `SKILL.md` file. The harness provides `formatSkillInvocation()` to wrap the loaded content in a `<skill name="..." location="...">` XML tag.

4. **Explicit Invocation**: Users can force-load via `/skill:name [args]` slash commands.

**Two versions of skill loading exist**:
- `packages/agent/src/harness/skills.ts` — abstracted via `ExecutionEnv` interface (async, env-agnostic, for library use)
- `packages/coding-agent/src/core/skills.ts` — Node.js-specific with ignore-file support (.gitignore, .ignore, .fdignore), collision detection, diagnostics

### 3.4 Agent Harness

The `AgentHarness` class (`packages/agent/src/harness/agent-harness.ts`) orchestrates the full agent lifecycle with explicit phases:

1. `setPhase("turn")` — enters a turn
2. Create turn state snapshot (tools, model, resources)
3. Load skills progressively (descriptions only initially)
4. Execute turn loop (LLM calls <-> tool execution)
5. Flush to session storage (JSONL)
6. `setPhase("idle")`

It supports:
- Compaction (context window management via branch summarization)
- Prompt templates (reusable Markdown with `$1`, `$@` variable substitution)
- Skill invocation (both model-initiated and user-initiated)
- Extensions (TypeScript files that register tools at startup)

### 3.5 Most Transferable Idea for Lyra

**Progressive disclosure / lazy-loading skill system.** This is the most practical skill system of all three projects. The key mechanics:

1. Scan for `SKILL.md` files in well-known directories
2. Parse YAML frontmatter for `name` + `description`
3. Inject only `<skill><name>...</name><description>...</description><location>...</location></skill>` into the system prompt (no body content)
4. The model reads the full file when relevant
5. Wrap loaded content in `<skill>` XML tags for context

This approach keeps the system prompt small (critical for prompt cache hit rates), avoids wasted tokens, and follows the "[harness over graph](https://github.com/Crokily/pi-agent-app-dev)" philosophy where the agent itself decides what capabilities to pull in.

Lyra already has a skill system (`.omc/skills/`) — adopting progressive disclosure would be a natural evolution: change the system prompt to list only descriptions, and let the agent `read` the full SKILL.md on demand.

---

## Comparative Summary

| Dimension | DeerFlow 2.0 | OpenCode | PI |
|-----------|--------------|----------|-----|
| **Language** | Python | TypeScript (Effect-TS) | TypeScript |
| **License** | MIT | MIT | MIT |
| **Provider Abstraction** | Config-driven factory + LangChain base classes | Protocol-Transport-Auth-Endpoint 4-axis composition | Simple config-driven (pi-ai package) |
| **Skill System** | SKILL.md files, YAML frontmatter, install from .skill archives, security scanning | N/A (no skill system) | Progressive disclosure (descriptions only, load on demand), AgentSkills.io standard |
| **Middleware** | 17 ordered LangChain AgentMiddleware subclasses | Effect-TS Service + Layer composition | Hook-based, less formalized |
| **Sub-agents** | Full SubagentExecutor with background execution, cancellation, token tracking | Tool execution runtime (tool-runtime.ts) | Extension system, subagent example |
| **Sandbox** | Local + Docker (AioSandbox), per-thread isolation, path mapping | N/A | N/A (sandbox example in extensions) |
| **Config** | YAML-driven, ~20 config modules | JSON/SST config + V2 schema | JSON config |
| **Memory** | LLM-based summarization with queue + debouncing | Session storage | Session JSONL + compaction |

## Top-3 Takeaways for Lyra

1. **OpenCode's Protocol-Transport-Auth-Endpoint separation** — Adopt this 4-axis model for Lyra's provider abstraction. It cleanly separates concerns and makes adding new providers a matter of composing existing pieces.

2. **DeerFlow's middleware pipeline** — Adopt the ordered chain of `AgentMiddleware` subclasses that wrap agent turns. The explicit ordering with dependency documentation (DeerFlow's lines 256-265) is critical.

3. **PI's progressive disclosure skill system** — Evolve Lyra's skill loading from "inject everything" to "inject only descriptions, load on demand." This saves tokens, improves cache hit rates, and lets the agent decide what it needs.
