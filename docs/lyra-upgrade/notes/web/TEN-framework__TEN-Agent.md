# TEN-framework/TEN-Agent -- Deep-Read

Source: https://github.com/TEN-framework/TEN-Agent (cloned to repos/TEN-framework__TEN-Agent/)
License: Apache 2.0 with additional restrictions (Agora commercial constraints)

---

## 1. Headline Feature & Mechanism

**Headline: Real-time multimodal conversational AI agent framework with a graph-based extension composition system.**

The headline feature is a **declarative graph-based agent assembly system** where developers wire together discrete AI components (ASR, LLM, TTS, VAD, avatar, tools) as pluggable extension nodes in a JSON-defined graph. The runtime then executes this graph, routing audio, video, data, and command messages between nodes in real time.

**Mechanism in detail:**

1. **Static graph definition** -- Every agent is configured as a `predefined_graphs[]` entry in `property.json`. Each graph declares nodes (extensions) and connections (data flow paths between them).

2. **Runtime property injection** -- When `POST /start` is called against the Go API server (port 8080), the server reads the static `property.json`, filters to the requested graph, and injects session-specific values: Agora RTC tokens, channel names, per-extension property overrides, environment variable resolution (`${env:VAR|default}`). The modified config is written to a temp file.

3. **Worker spawning** -- The Go server executes `tman run start -- --property <tmpfile>` as a subprocess, which starts a new OS process that loads the graph, initializes all extension nodes, and begins processing.

4. **Message routing** -- Extensions communicate via four typed message channels: `cmd` (named commands like `tool_register`, `flush`, `on_user_joined`), `data` (structured data like `asr_result`, `text_data`), `audio_frame` (PCM streams), and `video_frame`. The framework routes messages between nodes based on the connection declarations.

5. **Extension lifecycle** -- Each extension follows `on_init() -> on_start() -> [process messages] -> on_stop() -> on_deinit()`. Base classes (`AsyncASRBaseExtension`, `AsyncTTS2BaseExtension`, `AsyncLLMBaseExtension`, etc.) provide abstract methods that vendor-specific implementations override.

The system is **RTC-first**: primary media transport is Agora RTC (UDP-based, 50-150ms latency) rather than WebSockets. WebSockets are used only for signaling and configuration. This is a fundamental design choice that differentiates TEN from WebSocket-only agent frameworks.

---

## 2. Architecture & Core Modules

**Top-level directory structure:**
```
core/               -- C/C++ runtime (ten_runtime, ten_utils, ten_rust, ten_manager)
packages/           -- Core packages: addon loaders (Python, Node.js, Go), default apps/extensions, protocols (msgpack), example apps
ai_agents/          -- Primary development area:
  agents/
    ten_packages/
      extension/    -- 90+ vendor-specific extensions (ASR, TTS, LLM, tools, avatars)
      system/       -- Base classes (ten_ai_base), runtime bindings (Python, Go)
    examples/       -- 24+ pre-built agent configurations
    integration_tests/ -- ASR/TTS guarder test frameworks
  server/           -- Go HTTP API server (Gin framework)
  playground/       -- Next.js frontend UI (port 3000)
  esp32-client/     -- ESP32-S3 hardware client
build/              -- Build system (GN/Ninja)
docs/               -- Progressive disclosure AI docs, API docs, getting-started guides
third_party/        -- Third-party library references
tests/              -- C++ unit tests (Google Test), Python test utilities
tools/              -- Grafana monitoring, profilers, formatters
```

**Architecture pattern: Graph-based extension composition with server-worker process isolation.**

Key architectural components:

| Component | Language | Role |
|-----------|----------|------|
| C/C++ Runtime (`core/src/ten_runtime/`) | C/C++ | Core message-passing engine, app/engine/extension lifecycle, protocol handling, addon management |
| Rust Runtime (`core/src/ten_rust/`) | Rust | Service hub, metrics (optional, feature-gated) |
| Go API Server (`ai_agents/server/`) | Go | HTTP endpoints (`/start`, `/stop`, `/ping`, `/health`, `/graphs`), property injection pipeline, session management, worker lifecycle (SIGTERM/SIGKILL) |
| Python Extensions (`ai_agents/agents/ten_packages/extension/`) | Python | Vendor adapters implementing base class contracts (90+ extensions) |
| TMAN Manager (`core/src/ten_manager/`) | Rust | Package management, dependency resolution (`tman install`, `tman run`) |
| Playground UI (`ai_agents/playground/`) | TypeScript/React | Next.js frontend for agent interaction |

**Data flow:**
```
Client (browser/mobile)
    |  Agora RTC (audio/video)
    v
Worker Process (per-session)
    agora_rtc extension
    |--audio_frame--> stt extension (Deepgram, Azure, etc.)
    |                   |--data (asr_result)--> main extension (orchestrator)
    |                                              |--data (text_data)--> llm extension
    |                                              |                     |--data (response)--> main extension
    |                                              |                                          |--data (tts_text)--> tts extension
    |                                              |                                                            |--audio_frame--> agora_rtc
    |--video_frame--> vision extension (optional)
```

**Key design patterns:**
- **Extension lifecycle hooks**: `on_init/on_start/on_stop/on_deinit` -- standard lifecycle across all extension types
- **Property injection pipeline**: Static `property.json` -> filter graph -> merge per-extension overrides -> inject start params (RTC token, stream IDs, channel) -> resolve env vars -> write temp file
- **Process-per-session**: Each agent session runs in its own OS process, providing isolation
- **Channel auto-injection**: Any extension node with a `"channel"` property automatically receives the session's channel name -- future-proof design requiring zero server changes for new channel-aware extensions
- **startPropMap**: Centralized mapping in `config.go` that maps request fields to target extension/property pairs

---

## 3. Performance/Benchmarks

The repository itself does **not contain benchmark results or performance test code in the source tree**. The README and architecture docs make the following claims:

- **RTC latency**: 50-150ms (UDP-based Agora RTC) vs higher latency for TCP-based WebSockets
- **Minimal system requirements**: CPU >= 2 cores, RAM >= 4 GB
- **Build time**: ~5-8 minutes for first agent build inside Docker
- **Coverage**: The repo is connected to Coveralls (`Coverage Status` badge in README), but no specific coverage numbers are documented in the source tree.

The `tools/` directory references Grafana monitoring and profilers, suggesting observability infrastructure exists but benchmark data is not published in the repo.

---

## 4. Trade-offs

**Wins:**

1. **Multi-vendor flexibility**: 90+ extensions across 10+ ASR vendors, 15+ TTS vendors, 8+ LLM providers, 5+ avatar vendors. Easy to swap providers at graph-config level without code changes.
2. **RTC-first architecture**: UDP-based media transport gives significantly lower latency than WebSocket-only agents. Built-in bandwidth adaptation and FEC.
3. **Graph composition model**: Declarative JSON graph wiring makes agent architecture visible and auditable. Adding a new node is a config change, not a code change.
4. **Polyglot support**: Extensions can be written in Python, Go, or Node.js. Core runtime is C/C++ for performance. Server is Go.
5. **Multi-modal by default**: Audio, video, text, and command channels are first-class citizens in the message routing system, not afterthoughts.
6. **Future-proof property injection**: The channel auto-injection mechanism means any new extension with a `channel` property automatically works without server changes.
7. **Progressive disclosure docs**: The `docs/ai/` directory structure (L0 repo card, 8 L1 summaries, L2 deep dives) is an excellent pattern for AI agent onboarding.

**Losses:**

1. **Agora lock-in**: The license explicitly restricts deploying TEN in a way that competes with Agora. The RTC transport is deeply coupled to Agora's ecosystem (App ID, App Certificate, RTC/RTM tokens). While WebSocket is supported, the default and best-supported path is Agora.
2. **License restrictions**: Apache 2.0 with additional conditions -- Section 1 prohibits hosting on end-user devices and deploying in a way that competes with Agora. This is NOT standard open source; it's a source-available license with commercial guardrails.
3. **Heavy Docker dependency**: All development and deployment runs inside Docker (`ten_agent_dev` container). The dev environment requires 5+ external API keys (Agora, Deepgram, OpenAI, ElevenLabs, etc.). The initial build takes 5-8 minutes.
4. **Worker process management fragility**: Zombie worker processes can survive container and server restarts. The go-to fix is `pkill -9 -f 'bin/worker'`. Graceful shutdown has a 2-second timeout before SIGKILL.
5. **Complex dev gotchas**: Property getters returning tuples (the `[0]` extraction dance), signal handlers forbidden in extension threads, `.env` changes requiring full container rebuild, `tman install` can wipe `bin/worker`, Next.js lock file persistence, symlink drift in guarder tests.
6. **Parallel guarder test incompatibility**: ASR and TTS guarder tests cannot run in parallel in the same container due to shared temp paths (`/tmp/test: Text file busy`).
7. **Apple Silicon Docker issues**: Rosetta may be needed for x86 image emulation on ARM Macs.

---

## 5. Design Rationale

The architecture makes several intentional trade-offs that reveal the design philosophy:

1. **Process isolation over in-process multi-tenancy**: Each agent session gets its own OS process. This is heavier than thread-per-session but provides fault isolation -- a crash in one extension can't take down other sessions. This also simplifies resource cleanup (kill the process, release all resources).

2. **RTC over WebSocket as primary transport**: Agora RTC provides sub-200ms latency with built-in bandwidth adaptation, FEC, and codec support (Opus, VP8, VP9, AV1). The choice prioritizes real-time voice/video quality over protocol simplicity. This positions TEN for production voice agents, not prototype chat bots.

3. **Graph wiring over programmatic composition**: Rather than composing agents in code (`agent.add_component(asr).connect(llm)`), TEN uses declarative JSON graphs. This makes the architecture inspectable, version-controllable, and editable via a visual designer (TMAN Designer at port 49483). It also enables the property injection pipeline to dynamically modify graphs at session start.

4. **Separate API server from worker processes**: The Go HTTP server is a thin orchestrator that does not participate in media processing. It spawns workers, manages timeouts, and handles REST API concerns. This separation of concerns allows the server to be stateless and restartable without affecting active sessions (though zombie workers are a practical concern).

5. **Plugin architecture via Python extensions**: Python was chosen as the primary extension language (not C++ or Go) because it offers the fastest iteration cycle for vendor integration. The C/C++ core handles performance-sensitive message routing, while Python handles business logic for each vendor API. This is a pragmatic "fast core, slow plugins" pattern.

6. **License as competitive moat**: The additional conditions in the Apache 2.0 license explicitly protect Agora's business interests. This suggests TEN is primarily a customer acquisition funnel for Agora's RTC platform, not a purely altruistic open-source project. The open-source nature drives adoption; the license prevents competitors from benefiting.

---

## 6. Transfer to Lyra

**Transferable idea: Declarative graph-based agent composition with a runtime property injection pipeline.**

Lyra could adopt a similar **extension-graph architecture** where agent capabilities (memory, context management, tool use, router, safety checks, reporting) are independent nodes in a directed graph, connected via typed message channels. The key innovation to transfer is the **property injection at session start** -- rather than building a monolithic agent with hard-coded components, Lyra could define agent topologies in a config file and inject session-specific parameters (user identity, channel, permissions, model overrides) at runtime without code changes.

**Workstream route: Section 4.2 (Architecture: Extension Graph / Plugin System)**

This maps to the Lyra upgrade workstream for **agent composition and routing**. TEN's graph model directly addresses the problem of wiring together discrete AI capabilities (which in Lyra's case would be router, memory, context manager, safety check, tool registry) into coherent agent behavior.

**Impact: 8/10** -- High impact because Lyra's current architecture uses implicit wiring (components reference each other through hard-coded imports). Adopting a declarative graph model would make Lyra's agent topology visible, auditable, and reconfigurable at deploy time.

**Effort: 6/10** -- Moderate effort. The core runtime needs a message-passing substrate and an extension lifecycle, but Lyra already has module boundaries (the existing plan documents router, memory, context, plugins as separate subsystems). The main work is: (a) defining typed message contracts between subsystems, (b) building a graph parser for a config file, and (c) implementing the property injection pipeline.

**Tier: Tier 1** (breakthrough) -- This architecture change would fundamentally reshape how Lyra agents are built and deployed, enabling hot-swappable capabilities, A/B testing of different component combinations, and visual agent editing.

**Relevant caveat from TEN journey for Lyra:**
Watch out for the **process-per-session model** -- Lyra may not want OS process isolation for every session (it adds latency and resource overhead for simple tasks). The graph composition idea is separable from the process isolation model. Lyra should adopt the graph model with in-process node isolation (modules/threads) rather than TEN's OS-process-per-session.

**LICENSE note**: Apache 2.0 with additional restrictions. Cannot compete with Agora. For Lyra's purposes, the patent grant and Apache terms are fine (Lyra does not compete with Agora), but the "no end-user device hosting" clause and "no competing with Agora offerings" clause mean Lyra cannot fork or redistribute TEN itself without careful legal review. The transfer here is at the design/architecture level, not at the code level.
