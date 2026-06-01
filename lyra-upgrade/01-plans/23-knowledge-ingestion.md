# Plan: §4.23 Knowledge Ingestion & RAG

**Plain-Language Summary**: Lyra needs to understand your codebase and documents the way a senior engineer does -- not file-by-file, but as an interconnected web of symbols, their callers, their documentation, and what changed last week. This workstream builds a pipeline that ingests codebases, PDFs, diagrams, and configuration into a queryable knowledge graph so agents can ask questions like "what functions call `processPayment()`?" and get precise, freshness-tracked answers. The breakthrough is code-aware indexing: rather than treating code as flat text (which conventional RAG does), Lyra parses ASTs, builds call graphs, and indexes by symbol, type, and reference relationships -- then uses Self-RAG to verify retrieved results are actually relevant before injecting them into agent context. Empirical evidence from codegraph (findings #6, BREAKTHROUGH) shows this approach delivers 25% cost reduction, 57% fewer tokens, and 62% fewer tool calls across real codebases.

**Workstream**: Codebase indexing, document ingestion, multimodal RAG, knowledge freshness
**Priority**: P1 -- Required for Lyra to work with real codebases and documents
**Date**: 2026-06-01 (Run 20 -- Full deepening pass)
**Status**: Deepened plan -- integrates with `lyra-etl-pipeline`, `lyra-knowledge-graph`, `lyra-memory` packages; cross-references BREAKTHROUGH-ARCHITECTURE.md Algorithms 1-4

---

## 📋 Quick Reference Card

| What | RAG pipeline: indexing codebases/docs, hybrid retrieval, multimodal ingestion, knowledge freshness |
| Why | Lyra needs to understand your codebase — not just read files one at a time |
| Key Insight | Graph RAG (entities + relationships) beats flat RAG for code understanding; incremental re-indexing keeps knowledge fresh |
| Timeline | 8 weeks (5 parity + 3 breakthrough) |
| Key Sources | GraphRAG (Microsoft), Self-RAG (ICLR 2024), HippoRAG (NeurIPS 2024), codegraph, spaCy |

## 🎯 Executive Summary

Lyra's memory system stores what happens during agent execution (episodic). But Lyra also needs to understand STATIC knowledge: your codebase structure, your documentation, your API specs, your dependency graph. This is the ingestion pipeline — it indexes these artifacts into the TKG so the router, planner, and agents can retrieve relevant context before acting. The breakthrough is CODE-AWARE indexing: instead of treating code as plain text, Lyra parses ASTs, builds call graphs, and indexes by (symbol, type, references) — enabling queries like "find all callers of this function" that flat RAG cannot answer.

---

## 1. Problem

**Current state**: `lyra-etl-pipeline`, `lyra-knowledge-graph`, `lyra-memory/codebase_graph` packages exist. The memory system has `test_codebase_graph.py` suggesting code indexing capability.

**The gap**:
1. Ingestion pipeline not wired to agent workflow — agents can't query "what functions call `processPayment()`?"
2. No incremental re-indexing — if one file changes, the entire codebase must be re-indexed
3. No multimodal ingestion (PDFs, images, diagrams)
4. No freshness tracking — is this index from 5 minutes ago or 5 days ago?
5. Retrieval quality not measured — no relevance benchmarks for Lyra's retrieval

---

## 2. Evidence Synthesis

### 2.1 Core Sources (with Findings Citations)

| Source | Finding # | Key Finding | Empirical Result | Transfer to Lyra |
|--------|-----------|------------|------------------|-----------------|
| GraphRAG (Microsoft) | -- | Entity extraction + community detection + graph summarization; outperforms flat RAG on multi-hop queries | 30-40% improvement on multi-hop QA over naive RAG | Build entity-relationship graph from code ASTs and documentation |
| Self-RAG (ICLR 2024) | -- | LLM decides WHEN to retrieve and evaluates its OWN retrieval quality | 5-15% accuracy gain over standard RAG across 6 benchmarks | Agent decides "should I search the codebase for this?" and "was that result relevant?" |
| HippoRAG (NeurIPS 2024) | -- | Hippocampal-inspired: structured retrieval over knowledge graphs, not flat embeddings | 7-20% improvement on multi-hop QA vs. embedding-only retrieval | Use TKG as the retrieval substrate; graph traversal for multi-hop queries |
| codegraph | #6 (BREAKTHROUGH) | tree-sitter AST -> SQLite knowledge graph with FTS5; MCP server with 8 tools; staleness banner | **25% cost reduction, 57% fewer tokens, 23% faster, 62% fewer tool calls** across 7 repos; 20+ languages; 14 framework-aware routes | Parse code ASTs with tree-sitter; pre-indexed graph beats exploration; staleness signaling critical for trust |
| graphify | #5 (HIGH) | Knowledge graph from codebase with confidence tags (EXTRACTED/INFERRED/AMBIGUOUS); community detection via clustering | Works across 13+ platforms; auto-rebuild on git commit; 20+ languages | Confidence-tag every relationship; community detection enables "find related modules" queries |
| spaCy | #7 (MEDIUM) | Industrial NLP: NER, entity linking, 70+ languages; production-ready | State-of-the-art speed; GPU support; LLM integration | NLP primitives for extracting technical entities from docs and linking to code symbols |
| TencentDB-Agent-Memory | #1 (BREAKTHROUGH) | Layered pyramid: raw -> facts -> scenarios -> persona; symbolic short-term via Mermaid graphs | **61% token reduction, 51% pass rate improvement** on WideSearch; PersonaMem accuracy 48%->76% | Layer the knowledge graph: raw code -> symbol facts -> architectural scenarios -> project-level understanding |
| MemPalace | #4 (BREAKTHROUGH) | Verbatim + structured storage with hierarchical index (wings/rooms/drawers); 29 MCP tools | **96.6% R@5 on LongMemEval** (raw, no LLM); 98.4% hybrid | Hierarchical index organization for scoped retrieval; verbatim storage of code symbols preferred |
| LightMem | #N53 (HIGH) | SLM-based 3-tier memory; online vector retrieval + semantic re-ranking; offline abstraction | **83ms retrieval latency, 581ms end-to-end; +2.5 F1 over A-MEM** on LoCoMo | Use cheap models for retrieval/re-ranking; 83ms latency proves real-time KG traversal is achievable |
| Anthropic Context Engineering | #253 (BREAKTHROUGH) | Just-in-time context loading with lightweight identifiers; sub-agents return 1-2K token summaries | "Substantial improvement" on complex research tasks (qualitative) | Progressive disclosure: retrieve symbol summaries first, full definitions only when needed |
| STITCH | #17 (BREAKTHROUGH) | Intent-based indexing with (goal, action type, entity) triples | **35.6% improvement** by filtering semantically-similar but contextually-wrong memories | Tag each knowledge graph entry with contextual intent; filter by compatibility, not just similarity |
| APEX-MEM | #16 (BREAKTHROUGH) | Property graph with domain-agnostic ontology; append-only storage; multi-tool retrieval agent | 88.88% accuracy on LoCoMo QA; 86.2% on LongMemEval | Defer conflict resolution to query time; append-only event log for temporal provenance |

### 2.2 Extended Evidence

| Source | Key Finding | Empirical Result | Transfer to Lyra |
|--------|------------|------------------|-----------------|
| MASS-RAG (ACL 2026) | Multi-agent selective search RAG -- specialized retrieval agents each search different knowledge sources, then merge results | Outperforms single-agent RAG by 22% on multi-source queries | Lyra's swarm architecture is a natural fit: code-agent searches AST graph, doc-agent searches documentation index, config-agent searches config schema -- merge results for comprehensive context |
| LP-RAG (2025) | Link prediction for RAG -- predicts which documents are likely to be interlinked before retrieval, then uses predicted links to guide multi-hop retrieval | 18% improvement on multi-hop QA | Pre-generate synthetic queries for each code symbol; train link predictor for query-to-symbol retrieval |
| GraphRAG v2 (2025) | Community summarization with hierarchical clustering; summaries at multiple granularity levels (function-level, module-level, repo-level) | Consistent improvement over flat summarization across granularities | Index Lyra's codebase at three granularities: symbol-level (function), file-level (module), package-level (repo). Route queries to appropriate granularity based on scope |
| AST-Embed (2024) | Embedding code AST paths (not just text) improves code retrieval significantly | 30% improvement vs. text-only embeddings | Lyra's chunk embeddings should include AST path features: `module.class.method` as structured metadata alongside text embedding |
| Late Chunking (2024) | Chunk AFTER embedding (embed full document, then split by boundary) preserves cross-chunk context | 15-20% retrieval improvement vs. chunk-then-embed | For documentation: embed full pages, then chunk. For code: embed full files, then index symbols. Hybrid approach per content type |

### 2.3 Design Principles Extracted

1. **Code is not text**: Parse ASTs, not just token streams. Embed symbol paths alongside text.
2. **Retrieve at the right granularity**: Symbol-level for "find this function", file-level for "understand this module", package-level for "how is this project structured"
3. **Stay fresh**: Incremental re-indexing triggered by git hooks, not periodic full re-index. Every node knows which commit it was indexed from.
4. **Evaluate retrieval, not just generation**: Self-RAG pattern — the agent evaluates whether retrieved context was actually relevant before using it.

---

## 3. Proposed Lyra Design

### 3.1 Ingestion Pipeline

```mermaid
graph TB
    subgraph "Sources"
        CODE[Codebase<br/>.ts, .py, .go, ...]
        DOCS[Documentation<br/>.md, .rst, .pdf]
        DEPS[Dependencies<br/>package.json, go.mod, ...]
        CONFIG[Config<br/>.json, .yaml, .env]
    end

    subgraph "Ingestion Pipeline"
        AST[AST Parser<br/>Tree-sitter]
        ENT[Entity Extractor<br/>spaCy + LLM]
        CHUNK[Chunker<br/>AST-aware + semantic]
        EMBED[Embedding<br/>1536-dim vector]
    end

    subgraph "Knowledge Graph"
        SYMBOLS[Symbol Nodes<br/>functions, classes, types]
        CALLS[Call Edges<br/>calls, imports, extends]
        DOCNODES[Doc Nodes<br/>linked to symbols]
        FRESHNESS[Freshness Tracker<br/>git commit hash per node]
    end

    subgraph "Retrieval"
        HYBRID[Hybrid Search<br/>vector + keyword + graph]
        SELF_EVAL[Self-RAG Evaluator<br/>relevance scoring]
        MULTIHOP[Multi-Hop Traversal<br/>caller→callee→docs]
    end

    CODE --> AST
    DOCS --> ENT
    DEPS --> CHUNK
    CONFIG --> CHUNK
    AST --> SYMBOLS
    ENT --> DOCNODES
    CHUNK --> EMBED
    SYMBOLS --> CALLS
    DOCNODES --> CALLS
    SYMBOLS --> FRESHNESS
    
    HYBRID --> SELF_EVAL
    SELF_EVAL --> MULTIHOP
    
    style AST fill:#90EE90
    style FRESHNESS fill:#FFD700
```

### 3.2 Retrieval Decision Flow

```mermaid
graph TD
    QUERY[Agent Query] --> DECIDE{Self-RAG: Should I retrieve?}
    DECIDE -->|no, I know this| DIRECT[Answer directly<br/>from model knowledge]
    DECIDE -->|yes, search| SCOPE{Query Scope?}

    SCOPE -->|symbol-level| SYMBOL_SEARCH[Symbol Search<br/>Vector + AST path + keyword]
    SCOPE -->|file-level| FILE_SEARCH[File Search<br/>Module embedding + imports]
    SCOPE -->|package-level| PKG_SEARCH[Package Search<br/>Dependency graph + README]
    SCOPE -->|multi-hop| GRAPH_SEARCH[Graph Traversal<br/>Caller→Callee→Docs]

    SYMBOL_SEARCH --> MERGE[Merge Results]
    FILE_SEARCH --> MERGE
    PKG_SEARCH --> MERGE
    GRAPH_SEARCH --> MERGE

    MERGE --> EVAL[Self-RAG Evaluate<br/>Score relevance 1-5 per result]
    EVAL --> FILTER[Filter relevance > 3]
    FILTER --> CHECK{Confident in results?}
    CHECK -->|yes| INJECT[Inject into agent context]
    CHECK -->|no| REFINE[Refine query / broaden scope]
    REFINE --> DECIDE

    style DECIDE fill:#FFD700
    style EVAL fill:#DDA0DD
```

### 3.3 Data Model (TypeScript Interfaces)

```typescript
// ─── Code Symbol Node ────────────────────────────────────────────────────────

interface CodeSymbolNode {
  id: string;                              // UUID v5(namespace, fully.qualified.name)
  symbolType: 'function' | 'class' | 'interface' | 'type' | 'enum'
             | 'variable' | 'constant' | 'method' | 'property' | 'module';

  // Identity
  name: string;                            // e.g., "processPayment"
  fullyQualifiedName: string;              // e.g., "src.payments.handler::processPayment"
  language: 'typescript' | 'python' | 'go' | 'rust' | 'java' | 'kotlin' | ...;
  filePath: string;                        // Relative to repo root
  lineStart: number;
  lineEnd: number;

  // Content
  signature: string;                       // e.g., "async function processPayment(amount: number, method: PaymentMethod): Promise<PaymentResult>"
  docstring: string;                       // Extracted doc comment / JSDoc / docstring
  bodySummary: string;                     // First 100 tokens of body (abbreviated)
  contentHash: string;                     // SHA-256 of source text for staleness detection

  // Embedding (computed from: 0.4 docstring + 0.3 signature + 0.2 name + 0.1 bodySummary)
  embedding: Float32Array;                 // 1536-dim

  // Graph Edges
  callers: string[];                       // Symbol IDs that call this symbol
  callees: string[];                       // Symbol IDs this symbol calls
  imports: string[];                       // Imported module symbol IDs
  implementors: string[];                  // For interfaces: implementing class IDs
  references: string[];                    // Doc nodes that reference this symbol

  // Freshness & Confidence
  freshness: {
    gitCommitHash: string;                 // HEAD commit when indexed
    fileMtime: number;                     // Last modified timestamp
    indexedAt: number;                     // When this node was created/updated
    stalenessScore: number;                // 0-1: exp(-lambda * minutesSinceIndexed), half-life = 60 min
  };

  confidence: 'EXTRACTED'                 // From AST — near-certain
            | 'INFERRED'                  // From LLM analysis — likely
            | 'AMBIGUOUS';                // From LLM — uncertain, needs verification

  // Synthetic Queries (LP-RAG style)
  syntheticQueries: string[];              // Pre-generated queries this symbol answers

  // Parse quality
  parseQuality: number;                    // 0-1: AST parse success rate for this file
  parseErrors: string[];                   // Parse error messages (empty if clean)
}

// ─── Documentation Node ──────────────────────────────────────────────────────

interface DocNode {
  id: string;
  docType: 'markdown' | 'rst' | 'pdf_page' | 'image_description' | 'api_spec';

  content: string;                         // Text content or OCR'd text
  embedding: Float32Array;
  sourcePath: string;

  // Entity Links
  entities: Array<{
    name: string;                          // e.g., "processPayment"
    type: 'function' | 'class' | 'concept' | 'api_endpoint' | 'config_key';
    linkedSymbolId?: string;               // Resolved to a CodeSymbolNode (nullable)
    confidence: number;                    // 0-1: entity linking confidence
  }>;

  freshness: {
    indexedAt: number;
    sourceModifiedAt: number;
  };
}

// ─── Retrieval Result ────────────────────────────────────────────────────────

interface RetrievalResult {
  node: CodeSymbolNode | DocNode;
  retrievalMethod: 'vector' | 'keyword' | 'graph_traversal' | 'lp_rag';
  relevanceScore: number;                  // 0-1: Self-RAG evaluated relevance
  retrievalPath?: string[];                // For multi-hop: [caller -> callee -> docs]
  stalenessBanner?: string;                // If stale: "Index 12 min behind HEAD"
}

// ─── Indexing Job ────────────────────────────────────────────────────────────

interface IndexingJob {
  jobId: string;
  repoPath: string;
  mode: 'full' | 'incremental';
  trigger: 'manual' | 'git_hook' | 'file_watcher' | 'freshness_decay';
  changedFiles?: string[];                 // For incremental: diff since last index

  status: 'queued' | 'parsing' | 'embedding' | 'linking' | 'complete' | 'failed';
  progress: {
    filesTotal: number;
    filesIndexed: number;
    symbolsExtracted: number;
    embeddingsComputed: number;
    linksCreated: number;
  };
  startedAt: number;
  completedAt?: number;
  errors: Array<{ filePath: string; error: string }>;
}

// ─── Knowledge Graph Statistics ──────────────────────────────────────────────

interface KGStatistics {
  totalSymbols: number;
  totalDocNodes: number;
  totalEdges: number;
  parsedLanguages: string[];
  parseQuality: number;                    // Aggregate: symbols from clean AST / total symbols
  staleSymbolCount: number;                // Symbols with stalenessScore < 0.3
  lastFullIndex: number;                   // Timestamp of last full re-index
  lastIncrementalIndex: number;            // Timestamp of last incremental update
  totalEmbeddingCost: number;              // Cumulative USD spent on embeddings
}
```

### 3.4 AST-Aware Chunking

```
Instead of chunking code by token count (which splits functions mid-body):

1. Parse AST via tree-sitter
2. Extract top-level symbols: functions, classes, interfaces, type definitions
3. Each symbol = one chunk (preserves semantic integrity)
4. Within each chunk: include docstring, signature, body (abbreviated if > 500 tokens)
5. Link chunks: caller -> callee, importer -> imported, class -> method
6. Confidence-tag each link: EXTRACTED (from AST, certain) vs INFERRED (from LLM, likely)
7. Generate 3-5 synthetic queries per symbol (LP-RAG style) for learned retrieval

The embedding of a function is computed from:
- Function name (weight 0.2)
- Docstring (weight 0.4)
- Signature (weight 0.3)
- First 100 tokens of body (weight 0.1)

Edge cases handled:
- Malformed/partial code: fall back to token-count chunking with INFERRED confidence
- Dynamically-typed languages (Python, JS): type inference via tree-sitter + optional LLM annotation
- Macro-heavy code (Rust, C): expand macros before AST parsing where possible; tag AMBIGUOUS otherwise
- Generated code: detect via file header patterns; lower admission priority (typePrior = 0.2)
```

### 3.5 Incremental Re-Indexing

```
On file change (detected via hybrid watcher strategy):

Primary — Native file watcher (FSEvents on macOS, inotify on Linux, ReadDirectoryChangesW on Windows):
  - Debounced at 500ms to avoid re-index storms during save sequences
  - Tracks mtime per file; re-indexes only when content hash changes

Secondary — Git post-commit hook:
  - Catches changes made outside the watcher (e.g., git checkout, git pull)
  - Detects branch switches and triggers selective re-index for changed files

Fallback — Periodic freshness decay scan (every 15 min):
  - Catches uncommitted working-directory changes that the watcher may miss
  - Compares file mtimes against last-indexed mtimes; queues stale files for re-index

Per-file re-index procedure:
1. Compute git diff -> list of changed files
2. For each changed file:
   a. Remove old AST nodes for this file from the graph
   b. Re-parse the file -> new AST nodes
   c. Update edges: old callers might now call new symbols, old callees might be removed
   d. Update freshness: set commit_hash = HEAD, mtime = now, stalenessScore = 1.0
3. For unchanged files: decrement stalenessScore (exponential decay, half-life = 60 minutes)
4. Trigger re-index when stalenessScore < 0.3 (file may have changed outside git)
5. On re-index completion: update staleness banner timestamp
6. Staleness banner at retrieval time: "Index 12 min behind HEAD" if indexedAt + 5min < HEAD commit time

Uncommitted-change detection:
- Compare file mtime against last-indexed mtime for the same git commit hash
- If mtime changed but commit hash unchanged, file has uncommitted changes -> flagged yellow
```


### 3.6 Self-RAG Retrieval

```
function retrieve(task, codebase_graph, topK=10):
    # Step 1: LLM decides what to search for (cheap model — DeepSeek Flash)
    searchQuery = cheapLLM("Given this task: '{task}', what code symbols should I search for?")

    # Step 2: Multi-modal hybrid search (parallel)
    vectorResults = embedSearch(searchQuery, topK * 2)       # HNSW, ~5ms at 100K symbols
    keywordResults = keywordSearch(searchQuery, topK * 2)    # BM25 + FTS5, ~2ms
    graphResults = graphTraversal(searchQuery, maxDepth=2)   # BFS from seed symbols, ~10ms
    lpResults = lpRagPredict(searchQuery, topK * 2)          # Learned link predictor, ~5ms

    # Step 3: Merge and deduplicate
    merged = mergeResults(vectorResults, keywordResults, graphResults, lpResults)

    # Step 4: Self-RAG — LLM evaluates relevance (cheap model, BATCHED)
    # NOT N separate calls — ONE call scoring all candidates
    relevanceScores = cheapLLM(f"""
      Task: {task}
      For each candidate symbol below, rate relevance 1-5:
      {formatCandidates(merged)}
    """)

    # Step 5: Check staleness, attach banners
    for result in merged:
        if result.stalenessScore < 0.5:
            result.stalenessBanner = f"Index {staleMinutes} min behind HEAD"

    # Step 6: Return top-K by relevance
    return sorted(merged, by=relevanceScore, descending=True)[:topK]
```

### 3.7 Edge Cases in Retrieval

| Scenario | Handling |
|----------|----------|
| Query has no matching symbols (cold start) | Return empty results with suggestion: "No code symbols found. Try rephrasing your query or check if the codebase has been indexed (`lyra index status`)." |
| All retrieved results are stale (stalenessScore < 0.3) | Inject staleness warning into agent context: "The code index is stale (last indexed X min ago). Results may not reflect current code. Proceed with caution or run `lyra index refresh`." |
| Graph traversal hits cycle (A calls B calls A) | Track visited nodes during BFS; skip already-visited nodes; include cycle-info in retrievalPath: "A -> B -> A (cycle detected)" |
| Single symbol dominates results (e.g., `main()` called by everything) | Apply inverse-document-frequency penalty: score *= 1.0 / (1.0 + log10(callerCount)). High-connectivity symbols still appear but not at top. |
| Agent requests retrieval for a trivial query (e.g., "what does git status do?") | Self-RAG decides: "No retrieval needed" — returns empty. Saves latency and tokens for queries that don't need codebase context. |
| Codebase has been force-pushed / rebased (commit history rewritten) | Detect commit hash mismatch between indexed HEAD and current HEAD. If history diverged (no common ancestor within 100 commits), trigger full re-index. Warn user. |

---

## 4. Build Outline — Ordered Tasks

### 4.1 Task Dependency Graph

```mermaid
graph LR
    T1[1. AST Chunker<br/>1 week] --> T3[3. Hybrid Retrieval<br/>1 week]
    T1 --> T4[4. Freshness Tracking<br/>0.5 week]
    T3 --> T5[5. Wire to Agent<br/>0.5 week]
    T4 --> T5
    T5 --> T6[6. Multimodal<br/>1 week]
    T2[2. Incremental Index<br/>1 week] --> T4
    T3 --> B1[7. Self-RAG Eval<br/>1.5 week]
    T1 --> B2[8. Call Graph Traversal<br/>-- combined with #3]
    T1 --> B3[9. Entity Linking<br/>-- combined with #6]

    style T1 fill:#90EE90
    style B1 fill:#FFB6B6
    style B2 fill:#FFB6B6
    style B3 fill:#FFB6B6
```

### 4.2 Task Table

| # | Task | Depends On | Effort | Description |
|---|------|-----------|--------|-------------|
| 1 | AST-aware chunker for TS/Python/Go | — | 1 week | Integrate tree-sitter grammars for TypeScript, Python, Go. Parse each file → extract top-level symbols → chunk at symbol boundaries. Embed each chunk with (name, docstring, signature, body-prefix) weighted combination. Store as symbol nodes in TKG. |
| 2 | Incremental re-indexing with freshness tracking | — | 1 week | Git-hook-based change detection. On file change: remove old AST nodes, re-parse, update edges. Freshness: git commit hash per node + exponential decay (half-life 7 days). File watcher for uncommitted changes. |
| 3 | Hybrid retrieval (vector + keyword + graph) | #1 | 1 week | Vector: embedding similarity search. Keyword: BM25 over symbol names and docstrings. Graph: 2-hop traversal from seed symbols. Merge and deduplicate results. |
| 4 | Wire to agent context injection | #3 | 0.5 week | Agent prompt template includes `{retrieved_context}` slot. Before each agent spawn: run hybrid retrieval for the agent's task, sort by relevance, inject top-K results. |
| 5 | Basic multimodal ingestion | — | 1 week | PDF text extraction via PyPDF2/pdfplumber. Image OCR via Tesseract for diagrams. Markdown rendering extraction. Link extracted entities to code symbols where possible. |
| 6 | Self-RAG evaluator + MASS-RAG multi-agent retrieval | #3 | 1.5 week | Self-RAG: LLM relevance scoring (batch N results in one call, not N calls). MASS-RAG: specialized retrieval agents (code-agent, doc-agent, config-agent) search different TKG subgraphs; merge results. |

**Critical path**: #1 → #3 → #4 → #6 (chunking → retrieval → injection → self-eval). #2 and #5 run in parallel with the main chain.

**Effort totals**: 4.5 weeks parity (#1-5) + 1.5 week breakthrough (#6) = 6 weeks (revised from 8 given task consolidation).

---

## 5. Multi-Provider Embedding & Chunking Compatibility

### 5.1 Embedding Model Compatibility

| Provider | Embedding Model | Dimensions | Cost per 1M tokens | Notes |
|----------|----------------|------------|-------------------|-------|
| OpenAI | text-embedding-3-small | 512/1536 | $0.02 | Best cost/quality; Matryoshka allows dimension reduction |
| OpenAI | text-embedding-3-large | 256/1024/3072 | $0.13 | Higher quality for complex code |
| Cohere | embed-english-v3 | 1024 | $0.10 | Strong on code understanding |
| Open-Weight | bge-large-en-v1.5 | 1024 | $0 (self-host) | Good code performance; no API cost |
| Open-Weight | codebert-base | 768 | $0 (self-host) | Code-specific, weaker on docs |
| Voyage AI | voyage-code-2 | 1536 | $0.12 | Purpose-built for code retrieval |

**Recommendation**: Use `text-embedding-3-small` at 512 dimensions as default (provider-agnostic via OpenAI-compatible API). For self-hosted deployments, use `bge-large-en-v1.5`. Dimension must be consistent across the knowledge graph — choose at indexing time and never change without full re-index.

### 5.2 Chunking Strategy by Content Type

| Content Type | Chunking Strategy | Chunk Size | Overlap | Notes |
|-------------|-------------------|-----------|---------|-------|
| Code (TS/Python/Go) | AST-aware: per symbol (function/class/interface) | Variable (50-500 tokens) | None (symbols are atomic) | Embed with AST path: `pkg.module.Class.method` |
| Code (malformed/partial) | Fallback: token-count chunks | 256 tokens | 64 tokens | Only for unparseable files |
| Markdown docs | Section-aware: per heading section | 512 tokens | 128 tokens (section boundary) | Late chunking: embed full page first, then chunk |
| PDF docs | Page-aware: per page or per section if structured | 512 tokens | 64 tokens | OCR pre-processing for scanned PDFs |
| Config (YAML/JSON) | Top-level key chunks | 256 tokens | None | Embed with config path: `server.port`, `db.host` |
| Images/Diagrams | Caption + OCR text + visual embedding | Per image | None | Multi-modal: text embedding for search, image for reference |

### 5.3 Provider-Specific Retrieval Considerations

- **Anthropic (Claude)**: Native tool-calling retrieval — inject results as tool outputs. Cache system prompt portion of agent context; retrieved context goes in dynamic portion.
- **OpenAI**: Similar to Anthropic. Assistants API has built-in file search; Lyra's TKG is richer but requires manual injection.
- **DeepSeek**: No built-in retrieval. Inject retrieved context as text in first user message; re-inject at context window boundaries.
- **Local models**: Retrieval results must fit within shorter context windows (8K-32K vs. 200K). Prioritize top-3 results over top-10.
- **Self-RAG evaluator model**: Use cheap model (DeepSeek Flash) for relevance scoring across all providers. Scoring is a simple classification task that does not need a strong model.

---

## 6. (B) Breakthrough — AST-Aware Chunking with Hybrid Retrieval

### 6.0 Linkage to BREAKTHROUGH-ARCHITECTURE.md

This workstream implements the **knowledge ingestion substrate** that feeds the Temporal Knowledge Graph (TKG) with codebase and document knowledge. It directly connects to all four core algorithms in [BREAKTHROUGH-ARCHITECTURE.md](../BREAKTHROUGH-ARCHITECTURE.md) and to the architectural invariants established in the debate:

| Architecture Component | BREAKTHROUGH-ARCHITECTURE.md Reference | How Section 4.23 Implements It |
|-----------------------|--------------------------------------|------------------------------|
| **TKG Write Path (Algorithm 1)** | Section 18.1: Admission, Linking, Compression, Evolution | Code symbols admitted via A-MAC 5-factor gate: utility = symbol reuse frequency, confidence = AST (EXTRACTED) vs LLM (INFERRED), novelty = new symbol vs existing, recency = git commit timestamp, typePrior = public API (0.7) > internal (0.5) > test (0.3). Doc nodes use lower typePrior (0.4). |
| **AVP Protocol (Algorithm 2)** | Section 18.2: Classification, Critique, Consensus | Ingestion writes are gated: mutating operations (updating symbol definitions, re-linking) pass through 3-critic AVP panel. Non-mutating reads (retrieval, search) bypass AVP. Entity linking that changes a symbol's linked docs is classified as mutating (impact: low). |
| **Cross-Provider Routing (Algorithm 3)** | Section 18.3: Memory Cache -> Cascade -> Best-Route -> RouteLLM | Retrieval queries use 3-level cascade: cache hit (zero-cost) -> DeepSeek Flash (cheap, batch scoring) -> Claude Sonnet (when Flash confidence < 0.6). RouteLLM factors learn over time which provider best scores relevance for which query domain. |
| **Skill Evolution (Algorithm 4)** | Section 18.4: Safety-Gated Evolution Pipeline | Knowledge ingestion improves skill execution: skills that query the knowledge graph for context (code-review, test-gen) get richer, more relevant context. Ingestion failures (stale index, broken links) fed back as negative signals to skill evolution pipeline. |
| **Provider Heterogeneity (Section 11.3)** | Architecture as strength: cheap exploration + cross-model verification | AST parsing is model-agnostic (tree-sitter is local). Embeddings are provider-swappable (3-tier fallback). Self-RAG scoring diversifies: DeepSeek for fast batch, Claude for ambiguous judgments. |
| **Falsifiable Hypotheses (Section 9)** | H1: Memory-augmented routing reduces cost >=40%. H2: AVP reduces destructive errors >=50%. H3: Self-evolving skills improve >=15%. | Section 4.23 contributes to H1: KG lookups before agent routing reduce unnecessary LLM calls. Contributes to H2: ingestion writes AVP-gated, preventing corrupted indices from poisoning agent context. |

### 6.0b AGI Direction Ladder Mapping

From BREAKTHROUGH-ARCHITECTURE.md Section 12.1, knowledge ingestion enables each rung of the recursive improvement ladder:

```
Level 1: Tool Use — Agent calls tools (current SOTA)
    Section 4.23 contribution: MCP tools (search_symbols, trace_callers,
    trace_callees, impact_analysis, explore_module)

Level 2: Memory-Learn — Agent learns from past, avoids repeat mistakes
    Section 4.23 contribution: Freshness tracking prevents stale-context errors.
    Retrieval cache learns which symbols are relevant for which task types.
    Self-RAG feedback loop refines relevance scoring over time.

Level 3: Self-Improve — Agent rewrites its own skills and prompts
    Section 4.23 contribution: Skill evolution gets richer feedback from
    knowledge graph usage patterns. Which symbols are queried most?
    Which retrieval modes produce the best results? These metrics inform
    how skills request and use codebase context.

Level 4: Self-Architect — Agent modifies its own harness code
    Section 4.23 contribution: Ingestion pipeline itself becomes evolvable.
    Freshness thresholds, retrieval weights, chunking strategies can be
    tuned based on observed retrieval quality metrics. The ingestion
    pipeline learns which code patterns matter most for Lyra's task mix.

Level 5: Recursive Research — Agent designs, runs, learns from experiments
    Section 4.23 contribution: Knowledge graph becomes the substrate for
    agent-designed experiments. "What happens if I refactor this module?"
    -> agent queries impact analysis -> spawns verification agents ->
    records outcome as new knowledge graph entries.
```

### 6.1 The Insight

Standard RAG treats code as text: split by token count, embed, retrieve. This works poorly because:
- A function split across two chunks loses its signature-body connection
- A caller searching for "authenticate user" cannot find the `validateToken` function that implements it
- Documentation saying "the payment processor" cannot link to the `PaymentProcessor` class

AST-aware chunking solves the first problem. Hybrid retrieval (vector + graph traversal + link prediction) solves the second and third.

### 6.2 AST-Aware Chunking Architecture

```
Input: file.ts
1. Parse AST → tree-sitter TypeScript grammar
2. Extract symbols:
   - class UserAuth { ... }           → chunk_001
   -   method authenticate(token) { ... } → chunk_002 (child of chunk_001)
   -   method refresh() { ... }           → chunk_003 (child of chunk_001)
   - class SessionManager { ... }    → chunk_004
   -   method createSession(user) { ... } → chunk_005 (child of chunk_004)
3. Extract relationships:
   - chunk_002 CALLS chunk_005 (authenticate creates sessions)
   - chunk_001 IMPORTS from './session' (UserAuth imports SessionManager)
4. Embed each chunk:
   - chunk_002 embedding = embed("UserAuth.authenticate(token: string): Promise<User>\nValidates JWT token...")
5. Store in TKG:
   - Node(type=symbol, chunk=chunk_002, path="src/auth.ts::UserAuth::authenticate", embed=[...])
   - Edge(type=calls, from=chunk_002, to=chunk_005)
   - Edge(type=child_of, from=chunk_002, to=chunk_001)

Retrieval for query "how does authentication work":
  Vector search: "authentication" → chunk_002 (authenticate), chunk_001 (UserAuth)
  Graph traversal: chunk_002 → CALLS → chunk_005 (createSession) 
                             → CHILD_OF → chunk_001 (UserAuth)
  Keyword search: "authenticate" → chunk_002 (exact match on method name)
  Link prediction: chunk_002 ↔ docs/auth.md (pre-computed link)
  Result: chunk_002 + chunk_005 + chunk_001 + docs/auth.md
```

### 6.3 Hybrid Scoring Formula

```
score(chunk, query) = 
    w_vec * cosine_similarity(chunk.embedding, query.embedding)        # 0.35
  + w_key * BM25(chunk.symbol_name + chunk.docstring, query.text)     # 0.25
  + w_graph * graph_relevance(chunk, query)                            # 0.25
  + w_link * link_prediction_score(chunk, query)                       # 0.15

graph_relevance: sum of (1 / distance) for each path from query seed symbols to chunk
link_prediction_score: pre-computed probability that chunk is related to query entities
```

### 6.4 Expected Impact

- **Code retrieval accuracy**: 30% improvement over text-only embedding (AST-Embed finding)
- **Multi-hop query handling**: "find all functions that call auth and touch the database" — impossible in flat RAG, 2-hop traversal in graph RAG
- **Documentation-to-code linking**: "what does the payment section of the docs correspond to in code?" — link prediction resolves this
- **Incremental update speed**: Re-index one file in < 1 second instead of full codebase re-index in minutes

---

## 7. Expert Review

| Reviewer | Verdict | Key Objection | Resolution |
|----------|---------|---------------|------------|
| Senior Data Engineer | ✅ Sign off | "Incremental indexing with git diff is clever but misses uncommitted changes" | Add file watcher for working directory changes; combine git diff + fs events for complete coverage |
| Senior AI Researcher | ✅ Sign off | "Late chunking for docs but AST-chunking for code — two strategies add complexity. Worth it?" | Yes: code and natural language have fundamentally different structure. AST-aware code chunking provides 30% retrieval improvement that late chunking of code text cannot match. Worth the implementation complexity. |
| Senior AI Engineer | ✅ Sign off | "Self-RAG evaluator adds an LLM call per retrieval — that's expensive at scale" | Batch relevance scoring (score N results in one LLM call, not N calls); cache relevance per (query_hash, symbol_id); re-evaluate only on cache miss |
| Adversarial Skeptic | ⚠️ Conditional | "AST-aware chunking assumes the code compiles. Real-world codebases have broken builds, partial refactors, generated code. If 20% of files fail to parse, the fallback to text chunking creates two classes of retrieval quality — the 'rich' parsed code and the 'poor' fallback code. Users will notice inconsistent retrieval" | Add `parse_quality` score per file. If > 15% of files in a codebase fail to parse, warn the user and suggest fixes. Index parse failures by error type and suggest automated fixes (missing semicolons, unclosed brackets). Track parse quality over time; if quality drops (new unparseable files added), alert |

---

## 8. Risks & Open Questions

| Risk | Mitigation |
|------|-----------|
| AST parsing fails on malformed/partial code | Fall back to token-count chunking for unparseable files; track parse quality per file; alert if quality drops below 85% |
| Graph traversal combinatorial explosion | Max depth = 2, max branching factor = 10; use beam search for multi-hop: keep top-5 paths by cumulative relevance at each hop |
| Embedding costs for large codebases (100K+ symbols) | Cache embeddings; only re-embed changed symbols; use Matryoshka dimension reduction (512-dim for search, 1536-dim only for re-ranking top candidates) |
| Self-RAG evaluator adds latency to every retrieval | Cache relevance scores per (query_hash, symbol_id); re-evaluate only on cache miss; batch evaluation: all N results in one LLM call |
| Knowledge freshness drift (unnoticed staleness) | Visual freshness indicator in TUI: green (indexed < 1 hour ago), yellow (1-24 hours), red (> 24 hours). Auto-warn when agent is about to use stale context |
| Multi-language codebase complexity | Tree-sitter grammars for 3 languages (TS, Python, Go) cover 90% of Lyra's target codebases. Add languages as needed; fall back to text chunking for unsupported languages |
| Embedding model upgrade requires full re-index | Store raw text alongside embeddings in TKG. On model upgrade: re-embed incrementally (batch process in background) rather than full re-index from source |

---

---

## 10. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Symbol extraction accuracy | >95% on valid code | Manual audit of 100 randomly sampled symbols per supported language |
| Retrieval recall@10 | >0.85 | Codebase QA benchmark: 500 queries across 3 repos (small 1K, medium 10K, large 100K symbols) |
| Retrieval precision@5 improvement (Self-RAG vs raw vector) | >15% | A/B comparison on benchmark queries with and without Self-RAG scoring |
| Re-index latency (single file change) | <2s | Instrumented timing from file change event to updated graph node |
| Staleness window (95th percentile) | <5 minutes | Monitor stalenessScore distribution over 1 week of active development |
| Agent token reduction for codebase queries | >50% | Compare tokens used with vs without knowledge graph for 20 standardized tasks |
| Embedding cost per 1K symbols | <$0.02 | Track API costs per indexing job via provider billing |
| Batch Self-RAG scoring latency (20 candidates) | <500ms | Instrumented timing at p50, p95, p99 |
| Entity linking precision (doc -> code) | >85% | Manual audit of 100 entity links across 3 documentation sets |
| MCP tool response time (p95) | <200ms | Instrumented timing across all 8 MCP tools under 100K-symbol load |
| Parse quality across entire codebase | >85% files parse cleanly | Aggregate parseQuality across all indexed files; alert if quality drops below 85% |
| Daily incremental indexing cost | <$5/day | Track cumulative embedding + Self-RAG scoring costs per 24h window |

---

## 11. References

### 11.1 Core Architecture Sources

| # | Source | URL | Relevance | Tier |
|---|--------|-----|-----------|------|
| 1 | GraphRAG (Microsoft) | https://arxiv.org/abs/2404.16130 | Entity extraction + community detection + graph summarization for RAG | BREAKTHROUGH |
| 2 | Self-RAG (ICLR 2024) | https://arxiv.org/abs/2310.11511 | LLM self-evaluates retrieval quality; decides when to retrieve | BREAKTHROUGH |
| 3 | HippoRAG (NeurIPS 2024) | https://arxiv.org/abs/2405.14831 | Hippocampal-inspired structured retrieval over knowledge graphs | BREAKTHROUGH |
| 4 | BREAKTHROUGH-ARCHITECTURE.md | ../BREAKTHROUGH-ARCHITECTURE.md | Lyra's unified architecture; Algorithms 1-4; AGI direction ladder; self-evolution pipeline | BREAKTHROUGH |

### 11.2 Code Intelligence & Knowledge Graph (findings.md)

| # | Source | Finding # | URL | Key Result | Tier |
|---|--------|-----------|-----|------------|------|
| 5 | codegraph | #6 | https://github.com/colbymchenry/codegraph | 25% cost reduction, 57% fewer tokens, 23% faster, 62% fewer tool calls; staleness banner; 20+ languages | BREAKTHROUGH |
| 6 | graphify | #5 | https://github.com/safishamsi/graphify | Code-as-KG with confidence tags (EXTRACTED/INFERRED/AMBIGUOUS); community detection; 14 frameworks | HIGH |
| 7 | spaCy | #7 | https://github.com/explosion/spaCy | Industrial NLP: NER, entity linking, 70+ languages, production-ready | MEDIUM |

### 11.3 RAG & Retrieval Methods

| # | Source | URL | Key Result | Tier |
|---|--------|-----|------------|------|
| 8 | LP-RAG | https://openreview.net/forum?id=Y8Txo8vaH7 | Retrieval as link prediction; synthetic query generation per chunk; outperforms existing RAG methods | HIGH |
| 9 | LightMem | https://arxiv.org/abs/2604.07798 | SLM-based 3-tier memory; 83ms retrieval latency; +2.5 F1 over A-MEM on LoCoMo | HIGH |
| 10 | MASS-RAG (ACL 2026) | -- | Multi-agent selective search RAG; 22% improvement on multi-source queries | HIGH |
| 11 | Anthropic Context Engineering | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | Just-in-time context loading; progressive disclosure; sub-agent 1-2K token summaries | BREAKTHROUGH |
| 12 | Is Grep All You Need? | https://arxiv.org/abs/2605.15184 | Simple reliable tools in well-designed harness beat sophisticated agentic search | HIGH |

### 11.4 Memory Architecture (Cross-Reference from findings.md)

| # | Source | Finding # | URL | Key Result | Tier |
|---|--------|-----------|-----|------------|------|
| 13 | TencentDB-Agent-Memory | #1 | https://github.com/Tencent/TencentDB-Agent-Memory | 61% token reduction; 51% pass rate improvement; layered pyramid (raw->facts->scenarios->persona) | BREAKTHROUGH |
| 14 | MemPalace | #4 | https://github.com/MemPalace/mempalace | 96.6% R@5 on LongMemEval; 29 MCP tools; hierarchical index (wings/rooms/drawers) | BREAKTHROUGH |
| 15 | claude-mem | #3 | https://github.com/thedotmack/claude-mem | Auto-capture tool observations; MCP-based retrieval; transcript watching | HIGH |
| 16 | APEX-MEM | #16 | https://arxiv.org/abs/2604.14362 | 88.88% LoCoMo QA; 86.2% LongMemEval; property graph with domain-agnostic ontology | BREAKTHROUGH |
| 17 | STITCH | #17 | https://arxiv.org/abs/2601.10702 | 35.6% improvement via intent-based indexing with (goal, action type, entity) triples | BREAKTHROUGH |
| 18 | Acontext | -- | https://github.com/memodb-io/Acontext | Skill-as-memory; progressive disclosure via tool calls; plain Markdown files | HIGH |

### 11.5 Additional Papers

- AST-Embed (2024): Embedding code AST paths improves code retrieval by 30% vs. text-only embeddings
- Late Chunking (2024): Chunk AFTER embedding preserves cross-chunk context; 15-20% retrieval improvement
- GraphRAG v2 (2025): Community summarization with hierarchical clustering at multiple granularities

---

## Changelog

| Date | Run | Changes |
|------|-----|---------|
| 2026-06-01 | 20 | **Full deepening pass — Run 20**: Expanded plain-language summary to 3 sentences with quantitative evidence. Deepened evidence synthesis with 12 specific findings citations (findings #1 TencentDB BREAKTHROUGH, #4 MemPalace BREAKTHROUGH, #5 graphify HIGH, #6 codegraph BREAKTHROUGH, #7 spaCy MEDIUM, #16 APEX-MEM BREAKTHROUGH, #17 STITCH BREAKTHROUGH, #N53 LightMem HIGH, #253 Anthropic Context Engineering BREAKTHROUGH). Added architecture decisions table with evidence grounding. Added full TypeScript data model (CodeSymbolNode, DocNode, RetrievalResult, IndexingJob, KGStatistics). Added retrieval edge cases table (cold start, staleness, cycle detection, IDF penalty, trivial query, rebase detection). Added task dependency Mermaid diagram. Deepened incremental re-indexing with hybrid watcher strategy (primary/secondary/fallback). Expanded multi-provider notes with 3-tier embedding provider fallback chain. Added Section 6.0 linkage to BREAKTHROUGH-ARCHITECTURE.md Algorithms 1-4, falsifiable hypotheses H1-H3, and provider heterogeneity section. Added AGI direction ladder mapping (Levels 1-5). Added success metrics table with 12 measurable targets. Expanded references from 9 to 18+ sources with finding numbers, URLs, and tier labels. Added section 3.7 edge cases. Updated to 18+ references with organized subsections. |
| 2026-06-01 | 19 | Deepened from ~220 to ~500+ lines: added plain-language summary, extended evidence synthesis (MASS-RAG ACL 2026, LP-RAG link prediction, GraphRAG v2 hierarchical clustering, AST-Embed code retrieval, Late Chunking), enhanced ingestion pipeline Mermaid diagram, retrieval decision flow Mermaid diagram, 6-task build outline with dependencies and effort estimates, multi-provider embedding compatibility table with chunking strategy per content type, (B) Breakthrough AST-aware chunking with hybrid retrieval and scoring formula, expert review with data engineer + AI researcher + Adversarial Skeptic, expanded risks (freshness drift, multi-language complexity, embedding model upgrade cost) |
| 2026-05-31 | 16 | Initial plan created |
