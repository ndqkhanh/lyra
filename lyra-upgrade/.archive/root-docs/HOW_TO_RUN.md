# How to Run Lyra

## Quick Start

See **[QUICKSTART.md](QUICKSTART.md)** for the full setup guide.

### TL;DR

```bash
# Install
pip install -e ".[dev]"
npm install && npm run build --workspaces

# Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."

# Launch
lyra                        # Interactive REPL
lyra --continue             # Resume last session
lyra run "your task here"   # Single-shot
lyra --tui                  # TypeScript Ink TUI
lyra --help                 # All commands
```

## Entry Points

| Command | Description |
|---------|-------------|
| `lyra` | Interactive REPL (default — prompt_toolkit, Claude Code-style) |
| `lyra run <task>` | Single-shot task execution |
| `lyra plan <task>` | Plan-only mode, no execution |
| `lyra investigate <query>` | Research/investigation mode |
| `lyra --tui` | Launch TypeScript Ink terminal UI |
| `lyra doctor` | System health check |
| `lyra session list` | List all sessions |
| `lyra evals` | Run evaluation harness |

## Keyboard Reference

| Key | Action |
|-----|--------|
| `Ctrl+K` | Command palette |
| `Ctrl+D` | Exit |
| `Ctrl+L` | Clear screen |
| `Ctrl+G` | Open external editor |
| `Alt+T` | Toggle deep thinking |
| `Alt+P` | Model picker |
| `Shift+Tab` | Cycle permission mode |
| `Up/Down` | History navigation |
| `Tab` | Accept autocomplete |
| `!cmd` | Run shell command |

## Documentation

- **[README.md](README.md)** — Full project overview with architecture diagrams
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design and data flow
- **[EXAMPLES.md](EXAMPLES.md)** — Code examples for the Python API
- **[docs/](docs/)** — MkDocs documentation site
