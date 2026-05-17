# Tasks: Claude-Code-Parity TUI for Lyra

**Feature**: 001-tui-claude-code-parity
**Generated from**: `plan.md` (sections §2, §4, §6, §7)
**Convention**: each task is committed in its own commit using the
project commit-message template; tasks are grouped by phase to allow
parallel work where dependencies permit.

> **Parallelism legend**: `[P]` = safe to do in parallel with other `[P]`
> tasks in the same phase; `[S]` = strictly sequential.

---

## Phase 0 — Project Scaffolding

- [ ] **T001 [S]** Add `textual>=0.86`, `rich>=13.7`,
  `pytest-textual-snapshot`, `structlog`, `textual-autocomplete` to
  `pyproject.toml`. Update `uv.lock`.
- [ ] **T002 [S]** Create directory tree under `src/lyra_cli/tui/` exactly
  as in plan §2; add `__init__.py` files.
- [ ] **T003 [S]** Add `--tui` flag to the CLI entrypoint; when set, boot
  `LyraApp().run()`; otherwise keep the existing headless path.
- [ ] **T004 [P]** Wire `structlog` to write to `~/.lyra/logs/tui.log`
  (rotating, 5 × 5 MB); mirror to `textual console` when
  `LYRA_DEBUG=1`.
- [ ] **T005 [P]** Add a `Makefile` (or `justfile`) target `make tui-dev`
  that runs `uv run textual run --dev src/lyra_cli/tui/app.py:LyraApp`.

## Phase 1 — State & Event Bus

- [ ] **T010 [S]** Implement `state.py` with `SessionState`, `SubAgentState`,
  `BackgroundTask`, `TodoItem`, `CompactionEvent` per plan §4.1.
- [ ] **T011 [S]** Implement `events.py` with the `AgentEvent` tagged
  union per plan §4.2 (`contracts/agent-events.md`).
- [ ] **T012 [S]** Implement `bus.py`: a `@work(group="bus")` consumer
  that reads `asyncio.Queue[AgentEvent]` and calls
  `_handle_<kind>` methods on `SessionState`. Each handler mutates
  state via `call_from_thread` semantics (use `app.post_message` to
  stay on the event loop).
- [ ] **T013 [S]** Unit-test the bus with a recorded JSONL fixture
  containing one of each event kind; assert final `SessionState`.

## Phase 2 — Root App Shell

- [ ] **T020 [S]** Implement `app.py` with `LyraApp(App)`:
  - `CSS_PATH = "styles/app.tcss"`
  - `BINDINGS` including: `ctrl+p` command palette (built-in),
    `ctrl+c` ignore (replace with bell + interrupt hint),
    `esc` interrupt, `shift+tab` cycle permission mode,
    `ctrl+b` background, `ctrl+t` switcher, `ctrl+o` expand/collapse
    (proxied to focused widget), `ctrl+l` clear.
  - `compose()` yields `Header`, `MainScreen`, `Footer`.
- [ ] **T021 [S]** Implement `screens/main.py` with the layout grid:
  WelcomeCard top, transcript region middle (scrollable
  `VerticalScroll`), StatusLine + PromptInput bottom, FooterBar fixed.
- [ ] **T022 [P]** Add `styles/app.tcss` with the base palette and
  high-contrast variant.

## Phase 3 — Welcome Card (FR-001)

- [ ] **T030 [P]** Implement `widgets/welcome_card.py` per plan §6.1.
- [ ] **T031 [P]** Add `styles/welcome.tcss`.
- [ ] **T032 [P]** Snapshot test: default render at 120 cols and 60 cols
  (`tests/tui/test_welcome.py`).
- [ ] **T033 [P]** Pilot test: submit a message; assert the card
  collapses within one frame.

## Phase 4 — Status Line (FR-002, FR-003)

- [ ] **T040 [P]** Add `verbs.py` with the 50-word curated verb list.
- [ ] **T041 [S]** Implement `widgets/status_line.py` per plan §6.2.
- [ ] **T042 [P]** Snapshot test: status line at three states
  (idle, active, stalled-30s).
- [ ] **T043 [P]** Pilot test: feed `TokenDelta` events; assert the
  rendered token count matches.

## Phase 5 — Sub-Agent Tree (FR-004, FR-005, US-1)

- [ ] **T050 [S]** Implement `widgets/sub_agent_tree.py` per plan §6.3.
- [ ] **T051 [P]** Pilot test: spawn 4 agents (via bus fixture); assert
  4 child nodes; tick 10 `SubAgentProgress` events; assert in-place
  updates and no flicker (timing-based: render-count assertion via
  Textual's screen update counter).
- [ ] **T052 [P]** Pilot test: send `SubAgentDone(success=True)`; assert
  status glyph flips to `⎿ Done` and node remains.
- [ ] **T053 [P]** Pilot test: focus a node, press `Ctrl+O`; assert
  inline leaf showing `last_log_line` is added; press again — assert
  removed.
- [ ] **T054 [P]** Snapshot test: tree with 4 running + 2 done agents.

## Phase 6 — Tool Output Panel (FR-006)

- [ ] **T060 [S]** Implement `widgets/tool_output_panel.py` per plan §6.4.
- [ ] **T061 [P]** Pilot test: stream 20 chunks via `ToolCallChunk`;
  panel stays collapsed; `Ctrl+O` expands; full output visible.
- [ ] **T062 [P]** Pilot test: a chunk with `is_stderr=True` after one
  stdout chunk; assert error styling on the stderr line.
- [ ] **T063 [P]** Pilot test: `ToolCallEnd(success=False, error=...)`;
  assert header turns red and traceback hint is shown.
- [ ] **T064 [P]** Snapshot test: collapsed vs expanded.

## Phase 7 — Slash-Command Picker (FR-007)

- [ ] **T070 [S]** Implement `widgets/prompt_input.py` with the slash
  suggester per plan §6.5.
- [ ] **T071 [S]** Implement a `SlashCommand` registry in
  `tui/slash_commands.py`; register `/model`, `/agents`, `/clear`,
  `/help`, `/init`, `/release-notes`, `/btw`.
- [ ] **T072 [P]** Pilot test: type `/mo`; assert dropdown lists
  `/model`; press `Enter`; assert `SlashCommandInvoked("/model")` is
  posted.
- [ ] **T073 [P]** Pilot test: type `/  ` (slash then text without
  match); assert dropdown does NOT appear (per edge-case rule).

## Phase 8 — Model Selector Modal (FR-008, FR-009)

- [ ] **T080 [S]** Implement `screens/model_picker.py` per plan §6.6.
- [ ] **T081 [S]** Wire `SlashCommandInvoked("/model")` → push
  `ModelSelectorModal` → on result call
  `LyraApp.action_apply_model(result)` → post `ModelChanged` event.
- [ ] **T082 [P]** Pilot test: open modal; press `Down`; press `Enter`;
  assert new model committed; assert toast shown.
- [ ] **T083 [P]** Pilot test: open modal; press `Esc`; assert no model
  change.
- [ ] **T084 [P]** Snapshot test: modal at default size and at 60 cols.

## Phase 9 — Compaction Banner (FR-010)

- [ ] **T090 [P]** Implement `widgets/compaction_banner.py` per plan §6.7.
- [ ] **T091 [P]** Pilot test: send `CompactionStart` then
  `CompactionRestored(items=[...])`; assert banner renders with
  checklist; press `Ctrl+O`; assert side pane opens.
- [ ] **T092 [P]** Snapshot test: banner with 5 restored items.

## Phase 10 — Background Switcher (FR-011, FR-012, US-7)

- [ ] **T100 [S]** Implement `screens/background_switcher.py` per plan §6.8.
- [ ] **T101 [S]** Wire `Ctrl+B` on a focused sub-agent node to migrate
  its worker to `group="background"` and add a `BackgroundTask` to
  state.
- [ ] **T102 [S]** Wire `Ctrl+T` to push the switcher.
- [ ] **T103 [P]** Pilot test: background two agents; press `Ctrl+T`;
  assert both rows visible; select one and press `Enter`; assert it
  returns to foreground.
- [ ] **T104 [P]** Snapshot test: switcher with 3 tasks.

## Phase 11 — To-Do Panel (FR-015)

- [ ] **T110 [P]** Implement `widgets/todo_panel.py` per plan §6.9.
- [ ] **T111 [P]** Pilot test: feed `TodoUpdate` with 8 items (5 visible
  + 3 overflow); assert `… +3 pending` rendered.
- [ ] **T112 [P]** Pilot test: a `done` transition; assert glyph change
  and the 1-frame highlight class applied/removed.
- [ ] **T113 [P]** Snapshot test: 8-item list.

## Phase 12 — Context / Branch Row (US-9)

- [ ] **T120 [P]** Implement `widgets/context_row.py` per plan §6 (item
  for context selection).
- [ ] **T121 [P]** Pilot test: feed two contexts via bus; navigate with
  `↑/↓`; press `Enter`; assert main pane scopes to the selected
  context.

## Phase 13 — Footer Bar (FR-014, FR-016, US-10)

- [ ] **T130 [P]** Implement `widgets/footer_bar.py` per plan §6.10.
- [ ] **T131 [P]** Pilot test: `Shift+Tab` cycles permission mode and
  the pill updates immediately.
- [ ] **T132 [P]** Pilot test: with two background tasks live, the
  footer shows `2 background tasks · Ctrl+T to switch`.
- [ ] **T133 [P]** Snapshot test: footer in each of the three permission
  modes.

## Phase 14 — Cancellation & Robustness (FR-013, FR-018, FR-021)

- [ ] **T140 [S]** Implement `LyraApp.action_interrupt()` that cancels
  the `agent` worker group; ensure each worker catches
  `asyncio.CancelledError` and exits cleanly.
- [ ] **T141 [S]** Implement the global worker error handler: catch
  exceptions from any `agent` worker, post a `Toast` notification with
  the message and a binding to open the traceback modal.
- [ ] **T142 [S]** Implement `screens/traceback_modal.py`.
- [ ] **T143 [P]** Test: `Esc` → worker state becomes `CANCELLED`
  within 200 ms (use `time.monotonic()` deltas).
- [ ] **T144 [P]** Test: a worker raises; assert a `Toast` and assert the
  app does not exit.
- [ ] **T145 [P]** Test: render coalescing — feed 100 events/s for 2 s;
  assert render count < 60 (≤ 30 fps).

## Phase 15 — Theme, Accessibility, Resize (FR-020, FR-023, FR-024)

- [ ] **T150 [P]** Implement the high-contrast theme; register via
  `App.THEMES`.
- [ ] **T151 [P]** Walk the focus order with `Tab` in a Pilot test;
  assert no widget is unreachable.
- [ ] **T152 [P]** Resize test: 200 → 40 cols → 200 cols transitions;
  assert no exception and all panels reflow.

## Phase 16 — Persistence & Crash Recovery

- [ ] **T160 [P]** Implement `~/.lyra/state/session-<id>.json` snapshot
  writer (debounced, every 5 s or every 100 events).
- [ ] **T161 [P]** On startup with a recent snapshot, render a
  `Resume previous session?` prompt with `Y`/`N`/`Esc`.

## Phase 17 — Quickstart, Docs & Release

- [ ] **T170 [P]** Write `specs/001-.../quickstart.md` (already in the
  plan §5; copy to its own file and expand with screenshots).
- [ ] **T171 [P]** Update top-level `README.md` with a "TUI" section.
- [ ] **T172 [P]** Generate a one-page key-bindings cheatsheet at
  `docs/tui-bindings.md`.
- [ ] **T173 [P]** Tag `v0.x.0`; write CHANGELOG entries; demo recording
  with `asciinema` for the README.

---

## Definition-of-Done checklist (must be ticked before tagging)

- [ ] All FR-001 through FR-024 have at least one passing test.
- [ ] `pytest-textual-snapshot` shows zero unintentional diffs.
- [ ] Long-session perf test (10-minute, 1k chunks, 20 workers) stays
  under 200 MB RSS and ≥ 30 fps on a 2020-era laptop.
- [ ] Constitution compliance checklist in the PR body has all seven
  principles ticked.
- [ ] One contributor unfamiliar with the project can complete the
  Quickstart unaided.
