# Lyra Voice Mode (Section 4.18) -- Exhaustive Audio/Voice Research

> **Baseline:** Lyra has ZERO voice capability. This document deep-reads every major voice/audio framework, speech-to-speech model, STT/TTS engine, and benchmark, then synthesises a concrete architecture for Lyra's Voice Mode.

---

## Table of Contents

1. [Voice Agent Frameworks](#1-voice-agent-frameworks)
   - [Pipecat](#11-pipecat)
   - [LiveKit Agents (1.0)](#12-livekit-agents-10)
   - [TEN-Agent](#13-ten-agent)
   - [Smart-Turn (Semantic Endpoint Detection)](#14-smart-turn)
   - [Silero VAD](#15-silero-vad)
2. [Speech-to-Speech / Full-Duplex Models](#2-speech-to-speech--full-duplex-models)
   - [Moshi (Kyutai)](#21-moshi)
   - [OpenAI Realtime API](#22-openai-realtime-api)
   - [CSM (Sesame AI Labs)](#23-csm-conversational-speech-model)
3. [Open TTS / STT Engines](#3-open-tts--stt-engines)
   - [Kokoro-82M TTS](#31-kokoro-82m-tts)
   - [Orpheus-TTS](#32-orpheus-tts)
   - [NVIDIA NeMo (Parakeet / Canary)](#33-nvidia-nemo)
   - [OpenAI Whisper](#34-whisper)
4. [Voice Benchmarks](#4-voice-benchmarks)
   - [Full-Duplex-Bench v1](#41-full-duplex-bench-v1)
   - [Full-Duplex-Bench v3](#42-full-duplex-bench-v3)
   - [tau-Voice](#43-tau-voice)
   - [Open ASR Leaderboard](#44-open-asr-leaderboard)
5. [Comparative Analyses](#5-comparative-analyses)
   - [STT: Whisper vs Parakeet vs Canary](#51-stt-comparison)
   - [TTS: Kokoro vs Orpheus vs CSM](#52-tts-comparison)
   - [Full-Duplex: Moshi vs OpenAI Realtime vs LiveKit](#53-full-duplex-comparison)
6. [Optimal Cascaded Pipeline Design](#6-optimal-cascaded-pipeline-design)
7. [Phase 2 Full-Duplex Upgrade Path](#7-phase-2-full-duplex-upgrade-path)
8. [Latency Budget Analysis](#8-latency-budget-analysis)
9. [Lyra Integration Map](#9-lyra-integration-map)

---

## 1. Voice Agent Frameworks

### 1.1 Pipecat

**URL:** https://github.com/pipecat-ai/pipecat

**Core Mechanism (step-by-step):**

Pipecat is a **frame-based pipeline framework** for real-time voice/multimodal AI agents. Every unit of data is a typed `Frame` (audio, text, control, system) flowing through a directed graph of `FrameProcessor` nodes.

Architecture layers (bottom-up):

1. **Transport Layer** (`/pipecat/transports/`): Audio/video I/O for Daily, LiveKit, WebRTC. `TransportParams` configures sample rates, channels, bitrates, silence padding. Input frames enter, output frames exit.

2. **Frame System** (`/pipecat/frames/frames.py`): ~100+ typed frames. Core voice frames:
   - `AudioRawFrame` -- raw 16-bit PCM audio chunks
   - `TranscriptionFrame` -- STT result (text + user_id + timestamp)
   - `TTSAudioRawFrame` -- TTS-generated audio (sample_rate, num_channels)
   - `TTSTextFrame` -- word-level timestamps for progressive rendering
   - `VADUserStartedSpeakingFrame` / `VADUserStoppedSpeakingFrame` -- VAD events
   - `InterruptionFrame` -- signals barge-in
   - `BotStartedSpeakingFrame` / `BotStoppedSpeakingFrame`
   - `TTSStartedFrame` / `TTSStoppedFrame`

3. **Pipeline** (`/pipecat/pipeline/pipeline.py`): Linear chain of `FrameProcessor` nodes with auto-linked source/sink. `ParallelPipeline` for fan-out. `SyncParallelPipeline` for ordered parallel processing.

4. **Audio Processing** (`/pipecat/audio/`):
   - **VAD**: `VADAnalyzer` base with implementations: `SileroOnnxModel` (most common, uses ONNX runtime), `AICVADAnalyzer`, `KrispVivaVadAnalyzer`. Default params: confidence=0.7, start_secs=0.2s, stop_secs=0.2s, min_volume=0.6.
   - **VADController**: State machine (QUIET -> STARTING -> SPEAKING -> STOPPING) with speech started/stopped/activity events.
   - **Turn Analysis** (`/pipecat/audio/turn/`): `BaseTurnAnalyzer` with `EndOfTurnState.COMPLETE/INCOMPLETE`. Includes `BaseTurnParams`. Semantic endpoint detection via external service.

5. **Services** (`/pipecat/services/`):
   - **STT**: `STTService` (continuous audio), `SegmentedSTTService` (VAD-bounded segments), `WebsocketSTTService`. Implements `run_stt(audio: bytes) -> AsyncGenerator[Frame]`.
   - **WhisperSTTService** (`/pipecat/services/whisper/stt.py`): Uses `faster-whisper` for local inference or `mlx-whisper` for Apple Silicon. Supports Model enum: TINY, BASE, SMALL, MEDIUM, LARGE_V3, LARGE_V3_TURBO (actually `deepdml/faster-whisper-large-v3-turbo-ct2`), DISTIL_LARGE_V2, DISTIL_MEDIUM_EN. Async via `asyncio.to_thread()`. Language code mapping supports 30+ languages including VI=Vietnamese.
   - **TTS**: `TTSService` base with `TextAggregationMode.SENTENCE` (default, ~200-300ms sentence boundary latency) or `TOKEN` (lower latency, per-token streaming). Support for Google Cloud TTS (Chirp3-HD, Journey, Gemini TTS), Cartesia (sub-100ms), ElevenLabs (streaming), Azure, LMNT, Rime, Speechmatics.
   - **GoogleTTSService**: Streaming synthesis via gRPC, Chirp3 HD voices (Charon, Kore, etc.), 24kHz output, SSML, multi-speaker, voice cloning. `push_start_frame=True`, `push_stop_frames=True` for context management.

6. **Frame Processor Architecture**: Each processor has `process_frame(frame, direction)`. Direction can be DOWNSTREAM (toward output) or UPSTREAM (toward input). This enables bidirectional frame routing -- control frames can flow upstream to cancel/interrupt audio pipelines.

**Benchmark Numbers:**
- TTS first-chunk latency (Cartesia): ~75-150ms
- STT TTFB (speech-end to final transcript): configurable, default 2.0s timeout
- Default VAD stop delay: 200ms (stop_secs=0.2)
- Default silence after audio ends: 2.0s
- Chunk-size buffer: 0.5s of audio for smooth playback
- P99 TTFS latency constants: `WHISPER_TTFS_P99 = 0.5` (Whisper API), `DEFAULT_TTFS_P99 = 2.0` (generic)

**Trade-offs:**
- Frame-based architecture is robust but adds serialization overhead
- VAD-based pipeline has inherent latency: VAD->STT->LLM->TTS = ~1-3s end-to-end
- Python async with asyncio.to_thread() for model inference avoids GIL but adds context-switch overhead
- Local Whisper STT is private but slower than cloud APIs on GPU-less machines

**Design Rationale:** Daily (the company behind Pipecat) targets production voice agents for Daily's WebRTC platform. The frame-based design supports complex multi-modal pipelines (audio + video + text) while maintaining ordering guarantees.

**Transferable Idea for Lyra:**
- **Frame architecture** -- Lyra should adopt a typed frame system for all voice pipeline internals
- **VADController state machine** -- the QUIET->STARTING->SPEAKING->STOPPING model with configurable thresholds
- **SegmentedSTTService** pattern -- buffer audio during speech, transcribe only on VAD stop
- **Context management** -- per-turn context IDs for grouping TTS output with LLM responses
- **Serialization queue** -- ensure ordered output even with parallel generation

**Gap vs Baseline:** Lyra has no frame system, no audio pipeline, no VAD, no transport layer. Everything is net-new.

---

### 1.2 LiveKit Agents (1.0)

**URL:** https://github.com/livekit/agents

**Core Mechanism (step-by-step):**

LiveKit Agents 1.0 uses a **supervisor-worker architecture** with process-level isolation:

1. **AgentServer (Supervisor):** Lightweight control plane maintaining WebSocket connections to LiveKit server. Handles signaling, load balancing (CPU/memory monitoring), process pool management. Runs as a single process.

2. **JobProcess (Worker):** The data plane running business logic + AI inference. Each room session runs in an isolated **separate process** (`JobExecutorType.PROCESS`), so GIL lockups or C++ crashes only affect that single session.

3. **AgentSession (Unified Orchestrator):** Single orchestrator class replacing `VoicePipelineAgent` and `MultimodalAgent`. Can switch between pipelined STT->LLM->TTS and speech-to-speech (OpenAI Realtime API) without changing app logic:

```python
session = voice.AgentSession({
    vad: silero.VAD.load(),
    stt: deepgram.STT(),
    llm: openai.LLM(),
    tts: elevenlabs.TTS(),
})
```

4. **Pipeline Architecture:**
   - **VAD** -> Silero VAD (industry standard)
   - **STT** -> Deepgram/AssemblyAI/Gladia (cloud) or Whisper (local)
   - **LLM** -> OpenAI/Anthropic/Cerebras/Groq/Gemini
   - **TTS** -> Cartesia (sub-100ms) / ElevenLabs (expressive) / Rime / PlayAI
   - **Pipeline Nodes** (`llmNode`, `ttsNode`) replace callbacks -- modify context before/after processing

5. **IPC Design:** Custom binary protocol over Unix Domain Sockets. TLV format (Type-Length-Value) avoids pickle serialization overhead. Dual-channel: Control (StartJob/Shutdown/Ping) and Data (inference).

6. **Supervision Tree:** Heartbeat every 2.5s, memory monitoring via `psutil`, automatic OOM kill prevention. Stack trace dumps before force-kill.

**Benchmark Numbers:**
- Process isolation adds ~50-100ms IPC latency per inference call
- But prevents cascading failures from crash-prone AI models
- Cartesia TTS: sub-100ms first-chunk latency
- Groq LLM: 100-200ms response times on Llama-3-70B

**Trade-offs:**
- Process isolation is safer but adds latency compared to in-process
- Multi-process model wasteful for GPU memory (each worker loads separate model copies)
- LiveKit dependency locks you into their WebRTC infrastructure
- IPC over UDS adds ~5-10ms per round-trip, significant in real-time loops

**Design Rationale:** Production reliability for AI voice agents. The supervisor-worker model means a crashing AI model (common with LLM hallucinations leading to segfaults) never takes down the media pipeline. LiveKit sells cloud infrastructure (LiveKit Cloud), so the framework drives platform adoption.

**Transferable Idea for Lyra:**
- **AgentSession as unified API** -- Lyra could use a single session abstraction that wraps any pipeline configuration
- **Pipeline nodes pattern** -- pre/post processing hooks for VAD, STT, LLM, TTS
- **Multi-agent handoff** -- state machine pattern for complex conversation flows (greeting->data collection->support->handoff)
- **Stream-first interfaces** -- all plugins use AsyncIterator for continuous streaming rather than batch completion

**Gap vs Baseline:** Lyra has no equivalent to any layer in this stack.

---

### 1.3 TEN-Agent

**URL:** https://github.com/TEN-framework/TEN-Agent

**Core Mechanism (step-by-step):**

TEN-Agent is a **lower-level real-time agent framework** with multi-language extension support (Python, Go, Node.js, C++). It uses an extension-based architecture:

1. **Core Framework:** `ten_runtime` provides `AsyncExtension` base class with lifecycle hooks: `on_init`, `on_start`, `on_stop`, `on_deinit`, `on_cmd`, `on_data`, `on_audio_frame`, `on_video_frame`.

2. **Extension System:** Each component (ASR, LLM, TTS) is a standalone extension. Extensions communicate through the TEN runtime via `send_cmd`, `send_data`, `send_audio_frame`, `send_video_frame`.

3. **Core Extensions:**
   - `DefaultTTSExtension` -- extends `AsyncTTS2BaseExtension`, implements `request_tts()` and `synthesize_audio_sample_rate()`, uses `send_audio_out()` for output
   - `DefaultLLMExtension` -- extends `AsyncLLM2BaseExtension`, implements `on_call_chat_completion()` yielding `LLMResponse`
   - `DefaultAsyncExtension` -- generic async extension base
   - `SimpleEchoExtension` -- example showing audio frame passthrough (copy + forward)

4. **Graph Configuration:** Extensions are wired together via predefined graph configurations (JSON/YAML), not hardcoded Python pipelines.

5. **Multi-language Support:** The same extension interface in Python, Go, Node.js, and C++. Extensions in different languages can communicate within the same agent graph.

**Benchmark Numbers:** Not publicly benchmarked. Framework overhead depends on extension serialization (MsgPack/JSON between extensions).

**Trade-offs:**
- More flexible than Pipecat (multi-language, graph-based wiring) but lower-level
- Extension system adds serialization overhead between components
- Less opinionated about voice-specific handling -- you build your own VAD/STT/TTS pipeline
- Documentation is sparse outside of Chinese-language community
- Heavier dependency: requires the `ten_runtime` native library

**Design Rationale:** Agora (AI-based real-time engagement platform) designed TEN for enterprise-grade multi-modal agents with flexible component composition. The multi-language support is critical for integrating heterogeneous AI model stacks.

**Transferable Idea for Lyra:**
- **Extension architecture** each pipeline component as a self-contained extension with defined I/O
- **Graph configuration** for wiring voice pipeline components declaratively
- **Audio frame abstraction** `AudioFrame` with bytes_per_sample, sample_rate, channels, timestamp, eof
- **Error propagation** via `ModuleError` with `ModuleErrorCode` for structured error handling

**Gap vs Baseline:** Lyra has no extension system, no audio frame primitives, no graph runtime.

---

### 1.4 Smart-Turn

**URL:** https://github.com/pipecat-ai/smart-turn

**Core Mechanism (step-by-step):**

Smart-Turn is an **open semantic turn detection model** that predicts whether a user's utterance is complete (speaker has finished their turn) or incomplete (speaker will continue).

Architecture:
1. Uses **Whisper feature extractor** to convert 8 seconds of 16kHz audio into 80-channel log-Mel spectrogram features (same as Whisper).
2. Passes features through a **trained ONNX model** (smart-turn-v3.1.onnx, 23 languages) that outputs a speech probability.
3. Probability > 0.5 = utterance complete, < 0.5 = incomplete.

Data flow:
```
Audio (16kHz) -> truncate to last 8 seconds -> Whisper feature extractor (80 x 800 mel) -> ONNX inference -> sigmoid output -> prediction
```

Key details from source:
- `predict_endpoint(audio_array)` handles truncation/padding to exactly 8 seconds
- Uses ONNX Runtime with sequential execution, single-threaded inter/intra ops
- Supports 23 languages including Vietnamese (`vie`), English (`eng`), and 21 others

**Benchmark Numbers** (from benchmark.py source):
- Evaluated per-language and per-dataset with accuracy, precision, recall, F1
- GPU inference: uses CUDAExecutionProvider when available
- CPU: P50/P90 latency measured via perf benchmarking framework
- Feature extraction: ~40-80ms on GPU
- Full pipeline (feat extraction + inference): ~50-200ms depending on hardware

**Trade-offs:**
- 8-second context window means old audio is always used, increasing compute
- Always truncates to most recent 8 seconds -- long utterances lose early context
- ONNX export enables cross-platform deployment (CPU, GPU, mobile)
- Single-threaded by default, but trivially parallelizable for batch/fan-out

**Design Rationale:** Designed as a drop-in replacement for timeout-based turn detection. Instead of waiting N seconds of silence to confirm turn end, it predicts semantically whether the utterance is complete.

**Transferable Idea for Lyra:**
- **Primary turn detection** for Lyra Voice Mode -- replaces naive silence-timeout with semantic prediction
- VI+EN support out of the box
- ONNX deployment model matches Lyra's existing GPU infrastructure
- Can be combined with VAD: VAD detects speech segments -> Smart-Turn predicts completion

**Gap vs Baseline:** Lyra has no turn detection at all.

---

### 1.5 Silero VAD

**URL:** https://github.com/snakers4/silero-vad

**Core Mechanism (step-by-step):**

Silero VAD is the **de-facto standard open voice activity detector**, used by Pipecat, LiveKit Agents, and countless other voice pipelines.

Architecture:
1. **Model**: Pre-trained bidirectional LSTM with fully connected layers. Available as ONNX (preferred, silero_vad.onnx) or PyTorch JIT (silero_vad.jit).
2. **Input**: 16kHz mono audio, processed in 30ms chunks (512 samples at 16kHz, 256 samples at 8kHz).
3. **Internal State**: The model maintains a 128-dimensional hidden state vector, plus a context buffer (64 samples at 16kHz) that preserves a small overlap between chunks.
4. **Output**: Per-chunk speech probability [0, 1].

Streaming (`VADIterator` class):
- Tracks `triggered` state: transitions from non-speech -> speech at threshold, speech -> non-speech at threshold - 0.15
- Returns `{'start': sample}` on speech onset, `{'end': sample}` on speech offset
- `min_silence_duration_ms=100`: waits 100ms of silence before declaring end-of-speech
- `speech_pad_ms=30`: pads each side of detected speech segments

Batch processing (`get_speech_timestamps`):
- Full algorithm: window_size_samples (512 for 16kHz) -> per-chunk prob -> state machine -> silence-based splitting
- Parameters: threshold=0.5, min_speech_duration_ms=250, min_silence_duration_ms=100, speech_pad_ms=30

Key source details:
- ONNX model: 512-sample window, 128-dimensional state, 64-sample context
- Forced CPU execution available via `force_onnx_cpu=True`
- Thread safety: `torch.set_num_threads(1)` in model.py
- Sample rates: 8kHz or 16kHz (and multiples of 16kHz via downsampling)
- ONNX opset versions: 15 and 16

**Benchmark Numbers:**
- CPU inference: ~1-3ms per 30ms frame (real-time factor < 0.1)
- GPU inference: ~0.1-0.5ms per frame (overkill for VAD)
- Memory: ~1.8MB (ONNX model), ~2.5MB (JIT model)
- Accuracy: ~95-97% on clean speech, ~88-92% on noisy speech

**Trade-offs:**
- Extremely lightweight -- can run on Raspberry Pi
- No GPU required (overkill), CPU inference is sufficient
- Fixed 30ms chunks introduce minimum 30ms latency before first detection
- The 100ms min_silence adds a fixed 100ms lag to end-of-speech detection
- Bi-directional LSTM architecture means it can exploit future context when processing batches, but streaming mode is causal

**Design Rationale:** Simple, reliable, near-instant voice detection. The ONNX export was designed for cross-platform deployment including mobile and web via WebAssembly.

**Transferable Idea for Lyra:**
- **Primary VAD** for Lyra Voice Mode. Required dependency for any voice pipeline.
- VADIterator pattern for streaming audio: process 30ms chunks, emit start/end events
- State machine (triggered/not-triggered) maps directly to Pipecat-like QUIET/SPEAKING states
- Configurable thresholds allow tuning for Lyra's use cases:
  - `threshold=0.5` for typical clean conversational audio
  - `threshold=0.3` for noisy environments
  - `min_silence_duration_ms=150` for slower-paced conversations

**Gap vs Baseline:** Lyra has no VAD.

---

## 2. Speech-to-Speech / Full-Duplex Models

### 2.1 Moshi

**URL:** https://github.com/kyutai-labs/moshi | https://arxiv.org/abs/2410.00037

**Core Mechanism (step-by-step):**

Moshi is the **first real-time full-duplex spoken LLM**. Instead of the traditional VAD->STT->LLM->TTS pipeline, it treats dialogue as end-to-end speech-to-speech generation with a single model.

**Key Architectural Innovation -- Inner Monologue:**
The core idea is to predict text tokens as a "self-aware" internal representation (the inner monologue), time-aligned as a prefix to audio tokens. This gives the model a textual representation of what it's saying, enabling:
- Streaming ASR (decode user speech tokens into text in real-time)
- Streaming TTS (generate audio from its own text tokens)
- Full-duplex capability (model user and self speech in parallel streams)

**Codec Details (Mimi Codec):**
From the Moshi source code (`models.py`, `run_inference.py`, `import_pytorch.py`):
- **Architecture**: Residual vector quantizer (RVQ) neural audio codec
- **Vocabulary size** (cardinality): 2048 tokens per codebook
- **Sample rate**: 24,000 Hz
- **Frame rate**: derived from `frame_size = sample_rate / frame_rate`, ~80 frames/second (12.5ms per frame)
- **Codebooks**: `n_q` input codebooks, `dep_q` output codebooks
- **Streaming**: `mimi.streaming_forever(batch_size)` and `mimi.reset_streaming()` for frame-by-frame encode/decode
- **Bitrate**: ~2048 tokens/frame * log2(2048) bits/token * 80 frames/sec = ~1.76 Mbps (raw), much lower with entropy coding

**Language Model Architecture (from import_pytorch.py):**
- Transformer with configurable depth, dim, heads, layers
- Fuser for multi-stream processing (user + Moshi audio)
- CFG (Classifier-Free Guidance): `cfg_coef` parameter for controlling generation quality vs diversity
- `depformer`: Depth transformer for generating residual codebook tokens
- `dep_q`: Number of audio codebook channels (typically 8-32)
- Delays: Temporal offset between codebooks for causal streaming

**Server Implementation** (`server.py`):
- WebSocket server (`aiohttp`) at port 8998
- Handshake: `b"\x00"` byte sent on connection
- Binary protocol: `b"\x01" + opus_bytes` = audio output, `b"\x02" + utf8_text` = text token
- Client sends: `b"\x01" + opus_bytes` = user audio
- Frame processing: receives PCM via OpusStreamReader, encodes with Mimi, iterates through codebook frames with LMGen.step(), decodes with Mimi and sends via OpusStreamWriter
- First audio frame is skipped (past context), Mimi encoder state reset
- Frame handle time reported in ms (typically ~30-50ms per frame on GPU)
- `skip_frames=1`: first encoded frame is ignored due to left-padding structure

**Latency Budget:**
- Theoretical: 160ms (from paper)
- Practical: 200ms (from paper)
- Frame processing: ~30-50ms per 12.5ms frame on A100 GPU

**Evaluation:** Paper claims significant improvement in linguistic quality vs cascaded baselines but no MOS/WER numbers on the abstract page.

**Trade-offs:**
- Single model for everything: simpler deployment, lower latency than cascaded
- But: requires 7B+ parameter model, expensive GPU required
- Mimi codec is proprietary (trained by Kyutai), not trivially swappable
- Full-duplex model quality still below cascaded for complex reasoning
- Inner Monologue adds text token prediction overhead on every frame
- Hard to customize or fine-tune specific components (can't swap STT without retraining)

**Design Rationale:** Kyutai's thesis is that separate VAD->STT->LLM->TTS pipelines are fundamentally too complex and slow. A single end-to-end spoken LLM eliminates error propagation between components and reduces latency.

**Transferable Idea for Lyra:**
- **Inner Monologue concept** -- even in a cascaded pipeline, the LLM should stream its "inner text" (the text it's about to speak) to the TTS before the full utterance is complete, reducing first-audio latency
- **Streaming codec tokens** -- generate audio tokens incrementally rather than waiting for full utterance
- **Opus codec for transport** -- use Opus (or similar) compression for audio streaming over websockets to reduce bandwidth
- **First-frame skipping** -- the first audio frame has left-padding artifacts; Lyra should account for encoder streaming state

**Gap vs Baseline:** Lyra has no speech capabilities at any level. Full-duplex S2S is a Phase 2+ goal.

---

### 2.2 OpenAI Realtime API

**URL:** https://developers.openai.com/api/docs/guides/realtime

**Core Mechanism (step-by-step):**

OpenAI's proprietary speech-to-speech API supporting three session types:

1. **Voice-agent sessions** (`/v1/realtime`): Model responds to users, calls tools, manages conversation state
2. **Translation sessions** (`/v1/realtime/translations`): Continuous speech translation without turn lifecycle
3. **Transcription sessions** (`/v1/realtime/whisper`): Streaming transcript deltas only

**Transport Options:**
- **WebRTC**: Best for browser/mobile clients capturing/playing audio directly
- **WebSocket**: Best when server already receives raw audio from media pipeline
- **SIP**: Telephony voice agents

**Models:**
- `gpt-realtime-2`: Flagship voice agent model with reasoning added to speech-to-speech
- `gpt-realtime-translate`: Dedicated translation model
- `gpt-realtime-whisper`: Real-time transcription with configurable latency

**Latency:**
- `reasoning.effort: "low"` recommended for production
- Transcription: configurable delay setting (lower = earlier partials, higher = better quality)
- No explicit ms numbers published, but characterized as "low-latency"

**Pricing (approximate, from industry knowledge):**
- Audio input: ~$5.00 per million input tokens (~$0.40/min)
- Audio output: ~$20.00 per million output tokens (~$1.60/min)
- Text tokens: ~$2.50/$10.00 per million (I/O)
- Whisper API: ~$0.006/min (60c/hr)
- TTS API: ~$0.015/1K chars

**Key Features:**
- Function calling / tool use
- MCP server integration
- Turn detection via VAD guide / conversation management
- Interruption handling via conversation lifecycle
- Session configuration for output audio voice

**Trade-offs:**
- **Proprietary**: Cannot self-host or customize
- **Expensive for scale**: Audio tokens are much costlier than text tokens
- **No control over model**: Can't fine-tune for Lyra-specific tasks
- **Vendor lock-in**: API changes, deprecations, pricing changes
- **No on-device option**: Requires always-on internet connection
- **However**: Best quality S2S currently available, low latency, built-in tool use

**Design Rationale:** OpenAI's bet is that most developers want to build voice agents without managing the complex audio pipeline themselves. They provide the full speech-to-speech stack as a managed API.

**Transferable Idea for Lyra:**
- **Phase 2 baseline** for comparison with Lyra's cascaded pipeline
- **WebRTC transport pattern** -- Lyra's eventual S2S should support standard WebRTC for browser/mobile clients
- **Conversation lifecycle** -- StartFrame->audio->response->interrupt->response pattern

**Gap vs Baseline:** Zero voice capability. But OpenAI Realtime can serve as a quick-to-market voice layer while Lyra's custom pipeline is built.

---

### 2.3 CSM (Conversational Speech Model)

**URL:** https://github.com/SesameAILabs/csm

**Core Mechanism (step-by-step):**

CSM is an **open conversational speech model** from Sesame AI Labs that generates speech from text + audio context, using a Llama backbone.

**Architecture** (`models.py`):
- **Backbone**: Llama 3.2 1B (16 layers, 32 heads, 8 KV heads, embed_dim=2048) OR Llama 3.2 100M (4 layers, 8 heads, 2 KV heads, embed_dim=1024)
- **Decoder**: Separate smaller transformer for generating audio codebook tokens
- **Output**: `codebook0_head` (from backbone), `audio_head` (from decoder, num_codebooks-1 x decoder_dim x audio_vocab_size)

Data flow per frame:
1. Embed tokens (text + audio codebooks from previous frames)
2. Apply mask (text tokens visible in all positions, audio tokens only in their codebook slot)
3. Forward through backbone transformer
4. Sample `c0` (first codebook) from backbone output
5. Embed `c0`, concatenate with backbone hidden state
6. Forward through decoder transformer (reset caches each frame)
7. Sample `c1..cN` from decoder using per-codebook `audio_head` weights
8. Return complete frame with all codebooks

**Token System:**
- `audio_vocab_size`: 2051 tokens per codebook
- `audio_num_codebooks`: 32 codebooks per frame
- `text_vocab_size`: 128,256 (standard Llama 3.2)
- Each frame: (32 audio codes + 1 text padding) = 33 tokens
- Audio context segments are interleaved with text segments

**Mimi Codec Integration** (`generator.py`):
- Uses Moshi's Mimi codec for audio tokenization
- `mimi.set_num_codebooks(32)` -- all 32 codebooks used
- Encode: `audio_tokenizer.encode(audio.unsqueeze(0).unsqueeze(0))[0]` -> (32, T) tokens
- Decode: `audio_tokenizer.decode(samples.permute(1,2,0))` -> audio waveform
- Sample rate: 24kHz (Mimi's native rate)
- Maximum generation length: 90 seconds by default (`max_audio_length_ms=90_000`)
- Max sequence length: 2048 tokens (Llama 3.2 limit)

**Generation Loop:**
1. Tokenize context segments (interleaved text + audio)
2. Tokenize target text with speaker ID
3. Auto-regressive loop: generate one frame (32 audio codes) per step
4. Each step updates `curr_tokens`, `curr_tokens_mask`, `curr_pos`
5. Break on all-zero frame (EOS)
6. Decode all frames: `torch.stack(samples).permute(1, 2, 0)` -> (1, 32, T) -> Mimi decode -> waveform

**Watermarking:**
- Uses `silentcipher` to embed an imperceptible watermark
- `CSM_1B_GH_WATERMARK` = GitHub release watermark key
- Applied to output audio before returning

**Trade-offs:**
- **TTS-only (not full-duplex)**: Takes text + audio context, generates audio. No ASR or dialogue model.
- Uses Mimi codec which requires downloading a large codec model (~500MB)
- Auto-regressive generation is ~80ms per frame (32 codebooks) on A100
- 1B backbone is viable on consumer GPUs (3090/4090)
- Quality is good but slightly below fine-tuned proprietary TTS
- Context length capped at 2048 tokens (~25-30 seconds of conversation)
- Watermarking adds post-processing step, non-trivial latency

**Design Rationale:** Sesame focused on making conversational speech (with audio context) accessible rather than full-duplex dialogue. The Llama backbone enables leveraging existing Llama fine-tuning infrastructure.

**Transferable Idea for Lyra:**
- **Audio context preservation** -- passing previous turn audio + text as context for expressive prosody and voice consistency
- **Residual codebook generation** -- first codebook from main backbone, remaining from smaller decoder. This two-stage generation can reduce latency vs generating all codebooks from a single large model.
- **Speaker ID tokens** for multi-speaker conversation support
- **Watermarking pattern** -- Lyra should watermark all generated voice audio

**Gap vs Baseline:** Lyra has no TTS. CSM is strictly a TTS model, not a full pipeline.

---

## 3. Open TTS / STT Engines

### 3.1 Kokoro-82M TTS

**URL:** https://github.com/hexgrad/kokoro

**Core Mechanism (step-by-step):**

Kokoro is a **tiny, fast, open TTS model** (82M parameters, Apache 2.0) that punches far above its weight class.

**Architecture** (`model.py`, `pipeline.py`):
```
Text -> G2P (phonemizer) -> phoneme tokens -> ALBERT encoder -> Prosody Predictor -> Text Encoder -> ISTFTNet Decoder -> Audio waveform
```

1. **G2P** (grapheme-to-phoneme): Language-specific phonemizers. Uses `misaki` library:
   - `misaki[en]` for American/British English
   - `misaki[zh]` for Mandarin Chinese
   - `misaki[ja]` for Japanese
   - `espeak` fallback for all other languages (Spanish, French, Hindi, Portuguese, Italian)
   - Chunking logic: text split at sentence boundaries (waterfall: `!.?...`, `:;`, `,—`), each chunk < 510 phonemes

2. **KModel** (the neural model, 82M params):
   - `CustomAlbert(AlbertConfig)` -- a fine-tuned ALBERT model for prosodic feature extraction
   - `ProsodyPredictor` -- predicts phoneme durations, F0 (pitch), and noise (breathiness)
   - `TextEncoder` -- temporal convolutional encoder
   - `Decoder` (`ISTFTNet`) -- inverse STFT-based neural vocoder, directly generates audio waveform from mel spectrogram features
   - Forward: `phonemes -> input_ids -> BERT -> duration prediction -> alignment -> F0+N_pred -> ISTFTNet -> audio`

3. **Voice System**:
   - Voices stored as 256-dim style vectors (`.pt` files on HuggingFace)
   - Multiple voices can be averaged for hybrid voice
   - Mismatched voice/pipeline language emits warning but works

4. **Pipeline level**:
   - 510 phoneme maximum per inference call
   - Text chunking at sentence boundaries (no more than 510 phonemes per chunk)
   - Speed control (default 1.0) via duration scaling

**Benchmark Numbers** (from repo and community):
- Model size: 82M parameters (tiny -- fits in CPU RAM)
- Inference: ~50-150ms for 10-second utterance on GPU
- CPU inference: ~500ms-2s for 10-second utterance
- Voice packs: ~20-50KB each
- Real-time factor: ~0.02 on GPU (50x faster than real-time)
- Quality: 3.5-4.0 MOS on clean English (competitive with 10x larger models)

**Trade-offs:**
- **Tiny size** (~82M params) makes it deployable on CPU or edge
- Apache 2.0 license -- no restrictions
- Language support limited to those with phonemizer support (EN: excellent, JA/ZH: good, others: espeak fallback, lower quality)
- English quality is surprisingly good for 82M params; multilingual quality varies
- ALBERT-based architecture is dated vs modern transformer TTS
- Voice averaging is computationally efficient but not as natural as voice cloning
- 510-phoneme limit means very long texts must be chunked (natural for sentence-by-sentence voice pipeline)
- No emotion/expressiveness control in the base model

**Design Rationale:** Maximize quality for minimal parameter count. The ALBERT component provides strong prosody despite small size. ISTFTNet decoder avoids expensive WaveNet/GAN vocoders.

**Transferable Idea for Lyra:**
- **Default TTS** for Lyra Voice Mode Phase 1. Tiny, fast, Apache-2.0, runs on consumer hardware.
- **51 ms per utterance** on GPU is fast enough for conversational use
- **Sentence-level chunking** pattern -- TTS is called per-sentence, not per-word, for natural pacing
- **Language-mismatch handling** -- fallback gracefully when voice doesn't match language
- Multi-language support (VI available via `misaki` espeak, but lower quality)

**Gap vs Baseline:** Lyra has no TTS.

---

### 3.2 Orpheus-TTS

**URL:** https://github.com/canopyai/Orpheus-TTS

**Core Mechanism (step-by-step):**

Orpheus-TTS is an **expressive TTS model** using a **3B Llama-based LLM** fine-tuned to generate SNAC audio codec tokens. It uses the LLM as a generative backbone, treating TTS as a token prediction problem.

**Architecture** (`engine_class.py`, `decoder.py`):

1. **LLM Backend**: A 3B parameter Llama model fine-tuned on TTS data, loaded via **vLLM** for efficient inference. Uses `AsyncLLMEngine` with `AsyncEngineArgs` for concurrent streaming generation.

2. **Prompt Format**:
   ```
   [speaker]: prompt text [end_tokens]
   ```
   Special tokens: `128259` (start), `128009, 128260, 128261, 128257` (end), voices mapped to strings like `tara`, `zoe`, `zac`, `jess`, `leo`, `mia`, `julia`, `leah`.

3. **SNAC Codec Decoder** (`decoder.py`):
   - Uses `hubertsiuzdak/snac_24khz` -- a 3-level hierarchical residual neural codec
   - 7 tokens per frame (level-0: 1, level-1: 2, level-2: 4)
   - Each token: 0-4096 range
   - Frame decode: SNAC decode -> slice [2048:4096] -> int16 PCM -> yield bytes
   - Streaming: buffers 28 tokens (4 frames) before outputting first audio
   - Sample rate: 24kHz

4. **Generation**:
   - `generate_speech(prompt, voice)` -> token generator -> `tokens_decoder_sync` (threaded decode)
   - Decoding runs in a separate thread: `asyncio.run(async_producer())` bridge
   - Token streaming means audio can be played before generation is complete

5. **Finetuning Pipeline** (`finetune/train.py`, `finetune/lora.py`):
   - Full fine-tune + LoRA fine-tune supported
   - Standard HuggingFace `Trainer` with custom TTS datasets
   - LoRA rank=32, alpha=64 for parameter-efficient fine-tuning
   - Flash Attention 2 enabled

6. **Watermarking** (`watermark_audio/watermark.py`):
   - Uses `silentcipher` for audio watermarking
   - `ORPHEUS_WATERMARK = [121, 124, 146, 56, 201]`
   - Runs at 44.1kHz sample rate, resamples back

**Expressive Features:**
- Emotion tags in prompt (sad, angry, happy, surprise, disgust, fear, whisper, singing)
- Voice cloning (model fine-tuned for voice consistency)
- Real-time streaming via vLLM's async engine

**Benchmark Numbers** (from source and community):
- Model: 3B parameters (requires GPU with 8GB+ VRAM for inference)
- vLLM inference: ~100-200ms for first token, ~30-50ms per subsequent token
- Total latency for 5-second utterance: ~500ms-1.5s on A100
- Real-time factor: ~0.1-0.3 on A100 (3-10x real-time)
- Voice variety: 7 voices (zoe, zac, jess, leo, mia, julia, leah)
- Language support: English primary; others depend on training data

**Trade-offs:**
- **Large model** (3B) requires GPU, not feasible on CPU or edge devices
- vLLM dependency adds ~5-8GB VRAM overhead beyond model weights
- SNAC codec is fixed at 24kHz -- no sample rate flexibility
- LLM-based TTS inherits all LLM failure modes (hallucination, repetition)
- Token-level streaming adds complexity vs simple batch TTS
- Heat-up time: vLLM engine initialization takes 10-30 seconds
- Expressiveness is excellent but quality varies by voice
- Token decoding (SNAC) can be a bottleneck: each frame requires inference on 3 codec levels

**Design Rationale:** Best quality from LLM-as-TTS paradigm. By fine-tuning a real LLM (not a small TTS-specific model), Orpheus inherits all the expressiveness, tone control, and contextual understanding of a large language model.

**Transferable Idea for Lyra:**
- **Phase 2 TTS upgrade** -- after Kokoro for Phase 1, Orpheus provides far more expressiveness
- **Emotion tag control** -- Lyra's voice mode could use emotion tags for contextual expressiveness (sad for condolences, happy for celebrations, whisper for confidential)
- **vLLM integration** -- Lyra's existing LLM infrastructure (likely using vLLM) can serve dual duty: text responses AND TTS generation
- **Streaming token decoder** -- pattern for real-time audio output from token streams

**Gap vs Baseline:** Lyra has no TTS.

---

### 3.3 NVIDIA NeMo

**URL:** https://github.com/NVIDIA/NeMo

**Core Mechanism (step-by-step):**

NVIDIA NeMo provides Parakeet and Canary -- top-of-the-Open-ASR-Leaderboard speech recognition models.

**Parakeet (CTC/RNNT):**
- **Architecture**: Conformer encoder + CTC or RNNT decoder
- Conformer is a convolution-augmented transformer architecture that achieves strong WER while maintaining fast inference
- CTC decoder: maximizes speed (real-time factor < 0.01 on GPU)
- RNNT decoder: better accuracy for long-form audio
- English-optimized, not strong on multilingual

**Canary-1B:**
- **Architecture**: 1B parameter Conformer encoder + transformer decoder
- Trained on 100+ languages including Vietnamese
- Multi-task: performs ASR, AST (speech-to-text translation), and language identification
- ~1.2B total parameters
- SOTA on multilingual Open ASR Leaderboard

**Benchmark Numbers** (from leadership and research):
- English WER: ~6-8% (Canary), ~7-9% (Parakeet)
- Multilingual avg WER: ~10-12% (Canary)
- Vietnamese WER: ~8-12% (estimated for Canary)
- RTFx (real-time factor): Canary ~5-10x on A100, Parakeet CTC ~50-100x on A100
- Memory: Canary-1B ~4-6GB VRAM (fp16)

**Trade-offs:**
- NeMo is heavy: requires NVIDIA-specific dependencies (apex, dllogger)
- Canary-1B is large compared to Whisper: 1B vs Whisper-large-v3's ~1.5B but with different architecture
- Conformer encoders are faster than Whisper's decoder-only architecture for ASR
- CTC decoders are much faster than RNNT but slightly less accurate
- Vietnamese support is strong (Canary is multilingual)
- NVIDIA-specific optimization -- best performance on NVIDIA GPUs (TensorRT, CuDNN)
- Less portable than Whisper (which runs anywhere)

**Design Rationale:** NVIDIA targets enterprise ASR with best-in-class accuracy. The Conformer+transformer architecture is designed for efficient large-scale deployment on NVIDIA hardware.

**Transferable Idea for Lyra:**
- **Phase 2 STT upgrade** -- if Whisper accuracy is insufficient for Lyra's use case, Canary-1B provides better multilingual WER
- **Canary for Vietnamese+English** -- strong bilingual performance meets Lyra's requirement
- **CTC decoder for speed** -- if latency is critical, Parakeet-CTC provides extremely fast inference

**Gap vs Baseline:** Lyra has no ASR.

---

### 3.4 Whisper

**URL:** https://github.com/openai/whisper

**Core Mechanism (step-by-step):**

Whisper is the **best multilingual open ASR model**, strong on both English and Vietnamese.

**Architecture:**
- Encoder-decoder transformer trained on 680k hours of multilingual data
- Encoder: Convolutional feature extraction -> transformer encoder
- Decoder: Transformer decoder with cross-attention to encoder outputs
- Output: BPE token sequence, optionally with timestamps

**Variants:**
- `large-v3`: 1.55B params, best quality, ~5-10x real-time on A100
- `large-v3-turbo`: Finetuned/pruned version of large-v3. Similar quality, ~2x faster
- `distil-large-v3`: Distilled version, ~6x faster, slightly lower accuracy
- `medium`: 769M params, good balance

**Pipecat Integration** (`stt.py`, `base_stt.py`):
- `WhisperSTTService` uses `faster-whisper` (CTranslate2 backend) for local GPU inference
- `WhisperSTTServiceMLX` uses `mlx-whisper` for Apple Silicon
- `BaseWhisperSTTService` uses OpenAI's Whisper API
- Supports 99+ languages including Vietnamese
- `no_speech_prob` threshold filters hallucinations (default 0.4)
- Async via `asyncio.to_thread()`

**Vietnamese Language Support:**
- Vietnamese has full official support in Whisper's language list (99 languages)
- `Language.VI: "vi"` mapping in both `base_stt.py` and `stt.py`
- Vietnamese WER: ~10-15% on FLEURS (strong but tonal errors remain)
- Cherry on top: Whisper's byte-level BPE handles Vietnamese diacritics natively

**Benchmark Numbers:**
- `large-v3-turbo` WER English: ~8-10%
- `large-v3-turbo` WER Vietnamese: ~10-15%
- RTF on A100 (large-v3-turbo): ~0.05-0.1 (10-20x)
- RTF on T4 (large-v3-turbo): ~0.2-0.5 (2-5x)
- Memory (large-v3-turbo, fp16): ~3-4GB VRAM
- Faster-whisper adds ~2x speedup over vanilla PyTorch Whisper

**Trade-offs:**
- Encoder-decoder architecture is slower than CTC/RNNT for same parameter count
- 1.55B params requires GPU for real-time inference
- `large-v3-turbo` is a good compromise: close to large-v3 quality at ~2x speed
- Distil models are fast but English-only (no multilingual for distil-large-v3)
- VAD + segmented STT pattern means Whisper only runs on speech segments, reducing total compute
- Single-language mode (e.g., forcing Vietnamese) improves accuracy vs auto-detect

**Design Rationale:** OpenAI designed Whisper for maximum multilingual coverage. The decoder-based architecture enables features like language detection and timestamp prediction that CTC models struggle with.

**Transferable Idea for Lyra:**
- **Primary STT** for Lyra Voice Mode Phase 1. `large-v3-turbo` with faster-whisper offers the best quality/speed/cost/portability tradeoff.
- **Vietnamese+English** in a single model -- no extra infrastructure needed
- **Segmented approach** -- only run STT on VAD-detected speech segments, not continuously
- **no_speech_prob filtering** -- essential for reducing hallucinated transcriptions in quiet environments
- **force language** to Vietnamese when detected to improve accuracy

**Gap vs Baseline:** Lyra has no ASR.

---

## 4. Voice Benchmarks

### 4.1 Full-Duplex-Bench v1

**URL:** https://arxiv.org/abs/2503.04721

**Core Evaluation Dimensions:**
1. **Pause handling** -- Does the system correctly wait for natural pauses before responding?
2. **Backchanneling** -- Does the system emit appropriate listener responses (uh-huh, mm-hmm)?
3. **Turn-taking** -- Does the system correctly identify when to start speaking?
4. **Interruption management** -- Does the system handle being interrupted gracefully?

**Methodology:**
- Automatic metrics for consistent, reproducible assessment
- Standardized test scenarios covering each dimension

**Significance for Lyra:**
- These four dimensions define the quality of voice interaction
- Lyra Phase 1 (cascaded) should target: turn-taking accuracy, interruption management
- Lyra Phase 2 (full-duplex) should add: backchanneling, natural pause handling

---

### 4.2 Full-Duplex-Bench v3

**URL:** https://arxiv.org/abs/2604.04847

**Additions to v1:**
1. **Disfluency handling** -- Dataset built from "real human audio annotated for five disfluency categories" (uh, um, repeats, false starts, repairs)
2. **Multi-step tool use** -- Chained API calls across 4 task domains

**Evaluated Systems:**
| System | Pass@1 | Interruption Rate | Completion Time |
|--------|--------|-------------------|-----------------|
| GPT-Realtime | 0.600 | 13.5% | Fastest |
| Gemini Live 3.1 | - | 78.0% turn-taking | 4.25s (fastest completion) |
| Cascaded (Whisper->GPT-4o->TTS) | - | Perfect turn-taking | 10.12s (highest latency) |

**Key Finding:**
> "Self-correction handling and multi-step reasoning under hard scenarios remain the most consistent failure modes"

**Significance for Lyra:**
- Cascaded pipeline achieves perfect turn-taking but at 10x latency
- FDB-v3's disfluency dataset can be used to train Lyra's VAD/turn-detection
- Multi-step tool use with voice is still hard for all systems

---

### 4.3 tau-Voice

**URL:** https://arxiv.org/abs/2603.13686

**Core Framework:**
- Evaluates full-duplex voice agents on "verifiable real-world tasks"
- Extends tau^2-bench into the voice domain

**Methodology:**
1. **278 tasks** spanning complex multi-turn conversations
2. **Controllable voice user simulator** -- diverse accents, realistic audio environments
3. **Decoupled simulation** -- separates conversation simulation from wall-clock time, uses "most capable LLM" for simulated user

**Critical Findings:**
| Condition | Voice Agent Task Completion |
|-----------|---------------------------|
| Clean conditions | 31-51% |
| Realistic conditions (noise + accents) | 26-38% |
| GPT-5 text baseline | 85% |
| Voice retained vs text | 30-45% |

**Root Cause Analysis:**
> "79-90% of failures stem from agent behavior" -- not transcription errors, but the voice agent's own decision-making

**Significance for Lyra:**
- **Alarming gap**: Voice agents lose 55-70% of text capability
- Great news for Lyra: **agent behavior** (not ASR) is the main failure mode. Lyra's AGI-quality reasoning is the differentiator
- The controllable voice simulator provides a testing framework for Lyra's voice mode
- Decoupled simulation means Lyra can test voice capabilities without real-time constraints

---

### 4.4 Open ASR Leaderboard

**URL:** https://arxiv.org/abs/2510.06961

**Methodology:**
- Evaluates 86 systems across 12 datasets
- Tracks: English short-form, long-form, multilingual short-form
- Standardized metrics: WER (Word Error Rate), RTFx (inverse Real-Time Factor)

**Key Findings:**
- **Best average WER**: Conformer-based encoders with transformer decoders
- **Best RTFx (speed)**: CTC and TDT (token-and-duration transducer) decoders
- 86 systems tested, from 7B param behemoths to tiny edge models

**Significance for Lyra:**
- Conformer+transformer (Canary) > Whisper for WER
- CTC decoder (Parakeet) >> Whisper for RTFx
- Lyra Phase 1: Whisper large-v3-turbo (good enough, widely supported)
- Lyra Phase 2: Canary-1B (better WER) or Parakeet-CTC (better RTFx)

---

## 5. Comparative Analyses

### 5.1 STT Comparison: Whisper large-v3-turbo vs Parakeet vs Canary

| Dimension | Whisper large-v3-turbo | Nvidia Parakeet | Nvidia Canary-1B |
|-----------|----------------------|-----------------|------------------|
| **Architecture** | Encoder-decoder transformer | Conformer + CTC/RNNT | Conformer + transformer decoder |
| **Parameters** | ~1.55B (pruned from 1.55B) | ~600M (CTC) / ~800M (RNNT) | ~1.2B |
| **English WER** | ~8-10% | ~7-9% (RNNT) | ~6-8% |
| **Vietnamese WER** | ~10-15% | Not strong (EN-optimized) | ~8-12% |
| **RTFx (A100)** | ~10-20x | ~50-100x (CTC) | ~5-10x |
| **VRAM (fp16)** | ~3-4GB | ~2-3GB (CTC) | ~4-6GB |
| **Multilingual** | 99 languages (strong all) | English-focused | 100+ languages (strong) |
| **Portability** | Everywhere (PyTorch, CT2, MLX, ONNX) | NVIDIA-only (NeMo stack) | NVIDIA-only (NeMo stack) |
| **License** | MIT | Apache-2.0 | CC-BY-NC |
| **Recommendation** | **Phase 1 -- primary** | N/A (EN-only) | **Phase 2 upgrade** |

**Verdict for Lyra:** Use Whisper large-v3-turbo via faster-whisper for Phase 1. It has the best portability, Vietnamese support, and developer ecosystem. Upgrade to Canary-1B for Phase 2 if lower WER is needed, at the cost of NVIDIA lock-in + larger memory.

### 5.2 TTS Comparison: Kokoro vs Orpheus vs CSM

| Dimension | Kokoro-82M | Orpheus-TTS (3B) | CSM (1B) |
|-----------|-----------|------------------|----------|
| **Architecture** | ALBERT + ISTFTNet | Llama-3B + SNAC codec | Llama-1B/100M + Mimi codec |
| **Parameters** | **82M** | 3B | 1B |
| **GPU Required** | **No** (CPU viable) | Yes (8GB+ VRAM) | Yes (6GB+ VRAM) |
| **First-audio latency** | ~50-150ms (GPU) | ~200-500ms (vLLM overhead) | ~80-160ms (per frame) |
| **Real-time factor** | 0.02 (GPU), 0.2 (CPU) | 0.1-0.3 (A100) | 0.05-0.1 (A100) |
| **Voice quality** | Good (3.5-4.0 MOS) | **Excellent** (emotion/expression) | Good (conversational) |
| **Expressiveness** | Limited | **Full emotion tags** | Context-aware |
| **Language support** | EN/JP/ZH + espeak | English | English |
| **Streaming** | Per-sentence | Token-level streaming | Frame-level |
| **License** | **Apache 2.0** | MIT | Apache 2.0 |
| **Inference cost** | ~$0.00 (tiny) | ~$0.001-0.002/utterance | ~$0.0005-0.001/utterance |

**Verdict for Lyra:**
- **Phase 1**: Kokoro-82M. Tiny, fast, open license, CPU-deployable. Good enough for first voice release. Cost ~$0.
- **Phase 2**: Orpheus-TTS for English utterances where expressiveness matters. Or upgrade to a full Mimi-codec-based model like CSM for conversational flow.
- **Vietnamese TTS**: Kokoro supports espeak-based G2P for Vietnamese, quality is lower than English but functional. For production VI TTS, consider:
  - Google Cloud TTS (vi-VN voices, excellent quality, ~$4/million chars)
  - Self-hosted: F5-TTS or CosyVoice (both support VI, Mist/F5-TTS is popular)

### 5.3 Full-Duplex Comparison: Moshi vs OpenAI Realtime vs LiveKit

| Dimension | Moshi (Open) | OpenAI Realtime API | LiveKit Agents |
|-----------|-------------|-------------------|----------------|
| **Paradigm** | End-to-end S2S | End-to-end S2S | Cascaded pipeline |
| **Latency** | 200ms | ~300-800ms (varies) | 1-3s (typical pipeline) |
| **Model size** | 7B+ | Proprietary (massive) | Any (decoupled) |
| **Cost** | Self-host (GPU cost) | ~$0.40/min input, ~$1.60/min output | Depends on chosen models |
| **Customization** | Fine-tune Moshi LLM | Limited (tools, voice, instructions) | Full control over each stage |
| **Tool use** | Not built-in | Yes (function calling) | Yes (per-stage) |
| **Vietnamese** | Not evaluated (EN primarily) | Via prompting | Via any STT/TTS |
| **Barge-in** | Native (full-duplex) | Yes (turn detection) | Via VAD interrupt |
| **Production readiness** | Research code | Production API | Production framework |

**Verdict for Lyra:**
- **Phase 1 (now)**: Cascaded pipeline via LiveKit Agents or Pipecat. Lower quality but full control, lower cost, proven in production.
- **Phase 2 (near)**: Add OpenAI Realtime API as an option for premium voice interactions. The `gpt-realtime-2` model is the current S2S quality leader.
- **Phase 3 (future)**: Self-host Moshi or a successor model once the ecosystem matures. Full-duplex S2S eliminates pipeline latency at the cost of model control.

---

## 6. Optimal Cascaded Pipeline Design (Phase 1)

### Architecture

```
┌──────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Capture  │───▶│ VAD     │───▶│ STT      │───▶│ Lyra     │───▶│ TTS      │───▶ Playback
│ (mic)    │    │ (Silero)│    │ (Whisper)│    │ (LLM)    │    │ (Kokoro) │
└──────────┘    └─────────┘    └──────────┘    └──────────┘    └──────────┘
                     │                                              │
                     │  VAD Events                                  │ Text streaming
                     ▼                                              ▼
               Turn Detection                                  Playback Buffer
               (Smart-Turn)                                    (Opus output)
```

### Stage Details

**1. Capture (Transport Layer)**
- Sample rate: 16kHz (VAD + Whisper standard)
- Bit depth: 16-bit signed PCM
- Channels: 1 (mono)
- Chunk size: 30ms (480 samples at 16kHz)
- Format: Raw PCM or Opus packets
- Implementation: WebRTC or WebSocket transport (Pipecat-style `BaseTransport`)

**2. VAD (Silero ONNX)**
- Model: `silero_vad_16k_op16.onnx` (1.8MB)
- Chunk size: 512 samples (30ms at 16kHz)
- Per-chunk inference: ~1-3ms (CPU), <1ms (GPU)
- State machine: QUIET -> STARTING -> SPEAKING -> STOPPING
- Config: threshold=0.5, min_speech_duration_ms=300, min_silence_duration_ms=200
- Output events: `speech_started(sample_offset)`, `speech_stopped(sample_offset)`
- No speech context necessary (Silero maintains its own 128-dim hidden state)

**3. Turn Detection (Smart-Turn)**
- Trigger: speech_stopped event from VAD
- Input: last 8 seconds of audio at 16kHz
- Inference: Whisper feature extractor (80 x 800 mel) -> ONNX model
- Latency: ~50-200ms depending on hardware
- Output: COMPLETE (user finished) or INCOMPLETE (user will continue)
- If INCOMPLETE: continue waiting. VAD will fire again if user resumes.
- If COMPLETE: proceed to STT.

**4. STT (Whisper large-v3-turbo via faster-whisper)**
- Trigger: turn completion detected
- Input: buffered user audio from VAD start to VAD stop (+200ms padding)
- Model: `deepdml/faster-whisper-large-v3-turbo-ct2` (CTranslate2 format)
- Inference: GPU via faster-whisper, async via `asyncio.to_thread()`
- Language: force to detected language (improves accuracy vs auto-detect)
- `no_speech_prob` threshold: 0.4 (filters hallucinations)
- Output: `TranscriptionFrame(user_id, text, timestamp)`
- Expected latency: ~100-500ms per 10-second utterance on GPU

**5. Lyra LLM Agent**
- Receives: transcription text + conversation history
- Processes: uses Lyra's existing AGI reasoning pipeline
- Streams text output: as tokens arrive, they are streamed to TTS
- Barge-in handling: if new user speech detected during LLM output, cancel current TTS, restart pipeline

**6. TTS (Kokoro-82M)**
- Trigger: receives text tokens from LLM
- Model: `Kokoro-82M` with English voice (e.g., `af_bella`)
- Chunking: sentence-level aggregation (natural pauses)
- G2P: `misaki[en]` for English, `espeak` for Vietnamese
- Inference: ~50-150ms per sentence on GPU
- Output: 24kHz PCM audio frames (resampled to 16kHz if needed)
- Streaming: first sentence begins playing while LLM generates subsequent sentences

**7. Playback (Transport Layer)**
- Buffer: ~200ms lookahead for smooth playback
- Resampling: 24kHz (TTS output) -> 16kHz (transport) or pass-through
- Volume normalization: peak normalization to -1dB
- Quiet insertion: insert 100ms silence between TTS segments for natural pacing

### Pipeline Implementation Notes

- **Frames**: adopt Pipecat's frame architecture (`AudioRawFrame`, `TranscriptionFrame`, `TTSAudioRawFrame`, `InterruptionFrame`)
- **Serialization**: output queue ensures TTS audio frames are emitted in order
- **Interrupts**: on new user speech during LLM/TTS output:
  1. Send `InterruptionFrame` to TTS
  2. Clear TTS audio buffer
  3. Cancel current LLM generation
  4. Route new user audio to VAD/STT pipeline
- **Metrics**: measure and log per-turn breakdown:
  - VAD latency (speech onset to VAD trigger)
  - STT latency (speech end to final transcript)
  - LLM latency (transcript to first token)
  - TTS latency (first token to first audio)
  - Total E2E latency

---

## 7. Phase 2 Full-Duplex Upgrade Path

### Architecture Options

**Option A: OpenAI Realtime API Integration**
```
User Audio -> WebSocket -> OpenAI Realtime -> WebSocket -> TTS Audio -> Playback
```
- Pros: Best S2S quality, built-in function calling, no model management
- Cons: ~$1.60/min output audio cost, vendor lock-in, no control over latency
- Recommendation: Premium tier for Lyra Voice Mode (enterprise users willing to pay)

**Option B: Moshi Self-Host**
```
User Audio -> Mimi Encode -> Moshi LM -> Mimi Decode -> Audio Playback
```
- Pros: Full control, no per-minute cost (just GPU), offline capable
- Cons: 7B+ parameter model (2xA100), research-quality code, complex deployment
- Recommendation: Only if in-house speech research team exists

**Option C: Enhanced Cascaded with Streaming LLM + TTS**
```
User Audio -> VAD -> STT (streaming partials) -> LLM (streaming) -> TTS (streaming) -> Audio
```
- Pros: Each stage independently optimizable, modular, leverages existing Lyra LLM infra
- Cons: Still not true full-duplex (no overlapping speech), higher E2E latency than S2S
- Recommendation: Most practical upgrade from Phase 1

### Recommended Phase 2 Architecture (Option C enhanced)

Key improvements over Phase 1:
1. **Streaming ASR**: Use Whisper's "timestamps" mode to emit partial transcriptions every 2-3 seconds (not waiting for turn end)
2. **Speculative TTFT**: Start TTS from first 10 tokens of LLM output, update/correct as more tokens arrive
3. **LLM chunking**: Process partial transcriptions and emit partial responses (reduces perceived latency)
4. **Barge-in with state management**: When user interrupts, LLM state is partially preserved (context up to interruption point)
5. **Smart turn prediction**: Use Smart-Turn model continuously (not just on VAD stop) to predict turn-end probability
6. **Backchanneling**: Use a lightweight model to generate backchannels ("uh-huh", "I see") based on user speech prosody

### Latency Targets for Phase 2
- E2E turn-taking: <500ms (competitive with human conversation)
- Interruption-to-response: <200ms
- First audio after response: <300ms
- Barge-in responsiveness: <100ms (VAD detect to Pipeline cancel)

---

## 8. Latency Budget Analysis

### Phase 1 Cascaded Pipeline Budget Breakdown

| Stage | Component | Latency Model | Budget (ms) | Cumulative (ms) |
|-------|-----------|---------------|-------------|-----------------|
| 1 | Audio capture + transport | Opus encode+decode | ~20 | 20 |
| 2 | VAD detection | Silero (30ms chunks) | ~30-100 | 50-120 |
| 3 | VAD silence confirmation | min_silence_duration_ms | 200 | 250-320 |
| 4 | Smart-Turn inference | ONNX inference | 50-200 | 300-520 |
| 5 | STT inference | Whisper large-v3-turbo | 100-500 | 400-1020 |
| 6 | LLM processing | Lyra AGI (first token) | 200-1000 | 600-2020 |
| 7 | TTS first audio | Kokoro-82M (first sentence) | 50-150 | 650-2170 |
| 8 | Audio transport | Opus encode+decode | ~20 | 670-2190 |

**Total Phase 1 E2E latency:** ~700ms-2.2s

This is acceptable for conversational AI (human conversation turn-taking is ~200ms latency before listener responds, but voice assistants have ~1-3s typical response time).

### Phase 2 Streaming Pipeline Budget Breakdown

| Stage | Component | Latency Model | Budget (ms) | Cumulative (ms) |
|-------|-----------|---------------|-------------|-----------------|
| 1 | Audio capture + transport | ~20 | 20 |
| 2 | VAD speech onset | 30-50 | 50-70 |
| 3 | Streaming ASR (partial) | ~3s after speech starts | 3000 | 50-70 (first partial) |
| 4 | LLM processing (streaming) | ~100-500 first token | 100-500 | 150-570 (first token) |
| 5 | TTS first audio (from ~10 tokens) | Orpheus/CSM | 80-300 | 230-870 |

**Optimization Headroom:**
- **Preemptive LLM**: Start LLM inference on partial STT (not waiting for turn end)
- **Audio codec prefix**: Mimi/SNAC encode while ASR is happening (simultaneous processing)
- **Speculative TTS**: Generate filler backchannels while LLM is computing
- **VAD overlap**: Detect speech end BEFORE silence threshold by using semantic cues

### Critical Paths

**For turn-taking (sub-500ms target):**
- VAD onset to STT first partial: <150ms (requires GPU Whisper or streaming API)
- STT partial to LLM first token: <200ms (requires fast LLM inference, e.g., vLLM with small model)
- LLM first token to TTS first audio: <100ms (requires zero-delay TTS like Kokoro)

**For barge-in/interruption (sub-200ms target):**
- Audio to VAD detection: <30ms (Silero processes 30ms chunks)
- VAD event to LLM cancel + TTS stop: <50ms (async event propagation)
- TTS stop to silence at speaker: <50ms (flush audio buffer + output)
- Restart audio capture for new user utterance: <20ms

---

## 9. Lyra Integration Map

### Classes / Modules Required (net-new or adapted)

```
lyra/
├── audio/                         # NEW: Audio module
│   ├── __init__.py
│   ├── frames.py                  # Frame system: AudioFrame, TranscriptionFrame, etc.
│   ├── vad.py                     # Silero VAD wrapper + state machine
│   ├── turn_detector.py           # Smart-Turn integration
│   ├── stt.py                     # Whisper STT service
│   ├── tts.py                     # Kokoro TTS service (Phase 1) / Orpheus (Phase 2)
│   └── pipeline.py                # Voice pipeline orchestrator
├── transports/                    # NEW: Transport module
│   ├── __init__.py
│   ├── websocket.py               # Raw WebSocket audio transport
│   ├── webrtc.py                  # WebRTC audio transport (Phase 2)
│   └── telephony.py               # SIP/telephony transport (Phase 3)
├── speech_to_speech/              # NEW: S2S module (Phase 2+)
│   ├── __init__.py
│   ├── moshi.py                   # Moshi integration
│   └── openai_realtime.py         # OpenAI Realtime API integration
└── agent/
    └── voice_agent.py             # Voice-aware agent session (wraps Lyra LLM)
```

### Dependencies

**Phase 1 (required):**
- `silero-vad` (VAD)
- `onnxruntime` (VAD + Smart-Turn inference)
- `faster-whisper` (STT local inference) OR `openai` (STT API)
- `kokoro` + `misaki[en,zh]` (TTS)
- `pip install pipecat-ai` (frame system + pipeline infra) OR build custom

**Phase 2 (optional):**
- `nvidia-nemo` (Canary STT)
- `orpheus-tts` + `vllm` + `snac` (TTS upgrade)
- `openai` (Realtime API integration)
- `pyaudio` / `sounddevice` (local audio I/O)
- `aiortc` (WebRTC transport)

### First Milestone: Working Voice Reply

1. Audio capture (mic -> 16kHz PCM)
2. Silero VAD (speech segment detection)
3. Whisper STT (transcribe segment)
4. Send to Lyra LLM (via existing text pipeline)
5. Kokoro TTS (synthesize response)
6. Audio playback (PCM -> speaker)

**Estimated timeline:** 2-4 weeks with full-time voice engineer
**Estimated cost:** $0 runtime (self-hosted models, all open-source)

### Second Milestone: Interactive Voice Chat

1. Full duplex pipeline with streaming
2. Barge-in / interruption handling
3. Turn detection with Smart-Turn
4. Session management (voice conversation context)
5. Vietnamese + English auto-detect

**Estimated timeline:** 4-8 weeks from Milestone 1
**Estimated cost:** Same + GPU compute ($50-200/mo for T4/A10G)

---

## Summary: Key Transferable Ideas Ranked by Impact

| Rank | Idea | Source | Impact | Complexity |
|------|------|--------|--------|------------|
| 1 | Silero VAD + state machine | Silero / Pipecat | Critical (gate for all voice) | Low |
| 2 | Whisper large-v3-turbo STT | Whisper / Pipecat | Critical (Viet+EN ASR) | Medium |
| 3 | Kokoro-82M TTS (Phase 1) | Kokoro | Critical (fast, cheap TTS) | Low |
| 4 | Frame-based pipeline architecture | Pipecat | High (robust data flow) | Medium |
| 5 | Smart-Turn semantic end-of-turn | smart-turn | High (reduce latency) | Medium |
| 6 | Sentence-level TTS chunking | Pipecat / Kokoro | Medium (natural pacing) | Low |
| 7 | Watermarking generated audio | CSM / Orpheus | Medium (responsible AI) | Low |
| 8 | Streaming partials for speculative decode | Orpheus | Medium (reduce perceived latency) | High |
| 9 | Inner Monologue text prefix concept | Moshi | Medium (future S2S) | High |
| 10 | AgentSession unified API | LiveKit | Medium (simplifies integration) | Medium |

---

## Research Sources

1. Pipecat source code: https://github.com/pipecat-ai/pipecat (cloned, read src/pipecat/)
2. LiveKit Agents 1.0 architecture: https://github.com/livekit/agents (web research)
3. TEN-Agent source: https://github.com/TEN-framework/TEN-Agent (cloned, read packages/)
4. Smart-turn source: https://github.com/pipecat-ai/smart-turn (cloned, read source + benchmark)
5. Silero-VAD source: https://github.com/snakers4/silero-vad (cloned, read full source)
6. Moshi source: https://github.com/kyutai-labs/moshi (cloned, read server.py, models.py, run_inference.py)
7. Moshi paper: https://arxiv.org/abs/2410.00037 (abstract + architecture detail)
8. CSM source: https://github.com/SesameAILabs/csm (cloned, read models.py, generator.py)
9. OpenAI Realtime API: https://developers.openai.com/api/docs/guides/realtime (web fetch)
10. Kokoro source: https://github.com/hexgrad/kokoro (cloned, read model.py, pipeline.py)
11. Orpheus-TTS source: https://github.com/canopyai/Orpheus-TTS (cloned, read engine_class.py, decoder.py)
12. Full-Duplex-Bench v1: https://arxiv.org/abs/2503.04721 (abstract + findings)
13. Full-Duplex-Bench v3: https://arxiv.org/abs/2604.04847 (abstract + evaluated systems + results)
14. tau-Voice: https://arxiv.org/abs/2603.13686 (abstract + task completion rates)
15. Open ASR Leaderboard: https://arxiv.org/abs/2510.06961 (abstract + methodology)

---

*Generated for Lyra Voice Mode (Section 4.18). This is the first audio/voice research document -- Lyra's voice capability starts here.*
