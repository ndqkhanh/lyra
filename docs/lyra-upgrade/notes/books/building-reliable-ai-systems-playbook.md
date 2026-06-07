# Building Reliable AI Systems — Best-Practices Playbook for Lyra

**Source Book:** Building Reliable AI Systems (Rush Shahani, 2026, Manning MEAP V12)
**Generated:** 2026-06-06
**Usage:** Concrete engineering practices for Lyra's agent architecture, routing, memory, tools, safety, reliability, and observability workstreams.

---

## Practice 1: Separate Harness from Sandbox (Chapter 7)

**What:** Architect agent systems with a clear control-plane / compute-plane separation. The harness owns the agent loop, tool routing, approvals, tracing, and state management. The sandbox is an isolated execution environment where the agent reads/writes files, runs shell commands, and executes code. Credentials and sensitive data stay in the harness, never in the sandbox.

**Why:** This pattern emerged independently across OpenAI (Codex CLI, Agents SDK), OpenClaw (300K+ GitHub stars), and NVIDIA (NemoClaw). It prevents model-generated code from accessing credentials, ensures sandbox crashes don't lose state (the harness restores from last checkpoint), and enables clean permission boundaries. As Shahani puts it: "The model enables reasoning. The harness enables capability."

**Lyra Route:** `plans/16-reliability.md`, `plans/07-plugins.md`, `plans/09-commands.md` — Lyra's architecture debate around harness engineering directly maps to this pattern.

**Source Chapter:** Chapter 7, Section 7.8 (Beyond tools: Production agent harnesses and OpenClaw)

---

## Practice 2: Design Tools as Agent-Legible Interfaces (Chapter 7)

**What:** Every tool (MCP or otherwise) should be a self-documenting interface designed for LLM consumption. Tool names, parameter descriptions, and schemas function as routing instructions for the AI. Every tool response must follow a consistent structure: `{success: bool, error: string|null, message: string, results: [...]}`. Distinguish empty results (`success: true, results: []`) from actual errors (`success: false`).

**Why:** "What you name your tools, how you describe them, and how you design their arguments all influence how models use them." A well-designed tool schema eliminates the need for glue code — the model can reason about which tool to call, with what parameters, and how to interpret success vs. failure responses. Structured error responses prevent the model from hallucinating when tools fail.

**Lyra Route:** `plans/07-plugins.md`, `plans/05-router.md` — Lyra's plugin system should follow this standardized response contract.

**Source Chapter:** Chapter 7, Sections 7.5, 7.7

---

## Practice 3: Specialize Agents, Generalize Orchestration (Chapter 8)

**What:** Decompose complex agent systems into specialized agents (search, Q&A, vision, policy) coordinated by an orchestrator with shared typed state. Use lighter/cheaper models for intent classification and routing; reserve full-capability models only for synthesis and complex responses. Implement conditional routing based on analyzed user intent, not keyword matching.

**Why:** Monolithic agents become mediocre at everything. Specialization enables independent testing, debugging, scaling, and improvement. Selective model assignment (gpt-5.4-mini for routing, gpt-5.4 for synthesis) "can significantly improve response quality while keeping costs manageable." When one agent fails, others continue functioning — the system degrades gracefully.

**Lyra Route:** `plans/05-router.md`, `plans/09-commands.md`, `plans/16-reliability.md` — Lyra's multi-agent routing and command orchestration architecture.

**Source Chapter:** Chapter 8, Sections 8.1, 8.2

---

## Practice 4: Test Workflows, Not Just Components (Chapter 8)

**What:** Multi-agent testing requires five categories beyond unit tests: (1) blended queries (multi-modal, multi-intent), (2) ambiguous intent routing, (3) agent failure resilience, (4) state flow preservation across the workflow, and (5) regression against known bugs. Tests should verify that orchestrator decisions are correct, state flows without contamination, and critical user details survive the complete agent pipeline.

**Why:** "Bugs and failures happen at the seams: when agents pass information, when states are updated, or when workflows get complex." Individual agent correctness does not guarantee system correctness. State contamination between separate workflows is a silent failure mode — one user's session details must not leak into another's.

**Lyra Route:** `plans/16-reliability.md`, `tests/verification/` — Directly applicable to Lyra's verification and end-to-end testing infrastructure.

**Source Chapter:** Chapter 8, Section 8.2

---

## Practice 5: Implement Systematic Hallucination Measurement (Chapter 9)

**What:** Follow the four-step methodology: (1) identify grounding data (authoritative source of truth), (2) create generic (100-500 representative queries) and adversarial test sets, (3) extract claims from agent responses and validate against grounding data, (4) track Grounding Defect Rate (GDR) and Hallucination Severity Score (HSS) over time. Use FActScore to break responses into atomic facts for granular evaluation.

**Why:** "Hallucinations do not announce themselves. They slip past users and damage trust before anyone notices." Tracking GDR by topic (product info vs. shipping policies) reveals specific weak spots. Adversarial test sets surface edge cases that generic tests miss. Without systematic measurement, you cannot detect quality drift.

**Lyra Route:** `plans/16-reliability.md`, `plans/17-safety.md` — Evaluation methodology for Lyra's quality assurance.

**Source Chapter:** Chapter 9, Section 9.1

---

## Practice 6: Layer Semantic Caching with Similarity Thresholds (Chapter 9)

**What:** Implement semantic caching using vector embeddings and a similarity threshold (0.7-0.8). When a new query's embedding is within threshold of a cached query, return the cached response instead of making a fresh LLM call. Use cache invalidation strategies: version tagging, metadata checks (policy date, knowledge base version), and selective caching for stable topics only.

**Why:** "At scale, this can be the difference between a system that becomes prohibitively expensive under load and one that handles thousands of repeated questions with minimal overhead." LLM inference dominates both execution time (89.3%) and costs (97%) — caching is the highest-impact optimization.

**Lyra Route:** `plans/02-memory.md`, `plans/03-context.md` — Caching strategy for Lyra's memory and context retrieval layers.

**Source Chapter:** Chapter 9, Section 9.2.3

---

## Practice 7: Route Queries by Complexity with Multi-Model Fallback (Chapter 9)

**What:** Implement a router that classifies each query by complexity and sends simple queries to cheaper/faster models while escalating complex queries to full-capability models. Use function calling with a small model for intelligent routing (not brittle keyword matching). Optionally implement two-pass fallback: try the cheap model first, check confidence, escalate only if needed.

**Why:** "If 80-90% of your traffic can be handled by gpt-5.4-mini or similar, you drastically reduce your per-query charges." This is the most impactful cost optimization alongside caching.

**Lyra Route:** `plans/05-router.md` — Lyra's routing architecture.

**Source Chapter:** Chapter 9, Section 9.2.4

---

## Practice 8: Build LLM-Native Monitoring (Not Web-Server Monitoring) (Chapter 10)

**What:** Monitor the four critical questions: (1) Can users get help quickly? (2) Are answers actually useful? (3) Do users leave satisfied? (4) Will this bankrupt us? Track tokens-per-second (not just latency), cost-per-token efficiency trends, response quality scores, user satisfaction patterns, and session abandonment rates. Log every request with token counts, model version, prompt version, pipeline timing breakdown, and cost breakdown.

**Why:** "A system can have 99.9% uptime and 200ms response time while confidently stating incorrect refund policies for weeks." Traditional monitoring metrics are blind to LLM-specific failures. Token generation represents 97% of costs in most LLM applications — that's where optimization and monitoring should focus.

**Lyra Route:** `plans/16-reliability.md`, `plans/17-safety.md` — Lyra's observability and production monitoring strategy.

**Source Chapter:** Chapter 10, Sections 10.3, 10.4

---

## Practice 9: Version Prompts as Production Artifacts (Chapter 10)

**What:** Treat prompts as versioned production artifacts with controlled rollout, A/B testing, and instant revert capabilities. Maintain a golden test dataset (curated questions with expected response characteristics) and run automated quality checks on schedule. Shadow-test new models or prompt versions against production traffic before deploying.

**Why:** "Your prompts aren't just instructions. They're quality control mechanisms." A single prompt change can double your monthly bill or silently degrade response quality. Golden datasets catch regressions before users do. Shadow testing lets you safely evaluate changes against real traffic patterns.

**Lyra Route:** `plans/03-context.md`, `plans/05-router.md`, `plans/09-commands.md` — Lyra's system prompts, router prompts, and command templates.

**Source Chapter:** Chapter 10, Sections 10.5.2, 10.5.3

---

## Practice 10: Implement Defense-in-Depth Safety (Chapter 11)

**What:** Layer three safety mechanisms: (1) fast keyword/pattern matching to catch obvious dangerous content, (2) ML-based classifier for contextual safety analysis, (3) commercial moderation API (OpenAI Moderation endpoint) for comprehensive content policy checking. No single layer is sufficient — multiple layers compensate for each other's blind spots.

**Why:** "Think of it like airport security: you have multiple checkpoints because no single method is foolproof." Keyword matching alone is brittle (users bypass with synonyms). ML classifiers catch more nuanced violations. Commercial APIs provide the broadest coverage.

**Lyra Route:** `plans/17-safety.md` — Lyra's safety guardrail architecture.

**Source Chapter:** Chapter 11, Sections 11.4, 11.5

---

## Practice 11: Audit Training Data for Bias Before Fine-tuning (Chapter 11)

**What:** Before fine-tuning on user interaction logs (chat logs, support tickets), systematically audit for differential treatment patterns: compare response length, resolution time, escalation rate, and satisfaction score across demographic groups. Use balanced sampling, counterfactual data augmentation, and bias-aware filtering. During training, add a fairness-constrained loss term that penalizes the model for producing systematically different output distributions for different demographic groups.

**Why:** "When you fine-tune a model on customer service logs, you're training it on data that reflects real-world inequalities." The feedback loop is vicious: biased human decisions → biased training data → biased model outputs → more biased training data. Amazon's recruiting AI, COMPAS criminal justice algorithm, and healthcare AI disparities all trace back to un-audited training data.

**Lyra Route:** `plans/17-safety.md`, `plans/15-research.md` — Safety auditing and responsible AI for any Lyra fine-tuning or data ingestion.

**Source Chapter:** Chapter 11, Sections 11.2, 11.3

---

## Practice 12: Make the Repository the System of Record for Agents (Chapter 7)

**What:** Design decisions, architectural constraints, execution plans, and quality standards must live as versioned artifacts that agents can discover and reason about — not in Slack threads, Google Docs, or people's heads. Use AGENTS.md as a concise table of contents (~100 lines) with pointers to deeper structured documentation in `docs/`. Inject small, focused "skills files" on every turn rather than monolithic instruction blocks.

**Why:** "From the agent's perspective, anything it cannot access in-context effectively does not exist." Monolithic instruction files crowd out task context, agents cannot tell what is still current, and they rot faster than anyone can maintain them. Enforce invariants mechanically (linters, structural tests) rather than through documentation — "encode the rule once, and it applies everywhere at once."

**Lyra Route:** `source-ledger.md`, `plans/07-plugins.md`, `plans/09-commands.md` — Lyra's documentation conventions and agent context injection.

**Source Chapter:** Chapter 7, Section 7.8.2

---

## Practice 13: Evaluate Agent Trajectories, Not Just Final Outputs (Chapter 9)

**What:** Agent evaluation must verify both the final answer correctness AND the execution trajectory: intent classification accuracy, tool selection correctness, parameter extraction quality, and step sequencing. Log every tool call in a platform like LangSmith. Compare actual execution traces against expected trajectories. A correct answer via wrong intermediate steps indicates a fragile system.

**Why:** "A correct final answer might hide flawed intermediate reasoning, and correct reasoning might still produce wrong outputs if one tool call fails." This is the key difference between LLM evaluation and agent evaluation. Tracking trajectories also enables debugging — you can pinpoint exactly where the agent's reasoning deviated.

**Lyra Route:** `plans/16-reliability.md`, `src/verification/` — Lyra's agent verification and debugging infrastructure.

**Source Chapter:** Chapter 9, Section 9.3

---

## Practice 14: Enforce Structured Response Contracts for All Tools (Chapter 7)

**What:** Every tool in the agent's toolkit must return responses in a consistent format: `{success: bool, error: string|null, message: string, results: [...]}`. Include suggestions for next steps in error/empty-result responses (e.g., "Try broader search terms or remove the price filter"). Handle timeouts with exponential backoff retry (3 attempts, 1s/2s/4s delays) before returning structured timeout errors.

**Why:** Consistent response structures enable the model to: check `success` to know if the operation worked, use the `message` text directly in user-facing responses, use `error` codes to decide next actions (retry, ask clarification, suggest alternatives). Without structured responses, the model gets Python stack traces and produces unhelpful user responses.

**Lyra Route:** `plans/07-plugins.md`, `plans/09-commands.md` — Lyra's plugin and command response contracts.

**Source Chapter:** Chapter 7, Section 7.7

---

## Practice 15: Combine Explicit and Implicit User Feedback (Chapter 10)

**What:** Track both explicit feedback (thumbs up/down, star ratings, optional comments) and implicit behavioral signals (session abandonment, immediate query rephrasing, copy-paste behavior, escalation rates, return usage frequency). Run weekly 30-minute feedback triage meetings: categorize negative feedback into accuracy, length, tone, missing information, and escalation buckets. Track feedback participation rates — declining rates are a leading indicator of user disengagement that precedes satisfaction drops by 2-3 weeks.

**Why:** "Users might hesitate to give negative explicit feedback, but their behavior reveals true satisfaction levels." A user who gets an answer and immediately asks three follow-up questions is probably confused, not satisfied. Connecting feedback to business outcomes (task completion rate, support ticket reduction, customer retention correlation) proves AI ROI.

**Lyra Route:** `plans/16-reliability.md` — Lyra's quality monitoring and user feedback loops.

**Source Chapter:** Chapter 10, Sections 10.4.1, 10.4.2, 10.4.3
