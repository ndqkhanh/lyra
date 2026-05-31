# Implementation Backlog

**Purpose**: Track work discovered during implementation that the plans missed,
or non-blocking improvements deferred from reviews. Ranked by impact × effort.

---

## Deferred from Plans (known scope gaps)

| # | Item | Impact | Effort | Priority | Plan Ref |
|---|------|--------|--------|----------|----------|
| 1 | Wire lyra_provider into all capability packages (tools, MCP, skills, voice, permissions) | HIGH | LARGE | P0 | §4.5-§4.12 |
| 2 | GoogleProvider full adapter implementation | MEDIUM | MEDIUM | P1 | §4.5 |
| 3 | OpenWeightsProvider adapter | LOW | SMALL | P2 | §4.5 |
| 4 | Plugin system package (lyra-plugins) | MEDIUM | MEDIUM | P1 | §4.7 |
| 5 | Mermaid architecture diagrams in README | MEDIUM | SMALL | P1 | §6 |

## Stub Components in Voice/Audio/Speech (discovered during test audit)

| # | Item | Package | Impact | Effort | Priority |
|---|------|---------|--------|--------|----------|
| 1 | SpeechModule.transcribe() — returns `[Stub: ...]` placeholder message, not real STT. Real integration needed (Whisper/DeepSpeech). | lyra-speech | HIGH | LARGE | P0 |
| 2 | SpeechModule.synthesize() — generates silence WAV, not real TTS. Real synthesis required (Tacotron/FastSpeech/Bark). | lyra-speech | HIGH | LARGE | P0 |
| 3 | SpeechModule.identify_speaker() — hash-based stub, no real speaker embedding (d-vector/x-vector/ECAPA-TDNN). | lyra-speech | MEDIUM | LARGE | P1 |
| 4 | SpeechModule.detect_emotion() — amplitude variance proxy, no real emotion classifier (CNN-LSTM). | lyra-speech | MEDIUM | MEDIUM | P1 |
| 5 | VoiceInterface._stub_transcribe() — deterministic hash-to-phrase, no real STT engine. | lyra-voice | HIGH | LARGE | P0 |
| 6 | WhisperSTT._transcribe_stub() — fallback hash-to-phrase when faster-whisper unavailable. | lyra-voice | MEDIUM | MEDIUM | P1 |
| 7 | KokoroTTS — stub tone generator when torch/kokoro unavailable. Real KPipeline synthesis not wired. | lyra-voice | MEDIUM | MEDIUM | P1 |
| 8 | SileroVAD — ZCR+energy heuristics only (enhanced fallback), real Silero neural model path reserved but unused. | lyra-voice | LOW | MEDIUM | P2 |
| 9 | VoiceInterface.detect_wake_word() — energy + ZCR heuristic, no real wake word model (Porcupine/Snowboy). | lyra-voice | HIGH | LARGE | P0 |
| 10 | AudioPlayer.platform detection — only afplay/aplay/paplay/ffplay, no dedicated audio library (pygame/sounddevice). | lyra-audio | MEDIUM | SMALL | P2 |

## Discovered During Implementation

| # | Item | Discovered In | Impact | Effort | Priority |
|---|------|--------------|--------|--------|----------|
| 1 | Zero capability packages import from lyra_provider — provider abstraction is an island | Tier 4 scout audit | HIGH | LARGE | P0 |
| 2 | lyra-tools model_routing.py hardcodes Claude-only model IDs | Tier 4 scout audit | HIGH | MEDIUM | P0 |
| 3 | toolspec.py produces Anthropic-style schemas, not lyra_provider ToolSchema | Tier 4 scout audit | HIGH | MEDIUM | P0 |
| 4 | AVP middleware built but not universally wired into tool execution path | Tier 3 build | HIGH | LARGE | P0 |
| 5 | TKG write-path not universally enforced — memory as central nervous system is partial | Architecture audit | HIGH | LARGE | P0 |
| 6 | Per-tier review gate not executed (expert panel review) | Per-tier gate | HIGH | LARGE | P0 |
| 7 | End-to-end test-plan.md flow not executed | Final pass | HIGH | LARGE | P0 |
| 8 | Existing router test test_get_fallback_model is flaky (passes in isolation) | Tier 1 testing | LOW | SMALL | P2 |
| 9 | Agent loop in repl.py/oneshot.py uses empty ToolRegistry — no filesystem, search, MCP, or other tools wired | CLI agent-loop integration | HIGH | LARGE | P0 |
| 10 | run_agent_turn is synchronous per turn (AgentLoop.run is sync) — true async streaming from the LLM is not wired | CLI agent-loop integration | MEDIUM | MEDIUM | P1 |
| 11 | Budget cap (budget_cap_usd) is accepted but never enforced in AgentLoop | CLI agent-loop integration | MEDIUM | SMALL | P1 |
| 12 | Continuous multi-turn message transcript is not threaded through AgentLoop.run — each turn starts with a fresh transcript, losing conversation context | CLI agent-loop integration | HIGH | MEDIUM | P0 |
| 13 | Bare REPL (LyraREPL class, line 30) still uses legacy mock on_message — not wired to the agent loop | CLI agent-loop integration | LOW | SMALL | P2 |
| 14 | Session checkpoint metadata (token counts, message counts) not filled in by run_agent_turn — SessionManager.checkpoint() is never called | CLI agent-loop integration | MEDIUM | SMALL | P1 |
| 15 | oneshot.py does not persist to SessionStore — session is ephemeral | CLI agent-loop integration | LOW | SMALL | P2 |

## Review Deferrals (non-blocking nits)

| # | Item | Review | Impact | Effort | Priority |
|---|------|--------|--------|--------|----------|
| — | None yet (review gate not executed) | — | — | — | — |

---
