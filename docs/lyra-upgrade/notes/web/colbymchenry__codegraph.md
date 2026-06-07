# @colbymchenry/codegraph — Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: A local-first code intelligence library + CLI + MCP server that builds a semantic knowledge graph (symbols, edges, files) from any codebase using tree-sitter AST parsing, stores it in SQLite with FTS5 full-text search, and exposes it to AI agents over the Model Context Protocol — replacing grep/read exploration with sub-millisecond structural queries.

**Mechanism (end-to-end data flow)**:

1. **Indexing phase**: `files -> ExtractionOrchestrator -> tree-sitter AST parsing -> nodes/edges/files stored in SQLite`
   - File scanning uses `git ls-files` (fast path) or filesystem walk (fallback); respects .gitignore at all levels
   - AST parsing runs in worker threads (WASM-based tree-sitter grammars), with worker recycling every 250 parses to reclaim WASM linear memory
   - Files >1MB are skipped; single files are sent with a 10s + 10s/100KB timeout
2. **Resolution phase**: `ReferenceResolver` resolves unmatched references via import analysis, name matching, and framework-specific patterns (14+ web frameworks: Express, Laravel, Rails, FastAPI, Django, Flask, Spring, Gin, Axum, ASP.NET, Vapor, React Router, SvelteKit, Vue/Nuxt)
3. **Graph traversal**: `GraphTraverser` (BFS/DFS), `GraphQueryManager` support call graphs, impact radius, type hierarchy, dead code detection, circular dependencies
4. **Context/query phase**: `ContextBuilder` uses hybrid search (FTS5 + exact symbol lookup + CamelCase boundary matching) with graph connectivity ranking (Random Walk with Restart / personalized PageRank) to surface relevant symbols
5. **MCP tools**: `codegraph_explore` (primary — one call replaces grep+read loop), `codegraph_search`, `codegraph_node`, `codegraph_callers`, `codegraph_callees`, `codegraph_impact`, `codegraph_files`, `codegraph_status`
6. **Adaptive output budgeting**: The `codegraph_explore` response size scales to project file count (6 tiers, from 13KB on <150-file repos to 24KB on 15k+); tiny repos get fewer tools exposed (5 core tools only); generated files are down-ranked; test files are excluded unless the query is about tests

## 2. Architecture & Core Modules

**Language**: TypeScript
**Runtime**: Node.js (>=20, <25; hard block on 25.x due to V8 turboshaft WASM Zone bug)
**License**: MIT

**Layer diagram** (from CLAUDE.md):
```
files -> ExtractionOrchestrator (tree-sitter) -> DB (nodes/edges/files)
              |
       ReferenceResolver (imports, name-matching, framework patterns)
              |
       GraphQueryManager / GraphTraverser (callers, callees, impact)
              |
       ContextBuilder (markdown/JSON for AI consumption)
```

**Key modules**:

- `src/index.ts` — `CodeGraph` class (facade): lifecycle (init/open/close), indexing (indexAll/sync), graph queries (callers/callees/impact/traverse), context building (buildContext/findRelevantContext), file watching
- `src/bin/codegraph.ts` — CLI (commander): 15 subcommands (install, init, uninit, index, sync, status, query, files, context, callers, callees, impact, affected, serve --mcp, upgrade, unlock)
- `src/extraction/` — `ExtractionOrchestrator`, tree-sitter wrappers, 18 per-language extractors (typescript, javascript, python, go, rust, java, c/cpp, csharp, php, ruby, swift, kotlin, dart, svelte, vue, scala, lua, luau, pascal, objc), plus standalone extractors for Svelte/Vue/Liquid/Razor/DFM/MyBatis. Parsing runs in a worker thread (`parse-worker.ts`) with WASM recycle interval of 250 files
- `src/db/` — `DatabaseConnection`, `QueryBuilder`, `schema.sql`. SQLite with WAL mode, FTS5 virtual table for full-text search on node names/docstrings/signatures. Uses Node's built-in `node:sqlite` (Node 22.5+) with transparent wasm fallback
- `src/resolution/` — `ReferenceResolver`, import resolver, name matcher, 22 framework resolvers (one file each). LRU-cached with configurable size. Handles built-in/external symbol filtering per language (JS/Python/Go/Rust/Pascal/C/C++ sets)
- `src/graph/` — `GraphTraverser` (BFS, DFS, impact radius, path finding), `GraphQueryManager` (high-level queries, circular deps, dead code, file dependencies)
- `src/context/` — `ContextBuilder` + `formatter.ts`. Hybrid search strategy: extract symbols from query -> exact FTS search -> CamelCase boundary matching -> compound term matching -> graph connectivity ranking (RWR) -> per-file diversity cap
- `src/mcp/` — MCP server with 3 runtime modes: (1) Direct single-process, (2) Proxy (stdio-to-socket to shared daemon), (3) Detached daemon (background process serving multiple proxies over Unix socket). PPID watchdog for clean shutdown on parent death. Daemon uses O_EXCL lockfile arbitration + client refcount + idle timeout
- `src/installer/` — Multi-agent installer supporting Claude Code, Cursor, Codex CLI, opencode, Hermes Agent, Gemini CLI, Antigravity IDE, Kiro. Each agent has one target file in `installer/targets/`. Uses `jsonc-parser` for surgical config edits preserving user comments
- `src/sync/` — `FileWatcher` with native FSEvents/inotify/RDCW, debounce, git-hook helpers, worktree detection
- `src/search/` — FTS5 query parser and utilities (stemming, test file detection, path scoring)

**Database schema**: 7 tables (schema_versions, nodes, edges, files, unresolved_refs, nodes_fts, project_metadata) with composite indexes on (source, kind) and (target, kind) for fast graph traversal.

**Node types (21)**: file, module, class, struct, interface, trait, protocol, function, method, property, field, variable, constant, enum, enum_member, type_alias, namespace, parameter, import, export, route, component
**Edge types (12)**: contains, calls, imports, exports, extends, implements, references, type_of, returns, instantiates, overrides, decorates

## 3. Performance/Benchmarks

Tested across 7 real-world open-source codebases (7 languages), agent answering one architecture question WITH vs WITHOUT CodeGraph, median of 4 runs:

| Codebase | Language | Cost | Tokens | Time | Tool calls |
|----------|----------|------|--------|------|------------|
| VS Code | TS, ~10k files | 18% cheaper | 64% fewer | 11% faster | 81% fewer |
| Excalidraw | TS, ~640 | even | 25% fewer | 27% faster | 40% fewer |
| Django | Python, ~3k | 8% cheaper | 60% fewer | 13% faster | 77% fewer |
| Tokio | Rust, ~790 | even | 38% fewer | 18% faster | 57% fewer |
| OkHttp | Java, ~645 | 25% cheaper | 54% fewer | 31% faster | 50% fewer |
| Gin | Go, ~110 | 19% cheaper | 23% fewer | 24% faster | 44% fewer |
| Alamofire | Swift, ~110 | 40% cheaper | 64% fewer | 33% faster | 58% fewer |

**Averages**: 16% cheaper, 47% fewer tokens, 22% faster, 58% fewer tool calls.

**Current build (re-validated on Opus 4.8, 2026-06-02)**: 35% cost savings, 57% tokens, 46% time, 71% tool calls (average across all 7 repos).

**Mechanism**: Far fewer turns over much smaller accumulated context (not cache-ability). The without-CodeGraph arm's huge token volume is mostly cheap cache-reads, which is why token savings (57%) look bigger than cost savings (35%). Zero file reads on most repos with CodeGraph; 4-11 file reads without.

**Cost stays flat-to-cheaper everywhere**, largest on small repos (Alamofire -40%, OkHttp -25%), roughly break-even on response-heavy ones (Excalidraw, Tokio) where CodeGraph trades many small grep/read round-trips for a few large, cache-heavy tool responses.

## 4. Trade-offs

**Wins**:
- Huge reduction in agent tool calls (58-81% on large repos, 40-58% on small)
- Sub-millisecond structural reads vs grep/read loops (seconds to minutes)
- 100% local, no API costs for indexing, no data leaves the machine
- Deterministic extraction (AST-based, not LLM-summarized) — no hallucination risk in the index
- Agent-agnostic via MCP protocol (works with 8+ agent platforms)
- Rich graph queries: callers, callees, impact radius, trace, type hierarchy, circular deps, dead code
- Adaptive output budgeting prevents context bloat on all project sizes
- Framework-aware: 14+ web framework resolvers produce route nodes and reference edges
- Self-contained: bundled binary with no Node.js dependency for end users; npm for devs

**Losses**:
- Indexing lag: ~1 second behind file writes (watcher debounce + re-parse)
- Cross-file resolution is best-effort name matching; ambiguous calls may return multiple candidates
- No live correctness validation — still needs TypeScript compiler / test suite / linter
- WASM memory management: tree-sitter grammars run in WASM, which can grow but never shrink; worker recycling adds complexity
- 1MB max file size limit (reasonable for source, but generated files are skipped)
- Node 25.x hard block due to V8 turboshaft bug (crash in WASM compilation)
- Requires per-project initialization (`codegraph init -i`)
- Context-building uses heuristic scoring, not embeddings — can miss semantic connections that vector search would catch
- Worker thread recycling on large repos adds ~250ms overhead per batch
- Daemon mode complexity: O_EXCL lockfiles, Unix sockets, PPID watchdog, client refcount, idle timeout

## 5. Design Rationale

**Why AST over embeddings**: Deterministic, no token cost for extraction, no drift between index and code. "Extraction is deterministic — derived from AST, not LLM-summarized" (CLAUDE.md).

**Why SQLite (especially Node built-in)**: Zero dependencies, WAL mode for concurrent reads without blocking writers, FTS5 for full-text search, transparent wasm fallback on older Node versions. Single file database is easy to cache, backup, and delete.

**Why worker threads for parsing**: WASM tree-sitter grammars can OOM on large files. Worker isolation contains crashes and enables clean restart. Worker recycling every 250 files reclaims WASM linear memory (WebAssembly spec limitation: memory grows but never shrinks).

**Why "adapt the tool to the agent — don't try to change the agent"** (CLAUDE.md): The core design constraint. Tools are designed so agents naturally call them given their existing behavior patterns. If a change requires the agent to behave differently, it hits the "low-salience wall and won't land." This drives the decision to make `codegraph_explore` the primary tool — it returns verbatim source (Read-equivalent) so the agent uses it without changing its approach.

**Why MCP over custom protocol**: Agent-agnostic. The same server works with Claude Code, Cursor, Codex, opencode, Hermes Agent, and any MCP-compatible client. The proxy/daemon architecture enables shared connections across multiple agent sessions from different terminals.

**Why per-project indexes**: Each project's `.codegraph/` directory is self-contained. Enables per-project `.gitignore` handling, independent version tracking, and parallel indexing of unrelated projects.

**Why hybrid search over pure FTS**: FTS5 catches token matches but misses CamelCase boundaries (e.g., "Search" inside "TransportSearchAction"). The context builder combines exact symbol lookup, FTS, CamelCase substring matching, compound term matching, and graph connectivity ranking (random-walk-with-restart) for robust structural discovery.

**Adaptive output budgeting**: The `codegraph_explore` output budget scales to project size (6 tiers) because a 35KB response that works for VS Code crowds out relevant content on a 110-file repo. Tiny repos also get fewer exposed tools (5 core only) because on <500 file projects, the omitted tools reduce to one grep.

## 6. Transfer to Lyra

**Core idea**: Lyra should adopt a pre-indexed code knowledge graph with an MCP tool surface designed around "one call replaces grep/read." Specifically, the **adaptive output budget** mechanism — sizing MCP tool responses to project file count — is directly applicable to Lyra's `src/` agent loop.

**Key mechanisms to transfer**:
1. Tree-sitter-based extraction into SQLite+FTS5 for structural queries
2. `codegraph_explore` paradigm: one MCP tool returns verbatim source for relevant symbols, grouped by file, with adaptive sizing to project scale
3. Per-project index with auto-sync via file watcher
4. Agent-agnostic MCP server design (parallels Lyra's multi-provider architecture)
5. "Don't re-verify codegraph with grep" anti-pattern (saves tokens by trusting the index)

**Workstream route**: This maps naturally to Lyra's §4.05 Model Router (builds index for routing decisions) and especially §4.06 Tools (the MCP tool surface is the agent-facing API). The code graph itself serves the §4.02 Memory workstream (as a persistent structural memory store) and §4.16 Reliability (impact analysis tells you what tests need to pass before CI).

**Impact**: 7 (high — would eliminate the dominant source of agent tool call waste: grep/read exploration loops)
**Effort**: 5 (moderate-high — requires integrating tree-sitter WASM grammars, SQLite, MCP server, and per-project index lifecycle)
**Tier**: P1 (directly attacks the cost and latency problems identified in Lyra's baseline)
**License**: MIT
