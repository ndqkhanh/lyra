# OpenAI Realtime API Documentation (OpenAI)

Source: https://developers.openai.com/api/docs/guides/realtime

## Key Technical Claims

1. Three distinct session types exist under a single API surface: voice-agent (conversational), translation (continuous speech translation), and transcription (streaming transcript deltas with no spoken response). Each has different lifecycle semantics.
2. Multiple transport protocols supported for the same API: WebRTC (browser/mobile), WebSocket (server-side), and SIP (telephony). Transport choice is orthogonal to session type.
3. GPT-Realtime-2 introduces configurable reasoning effort (low, medium, high) for speech-to-speech workflows, explicitly trading latency for reasoning depth.
4. GPT-Realtime-Whisper offers controllable latency via delay settings — lower delay yields earlier partial text, higher delay improves transcript quality.
5. The Realtime API is GA; the beta-to-GA migration involved removing the beta header, adopting new event names (e.g., `response.output_text.delta` replacing beta equivalents), and restructuring session configuration.

## Architecture/Mechanism Details

- **Session-type-based endpoints**: `/v1/realtime` (voice-agent), `/v1/realtime/translations` (translation), transcription sessions share a similar pattern.
- **WebRTC session establishment** uses `/v1/realtime/calls`; ephemeral credentials for untrusted clients are created via `POST /v1/realtime/client_secrets`.
- **Event model**: GA uses named delta events: `response.output_text.delta`, `response.output_audio.delta`, `response.output_audio_transcript.delta`. Standard lifecycle: client sends audio/text, listens for model responses, tool calls, and session events.
- **Tool integration**: Voice-agent sessions support function tools, MCP server connections, and webhook-driven server-side session control. For browser-based voice agents, the recommended path uses the Agents SDK with WebRTC.
- **Safety**: The `OpenAI-Safety-Identifier` header binds a stable, privacy-preserving identifier to a session. When using ephemeral tokens, it must be set at credential-creation time. Does not carry over from Responses API or other sessions.
- **Pricing**: No concrete numbers on this page; a "Managing costs" guide is referenced separately.

## Numbers & Benchmarks

- No concrete millisecond latency numbers, throughput figures, or benchmark comparisons are provided on this documentation page.
- The key numerical lever mentioned is `reasoning.effort` (low / medium / high) which directly controls the latency-vs-quality tradeoff.
- GPT-Realtime-Whisper's configurable delay is described qualitatively (lower -> earlier partials, higher -> better quality), with no specific ms values provided.

## Transfer to Lyra (one idea + SS4.x route)

**Transferable idea: Session-type-differentiated routing with orthogonal transport binding.**

OpenAI's Realtime API cleanly separates three concerns: (1) the session type determines lifecycle and event semantics, (2) the transport (WebRTC / WebSocket / SIP) determines how bits move, and (3) tool/MCP integration is a cross-cutting concern attached to voice-agent sessions. Lyra's current router and session management layers likely treat all sessions monolithically.

**Apply to Lyra**: Introduce a `SessionType` enum (e.g., `conversation`, `batch`, `stream`, `research`) at the router layer (SS4.2). Each type defines its own lifecycle rules (timeout, reconnect behavior, event schema) and transport binding (WebSocket vs. HTTP vs. gRPC). This decouples protocol handling from session semantics, making the system easier to extend with new interaction patterns without touching the core router.

**Workstream route**: SS4.2 (Agent Routing) for the session-type-based dispatch; SS4.4 (Session Management) for the type-specific lifecycle rules and event contracts.
