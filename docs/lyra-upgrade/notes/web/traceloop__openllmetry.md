# traceloop/openllmetry -- Deep-Read

## 1. Headline Feature & Mechanism

OpenLLMetry is an open-source LLM observability layer built on top of OpenTelemetry (OTel). Its headline feature is **zero-code auto-instrumentation of LLM applications**: add `Traceloop.init()` to your Python app and it transparently traces every call to OpenAI, Anthropic, Bedrock, Gemini, Mistral, Ollama, Cohere, and 15+ other LLM providers, plus vector DBs (Pinecone, Chroma, Qdrant, Milvus, Weaviate) and AI frameworks (LangChain, LlamaIndex, Haystack, CrewAI, LangGraph).

**How it really works** -- three-layer mechanism:

1. **Monkey-patching via `wrapt`**: Each instrumentation package (e.g., `opentelemetry-instrumentation-openai`) calls `wrapt.wrap_function_wrapper("openai.resources.chat.completions", "Completions.create", chat_wrapper(...))` on `_instrument()`. This intercepts every library call at the method level, wrapping it in an OpenTelemetry span before delegating to the real implementation.

2. **OpenTelemetry pipeline**: The wrapped function creates a span (`tracer.start_span(SpanKind.CLIENT)`), records request attributes (model, temperature, messages), calls the original function, records response attributes (completion, usage tokens, finish reason), and ends the span. Errors are captured as span events + `ERROR_TYPE` attribute. For streaming responses, a `ChatStream(ObjectProxy)` wraps the generator, accumulating chunks and closing the span when iteration completes.

3. **Output to any OTLP backend**: Because spans are standard OTel, they can be exported via HTTP or gRPC OTLP exporters to 20+ backends (Datadog, Honeycomb, New Relic, SigNoz, Grafana, Splunk, Sentry, etc.) without any vendor lock-in.

## 2. Architecture & Core Modules

The repo is a **monorepo** with an Nx workspace (Python via `@nxlv/python` plugin), `uv` as the package manager, organized into ~33 packages:

### Core packages

| Package | Purpose |
|---------|---------|
| `traceloop-sdk` (v0.61.0) | Main entry point. `Traceloop.init()` configures the tracer provider, span processor, metrics, logging, and auto-instruments by iterating over all registered `Instruments`. Also provides `@workflow`, `@task`, `@agent`, `@tool` decorators for manual instrumentation of custom code. |
| `opentelemetry-semantic-conventions-ai` | Shared constants defining `SpanAttributes`, `Meters`, `Events`, and `GenAISystem` enum -- the canonical attribute names for LLM spans (e.g., `gen_ai.request.model`, `gen_ai.usage.completion_tokens`). Now partially adopted into the official OTel semconv spec. |
| `opentelemetry-instrumentation-openai` | Reference instrumentation. Covers v0 and v1 APIs, sync/async, chat completions, embeddings, image gen, assistants, responses API, realtime API. Uses `wrapt.wrap_function_wrapper` to patch `openai.resources.*` classes. |
| `opentelemetry-instrumentation-anthropic` | Anthropic Messages API instrumentation. Same pattern -- wraps `anthropic.Anthropic().messages.create()`. |
| 28 other instrumentation packages | Same pattern for each provider/DB/framework. Each is independently pip-installable. |

### Entry point flow

```
Traceloop.init()
  -> TracerWrapper (singleton, OTel TracerProvider)
     -> init_tracer_provider() -- creates/resues TracerProvider
     -> get_default_span_processor() -- HTTP or gRPC OTLP exporter + BatchSpanProcessor
     -> ThreadingInstrumentor().instrument() -- ensures OTel context propagates across threads
     -> init_instrumentations() -- iterates Instruments enum, calls each init_*_instrumentor()
        -> OpenAIInstrumentor().instrument() -- wraps openai methods
        -> AnthropicInstrumentor().instrument() -- wraps anthropic methods
        -> ... for all enabled instruments
  -> MetricsWrapper (OTel MeterProvider, histograms/counters for token usage, latency)
  -> LoggerWrapper (OTel LoggerProvider for event-based prompt/completion logging)
```

### Data flow

```
User code -> wrapped library function -> OTel span created -> request attrs recorded
  -> original function called -> response attrs + metrics recorded -> span ended
  -> BatchSpanProcessor exports via OTLP -> [Datadog|Honeycomb|Grafana|...]
```

### Architecture pattern

**Instrumentor pattern** (Decorator/Monkey-patch): Each package implements `BaseInstrumentor` with `_instrument()` / `_uninstrument()` lifecycle. The instrumentor creates meters (histograms, counters), wraps specific library methods using `wrapt.wrap_function_wrapper`, and registered via `pyproject.toml` entry points under `[project.entry-points."opentelemetry_instrumentor"]` so they auto-discover.

## 3. Performance/Benchmarks

The repo does not publish formal benchmarks in its README or docs. The overhead characteristics derive from OpenTelemetry's SDK:

- **Span creation overhead**: ~0.1-0.5ms per span (negligible vs. LLM call latency of 200ms-30s)
- **Batch export**: Default `BatchSpanProcessor` exports in batches (up to 512 spans / 5s interval), minimizing I/O overhead
- **Memory**: Each span holds request/response payloads as string attributes; large prompts could increase memory pressure (mitigated by `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT`)
- **No synchronous network**: Exports are async/in-background in production (batch mode); `disable_batch=True` is for local debugging only

Key performance design decisions visible in code:
- `EXCLUDED_URLS` list prevents double-instrumentation of OTel's own HTTP calls and common AI API base URLs
- `ChatStream` proxy uses `threading.Lock()` for thread-safe cleanup
- `dont_throw` decorator ensures instrumentation failures never crash the host application
- Content tracing can be toggled off via `TRACELOOP_TRACE_CONTENT=false` to save attribute storage

## 4. Trade-offs

### Wins
- **Zero-code adoption**: Single-line `Traceloop.init()` instruments everything -- massively lower barrier than manual OTel setup
- **Vendor freedom**: Standard OTel output means no lock-in to any single observability platform
- **Breadth of coverage**: 30+ instrumentations (providers + DBs + frameworks) all under one consistent schema
- **OTel compliance**: Semantic conventions are upstreamed into the official OpenTelemetry project, ensuring forward compatibility
- **Rich SDK beyond instrumentation**: `@workflow`/`@task`/`@agent`/`@tool` decorators, guardrails, evaluators, datasets, prompt management -- not just tracing
- **Active maintenance**: Y Combinator-backed, frequent releases (v0.61.0 as of June 2026), responsive to upstream API changes

### Loses / known limitations
- **Monkey-patching fragility**: `wrapt.wrap_function_wrapper` patches internal class methods -- compatible only with specific library versions. When a library bumps a major version or renames internal classes, instrumentation breaks. Evidence: the `_try_wrap` pattern with try/except for beta APIs, and separate v0/v1 instrumentors in OpenAI.
- **Streaming complexity**: `ChatStream` proxy is a large (250+ lines), stateful wrapper with locking and deferred cleanup -- a significant maintenance surface for a "zero-code" abstraction.
- **Semconv migration churn**: The repo carries extensive compatibility layers for attribute renames. File `semconv_ai/__init__.py` is ~400 lines with "TODO: migrate" comments throughout, documenting at least three naming generations (`LLM_*` -> `GEN_AI_*` with value changes, plus underscore-to-dot cache key migrations).
- **No built-in storage**: Unlike dedicated LLM observability platforms (LangSmith, Weights & Biases), OpenLLMetry is purely a pipe -- you must bring your own OTel backend. No query UI, no experiment comparison.
- **Python-only (for the main repo)**: JS/TS is a separate project (`openllmetry-js`) with potentially divergent feature sets.
- **Traceloop SaaS dependency for full features**: Guardrails, evaluators, and datasets require the Traceloop cloud API key.
- **Attribute size limits on prompts**: Large system prompts or multi-turn conversations hit OTel's default attribute size limits, requiring truncation or event-based emission (which then needs an `EventLoggerProvider` config).

## 5. Design Rationale

The choice of OpenTelemetry as the foundation (rather than building a bespoke observability protocol or a managed SaaS agent) reflects several deliberate decisions:

1. **Ecosystem leverage**: OTel is the CNCF standard for observability. By building on it, OpenLLMetry inherits a mature pipeline (sampling, batching, export, context propagation) and immediate integration with every major observability backend.

2. **Standardization over control**: The project invested in upstreaming LLM semantic conventions into the OTel spec rather than defining proprietary attributes. This means longer development cycles (attribute names must go through OTel RFC process) but ensures the data is natively understood by all OTel-compatible tools.

3. **Monorepo for aligned versioning**: All 33 packages version-bump together, ensuring semantic convention changes are atomically rolled out. The `pyproject.toml` sources use `editable = true` path references for development, a unified schema.

4. **wrapt over import hooks**: `wrapt.wrap_function_wrapper` was chosen over Python import hooks (`sys.meta_path`) because it is simpler, more predictable (no import order issues), and allows clean `_uninstrument()` by reference.

5. **Singleton tracer**: `TracerWrapper` uses a singleton pattern (`__new__`) so that `Traceloop.init()` can be safely called once, and `TracerWrapper.verify_initialized()` acts as a runtime guard for decorators that need the tracer to exist.

## 6. Transfer to Lyra

### Idea: Instrument Lyra's LLM call layer with the OpenLLMetry wrapping pattern

Lyra's Workflow Engine (§5.4 in the Lyra architecture) makes many LLM calls across potentially multiple providers (OpenAI, Anthropic, local models). By applying the same `wrapt.wrap_function_wrapper` + OTel semantic conventions pattern that OpenLLMetry pioneered, Lyra could gain:

- **Automatic cost tracking**: Capture model, token usage, and finish reason per LLM call as OTel span attributes, exportable to any observability backend
- **Latency histograms**: Track P50/P95/P99 of LLM call durations by model and provider
- **Error attribution**: Record error types (rate limit, timeout, content filter) with `error.type` attributes
- **Workflow-span correlation**: Propagate trace context through Lyra's workflow DAG so every LLM call within a workflow is correlated under one trace ID

### Implementation route

**Route**: §5.4 Workflow Orchestration (specifically the LLM invocation layer within the task executor)

Instead of embedding OpenLLMetry as a direct dependency (which would pull in its full SDK and all instrumentations), Lyra should:

1. Import only `opentelemetry-sdk` and `opentelemetry-api` as dependencies
2. Adopt the `opentelemetry-semantic-conventions-ai` package (or copy the `SpanAttributes` constants) for attribute naming
3. Wrap Lyra's internal LLM client abstraction (the layer that calls `client.chat.completions.create(...)`) with an OTel span, following the `chat_wrapper` pattern
4. Export via a configurable `OTLPSpanExporter` (HTTP/gRPC) so users can plug in any OTel backend

### Impact / Effort / Tier

- **Impact**: 8/10 -- brings production-grade observability to Lyra workflows without requiring users to adopt a specific monitoring platform
- **Effort**: 5/10 -- moderate. Requires adding OTel SDK as a dependency, instrumenting ~3-5 internal call sites (LLM call, tool execution, workflow steps), and adding a configuration surface for the OTLP endpoint/headers. The pattern is well-documented by OpenLLMetry.
- **Tier**: Tier 2 (Post-MVP Quality) -- essential for production deployment but can follow initial workflow engine implementation

### LICENSE

Apache 2.0 -- fully permissive for copy/modify/redistribution. No attribution requirements beyond retaining the notice file. Compatible with Lyra's existing license (if also Apache 2.0 or MIT).
