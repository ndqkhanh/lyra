# Contributing to Lyra

Lyra is a CLI-native general-purpose coding-agent harness. This document
explains how to set up a dev environment, what tools we use, and the
conventions you are expected to follow when sending changes.

## Project layout

Lyra is a Python monorepo with eight installable packages:

| Package         | Role                                                      |
| --------------- | --------------------------------------------------------- |
| `lyra-core`    | Kernel: agent loop, hooks, tools, context, memory, HIR    |
| `lyra-cli`     | User-facing CLI (`lyra`, `ly`) — Typer + Rich + prompt_toolkit |
| `lyra-skills`  | SKILL.md loader, router, ledger, extractor, packs         |
| `lyra-research` | 10-step deep research pipeline with paper discovery       |
| `lyra-evolution` | Self-evolution: Ctx2Skill, Voyager, Reflexion           |
| `lyra-memory`   | Long-term memory: codebase graph, FTS5 search            |
| `lyra-evals`   | Eval harness: golden corpus, drift gate, public-benchmark adapters |
| `lyra-mcp`     | MCP client + server adapters                              |

`lyra-core` depends on the sibling library [`harness_core`](../orion-code/harness_core/),
which is **not** part of this repo. Clone it next to `harness-engineering/`
or `pip install -e` it before running the test suite.

## Dev environment

Requires **Python 3.11+** (CI runs 3.11; the legacy `>=3.9` pin in package
metadata is being phased out — see Phase 1e in `CHANGELOG.md`).

```bash
# Editable install + dev tooling (ruff, pyright, pytest, PyYAML)
make install-dev

# Or by hand
python3 -m pip install ruff pyright pytest pytest-cov PyYAML
python3 -m pip install -e packages/lyra-core \
                        -e packages/lyra-skills \
                        -e packages/lyra-research \
                        -e packages/lyra-evolution \
                        -e packages/lyra-memory \
                        -e packages/lyra-evals \
                        -e packages/lyra-mcp \
                        -e packages/lyra-cli
```

## Running checks before sending a PR

The single command CI runs:

```bash
make ci    # = lint + typecheck + test + evals
```

Individual targets:

```bash
make lint       # ruff check on all 8 packages
make typecheck  # pyright on all 8 packages (strict on lyra-core / lyra-cli)
make test       # full pytest suite (~2,115 tests)
make test-fast  # stop on first failure
make evals      # golden-corpus smoke
```

## Conventions

- **Style**: ruff with `select = ["E","F","I","UP","B","RUF"]` and 100-col
  lines. Format on save; do not hand-format.
- **Types**: `pyright` `basic` mode for all five packages. `lyra-core`
  and `lyra-cli` are held to a stricter bar — adding `# type: ignore`
  there requires a comment explaining why.
- **Tests**: always add a test for a behavior change. RED-test marker
  `phase0_red` is for in-flight scaffolding; remove it in the PR that
  makes the test pass.
- **Skills (SKILL.md)**: every vendored skill must carry an SPDX
  frontmatter line. AGPL-licensed skills are rejected by the loader by
  default (override with `--accept-agpl`).
- **Slash commands**: register through the canonical
  `lyra_cli.commands.registry.COMMAND_REGISTRY`. Do not add ad-hoc
  registries.

## What not to commit

- `**/*.egg-info/`, `**/.pytest_cache/`, `**/__pycache__/` (gitignored).
- `papers/*.pdf` (large; track in Git LFS or out-of-tree).
- Anything in `.lyra/` other than `.gitkeep` and `policy.yaml`.
- Any file with secrets (API keys, OAuth tokens, `.env` content).

## Reporting issues

File issues at the project's GitHub repo. Include `lyra doctor --json`
output and a minimal reproduction.

## License

By contributing you agree your code is released under the MIT License
in `LICENSE`.
