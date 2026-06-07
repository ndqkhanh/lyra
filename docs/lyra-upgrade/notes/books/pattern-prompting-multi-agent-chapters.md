# Building Complex Multi-Agent Systems Using Pattern Prompting — Chapter Notes

**Author:** Tim O'Brien (former Google engineer, 22+ years enterprise systems)
**Year:** 2026 (Packt Publishing)
**Core Thesis:** Production-ready agentic AI systems should be built using established GoF and Enterprise Integration Patterns (EIP) as the explicit design vocabulary, with message-broker infrastructure (RabbitMQ) as the communication substrate. "Agentic patterns" (ReAct, RAG, Plan-and-Execute) are NOT software design patterns — they are workflow shapes that must be implemented using real software patterns. LLMs are best understood as "badly behaving RESTful endpoints" whose integration challenges have been solved by decades of enterprise software engineering.

**Target Audience:** Software engineers with enterprise experience who want to build production-grade GenAI applications without buying into tool-specific hype. Language-agnostic approach; examples use Python, TypeScript, Java, and RabbitMQ.

---

## Chapter 1: Introduction — Patterns, Abstractions, and the GenAI Landscape

- **Key insight:** GenAI applications have far more in common with traditional enterprise software than industry hype suggests. Every term in GenAI has an equivalent in traditional IT (e.g., "agent" ≈ "service/microservice", "agentic pattern" ≈ "component collaboration architecture", "tool use" ≈ "API callout"). The author deliberately uses "microarchitecture" instead of "agentic pattern" to preserve the rigor of what "pattern" means in software engineering.
- **Best practices:**
  - Take a fundamentals-first approach — learn patterns, not specific tools. "Picking tools is like betting in a horse race."
  - Leverage what you already know — patterns make the unfamiliar familiar.
  - Do not lose sight of the forest for the trees — use abstractions to filter out rapidly-changing low-level details.
  - Harmonize GenAI with existing IT architecture by using shared vocabulary.
- **Anti-patterns:** Learning GenAI by learning a specific tool or product; treating LLM endpoints as fundamentally different from any other unreliable web service.
- **Two mental models for LLMs:**
  1. LLM as a continuation of big data — next-generation text processing that delivers value big data promised.
  2. LLM as a badly behaving RESTful endpoint — non-deterministic, high-latency, unreliable, insecure. The fact that it happens to be an LLM is often irrelevant to the engineering challenges.
- **Relevant to Lyra §4.x:** Foundation for Lyra's architectural philosophy — the book's framing of agentic AI as component-based architecture aligns directly with Lyra's multi-agent design.

---

## Chapter 2: Embeddings — The Language of AI

- **Key insight:** Embeddings are the "common thread" running through prompts, vector databases, and LLMs simultaneously. Understanding affinity (co-occurrence frequency) and cosine similarity is essential for building effective retrieval.
- **Best practices:**
  - Select embedding models based on: max tokens, memory requirements, dimensions, cost, training domain, zero-shot capability, language support, compatibility with vector DB.
  - Chunk size and overlap are the most critical tuning parameters — the optimal combination returns the minimum data needed for the LLM to produce the optimal response.
  - Test embeddings programmatically during development using sentence-transformers and cosine similarity to build intuition.
  - Use 50% overlap for dense, interconnected documents; less/none for well-separated topic documents.
- **Anti-patterns:** Blindly using default chunk sizes; neglecting overlap entirely (loses contextual continuity); loading entire documents as single chunks for large files.
- **Numbers:** Cosine similarity is the most widely used similarity function. Chunk size typically measured in tokens (~3-4 chars per token).
- **Relevant to Lyra §4.x:** Direct applicability to Lyra's RAG subsystem, vector database design, and document ingestion pipeline (§4.2, §4.3).

---

## Chapter 3: Building with GenAI — Parameters, Tuning, and Project Phases

- **Key insight:** GenAI projects have 15+ interdependent parameters creating circular dependencies. The dependency graph has five key chains: (1) Document→Chunking, (2) Chunking→Retrieval, (3) Retrieval↔Prompting, (4) Model→Context/Tokens→Prompts, (5) Temperature→Prompt behavior. Understanding these dependencies reduces tuning time by "several orders of magnitude."
- **Best practices:**
  - Maintain tight environment control — no simultaneous modifications by multiple team members.
  - Keep all tests version-controlled.
  - Parallelize parameter testing across multiple environments.
  - Document system goals before tuning (customer profiles, focus groups).
  - Build at least 120 ground-truth query/answer pairs before serious tuning.
  - Three project phases: (1) Project Initiation, (2) Intermediate Goals, (3) Crossing the Finish Line.
- **Temperature guidelines per component role:**
  - Decision-making/routing components: low temperature (deterministic).
  - Summarization: moderate temperature.
  - Creative generation: higher temperature.
- **Anti-patterns:** Testing parameters sequentially when parallelization is possible; neglecting the dependency graph (changing one parameter without re-tuning dependents).
- **Relevant to Lyra §4.x:** Parameter tuning framework applies directly to Lyra's configurable subsystems — embedding selection, chunking strategy, temperature per agent role (§4.5).

---

## Chapter 4: Building Your First RAG App

- **Key insight:** "Production-grade" means the application satisfies 10 explicit requirements: easy to describe, easy to deploy, easy to monitor, supports scalability trade-offs, adaptable, integrates with back-office systems, security-compatible, trusted/proven technology, easy to modify, large community support. RabbitMQ satisfies all ten as the messaging layer.
- **Best practices:**
  - Use message queues (RabbitMQ) to decouple LLM calls from request handling — enables retry, parallel execution, backpressure management.
  - Apply GoF patterns directly: Template Method for consumer pipelines, Adapter for LLM API abstraction, Strategy for model/provider selection.
  - Manual ACK only — never auto-ACK for agent task queues. At-least-once delivery semantics with idempotent consumers.
- **Anti-patterns:** Direct synchronous HTTP calls to LLM APIs inside message processing code; auto-ACK removing messages before processing completes.
- **Design rationale:** Queues solve the fundamental problems of LLM endpoints (latency, unreliability, rate limiting) by providing buffering, retry, and backpressure — all problems EIP was designed for.
- **Relevant to Lyra §4.x:** Core multi-agent communication architecture — Lyra's agent-to-agent message passing can adopt this queue-based model (§4.1, §4.4).

---

## Chapter 5: Starting Your Data Migration Project

- **Key insight:** Data pipeline engineering for GenAI is "more of a systems-engineering exercise, combining reliability, security, cost optimization, and a solid understanding of vector embedding models." The correct capacity metric is not gigabytes but embeddings per second (EPS).
- **Best practices:**
  - Design pipeline in three concurrent stages: Extraction, Embedding, Loading — each independently scalable.
  - Use incremental sync (cursor field or content hash) rather than full reloads for document updates.
  - Implement Change Data Capture (CDC) for near-real-time synchronization.
  - Classification levels for documents before ingestion: public, internal, restricted, confidential.
  - Field-level masking, encryption at rest (AES-256) and in transit (TLS).
  - Target 50-200 EPS for enterprise pipelines; at 100 EPS, 2M embeddings takes ~5.5 hours.
  - Maintain test suite of (question → expected answer) pairs; baseline precision@5 > 0.8.
  - Integrate evaluation into CI/CD — treat data ingestion as a deployment event with quality gates.
- **Advanced techniques covered:**
  - Taxonomy discovery via k-means/hierarchical clustering on embeddings.
  - Hybrid search (vector + BM25/lexical) — "often produces the best retrieval quality."
  - Graph databases (GraphRAG) for explicit entity relationships and explainability.
  - Data cleaning: remove headers/footers/page numbers, deduplicate via hashing, standardize terminology.
- **Anti-patterns:** Throttling too aggressively (leaving GPUs idle); using gigabytes instead of EPS for capacity planning; neglecting continuous validation (sample 1% of embeddings, recompute similarities).
- **Relevant to Lyra §4.x:** Data ingestion architecture (§4.3), hybrid search strategy (§4.2), knowledge graph integration (§4.7).

---

## Chapter 7: Tips and Best Practices

- **Key insight:** This is the most content-dense chapter — covers the operational, security, cost, governance, and evaluation disciplines needed for production GenAI. The organizing principle: GenAI projects are not fundamentally new; they require the same engineering discipline as any other software project, plus awareness of LLM-specific threat vectors.
- **Best practices (design & operations):**
  - Have an R&D mindset — expect things to break. Precede serious development with small pilots.
  - Don't shoehorn requirements into canned "agentic patterns" — analyze and discover your own.
  - Decompose into four atomic actions: Decision making, Summarization, Information gathering, Generation of output.
  - Keep all POCs under 2 days. Break tasks into POC + Implementation phases.
  - Set latency and throughput targets early; load test frequently.
  - Have an explicit plan for managing drift (document updates, model version changes).
  - NEVER use LLM-generated data as input to deterministic IT systems.
  - Validate UX with extensive usability testing — text-based input is poor outside chat, voice is distracting, people don't read large text blocks.

- **Security best practices (detailed):**
  - **Prompt injection:** Use XML-style delimiters (`<user_input>…</user_input>`) to separate untrusted content from system instructions. Validate/sanitize all user input. Use a dedicated LLM guard call to screen for adversarial input. Apply least privilege to agent components. Log and monitor for injection patterns.
  - **Indirect prompt injection:** More dangerous variant — attacks embedded in retrieved data. Documents ingested into vector DB can contain malicious instructions.
  - **Context window leakage:** Design system prompts so that even if fully disclosed, no harm occurs. "Treat your system prompt as semi-public, not secret." Implement document-level access controls on vector DB.
  - **PII handling:** Establish 3-tier data classification: safe-for-external-LLM, must-be-anonymized, must-never-leave-org. Implement "PII shielding" — pre-process anonymization + post-process re-substitution.
  - **Output validation:** Build output validation layer that screens for policy violations, profanity, harmful content. For high-stakes apps, human-in-the-loop review above risk threshold. Confidence scoring via secondary LLM call.
  - **Compliance by industry:** HIPAA requires BAA + no training on PHI; financial services require explainability for automated decisions.
  - **Security-first culture:** Threat modeling session at project start with all disciplines. Security as standing agenda item in sprint reviews. Dedicated security review before every production deployment.

- **Cost management best practices:**
  - Instrument every LLM call from day 1: log input/output token counts tagged by component.
  - Build cost model early and revisit after every prompt change, feature addition, traffic increase.
  - Trim retrieved context aggressively (top 3-5 chunks).
  - Compress conversation history after N turns (summarize earlier exchanges) — reduces history tokens 60-80%.
  - Audit system prompts regularly for redundant instructions.
  - Set explicit max_tokens limits per component.
  - Use semantic caching for repeated/near-identical queries.
  - Implement tiered model strategy: small/cheap model for routing/classification, large model only for synthesis. Can reduce spend 40-70%.
  - Set daily spend alert at 150% expected, hard cap at 200%.
  - Require approval for any change projected to increase monthly spend >10%.

- **Prompt governance:**
  - Treat prompts as code — store in version control with meaningful commit messages.
  - Semantic versioning (v1.0.0, v1.1.0, v2.0.0).
  - PR review process for prompt changes with evaluation dataset validation.
  - Independent prompt rollback (without code redeploy).
  - Designated prompt owner per prompt.

- **Evaluation and testing:**
  - Build curated evaluation dataset: 50-100 test cases before first release, expand to hundreds.
  - Automated evaluation pipeline in CI/CD with multiple scoring strategies: exact match, semantic similarity, LLM-as-judge.
  - Run each test case 5-10 times; report pass rate across runs (not binary pass/fail).
  - Red-teaming: assign team members adversarial role, document every failure mode, add to eval dataset.
  - Test for drift after EVERY vector database change (treat data ingestion as deployment event).
  - Quality threshold: no more than 2% decline in eval dataset pass rate allowed per change.

- **Relevant to Lyra §4.x:** This chapter maps to Lyra's safety (§4.7), reliability (§4.8), observability (§4.9), cost management, and evaluation (§4.6) workstreams. The four-action decomposition (Decide, Summarize, Gather, Output) directly maps to Lyra's agent role taxonomy.

---

## Chapter 8: Pattern-Guided Coding — Using Patterns as the Design Vocabulary for GenAI Systems Built on RabbitMQ

- **Key insight:** This is the architectural core of the book. Pattern-guided coding is a discipline where every significant design decision is mapped to named GoF/EIP patterns BEFORE code is written. The term "agentic pattern" (ReAct, RAG, etc.) describes a workflow shape, NOT a software design pattern. Real patterns have canonical participants, collaborations, responsibilities, failure modes, and deployment structures. The book introduces Topologos, a Claude skill that implements this as a four-phase protocol.

- **The four-phase Topologos process:**
  1. **Clarification before design:** Five mandatory constraints — problem scope, scale/reliability requirements, existing infrastructure, security posture, failure tolerance model.
  2. **Pattern analysis across four lenses:** (A) Agentic pattern decomposition into message flows, (B) GoF pattern mapping for each interaction, (C) Security threat model per message flow, (D) Failure mode analysis per queue (transient/permanent/poison/expired/rejected).
  3. **Iterative approval — one decision at a time:** Chain of Responsibility pattern applied to design review. Nine canonical decisions in order: exchange topology, queue naming/durability, routing key schema, DLQ topology, security model, correlation strategy, consumer concurrency model, persistence, acknowledgment policy.
  4. **Final topology output:** Topology diagram, JSON manifest (for Terraform/Management API), pattern reference card, security manifest, DLQ diagram, operational notes.

- **GenAI workflow → GoF/EIP pattern mapping table (Table 8.1):**
  | Workflow | GoF Patterns | EIP Patterns |
  |---|---|---|
  | ReAct | Command, Mediator | Process Manager, Correlation Identifier, Return Address |
  | Plan-and-Execute | Template Method, Iterator | Routing Slip, Scatter-Gather, Aggregator |
  | Reflection/Critic | Chain of Responsibility, Decorator | Message Filter, Process Manager, DLQ |
  | Tool Use | Command, Facade, Strategy | Competing Consumers, Return Address, DLQ |
  | Multi-Agent Collaboration | Mediator, Observer | Publish-Subscribe Channel, Message Filter, Scatter-Gather |
  | RAG | Decorator, Proxy | Claim Check, Content Enricher, Correlation Identifier |
  | Orchestrator-Subagent | Mediator, Facade, Command | Scatter-Gather, Process Manager, Aggregator, Routing Slip |
  | Human-in-the-Loop | Chain of Responsibility, State | Process Manager, DLQ, Selective Consumer |

- **The three-tier Dead Letter Queue strategy (Table 8.2):**
  | Failure Class | Examples | DLQ Tier | EIP Pattern |
  |---|---|---|---|
  | Transient | Tool timeout, network blip | Tier 1 (30s retry) | DLQ, Retry |
  | Transient (persistent) | Repeated timeout, rate limit | Tier 2 (5 min retry) | DLQ, Circuit Breaker |
  | Permanent | Schema violation, unsupported type | Quarantine (no retry) | DLQ, Message Filter |
  | Poison | Malformed payload, crash loop | Quarantine + alert | DLQ, Message Filter |
  | Expired | SLA breach, stale result | Expiry handler | DLQ, Process Manager |
  | Rejected | Critic rejects, human rejects | Rejection handler | DLQ, Message Filter |

- **Consumer patterns:**
  - Strategy pattern for producer routing — injectable routing logic.
  - Command pattern for agent task messages — self-contained, replayable, auditable messages with correlation_id, timestamp, agent_id.
  - Template Method for consumer pipelines — fixed sequence (validate, deserialize, enrich, process, acknowledge) with overridable steps.
  - Channel Adapter for external integration — wraps synchronous HTTP LLM calls behind async message interface.
  - Manual ACK rule is non-negotiable for agent task queues.

- **Case study — Extending single-LLM RAG to dual-LLM Scatter-Gather:**
  - Changes localized to 5 new components (scatter exchange, Claude queue, gather exchange, aggregate queue, Aggregator agent).
  - Aggregator correlation window: in-memory map keyed by correlation_id with TTL timer; merge strategy (Best-of, Ensemble, Fallback) injected via GoF Strategy.
  - Without pattern-guided coding, the same change would be a Promise.all() callback — invisible design problems (no failure isolation, no independent retry, no DLQ for partial results, no independent scaling, no swappable merge logic).

- **Topologos commands demonstrated:**
  ```
  /pattern react + tool-use with critic-gate, circuit-breaker high-throughput regulated multi-tenant retry-5
  ```
  Produces a complete topology spec, security manifest, DLQ topology, and operational notes from a single command.

- **Relevant to Lyra §4.x:** This is the single most relevant chapter for Lyra. The pattern-guided coding methodology, Topologos workflow, GoF/EIP mapping table, three-tier DLQ strategy, and the case study all map directly to Lyra's multi-agent architecture (§4.1), message routing (§4.4), reliability/error handling (§4.8), and harness engineering (§4.9).

---

## Chapter 9: Implementing the ReAct Pattern Over RabbitMQ

- **Key insight:** Complete, runnable implementation of the ReAct pattern as a distributed system over RabbitMQ. The agent runs a Thought → Action → Observation loop, with tool dispatch and result collection handled entirely through message queues. Full source code provided (Python 3.11+, pika, Anthropic SDK).

- **Architecture:**
  - Dedicated /react vhost for isolation.
  - Topic exchanges: commands, tool dispatch, tool results.
  - Three-tier DLQ: retry1 (30s TTL), retry2 (5 min TTL), quarantine (no TTL, manual replay only).
  - Separate user accounts (react.agent, react.operator) with minimum-privilege permissions.

- **Key implementation details:**
  - correlation_id is the thread through the entire reasoning chain — set once on command receipt, preserved through every ToolRequest and ToolResult.
  - Agent polls results queue with basic_get + correlation_id filter; non-matching messages are NACKed with requeue=True.
  - 30-second timeout for tool results; triggers transient failure → Tier 1 retry.
  - MAX_STEPS=10 as safety limit.

- **Failure classification (Table 9.2):**
  | Exception | Failure Type | DLQ Path |
  |---|---|---|
  | JSONDecodeError, ValueError, KeyError | Poison | → retry1 → retry2 → quarantine |
  | TimeoutError | Transient | → retry1 (30s) → retry2 (5m) → quarantine |
  | RuntimeError (step limit) | Permanent | → retry1 → retry2 → quarantine |
  | Unexpected Exception | Unknown | → retry1 → retry2 → quarantine |

  All cases use NACK with requeue=False — the DLX configuration on the queue determines routing.

- **Tool workers:** Simple consumers reading ToolRequest, executing function, publishing ToolResult. Search, calculator, weather implemented as keyword-matched responses (production would use real APIs). Competing Consumers pattern for horizontal scaling — multiple worker instances per tool type.

- **System prompt design:** Explicit JSON-only output format. Two possible forms: action step (thought + tool/input) or final answer (thought + final_answer). Model explicitly instructed not to guess tool results.

- **Best practices embedded in code:**
  - Manual acknowledgment only (auto_ack=False).
  - Persistent messages (delivery_mode=2).
  - Prefetch count of 1 (one command at a time per consumer).
  - Consumer tag includes unique ID for traceability.
  - Reconnection loop with exponential backoff on broker disconnect.

- **Relevant to Lyra §4.x:** Concrete reference implementation for Lyra's agent loop (§4.1), tool dispatch mechanism (§4.4), failure handling (§4.8), and the dead-letter strategy that Lyra's harness should adopt.

---

## Chapter 10: The Future and Limitations of LLMs

- **Key insight:** An honest engineering assessment of what LLMs can and cannot do. Critical for setting realistic expectations and avoiding architecture built on false assumptions about LLM capabilities.

- **What LLMs cannot reliably do:**
  - Systematic mathematical reasoning
  - Maintain logical consistency over long contexts
  - Provide calibrated confidence in responses
  - Produce genuinely novel insights (as opposed to recombination)
  - Solve the symbol grounding problem

- **What LLMs are genuinely good at:**
  - Text generation, summarization, translation
  - Pattern matching and completion
  - Recombination of known information
  - Following instructions within their training distribution

- **Key theoretical frameworks referenced:**
  - Stochastic Parrot (Bender et al.) — fluency without understanding.
  - Chomsky's limits of statistical learning.
  - Searle's Chinese Room — syntax is not semantics.
  - Penrose/Gödel — mathematical limits of computation.

- **Practical guidance for working with limitations:**
  - Never trust LLM output for critical decisions without human review.
  - Design systems that treat LLM output as a hypothesis to be verified, not a conclusion.
  - Build evaluation pipelines that measure factual accuracy, not just fluency.
  - Use multiple LLMs in ensemble for high-stakes outputs (dual-LLM Scatter-Gather pattern from Ch. 8).

- **Relevant to Lyra §4.x:** Foundation for Lyra's safety architecture (§4.7), critic/evaluator agents, and the ensemble/verification patterns needed for reliable output.

---

## Appendix A: Pattern Reference

- Comprehensive catalog of 19 patterns across four categories:
  - **GoF (3):** Strategy, Adapter, Template Method
  - **EIP (11):** Message Channel, Channel Adapter, Publish-Subscribe Channel, Content Enricher, Request-Reply, Correlation Identifier, Scatter-Gather, Dead Letter Channel, Message History, Content-Based Router, Pipes and Filters
  - **Reliability (2):** Circuit Breaker, Retry with Exponential Backoff
  - **Microarchitecture (2):** Orchestration, Choreography
  - Plus one GenAI microarchitecture: RAG Microarchitecture
- Each entry includes: pattern name, category, chapters where used, and cross-references.
