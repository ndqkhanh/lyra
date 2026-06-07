# openai/whisper -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: General-purpose speech recognition -- a Transformer sequence-to-sequence model trained on 680,000 hours of weakly supervised audio data, capable of multilingual speech recognition, speech-to-English translation, and language identification, all from a single model.

**How the code really works** (data flow):

1. **Audio ingestion** (`audio.py`): The file is decoded via a subprocess call to `ffmpeg` (downmixed to mono 16 kHz PCM). No Python audio decoding library -- pure CLI pipe.

2. **Feature extraction** (`audio.py::log_mel_spectrogram`): The raw waveform is converted to a log-Mel spectrogram via STFT (400-sample Hann window, 160-sample hop) followed by a precomputed Mel filterbank (80 or 128 bands loaded from `assets/mel_filters.npz`). The output is normalized to `[-4, 4]` range via clamp-and-shift.

3. **Sliding window** (`transcribe.py::transcribe`): The audio is processed in fixed 30-second windows (N_SAMPLES = 480,000 at 16 kHz). The Mel spectrogram is padded/trimmed to exactly N_FRAMES = 3000 frames per window. The `seek` pointer advances by segment-determined offsets using timestamp tokens from the decoder output.

4. **Encoder** (`model.py::AudioEncoder`): A stack of 2 Conv1D layers (kernel 3, stride 1 then stride 2) downsamples 3000 Mel frames to 1500 encoder states, adding sinusoidal positional embeddings. Followed by `n_audio_layer` Transformer encoder blocks (pre-LayerNorm residual, MultiHeadAttention with optional SDPA, GELU-MLP with 4x expansion).

5. **Decoder** (`model.py::TextDecoder`): An embedding layer + learned positional embedding + `n_text_layer` Transformer decoder blocks with causal masking and cross-attention to encoder output. Produces logits over the vocabulary (including special task tokens and 1501 timestamp tokens for 0.02-second increments over 30 seconds).

6. **Task specification** (`tokenizer.py`, `decoding.py`): The decoder's input begins with a special token sequence: `<|startoftranscript|>`, `<|language|>`, `<|transcribe|>` or `<|translate|>`. This single-model/multi-task design means the architecture never changes -- only the prompt prefix selects the behavior. Language detection runs as a separate forward pass on the first 30-second chunk.

7. **Decoding strategies** (`decoding.py`): Greedy (T=0 with argmax), beam search (configurable beam size and patience), or best-of-N sampling (T>0). Temperature fallback is managed in `transcribe.py -- decode_with_fallback()`: if compression_ratio > 2.4 or avg_logprob < -1.0, retry with higher temperature (default: 0.0, 0.2, 0.4, 0.6, 0.8, 1.0).

8. **KV-cache** (`model.py::install_kv_cache_hooks`): Forward hooks on key/value projection modules cache their outputs for reuse across decoder steps. The `PyTorchInference` class in `decoding.py` manages these hooks and handles cache rearrangement for beam search.

9. **Word-level timestamps** (`timing.py`): An optional post-processing pass. Cross-attention weight matrices from decoder layers are extracted, averaged across alignment heads (specified per-model in `__init__.py`), median-filtered, and aligned to text tokens via Dynamic Time Warping (DTW). Both CPU (numba JIT) and CUDA (custom Triton kernel) implementations exist.

10. **Output formatting** (`utils.py`): Writers for TXT, VTT, SRT, TSV, and JSON formats. Subtitle writers handle line splitting, word highlighting, and max-line-width/count constraints.

## 2. Architecture & Core Modules

**Entry point**: `whisper/__main__.py` calls `cli()` from `transcribe.py`, which uses argparse. The `pyproject.toml` registers `whisper.transcribe:cli` as the `whisper` console script.

**Module map** (all in `whisper/`):

| File | Lines | Role |
|------|-------|------|
| `__init__.py` | 162 | Model registry with SHA256 downloads, `load_model()` factory, `_ALIGNMENT_HEADS` bitmask constants |
| `transcribe.py` | 624 | CLI entry point + `transcribe()` orchestration: audio-to-Mel, sliding window loop, temperature fallback, hallucination detection heuristics |
| `model.py` | 346 | `Whisper(nn.Module)` container, `AudioEncoder`, `TextDecoder`, `MultiHeadAttention` (with SDPA fallback), `ResidualAttentionBlock`, `LayerNorm`/`Linear`/`Conv1d` type-preserving wrappers |
| `decoding.py` | 827 | `DecodingTask` lifecycle, `GreedyDecoder`, `BeamSearchDecoder`, logit filters (`SuppressBlank`, `SuppressTokens`, `ApplyTimestampRules`), `PyTorchInference` with kv-cache management |
| `audio.py` | 158 | Audio loading via ffmpeg subprocess, `log_mel_spectrogram()`, `pad_or_trim()`, hyper-constants (SAMPLE_RATE, N_FFT, HOP_LENGTH, N_FRAMES) |
| `timing.py` | 389 | Word alignment via cross-attention + DTW (numba CPU / Triton CUDA), punctuation merging, segment boundary heuristics |
| `tokenizer.py` | 396 | `tiktoken` wrapper with 99-language special tokens, timestamp token range, `split_to_word_tokens()` for CJK vs space-delimited languages |
| `utils.py` | 319 | Output writers (TXT, VTT, SRT, TSV, JSON), `compression_ratio()`, `format_timestamp()`, `get_start()`/`get_end()` |
| `triton_ops.py` | 118 | Custom Triton JIT kernels for DTW and median filter (string-manipulated kernel generation for the median filter) |
| `version.py` | 1 | `__version__ = "20250625"` |

**Assets**:
- `assets/gpt2.tiktoken` / `assets/multilingual.tiktoken` -- BPE rank tables
- `assets/mel_filters.npz` -- Precomputed Mel filterbanks (80 and 128 bands)
- `normalizers/english.py` + `english.json` -- English text normalizer for WER evaluation

**Data flow pattern**: Pipeline of imperative transformations. No dependency injection or abstract interfaces for the main transcription path. Decoding uses a Strategy pattern (GreedyDecoder / BeamSearchDecoder implementing TokenDecoder interface) and a Filter pattern (LogitFilter subclasses). Inference uses a lightweight adapter (PyTorchInference implementing the Inference protocol).

**Dependencies** (from `pyproject.toml`): `torch`, `numpy`, `tiktoken`, `numba`, `tqdm`, `more-itertools`, `triton` (Linux x86_64 only).

## 3. Performance/Benchmarks

**Model size vs speed** (from README, measured on A100 transcribing English speech):

| Model | Params | VRAM | Relative speed (vs large) |
|-------|--------|------|--------------------------|
| tiny | 39M | ~1 GB | ~10x |
| base | 74M | ~1 GB | ~7x |
| small | 244M | ~2 GB | ~4x |
| medium | 769M | ~5 GB | ~2x |
| large | 1550M | ~10 GB | 1x |
| turbo | 809M | ~6 GB | ~8x |

**turbo model**: An optimized version of `large-v3` (same underlying architecture but fewer layers or distilled). Offers ~8x speedup with "minimal degradation in accuracy."

**Accuracy by language**: Performance varies widely. Strong on ~10 high-resource languages (English, German, Spanish, French, Japanese, Chinese, etc.). Significantly weaker on low-resource languages (WER/CER metrics in Appendix D.1, D.2, D.4 of the paper). Translation quality measured with BLEU (Appendix D.3).

**Training data scale**: 680,000 hours -- 65% English (438k hrs), 18% non-English with English translations (126k hrs), 17% non-English with native transcripts (117k hrs), covering 98 languages.

**Key limitations** (from model card and paper):
- Hallucinations: model generates text not actually spoken (hypothesized as language-model prior overpowering audio signal)
- Repetition loops: autoregressive decoder can get stuck in repeated tokens; mitigated but not eliminated by beam search and temperature scheduling
- Performance disparity across languages, accents, and demographics

## 4. Trade-offs

| Win | Lose | Source |
|-----|------|--------|
| Single model replaces entire speech pipeline (VAD, ASR, language ID, translation) | Each individual task may underperform specialized models | Architecture decision |
| 680k hours of noisy web data enables broad robustness | Weak supervision introduces hallucinations and noisy training signal | Model card, paper |
| Fixed 30-second window simplifies implementation | Inefficient for variable-length audio; context limited to 30s; no streaming | Code design |
| Autoregressive decoding enables multitask output format | Slower than CTC/RNN-T; prone to repetition loops | Decoding strategy |
| Temperature fallback systematically reduces failure cases | Adds latency from re-decoding at multiple temperatures | `transcribe.py` logic |
| English-only models outperform multilingual at same size | Requires maintaining separate model variants | Model table |
| turbo trades ~5% accuracy for ~8x speed vs large | turbo not suitable for translation tasks | README note |
| Word-level timestamps via DTW are lightweight, no extra model needed | Experimental quality; unreliable on translations; significant compute cost | `timing.py`, warnings |
| ffmpeg subprocess is simple and universal | External dependency; no cross-platform binary; adds ~200ms startup overhead | `audio.py` |

**Hallucination detection heuristics** (added in v20240927): The code in `transcribe.py` has grown elaborate heuristics (lines ~315-472) to detect and skip hallucinated segments by examining word anomaly scores (probability < 0.15, very short or very long durations), checking for surrounding silence gaps, and skipping segments that look implausible. This is a clear recognition that the core model has a hallucination problem that prompt/post-processing engineering is compensating for.

**Turbo model limitation**: The `turbo` model is explicitly documented as not trained for translation tasks. If `--task translate` is specified with turbo, it silently returns the original language. This is a surprising gotcha documented in the README.

## 5. Design Rationale

The key design choices stem from a single goal: **robustness through scale and simplicity**.

1. **Encoder-decoder Transformer over CTC/RNN-T**: CTC models can only transcribe, and RNN-T requires alignment during training. The encoder-decoder architecture allows the model to output arbitrary token sequences, enabling the multitask format where a single decoder step can produce a language ID token, a transcription token, a translation token, or a timestamp token. This is the central innovation -- treating ASR, translation, and language ID as the same sequence-prediction problem with different token prefixes.

2. **Weak supervision at scale**: Rather than curating clean datasets (which max out at a few thousand hours), Whisper trains on 680k hours of internet audio/transcript pairs. The paper shows that despite the noise, scaling data quantity improves robustness to accents, noise, and rare words -- properties that small clean datasets cannot achieve.

3. **Log-Mel spectrogram as input**: Simple, well-understood, deterministic preprocessing. The Mel filterbank is precomputed and loaded from an NPZ file, avoiding a librosa dependency.

4. **Fixed 30-second chunks**: A pragmatic simplification. Long-range audio context is preserved by feeding the previous window's transcription back as a prompt (`condition_on_previous_text`). This avoids the complexity of variable-length sequence handling in both the encoder and the batching logic.

5. **Special tokens as task specifiers**: Instead of having separate model heads or output layers for each task, Whisper uses special tokens in the vocabulary. `<|startoftranscript|>` always begins decoding; the next tokens select the language and task. This is elegant because it requires zero architectural changes for new tasks -- just add a new special token and train on it.

6. **KV-cache via hooks**: Rather than modifying the forward pass to store/retrieve cached keys and values, Whisper installs PyTorch forward hooks on the key and value projection modules. This keeps the model's forward pass clean and allows the caching logic to be swapped out independently.

7. **DTW for word alignment**: Rather than training a separate alignment model (which would require alignment-annotated data), Whisper uses the cross-attention weights directly. DTW finds the optimal path through the attention matrix, producing word-level timestamps without additional training.

## 6. Transfer to Lyra

**The one idea: Multitask token-based routing.**

Whisper's core insight is that a single Transformer decoder can handle multiple tasks (transcribe, translate, language ID) by simply prepending different special tokens to the input sequence. The model architecture itself never changes -- only the prompt prefix selects the behavior.

**Direct parallel to Lyra's routing problem**: Lyra currently needs to route user intents to different tools, sub-agents, and processing pipelines. Instead of building a separate routing module with classification logic, Lyra could adopt Whisper's approach: define a vocabulary of "instruction tokens" (action tokens, tool selectors, output format specifiers) and train or prompt the model to generate the appropriate token sequence prefix.

For example:
- `<|action:research|>` -- route to research pipeline
- `<|action:generate|>` -- route to code generation
- `<|action:analyze|>` -- route to analysis
- `<|format:report|>` -- produce structured report output
- `<|resume|>` -- continue from conversation history (analogous to `condition_on_previous_text`)

This eliminates the need for a separate classifier/router module, reduces latency (no multi-hop routing), and makes the system more extensible (adding a new action = adding a new token to the vocabulary + few training examples).

**Workstream route**: **Section 4.3 (Router Design)**, with secondary application in 4.5 (Task Decomposition Orchestrator).

**Impact**: 8/10 -- Would substantially simplify Lyra's routing architecture by replacing an external classifier with token-level task specification embedded in the generation process itself.

**Effort**: 4/10 -- Low implementation effort for the core concept (define instruction tokens, add to tokenizer, adjust prompts). Full integration requires changes to the routing layer, but the code change is minimal since it's a prompt-side change rather than an architecture change.

**Tier**: Gold -- High impact, low effort, directly addresses a core Lyra architectural challenge.

**License**: MIT -- Free to use, modify, and distribute. No restrictions on transfer or integration.
