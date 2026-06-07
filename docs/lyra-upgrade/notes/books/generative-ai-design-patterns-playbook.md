# Generative AI Design Patterns — Best Practices Playbook

## Practice 1: Structured Output Enforcement via Grammar

- **What:** Use Pydantic dataclasses or constrained decoding to enforce output structure. Define explicit response schemas for every agent invocation. Use `output_type`, `response_format`, or JSON mode to guarantee parseable results.
- **Why:** Unstructured text from LLMs breaks downstream processing chains. Structured output is the foundation of reliable agent-to-agent communication, tool calling, and testable pipelines. Without it, every consumer must implement fragile parsing.
- **Lyra route:** §4.6 (Plugin/Command System) — all agent outputs should conform to typed schemas.
- **Source:** Pattern 2 (Grammar), Chapter 2. Also reinforced in Patterns 17, 19, 21, and Chapter 10.

---

## Practice 2: Use a Different Model for Evaluation Than Generation

- **What:** When using LLM-as-Judge or Reflection, ALWAYS use a different LLM for evaluation than for content generation. For example, Gemini generates, Claude critiques.
- **Why:** LLMs exhibit strong self-bias — they rate their own outputs much more favorably than a different model would. Using the same model for generation and evaluation inflates scores and hides quality issues. Self-bias is so strong that asking for explanations can actually increase bias.
- **Lyra route:** §4.7 (Reliability/Evaluation) — Lyra's verifier agents must use different model providers than generator agents.
- **Source:** Pattern 17 (LLM-as-Judge), Pattern 18 (Reflection), Chapter 6.

---

## Practice 3: Implement All Four Memory Types

- **What:** Build working memory (current session, token-budget-trimmed), episodic memory (relevant past messages from DB), procedural memory (user profiles, preferences, system instructions), and semantic memory (key facts extracted across sessions). Use a framework like Mem0 or LangMem.
- **Why:** LLMs are stateless — each call is independent. Working memory alone (prepending history) becomes cost-prohibitive due to transformer quadratic scaling. Selective retrieval of only relevant memories from persistent stores is essential for both quality and cost.
- **Lyra route:** §4.2 (Memory Subsystem) — Lyra needs all four memory types for persistent agent operation.
- **Source:** Pattern 28 (Long-Term Memory), Chapter 8.

---

## Practice 4: Reflection with Exactly One Re-evaluation Round

- **What:** Implement Reflection as: (1) Generate → (2) Evaluate with critique (using different LLM) → (3) Apply feedback → (4) Regenerate once. Avoid multi-round threshold-setting complexity.
- **Why:** Setting a "good enough" quality threshold is surprisingly hard because LLM-as-Judge scoring is lenient — produced work and good work often get the same scores. A single retry avoids threshold calibration entirely while still catching most errors. For code generation, even one reflection round dramatically reduces syntax errors and logical bugs.
- **Lyra route:** §4.7 (Reliability) — Lyra's quality gates should implement single-round reflection.
- **Source:** Pattern 18 (Reflection), Chapter 6.

---

## Practice 5: Defend Tool Calling with Plan-Then-Execute

- **What:** Before invoking tools, have the agent formulate a fixed plan of actions. Tool call results are inserted into context but the agent does NOT deviate from the original plan. This prevents untrusted third-party data from injecting instructions.
- **Why:** Tool calling dramatically expands the attack surface — adversarial actors can manipulate external tools to inject prompts that hijack agent behavior. A fixed plan limits the blast radius.
- **Lyra route:** §4.8 (Plugin/Tool System) — Lyra's tool execution must follow Plan-Then-Execute for safety.
- **Source:** Pattern 21 (Tool Calling), Chapter 7. Beurer-Kellner et al. (2025) prompt injection defenses.

---

## Practice 6: Cascade Model Selection by Task Complexity

- **What:** Route requests to different model tiers: SMALL_MODEL for guardrails, classification, simple checks; DEFAULT_MODEL for standard generation; BEST_MODEL for quality-critical reasoning. Log prompts at each tier to build distillation datasets.
- **Why:** Frontier models are expensive and slow. A 3-tier routing strategy can reduce costs by 10-50x while maintaining quality where it matters. Guardrails run on small models because they perform simple boolean checks. The distillation pipeline (prototype on frontier → log prompts → distill on logged distribution → quantize) makes the strategy sustainable.
- **Lyra route:** §4.9 (Model Routing/Cost Optimization) — Lyra's cost-aware model selection.
- **Source:** Pattern 24 (Small Language Model), Pattern 26 (Inference Optimization), Chapter 8. Chapter 10 implementation.

---

## Practice 7: Test Agent Chains with Dependency Injection

- **What:** Define structured input/output types for each chain step (Pydantic dataclasses), write assertion-based tests on structured outputs, mock individual LLM calls with deterministic responses, and test on multiple LLM providers.
- **Why:** LLM chains have nondeterministic outputs, models change rapidly, and the same prompt behaves differently across providers. Without DI-based testing, you're reduced to "vibe checking" — eyeballing output and saying "looks right." Assertions on structured output are concrete and repeatable.
- **Lyra route:** §4.7 (Reliability/Testing) — Lyra's harness testing architecture.
- **Source:** Pattern 19 (Dependency Injection), Chapter 6.

---

## Practice 8: Use Few-Shot CoT When Zero-Shot Fails

- **What:** When the model fails at a domain-specific task, provide 2-3 worked examples demonstrating the step-by-step reasoning pattern. The model will template its response on those examples.
- **Why:** Zero-shot CoT ("think step-by-step") only unlocks pretrained capabilities. For industry-specific tasks not well covered in training data, you need to demonstrate the reasoning pattern — this is fundamentally different from RAG, which provides knowledge. CoT shows how to reason; RAG provides what to reason about.
- **Lyra route:** §4.5 (Reasoning Subsystem) — Lyra's planning and reasoning prompts.
- **Source:** Pattern 13 (Chain of Thought), Chapter 5.

---

## Practice 9: Scale Retrieval Quality Before Generation Quality

- **What:** Invest heavily in retrieval postprocessing: rerank retrieved chunks with a cross-encoder or LLM, deduplicate, filter by relevance threshold, and enrich with metadata. Poor retrieval cannot be salvaged by good generation.
- **Why:** Embedding similarity does not equal relevance. Chunks that are vector-adjacent may be unrelated in meaning. Postprocessing dramatically improves faithfulness. Citations should be grounded on retrieved chunks — if the chunks are wrong, citations are wrong.
- **Lyra route:** §4.3 (Knowledge/Context) — Lyra's retrieval pipeline and grounding mechanisms.
- **Source:** Pattern 10 (Node Postprocessing), Pattern 11 (Trustworthy Generation), Pattern 12 (Deep Search), Chapter 4.

---

## Practice 10: Separate Assembly from Generation for Safety-Critical Content

- **What:** For high-risk content (product catalogs, financial data, medical information): Step 1 — Assemble raw facts using deterministic sources (databases, OCR, templates) with low temperature (=0-0.1). Step 2 — Have LLM reformat assembled facts (rephrase, summarize) without adding new claims.
- **Why:** LLM generation from scratch can introduce costly errors (e.g., wrong battery type → airline cargo fire). Assembly from verified sources + LLM reformatting dramatically reduces hallucination risk while still producing fluent, appealing content.
- **Lyra route:** §4.7 (Safety) — Lyra's controlled-output generation for high-stakes use cases.
- **Source:** Pattern 30 (Assembled Reformat), Chapter 9.

---

## Practice 11: Log Human Feedback for Continuous Improvement

- **What:** In copilot mode, every time a user overrides an AI recommendation, log the override as implicit feedback. Store user modification instructions in long-term memory for future runs. Use logged prompts and human edits to build fine-tuning datasets.
- **Why:** Human feedback is the most valuable training signal. Unobtrusive collection in copilot mode generates training data at scale without explicit annotation effort. This is the engine that enables graduation from copilot to autonomous agent.
- **Lyra route:** §4.10 (Self-Improvement/Learning) — Lyra's evolution and data flywheel.
- **Source:** Chapter 10 (Composable Agentic Workflows), Pattern 28 (Long-Term Memory).

---

## Practice 12: Run Guardrails in Parallel, Not Sequentially

- **What:** Use `asyncio.gather` to start guardrail checks simultaneously with the main LLM call. If guardrail fails, terminate the main call. This prevents guardrails from adding latency.
- **Why:** Guardrails that run sequentially before the main call add latency to every user interaction. Parallel execution with early termination maintains response speed while preserving safety. Guardrails should use SMALL_MODEL for cost efficiency.
- **Lyra route:** §4.7 (Safety/Guardrails) — Lyra's guardrail architecture.
- **Source:** Chapter 10 implementation, Pattern 32 (Guardrails), Chapter 9.

---

## Practice 13: Prefer Composable Patterns Over Frameworks

- **What:** Build multiagent workflows using direct composition of individual patterns (CoT, RAG, Tool Calling, Reflection, Guardrails) rather than monolithic multiagent frameworks. Implement workflow logic directly in application code, with each step as an async function.
- **Why:** "The most successful implementations use simple, composable patterns rather than complex frameworks" (Anthropic). Direct control gives you: explicit state management, clear error handling, straightforward testing via DI, and the ability to swap individual components without framework lock-in. Frameworks add abstraction layers that obscure failure modes.
- **Lyra route:** §4.10 (Architecture) — This is Lyra's core architectural philosophy.
- **Source:** Chapter 10, cited from Anthropic's guidance on building effective agents.

---

## Practice 14: Use Auto-CoT for Dynamic Example Selection at Scale

- **What:** Build a question-answer example store indexed by embedding. For each new question, retrieve the 5 most similar examples and include them as few-shot demonstrations. Generate the example store by: (1) Diverse question sampling → (2) Zero-shot CoT generation with multiple models/settings → (3) Consistency/correctness filtering.
- **Why:** Static few-shot examples limit generalization. Auto-CoT dynamically selects the most relevant reasoning patterns for each query, effectively showing the model "how to fish in this specific way." The consistency filtering step is critical — only examples where multiple models agree on both answer and reasoning are accepted.
- **Lyra route:** §4.5 (Reasoning) — Lyra's dynamic prompt construction.
- **Source:** Pattern 13 (Chain of Thought) — Auto-CoT variant, Chapter 5.

---

## Practice 15: Prototype on Frontier, Distill for Production

- **What:** Three-phase deployment: (1) Prototype with frontier model (Gemini 2.5 Pro, Claude Opus) to establish quality baseline. (2) Deploy logging to capture real prompt distribution. (3) Distill a smaller model on logged prompts (teacher → student via KL divergence), optionally quantize (FP32 → INT4), and deploy with speculative decoding for latency reduction.
- **Why:** Frontier models are too expensive and slow for production at scale. But smaller models fail on complex tasks out of the box. Distillation narrows the smaller model's knowledge to exactly the tasks needed, achieving frontier-level quality at a fraction of the cost. The full pipeline (12B → 1B distillation + 4-bit quantization) can reduce inference time from minutes to seconds.
- **Lyra route:** §4.9 (Model Optimization) — Lyra's deployment and cost optimization strategy.
- **Source:** Pattern 24 (Small Language Model), Chapter 8.
