<!--
Sync Impact Report
==================
Version change: — → 1.0.0
Modified principles: (initial constitution — all principles new)
Added sections:
  - Core Principles (I–VII)
  - Operational Constraints
  - Quality Gates
  - Governance
Removed sections: none
Templates requiring update:
  - .specify/templates/plan-template.md → ✅ aligned (constitution-check section maps to Principles I–VII)
  - .specify/templates/spec-template.md → ✅ aligned (no mandatory section added/removed beyond defaults)
  - .specify/templates/tasks-template.md → ✅ aligned (category headings cover Observability, Testing, UX)
Follow-up TODOs: none
-->

# Lyra TUI Constitution

The Lyra TUI is the visible surface of an AI coding agent. Whatever the agent
does internally — spawning sub-agents, compressing context, switching models,
running shell tools — the user only believes what they can **see**. The
principles below exist to make sure the TUI never lies about state, never
blocks the user, and always shows the receipts on demand.

## Core Principles

### I. Truth Over Aesthetics (NON-NEGOTIABLE)
Every visible status string maps to a real, observable runtime state. Spinners
only spin while real work is happening. Token counts and timings are reported
from the actual subprocess that did the work, not estimated client-side.
Sub-agent labels match the sub-agent name in the orchestrator. If the agent
fails silently, the TUI must surface that — silent success states are
forbidden.

### II. Non-Blocking by Default (NON-NEGOTIABLE)
The event loop is sacred. No network call, no LLM call, no subprocess wait,
and no file I/O above ~5 ms may run on the main thread. All such work runs in
a Textual `Worker` (`@work` decorator) with explicit `exclusive`, `group`, and
`thread` parameters. Worker exceptions are caught and surfaced — never
swallowed. Cancellation via `Esc` must propagate to running workers within
200 ms.

### III. Progressive Disclosure
Default views are dense and scannable. Detail is one keystroke away.
Compaction summaries, tool output, agent traces, and model selectors all
support an expand/collapse affordance (`Ctrl+O` for inline output, `Enter` on
a tree row, `Ctrl+P` for the command palette). The user should never have to
scroll back to learn what just happened — recent activity stays visible until
explicitly dismissed.

### IV. Streaming as a First-Class Citizen
LLM responses, tool output, and sub-agent progress all stream. The TUI never
buffers a full response before rendering. Markdown is rendered incrementally
via `Markdown.get_stream()`; logs append via `RichLog.write()`; data tables
update row-by-row. Render coalescing is permitted (and encouraged) above
~20 updates/sec, but a slow update path is never an excuse to hide partial
state.

### V. Keyboard-First, Mouse-Acceptable
Every action reachable by mouse is also reachable by keyboard with a binding
visible in the footer. The slash-command picker (`/model`, `/agents`, etc.),
the agent tree, the expand toggle, and the background-task switcher all have
discoverable bindings. Mouse support is a convenience layer, never a
prerequisite.

### VI. Single Source of Truth for State
There is exactly one in-memory representation of agent state (the
`SessionState` reactive object). Widgets subscribe via Textual reactives and
`watch_*` handlers; they do not poll, and they do not own duplicate copies of
state. Background workers mutate state via `call_from_thread` or by posting
typed `Message` objects — never by touching widgets directly.

### VII. Observability Over Opacity
Every screen and every long-running worker emits structured log lines to the
Textual dev console (`textual console`) and to a rotating file log under
`~/.lyra/logs/`. Log entries include `session_id`, `agent_id`, `worker_id`,
`event_type`, and timing. Bug reports must be reproducible from logs alone.

## Operational Constraints

- **Python ≥ 3.11.** Required for `asyncio.TaskGroup` and `Self` typing.
- **Textual ≥ 0.86.** Required for `MarkdownStream`, modern `Worker` API,
  and stable command-palette bindings.
- **Rich ≥ 13.7.** Required for live-streaming syntax highlighting.
- **No browser dependency.** The TUI runs in any VT100-compatible terminal.
  `textual serve` is supported as a convenience but is never a requirement.
- **CSS lives in `.tcss` files** colocated with the screen/widget that owns
  it. No inline `DEFAULT_CSS` strings longer than five rules.
- **One screen = one file** under `src/lyra_cli/tui/screens/`. One reusable
  widget = one file under `src/lyra_cli/tui/widgets/`.

## Quality Gates

A change is mergeable only if it satisfies all of:

1. **Test coverage.** New widgets ship with snapshot tests
   (`pytest-textual-snapshot`) plus at least one async interaction test
   (`Pilot.press`, `Pilot.click`).
2. **Accessibility.** The screen passes the high-contrast theme without
   color-only information. Footer bindings render. Focus order is
   walkable with `Tab` / `Shift+Tab`.
3. **Performance.** A 10-minute synthetic session (1k streaming chunks,
   20 background workers, 200 tool-call panels) maintains ≥ 30 fps on a
   2020-era laptop and stays under 200 MB RSS.
4. **Constitution check.** The plan's "Constitution Check" section in
   `plan.md` confirms compliance with Principles I–VII, with any
   exceptions written down in the Complexity Tracking table.

## Governance

This constitution supersedes ad-hoc design choices, individual maintainer
preferences, and screenshots from other tools (including Claude Code). The
principles are the *rules*; Claude Code is merely a *reference
implementation* of similar rules.

Amendments require:

- A pull request that updates this file with a Sync Impact Report comment at
  the top.
- A bump to the version below using semver: MAJOR for principle removals or
  incompatible changes, MINOR for new principles or sections, PATCH for
  wording fixes.
- A confirmation in the PR description that
  `.specify/templates/plan-template.md`, `.specify/templates/spec-template.md`,
  and `.specify/templates/tasks-template.md` remain aligned (or are updated
  in the same PR).

All PRs that touch `src/lyra_cli/tui/` must include a "Constitution
compliance" checklist with one box per principle.

**Version**: 1.0.0 | **Ratified**: 2026-05-17 | **Last Amended**: 2026-05-17
