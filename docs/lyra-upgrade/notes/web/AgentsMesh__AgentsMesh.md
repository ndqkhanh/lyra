# AgentsMesh/AgentsMesh -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline Feature:** A distributed AI Agent Workforce Platform -- deploy, coordinate, and monitor multiple AI coding agents (Claude Code, Codex CLI, Gemini CLI, Aider, OpenCode) on self-hosted remote infrastructure through a unified web console.

**How it really works:**

The system separates control plane from data plane. The Go backend (Gin+GORM) owns all orchestration logic: auth, org/team/user hierarchy, pod lifecycle, ticket kanban, channel collaboration, and billing. Communication with self-hosted Runners uses gRPC bidirectional streaming with mTLS client certificates issued by the backend's internal PKI. Terminal I/O (the "data plane") flows through a separate Relay cluster via WebSocket binary protocol -- the backend never touches raw PTY bytes.

The Runner is a lightweight Go daemon installed on user machines. Once registered and authenticated via mTLS, it receives `create_pod` commands over the gRPC stream. Each Pod is an isolated execution environment with a PTY terminal (via `creack/pty`) or ACP (Agent Communication Protocol) session backed by a git worktree sandbox. The Runner builds pods using a Builder pattern -- it resolves the AgentFile DSL (a declarative config that declares ENV, EXECUTABLE, MCP, SKILLS, MODE, CONFIG), clones the repository, injects credentials, and spawns the agent CLI process. Terminal output is captured, processed through a SmartAggregator with bandwidth-aware throttling, and fanned out to both the cloud Relay and a local browser relay.

A Rust Core crate (`clients/core/`) acts as the single source of truth for all client business logic. It compiles to WASM for the Next.js web frontend and to a native XCFramework via UniFFI for the iOS app. The web frontend loads a 21MB wasm blob at boot and all state is derived from Rust selectors triggered by a `_tick` mechanism -- the React/Zustand stores are thin view mirrors, not source of truth.

Key behaviors include: Perpetual mode (auto-restart agent on clean exit), Loop (cron-triggered CI/CD for AI agent tasks), Autopilot (circuit-broken iterative execution), Channel (multi-pod group chat with @mention prompt forwarding), and Mesh (dynamic runtime topology of active pods + pod bindings).

## 2. Architecture & Core Modules

**Entry points:**
- `backend/cmd/server/main.go` -- Backend API server entry (Go). Initializes config, logger, OpenTelemetry, database, infrastructure (Redis event bus, WebSocket hub), services (pod, channel, ticket, runner, loop, autopilot), gRPC with mTLS PKI, and HTTP+Connect-RPC server. ~190 lines.

- `runner/cmd/runner/main.go` -- Runner CLI entry (Go). Routes subcommands: `register`, `run`, `service`, `update`, `reactivate`, `webconsole`. The `run` subcommand initializes dependencies (gRPC connection, workspace, certs) then creates a Runner struct and calls `Run(ctx)`. ~108 lines.

- `relay/cmd/relay/main.go` -- Standalone terminal relay server (Go). WebSocket pub/sub between Runners and browsers. ~1 file.

**Data flow:**
```
Browser (Next.js)  --REST/WS-->  Backend (Go+Gin+gRPC)
                                     |
                            gRPC+mTLS bidi stream
                                     |
                                  Runner (Go daemon)
                                     |
                      +-------+------+------+--------+
                      |       |             |        |
                   Pod PTY  ACP Session  WebSocket  MCP
                      |       |           Relay     Server
                      +-------+------+------+
                                 |
                         Relay Cluster (WS)
                                 |
                             Browser xterm.js
```

**Core modules:**

| Module | Path | Lines/files | Purpose |
|--------|------|------------|---------|
| Backend | `backend/` | 2663 .go files | API server, domain models (DDD), services, infra |
| Runner | `runner/` | ~130 files in internal/runner | Pod lifecycle, sandbox, gRPC client, PTY/ACP |
| Relay | `relay/` | ~20 .go files | WebSocket terminal relay cluster |
| Proto | `proto/` | 56 .proto files | 39 gRPC service definitions |
| Web | `clients/web/` | 1758 .ts/.tsx files | Next.js 16 App Router, WASM-backed |
| Core | `clients/core/` | 328 .rs files | Rust SSOT, compiled to WASM + native |
| Desktop | `clients/desktop/` | Electron | Reuses web source + Rust native NAPI |
| iOS | `clients/ios/` | SwiftUI+TCA | UniFFI-generated bindings to Rust Core |

**Architecture pattern:** Control/Data plane separation + DDD-layered backend + SSOT Rust core + Bazel monorepo.

The backend follows DDD with domain entities in `backend/internal/domain/`, business logic in `backend/internal/service/`, infrastructure in `backend/internal/infra/`, and REST handlers in `backend/internal/api/rest/`. Wire format is evolving from REST to Connect-RPC (protobuf). The Runner uses a Supervisor pattern (`thejerf/suture/v4`) for service lifecycle management, Builder pattern for pod construction, and Strategy pattern for sandbox setup strategies.

**Build system:** Bazel monorepo. Go services built via `rules_go`, Rust via `rules_rust`, Next.js via custom `nextjs_bundle` macro, iOS via `ios_app` macro. Legacy Docker Compose dev environment remains as fallback.

## 3. Performance/Benchmarks

**From RFC-001 (100K Runner Architecture):**

- Target: 100,000 concurrent Runner gRPC connections, 300,000 active AgentPods
- Heartbeat latency target: P99 < 500ms
- Availability target: > 99.9%
- Identified bottlenecks:
  - ConnectionManager single global `sync.RWMutex` shared across all connections -- lock contention estimated to increase latency 10-100x at scale
  - DB connection pool hardcoded to `SetMaxOpenConns(100)` -- severely undersized for 10K writes/sec (heartbeat at 30s interval = 3,333 UPDATE/sec, pod sync ~10,000 queries/sec)
  - TerminalRouter memory pressure from buffering large terminal frames

**From RFC-004 (Terminal Bandwidth Optimization):**

- Claude Code single frame: ~880KB
- Frame rate: ~0.85 fps
- Bandwidth: ~800 KB/s
- 7-minute session: ~113 MB total
- VT Serialize mode targets 30-50% per-frame reduction
- Bandwidth-aware sliding window throttling already deployed: detects high-frequency full-redraw patterns, adjusts throttle window 1-4 seconds, targets 70-90% traffic reduction in high-frequency scenarios

**Test suite:**
- 1,187 Go test files
- 1,510 Vitest unit tests (web frontend)
- Integration tests for pod lifecycle, message handlers, relay, ACP, upgrade
- E2E tests via Playwright

## 4. Trade-offs

**Wins:**

1. **True multi-tenant isolation** -- Organization > Team > User hierarchy with row-level SQL policies enables enterprise-grade tenant isolation.

2. **Self-hosted runners** -- User code never leaves user infrastructure. Runner is a lightweight Go binary vs. a full container. BYOK (Bring Your Own Key) model gives users full cost control.

3. **Multi-agent flexibility** -- Supports Claude Code, Codex CLI, Gemini CLI, Aider, OpenCode, and any custom terminal-based agent. Users are not locked into a single AI provider.

4. **Rust Core SSOT** -- Business logic written once in Rust, compiled to WASM (web), native NAPI (Electron), and XCFramework via UniFFI (iOS). Eliminates duplicate logic across three frontend codebases.

5. **Pod daemon architecture** -- Separate daemon process holds the PTY file descriptor, surviving Runner restart. Enables session persistence, perpetual mode (auto-restart), and clean state recovery.

6. **AgentFile DSL** -- Declarative pod configuration that separates concerns: ENV variables, executable choice, MCP server config, skills, and interaction mode. Version-controllable and shareable.

7. **Comprehensive monitoring** -- OpenTelemetry instrumentation across all Go services, Jaeger for distributed tracing, structured logging, audit logging for admin actions.

**Losses / Pain Points:**

1. **Terminal bandwidth is extreme** -- ~880KB per Claude Code frame, ~800KB/s sustained. Bandwidth-aware throttling helps but VT Serialize mode and other optimizations are still being deployed.

2. **9-layer data architecture** -- Data passes through DB -> GORM -> Proto wire -> Rust cache -> wasm bridge -> Web TS -> UniFFI -> iOS Swift. 258 legacy Rust structs + 131 UniFFI records + 15 handwritten TS interfaces. ~2,200 lines of hand-written conversion boilerplate. Each `list_pods` call does 4-5 serde_json conversions across wasm/JS boundary.

3. **No pod privacy** -- Any org member can see all pod terminal output. No Pod ownership concept.

4. **No private channels** -- Channels are org-visible by default, no member list restriction.

5. **API key scopes defined but unenforced** -- Scope definitions exist in code but middleware does not check them.

6. **Bazel migration in progress** -- Dual build system (legacy dev.sh Docker Compose + Bazel) increases CI complexity and onboarding friction. Migration is incremental, meaning some targets use Bazel while others still use the legacy path.

7. **Runner upgrade complexity** -- Self-update mechanism requires process re-exec, PID file management, and a separate PodDaemon to survive restart. The CHANGELOG documents several race conditions and permission escalation bugs in the upgrade path.

## 5. Design Rationale

**Why control/data plane split?** The backend should never handle raw terminal bytes at scale. By routing terminal I/O through a dedicated Relay cluster, the backend's event loop stays focused on orchestration commands and can be horizontally scaled independently of the data plane. This is the same principle that separates signaling from media in VoIP systems.

**Why self-hosted runners?** Enterprise customers will not send source code to a third-party cloud. By keeping the Runner on user infrastructure and only connecting via gRPC+mTLS, AgentsMesh provides the SaaS convenience of a web console without the data residency objection.

**Why Rust Core SSOT?** Duplicating business logic across Web (TS), Desktop (Electron/TS), and iOS (Swift) creates a maintenance nightmare where behavior diverges across platforms. Compiling shared Rust to both WASM and native eliminates this. The 21MB wasm cost is paid at dashboard load -- marketing pages stay wasm-free.

**Why Bazel?** A monorepo with Go, Rust, TypeScript, Swift, and protobuf needs a single build system that understands cross-language dependencies. Bazel's remote caching, incremental builds, and hermetic execution make CI reproducible across languages.

**Why Pod as universal execution unit?** All system entities (Ticket, Channel, Loop, Autopilot) revolve around the Pod. This simplifies the mental model: there is exactly one way to execute work, and everything else is context or orchestration around it.

**Why AgentFile DSL vs. fixed config?** AI agent capabilities evolve faster than platform releases. A declarative DSL lets users and organizations define custom agent configurations (which MCP servers, which skills, which environment variables) without waiting for platform features.

## 6. Transfer to Lyra

**Transferable Idea: Declarative Agent Manifest (AgentFile DSL)**

AgentsMesh's AgentFile DSL provides a declarative, version-controllable configuration format for AI agent pods. It separates the concerns of environment (ENV), executable choice (EXECUTABLE), tool extensions (MCP, SKILLS), interaction mode (MODE: pty/acp), and runtime config (CONFIG) into a single unified manifest. Pods are instantiated purely from this declaration + platform-level references (repo, credentials).

For Lyra, this maps to a **declarative agent manifest** -- a YAML/JSON file that describes what an agent is, what tools it has, what runtime it uses, and what environment variables it needs. This would enable:

1. Reproducible agent environments checked into version control alongside the codebase
2. Sharing of agent configurations across teams via a registry or marketplace
3. Decoupling agent capability definition from the Lyra core runtime
4. Natural extension points for per-organization custom agents

**Workstream route: Section 4.1 (Agent Registry & Loading)**

The AgentFile concept fits naturally into Lyra's agent registry. Instead of hardcoding agent types, the registry would load manifests from a well-known path (e.g., `.lyra/agents/manifest.yaml`), resolve MCP tool references, validate against a schema, and instantiate the agent runtime accordingly.

| Dimension | Value |
|-----------|-------|
| **Impact** | 5/10 -- Clear quality-of-life improvement, reduces agent config sprawl, enables sharing. Not a fundamental architecture rewrite. |
| **Effort** | 4/10 -- Needs: manifest schema definition, resolver/loader, validation, migration from current inline config. The Go implementation pattern is well-documented in the AgentsMesh runner code. |
| **Tier** | 2 -- A solid mid-priority improvement. Easy to prototype, demonstrable value, low risk. |
| **License** | BSL-1.1 (Business Source License 1.1). Change date 2030-02-28, change license GPL-2.0-or-later. Non-production use permitted, production use requires commercial license until change date. The ideas and architectural patterns are not copyrightable; the specific AgentFile parsing and resolution implementation would need clean-room reimplementation under Lyra's license. |
