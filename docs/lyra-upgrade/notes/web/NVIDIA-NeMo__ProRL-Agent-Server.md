# NVIDIA-NeMo/ProRL-Agent-Server ("Polar") -- Deep-Read

## 1. Headline Feature & Mechanism

**Rollout-as-a-Service for RL training of multi-turn LLM agents.** Polar treats any agent harness as an RL environment by inserting a transparent inference proxy between the agent and the LLM serving backend. Every API call the agent makes (regardless of API format -- Anthropic Messages, OpenAI Chat/Responses, Google Gemini) is intercepted, forwarded to a single inference server (SGLang or vLLM), and the response is captured with **per-token logprobs + token IDs** -- the raw signals needed for policy-gradient RL (GRPO, PPO). The proxy converts API formats bidirectionally so agents see their native API while one backend serves all. Results are assembled into training-ready trajectories (token streams with loss masks) and delivered to an RL trainer via HTTP callback or polling.

The mechanism is implemented as a three-tier distributed system:
- **Rollout Server** (port 8080): Central orchestrator that accepts tasks, schedules them across gateway nodes via a stage-aware load balancer, and collects results.
- **Gateway Nodes** (port 8100+): Per-machine workers that manage the full session lifecycle (INIT -> READY -> RUN -> POSTRUN), each with isolated worker pools per stage.
- **Inference Server** (external): SGLang or vLLM serving the actual model.

## 2. Architecture & Core Modules

**Entry point:** `polar.cli:main` (registered in pyproject.toml as `polar` script). Five subcommands: `serve_rollout`, `serve_gateway`, `dashboard`, `submit`, `status`.

**Core modules (14k+ lines Python, TypeScript frontend):**

| Module | File(s) | Role |
|--------|---------|------|
| `rollout/server.py` | 242 lines | FastAPI app: task submission, node registration, health, event SSE, session callbacks |
| `rollout/manager.py` | 335 lines | Task lifecycle management, background execution, session state tracking, callback delivery |
| `rollout/pipeline.py` | 464 lines | Dispatch+collect: acquires gateway nodes, dispatches sessions, interleaves callback-wait with polling for safety |
| `rollout/balancer.py` | 248 lines | Stage-aware scheduler: multi-dimensional scoring (run pressure, postrun pressure, init pressure, ready gap, total pressure) |
| `gateway/server.py` | 840 lines | Gateway FastAPI app: session CRUD, inference proxy (`/{path:path}` catch-all), streaming, SSL fan-out |
| `gateway/node.py` | 973 lines | Session lifecycle executor: INIT (runtime start + prepare), RUN (harness steps), POSTRUN (trajectory build + eval + teardown) |
| `gateway/engine.py` | 149 lines | Inference backend strategies: SGLang (canonical, requires patch) and vLLM (`return_token_ids` flag) |
| `gateway/proxy.py` | 207 lines | HTTP client to inference server with pause/resume generation for online weight updates |
| `gateway/dispatcher.py` | 355 lines | Stage-isolated asyncio worker pools (INIT/READY/RUN/POSTRUN) |
| `gateway/transform/` | ~500 lines | API adapter layer: Anthropic Messages, OpenAI Chat, OpenAI Responses, Google Gemini -> OpenAI Chat Completions |
| `trajectory/builder/prefix_merging.py` | 364 lines | Multi-turn token stream reconstruction via token-prefix matching, EOT-aware interstitial splitting |
| `trajectory/evaluator/swebench_harness.py` | 165 lines | SWE-Bench/SWE-Gym harness-based grading via patch extraction and test execution |
| `agent/presets/` | 10 harnesses | Claude Code, Codex, Gemini CLI, Hermes, OpenClaw, OpenHands SDK, OpenCode, Pi, Qwen Code, Shell |
| `runtime/docker.py` | 234 lines | Docker container lifecycle with bind mounts, GPU passthrough, chmod reconciliation |
| `platform/server.py` | 198 lines | Dashboard observability service with React/TypeScript frontend |
| `slime_bridge/adapter.py` | 323 lines | Converts Polar rollout results into Slime training samples |

**Data flow:** Client submits task -> RolloutServer schedules sessions across GatewayNodes -> GatewayNode starts Docker/Apptainer runtime -> AgentPreparer installs config -> AgentHarness runs agent steps via ExecInput -> each LLM call hits GatewayNode proxy -> proxy forwards to SGLang/vLLM, captures token IDs + logprobs -> proxy returns native-API response to agent -> agent completes -> GatewayNode builds Trajectory (prefix-merging or per-request) -> Evaluator scores it -> result POSTed back to RolloutServer -> SlimeBridge converts to training samples -> callback delivers to trainer.

**Design pattern:** Plugin architecture with registry pattern (harness factory, engine strategy, builder registry, evaluator registry). Pydantic models with strict validation (`extra="forbid"`). Immutable dataclasses and frozen Pydantic models throughout. Stage-isolated worker pools with asyncio queues and semaphores.

## 3. Performance/Benchmarks

No formal benchmarks in the repo itself, but the testing infrastructure reveals:
- **Trajectory equivalence proven** between SGLang and vLLM backends: `tests/trajectory/test_engine_trajectory_equivalence.py` proves both backends produce byte-identical Trace objects (prompt_ids, response_ids, loss_mask, logprobs, messages) from the same generation.
- **Training curves** included in `assets/swegym_grpo_training_curves.png` showing GRPO training on SWE-Gym.
- **Worker scaling:** topology examples show 8-16 init/run/postrun workers per gateway node.
- **Architecture optimized for** reducing GPU idle time via "Rollout Staging & Runtime Pooling" -- the README claims "Save GPU hours."
- Two tech reports: arXiv:2605.24220 (Polar) and arXiv:2603.18815 (ProRL Agent).

## 4. Trade-offs

**Wins:**
- **Harness-agnostic**: Any agent framework plugs in (Claude Code, Codex, OpenHands, shell, etc.) via the `BaseHarness` interface. No code changes to the harness.
- **Trainer-agnostic**: Works with any RL trainer via HTTP callback. Currently bridged to Slime; architecture supports NeMo-RL, VERL, etc.
- **Token-level fidelity**: Real sampled logprobs captured at inference time, never decoded/re-encoded, so BPE drift cannot corrupt training data.
- **Online RL support**: Pause/resume generation mechanism drains inflight requests, swaps weights, then resumes -- enabling live policy updates.
- **Multi-API support**: Agents speaking Anthropic Messages, OpenAI Chat/Responses, or Google Gemini all work through one inference backend via the transform layer.
- **Isolation**: Docker/Apptainer per-session runtime with GPU, network, CPU, memory controls.
- **Grounded prefix-merging**: Reconstructs multi-turn trajectories using pure token-prefix matching against server-tokenized prompts, avoiding BPE re-tokenization errors.

**Loses:**
- **SGLang dependency**: Requires a patched SGLang version (`scripts/patch/patch_sglang.sh`) for token-ID emission. Upstream support not yet merged.
- **Complexity**: Three-service distributed system (rollout server, gateway, inference) with heartbeat polling, registration, and callback paths. Significant operational overhead.
- **Infrastructure heavy**: Requires Docker, GPU servers, inference servers. Not suitable for lightweight setups.
- **vLLM normalization code**: vLLM's response shape differs from SGLang's canonical shape, requiring a non-trivial `normalize_response` method in `VLLMEngine` that renames fields and stamps token IDs onto logprobs.
- **Only Slime bridge implemented**: Despite "trainer-agnostic" design, only the Slime integration is complete. NeMo-RL and VERL bridges are on the roadmap.
- **Pre-1.0 maturity**: Version 0.1.0, no CHANGELOG, no issue tracker in the repo. README acknowledges "We'll remove this once upstream support goes through" for the SGLang patch.
- **In-memory state**: Session storage is in-memory (thread-safe dicts), though optional disk persistence via CompletionWriter exists.
- **vLLM reasoning field name mismatch**: vLLM names the reasoning field `reasoning` while Polar's canonical field is `reasoning_content`, requiring a rename in both directions.

## 5. Design Rationale

The architecture is driven by one constraint: **RL training requires token-level logprobs from the exact model that generated the tokens.** This means:
1. The inference call cannot go through a third-party API (Anthropic, OpenAI) that doesn't expose per-token logprobs. Hence the proxy + local inference server pattern.
2. Each agent turn is a separate completion request, but the trainer needs a single token stream per environment episode. Hence the prefix-merging trajectory builder, which re-stitches multi-turn interactions using token-prefix matching.
3. Weight updates during training must be reflected in subsequent rollouts without restarting the system. Hence the pause/resume generation mechanism.
4. The system must be trainer-agnostic because RL training frameworks are fragmented and rapidly evolving. Hence the HTTP callback boundary and the Slime bridge as the first concrete integration.

The use of Pydantic strict models (`extra="forbid"`) throughout reflects a "fail loudly on misconfiguration" philosophy -- important for a distributed system where topology YAML errors could silently waste GPU hours.

## 6. Transfer to Lyra

**One idea:** Adopt Polar's **inference proxy pattern** for Lyra's agent evaluation harness. Insert a transparent proxy between any Lyra agent (Codex, Claude Code, etc.) and its LLM backend that captures token IDs, per-token logprobs, and full request/response pairs. Store these as structured `CompletionSession` records, then build trajectory reconstruction (multi-turn merging with loss masks) on top. This would give Lyra the foundation for:
- Collecting training data from agent runs
- Computing reward signals from existing evaluators
- Feeding structured trajectories into any RL training framework

**Route:** This maps to `workstream §4.3 (Verification & Auditing)` and `§4.5 (Agent Infrastructure)`. The proxy pattern is infrastructure-level, while the trajectory collection feeds directly into the verification feedback loop.

**Impact:** 7/10 -- Foundational capability for RL training from Lyra rollouts, but requires significant infrastructure investment.

**Effort:** 8/10 -- Full implementation requires: inference proxy, completion storage, API transform layer (for multi-backend support), trajectory builders, evaluator integration, and training bridge. Many optional pieces (dashboard, multi-node scheduling).

**Tier:** A (Strategic) -- RL training from rollouts is a long-term competitive advantage for Lyra, enabling continuous policy improvement from real agent execution data. The design pattern is clean and well-validated by this repo.

**LICENSE:** Apache 2.0 -- fully permissive for incorporation, modification, and distribution. No copyleft restrictions.
