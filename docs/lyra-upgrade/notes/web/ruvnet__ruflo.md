# ruflo (ruvnet/ruflo) -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** Multi-agent AI orchestration harness for Claude Code and Codex that turns a single-context coding assistant into a coordinated swarm of 100+ specialized agents with self-learning memory, federated cross-machine communication, and plugin-based extensibility.

**How it works:** The system runs as an npm package (`ruflo`) that, after a one-line `npx ruflo init`, registers an MCP (Model Context Protocol) server with Claude Code. This server exposes 323 tools spanning agent lifecycle, vector memory, swarm coordination, hooks, GitHub integration, browser automation, and security scanning. The CLI provides 45 top-level commands (`ruflo agent`, `ruflo swarm`, `ruflo memory`, `ruflo hooks`, `ruflo verify`, etc.) for terminal/script use. A hook system (17 hooks + 12 background workers) sits between the user and Claude Code to auto-route tasks, retrieve learned patterns, dispatch background analysis, and coordinate agents.

The actual execution is split: MCP tools handle *coordination* (swarm init, memory store, neural training); Claude Code's native Task tool handles *execution* (code generation, file operations). The intelligence pipeline follows a 4-step loop: RETRIEVE (HNSW vector search) -> JUDGE (verdict evaluation) -> DISTILL (LoRA extraction) -> CONSOLIDATE (EWC++ anti-forgetting).

**Key architectural layers (README + source):**

```
User --> Claude Code / CLI
          |
          v
    Orchestration Layer       (MCP Server, Router, 27 Hooks)
          |
          v
    Swarm Coordination        (Queen, Topology, Consensus)
          |
          v
    100+ Specialized Agents   (coder, tester, reviewer, architect, security...)
          |
          v
    Memory & Learning         (AgentDB, HNSW, SONA, ReasoningBank)
          |
          v
    LLM Providers             (Claude, GPT, Gemini, Cohere, Ollama)
```

## 2. Architecture & Core Modules

**Entry points:**
- `bin/cli.js` -- Umbrella CLI entry. Proxies to `v3/@claude-flow/cli/bin/cli.js`. Auto-detects MCP stdio mode when stdin is piped (for `claude mcp add ruflo`), else runs normal CLI mode.
- `v3/@claude-flow/cli/bin/cli.js` -- Actual CLI bin. Imports `dist/src/index.js` for normal CLI or inlines a full MCP stdio server when in pipe mode. Console-filter patches installed before ANY heavy import to suppress agentdb cosmetic noise and redirect embedder progress to stderr (fixes #2253 MCP stdio corruption).
- `v3/@claude-flow/cli/src/index.ts` -- `CLI` class with `run()`, `showHelp()`, lazy command loading, config loading from `@claude-flow/shared`.

**Core modules (in `v3/@claude-flow/cli/src/`):**
- **commands/** (38 files) -- `agent.ts`, `swarm.ts`, `memory.ts`, `hooks.ts`, `hive-mind.ts`, `benchmark.ts`, `gaia-bench.ts`, `security.ts`, `neural.ts`, `plugins.ts`, `federation` commands, etc. Each exports a `Command` struct with name, description, options, subcommands, and action.
- **mcp-server.ts** -- Full MCP server manager: stdio, HTTP, WebSocket transports. JSON-RPC 2.0 protocol. Handles `initialize`, `tools/list`, `tools/call`, `notifications/initialized`, `ping` methods. Auto-initializes memory DB on startup. 10MB buffer cap against DoS. Console hijack to redirect debug output to stderr away from JSON-RPC stdout.
- **mcp-client.ts** -- Tool registry: `listMCPTools()`, `callMCPTool()`, `hasTool()`. Exports all tool definitions.
- **mcp-tools/** (30 files) -- Individual tool registries: `memory-tools.ts`, `agent-tools.ts`, `swarm-tools.ts`, `neural-tools.ts`, `security-tools.ts`, `github-tools.ts`, `browser-tools.ts`, `hooks-tools.ts`, etc.
- **memory/memory-initializer.ts** (3031 lines) -- The largest single file. SQLite via sql.js (WASM), HNSW via `@ruvector/core`, Int8 quantization, RaBitQ index, cosine similarity, flash-attention-style batch ops, legacy migration, ONNX model loading (tries `@huggingface/transformers` -> `@xenova/transformers` -> agentic-flow -> ruvector -> mock fallback).
- **memory/intelligence.ts** -- SONA optimizer (0.0043ms/adapt), MoE gate, ReasoningBank, trajectory learning, EWC++ consolidation.
- **memory/sona-optimizer.ts** -- Self-Optimizing Neural Architecture for adaptive routing.
- **memory/ewc-consolidation.ts** -- Elastic Weight Consolidation to prevent catastrophic forgetting.
- **memory/memory-bridge.ts** -- AgentDB v3 bridge for ADR-053 ControllerRegistry (ReasoningBank, SkillLibrary, ExplainableRecall, etc.).
- **commands/index.ts** -- Registers all commands: core (init, agent, swarm, memory, mcp, task, session, config, status, start, workflow, hooks, hive-mind) and advanced (daemon, neural, security, performance, providers, plugins, deployment, embeddings, claims, migrate, process, doctor, completions).

**Plugin system:**
- 33 plugins in `plugins/` (ruflo-core, ruflo-swarm, ruflo-federation, ruflo-rag-memory, etc.)
- IPFS/Pinata registry for decentralized immutable distribution
- Claude Code's `/plugin marketplace add ruvnet/ruflo` for lite install

**Package structure:**
- `ruflo` (npm alias, ~250KB) -> depends on `@claude-flow/cli` (monorepo in `v3/@claude-flow/cli/`)
- 19 sub-packages in `v3/@claude-flow/`: cli, shared, memory, hooks, security, neural, guidance, swarm, plugins, codex, etc.
- `v3/@claude-flow/guidance` -- Governance control plane (WASM policy kernel, ContinueGate, capability algebra)
- `v3/@claude-flow/memory` -- AgentDB integration, HNSW, embeddings
- `v3/@claude-flow/codex` -- Dual-mode Claude + Codex collaboration

**Patterns:**
- Command pattern (each command is a `Command` interface with name, description, options, action)
- MCP JSON-RPC protocol for tool exposure
- Singleton managers (MCPServerManager, serverManager)
- Lazy loading for heavy modules (agentic-flow, ruvector ONNX, transformers)
- Bridge pattern for AgentDB v3 backward compatibility
- Schema-as-code (MEMORY_SCHEMA_V3 is a string constant defining all SQLite tables)

## 3. Performance / Benchmarks

**BEIR Retrieval (measured, from docs/benchmarks/BEIR-MATRIX.md):**
- 4-dataset mean nDCG@10: 0.421 (rank 3/11 on 4-dataset leaderboard), using BGE-base-en-v1.5 (110M params)
  - NFCorpus: 0.358 (2/11), SciFact: 0.683 (3/11), ArguAna: 0.432 (5/11), SciDocs: 0.211 (2/11)
  - Beats BM25 (+0.024), GTR-XL (1.2B params), Contriever, TAS-B, ColBERT, DocT5query, SBERT
  - Loses to SPLADE++ (-0.012) and BGE-large (-0.070)
  - **Honest negative findings**: ArguAna cross-encoder rerank actively hurts (-0.149); RRF degraded when BM25 was weak; BGE-large NFCorpus showed no lift over BGE-base (0.350 vs 0.352, below published 0.380)
  - Bootstrap CI significance testing (10k resamples, seed=42) per ADR-086

**Intelligence benchmarks (measured, from CLAUDE.md + audit):**
- HNSW search vs brute force: ~1.9x faster at N=20k, ~3.2x-4.7x at N=5k (recall@10 ~0.99)
- Int8 quantization: 3.84x compression, reconstruction cosine similarity 0.99999
- RaBitQ quantization: 32x compression, 0.60ms/query (14,760-vector index)
- SONA adaptation: 0.0043ms/adapt (target <0.05ms -- met)
- MoE gate convergence: confidence 0.13 -> 0.88, Q 0 -> 99.8 after rewards
- Flash Attention: 2.49x-7.47x claimed but **unverified -- no benchmark exists**

**SOTA comparison vs LangGraph / AutoGen / CrewAI (from README):**
- ruflo wins cold start, single turn, RSS by 1.3x-1953x on darwin-arm64 + linux-x64 (v3.8.0)

**GAIA benchmarks (from v3/@claude-flow/cli/src/benchmarks/):**
- Multi-track GAIA evaluation: voting (Track A), planning interval (Track B), critic (Track D), decomposition (Track E), hardness-routing (Track Q)
- Integration with CI via `gaia-benchmark.yml` workflow

**Memory benchmarks target (from benchmark.ts):** Embedding generation <5ms, batch cosine <5ms, flash attention search <2ms, memory store <10ms, HNSW search <10ms

**Test baseline (from STATUS.md):** 1999/1999 vitest passing (0 failures, 46 intentionally skipped) for `@claude-flow/cli`; 366/366 for `@claude-flow/plugin-agent-federation`

## 4. Trade-offs

**Wins:**
- **Scope of ambition**: No other open-source project ships 323 MCP tools, 45 CLI commands, 33 plugins, 12 background workers, and self-learning memory in a single package aimed at Claude Code. This is a *platform*, not a tool.
- **Federation as first-class**: Zero-trust cross-machine agent collaboration with PII stripping, behavioral trust scoring, mTLS+ed25519, and compliance audit trails. This is far beyond what LangGraph/AutoGen/CrewAI offer for multi-instance coordination.
- **Honest metrics culture**: The BEIR-MATRIX explicitly calls out statistical insignificance (n.s. at p<0.05), counter-findings (ArguAna CE rerank hurts), and benchmark limitations (2-dataset not BEIR-average). The `CLAUDE.md` marks "Flash Attention" as **unverified** -- rare transparency.
- **Plugin marketplace on IPFS**: Decentralized immutable distribution via Pinata means plugin discovery does not depend on a single npm registry.
- **Auto-learning feedback loop**: The 4-step pipeline (RETRIEVE -> JUDGE -> DISTILL -> CONSOLIDATE) is a real closed loop, not just a diagram. SONA, MoE, and EWC++ are all implemented with measured convergence targets.

**Loses:**
- **Monolithic codebase**: 5,500+ commits, 4446+ source files, a single 3031-line file (`memory-initializer.ts`). The CLAUDE.md instructs "files under 500 lines" but this file alone is 6x that. Cognitive load for contributors is high.
- **Complex dependency chain**: 19 sub-packages in the monorepo, 5+ optional embedding backends with graceful degradation chains, proxy npm packages (`claude-flow` and `ruflo` both wrap `@claude-flow/cli`). The 3-package publish ritual (all three packages + 3 dist-tags each = 9 tag updates per release) is fragile.
- **Overclaim vs measured reality**: README banners cite "150x-12,500x faster" for HNSW but the internal full-context audit explicitly says "150x-12,500x NOT reproduced -- was brute-force fallback." Benchmark targets (Embedding <5ms, Flash Attention 2.49x-7.47x) have targets but no published benchmark dashboards.
- **Dual-mode (Claude + Codex) integration**: Heavily documented but depends on `@claude-flow/codex` which is optional and may not be shipped/working at the claimed level.
- **Plugin count discrepancy**: README says "33 plugins" but some project files reference different counts. The ecosystem is in active development.
- **Windows compatibility**: README has a detailed Windows note. Many MCP-tool paths were fixed for cross-platform, but WASM kernel and native bindings (sharp/libvips for darwin-arm64) remain friction points.

## 5. Design Rationale

The architecture is driven by a clear design philosophy: **user experience is Claude Code, not yet another agent UI**. Ruflo does not ask users to learn a new chat interface or agent dashboard -- it hooks into the existing Claude Code workflow via MCP and auto-routing hooks. The rationale:

1. **MCP over custom protocol**: Model Context Protocol is an emerging standard for LLM-tool interaction. By exposing everything as MCP tools, ruflo is immediately accessible to any MCP-compatible client (Claude Desktop, Claude Code, third-party MCP hosts).

2. **CLI for orchestration, Task tool for execution**: This split recognizes that Claude Code is better at writing code (Task tool agents) than at coordination orchestration. MCP/swarm tools handle the coordination strategy; Task tool spawns the actual agents that generate code, write tests, review PRs.

3. **Hooks as the "nervous system"**: 17 hooks (pre-edit, post-edit, pre-command, pre-task, post-task, session-start, session-end, route, explain, etc.) intercept every user action to route it intelligently, store patterns, and trigger background workers. This is the self-learning loop in practice.

4. **sql.js + HNSW over dedicated vector DB**: Using in-process WASM SQLite (sql.js) instead of a separate PostgreSQL/Chroma/Qdrant server means zero-infrastructure memory. The trade-off is lower scalability (10k entries is the documented LIMIT in search queries), which is acceptable for a per-user local agent.

5. **Plugin marketplace over hard dependencies**: The IPFS-based plugin registry lets users opt into capabilities (federation, security, trading, IoT) without bloating the core install. This is good engineering for a 300-tool surface.

6. **Self-learning as differentiator**: Unlike LangGraph's deterministic DAG or AutoGen's conversational loops, ruflo invests heavily in learning (SONA, MoE, ReasoningBank, EWC++). The bet is that agents that learn from past trajectories produce better results than stateless orchestration -- even if the learning algorithms are heuristic rather than trained.

## 6. Transfer to Lyra

**One transferable idea: MCP-as-Control-Plane for agent coordination.**

Lyra could adopt ruflo's MCP server pattern: instead of building a proprietary agent communication protocol, expose Lyra's swarm coordination, memory operations, and agent lifecycle as MCP tools that any MCP-compatible client can call. This would mean:
- Lyra agents become "just MCP tools" callable from Claude Code, Claude Desktop, or any MCP host
- The orchestrator becomes an MCP tool registry with NATS or HTTP transport
- Plugin marketplaces (Lyra plugins) register MCP tool definitions

**Concrete mechanism to steal:** The `mcp-server.ts` pattern of intercepting console.log/stdout to protect JSON-RPC framing (ruflo#1910, ruflo#2253). If Lyra uses MCP stdio transport, a single stray `console.log` from a lazily-loaded dependency will corrupt the entire protocol stream and brick the session. Ruflo's solution -- `process.env.MCP_STDIO_MODE = '1'` + replacing `console.log/info/debug` with stderr writers + a dedicated `writeFrame()` for protocol frames -- is production-hardened and directly applicable.

**Workstream route:** SS4.x (System Software / Infrastructure) -- specifically SS4.3 (Agent Runtime & Middleware) or SS4.4 (Tool/Plugin System). The MCP tool registry is infrastructure, not a research feature.

**Impact:** 6/10 (Medium-High). MCP is increasingly the standard interface for LLM-tool interaction. Adopting it as Lyra's control-plane protocol would unlock interop with Claude Code, Claude Desktop, and the growing MCP ecosystem without writing custom clients.

**Effort:** 5/10 (Medium). Requires: (1) wrapping existing Lyra agent coordination as MCP tool definitions, (2) an MCP server process (stdio + HTTP transport), (3) JSON-RPC message framing with console hijacking, (4) MCP tool discovery/listing, (5) migrating existing coordination hooks to use the MCP tool registry. The MCP protocol is documented and ruflo provides a reference implementation.

**Tier:** B (Strong recommendation). MCP interop is a strategic capability with clear ecosystem benefits. The implementation risk is low (proven pattern from ruflo). The main cost is migration of existing tool registrations.

**LICENSE:** MIT (compatible with Lyra's licensing).
