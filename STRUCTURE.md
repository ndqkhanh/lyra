# Lyra — Repository Structure

> Auto-generated from the live codebase. Last updated: 2026-06-07.

## Top-Level

```
lyra/
├── src/
│   ├── lyra/              # Python package (40 modules)
│   └── ui/                # TypeScript UI packages (3)
├── tests/                 # Test suite (1215 passing, 0 failures)
├── docs/                  # Documentation tree
│   ├── architecture/      # Architecture docs
│   ├── guides/            # User & developer guides
│   ├── concepts/          # Concept explanations
│   ├── systems/           # Subsystem docs
│   └── lyra-upgrade/      # Research corpus & workstream plans
├── scripts/               # Build & utility scripts
├── pyproject.toml         # Python build config
├── package.json           # TypeScript workspace config
├── Makefile               # Build targets
├── README.md              # Project overview
└── CHANGELOG.md           # Version history
```

## src/lyra/ — 40 Modules

| Module | Purpose | Lines (approx) |
|--------|---------|----------------|
| `core/` | Task, Result, Message types; base classes | 2,500 |
| `agents/` | Agent implementations (Primary, Code, Research, Review, Test) | 2,500 |
| `agent_loop/` | Think→Act→Observe→Reflect executor loop | 700 |
| `routing/` | Provider backends (Anthropic, OpenAI, DeepSeek, Google) + router | 2,000 |
| `memory/` | 3-tier memory (STM/LTM/index), consolidation, retrieval, vector search | 2,700 |
| `context/` | Context compaction, workspace report | 300 |
| `skills/` | Skill registry, parser, executor, importer | 1,300 |
| `tools/` | Tool registry, executor, sandbox, builtins | 800 |
| `hooks/` | Lifecycle event hooks (PreToolUse, PostToolUse, Stop) + handlers | 1,000 |
| `sessions/` | SQLite-backed session persistence | 500 |
| `permissions/` | ALLOW/DENY/ASK access control | 400 |
| `safety/` | 5-layer defense-in-depth pipeline, tool gate, evolution guard | 1,800 |
| `security/` | (see safety/) | — |
| `verification/` | Error probe, eval harness, mutation verifier, tracing | 2,700 |
| `reliability/` | Checkpoint, circuit breaker, retry | 500 |
| `self_knowledge/` | Introspection, uncertainty estimation | 300 |
| `supervisor/` | Supervisor daemon, state machine, fleet orchestration | 400 |
| `worktree/` | Git worktree isolation manager | 300 |
| `orchestrator/` | Sub-task decomposition, worker pool, artifact mgmt | 850 |
| `coordination/` | Task allocation, dependency mgmt, conflict resolution | — |
| `voice/` | Audio capture, STT, TTS, streaming pipeline, barge-in | 1,600 |
| `research/` | Research pipeline | 600 |
| `plugins/` | Plugin protocol, PluginManager, MCP gateway | 700 |
| `mcp/` | MCP integration | — |
| `commands/` | Command dispatcher | 400 |
| `economics/` | Budget management | 300 |
| `monitoring/` | (see economics/) | — |
| `observability/` | Dashboard | 300 |
| `ingestion/` | Knowledge ingestion/RAG pipeline | 400 |
| `adapters/` | Harness adapters (Claude Code, Cursor, etc.) | 600 |
| `rules/` | Static analysis rules engine | 700 |
| `transport/` | Transport layer bridge | 400 |
| `rmux/` | rmux integration | 200 |
| `agents_mesh/` | Multi-tenancy bridge | 300 |
| `rl_optimizer/` | RL optimizer (stub) | 200 |
| `desktop/` | Desktop GUI config (stub) | 400 |

## Naming Conventions

- **Python files**: `snake_case.py` (e.g., `agent_loop.py`, `memory_store.py`)
- **Python packages**: `snake_case` (e.g., `self_knowledge`, `rl_optimizer`)
- **Test files**: `test_<module>.py` in `tests/<package>/`
- **Docs**: `kebab-case.md` (e.g., `architecture-debate.md`)
- **Classes**: `PascalCase` (e.g., `AgentLoop`, `MemoryStore`)
- **Functions/variables**: `snake_case` (e.g., `run_loop`, `memory_store`)

## Build & Test

```bash
make install        # pip install -e .
make test           # pytest tests/ (1215 tests)
make lint           # ruff check
make typecheck      # pyright
```

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python build configuration |
| `package.json` | TypeScript workspace (ui-core, ui-terminal, ui-transport) |
| `Makefile` | Build targets |
| `.gitignore` | Git ignore rules |
| `README.md` | Project overview |
| `CHANGELOG.md` | Version history |
| `LICENSE` | MIT license |
| `SOUL.md` | Project identity & philosophy |
