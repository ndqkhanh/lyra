# ShengranHu/ADAS — Deep-Read

**Repository**: https://github.com/ShengranHu/ADAS
**Paper**: arXiv 2408.08435
**Venue**: ICLR 2025 (Outstanding Paper, NeurIPS 2024 Open-World Agent Workshop)
**License**: Apache 2.0
**Language**: Python (no package.json/Cargo.toml; plain requirements.txt)

---

## 1. Headline Feature & Mechanism

**Headline Feature**: Meta Agent Search -- an algorithm where a meta-level LLM *iteratively invents novel agentic system architectures by writing executable Python code*.

**How the code really works**: The meta agent receives the full archive of previously discovered agent architectures (each a `forward(self, taskInfo)` function + its fitness score on a validation set). It is prompted to propose the *next interesting* agent architecture, writing a complete Python `forward()` method that orchestrates sub-agents. A two-round Reflexion loop self-critiques the proposal (interestingness, bugs, improvements) before evaluation. The proposed code is `exec()`'d into the `AgentSystem` class, evaluated on held-out tasks, and scored with bootstrap confidence intervals. The archive grows with each generation, seeding subsequent proposals with more context. This is an LLM-in-the-loop evolutionary search where the representation space is source code and mutation/crossover are replaced by LLM prompting.

The core primitive is `LLMAgentBase`, a thin wrapper around an OpenAI chat completion call that takes `output_fields`, `role`, `temperature`, and `model`, and returns `Info` namedtuples. The meta agent composes these primitives into arbitrary control flows (loops, branching between specialized agents, voting, debate rounds, self-reflection cycles).

---

## 2. Architecture & Core Modules

### Entry Points
- `_mmlu/search.py`, `_arc/search.py`, `_drop/search.py`, `_gpqa/search.py`, `_mgsm/search.py` -- one per benchmark domain, each self-contained with its own copy of the search loop, evaluation logic, and agent base class. Duplicated (not shared).
- `_transfer_math/evaluation_gsm8k.py`, `evaluation_DROP.py`, `evaluation_ASdiv.py`, `evaluation_SVAMP.py`, `evaluation_gsmhard.py`, `evaluate_gpqa.py`, `evaluate_mmlu.py` -- cross-domain transfer evaluation scripts run after search.

### Core Source Files
- `search.py` (per domain): Contains the main loop -- load/save archive, call meta agent to propose new architecture, 2-step Reflexion, eval with debug retry, compute bootstrap CI, append to archive. Uses `ThreadPoolExecutor` for parallel task evaluation.
- `*_prompt.py` (per domain): Contains the initial archive (7 hand-crafted architectures: CoT, CoT-SC, Reflexion, LLM Debate, Step-back Abstraction, Quality-Diversity, Dynamic Role Assignment), the meta-agent system prompt template (domain-specific task description, utility code listing, WRONG-implementation examples), and Reflexion prompt templates.
- `utils.py` (per domain): Bootstrap confidence interval calculator (100k samples for 95% CI), data formatters, evaluation metrics (exact match for most domains, grid-matching for ARC).

### Key Data Structures
- `Info` namedtuple: `(name, author, content, iteration_idx)` -- the universal message type passed between agents.
- `LLMAgentBase`: Encapsulates a single LLM call. Constructor takes `output_fields`, `agent_name`, `role`, `model`, `temperature`. `__call__` accepts `[Info]` + instruction string, returns `[Info]`. Uses OpenAI `response_format={"type": "json_object"}`.
- `AgentSystem`: Container class whose `forward()` is dynamically replaced via `setattr` after `exec()` of the meta agent's generated code. Domain-specific variants exist (e.g., ARC's `AgentSystem.__init__` stores examples and test input for `run_examples_and_get_feedback`).

### Data Flow
1. `search.py:search()` loads/sets initial archive -> evaluates seed architectures -> enters generation loop
2. Meta agent prompted with full archive -> proposes `{"thought", "name", "code"}` via `get_json_response_from_gpt_reflect()`
3. Two Reflexion rounds refine the proposal
4. `evaluate_forward_fn()` calls `exec(forward_str, globals(), namespace)` -> `setattr(AgentSystem, "forward", func)` -> spawns `AgentSystem` per task -> aggregator runs via ThreadPoolExecutor
5. Bootstrap CI computed -> fitness string recorded -> archive appended -> JSON saved

### Architectural Pattern
**LLM-as-evolutionary-search with meta-programmed code generation**. The meta agent acts simultaneously as crossover (combining ideas from past architectures in the archive), mutation (proposing novel variations), and selection (it sees fitness values). The Reflexion steps serve as a critic/elitism filter.

---

## 3. Performance/Benchmarks

Results are stored in `results/` as JSON archives. All reported below use **gpt-3.5-turbo-0125** as the backbone (the meta agent uses gpt-4o-2024-05-13 for proposal).

| Domain | Baseline CoT (test) | Best Discovered (test) | Generation | Architecture Name |
|--------|---------------------|----------------------|------------|------------------|
| MMLU   | 65.4%               | 69.6%               | 9          | Domain-Specific Reflection with Dynamic Requests |
| DROP   | 64.2%               | 74.9%               | 5          | Collaborative Agent |
| MMLU*  | 65.4%               | 74.2%               | 4 (DROP)   | Dynamic Task Reassignment Agent (transferred from DROP) |

*The DROP results show Dynamic Task Reassignment cross-evaluating at 74.2% test on MMLU, suggesting transfer from one domain's discovered architecture to another.

Key observations from the archives:
- Not all novel architectures improve over baselines; many plateau near baseline levels (~64-68%)
- Some degenerate architectures collapse to ~10% accuracy (generations 23-25 in DROP, generations 23+ in MMLU)
- The initial 7 seed architectures provide strong baselines; Reflexion (Self-Refine) is often the strongest seed
- ARC uses `n_repreat=5` (evaluation budget multiplier) while MMLU uses `n_repreat=1`

---

## 4. Trade-offs

### Wins
- **Demonstrates LLMs can invent novel agent architectures** -- not just combine known prompting techniques but produce qualitatively new control flows (e.g., "Dynamic Task Reassignment", "Hierarchical Collaborative Reasoning") that match or exceed human-designed baselines.
- **Code as representation** is natural for LLMs, compositional, and executable -- avoids search over discrete hyperparameter grids.
- **Bootstrap confidence intervals** provide rigorous fitness estimates with uncertainty quantification.
- **Self-contained per-domain design** makes extension to new benchmarks straightforward.
- **Reflexion loop** catches many implementation bugs before costly evaluation runs.

### Loses
- **OpenAI-only** -- hardcoded to gpt-3.5-turbo, gpt-4, and gpt-4o through the `openai` Python library. No support for open-source models or API-agnostic backends.
- **`exec()` of untrusted code** -- the README includes an explicit safety warning. Model-generated code from the meta agent and from LLMAgentBase sub-agent outputs is executed without sandboxing.
- **Expensive search** -- each generation runs full validation on hundreds of tasks (128 tasks x 5 repeats = 640 evaluations for ARC), each evaluation potentially making multiple LLM calls depending on the architecture.
- **Context window grows linearly** -- the meta agent prompt includes the entire archive as serialized JSON. By generation 25, this is substantial and risks context truncation (there is an explicit error handler for `maximum context length`).
- **High variance** -- many proposed architectures do not improve over baselines; the quality of proposals degrades in later generations as the archive grows with mediocre designs.
- **Code duplication** -- `LLMAgentBase`, `get_json_response_from_gpt`, the search loop, and argument parsing are copy-pasted across all 5 domain directories rather than shared.
- **No issue tracker or CHANGELOG** -- no historical record of bugs, design decisions, or known limitations beyond what the README safety warning provides.
- **No unit tests, no CI** -- the repo is a research artifact, not production software.

---

## 5. Design Rationale

The core insight is that if you want to discover truly novel agent architectures -- not just tune hyperparameters of known designs -- you need a meta-level optimizer that operates in the *space of agent designs* rather than in a fixed parameter space. Code is the natural representation because:

1. **Compositionality**: A single `forward()` function can express any combination of sub-agents (sequential, parallel, conditional loops, debate rounds, hierarchical delegation).
2. **Executability**: Code can be evaluated directly via `exec()`, giving immediate fitness feedback.
3. **LLM-native**: Large language models are trained on code and generate code fluently.

The Reflexion two-step design reflects a pragmatic insight: LLMs generate buggy code on first attempt, so a self-critique step dramatically improves proposal quality before expensive evaluation.

The initial archive of 7 architectures provides the meta agent with a vocabulary of primitives (CoT, ensembling, self-reflection, debate, step-back abstraction, diversity, routing). The meta agent is not asked to generate architectures from scratch but to *extend* the archive, drawing inspiration from the successes and failures of previous attempts.

The bootstrap confidence interval (100k resamples, 95% CI) for fitness was chosen to provide robust estimate of architecture quality given the high per-task variance in LLM outputs.

---

## 6. Transfer to Lyra

### One Transferable Idea
**Meta-level agent architecture search via code generation**. ADAS demonstrates that an LLM can discover novel multi-agent architectures by iteratively proposing and evaluating agent system compositions. For Lyra, this maps directly to automated discovery of pipeline architectures: instead of a human designing the router/planner/plugin workflow topology, a meta agent could propose new Lyra pipeline configurations (as workflow YAML/JSON or plugin composition specs), evaluate them on benchmark tasks, and iteratively discover optimal topologies.

### Workstream Route
**Section 4.x -- Self-Improving Router/Planner**. The meta-search concept aligns with Lyra's need for automated pipeline optimization. ADAS's `exec(code)` approach would need adaptation to Lyra's plugin system -- rather than executing arbitrary Python, the meta agent would generate structured pipeline configurations validated against Lyra's schema before deployment.

### Assessment
- **Impact**: 7/10 -- Could unlock automated discovery of novel Lyra pipeline architectures not conceived by human designers, complementing manual design and parameter tuning.
- **Effort**: 8/10 -- Substantial engineering required: (a) building a sandboxed evaluation harness for Lyra pipeline variants, (b) designing a pipeline configuration DSL that the meta agent can generate, (c) managing the compute budget for multi-generation search, (d) porting the approach from OpenAI-only to Lyra's model-agnostic backend, (e) ensuring safety since generated configs could produce infinite loops or runaway costs.
- **Tier**: Opportunity -- Feasible and high-potential but would require dedicated workstream with significant infrastructure investment.

### License Compatibility
Apache 2.0 -- fully compatible with Lyra's licensing. Derivative use, modification, and redistribution are permitted with attribution.
