# @evomap/evolver — Deep-Read

**Repo:** EvoMap/evolver | **Source:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/EvoMap__evolver`

## 1. Headline Feature & Mechanism (how the code really works)

Evolver is a **GEP (Genome Evolution Protocol)-powered self-evolution engine for AI agents**. Its core mechanism is a closed-loop pipeline that scans runtime logs, detects failure signals and improvement opportunities, selects matching Genes/Capsules (structured evolution assets), and emits protocol-bound prompts that guide the agent's next evolution step. Each cycle produces an auditable `EvolutionEvent` with git-integrated rollback.

The evolution cycle (from `index.js` line ~1352-1584, `src/evolve.js`, `src/gep/prompt.js`, `src/gep/solidify.js`):

1. **Signal Collection** (`src/gep/signals.js`): Reads `memory/` directory for logs, error patterns, session transcripts, and the `memory_graph.jsonl` (a JSONL event store). Extracts structured signals (error patterns, performance bottlenecks, capability gaps, plateau stagnation, etc.)
2. **Signal De-duplication** (`src/gep/signals.js:analyzeRecentHistory`): Suppresses signals that appeared 3+ times in the last 8 events to prevent repair loops.
3. **Gene/Capsule Selection** (`src/gep/selector.js`, obfuscated): Scores available Genes (strategies) and Capsules (batched changes) against extracted signals using tag overlap, semantic matching, epigenetic boost, anti-pattern penalties, and saturation detection.
4. **Strategy Preset** (`src/gep/strategy.js`): Governs the innovate/optimize/repair balance via `EVOLVE_STRATEGY` (balanced, innovate, harden, repair-only, early-stabilize, steady-state).
5. **GEP Prompt Assembly** (`src/gep/prompt.js`, obfuscated): Builds a protocol-bound GEP prompt with constraints, selected genes, signal context, and personality state.
6. **Solidify** (`src/gep/solidify.js`, obfuscated; `src/gep/gitOps.js`, readable): Applies validation commands (whitelisted: `node`, `npm`, `npx` only), measures blast radius (capped at 60 files, 20k lines), and writes the final `EvolutionEvent` to disk. Failed cycles roll back via `git stash push --include-untracked` (default) or `git reset --hard`.
7. **Daemon Loop** (`index.js` lines ~1352-1584): Adaptive sleep (2s-5min), OMLS-inspired idle scheduling for background distillation and exploration, suicide-respawn on cycle timeout (45min default) or memory leak (500MB RSS cap), singleton lock via atomic `link(2)`.

**Critical implementation note**: The core engine files (`evolve.js`, `selector.js`, `prompt.js`, `solidify.js`, `strategy.js`, `personality.js`, `mutation.js`, `epigenetics.js`, `skillDistiller.js`, `curriculum.js`, `explore.js`, `learningSignals.js` and most GEP modules) are **obfuscated** via `javascript-obfuscator` (devDependency). Only the infrastructure layer (`index.js`, `src/gep/paths.js`, `src/gep/gitOps.js`, `src/gep/signals.js`, `src/config.js`, `src/gep/memoryGraph.js`, adapters, ops, proxy, webui) remains readable. The repository is also transitioning from GPL-3.0 to source-available licensing, as stated in the README banner.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Entry point**: `index.js` (3010 lines, single file) -- serves as both CLI binary (`bin.evolver`) and daemon. Supports `run` (single cycle), `solidify`, `--loop` (daemon), `--review`, `fetch`, `sync`, `setup-hooks`, and ATP commands.

**Data flow** (from index.js main() through evolve.run()):

```
index.js (main loop)
  ├── load .env -> resolve repo root (getRepoRoot in src/gep/paths.js)
  ├── acquireLock() (singleton via atomic link(2) to ~/.evomap/instance.lock)
  ├── startHeartbeat() / startEventStream() (Hub connectivity, a2aProtocol.js)
  ├── startProxy() / registerMailboxTransport() (EvoMap Proxy, src/proxy/ for mailbox transport)
  ├── startValidatorDaemon() (decentralized validator role, src/gep/validator/index.js)
  ├── merchantAgent.start() / autoBuyer.start() (ATP marketplace, src/atp/)
  └── while(true):
        ├── evolve.run() [calls pipeline: collect -> signals -> select -> dispatch -> enrich -> hub]
        │     ├── src/evolve/pipeline/collect.js (obf) - read memory dirs, session logs
        │     ├── src/evolve/pipeline/signals.js (obf) - extract opportunity signals
        │     ├── src/evolve/pipeline/select.js (obf) - score + select Genes/Capsules
        │     ├── src/evolve/pipeline/dispatch.js (obf) - build GEP prompt
        │     ├── src/evolve/pipeline/enrich.js (obf) - add context, personality
        │     └── src/evolve/pipeline/hub.js (obf) - optional Hub sync
        ├── idleScheduler.getScheduleRecommendation() -> autoDistillFromFailures()
        ├── tryExplore() (opportunity exploration)
        └── adaptive sleep with jitter + saturation multiplier
```

**Module map:**

| Directory | Key Files | Purpose |
|---|---|---|
| `src/evolve/` | `evolve.js` (obf), `guards.js` (obf), `pipeline/` (6 files, obf) | Evolution loop orchestration |
| `src/gep/` | 60+ files covering selectors, prompts, signals, assets, strategies, personality, gitOps, paths, mutation, epigenetics, curation, skill distiller, validators, hub client, mailbox, etc. | GEP protocol engine - core intelligence |
| `src/gep/gitOps.js` | git operations (clean) | git rollback, diff snapshot, protected file list, blast radius |
| `src/gep/paths.js` | path resolution (clean) | repo root, workspace root, evolution dir, GEP assets dir |
| `src/gep/signals.js` | signal definitions + de-duplication (clean) | 20 opportunity signal types, frequency-based loop prevention |
| `src/config.js` | centralized config (clean) | All timeouts, thresholds, network configs, and limits |
| `src/adapters/` | claudeCode.js, cursor.js, codex.js, kiro.js, opencode.js | Platform-specific hook integration |
| `src/atp/` | 14 files | Agent Task Protocol - marketplace for evolution tasks |
| `src/ops/` | lifecycle, self_repair, health_check, cleanup, trigger, commentary, skills_monitor | Background operations |
| `src/proxy/` | server, router, mailbox, sync, extensions | Local proxy for EvoMap Hub communication |
| `src/webui/` | client + server + observer | Real-time dashboard for monitoring |
| `scripts/` | 16 scripts | Build, export/ingest, changelog, validation |
| `test/` | ~163 test files | Extensive test suite |

**Architecture pattern**: Daemon loop + pipeline processor + plugin adapters. The evolution pipeline is a fixed sequence of steps (collect -> signals -> select -> dispatch -> enrich -> hub), each in its own module. The outer daemon adds lifecycle management, idle scheduling, suicide-recovery, and Hub connectivity.

**Dependencies** from `package.json`:
- `@evomap/gep-sdk` (^1.5.0) and `@evomap/atp-sdk` (^0.1.0) -- likely obfuscated SDKs
- `@aws-sdk/client-bedrock-runtime` (^3.1053.0) -- LLM access
- `dotenv`, `undici` (HTTP client), `@napi-rs/keyring` (optional, OS keychain)
- Dev: `javascript-obfuscator` (^5.4.1)

## 3. Performance/Benchmarks (real numbers from the repo)

From `test/bench.test.js` and the arXiv paper (2604.15097):

| Metric | Value | Source |
|---|---|---|
| Controlled trials | 4,590 trials on 45 scientific code-solving scenarios | arXiv paper |
| CritPt lift (pair 1) | 9.1% -> 18.57% | arXiv paper / README |
| CritPt lift (pair 2) | 17.7% -> 27.14% | arXiv paper / README |
| Gene selection accuracy | >= 80% on standard signal scenarios | bench.test.js |
| Signal extraction recall (top-1) | > 50% | bench.test.js |
| Signal extraction recall (top-3) | > 80% | bench.test.js |
| Anti-pattern avoidance | >= 1 gene excluded per scenario, 0 false positives | bench.test.js |
| Failure distillation accuracy | > 70% for repair-domain genes | bench.test.js |
| Failure distillation learn rate | > 60% in learn-phase | bench.test.js |
| Daemon cycle timeout | 45 min default (configurable) | index.js / config.js |
| Max cycles per process | 100 (configurable) | index.js |
| Max RSS | 500 MB hard cap | index.js |
| Singleton lock TTL | 5 min (Unix), 3 min (Windows) | index.js |
| Heartbeat interval | 6 min (configurable) | config.js |
| Adaptive sleep range | 2 sec - 5 min | index.js |

## 4. Trade-offs (wins vs losses)

**Wins:**
- Protocol-constrained evolution ensures auditable, rollback-capable changes -- every cycle produces an `EvolutionEvent` with score, intent, blast radius, and validation outcomes
- GEP asset store (Genes + Capsules) enables reuse of successful evolution patterns across projects, with drift detection and epigenetic suppression of failing genes
- Strategy presets (balanced/innovate/harden/repair-only) adapt evolution tempo to project phase -- including force_steady_state and evolution_saturation signals
- Git-integrated rollback with stash-mode preserves user work on failure (default since v1.80.8)
- Protected critical files list prevents self-inflicted damage (MEMORY.md, SOUL.md, AGENTS.md, etc.)
- Extensive daemon hardening: singleton via atomic link(2), macOS App Nap protection (setPriority + caffeinate), OOM score adjustment, drift detector, EPIPE swallowing, process suicide with respawn, unhandled rejection sliding-window threshold
- Multi-platform adapter architecture (Cursor, Claude Code, Codex, Kiro, opencode, OpenClaw)
- Decentralized validator role for Hub consensus participation
- ATP (Agent Task Protocol) marketplace for buying/selling evolution tasks
- Comprehensive security model with command whitelisting for validation commands

**Losses:**
- **Obfuscated core engine**: The actual evolution logic (scoring, selection, prompt generation, solidify) is obfuscated via `javascript-obfuscator`. The "how it works" at the algorithmic level is hidden, making independent audit, forking, or deep learning impossible without reverse engineering.
- **Moving away from open source**: Already transitioned from MIT -> GPL-3.0, with a public commitment to move to source-available. The npm-published version has a disappearing audit trail.
- **Massive entry point**: `index.js` is 3010 lines -- a single monolithic file handling CLI parsing, daemon lifecycle, signal handling, lock management, and process supervision. Architectural debt.
- **Bleeding-edge requirement**: Requires Node >= 22.12 (as of v1.88.3), which is an extremely recent release.
- **Proprietary SDK dependencies**: `@evomap/gep-sdk` and `@evomap/atp-sdk` are not in the repo -- they are npm dependencies, likely proprietary.
- **Protocol overhead**: Not suitable for quick fixes -- every evolution cycle requires signal collection, scoring, prompt generation, and optional validation. The loop is designed for background maintenance, not interactive use.
- **Not a code patcher by design**: The primary output is GEP prompts to stdout, requiring a host runtime (OpenClaw, etc.) to execute changes. This is a deliberate architectural choice but limits standalone utility.
- **CLI/stdout coupling**: The daemon consumes its own stdout in loop mode. Output format (`sessions_spawn(...)`) is host-runtime-specific, creating a brittle contract.
- **Daemon operational complexity**: The background daemon has many subsystems (heartbeat, drift detector, SSE, ATP merchant/consumer, validator, auto-buyer, auto-deliver, keepalive timer). Each is a surface for failure in production deployment.

## 5. Design Rationale (why this approach)

The README's tagline ("Evolution is not optional. Adapt or die.") and the arXiv paper establish the core thesis: **agent evolution should be structured, auditable, and reusable, not ad-hoc prompt hacking.**

Key design decisions and their rationale:

1. **Evolver is a prompt generator, not a code patcher**: This is the single most important architectural boundary. By separating "what to evolve" (the GEP prompt) from "how to apply it" (the host runtime), Evolver can operate as a safe, auditable advisory layer. The host runtime (OpenClaw, Cursor hooks, Claude Code hooks) interprets the output and applies changes. This enables a clean security model where Evolver never executes arbitrary code.

2. **GEP protocol over ad-hoc skills**: The arXiv paper explicitly tests this: documentation-oriented "Skill" packages provide unstable, sparse control signal, while compact "Gene" representations deliver stronger performance and are more robust under structural perturbation. This is the evidence base for the entire GEP asset system.

3. **Genes/Capsules/Events triad**: Genes encode reusable strategies, Capsules batch related changes, Events provide the audit trail. The separation allows Genes to be shared across projects (via Hub), Capsules to be promoted to Genes after validation, and Events to enable rollback and traceability.

4. **Strategy presets instead of fixed evolution**: The project recognizes that different project phases need different evolution rhythms -- innovation during feature work, hardening during stabilization, repair during emergencies. Strategy presets modulate the signal-to-gene mapping weights rather than requiring code changes.

5. **Git as the rollback substrate**: Rather than building a custom undo system, Evolver piggybacks on git's existing stash/reset/revert infrastructure. This grounds evolution in the tool developers already trust and use.

6. **Hub-connected but offline-first**: The core evolution cycle runs fully offline. Hub connection is additive for network effects (skill sharing, worker pool, leaderboards). This recognizes that agent self-evolution must work in air-gapped or private environments.

7. **Singleton daemon with extensive process supervision**: The ~1000 lines of daemon lifecycle code in index.js (lock files, OOM adjustment, App Nap prevention, caffeinate, unhandled rejection windows, cycle timeouts, suicide-respawn, keepalive timers) reflect a production-oriented mindset. This was built to run 24/7, not as a research prototype.

8. **Obfuscation of the core**: The README announces a shift to source-available licensing, citing a competitor's uncredited reuse. The obfuscation is explicitly a defensive measure to protect IP while still publishing a usable npm package.

## 6. Transfer to Lyra (one idea + route + impact/effort/tier)

**Transferable Idea**: **GEP Protocol Architecture for Agent Evolution Assets**

Replace Lyra's ad-hoc prompt-based skill system with a structured evolution asset pipeline modeled after Evolver's Gene/Capsule/Event triad. Each successful agent behavior pattern becomes a versioned, auditable "Gene" with metadata (signals_match, category, strategy, confidence score). Failed attempts become "Capsules" that feed a failure distillation pipeline. Every evolution cycle produces an "EvolutionEvent" for traceability.

Concretely:
- A `lyra-skills/` directory becomes `lyra-gep/` with `genes.json`, `capsules.json`, `events.jsonl` -- a structured, queryable asset store instead of free-form skill markdown files
- Signal extraction (from agent session logs) maps directly to Lyra's existing session transcript analysis
- Strategy presets (balanced/innovate/harden) give Lyra operators control over the agent's evolution tempo
- The audit trail (`EvolutionEvent` with git rollback) provides the confidence needed for autonomous operation

The signal de-duplication system (`signals.js:analyzeRecentHistory`) is a directly transferable algorithm for preventing Lyra from cycling on the same problems -- count signal frequency in the last N events and suppress overprocessed signals.

**Workstream Route**: **Section 4.x -- Agent Evolution Assets & Audit Pipeline**

- **§4.2 (Asset Pipeline)**: GEP asset store replaces ad-hoc skill files with structured, versioned Genes and Capsules. Signal extraction from Lyra session logs drives asset selection.
- **§4.3 (Memory Graph)**: The `memory_graph.jsonl` pattern provides a durable, append-only evolution event store with workspace attestation (cryptographic workspace-id). This is directly applicable to Lyra's memory/state persistence.
- **§4.4 (Skill Distillation)**: Evolver's auto-distillation from failures (analyzing failed Capsules, synthesizing repair Genes) is a powerful pattern for Lyra's self-improvement pipeline.

**LICENSE**: GPL-3.0-or-later (package.json authoritative; README incorrectly states MIT). The core engine is obfuscated. Future versions will be source-available, not fully open source.

**Impact**: 9 / 10 (Transformational -- the GEP protocol pattern fundamentally changes how agent evolution assets are structured, versioned, and audited. It moves Lyra from ad-hoc prompt modifications to a structured evolution pipeline with measurable outcomes.)

**Effort**: 8 / 10 (Large -- implementing the full GEP triad (Genes, Capsules, Events), signal extraction pipeline, selector engine, and solidify/validation machinery requires substantial engineering. Around 60+ module equivalents when counting Evolver's GEP directory. However, substantial portions can be adapted rather than written from scratch, and the audit trail / rollback infrastructure can bootstrap from Lyra's existing git integration.)

**Tier**: breakthrough
