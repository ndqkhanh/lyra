# facebookresearch/HyperAgents -- Deep-Read

## 1. Headline Feature & Mechanism

HyperAgents implements a **self-referential, self-improving agent system** based on the Darwin-Godel Machine (DGM) architecture. The core loop: an LLM-powered **MetaAgent** recursively edits its own agent-generation code, which produces **TaskAgents** that solve specific benchmark domains. The MetaAgent is given access to both the source repository and the accumulated evaluation history, enabling it to introspect on past performance and modify its own code to improve future generations. This creates an open-ended evolutionary loop where the system's agent-writing abilities improve over time without human intervention.

**How it really works (five-step loop):**

1. **Setup**: The repo is cloned into a fresh Docker container. Initial baseline TaskAgent evaluations are run and stored.
2. **Parent selection**: A node from the evolutionary archive is selected (random, best, score-proportional, or score-child-proportional).
3. **MetaAgent invocation**: The MetaAgent (an LLM with `bash` and `editor` tools) receives the repo path and a folder of prior eval results. It modifies any part of the codebase (task_agent.py, meta_agent.py, ensemble.py, etc.) to improve downstream agent generation.
4. **Compilation & evaluation**: The modified agent is checked for importability, then evaluated across domain-specific harnesses. A staged eval strategy filters out clearly bad mutations early.
5. **Archive update & visualization**: Successful nodes are added to the JSONL archive. Progress plots and archive visualizations are generated automatically. The loop repeats.

The MetaAgent modifies code by producing **git diff patches** via its editor tool. The `run_meta_agent.py` entry point resets `domains/` before saving the patch, so only agent-generation logic changes are captured.

## 2. Architecture & Core Modules

```
Entry points:
  generate_loop.py          -- Main orchestration loop (argparse CLI)
  run_meta_agent.py         -- Invokes MetaAgent, saves model_patch.diff
  run_task_agent.py         -- Invokes TaskAgent for polyglot domain
  ensemble.py               -- Best-agent voting across archive
  select_next_parent.py     -- Parent selection strategy

Core modules:
  agent/
    base_agent.py           -- ABC with thread-safe logging
    llm.py                  -- litellm-backed LLM API (Claude, GPT, Gemini)
    llm_withtools.py        -- Tool-use loop (bash, editor) with retry logic
    tools/
      __init__.py           -- Dynamic tool loader from agent/tools/*.py
      bash.py               -- Async bash session with sentinel-based output capture
      edit.py               -- File editor (view/create/replace/insert/undo)

  meta_agent.py             -- MetaAgent.forward(repo_path, eval_path, iterations_left)
  task_agent.py             -- TaskAgent.forward(inputs) -> (prediction, msg_history)

  utils/
    constants.py            -- REPO_NAME = "hyperagents"
    common.py               -- read_file, extract_jsons, load_json_file
    git_utils.py            -- apply_patch, diff_versus_commit, reset_to_commit, commit_repo
    docker_utils.py         -- Docker/podman container lifecycle, GPU passthrough
    gl_utils.py             -- Archive management, parent selection, score tracking
    domain_utils.py         -- Per-domain configuration (scores, splits, staged eval)
    thread_logger.py        -- Thread-safe rotating file logger

  domains/
    harness.py              -- Generic eval harness (imports domain-specific utils)
    report.py               -- Score reporting
    search_arena/           -- Web search game domain
    paper_review/           -- Paper review quality domain
    balrog/                 -- RL agent training (BabyAI, Minihack, NLE)
    genesis/                -- Robot locomotion (Go2 walking/hop)
    imo/                    -- Olympiad math grading & proof
    polyglot/               -- Multi-language code repair (SWE-bench based)

  analysis/                 -- Progress plotting, bootstrap CI, significance tests, transfer analysis
  baselines/                -- DGM, SFT, AI reviewer baselines
```

**Data flow (generate_loop.py):**
```
setup_initial_gen() -> copy repo + initial evals -> archive = [initial]
loop over generations:
  parent = select_parent(archive, method=score_child_prop)
  container = build_docker() + apply lineage diff patches
  copy_prev_eval_to_container(container, output_dir)
  meta_agent.run(repo_path, evals_folder)  # LLM edits code
  check_compilation(meta_agent, task_agent)
  eval_produced_agent(container, domain)
  archive += [genid]
  plot_progress()
  (optional) get_ensemble_scores()
```

**Patterns used:**
- **Docker-per-generation isolation**: Each generation runs in a fresh container with host networking and optional GPU passthrough. Patches are applied via git, evals are copied in/out.
- **Staged evaluation**: Small subset first (10 samples for paper_review), proceeds to full eval only if score > 0 threshold.
- **ThreadPoolExecutor parallelism**: Domain evals within a generation run in parallel threads.
- **JSONL archive with metadata**: Each node has a `gen_{id}/metadata.json` tracking parent, patch files, eval validity.
- **LiteLLM abstraction**: Single API call abstraction supporting 14+ model variants across Anthropic, OpenAI, and Google.

## 3. Performance/Benchmarks

The repository does **not contain raw benchmark result files** in the source tree. Experiment logs are hosted externally (Google Drive link in README). The following can be inferred from the source and the arXiv abstract (2603.19461):

**Domains tested (from domain_utils.py and setup_initial.sh):**
- `search_arena` -- web search game (accuracy)
- `paper_review` -- paper quality assessment (accuracy)
- `balrog_babyai`, `balrog_babaisai`, `balrog_minihack`, `balrog_nle` -- RL game training (progress %)
- `genesis_go2walking`, `genesis_go2walkback`, `genesis_go2hop` -- robot locomotion (fitness)
- `polyglot` -- multi-language code repair (accuracy)
- `imo_grading` -- Olympiad math grading (accuracy)
- `imo_proof` -- Olympiad math proof correctness (points %)

**Baselines compared (from analysis/plot_comparison.py colors/methods):**
- DGM (original Darwin-Godel Machine)
- DGM with customization
- DGM-HA without open-ended exploration
- DGM-HA without self-improvement
- SFT (supervised fine-tuning)
- Representative Baseline
- Various parent selection variants (random, modifiable, score-child-prop)
- Transfer experiments across domains and runs

**Claimed result (abstract):** DGM-H "outperforms baselines without self-improvement or open-ended exploration, as well as prior self-improving systems." Meta-improvements are claimed to "transfer across domains and accumulate across runs."

**Staged eval sample sizes** (from domain_utils.py): 10 for search_arena/paper_review/imo_grading/polyglot/imo_proof, 1 for balrog, 3 for genesis. Full eval uses -1 (all).

## 4. Trade-offs

**Wins:**
- **True self-referential loop**: The MetaAgent edits its own code, enabling genuine open-ended improvement without human-in-the-loop.
- **Domain generality**: 11 different domain configurations across code, games, robotics, math. The same MetaAgent loop works for all.
- **Container isolation**: Docker per generation ensures reproducible evals and prevents side effects from bad code mutations.
- **Staged eval efficiency**: Small sample first avoids burning API budget on clearly bad mutations.
- **Archive-based exploration**: Parent selection with novelty pressure (score_child_prop) prevents premature convergence.
- **Ensemble support**: Agent predictions can be ensembled across archive nodes via `ensemble.py`.
- **Transfer learning**: The `transfer_utils.py` module supports zero-shot transfer of meta-improvements across domains.

**Losses:**
- **Extreme computational cost**: Each generation requires 1+ LLM API calls for the MetaAgent, plus Docker setup, plus full domain evaluation. A 10-generation run could cost hundreds of dollars in API fees plus GPU time.
- **Python-only and single-entry**: The MetaAgent can only modify Python files; the bash tool provides general capability but the architecture is strongly coupled to the Python/Docker stack.
- **No error recovery in loop**: If the MetaAgent produces a non-compilable change, that generation is wasted (metadata marks `valid_parent: False`). The loop continues but the parent's lineage is dead.
- **Synchronous, blocking loop**: Generations run sequentially. No support for parallel branching or asynchronous exploration.
- **Docker dependency**: Requires Docker (or Podman) installed and running. GPU passthrough is fragile, especially with Podman's CDI model.
- **No test suite in source**: CONTRIBUTING.md mentions "ensure the test suite passes" but no tests are present in the repository. Reliability depends on the compilation check only.
- **LiteLLM coupling**: All model interactions go through litellm, which means any litellm bug or API change can break the entire loop. Proxy/Firewall configuration is Facebook-specific.
- **No built-in cost tracking**: The system has no budget-awareness mechanism. The `iterations_left` parameter is passed to MetaAgent but not used in the current implementation.
- **CC BY-NC-SA 4.0 license**: NonCommercial restriction limits production use in commercial settings.

## 5. Design Rationale

**Why LLM-as-code-mutator?** Rather than using hand-crafted mutation/crossover operators (traditional evolutionary computation), the system leverages an LLM's code understanding to make semantically meaningful edits. The MetaAgent can read eval results and infer which parts of its own code need improvement -- something impossible with random mutation.

**Why containers?** The system involves executing LLM-generated code against real benchmarks. Docker provides:
- Reproducibility (same base environment every generation)
- Safety (containers can be killed if generated code goes rogue)
- GPU isolation (for robotics domains requiring CUDA)
- Clean git reset between generations (domains/ folder is always reverted)

**Why staged evaluation?** Full evaluation on all domains is expensive (hours of compute per generation). The staged eval approach (small subset first, proceed only if score > 0) acts as a cheap fitness filter, discarding clearly bad mutations before investing compute.

**Why score_child_prop parent selection?** The combination of score-proportional selection with a child count penalty (exponential decay with sqrt of child count) balances exploitation (high-scoring parents) with exploration (parents with fewer descendants get higher probability). This is a standard quality-diversity technique adapted for the LLM self-improvement setting.

**Why the ensemble option?** Different generations may specialize in different aspects of task solving. The ensemble module (`ensemble.py`) picks the best-performing node for each question, creating a strong baseline from the archive without further training.

**Why JSONL archive format?** The append-only JSONL format (one JSON object per line, each containing the full archive snapshot) enables:
- Resume from any point (`--resume_from`)
- Complete lineage reconstruction
- Consistent state even if a generation crashes mid-write

## 6. Transfer to Lyra

**Transferable idea: Self-referential meta-improvement loop with evaluation-driven introspection.**

HyperAgents' key insight is that the MetaAgent can inspect its *own* previous evaluation results to inform code changes. Applied to Lyra, this suggests building a **Meta-Critic agent** that receives:
- The current Lyra system prompt, skill definitions, and tool configurations
- A log of previous run outcomes (pass/fail on test suites, user satisfaction scores, latency metrics)
- Instructions to edit its own configuration to improve future outcomes

Lyra's architecture already has a plugin/skill system and a router for tool selection. The HyperAgents pattern would add an **introspective optimization loop**: after each Lyra run, a Critic agent reviews the run log and suggests prompt/configuration patches, which are stored and automatically applied on the next invocation.

**Recommended workstream route:** This maps to SS4.x (Self-Improving Agent Loop) in the Lyra architecture. Specifically, integrate the Meta-Critic into the existing plugin lifecycle -- after each run completes, invoke a `post_run_hook` skill that reads the execution trace and produces a diff to `system_prompt.md` or skill definitions.

**Impact:** 7/10 -- Adds genuine self-improvement capability that compounds over time. Lyra currently has no mechanism to learn from its own mistakes except manual prompt engineering.

**Effort:** 8/10 -- Requires building the evaluation-trace pipeline, the Critic agent skill, safe patch application logic, and a versioned configuration store. The core loop is ~500 lines of Python but the infrastructure (trace collection, safe rollback, cost budgeting) is substantial.

**Tier:** Tier 1 (long-term strategic). This is a fundamental capability that requires the rest of Lyra's architecture to be stable first.

**LICENSE:** CC BY-NC-SA 4.0 (NonCommercial). The code can be studied and adapted for non-commercial Lyra. For commercial use, the idea (self-referential LLM-as-code-mutator) is a well-known research pattern, not protectable -- only this specific implementation is licensed.
