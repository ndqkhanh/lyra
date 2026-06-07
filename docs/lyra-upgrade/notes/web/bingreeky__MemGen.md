# bingreeky/MemGen -- Deep-Read

**Paper**: ICLR 2026 -- MemGen: Weaving Generative Latent Memory for Self-Evolving Agents (arXiv 2509.24704)
**Repo**: https://github.com/bingreeky/MemGen
**Date read**: 2026-06-07
**No LICENSE file found in repo**.

---

## 1. Headline Feature & Mechanism

MemGen inserts **generative latent memory tokens** directly into a language model's hidden-state stream at delimiter positions (commas, periods, newlines). The mechanism has two learned modules:

- **Memory Weaver** (`memgen/model/weaver.py`): A LoRA-tuned small LM with two learnable parameter vectors (`prompt_query_latents` and `inference_query_latents`, typically 4-16 tokens each). At each augmentation point, the weaver concatenates these query latents onto the accumulated embedding sequence, runs a forward pass through its own LM, takes the last `latent_len` hidden states, projects them through `nn.Linear(weaver_hidden_size, reasoner_hidden_size)`, and splices them into the reasoner's embedding stream. The reasoner sees these latent embeddings as if they were ordinary tokens but they do not contribute to the LM loss (masked by `current_latents_mask`).

- **Memory Trigger** (`memgen/model/trigger.py`): A LoRA-tuned LM plus a linear `hidden_size -> 2` output layer. During autoregressive generation, after every token whose prefix ends with a delimiter, the trigger is called. It produces a binary decision: augment (insert latents) or skip. This is the "when to recall" decision.

**Two-stage training pipeline**:
1. **Weaver training** (SFT or GRPO): Fix the trigger, train the weaver to generate useful latent tokens. During SFT, latents are inserted at augmentation points determined by labels (prompt boundaries and delimiter positions). During GRPO, the weaver's augmentations influence generation quality, rewarded by the environment's `compute_reward`.
2. **Trigger training** (GRPO only): Fix the weaver, train the trigger to decide when to augment. The trigger's decisions affect generation, again rewarded by `compute_reward`.

---

## 2. Architecture & Core Modules

**Entry point**: `main.py` (100 lines) parses `--cfg-path <yaml>` and optional `--options key=value` overrides via OmegaConf.

**Data flow**: `main.py`
- `Config(args)` loads YAML, merges CLI overrides
- `get_data_builder(config_dict["dataset"])` returns a `BaseBuilder` subclass (KodCodeBuilder, GSM8KBuilder, GPQABuilder, TriviaQABuilder) that loads HuggingFace datasets and splits train/valid/test
- `MemGenModel.from_config(config_dict["model"])` instantiates the three sub-models (reasoner, weaver, trigger) from HuggingFace checkpoints
- `MemGenRunner(model, data_builder, config, working_dir)` orchestrates all training and evaluation

**Core modules**:

| Module | Path | Lines | Role |
|--------|------|-------|------|
| MemGenModel | `memgen/model/modeling_memgen.py` | 788 | Main model: reasoner + weaver + trigger + projection layers |
| MemGenWeaver | `memgen/model/weaver.py` | 126 | Latent query params + LoRA model that processes embeddings |
| MemGenTrigger | `memgen/model/trigger.py` | 46 | Binary classifier on hidden states |
| MemGenGenerationMixin | `memgen/model/modeling_utils.py` | ~350 | Autoregressive generation with trigger-augment loop |
| MemGenRunner | `memgen/runner.py` | 446 | Training orchestrator, creates SFT/GRPO trainers |
| WeaverGRPOTrainer | `memgen/trainer/weaver_grpo_trainer.py` | ~600 | Custom GRPO trainer (subclasses `trl.GRPOTrainer`) |
| TriggerGRPOTrainer | `memgen/trainer/trigger_grpo_trainer.py` | ~500 | Trigger-specific GRPO training |
| BaseBuilder / BaseEnv | `data/base_builder.py`, `data/base_env.py` | -- | Abstract data loading and environment interfaces |
| InteractionManager | `interactions/` | -- | Agent-loop abstraction (single-turn vs multi-turn eval) |

**Key architectural patterns**:
- **LoRA adapters**: Both weaver and trigger are `PeftModel` objects initialized from the same or different base LMs. Only LoRA A/B matrices and the weaver's query latent vectors are trained.
- **Projection layers**: Two `nn.Linear` bridges connect reasoner hidden space to weaver hidden space and back. These are trained only during weaver training.
- **`SFTTrainer` for weaver SFT**: Uses HuggingFace `trl.SFTTrainer`; the `MemGenModel._forward()` method masks latent positions from the loss.
- **`WeaverGRPOTrainer` for weaver GRPO**: Subclasses `trl.GRPOTrainer`, overrides generation to use `MemGenModel.generate()` (which runs the trigger-augment loop) instead of standard generation.
- **Two-stage training as two separate runs**: The runner trains either weaver or trigger (not both at once), controlled by CLI flags `train_weaver`/`train_trigger`. The trained component is fixed (`fix_component`) while the other is trained.

**Config structure** (`memgen.yml` / `requirements.txt`):
- Dependencies: `torch 2.7.1`, `transformers 4.55.4`, `trl 0.18.0`/`0.21.0`, `peft 0.17.1`, `deepspeed 0.17.5`, `omegaconf 2.3.0`, `accelerate`, `datasets`, `wandb`
- Training configs in YAML under `configs/latent_memory/{dataset}.yaml` control every hyperparameter including LoRA rank, latent length, augmentation frequency, learning rate, optimizer, etc.
- Three LM copies required: reasoner (frozen), weaver (LoRA), trigger (LoRA). Can all be the same model ID or different.

---

## 3. Performance/Benchmarks

The README links to HuggingFace-hosted checkpoints but does not include benchmark tables in the repository itself. The paper (ICLR 2026) reports results. Based on the repo structure:

- **Datasets supported**: GSM8K (math), GPQA (science), KodCode (code generation), TriviaQA (multi-hop QA)
- **Base models**: Qwen2.5-1.5B-Instruct, SmolLM3-3B
- **Training methods**: SFT (weaver) and GRPO (weaver + trigger separately)
- **Latent lengths**: 4-16 tokens (configurable per prompt vs inference)
- **Augmentation frequency**: Typically 1 prompt augment + up to 5 inference augments for single-turn; up to 6 prompt augments for multi-turn (TriviaQA)
- **Evaluation modes**: Static (single-turn QA with `compute_reward`) and Dynamic (multi-turn interactive environments like AlfWorld)

Latent lengths are remarkably small (4-16 tokens), suggesting that even very compact latent representations add measurable value.

---

## 4. Trade-offs

**Wins**:
- No external memory database or RAG pipeline needed; memory lives in the model's own hidden states.
- Very compact: 4-16 latent tokens per augmentation point, much smaller than full conversation history.
- LoRA-based training is parameter-efficient (only LoRA adapters + query vectors are trained).
- Plug-and-play: augments any causal LM without changing the base model architecture.
- Two-stage training cleanly separates "what to remember" (weaver) from "when to recall" (trigger).

**Loses / Limitations** (from code and FAQ):
1. **FSDP NOT supported**: The FAQ explicitly warns that FSDP does not work. Only DDP and DeepSpeed ZeRO-2 are supported.
2. **Batch size 1 for conversational SFT**: `_conversational_forward` asserts `input_ids.shape[0] == 1`, severely limiting throughput for multi-turn data.
3. **Fixed delimiter-based augmentation**: Augmentation only fires after specific delimiter tokens (`,`, `.`, `\n`). This may miss opportunities between other token boundaries.
4. **Two-stage training complexity**: Requires training weaver first, then trigger, with separate configs and checkpoints. The trigger can only be trained via GRPO (not SFT), adding RL engineering overhead.
5. **Memory is not persistent training data**: Latent tokens are generated fresh each forward pass; there is no mechanism to store/retrieve across inference sessions (it is "working memory" not "episodic memory").
6. **Recomputes weaver forward at each augmentation**: The weaver processes the entire prefix embedding sequence each time, which is O(N^2) in the number of augmentation points during generation.
7. **Hyperparameter sensitivity**: The README's FAQ (Q3) documents that trailing `\boxed{}` formatting (`\n` vs `.`) significantly affects results, indicating brittleness.
8. **No explicit license**: The repository has no LICENSE file, which creates uncertainty for derivative use.

---

## 5. Design Rationale

- **Why latent tokens instead of explicit memory retrieval?** To avoid the latency and complexity of external vector databases and to keep memory within the model's native distribution. The weaver's latents are processed by the same LM that generates tokens, so they are "in-distribution" for the attention mechanism.

- **Why delimiter-based augmentation points?** Pragmatic choice. Delimiters (sentence/thought boundaries) are natural places where a human might pause to reflect. The `_check_ends_with_delimiter` check is O(1) per token using precomputed token IDs, avoiding expensive decode operations during generation.

- **Why two separate models for weaver and trigger?** Decouples the capacity to generate useful latents from the decision of when to generate them. This prevents reward hacking where a single model could simply choose to never augment (reducing compute) or always augment (ignoring relevance).

- **Why LoRA adapters?** PEFT philosophy: the model's general knowledge stays intact. Only the ability to compress and recall experiences is learned via low-rank updates.

- **Why copy the base LM three times?** The reasoner is frozen, the weaver and trigger each need their own LoRA adapter and forward pass because they operate on different views of the data (weaver reads accumulated embeddings, trigger reads raw input_ids). This is memory-intensive but architecturally clean.

---

## 6. Transfer to Lyra

**One idea**: Adopt MemGen's **latent memory splicing** approach for Lyra's conversation context management. Instead of always appending raw conversation history to the prompt (which grows unbounded), use a small weaver-like module that periodically compresses recent turns into a fixed-length latent representation and splices it into the embedding stream.

**Workstream route**: SS4.4 (Long-Context & Capacity) -- Latent memory compression is a direct solution for context window overflow in agent loops.

**Impact**: 7/10. Could significantly reduce token consumption for long-running agent conversations while preserving relevant information. The compression is generative (not just truncation/retrieval), so it can synthesize and abstract past information.

**Effort**: 6/10. Requires: (a) training a small LoRA weaver on Lyra conversation traces, (b) designing augmentation point selection for agent turns (not just delimiters), (c) managing the two-stage training pipeline.

**Tier**: T2 (6-12 month horizon). The approach is proven academically (ICLR 2026) but needs engineering adaptation to Lyra's specific multi-agent architecture and conversation patterns.

**LICENSE**: No license in the repo. For transfer, the paper's academic publication (ICLR 2026) enables reproducing the described method, but directly using the repository code is not legally safe without a license. Recommendation: reimplement from paper description rather than copying code.
