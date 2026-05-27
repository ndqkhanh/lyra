# UI-Refs Fusion — v1.7.2 "Integrity + Fusion" spec

> **Status**: active, 2026-04-24.
> **Parent audit**: `lyra-ui-refs-verification.canvas.tsx`.
> **Scope**: Close every gap identified between Lyra and the three
> reference stacks (`claw-code`, `opencode`, `hermes-agent`) either as
> a shipped feature or as a scaffold + failing contract test. The spec
> is intentionally decomposed into 4 phases so each can be spec-reviewed,
> RED-proved, and GREEN-shipped independently without holding the
> others hostage.

Lyra's TDD discipline (RED → GREEN → REFACTOR → SHIP) applies *per item*.
No feature in this spec lands without a failing test that captures the
contract first.

---

## Phase A — `docs/feature-parity.md` integrity patch

Zero code churn. Fixes factual errors the audit found:

| id  | edit                                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------------------ |
| A1  | `MCP server` row in §2.10: `HA —` → `HA ✓` (hermes ships `hermes mcp serve`).                                             |
| A2  | §1.3 "Session management" / "Config & theme": annotate HA slash renames (`/compact→/compress`, `/cost→/usage`, `/stats→/insights`, `/theme→/skin`). |
| A3  | §2.2 "Subagents": annotate HA preset rename (`Explore`/`General` → `leaf`/`orchestrator`).                                 |
| A4  | §2.6 "Hooks": header-note that OC uses `chat.message` / `tool.execute.before` / `tool.execute.after`, not Claude-Code names. |
| A5  | §2.2 "Worktree isolation": downgrade `OC ✓` → `OC partial` (not wired into OC's Task subagent).                           |
| A6  | §1.3: `/keybindings`, `/cost`, `/context`, `/spawn`, `/tools` are OC dialogs / commands but not `/` slashes — mark `dialog` not `✓`. |

## Phase B — v1 "NOW" code items (RED-first, full GREEN)

Hard-scoped, each a self-contained contract + impl:

| id  | item                             | RED test                                                            |
| --- | -------------------------------- | ------------------------------------------------------------------- |
| B1  | `post_tool_call` hook in AgentLoop | new test in `test_agent_loop_contract.py` — asserts hook fires after every tool dispatch with the tool's return value. |
| B2  | Slash alias layer (`/compact→/compress`, etc.) | new test `test_slash_alias_resolution.py` — asserts hermes-muscle-memory aliases resolve to canonical commands. |
| B3  | `@file` mention completer        | new test `test_at_file_completer.py` — `@src/` suggests file entries. |
| B4  | Multi-line input keybinds (`\\`+Enter, Alt+Enter, Ctrl+J) | new test `test_multiline_keybind.py` — shift buffer extends on trailing `\\`. |
| B5  | External-editor `Ctrl+G`         | new test `test_ctrl_g_edits_with_editor.py` — invokes `$EDITOR` on a temp file, replaces buffer. |
| B6  | `/keybindings` slash             | new test `test_keybindings_slash.py` — prints current chord table. |

## Phase C — v1 / v1.5 roadmap medium features (RED + interface contract + stub impl)

Each feature gets:
1. Module scaffolded at canonical path.
2. Failing contract test (plain, not xfail — we explicitly want RED at CI time so the next wave shows GREEN).
3. Stub implementation that *runs* (imports cleanly, raises `NotImplementedError` on the unshipped paths) so downstream wiring can be done incrementally.

| id  | item                                       | module                                                        |
| --- | ------------------------------------------ | ------------------------------------------------------------- |
| C1  | LSP tool (opencode parity)                 | `lyra_core.tools.lsp`                                         |
| C2  | Git-worktree subagent isolation            | `lyra_core.worktree`                                          |
| C3  | `codesearch` + `apply_patch` tools         | `lyra_core.tools.codesearch`, `lyra_core.tools.apply_patch`   |
| C4  | `/cron` scheduled automations (hermes)     | `lyra_core.scheduler`                                         |

## Phase D — v1.5 / v1.7 / v2 subsystems (RED + interface contract only)

Large-surface work that doesn't fit in a single session. Each ships as:
- A package or subpackage with clean `__init__.py` + README note.
- An interface (`typing.Protocol` or `abc.ABC`) defining the contract.
- At least one failing test that locks the shape.

| id  | item                                                | target                                                      |
| --- | --------------------------------------------------- | ----------------------------------------------------------- |
| D1  | ACP protocol bridge                                 | `packages/lyra-acp/`                                        |
| D2  | Multi-channel gateway (Telegram/Discord/Slack)      | `packages/lyra-gateway/`                                    |
| D3  | Plugin manifest system                              | `packages/lyra-plugins/`                                    |
| D4  | Multi-backend terminal (Docker/Modal/SSH/Daytona/Singularity) | `lyra_core.runtime.backends`                    |
| D5  | Mock-LLM parity harness                             | `lyra_evals.mock_llm`                                       |
| D6  | RL/Atropos trajectory tooling                       | `lyra_core.trajectory`                                      |
| D7  | `NotebookEdit` + PDF auto-extract                   | `lyra_core.tools.notebook_edit`, `lyra_core.tools.pdf_extract` |

## Non-goals

- No changes to existing GREEN tests — only new tests.
- No mass rename / refactor of existing modules.
- No changes to the v1.8 Phase 2/3 work already Unreleased at the top of the changelog.
- No visual/UX redesign — we land functionality and parity notes only.

## Release shape

All Phase A + B + C + D work rolls into `v1.7.2 "Integrity + Fusion"`.
A new Unreleased section in `CHANGELOG.md` documents the boundary.
Phases A and B are fully GREEN; C ships GREEN stubs with working tests;
D ships scaffolds with failing tests that light up the next wave.
