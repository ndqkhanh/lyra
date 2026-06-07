# yvgude/lean-ctx — Deep-Read

## 1. Headline Feature & Mechanism

**LeanCTX is a Cognitive Context Layer for AI coding agents — a single Rust binary that compresses, caches, remembers, routes, and governs every token flowing between code and the model.**

The central mechanism is a **dual-surface architecture**:
- **MCP server** (69 `ctx_*` tools): Intercepts reads (`ctx_read` with 10 compression modes: `full`, `map`, `signatures`, `diff`, `lines:N-M`, `aggressive`, `entropy`, `task`, `reference`, `auto`), searches (`ctx_search`, `ctx_semantic_search`), shell commands (`ctx_shell`, `ctx_execute`), knowledge recall (`ctx_knowledge`), session handoff (`ctx_handoff`), and context composting (`ctx_compile`). Re-reads of cached files cost ~13 tokens regardless of original size.
- **Shell hook** (CLI `lean-ctx -c`): Transparently intercepts shell commands via `~/.zshenv` / `~/.bashrc` hooks and compresses output through 56 pattern modules (git, cargo, npm, docker, kubectl, terraform, gh, glab, ninja, etc.) with 270+ passthrough rules.

The compression engine uses **tree-sitter AST parsing** (18 languages) for structural understanding — not just text-level compression. `map` mode extracts dependencies + API signatures; `signatures` mode surfaces only the API surface with line ranges; `aggressive` mode strips comments, blank lines, and normalizes indentation.

Cross-session memory is implemented as **CCP (Cognitive Context Persistence)**: a SQLite-backed session store with structured recovery queries that survive compaction. Facts in the knowledge store carry confidence scores, temporal validity windows, and Ed25519-signed audit trails.

## 2. Architecture & Core Modules

**Language**: Rust (primary binary). Supporting packages in TypeScript (npm), Python, Neovim Lua, JetBrains, VS Code, Sublime Text, Emacs.

**Entry points**:
- `rust/src/main.rs` — sets panic hook, wraps `lean_ctx::cli::dispatch::run()` in `catch_unwind`
- `rust/src/lib.rs` — re-exports all modules (cli, core, engine, server, tools, shell, hooks, etc.)
- `rust/src/cli/dispatch/` — dispatches to 75+ subcommands
- `rust/src/engine/mod.rs` — `ContextEngine` struct wrapping `LeanCtxServer`, provides `call_tool_value/result` bridge for programmatic use
- `rust/src/server/` — MCP server with dispatch pipeline, role guard, context gate, post-processing, tool registry

**Core source modules** (in `rust/src/core/`):
- **Compression domain** (25 modules): `compressor.rs`, `entropy.rs`, `information_bottleneck.rs`, `predictive_coding.rs`, `progressive_compression.rs`, `structural_tokenizer.rs`, `structured_read.rs`, `compression_safety.rs`, `preservation.rs`, `codebook.rs`
- **Memory domain** (8 modules): `episodic_memory.rs`, `memory_consolidation.rs`, `memory_lifecycle.rs`, `memory_policy.rs`, `procedural_memory.rs`, `prospective_memory.rs`, `multiscale_index.rs`
- **Graph domain** (11 modules): `property_graph/`, `call_graph.rs`, `graph_context.rs`, `graph_index.rs`, `graph_enricher.rs`, `pagerank.rs`, `repomap.rs`
- **Context domain** (13 modules): `context_compiler.rs`, `context_ir.rs`, `context_ledger.rs`, `context_os.rs`, `context_package/`, `context_proof.rs`, `context_proof_v2.rs`
- **Knowledge domain** (7 modules): `knowledge/`, `cognition_loop.rs`, `cognition_scheduler.rs`, `knowledge_relations.rs`, `knowledge_embedding.rs`
- **Search & Retrieval** (15 modules): `bm25_index/`, `bm25_cache.rs`, `embeddings/`, `hybrid_search.rs`, `hnsw.rs`, `semantic_cache.rs`, `splade_retrieval.rs`, `dense_backend.rs`
- **Shell patterns** (56 modules): `git/`, `cargo.rs`, `npm.rs`, `docker.rs`, `kubectl.rs`, `terraform.rs`, `gh.rs`, `glab.rs`, `ninja.rs`, `clang.rs`, `typescript.rs`, etc.
- **Agent & Multi-Agent** (6 modules): `agents.rs`, `a2a.rs`, `a2a_transport.rs`, `agent_identity.rs`, `handoff_ledger.rs`, `handoff_transfer_bundle.rs`
- **Adaptive systems** (7 modules): `adaptive.rs`, `bandit.rs`, `mode_predictor.rs`, `model_registry.rs`, `intent_engine.rs`, `intent_router.rs`, `task_relevance.rs`
- **Policy engine** (7+ modules): `profiles.rs` (1376 lines), `budgets.rs`, `roles.rs`, `slo.rs`, `memory_policy.rs`, `tool_profiles.rs`, `autonomy_drivers.rs`
- **Config** (6 modules): `config/mod.rs` (1188 lines), `config/setter.rs`, `config/sections.rs`
- **Infrastructure** (50+ modules): `cache.rs`, `tokens.rs`, `hasher.rs`, `pathutil.rs`, `sandbox.rs`, `audit_trail.rs`, `secret_detection.rs`, `smells.rs`, etc.

**Tools directory** (`rust/src/tools/`): 69 MCP tool implementations including `ctx_read/`, `ctx_knowledge/`, `ctx_shell.rs`, `ctx_search.rs`, `ctx_edit.rs`, `ctx_gain.rs`, `ctx_handoff.rs`, `ctx_agent.rs`, `ctx_overview.rs`, `ctx_compile.rs`, `ctx_preload.rs`, `ctx_proof.rs`, `ctx_url_read.rs`, `ctx_refactor.rs`, `ctx_impact.rs`, `ctx_callgraph.rs`, `ctx_tree.rs`, `ctx_delta.rs`, etc.

**Architecture pattern**: **Modular monolith / layered pipeline**. The `LeanCtxServer` struct (in `server/`) owns a dispatch pipeline: Pre-Pipeline (meta-resolve, role guard, workflow gate, loop detection, budget gate, degradation eval, context gate) -> HybridDispatch -> ToolRegistry (69 trait-based `McpTool`s) -> Post-Pipeline (Context IR, tokens, archive, density, translation, verify, enrich, evidence, sandbox routing). Config is field-wise mergable TOML with profile inheritance. No microservices — one binary does everything.

**Data flow**:
1. Agent calls `ctx_read("src/main.rs", "map")` via MCP
2. Server pre-pipeline: role check -> budget check -> loop detection -> context gate
3. Dispatch to `ctx_read` handler -> checks cache (hash + mtime) -> if cached, returns ~13-token result; if miss, reads file, runs tree-sitter AST for `map` mode, caches zstd-compressed content, returns for Agent
4. Post-pipeline: record in context IR, update savings ledger, archive large output, update heatmap, fire bus events
5. Session state persists across chats via SQLite-backed CCP

## 3. Performance/Benchmarks

From `BENCHMARKS.md` (measured on lean-ctx repo, 50 files, 457.6K total raw tokens):

| Mode | Compression | Latency | Quality |
|------|------------:|--------:|--------:|
| full (cached re-read) | inherits prior compression | ~13 tokens | 100% |
| map | 97.7% (8.9K) | 15.1ms | 83% |
| signatures | 97.0% (11.8K) | 4.6ms | 92% |
| aggressive | 3.9% (438K) | 238μs | 100% |
| entropy | 0.4% (455.8K) | 32.3ms | 100% |

Search latency: avg 479μs (BM25, range 85μs-874μs)

Cold start: 2.69s (file scan 655μs + BM25 index build 2.69s + first read 96μs)

Disk footprint: BM25 index 2.7 MB, total `.lean-ctx/` 256 KB

**Competitor comparison**:
- Raw: 0% compression
- Repomix: 70% (137.3K)
- aider `/map`: 85% (68.6K)
- lean-ctx `map`: 97.7% (8.9K)
- codebase-memory-mcp: 99.2% (3.7K)

**30-min coding session simulation**:
- Raw: 686.1K tokens, $1.715
- lean-ctx (no CCP): 99.5K, $0.249 (85.5% savings)
- lean-ctx + CCP: 93.6K, $0.234 (86.4% savings)

## 4. Trade-offs

**Wins**:
- Dramatic token savings (60-99% on shell output, 97% on code maps)
- Cross-session memory persistence eliminates "cold start" in every new chat
- Works with 30+ AI coding agents (Cursor, Claude Code, Copilot, Windsurf, Codex, Gemini, etc.)
- Single binary install — zero external dependencies, no runtime
- Local-first, no telemetry by default, opt-in cloud sync
- Self-healing diagnostics (`lean-ctx doctor --fix`)
- Verified, auditable savings ledger with SHA-256 chain and Ed25519 signatures
- Supports multi-agent handoff with context transfer bundles
- Ed25519-signed audit trail, prompt-injection detection, SSRF-guarded web fetches

**Losses**:
- **Complexity**: 400+ source modules, 160K-line `Cargo.lock`, 3.7.x release cycle with 180+ releases in 4 months. The surface area (69 MCP tools, 75+ CLI commands, 56 patterns) is enormous for a single binary.
- **Compression-quality tradeoff**: `map` mode achieves 97.7% compression but at 83% quality preservation. The aggressive mode barely compresses (3.9%) because it only strips comments/whitespace on already-compact code. Entropy mode filters by Shannon self-information and can drop task-critical lines if they are common (mitigated by task-conditioned IB filtering added in v3.7.4).
- **Cold start cost**: The first BM25 index build takes 2.69s even on a modest repo — lazy loading (added in v3.7.4) defers this until first search.
- **Shell interference**: The shell hook must carefully avoid corrupting file reads — v3.7.1 had a bug where the proxy treated every tool result as shell output, gutting large source files. Identifier alpha-substitution (`§MAP`) was made opt-in because it confused developers during active editing.
- **Proxy latency**: The compressing proxy adds overhead — large body ceiling was initially 10 MiB (raised to 64 MiB in v3.7.3), and streaming timeouts were too aggressive (fixed by separating connect/read timeouts).
- **Learning curve**: The 10 read modes, 4 compression levels, profiles, rules injection modes (shared vs dedicated), and pluggable providers create a steep configuration surface for new users.
- **Platform quirks**: Windows path normalization (`\\?\` prefixes, backslash corruption), WSL cache misses (DrvFS mtime=None), macOS Documents directory (v3.7.3 had to stop writing to `~/Documents`), and per-platform package distribution.

**Known limitations from CHANGELOG/issues**:
- Cloud placeholders (OneDrive/iCloud) triggered full file downloads on background scans (v3.7.5)
- OpenCode OpenAI-compatible provider keys rejected by proxy auth gate (v3.7.5)
- MCP stdio transport must never interleave log lines with JSON-RPC (regression-guarded)
- `ctx_search` and background index could hang on FIFOs/sockets (v3.7.3)
- Parallel `remember` calls clobbered each other (v3.7.0)
- Test-runner output could be truncated losing pass/fail summaries (v3.7.0)
- Config.toml overwritten on update (v3.7.0, fixed with format-preserving TOML merge)

## 5. Design Rationale

The README states the core philosophy: **"Your AI coding agent wastes thousands of tokens rereading files, parsing noisy shell output, and losing context between sessions — and you have no control over any of it. LeanCTX is the operating system for that context."**

Key design decisions surfaced by the code:
1. **Single Rust binary** over microservices: Simpler deployment, no runtime dependencies, atomic updates, and a single surface to harden. The `--help` page alone is massive, but the user never sees it — tools and commands are discovered through MCP `tools/list` and `lean-ctx` subcommand completion.
2. **Pattern-based shell compression** (not regex): Each shell pattern is a standalone CompiledPattern module with deterministic, versioned output (`PATTERN_ENGINE_VERSION = 1`). This enables formal verification (the `LeanCtxProofs/` subproject in the Lean theorem prover actually proves pattern correctness).
3. **MCP over custom protocol**: The Model Context Protocol provides tool discovery, call/result framing, and dynamic tool surfaces out of the box. LeanCTX extends it with HTTP streaming, SSE, and team-server multi-workspace capabilities.
4. **ZSTD over gzip** for content compression in cache: Better compression ratios at acceptable speed for the hot read path.
5. **Thompson Sampling bandits** for adaptive mode prediction: The `ModePredictor` and `ProviderBandit` use Beta-Bernoulli Thompson Sampling (not epsilon-greedy) because it explores near-optimal arms probabilistically without an exploration phase parameter.
6. **SQLite WAL** for context OS bus: The shared session store uses SQLite WAL mode for concurrent read/write with split read/write paths, bounded WAL, and dead-owner lock reclamation.
7. **Profiles with field-wise merge**: Profiles (`coder`, `reviewer`, `explorer`, `ops`) use `Option<T>` inheritance — each field is either set (override) or None (inherit from base) — avoiding the classic diamond problem in layered configs.
8. **Information Bottleneck in entropy mode**: The entropy-based read compression now conditionally rescues low-entropy lines that mention task keywords, implementing a variational information bottleneck principle — keeping what is either surprising OR task-relevant.
9. **Ed25519 signatures on audit trail**: Cryptographic proof of provenance (which installation produced which record) without a central CA — the local identity key is installation-specific and the chain is append-only.
10. **Format-aware passthrough for TOON**: The compression engine detects Token-Oriented Object Notation output and skips recompression, preserving exact line/field shapes that agents use for CLI-output contract validation.

## 6. Transfer to Lyra

**One transferable idea**: **Structured context compression with mode-selectable fidelity** — specifically the approach of encoding file content into multiple "read modes" (map/signatures/full/entropy/task) that are cached with zstd compression and delivered at ~13 tokens on re-read. Lyra's context management currently lacks any mechanism to distinguish between "I need to understand the API surface" vs "I need to edit this function" — every read pays the full token cost regardless of fidelity required.

**Workstream route**: **Section 4.x (Reliability / Memory / Context)** — this maps most directly to:
- `§4.1 Reliability`: Cached reads with mtime validation prevent re-reading unchanged files, reducing context waste and API costs during long sessions.
- `§4.2 Memory (Cross-session)`: The CCP (Cognitive Context Persistence) model — session state with structured recovery queries, knowledge facts with confidence and temporal windows, Ed25519-signed audit trails — provides a concrete implementation pattern for Lyra's cross-session memory that goes beyond simple file-based persistence.
- `§4.3 Context / Shell`: The 56-pattern shell compression module (esp. git, cargo, npm, docker patterns) directly addresses the "noisy shell output" problem in Lyra's agent harness.

**Impact: 8/10** — Token savings of 60-97% on routine operations would dramatically extend Lyra's useful session length and reduce API costs. The cross-session memory stops the "I already showed you this file" problem that wastes ~30% of context in multi-chat workflows.

**Effort: 7/10** — Implementing the full 10-mode read pipeline with tree-sitter AST extraction is significant (the lean-ctx team has 400+ source modules). However, a minimal version with 3-4 modes (full/map/signatures) plus zstd caching could be built in 2-3 weeks. The shell compression patterns could be ported selectively (start with git + cargo patterns, ~5 patterns) and grown organically.

**Tier: T1 — Directly adoptable** — The Rust binary is Apache 2.0 licensed. Lyra can fork or embed the compression core (excluding the MCP server, team server, and cloud features) as a library dependency. The shell pattern modules are independent of the MCP infrastructure and can be used standalone. Alternatively, lean-ctx can be installed as a sidecar and Lyra's agents configured to use `lean-ctx -c` and `ctx_read` via MCP — zero code change, immediate benefit.

**License**: Apache 2.0 — permissive, allows embedding, modification, and commercial use. No copyleft obligations. Copyright Yves Gugger, 2026.
