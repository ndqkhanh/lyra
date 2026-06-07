# jennyzzt/dgm -- Darwin Godel Machine: Deep-Read

## 1. Headline Feature & Mechanism

**Open-ended evolution of self-improving coding agents** via a Darwinian loop. The system iteratively (1) selects a "parent" agent from an archive, (2) diagnoses a concrete weakness by inspecting SWE-bench failure logs, (3) prompts an LLM (currently o1-2024-12-17 for diagnosis, claude-3.5-sonnet or o3-mini for coding) to propose a code change to the agent's own source code (primarily `coding_agent.py`, `tools/`, `utils/`), (4) evaluates the modified agent on a subset of SWE-bench tasks inside an isolated Docker container, and (5) archives successful mutations for the next generation.

**Key mechanism -- the "diagnose-then-patch" loop:**

- `DGM_outer.py` orchestrates the outer evolutionary loop: up to 80 generations, 2 self-improvement attempts per generation, parallelized via `ThreadPoolExecutor`.
- `choose_selfimproves()` uses probabilistic parent selection (score-proportional or score-child-proportional -- sigma(x) = 1/(1+exp(-10*(x-0.5))) on accuracy, with child-count regularization to maintain diversity).
- `self_improve()` in `self_improve_step.py` runs the full inner loop inside Docker:
  1. Build/start a `dgm` container.
  2. Copy in the full accumulated parent patch chain.
  3. Apply all patches via `patch -p1`.
  4. Commit the patched state as a git baseline.
  5. Diagnose the selected SWE-bench failure via an LLM (o1) which analyzes agent logs, predicted patches, test patches, and eval logs to produce a JSON problem description.
  6. Run the coding agent (`coding_agent.py` with a 30-minute timeout) against that problem description inside the container.
  7. Extract the resulting `model_patch.diff`.
  8. Evaluate the new agent on SWE-bench subsets (small, conditional medium) via the SWE-bench harness.
  9. Optionally post-diagnose with another o1 call to score the improvement (-2 to +2).
- `filter_compiled()` checks that the run produced non-empty patches and properly evaluated against the expected number of issues.
- `update_archive()` adds compiled children to the archive (either keep_all or keep_better with noise leeway).

The **coding agent** itself (`coding_agent.py`) is a Claude/OpenAI-based agent that loads tools (`edit.py`, `bash.py`), receives a problem statement and a git repo, and iterates with tool-calling support via `llm_withtools.py`. The polyglot variant (`coding_agent_polyglot.py`) handles C++, Go, Java, JavaScript, Python, and Rust tasks.

**Confirmed benchmark** (from the paper arxiv 2505.22954): Starting from 28.67% pass@1 on SWE-bench Verified, DGM evolves agents reaching **45.83% pass@1 after 80 generations** (Figure 3 in the paper). The best agent lineage achieves 51% on the full SWE-bench Verified. The system also evolves agents that improve from 0% to 100% on held-out hallucination detection.

## 2. Architecture & Core Modules

```
jennyzzt__dgm/
|-- DGM_outer.py           # ENTRY POINT: evolutionary outer loop (generations, selection, archive)
|-- self_improve_step.py   # Inner self-improvement loop (diagnose, patch, eval inside Docker)
|-- coding_agent.py        # SWE-bench coding agent (AgenticSystem class, tool-use loop)
|-- coding_agent_polyglot.py  # Polyglot variant (Python/Rust/Go/Java/C++/JS)
|-- llm.py                 # Unified LLM abstraction (Anthropic Claude, OpenAI, Bedrock, Vertex AI, DeepSeek)
|-- llm_withtools.py       # Tool-calling wrapper (Claude native tools, OpenAI responses API, manual tool format)
|-- test_swebench.py       # Standalone SWE-bench evaluation script
|-- tools/
|   |-- edit.py            # File create/view/edit tool (view file, create new, overwrite entire file)
|   |-- bash.py            # Async bash shell session tool (2-min timeout, sentinel-based output parsing)
|-- utils/
|   |-- common_utils.py    # read_file, load_json_file
|   |-- docker_utils.py    # Docker lifecycle (build_image, create_container, copy_to/from, cleanup)
|   |-- evo_utils.py       # DGM metadata loading, patch path traversal, performance aggregation, compilation check
|   |-- git_utils.py       # diff_versus_commit, reset_to_commit, apply_patch, filter/remove patches
|   |-- eval_utils.py      # Test report parsing, score computation, LLM tiebreaker
|   |-- swe_log_parsers.py # SWE-bench repo-specific log parsers
|-- prompts/
|   |-- self_improvement_prompt.py  # Diagnose prompts (emptypatches, stochasticity, context_length, generic)
|   |-- diagnose_improvement_prompt.py  # Post-improvement analysis prompt (score -2..2)
|   |-- tooluse_prompt.py            # Manual tool-use format prompt for non-native-tool models
|   |-- testrepo_prompt.py           # Test command extraction and description
|-- swe_bench/              # SWE-bench harness (cloned from princeton-nlp/SWE-bench)
|-- polyglot/               # Polyglot benchmark (cloned from Aider-AI/polyglot-benchmark)
|-- tests/                  # Unit tests for DGM system
|-- analysis/               # Plotting and visualization (Plotly interactive trees, matplotlib progress curves)
|   |-- plot_comparison.py          # DGM vs baselines comparison plots
|   |-- plot_progress.py            # Single-run progress plots (best, avg, lineage)
|   |-- visualize_archive.py        # Graphviz+Plotly archive tree visualization, analysis stats
|-- Dockerfile              # python:3.10-slim, installs build-essential + git + pip requirements
|-- requirements.txt        # datasets, anthropic, openai, docker, GitPython, pytest, etc.
|-- pytest.ini              # Pytest configuration
```

**Data flow:**
1. `DGM_outer.py:main()` initializes archive, enters generation loop.
2. Each generation: `choose_selfimproves()` picks (parent_commit, entry) pairs based on accuracy scores.
3. Each pair runs in a thread: `self_improve()` creates a Docker container, applies the patch chain, commits, diagnoses the failure, runs the coding agent with the new problem, extracts the diff, evaluates on SWE-bench, optionally post-diagnoses.
4. `filter_compiled()` verifies compilation; `update_archive()` adds to archive.
5. `dgm_metadata.jsonl` captures all state per generation.

**Architecture pattern:** Evolutionary algorithm with an LLM-in-the-loop mutation operator (diagnose-mutate-evaluate). The codebase follows a layered modular design: outer loop (`DGM_outer.py`) is agnostic to the inner loop (`self_improve_step.py`), which is agnostic to the LLM client (`llm.py`/`llm_withtools.py`). The Docker isolation layer (`docker_utils.py`) encapsulates container lifecycle cleanly.

## 3. Performance/Benchmarks

From the paper (arxiv 2505.22954) and code analysis:

- **SWE-bench Verified pass@1**: Starting from 28.67% (initial agent = claude-sonnet-3.5-20241022 on SWE-bench), DGM evolves to **45.83%** after 80 generations. The best agent scored **51%** on the full SWE-bench Verified dataset.
- **Ablation baselines** (from `plot_comparison.py` labels): DGM w/o Open-ended exploration ("no_darwin"), DGM w/o Self-improve ("no_selfimprove"), DGM Greedy. DGM outperforms all three.
- **Polyglot benchmark**: DGM evolves agents that improve coding ability across 6 languages (C++, Go, Java, JavaScript, Python, Rust).
- **Hallucination detection**: From 0% to 100% on held-out hallucination detection tasks (detects whether the coding agent is hallucinating).
- **Resource usage**: Each self-improvement attempt runs in a Docker container with a 30-minute agent timeout and 1.5-hour total timeout. Up to 2 parallel workers. SWE-bench evaluation uses up to 5 parallel workers.
- **Models used**: Claude 3.5 Sonnet (20241022) via Bedrock for coding, o1-2024-12-17 for diagnosis, o3-mini-2025-01-31 for polyglot coding agent self-improvement. Supports OpenAI, Anthropic, Bedrock, Vertex AI, DeepSeek, and OpenRouter backends.

## 4. Trade-offs (Wins vs Losses)

**Wins:**
1. **Demonstrates open-ended evolution**: The system does not plateau after 80 generations -- the paper notes continued improvement trends.
2. **Emergent specialization**: Different branches in the archive tree solve different types of failures (empty patches, stochasticity, context length), leading to a diverse population.
3. **Isolated evaluation**: Docker containers ensure reproducibility and prevent environment contamination.
4. **Comprehensive diagnosis**: The LLM-based diagnosis uses actual failure logs, predicted patches, test patches, and evaluation results -- a rich signal for improvement.
5. **Multiple baselines**: "no_selfimprove" (same agent, no code changes) and "no_darwin" (sequential, no branching) baselines rigorously separate the effect of open-ended evolution from simple prompt changes.

**Losses/Drawbacks:**
1. **Extremely expensive**: Each self-improvement attempt requires a Docker build, an o1 diagnosis call, a Sonnet coding session (up to 30 min), and full SWE-bench evaluation on small (and conditionally medium) subsets. 80 generations x 2 attempts = ~160 expensive runs.
2. **Evaluation noise**: SWE-bench evaluation is stochastic (multiple `num_evals`) and the system uses a 0.1 noise leeway threshold. The `filter_compiled()` function can reject valid improvements if evaluation doesn't reach expected issue counts.
3. **Patch chain fragility**: Accumulated patches applied sequentially via `patch -p1` can fail if patches conflict or the repository state diverges. The system does not handle merge conflicts -- it relies on clean application.
4. **Context window limits**: The system explicitly detects and handles "input too long" errors but the diagnosis prompt truncates logs at 250k characters, potentially losing information.
5. **No regression testing**: The coding agent's own tests are generated by the LLM, not validated against the full SWE-bench suite during the inner loop (only during evaluation).
6. **OpenAI/Anthropic dependency**: The entire system requires API keys for frontier models. The system cannot self-improve using weaker models.
7. **Single-entry mutation**: Each self-improvement focuses on ONE SWE-bench failure at a time, which may lead to overfitting to specific failure modes rather than general improvement.

## 5. Design Rationale

- **Why Darwinian evolution rather than RL?** The authors argue that open-ended evolution naturally handles diverse, ill-defined goals where reward functions are hard to specify. The "fitness" is directly SWE-bench pass rate -- grounded, measurable, but decomposed into specific failure cases.
- **Why LLM-as-mutator?** Traditional genetic programming uses random mutations; using an LLM to diagnose failures and propose targeted code changes produces intelligent, semantically meaningful mutations.
- **Why Docker isolation?** Self-improvement modifies the agent's own source code, so running in an isolated container prevents the evaluation process from corrupting the host environment and ensures clean reproduction.
- **Why probabilitistic parent selection?** The sigmoid score transform (sigma(10*(x-0.5))) amplifies differences in the 0.3-0.7 range where most agents operate. Child-count regularization prevents a single successful lineage from dominating.
- **Why patch chain accumulation?** Rather than keeping full snapshots, the system accumulates patches from parent to child, enabling git-based diff tracking and minimal storage. Each node stores only its incremental diff.
- **Why separate diagnosis and improvement models?** The diagnosis uses o1 (strongest reasoning) while the coding agent uses Claude Sonnet (fast, capable coder). This separates the hard reasoning task from the generation task, consistent with the pattern of using stronger models for analysis and cheaper models for execution.
- **Why manual tool format for non-native models?** The `tooluse_prompt.py` creates a `<tool_use>` XML-based manual tool format for models that lack native tool calling, ensuring cross-model compatibility.

## 6. Transfer to Lyra

**Transferable idea:** The **diagnose-mutate-evaluate evolutionary loop** can be applied to Lyra's skill/plugin system. Instead of manually engineering new skills, Lyra can analyze failure cases from its own execution traces, propose modifications to its skill definitions or routing logic, evaluate the modified configuration against a test suite (Lyra's E2E benchmarks), and iteratively improve.

Specifically: Lyra's **evaluation framework** (foundational-code-evaluator, result aggregation) already captures failure traces. We can add a DGM-style "self-improvement scheduler" that:
1. Identifies recurring failure patterns (e.g., empty responses, context length errors, routing failures) from Lyra's evaluation logs.
2. Uses a strong LLM (Opus 4.5) to diagnose the root cause and propose a modification to Lyra's skill definitions, prompt templates, or routing rules.
3. Applies the modification (via git patch, just as DGM does to its own source code) and re-evaluates.
4. Retains successful modifications in an archive, building a lineage of progressively better Lyra configurations.

The key insight is that DGM mutates **its own source code** (the agent's behavior), not just prompts or weights. For Lyra, this translates to mutating **skill implementations, tool definitions, and routing logic** -- the code that defines Lyra's behavior.

**Workstream route:** Section 4.x -- Self-Improving Agent Loop. Lyra's groundwork with evaluation harness and skill system makes this a natural fit.

**Impact (1-5):** 5 -- A self-improving loop would be Lyra's killer feature. No other agent framework has demonstrated open-ended improvement of its own architecture. The DGM paper (Sakana AI, 2025) already has significant attention.

**Effort (1-5):** 4 -- Requires: Docker-based evaluation isolation, an evaluation harness that can measure pass/fail per task, an LLM-based diagnosis module, a patch application and versioning system, and archive management. The patch application and versioning are the hardest parts because Lyra's configuration is complex (skills, tools, prompts, routing rules).

**Tier:** High (4.2)

**LICENSE:** Apache 2.0
