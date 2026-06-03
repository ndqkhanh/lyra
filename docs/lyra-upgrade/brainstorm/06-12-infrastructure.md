# Brainstorm — Infrastructure Workstreams (§4.6-§4.12 + §4.23 + §4.26 + §5.1-5.2)

> Run 1 — June 3, 2026 | Combined for efficiency — each workstream gets ≥1 breakthrough idea

---

## §4.6 Tools

### Breakthrough Idea: Deferred Tool Loading + Tool Search + Provider-Normalized Schemas

**Sources Fused:** Claude Code Tool Search + ANX Protocol 3EX (2604.04820) + lean-ctx Token Dense Dialect

- **Deferred Loading:** Only load tool schemas for tools the agent is likely to use (matching query). Scales to 10K+ tools without context bloat.
- **Tool Search:** Agent queries "I need to deploy to Kubernetes" → returns k8s-related tools with descriptions. Threshold mode for confidence-gating.
- **Provider-Normalized:** Tool schema normalized to Lyra's internal format → translated per-provider (Anthropic tool_use vs OpenAI function vs DeepSeek tool_calls)
- **ANX 3EX Decoupling:** Tool execution decoupled from tool definition → 47-66% token reduction vs inline MCP
- **Output Compression:** lean-ctx Token Dense Dialect applied to tool outputs → 89-99% reduction

**Impact:** 5 | **Effort:** 3 | **Tier:** (A) Parity

---

## §4.7 Plugins

### Breakthrough Idea: Hook-Based Plugin System with Hot-Reload

- Plugins = packaged hooks + skills + tools in a directory
- `lyra/plugins/<name>/plugin.json` + hooks + skills + tools
- Install via: `lyra plugin install <url>`, `lyra plugin enable/disable <name>`
- Hot-reload: enabled plugins loaded at session start, configurable per-session
- Marketplace: community plugin registry (GitHub-based)
- Isolation: plugins run with restricted permissions (can't access other plugins' data)

**Impact:** 3 | **Effort:** 3 | **Tier:** (A) Parity

---

## §4.8 MCP

### Breakthrough Idea: Multi-Transport MCP Gateway + ANX Token Optimization

- **Multi-Transport:** stdio, HTTP/SSE, WebSocket transports
- **Server Discovery:** bundle top-10 MCP servers (filesystem, git, web search, database, memory)
- **Dynamic Tool Updates:** server notifies client when tools change (tool list change notifications)
- **OAuth 2.0:** standard MCP auth flow for remote servers
- **ANX 3EX Decoupling:** 47-66% token reduction by decoupling tool definition from execution
- **Auto-Reconnect:** server crash → auto-reconnect with exponential backoff

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

---

## §4.9 Commands

### Breakthrough Idea: Slash-Command System with Skill Integration

- `/help`, `/clear`, `/config`, `/model`, `/effort`, `/fleet`, `/voice`, `/dream`, `/research`
- Each command maps to a Lyra subsystem (no LLM needed for pure UI commands)
- `/skill <name>` manually invokes a skill
- `/workflow <name>` runs a saved workflow
- Command aliases: user-configurable (`/dr` → `/deep-research`)
- Tab-completion for command names and arguments

**Impact:** 3 | **Effort:** 2 | **Tier:** (A) Parity

---

## §4.11 Sessions

### Breakthrough Idea: Checkpointing with Selective Restore

- Per-prompt snapshots: save before each agent turn
- Selective restore: restore code only, conversation only, or both
- Session resume: `lyra resume <session-id>` rehydrates full state from disk
- Session search: SQLite FTS5 over session transcripts
- Session branching: fork a session at any checkpoint to explore alternatives
- Automatic summarization on long sessions (>100 turns) with key decision preservation

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

---

## §4.23 Knowledge Ingestion / RAG

### Breakthrough Idea: Multi-Agent RAG with Freshness Management

**Sources Fused:** SEMA-RAG (2605.17101) + GraphRAG (2404.16130) + ClusterRAG (2605.18769) + MASS-RAG (2604.18509)

- **Decoupled RAG Agents:** Interpreter (schema interpretation) + Explorer (sufficiency-driven multi-round retrieval) + Arbiter (evidence adjudication) — replaces single-round static retrieval. +6.46 acc pts avg.
- **Graph RAG:** Automatically extract entities + relationships from ingested documents → knowledge graph → graph-based retrieval for multi-hop questions
- **Freshness Management:** Track when each ingested source was last updated; auto-reindex stale sources; invalidation markers for outdated information
- **Multimodal Ingestion:** PDFs (text + images), audio (transcribe), codebases (AST indexing), spreadsheets (structural sketch + row/col summaries)
- **ClusterRAG Personalization:** Group documents by user profiles for personalized retrieval

**Impact:** 4 | **Effort:** 4 | **Tier:** (B) Breakthrough

---

## §4.26 Harness Engineering Discipline

### Breakthrough Idea: 5-Pillar Harness Engineering Subsystem

**Sources Fused:** OpenAI 1M lines + Netflix 4-pillar + Anthropic Context Cookbook + ThoughtWorks 5 building blocks

1. **Context Engineering:** Adaptive compaction, memory, tool clearing, "less is more" (system prompt and tool count minimized, evals gate additions)
2. **Evaluation Infrastructure:** Capability evals (ceiling) + regression evals (floor) + simulation personas + continuous eval refresh (100% pass rate = useless signal)
3. **Safety Architecture:** 5-layer defense-in-depth across Prompt → Schema → Runtime → Tool → Lifecycle
4. **Methodology:** AI-native SDLC — spec-to-code pipelines, agent lanes in CI/CD, adversarial review gates
5. **Platform Prerequisites:** CI/CD + IaC + observability + security scanning — fix foundations before adding agents

**Impact:** 4 | **Effort:** 5 | **Tier:** (B) Breakthrough

---

## §5.1 rmux Clean-Room Rebuild

### Breakthrough Idea: Lyra Terminal Multiplexer with Worktree Integration

- Clean-room rebuild of tmux-like terminal multiplexing
- PTY hosting: spawn/manage pseudo-terminals for each session
- Detach/reattach: sessions survive terminal close
- **Worktree Integration (the differentiator):** Each PTY pane is backed by a git worktree — edit isolation built into the multiplexer
- Pane layout: fleet view (top), session terminal (main), status bar (bottom)
- Resolve ownership: rmux owns PTY/terminal I/O; supervisor owns session lifecycle; worktrees own file isolation

**Impact:** 3 | **Effort:** 4 | **Tier:** (A) Parity

---

## §5.2 Multi-Tenancy (AgentsMesh)

### Evaluation: NOT Recommended for Lyra

**Pros:** Multi-user isolation, shared resource pooling, tenant-level billing
**Cons:** Massive complexity increase, Lyra is designed as a single-user terminal agent, multi-tenancy conflicts with local-first architecture, adds network attack surface

**Recommendation:** Lyra stays single-user (local agent harness). Multi-tenancy is a different product category (enterprise platform). If needed later, implement as a separate `lyra-server` product with tenant isolation.

---

## §5.3 Voice SFX (fold into §4.18)

See plans/18-voice-mode.md and voice-mode.md for the complete voice pack design.
