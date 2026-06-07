# Grokking Software Architecture — Best Practices Playbook

**Source Book:** Grokking Software Architecture (MEAP V01), Matt Erman, Manning Publications, 2026.
**Context:** These practices are extracted and translated from a general software architecture book for application to Lyra, an AI agent harness. The book itself does NOT cover AI agents; these are principled adaptations of its architectural discipline to Lyra's specific challenges.

---

## Practice 1: The 5-Step Architectural Thinking Process for Every Design Decision

- **What:** Before writing code for any Lyra subsystem, apply the repeatable 5-step process: Spark (what is the request) → Inquiry (why — use 5 Whys) → Sketch (draw boxes and arrows before code) → Options (list 2-3 with explicit pros/cons) → Decision (document what you chose, why, and what consequences you accept).
- **Why:** Lyra is undergoing a major upgrade with many interconnected decisions (plugin protocol, memory architecture, routing mechanism, evaluation framework). Without a disciplined process, decisions made in isolation will create tangled dependencies. The Inquiry step is particularly critical: "Why do we need GraphRAG?" "Why are we choosing an event-driven agent communication model?" must be answered before implementation.
- **Lyra route:** §4.1 (Core Architecture), §4.9 (Harness Engineering)
- **Source:** Chapter 1 (§1.5), Chapter 2 (§2.2-2.7)
- **Concrete application:**
  - Before each major subsystem design, produce a 1-page "Decision Receipt" table: Decision | Rationale | Consequences.
  - Use 5 Whys on every PRD item: "Why do we need a plugin system?" → "To allow extensibility" → "Why extensibility?" → drill until bedrock.
  - The `ARCHITECTURE-DEBATE.md` file should be refactored into individual ADRs per decision.

---

## Practice 2: Architecture Decision Records (ADRs) as Source of Truth

- **What:** Lightweight, structured documents capturing: metadata (date, status, participants), context (problem statement), options considered (with pros/cons), decision, consequences (what tradeoffs accepted), and compliance notes (how to verify this decision is followed).
- **Why:** Lyra currently has rich architectural discussion across `MASTER-PLAN.md`, `findings.md`, `ARCHITECTURE-DEBATE.md`, and various brainstorm files — but no single source of truth for "what did we decide and why." Six months from now, when a new developer asks "Why did we choose GraphRAG over Pinecone?" or "Why is the plugin protocol JSON-based?" there should be a single document to point to.
- **Lyra route:** §4.1 (Core Architecture), §4.9 (Harness Engineering)
- **Source:** Chapter 2 (§2.6-2.7)
- **Concrete application:**
  - Create `docs/lyra-upgrade/adr/` directory.
  - ADR-001: Overall Lyra architecture style (Hexagonal/Layered hybrid).
  - ADR-002: Plugin and tool interface protocol.
  - ADR-003: Memory architecture (hybrid vector + graph + key-value).
  - ADR-004: Model provider abstraction pattern.
  - ADR-005: Evaluation methodology (LLM-as-judge + automated metrics + human review).
  - Each ADR is a single markdown file, 1-3 pages max. Keep them lightweight.

---

## Practice 3: Explicit "-ility" Priorities for Every Subsystem

- **What:** Before building any Lyra subsystem, explicitly declare: (a) which two quality attributes ("-ilities") are non-negotiable, and (b) which one quality attribute you are deliberately sacrificing — with stated consequences.
- **Why:** Lyra, like all complex systems, cannot have everything. The memory subsystem cannot simultaneously optimize for perfect recall (Reliability), sub-10ms retrieval (Performance), and seamless provider swapping (Maintainability). Different subsystems need different priorities. Explicit declaration prevents the "silent drift" where every subsystem tries to be perfect at everything.
- **Lyra route:** §4.2 (Memory/Context), §4.4 (Safety/Reliability), §4.6 (Evaluation/Observability)
- **Source:** Chapter 2 (§2.4)
- **Concrete application:**
  - Plugin System: Prioritize Extensibility and Security; de-prioritize Performance (plugin overhead is acceptable for isolation).
  - Memory Retrieval: Prioritize Performance and Relevance; de-prioritize perfect Consistency (slightly stale context is acceptable).
  - Evaluation Harness: Prioritize Reliability and Repeatability; de-prioritize Speed to Ship (eval quality matters more than eval speed).
  - Agent Loop: Prioritize Safety and Observability; de-prioritize raw Throughput (safety gates per step are non-negotiable).

---

## Practice 4: Hexagonal Architecture for the Agent Core

- **What:** Structure Lyra so the agent's core reasoning loop (the "domain") is at the center of a hexagon. Everything external — model providers, memory stores, tools/plugins, evaluation frameworks, observability backends — connects through ports (interfaces) to swappable adapters (concrete implementations). The core never imports adapter-specific types.
- **Why:** This is how Lyra achieves model-agnostic operation, tool-agnostic execution, and memory-store-agnostic context retrieval. Without the port-adapter separation, switching from OpenAI to Anthropic, or from Pinecone to pgvector, would require changes to core agent logic — creating a fragile, vendor-locked system.
- **Lyra route:** §4.1 (Core Architecture), §4.5 (Tool Use/Plugins)
- **Source:** Chapter 5 (Hexagonal Architecture)
- **Concrete application:**
  - `ILLMProvider` port: `complete(prompt)`, `complete_with_tools(prompt, tools)` — adapters for Anthropic, OpenAI, Ollama, local.
  - `IMemoryStore` port: `store(embedding, metadata)`, `search(query, top_k)`, `get(id)` — adapters for Pinecone, pgvector, Chroma, Qdrant.
  - `IToolExecutor` port: `execute(tool_name, params)` — adapters for HTTP tools, Python subprocess, Docker sandbox, MCP servers.
  - `IEvaluator` port: `evaluate(agent_run, criteria)` — adapters for LLM-as-judge, human review, automated metrics.
  - Enforce at compile/lint time: core package has zero imports from adapter packages.

---

## Practice 5: Resilience Patterns on Every External Call

- **What:** Every call from Lyra to an external system (model inference API, database query, tool execution, memory retrieval) must be wrapped with: a circuit breaker (stop calling after N failures, test recovery periodically), a timeout (fail fast, never hang), retry with exponential backoff and jitter (only for idempotent operations), and a bulkhead (isolated resource pools per dependency).
- **Why:** Lyra is a composition of unreliable external dependencies. Model APIs rate-limit, databases have hiccups, tool executions can hang. Without resilience patterns, a single failing dependency cascades into agent failure, which cascades into task failure, which cascades into user-facing failure. The Agent Hospital concept from the Lyra research corpus is a bulkhead pattern applied to agents.
- **Lyra route:** §4.4 (Safety/Reliability), §4.9 (Harness Engineering)
- **Source:** Chapter 10 (Architecting for Resilience and Scale)
- **Concrete application:**
  - Circuit breaker for model APIs: after 5 consecutive failures, trip circuit; half-open probe every 30s; close after 3 consecutive successes.
  - Retry with backoff: 1s → 2s → 4s → 8s → max 30s, with ±25% jitter.
  - Idempotency keys on all mutation tool calls (writes, API mutations). Read-only tool calls are naturally idempotent.
  - Bulkhead: separate thread/connection pools for OpenAI calls, Anthropic calls, database queries, tool sandbox processes. If the tool sandbox exhausts its pool, model calls are unaffected.
  - Timeout on EVERY external call — no defaults. Model inference: 120s. Database: 5s. Memory retrieval: 2s. Tool execution: 30s (configurable per tool).

---

## Practice 6: Separation of Concerns at Every Scale

- **What:** Ensure each class, module, and subsystem in Lyra has a single, well-defined responsibility. A component that "fetches context AND formats it for the model AND logs the result AND caches the embedding" has too many concerns. Use the "and" test: if describing a component's job requires the word "and," split it.
- **Why:** Lyra's complexity will grow rapidly as subsystems interact. Without strict SoC, fixing a bug in tool selection could break memory retrieval, and adding a new evaluation metric could destabilize the agent loop. Maintainability depends on clean separation.
- **Lyra route:** §4.1 (Core Architecture), §4.3 (Multi-Agent Orchestration)
- **Source:** Chapter 3 (§3.2-3.3), Chapter 4 (§4.4-4.7)
- **Concrete application:**
  - Agent Loop: One module for the reasoning loop (LLM interaction), separate from tool selection, separate from context assembly, separate from response formatting.
  - Memory: Retrieval logic separate from embedding generation, separate from storage, separate from pruning/compaction.
  - Plugins: Tool schema definition separate from tool execution, separate from tool result formatting.
  - Test each concern in isolation — if a test requires spinning up 4 subsystems, those subsystems are too coupled.
  - Apply SRP at method, class, module, and subsystem levels (fractal architecture).

---

## Practice 7: Fitness Functions as Automated Architecture Guards

- **What:** Write automated tests that verify Lyra's architectural invariants. These are not unit tests of business logic — they are tests OF the architecture. Examples: "No import from adapter packages in core," "All tool implementations satisfy the ITool interface," "No circular dependencies between modules."
- **Why:** Architecture diagrams and ADRs are aspirational documents unless enforced. Over time, developer shortcuts erode architectural boundaries — a "quick" direct database call from the agent loop, an "emergency" circular import. Fitness functions catch these violations at build time, before they become entrenched.
- **Lyra route:** §4.9 (Harness Engineering), §4.1 (Core Architecture)
- **Source:** Chapter 2 (§2.7.2), Chapter 4 (§4.3), Chapter 13
- **Concrete application:**
  - Python: `import-linter` to enforce layer dependency rules.
  - TypeScript: ESLint `import/no-restricted-paths` rules.
  - Write fitness functions that fail the build:
    - "Core module must not import from any adapter module."
    - "All files in `plugins/` must export a class implementing `BasePlugin`."
    - "No file may import both `openai` and `anthropic` directly — only through the adapter layer."
    - "Circular imports must be zero."
  - Run fitness functions in CI as a separate job before tests.

---

## Practice 8: The Tradeoff Triangle for Prioritization Debates

- **What:** When the team is stuck debating two architectural options, draw a triangle with three competing priorities at the corners (e.g., Speed to Ship, Cost to Operate, Ease to Change). Place a dot to show where each option lands. The conversation shifts from "I prefer X" to "which tradeoff does the business need right now."
- **Why:** Lyra faces constant priority tension: ship features fast vs. build robust infrastructure; support many model providers vs. optimize for one; maximize safety vs. minimize latency. These are not technical disagreements — they are priority disagreements. The Tradeoff Triangle makes priorities visible and debatable.
- **Lyra route:** §4.1 (Core Architecture), §4.9 (Harness Engineering)
- **Source:** Chapter 2 (§2.8)
- **Concrete application:**
  - Use in sprint planning: "For this sprint, the triangle is: Ship Lyra V1 (top priority), Production Reliability, Developer Experience. Dot near Ship."
  - Use in design reviews: "For the memory subsystem, our triangle is: Retrieval Accuracy, Query Latency, Implementation Complexity. Where does this design land?"
  - Use in architecture debates: Draw the triangle on the whiteboard (or in the ARCHITECTURE-DEBATE.md) for each contested decision.
  - Can formalize further with Weighted Decision Models when the debate is quantitative.

---

## Practice 9: Observability as a First-Class Architectural Concern

- **What:** Lyra must emit structured telemetry (logs, metrics, traces) that answers new questions without deploying new code. Every agent decision — tool chosen, memory retrieved, routing path taken, model called — must be traceable from end to end. Implement the three pillars: Logs (what happened), Metrics (how much/how fast), Traces (the journey).
- **Why:** AI agent systems are non-deterministic. When Lyra makes a wrong decision, you cannot simply re-read the code — you need to reconstruct exactly what the agent saw (context), what it chose (tool/routing), what it received (tool output), and what it produced (response). Without observability, debugging is guesswork.
- **Lyra route:** §4.6 (Evaluation/Observability)
- **Source:** Chapter 14 (Architecting for Quality and Observability)
- **Concrete application:**
  - Distributed tracing via OpenTelemetry: Trace ID propagated across all agent interactions.
  - Structured log format: `{"timestamp": "...", "trace_id": "...", "agent_id": "...", "event": "tool_call", "tool": "search", "latency_ms": 230, "success": true, "tokens_used": 450}`
  - Critical metrics dashboards: agent task completion rate, tool call success rate, model API latency P50/P95/P99, token consumption per task, memory retrieval hit rate, circuit breaker state transitions.
  - Alerting: Alert on task failure rate > 5%, tool execution error rate > 3%, model API timeout rate > 2%, memory retrieval miss rate > 20%.
  - SLIs for Lyra: task completion rate (target >95%), response latency P95 (target <30s for standard tasks), tool call accuracy (target >90% correct tool selected).

---

## Practice 10: Composability over Duplication (the "35-Headed Hydra" Principle)

- **What:** When Lyra needs similar functionality across multiple subsystems (e.g., context formatting for different model providers, tool result normalization for different tool types), build small, reusable, composable components with standardized interfaces rather than copy-pasting logic. Each component should be independently testable and snap-together via interfaces.
- **Why:** The "35-Headed Hydra" case study showed that duplicated logic across 35 industry scorecards turned a 15-minute regulatory change into a multi-day detective exercise. Lyra risks the same fate if similar but slightly different implementations of context assembly, tool calling, or memory retrieval proliferate across subsystems.
- **Lyra route:** §4.3 (Multi-Agent Orchestration), §4.5 (Tool Use/Plugins)
- **Source:** Chapter 3 (§3.6)
- **Concrete application:**
  - Context assembly: One `ContextBuilder` that supports composition of context blocks (system prompt + memory + tool results + conversation history), not N different implementations across agent types.
  - Tool result normalization: One `ToolResultNormalizer` that handles the common case (success/failure/partial) with standardized format, then specialized formatters for tool-specific output.
  - Model request building: One `RequestBuilder` that composes the model-agnostic request, then adapter-specific formatters for provider schemas.
  - The multiplier effect: when you add a new memory source, it plugs into the existing `ContextBuilder` via interface — you write the unique 10%, inherit the stable 90%.

---

## Practice 11: Defensive Input Validation at Every Boundary

- **What:** Every entry point into Lyra — user input, model API response, tool output, plugin return value, memory retrieval result — must be validated before processing. Fail fast with clear error messages. Never trust external data.
- **Why:** AI agent systems compound risk: untrusted user input flows into model context, model output flows into tool execution, tool output flows back into model context. A single unvalidated injection at any boundary can compromise the entire agent. This is not just a security concern — it's a correctness concern (malformed tool outputs corrupting agent reasoning).
- **Lyra route:** §4.4 (Safety/Reliability)
- **Source:** Chapter 11 (Foundational Security Architecture)
- **Concrete application:**
  - User input validation: schema-check all user-provided parameters before they enter agent context. Reject/escape any content attempting prompt injection patterns.
  - Tool output validation: every tool result must conform to its declared schema before being passed to the agent. If a tool returns `{"status": "malformed_json` instead of the expected structure, catch it and surface an error to the agent, not raw garbage.
  - Model response validation: verify model outputs conform to expected formats (tool call schema, structured output schema) before acting on them.
  - Plugin permission enforcement: each plugin declares its required permissions; the harness validates that plugins don't exceed declared permissions at boundary crossing.
  - No hardcoded secrets anywhere in Lyra source, config committed to git, or log output. Use a secret manager or env injection.

---

## Practice 12: Design for Replaceability (the OSI Model Principle)

- **What:** Every component in Lyra should be replaceable without changing anything above or below it. Model providers, memory stores, tool implementations, evaluation frameworks, and observability backends should all be swappable via interface contracts, just as the OSI model allows swapping Physical Layer (copper → fiber) without touching Application Layer.
- **Why:** The AI infrastructure landscape is changing weekly. Today's best model provider may be tomorrow's legacy; today's best vector database may be outpaced by a new entrant. Lyra's architecture should treat this as a given, not a surprise. Replaceability is the architecture's most valuable property.
- **Lyra route:** §4.1 (Core Architecture), §4.5 (Tool Use/Plugins)
- **Source:** Chapter 4 (§4.8 — OSI Model parallel), Chapter 5 (Hexagonal Architecture)
- **Concrete application:**
  - Can you swap Anthropic for OpenAI without changing agent core code? If not, the port-abstraction is leaking.
  - Can you swap Pinecone for pgvector without changing memory retrieval logic? If not, the memory port needs refinement.
  - Can you add a new tool without modifying the agent loop? If not, the tool interface is coupled to the loop.
  - Test replaceability explicitly: write an integration test that swaps a real adapter for a mock and verifies the core produces identical behavior.
  - The ultimate test: can a new team member add support for a new model provider by writing only an adapter class, without touching any other file?

---

## Practice 13: Minimal Blast Radius Through Clear Boundaries

- **What:** Design Lyra so that a failure in any single component (model call timeout, tool execution error, memory store crash) is contained — it cannot cascade into other components or bring down the entire agent. This means: separate process/thread pools per dependency, no shared mutable state between subsystems, explicit error boundaries.
- **Why:** In a multi-agent system, one agent's failure should not cascade into the entire task execution. In a single-agent system, one tool's crash should not abort the entire reasoning loop. The "blast radius" concept from safety engineering applies directly to Lyra's reliability architecture.
- **Lyra route:** §4.4 (Safety/Reliability), §4.3 (Multi-Agent Orchestration)
- **Source:** Chapter 3 (§3.3.1 — Blast Radius definition), Chapter 10 (Bulkhead pattern)
- **Concrete application:**
  - Agent isolation: if running multiple agents, each gets its own sandbox — failure in Agent A does not affect Agent B's execution.
  - Tool isolation: each tool execution runs in its own process or sandbox. A crashing tool cannot crash the agent harness.
  - Memory isolation: retrieval failure falls back to cached context or empty context — never blocks the agent loop.
  - Explicit error boundaries: each subsystem has a well-defined error handling contract. No "silent failures" — every failure is caught, logged with trace ID, and either retried or reported to the agent with clear error context.
  - Blast radius should be observable: when a failure occurs, the trace should show exactly which components were affected and which were unaffected.

---

## Practice 14: CI/CD as Architecture, Not Afterthought

- **What:** Lyra's build pipeline should be designed alongside its runtime architecture. Automated quality gates — linting, type checking, unit tests, integration tests, fitness functions, security scans, eval harness runs — should run on every PR. Deployment strategy (canary, blue-green) is an architectural decision, not an ops task.
- **Why:** Architecture that isn't enforced in CI/CD is just documentation. If Lyra's layered/hexagonal architecture isn't checked automatically, it WILL degrade. The eval harness is particularly critical: every PR that changes agent logic should run evaluation benchmarks before merge.
- **Lyra route:** §4.9 (Harness Engineering), §4.6 (Evaluation/Observability)
- **Source:** Chapter 13 (Architecting for the Delivery Lifecycle)
- **Concrete application:**
  - CI pipeline stages (sequential, fail-fast):
    1. Lint + Format check (<30s)
    2. Type check (<1min)
    3. Fitness functions (architectural constraint checks) (<1min)
    4. Unit tests (80%+ coverage required) (<5min)
    5. Integration tests (model mocks, database testcontainers) (<10min)
    6. Eval harness run (agent performance benchmarks on test suite) (<15min)
    7. Security scan (secret detection, dependency audit) (<2min)
  - Deploy: canary → 10% traffic → monitor for 30min → full rollout. Auto-rollback if error rate exceeds threshold.
  - Feature flags for dark-launching new agent capabilities without exposing to all users.

---

## Practice 15: Language-Agnostic Principles, Language-Specific Enforcement

- **What:** The architectural principles in this playbook (SoC, hexagonal ports, resilience patterns, observability) are language-agnostic — they apply regardless of whether Lyra is built in TypeScript, Python, or a polyglot stack. Use each language's specific idioms to enforce the principles: TypeScript's type system, Python's ABC/protocol interfaces, Rust's trait system.
- **Why:** The book demonstrates that SOLID principles apply identically across C#, Java, Python, and JavaScript — it's the concepts, not the syntax. Lyra should not tie its architecture to a specific language's patterns but should use the best enforcement mechanisms available in its chosen language(s).
- **Lyra route:** §4.1 (Core Architecture), §4.9 (Harness Engineering)
- **Source:** Introduction (§1.6.3), throughout all chapters
- **Concrete application:**
  - TypeScript Lyra: Use TypeScript interfaces (not classes) for ports. Use `satisfies` operator for adapter conformance. Use `never` type for unreachable error states.
  - Python Lyra: Use `Protocol` classes (PEP 544) for ports — structural subtyping. Use `ABC` with `@abstractmethod` for contracts that require runtime enforcement.
  - Regardless of language: the port interface is defined FIRST, the adapter implementation SECOND. Never the reverse.
  - The companion repository pattern from the book (all examples in 4 languages) should inspire Lyra's documentation: key patterns shown across language boundaries where relevant.
