# Architecting Generative AI Applications — Best-Practices Playbook

**Source:** *Architecting Generative AI Applications* by Leonid Kuligin (2024)
**Extracted:** 12 practices for Lyra architecture

---

## Practice 1: Treat Prompts as Versioned Code

**What:** Every prompt template must be stored in version control with semantic versioning, structured input/output schemas, and automated regression tests. Prompts are not strings — they are configuration-as-code with the same rigor as application code.

**Why:** Ad-hoc prompts scattered across the codebase are untestable, unreviewable, and impossible to roll back. A prompt change can silently degrade quality across the entire system.

**How:**
- Store prompts in a dedicated directory (e.g., `prompts/`) with YAML or JSON schema definitions
- Tag each prompt with version, expected input schema, expected output schema
- Run prompt regression tests in CI — known inputs should produce expected outputs
- Use semantic versioning: MAJOR for output format changes, MINOR for instruction changes, PATCH for wording

**Lyra Application:** Centralize all Lyra prompts (orchestrator, sub-agents, verifier) in `prompts/` with schemas and regression tests in CI.

---

## Practice 2: Implement Multi-Layer Guardrails (Defense in Depth)

**What:** Safety cannot be achieved with a single check. Implement guardrails at three layers: input (before LLM), output (after LLM), and runtime (during tool execution). Each layer catches what others miss.

**Why:** LLMs are vulnerable to prompt injection, hallucination, and unsafe tool use. The primary LLM cannot reliably police itself — dedicated safety mechanisms are required.

**How:**
- **Input layer:** Prompt injection detection, content policy filter, input schema validation
- **Output layer:** Factual consistency check against retrieved context, format validation, toxicity screening
- **Runtime layer:** Tool parameter validation, execution sandboxing, allow/deny lists for operations
- Use a smaller/cheaper model or rule-based system for guardrails
- Implement graduated responses: warn → flag → escalate → block

**Lyra Application:** Lyra's safety workstream (17-safety) should implement all three layers. The verifier agent serves as the output guardrail.

---

## Practice 3: Design Memory as a Three-Tier System

**What:** Agent memory is not a monolithic log. Design three distinct tiers: working memory (active context window), episodic memory (past interactions, externally stored), and semantic memory (facts/knowledge, retrieved as needed).

**Why:** The context window is the scarcest resource in any agent system. Without structured memory management, systems either overflow the context or operate with amnesia.

**How:**
- **Working memory:** Active conversation + relevant retrieved facts. Budget the context window portions.
- **Episodic memory:** Store past conversations externally with embeddings. Retrieve relevant episodes when contextually useful.
- **Semantic memory:** Facts, preferences, knowledge — stored and retrieved via hybrid search (dense + sparse). Support CRUD operations.
- Implement context summarization when approaching limits — keep last N turns raw, summarize older
- Support memory expiration for time-sensitive information

**Lyra Application:** Lyra's memory workstream (02-memory) should implement this three-tier model. The source-ledger can serve as semantic memory's attribution layer.

---

## Practice 4: Use Structured Inter-Agent Communication

**What:** When multiple agents collaborate, they must communicate via structured, schema-validated messages — never free-form natural language. Each agent handoff is a typed message with defined fields.

**Why:** Natural language communication between agents loses information, introduces ambiguity, and makes debugging impossible. Structured messages enable reliable routing, validation, and traceability.

**How:**
- Define a message schema for each agent-to-agent interaction (JSON Schema)
- Include: source agent, target agent, intent, payload, context references, priority
- Validate messages at both send and receive boundaries
- Log every inter-agent message for debugging

**Lyra Application:** Lyra's orchestrator-to-agent and agent-to-agent communication must use structured schemas. The message bus should validate at both ends.

---

## Practice 5: Build an Evaluation Harness as a Separate System

**What:** Evaluation must be a standalone system, not embedded in the application. It runs continuously — both offline (against benchmark datasets) and online (against production traffic). Uses three pillars: automated metrics, LLM-as-judge, and human evaluation.

**Why:** Without a dedicated evaluation system, quality regressions are invisible until users complain. Prompt changes, model updates, and tool modifications all risk quality degradation.

**How:**
- Create a golden dataset of inputs with expected outputs for regression testing
- Use LLM-as-judge with structured rubrics (accuracy, completeness, safety, format correctness)
- Run evaluation on every prompt change, model update, or pipeline modification
- Track scores over time to detect regressions
- Evaluate at multiple granularities: individual tool calls, agent trajectories, end-to-end outcomes

**Lyra Application:** Lyra's verification workstream should implement all three pillars. The evaluation harness should be a separate subsystem with its own CI pipeline.

---

## Practice 6: Implement Model Fallback Chains

**What:** Never hard-depend on a single model provider or model version. Design a fallback chain: primary model → secondary model → cached response → graceful degradation message. Every LLM call point in the system should implement this.

**Why:** Model APIs have outages, rate limits, and latency spikes. A single-model dependency creates a single point of failure for the entire agent system.

**How:**
- Abstract model interface so any provider can be swapped without code changes
- Configure fallback order per use case (complex reasoning may need different fallbacks than simple classification)
- Implement circuit breakers: if a model returns errors above threshold, automatically shift traffic
- Cache semantically similar queries to serve during outages
- Monitor fallback rates — high rates indicate primary model issues

**Lyra Application:** Lyra's multi-model architecture (Claude, GPT, Gemini) should implement model-agnostic interfaces with automatic fallback chains per workstream.

---

## Practice 7: Log Everything with LLM-Specific Instrumentation

**What:** Every LLM interaction must be logged with: model identifier, prompt template version, full input, full output, token count, latency, cost, and success/failure. Use OpenTelemetry-compatible spans with LLM-specific attributes.

**Why:** Debugging AI systems without full trace data is nearly impossible. Cost surprises, quality issues, and latency problems all require per-request data to diagnose.

**How:**
- Instrument every LLM call with a span containing: model, prompt_version, input_tokens, output_tokens, latency_ms, cost_estimate
- Redact PII from logged prompts and responses before storage
- Create dashboards: cost per workstream, latency p50/p95/p99, error rates by model, token usage trends
- Set alerts: cost spike, latency degradation, error rate increase, guardrail trigger rate increase

**Lyra Application:** Lyra's harness engineering should implement OpenTelemetry with LLM-specific spans. Every orchestrator decision, tool call, and agent response must be traced.

---

## Practice 8: Sandbox All Tool Execution

**What:** Never trust agent-chosen parameters for tool calls. Every tool execution must go through: parameter validation (against schema), execution in a sandboxed environment, result validation (structured output check), and logging.

**Why:** Agents can hallucinate tool parameters, attempt unauthorized operations, or produce malformed tool calls. Direct execution without validation is a security and reliability risk.

**How:**
- Validate all tool parameters against strict JSON Schema before execution
- Execute tools in isolated environments (containers, Lambda, separate processes)
- Implement allow/deny lists for tool operations (e.g., file system paths, API endpoints)
- Set per-tool timeouts and retry policies
- Validate tool outputs against expected response schema before passing back to agent

**Lyra Application:** Lyra's plugin/tool system (07-plugins) must enforce parameter validation and execution sandboxing for every tool.

---

## Practice 9: Implement the Reflector/Critic Pattern

**What:** Every agent action should be reviewed by a separate "critic" or "verifier" agent before being committed. The critic is a dedicated agent that checks: correctness, safety, format compliance, and alignment with intent.

**Why:** Agents make mistakes — hallucinated facts, unsafe actions, malformed outputs. Self-checking is unreliable (the same reasoning that produced the error is unlikely to catch it). A separate verifier breaks the confirmation bias loop.

**How:**
- Run the critic as a separate LLM call with a different prompt (not just "check your work")
- Critic receives: the original intent, the agent's output, and the evaluation rubric
- Critic returns: pass/fail + specific issues found + confidence score
- Failed outputs trigger retry (with critic feedback) or escalation
- Track critic pass/fail rates per agent to identify underperforming agents

**Lyra Application:** Lyra's verification workstream IS the critic pattern. Every orchestrator output and sub-agent response should pass through the verifier.

---

## Practice 10: Budget the Context Window Proactively

**What:** The context window must be explicitly allocated — not passively filled until overflow. Define budgets: X% system prompt, Y% tool definitions, Z% conversation history, W% working memory. When approaching limits, compress or evict strategically.

**Why:** Context overflow causes silent degradation (truncation, lost context) or hard errors. Without budgeting, systems inevitably hit limits at the worst times (long conversations, complex tasks).

**How:**
- Define explicit percentage allocations for each context category
- Implement a context manager that tracks token usage per category in real-time
- When approaching budget: summarize older conversation turns, evict least-relevant retrieved context, compress tool outputs
- Reserve headroom (10-15%) for unexpected needs
- Use token counting libraries to estimate usage before sending requests

**Lyra Application:** Lyra's context workstream (03-context) should implement proactive budgeting with the context manager tracking usage in real-time.

---

## Practice 11: Collect Implicit Feedback and Close the Loop

**What:** Explicit ratings are rare. Collect implicit signals: user edits the output (correcting), user abandons (dissatisfied), user re-asks with different phrasing (output wasn't helpful), verification failures (output was wrong). Feed these back into prompt improvements and few-shot example banks.

**Why:** <5% of users provide explicit feedback. Implicit signals provide 20x more data about system quality. Without closing the loop, the same mistakes repeat indefinitely.

**How:**
- Track: verification pass/fail rates, user edit distance from agent output, conversation abandonment rate, re-query rate
- Use a separate "reflector" agent to analyze failure patterns and suggest improvements
- Maintain a dynamic few-shot example bank — add successful interactions, remove stale ones
- A/B test prompt improvements suggested by feedback analysis
- Measure whether "improvements" actually moved metrics

**Lyra Application:** Lyra's self-improvement loop should collect implicit signals from the verification workstream. The reflector agent analyzes patterns and proposes prompt updates.

---

## Practice 12: Separate AI Logic from Infrastructure (Harness Pattern)

**What:** The "harness" — job queues, state management, configuration, deployment, monitoring — must be a separate layer from the AI logic. Agents should not know about databases, queues, or deployment. The harness provides durability, observability, and configuration management.

**Why:** Mixing AI and infrastructure creates systems that are hard to test (can't test agents without full infrastructure), hard to debug (can't isolate AI failures from infrastructure failures), and hard to evolve (changing infrastructure requires touching AI code).

**How:**
- AI logic layer: agents, prompts, tools — stateless functions that receive input and return output
- Harness layer: job queues, state persistence, retry logic, configuration management, monitoring
- Communication via well-defined interfaces (not direct database access from agents)
- Use durable execution for long-running agent workflows (survive process restarts)
- Configuration-as-code for all AI parameters — deploy config changes without code deploys

**Lyra Application:** This is Lyra's defining architectural principle. The harness-engineering foundation should provide durability, observability, and configuration management as a service to the AI layer.
