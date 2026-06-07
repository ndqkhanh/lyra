# Voice Pipeline — Block Spec

> A provider-swappable voice I/O pipeline: capture→VAD→STT→agent→TTS→playback. Two tiers: cascaded (Tier A, implemented) and full-duplex Inner Monologue (Tier B, implemented).

## Architecture

```
Microphone → VAD (Silero/WebRTC) → STT (Whisper/DeepSeek/Anthropic) → Agent Router → LLM → Safety Gate → TTS (ElevenLabs/Orpheus/OpenAI) → Speaker
                                                                              ↑
                                                                     Barge-in (semantic endpointing)
```

## Key Interfaces

| Component | File | Role |
|-----------|------|------|
| `VoicePipeline` | `src/lyra/voice/pipeline.py` | Orchestrates STT→LLM→TTS flow |
| `AudioCapture` | `src/lyra/voice/capture.py` | Microphone input + VAD |
| `STTProvider` | `src/lyra/voice/stt.py` | Speech-to-text adapter |
| `TTSProvider` | `src/lyra/voice/tts.py` | Text-to-speech adapter |
| `VoiceRouter` | `src/lyra/voice/router.py` | Task classification (simple/complex) |
| `InnerMonologueEngine` | `src/lyra/voice/inner_monologue.py` | Tier B: text-before-audio at 80ms |
| `FullDuplexHandler` | `src/lyra/voice/duplex.py` | Simultaneous listen+speak |
| `BilingualRouter` | `src/lyra/voice/bilingual.py` | VI+EN + code-switching |

## Latency Budget

| Stage | Target |
|-------|--------|
| VAD + AEC | 10ms |
| ASR (first partial) | 80-150ms |
| Endpointing | 50ms |
| LLM (simple) | 500-1000ms |
| TTS (first audio) | 200ms |
| **Total (simple)** | **~1.7s** |
| **Total (complex)** | **~4.7s** |

## → Dive Deeper

- [Voice Architecture](../architecture/07-voice-pipeline.md)
- [Innovation Doc](../innovations/voice-mode.md)
- [Voice Plan](../lyra-upgrade/plans/18-voice-mode.md)
