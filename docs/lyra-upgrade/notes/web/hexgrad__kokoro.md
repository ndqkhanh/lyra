# hexgrad/kokoro -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** Kokoro-82M is an open-weight text-to-speech (TTS) model with 82 million parameters. Despite its small footprint, it delivers quality comparable to much larger models (e.g., Bark, Tortoise-TTS) while being significantly faster and more cost-efficient. Weights are Apache 2.0 licensed, enabling unrestricted deployment.

**How the code really works (end-to-end data flow):**

1. **Text input** is received by `KPipeline.__call__()`.
2. **Grapheme-to-Phoneme (G2P) conversion:** `KPipeline` delegates to the `misaki` library. For American/British English (`misaki[en]`), this uses a transformer-based G2P with espeak-ng fallback. For other languages, it uses `espeak.EspeakG2P` or dedicated Japanese/Mandarin G2P modules. The G2P outputs a list of `MToken` objects carrying text, phonemes, and whitespace info.
3. **Chunking:** English text is chunked using a "waterfall" strategy -- the pipeline scans for sentence boundaries (`!.?...` -> `:;` -> `,--`) and splits phoneme strings before they exceed 510 characters (the model's context limit). Non-English text is split on sentence boundaries every ~400 graphemes, then phonemized.
4. **Voice loading:** Voice names (e.g., `af_heart`) are lazily downloaded from Hugging Face Hub as `.pt` files. Each voice is a 256-dimensional style tensor (first 128 dims = timbre embedding, last 128 = prosody style). Multiple voices can be averaged by comma-separated names.
5. **KModel inference:** The phoneme string is tokenized via a vocab dict, prepended/appended with BOS/EOS tokens, and passed as `input_ids` to the neural network. The model:
   - Encodes phonemes through a **CustomAlbert** (ALBERT transformer) into contextual embeddings
   - Projects through a **ProsodyPredictor** that uses a duration encoder, bidirectional LSTM, and duration projection head to predict per-phoneme duration
   - Uses predicted durations to create an alignment matrix that expands token embeddings to the time domain
   - Predicts **F0 (pitch) and N (noise) contours** through AdaINResBlk1d blocks conditioned on the style vector
   - Feeds the expanded representation + F0 + noise into a **hi-fi iSTFT-based decoder** (adapted from StyleTTS2) that outputs raw 24kHz waveform audio
6. **Timestamps:** When English tokens are used, predicted durations are mapped back to tokens to produce per-token start/end timestamps (in seconds).

## 2. Architecture & Core Modules

**Entry points:**
- `kokoro/__main__.py` -- CLI interface (`python3 -m kokoro --text "..." -o output.wav`)
- `kokoro/__init__.py` -- Exports `KModel` and `KPipeline`, configures `loguru` logger
- `kokoro/pipeline.py` -- `KPipeline` class: G2P, voice management, chunking, text-to-phonemes-to-audio orchestration
- `kokoro/model.py` -- `KModel` class: pure PyTorch neural network, loads weights from HF Hub, defines `forward()` for phonemes->audio

**Core modules (data flow order):**

| File | Role | Key Classes |
|------|------|-------------|
| `pipeline.py` | Orchestration & G2P | `KPipeline`, `KPipeline.Result` |
| `model.py` | Neural model wrapper | `KModel`, `KModelForONNX` |
| `modules.py` | Sub-modules (from StyleTTS2) | `TextEncoder`, `ProsodyPredictor`, `DurationEncoder`, `CustomAlbert` |
| `istftnet.py` | Decoder (from StyleTTS2) | `Decoder`, `Generator`, `AdaINResBlk1d`, `AdaINResBlock1`, `TorchSTFT`, `SineGen`, `SourceModuleHnNSF` |
| `custom_stft.py` | ONNX-safe STFT | `CustomSTFT` (conv1d-based, no complex ops) |

**Supporting files:**
- `demo/app.py` -- Gradio web demo (Hugging Face Space)
- `examples/export.py` -- ONNX export utility
- `examples/device_examples.py` -- Device selection/performance testing
- `examples/make_triton_compatible.py` -- Triton inference server adaptation
- `examples/phoneme_example.py` -- Raw phoneme input and timestamp extraction
- `tests/test_custom_stft.py` -- STFT reconstruction tests
- `kokoro.js/` -- JavaScript sibling package (separate implementation)

**Key dependencies (from pyproject.toml):**
- `torch`, `numpy`, `transformers` -- neural compute + ALBERT
- `misaki[en]>=0.9.4` -- G2P engine (also supports `[ja]`, `[zh]` extras)
- `huggingface_hub` -- weight/voice downloading
- `loguru` -- logging
- Python >=3.10, <3.14

**Architecture pattern:** Pipeline-Model separation. `KPipeline` handles all language-specific pre-processing (G2P, chunking, voice management). `KModel` is a pure language-agnostic neural network. Multiple `KPipeline` instances (one per language) can share a single `KModel` to avoid redundant memory allocation.

## 3. Performance/Benchmarks

From the repository and associated community benchmarks:

- **Model size:** 82 million parameters (weights ~330 MB)
- **Output format:** 24 kHz mono 16-bit WAV
- **Context window:** 510 phonemes per inference pass
- **Inference speed:** Real-time factor < 0.1 on GPU (NVIDIA A10G/T4), approximately 0.1-0.2 on CPU (Apple M-series)
- **Memory:** ~600 MB VRAM during inference (FP32); less with FP16
- **Voice library:** ~30+ pre-built voices (American/British English, across male/female)
- **Language support:** 9 languages (American English, British English, Spanish, French, Hindi, Italian, Brazilian Portuguese, Japanese, Mandarin Chinese)

The `examples/device_examples.py` script provides a structured timing harness, but the repo does not ship a formal benchmark suite with published latency numbers.

## 4. Trade-offs

**Wins:**

1. **Size-quality ratio.** 82M parameters deliver output that many listeners rank near or above models 5-10x larger (Bark: ~1B, Tortoise: ~400M). This is the repo's core differentiator.
2. **Apache 2.0 license.** Full commercial freedom, no attribution requirement in all contexts, no "research only" restrictions. This is rare in the TTS space (most alternatives use CC-BY-NC or similar).
3. **Deployment flexibility.** Runs on CPU, GPU (CUDA), Apple MPS (with env var workaround), and exports to ONNX for Triton/onnxruntime serving. The `CustomSTFT` module was specifically written to avoid complex-number ops that break ONNX export.
4. **Easy pip install.** `pip install kokoro` with automatic weight downloading from HF Hub. No manual checkpoint management.
5. **Voice averaging.** Multiple voices can be blended by comma-separated names, creating novel timbres without retraining.

**Loses:**

1. **G2P dependency chain.** English requires `misaki[en]` + espeak-ng for OOD fallback. Japanese requires `misaki[ja]` (additional install). Chinese requires `misaki[zh]`. espeak-ng must be installed as a system package (apt/brew/msi), adding friction especially on Windows.
2. **Non-English chunking is simplistic.** Unlike English which has a sophisticated "waterfall" sentence-boundary chunking strategy, non-English languages use a fixed 400-character sentence-split approach, then phonemize. This may degrade prosody on very long texts.
3. **510 phoneme context limit.** Long-form content requires chunking, and while the pipeline handles this internally, it means the model has no cross-chunk context. This can affect prosodic consistency across sentence boundaries.
4. **No streaming optimization.** The primary `__call__` generator yields full audio segments; there is no token-by-token streaming decoder or low-latency first-chunk optimization.
5. **MPS GPU acceleration is fragile.** Requires `PYTORCH_ENABLE_MPS_FALLBACK=1` environment variable. The code explicitly checks for this and raises an error if it's not set.
6. **No training code in this repo.** The repo is purely an inference library. Training was done by the author (@hexgrad / @yl4579) using the StyleTTS2 training framework, which is not included.
7. **Demo Gradio Space has ZeroGPU quota limits.** The HF Space demo prominently surfaces this limitation with CPU fallback logic.

**Design decisions visible in the code:**
- `loguru` logging is **disabled by default** (`logger.disable("kokoro")` in `__init__.py`). This prevents logging overhead in production but makes debugging non-trivial (user must modify source or set environment).
- The `disable_complex` flag in KModel switches between `TorchSTFT` (PyTorch native, complex tensors) and `CustomSTFT` (conv1d-based, ONNX-friendly). This is a classic inference-vs-exportability trade-off.
- Voice mismatch generates only a warning, not an error (loading an English voice into a French pipeline), prioritizing flexibility over guardrails.
- The `KModelForONNX` wrapper explicitly strips the `return_output` abstraction from KModel, showing that optimization for serving sometimes requires exposing lower-level APIs.

## 5. Design Rationale

The codebase rationale can be inferred from the architecture:

1. **Language-agnostic model, language-specific G2P.** The neural network (`KModel`) operates purely on phoneme sequences and style vectors -- it has no concept of language. All language-specific behavior is pushed into `KPipeline` and the `misaki` G2P library. This means the model weights work for any language that can be phonemized, without retraining.

2. **StyleTTS2 foundation.** The architecture is adapted from [yl4579/StyleTTS2](https://github.com/yl4579/StyleTTS2), a known high-quality TTS architecture. The key innovation of StyleTTS2 is using style vectors to condition both prosody prediction and waveform generation, enabling efficient voice adaptation without finetuning.

3. **Chunk-and-concatenate.** Rather than designing a model with infinite context, Kokoro uses a fixed 510-phoneme window and handles long text by chunking at natural boundaries. This keeps the model tiny (82M) and fast, at the cost of cross-chunk consistency.

4. **ONNX-first for production.** The presence of `CustomSTFT`, `KModelForONNX`, `disable_complex`, and the Triton compatibility script shows a clear design priority: the model should be deployable in production inference serving stacks (Triton, ONNX Runtime) without PyTorch dependency.

5. **Inference-only distribution.** By releasing only the inference library (no training code, no data processing scripts), the repo stays lightweight and focused. The complexity of training TTS models (data curation, alignment, multi-stage training) is explicitly left to the upstream StyleTTS2 framework.

## 6. Transfer to Lyra

**Transferable idea:** **Style-vector conditioned prosody prediction + lightweight iSTFT decoder.** Lyra's TTS component could adopt the same pattern: separate a small prosody predictor/duration model (predicting F0, duration, energy) from a fast iSTFT-based waveform decoder, conditioned on a compact style vector (256 dims). This is much lighter than autoregressive or diffusion-based TTS backends and achieves comparable quality at a fraction of the compute cost.

**Relevant Lyra workstream route:** Section 4.x (Voice & Response Generation) within the Lyra upgrade plan. Specifically:
- Route **4.3 Voice cloning / TTS module** -- Kokoro proves that 82M params + style vectors can produce high-quality TTS. Lyra's TTS module should consider a similar pipeline-model separation (G2P pipeline vs. neural synthesizer).
- Route **4.4 Streaming audio generation** -- Kokoro's simple chunk-and-concatenate approach could be adapted for Lyra's streaming use case, but with the addition of cross-chunk context (e.g., passing the last few style vectors across chunks).

**Impact:** 7/10 (High. Proves a concrete, lightweight architecture for high-quality TTS that Lyra could adopt or adapt directly. Significantly simpler than alternatives like Bark or VALL-E.)

**Effort:** 4/10 (Medium. The architecture is well-documented and Apache-licensed. Main effort would be integrating the G2P pipeline with Lyra's existing audio subsystem and adding streaming/latency optimizations.)

**Tier:** Tier 2 (Directly applicable component. Kokoro could be used as-is via pip in Lyra's audio pipeline, or the architectural patterns could be reimplemented.)

**License:** Apache 2.0 (fully compatible with any Lyra licensing, no restrictions on commercial use, modification, or redistribution).

**Key file paths:**
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/kokoro/pipeline.py` -- Full pipeline orchestration (360 lines)
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/kokoro/model.py` -- KModel neural network wrapper (150 lines)
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/kokoro/modules.py` -- Text encoder, prosody predictor, duration encoder (180 lines)
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/kokoro/istftnet.py` -- Hi-fi iSTFT decoder with AdaIN conditioning (420 lines)
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/kokoro/custom_stft.py` -- ONNX-safe STFT implementation (200 lines)
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/pyproject.toml` -- Package metadata and dependencies
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/hexgrad__kokoro/LICENSE` -- Apache 2.0
