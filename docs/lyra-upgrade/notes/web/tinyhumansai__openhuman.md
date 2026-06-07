# tinyhumansai/openhuman — Deep-Read

Repository: https://github.com/tinyhumansai/openhuman
Stars: Trending (Product Hunt Top Post, multiple weeks)
Status: Early beta, active development
License: GNU General Public License v3.0

## 1. Headline Feature & Mechanism

**Headline: Personal AI super intelligence with local-first persistent memory, auto-fetching from 118+ integrations, token compression, and multi-agent orchestration — all in a desktop app.**

OpenHuman is a Rust (core) + React/Tauri (desktop shell) monorepo that builds a persistent, context-aware AI assistant. The core insight is that most AI agents start "cold" every session; OpenHuman inverts this by continuously pulling data from the user's connected accounts (Gmail, GitHub, Slack, Notion, Linear, Calendar, Drive, etc.) on a 20-minute loop, canonicalizing it into <=3k-token Markdown chunks, scoring and ranking those chunks, and folding them into hierarchical summary trees stored in local SQLite (with an Obsidian-compatible `.md` vault on disk).

The mechanism is a layered pipeline:

1. **Auto-fetch** (memory sync pipelines at `src/openhuman/memory_sync/`): Three kinds of sync pipelines (Composio for managed connectors, workspace for local vault sync, MCP for third-party MCP servers) all implement a uniform `SyncPipeline` trait. The Composio pipeline fires every 20 minutes, pulls delta data from each connected integration, and pushes raw content into `memory_store`.

2. **Ingest pipeline** (`src/openhuman/memory/ingest_pipeline/`): Raw content gets canonicalized (normalized, deduped, compressed to <=3k-token chunks), entities are extracted (regex + optional LLM extraction), embeddings computed (OpenAI `text-embedding-3-small`, though embeddings are currently disabled for summaries), and everything lands in SQLite FTS5 tables.

3. **Memory Tree** (`src/openhuman/memory_tree/`): A generic summary-tree engine. Leaves (individual chunks) are appended to level-0 buffers. When a buffer crosses its gate (token count for L0, sibling count for higher levels), the engine cascades a seal: it calls the summarizer LLM to produce a compressed summary, writes that summary as a new node, clears the buffer, and queues the summary at the next level. The result is a multi-level summary tree (L0 leaves -> L1 summaries -> L2 summaries -> ...) stored in SQLite + `.md` files on disk. Retrieval walks this tree to find relevant context.

4. **TokenJuice** (`src/openhuman/tokenjuice/`): A Rust port of vincentkoc/tokenjuice. Before any tool output enters the LLM context window, it is run through a compaction engine with 96 vendored rules (git, npm, cargo, docker, kubectl, etc.). Rules are loaded from a three-layer overlay (builtin -> user config -> project config). Pass-through safety: outputs <512 bytes or compaction ratio >0.95 are returned verbatim. Claims "up to 80% cost and latency reduction."

5. **Multi-agent harness** (`src/openhuman/agent/harness/`): One shared tool-call loop engine (`engine::run_turn_engine`) with three entry points: `Agent::turn` (desktop/web chat), `run_tool_call_loop` (bus handler for channels/triage), `run_subagent` (spawned specialists). The harness supports a tiered spawn hierarchy (chat -> reasoning -> worker) with static loader-time tier validation and a runtime `MAX_SPAWN_DEPTH=3` fence. Sub-agents inherit parent context (KV-cache prefix, sandbox mode, interrupt fence). Archetypes include orchestrator, planner, researcher, code_executor, critic, summarizer, archivist, tool_maker, integrations_agent, trigger_triage, trigger_reactor, morning_briefing.

## 2. Architecture & Core Modules

**Language**: Rust (2021 edition) for core, TypeScript 5.8 + React 19 for frontend, Tauri v2 for desktop shell.

**Entry points**:
- `src/main.rs` — CLI binary `openhuman-core`. Initializes Sentry, loads dotenv, dispatches to `core::cli::run_from_cli_args`.
- `src/lib.rs` — Library crate `openhuman_core`. Exposes `run_core_from_args`, re-exports `DaemonConfig` and `MemoryClient`.
- `app/src/main.tsx` — React entry point. Mounts provider chain: Sentry -> Redux -> PersistGate -> BootCheckGate -> CoreStateProvider -> SocketProvider -> ChatRuntimeProvider -> HashRouter -> CommandProvider -> ServiceBlockingGate -> AppShell.
- `app/src-tauri/src/core_process.rs` — Tauri host. Spawns Rust core in-process as a tokio task (sidecar removed PR #1061). Frontend RPC via `http://127.0.0.1:<port>/rpc` with per-launch hex bearer token.

**Core modules** (`src/openhuman/`, ~65+ domains):

| Module | Lines | Role |
|--------|-------|------|
| `memory_tree/` | ~1100+ | Generic summary-tree engine: bucket-seal cascade, scoring, embedding, entity extraction, summarization |
| `memory_store/` | ~2000+ | SQLite persistence layer: FTS5, vectors, tree tables, content staging |
| `memory/` | large | Orchestration: policy, ingest pipeline, recall ranking, RPC surface |
| `memory_sync/` | large | Auto-fetch pipelines: Composio, workspace, MCP sync drivers |
| `tokenjuice/` | ~1000+ | Tool output compaction: 96 vendored rules, 3-layer overlay, pass-through safety |
| `agent/` | very large | Agent harness: tool-call loop, sub-agent dispatch, triage, hooks, cost accounting |
| `security/` | ~1500+ | Security policy: sandbox backends, prompt injection guard, access tiers |
| `config/` | large | TOML config schema with env overrides, autonomy settings |
| `providers/` | large | Integration proxy layer for Gmail, GitHub, Slack, etc. via Composio |
| `routing/` | moderate | Model routing: quality detection, refusal/empty-noise filtering |
| `inference/` | large | Provider HTTP transport, cost tracking, usage reporting |

**Data flow** (end-to-end turn):

```
User message -> React UI -> Redux dispatch -> coreRpcClient -> Tauri IPC (core_rpc_relay)
  -> HTTP JSON-RPC to core process
    -> Agent::turn() 
      -> memory_loader injects relevant Memory Tree chunks
      -> tool-call loop (up to 10 iterations default, 50 for specialists)
        -> Provider call (model resolved by model router)
        -> Parse response (Native/XML/P-Format dialects)
        -> Execute tools (gated by SecurityPolicy + sandbox)
        -> TokenJuice compacts tool output
        -> Context guard (microcompact/autocompact if near window limit)
        -> Stop hook check (budget caps, max iterations)
      -> Post-turn hooks (archivist, learning, cost log, episodic memory)
    -> Response flows back through same path to UI
```

**Pattern**: Clean domain-driven monorepo. Transport lives in `src/core/` (no business logic). Business logic lives in `src/openhuman/<domain>/`. Each domain follows a canonical module shape: `mod.rs` (re-exports only), `types.rs`, `store.rs`, `ops.rs`, `schemas.rs`, `tools.rs`, `bus.rs`. Frontend communicates via JSON-RPC over Tauri IPC relay.

**Persistence strategy**:
- SQLite via rusqlite (bundled, no system dep) for: memory chunks, FTS5 full-text index, tree metadata, session transcripts, config
- OS keychain for credentials (keyring crate)
- Obsidian-compatible `.md` files on disk for human-browsable memory
- Node.js managed runtime for tool helpers (installs `v22.11.0` default)
- Redis/Postgres mentioned in deps but appear to be for optional backend features

**Testing**: Vitest (frontend), Cargo tests with `#[cfg(test)]` modules (unit) + `tests/` (integration). WDIO + Appium for E2E. Coverage gate: >=80% on changed lines via diff-cover.

## 3. Performance/Benchmarks

The repo does not publish formal benchmarks in CI or docs. The following claims come from the README and architecture docs:

- **Cold startup**: "Sub-500ms" (Tauri + Rust vs Electron's 2-5 seconds)
- **Memory per tool execution**: "Native Rust (no per-tool VM); shared managed Node runtime for helper calls" vs "~150 MB+ (Chromium renderer per process)" for Electron
- **TokenJuice**: "Reducing cost & latency by up to 80%" (from README)
- **Tool-call loop**: Default 10 max iterations, 50 for multi-step specialists
- **SQLite**: Embedded, zero-config, per-skill isolation
- **Auto-fetch cadence**: Every 20 minutes per active connection
- **Memory chunk size**: <=3k tokens per chunk
- **Binary size**: "Feature-dependent (CEF runtime dominates)" — no specific number
- **Embedding batch**: 70% vector similarity + 30% FTS5 hybrid search
- **No GC pauses**: Rust ownership model eliminates garbage collection pauses that affect Electron/Node apps

A detailed performance note in `Cargo.toml` documents a real-world issue: the removed `html2md` dependency allocated ~894 MB peak heap on a 10 KB HTML input (deeply-nested table-as-layout HTML from Otter.ai emails). Replaced with a linear-time tag-and-entity stripper. This demonstrates performance-conscious engineering.

## 4. Trade-offs

**Wins**:
- **Local-first memory is genuinely novel**. The Memory Tree + Obsidian vault pattern means the agent accumulates persistent context across sessions without fine-tuning or vector DB sprawl. Auto-fetch on 20-min cadence gives "tomorrow's context this morning."
- **TokenJuice is elegant**. Compacting tool output before it hits the LLM context window is a practical optimization. The 3-layer rule overlay (builtin, user, project) lets users customize without forking. Pass-through safety (skip if >0.95 ratio or <512 bytes) prevents data loss.
- **Security is thorough**. Multi-layer: OS keychain, Argon2id + AES-256-GCM, sandbox backends (Docker, landlock, AppContainer, bubblewrap, firejail), command classification (Read/Write/Network/Install/Destructive), tiered autonomy (readonly/supervised/full), prompt injection guard with pattern + heuristic classifier, 10-min approval TTL. Hard to find another open-source agent harness with this depth.
- **Multi-agent harness is well-designed**. One shared tool-call loop, three entry points, tiered spawn hierarchy with static + dynamic depth enforcement, KV-cache prefix sharing, repeated-failure circuit breaker, self-healing for missing commands.
- **Integration surface is massive**. 118+ integrations via Composio OAuth, all exposed as typed tools to the agent, auto-fetched every 20 minutes.
- **i18n**: 6 language READMEs, 14+ locale files for UI text, CI-enforced translation parity.
- **Code quality is high**. Comprehensive `CLAUDE.md`/`AGENTS.md`, well-documented code, canonical module shapes, inline `// SAFETY:` comments, detailed dep comments in Cargo.toml explaining why each dependency exists. 1 commit in history (recent large squash) suggests curated history.

**Losses**:
- **GPLv3 license** is a hard copyleft barrier. Any project that distributes a derivative work (including Lyra, if it ships as a product) must open-source under GPLv3. This is not compatible with MIT/Apache-2 projects. The README's comparison table disingenuously lists OpenHuman as "GNU" while competitors are "MIT" — buyers should be aware.
- **Managed backend dependency**. "The default managed experience still uses OpenHuman-hosted services for account sign-in, model routing, web search proxying, and managed integration/OAuth flows." The "choose custom/local settings" escape hatch exists but is clearly second-class. Self-hosting requires your own Composio API key, model endpoints, web search proxy, and webhook hosting. The README is transparent about this but it means the open-source claim is partially aspirational.
- **Beta quality**. "Early Beta: Under active development. Expect rough edges." Known issues: AppImage crashes under Wayland, `sharun: Interpreter not found!` on Arch, deep links require built `.app` bundle on macOS.
- **Massive dependency surface**. Cargo.toml lists ~100+ direct dependencies including niche crates (whatsapp-rust, matrix-sdk, bitcoin, ethers, Solana, Tron). Each is optional but the surface area is enormous. The Node.js managed runtime adds another V8 dependency. The CEF vendored CLI adds ~500MB+ to the toolchain.
- **Single-process SQLite concurrency**. The bucket_seal code comments that Phase 3a assumes single-process SQLite and blocks on DB calls inside async functions — "acceptable for Phase 3a because the Inert summariser does no real I/O." A networked summariser would require `spawn_blocking` wrapping. This is acknowledged but not yet fixed.
- **iOS client is experimental**. The iOS Tauri app shares the React UI but ships no core binary — it's a thin transport client to the desktop core. Requires E2E encryption tunnel (X25519 + XChaCha20-Poly1305). Pairing flow depends on an unmerged backend PR.
- **Model routing depends on managed backend**. The `model: "hint:reasoning"` resolution goes through the OpenHuman backend. Local AI via Ollama is listed as "[optional] for supported on-device workloads" — unclear which workloads qualify.

## 5. Design Rationale

The architecture reveals several deliberate design decisions:

1. **Async Rust + Tauri over Electron**: "Traders and analysts run OpenHuman alongside resource-intensive tools, charting software, multiple browser tabs, trading terminals. A native binary with sub-500ms startup means the app feels native and stays out of the way." The crypto community focus (wallets, exchanges, trading terminals) explains the crypto-related dependencies (bitcoin, ethers, Solana, Tron).

2. **Memory-first agent design**: Inspired by Karpathy's Obsidian wiki workflow and the observation that "most agents start cold." The bet is that persistent, auto-updating memory is the key differentiator over chat-scoped agents. The Memory Tree's bucket-seal cascade (append -> token/sibling threshold -> summarize -> cascade) is a pragmatic, incremental compaction strategy that doesn't require a vector DB for basic function.

3. **Multi-agent over monolithic prompts**: "A single agent that knows everything also has a system prompt the size of a small book." Splitting work across specialists with narrow prompts, filtered tool registries, and separate model tiers (cheap workers, expensive orchestrators) is the scalability strategy. The tiered spawn hierarchy prevents runaway recursive delegation.

4. **Token compression as first-class concern**: TokenJuice at every tool output boundary, context guard mid-loop, microcompact/autocompact for window management, payload summarizer detour for oversized results — the system treats token budget as a hard constraint and designs for it from the start, not as an afterthought.

5. **Managed services with local escape hatch**: The dual-mode architecture (managed backend by default, self-host option) is a pragmatic compromise between "fully open source" and "actually works out of the box." The managed backend handles the hard parts (model routing billing, OAuth proxy, web search) that are genuinely difficult to self-host.

6. **Unix-style modules in Rust**: The 65+ domain directories under `src/openhuman/`, each with the canonical `mod.rs`/`types.rs`/`store.rs`/`ops.rs`/`schemas.rs`/`tools.rs`/`bus.rs` shape, enforce separation of concerns at the module level. The explicit rule "No business logic in `src/core/`" keeps transport concerns separate.

7. **Prompt injection as security layer**: The dedicated `prompt_injection/` domain with normalization -> pattern rules -> optional classifier -> verdict contract (allow/block/review) -> enforcement flow, plus advisory frontend UX, shows injection attacks were treated as a primary threat model from day one.

## 6. Transfer to Lyra

**Most transferable idea: TokenJuice — pre-compaction of tool output before it enters the LLM context window.**

Lyra's research workflow generates enormous tool outputs: web fetch results, PDF extracts, code analysis dumps, search result pages. Implementing a TokenJuice-style compaction layer at the tool-output boundary would directly reduce token costs and latency for every research turn. The 3-layer rule overlay (builtin + user + project) maps naturally to Lyra's plugin/skill architecture — research domains could ship compaction rules alongside their tool definitions.

**Second transferable idea: Memory Tree bucket-seal cascade** — incremental summary tree with token/sibling-count sealing gates. Lyra's long-term context management (keeping research findings across sessions) could use a similar approach: append findings chunks, auto-summarize when thresholds are crossed, walk the tree for retrieval.

**Third transferable idea: Multi-agent harness with tiered spawn hierarchy** — chat orchestrator spawns reasoning specialists, which spawn worker agents. Lyra's research pipeline (planner -> researcher -> coder -> critic) maps directly to this pattern.

**Workstream route**: §4.x (Token Management / Budget)

**Estimated effort**: Medium (3-6 weeks for a TokenJuice port + integration). The Rust core is portable; the tokenjuice module is fully self-contained (no other `openhuman` imports, only serde/regex/once_cell/unicode-segmentation deps).

**Impact**: High. Token compaction at the tool boundary is a multiplicative win — every research turn benefits, every agent call benefits, every tool output is smaller.

**Tier**: P1 (quick win, high impact, relatively isolated)

**License caveat**: GPLv3. If Lyra is MIT/Apache-2, direct port of TokenJuice source would require license compatibility analysis. The concept (rule-based tool output compaction) is not patentable and can be independently implemented. The rule files (96 vendored JSON rule sets) are MIT-licensed per the vendor README.
