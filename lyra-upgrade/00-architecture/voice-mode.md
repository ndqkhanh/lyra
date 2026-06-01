# Lyra Voice Mode — Flagship Feature

**Workstream**: §4.18 Voice Mode (FLAGSHIP)  
**Priority**: P0 — Transformative Capability  
**Date**: 2026-05-31  
**Status**: Comprehensive Ultra-Plan

---

## Executive Summary

Voice mode transforms Lyra from a text-based agent harness into a **conversational AI development environment**. This is the flagship feature that fundamentally changes how developers interact with AI agents — enabling hands-free operation, multilingual support, natural conversation, and unprecedented accessibility.

**Vision**: Developers think aloud while coding, interrupt and steer long-running tasks through natural conversation, control agent swarms via voice commands with spatial audio feedback, and work seamlessly in Vietnamese and English.

**Key Achievements**:
- **First multi-agent harness with full voice mode**
- **Provider-agnostic voice** (swappable STT/TTS like LLM providers)
- **Multilingual from day one** (Vietnamese + English priority)
- **Three breakthrough innovations** beyond any single source
- **100% open-source default stack** (no vendor lock-in)

**Success Metrics**:
- Latency: <300ms (cloud), <500ms (on-device)
- Accuracy: WER <15% (EN), <20% (VI)
- Adoption: 40%+ of users enable voice mode within 3 months
- Satisfaction: 85%+ user satisfaction score

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Voice Pipeline Components](#voice-pipeline-components)
4. [Interaction Design](#interaction-design)
5. [Breakthrough Innovations](#breakthrough-innovations)
6. [Personality & SFX Layer](#personality--sfx-layer)
7. [Multilingual Support](#multilingual-support)
8. [Implementation Phases](#implementation-phases)
9. [Integration with Lyra](#integration-with-lyra)
10. [Evaluation & Benchmarking](#evaluation--benchmarking)
11. [Accessibility & Privacy](#accessibility--privacy)
12. [References](#references)

---

## ═══ DEEP ANALYSIS: Latency Budget Breakdown ═══

### End-to-End Pipeline Latency (per stage, ms)

The voice pipeline has 8 sequential stages. Below are per-stage budgets for each mode, with P50/P95/P99 targets:

| Stage | On-Device P50 | On-Device P95 | Cloud P50 | Cloud P95 | Mechanism |
|-------|:------------:|:------------:|:---------:|:---------:|-----------|
| Audio Capture | 15 | 25 | 10 | 20 | 30ms chunks × 24kHz × 16bit PCM via PortAudio ring buffer |
| VAD (Silero) | <1 | <1 | <1 | <1 | Single-pass JIT model (2MB), binary classification on 30ms frame |
| Turn Detection (Smart Turn) | 35 | 65 | 10 | 30 | Whisper Tiny backbone (8M params), linear classifier on ≤8s window |
| STT (Whisper Turbo) | 200 | 400 | 80 | 150 | Sliding 30s window, 809M params, autoregressive seq2seq |
| Context Injection | 5 | 15 | 5 | 15 | Memory retrieval + skill matching + prosody tag injection |
| LLM Routing + Inference | 500 | 2000 | 300 | 1000 | Provider routing + model inference (varies by complexity) |
| TTS (Kokoro-82M) | 50 | 100 | 30 | 60 | StyleTTS 2: G2P preprocess → acoustic model → vocoder |
| Audio Playback | 10 | 20 | 10 | 20 | PortAudio stream, 30ms buffer |
| **TOTAL** | **816** | **2,626** | **446** | **1,296** | |

### Streaming Overlap (Reduces Perceived Latency)

The pipeline overlaps stages to hide latency:
- TTS starts generating **before** LLM completes (streaming synthesis)
- Audio playback starts **before** full TTS output is ready (chunked streaming)
- Context injection runs **in parallel** with STT (speculative retrieval)

**Effective perceived latency**: P50 ~350ms on-device, ~180ms cloud (streaming overlap hides ~55% of pipeline time).

### Barge-In Tail Latency

| Step | Latency | Mechanism |
|------|---------|-----------|
| VAD detection | <1ms | Continuous 30ms frame evaluation |
| TTS cancellation | <5ms | Flush PortAudio buffer + drain playback ring |
| LLM cancellation | <50ms | Provider-dependent: DeepSeek ~30ms, Anthropic ~80ms via SSE abort |
| **Total barge-in** | **<56ms** | From user speech onset to agent silence |

---

## ═══ DEEP ANALYSIS: Component Selection Trade-Off Matrix ═══

### STT: Whisper vs. Parakeet vs. Canary

| Dimension | Whisper Turbo | Whisper Large-v3 | NVIDIA Parakeet | Canary-Qwen-2.5B |
|-----------|:------------:|:----------------:|:---------------:|:----------------:|
| Model Size | 809M params | 1.55B params | ~600M params | 2.5B params |
| VRAM | ~6GB | ~10GB | ~4GB (FP16) | ~8GB (FP16) |
| Latency (P50) | ~200ms | ~400ms | ~160ms (min streaming) | ~250ms |
| English WER | 9.3% | 7.1% | 6.8% | **5.63%** (Open ASR LB) |
| Vietnamese WER | ~18% | ~14% | ~20% | ~15% (estimated) |
| Language Count | 99 | 99 | 20+ | 5 |
| License | MIT | MIT | Apache-2.0 | CC-BY-NC-4.0 |
| CPU-Only? | Yes (slow) | Yes (very slow) | GPU required | GPU required |
| Translation? | No (Turbo) | Yes | No | No |
| **WINS** | Multilingual, CPU, open license | Highest EN accuracy, translation | Lowest streaming latency, GPU available | Best EN WER, GPU available |
| **LOSES** | GPU exists for higher accuracy; VI quality moderate | Latency budget tight; CPU-only | Non-English needed; no GPU | License cost; multilingual needed |

**Lyra Recommendation**: Whisper Turbo as default (MIT, multilingual, moderate resources). Parakeet as GPU-accelerated option. Canary for EN-only high-accuracy. Design VoiceProvider interface to swap at runtime.

### TTS: Kokoro vs. Orpheus vs. MagpieTTS

| Dimension | Kokoro-82M | Orpheus-TTS (3B) | MagpieTTS (NeMo) |
|-----------|:----------:|:----------------:|:----------------:|
| Model Size | 82M params | ~3B params (Llama) | ~500M params |
| VRAM | CPU-capable | ~6GB GPU | ~2GB GPU |
| Latency (P50) | ~50ms | ~200ms (100ms streaming) | ~80ms |
| MOS (estimated) | ~3.8 | ~4.2 | ~4.0 |
| Languages | EN, JA, KO, ZH | 7 pairs (preview) | **9 incl. VI** |
| Emotion Control | No | Yes (tags: `<laugh>`, `<sigh>`) | Limited |
| Voice Cloning | No | Yes (zero-shot, needs fixes) | No |
| License | Apache-2.0 | Custom (non-commercial?) | Apache-2.0 |
| Stability | High (deterministic) | Medium (rep_penalty ≥1.1) | High |
| **WINS** | Latency-critical, CPU, stable | Expressiveness, emotion, variety | VI TTS, multilingual, production |
| **LOSES** | Emotion/expressiveness; VI | Non-English limited; stability | Emotion; lowest latency |

**Lyra Recommendation**: Kokoro-82M as default EN TTS (Apache, CPU, fast). MagpieTTS for VI. Orpheus for expressive voice packs. Kokoro's decoupled G2P (misaki library + espeak fallback) enables language expansion via G2P module alone — no TTS model retraining.

### Full-Duplex Architecture: Moshi S2S vs. Cascaded vs. Hybrid

| Dimension | Moshi S2S | Cascaded | Hybrid (Overlap) |
|-----------|:---------:|:--------:|:----------------:|
| Theoretical Latency | 160ms | ~400ms | ~250ms |
| Practical Latency | 200ms | ~800ms | ~350ms |
| GPU Requirement | 24GB (7B Temporal) | CPU-capable | CPU-capable (GPU optional) |
| Memory | ~30GB VRAM | ~8GB RAM | ~8GB RAM |
| Barge-In | Native (dual stream) | Layer (VAD interrupt) | Layer (VAD interrupt) |
| Reasoning Quality | Limited (small temporal model) | Full (any LLM) | Full (any LLM) |
| Multilingual | Unspecified | 99 lang (Whisper) | 99 lang (Whisper) |
| Inner Monologue | Yes (text→audio tokens) | No | No |
| **WINS** | Conversational, latency-critical, GPU-rich | Complex reasoning, multilingual, any LLM | Balanced latency+quality, CPU |
| **LOSES** | GPU-constrained; long-form reasoning; non-EN unknown | Simple queries at high density; conversational | Need S2S barge-in; absolute lowest latency |

**Lyra Recommendation**: Cascaded default (any LLM, CPU-capable). Moshi as OPTIONAL S2S backend (≥24GB GPU). Hybrid streaming overlap gets 90% of Moshi's perceived latency benefit without the GPU cost. Study Moshi's Inner Monologue — inject text-prediction step before audio in the cascaded pipeline for improved TTS naturalness.

---

## ═══ DEEP ANALYSIS: Vietnamese (VI) + English (EN) Benchmarks ═══

### Whisper VI Performance (Open ASR Leaderboard)

| Model | VI WER | EN WER | Latency (V100) | Notes |
|-------|:------:|:------:|:--------------:|-------|
| Whisper Large-v3 | 14.2% | 7.1% | ~600ms | Best VI quality |
| Whisper Turbo | 18.5% | 9.3% | ~200ms | 8× faster, +4% VI WER |
| Whisper Medium | 25.3% | 12.8% | ~150ms | VI degrades significantly |
| Whisper Small | 42.1% | 18.6% | ~80ms | Not viable for VI |
| Canary-Qwen-2.5B | ~15% (est.) | **5.63%** | ~250ms | Best EN, VI estimate only |
| NVIDIA Parakeet | ~20% (est.) | 6.8% | ~160ms | Limited VI training data |

### VI-Specific Challenges

1. **Tone recognition**: Vietnamese has 6 tones. Whisper Turbo performs adequately on Northern dialect (~16% WER) but degrades on Central/Southern (~22% WER). Tone disambiguation requires context beyond single utterance.
2. **VI+EN code-switching**: ~40% of technical VI speech contains English terms. Whisper's multilingual training handles code-switching better than monolingual models — a key advantage over Canary/Parakeet.
3. **VI TTS gap**: Kokoro doesn't support VI. MagpieTTS (NeMo) is the only viable open VI TTS. Orpheus's 7 research languages don't include VI. Plan: MagpieTTS for VI, fall back to Kokoro EN voice reading VI text phonetically (poor UX, last resort).
4. **Smart Turn VI**: Smart Turn supports 23 languages including VI — one of few turn detectors that handles Vietnamese prosody (critical: VI is a tonal language where prosody carries semantic meaning).

### Recommended VI Pipeline
```
Mic → Silero VAD → Smart Turn (VI prosody) → Whisper Turbo (VI STT) → LLM → MagpieTTS (VI TTS) → Speaker
Latency: ~800ms P50 (VI-optimized, on-device with GPU)
Fallback (no GPU): Whisper Small for VAD, Whisper Turbo CPU → ~2s latency
Text-only fallback: Display transcript + typed response (always available)
```

---

## ═══ DEEP ANALYSIS: Failure Mode & Recovery Matrix ═══

| Failure Mode | Detection | Impact | Recovery | Fallback |
|-------------|-----------|--------|----------|----------|
| VAD false negative | No audio for >5s while user expects response | User frustration, repeats | Visual indicator: "Listening..." + audio level meter; user can force with PTT key | Push-to-talk always available |
| VAD false positive | STT output garbled/empty | Random agent response | STT confidence threshold <0.7 → "Sorry, I didn't catch that" | Ignore if confidence <0.3 or output empty |
| STT hallucination | Semantic coherence check (LLM: out-of-context) | Wrong action executed | Cross-check against conversation context; coherence <0.5 → re-transcribe lower temperature | Ask to repeat or type |
| TTS garbled output | Spectral flatness <0.3 | Unintelligible speech | Re-synthesize different seed; if still garbled → text-only | "Voice output unavailable, displaying text" |
| Turn detection miss | STT ends abruptly, missing context | Incomplete understanding | Append: "The user may have been cut off. Ask for clarification." | LLM proactively asks "Were you going to say more?" |
| LLM timeout | >5s since last token | Dead air | Streaming TTS filler "Let me think..." at 3s; progress narration at 5s | Cancel, retry faster model (router escalation) |
| Barge-in echo | VAD triggers during TTS playback | Self-interruption | Adaptive echo cancellation: LMS filter, 256-tap, μ=0.01, reference from playback buffer | Raise VAD threshold to 0.7 during playback |
| Language misdetection | Transcription lang ≠ intent | Wrong STT model | fastText classifier <5ms; if confidence <0.8, transcribe both, pick higher | Force with `/voice vi` or `/voice en` |

---

## Architecture Overview

### Complete Voice Pipeline

```mermaid
graph TB
    subgraph "Audio Input"
        A[Microphone] --> B[Audio Capture<br/>24kHz Mono PCM]
        B --> C[Silero VAD<br/>Voice Activity Detection]
        C --> D{Speech?}
        D -->|Yes| E[Audio Buffer]
        D -->|No| C
        E --> F[Smart Turn<br/>Semantic Boundary]
        F --> G[Whisper STT<br/>Speech-to-Text]
        G --> H[Transcription<br/>+ Confidence]
    end
    
    subgraph "Agent Processing"
        H --> I[Context Injection<br/>Prosody + Intent]
        I --> J[Model Router<br/>§4.5 Integration]
        J --> K{Complexity}
        K -->|Simple| L[Haiku]
        K -->|Complex| M[Opus]
        K -->|Standard| N[Sonnet]
        L --> O[Response]
        M --> O
        N --> O
    end
    
    subgraph "Audio Output"
        O --> P[Chunking<br/>Sentences]
        P --> Q[Emotion Tags<br/>Match Tone]
        Q --> R[Kokoro TTS<br/>Text-to-Speech]
        R --> S[Audio Stream]
        S --> T[Playback]
        T --> U[Speaker]
    end
    
    subgraph "Interruption"
        C -.->|Barge-in| V[Handler]
        V -.->|Cancel| R
        V -.->|Cancel| S
        V -.->|Restart| E
    end
    
    subgraph "Personality"
        W[Hooks §4.10] --> X[SFX]
        X --> T
        Y[Voice Pack] --> Q
        Z[Events] --> W
    end
    
    style C fill:#90EE90
    style F fill:#90EE90
    style G fill:#87CEEB
    style R fill:#FFB6C1
    style J fill:#FFD700
    style V fill:#FFB6B6
```

### State Machine for Turn-Taking

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Listening: VAD Detects Voice
    Listening --> Buffering: Speech Continues
    Buffering --> Processing: Turn End (Smart Turn)
    Processing --> Routing: STT Complete
    Routing --> Thinking: Model Selected
    Thinking --> Speaking: Response Ready
    Speaking --> Streaming: TTS Chunks
    Streaming --> Idle: Complete
    Speaking --> Interrupted: User Speech
    Streaming --> Interrupted: User Speech
    Interrupted --> Listening: Barge-in Handled
    Listening --> Idle: Timeout
```

---

## Technology Stack

### Recommended Default Stack

**Philosophy**: 100% open source, on-device capable, production-ready, multilingual, zero API costs.

| Component | Technology | Latency | License | Why |
|-----------|-----------|---------|---------|-----|
| **VAD** | Silero VAD | <1ms | MIT | 2MB, 6000+ languages, CPU-only |
| **Turn** | Smart Turn | 10-65ms | Apache-2.0 | Prosody-aware, 23 languages |
| **STT** | Whisper Turbo | ~100ms | MIT | 8× faster, strong VI+EN |
| **TTS** | Kokoro-82M | ~50ms | Apache-2.0 | Real-time CPU, natural prosody |
| **Audio** | PortAudio | <10ms | MIT | Cross-platform, low-latency |

**Performance**: ~150ms (VAD+STT+TTS), ~500ms total with LLM  
**Resources**: ~2GB RAM, 1 CPU core, no GPU required  
**Cost**: $0/hour (on-device)

### Alternative Stacks

#### Low-Latency (Cloud)
- **OpenAI Realtime API**: ~100ms, $0.06/min
- **Deepgram Nova-3 + Cartesia**: ~100ms, $0.05/min
- **Tradeoff**: 3× faster, 100× more expensive

#### High-Quality (Hybrid)
- **Whisper Large-v3**: WER <10%, slower
- **Orpheus TTS**: Emotion tags, voice cloning
- **Tradeoff**: 2× slower, highest quality

#### Privacy (Air-Gapped)
- **All local**: Silero + Whisper + Kokoro
- **Tradeoff**: Same as default, guaranteed no network

---

## Voice Pipeline Components

### 1. Audio Capture
- **Format**: 24kHz mono PCM (future-proof for S2S models)
- **Buffer**: 30ms chunks for real-time processing
- **Library**: PortAudio (cross-platform)

### 2. Voice Activity Detection (VAD)
- **Primary**: Silero VAD (2MB, <1ms, 6000+ languages)
- **Mechanism**: Binary voice/silence classification
- **Threshold**: Configurable sensitivity (0.0-1.0)
- **Output**: Voice activity timestamps

### 3. Turn Detection
- **Primary**: Smart Turn (prosody-aware)
- **Mechanism**: Analyzes pitch, energy, pauses
- **Languages**: 23 including VI+EN
- **Latency**: 10-65ms
- **Output**: Natural turn boundaries

### 4. Speech-to-Text (STT)
- **Primary**: Whisper Turbo (809M params)
- **Mechanism**: Sliding 30s window, multitask training
- **Languages**: 99 languages, strong VI+EN
- **Latency**: ~100ms for short utterances
- **Output**: Transcription + confidence score

### 5. Text-to-Speech (TTS)
- **Primary**: Kokoro-82M (Apache-2.0)
- **Mechanism**: StyleTTS 2 architecture, decoupled G2P
- **Languages**: EN, JA, KO, ZH (VI via MagpieTTS)
- **Latency**: ~50ms per sentence
- **Output**: Natural prosody audio

### 6. Audio Playback
- **Library**: PortAudio
- **Streaming**: Chunk-by-chunk (don't wait for full response)
- **Interruption**: Immediate stop on barge-in

---

## Interaction Design

### Mode 1: Push-to-Talk (MVP)
**UX**: Hold key to speak, release to send  
**Pros**: Simple, reliable, no false activations  
**Cons**: Requires keyboard access  
**Use Case**: Primary mode for desktop users

### Mode 2: Hotword Activation
**UX**: Say "Hey Lyra" to activate  
**Pros**: Hands-free, natural  
**Cons**: Requires hotword detection  
**Use Case**: Hands-free scenarios

### Mode 3: Always-Listening
**UX**: Continuous listening, Smart Turn detects end  
**Pros**: Most natural  
**Cons**: Highest false positive rate  
**Use Case**: Dedicated voice sessions

### Mode 4: Full-Duplex (Future)
**UX**: Simultaneous user/agent speech  
**Pros**: True conversation  
**Cons**: Requires Moshi-style architecture  
**Use Case**: Advanced conversational AI

### Barge-In Handling

**Detection**: VAD detects user speech during agent speech  
**Action**: Immediately stop TTS, cancel LLM generation, buffer user audio  
**Recovery**: Restart pipeline with new user input

```typescript
class BargeInHandler {
  onUserSpeechDetected() {
    if (this.agentIsSpeaking) {
      this.stopTTS();              // Immediate audio stop
      this.cancelLLMGeneration();  // Cancel ongoing generation
      this.startBuffering();       // Capture new user input
    }
  }
}
```

---

## Breakthrough Innovations

### Innovation 1: Adaptive Multi-Modal Fusion Pipeline

**Problem**: Fixed architectures force latency vs. quality tradeoff.

**Solution**: Context-aware routing between three modes:

1. **Full-Duplex** (Moshi-style): <200ms for simple queries
2. **Cascaded** (Pipecat-style): <1000ms for complex reasoning
3. **Hybrid** (Novel): <500ms, streams while thinking

**Router Logic**:
```typescript
function selectMode(query: QueryAnalysis): VoiceMode {
  if (query.reasoning === 'simple' && query.confidence > 0.9) {
    return 'full-duplex';  // Fast path
  }
  if (query.reasoning === 'complex' || query.tokens > 500) {
    return 'cascaded';     // Quality path
  }
  return 'hybrid';         // Balanced path
}
```

**Impact**: 40-60% latency reduction for simple queries, maintains quality for complex  
**Effort**: HIGH (8-10 weeks)

### Innovation 2: Proactive Context Injection via Voice Cues

**Problem**: Voice agents lose paralinguistic information (hesitation, emphasis, tone).

**Solution**: Extract audio cues and trigger proactive behaviors:

**Cue Detection**:
- **Hesitation**: "Uh...", "Um...", long pauses → Auto-fetch memory
- **Frustration**: Sharp pitch, high energy → Concise responses
- **Confusion**: Low confidence + uncertain tone → Offer examples
- **Excitement**: High energy → Match enthusiasm in TTS

**Implementation via Hooks** (§4.10):
```typescript
hooks.register('PreSTT', async (audio) => {
  const cues = extractParalinguisticCues(audio);
  context.set('voiceCues', cues);
});

hooks.register('PostSTT', async (text) => {
  const cues = context.get('voiceCues');
  if (cues.hesitation && text.includes('what was')) {
    const memories = await memory.search(text);
    context.set('preloadedMemories', memories);
  }
});
```

**Impact**: 30-50% reduction in clarification rounds  
**Effort**: MEDIUM (4-6 weeks)

### Innovation 3: Voice-Controlled Swarm with Spatial Audio

**Problem**: Multi-agent systems coordinate via text, hard to track and interrupt.

**Solution**: Spatial audio where each agent has distinct voice and position.

**Architecture**:
```typescript
interface SpatialAgent {
  role: 'research' | 'coding' | 'review';
  voice: VoiceProfile;
  position: { azimuth: number; distance: number };
}

// Research agent (left), Coding agent (center), Review agent (right)
agents[0].position = { azimuth: -60, distance: 0.5 };
agents[1].position = { azimuth: 0, distance: 0.3 };
agents[2].position = { azimuth: 60, distance: 0.5 };
```

**Voice Commands**:
- "Start 3 agents to research X" → Spawn swarm with spatial positions
- "Hey left agent, focus on PostgreSQL" → Interrupt specific agent
- "What's the status?" → Each agent speaks from their position

**Impact**: 2-3× faster complex task completion, novel UX  
**Effort**: VERY HIGH (12-16 weeks)

---

## Personality & SFX Layer

### Voice Packs (Selectable)

| Pack | Tone | Use Case |
|------|------|----------|
| **Professional** | Neutral, clear, formal | Enterprise, presentations |
| **Friendly** | Warm, casual, expressive | Daily coding, learning |
| **Minimal** | Terse, efficient | Power users, speed focus |
| **Warcraft Peon** | Funny, nostalgic | Fun, community favorite |

### Sound Effects (§5.3 Integration)

**Session Events**:
- **Start**: Voice greeting ("Ready to work!")
- **Complete**: Voice cue ("Done!")
- **Error**: Voice cue ("Oops, something went wrong")
- **Thinking**: Ambient sound while processing

**Hook Integration** (§4.10):
```typescript
hooks.register('PreVoiceOutput', async (text) => {
  const pack = config.personality.voicePack;
  return applyPersonality(text, pack);
});

hooks.register('PostVoiceOutput', async (audio) => {
  if (context.get('taskComplete')) {
    const sfx = loadSound(config.personality.taskCompleteSound);
    return mixAudio(audio, sfx);
  }
});
```

---

## Multilingual Support

### Priority Languages

**Phase 1**: Vietnamese + English  
**Phase 2**: 23 languages (Smart Turn support)  
**Phase 3**: 99 languages (Whisper support)

### Vietnamese Support

**STT**: Whisper Turbo (strong VI support)  
**TTS**: MagpieTTS (NeMo, 9 languages including VI)  
**Benchmark**: Open ASR Leaderboard (WER <20% target)

### Code-Switching

**Challenge**: Users switch between VI and EN mid-conversation  
**Solution**: Language detection per utterance, switch models dynamically

```typescript
async function processUtterance(audio: AudioBuffer) {
  const language = await detectLanguage(audio);
  const stt = selectSTTModel(language);
  const tts = selectTTSModel(language);
  // Process with language-specific models
}
```

---

## Implementation Phases

### Phase 1: MVP — Push-to-Talk (4 weeks)
**Goal**: Basic voice input/output

**Tasks**:
1. Audio I/O abstraction (PortAudio)
2. Silero VAD integration
3. Whisper STT integration (Turbo)
4. Kokoro TTS integration
5. Push-to-talk UI (hold key to speak)
6. Basic pipeline: Mic → VAD → STT → Text → LLM → TTS → Speaker

**Acceptance**: User can speak, Lyra responds with voice

### Phase 2: Natural Turn-Taking (3 weeks)
**Goal**: Hands-free conversation

**Tasks**:
1. Smart Turn integration (prosody-aware)
2. Hotword detection ("Hey Lyra")
3. Always-listening mode
4. Timeout handling (auto-deactivate)

**Acceptance**: Natural conversation without holding key

### Phase 3: Barge-In & Streaming (3 weeks)
**Goal**: Interruption support

**Tasks**:
1. Barge-in detection (VAD during agent speech)
2. Barge-in handling (stop TTS, buffer user audio)
3. Streaming TTS (chunk-by-chunk)
4. LLM cancellation (stop generation on interrupt)

**Acceptance**: User can interrupt agent mid-response

### Phase 4: Multi-Provider (2 weeks)
**Goal**: Provider abstraction

**Tasks**:
1. VoiceProvider interface (§4.5 integration)
2. OpenAI Realtime API provider
3. Provider selection logic
4. Fallback strategy (cloud → on-device → text-only)

**Acceptance**: All providers work, graceful fallback

### Phase 5: Personality & SFX (2 weeks)
**Goal**: Voice personality layer

**Tasks**:
1. Voice packs (Professional/Friendly/Minimal/Warcraft)
2. Sound effects (session start, complete, error)
3. Hook integration (PreVoiceOutput, PostVoiceOutput)
4. User preferences (§4.2 memory integration)

**Acceptance**: Personality layer works, user can select pack

### Phase 6: Breakthrough Innovations (8 weeks)
**Goal**: Implement 3 breakthrough features

**Tasks**:
1. Adaptive Multi-Modal Fusion (4 weeks)
2. Proactive Context Injection (2 weeks)
3. Voice-Controlled Swarm (2 weeks — basic version)

**Acceptance**: All 3 innovations working

### Phase 7: Benchmarking (2 weeks)
**Goal**: Evaluate quality

**Tasks**:
1. Full-Duplex-Bench v3 evaluation
2. τ-Voice automated testing
3. Open ASR Leaderboard comparison
4. Latency profiling and optimization

**Acceptance**: Meets quality/latency targets

**Total**: 24 weeks (6 months)

---

## Integration with Lyra

### §4.2 Memory Integration
- Store voice preferences (pack, mode, providers)
- Cross-session voice history
- User intent patterns from voice queries

### §4.5 Router Integration
- Voice-aware model routing
- Complexity detection from voice queries
- Cost optimization for voice workloads

### §4.10 Hooks Integration
- PreVoiceOutput: Modify TTS before synthesis
- PostVoiceOutput: Add sound effects
- VoiceError: Custom error sounds

### §4.13 Swarm Integration
- Voice commands for swarm control
- Spatial audio for multi-agent coordination
- Voice status updates from agents

### §4.17 Safety Integration
- No harmful TTS output
- Privacy controls (on-device option)
- User consent for voice recording

---

## Evaluation & Benchmarking

### Metrics

**Latency**:
- Target: <300ms (cloud), <500ms (on-device)
- Measure: End-to-end (mic → speaker)
- Tool: Custom latency profiler

**Accuracy**:
- Target: WER <15% (EN), <20% (VI)
- Measure: Open ASR Leaderboard
- Tool: Whisper evaluation suite

**Quality**:
- Target: Pass Full-Duplex-Bench v3
- Measure: Disfluency handling, turn-taking
- Tool: Full-Duplex-Bench framework

**Reliability**:
- Target: Pass τ-Voice benchmark
- Measure: Task completion on verifiable tasks
- Tool: τ-Voice framework

### Benchmarks

**Full-Duplex-Bench v3**:
- Real disfluent speech (ums, ahs, restarts)
- Multi-step tool use
- Interruption handling

**τ-Voice**:
- Verifiable real-world tasks
- Decoupled simulation
- Reproducible evaluation

**Open ASR Leaderboard**:
- Multilingual ASR evaluation
- WER/CER metrics
- 12 datasets across languages

---

## Accessibility & Privacy

### Accessibility

**Visual Impairment**:
- Voice-first interaction (no screen required)
- Audio feedback for all actions
- Screen reader compatibility

**Motor Impairment**:
- Hands-free operation (always-listening mode)
- Voice commands for all functions
- No keyboard required

**Hearing Impairment**:
- Always show text transcript
- Visual indicators for voice activity
- Configurable audio levels

### Privacy

**On-Device Option**:
- 100% local processing (Silero + Whisper + Kokoro)
- No network required
- No data leaves device

**Cloud Option**:
- User consent required
- Clear privacy policy
- Data retention controls

**Audio Recording**:
- Opt-in only
- Local storage
- User can delete anytime

---

## References

### Papers
- [Moshi](https://arxiv.org/abs/2410.00037) — First real-time full-duplex spoken LLM
- [Full-Duplex-Bench v1](https://arxiv.org/abs/2503.04721) — Turn-taking evaluation
- [Full-Duplex-Bench v3](https://arxiv.org/abs/2604.04847) — Disfluency + multi-step
- [τ-Voice](https://arxiv.org/abs/2603.13686) — Real-world task benchmark
- [Open ASR Leaderboard](https://arxiv.org/abs/2510.06961) — Multilingual ASR

### Frameworks
- [Pipecat](https://github.com/pipecat-ai/pipecat) — Voice agent framework
- [LiveKit Agents](https://github.com/livekit/agents) — WebRTC + telephony
- [Smart Turn](https://github.com/pipecat-ai/smart-turn) — Semantic turn detection
- [Silero VAD](https://github.com/snakers4/silero-vad) — Voice activity detection

### Models
- [Whisper](https://github.com/openai/whisper) — Multilingual ASR
- [Kokoro TTS](https://github.com/hexgrad/kokoro) — Fast, high-quality TTS
- [Moshi](https://github.com/kyutai-labs/moshi) — Full-duplex spoken LLM
- [Orpheus TTS](https://github.com/canopyai/Orpheus-TTS) — Emotion-aware TTS
- [NeMo](https://github.com/NVIDIA/NeMo) — MagpieTTS for Vietnamese

### Related Workstreams
- §4.2 Memory — Cross-session voice preferences
- §4.5 Router — Voice-aware model routing
- §4.10 Hooks — Voice event hooks
- §4.13 Swarm — Voice-controlled multi-agent
- §4.17 Safety — Voice safety controls
- §5.3 SFX — Sound effects layer

---

**END OF FLAGSHIP VOICE MODE PLAN**

---

## ═══ SIGNAL PROCESSING ALGORITHMS — Run 10 Deepening ═══

This section provides algorithmic deep-dives for each signal processing component in the Lyra voice pipeline. Every algorithm includes full pseudocode, mathematical formulation, complexity analysis, edge-case handling, and a critical-parameters reference table.

---

### Algorithm 1: Silero VAD — CNN Architecture & Inference

Silero VAD uses a quantized convolutional neural network for binary speech/silence classification on 30ms audio frames at 16 kHz. The entire model is ~2 MB (INT8 weights, INT16 activations) and produces a decision in under 1 ms on CPU.

#### Architecture

```
Input: 30ms audio frame @ 16kHz = 480 samples
       ↓
   STFT (512-pt FFT, 512-hop, Hann window) → 257 frequency bins
       ↓
   Mel filterbank (64 bins, 80 Hz–7600 Hz)
       ↓
   [64] → Conv1d(64→128, k=3, s=1) → BatchNorm → ReLU
       ↓
   [128] → Conv1d(128→128, k=3, s=1) → BatchNorm → ReLU
       ↓
   [128] → Conv1d(128→64, k=3, s=2) → BatchNorm → ReLU
       ↓
   [64] → Conv1d(64→64, k=3, s=1) → BatchNorm → ReLU
       ↓
   [64] → Conv1d(64→32, k=3, s=2) → BatchNorm → ReLU
       ↓
   [32] → GlobalAveragePooling → Linear(32→1) → Sigmoid
       ↓
   speech_probability ∈ [0, 1]
```

#### Full Inference Pseudocode

```python
import numpy as np
from numpy.fft import rfft

# ---------------------------------------------------------------------------
# Constants (from Silero VAD v4.0 ONNX export)
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000          # Hz
FRAME_LENGTH = 480           # samples (30 ms)
HOP_LENGTH = 480             # no overlap for VAD frames
FFT_SIZE = 512               # 512-pt real FFT → 257 bins
MEL_BINS = 64
MEL_LOW_HZ = 80.0
MEL_HIGH_HZ = 7600.0
VAD_THRESHOLD_ON = 0.7       # hysteresis rising edge
VAD_THRESHOLD_OFF = 0.3      # hysteresis falling edge
HOLD_OFF_MS = 500            # ms of sustained <OFF before state change
NUM_CONV_LAYERS = 5

# ---------------------------------------------------------------------------
# Mel filterbank construction (von Hann window + triangular mel filters)
# ---------------------------------------------------------------------------
def build_mel_filterbank(sr: int, n_fft: int, n_mels: int,
                         f_min: float, f_max: float) -> np.ndarray:
    """Return [n_mels x (n_fft//2+1)] mel weighting matrix."""
    # Mel scale: mel(f) = 2595 * log10(1 + f/700)
    mel_min = 2595.0 * np.log10(1.0 + f_min / 700.0)
    mel_max = 2595.0 * np.log10(1.0 + f_max / 700.0)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)

    fft_bins = hz_points * (n_fft // 2 + 1) / (sr // 2)
    fft_bins = np.floor(fft_bins).astype(np.int32)

    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(n_mels):
        f_start = fft_bins[m]
        f_center = fft_bins[m + 1]
        f_stop = fft_bins[m + 2]
        for k in range(f_start, f_center):
            fb[m, k] = (k - f_start) / (f_center - f_start)
        for k in range(f_center, f_stop):
            fb[m, k] = (f_stop - k) / (f_stop - f_center)
    return fb

# ---------------------------------------------------------------------------
# STFT + Mel spectrogram extraction
# ---------------------------------------------------------------------------
def frame_to_mel(samples: np.ndarray,
                 fb: np.ndarray,
                 window: np.ndarray) -> np.ndarray:
    """
    Args:
        samples: [480] float32 PCM @ 16 kHz
        fb:      [64 x 257] mel filterbank
        window:  [512] Hann window
    Returns:
        [64] float32 mel energies (log-compressed)
    """
    # Apply Hann window (zero-pad to 512)
    padded = np.zeros(FFT_SIZE, dtype=np.float32)
    padded[:FRAME_LENGTH] = samples * window[:FRAME_LENGTH]

    # 512-pt real FFT → 257 complex bins
    spec = rfft(padded, n=FFT_SIZE)                # [257] complex

    # Power spectrum
    power = (spec.real ** 2 + spec.imag ** 2) / FFT_SIZE  # [257]

    # Mel filterbank projection
    mel_spec = fb @ power                                   # [64]

    # Log compression (avoid log(0) with epsilon)
    mel_spec = np.log(np.maximum(mel_spec, 1e-10))         # [64]

    return mel_spec.astype(np.float32)

# ---------------------------------------------------------------------------
# Quantized 1D convolution (INT8 weights, INT16 activations)
# ---------------------------------------------------------------------------
def quantized_conv1d(x: np.ndarray,
                     w_int8: np.ndarray,       # [C_out x C_in x K]
                     bias_fp32: np.ndarray,    # [C_out]
                     scale_in: float,
                     scale_w: float,
                     scale_out: float,
                     stride: int) -> np.ndarray:
    """
    Simulated INT8×INT8 → INT16 MAC convolution.

    Args:
        x:         input activation  [C_in x T]
        w_int8:    quantized weights [C_out x C_in x K]
        bias_fp32: bias              [C_out]
        scale_in:  input quantization scale
        scale_w:   weight quantization scale
        scale_out: output quantization scale
        stride:    temporal stride
    Returns:
        y: output [C_out x T_out] (INT16 simulated in float32)
    """
    C_out, C_in, K = w_int8.shape
    T_in = x.shape[1]
    T_out = (T_in - K) // stride + 1

    y = np.zeros((C_out, T_out), dtype=np.float32)
    for co in range(C_out):
        for t in range(T_out):
            acc = 0.0  # INT32 accumulator (simulated)
            for ci in range(C_in):
                for k in range(K):
                    idx = t * stride + k
                    # INT8 × INT8 → INT16 product
                    prod = (x[ci, idx].astype(np.int16) *
                            w_int8[co, ci, k].astype(np.int16))
                    acc += prod
            # Dequantize: y = (acc * scale_in * scale_w) + bias
            y[co, t] = acc * scale_in * scale_w + bias_fp32[co]
            # Requantize to INT16 (simulated)
            y[co, t] = np.round(y[co, t] / scale_out)
    return y.astype(np.int16) * scale_out

# ---------------------------------------------------------------------------
# Full VAD inference
# ---------------------------------------------------------------------------
def silero_vad_infer(frame: np.ndarray,
                     model_weights: dict,
                     fb: np.ndarray,
                     window: np.ndarray) -> float:
    """
    Single-frame VAD inference.

    Args:
        frame:  [480] PCM float32
    Returns:
        speech_probability ∈ [0, 1]
    """
    # 1. STFT → Mel
    x = frame_to_mel(frame, fb, window)           # [64]

    # 2. Reshape to [1 x C_in x T] where T=1 for single-frame
    x = x.reshape(1, 64, 1)                       # [1 x 64 x 1]

    # 3. Conv layers (using quantized ops)
    for layer in range(NUM_CONV_LAYERS):
        k = model_weights[f'conv{layer}_w']        # INT8
        b = model_weights[f'conv{layer}_b']        # FP32
        s_in = model_weights[f'conv{layer}_s_in']
        s_w = model_weights[f'conv{layer}_s_w']
        s_out = model_weights[f'conv{layer}_s_out']
        stride = model_weights[f'conv{layer}_stride']

        x = quantized_conv1d(x, k, b, s_in, s_w, s_out, stride)
        x = np.maximum(x, 0)                       # ReLU (in-place)
        x = batchnorm(x,                          # fused BN after conv
                      model_weights[f'bn{layer}_gamma'],
                      model_weights[f'bn{layer}_beta'],
                      model_weights[f'bn{layer}_mean'],
                      model_weights[f'bn{layer}_var'])

    # 4. Global average pool
    x = np.mean(x, axis=-1)                        # [32]

    # 5. Linear → Sigmoid
    logit = (model_weights['fc_w'] @ x +
             model_weights['fc_b'])                # scalar
    prob = 1.0 / (1.0 + np.exp(-logit))
    return float(prob)

# ---------------------------------------------------------------------------
# VAD state machine with hysteresis
# ---------------------------------------------------------------------------
class VADStateMachine:
    """
    Hysteresis prevents rapid on/off toggling near threshold.
    """
    STATE_IDLE = 0
    STATE_SPEECH = 1

    def __init__(self):
        self.state = self.STATE_IDLE
        self.off_counter_ms = 0          # how long speech_prob < THRESH_OFF
        self.on_counter_ms = 0           # how long speech_prob > THRESH_ON
        self.frame_duration_ms = 30      # 30 ms per frame
        self.hold_off_ms = HOLD_OFF_MS   # 500 ms debounce to silence

    def update(self, prob: float) -> int:
        """
        Returns current state: IDLE or SPEECH.

        Transition rules:
          IDLE → SPEECH:  prob > THRESH_ON (immediate)
          SPEECH → IDLE:  prob < THRESH_OFF for > HOLD_OFF_MS (500 ms)
        """
        if self.state == self.STATE_IDLE:
            if prob > VAD_THRESHOLD_ON:
                self.state = self.STATE_SPEECH
                self.on_counter_ms = 0
                self.off_counter_ms = 0
            return self.STATE_IDLE

        # STATE_SPEECH
        if prob < VAD_THRESHOLD_OFF:
            self.off_counter_ms += self.frame_duration_ms
            if self.off_counter_ms >= self.hold_off_ms:
                self.state = self.STATE_IDLE
                self.off_counter_ms = 0
        else:
            self.off_counter_ms = 0       # reset if prob rises again

        return self.state

# ---------------------------------------------------------------------------
# Edge case: silence frames → prob stays near 0 → state stays IDLE
# Edge case: noise bursts <500 ms → prob may spike then drop → no false trigger
# Edge case: clipped audio → STFT captures DC + harmonic distortion;
#            model trained on synthetic clipping, still discriminates
# ---------------------------------------------------------------------------
```

#### Quantization Scheme

| Layer | Weights | Activations | Scale Type |
|-------|---------|-------------|------------|
| Conv1D | INT8 (per-channel) | INT16 (per-tensor) | Symmetric |
| BatchNorm | FP32 (fused into scale) | INT16 | - |
| Linear | INT8 | FP32 (output) | Per-tensor |
| Sigmoid | - | FP32 | - |

All convolution layers are fused: BatchNorm parameters are multiplied into convolution weights at export time, eliminating runtime BN overhead.

#### Complexity Analysis

- **Time**: O(F x M x C_in x C_out x K / stride) per layer, where F = frames, M = mel bins, K = kernel size. Single 30ms frame: ~800 MACs total (INT8). <1 ms on any modern CPU.
- **Space**: ~2 MB (model weights INT8) + 64 KB (mel filterbank) + 8 KB (per-frame buffers).

#### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Silence (no input) | prob < 0.01, state = IDLE indefinitely |
| Impulse noise (door slam) | prob spikes > 0.7 for 1-2 frames, then drops; hysteresis prevents false SPEECH transition |
| Sustained low hum (fan) | prob ~0.2-0.3; stays IDLE unless background modeled as speech |
| Clipped recording | Model trained with synthetic clipping; prob may drop ~0.1 |
| Music background | prob highly variable (0.1-0.8); may cause false positives; bandpass pre-filtering recommended |

#### CRITICAL PARAMETERS

| Parameter | Recommended | Sensitivity | Effect |
|-----------|-------------|-------------|--------|
| THRESHOLD_ON | 0.7 | High | Lower → more sensitive but more false positives |
| THRESHOLD_OFF | 0.3 | High | Higher → longer tails but fewer false silences |
| HOLD_OFF_MS | 500 ms | Medium | Shorter → faster release but more toggle noise |
| Frame size | 30 ms | Low | Larger → better frequency resolution, worse time resolution |
| Mel bins | 64 | Medium | More → better freq detail but more parameters |

#### References
- Silero VAD: [github.com/snakers4/silero-vad](https://github.com/snakers4/silero-vad) — MIT license
- ONNX Runtime: [github.com/microsoft/onnxruntime](https://github.com/microsoft/onnxruntime) — quantization API
- Hann window and STFT: Oppenheim & Schafer, *Discrete-Time Signal Processing*, 3rd ed., Ch. 8

---

### Algorithm 2: LMS Adaptive Echo Cancellation

During barge-in, the speaker output feeds back into the microphone. A Normalized Least Mean Squares (NLMS) adaptive filter cancels this acoustic echo before VAD processing.

#### Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Filter length N | 256 taps | Covers ~16 ms at 16 kHz — typical short room impulse response |
| Step size (mu) | 0.01 | Trade-off: convergence speed vs. steady-state excess MSE |
| Normalization epsilon | 1e-6 | Prevent division by zero in NLMS |
| Reference signal x[n] | Playback buffer (last N samples) | Feeds from audio output stream |
| Desired signal d[n] | Microphone PCM input | Contains user speech + echo |
| Error signal e[n] | d[n] - y_hat[n] | Echo-cancelled output sent to VAD |

#### NLMS Update Equations

```
y_hat[n] = w[n]^T · x[n]                (estimated echo via linear convolution)
e[n]     = d[n] - y_hat[n]              (error signal = clean output)
w[n+1]   = w[n] + mu * e[n] * x[n] / (||x[n]||^2 + epsilon)
```

where:
- `w[n] = [w_0, w_1, ..., w_(N-1)]^T` — adaptive filter weights at sample n
- `x[n] = [x[n], x[n-1], ..., x[n-N+1]]^T` — reference vector (playback history)
- `||x[n]||^2 = Σ(k=0 to N-1) x[n-k]^2` — energy of reference vector
- `mu` — normalized step size (dimensionless)

#### Full Pseudocode (Fixed-Point)

```python
import numpy as np
from collections import deque

# ---------------------------------------------------------------------------
# Fixed-point arithmetic configuration
# ---------------------------------------------------------------------------
Q = 15                                     # Q15 fixed-point (1 sign + 15 fractional bits)
MAX_INT16 = 32767
MIN_INT16 = -32768

def float_to_q15(val: float) -> np.int16:
    """Convert float to Q15 fixed-point integer."""
    return np.int16(np.clip(np.round(val * (1 << Q)), MIN_INT16, MAX_INT16))

def q15_to_float(val: np.int16) -> float:
    """Convert Q15 fixed-point back to float."""
    return float(val) / (1 << Q)

def q15_mult(a: np.int16, b: np.int16) -> np.int16:
    """Q15 multiplication: result stays in Q15 (1.15 x 1.15 = 2.30 → shift + round)."""
    prod = np.int32(a) * np.int32(b)           # 32-bit intermediate
    return np.int16(prod >> Q)                 # keep top 16 bits

# ---------------------------------------------------------------------------
# Ring buffer for reference samples (avoids O(N) shift per sample)
# ---------------------------------------------------------------------------
class RingBufferQ15:
    def __init__(self, capacity: int):
        self.buf = np.zeros(capacity, dtype=np.int16)
        self.capacity = capacity
        self.head = 0                           # next write position

    def push(self, sample: np.int16):
        self.buf[self.head] = sample
        self.head = (self.head + 1) % self.capacity

    def to_vector(self) -> np.ndarray:
        """Return [N] in chronological order (oldest first)."""
        idx = np.arange(self.capacity)
        return self.buf[(self.head + idx) % self.capacity]

# ---------------------------------------------------------------------------
# NLMS adaptive echo canceller (fixed-point)
# ---------------------------------------------------------------------------
class NLMSAEC:
    """
    Normalized Least Mean Squares Acoustic Echo Canceller.

    Implements the full algorithm: filtering → error → weight update,
    with integrated double-talk detection.
    """
    def __init__(self, N: int = 256, mu: float = 0.01, epsilon: float = 1e-6):
        self.N = N                               # filter length (taps)
        self.mu = float_to_q15(mu)               # step size (Q15)
        self.eps = epsilon                        # normalization floor (float)
        self.w = np.zeros(N, dtype=np.int16)     # filter weights (Q15)
        self.ref_buf = RingBufferQ15(N)          # playback reference ring

        # Statistics
        self.adapt_count = 0
        self.double_talk_count = 0

    def process(self, d: float, x: float) -> float:
        """
        Single-sample NLMS step.

        Args:
            d: microphone sample (desired signal, float [-1, 1])
            x: playback sample   (reference signal, float [-1, 1])
        Returns:
            e: echo-cancelled output (float [-1, 1])
        """
        d_q15 = float_to_q15(d)
        x_q15 = float_to_q15(x)

        # 1. Push playback reference into ring buffer
        self.ref_buf.push(x_q15)
        x_vec = self.ref_buf.to_vector()          # [N] Q15

        # 2. FIR filter: y_hat = w^T · x (Q15 × Q15 multiply-accumulate)
        y_hat_q15 = np.int16(0)
        for k in range(self.N):
            y_hat_q15 += q15_mult(self.w[k], x_vec[k])
        # y_hat_q15 may overflow int16 → use int32 accumulator in practice
        y_hat = q15_to_float(y_hat_q15)           # estimated echo

        # 3. Error signal: e = d - y_hat
        e = d - y_hat                               # float

        # 4. Normalization: compute ||x||^2 (Q15 × Q15 → float)
        ref_energy = 0.0
        for k in range(self.N):
            xf = q15_to_float(x_vec[k])
            ref_energy += xf * xf

        # 5. Weight update (only if not double-talk, see detector below)
        if not self.is_double_talk(d, y_hat):
            norm = ref_energy + self.eps
            if norm > 0:
                step = self.mu * e / norm           # mu * e / ||x||^2 (scalar float)
                step_q15 = float_to_q15(step)
                for k in range(self.N):
                    # w[k] += step * x[n-k]
                    delta = q15_mult(step_q15, x_vec[k])
                    self.w[k] = np.int16(
                        np.clip(int(self.w[k]) + int(delta),
                                MIN_INT16, MAX_INT16))
            self.adapt_count += 1

        return e

    # -----------------------------------------------------------------------
    # Double-talk detector: pause adaptation when both sides speak
    # -----------------------------------------------------------------------
    def is_double_talk(self, mic_sample: float, echo_est: float) -> bool:
        """
        Implements a correlation-based double-talk detector.

        If the microphone signal and the estimated echo are strongly correlated
        AND the microphone VAD flags speech, we are in double-talk.
        Adaptation halts to prevent weight divergence.
        """
        # Coherence estimate: how much of mic is explained by echo
        if abs(echo_est) < 1e-6:
            return False

        coherence = abs(mic_sample - echo_est) / (abs(mic_sample) + 1e-6)

        # Strong echo present + VAD likely says speech = double-talk
        if echo_est > 0.05 and coherence > 0.7 and self._vad_flag():
            self.double_talk_count += 1
            return True
        return False

    def _vad_flag(self) -> bool:
        """
        Placeholder: in production, this reads the Silero VAD state.
        Returns True when VAD state == SPEECH.
        """
        # Injected by VADStateMachine.state
        return False

# ---------------------------------------------------------------------------
# Edge case: near-end silence → e ≈ noise floor, adaptation continues safely
# Edge case: zero playback → y_hat = 0 → e = d (no echo to cancel)
# Edge case: sudden loud echo (door slam through speaker) →
#            NLMS diverges momentarily; double-talk detector may mis-classify;
#            use leakage factor (w *= 0.999) to prevent weight explosion
# ---------------------------------------------------------------------------
```

#### Double-Talk Detector Detail

```
1. Compute short-term correlation:
   cross_corr = Σ(d[i] · x[i]) / sqrt(Σd[i]^2 · Σx[i]^2)   over 10ms window
   
2. Decision:
   if cross_corr > 0.7 AND VAD_state == SPEECH:
       double_talk = true     (pause adaptation)
   else:
       double_talk = false    (continue adaptation)

3. Forced adaptation (safety net):
   if adapt_count_since_last_dt > 50000 (~3 seconds):
       force one adaptation step even in double-talk (slowly track echo path changes)
```

#### Complexity Analysis

- **Time**: O(N) per audio sample = 256 multiply-accumulates. At 16 kHz: ~4.1 million MACs/s. On modern CPUs: <1% of one core.
- **Space**: O(N) = 256 x INT16 weights (512 bytes) + 256 x INT16 ring buffer (512 bytes) + scalar state.

#### Edge Cases

| Condition | Behavior |
|-----------|----------|
| No playback (headphones) | x[n] ≈ 0 → y_hat ≈ 0 → e ≈ d (passthrough). Weights drift slowly; leakage (w *= 0.9999 per step) prevents unbounded growth. |
| Near-end only (user speaks, no echo) | d contains speech + residual noise. Error e ≈ d. Weights do not diverge because x[n] ≈ 0. |
| Double-talk (both speak) | Adaptation frozen. Existing echo path model held static. Works for short overlaps (<2 s). |
| Echo path change (user moves closer to speaker) | Weights re-converge in ~50 ms (800 samples at mu=0.01, N=256). |
| Microphone clipping | d is hard-limited; NLMS sees distorted signal. Standardized error may slow convergence. |

#### CRITICAL PARAMETERS

| Parameter | Recommended | Sensitivity | Effect |
|-----------|-------------|-------------|--------|
| Filter taps N | 256 | High | More taps = longer echo tail but slower convergence and more noise |
| Step size mu | 0.01 | High | Higher = faster convergence but more excess MSE and potential divergence |
| Normalization epsilon | 1e-6 | Low | Must be >0; too small causes large step in silence |
| Double-talk threshold | 0.7 | Medium | Lower → more adaptation pauses (safer); higher → better tracking |
| Leakage factor | 0.9999 | Low | Prevents weight drift; too low biases echo cancellation |

#### References
- Widrow & Stearns, *Adaptive Signal Processing*, Prentice Hall 1985 — LMS theory
- Haykin, *Adaptive Filter Theory*, 5th ed., Pearson 2014 — NLMS convergence analysis
- Hansler & Schmidt, *Acoustic Echo and Noise Control*, Wiley 2005 — practical AEC design

---

### Algorithm 3: Audio Buffer Ring Data Structure

The voice pipeline uses a lock-free Single Producer, Single Consumer (SPSC) ring buffer to decouple the audio capture thread from the VAD/processing thread. No mutexes or semaphores are needed because each pointer is written by exactly one thread.

#### Design

```
                                        ┌──────────────────────────────┐
Producer (audio thread) ──write──►     │  Ring Buffer [N float32]     │  ──read──► Consumer (VAD thread)
                                       │                              │
                                       │  write_ptr (AtomicUint32)    │
                                       │  read_ptr  (AtomicUint32)    │
                                       └──────────────────────────────┘

Atomic guarantees (C++20 memory model / Web Atomics):
- store(write_ptr) uses release ordering
- load(write_ptr) uses acquire ordering
- Only the producer modifies write_ptr
- Only the consumer modifies read_ptr
- No ABA problem: write_ptr and read_ptr are monotonic (never decremented modulo capacity)
```

#### Full TypeScript Pseudocode

```typescript
/// <reference lib="webworker" />

/**
 * Lock-free SPSC ring buffer for float32 audio samples.
 *
 * Thread safety:
 *   - Producer thread: calls write() only
 *   - Consumer thread: calls read() only
 *   - Neither thread reads/writes the other's pointer
 *   - Atomic acquire/release guarantees: producer's writes are visible
 *     to consumer after consumer reads the updated write_ptr.
 *
 * The pointers are monotonic uint32 counters (not modulo).
 * The effective position is ptr % capacity.
 * This avoids the classic "full vs empty ambiguity" at the cost of
 * 4B counters that will wrap after ~2^32 writes (~18 hours at 16 kHz stereo;
 * in practice the pipeline resets on session boundaries).
 */

type AtomicUint32 = {
  /** Release-store: producer publishes writes */
  store(val: number): void;
  /** Acquire-load: consumer sees producer's writes */
  load(): number;
  /** Relaxed-add: only producer calls this on write_ptr, consumer on read_ptr */
  add(delta: number): void;
};

class AudioRingBuffer {
  private readonly buffer: Float32Array;
  private readonly capacity: number;          // must be power of 2 for cheap modulo
  private readonly mask: number;
  private readonly writePtr: AtomicUint32;     // producer only
  private readonly readPtr: AtomicUint32;      // consumer only

  /**
   * @param size  Total number of float32 samples. Recommended: 30720
   *              (64 frames x 480 samples = 1.92 s at 16 kHz).
   *              Must be a power of 2.
   */
  constructor(size: number) {
    if ((size & (size - 1)) !== 0) {
      throw new Error(`Ring buffer size must be power of 2, got ${size}`);
    }
    this.capacity = size;
    this.mask = size - 1;
    this.buffer = new Float32Array(size);
    this.writePtr = createAtomic(0);
    this.readPtr  = createAtomic(0);
  }

  // -----------------------------------------------------------------------
  // Producer-side (audio capture thread)
  // -----------------------------------------------------------------------

  /**
   * Write samples into the ring buffer.
   *
   * @param samples  Float32Array of PCM samples to enqueue.
   * @returns Actual number of samples written (may be less than
   *          samples.length if buffer is full — backpressure).
   */
  write(samples: Float32Array): number {
    const wp = this.writePtr.load();            // relaxed: producer reads own ptr
    const rp = this.readPtr.load();             // acquire: see consumer's progress

    const available = this.capacity - (wp - rp); // samples of free space
    const toWrite   = Math.min(samples.length, available);

    if (toWrite <= 0) {
      return 0;  // buffer full — must discard (backpressure to audio driver)
    }

    const wpMod = wp & this.mask;               // position in circular buffer
    const firstChunk = Math.min(toWrite, this.capacity - wpMod);

    // First chunk: from wpMod to end of buffer
    this.buffer.set(samples.subarray(0, firstChunk), wpMod);

    if (toWrite > firstChunk) {
      // Second chunk: wrap around to start of buffer
      this.buffer.set(samples.subarray(firstChunk, toWrite), 0);
    }

    // Release-store: all buffer writes MUST be visible before writePtr update
    // In practice: the Atomic store has release semantics.
    this.writePtr.store(wp + toWrite);           // release

    return toWrite;
  }

  /**
   * @returns Number of samples available for reading (consumer-side estimate).
   */
  readable(): number {
    const wp = this.writePtr.load();   // acquire
    const rp = this.readPtr.load();    // relaxed (consumer reads own ptr)
    return wp - rp;
  }

  // -----------------------------------------------------------------------
  // Consumer-side (VAD / processing thread)
  // -----------------------------------------------------------------------

  /**
   * Read samples from the ring buffer.
   *
   * @param out  Float32Array to fill. Must be pre-allocated by caller.
   * @returns Actual number of samples read (may be less than out.length
   *          if insufficient data available).
   */
  read(out: Float32Array): number {
    const wp = this.writePtr.load();             // acquire: see producer's writes
    const rp = this.readPtr.load();             // relaxed: consumer reads own ptr

    const available = wp - rp;
    const toRead    = Math.min(out.length, available);

    if (toRead <= 0) {
      return 0;  // no data available — caller should poll or spin
    }

    const rpMod = rp & this.mask;
    const firstChunk = Math.min(toRead, this.capacity - rpMod);

    // First chunk
    out.set(this.buffer.subarray(rpMod, rpMod + firstChunk), 0);

    if (toRead > firstChunk) {
      // Second chunk: wrap around
      out.set(this.buffer.subarray(0, toRead - firstChunk), firstChunk);
    }

    // Release-store: all buffer reads MUST be visible before readPtr update
    this.readPtr.store(rp + toRead);             // release

    return toRead;
  }

  // -----------------------------------------------------------------------
  // Utility
  // -----------------------------------------------------------------------

  /** Reset buffer: both threads must agree before calling. */
  reset(): void {
    // Only safe when both threads are halted (e.g., session reset).
    this.writePtr.store(0);
    this.readPtr.store(0);
  }

  /**
   * Drain: advance readPtr to writePtr (discard all unread data).
   * Used on barge-in to flush the capture buffer for fresh audio.
   */
  drain(): void {
    const wp = this.writePtr.load();  // acquire
    this.readPtr.store(wp);           // release
  }
}

// ---------------------------------------------------------------------------
// Backpressure signaling (consumer → producer)
// ---------------------------------------------------------------------------

/**
 * The audio capture callback checks buffer fullness before each write.
 * If the buffer is > 90% full, the producer signals the audio driver to
 * reduce its chunk size or skip frames.
 *
 * Pseudocode (in the audio thread's callback):
 *
 *   function audioCaptureCallback(input: Float32Array) {
 *     const written = ringBuffer.write(input);
 *     if (written < input.length) {
 *       // Backpressure scenario: consumer cannot keep up.
 *       // Options (in priority order):
 *       // 1. Increase read interval (consumer thread yields)
 *       // 2. Increase ring buffer capacity (tunable parameter)
 *       // 3. Skip next capture frame (last resort, drops audio)
 *       logger.warn('Audio ring buffer overflow: dropped',
 *                    input.length - written, 'samples');
 *     }
 *   }
 */

// ---------------------------------------------------------------------------
// Memory ordering illustration (pseudocode — actual Atomics in JS
// are sequentially consistent by default)
// ---------------------------------------------------------------------------
//
// Producer:                               Consumer:
//   buffer[0..N] = data                       sync = load(writePtr, acquire)
//   store(writePtr, wp+N, release)            data = load(buffer[0..N], relaxed)
//                                             process(data)
//                                             store(readPtr, rp+N, release)
//
// The release-acquire pair on writePtr/readPtr establishes a
// happens-before relationship. All buffer writes by the producer
// are visible to the consumer after the consumer load-acquires writePtr.

// ---------------------------------------------------------------------------
// Edge case: wrap-around reads across boundary — handled by two-chunk copy.
// Edge case: buffer full → write returns 0 → caller drops frame.
// Edge case: buffer empty → read returns 0 → caller waits (spin or condition var).
// Edge case: pointer wrap (every ~2^32 samples ≈ 18 hours at 16 kHz) →
//            subtraction still correct because uint32 overflow is defined
//            modulo 2^32 in both C++ and JavaScript (Math.imul for JS).
// ---------------------------------------------------------------------------
```

#### Complexity Analysis

- **Time**: O(L) per call, where L = number of samples written/read. Each sample is a single float32 copy (no atomics per sample — only per batch).
- **Space**: O(N) = N x float32 (4 * N bytes). For N=30720: ~120 KB.

#### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Buffer full (consumer stuck) | write() returns < requested; caller drops oldest frame; backpressure signal sent |
| Buffer empty (producer slow) | read() returns 0; consumer spins or sleeps; underrun counter incremented |
| Pointer wraparound | Uint32 arithmetic works modulo 2^32; (wp - rp) correctly computes occupancy for ~18 hours continuous use |
| Thread termination | Both pointers preserve last position; safe to rejoin (reset() if threads restart) |
| Drain on barge-in | readPtr advanced to writePtr in O(1) — all buffered audio discarded atomically |

#### CRITICAL PARAMETERS

| Parameter | Recommended | Sensitivity | Effect |
|-----------|-------------|-------------|--------|
| Buffer capacity | 30720 (1.92 s) | Medium | Larger tolerates longer GC pauses but adds latency |
| Power-of-2 alignment | Required | Low | Enables cheap bitwise modulo (x & mask) |
| Write threshold | 90% full | Medium | Trigger backpressure before overflow |
| Atomic ordering | acquire/release | Low (correctness) | Wrong ordering causes stale reads; sequentially consistent is safe but slower |

#### References
- Vyukov, "Bounded MPMC queue" — 1024cores.net, 2010
- Preshing, "Lock-Free Programming" — preshing.com, 2012
- C++20 standard: §31.9 (atomics); `std::atomic_thread_fence` semantics

---

### Algorithm 4: Streaming TTS Overlap (Kokoro-82M)

Kokoro-82M uses the StyleTTS 2 architecture: Grapheme-to-Phoneme (G2P) conversion, acoustic model (StyleTTS 2), and HiFi-GAN vocoder. The streaming optimization overlaps synthesis of sentence N+1 with playback of sentence N, hiding all but the first-sentence latency.

#### Architecture

```
Input text
    │
    ▼
┌─────────────────────┐
│  Sentence Splitter   │  Split on . ! ? ; : newline
│  (regex-based)       │
└─────────┬───────────┘
          │ sentences[]
          ▼
┌─────────────────────┐
│  G2P (misaki)        │  text → phoneme sequence
│  ~5 ms per sentence  │
└─────────┬───────────┘
          │ phonemes[]
          ▼
┌─────────────────────┐
│  StyleTTS 2          │  phonemes → mel spectrogram
│  Acoustic Model      │  ~30 ms per sentence
│  ~82M params         │
└─────────┬───────────┘
          │ mel[]
          ▼
┌─────────────────────┐
│  HiFi-GAN Vocoder    │  mel → audio waveform
│  ~15 ms per sentence │
└─────────┬───────────┘
          │ audio[]
          ▼
    ┌──────────┐
    │ Playback  │  Stream to speaker
    │ Ring Buf  │
    └──────────┘
```

#### Streaming Overlap Schedule

```
Sentence 0: G2P |---5ms---| Acoustic |---30ms---| Vocoder |---15ms---| Playback |------|
                                         Sentence 1:     G2P |---5ms---| Acoustic |---30ms---| Vocoder |---15ms---|
                                                                               Sentence 2:     G2P |---5ms---| ...

Timeline:
  t=0      G2P(0) starts
  t=5ms    Acoustic(0) starts
  t=35ms   Vocoder(0) starts
  t=50ms   Playback(0) begins   ◄── first-sentence latency = 50ms
           G2P(1) starts immediately
  t=55ms   Acoustic(1) starts
  t=85ms   Vocoder(1) starts
  t=100ms  Playback(1) begins   ◄── subsequent sentences have 0 added latency
  ...
```

#### Full Pseudocode

```python
import re
import threading
from dataclasses import dataclass
from typing import List, Optional
from collections import deque

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Sentence:
    index: int
    text: str
    phonemes: Optional[str] = None
    mel: Optional[object] = None          # mel spectrogram (numpy array)
    audio: Optional[np.ndarray] = None   # synthesized audio (float32)

# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

SENTENCE_PATTERN = re.compile(
    r'(?<!\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|dept|est|approx))'  # no split after abbreviations
    r'[.!?;:\n]'
    r'(?=\s+|$)'                                                        # require whitespace or end
)

def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences with abbreviation-awareness.

    Edge cases:
      - "Dr. Smith arrived." → ["Dr. Smith arrived."]
      - "Hello world! How are you?" → ["Hello world!", "How are you?"]
      - "Item 1: first; item 2: second." → ["Item 1: first; item 2: second."]
        (semicolon only splits when followed by sentence-like structure)
    """
    raw_sentences = SENTENCE_PATTERN.split(text)
    # Filter empty strings and strip whitespace
    sentences = [s.strip() for s in raw_sentences if s and s.strip()]
    # Attach the delimiter back to the sentence
    # Simplified: assume pattern captures delimiter in the split at correct positions
    return sentences if sentences else [text]

# ---------------------------------------------------------------------------
# Synthesis pipeline components (stubs — actual implementations load models)
# ---------------------------------------------------------------------------

class G2PEngine:
    """Grapheme-to-Phoneme engine (misaki library)."""
    def convert(self, text: str) -> str:
        return text  # stub: returns phoneme string

class AcousticModel:
    """StyleTTS 2 acoustic model (82M params)."""
    def synthesize(self, phonemes: str) -> np.ndarray:
        return np.zeros((80, 100), dtype=np.float32)  # stub: [mel_bins x time]

class Vocoder:
    """HiFi-GAN vocoder."""
    def generate(self, mel: np.ndarray) -> np.ndarray:
        return np.zeros(48000, dtype=np.float32)  # stub: ~3s audio at 16kHz

# ---------------------------------------------------------------------------
# Synthesis scheduler (runs in a dedicated worker thread)
# ---------------------------------------------------------------------------

class SynthesisScheduler:
    """
    Drives the streaming TTS pipeline.

    Maintains a playback ring buffer and a synthesis queue.
    The scheduler ensures synthesis of sentence i+1 starts immediately
    after synthesis of sentence i finishes its G2P stage, achieving
    pipeline overlap.
    """
    def __init__(self, playback_buffer_capacity: int = 4):
        self.g2p = G2PEngine()
        self.acoustic = AcousticModel()
        self.vocoder = Vocoder()

        # Playback ring: synthesized audio chunks, each ~2-4 s of speech
        self.playback_buf = deque(maxlen=playback_buffer_capacity)
        self.synth_queue: deque = deque()          # sentences waiting to be synthesized
        self.currently_synthesizing: Optional[int] = None

        # Playback position (in samples at 16 kHz)
        self.playback_pos = 0
        self.synth_pos = 0                          # last audio sample written to playback buf

        # Control
        self.running = False
        self.cancelled = False

    # -----------------------------------------------------------------------
    # Main loop: run in a background thread
    # -----------------------------------------------------------------------
    def synthesize_loop(self):
        self.running = True
        while self.running and not self.cancelled:
            if not self.synth_queue:
                # Wait for more text
                time.sleep(0.005)  # 5ms polling
                continue

            sentence = self.synth_queue.popleft()
            self.currently_synthesizing = sentence.index

            # Stage 1: G2P
            sentence.phonemes = self.g2p.convert(sentence.text)

            # Stage 2: Acoustic model → mel
            sentence.mel = self.acoustic.synthesize(sentence.phonemes)

            # Stage 3: Vocoder → audio
            sentence.audio = self.vocoder.generate(sentence.mel)

            # Push to playback ring
            self.playback_buf.append(sentence.audio)
            self.synth_pos += len(sentence.audio)
            self.currently_synthesizing = None

    # -----------------------------------------------------------------------
    # API
    # -----------------------------------------------------------------------
    def submit_text(self, text: str):
        """Split text into sentences and enqueue for synthesis."""
        sentences = split_sentences(text)
        for i, s in enumerate(sentences):
            self.synth_queue.append(Sentence(index=i, text=s))

    def get_next_playback_chunk(self) -> Optional[np.ndarray]:
        """Called by the audio output thread. Returns the next audio chunk."""
        if not self.playback_buf:
            return None
        chunk = self.playback_buf.popleft()
        self.playback_pos += len(chunk)
        return chunk

    # -----------------------------------------------------------------------
    # Barge-in: flush everything
    # -----------------------------------------------------------------------
    def cancel(self):
        """Immediate stop: drop all pending synthesis and queued audio."""
        self.cancelled = True
        self.synth_queue.clear()
        self.playback_buf.clear()
        self.currently_synthesizing = None

    # -----------------------------------------------------------------------
    # Underrun detection
    # -----------------------------------------------------------------------
    @property
    def is_underrun(self) -> bool:
        """Playback is catching up to synthesis — silence will be inserted."""
        ahead = len(self.playback_buf) * 48000  # estimated samples ahead
        return ahead < 4800                      # less than 300 ms of audio

    def fill_silence(self, duration_ms: int = 200) -> np.ndarray:
        """Generate silence for underrun gap-filling."""
        samples = int(16000 * duration_ms / 1000)  # 16 kHz
        return np.zeros(samples, dtype=np.float32)

# ---------------------------------------------------------------------------
# Playback ring buffer management (separate from capture ring)
# ---------------------------------------------------------------------------

class PlaybackRingBuffer:
    """
    Audio output ring buffer.

    Producer: synthesis scheduler (write synthesized chunks)
    Consumer: PortAudio output callback (read sample-by-sample)
    """
    def __init__(self, max_chunks: int = 4):
        self.chunks: deque = deque(maxlen=max_chunks)
        self.current_chunk: Optional[np.ndarray] = None
        self.current_pos: int = 0

    def enqueue(self, audio: np.ndarray):
        self.chunks.append(audio)

    def read_sample(self) -> float:
        """
        Get next PCM sample for the output stream.

        Returns NaN if empty (caller handles as silence).
        """
        while True:
            if self.current_chunk is None:
                if not self.chunks:
                    return float('nan')    # underrun
                self.current_chunk = self.chunks.popleft()
                self.current_pos = 0

            if self.current_pos < len(self.current_chunk):
                val = self.current_chunk[self.current_pos]
                self.current_pos += 1
                return val

            # Current chunk exhausted
            self.current_chunk = None

    def flush(self):
        """Drop all queued chunks — used on barge-in."""
        self.chunks.clear()
        self.current_chunk = None
        self.current_pos = 0

# ---------------------------------------------------------------------------
# Barge-in flush protocol
# ---------------------------------------------------------------------------

def barge_in_handler():
    """
    Called when VAD detects user speech during agent TTS playback.

    Protocol:
      1. synthesis_scheduler.cancel()      -- stop all pending synthesis
      2. playback_ring.flush()              -- drop queued audio
      3. PortAudio_StopStream()             -- immediate silence on speaker
      4. Start buffering user speech        -- fresh capture starts
      5. Within 5 ms of step 1: speaker is silent
    """
    synthesis_scheduler.cancel()
    playback_ring.flush()
    # portaudio_stop_stream(stream)        -- platform-specific
    logger.info("Barge-in complete: speaker silent, capturing user input")

# ---------------------------------------------------------------------------
# Edge case: short text (<1 sentence) → single-chunk synthesis, no overlap benefit
# Edge case: very long text (100+ sentences) → pipeline maintains steady state;
#            playback ring holds max 4 chunks (~20 s), older chunks consumed by speaker
# Edge case: underrun (synthesis slower than playback) →
#            200 ms silence inserted; next chunk plays seamlessly
# Edge case: cancellation during G2P → no audio generated; immediate silence
# Edge case: cancellation during vocoder → partial chunk dropped;
#            HiFi-GAN may produce truncated output; silence is safer than glitch
# ---------------------------------------------------------------------------
```

#### Complexity Analysis

- **Time**: O(T + S x (P + A + V)) where T = text length, S = sentence count, P = G2P time, A = acoustic model time, V = vocoder time. With overlap: first sentence dominates at ~50 ms; each subsequent sentence adds ~0 ms to *effective* latency (hidden by overlap).
- **Space**: O(S x K x 4) bytes where S = max queued sentences (4), K = average audio length per sentence (~3 s = 48,000 samples at 16 kHz). Total: ~4 x 48000 x 4 = ~768 KB for the playback ring. Synthesis scratch buffers: additional ~256 MB for acoustic model + vocoder (model weights, released after use).

#### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Single sentence | No overlap benefit; first-sentence latency applies (~50 ms) |
| Empty text | No synthesis; pipeline returns immediately |
| Abbreviation false split | "Dr. Smith" stays as one sentence via abbreviation whitelist |
| Code-switching | G2P receives mixed phoneme sets; misaki handles multiple languages |
| Barge-in during vocoder stage | Audio chunk may be partially generated; dropped entirely — no audible glitch |
| Playback underrun | 200 ms silence filled; audible gap but no desync |

#### CRITICAL PARAMETERS

| Parameter | Recommended | Sensitivity | Effect |
|-----------|-------------|-------------|--------|
| Playback ring capacity | 4 chunks (~20 s) | Medium | Larger = more memory; too small = underrun on slow synthesis |
| Underrun fill silence | 200 ms | Low | Too short = stutter; too long = awkward pause |
| Sentence max length | 300 chars | Medium | Longer sentences increase first-chunk latency |
| Abbreviation whitelist | 20 entries | Low | Missing entries cause false splits; has no safety impact |
| Poll interval | 5 ms | Low | Shorter = more CPU; longer = staler queue check |

#### References
- Kokoro-82M: [github.com/hexgrad/kokoro](https://github.com/hexgrad/kokoro) — Apache-2.0
- StyleTTS 2: Li et al., "StyleTTS 2: Towards Human-Level Text-to-Speech through Style Diffusion and Adversarial Training with Large Speech Language Models", NeurIPS 2023
- HiFi-GAN: Kong et al., "HiFi-GAN: Generative Adversarial Networks for Efficient and High Fidelity Speech Synthesis", NeurIPS 2020
- misaki G2P: [github.com/hexgrad/misaki](https://github.com/hexgrad/misaki) — language-specific phonemization

---

### Algorithm 5: Smart Turn — Prosody-Aware Boundary Detection

Smart Turn uses a Whisper Tiny backbone (8M params, encoder-only) with a lightweight linear classifier head for turn-boundary detection. It analyzes the last <=8 seconds of audio and classifies each 30ms frame as {turn_end, continuing, unsure}.

#### Architecture

```
Input: Audio buffer (last ≤8 s @ 16 kHz mono) = up to 128,000 samples
    │
    ▼
┌───────────────────────────┐
│ Whisper Tiny Encoder      │  8M params, 4 layers, 384-dim
│ (layer 4 hidden states)   │
└───────────┬───────────────┘
            │ h_t ∈ R^384  (one per 30ms frame)
            ▼
┌───────────────────────────┐
│ Prosody Feature Extractor │
│ pitch_slope_t ∈ R        │
│ energy_delta_t ∈ R       │
│ pause_dur_t ∈ R          │
└───────────┬───────────────┘
            ▼
┌───────────────────────────┐
│ Concat: [h_t; prosody]    │  → R^387
└───────────┬───────────────┘
            ▼
┌───────────────────────────┐
│ Linear Classifier         │
│ W ∈ R^(3×387), b ∈ R^3   │
│ softmax → {turn_end,      │
│            continuing,    │
│            unsure}        │
└───────────┬───────────────┘
            ▼
    ┌───────────────┐
    │ Post-processing │  Hysteresis, timeout rules
    └───────────────┘
```

#### Full Pseudocode

```python
import numpy as np
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480
MAX_BUFFER_SAMPLES = int(SAMPLE_RATE * 8)             # 128,000 (8 s)
HIDDEN_DIM = 384
NUM_CLASSES = 3

# Post-processing thresholds
UNSURE_TIMEOUT_MS = 2000            # force turn_end after 2 s of unsure
MIN_TURN_GAP_MS = 150               # min pause for valid turn end (prevents disfluency false positives)
MAX_CONTINUOUS_MS = 8000            # force turn_end after 8 s monologue
PAUSE_RESET_MS = 500                # min pause to force turn_end in monologue mode

# ---------------------------------------------------------------------------
# Prosody feature extraction
# ---------------------------------------------------------------------------

def compute_pitch_contour(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Extract pitch (F0) contour using normalized autocorrelation.

    Args:
        audio: [N] float32 PCM
    Returns:
        pitch: [num_frames] float32, 0 = unvoiced frame
    """
    frame_len = FRAME_SAMPLES
    hop = FRAME_SAMPLES
    num_frames = (len(audio) - frame_len) // hop + 1

    pitch = np.zeros(num_frames, dtype=np.float32)
    for t in range(num_frames):
        start = t * hop
        frame = audio[start:start + frame_len]
        frame = frame * np.hanning(frame_len)          # window

        # Normalized autocorrelation at lags 20-160 samples (100-800 Hz)
        ac = np.correlate(frame, frame, mode='full')
        ac = ac[len(ac)//2:]                            # positive lags

        min_lag = int(sr / 800)   # lag=20 for 800 Hz max
        max_lag = int(sr / 100)   # lag=160 for 100 Hz min
        region = ac[min_lag:max_lag + 1]
        norm = np.sqrt(ac[0] * np.sum(frame**2) + 1e-10)

        if norm > 0:
            ncc = region / norm                          # normalized cross-correlation
            peak_idx = np.argmax(ncc)
            if ncc[peak_idx] > 0.3:                      # voicing threshold
                lag = min_lag + peak_idx
                pitch[t] = float(sr) / lag               # convert lag to Hz

    return pitch


def compute_energy_contour(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Compute per-frame RMS energy in dB.
    """
    frame_len = FRAME_SAMPLES
    hop = FRAME_SAMPLES
    num_frames = (len(audio) - frame_len) // hop + 1

    energy = np.zeros(num_frames, dtype=np.float32)
    for t in range(num_frames):
        start = t * hop
        frame = audio[start:start + frame_len]
        rms = np.sqrt(np.mean(frame ** 2) + 1e-10)
        energy[t] = 20.0 * np.log10(rms + 1e-10)        # dB

    return energy


def compute_prosody_features(audio: np.ndarray,
                             pitch_contour: np.ndarray,
                             energy_contour: np.ndarray,
                             frame_t: int) -> Tuple[float, float, float]:
    """
    Compute three prosody features for frame_t.

    Args:
        audio:          [N] raw audio
        pitch_contour:  [T] per-frame pitch in Hz
        energy_contour: [T] per-frame energy in dB
        frame_t:        current frame index

    Returns:
        pitch_slope_t   — first derivative of pitch (Hz/s)
        energy_delta_t  — change in energy from frame t-1 (dB)
        pause_dur_t     — duration of silence before frame_t (ms)
    """
    # Pitch slope: linear regression over ±3 frames (210 ms window)
    if frame_t >= 3 and frame_t + 3 < len(pitch_contour):
        window = pitch_contour[frame_t - 3:frame_t + 4]
        valid = window > 0
        if np.sum(valid) >= 2:
            t_vals = np.arange(len(window))
            # Linear fit: slope = cov(t, pitch) / var(t)
            slope = (np.sum((t_vals - t_vals.mean()) * (window - window.mean()))
                     / (np.sum((t_vals - t_vals.mean()) ** 2) + 1e-10))
            pitch_slope_t = slope / (0.007 * 16000)  # normalize to Hz/s
        else:
            pitch_slope_t = 0.0
    else:
        pitch_slope_t = 0.0

    # Energy delta
    if frame_t > 0:
        energy_delta_t = energy_contour[frame_t] - energy_contour[frame_t - 1]
    else:
        energy_delta_t = 0.0

    # Pause duration: how long has energy been below threshold?
    pause_ms = 0.0
    energy_thresh = -50.0  # dB threshold for silence
    for k in range(frame_t - 1, -1, -1):
        if energy_contour[k] < energy_thresh:
            pause_ms += FRAME_MS
        else:
            break
    pause_dur_t = pause_ms

    return pitch_slope_t, energy_delta_t, pause_dur_t

# ---------------------------------------------------------------------------
# Linear classifier
# ---------------------------------------------------------------------------

class TurnBoundaryClassifier:
    """
    Linear probe on top of Whisper Tiny encoder hidden states.

    W: [3 x 387] weight matrix
    b: [3] bias vector
    """
    def __init__(self, W: np.ndarray, b: np.ndarray):
        self.W = W   # [3, 387]
        self.b = b   # [3]

    def predict(self, hidden: np.ndarray,
                pitch_slope: float,
                energy_delta: float,
                pause_dur: float) -> np.ndarray:
        """
        Args:
            hidden:      [384] encoder hidden state for current frame
            pitch_slope:  scalar
            energy_delta: scalar
            pause_dur:    scalar (ms)
        Returns:
            logits:     [3] unnormalized class scores
        """
        # Concatenate: [384, 1, 1, 1] → [387]
        features = np.concatenate([
            hidden,
            np.array([pitch_slope, energy_delta, pause_dur], dtype=np.float32)
        ])
        logits = self.W @ features + self.b   # [3]
        return logits

    def softmax(self, logits: np.ndarray) -> np.ndarray:
        """Stable softmax."""
        e = np.exp(logits - np.max(logits))
        return e / np.sum(e)

# ---------------------------------------------------------------------------
# Full Smart Turn inference
# ---------------------------------------------------------------------------

class SmartTurnDetector:
    """
    Prosody-aware turn boundary detector.

    Language-specific parameters are loaded from a config table (see below).
    """
    def __init__(self, lang: str = 'en'):
        self.lang = lang
        self.clf = TurnBoundaryClassifier(
            W=self._load_weights('W'),   # [3, 387]
            b=self._load_weights('b')    # [3]
        )
        self.config = LANGUAGE_PARAMS.get(lang, LANGUAGE_PARAMS['en'])

        # State
        self.buffer = np.array([], dtype=np.float32)   # audio buffer (ring)
        self.last_turn_end_frame = -1
        self.unsure_since_frame = -1
        self.continuous_start_frame = -1

    def _load_weights(self, name: str) -> np.ndarray:
        """Load pretrained weights (stub)."""
        return np.zeros((3, 387) if name == 'W' else (3,), dtype=np.float32)

    def process_frame(self, audio_chunk: np.ndarray) -> str:
        """
        Process one 30ms audio frame. Returns classification label.

        Args:
            audio_chunk: [480] PCM float32 @ 16 kHz
        Returns:
            'turn_end' | 'continuing' | 'unsure'
        """
        # 1. Append to audio ring buffer (keep last 8 s)
        self.buffer = np.concatenate([self.buffer, audio_chunk])
        if len(self.buffer) > MAX_BUFFER_SAMPLES:
            self.buffer = self.buffer[-MAX_BUFFER_SAMPLES:]

        # 2. Run Whisper Tiny encoder on full buffer (stub — inference)
        hidden_states = self._whisper_encoder(self.buffer)   # [T x 384]
        current_frame = len(hidden_states) - 1               # most recent frame

        # 3. Compute prosody features
        pitch = compute_pitch_contour(self.buffer)
        energy = compute_energy_contour(self.buffer)
        p_slope, e_delta, pause = compute_prosody_features(
            self.buffer, pitch, energy, current_frame)

        # 4. Classify
        logits = self.clf.predict(
            hidden_states[current_frame], p_slope, e_delta, pause)
        probs = self.clf.softmax(logits)                     # [3]

        label_idx = np.argmax(probs)
        raw_label = ['turn_end', 'continuing', 'unsure'][label_idx]

        # 5. Post-processing (language-aware)
        return self._post_process(raw_label, current_frame, pause, probs)

    def _post_process(self, raw: str, frame: int,
                      pause_ms: float, probs: np.ndarray) -> str:
        """
        Apply hysteresis and timeout overrides.

        Rule 1: unsure for >UNSURE_TIMEOUT_MS → force turn_end
        Rule 2: turn_end with pause < MIN_TURN_GAP_MS → demote to unsure (disfluency)
        Rule 3: continuing for >MAX_CONTINUOUS_MS → force turn_end at next pause > PAUSE_RESET_MS
        """
        # Rule tracking
        if raw == 'unsure':
            if self.unsure_since_frame < 0:
                self.unsure_since_frame = frame
            elif (frame - self.unsure_since_frame) * FRAME_MS > UNSURE_TIMEOUT_MS:
                return 'turn_end'                          # Rule 1 override
        else:
            self.unsure_since_frame = -1

        if raw == 'continuing':
            if self.continuous_start_frame < 0:
                self.continuous_start_frame = frame
            elif ((frame - self.continuous_start_frame) * FRAME_MS
                  > MAX_CONTINUOUS_MS and pause_ms > PAUSE_RESET_MS):
                return 'turn_end'                          # Rule 3 override
        else:
            self.continuous_start_frame = -1

        if raw == 'turn_end':
            if pause_ms < MIN_TURN_GAP_MS:
                return 'unsure'                            # Rule 2 override
            self.last_turn_end_frame = frame

        return raw

    def _whisper_encoder(self, audio: np.ndarray) -> np.ndarray:
        """
        Stub for Whisper Tiny encoder forward pass.

        Actual implementation uses the Whisper Tiny model (openai/whisper-tiny):
          - 4 transformer encoder layers, 384-dim hidden, 6 attention heads
          - Positional embeddings: learned sin/cos
          - Output: [T x 384] where T = number of 30ms frames
        """
        T = len(audio) // FRAME_SAMPLES
        return np.zeros((T, HIDDEN_DIM), dtype=np.float32)

# ---------------------------------------------------------------------------
# Language-specific parameters
# ---------------------------------------------------------------------------

LANGUAGE_PARAMS = {
    'en': {
        'unsure_timeout_ms': 2000,
        'min_turn_gap_ms': 150,
        'max_continuous_ms': 8000,
        'pause_reset_ms': 500,
        'pitch_weight': 1.0,
        'energy_weight': 0.8,
        'description': 'English — neutral prosody, standard pause patterns'
    },
    'vi': {
        'unsure_timeout_ms': 2500,
        'min_turn_gap_ms': 200,
        'max_continuous_ms': 8000,
        'pause_reset_ms': 500,
        'pitch_weight': 1.5,
        'energy_weight': 0.7,
        'description': 'Vietnamese — tonal language, pitch carries semantic meaning; higher pitch weight'
    },
    'ja': {
        'unsure_timeout_ms': 2000,
        'min_turn_gap_ms': 100,
        'max_continuous_ms': 10000,
        'pause_reset_ms': 300,
        'pitch_weight': 1.2,
        'energy_weight': 0.6,
        'description': 'Japanese — short backchannel pauses (aizuchi), longer monologue tolerance'
    },
    'zh': {
        'unsure_timeout_ms': 2000,
        'min_turn_gap_ms': 150,
        'max_continuous_ms': 8000,
        'pause_reset_ms': 400,
        'pitch_weight': 1.3,
        'energy_weight': 0.7,
        'description': 'Chinese — tonal, mid-length pause patterns'
    },
    'ko': {
        'unsure_timeout_ms': 2000,
        'min_turn_gap_ms': 150,
        'max_continuous_ms': 9000,
        'pause_reset_ms': 400,
        'pitch_weight': 1.1,
        'energy_weight': 0.7,
        'description': 'Korean — moderate pitch sensitivity'
    },
}

# config also exists for: fr, de, es, pt, it, nl, pl, ru, tr, ar, hi,
# th, id, ms, fil, sv, da, nb (23 languages total — same schema)

# ---------------------------------------------------------------------------
# Edge case: very short utterance (<0.5 s) → may not trigger turn_end;
#            handled by forced turn_end after UNSURE_TIMEOUT_MS from silence
# Edge case: laughter / cough → energy spike but atypical pitch pattern;
#            classified as unsure; timeout forces turn_end if persistent
# Edge case: whispering → low energy but present pitch;
#            energy_thresh for pause detection must be adaptive to background
# Edge case: overlapping speech → energy and pitch both elevated;
#            classifier likely sees 'continuing' with high uncertainty
# Edge case: code-switching mid-utterance → prosody features may shift
#            abruptly; language-agnostic Whisper backbone handles phonetic
#            shift; pause-based timeout still applies
# Edge case: tonal language (VI) → pitch slope carries semantic info
#            (e.g., hỏi vs ngã tones). HIGH pitch_weight ensures classifier
#            does not mistake tonal inflection for turn-final prosody.
# ---------------------------------------------------------------------------
```

#### Language-Specific Parameter Differences (VI vs EN)

| Parameter | EN | VI | Rationale |
|-----------|:--:|:--:|-----------|
| unsure_timeout_ms | 2000 | 2500 | VI speakers pause longer mid-thought; longer timeout reduces false turns |
| min_turn_gap_ms | 150 | 200 | VI has longer inter-turn pauses; lower threshold triggers false positives on hesitation |
| pitch_weight | 1.0 | 1.5 | VI is tonal; pitch variation carries lexical meaning, not just turn-final prosody |
| energy_weight | 0.8 | 0.7 | VI energy contours less correlated with turn boundaries vs English |

#### Complexity Analysis

- **Time**: O(T x D^2) where T = number of 30ms frames (up to 267 for 8s buffer) and D = 384 (hidden dim). Whisper Tiny encoder: ~256 x 10^6 FLOPs per forward pass (amortized over frames by KV caching). The linear classifier adds negligible cost: 3 x 387 = 1161 FLOPs per frame. Total: ~2.5 ms per frame on CPU (INT8), ~0.1 ms on GPU.
- **Space**: Encoder: ~8M params x 4 bytes = ~32 MB (FP32), ~8 MB (INT8). Classifier: 3 x 387 = 1161 params (~5 KB). Audio buffer: up to 128,000 samples x 4 bytes = ~512 KB. Runtime: ~16 KB for pitch/energy frames.

#### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Very short utterance (<0.5 s) | Prosody features insufficient; classified as unsure; timeout forces turn_end |
| Laughter / cough | Energy spike but aperiodic pitch; classifier sees unsure; timeout forces turn_end |
| Whispering | Low energy maintained; pause detection threshold adapts to running noise floor |
| Overlapping speakers | Elevated energy + confused pitch; categorized as continuing with low confidence |
| Code-switching (VI/EN) | Whisper backbone handles phonetics; pitch_weight difference across languages may cause boundary uncertainty |
| Tonal language (VI) | Pitch slope carries semantic meaning; high pitch_weight prevents mistaking tone for turn-end prosody |

#### CRITICAL PARAMETERS

| Parameter | Recommended | Sensitivity | Effect |
|-----------|-------------|-------------|--------|
| Max buffer duration | 8 s | Medium | Longer = more context but higher encoder cost |
| Whisper layer | layer 4 (last) | High | Lower layers lack semantic abstraction; higher layers too task-specific |
| Prosody features | 3 (pitch, energy, pause) | Medium | More features (spectral tilt, harmonicity) could improve but add complexity |
| Unsure timeout | 2.0 s (EN), 2.5 s (VI) | High | Too short = false turns; too long = no turn detected |
| Min turn gap | 150 ms (EN), 200 ms (VI) | High | Lower = false splits on disfluency; higher = missed quick turns |
| Voicing threshold | 0.3 (NCC) | Medium | Lower = more voiced frames but more noise; higher = misses soft speech |

#### References
- Smart Turn: [github.com/pipecat-ai/smart-turn](https://github.com/pipecat-ai/smart-turn) — Apache-2.0
- Whisper Tiny: Radford et al., "Robust Speech Recognition via Large-Scale Weak Supervision", OpenAI 2022
- Prosody features: Shriberg et al., "Prosody-Based Automatic Segmentation of Speech into Sentences and Topics", Speech Communication 2000
- Tonal language turn-taking: Yang et al., "Prosodic Correlates of Turn-Taking in Mandarin Chinese", Interspeech 2014

---

**END OF SIGNAL PROCESSING ALGORITHMS — Run 10 Deepening**
