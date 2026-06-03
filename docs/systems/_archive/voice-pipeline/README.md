# Voice Pipeline -- Learning Path

> **Phase:** 1 | **Composes blocks:** Agent Loop, MCP Adapter, Hooks & TDD Gate, Safety Monitor | **Architecture doc:** [07-voice-pipeline.md](../../architecture/07-voice-pipeline.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- voice interface for Lyra via two subsystems: VoiceInterface (command parsing with stub heuristics, entry API) and VoicePipeline (full-duplex streaming orchestrator, 413 lines), provider-swappable STT/TTS/VAD/Turn abstractions (873 lines) |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | 3 interaction modes (push-to-talk, wake word, full-duplex), pipeline state machine (IDLE, LISTENING, PROCESSING, SPEAKING, INTERRUPTED), barge-in architecture, provider registry pattern with hot-swappable components |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Provider ABC patterns (STTProvider, TTSProvider, VADProvider, TurnTakingProvider), stub-to-production migration strategy, streaming overlap for low latency, SFX and hooks integration, zero external dependencies |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Stub vs production model trade-offs, streaming vs batch latency, provider selection for STT/TTS, wake word detection strategies (Porcupine/Snowboy/openWakeWord) |
| 🔬 Evaluation | [evaluation.md](evaluation.md) | Latency budgets per pipeline stage, stub accuracy metrics (energy-threshold VAD), provider comparison baseline, test coverage status |

## In 30 Seconds

The Voice Pipeline adds voice interface capabilities to Lyra through two subsystems: a ready-to-use VoiceInterface (command parsing with energy-threshold VAD, keyword-based classification, stub heuristics) and a full-duplex VoicePipeline orchestrator (audio capture -> VAD -> STT -> LLM routing -> TTS -> playback with barge-in). All components use provider-swappable abstractions (STTProvider, TTSProvider, VADProvider, TurnTakingProvider ABCs with registry pattern). The architecture and stubs are complete, but production model integration (Whisper, Kokoro, Silero) is pending. Zero external dependencies in current state.

## What This System Composes

| Block | Role |
|-------|------|
| [Agent Loop](../../blocks/agent-loop/) | LLM routing and response generation within the voice pipeline |
| [MCP Adapter](../../blocks/mcp-adapter/) | Provider-swappable pattern used by STT/TTS/VAD abstractions (registry + ABC pattern) |
| [Hooks & TDD Gate](../../blocks/hooks-tdd/) | Pipeline event hooks (VoiceHookManager with 10 event types) and lifecycle integration |
| [Safety Monitor](../../blocks/safety-monitor/) | Audio content guardrails, wake word validation, and barge-in safety |

## Quick Reference

- **When you need this:** Adding voice input/output to Lyra, building STT->Agent->TTS pipelines, integrating wake word detection
- **Related architecture doc:** [07-voice-pipeline.md](../../architecture/07-voice-pipeline.md)
- **Upgrade plan:** [18-voice-mode.md](../../lyra-upgrade/plans/18-voice-mode.md)
- **Package:** `packages/lyra-voice/src/lyra_voice/` (5 source files, 1967 total lines)
- **Status:** Architecture & API definition complete; production model integration pending

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
