# Build an Advanced RAG Application (From Scratch) — Best Practices Playbook

**Source:** Hamza Farooq, *Build an Advanced RAG Application (From Scratch)*, MEAP V04, Manning Publications, 2026
**Target Audience:** Lyra architecture team building a production-grade multi-agent AI harness

---

## Practice 1: Separate Routing from Retrieval — The Agentic Router Pattern

- **What:** Insert an LLM-powered classification step at the front of every query pipeline that analyzes user intent and dynamically directs each request to the most appropriate retrieval backend (domain-specific vector collection, live web search, structured database, etc.). The router outputs structured JSON with the route label, a one-sentence justification, and optionally a direct answer for trivially simple queries.
- **Why:** Embedding models measure textual similarity but have no concept of domain boundaries, document authority, or information freshness. A unified vector index causes cross-domain contamination (financial vocabulary leaking into technical search results), authority blindness (blog posts treated equal to official filings), and precision degradation (each new domain added increases the noise floor for ALL queries). Separating routing (LLM reasoning about intent) from retrieval (vector search within a domain-specific collection) gives you the best of both approaches: intelligent classification followed by precise, focused search.
- **Lyra route:** §4.05 (Router)
- **Source:** Chapter 7, Section 7.2

---

## Practice 2: Semantic Caching as a First-Class Architectural Component

- **What:** Build a semantic cache that stores query-answer pairs in a FAISS vector index, matching incoming queries against cached ones using embedding similarity (L2 distance threshold of 0.2, corresponding to cosine similarity ~0.98). Include a keyword-based time-sensitivity filter that bypasses the cache entirely for queries containing temporal indicators ("today", "current", "latest", "this week", etc.). Cache check runs first in the pipeline — on hit, the entire downstream pipeline is skipped, returning results in 10-50ms.
- **Why:** Enterprise query patterns are highly repetitive (teams ask variations of the same questions). Exact-match caching fails for natural language because users phrase identical concepts differently. Semantic caching at the meaning level captures "What was Uber's revenue in 2021?" and "How much money did Uber make in 2021?" as the same query. Measured results: 12.4x speedup (3.84s → 0.31s), 40-60% LLM API cost reduction at enterprise scale. The time-sensitivity filter is critical — returning stale data is worse than the cost of a fresh retrieval. Use keyword-based detection (not LLM) for time-sensitivity to keep cache lookups fast (microseconds, not seconds).
- **Lyra route:** §4.02 (Memory)
- **Source:** Chapter 7, Section 7.3

---

## Practice 3: Query Rewriting + Sub-Query Decomposition as Pre-Retrieval Gates

- **What:** Run every user query through two pre-retrieval transformation steps. (1) Single-query rewriting: an LLM call (temperature=0, max_tokens=200) that expands abbreviations, makes implicit references explicit using the last 3 conversation turns, and adds domain specificity WITHOUT inventing constraints the user didn't express. (2) Sub-query decomposition: an LLM call that detects compound multi-part questions and splits them into 2-4 atomic, independently answerable sub-queries. Simple queries pass through unchanged.
- **Why:** Users write bad queries — casually, with abbreviations, implicit context, and compound intentions. Embedding models produce bad embeddings from bad queries (a vague multi-intent query produces an averaged vector that is not close to any specific relevant chunk). Query rewriting fixes the query BEFORE it reaches the embedding model, improving retrieval precision with zero changes to the index. Sub-query decomposition ensures each distinct information need gets its own focused embedding, route, and retrieval, rather than producing a mediocre "general" result. Overhead: 200-400ms, offset by reduced re-query rate.
- **Lyra route:** §4.03 (Context)
- **Source:** Chapter 7, Section 7.4

---

## Practice 4: Partition Knowledge Bases by Domain, Not by Document Type

- **What:** Instead of embedding all documents into a single vector index, create purpose-built collections per knowledge domain (e.g., separate Qdrant collections for API documentation, financial filings, HR policies, legal contracts). Add a live web search route as a mandatory escape hatch for queries outside all internal collections. Routes should map to fundamentally different retrieval STRATEGIES, not just different topics — a vector DB route, a structured SQL route, a graph DB route, a web search route are architecturally distinct and each warrants its own path.
- **Why:** Cross-domain contamination, authority blindness, and scalability degradation are inherent to unified indexes. With partitioned collections, adding a new domain means creating a new collection and updating the router prompt — existing collections and their retrieval precision remain completely unaffected. The web search escape hatch ensures no query goes unanswered, preventing the system from hallucinating from irrelevant internal documents.
- **Lyra route:** §4.04 (Retrieval), §4.05 (Router)
- **Source:** Chapter 7, Section 7.2.1

---

## Practice 5: Recursive Chunking with Overlap for Document Indexing

- **What:** Use recursive chunking as the default document splitting strategy. The algorithm tries natural semantic boundaries hierarchically: paragraphs (\n\n) → sentences (\n) → phrases (. or ,) → words (space) → character-level brute-force fallback. Set chunk_size based on embedding model context window (e.g., 1,024 characters for Nomic with 8,192 token limit). Add 50-character overlap from the previous chunk to preserve cross-chunk context continuity.
- **Why:** Embedding models have fixed context windows (8,192 tokens for Nomic). Documents exceeding this limit have text silently truncated — information is lost. Fixed-size chunking breaks semantic coherence mid-sentence. Recursive chunking preserves meaning by respecting natural linguistic boundaries, falling back to brute-force only when necessary. The overlap ensures that sentences spanning chunk boundaries remain contextually connected in both chunks.
- **Lyra route:** §4.04 (Retrieval)
- **Source:** Chapter 6, Section 6.3

---

## Practice 6: Production Vector Database Over In-Memory FAISS

- **What:** Migrate from FAISS (suitable for prototyping and small-scale caches) to a production vector database (Qdrant recommended) for the primary document index. Production vector DB requirements: persistent storage, concurrent access, metadata filtering (filterable HNSW), hybrid search (sparse + dense vectors), multi-tenant partitioning, quantization for memory efficiency.
- **Why:** FAISS is an in-memory library, not a database. It lacks persistence (data lost on restart), concurrent access (single process), metadata filtering (pure vector search), and access control. Qdrant's filterable HNSW implementation integrates metadata filtering directly into the search algorithm rather than post-processing, enabling city-filtered hotel search, year-filtered paper search, and permission-filtered enterprise document search without performance degradation. Core written in Rust for reliability.
- **Lyra route:** §4.04 (Retrieval)
- **Source:** Chapter 6, Section 6.2; Qdrant spotlight by Andre Zayarni (CEO)

---

## Practice 7: Component-Level RAG Evaluation with RAGAS

- **What:** Evaluate RAG systems using the RAGAS framework which measures four core metrics. Retrieval quality: Context Precision (are top results relevant?) and Context Recall (are all relevant docs found?). Generation quality: Faithfulness (are all claims grounded in the retrieved context?) and Answer Relevancy (does the response address the query?). Evaluate components independently before end-to-end testing. Use LLM-as-Judge for faithfulness scoring — more reliable than rule-based classification models for hallucination detection.
- **Why:** Traditional NLP metrics (BLEU, ROUGE) measure surface text similarity and fail to capture factual accuracy, context relevance, and hallucination. RAGAS is reference-free (no expensive human-annotated ground truth needed) and LLM-judged (captures nuanced quality assessment). Component-level evaluation enables targeted optimization: fix retrieval precision without touching generation, or fix generation faithfulness without rebuilding the index. Use synthetic data generation for creating comprehensive test datasets from existing documents.
- **Lyra route:** §4.16 (Reliability)
- **Source:** Chapter 6, Section 6.5

---

## Practice 8: The Full Enterprise RAG Pipeline Lifecycle (9-Step Sequence)

- **What:** Process every query through a fixed 9-step pipeline: (1) Raw query arrives, (2) Semantic cache check → return immediately on hit, (3) Time-sensitivity filter → bypass cache if temporal, (4) LLM route classification, (5) Query rewrite with conversation history, (6) Decompose if compound, (7) Retrieve from target collection(s), (8) Synthesize grounded cited response, (9) Cache result. Return a dictionary with the full audit trail: original query, rewritten query, sub-queries, route, reason, cache hit flag, time sensitivity flag, answer.
- **Why:** Each step addresses a distinct failure mode of naive RAG. The fixed sequence ensures the most expensive components (LLM routing, generation) only run on cache misses — the system gets faster and cheaper the longer it operates (cache warms up). The audit trail dictionary is essential for debugging (why was this query routed here?), compliance (what information was used to answer this?), and continuous improvement (which steps are failing?). The pipeline is modular — you can add or remove steps without restructuring.
- **Lyra route:** §4.01 (Orchestration/Architecture), §4.16 (Reliability/Observability)
- **Source:** Chapter 7, Section 7.5

---

## Practice 9: Structured Output via Prompt Engineering (Not JSON Mode)

- **What:** For classification/routing tasks, embed the expected JSON schema directly in the system prompt rather than relying on API-level JSON mode or function calling. Include a regex-based JSON extraction step as a safety net (handles markdown code fences and surrounding explanatory text). Always include a parse-failure fallback that routes to the safest default (e.g., WEB_SEARCH) rather than crashing the pipeline.
- **Why:** Prompt-embedded schemas are self-documenting, work consistently across model versions, and allow you to test and iterate on routing logic without changing application code. Regex extraction handles the real-world case where models sometimes wrap JSON in markdown formatting. JSON mode and function calling create harder dependencies on specific API features that may change. The fallback-on-failure pattern ensures the system always returns a response rather than throwing an exception — critical for production reliability.
- **Lyra route:** §4.05 (Router), §4.07 (Plugins/Tools)
- **Source:** Chapter 7, Section 7.2.2

---

## Practice 10: Model Selection by Task Profile

- **What:** Route different pipeline stages to different models based on task requirements. Deterministic tasks (routing, query rewriting, validation): use temperature=0 with any capable model (GPT-4o, Claude). Creative generation (final response synthesis): use temperature=0.7-0.9 with top-p sampling. Trivially simple tasks: consider whether an LLM call is even needed (keyword-based time-sensitivity detection instead of LLM classification). For cost optimization, use a unified API gateway (OpenRouter pattern) with model fallbacks.
- **Why:** Not every pipeline stage needs a frontier model. Routing and rewriting benefit from determinism (temperature=0) but don't need creative capacity. Generation needs nuance but should be grounded with citations. Some tasks (time-sensitivity keyword matching) need zero LLM calls — microseconds vs. seconds of latency. The OpenRouter pattern provides model fallbacks and cost optimization through a single API. Model selection is a cost and latency lever, not just a quality lever.
- **Lyra route:** §4.01 (Architecture), §4.05 (Router)
- **Source:** Chapter 5, Section 5.4; Chapter 7 patterns throughout

---

## Practice 11: Guardrails and Memory as Non-Negotiable Production Requirements

- **What:** Input guardrails: validate and sanitize incoming queries, detect prompt injection, filter harmful/out-of-scope requests, enforce organizational policies BEFORE the query reaches retrieval. Output guardrails: validate generated responses for sensitive information leakage, compliance violations, harmful content. Memory: short-term (conversation thread tracking for follow-up resolution), long-term (user preferences, past interactions, learned patterns for personalization).
- **Why:** In regulated industries (finance, healthcare, legal), guardrails are not optional — they are foundational requirements without which deployment is impossible. Memory transforms stateless Q&A into coherent conversations: without it, every follow-up like "What about last quarter?" requires the full context to be restated, creating frustrating user experiences. These are previewed in Chapter 7 and described as the focus of Chapter 8.
- **Lyra route:** §4.17 (Safety), §4.02 (Memory)
- **Source:** Chapter 7, Section 7.1; Chapter 8 preview

---

## Practice 12: Streaming Responses with Source Attribution

- **What:** Stream LLM responses token-by-token for immediate user feedback. Structure the generation prompt to require numbered citations [1][2][3] referencing specific retrieved context chunks. Start responses directly with the answer (no salutations like "Sure, here is..."). Return both the polished streamed response and the raw sources for transparency.
- **Why:** Streaming eliminates perceived latency — users see content appearing immediately rather than waiting 3-5 seconds for the full generation. Numbered citations serve dual purpose: (1) they constrain the model to generate traceable responses grounded in retrieved context, and (2) if retrieved chunks don't contain relevant information, the model struggles to produce convincing citations, making it more likely to acknowledge gaps rather than hallucinate. The dual return (response + sources) enables downstream verification and user-facing source links.
- **Lyra route:** §4.01 (Architecture), §4.04 (Retrieval)
- **Source:** Chapter 6, Section 6.1; Chapter 7, Section 7.2.2

---

## Practice 13: OpenRouter-Style Unified LLM Gateway

- **What:** Use a unified API gateway (OpenRouter pattern) that provides a single interface to multiple LLM providers (OpenAI, Anthropic, Mistral, open-source models). Benefits: standardized API access, cost optimization across providers, model fallbacks (if one model fails, the next in line takes over), free-tier usage for certain models, and the ability to let users choose preferred models without application code changes.
- **Why:** Single-provider lock-in creates risk (API outages, pricing changes, model deprecation). A unified gateway provides operational resilience through fallbacks and cost optimization through provider competition. Critically, it enables the model-selection-by-task pattern: use GPT-4o for routing classification, Claude for nuanced generation, and free-tier models for low-stakes tasks — all through the same API interface.
- **Lyra route:** §4.01 (Architecture), §4.05 (Router)
- **Source:** Chapter 6, Section 6.1

---

## Practice 14: Bi-Encoder Search + Cross-Encoder Re-Ranking

- **What:** Use a bi-encoder architecture for initial retrieval (query and documents encoded separately, compared via cosine similarity — fast and scalable). Apply a cross-encoder as a re-ranking step on the top-k results (query and document processed jointly, capturing fine-grained interaction — slower but more accurate). This two-stage approach balances speed and precision.
- **Why:** Bi-encoders alone miss nuanced relevance (same embedding dimension must represent both query intent and document content). Cross-encoders alone are too slow for large-scale search (every query-document pair requires a full forward pass). The two-stage approach gives you the best of both: fast bi-encoder retrieval narrows the search space to top-k candidates, then the cross-encoder re-ranks for precision. This is the recommended pattern for production semantic search.
- **Lyra route:** §4.04 (Retrieval)
- **Source:** Chapter 4, Section 4.3

---

## Practice 15: Embedding Reuse Across Pipeline Stages

- **What:** When a pipeline stage computes an embedding (e.g., cache check, query encoding), pass that embedding forward to downstream stages that need it rather than recomputing. Example: the semantic cache's `check_cache()` returns the computed query embedding alongside the hit/miss result. On a cache miss, the caller passes this embedding to `add_to_cache()` and to the retrieval function, avoiding a redundant encoding call.
- **Why:** Embedding computation accounts for a significant portion of pipeline latency (hundreds of milliseconds per call). In a pipeline with cache check, retrieval, and possible re-ranking, embedding reuse can eliminate 1-2 redundant model inferences per query. At enterprise scale with thousands of daily queries, this directly translates to lower latency, reduced compute cost, and fewer embedding API calls.
- **Lyra route:** §4.01 (Architecture), §4.02 (Memory)
- **Source:** Chapter 7, Section 7.3.3
