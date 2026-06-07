# laude-institute/terminal-bench -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: Terminal-Bench (T-Bench) is a benchmark and execution harness for evaluating AI agents on hard, realistic tasks inside real terminal environments.

**How it really works**:

T-Bench has two halves:

**(a) Task Dataset** -- ~100 hand-crafted tasks (beta, growing). Each task lives in its own directory and contains:
- `task.yaml` -- An English instruction, metadata (difficulty, category, tags), parser config, timeout settings, and a canary string (`terminal-bench-canary GUID ...`) inserted to prevent training-data contamination.
- `docker-compose.yaml` + `Dockerfile` -- An isolated environment (available software, dependencies, network setup). Each task can declare its own Docker image.
- `run-tests.sh` -- The evaluation script that installs test dependencies at runtime (not baked into the image, preventing test data from leaking) and runs the test suite.
- `tests/` -- Test files (e.g., `test_outputs.py`). These are hidden from the agent -- the harness copies them into the container only *after* the agent finishes.
- `solution.sh` -- An oracle/reference solution that demonstrates one valid approach (not used for grading, only for reference).

**(b) Execution Harness** -- The Python package `terminal-bench` (pip-installable, `tb` CLI). The `Harness` class orchestrates the full pipeline:
1. Spin up a Docker container per task (using the task's `docker-compose.yaml`).
2. Create a tmux session inside the container.
3. Give the agent the task instruction and let it interact with the terminal (send keystrokes, read output) in an episode loop.
4. After the agent signals completion (or times out), copy the test files into the container, run `run-tests.sh`, capture the output.
5. Parse test output (via a pluggable parser: pytest, SWE-bench, MLE-bench, etc.) into structured pass/fail per test case.
6. Record the result: resolved/unresolved, failure mode, token counts, timing, and an asciinema recording.

**The agent loop** (most interesting implementation detail, in `terminus_2.py`):
- Agent gets a prompt template that instructs it to output commands in JSON or XML format.
- LLM responds with `{"keystrokes": "...", "duration_sec": N}`.
- The terminal executes keystrokes (non-blocking with min timeout), then captures incremental output.
- Output is fed back as the next prompt. The loop runs for up to 1M episodes (practically unlimited).
- Double-confirmation on task completion -- agent must affirm twice to exit.
- Proactive summarization when context window gets tight (<8000 free tokens): LLM generates a summary, passes it to a "next agent" via question/answer handoff.
- Output truncation: terminal output exceeding 10KB is trimmed (first half + last half with omitted-bytes notice).
- Context unwinding: when context is exceeded, the most recent message pairs are dropped, then a summarization step compacts the remaining state.
- Three retry attempts per LLM call. On `OutputLengthExceededError`, it tries to salvage a truncated response. On `ContextLengthExceededError`, it unwinds and summarizes.

## 2. Architecture & Core Modules

### Entry Points
- **CLI**: `terminal_bench/cli/tb/main.py` -- Typer app, subcommands: `run`, `tasks`, `datasets`, `runs`, `cache`, `admin`.
- **Run orchestrator**: `terminal_bench/harness/harness.py` -- `Harness` class (800+ lines) that manages the full experiment lifecycle: dataset loading, agent creation, concurrent task execution (`ThreadPoolExecutor`), Docker orchestration, test execution, result aggregation.
- **Runs CLI**: `terminal_bench/cli/tb/runs.py` -- `tb runs create` (aliased as `tb run`), `tb runs resume`, `tb runs status`, `tb runs summarize`, `tb runs list`, `tb runs upload`.

### Core Data Flow
```
tb run --agent terminus-2 --model claude-3-7-sonnet
  |
  v
Harness.__init__()
  |-- Dataset.__init__()      # Load tasks from registry or local path
  |-- AgentFactory.get_agent_class()  # Resolve agent by name or import path
  |
  v
Harness.run()
  |-- _execute_tasks()         # ThreadPoolExecutor per task
       |-- _execute_single_trial()
            |-- TrialHandler   # Manages paths, config, parser
            |-- spin_up_terminal()  # Docker Compose up + tmux
            |-- _run_agent()        # agent.perform_task(instruction, session, ...)
            |-- _run_tests()        # Copy tests, run run-tests.sh
            |-- _parse_results()    # Parse test output via Parser
            |-- write results.json
```

### Agent Architecture
- `BaseAgent` (ABC) -- defines `perform_task()` interface + `_render_instruction()` for Jinja2 prompt templates.
- **Built-in agents** (in `terminal_bench/agents/`):
  - `terminus-2` -- The flagship: LLM-driven agent that emits JSON/XML commands in a loop. Most sophisticated agent with summarization, context unwinding, output truncation, and asciinema markers.
  - `terminus-1` -- Older simpler version.
  - `naive_agent` -- Minimal test agent.
  - `oracle_agent` -- Reads the reference solution and executes it directly (upper-bound baseline).
  - `null_agent` -- No-op (lower-bound baseline).
  - `installed_agents/` -- Adapters for external coding agents: `ClaudeCodeAgent`, `AiderAgent`, `CodexAgent`, `CursorCliAgent`, `GeminiCliAgent`, `GooseAgent`, `GrokCliAgent`, `MiniSweAgent`, `OpenCodeAgent`, `OpenHandsAgent`, `QwenCode` (`qwencoder`).
  - `mcp_agents/` -- MCP-based integrations: `GooseMCPAgent`, `MCPTerminus`.

### Terminal & Docker Layer
- `terminal/terminal.py` -- `Terminal` class wraps Docker Compose lifecycle (`start`/`stop`), delegates session creation to `TmuxSession`.
- `terminal/tmux_session.py` -- Low-level tmux interaction: `send_keys()` (blocking/non-blocking), `capture_pane()`, `get_incremental_output()` (diff-based tracking), `clear_history()`. Supports asciinema recording for replay.
- `terminal/docker_compose_manager.py` -- Wraps `docker compose` CLI commands for building, running, stopping containers, and file copy via tar archives.

### LLM Layer
- `llms/base_llm.py` -- `BaseLLM` ABC, exception types (`ContextLengthExceededError`, `OutputLengthExceededError`, `ParseError`).
- `llms/lite_llm.py` -- `LiteLLM` implementation using the `litellm` library (supports 100+ providers). Handles response_format, temperature, retries with exponential backoff, caching for Anthropic models, and token counting.
- `llms/chat.py` -- `Chat` class that wraps `BaseLLM` with message history management, cumulative token tracking (even after unwinding), and logging.

### Parsers (test output evaluators)
- `parsers/base_parser.py` -- `BaseParser` ABC + `UnitTestStatus` (PASSED/FAILED).
- `parsers/pytest_parser.py` -- Parses pytest short summary output.
- `parsers/swebench_parser.py`, `mlebench_parser.py`, `swelancer_parser.py`, `sweperf_parser.py` -- Parsers for other benchmark formats.
- `parsers/parser_factory.py` -- Resolves parser by name.

### Dataset & Registry
- `dataset/dataset.py` -- `Dataset` class loads task paths from registry (remote or local), supports task filtering by glob patterns, exclusion, and n_tasks limiting. Sorts tasks by estimated duration (longest-first) for optimal concurrent scheduling.
- `registry/client.py` -- `RegistryClient` downloads datasets from a registry server.
- `registry.json` -- Local registry listing dataset versions (e.g., `terminal-bench-core` versions `head`, `0.1.0`) with GitHub URLs, commit hashes, and task subsets.

### Configuration & State
- `config.py` -- Environment-driven configuration (AWS S3, DB).
- `utils/run_lock.py` -- `RunLock`, `DatasetLock`, `AgentLock`, `RunConfigLock` -- Pydantic models for serializing run configuration to `tb.lock` files, enabling resumability.

### Database
- `db.py` -- SQLAlchemy models for PostgreSQL storage (`run_metadata`, `task_results`, `trial_results`). Enabled for leaderboard submission and result tracking.

### Output & Logging
- Results are written as JSON per-task (individual `results.json`) and aggregated (top-level `results.json`).
- Run metadata (config, commit hash, timestamps) in `run_metadata.json`.
- Terminal sessions logged to text files and asciinema `.cast` files.
- Token counts tracked cumulatively even after context unwinding.

### Adapters (Other Benchmarks)
- `adapters/` contains bridges to run other benchmarks through T-Bench: `swebench`, `swelancer`, `sweperf`, `swesmith`, `mlebench`, `quixbugs`, `deveval`, `evoeval`, `appworld`, `algotune`, `cybench`, `aider_polyglot`, `USACO`.

## 3. Performance/Benchmarks

The paper (arXiv 2601.11868) and launch blog report numbers, but the codebase itself reveals these key metrics:

- **Dataset size**: ~100 tasks at beta launch (v0.1.0), named `terminal-bench-core`. Registry supports versioning for expansion.
- **Task difficulty range**: easy to hard, across categories like `software-engineering`, `file-operations`, `security`, `configuration`, `data-processing`, etc.
- **Scoring**: `accuracy` = resolved_trials / total_trials. `pass@k` computed for k values up to the number of attempts (powers of two + 5, 10).
- **Concurrency**: Default `n_concurrent_trials=4`, tunable. Uses `ThreadPoolExecutor` for parallel task execution.
- **Timeouts**: Per-task configurable (`max_agent_timeout_sec`, `max_test_timeout_sec`) with global multiplier override.
- **Oracle upper bound**: Running the reference `solution.sh` directly (no LLM) provides the "accuracy ceiling" for each task.
- **Leaderboard**: Hosted at tbench.ai, with database-backed submission upload.

## 4. Trade-offs

### Wins
- **Real terminal fidelity**: Agents interact with a real bash shell, tmux, and Docker -- no simulated environments. This catches failures that simulators miss (timing issues, I/O buffering, command availability).
- **Pluggable agents**: Anyone can bring their own agent via `import_path` (module:Class format). The factory pattern makes it trivial to add new agents.
- **Task isolation**: Each task gets its own Docker container and tmux session. No state leakage between tasks. Full cleanup on completion.
- **Comprehensive error taxonomy**: 10 failure modes (timeout, parse error, context length, output length, installation failure, etc.) -- not just pass/fail -- enabling detailed failure analysis.
- **Resumability**: Full run-lock serialization enables restarting interrupted runs without losing progress.
- **Recording**: asciinema captures session recordings with agent-inserted markers, enabling post-hoc debugging and replay.
- **Adapter ecosystem**: Can run SWE-bench, SWE-Lancer, MLE-bench, USACO, and other benchmark tasks through the same harness.

### Losses / Limitations
- **Dependency on Docker**: Heavy system requirement. Each task requires Docker build and runtime. Concurrent runs can consume significant resources.
- **~100 tasks is small** compared to software engineering benchmarks (SWE-bench has 2,294). The authors acknowledge this is a beta and plan to expand.
- **Tmux-based interaction is fragile**: Terminal output parsing depends on tmux `capture-pane` behavior, which can miss content during rapid output. The `get_incremental_output()` method acknowledges this with fallback to current screen.
- **No streaming support**: The `LiteLLM.call()` method explicitly raises NotImplementedError for streaming responses.
- **Output truncation**: Terminal output >10KB gets truncated (first half + last half). This can lose critical intermediate output.
- **No standardized difficulty calibration**: The README mentions difficulty levels but the schema uses free-form categories and tags, making cross-task comparison harder.
- **Context window management is reactive**: The agent only summarises/unwinds when it hits the context limit, rather than proactively managing context throughout execution.
- **Basic result analysis**: The `summarize` command shows accuracy and failure modes but lacks per-category breakdowns, token efficiency analysis, or comparison across runs.

## 5. Design Rationale

**Why real terminals, not simulations?** -- The authors chose Docker + tmux over simulated shells (like `bashlex` or restricted environments) because terminal interactions have subtle timing and environment dependencies that simulations only approximate. Real shells fail in realistic ways.

**Why per-task Docker images?** -- Each task declares its own `docker-compose.yaml` and `Dockerfile` so tasks can require specific software stacks (Python, C compilers, database servers, network configurations) without interfering with each other. This makes tasks reproducible and portable.

**Why tmux?** -- Tmux provides flexible pane capture, session persistence, and programmatic key sending. The `pipe-pane` mechanism enables real-time logging of all terminal output. Asciinema integration provides replay-capable recordings.

**Why the agent-loop architecture?** -- Terminus-2's episodic loop (LLM -> parse -> execute -> observe -> repeat) mirrors how a human would use a terminal: think of a command, run it, see the output, decide next step. The JSON/XML output format is a deliberate design choice to make command generation structured and parseable.

**Why separate test parsing from agent execution?** -- Tests run in a fresh shell (or same shell, configurable) to avoid agent contamination of test state. Test dependencies are installed at runtime (not baked into the container image) to prevent agents from accessing test code.

**Why the canary string?** -- Every task includes `terminal-bench-canary GUID 26b5c67b-...` to prevent the benchmark from appearing in LLM training data, following the BIG-bench canary pattern.

**Why `litellm` for LLM calls?** -- Rather than hard-coding provider-specific SDKs, the harness uses litellm's unified interface to support 100+ model providers. This makes it easy to run the same benchmark with any model.

## 6. Transfer to Lyra

### Transferable Idea: Agent-in-a-Sandbox Evaluation Loop

The Terminus-2 agent loop architecture is directly applicable to Lyra's verification system. The key pattern: an LLM emits structured commands (JSON keystrokes), executes them in a real environment (tmux inside Docker), observes the output, and continues in a loop until the task is solved or time runs out.

**For Lyra specifically**:
- Lyra's verification system (`lyra-verify`, `verification-loop`) could adopt the **episodic agent loop** pattern where each episode is: plan -> emit structured command -> execute -> observe -> plan. This is more robust than single-shot verification because it handles multi-step tasks and provides a replayable record.
- The **output truncation strategy** (keep first N/2 bytes, last N/2 bytes, report omitted size) is portable for Lyra's long-output handling.
- The **context unwinding + summarization** pattern when approaching token limits is a general technique for any long-running LLM agent loop.
- The **double-confirmation on task completion** prevents premature termination.

### Non-transferable parts
- Docker/tmux infrastructure is heavy. Lyra's modular verification should use lighter-weight sandboxing.
- The model-agnostic `litellm` layer is good; Lyra already has this via its extensible provider system.
- The per-task Docker image pattern is overkill for Lyra; a single sandbox environment with per-task setup scripts suffices.

### Route
- **Workstream**: `§4.x Verification & Testing` -- The episodic agent loop pattern maps directly to Lyra's verification subsystem design.
- **Alternative route**: `§5.x Architecture & Sandboxing` -- If Lyra adopts container-based sandboxing for its agent runner, the TmuxSession pattern (+ asciinema recording) is a clean implementation model.

### Estimated Impact, Effort, Tier
- **Impact**: 6/10 -- The episodic loop pattern improves verification thoroughness; context management strategies reduce timeout failures.
- **Effort**: 4/10 -- Low-medium. The core pattern is a loop with structured I/O; integration into Lyra's existing agent framework requires adapting the command format and removing Docker dependency.
- **Tier**: Tier 2 -- Targeted improvement to verification module, not a cross-cutting architecture change.
- **License Compatibility**: Apache 2.0 -- Fully compatible with Lyra's MIT license. Can freely adopt patterns and adapt code.
