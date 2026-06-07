# bytedance/deer-flow -- Deep-Read

Repo: https://github.com/bytedance/deer-flow
Cloned to: /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/bytedance__deer-flow
Deep-read date: 2026-06-07
Version: 2.0 (ground-up rewrite, shares no code with v1)

---

## 1. Headline Feature & Mechanism

**DeerFlow is an open-source "super agent harness"** -- a LangGraph-based runtime that gives LLM agents a full execution environment: sandboxed filesystem, persistent long-term memory, dynamic sub-agent delegation, extensible skill packs, MCP tool integration, and multi-platform IM channels (Telegram, Slack, Feishu/Lark, WeChat, DingTalk). It is NOT a deep research tool (that was v1); v2 is a general-purpose agent OS.

**How the code really works:**

The entire system is built on a LangGraph state graph. The entry point (registered in `backend/langgraph.json`) is `deerflow.agents:make_lead_agent`, which constructs a `langchain.agents.create_agent()` graph. The real magic is not in the graph itself but in the **middleware chain** that wraps every LLM call and tool execution -- 18 middleware components assembled in strict order across two files (`build_lead_runtime_middlewares` and `_build_middlewares`):

1. ThreadDataMiddleware -- creates per-thread directories under `users/{user_id}/threads/{thread_id}/user-data/{workspace,uploads,outputs}`
2. UploadsMiddleware -- injects uploaded files into conversation
3. SandboxMiddleware -- acquires a sandbox (local, Docker, or Kubernetes) per thread
4. DanglingToolCallMiddleware -- handles interrupted tool call sequences
5. LLMErrorHandlingMiddleware -- normalizes provider failures
6. GuardrailMiddleware -- pre-tool-call authorization (AllowlistProvider, OAP, or custom)
7. SandboxAuditMiddleware -- security logging for shell/file ops
8. ToolErrorHandlingMiddleware -- converts tool exceptions into error ToolMessages
9. SummarizationMiddleware -- context compression at token limits
10. TodoListMiddleware -- plan-mode task tracking (optional)
11. TokenUsageMiddleware -- token accounting
12. TitleMiddleware -- auto-generates thread titles
13. MemoryMiddleware -- queues conversation for async memory update
14. ViewImageMiddleware -- injects base64 image data before LLM call
15. DeferredToolFilterMiddleware -- hides MCP tool schemas until needed
16. SubagentLimitMiddleware -- caps concurrent sub-agents at 3
17. LoopDetectionMiddleware -- detects repeated tool-call loops
18. ClarificationMiddleware -- intercepts ask_clarification tool (must be last)

The agent's sandbox abstraction provides a consistent `/mnt/user-data/{workspace,uploads,outputs}` virtual path regardless of backend: `LocalSandboxProvider` maps these to per-thread host directories via `PathMapping`; `AioSandboxProvider` volume-mounts them into Docker containers. Both implement the same `Sandbox` ABC with `execute_command`, `read_file`, `write_file`, `download_file`.

**Skills** are Markdown files with YAML frontmatter stored in `skills/public/` and `skills/custom/`. They are loaded progressively -- only when the task needs them, not all at once -- via `load_skills()` which scans for `SKILL.md`, parses metadata, and reads enabled state from `extensions_config.json`. The system prompt injects only enabled skills. Custom skills can be installed via `.skill` ZIP archives.

**Subagent delegation** uses dual thread pools (`_scheduler_pool` 3 workers + `_execution_pool` 3 workers) with a max of 3 concurrent sub-agents. The `task()` tool dispatches to `SubagentExecutor` which runs background threads, polls at 5s intervals, and emits SSE events (`task_started`, `task_running`, `task_completed`/`failed`/`timed_out`).

**Memory** is per-user, file-based, with LLM-based fact extraction, 30-second debounce, duplicate-sliding at apply time, atomic writes (temp file + rename), and fact confidence thresholding (0.7 default). Injected as `<memory>` tags in the system prompt (top 15 facts + context, 2000 token budget).

**Embedded Python client** (`DeerFlowClient`) provides in-process access to all capabilities without HTTP -- shares the same config files and data directories, and returns Gateway-aligned Pydantic response models.

---

## 2. Architecture & Core Modules

**Entry Points:**
- `backend/langgraph.json` -> `deerflow.agents:make_lead_agent` (the LangGraph graph definition)
- `backend/app/gateway/app.py` -> FastAPI application on port 8001
- `backend/packages/harness/deerflow/client.py` -> `DeerFlowClient` (embedded)

**Layer Architecture:**
```
Project Root: config.yaml, extensions_config.json, Makefile
  ├── backend/
  │   ├── packages/harness/deerflow/   (harness layer -- publishable as deerflow-harness)
  │   │   ├── agents/                   lead_agent/ + middlewares/ + memory/ + thread_state.py
  │   │   ├── sandbox/                  local/ + sandbox.py (ABC) + tools.py + middleware.py
  │   │   ├── subagents/                executor.py + registry.py + builtins/ + config.py
  │   │   ├── skills/                   storage.py + loader + tool_policy + parsing
  │   │   ├── models/                   factory.py + vllm_provider + patched providers
  │   │   ├── mcp/                      integration + cache + client
  │   │   ├── tools/builtins/           present_files, ask_clarification, view_image
  │   │   ├── community/                tavily, jina_ai, firecrawl, exa, aio_sandbox, etc.
  │   │   ├── config/                   app_config, agents_config, paths, extensions_config
  │   │   ├── reflection/               dynamic module loading (resolve_variable)
  │   │   ├── tracing/                  Langfuse + LangSmith callback wiring
  │   │   ├── runtime/                  run manager, stream bridge, worker, user_context
  │   │   └── client.py                 DeerFlowClient (embedded)
  │   ├── app/                          (application layer -- NOT publishable)
  │   │   ├── gateway/                  FastAPI: routers for models, mcp, skills, memory, uploads, threads, artifacts, suggestions, channels, runs, feedback
  │   │   └── channels/                 Feishu, Slack, Telegram, DingTalk, WeChat, WeCom, Discord
  │   ├── tests/                        277 tests
  │   └── docs/                         Architecture, Configuration, API docs
  ├── frontend/                         Next.js 16 + React 19 + TypeScript
  │   ├── src/app/                      Routes (landing, workspace/chats/[thread_id])
  │   ├── src/components/               UI + workspace components
  │   ├── src/core/                     Thread hooks, API client, artifacts, settings, memory, i18n
  │   └── tests/e2e/                    Playwright E2E tests
  ├── skills/public/                    20 built-in skill packs (deep-research, ppt-generation, image-generation, etc.)
  ├── docker/                           docker-compose-dev.yaml, Dockerfiles
  └── scripts/                          serve.sh, deploy.sh, docker.sh, etc.
```

**Key Design Pattern:** Middleware pipeline + LangGraph state graph. Each middleware implements `before_model` / `after_model` / `before_tools` / `after_tools` hooks. The order is critical and documented explicitly with the invariant "ClarificationMiddleware must be last."

**Data Flow:**
1. User input -> Frontend/LangGraph SDK -> Nginx (port 2026) -> Gateway API (port 8001)
2. Gateway creates run -> `run_agent()` -> builds graph with config -> invokes LangGraph
3. Lead agent receives prompt with injected memory + skills -> calls model
4. Model produces tool_calls -> middleware chain processes each -> tools execute in sandbox
5. Sub-agent tasks spawn via dual thread pools -> results merged back
6. Summarization middleware compresses history when token thresholds hit
7. Memory middleware queues async update after conversation turn
8. Stream events flow back: values, messages-tuple, custom, end

---

## 3. Performance / Benchmarks

The repo does not publish latency or throughput benchmarks. The following are gleaned from CI and documentation:

- **Backend test suite**: 277 tests pass in ~76.6s (ruff lint + pytest)
- **Sizing guide** (from README):
  - Light dev: 4 vCPU, 8 GB RAM, 20 GB SSD
  - Docker dev: 8 vCPU, 16 GB RAM, 25 GB SSD
  - Production server: 8+ vCPU, 16+ GB RAM, 40 GB SSD
- **Subagent concurrency**: MAX_CONCURRENT_SUBAGENTS = 3, dual thread pools at 3 workers each
- **Memory debounce**: 30s before processing queued updates (configurable)
- **Tool output protection**: 12KB threshold for externalizing to disk; 30KB fallback truncation
- **Loop detection**: warn at 3 repetitions, hard-stop at 5, within window of 20 messages
- **Sandbox LRU cache**: 256 entries for LocalSandbox per-thread instances
- **Config hot-reload**: mtime-based detection, reloads on next request (no restart needed for model/tool config changes)

---

## 4. Trade-offs (Wins vs Losses)

**Wins:**

1. **Skills as Markdown files** is brilliant for portability and LLM readability. Skills are simply SKILL.md with YAML frontmatter -- zero boilerplate, no API to learn. This is far more accessible than code-based plugin systems.

2. **Progressive skill loading** keeps context lean. Skills load only when the task needs them (by name in the system prompt). This is a direct answer to the context-window problem that plagues monolithic agent designs.

3. **Two-layer harness/app split** with a CI-enforced import firewall (deerflow.* never imports app.*). This is the cleanest separation of reusable framework from deployment-specific code I have seen in an agent project.

4. **Deferred MCP tool loading**: MCP tools are hidden from the model until the `tool_search` tool explicitly promotes them. This prevents hundreds of MCP tool schemas from consuming context budget on every turn.

5. **Sandbox abstraction** with virtual `/mnt/user-data/` paths provides a uniform filesystem contract across local, Docker, and Kubernetes backends. The `PathMapping` system means tool code never needs to know which provider is active.

6. **Embedded Python client** (`DeerFlowClient`) that shares return schemas with the HTTP Gateway and has CI-enforced conformance tests (`TestGatewayConformance`). This means agent programs can run in-process or over HTTP with identical APIs.

**Losses / Risks:**

1. **Complexity of 18 middlewares** is a maintenance hazard. The strict ordering dependency means adding a new middleware requires understanding all 17 existing ones. The docstring in `agent.py` describes the ordering twice in two different functions -- a code smell.

2. **Heavy LangChain/LangGraph dependency** locks the project into a specific framework's evolution. If LangChain changes its middleware API or graph semantics, DeerFlow must adapt. The `create_agent()` call is a LangChain-specific abstraction.

3. **No published benchmarks**. The README has deployment sizing but no latency numbers, no token efficiency statistics, no cost-per-task analysis. This makes it difficult to evaluate against alternatives.

4. **Memory system is file-based SQLite** with no vector database integration. For a project emphasizing "long-term memory," the implementation is surprisingly simple: JSON files with LLM-based fact extraction. No RAG, no embeddings, no semantic search over past facts.

5. **Frontend tightly coupled to LangGraph SDK**. The frontend uses `@langchain/langgraph-sdk` directly and assumes the Gateway speaks LangGraph SSE protocol. Replacing the backend would require rewriting the frontend.

6. **Config versioning (currently v11)** suggests frequent breaking changes in the config schema. The `make config-upgrade` workflow exists but adds maintenance burden for users.

7. **Security notice is prominent** for good reason. The sandbox's LocalSandboxProvider explicitly disables host bash by default because it is "not a secure isolation boundary." The AioSandboxProvider (Docker) is the production recommendation, but adds significant complexity.

---

## 5. Design Rationale

**Why LangGraph?** The README explicitly says the project started as a Deep Research framework and evolved. LangGraph provides the state-graph foundation (thread-level persistence via checkpointer, configurable streaming modes, node-based execution) that made the evolution from "research tool" to "agent harness" natural. The LangGraph `stream_mode` protocol also provides a clean contract for the frontend, IM channels, and embedded client to all consume the same events.

**Why the middleware pipeline?** Rather than baking safety, memory, summarization, and loop detection into the agent prompt (which is fragile and model-specific), DeerFlow extracts these concerns into composable middleware that runs before/after model calls and tool executions. This makes each concern independently testable, configurable, and swappable. The middleware order encodes a dependency graph (e.g., view_image must run after summarization because it re-adds image data; clarification must be last because it interrupts via `Command(goto=END)`).

**Why dual thread pools for sub-agents?** Sub-agents run as background tasks that the lead agent polls. The scheduler pool manages the polling/dispatch loop; the execution pool runs the actual sub-agent LangGraph calls. This separation prevents scheduling overhead from blocking execution and vice versa. The 3-concurrent limit is acknowledged as a deliberate scaling constraint to prevent resource exhaustion.

**Why file-based skills?** Skills are inherently static, prompt-sized knowledge modules. A Markdown file with YAML frontmatter is the simplest possible representation that is both human-editable and LLM-readable. Installing skills as `.skill` ZIP archives is a deliberate choice to avoid a package manager dependency.

**Why per-user memory isolation?** The migration to `users/{user_id}/memory.json` acknowledges that multi-user deployments are a primary use case. The fact that the embedded client and Gateway share the same per-user isolation logic means the system works identically in single-user embedded mode and multi-user server mode.

---

## 6. Transfer to Lyra

**Transferable Idea: Progressive Skill Loading with Markdown-file Skills + Deferred Tool Registry**

DeerFlow's skill system and deferred tool loading are the most directly transferable ideas to Lyra's architecture:

**The mechanism:**
1. Skills are directories containing a single `SKILL.md` file with YAML frontmatter (name, description, allowed-tools)
2. Skills live in `skills/public/` (committed) and `skills/custom/` (user-installed via `.skill` archives)
3. The system prompt lists enabled skills by name but does NOT include their full content
4. Only when the agent explicitly reference a skill (or a tool associated with one) does the full SKILL.md content get injected into context
5. MCP tools are similarly deferred: hidden from the model until `tool_search` promotes them

**How this maps to Lyra:**
- Lyra's current skill/plugin system could adopt the SKILL.md format (Markdown + YAML frontmatter) instead of a code-level plugin API. This lowers the barrier for creating new skills -- any user who can write a Markdown prompt can author a skill.
- Lyra's context budget management could adopt progressive loading: instead of loading ALL activated skills' content into every prompt, list them by name and inject content on demand.
- Lyra could adopt the `.skill` archive format for distributing community skills as self-contained ZIP files with metadata.

**Workstream Route:** This maps to **Section 4.2 (Agent Core / Runtime)** because it is about how the harness loads, selects, and injects skills into the agent's runtime context. It touches the system prompt construction, context management, and tool registry -- all core runtime concerns.

**Impact: High** -- Progressive skill loading directly addresses Lyra's context-bloat problem. The SKILL.md format would make skill creation accessible to non-developers. Deferred tool loading would prevent MCP server proliferation from consuming context.

**Effort: High** -- Requires redesigning the skill loading pipeline, the skill storage format, the system prompt construction logic, and the tool visibility mechanism. Would also require migration of existing Lyra skills.

**Tier: 1** -- This is a mid-to-long-term architectural enhancement. It is not a hotfix but a structural improvement to Lyra's extensibility model. It belongs in the Tier-1 roadmap alongside other architectural improvements.

**License:** MIT License -- compatible with Lyra. Full text in `LICENSE`.

---

**Note path:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/bytedance__deer-flow.md`
