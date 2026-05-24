# Contributing to Lyra

Lyra is a CLI-native general-purpose coding-agent harness. This document explains how to set up a dev environment, what tools we use, and the conventions you are expected to follow when sending changes.

## Project Layout

Lyra is a Python + TypeScript monorepo with 135+ installable packages organized in three tiers:

**Foundation Tier** (core agent runtime):

| Package | Role |
|---------|------|
| `lyra-core` | Kernel: AgentLoop, TDD state machine, permissions, hooks, HIR observability |
| `lyra-cli` | User-facing CLI (`lyra`, `ly`) — Typer + prompt_toolkit + Rich |
| `lyra-agents` | Agent implementations (PrimaryAgent, CodeAgent, TestAgent, etc.) |
| `lyra-orchestration` | Task allocation, load balancing, dependency management |
| `lyra-memory` | 8-level hierarchical memory with hybrid BM25+vector retrieval |
| `lyra-skills` | SKILL.md loader, router, trigger registry |
| `lyra-evals` | Eval harness: golden corpus, drift gate |
| `lyra-mcp` | MCP client + server adapters |

**Breakthrough & AGI Ascent tiers** (advanced intelligence): `lyra-reasoning`, `lyra-research`, `lyra-evolution`, `lyra-cognitive`, `lyra-continual`, `lyra-verification`, `lyra-rsi`, and 120+ more. See the [package catalog](../README.md#package-catalog) for the full list.

**UI tier** (TypeScript): `ui-core`, `ui-terminal`, `ui-transport`.

## Dev Environment

Requires **Python 3.11+** and **Node.js 20+** (for TUI).

```bash
# Editable install + dev tooling
pip install -e ".[dev]"
npm install && npm run build --workspaces

# Or via make
make install-dev
```

### Installing specific packages

```bash
pip install -e packages/lyra-core \
            -e packages/lyra-cli \
            -e packages/lyra-memory \
            -e packages/lyra-skills
```

## Running Checks

```bash
make ci         # = lint + typecheck + test

make lint       # ruff check on all packages
make typecheck  # mypy + pyright on all packages
make test       # full pytest suite
make unit       # unit tests only
make integration # integration tests
```

### Individual checks

```bash
# Python
ruff check src/ packages/
mypy src/
pytest tests/ -v

# TypeScript
npm run type-check
npm test
```

## Conventions

- **Style**: ruff with `select = ["E","F","I","UP","B","C4"]` and 100-col lines. Format on save; do not hand-format.
- **Types**: mypy `strict` mode for `src/`. Type annotations on all function signatures.
- **Tests**: Always add a test for a behavior change. Follow TDD: RED → GREEN → REFACTOR.
- **Skills (SKILL.md)**: Every vendored skill must carry YAML frontmatter with `name`, `description`, `category`, `trigger_patterns`, and `tags`.
- **Immutability**: Prefer `dataclass(frozen=True)` and `NamedTuple`. Never mutate in place.
- **File size**: 200-400 lines typical, 800 max. Functions under 50 lines.
- **Package isolation**: Each package has its own `pyproject.toml`, tests, and README.

## What Not to Commit

- `**/*.egg-info/`, `**/.pytest_cache/`, `**/__pycache__/` (gitignored)
- `papers/*.pdf` (large; track in Git LFS or out-of-tree)
- Anything in `.lyra/` other than `.gitkeep` and `policy.yaml`
- Any file with secrets (API keys, OAuth tokens, `.env` content)
- Session artifacts and progress reports (these go in `archive/`)

## Reporting Issues

File issues at the project's GitHub repo. Include `lyra doctor --json` output and a minimal reproduction.

## License

By contributing you agree your code is released under the MIT License in `LICENSE`.
