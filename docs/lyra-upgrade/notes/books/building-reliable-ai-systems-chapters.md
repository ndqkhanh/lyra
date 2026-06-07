# Building Reliable AI Systems — Chapter Notes

**Book Title:** Building Reliable AI Systems: Applications and Agents You Can Trust
**Author:** Rush Shahani
**Year:** 2026 (MEAP V12, Manning Publications)
**Core Thesis:** Production AI reliability demands a three-layer engineering framework covering outputs, agents, and operations. Benchmark capability is not the same as production reliability — models that score 85%+ on SWE-bench drop to 58-65% on fresh codebases. Engineering the system around the model (harness, monitoring, observability, safety guardrails) matters more than model selection alone.

---

## Chapter 1: AI Reliability — Building LLMs for the Real World

**Key Insight:** 95% of generative AI pilots fail to deliver measurable ROI (MIT study). The gap between benchmark scores and production behavior — what Shahani calls "the reliability gap" — is the central problem. SWE-bench Verified: 85% resolve rate; SWE-bench Pro (fresh codebases): 58-65%. Reliability means producing accurate outputs, taking safe actions, and maintaining quality over time under real-world conditions.

**Best Practices:**
- Define reliability across three layers: outputs, agents, and operations — never just one.
- Measure the reliability gap explicitly for your domain (benchmark vs. real-world performance).
- Treat model selection as necessary but insufficient; engineering scaffolding delivers reliability.

**Anti-Patterns:**
- Equating benchmark scores with production readiness.
- Deploying LLM functionality without a production monitoring plan.

**Relevance to Lyra Workstreams:** Foundational framing — directly maps to Lyra's concerns about harness engineering, reliability (plan 16), and safety (plan 17). The three-layer framework mirrors Lyra's architecture debates.

---

## Chapter 2: Generating Trustworthy Responses with Prompt Engineering

**Key Insight:** Prompts are production quality contracts, not just instructions. Well-structured prompts with explicit role, tone, format, and constraints dramatically reduce output variability. Prompt versioning and controlled rollouts are essential production practices.

**Best Practices:**
- Version all prompts and track which version produced each response.
- Use structured output formats (JSON schema) when precision matters.
- Start simple, add layers of instruction only after measuring baseline performance.

**Anti-Patterns:**
- Vague prompts that leave too much room for model interpretation.
- Changing prompts in production without A/B testing or shadow deployment.

**Relevance to Lyra Workstreams:** Applies to Lyra's prompt engineering for agent system prompts, router instructions, and command templates. Relevant to plans 03-context and 05-router.

---

## Chapter 3: Grounding Outputs with RAG

**Key Insight:** Retrieval-Augmented Generation anchors LLM outputs in verifiable external knowledge. The quality of retrieval (chunking strategy, embedding model choice, metadata enrichment) directly determines response accuracy. RAG alone is insufficient — it must be combined with source attribution and confidence scoring.

**Best Practices:**
- Chunk by semantic boundaries, not arbitrary character limits.
- Enrich chunks with metadata (source, date, topic) for better retrieval.
- Implement citation mechanisms so users can verify claims.

**Anti-Patterns:**
- Indexing without a chunk-refresh strategy (stale documents produce stale answers).
- Relying solely on vector similarity without re-ranking or metadata filtering.

**Relevance to Lyra Workstreams:** Directly relevant to Lyra's 03-context plan and knowledge retrieval in the agent architecture. Source attribution aligns with Lyra's source-ledger.md approach.

---

## Chapter 4: Embeddings and Vector Search

**Key Insight:** Embedding quality and vector search configuration are the silent determinants of RAG performance. Different embedding models serve different use cases. Dense retrieval works well for semantic similarity but can miss exact matches; hybrid search (dense + sparse/BM25) is more robust.

**Best Practices:**
- Evaluate embeddings on your specific domain data, not just public benchmarks.
- Implement hybrid search (dense vectors + keyword/BM25) for production reliability.
- Monitor embedding drift when switching models or updating data.

**Anti-Patterns:**
- Assuming one embedding model works for all tasks.
- Neglecting to re-index when embedding models are updated.

**Relevance to Lyra Workstreams:** Relevant to plans 02-memory, 03-context, and 15-research for knowledge retrieval infrastructure.

---

## Chapter 5: Fine-Tuning LLMs for Improved Performance

**Key Insight:** Fine-tuning is powerful but introduces subtle risks: catastrophic forgetting, bias amplification from training data, and concept drift. LoRA (Low-Rank Adaptation) provides a practical middle ground — parameter-efficient, faster to train, and easier to version. Fine-tuning works best when you have a well-defined, narrow domain with consistent patterns.

**Best Practices:**
- Use LoRA for domain adaptation to reduce cost and preserve base model capabilities.
- Audit fine-tuning data for bias before training (see Chapter 11 techniques).
- Maintain a held-out evaluation set to detect regressions after each fine-tuning run.

**Anti-Patterns:**
- Fine-tuning on unclean, un-audited user interaction logs.
- Assuming fine-tuning fixes fundamental architecture or data quality problems.

**Relevance to Lyra Workstreams:** Relevant to plans 15-research (specialized models) and 17-safety (bias auditing of training data). LoRA approach applicable if Lyra ever fine-tunes router or specialized agents.

---

## Chapter 6: Creating Effective AI Agents

**Key Insight:** Standalone LLMs have three fatal limitations: static knowledge, inability to act, and no workflow management. Agents solve all three by adding memory, tool integration, and decision-making frameworks. The ReAct (Reasoning + Acting) framework is the foundation: reason → act → observe → repeat. Agentic RAG combines retrieval with action capabilities. Production case studies (JPMorgan 450+ AI use cases, Mass General Brigham 21% burnout reduction) validate the pattern.

**Best Practices:**
- Build agents with three core components: memory (short-term + persistent), tool integration, and decision-making frameworks.
- Use ReAct for iterative reasoning; consider Tree-of-Thought for high-uncertainty multi-path problems.
- Implement transparent decision-making — show users which tools the agent selected and why.
- Cross-reference outputs from multiple independent tools for critical decisions.
- Separate the harness (control plane: agent loop, approvals, tracing, state) from the sandbox (compute plane: file I/O, shell, code execution).

**Anti-Patterns:**
- Building monolithic agents that try to do everything (mediocre at everything).
- Neglecting fallback logic for tool failures.
- Hiding agent reasoning from users (erodes trust).
- Relying on keyword-based guardrails for safety (use LLM-as-judge or structured classifiers).

**Relevance to Lyra Workstreams:** Foundational chapter for Lyra's entire agent architecture. Directly relevant to plans 02-memory, 05-router, 07-plugins, 09-commands, 16-reliability, and 17-safety. The ReAct pattern maps to Lyra's agent loop.

---

## Chapter 7: Tool Integration and MCP

**Key Insight:** The N×M integration problem (N apps × M APIs = N×M custom integrations) is the central bottleneck in AI agent development. The Model Context Protocol (MCP) solves this by standardizing how LLMs discover and use tools — "USB for AI." MCP servers expose tools via a standardized `/tools/list` endpoint; models auto-discover available tools and their schemas. The harness/sandbox architectural pattern (OpenClaw, OpenAI Codex CLI, NVIDIA NemoClaw) separates the control plane from the compute plane. AGENTS.md files work best as a table of contents (~100 lines) with pointers to deeper docs.

**Best Practices:**
- Design tool descriptions as interfaces for intelligent agents — clear names, self-documenting parameters.
- Every tool response should follow a consistent structure: `{success, error, message, results}`.
- Distinguish empty results (`success: true, results: []`) from errors (`success: false`).
- Implement timeouts with exponential backoff retry (3 attempts, 1s/2s/4s delays).
- Give agents a "map, not an encyclopedia" — use AGENTS.md as a TOC with pointers to structured docs.
- Enforce invariants mechanically (linters, structural tests) rather than through documentation.
- Design tools assuming prompt injection and data exfiltration attempts.

**Anti-Patterns:**
- Monolithic instruction files that crowd out task context and rot faster than maintained.
- Returning Python stack traces to the LLM instead of structured error responses.
- Setting `require_approval: "never"` on tools that modify data or make purchases.

**Relevance to Lyra Workstreams:** Critical chapter for plans 07-plugins and 05-router. The harness/sandbox separation is directly relevant to Lyra's harness engineering architecture debate. AGENTS.md conventions inform source-ledger.md design. MCP patterns map to Lyra's tool/plugin system.

---

## Chapter 8: Multi-Agent Systems

**Key Insight:** Monolithic agents are mediocre at everything. Specialized agents (search, policy, vision), coordinated by an orchestrator with shared state, outperform single-agent architectures. LangGraph provides the framework: State (shared TypedDict), Nodes (agents), Edges (connections), Conditional Edges (dynamic routing). Selective model assignment (mini for routing, full for synthesis) dramatically improves cost-quality ratio. Testing must cover blended queries, ambiguous intent, agent failure resilience, state flow preservation, and regression.

**Best Practices:**
- Specialize agents by domain (search, Q&A, vision) rather than building monoliths.
- Use a lighter/cheaper model for intent classification and routing; reserve full models for synthesis.
- Test workflows, not just individual agents — bugs occur at the seams.
- Implement graceful degradation when individual agents fail (other agents continue functioning).
- Verify state flow preservation: critical user details must survive the complete workflow.
- Ensure no state contamination between separate workflows.

**Anti-Patterns:**
- Testing only individual agents without end-to-end workflow validation.
- Letting agents share state without a clear TypedDict schema.
- Ignoring agent failure scenarios in testing.

**Relevance to Lyra Workstreams:** Foundational chapter for plans 05-router, 07-plugins, 09-commands, and 16-reliability. The LangGraph orchestration pattern directly maps to Lyra's multi-agent routing architecture. The 5-category testing framework is directly applicable to Lyra's verification infrastructure.

---

## Chapter 9: Evaluation and Performance for LLMs and Agents

**Key Insight:** Evaluation must cover both outputs (correctness) and process (trajectory). Four-step hallucination measurement: (1) identify grounding data, (2) create generic + adversarial test sets, (3) extract claims and validate, (4) report metrics (GDR, HSS). FActScore breaks responses into atomic facts for granular scoring. Four performance patterns: token streaming, batching (system-level + OpenAI Batch API), semantic caching (FAISS or GPTCache with 0.7-0.8 similarity threshold), and multi-model fallback routing.

**Best Practices:**
- Create both generic and adversarial test sets — adversarial exposes edge cases generic misses.
- Use Grounding Defect Rate (GDR) for system-level tracking; FActScore for response-level granularity.
- Combine LLM-as-judge with human calibration to mitigate judge bias.
- Set semantic caching similarity threshold at 0.7-0.8; implement cache invalidation by versioning.
- Route simple queries to cheaper models (keyword-based or function-calling-based routing).
- Evaluate agent trajectories — not just whether the answer was correct, but whether the right tools were called in the right order.
- Conduct regular red teaming as a continuous feedback loop, not a one-time exercise.

**Anti-Patterns:**
- Treating "no results" as errors (they're different: empty results = `success: true, results: []`).
- Using ROUGE as the sole evaluation metric for LLM outputs.
- Relying on exact-match caching alone (users rephrase questions in countless ways).
- Over-relying on a single judge model without majority voting or human calibration.

**Relevance to Lyra Workstreams:** Directly relevant to plans 16-reliability, 17-safety, and 15-research. Evaluation methodology informs Lyra's verification infrastructure. Performance patterns (caching, fallback routing) apply to Lyra's production deployment.

---

## Chapter 10: Deploying and Monitoring

**Key Insight:** LLM failures are non-deterministic — the same input can succeed 99 times and fail on the 100th. Traditional monitoring (uptime, latency, HTTP errors) misses LLM-specific failures (wrong but confident answers). LLM-native monitoring must answer four questions: (1) speed/availability, (2) answer quality, (3) user satisfaction, (4) cost sustainability. The five-layer LLMOps architecture: input processing → model execution → output processing → monitoring/observability → continuous improvement.

**Best Practices:**
- Monitor tokens-per-second (not just latency) to catch real performance degradation.
- Alert on cost-per-token efficiency degradation and cost trend slopes, not just absolute costs.
- Implement three-layer output quality defense: automated content filters, statistical monitoring, LLM-as-judge evaluation.
- Track both explicit feedback (ratings) and implicit signals (session abandonment, rephrasing, escalation rates).
- Maintain golden test datasets that run automatically on schedule to catch quality drift.
- Use shadow testing before deploying new models or prompts (budget for 2× model costs during test windows).
- Version prompts and treat them as production artifacts with rollout/revert capabilities.
- Implement a feedback triage process (weekly 30-min meeting categorizing negative feedback into actionable buckets).

**Anti-Patterns:**
- Alerting on raw latency thresholds without context (tokens-per-second is more informative).
- Forcing user feedback through modal dialogs (creates negative UX and biased data).
- Deploying model updates without shadow testing against production traffic.
- Treating monitoring as purely technical (connect technical metrics to business outcomes: cost per satisfied customer, resolution rate without escalation).

**Relevance to Lyra Workstreams:** Directly relevant to plans 16-reliability, 17-safety, and the verification infrastructure. The LLMOps monitoring patterns inform Lyra's observability strategy. Langfuse case study is directly applicable. Cost monitoring patterns apply to Lyra's operations.

---

## Chapter 11: Bias, Privacy, and Responsible AI

**Key Insight:** AI amplifies patterns in training data at unprecedented scale. Four fundamental failure modes: unfair treatment (bias), harmful content (safety), privacy violations (data protection), and opaque failures (accountability). The four-layer defense architecture: data layer (balanced sampling, counterfactual augmentation, bias-aware filtering), model layer (fairness-constrained loss during fine-tuning, Constitutional AI), safety layer (keyword → ML classifier → moderation API), and privacy layer (sensitive data detection, HIPAA de-identification, GDPR compliance).

**Best Practices:**
- Audit training/fine-tuning data for bias BEFORE training — use ChatLogBiasDetector-style analysis.
- Use fairness-constrained loss functions during fine-tuning (demographic gap penalty in cross-entropy loss).
- Implement defense-in-depth safety: keyword filter (fast) → ML classifier (contextual) → moderation API (comprehensive).
- Detect and sanitize PII at system boundaries before it enters LLM context.
- Structure HIPAA/GDPR compliance as configurable layers rather than hardcoded rules.
- Design privacy protection proactively (sanitization) rather than reactively (post-hoc filtering).

**Anti-Patterns:**
- Fine-tuning on raw user interaction logs without bias auditing.
- Relying on a single safety layer (keyword matching alone is brittle and easily bypassed).
- Name-based demographic inference with small, stereotype-prone name lists for bias detection.
- Assuming base model safety alignment eliminates the need for runtime safety layers.
- Treating responsible AI as a post-deployment checkbox rather than a layered architectural concern.

**Relevance to Lyra Workstreams:** Directly relevant to plans 17-safety and 16-reliability. The four-layer defense architecture maps to Lyra's safety guardrails. Responsible AI patterns apply to any Lyra deployment handling user data.
