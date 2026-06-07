# Designing AI Systems — Chapter Notes

**Author:** Suhas Suresha and Dewang Sultania
**Year:** 2026 (MEAP v4, Manning Publications)
**Core Thesis:** The model API call represents only 2% of total system complexity in modern GenAI applications. The remaining 98% — knowledge management, session management, safety/compliance layers, tool integration, observability, model abstraction, and infrastructure — must be built as shared platform services to avoid "AI sprawl" where every team independently rebuilds the same infrastructure. Without a platform foundation, AI projects are trapped in the "prototype trap" where demos work brilliantly but production collapses under real load, costs explode without visibility, and safety becomes an afterthought.

---

## Chapter 1: Why Your AI Projects Need a Platform

- **Key insight:** The "prototype trap" is universal — Sam builds a 2-week chatbot prototype that wows leadership, then spends 3 months retrofitting infrastructure (monitoring, cost tracking, session management, safety) that should have existed as platform services. The model API call is just 2% of system complexity — modern GenAI requires vastly more infrastructure than traditional ML (which was already 5-10% model code).
- **Best practices:**
  - Build shared platform services (Session, Data, Model, Tool, Guardrails, Workflow, Observability, Evaluation) rather than letting teams rebuild the same components
  - Design for 7 core requirements: context-aware intelligence, multi-step orchestration, dynamic tool integration, safety/compliance, observability/experimentation, model abstraction, scalable infrastructure
  - Use the "first principles" approach: ask what applications actually need, not what existing platforms provide
- **Anti-patterns:**
  - Building demos without production infrastructure from day one
  - "AI sprawl" — 4 teams in 6 months each implementing their own session management, token tracking, API key storage differently
  - Assuming LangChain/AWS Bedrock/etc. eliminate the need for understanding underlying platform patterns
- **Relevant to Lyra §4.x:** This chapter directly validates Lyra's entire architecture. The platform-service-oriented approach with Session Service (§4.2), Data Service (§4.3), Guardrails Service (§4.16-17), Model abstraction (§4.5), Tool Service (§4.7), and Observability (§4.22) maps 1:1 to the book's service architecture.

---

## Chapter 2: Building with the Platform — SDK and API Design

- **Key insight:** The SDK is the "connective tissue" between developer-written workflow code and distributed platform services. The GenAIPlatform object serves as a lightweight runtime entry point with lazy-initialized service clients. Three distinct interaction patterns are needed: synchronous (<10s), asynchronous (minutes/hours), and streaming (progressive token delivery via SSE).
- **Best practices:**
  - Design the SDK backwards from developer needs — Sarah wants immediate productivity (few lines of code for a working assistant), automatic conversation memory, seamless knowledge integration, reliable safety controls, natural tool integration, systematic optimization, effortless orchestration
  - Use lazy initialization for service clients (platform.sessions exists as None until first access)
  - gRPC + Protocol Buffers for internal service communication (30-50% smaller payloads, 3-5x faster than JSON/HTTP)
  - HTTP + JSON for external client communication (universal, works everywhere)
  - API Gateway as single entry point handling auth, rate limiting, TLS, routing, health checks
  - "One workflow, one service" principle — each workflow gets its own container deployment for independent scaling/versioning
  - Protocol choice: gRPC for internal (efficiency), HTTP for external (universality)
  - Containers (not VMs, not bare processes) for workflow isolation
  - Unified domain structure to prevent API sprawl (all workflows behind a domain share auth, response formats)
- **Anti-patterns:**
  - Running all workflows in a single shared process
  - "API sprawl" — teams deploying workflows at different URLs with different auth mechanisms
  - Forcing one protocol everywhere (HTTP for internal service calls)
- **Relevant to Lyra §4.x:** The SDK design patterns (lazy initialization, gateway routing, @workflow decorator) directly inform Lyra's plugin/workflow system §4.7-4.9. The three interaction patterns map to Lyra's command handling modes.

---

## Chapter 3: The Model Service — Your Platform's Gateway to AI Models

- **Key insight:** Provider adapters hide substantial differences between OpenAI, Anthropic, Google, and self-hosted deployments behind a unified interface. The Model Service handles provider-specific API differences, response formatting variations, error handling, streaming, structured outputs, multimodal inputs, rate limiting, and intelligent routing.
- **Best practices:**
  - Provider adapters translate between platform's unified interface and each provider's specific API
  - Structured output support via response_format (JSON mode, function-calling patterns)
  - Streaming response support with token-by-token delivery
  - Fallback chains with configurable retry strategies and exponential backoff
  - Cost-aware routing: select provider based on current spending and task complexity
  - Load-balancing routing: distribute across providers/regions
  - Feature-based routing: route tasks to models that support required capabilities (vision, function calling)
  - Prompt caching: cache system prompts and reuse across requests to reduce latency/cost
  - Response caching: cache identical requests with semantic deduplication
  - Record per-request metrics (provider, model, tokens, latency, cost, cache status)
  - Feed metrics to Observability Service for unified dashboards
- **Anti-patterns:**
  - Hard-coding provider-specific API calls in application code
  - No fallback strategy — single provider outage breaks everything
  - Ignoring cost metrics (the $50→$2000 invoice mystery)
- **Relevant to Lyra §4.5:** The Model Service architecture directly mirrors Lyra's provider abstraction layer. Fallback chains and cost-aware routing are especially relevant for Lyra's multi-provider strategy.

---

## Chapter 4: The Session Service — Teaching Your AI to Remember

- **Key insight:** A session contains more than message history — it includes tool calls, tool results, metadata. A single user exchange can generate 5+ internal messages (user question → assistant tool call → tool result → assistant response). The OpenAI message format is becoming an industry standard. Context engineering (what to include/exclude from the context window) is as important as prompt engineering.
- **Best practices:**
  - **Session data model:** Users, Sessions, Messages (with roles: user, assistant, system, tool), tool_call_id to link results
  - **Storage abstraction:** Abstract base class (SessionStorage) with pluggable backends (PostgreSQL, Redis, DynamoDB) — swap backends without changing service code
  - **Batch message insertion:** Use executemany for atomic batch inserts, commit once
  - **Pagination:** get_messages with limit/offset + total_count for paginated UIs
  - **Model-managed memory (MemGPT-inspired):** LLM actively decides what to remember via save_memory tool. Memories are key-value (user_id + optional session_id scope). Critical facts survive context window truncation. For healthcare: allergies, medications persist across visits
  - **Context window management strategies:**
    - Simple truncation: keep most recent N messages within budget (good for transactional)
    - Summarization: compress older messages with cheap model call (GPT-4o-mini), cache summaries with hash of covered messages
    - Hierarchical memory: 3 tiers — model-managed memories (critical facts, ~10%), rolling summaries (older context, ~20%), recent verbatim messages (~70%)
    - Retrieval-augmented memory: cross-session search when users reference past conversations
    - "Lost in the middle" mitigation: put critical facts at beginning, recent at end
  - **Memory concurrency:** Last-write-wins for most cases; optimistic concurrency or append-only for critical facts
  - **Memory as audit trail:** Log every save_memory call with context
  - **Strategy selection:** Let workflows choose truncate/hierarchical/retrieval strategy dynamically
- **Anti-patterns:**
  - Simple truncation that drops critical early information (allergy in message 1, dropped by message 50)
  - Generic "summarize this conversation" prompts that omit critical domain-specific details
  - Single context management strategy for all applications — shopping bot vs healthcare vs coding have different needs
- **Relevant to Lyra §4.2:** This chapter is the single most relevant for Lyra's memory subsystem. The hierarchical memory model (model-managed memories + summaries + recent messages) should be directly adopted. The context engineering strategies directly address Lyra's context budget management challenges.

---

## Chapter 5: The Data Service — Teaching AI What Your Organization Knows

- **Key insight:** Organizational knowledge is fundamentally different from conversation history — unstructured documents require an ingestion pipeline (parsing → chunking → embedding → vector storage → similarity search). Index isolation is critical: separate indexes for separate teams/document types with independent embedding models and chunking strategies.
- **Best practices:**
  - **Indexes as isolation units:** Each index has its own embedding model, chunking strategy, and metadata schema. Support team's index vs. Legal team's index never cross-contaminate.
  - **Embedding model per index:** Legal texts may need legal-specific embeddings; technical docs need code-optimized embeddings. Platform can maintain an allowlist of approved models for compliance.
  - **Chunking strategies:** Fixed-size (default 512 tokens, 50 overlap), or semantic-chunk (respect section/sentence boundaries). Per-index configurability.
  - **Metadata schemas:** Enforce consistent metadata keys (dept vs department) at ingestion time via optional schema validation
  - **Hybrid retrieval:** Combine vector similarity search with keyword search for better results
  - **Ingestion pipeline:** File format detection → text extraction → chunking → embedding generation (via Model Service, reusing provider abstraction) → vector storage
  - **Search results include:** Chunk text, source document, relevance score, all metadata for filtering
  - **Index migration:** To change embedding model: create new index with new model, re-ingest, validate, swap traffic
- **Anti-patterns:**
  - Single global index with mixed document types and one embedding model
  - Inconsistent metadata keys across teams (dept/department causing silent filter misses)
  - Changing an index's embedding model in-place (vectors from different models live in incompatible spaces)
- **Relevant to Lyra §4.3:** The Data Service architecture directly maps to Lyra's knowledge retrieval pipeline. Index isolation, per-index embedding configuration, and hybrid retrieval are directly applicable.

---

## Chapter 6: Tools and Guardrails — Enabling Safe, Managed AI Actions

- **Key insight:** Tools are platform-managed capabilities, not JSON blobs embedded in application code. Guardrails are execution policies, not just content filters. Five inspection points: input validation, pre-tool policy checks, argument validation, external response filtering, output filtering. Guardrails must capture what the AI *proposed* (blocked tool calls) not just what actually happened.
- **Best practices:**
  - **Tool Service contract:** Register (with namespaces + versioning), Discover (by namespace/capability), Execute (with automatic credential injection), Validate (check arguments before execution)
  - **Tool metadata:** Rate limits, idempotency declarations, cost info, side-effect documentation
  - **MCP (Model Context Protocol):** Standardizes wire protocol for tool communication. Platform provides organizational capabilities above the protocol: credential management, policy enforcement, rate limiting, audit trails, version governance.
  - **Tool execution isolation:** Per-invocation resource limits (timeout, memory, response size), circuit breakers (closed → open → half-open state machine) to prevent cascading failures
  - **Execution patterns:** Synchronous for fast tools, asynchronous with job tracking for long-running tasks
  - **Guardrail inspection points:** Input (prompt injection detection, topic classification, schema validation) → Pre-tool policy checks → Argument validation → External response filtering → Output (PII redaction, hallucination detection, factual grounding)
  - **Behavioral guardrails:** Session-level permissions, cross-tool consistency checks, human-in-the-loop approval gates for high-stakes operations
  - **Declarative policies:** YAML configs separate safety constraints from application logic. Compliance teams edit policies; developers handle violation errors.
  - **Safe rollout:** Shadow mode evaluation → canary enforcement → automatic rollback
  - **Observability:** Structured logs, operational metrics, compliance-ready audit trails. Audit trails capture attempted (blocked) actions, not just executed ones.
- **Anti-patterns:**
  - Guardrails as content filters only — missing behavioral guardrails that enforce session permissions and cross-tool consistency
  - Tools as hard-coded JSON schemas in application code instead of platform-managed capabilities
  - No circuit breaker pattern — one failing tool degrades entire system
  - Safety relying solely on model behavior/prompt engineering
- **Relevant to Lyra §4.7 (Tools), §4.16-17 (Safety/Guardrails):** The five inspection points, circuit breaker pattern, declarative YAML policies, and MCP integration approach are directly applicable. The audit trail philosophy (capture what was proposed + what was decided) is essential.

---

## Chapter 7: Observability and Experimentation — Seeing and Improving What AI Does

- **Key insight:** Traditional monitoring answers "is the system running?" — AI observability must answer "is the system working correctly?" A web server returning 200 in 50ms is healthy; an AI returning 200 with a fluent but wrong answer is toxic. AI systems need specialized telemetry: token consumption, model costs, retrieval relevance, guardrail evaluations, response quality scores. Observability is passive (watches); Experimentation is active (changes and measures).
- **Best practices:**
  - **Observability data model (5 primitives):** Sessions (group conversations), Traces (single request end-to-end), Spans (unit of work within a service), Generations (specialized span for LLM calls with model/tokens/cost), Scores (quality signals from automated/LLM-judge/human sources)
  - **Generations as first-class:** Separate from generic spans because LLM calls are where most cost/latency concentrates. Directly queryable: "show me all GPT-4 calls > $0.05 this week"
  - **Three-level debugging workflow:** Trace waterfall → identify bottleneck → drill into logs for that trace_id → confirm pattern with metrics. Resolves most issues in minutes.
  - **Histograms over averages:** AI latencies are heavy-tailed. p50=800ms while p99=12s. Averages hide both facts.
  - **Standardized metric naming:** `ai.platform.{service}.{metric_name}`. Counters end in `_total`, histograms in `_ms` or `_score`.
  - **Telemetry never blocks user requests:** ObservabilityClient buffers locally, flushes periodically (5s or batch_size=100). Never a single point of failure.
  - **"Observability by default":** TracedService base class creates spans automatically. Workflow developers call platform.services normally — traces build themselves.
  - **Three evaluation modes:** Offline (catches regressions before deploy), Online (monitors production with sampling), Human (calibrates automated scorers). Reinforcing cycle.
  - **Experimentation service:** 20 gRPC operations in 6 groups — Target lifecycle (DRAFT→TESTING→ACTIVE→DEPRECATED), Dataset management, Offline evaluation, Online scoring, A/B testing (consistent hashing for user assignment), Annotation queues
  - **A/B testing:** Consistent hashing on user ID ensures same user always sees same variant. Track sample sizes, confidence intervals, p-values, effect sizes.
  - **Cost drift-down pattern:** Total → by team → by workflow → by model. Budget alerts at 70%/90%/100% with projected spending.
  - **Annotation queues:** Route low-confidence LLM-judge traces, guardrail-triggered traces, random samples to human reviewers. Reviewers can flag traces for evaluation dataset inclusion.
  - **Custom observability:** SDK exposes same trace_operation context manager for application-specific spans
- **Anti-patterns:**
  - Relying on traditional application monitoring for AI systems (missing quality dimension)
  - Blocking user requests on observability ingestion success
  - LLM-as-judge absolute scores as deployment gates (not calibrated against human evaluation)
  - Gut-feel prompt engineering (no dataset, no scoring, no statistical tests)
  - Analysis paralysis (collecting data but never experimenting)
  - Static evaluation datasets that drift from real user behavior
- **Relevant to Lyra §4.22:** This chapter is the blueprint for Lyra's observability and evaluation infrastructure. The 5-primitive data model, three-level debugging workflow, automatic tracing, and experimentation lifecycle are all directly implementable. The improvement loop (production→scores→datasets→evaluation→A/B test→production) is essential for Lyra's continuous improvement.

---

## Chapter 8: The Workflow Service — Orchestrating and Deploying AI Applications

- **Key insight:** The Workflow Service has a control plane (deployment, scaling, routing) and a data plane (request handling at runtime). The @workflow decorator captures metadata consumed by two different consumers at two different times: the deployment pipeline (reads scaling/resources) and the runtime server (reads reliability/mode). "One workflow, one service" means each @workflow function gets its own container deployment.
- **Best practices:**
  - **Control plane vs. data plane separation:** Control plane = Workflow Service gRPC contract + Kubernetes integration. Data plane = SDK runtime server inside each container.
  - **@workflow decorator:** Non-invasive — attaches metadata dict, doesn't change function behavior. Three config categories: scaling (min/max replicas, CPU/memory thresholds), resources (CPU, memory, GPU), reliability (timeout_seconds, max_retries)
  - **Runtime server:** SDK library code, not a separate service. Uses FastAPI + Uvicorn. Imports developer's module, finds decorated function by WORKFLOW_NAME env var, registers HTTP route
  - **Three response mode handlers:** Sync (inline, JSON response, timeout enforced), Stream (SSE, progressive token delivery), Async (202 Accepted with job_id, background execution, polling endpoint)
  - **Sync handler details:** Validates request body against function signature (422 on mismatch), runs in thread with asyncio.wait_for(timeout), returns 504 on timeout, 500 on exception
  - **Async handler details:** Returns 202 + job_id immediately, runs function in background, provides GET /jobs/{job_id} for status polling with progress percentage and current_step
  - **Stream handler details:** POST with Accept: text/event-stream, yields data: {"token": "..."} events, connection stays open for duration
  - **GPU support:** gpu_type and num_gpus parameters in workflow metadata for GPU-dependent workflows
  - **Deployment pipeline:** Reads decorator metadata → builds container image → registers with Workflow Service → creates Kubernetes Deployment → registers route with API Gateway
  - **Kubernetes integration:** Workflow Service manages Deployments, Services, HorizontalPodAutoscalers mapped from decorator metadata
  - **Workflow composition:** platform.workflows.invoke() method for calling other workflows (sequential) or fanning out in parallel
- **Anti-patterns:**
  - Combining multiple workflows in one container deployment
  - Synchronous handling of long-running operations (should be async)
  - Not separating control plane from request-time concerns
- **Relevant to Lyra §4.7-4.9:** The @workflow decorator pattern, control/data plane separation, three response modes, and composition approach are directly applicable to Lyra's command/workflow routing system.

---

## Chapter 9: Building an AI Assistant — Putting the Platform to Work

- **Key insight:** This chapter serves as a capstone walkthrough, building a personal AI assistant that integrates all platform services: memory (Session Service), knowledge (Data Service), tools (Tool Service), safety (Guardrails), observability, and experimentation. Demonstrates incremental capability addition — start simple, add complexity as needed.
- **Best practices:**
  - Start with basic Model Service integration, then add Session Service for conversation memory
  - Add Data Service for RAG (grounding responses in organizational knowledge)
  - Layer in Tool Service for external API access (calendar, email, etc.)
  - Apply Guardrails progressively (input validation first, then output validation, then behavioral)
  - Enable observability from the start (it comes free with platform services)
  - Add experimentation when optimization becomes necessary (not before)
  - Incremental complexity: don't implement all capabilities upfront; let user behavior guide what to add
- **Relevant to Lyra §4.x:** This chapter validates the incremental development approach. The full assistant build demonstrates how Lyra's services should compose — starting simple and adding capabilities as needed rather than over-engineering upfront.
