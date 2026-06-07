# gepa-ai/gepa -- Deep-Read

- **URL**: https://github.com/gepa-ai/gepa
- **Language**: Python (3.10+)
- **License**: MIT
- **Built with**: setuptools, ruff (lint/formatter), pyright (type checking), pytest (testing), uv (dependency mgmt)
- **Dependencies (optional extras)**: litellm, tqdm, cloudpickle, datasets, mlflow, wandb, pydantic, langchain, llm-structured-confidence, swesmith, docker

## 1. Headline Feature & Mechanism

GEPA (Genetic-Pareto) is a framework for optimizing any system with textual parameters (prompts, code, agent architectures, configuration files, policies, SVGs) against any evaluation metric. It replaces RL/gradient-based optimization with **LLM-based reflective evolutionary search** guided by **Actionable Side Information (ASI)** -- diagnostic feedback from execution traces.

**How it really works** (the inner loop):

1. **Select** -- pick a candidate from the Pareto frontier (set of candidates that each excel on different subsets of the validation set). The frontier is tracked per-validation-example (`frontier_type="instance"`), per-objective (`"objective"`), hybrid, or per-example-per-metric (`"cartesian"`).
2. **Evaluate with traces** -- run the candidate on a small minibatch (default 3 examples), capturing full execution traces: error messages, profiling data, reasoning logs, compiler diagnostics.
3. **Build reflective dataset** -- the adapter's `make_reflective_dataset()` extracts per-component textual feedback from the traces. Each component gets a structured record: Inputs, Generated Outputs, Feedback.
4. **Reflect** -- an LLM (the "reflection LM") reads the reflective dataset, analyzes failure patterns, success patterns, and root causes, then proposes a new text for the selected component.
5. **Evaluate mutated candidate** -- run the mutated candidate on the same minibatch. Compare summed scores.
6. **Accept/Reject** -- if strict improvement (or improvement-or-equal), run full valset evaluation and add to the candidate pool, updating the Pareto frontier. If rejected, skip.
7. **Merge** (optional) -- cross-pollinate two Pareto-optimal candidates that each excel on different valset examples. Find their common ancestor, take components from each parent, propose a merged candidate.

The key conceptual innovation is **ASI as the gradient analogue**: where RL gradients tell a numerical optimizer which direction to move, ASI tells the LLM proposer *why* a candidate failed and *how* to fix it. The reflection LLM reads error messages, expected-vs-actual output, profiling traces, and proposes targeted fixes rather than random mutation.

A second key insight is **Pareto-efficient search**: by tracking frontiers per-example or per-metric, GEPA preserves specialized candidates that excel on a subset of data, preventing "averaging away" of hard-won improvements. This lets it discover candidates that work well on *specific* failure modes and later merge them.

A third insight is **mini-batch reflection**: showing only 3 examples per iteration makes each reflection step focused and tractable. Over many iterations, all examples get attention, and the Pareto frontier preserves gains across iterations.

## 2. Architecture & Core Modules

Entry points:
- `api.py` -- `gepa.optimize()` (high-level API for prompt optimization)
- `optimize_anything.py` -- `gepa.optimize_anything.optimize_anything()` (universal API for any text artifact)

Core modules:

| Module | File(s) | Role |
|---|---|---|
| **Engine** | `core/engine.py` | Main optimization loop: orchestrates reflective mutation and merge, evaluates on valset, manages state persistence, callbacks |
| **State** | `core/state.py` | `GEPAState` -- full persistent state: candidate pool, Pareto frontiers (instance/objective/hybrid/cartesian), valset evaluations, evaluation cache, budget hooks, checkpoint save/load with schema migration |
| **Adapter** | `core/adapter.py` | `GEPAAdapter` protocol -- the single integration point. Three responsibilities: `evaluate()` (run candidate on batch), `make_reflective_dataset()` (build per-component feedback from traces), optional `propose_new_texts()` (custom proposal logic) |
| **Data Loader** | `core/data_loader.py` | `DataLoader` protocol -- abstract data access via `all_ids()` + `fetch()`. `ListDataLoader` for in-memory lists |
| **Result** | `core/result.py` | `GEPAResult` -- immutable snapshot: best_candidate, lineage, val_subscores, Pareto maps, candidate tree (HTML/DOT) |
| **Callbacks** | `core/callbacks.py` | Event system: ~20 event types (optimization start/end, iteration start/end, candidate accepted/rejected, merge attempted/accepted/rejected, pareto front updated, etc.) |
| **Reflective Mutation** | `proposer/reflective_mutation/reflective_mutation.py` | `ReflectiveMutationProposer` -- select candidate, sample minibatch, evaluate with traces, build reflective dataset, call reflection LM, evaluate mutated candidate, return `ProposalOutput` |
| **Merge** | `proposer/merge.py` | `MergeProposer` -- find common ancestors of two Pareto candidates, check component diversity, propose merged candidate |
| **Candidate Selection** | `strategies/candidate_selector.py` | 4 strategies: `ParetoCandidateSelector`, `CurrentBestCandidateSelector`, `EpsilonGreedyCandidateSelector`, `TopKParetoCandidateSelector` |
| **Batch Sampling** | `strategies/batch_sampler.py` | `EpochShuffledBatchSampler` -- epoch-aware shuffling with minibatch |
| **Acceptance** | `strategies/acceptance.py` | `StrictImprovementAcceptance`, `ImprovementOrEqualAcceptance` |
| **Instruction Proposal** | `strategies/instruction_proposal.py` | Default LLM prompt template: renders reflective dataset as markdown, handles Image objects for multimodal reflection |
| **LM** | `lm.py` | LiteLLM-based wrapper with reasoning model detection, retries, cost tracking |
| **Experiment Tracking** | `logging/experiment_tracker.py` | WandB + MLflow adapter |

### Adapters (integration layer)

| Adapter | Description |
|---|---|
| `default_adapter/` | Single-turn LLM prompt optimization |
| `optimize_anything_adapter/` | Universal adapter for `optimize_anything()` API -- wraps user evaluators, handles parallel eval, caching (memory/disk), refiner loop, best-evals tracking |
| `dspy_adapter/` | DSPy program optimization |
| `dspy_full_program_adapter/` | Evolves entire DSPy programs (signatures, modules, control flow) |
| `langchain_adapter/` | LangChain pipeline optimization |
| `mcp_adapter/` | MCP tool descriptions and system prompts |
| `generic_rag_adapter/` | Vector-store-agnostic RAG optimization |
| `confidence_adapter/` | Logprob-aware classification optimization |
| `terminal_bench_adapter/` | Terminus terminal-use agent |
| `anymaths_adapter/` | Mathematical reasoning tasks |

### Data flow diagram

```
seed_candidate
    |
    v
GEPAEngine.run()
    |
    |-- Evaluate seed on valset -> initialize GEPAState
    |
    |-- Main loop (while not stopped):
    |       |
    |       |-- (optional) MergeProposer.propose() -> accept/reject
    |       |
    |       |-- ReflectiveMutationProposer.prepare_proposal()
    |       |       |-- CandidateSelector.select_candidate_idx() -> pick from Pareto front
    |       |       |-- BatchSampler.next_minibatch_ids() -> 3 examples
    |       |
    |       |-- ReflectiveMutationProposer.execute_proposal()
    |       |       |-- adapter.evaluate(minibatch, curr_prog, capture_traces=True)
    |       |       |       -> EvaluationBatch(outputs, scores, trajectories)
    |       |       |-- adapter.make_reflective_dataset() -> per-component feedback
    |       |       |-- propose_new_texts() -> reflection LM proposes new text
    |       |       |-- adapter.evaluate(minibatch, new_prog) -> new scores
    |       |       |-- return CandidateProposal
    |       |
    |       |-- Acceptance check (sum(scores) improved?)
    |       |       |-- YES: evaluate on full valset -> update state + Pareto front
    |       |       |-- NO: skip, log rejection
    |       |
    |       |-- State.save() -> checkpoint (pickle/cloudpickle)
    |
    v
GEPAResult (best_candidate, lineage, scores, Pareto maps)
```

## 3. Performance/Benchmarks

All numbers from the README and paper (arXiv:2507.19457):

| Metric | Value |
|---|---|
| **90x cheaper** | Open-source models + GEPA beat Claude Opus 4.1 at Databricks |
| **35x faster than RL** | 100-500 evaluations vs 5,000-25,000+ for GRPO |
| **32% -> 89%** | ARC-AGI agent accuracy via architecture discovery |
| **40.2% cost savings** | Cloud scheduling policy discovered by GEPA |
| **55% -> 82%** | Coding agent resolve rate on Jinja via auto-learned skills |
| **67% -> 93%** | DSPy Full Program adapter on MATH benchmark |
| **46.6% -> 56.6%** | AIME 2025 (+10pp) with GPT-4.1 Mini prompt optimization |
| **+142% student performance** | Augmenting RL-tuned teachers with GEPA (ARC blog) |
| **100% accuracy** | GEPA on clock-hands problem |
| **50+ production uses** | Across Shopify, Databricks, Dropbox, OpenAI, Pydantic, MLflow, Google, Microsoft, etc. |
| **100-500 evals** vs **10K+ for RL** | Massive sample efficiency advantage |

Specific academic benchmarks citing GEPA:

- **Prompt Triage (Stanford)**: median 53% relative improvement on 5 medical imaging tasks
- **Clinical NER (IEEE BigData)**: up to 12.5% F1 lift in zero-shot clinical NER
- **MEDEC error detection**: GPT-5 0.669 -> 0.785, Qwen3-32B 0.578 -> 0.690
- **OCR error rate**: cut by up to 38% across model classes
- **DivSkill-SQL (UCSD+Microsoft)**: +11.1pp on Spider2-Lite, +8.3pp on BigQuery
- **RLM-GEPA (AppWorld)**: 0.804 SGC leaderboard -> 0.911 SGC

## 4. Trade-offs (Wins vs Losses)

### Wins

1. **Extreme sample efficiency**: 100-500 evaluations vs 10K+ for RL/GRPO. A game-changer for expensive rollouts (scientific simulations, complex agents, compilation).

2. **Interpretable traces**: every prompt change is human-readable. The reflection LM writes *why* it made each change. No black-box weights.

3. **Works with API-only models**: no weights access needed. Optimize GPT-5, Claude, Gemini directly through API calls.

4. **Scarce data tolerance**: works with as few as 3 examples. No large training sets required.

5. **Complements RL**: can be used as a rapid initial optimization stage, then RL/fine-tuning for additional gains ("Better Together" paper).

6. **Multi-paradigm**: the `optimize_anything()` API cleanly unifies single-task, multi-task, and generalization modes.

7. **Rich adapter ecosystem**: DSPy, LangChain, MCP, RAG, custom -- broad integration surface.

8. **Production track record**: 50+ known production deployments at companies like Shopify, Databricks, Dropbox, OpenAI, Google, Microsoft.

### Losses/Limitations

1. **Reflection quality ceiling**: GEPA is only as good as the reflection LLM. If the LLM cannot diagnose the failure mode from the traces, the mutation will be poor. No formal convergence guarantees.

2. **Reflection cost**: each iteration requires LLM calls for both evaluation (task LM) and reflection (reflection LM). The reflection LM calls add overhead, though much less than RL training.

3. **State growth**: GEPAState grows with each accepted candidate (candidate pool, scores, Pareto fronts). No built-in pruning of dominated candidates (though `remove_dominated_programs` exists in utils).

4. **Adapter complexity**: users must implement `GEPAAdapter` to optimize a new system. While the protocol is clean (3 methods), correct implementation requires understanding the full data flow.

5. **Minibatch noise**: acceptance decisions are based on summed minibatch scores (default 3 examples). This introduces noise -- a candidate might score poorly on 3 examples but generalize well, or vice versa. The valset eval is the ground truth but happens less frequently.

6. **No built-in hyperparameter optimization**: `frontier_type`, `minibatch_size`, acceptance criterion, module selector all affect results. The paper likely provides heuristics but the defaults may not work universally.

7. **Pickle-based serialization**: state persistence uses pickle/cloudpickle, which can be fragile across Python/environment versions. Schema migration exists but adds complexity.

8. **Single-machine parallelism**: parallel proposals use `ThreadPoolExecutor` within a single process. No distributed optimization support (though adapter-level eval could be distributed).

## 5. Design Rationale

The core insight is that **text optimization is fundamentally different from numeric optimization**. Traditional optimization methods (gradient descent, evolutionary algorithms with numeric crossover/mutation) operate on differentiable or numerically-representable spaces. Text parameters (prompts, code, configurations) are discrete, combinatorial, and semantically structured.

**Why not RL?** RL treats execution traces as a single scalar reward, discarding all information about *why* a candidate failed. GEPA uses the full trace as structured feedback.

**Why ASI = gradient analogue?** In gradient descent, the gradient tells you the direction and magnitude of improvement. In text space, there is no gradient -- but the *diagnosis* of what went wrong (error messages, failure patterns, missing knowledge) provides the same directional information. The reflection LLM consumes this "text gradient" and proposes a targeted fix.

**Why Pareto frontiers?** Text candidates often excel on different data subsets. A prompt that solves algebra problems well might fail on geometry. Traditional aggregated metrics (average accuracy) would discard the algebra specialist. Pareto tracking preserves it. Periodic merge recombines strengths.

**Why mini-batches?** Showing all training examples to the reflection LLM would be expensive and overwhelming. A small mini-batch (3 examples) keeps each reflection step focused. Over iterations, epoch-shuffled sampling ensures all examples eventually contribute.

**Why adapters?** GEPA optimizes any system with textual parameters, not just prompts. The adapter protocol abstracts the system-specific details (how to construct the program from text parameters, how to evaluate it, how to extract diagnostics from traces) behind a clean interface.

**Why seedless mode?** Sometimes you don't have a starting point but know what "good" looks like. The seedless mode lets the LLM bootstrap the first candidate from the objective description, removing the need for a seed artifact.

## 6. Transfer to Lyra

### Transferable idea: **Reflective Self-Optimization via ASI-grounded mutation**

GEPA's core concept -- using LLM reflection on execution traces (ASI) to propose targeted text mutations -- maps directly to Lyra's need for self-improving agent behavior. Lyra generates prompts, tool descriptions, and agent configurations. Currently these are static or manually tuned. GEPA suggests a loop where Lyra:

1. Runs a trial on a task, capturing the full execution trace (tool calls, reasoning, errors)
2. Builds a "reflective dataset" from the trace (what worked, what failed, error messages)
3. Asks a reflection LM to propose improvements to the prompt/tool description
4. Validates the improved version on a held-out valset
5. Maintains a Pareto frontier of prompt variants that excel on different tasks

This is particularly applicable to Lyra's **auto-learned skills** and **prompt optimization** -- exactly the use case GEPA was designed for.

### Workstream route

**Section 4.3 (Memory & Self-Improvement)**, subsection "Automated Instruction Refinement":
- GEPA's mini-batch reflection loop maps to Lyra's need for continuous prompt/tool-description improvement
- The Pareto frontier concept maps to Lyra's need to maintain multiple skill/prompt variants for different task types
- The adapter pattern maps to Lyra's existing plugin/component architecture

Alternatively, **Section 4.2 (Architecture)**, subsection "Self-Modifying Agents":
- Treat each Lyra agent's system prompt as an optimizable parameter
- Use execution traces (ASI) as feedback for self-modification

### Impact/Effort/Tier

- **Impact**: 9/10 -- Self-optimizing agents are a transformative capability. Lyra could automatically improve its own prompts, tool descriptions, and agent configurations based on real usage traces. Every deployment gets better over time without manual prompt engineering.
- **Effort**: 7/10 -- Requires: (a) implementing a Lyra-specific `GEPAAdapter` that maps Lyra's component structure to text parameters, (b) setting up a reflection LM (could be a smaller model), (c) designing the reflective dataset format from Lyra execution traces, (d) managing state persistence across Lyra sessions. The adapter pattern already exists in Lyra's architecture; the main effort is designing the trace-to-ASI pipeline.
- **Tier**: Diamond (core differentiator -- few agent frameworks offer reflective self-improvement)

### Integration notes

- GEPA is MIT-licensed -- can be vendored or depended on directly
- The `optimize_anything` API is the cleanest integration point: Lyra would implement the evaluator function and configure `GEPAConfig`
- GEPA's `Image` class enables VLM-based reflection if Lyra uses images (screenshots, rendered outputs)
- GEPA's `CaptureStdio` feature could automatically capture Lyra's `print()` / logging output as ASI with zero code changes
- The `best_example_evals_k` parameter enables warm-starting: Lyra could seed new optimization runs with previous best evaluations
