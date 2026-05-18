# Feature Specification: Claude-Code-Parity TUI for Lyra

**Feature ID**: 001-tui-claude-code-parity
**Status**: Draft
**Owner**: Khanh
**Created**: 2026-05-17

---

## 1. Summary

Lyra is an agentic CLI. Today it has a working agent loop but a thin terminal
surface: most progress is invisible until the run completes, sub-agent
parallelism is not shown, slash commands are bare prompts, and there is no
way to expand a collapsed tool output. This spec describes the user-facing
TUI required to bring Lyra to functional parity with the Claude Code v2.x
terminal experience, scoped to the patterns Khanh has observed in real
sessions.

The TUI is the entire visible surface of an agent run: the welcome card,
the prompt input, the streaming output region, the slash-command picker,
the sub-agent tree, the status line, the compaction banner, and the
to-do list. It must show what the agent is doing, what model and how many
tokens it is spending, when it is waiting, when it is compacting, and which
background tasks are still alive — all without blocking the user from typing
the next command.

## 2. Goals and Non-Goals

### Goals

- Reach feature parity with the eight UI patterns documented in the source
  examples (see §5).
- Give the user actionable visibility into every long-running operation
  (sub-agents, tools, research pipelines).
- Make every interactive element keyboard-driven and discoverable.
- Match Claude Code's "feel": streaming responses, animated spinner
  vocabulary, expandable collapsed output, slash-command picker, and a
  persistent status line.

### Non-Goals

- Reimplementing Claude Code's internals (Ink/React reconciler, Yoga layout).
  Lyra is Python; the TUI is Textual.
- Web rendering (`textual serve` is allowed but not required).
- Mouse-only flows or GUI-style modal dialogs.
- Theming beyond Textual's built-in themes plus one high-contrast variant.

## 3. Personas

- **Khanh, the primary author.** Runs Lyra dozens of times a day. Needs to
  see what each agent is doing without `tail -f`-ing five log files. Will
  hit `Ctrl+O` to expand collapsed output, `Ctrl+B` to background a job,
  `/model` to switch model mid-session, and `Esc` to interrupt.
- **A new Lyra contributor.** Has never used the tool. Should be oriented
  by the welcome card, learn key bindings from the footer, and discover
  slash commands from the picker.
- **A researcher reviewing a long run.** Wants to scroll back, expand
  collapsed sections, and trust that the displayed token/timing/model
  numbers reflect reality.

## 4. User Stories (with priorities)

> Priority scale: P0 = must ship in v1, P1 = should ship in v1,
> P2 = stretch.

### US-1 (P0): See what each parallel sub-agent is doing right now
**As** a Lyra user running a research command,
**I want** a live tree of every spawned sub-agent with its label, tool-use
count, token count, and elapsed time,
**so that** I can tell which agent is stuck and which is finishing.

**Acceptance scenarios**
1. **Given** the orchestrator has spawned 4 sub-agents, **when** I look at
   the screen, **then** I see 4 rows under a tree node titled
   `Running N agents…` (where N is the live count), each row showing
   `[status-glyph] [agent-name] [task-summary truncated] · [tool-use-count] tool uses · [token-count] tokens`.
2. **Given** a sub-agent completes, **when** the orchestrator receives
   its result, **then** the row's status glyph flips from a spinner to
   `⎿ Done` and the row stays visible (does not vanish).
3. **Given** a sub-agent is still running, **when** I press `Ctrl+O` on
   its row, **then** the row expands inline to show the worker's most
   recent log line (e.g., `Searching for 1 pattern, reading 13 files…`).
4. **Given** any sub-agent is running, **when** I press `Ctrl+B`, **then**
   the message "(ctrl+b to run in background)" hint becomes "(running in
   background)" and the agent continues but no longer blocks the prompt.

### US-2 (P0): See streaming agent thought and a live status line
**As** a user who just submitted a prompt,
**I want** a one-line "thinking" status above the prompt showing animated
verb, elapsed time, token delta, and a short thought summary,
**so that** I am never wondering "is it still alive?"

**Acceptance scenarios**
1. **Given** the agent is mid-response, **when** I watch the screen,
   **then** the status line shows `[symbol] [animated-verb]… ([elapsed] · ↓ [token-delta] tokens · [thought-status])`
   updated at ≥ 5 Hz, where animated-verb cycles through a curated word
   list (e.g., "Blanching", "Roosting", "Pollinating", "Galloping",
   "Puttering").
2. **Given** the agent emits a thought summary every N turns, **when** the
   summary changes, **then** it replaces the trailing `[thought-status]`
   text without flicker.
3. **Given** the agent's status persists for > 30 s with no token motion,
   **when** I look, **then** the status line shows a stalled-state hint
   `(no tokens for 30s — Esc to interrupt)`.
4. **Given** the agent finishes, **when** the final token arrives, **then**
   the status line collapses to `(no active work)` and the prompt
   re-focuses.

### US-3 (P0): Pick a model interactively with a slash command
**As** a user who wants to switch from Sonnet to Opus mid-session,
**I want** to type `/model`, see a list with descriptions, pick with arrow
keys, and confirm,
**so that** I do not have to remember CLI flags.

**Acceptance scenarios**
1. **Given** I type `/` in the prompt, **when** the next character is a
   letter, **then** a fuzzy-search dropdown appears below the prompt
   listing matching slash commands with one-line descriptions.
2. **Given** I select `/model` and press Enter, **when** the screen
   re-renders, **then** a modal labeled `Select model` opens with the
   available models, their short descriptions, and a checkmark on the
   currently active one.
3. **Given** the modal is open, **when** I press `Up`/`Down`, **then** the
   selection cursor moves and the highlighted row is visually distinct;
   **when** I press `Left`/`Right`, **then** the "effort" slider (or
   equivalent secondary toggle) cycles through its values.
4. **Given** I press `Enter`, **when** the modal closes, **then** the new
   model becomes the session model, the status line shows a one-second
   confirmation toast (`Model: Opus 4.7`), and the change applies to the
   next request.
5. **Given** I press `Esc` on the modal, **when** it closes, **then** no
   change is applied.

### US-4 (P0): Expand collapsed tool output on demand
**As** a user reviewing a tool call that printed 200 lines,
**I want** to see a one-line summary by default and expand on `Ctrl+O`,
**so that** my scrollback is not flooded.

**Acceptance scenarios**
1. **Given** a tool call returns more than 5 lines of output, **when** the
   panel renders, **then** it shows a header `[icon] [tool-name] (ctrl+o
   to expand)` and the first 1–3 lines, truncated with `…`.
2. **Given** the panel is focused or hovered, **when** I press `Ctrl+O`,
   **then** the panel expands inline to show the full output, the header
   updates to `(ctrl+o to collapse)`, and pressing `Ctrl+O` again
   collapses it.
3. **Given** the user scrolls away and the panel goes out of viewport,
   **when** they return, **then** the expanded/collapsed state is
   preserved.

### US-5 (P0): See the welcome card on launch
**As** a user starting Lyra for the first time today,
**I want** a welcome card with my name, the working directory, the active
model, and tips for getting started,
**so that** I know I am in the right place.

**Acceptance scenarios**
1. **Given** Lyra is launched, **when** the TUI mounts, **then** the
   welcome card occupies the top of the screen with: greeting (e.g.,
   `Welcome back Khanh!`), an ASCII/visual mascot, an "info column"
   showing model + plan + account, the current working directory
   (truncated intelligently if long), and a "What's new" / "Tips" panel.
2. **Given** the user submits their first message, **when** the response
   begins streaming, **then** the welcome card collapses to a single
   header line (mascot + current model + cwd) and stays at the top.
3. **Given** the user resizes the terminal narrower than 80 cols,
   **when** the welcome card re-renders, **then** the two-column layout
   stacks vertically and long paths are truncated with `…`.

### US-6 (P1): See a "Conversation compacted" banner with restored context
**As** a user whose long session just compressed its context,
**I want** a one-screen banner listing the artifacts re-loaded after
compaction,
**so that** I trust the next response will know what the previous one knew.

**Acceptance scenarios**
1. **Given** the agent's context exceeds the compaction threshold,
   **when** the compactor runs, **then** a banner renders inline reading
   `Conversation compacted (ctrl+o for history)` followed by a checklist
   of restored items (each with `⎿  Read <path> (<lines> lines)`,
   `⎿  Loaded <skill>`, `⎿  Skills restored (<name>)`).
2. **Given** the user presses `Ctrl+O` on the banner, **when** the
   handler fires, **then** a side pane opens showing the pre-compaction
   conversation summary.

### US-7 (P1): Track multiple background tasks
**As** a user who has put work in the background with `Ctrl+B`,
**I want** a status-line counter (e.g., `5 background tasks`) and a way to
switch to any of them,
**so that** I do not lose track.

**Acceptance scenarios**
1. **Given** ≥ 1 backgrounded worker exists, **when** the status footer
   re-renders, **then** it shows `N background tasks` and a hint
   `Ctrl+T to switch`.
2. **Given** I press `Ctrl+T`, **when** the switcher opens, **then** a
   list shows each backgrounded task with its label, elapsed time, last
   tokens-down delta, and a `↑/↓ to select · Enter to view` footer.
3. **Given** a backgrounded task completes, **when** it finishes, **then**
   the row shows a green check and a toast `Task '<label>' completed
   (Ctrl+T to view)` appears for 3 s.

### US-8 (P1): See a live to-do / phase list during planning
**As** a user whose agent is executing a multi-phase plan,
**I want** an inline list of phases with checkboxes (`◻` pending, `◼`
done) overflowing to `… +N pending`,
**so that** I have shared situational awareness with the agent.

**Acceptance scenarios**
1. **Given** the agent emits a `todo_update` event, **when** the renderer
   receives it, **then** the to-do panel reflects the new list with at
   most 5 visible rows and an overflow footer `… +N pending`.
2. **Given** a phase transitions from pending to done, **when** the
   update arrives, **then** the row's glyph changes and the change
   animates briefly (1 frame highlight) — no full re-render.

### US-9 (P1): Branch / agent-context indicator on the prompt
**As** a user with multiple Lyra sub-agents reporting back,
**I want** a row above the prompt showing the current branch / namespace
(e.g., `⏺ main`) and any selectable agent contexts with `↑/↓ to select ·
Enter to view`,
**so that** I can drill into a specific agent's view.

**Acceptance scenarios**
1. **Given** the orchestrator has named contexts, **when** the screen
   renders, **then** the context row lists each with a glyph
   (`⏺` active, `◯` available), a label, the last activity hint, and an
   elapsed time.
2. **Given** I press `Enter` on a selected context, **when** the focus
   shifts, **then** the main pane scopes to that context's transcript.

### US-10 (P2): Permission-bypass and one-shell indicators
**As** a user who launched with `--dangerously-skip-permissions`,
**I want** a footer pill that always reminds me of the bypass state,
**so that** I never forget I am in "yolo mode".

**Acceptance scenarios**
1. **Given** the bypass flag is set, **when** the footer renders, **then**
   it shows `⏵⏵ bypass permissions on · N shells · esc to interrupt`.
2. **Given** I press `Shift+Tab`, **when** the handler fires, **then**
   the permission mode cycles (read-only → ask → bypass) and the pill
   updates immediately.

## 5. Catalog of UI Surfaces (parity with source examples)

These are the eight discrete surfaces extracted from the provided session
transcripts. Each must exist by name and behavior in the implementation.

| Surface | Source example | What it shows |
|---|---|---|
| **Welcome Card** | `╭─── Claude Code v2.1.142 ───╮ … Welcome back Khanh! …` | Greeting + mascot + model/plan/cwd + tips, collapses after first message |
| **Slash-Command Picker** | typing `/` opens an inline list | Fuzzy-searchable list of slash commands with descriptions |
| **Model Selector Modal** | `Select model` block | Modal list of models with descriptions, checkmark, secondary toggle (effort), Enter/Esc |
| **Status Line ("Spinner")** | `✳ Blanching… (10m 50s · ↓ 62.1k tokens · thought for 28s)` | Animated verb + elapsed + token delta + thought hint, ≥ 5 Hz updates |
| **Sub-Agent Tree** | `Running 4 oh-my-claudecode:executor agents… ├ … · 12 tool uses · 46.8k tokens │ ⎿ Done` | Live tree of sub-agents, per-row tool count + tokens + status + ctrl+b hint, expandable via Ctrl+O |
| **Tool Output Panel (collapsible)** | `Searched for 2 patterns, read 1 file (ctrl+o to expand)` | One-line summary + expand-on-keypress full view |
| **Compaction Banner** | `✻ Conversation compacted (ctrl+o for history) ⎿ Read … ⎿ Loaded …` | Inline checklist of restored skills/files/rules |
| **Footer / Bindings Row** | `⏵⏵ bypass permissions on · 1 shell · esc to interrupt · ↓ to manage` | Persistent permission/bg-tasks/keyboard hints |
| **Context / Branch Row** | `⏺ main ↑/↓ to select · Enter to view` | Active branch / agent context with selection affordance |
| **To-Do Panel** | `◻ Phase 9: … ◻ Phase 3: … … +3 pending` | Live phase list with checkbox glyphs and overflow |

## 6. Functional Requirements

> **FR-XXX** numbers are stable; new requirements get the next free number.

- **FR-001** The TUI MUST render the Welcome Card on launch and collapse it
  to a one-line header on the first user submission.
- **FR-002** The TUI MUST display a Status Line above the prompt while any
  worker is active, updating at ≥ 5 Hz and showing
  `[verb-animated]… ([elapsed] · ↓ [token-delta] tokens · [thought-hint])`.
- **FR-003** The Status Line's animated verb MUST cycle through a list of
  at least 30 curated whimsical verbs (e.g., Blanching, Roosting,
  Pollinating, Galloping, Puttering, Simmering, Marinating).
- **FR-004** The TUI MUST show a Sub-Agent Tree whenever > 0 sub-agents
  are alive; each row MUST show status glyph, label, truncated task
  summary, tool-use count, and tokens.
- **FR-005** The Sub-Agent Tree MUST update each row in place as workers
  emit progress events; rows MUST NOT disappear on completion (they
  transition to a done state).
- **FR-006** Every Tool Output Panel with > 5 lines of output MUST collapse
  by default and MUST expand on `Ctrl+O` when focused.
- **FR-007** The TUI MUST support a fuzzy-search Slash-Command Picker
  triggered by `/` at the start of input; it MUST list at minimum
  `/model`, `/agents`, `/clear`, `/help`, `/init`, `/release-notes`,
  `/btw`, and the application's registered slash commands.
- **FR-008** Selecting `/model` MUST open a modal listing all available
  models with names, descriptions, current selection marker, and a
  secondary toggle for effort/temperature when applicable.
- **FR-009** The Model Selector modal MUST commit the selected model on
  `Enter`, cancel on `Esc`, and emit a 1-second toast on commit.
- **FR-010** The TUI MUST detect a context-compaction event and render
  the Compaction Banner with a checklist of restored items.
- **FR-011** The TUI MUST track background tasks created via `Ctrl+B` and
  surface their count + a `Ctrl+T to switch` hint in the Footer.
- **FR-012** Pressing `Ctrl+T` MUST open a switcher listing every
  background task with label, elapsed time, last token delta, and a
  status glyph.
- **FR-013** Pressing `Esc` MUST attempt to cancel the active (foreground)
  worker within 200 ms via Textual's `Worker.cancel()`.
- **FR-014** The TUI MUST render a Footer pill reflecting the active
  permission mode (read-only / ask / bypass) and the count of live
  shells; pressing `Shift+Tab` cycles the modes.
- **FR-015** The TUI MUST render a To-Do Panel when the agent emits a
  `todo_update` event, with `◻` / `◼` glyphs and a `… +N pending`
  overflow line.
- **FR-016** Every key binding visible to the user MUST appear in the
  Footer bindings row when its target widget is focused.
- **FR-017** All worker output (LLM streaming, tool stdout) MUST be
  rendered incrementally via `Markdown.get_stream()` or `RichLog.write()`;
  the TUI MUST NOT buffer a full response before first paint.
- **FR-018** Streaming render coalescing IS permitted above ~20 events/s
  to avoid UI lag, but the maximum lag between event arrival and screen
  update MUST stay below 100 ms.
- **FR-019** The TUI MUST persist scroll position, expand/collapse state
  of each panel, and command palette history across panel re-renders
  within a session.
- **FR-020** A high-contrast theme MUST be available via the command
  palette (`Change theme`).
- **FR-021** A failure in a Worker MUST surface as a red toast with the
  exception message and a `Ctrl+O for traceback` hint; the TUI MUST NOT
  crash on worker exceptions.
- **FR-022** All visible counters (tokens, tool uses, elapsed seconds)
  MUST be sourced from a single `SessionState` reactive object — no
  per-widget shadow counters.
- **FR-023** The TUI MUST be fully usable without a mouse; every action
  reachable by click is reachable by a documented key binding.
- **FR-024** On terminal resize, the TUI MUST reflow layouts within
  100 ms; no widget may overflow its parent box.

## 7. Key Entities

- **SessionState**: the singleton reactive object holding `model`,
  `cwd`, `permission_mode`, `background_tasks: dict[id, BackgroundTask]`,
  `sub_agents: dict[id, SubAgentState]`, `todos: list[TodoItem]`,
  `compaction_history: list[CompactionEvent]`, and `prompt_history`.
- **SubAgentState**: per sub-agent — `id`, `name`, `label`, `task_summary`,
  `status` (pending/running/done/failed), `tool_uses`, `tokens_in`,
  `tokens_out`, `elapsed_seconds`, `last_log_line`, `expanded: bool`.
- **BackgroundTask**: `id`, `label`, `worker_ref`, `started_at`,
  `last_token_delta`, `status`.
- **ToolPanel**: a renderable for a single tool call — `tool_name`,
  `args_preview`, `output_lines`, `summary_line`, `expanded: bool`,
  `error: str | None`.
- **CompactionEvent**: `triggered_at`, `restored: list[RestoredItem]`,
  where `RestoredItem` is `(kind: read|loaded|skill, path, lines)`.
- **TodoItem**: `id`, `label`, `status` (pending/done/blocked).
- **SlashCommand**: `name`, `description`, `handler`, `requires_modal:
  bool`.

## 8. Edge Cases

- **Terminal width < 60 cols.** Welcome Card stacks vertically; Status
  Line truncates the thought hint first, then elapsed, never the verb;
  Sub-Agent Tree drops the token count before the tool count.
- **A sub-agent's output is binary or has no newlines.** The Tool Output
  Panel shows `(binary output, N bytes — Ctrl+O to dump)`.
- **Compaction triggers while user is typing.** The Compaction Banner
  renders above the prompt; the prompt's typed-but-unsubmitted text is
  preserved.
- **User presses Esc with no active worker.** Esc closes the most
  recently focused modal/panel; if nothing is open, a one-line hint
  appears.
- **A worker raises before producing output.** The Tool Output Panel
  renders with a red header, the exception message, and the `Ctrl+O for
  traceback` hint.
- **The terminal is paused (SIGSTOP, e.g., `Ctrl+Z`).** On resume the
  TUI MUST repaint without missing state.
- **The user resizes from 200 cols to 40 cols mid-render.** No exception;
  layout reflows.
- **A slash command name collides with a typed sentence starting with
  `/`.** The picker requires `/` at column 0 AND no whitespace before
  the next char to activate.
- **Sub-agent emits 1000 progress events/sec.** Render coalescing keeps
  UI responsive; an internal counter shows the per-second event rate to
  the dev console only.

## 9. Out of Scope

- Image rendering inline (terminal image protocols).
- Voice / audio cues.
- Cross-machine SSH session forwarding beyond what the terminal already
  provides.
- A web UI version (deferred; `textual serve` is acceptable as a side
  effect but not a feature).
- Plugin authoring UI for slash commands (slash commands are loaded from
  config; a builder UI is out of scope).

## 10. Success Criteria

- A new contributor can run Lyra, see the welcome card, type a prompt,
  watch the sub-agent tree update live, expand one collapsed tool output,
  switch the model via `/model`, and interrupt with `Esc` — all without
  reading documentation.
- A 10-minute session running 4 parallel sub-agents and ~1000 streamed
  tokens does not exceed 200 MB RSS or drop below 30 fps render rate
  on a 2020-era laptop.
- All 24 FRs have passing automated tests in `tests/tui/`.
- The pytest-textual-snapshot suite has zero unintentional diffs against
  the curated baseline.

---

## Clarifications

> *Mark any open questions with `[NEEDS CLARIFICATION: …]`. None at the
> moment — Khanh confirmed the source examples are the authoritative
> reference.*
