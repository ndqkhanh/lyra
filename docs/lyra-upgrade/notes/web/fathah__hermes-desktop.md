# fathah/hermes-desktop — Deep-Read

## 1. Headline Feature & Mechanism

**Hermes Desktop** (also branded "Hermes One") is a native Electron desktop GUI for the Hermes Agent CLI — a self-improving AI assistant built by Nous Research. The headline feature is a **guided first-run installer + graphical chat UI** that replaces the raw Hermes CLI workflow. Instead of managing a Python CLI by hand (install, configure `.env`, start gateway, chat in terminal), the desktop app provides a React-based streaming chat interface with SSE streaming, tool progress indicators, slash commands, session management (SQLite FTS5), profile isolation, token tracking, and a 12-screen management UI.

**How it really works:**

The app is an Electron shell (three-process model: main/preload/renderer) that wraps the Hermes Agent Python gateway. On first launch:

1. If local mode is selected, the app runs the official Hermes install script (`curl install.sh | bash`) with `--skip-setup`, capturing stdout/stderr and feeding it to a React progress component.
2. After install, it starts a Python gateway process (`hermes gateway`) for the active profile, binding to a unique per-profile port (range 8642-8742).
3. Chat requests go via HTTP SSE to the profile's local gateway API server at `http://127.0.0.1:<port>/v1/chat/completions`, using the OpenAI-compatible streaming format.
4. Three transport layers exist, selected in priority order: **TuiGatewayClient** (WebSocket JSON-RPC to the gateway's dashboard protocol), **HTTP API** (direct SSE to `/v1/chat/completions` or the newer `/v1/runs` "Hermes Runs" transport), and **CLI fallback** (spawns `hermes chat -q "<message>"`).

The app can also be configured in **remote mode** (point at a remote Hermes API server) or **SSH tunnel mode** (connect via SSH, start a local tunnel, and proxy all API calls through it).

## 2. Architecture & Core Modules

**Stack:** Electron 39 + React 19 + TypeScript 5.9 + Tailwind CSS 4 + Vite 7 + better-sqlite3 + i18next + Vitest

**Process model — three Electron layers:**

| Process | Entry | Responsibility |
|---------|-------|----------------|
| **Main** | `src/main/index.ts` (~2220 lines) | BrowserWindow management, IPC handler registration (100+ handlers for installer, gateway, chat, config, sessions, memory, tools, skills, cron, kanban, MCP, registry), auto-updater, native menus, security hardening, SSH tunnel lifecycle |
| **Preload** | `src/preload/index.ts` (~1156 lines) | Context bridge exposing `window.electron` and `window.hermesAPI` to the renderer — all IPC invocations funnel through this typed bridge |
| **Renderer** | `src/renderer/src/main.tsx` | React 19 app root with 12+ screen components |

**Core modules in `src/main/`:**

- **`installer.ts`** — Hermes path resolution (`HERMES_HOME`, `HERMES_REPO`, `HERMES_PYTHON`), install script execution (bash/PowerShell with sudo credential caching), version check, backup/import, memory provider discovery, MCP server list parsing, log viewer, OpenClaw migration
- **`hermes.ts`** (~3352 lines, the heart of the app) — Chat transport management: three transport layers (TuiGatewayClient WebSocket, HTTP API streaming via `/v1/chat/completions` or `/v1/runs`, CLI fallback), auto-recovery with gateway restart, gateway lifecycle (spawn/stop/restart per profile), API server health polling, audio transcription, tool progress/usage streaming, `API_SERVER_KEY` bridge
- **`config.ts`** (~1680 lines) — Connection config (local/remote/ssh), `.env` reader/writer with TTL cache, YAML config reader/writer with dotted-path support and block-scoped children, credential pool management (auth.json), platform-enabled state per messaging platform, `API_SERVER_KEY` canonicalization with migration-on-read
- **`sessions.ts`** / **`session-cache.ts`** — SQLite session storage with FTS5 full-text search
- **`ssh-remote.ts`** / **`ssh-tunnel.ts`** — SSH tunnel management and remote Hermes operations over SSH exec
- **`claw3d.ts`** / **`office-start.ts`** — Claw3D (3D office interface) dev server and adapter management
- **`cronjobs.ts`** — Scheduled task management using Hermes cron jobs
- **`kanban.ts`** — Task board system with dispatch, assignment, commenting
- **`messaging-platforms.ts`** — Gateway platform configuration (Telegram, Discord, Slack, etc.)
- **`security.ts`** — Webview hardening, URL allowlist checks
- **`mcp-servers.ts`** — MCP server configuration management
- **`model-discovery.ts`** — Provider model autocomplete via `/v1/models`

**Architecture pattern:** Electron three-process with IPC-bridge abstraction. The main process is a thick backend (file I/O, process spawning, HTTP streaming, SSH tunneling), the renderer is a thin UI, and the preload is a typed aperture. Data flow is strictly unidirectional: React components call `window.hermesAPI.*` which invokes `ipcRenderer.invoke()`, main process handles it and streams results back via `event.sender.send()`.

## 3. Performance / Benchmarks

The repository does not contain formal benchmarks. Key performance characteristics inferred from the source:

- **Install progress:** 7-step installer with progress streaming (prerequisites, uv, Python, clone, venv, pip deps, finish)
- **Chat latency:** API health polling at 15s intervals; capabilities cache TTL of 60s; `API_SERVER_KEY` cache TTL of 5s; health probe timeout of 1.5s
- **Gateway ready wait:** 8s timeout for API server readiness (250ms poll interval); 45s timeout for dashboard gateway WebSocket ready
- **SSE streaming:** Content-Length is pre-computed (Buffer-based, not chunked) to pass the gateway's `body_limit_middleware` — issue #405
- **Session search:** SQLite FTS5 full-text search across all conversations
- **Test suite:** 70+ Vitest test files covering SSE parsing, IPC handlers, preload API surface, installer utilities, YAML path resolution, credential pool schema, config health, and more
- **CDP-based E2E scripts:** 23 Playwright scripts in `scripts/` for bug reproduction and verification

## 4. Trade-offs

### Wins

- **Massive integration surface:** 16 messaging gateways, 11 LLM providers, 14 toolsets, 5 memory providers, 1 MCP catalog, community registry — all managed through a single GUI
- **Three connection modes:** local, remote, SSH tunnel — covers self-hosted, cloud, and hybrid deployments
- **Multi-profile isolation:** Each Hermes profile runs its own gateway on its own port, with isolated `.env`, `config.yaml`, `auth.json`, and `state.db` — profiles can run simultaneously
- **Graceful degradation:** Chat transport has a 3-layer fallback chain (TuiGateway WebSocket -> HTTP API -> CLI spawn), with auto-recovery that tries to restart the gateway on transport errors
- **Installation UX:** Guided 7-step installer with sudo credential caching (solves the headless `sudo` hang in install scripts — issue #104)
- **Security posture:** Sandboxed renderer (`sandbox: true`, `contextIsolation: true`, `nodeIntegration: false`), URL allowlist filtering, webview hardening, `API_SERVER_KEY` never leaves main process
- **Migration-on-read:** Legacy config locations auto-migrate to canonical `.env` storage silently

### Losses

- **Upstream coupling:** Entire app depends on `hermes-agent` Python code living at `~/.hermes/hermes-agent`. If upstream changes its CLI interface, gateway API, or config schema, the desktop breaks
- **CLI fallback is fragile:** The `sendMessageViaCli` path parses ANSI output, filters noise patterns, and has no image attachment support — it's a last resort that loses fidelity
- **Install script proxying:** The desktop downloads and runs `install.sh`/`install.ps1` via shell -- it has no hermetic installer of its own. This means it inherits any flakiness in the upstream install script (network failures, sudo hangs, TTY requirements)
- **No formal benchmark suite:** Performance characteristics are implicit (timeouts, poll intervals) with no published numbers
- **Remote/SSH mode limitations:** Remote mode can't start/stop a local gateway; SSH mode requires systemd on the remote host for gateway management; gateway restart in SSH mode uses `systemctl --user restart hermes`
- **Upstream session-ID collision:** Without the `X-Hermes-Session-Id` header, Hermes derives session IDs via `sha256(system_prompt + first_user_message)[:16]`, causing collision when the same first message is sent in different chats. Fixed in the desktop by always sending a UUID-based session ID (issue tracked upstream as `NousResearch/hermes-agent#7484`)
- **API key resolution divergence:** The desktop and the upstream gateway resolve `API_SERVER_KEY` from different config locations (`api_server.token` vs top-level `API_SERVER_KEY`), causing 403 errors on second message. Fixed by bridging the resolved key into the gateway spawn environment
- **No offline mode:** Gateway requires network access for model inference (even local models depend on a running OpenAI-compatible server)
- **Windows installer is not code-signed:** SmartScreen warns on first launch

## 5. Design Rationale

**Why wrap a CLI in a desktop app?** The Hermes Agent CLI is powerful but has a high barrier to entry: users must install Python 3.11+, set up the venv, configure providers via `.env`, understand the gateway lifecycle, and manage profiles through terminal commands. The desktop app abstracts all of this behind a graphical flow, drastically lowering the "time to first message."

**Why Electron?** Cross-platform desktop shell with mature IPC model, built-in updater (electron-updater), native OS integration (menus, notifications, file dialogs, microphone), and the ability to spawn and manage child processes (the Python gateway). The project leverages Electron's process model explicitly: the main process holds all secrets and manages all subprocesses, the renderer is a disposable UI that can be hot-reloaded in dev.

**Why Python gateway instead of Node.js?** The Hermes Agent itself is Python-based (uses `uv` for package management, `hermes_cli.main` for CLI commands, `gateway/` for the API server). Rather than reimplementing the agent in JS/TS, the desktop treats it as an external service and communicates via HTTP/SSE. This keeps the desktop thin and avoids maintaining two agent implementations.

**Three transport layers, not one:**
- **TuiGatewayClient (WebSocket JSON-RPC)**: The most capable transport -- supports session create/resume, approval dialogs, clarify/sudo/secret requests, and live tool events. Only works locally (not in remote/SSH mode). The preferred path.
- **HTTP API (SSE)**: Works in all modes (local, remote, SSH). Stateless per-request. Uses the OpenAI-compatible `/v1/chat/completions` endpoint or newer `/v1/runs` "Hermes Runs" endpoint. The Hermes Runs transport is checked via a capabilities endpoint and preferred when available (it supports tool events natively; the legacy completions endpoint embeds them in SSE event: lines).
- **CLI fallback**: Spawns a Python process. Slowest, least capable, but always available as a last resort.

**Per-profile gateway isolation:** Each Hermes profile runs its own gateway on its own port. This lets multiple profiles (each with their own Telegram bot, model config, memory provider) run concurrently without port conflicts. The desktop tracks gateway processes in a `Map<string, ChildProcess>` and resolves which profile to target based on the active profile or explicit argument.

## 6. Transfer to Lyra

### Transferable Idea: Configurable multi-transport chat with per-profile gateway isolation

The three-tier transport strategy (WebSocket dashboard -> HTTP SSE -> CLI spawn) with auto-detection of capabilities and automatic fallback is directly applicable to Lyra. Lyra currently has a single chat path; adopting a capability-negotiated transport layer would let it gracefully handle different backend setups (local gateway, remote endpoint, SSH tunnel) without user configuration.

More specifically, the **per-profile port allocation** pattern (`getProfilePort()` in `gateway-ports.ts`, range 8642-8742, collision-free) is elegant: each profile's services are fully isolated on their own port, enabling true multi-profile concurrent operation. Lyra could adopt this for its own multi-session architecture.

**Workstream route:** §4.x Architecture & Modularity — Per-Profile Service Isolation.

- **Impact:** Medium (7/10) — Adds a proven pattern for multi-session/service isolation that Lyra's architecture currently lacks.
- **Effort:** Medium (5/10) — Requires port management middleware, per-profile state directory conventions, and gateway lifecycle tracking. The Hermes code provides a concrete reference implementation.
- **Tier:** Tier 2 (Strategic improvement — impactful but not blocking).
- **LICENSE:** MIT (Copyright (c) 2026 github.com/fathah) — fully compatible with any Lyra licensing.

### Additional transfer notes

- **SSE streaming with reasoning+tool events on separate channels:** Hermes streams `chat-reasoning-chunk` and `chat-tool-progress` on dedicated IPC channels alongside `chat-chunk`, allowing the renderer to render thinking bubbles and tool progress live. Lyra could adopt this multi-channel streaming pattern.
- **Config health audit system:** `config-health.ts` + `config-fixes.log` with per-issue auto-fix buttons is a pattern Lyra could borrow for its own configuration validation.
- **CDP-based E2E harness:** `scripts/README.md` describes an opt-in Chrome DevTools Protocol harness (set `ENABLE_CDP=1`) that allows Playwright to attach to the running renderer and drive tests via DOM selectors + IPC evaluate. This is a lightweight alternative to screenshot-driven testing that Lyra could adopt.

### Repository metadata

- **Stars:** High (community adoption, related to Nous Research's Hermes Agent)
- **License:** MIT
- **Primary language:** TypeScript (with Python for the upstream agent)
- **Version:** 0.5.7 (active development)
- **Installer integrity:** Not Windows code-signed; not RPM GPG-signed (documented tradeoffs)
- **Test coverage:** 70+ Vitest test files + 23 Playwright E2E repro scripts
