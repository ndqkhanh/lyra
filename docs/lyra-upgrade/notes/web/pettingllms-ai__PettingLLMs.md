# PettingLLMs (pettingllms-ai/PettingLLMs) -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**PettingLLMs is an open-source RL framework for training collaborative and self-organizing LLM agents.** It powers two major research thrusts:

- **Metaagent-X (arXiv 2605.14212):** End-to-end trainable automatic multi-agent systems. A meta-designer (LLM) generates executable MAS orchestration code (Workflow with nodes/edges), which is then executed by a downstream executor. Both the designer and executor policies are jointly optimized via on-policy RL, closing the gap from earlier "partially adaptive" approaches where the executor was frozen. The designer emits raw Python code (via `gen_agent.py` `MASGenerator`/`MASExecutor`), which is patched at runtime with absolute imports, werkzeug AIClient setup, and DataProto serialization, then executed in a Ray Docker sandbox.

- **Stronger-MAS / AT-GRPO (arXiv 2510.11062):** Agent- and Turn-wise Group Relative Policy Optimization for fixed-topology multi-agent systems. Extends GRPO with per-agent/per-turn credit assignment, multi-level rewards (process + agent + global/team), and per-role specialization via LoRA adapters or independent models.

**Core RL loop** (in `train.py` -> `MultiAgentsPPOTrainer.fit()`):
1. Wake up vLLM serving engines
2. Generate multi-agent rollouts via `generate_multiple_rollouts_concurrent()` (tree or single mode)
3. Sleep vLLM engines
4. Assign consistent UIDs for GRPO grouping
5. Compute old_log_probs, reference log_probs, advantages (GRPO)
6. Per-agent/per-policy parameter updates with optional splits (LR alternating, IBR phase alternation)
7. Periodically validate on benchmarks
8. Save best checkpoints

**Three workflow types** (selected by `workflow_type` in config):
- `turn` -- sequential turn-based agents (standard MAS)
- `graph` -- graph-based MAS (AutoGen/AG2/LangGraph integration)
- `autoevol` -- Metaagent-X style: designer writes code, executor runs it

**Three specialization levels** (selected by `specialization` in config):
- `prompt` -- shared policy + role-specific prompts (L1)
- `lora` -- shared base model + per-agent LoRA adapters (L2)
- `full` -- independent per-agent models (L3)

**Reward System** (`core_algo.py`):
- `default`, `hop_weighted`, `hop_discount`, `turn_weighted`, `discount`, `binary`, `normalized`, `shaped`
- For Metaagent-X: correctness_reward + delivery_reward (format tags) + solution_reward (boxed/syntax)
- Math: uses `math_verify` (parse + verify) with fallback string/numeric matching
- Code: extracts code blocks, runs against ground-truth test cases via subprocess, pass ratio as reward

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Top-level structure:**
```
pettingllms/
  train.py             # Hydra-based entry point; injects config, launches trainers
  trainer/
    core_algo.py       # Reward calculation algorithms
    train.py           # main() / run_ppo() entry
    multi_agents_ppo_trainer.py  # Orchestrator: PPO trainers, rollouts, validation
    multi_agents_execution_engine.py  # Turn-based rollouts (single/batched)
    multi_agents_execution_engine_autoevol.py  # Metaagent-X rollouts
    multi_agents_execution_engine_graph.py     # Graph-based rollouts
    multiagentssys_register.py   # Class registry (envs, agents, workers)
    async_generate.py  # async vLLM calls
  multi_agent_env/
    base/agent.py, env.py  # Abstract base classes
    math/, code/, search/, stateful/, stateful_vision/, pychecker_rl/, mixed/
    autoevol/          # Metaagent-X: gen_agent.py (MASGenerator, MASExecutor), reward_function.py
  config/
    math/, code/, search/, stateful/, ppo_trainer/, autoevol/, mas_graph/
  mas_graph/           # AutoGen/AG2/LangGraph integration
  utils/
  verl/                # VERL integration layer (wraps RayPPOTrainer)
```

**Data flow (default turn-based training):**
```
Hydra config --> train.py::main()
  --> MultiAgentsPPOTrainer.__init__()
    --> init_workers() (spawns Ray workers: vLLM + FSDP shards)
    --> init_multi_agent_sys_execution_engine()
    --> fit():
      for step in total_training_steps:
        rollout_engine.wake_up()
        generate_multiple_rollouts_concurrent():
          for each env:
            for each turn:
              for each agent (async parallel or sequential):
                llm_async_generate() --> DataProto
                agent.step(env, env_worker)  # Ray Docker sandbox
                calculate_reward()
        rollout_engine.sleep()
        assign_consistent_uids()
        compute_old_log_prob()  # FSDP workers
        compute_advantage()     # GRPO
        update_actor()           # FSDP workers (per-agent LR)
        validate()              # every val_freq steps
```

**Architecture pattern:** Hybrid distributed RL training (FSDP2 for training, vLLM for inference) orchestrated via Ray. Uses a "wake/sleep" pattern to manage vLLM engines (free GPU memory between rollouts and training). Configs use Hydra/OmegaConf. Multi-agent coordination is async with asyncio.

## 3. Performance/Benchmarks (real numbers from the repo)

- **Metaagent-X** achieves **up to +21.7% improvement** over single-agent and automatic-MAS baselines across **six math and code benchmarks** and **two base models**
- Ablations show both designer and executor improve throughout training
- Effective co-evolution follows a stagewise process with decoupled optimization benefits
- Specific benchmarks used: AIME24, AIME25, OlympiadBench (math); APPS, CodeContests, LiveCodeBench (code)
- Supports up to 8 GPUs per node, multiple nodes (`nnodes` config)
- Uses pytorch FSDP2 for model sharding, vLLM for inference
- LoDA rank configurable (default 16), multi-turn max_turns=4-8 typical
- Training batch sizes: 32 environments x 8 samples = 256 trajectories typical

## 4. Trade-offs (wins vs loses -- from issues, design decisions, complexity)

**Wins:**
- End-to-end RL for automatic MAS where both designer AND executor improve (not just designer)
- Fine-grained credit assignment via AT-GRPO (per-turn, per-agent) avoids the "credit assignment problem" of shared-reward MAS
- Three specialization levels (prompt/LoRA/full) provide cost-efficiency continuum
- Flexible reward shaping with 8 built-in algorithms
- Supports both turn-based and graph-based MAS topologies
- Integrates with AutoGen, AG2, LangGraph, LlamaIndex for real-world agent ecosystems
- Multimodal support (Qwen2.5VL)

**Loses / Complexity:**
- **Extreme resource requirements:** 8 GPUs per node minimum, Ray cluster setup, vLLM serving, Docker sandboxes. Not suitable for single-GPU or consumer hardware.
- **Code-generation-based MAS is fragile:** Metaagent-X generates raw Python that must be patched/executed in sandbox. Runtime errors, import errors, syntax errors, and timeouts are common failure modes (see `gen_agent.py` fallback strategies).
- **Complex configuration surface:** Hydra configs are deeply nested (OmegaConf inheritance, overrides, dynamic resolution). Hard to debug misconfiguration.
- **Tight coupling to VERL:** Vendor lock-in to VERL (DataProto, RayPPOTrainer, ResourcePoolManager). Cannot easily swap to another RL backend.
- **Retry logic on vLLM crashes but no graceful degradation:** `MAX_ROLLOUT_RETRIES` (default 3) with 10s sleep between retries. All retries failing raises fatally.
- **Memory management is manual:** Explicit `del`, `gc.collect()`, `torch.cuda.empty_cache()` calls throughout the codebase indicate OOM is a recurring challenge.
- **Wake/sleep engine management:** Strict pairing required; desync causes corruption. Comment in code: "Do NOT call reset_prefix_cache separately -- it corrupts vLLM state."
- **No unit tests visible in the source tree** -- testing appears to be done via end-to-end training runs only.
- **Distributed debugging difficulty:** Extensive `[DEBUG HANG]` print statements and try/except logging suggest hangs and deadlocks during distributed training.
- **Tree design mode (M*N rollouts)** multiplies compute quadratically (e.g., 4 designs x 8 executions = 32 rollouts per problem).

## 5. Design Rationale (why this approach)

1. **Why end-to-end RL instead of prompt-level coupling?** Prior work only coupled designer and executor at inference time through prompts. The key insight: the executor is a "hard ceiling" on the meta-designer. Joint optimization of both via RL gradients removes this ceiling and allows emergent specialization.

2. **Why AT-GRPO instead of standard GRPO?** Standard GRPO groups all responses into one group per problem. In a multi-agent setting with multiple turns, this loses fine-grained signal. AT-GRPO creates groups at per-turn/per-agent granularity, enabling role-specific advantage computation.

3. **Why code-generation for the designer?** The designer emits executable Python (Workflow framework) rather than JSON/structured configs. This allows arbitrary MAS topologies (branching, conditional routing, tool calls) that a fixed schema cannot express. The trade-off is fragility.

4. **Why VERL as the RL backend?** VERL (Volcengine) provides battle-tested implementations of PPO/GRPO with FSDP2 and vLLM integration. Building from scratch would be prohibitive. PettingLLMs layers multi-agent coordination on top.

5. **Why Hydra for configs?** Deeply nested configs with inheritance enable complex multi-model, multi-agent setup. Each agent can have its own model, LoRA config, sampling parameters, and reward settings.

6. **Why Ray Docker workers for task execution?** Running untrusted LLM-generated code (Metaagent-X) requires sandboxing. Ray provides distributed task scheduling across GPU nodes.

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier + LICENSE)

**Transferable idea: AT-GRPO for multi-module code generation.** Lyra's agent system generates multiple modules that must work together (e.g., planner -> executor -> verifier). Currently, feedback is sparse (pass/fail on end-to-end tests). AT-GRPO-style per-module credit assignment could provide finer-grained training signal: reward the planner when its plan led to a correct implementation, even if the executor made errors, and vice versa.

**Specific mechanism:** Wrap each Lyra agent's response in a DataProto-like structure with `agent_name`, `turn_idx`, `env_idx`. Collect trajectories over N sampled paths. Compute rewards per-agent/per-turn using correctness pass/fail as the env_final_reward, then apply GRPO advantage normalization within each agent-turn group. This is exactly what `_assign_consistent_uids()` and `core_algo.py` implement.

**Workstream route: 4.2 Training & Optimization.** The AT-GRPO algorithm implementation (200 lines in `core_algo.py`) is self-contained and can be extracted without the VERL/Ray infrastructure. Lyra already has environments (test suites, evaluation harness) that provide binary success/failure signals.

- Impact: 7 (high -- gives Lyra agents a structured RL training signal)
- Effort: 5 (moderate -- requires implementing the grouping, advantage computation, and reward shaping)
- Tier: **Gold** (demonstrates a novel training paradigm for modular agent systems)
- LICENSE: MIT (fully permissive, no restrictions on use)

**Repository:** `pettingllms-ai/PettingLLMs`
**License:** MIT
**Language:** Python
**Architecture Pattern:** Hybrid distributed multi-agent RL (Ray + FSDP2 + vLLM + Hydra)
