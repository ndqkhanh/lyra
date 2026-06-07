# Next Gen Chatbots & RAG — Chapter Notes

**Author:** Temotec AI Academy | **Year:** 2025 (1st Edition) | **Core Thesis:** Enterprise AI assistants must be built on the "open-book" architecture — a RAG framework where the LLM speaks only from proprietary documents, never fabricates, and says "I don't know" when evidence is absent. Generic AI (ChatGPT-style) hallucinates because it was trained on the internet, not your internal knowledge base. The solution is not fine-tuning but retrieval: anchor every response to verifiable source documents stored in a private, encrypted vault.

**Target Audience:** Business owners, product managers, IT leads, and developers building production AI assistants — not researchers or prompt-hobbyists. Assumes zero prior AI knowledge.

---

## Book Structure

5 Parts, 13 Chapters + 3 Appendices, ~511 pages.

**Part I: The Private AI Paradigm ("Zero" Phase)** — Chapters 1-2: Why generic AI fails; the "open-book test" architecture; ROI calculation.

**Part II: The Invisible Librarian (Novice to Intermediate)** — Chapters 3-5: Semantic search, vector databases, document ingestion.

**Part III: Precision Recall (Advanced Intermediate)** — Chapters 6-7: Intelligent data chunking, hybrid search.

**Part IV: The Autonomous Agent ("Hero" Phase)** — Chapters 8-11: Conversational memory, truth mandate, autonomous routing, automated quality inspection. (MOST RELEVANT TO LYRA)

**Part V: Capstone & Deployment** — Chapters 12-13: Full pipeline build, production deployment.

**Appendices:** Secure DB cheat sheet, Document prep guide, Anti-hallucination prompt library.

---

## Chapter 1: The End of Generic AI

**Page range:** ~64-88
**Role in book:** Foundation — why generic AI fails, introduction to "open-book" paradigm.

### Key Architectural Insight
The "open-book test" architecture: the LLM is given access only to proprietary documents. It must explicitly cite sources. If no evidence is found, it must say "I don't know." This fundamentally differs from fine-tuning (expensive, still hallucinates) and from generic chat (trained on public web, not internal data). The shift is from "smarter model" to "controlled retrieval."

### Best Practices
- Define a "truth anchor" prompt that constrains the LLM to only use provided documents
- Structure data as searchable semantic chunks (not raw files dumped into context)
- Test the system with deliberately impossible questions (e.g., "What color is the CEO's car?") to verify it refuses rather than hallucinates
- Encrypt all stored documents at rest; never store proprietary data in public cloud buckets
- Implement a private data vault using encrypted SQLite (small) or AWS S3 with role-based access (enterprise)

### Anti-Patterns
- Assuming "contextual understanding" automatically produces honesty — context enables relevance, not truth
- Relying on model's "default response" — always define an explicit fallback like "I don't know"
- Dumping 10,000 pages into context without chunking — the LLM gets overwhelmed and hallucinates
- Believing fine-tuning solves hallucination — fine-tuned models still fabricate when inputs are ambiguous

### Relevant to Lyra
- §4.1 (Safety/Alignment): The "truth anchor" prompt pattern directly maps to Lyra's safety constraints
- §4.2 (Context/Retrieval): Private vault + encrypted storage pattern
- §7.1 (RAG Pipeline): The open-book architecture is the core pattern Lyra should adopt

---

## Chapter 2: Anatomy of a Brilliant Assistant

**Page range:** ~89-124
**Role in book:** Core feedback loop and constraint understanding.

### Key Architectural Insight
The RAG pipeline is a 5-step assembly line: (1) Query Reception (frontend → backend API), (2) Retrieval Engine Activation (search private vector DB), (3) Context Injection (prepend retrieved chunks to user query with strict prompt), (4) Response Generation (LLM generates only from injected context), (5) Output Delivery (answer + optional source citations). The "attention span constraint" means you cannot feed a 10,000-page manual into context — intelligent chunking is mandatory.

### Best Practices
- Keep the 5-step pipeline separable — each step should be independently testable and replaceable
- Always include source citations in responses (e.g., "Based on internal document 'Safety Specs v2.1'")
- The anchor prompt must be embedded architecturally (system prompt), not just per-query
- Test multiple anchor prompt variants: "strict" prompts for technical queries, "contextual" for customer-facing
- Use lightweight frontend (React/Vue) with backend API separation — never embed business logic in UI

### Anti-Patterns
- Assuming one anchor prompt works for all query types — measure hallucination rates per prompt variant
- Skipping the Context Injection step — without explicit "Answer ONLY based on following context:", the LLM defaults to its training data
- Not version-controlling documents — the AI must know which version it's referencing
- Trying to build a "perfect" RAG system on day 1 — start with one document, one question

### Relevant to Lyra
- §4.3 (Agent Architecture): The 5-step pipeline maps directly to Lyra's agent loop
- §4.4 (Tool Use): The retrieval engine activation is a tool call pattern
- §7.1 (RAG): Core feedback loop structure

---

## Chapter 3: The Semantic Search Engine

**Page range:** ~125-153
**Role in book:** Moving from keyword search to meaning-based retrieval.

### Key Architectural Insight
Semantic search converts text into mathematical vectors (embeddings) so the system finds semantically similar content, not just exact keyword matches. "What's the maximum operating temperature?" finds documents about "thermal limits" even if those words don't appear. The embedding model choice (Sentence-BERT, OpenAI text-embedding-3) is critical — accuracy matters more than speed.

### Best Practices
- Use SBERT's `all-MiniLM-L6-v2` (384-dim) for prototyping; upgrade to larger models for production
- Always save embeddings as numpy arrays or parquet files — never recompute on every launch
- Normalize vectors to unit length before adding to FAISS index (use `np.linalg.norm()`)
- Chunk documents at 100-200 words per chunk for optimal retrieval granularity; never exceed 500 words
- Popular vector DB options: FAISS (local/free), Weaviate (prod), Chroma (developer-friendly), Redis (cached)
- Regenerate embeddings when source documents are updated — embeddings are dynamic, not static

### Anti-Patterns
- Choosing embedding models based on speed alone — inaccurate models return irrelevant results
- Forgetting to normalize vectors — FAISS expects unit-length vectors; unnormalized = inaccurate search
- Embedding too-large chunks (500+ words) — the semantic signal gets diluted
- Not adding metadata to embeddings — without product_id/department/version tags, context is lost

### Relevant to Lyra
- §3.1 (Memory/Vector Store): Embedding pipeline and vector DB selection
- §7.1 (RAG): Semantic search as core retrieval primitive

---

## Chapter 4: The Secure Data Vault

**Page range:** ~154-180
**Role in book:** Private storage architecture for enterprise data.

### Key Architectural Insight
The data vault must be encrypted at rest (Fernet/AES-256), accessible only to authorized users via role-based permissions. Documents must be converted to plain text before storage — binary files (PDF/Word) cannot be searched by the LLM directly. Storage solution scales from SQLite (small business) to AWS S3/DynamoDB (enterprise).

### Best Practices
- Always encrypt at rest, even for local storage — compromised DB = exposed proprietary data
- Convert all non-text formats (PDF, Word, Excel) to plain text before indexing
- Use cryptography library's Fernet for symmetric encryption in Python
- For cloud: AWS S3 with server-side encryption + IAM roles; Google Cloud Storage with private ACLs
- Store metadata alongside extracted text: {product_id, department, version, date}
- Implement checksum-based duplicate detection (MD5/SHA256) to avoid indexing the same document twice

### Anti-Patterns
- Storing unstructured data (PDFs, Word docs) directly in structured databases — AI can only search text
- Skipping encryption "because it's internal" — internal leaks are as dangerous as external breaches
- No duplicate detection — multiple versions of the same doc confuse the AI
- Storing everything in one flat structure — use categorization: product manuals, HR policies, compliance docs, etc.

### Relevant to Lyra
- §4.6 (Data Security): Encryption-at-rest pattern, role-based access
- §7.2 (Data Ingestion): Document preprocessing pipeline

---

## Chapter 5: Absorbing Your Enterprise Data

**Page range:** ~181-205
**Role in book:** Real-world data ingestion from messy company sources.

### Key Architectural Insight
Most company data is chaotic: PDFs with complex layouts, Word docs with tables, spreadsheets in nested folders. The ingestion pipeline must: (1) extract plain text from all formats (PyPDF2, pdfplumber, python-docx, unstructured.io), (2) normalize (consistent formatting, strip images/headers), (3) validate (check for missing sections, malformed data), (4) handle errors gracefully (skip corrupted files, log failures). Automation via `os.walk()` or cloud storage APIs keeps the index fresh.

### Best Practices
- Use `unstructured.io` for complex layout PDFs that PyPDF2 can't handle
- Normalize all text before feeding to AI: strip formatting, convert to consistent case/encoding
- Implement try-except error handling — one broken PDF shouldn't crash the entire pipeline
- Validate extracted text: if a document claims to have "Product ID", verify it contains "Category" too
- Automate ingestion: use `os.walk()` for local files or S3 bucket notifications for cloud
- Flag validation failures for manual review rather than silently ingesting bad data

### Anti-Patterns
- Assuming all PDFs are searchable — many are image-only and need OCR
- Skipping data validation — garbage in, garbage out applies doubly to RAG
- No error handling — a single corrupted file crashes the indexing pipeline
- Manual uploads as primary strategy — must automate for scale

### Relevant to Lyra
- §7.2 (Data Pipeline): Document ingestion, normalization, validation patterns
- §4.5 (Observability): Error logging and pipeline monitoring

---

## Chapter 6: Intelligent Data Slicing

**Page range:** ~216-243
**Role in book:** The chunking strategy that determines retrieval quality.

### Key Architectural Insight
The "secret to perfect memory" is intelligent chunking: splitting massive documents into bite-sized concepts (100-200 words) while preserving context via metadata anchoring. Chunks must be tagged with product_id, category, department, and version so the AI knows exactly which product a paragraph belongs to — even after it's been filed away in the vector database. Contextual anchoring prevents the "wrong product" problem where a sentence from Product A's manual is retrieved for a query about Product B.

### Best Practices
- Chunk size: 100-200 words for optimal retrieval; 500 words max
- Always attach metadata to each chunk: {product_id, category, department, version, date}
- Use schema-based metadata (JSON Schema or Apache Avro) to enforce consistency
- Implement versioned metadata: don't overwrite on document update; create new version entries
- Dynamic metadata extraction: use NLP models (BERT/GPT) to auto-extract attributes from unstructured text
- Metadata-based filtering in retrieval: filter chunks by product_id/department before semantic search

### Anti-Patterns
- Chunking by character count alone — breaks sentences mid-thought, loses context
- Tagging with irrelevant metadata ("color: silver" for a warranty policy chunk) — creates noise
- Assuming metadata is static — product IDs change; metadata must evolve with catalog
- Ignoring metadata in prompts — the AI prompt must reference metadata for context-aware retrieval
- Not filtering by metadata before retrieval — forces the LLM to sort through irrelevant chunks

### Relevant to Lyra
- §3.1 (Memory): Chunking strategies and metadata anchoring directly apply to Lyra's document memory
- §7.1 (RAG): Retrieval quality depends entirely on chunking granularity

---

## Chapter 7: The Hybrid Search Upgrade

**Page range:** ~244-276
**Role in book:** Combining semantic + keyword search for zero-miss retrieval.

### Key Architectural Insight
Standard semantic search fails when users query with highly specific part numbers ("SKU-7892-B"), industry jargon, or technical codes. The solution is hybrid search: combine semantic similarity (embeddings) with exact keyword matching (BM25 or Elasticsearch multi-field queries). Results are ranked by a weighted scoring system that prioritizes matches on both axes. Re-ranking with BM25 after semantic retrieval ensures exact term matches surface above merely-similar results.

### Best Practices
- Implement 3-stage retrieval: (1) semantic search for meaning, (2) keyword filter for exact terms, (3) BM25 re-ranking
- Use Elasticsearch multi-field queries or custom weighted scoring for hybrid
- Create a secondary index storing all part numbers/SKUs as exact-match entries
- Combine Sentence Transformers with BM25: semantic → top-k candidates, BM25 → re-rank
- Prepend queries with context metadata before semantic search (e.g., "Product: X-100, Query: how to reset?")
- A/B test precision: measure retrieval precision with and without hybrid search

### Anti-Patterns
- Using a single embedding model for everything — different query types need different retrieval strategies
- Not adding context to queries before searching — "reset password" means server admin vs. user account
- Ignoring document metadata during search — metadata filtering eliminates irrelevant results before semantic comparison
- Not testing with real user queries — synthetic data doesn't capture the variety of real user phrasing
- No re-ranking after semantic retrieval — semantically similar but technically wrong results slip through

### Relevant to Lyra
- §7.1 (RAG): Hybrid search as the retrieval backbone
- §3.1 (Memory): Multi-index strategies for different query types
- §4.4 (Tool Use): Search as a tool with strategy selection

---

## Chapter 8: Perfect Conversational Memory (MOST LYRA-RELEVANT)

**Page range:** ~286-318
**Role in book:** The memory architecture that prevents the "goldfish problem" — chatbots forgetting after 2 turns.

### Key Architectural Insight
Three-tier modular memory architecture: **(1) Short-Term Working Memory** — immediate conversation state via bounded deque or Redis with TTL; stores recent messages, user preferences, dynamic variables like "current product under discussion." **(2) Long-Term Persistent Storage** — encrypted databases (PostgreSQL, DynamoDB) or distributed caches for cross-session continuity; stores user profiles, historical interactions, persistent preferences. **(3) Context-Aware Retrieval Logic** — vector embeddings (Sentence-BERT/OpenAI) compare current queries against historical messages via cosine similarity, enabling semantic retrieval of past context without exact keyword matching.

Memory must be treated as an *extension of retrieval*, not a separate component. The RAG pipeline should query both the memory layer and the document store simultaneously, then combine results before feeding to the LLM ("dual-source RAG pipeline").

Critical insight: "Context is not just data. It's intent." The state layer must capture not just text but intent, location, user preferences, and emotional tone.

### Best Practices
- **3-tier memory**: short-term (deque/Redis TTL), long-term (PostgreSQL/DynamoDB), retrieval (vector embeddings)
- **Dual-source RAG**: query memory + document store simultaneously, combine results
- **Bounded working memory**: always cap with max_size; use Redis TTL to auto-expire old entries
- **Session-based isolation**: every conversation gets a UUID; never use global state variables
- **Per-user state management**: Redis hash tables or DB partitions keyed by `user_id`
- **Automatic cleanup**: TTL-based pruning + garbage collection thread to prevent unbounded growth
- **Cosine similarity for memory retrieval**: embed historical messages; compare query embedding to find most relevant prior context
- **Thread-aware retrieval**: conversation thread manager maps user messages to their respective conversation IDs
- **Log all memory operations**: invaluable for debugging memory leaks or inconsistent state
- **Performance targets**: memory latency <10ms, hit rate (relevant context found) tracked, error rate monitored

### Anti-Patterns
- Storing context in in-memory Python variables — lost on restart; multiple workers cause inconsistency
- Storing entire conversation history as one unstructured string — impossible to query specific turns
- No TTL on sessions — memory grows unbounded, eventually crashes
- Forgetting to clear memory on session termination — memory leaks over weeks/months
- No serialization of complex objects — raw Python dicts into JSON cause encoding errors
- Synchronous external API calls in memory layer — blocks the agent; use async
- Global state variable for all conversations — race conditions and data corruption

### Advanced Patterns
- **Context Chains**: linked list of conversation states where each node references the previous — enables full conversation reconstruction
- **State Graphs**: directed graph where nodes are decision points ("return_request", "upgrade_plan") and edges are transitions — for multi-step workflows
- **State Machine integration**: Celery/Airflow/AWS Step Functions for complex workflow orchestration
- **Distributed memory**: Redis Cluster or Kafka for multi-node replication and fault tolerance
- **Caching at 3 levels**: (1) application cache (Redis/Memcached), (2) DB-level indexes, (3) precomputed embeddings for common phrases

### Relevant to Lyra
- §3.0 (Context/Memory System): **Directly** maps to Lyra's context window management and memory layer
- §4.3 (Agent Loop): Dual-source RAG pipeline as Lyra's agent cognition loop
- §4.2 (Context Management): Session isolation, TTL-based pruning, per-user state

---

## Chapter 9: The "Truth Only" Mandate (MOST LYRA-RELEVANT)

**Page range:** ~319-346
**Role in book:** Safety/alignment architecture — forcing the AI to never lie.

### Key Architectural Insight
Truth enforcement requires *layered constraints*, not just prompts. The architecture has 3 layers: **(1) Prompt-level anchoring** — explicit instructions constraining the LLM to only use provided data with mandatory "I don't know" fallback. **(2) System-level truth gates** — a post-generation function that checks whether the AI's response matches source documents; if mismatch detected, response is rejected and regeneration is forced. **(3) Dynamic truth anchors** — version-controlled document knowledge that auto-updates when company policies change, ensuring the AI always uses the latest data.

The "cross-document truth validation" pattern: when a question spans multiple departments (HR, IT, Finance), the system must verify consistency across all relevant documents before responding. Conflicts must be surfaced ("GDPR requires X while CCPA requires Y — please consult legal").

### Best Practices
- **Truth gate function**: validate response against source documents before sending to user; reject and regenerate if hallucination detected
- **Anchor prompt template**: "You are an AI assistant for [COMPANY]. Answer ONLY based on the provided context. If insufficient information, say 'I don't know.' Do not invent, guess, or extrapolate."
- **Partial data handling**: when documents are incomplete, say "Based on available data: [fact]. Please consult official documentation for complete details."
- **Version-controlled responses**: include version tag in answers — "Based on version 2.1 of the HR policy document."
- **Dynamic truth anchors**: auto-update knowledge base on document revisions; tag with version numbers
- **Hallucination detection tests**: ask impossible questions ("What color is the CEO's car?") — system must respond "I don't know"
- **Cross-document consistency checks**: when multiple documents are relevant, verify they don't conflict before responding
- **Add disclaimers to every response**: "This answer is derived from verified company data."

### Anti-Patterns
- Relying on prompts alone for truth enforcement — prompts can be bypassed; need system-level truth gates
- Over-engineering truth constraints — a 100-page prompt creates brittleness; start with 3-4 lines and layer
- Not testing for hallucinations — must have automated hallucination detection in QA pipeline
- Assuming "don't lie" is understood by the LLM — must be specific: "If information not in provided documents, say 'I don't know'"
- No version control on documents — AI may reference outdated policies
- Allowing the model to extrapolate from partial data — must say "I don't know" when data is incomplete

### Relevant to Lyra
- §4.1 (Safety/Alignment): **Directly** maps — truth gates are Lyra's safety guardrails
- §4.6 (Verification): Hallucination detection testing pipeline
- §4.5 (Observability): Response auditing — tracking which documents generated each answer

---

## Chapter 10: The Autonomous Router (MOST LYRA-RELEVANT)

**Page range:** ~347-372
**Role in book:** Upgrading from Q&A bot to autonomous agent with decision-making and action execution.

### Key Architectural Insight
The full agent architecture is a 3-layer state machine: **(1) Memory Layer** — retrieves context. **(2) Rule Engine Layer** — evaluates if-then rules based on context + user input. **(3) Action Execution Layer** — triggers real-world actions (send email, create Jira ticket, call webhook, route to human). The rule engine is where decisions are made: "If user asks about returns AND location is Canada, return Canadian policy. If pricing question AND company has volume discount, apply discount."

The autonomous router has three pillars: **context awareness** (understands user role, product, intent), **decision logic** (rule set or heuristics mapping inputs to actions), and **action triggers** (execution of the chosen action). Fallback rules define what happens when no answer is found: route to human, create support ticket, log the question.

### Best Practices
- **3-layer agent architecture**: Memory → Rule Engine → Action Execution — each independently testable
- **JSON-based rule storage**: store rules externally in JSON files, load dynamically — enables rule updates without code redeployment
- **Context-aware routing**: integrate user_id, product_category, session_history into every routing decision
- **Fallback rule hierarchy**: (1) "I don't know" → route to live agent, (2) policy question → create Jira ticket, (3) malformed input → log for review
- **State machine for complex workflows**: pyState or custom state machines with clear transitions and validation
- **Async action execution**: use `asyncio` for external API calls to avoid blocking the main agent thread
- **Start with 2-3 core rules**: cover most common scenarios first; add complexity incrementally
- **Decision trees for multi-step workflows**: hierarchical if-then with input validation at each step

### Anti-Patterns
- Hardcoding rules in application code — policy changes require full redeployment
- Building agents without a state machine — rules conflict, actions trigger unexpectedly, no way to track state
- Synchronous actions blocking the agent — external API calls freeze the conversation
- Overcomplicating rules too early — start with simple keyword-based routing
- Decision trees without validation — agent loops infinitely or collects invalid data
- No fallback rules — agent crashes or returns empty on edge cases instead of gracefully degrading

### Relevant to Lyra
- §4.3 (Agent Architecture): **Directly** maps — 3-layer state machine is Lyra's agent loop design
- §4.4 (Tool Use/Plugins): Action execution layer is Lyra's tool calling system
- §4.5 (Routing): Decision logic and rule engine patterns
- §4.1 (Safety): Fallback rules as safety net

---

## Chapter 11: The Automated Quality Inspector (MOST LYRA-RELEVANT)

**Page range:** ~373-402
**Role in book:** Automated QA/evaluation framework for AI assistants before production deployment.

### Key Architectural Insight
Quality assurance is not optional — "78% of AI errors are hallucinations, not bugs." The QA system has four pillars, each with its own automated test suite: **(1) Honesty Tests** — verify the AI never fabricates answers; use exact phrase matching against source documents. **(2) Relevance Tests** — confirm responses address what was asked; use cosine similarity against known-relevant contexts. **(3) Accuracy Tests** — validate factual claims match source documents via checksums and fuzzy matching. **(4) Contextual Consistency Tests** — ensure multi-turn memory works correctly across follow-up questions.

The framework uses pytest for test execution and runs in seconds. Critical design choice: test for compliance (did it follow the rules?) before correctness (was the answer right?).

### Best Practices
- **4-pillar QA suite**: Honesty → Relevance → Accuracy → Contextual Consistency
- **Exact phrase matching** for honesty: response must contain the exact sentence from source document
- **Cosine similarity thresholds** for relevance: score < threshold = test failure (off-topic)
- **Checksum-based accuracy**: hash source document text; compare with AI response to detect deviation
- **Deliberately misleading test queries**: ask impossible questions to validate "I don't know" behavior
- **Reject deployments** that produce any hallucination in test suite — zero-tolerance
- **Automated QA pipeline**: run on every data update or model change; seconds, not hours
- **Log when the AI says "I don't know"** — analyze patterns to identify knowledge base gaps

### Anti-Patterns
- Validating honesty by checking for keywords — AI can say "72 hours" but add "in most cases" (misleading)
- No hallucination tests in QA pipeline — most common failure mode goes untested
- Assuming QA is for "later" — deploy without testing = deploy a liability
- Testing with synthetic data only — must test with real user queries to catch edge cases
- No re-testing after data updates — new documents may introduce new failure modes

### Relevant to Lyra
- §4.6 (Evaluation/Verification): **Directly** maps to Lyra's eval harness
- §4.1 (Safety): Honesty tests as safety verification
- §4.5 (Observability): QA metrics tracking and logging

---

## Chapter 12: Capstone Setup — The Automated Employee Onboarding Expert

**Page range:** ~418-448
**Role in book:** End-to-end pipeline build for a specialized internal Q&A bot.

### Key Architectural Insight
Full pipeline execution for a real use case: building an HR onboarding bot trained on HR manuals, benefits packages, and training documentation. The pipeline stages: document collection → text extraction → chunking → embedding → vector DB indexing → prompt template design → testing → deployment.

### Best Practices
- Pipeline must be reproducible: same inputs → same outputs, every time
- Specialize the assistant to one domain (HR) rather than building a generalist
- Test with real employee questions before deployment
- Measure time-to-answer: pre-AI vs. post-AI for ROI calculation

### Relevant to Lyra
- §7.0 (End-to-End Architecture): Replicable pipeline pattern
- §4.5 (Observability): ROI/performance measurement

---

## Chapter 13: Launching the Command Center

**Page range:** ~449-480
**Role in book:** Production deployment with UI, monitoring, and scaling.

### Key Architectural Insight
Production deployment requires: **(1) User-friendly chat interface** (React/Vue frontend wrapping API), **(2) Tracking dashboard** monitoring what questions users ask, response times, and documentation gaps, **(3) Canary releases** — deploy to 1% of users, monitor, then gradually increase, **(4) Caching with TTL** — Redis for FAQ caching reduces LLM load and speeds responses from 2s to 0.1s, **(5) API versioning** — `/v1/query` for legacy, `/v2/query` for enhanced features, **(6) Swagger/OpenAPI documentation** for integration, **(7) User feedback loops** — "Rate this response" + A/B testing.

### Best Practices
- Cache common FAQs with Redis TTL — expires automatically when policies change
- Canary releases: Istio/service mesh for traffic routing by user segment
- API versioning from day 1 — prevents breaking existing integrations
- Swagger/OpenAPI for auto-generated documentation and client SDKs
- Kubernetes HPA (Horizontal Pod Autoscaler) for auto-scaling based on CPU/memory
- Monitor: Prometheus/Grafana for real-time performance dashboards
- Always collect user feedback; use it to improve accuracy
- Use webhooks for real-time actions (send email, update database)

### Anti-Patterns
- Deploying without caching — repeated identical queries overload the LLM
- No API versioning — upgrades break existing integrations
- Skipping canary releases — full rollout of untested version = production failure
- No feedback collection mechanism — can't improve what you don't measure

### Relevant to Lyra
- §4.7 (Deployment): Production deployment patterns, canary releases, monitoring
- §4.5 (Observability): Dashboard, logging, feedback loops

---

## Appendix A: Secure Database Cheat Sheet
- Store size → recommended DB: Small (<1K docs) → SQLite/Chroma; Medium (1K-100K) → PostgreSQL with pgvector; Large (100K+) → AWS DynamoDB/Google Cloud Spanner; Enterprise → multi-region with Redis caching

## Appendix B: Document Preparation Guidelines
- Convert all formats to plain text; strip images, headers, footers; use consistent encoding (UTF-8); validate dates and sections

## Appendix C: Anti-Hallucination Prompt Library
- Collection of copy-paste prompt templates for various scenarios (customer support, HR, legal, technical)
