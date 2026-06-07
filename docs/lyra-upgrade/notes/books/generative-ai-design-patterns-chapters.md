# Generative AI Design Patterns — Chapter Notes

**Author:** Valliappa Lakshmanan & Hannes Hapke | **Year:** 2026 (O'Reilly) | **757 pages**

**Core Thesis:** 32 battle-tested design patterns codify proven solutions derived from cutting-edge research and refined by practitioners who have successfully deployed GenAI systems at scale. The book bridges the gap between impressive prototypes and production-grade AI applications, addressing hallucinations, nondeterminism, knowledge gaps, reliability, safety, and deployment constraints. Target audience: AI engineers, data scientists, enterprise architects building on foundational models (GPT, Claude, Gemini, Llama). Approximately 75% accessible to junior engineers; 25% requires specialized ML/optimization knowledge.

---

## Chapter 1: Introduction (pp. 13–53)

**No patterns — foundational concepts and landscape.**

- **Key insight:** AI engineering is building on top of foundational models rather than training bespoke models. Agentic AI — autonomous systems that break complex tasks into components handled by LLM-powered agents — is the frontier but remains aspirational due to nondeterminism, hallucinations, and planning failures.
- **Agent characteristics defined:** Goal orientation, planning/reasoning, perception/action, adaptability/learning. Autonomy = the ability to operate independently without explicit programming.
- **Sampling control:** Temperature (T=0 = greedy, higher = creative), Top-K (restrict to k most likely tokens), Nucleus/Top-P (dynamic probability nucleus), beam search with frequency/presence/length penalties. Softmax transforms logits to probabilities.
- **In-context learning:** Zero-shot (instruction only), few-shot (with examples). Models adapt without weight changes.
- **Model landscape:** Frontier (GPT-5, Gemini 2.5 Pro), distilled (Gemini Flash, Claude Sonnet, GPT-4o-mini), open-weight (Llama, Mistral, DeepSeek), locally hostable (Llama 8B, Gemma 2B). LMArena leaderboard for blind pairwise comparison.
- **Relevant to Lyra §1.1–§1.3:** Foundational definitions for Lyra's agent architecture. The agent characteristics map directly to Lyra's capability taxonomy.

---

## Chapter 2: Controlling Content Style (pp. 54–161)

**Patterns 1–5: Logits Masking, Grammar, Style Transfer, Reverse Neutralization, Content Optimization**

- **Key insight:** Fine-grained control over LLM output style and format is achievable through logits manipulation, constrained decoding (grammar), and iterative refinement (content optimization). Not core for Lyra's harness engineering concerns.
- **Best practices:**
  - Grammar (Pattern 2): Use structured output constraints (dataclasses/Pydantic models) to guarantee format compliance — critical for tool calling and agent-to-agent communication.
  - Content Optimization (Pattern 5): Use LLM-as-Judge with a scoring rubric; iterate via mutation + evaluation to optimize a piece of content against KPIs.
  - Try-and-try-again anti-pattern: If LLM calls have >90% success rate, retry twice (drops refusal rate below 1% while keeping tail latency reasonable).
- **Relevant to Lyra §4.6:** Structured output enforcement for agent orchestration messages.

---

## Chapter 3: Adding Knowledge — Bass (pp. 162–224)

**Patterns 6–8: Basic RAG, Semantic Indexing, Indexing at Scale**

- **Key insight:** RAG gives the model a (few) fish; Few-shot CoT shows the model how to fish. RAG adds knowledge (data); CoT demonstrates logic. Different context engineering strategies for different needs.
- **Basic RAG (Pattern 6):** Retrieve relevant chunks via embedding similarity, inject into prompt context. Works for static knowledge; dynamic knowledge requires Tool Calling.
- **Semantic Indexing (Pattern 7):** Structure the retrieval index with metadata filtering, hybrid search (keyword + vector), and chunking strategies that preserve document structure.
- **Indexing at Scale (Pattern 8):** Batch embedding generation, incremental indexing, distributed vector stores, cost-aware retrieval (cascade: cheap keyword filter first, then expensive vector search).
- **Relevant to Lyra §4.3–§4.4:** Knowledge grounding and context engineering. Lyra's document ingestion pipeline maps directly to these patterns.

---

## Chapter 4: Adding Knowledge — Syncopation (pp. 225–299)

**Patterns 9–12: Index-Aware Retrieval, Node Postprocessing, Trustworthy Generation, Deep Search**

- **Key insight:** Retrieval quality is dominant over generation quality. Postprocessing retrieved chunks (reranking, deduplication, filtering) dramatically improves faithfulness.
- **Node Postprocessing (Pattern 10):** Rerank retrieved chunks by relevance using an LLM or cross-encoder. This is essential because embedding similarity does not equal relevance.
- **Trustworthy Generation (Pattern 11):** Provide retrieved chunks alongside generated claims; use citation mechanisms to ground generation. Make the LLM cite its sources.
- **Deep Search (Pattern 12):** Iterative retrieval — use initial retrieval to generate sub-questions, retrieve answers for each sub-question, synthesize final answer. Core to deep research workflows.
- **Relevant to Lyra §4.3:** Deep Search maps directly to Lyra's multi-hop research pipeline. Trustworthy Generation informs citation and grounding mechanisms.

---

## Chapter 5: Extending Model Capabilities (pp. 309–406)

**Patterns 13–16: Chain of Thought, Tree of Thoughts, Adapter Tuning, Evol-Instruct**

- **Key insight:** LLMs can generalize from training data but fail on industry-specific tasks not well covered in pretraining. These four patterns teach foundational models new capabilities — from simple prompting to full model customization.

### Pattern 13: Chain of Thought (CoT)

- **Key insight:** Adding "think step-by-step" (Zero-shot CoT) or providing worked examples (Few-shot CoT) unlocks latent reasoning. Auto-CoT dynamically selects examples from a question-answer store indexed by embedding similarity.
- **Critical distinction:** CoT shows logic (how to fish); RAG adds knowledge (gives a fish). They are complementary context engineering strategies.
- **Limitations:** CoT does not fix data gaps — if the model doesn't know the facts, reasoning steps will still hallucinate. In that case, add knowledge via RAG or multimodal context (e.g., a map image).
- **Anti-pattern:** Asking the model "why" after an answer does NOT get you the actual reasoning used — the explanation is likely hallucinated. The model is a black box; CoT must be embedded in the prompt, not post-hoc.
- **Best practice:** Use Few-shot CoT when Zero-shot fails; it demonstrates logic and forces the model to follow a template. Use Auto-CoT with a diverse question bank when scaling.

### Pattern 14: Tree of Thoughts (ToT)

- **Key insight:** ToT extends CoT by exploring multiple reasoning paths in parallel, evaluating each path at each step, and pruning poor candidates — effectively breadth-first search over reasoning. Treats reasoning as search, allowing more tokens to be allocated.
- **Best practice:** ToT is powerful when multiple approaches are possible and intermediate evaluation criteria exist. Use beam-search-like pruning to manage costs.

### Pattern 15: Adapter Tuning

- **Key insight:** Fine-tune small adapter layers (LoRA/QLoRA) instead of full model. Adapters add only ~1% of model parameters while achieving task-specific performance. This enables cost-effective customization when prompting alone is insufficient.

### Pattern 16: Evol-Instruct

- **Key insight:** Use an LLM to iteratively deepen and broaden instruction datasets: (1) In-Breadth evolving — add new topics/domains; (2) In-Depth evolving — add constraints, increase reasoning steps, increase complexity. Then filter poor-quality examples.
- **Best practice:** Evol-Instruct is how synthetic training data is created at scale. The quality filtering step is critical — use consistency checks (generate multiple answers, keep only consistent ones).

- **Relevant to Lyra §4.5:** CoT and ToT map to Lyra's reasoning and planning subsystems. Evol-Instruct informs Lyra's self-improvement data generation. Adapter Tuning informs fine-tuning strategy for domain-specific agent capabilities.

---

## Chapter 6: Improving Reliability (pp. 411–463)

**Patterns 17–20: LLM-as-Judge, Reflection, Dependency Injection, Prompt Optimization**

- **Key insight:** Reliability in GenAI requires systematic evaluation, self-correction loops, testable architecture, and prompt refinement. These four patterns form a comprehensive framework for dependability.

### Pattern 17: LLM-as-Judge

- **Key insight:** LLM-as-Judge provides scalable, customizable evaluation that bridges the gap between fully automated metrics (BLEU/ROUGE — fail to capture semantics) and human evaluation (expensive, biased, slow). Three approaches: Prompting, ML, Fine-tuning.
- **Best practices:**
  - Set temperature=0 for consistency. Use client-side or server-side prompt caching for repeatability.
  - Preprocess input to make it self-contained. Include conversation history when evaluating conversational answers.
  - Expand the calibration rubric with concrete descriptions of each score level (not just "1-5").
  - Coarse scores > fine-grained: 1-5 range OK; binary (yes/no) best. Multiple criteria > single score.
  - Use a DIFFERENT LLM for evaluation than generation (avoid self-bias — LLMs rate their own work highly).
  - LLM-as-Jury: multiple LLMs as different stakeholders evaluating responses.
  - Polling: multiple binary evaluations combined with jury for nuanced scoring.
- **Known biases:** Self-bias (favor own outputs), length bias (prefer longer text), positional bias (favor beginning/end over middle). Asking for explanations can INCREASE bias.
- **Leniency problem:** LLMs are like professors who give everyone A's and B's. Direct comparison (A vs B) > absolute scores. Group relative policy optimization (GRPO) normalizes scores by group average.
- **ML approach:** Train classifier on LLM-as-Judge rubric scores + real-world outcomes (e.g., sales data). The ML model discounts criteria the LLM is inconsistent on.
- **Fine-tuned approach:** Human experts annotate with same rubric; fine-tune a small model (PandaLM, PatronusAI) for lower cost and higher consistency.

### Pattern 18: Reflection

- **Key insight:** One of the four core agentic patterns (Andrew Ng). The system evaluates its own output, generates a critique, and regenerates. This is NOT the same LLM reflecting — evaluation should use a different model or tool. Single retry (exactly one round) is a common special case that avoids threshold-setting.
- **Best practices:**
  - Use a DIFFERENT LLM for evaluation to avoid self-bias (e.g., Gemini generates, Claude critiques).
  - The evaluator does not just score — it provides a critique explaining HOW the response falls short.
  - Multiple drafts + beam-search pruning: generate N drafts, evaluate all, prune weak ones, keep best after each iteration.
  - Log reviews to identify edge cases and failure modes over time.
- **Cost-quality tradeoff:** Each reflection round adds inference calls and tail latency. Heuristic: adjust reflection depth based on problem complexity, available time, and business impact. For code generation, reflection is cost-effective (cost of broken build >> cost of extra LLM call). For real-time chatbots, reflection may be too slow.
- **Critical:** Getting evaluation right is the most important part. Robust evaluation rubric is make-or-break.

### Pattern 19: Dependency Injection

- **Key insight:** When building chains of LLM calls, make each step independently testable by injecting mocks. This addresses: nondeterministic outputs, rapid model changes, LLM-agnostic requirements, and testability of multi-step chains.
- **Best practices:**
  - Define structured input/output types for each chain step (Pydantic dataclasses).
  - Write assertion-based tests on structured outputs (e.g., `assert len(critique.improvements) > 3`).
  - Mock individual LLM calls with deterministic responses for integration testing.
  - Test on MULTIPLE LLMs (same prompt may behave differently across providers).
- **Anti-pattern:** Vibe checking — eyeballing LLM output and saying "that looks right." Use structured output + assertions instead.

### Pattern 20: Prompt Optimization

- **Key insight:** Systematically refine prompts against a diverse input distribution using DSPy or similar frameworks. Treat prompts as optimizable parameters. Measure performance on a held-out eval set.
- **Best practices:**
  - Collect a diverse eval set FIRST, then optimize prompts against it.
  - Use LLM-as-Judge as the optimization metric.
  - Avoid overfitting to eval set — prompts brittle to model version changes.
  - Longer, more detailed prompts are more brittle across model upgrades.

- **Relevant to Lyra §4.7:** LLM-as-Judge maps to Lyra's evaluation framework. Reflection maps to self-correction and quality gates. Dependency Injection maps to harness testing architecture. Prompt Optimization maps to Lyra's prompt management and versioning.

---

## Chapter 7: Enabling Agents to Take Action (pp. 467–521)

**Patterns 21–23: Tool Calling, Code Execution, Multiagent Collaboration**

- **Key insight:** Tool Calling + Reflection = the threshold beyond which GenAI becomes truly agentic. Multiagent architecture is the path to handling complex real-world tasks through division of cognitive labor.

### Pattern 21: Tool Calling

- **Key insight:** LLMs emit special tokens to indicate function calls, client-side postprocessor invokes the function, results are fed back. This is an extension of Grammar (Pattern 2) — structured output as function calls.
- **Best practices:**
  - Use clear, self-descriptive function names and parameter docstrings. Models use these to decide when to call tools.
  - System prompt should describe policies on when to use each function (e.g., "search first, then book").
  - Include examples of valid inputs; use enum parameter types (Grammar pattern) for reliability.
  - Limit to 3–10 tools per agent (at time of writing, June 2025) — fewer tools = more accurate tool selection.
  - Don't make the model fill in information you already know deterministically (e.g., passenger details from session).
  - Return descriptive error messages to enable Reflection-based retry.
  - Use LLM-agnostic frameworks (PydanticAI, LangChain, LiteLLM) — NEVER use provider client API directly in development. Tool calling format varies across providers.
- **MCP (Model Context Protocol):** `@mcp.tool()` annotation standardizes tool definition. MCP servers expose tools via stdio or HTTP. Client uses `MultiServerMCPClient` to aggregate tools. ReAct agent (`create_react_agent`) reasons about when to call tools.
- **MCP limitations (May 2025):** No built-in authentication/authorization, mostly one-way communication (agent-to-agent needs A2A/ACP), streaming timeouts at 30-60s.
- **Prompt injection defenses for tool calling (Beurer-Kellner et al., 2025):**
  1. Action-Selector: only predefined actions, no feedback from tools back to agent
  2. Plan-Then-Execute: fixed plan, tool feedback inserted but plan not deviated from
  3. Map-Reduce: isolated subagents process untrusted data individually
  4. Dual-LLM: privileged LLM (plans + tools) + sandboxed LLM (processes untrusted data without tool access)
  5. Code-Then-Execute: LLM writes formal program that spawns unprivileged LLMs
  6. Context-Minimization: remove original user prompt from context during subsequent steps

### Pattern 22: Code Execution

- **Key insight:** When the action requires a DSL (SQL, DOT/Graphviz, Matplotlib, Mermaid), have the LLM generate code rather than calling tools. Execute in a sandbox with resource limits.
- **Best practices:** Validate code before execution (syntax check, static analysis). Send compiler/runtime errors back via Reflection for retry. Use containerized sandboxes (Docker) with CPU/memory/network/time limits. Code Execution works best with narrow DSLs that have parsers.

### Pattern 23: Multiagent Collaboration

- **Key insight:** Multiagent systems implement division of cognitive labor mirroring human organizations. Key advantage: horizontal scaling (adding agents) vs. vertical scaling (bigger models). Emergent capabilities arise from agent interactions.
- **Problem with single agents:**
  - Cognitive bottlenecks: finite context windows, struggles with multiple knowledge domains
  - Decreasing parameter efficiency: diminishing returns from larger models
  - Limited reasoning depth: sequential transformer inference limits parallel reasoning paths
  - Domain adaptation: general models lack specialized expertise; fine-tuning risks catastrophic forgetting
- **Three multiagent architectures:**
  1. **Hierarchical (executive-worker):** Task decomposition → delegation → integration. Simplest form: prompt chaining / sequential workflow. Clear lines of authority. Router pattern: classifier fronting a group of specialized workers.
  2. **Peer-to-peer (collaborative):** Agents as equals with voting/consensus mechanisms. CrewAI example: senior editor + content editor + research editor reach consensus through up to 3 discussion rounds.
  3. **Market-based (auction):** Tasks allocated via bidding. Sealed-bid or English auction. Agents bid based on capabilities and resource availability.
- **Key use cases:**
  - Parallel execution (most common, useful, least complex): process multiple files simultaneously
  - Complex reasoning: different agents for different domains/methodologies
  - Multistep problem solving: planning agent, execution agent, monitoring agent, adaptation agent
  - Adversarial verification: red team finds flaws, blue team defends/improves
  - Self-improving systems: evaluator agents assess performance, identify improvement areas
- **Human-in-the-loop:** One agent acts as human proxy; human resolves peer-to-peer/market conflicts. Human input can be introduced at any workflow point.
- **Anthropic's guidance (cited in Ch. 10):** "The most successful implementations use simple, composable patterns rather than complex frameworks."

- **Relevant to Lyra §4.8–§4.10:** Tool Calling maps to Lyra's plugin/action system. Code Execution maps to sandboxed compute. Multiagent Collaboration maps to Lyra's orchestration architecture (router, worker pools, adversarial verification).

---

## Chapter 8: Addressing Constraints (pp. 524–580)

**Patterns 24–28: Small Language Model, Prompt Caching, Inference Optimization, Degradation Testing, Long-Term Memory**

### Pattern 24: Small Language Model (SLM)

- **Key insight:** Three techniques to use smaller models without compromising quality unduly: Distillation (narrow knowledge scope), Quantization (lower precision weights), Speculative Decoding (small model proposes tokens, large model validates).
- **Distillation:** Teacher model (large) → Student model (small) via KL divergence loss. Student forgets irrelevant knowledge, focuses on domain-specific tasks. Iterative: can go from 12B → 1B over multiple rounds. Ensemble distillation: multiple teachers → one student.
- **Quantization:** FP32→INT8 (4x reduction), FP32→INT4 (8x reduction). QLoRA fine-tunes already quantized models. NF4 format optimized for language model weight distributions. BitsAndBytes library provides easy 4-bit quantization with minimal accuracy loss.
- **Speculative Decoding:** Small model generates tokens rapidly; large model verifies in parallel. Simple/common tokens accepted; complex tokens regenerated by large model. Achieves speedup because: (1) proposal tokens from small model are fast, (2) parallel verification is fast, (3) most tokens are simple. vLLM supports out of the box.
- **Concrete benchmark:** Gemma 3 27B → 3.26 tok/s; Gemma 3 1B → 8.82 tok/s (same hardware: 2×A100-40GB). After distillation + quantization: 1B model matches 27B quality on narrow task, inference drops from minutes to 19 seconds.
- **Key strategy:** Prototype with frontier model → log prompts → distill on logged distribution → quantize for deployment.

### Pattern 25: Prompt Caching

- **Key insight:** Cache repeated prompt prefixes (system prompts, tool definitions, static context) to reduce latency and cost. Most effective when many calls share the same prefix.
- **Best practices:** Structure prompts with static content first, dynamic content last. Cache across user sessions for shared system prompts. Use `@st.cache_resource` in Streamlit for UI-level caching.

### Pattern 26: Inference Optimization

- **Key insight:** Continuous batching, PagedAttention (vLLM), and speculative decoding maximize GPU utilization. vLLM/SGLang provide built-in benchmarking. Observability platforms include LangSmith and Phoenix (Arize).

### Pattern 27: Degradation Testing

- **Key insight:** Systematically test LLM application performance as conditions degrade — lower-quality models, reduced context windows, higher latency, adversarial inputs. Prepare graceful degradation strategies.
- **Best practice:** Establish performance baselines; test with progressively smaller/faster models; define SLAs for each degradation tier; implement automated monitoring and alerting.

### Pattern 28: Long-Term Memory

- **Key insight:** Four types of memory essential for LLM applications:
  1. **Working memory:** Current session messages. Implemented as token-budget-trimmed message list. Prune by token count, maintain valid conversation structure (start_on="human", include_system=True).
  2. **Episodic memory:** Relevant messages from previous sessions. Stored in persistent DB; retrieved via cosine similarity on embeddings. Filter by metadata (user_id, recency, topic).
  3. **Procedural memory:** System instructions, user profiles, preferences. Extract facts from conversations into profiles. Construct user-specific system prompts.
  4. **Semantic memory:** Content-based facts (not recency-based like episodic). Used for remembering trips, preferences, key facts about the user's world.
- **Implementation:** Mem0 framework — extracts entities/relationships from conversations using LLM, resolves contradictions, embeds into vector store (ChromaDB), retrieves via semantic search. Supports user_id for per-user memory, run_id for session-scoped memory. LLM preprocesses to keep personal facts/preferences/plans/relationships, ignore small talk/greetings/general knowledge.
- **Cost consideration:** Prepending full conversation history to each prompt is cost-prohibitive due to transformer quadratic scaling. Selective retrieval from long-term memory is essential.

- **Relevant to Lyra §4.2:** Long-Term Memory (all 4 types) maps directly to Lyra's memory subsystem. SLM techniques map to Lyra's model routing and cost optimization. Degradation Testing maps to Lyra's reliability engineering.

---

## Chapter 9: Setting Safeguards (pp. 584–619)

**Patterns 29–32: Template Generation, Assembled Reformat, Self-Check, Guardrails**

### Pattern 29: Template Generation

- **Key insight:** When human review of every generated output doesn't scale, pregenerate templates that humans review once, then do deterministic string replacement at inference time. Works when the number of combinations (destinations × package types × languages) is tractable.
- **Best practice:** Combine with ML for personalization — pregenerate templates, use ML propensity model to select which template to show which user.

### Pattern 30: Assembled Reformat

- **Key insight:** Separate content creation into two low-risk steps: (1) Assemble raw data using low-hallucination methods (databases, OCR, RAG, tool calling, template generation), (2) Reformat using LLM (rephrasing, summarizing — unlikely to introduce inaccuracies). Ground generation on verified facts.
- **When to use:** Template Generation is preferred (human review of all templates). Use Assembled Reformat when combinations exceed human review capacity. Validate results: extract data two ways for consistency; use LLM-as-Judge to verify generated content retains raw data.

### Pattern 31: Self-Check

- **Key insight:** Use token logprobs to detect hallucinations. When model is confident, winning token probability is near 100%. When hallucinating, probability drops — multiple competing tokens. Four detection approaches:
  1. **Identify tokens of interest:** Only check logprobs on known key positions (structured output)
  2. **Sample generated sequences:** Multiple generations; compare if they agree on answer
  3. **Normalize statistics:** Perplexity = e^{−1/N Σ logits_i}; lower = more confident
  4. **Build ML model:** Token probabilities + embedding distances + perplexity + contextual features → trained on your data
- **Concrete data:** Vectara hallucination rates (Dec 2024 → Apr 2025): best LLM 1.3% → 0.7%; 25th best 4.1% → 2.4%. Visual extraction accuracy: 90-97% (3-10% hallucination rate). Hallucination compounds in multi-step chains.
- **Best practice:** Self-Check is most robust with an ML model trained on your specific use case. For RAG, contradictory retrieved chunks produce token probabilities indicating multiple generation paths.

### Pattern 32: Guardrails

- **Key insight:** A comprehensive guardrail layer intercepts inputs, outputs, context, and tool parameters at multiple points in the conversation flow. Five protection domains: Security (prompt injection, jailbreaking), Data Privacy (PII, trade secrets), Content Moderation (toxic/harmful content), Hallucination (accuracy, truthfulness), Alignment (policy, brand voice, fairness).
- **Implementation:** Preprocessing (input filtering) + postprocessing (output filtering). Use LLM-as-Judge with a guardrail-specific prompt as a starting point. Input guardrails should run in parallel with the main LLM call (asyncio.gather) to avoid latency impact.
- **Chapter 10 implementation pattern:**
  - `InputGuardrail` class: condition string → LLM-as-Judge prompt → bool output (SMALL_MODEL for cost)
  - Raises `InputGuardrailException` if unacceptable
  - Run guardrail + main agent call simultaneously via `asyncio.gather`
  - Log all guardrail results to `guards.log` for monitoring, fine-tuning, and attack pattern detection
- **Systematic monitoring:** Degradation testing (Pattern 27), guardrail logging, access controls, audit logging, human-in-the-loop checkpoints.

- **Relevant to Lyra §4.7:** Guardrails maps to Lyra's safety subsystem. Self-Check maps to hallucination detection. Template Generation and Assembled Reformat map to controlled-output patterns. Guardrail logging maps to Lyra's observability.

---

## Chapter 10: Composable Agentic Workflows (pp. 623–645)

**No new patterns — synthesis of all 32 patterns into a working multiagent application.**

- **Key insight:** The most effective agentic implementations use simple, composable patterns rather than complex frameworks (Anthropic's guidance). This is the Unix philosophy applied to agents.
- **System architecture (5 components):**
  1. **Agent patterns (per step):** Each workflow step implemented independently. Mixes CoT, RAG, Tool Calling, Reflection, Self-Check, Template Generation, Assembled Reformat as needed. Different agents can use different frameworks.
  2. **Multiagent architecture:** Agents orchestrated in agent mode (async sequential: find_writer → write_about → panel_review → revise_article) or copilot mode (each Streamlit page invokes its agent). Direct control logic > framework magic.
  3. **Governance, monitoring, security:** Input guardrails via LLM-as-Judge. All guardrails logged to guards.log. Degradation testing + systematic monitoring. Access controls, policy management, audit logging, human-in-the-loop checkpoints.
  4. **Learning pipeline:** Log human feedback (user overrides AI recommendations) from copilot mode → use for continuous improvement. Store modification instructions in long-term memory for future runs. Every user correction is training data.
  5. **Data creation/curation:** Log prompts and human edits → use as training data for model distillation and fine-tuning.
- **Model routing strategy:** Three LLM tiers: BEST_MODEL (Gemini 2.5 Pro for quality-critical), DEFAULT_MODEL (Gemini 2.5 Flash for standard), SMALL_MODEL (Gemini 2.5 Flash Lite for guardrails/classification).
- **Context and latency management:** Prompt templating via Jinja2 for different installations. `@st.cache_resource` for prompt caching at UI level. Async/await for concurrent agent execution. Long-term memory (Mem0) for persistent user instructions.
- **Copilot → Agent progression:** Start in copilot mode (human-in-the-loop), collect feedback, eventually graduate to agent mode (fully autonomous). Human feedback collection must be unobtrusive — good UX design essential.
- **Prompt injection defense:** Guardrail runs in parallel with main call. If guardrail fails, second call is terminated. Uses SMALL_MODEL for cost efficiency.

- **Relevant to Lyra §4.10:** Composable patterns = Lyra's architectural philosophy. Learning pipeline = Lyra's self-improvement. Model routing = Lyra's cost-aware model selection. Copilot-to-agent progression = Lyra's deployment strategy.
