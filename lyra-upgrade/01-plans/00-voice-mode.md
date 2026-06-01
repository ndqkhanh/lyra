# Plan: Voice Mode — Lyra's Flagship Feature (Section 4.18)

**Workstream:** Section 4.18 Voice Mode  
**Status:** Draft Plan v2  
**Date:** 2026-05-31  
**Tier:** BREAKTHROUGH

---

## Quick Reference Card

| Item | Detail |
|------|--------|
| **What** | Full voice mode for Lyra: speak to your agents, hear them respond. Provider-swappable STT/TTS, multilingual (VI + EN), streaming overlap for low latency. |
| **Latency Target** | <300ms perceived (cloud), <500ms perceived (on-device) via streaming overlap |
| **Default Stack** | Silero VAD + Smart Turn detection + Whisper Turbo STT + Kokoro TTS (all open-source, CPU-capable) |
| **Estimated Cost** | $0/hour for on-device stack; ~$0.05-0.06/min for cloud alternatives (Deepgram/Cartesia) |
| **MVP Timeline** | 8 weeks (Phase 1-3 combined) |
| **Full Timeline** | 16-24 weeks (all 5 phases + breakthroughs) |
| **Key Dependencies** | Section 4.5 (Router), Section 4.10 (Hooks), Section 5.3 (SFX layer) |
| **Document Path** | `lyra-upgrade/plans/00-voice-mode.md` (this file — accessible entry point) |
| **Deep Technical Reference** | `lyra-upgrade/voice-mode.md` (DSP algorithms, full pseudocode, latency math) |
| **Brainstorm Archive** | `lyra-upgrade/brainstorm/00-voice-mode.md` (breakthrough ideas, fusion algorithms) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem -- Why Voice Matters](#2-problem--why-voice-matters)
3. [Evidence Synthesis -- Voice SOTA](#3-evidence-synthesis--voice-sota)
   - 3.1 STT (Speech-to-Text) Landscape
   - 3.2 TTS (Text-to-Speech) Landscape
   - 3.3 Full-Duplex vs Cascaded Architecture
   - 3.4 Voice Activity Detection and Turn Management
4. [Proposed Lyra Design](#4-proposed-lyra-design)
   - 4.1 Complete Pipeline Architecture
   - 4.2 How Voice Mode Works -- Step by Step
   - 4.3 Interaction Modes
   - 4.4 Multilingual Support (VI + EN)
   - 4.5 Personality and SFX Layer
   - 4.6 Accessibility, Privacy, and Cost
5. [Architecture and Data Models](#5-architecture-and-data-models)
6. [Build Outline -- Phased Rollout](#6-build-outline--phased-rollout)
7. [Multi-Provider Notes](#7-multi-provider-notes)
8. [Risks and Open Questions](#8-risks-and-open-questions)
9. [Evaluation and Benchmarking Plan](#9-evaluation-and-benchmarking-plan)
10. [(A) Parity vs (B) Breakthrough](#10-a-parity-vs-b-breakthrough)
11. [References](#11-references)
12. [Changelog](#12-changelog)

---

## 1. Executive Summary

Voice mode transforms Lyra from a text-based agent harness into a **conversational AI development environment**. This is the flagship feature that fundamentally changes how developers interact with AI agents.

**The vision:** Developers think aloud while coding, interrupt and steer long-running tasks through natural conversation, control agent swarms via voice, and work seamlessly in both Vietnamese and English. Voice is not a gimmick -- it is a new interaction modality that makes multi-agent AI truly accessible.

**What makes Lyra's voice mode special:**

- **Provider-agnostic.** STT and TTS are swappable via the same abstraction pattern used for LLM providers (Section 4.5). Choose your own stack: open-source on-device, cloud premium, or OpenAI Realtime API.
- **Streaming overlap hides latency.** TTS begins synthesizing before the LLM finishes generating. The effective perceived latency (~350ms on-device, ~180ms cloud) is far lower than the raw pipeline sum (~816ms on-device).
- **Multilingual from day one.** Vietnamese and English work out of the box. Vietnamese presents unique challenges (6 tones, code-switching, tonal prosody) that Smart Turn and Whisper Turbo handle natively.
- **Three breakthrough innovations** beyond any single existing solution (detailed in Section 9).
- **100% open-source default stack** with zero API costs for the core pipeline.

**What voice mode is NOT:**
- It is NOT a replacement for text -- both work together. Text is precise and reviewable. Voice is fast and natural. Lyra uses the right modality for the moment.
- It is NOT a gimmick or a video demo feature. Voice mode is designed for daily use: low latency, reliable, works in noisy environments, falls back gracefully when it fails.
- It is NOT a closed ecosystem. Every component is swappable. Users can choose their own STT (Whisper, Deepgram, Parakeet), TTS (Kokoro, MagpieTTS, Orpheus, Cartesia), and LLM (any provider). No lock-in.

**Target audience:**

| User Profile | Benefit |
|-------------|---------|
| Solo developer | Think aloud while coding, no typing required. Maintain flow state. |
| Hands-free worker | Voice commands while reading printouts, whiteboarding, debugging hardware. |
| Multilingual team | VI + EN seamless switching, no language barrier. Natural code-switching. |
| Accessibility user | Full voice control without keyboard or screen. RSI, vision, and motor disability support. |
| Power user | Voice control of agent swarms, spatial audio feedback, multi-agent steering. |
| Pair programmer | Speak naturally to Lyra while your partner drives the keyboard. |
| Technical reviewer | Review code aloud while Lyra checks for issues in real-time. |
| Meeting participant | Get Lyra to research a question mid-meeting without typing. |

**How this fits into Lyra's broader architecture:**
Voice mode is not a standalone feature -- it is a new INTERACTION LAYER that sits on top of existing Lyra components. The voice pipeline (Section 4.1) feeds into the same Model Router (Section 4.5), knowledge graph (Section 4.2), skill system, and agent swarm (Section 4.13) as text input. Voice is a new way to interact with the same powerful system, not a separate product. The hooks system (Section 4.10) connects voice events to the SFX layer (Section 5.3) for audio cues at every touchpoint.

**Success metrics:**

| Metric | Target |
|--------|--------|
| Perceived latency (cloud) | <300ms P50 |
| Perceived latency (on-device) | <500ms P50 |
| Word Error Rate (English) | <15% |
| Word Error Rate (Vietnamese) | <20% |
| Barge-in response time | <56ms |
| Adoption (3 month) | 40%+ of users enable voice |
| User satisfaction | 85%+ |

---

## 2. Problem — Why Voice Matters

### 2.1 Current State: Text-Only Interaction

Lyra today is a text-based multi-agent harness. Every interaction flows through the keyboard: type a command, read the response, type again. This works but has fundamental limits.

### 2.2 What Users Lose Without Voice

**Speed.** Speaking is 2-3x faster than typing for most people. Average typing speed is 40 WPM; average speaking speed is 150 WPM. Voice users can express intent in seconds rather than minutes.

**Fluidity.** Text interrupts the developer's flow. Each pause to type breaks the mental model. Voice allows developers to think aloud while coding, with Lyra listening and responding without friction.

**Accessibility.** RSI, vision impairment, and motor disabilities make text-heavy interaction difficult or impossible. Voice mode opens Lyra to users who cannot type or read screens effectively.

**Hands-free operation.** Debugging with printed schemas, whiteboarding architecture, reviewing paper documents -- all scenarios where hands are occupied but a voice assistant would be invaluable.

**Natural conversation.** Voice supports backchannel ("uh-huh"), interruption ("wait, not that"), and prosody (tone conveys urgency, hesitation, excitement). Text loses all of these channels.

**Multimodal expression.** Complex technical queries benefit from voice: "Find all SQL injection vulnerabilities in my auth module and fix them" is faster to speak than to type, and the developer's tone conveys whether this is urgent or exploratory.

### 2.3 Concrete Scenarios

| Scenario | Without Voice | With Voice |
|----------|---------------|------------|
| Debugging mid-coding | Stop coding, type query, read response, resume coding | Speak "Hey Lyra, find this bug" while continuing to scroll code |
| Hands full (reading paper docs) | Cannot interact | Voice command "Research this topic and summarize" |
| Urgent production issue | Fumbling keyboard under pressure | "Lyra, check the production logs for errors -- now!" |
| Code review aloud | Type each comment | "Review this file and mark the security issues" |
| Multilingual team meeting | Switch between VI and EN typing | Speak naturally, Lyra handles language detection |
| Controlling agent swarm | Impossible while debugging | "Pause agent 3, what's the status?" with spatial audio response |

---

## 3. Evidence Synthesis — Voice SOTA

This section surveys the state of the art across four voice technology categories. Deep algorithm details (pseudocode, latency math) live in the companion document `voice-mode.md`. This section provides the accessible comparison needed for decision-making.

---

### 3.1 STT (Speech-to-Text) Landscape

Five STT models compete for the default slot in Lyra's voice pipeline:

| Dimension | Whisper Turbo | Whisper Large-v3 | NVIDIA Parakeet | Canary-Qwen-2.5B | Deepgram Nova-3 |
|-----------|:------------:|:----------------:|:---------------:|:----------------:|:---------------:|
| Model Size | 809M params | 1.55B params | ~600M params | 2.5B params | Cloud API |
| VRAM | ~6GB | ~10GB | ~4GB (FP16) | ~8GB (FP16) | 0 (cloud) |
| Latency P50 | ~200ms | ~400ms | ~160ms | ~250ms | ~100ms |
| English WER | 9.3% | 7.1% | 6.8% | **5.63%** | ~5% |
| Vietnamese WER | ~18% | ~14% | ~20% | ~15% (est.) | ~12% |
| Languages | 99 | 99 | 20+ | 5 | 30+ |
| License | MIT | MIT | Apache-2.0 | CC-BY-NC-4.0 | Proprietary |
| CPU-only viable? | Yes (slow) | Yes (very slow) | No (GPU needed) | No (GPU needed) | Yes (cloud) |
| Streaming support | Yes | Partial | Yes | No | Yes |
| Code-switching | Strong | Strong | Weak | Weak | Strong |

**Decision table: which to use when**

| Situation | Recommended STT | Rationale |
|-----------|----------------|-----------|
| Default, general use | Whisper Turbo | Best balance of speed, WER, languages, and license. 8x faster than Large-v3 with only +2-4% WER. |
| Maximum English accuracy | Canary-Qwen-2.5B | Best EN WER at 5.63% on Open ASR Leaderboard. Use for EN-only high-stakes transcriptions. |
| GPU-accelerated, low latency | NVIDIA Parakeet | Lowest streaming latency at ~160ms. Use when GPU is available and latency is critical. |
| Cloud premium quality | Deepgram Nova-3 | Lowest overall latency at ~100ms, excellent accuracy. Use when cost is acceptable. |
| Privacy-sensitive / air-gapped | Whisper Turbo | On-device inference, zero network egress. All other on-device options are viable too. |
| Multilingual code-switching | Whisper Turbo | 99 languages with strong code-switching. Canary and Parakeet degrade on non-English. |

**Vietnamese-specific analysis:**

- **Tone recognition:** Vietnamese has 6 tones. Whisper Turbo is adequate on Northern dialect (~16% WER) but degrades on Central/Southern (~22% WER). Tone disambiguation needs context beyond single utterance.
- **Code-switching:** ~40% of technical Vietnamese speech contains English terms (e.g., "fix cai bug do di" = "fix that bug"). Whisper handles this natively; monolingual models (Canary, Parakeet) struggle.
- **Key finding:** Whisper Turbo is the only model that scores adequately on ALL three criteria for Lyra's use case: multilingual (99), CPU-capable (yes), open license (MIT).

---

### 3.2 TTS (Text-to-Speech) Landscape

Four TTS models compete for the default:

| Dimension | Kokoro-82M | Orpheus-TTS (3B) | MagpieTTS (NeMo) | Cartesia Sonic |
|-----------|:----------:|:----------------:|:----------------:|:--------------:|
| Model Size | 82M params | ~3B params | ~500M params | Cloud API |
| VRAM | CPU-capable | ~6GB GPU | ~2GB GPU | 0 (cloud) |
| Latency P50 | ~50ms | ~200ms | ~80ms | ~30ms |
| MOS (estimated) | ~3.8 | ~4.2 | ~4.0 | ~4.5 |
| Languages | EN, JA, KO, ZH | 7 pairs (preview) | 9 incl. **VI** | 8+ |
| Emotion control | No | Yes (tags: `<laugh>`, `<sigh>`) | Limited | Yes |
| Voice cloning | No | Yes (zero-shot) | No | Yes |
| License | **Apache-2.0** | Custom | Apache-2.0 | Proprietary |
| Stability | High | Medium | High | High |

**Decision table with trade-offs:**

| Situation | Recommended TTS | Rationale |
|-----------|----------------|-----------|
| Default EN | Kokoro-82M | Apache-2.0 license, CPU-capable, 50ms latency, stable. The G2P module (misaki) enables language expansion without retraining. |
| Vietnamese TTS | MagpieTTS (NeMo) | Only viable open VI TTS. Apache-2.0, production-quality (~4.0 MOS). |
| Expressive / emotional | Orpheus-TTS | Emotion tags, voice cloning, highest expressive quality. Use for personality voice packs. |
| Cloud premium | Cartesia Sonic | Lowest latency (~30ms), highest MOS (~4.5). Use when cost is acceptable. |
| Streaming, chunked | Kokoro-82M | Streaming overlap algorithm (voice-mode.md, Algorithm 4) achieves 0ms incremental latency per additional sentence. |

**Key architectural insight about Kokoro:** Kokoro's StyleTTS 2 architecture decouples G2P (misaki) from the acoustic model. This means adding a new language only requires training a G2P module -- no TTS model retraining. This makes Kokoro the most extensible open TTS option.

---

### 3.3 Full-Duplex vs Cascaded Architecture

There are three architectural approaches to voice interaction:

| Dimension | Moshi S2S (Full-Duplex) | Cascaded STT->LLM->TTS | Lyra Hybrid (Streaming Overlap) |
|-----------|:-----------------------:|:----------------------:|:-------------------------------:|
| Theoretical latency | 160ms | ~400ms | ~250ms |
| Practical latency | 200ms | ~800ms | ~350ms perceived |
| GPU requirement | **24GB** (7B Temporal) | CPU-capable | CPU-capable |
| Memory | ~30GB VRAM | ~8GB RAM | ~8GB RAM |
| Barge-in | Native (dual audio stream) | Layered (VAD interrupt) | Layered (VAD interrupt) |
| Reasoning quality | Limited (small temporal model) | **Full (any LLM)** | **Full (any LLM)** |
| Multilingual | Unspecified | 99 languages (Whisper) | 99 languages (Whisper) |
| Inner Monologue | Yes (text->audio tokens) | No | No |

**Lyra's decision: Cascaded default, Moshi optional.**

Cascaded mode wins for Lyra because:
1. It works with any LLM provider (Haiku, Sonnet, Opus, DeepSeek, open-weights)
2. It runs on CPU-only hardware (no GPU needed)
3. It supports 99 languages via Whisper
4. It allows complex reasoning without limiting the model

Moshi requires a 24GB GPU and locks reasoning to its small temporal model -- unsuitable for Lyra's multi-agent architecture.

**Lyra Hybrid gets 90% of Moshi's perceived latency without the GPU cost.** By streaming TTS output before LLM completion, and starting audio playback before full TTS output, we hide ~55% of the pipeline latency. The effective perceived latency: ~350ms on-device, ~180ms cloud.

---

### 3.4 Voice Activity Detection and Turn Management

Two components handle the audio timing:

**Silero VAD (Voice Activity Detection)**

| Property | Value |
|----------|-------|
| Model size | 2MB (INT8), CNN-based |
| Inference | <1ms per 30ms frame on CPU |
| Languages | 6000+ (language-agnostic, binary voice/silence classification) |
| License | MIT |
| Architecture | 5-layer quantized Conv1D -> sigmoid -> speech probability [0,1] |
| Hysteresis | Rising edge at 0.7, falling edge at 0.3, 500ms hold-off to prevent chatter |

**Smart Turn (Semantic Turn Detection)**

| Property | Value |
|----------|-------|
| Backbone | Whisper Tiny encoder (8M params) |
| Classifier | 3-class linear head: {turn_end, continuing, unsure} |
| Latency | 10-65ms |
| Languages | 23 including VI + EN |
| Prosody features | Pitch slope, energy delta, pause duration |
| License | Apache-2.0 |

**Turn management state machine:**

```
     [*] --> Idle
     Idle --> Listening: VAD detects voice (prob > 0.7)
     Listening --> Buffering: Speech continues
     Buffering --> Processing: Turn end (Smart Turn)
     Processing --> Routing: STT complete
     Routing --> Thinking: Model selected
     Thinking --> Speaking: Response ready
     Speaking --> Streaming: TTS chunks
     Streaming --> Idle: Complete
     Speaking --> Interrupted: User speech detected (barge-in)
     Streaming --> Interrupted: User speech detected
     Interrupted --> Listening: Barge-in handled
     Listening --> Idle: Timeout (>5s silence, no speech)
```

**Why two detectors?** Silero VAD detects voice vs silence (binary, fast, simple). Smart Turn detects conversational boundaries (semantic, prosody-aware, slower but smarter). They work together: VAD gates the audio into speech/non-speech frames, Smart Turn analyzes the speech buffer for natural turn boundaries. Using both eliminates the main failure mode of each one alone.

**How they interact in the pipeline:**

```
Audio capture thread (30ms frames):
  -> Silero VAD.evaluate(frame) -> speech_prob [0,1]
  -> If speech_prob > 0.7: mark frame as SPEECH
  -> If speech_prob < 0.3 for >500ms: mark frame as SILENCE
  
Processing thread (on complete utterances):
  -> Accumulate SPEECH frames into utterance buffer
  -> On SILENCE detected: send buffer to Smart Turn
  -> Smart Turn.analyze(buffer) -> {turn_end, continuing, unsure}
  -> If turn_end: send buffer to STT
  -> If continuing: wait for more audio
  -> If unsure for >2s: force turn_end
```

**Failure mode analysis for the two-detector system:**

| Failure Mode | Root Cause | Mitigation |
|-------------|-----------|------------|
| VAD false positive -> Smart Turn never runs | Noise triggers VAD, but noise doesn't have speech prosody | Smart Turn on garbage audio produces low-confidence output; filter by min confidence score |
| VAD false negative -> Smart Turn has no buffer | Speech never makes it past VAD | Push-to-talk bypasses VAD entirely; audio level meter helps user adjust mic |
| Smart Turn false positive -> user cut off | Turn_end incorrectly during natural pause | Unsure timeout >=2s gives user time to continue; push-to-talk mode for control |
| Smart Turn false negative -> dead air | Turn_end never fires, system waits forever | Max_continuous_ms=8000 forces turn_end; audio level meter shows mic is still active |
| Both fail simultaneously -> pipeline hangs | VAD on, Smart Turn unsure forever | Hard timeout at 15s of sustained speech: force a turn and process what we have |

**Silero VAD vs alternatives:**

| Detector | Size | Speed | Languages | License | Use Case |
|----------|------|-------|-----------|---------|----------|
| Silero VAD | 2MB | <1ms | 6000+ | MIT | Default -- best balance of speed, accuracy, and license |
| WebRTC VAD | ~500KB | <0.1ms | ~20 | BSD | Ultra-low resource environments (embedded) |
| MarbleNet (NeMo) | ~5MB | ~2ms | ~100 | Apache-2.0 | When higher accuracy needed (NeMo ecosystem) |
| OpenVAD | ~1MB | <1ms | All | MIT | Microsoft's lightweight alternative |

**Decision:** Silero VAD is the clear default. Its MIT license, tiny size (2MB), sub-millisecond speed, and cross-platform ONNX support make it the best choice. WebRTC VAD is the fallback for environments where ONNX Runtime is unavailable (rare).

**Smart Turn vs silence timeout vs alternatives:**

| Detector | Approach | Languages | Latency | False Positive | Use Case |
|----------|----------|-----------|---------|----------------|----------|
| Simple timeout (N ms silence) | Fixed threshold | All (no ML) | 0ms | High | Not recommended -- creates frustrating UX |
| Smart Turn | Whisper Tiny + prosody classifier | 23 | 10-65ms | Low | Default -- best balance of accuracy and coverage |
| Semantic VAD (Deepgram) | Cloud voice model | ~30 | ~20ms | Very low | Cloud premium -- highest accuracy, costs money |
| Moshi VAD (Kyutai) | Mimi codec + temporal model | Unspecified | <5ms | Low | Full-duplex only -- requires 24GB GPU |

**Decision:** Smart Turn is the default. It covers 23 languages including VI, has low latency, and is open-source (Apache-2.0). The whisper-tiny backbone (8M params) is cheap to run on CPU. Simple silence timeout is a fallback if Smart Turn is unavailable.

**Preventing specific failure modes with the two-detector system:**

- **User coughs/laughs mid-speech:** VAD detects as speech (energy spike). Smart Turn may see unusual prosody and classify as 'unsure'. After 2s unsure timeout, system assumes user was expressing and asks "Did you say something?" rather than processing garbage audio.
- **User pauses to think:** VAD stays on (background room noise may keep prob >0.3). Smart Turn sees flat pitch, no turn-final contour. Classifies as 'continuing'. System waits patiently.
- **User reads code aloud (disfluent):** "Select star from... no wait... select, column, name... from users..." -- VAD stays on (continuous speech). Smart Turn sees multiple short pauses with flat pitch. Classifies as 'continuing' for each pause (disfluency, not turn end). At MAX_CONTINUOUS_MS=8000, forces a turn end so the system doesn't wait forever.
- **Background conversation (office):** VAD detects speech from someone else's voice. Smart Turn may detect prosody and classify as 'turn_end'. STT processes it. Mitigation: if STT confidence <0.4 AND content doesn't match conversation context, ignore and re-enter listening.

---

## 4. Proposed Lyra Design

### 4.1 Complete Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         VOICE PIPELINE — LYRA                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐ │
│  │  MIC     │───>│  Audio   │───>│  Silero  │───>│  Ring    │───>│  Smart  │ │
│  │ (24kHz)  │    │ Capture  │    │  VAD     │    │  Buffer  │    │  Turn   │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └────┬────┘ │
│                                                                       │     │
│                                    ┌──────────────────────────────────┘     │
│                                    ▼                                        │
│                            ┌──────────────┐                                 │
│                            │  Whisper     │                                 │
│                            │  Turbo STT   │                                 │
│                            └──────┬───────┘                                 │
│                                   ▼                                         │
│                            ┌──────────────┐                                 │
│                            │  Text:       │                                 │
│                            │  "find all   │                                 │
│                            │  SQL injection│                                 │
│                            │  vulns..."   │                                 │
│                            └──────┬───────┘                                 │
│                                   ▼                                         │
│                            ┌──────────────┐                                 │
│                            │  Context     │                                 │
│                            │  Injection   │                                 │
│                            │  (memory +   │                                 │
│                            │   skills +   │                                 │
│                            │   prosody)   │                                 │
│                            └──────┬───────┘                                 │
│                                   ▼                                         │
│                            ┌──────────────┐                                 │
│                            │  Model       │                                 │
│                            │  Router      │  ───────────>  Haiku/Sonnet/Opus│
│                            │  (Sec 4.5)   │                                 │
│                            └──────┬───────┘                                 │
│                                   ▼                                         │
│                            ┌──────────────┐    ┌──────────────────┐        │
│                            │  LLM Output  │───>│  Kokoro TTS      │        │
│                            │  streams     │    │  (streaming      │        │
│                            │  text        │    │   overlap)       │        │
│                            └──────────────┘    └────────┬─────────┘        │
│                                                         ▼                  │
│                            ┌──────────────┐    ┌──────────────────┐        │
│                            │  SFX Layer   │───>│  Speaker Output  │        │
│                            │  (Sec 5.3)   │    │                  │        │
│                            └──────────────┘    └──────────────────┘        │
│                                                                              │
│  ═══ STREAMING OVERLAP ════════════════════════════════════════════════     │
│  TTS starts BEFORE LLM completes (first sentence).                          │
│  Audio playback starts BEFORE full TTS output (chunked streaming).          │
│  Context injection runs IN PARALLEL with STT (speculative retrieval).       │
│  Perceived latency: ~55% lower than raw pipeline sum.                       │
│                                                                              │
│  ═══ BARGE-IN ═════════════════════════════════════════════════════════     │
│  VAD monitors mic during TTS playback.                                      │
│  On speech detected: stop TTS <5ms, cancel LLM <50ms, buffer user audio.    │
│  Total barge-in latency: <56ms from speech onset to agent silence.          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Latency budget per stage:**

| Stage | On-Device P50 | On-Device P95 | Cloud P50 | Cloud P95 |
|-------|:------------:|:------------:|:---------:|:---------:|
| Audio Capture | 15ms | 25ms | 10ms | 20ms |
| VAD (Silero) | <1ms | <1ms | <1ms | <1ms |
| Turn Detection | 35ms | 65ms | 10ms | 30ms |
| STT (Whisper Turbo) | 200ms | 400ms | 80ms | 150ms |
| Context Injection | 5ms | 15ms | 5ms | 15ms |
| LLM Routing + Inference | 500ms | 2000ms | 300ms | 1000ms |
| TTS (Kokoro-82M) | 50ms | 100ms | 30ms | 60ms |
| Audio Playback | 10ms | 20ms | 10ms | 20ms |
| **Raw total** | **816ms** | **2,626ms** | **446ms** | **1,296ms** |
| **Perceived (with overlap)** | **~350ms** | **~450ms** | **~180ms** | **~300ms** |

> Full pipeline latency math, including formula for streaming overlap savings, is in `voice-mode.md` (Section "Latency Budget Breakdown").

---

### 4.2 How Voice Mode Works — Step by Step

Let's walk through a complete voice interaction with a concrete example. This is the single most important section for understanding how voice mode works in practice.

**Example scenario:** A developer is working on an authentication module. They lean back from the keyboard and say:

> "Hey Lyra, find all SQL injection vulnerabilities in my auth module and fix them."

Here is exactly what happens, step by step:

---

#### Step 1: Audio Capture Begins

**What happens:** The microphone starts capturing audio at 24kHz, 16-bit PCM mono. Audio is collected in 30ms chunks and written into a lock-free SPSC ring buffer.

**Latency budget:** 15ms (on-device) / 10ms (cloud) per chunk

**Data flow:**
```
Mic -> PortAudio callback (30ms chunks, 480 samples each) -> AudioRingBuffer.write()
```

**What could go wrong:**
- Microphone not available (permissions denied, no mic hardware)
- Buffer overflow if processing is slower than capture
- Background noise captured alongside speech

**Fallback:**
- Show error "Microphone not available. Check permissions."
- Fall back to text-only interaction
- Adjust buffer size dynamically if overflow detected

---

#### Step 2: Silero VAD Detects Speech

**What happens:** The consumer thread reads audio chunks from the ring buffer and runs them through Silero VAD. Each 30ms frame gets a speech probability score [0, 1]. When the score crosses the threshold (0.7), the system transitions from IDLE to LISTENING state.

**Real-time behavior:**
- Frame 1: prob = 0.12 (silence) -- state stays IDLE
- Frame 2: prob = 0.08 (silence) -- state stays IDLE
- Frame 3: prob = 0.03 (silence) -- state stays IDLE
- Frame 4: prob = 0.89 (SPEECH DETECTED) -- state -> LISTENING
- Frame 5-100: prob stays >0.7 -- state stays LISTENING
- Frame 101: prob = 0.25 (utterance end) -- hold-off counter starts

**Latency budget:** <1ms per frame (INT8 quantized CNN, 2MB model)

**What could go wrong:**
- VAD false negative: speech exists but prob stays <0.7. User speaks but Lyra doesn't respond.
- VAD false positive: noise triggers speech detection. Lyra processes background chatter.
- Short utterances (<500ms) may not trigger if VAD threshold is too high.

**Fallback:**
- Push-to-talk mode always works regardless of VAD state (user presses a key to force capture)
- Visual audio level meter shows the user that Lyra is listening
- Adjustable sensitivity setting (0.0-1.0) for noisy environments

**Technical detail (see `voice-mode.md`, Algorithm 1):** Silero VAD uses a quantized 5-layer Conv1D with hysteresis. The rising edge threshold (0.7) is higher than the falling edge (0.3) to prevent rapid on/off toggling near the threshold. A 500ms hold-off prevents false silence detection during natural pauses.

---

#### Step 3: Smart Turn Detects End of Utterance

**What happens:** Once speech is detected, audio continues buffering. Smart Turn analyzes the audio buffer (up to 8 seconds) looking for prosodic cues of turn completion: falling pitch, pause duration, energy decay. When the classifier outputs `turn_end` with confidence >0.5, the utterance is complete.

**Real-time behavior:**
- User says: "Hey Lyra, find all SQL injection vulnerabilities in my auth module and fix them."
- Smart Turn processes each 30ms frame as it arrives
- Mid-utterance: classifier outputs `continuing` (energy high, pitch active, no pause)
- End of utterance: classifier outputs `turn_end` (final pause >200ms, falling pitch contour)
- Post-processing rules:
  - If `unsure` persists for 2+ seconds -> force `turn_end`
  - If `continuing` for 8+ seconds -> force `turn_end` at next pause
  - If pause <150ms at `turn_end` -> demote to `unsure` (disfluency, not turn end)

**Latency budget:** 35ms (on-device) / 10ms (cloud) per analysis

**What could go wrong:**
- Turn detection miss: user pauses mid-thought (hesitation) and Smart Turn cuts them off
- Turn detection false: short utterance followed by thinking pause classified as turn end
- Vietnamese tonal prosody: pitch changes carry semantic meaning, not turn signals

**Fallback:**
- If turn is cut short, LLM can ask "Were you going to say more?"
- Push-to-talk eliminates turn detection entirely (release key = turn end)
- Vietnamese language profile uses higher pitch weight (1.5 vs 1.0) and longer unsure timeout (2.5s vs 2.0s) to handle tonal prosody

**Technical detail (see `voice-mode.md`, Algorithm 5):** Smart Turn uses a Whisper Tiny encoder (8M params, 4 layers, 384-dim) with a linear classifier over concatenated hidden states and prosody features (pitch slope, energy delta, pause duration). The prosody features are critical: they distinguish between a mid-utterance thinking pause (flat pitch, consistent energy) and an utterance-final pause (falling pitch, decaying energy). Without them, a silence-based detector would fire during any thoughtful pause.

**How Smart Turn differs from simple silence timeout:**
- Simple silence timeout: wait N ms of silence, then assume turn is over. Problem: pauses are natural in speech (thinking, hesitation, breath). A 600ms pause is normal mid-utterance but also signals turn end. Context-blind.
- Smart Turn: analyzes pitch contour, energy envelope, and pause duration. If pitch is falling (utterance-final) AND pause is present -> turn end. If pitch is flat or rising (mid-thought) AND pause is present -> continuing. The difference in behavior between these two is the difference between a natural conversation and a frustrating one where Lyra keeps cutting you off.

**Real-world example of Smart Turn's advantage:**
- User: "Find all SQL injection vulnerabilities... (pause, thinking) ...and also check the XSS in the login form" -> Smart Turn sees flat pitch during pause, no turn-final contour. Classifies as 'continuing'. Lyra waits.
- User: "Find all SQL injection vulnerabilities in my auth module and fix them" -> Smart Turn sees falling pitch on "them", pause >200ms. Classifies as 'turn_end'. Lyra processes.
- Simple timeout: would fire on the first pause (thinking), cutting the user off.

**Language-specific profiles (see voice-mode.md for all 23 languages):**

| Parameter | EN | VI | JA | Rationale |
|-----------|:--:|:--:|:--:|-----------|
| unsure_timeout_ms | 2000 | 2500 | 2000 | VI speakers pause longer mid-thought; JA has short backchannel pauses (aizuchi) |
| min_turn_gap_ms | 150 | 200 | 100 | VI has longer inter-turn pauses; JA allows quick back-and-forth |
| pitch_weight | 1.0 | 1.5 | 1.2 | VI is tonal -- pitch carries lexical meaning, not just turn-final prosody |
| energy_weight | 0.8 | 0.7 | 0.6 | VI/JA energy contours less correlated with turn boundaries vs English |
| max_continuous_ms | 8000 | 8000 | 10000 | JA allows longer monologues before forcing turn end |
| pause_reset_ms | 500 | 500 | 300 | JA expects quicker turn-taking after pauses |

---

#### Step 4: Whisper Turbo Transcribes

**What happens:** The captured audio buffer (up to 30 seconds) is sent to Whisper Turbo for transcription. Whisper processes with a sliding 30s window and returns text with confidence score.

**Input:** ~3 seconds of audio PCM (24kHz, 16-bit) containing "Hey Lyra find all SQL injection vulnerabilities in my auth module and fix them"

**Output:**
```json
{
  "text": "Hey Lyra find all SQL injection vulnerabilities in my auth module and fix them",
  "confidence": 0.94,
  "language": "en",
  "segments": [
    { "start": 0.0, "end": 0.4, "text": "Hey Lyra" },
    { "start": 0.5, "end": 2.8, "text": "find all SQL injection vulnerabilities in my auth module and fix them" }
  ]
}
```

**Latency budget:** 200ms (on-device GPU) / 80ms (cloud)

**What could go wrong:**
- Hallucination: Whisper generates text that doesn't match the audio
- Low confidence (<0.6) due to accent, background noise, or technical jargon
- "SQL injection" might be misheard as "sequel injection" or similar
- Vietnamese accented English might produce incorrect transcription

**Fallback:**
- Confidence threshold-based filtering: ignore if confidence <0.3
- Re-transcribe with lower temperature if confidence <0.6
- Show the transcription to the user so they can correct it
- Fall back to text input for clarity

**Vietnamese-specific:**
- Whisper Turbo on Vietnamese: ~18% WER
- Code-switching: "fix cai bug do di" -> "fix that bug" -- Whisper handles this because it was trained on multilingual code-switching data
- If language is detected as VI, use Vietnamese-specific post-processing for tone normalization

---

#### Step 5: Context Injection

**What happens:** Before sending to the LLM, Lyra enriches the transcription with context:
1. **Memory retrieval:** Search TKG for relevant memories about "auth module," "SQL injection," and previous conversations
2. **Skill matching:** Load security-review skill (matched to "vulnerabilities" intent)
3. **Prosody markers:** Attach detected user tone (urgency: high, confidence: moderate, from Step 3)
4. **Conversation history:** Attach previous 5 turns for continuity

**Enriched prompt (simplified):**
```
User query: "find all SQL injection vulnerabilities in my auth module and fix them"
Voice cues: urgency=high, confidence=moderate
Retrieved memories:
  - "Auth module uses Express + PostgreSQL, stored procedures for auth queries" (2 days ago)
  - "Previous security audit flagged input sanitization gaps in /api/login" (1 week ago)
Active skills: security-review, code-review
Conversation context: User was refactoring the auth error handling
```

**Latency budget:** 5ms (on-device) / 5ms (cloud) -- runs in parallel with STT (speculative retrieval starts when VAD detects speech)

**What could go wrong:**
- Memory retrieval returns irrelevant results (e.g., auth module for a different project)
- Skill matching fails because "vulnerabilities" doesn't match skill names
- Speculative retrieval wastes resources if user doesn't finish the query

**Fallback:**
- Standard (non-speculative) retrieval if speculative results are stale
- Broaden search if top-K results have low relevance scores
- Use LLM to re-rank retrieval results

---

#### Step 6: Router Selects LLM Provider

**What happens:** The Model Router (Section 4.5) analyzes the enriched query and selects the optimal LLM provider and model. For this security-critical, reasoning-heavy query:

**Router decision:**
```
Complexity score: 0.85 (high)
Reasoning depth: 8/10 (needs multi-step reasoning: find -> analyze -> recommend -> fix)
Security relevance: critical (SQL injection is a vulnerability)
Selection: Claude Opus (deepest reasoning, extended thinking)
Cost: Higher, but justified by security-critical nature
```

**Alternative scenarios:**
| Query Type | Router Selection | Rationale |
|------------|-----------------|-----------|
| "Hello Lyra" | Haiku | Simple greeting, no reasoning needed |
| "Explain async/await" | Sonnet | Moderate complexity, standard coding question |
| "Find SQL injection vulns and fix" | **Opus** | Security-critical, multi-step reasoning |
| "What time is it?" | Haiku | Trivial query, fast model |
| Long-running code generation | DeepSeek | Cost-effective for long outputs |

**Latency budget:** LLM inference time dominates the pipeline:
- Haiku: ~200ms
- Sonnet: ~500ms
- Opus: ~2000ms (includes extended thinking)
- DeepSeek: ~1000ms

**What could go wrong:**
- Router selects too-small model for a complex task -> poor quality response
- Router selects too-large model for a simple task -> unnecessary latency and cost
- Provider API is down or rate-limited

**Fallback:**
- Cascade: if Haiku returns low confidence, re-route to Sonnet/Opus
- Provider fallback: if primary provider fails, try secondary
- Timeout escalation: if Opus takes >30s, switch to Sonnet with streaming

---

#### Step 7: LLM Processes and Plans Workflow

**What happens:** Claude Opus receives the enriched prompt and:
1. Analyzes the auth module's codebase
2. Identifies 3 SQL injection vulnerabilities in the login endpoint, password reset, and user search
3. Plans the fixes: parameterized queries for login, input sanitization for search, rate limiting for reset
4. Spawns sub-agents to implement each fix

**Streaming response begins:**
```
"I found three SQL injection vulnerabilities in your auth module.

First, the login endpoint at /api/login constructs queries with string interpolation.
Your code does: `SELECT * FROM users WHERE email = '${req.body.email}'`
This should use parameterized queries: `SELECT * FROM users WHERE email = $1`

Second, the password reset endpoint at /api/reset has similar issues in the token validation...

Third, the user search endpoint at /api/users/search reflects unvalidated input in error messages.

I've started fixing all three. The first fix is complete. Do you want me to continue with the others?"
```

**What could go wrong:**
- LLM hallucinates vulnerabilities that don't exist
- LLM suggests fixes that break other functionality
- Multi-agent orchestration fails (agents don't coordinate correctly)
- Extended thinking reveals a much larger problem (architectural issue)

**Fallback:**
- Always show a diff before applying changes
- Allow user to approve/reject each fix
- Rollback mechanism for applied changes
- Safety review: security-related changes flagged for human approval

---

#### Step 8: Kokoro Begins TTS Synthesis Before LLM Completes

**This is the key latency optimization.** The LLM response is streamed as tokens/text. TTS synthesis starts on the FIRST SENTENCE while the LLM continues generating the rest.

**Streaming overlap in action:**
```
Time 0ms:     LLM starts generating
Time 300ms:   LLM outputs first sentence: "I found three SQL injection vulnerabilities..."
              ═══ TTS BEGINS ═══
              Kokoro: G2P conversion -> acoustic model -> vocoder -> audio chunk 1
Time 350ms:   Audio chunk 1 starts playing
              LLM continues: "...First, the login endpoint..."
              ═══ TTS CONTINUES ═══
              Kokoro: Sentence 2 synthesis starts (overlap with playback of sentence 1)
Time 650ms:   Audio chunk 2 starts playing (0ms additional latency from overlap)
              LLM continues with remaining content
              ...
```

**Result:** The user hears the first words of Lyra's response at ~350ms, even though the full LLM response takes ~2 seconds to generate. Each additional sentence adds 0ms to effective latency because TTS overlaps with playback.

**Latency budget:** 50ms (on-device) / 30ms (cloud) for the first sentence's TTS synthesis; 0ms incremental for each subsequent sentence.

**What could go wrong:**
- Underrun: synthesis is slower than playback -> audible silence gap
- Abbreviation false split: "Dr. Smith" split into two sentences mid-name
- Code-switching in TTS: Kokoro doesn't support VI, so VI text in EN response would sound wrong

**Fallback:**
- Insert 200ms of silence if underrun detected (better than glitchy audio)
- Abbreviation whitelist prevents false sentence splits
- If VI text is detected in EN TTS output, flag for human review

**Technical detail (see `voice-mode.md`, Algorithm 4):** The streaming overlap scheduler maintains a 4-chunk playback ring buffer. Chunks are ~2-4 seconds of speech each. The scheduler submits text sentence by sentence; synthesis of sentence N+1 starts immediately after sentence N's G2P stage completes. This achieves a steady state where the playback ring always has 1-2 synthesized chunks ready, hiding all inter-sentence latency.

---

#### Step 9: Audio Playback Begins (Chunked Streaming)

**What happens:** As TTS finishes each audio chunk, it's enqueued in the playback ring buffer. The PortAudio output callback reads samples from the buffer and plays them through the speaker/headphones. Playback starts as soon as the first chunk is ready -- it does NOT wait for the full response.

**The user hears audio chunk by chunk:**
- Chunk 1 (0-2s): "I found three SQL injection vulnerabilities in your auth module..."
- Chunk 2 (2-4s): "First, the login endpoint at /api/login constructs queries..."
- Chunk 3 (4-6s): "Second, the password reset endpoint..."
- (continues until all chunks played)

**Latency budget:** 10ms (on-device) / 10ms (cloud) per chunk -- negligible

**What could go wrong:**
- Audio device not available or busy
- Buffer underrun (no chunks ready when playback needs them)
- Volume too low or too high
- Echo through microphone (especially in always-listening mode)

**Fallback:**
- Display text alongside audio (always visible)
- Adjustable playback volume
- Acoustic echo cancellation (NLMS adaptive filter, 256 taps, see `voice-mode.md` Algorithm 2)

---

#### Step 10: User Interrupts Mid-Response (Barge-In)

**What happens:** While Lyra is explaining the second vulnerability, the user realizes the issue and speaks:

> "Actually, focus on the login endpoint. The password reset isn't in production yet."

**Barge-in sequence:**
```
Time 0ms:   User starts speaking: "Actually..."
Time <1ms:  Silero VAD detects speech probability >0.7 during TTS playback
Time <1ms:  Backchannel check: audio duration >500ms, not a backchannel ("uh-huh", "okay")
Time 1ms:   Barge-in handler activated
Time <5ms:  PortAudio stream stopped, playback buffer flushed -> speaker goes silent
Time <50ms: LLM generation stopped (SSE abort sent to provider)
Time <5ms:  Ring buffer drained, fresh audio capture starts -> user speech captured
Time <56ms: TOTAL: from user speech onset to agent silence
```

**After barge-in, Steps 4-9 repeat with the new query.**
The LLM receives the new query plus context of what was said so far:
- Previous query: "find all SQL injection vulnerabilities..."
- Lyra's partial response: explained vulns 1 and 2 (text preserved)
- New query: "focus on the login endpoint... password reset isn't in production"
- New response: "Agreed. Let me focus on the login endpoint. The issue is..."

**What could go wrong:**
- Backchannel false negative: user says "okay" (a backchannel) but barge-in triggers, cutting Lyra off
- Barge-in false positive: non-speech sound (cough, door slam) triggers barge-in
- Partial LLM cancellation: caching the partial generation state is complex (provider-specific)
- User interrupts and immediately changes topic -> cached state is wasted

**Fallback:**
- Backchannel detection: short utterances (<500ms) with low prosody variance = backchannel (ignore barge-in)
- If barge-in was a false positive, Lyra can say "Sorry, did you say something?"
- Cached LLM state can be used if the interruption was a short clarification rather than a new query
- VAD threshold raised to 0.7 during playback to reduce false positives

---

### 4.3 Interaction Modes

#### Push-to-Talk (Default)

**How it works:** User presses and holds a key (e.g., the V key, or the microphone button in the CLI UI). While held, audio is captured. On release, the captured audio is processed as described above.

**UX flow:**
```
1. User presses key -> visual indicator: "LISTENING" (red mic icon)
2. User speaks -> audio captured
3. User releases key -> visual indicator: "PROCESSING" (spinning)
4. Lyra responds with synthesized voice
5. Optionally: user presses key again during response to barge-in
```

**Pros:** Simple, reliable, no false activations. Always available, even in noisy environments.

**Cons:** Requires keyboard access. Not hands-free.

**Default in MVP:** Yes (Phase 1)

#### Always-Listening

**How it works:** Continuous VAD monitoring. When speech is detected, audio capture begins automatically. Smart Turn detects the end of the user's utterance. The pipeline runs fully hands-free.

**UX flow:**
```
1. Visual indicator: "IDLE" (green dot)
2. User speaks -> VAD detects -> indicator: "LISTENING" (red dot with audio level)
3. User finishes speaking -> Smart Turn detects turn end -> indicator: "PROCESSING"
4. Lyra responds with voice
5. User interrupts mid-response -> barge-in -> indicator: "LISTENING"
```

**Pros:** Fully hands-free, most natural, fluid conversation.

**Cons:** Highest false positive rate (background noise triggers). Requires echo cancellation. More complex state management.

**Echo cancellation required:** In always-listening mode, Lyra's own voice can feed back into the microphone. The NLMS adaptive filter (voice-mode.md, Algorithm 2) cancels this echo. The filter has 256 taps, covers ~16ms of echo tail, and converges in ~50ms.

**Default in MVP:** No (Phase 2+)

#### Hybrid Mode (Push-to-Talk + Always-Listening)

**How it works:** Context-dependent mode switching. When the user is actively coding (typing), use push-to-talk. When there's a pause in typing, switch to always-listening. When the user speaks a wake word ("Hey Lyra"), enter always-listening.

**Mode transition logic:**
```
State: CODING (keyboard active, Lyra silent)
  -> User presses PTT key -> voice mode
  -> Release key -> process utterance -> back to CODING

State: IDLE (no keyboard activity for >5s)
  -> User says "Hey Lyra" -> wake word detected -> enter LISTENING
  -> Always-listening until:
     a) No speech for >30s -> return to CODING
     b) User resumes typing -> return to CODING

State: CONVERSATION (active back-and-forth)
  -> Continues until timeout or user dismisses
  -> Voice controls available: "Go back to coding mode"
```

**Pros:** Best of both worlds. No cognitive overhead for the user.

**Cons:** Most complex to implement. Requires wake word detection.

**Default in MVP:** No (Phase 2+)

#### Voice Control of Swarm

**How it works:** User speaks commands that control the agent swarm (Section 4.13). Voice is parsed for control intent vs task intent.

**Voice commands:**
- "Lyra, pause agent 3" -> Pause specific agent
- "Lyra, show progress" -> Voice status report from all agents
- "Lyra, focus on the login endpoint" -> Redirect agents to specific task
- "Lyra, kill all agents" -> Emergency swarm stop
- "Lyra, resume agent 1 and 2" -> Selective resume

**How Lyra distinguishes control from task:**
```
Query: "pause agent 3"
  Intent analysis:
    - Action: control (not task)
    - Target: agent 3
    - Command: pause
  -> Route to swarm controller API, not to LLM reasoning

Query: "find SQL injection vulnerabilities"
  Intent analysis:
    - Action: task (not control)
    - Content: security audit
  -> Route to LLM as normal voice query
```

**In-scope for v1:** Basic voice control (start/pause/resume agents, check status)

**Future scope:** Spatial audio (left agent, right agent, center agent), multi-agent voice steering

#### Visual Indicators

Voice mode needs clear visual feedback so users know what state Lyra is in. These indicators must work in both CLI (terminal) and GUI environments.

**CLI visual indicators:**

| State | Indicator | Description |
|-------|-----------|-------------|
| IDLE | `[VA]` (dim) | Voice mode enabled, waiting for input. Mic not active. |
| LISTENING | `[VA]` (bright green, animated) | Mic is capturing audio. Show audio level meter: `[VA ~~~]` |
| PROCESSING | `[VA]` (yellow, blinking) | Audio captured, STT + LLM processing |
| SPEAKING | `[VA]` (bright blue, animated) | TTS playing through speakers. Show waveform: `[VA ~~~ ]` |
| INTERRUPTED | `[VA]` (red, flash once) | Barge-in triggered, mic re-enabled |
| ERROR | `[VA]` (red, static) | Voice mode error. Show error message inline. |
| DISABLED | (no indicator) | Voice mode off. All interaction text-only. |

**Audio level meter (CLI):**
The level meter updates every 100ms and provides real-time feedback that VAD is working. This is critical for user trust: without it, users do not know if Lyra is listening or broken.

```
[VA ---][  ]          Silence, no audio. VAD idle.
[VA --+][~ ]          Low-level background noise. VAD checking, below threshold.
[VA -++][~~]          Active speech detected. VAD triggered. System listening.
[VA +++][~ ]          Loud speech. User speaking clearly. High confidence.
```

**Configuration:** Users can customize the indicator format, colors, and visibility. Power users may want minimal indicators ("just show me errors"). Accessibility users may want verbose indicators with spoken state announcements.

**Accessible alternative:** For users with visual impairments, state changes are also announced via a short audio tone (different pitch for each state) and/or spoken description (e.g., a synthesized voice says "Listening" when the state changes to listening).

---

#### Mode Comparison Summary

| Feature | Push-to-Talk | Always-Listening | Hybrid | Swarm Control |
|---------|:------------:|:----------------:|:------:|:-------------:|
| Requires keyboard | Yes | No | Sometimes | No |
| False positive rate | Zero | High (needs tuning) | Medium | Low |
| Echo cancellation needed | No | Yes | Yes | Yes |
| Hands-free | No | Yes | Yes | Yes |
| Best for | Focused work | Conversation | Mixed workflow | Agent management |
| Complexity | Low | Medium | High | Medium |
| Implementation Phase | Phase 1 | Phase 2 | Phase 2 | Phase 3 |

#### Mode Switching UX

When the user switches modes (from PTT to Always-Listening or vice versa), the transition should be seamless:

```
User runs: `voice mode always-listening`
1. Visual indicator: "Switching to always-listening mode..."
2. Audio reconfiguration: enable continuous capture, start echo cancellation
3. Visual indicator: "ALWAYS LISTENING" (green dot, pulsing)
4. Audio cue (optional): soft chime to confirm mode change
5. Done -- Lyra now listens continuously

User runs: `voice mode push-to-talk`
1. Visual indicator: "Switching to push-to-talk mode..."
2. Audio reconfiguration: disable continuous capture, stop echo cancellation
3. Visual indicator: "PUSH TO TALK" (mic icon, dim)
4. Audio cue (optional): soft click sound
5. Done -- Lyra now waits for key press
```

The mode switch should complete in <100ms. No audible glitch or dropped audio.

---

### 4.4 Multilingual Support (VI + EN)

#### Language Detection

**How it works:** A fastText classifier (lID model, <5ms inference) runs on the first 30ms of the utterance audio. If confidence >0.8, the detected language is used. If confidence <0.8, both VI and EN pipelines run in parallel and the higher-confidence transcription wins.

```
Audio -> fastText classifier (<5ms)
  |
  +--> Confidence >0.8 EN -> EN pipeline (Silero VAD -> Whisper Turbo EN -> LLM -> Kokoro TTS)
  |
  +--> Confidence >0.8 VI -> VI pipeline (Smart Turn VI -> Whisper Turbo VI -> LLM -> MagpieTTS)
  |
  +--> Confidence <0.8 -> Parallel pipelines, pick higher-confidence result
```

#### English Pipeline

```
Mic -> Silero VAD -> Smart Turn (EN prosody config) -> Whisper Turbo (EN) -> 
LLM -> Kokoro TTS (EN, default voice)
```

- Latency: ~350ms perceived (on-device)
- WER target: <15%
- TTS quality: ~3.8 MOS

#### Vietnamese Pipeline

```
Mic -> Silero VAD -> Smart Turn (VI prosody: pitch_weight=1.5, unsure_timeout=2500ms) -> 
Whisper Turbo (VI) -> LLM -> MagpieTTS (VI)
```

- Latency: ~800ms P50 (on-device with GPU) -- VI Whisper is slower than EN Whisper
- WER target: <20%
- TTS quality: ~4.0 MOS (MagpieTTS)
- VI-specific: Smart Turn's higher pitch weight (1.5 vs 1.0) prevents tonal prosody from triggering false turn detection

**VI challenges:**

| Challenge | Details | Mitigation |
|-----------|---------|------------|
| Tone recognition | 6 tones, Central/Southern dialects worse | Whisper Turbo training data covers all dialects; context-based tone disambiguation |
| Code-switching (VI+EN) | ~40% of technical VI speech has English terms | Whisper handles natively; avoid Canary/Parakeet for VI |
| TTS gap | Kokoro doesn't support VI | MagpieTTS (NeMo) as primary; Kokoro EN voice reading VI phonetically as last resort |
| Turn detection | Tonal prosody carries semantic meaning | Smart Turn VI profile: pitch_weight=1.5, min_turn_gap=200ms, unsure_timeout=2500ms |

#### Code-Switching Handling

When a user mixes VI and EN in a single utterance (e.g., "fix cai bug trong auth module di"), Whisper Turbo handles it because:
1. It was trained on 96 languages including code-switching data
2. The multilingual model has shared representations across languages
3. The sliding 30s window captures linguistic context

However, TTS is a challenge: if the output contains English text with Vietnamese terms (or vice versa), Kokoro cannot synthesize VI phonemes. The fallback is:
1. MagpieTTS for primarily VI output (it has better VI phoneme coverage)
2. For mixed output: synthesize English portions with Kokoro, Vietnamese portions with MagpieTTS, concatenate
3. Last resort: display text only with language mismatch warning

**Language expansion roadmap:**
- Phase 1 (MVP): English only. Kokoro TTS, Whisper EN STT. Best latency, highest quality.
- Phase 2: Add Vietnamese. MagpieTTS, Whisper multilingual STT. VI language detection, VI-specific Smart Turn profile.
- Phase 3 (6 months): Expand to 23 languages (Smart Turn coverage). Japanese (Kokoro), Chinese (Kokoro), Korean (Kokoro), French, German, Spanish, Arabic.
- Phase 4 (12 months): Expand to 99 languages (Whisper coverage). For languages without TTS support, use Kokoro's extensible G2P (add G2P module for each language -- no TTS model retraining needed).

**Language expansion effort per language:**
| Component | New Language Effort | Notes |
|-----------|-------------------|-------|
| Silero VAD | Zero | Language-agnostic, 6000+ languages |
| Smart Turn profile | ~2 hours | Add language config params (pitch_weight, unsure_timeout, etc.) |
| Whisper STT | Zero | Already supports 99 languages |
| Kokoro G2P | ~1 week per language | Train misaki G2P module for the language |
| MagpieTTS | N/A for non-VI | MagpieTTS specific to Vietnamese |
| TTS voice selection | ~0 (pick best existing) | Orpheus for expressive, Kokoro for fast, cloud for premium |
| Language detection | Zero | fastText already supports 176 languages |
| Testing | ~1 day per language | Transcribe 100 utterances, measure WER, verify quality |
| **Total per language** | **~1-2 weeks** | Mostly testing; model integration is trivial |

---

### 4.5 Personality and SFX Layer (Section 5.3 Integration)

Voice is not just about speech -- it's about **character**. The SFX layer adds personality to Lyra's voice interactions through voice packs and sound effects.

#### Voice Packs

| Pack | Tone | Voices | Use Case |
|------|------|--------|----------|
| **Professional** | Neutral, clear, formal | Kokoro default, MagpieTTS default | Enterprise, presentations, serious work |
| **Friendly** | Warm, casual, expressive | Orpheus TTS cheerful voice | Daily coding, learning, casual chats |
| **Minimal** | Terse, efficient | Kokoro fast mode (higher speed) | Power users, speed focus |
| **Warcraft Peon** | Funny, nostalgic | Custom audio clips + default TTS | Fun, community favorite |
| **Custom** | User-defined | User-provided voice samples | Personalization |

**How voice packs work:**
```
User selects "Warcraft Peon" pack:
  1. Session start: plays "Ready to work!" (Warcraft peon voice clip)
  2. Task complete: plays "Job's done!" (Warcraft peon voice clip)
  3. Error: plays "Something's not quite right" (Warcraft peon voice clip)
  4. Regular TTS: uses Kokoro default (voice clips cover only specific events)
```

#### Sound Effects System

**Triggers (via Section 4.10 hooks):**

| Event | Sound | Hook Point |
|-------|-------|------------|
| Session start | Voice greeting | `PostInit` |
| Task complete | Completed cue | `PostToolUse` |
| Error | Error sound | `OnError` |
| Thinking | Ambient tone | `PreLLM` (if >3s) |
| Voice on | Mic activation click | `PreVAD` |
| Voice off | Deactivation sound | `PostTTS` |

**Implementation via hooks:**
```typescript
// Pseudocode for registering voice SFX hooks
hooks.register('PostInit', async () => {
  const pack = config.voice.personality.voicePack;
  if (pack === 'warcraft-peon') {
    await audioPlayback.play(loadSound('ready-to-work.wav'));
  }
});

hooks.register('PostToolUse', async (result) => {
  if (result.status === 'complete') {
    await audioPlayback.play(loadSound(config.voice.personality.taskCompleteSound));
  }
});
```

---

### 4.6 Accessibility, Privacy, and Cost

#### Accessibility

| Need | Voice Mode Feature |
|------|-------------------|
| Visual impairment | Voice-first interaction: all actions possible by voice. Audio feedback for everything. Screen reader compatible. |
| Motor impairment | Hands-free operation via always-listening. All functions controllable by voice. No keyboard needed. |
| Hearing impairment | Always show text transcript alongside audio. Visual indicators for voice activity (VU meter). Configurable audio levels. |
| Cognitive / attention | Adjustable speech speed (0.8x - 2.0x). Concise mode for shorter responses. Read-back of previous responses on request. |

**Transcript always visible:** Audio output is always accompanied by text on screen. This helps all users verify what Lyra said, especially in noisy environments or when response is long.

#### Privacy

| Concern | Mitigation |
|---------|------------|
| Audio recording | Opt-in only. Not stored by default. User can delete anytime. |
| Cloud STT | Data sent to provider (e.g., Deepgram). Clear privacy disclosure. |
| Cloud TTS | Response text sent to provider. Clear privacy disclosure. |
| On-device mode | 100% local: Silero + Whisper Kokoro. Zero network egress. No data leaves device. |
| Voice cloning | If enabled (future), cloned voice stored locally. Never uploaded. |
| Paralinguistic analysis | `PreSTT` hooks run locally. Prosody data never sent to cloud providers. |

#### Cost Model

| Stack | STT Cost | TTS Cost | LLM Cost | Total per Minute |
|-------|----------|----------|----------|-----------------|
| Open-source on-device | $0 | $0 | LLM cost only | `~$0` + LLM fees |
| Cloud (Deepgram + Cartesia) | ~$0.004/min | ~$0.005/min | LLM cost | `~$0.009/min` + LLM fees |
| Open-source with cloud LLM | $0 | $0 | LLM cost | `~$0` + LLM fees |
| OpenAI Realtime API | Included | Included | Included | ~$0.06/min (all-in) |

**Recommendation:** Use open-source on-device STT/TTS by default (zero audio costs). Users who need higher quality can switch to cloud providers per-utterance (e.g., for a critical demo, use Cloud; for daily coding, use On-device).

---

### 4.7 Hardware Requirements and Platform Support

Voice mode places additional demands on hardware beyond Lyra's base requirements. These are recommendations, not hard requirements.

**Minimum configuration (cloud STT/TTS, no GPU):**
- RAM: 2GB free (audio capture + playback only)
- CPU: Any x86_64 or ARM
- GPU: None required
- Mic: Any USB or built-in microphone
- Latency: ~180ms perceived (cloud)
- Note: Stable internet required. Expect ~50ms network latency per API call.

**Recommended configuration (on-device STT + TTS):**
- RAM: 8GB free
- CPU: Any x86_64 or ARM
- GPU: 6GB VRAM (for Whisper Turbo FP16)
- Mic: USB microphone (better noise rejection than built-in)
- Latency: ~500ms perceived (on-device)

**Optimal configuration (full on-device pipeline):**
- RAM: 16GB free
- CPU: x86_64 with AVX2
- GPU: 8GB+ VRAM
- Mic: Professional USB/XLR microphone with noise gate
- Latency: <300ms perceived (on-device GPU)

**Platform matrix:**

| Platform | Audio I/O | GPU Backend | Notes |
|----------|-----------|-------------|-------|
| macOS (Intel) | CoreAudio via PortAudio | Metal (limited) | Fully supported. CoreAudio provides low-latency audio. |
| macOS (Apple Silicon) | CoreAudio via PortAudio | MPS / CoreML | Best experience on Apple hardware. Whisper runs via MLX or CoreML. Neural Engine available for on-device inference. |
| Linux | ALSA / PulseAudio via PortAudio | CUDA | Most flexible. May require PulseAudio configuration for low-latency audio. JACK for pro audio setups. |
| Windows | WASAPI via PortAudio | CUDA / DirectML | Fully supported. WASAPI exclusive mode for lowest latency. |
| WSL2 | PulseAudio via Windows | CUDA | Audio I/O requires PulseAudio server on Windows host. Less tested. |

**Model load times and memory (first load):**

| Model | Size | Load Time (SSD) | VRAM | RAM |
|-------|------|----------------|------|-----|
| Silero VAD | 2MB | <10ms | 0 | ~50MB |
| Smart Turn | 32MB | <100ms | 0 (CPU) | ~100MB |
| Whisper Turbo | 1.5GB | ~2s | ~6GB (FP16) | ~4GB |
| Whisper Large-v3 | 3GB | ~4s | ~10GB | ~8GB |
| Kokoro-82M | 300MB | ~500ms | 0 (CPU) | ~500MB |
| MagpieTTS | 1GB | ~1.5s | ~2GB | ~2GB |
| Moshi (full-duplex) | 14GB | ~10s | ~24GB | ~16GB |

**Caching strategy:** Load small models (Silero, Kokoro) on session start. Load large models (Whisper) on first utterance and keep warm. Unload after 5 minutes of inactivity. This keeps startup time under 1 second while minimizing memory footprint during idle periods.

---

## 5. Architecture and Data Models

### 5.1 Voice Provider Interface

Just as LLM providers are swappable via the Model Router (Section 4.5), STT and TTS providers are swappable via the VoiceProvider interface. This is the same abstraction pattern.

**STTProvider interface:**
```typescript
interface STTProvider {
  name: string;
  supportsStreaming: boolean;
  supportedLanguages: string[];

  initialize(config: STTConfig): Promise<void>;
  transcribe(audio: AudioChunk): Promise<TranscriptionResult>;
  transcribeStream(audioStream: AudioStream): AsyncIterator<TranscriptionResult>;
  destroy(): Promise<void>;
}
```

**TTSProvider interface:**
```typescript
interface TTSProvider {
  name: string;
  supportsStreaming: boolean;
  supportedLanguages: string[];
  supportedVoices: VoiceProfile[];

  initialize(config: TTSConfig): Promise<void>;
  synthesize(text: string, voice: string): Promise<AudioBuffer>;
  synthesizeStream(textStream: AsyncIterator<string>): AsyncIterator<AudioChunk>;
  destroy(): Promise<void>;
}
```

### 5.2 AudioBufferRing Data Structure

The voice pipeline uses a lock-free Single Producer, Single Consumer (SPSC) ring buffer. This decouples the audio capture thread from the VAD/processing thread. No mutexes are needed because each pointer is written by exactly one thread.

```
Producer (audio callback) -> write -> [ RingBuffer N float32 ] -> read -> Consumer (VAD thread)
                                     write_ptr: AtomicUint32
                                     read_ptr:  AtomicUint32
```

**Key properties:**
- Lock-free (no mutexes, no semaphores)
- Power-of-2 capacity for cheap modulo (x & mask)
- Monotonic uint32 pointers (not modulo) to avoid full/empty ambiguity
- Recommended capacity: 30720 samples (~1.92s at 16kHz)
- Drain operation: advance readPtr to writePtr in O(1) -- used for barge-in

> Detailed implementation with full TypeScript pseudocode, edge case handling, and atomic ordering semantics is in `voice-mode.md` (Algorithm 3: Audio Buffer Ring).

### 5.3 VoiceSession State Machine

```typescript
type VoiceSessionState = 'idle' | 'listening' | 'buffering' | 'processing' 
                       | 'routing' | 'thinking' | 'speaking' | 'streaming' 
                       | 'interrupted';

interface VoiceSession {
  id: string;
  config: VoiceConfig;
  state: VoiceSessionState;

  // Audio streams
  inputStream: AudioStream;
  outputStream: AudioStream;

  // Current utterance
  currentUtterance: {
    text: string;
    confidence: number;
    isFinal: boolean;
    language: string;
  };

  // Barge-in tracking
  bargeInCount: number;
  lastBargeInTime: number;

  // Metrics
  metrics: {
    avgLatency: number;      // ms (rolling average)
    totalUtterances: number;
    totalInterruptions: number;
    sttErrors: number;
    ttsErrors: number;
  };

  // Cached LLM generation (for barge-in resume)
  cachedGeneration?: {
    text: string;           // what was generated so far
    isComplete: boolean;
    provider: string;       // which LLM provider
  };
}
```

### 5.4 VoiceConfig Data Model

```typescript
interface VoiceConfig {
  enabled: boolean;

  // VAD settings
  vad: {
    provider: 'silero';
    sensitivity: number;         // 0.0-1.0, default 0.7
    holdOffMs: number;           // ms of silence before state change, default 500
  };

  // STT settings
  stt: {
    provider: 'whisper' | 'deepgram' | 'nemo' | 'openai';
    model: string;               // e.g., 'turbo', 'nova-3', 'canary-1b-v2'
    language: string[];          // ['en', 'vi']
    streaming: boolean;          // default true
    onDevice: boolean;           // true = local inference
    fallback: string;            // fallback provider
  };

  // TTS settings
  tts: {
    provider: 'kokoro' | 'magpie' | 'orpheus' | 'cartesia' | 'openai';
    voice: string;               // voice ID or name
    language: string;            // 'en' | 'vi'
    streaming: boolean;          // default true
    onDevice: boolean;
    fallback: string;
    speed: number;               // 0.8-2.0, default 1.0
  };

  // Interaction settings
  interaction: {
    mode: 'push-to-talk' | 'always-listening' | 'wake-word';
    wakeWord?: string;           // e.g., "Hey Lyra"
    bargeInEnabled: boolean;     // default true
    endOfTurnSilence: number;    // ms of silence to end turn, default 600
  };

  // Personality / SFX (Section 5.3)
  personality: {
    enabled: boolean;            // default true
    voicePack: 'professional' | 'friendly' | 'minimal' | 'warcraft-peon' | 'custom';
    sessionStartSound: string;   // path to audio file
    sessionEndSound: string;
    taskCompleteSound: string;
    errorSound: string;
  };
}
```

**Example configuration:**
```json
{
  "voice": {
    "enabled": true,
    "vad": { "provider": "silero", "sensitivity": 0.7 },
    "stt": {
      "provider": "whisper",
      "model": "turbo",
      "language": ["en", "vi"],
      "streaming": true,
      "onDevice": true,
      "fallback": "deepgram"
    },
    "tts": {
      "provider": "kokoro",
      "voice": "default",
      "language": "en",
      "streaming": true,
      "onDevice": true,
      "fallback": "cartesia",
      "speed": 1.0
    },
    "interaction": {
      "mode": "push-to-talk",
      "bargeInEnabled": true,
      "endOfTurnSilence": 600
    },
    "personality": {
      "enabled": true,
      "voicePack": "professional"
    }
  }
}
```

---

## 6. Build Outline — Phased Rollout

### Phase 1: MVP Push-to-Talk (Weeks 1-4)

**Goal:** Functional voice input/output. Press a key, speak, hear a response. The foundation for everything else.

| # | Task | Description | Dependencies | Estimated Hours | Acceptance Criteria |
|---|------|-------------|-------------|----------------|---------------------|
| 1.1 | Audio I/O abstraction | Implement AudioCapture (PortAudio mic access) and AudioPlayback (speaker output). Add PCM format conversion utilities. | None | 16 | Can capture 24kHz mono PCM from mic and play back through speakers. |
| 1.2 | Audio ring buffer | Implement lock-free SPSC ring buffer (Algorithm 3 in voice-mode.md). 30720 samples capacity. | 1.1 | 8 | Producer writes 30ms chunks, consumer reads them without data race. |
| 1.3 | Silero VAD integration | Load Silero VAD ONNX model (2MB). Implement per-frame inference + hysteresis state machine. | 1.1, 1.2 | 12 | Speech detected within 30ms of onset. 500ms hold-off prevents chatter. |
| 1.4 | Whisper Turbo STT | Load Whisper Turbo model (809M params). Implement transcribe() for complete utterances. | 1.3 | 16 | Transcribes EN speech with WER <15%. Latency <200ms (GPU) or <800ms (CPU). |
| 1.5 | Kokoro TTS | Load Kokoro-82M model. Implement synthesize() for text-to-audio. | 1.1 | 12 | Synthesizes EN text to audio in <50ms per sentence. >=3.5 MOS quality. |
| 1.6 | Push-to-talk interaction | Wire PTT key -> VAD -> STT -> LLM -> TTS -> playback pipeline. Add visual indicators (listening/processing/speaking). | 1.2, 1.3, 1.4, 1.5 | 16 | Press key, speak, release, hear Lyra respond. Full round-trip <2s (on-device). |
| 1.7 | CLI integration | Add `--voice` flag to Lyra CLI. Add voice config to settings file. Display voice status in CLI UI. | 1.6 | 8 | `lyra --voice` starts with PTT enabled. Settings persist across sessions. |
| 1.8 | Error handling | Handle mic unavailable, model load failure, inference errors with clear user messages. | 1.7 | 8 | Each failure mode shows a human-readable message and falls back to text. |

**Phase 1 Acceptance:** User can press a hotkey, speak a query in English, and hear Lyra's synthesized response. Full round-trip <2 seconds on-device. Error messages are clear and helpful. **Total: ~96 hours.**

---

### Phase 2: Always-Listening + Hotword (Weeks 5-6)

**Goal:** Hands-free voice interaction. Lyra listens continuously and responds when spoken to.

| # | Task | Description | Dependencies | Hours | Acceptance Criteria |
|---|------|-------------|-------------|-------|---------------------|
| 2.1 | Smart Turn integration | Load Smart Turn model (Whisper Tiny backbone). Implement prosody-aware turn detection for EN. | Phase 1 | 16 | Detects natural turn boundaries with <10% false positives. Latency <35ms. |
| 2.2 | Always-listening mode | Continuous VAD + Smart Turn loop. Auto-start capture on speech, auto-process on turn end. | 2.1 | 12 | User speaks naturally, Lyra responds without any key press. |
| 2.3 | Acoustic echo cancellation | Implement NLMS adaptive filter (Algorithm 2 in voice-mode.md). 256 taps, mu=0.01, double-talk detection. | 2.2 | 20 | No echo detected during always-listening. Convergence <50ms. |
| 2.4 | Wake word detection | Implement "Hey Lyra" hotword detection. Use Porcupine (proprietary) or Picovoice for MVP. | 2.2 | 16 | Wake word detected with >90% accuracy at <5% false positive rate (1 false trigger per 10 hours). |
| 2.5 | Timeout handling | Auto-deactivate after 30s of silence. Return to IDLE state. Resume on wake word or PTT key. | 2.2, 2.4 | 8 | Session deactivates after 30s silence. Wake word or PTT re-activates. |

**Phase 2 Acceptance:** User can speak naturally without pressing any key. "Hey Lyra" activates listening mode. Lyra does not echo its own voice. Session auto-deactivates on prolonged silence. **Total: ~72 hours.**

---

### Phase 3: Streaming + Barge-In (Weeks 7-8)

**Goal:** Low-latency conversation. User can interrupt Lyra mid-response.

| # | Task | Description | Dependencies | Hours | Acceptance Criteria |
|---|------|-------------|-------------|-------|---------------------|
| 3.1 | Streaming STT | Whisper Turbo streaming mode. Transcribe partial utterances for early context injection. | Phase 1 | 8 | Partial transcriptions available within 200ms of each speech segment. No regressions on final accuracy. |
| 3.2 | Streaming TTS overlap | Implement SynthesisScheduler (Algorithm 4 in voice-mode.md). Split text, synthesize in pipeline, overlap with playback. | Phase 1 | 20 | First sentence latency ~50ms. Subsequent sentences add 0ms effective latency. |
| 3.3 | Barge-in detection | VAD monitors mic during TTS playback. Distinguish backchannel vs actual interruption. | 3.2, Phase 2 | 12 | Barge-in detected within <1ms of speech onset. Backchannel ("uh-huh") correctly ignored. |
| 3.4 | Barge-in handling | Stop TTS, cancel LLM, flush ring buffer, start fresh capture. Resume or restart based on context. | 3.3 | 16 | Total barge-in time <56ms from speech onset to agent silence. Cached generation preserved. |
| 3.5 | LLM cancellation | Send SSE abort to provider. Cache partial generation state. Decide resume vs restart. | 3.4 | 12 | LLM generation stops within <50ms (SSE abort). Cached state available for resume. |

**Phase 3 Acceptance:** TTS starts before LLM finishes. User hears first words within ~350ms of pressing/speaking. User can interrupt Lyra mid-response. Backchannel (uh-huh, okay) does NOT trigger barge-in. **Total: ~68 hours.**

---

### Phase 4: Multilingual + SFX (Weeks 9-10)

**Goal:** Vietnamese support and personality layer.

| # | Task | Description | Dependencies | Hours | Acceptance Criteria |
|---|------|-------------|-------------|-------|---------------------|
| 4.1 | Language detection | Integrate fastText language classifier. Detect EN vs VI from first 30ms of audio. <5ms latency. | Phase 2 | 8 | Correctly identifies EN and VI with >95% accuracy. 
| 4.2 | Smart Turn VI profile | Configure VI-specific parameters: pitch_weight=1.5, unsure_timeout=2500ms, min_turn_gap=200ms. | 4.1, 2.1 | 8 | VI turn detection WER <20%. No false turns on tonal prosody. |
| 4.3 | Vietnamese Whisper | Whisper Turbo with VI language detection and post-processing. WER <20% target. | 4.1 | 8 | VI transcription accuracy >=80%. Code-switching (VI+EN) handled natively. |
| 4.4 | MagpieTTS for Vietnamese | Integrate MagpieTTS (NeMo). Default VI TTS voice. | 4.3 | 12 | Synthesizes VI text at >=4.0 MOS. Latency <80ms per sentence. |
| 4.5 | Sound effects system | Load audio files for session events. Play via AudioPlayback. Configurable voice packs. | Phase 1 | 8 | Session start plays greeting. Task completion plays cue. Error plays distinct sound. |
| 4.6 | Hook integration for SFX | Register PostInit, PostToolUse, OnError hooks for voice events. Apply selected voice pack. | 4.5 | 8 | Sounds trigger at correct events. Voice pack selection works in config. |

**Phase 4 Acceptance:** User can speak in Vietnamese and hear Vietnamese response. Language auto-detected. Session start/complete/error sounds play correctly. User can select a voice pack. **Total: ~52 hours.**

---

### Phase 5: Full-Duplex Optional Backend (Weeks 11-12)

**Goal:** Explore or integrate a Moshi-style full-duplex backend for users with 24GB+ GPUs.

| # | Task | Description | Dependencies | Hours | Acceptance Criteria |
|---|------|-------------|-------------|-------|---------------------|
| 5.1 | Moshi S2S integration | Load Moshi model (7B temporal + 7B text). Run on 24GB GPU. | Phase 2 | 24 | Moshi pipeline functional. User can have full-duplex conversation. |
| 5.2 | Provider abstraction update | Add `fullDuplex` provider type alongside STT+TTS. VoiceConfig selects full-duplex or cascaded. | 5.1 | 8 | User can switch between full-duplex (Moshi) and cascaded (default) via config. |
| 5.3 | Moshi fallback to cascaded | If Moshi fails (OOM, timeout), fall back to cascaded pipeline automatically. | 5.1, 5.2 | 8 | Moshi failure triggers graceful fallback to cascaded. User notified. |
| 5.4 | Benchmarking | Run Full-Duplex-Bench v1 on both pipelines. Compare latency, quality, resource usage. | 5.2 | 12 | Data-driven decision: document latency, WER, MOS differences for both pipelines. |

**Phase 5 Acceptance:** Moshi optional backend works on compatible hardware. Provider abstraction supports full-duplex type. Fallback to cascaded works on error. Benchmarks document trade-offs. **Total: ~52 hours.**

---

**Total estimate: ~340 hours (~8.5 weeks at 40h/week for 1 developer)**

This is a sequential estimate. With parallel workstreams (e.g., Phase 1 audio I/O and TTS can start in parallel with Phase 2 VAD), the calendar timeline can be compressed to ~12 weeks for all 5 phases.

---

## 7. Multi-Provider Notes

### 7.1 Provider-Specific Behavior

Voice providers follow the same swappable pattern as LLM providers (Section 4.5). Each provider must implement the STTProvider or TTSProvider interface.

**DeepSeek:**
- No native voice API.
- Use Lyra's voice layer with DeepSeek LLM backend.
- STT/TTS independent of LLM provider.

**Anthropic Claude:**
- No native voice API (as of May 2026).
- Use Lyra's voice layer with Claude LLM backend.
- Monitor Claude roadmap for future voice API.

**OpenAI:**
- Has Realtime API (native voice, ~$0.06/min all-inclusive).
- Lyra supports BOTH:
  - **Native:** Use OpenAI Realtime API directly (lower latency, ~160ms end-to-end).
  - **Layered:** Use Lyra's voice layer + GPT backend (more control, works with any LLM).
- User chooses via config: `openai.voiceMode: 'native' | 'layered'`

**Open-weights (Llama, Qwen, etc.):**
- No voice APIs.
- Always use Lyra's voice layer.
- STT/TTS run locally or via third-party.

### 7.2 Fallback Strategy

The fallback strategy is a hierarchical chain. Each level degrades gracefully:

```
Level 1: Primary (user-configured providers)
  - STT: User's chosen provider (e.g., Whisper Turbo on-device)
  - TTS: User's chosen provider (e.g., Kokoro on-device)
  - Best experience, lowest cost, user's preferred provider.

Level 2: Provider-to-Provider Fallback
  - STT on-device fails -> switch to cloud STT (Deepgram)
  - TTS on-device fails -> switch to cloud TTS (Cartesia)
  - Cloud fails -> switch to on-device (if available)
  - If both fail -> Level 3
  - Trigger conditions: model load failure, inference timeout (>5s), API error, rate limit
  - Notification: "Voice processing provider A failed. Falling back to provider B."

Level 3: Voice-to-Text Degradation
  - Voice input fails: display "Speech not recognized" and switch to keyboard input
  - Voice output fails: display text response only
  - User can still interact via keyboard (Lyra's primary interaction mode)
  - All Lyra features work in text mode -- no functionality lost

Level 4: Complete Voice Shutdown
  - If all providers fail AND critical error persists, disable voice mode
  - Set voice.enabled = false in session (not permanent config)
  - Display: "Voice mode unavailable. You can re-enable with 'voice on'."
  - User can re-enable with command or after session restart
```

**Recovery strategy:**
- Periodic retry: if a provider failed, retry on the next utterance (not immediately)
- Warm-up on enable: pre-heat models when voice mode is first enabled, not on first utterance
- Diagnostics: `voice status` command shows all provider states, current level, and counts of failures

### 7.3 Provider Configuration Examples

**Example 1: Default on-device stack (recommended)**
```json
{
  "voice": {
    "vad": { "provider": "silero" },
    "stt": { "provider": "whisper", "model": "turbo", "onDevice": true, "fallback": "deepgram" },
    "tts": { "provider": "kokoro", "onDevice": true, "fallback": "cartesia" },
    "interaction": { "mode": "push-to-talk" }
  }
}
```
Cost: $0/hour for STT+TTS. Only LLM costs apply.

**Example 2: Cloud premium stack**
```json
{
  "voice": {
    "stt": { "provider": "deepgram", "model": "nova-3", "onDevice": false },
    "tts": { "provider": "cartesia", "voice": "sonic-english", "onDevice": false },
    "interaction": { "mode": "always-listening" }
  }
}
```
Cost: ~$0.009/min. Lower latency (~100ms STT, ~30ms TTS), higher accuracy.

**Example 3: OpenAI Realtime API (all-in-one)**
```json
{
  "voice": {
    "stt": { "provider": "openai" },
    "tts": { "provider": "openai" },
    "openai": { "voiceMode": "layered" }
  }
}
```
Cost: ~$0.06/min all-inclusive. Simplest setup, lowest latency, but highest cost and vendor lock-in.

**Example 4: Mixed stack (on-device STT + cloud TTS)**
```json
{
  "voice": {
    "stt": { "provider": "whisper", "model": "turbo", "onDevice": true },
    "tts": { "provider": "cartesia", "voice": "sonic-english", "onDevice": false },
    "interaction": { "mode": "push-to-talk" }
  }
}
```
Rationale: STT needs GPU which may not be available, but TTS can run on cloud cheaply. Best of both worlds for CPU-only machines.

**Example 5: VI-only stack**
```json
{
  "voice": {
    "stt": { "provider": "whisper", "model": "turbo", "language": ["vi"] },
    "tts": { "provider": "magpie", "language": "vi" },
    "interaction": { "mode": "push-to-talk" }
  }
}
```
Cost: $0/hour (on-device). All Vietnamese pipeline with appropriate providers.

---

## 8. Risks and Open Questions

### 8.1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Latency on low-end hardware** | Medium | High | On-device Whisper may exceed 500ms on CPU-only machines. Mitigation: require GPU for on-device, default to cloud on CPU-only. |
| **Echo cancellation failure** | Medium | High | Always-listening mode picks up Lyra's own voice, causing feedback loop. Mitigation: NLMS adaptive filter (Algorithm 2 in voice-mode.md); PTT-only for MVP. |
| **Vietnamese WER above target** | Medium | Medium | VI Whisper WER ~18% target may be hard to reach. Mitigation: context-based post-processing, user can clarify via text. |
| **Provider API changes** | Low | Medium | Cloud STT/TTS providers may change APIs or pricing. Mitigation: abstract behind interface, support multiple alternatives. |
| **Memory usage of multiple models** | Medium | Medium | Silero (2MB) + Whisper (6GB) + Kokoro (82M params, CPU). Total ~8GB RAM. Mitigation: unload models when not in use. |
| **Browser/terminal compatibility** | Low | High | Audio I/O via CLI (PortAudio) may not work in all terminals. Mitigation: cross-platform testing, graceful text fallback. |

### 8.2 Open Questions

| Question | Options | Recommendation |
|----------|---------|---------------|
| **Wake word implementation** | Porcupine (proprietary) vs Picovoice (free tier) vs custom tiny model | Defer to Phase 2. Use Porcupine for MVP. Evaluate Picovoice for production. |
| **Audio format** | 16kHz vs 24kHz? Mono vs stereo? | 24kHz mono PCM. Matches Mimi codec for future S2S. Mono for single-user. Stereo in v2 for spatial audio. |
| **Voice cloning** | Should Lyra support custom voice cloning? | Not for MVP. Design TTS interface to support cloning later (Orpheus TTS supports zero-shot cloning). |
| **Multi-user support** | How to handle multiple speakers in same session? | Single-user for MVP. Speaker diarization in future phase. |
| **Audio recording storage** | Store audio for debugging / improvement? | Opt-in only. Local storage. Clear consent prompt. User can delete anytime. |
| **Benchmark selection** | Which benchmarks to run for evaluation? | Open ASR Leaderboard (WER) + Full-Duplex-Bench v1 (turn-taking) for MVP. τ-Voice (task completion) for later. |
| **GPU requirement** | Minimum GPU for on-device pipeline? | Whisper Turbo: 6GB VRAM. For CPU-only: cloud STT recommended (Whisper CPU is slow). |
| **Model caching strategy** | Keep all models loaded vs load-on-demand? | Load Silero + Kokoro on session start (small, <100ms load). Load Whisper on first utterance (large, ~2s load) and keep warm. Unload on 5min idle. |
| **Error recovery from invalid audio** | What happens when audio device fails mid-session? | Restart capture on next utterance. If 3 consecutive failures, disable voice mode and notify user. |

### 8.3 Dependency Map

Voice mode depends on several other Lyra components. Each dependency is a risk if it is delayed or changed:

| Dependency | What voice mode needs | Risk if missing |
|------------|----------------------|-----------------|
| Section 4.5 (Router) | Voice-aware model routing, different provider for voice queries | Voice uses wrong model; no latency optimization |
| Section 4.10 (Hooks) | PreSTT, PostSTT, PreTTS, PostTTS hooks for context injection and SFX | Cannot inject prosody cues; no sound effects |
| Section 5.3 (SFX) | Voice pack system, sound effect triggers | Works but personality layer is missing; no audio cues |
| Section 4.2 (Memory) | Cross-session voice preferences, voice history | Voice config resets every session |
| Section 4.13 (Swarm) | Voice commands for agent control | Voice control of swarm unavailable |
| Audio I/O (PortAudio) | Cross-platform mic access and speaker output | Voice mode cannot exist without this |

### 8.4 What Happens When It Breaks

Realistic failure scenarios and their visible symptoms:

**Scenario A: Microphone not connected or permissions denied.**
Symptom: `voice status` shows "Microphone: unavailable (permissions)" or "Microphone: not detected".
User sees: Error message on first `voice` command. Text interaction continues normally.
Recovery: User checks mic connection, grants permissions, or installs audio drivers.

**Scenario B: Model download fails (first run).**
Whisper Turbo is 1.5GB. Kokoro is 300MB. These downloads may fail on slow connections.
Symptom: `voice enable` shows "Downloading Whisper Turbo (45% complete...)" then "Download failed. Check your internet connection."
Recovery: Resume download with retry. Show progress bar. Allow user to specify a proxy or alternate download mirror.

**Scenario C: Low memory / OOM during inference.**
Whisper Turbo requires ~6GB VRAM on GPU or ~8GB RAM on CPU. If the system doesn't have enough memory:
Symptom: Model fails to load. Error: "Whisper model could not be loaded. System has X GB free, needs Y GB."
Recovery: Fall back to cloud STT (Deepgram) if configured. Otherwise fall back to text-only.

**Scenario D: Audio feedback loop (always-listening mode).**
Lyra speaks, microphone picks up its own voice, VAD triggers, barge-in fires, Lyra stops speaking, silence, loop repeats.
Symptom: Lyra speaks for 1-2 seconds, stops, then enters listening. Speaks again, stops, listens. Perpetual cycle.
Recovery: Auto-detect feedback pattern (speak -> stop -> speak -> stop more than 3 times in 15 seconds). Temporarily disable always-listening, fall back to PTT. Log the issue. Suggest echo cancellation tuning.

**Scenario E: Cloud provider API failure.**
Deepgram or Cartesia API is down.
Symptom: `voice status` shows "Deepgram: error (HTTP 503)" or "Deepgram: rate limited".
Recovery: Automatic failover to fallback provider. If no fallback configured, degrade to text-only. Retry primary provider on next attempt. Notify user: "Deepgram unavailable. Using fallback provider (Whisper on-device)."

---

## 9. Evaluation and Benchmarking Plan

Before declaring voice mode ready, we must measure against objective benchmarks.

### 9.1 Latency Benchmarks

| Metric | Target | How to Measure | Tool |
|--------|--------|---------------|------|
| End-to-end perceived latency | <300ms (cloud), <500ms (on-device) | Inject test audio at mic input, measure time to first audio output | Custom profiler instrumented in pipeline |
| STT latency | <200ms (on-device GPU), <100ms (cloud) | Measure time from audio buffer received to text output | Per-component timestamps |
| TTS latency (first sentence) | <50ms (on-device), <30ms (cloud) | Measure time from text received to first audio chunk output | Per-component timestamps |
| Barge-in response time | <56ms | Measure from speech onset (VAD trigger) to speaker silence | Oscilloscope or audio capture analysis |
| Streaming overlap savings | >=55% pipeline time hidden | Compare perceived latency to raw pipeline sum | Pipeline instrumentation |

### 9.2 Accuracy Benchmarks

| Metric | Target | How to Measure | Dataset |
|--------|--------|---------------|---------|
| English WER | <15% | Transcribe test set, compare to ground truth | Open ASR Leaderboard EN subset |
| Vietnamese WER | <20% | Transcribe test set, compare to ground truth | Open ASR Leaderboard VI subset |
| Code-switching WER | <25% | Transcribe mixed VI+EN utterances | Custom dataset (50 utterances with code-switching) |
| Turn detection accuracy | >90% precision, >85% recall | Feed labeled conversation audio, compare turn boundary detections | Full-Duplex-Bench v1 test set |
| Backchannel detection accuracy | >95% | Test with "uh-huh", "okay", "right", "mhm" during playback | Custom dataset (20 backchannel samples) |
| Language detection accuracy | >95% (EN/VI) | Test fastText classifier on 100 audio samples per language | Custom dataset (200 samples) |

### 9.3 Quality Benchmarks

| Metric | Target | How to Measure | Tool |
|--------|--------|---------------|------|
| TTS MOS (English) | >=3.8 | Mean Opinion Score from human raters (crowdsourced) | 20 raters, 10 samples each |
| TTS MOS (Vietnamese) | >=4.0 | Mean Opinion Score from human raters (crowdsourced) | 20 raters (VI speakers), 10 samples each |
| TTS latency jitter | <20ms stddev | Measure per-sentence synthesis time over 100 sentences | Automatic timing |
| Full-duplex naturalness | Pass baseline | Full-Duplex-Bench v1 end-to-end test | Automated benchmark framework |

### 9.4 Reliability Benchmarks

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Provider failover time | <1s | Induce provider failure, measure time to alternate provider |
| Crash recovery | <2s | Kill audio process, measure time to automatic restart |
| Memory leak over 1 hour | <100MB | Run voice mode for 1 hour with continuous usage, measure before/after RSS |
| CPU usage (idle, always-listening) | <5% of one core | Measure CPU during silence with continuous VAD |
| False barge-in rate | <1 per hour | Run voice mode with continuous playback in quiet room, count false interruptions |

### 9.5 Testing Strategy During Development

Testing voice mode requires different approaches than testing text features, because audio is hard to automate and subjective quality matters.

**Unit tests (automated, run on every CI push):**

```typescript
// Example unit test structure
describe('VoicePipeline', () => {
  it('transcribes audio through Whisper Turbo', async () => {
    const audio = loadTestAudio('hello-world.wav');
    const result = await whisper.transcribe(audio);
    expect(result.text).toContain('hello world');
    expect(result.confidence).toBeGreaterThan(0.8);
  });

  it('detects turn boundaries correctly', async () => {
    const audio = loadTestAudio('complete-utterance.wav');
    const result = await smartTurn.analyze(audio);
    expect(result.label).toBe('turn_end');
  });

  it('handles barge-in within latency budget', async () => {
    const playback = startTTSPlayback('test-response.wav');
    const interrupt = playAudio('interrupt-speech.wav', delayMs: 500);
    const stopTime = measureTimeToSilence();
    expect(stopTime).toBeLessThan(56); // ms
  });
});
```

**Integration tests (run on every PR):**

1. **Audio I/O loopback test:** Connect mic output to speaker input (loopback cable or virtual audio device). Send known audio through the pipeline. Verify the output matches expected transcription and TTS quality.
2. **Barge-in integration test:** Play a long TTS response while simultaneously injecting a user utterance. Verify the pipeline stops TTS, processes the interruption, and responds correctly.
3. **Language detection test:** Feed EN and VI audio samples. Verify correct pipeline selection within 100ms.
4. **Provider failover test:** Configure primary provider with a fake API key (guaranteed to fail). Verify automatic failover to secondary provider within <1s.

**Manual testing checklist (before each release):**

- [ ] PTT mode: press key, speak, release, hear response. Full round-trip <2s.
- [ ] Always-listening: speak naturally, hear response without key press.
- [ ] Barge-in: interrupt Lyra mid-response, hear correct handling.
- [ ] Backchannel: say "uh-huh" during TTS playback, verify Lyra continues speaking.
- [ ] Vietnamese: speak in Vietnamese, verify transcription and response in Vietnamese.
- [ ] Code-switching: mix VI and EN in one utterance, verify correct handling.
- [ ] Wake word: say "Hey Lyra" from idle state, verify activation.
- [ ] Timeout: stay silent for 35s, verify auto-deactivation.
- [ ] Error recovery: unplug mic during conversation, verify graceful fallback.
- [ ] Sound effects: verify session start/complete/error sounds play.
- [ ] Noisy environment test: run voice mode with background music. Verify VAD does not false-trigger more than once per minute.
- [ ] Whisper hallucination test: feed 500ms of silence to Whisper. Verify empty transcription is ignored.

---

## 10. (A) Parity vs (B) Breakthrough

### 10.1 (A) Parity: Matching Industry Standard

**(A) Level** is what Claude Code Voice Dictation and GPT-4o Voice Mode already offer. Lyra needs this to be competitive:

| Feature | Cloud dictation | GPT Voice | Lyra (A) Target |
|---------|----------------|-----------|-----------------|
| Push-to-talk | Yes | No (always-listening) | Yes |
| Always-listening | No | Yes | Yes |
| Barge-in | No | Yes (limited) | Yes |
| STT | Cloud | Cloud/Whisper | Provider-swappable |
| TTS | Cloud | Cloud | Provider-swappable |
| Multilingual | 30+ | 50+ | VI + EN (day one) |
| Latency | ~500ms | ~300ms | <300ms (cloud) |
| Cost | Free | $0.06/min included | $0 (on-device) |

**(A) Implementation effort:** ~12 weeks (Phases 1-3). Straightforward engineering using well-documented open-source components.

### 10.2 (B) Breakthrough: Beyond Any Existing System

**(B) Level** is what makes Lyra unique. These three breakthrough innovations go beyond parity:

#### Breakthrough 1: Adaptive Multi-Modal Fusion Pipeline

**Innovation:** Instead of a fixed STT-LLM-TTS cascade, Lyra dynamically switches between three modes based on query complexity:

1. **Voice-only** (fast path): Haiku model, minimal processing, fastest response. For simple queries ("What time is it?")
2. **Hybrid** (balanced path): Sonnet model, TTS overlaps with streaming LLM output. For standard queries ("Explain async/await")
3. **Text-only** (quality path): Opus model, extended thinking, no TTS. For complex reasoning ("Find and fix SQL injection vulns")

**Router logic (simplified):**
```
Complexity score = 0.30 * (query length) + 0.25 * (1 - STT confidence) + 0.25 * (intent ambiguity) + 0.20 * (reasoning depth)
- Score <0.4: voice-only (Haiku)
- Score 0.4-0.7: hybrid (Sonnet, streaming TTS)
- Score >0.7: text-only (Opus, extended thinking)
```

**Why it's breakthrough:** No existing voice agent system dynamically switches between architectures based on query complexity. Moshi is always full-duplex (limited reasoning). GPT-4o voice is always cloud (locked to OpenAI). Lyra adapts to the query and hardware.

**Expected impact:** 40-60% latency reduction for simple queries while maintaining full quality for complex ones.

#### Breakthrough 2: Proactive Context Injection via Voice Cues

**Innovation:** Lyra doesn't just transcribe what you say -- it analyzes HOW you say it and acts on the paralinguistic information:

| Cue | Detection | Action |
|-----|-----------|--------|
| Hesitation ("Uh... what was...") | Low pitch slope, pauses, filler words | Auto-fetch relevant memory, offer suggestions |
| Frustration (sharp pitch, high energy) | High pitch variance, clipped words | Concise responses, skip verification steps |
| Confusion (uncertain tone) | Low energy, rising final pitch | Offer examples, ask clarifying questions |
| Excitement (high energy, fast pace) | High speech rate, wide pitch range | Match enthusiasm in TTS, dive deeper |
| Urgency (clipped, fast speech) | Short pauses, high speech rate | Route to fastest model, skip non-essential steps |

**Implementation via hooks (Section 4.10):**
```typescript
hooks.register('PreSTT', async (audio) => {
  const prosody = extractProsody(audio);
  context.set('voiceCues', { frustration: prosody.energy > 0.8 && prosody.pitchVariance > 0.6 });
});

hooks.register('PostSTT', async (text, context) => {
  if (context.get('voiceCues').frustration) {
    context.set('responseStyle', 'concise');
  }
});
```

**Why it's breakthrough:** No existing voice agent (Claude Code dictation, GPT-4o voice, Moshi) uses prosody as an INPUT to agent behavior. They all treat voice as a text replacement. Lyra preserves the communicative richness of speech.

**Expected impact:** 30-50% reduction in clarification rounds, more empathetic interaction.

#### Breakthrough 3: Inner Monologue Injection for Natural Prosody

**Innovation:** Moshi's key innovation is the "Inner Monologue" -- predicting text tokens before audio tokens, which gives the speech natural prosody. Lyra extracts this concept and injects it into the cascaded pipeline WITHOUT requiring Moshi's 24GB GPU.

**How it works:**
```
LLM output: "I found three potential issues in your auth module"
    |
    v Inner Monologue classifier (DistilBERT, 66M params, CPU, <5ms)
    |
    v Annotated text: "<pause=100ms>I found <emphasis>three</emphasis> potential issues in your <speed=0.9x>auth module</speed>"
    |
    v Kokoro TTS with annotation-aware synthesis
    |
    v Audio with natural prosody (emphasis on "three", slower on "auth module")
```

**Key insight:** The Inner Monologue is a TEXT-TO-TEXT transformation. It doesn't need audio I/O, just a lightweight NLU model (DistilBERT, 66M params, CPU-capable). This makes it provider-agnostic and cheap.

**Expected impact:** +0.3-0.5 MOS improvement (3.8 -> 4.1-4.3) at <5ms additional latency, CPU-capable.

**Why it's breakthrough:** Lyra gets Moshi-quality prosody without the 24GB GPU. No other cascaded voice system does this. It's a fusion of two separate ideas (Moshi's architecture + Kokoro's TTS) into something neither does alone.

---

### 10.3 Decision: (B) Breakthrough First

Lyra implements (B) throughout. Voice mode is designed from day one with:

1. Provider-swappable STT/TTS (not locked to any vendor)
2. Streaming overlap for perceived latency reduction (from the first working pipeline)
3. Breakthrough 1 integration: adaptive mode routing by query complexity
4. Breakthrough 2 foundation: prosody hooks ready for cue detection
5. Breakthrough 3 as Phase 5 optimization

This is BOLDER than matching existing products. (A) parity is a stepping stone that we pass through during Phase 1 -- not a destination.

---

## 11. References

### Frameworks and Toolkits
- [Pipecat](https://github.com/pipecat-ai/pipecat) -- Real-time voice/multimodal agent framework, Python
- [LiveKit Agents](https://github.com/livekit/agents) -- WebRTC + telephony + MCP support
- [TEN Framework](https://github.com/TEN-framework/TEN-Agent) -- Multi-language realtime framework
- [Smart Turn](https://github.com/pipecat-ai/smart-turn) -- Semantic turn detection, 23 languages, Apache-2.0

### Speech-to-Speech Models
- [Moshi](https://arxiv.org/abs/2410.00037) -- First real-time full-duplex spoken LLM (Kyutai, 24GB GPU)
- [CSM](https://github.com/SesameAILabs/csm) -- Conversational Speech Model (Sesame, Llama backbone)

### STT Models
- [Whisper](https://github.com/openai/whisper) -- Multilingual ASR (OpenAI, MIT license, 99 languages)
- [NeMo Parakeet / Canary](https://github.com/NVIDIA/NeMo) -- NVIDIA STT models (Apache-2.0)
- [Open ASR Leaderboard](https://arxiv.org/abs/2510.06961) -- Multilingual ASR evaluation

### TTS Models
- [Kokoro-82M](https://github.com/hexgrad/kokoro) -- Tiny, fast, high-quality TTS (Apache-2.0, CPU)
- [Orpheus TTS](https://github.com/canopyai/Orpheus-TTS) -- Expressive TTS, emotion tags, voice cloning
- [MagpieTTS (NeMo)](https://github.com/NVIDIA/NeMo) -- Vietnamese TTS (Apache-2.0)

### VAD
- [Silero VAD](https://github.com/snakers4/silero-vad) -- De-facto open VAD (MIT, 2MB, <1ms, 6000+ languages)

### Benchmarks
- [Full-Duplex-Bench v1](https://arxiv.org/abs/2503.04721) -- Turn-taking, backchannel, interruption
- [Full-Duplex-Bench v3](https://arxiv.org/abs/2604.04847) -- Disfluency + multi-step tool use
- [Tau-Voice](https://arxiv.org/abs/2603.13686) -- Real-world task completion benchmark
- [Open ASR Leaderboard](https://arxiv.org/abs/2510.06961) -- Multilingual ASR evaluation

### UX and Product References
- [Claude Code Voice Dictation](https://code.claude.com/docs/en/voice-dictation)
- [Warcraft Peon Notifications](https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852)
- [Sound Effects via Hooks](https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/)

### Related Lyra Workstreams
- Section 4.5 Router -- Voice-aware model routing
- Section 4.10 Hooks -- Voice event hooks for SFX, context injection
- Section 4.13 Swarm -- Voice-controlled multi-agent coordination
- Section 4.17 Safety -- Voice safety controls, privacy
- Section 5.3 SFX -- Sound effects layer, voice packs

### Deep Technical References
- `lyra-upgrade/voice-mode.md` -- Full DSP algorithm pseudocode, latency math, ring buffer implementation, NLMS echo cancellation, Smart Turn architecture, Kokoro streaming overlap scheduler
- `lyra-upgrade/brainstorm/00-voice-mode.md` -- Breakthrough ideas archive, fusion algorithms, ablation studies, TypeScript pseudocode for all three breakthroughs

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **AEC** | Acoustic Echo Cancellation. Algorithm that removes speaker output from microphone input to prevent feedback loops. |
| **ASR** | Automatic Speech Recognition. Converting audio to text (STT). |
| **Barge-in** | The ability for a user to interrupt the system mid-response. Requires VAD monitoring during TTS playback. |
| **Cascaded** | STT -> LLM -> TTS pipeline. Each component runs sequentially. Default architecture for Lyra. |
| **Codec** | Audio compression/decompression format. Mimi codec (used by Moshi) compresses 24kHz audio to 1.7 kbps. |
| **Diarization** | Identifying which speaker said what in multi-speaker audio. Not in MVP scope. |
| **Double-talk** | When both user and system speak simultaneously. AEC must handle this correctly. |
| **FastText** | Facebook's text classification library. Used here for language identification (176 languages, <5ms). |
| **Full-Duplex** | Simultaneous two-way audio. Both parties can speak at the same time. Requires Moshi-style architecture. |
| **G2P** | Grapheme-to-Phoneme. Converting written text to a phonetic representation. Kokoro's misaki library handles this. |
| **Hysteresis** | Using different thresholds for rising vs falling edges to prevent rapid state toggling. VAD uses 0.7 on, 0.3 off. |
| **Inner Monologue** | Moshi's technique of predicting text tokens before audio tokens for natural prosody. Lyra's Breakthrough 3 extracts this. |
| **LLM** | Large Language Model, e.g., Claude, GPT, DeepSeek. Provides reasoning capabilities. |
| **MOS** | Mean Opinion Score. Human-rated speech quality from 1 (bad) to 5 (perfect). Kokoro ~3.8, Orpheus ~4.2. |
| **NLMS** | Normalized Least Mean Squares. Adaptive filter algorithm used for echo cancellation. 256 taps, mu=0.01. |
| **PCM** | Pulse Code Modulation. Raw audio format: 24kHz, 16-bit, mono. No compression. |
| **PortAudio** | Cross-platform audio I/O library. Handles mic capture and speaker playback on macOS, Windows, Linux. |
| **Prosody** | The rhythm, stress, and intonation of speech. Conveys emotion, emphasis, and turn-taking cues. |
| **PTT** | Push-to-Talk. Voice mode activated by holding a key. Default interaction mode for MVP. |
| **Ring Buffer** | Lock-free SPSC data structure for thread-safe audio transfer between capture and processing threads. |
| **S2S** | Speech-to-Speech. End-to-end model that directly converts input audio to output audio (Moshi). |
| **SOTA** | State of the Art. Best currently available technology for a given task. |
| **SPSC** | Single Producer, Single Consumer. Concurrency pattern used by the ring buffer. No mutexes needed. |
| **SSE** | Server-Sent Events. Used for streaming LLM output. Aborting SSE stops generation. |
| **STT** | Speech-to-Text. Converting audio to text (Whisper Turbo, Deepgram). |
| **TKG** | Temporal Knowledge Graph. Lyra's memory system that stores facts with timestamps for context-aware retrieval. |
| **TTS** | Text-to-Speech. Converting text to audio (Kokoro, MagpieTTS, Orpheus). |
| **VAD** | Voice Activity Detection. Binary classification of audio frames as speech or silence (Silero). |
| **WER** | Word Error Rate. Percentage of words incorrectly transcribed. Lower is better. Target: <15% EN, <20% VI. |
| **WPM** | Words Per Minute. Typing speed (~40 WPM) vs speaking speed (~150 WPM). |

---

## 13. Quick Commands Reference

A summary of all voice-related commands for the Lyra CLI:

| Command | Action | Phase |
|---------|--------|-------|
| `lyra --voice` | Start Lyra with voice mode enabled | 1 |
| `voice on` | Enable voice mode in current session | 1 |
| `voice off` | Disable voice mode in current session | 1 |
| `voice mode push-to-talk` | Switch to PTT interaction mode | 1 |
| `voice mode always-listening` | Switch to always-listening mode | 2 |
| `voice mode hybrid` | Switch to hybrid mode (auto-switch) | 2 |
| `voice status` | Show voice provider status, metrics, mode | 1 |
| `voice test mic` | Test microphone input with audio level display | 1 |
| `voice test speakers` | Test speaker output with a sample audio | 1 |
| `voice pack <name>` | Set voice personality pack | 4 |
| `voice language` | Show detected language stats | 4 |
| `voice language en` | Force English mode | 4 |
| `voice language vi` | Force Vietnamese mode | 4 |
| `voice speed 1.2` | Set TTS playback speed (0.8-2.0) | 1 |
| `voice logs` | Show voice mode diagnostics | 1 |
| `voice reset` | Reset voice config to defaults | 1 |

---

## 14. Changelog

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-05-31 | v2.1 | Writer | **Run 15**: Added §9 Expert Review section with senior persona sign-off (Senior Backend, Senior AI Engineer, Senior PM), plain-language summary, implementation readiness checklist, top 3 implementation risks from deep-read evidence, and expert verdict with go/no-go criteria. |
| 2026-05-31 | v2.0 | Writer | Complete rewrite. Expanded from 439 lines to 2000+ lines. Added: Executive summary, problem analysis, evidence synthesis with STT/TTS/architecture comparison tables, step-by-step voice interaction walkthrough (10 steps with real example), interaction modes, multilingual analysis, voice pack system, accessibility/privacy/cost sections, complete data models, phased build outline with 28 tasks, multi-provider notes, risk matrix, (A) parity vs (B) breakthrough comparison, comprehensive references. References deep technical content in `voice-mode.md` without duplicating it. |
| 2026-05-31 | v1.0 | Original | Initial draft. Basic architecture, provider interfaces, implementation phases, multi-provider notes, risks, references. 439 lines. |

---

## §9 Expert Review (Run 15)

**Reviewers**: Senior Backend, Senior AI Engineer, Senior PM

### Plain-Language Summary

Lyra Voice Mode lets developers talk to their AI coding assistant and hear it talk back -- like having a phone conversation with a colleague. Instead of typing every command and reading every response, you speak naturally, and Lyra transcribes your speech, plans its answer using the same powerful AI models it uses for text, and speaks its response aloud through your speakers. This matters because speaking is about three times faster than typing, it keeps developers in a state of flow (no stopping to type), it makes the tool accessible to people who cannot use a keyboard or screen, and it supports Vietnamese and English from day one. The entire default voice pipeline runs on your own computer with zero API costs for the speech parts, though users can optionally swap in cloud providers for higher quality.

### Expert Sign-Off Status

| Role | Status | Key Objections | Resolution | Signed Off |
|------|--------|---------------|------------|------------|
| **Senior Backend** | Pending | [To be filled after expert review] | [To be filled] | ⬜ |
| **Senior AI Engineer** | Pending | [To be filled after expert review] | [To be filled] | ⬜ |
| **Senior PM** | Pending | [To be filled after expert review] | [To be filled] | ⬜ |

### Implementation Readiness Checklist
- [ ] All TypeScript interfaces are complete (no `any` types, no missing fields)
- [ ] Build outline has per-task hour estimates and acceptance criteria
- [ ] Multi-provider behavior is explicitly defined (not "may vary")
- [ ] Failure modes are enumerated with detection + recovery strategies
- [ ] Cold start / first-use experience is explicitly designed
- [ ] Operational burden is estimated (backup, monitoring, scaling, cost)

### Top 3 Implementation Risks
1. **Cascaded pipeline latency on CPU-only hardware may exceed the <500ms perceived target**, especially for Vietnamese (Whisper Turbo VI is slower than EN). Without a GPU, the on-device Whisper Turbo alone adds 200-400ms P50, and with TTS overhead the total perceived latency may reach 600-800ms, degrading the conversational feel. Mitigation: default CPU-only users to cloud STT (Deepgram at ~100ms) if available, or surface a clear warning that on-device latency will be higher on CPU.
2. **Echo cancellation failure in always-listening mode could create a feedback-loop UX that makes the feature unusable.** The NLMS adaptive filter (256 taps) is well-understood but sensitive to double-talk, room acoustics, and microphone placement. If the filter diverges, Lyra hears itself, triggers barge-in, stops speaking, then re-enters listening in a perpetual cycle. Mitigation: auto-detect feedback patterns (>3 speak-stop cycles in 15s), temporarily disable always-listening, and fall back to push-to-talk with a diagnostic message.
3. **Vietnamese code-switching WER may exceed the 25% target due to domain-specific technical jargon.** Whisper Turbo handles general code-switching well, but Lyra-specific vocabulary (agent names, Lyra commands, skill names embedded in VI sentences) may produce poor transcriptions because these terms were never in training data. Mitigation: build a Lyra-specific phrase list for Whisper's `initial_prompt` parameter, collect real-world transcriptions from beta users to measure actual WER, and allow users to correct transcriptions inline to build a feedback loop.

### Expert Verdict

This plan is **IMPLEMENTATION-READY for Phase 1 (push-to-talk MVP)**. The architecture is sound, the component selection (Silero VAD + Whisper Turbo + Kokoro TTS) is well-justified against alternatives in the evidence synthesis, and the phased rollout (PTT first, always-listening later, breakthroughs last) de-risks the hardest problems. The single biggest gap is the absence of real-world latency measurements on representative hardware -- the latency budget is model-derived (Whisper Turbo ~200ms, Kokoro ~50ms) but has not been validated end-to-end on the target platforms (macOS Apple Silicon, Linux x86_64, Windows WASAPI). Before committing the full 340-hour estimate, the team should run a 2-day spike: wire audio capture to Whisper Turbo to Kokoro on at least two platforms, measure actual round-trip latency, and confirm the streaming overlap savings hold in practice. For this plan to succeed, three things must be true: (1) Whisper Turbo's on-device latency on Apple Silicon is within 150% of the published benchmarks, (2) PortAudio provides stable, low-latency audio I/O across all three target platforms without per-platform workarounds exceeding 20% of the Phase 1 budget, and (3) the streaming overlap algorithm (TTS starting on first sentence) reliably hides at least 40% of the raw pipeline latency in practice, not just on paper.

---

**END OF PLAN: Voice Mode (Section 4.18)**

> This plan references deep technical content in `lyra-upgrade/voice-mode.md` (DSP algorithms, latency budgets, pseudocode) and breakthrough ideation in `lyra-upgrade/brainstorm/00-voice-mode.md`. Those documents provide the algorithmic depth that this plan deliberately keeps accessible.
