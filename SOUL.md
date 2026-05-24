# SOUL — Project Persona

> This file defines how Lyra operates. It is read at the start of every session.
> Keep it short, durable, and reviewed in PRs.

## Operating Principles

1. **Tests First.** Every code change starts with a failing test. No test exists for the behavior you're about to change? Write one first.
2. **Evidence Over Assertion.** Run the command before claiming the fix. Verify before declaring success.
3. **Minimum Viable Diff.** The smaller the diff that makes the test pass, the easier the review. Three similar lines beats a premature abstraction.
4. **Transparent Failure.** On error, print the specific blocked path or missing precondition; do not swallow.
5. **Immutable State.** Create new objects, never mutate. Pydantic models with `frozen=True` throughout.
6. **Provider Agnostic.** The kernel has zero network dependencies. All provider clients live in `lyra-cli`.
7. **Package Isolation.** Each package has its own `pyproject.toml`, tests, and README. Compose, don't inherit.

## Project Context

- **Language(s):** Python 3.11+ (primary), TypeScript 5.3+ (UI layer)
- **Package Manager:** pip (Python), npm (TypeScript/Node)
- **Test Runner:** pytest (Python), Jest/Vitest (TypeScript)
- **Lint / Format:** ruff + black + mypy (Python), ESLint + Prettier (TypeScript)
- **CI:** GitHub Actions (.github/workflows/ci.yml)
- **Deploy Target:** CLI application (pip install), optional TUI (npm)

## Repository Layout

```
src/                  # Core Python library (agents, memory, hooks, rules, skills, security)
packages/             # 135+ subpackages in 3 tiers (Foundation → Breakthrough → AGI Ascent)
  lyra-core/          # Kernel: AgentLoop, TDD gate, permissions, HIR observability
  lyra-cli/           # CLI application: Typer, prompt_toolkit REPL, 16 LLM providers
  lyra-*/             # Domain packages (reasoning, research, memory, evolution, etc.)
  ui-*/               # TypeScript UI packages (core state, Ink terminal, transport)
harness_core/         # Shared harness primitives (tools, permissions, evals, verifier)
tests/                # Integration and system tests
docs/                 # MkDocs documentation site (architecture, contributing, guides)
```

## Branch & Commit Policy

- **Main branch:** `main` — protected, CI must pass
- **Feature branches:** `feat/<name>`, `fix/<name>`, `refactor/<name>`
- **Commit style:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`

## Conventions

- **Python:** PEP 8, type annotations on all function signatures, `black` formatting (line-length=100), `ruff` linting
- **TypeScript:** Strict mode, React JSX, bundler module resolution
- **File size:** 200-400 lines typical, 800 max
- **Function size:** <50 lines
- **Nesting:** Max 4 levels, prefer early returns
- **Imports:** `isort` ordering, absolute imports preferred within `src/`
- **Naming:** snake_case (Python), camelCase (TypeScript)
- **Docstrings:** One-line summary for public API. Full Google-style only when non-obvious.

## Dangerous Operations

The following must never run without explicit human approval:

- `git push --force` on `main`
- `DROP TABLE`, `DELETE FROM` without a `WHERE` clause
- Any command that rewrites `.git/objects/*`
- Deployment commands to production environments
- `rm -rf` outside of build artifacts
- Modifying `.github/workflows/ci.yml` without review
