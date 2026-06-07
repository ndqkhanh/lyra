# pipecat-ai/smart-turn -- Deep-Read

## 1. Headline Feature & Mechanism

**Smart Turn v3.2** is an open-source, audio-native turn detection model for conversational voice AI. Its job is to decide when a voice agent should respond to human speech -- replacing naive Voice Activity Detection (VAD) with a learned classifier that understands prosody, grammar, and semantic cues.

**How it really works:**

The inference pipeline (defined in `inference.py`) is deceptively simple:

1. **Audio preconditioning** (`audio_utils.py`): Input 16 kHz mono PCM audio is truncated (keeping the END) or zero-padded at the front to exactly 8 seconds. This ensures the most recent speech is always at the end of the window.

2. **Feature extraction**: A HuggingFace `WhisperFeatureExtractor` (chunk_length=8s) converts raw PCM into 80-channel log-mel spectrograms with 800 time frames -- shape `(1, 80, 800)`.

3. **ONNX inference**: An ONNX Runtime session runs the quantized model. The model itself (defined in `train.py` as `SmartTurnV3Model`) uses:
   - **Whisper Tiny encoder** (~8M params total) as the backbone -- no decoder needed since we don't generate text, only classify
   - **Attention pooling** over encoder hidden states (learned per-timestep attention weights via softmax)
   - **Binary classifier head**: `Linear(256) -> LayerNorm -> GELU -> Dropout -> Linear(64) -> GELU -> Linear(1)`

4. **Output**: A sigmoid probability in `[0, 1]`. `> 0.5` means "turn complete (agent should respond)", `< 0.5` means "speaker is still going".

**Critical design insight -- VAD-gated execution:** The model is NOT meant to run on every audio frame. The `record_and_predict.py` reference implementation runs a lightweight Silero VAD model FIRST (512-sample chunks, ~200ms pre-speech buffer, 1s trailing silence threshold). Smart Turn only runs once VAD detects silence, on the FULL recording of the user's turn. This keeps inference costs low -- Smart Turn runs maybe 1-2x per conversation turn instead of continuously.

## 2. Architecture & Core Modules

```
smart-turn/
  inference.py           # Core ONNX inference: build_session(), predict_endpoint()
  audio_utils.py         # truncate_audio_to_last_n_seconds() -- pad/truncate to 8s
  predict.py             # CLI for file-based prediction (librosa -> inference)
  record_and_predict.py  # Real-time mic pipeline: Silero VAD -> Smart Turn gate
  train.py               # Full training: SmartTurnV3Model, export_to_onnx_fp32, quantize_onnx_model
  train_local.py         # Local orchestrator (argparse: --training-run-name, --quantize, --benchmark)
  train_modal.py         # Modal cloud orchestrator (GPU: L4/T4, 32GB+ RAM)
  benchmark.py           # Accuracy + latency benchmark suite: per-language, per-dataset, end-to-end
  logger.py              # Structured logging, device info, model structure dumper
  requirements.txt       # torch 2.9, transformers 4.48, onnxruntime-gpu, datasets, wandb
  requirements_inference.txt  # Minimal inference deps: numpy, onnxruntime, transformers, librosa
  requirements_aarch64.txt   # DGX Spark / ARM CUDA nightlies
  datasets/scripts/
    raw_to_hf_dataset.py      # Convert raw FLAC to HuggingFace dataset format
    upload-to-hub.py          # Push datasets to HuggingFace hub
  docs/data_generation_contribution_guide.md  # How to contribute labeled audio data
```

**Data flow (inference):**
```
Mic -> PyAudio (16 kHz, 512-sample chunks) -> Silero VAD ONNX (speech/non-speech per chunk)
  -> VAD triggers on speech -> buffer chunks until 1s trailing silence
  -> Concatenate segment (float32) -> predict_endpoint()
    -> truncate/pad to 8s -> WhisperFeatureExtractor -> ONNX model -> sigmoid -> binary prediction
```

**Data flow (training):**
```
HuggingFace datasets (pipecat-ai/smart-turn-data-v3.2-*) 
  -> OnDemandSmartTurnDataset (lazy feature extraction, truncate/pad to 8s)
  -> HuggingFace Trainer (cross-entropy, BCEWithLogitsLoss with dynamic pos_weight)
  -> PyTorch model -> torch.onnx.export -> ONNX FP32
    -> ONNX static quantization (CalibrationDataReader, Entropy calibration, int8 weights, uint8 activations)
      -> benchmark.py (accuracy + latency across languages/datasets/providers)
```

**Architecture pattern:** Transformer encoder + lightweight classification head, deployed via ONNX Runtime. Training uses HuggingFace Trainer + Weights & Biases. Cloud training uses Modal for GPU orchestration.

## 3. Performance / Benchmarks

**From README and code (`benchmark.py`):**

- **Inference latency** (int8 quantized, CPU, 8s audio): As low as **10ms** on some CPUs, under **100ms** on most cloud instances
- **GPU inference** (fp32, e.g. L4/T4): ~**65ms** on Pipecat Cloud 1x instance (end-to-end with feature extraction)
- **Model size**: ~8M parameters
  - CPU version: **8MB** (int8 quantized ONNX)
  - GPU version: **32MB** (fp32 ONNX)
- **Accuracy**: GPU fp32 version outperforms CPU int8 by ~1%
- **Languages**: 23 languages supported
- **Benchmark methodology** (`benchmark.py`):
  - `run_perf()`: Direct inference on zero features (1000 timed runs, 100 warmup) -- measures ONNX runtime alone
  - `run_fe_perf()`: Whisper feature extraction timing (1000 runs)
  - `run_e2e_perf()`: Full pipeline (feature extraction + inference)
  - `run_accuracy()`: Dataset evaluation with per-language and per-dataset breakdowns
  - Metrics: accuracy, precision, recall, F1, false positive rate, false negative rate
  - Output: Structured markdown report with P50/P90/mean latency tables

## 4. Trade-offs

### Wins

- **Audio-native, not ASR-dependent**: Unlike approaches that transcribe audio to text then classify, Smart Turn works directly on PCM audio. This captures prosody (tone, pace, pitch contours) that text transcription loses.
- **VAD-gated efficiency**: By only running during silence periods, the model avoids processing every audio frame. The 8M parameter model is small enough to run on CPU.
- **Fully open**: BSD 2-Clause license, open training data, open training code, open model weights. Anyone can fork, fine-tune, or contribute.
- **Lazy feature extraction** (`OnDemandSmartTurnDataset`): Audio features are computed on-the-fly during training, avoiding the need to store pre-computed spectrograms for the entire dataset.
- **Balanced training data**: 50:50 split of complete/incomplete samples, with explicit guidance for data contributors about prosody, filler words, and trailing silence.

### Losses / Limitations

- **8-second context window**: The model only sees the last 8 seconds of audio. Longer turns are truncated from the beginning. This is a deliberate trade-off (context length vs. inference speed) but means very long turns lose early context.
- **Whisper Tiny backbone**: While small and fast, Whisper Tiny was designed for ASR, not turn detection. The encoder may not be optimal for this task. The README explicitly notes interest in experimenting with wav2vec2-BERT, LSTM, and other architectures.
- **No text conditioning**: The model has no awareness of what words were spoken -- it operates purely on audio features. The project lists "text conditioning for modes like credit card entry" as a medium-term goal.
- **Static ONNX quantization only**: The int8 model uses post-training static quantization (calibrated on 1024 samples). No quantization-aware training (QAT) is implemented, which could recover accuracy lost in quantization.
- **Training code complexity**: The `train.py` file is ~650+ lines (with the rest beyond line 650 doing piped output handling). The `ExternalEvaluationCallback` is 175 lines of WandB logging wiring -- substantial scaffolding for what is conceptually a simple binary classification loop.
- **Dependency on torchcodec**: HuggingFace `datasets` audio decoding requires `torchcodec`, which lacks PyPI wheels for aarch64 (requiring PyTorch CUDA nightly index workaround via `requirements_aarch64.txt`).

## 5. Design Rationale

**Why Whisper Tiny as the backbone?** The Whisper encoder is well-understood, has pre-trained weights available, and provides strong audio representations out of the box. At 8M parameters, it is small enough for CPU inference. The Whisper feature extractor (80-channel log-mel spectrograms) is a proven front-end for audio tasks.

**Why VAD gating?** The README states: "VAD can't take into account the actual linguistic or acoustic content of the speech." But VAD IS used to determine WHEN to run Smart Turn. The rationale: VAD is extremely cheap (512-sample chunks, ~1ms per inference) and can reliably detect silence boundaries. Smart Turn is more expensive but more accurate -- so gate the expensive model behind the cheap one.

**Why ONNX for deployment?** ONNX Runtime provides hardware-agnostic inference with optimizations for both CPU and GPU. The `ort.ExecutionMode.ORT_SEQUENTIAL` with `inter_op_num_threads=1` suggests a focus on predictable single-threaded latency rather than throughput.

**Why attention pooling over mean pooling?** The learned attention mechanism (`self.pool_attention`) allows the model to learn which time frames are most informative for turn detection. This is more expressive than simple mean pooling of encoder states.

**Why HuggingFace Trainer?** It provides standardized training loops, evaluation, checkpointing, and logging integration (WandB). The code uses `TrainingArguments` with `eval_steps=500`, `save_steps=500`, and `logging_steps=100` -- frequent evaluation is important for a binary classification task where accuracy can plateau quickly.

**Why balanced data with explicit labeling guide?** Turn detection is a nuanced perceptual task. The contribution guide goes into detail about prosody ("if the speaker sounds like they're still thinking"), filler words, and trailing silence. This domain-specific labeling guidance is arguably more important than the model architecture itself.

## 6. Transfer to Lyra

### One specific, transferable idea

**VAD-gated inference pattern as a lightweight input router gate.**

Lyra's router (§4.3) currently processes every input through the full routing pipeline. The Smart Turn pattern suggests a cheap pre-filter: before running the full router, run a lightweight signal that answers "is this input worth routing?" For audio inputs, this is VAD. For text inputs, this could be a simple classifier ("is this a complete utterance?"), a length check, or a domain classifier.

The specific mechanism: gating_model.predict(prob > threshold: boolean) -> if false, skip/fast-path; if true, run full pipeline. This maps to Lyra's §4.3 Router workstream.

### Workstream Route

**§4.3 Router** -- The VAD-gated turn detection pattern is a direct analog to "gate before route." Lyra could implement a lightweight input classifier that runs before the main router, fast-pathing trivial inputs and only routing complex ones through the full pipeline. The training data methodology (balanced dataset, per-category evaluation, explicit labeling guidance) also informs how Lyra should build its router training data.

### Impact / Effort / Tier

- **Impact**: 6/10 -- Turn detection is a specific, well-understood capability. The VAD-gated pattern is broadly useful as a pre-processing stage but not a transformative architectural insight for Lyra.
- **Effort**: 3/10 -- The concept is simple to implement as an optional gate before the router. The core code (`inference.py` is ~75 lines) is minimal.
- **Tier**: "quick-win" -- Low effort for moderate, well-bounded benefit.

### LICENSE

**BSD 2-Clause** -- Permissive. No restrictions on use, modification, or redistribution (provided the copyright notice is retained). Fully compatible with Lyra's open-source ecosystem.
