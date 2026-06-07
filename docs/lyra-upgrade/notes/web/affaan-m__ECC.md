# affaan-m/ECC -- Deep-Read

Repo: `affaan-m/ECC` (npm: `ecc-universal`)
Version: `2.0.0-rc.1`
Clone path: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/affaan-m__ECC`

---

## 1. Headline Feature & Mechanism

**Headline:** A cross-harness agent operating system that installs a production-ready catalog of agents, skills, commands, hooks, rules, and MCP configurations across every major AI coding harness: Claude Code, Codex, Cursor, OpenCode, Gemini, Zed, Qwen, Antigravity, CodeBuddy, JoyCode, and GitHub Copilot.

**How it really works:**

The core mechanism is a **manifest-driven selective install pipeline**. There is no single entry-point binary that "runs" ECC -- instead, the repo is a curated filesystem layout that gets copied into the target harness's configuration directories (e.g., `~/.claude/`, `.cursor/`, `~/.opencode/`). The main CLI entrypoint, `scripts/ecc.js`, dispatches to subcommands: `install`, `plan`, `catalog`, `consult`, `status`, `doctor`, `repair`, `auto-update`, `uninstall`, and others.

The install engine works in three phases:

1. **Manifest resolution** (`scripts/lib/install-manifests.js`): Reads `manifests/install-modules.json` (a module registry) and `manifests/install-profiles.json` (profile definitions like "core", "developer", "security", "research", "full"). Each module maps to a set of filesystem paths. Each profile maps to a set of modules. Components are user-facing abstractions (skills, languages, frameworks, capabilities) that group modules.

2. **Install planning** (`scripts/lib/install/request.js` -> `scripts/lib/install/runtime.js`): Takes the user's install request (profile + target harness + includes/excludes) and produces a file-copy plan with source-to-destination mappings, respecting target-specific adapters in `scripts/lib/install-targets/`.

3. **Install execution** (`scripts/lib/install-executor.js`): Copies files per the plan, writes an `ecc-install-state.json` to track what was installed, and records version/commit metadata. Supports dry-run, partial installs (`--with`/`--without`), and incremental updates.

Beyond install, ECC provides a **hook runtime** (`scripts/hooks/`) for automation (pre-tool, post-tool, session-start, stop hooks), a **session manager** (`scripts/lib/session-manager.js`) for CRUD on Claude Code sessions stored as `.tmp` markdown files, and a **worktree orchestrator** (`scripts/lib/tmux-worktree-orchestrator.js`).

The **ecc2/** directory contains a Rust alpha control plane (`ecc-tui`) with a TUI dashboard built on `ratatui + crossterm`, a session store backed by SQLite (`rusqlite`), and subcommands: `dashboard`, `start`, `sessions`, `status`, `stop`, `resume`, `daemon`. This is the v2.0 future direction but is explicitly alpha -- the current GA surface is the Node.js install pipeline and file-based hook system.

The **src/llm/** directory is a separate Python subproject providing a provider-agnostic LLM abstraction layer (OpenAI, Anthropic, Ollama, AstraFlow) with a common interface (`LLMProvider` ABC), tool execution, and prompt templating. This lives in-tree but is independent of the main Node.js surface.

---

## 2. Architecture & Core Modules

### Entry Points

| Entry Point | Language | Purpose |
|---|---|---|
| `scripts/ecc.js` | Node.js | Main CLI dispatcher with 17 subcommands |
| `scripts/install-apply.js` | Node.js | Installation executor (also `npx ecc-install`) |
| `scripts/install-plan.js` | Node.js | Install plan inspector |
| `scripts/control-pane.js` | Node.js | ECC2 operator control pane launcher |
| `ecc_dashboard.py` | Python 3/Tkinter | Desktop GUI for browsing agents/skills/commands |
| `ecc2/src/main.rs` | Rust | ECC2 alpha TUI control plane binary |
| `src/llm/__main__.py` | Python | Provider-agnostic LLM CLI selector |
| `install.sh` / `install.ps1` | Shell/PowerShell | Legacy install scripts |

### Core Modules (scripts/lib/)

| Module | Lines | Responsibility |
|---|---|---|
| `install-manifests.js` | 20,154 | Module registry, profile resolution, component filtering |
| `install-lifecycle.js` | 33,295 | Full install lifecycle: pre/post hooks, state transitions |
| `install-executor.js` | 22,660 | File copy engine, install state recording |
| `install-state.js` | 10,508 | SQLite-backed install state read/write |
| `session-manager.js` | 15,539 | Session CRUD (`.tmp` markdown files) |
| `session-aliases.js` | 12,333 | Named aliases for sessions |
| `utils.js` | 17,846 | Shared utilities, path resolution |
| `package-manager.js` | 12,016 | Multi-PM detection (npm/pnpm/yarn/bun) |
| `project-detect.js` | 13,369 | Project type detection from filesystem |
| `tmux-worktree-orchestrator.js` | 18,241 | Git worktree + tmux session management |
| `install-targets/registry.js` | -- | Target harness adapter registry |
| `state-store/` | -- | SQLite state store abstraction |
| `skill-evolution/` | -- | Self-improving skills pipeline |
| `control-pane/` | -- | ECC2 operator plane JSON-RPC client |

### Data Flow

```
User runs: npx ecc install --profile developer --target claude

1. scripts/ecc.js (CLI dispatcher)
   -> resolves "install" subcommand
   -> spawns scripts/install-apply.js

2. scripts/install-apply.js
   -> parses args (profile=developer, target=claude)
   -> loads install config (ecc-install.json if exists)
   -> calls normalizeInstallRequest() -> createsInstallPlanFromRequest()

3. scripts/lib/install/runtime.js
   -> maps "developer" profile to module IDs
   -> calls install-manifests.js to resolve modules
   -> applies target adapter from install-targets/registry.js
   -> produces file-copy plan with source->dest mappings

4. scripts/lib/install-executor.js
   -> creates destination directories
   -> copies files (with conflict detection)
   -> writes install-state to SQLite or JSON file
   -> returns result with operation count

5. Result: Files installed to ~/.claude/ with metadata in install-state
```

### Architecture Pattern

**Modular layered architecture with pipeline-based install.** The system uses:
- **Manifest registry** (declarative config files in `manifests/`) to define what can be installed
- **Target adapters** (strategy pattern in `install-targets/`) to handle harness-specific paths and conventions
- **Pipeline phases** (plan -> resolve -> execute -> record) for the install flow
- **Event hooks** (runtime hooks in `hooks/`) for lifecycle automation
- **State store** (SQLite + JSON) for idempotent install tracking

The agent/skill content itself is purely declarative -- agents are Markdown files with YAML frontmatter, skills are Markdown documents with structured sections, commands are Markdown files with `description:` frontmatter. The "code" that makes ECC work is the install engine that places these files into the correct harness directory.

### Test Infrastructure

- 58+ test files across `tests/` mirroring `scripts/` structure
- CI pipeline with 19+ validation scripts (`tests/ci/`)
- Tools: `c8` for coverage (80% target), ESLint, markdownlint
- Test runner: `node tests/run-all.js`

---

## 3. Performance/Benchmarks

The repo does not publish latency or throughput benchmarks. Evidence is structural only:

- **997 internal tests passing** (v1.8.0), expanded to **992** (v1.7.0), **978** (v1.6.0) -- testing covers scripts, hooks, manifests, install logic
- **102 rules** in AgentShield integration (v1.6.0)
- **63 agents, 251 skills, 79 legacy command shims** (v2.0.0-rc.1 published counts)
- **12+ language ecosystems** with rule coverage
- **150 GitHub App installs** as of v2.0.0-rc.1 README badge
- **182K+ stars, 28K+ forks, 170+ contributors** on GitHub

Observability scripts exist but no published results:
- `scripts/observability-readiness.js` -- readiness scoring
- `scripts/operator-readiness-dashboard.js` -- 55KB dashboard generator
- `scripts/harness-audit.js` -- 35KB audit framework with 12 rubric categories

---

## 4. Trade-offs

### Wins

1. **Cross-harness portability is real.** The same install pipeline targets 11+ different AI coding harnesses with dedicated adapters. The fact that this works at all (rules, agents, skills, hooks translated to each harness's plugin model) is a significant engineering achievement.

2. **Selective install solves the bloat problem.** Rather than dumping 250+ skills and 60+ agents into the user's environment, profiles (core/minimal/developer/security/research/full) and per-component selection let users install exactly what they need. The `--without` flag can exclude specific components.

3. **Install state tracking enables idempotence.** The SQLite/JSON state store tracks exactly what was installed, from which version/commit, enabling `doctor`, `repair`, and `uninstall` commands that only touch ECC-managed files. This is a clean solution to the "how do I undo this?" problem.

4. **Maturity from daily use.** The changelog shows 10+ months of intensive real-world iteration with regular releases, community PRs (30+ in v1.6.0 alone), and specific bug fixes (e.g., instinct import content loss in v1.4.1).

5. **Security-first design.** AgentShield integration, prompt defense baseline in CLAUDE.md, IOC scanning supply chain scripts, security review skills -- security is treated as a first-class concern, not an afterthought.

### Losses / Limitations

1. **Massive surface area creates maintenance burden.** 251 skills, 63 agents, 79 commands -- this is an enormous catalog to keep current. Many skills may drift from their upstream library versions. The repo acknowledges this with automated validation scripts but the sheer volume is a risk.

2. **Claude plugin cannot distribute rules.** This is a platform limitation: Anthropic's plugin system doesn't support automatic rule file distribution. This means the plugin install path is incomplete -- users must manually copy rules. This is documented openly but creates a confusing install flow where "/plugin install" does not give you the full experience.

3. **Stacking install methods causes breakage.** The README has an entire section warning users not to stack install methods, with reset instructions. This is honest but indicates the install pipeline is fragile when composed. The warning "do not also run" appears multiple times.

4. **ECC2 Rust control plane is alpha with unknown GA timeline.** The `ecc2/` directory is billed as "the future" but explicitly marked alpha. The main.rs is 444KB (likely containing generated or bundled code). It's unclear when/if this will replace the Node.js install pipeline.

5. **No performance benchmarks for hooks.** The hook runtime (PreToolUse, PostToolUse) could add latency to every tool call, but there are no published benchmarks showing overhead.

6. **Documentation is fragmented.** Key knowledge is split across README.md (83KB), the-shortform-guide.md, the-longform-guide.md, the-security-guide.md, COMMANDS-QUICK-REF.md, TROUBLESHOOTING.md, and separate docs/ directories per locale. Finding a specific piece of information requires knowing which document to consult.

---

## 5. Design Rationale

ECC's design is rooted in the observation that AI coding harnesses (Claude Code, Cursor, Codex, etc.) share a common pattern: they all support some combination of agents, skills/commands, hooks/automation, rules/guidelines, and MCP/external tool configuration. Each harness implements these differently, but the _content_ is largely the same.

The design decisions follow from this:

1. **Filesystem as the interface.** Instead of building a proprietary runtime, ECC installs standard files (Markdown agents, JSON hooks, rule files) into each harness's expected directories. This makes the system declarative, inspectable, and debuggable with standard tools.

2. **Manifest-driven install avoids lock-in.** The module/profile/component manifest system (`manifests/install-modules.json`, `manifests/install-profiles.json`) means the install pipeline is data-driven. Adding a new harness target only requires writing a new adapter in `install-targets/` -- no changes to the install pipeline itself.

3. **Install state enables safety.** The SQLite state store records every file ECC installed, its source version, and checksum. This enables safe uninstall (only ECC-managed files are removed) and repair (detect and restore drifted files). This is a direct response to the pain of "I installed a config pack and now I can't undo it."

4. **Profiles map to user mental models.** "Core" = minimum viable, "Developer" = daily work, "Security" = audit-focused, "Research" = content/synthesis, "Full" = everything. This avoids overwhelming users while keeping the full catalog available.

5. **Cross-harness is not abstraction -- it's adapters.** Rather than creating a single ECC runtime that all harnesses must integrate with, ECC provides a separate adapter per harness. This is more work per-harness but avoids coupling to any single harness's API decisions.

6. **The Python LLM abstraction is structurally separate** because it solves a different problem (runtime LLM calls vs. editor configuration). It lives in-tree for convenience but has its own `pyproject.toml`, dependencies, test files, and CLI entry point.

---

## 6. Transfer to Lyra

### One Transferable Idea: **Manifest-driven selective install pipeline**

Lyra's current upgrade planning operates mostly on static plans and direct implementations. ECC's manifest-driven install system offers a proven pattern for making Lyra's own agent/skill/tool catalog modular, installable on demand, and trackable via state store.

The specific mechanism to borrow is the three-part pipeline:
1. **Module registry** (`manifests/install-modules.json`) -- a declarative JSON file that maps module IDs to their filesystem paths, dependencies, and target compatibility.
2. **Install profiles** as composable module groups -- so users can install "core" (minimal agent loop), "developer" (code review + TDD + testing), or "research" (web fetch + deep read + synthesis) profiles.
3. **Install state store** -- a simple SQLite or JSON file that records what was installed, from which version, enabling `doctor`/`repair`/`uninstall` commands.

For Lyra, this means the 30+ brainstorm plans and subsystems could be packaged as installable modules rather than monolithic upgrades. A user could install just the "memory subsystem" module (`lyra install --module memory-persistence`) or the full "reliability" profile (`lyra install --profile reliability`), with state tracking to enable clean upgrades and rollbacks.

### Integration Route

**Workstream:** Section 4.x (Component Architecture / Modular Build System)

This fits under Lyra's component architecture workstream because it addresses how Lyra's own subsystems are discovered, installed, and tracked. It's not a feature for end users -- it's an infrastructure pattern for Lyra's internal module management.

- **Where:** New `manifests/` directory at Lyra root with `install-modules.json` and `install-profiles.json`; new `lyra install` CLI subcommand; state store at `.lyra/install-state.json`
- **Impact:** 6/10 (high for developer ergonomics and upgrade reliability; lower for end-user features)
- **Effort:** 5/10 (moderate -- requires manifest schema design, file copy engine, state store, and CLI integration; the ECC codebase provides a reference implementation but Lyra would need its own)
- **Tier:** Tier 2 (Post-MVP quality-of-life improvement; not blocking initial ship)
- **Risk:** Low -- the pattern is well-demonstrated by ECC and the implementation is straightforward copy-and-track logic. The main cost is schema design and CLI surface area.

### License Compatibility

MIT (the ECC license) is fully compatible with integration into any project. No restrictions on use, modification, or distribution.

---

**Note file written to:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/affaan-m__ECC.md`
