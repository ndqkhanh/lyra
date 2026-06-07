# Building Agentic AI — Best Practices Playbook

**Source:** Sinan Ozdemir, *Building Agentic AI: Workflows, Fine-Tuning, Optimization, and Deployment* (Pearson, 2025 Early Release)

---

## Practice 1: Build Both Workflow AND Agent Versions, Then Benchmark

- **What:** For any production task, implement both a deterministic LLM workflow (predefined nodes/edges) and an autonomous agent (ReAct + tools). Run both against the same test dataset and compare accuracy, latency, cost, and tool efficiency before choosing.
- **Why:** Workflows are cheaper, faster, and more predictable; agents are more flexible and can handle unforeseen edge cases. The SQL RAG workflow and SQL agent produced similar accuracy (~51%) but the agent cost more and ran slower. You cannot know which approach wins without testing both.
- **Lyra route:** §4.3 (Agent Architecture), §4.6 (Evaluation Harness)
- **Source:** Chapter 4

---

## Practice 2: Semantic Few-Shot + Chain-of-Thought as the Default Prompting Baseline

- **What:** Retrieve semantically similar examples (via embedding match) rather than using random or static few-shot examples. Combine with chain-of-thought prompting. Aim for 3-7 examples that maximize domain coverage without introducing conflicting information.
- **Why:** Semantic few-shot alone provided ~20% accuracy lift over random examples. Adding CoT raised the total gain to ~35% over zero-shot baselines (from 33% to 45% on SQL generation). More than 7 examples can introduce conflicting signals.
- **Lyra route:** §4.1 (Prompt Engineering), §4.3 (Context Assembly)
- **Source:** Chapter 3

---

## Practice 3: Use Multi-Metric Evaluation — Never Rely on a Single Score

- **What:** For retrieval systems, measure at minimum Precision@k, Recall@k, and MRR@k. For generation, use rubric-based grading with a different LLM family. For the full system, track accuracy, latency, cost, and calibration together. Break results down by sub-domain (heatmap per database/per task type).
- **Why:** Precision alone misses recall failures. MRR alone is misleading for multi-hop tasks. A model can be accurate but uncalibrated. Gemini 2.5 Pro had the best SQL accuracy (57.5%) but cost 28x more than the next best model — without cost tracking, the wrong model would have been selected.
- **Lyra route:** §4.6 (Evaluation Harness), §4.8 (Observability)
- **Source:** Chapters 3, 4

---

## Practice 4: Explicitly Prompt Agents to Use Their Tools — Do Not Trust Default Behavior

- **What:** Add explicit instructions in the system prompt telling agents WHEN and HOW to use tools. A single sentence ("ALWAYS USE the BM25 tool before answering any question, even if you think you don't need it") can make the difference between a working and non-working system.
- **Why:** GPT-4.1 ignored its database tool nearly 100% of the time when not explicitly prompted — it was overconfident in its own knowledge. That single sentence lifted accuracy from ~48% to ~71%. Conversely, GPT-4.1-Nano failed to use the tool ~20% of the time even when explicitly told to do so — revealing instruction adherence gaps that must be measured.
- **Lyra route:** §4.1 (Prompt Engineering), §4.3 (Tool Design)
- **Source:** Chapter 5

---

## Practice 5: Separate Planning from Execution Using Tiered LLMs

- **What:** Use a large, capable LLM (GPT-4.1, Claude Opus) for initial planning and task decomposition. Use smaller, cheaper LLMs (GPT-4.1-Mini, Llama-4-Scout) for executing individual steps. Add a re-planning component that re-evaluates the plan after each step and condenses or expands as needed.
- **Why:** Creating a good plan is harder than executing its steps. The deep research workflow spent the majority of latency on step execution — optimizing the executor model yields the biggest speed gains. Planning with a large model + executing with a small model balances cost and quality.
- **Lyra route:** §4.4 (Multi-Agent Orchestration), §4.5 (Model Routing)
- **Source:** Chapter 5

---

## Practice 6: Design Tools as Self-Contained Error Handlers

- **What:** Every tool must catch all exceptions internally and return structured error messages as tool response text (never let tracebacks propagate silently). Include metadata about what failed, what was attempted, and what the agent should try next. Test each tool in isolation before connecting it to an agent.
- **Why:** The LLM cannot see tool execution tracebacks; it only sees the string response. When a tool fails silently, the agent either hallucinates a result or tells the user "I encountered an error" with no recovery path. Well-structured error responses let the agent self-correct (e.g., retry with different parameters).
- **Lyra route:** §4.3 (Tool Design), §4.7 (Reliability)
- **Source:** Chapter 4, Case Study 3

---

## Practice 7: Use the Supervisor (Tool-Calling) Pattern for Multi-Agent Orchestration

- **What:** In a multi-agent system, use a supervisor agent that treats sub-agents as tools — delegating targeted tasks with limited context, waiting for completion, and aggregating results. Avoid any-to-any networking unless agents genuinely need to share conversation history bidirectionally.
- **Why:** Supervisor = micro-service orchestrator. It prevents race conditions (two agents emailing the same lead), enables independent debugging/tweaking of each agent, allows different LLMs for different roles (cheap for lead gen, expensive for qualification), and isolates prompt changes to prevent regressions across the pipeline.
- **Lyra route:** §4.4 (Multi-Agent Orchestration), §4.5 (Supervisor/Manager Agent)
- **Source:** Chapter 5, Case Study 4 Revisited

---

## Practice 8: Treat Reasoning as a Hyperparameter, Not a Default

- **What:** Test every task with reasoning OFF, LOW, MEDIUM, and HIGH. Enable reasoning only for decomposition-heavy tasks (multi-step math, planning, multi-tool orchestration, screen coordinate pointing). Keep reasoning off for simple QA, retrieval-first answers, and high-throughput endpoints.
- **Why:** Across three separate benchmarks (HLE, MathQA, computer-use), reasoning did not reliably improve accuracy and always increased latency and cost. On MathQA, Claude Opus 4 performed BEST with reasoning OFF. Reasoning doubled latency on computer-use coordinate tasks while improving accuracy by only 2.4%.
- **Lyra route:** §4.5 (Model Routing), §4.6 (Evaluation)
- **Source:** Chapter 7

---

## Practice 9: Prefer Fine-Tuned Classifiers Over Prompted Generative Models for Classification

- **What:** When the task is classification (predicting from a fixed set of labels), fine-tune an autoencoding model (e.g., ModernBERT) rather than prompting a generative LLM. Use calibration metrics (ECE) alongside accuracy to select the best model.
- **Why:** Fine-tuned classifiers achieve similar accuracy (~73%) at 1/5 the inference cost, with guaranteed output format (no hallucinated classes), and much better calibration (ModernBERT ECE was 1.7x lower than GPT-4.1). The fine-tuning cost is ~$1 for ModernBERT vs. $122 for GPT-4.1. Self-hosting keeps data in-VPC for privacy compliance.
- **Lyra route:** §4.2 (Classification/Routing), §4.6 (Evaluation)
- **Source:** Chapter 8

---

## Practice 10: Use Domain Adaptation (Continued Pre-Training) to Internalize Policy Knowledge

- **What:** Fine-tune an open-source LLM on raw domain documents (policy texts, knowledge base articles) using continued pre-training — not conversational fine-tuning. Chunk documents with overlap and source metadata prefixes. Use LoRA + 4-bit quantization for memory efficiency. Mix in some conversational data to prevent catastrophic forgetting.
- **Why:** A domain-adapted Qwen3-8B went from 6.5% to 50%+ accuracy on policy QA — matching GPT-4.1-Nano with retrieval tools but requiring no external lookup at inference time. The model internalized the rules natively, eliminating retrieval latency and cost for every query.
- **Lyra route:** §4.2 (Domain Knowledge), §4.7 (Safety/Policy Compliance)
- **Source:** Chapter 8, Case Study 14

---

## Practice 11: Benchmark the Full Voice Pipeline End-to-End, Not Components in Isolation

- **What:** For voice/real-time systems, test every STT+TTS combination by running audio through the full round-trip (TTS → STT) and measuring both Word Error Rate (WER) and latency per word. Select the fastest combination that meets your accuracy threshold, not the most accurate in isolation.
- **Why:** Groq's distil-whisper was 7.5x faster than GPT-4o-mini TTS with near-identical accuracy. Testing components separately misses the interaction effects between specific STT and TTS models. Voice bots require sub-second end-to-end latency; the LLM text generation is often not the bottleneck.
- **Lyra route:** §4.9 (Voice/Real-Time)
- **Source:** Chapter 9, Case Study 16

---

## Practice 12: Use Matryoshka Embeddings for Flexible Dimension Trade-Offs

- **What:** Fine-tune embedding models with MatryoshkaLoss — apply the ranking loss to progressively truncated embedding dimensions (e.g., 1024, 512, 256, 128, 64). This produces a single model that generates quality embeddings at multiple sizes. Truncate at runtime based on latency/memory requirements.
- **Why:** 64-dim embeddings can match 1024-dim retrieval performance but use ~1/20 the disk space and much less compute for similarity search. The Matryoshka training encourages the model to front-load important information into the earliest dimensions. For 1M vectors, dropping from 1024 to 64 dimensions cuts disk usage by ~20x and slashes search latency.
- **Lyra route:** §4.2 (Embedding/Pipeline Optimization), §4.3 (RAG)
- **Source:** Chapter 9, Case Study 17

---

## Practice 13: Implement an LLM-as-Judge Rubric with Cross-Family Grading

- **What:** For tasks without structured ground truth, create a rubric prompt that grades agent responses on a 0-3 scale with explicit criteria. Use a mid-tier LLM from a DIFFERENT family than the agent's LLM (e.g., Llama-4-Scout to grade GPT-4.1 agent responses). Validate rubric quality by manually spot-checking ~5% of graded responses.
- **Why:** Same-family LLMs may share subliminal biases that inflate or deflate scores. Mid-tier LLMs are sufficient because all context is provided in the rubric prompt — they never need external knowledge. Manual spot-checking builds trust without requiring full human evaluation.
- **Lyra route:** §4.6 (Evaluation Harness)
- **Source:** Chapters 4, 5

---

## Practice 14: Cache Static Prompt Prefixes and Order Content for Cache-Efficiency

- **What:** Place all static content (guardrails, system instructions, few-shot examples, tool descriptions) at the beginning of the prompt. Place all dynamic content (retrieved documents, user queries, current date) at the end. Use prompt caching wherever the LLM provider supports it.
- **Why:** Prompt caching breaks at the first token that differs from a cached prefix. Static-first ordering maximizes cache hits, reducing input processing cost and latency. Non-reasoning models (GPT-4.1-mini) showed consistent cost/latency reductions from caching; reasoning models (o4-mini) showed negligible benefit due to non-deterministic reasoning tokens.
- **Lyra route:** §4.1 (Prompt Engineering), §4.3 (Context Assembly)
- **Source:** Chapters 1, 5

---

## Practice 15: Keep Experiments Reproducible and Version-Controlled

- **What:** Use LangGraph scripts (or equivalent) as the experimentation framework. Version-control prompts, embedders, LLM selections, and hyperparameters alongside code. Log every experiment with cost, latency, and accuracy results. Use LangSmith or equivalent for traceability.
- **Why:** The field moves fast — models change, prompts evolve, and results must be reproducible. A structured experimentation framework lets you re-run tests when new models are released and compare results across versions. The 14-configuration few-shot experiment (Chapter 3) demonstrates the power of systematic, reproducible experimentation.
- **Lyra route:** §4.6 (Evaluation), §4.8 (Observability)
- **Source:** Chapters 3, 4, 5
