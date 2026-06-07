# microsoft/SkillOpt -- Deep-Read

**Source**: https://github.com/microsoft/SkillOpt
**Paper**: https://arxiv.org/abs/2605.23904
**Project page**: https://microsoft.github.io/SkillOpt/
**PyPI**: `pip install skillopt`

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: SkillOpt treats an agent's text-based skill document (a `.md` system-prompt file) as trainable "weights" and optimizes it through a closed-loop pipeline -- **ReflACT** -- without ever touching the underlying model's parameters. The deployed artifact is a plain Markdown file (300-2000 tokens) that runs against the unchanged target model, adding zero inference-time overhead.

**Mechanism in detail**:

The framework separates concerns into two LLM roles:
- **Target model** (frozen): executes episodes using the current skill document as a system prompt. Never modified.
- **Optimizer model** (separate LLM call): analyzes trajectories, generates candidate edits, merges and ranks them.

The ReflACT pipeline (6 stages per step):

1. **Rollout** -- Execute a batch of episodes with the current skill document against the target model. Collect trajectories with `hard` (binary) and `soft` (partial credit) scores.
2. **Reflect** -- Group failed trajectories into minibatches (size M, default 8). For each minibatch, call the optimizer LLM to analyze failure patterns and propose edits. Successful trajectories are optionally analyzed too. Uses `ThreadPoolExecutor` for parallel analyst calls.
3. **Aggregate** -- Hierarchical merging of all analyst-generated patches via parallel LLM calls. Failure-driven patches take priority over success-driven ones. Multiple merge levels reduce N patches to 1.
4. **Select** -- "Gradient clipping" analog: rank all candidate edits by importance using another optimizer LLM call, keep only the top-L (where L = textual "learning rate", default 4, cosine-decayed to 2). Alternatively, use autonomous LR where the optimizer decides the edit count.
5. **Update** -- Apply selected edits to the skill document. Supports multiple modes: `patch` (add/delete/replace), `rewrite_from_suggestions` (full rewrite guided by suggestions), `full_rewrite_minibatch` (replace the entire skill).
6. **Evaluate** -- Roll out the candidate skill on a held-out validation split (`valid_seen`). Accept the candidate **only if** it strictly improves a gate metric over the current best score (`hard` exact-match, `soft` partial-credit, or `mixed` weighted average). **Rejected edits are saved to a step buffer** so subsequent analyst calls can avoid repeating ineffective patterns.

**Epoch-level mechanisms**:
- **Slow update** (end of each epoch): Compares current-skill vs previous-epoch-skill on a shared set of train items. Produces longitudinal guidance injected into a `<!-- SLOW_UPDATE_START -->` comment block in the skill document. Two modes: gated (paper default, evaluated on selection set) or force-accept (post-submission default).
- **Meta skill** (end of each epoch): Produces optimizer-side memory (not injected into the skill document) that improves future optimizer decisions -- an analog to momentum or optimizer state in neural network training.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

### Directory Structure

```
skillopt/                        # Core library
├── config.py                    # YAML config with _base_ inheritance + flatten
├── engine/
│   └── trainer.py               # ReflACTTrainer — the 6-stage loop (~2000 lines)
├── gradient/
│   ├── reflect.py               # Minibatch error/success analyst — parallel LLM calls
│   └── aggregate.py             # Hierarchical patch merging (failure-first)
├── optimizer/
│   ├── clip.py                  # rank_and_select — LLM-driven edit ranking
│   ├── scheduler.py             # LR schedulers (constant/linear/cosine/autonomous)
│   ├── meta_skill.py            # Optimizer-side cross-epoch memory
│   ├── rewrite.py               # Full skill rewrite from suggestions
│   ├── skill.py                 # apply_patch_with_report — structured add/delete/replace
│   └── slow_update.py           # Longitudinal epoch comparison + guidance injection
├── evaluation/
│   └── gate.py                  # Pure validation gate — accept/reject decision
├── model/
│   ├── common.py                # Token tracker, backend aliases, model defaults
│   ├── router.py                # Routes to appropriate backend
│   ├── azure_openai.py          # Azure OpenAI / OpenAI-compatible backend
│   ├── claude_backend.py        # Anthropic Claude backend
│   ├── codex_backend.py         # Codex CLI backend
│   ├── codex_harness.py         # Codex execution harness
│   ├── qwen_backend.py          # Qwen (vLLM) backend
│   └── minimax_backend.py       # MiniMax backend
├── envs/
│   ├── base.py                  # EnvAdapter ABC — abstract interface
│   ├── _template/               # Template for new benchmark adapters
│   ├── searchqa/                # SearchQA benchmark
│   ├── alfworld/                # ALFWorld embodied agent
│   ├── docvqa/                  # Document QA
│   ├── livemathematicianbench/  # Math reasoning
│   ├── spreadsheetbench/        # Spreadsheet code generation
│   └── officeqa/                # Tool-augmented QA
├── datasets/
│   └── base.py                  # BatchSpec, BaseDataLoader
└── prompts/                     # Prompt templates (.md files) for all stages
scripts/
├── train.py                     # Main training entry point
└── eval_only.py                 # Evaluate a skill without training
configs/
├── _base_/default.yaml          # Base config (single source of truth)
├── searchqa/default.yaml        # Per-benchmark configs (inherit from _base_)
├── alfworld/default.yaml
├── docvqa/default.yaml
├── ...
└── features/soft_gate.yaml      # Optional soft-gate feature config
tests/                           # 4 test files (test_json_utils, test_scoring, test_types)
ckpt/                            # Paper-aligned pretrained skills (GPT-5.5, 6 benchmarks)
data/                            # Split manifests (ID-only for most benchmarks)
```

### Entry Points

- **`scripts/train.py`**: Loads config with `_base_` YAML inheritance, applies CLI overrides (both structured `--cfg-options section.key=val` and legacy `--key val`), normalizes backend settings, builds the `EnvAdapter` from a lazy-imported registry, then creates and runs `ReflACTTrainer.train()`.

- **`scripts/eval_only.py`**: Loads a skill document from disk, builds evaluation environments for the specified split, runs rollout, scores with `compute_score`, and saves results.

- **CLI entry points** (via pyproject.toml `[project.scripts]`): `skillopt-train`, `skillopt-eval`.

### Data Flow

```
Config (YAML) → load_config (inheritance + flatten) → flat dict
train.py → get_adapter(cfg) → EnvAdapter subclass
         → ReflACTTrainer(cfg, adapter)
              → rollout(current_skill, train_env) → [RolloutResult]
              → reflect(results, current_skill) → [RawPatch]
              → merge_patches(failure_patches, success_patches) → merged Patch
              → rank_and_select(patch, edit_budget) → ranked Patch
              → apply_patch / rewrite → candidate_skill
              → evaluate_gate(candidate) → accept/reject
```

### Architecture Pattern

**Pipeline/Workflow** architecture with an **Abstract Adapter** pattern at the core. The `EnvAdapter` ABC defines the contract (build_train_env, build_eval_env, rollout, reflect, get_task_types), and each benchmark implements its own adapter. The trainer is completely environment-agnostic -- it never imports or references any specific environment module.

The optimizer module hierarchy mirrors neural network training concepts: `scheduler.py` = LR schedulers, `clip.py` = gradient clipping, `aggregate.py` = gradient accumulation, `gate.py` = validation-based early stopping, `rewrite.py` = full model update, `meta_skill.py` = optimizer momentum/state.

## 3. Performance/Benchmarks (real numbers from the repo)

From the README and paper description:

| Metric | Value |
|--------|-------|
| Evaluation scope | 52 (model, benchmark, harness) cells |
| Benchmarks | 6 (SearchQA, ALFWorld, DocVQA, LiveMathematicianBench, SpreadsheetBench, OfficeQA) |
| Target models | 7 (including GPT-5.5, GPT-5.4, GPT-5.3, GPT-5.2, GPT-5.1, GPT-5.0, Claude Sonnet 4.6, Qwen 3.5-4B, MiniMax M2.7) |
| Execution harnesses | 3 (direct chat, Codex CLI, Claude Code CLI) |
| Result | Best or tied-best on **all 52 evaluated cells** |
| GPT-5.5 lift (direct chat) | +23.5 points average over no-skill baseline |
| GPT-5.5 lift (Codex) | +24.8 points |
| GPT-5.5 lift (Claude Code) | +19.1 points |
| Skill document size | 300-2000 tokens (also described as ~2k-13k chars) |
| Training config | 4 epochs, batch size 40, edit budget 4 (cosine-decayed to 2) |
| Minibatch size | 8 trajectories per analyst call |
| Slow update samples | 20 train items per epoch |
| Workers | 16 parallel analyst threads |

**Skill transfer properties** (claimed):
- Optimized skills transfer across model scales (e.g., GPT-5.5-trained skill works on GPT-5.3)
- Transfer between Codex and Claude Code harnesses
- Transfer to nearby benchmarks without re-optimization

## 4. Trade-offs (wins vs loses)

### Wins
- **Zero inference-time cost**: The skill document is just a system prompt. No extra model calls, no fine-tuned weights.
- **Model-agnostic**: Works with any LLM backend. Tested on 7 different models across 4 API families.
- **Portable artifacts**: Skills are plain Markdown files. Easy to version, share, inspect, edit.
- **Strict no-regression guarantee**: The validation gate only accepts changes that improve held-out performance. Stronger guarantee than most self-improvement approaches.
- **Pragmatic training loop**: Every artifact (patches, rankings, skill snapshots, step records) is saved as JSON/Markdown. Resume from any step. Full audit trail.
- **Multi-backend support**: 6 backend implementations (Azure OpenAI, OpenAI-compatible, Claude, Codex CLI, Claude Code CLI, Qwen/vLLM, MiniMax).
- **Good engineering**: Config inheritance, lazy imports, `ThreadPoolExecutor` parallelism, resume support, token tracking, API key redaction.

### Loses
- **Expensive training**: Each training step requires multiple optimizer LLM calls (analyst per minibatch, hierarchical merging per level, ranking, possibly rewrite). With batch size 40, minibatch 8, that's ~5 analyst calls + merge calls + 1 ranking call per step.
- **Requires labeled evaluation data**: The validation gate needs a held-out `valid_seen` split with ground-truth answers. Not applicable for open-ended tasks or environments without automatic scoring.
- **Validation overfitting risk**: The skill is explicitly optimized against `valid_seen`. The paper tests on `valid_unseen` but the design choice for the gate metric (`hard` exact-match) creates pressure to optimize for the scorer's definition of correctness.
- **Two slow-update modes**: The main branch default (`force-accept`) diverges from the paper (`gated`). The README documents this transparently, but it means reproducing paper results requires a non-default config flag.
- **Partial artifact release**: Only 6 of the paper's GPT-5.5 skills are released. Remaining optimized skills and most benchmark split manifests are "being prepared for upload."
- **Incomplete data**: Most data/ manifests are ID-only lookup tables. Users must materialize full datasets separately. Only `alfworld_path_split/` can be used directly as `--split_dir`.
- **Small test suite**: Only 4 test files (test_json_utils, test_scoring, test_types). Core training loop, optimizer, aggregation, and reflection modules are untested.
- **Trainer complexity**: `engine/trainer.py` is ~2000 lines with dense conditional logic (resume handling, accumulation, slow update, meta skill, mode-specific branches). Hard to reason about edge cases.
- **API cost asymmetry**: The optimizer model typically does more token-heavy work (analyzing trajectories, merging patches) than the target model doing rollouts. Cost can be optimizer-dominated.

## 5. Design Rationale (why this approach)

The entire codebase and README are organized around a deliberate analogy to neural network training. This is not incidental -- it is the core design principle:

- Why **treat skills as trainable state**? Because hand-crafted skills don't improve under feedback, and one-shot generation is fragile. The training loop provides reproducible, monotonic improvement.
- Why **separate optimizer and target models**? To ensure the skill document remains a portable artifact that works with any frozen model. The optimizer can be arbitrarily expensive (large model, high reasoning effort) while the deployed artifact costs nothing extra.
- Why **hierarchical merging**? Because individual trajectory analyses produce conflicting or overlapping edits. Merging them via LLM replicates the effect of gradient accumulation in weight-space optimization -- combining weak signals into a coherent update direction.
- Why **edit budget / LR scheduling**? Because too many simultaneous edits destabilize the skill. The cosine-decayed edit budget (4->2) mirrors learning rate annealing, allowing large changes early and fine-tuning late.
- Why **validation gating**? Because self-improvement systems risk regression (the "self-delusion" problem). The strict accept/reject gate provides a hard safety guarantee that the skill never degrades on the selection set.
- Why **slow update**? Because step-level edits are local and near-sighted. The epoch-level longitudinal comparison provides a global view, catching regressions and persistent failures that individual steps miss.
- Why **meta skill**? Because the optimizer itself can improve over time. Cross-epoch optimizer memory captures "what kinds of edits work in this environment" -- analogous to learning an optimizer (e.g., learned optimizer in meta-learning).

## 6. Transfer to Lyra (one idea + route)

### Transferable Idea: **Executive Skill Loop**

Adopt SkillOpt's core loop structure for Lyra: treat Lyra's system prompt and instruction set as an optimizable "skill document." When Lyra fails on a task, the system can:

1. Record the trajectory (agent observations, tool calls, environment feedback).
2. Use an optimizer LLM (could be stronger than the agent's model) to identify failure patterns.
3. Propose targeted edits to Lyra's instructions (add a new rule, refine an existing one, delete an outdated constraint).
4. Evaluate the candidate instructions on held-out validation tasks.
5. **Accept only if performance strictly improves** -- a no-regression guarantee for the agent's behavior.

The critical distinction from naive self-improvement: the **validation gate**. Without it, agents that rewrite their own instructions tend to "hack" the feedback signal or over-generalize from a single failure mode. SkillOpt's gate is the key safeguard.

### Workstream Route

**§4.x -- Meta-optimization / Executive Strategy** (Self-improving agent infrastructure)

The ReflACT loop operates at the meta-level: it does not change how Lyra executes a task, only the instructions that guide Lyra's execution. This fits naturally into a "self-improving agent" workstream alongside Lyra's existing architecture debates about routing, plugins, and commands.

### Impact, Effort, Tier

| Field | Value |
|-------|-------|
| Impact | 9/10 -- Directly addresses skill stagnation, a core unsolved problem for production agents. A Lyra that improves its own instructions from usage data would be qualitatively more valuable. |
| Effort | 7/10 -- Substantial but bounded. Requires: a task execution recorder, an evaluation harness with ground-truth scoring, an optimizer backend integration, and the pipeline orchestrator. The individual components are well-understood. |
| Tier | **Tier 1** -- High impact, achievable with current architecture. No model fine-tuning, no infrastructure changes. The skill document abstraction maps directly to Lyra's existing prompt management. |

### Implementation Sketch

```
1. Instrument Lyra's execution loop to record trajectories (tool calls, observations, outcomes).
2. Define a "validation split" of tasks with known correct answers (or a reward model).
3. Implement the ReflACT pipeline:
   a. Rollout: Run Lyra on training tasks with current instructions.
   b. Reflect: Use a strong optimizer model (e.g., Claude Opus) to analyze failed trajectories and propose instruction edits.
   c. Aggregate & Select: Merge and rank candidate edits.
   d. Update: Apply edits to Lyra's instruction set.
   e. Evaluate: Run candidate instructions on the validation split.
   f. Gate: Accept only if validation score strictly improves.
4. Repeat for N epochs, ending with an improved instruction set.
```

### License Note

MIT License -- fully permissive, no restrictions on use, modification, or redistribution.
