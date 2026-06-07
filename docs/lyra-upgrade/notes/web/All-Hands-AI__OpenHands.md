# All-Hands-AI/OpenHands -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline Feature:** OpenHands is an AI-powered software engineering platform that runs LLM-based agents inside isolated sandbox environments (Docker containers, local processes, or remote hosts) to autonomously write code, execute bash commands, browse the web, interact with Git hosting platforms (GitHub, GitLab, Bitbucket, Azure DevOps), and create PRs -- all driven by a FastAPI backend and a React single-page frontend.

**How It Works (Data Flow):**

1. A user creates a "conversation" via the REST API (`/api/v1/conversations`). The request specifies an LLM profile, an agent type (e.g., CodeActAgent), and optional repository/skill references.
2. The app server starts a **sandbox** -- a Docker container (or local process, or remote host) running the `agent-server` image. Each sandbox gets its own API key, working directory, and environment variables (provider tokens, CORS config, webhook callbacks).
3. Within the sandbox, an **agent loop** runs: it receives user messages, invokes the configured LLM (via litellm), executes tool calls (bash, file editing, browser, git, MCP), and streams events back to the app server via HTTP.
4. Events are persisted (to filesystem, AWS S3, or GCP) for resume and audit. An optional SQL event callback service processes events for webhook delivery.
5. The agent has access to an MCP server running in the app server process that exposes tools like `create_pr`, `create_mr`, `create_bitbucket_pr` -- proxied into the sandbox so agents can interact with Git providers without exposing API tokens.
6. Skills (markdown files in `skills/` directory) define agent prompts, tool sets, and trigger keywords. They are loaded at sandbox start and merged into the agent's system prompt.

**Key Architectural Insight:** OpenHands V1 (this repo) separates the **app server** (user-facing FastAPI) from the **agent server** (sandboxed execution). The `openhands` Python package in this repo is a namespace package that imports from three separate packages: `openhands-sdk`, `openhands-tools`, and `openhands-agent-server` (all version 1.25.0). The app server communicates with agent-server containers via HTTP, creating a clean isolation boundary.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

### Entry Points

| File | Role |
|------|------|
| `openhands/app_server/app.py` | FastAPI app creation, lifespan management, MCP mount, middleware |
| `openhands/server/__main__.py` | DEPRECATED -- legacy uvicorn runner (points to `openhands.server.listen:app`) |
| `openhands/app_server/v1_router.py` | Root API router assembling all sub-routers under `/api/v1` |
| `openhands/app_server/config.py` | Global config factory from env vars; DI injector wiring |
| `frontend/src/entry.client.tsx` | React SPA entry point |

### Core Modules

| Module | Size | Responsibility |
|--------|------|----------------|
| `app_server/app_conversation/` | ~16 files (104KB main impl) | Conversation lifecycle: start, resume, send messages, list, delete. Core logic: `LiveStatusAppConversationService` (104KB) orchestrates sandbox start, agent creation, event streaming, skill loading, resume from history |
| `app_server/sandbox/` | 17 files | 3 sandbox implementations: **Docker** (27KB), **Process** (16KB), **Remote** (37KB). `SandboxService` is the abstract base; each provides `start_sandbox`, `resume_sandbox`, `get_sandbox`, health-check polling. Docker is the default; Process is for `RUNTIME=local`; Remote for cloud-hosted agent servers |
| `app_server/event/` | 8 files | Event persistence: `FilesystemEventService` (local JSON files), `AwsEventService` (S3), `GoogleCloudEventService` (GCS). Events are stored as individual JSON files per event |
| `app_server/event_callback/` | 8 files | Webhook delivery and post-event processing (e.g., auto-set conversation title from first user message) |
| `app_server/integrations/` | 14 dirs | Git provider integrations: GitHub, GitLab, Bitbucket, Bitbucket DC, Azure DevOps, Forgejo. `provider.py` (27KB) is the central token/service factory |
| `app_server/mcp/` | `mcp_router.py` | FastMCP server exposing `create_pr`, `create_mr`, `create_bitbucket_pr`, `create_bitbucket_data_center_pr`, `create_azure_devops_pr` tools. Also proxies Tavily search API |
| `app_server/settings/` | 6 files | LLM profile management, settings CRUD, LiteLLM proxy configuration |
| `app_server/services/` | 7 files | DI infrastructure: `Injector` base class, `DbSessionInjector`, `HttpxClientInjector`, `JwtService` |
| `app_server/user/` | 9 files | User context, skills CRUD, user management |
| `app_server/user_auth/` | 3 files | Authentication/authorization middleware |
| `app_server/secrets/` | 5 files | Secret management (env vars injected into sandbox) |
| `app_server/analytics/` | 8 files | PostHog analytics integration (+ OSS install ID tracking) |

### Architecture Pattern

**Layered Service Architecture with Dependency Injection:**
- **FastAPI** serves as the HTTP framework with middleware (CORS, rate limiting, auth, cache control)
- **global config** is built once from env vars (`config_from_env()`) and cached; all routes use `Depends()` to inject services
- **Injector pattern**: Each service has an abstract interface, a concrete implementation, and an `Injector` class. Injectors can be composed/overridden per deployment. The `Injector` base class provides `inject()` async generator, `context()` context manager, and `depends()` FastAPI dependency
- **Sandbox abstraction**: Three implementations (Docker, Process, Remote) share the same `SandboxService` ABC. The config selects one based on `RUNTIME` env var
- **Event storage abstraction**: Three backends (local filesystem, S3, GCS) behind `EventService` ABC
- **Namespace package**: This repo's `openhands/` extends via `pkgutil.extend_path` to merge with `openhands-sdk`, `openhands-tools`, `openhands-agent-server` installed packages

### Frontend

React SPA with Remix (react-router v7), Tailwind CSS v4, Zustand state management, TanStack Query, Monaco editor, xterm.js terminal, Socket.IO for real-time event streaming. 27 directories, 115 icons, 59 hooks.

## 3. Performance/Benchmarks (real numbers from the repo)

The README badge reports **SWE-bench 77.6%** (linked to a Google Sheets scorecard).

Additional benchmark references are external:
- [Evaluation infrastructure](https://github.com/OpenHands/benchmarks) (separate repo)
- [Tech report on arXiv](https://arxiv.org/abs/2511.03690)

The `CREDITS.md` references SWE-bench in the context of rating contributions. The `CONTRIBUTING.md` contains a link to the benchmarks repo.

No benchmark execution code lives in this repository -- it is a separate project.

The codebase contains performance-related constants:
- `_ACP_RESUME_MAX_EVENTS = 200` (hard cap on events fetched for resume)
- `_ACP_RESUME_CONTEXT_MAX_CHARS = 60_000` (total resume block char limit)
- `_ACP_RESUME_MESSAGE_MAX_CHARS = 8_000` (per-message char limit for resume)
- `_ACP_RESUME_TOOL_MAX_CHARS = 2_000` (per-tool-event char limit)
- `InMemoryRateLimiter(requests=10, seconds=1)` (API rate limiting)
- `wait_for_sandbox_running` default timeout: 120s, poll interval: 2s
- `STARTUP_GRACE_SECONDS = 15` (Docker sandbox startup grace period, configurable)

## 4. Trade-offs (wins vs losses -- from issues, design decisions, complexity)

### Wins

1. **Sandbox isolation is first-class.** Three sandbox implementations mean users can choose isolation level: Docker (max security), local processes (fast, for development), or remote hosts (for scale). The `SandboxService` abstraction makes this transparent to the rest of the system.

2. **Modular V1 architecture.** The split into `app_server`, `sdk`, `tools`, and `agent-server` as separate packages enables independent versioning, independent deployment, and clean API boundaries.

3. **Provider-agnostic LLM support.** Using litellm means any LLM provider works with the same code. The `openhands/` and `litellm_proxy/` model prefixes support deployment-specific proxy routing.

4. **Enterprise features are genuinely source-available.** The `enterprise/` directory contains real SaaS features: Keycloak auth, Slack/Jira/Linear integrations, RBAC, billing, analytics. It's not vaporware.

5. **Skills system is powerful.** Skills are markdown files with YAML frontmatter defining triggers, tool requirements, and agent prompts. They can be loaded per-conversation, making the agent behavior programmable without code changes.

6. **Comprehensive Git provider support.** GitHub, GitLab, Bitbucket, Bitbucket DC, Azure DevOps, Forgejo -- all with their own service implementations, token management, and PR/MR creation.

7. **DI-based service architecture** enables swapping implementations (e.g., event storage backend) without changing business logic.

### Losses / Complexity

1. **Docker dependency is hard.** The default runtime requires Docker Desktop (or equivalent). Without Docker, only the `process` sandbox works, which lacks isolation. The startup overhead of Docker containers makes conversation initialization non-trivial (120s default timeout).

2. **Namespace package complexity.** The `openhands` namespace is split across 4 packages (`openhands`, `openhands-sdk`, `openhands-tools`, `openhands-agent-server`). Missing any one breaks imports. The `extend_path` approach is fragile and makes local development tricky.

3. **Event storage as individual JSON files.** The filesystem event store creates one JSON file per event. For conversations with hundreds of events, this means thousands of files, slow `search_events` (runs `os.listdir` + individual JSON loads), and fragmentation. The S3/GCP backends mitigate this for production.

4. **Heavy dependency footprint.** `pyproject.toml` lists ~80+ dependencies including Docker, playwright, kubernetes, multiple cloud SDKs, MCP, Tree-sitter, Jupyter kernels, etc. Many of these are only relevant in specific deployment configurations.

5. **V0/V1 migration baggage.** The codebase has legacy `server/` modules that are marked DEPRECATED. Multiple env var fallback paths (e.g., `FILE_STORE_PATH` vs `OH_PERSISTENCE_DIR`) add maintenance surface.

6. **Conversation router is massive.** `app_conversation_router.py` is 56KB -- one file handling all conversation CRUD, message sending, streaming, and lifecycle. This is a single-responsibility violation.

7. **Resume logic is complex.** The resume mechanism (`_ACP_RESUME_*` constants, `load_and_merge_all_skills`, event replay) tries to reconstruct full agent state from past events. The code has explicit guards against double-resume and uses hard limits to prevent O(N) fetches, indicating this has been a pain point.

## 5. Design Rationale (why this approach)

1. **Why a separate agent-server container?** Security isolation. The LLM runs tool calls that could be destructive (file writes, git pushes, npm publish). Running these in a separate container that can be destroyed and recreated ensures the app server is never compromised. This also enables the "resume" feature -- if the sandbox dies, a new one can start and replay events.

2. **Why namespace packages?** Clean separation of concerns. The SDK (`openhands-sdk`) defines the core agent abstractions (Agent, LLM, Event). The tools package (`openhands-tools`) defines built-in tools (bash, file editor, browser). The agent-server (`openhands-agent-server`) is the runtime. The app-server (`openhands`) is the user-facing API. They version independently.

3. **Why multiple sandbox implementations?** Progressive complexity. Docker is the default for production-like isolation. Process sandbox enables fast iteration without Docker (just Python). Remote sandbox supports cloud deployments where containers are managed by Kubernetes. Each is a different deployment model, not a different architecture.

4. **Why events, not state?** Full audit trail. By storing every event as an immutable JSON object, OpenHands supports replay, debugging, and resume. The event store is append-only -- no state mutations. Event callbacks (webhooks, title-setting) are side-effect processors that fire asynchronously.

5. **Why MCP for git operations?** API key isolation. Rather than passing GitHub tokens into the sandbox (where a rogue agent could read them), the app server exposes an MCP server with `create_pr` etc. The sandbox agent calls these tools via MCP, and the app server makes the API calls using stored tokens. The agent never sees the raw token.

6. **Why "conversations" as the core abstraction?** OpenHands models each user interaction as a conversation -- a sequence of user messages, agent responses (which may include tool calls), and events. This maps naturally to the UI (chat interface), the event store (append-only event sequence), and the sandbox lifecycle (one sandbox per conversation).

## 6. Transfer to Lyra (one idea + section 4.x route + Impact/Effort/Tier + LICENSE)

### Transferable Idea: **Sandboxed Agent Execution with Isolation Abstraction**

OpenHands demonstrates that you can build a generic **agent execution sandbox** with multiple backends (Docker, local process, remote host) behind a single `SandboxService` interface, and cleanly separate the orchestration layer from the execution layer via HTTP.

**For Lyra:** Lyra currently runs agents in-process. Implementing a `SandboxService` abstraction would allow Lyra to:
- Run agents in Docker containers for security isolation (preventing file system damage from tool calls)
- Support local "process" mode for development/testing without Docker
- Support remote sandbox execution for cloud deployments
- Use MCP for tool execution across the sandbox boundary (as OpenHands does for Git provider operations)

### Workstream Route

**Section 4.x route:** `§4.7 Infrastructure / Deployment` -- the sandbox isolation abstraction fits naturally into the deployment and infrastructure workstream, alongside containerization and environment management.

### Impact / Effort / Tier

- **Impact:** 8/10 -- Sandbox isolation is a foundational capability that unlocks safe multi-agent execution, cloud deployment, and production-grade security. Without it, Lyra cannot safely run arbitrary agent tool calls.
- **Effort:** 7/10 -- Requires defining the `SandboxService` interface (1-2 days), implementing the process sandbox (3-5 days), implementing the Docker sandbox (5-10 days including Docker image builds), and retrofitting the existing agent loop to communicate with sandboxes via HTTP (5-7 days). Total: ~3-4 weeks for a solid first version.
- **Tier:** Tier 3 (Foundation) -- This is foundational infrastructure that other features build on. It should be implemented before multi-agent collaboration or cloud deployment.

### License

**MIT License** (core), with source-available license for `enterprise/` directory. The MIT license covers all code outside `enterprise/`, including the `openhands` package, frontend, skills, and Docker images. This means Lyra can freely use, modify, and distribute the core ideas without licensing restrictions.
