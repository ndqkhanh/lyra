# Lyra

A self-evolving CLI-native coding agent that learns from every session and routes across 16 LLM providers.

[![Tests](https://img.shields.io/badge/tests-289%20E2E%20%7C%2099.3%25%20pass-brightgreen)](https://github.com/ndqkhanh/lyra)
[![Version](https://img.shields.io/badge/version-3.14.0-orange)](https://github.com/ndqkhanh/lyra)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Why Lyra

- **Production-ready with 99.3% test coverage** — [289 comprehensive E2E tests](LYRA_E2E_FINAL_REPORT.md) validating all core systems
- **Self-improving agent** — Automatically extracts reusable skills and strategies from execution traces
- **Smart model routing** — 3-tier system (fast/reasoning/advisor) with 16 providers; automatic fallback
- **Deep research capabilities** — 10-step pipeline with academic paper discovery and synthesis
- **Strategic roadmap** — [6-phase optimization plan](LYRA_OPTIMIZATION_PLAN.md) for enterprise-grade AI harness architecture

## Quick Start

Install and run in under 5 minutes:

```bash
# Clone and install
git clone https://github.com/ndqkhanh/lyra.git
cd lyra
pip install -e packages/lyra-cli[dev]

# Store an API key (DeepSeek, Anthropic, OpenAI, Gemini, etc.)
lyra connect deepseek
# Paste your API key; it's saved to ~/.lyra/auth.json (chmod 600)

# Start the interactive REPL
lyra

# In the REPL
agent › /help                              # List all slash commands
agent › what does this function do?        # Ordinary chat
agent › /model list                        # See all available models
agent › /research "your topic here"        # 10-step deep research
agent › /mode plan                         # Switch to design mode
agent › /exit
```

## Architecture

Lyra is an 8-package monorepo:

| Package | Role |
|---------|------|
| **lyra-cli** | Interactive REPL + headless CLI (Typer + Rich + prompt_toolkit) |
| **lyra-core** | Agent kernel: loop, hooks, tools, context, HIR |
| **lyra-skills** | SKILL.md loader, router, extractor, lifecycle |
| **lyra-research** | 10-step deep research pipeline |
| **lyra-evolution** | Self-evolution: Ctx2Skill, Voyager, Reflexion |
| **lyra-memory** | Long-term memory: codebase graph + FTS5 |
| **lyra-evals** | Eval harness: AER traces, SLO tracking |
| **lyra-mcp** | MCP client + server adapters |

## Key Features

**109+ Slash Commands**

Organized by function: conversation, models/budget, working code, lifecycle, tools/skills/memory, sessions, and diagnostics.

```bash
agent › /model fast=deepseek-chat             # Switch models in one turn
agent › /spawn refactor auth module           # Fork a subagent in git worktree
agent › /research "transformers attention"    # Deep research with citations
agent › /memory consolidate                   # Extract long-term learnings
agent › /checkpoint save                      # Save execution state
agent › /mode plan                            # Read-only design mode
agent › /verify                               # Run post-turn verification
agent › /aer session-123                      # View execution traces
```

**TUI Features (Waves 1–5)**

- Wave 1: Full-screen model picker with effort slider (low/medium/high/xhigh/max)
- Wave 2: Status bar footer showing model, mode, permissions, shell, and background tasks
- Wave 3: `Ctrl+B` background-turn mode (non-blocking execution)
- Wave 4: `Ctrl+O` verbose tool output toggle
- Wave 5: Smart spinner with reasoning tokens, elapsed time, and live tips

**4 REPL Modes** (Tab to cycle)

| Mode | Prompt | Reads | Writes | Calls Tools | Use Case |
|------|--------|-------|--------|-------------|----------|
| `agent` | `agent ›` | yes | yes | yes | Default; implement, refactor, execute |
| `plan` | `plan ›` | yes | no | read-only | Design before coding; `/approve` to execute |
| `debug` | `debug ›` | yes | yes | yes | Investigate failures with live evidence |
| `ask` | `ask ›` | yes | no | read-only | Codebase Q&A and tutorials |

**Lifecycle Commands (30+)**

Memory, context, research, skills, specification-driven, closed-loop, and routing:

- `/memory consolidate|distill|audit|evolve|promote`
- `/context checkpoint|prune|playbook|inject`
- `/research plan|verify|falsify|sandbox` + `/deepsearch <query>`
- `/skills create|admit|audit|distill|compose|merge|prune`
- `/specify`, `/tasks`, `/bmad <role>`
- `/verify`, `/checkpoint [label]`, `/rollback [id]`
- `/route`, `/monitor`, `/aer [session-id]`

**16 LLM Providers**

| Provider | Models |
|----------|--------|
| DeepSeek | chat, reasoner |
| Anthropic | Claude Opus, Sonnet, Haiku |
| OpenAI | GPT-5, GPT-4o, o1 |
| Gemini | 2.5 Pro, Flash |
| xAI | Grok-4 |
| Groq, Cerebras, Mistral, Qwen | Various |
| OpenRouter | Aggregator |
| GitHub Copilot | Copilot Chat models |
| AWS Bedrock, GCP Vertex | Cloud native |
| LM Studio, Ollama | Local |
| OpenAI-compatible | Custom endpoints |

**Key Keybindings**

| Key | Action |
|-----|--------|
| `Tab` | Cycle modes |
| `Alt+M` | Cycle permission levels |
| `Alt+T` | Toggle extended reasoning |
| `Ctrl+B` | Background-turn mode |
| `Ctrl+O` | Verbose tool output |
| `Ctrl+N` | New chat (preserves mode/model) |
| `Ctrl+T` | Task panel |
| `Ctrl+F` | Focus most recent subagent |
| `Esc Esc` | Rewind last turn |

## Documentation

- **[Installation](docs/INSTALL.md)** — Detailed setup and provider configuration
- **[lyra-cli README](packages/lyra-cli/README.md)** — Full slash command reference and TUI guide
- **[Architecture](docs/ARCHITECTURE_DIAGRAMS.md)** — System design and component interactions
- **[Testing](TESTING.md)** — Test suite overview and coverage
- **[E2E Test Report](LYRA_E2E_FINAL_REPORT.md)** — Comprehensive validation of all systems (289 tests, 99.3% pass rate)
- **[Optimization Plan](LYRA_OPTIMIZATION_PLAN.md)** — 6-phase roadmap for enterprise AI harness architecture

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, and submission guidelines.

Quick setup:

```bash
pip install -e packages/lyra-{core,cli,skills,mcp,evals,research,memory,evolution}
make test       # Run full test suite
make lint       # Check code style (ruff)
make typecheck  # Type checking (pyright)
```

**Test Coverage:** Lyra v3.14.0 has been comprehensively validated with 289 E2E tests achieving 99.3% pass rate. See [LYRA_E2E_FINAL_REPORT.md](LYRA_E2E_FINAL_REPORT.md) for detailed results.

## Research Basis

Lyra is grounded in peer-reviewed research:

- arXiv:2603.21692 — Automated Execution Representation (AER) + SLO tracking
- arXiv:2602.21227 — BAAR: 3-tier provider routing with fallback
- arXiv:2212.10509 — In-context Retrieval-augmented Chain-of-Thought (IRCoT)
- arXiv:2305.16291 — Voyager: Lifelong learning agents
- arXiv:2303.11366 — Reflexion: Structured self-reflection

Plus 7 additional papers on skill evolution, memory systems, and self-improvement techniques.

## License

MIT — see [LICENSE](LICENSE) for details.

## Links

- **GitHub**: https://github.com/ndqkhanh/lyra
- **Issues**: https://github.com/ndqkhanh/lyra/issues
- **Discussions**: https://github.com/ndqkhanh/lyra/discussions
