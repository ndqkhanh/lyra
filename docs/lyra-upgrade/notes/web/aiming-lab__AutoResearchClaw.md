# aiming-lab/AutoResearchClaw -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**AutoResearchClaw** is an autonomous 23-stage research pipeline that converts a single research topic into a conference-ready paper (NeurIPS/ICML/ICLR) with real experiments, real literature citations, and compiled LaTeX. The headline feature is the **PIVOT/REFINE autonomous decision loop** (Stage 15) combined with a **time-weighted self-learning evolution store** that causes future runs to improve without human retraining.

The pipeline is organized as 8 phases executed sequentially through a state machine (`pipeline/stages.py`, `pipeline/executor.py`):

```
Phase A: Scoping       (Stages 1-2)  Topic init, problem decomposition
Phase B: Literature    (Stages 3-6)  Multi-source search (OpenAlex/Semantic Scholar/arXiv), screening, knowledge extraction
Phase C: Synthesis     (Stages 7-8)  Gap analysis, multi-agent debate hypothesis generation
Phase D: Design        (Stages 9-11) Experiment protocol, code generation (AST-validated), resource planning
Phase E: Execution     (Stages 12-13) Sandbox/Docker/SSH/Colab experiment execution with self-healing repair
Phase F: Analysis      (Stages 14-15) Statistical analysis, PROCEED/PIVOT/REFINE decision
Phase G: Writing       (Stages 16-19) Outline, draft, peer review (multi-agent), revision
Phase H: Finalization  (Stages 20-23) Quality gate, knowledge archive, LaTeX export, citation verification
```

Three stages are **gates** (5, 9, 20) that pause for human approval. Stage 15 can trigger a PIVOT (back to Stage 8) or REFINE (back to Stage 13) with automatic artifact versioning, preventing infinite loops via `MAX_DECISION_PIVOTS=2`.

**Key mechanism:** Every stage is an LLM call plus domain-specific tooling (web search, code execution, peer review). Results flow through a contract system (`pipeline/contracts.py`) that validates required keys and output files per stage. After each run, the `EvolutionStore` (`evolution.py`) extracts lessons from failures/warnings/metric-anomalies, classifies them into 6 categories, stores them in JSONL, and injects them into future stages as prompt overlays with 30-day half-life time-decay weighting.

## 2. Architecture & Core Modules

### Entry Points
- `researchclaw/__main__.py` -- `python -m researchclaw` entry
- `researchclaw/cli.py` -- All CLI commands: `run`, `validate`, `doctor`, `init`, `setup`, `info`, `report`, `serve`, `dashboard`, `wizard`, `project`, `mcp`, `overleaf`, `trends`, `calendar`, `skills`, `profile`, `attach`, `status`, `approve`, `reject`, `guide`

### Core Modules
| Module | Purpose |
|--------|---------|
| `config.py` | `RCConfig` dataclass tree (frozen, nested dataclasses), YAML loading with validation + profile-driven defaults |
| `pipeline/stages.py` | `Stage` IntEnum (23 values), `StageStatus` enum, `TransitionOutcome` dataclass, `advance()` state machine, `gate_required()` logic, `GATE_ROLLBACK`/`DECISION_ROLLBACK` maps |
| `pipeline/executor.py` | `execute_stage()` dispatcher with `_STAGE_EXECUTORS` dict mapping each Stage to its executor function, ~3500 lines of stage implementations |
| `pipeline/runner.py` | `execute_pipeline()` orchestrator: sequential stage loop, checkpointing, evolution store, knowledge base writes, sentinel heartbeat |
| `evolution.py` | `EvolutionStore` (JSONL-backed), `extract_lessons()`, `build_overlay()`, 30-day half-life decay, MetaClaw cross-run skill injection |
| `adapters.py` | `AdapterBundle` with typed Protocol interfaces: `CronAdapter`, `MessageAdapter`, `MemoryAdapter`, `SessionsAdapter`, `WebFetchAdapter`, `BrowserAdapter` |
| `hardware.py` | `HardwareProfile` detection (NVIDIA CUDA / Apple MPS / CPU), remote SSH GPU detection, VRAM tier classification |
| `quality.py` | Template/placeholder detection via regex patterns, `QualityReport` dataclass |
| `config.researchclaw.example.yaml` | ~20 config sections with extensive inline documentation |

### Dependency Tree
Minimal runtime: `pyyaml`, `rich`, `arxiv`, `numpy`. Optional: `scholarly`, `crawl4ai`, `tavily-python`, `PyMuPDF`, `matplotlib`, `scipy`, `huggingface-hub`, `httpx`.

## 3. Performance/Benchmarks

The README cites these numbers from the repo's experiments:

- **2,699 tests pass** (pytest) across 90+ test files covering evolution, HITL, agents, pipeline stages, web search, MCP, sandbox, config, skills, citation verification
- **MetaClaw cross-run learning**: +18.3% composite robustness score, -24.8% stage retry rate, -40.0% refine cycle count in controlled A/B experiments
- **arXiv paper**: 2605.20025 ("AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration"), 35 authors from AIMING Lab
- **ARC-Bench**: 55-topic open-ended autonomous-research benchmark spanning ML (25), HEP (10), quantum (10), biology (7), statistics (3)
- **8 generated papers** showcased across math, statistics, biology, computing, NLP, RL, vision, robustness
- **Concurrent CI**: Runs 23 stages serially per pipeline, max 3 parallel tasks per stage

## 4. Trade-offs (wins vs loses)

### Wins
- **Fully autonomous**: No human intervention required for a complete research cycle (literature through publication-ready PDF)
- **Self-healing**: Failed stages auto-retry (up to configurable limit). NaN/Inf fast-fail in experiment output. Experiment repair loop diagnoses and fixes broken code.
- **Anti-fabrication**: 4-layer citation verification (arXiv ID -> CrossRef/DataCite DOI -> Semantic Scholar title -> LLM relevance scoring). VerifiedRegistry enforces ground-truth experiment data in paper text.
- **Multi-domain support**: Routes beyond ML to HEP physics (ColliderAgent via Magnus cloud), biology (COBRApy FBA modelling), statistics (simulation studies) -- each with a dedicated execution agent.
- **HITL co-pilot**: 6 intervention modes from full-auto to step-by-step, with SmartPause (confidence-driven dynamic pausing), idea workshop, baseline navigator, paper co-writer.
- **Self-learning**: Time-weighted evolution store (30-day half-life) + MetaClaw bridge for cross-run skill generation.
- **Platform-agnostic**: ACP-compatible with Claude Code, Codex CLI, Copilot CLI, Gemini CLI, Kimi CLI, Ollama.

### Losses
- **LLM-cost dominated**: Each of 23 stages is an LLM call. A single run consumes significant tokens for the topic init, literature review, debate, paper writing, peer review, etc.
- **Experiment realism**: Sandbox mode executes real code but the experiment designs and metrics are generated by the LLM. The "realness" of results depends on the LLM generating correct, non-fabricated code.
- **Knowledge base is file-based**: Uses markdown/obsidian flat files for the 6-category KB, not a vector database or graph DB. No built-in semantic retrieval.
- **Zero-shot per domain**: No fine-tuned models per domain. Each research run starts from scratch with no domain-specific pretrained weights. The skill library mitigates this but does not replace actual training.
- **No multi-run experiment tracking**: No wandb/MLflow-style run comparison across pipeline executions. The evolution store tracks lessons but not experiment metrics.
- **Docker is optional but recommended**: Without Docker, sandbox execution uses the local Python environment, which is less secure and reproducible.
- **OpenCode external dependency**: Best experiment code generation requires installing `opencode-ai` via npm (Node.js dependency).
- **No parallel pipeline stages**: Stages execute sequentially (max 3 parallel tasks within a stage for literature search). Full pipeline runtime is wall-clock additive.

## 5. Design Rationale (why this approach)

The architecture follows a **strict sequential pipeline with state machine orchestration** rather than a DAG/event-driven approach. This choice is intentional for several reasons:

1. **Deterministic reproducibility**: Each stage produces well-defined artifacts, and the checkpoint system enables resume-from-any-point. A parallel DAG would complicate checkpoint semantics.

2. **Human-in-the-loop compatibility**: Gates are natural pause points. The sequential model makes it unambiguous what to roll back to on rejection (each gate has a hardcoded `GATE_ROLLBACK` target).

3. **LLM as the universal primitive**: Every stage is essentially an LLM call with different prompts and context. The system treats the LLM as a general reasoning engine and uses prompt engineering (debate roles, perspective synthesis, skill overlays) rather than specialized models.

4. **Profile-driven defaults over inheritance**: Domain profiles (hep_ph, ml, etc.) deploy config defaults (experiment mode, Docker image, pip packages, target conference) rather than subclassed stage executors. This avoids deep inheritance and makes profiles trivially extensible via YAML files.

5. **Adapter Protocols over abstract base classes**: The OpenClaw bridge uses `typing.Protocol` (structural subtyping) rather than ABCs, which means OpenClaw can provide capabilities without importing or inheriting from ResearchClaw types.

6. **Time-decayed lessons over fixed rules**: Rather than hand-coded "if this error then do that" logic, the evolution store learns from actual failures and injects context into prompts. This is more adaptive but less predictable than static error handling.

## 6. Transfer to Lyra

### Most Transferable Idea
**The time-weighted self-learning evolution store with MetaClaw bridge for cross-run skill injection.** Lyra currently has no mechanism to learn from past pipeline failures or improvements across runs. Every run starts from scratch. The EvolutionStore architecture (JSONL-backed lessons with 30-day half-life, category classification, per-stage prompt overlay injection) is directly adaptable: extract failed stage+error, classify via keywords, store with timestamp, query by stage with time-decay weighting, and inject into prompt context.

### Workstream Route
**Section 4.x: Self-Improving Pipeline (Evolution/MetaClaw)** -- This maps to the evolution/self-learning workstream. The concrete mechanism (lesson extraction, classification, overlay injection) is implementable in Lyra's existing pipeline runner without architectural changes -- just add a `run_evolution_store()` call in the pipeline post-process and a `build_overlay()` call in each stage's prompt assembly.

### Assessment
- **Impact**: 8/10 -- Self-improving pipelines directly compound quality over time. The reported +18.3% robustness lift is significant.
- **Effort**: 5/10 -- The evolution store is ~500 lines of straightforward Python (JSONL, keyword classification, exponential decay). Integration requires adding overlay injection to each stage's prompt builder, which is mechanical but touches many files.
- **Tier**: Tier 2 (high-value mid-effort) -- Not as foundational as the core pipeline but provides a measurable quality multiplier that compounds with every run.
- **License**: MIT -- fully compatible for adoption and adaptation.
