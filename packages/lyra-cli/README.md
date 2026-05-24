# lyra-cli

The user-facing CLI for Lyra — a self-evolving coding agent. Provides an interactive REPL (Claude Code-style) and headless commands for scripting and CI.

**v3.5.0** | Python 3.11+ | MIT License

## Install

```bash
pip install -e packages/lyra-cli[dev]    # From repo root
```

Lyra defaults to **DeepSeek** — set one API key to start:

```bash
export DEEPSEEK_API_KEY="sk-..."
lyra                                     # Start the interactive REPL
```

## Quick Start

```bash
lyra                                     # Interactive prompt_toolkit REPL
lyra --model deepseek-v4-pro             # Pin a specific model
lyra --budget 5.00                       # Cap session spend at $5.00
lyra --tui                               # Launch TypeScript Ink TUI (optional)
lyra --continue                          # Resume last session
```

In the REPL:

```text
> /help                                 # List all slash commands
> what does session.py do?              # Ordinary chat
> /model                                # Show current model + slots
> /research "transformers"              # 10-step deep research
> /mode plan                            # Switch to plan mode
> /plan implement feature X             # Create a numbered plan
> /exit                                 # Leave the REPL
```

## Permission Modes

Tab cycles through modes. Prompt prefix shows active mode.

| Mode | Prompt | Reads | Writes | Tools | When to Use |
|------|--------|-------|--------|-------|-------------|
| `plan` | `plan ›` | yes | no | read-only | Design before coding; approve to hand off |
| `auto-edit` | `build ›` | yes | yes | gated | Default: implement, refactor, execute |
| `bypass` | `run ›` | yes | yes | all | Trusted automation (use with caution) |

## Slash Commands

### Conversation
- `/exit`, `/quit` — Leave the REPL
- `/clear` — Wipe visible chat (history kept on disk)
- `/compact` — Compress chat history
- `/history`, `/replay` — List and replay past sessions

### Models & Budget
- `/model` — Show current model + fast/smart slots
- `/model list` — List every available model alias
- `/model <slug>` — Pin a specific model
- `/model fast=<slug>` / `/model smart=<slug>` — Re-pin a slot
- `/model auto` — Restore slot-based routing
- `/budget`, `/budget set <usd>` — Manage spend cap
- `/status` — Show model, slots, mode, budget, MCP, plugins

### Working Code
- `/plan <task>` — Invoke the planner (smart slot)
- `/spawn <description>` — Fork a subagent in isolated git worktree
- `/review` — Post-turn diff review
- `/verify` — Replay the verifier
- `/diff` — Show working tree diff

### Tools, Skills, Memory
- `/tools` — List registered tools (built-in + MCP)
- `/skills` — Show injected SKILL.md files
- `/memory` — Show recalled memory window
- `/mcp list|add|remove|doctor` — Manage MCP servers

### Sessions
- `/session list|show <id>|export <id>` — Local session store
- `/handoff` — Print paste-ready handoff message
- `/retro` — Session retrospective

### Memory Lifecycle
- `/memory consolidate` — Merge learned patterns
- `/memory distill` — Extract key insights
- `/memory audit` — Validate stored facts
- `/memory promote` — Mark important for fast recall

### Research
- `/research plan` — Design research strategy
- `/research verify` — Falsify claims with evidence
- `/deepsearch <query>` — Find code/papers

### Skills
- `/skills create` — Synthesize new skill
- `/skills admit` — Import external skill
- `/skills audit` — Check skill quality
- `/skills prune` — Remove unused skills

### TDD Plugin (opt-in)
- `/tdd-gate [on|off|status]` — Toggle gate hook
- `/red-proof <cmd>` — Run failing test and attach proof
- `/phase` — Show TDD state (IDLE → PLAN → RED → GREEN → REFACTOR → SHIP)

### Diagnostics
- `/doctor` — Environment health check
- `/keys` — Show registered keybinds

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Cycle REPL modes (plan → build → run) |
| `Alt+T` | Toggle deep thinking |
| `Alt+P` | Model picker |
| `Ctrl+K` | Command palette |
| `Ctrl+B` | Background-turn mode |
| `Ctrl+O` | Verbose tool output |
| `Ctrl+L` | Clear screen |
| `Ctrl+G` | Open in editor |
| `Esc Esc` | Rewind last turn |
| `!cmd` | Run shell command |

## Model Routing

Lyra uses a **2-slot system** for fast context-switching:

| Slot | Default | Usage |
|------|---------|-------|
| **fast** | `deepseek-v4-flash` | Chat, tool calls, summaries, status |
| **smart** | `deepseek-v4-pro` | Planning, spawning subagents, verification |

**Resolution Logic:**

```
chat      → fast slot
plan      → smart slot
spawn     → smart slot
review    → smart slot
verify    → smart slot
(default) → session model (universal pin)
```

Configure slots in `~/.lyra/settings.json`:

```json
{
  "fast_model": "deepseek-v4-flash",
  "smart_model": "deepseek-v4-pro",
  "default_model": "auto"
}
```

## Provider Catalogue (16 Providers)

Auto-cascade fallback: DeepSeek → Anthropic → OpenAI → Gemini → xAI → Groq → Cerebras → Mistral → Qwen → OpenRouter → Bedrock → Vertex → LM Studio → Ollama.

| Provider | Env Var | Default Models |
|----------|---------|---------------|
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` / `deepseek-reasoner` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` / `claude-opus-4-7` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` / `o3-mini` |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.5-flash` / `gemini-2.5-pro` |
| xAI | `XAI_API_KEY` | `grok-4` |
| Groq | `GROQ_API_KEY` | Provider defaults |
| Mistral | `MISTRAL_API_KEY` | `mistral-large` |
| Qwen | `QWEN_API_KEY` | `qwen3-coder-flash` / `qwen3-coder-plus` |
| Bedrock | AWS SDK creds | Claude via AWS |
| Ollama | (auto-detect) | Local models |

## Headless Commands

```bash
lyra init                         # Scaffold SOUL.md + .lyra/
lyra run "ship tests for X"       # Plan-gated end-to-end task
lyra run --no-plan "..."          # Bypass the planner
lyra plan "..."                   # Plan artifact only
lyra investigate "..."            # Research mode
lyra retro <session-id>           # Session retrospective
lyra evals --bundle golden        # Run the evals harness
lyra session list|show <id>       # Session management
lyra mcp list                     # List MCP servers
lyra doctor                       # Health check
lyra evolve                       # Run prompt evolution
```

## Package Layout

```
src/lyra_cli/
    __main__.py             # Typer app entrypoint
    commands/               # Subcommand handlers (run, plan, evals, evolve...)
    interactive/
        driver.py           # REPL loop (status bar, prompt, slash dispatch)
        session.py          # InteractiveSession + fast/smart model slots
        budget.py           # BudgetMeter (pricing, cap enforcement)
        keybindings.py      # Keyboard shortcut registry
    providers/              # LLM clients (anthropic, openai, gemini, deepseek...)
    llm_factory.py          # build_llm factory
    memory/                 # 8-level hierarchical memory
    skills/                 # 20+ skill categories
```

## Testing

```bash
pytest packages/lyra-cli/tests/ -v
pytest --cov=packages/lyra-cli/src
```

## See Also

- [Main README](../../README.md) — Full project overview
- [Architecture](../../ARCHITECTURE.md) — System design
- [Examples](../../EXAMPLES.md) — Python API examples
