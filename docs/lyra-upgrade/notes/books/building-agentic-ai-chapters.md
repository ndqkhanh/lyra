# Building Agentic AI — Chapter Notes

**Author:** Sinan Ozdemir | **Year:** 2025 (Early Release) | **Publisher:** Pearson

**Core Thesis:** Production AI agents are built through systematic experimentation across the full stack — from prompt engineering and retrieval to multi-agent architectures, fine-tuning, and model optimization. There is no single "best" approach; the right design emerges from rigorous evaluation of accuracy, latency, cost, calibration, and privacy trade-offs. Workflows and agents are complementary, not competing, paradigms.

**Target Audience:** Practitioners, engineers, and data scientists with Python/ML familiarity who want to build production AI systems, not just use existing products.

---

## Chapter 1: An Introduction to AI, LLMs, and Agents

- **Key insight:** The fundamental distinction between workflows (predefined pathways with clear start/stop triggers) and agents (autonomous LLMs with tools that choose their own paths). Both have roles in production systems.
- **Best practices:**
  - Prompt order matters: put asks + guardrails at the top, static documentation/in-context examples next, dynamic content (retrieved docs) at the bottom
  - Few-shot examples should go in the system prompt, not user messages, because foundation labs train LLMs specifically to follow system prompts
  - Use temperature ≤ 1.0; lower values = more deterministic outputs; set top_k=1 for true determinism
  - Place static content before dynamic content to preserve prompt caching (cache breaks at the first different token)
  - Cache hits can reduce cost by 40-50% and latency by similar margins for non-reasoning models
- **Anti-patterns:**
  - Relying on agents when a deterministic workflow would suffice
  - Ignoring positional bias (LLMs pay more attention to beginning and end of prompts — the "lost in the middle" problem)
  - Assuming reasoning models benefit from prompt caching (they generally don't, due to non-deterministic reasoning tokens)
- **Relevant to Lyra §4.x:** Agent architecture fundamentals, ReAct pattern, workflow-vs-agent decision framework

---

## Chapter 2: First Steps with LLM Workflows

- **Key insight:** Production RAG systems require careful state management. The jump from stateless to stateful RAG (conversational memory) transforms a one-shot tool into an assistant-like system. LangGraph's `MemorySaver` + `interrupt` pattern provides human-in-the-loop capability with a single line of code for checkpointing.
- **Best practices:**
  - Use structured outputs (Pydantic models) for reliable parsing of LLM responses in workflows
  - Always use the same embedder for indexing AND retrieval — embedding models are not interchangeable
  - Store metadata (db_id, source, etc.) alongside embeddings to enable filtered retrieval
  - Match state keys with node output keys for maintainability, even though not technically required
  - Temperature=0 for SQL/code generation workflows to maximize consistency
  - Use HNSW with cosine distance for vector databases as a sensible default
- **Anti-patterns:**
  - Embedding evidence without metadata — makes filtered/per-database retrieval impossible
  - Resetting state on every invocation when multi-turn conversation is expected
  - Not handling tool execution errors (SQL failures must be piped back to the LLM, not silently swallowed)
- **Relevant to Lyra §4.x:** RAG pipeline design, state management, conversational memory patterns

---

## Chapter 3: AI Evaluation Plus Experimentation

- **Key insight:** Evaluation is multidimensional and task-specific. The four task categories (generation, multiple-choice, free-text response, understanding tasks like embedding/classification) require different metrics. No single metric suffices; use at least precision, recall, MRR, accuracy, cost, and latency together.
- **Best practices:**
  - Semantic few-shot learning (retrieving similar examples via embedding match) beats random few-shot by ~20% accuracy
  - Chain-of-thought + 3 semantically-similar examples can lift accuracy 35%+ over zero-shot baselines
  - 3-7 few-shot examples is the sweet spot; more examples risk conflicting information
  - Test embedders across all sub-domains (database-by-database) — the best embedder varies per domain
  - Use a different LLM family for grading rubrics to avoid subliminal self-bias
  - Prompt chaining (chunk then summarize) beats single-shot summarization for long documents, at the cost of higher latency and token usage
- **Anti-patterns:**
  - Evaluating retrieval with a single metric (precision alone misses recall failures; MRR alone misses multi-hop needs)
  - Assuming one embedder is universally best — Cohere V4 won overall but V3 was better for some databases
  - Using the agent's own LLM to grade its responses — use a mid-tier LLM from a different provider
- **Numbers:**
  - Best reported accuracy on BIRD-SQL benchmark: ~75% (SOTA), baseline workflow with GPT-4o-mini: ~57%
  - Gemini 2.5 Pro: 57.5% accuracy but 28x higher cost than GPT-4.1-Mini
  - Prompt chaining increased summary quality across measured metrics for Llama 4 Scout
- **Relevant to Lyra §4.x:** Eval harness design, rubric-based grading, multi-metric evaluation framework

---

## Chapter 4: First Steps with AI Agents and Multi-Agent Workloads

- **Key insight:** Agents are less code but more cost and latency compared to equivalent workflows. The SQL agent achieved similar accuracy (~51%) to the RAG workflow but with higher median cost and latency. The choice between them depends on whether you need flexibility (agents) or efficiency (workflows).
- **Best practices:**
  - Build both workflow AND agent versions, benchmark them head-to-head on the same dataset before deciding
  - Error handling in tool calls is critical — the LLM cannot see tool execution tracebacks; pipe them back as tool response messages
  - Use checkpointer/MemorySaver for stateful agents (conversational memory) — a one-line solution in LangGraph
  - Multi-agent systems resemble micro-service architectures: isolate concerns, minimize overlap, experiment independently
  - Use smaller/cheaper LLMs for agents with low false-positive costs (e.g., lead generation), larger/slower ones for high-stakes decisions (e.g., qualification)
  - MCP (Model Context Protocol) standardizes tool discovery across frameworks and providers — use it for portable tool definitions
  - Give agents write-access tools (e.g., log_evidence) to enable learning over time — Otto's notebook pattern
- **Anti-patterns:**
  - Giving agents too many tools without clear descriptions — even one bad tool description derails entire agent runs
  - Assuming agents will always use provided tools — GPT-4.1 ignored its database tool ~100% of the time when not explicitly prompted
  - Single-agent for complex multi-step pipelines when separation of concerns would reduce regression risk
- **Numbers:**
  - Agent vs. workflow accuracy: ~51% vs similar (both on GPT-4.1-Mini)
  - Agent cost/latency higher due to extra LLM invocations for tool planning
  - With synthetic similar questions + Otto's notebook: accuracy improved from 37.7% to 67.2% over time
- **Relevant to Lyra §4.x:** Multi-agent design, MCP integration, tool design, agent-vs-workflow decision matrix, LangSmith observability

---

## Chapter 5: Enhancing Agents with Prompting, Workflows, and More Agents

- **Key insight:** A single sentence in the system prompt ("ALWAYS USE the BM25 tool before answering") can increase accuracy by ~50% (GPT-4.1: 47.8% → 70.7%). Prompt engineering agents is just as impactful as prompt engineering LLMs. Hybrid agentic workflows (rigid structure + agentic steps) often outperform pure agents or pure workflows.
- **Best practices:**
  - BM25 keyword search still beats neural embeddings for industry jargon and policy documents — test both
  - Planning + Re-planning + Reflection components dramatically improve complex multi-step tasks (deep research)
  - Use large/expensive LLMs for planning, smaller/cheaper LLMs for step execution (plan-execute pattern)
  - Supervisor (tool-calling) pattern: supervisor treats sub-agents as tools, delegates tasks with limited context, waits for completion
  - Network-based multi-agent: handoff tools allow agents to route conversations to each other — flexible but can get messy
  - For multi-agent: only use networking if agents truly need each other; otherwise use supervisor delegation
- **Anti-patterns:**
  - Relying on LLMs to self-determine when to use tools — GPT-4.1 was "smug" enough to skip the database 100% of the time without explicit prompting
  - Assuming larger models follow instructions better — GPT-4.1-Nano used tools 31/232 times without prompting vs. GPT-4.1's near-zero
  - Network-based architectures without guardrails — agents may hand off unnecessarily or create loops
- **Numbers:**
  - GPT-4.1 (no prompt to use tool): ~48% accuracy. With "ALWAYS USE tool": ~71% accuracy
  - GPT-4.1-Nano: ~20% failure to use tool even when explicitly told to do so (instruction adherence gap)
  - Positional bias in tool selection: LLMs favor first 3 tools by ~0.2% over expected selection rate
- **Relevant to Lyra §4.x:** Hybrid agentic workflows, supervisor pattern, deep research architecture, tool selection design

---

## Chapter 6: Moving Beyond Natural Language: Multimodal and Coding AI

- **Key insight:** Five strategies for multimodal AI: (1) embed modalities in same vector space (CLIP), (2) map from one mode to another (diffusion), (3) ground modalities in a primary modality (text as the hub), (4) jointly model modes (ViLT, LLaVA, Moondream), (5) handle modalities separately (coding agents calling separate models). Most production systems combine multiple strategies.
- **Best practices:**
  - Two-stage retrieval for multimodal search: CLIP (fast embedding similarity) → ViLT (cross-encoder re-ranking) balances speed and accuracy
  - Coding agents (LLMs that write executable code) can call multiple tools in a single code block, reducing LLM invocations
  - Use custom code markers (e.g., `<<PYTHON_CODE>>`) instead of backticks to avoid collision with LLM's explanation training
  - The "ground everything to text" approach (STT → LLM → TTS) remains the most production-ready for voice despite emerging audio-to-audio models
  - Diffusion LLMs (dLLMs) like Mercury offer 6-10x token generation speed vs. autoregressive models but lower benchmark performance
- **Anti-patterns:**
  - Giving coding agents unrestricted file system access without guardrails — they can delete/create files
  - Assuming CLIP-style similarity alone is sufficient for nuanced queries (it misses cross-modal joint reasoning)
  - Using HuggingFace Spaces as production tools (rate limits, not designed for production throughput)
- **Numbers:**
  - Mercury dLLM: ~620 tokens/sec vs GPT-4.1: ~62 tps, GPT-4.1-Nano: ~121 tps
  - Moondream: 1.42B param VQA model, runs on edge devices, single-shot (no chat)
- **Relevant to Lyra §4.x:** Multimodal strategy, coding agent pattern, image retrieval + re-ranking, voice grounding architecture

---

## Chapter 7: Reasoning LLMs and Computer Use

- **Key insight:** Reasoning models are NOT a universal upgrade. Across multiple benchmarks (HLE, MathQA, computer-use coordinate tasks), "more thinking" did not reliably yield better performance and always increased latency and cost. Treat reasoning as an experimental hyperparameter, not a default setting.
- **Best practices:**
  - Context engineering framework: tool integration + prompt engineering + memory management + retrieval — the four pillars of giving an LLM everything it needs
  - Turn reasoning OFF for simple QA, retrieval-first answers, and high-throughput endpoints
  - Turn reasoning ON for decomposition-heavy tasks (multi-step math, planning, multi-tool orchestration, screen coordinate tasks)
  - Use reasoning models for ReAct agents to get interleaved chain-of-thought before each tool call (transparency + potentially better accuracy)
  - Combine vision + grounded element lists for computer use rather than relying on either approach alone
  - When reasoning helps: coordinate tasks improved 2.4% with Opus 4.1 but latency increased 96.5%
- **Anti-patterns:**
  - Defaulting to high reasoning effort — on MathQA, Opus performed BEST with reasoning turned OFF
  - Expecting reasoning to solve calibration problems — Claude/Opus with reasoning still gave wrong birthdays at 70%+ confidence
  - Ignoring diminishing returns — when benchmarks are near ceiling, reasoning yields fewest benefits and may hurt performance
- **Numbers:**
  - HLE benchmark: no correlation between reasoning effort and accuracy for GPT-o4-mini and Claude Sonnet 4
  - MathQA: Claude Opus 4 with no reasoning outperformed all reasoning levels
  - Computer use coordinate task: reasoning improved Opus 4.1 score by 2.4% but nearly doubled latency
- **Relevant to Lyra §4.x:** Reasoning model routing, context engineering framework, computer-use architecture, seven pillars of intelligence

---

## Chapter 8: Fine-Tuning AI for Calibrated Performance

- **Key insight:** Fine-tuning is not just about accuracy — it is about calibration (making confidence scores trustworthy). A well-calibrated model's stated 80% confidence should mean it is correct ~80% of the time. Fine-tuned classifiers drastically outperform prompted classifiers on calibration (ECE), even when accuracy is similar.
- **Best practices:**
  - For classification tasks: fine-tune an autoencoding model (ModernBERT) instead of prompting a generative LLM — similar accuracy, 1/5 the cost, forced output classes, better calibration
  - Use ECE (Expected Calibration Error) alongside accuracy — a model can be accurate but poorly calibrated (overconfident)
  - For domain adaptation: mix unstructured pre-training data with conversational data to prevent catastrophic forgetting
  - Use LoRA + 4-bit quantization for efficient fine-tuning (1.42B trainable params from 9.61B total)
  - Set embedding learning rate 2-10x lower than overall learning rate — embedding weights impact all attention calculations
  - Lower WER (token-level) generally means better calibration at the generation level
  - Self-hosted models (ModernBERT) cost ~$1 to fine-tune vs. $122 for GPT-4.1 on the same classification task
- **Anti-patterns:**
  - Using generative LLMs for classification when a fine-tuned classifier would be cheaper, faster, and better calibrated
  - Trusting LLM self-reported confidence ("I'm 85% sure") — these are nearly uncorrelated with correctness in free-text generation
  - Including system prompts in fine-tuning data when the fine-tuning should eliminate the need for them (wastes tokens/cost)
- **Numbers:**
  - Fine-tuned classifier accuracy: ~73% across all models (GPT-4.1, GPT-4.1-Nano, ModernBERT)
  - ModernBERT ECE: 1.7x lower (better calibrated) than GPT-4.1 despite 1.007x lower accuracy
  - Fine-tuning cost: GPT-4.1 = $122, GPT-4.1-Nano (no system prompt) = $7.33, ModernBERT = ~$1
  - Domain-adapted Qwen3-8B: 6.5% → 50%+ accuracy on policy QA, matching GPT-4.1-Nano with retrieval
  - Quantization accuracy drop: at most 10-15% on benchmarks, often recoverable via fine-tuning
- **Relevant to Lyra §4.x:** Calibration metrics, fine-tuning strategy, domain adaptation, model selection framework (accuracy/cost/speed/privacy)

---

## Chapter 9: Optimizing AI Models for Production

- **Key insight:** Production optimization is a multi-dimensional trade-off space (speed, cost, accuracy, privacy). No single technique solves everything. The VRAM formula (params × bits/8 × 1.2) gives a quick deployment feasibility estimate. Speculative decoding, quantization, distillation, and Matryoshka embeddings are complementary techniques, not alternatives.
- **Best practices:**
  - Quantization (FP32→INT8 or NF4) reduces memory ~4x with ≤15% accuracy drop; pair with fine-tuning to recover
  - Speculative decoding works best when the assistant model is domain-aligned with the base model; unaligned assistants can SLOW generation (as seen with Airbnb policy domain)
  - Matryoshka embeddings: train on multiple truncated dimensions simultaneously; 64-dim embeddings can match 1024-dim performance at ~1/20 the storage
  - For voice bots: benchmark STT+TTS combinations end-to-end (WER + latency), not individually — Groq's distil-whisper was 7.5x faster than GPT-4o-mini TTS with similar accuracy
  - Use model-agnostic agent frameworks (coding agents with custom `<<PYTHON_CODE>>` markers) to hot-swap LLMs without tool-calling requirements
  - For distill + quantize: distill first to create a smaller model, THEN quantize for maximum compression
- **Anti-patterns:**
  - Using speculative decoding with misaligned assistant models — Airbnb policy prompts ran SLOWER with assistance because the base model kept correcting hallucinations
  - Deploying without considering privacy trade-offs — closed-source APIs send data off-site; self-hosted models keep data in-VPC
  - Assuming MLM pre-training always helps embedding fine-tuning — for Les Misérables, it added no benefit because no new jargon was introduced
- **Numbers:**
  - VRAM for 8B model in FP16: ~17.88 GB; in 4-bit: ~6 GB (75% reduction)
  - 1M vectors at 64-dim: ~1/20 the disk space of 1024-dim
  - Speculative decoding speed-ups: 10-25% for aligned domains (reciting, math, general knowledge); slowdown for misaligned domains (Airbnb policy)
  - Groq distil-whisper STT latency: ~0.02 sec/word at ~95% accuracy
- **Relevant to Lyra §4.x:** Model optimization pipeline, voice bot architecture, embedding optimization, speculative decoding for harness engineering
