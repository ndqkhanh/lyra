# lyra-cli

The user-facing front-end for **Lyra**, the general-purpose
CLI-native coding agent. `lyra-cli` ships:

* a Typer-based command surface (`lyra init`, `run`, `plan`,
  `connect`, `doctor`, `retro`, `evals`, `session`, `mcp`, `acp`);
* a Claude-Code-style interactive REPL when invoked with no
  subcommand (`lyra` → status banner → slash commands);
* the **provider catalogue** (DeepSeek, Anthropic, OpenAI, Gemini,
  xAI, Groq, Cerebras, Mistral, Qwen, OpenRouter, GitHub Copilot, AWS
  Bedrock, GCP Vertex, LM Studio, Ollama, OpenAI-compatible) wired
  through a single `build_llm` factory that the rest of the harness
  (subagent runner, cron daemon, planner, evaluator) reuses;
* an **opt-in TDD plugin** (`/tdd-gate on`, `/phase`, `/red-proof`)
  for teams that want a hard gate around `src/**` writes — off by
  default in v3.0.0 to match `claw-code`, `opencode`, and
  `hermes-agent`.

Everything below is current as of **v3.2.0** (2026-04-27 —
Claude-Code 4-mode taxonomy + screenshot-bug fix + docs sweep).
v3.2.0 supersedes v3.1.0 (Phase J research synthesis) and v3.0.0
(TDD opt-in repositioning + DeepSeek small/smart split). For the
per-release narrative see
[`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md).

## Install

The CLI is published as a stand-alone Python package; the only hard
requirement is Python ≥ 3.11.

```bash
pipx install lyra-cli            # recommended (isolated venv on PATH)
# or
pip install --user lyra-cli      # plain user install

lyra --version                   # → lyra 3.2.0
```

The shipping binary uses **DeepSeek** by default so a single API key
is enough to drive every role (chat, planning, subagents). Configure
it once and persist it:

```bash
lyra connect deepseek
# Paste sk-… ; auth.json is written to ~/.lyra/auth.json (chmod 600).
```

`lyra connect` understands every provider in the catalogue (run
`lyra connect --help` for the list) and validates the key against the
provider's `/models` endpoint before saving so a typo fails fast
instead of mid-turn.

## Quick start

```bash
lyra                       # opens the interactive REPL in $PWD
lyra --repo-root path/to/checkout  # pin a different repo
lyra --model claude-opus-4-5       # pin the *universal* model
lyra --budget 5.00         # cap this session at USD 5.00
```

In the REPL (default mode is `agent` since v3.2.0):

```text
agent › /help                 # list every slash command
agent › /status               # model + slot + budget + tools
agent › what does session.py do?     # ordinary chat turn
agent › /mode plan                   # switch to read-only design mode
plan  › /plan ship tests for X       # propose a numbered plan
plan  › /approve                     # hand off to agent for execution
agent › /spawn refactor migrations   # subagent in an isolated worktree
agent › /budget set 10               # one-shot cap raise
agent › /exit
```

Non-TTY environments (CI, piped stdin) fall back automatically to
plain `input()` and strip ANSI; `echo /exit | lyra` works.

## Model routing — fast vs. smart

v2.7.1 introduces a Claude-Code-style **two-tier model split** on top
of DeepSeek's catalog (cheapest competitive frontier API). The
session carries two slots, both re-pinnable per session:

| Slot      | Default alias       | Resolves to            | Used by |
|-----------|---------------------|------------------------|---------|
| **fast**  | `deepseek-v4-flash` | `deepseek-chat`        | chat turns, tool calls, summaries, `/compact`, status helpers |
| **smart** | `deepseek-v4-pro`   | `deepseek-reasoner`    | `lyra plan`, `/spawn` subagents, cron fan-out, `/review --auto`, evaluator |

Resolution is performed by a single helper,
`_resolve_model_for_role(session, role)`, with this mapping:

```
chat      → fast
plan      → smart
spawn     → smart
cron      → smart
review    → smart
verify    → smart
subagent  → smart
(unknown) → session.model      # legacy "auto" pin escape hatch
```

When a role resolves a different alias than the cached provider's
`model` attribute, Lyra **mutates the cached provider in place**
(setting `provider.model = "<resolved-slug>"`) and stamps both
`HARNESS_LLM_MODEL` (the universal env the `build_llm` factory reads)
and the provider-specific override (`DEEPSEEK_MODEL`,
`ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`) so a freshly built
provider lands on the same slug. The chat history, the budget meter,
and the in-memory MCP plumbing all stay attached — only the next
`generate` / `stream` call talks to a different model.

### `/model` cheatsheet

```text
agent › /model
current model: auto (resolves through fast/smart slots)
fast slot:     deepseek-v4-flash  →  deepseek-chat
smart slot:    deepseek-v4-pro    →  deepseek-reasoner

agent › /model list                       # show every alias the registry knows
agent › /model fast                       # next turn → fast slot (one-shot)
agent › /model smart                      # next turn → smart slot (one-shot)
agent › /model fast=qwen-coder-flash      # re-pin the fast slot persistently
agent › /model smart=claude-opus-4-5      # re-pin the smart slot persistently
agent › /model claude-sonnet-4-5          # legacy: pin the universal model
                                           # (overrides the slots until /model auto)
agent › /model auto                       # restore slot-based routing
```

To re-pin the slots **across sessions**, drop them into
`~/.lyra/settings.json`:

```json
{
  "fast_model": "claude-sonnet-4-5",
  "smart_model": "claude-opus-4-5",
  "default_model": "auto",
  "budget_cap_usd": 5.00
}
```

API keys are stored separately in `~/.lyra/auth.json` (created by
`lyra connect`, `chmod 600` enforced).

## Provider catalogue

The factory honours a fixed precedence when `--model auto` is in
effect: **DeepSeek → Anthropic → OpenAI → Gemini → xAI → Groq →
Cerebras → Mistral → Qwen → OpenRouter → LM Studio → Ollama → mock**.
The first one with valid credentials wins; you can pin any of them
explicitly with `--model <name>` or `/model <slug>` inside the REPL.

| Provider                         | Connect command            | Default models (fast / smart)            |
|----------------------------------|----------------------------|------------------------------------------|
| DeepSeek (default)               | `lyra connect deepseek`    | `deepseek-chat` / `deepseek-reasoner`    |
| Anthropic                        | `lyra connect anthropic`   | `claude-sonnet-4-5` / `claude-opus-4-5`  |
| OpenAI                           | `lyra connect openai`      | `gpt-4o-mini` / `gpt-4o`                 |
| Google Gemini                    | `lyra connect gemini`      | `gemini-2.5-flash` / `gemini-2.5-pro`    |
| xAI / Groq / Cerebras / Mistral  | `lyra connect <name>`      | provider-published defaults              |
| Qwen / OpenRouter                | `lyra connect <name>`      | `qwen3-coder-flash` / `qwen3-coder-plus` |
| GitHub Copilot                   | `lyra connect copilot`     | OAuth, copilot-chat models               |
| AWS Bedrock / GCP Vertex         | `lyra connect <name>`      | uses cloud SDK creds                     |
| Ollama / LM Studio               | (auto-detect)              | whatever your local server exposes       |

## Modes (v3.2.0)

Lyra mirrors Claude Code's 4-mode REPL taxonomy. The active mode
appears in the prompt prefix (`agent ›`, `plan ›`, `debug ›`, `ask ›`)
and in the status bar's `mode` chip. Tab cycles forward through the
list.

| Mode    | Prompt prefix | Reads files | Writes files | Calls tools | Use when                                                 |
| ------- | ------------- | ----------- | ------------ | ----------- | -------------------------------------------------------- |
| `agent` | `agent ›`     | yes         | yes          | yes         | Default. Implementing, refactoring, executing tasks.     |
| `plan`  | `plan ›`      | yes         | no           | no (read)   | Designing before coding; `/approve` ships to `agent`.    |
| `debug` | `debug ›`     | yes         | yes          | yes         | Investigating a failure; runtime evidence over guesses.  |
| `ask`   | `ask ›`       | yes         | no           | no (read)   | Codebase Q&A; tutorial / explanation requests.           |

Switch modes with `/mode <name>` or by hitting **Tab**. Legacy v3.1
names (`build`, `run`, `explore`, `retro`) are still accepted —
they remap to the canonical mode and emit a one-shot
`'<old>' was renamed to '<new>' in v3.2.0` notice. The legacy →
canonical map:

| v3.1 (legacy) | v3.2 (canonical) |
| ------------- | ---------------- |
| `build`       | `agent`          |
| `run`         | `agent`          |
| `explore`     | `ask`            |
| `retro`       | `debug`          |

> **Why four?** v3.2.0 collapsed Lyra's older 5-mode taxonomy onto
> the same surface as `claw-code` / `opencode` / `hermes-agent`.
> The system prompts now ENUMERATE the four modes verbatim and
> explicitly disclaim that TDD's RED → GREEN → REFACTOR phases are
> a plugin's internal phases, **not modes** — fixing a bug where
> the model would list `BUILD / RED / GREEN / REFACTOR` as four
> peer modes when asked. See
> [`CHANGELOG.md`](../../CHANGELOG.md#v320--2026-04-27--claude-code-4-mode-taxonomy).

## Slash command surface (v3.2.0)

This is the canonical list as of v3.2.0. `/help` always wins if this
README drifts.

### Conversation

* `/exit`, `/quit`              — leave the REPL.
* `/clear`                      — wipe the visible chat (history kept on disk).
* `/compact`                    — heuristic chat-history compactor (keeps the last 6 turns verbatim, collapses the rest into a digest, recomputes `tokens_used`).
* `/history` / `/replay`        — list and replay past sessions.

### Models, budget, status

* `/model`                       — show current model + fast/smart slots.
* `/model list`                  — list every alias the registry knows.
* `/model <slug>`                — pin the universal model.
* `/model fast` / `/model smart` — one-shot switch the next turn to that slot.
* `/model fast=<slug>` / `/model smart=<slug>` — re-pin the slot persistently.
* `/model auto`                  — restore slot-based routing.
* `/budget`, `/budget set <usd>`, `/budget save <usd>` — inspect / raise the cap.
* `/status`                      — model, slots, mode, budget, MCP, plugins.

### Working code

* `/plan <task>`                 — invoke the planner (smart slot).
* `/spawn <description>`         — fork a subagent in an isolated `git worktree` (smart slot).
* `/review`, `/review --auto`    — post-turn diff review.
* `/verify`                      — replay the verifier (smart slot).
* `/diff`, `/diff --staged`      — show the working tree diff.

### Tools, skills, memory

* `/tools`                       — list registered tools (built-in + MCP + plugins).
* `/skills`                      — show injected SKILL.md files.
* `/memory`                      — show the recalled memory window.
* `/mcp list|add|remove|doctor`  — manage MCP servers.

### Sessions

* `/session list|show <id>|export <id>` — local session store (FTS5 by default).
* `/handoff`                     — print a paste-ready handoff message.
* `/retro`                       — session retrospective.

### Diagnostics

* `/doctor`                      — environment health check.
* `/keys`                        — show registered keybinds.

### Optional TDD plugin (v3.0.0+ opt-in)

* `/tdd-gate [on|off|status]`    — toggle the gate hook (`src/**`
  writes blocked without a passing RED proof). Off by default; flip
  it on per-session, or persist via `/config set tdd_gate=on`.
* `/red-proof <cmd>`             — run a test command and attach its
  failing output as a `RedProof` to the session.
* `/phase`                       — surface the TDD state machine
  (`IDLE → PLAN → RED → GREEN → REFACTOR → SHIP`).
* `/review` and `/ultrareview`   — when the gate is on, the
  reviewer voices include "TDD discipline"; when off they fall back
  to a generic "test coverage" rubric so the verifier doesn't
  punish sessions that opt out of TDD.

## Headless commands

Every interactive feature also exists as a headless subcommand for
scripting and CI:

```bash
lyra init                         # scaffold SOUL.md + .lyra/
lyra run "ship tests for X"       # plan-gated end-to-end task
lyra run --no-plan "..."          # bypass the planner (for trusted scripts)
lyra plan "..."                   # plan artifact only, no execution
lyra retro <session-id>           # session retrospective
lyra evals --bundle golden        # run the evals harness
lyra session list
lyra session show <id>
lyra mcp list                     # manage MCP servers (and validate config)
lyra acp serve                    # host Lyra as an ACP stdio server
lyra doctor                       # health check
```

`lyra run` honours `--llm` / `--model`, `--budget`, and `--repo-root`
the same way the interactive entry point does, and it routes the
planner stage through the **smart** slot and the executor stage
through the **fast** slot — same role-driven router as the REPL.

## Where things live

```
src/lyra_cli/
    __main__.py             # Typer app + version flag + interactive entrypoint
    commands/               # subcommand handlers (run, plan, connect, doctor, retro, evals, mcp, acp, session, init)
    interactive/
        driver.py           # REPL loop wiring (status bar, prompt, slash dispatch)
        session.py          # InteractiveSession dataclass + slash command handlers
                            #   incl. fast_model / smart_model slots, /model, /spawn, ...
        budget.py           # BudgetMeter (per-turn pricing, cap enforcement)
        cron.py             # cron daemon (smart slot)
        mcp_autoload.py     # MCP server discovery + injection
        skills_inject.py    # SKILL.md surfacer
        memory_inject.py    # recall window builder
        tool_renderers/     # human-readable per-tool output formatters
        ...
    providers/              # per-backend LLM clients (anthropic, openai, gemini,
                            #   deepseek, qwen, ollama, copilot, bedrock, vertex, ...)
    llm_factory.py          # build_llm — single seam every consumer routes through
    channels/               # outbound notification channels (slack, discord, ...)
```

## Testing

```bash
# from projects/lyra/packages/lyra-cli/
uv run pytest -q             # 1016 tests in v3.0.0 (2 sandbox-skipped)
```

The CLI's tests cover every slash command (`test_slash_*.py`), the
fast/smart routing layer (`test_model_slot_routing.py`), the chat
loop and billing (`test_chat_mode_handlers.py`), the alias registry
contract (`test_providers_aliases.py`), and the headless commands
(`test_run_command.py`, `test_plan_command.py`, …).

## See also

* [`projects/lyra/README.md`](../../README.md) — top-level intro.
* [`projects/lyra/docs/architecture.md`](../../docs/architecture.md) — invariants + topology.
* [`projects/lyra/docs/blocks/`](../../docs/blocks/) — per-feature design docs.
* [`projects/lyra/docs/feature-parity.md`](../../docs/feature-parity.md) — claw-code / opencode / hermes-agent ↔ Lyra parity matrix.
* [`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md) — release log.
