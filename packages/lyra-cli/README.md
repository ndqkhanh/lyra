# lyra-cli

The user-facing CLI for Lyra, a self-evolving coding agent. Provides an interactive REPL (Claude-Code style) and headless commands.

**Current version: 3.14.0** | Python 3.11+ | MIT License

## Install

```bash
pip install -e packages/lyra-cli[dev]    # From repo root
# or
pipx install lyra-cli                    # Isolated environment
```

Lyra defaults to **DeepSeek**, so you only need one API key to start:

```bash
lyra connect deepseek
# Paste your API key; saved to ~/.lyra/auth.json (chmod 600)

lyra                                     # Start the interactive REPL
```

## Quick Start

```bash
lyra                                     # Open TUI (tui_v2, Textual-based)
lyra --model claude-opus-4-5             # Pin a specific model
lyra --budget 5.00                       # Cap session spend at $5.00
lyra --legacy-tui                        # Use legacy TUI (deprecated, removed in v1.0.0)
```

**Note:** As of Phase 2, `lyra` launches the new Textual-based TUI (tui_v2) by default. The legacy prompt_toolkit TUI is deprecated and accessible via `--legacy-tui` flag only.

In the REPL:

```text
agent › /help                             # List all slash commands
agent › what does session.py do?          # Ordinary chat
agent › /model                            # Show current model + slots
agent › /research "transformers"          # 10-step deep research
agent › /mode plan                        # Switch to design mode
agent › /plan implement feature X         # Create a numbered plan
agent › /approve                          # Hand off to agent for execution
agent › /exit                             # Leave the REPL
```

## Modes (4-Mode Taxonomy, v3.2.0+)

Tab cycles through modes. Prompt prefix shows active mode.

| Mode | Prompt | Reads | Writes | Tools | When to Use |
|------|--------|-------|--------|-------|------------|
| `agent` | `agent ›` | yes | yes | yes | Default: implement, refactor, execute tasks |
| `plan` | `plan ›` | yes | no | read-only | Design before coding; `/approve` hands off to agent |
| `debug` | `debug ›` | yes | yes | yes | Investigate failures; use live evidence over guesses |
| `ask` | `ask ›` | yes | no | read-only | Codebase Q&A; tutorials and explanations |

Legacy mode names (`build`, `run`, `explore`, `retro` from v3.1) still work and remap to canonical modes with a one-shot notice.

## Slash Commands (109+)

### Conversation

- `/exit`, `/quit` — Leave the REPL
- `/clear` — Wipe visible chat (history kept on disk)
- `/compact` — Heuristic chat-history compactor
- `/history`, `/replay` — List and replay past sessions

### Models & Budget

- `/model` — Show current model + fast/smart slots
- `/model list` — List every available model alias
- `/model <slug>` — Pin a specific model (one-shot or persistent)
- `/model fast=<slug>` / `/model smart=<slug>` — Re-pin the slot
- `/model auto` — Restore slot-based routing
- `/budget`, `/budget set <usd>`, `/budget save <usd>` — Manage spend cap
- `/status` — Show model, slots, mode, budget, MCP, plugins

### Working Code

- `/plan <task>` — Invoke the planner (smart slot)
- `/spawn <description>` — Fork a subagent in isolated `git worktree` (smart slot)
- `/review`, `/review --auto` — Post-turn diff review
- `/verify` — Replay the verifier (smart slot)
- `/diff`, `/diff --staged` — Show working tree diff

### Tools, Skills, Memory

- `/tools` — List registered tools (built-in + MCP + plugins)
- `/skills` — Show injected SKILL.md files
- `/memory` — Show recalled memory window
- `/mcp list|add|remove|doctor` — Manage MCP servers

### Sessions

- `/session list|show <id>|export <id>` — Local session store (FTS5)
- `/handoff` — Print paste-ready handoff message
- `/retro` — Session retrospective

### Lifecycle Commands (Waves A–G, 30+ total)

**Memory:**
- `/memory consolidate` — Merge learned patterns
- `/memory distill` — Extract key insights
- `/memory audit` — Validate stored facts
- `/memory evolve` — Auto-improve memory structure
- `/memory promote` — Mark important for fast recall

**Context:**
- `/context checkpoint` — Save execution state
- `/context prune` — Remove low-signal history
- `/context playbook` — Show decision checklist
- `/context inject` — Load external context

**Research:**
- `/research plan` — Design a research strategy
- `/research verify` — Falsify claims with evidence
- `/research falsify` — Test opposite hypothesis
- `/research sandbox` — Safe exploration
- `/deepsearch <query>` — Find code/papers

**Skills:**
- `/skills create` — Synthesize new skill
- `/skills admit` — Import external skill
- `/skills audit` — Check skill quality
- `/skills distill` — Extract from traces
- `/skills compose` — Combine skills
- `/skills merge` — Unify overlapping skills
- `/skills prune` — Remove unused skills

**Specification-Driven:**
- `/specify` — Create formal spec
- `/tasks` — Generate task breakdown
- `/bmad <role>` — Behavioral modeling

**Closed-Loop:**
- `/verify` — Run verification gate
- `/checkpoint [label]` — Save snapshot
- `/rollback [id]` — Restore to snapshot

**Routing & Monitoring:**
- `/route` — Show routing decision
- `/monitor` — Live trace viewer
- `/aer [session-id]` — View Automated Execution Representation traces

### Diagnostics

- `/doctor` — Environment health check
- `/keys` — Show registered keybinds

### Optional TDD Plugin (opt-in, off by default)

- `/tdd-gate [on|off|status]` — Toggle gate hook (`src/**` writes blocked without RED proof)
- `/red-proof <cmd>` — Run failing test and attach proof
- `/phase` — Show TDD state machine (IDLE → PLAN → RED → GREEN → REFACTOR → SHIP)

## TUI Features (Waves 1–5, all shipped)

**Wave 1: Full-Screen Model Picker**
- Press `/model` to open interactive picker with all models
- Use ←/→ to adjust effort slider (low/medium/high/xhigh/max)
- Shows live speed vs. intelligence axis
- Confirm with Enter

**Wave 2: Status Bar Footer**
- `cwd · ◆ model · mode · △ perms · N shell · bg tasks ↓ · esc to interrupt`
- Yolo mode displays `⏵⏵ bypass permissions on` in red
- Always visible, updated in real-time

**Wave 3: Background-Turn Mode**
- Press `Ctrl+B` to toggle (one-shot; auto-resets after turn)
- Non-blocking execution; continue working while turn runs
- Great for long-running operations

**Wave 4: Verbose Tool Output**
- Press `Ctrl+O` to expand tool calls
- Shows full output of tools instead of summaries
- Hint on tool calls: `ctrl+o to expand`

**Wave 5: Smart Spinner**
- Shows reasoning tokens, elapsed time, background task count
- `⠋ Thinking  ↓ 1.2k  3s  [ctrl+b: bg]`
- Tips panel in welcome banner with quick reference

## Key Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Cycle REPL modes (agent → plan → debug → ask) |
| `Alt+M` | Cycle permission levels (normal → strict → yolo) |
| `Alt+T` | Toggle extended reasoning (deep-think) |
| `Ctrl+B` | Background-turn mode (non-blocking) |
| `Ctrl+O` | Verbose tool output |
| `Ctrl+N` | New chat (preserves mode/model) |
| `Ctrl+T` | Task panel |
| `Ctrl+F` | Focus most recent subagent |
| `Esc Esc` | Rewind last turn |
| `Ctrl+X m` | Leader chord for `/mode` |

## Model Routing

Lyra uses a **2-slot system** for fast context-switching:

| Slot | Default | Usage |
|------|---------|-------|
| **fast** | `deepseek-chat` | Chat, tool calls, summaries, status |
| **smart** | `deepseek-reasoner` | Planning, spawning subagents, verification |

**Resolution Logic:**

```
chat      → fast slot
plan      → smart slot
spawn     → smart slot
review    → smart slot
verify    → smart slot
(default) → session model (universal pin)
```

**Configure Slots (persistent):**

```json
{
  "fast_model": "claude-sonnet-4-5",
  "smart_model": "claude-opus-4-5",
  "default_model": "auto"
}
```

Save in `~/.lyra/settings.json`.

**One-Shot Overrides (in REPL):**

```text
agent › /model fast=qwen-coder-flash
agent › /model smart=claude-opus-4-5
agent › /model auto                    # Back to slot-based routing
```

## Provider Catalogue (16 Providers)

Auto-cascade fallback order: DeepSeek → Anthropic → OpenAI → Gemini → xAI → Groq → Cerebras → Mistral → Qwen → OpenRouter → GitHub Copilot → AWS Bedrock → GCP Vertex → LM Studio → Ollama → OpenAI-compatible.

| Provider | Connect Command | Default Models |
|----------|-----------------|-----------------|
| DeepSeek | `lyra connect deepseek` | `deepseek-chat` / `deepseek-reasoner` |
| Anthropic | `lyra connect anthropic` | `claude-sonnet-4-5` / `claude-opus-4-5` |
| OpenAI | `lyra connect openai` | `gpt-4o-mini` / `gpt-4o` |
| Google Gemini | `lyra connect gemini` | `gemini-2.5-flash` / `gemini-2.5-pro` |
| xAI | `lyra connect xai` | `grok-4` / `grok-4-vision` |
| Groq | `lyra connect groq` | Provider defaults |
| Cerebras | `lyra connect cerebras` | Provider defaults |
| Mistral | `lyra connect mistral` | `mistral-large` |
| Qwen | `lyra connect qwen` | `qwen3-coder-flash` / `qwen3-coder-plus` |
| OpenRouter | `lyra connect openrouter` | Aggregator (any model) |
| GitHub Copilot | `lyra connect copilot` | OAuth, copilot-chat models |
| AWS Bedrock | `lyra connect bedrock` | Uses cloud SDK creds |
| GCP Vertex | `lyra connect vertex` | Uses cloud SDK creds |
| LM Studio | (auto-detect) | Your local server |
| Ollama | (auto-detect) | Your local server |
| OpenAI-compatible | `lyra connect custom` | Any OpenAI-compatible endpoint |

## Headless Commands

Every interactive feature has a headless equivalent for scripting and CI:

```bash
lyra init                         # Scaffold SOUL.md + .lyra/
lyra run "ship tests for X"       # Plan-gated end-to-end task
lyra run --no-plan "..."          # Bypass the planner
lyra plan "..."                   # Plan artifact only
lyra retro <session-id>           # Session retrospective
lyra evals --bundle golden        # Run the evals harness
lyra session list|show <id>       # Session management
lyra mcp list                     # List MCP servers
lyra acp serve                    # Host as ACP stdio server
lyra doctor                       # Health check
```

Model routing applies to headless commands: planner runs on **smart** slot, executor on **fast** slot.

## Where Things Live

```
src/lyra_cli/
    __main__.py             # Typer app + version + REPL entrypoint
    commands/               # Subcommand handlers (run, plan, connect, etc.)
    interactive/
        driver.py           # REPL loop (status bar, prompt, slash dispatch)
        session.py          # InteractiveSession dataclass + slash handlers
                            #   (fast_model/smart_model slots, /model, /spawn, ...)
        budget.py           # BudgetMeter (pricing, cap enforcement)
        cron.py             # Cron daemon (smart slot)
        mcp_autoload.py     # MCP server discovery + injection
        skills_inject.py    # SKILL.md surfacer
        memory_inject.py    # Memory recall window builder
        tool_renderers/     # Per-tool output formatters
        ...
    providers/              # LLM clients (anthropic, openai, gemini,
                            #   deepseek, qwen, ollama, copilot, bedrock, vertex, ...)
    llm_factory.py          # build_llm factory (single seam)
    channels/               # Outbound notification channels (slack, discord, ...)
```

## Testing

Run the CLI test suite:

```bash
pytest packages/lyra-cli/tests/ -v        # All tests with verbose output
pytest --cov=packages/lyra-cli/src        # With coverage
pytest packages/lyra-cli/tests/test_slash_*.py -v  # Just slash command tests
```

**Coverage:** ~1,016 tests covering every slash command, model routing, chat loop, billing, provider aliases, and headless commands.

## See Also

- [`projects/lyra/README.md`](../../README.md) — Main project intro
- [`projects/lyra/docs/ARCHITECTURE_DIAGRAMS.md`](../../docs/ARCHITECTURE_DIAGRAMS.md) — Detailed system design
- [`projects/lyra/docs/`](../../docs/) — Per-feature documentation
- [`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md) — Release history
- [`projects/lyra/CONTRIBUTING.md`](../../CONTRIBUTING.md) — Contributing guidelines
