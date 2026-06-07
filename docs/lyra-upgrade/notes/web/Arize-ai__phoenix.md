# Arize-ai/phoenix -- Deep-Read

**URL:** https://github.com/Arize-ai/phoenix
**Version Reviewed:** v17.2.0
**Date:** 2026-06-07

---

## 1. Headline Feature & Mechanism

Phoenix is an **open-source AI observability platform** for experimenting with, evaluating, and troubleshooting LLM applications. Its core mechanism is an **OpenTelemetry-based trace ingestion pipeline** that decodes OTLP gRPC spans into a rich semantic model (`SpanKind`, `SpanStatusCode`, `SpanAttributes`), persists them via SQLAlchemy, and exposes them through a GraphQL API (Strawberry) consumed by a React/Relay SPA. Three tightly integrated subsystems sit on top of this foundation:

- **Evaluation framework** -- LLM-as-judge evaluators that run against traced spans and optionally produce versioned datasets and experiments.
- **Playground** -- In-browser prompt engineering environment where users can replay traced LLM calls, swap models/parameters, and save prompt versions.
- **PXI built-in agent** -- A Pydantic-AI-based agent embedded in the product that can debug traces across a project, query the GraphQL API, load datasets, author evaluators, read/search documentation via MCP, and navigate the Phoenix UI itself. PXI is permission-gated, admin-controllable, and extensible via skills and web access capabilities.

The data flow is:

1. LLM application emits spans via OTLP gRPC -> Phoenix gRPC `Servicer.Export()` receives them.
2. `decode_otlp_span()` converts protobuf spans into Phoenix-native `Span` dataclasses, synthesizing OpenInference semantic convention attributes alongside raw OTel attributes.
3. Spans are enqueued into a `BulkInserter` thread that batches writes to SQLite or PostgreSQL.
4. The GraphQL layer serves cached, paginated, and filtered views of spans, traces, projects, datasets, experiments, and evaluations.
5. The React frontend renders all of this with a Relay-driven component tree.

---

## 2. Architecture & Core Modules

### Entry Point

`src/phoenix/server/main.py` is the CLI entry. It registers two subcommands (`serve`, `db`) via argparse. `serve` calls `create_app()` in `src/phoenix/server/app.py`, which assembles the FastAPI application with all middleware, routers, GraphQL schema, gRPC server, database engine, and agent infrastructure.

### Core Modules

| Module | Path | Role |
|--------|------|------|
| **Server** | `src/phoenix/server/` | FastAPI app, gRPC server, middleware (auth, CORS, telemetry, rate limiting), CLI |
| **GraphQL API** | `src/phoenix/server/api/` | Strawberry schema with ~90 type modules, ~25 dataloaders, ~27 mutation modules, queries, subscriptions, REST v1 routers |
| **Trace Models** | `src/phoenix/trace/` | Core `Span` dataclass (`trace/schemas.py`), OTLP encode/decode (`trace/otel.py`), OpenInference semantic conventions, span evaluations |
| **Database** | `src/phoenix/db/` | SQLAlchemy ORM models (`db/models.py` ~100 tables), migrations (Alembic), bulk inserter, facilitator, engines (SQLite/PostgreSQL) |
| **PXI Agent** | `src/phoenix/server/agents/` | Pydantic-AI-based agent (`agent_factory.py`), model factory (`model_factory.py`), capabilities (Mintlify docs MCP, skills, web search/fetch), prompt management |
| **Sandbox** | `src/phoenix/server/sandbox/` | Multi-provider sandbox abstraction (WASM, E2B, Daytona, Vercel, Modal) for safe code execution |
| **Evals** | `packages/phoenix-evals/` (workspace) | LLM-as-judge evaluation library: RAG relevance, answer relevance, hallucinations, Q&A correctness |
| **Client** | `packages/phoenix-client/` (workspace) | Lightweight REST/GraphQL client for the Phoenix server API |
| **OTel** | `packages/phoenix-otel/` (workspace) | OpenTelemetry wrapper with Phoenix-aware defaults |
| **Frontend** | `app/src/` | React + TypeScript SPA with Relay GraphQL client; pages: projects, traces, spans, datasets, experiments, playground, dashboards, agents/chat |

### Architecture Pattern

**Backend**: Layered hexagonal architecture -- gRPC/REST at the boundary -> service layer -> SQLAlchemy persistence -> GraphQL as the contract layer for the UI. Strawberry provides the GraphQL schema, dataloaders batch database queries, and mutations are organized by domain.

**Frontend**: React component tree with Relay for data fetching. Context providers for theme, credentials, feature flags, preferences, functionality. Navigation via React Router with lazy-loaded page modules.

**Agent**: Capability-based composition. The PXI agent is built by composing capabilities (external tools, docs MCP, web search/fetch, skills) into a Pydantic-AI `Agent` instance. Each capability is wrapped in OpenInference instrumentation for self-tracing.

---

## 3. Performance / Benchmarks

The README does not publish benchmark numbers. As an observability tool, its performance characteristics are operational rather than algorithmic:

- **Trace ingestion** is designed to be non-blocking: the gRPC handler decodes spans in a threadpool then enqueues them. The `BulkInserter` batches database writes.
- **SQLite** is used for local development and single-user deployment; **PostgreSQL** is the production backend with connection pooling via `asyncpg`.
- **GraphQL query optimization**: Dataloaders (`CacheForDataLoaders`, `AnnotationSummaryDataLoader`, etc.) implement batching and caching. `MaxAliasesLimiter` and `QueryDepthLimiter` are Strawberry extensions that prevent expensive or recursive queries.
- **Frontend**: Relay's `@defer` directive is used for streaming large fields. Cursor-based pagination is applied throughout the GraphQL API.

---

## 4. Trade-offs

### Wins
- **Vendor and language agnostic** -- works with any framework that emits OTLP (OpenAI, Anthropic, LangChain, LlamaIndex, DSPy, CrewAI, Vercel AI SDK, Claude Agent SDK, etc.).
- **Rich semantic model for AI workloads** -- `SpanKind` (TOOL, CHAIN, LLM, RETRIEVER, AGENT, GUARDRAIL, etc.) goes far beyond generic OTel span kinds, enabling domain-specific visualizations and filters.
- **Self-instrumenting agent** -- PXI traces its own operations, enabling dogfooding and easier debugging.
- **Sandbox diversity** -- supports 5 sandbox providers (WASM, E2B, Daytona, Vercel, Modal) so users can choose their security/compute trade-off.
- **Embedded evaluation framework** -- evals are not a separate product; they run against spans already in the database.

### Losses
- **Elastic License 2.0 (ELv2)** -- not truly open-source. Restricts use as a hosted/managed service for third parties. Cannot deploy as a multi-tenant SaaS offering without an additional commercial license.
- **Heavy dependency graph** -- `pyproject.toml` lists ~45 production dependencies including OpenAI, Anthropic, Pydantic-AI, FastAPI, Strawberry, SQLAlchemy, Alembic, gRPC, Prometheus, LDAP, OAuth2 libraries. Each is pinned and version-managed, but the surface area is large.
- **Strawberry GraphQL version lock** -- pinned to `==0.316.0`, which constrains GraphQL feature adoption.
- **Database split** -- SQLite for local dev, PostgreSQL for production. This creates an impedance mismatch: some features (e.g., full-text search, vector operations) behave differently or are absent in SQLite.
- **No built-in alerting** -- Phoenix is observability + debugging, not monitoring/alerting. Users must pair it with Prometheus/Grafana.
- **Frontend bundled as binary artifacts** -- the React SPA is pre-built and committed as static files, making frontend contributions require a full local build pipeline (pnpm install + build).

---

## 5. Design Rationale

Several architectural decisions reveal Phoenix's design philosophy:

**OpenTelemetry-first**: By building on the OTLP standard rather than a custom ingestion protocol, Phoenix integrates with the growing ecosystem of OTel-instrumented applications. The `openinference-semantic-conventions` package extends OTel with AI-specific attributes (token counts, tool parameters, prompt templates) so that generic OTel tooling also captures AI semantics.

**GraphQL as the internal contract**: Rather than a REST-only API, Phoenix uses Strawberry GraphQL as the primary data-fetching layer for the UI. This lets the frontend demand exactly the span/project/evaluation data it needs in a single round trip, using Relay for efficient client-side caching and pagination.

**Capability-based agent composition**: The PXI agent is not a monolithic code path. It's assembled from pluggable `CapabilityFunc` builders that add features (MCP docs server, web search, skills loading) via Pydantic AI's capability system. This design anticipates future capabilities without changing the agent core.

**Sandbox abstraction as the evaluation executor**: Rather than running LLM-written code in-process, Phoenix delegates execution to isolated sandboxes with a uniform `SandboxAdapter` protocol. This was a deliberate response to security concerns (CVE-2026-42208 in litellm is explicitly noted in the dependency overrides).

**Self-tracing for dogfooding**: The server and agent are instrumented with their own OpenInference semantics. This means Phoenix can debug its own performance using the same tools it offers to users -- a powerful consistency guarantee.

**Separate Python sub-packages**: `phoenix-otel`, `phoenix-evals`, and `phoenix-client` are published as independent packages (and workspace members), allowing users to consume only what they need (e.g., send traces to a remote Phoenix instance without running a local server).

---

## 6. Transfer to Lyra

**Transferable Idea**: **OpenTelemetry-span-based agent tracing pipeline** -- Phoenix's pattern of ingesting OTLP spans, decorating them with AI-semantic attributes (OpenInference conventions), and exposing them through a GraphQL API is directly applicable to Lyra's reliability and safety observability needs.

**Why it fits**: Lyra currently lacks structured telemetry for its agent loops. Implementing a Phoenix-inspired OTel ingestion layer would give Lyra:
- Trace visualization of multi-step agent chains (tool calls, LLM invocations, retrievals)
- Cost/latency attribution per span
- Evaluation data attached to specific trace nodes
- A GraphQL API that the Lyra UI and safety monitors can query uniformly

**Implementation path**:
- Adopt `openinference-semantic-conventions` for Lyra's agent spans (kinds: AGENT, TOOL, LLM, RETRIEVER, GUARDRAIL)
- Implement a lightweight OTLP gRPC receiver or use Phoenix as the backend directly
- Build Lyra-specific span processors that inject safety/verification results as span events

**Workstream route**: This maps to **Lyra Upgrade Plan SS4.x -- Reliability & Observability**. The trace pipeline is the foundation that all other observability features (evaluations, dashboards, alerts) build on.

**Impact vs. Effort vs. Tier**:
- **Impact: 10/10** -- Structured telemetry is the single highest-leverage investment for making Lyra reliable and debuggable.
- **Effort: 7/10** -- Significant because it requires integrating OTel SDKs, defining custom span attributes, building the receiver, and wiring to storage. However, using Phoenix as the backend (rather than building from scratch) cuts effort significantly.
- **Tier: Tier 1 (Core/Foundation)** -- Every other reliability, safety, and debugging feature depends on having trace data in the first place.

**License note**: Phoenix is ELv2 licensed. If Lyra embeds Phoenix directly, the ELv2 hosting restriction would apply. A safer path is to adopt the OpenInference span semantics and OTLP protocol without embedding the Phoenix server, or to use `phoenix-otel` and `phoenix-evals` as pip/NPM dependencies (which are published as separate packages with their own licensing).
