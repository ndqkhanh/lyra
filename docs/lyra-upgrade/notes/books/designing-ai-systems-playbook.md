# Designing AI Systems — Best Practices Playbook

## Practice 1: Hierarchical Context Engineering (3-Tier Memory)
- **What:** Structure the context window into three tiers: model-managed key-value memories (~10% budget) for critical facts that must never be lost, a rolling LLM summary of older conversation history (~20% budget), and verbatim recent messages (~70% budget). Assembly order matters due to the "lost in the middle" phenomenon — put critical facts at the beginning and recent messages at the end.
- **Why:** Simple truncation drops safety-critical information (a penicillin allergy mentioned in message 1 is gone by message 50). Full conversation history exceeds token budgets. Hierarchical memory preserves essential facts as structured data (persisting across sessions), compresses older context into summaries (extending effective window length), and retains verbatim recent exchanges (preserving conversational fidelity).
- **Lyra route:** §4.2 (Memory/Context)
- **Source:** Chapter 4, Sections 4.6-4.7

## Practice 2: Platform-Service Isolation with Automatic Observability
- **What:** Build independent platform services (Model, Session, Data, Guardrails, Workflow) behind a unified API Gateway. Each service extends a `TracedService` base class that automatically creates distributed trace spans and generations on every call. Use gRPC + Protocol Buffers for internal communication (30-50% smaller, 3-5x faster than JSON), HTTP + JSON for external access. Separate observability into 5 data model primitives: Sessions, Traces, Spans, Generations (specialized LLM spans), Scores.
- **Why:** Without platform-level isolation, teams rebuild the same session management, cost tracking, and safety infrastructure independently (AI sprawl). Without automatic tracing, debugging a single slow request requires manually correlating timestamps across isolated service logs. gRPC efficiency compounds at scale (5+ internal calls per user request).
- **Lyra route:** §4.5 (Model), §4.2 (Session), §4.3 (Data), §4.22 (Observability)
- **Source:** Chapter 1, Section 1.5 (end-to-end trace); Chapter 2, Section 2.4; Chapter 7, Section 7.5

## Practice 3: Model-Managed Memory with Structured Fact Persistence
- **What:** Extend the Session Service with a key-value memory store where the LLM actively decides what to remember via a `save_memory` tool. Each memory entry has a user_id, optional session_id (for session-scoped vs. cross-session persistence), key, and arbitrary JSON value. Key insight: memories are mutable (can be updated), unlike the append-only message log. Memory writes should be logged as audit events.
- **Why:** Inspired by the MemGPT paper concept (context window as RAM, external storage as disk). A patient's penicillin allergy entered in message 3 must be available in message 50 and in a session 6 months later. Structured memories survive context window truncation and cross sessions. The model extracts the "what" (allergy=penicillin) while messages preserve the "how" (full context of how it was discussed).
- **Lyra route:** §4.2 (Memory/Context)
- **Source:** Chapter 4, Sections 4.6

## Practice 4: The Five Inspection Points for Guardrails
- **What:** Implement safety at five specific interception points, not just as content filters: (1) Input validation — prompt injection detection, topic classification, schema validation; (2) Pre-tool policy checks — before executing any external action, verify permissions; (3) Argument validation — check tool call arguments against constraints; (4) External response filtering — sanitize data from external APIs before it reaches the model; (5) Output filtering — PII redaction, hallucination detection, factual grounding. Use declarative YAML policies that separate safety constraints from application logic.
- **Why:** Relying solely on model behavior/prompt engineering for safety is fragile — users can and will manipulate prompts. A proper guardrails system makes safety violations impossible rather than hoping the model behaves. The five inspection points ensure coverage at every layer where unsafe actions could occur.
- **Lyra route:** §4.16 (Safety), §4.17 (Guardrails)
- **Source:** Chapter 6, Sections 6.5-6.8

## Practice 5: The Improvement Loop (Observability → Experimentation → Production)
- **What:** Close the loop: Production traffic generates traces → Scores (automated, LLM-judge, human) attach quality signals → Low-scoring traces flow into evaluation datasets → Offline evaluation compares prompt/model/retrieval variants → A/B testing validates the winner in production → Results feed back into production. The Experimentation Service manages a target lifecycle (DRAFT → TESTING → ACTIVE → DEPRECATED) that applies to any artifact type: prompts, model configs, or retrieval configs. A/B tests use consistent hashing on user ID to ensure the same user always sees the same variant.
- **Why:** Without this loop, teams fall into "gut-feel prompt engineering" (rewrite prompts based on complaints, deploy blindly) or "analysis paralysis" (collect data but never experiment). Three evaluation modes reinforce each other: offline catches regressions before deployment, online catches problems curated datasets miss, human evaluation calibrates the automated scorers.
- **Lyra route:** §4.22 (Observability/Evaluation)
- **Source:** Chapter 7, Sections 7.7-7.9

## Practice 6: Provider Adapter Pattern with Cost-Aware and Capability-Based Routing
- **What:** Build provider adapters that translate between a unified platform interface and each provider's specific API (OpenAI, Anthropic, Google, self-hosted). Implement multiple routing strategies: cost-aware (select cheapest capable model based on current spending vs. budget), load-balancing (distribute across providers/regions), feature-based (route to models that support required capabilities like vision or function calling). Always configure fallback chains with exponential backoff retry.
- **Why:** Applications that hard-code provider-specific APIs become locked in. When OpenAI introduced GPT-4o or Anthropic released Claude 3.5 Sonnet, teams should be able to evaluate and adopt without rewriting application logic. A single provider outage shouldn't break all AI features.
- **Lyra route:** §4.5 (Model/Provider abstraction)
- **Source:** Chapter 3, Sections 3.4-3.5

## Practice 7: Telemetry Buffering with Fire-and-Forget Ingestion
- **What:** All platform services publish telemetry (spans, metrics, logs) through an in-memory buffer managed by an `ObservabilityClient`. The client batches telemetry locally and flushes periodically (every 5s or when batch_size=100 is reached). If the Observability Service is down, the buffer retries on the next cycle. If the buffer exceeds max_buffer_size, oldest data is dropped. Never make user-facing request processing depend on observability ingestion succeeding.
- **Why:** Adding a network round-trip to every service call for telemetry would cripple latency. If the Observability Service goes down, it must never cause user-facing requests to fail or slow down. This fire-and-forget design ensures observability is comprehensive by default without becoming a single point of failure.
- **Lyra route:** §4.22 (Observability)
- **Source:** Chapter 7, Sections 7.5.3

## Practice 8: Controlled Rollout of Safety Policies (Shadow → Canary → Full)
- **What:** Deploy new guardrail policies through three phases: Shadow mode (evaluate policy against live traffic but take no action — measure false positive rate), Canary enforcement (enforce on a small percentage of traffic — monitor for user impact), Full enforcement (enable for all traffic). If the canary shows elevated false positives, automatically roll back. This applies to guardrails, prompt changes, and model switches.
- **Why:** A new guardrail policy that incorrectly blocks 5% of legitimate requests deployed at full scale causes immediate user-facing damage. Shadow mode reveals the true false positive rate against real traffic. Canary enforcement limits blast radius. Automatic rollback prevents prolonged damage.
- **Lyra route:** §4.17 (Guardrails/Safety rollout)
- **Source:** Chapter 6, Section 6.8

## Practice 9: Workflow Metadata Decorator Pattern (Control Plane vs. Data Plane)
- **What:** Use a non-invasive `@workflow` decorator that attaches a metadata dictionary to the function without changing its behavior. The metadata has two consumers read at two different times: the deployment pipeline reads scaling/resources parameters when building the container, and the runtime server reads reliability/mode parameters at container startup. Three response modes: synchronous (JSON response, timeout-enforced), streaming (Server-Sent Events for progressive token delivery), asynchronous (202 Accepted + job_id + polling endpoint).
- **Why:** The developer writes one function that is callable directly in tests (no platform required) and deployable in production (full container orchestration). Separating control plane (deployment/operations) from data plane (request handling) prevents deployment concerns from polluting request-time logic. Three response modes cover all AI interaction patterns without forcing one approach.
- **Lyra route:** §4.7 (Plugin/Workflow system), §4.9 (Commands)
- **Source:** Chapter 8, Sections 8.1-8.2

## Practice 10: Knowledge Index Isolation with Per-Index Embedding Configuration
- **What:** Organize organizational knowledge into named, isolated indexes — each with its own embedding model, chunking strategy, and metadata schema. Support team gets a troubleshooting index with a support-optimized embedding model. Legal team gets a compliance index with a legal-text-optimized embedding model. Create an allowlist of approved embedding models for compliance (some route data to external APIs). To migrate embedding models, create a new index, re-ingest documents, validate retrieval quality, then swap traffic.
- **Why:** A single index mixing all document types with a one-size-fits-all embedding model degrades search quality for everyone. Inconsistent metadata keys across teams (dept vs department) silently corrupt search results when filtering. Embedding models optimized for general text perform poorly on domain-specific content (legal, medical, technical).
- **Lyra route:** §4.3 (Data/Knowledge retrieval)
- **Source:** Chapter 5, Sections 5.2

## Practice 11: Circuit Breakers for Tool Execution
- **What:** Implement per-tool circuit breakers using the standard closed → open → half-open state machine pattern. When a tool fails N times within a time window, the circuit opens and the platform fast-fails subsequent calls instead of letting them queue up and timeout. After a cooldown period, one trial request flows through (half-open). If successful, the circuit closes; if it fails, back to open. Apply per-invocation resource limits (timeout, memory, response size) to prevent one tool from consuming unbounded resources.
- **Why:** A single failing external API (payment processor down, calendar service degraded) can cause cascading failures if every request waits for the full timeout. Circuit breakers prevent one failing tool from degrading the entire platform. Resource limits prevent memory exhaustion from unusually large tool responses.
- **Lyra route:** §4.7 (Tool/Plugin reliability)
- **Source:** Chapter 6, Section 6.4

## Practice 12: Production-to-Dataset Pipeline for Evaluation
- **What:** Build evaluation datasets from two sources: hand-curated test cases (covering known scenarios) and production traces filtered by quality signals. Query the Observability Service for traces with low helpfulness scores, triggered guardrails, or anomalous patterns. Route flagged traces through an annotation queue with `require_human_review=True` before they become test cases. Update datasets every few weeks as user behavior evolves.
- **Why:** The most valuable test cases are the ones you can't anticipate — edge cases that confused the model in production. Hand-curated datasets cover known scenarios but miss emerging user behavior patterns. Requiring human review before traces enter the dataset prevents garbage-in-garbage-out evaluation.
- **Lyra route:** §4.22 (Evaluation)
- **Source:** Chapter 7, Section 7.8.1

## Practice 13: The Three-Level Debugging Workflow (Trace → Logs → Metrics)
- **What:** When investigating any production issue: (1) Start with the trace waterfall visualization to identify the bottleneck service/span. (2) Drill into structured logs for that specific trace_id to see detailed event sequences (which guardrail rules fired with what confidence scores). (3) Confirm with aggregate metrics to distinguish between a one-off issue and a systemic pattern over time. This workflow resolves most production issues in minutes.
- **Why:** Without correlated traces and logs, operators manually compare timestamps across isolated service log streams (often with unsynchronized clocks). The waterfall visualization immediately reveals which span consumed most time. Logs for the exact trace_id provide the "why." Metrics confirm whether the pattern is widespread. This three-step workflow is the standard operating procedure for AI system debugging.
- **Lyra route:** §4.22 (Observability/Debugging)
- **Source:** Chapter 7, Section 7.4.3

## Practice 14: Synchronous + Asynchronous + Streaming API Patterns
- **What:** Expose AI workflows through three interaction patterns, all built on HTTP: (1) Synchronous POST → JSON response for operations completing in <10 seconds (image classification, quick RAG). (2) Asynchronous POST → 202 + job_id → GET /jobs/{id} polling with progress for long-running operations (deep research, batch processing). (3) Streaming POST + Accept: text/event-stream → Server-Sent Events for progressive token delivery (conversational generation). Also return `estimated_duration` and `current_step` in async status responses.
- **Why:** AI operations have fundamentally different timing characteristics than traditional web APIs. Forcing everything through synchronous request-response creates terrible UX (20-second blank screen waiting for a full response). Asynchronous patterns survive browser closures and network disruptions. Streaming creates perceived responsiveness even when total generation time is unchanged.
- **Lyra route:** §4.9 (Command/response modes)
- **Source:** Chapter 2, Sections 2.3.4; Chapter 8, Section 8.1

## Practice 15: Declarative Safety Policies with Shadow Mode Testing
- **What:** Define safety policies as YAML configurations (not code) that specify inspection points, conditions, and actions (block, flag, redact, log). Compliance teams write and maintain these policies; developers handle violation errors. Shadow mode evaluates policies against live traffic without enforcement — measuring false positive rates against real data before any user impact. Only promote to enforcement after shadow mode confirms acceptable precision.
- **Why:** Safety policies encoded in application logic require developer changes for every policy update, creating bottlenecks and increasing risk of misimplementation. Compliance teams should own policies without needing to understand application code. Shadow mode reveals the gap between theoretical policy behavior and real-world false positive rates against diverse user inputs.
- **Lyra route:** §4.16-17 (Safety/Guardrails)
- **Source:** Chapter 6, Sections 6.6-6.8
