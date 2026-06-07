# Build an Advanced RAG Application (From Scratch) — Chapter Notes

**Author:** Hamza Farooq (Founder Traversaal.ai, Adjunct Professor, UCLA & Stanford)
**Year:** 2026 (MEAP V04, Manning Publications)
**Core Thesis:** Build LLM-based applications — search engines, RAG systems, and agentic pipelines — entirely from scratch without frameworks like LangChain or LlamaIndex, progressing from transformer fundamentals through to enterprise-grade multi-component architectures with agentic routing, semantic caching, query rewriting, and production deployment.

**Target Audience:** Python developers with basic ML/AI familiarity who want deep, framework-independent understanding of RAG systems. The book explicitly avoids framework lock-in to teach principles that transfer across toolchains.

---

## Chapter 1: The World of Large Language Models

- **Key insight:** LLMs are probabilistic next-token predictors trained on massive datasets (Common Crawl: 250B+ pages). Their scale is both their advantage (nuanced language understanding) and their challenge (compute cost, bias, hallucinations).
- **Best practices:** Distinguish training (broad pattern learning) from fine-tuning (domain-specific adaptation). Understand the RAG pattern early: retrieve external knowledge → integrate into context → generate grounded response.
- **Anti-patterns:** Treating LLMs as deterministic knowledge stores; ignoring the retrieval step for domain-specific applications.
- **Key challenges identified:** Data bias, ethical concerns, interpretability (black-box), hallucinations.
- **Relevant to Lyra §4.x:** Foundational context for why Lyra needs retrieval grounding and evaluation frameworks. The "Anatomy of an LLM Application" (1.2) frames the multi-component reality Lyra must embody.

---

## Chapter 2: Transformer Architecture Deep Dive

- **Key insight:** The Transformer's advantage over RNNs/GRUs is parallelizable self-attention, which captures long-range dependencies without sequential bottlenecks. The encoder-decoder split allows task-specific architectures: encoder-only (BERT for understanding), decoder-only (GPT for generation), or full encoder-decoder (translation, search).
- **Best practices:** Choose encoder models when you need dense semantic representations (search, classification). Choose decoder models when you need text generation. Combine both for RAG pipelines.
- **Design rationale:** Self-attention computes relationships between ALL token pairs simultaneously, unlike RNNs that process sequentially. Multi-head attention provides multiple "perspectives" on the same input. Positional encoding is mandatory because parallel processing loses sequence order.
- **Relevant to Lyra §4.x:** Lyra's architecture choices for different sub-tasks should follow the encoder/decoder split pattern. Semantic search (encoder), response generation (decoder), hybrid understanding tasks (both).

---

## Chapter 3: Encoder Models — Semantic-Based Retrieval Systems

- **Key insight:** Keyword search (TF-IDF + inverted index) is computationally efficient but semantically blind. Semantic search via sentence transformers captures meaning, not just token overlap. The transition demonstrates why RAG needs embeddings.
- **Best practices:** Use pre-trained Sentence Transformers (`all-MiniLM-L6-v2`) for balanced speed/quality. Cosine similarity is the preferred metric for semantic matching. Normalize embeddings (L2) for consistent similarity scoring.
- **Concrete comparison:** Keyword search returned 2/6 documents with non-zero scores for "machine learning" query. Semantic search returned graded scores for all 6, correctly ranking conceptually related (but not keyword-matching) content.
- **Anti-patterns:** Relying solely on keyword search for user-facing applications; ignoring embedding normalization.
- **Relevant to Lyra §4.x:** Lyra's retrieval subsystem. The keyword vs. semantic comparison directly informs the hybrid search pattern Lyra should use.

---

## Chapter 4: Semantic Search from Scratch (Travelle)

- **Key insight:** Building a production semantic search engine requires: data preparation → embedding generation → similarity search → vector database. The Travelle hotel search case study demonstrates the full pipeline end-to-end.
- **Best practices:** Select encoder models carefully — consider domain, language, embedding dimension (384 for MiniLM, 768 for Nomic). Use bi-encoders for efficient search, cross-encoders for re-ranking. FAISS for prototyping, Qdrant (or similar vector DB) for production with metadata filtering.
- **Architecture:** Bi-encoders encode query and documents separately (fast, scalable). Cross-encoders take both as joint input (slower but captures fine-grained interaction — best used as a re-ranker on top-k results).
- **Tools introduced:** FAISS (IndexFlatIP for cosine, IndexFlatL2 for Euclidean), Qdrant (filterable HNSW, persistent storage, async queries).
- **Relevant to Lyra §4.x:** Direct parallel to Lyra's document indexing and retrieval pipeline. The bi-encoder/cross-encoder re-ranking pattern is directly applicable.

---

## Chapter 5: Decoders in Action

- **Key insight:** Decoder models (GPT family) generate text autoregressively — each token prediction conditions on all previously generated tokens. Decoding strategy dramatically affects output quality: greedy (fast, deterministic, repetitive), beam search (better quality, higher cost), sampling with temperature (creative, less predictable).
- **Best practices:** Use temperature=0 for deterministic tasks (routing, classification). Use temperature=0.7-0.9 for creative generation. Top-p (nucleus) sampling balances diversity and coherence better than pure temperature. Stream responses for UX.
- **Model selection framework:** Consider (a) task requirements, (b) context window needed, (c) latency budget, (d) cost per token, (e) deployment mode (API vs. self-hosted).
- **Challenges:** Hallucinations, context window limits, prompt sensitivity, cost.
- **Relevant to Lyra §4.x:** Lyra's generation subsystem. The decoding strategy and model selection framework directly inform Lyra's model routing decisions.

---

## Chapter 6: Retrieval Augmented Generation (RAG)

- **Key insight:** RAG combines semantic search (encoder) with LLM generation (decoder) to produce grounded, cited responses. The core pattern: Query → Embed → Retrieve top-k chunks → Augment prompt with context → Generate cited response.
- **Best practices for RAG prompts:** Explicitly instruct the model to use ONLY the provided context. Require numbered citations [1][2][3]. Start directly with the answer (no salutations). Return in Markdown for readability.
- **Document chunking (6.3):** Recursive split is the recommended strategy — tries natural boundaries first (paragraphs → sentences → words → character fallback). Use 50-character overlap between chunks to preserve cross-chunk context continuity. Embedding models have fixed context windows (8,192 tokens for Nomic), making chunking mandatory for any document exceeding that limit.
- **Chunking strategies compared:** Fixed-size (simple, breaks semantics), sentence-based (preserves grammar, variable sizes), paragraph-based (good for structured docs, may exceed limits), recursive (best balance — default recommendation), semantic (best quality, highest compute cost).
- **Vector DB production migration (6.2):** Qdrant advantages over FAISS: persistent storage, concurrent access, metadata filtering (filterable HNSW), multi-tenant partitioning, hybrid search (sparse + dense vectors), quantization for memory efficiency. Qdrant's engine core is written in Rust for performance.
- **Evaluation framework (6.5):** RAGAS — reference-free, LLM-judged evaluation. Four core metrics: Context Precision (are top results relevant?), Context Recall (are all relevant docs found?), Faithfulness (are claims grounded in context?), Answer Relevancy (does response address query?). Component-level evaluation: evaluate retrieval and generation separately before end-to-end.
- **Additional evaluation tools:** Arize (production monitoring), TruLens (domain-specific), Vertex AI Evaluation (Google Cloud). LLM-as-Judge paradigm increasingly replaces rule-based metrics.
- **Key numbers:** Nomic embedding model context window: 8,192 tokens (~6,000-7,000 words). Cosine similarity scores for good hotel matches: 0.67-0.82.
- **Relevant to Lyra §4.x:** Core RAG architecture pattern. Chunking strategy directly applicable. RAGAS evaluation framework should be part of Lyra's eval harness. The "recursive chunking with overlap" pattern is production-ready.

---

## Chapter 7: Enterprise RAG — Agentic Routing, Semantic Caching, and Query Rewriting

This is the most architecturally significant chapter for Lyra. It defines the transition from naive RAG to production Enterprise RAG.

### 7.1 The Enterprise RAG Landscape

- **Key insight:** Enterprise RAG is an architectural philosophy, not a single technique. The five core components form a modular pipeline: Agentic Routing (decision brain), Guardrails (safety layer), Memory (continuity across turns), Semantic Caching (performance/cost optimization), Query Rewriting (retrieval precision).
- **Design principle:** Each component addresses a distinct failure mode of naive RAG. The components are independent and composable — you can deploy routing without caching, or caching without rewriting.
- **Relevant to Lyra §4.x:** This modular architecture directly maps to Lyra's subsystem design. Each Enterprise RAG component should map to a Lyra workstream.

### 7.2 Agentic Routing — The Three-Route Architecture

- **Key insight:** Routing and retrieval solve fundamentally different problems and MUST be handled by different mechanisms. Routing answers "Where should I look?" Retrieval answers "What should I find?" Conflating them into a single semantic search over a unified index forces the embedding model to perform a task it was never designed for.
- **Three failure modes of unified indexes:**
  1. **Cross-domain contamination:** Overlapping vocabulary across domains (e.g., "rate" in API docs vs. financial filings) produces false semantic matches.
  2. **Authority and provenance blindness:** Embedding models treat all chunks as equal. They cannot distinguish official 10-K filings from blog posts mentioning the same numbers.
  3. **Scalability of retrieval precision:** Each new domain added to a unified index increases the noise floor for ALL queries, degrading precision across every existing domain.
- **The Three-Route Architecture:**
  - Route 1: OpenAI SDK docs → Qdrant vector DB collection
  - Route 2: Uber/Lyft 10-K filings → Qdrant vector DB collection
  - Route 3: Live web search → SerpApi (escape hatch for out-of-scope queries)
- **Design principles for routes:**
  - Routes should map to fundamentally different retrieval STRATEGIES, not just different topics
  - Each new route requires only: a new collection + an updated router prompt
  - The three-route minimum is deliberately chosen to demonstrate the full pattern without infrastructure complexity
  - Always include a fallback route (WEB_SEARCH) as the safety net
- **Router implementation (7.2.2):**
  - Single GPT-4o call with structured prompt (JSON schema embedded in prompt, not function calling)
  - Output: `{"action": "ROUTE_LABEL", "reason": "one sentence", "answer": "optional short answer"}`
  - Fallback on parse failure: route to WEB_SEARCH (safest default)
  - `reason` field creates audit trail for debugging and compliance
  - Structured output via prompt engineering (not JSON mode) for cross-model-version consistency
- **Key latency tradeoff:** LLM-based routing adds ~200-400ms per query but dramatically improves retrieval precision. This is worth the cost.
- **Relevant to Lyra §4.x:** Lyra's router subsystem (§4.05). The three-route pattern scales directly to Lyra's multi-tool routing needs. The audit trail pattern (`reason` field) is essential for Lyra's observability.

### 7.3 Semantic Caching

- **Key insight:** Enterprise query patterns are highly repetitive (teams ask the same questions). Semantic caching eliminates redundant pipeline execution by recognizing semantically equivalent queries at the meaning level, not the string level. Exact-match caching fails for natural language because users phrase the same question differently.
- **Architecture:** FAISS IndexFlatL2 (exact nearest-neighbor, not approximate — cache scale is thousands, not millions). L2 distance threshold of 0.2 (corresponds to cosine similarity ~0.98). Conservative threshold trades hit rate for precision.
- **Why FAISS not Qdrant for cache:** Cache scale is 1K-100K entries. Exact search (IndexFlatL2) is fast enough. Approximate indexes (HNSW/IVF) add complexity for no benefit at this scale. Can upgrade later if cache grows.
- **Time-sensitivity filter (7.3.3):** Keyword-based detection (NOT LLM-based — LLM call would defeat the purpose of caching). Keywords include "today", "currently", "latest", "this week", "stock price", etc. Conservative approach: false positive costs one extra search; false negative returns stale data (worse). Time-sensitive queries bypass cache entirely → fresh web search.
- **Design principles for SemanticCaching class:**
  - Separation of concerns: `check_cache()` only reads, `add_to_cache()` only writes
  - Embedding reuse: `check_cache()` returns the computed embedding so `add_to_cache()` can reuse it (avoids redundant encoding)
  - Cold-start recovery: `load_cache()` rebuilds FAISS index from persisted JSON on startup
- **Measured performance:** Cache MISS: 3.84s (full pipeline). Cache HIT: 0.31s. Speedup: **12.4x**. Cache hit latency dominated by single embedding call; FAISS search completes in microseconds.
- **Cost implications:** In 500-user enterprise with 60% cache hit rate, semantic caching reduces LLM API costs by **40-60%** (source: percona.com/blog/semantic-caching-for-llm-apps).
- **Anti-patterns:** Using LLM for time-sensitivity detection (adds 1-3s latency, negates caching benefit). Setting similarity threshold too loose (returns wrong answers). Treating cache as an afterthought (it should be a first-class architectural component alongside routing).
- **Relevant to Lyra §4.x:** Lyra's memory subsystem (§4.02). Semantic caching is the performance counterpart to Lyra's conversation memory. The time-sensitivity filter pattern directly applies to Lyra's context freshness management.

### 7.4 Query Rewriting and Sub-query Decomposition

- **Key insight:** Users write bad queries. Embedding models produce bad embeddings from bad queries. Query rewriting is a pure pre-retrieval transformation — fix the query before it reaches the embedding model, and you improve retrieval without changing anything downstream.
- **Single-query rewriting (7.4.2):**
  - Rules: Expand abbreviations ("Q3" → "third quarter"), make implicit references explicit, add domain specificity when implied, do NOT add constraints the user didn't express.
  - Pass last 3 conversation exchanges for reference resolution ("same as last time" → resolved from history).
  - Implementation: Single GPT-4o call, `temperature=0` (deterministic), `max_tokens=200`.
  - Overhead: 200-400ms. Offset by improved retrieval precision reducing re-query rate.
- **Sub-query decomposition (7.4.3):**
  - Breaks compound questions into 2-4 atomic sub-queries, each independently answerable.
  - Each sub-query gets its own embedding, route, and retrieval → combined context for synthesis.
  - Example: "What was Uber's revenue in 2021 and how does their gross bookings growth compare to Lyft's?" → 3 atomic sub-queries.
  - Simple queries pass through unchanged (decomposer returns single-element array).
- **Anti-patterns:** Rewriting with hallucinated constraints. Skipping decomposition for compound queries (produces averaged, imprecise embeddings).
- **Relevant to Lyra §4.x:** Lyra's context subsystem (§4.03). Query rewriting is a pre-processing gate. Sub-query decomposition maps to Lyra's multi-step reasoning and tool-use planning.

### 7.5 Combined Enterprise RAG Pipeline

- **Full query lifecycle (9 steps):**
  1. Raw query arrives
  2. Semantic cache check → HIT: return immediately
  3. Time-sensitivity filter → TRUE: bypass cache, go to live search
  4. LLM-based route classification → select target collection
  5. Query rewrite → expand abbreviations, resolve references
  6. Decompose if compound → split into atomic sub-queries
  7. Retrieve from target collection(s) → domain-specific vector search or web search
  8. Synthesize grounded, cited response → GPT-4o with numbered citations
  9. Cache result → store query-response pair for future reuse
- **Pipeline return format:** Returns a dictionary with full audit trail: original query, rewritten query, sub-queries, route, reason, cache_hit flag, time_sensitive flag, answer. Essential for debugging, compliance, and continuous improvement.
- **Production characteristics by query pathway (Table 7.3):**
  - Cache HIT: 10-50ms, 0 LLM calls, 1 embedding call, cost: embedding only
  - Cache MISS (Qdrant RAG): 2-5s, 2 LLM calls (route + generate), 2 embedding calls (cache + retrieve), cost: full pipeline
  - Time-Sensitive (SerpApi): 2-4s, 1 LLM call (generate), 0 embedding calls, cost: SerpApi + generation
- **Key design principle:** The most expensive components only run on cache misses. The system gets faster AND cheaper the longer it operates (cache warms up over time).
- **Relevant to Lyra §4.x:** This is the reference architecture for Lyra's complete query processing pipeline. Every step maps to a Lyra subsystem: cache (§4.02), router (§4.05), rewrite/decompose (§4.03), retrieve (§4.04), synthesize (§4.01), evaluate (§4.16).

### 7.6 Chapter Summary

- Naive RAG (single unified index) fails in enterprise due to cross-domain interference, authority blindness, and scalability degradation.
- Agentic routing fixes "where to search" via LLM-based intent classification.
- Semantic caching fixes "should we search" via FAISS-based semantic similarity matching (12.4x speedup).
- Query rewriting fixes "is the query any good" via LLM-based pre-retrieval transformation.
- The three components compose into a pipeline that gets faster and cheaper over time.

---

## Chapter 8: Deploying RAG into Production (Preview/Summary only)

The MEAP V04 text ends at Chapter 7. Chapter 8 is described as building on the Chapter 7 foundations to create:
- **Full agentic RAG systems** where autonomous agents orchestrate multi-step reasoning across enterprise knowledge landscapes
- **Guardrails** for production safety (input validation, output filtering, prompt injection detection)
- **Memory systems** for multi-turn conversation continuity (short-term: conversation thread; long-term: user preferences, learned patterns)
- **Feedback loops** for continuous improvement
- **Access control layers** for document-level permissions
- **Monitoring and observability** for real-time pipeline visibility

These topics are previewed but not fully developed in MEAP V04.

---

## Cross-Cutting Themes

1. **Framework independence:** Every component is built from scratch (raw Python + API calls). This teaches principles, not tool-specific recipes.
2. **Incremental complexity:** Each chapter builds on the previous one — Chapter 4's semantic search becomes Chapter 6's RAG retrieval layer, which becomes Chapter 7's domain-specific collection search.
3. **Production realism:** The book does not pretend FAISS is production-ready. It explicitly shows the migration path to Qdrant and explains WHY (persistence, concurrency, metadata filtering).
4. **Cost consciousness:** LLM API costs are treated as a first-class architectural concern. Semantic caching, routing optimization, and model selection are all discussed in cost terms.
5. **Auditability:** Every architectural decision (routing `reason` field, numbered citations in responses, pipeline return dictionary) includes an explicit audit trail mechanism.
