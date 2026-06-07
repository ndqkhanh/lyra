# snakers4/silero-vad — Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: Enterprise-grade, real-time Voice Activity Detector (VAD) that detects the presence of human speech in audio streams. Pre-trained on 150,000+ hours of speech across 6,000+ languages. Weighs ~2 MB (JIT) with inference under 1 ms per 31.25 ms audio chunk on a single CPU thread.

**How the code really works** (mechanics, not just API usage):

1. **Model architecture** (observable in `tinygrad_model.py`, the pure-Python reimplementation): A compact neural network consisting of:
   - A **learned STFT layer** implemented as `nn.Conv1d(1, 258, kernel_size=256, stride=128)` — the first 129 channels capture the real part of the STFT and channels 129-257 capture the imaginary part, then squared and summed to compute the power spectrogram.
   - **4 Conv1D layers** with ReLU activation: 129->128 (kernel 3, pad 1), 128->64 (kernel 3, stride 2), 64->64 (kernel 3, stride 2), 64->128 (kernel 3, stride 1). These progressively compress the frequency dimension while extracting temporal features.
   - An **LSTMCell(128, 128)** that maintains a 128-dimensional state vector across chunks — this is the key to streaming: the model remembers what happened in previous audio chunks without reprocessing the whole audio.
   - A **final Conv1d(128, 1, kernel=1)** with sigmoid activation that produces a 0-1 speech probability per timestep.

2. **Dual-rate support** via internal architecture: The JIT model bundles two sub-networks — one for 8 kHz (telephony) and one for 16 kHz (ASR/voip). The `hubconf.py` and `model.py` entry points load the appropriate ONNX model or JIT bundle. The `_validate_input` method in `OnnxWrapper` silently down-samples audio that is a multiple of 16 kHz (e.g., 32 kHz or 48 kHz) by striding.

3. **Streaming inference** (`VADIterator` class in `utils_vad.py` lines 458-549): A stateful iterator that processes audio chunk-by-chunk (512 samples at 16 kHz = 31.25 ms). It maintains:
   - `triggered` flag: whether currently in a speech segment
   - `temp_end`: sample position of a potential speech endpoint (to tolerate short silences)
   - `current_sample`: running sample counter
   
   The state machine has three transitions: silence-to-speech (returns `{'start': ...}`), speech-within-silence-gap (returns `None` while tracking tolerance), and speech-to-silence (returns `{'end': ...}` when silence exceeds `min_silence_duration_ms`). This enables real-time streaming without lookahead.

4. **Offline/batch processing** (`get_speech_timestamps` function, lines 211-455): A more sophisticated state machine that processes entire audio clips in one call. Key algorithmic details:
   - **Sliding window**: Audio is processed in 512-sample (16 kHz) or 256-sample (8 kHz) chunks via `model(chunk, sampling_rate).item()`.
   - **Hysteresis thresholding**: Uses two thresholds — `threshold` (entry, default 0.5) and `neg_threshold` (exit, default `threshold - 0.15 = 0.35`). This prevents chattering: once speech is detected, the model must see a significantly lower probability before declaring silence.
   - **Max speech duration handling**: When `max_speech_duration_s` is reached, rather than cutting abruptly, the algorithm searches for the longest silence segment within the current speech chunk (`use_max_poss_sil_at_max_speech=True`) and cuts there, then resumes from the end of that silence. This avoids cutting mid-syllable.
   - **Padding**: Speech chunks are padded on each side by `speech_pad_ms` (default 30 ms). Adjacent chunks separated by less than `2 * speech_pad_ms` are merged with overlapping padding.
   - **Post-processing**: Chunks shorter than `min_speech_duration_ms` (default 250 ms) are discarded.

5. **Dual runtime support**: The model runs either as a **PyTorch JIT** script (TorchScript, traced model file `silero_vad.jit`) or as an **ONNX** model (`silero_vad.onnx`). The ONNX path uses `onnxruntime.InferenceSession` with single-threaded session options (`inter_op_num_threads=1, intra_op_num_threads=1`). The `OnnxWrapper` maintains state tensors (`_state`, `_context`, `_last_sr`, `_last_batch_size`) across sequential calls, implementing a stateful ONNX session.

6. **Tuning/fine-tuning system** (`tuning/` directory): Uses a **decoder-only fine-tuning** strategy. The encoder (STFT + Conv layers) is frozen; only the LSTM-based decoder head is trained. Training data is specified via `.feather` dataframes with `audio_path` and `speech_ts` columns. Augmentations (noise injection, filtering, compression, pitch shift, room simulation) are applied with 40% probability during training. Validation uses ROC-AUC as the primary metric.

## 2. Architecture & Core Modules

**Entry points**:
- `src/silero_vad/__init__.py` — Exports public API: `load_silero_vad`, `get_speech_timestamps`, `save_audio`, `read_audio`, `VADIterator`, `collect_chunks`, `drop_chunks`
- `src/silero_vad/model.py` — `load_silero_vad(onnx=False, opset_version=16)` factory function. Resolves model file path from package data, dispatches to either `OnnxWrapper` or `init_jit_model`
- `hubconf.py` — `torch.hub` entry point for `torch.hub.load('snakers4/silero-vad', 'silero_vad')`

**Module map** (all in `src/silero_vad/`):

| File | Lines | Role |
|------|-------|------|
| `__init__.py` | 13 | Package version + public API re-exports |
| `model.py` | 37 | `load_silero_vad()` factory — resolves model files from package data directory |
| `utils_vad.py` | 656 | Core logic: `OnnxWrapper`, `get_speech_timestamps`, `VADIterator`, `read_audio`, `save_audio`, `collect_chunks`, `drop_chunks`, `init_jit_model` |
| `tinygrad_model.py` | 72 | Pure-Python `TinySileroVAD` class (tinygrad reimplementation) — documents exact architecture: 4 Conv1D layers, LSTMCell, final Conv1d+ sigmoid |

**Data files** (in `src/silero_vad/data/`):
- `silero_vad.jit` — PyTorch JIT script model (~2 MB, 260K parameters)
- `silero_vad.onnx` — ONNX model (opset 16)
- `silero_vad_16k_op15.onnx` — ONNX model (opset 15, 16 kHz only)
- `silero_vad_half.onnx` — FP16 ONNX model
- `silero_vad_op18_ifless.onnx` — Experimental ONNX with `If` op removed (opset 18)
- `silero_vad_16k.safetensors` — Tinygrad-compatible safetensors weights

**Tests**: `tests/test_basic.py` — Two test functions (JIT and ONNX), each loading the model and processing test audio files (wav, opus, mp3) to assert non-Null speech timestamps and forward pass outputs.

**Tuning infrastructure** (`tuning/`):
- `tune.py` — Main training loop (20 epochs, Adam, BCELoss with noise weighting, ROC-AUC-based checkpointing)
- `search_thresholds.py` — Grid search over entry/exit thresholds
- `utils.py` — Dataset loading, augmentation pipeline, `VADDecoderRNNJIT` (the trainable decoder head), train/validate loops
- `config.yml` — Hyperparameters (lr=5e-4, batch_size=128, num_epochs=20)

**Portability**: Examples in C++, C, C#, Java, Go, Rust, Haskell, Python, PyTorch LibTorch, and ExecuTorch are provided under `examples/`.

**Data flow pattern**: Stateful streaming pipeline. Audio flows as raw waveform -> (optional pad + STFT-like convolution) -> Conv1D encoder -> LSTM state cell -> sigmoid classifier. For batch/offline processing, `get_speech_timestamps` wraps the streaming model in a sliding window + state machine. For streaming, `VADIterator` wraps per-chunk calls with a lightweight state machine.

**Dependencies** (from `pyproject.toml`): `packaging`, `torch>=1.12.0`, `torchaudio>=0.12.0`. Optional: `onnxruntime>=1.16.1` (CPU or GPU), `soundfile`, `pytest`, `omegaconf`, `sklearn`, `pandas`, `tqdm`, `audiomentations`.

## 3. Performance/Benchmarks

All concrete numbers from the [Performance Metrics wiki page](https://github.com/snakers4/silero-vad/wiki/Performance-Metrics) and the README:

**Inference speed** (single CPU thread, batch size 1, 16 kHz, 31.25 ms chunk):

| Model | Inference (microseconds per chunk) | Real-time speed (RTS = audio-time / wall-time) |
|-------|-------------------------------------|-----------------------------------------------|
| V4 JIT | 830 us | 36x |
| V4 ONNX | 207 us | 151x |
| V5 JIT | 325 us | 96x |
| **V5 ONNX** | **189 us** | **165x** |

One CPU core can process ~165 seconds of audio per wall-clock second.

**Model size**: ~2 MB (JIT format). ONNX models are similarly compact.

**Model parameters**: ~260K parameters (tiny enough to fit in L2 cache on modern CPUs).

**Quality** (from the [Quality Metrics wiki page](https://github.com/snakers4/silero-vad/wiki/Quality-Metrics)):

**ROC-AUC on Multi-Domain Validation set** (17 hours, multi-domain speech):
- **Silero v6: 0.97** (best overall)
- Silero v5: 0.96
- FireRed VAD: 0.94
- Unnamed commercial VAD: 0.93
- WebRTC VAD: 0.73

**Accuracy (31.25 ms chunks, Multi-Domain Val)**:
- **Silero v6: 0.92** (best)
- Silero v5: 0.91
- WebRTC: 0.74

**Noise rejection (ESC-50 environmental noise)**:
- **Silero v6: 0.87** (dramatically improved from v5's 0.61)
- FireRed VAD: 0.60 (next best)
- WebRTC: 0.0 (detects all noise as speech)

**Training data scale**: 150,547 hours across 6,171+ languages from Bible.is, globalrecordings.net, VoxLingua107, Common Voice, and MLS.

## 4. Trade-offs

| Win | Lose | Source |
|-----|------|--------|
| 165x real-time ONNX speed on CPU | Still slower than WebRTC VAD (though within same order of magnitude) | Wiki FAQ, Performance Metrics |
| ~260K params, ~2 MB model — fits L2 cache | Only 8 kHz and 16 kHz natively supported (higher rates auto-downsampled) | FAQ, code |
| Stateful streaming: no lookahead needed | Model must be reset between unrelated audio segments | `VADIterator` design |
| 150k hours, 6000+ languages training data | No published research paper, no training code for the core model, no formal dataset release | FAQ |
| Dual-rate (8k + 16k) in a single JIT bundle | Dual-rate bundling makes the JIT model larger than necessary (can't share all weights between subnets) | FAQ: "we arrived at this one after a lot of experiments" |
| ONNX is 30-60% faster than PyTorch JIT on small inputs | JIT lacks fusible module patterns (ConvBnReLU), making the speed gap "kind of unavoidable" | FAQ |
| Fine-tuning only needs decoder head training (encoder frozen) | Requires `.feather`-formatted annotation data with 30 ms precision per dataset | Tuning README, config |
| MIT license — no restrictions, no telemetry, no registry | ONNX mobile/edge only supports 16 kHz (no 8 kHz on ARM) | FAQ: ARM builds |
| Dual-threshold hysteresis prevents chattering | Tuning thresholds is domain-dependent; default threshold=0.5 may need adjustment | Code, wiki |
| Robust to extreme noise (ESC-50 score 0.87) | Long chunks can degrade model quality (specific degradation not quantified) | FAQ |
| Works on mp3, opus, wav + any format torchaudio can decode | Requires FFmpeg < 7 or sox or soundfile for audio I/O via torchaudio | README dependencies |
| Tinygrad reimplementation available in repo | tinygrad support is experimental ("ifless" variant, v6.2, 16k only) | Version history, code |
| Decoder-only fine-tuning is fast and low-data | Fine-tuning only tunes the decoder head, which is the smallest part of the model | Tuning code |

**Key design tension**: The JIT model bundles two sub-networks (8k and 16k) into one file, but they share minimal weights. The FAQ explicitly notes this was a trade-off arrived at "after a lot of experiments." A more modular architecture could save model size, but the dual-rate JIT packaging simplifies deployment (single file for all use cases).

## 5. Design Rationale

Every major design choice traces back to one goal: **a single, lightweight, streaming-first model that works everywhere without tuning**.

1. **Streaming-first architecture**: The model was explicitly "designed for streaming" (FAQ). The LSTM state cell (128-dim) maintains temporal context from previous chunks without reprocessing. This is the opposite of sliding-window-over-FULL-audio approaches — the LSTM state is the compressed representation of all prior audio. This choice enables: (a) real-time microphone processing with sub-1ms latency, (b) arbitrarily long audio without OOM, and (c) simple integration into voice-based pipelines.

2. **Learned STFT over fixed spectrogram**: Rather than computing a standard STFT + Mel filterbank (as Whisper does), Silero VAD uses a Conv1d layer with kernel_size=256 and stride=128 to learn the frequency decomposition. This is documented in `tinygrad_model.py`. The advantage is that the model learns which frequency bands are most discriminative for speech vs. non-speech, rather than relying on a fixed psychoacoustic scale. The Conv1d weights effectively encode a bank of learned bandpass filters.

3. **No training code released**: The FAQ states the team has "not published any of those [papers, datasets, training code] for lack of time and motivation." This is a deliberate choice to focus on the inference product. The `tuning/` directory provides fine-tuning infrastructure (decoder-only), but the core model weights and training pipeline remain proprietary — protecting their competitive advantage.

4. **Dual sampling rate via separate sub-networks**: Rather than designing a single model that handles both 8 kHz and 16 kHz internally, the JIT model contains two separate processing chains. This is simpler to train (separate runs for each rate) but means the model can't share parameters between rates. The choice is pragmatic: 8 kHz is the telephony standard; 16 kHz is the ASR standard; handling both in a single download simplifies deployment for both use cases.

5. **ONNX as primary deployment target**: The performance table shows ONNX is 4x faster for v4 and 1.7x faster for v5 compared to JIT. The team recommends ONNX for production. The `OnnxWrapper` explicitly sets single-threaded session options, optimizing for real-time streaming on constrained hardware. The choice to support both JIT and ONNX gives users flexibility: JIT for quick prototyping in PyTorch ecosystems, ONNX for production on ARM/mobile/edge.

6. **Minimum viable I/O**: Audio I/O is handled entirely through `torchaudio`, which itself delegates to system libraries (FFmpeg, sox, soundfile). The VAD model does not care about input format — it only processes raw PCM samples at 8k or 16k. This clean separation means the VAD works with any audio source (microphone, file, network stream) as long as the upstream pipeline delivers the right sample rate.

7. **Hysteresis thresholding as the default**: The `get_speech_timestamps` function uses two thresholds (entry at `threshold`, exit at `threshold - 0.15`). This is a standard control-systems technique to prevent oscillation at the decision boundary. The default threshold of 0.5 was chosen as "lazy" good-enough for most datasets, but the function is explicitly designed for tuning (`neg_threshold` parameter is user-configurable).

8. **Decoder-only fine-tuning**: The `tuning/` code freezes the encoder (STFT conv + Conv layers) and only trains the decoder (LSTMCell + final conv). This is efficient because: (a) the encoder learns universal frequency features, (b) only the decision boundary (in LSTM state space) needs adaptation per-domain, (c) fewer parameters = less data needed = faster training. The `noise_loss` parameter further weights non-speech frames down, preventing the model from becoming overly conservative on noise-rich data.

## 6. Transfer to Lyra

**The one idea: Streaming stateful inference as an architectural pattern for real-time agent perception.**

Silero VAD demonstrates a clean pattern for processing a continuous, real-time data stream (audio) with a lightweight learned model while maintaining temporal state. This pattern is directly applicable to Lyra's voice mode and, more broadly, to any stream-processing subsystem (logs, metrics, sensor data).

**Specific transferable mechanisms**:

1. **LSTM-based streaming state machine**: Lyra's voice mode (the most direct application) needs a VAD to determine when the user is speaking vs. silent. Silero VAD's `VADIterator` is a ready-to-integrate Python class that takes 512-sample chunks and returns speech start/end events. It handles real-time microphone input with <1ms inference overhead. No server-side audio processing needed — it runs on-device in the agent process.

2. **Hysteresis thresholding for event debouncing**: The dual-threshold pattern (trigger at 0.5, release at 0.35) is directly transferable to any binary classification in Lyra: tool call validation (when is confidence high enough to execute?), anomaly detection, attention gating. A single threshold causes oscillation at the boundary; dual thresholds provide stable transitions.

3. **Decoder-only fine-tuning for domain adaptation**: The pattern of freezing a general encoder and training only the decoder head on new domain data is a transferable meta-learning pattern. Lyra could adopt this for adapting its core models to specific user domains: train a domain-specific adapter (decoder head) on a small dataset while the base model remains frozen.

4. **On-device model packaging**: The ~2 MB model that runs on a single CPU thread demonstrates that meaningful AI perception can happen entirely on-device without GPU or cloud dependency. This validates the approach of bundling small, focused models directly in the agent runtime rather than relying on external APIs.

**Workstream route**: **Section 18 (Voice Mode)** — Primary integration. Silero VAD is the critical missing piece for Lyra's voice pipeline: without a VAD, the system cannot distinguish speech from silence, cannot segment utterances, and cannot process asynchronous voice input. Secondary: **Section 16 (Reliability)** — The thresholding + state machine pattern for event detection in noisy streams.

**Impact**: 9/10 — A VAD is a prerequisite for any voice interaction system. Without it, voice mode either requires a push-to-talk (defeating the hands-free use case) or wastes compute/API costs processing silence. Silero VAD directly enables continuous listening, utterance segmentation, and noise rejection.

**Effort**: 2/10 — The existing Python package (`silero-vad` on PyPI) can be installed with `pip install silero-vad` and integrated in under 50 lines of code. The heavy lifting (model loading, state management, audio I/O) is entirely handled by the library. The only integration work is wiring the VAD events into Lyra's voice processing pipeline (already planned in Section 18).

**Tier**: Gold — Highest impact with trivial effort. Enables a whole new interaction modality (always-on voice) with zero model training or complex engineering.

**License**: MIT — Free to use, modify, sublicense, and integrate for any purpose, including commercial. No restrictions, no attribution requirement (though recommended), no copyleft.
