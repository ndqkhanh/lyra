# sierra-research/tau2-bench — Deep-Read

**Quick ref**: MIT License | Python 3.12+ | arXiv 2506.07982 | ~4,500+ Python source files | 5 domains | >400 tasks | Active (v1.0.0, 2026)

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: A benchmark for evaluating conversational (customer-service) agents in a dual-control, tool-accentuated environment -- supporting both half-duplex (text, turn-based) and full-duplex (voice/audio-native, tick-based) evaluation across five real-world domains.

**Mechanism in detail**:

The framework runs a **three-actor simulation loop** (Agent, User Simulator, Environment) where:

1. **Agent** is an LLM prompted with a domain policy and tool set. It responds to user messages and/or calls tools.
2. **User Simulator** is a secondary LLM prompted with a scenario/instructions and optional user tools. It plays the role of a customer with a specific issue.
3. **Environment** maintains domain-specific state (an in-memory database) and executes tool calls (read/write operations on airline bookings, retail orders, telecom accounts, etc.).

The **Orchestrator** mediates the loop. In half-duplex mode (`Orchestrator`), it alternates messages: Agent->User->Agent->Environment->Agent, etc. In full-duplex mode (`FullDuplexOrchestrator`), it runs a tick-based simulation (200ms ticks) where agent and user produce audio chunks simultaneously via realtime APIs (OpenAI Realtime, Gemini Live, xAI Grok Voice, Amazon Nova Sonic, Qwen Omni, LiveKit cascaded).

**Evaluation** is four-dimensional, gated by the task's `reward_basis`:
- **Env (DB)**: Replay task's mutating tool calls on a fresh environment, compare final DB hash to reference.
- **Action**: Check every expected action (tool name + arguments) appears in the trajectory's tool calls. All must match for full credit -- binary reward per action, product across all actions.
- **Communicate**: Verify required information was conveyed to the user (info string match).
- **NL Assertion**: LLM-judged qualitative checks (WIP/experimental).

Final reward = product of all active basis dimensions. A task passes iff reward = 1.0.

## 2. Architecture & Core Modules

### Module Map

```
tau2/
  cli.py              -- CLI entry point (tau2 run, view, play, leaderboard, submit, etc.)
  config.py           -- All defaults: LLM models, timing, sample rates, providers, retries
  run.py              -- Facade -> delegates to tau2.runner
  __init__.py         -- Public API exports + deprecated aliases
  
  agent/
    base_agent.py     -- Abstract HalfDuplexAgent / FullDuplexAgent classes
    llm_agent.py      -- LLMAgent, LLMGTAgent (ground-truth), LLMSoloAgent (no user)
    discrete_time_audio_native_agent.py  -- Full-duplex voice agent
    base/             -- LLMConfig, streaming utils, participant base
  
  orchestrator/
    orchestrator.py           -- Half-duplex Orchestrator (turn-based)
    full_duplex_orchestrator.py  -- Full-duplex Orchestrator (tick-based)
    modes.py                  -- CommunicationMode enum
  
  environment/
    environment.py    -- Environment: wraps domain tools, DB, state management
    db.py             -- In-memory DB abstraction
    tool.py           -- Tool wrapper
    toolkit.py        -- ToolKitBase, signatures, types
  
  user/
    user_simulator.py           -- LLM-based user simulator for half-duplex
    user_simulator_streaming.py  -- Voice streaming user simulator for full-duplex
    user_simulator_base.py       -- HalfDuplexUser / FullDuplexUser bases
  
  domains/
    airline/          -- 50 tasks, policy + tools
    retail/           -- 114 tasks
    telecom/          -- 114 tasks + workflow variant
    banking_knowledge/ -- 97 tasks + RAG pipeline configs
    mock/             -- Lightweight test domain
  
  evaluator/
    evaluator.py              -- Top-level evaluate_simulation() dispatches to sub-evaluators
    evaluator_action.py       -- ActionEvaluator, FullDuplexActionEvaluator
    evaluator_communicate.py  -- CommunicateEvaluator
    evaluator_env.py          -- EnvironmentEvaluator (DB + env assertions)
    evaluator_nl_assertions.py -- NLAssertionsEvaluator (LLM-judged)
    reviewer.py               -- LLM conversation reviewer, hallucination detection
  
  runner/
    simulation.py  -- Layer 1: run_simulation()
    build.py       -- Layer 2: build_agent, build_user, build_orchestrator
    batch.py       -- Layer 3: run_domain, run_tasks, run_single_task
    helpers.py     -- get_tasks, get_options, make_run_name
    checkpoint.py  -- Save/resume checkpointing
    progress.py    -- Status monitor, run_with_retry
  
  knowledge/        -- RAG pipeline: embedders, retrievers, postprocessors, caching
  voice/            -- Audio native: providers (openai, gemini, xai, nova, qwen, livekit), audio effects, TTS, transcription
  gym/              -- Gymnasium RL interface
  data_model/       -- Pydantic models: SimulationRun, Task, Results, AudioNativeConfig, etc.
  registry.py       -- Registry of domain/agent/user constructors
  metrics/          -- Agent metrics computation
  scripts/          -- viewer, manual mode, leaderboard, submission
  
data/tau2/
  results/final/    -- Pre-computed benchmark results for 20+ model/domain combos
  user_simulator/   -- Global simulation guidelines (system prompts for user LLM)
```

### Data Flow

```
CLI (tau2 run --domain retail --agent-llm gpt-4.1 --user-llm gpt-4.1)
  -> run.py:run_domain(TextRunConfig)
    -> runner/batch.py:run_tasks()  // loads tasks, manages seeds, concurrency, retries
      -> runner/batch.py:run_single_task()
        -> runner/build.py:build_orchestrator()  // constructs agent, user, env
        -> runner/simulation.py:run_simulation(orchestrator)
          -> orchestrator.run()   // simulation loop
          -> evaluate_simulation() // 4-dimension scoring
```

### Design Patterns

- **Template Method**: `BaseOrchestrator.run()` defines the simulation lifecycle (initialize -> step loop -> finalize). Subclasses implement `step()` for half-duplex vs full-duplex.
- **Strategy**: Each domain registers its own tools, policy, and environment via the Registry.
- **Layered Architecture**: Runner has 3 clean layers (simulation -> build -> batch) with clear dependencies.
- **Command**: CLI uses argparse subparsers mapping to handler functions.
- **Builder**: `build_agent`, `build_user`, `build_orchestrator` factory functions in the runner/build layer.
- **Config Objects**: `TextRunConfig`, `VoiceRunConfig`, `AudioNativeConfig` are Pydantic models carrying all parameters.

## 3. Performance/Benchmarks (real numbers from the repo)

All numbers from pre-computed results in `data/tau2/results/final/`. Pass@1 requires reward = 1.0.

| Domain | Agent LLM | User LLM | Pass@1 | Avg Cost | Tasks | Trials |
|--------|-----------|----------|--------|----------|-------|--------|
| Airline (50 tasks) | gpt-4.1 | gpt-4.1 | **56.0%** | $0.054 | 50 | 4 |
| Airline (50 tasks) | o4-mini | gpt-4.1 | **59.0%** | $0.051 | 50 | 4 |
| Airline (50 tasks) | gpt-4.1-mini | gpt-4.1 | **50.5%** | $0.013 | 50 | 4 |
| Retail (114 tasks) | gpt-4.1 | gpt-4.1 | **74.1%** | $0.058 | 114 | 4 |
| Retail (114 tasks) | o4-mini | gpt-4.1 | **71.5%** | $0.057 | 114 | 4 |
| Retail (114 tasks) | gpt-4.1-mini | gpt-4.1 | **66.0%** | $0.014 | 114 | 4 |
| Telecom (114 tasks) | gpt-4.1 | gpt-4.1 | **34.2%** | $0.110 | 114 | 4 |
| Telecom (114 tasks) | o4-mini | gpt-4.1 | **42.1%** | $0.092 | 114 | 4 |
| Telecom (114 tasks) | claude-3.7-sonnet | gpt-4.1 | **49.3%** | $0.582 | 114 | 4 |
| Telecom-workflow (114 tasks) | o4-mini (oracle plan + no user) | N/A | **98.9%** | $0.056 | 114 | 4 |
| Telecom-workflow (114 tasks) | o4-mini (oracle plan only) | gpt-4.1 | **87.9%** | $0.035 | 114 | 4 |

Key observations:
- Telecom is the hardest domain (<50% for all models even with strong user sim)
- Upper bound with oracle plans + no user sim is ~99%, meaning tasks are theoretically solvable
- gpt-4.1-mini is surprisingly competitive (66% retail) at 4-5x lower cost
- claude-3.7-sonnet leads on telecom (49.3%) but at 5x the cost of gpt-4.1
- Retail is the "easiest" domain (best model scores 74%)

## 4. Trade-offs (wins vs losses)

### Wins
1. **Multi-dimensional evaluation** (DB + actions + communicate + NL assertions) is more rigorous than single-pass/fail metrics. Catches agents that "say the right thing but do the wrong thing."
2. **Dual-control framework** (both agent and user can call tools) mirrors real customer service where users also navigate UI tools.
3. **Task quality rigor**: 75+ task fixes based on SABER analysis (Cuadron et al., 2025). Tasks are painstakingly validated for correctness, feasibility, and clarity.
4. **Two modes**: Half-duplex (cheap, fast, text) and full-duplex (realistic voice) on the same task set.
5. **Modular domain design**: Easy to add new domains -- just define policy, tools, tasks, and register.
6. **Cost transparency**: All benchmark results include per-task costs, enabling cost-vs-quality analysis.
7. **Voice providers**: 6 realtime providers supported (OpenAI, Gemini, xAI, Nova, Qwen, LiveKit) with pluggable adapter architecture.

### Losses
1. **LLM-based user simulator is expensive and imperfect**: Runs a separate LLM call per turn. Can hallucinate (requires hallucination detection + retry loop). The user simulation cost is significant.
2. **Evaluation is costly**: Environment evaluator must replay all mutating tool calls. NL assertion evaluator requires an LLM call.
3. **Telecom domain is very hard** (34-49%): Current models perform poorly. Tasks may have hidden complexity or ambiguous policy interactions.
4. **Binary reward per action**: Action evaluation is all-or-nothing per expected action. An agent that does 9/10 actions correctly gets 0.0 reward for that dimension.
5. **Dependency-heavy**: 50+ dependencies including LiteLLM, FastAPI, multiple voice SDKs, etc. Installation is non-trivial (especially voice extras with portaudio/ffmpeg).
6. **Python 3.12-3.13 only**: Relatively new Python requirement.
7. **Redis dependency for caching**: Requires Redis for LLM call caching (optional but default config points at localhost).
8. **Cost of full benchmark run**: At ~$0.10/task * 114 tasks * 4 trials = ~$45/domain + user model costs, a full evaluation across all domains costs ~$200+. Adding voice raises this significantly.

## 5. Design Rationale (why this approach)

1. **Why dual-control?** Real customer service conversations involve two parties both accessing systems (agent CRM tools, user self-service portals). Prior benchmarks only give tools to one side. τ-bench's key insight is that evaluating both parties' tool usage gives a more complete picture.

2. **Why product-of-rewards?** The task reward_basis defines which dimensions gate the pass. By taking the product, a zero in any dimension zeros the total -- no partial credit for critical failures. This incentivizes agents that do everything right, not "mostly right."

3. **Why LLM-based user simulator?** Scripted user simulators can't adapt to unexpected agent behavior. An LLM user can handle open-ended conversations, ask follow-ups, express frustration, etc. -- more realistic. The trade-off is cost and hallucination risk, managed by the hallucination detection/retry system.

4. **Why environment replay for DB evaluation?** Instead of comparing agent's DB at runtime (which could include artifacts of the agent's actual errors), τ-bench re-executes all mutating tool calls from the trajectory on a fresh environment and compares the final state. This ensures DB evaluation is deterministic regardless of execution order or non-mutating calls.

5. **Why tick-based voice simulation?** Real-time audio APIs are streaming and bidirectional -- turn-based abstraction doesn't apply. Ticks (fixed 200ms time slices) provide a discrete simulation of continuous time, enabling deterministic evaluation of full-duplex conversations.

6. **Why 75+ task fixes from SABER?** Prior version of the benchmark had incorrect expected actions, impossible constraints, ambiguous instructions, and missing fallback behaviors. Fixing these systematically was necessary for the benchmark to produce meaningful results. The SABER paper's analysis was directly applied.

7. **Why multiple task splits?** The `base` split matches the original τ-bench structure for backward compatibility. `default`, `workflow`, etc. are ablations for studying specific phenomena (oracle plans, no-user mode, workflow policies).

## 6. Transfer to Lyra (one idea + route + impact/effort/tier)

### Transferable Idea: Four-Dimensional Evaluation Harness with Environment Replay

τ-bench's evaluation approach directly addresses Lyra's need to verify agent correctness beyond simple task completion. Lyra's agents operate in complex environments (tools, knowledge bases, user interactions) and need holistic verification.

**Specific mechanism to adopt**: A modular "evaluator pipeline" that checks:
1. **Action trace**: Did the agent call the right tools with right args? (Binary per-expected-action, product reward)
2. **State transition**: After replaying actions, does the world state match expected? (Environment replay + DB hash comparison)
3. **Communication**: Did the agent convey required information to the user? (Message content scanning)
4. **NL assertions**: LLM-judged qualitative checks on conversation quality (experimental)

**How it maps**: Instead of a monolithic "task pass/fail," Lyra should decompose evaluation into these orthogonal dimensions. The product-of-rewards formulation ensures no category is neglected. The environment replay mechanism is especially valuable for Lyra's tool-use evaluation -- deterministic state comparison regardless of execution path.

### Route

**§4.x Route: §4.3 (Agent Architecture / Evaluation & Testing)**

τ-bench is fundamentally an agent evaluation framework. The multi-dimensional evaluation harness maps naturally to Lyra's §4.3 focus on building reliable agent architectures with robust evaluation.

### Rating

- **Impact: 8/10** -- This is the single most transferable evaluation pattern from any benchmark I have reviewed. It directly solves Lyra's problem of "how do we know if an agent truly solved a task, beyond just checking the final output?" The environment-replay approach catches failure modes that simple end-state checks miss.
- **Effort: 5/10** -- Implementing the evaluator pipeline itself is moderate (a few hundred lines of evaluation logic). The hard part is specifying the expected actions and assertions for each task -- this requires domain expertise and rigorous manual validation (as τ-bench's 75+ bug fixes demonstrate). Lyra would need a task authoring workflow alongside the evaluator.
- **Tier: Tier 2 (Strategic Adoption)** -- Core architectural pattern that should be integrated into Lyra's evaluation subsystem, not a quick cherry-pick. Requires planning and investment but pays compounding returns as the task library grows.

### LICENSE

MIT License. Copyright (c) 2025 Sierra Research. No restrictions on use, modification, or redistribution. Full compatibility with Lyra's licensing.
