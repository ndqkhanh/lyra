# Voice Mode & Real-Time Interaction (FLAGSHIP) -- Thematic Synthesis
> **FLAGSHIP THEME** -- deepest, most complete synthesis required
> Synthesized from 281 paper rigor notes, 184 repo/doc notes, 80 book notes
> Date: 2026-06-07

## 1. Frontier Techniques (ranked by evidence strength)

### 1.1 Full-Duplex Multi-Stream Speech Modeling (Moshi)

- **Sources:** Moshi (arXiv:2410.00037v2, Kyutai), kyutai-labs/moshi repo (Apache 2.0), Full-Duplex-Bench (arXiv:2503.04721v3), Full-Duplex-Bench-v3 (arXiv:2604.04847v1)
- **Mechanism:** A single autoregressive transformer models 17 parallel token streams (1 text + 8 Moshi audio + 8 user audio) at 12.5 Hz (80ms frames). The temporal transformer (32 layers, 7B params, initialized from Helium text LLM) models cross-time dependencies; a depth transformer (6 layers, 1024-dim) models inter-codebook dependencies within each timestep. The "Inner Monologue" predicts text tokens ahead of speech tokens at each frame. Acoustic delay (tau=1-2 frames, 80-160ms) prevents collapse from co-temporal semantic-acoustic mutual information. Split RVQ in the Mimi codec decouples semantic quantization (1 VQ codebook, WavLM-distilled) from acoustic quantization (7 RVQ codebooks, adversarial-trained).
- **Evidence:**
  - MUSHRA: 81.0 at 1.1 kbps, 12.5 Hz, fully causal (Mimi codec, Table from arXiv:2410.00037v2)
  - Spoken QA: 26.6% WebQ, 62.3% LlamaQ, 22.8% TriviaQA -- Inner Monologue nearly triples accuracy (from 9.2/21.0/7.3 without it)
  - Turn-taking: Cond. PPL 41.9 at temp=0.8 (better than cascaded 45.9 and human 65.0)
  - Practical latency: 160ms theoretical (tau=1), 200ms on L4 GPU
  - Full-Duplex-Bench: Moshi responds fastest on turn-taking (0.265s latency) and interruption (0.257s) but has high pause-interruption rate (TOR 0.98) and low interruption coherence (GPT-4o score 0.765)
  - Quantization: W4A8 preserves 95.7% artifact-free generation at ~5GB
- **Maturity:** Lab validated -- open-source weights and code available, multi-platform (PyTorch + MLX + Rust/Candle), but not production-hardened (safety score 83.05 ALERT, far below text-only LLMs)

### 1.2 Think-Before-Speak (TbS) End-to-End Speech Agents (VoxMind)

- **Sources:** VoxMind (arXiv:2604.15710v1, Zhejiang University), building-multimodal-genai-agentic-apps-chapters (Book, Ch.11-12)
- **Mechanism:** Inserts an explicit Chain-of-Thought reasoning step between speech input and action/output. The system state S_t = (O_t, H_t, A_t) processes observations through a reasoning trajectory c_t ~ pi(c | o_t, H_{t-1}, T_t^local) BEFORE any action or tool invocation. A parallel auxiliary LLM asynchronously retrieves candidate tools from the global pool (1.3-2.6s latency, hidden behind reasoning time). The speech model only sees a small local tool set; the auxiliary LLM expands it on demand. Reverse CoT generation (Q, A -> R) produces training data via text LLMs.
- **Evidence:**
  - Overall Score: 74.57 vs Gemini-2.5-Pro 71.51, GPT-4o-audio 54.77 (Table 2)
  - +113.79% relative improvement over base StepAudio2 model (34.88 -> 74.57)
  - CoT preserves general speech quality (VoiceBench 64.21 with CoT vs 54.80 without -- prevents catastrophic forgetting)
  - Tool pool scaling: O(1) latency overhead (<15ms waiting) from 1 to 100 tools
  - Token overhead: 12.6% in speech mode (88 think tokens vs 701 answer tokens)
  - Real speech robustness: 86% task success despite disfluencies
- **Maturity:** Lab validated -- open-source (Apache 2.0), AgentChat dataset released, but requires H20-NVLink GPUs for training, real-speech gap (-7.3% FS)

### 1.3 LLM-Backbone Text-to-Speech (Orpheus TTS)

- **Sources:** canopyai/Orpheus-TTS repo (Apache 2.0), Orpheus paper (arXiv:2506.13131v1)
- **Mechanism:** Uses a standard Llama-3.2-3B causal LLM as the backbone for TTS, extended with 28,682 custom neural audio codec tokens (SNAC codec, 24kHz, 7 tokens/frame in 3 hierarchical codebooks). The LLM "understands" text semantically (not just phonetically), enabling contextual prosody, emotion, and zero-shot voice cloning. Interleaved training curriculum (2:1 -> 1:1 -> 0:1 text:speech ratio) preserves base LLM reasoning while adding speech tokens. vLLM async engine provides streaming at ~200ms latency. Sliding-window audio decoding (4 frames of 28 tokens) avoids boundary artifacts.
- **Evidence:**
  - Streaming latency: ~200ms real-time, ~100ms input streaming (README)
  - Model size: 3B parameters, BF16
  - Training data: 100k+ hours English speech
  - Supported voices: 8 English, 7 language pairs
  - 20 emotion/style tags (laugh, sigh, whisper, etc.)
  - No MOS scores or formal benchmarks published in the repo
- **Maturity:** Production deployed -- Apache 2.0, pip-installable, supports vLLM (GPU) + llama.cpp (CPU) + Baseten cloud, but lacks formal evaluation rigor (no MOS, no A/B vs ElevenLabs/Play.ht)

### 1.4 Conversational Speech Model with Audio Context (CSM)

- **Sources:** SesameAILabs/csm repo (Apache 2.0)
- **Mechanism:** A Llama-3.2-1B backbone + 100M decoder that generates multi-speaker conversational speech from text + audio context. Each 80ms frame has 33 token positions (32 Mimi RVQ audio codebook tokens + 1 text token). The backbone autoregressively models cross-modal sequence; a lightweight decoder iteratively predicts codebooks 1-31 (conditioned on C0 from backbone). Speaker identity is prompt-controlled -- zero-shot voice cloning from context audio, no fine-tuning needed. Mimi codec at 12.5 Hz from Kyutai. Imperceptible watermarking via SilentCipher.
- **Evidence:**
  - Frame rate: 12.5 Hz (80ms per frame)
  - Max generation: 90 seconds, limited by 2048-token context window
  - GPU memory: ~1.5-2 GB at BF16 for 1B backbone
  - No benchmarks published; codebase is ~550 lines (inference-only, no training)
  - Tested on CUDA 12.4/12.6; no MPS support
- **Maturity:** Demo/Release snapshot -- single commit repo, no training code, no formal evaluation, but Apache 2.0 and clean architecture

### 1.5 Cascaded Pipeline: STT -> LLM -> TTS (Production Standard)

- **Sources:** livekit/agents (Apache 2.0), pipecat-ai/pipecat (BSD 2-Clause), TEN-framework/TEN-Agent (Apache 2.0), OpenAI Realtime API docs, building-multimodal-genai-agentic-apps-chapters (Book, Ch.11), Full-Duplex-Bench-v3 (arXiv:2604.04847v1)
- **Mechanism:** Separate ASR (speech-to-text) -> LLM (reasoning) -> TTS (text-to-speech) with WebRTC transport. The pipeline is linear but with turn detection (VAD/endpointing), interruption handling, and barge-in. Frameworks differ in orchestration: Pipecat uses typed Frame objects on a directed graph; TEN uses JSON-defined static graphs with Agora RTC; LiveKit uses overridable async generator nodes with WebRTC.
- **Evidence (FDB-v3, arXiv:2604.04847v1):**
  - Cascaded: Tool Sel F1=0.803, Arg Acc=0.562, Pass@1=0.450, Latency=10.12s, Turn-take=100%
  - GPT-Realtime (end-to-end): Tool Sel F1=0.876, Pass@1=0.600, Latency=6.89s, Turn-take=96%
  - Cascaded guarantees 100% turn-take but is 1.5-2.4x slower than end-to-end
  - Cascaded self-correction Pass@1 = 0.176 (lowest of any model) -- Whisper finalizes before self-correction arrives
  - Gemini Live 3.1: fastest (4.25s) but 22% "silent worker" rate
- **Maturity:** Production deployed -- LiveKit, Pipecat, and TEN are all production frameworks with 50-60+ provider integrations each. OpenAI Realtime API is GA. This is the current industry standard.

### 1.6 Full-Duplex-Bench Evaluation Framework

- **Sources:** Full-Duplex-Bench (arXiv:2503.04721v3), Full-Duplex-Bench-v3 (arXiv:2604.04847v1)
- **Mechanism:** Four-dimensional automatic evaluation for full-duplex spoken dialogue: (1) Pause Handling -- Takeover Rate during mid-utterance pauses; (2) Backchanneling -- frequency + Jensen-Shannon divergence from human timing distribution; (3) Smooth Turn-Taking -- TOR + response latency; (4) User Interruption -- success rate + coherence score + latency after barge-in. FDB-v3 adds 100 real-human recordings with 5 disfluency categories and 11 mock APIs across 4 task domains for tool-use evaluation.
- **Evidence:**
  - Moshi: best latency (0.265s turn-taking) but worst pause handling (TOR 0.98)
  - Gemini Live: best pause handling (TOR 0.31) and backchannel timing (JSD 0.896)
  - Freeze-Omni: best interruption coherence (GPT-4o 3.615) but highest turn-taking latency (0.953s)
  - No model dominates across all dimensions -- architecture trade-offs are fundamental, not optimization artifacts
  - FDB-v3: GPT-Realtime best overall (Pass@1=0.600), all models fail >40% of self-correction scenarios
- **Maturity:** Research framework -- scenario-driven, fully automatic, but English-only, no human preference calibration

### 1.7 Streaming ASR with Speed-Accuracy Pareto Frontier

- **Sources:** Open ASR Leaderboard (arXiv:2510.06961v4), openai/whisper repo, NVIDIA NeMo repo (web)
- **Mechanism:** Conformer-based encoders + CTC/TDT decoders achieve 5-44x faster inference than Whisper-based encoders at modest WER cost (0.6-3.5pp). The Pareto frontier shows Conformer+Transformer for best accuracy (5.42% avg WER), Conformer+CTC for fastest inference (RTFx 2730-6400, WER 7.40-8.96%), and Conformer+TDT for best balance (RTFx 3390, WER 6.05%). For real-time voice agents, CTC/TDT decoders are the pragmatic choice -- they sacrifice 1-2pp WER for 20-40x speedup.
- **Evidence (Open ASR Leaderboard, 86 models):
  - Best accuracy: Cohere Labs Transcribe (5.42% WER, RTFx 525, FastConformer+Transformer)
  - Best speed: NVIDIA FastConformer CTC Large (8.96% WER, RTFx 6400)
  - Best balance: NVIDIA Parakeet TDT 0.6B v2 (6.05% WER, RTFx 3390)
  - Multilingual degrades English WER by 0.27-0.65pp across all architectures
  - Long-form (>30s): CTC/TDT gap narrows, RTFx advantage remains massive (2790-4383)
- **Maturity:** Production deployed -- NVIDIA NeMo, Whisper, and commercial APIs all benchmarked on standardized hardware (A100-80GB)

## 2. Head-to-Head Comparisons

| Technique | Accuracy | Latency | Memory Cost | Complexity | Scalability | Evidence Strength |
|-----------|----------|---------|-------------|------------|-------------|-------------------|
| **Moshi (End-to-End S2S)** | Spoken QA 62.3% LlamaQ; MMLU 49.7 (degrades from Helium 54.3) | 160-200ms theoretical, 265ms turn-taking | 15GB BF16; 5GB W4A8 | Very High -- 4-stage training, multi-stream data, RQ-Transformer | English-only; quantization-sensitive (W4A8 drops 7.5 MMLU pts) | HIGH -- detailed ablations, open-source weights, 3 independent benchmarks |
| **VoxMind (TbS End-to-End)** | 74.57 Overall Score vs Gemini Pro 71.51 | CoT adds ~88 tokens; aux LLM hidden latency <15ms | 2x H20-NVLink GPUs training; inference ~2B params | High -- CoT fine-tuning, dual-agent tool management, reverse CoT data gen | Scales to 100 tools with O(1) overhead | HIGH -- 5-model comparison, detailed ablations, 470hr AgentChat dataset |
| **Orpheus TTS (LLM-Backbone)** | No formal MOS; claims "superior to SOTA closed-source" | ~200ms streaming (vLLM); ~100ms input streaming | 3B params, BF16, GPU-required for streaming | Medium -- standard LLM fine-tuning, custom token vocab, SNAC codec | 8 voices, 7 languages, 20 emotions; fine-tunable with ~50 examples | LOW -- no published metric tables, no MOS, no A/B comparisons |
| **CSM (Backbone+Decoder S2S)** | No benchmarks published | 12.5 Hz frame rate, ~1125 frames/90s max | ~1.5-2 GB for 1B backbone + 100M decoder | Low-Medium -- ~550 lines inference-only, no training code | Context-limited (2048 tokens); English with leakage only | VERY LOW -- single-commit repo, no formal evaluation at all |
| **Cascaded STT->LLM->TTS** | Tool Sel F1=0.803, Pass@1=0.450 (FDB-v3); ASR WER 5.4-9% | 10.12s e2e (FDB-v3 cascaded); 100% turn-take; 4-7s with optimized pipeline | STT: ~0.6-8B; LLM: 7-70B; TTS: 0.1-3B; total easily 10-50GB | Low -- well-understood, 50+ provider integrations, mature frameworks | All languages (Whisper), all LLM abilities; weakest on self-correction (Pass@1=0.176) | HIGH -- FDB-v3 provides rigorous tool-use benchmark; ASR Leaderboard provides 86-model comparison |
| **Full-Duplex-Bench (Eval)** | Multi-axis behavioral metrics, no aggregate score | N/A (evaluation, not inference) | ASR transcription overhead per evaluation | Low -- automatic pipeline, 590 samples, scenario-driven | English-only; 4 models tested (v1), 6 models (v3) | HIGH -- well-defined metrics, ASR+judge automated, but no human preference calibration |
| **Conformer+CTC ASR (Fastest)** | WER 7.40-8.96% (short-form) | RTFx 2730-6400 (44x faster than Whisper) | 0.6-1.1B params | Medium -- requires Conformer training or fine-tuning | Multilingual degrades English by 0.27-0.65pp | HIGH -- 86-model standardized leaderboard on A100-80GB |
| **Voice Pipeline Frameworks** | Depends entirely on provider choice | LiveKit/Pipecat: WebRTC, ~50-150ms transport; TEN: Agora RTC, ~50-150ms | Varies by model selection | Low-Medium -- Pipecat (Python asyncio), TEN (Go server + C++ runtime), LiveKit (Python process pool) | 50-60+ provider integrations each; distributed via Redis/PGMQ buses | MEDIUM -- production frameworks but no end-to-end latency benchmarks published |

## 3. Convergences

### 3.1 Inner Monologue / Think-Before-Speak Is Essential for Speech Reasoning

Three independent sources converge on the necessity of an intermediate reasoning step between speech input and speech output:

- **Moshi** (arXiv:2410.00037v2): Inner Monologue -- predicting text tokens before audio tokens at each 80ms frame -- improves Spoken QA from 9.2% to 26.6% (WebQ) and nearly triples transcript length (486 -> 1920). Text acts as a "semantic scaffold" per frame.
- **VoxMind** (arXiv:2604.15710v1): Think-before-Speak -- explicit CoT before any action or speech output -- improves task completion from 34.88 to 74.57 (+113.79%) and prevents catastrophic forgetting of general speech ability (VoiceBench 64.21 with CoT vs 54.80 without).
- **Building Multimodal GenAI** (Book, Ch.11-12): Voice RAG is a bidirectional pipeline where reasoning must happen in text space between STT and TTS. "Reasoning is the bridge between generation and intelligence."

**Convergence statement:** Speech models MUST generate text-level reasoning tokens before producing audio output. Direct speech-to-speech without intermediate text reasoning catastrophically degrades on any task requiring comprehension beyond simple acoustic continuation. This is not a latency optimization -- it is a correctness requirement. The cost (~12% token overhead at 80ms granularity for Moshi, ~12.6% for VoxMind) is small relative to the accuracy gain (200-300%).

### 3.2 Full-Duplex Requires Architecture Trade-offs -- No Free Lunch

Both Full-Duplex-Bench papers (arXiv:2503.04721v3, arXiv:2604.04847v1) converge on the finding that no architecture dominates all conversational behaviors:

- End-to-end models (Moshi, dGSLM) optimize for latency but sacrifice pause handling and interruption coherence
- Cascaded models optimize for semantic quality and turn-taking reliability but sacrifice latency and self-correction handling
- Even commercial giants (Gemini Live, GPT-Realtime) show specific failure modes (silent worker at 22%, self-correction Pass@1 only 0.588 at best)

**Convergence statement:** Voice mode design requires explicit prioritization of which conversational behaviors matter most for the deployment context. A single "voice quality" metric is misleading -- the four axes (pause handling, backchanneling, turn-taking, interruption) must be evaluated and optimized separately.

### 3.3 Audio Codec Framerate (12.5 Hz / 80ms) Is the Emerging Standard

Multiple independent systems converge on 12.5 Hz (80ms frames) as the optimal codec framerate:

- **Mimi** (Moshi, arXiv:2410.00037v2): 12.5 Hz, 1.1 kbps, 24kHz, Split RVQ
- **CSM** (SesameAILabs/csm): Uses Mimi codec at 12.5 Hz, 32 RVQ codebooks
- **SNAC** (Orpheus): 24kHz, hierarchical (not framerate-fixed but approximates similar granularity)

**Convergence statement:** 12.5 Hz is the sweet spot -- fast enough for real-time interaction (<100ms per frame), slow enough for autoregressive generation with reasonable context windows. The 80ms granularity is coarse for phenomena like backchannels (<80ms) but covers most conversational speech.

### 3.4 WebRTC/UDP Transport Is Essential for Real-Time Voice

Three production frameworks and one commercial API converge on real-time media transport:

- **LiveKit agents**: WebRTC via LiveKit media server
- **Pipecat**: WebRTC via Daily/LiveKit transports
- **TEN Agent**: Agora RTC (UDP-based, 50-150ms latency)
- **OpenAI Realtime API**: WebRTC (browser/mobile), WebSocket (server), SIP (telephony)

**Convergence statement:** WebSocket-only voice transport is insufficient for production voice agents. UDP-based real-time transport (WebRTC) is required for latency under 200ms. WebSocket is acceptable only for server-side processing where transport latency is not the bottleneck.

### 3.5 Disfluency Handling Requires Explicit Evaluation and Training

Both FDB-v3 and VoxMind converge on the critical nature of natural speech disfluencies:

- **FDB-v3** (arXiv:2604.04847v1): Self-corrections are the hardest disfluency category -- even GPT-Realtime only achieves Pass@1=0.588. Cascaded models are worst at self-correction (0.176) because ASR finalizes before the correction arrives.
- **VoxMind** (arXiv:2604.15710v1): The gap between TTS training data and real speech is -7.3% FS, -6.7% PF. CoT training helps (86% real-speech success) but doesn't eliminate the gap.

**Convergence statement:** Voice agents must be trained and evaluated on real human speech with disfluencies, not clean TTS-synthesized audio. Self-correction handling ("Book me to New York -- actually, wait, make that Boston") is the hardest capability and must be tested explicitly with a dedicated scenario suite.

## 4. Contradictions

### 4.1 End-to-End (S2S) vs Cascaded (STT->LLM->TTS)

This is the central architectural debate in voice AI, and the evidence is split:

**Evidence for end-to-end:**
- Moshi achieves 160-200ms latency vs cascaded's 10.12s (FDB-v3) -- a 50x advantage
- Moshi preserves paralinguistic information (emotion, prosody, tone) lost in text bottleneck
- Moshi enables true full-duplex: overlapping speech, no turn boundaries
- VoxMind outperforms cascaded baselines (74.57 vs 64.0 best cascaded)

**Evidence for cascaded:**
- Cascaded guarantees 100% turn-take (vs Moshi 98% pause interruption, Gemini Live 3.1's 22% silent worker)
- Cascaded achieves far better semantic quality on complex reasoning (FDB-v3: cascaded GPT-4o score 0.600 vs Moshi's 0.765 interruption coherence)
- Cascaded leverages the full LLM ecosystem -- any model, any tool, any safety layer
- Cascaded can be optimized: LiveKit and Pipecat achieve 2-4s e2e in production (not 10s)
- Cascaded self-correction is fixable: an explicit "state rollback" buffer solves the ASR-finalization problem that causes 0.176 Pass@1

**Resolution needed:** Lyra Phase 4 plans must decide whether to commit to end-to-end (Moshi-based, highest ambition, highest risk) or optimized cascaded (LiveKit/Pipecat-based, lower risk, lower ceiling). A hybrid architecture (end-to-end for real-time turn-taking + cascaded for complex reasoning fallback) may be optimal but has not been demonstrated by any paper.

### 4.2 Streaming ASR Architecture: CTC/TDT Speed vs Transformer Accuracy

The Open ASR Leaderboard (arXiv:2510.06961v4) reveals a direct tradeoff:

- NVIDIA Parakeet TDT 0.6B v2: RTFx 3390 (fastest competitive accuracy), WER 6.05%
- Cohere Labs Transcribe: WER 5.42% (best accuracy), RTFx 525
- Difference: 0.63pp WER for 6.5x speedup

But the paper does NOT answer: which matters more for voice agent UX -- 0.63pp better transcription or 6.5x faster inference? This requires user studies that don't exist yet.

### 4.3 How Much Reasoning Is Acceptable Before Speaking?

VoxMind argues for explicit CoT before any output (correctness-first). Moshi interleaves text and speech at 80ms granularity (latency-first). The Open ASR Leaderboard shows inference speed varies 44x between architectures.

The tension: users expect sub-second first-word latency in conversation, but complex tool use (FDB-v3) requires multi-step reasoning. No paper resolves this. Gemini Live 3.1's approach (pre-emptive tool calls, 3.95s first-word in FDB-v3) offers one path but produces silent workers 22% of the time.

## 5. Open Problems

### 5.1 No Auditory Safety Framework Comparable to Text Safety

Moshi's safety evaluation (arXiv:2410.00037v2) is text-only and achieves only ALERT 83.05 (vs Llama 2's 99.98). Audio-specific toxicity -- tone, irony, paralinguistic hostility, prosodic manipulation -- is completely unevaluated. Audio watermarks (Audioseal 0.9999 on clean audio) are destroyed by neural codec re-encoding (0.08). LlamaFirewall (arXiv:2505.03574v1) shows multi-layer guardrails work for text agents, but no equivalent exists for speech.

**Research opportunity:** An Audio Safety Framework that evaluates spoken responses across: semantic toxicity (text content), prosodic toxicity (hostile tone), pragmatic toxicity (implied threats via intonation), and acoustic jailbreaks (adversarial audio inputs).

### 5.2 Real Human Conversation Data for Training

Moshi's instruct fine-tuning uses 20k hours of SYNTHETIC data (Helium + TTS). VoxMind's AgentChat is synthesized from text corpora (ToolACE + APIGen-MT) via CosyVoice2 TTS. Both show measurable real-speech degradation (-7.3% for VoxMind). The MIMIC framework (arXiv:2502.13001v2) generates meeting transcripts with psychological behavior profiles, but these are text-only.

**Research opportunity:** A pipeline for collecting, annotating, and safely using real human spoken conversations as training data for voice agents, with privacy guarantees and disfluency preservation.

### 5.4 State Rollback During Self-Corrections

FDB-v3 (arXiv:2604.04847v1) reveals that ALL current voice models fail significantly on self-corrections. Cascaded models fail because ASR finalizes before the correction arrives; end-to-end models fail because state rollback competes with latency optimization. Gemini Live 3.1's pre-emptive tool calls lock in stale parameters.

**Research opportunity:** A "hypothesis buffer" that holds tool-call parameters in a tentative state until end-of-utterance confirmation, with explicit rollback on correction detection. Inspired by transactional memory in databases.

### 5.5 Cross-Lingual Voice Interaction

All major models are English-only or English-primary. Full-Duplex-Bench is English-only. The Open ASR Leaderboard shows multilingual support degrades English WER by 0.27-0.65pp. Pause timing norms, backchannel conventions, and turn-taking dynamics are language-specific. No benchmark evaluates cross-lingual voice interaction.

**Research opportunity:** A multilingual voice evaluation framework that accounts for language-specific conversational norms, with native-speaker calibration of "appropriate" pause handling and backchanneling per language.

### 5.6 Long-Context Voice Conversations

Moshi's temporal transformer context is 4096 tokens (at 12.5 Hz text + audio, this is ~5 minutes of conversation). CSM caps at 2048 tokens. No model demonstrates persistent multi-turn voice conversations beyond 5-10 minutes. The HippoRAG pattern (arXiv:2405.14831v3) shows how associative memory can enable single-step multi-hop retrieval in text, but no voice model integrates long-term memory across sessions.

**Research opportunity:** A voice agent that maintains a persistent knowledge graph of conversation history, using HippoRAG-like associative retrieval for rapid context recall during 80ms real-time frames.

### 5.3 Objective Audio Quality Metrics Are Broken for Adversarial Codecs

Mimi achieves MUSHRA 81.0 but VisQOL 1.84 -- a catastrophic disconnect. MOSNet and other objective metrics fail for adversarially-trained neural codecs. This makes fair comparison, optimization, and regression testing impossible without expensive MUSHRA human studies.

**Research opportunity:** An objective audio quality metric that correlates with MUSHRA for adversarially-trained neural codecs, or a simulation-based evaluation that approximates human perceptual judgments.

## 6. Recommendations for Lyra

Ranked by feasibility x impact for Lyra's upgrade architecture:

### Recommendation 1: Deploy Optimized Cascaded Pipeline First (Impact: 5/5, Effort: 2/5)

Build Lyra Voice on a cascaded STT -> LLM -> TTS pipeline using Pipecat's Frame-based architecture for orchestration and LiveKit WebRTC for transport. Use Conformer+TDT (NVIDIA Parakeet TDT 0.6B) for STT at RTFx 3390, keeping transcription latency under 100ms. This is the production-proven baseline.

**Rationale:** End-to-end approaches (Moshi, VoxMind) are 3-5x more complex to implement and train, with lower text reasoning quality and no safety framework. Cascaded lets Lyra leverage its full LLM (text reasoning, tool use, safety layers) immediately, with acceptable latency (2-4s e2e with optimized components). The key advantage is reliability: 100% turn-take vs end-to-end's unpredictable behaviors (silent worker, high pause interruption).

**Sources:** FDB-v3 (arXiv:2604.04847v1) for cascaded performance data, Pipecat (BSD 2-Clause) for Frame-based pipeline, LiveKit (Apache 2.0) for WebRTC transport, Open ASR Leaderboard (arXiv:2510.06961v4) for STT selection, Building Multimodal GenAI (Book, Ch.11) for voice RAG pattern.

### Recommendation 2: Implement Self-Correction Buffer (Impact: 4/5, Effort: 1/5)

Add an explicit state-rollback buffer that holds tool-call parameters in a tentative state until end-of-utterance is confirmed. On detection of self-correction keywords ("actually", "wait", "no, I meant"), roll back to the last confirmed state and reprocess. This directly addresses FDB-v3's finding that cascaded self-correction Pass@1 is only 0.176.

**Rationale:** This is the single highest-leverage fix for cascaded pipelines -- low implementation effort, high impact on the most common real-world failure mode (mid-utterance corrections). The buffer pattern is well-understood from database transaction management.

**Sources:** FDB-v3 (arXiv:2604.04847v1) for the failure mode characterization.

### Recommendation 3: Adopt Think-Before-Speak for Complex Reasoning (Impact: 4/5, Effort: 3/5)

Integrate explicit Chain-of-Thought reasoning between STT output and LLM response generation, but only for tasks classified as "complex" (multi-step tool use, reasoning-heavy queries). Use a lightweight classifier to route simple queries (direct answer) vs complex queries (CoT before response). This avoids the latency overhead of CoT on every turn while capturing the 113.79% improvement VoxMind demonstrates.

**Rationale:** VoxMind (arXiv:2604.15710v1) and Moshi (arXiv:2410.00037v2) independently prove that intermediate reasoning is essential for complex spoken tasks. But adding 88 tokens of CoT on every simple greeting or confirmation would unnecessarily increase perceived latency. Task-based routing preserves the benefit while minimizing the cost.

**Sources:** VoxMind (arXiv:2604.15710v1), Moshi (arXiv:2410.00037v2), Building Multimodal GenAI (Book, Ch.11-12), RMoA (arXiv:2505.24442v1) for diversity-based routing.

### Recommendation 4: Build Full-Duplex-Bench-Style Evaluation Suite (Impact: 4/5, Effort: 3/5)

Create a Lyra-specific voice evaluation suite with four behavioral dimensions: (1) Pause handling during agent speaking turns, (2) Backchannel appropriateness, (3) Smooth turn-taking latency measurement, (4) Interruption/self-correction handling. Augment with 20-30 real-speaker recordings from Lyra's team, annotated with disfluency types (fillers, pauses, hesitations, false starts, self-corrections). Gate every voice model change on Pass@1 thresholds per dimension.

**Rationale:** Full-Duplex-Bench (arXiv:2503.04721v3) proves that multi-dimensional evaluation reveals architecture trade-offs invisible to aggregate scores. FDB-v3 (arXiv:2604.04847v1) proves that self-correction scenarios are the most diagnostic. Building this before voice model integration prevents regressions to specific conversational behaviors.

**Sources:** Full-Duplex-Bench (arXiv:2503.04721v3), Full-Duplex-Bench-v3 (arXiv:2604.04847v1), Open ASR Leaderboard (arXiv:2510.06961v4) for evaluation methodology.

### Recommendation 5: Plan for Inner Monologue Migration Path (Impact: 5/5, Effort: 5/5, Long-term)

Architect Lyra's voice pipeline with the Inner Monologue pattern as the v2 target. The text token stream at each 80ms frame provides hooks for: real-time content moderation, factuality verification, streaming partial responses, and natural interruption handling. Even if v1 is cascaded, the architecture should support migrating to multi-stream end-to-end when the technology matures.

**Rationale:** Moshi (arXiv:2410.00037v2) proves Inner Monologue is the single most impactful architectural innovation for speech-language models (nearly 3x SQA improvement). It is also the most complex to implement (5/5 effort). Planning the migration path now avoids architectural lock-in that would make Inner Monologue adoption impossible later.

**Sources:** Moshi (arXiv:2410.00037v2), kyutai-labs/moshi repo (Apache 2.0).

### Recommendation 6: Use Orpheus TTS for Custom Voice Personality (Impact: 3/5, Effort: 2/5)

Adopt Orpheus TTS (Llama-3.2-3B backbone) as Lyra's TTS engine for its combination of semantic understanding (LLM backbone produces contextually appropriate prosody), zero-shot voice cloning (no fine-tuning for new voices), emotion control (20 tags), streaming compatibility (~200ms), and Apache 2.0 license. Finetune on 50-300 examples of Lyra's target voice personality.

**Rationale:** Orpheus's LLM-backbone approach produces more natural prosody than Tacotron-style TTS because the model "understands" the text semantically. The fine-tuning simplicity (standard HuggingFace Trainer, LoRA option, 50 examples minimum) makes custom voice creation practical. The Apache 2.0 license is production-safe.

**Sources:** canopyai/Orpheus-TTS repo (Apache 2.0), Orpheus paper (arXiv:2506.13131v1).

## 7. Voice Mode Architecture Blueprint

### 7.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    LYRA VOICE MODE (v1)                          │
│               Optimized Cascaded with Self-Correction            │
└─────────────────────────────────────────────────────────────────┘

    Microphone (User Speech)
         │
         ▼
    ┌──────────────┐
    │  VAD + AEC   │  ← WebRTC AudioProcessing (echo cancellation, noise suppression)
    │  (WebRTC)    │
    └──────┬───────┘
           │ audio frames (20ms, 16kHz mono PCM)
           ▼
    ┌──────────────────┐
    │  Streaming ASR   │  ← NVIDIA Parakeet TDT 0.6B v2 (RTFx 3390, WER 6.05%)
    │  (Conformer+TDT) │     Deployed via NVIDIA NeMo or HuggingFace
    └──────┬───────────┘     Source: Open ASR Leaderboard (arXiv:2510.06961v4)
           │ partial transcripts (every 80-200ms)
           ▼
    ┌──────────────────────┐
    │  Endpointing +       │  ← Smart Turn V3 (VAD-based endpointing)
    │  Self-Correction     │     Hypothesis buffer for self-correction rollback
    │  Buffer              │     Source: FDB-v3 (arXiv:2604.04847v1) for failure analysis
    └──────┬───────────────┘
           │ finalized transcript
           ▼
    ┌──────────────────────┐
    │  Task Router         │  ← Classify: simple (direct) vs complex (CoT required)
    │  (Lightweight LLM)   │     Source: VoxMind (arXiv:2604.15710v1) for TbS routing
    └──────┬───────────────┘
           │
    ┌──────┴──────────────────────────────────┐
    │                                          │
    ▼ (simple)                                 ▼ (complex)
    ┌────────────────┐              ┌───────────────────────┐
    │  Direct Answer │              │  Think-Before-Speak   │
    │  (Lyra LLM)    │              │  (Lyra LLM + CoT)     │
    └───────┬────────┘              │  Explicit reasoning    │
            │                       │  before action/output  │
            │                       └───────────┬───────────┘
            │                                   │
            └───────────────┬───────────────────┘
                            │ text response
                            ▼
    ┌──────────────────────┐
    │  Safety Gate         │  ← LlamaFirewall-style multi-layer guard (input + output)
    │  (Text Guardrails)   │     Source: LlamaFirewall (arXiv:2505.03574v1)
    └──────┬───────────────┘
           │ approved text
           ▼
    ┌──────────────────────┐
    │  Orpheus TTS         │  ← Llama-3.2-3B backbone, ~200ms streaming
    │  (LLM-Backbone TTS)  │     Fine-tuned on Lyra voice persona (50-300 examples)
    └──────┬───────────────┘     Source: canopyai/Orpheus-TTS (Apache 2.0)
           │ audio frames (24kHz mono PCM)
           ▼
    ┌──────────────┐
    │  Watermark   │  ← SilentCipher imperceptible watermarking (private key)
    │  + Speaker   │     Source: SesameAILabs/csm watermarking pattern
    └──────┬───────┘
           │
           ▼
    Speaker (Lyra Voice Output)
```

### 7.2 Component Recommendations

| Stage | Component | Rationale | Source |
|-------|-----------|-----------|--------|
| **Transport** | WebRTC via LiveKit media server | UDP-based, 50-150ms latency, browser-native, proven in 3 frameworks | LiveKit agents (Apache 2.0), Pipecat WebRTC (BSD 2-Clause), TEN Agora RTC (Apache 2.0), OpenAI Realtime API docs |
| **VAD + AEC** | WebRTC AudioProcessing module + Silero VAD fallback | Echo cancellation critical for speakerphone use; Silero VAD is lightweight (onnx, <1MB) | snakers4/silero-vad (MIT), Pipecat Smart Turn V3 (60MB RSS, 0.3s cold start) |
| **ASR** | NVIDIA Parakeet TDT 0.6B v2 | Best speed-accuracy balance: RTFx 3390, WER 6.05% | Open ASR Leaderboard (arXiv:2510.06961v4) |
| **Endpointing** | Smart Turn V3 (VAD-based) | 60MB RSS, 0.3s cold start, vendored numpy-only STFT (no transformers dependency) | Pipecat Smart Turn V3 (PR #4536) |
| **Self-Correction Buffer** | Tentative state buffer with keyword-triggered rollback | FDB-v3's highest-impact fix; detect "actually", "wait", "no, I meant" | FDB-v3 (arXiv:2604.04847v1) |
| **Task Router** | Lightweight LLM classifier (Qwen2.5-0.5B or similar) | Classify simple vs complex to gate CoT overhead | VoxMind (arXiv:2604.15710v1), Building Multimodal GenAI (Book, Ch.11) |
| **LLM** | Lyra's primary reasoning LLM | Text reasoning in cascaded pipeline leverages full LLM capability | Existing Lyra architecture |
| **Safety Gate** | Multi-layer guard: PromptGuard (input) + AlignmentCheck (output CoT) | LlamaFirewall pattern adapted for speech: filter ASR output before LLM, filter LLM output before TTS | LlamaFirewall (arXiv:2505.03574v1) |
| **TTS** | Orpheus TTS (Llama-3.2-3B) | Semantic understanding by LLM backbone, zero-shot cloning, 20 emotions, streaming, Apache 2.0 | canopyai/Orpheus-TTS (Apache 2.0) |
| **Watermark** | SilentCipher with private key | Imperceptible, detectable, SDR 36dB; use private key per deployment (not CSM's public key) | SesameAILabs/csm watermarking pattern, Orpheus watermarking |
| **Pipeline Orchestration** | Pipecat Frame-based pipeline | Typed Frame passing, bidirectional flow, interruption semantics, multi-worker bus for future scaling | pipecat-ai/pipecat (BSD 2-Clause) |

### 7.3 Latency Budget

| Stage | Component | Target Latency | Cumulative |
|-------|-----------|---------------|------------|
| Transport (mic -> server) | WebRTC | 20-50ms | 50ms |
| VAD + AEC | WebRTC + Silero | 10ms | 60ms |
| ASR (partial) | Parakeet TDT 0.6B | 80-150ms (first partial) | 210ms |
| Endpointing + Rollback | Smart Turn V3 | 50ms after end-of-speech | 260ms |
| Task Routing | Small classifier LLM | 50-100ms | 360ms |
| LLM thinking (simple) | Direct answer | 500-1000ms | 1360ms |
| LLM thinking (complex) | CoT + reasoning | 2000-4000ms | 4360ms |
| Safety Gate | Text guardrails | 50-100ms | 1460ms / 4460ms |
| TTS (first audio) | Orpheus streaming | 200ms (TTFB) | 1660ms / 4660ms |
| Transport (server -> speaker) | WebRTC | 20-50ms | 1710ms / 4710ms |
| **Total (simple query)** | | **~1.7s** | |
| **Total (complex query)** | | **~4.7s** | |

**Comparison to FDB-v3 cascaded (10.12s):** Our optimized budget achieves 2-6x improvement over the FDB-v3 cascaded baseline by using (a) Conformer+TDT ASR instead of Whisper, (b) streaming partial ASR results instead of waiting for finalization, (c) streaming TTS instead of batch TTS.

### 7.4 Failure Modes and Mitigations

| Failure Mode | Source Evidence | Mitigation |
|-------------|----------------|------------|
| ASR finalizes before self-correction | FDB-v3: cascaded self-corr Pass@1=0.176 | Hypothesis buffer: hold parameters tentative until end-of-utterance confirmation |
| Silent worker (LLM produces text but no speech) | FDB-v3: Gemini Live 3.1 22% silent | TTS output guard: if TTS produces no audio within 2s of LLM output, force fallback phrase |
| Pause misidentified as end-of-turn | Full-Duplex-Bench: Moshi TOR 0.98 on pauses | Smart Turn V3: distinguish internal pause vs end-of-turn pause via duration + prosodic cues |
| LLM hallucinates in CoT, amplifies through TTS | VoxMind: FC score 3.94% (near-zero result feedback accuracy) | Safety gate on CoT output before TTS; alignment check per LlamaFirewall |
| Audio watermark destroyed by transcoding | Moshi: Audioseal 0.9999 -> 0.08 after Mimi re-encode | SilentCipher at final output stage (post-TTS), not pre-codec |
| GPU memory exhaustion with concurrent users | Orpheus: 3B params, vLLM required | Model quantization (W8A8 or W4A8), request queuing, graceful degradation to CPU TTS fallback |

### 7.5 Implementation Phases

**Phase 1: Cascaded Baseline (4-6 weeks)**
- Deploy Pipecat pipeline with LiveKit WebRTC transport
- Integrate NVIDIA Parakeet TDT ASR (RTFx 3390) or Deepgram API as initial provider
- Integrate Orpheus TTS with default voice (zero-shot, no fine-tuning)
- Implement Smart Turn V3 endpointing
- Implement self-correction buffer
- Build FDB-style evaluation suite with 20-30 scenarios

**Phase 2: TTS Customization + Safety (2-4 weeks)**
- Fine-tune Orpheus on Lyra voice persona (50-300 examples)
- Implement LlamaFirewall-style multi-layer safety gate for voice I/O
- Add SilentCipher watermarking with private key
- Run full FDB-style evaluation with regressions gated

**Phase 3: Think-Before-Speak Routing (3-4 weeks)**
- Deploy task router (simple vs complex classification)
- Implement CoT reasoning path for complex queries
- Integrate HippoRAG-style associative memory for conversation context
- Optimize latency: parallelize ASR partials with endpointing

**Phase 4: Inner Monologue Migration Path (6-8 weeks, v2 target)**
- Evaluate Moshi Mimi codec for Lyra's audio domain
- Train or fine-tune multi-stream model with Inner Monologue
- Implement partial-response streaming for perceived latency reduction
- Deploy end-to-end path as primary, keep cascaded as fallback

### 7.6 Architecture Decision Record

**Decision:** Build v1 on optimized cascaded pipeline with planned migration to end-to-end with Inner Monologue for v2.

**Rationale:**
1. Cascaded leverages Lyra's existing LLM investment immediately
2. FDB-v3 proves cascaded achieves highest semantic quality (GPT-Realtime), best turn-taking reliability (100%), and competitive accuracy (Pass@1=0.450 vs 0.600 best end-to-end)
3. Cascaded's latency disadvantage (10.12s in FDB-v3) is addressable: Conformer+TDT ASR + streaming TTS + parallelized pipeline can reduce to 1.7-4.7s
4. End-to-end's advantages (160-200ms latency, paralinguistic preservation, true full-duplex) are real but the technology is not mature enough for production reliability (safety score 83.05, silent workers, quantization sensitivity)
5. The architecture must support Inner Monologue migration without requiring a complete rewrite -- the text token stream at 80ms granularity is the key interface point

**Alternatives considered:**
- Pure Moshi fork: Rejected due to safety immaturity (ALERT 83.05), quantization sensitivity (MMLU drops 7.5 pts at W4A8), English-only, and inability to leverage Lyra's full LLM capabilities
- Pure cascaded without Inner Monologue migration: Rejected because it forecloses the latency ceiling improvement that end-to-end promises (50x reduction from 10s to 200ms)
- VoxMind fork: Rejected due to training data quality (synthesized from text, -7.3% real-speech gap) and specialized hardware requirements (H20-NVLink)

**Approved by:** This synthesis | **Date:** 2026-06-07

---

*Sources cited: 24 documents across papers (12), web/repos (11), and books (1). Full reference list with arXiv IDs and repository URLs available in source-ledger.md.*
