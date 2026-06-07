# livekit/agents -- Deep-Read

## 1. Headline Feature & Mechanism

**livekit/agents** is a Python framework for building realtime, programmable voice AI agents that run server-side. Its headline feature is the end-to-end orchestration of a **conversational voice pipeline** (STT -> LLM -> TTS) over **WebRTC** via the LiveKit media server, with built-in turn detection, interruption handling, multi-agent handoff, and a 50+ provider plugin ecosystem.

The core loop works as follows:
1. An `AgentServer` (formerly `Worker`) connects to LiveKit via protobuf-over-WebSocket and registers for job dispatch.
2. LiveKit sends job requests; the server's `request_fnc` decides whether to accept.
3. On acceptance, a **child process or thread** is spawned (via `ProcPool`) to run the entrypoint, providing process-level isolation and parallelism.
4. The entrypoint creates an `AgentSession` with configured STT, LLM, TTS, VAD, and turn-handling, then starts an `Agent` with instructions and tools.
5. `AgentSession` creates an `AgentActivity` -- the internal state machine that drives the `stt_node -> llm_node -> tts_node` pipeline as a chain of composable async generators.
6. The audio I/O flows through `RoomIO` (WebRTC tracks) or the Console CLI, with `RoomSessionTransport` for remote session management.

The critical architectural insight: **pipeline nodes are overridable async generators**. Every node in the pipeline (`stt_node`, `llm_node`, `transcription_node`, `tts_node`, `realtime_audio_output_node`) can be individually replaced by subclassing `Agent`, enabling fine-grained customization without forking the framework.

## 2. Architecture & Core Modules

### Module Layout
```
livekit-agents/livekit/agents/
+-- __init__.py          # Public API surface (re-exports)
+-- __main__.py          # CLI entry (python -m livekit.agents)
+-- worker.py            # AgentServer -- main coordinating process
+-- job.py               # JobContext, JobRequest, JobProcess
+-- plugin.py            # Plugin registration base class
+-- types.py             # Shared types (NotGiven, APIConnectOptions, etc.)
+-- language.py          # Language code definitions
+-- version.py           # Version string
+-- log.py               # Logging setup
+-- observability.py     # Tracing tags
+-- cli/                 # CLI commands (console, dev, start, connect)
|   +-- cli.py           # Rich TUI console, hot-reload watcher
|   +-- discover.py      # Agent source discovery
|   +-- proto.py         # IPC protobuf for CLI-agent communication
+-- voice/               # Core voice agent runtime
|   +-- agent.py         # Agent and AgentTask classes
|   +-- agent_session.py # AgentSession -- the main runtime orchestrator
|   +-- agent_activity.py # Internal state machine driving the pipeline
|   +-- turn.py          # Turn detection, endpointing, interruption configs
|   +-- generation.py    # Pipeline execution: LLM/TTS generation orchestrator
|   +-- io.py            # I/O abstractions (AgentInput, AgentOutput)
|   +-- room_io.py       # WebRTC room I/O
|   +-- run_result.py    # Test harness -- RunResult, event assertions
|   +-- speech_handle.py # Handle for managing speech lifecycle
|   +-- tool_executor.py # Tool/function execution engine
|   +-- endpointing.py   # End-of-utterance detection algorithms
|   +-- audio_recognition.py # Audio recognition pipeline
|   +-- events.py        # Event types (state changes, metrics, etc.)
|   +-- filler_scheduler.py # Background audio/filler scheduling
|   +-- background_audio.py # Background audio player
|   +-- remote_session.py    # Remote session transport
|   +-- recorder_io.py   # Audio recording
|   +-- amd/             # Answering Machine Detection
+-- llm/                 # LLM integration
|   +-- llm.py           # LLM abstract base class + LLMStream
|   +-- chat_context.py  # ChatContext, ChatMessage, Instructions
|   +-- tool_context.py  # Tool definitions, function_tool decorator
|   +-- realtime.py      # Realtime model interface (WebSocket-based)
|   +-- mcp.py           # MCP server integration
|   +-- fallback_adapter.py  # LLM fallback chain
+-- stt/                 # Speech-to-text interface + adapters
+-- tts/                 # Text-to-speech interface + adapters  
+-- inference/           # Remote model inference (LLM, STT, TTS)
+-- ipc/                 # Inter-process communication
|   +-- proc_pool.py     # Process/thread pool for job isolation
|   +-- job_executor.py  # Job executor base
|   +-- channel.py       # IPC channel
+-- evals/               # Testing framework
|   +-- evaluation.py    # Evaluator protocol, JudgeGroup, EvaluationResult
|   +-- judge.py         # JudgmentResult
+-- metrics/             # Metrics collection (LLM, STT, TTS, VAD, EOU, etc.)
+-- telemetry/           # OpenTelemetry integration + Prometheus
+-- tokenize/            # Text tokenization utilities
+-- utils/               # Audio, HTTP, connection pool, misc
```

### Data Flow Diagram
```
LiveKit Server <--WebSocket/Protobuf--> AgentServer (worker.py)
                                            |
                                       ProcPool (ipc/proc_pool.py)
                                      /             \
                          [Process/Thread 1]   [Process/Thread N]
                               |                       |
                          JobContext                 JobContext
                               |                       |
                          AgentSession              AgentSession
                               |                       |
                      [STT -> LLM -> TTS]      [STT -> LLM -> TTS]
                        pipeline nodes           pipeline nodes
```

### Entry Points
- **Production:** `python myagent.py start` -- starts AgentServer connected to LiveKit server
- **Development:** `python myagent.py dev` -- hot-reload mode
- **Testing:** `python myagent.py console` -- local audio I/O, no server needed
- **CLI utility:** `python -m livekit.agents download-files` -- download plugin model files

### Configuration
All configuration is done via constructor kwargs and environment variables:
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (required for server mode)
- `AgentServer` and `AgentSession` accept detailed configuration objects
- Plugin selection is import-based (just import the plugin package)

## 3. Performance/Benchmarks

The repo does **not publish pre-computed benchmark numbers**, but it has **comprehensive built-in latency telemetry** via OpenTelemetry histograms:

| Metric | Description | Instrument |
|--------|-------------|------------|
| `lk.agents.turn.e2e_latency` | End-to-end turn latency (user stops speaking -> agent starts speaking) | Histogram |
| `lk.agents.turn.llm_ttft` | LLM time to first token at pipeline level | Histogram |
| `lk.agents.turn.tts_ttfb` | TTS time to first byte at pipeline level | Histogram |
| `lk.agents.turn.transcription_delay` | End-of-speech to transcript available | Histogram |
| `lk.agents.turn.end_of_turn_delay` | End-of-speech to turn decision | Histogram |
| `lk.agents.connection.acquire_time` | WebSocket connection acquire time | Histogram |
| `lk.agents.usage.*` | Token/character/audio duration counters | Counter |

Per-metrics detail in `LLMMetrics`: `ttft` (time to first token), `duration`, `tokens_per_second`.
Per-metrics detail in `TTSMetrics`: `ttfb` (time to first byte), `audio_duration`.
Per-metrics detail in `STTMetrics`: `duration`, `audio_duration`, `acquire_time`.

These feed into CLI console display showing per-turn latency breakdowns (llm_ttft, tts_ttfb, e2e_latency in ms).

The `RealtimeModelMetrics` captures session-level metrics including `ttft` for the first audio token and `session_duration` for billing.

## 4. Trade-offs

### Wins
1. **Extremely modular plugin architecture**: 50+ provider plugins (OpenAI, Anthropic, Google, Deepgram, Cartesia, ElevenLabs, Azure, etc.) each as separate packages -- mix-and-match STT/LLM/TTS from different vendors per agent.
2. **Built-in WebRTC transport**: Leverages LiveKit's battle-tested WebRTC media server for audio/video transport; no need to build audio streaming infrastructure.
3. **Deep multi-agent handoff**: `AgentTask` (awaitable sub-agent) suspends the parent agent's state and resumes it after completion, enabling nested conversation flows with full state preservation.
4. **Rich built-in telemetry**: OpenTelemetry traces, Prometheus metrics, and per-turn latency histograms ship as part of the framework -- no bolt-on observability needed.
5. **Multiple runtime modes**: Console (local testing), dev (hot-reload), start (production) -- supports full development lifecycle.
6. **Process-level job isolation**: Each agent runs in its own process or thread via ProcPool, preventing crash propagation.
7. **Built-in test framework**: `RunResult` with event assertions (`expect.next_event().is_function_call(name=...)`) and LLM judges for behavioral evaluation.

### Loses
1. **Tightly coupled to LiveKit ecosystem**: Production use requires a LiveKit server (self-hosted or cloud). The console mode works standalone but doesn't exercise WebRTC.
2. **Significant internal complexity**: The `AgentActivity` state machine in `agent_activity.py` is ~3500 lines and handles intricate states (pipeline scheduling, interruption, forced interruption, AEC warmup, IVR detection, AMD, user away timeout, tool execution, multi-agent handoff, etc.).
3. **Process isolation overhead**: Job state must be serializable across process boundaries. Agent state (`ChatContext`, tool registrations) that cannot be pickled breaks process-mode execution.
4. **Ongoing API migration**: Many constructor parameters are deprecated and routed through migration functions (`_migrate_turn_handling` translates old flat kwargs to new `TurnHandlingOptions` dict). Multiple versions of APIs coexist.
5. **Plugin discovery is manual**: Plugins must be `import`-ed before use (though `__main__.py` does namespace scanning for `download-files`). No true automatic discovery.
6. **Documentation lives off-repo**: All API details defer to `docs.livekit.io/agents` -- the repo's docstrings are thorough but the conceptual docs are external.

## 5. Design Rationale

The framework's architecture is driven by three core realizations about voice AI:

1. **Voice is a pipeline, not a transaction.** Unlike chat APIs (request->response), voice AI requires continuous streaming through STT -> LLM -> TTS stages. Each stage has its own streaming contract, and the pipeline must handle backpressure, interruptions, and partial results. Hence the **async generator node pattern** -- each pipeline stage is a Python async generator that can be independently overridden.

2. **Voice agents need interruptible sequences.** A user might interrupt the agent mid-speech, requiring TTS to stop, transcript to update, and a new LLM turn to begin -- all while preserving the conversation context. The `AgentActivity` state machine handles `speaking -> (interrupt) -> listening -> (new turn) -> thinking -> speaking` transitions with safeguards like AEC warmup (ignore early interruptions caused by echo before acoustic echo cancellation stabilizes).

3. **Real voice apps have multiple phases.** A restaurant agent might start with an intro agent, hand off to a menu agent, then a reservation agent. The `AgentTask` mechanism (which is `await`-able and returns a typed result) enables this while automatically merging the sub-agent's chat context back into the parent.

The technical decisions flow from these:
- **Process pool** (`ipc/proc_pool.py`) for job isolation -- voice agents can be long-running, and a crash should not take down other agents.
- **WebSocket-based IPC** between server and agents -- enables hot-reload (server kills old processes, spawns new ones with updated code).
- **NotGiven** sentinel pattern throughout -- allows distinguishing "not set" from "set to None" for layered configuration resolution (agent-level overrides session-level defaults).
- **OpenTelemetry integration** -- not just for monitoring but for the recording/playback system that uploads session reports to LiveKit Cloud.

## 6. Transfer to Lyra

### Transferable Idea

Adopt LiveKit Agents' **pipeline-node architecture** for Lyra's multimodal processing pipeline. Instead of rigid tool-call chains or monolithic inference handlers, define composable async generator "nodes" (`stt_node`, `llm_node`, `tts_node`, `transcription_node`, `realtime_audio_output_node`) that can be individually overridden by subclassing. Combined with Lyra's planned router and plugin systems, each routing "lane" becomes a pluggable pipeline node.

This would allow Lyra users to:
- Swap only the STT provider without touching LLM or TTS config.
- Insert custom preprocessing nodes (e.g., audio normalization, profanity filtering) at any pipeline stage.
- Override the `llm_node` for one specific agent lane to use a realtime API while other lanes use standard chat completions.
- Layer on observability per-node (latency, token usage, error rates) using the same pattern.

### Workstream Route
**Section 4.x Pipeline Architecture** -- specifically **§4.3 (Modular Plugin Architecture)** or a new **§4.7 (Realtime/Multimodal Processing)** sub-section in the Lyra upgrade architecture document. The plugin interface pattern belongs in the plugin architecture section; the pipeline-node concept for multimodal processing could warrant its own section.

### Impact: 7/10 (High)
This is a foundational architectural pattern that would reshape how Lyra's processing pipeline is composed. The composable-node pattern directly addresses Lyra's need for multimodal and realtime agent support.

### Effort: 5/10 (Moderate)
The core concept is architecturally straightforward (async generators are already Python-native), but retrofitting existing Lyra processing paths into this pattern requires refactoring tool execution, context management, and error handling. Does not require new infrastructure -- just a redesign of the processing abstraction layer.

### Tier: Tier 1 (Architecture)

### License
**Apache 2.0** -- permissive, compatible with Lyra's license, allows both use and modification without restriction.
