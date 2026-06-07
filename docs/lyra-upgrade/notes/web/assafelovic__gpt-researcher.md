# assafelovic/gpt-researcher — Deep-Read

**Source**: https://github.com/assafelovic/gpt-researcher
**Stars**: ~15k+ | **Language**: Python 3.11+ | **License**: Apache 2.0 (LICENSE file), declared MIT in pyproject.toml/setup.py metadata
**Last release**: v0.14.7
**Package**: pip install gpt-researcher

---

## 1. Headline Feature & Mechanism

**Headline**: The first open-source autonomous deep research agent for web and local document research. Produces detailed, factual, unbiased research reports with citations.

**How the code really works** (Plan-and-Solve + RAG):

The core resides in `gpt_researcher/agent.py` (`GPTResearcher` class) and `gpt_researcher/skills/researcher.py` (`ResearchConductor`). The pipeline is:

1. **Agent selection** — An LLM call analyzes the user query and assigns a persona (e.g., "Senior Data Scientist") whose system prompt shapes research framing. Done in `actions/agent_creator.py`.

2. **Research planning** — `ResearchConductor.plan_research()` runs an initial web search on the raw query, then calls `plan_research_outline()` (in `actions/query_processing.py`) which uses the LLM to decompose the topic into 3-5 sub-queries, each with a stated research goal.

3. **Parallelized execution** — Each sub-query is processed concurrently via `asyncio.gather()` in `_get_context_by_web_search()`. For each sub-query:
   - All configured **retrievers** fire in sequence (Tavily, DuckDuckGo, Google, Bing, Exa, Arxiv, PubMed, Semantic Scholar, MCP servers, etc. — 18 backends in `gpt_researcher/retrievers/`).
   - URLs are scraped by the browser manager (`skills/browser.py`, using BeautifulSoup or Playwright).
   - Scraped content is compressed via embedding similarity filtering (`context/compression.py` — `ContextCompressor`) to keep only chunks relevant to the sub-query.

4. **Context aggregation** — All sub-query results are concatenated. Optional curation (`SourceCurator` in `skills/curator.py`) re-ranks sources.

5. **Report generation** — `ReportGenerator.write_report()` (in `skills/writer.py`) feeds the full context + agent role + tone into the "smart" LLM (default `gpt-4.1`) to produce a cohesive report. Supports pre-generated inline images via Google Gemini/Imagen.

6. **Deep Research mode** — A separate recursive tree search in `skills/deep_research.py` (`DeepResearchSkill`). Configurable breadth (num queries per level) and depth (recursion levels). Each node spawns a full `GPTResearcher` instance. Context is trimmed at 25k words to stay within LLM limits.

---

## 2. Architecture & Core Modules

**Entry points**:
- `main.py` — Starts FastAPI + uvicorn server
- `cli.py` — CLI wrapper for one-shot research, supports 7 report types + PDF/DOCX export
- `gpt_researcher/__init__.py` — Exports `GPTResearcher` class for programmatic use

**Package structure** (`gpt_researcher/`):

| Module | Purpose |
|--------|---------|
| `agent.py` | Main `GPTResearcher` orchestrator (3000+ lines, holds all state) |
| `skills/researcher.py` | `ResearchConductor` — web search, sub-query execution, MCP orchestration |
| `skills/deep_research.py` | `DeepResearchSkill` — recursive tree-based research (breadth/depth params) |
| `skills/writer.py` | `ReportGenerator` — report writing delegation |
| `skills/context_manager.py` | Context retrieval via embeddings |
| `skills/curator.py` | Source curation/re-ranking |
| `skills/browser.py` | URL scraping management |
| `skills/image_generator.py` | AI image generation (Gemini/Imagen) |
| `actions/` | Functional-layer: agent_creator, query_processing, report_generation, retriever factory, web_scraping, markdown_processing |
| `config/` | `Config` class + TypedDict defaults; env vars override file configs |
| `context/` | `ContextCompressor`, `VectorstoreCompressor` — embedding-based content filtering |
| `retrievers/` | 18 pluggable search backends (tavily, duckduckgo, google, bing, arxiv, pubmed, exa, mcp, etc.) |
| `llm_provider/` | `GenericLLMProvider` — abstracts openai, ollama, litellm |
| `memory/` | Embedding + local memory backend |
| `document/` | Document loaders (local files, Azure, LangChain, online) |
| `scraper/` | Web scraping implementations (bs4, playwright, firecrawl) |
| `vector_store/` | Vector store wrapper |
| `mcp/` | MCP integration (client + retriever) |
| `utils/` | Enums (ReportType, ReportSource, Tone), LLM helpers, cost tracking, logging |

**Backend** (`backend/server/app.py`): FastAPI server with WebSocket streaming for real-time progress, REST endpoints for research management, report store (SQLite).

**Frontend**: Two options — lightweight HTML/CSS/JS served by FastAPI, or full NextJS + Tailwind app in `frontend/`.

**Data flow**:
```
User Query
  -> choose_agent() -> persona assignment
  -> plan_research() -> web search + LLM -> sub-queries
  -> asyncio.gather(sub_queries)
       -> retriever.search() * N retrievers -> URL list
       -> scraper.browse_urls() -> raw content
       -> ContextCompressor (embedding filter) -> relevant chunks
  -> aggregated context
  -> (optional) SourceCurator
  -> ReportGenerator (LLM) -> final report with citations
  -> (optional) PDF/DOCX export
```

**Configuration**: Hierarchical — defaults in `config/variables/default.py` (TypedDict), overridden by JSON config file, overridden by environment variables. Key triple: `FAST_LLM` (gpt-4o-mini), `SMART_LLM` (gpt-4.1), `STRATEGIC_LLM` (o4-mini). Retriever selection via comma-separated `RETRIEVER` env var.

---

## 3. Performance/Benchmarks

**Directly from the repo**:

- **Deep Research mode**: ~5 minutes per research, ~$0.40 cost using o3-mini on "high" reasoning effort (README).
- **SimpleQA evaluation** (`evals/simple_evals/`): 92.9% accuracy, F1 = 0.925 on 100-problem factual test set. Costs ~$0.14/query average. Uses GPT-4-turbo as grader, GPTResearcher default config (gpt-4o-mini + Tavily).
- **Hallucination evaluation** (`evals/hallucination_eval/`): 0% hallucination rate reported in example output (small sample).
- **Cost tracking**: Built-in per-step cost accounting in `GPTResearcher.add_costs()` + `get_step_costs()`. Costs broken down by agent_selection, research, report_writing.
- **Aggregation guarantees**: README claims 20+ sources per report for "objective conclusions" — the default `max_search_results_per_query = 5` per retriever, multiplied by sub-queries.
- **Scaling**: Default scraper workers = 15 concurrent; rate-limit delay configurable. Embedding-based compression threshold defaults to 8KB — documents under this skip expensive pipeline entirely, "reducing latency by 40-50%."

**No independent third-party benchmarks posted in the repo.**

---

## 4. Trade-offs

**Wins**:
- Broadest retriever ecosystem in any open-source research agent (18 backends including MCP).
- Deep Research mode with tree search (configurable breadth/depth) beats flat sub-query approaches on coverage.
- Built-in cost accounting — every LLM call is tracked to the step level.
- Strong SimpleQA eval results (92.9%) suggest good factuality.
- Document source parity — local PDFs, DOCX, PPTX, Excel, Azure Blob, LangChain stores.
- Image generation (Gemini/Imagen) for inline illustrations.
- MCP server integration extending research to GitHub, databases, custom APIs.

**Losses**:
- Heavy LLM dependency: every research step (agent selection, query planning, summarization, report generation) calls an LLM. Costs scale linearly with sub-queries and depth.
- Context window capped: `smart_token_limit` defaullts to 6000 tokens; even the deep research context is trimmed at 25k words. Longer reports require multi-pass writing.
- Scraping reliability is uneven — depends on the chosen backend. JavaScript-rendered sites require Playwright, which is an optional dependency.
- No built-in caching layer for repeated queries. Each run is from scratch.
- `visited_urls` deduplication is session-scoped only — no persistent URL cache.
- MCP integration is still maturing (strategy options: "fast"/"deep"/"disabled" with backward compatibility shims for renamed params).
- Architecture note: `GPTResearcher` constructor takes ~40+ parameters, which indicates an evolving API surface rather than settled design.

**Known issues from environment/config** (`.env.example` comments):
- Firecrawl Free tier: only 2 concurrent browsers, 10 req/min — conflicts with default scraper_workers=15.
- COMPRESSION_THRESHOLD optimization (8KB) is a fast-path that skips embedding filtering entirely — could miss relevant content for dense but short documents.

---

## 5. Design Rationale

The project is explicitly motivated by the Plan-and-Solve paper (arXiv:2305.04091) and RAG (arXiv:2005.11401). Key design decisions:

1. **Sub-query parallelism as the weapon against hallucination**: By decomposing a query into multiple sub-questions, each researched independently across 20+ sources, the system cross-validates facts. The README states: "the more sites we scrape the less chances of incorrect data."

2. **Agent persona selection**: Rather than a single generic system prompt, the agent self-selects a domain-relevant persona (e.g., "Senior Data Engineer" for a tech query). This mimics human expert behavior and improves relevance filtering.

3. **Pluggable retriever architecture**: The `retriever.py` factory + 18 directory-based backends means the research source can be swapped without touching pipeline code. This is crucial for the "reduce bias" goal — aggregating across search engines prevents any single provider's ranking from dominating.

4. **Skill decomposition**: The `skills/` layer (Researcher, Writer, ContextManager, Curator, BrowserManager, DeepResearcher) separates concerns that are increasingly complex. The `actions/` layer provides stateless functional counterparts for reuse outside the class.

5. **Async-first from the ground up**: `asyncio.gather()` for sub-queries, `asyncio.to_thread()` for blocking retriever calls, async file I/O, async WebSocket streaming. This is necessary for responsive UX during research that can take 2-5 minutes.

6. **Two-tier LLM strategy**: Fast LLM (gpt-4o-mini) for planning and summarization; Smart LLM (gpt-4.1) for final report generation; Strategic LLM (o4-mini) for deep research reasoning. This optimizes cost vs. quality.

---

## 6. Transfer to Lyra

**Transferable Idea**: **Plan-and-Solve with configurable breadth/depth parallelism**.

Lyra's current research/information-gathering pipeline (in workstream §4.x, likely §4.3 for retrieval or §4.5 for agent orchestration) could adopt:
- The **sub-query decomposition pattern**: Given a user query, generate 3-5 parallel sub-queries with explicit research goals, run them concurrently, and aggregate results.
- The **tree-based deep research** recursion pattern (breadth=number of parallel queries per level, depth=max recursion). This is valuable for Lyra's planned "deep research" capability.
- The **pluggable retriever factory** pattern: Lyra's current retriever system could adopt the registry-by-directory pattern so new search backends (arxiv, pubmed, semantic scholar, MCP) can be added without modifying pipeline code.
- The **cost accounting** per-step model: Each LLM/research step tracked with `add_costs()`.
- The **context compression** optimization: Small-content fast-path (skip embedding filter below 8KB) + embedding-based relevance filtering for large content.

| Aspect | Value |
|--------|-------|
| **Workstream route** | §4.3 (Retrieval/Context pipeline) — adopt sub-query planning + pluggable retrievers. Could also route to §4.5 (Agent orchestration) for the DeepResearch recursive pattern. |
| **Impact** | 7 (high) — Sub-query parallelism and tree-based depth would directly address Lyra's known weakness in shallow single-pass research. |
| **Effort** | 5 (medium) — The pattern is well-documented in code, but adapting the async sub-query orchestration and context compression into Lyra's existing pipeline requires moderate engineering. |
| **Tier** | Tier 1 (high value, moderate effort) |
| **LICENSE** | Apache 2.0, permissive — can incorporate into any project. |
