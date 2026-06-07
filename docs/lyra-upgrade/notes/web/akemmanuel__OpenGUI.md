# OpenGUI (akemmanuel) -- Deep-Read

**Repo**: https://github.com/akemmanuel/OpenGUI
**Version**: 0.5.24
**Language**: TypeScript (React 19 + Electron 42 + Hono Node.js server)
**License**: MIT (Copyright 2026 akemmanuel)

## 1. Headline Feature & Mechanism

**Headline**: A unified desktop + web command center that lets users manage multiple coding-agent backends (OpenCode, Claude Code, Codex, Pi) across multiple project workspaces from one UI -- with streaming SSE responses, prompt queueing, model switching, MCP tool configuration, voice input, and detached project windows.

**How it works**: OpenGUI is a three-layer system. The platform-specific "Shell" (Electron main process or browser or Capacitor mobile scaffold) bootstraps the "Frontend" -- a shell-agnostic React app -- which talks exclusively to the "Backend" (a Node.js HTTP/WebSocket server) via the `OpenGuiClient` protocol. The Backend owns all "Harness Adapters", which are the integration layers that translate OpenGUI's operations into SDK calls for each of the four supported coding-agent runtimes. Each adapter normalizes backend-specific events (session creation, message deltas, permission requests, questions) into a unified `HarnessEvent` discriminated union type. The Frontend subscribes to these normalized events over SSE and updates its React state via the central `use-agent-impl-core` hook which uses a `useReducer`-based state machine covering workspace connection, project hydration, session lifecycle, message loading, queue dispatch, variant selection, and prompt submission. The Prompt Queue allows the user to queue prompts while the agent is busy; the queue dispatches the next prompt automatically when the agent session becomes idle.

**Key architectural insight**: The system is designed around a "Harness" abstraction that decouples the UI from any specific coding-agent CLI/SDK. Four harnesses exist today (OpenCode, Claude Code, Codex, Pi), each with its own capability mask (e.g., Claude Code supports sessions/streaming/models/commands but NOT agents/variants/providerAuth/mcp/skills/localServer; OpenCode supports all of those). The `HarnessCapabilities` interface drives which UI controls appear (e.g., variant selectors only show for OpenCode).

## 2. Architecture & Core Modules

### Entry Points

| File | Role |
|------|------|
| `main.ts` | Electron main process -- window management, IPC handlers, backend sidecar lifecycle, settings store, file dialogs, terminal/OS integration |
| `preload.ts` | Electron preload script -- `contextBridge.exposeInMainWorld("electronAPI", ...)` exposing IPC-safe API for renderer |
| `src/frontend.tsx` | React entry point -- creates root, calls `installWebElectronAPI()`, `initializeRuntimeClients()`, `applyStoredAppearance()`, `initI18n()` |
| `src/App.tsx` | Main app layout -- `HarnessProvider` + `AppSidebar` + `MessageList` + `PromptBox` + settings/setup/update dialogs |
| `server/web-server.ts` | Node.js Hono HTTP/WS server for browser mode -- owns all service orchestration (HarnessService, SessionService, ProjectService, PromptQueueService), SSE event bus, REST/RPC endpoints |
| `server/harness-runtime.ts` | Registers all four harness adapters (opencode, claude-code, pi, codex) with their bridge event normalizers |

### Core Data Flow

1. **Frontend** (React) calls `OpenGuiClient` methods (REST/RPC over HTTP) on the Backend
2. **Backend** (web-server.ts) delegates to services (SessionService, HarnessService, etc.) which call **Harness Adapters** (opencode-bridge.ts, claude-code-bridge.ts, etc.)
3. **Harness Adapters** translate operations into SDK calls (OpenCode SDK, Claude Agent SDK, Codex SDK, Pi SDK)
4. Events from harnesses flow back: normalized by `src/agents/*.ts` normalizers into `HarnessEvent` union type
5. Events are broadcast to frontend via SSE (`/api/events`) or Electron IPC (`backend:status-changed`, `opencode:bridge-event`, etc.)
6. Frontend's `use-agent-impl-core.tsx` handles events via `handleHarnessEvent()` reducer, updating session/message/queue state

### Architectural Pattern

**Three-layer shell-agnostic architecture**:
- Shell (platform scaffold: Electron, browser, or Capacitor mobile)
- Frontend (React UI, shell-agnostic, communicates via `OpenGuiClient` protocol interface)
- Backend (Node.js server owning all Harness adapters, services, state)

**Protocol decoupling**: The `OpenGuiClient` interface (`src/protocol/client.ts`) defines the complete API surface between Frontend and Backend. The HTTP implementation (`src/protocol/http-client.ts`) handles REST calls + RPC wrapper + SSE event subscription. The `unified-agent-protocol.ts` is an experimental draft for a wire protocol to standardize even the agent-level communication.

**Harness adapter pattern**: Each harness (opencode, claude-code, codex, pi) has three files:
- A bridge file (root level, e.g., `opencode-bridge.ts`) -- IPC handler registration for Electron
- A normalizer (e.g., `src/agents/opencode.ts`) -- raw event -> `HarnessEvent` conversion
- Capability/workspace constants (e.g., `OPENCODE_CAPABILITIES`, `OPENCODE_WORKSPACE`)

**State management**: Central `useReducer` in `use-agent-impl-core.tsx` with ~30 sub-hooks covering workspace lifecycle, project hydration, session lifecycle, message loading, queue dispatch, variant selection, prompt submission, and keyboard shortcuts. Separate persistence layer (`agent-state-persistence.ts`) handles localStorage serialization for workspaces, variants, unread sessions, etc.

### Key Configuration

| File | Purpose |
|------|---------|
| `settings-store.ts` | Simple JSON file-based key-value store (atomic writes via temp file + rename) |
| `src/lib/constants.ts` | All magic strings (localStorage keys, URLs, timing constants) centralized |
| `src/runtime/clients.ts` | Bootstrap logic for creating the right `OpenGuiClient` (Electron vs web vs mobile) and `DesktopShellClient` |
| `src/agents/index.ts` | Harness ID registry with session ID codec for disambiguating which harness owns a session |
| `src/agents/backend.ts` | Core types: `HarnessEvent` union, `HarnessCapabilities`, `HarnessTarget`, descriptor types |

## 3. Performance / Benchmarks

No explicit benchmark numbers in the repo. The repo provides structural performance indicators:

- Prompt Queue with auto-dispatch on idle -- allows user to type next prompt while agent is still working, avoiding serial wait time
- A single `DEFAULT_SERVER_PORT = 4096` for the backend; no throughput/load data
- SSE for real-time streaming (not polling), with `lastEventAt` heartbeat tracking per harness
- Server-side session/message pagination (`MessagePageResult` with `nextCursor`)
- `backend-event-normalization.ts` includes defensive deduplication of SSE connection lifecycle errors
- Electron's `smartUnpack: true` in asar packing for optimized startup
- Model discovery TTL of 5 minutes (`MODEL_DISCOVERY_TTL_MS = 5 * 60 * 1000` in claude-code-bridge.ts)
- No latency, throughput, or memory benchmarks published

## 4. Trade-offs (wins vs losses)

### Wins

- **Multi-agent, multi-project in one UI**: Eliminates terminal-tab juggling. Users can switch between OpenCode, Claude Code, Codex, and Pi without leaving the app.
- **Platform portability**: Single React frontend runs identically on Desktop (Electron), Web (browser), and Mobile (Capacitor). The `OpenGuiClient` protocol makes this possible.
- **Harness abstraction cleanly decouples UI from agent SDKs**: Each harness adapter can be added/removed independently with its own capability mask.
- **Prompt queue** is a genuine productivity feature -- unlike terminal-based workflows where you must wait for the agent to finish before typing the next command.
- **Detached project windows** let users open separate OS windows for different projects, each with its own session list and chat.
- **Docker deployment** with host-control mode (nsenter) gives users the option to run in a container while still using host CLIs.
- **Comprehensive documentation**: ADRs, CONTEXT.md glossary, architecture diagrams, contributing guide, deploy guides.

### Losses / Limitations

- **Young project**: v0.5.24, described as "Early but usable." Single commit in local clone -- heavy active development.
- **Dependency on external agent CLIs**: OpenGUI itself has no coding-agent capability; it is purely a UI/management layer on top of other tools that must be separately installed and configured.
- **No built-in auth/teams**: Single-user by design. Multi-user sessions explicitly flagged as non-goal.
- **Windows support is soft**: "Windows builds are unsigned. Windows SmartScreen will warn." Windows support hardening listed as a help-wanted area.
- **Mobile shell is scaffold-only**: Capacitor JS exists but "Never spawns a Backend, never opens a file browser or terminal." No evidence of App Store deployment.
- **Fire-and-forget backend design**: The backend stores session state but it is ephemeral from the frontend's perspective (localStorage for most frontend state). A backend restart wipes in-memory harness sessions unless they are persisted by the underlying agent CLI.
- **No offline mode**: Everything requires network to the Backend (even Desktop mode runs a local Node.js server sidecar).
- **Codebase size**: Large bridge files (opencode-bridge.ts = 89KB, pi-bridge.ts = 106KB, codex-bridge.ts = 65KB, claude-code-bridge.ts = 77KB) suggest these modules carry significant complexity and may benefit from decomposition.
- **TypeScript strictness**: Several bridge files use `@ts-nocheck` and heavily rely on `any`/untyped parameters, reducing type safety in the most mission-critical integration layer.
- **No in-repo benchmarks**: No performance data for large sessions, many concurrent projects, or memory usage under sustained streaming.

## 5. Design Rationale

**Why a separate Backend process instead of in-process agent management?**
The plan document (`docs/plans/2026-05-12-backend-frontend-split-workspaces-mobile.md`) makes this explicit: separating Backend from Frontend allows three Shell variants (Desktop, Web, Mobile) to share one codebase and one protocol. The Backend is "the only stateful layer." The Desktop Shell runs it as a sidecar; Web/Mobile connect to a remote one. This also enables Docker deployment and remote access.

**Why "Harness" terminology?**
ADR 0001 documents the rename from "Agent Backend" to "Harness". The term "Backend" was causing a naming collision between the OpenGUI server process and the coding-agent runtimes. "Harness" was chosen because it has no pre-existing meaning in the project, forcing explicitness.

**Why text-only prompts with file uploads (ADR 0002)?**
Instead of a special image attachment channel, OpenGUI uploads all files to Backend temp storage and inserts `@<path>` mentions in the prompt text. This works uniformly across Desktop, Web, and Mobile, and supports any file type (not just images). Simpler UX, simpler implementation, no platform-specific image handling.

**Why no React StrictMode?**
The comment in `frontend.tsx` explains: StrictMode's double-mount behavior causes IPC event subscriptions (SSE bridge) to fire twice, producing garbled streaming output. A pragmatic trade-off: forgo StrictMode's development checks for correct streaming behavior.

**Why one Backend binary with multiple deployment modes?**
The plan document explicitly rejects a separate "headless backend" binary. Instead, environment variables (`OPENGUI_SERVER_MODE`, `OPENGUI_AUTH_TOKEN`, `OPENGUI_ALLOWED_ROOTS`) configure the same binary for sidecar, standalone, Docker, or combined frontend+backend mode. Reduces build targets and testing matrix.

## 6. Transfer to Lyra

### Transferable Idea: Unified Harness Abstraction with Capability Masks

OpenGUI's approach of defining a `HarnessCapabilities` interface (boolean flags for sessions, streaming, messagePaging, models, agents, commands, compact, fork, revert, permissions, questions, providerAuth, mcp, skills, config, localServer) and then mapping each backend to its capability profile is directly transferable to Lyra.

Lyra currently has separate "adapter modules" for each supported agent/LLM backend, but lacks a formal capability declaration system. An OpenGUI-style capability mask would let Lyra:
- Enable/disable features in the monitoring UI automatically (e.g., hide "variant selector" for backends that don't support variants)
- Drive routing decisions (e.g., only route to a backend that supports `skills: true`)
- Self-document backend limitations to users
- Simplify adding new backends: just implement a capability mask + event normalizer

### Proposed Workstream Route: **Section 4.x -- Multi-Agent / Backend Adapters**

This maps to Lyra's agent runtime layer. OpenGUI's harness adapter + capability mask + unified event normalizer pattern is a concrete design to adopt for Lyra's backend adapter registry (plans/02-memory, plans/05-router).

### Assessment

- **Impact: 7** (medium-high). A capability-mask abstraction would improve Lyra's backend-agnostic routing, monitoring, and feature gating. It is not a headline feature but addresses a recurring pain point: inconsistent backend features breaking the UI.
- **Effort: 4** (moderate). Adding a `HarnessCapabilities`-style interface to Lyra's backend adapter types is modest work. The bigger effort is retrofitting existing adapters to declare their capabilities. OpenGUI's interfaces can be adapted directly since they are MIT-licensed TypeScript types.
- **Tier: T2** (enhancement to existing pattern). This improves Lyra's backend abstraction without introducing a new subsystem.

### License Note

OpenGUI is MIT-licensed. Its `HarnessCapabilities`, `HarnessEvent`, and normalizer patterns can be freely adapted into Lyra (which itself must verify license compatibility). The code is available at https://github.com/akemmanuel/OpenGUI.
