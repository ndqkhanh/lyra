# Contributing to Lyra

## Development Setup

```bash
git clone https://github.com/ndqkhanh/lyra.git
cd lyra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Code Conventions

### Naming
- **Files**: `snake_case.py` for Python, `kebab-case.ts` for TypeScript
- **Classes**: `PascalCase` (e.g., `AgentLoop`, `MemoryStore`)
- **Functions/variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_<module>.py` in `tests/<package>/`

### Structure
- One concept per file. Files stay under 800 lines.
- Functions stay under 50 lines.
- No nesting deeper than 4 levels.
- New modules go in `src/lyra/<module>/` with an `__init__.py`.
- Tests mirror source: `tests/<module>/test_<thing>.py`.

### Imports
- Always use absolute imports: `from lyra.memory import MemoryStore`
- Never use relative imports: `from .memory import ...`

## Commit Convention

```
<type>: <description>

feat: add voice barge-in support
fix: memory leak in long-term store
refactor: extract tool registry from executor
test: add integration tests for research pipeline
docs: update voice mode architecture diagram
chore: clean unused dependencies
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

## Pull Request Process

1. Create a branch: `git checkout -b feat/my-feature`
2. Write tests first (TDD)
3. Implement with small, focused commits
4. Run full suite: `make test` (must be green)
5. Run lint: `make lint` (must pass)
6. Push and open a PR
7. Request review — all PRs require adversarial review before merge

## Testing

- **Unit tests**: Every new function/module gets unit tests. 80%+ coverage required.
- **Integration tests**: API boundaries, provider calls, multi-agent flows.
- **Live tests**: Use `DEEPSEEK_API_KEY` for integration tests that need real LLM calls.
- Run: `make test` (1215 tests, should complete in ~2 minutes)

```bash
make test        # Full suite
make test-fast   # Stop on first failure
make ci          # Lint + typecheck + test + evals
```

## Architecture Decisions

All architecture-level decisions are recorded in [`docs/lyra-upgrade/impl/DEBATE_LEDGER.md`](docs/lyra-upgrade/impl/DEBATE_LEDGER.md) using the ADR format:
- Who objected, on what grounds
- How it was resolved
- Steelman of the rejected alternative

New architectural decisions must go through the same process: spec → debate → sign-off → build.

## Adding a New Module

1. Create `src/lyra/<module>/__init__.py`
2. Write the spec in `docs/lyra-upgrade/impl/specs/<module>.md`
3. Write failing tests in `tests/<module>/`
4. Implement in `src/lyra/<module>/`
5. Update `STRUCTURE.md` with the new module
6. Submit PR with spec link

## Code Quality

Before committing:
- [ ] Tests pass: `make test`
- [ ] Lint passes: `make lint`
- [ ] No debug prints or console.log
- [ ] No hardcoded secrets or API keys
- [ ] Error handling is explicit (no silent exception swallowing)
- [ ] Imports use absolute paths (`from lyra.x import y`)

## Questions?

See [`STRUCTURE.md`](STRUCTURE.md) for the repo map or [`docs/lyra-upgrade/`](docs/lyra-upgrade/) for the research corpus backing every design decision.
