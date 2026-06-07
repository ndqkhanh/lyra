# Lyra — Repository Structure

> Auto-generated from the live codebase. Last updated: 2026-06-07.

## Top-Level

```
lyra/
├── src/
│   ├── lyra/              # Python package (47 modules)
│   └── ui/                # TypeScript UI packages (3)
├── tests/                 # Test suite (90 new + 1215 existing = 1305+)
├── docs/                  # Documentation tree
│   ├── architecture/      # Architecture docs (18 files)
│   ├── blocks/            # Block-level specs (17 files)
│   ├── concepts/          # Concept explanations (20 files)
│   ├── guides/            # User & developer guides (13 files)
│   ├── innovations/       # Innovation specs (21 files)
│   ├── systems/           # Subsystem docs
│   ├── research/          # Research findings
│   └── lyra-upgrade/      # Research corpus & workstream plans
│       ├── notes/papers/  # 323 paper rigor notes
│       ├── notes/books/   # 40 book chapter notes
│       ├── notes/web/     # 11 web deep-dives
│       ├── synthesis/     # 13 thematic syntheses
│       ├── plans/         # 16 workstream plans
│       ├── repos/         # 81 cloned repos
│       ├── AUDIT.md       # Phase 6 independent audit (PASS)
│       ├── FINAL_REPORT.md # Executive summary + 8 breakthroughs
│       ├── PROGRESS.md    # Reconciled manifest (313 read + 10 failed)
│       └── RESEARCH_LOG.md # Full run log
├── scripts/               # Build & utility scripts
├── pyproject.toml         # Python build config
├── package.json           # TypeScript workspace config
├── Makefile               # Build targets
├── README.md              # Project overview
├── CHANGELOG.md           # Version history
├── SOUL.md                # Project identity & philosophy
├── BEST-PRACTICES-PLAYBOOK.md # 40-book engineering synthesis
└── LICENSE                # MIT license
```

## src/lyra/ — 47 Modules

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `core/` | Task, Result, Message types; base classes | — |
| `agents/` | Agent implementations (Primary, Code, Research, Review, Test) | — |
| `agent_loop/` | Think→Act→Observe→Reflect executor loop | — |
| `routing/` | Learned router (BEST-Route), memory router, provider backends | `learned_router.py` |
| `memory/` | 3-tier memory, consolidation, vector search, **A-MAC admission** (NEW) | `admission_control.py` |
| `context/` | Context compaction, workspace report, **ANX protocol** (NEW) | `anx_protocol.py` |
| `skills/` | Skill registry, parser, executor, importer, SkillGraph | `registry.py` |
| `tools/` | Tool registry, executor, sandbox, builtins | — |
| `hooks/` | Lifecycle event hooks + handlers | `hook_engine.py` |
| `sessions/` | SQLite-backed session persistence | — |
| `permissions/` | ALLOW/DENY/ASK access control | — |
| `safety/` | 5-layer defense, **SABER mutation gate** (NEW), evolution guard | `mutation_gate.py` |
| `verification/` | Error probe, eval harness, mutation verifier, **identity anonymizer** (NEW) | `anonymizer.py` |
| `reliability/` | Checkpoint, circuit breaker, retry | — |
| `self_knowledge/` | Introspection, uncertainty estimation | — |
| `supervisor/` | Supervisor daemon, state machine, session lifecycle | `daemon.py` |
| `worktree/` | Git worktree isolation, **.lyrainclude processor** (NEW) | `lyrainclude.py` |
| `orchestrator/` | Sub-task decomposition, worker pool, artifact mgmt | `orchestrator.py` |
| `coordination/` | Task allocation, dependency mgmt, conflict resolution | — |
| `voice/` | Audio capture, STT, TTS, pipeline, **sound effects engine** (NEW) | `sound_effects.py` |
| `research/` | Research pipeline, **Karpathy auto-research loop** (NEW) | `auto_research_loop.py` |
| `plugins/` | Plugin protocol, PluginManager, MCP gateway | — |
| `mcp/` | MCP integration, security scanning | — |
| `commands/` | Command dispatcher | — |
| `economics/` | Budget management | — |
| `observability/` | Dashboard | — |
| `ingestion/` | Knowledge ingestion/RAG pipeline | — |
| `adapters/` | Harness adapters (Claude Code, Cursor, etc.) | — |
| `rules/` | Static analysis rules engine | — |
| `transport/` | Transport layer bridge | — |
| `rmux/` | rmux integration | — |
| `agents_mesh/` | Multi-tenancy bridge | — |
| `rl_optimizer/` | GEPA optimizer, evolution guard, maker-checker | `gepa_optimizer.py` |
| `autonomy/` | Continuous autonomy loop, crash recovery | `loop.py` |
| `server/` | FastAPI server, **relay server** (NEW), routes | `relay.py` |
| `desktop/` | Desktop GUI config | — |
| `steering/` | Interrupt handling, panel steering | — |

## New Modules (June 2026 Build)

| Module | File | Research Source | Tests |
|--------|------|-----------------|-------|
| A-MAC Admission Control | `memory/admission_control.py` | MemAgent ICLR 2026 (2603.04549) | 16 |
| Identity Anonymizer | `verification/anonymizer.py` | UW-Madison (2510.07517) | 9 |
| ANX Protocol | `context/anx_protocol.py` | ANX Protocol (2604.04820) | 9 |
| .lyrainclude Processor | `worktree/lyrainclude.py` | Claude Code Worktrees + §5.1 | — |
| Sound Effects Engine | `voice/sound_effects.py` | §5.3 Voice/Sound UX | 16 |
| SABER Mutation Gate | `safety/mutation_gate.py` | SABER MemAgent ICLR 2026 | 14 |
| Karpathy Auto-Research Loop | `research/auto_research_loop.py` | Karpathy/autoresearch (~80k★) | 7 |
| Relay Server | `server/relay.py` | Claude Code Remote Control + §4.29 | 14 |
| FleetView (TUI) | `ui/ui-terminal/components/FleetView.tsx` | Claude Code Agent View + §4.13 | — |
| SkillsHub (Desktop) | `ui/desktop/src/components/SkillsHub.tsx` | §4.4 Skills System | — |

## Naming Conventions

- **Python files**: `snake_case.py` (e.g., `agent_loop.py`, `memory_store.py`)
- **Python packages**: `snake_case` (e.g., `self_knowledge`, `rl_optimizer`)
- **Test files**: `test_<module>.py` in `tests/`
- **Docs**: `kebab-case.md` (e.g., `architecture-debate.md`)
- **Classes**: `PascalCase` (e.g., `AgentLoop`, `MemoryStore`)
- **Functions/variables**: `snake_case` (e.g., `run_loop`, `memory_store`)

## Build & Test

```bash
make install        # pip install -e .
make test           # pytest tests/ (90 new tests, all passing)
make lint           # ruff check
make typecheck      # pyright
```

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python build configuration |
| `package.json` | TypeScript workspace (ui-core, ui-terminal, ui-transport) |
| `Makefile` | Build targets |
| `README.md` | Project overview |
| `CHANGELOG.md` | Version history |
| `LICENSE` | MIT license |
| `SOUL.md` | Project identity & philosophy |
| `docs/BEST-PRACTICES-PLAYBOOK.md` | 40-book engineering synthesis (8 sections, 24 practices) |
| `docs/lyra-upgrade/AUDIT.md` | Independent audit verdict (PASS) |
| `docs/lyra-upgrade/FINAL_REPORT.md` | 8 ranked breakthrough recommendations |
