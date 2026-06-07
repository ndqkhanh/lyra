# karpathy/autoresearch -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Autonomous LLM pretraining research swarm.** The core idea: give an AI coding agent a real, single-GPU LLM training pipeline and let it modify the code and run experiments autonomously overnight. The agent edits `train.py`, runs a 5-minute training session, checks if the validation bits-per-byte (val_bpb) improved, commits or reverts via git, and loops ~100 times over a human sleep cycle.

The mechanism is a hardened experiment loop encoded in `program.md`:

1. Agent reads `prepare.py` (read-only constants, data loader, tokenizer, evaluator) and `train.py` (the editable file with model, optimizer, training loop).
2. Agent creates a git branch `autoresearch/<tag>`, runs a baseline, then loops: hypothesize an improvement -> hack `train.py` -> git commit -> `uv run train.py` (exactly 5 min wall-clock) -> grep val_bpb from output -> log to `results.tsv` -> if improved: keep commit (advance branch); if worse: `git reset --hard` (discard).
3. Metric: **val_bpb** (validation bits-per-byte) is defined in `prepare.py:evaluate_bpb()` and is vocab-size-independent, enabling fair comparison across architectural changes like different tokenizers or vocab sizes. It sums per-token cross-entropy, divides by byte-length of target tokens (excluding special tokens).
4. Training always stops after exactly 300 seconds (TIME_BUDGET) of wall-clock time, regardless of model size, batch size, or architecture -- this makes experiments comparable within a given platform (but not across platforms).

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Total code: ~1,160 lines across 3 files + 1 Jupyter notebook for analysis.**

```
File           Lines   Role
prepare.py      389   Fixed constants, data download, BPE tokenizer training (rustbpe), dataloader with BOS-aligned best-fit packing, evaluate_bpb evaluator. NOT modified by agent.
train.py        630   GPT model (GPTConfig, CausalSelfAttention, MLP, Block, GPT), MuonAdamW optimizer, hyperparameters, setup, training loop. Agent edits this file.
program.md      114   Agent instructions: setup protocol, experiment loop, output parsing, logging format, decision rules (simplicity criterion, crash handling). Human edits this file.
analysis.ipynb   12 cells   Post-hoc analysis of results.tsv: reproducibility plots, cumulative improvement tracking.
```

**Data flow:**
- `prepare.py` downloads ClimbMix-400B parquet shards from HuggingFace, trains a BPE tokenizer via `rustbpe`, wraps it in a tiktoken Encoding, and precomputes token-byte lookups for BPB evaluation.
- `train.py` imports MAX_SEQ_LEN (2048), TIME_BUDGET (300s), Tokenizer, make_dataloader, and evaluate_bpb from `prepare.py`. It constructs a GPT decoder-only model with: value embeddings (ResFormer-style alternating per-layer), rotary embeddings, QK-RMSNorm, Flash Attention 3 (varunneal on H100, kernels-community fallback), ReLU^2 activations (SwiGLU alternative), logit softcapping.
- Optimizer is MuonAdamW: 2D matrix params use Muon (Newton-Schulz-based orthogonalization + Nesterov momentum + NorMuon variance reduction), all other params use AdamW.
- Training loop uses a fixed wall-clock budget with LR warmup/cool-down schedules, Muon momentum annealing, and weight decay decay.
- After training ends, `evaluate_bpb()` runs on a fixed validation shard; results are printed as key-value summary.

**Architecture pattern:** Minimal-surface-area agent interface. The agent only touches `train.py`. `prepare.py` is declared off-limits (the fixed evaluation harness is the ground truth). `program.md` is the human-authored "research org charter." This is essentially a **generator-evaluator loop** where the agent is the generator (proposes code changes) and the fixed training+evaluation pipeline is the evaluator.

## 3. Performance/Benchmarks (real numbers from the repo)

The repo does not include published benchmark results (no results.tsv committed -- it's gitignored). However, the design yields predictable throughput:

- **~12 experiments/hour**, ~100 experiments per 8-hour sleep cycle.
- **H100 BF16 peak:** 989.5 TFLOPS (hardcoded in train.py for MFU calculation).
- **Default model:** ~50M params (DEPTH=8, model_dim=512, n_head=4, n_kv_head=4), trained on ~500M tokens in 5 minutes.
- Each experiment produces: val_bpb, training_seconds (~300), total_seconds (~325 including startup), peak_vram_mb (~45GB on H100), MFU (~40%), total_tokens_M (~500M), num_steps (~953), num_params_M (~50.3M).
- The analysis notebook tracks cumulative improvement over baseline and produces a "progress frontier" plot.

## 4. Trade-offs (wins vs loses)

**Wins:**
- Extraordinary simplicity: ~1,160 lines total, zero configuration files, zero CLI flags, one editable file. This makes agent experimentation feasible because the action space is small and diffs are reviewable.
- Fixed time budget is a clever trick: normalizes across architectural changes (bigger model trains fewer steps, smaller model trains more steps, both get exactly 5 minutes). This removes the need for any step-based scheduling and lets agents freely explore architecture space.
- Git-native experiment tracking: branch-per-run, commit-per-attempt, reset-on-failure. No experiment management infrastructure needed. results.tsv stays untracked so the branch history reflects only successful innovations.
- Simplicity criterion in `program.md` (lines 37-38): "A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it." This is an explicit anti-over-engineering guardrail for the agent.

**Loses:**
- H100-only by default (Flash Attention 3 requires Hopper architecture, CUDA 12.8). Community forks exist for Mac (MLX), Windows, AMD, but the upstream repo is deliberately NVIDIA-only.
- Experiments are not cross-platform comparable: the 5-minute wall-clock budget means results on different GPUs measure different things (you are optimizing for your specific platform).
- No distributed training, no multi-GPU. Single GPU, single file. This is a feature for simplicity but limits relevance to production-scale training.
- No model checkpointing or mid-run recovery. If the process crashes mid-experiment, the experiment is lost.
- The evaluation is a single checkpoint at the end of 5 minutes -- no evaluation during training, no checkpoint averaging, no early stopping based on val loss. The agent cannot observe intermediate training dynamics.

## 5. Design Rationale (why this approach)

Andrej Karpathy's design philosophy here is deliberate minimalism applied to autonomous research:

- **"Single file to modify"** reduces the agent's search space. The agent doesn't need to navigate a codebase; it edits one file. This is critical because LLM agents struggle with multi-file coordination.
- **Fixed time budget** eliminates a whole class of confounding variables. Without this, the agent could "improve" val_bpb simply by training longer. With it, any improvement must come from genuine architectural or algorithmic innovation.
- **BPB over perplexity** enables architectural changes (vocab size, tokenizer, byte-level models). Perplexity is vocab-size-dependent and would penalize larger vocabularies; BPB normalizes this.
- **program.md as the human interface** separates concerns: the human writes research strategy (which experiment loop to run, what constraints apply, what trade-off criteria to use), the agent executes tactics (which code changes to try).
- **git as the experiment database** is elegant: no separate database, no serialization format, no checkpoint management. The branch history IS the experiment log. git reset is the "reject" operation.
- The MuonAdamW optimizer and the specific architectural choices (value embeddings, QK-RMSNorm, ReLU^2, logit softcap) are cherry-picked from nanochat, which itself represents a distillation of recent LLM architecture research (ResFormer, Griffin, Gemma 2, etc.).

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier)

**Transferable idea:** The **fixed-time-budget experiment loop** as a paradigm for agent-driven hyperparameter search and code improvement in Lyra. Currently Lyra's upgrade workstreams lack a standardized way for an agent to propose a change, test it (with a hard time cap), measure a single comparable metric, and either keep or discard via git. The autoresearch pattern provides the exact protocol for this: program.md defines the loop, program.md is the human's lever, git is the experiment log, and the metric is immutable.

**Workstream route:** SS 4.x (Self-Supervised / Agent-Driven Optimization). This plugs directly into Lyra's need for automated prompt optimization, router tuning, and memory system parameter search. Lyra could adopt a `program.md`-equivalent that defines: (a) the metric to optimize, (b) the time budget per experiment, (c) the scope of editable files, (d) the simplicity criterion.

**Impact:** 7 (High -- the fixed-budget disciplined loop is a reusable pattern that would unlock automated optimization across every Lyra subsystem from router weights to memory retrieval thresholds).

**Effort:** 2 (Low -- the core idea is a protocol, not infrastructure. It requires writing a Lyra-specific `program.md`, identifying a measurable metric, and pointing an agent at it. The git-based experiment tracking is already available in Lyra's repo.)

**Tier:** Quick Win (high impact, low effort, immediately actionable).

**License:** MIT (stated in README). Fully compatible with Lyra's usage.
