# Sessions — Plan (§4.11)

> Run 3, 2026-06-03 | Deep-read update 2026-06-07

## Plain-Language Summary

Lyra sessions are check-pointed, resumable, and forkable. Each session saves its full transcript + state to disk after every turn. Sessions can be named, listed, resumed, forked (create a branch from any point), and backgrounded. The supervisor daemon (§4.13) manages detached session lifecycle — sessions survive terminal close, sleep, and restart.

## Evidence Synthesis

| Source | Key Insight | Citation |
|--------|------------|----------|
| Claude Code Checkpointing | Per-turn transcript save, resume by session ID or name. 30-day auto-clean retention (configurable). Three restore actions (code+conversation, conversation-only, code-only) and two targeted summarization actions (summarize-from-here, summarize-up-to-here). Fork via `--fork-session`. | Claude Code Checkpointing docs (code.claude.com), "Checkpointing" note |
| Claude Code Agent View | Supervisor daemon with per-user background process, two-axis session state (state x process shape), cheap Haiku-class model for row summaries (15s refresh interval), auto-worktree isolation, idle process reaping (~1h unattached), memory-pressure eviction, configuration persistence across process restart, state survives sleep/supervisor restart (`~/.claude/jobs/<id>/state.json`). | Claude Code Agent View docs (code.claude.com), "Manage multiple agents with agent view" note |
| Lyra's session_fork.py (349L) | Existing fork + resume infrastructure | Internal |
| Lyra's resumable.py (311L) | Existing checkpoint/replay | Internal |
| Letta/MemGPT (letta-ai/letta) | Three-tier memory: Core (always in-context typed blocks), Archival (vector-searchable), Recall (conversation history with auto-compaction at 90% threshold). Tool-editable memory blocks (`memory()` built-in with create/str_replace/insert/delete/rename). Session persistence by default — kill/restart server preserves all agent state. | Letta/MemGPT deep-read note, Apache 2.0, github.com/letta-ai/letta |
| claude-mem (thedotmack) | Progressive-disclosure context injection engine: timeline (titles) -> full observations (selected) -> summary. Token economics displayed (98% compression ratio from LLM-to-LLM observer). SQLite FTS5 schema with auto-sync triggers. 3-layer MCP search (~10x token savings). Session memory captured via lifecycle hooks, persisted across Claude Code restarts. | claude-mem deep-read note, Apache 2.0, github.com/thedotmack/claude-mem |
| OpenCode (anomalyco/opencode) | System Context Registry with typed Context Sources separated from conversation history. Context Epochs — system prompt is a durable snapshot changing only at safe provider-turn boundaries, enabling deterministic retry. Compaction protects recent 40K tokens, prunes before last 20K, starts fresh Context Epoch. Event-sourced session state via Effect-TS. | OpenCode deep-read note, MIT, github.com/anomalyco/opencode |
| Agent Way (wquguru) | Continuity sovereignty must be explicit (main loop vs. thread+rollout+state). Long sessions need compact/truncation/recovery trio. Anti-pattern: "inject first, rescue later" context governance. Source-identifiable instruction fragments with precedence rules. | Agent Way / Comparative Harness Notes (agentway.dev, 2026), Ch.3, Ch.7, Ch.8 |
| continuous-claude (AnandChowdhary) | SHARED_TASK_NOTES.md as relay baton for cross-iteration context continuity. Autonomous loop: branch -> execute -> commit -> PR -> wait CI -> merge. Cost per iteration: ~$0.042. Completion detection via exact phrase or heuristic. | continuous-claude deep-read note, MIT, github.com/AnandChowdhary/continuous-claude |
| Agentic Design Patterns (Gulli, 2025) | Dual memory architecture mandated (short-term + long-term). Exception handling three-phase pipeline: detection -> handling -> recovery. NEVER directly mutate session state — use event-driven state_delta or output_key. | Agentic Design Patterns, Ch.8 (Memory Management), Ch.12 (Exception Handling and Recovery) |
| Agentic Architectural Patterns (Arsanjani, 2026) | Shared Epistemic Memory as single source of truth outside agent context windows. Supervision Tree with guarded capabilities: hierarchical failure containment ("let it crash" + automatic recovery). State persistence/checkpointing essential for Task Delegation frameworks. | Agentic Architectural Patterns, Ch.5 (Multi-Agent Coordination Patterns), Ch.6 (Shared Epistemic Memory) |

## Proposed Design

1. **Checkpointing:** Save transcript + state (model, effort, cwd, permission mode) to `~/.lyra/sessions/<id>.jsonl` after each turn.
   - **Adopt Claude Code's orthogonal checkpoint dimensions** (code state, conversation state, decision trace) for selective rollback. Source: Claude Code Checkpointing docs.
   - **Adopt Letta's block-based memory model** for structured, tool-editable memory blocks within session state — add `MemoryBlock` class (label, value, limit, read_only). Source: Letta/MemGPT deep-read note.
   - **Adopt OpenCode's Context Epoch pattern**: system prompt is a durable snapshot changing only at safe turn boundaries. Compaction starts a fresh epoch. Source: OpenCode deep-read note.

2. **Session management:** `lyra session list`, `lyra session resume <id|name>`, `lyra session rename <id> <name>`, `lyra session delete <id>`.
   - **Adopt Claude Code's shell-accessible management commands** (`claude attach/logs/stop/respawn/rm/daemon`) for scripting and CI integration. Source: Claude Code Agent View docs.
   - **Adopt claude-mem's SQLite FTS5 schema** for session metadata storage and search. Source: claude-mem deep-read note.

3. **Forking:** `lyra session fork <id> --at <turn>` — creates new session branching from specified turn.
   - **Adopt continuous-claude's SHARED_TASK_NOTES.md relay baton pattern**: each fork carries a structured notes file recording what was done, what is next, gotchas. Source: continuous-claude deep-read note.

4. **Backgrounding:** `/bg` or `lyra --bg` or `<-` on empty prompt — detach session, supervisor manages lifecycle.
   - **Adopt Claude Code's two-axis state model** (state x process shape) to separate logical progress from process lifecycle. Source: Claude Code Agent View docs.
   - **Adopt auto-worktree isolation** for parallel background sessions (mapped to Lyra's EnterWorktool). Source: Claude Code Agent View docs.
   - **Adopt memory-pressure eviction of idle sessions**. Source: Claude Code Agent View docs.

5. **Session search:** Full-text search across all saved transcripts.
   - **Adopt claude-mem's progressive-disclosure tiers**: timeline (titles) -> full details (selected items) -> summary, with token economics display. Source: claude-mem deep-read note.
   - **Use SQLite FTS5** with porter+unicode tokenizer for keyword search, opt-in vector search (Chroma) later. Source: claude-mem deep-read note.

6. **(Breakthrough enhancement) Session state machine with orthogonal dimensions:**
   - Independently version Knowledge state (artifacts, findings), Conversation history (transcript), and Agent decision trace (router logs, tool calls).
   - Enable selective rollback: rewind research output without losing conversation trail, or rewind conversation without discarding findings.
   - Source: Claude Code Checkpointing docs (decoupled checkpoint dimensions), Agent Way Ch.3 (continuity sovereignty).
   - Impact: enables surgical recovery instead of full-session rewind.

## Trade-off Analysis

### Synchronous vs. Asynchronous Session State Persistence
| Approach | Latency | Durability | Complexity |
|----------|---------|------------|------------|
| Per-turn synchronous write (Claude Code model) | Adds ~5-20ms per turn | Full durability at every step | Low: simple append to JSONL |
| Batched async write (every N turns or timer) | Near-zero overhead | Loss of up to N turns on crash | Low: batch buffer + flush timer |
| Event-sourced incremental (OpenCode model) | Per-event write latency | Full event-level replay | High: EventV2, projectors, aggregates |
| **Recommendation:** Synchronous append per turn for transcript. Event-sourced for decision trace (audit trail). Batched for large artifacts. | | | |

### Fork Model: Copy-on-Write vs. Reference + Diff
| Approach | Storage | Fork Cost | Isolation |
|----------|---------|-----------|-----------|
| Copy-on-Write (full transcript copy) | O(n) per fork | High for long sessions | Full isolation |
| Reference + Journal (base + diff log) | O(1) per fork, O(delta) journals | Low (metadata only) | Needs compaction to bound diff chain length |
| **Recommendation:** Start with copy-on-write (simple, safe). Graduate to reference + journal when fork counts exceed 10 per base session. | | | |

### Search Index: SQLite FTS5 vs. Vector (Chroma) vs. Hybrid
| Approach | Recall | Infrastructure | Latency |
|----------|--------|----------------|---------|
| SQLite FTS5 (porter+unicode61) | Keyword match only | Zero: built into SQLite | <5ms |
| Chroma vector search | Semantic match | Requires Python/uv runtime | ~50-200ms |
| Hybrid (FTS5 + Chroma with fallback) | Best of both | Both infra needed | FTS5 fallback: <5ms; full: ~200ms |
| **Recommendation:** FTS5 first (claude-mem proven, zero infra). Vector search as optional upgrade. | | | |
| Source: claude-mem deep-read note (progressive disclosure + FTS5 schema + Chroma opt-in). | | | |

### Context Compression on Resume
| Technique | Compression Ratio | Accuracy Preservation | Latency Cost |
|-----------|------------------|----------------------|--------------|
| Targeted summarization (Claude Code) | Variable (user-directed) | Very high (human chooses what to keep) | Low (one summarizer call per action) |
| claude-mem LLM-to-LLM compression | ~98% (structured observations) | High (observation extraction preserves semantics) | Medium (observer Claude call per turn end) |
| Redundancy-aware pruning (R-KV style) | Up to 90% KV reduction | ~100% of FullKV at 10-34% retention | Low (training-free, per-128-token batch) |
| **Recommendation:** Targeted summarization for human-initiated compaction. R-KV-style redundancy pruning (cosine similarity of chunk embeddings) for automatic context compression during long sessions. claude-mem-style observer for cross-session memory persistence. | | | |
| Source: R-KV arXiv:2505.24133v4 (NeurIPS 2025, redundancy-aware KV pruning at up to 90% reduction); claude-mem deep-read note (98% token compression through LLM-to-LLM observer); Claude Code Checkpointing docs (targeted summarization). | | | |

## Build Outline

1. Session state schema + per-turn JSONL persistence (week 1)
   - Decouple transcript, decision trace, and artifact state into independently versioned dimensions
   - Source: Claude Code Checkpointing docs (orthogonal checkpoint dimensions)
2. Session CLI (list/resume/rename/delete) + SQLite FTS5 search (week 1-2)
   - FTS5 schema based on claude-mem's proven design (porter+unicode61 tokenizer, auto-sync triggers)
   - Source: claude-mem deep-read note, SQLite FTS5 proven at 33 schema versions
3. Fork from arbitrary turn with copy-on-write (week 2)
   - Include SHARED_TASK_NOTES.md relay baton in each fork
   - Source: continuous-claude deep-read note (relay baton), Claude Code Checkpointing docs
4. Backgrounding + supervisor integration (week 3, gated on supervisor Phase 3)
   - Two-axis state model (state x process shape)
   - Auto-worktree isolation for parallel sessions
   - Memory-pressure eviction of idle sessions
   - Source: Claude Code Agent View docs
5. Advanced: session context compression on resume (optional, Phase 4)
   - R-KV-style redundancy pruning: compute pairwise cosine similarity of chunk embeddings, score as `Z = lambda * relevance - (1-lambda) * max_similarity`, retain top-K
   - Source: R-KV arXiv:2505.24133v4, Lyra internal context-engineering synthesis R4

## Evidence Base

Sources consulted for this plan revision:

### Technical Docs
1. **Claude Code Checkpointing** (code.claude.com) — Per-turn transcript save, 30-day retention, rewind menu (3 restore + 2 summarize actions), orthogonal state dimensions, fork via `--fork-session`. Web note at `notes/web/https___code_claude_com_docs_en_checkpointing.md`.
2. **Claude Code Agent View** (code.claude.com) — Supervisor daemon, two-axis state model, Haiku-class row summaries (15s refresh), auto-worktree isolation, idle reaping (~1h), memory-pressure eviction, state survives sleep/restart (`~/.claude/jobs/<id>/state.json`). Web note at `notes/web/https___code_claude_com_docs_en_agent-view.md`.

### Papers
3. **R-KV: Redundancy-aware KV Cache Compression** (Cai et al., NeurIPS 2025, arXiv:2505.24133v4) — Joint importance-redundancy scoring: `Z = lambda*I - (1-lambda)*R`. At 34% retention preserves ~100% MATH-500 accuracy. Up to 90% KV cache reduction. Training-free, per-128-token batch.

### Open-Source Repos
4. **Letta/MemGPT** (letta-ai/letta, Apache 2.0) — Three-tier memory (Core + Archival + Recall), auto-compaction at 90% threshold, tool-editable memory blocks, session persistence across server restart. Web note at `notes/web/letta-ai__letta.md`.
5. **claude-mem** (thedotmack/claude-mem, Apache 2.0) — Progressive-disclosure context injection (98% compression via LLM-to-LLM observer), SQLite FTS5 schema with auto-sync triggers, 3-layer MCP search (~10x token savings). Web note at `notes/web/thedotmack__claude-mem.md`.
6. **OpenCode** (anomalyco/opencode, MIT) — System Context Registry with typed Context Sources, Context Epochs (durable snapshot at safe turn boundaries), event-sourced session state, compaction at 40K/20K token thresholds. Web note at `notes/web/anomalyco__opencode.md`.
7. **continuous-claude** (AnandChowdhary/continuous-claude, MIT) — SHARED_TASK_NOTES.md relay baton, autonomous iteration loop (branch->execute->PR->merge), ~$0.042/iteration. Web note at `notes/web/AnandChowdhary__continuous-claude.md`.

### Books
8. **Agentic Design Patterns** (Gulli, Springer 2025) — Ch.8 Dual Memory Architecture, Ch.12 Exception Handling as three-phase pipeline (detection -> handling -> recovery). Book notes at `notes/books/agentic-design-patterns-chapters.md`.
9. **Agentic Architectural Patterns** (Arsanjani, Packt 2026) — Ch.5 Task Delegation with checkpointing, Supervision Tree with "let it crash" recovery, Ch.6 Shared Epistemic Memory. Book notes at `notes/books/agentic-architectural-patterns-arsanjani-chapters.md`.
10. **Agent Way / Comparative Harness Notes** (wquguru, agentway.dev, 2026) — Ch.3 continuity sovereignty, Ch.7 "inject first, rescue later" anti-pattern, Ch.8 compact/truncation/recovery trio. Book notes at `notes/books/agentway-comparing-harnesses-chapters.md`.

### Lyra-Internal
11. **Context Engineering Thematic Synthesis** (Lyra internal, 2026-06-07) — R-KV adoption recommendation (R4) for redundancy-aware pruning in session context assembly. Synthesis at `synthesis/context-engineering.md`.
12. **Lyra's session_fork.py (349L)** — Existing fork + resume infrastructure.
13. **Lyra's resumable.py (311L)** — Existing checkpoint/replay.

## Baseline Delta

| Component | Change | Migration Cost | Evidence |
|-----------|--------|---------------|----------|
| session_fork.py (349L) | KEEP + EXTEND: turn-level fork precision, add SHARED_TASK_NOTES.md relay baton | Low | continuous-claude relay baton pattern; Claude Code `--fork-session` |
| resumable.py (311L) | KEEP + EXTEND: backgrounding integration, orthogonal checkpoint dimensions | Low | Claude Code Checkpointing (3 restore + 2 summarize actions) |
| Session search | ADD: SQLite FTS5 transcript index | None | claude-mem FTS5 schema (proven at v33), porter+unicode61 tokenizer |
| Session state persistence | REWRITE: adopt Letta block-based memory + OpenCode Context Epochs | Medium | Letta three-tier memory; OpenCode System Context Registry |
| Supervisor integration | ADD: two-axis state model, auto-worktree isolation, memory-pressure eviction | Medium | Claude Code Agent View docs |
| Context compression on resume | ADD: R-KV-style redundancy pruning (optional, Phase 4) | Low-Medium | R-KV arXiv:2505.24133v4 (training-free, per-128-token batch) |

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Deep-read findings that strengthen the plan:**

1. **Progressive-disclosure context injection (claude-mem)** beats Claude Code's all-in-one context injection by giving the agent a searchable, tiered memory index. Token economics display (98% savings) makes the trade-off transparent. Adopt for Phase 4 cross-session memory.

2. **Targeted summarization (Claude Code Checkpointing)** is superior to all-or-nothing compact for session context management. The summarize-from-here / summarize-up-to-here actions let operators surgically recover context without full rewind.

3. **Event-sourced session state (OpenCode)** provides deterministic retry and auditability that Claude Code's state model lacks. Adopt for decision trace dimension; transcript can stay append-only JSONL.

4. **R-KV redundancy pruning** is a training-free mechanism to extend effective session length by compressing semantically duplicate content at the embedding level. Lyra should implement this as a context assembly filter before attempting full COMEM-style decoupled memory.

**Sign-off:** Plan is feasible with strong evidence alignment. Structure by evidence strength: parity from Claude Code docs (strongest), FTS5 schema from claude-mem (proven), block-based memory from Letta (Apache 2.0, code-available), Context Epochs from OpenCode (MIT). R-KV-style pruning is the one breakthrough candidate with peer-reviewed validation (NeurIPS 2025) and low implementation risk (training-free).

## Changelog

- Run 4 (2026-06-07): Deep-read update — expanded Evidence Synthesis to 10 sources, added Trade-off Analysis (4 tables), added Evidence Base section (13 sources), added R-KV-style context compression breakthrough enhancement, added Letta/OpenCode/claude-mem/continuous-claude patterns. 26 new citations added.
- Run 3 (2026-06-03): Added Expert Review section, Changelog
