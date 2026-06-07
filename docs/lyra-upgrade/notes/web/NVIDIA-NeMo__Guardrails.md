# NVIDIA-NeMo/Guardrails -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline:** NeMo Guardrails is an open-source toolkit for adding programmable guardrails to LLM-based conversational applications. It intercepts user input and LLM output, running configurable "rails" (safety, topical, jailbreak, fact-checking, hallucination, etc.) via a custom domain-specific language called **Colang**.

**How it works (actual code path):**

The primary entry point is `Guardrails` (a facade in `nemoguardrails/guardrails/guardrails.py`), which wraps either `LLMRails` (`nemoguardrails/rails/llm/llmrails.py`) or `IORails` (`nemoguardrails/guardrails/iorails.py`). The facade auto-selects the engine:

- **LLMRails** (default, full Colang runtime): An event-driven engine that loads Colang `.co` flow definitions, converts incoming chat messages into an internal event stream (`UtteranceUserActionFinished` -> `UserMessage` -> ...), runs the events through the Colang runtime, which triggers rails and actions. The runtime dispatches LLM calls through a framework-agnostic `LLMModel` Protocol (OpenAI, LangChain, NIM, etc.). Events are processed in a loop -- `Runtime.generate_events` keeps processing until a `listen` event is produced.

- **IORails** (optimized path, v0.21+): A lightweight engine for a restricted subset of rails (content safety, topic safety, jailbreak detection only). It bypasses the Colang runtime entirely and uses `RailsManager` + `EngineRegistry` for a direct pipeline: `input rails -> LLM call -> output rails`. Supports **speculative generation** (rails and LLM call run concurrently; if rails block, the LLM result is discarded). Uses an `AsyncWorkQueue` with configurable concurrency (`NONSTREAM_MAX_CONCURRENCY=256`, `NONSTREAM_QUEUE_DEPTH=256`) for non-streaming requests and an `asyncio.Semaphore(STREAM_MAX_CONCURRENCY=256)` for streaming. OTEL tracing/metrics are integrated.

**Colang Language:** A Python-like DSL for defining dialog flows. Supports two versions:
- **Colang 1.0**: Mature, default. Three constructs: `define user X` (user intent patterns), `define bot X` (bot responses), `define flow` (conversation flow with user/bot turns).
- **Colang 2.0**: Enhanced with states, actions, active decorators, richer flow control.

**Five rail types:** Input (user message), Dialog (LLM prompting behavior), Retrieval (RAG chunk filtering), Execution (tool I/O), Output (LLM response).

## 2. Architecture & Core Modules

```
nemoguardrails/
  __init__.py          -- Top-level API: exports LLMRails, RailsConfig, Guardrails, types
  __main__.py          -- CLI entry point -> nemoguardrails.cli.app
  base_guardrails.py   -- ABC: generate(), generate_async(), stream_async()
  types.py             -- Core types: ChatMessage, LLMModel (Protocol), LLMResponse, LLMFramework
  rails/
    __init__.py         -- Exports RailsConfig, LLMRails
    llm/
      config.py         -- RailsConfig: Pydantic model for YAML config (models, rails, flows, KB)
      llmrails.py       -- LLMRails: Full-featured engine, ~2100 lines. init_llms, generate_async,
                           stream_async, _run_output_rails_in_streaming, generate_events, etc.
      options.py        -- GenerationOptions, RailsResult, RailType enums
      buffer.py         -- BufferStrategy for streaming output rails
  guardrails/
    guardrails.py       -- Guardrails facade (auto-selects IORails vs LLMRails)
    iorails.py          -- IORails: Optimized engine, spec gen, OTEL, work queues
    rails_manager.py    -- Runs input/output rail flows against EngineRegistry
    engine_registry.py  -- Manages LLM engines (main, content_safety, topic_safety, jailbreak)
    model_engine.py     -- LLM call abstraction (OpenAI-compatible, streaming)
    api_engine.py       -- HTTP API engine for external model endpoints
    guardrails_types.py -- Internal types: LLMMessage, RailDirection
    telemetry.py        -- OTEL metrics, tracing, content capture
    async_work_queue.py -- AsyncWorkQueue: admission queue + worker pool for non-streaming
  colang/
    runtime.py           -- Abstract Base Runtime class
    v1_0/runtime/        -- Colang 1.0 runtime (full event loop, flow execution)
    v2_x/runtime/        -- Colang 2.0 runtime
  library/               -- Built-in guardrails (30+): content_safety, jailbreak_detection,
                            factchecking, hallucination, sensitive_data_detection, topic_safety,
                            regex, llama_guard, activefence, policyai, etc.
  cli/                   -- CLI: chat, server, convert, find_providers, actions-server
  server/                -- FastAPI server with OpenAI-compatible /v1/chat/completions
  actions/               -- Action dispatcher, LLM generation actions, core/math actions
  llm/                   -- LLM abstraction: providers, task manager, prompts, cache, filters
  embeddings/            -- Embedding providers: Basic (FastEmbed), cache, index
  kb/                    -- Knowledge base (RAG document store)
  tracing/               -- OTEL tracing: span format, interaction types, span extractors
  eval/                  -- Evaluation CLI for topical, moderation, fact-checking, hallucination
```

**Data Flow (LLMRails):**
```
User messages -> LLMRails.generate_async()
  -> convert to events (UtteranceUserActionFinished, etc.)
  -> Runtime.generate_events(events)
    -> Input rails (jailbreak, content safety, topic safety)
    -> Dialog flow (canonical form -> next step generation -> action execution -> bot message)
    -> Output rails (fact-checking, hallucination, moderation)
  -> Extract bot response from events
  -> Return GenerationResponse or dict
```

**Data Flow (IORails):**
```
User messages -> IORails.generate_async()
  -> AsyncWorkQueue.submit()
    -> [SPECULATIVE] Input rails || LLM call concurrently
    -> [SEQUENTIAL] Input rails -> LLM call -> Output rails
  -> Return LLMMessage (dict with role/content)
```

**Config structure:**
```
config/
  config.yml   -- Models, rails, flows, KB config (Pydantic-validated)
  config.py    -- Custom initialization code
  actions.py   -- Custom Python actions
  *.co         -- Colang flow definitions
```

## 3. Performance/Benchmarks

The repo provides a comprehensive benchmarking suite in `benchmark/`:

- **AIPerf load testing**: Sweeps concurrency from 1 to 256 in powers-of-2, measuring throughput and latency. Uses mock LLMs (configurable latency: sampled from normal distribution with mean/std, clamped to [min,max]). No GPUs required.
- **Mock LLM parameters**: `LATENCY_MIN_SECONDS`, `LATENCY_MAX_SECONDS`, `LATENCY_MEAN_SECONDS`, `LATENCY_STD_SECONDS` -- configurable per endpoint (app_llm, content_safety_llm).
- **Concurrency budgets**: IORails non-streaming: queue depth=256, max workers=256. Streaming: semaphore=256. Multiple uvicorn workers (4 default).
- **Locust stress-test** also included in benchmark suite.
- Key benchmarking insight: Guardrails adds measurable latency proportional to the number and complexity of rail checks. The IORails engine and speculative generation are specifically designed to reduce this overhead by running rails in parallel with or before/after the main LLM call.
- The repo states the IORails engine was "introduced for low-latency input/output rail serving" -- optimized for production deployments that only need content safety / topic safety / jailbreak detection.

## 4. Trade-offs (wins vs losses)

**Wins:**
- **Comprehensive rail library**: 30+ built-in guardrails spanning jailbreak detection, content safety, fact-checking, hallucination, PII masking, topic control, etc. Plus third-party integrations (ActiveFence, PolicyAI, Cleanlab, etc.).
- **Colang DSL**: Unique among guardrails toolkits. Enables precise dialog flow control beyond simple input/output filtering. Allows context-dependent rail activation.
- **Dual-engine architecture**: LLMRails for full flexibility (Colang flows, RAG, tool calling), IORails for low-latency production serving. Auto-selection via the `Guardrails` facade.
- **Speculative generation**: IORails races input rails against LLM generation, saving one sequential round-trip when rails pass (typical case). Nice latency optimization for safety checks.
- **Framework-agnostic LLM protocol**: `LLMModel` Protocol with OpenAI-compatible default, LangChain adapter, NIM support. No hard dependency on LangChain as of v0.22.
- **Async-first**: Core pipeline is fully async, with sync wrappers using `asyncio.run` / `nest_asyncio`.
- **Observability**: OpenTelemetry tracing and metrics built into IORails. Configurable log options (activated_rails, llm_calls, internal_events).
- **Active development**: v0.23.dev0, frequent releases, detailed changelog, growing community.
- **Published EMNLP 2023 paper** with evaluation methodology.

**Losses (from changelog, issues, code):**
- **Complexity**: Two Colang versions (1.0 and 2.0), two engine implementations (LLMRails and IORails), plus the `Guardrails` facade. Significant API surface and learning curve. Breaking changes between versions (e.g., LangChain decoupling in 0.22, LLMModel Protocol switch in 0.22).
- **IORails limitations**: Only supports a small subset of rails (content safety input/output, topic safety input, jailbreak detection). No dialog rails, no RAG, no custom actions. Falls back to LLMRails for anything outside this set.
- **Streaming + output rails tension**: Streaming with output rails requires buffering (cans chunks, run rails, then yield). The `stream_first` vs `stream_last` config controls latency vs. safety tradeoff. Output rails must be explicitly enabled for streaming or it raises `StreamingNotSupportedError`.
- **LangChain dependency weight**: Even though decoupled in 0.22, legacy LangChain support still exists. The `_compat/langchain_kwargs.py` compat layer suggests ongoing migration burden.
- **Colang 2.0 immaturity**: Several features not supported in 2.0 that exist in 1.0: log options, `llm_output`, `output_vars`, assistant messages as input. Internal events and activated rails logging also not yet supported. Breaking change in 0.22 rejected public Colang 2.0 runtime state.
- **Caching**: In-memory LFU cache support for models, but cache stats logging and config are relatively recent (0.18+) and likely still maturing.
- **Telemetry**: Anonymous telemetry is opt-out (set `DO_NOT_TRACK=1`). This may be a concern for some deployments.
- **Dependency management**: Complex optional dependency groups (server, eval, sdd, jailbreak, tracing, etc.) with version constraints. FastEmbed/ONNX runtime version pinning for Python 3.10. Protobuf pinned for CVE.
- **Breaking changes in recent releases**: v0.22 had multiple breaking changes (LangChain decoupling, LLMModel Protocol, IORails refactor, streaming usage removal). Migration cost is real.

## 5. Design Rationale

The architecture reflects a clear philosophy: **guardrails are programmable, modular, and should not force a specific LLM stack.**

Key design decisions and their rationale:

1. **Colang DSL over code-only**: Rather than hard-coding rail logic in Python, Colang provides a declarative way to define dialog flows. This separates policy from implementation, enables non-developers to author guardrails, and allows dynamic flow activation based on conversation state. The two-version strategy (1.0 stable, 2.0 evolving) manages risk while pushing toward a more expressive future.

2. **Event-driven internals**: The LLMRails engine converts messages to internal events, then processes them through the Colang runtime. This design enables complex multi-turn flows, conditional branching, and integration with arbitrary external events (not just chat messages). The trade-off is complexity and latency for simple use cases -- hence IORails.

3. **IORails as a performance escape hatch**: Recognizing that many production deployments only need basic input/output safety, the IORails engine strips away the Colang runtime entirely. This is a textbook "optimize for the common case" pattern. The auto-fallback in the `Guardrails` facade means users can write one config and get the right engine.

4. **LLM Protocol over LLM Framework**: The shift from LangChain-dependent to `LLMModel` Protocol (v0.22) shows a deliberate move toward framework independence. The Protocol uses duck typing (`Protocol`, `runtime_checkable`), so any object conforming to the interface works. This is the right call for a middleware library.

5. **Async-first with sync bridge**: The core pipeline is fully async (asyncio native). Sync wrappers use `asyncio.run()` for fresh event loops or `nest_asyncio` for nested loops. This is pragmatic: async enables high concurrency, but the sync bridge ensures compatibility with sync codebases.

6. **Speculative generation**: Racing input rails against LLM generation is an elegant optimization. It assumes rails typically pass, so the latency penalty for the common case is zero (rails run in the shadow of the LLM call). When rails do block, the LLM work is wasted -- but this is acceptable because safety violations are rare.

7. **Pluggable everything**: Embedding providers, search providers, LLM frameworks, actions, filters, output parsers -- all extensible. The registry pattern (`register_provider`, `register_framework`, etc.) is used consistently.

## 6. Transfer to Lyra

**Transferable idea: Speculative Guardrail Execution**
The IORails speculative generation pattern (`_do_generate_speculative` in `iorails.py`) races safety/sanity checks against the primary LLM call. For Lyra, this same pattern can be applied to any validation or constraint check: before committing an agent's output, run pre-checks in parallel with the next action to hide latency.

Specifically, Lyra can adopt a **dual-engine architecture** similar to NeMo's LLMRails/IORails split:
- A "full runtime" engine (for complex multi-agent workflows, RAG, tool orchestration) with the Colang analogy being Lyra's own flow DSL
- An "optimized path" engine (for simple safety/quality gates) that strips runtime overhead and runs checks in parallel with agent generation

**Workstream route:** §4.2 (Agent Runtime Engine) -- the dual-engine architecture and speculative execution pattern directly apply to Lyra's agent execution pipeline.

**Impact:** 8/10 -- Speculative guardrail execution could meaningfully reduce per-turn latency for Lyra agents by hiding validation behind generation.

**Effort:** 5/10 -- The pattern is conceptually simple (race a safety coroutine against the LLM call), but integrating it requires Lyra's agent loop to support concurrent validation tasks and graceful cancellation.

**Tier:** P1 -- This is a latency optimization for the core agent loop, not an experimental feature.

**LICENSE:** Apache 2.0 -- Compatible with Lyra's likely licensing. Attribution required, no copyleft restrictions.
