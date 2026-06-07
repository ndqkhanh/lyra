# HKUDS/CLI-Anything — Deep-Read

**Repo**: https://github.com/HKUDS/CLI-Anything
**Paper**: arXiv:2606.03854 (tech report)
**Star cred**: Trendshift #22991

---

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: CLI-Anything auto-generates stateful, agent-native CLI interfaces for any GUI software, turning human-designed applications into tools AI agents can drive via terminal commands -- no screenshots, no brittle UI automation, no toy reimplementations.

**How it works (the 7-phase pipeline)**:

The project is NOT a single CLI tool. It is a **methodology-as-code** orchestrated by an AI coding agent (Claude Code, OpenCode, Codex, Hermes, etc.). The agent reads `HARNESS.md` (the SOP source of truth) then executes 7 phases:

1.  **Codebase Analysis** -- Scans the target software's source code to identify the backend engine (e.g., MLT for Shotcut, bpy for Blender, Pillow/GEGL for GIMP), maps GUI actions to API calls, catalogs the data model and command/undo system.
2.  **CLI Architecture Design** -- Designs Click command groups matching the app's logical domains, chooses the interaction model (stateful REPL + subcommand CLI), plans JSON output mode, designs the session state model with undo/redo.
3.  **Implementation** -- Builds the full Click CLI with modules under `cli_anything/<software>/core/`, a `utils/<software>_backend.py` that wraps the real software's subprocess interface, and `utils/repl_skin.py` for the unified REPL.
4.  **Test Planning** -- Produces `TEST.md` with unit test inventory, E2E plans, and realistic workflow scenarios before any test code is written.
5.  **Test Implementation** -- Writes multi-layered tests: unit tests (synthetic data, no external deps), E2E tests that generate intermediate files + verify structure, E2E tests calling the real software backend, and CLI subprocess tests using `_resolve_cli()`.
6.  **Documentation & SKILL.md Generation** -- Runs all tests, appends results to TEST.md, generates `SKILL.md` with YAML frontmatter and command docs for agent discovery.
7.  **PyPI Publishing** -- Creates `setup.py` with PEP 420 namespace packaging (`cli_anything.*`), configures `console_scripts` entry point, installs via `pip install -e .`.

**The generated CLI itself** is a Click-based Python package that:
- Runs in dual mode: bare command enters REPL (`invoke_without_command=True`), subcommands work as one-shot scripts
- Emits `--json` on every command for structured agent consumption
- Persists project state with undo/redo stacks (max 50 deep) via `core/session.py`
- Uses `_locked_save_json()` with `fcntl.flock()` for safe concurrent writes
- Delegates all rendering/export to the **real** software backend (e.g., `libreoffice --headless`, `blender --background`, `melt`, `sox`) -- never reimplements the software's renderer
- Displays a branded REPL banner pointing agents to the `SKILL.md` for full capability discovery

---

## 2. Architecture & Core Modules (entry points, data flow, patterns)

### Repository structure

```
cli-anything/
├── cli-anything-plugin/          # Claude Code plugin (the generator orchestrator)
│   ├── HARNESS.md                # SOP methodology -- the single source of truth
│   ├── commands/                  # Agent-facing command definitions (Markdown)
│   │   ├── cli-anything.md        # /cli-anything build command
│   │   ├── refine.md              # Incremental gap-fill refinement
│   │   ├── test.md                # Test runner
│   │   └── validate.md            # Standards compliance validation
│   ├── guides/                    # Deep-dive methodology guides
│   │   ├── preview-methodology.md # Three-layer preview model (bundle/session/trajectory)
│   │   ├── pypi-publishing.md     # Namespace packaging conventions
│   │   ├── skill-generation.md    # SKILL.md generator usage
│   │   ├── auto-save-dry-run.md   # Session auto-save pattern
│   │   ├── session-locking.md     # File lock pattern for JSON session files
│   │   ├── filter-translation.md  # Mapping effects between formats
│   │   └── timecode-precision.md  # Non-integer frame rate handling
│   ├── repl_skin.py              # Unified REPL interface (shared across all harnesses)
│   ├── skill_generator.py        # Extracts Click metadata, generates SKILL.md
│   └── preview_bundle.py         # Preview bundle packaging logic
│
├── cli-hub/                       # Package manager for installed CLIs
│   └── cli_hub/
│       ├── cli.py                # Click CLI entry point (cli-hub list/search/install/etc.)
│       ├── registry.py           # Dual registry fetcher (harness.json + public_registry.json)
│       ├── installer.py          # Dispatches to pip/npm/uv/bundled based on source metadata
│       ├── preview.py            # Generic preview bundle viewer (inspect/session/html/browser)
│       └── analytics.py          # Usage tracking (first-run, install, launch, uninstall, visit)
│
├── skills/                        # Generated SKILL.md files (62 CLIs)
│   ├── cli-anything-gimp/SKILL.md
│   ├── cli-anything-blender/SKILL.md
│   └── ...
│
├── <software>/agent-harness/      # Each generated harness (30+)
│   └── cli_anything/<software>/
│       ├── <software>_cli.py      # Click CLI group
│       ├── __main__.py            # `python -m` entry
│       ├── core/                  # Domain modules
│       │   ├── project.py         # Project create/open/save/info
│       │   ├── session.py         # Session state, undo/redo stacks
│       │   ├── layers.py          # Layer operations (add/remove/duplicate/reorder)
│       │   ├── filters.py         # Filter/effect operations
│       │   ├── export.py          # Export to real backend
│       │   └── ...                # Domain-specific modules
│       ├── utils/
│       │   ├── repl_skin.py       # Copy of shared REPL interface
│       │   └── <sw>_backend.py    # Real software subprocess wrapper
│       ├── tests/
│       │   ├── TEST.md            # Test plan + results
│       │   ├── test_core.py       # Unit tests
│       │   └── test_full_e2e.py   # E2E tests
│       └── setup.py               # PEP 420 namespace package
│
├── registry.json                  # Harness CLI registry metadata
├── public_registry.json           # Third-party public CLI metadata
└── docs/                          # Hub website, preview protocol, design docs
    ├── PREVIEW_PROTOCOL.md        # Cross-harness preview artifact spec
    └── hub/                       # CLI-Hub website (jekyll/static)
```

### Architecture patterns

- **SOP-driven code generation**: The methodology (`HARNESS.md`) is the intellectual core. Agent commands in `commands/` are thin wrappers that tell the agent to read HARNESS.md and follow it step by step. This is not traditional code generation -- it is LLM-driven code generation guided by a structured, battle-tested playbook.
- **Monorepo of independently-packaged harnesses**: Each harness is isolated under `cli_anything.<software>.*` (namespace package). They share `repl_skin.py` and `skill_generator.py` as copied files, not shared libraries. This means each is independently pip-installable with zero cross-dependencies.
- **Dual registry system**: `registry.json` contains harnesses generated by CLI-Anything itself; `public_registry.json` contains third-party CLIs (npm, brew, bundled). `cli-hub` merges them at query time.
- **Three-layer preview model**: Bundle (immutable snapshot), session (mutable live head), trajectory (append-only history) -- designed to decouple preview production (harness) from preview consumption (cli-hub viewer).
- **Multi-layered testing strategy**: Unit tests (synthetic data) -> E2E native (intermediate file validation) -> E2E real backend (invokes actual software, verifies output) -> CLI subprocess tests (tests the installed `cli-anything-<software>` command as a black box).

---

## 3. Performance/Benchmarks (real numbers from the repo)

| Metric | Value |
|--------|-------|
| Total tests | 2,461 passing, 100% pass rate |
| Unit tests | 1,732 |
| End-to-end tests | 579 |
| Node.js tests | 19 |
| Harness count | 30+ generated CLIs (GIMP, Blender, Inkscape, Audacity, LibreOffice, OBS, Shotcut, Kdenlive, Draw.io, s&box, Godot, etc.) |
| SKILL.md files | 62 generated |
| CLI-Hub catalog | 40+ installable CLIs (harness + public registries) |
| Largest harness | s&box: 244 tests (157 unit + 17 orchestrator + 50 e2e + 20 exit-code) |
| Runner-up harness | Blender: 208 tests (150 unit + 58 e2e) |
| Smallest harness | Mermaid: 10 tests |
| CLI-Hub version | 0.3.0 |
| Plugin agents supported | Claude Code, Pi, OpenCode, OpenClaw, Codex, Hermes, Qodercli, GitHub Copilot CLI |
| CI gating | pytest 100% pass, SKILL.md validation, root-skill validation |
| Security baseline | defusedxml parsing for all XML/SVG/ODF/MLT/MusicXML/CSL input |

---

## 4. Trade-offs (wins vs losses -- from issues, design decisions, complexity)

### Wins

- **Zero brittle UI automation**: No screenshots, no pixel-clicking, no RPA fragility. The CLI talks to the software's backend directly. This addresses the core failure mode of GUI-based agent approaches.
- **Real software integration**: Every generated CLI delegates rendering to the actual application (LibreOffice, Blender, GIMP, etc.). No toy reimplementations that diverge from real-world behavior.
- **Dual interaction model**: Both REPL (interactive agent sessions with context) and one-shot subcommands (scripting, pipelines) are first-class. Bare command enters REPL via `invoke_without_command=True`.
- **Agent-native from the ground up**: JSON output on every command, SKILL.md for agent discovery, `--help` auto-documentation, standard `which` for tool location.
- **Unified UX across 30+ harnesses**: ReplSkin provides consistent banners, colors, progress bars, tables, and styled output across all generated CLIs.
- **Comprehensive testing culture**: Multi-layered tests with real backend verification, magic byte checks, ZIP/OOXML structure validation, pixel/audio analysis.
- **Incremental refinement via `/refine`**: Existing harnesses can be expanded through gap analysis + targeted command generation without starting over.
- **Namespace package isolation**: Each CLI is independently versioned and installable, avoiding dependency hell.
- **Security hardening applied**: defusedxml for all XML parsing, path traversal guards (Sketch), shell metacharacter safety in installer command dispatch.

### Losses / Limitations

- **Requires frontier LLMs**: The 7-phase pipeline needs Claude Opus 4.6, Claude Sonnet 4.6, or GPT-5.4 class models. Weaker models produce incomplete or incorrect harnesses requiring extensive manual correction. This creates a hard dependency on expensive proprietary models.
- **Requires source code access**: The pipeline cannot analyze compiled-only binaries. If the target software has no available source (proprietary, decompiled-only), harness quality degrades substantially.
- **Iterative refinement often needed**: A single `/cli-anything` run may not fully cover all capabilities. Running `/refine` one or more times is documented as expected, not exceptional. This means full coverage requires multiple LLM invocations.
- **Generator quality ceiling**: The generated CLI is only as good as the LLM's understanding of the target codebase. Complex software with non-obvious backend architecture may produce incomplete or subtly wrong harnesses.
- **No unified runtime**: Each harness is a standalone Python package. There is no shared runtime that manages session state across multiple CLIs or provides cross-tool workflows.
- **Real software dependency**: Each CLI requires the target application to be installed. This is by design ("zero compromise") but means the CLI is useless without the upstream software -- no fallback, no graceful degradation. Tests fail (not skip) when backends are missing.
- **License split**: The main repository is Apache 2.0, but `cli-hub` and individual harness `setup.py` files use MIT. This dual-license surface requires attention when redistributing.
- **Preview model is harness-optional**: The three-layer preview protocol (bundle/session/trajectory) is well-designed but not all harnesses implement it. Adoption is incremental.

---

## 5. Design Rationale (why this approach)

**Why CLI?**
The authors argue CLI is the universal interface for AI agents: structured text matches LLM token format, commands chain naturally for complex workflows, `--help` provides self-describing documentation, JSON output eliminates parsing ambiguity, and it is deterministic and lightweight compared to GUI automation or API wrappers.

**Why methodology-as-code instead of a static generator?**
Rather than building a fixed code generator that produces CLIs from a schema, CLI-Anything encodes the methodology in `HARNESS.md` and lets an LLM execute it. This means the generator itself is naturally extensible -- improving the methodology improves all future harnesses. The trade-off is reliance on a frontier LLM for execution quality.

**Why real software instead of mock backends?**
The key insight is that "dumbed-down reimplementations miss 90% of functionality." A Pillow-based GIMP replacement cannot handle real GIMP filters, color profiles, or plug-in effects. Only the real software can produce authentic results. This is why the #1 rule in HARNESS.md is "use the real software -- don't reimplement it."

**Why dual-mode (REPL + subcommand)?**
Agents need two interaction modes: interactive sessions where context accumulates (REPL) and scripting where each command is independent (one-shot). Both are first-class because agents operate differently in exploration vs. production scenarios.

**Why namespace packages?**
PEP 420 namespace packages (`cli_anything.*`) allow each CLI to be independently installed, versioned, and published to PyPI without name conflicts. This enables the community-contributed harness model where anyone can publish `cli-anything-<software>` under the shared namespace.

**Why SKILL.md generation?**
AI agents discover tools through skill registries (npx skills, ClawHub, SkillHub). SKILL.md files provide a standard format for agent skill discovery. Without this, the generated CLIs would be invisible to the agent ecosystem -- they would exist on disk but the agent would never know to use them.

**Why three-layer preview (bundle/session/trajectory)?**
The preview protocol separates concerns: harnesses produce immutable bundles (one per preview step), a live session tracks the current head, and a trajectory records the full evolution. This lets `cli-hub` become a generic viewer instead of each harness building its own monitoring UI. The protocol is designed to be cheap enough for agent loops (low-res, cacheable, small) while keeping the rendering path honest (real software, no toy renderers).

---

## 6. Transfer to Lyra (one idea + SS4.x route + Impact/Effort/Tier + LICENSE)

**Idea**: Adopt a **"HARNESS.md for Lyra"** methodology -- a structured SOP document that guides AI agents to generate Lyra-compatible modules, commands, and plugins through a proven pipeline, mirroring CLI-Anything's 7-phase approach.

**Specific transfer points**:

1.  **SOP-driven module generation (SS4.2 Command Architecture)**: Lyra could use a `LYRA-HARNESS.md` that defines a standard pipeline for generating new command modules. The agent reads the SOP, analyzes the target (whether an API, a file format, or a service), designs command groups with the Lyra interaction model (LyraSession + commands as functions + structured output), implements tests, generates a module manifest, and registers it. This turns Lyra's extensibility from "write code by hand" into "tell the agent what to wrap."

2.  **SKILL.md for module discovery (SS4.6 Plugin System)**: Each Lyra module would ship a `SKILL.md` describing its commands, output format, and agent guidance. This makes the module discoverable by the Lyra agent and by external agent skill systems. Combined with a lightweight registry, Lyra modules become a marketplace rather than a file system convention.

3.  **Dual interaction model (SS4.2)**: Lyra already has session context (`LyraSession`), but formalizing the REPL vs. one-shot distinction (mirroring CLI-Anything's `invoke_without_command=True` pattern) would let modules self-describe whether they work best interactively or as scripting building blocks.

4.  **Multi-layered test pattern (SS4.4 Testing)**: CLI-Anything's four-layer test architecture (unit -> E2E native -> E2E real backend -> CLI subprocess) is directly applicable to Lyra's testing approach. Unit tests validate individual commands, integration tests verify module interactions, and E2E tests run full agent workflows against real tool backends.

5.  **Preview protocol (SS4.x or new SS)**: The three-layer preview model (bundle/session/trajectory) is relevant for any Lyra module that produces visual or structured intermediate artifacts (diagrams, renders, reports). Instead of each module inventing its own preview mechanism, adopt CLI-Anything's cross-harness protocol.

| Dimension | Value |
|-----------|-------|
| **Impact** | 8/10 -- SOP-driven generation would dramatically lower the barrier to creating Lyra modules and ensure consistent quality across all extensions |
| **Effort** | 6/10 -- Requires writing the Lyra-specific SOP (`LYRA-HARNESS.md`), adapting the SKILL.md generator, and building a lightweight registry; does not require a new plugin runtime since Lyra's architecture already supports module loading |
| **Tier** | **Gold** -- This is a structural improvement that compounds over time (every new module benefits from the methodology) and aligns with Lyra's extensibility goals |
| **License** | Apache 2.0 (main repo) / MIT (cli-hub and harness setup.py) -- both compatible with any Lyra license |

**Workstream route**: SS4.2 (Command Architecture) for the dual-mode interaction model and SOP-driven generation; SS4.6 (Plugin System) for the module registry and SKILL.md discovery; SS4.4 (Testing Infrastructure) for the multi-layered test pattern.
