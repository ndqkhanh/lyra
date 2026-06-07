# JuliusBrussee/caveman — Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: Caveman is an output-compression system for AI coding agents. It makes agents speak in terse caveman-style prose, cutting ~65-75% output tokens while preserving full technical accuracy. Its tagline is "why use many token when few do trick."

**Mechanism in practice**: The entire behavior change comes from a single SKILL.md prompt instruction file loaded as Claude Code system context (or injected via per-agent rule files). The instruction defines:

- Drop articles (a/an/the), filler words (just/really/basically), pleasantries (sure/certainly/of course), hedging (perhaps/maybe/I think)
- Use sentence fragments, short synonyms (big not extensive, fix not "implement a solution for")
- Code blocks, URLs, paths, error strings, identifiers: never abbreviated
- Pattern: `[thing] [action] [reason]. [next step].`
- Six intensity levels: lite, full (default), ultra, wenyan-lite, wenyan-full, wenyan-ultra

Crucially, the model is told to **drop caveman mode** (auto-clarity) for security warnings, irreversible action confirmations, and when the user is confused. Code, commits, and PRs are always written in normal prose.

The mechanism is **not model fine-tuning**, it is a pure prompt-level transformation. A companion fine-tuned model (cavegemma, Gemma 4 31B on caveman pairs) exists but is separate.

Supporting mechanisms:
- **caveman-shrink**: an MCP middleware proxy that compresses tool descriptions in MCP server responses using the same compression rules (but implemented in Node.js regex, not via an LLM)
- **caveman-compress**: a sub-skill that rewrites memory files (CLAUDE.md, project notes) into caveman prose, reducing input tokens by ~46% for every future session
- **caveman-stats**: reads Claude Code session logs, computes lifetime token savings, writes to statusline badge

## 2. Architecture & Core Modules

**Language**: Node.js (installer, hooks, MCP shrink) + Python (evals and benchmarks). Zero npm runtime dependencies for the installer.

### Source layout

```
bin/install.js              # UNIFIED INSTALLER — detects 30+ agents, installs caveman per-mechanism
bin/lib/settings.js         # JSONC-tolerant settings.json reader/writer, validateHookFields
bin/lib/openclaw.js         # OpenClaw workspace helper (skill folder + SOUL.md bootstrap)

src/hooks/caveman-config.js        # SHARED: getDefaultMode(), safeWriteFlag(), readFlag(), appendFlag()
src/hooks/caveman-activate.js      # SessionStart hook: writes flag file, emits SKILL.md as system context
src/hooks/caveman-mode-tracker.js  # UserPromptSubmit hook: slash-command / NL activation, per-turn reinforcement
src/hooks/caveman-stats.js         # SessionLog hook: reads token logs, computes savings
src/hooks/caveman-statusline.sh    # Statusline: reads flag file, prints [CAVEMAN] badge

src/rules/caveman-activate.md      # Always-on rule body (embedded in installer, per-repo init files)
src/tools/caveman-init.js          # Per-repo init: writes rule files to .cursor/, .windsurf/, .clinerules/, AGENTS.md

src/mcp-servers/caveman-shrink/
  index.js       # MCP proxy — wraps any MCP server, compresses description fields
  compress.js    # Pure-Node prose compressor (regex-based, no LLM)

skills/caveman/SKILL.md            # SINGLE SOURCE OF TRUTH — behavioral ruleset
skills/caveman-{commit,review,stats,help,compress}/SKILL.md   # Independent sub-skills

evals/
  llm_run.py     # Three-arm eval generator: baseline / terse / terse+skill
  measure.py     # Offline token counter (tiktoken), reports honest delta
  snapshots/     # Committed eval results for CI
  prompts/en.txt # Eval prompt set

benchmarks/
  run.py         # Claude API benchmark: 10 prompts x 2 modes x 3 trials
  prompts.json   # 10 coding prompts in 10 categories
  results/       # JSON results committed to git
```

### Data flow

```
[User says "caveman mode"]
        |
        v
[UserPromptSubmit hook: caveman-mode-tracker.js]
  - Parses prompt for /caveman or NL triggers
  - Writes mode to $CLAUDE_CONFIG_DIR/.caveman-active via safeWriteFlag()
  - Emits small hookSpecificOutput JSON reminder (per-turn reinforcement anchor)
        |
        v
[Next response: model sees SKILL.md + per-turn reminder]
  - SKILL.md was injected by SessionStart hook as hidden system context
  - Full rules with intensity-level filtering (only active level's examples shown)
  - Per-turn reminder prevents drift after context compression or competing injections
        |
        v
[Statusline badge reads flag file]
  - caveman-statusline.sh reads .caveman-active
  - Shows [CAVEMAN] or [CAVEMAN:ULTRA] in Claude Code statusline
  - Appends lifetime savings suffix (e.g., "⛏ 12.4k")
```

### Provider matrix
The installer supports 30+ agents organized by install mechanism:
- **Plugin/hook**: Claude Code (plugin + hooks), Gemini CLI (extension), opencode (native plugin), OpenClaw (workspace skill + SOUL.md bootstrap)
- **Skills CLI**: Codex, Cursor, Windsurf, Cline, Continue, Roo Code, Augment, Copilot, Aider, and 15+ more via `npx skills add`
- **Soft probes** (opt-in only): Junie, Qoder, Antigravity -- no reliable detect probe

### Design patterns
- **Flag-file IPC**: hooks communicate state through a shared flag file at `$CLAUDE_CONFIG_DIR/.caveman-active`. Written with symlink-attack mitigation (O_NOFOLLOW, uid check, atomic temp+rename, 0600 perms).
- **Single source of truth**: SKILL.md is the only behavior file. Hooks read it at runtime and filter to active level. Synced via CI to plugin distribution mirrors in `plugins/caveman/`.
- **Idempotent installer**: re-runs are safe. Settings merges are guarded by JSONC-tolerant readers, backup-then-write, and `validateHookFields()` before every write.
- **Marker-fenced blocks**: OpenClaw SOUL.md and opencode AGENTS.md get `<!-- caveman-begin -->` / `<!-- caveman-end -->` markers, enabling clean strip on uninstall while preserving user content above and below.

## 3. Performance/Benchmarks

All numbers from the README, generated by `benchmarks/run.py` through the real Claude API.

### Output token reduction (Claude API benchmarks)
10 prompts x 2 modes x 3 trials on `claude-sonnet-4-20250514`:

| Task | Normal (tokens) | Caveman (tokens) | Saved |
|------|----------------:|-----------------:|------:|
| Explain React re-render bug | 1180 | 159 | 87% |
| Fix auth middleware token expiry | 704 | 121 | 83% |
| Set up PostgreSQL connection pool | 2347 | 380 | 84% |
| Explain git rebase vs merge | 702 | 292 | 58% |
| Refactor callback to async/await | 387 | 301 | 22% |
| Architecture: microservices vs monolith | 446 | 310 | 30% |
| Review PR for security issues | 678 | 398 | 41% |
| Docker multi-stage build | 1042 | 290 | 72% |
| Debug PostgreSQL race condition | 1200 | 232 | 81% |
| Implement React error boundary | 3454 | 456 | 87% |
| **Average** | **1214** | **294** | **65%** |

Range: 22% (async refactor -- short prompts have less filler to drop) to 87% (explanations with heavy filler).

### Input token reduction (caveman-compress)
Real memory files compressed:

| File | Original | Compressed | Saved |
|------|---------:|----------:|------:|
| claude-md-preferences.md | 706 | 285 | 59.6% |
| project-notes.md | 1145 | 535 | 53.3% |
| claude-md-project.md | 1122 | 636 | 43.3% |
| todo-list.md | 627 | 388 | 38.1% |
| mixed-with-code.md | 888 | 560 | 36.9% |
| **Average** | **898** | **481** | **46%** |

### Three-arm eval design
The `evals/` harness is designed to measure the **honest delta**: how much the SKILL.md itself adds beyond a plain "Answer concisely." instruction:

- **baseline**: no system prompt
- **terse control**: system = "Answer concisely."
- **skill**: system = "Answer concisely.\n\n{SKILL.md}"

The published README number (65%) is from the benchmarks/ directory which measures normal Claude (default system) vs full SKILL.md. The evals/ measure the skill-over-terse delta.

### What is NOT saved
- Thinking/reasoning tokens are untouched
- High-filler tasks like "async refactor" get only 22% reduction
- Code/commits/PRs are written in normal prose per the skill's boundaries

## 4. Trade-offs

### Wins
- **~65-75% cost reduction** on output tokens for explanation/architecture tasks
- **~3x perceived speed** -- shorter responses are faster to read and process
- **~46% input token savings** via caveman-compress on memory files alone (compound savings: less input, less output, every session)
- **30+ agent reach**: one codebase, one installer, 30+ agent targets
- **Honest evals**: the three-arm design prevents self-deception (measuring vs "Answer concisely." not vs baseline)
- **No model fine-tuning required**: pure prompt instruction, instantly deployable
- **Auto-clarity safety valves**: the model drops caveman mode for security warnings and destructive operations
- **Symlink-attack hardened**: safeWriteFlag() uses O_NOFOLLOW, uid verification, atomic temp+rename, permission 0600, size capping on reads

### Losses / Limitations
- **Not all tasks benefit equally**: short/terse prompts (refactor, architecture debate) get only 22-30% savings
- **Cannot compress code output**: code/commits/PRs explicitly excluded; the compression can only work on prose
- **Thinking tokens untouched**: caveman compresses what the model *says*, not what it *thinks*. The cost of internal reasoning is unchanged.
- **Prompt-only fragility**: the behavior depends entirely on the model obeying the instruction. Future model updates could regress compliance.
- **Context-window overhead**: the SessionStart hook emits the full SKILL.md (filtered per level) as system context -- this adds ~200-400 tokens of system prompt overhead per session.
- **Per-turn reinforcement overhead**: each UserPromptSubmit injects a small JSON reminder. Adds a few tokens per turn, but prevents drift.
- **MCP shrink is regex-based**: the caveman-shrink MCP proxy uses regex, not an LLM. It can only strip known patterns, not restructure prose. The MCP shrink compresses descriptions but cannot reduce the *number* of tools exposed.

### Design decisions learned from issues
- `bin/install.js` replaced the old bash/ps1 quartet because of Windows quoting bugs causing JSON merge corruption (issue #249)
- `npx skills add` must pass `--yes --all` flags when stdin is not a TTY (curl|bash) -- without these, the interactive checkbox list exits 0 with zero skills installed (issue #370)
- `src/hooks/package.json` pins `{"type": "commonjs"}` so `require()` works even when an ancestor package.json declares `"type": "module"` (ReferenceError in ES module scope)
- The safeWriteFlag() symlink protection exists because the flag file path is predictable (`~/.claude/.caveman-active`) -- a local attacker could replace it with a symlink to clobber other files writable by the user
- Hook files must silent-fail on all filesystem errors -- never let hook crash block session start

## 5. Design Rationale

**Why prompt instruction instead of fine-tuning?**
Because it's deployable instantly, requires no model training, and works across 30+ agent backends. The cavegemma fine-tuned model exists as a companion for users who want baked-in compression, but the primary distribution is prompt-based.

**Why a three-arm eval?**
The honest delta is skill vs terse, not skill vs baseline. Comparing to baseline conflates the skill with generic terseness. The harness is designed to prevent this cheating.

**Why flag-file-based IPC instead of in-memory?**
Hooks run as separate Node.js processes spawned by Claude Code. They cannot share in-memory state. The flag file at a well-known path is the only reliable communication mechanism between the SessionStart hook (runs once per session) and the UserPromptSubmit hook (runs every turn) and the statusline script (runs on every keystroke).

**Why SKILL.md as the single source of truth?**
The skill file is the only behavior definition. Hooks read it at runtime, filter by active level, and emit the relevant subset as system context. The CI workflow auto-syncs edits to plugin mirrors. Three independent mechanisms (plugin hooks, standalone hooks, per-repo init files) all consume the same source, preventing behavioral drift across distribution paths.

**Why MCP shrink exists as a separate tool?**
The model-level caveman skill compresses what the model *produces* (output). The MCP shrink compresses what the model *consumes* (tool descriptions from MCP servers). Two different attack surfaces for the same problem. The MCP layer doesn't use an LLM -- it uses the same regex-based compression as caveman-compress but in Node.js (single-runtime constraint for MCP proxies).

**Why auto-clarity?**
Caveman mode trades grammatical completeness for terseness. For security warnings, destructive operations, and multi-step instructions, the ambiguity risk outweighs the token savings. The model is instructed to drop caveman for those cases and resume after. This is a deliberate safety boundary, not a performance limitation.

## 6. Transfer to Lyra

**Transferable idea**: The **per-turn reinforcement anchor** pattern from `caveman-mode-tracker.js`.

In caveman, the SessionStart hook injects the full ruleset once. But after many turns, context compression prunes or weakens it. The UserPromptSubmit hook emits a small `hookSpecificOutput` JSON reminder each turn -- not the full ruleset, just enough to re-anchor the behavior. This prevents drift after competing instructions from other plugins or context-window pressure.

**Why this matters for Lyra**: Lyra faces the same drift problem for memory persistence and task state. The SessionStart-equivalent (loading memory) happens once, but after N turns of task execution, the model may lose track of what it was doing. A per-turn reinforcement mechanism -- a short JSON snippet re-emitted every time, acting as an attention anchor -- would keep task state alive in context without the overhead of re-injecting the full memory graph.

Specifically: rather than injecting the full memory/context onto every turn, inject a small state-snapshot (current goal, active context priority, last action). This is exactly what caveman does with `{"mode":"full"}` instead of re-emitting the full SKILL.md.

**Workstream Route**: This maps to Lyra's **Section 4.x: Context & Memory** -- specifically the problem of memory persisting across long agent interactions and surviving context compression.

**Impact**: 6/10. Not a breakthrough, but a robust, production-proven pattern for preventing behavioral drift in long-running agent sessions.

**Effort**: 2/10. The pattern is trivial to implement: a hook or middleware that emits a small JSON reminder on each UserPromptSubmit. No architectural changes.

**Tier**: Tier 1. The caveman hooks are already running in Claude Code -- this is a verified, deployed pattern that can be copied into Lyra with minimal adaptation.

**LICENSE**: MIT. Copyright (c) 2026 Julius Brussee. Free to reuse, modify, and adapt.
