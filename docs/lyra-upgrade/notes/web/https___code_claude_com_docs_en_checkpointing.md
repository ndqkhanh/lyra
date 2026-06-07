# Checkpointing (code.claude.com / Anthropic)

## Key Technical Claims

- Claude Code automatically tracks file edits as checkpoints, enabling undo/rewind of code changes and conversation history within a session.
- Checkpoints persist across sessions (survive resume), giving a safety net for ambitious, wide-scale tasks.
- Every user prompt creates a new checkpoint.
- Checkpoints are auto-cleaned after 30 days (configurable).
- The rewind menu offers five distinct actions on any checkpoint, separating concerns between code state and conversation state.

## Architecture/Mechanism Details

**Automatic tracking**: Every prompt-triggered file edit generates a checkpoint. The system captures state before each edit using Claude's file-editing tool calls, not filesystem snapshots.

**Rewind menu** (triggered via `/rewind` or double-Esc on empty input):

Three restore actions (destructive -- reverts state):
| Action | Code reverted? | Conversation reverted? |
|---|---|---|
| Restore code and conversation | Yes | Yes |
| Restore conversation | No | Yes |
| Restore code | Yes | No |

Two summarize actions (non-destructive -- compresses context, files untouched):
| Action | What happens |
|---|---|
| Summarize from here | Selected message onward replaced with AI summary; earlier messages intact. |
| Summarize up to here | Messages before selected point replaced with summary; later messages intact. |

Both summarize options accept optional user instructions to guide what the summary emphasizes. Original messages survive in the session transcript for reference.

**Comparison to `/compact`**: The summarize actions are targeted -- they compress only one side of a chosen checkpoint, not the entire conversation.

**Forking** (related feature): `claude --continue --fork-session` branches off and preserves the original session intact, complementing the in-session summarize/restore.

## Numbers & Benchmarks (if any)

- **30-day retention** for checkpoints (configurable, but no lower/upper bounds documented).
- No performance benchmarks, storage costs, or latency numbers published.

## Limitations

1. **Bash command changes not tracked** -- `rm`, `mv`, `cp`, `git` operations from the shell are invisible to checkpointing. Only file-editing tool calls are captured.
2. **External changes not tracked** -- manual IDE edits or other concurrent Claude Code sessions on the same files are normally not captured (unless they touch files the current session has already checkpointed).
3. **Not a replacement for version control** -- checkpoints are local undo, not permanent history. Git is still the canonical source of truth for long-term record.
4. **Session-scoped** -- checkpoints are tied to a session. Cross-session branching requires the fork mechanism, not rewind.

## Transfer to Lyra

**Core idea**: Decouple checkpoint/rewind into orthogonal dimensions of agent state, and make summary actions targeted (from-here vs. up-to-here).

Lyra should implement a **session state machine** where at least three dimensions of agent state are independently versioned:

| Dimension | What it captures | Lyra analogue |
|---|---|---|
| Knowledge state | artifacts written, research findings saved | `plans/*`, `findings-*.md`, note files |
| Conversation history | prompts + agent responses | Session transcript |
| Agent decision trace | tool calls, router decisions, safety checks | Router logs, guardrail invocations |

The transferable designs from this page:

1. **Selective rollback**: Lyra should let an operator rewind research output without losing the conversation trail, or rewind the conversation history without discarding findings. This maps directly to the three restore actions in Claude Code's checkpointing.

2. **Targeted summarization**: Lyra's context window management should support compressing "early setup" discussion (summarize up to here) vs. discarding "side exploration" (summarize from here), rather than only an all-or-nothing compact. This is especially useful in Lyra's multi-phase research loops where early goal-setting is precious but intermediate exploration is noisy.

3. **Checkpoint-as-fork-point**: The existence of `--fork-session` suggests that checkpoints should be first-class branchable objects, not just undo history. Lyra could use this to spawn parallel research threads from a common checkpoint (e.g., explore two routing strategies from the same session state).

**Workstream route**: These ideas serve the Reliability (brainstorm 16) and Safety (brainstorm 17) workstreams, since checkpoint integrity underpins both recoverability (reliability) and audit trail preservation (safety). Targeted summarization also feeds into Context Management (brainstorm 03).

**Suggested placement**: Section 4.4 (Reliability Engine) and/or a new Section 4.x dedicated to "Session State & Recovery."
