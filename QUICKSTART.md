# Quickstart Guide

Get Lyra running in under 5 minutes.

## Prerequisites

- **Python 3.11+** with pip
- **Node.js 20+** with npm (for TUI mode only)
- **At least one LLM API key** (Anthropic, DeepSeek, OpenAI, or Google recommended)

## Installation

```bash
# Clone the repository
git clone https://github.com/lyra-ai/lyra.git
cd lyra

# Install Python dependencies (core + dev tools)
pip install -e ".[dev]"

# Install TypeScript dependencies (for the Ink terminal UI, optional)
npm install
npm run build --workspaces
```

## Configure API Keys

Set at least one provider's API key. Lyra auto-detects available providers.

```bash
# Recommended: Anthropic (best coding model)
export ANTHROPIC_API_KEY="sk-ant-..."

# DeepSeek (cost-effective reasoning)
export DEEPSEEK_API_KEY="sk-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google Gemini
export GOOGLE_API_KEY="..."

# Or use a .env file
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
echo 'DEEPSEEK_API_KEY=sk-...' >> .env
```

Lyra auto-discovers the best available provider: **DeepSeek → Anthropic → OpenAI → Gemini → xAI → Groq → Mistral → Ollama**.

## Launch Lyra

```bash
# Interactive REPL (prompt_toolkit, Claude Code-style)
lyra

# With a specific model
lyra --model deepseek-v4-pro

# Resume your last session
lyra --continue

# Single-shot task (no REPL)
lyra run "Add rate limiting to the API gateway"

# Plan-only mode (no execution)
lyra plan "Design a WebSocket notification system"

# Full CLI help
lyra --help
```

## First Session

```bash
$ lyra

  🧬 Lyra v5.0.0 — AGI Through Emergence
  Model: deepseek-v4-pro | Mode: plan | Repo: ~/projects/my-app

> Write a pytest fixture for a PostgreSQL test database

  [Plan] Analyzing request...
  [Agent] CodeAgent → Generating fixture code
  [Verify] Output validated ✓

  ```python
  import pytest
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker

  @pytest.fixture
  def pg_session():
      engine = create_engine("postgresql://localhost/test_db")
      Session = sessionmaker(bind=engine)
      session = Session()
      yield session
      session.rollback()
      session.close()
  ```

  ✅ Done | 1 turn | 234 tokens | $0.002
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+K` | Command palette |
| `Ctrl+D` | Exit session |
| `Ctrl+L` | Clear screen |
| `Ctrl+G` | Open in external editor |
| `Alt+T` | Toggle deep thinking |
| `Alt+P` | Model picker |
| `Shift+Tab` | Cycle permission mode |
| `Up/Down` | Navigate command history |
| `Tab` | Accept autocomplete |
| `!cmd` | Run shell command inline |

## Permission Modes

| Mode | Behavior |
|------|----------|
| `plan` | All tool calls require approval (default, safest) |
| `auto-edit` | File edits auto-approved; destructive ops still gated |
| `bypass` | All operations auto-approved (use with caution) |

Cycle modes with `Shift+Tab` or set in `~/.lyra/settings.json`.

## TypeScript TUI (Optional)

```bash
# Launch the React/Ink terminal UI
lyra --tui

# Or directly via npm
npm run dev --workspace=@lyra/ui-terminal
```

The TUI provides a model picker dropdown (`/model`), command palette (`Ctrl+K`), syntax-highlighted code blocks, agent tree visualization, and a token/cost status bar.

## Running Tests

```bash
# All tests
make test

# Unit tests only
make unit

# Integration tests
make integration

# With coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Specific test file
pytest tests/test_primary_agent.py -v

# TypeScript tests
npm test
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No LLM provider configured"** | Set at least one `*_API_KEY` environment variable. Check with `lyra doctor`. |
| **"Module not found: lyra_core"** | Run `pip install -e .` from the project root. |
| **npm install fails** | Ensure Node 20+. Try `npm cache clean --force` then retry. |
| **Import errors in tests** | Run `pip install -e ".[dev]"` to install pytest and coverage tools. |
| **TUI shows blank screen** | Run `npm run build --workspaces` first. Check terminal supports 256 colors. |

## Next Steps

- **[README](README.md)** — Full project overview with architecture diagrams
- **[Architecture](ARCHITECTURE.md)** — System design and data flow
- **[Examples](EXAMPLES.md)** — Code examples for common workflows
- **[Contributing](docs/CONTRIBUTING.md)** — Development setup and guidelines
