# openclaw/openclaw -- Deep-Read

## 1. Headline Feature & Mechanism

**OpenClaw** is a personal AI assistant Gateway -- a single, local-first daemon that connects one AI agent to 20+ messaging channels simultaneously. The headline feature is the **multi-channel messaging gateway**: the same assistant instance simultaneously serves WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, IRC, Microsoft Teams, Matrix, Feishu, LINE, Mattermost, Nextcloud Talk, Nostr, Synology Chat, Tlon, Twitch, Zalo, WeChat, QQ, and WebChat.

**How it works (mechanism):** The `openclaw.mjs` launcher bootstraps a Node.js CLI process (`entry.ts` -> `cli/run-main.ts`). The main runtime is a **Gateway daemon** (`src/gateway/server.impl.ts`) that:
1. Opens a WebSocket server on `127.0.0.1:18789` (default)
2. Loads channel plugins from `extensions/` (WhatsApp via Baileys, Telegram via grammY, etc.) -- each is a transport-only adapter
3. Maintains a provider-agnostic LLM integration layer (`src/llm/providers/`) for Anthropic, OpenAI, Google, Amazon Bedrock, etc.
4. Exposes a typed Request/Response/Event protocol over WebSocket
5. Routes inbound messages through the **agent loop** (`src/agents/agent-command.ts`), which orchestrates session management, model selection, tool execution, and delivery

The agent loop is transport-agnostic: channels only render presentation, enforce transport limits, and map native callback envelopes. The core agent does not know about WhatsApp vs. Telegram -- it produces typed presentation actions, and the channel plugin renders them for the target platform.

## 2. Architecture & Core Modules

### Entry Points
- `openclaw.mjs` -- Wrapper launcher, Node version check, compile cache setup
- `src/entry.ts` -- CLI process entry point, argv parsing, respawn logic
- `src/index.ts` -- Package entry, library facade for embedding, error handlers
- `src/cli/run-main.ts` -- Main CLI orchestration (fast paths, env setup, Commander dispatch)
- `src/library.ts` -- Public library facade for embedding OpenClaw reply runtime APIs

### Core Module Map
| Module | Path | Purpose |
|--------|------|---------|
| Gateway daemon | `src/gateway/` | WS server, HTTP surfaces, auth, sessions, config reload, graceful restart |
| Agent runtime | `src/agents/` | Session lifecycle, model selection, tool inventory, MCP binding, subagent spawning |
| LLM providers | `src/llm/` | Provider-agnostic integration: Anthropic, OpenAI, Google, Bedrock, etc. |
| Channels | `src/channels/` | Transport abstraction: message routing, typing, streaming, thread binding |
| Plugins | `src/plugins/` | Plugin system: runtime, hooks, manifest loading, registry |
| Tool system | `src/tools/` | Descriptor-driven tool planning: availability, execution, protocol conversion |
| CLI commands | `src/cli/` | Commander-based command tree, help, bash completion, JSON output |
| Configuration | `src/config/` | Config loading, validation, SecretRef resolution, migration/doctor |
| Skills | `src/skills/` | Skill discovery, runtime, ClawHub integration |
| MCP | `src/mcp/` | MCP server and runtime integration surfaces |

### Data Flow
```
User Message (WhatsApp/Telegram/etc.)
  -> Channel Plugin (extensions/telegram/src/index.ts)
  -> Channel Abstraction (src/channels/)
  -> Gateway Server (src/gateway/server-chat.ts)
  -> Agent Command (src/agents/agent-command.ts)
  -> Session/Lifecycle Management
  -> LLM Provider Call (src/llm/providers/)
  -> Tool Execution (src/tools/)
  -> Response Delivery back through Channel Plugin
```

### Architecture Patterns
- **Gateway as control plane** -- single daemon owns all connections, auth, routing
- **Plugin-based extensibility** -- two styles: code plugins (in-process runtime hooks) and bundle-style plugins (skills, MCP servers, config)
- **Transport-agnostic agent loop** -- channels are thin adapters; core does not know transport details
- **SQLite-first storage** -- shared state DB for global runtime, per-agent DB for agent-scoped state
- **Provider-agnostic LLM layer** -- `src/llm/providers/` has provider-specific adapters behind a generic interface
- **Described tool dispatch** -- tools are declared via `ToolDescriptor`, evaluated for availability, and dispatched via `ToolExecutorRef`
- **Lazy dynamic imports** -- heavy gateway/agent runtime is behind dynamic import() for fast CLI startup

### Package Structure (21 shared packages)
- `agent-core`, `gateway-client`, `gateway-protocol` -- shared types and clients
- `llm-core`, `llm-runtime` -- LLM abstraction
- `plugin-sdk`, `plugin-package-contract` -- plugin developer API
- `model-catalog-core` -- model registry
- `speech-core`, `media-core`, `media-generation-core` -- media handling
- `memory-host-sdk`, `web-content-core`, `terminal-core` -- auxiliary
- `tool-call-repair`, `net-policy`, `normalization-core` -- utilities

### Sizes
- ~5,037 non-test TypeScript source files
- 137 extension/plugin packages
- 474 agent source files (non-test)
- 42 `src/` subdirectories
- Language: TypeScript ESM, strict mode

## 3. Performance/Benchmarks

No explicit performance benchmarks are published in the repository. The project surfaces several performance characteristics through its AGENTS.md and code patterns:

- **Startup time**: The CLI has a fast-path architecture that avoids importing heavy gateway runtime until needed (dynamic `import()`). Node compile cache is used for faster second-run startup.
- **Test performance**: Agent tests are import-bound (~474 non-test agent files). Guardrails exist to avoid cold-loading bundled plugin/channel/provider runtime for static queries. `vitest` with up to 16 workers.
- **SQLite over JSON files**: The project explicitly migrated from JSON/JSONL file stores to SQLite for state, caching, and queues, citing performance and reliability benefits.
- **Prompt caching**: Deterministic ordering for maps/sets/registries before model/tool payloads to maximize prompt cache hits.
- **Recommended runtime**: Node 24 (Node 22.19+ minimum).
- **Process model**: One Gateway per host, single daemon. Launchd/systemd for auto-restart. Docker deployment supported.
- **Memory pressure**: `OPENCLAW_VITEST_MAX_WORKERS=1` environment variable for constrained test environments.

## 4. Trade-offs

| Win | Lose |
|-----|------|
| **Massive channel coverage** (20+ platforms) | **Single-user assistant** -- not designed for multi-tenant/multi-user boundaries. Security model assumes one trusted operator. |
| **Local-first privacy** -- no cloud dependency, data stays on device | **User-managed infrastructure** -- users must maintain their own gateway, networking, and security |
| **Plugin architecture keeps core lean** | **High bar for plugin inclusion** -- many features live outside core in third-party repos, creating fragmentation |
| **TypeScript for hackability** -- widely known, fast iteration | **JavaScript runtime overhead** -- not suitable for latency-critical or compute-heavy paths |
| **SQLite-first storage** -- simple, reliable, no distributed complexity | **No horizontal scaling** -- single process, single SQLite database per host |
| **One Gateway per host** -- simple operational model | **No HA/failover** -- gateway restart = service interruption |
| **Rich tool system** (descriptors, MCP, skills) | **Complex configuration surface** -- large config schema, many env vars, migration overhead |
| **Extensive AGENTS.md / CLAUDE.md developer guidance** | **High cognitive load for contributors** -- massive onboarding surface for new developers |
| **Sponsorship by OpenAI, NVIDIA, GitHub, Vercel** | **Fast-moving target** -- weekly releases (2026.6.1, 2026.6.2, 2026.6.5), breaking changes possible |
| **Comprehensive security posture** (DM pairing, sandboxing, execution approval) | **Security complexity** -- many knobs (dmPolicy, allowFrom, sandbox modes) require operator expertise |

## 5. Design Rationale

1. **Local-first by design**: The project explicitly prioritizes running on user-owned devices. The Gateway is described as "the control plane -- the product is the assistant." This avoids cloud dependencies, data leakage, and recurring API costs for the operator.

2. **TypeScript for orchestration**: The VISION.md states: "OpenClaw is primarily an orchestration system: prompts, tools, protocols, and integrations. TypeScript was chosen to keep OpenClaw hackable by default." This is a deliberate contrast to performance-oriented AI projects that might use Rust or C++.

3. **Plugin over core**: "Core stays lean; optional capability should usually ship as plugins." The project actively resists adding features to core, preferring plugin API extensions. The VISION.md explicitly lists what will NOT be merged into core (new core skills, full-doc translations, wrapper channels, agent-hierarchy frameworks, heavy orchestration layers).

4. **SQLite as universal store**: The project enforces SQLite as the only runtime state store. No JSON/JSONL/TXT/sidecar files for state. This eliminates a class of consistency bugs and simplifies backup/migration. The AGENTS.md has explicit rules: "If it is app state or cache, it belongs in SQLite."

5. **Compatibility is opt-in**: "Shipped means reachable from a release Git tag." Old config shapes, retired APIs, and legacy storage formats get migration in `openclaw doctor --fix`, not runtime shims. This keeps the runtime code lean and avoids technical debt from backward-compatibility branches.

6. **Security as deliberate tradeoff**: "Strong defaults without killing capability." Default DM policy is `pairing` (unknown senders get a pairing code). Sandboxing defaults to allowing `bash`, `process`, `read`, `write`, `edit` for the main session. The project acknowledges it is not designed as a shared multi-tenant boundary between adversarial users.

7. **No agent hierarchy frameworks**: The VISION.md explicitly rules out "manager-of-managers / nested planner trees as a default architecture." OpenClaw routes channels/accounts/peers to isolated agents via workspaces and per-agent sessions, but keeps routing simple.

## 6. Transfer to Lyra

### Transferable Idea: Gateway + Channel Abstraction Pattern

The single most transferable architectural pattern is **OpenClaw's Gateway + transport-agnostic agent loop**. Lyra currently delivers output primarily through CLI and/or a single agent process. By adopting a Gateway architecture:

1. A lightweight daemon owns all outbound delivery surfaces
2. The core agent loop produces typed presentation actions (text, card, image, approval) without knowing the delivery channel
3. Thin channel adapters translate presentation actions to platform-native formats
4. Channels can be added/removed independently without touching agent logic

This directly addresses Lyra's workstream roadmap:
- **Section 4.2 (Multi-channel delivery)**: OpenClaw's channel abstraction and transport-only plugin design provides a reference implementation for unified multi-platform delivery
- **Section 4.3 (Plugin/extension architecture)**: OpenClaw's plugin system (code plugins + bundle-style plugins) and ClawHub marketplace pattern offers a proven model for Lyra's extension ecosystem
- **Section 4.4 (Tool system)**: OpenClaw's descriptor-driven tool planning (`ToolDescriptor` + `ToolExecutorRef` + `ToolPlan`) provides a clean pattern for declarative tool definition, availability evaluation, and dispatch

### Assessment
- **Workstream Route**: Section 4.2 (Multi-channel delivery) -- primary fit is the channel abstraction pattern for multi-platform output delivery
- **Impact**: 8/10 -- A Gateway pattern enables Lyra to deliver across CLI, web, Slack, Discord, and custom surfaces from a single agent core
- **Effort**: 6/10 -- Medium-high effort; requires building a lightweight Gateway daemon, WebSocket protocol, and at least 2-3 channel adapters
- **Tier**: Tier 2 (High-impact, medium-term feature) -- not critical for MVP, but unlocks broad distribution
- **LICENSE**: MIT -- fully compatible, no restrictions on use or derivative works

### Key File References
- `src/gateway/server.impl.ts` -- Gateway implementation
- `src/gateway/server-chat.ts` -- Chat routing through gateway
- `src/agents/agent-command.ts` -- Transport-agnostic agent loop
- `src/channels/session.ts` -- Channel session abstraction
- `src/tools/index.ts` -- Tool planning system
- `extensions/telegram/src/index.ts` -- Example channel plugin
- `docs/concepts/architecture.md` -- Architecture documentation
- `src/plugins/` -- Plugin system runtime
