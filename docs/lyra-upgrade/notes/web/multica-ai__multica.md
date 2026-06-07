# multica-ai/multica -- Deep-Read

## 1. Headline Feature & Mechanism

**Multica is an open-source managed-agents platform** -- "like Linear, but with AI agents as first-class citizens." It turns coding agents (Claude Code, Codex, GitHub Copilot CLI, OpenClaw, OpenCode, Hermes, Gemini, Pi, Cursor Agent, Kimi, Kiro CLI, Antigravity) into real teammates: assign an issue to an agent as you would a colleague, and the agent picks it up, writes code, reports blockers, and updates statuses autonomously.

**How the execution actually works (daemon-centric):**

1. A local daemon process runs on the user's machine, authenticates via a PAT, and registers one or more "runtimes" with the Go API server. Each runtime is a configured agent provider (e.g., "claude") with a detected CLI version.
2. The daemon runs a per-runtime poll loop (`runRuntimePoller`) that claims tasks from the server via HTTP, then spawns the agent CLI as a subprocess. The claim+dispatch cycle uses a slot semaphore (`MaxConcurrentTasks`) to avoid overloading the machine.
3. The agent runs in a cancellable context. A background goroutine (`watchTaskCancellation`) polls the server every 5s and kills the subprocess if the task is cancelled server-side or the task row is deleted.
4. Real-time progress streams from the agent subprocess back to the server via WebSocket, then fanned out through an in-memory Hub or (in multi-node mode) a Redis sharded-stream relay to frontend clients.
5. Every agent receives "built-in skills" -- markdown files embedded into the Go binary at compile time (e.g., `multica-working-on-issues/SKILL.md`) that teach the agent platform-specific workflows: how to link PRs, read linked-PR state, use metadata keys, etc.

**Squad mechanism:** Group agents (and humans) under a leader agent. Assign work to the squad; the leader decides who should pick it up. This keeps routing stable as the team grows.

**Autopilots:** Schedule recurring work for agents via cron triggers, webhooks, or manual runs -- each autopilot creates an issue and routes it to an agent automatically.

## 2. Architecture & Core Modules

```
                   +------------------+
                   |   Next.js 16     |
                   |   (App Router)   |
                   +--------+---------+
                            |
                    HTTP/WS | CORS
                            |
              +-------------+-------------+
              |   Go Backend (Chi + WS)   |
              |   server/cmd/server/      |
              +------+----------+---------+
                     |          |
              pgx/v5 |          | gorilla/websocket
              +------+---+  +--+-----------+
              | PG 17   |  | Daemon WS Hub |
              | pgvector |  +--+-----------+
              +----------+     |
                               | Redis relay (multi-node)
                               |
              +----------------+----------------+
              |       Daemon (local machine)    |
              |  server/internal/daemon/        |
              |  polls, claims, spawns agents   |
              +--+--------+--------+--------+---+
                 |        |        |        |
            claude    codex   copilot   gemini ...
              subprocesses (agent CLIs)
```

**Go backend (`server/`)**:
- `cmd/server/main.go` -- entry point. Wires DB pool, Redis, realtime Hub, event bus, background workers (runtime sweeper, heartbeat scheduler, autopilot scheduler, metrics server).
- `cmd/server/router.go` -- 1100-line Chi router with all middleware and routes: auth, daemon API, workspace-scoped CRUD for issues/agents/skills/squads/projects/runtimes.
- `internal/daemon/` -- the local agent runtime: task polling, claim, subprocess execution, heartbeat loop, auto-update, local skill import, repo cache sync.
- `internal/service/task.go` -- server-side task lifecycle: enqueue, dispatch, complete/fail, wakeup notification, analytics, metrics.
- `internal/handler/` -- HTTP handlers for every API endpoint, including `task_lifecycle.go` (RecoverOrphanedTasks, PinTaskSession).
- `internal/realtime/` -- WebSocket Hub, Redis relay (sharded stream + legacy dual-write), broadcaster abstraction.
- `internal/skill/` -- frontmatter parsing and reserved slug validation for workspace skills.
- `pkg/agent/` -- unified `Backend` interface for executing prompts via all supported agent CLIs. Each provider has its own file (claude.go, codex.go, copilot.go, etc.) implementing the subprocess invocation.
- `pkg/db/` -- sqlc-generated Go code from SQL queries.
- `pkg/protocol/` -- event/message types for agent-server communication.

**Frontend (`apps/web/`, `apps/desktop/`, `apps/mobile/`)**:
- Shared packages in `packages/`: `core/` (headless business logic, Zustand stores, TanStack Query), `ui/` (atomic shadcn components), `views/` (shared business pages).
- Desktop is an Electron app; mobile is Expo/React Native (iOS only currently).

**Monorepo tooling**: pnpm workspaces + Turborepo. All shared dependencies pinned via `catalog:` in `pnpm-workspace.yaml`.

**Key stack details**: Go 1.26.1, Chi v5 router, pgx v5, gorilla/websocket, Redis (go-redis/v9), S3 storage (fallback to local filesystem), Prometheus metrics.

## 3. Performance / Benchmarks

The repository does not publish any formal benchmarks or performance numbers. However, the code reveals several design decisions for performance:

- **Per-runtime goroutine isolation**: Each runtime gets its own poll loop and heartbeat ticker, so a slow HTTP claim (30s timeout) cannot block other runtimes. This directly fixed MUL-1744 (cross-workspace stall mode).
- **Runtime report retries**: Delivery of async results (model lists, local skills, updates) uses a retry schedule: 0ms, 500ms, 2s, 4s -- sum ~6.5s, staying under the 60s server-side timeout.
- **WS heartbeat suppresses HTTP heartbeat**: Fresh WS acks keep `last_seen_at` current without redundant HTTP writes. Freshness window is 2x heartbeat interval (default 30s). Two missed WS acks re-enable HTTP.
- **Empty claim cache**: Redis-backed cache for "this runtime has no queued task" -- skips a Postgres scan on the steady-state empty case.
- **Heartbeat batching**: `BatchedHeartbeatScheduler` queues runtime heartbeat bumps and flushes in batch, reducing DB write pressure.
- **Redis relay for realtime fanout**: Sharded stream relay supports multi-node deployments, with configurable shard count, stream max length, and XREAD count/block.
- **sqlc for all DB queries**: Compile-time SQL-to-Go codegen, no runtime ORM overhead. All queries filter by `workspace_id`.

## 4. Trade-offs

### Wins

1. **Vendor-neutral agent abstraction**: The `pkg/agent.Backend` interface lets Multica work with 11+ different coding agents. Adding a new provider means implementing one interface (Execute + ListModels + DetectVersion). This is a genuinely useful abstraction -- Lyra could benefit from a similar provider abstraction.

2. **Built-in skills system**: Embedding SKILL.md files in the Go binary that teach agents platform-specific behavior is elegant. Every agent automatically gets these skills at compile time, no DB round-trip. The skills are markdown with YAML frontmatter, which agents natively understand.

3. **Daemon-side task polling + WS wakeup**: Rather than requiring the server to SSH into machines, the daemon polls for tasks. The WebSocket path provides real-time wakeup (sub-second latency) while the HTTP poll loop is the fallback. This is both simpler to deploy and more resilient.

4. **Squad routing**: Hierarchical agent delegation where a leader agent routes work to members is a clean solution for team scaling. Leaders get a "briefing" context that summarizes squad state.

5. **Polymorphic assignees**: Issues carry `assignee_type` + `assignee_id`, so the same field works for humans and agents. This simplicity in data model is a big win over separate assignment systems.

6. **Autopilot system**: Scheduled recurring work via cron/webhook triggers that creates issues and routes to agents. Useful for daily standups, weekly reports, periodic audits.

### Losses / Risks

1. **Daemon dependency**: Every agent execution requires a running daemon on the target machine. This means the daemon must be installed, configured, and kept alive. Cloud runtime is mentioned but appears to be SaaS-only (self-host docs show 503 for cloud-runtime endpoints without SaaS config).

2. **PostgreSQL + Redis hard dependency**: Self-hosting requires both PG 17 with pgvector AND Redis. This is heavy for small teams. The in-memory Hub works for single-node, but Redis is required for multi-node and rate limiting.

3. **No air-gapped mode**: The daemon always needs connectivity to the Multica server to claim tasks. Offline execution is not supported. This is acknowledged in the architecture (heartbeat timeout = 45s before sweeper marks runtime offline).

4. **Complex self-hosting**: The self-hosting guide is 5 separate markdown files (SELF_HOSTING.md, SELF_HOSTING_AI.md, SELF_HOSTING_ADVANCED.md, plus Docker Compose configs). The CLAUDE.md itself is 400+ lines of conventions. This project has significant operational complexity.

5. **Electron desktop app**: The desktop app (Electron with electron-vite) introduces platform-specific complexity: tab isolation, WindowOverlay state, drag regions, workspace context management. The CLAUDE.md documents several bugs from this architecture (route categories, workspace destructive operations ordering, cross-workspace tab leakage).

6. **No built-in memory/persistence for agent state**: Tasks are ephemeral -- once completed, the agent session ends. Resume is supported (session_id + work_dir pinning), but there's no agent-level long-term memory that persists across tasks. Each task starts with the built-in skills and any workspace skills.

7. **CLI version coupling**: The server and CLI versions must be compatible. The update flow (auto-update via Heartbeat) and version detection (agent.DetectVersion) add operational surface area.

## 5. Design Rationale

The README explicitly draws the analogy to **Multics** -- the 1960s operating system that introduced time-sharing. The bet is that the same inflection is happening for software teams: the "single-threaded engineer" model is giving way to multiplexed human + AI teams. The name (Multica = **Mul**tiplexed **I**nformation and **C**omputing **A**gent) encodes this philosophy.

**Key design decisions and their rationale:**

- **Daemon architecture over server-side SSH**: The daemon polls because the server cannot initiate SSH connections into arbitrary developer machines. This is a practical concession to network topology -- developers are behind NATs, VPNs, and firewalls. The WebSocket path provides the low-latency reverse tunnel.

- **Skills as markdown over code**: Rather than hardcoding agent behavior in Go, skills are natural-language markdown files with YAML frontmatter. Agents (especially Claude Code and similar) are trained to follow written instructions. This means skills can be authored by non-Go developers and iterated without recompiling the binary for user-created skills (built-in skills still need recompile).

- **Squads over flat agent pools**: As the team scales, routing becomes a bottleneck. Squads introduce a hierarchy where the leader agent makes routing decisions autonomously, informed by a briefing of squad member capabilities and current load.

- **Modified Apache 2.0**: The license is explicitly designed to prevent SaaS competitors from hosting Multica as a service, while allowing internal enterprise use and individual self-hosting. This is a deliberate business model choice -- Multica AI, Inc. sells cloud hosting and commercial licenses.

## 6. Transfer to Lyra

### Transferable Idea: Built-in Skills as Agent Instruction Infrastructure

Multica's built-in skills system is directly transferable to Lyra. The concept: ship natural-language markdown files that teach agents about the platform itself -- not as documentation for humans, but as machine-readable instructions that every agent loads before starting work.

Lyra could embed a directory of `LYRA_SKILLS/` at build time, where each skill teaches agents about a Lyra subsystem:
- `lyra-architecture.md` -- overall system architecture, key abstractions, extension points
- `lyra-commands.md` -- how to create, invoke, and discover commands
- `lyra-memory.md` -- the memory subsystem contract: read/write semantics, persistence guarantees
- `lyra-plugins.md` -- plugin API, lifecycle hooks, sandbox model
- `lyra-context.md` -- how context is assembled, prioritization, budget management

This is stronger than documentation because:
1. Agents read it automatically -- no context-window waste asking the user for docs
2. It's version-locked to the binary -- agent behavior stays in sync with the code
3. It's authorable in natural language -- no API changes needed to update agent guidance
4. Each skill can have a `references/` directory with source-code maps for ground truth

The key insight is that **agents learn from what they read**, so writing the right instructions as markdown is a cheaper and more flexible mechanism than coding them in Go/Python.

### Route and Impact

- **Workstream route**: SS4.x (Agent Runtime) -- the skills infrastructure lives in the agent runtime layer, not in the core engine or orchestration.
- **Impact**: 6/10 (medium-high). Gives Lyra agents reliable knowledge of the Lyra platform without hardcoding behavior. Reduces "agent doesn't know how to use Lyra commands" support burden. Compounds over time as more skills are added.
- **Effort**: 3/10 (low). The pattern is simple: embed a directory, read it at startup, inject into agent context. No new APIs, no state machines, no database schemas. Rough estimate: 2-3 days for the infrastructure, 1 day per skill.
- **Tier**: Tier 2 (Phase 2 -- after core agent execution works, this is a force multiplier).

Implementation sketch for Lyra:
```
lyra/
  skills/                          # built-in skills directory
    lyra-plugins/SKILL.md          # How to list/install/create plugins
    lyra-commands/SKILL.md         # How to create/invoke/discover commands
    lyra-memory/SKILL.md           # Memory subsystem contract
    lyra-context/SKILL.md          # Context assembly and budget
    lyra-architecture/SKILL.md     # Overall system tour
  pkg/skill/
    embed.go                       //go:embed skills/*/SKILL.md
    loader.go                      // parses frontmatter, loads content
```

### License

Modified Apache 2.0 with a commercial-use restriction on SaaS hosting and logo removal. Non-commercial internal use is Apache 2.0. The restriction pattern is similar to what Lyra may want: it allows individual/enterprise use while protecting against SaaS copying.
