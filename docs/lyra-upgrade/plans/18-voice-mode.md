# Voice Mode — Ultra Plan (§4.18)

> ⭐ NEXT FLAGSHIP FEATURE — deepest research, most complete plan
> Run 1 — June 3, 2026

## Plain-Language Summary

Lyra's Voice Mode lets you talk to Lyra naturally — speak your requests, hear Lyra's responses, interrupt when you want, and have multi-turn conversations. It works across Vietnamese and English, runs locally for privacy (Whisper + Kokoro), and connects to cloud providers for higher quality when you want it. The key innovation: Lyra's voice pipeline is provider-swappable like its LLM backends — swap Whisper for Parakeet, Kokoro for Orpheus, without touching the agent core. The pipeline is: microphone → voice activity detection → speech-to-text → Lyra agent (same as text mode) → text-to-speech → speaker.

## 1. Problem

Terminal-based agents require typing. For mobile use, accessibility, multi-tasking, and natural interaction, voice is transformative. Current state: Lyra has ZERO voice capability. The goal is a full voice pipeline that matches or exceeds Claude Code's voice dictation while being provider-agnostic and supporting full-duplex conversation in Phase 2.

## 2. Evidence Synthesis

> Research corpus: §3.13 (voice frameworks, models, benchmarks) + §3.1 (Claude Code voice dictation) + §3.29 (multimodal desktop)

### 2.1 Voice Pipeline Components (from corpus deep-read)

**Speech-to-Text (STT):**
| Engine | WER (EN) | WER (VI) | Latency | Model Size | License |
|--------|----------|----------|---------|------------|---------|
| Whisper large-v3-turbo | 5.2% | 8.1% | ~400ms/30s | 1.5GB | MIT |
| Whisper large-v3 | 4.8% | 7.3% | ~800ms/30s | 3.0GB | MIT |
| NVIDIA Parakeet-CTC-1.1B | 4.2% | N/A | ~200ms/30s | 1.1B params | CC-BY-4.0 |
| NVIDIA Canary-1B | 3.8% | N/A | ~300ms/30s | 1.0B params | CC-BY-NC-4.0 |

**Text-to-Speech (TTS):**
| Engine | MOS | Latency | Model Size | Voice Cloning | License |
|--------|-----|---------|------------|---------------|---------|
| Kokoro-82M | 4.1 | <100ms/sentence | 82M params | No | Apache 2.0 |
| Orpheus-TTS | 4.3 | ~150ms/sentence | 3B params | Yes | Apache 2.0 |
| CSM (Sesame) | 4.2 | ~200ms/sentence | 1B params | Yes | Apache 2.0 |
| OpenAI TTS-1 | 4.4 | ~100ms/sentence | Proprietary | Limited | Proprietary |

**Voice Activity Detection (VAD):**
| Engine | Accuracy | Latency | Model Size | License |
|--------|----------|---------|------------|---------|
| Silero VAD | 96% | <1ms/frame | 1.3MB | MIT |
| WebRTC VAD | 90% | <1ms/frame | Tiny | BSD |

**Turn-Taking / Barge-In:**
| System | Barge-In Latency | Languages | Approach |
|--------|------------------|-----------|----------|
| Smart Turn (Pipecat) | <200ms | 23 incl. VI+EN | Semantic endpoint detection |
| OpenAI Realtime API | ~100ms | EN primarily | Server-side VAD + semantic turn |
| Moshi (Kyutai) | ~160ms | EN, FR | Full-duplex neural codec |

**Framework Comparison:**
| Framework | Language | Transport | Full-Duplex | License |
|-----------|----------|-----------|-------------|---------|
| Pipecat | Python | WebRTC/WebSocket | Yes | BSD |
| LiveKit Agents | Python/Node/Go | WebRTC | Yes | Apache 2.0 |
| TEN Framework | C++/Python/Go | WebRTC | Yes | Apache 2.0 |

### 2.2 Voice Benchmarks

**Full-Duplex-Bench v1** (2503.04721): Evaluates turn-taking, backchannel, interruption handling. Key metric: End-to-end latency, interruption success rate.

**Full-Duplex-Bench v3** (2604.04847): Adds disfluency handling and multi-step tool use during voice interaction. Key finding: cascaded systems match end-to-end on tool-use tasks but lag on emotional prosody.

**τ-Voice** (2603.13686): Full-duplex voice over verifiable real-world tasks. Combines voice with tool-use verification.

### 2.3 Claude Code Voice Dictation

From the Claude Code docs (§3.1):
- Push-to-talk model (hold a key, speak, release)
- Uses OS-level dictation where available
- Text appears in the input buffer (not sent directly)
- Supports editing before sending

## 3. Proposed Lyra Voice Architecture

### 3.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     LYRA VOICE PIPELINE                          │
│                                                                  │
│  ┌──────────┐   ┌─────┐   ┌──────────┐   ┌─────────┐   ┌─────┐ │
│  │ Microphone│──▶│ VAD │──▶│   STT    │──▶│  Lyra   │──▶│ TTS │─│─▶ Speaker
│  │ Capture   │   │     │   │ Engine   │   │  Agent  │   │     │ │
│  └──────────┘   └─────┘   └──────────┘   └─────────┘   └─────┘ │
│       │             │           │              │            │     │
│       │         ┌───┴───┐   ┌───┴──────┐   ┌───┴────┐   ┌──┴──┐ │
│       │         │Silero │   │Whisper    │   │Provider│   │Kokoro│ │
│       │         │ VAD   │   │lg-v3-turbo│   │Router  │   │ 82M  │ │
│       │         └───────┘   │(Primary)  │   │(§4.5)  │   └──────┘ │
│       │                     └───────────┘   └────────┘            │
│       │                     ┌───────────┐                         │
│       │                     │Parakeet   │ (Alt STT)               │
│       │                     │CTC-1.1B   │                         │
│       │                     └───────────┘                         │
│                                                                  │
│  ◀───────────── PROVIDER SWAPPABLE ─────────────────────────▶    │
│                                                                  │
│  CONTROL PLANE:                                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Barge-In  │  │Turn-Taking│  │Emotion   │  │Wake-Word     │   │
│  │Manager   │  │FSM        │  │Detection │  │Detector      │   │
│  └──────────┘  └───────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Interaction Modes

**Mode 1: Push-to-Talk (Phase 1 MVP)**
- Hold configured key (default: F2 or Ctrl+Shift+V)
- Speak while holding
- Release to transcribe
- Text appears in input buffer for review before sending
- Same as Claude Code's model

**Mode 2: Always-Listening with Wake Word (Phase 2)**
- Wake word: "Hey Lyra" (configurable)
- VAD gates audio → STT only when speech detected
- Wake word detection: lightweight on-device model (Porcupine or similar)
- Auto-send after brief silence (configurable timeout: 1-3s)
- Privacy: audio never leaves device until wake word detected

**Mode 3: Full-Duplex Conversation (Phase 3)**
- Barge-in: user can interrupt Lyra mid-response
- Semantic turn detection (Smart Turn) for natural turn-taking
- Backchannel support: Lyra provides "mm-hmm" during user speech
- Streaming TTS: response starts playing before full generation completes
- Emotion/prosody preservation

### 3.3 Provider-Abstraction Layer for Voice

```python
class STTProvider(Protocol):
    """Swappable STT backend."""
    async def transcribe(self, audio: bytes, language: str | None = None) -> str: ...
    @property
    def latency_ms(self) -> float: ...
    @property
    def supported_languages(self) -> list[str]: ...

class TTSProvider(Protocol):
    """Swappable TTS backend."""
    async def synthesize(self, text: str, voice: str = "default") -> bytes: ...
    async def stream_synthesize(self, text: str, voice: str = "default") -> AsyncIterator[bytes]: ...
    @property
    def latency_ms(self) -> float: ...

class VADProvider(Protocol):
    """Swappable VAD backend."""
    def detect_speech(self, audio_chunk: bytes) -> float: ...  # Returns probability
    def is_speech(self, audio_chunk: bytes, threshold: float = 0.5) -> bool: ...

class VoicePipeline:
    """Orchestrates STT → Agent → TTS with provider swapping."""
    def __init__(self, stt: STTProvider, tts: TTSProvider, vad: VADProvider): ...
    async def process_turn(self, audio: bytes) -> TurnResult: ...
    async def handle_barge_in(self) -> None: ...
```

### 3.4 Data Model

```
VoiceSession:
  id: UUID
  mode: push-to-talk | always-listening | full-duplex
  stt_provider: str  # "whisper-large-v3-turbo" | "parakeet-ctc-1.1b" | ...
  tts_provider: str  # "kokoro-82m" | "orpheus-tts" | ...
  vad_provider: str  # "silero-vad" | "webrtc-vad"
  language: str      # "en" | "vi" | "auto"
  voice_pack: str    # "default" | "warcraft-peon" | ...
  wake_word: str | None
  barge_in_enabled: bool
  emotion_detection: bool

Turn:
  id: UUID
  session_id: UUID → VoiceSession
  audio_input: bytes | None
  transcript: str | None
  agent_response: str | None
  audio_output: bytes | None
  latency: TurnLatency  # breakdown by stage
  barge_in_occurred: bool

TurnLatency:
  vad_ms: float
  stt_ms: float
  agent_ms: float
  tts_ms: float
  total_ms: float
```

### 3.5 Latency Budget

| Stage | Target (Phase 1) | Target (Phase 3) |
|-------|------------------|------------------|
| VAD | <5ms | <5ms |
| STT | <500ms | <200ms |
| Agent (first token) | <1000ms | <500ms |
| TTS (first audio) | <200ms | <100ms |
| Total E2E | <2000ms | <800ms |
| Barge-in detection | N/A | <200ms |

### 3.6 Voice Packs (§5.3 SFX Layer)

- **Warcraft Peon:** "Work complete!" on task finish, "Something need doing?" on wake
- **Portal Turret:** Sarcastic responses, "Are you still there?" on idle
- **HAL 9000:** Calm, measured responses, "I'm sorry, Dave" on errors
- **JARVIS:** Professional, British accent, "At your service, sir"
- Implemented via hook system (§4.10): `on_session_start`, `on_task_complete`, `on_error`

## 4. Build Outline

### Phase 1: Push-to-Talk MVP (4 weeks)

1. **Audio capture module** — microphone input via `pyaudio` or `sounddevice`; configurable device selection; sample rate normalization (16kHz mono for Whisper)
2. **Silero VAD integration** — load ONNX model; frame-by-frame speech probability; configurable threshold
3. **Whisper large-v3-turbo integration** — local inference via `faster-whisper` (CTranslate2 backend); 4-bit quantization for speed; language auto-detection
4. **Kokoro-82M TTS integration** — local inference; voice pack selection; streaming audio output
5. **Voice pipeline orchestration** — `VoicePipeline` class wiring STT → Agent → TTS
6. **Push-to-talk keybinding** — configure hook in Lyra keybindings; hold to record; release to transcribe
7. **Text buffer integration** — transcript appears in input buffer; editable before send
8. **Basic voice config** — `lyra voice config` command; provider selection; language; voice pack

### Phase 2: Always-Listening + Wake Word (4 weeks)

1. **Wake word detection** — Porcupine or OpenWakeWord; on-device; <100ms detection latency
2. **Always-listening mode** — audio ring buffer (last 2s); VAD + wake word → capture → STT → send
3. **Auto-send on silence** — configurable silence timeout; visual indicator of listening state
4. **Privacy controls** — audio never leaves device before wake word; optional local-only mode
5. **Turn-taking FSM** — idle → listening → processing → speaking → idle; state machine with timeout guards

### Phase 3: Full-Duplex Conversation (8 weeks)

1. **Smart Turn integration** — semantic endpoint detection; 23-language support including VI
2. **Barge-in handling** — detect user speech during TTS playback; interrupt and switch to listening
3. **Streaming TTS** — token-by-token audio generation; start playback before full response
4. **Emotion/prosody** — basic emotion detection in STT output; prosody markup in TTS
5. **Duplex state machine** — concurrent speaking + listening; backchannel support
6. **τ-Voice evaluation** — benchmark on full-duplex voice tasks

### Phase 4: Voice in lyra-desktop (§4.28) + Polish (4 weeks)

1. **Voice surface in desktop** — waveform visualization; transcript panel; voice config screen
2. **Multilingual VI+EN** — language switch mid-conversation; accent handling
3. **Voice pack marketplace** — community voice packs; hook-based SFX system
4. **Accessibility** — screen reader integration; voice-only mode

## 5. Multi-Provider Note

**STT providers are swappable** via the `STTProvider` protocol:
- Default: Whisper large-v3-turbo (MIT, local, best VI+EN)
- Alternative: NVIDIA Parakeet (requires API key, faster, EN only)
- Alternative: OpenAI Whisper API (cloud, best quality, costs $0.006/min)
- Alternative: Deepgram (cloud, real-time, costs $0.0059/min)

**TTS providers are swappable** via the `TTSProvider` protocol:
- Default: Kokoro-82M (Apache 2.0, local, fast)
- Alternative: Orpheus-TTS (Apache 2.0, local, expressive)
- Alternative: OpenAI TTS-1 (cloud, best quality, costs $0.015/1K chars)
- Alternative: ElevenLabs (cloud, voice cloning, costs $0.015/1K chars)

**Provider selection guided by §4.5 router** based on: quality requirements, latency budget, privacy needs, cost constraints.

## 6. Risks & Open Questions

1. **VI+EN quality gap:** Vietnamese ASR is harder than English. Whisper large-v3-turbo gets ~8% WER on VI vs ~5% on EN. Mitigation: fine-tune Whisper on VI data; use language-specific post-processing.
2. **Local inference resource usage:** Whisper large-v3-turbo uses ~1.5GB RAM + GPU. On CPU, latency may exceed budget. Mitigation: quantized models; fallback to cloud.
3. **Barge-in timing:** Sub-200ms barge-in is hard with cascaded systems. Mitigation: use Smart Turn's semantic endpoint detection; accept 300-500ms in Phase 1-2.
4. **Wake word false positives:** Background noise triggers wake word. Mitigation: two-stage detection (VAD + wake word); sensitivity tuning.
5. **Emotion/prosody preservation:** Cascaded STT→TTS loses emotion. Mitigation: Phase 3 explores full-duplex models (Moshi) that preserve prosody.

## 7. (A) Parity vs (B) Breakthrough

**(A) Parity:** Push-to-talk voice dictation matching Claude Code's voice feature — Whisper STT + Kokoro TTS + push-to-talk keybinding. Same feature set, provider-agnostic.

**(B) Breakthrough:** Full-duplex, barge-in-capable, multilingual voice conversation with emotion preservation, wake word, always-listening mode, and provider-swappable pipeline. The breakthrough is making the ENTIRE voice pipeline provider-swappable (like LLM providers) — no other agent system does this. Voice packs via hooks for personality.

**Link to BREAKTHROUGH-ARCHITECTURE.md:** Voice is Lyra's multimodal surface — the voice pipeline is one modality of the unified provider-abstraction layer. The same provider-swapping pattern applies to images, video, and other modalities in §4.28.

## 8. Baseline Delta

**Changes:** Adds entirely new voice subsystem (audio capture, VAD, STT, TTS, pipeline orchestration, interaction modes, voice packs)
**Keeps:** All existing text-mode functionality; agent core unchanged
**Replaces:** Nothing (greenfield)
**Migration cost:** New dependencies (faster-whisper, kokoro, pyaudio, silero-vad, porcupine); ~4 new Python modules

## 9. Expert Review

**Senior Voice/Audio Engineer:** "The cascaded architecture (Whisper→Agent→Kokoro) is the right Phase 1 choice — it's battle-tested, each component is independently best-in-class, and it's debuggable. Full-duplex in Phase 3 with Moshi or a similar end-to-end model is the right ambition but the technology isn't mature enough for Phase 1. The latency budget is realistic for push-to-talk, ambitious but achievable for full-duplex."

**Senior AI Engineer (LLMOps):** "Local Whisper inference on CPU will struggle with the latency budget — faster-whisper with INT8 quantization and CTranslate2 helps but test on target hardware. Consider a hybrid: local VAD + cloud STT for quality-critical use, local STT for privacy-critical use. The provider-swappable design enables this."

**Senior UX Designer:** "Push-to-talk is the safest interaction model for Phase 1 — users understand it, it eliminates the 'is it listening?' anxiety, and the edit-before-send step prevents voice misrecognition disasters. Always-listening with wake word is Phase 2 material and needs very clear visual indicators of listening state."

**Adversarial Skeptic:** "Voice mode is a massive engineering investment (20 weeks to Phase 3) for a feature that may have limited daily use. Most developers type faster than they speak for code tasks. The real value is in mobile/accessibility/multi-tasking use cases. Prove demand with Phase 1 (push-to-talk, 4 weeks) before committing to Phases 2-3."

**Resolution:** Phase 1 (push-to-talk) proceeds immediately as the MVP — it's small enough to validate demand. Phases 2-3 are gated behind Phase 1 usage data showing ≥20% of sessions use voice at least once.

## 10. References
- Pipecat: https://github.com/pipecat-ai/pipecat
- LiveKit Agents: https://github.com/livekit/agents
- Smart Turn: https://github.com/pipecat-ai/smart-turn
- Silero VAD: https://github.com/snakers4/silero-vad
- Moshi: https://github.com/kyutai-labs/moshi
- CSM: https://github.com/SesameAILabs/csm
- Kokoro: https://github.com/hexgrad/kokoro
- Orpheus: https://github.com/canopyai/Orpheus-TTS
- Whisper: https://github.com/openai/whisper
- NeMo: https://github.com/NVIDIA/NeMo
- Full-Duplex-Bench v1: https://arxiv.org/abs/2503.04721
- Full-Duplex-Bench v3: https://arxiv.org/abs/2604.04847
- τ-Voice: https://arxiv.org/abs/2603.13686
- Claude Code voice dictation: https://code.claude.com/docs/en/voice-dictation
- hermes-desktop: https://github.com/fathah/hermes-desktop

## 11. Changelog
- Run 1: Initial plan written — complete voice pipeline design, all 4 phases, provider-swappable architecture
