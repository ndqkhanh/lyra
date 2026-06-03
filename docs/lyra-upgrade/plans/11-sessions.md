# Sessions — Plan (§4.11)

> Run 3, 2026-06-03

## Plain-Language Summary

Lyra sessions are check-pointed, resumable, and forkable. Each session saves its full transcript + state to disk after every turn. Sessions can be named, listed, resumed, forked (create a branch from any point), and backgrounded. The supervisor daemon (§4.13) manages detached session lifecycle — sessions survive terminal close, sleep, and restart.

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Checkpointing (§3.1) | Per-turn transcript save, resume by session ID or name, fork to branch |
| Claude Code Agent View (§3.1) | Background sessions: detach without stopping, survive terminal close/sleep |
| Lyra's session_fork.py (349L) | Existing fork + resume infrastructure |
| Lyra's resumable.py (311L) | Existing checkpoint/replay |

## Proposed Design

1. **Checkpointing:** Save transcript + state (model, effort, cwd, permission mode) to `~/.lyra/sessions/<id>.jsonl` after each turn.
2. **Session management:** `lyra session list`, `lyra session resume <id|name>`, `lyra session rename <id> <name>`, `lyra session delete <id>`.
3. **Forking:** `lyra session fork <id> --at <turn>` — creates new session branching from specified turn.
4. **Backgrounding:** `/bg` or `lyra --bg` or `←` on empty prompt — detach session, supervisor manages lifecycle.
5. **Session search:** Full-text search across all saved transcripts via SQLite FTS5.

## Build Outline

1. Session state serialization + deserialization (week 1)
2. Session CLI (list/resume/rename/delete) (week 1)
3. Fork from arbitrary turn (week 2)
4. Backgrounding + supervisor integration (week 3, gated on supervisor Phase 3)
5. Transcript search (SQLite FTS5) (week 3)

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| session_fork.py (349L) | KEEP + EXTEND: turn-level fork precision | Low |
| resumable.py (311L) | KEEP + EXTEND: backgrounding integration | Low |
| Session search | ADD: SQLite FTS5 transcript index | None |

**Impact:** 4 | **Effort:** 3 | **Tier:** (A) Parity

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code docs (§3.1). Breakthrough tier gated on evidence from batch research findings.

## Changelog

- Run 4 (2026-06-03): Added Expert Review section, Changelog
