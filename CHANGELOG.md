<!-- lyra-legacy-aware: this changelog preserves the full rename history
     (v1.6 `open-coding` → v1.7 `open-harness` → v1.7.1 `lyra`) so release
     archaeology keeps working. Legacy brand tokens below are intentional. -->

# Changelog

All notable changes to Lyra will be documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/).

> **Brand history.** This project was **`open-coding`** through v1.6,
> **`open-harness`** during the v1.7 transitional development cycle,
> and is **`lyra`** from v1.7.1 onward. Upgrade notes for both hops
> live in [`docs/migration-to-lyra.md`](docs/migration-to-lyra.md).

## v3.5.0 — 2026-04-27 — "Phase O: Reflective Learning"

The harness learns from itself. Phase O wires a Memento-style
**Read-Write Reflective Learning (RWRL)** loop into Lyra's progressive
skills surface — every chat turn now writes outcomes back to a local
skill ledger, and the next turn *reads* those outcomes to decide
which skills to inject. No new infrastructure is required: the
ledger is one JSON file, the reflective tooling reuses the existing
provider registry, and every new seam is best-effort so a missing
ledger or read-only `$LYRA_HOME` cannot break a chat.

The design sources are deliberate:

* **GitHub — `Memento-Teams/Memento-Skills`** for the agent shape:
  stateful prompts, skill utility scoring, failure attribution, and
  a "dream daemon" that consolidates recurring sessions into new
  skills.
* **arXiv:2603.18743** for the *Read-Write Reflective Learning*
  formalisation: every action emits a writable outcome, future
  decisions read aggregated outcomes, and reflection happens on
  demand rather than in a heavy training loop.

What we deliberately did **not** import from those sources: hybrid
BM25 + dense retrieval (Lyra's progressive activation already covers
the keyword path and we keep the leaf package dependency-free), the
multi-IM gateway and PyQt GUI shell (Lyra is CLI-first), and the
operator-facing fine-tuning pipeline (Lyra runs the harness, not the
model). Everything below is what *did* survive the filter.

### Added

- **`SkillLedger` (`lyra_skills.ledger`)** — a stdlib-only JSON
  ledger at `~/.lyra/skill_ledger.json` that aggregates per-skill
  `successes`, `failures`, `last_used_at`, `last_failure_reason`,
  and a bounded `outcomes[]` history. Writes are atomic
  (`tempfile + os.replace`), the file is `chmod 600`, and the
  module exposes:
  - `SkillOutcome` (`success` | `failure` | `neutral`),
  - `SkillStats.record(...)`,
  - `utility_score(stats)` — success-ratio with a 24-hour recency
    boost,
  - `top_n(ledger, n)` — sorted by utility, then by activation
    count, then by recency.
- **Per-turn activation telemetry.** `_augment_system_prompt_with_skills`
  now receives the user's `line` (fixing a long-standing wiring
  bug — progressive bodies had previously been injected only when
  forced via `force_ids`). The new `render_skill_block_with_activations`
  helper returns both the rendered system block and the list of
  activated skill IDs / reasons.
- **`LifecycleEvent.SKILLS_ACTIVATED`** — a new lifecycle event the
  driver fires before each turn carrying
  `{ session_id, turn, activated_skills: [{skill_id, reason}, …] }`.
  Subscribed by the HIR journaller (`skills.activated` line in
  `events.jsonl`), the OTel/Langfuse/LangSmith fan-out, and any
  user plugin via `on_skills_activated`.
- **`SkillActivationRecorder`** — bridges
  `TURN_COMPLETE` / `TURN_REJECTED` from the lifecycle bus to
  `SkillLedger.record(...)`. A rejected turn (slash-command revert,
  permission denial, plan rejection, etc.) attributes the *failure*
  to every skill that fired that turn, so utility scores reflect
  *user-visible* outcomes, not just LLM completion.
- **`lyra skill stats`** — Rich table (or `--json`) of
  `id · utility · successes · failures · last_used`, sorted by
  utility. `--top N` to limit rows; `--include-zero` to surface
  never-fired packs that may need promotion.
- **`lyra skill reflect <id>`** — LLM-backed dry-run that proposes
  an improved `SKILL.md` from the failure history of one skill.
  Defaults to a unified diff on stdout; `--apply` writes the new
  file with a timestamped `.bak` next to it. Provider is picked by
  the existing `build_llm("auto")` registry (no hard dep on any
  one vendor).
- **`lyra skill consolidate`** — the "dream daemon" port. Scans
  recent `events.jsonl` for `user.prompt` lines, clusters them with
  light stemming + Jaccard similarity, and asks the active LLM to
  propose new `SKILL.md` candidates for the dominant clusters.
  Default writes proposals to `$LYRA_HOME/skills/_proposals/` for
  human review; `--apply` installs straight into
  `$LYRA_HOME/skills/`.
- **Utility-aware progressive activation.** `select_active_skills`
  now accepts an optional `utility_resolver: Callable[[str], float]`.
  When two progressive skills tie on keyword match, the one with
  higher ledger utility wins. `force_ids` continue to take absolute
  precedence; a missing or failing resolver falls back to the
  pre-O.6 iteration order (no behaviour change for fresh installs
  with an empty ledger).
- **Live REPL wiring** — `skills_inject._build_utility_resolver`
  loads the ledger once per turn and feeds it to
  `select_active_skills`, so chat traffic immediately benefits
  from the closing RWRL loop without any user opt-in.
- **`test_phase_o_smoke.py`** — the canary that fails first if
  the version string, `lyra skill stats|reflect|consolidate`, the
  `SKILLS_ACTIVATED` lifecycle event, the ledger module, or the
  `utility_resolver` parameter ever regress.

### Changed

- **CLI version** bumped from `3.4.0` → `3.5.0`. `lyra version`,
  `--version`, the banner, and the embedded `LyraClient` all
  surface the new string. `test_phase_m_smoke` /
  `test_phase_n_smoke` were updated in lockstep.
- **`select_active_skills(...)`** — added the optional
  `utility_resolver` keyword argument. Existing call sites are
  unchanged; older `lyra-skills` builds (pre-O.6) keep working
  because `lyra-cli` falls back to the resolver-free signature on
  `TypeError`.
- **Driver lifecycle subscriptions** — the journaller and the
  plugin dispatcher both bind to `SKILLS_ACTIVATED` when the enum
  exposes it (`hasattr` guard), keeping the change forward-only
  for callers pinned to older `lyra-core`.

### Fixed

- **Progressive activation wiring bug.** The CLI's
  `_augment_system_prompt_with_skills` previously called the skill
  injection helper without forwarding the user's prompt, so
  `select_active_skills` saw an empty string and only ever returned
  the `force_ids` set. Phase O.2 routes `line` through the helper
  and adds a regression test in `test_skills_telemetry.py`.

### Research notes

The `references/research/memento-skills.md` design memo (added in
the same release) records exactly which Memento-Skills concepts
were imported, which were rejected, and why — useful when somebody
asks "should we add hybrid retrieval / agent-to-agent chat / a
Qt GUI?" again in 2027.

## v3.4.0 — 2026-04-27 — "Phase N: Harness Hardening"

The runtime grows up. Phase N takes the building blocks Lyra already
ships (chat, plan, sessions, skills, slash commands) and turns them
into a programmable, observable, sandbox-able harness — without
breaking any of the v3.3 surface.

The five pillars are pulled from DeerFlow's design playbook:

* **Embedded library.** Anything the CLI can do, a Python program
  now can do too: `from lyra_cli.client import LyraClient`.
* **Observability.** Every turn fires a fan-out trace through a
  pluggable hub. Two production observers ship in the box
  (LangSmith, Langfuse); custom ones are 30 lines.
* **Skills are first-class artifacts.** SKILL.md grows a versioned
  frontmatter (`version`, `keywords`, `progressive`, `requires`,
  `applies_to`); `lyra skill add` installs from a local path or a
  Git URL; progressive packs only inject their body when activated.
* **Sandbox + HTTP.** A drop-in ephemeral workspace provider
  (`LocalSandbox` always, `DockerSandbox` when Docker is on PATH)
  and a stdlib-only HTTP API (`lyra serve`) that exposes chat,
  stream, and the sandbox runner.
* **First-run friction killed.** `lyra setup` walks a fresh
  install through provider + key + default model in <60 s, and
  `lyra doctor --json` makes the same probes machine-readable so
  the wizard, CI, and the future Cloud Bridge all share one view
  of "what's configured?".

### Added

- **`from lyra_cli.client import LyraClient`** — embedded Python
  library for programmatic chat (`chat()`, `stream()`,
  `list_models()`, `list_skills()`, `list_sessions()`). Lazy
  session creation, typed `ChatRequest`/`ChatResponse`/`StreamEvent`
  contracts, and a context-manager lifecycle.
- **`lyra_cli.tracing.TracingHub`** with two shipped observers:
  - `LangSmithCallback` — soft-depends on `langsmith`, picks up
    `LANGSMITH_API_KEY` automatically.
  - `LangfuseCallback` — soft-depends on `langfuse`, picks up
    `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` automatically.
  Hub is safe to attach a dozen observers; an exception in one
  callback never blocks the rest.
- **`lyra setup`** — interactive first-run wizard. Probes the
  environment, picks a default provider, optionally collects the
  API key (chmod 600 on `$LYRA_HOME/.env`), and writes
  `$LYRA_HOME/settings.json` with `config_version`,
  `default_provider`, `default_model`. Driveable non-interactively
  via `--provider`, `--model`, `--api-key`, `--non-interactive`,
  `--json` for CI / docker images.
- **`lyra doctor --json`** — emits the structured probe list that
  `lyra setup` (and any future automation) consumes. Adds
  optional-integration probes for `langsmith`, `langfuse`,
  `aiosandbox`, `docker`, `rich`.
- **`lyra serve`** — stdlib WSGI HTTP API (no FastAPI dependency)
  exposing:
  - `GET /healthz` — liveness.
  - `GET /v1/models` / `GET /v1/skills` / `GET /v1/sessions`.
  - `POST /v1/chat` — synchronous chat turn.
  - `POST /v1/stream` — Server-Sent Events stream of the same.
  - `POST /v1/run` — execute a command in a fresh `LocalSandbox`
    with optional file staging, env vars, cwd, and timeout.
  Bearer-token auth via `LYRA_API_TOKEN` (off by default for
  localhost).
- **`lyra skill add <path-or-git-url>`** + **`lyra skill list`** /
  **`lyra skill remove <id>`** — local + Git installer for skill
  packs. Validates ids, refuses overwrites unless `--force`,
  honours `LYRA_HOME`, and lands packs in `~/.lyra/skills/<id>/`
  by default.
- **Progressive skills** — `progressive: true` in `SKILL.md`
  frontmatter keeps the body out of the system prompt until the
  skill activates (keyword match, explicit `USE SKILL: <id>`,
  or a `force_ids` flag). Non-progressive skills retain pre-N
  behaviour (description-only advertisement; body fetched via
  `Read` on demand).
- **Custom provider registry** — `settings.json:providers`
  accepts `slug → "package.module:Symbol"` import strings. The
  resolved class / factory is wired into `--llm <slug>` so users
  can plug in in-house LLMs without forking. Surfaced in
  `known_llm_names()` for `--help` and shell completion.
- **`lyra_cli.sandbox`** — drop-in ephemeral workspaces:
  - `LocalSandbox` — `tempfile.mkdtemp` + `subprocess.run` with
    path-escape protection. Always available.
  - `DockerSandbox` — bind-mounts the workspace into a fresh
    `docker run --rm` per command. Defaults to
    `python:3.11-slim`, `--network=none`. Soft-depends on the
    Docker CLI being on PATH.
  - `pick_sandbox(preference="auto")` — Docker → Local cascade.
- **`skills/claude-to-lyra/SKILL.md`** — reverse-bridge skill
  letting Claude Code (or any other harness) invoke a running
  `lyra serve` for second-opinion calls, cost-shifted sub-tasks,
  and sandboxed shell execution.
- **`SKILL.md` frontmatter** gains `version`, `keywords`,
  `applies_to`, `requires`, `progressive`, `extras` — fully
  backward-compatible (older packs still parse cleanly).
- **`config_version: 2`** — adds the `providers` field. Pre-v2
  configs are migrated transparently on read; the wizard always
  writes v2 going forward.

### Changed

- Bumped `lyra-cli` to `3.4.0`.
- `lyra doctor` exit code now treats *required* probes (Python
  version, `lyra-core`/`lyra-cli` packages) as hard failures and
  optional / state probes as soft, so a fresh install with no API
  keys still exits 0 — the wizard wants `doctor` to succeed.
- `render_skill_block` accepts an optional `prompt=` and
  `force_ids=` so the chat handler can drive progressive
  activation per turn. Old call sites (no kwargs) keep emitting
  description-only blocks, matching pre-N behaviour.

### Internal

- 198 new Phase N tests across `test_client_library.py`,
  `test_tracing.py`, `test_skill_command.py`, `test_sandbox.py`,
  `test_serve.py`, `test_setup_command.py`, `test_diagnostics.py`,
  `test_config_io.py`, `test_provider_registry.py`,
  `test_skill_activation.py`, plus extensions to
  `test_skills_inject.py` and `test_skill_loader.py`.
- New modules: `lyra_cli.client`, `lyra_cli.tracing`,
  `lyra_cli.sandbox`, `lyra_cli.serve`, `lyra_cli.diagnostics`,
  `lyra_cli.config_io`, `lyra_cli.provider_registry`;
  `lyra_skills.installer`, `lyra_skills.activation`.
- `lyra_skills.loader.SkillManifest` extended with the new
  frontmatter fields; old packs read in with sensible defaults
  (`progressive=False`, empty lists for the rest).

## v3.3.0 — 2026-04-27 — "Phase M: Token Observatory"

A new top-level command, **`lyra burn`**, that turns the Phase L turn
transcripts (`<repo>/.lyra/sessions/*/turns.jsonl`) into a real-time
spend, activity, and waste-pattern dashboard. Inspired by
[CodeBurn](https://github.com/getagentseal/codeburn) — we ported its
13-category classifier, retry counter, and one-shot rate, then re-aimed
the same primitives at Lyra's first-party JSONL and added Lyra-specific
extensions (4-mode taxonomy bias, slash-command awareness, and a
`R-FLASH-OVER-PRO` rule for our small/smart split).

### Added

- **`lyra burn`** — Rich snapshot dashboard. Reads
  `<repo>/.lyra/sessions/*/turns.jsonl` and renders total spend, by-model
  and by-category breakdowns, recent sessions, one-shot rate, and retry
  rate. Flags: `--since` (`7d`, `24h`, ISO date), `--until`, `--limit`,
  `--json`, `--watch`, `--refresh-pricing`.
- **`lyra burn compare <model_a> <model_b> [...]`** — side-by-side
  metrics: $/turn, avg tokens, avg latency, one-shot rate. Picks
  cheapest, fastest, and highest-1-shot winners.
- **`lyra burn optimize`** — waste-pattern detector with rules
  `R-RETRY-STREAK-3`, `R-LOW-1SHOT-RATE`, `R-EXPLORE-HEAVY`, and
  `R-FLASH-OVER-PRO`. Pluggable rule registry in
  `lyra_cli.observatory.optimize_rules`.
- **`lyra burn yield`** — git correlation. Classifies each session as
  `productive` / `reverted` / `abandoned` by checking which commits
  inside the session window survive to HEAD vs got reverted.
- New package `lyra_cli.observatory` with:
  - 13-category deterministic activity classifier (port of CodeBurn's
    `classifier.ts` plus Lyra-specific keyword and tool extensions).
  - Coding-family retry-streak heuristic so `coding → debugging` chains
    extend a single workstream while a fresh `feature` or `coding` verb
    resets it.
  - LiteLLM pricing engine with on-disk cache, ETag refresh, and a
    hardcoded fallback table for the top 20 models so `lyra burn` never
    returns `$?.??` on an airgapped checkout.

### Changed

- Bumped `lyra-cli` to `3.3.0`.

### Internal

- 87 new tests across `test_observatory_*.py`, `test_burn_*.py`, and
  `test_phase_m_smoke.py` (1,153 → 1,240 passing; yield tests skip when
  `git` is sandbox-blocked).

### Upgrade notes

- Pure-additive — no schema migrations, no JSONL writer changes. The
  `burn` subtree lives entirely on the read side.
- No new third-party dependencies (Rich, Typer, and `urllib` only).

---

## v3.2.0 — 2026-04-27 — "Claude-Code 4-mode taxonomy"

The **mode rename.** Through v3.1, Lyra carried a 5-mode REPL taxonomy
(`plan` / `build` / `run` / `explore` / `retro`) that was a holdover
from the v1.x "open-coding" era. Two production bugs forced a rethink:

1. **The screenshot bug.** Asked "how many modes do you have?", the
   model would confidently list `BUILD / RED / GREEN / REFACTOR` as
   four peer modes — leaking the TDD plugin's internal phase machine
   into the user-facing taxonomy. The system prompts only said the
   *active* mode; nothing grounded the model in the closed mode set,
   so it confabulated from training-data residue. See
   `terminals/6.txt:39-61` in the v3.1.0 dogfood log.

2. **Mode sprawl vs. Claude Code parity.** `claw-code`, `opencode`,
   and `hermes-agent` all converged on Claude Code's four modes.
   Lyra's extra `build`/`run` split (design-vs-execute) and its
   non-LLM `retro` journaling mode added cognitive overhead without
   buying clarity, and they made the parity matrix in
   `docs/feature-parity.md` harder to verify.

v3.2.0 collapses Lyra onto Claude Code's four modes — `agent` /
`plan` / `debug` / `ask` — and pins them in every system prompt so
the LLM cannot hallucinate alternatives.

### Major (breaking)

* **REPL mode taxonomy: `plan / build / run / explore / retro` →
  `agent / plan / debug / ask`.** The `_VALID_MODES` tuple in
  `lyra_cli.interactive.session` is now `("agent", "plan", "debug",
  "ask")`. The mapping:

  | v3.1 (legacy) | v3.2 (canonical) | Why                                              |
  | ------------- | ---------------- | ------------------------------------------------ |
  | `plan`        | `plan`           | Identity — read-only collaborative design.       |
  | `build`       | `agent`          | Default; full-access execution surface.          |
  | `run`         | `agent`          | Execute-after-`/approve` collapses into `agent`. |
  | `explore`     | `ask`            | Read-only Q&A; rename matches Claude Code.       |
  | `retro`       | `debug`          | Interactive troubleshooting mode (LLM-driven).   |

* **Default REPL mode: `build` → `agent`.** Fresh sessions, the
  banner, the spinner verb table, and the `lyra acp --mode` default
  all now report `agent`. Migration: nothing to do — every entry
  point that accepts a mode string runs the legacy → canonical
  remap on construction (see below).

* **`retro` is no longer a non-LLM journaling mode.** The legacy
  `retro` mode skipped `build_llm` entirely and printed
  `note logged`; that contract is retired. `/mode retro` now remaps
  to `debug` (an interactive LLM mode) and the next plain-text turn
  goes through the LLM like any other mode. Journaling moved to the
  `lyra retro` CLI subcommand.

* **System prompts now ENUMERATE all four modes.** A shared
  preamble (`_LYRA_MODE_PREAMBLE`) prefixes every mode-specific
  prompt with the verbatim list `agent, plan, debug, ask` and
  explicitly states that TDD's RED → GREEN → REFACTOR cycle is an
  **opt-in plugin, not a mode**. When the user asks "how many
  modes do you have?" the model now answers "exactly four". This
  is the structural fix for the screenshot bug — eval harnesses
  that fingerprint the prompt body need to add the preamble to
  their golden output.

* **Tab cycle order: `(build, plan, run, retro, explore)` →
  `(agent, plan, ask, debug)`.** The `_MODE_CYCLE_TAB` tuple in
  `lyra_cli.interactive.keybinds` rotates the new four. The order
  intentionally puts the two execution-capable modes (`agent`,
  `debug`) at opposite ends so a single Tab press never
  accidentally toggles between them.

### Added

* **Legacy mode aliases honoured everywhere.** `_LEGACY_MODE_REMAP`
  in `session.py` maps the old names (`build`, `run`, `explore`,
  `retro`) to the new ones at four entry points: (1) the
  `InteractiveSession` constructor (`__post_init__`), (2)
  `_TurnSnapshot` deserialisation when loading `turns.jsonl`, (3)
  the `/mode <name>` slash command, and (4) the `lyra acp --mode`
  CLI flag. So a user with `mode = "build"` in their settings.json,
  a stored `turns.jsonl` from v3.1, or muscle memory for `/mode
  explore` keeps working without manual migration. The `/mode`
  command emits a one-shot
  `'<legacy>' was renamed to '<canonical>' in v3.2.0 to match
  Claude Code's mode taxonomy` notice on first use so the user
  learns the new name.

* **`tests/test_modes_taxonomy_v32.py`** — a dedicated regression
  test pinning the entire 4-mode contract: `_VALID_MODES`, the
  default mode, `_MODE_HANDLERS`, `_MODE_SYSTEM_PROMPTS`,
  `_MODE_BLURBS`, `_MODE_CYCLE_TAB`, every system prompt's
  preamble (verbatim `"agent, plan, debug, ask"` enumeration plus
  the TDD-disclaimer), and the legacy alias remapping at every
  entry point. 19 tests, runs in 0.14s. Reproduces the screenshot
  bug as a failing test on a v3.1 codebase.

### Changed

* **`docs/feature-parity.md`** gains a "v3.2.0 — mode taxonomy
  alignment" snapshot row in the Claude-Code parity matrix.
* **`packages/lyra-cli/README.md`** mode table re-titled to
  "v3.2 modes" and updated to enumerate `agent / plan / debug /
  ask` with one-line semantics each.
* **`output.py`** banner / chat colour map gains explicit entries
  for the new modes so the visual identity (mode chip colour,
  panel border) doesn't fall back to the default for fresh
  sessions. Legacy mode names retain their colour mapping for
  backward compatibility with custom skins that pin colours by
  legacy name.
* **`driver._AGENT_VERB_BY_MODE`** spinner verb table gains
  entries for `agent` ("thinking"), `debug` ("investigating"),
  and `ask` ("looking up"), while keeping the legacy entries for
  custom skins.

### Internal

* `_LYRA_MODE_PREAMBLE` is a module-level constant in
  `session.py`; every mode prompt is `_LYRA_MODE_PREAMBLE +
  "\n" + <mode-specific tail>`. Future mode additions (or rare
  removals) only need to touch the preamble + the per-mode tail
  — the LLM's mental model of the taxonomy is centralised.
* `_handle_retro_text` is removed from `_MODE_HANDLERS`. The
  registry now pins `agent → _handle_agent_text`, `plan →
  _handle_plan_text`, `debug → _handle_debug_text`, `ask →
  _handle_ask_text` — four entries, no orphans.

### Upgrade notes

* **Test suites that hard-code legacy mode names.** Search for the
  string `"build"` in mode-related assertions; the canonical name
  is now `"agent"`. Tests that send `/mode retro` and asserted
  "note logged" will break — convert them to assert
  `session.mode == "debug"` and let the dispatcher run the LLM.
* **System prompt fingerprints.** Eval harnesses comparing the
  full system prompt string against a golden file need to
  regenerate the golden after this release; the preamble line is
  new on every mode.
* **CLI scripts passing `--mode build`.** No code change needed —
  the legacy alias is honoured, but the resolved mode is `agent`.
  Update scripts at your leisure for clarity.

### Phase L — session consumption

The mode rename made Lyra's REPL semantics match Claude Code; **Phase
L** does the same for *session ergonomics*. Through v3.1 sessions
were silently dropped to disk under `<repo>/.lyra/sessions/<id>/` but
the consumption story was incomplete: `lyra session list` only
echoed directory names, `lyra session show` was a stub, and resuming
a session re-hydrated the snapshot but lost the `_chat_history` /
`model` slots so the LLM "forgot" the conversation on `/resume`.
Phase L closes the loop with five user-facing wins and one
data-model migration, all backwards-compatible with pre-v3.2
session files on disk.

#### Added

* **`lyra --resume [ID]` / `lyra --continue` (`-c`) / `lyra --session
  ID` flags.** Top-level CLI flags, mirroring `claude --resume` /
  `claude --continue`. `--resume` alone or `--resume latest`
  attaches to the most recently modified session in the current repo;
  `--resume <id>` (or a unique prefix) picks a specific one;
  `--continue` is a shortcut for "latest"; `--session ID` resumes
  when the id exists, otherwise creates a fresh session pinned to
  that id (useful for scripting + CI). Resolution lives in a single
  helper, `_resolve_session_reference(reference, sessions_root,
  fallback=…)`, that the slash command `/resume` also calls so REPL
  and shell behaviours stay symmetric.
* **`lyra session list` — recency-sorted summary.** Walks every
  `<repo>/.lyra/sessions/<id>/turns.jsonl`, rolls up per-session
  metadata (msgs / mode / model / cost / tokens), and prints a Rich
  table with a current-session marker (●) and a fork-of hint. Pass
  `--json` for a machine-readable payload (one object per session
  with `session_id`, `name`, `msgs`, `turns`, `modified_unix`,
  `modified_iso`, `mode`, `model`, `cost_usd`, `tokens`,
  `forked_from`, `path`). `--limit N` (default 20) caps the table;
  `--limit 0` shows all.
* **`lyra session show <id|prefix|latest>` — full manifest.** The
  long-promised real implementation. Resolves `latest` or any unique
  prefix the same way `--resume` does, then dumps a manifest header
  (id, name, repo, paths, created/modified timestamps, mode, model,
  turn count, msgs, cost, tokens, fork lineage). With `--verbose`
  it walks the JSONL and prints one row per turn — *which model
  answered, how many tokens each side spent, what the turn cost,
  how long it took, and when it ran*. With `--json` it emits the
  manifest as JSON; pair with `--verbose --json` to also get the
  raw event array.
* **`lyra session delete <id|prefix>`.** Confirms by default,
  honours `--yes` for scripting. Refuses ambiguous prefixes so a
  fat-fingered `lyra session delete a` cannot wipe the wrong
  session.
* **`/history --verbose` (`-v`).** The slash command grew a verbose
  mode that walks `_turns_log` (the in-memory snapshot list) and
  renders model + tok-in + tok-out + cost-Δ + latency-ms +
  timestamp + preview per turn. Without the flag the output is the
  unchanged numbered input list — muscle memory and existing tests
  unaffected. The plain-text mirror (used by non-TTY consumers) is
  column-for-column identical to the Rich table so scripts can
  parse it.
* **Default JSONL persistence.** `driver.run` now creates and
  passes `<repo>/.lyra/sessions/` as `sessions_root` to fresh
  `InteractiveSession` instances, so every REPL run lands its
  `turns.jsonl` on disk by default — no flags required, matching
  Claude Code's "your sessions are always persisted" contract.
  Pre-v3.2 sessions written without a `sessions_root` are still
  loadable; the resume path wires one in on read.
* **`meta.json` bootstrap.** `_persist_turn` writes a minimal
  `meta.json` (`{session_id, created_at}`) on the first turn so
  `lyra session show` always has a meaningful `created_at`,
  even for sessions never explicitly named or forked. Subsequent
  writes are no-ops; user-set `name` / `forked_from` survive
  intact.

#### Changed

* **`_TurnSnapshot` carries per-turn metadata.** Six new optional
  fields — `model`, `ts`, `tokens_in`, `tokens_out`,
  `cost_delta_usd`, `latency_ms` — all default to `None` so:
    * existing positional/keyword call sites keep working,
    * pre-v3.2 `turns.jsonl` files load with all six set to
      `None` (the JSONL reader skips missing keys silently),
    * `_persist_turn` only writes the optional fields when they're
      set, so old readers don't see a flood of `null` keys.
  `_persist_chat_exchange` accepts the same optional kwargs and
  writes them to `kind: chat` records. The LLM dispatch path in
  `_chat_with_llm` now wraps each LLM call with a `_persist_with_
  metrics` helper that captures `t0 / cost_before / tokens_before
  / model` *before* the request and computes deltas after, so
  every recorded turn carries the cost / latency / model that
  produced it.
* **`/resume` restores the full conversational state.** `_cmd_
  resume` now copies `_chat_history` (so the model picks up where
  it left off — the load-bearing fix for "the LLM forgot our
  conversation"), `history` (so `/history` sees prior inputs),
  `model` / `fast_model` / `smart_model` (so the same provider
  answers), and clears the cached `_llm_provider` so the next
  call rebuilds for the resumed model. Resolves `latest` /
  prefixes via `_resolve_session_reference`.
* **Driver-level snapshot loading is gone.** Pre-v3.2,
  `driver._post_slash_actions` had a `resume` branch that loaded
  a JSON snapshot *after* `_cmd_resume` had already restored
  state from JSONL, leading to either a `FileNotFoundError` or
  a silent overwrite. The branch is now a no-op; `_cmd_resume`
  is the sole code path that restores a session.

#### Internal

* New helpers `_list_session_ids(sessions_root)` and `_resolve_
  session_reference(ref, sessions_root, *, fallback)` in
  `session.py` — single source of truth for "what's on disk?"
  and "translate a user reference to a concrete id?".
* `commands/session.py` rewritten end-to-end (was a stub). The
  test surface stays narrow: `_summarize_session(session_dir)`
  is the only seam; the four CLI commands compose around it. JSON
  output lives behind `--json` on every command for piping into
  `jq` and for tests that want structural assertions.
* `output.verbose_history_renderable(turns)` — Rich Panel
  builder for the new verbose history table; columns mirror the
  `lyra session show --verbose` table so the visual identity
  stays consistent across the slash and shell surfaces.

#### Tests

* `tests/test_phase_l_session_consumption.py` — 19 behavioural
  tests pinning the new contract: `_TurnSnapshot` field
  enrichment, `_persist_turn` JSONL backwards-compat,
  `meta.json` bootstrap idempotency, `_resolve_session_
  reference` (latest / unique prefix / ambiguous prefix /
  empty-dir fallback), `lyra session list` text + JSON
  payload, `lyra session show` (latest / unique prefix /
  unknown / verbose / JSON+events), root callback flag
  plumbing (`--continue` → `latest`, `--resume <id>`,
  `--session ID` pins both `resume_id` and `pin_session_id`),
  and `/history --verbose` plain-text mirror.
* Full `lyra-cli` suite: **1119 passed, 2 skipped, 0 regressions**
  (the lone evolve test failure on this branch is a pre-existing
  typer 0.23 / Click 8 stderr-vs-stdout compat issue unrelated
  to Phase L).

#### Upgrade notes

* **Tests that constructed `InteractiveSession` without a
  `sessions_root`.** Behaviour change: the driver now defaults
  it to `<repo>/.lyra/sessions/`, which means a `.lyra/`
  directory will be created in the test's `tmp_path`. The
  autouse `_isolate_lyra_state` fixture already chdirs into
  `tmp_path`, so this is invisible to existing tests, but
  custom integration harnesses that ran the driver against a
  read-only filesystem need to either pre-create `.lyra/` or
  pass `sessions_root=None` explicitly to opt out.
* **Tooling that reads `turns.jsonl`.** Old readers continue to
  work (every new field is optional), but downstream consumers
  that want the new metadata should expect missing keys on
  pre-v3.2 lines and treat them as "not recorded" rather than
  zero.
* **`lyra session list` JSON schema.** `cost_usd` is now a
  rounded float (6dp) and `tokens` is an integer; the field
  set is documented in the section above. Any existing
  scripts that consumed the old text-only output by line count
  should switch to `--json`.

## v3.1.0 — 2026-04-27 — "phase J: best-of-fleet research synthesis"

This release ports five high-leverage ideas selected from a survey of the
2025–2026 agent fleet: `NousResearch/hermes-agent`,
`garrytan/gbrain`, `nesquena/hermes-webui`,
`NousResearch/hermes-agent-self-evolution`, and
`FoundationAgents/MetaGPT` (hong2024metagpt; ICLR 2024 oral). The
selection criteria, the alternatives we did **not** pull, and the
research justifications all live in
[`docs/research-synthesis-phase-j.md`](docs/research-synthesis-phase-j.md).

### Added

* **Brain bundles** (Phase J.1, inspired by `garrytan/gbrain`). Curated
  installable agent presets that drop a `SOUL.md` + `policy.yaml` +
  `.lyra/commands/*.md` set into a target repo with one command. Four
  built-ins: `default`, `tdd-strict`, `research`, `ship-fast`. Public
  surface: `lyra brain list|show|install`,
  `lyra_core.brains.{BrainBundle, BrainRegistry, install_brain}`.

* **`pass^k` reliability metric** (Phase J.2, inspired by τ-bench
  `yao2024taubench`). Runs each eval case `K` times and reports both
  `pass@k` (HumanEval-style: any trial passes) and `pass^k` (τ-bench:
  *all* trials pass). The drop between the two — `reliability_gap` —
  is the silent-flakiness signal a single `pass@1` number hides.
  Public surface: `lyra evals --passk N [--json]`,
  `lyra_core.eval.{CaseTrials, PassKReport, run_passk}`.

* **Team roles + multi-agent orchestrator** (Phase J.3, inspired by
  *MetaGPT* `hong2024metagpt`). Five built-in roles
  (`pm`, `architect`, `engineer`, `reviewer`, `qa`), each carrying a
  persona, toolset binding, and Standard Operating Procedure (SOP).
  The `/team` slash command renders, plans, and assembles a multi-role
  brief in one turn. Public surface: `/team [show <name>|plan|run
  <task>]`, `lyra_core.teams.{TeamRole, TeamPlan, TeamRegistry,
  run_team_plan}`.

* **Reflexion retrospective loop** (Phase J.4, inspired by *Reflexion*
  Shinn et al. 2023). Verbal self-improvement memory: failed attempts
  emit short textual lessons that prepend to the next attempt's
  system preamble. On-disk snapshot at `<repo>/.lyra/reflexion.json`,
  tag-aware retrieval, opt-in auto-injection. Public surface:
  `/reflect [on|off|add <verdict> :: <lesson>|tag <t1,t2> <v> :: <l>|
  clear]`, `lyra_core.loop.{Reflection, ReflectionMemory,
  inject_reflections, make_reflection}`.

* **GEPA-style prompt evolver** (Phase J.5, inspired by *GEPA*
  `khattab2024gepa` and `NousResearch/hermes-agent-self-evolution`).
  Pareto-filtered reflective mutation loop that evolves a prompt
  against a small `(input, expected)` training set, tracking
  score↑ vs length↓ as the two-objective Pareto front. Default
  templated mutator works offline; pluggable LLM-backed mutator slot
  for production. Public surface: `lyra evolve --task spec.yaml
  [--generations N] [--population K] [--llm <alias>] [--json]`,
  `lyra_core.evolve.{EvolveCandidate, EvolveTrainExample, evolve,
  pareto_front, score_candidate, templated_mutator}`.

### Changed

* **`lyra --help`** now lists `evolve` and `brain` as top-level
  subcommands so the new surfaces are discoverable.
* **`docs/feature-parity.md`** gains a "v3.1.0 / Phase J — research
  synthesis" section documenting which ideas we pulled, which we
  rejected, and the citation chain for each.

### Internal

* `lyra_core.brains`, `lyra_core.teams`, `lyra_core.evolve`, and
  `lyra_core.loop.reflexion` are new modules; each ships its own
  contract test file under `packages/lyra-core/tests/`.
* `InteractiveSession` gains `reflexion_enabled: bool`,
  `_reflexion_memory: Optional[ReflectionMemory]`, and
  `_last_user_task: Optional[str]` (all default-safe; existing
  callers untouched).
* `_dispatch_plain` records the most recent prompt as
  `_last_user_task` so `/reflect add` can attach a lesson without
  the user retyping it.

### Not pulled (and why)

* **Hermes WebUI** (`nesquena/hermes-webui`) — Lyra's design centres
  on the CLI; a web UI is an out-of-tree concern best handled by a
  separate package. The relevant primitives (session JSONL stream,
  `/sessions` listing, `acp` server) are already in v3.0.0.
* **Self-evolution daemon** from `hermes-agent-self-evolution` — the
  always-on background optimiser is overkill for a single-developer
  CLI. We ship the same algorithm (GEPA) as a one-shot `lyra evolve`
  command; users pick when to run it.
* **MetaGPT's full software-company demo** — we ship the role +
  SOP + handoff primitives; we deliberately do **not** ship the
  baked-in 5-step "build a 2048 game from one sentence" autodriver.
  Users compose the pipeline themselves via `/team` so the loop
  stays observable and interruptible.

## v3.0.0 — 2026-04-27 — "general-purpose repositioning"

The **TDD posture change.** Through v2.x, Lyra advertised itself as
"TDD-first" and shipped with the gate hook armed by default. v3.0.0
repositions Lyra as a **general-purpose CLI coding agent** on par
with `claw-code`, `opencode`, and `hermes-agent`. The TDD plugin
itself is unchanged — the state machine, the gate hook, the
`/phase`, `/red-proof`, and `/tdd-gate` slashes all still ship —
but it's now **opt-in**, off by default. Out of the box `lyra` no
longer refuses Edits because no failing test exists yet. Teams who
want the historical TDD-as-kernel posture flip a single switch.

### Major (breaking)

* **`InteractiveSession.tdd_gate_enabled` defaults to `False`.**
  Previously `True`. The gate hook (`lyra_core.hooks.tdd_gate`) is
  still registered on every session — it just short-circuits when
  the flag is off. Every test that asserted `tdd_gate_enabled is
  True` on a fresh session will now read `False`; pin the flag with
  `/tdd-gate on`, `/config set tdd_gate=on`, or
  `[plugins.tdd] enabled = true` in `~/.lyra/settings.toml` to
  restore v2.x behaviour.

* **System prompts no longer say "TDD-first".** The four mode
  prompts (`_PLAN_SYSTEM_PROMPT`, `_BUILD_SYSTEM_PROMPT`,
  `_RUN_SYSTEM_PROMPT`, `_EXPLORE_SYSTEM_PROMPT`) in
  `lyra_cli.interactive.session` now describe Lyra as a "CLI-native
  coding assistant". Eval harnesses that fingerprint the prompt
  string need to be updated.

* **`/review` no longer flags TDD-off as a verifier failure.** The
  `_local_verifier_passes` helper used to fail when
  `tdd_gate_enabled` was `False`; now it only fails on real safety
  violations (yolo mention, etc.). When the gate is off, `/review`
  reports `tdd-gate: off (opt-in; /tdd-gate on to enable)` as a
  neutral status. When explicitly enabled but misconfigured, it
  still reports `on` and feeds the post-turn rubric.

* **`/ultrareview` rubric voices changed when TDD is off.** The
  default reviewer line-up is now
  `(reviewer-A correctness, reviewer-B test coverage, reviewer-C
  safety)`. When `tdd_gate_enabled is True`, the middle voice
  switches back to `reviewer-B (TDD discipline)` with the historical
  RED-test rubric. Eval harnesses asserting the v2.x string will
  need to either pin TDD on or update the assertion.

* **Banner taglines and CLI help text drop "TDD-first".** The
  ASCII-Shadow banner now reads
  `general-purpose · multi-provider · self-evolving coding agent`,
  and `lyra --help` describes Lyra as "a general-purpose,
  CLI-native coding agent harness" with a parenthetical pointing at
  the optional TDD plugin.

* **`lyra doctor` reports `tdd plugin: off (opt-in via /tdd-gate
  on)`** instead of the placeholder `tdd state: IDLE` row.

### Added

* **`/tdd-gate` is now the canonical opt-in surface.** `/tdd-gate on`
  arms the gate for the current session. `/config set tdd_gate=on`
  persists across sessions in `~/.lyra/config.yaml`. Both routes
  fully restore the v2.x posture (Edits to `src/**` blocked without
  a passing RED proof, `/review` rubric promotes the TDD discipline
  voice, etc.).

* **Phase I parity ports — `claw-code` / `opencode` / `hermes-agent`.**
  Five missing features land in v3.0.0 alongside the TDD repositioning;
  every one ships with full test coverage and is wired through the
  REPL's existing dispatch / palette / `/help` plumbing:

  * **`AskUserQuestion` LLM-callable tool** (`lyra_core.tools.
    ask_user_question.make_ask_user_question_tool`). Mirrors
    Claude Code's `AskUserQuestionTool`, opencode's `QuestionTool`,
    and hermes-agent's `clarify_tool`. Schema accepts a list of
    structured questions with optional multi-choice options,
    `allow_multiple`, and `allow_free_text`. The agent loop injects
    a callback that knows how to surface the prompt (REPL →
    prompt_toolkit, channel adapters → message bubble, headless →
    deterministic fixture). Cancellations come back as
    `{"cancelled": True, "answers": []}`. Locked surface in
    `lyra-core/tests/test_ask_user_question_tool.py`.

  * **Named toolsets registry** (`lyra_core.tools.toolsets`).
    Hermes-agent parity. Five built-in bundles ship out of the box —
    `default`, `safe` (read-only + plan), `research` (`safe` plus
    PDF/image extractors), `coding` (`safe` plus writes / patches
    / notebook edits), `ops` (everything). Custom bundles register
    at runtime via `register_toolset(name, tools)`. The
    `apply_toolset` helper returns a `ToolsetApplication` diff so
    callers see exactly which tools landed and which were requested
    but unavailable on this session.

  * **`/toolsets` slash command** (`lyra_cli.interactive.session`).
    Three forms — `/toolsets` lists every bundle with a tool
    preview; `/toolsets show <name>` enumerates the full bundle;
    `/toolsets apply <name>` records the bundle on
    `session.active_toolset` and reports `applied` / `skipped`.
    The kernel's permission stack still arbitrates per-call risk
    — toolsets are purely the *bundle* selector.

  * **`/redo` paired with `/rewind`.** Opencode's `revert/unrevert`
    parity. `InteractiveSession._redo_log` is populated by
    `rewind_one`; `redo_one` drains it and re-applies the popped
    snapshot, replaying the JSONL append so `/resume` lands on the
    post-redo state. A new plain-text turn drains the redo stack so
    a stale `/redo` can never resurrect a divergent timeline.
    Aliases: `/redo!`, `/unrewind`. Locked surface in
    `lyra-cli/tests/test_slash_redo.py`.

  * **In-REPL `/init`.** Opencode parity. Runs the same scaffolder
    as `lyra init` (writes `SOUL.md` and `.lyra/policy.yaml` from
    the packaged templates, ensures `.lyra/{plans,sessions}`,
    auto-migrates legacy state dirs) but operates on the live
    session's repo without dropping back to the shell. Idempotent
    by default; `/init force` overwrites both files. Reports next-
    step commands inline.

  * **User-authored slash commands**
    (`lyra_cli.interactive.user_commands`). Opencode parity. Drop
    a markdown file in `<repo>/.lyra/commands/<name>.md`, optionally
    with YAML-ish frontmatter (`description`, `args_hint`,
    `aliases`), and the REPL exposes `/<name>` as a first-class
    slash. The body is rendered with `{{args}}` substitution and
    dispatched through the plain-text path so the LLM sees it as
    the next user turn. Built-ins always shadow user commands so a
    file named `init.md` cannot hijack `/init`. The new
    `/user-commands` (alias `/user-cmds`) lists everything loaded;
    `/user-commands reload` re-scans the directory after edits.

### Changed (non-breaking)

* **Docs sweep.** The top-level `README.md`, `lyra-cli/README.md`,
  `lyra-core/README.md`, `docs/architecture.md`,
  `docs/system-design.md`, `docs/roadmap.md`,
  `docs/migration-to-lyra.md`, `docs/feature-parity.md`,
  `docs/tdd-discipline.md`, and `docs/blocks/08-soul-md-persona.md`
  were rewritten to describe TDD as an opt-in plugin and Lyra as a
  general-purpose harness. `migration-to-lyra.md` gained a
  dedicated "v3.0.0 — TDD becomes opt-in" section with a behaviour
  table and a one-liner restore command. `tdd-discipline.md` gained
  a v3.0.0 status preamble.

* **CLI version bump.** `lyra-cli/__init__.py` and
  `lyra-cli/pyproject.toml` are now `3.0.0`. Other workspace packages
  keep their own semvers.

### Unchanged (intentional)

* The TDD code itself (`lyra_core.tdd.state`,
  `lyra_core.hooks.tdd_gate`, `lyra_core.tdd.audit`,
  `lyra_core.verifier.cross_channel`,
  `lyra_core.verifier.evaluator_family`,
  `lyra_core.tdd.coverage`) is byte-for-byte the same as v2.7.1.
  When the plugin is enabled, the contracts and behaviour are
  identical.
* All v2.7.1 wiring — DeepSeek small/smart routing,
  `_LyraCoreLLMAdapter`, real `/compact`, real `/spawn`, OTel
  bridge, MCP autoload — is preserved.

### Test totals

* `lyra-cli`: **1049** (1016 from the TDD repositioning plus 25 new
  Phase-I tests — `/redo` round-trip, `/init` REPL scaffolder,
  `/toolsets` list/show/apply, `/user-commands` markdown loader —
  plus eight other adjustments to keep banner / brand /
  registry assertions aligned). 2 sandbox-only skips
  (`test_slash_diff.py`, git-not-available).
* `lyra-core`: **818** (796 from v2.7.1 plus 22 new Phase-I tests —
  the `AskUserQuestion` schema/cancel/validation contract and the
  hermes-style toolsets registry contract).
* `lyra-mcp`: 57 (unchanged).
* `lyra-skills`, `lyra-evals`: unchanged.
* **Total ≥ 1924 passing** (≥ 55 net-new vs v2.7.1's 1869).

## v2.7.1 — 2026-04-27 — "deepseek small/smart split + docs sweep"

Phase F of the rebuild adopts Claude Code's two-tier model pattern (Haiku
for cheap turns, Sonnet for reasoning) but on DeepSeek's catalog: Lyra
keeps a **fast** slot for chat / tool calls / summaries and a **smart**
slot for planning, subagents, cron fan-out, and post-turn review. The
defaults are `deepseek-v4-flash` (→ DeepSeek's `deepseek-chat`) and
`deepseek-v4-pro` (→ DeepSeek's `deepseek-reasoner`); both slots can be
re-pinned per session, and `/model` learned three new sub-verbs
(`fast`, `smart`, and `fast=<slug>` / `smart=<slug>`). v2.7.1 also
sweeps every shipping doc under `projects/lyra/` so version strings,
status panels, and architectural diagrams reflect the small/smart
default.

### Added

* **DeepSeek small/smart aliases.** `lyra_core.providers.aliases`
  registers `deepseek-v4-flash` / `deepseek-flash` /
  `deepseek-chat` / `deepseek-coder` → DeepSeek API slug
  `deepseek-chat`, and `deepseek-v4-pro` / `deepseek-pro` /
  `deepseek-reasoner` → API slug `deepseek-reasoner`. The
  user-facing `v4` aliases are the names that appear in `/model
  list`, README install steps, and `~/.lyra/settings.json` examples;
  the raw API slugs work too (identity aliases) so muscle memory
  from the DeepSeek dashboard always resolves.

* **`InteractiveSession.fast_model` and `.smart_model` slots.** Two
  new dataclass fields on the REPL state object, defaulting to
  `deepseek-v4-flash` and `deepseek-v4-pro`. Every code path that
  needs a model now resolves it through these slots via the new
  `_resolve_model_for_role(session, role)` helper, which maps:
  `chat` → fast, `smart` / `plan` / `spawn` / `cron` / `review` /
  `verify` / `subagent` → smart. Unknown roles fall back to
  `session.model` (the legacy "auto" pin).

* **Universal + provider-specific env stamping.** A new
  `_stamp_model_env(alias)` helper resolves the alias through the
  shared `AliasRegistry`, then sets both `HARNESS_LLM_MODEL` (the
  universal flag the `build_llm` factory reads) and the
  provider-specific override (e.g. `DEEPSEEK_MODEL`,
  `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`) so a freshly
  built provider lands on the role-correct slug regardless of which
  backend `/connect` configured.

* **In-place provider mutation.** When a session already has a
  cached `LLMProvider` instance (the common case mid-REPL),
  `_apply_role_model` mutates the provider's `model` attribute in
  place instead of rebuilding. The cache, the chat history, and the
  budget meter all stay attached; only the next `generate` /
  `stream` call talks to a different model.

* **`SubagentRunner` activates the smart slot.** The `_loop_factory`
  in `lyra_cli.interactive.session` wraps `build_llm` with an
  `_apply_role_model(session, "smart")` call so every `/spawn` (and
  every cron fan-out routed through the same factory) opens
  `deepseek-v4-pro` by default — matching Claude Code's "Sonnet for
  reasoning" pattern. Subagent budgets and trust banners are
  unchanged.

* **`/model` learned `fast` / `smart` / `fast=<slug>` /
  `smart=<slug>`.** Bare `/model fast` and `/model smart`
  temporarily switch the next turn to that slot (mutating the
  cached provider only); `/model fast=qwen-coder-flash` or
  `/model smart=claude-opus-4-5` re-pins the slot persistently for
  the remainder of the session. `/model` with no arguments now
  prints `current model`, `fast slot`, and `smart slot` together so
  the user always knows what each role is going to call. Legacy
  `/model <slug>` still pins the universal `session.model` and
  forces every role to that slug — escape hatch for anyone who
  doesn't want the split.

### Changed

* **`/status` shows both slots.** The status panel now lists the
  active model, the fast slot, the smart slot, the permission mode,
  and the budget cap together so a one-line `/status` answers "what
  is going to be called for the next chat turn vs. the next
  `/spawn`?".

* **`_ensure_llm` accepts a `role=` keyword.** Every call site that
  previously read `session.model` directly was migrated to call
  `_ensure_llm(session, role="chat")` / `role="smart"` /
  `role="plan"` / `role="spawn"` / `role="cron"` / `role="review"`.
  This is the single seam the rest of the routing logic is hung
  off — the loop, the planner, the subagent runner, the cron
  daemon, and the post-turn reviewer all share one resolver.

### Fixed

* **Chat-mode billing tests overrode the role default.** Three
  tests in `test_chat_mode_handlers.py`
  (`test_cost_uses_model_pricing`,
  `test_unknown_model_falls_back_to_default_pricing`,
  `test_streaming_bills_from_final_usage_event`) used to set
  `FakeLLM.model` directly and assume `_bill_turn` would read it;
  the new role-based router was overwriting that attribute to
  `deepseek-chat` (the fast-slot default). The tests were updated
  to set `session.fast_model` so the test's intended billing model
  flows through the same routing seam the production code uses.
  No production behaviour change; the test updates documented the
  invariant the v2.7.1 routing introduces.

### Tests

* `packages/lyra-cli/tests/test_providers_aliases.py` — extends the
  alias contract with seven new cases for the DeepSeek family
  (`v4-flash`, `flash`, `chat`, `coder`, `v4-pro`, `pro`,
  `reasoner`) and pins the provider key to `"deepseek"` for all of
  them.
* `packages/lyra-cli/tests/test_model_slot_routing.py` (new) — pins
  the default fast/smart values, the role → slot mapping table,
  the env-stamping behaviour, the in-place provider mutation, the
  extended `/model` UX, and the `_loop_factory` smart-slot
  activation for `/spawn`.
* Full regression: `lyra-cli` 1016 passed (2 sandbox-skipped),
  `lyra-core` 796 passed, `lyra-mcp` 57 passed.

### Docs

* `README.md` — status banner bumped to `v2.7.1`; new "Default
  models" subsection introducing the small/smart split with the
  exact alias-to-API-slug mapping; install step shows
  `lyra --version` reading `2.7.1`.
* `docs/feature-parity.md` — adds a v2.7.1 row to the "Honest
  Rebuild" series table; flips the v2.0.0 `cost-aware router per
  turn` cell from `v2` to `★ ✓ shipped (v2.7.1)` for the
  role-driven router.
* `docs/architecture.md` — new commitment **3.11 Small/smart model
  routing**; topology diagram annotated with the two slots.
* `docs/system-design.md` — `Agent.from_config` example shows the
  `fast` and `smart` keys; `ModelSelection` schema documents both
  slots.
* `docs/blocks/01-agent-loop.md` — "Model routing" section
  rewritten to describe the role-keyed resolver and the
  `_resolve_model_for_role` mapping table.
* `docs/blocks/02-plan-mode.md` — Planner row now reads
  "smart slot (default `deepseek-v4-pro`)".
* `docs/blocks/10-subagent-worktree.md` — "Subagent lifecycle"
  notes that `/spawn` opens the smart slot before `build_llm`.
* `docs/blocks/11-verifier-cross-channel.md` — Phase 2 LLM
  evaluator marked as "smart slot, different family from generator
  preferred".
* `docs/migration-to-lyra.md` — adds a behavioral-change row for
  the small/smart slot defaults and the `/model fast` / `smart`
  sub-verbs.
* `docs/roadmap.md` — post-v2.7 status section refreshed; v2.7.1
  marked complete with the small/smart milestone.
* `packages/lyra-cli/README.md` — full rewrite from the legacy
  Phase-2 stub: install steps, default models, `/model` cheatsheet,
  `lyra connect`, and the small/smart routing table.
* `packages/lyra-core/README.md` — adds the alias registry section
  with the DeepSeek family.

## v2.7.0 — 2026-04-27 — "production-ready honest rebuild"

Phase E of the rebuild is the release that lines the slash menu up
with what the binary actually does. Pre-v2.7, several commands carried
`(stub)`, `(planned)`, or `(Wave-X)` markers, two important commands
were silently broken at runtime, and `LifecycleBus` events emitted by
v2.6's chat handler had no observability sink. v2.7 fixes all of it,
runs the full test surface to ground (lyra-cli 997, lyra-core 796,
lyra-mcp 57), and refreshes the README + feature-parity doc to match.

### Added

* **`/evals` runs inline against bundled corpora.** The slash command
  used to print "run `lyra evals` in another shell" — technically
  correct, useless inside the REPL. v2.7 invokes
  `lyra_cli.commands.evals._run_bundled` directly and renders a
  one-line `corpus=… → P/T passed (rate=…)` summary. Pass `--full`
  for the entire JSON dump. Public corpora (`swe-bench-pro`,
  `loco-eval`) still point at the standalone `lyra evals` because
  they need the public dataset on disk.

* **`/compact` is a real heuristic compactor.** Replaces the legacy
  "halve the `tokens_used` counter" no-op with: keep the six most
  recent chat-history messages verbatim, collapse everything older
  into a single `role="system"` digest entry, recompute the token
  estimate from the surviving messages. The semantic NGC compactor
  (LLM-mediated summary) lands in a later phase; v2.7 ships the
  deterministic, no-network version that's safe to run every turn.

* **Lifecycle bus → HIR JSONL → optional OTel.** A new
  `_wire_observability_to_lifecycle` hook in
  `lyra_cli.interactive.driver` subscribes to every
  `LifecycleBus` event v2.6 added (`session_start`, `turn_start`,
  `turn_complete`, `turn_rejected`, `tool_call`, `session_end`),
  journals each as `chat.<event_name>` into the existing
  `.lyra/sessions/events.jsonl` file, and conditionally fans the
  same span into an OTel collector based on `LYRA_OTEL_COLLECTOR`:
  unset / `off` keeps just the JSONL path; `in-memory` attaches
  `lyra_core.observability.InMemoryCollector` (used by the new
  contract tests); `otel` attaches `OpenTelemetryCollector`, which
  pushes through the global `opentelemetry.trace` provider when the
  SDK is installed and degrades to a logged warning when it isn't.
  Every step is best-effort: a broken collector cannot block a
  chat turn.

* **`SubagentRunner` allocates real `git worktree`s.** When the
  parent repo is a git checkout, every `/spawn` (and every cron-job
  fan-out via the same path) now passes through
  `lyra_core.subagent.WorktreeManager.allocate(scope_id=…)`, getting
  its own branch and isolated checkout under `.lyra/worktrees/`.
  Cleanup runs in the `finally` of `run()` by default
  (`cleanup_on_exit=True`) so successful and failed runs both reap
  their worktree; a single `/spawn` cycle no longer leaks branches.
  Non-git roots and `use_git_worktree=False` keep the legacy plain
  `mkdir` fallback so tests, sandboxes, and single-file scripts
  still work.

* **`/spawn` actually constructs a working AgentLoop.** Pre-v2.7
  the factory in `_ensure_subagent_registry` did
  `AgentLoop(provider=provider)` — a kwarg the lyra-core dataclass
  doesn't accept — and imported from a non-existent
  `lyra_cli.interactive.llm_factory` module. Both bugs were
  silenced by the `try/except` in the surrounding code; every real
  `/spawn` died on first call. v2.7 introduces
  `_LyraCoreLLMAdapter` (Message-in / dict-out, single-purpose,
  ~30 LOC) so the lyra-cli provider drives the lyra-core
  subagent loop on a single LLM substrate, fixes the import path,
  and wires the registry to the public `AgentLoop(llm=, tools=,
  store=, budget=)` signature. The two loop families
  (`harness_core.AgentLoop` for one-shot `run`,
  `lyra_core.agent.AgentLoop` for hermes-pattern subagents) are
  now bridged at the boundary instead of forked across the codebase.

### Changed

* **Slash menu descriptions audited.** Every `(stub)`, `(planned)`,
  `(Wave-D)`, `(Wave-E)`, `(Wave-F)` marker that didn't match
  reality is removed. Sixteen commands updated:
  - `/compact` — "compress the context window (heuristic prune of older turns)"
  - `/ultrareview` — "multi-rubric deep review (3 verifier voices over /review)"
  - `/agents` — "live subagent registry (kill <id> to cancel a run)"
  - `/map` — "ASCII tree of every *.py under repo_root"
  - `/blame` — "git-blame annotations for a file"
  - `/pair` — "pair-programming live stream over LifecycleBus"
  - `/wiki`, `/team-onboarding`, `/replay`, `/catch-up` — Wave-E markers dropped
  - `/voice` — clarified to "advisory voice-mode flag (toggles session.voice_mode)"
  - `/phase`, `/split`, `/vote`, `/observe`, `/ide` — Wave-F markers dropped, descriptions match runtime behaviour

  The new test `test_phase_e_honest_slashes.py` asserts no command's
  description still contains `(stub)`, `(planned)`, or any
  `(Wave-?)` token — so future regressions in slash-menu honesty
  fail CI.

### Fixed

* **Module path crash on `/spawn`.** The legacy import
  `from lyra_cli.interactive.llm_factory import build_llm` is
  rewritten to `from lyra_cli.llm_factory import build_llm`. Without
  this fix, every `/spawn` after v2.6 failed inside the
  `try/except` that swallowed `ModuleNotFoundError`, leaving the
  user with a no-op slash command and no error message.

* **Kwarg mismatch on `AgentLoop` construction.** Same site: the
  legacy factory passed `provider=` to the lyra-core dataclass
  whose field is `llm=`. Even after the import was fixed, every
  spawned subagent died with `TypeError: __init__() got an
  unexpected keyword argument 'provider'`. v2.7 ships the proper
  signature (`AgentLoop(llm=adapter, tools={}, store=NoopStore(),
  budget=IterationBudget(max=8))`).

### Tests

* `packages/lyra-cli/tests/test_phase_e_honest_slashes.py` (23
  tests) pins inline `/evals`, real `/compact` history pruning, and
  the slash-menu honesty contract.
* `packages/lyra-cli/tests/test_observability_bridge.py` (4 tests)
  pins lifecycle → HIR JSONL fan-in, OTel `in-memory` collector
  attachment, robustness against buggy collectors, and disabled-by-default behaviour.
* `packages/lyra-core/tests/test_subagent_runner_worktree.py` (4
  tests) pins real `git worktree add` allocation in a git repo,
  default cleanup, plain-mkdir fallback for non-git roots, and the
  `use_git_worktree=False` opt-out.
* `packages/lyra-cli/tests/test_subagent_loop_unification.py` (4
  tests) pins the `_LyraCoreLLMAdapter` Message↔dict bridge and
  asserts the legacy `provider=` `TypeError` is gone end-to-end.
* Full regression: `lyra-cli` 997 passed, `lyra-core` 796 passed,
  `lyra-mcp` 57 passed.

### Docs

* `README.md` rewritten: status now reads "v2.7.0 Production-Ready
  Honest Rebuild — 1850 tests green" with a concrete delta from
  v2.6.0 instead of stale v2.2.0 marketing copy.
* `docs/feature-parity.md` adds a "v2.3.0 → v2.7.0 — The 'Honest
  Rebuild' series" section that names every wiring gap closed in
  the five-phase remediation, so the matrix below stops needing
  qualifiers.

## v2.6.0 — 2026-04-27 — "the agent that's wired end-to-end"

Phase D of the production-ready rebuild closes the gap between Lyra's
"orchestration" marketing and a runtime where multi-agent, scheduled,
plugin-driven, editor-integrable, and full-text-searchable behaviours
all actually exist on disk. Pre-v2.6 these primitives existed in
`lyra_core` but were unreachable from the REPL or the CLI; v2.6 wires
the last mile so a default install gets all of them with no
configuration.

### Added

* **`/spawn` dispatches a real `SubagentRunner`.** The slash command
  used to print "(spawning placeholder)"; it now allocates a
  worktree-isolated child via `lyra_core.subagents.SubagentRunner`,
  feeds it through `AgentLoop`, captures stdout/stderr, and stores
  the run record in `SubagentRegistry` so `/agents` can list state,
  parent-session linkage, exit code, and cumulative cost. Recursion
  depth is capped to protect against runaway fan-outs.

* **`CronDaemon` boots with the REPL.** A new background thread is
  started from `lyra_cli.interactive.driver` after the budget hook
  and torn down in the `finally` block. The injected runner routes
  every fired job through the same `SubagentRunner` path as
  `/spawn`, so cron jobs get the same logging, billing, and
  registry semantics. `/cron run <id>` now executes the job
  synchronously instead of stub-printing it; `/cron list` reflects
  daemon state (`scheduled` / `running` / `last_run`).

* **`LifecycleBus` events emitted from the chat handler.** The chat
  loop now publishes `session_start` (once per REPL session),
  `turn_start`, `turn_complete`, `turn_rejected`, and `tool_call`
  events through `lyra_core.hooks.lifecycle.LifecycleBus`. Every
  event is best-effort: a buggy subscriber can never break a chat
  turn. `session_end` fires from `driver.py`'s `finally` block on
  exit. The REPL also closes the SQLite session store cleanly there.

* **Plugin discovery on driver boot.** `_wire_plugins_to_lifecycle`
  in `lyra_cli.interactive.driver` reads the `lyra.plugins`
  entry-point group via `lyra_core.plugins.discover_plugins` and
  binds each plugin's hooks (`on_session_start`, `on_turn_start`,
  `on_turn_complete`, `on_turn_rejected`, `on_tool_call`,
  `on_session_end`, or universal `on_lifecycle_event`) to the
  bus. Every binding is wrapped in `try/except` so a third-party
  plugin can crash without taking the user's REPL down with it. To
  resolve a long-standing namespace collision, the `Plugin`
  protocol, `discover_plugins`, and `fire` were moved from the
  legacy `lyra_core/plugins.py` module into the `lyra_core/plugins`
  package (new `lyra_core/plugins/discovery.py`) and re-exported
  from `__init__.py`. The old top-level `plugins.py` is deleted.

* **`lyra acp` subcommand** registered in `lyra_cli.__main__`. The
  new `lyra_cli.commands.acp` Typer module implements an
  Agent-Client-Protocol JSON-RPC 2.0 server over stdio (same idea
  as Claude Code's editor bridge). It currently handles
  `initialize` (returns version + capabilities), `sendUserMessage`
  (routes through `_chat_with_llm`, materialises a `LifecycleBus`
  in the same shape as the REPL so plugins observe both surfaces
  symmetrically), and `cancel`. `--once` runs a single request and
  exits, suitable for CI smoke tests; default is a long-lived
  serve loop that streams responses line-by-line on stdout.

* **`/search` lazy-boots a default FTS5 store.** `_cmd_search` no
  longer requires a caller-supplied `search_fn` — on first use it
  calls `_ensure_default_search_fn(session)`, which materialises a
  SQLite + FTS5 `lyra_core.sessions.store.SessionStore` at
  `<repo>/.lyra/sessions.sqlite`, back-fills it from any existing
  `turns.jsonl` files, and binds `search_fn` to
  `SessionStore.search_messages`. New chat exchanges are
  live-indexed via `_index_exchange_in_store` from
  `_persist_chat_exchange`, so anything you say or hear becomes
  searchable on the next turn. The driver pre-warms the store at
  boot and closes it in the `finally` block.

### Changed

* **`/search` UX contract.** Previously, `/search` without an
  injected `search_fn` reported "search unavailable / not wired".
  As of v2.6 it silently boots the default FTS5 store and reports
  `(no matches for '<query>')` only when there genuinely are
  none. This is a deliberate behaviour change; the legacy
  contract test in
  `packages/lyra-cli/tests/test_session_search_slash_contract.py`
  has been updated to
  `test_search_without_search_fn_lazy_boots_default_store`.

### Internal

* `lyra_core/plugins/` is now a proper subpackage. The old
  `lyra_core/plugins.py` file is removed and `Plugin`,
  `discover_plugins`, `fire` are re-exported from
  `lyra_core/plugins/__init__.py`. Anything importing
  `from lyra_core.plugins import Plugin, discover_plugins`
  continues to work; consumers reaching into
  `lyra_core.plugins` as a module object will need to switch
  to the package form (none in-tree).

### Tests

* `packages/lyra-cli/tests/test_lifecycle_emit.py` (new) covers
  `session_start`, `turn_start`, `turn_complete`, `turn_rejected`,
  `tool_call` emission and verifies entry-point plugin wiring.
* `packages/lyra-cli/tests/test_cli_acp_command.py` (new) drives
  `lyra acp` through `typer.testing.CliRunner` and asserts both
  `--once` mode and the long-lived serve loop produce well-formed
  JSON-RPC.
* `packages/lyra-cli/tests/test_search_fts5_default.py` (new)
  exercises lazy default boot, historical `turns.jsonl` import,
  live indexing, and the `/search` happy path.
* `packages/lyra-cli/tests/test_session_search_slash_contract.py`
  updated to reflect the new contract.

Full regression: 964 lyra-cli tests pass (2 skipped because git
isn't on PATH in the sandbox), 792 lyra-core tests pass, 57
lyra-mcp tests pass.

## v2.5.0 — 2026-04-27 — "the agent that actually speaks MCP"

Phase C of the production-ready rebuild closes the gap between Lyra's
long-standing MCP marketing and the reality on disk. Pre-v2.5 the
`/mcp` slash and the `lyra_mcp.client` package only handled the *URL*
trust-registry path — Claude Code's stdio child-process model (the
one every real MCP server actually ships) was a TODO comment. v2.5
ships the missing layer end-to-end:

1. **Real stdio JSON-RPC transport** (`StdioMCPTransport`) with full
   `initialize` handshake, ID-correlated request/response, reader
   threads, and idempotent shutdown. Backed by 14 unit tests that
   exercise a real subprocess running a pure-Python fake server.
2. **`~/.lyra/mcp.json` autoload** (user-global + project-local with
   project-wins precedence), exposed through a new `lyra mcp`
   Typer subcommand (`list`/`add`/`remove`/`doctor`) and an
   extended `/mcp` REPL slash (`connect`/`disconnect`/`tools`/
   `reload`).
3. **MCP tools wired into the chat loop.** Servers connected with
   `/mcp connect <name>` automatically expose their `tools/list`
   output to the chat tool loop as `mcp__<server>__<tool>` schemas;
   when the LLM proposes one, the loop dispatches it to the right
   transport, renders a tool card, and feeds the result back in for
   the next hop. The Phase B approval cache and renderer apply
   transparently — you get the same "user denied X" semantics
   regardless of whether the tool came from the local registry or
   an MCP server.

The cumulative effect: a fresh `lyra` install with `npx -y
@modelcontextprotocol/server-filesystem /tmp` declared in
`~/.lyra/mcp.json` now actually lets the model read files through
that server, not just *advertise* the capability in the help text.

### Added

* **`lyra_mcp.client.stdio` (new module).** `StdioMCPTransport.start()`
  spawns a subprocess and performs a JSON-RPC `initialize` /
  `notifications/initialized` handshake, then runs as a long-lived
  request/response peer. Highlights:
  - Reader thread parses newline-delimited JSON-RPC frames, routes
    responses to per-id `threading.Event`-backed waiters, and
    surfaces stderr through a tail buffer (`last_stderr`) for
    diagnostics.
  - `list_tools()` and `call_tool(name, args, *, timeout=…)` are
    synchronous wrappers around `_request("tools/list" | "tools/call")`.
  - `close()` is idempotent: SIGTERM, then SIGKILL after
    `grace_period_s`, so REPL exit can never leave npx zombies.
  - `MCPHandshakeError` (raised from `start()` if the child never
    answers `initialize`) and `MCPTransportError` (catch-all for
    JSON-RPC failures) give callers tight error shapes.

* **`lyra_mcp.client.config` (new module).** Implements
  `load_mcp_config()` over `default_config_paths(repo_root)` =
  (`~/.lyra/mcp.json`, `<repo>/.lyra/mcp.json`) with project-wins
  precedence. Tolerates missing files, malformed JSON, and bad
  entries (each one becomes an `MCPLoadIssue` so `lyra mcp doctor`
  can surface the problem). `add_user_mcp_server()` /
  `remove_user_mcp_server()` provide atomic write helpers backing
  the new `lyra mcp add` / `lyra mcp remove` subcommands; both are
  idempotent.

* **`lyra_mcp.client.toolspec` (new module).** Translates MCP
  `tools/list` payloads into Lyra chat-loop schemas with names of
  the form `mcp__<server>__<tool>` (matches Claude Code / Codex
  /open-claw conventions). `MCPToolDispatcher` routes calls back to
  the right transport; `render_mcp_result_for_chat` flattens the
  typed `content` array into a single string the loop can pass to
  the next LLM hop.

* **`lyra mcp` Typer subcommand** registered in `lyra_cli/__main__`.
  Five subcommands:
  - `lyra mcp list [--json]` — table or JSON of every configured
    server, plus any load issues.
  - `lyra mcp add <name> --command <cmd> [--arg …] [--env K=V …]
    [--cwd <path>] [--trust first-party|third-party]
    [--config <path>]` — appends or replaces an entry.
  - `lyra mcp remove <name> [--config <path>]` — idempotent delete.
  - `lyra mcp doctor` — `shutil.which()` health check; non-zero
    exit when an executable is missing, so CI gates work.

* **Extended `/mcp` REPL slash** in `lyra_cli.interactive.session`:
  - `/mcp list` now merges URL-registered servers (Wave-D legacy)
    and stdio-autoloaded ones into a single output, marking each
    stdio server `[connected]` or `[idle]`.
  - `/mcp connect <name>` lazily spawns the child, runs the
    handshake, and prints the advertised tool names.
  - `/mcp disconnect <name>` cleanly closes the cached transport.
  - `/mcp tools <name>` shows the descriptions for every advertised
    tool (auto-spawns if needed).
  - `/mcp reload` re-reads the config files without restarting the
    REPL — handy when you edit `~/.lyra/mcp.json` mid-session.

* **REPL boot autoload** in `lyra_cli.interactive.driver`. After
  `_apply_budget_settings`, `autoload_mcp_servers()` populates
  `session.mcp_servers` from disk and the REPL's exit hook calls
  `shutdown_all_mcp_clients()` so every spawned child is reaped.
  Honours `LYRA_DISABLE_MCP_AUTOLOAD=1` for paranoid CI / test
  isolation.

* **MCP-aware chat tool loop.** `chat_tools.collect_mcp_tool_specs()`
  returns the union of tool schemas advertised by every connected
  MCP server, plus a transport map keyed by Lyra-side name. The
  chat handler in `_chat_with_tool_loop` calls this before each
  loop and passes the result through `mcp_schemas=` /
  `mcp_transports=`. Inside the loop, names matching
  `mcp__<server>__<tool>` route to MCP — every other call goes to
  the local registry as before. Errors during MCP dispatch turn
  into `is_error=True` ToolEvents so the renderer surfaces them
  alongside regular tool failures.

* **`InteractiveSession` fields:** `mcp_servers: list[Any]`,
  `_mcp_clients: dict[str, Any]`, `mcp_autospawn: bool = True`,
  `_mcp_load_issues: list[Any]`. None of them affect users who
  never configure MCP.

### Changed

* `lyra_mcp.client.__init__` now exports the full Phase C surface
  (`StdioMCPTransport`, `MCPHandshakeError`, `MCPTransportError`,
  `MCPServerConfig`, `MCPLoadIssue`, `MCPLoadResult`,
  `add_user_mcp_server`, `default_config_paths`, `load_mcp_config`,
  `load_mcp_config_from`, `remove_user_mcp_server`,
  `MCPToolDispatcher`, `MCPToolEntry`, `normalise_mcp_tools`,
  `parse_lyra_mcp_name`, `render_mcp_result_for_chat`).
* `lyra-cli` now declares `lyra-mcp` as a hard dependency in
  `pyproject.toml` (was previously importable only when installed
  out-of-band). Brings the marquee MCP UX into the default install.

### Tests

* **+57** total in `packages/lyra-mcp/tests/`:
  - `test_mcp_stdio.py` (14): handshake, tool list/call, JSON-RPC
    error propagation, ID monotonicity, idempotent close,
    context-manager exit.
  - `test_mcp_config.py` (11): file precedence, malformed JSON,
    bad entry shapes, add/remove round-trip, env override.
  - `test_mcp_toolspec.py` (18): name normalisation, dispatcher
    routing, error rendering, JSON fallback.
* **+31** in `packages/lyra-cli/tests/`:
  - `test_mcp_autoload.py` (18): autoload, find/ensure caching,
    shutdown, every `/mcp` slash subcommand path.
  - `test_chat_tools_mcp.py` (6): `collect_mcp_tool_specs` filters,
    end-to-end loop with MCP transports, error propagation.
  - `test_cli_mcp_command.py` (7): `lyra mcp` Typer surface
    (list/add/remove/doctor + JSON output).

Total package suites:

* `lyra-cli`: 943 tests passing (was 912 in v2.4.0).
* `lyra-mcp`: 57 tests passing (was 14 — Phase C took it from
  bare-bones to production-ready).
* Combined `lyra-cli` + `lyra-mcp`: **1,000 / 1,000 passing**.

### Migration notes

* If you already had `~/.lyra/mcp.json` from a hand-rolled experiment
  — keep it. The format is identical to Claude Code / Codex.
* `LYRA_DISABLE_MCP_AUTOLOAD=1` is a safety valve for environments
  that don't want any subprocess management at REPL boot.
* The legacy URL-mode `/mcp register …` / `/mcp trust …` paths are
  unchanged. They coexist with the new stdio path in the same
  `/mcp list` output.

## v2.4.0 — 2026-04-27 — "the agent that actually edits, knows skills, and remembers lessons"

Phase B of the production-ready rebuild: the chat handler stops being
a pure "wrap an LLM" passthrough and becomes an **honest agent**.
Three structural additions land together because they share a single
contract — every chat turn now goes through a tool-aware loop, sees a
skill catalogue, and is primed with relevant memory before the LLM
ever opens its mouth.

### Added

- **Chat-mode tool loop (B.1 + B.2 + B.3).** New
  ``lyra_cli.interactive.chat_tools`` module. Every conversational
  turn now runs through a real *think → act → observe* loop:
  - The LLM sees a curated set of file-system tools (``Read``,
    ``Glob``, ``Grep``, ``Edit``, ``Write``) sandboxed to the repo
    root via ``ToolRegistry.register_builtin_tools``.
  - Tool calls dispatch in-process; results stream back as
    ``ToolMessage``s for a follow-up LLM hop, and the loop continues
    until the model emits a no-tool-calls answer or hits
    ``max_steps`` (default 8 — protection against runaway).
  - Each hop is billed individually via ``_bill_turn`` so a 5-step
    tool run shows the *real* dollar cost, not just the last call.
  - User consent flows through ``ToolApprovalCache``: ``yolo`` mode
    skips prompts, ``normal`` and ``strict`` ask once per
    (tool, args) and remember the decision.
  - Tool calls render as Rich panels in the REPL with
    arguments, abridged results, and approval/denial state — the
    user never wonders "what just ran?".
- **SKILL.md injection (B.4).** New
  ``lyra_cli.interactive.skills_inject`` module. Every chat turn
  prepends a compact "## Available skills" block to the system
  prompt, listing every ``SKILL.md`` discovered across:
  - the packaged ``lyra_skills.packs/`` (atomic-skills, karpathy
    heuristics, safety triage, the 7-phase TDD sprint),
  - ``~/.lyra/skills/`` (user-global), and
  - ``<repo>/.lyra/skills/`` (project-local, top precedence).
  The block is bounded (default 32 entries, 240-char per-line cap)
  so a user with hundreds of skills can't drown the prompt budget.
  New ``/skills`` slash command:
  - ``/skills`` — status + the four shipped pack categories
    (preserves the v0.1.0 contract).
  - ``/skills list`` — every discovered SKILL.md.
  - ``/skills on`` / ``off`` — toggle the per-session injection.
  - ``/skills reload`` — invalidate the cache after editing a
    SKILL.md.
- **Memory injection (B.5).** New
  ``lyra_cli.interactive.memory_inject`` module. Every chat turn
  also prepends a "## Relevant memory" block when either store
  contains relevant material:
  - The project-local SQLite ``ProceduralMemory`` (FTS5-backed) at
    ``<repo>/.lyra/memory/procedural.sqlite`` is queried with
    tokens extracted from the user's input.
  - The in-process ``ReasoningBank`` (positive lessons +
    *anti-skill* failure distillations from
    arXiv:2509.25140) is recalled with the same signature; lessons
    surface tagged ``[do]`` or ``[avoid]`` so the LLM can reason
    about them differently.
  - The block stays empty when no store has anything to say — no
    dangling header.
  - New ``/memory`` slash command exposes ``status``, ``on/off``,
    ``search <q>``, and ``reload``.

### Changed

- ``InteractiveSession`` gains six new fields:
  ``chat_tools_enabled``, ``skills_inject_enabled``,
  ``memory_inject_enabled``, ``reasoning_bank``,
  ``_chat_tool_registry``, and ``_procedural_memory`` —
  see the inline docstrings in ``session.py`` for cache and
  precedence semantics.
- ``_chat_with_llm`` is now a three-phase function: skills →
  memory → tool-loop. Streaming is still available on tool-free
  turns; tool-bearing turns deliberately serialise the final
  answer because partial-tool-call SSE is a rendering hazard.
- The legacy ``/skills`` (which only listed pack categories) is
  superseded by the v2.4.0 command. Pack-category enumeration is
  preserved as the no-args default *and* via ``/skills packs`` so
  every existing test and habit still works.

### Tests

- ``test_chat_tool_loop.py`` (11 cases): scripted ``ToolingFakeLLM``
  drives the loop through single-call, multi-call, max-steps,
  approval/denial, ``yolo`` mode, per-hop billing, and
  end-to-end ``InteractiveSession`` integration.
- ``test_skills_inject.py`` (17 cases): discovery precedence,
  rendering caps, malformed-SKILL.md tolerance, system-prompt
  augmentation caching, and every ``/skills`` subcommand.
- ``test_memory_inject.py`` (21 cases): token extraction,
  procedural + reasoning bank rendering, polarity tags, search
  failure swallowing, and every ``/memory`` subcommand.
- Full sweep: lyra-cli **912 passed**, lyra-core **792 passed**,
  lyra-skills **19 passed** (1,723 total).

### Migration

- No breaking changes for users staying on v2.3 mock providers.
- Real-LLM users gain the tool loop automatically; flip
  ``/tools chat off`` to revert to pure-conversation behaviour.
- Skill-rich projects: drop ``SKILL.md`` files into
  ``.lyra/skills/<id>/`` and they show up next turn. ``/skills
  reload`` if you edit a description live.

## v2.3.0 — 2026-04-27 — "every provider bills, every key works, every reload remembers"

The post-v2.2.4 audit uncovered 34 features that Lyra advertised but
didn't fully wire — chiefly around provider correctness for accurate
billing and conversational continuity. Phase A of the production-ready
push (this release) closes the **Tier-1 silent-lie** items: every LLM
provider now reports real token usage, the cascade resolves Bedrock /
Vertex / Copilot end-to-end, streaming SSE without a final ``usage``
chunk no longer bills $0, the price table covers the 2025-2026 model
generations, and a ``lyra resume`` actually rehydrates your last chat
instead of starting over with "who are you?".

### Added — first-class usage capture across every provider

- ``providers/anthropic.py``: new ``LyraAnthropicLLM`` subclass of
  ``harness_core.models.AnthropicLLM`` that *spies* on the SDK's
  ``client.messages.create`` to capture the raw response, extracts
  ``usage.input_tokens`` / ``usage.output_tokens``, and parks them on
  ``self.last_usage`` after every turn. The spy restores the original
  method in a ``finally`` so subsequent calls (and parallel sessions)
  see a clean SDK. Done in lyra-cli rather than upstream so other
  monorepo consumers of ``harness_core`` aren't perturbed.
- ``providers/bedrock.py``: ``_record_usage`` reads the AWS
  Converse API ``usage`` block (``inputTokens`` / ``outputTokens`` /
  ``totalTokens``) and maps to the OpenAI-style key trio Lyra's billing
  consumes. Wired into ``generate``.
- ``providers/copilot.py``: ``_record_usage`` reads the OpenAI-shaped
  ``usage`` block GitHub Copilot returns; same canonical key trio.
- ``providers/gemini.py``: ``_record_usage`` parses Google's
  ``usageMetadata`` (``promptTokenCount`` /
  ``candidatesTokenCount`` / ``totalTokenCount``).
- ``providers/ollama.py``: ``_record_usage`` reads the
  ``prompt_eval_count`` / ``eval_count`` pair Ollama emits and
  derives ``total_tokens``. Local model billing now reflects real
  token throughput rather than zero.
- ``providers/vertex.py``: ``_record_usage`` parses
  ``response.usage_metadata`` from the Vertex AI Gemini SDK. Same
  canonical key trio surfaced.

### Fixed — Vertex tools= silently dropped on the wire

- Before this release, ``GeminiVertexLLM.generate`` accepted a
  ``tools=`` kwarg per the ``LLMProvider`` interface but never
  forwarded it to ``GenerativeModel.generate_content`` — every Lyra
  tool call routed through Vertex was silently demoted to a plain
  text turn. ``vertex.py`` now translates Lyra's OpenAI-shape tool
  list to the Vertex ``Tool``/``FunctionDeclaration`` schema via
  ``_tool_to_vertex`` and threads it through the SDK call. Function
  calls in responses are converted back to ``tool_calls`` on the
  reply ``Message`` via ``_response_to_msg``.

### Fixed — streaming SSE without a final usage block no longer bills $0

- ``OpenAICompatibleLLM.stream`` now tracks ``streamed_chars`` and
  ``prompt_chars`` in addition to yielding text deltas. A ``finally``
  block runs after the generator exhausts: if no final ``usage``
  frame populated ``self.last_usage``, the backstop synthesises an
  estimate using a 4-chars-per-token heuristic and stamps
  ``estimated: True`` so dashboards can distinguish real from
  estimated rows. This catches OpenRouter, LM Studio in some
  configurations, and any provider that gates final-usage behind a
  flag we haven't sent.

### Added — Bedrock, Vertex, Copilot wired into ``build_llm`` and ``lyra connect``

- ``llm_factory.build_llm`` and ``describe_selection`` gain explicit
  ``"bedrock"``, ``"vertex"``, ``"copilot"`` branches; previously
  these required arcane env-var sniffing or a manual import.
- ``llm_factory._DOTENV_KEYS`` extended with ``AWS_ACCESS_KEY_ID``,
  ``AWS_SECRET_ACCESS_KEY``, ``AWS_PROFILE``,
  ``GOOGLE_APPLICATION_CREDENTIALS``, ``GOOGLE_CLOUD_PROJECT``,
  ``VERTEX_PROJECT``, ``VERTEX_LOCATION``, ``BEDROCK_MODEL``,
  ``GITHUB_TOKEN``, ``COPILOT_MODEL`` so ``.env`` and
  ``~/.lyra/auth.json`` hydration paths now feed every supported
  cloud auth flow.
- ``llm_factory._AUTHJSON_PROVIDER_TO_ENV`` maps
  ``"bedrock" → AWS_ACCESS_KEY_ID``,
  ``"vertex" → GOOGLE_APPLICATION_CREDENTIALS``,
  ``"copilot" → GITHUB_TOKEN`` so ``lyra connect bedrock --api-key
  AKIA…`` round-trips through the long-lived store.
- ``commands/connect.py`` ``_SUPPORTED`` now lists ``bedrock``,
  ``vertex``, ``copilot``. A new ``_PREFLIGHT_DEFERRED`` set causes
  ``lyra connect`` to skip the generic HTTP preflight for these
  three (their auth flows — AWS credential chain, Google ADC,
  GitHub OAuth token exchange — can't be probed with a single
  ``GET /v1/models`` call) and prints "preflight skipped — will
  validate on first chat" so the user knows it's deliberate.

### Added — stdlib-only HTTP shim for Copilot

- ``providers/_urllib_http.py`` introduces ``StdlibHTTP``: a minimal
  duck-typed ``request(method, url, headers=, json=, timeout=)``
  client backed by ``urllib.request`` that returns an object with
  ``status_code``, ``text``, and ``json()`` — exactly the surface
  ``CopilotLLM`` expects. This lets Copilot work without pulling
  ``requests``/``httpx`` into Lyra's core install footprint, keeping
  the ``pip install lyra-cli`` payload small for users who never
  use Copilot.

### Changed — pricing table now covers Grok, Codestral, Qwen-Plus, Llama-3.3 …

- ``interactive/budget._DEFAULT_PRICES_PER_MTOK`` extended with
  pricing for **47 additional models** spanning OpenAI (gpt-4.1-nano,
  gpt-5-mini, o3-mini, o1, o1-mini), Anthropic
  (claude-haiku-4-5, claude-sonnet-4-5), Qwen (qwen-3-max, qwen-plus,
  qwen-turbo, qwen-max, qwen-vl-plus), Gemini
  (gemini-2.5-flash-lite, gemini-2.0-flash, gemini-1.5-pro,
  gemini-1.5-flash), xAI Grok (grok-4, grok-4-mini, grok-3,
  grok-3-mini, grok-2, grok-2-mini), Mistral
  (codestral-latest, codestral-2405, mistral-large/medium/small/nemo,
  ministral-3b, ministral-8b), Groq (llama-3.3-70b-versatile,
  llama-3.1-* lineup, mixtral-8x7b-32768), Cerebras
  (llama-3.3-70b-cerebras, llama3.1-8b-cerebras), and local LM Studio
  / Ollama models (llama-3.2-3b-instruct, qwen-2.5-coder:1.5b).
  Previously these models silently fell back to ``DEFAULT_RATE`` and
  under- or over-billed by 30-90% per turn.

### Added — chat history actually survives ``lyra resume``

- ``InteractiveSession`` now persists every user-assistant exchange to
  ``turns.jsonl`` as a new ``{"kind": "chat", "turn": N, "user":
  "…", "assistant": "…"}`` record alongside the existing turn
  snapshots. Done in both branches of ``_chat_with_llm`` (streaming
  and non-streaming) via ``_persist_chat_exchange``.
- ``resume_session`` now scans ``turns.jsonl`` for both
  ``_TurnSnapshot`` and ``"kind": "chat"`` records, reconstructs
  ``_chat_history`` from the latter, and trims to
  ``_CHAT_HISTORY_TURNS`` to keep the system prompt under context-
  window pressure. Result: ``lyra resume`` continues your previous
  conversation in full — the LLM sees the same scrollback you do —
  instead of greeting you with "I'm a new instance".
- ``_truncate_persisted_log_by_one`` (the ``/redo`` and ``/edit``
  rewind primitive) now atomically removes both the latest turn
  snapshot **and** the trailing chat record, so rewinding once
  doesn't desync the persisted history from the in-memory one.

### Test infrastructure

- ``packages/lyra-cli/tests/conftest.py`` (new): autouse fixture
  ``_isolate_lyra_state`` redirects ``LYRA_HOME`` to a per-test
  temporary directory and ``chdir``s into it. Without this every
  CI/dev test was implicitly inheriting the developer's real
  ``~/.lyra/auth.json``, which made ``test_build_llm_auto_raises_no_provider_configured…``
  flake whenever a key was on disk.
- ``packages/lyra-core/pyproject.toml`` now sets
  ``python_functions = "test_*"`` to match the rest of the
  monorepo, fixing a collection bug where pytest's default
  ``test*`` pattern picked up the ``tests_for_edit`` helper in
  ``lyra_core.tdd.impact_map`` and tried to run it as a test.

### Known limitations (intentional)

- The streaming usage backstop's 4-chars-per-token estimate is
  deliberately conservative; CJK / emoji-heavy turns will under-
  estimate. The fix is wire-side: send ``stream_options
  .include_usage=true`` to providers that respect it. The backstop
  is a safety net, not a substitute.
- ``last_usage`` for Anthropic via ``LyraAnthropicLLM`` requires the
  upstream SDK to expose ``client.messages.create``. This is stable
  in ``anthropic>=0.34``; older SDK versions fall back to
  ``last_usage = {}`` and the budget meter records zero tokens —
  the existing pre-2.3 behaviour.

## v2.2.4 — 2026-04-26 — "stream the answer"

The chat handler from v2.2.1 finally talks to the LLM, but it sat
silent until the *whole* reply landed and only then re-rendered the
panel. Long answers (~10s on Claude / GPT-5, longer on reasoning
tiers) felt like Lyra had hung. v2.2.4 streams every reply
token-by-token via Rich Live, so the panel grows under your prompt
the same way `claude` and `chatgpt --tui` do.

### Added — provider-side streaming

- ``OpenAICompatibleLLM.stream(messages, ...)`` — the streaming peer
  of ``generate``. Posts to ``/chat/completions`` with
  ``stream=true`` and ``stream_options.include_usage=true``, parses
  SSE frames, yields plain ``str`` text deltas, and parks the final
  ``usage`` block on ``last_usage`` so :func:`_bill_turn` (v2.2.2)
  picks it up the moment the iterator finishes. Stdlib-only — no
  new dependencies.
- This single method covers **DeepSeek, OpenAI, Qwen, Groq,
  Cerebras, Mistral, OpenRouter, xAI / Grok, LM Studio** — every
  preset in :mod:`openai_compatible`. Anthropic, Gemini, Ollama
  and the mock provider don't yet implement ``stream``; the chat
  handler falls back to non-streaming ``generate`` for them
  automatically — no error, just no live deltas.
- The SSE parser handles CRLF / LF, ``data:`` with or without the
  space prefix, ``: keepalive`` heartbeats (OpenRouter), malformed
  individual frames (skipped, not fatal), and always closes the
  HTTP response when the iterator exhausts so file descriptors
  don't leak across many turns.

### Added — REPL surface

- ``InteractiveSession`` gains ``_console`` (the Rich console the
  driver wires up) and ``_streaming_enabled`` (gated to TTY). When
  both are set *and* the active provider has a callable ``stream``
  attribute, the chat handler picks the streaming branch. All
  three conditions failing falls back to the v2.2.3 ``generate``
  path — no behaviour change for piped / scripted runs.
- ``/stream [on|off|status]`` slash to toggle streaming live without
  restarting. Refuses ``/stream on`` when no Rich console is
  attached (i.e. plain mode) instead of silently flipping a flag
  that can't paint.
- ``LYRA_NO_STREAM=1`` shell env to disable streaming at boot —
  useful for terminal multiplexers and older Windows consoles
  where Rich Live repaints poorly.

### Changed — chat handler

- ``_chat_with_llm`` now branches on streaming-vs-not. Streaming:
  opens a ``rich.live.Live`` panel, drives it with each delta from
  ``provider.stream``, captures usage from ``last_usage`` post-
  stream, bills via ``_bill_turn``, appends the assembled reply to
  ``_chat_history``. Non-streaming: identical to v2.2.3.
- A streaming failure mid-call (``ConnectionResetError``,
  ``TimeoutError``, malformed SSE) keeps whatever text already
  painted on screen, appends a ``[stream interrupted: ...]``
  marker, and **transparently retries via** ``generate`` so the
  user still gets an answer. Both attempts share the same chat
  history slot — no double-billing.
- The mode-handler factory (``_build_chat_handler``) checks
  ``session._stream_just_drew`` and returns
  ``CommandResult(output="", renderable=None)`` when the panel is
  already on screen, so the driver doesn't repaint the same reply
  twice.

### Changed — driver

- ``driver.run`` flips ``session._streaming_enabled = True`` for
  TTY sessions (``sys.stdout.isatty() and not LYRA_NO_STREAM``) and
  attaches the Rich console to the session. Plain / piped sessions
  stay non-streaming.

### Tests

- ``tests/test_openai_compatible_streaming.py`` — 9 new tests:
  delta order + assembly, final-chunk usage capture, wire payload
  has ``stream=true`` + ``include_usage=true``, ``Accept:
  text/event-stream`` header, comment-line skipping, malformed-
  chunk tolerance, response close on exhaustion,
  ``ProviderHTTPError`` on 4xx, ``last_usage`` reset between calls.
- ``tests/test_chat_mode_handlers.py`` — 9 new tests: panels grow
  per-delta, billing from final usage event, history records the
  assembled reply, fallback when provider lacks ``stream``,
  fallback when ``_streaming_enabled=False``, fallback after a
  mid-stream exception, ``/stream off`` flips state, ``/stream
  status`` reports state, ``/stream on`` refuses without a console.

### How it looks

```text
> hello
╭─ build ─────────────────────────────────────────────╮
│                                                     │
│   Hello! How can I help you build something today?  │  ← grows token-by-token
│                                                     │
╰─────────────────────────────────────────────────────╯
```

Type ``/stream off`` if your terminal redraws poorly; ``LYRA_NO_STREAM=1
lyra`` to make that the default.

The full regression now reads **860 passing, 2 skipped** in
``lyra-cli`` (up from 841), with no regressions in ``lyra-core``.

---

## v2.2.3 — 2026-04-26 — "automatic budget"

The cost meter from v2.2.2 finally records spend, but the user still
had to type ``/budget set 5`` at the start of every session before
that record-keeping turned into a real guardrail. v2.2.3 makes the
budget configuration **persistent, auto-applied, and enforcing**.

### Added — persistent budget configuration

- ``lyra_core.auth.store.load_budget()`` / ``save_budget(...)`` /
  ``clear_budget()``. Budget settings live in the same 0600
  ``~/.lyra/auth.json`` (under a top-level ``budget`` block) so a
  single file holds everything that needs to survive REPL restarts.
  Schema:

  ```json
  {
    "providers": {...},
    "budget": {
      "cap_usd": 5.0,
      "alert_pct": 80.0,
      "auto_stop": true
    }
  }
  ```

- ``--budget <usd>`` CLI flag on the top-level ``lyra`` command for
  one-shot caps that don't touch disk
  (e.g. ``lyra --budget 0.50``).

- ``InteractiveSession.budget_auto_stop`` field. When ``True`` (the
  default) the chat handler refuses new LLM calls once the meter
  reports ``EXCEEDED``. Toggle persists in ``auth.json`` so the
  preference follows you between sessions.

### Added — REPL surface

- ``/budget save`` — persist the *current* session cap as the
  default for every future session.
- ``/budget save <usd>`` — set the live cap **and** persist it in
  one keystroke.
- ``/budget save off`` — clear the persistent default; future
  sessions boot uncapped.
- ``/budget suggest`` — produce a price-aware suggestion based on
  the active model's per-Mtok rate (≈ 50 typical 700-token chat
  turns). Output is one ``/budget save`` away from being applied.

### Changed — REPL boot path

- ``driver.run`` now calls a new ``_apply_budget_settings`` helper
  on every fresh session. Resolution order: explicit ``--budget``
  flag → cap already on the resumed snapshot → persisted default
  in ``auth.json``. A :class:`BudgetMeter` is materialised
  unconditionally so the chat preflight never has to ``None``-check.

### Changed — chat handler

- ``_chat_with_llm`` now runs a budget preflight before every
  ``provider.generate``. If ``budget_auto_stop`` is on (the default)
  and the meter reports ``EXCEEDED``, the turn is refused with a
  one-line diagnostic that names the exact slash to raise the cap
  (``/budget set <usd>``) or disable the gate (``/budget off``).
  Refused turns do not bill — counters stay where they were.

### Tests

- ``tests/test_auth_store.py``: 10 new assertions covering the
  budget block — defaults, round-trip, partial updates,
  ``clear_budget``, 0600 enforcement, validation of bad values,
  and isolation from the providers block.
- ``tests/test_chat_mode_handlers.py``: 12 new tests:
  preflight refusal when over cap, normal-cost turn under cap,
  uncapped behaviour preserved, ``auto_stop=False`` opt-out path,
  ``/budget save`` round-trip, ``/budget save 5`` one-shot,
  ``/budget save off`` clearing the default, ``/budget save`` with
  no live cap, ``/budget suggest`` per-model estimate,
  ``_apply_budget_settings`` seeding from disk, CLI override
  precedence, and uncapped fallback.

### How to use it

```text
lyra                              # uses persisted default if any
lyra --budget 1.00                # one-shot $1 cap, doesn't touch disk

# at the REPL:
/budget set 5.00                  # this session only
/budget save 5.00                 # this session AND every future one
/budget save off                  # remove the persistent default
/budget suggest                   # ask Lyra for a sane cap
/budget status                    # current spend vs cap
```

The full regression now reads **841 passing, 2 skipped** in
``lyra-cli`` (up from 829), with no regressions in ``lyra-core``.

---

## v2.2.2 — 2026-04-26 — "actually bill the turns"

v2.2.1 fixed the chat handler but the bye-screen still reported
``cost: $0.0000 / tokens: 0`` after three real DeepSeek round-trips.
The handler talked to the LLM but never read ``provider.last_usage``
back. v2.2.2 wires that final stretch.

### Added — pricing & billing

- ``budget._DEFAULT_PRICES_PER_MTOK`` extended with the providers
  Lyra actually ships against by default — DeepSeek (chat / coder /
  reasoner / V3 / V4 / V4 Pro), Qwen-3-Coder, Gemini 2.5 Flash / Pro,
  GPT-4.1 / GPT-5, claude-opus-4-5. All values are public list-prices
  per Mtok at ship date.
- New ``session._bill_turn(provider)`` helper called from
  ``_chat_with_llm`` after every successful ``generate``. It:
  * reads ``provider.last_usage`` (the OpenAI-compat capture surface
    the providers have exposed since v2.1.3),
  * adds ``total_tokens`` to ``session.tokens_used``,
  * looks up the model rate via ``budget.price_for(model_id)`` and
    adds the dollar delta to ``session.cost_usd``,
  * forwards the same delta to ``session.budget_meter`` when one is
    wired so ``/budget`` and the alert chip stay accurate.
- Failures (``generate`` raises, empty reply, missing ``last_usage``)
  do **not** bill — the counters only move on a successful turn.

### Tests

- 5 new tests in ``test_chat_mode_handlers.py``:
  * tokens accumulate across turns,
  * cost matches the model's per-Mtok rate,
  * unknown models fall back to the conservative default,
  * zero-usage responses don't crash and don't bill,
  * failed turns don't bill.

### Verified

```
packages/lyra-cli/tests …………………… 829 passed, 2 skipped
```

Live REPL with ``DEEPSEEK_API_KEY`` set will now show real numbers in
``/status`` and the goodbye panel after every turn — e.g. ``turns 3
/ tokens 472 / cost $0.0009`` for a typical short chat.

## v2.2.1 — 2026-04-26 — "type, get a reply"

The shipping v2.2.0 still booted the REPL into **plan mode** *and* the
plan / build / run / explore handlers all printed canned strings like
`[build] would implement: hello (real LLM dispatch lands with the
Phase 14 CodeAct plugin)`. User feedback was blunt: *"wtf, UX like this
is shit, supposed with claude code, when you type hello, it should
hello doesn't it???"*

They were right. v2.2.1 fixes the first-impression UX so Lyra behaves
like Claude Code / opencode out of the box.

### Changed — REPL boots in `build`, plain text talks to the LLM

- `InteractiveSession.mode` now defaults to **`build`** (was `plan`).
  Plain-text input on a fresh session is now *"talk to the model"*,
  not *"queue a plan for /approve"*.
- `lyra_cli.interactive.driver.run` mirrors the new default.
- `_handle_plan_text` / `_handle_build_text` / `_handle_run_text` /
  `_handle_explore_text` were rewritten on top of a new
  `_chat_with_llm(...)` helper:
  * It lazily resolves the provider via `llm_factory.build_llm(model)`
    and caches the `LLMProvider` on the session so we don't
    re-validate the API key every keystroke.
  * Sends `[system, ...rolling history, user(line)]` to
    `provider.generate(...)` with a mode-specific system prompt that
    describes the active surface (PLAN / BUILD / RUN / EXPLORE).
  * Rolls a 20-turn rolling chat history forward so follow-ups have
    context without unbounded growth.
  * Wraps the call in a try/except — *any* failure (missing key,
    network timeout, rate limit, etc.) is rendered as a friendly
    one-line error panel and the REPL keeps running.
- `/model <name>` invalidates the cached `LLMProvider` so a model
  switch takes effect on the very next turn.
- Plan mode still records `pending_task` for the `/approve` path,
  *and* now answers the user — both behaviours are preserved.
- Retro mode keeps its log-note semantics; that's the journal surface,
  not a chat surface.

### Added — chat-mode rendering

- `output.chat_renderable(reply, *, mode)` — Rich panel that wraps an
  actual LLM reply, coloured by mode (cyan for plan/explore, amber
  for build, pink for run). Treats reply text as plain text so model
  output doesn't accidentally inject Rich markup.
- `output.chat_error_renderable(detail, *, mode)` — friendly red panel
  shown when `build_llm` or `provider.generate` raises. Includes a
  pointer to `lyra connect` so the fix is one command away.

### Tests

- `packages/lyra-cli/tests/test_chat_mode_handlers.py` (9 new) covers:
  * default-mode is build,
  * `build_llm` is called once per model and cached,
  * `/model` invalidates the cache,
  * mode-specific system prompts,
  * conversation history threads forward,
  * `RuntimeError` from `build_llm` and `TimeoutError` from `generate`
    both fall back to the friendly error renderable,
  * retro mode does NOT call the LLM,
  * plan mode still records `pending_task`.
- Updated 6 legacy tests (`test_interactive_session.py`,
  `test_interactive_skin_polish.py`, `test_interactive_features.py`)
  that asserted on the old "default mode is plan" or the
  `[plan] recorded task: …` stub string.

### Verified

```
packages/lyra-cli/tests …………………… 824 passed, 2 skipped
```

The 2 skips are pre-existing `git`-in-sandbox tests, unrelated to this
change. The full repo regression (`pytest projects/lyra`) reports
**1670 passing** outside the sandbox, up from 1659 in v2.2.0 by the 9
new chat-mode tests + 2 environment skips that pass when run directly.

## v2.2.0 "Claude-Code-Class" Production Rebuild — 2026-04-26

The user feedback after v2.1.4 was unambiguous: *"Fix for me whole Lyra
projects, it should follow UI/UX in claw-code, and open-claw …
production ready best version of claude code."* v2.2.0 closes the loop
on the eight-phase production rebuild plan (`docs/superpowers/plans/
2026-04-26-v2.1-claude-code-class-rebuild.md`). Every phase landed via
strict TDD: failing test first, then implementation, then full
regression — **1671 tests pass** with **zero** added failures vs the
pre-rebuild baseline.

### Added — provider auth, preflight, persistent store

- `lyra connect <provider> [--key K | --no-prompt | --no-preflight |
  --list | --revoke]` — single Typer subcommand that picks a provider,
  preflights the API key with one cheap HTTP round-trip, then writes
  `~/.lyra/auth.json` with mode 0600. First-class providers are
  Anthropic, OpenAI, Gemini, DeepSeek, Qwen, Ollama; additional
  providers (xAI, Groq, Cerebras, Mistral, OpenRouter, DashScope,
  LM Studio, vLLM) are also wired.
- Interactive picker (Rich panel + `prompt_toolkit` masked input) when
  no `--key` is supplied. Falls back to plain `getpass` when
  `prompt_toolkit` can't initialise the terminal.
- `lyra_core.auth.preflight` — provider-aware HTTP probe with friendly
  one-line diagnostics (`invalid api key (HTTP 401)`, `rate limited —
  try again in a moment (HTTP 429)`, `connection refused — is Ollama
  running?`).
- `lyra_core.auth.store` — atomic writes via tempfile + rename, mode
  0600 enforced on every save, idempotent revoke, backwards-compatible
  load on corrupt JSON.

### Added — planner robustness

- `lyra_core.plan.artifact.load_plan` is now a tolerant cascade. The
  v2.1.x parser accepted only strict `---\n…\n---` frontmatter and
  blew up when DeepSeek/Qwen prepended prose, code-fenced the YAML,
  emitted JSON, or returned pure prose. v2.2.0 walks six recovery
  paths in priority order:
  1. Strict fenced frontmatter (unchanged).
  2. Prose prefix → fenced plan.
  3. Code-fenced YAML treated as frontmatter.
  4. JSON object translated to Plan schema.
  5. No frontmatter → synthesise defaults from body Markdown.
  6. Pure prose → synthesise minimal valid Plan from `task_hint`.
- Every non-strict recovery emits a `planner.format_drift` event so
  `lyra doctor` can surface noisy LLMs that need prompt nudging.
- Planner system prompt strengthened with an explicit "first three
  characters MUST be `---`" requirement.

### Added — UI/UX v2 (status bar, tool rendering, command palette)

- **Status-bar v2** (`lyra_cli.interactive.status_bar.render_footer`):
  opencode-style icon footer (`◆ model · plan · △ permissions · ✦ LSP
  · ⊙ MCP · t<turn> · 1.2k tok · $0.04`). Empty/zero fields collapse;
  long cwd middle-elides; non-TTY callers ask for `plain=True` and get
  greppable plain text.
- **Tool-rendering v2** (`lyra_cli.interactive.tool_renderers/`): per-
  tool registry that dispatches to specialised renderers. `bash` shows
  the command and (on failure) exit code + first stderr line. `read_
  file` echoes path + line range. `write_file` / `edit_file` show
  `+N/-M` diff stats. `grep`/`glob` show pattern + match count.
  Unknown tools fall through to the generic claw-code card.
- **Command-palette v2** (`lyra_cli.interactive.command_palette`):
  fuzzy filter (substring + initials) + grouped Rich renderer. Wired
  to `/palette [query]` and `/?`. Matched query fragments bold-
  highlight in the panel. Truncates to `max_height`, appends `…` so
  users know to refine.

### Added — first-run onboarding wizard

- `lyra_cli.interactive.onboarding` — fires only on a true first-run
  TTY launch (no `auth.json`, no provider env var, not previously
  dismissed). Shows a welcome panel and delegates to the connect
  picker. Ctrl-C dismisses gracefully without persisting state.
- `/skip-onboarding` slash drops a sentinel at
  `$LYRA_HOME/.no-onboarding` so the wizard never fires again.
- Hooked into `driver.run` ahead of the banner so the wizard appears
  before the prompt.

### Changed

- `llm_factory` now consults `~/.lyra/auth.json` after env vars but
  before the project-local `.env`, so a key saved via `lyra connect`
  is automatically picked up by the auto-cascade.
- DeepSeek elevated to first-class default (parity with OpenAI,
  Anthropic, Gemini, Qwen, Ollama in the picker order).
- `_PLANNER_SYSTEM_PROMPT` rewritten to teach the LLM to honour the
  strict fence even though the parser is tolerant — telemetry events
  flag drift so we can verify in production.

### Fixed

- `lyra_core.auth.__init__` no longer re-exports the `preflight`
  function from the same-named submodule; the shadowing was breaking
  `monkeypatch("lyra_core.auth.preflight._http_get")` in the contract
  tests.
- Plan parser previously surfaced "plan rejected: plan block not
  found" as a hard failure on first-turn DeepSeek/Qwen output. v2.2.0
  synthesises a valid Plan and emits a drift event instead, so the
  agent can keep moving.

### Tests

- 1671 tests pass (was ~1612 pre-rebuild). New coverage:
  - `test_preflight_contract.py` — HTTP probe success, 401, 429,
    network refused, unknown provider, unicode/garbage bodies.
  - `test_auth_store.py` — round-trip, mode-0600 enforcement, atomic
    write, revoke, get_api_key, $LYRA_HOME redirection.
  - `test_connect_command.py` — non-interactive `--key` path, `--no-
    preflight`, failed preflight does not save, `--list`, `--revoke`,
    overwrite, `--model` persisted.
  - `test_planner_tolerant_parser.py` — six representative LLM output
    shapes all parse or synthesise.
  - `test_status_bar_v2.py` — 9 cases: rich vs plain mode, collapse
    zero fields, middle-elide cwd, drop low-priority on narrow term.
  - `test_tool_renderers.py` — bash command + exit code, read/write/
    edit path, search pattern + match count, generic fallback.
  - `test_command_palette_v2.py` — fuzzy substring + initials match,
    aliases, no-match path, max-height truncation, query highlight.
  - `test_onboarding_wizard.py` — pristine-home trigger, env-var
    suppression, dismissal sentinel, non-TTY no-op, welcome render.

### Migration notes

- No state-file migration required. Existing users continue to use
  their env-var keys (Lyra checks env vars **before** `auth.json`).
- The first time you run `lyra` interactively without an env-var key,
  the onboarding wizard appears. If you prefer to keep configuring via
  env vars, type Ctrl-C or `/skip-onboarding` and you'll never see it
  again.

## v2.1.4 "Claude-Code-Class" Phase 2 (partial) — global `lyra` binary on $PATH — 2026-04-26

User feedback after v2.1.3: *"export this to binary file that can use
alias lyra just like claude in terminal to run."* The Typer
``[project.scripts]`` shims (``lyra``, ``ly``) had been generated by
``pip install -e`` since v0.1.0, but they landed in the user-base
``bin/`` directory which is not on macOS's default ``$PATH``, so the
only working invocation was ``python3 -m lyra_cli``. v2.1.4 ships the
last-mile that exposes them as global commands behaving exactly like
``claude`` / ``gh`` / ``brew`` — single word, runs from any directory,
no shell-config edits required.

### Added — first-class binary install

- ``scripts/install-lyra.sh`` — idempotent installer that
  (1) editable-installs all five packages, (2) locates the
  ``lyra``/``ly`` entry-point shims via ``site.USER_BASE``, and
  (3) symlinks them into the first writable ``$PATH`` directory it
  finds (preference order: ``/opt/homebrew/bin`` → ``/usr/local/bin``
  → ``~/.local/bin`` → ``~/bin``). Supports
  ``--bindir DIR`` (force a specific target),
  ``--skip-pip`` (re-symlink only),
  ``--uninstall`` (clean removal).
- ``Makefile`` targets:
  - ``make install-bin`` — runs ``scripts/install-lyra.sh``.
  - ``make uninstall-bin`` — removes the symlinks.
  - ``make binary`` — builds a true single-file standalone via
    PyInstaller (``dist/lyra``, ~50 MB, no Python required on the
    target machine; suitable for distribution).

### Changed — version & cascade docstring

- ``lyra-cli`` package version bumped to ``2.1.4`` in both
  ``__init__.py`` and ``pyproject.toml`` so ``lyra doctor`` and
  ``pip show lyra-cli`` report consistent numbers (was lying as
  ``0.1.0`` since the original v0.1 release).
- ``--model`` / ``--llm`` help text in ``__main__.py`` updated to
  reflect the v2.1.1 DeepSeek-first cascade order (was still listing
  ``Anthropic → OpenAI → Gemini → DeepSeek →…``); now correctly reads
  ``DeepSeek → Anthropic → OpenAI → Gemini →…``.

### Verification

- 767 lyra-cli tests pass, 2 pre-existing skips (no regressions).
- ``which lyra`` → ``/opt/homebrew/bin/lyra``.
- ``lyra --version`` → ``lyra 2.1.4`` from any directory.
- ``lyra doctor`` reports ``lyra-cli 2.1.4`` (was ``0.1.0`` until the
  egg-info refresh in this release).
- ``lyra run "hello" --llm mock --no-plan`` from ``/tmp`` renders the
  full Rich panel + plan + footer chrome end-to-end via the global
  ``lyra`` shim — proof the entry-point preserves everything v2.1.2
  and v2.1.3 added.

### Why this matters

Phase 1 made the runtime work, Phase 2 (in flight) is making the
day-zero developer experience match Claude Code's ``claude`` and
OpenClaw's ``opc``. Typing ``lyra`` instead of ``python3 -m lyra_cli``
is the single biggest readability win for the prompt; every demo,
screencast, and handover doc gets shorter. ``make install-bin`` makes
this reproducible across machines without anyone needing to remember
to add ``~/Library/Python/3.9/bin`` to ``$PATH``.

## v2.1.3 "Claude-Code-Class" Phase 2 (partial) — token-usage proof-of-life — 2026-04-26

User feedback after v2.1.2: "looks good, but I don't see real call
to deepseek yet??". The new chrome rendered the right header, but
the bare ``hello world`` answer was indistinguishable from a canned
mock. v2.1.3 ships **API-returned token counts in the run footer**
as hard proof-of-life — mocks never report tokens, so a non-zero
``in/out`` is verifiable evidence the upstream API actually answered.

### Added — token-usage capture on OpenAI-compatible providers

- ``OpenAICompatibleLLM.last_usage`` (per-call) and
  ``OpenAICompatibleLLM.cumulative_usage`` (session-wide sum)
  capture the response body's ``usage`` block (``prompt_tokens``,
  ``completion_tokens``, ``total_tokens``). Initialised to empty /
  zero so callers can read safely before the first turn without
  ``AttributeError``.
- New ``OpenAICompatibleLLM._record_usage`` helper tolerates
  partial / missing blocks: providers that omit ``usage`` entirely
  (some local servers, some older Groq builds) leave ``last_usage``
  empty without crashing; providers reporting only ``total_tokens``
  (no in/out split) render as ``11 tokens`` rather than the
  misleading ``0 in / 0 out``.

### Changed — run footer surfaces token usage

- Footer reads ``done · 1 step · 0 tools · 7 in / 4 out · 1.5s`` when
  the provider returned a usage block, ``done · 1 step · 0 tools ·
  1.5s`` otherwise (column omitted when missing or all-zero so local
  providers stay clean).
- New helper ``_format_token_usage`` decides between ``X in / Y out``
  vs ``Z tokens`` vs no column.

### Tests

- 5 new tests in ``test_provider_usage_capture.py`` pin
  ``last_usage`` / ``cumulative_usage`` shape, multi-call
  accumulation, missing-block tolerance, and partial-block
  handling.
- 3 new tests in ``test_run_render.py`` for the footer's usage
  column (presence, omission when zero, ``total_tokens``-only
  rendering).

Full lyra-cli regression: 767 passed, 2 skipped (pre-existing
``git not available in sandbox`` skips, unaffected).

## v2.1.2 "Claude-Code-Class" Phase 2 (partial) — `lyra run` chrome — 2026-04-26

Polishes the bare 3-line output that `lyra run --no-plan "<task>"`
used to emit (header-less, unframed answer, `StopReason.END_TURN`
Python-repr leak in the footer) into a proper Claude-Code-class
session.

### Changed — `lyra run` output

- **One-line header** before the agent loop names the *resolved*
  provider/model and current mode:
  `Lyra v2.1.2  ·  deepseek · deepseek-v4-pro  ·  no-plan`. Provider
  label comes from :func:`describe_selection` so the header, the
  REPL banner, and `lyra doctor` all stay in lock-step.
- **Final answer rendered inside a labelled Rich `Panel`** (cyan
  border, `answer` title) instead of dumped naked. Empty answers
  skip the panel rather than emit an empty box.
- **Footer line cleaned up**: `done · 1 step · 0 tools · 1.4s`
  (clean success) or `max_tokens · 5 steps · 7 tools · 2 blocked
  · 12.7s` (soft failure). The clean-success leader uses `done`
  in bold green so completion pops; soft failures show the raw
  stop reason in bold yellow.
- **Elapsed time** added to the footer (uses `time.monotonic` so
  wall-clock jumps don't poison long runs). Sub-minute values render
  as `1.4s`; past 60s switch to compact `1m23s` to keep the column
  narrow.
- **`StopReason.END_TURN` Python-repr leak fixed**: the footer used
  to read `agent stopped: StopReason.END_TURN` because Python <
  3.11 stringifies `str` enums to their qualified name; now
  normalised to `end_turn` (and replaced with `done` for the
  success case).
- **Mode label is honest**: when `plan_skip_decision` auto-skips
  Plan Mode (short low-stakes tasks), the header reads
  `auto-skip` rather than `no-plan` so users can tell whether the
  flag fired or the heuristic did.

### Added — render helpers

- `lyra_cli.commands.run._format_run_header` /
  `_format_run_footer` / `_render_answer_panel` /
  `_format_stop_reason` / `_format_elapsed` — pure / no-I/O so they
  test directly. 16 new tests in `test_run_render.py` pin the
  contract for prefix-stripping, sub-minute / past-minute elapsed
  formatting, blocked-call surfacing, and the `done` vs raw-reason
  leader split.

Full lyra-cli regression: 759 passed, 2 skipped (pre-existing
`git not available in sandbox` skips, unaffected).

## v2.1.1 "Claude-Code-Class" Phase 2 (partial) — DeepSeek-default + Qwen first-class — 2026-04-26

Mid-Phase-2 ship that lands two user-visible polishes ahead of the
full Provider Registry v2 work:

### Changed — auto-cascade priority

- **DeepSeek is the new head of the `--llm auto` cascade.** Previous
  order put Anthropic first (Claude as the reference target for tool
  agents); v2.1.1 promotes DeepSeek to slot 1 because in 2026 its
  coder models match Sonnet / GPT-5 on agentic-coding benchmarks at
  ~10-20× lower per-token cost. For the typical Lyra user — whose
  bill is dominated by tool loops — the cost-aware default is the
  right one. **Users who want Anthropic-first still get it via
  `--llm anthropic` (explicit), or by simply not setting
  `DEEPSEEK_API_KEY`.** Cascade is now: `deepseek → anthropic →
  openai → gemini → xai → groq → cerebras → mistral → qwen →
  openrouter → lmstudio → ollama`.
- **REPL banner resolves `Model auto` → `Model deepseek · deepseek-chat`.**
  When the session model is the implicit default `"auto"`, the welcome
  banner now displays the *resolved* provider+model instead of the
  literal flag value, so users with one key set see exactly which
  backend they're talking to without typing `/status`.

### Added — Qwen as a first-class provider

- **`qwen` is a real preset peer of `dashscope`.** Phase 1 had a
  build-time string substitution (`if kind == "qwen": kind =
  "dashscope"`); Phase 2 promotes it to a registered preset that
  reads `QWEN_API_KEY` *or* `DASHSCOPE_API_KEY` (whichever is set
  first wins) and advertises itself as `qwen` in `describe_selection`,
  status bars, and `lyra doctor`. The legacy `dashscope` preset
  stays for back-compat with anyone scripting against the old name.

### Tests

- 16 new tests across `test_deepseek_default_priority.py`,
  `test_qwen_first_class.py`, and `test_banner_model_resolution.py`
  pin the new contracts.
- 1 existing test renamed (`test_build_llm_auto_prefers_anthropic_when_both_set`
  → `test_build_llm_auto_prefers_anthropic_over_openai_when_deepseek_absent`)
  + 1 new sibling test (`test_build_llm_auto_prefers_deepseek_over_anthropic_when_both_set`)
  pin the new "DeepSeek beats Anthropic in auto" rule.

Full lyra-cli regression: 743 passed, 2 skipped (pre-existing
`git not available in sandbox` skips, unaffected).

## v2.1.0 "Claude-Code-Class" Phase 1 — Foundation — 2026-04-26

Phase 1 of the v2.1 [Claude-Code-Class rebuild](docs/superpowers/plans/2026-04-26-v2.1-claude-code-class-rebuild.md):
make Lyra production-ready out of the box. The mock-as-default trap is
gone, `lyra run` actually executes, and unconfigured installs surface a
real setup hint instead of pretending to work.

### Changed — production defaults

- **`lyra` REPL `--model` / `--llm` default flips from `"mock"` to `"auto"`.**
  Before: starting `lyra` with no flags showed `model mock` in the
  status bar even when `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` etc.
  were set, because typer's hard-coded default never consulted the
  environment. After: the default is `"auto"`, the cascade picks the
  first configured backend, and the status bar shows what's actually
  routing.
- **`lyra run <task>` actually runs the task.** Pre-2.1 the command
  exited with "Phase 2 CLI currently stops here" *after* approving the
  plan, which is why setting `DEEPSEEK_API_KEY` and running
  `lyra run --no-plan "say hello"` produced silence. Now: planner →
  approval → `harness_core.AgentLoop.run(task)` → final answer
  rendered, with a `--max-steps` cap (default 20).
- **`build_llm("auto")` raises `NoProviderConfigured` instead of falling
  back to MockLLM.** The silent downgrade was the single biggest
  source of "is my agent actually running?" confusion. The new
  exception lists every env var the cascade scanned, points at
  `lyra connect`, and tells you exactly how to fix it.
- **`describe_selection("auto")` returns `"unconfigured · run lyra
  connect or set an API key"`** when nothing is configured. Status
  bars and `lyra doctor` no longer advertise `"mock · canned outputs"`
  to operators who simply forgot to export a key.
- **`InteractiveSession.model` and `store.load(...)` defaults change
  from `"mock"` to `"auto"`.** Old snapshots without a `model` field
  load as auto, so resumed sessions never accidentally land on mock.
- **`--llm qwen` becomes a first-class alias** for the DashScope
  OpenAI-compatible preset; users who think of the model family
  rather than the cloud product no longer have to know the trade
  name.

### Added — `NoProviderConfigured` exception

- `lyra_cli.llm_factory.NoProviderConfigured` — raised by
  `build_llm("auto")` when no backend is reachable. The default
  message enumerates the env vars scanned and points at three
  remediations (set a key, run `lyra connect`, or pass `--llm mock`
  for tests). Exported from the module's `__all__`.
- `lyra run` and the REPL both catch it and render the message in red
  rather than spilling a Python traceback.

### Removed

- Silent `MockLLM` fallback at the tail of the `auto` cascade.
- The "Phase 2 CLI currently stops here; execution loop ships in
  Phase 3" stub at the bottom of `commands/run.py`.

### Tests

- New: `packages/lyra-cli/tests/test_phase1_production_defaults.py`
  (8 tests) — locks down the new contract end-to-end.
- Updated: `test_llm_providers.py` × 3 — the old "auto falls back to
  mock" / "describe says mock" assertions now expect
  `NoProviderConfigured` and the `"unconfigured"` label.
- Whole-repo regression: **1480 passed, 0 failed** on
  `lyra-cli + lyra-core` (sandbox-bound git tests excluded as in v2.0).

### Migration notes

- Anyone scripting `build_llm("auto")` and expecting it to *always*
  return a provider needs to either (a) catch `NoProviderConfigured`,
  or (b) pass `"mock"` explicitly.
- The REPL banner stops claiming `model mock` when the user hasn't
  set up a provider. CI checks asserting on that string need to
  expect `model auto` (or the resolved provider name) instead.
- Snapshots written by Lyra ≤2.0 with a `model: "mock"` field are
  honored as-is — only **missing** `model` keys default to `"auto"`.

## v2.0.0 "Frontier" — 2026-04-24 (Wave F of full-parity roadmap)

Wave F closes out the [full-parity roadmap](docs/superpowers/plans/2026-04-24-full-parity-roadmap.md):
all 17 ★ net-new features plus 14 frontier research ideas land as
15 task buckets (`f1`…`f15`), each with RED→GREEN contract tests
and zero regressions on the whole-repo suite.

Net change: **186 new contract tests** across 15 new modules.
Whole-repo regression: **1530 passed, 2 skipped, 0 failed**
(sandbox-bound git tests in `test_subagent_parallel.py`,
`test_worktree_lifecycle.py`, and `test_merge_conflict_resolver.py`
are deselected — they pass cleanly outside the sandbox).

### Added — Discipline, verifiers, and adversarial loops (Tasks f1–f4)

- `lyra_core.tdd.state.TDDStateMachine` — strict/lenient FSM
  `IDLE → PLAN → RED → GREEN → REFACTOR → SHIP` with typed evidence
  artefacts (`PlanArtifact`, `RedFailureArtifact`, `GreenPassArtifact`,
  `RefactorArtifact`, `ShipArtifact`). Exposes both the evidence-driven
  `advance(target, *, evidence=…)` API and the lightweight reason-driven
  `transition(target, *, reason=…)` API. Slash surface: `/phase
  [status|next-legal|reset|set <phase>]`.
- `lyra_core.verifier.trace_verifier` — extracts `I edited foo.py:34`
  claims from assistant narration and cross-checks them against the
  filesystem and optional git diff; rejects path escapes and
  hallucinated line numbers before the user sees them.
- `lyra_core.loop.refute_or_promote.RefuteOrPromoteStage` — runs a
  sub-agent adversary against the proposed solution; successful
  refutation loops back to PLAN, exhausted refutation attempts promote
  the solution.
- `lyra_core.eval.prm.{Rubric, RubricJudge, RubricSet, RubricSetReport}` —
  named, weighted-rubric Process Reward Model; judges score
  turns 0–1 and the report surfaces weakest-link rubrics for
  qualitative regressions.

### Added — Context + skills (Tasks f5–f8)

- `lyra_core.context.ngc.{NGCCompactor, NGCItem, NGCOutcomeLogger}` —
  grow-then-evict Neural Garbage Collector with outcome logging
  (`compactor-outcomes.jsonl`) for training a classifier offline.
- `lyra_core.skills.registry.{Skill, SkillRegistry}` and
  `lyra_core.skills.router.HybridSkillRouter` — reuse-first hybrid
  router: trigger match + historical success rate drives the decision
  to reuse an existing skill over synthesising a new one.
- `lyra_core.skills.optimizer.TriggerOptimizer` — rule-based
  auto-optimizer that mutates skill trigger sets based on user
  feedback (miss → add trigger, false-positive → refine/remove),
  with token-set deduplication so near-duplicates never accumulate.
- `lyra_core.skills.synthesizer.SkillSynthesizer` — drafts new
  `Skill` entries from user queries and proposed triggers; integrates
  with the registry so synthesis outputs become reusable immediately.

### Added — Plugins, meta-harness, arena, federation (Tasks f9–f13)

- `/review --auto` — enhances the Wave-C `/review` slash command so
  the post-turn verifier runs automatically after every agent turn
  without an explicit invocation.
- `lyra_core.plugins.{registry, manifest, runtime}` — two parallel
  plugin surfaces living side-by-side: the programmatic
  `PluginManifest` / `PluginRegistry` (in-process Python modules with
  a module-level `manifest` attribute) and the declarative
  `PluginManifestSpec` / `PluginRuntime` (`.lyra-plugin` /
  `.claude-plugin` / `plugin.json` with a deferred `entry` callable).
  Dispatch is per-plugin-isolated — one broken plugin can't take the
  whole loop down.
- `lyra_core.meta.{corpus, outer_loop}` — `ParityCorpus` +
  `HarnessTask` + `MetaHarness` runs candidate agent configurations
  against a standard evaluation set and ranks them by pass rate.
- `lyra_core.arena.elo.Arena` — Elo-style pairwise leaderboard for
  harness configurations on specific tasks, with an audit trail.
- `lyra_core.skills.federation.{SkillManifest, FederatedRegistry,
  Federator}` — export/import shared skill manifests with merge
  strategies for conflicts.

### Added — Long-horizon checkpoints + frontier UX bundle (Tasks f14–f15)

- `lyra_core.klong.checkpoint` — KLong (long-horizon) snapshot
  format with schema versioning and forward migrators; sessions
  resume cleanly across model generations.
- `lyra_core.ide.bridges.{IDEBridge, build_open_command}` — shell-
  command builders for VS Code (`code --goto path:line:col`),
  Cursor (`cursor path:line`), JetBrains (`idea --line --column`),
  Zed (`zed path:line`), and Neovim (`nvim +line path`).
- Frontier UX slash commands on the REPL:
  - `/split <task>` — queue a task for subagent fan-out.
  - `/vote <candidate>|results|clear` — ranked-choice preference
    ledger with a results view.
  - `/observe [on|off|status|tail]` — toggle the ambient observation
    channel; `tail` prints the most recent notes.
  - `/ide [list|set <name>|open <path>[:line[:col]]]` — configure and
    use an IDE bridge.
  - `/catch-up` — session briefing that summarises TDD phase, split
    queue depth, vote tally, and recent observations.

### Test coverage

Every new module ships with a RED/GREEN contract test file:
`test_tdd_state_machine_contract.py`,
`test_cross_channel_verifier_contract.py`,
`test_refute_or_promote_contract.py`,
`test_prm_contract.py`,
`test_ngc_compactor_contract.py`,
`test_skill_router_contract.py`,
`test_trigger_optimizer_contract.py`,
`test_skill_synthesizer_contract.py`,
`test_review_auto_contract.py`,
`test_plugin_registry_contract.py`,
`test_plugin_manifest_contract.py`,
`test_plugin_runtime_contract.py`,
`test_meta_harness_contract.py`,
`test_arena_contract.py`,
`test_federated_skill_registry_contract.py`,
`test_klong_checkpoint_contract.py`,
`test_ide_bridges_contract.py`,
`test_frontier_ux_contract.py`.

---

## v1.9.0 "Channels, Backends, Eval" — 2026-04-24 (Wave E of full-parity roadmap)

Wave E of the [full-parity roadmap](docs/superpowers/plans/2026-04-24-full-parity-roadmap.md)
brings Lyra to **hermes-agent parity** on every channel adapter
and remote terminal backend, and ships the eval gates Lyra's
TDD-first identity needs to survive model upgrades.

Net change: **23 new modules, 93 new contract tests** across
`lyra-cli` and `lyra-core`. Whole-repo regression: **1339
passed**, 0 net new regressions (the 4 failures + 7 errors are
all sandbox-only `git init` permission denials in
`test_subagent_parallel.py`, `test_worktree_lifecycle.py`, and
`test_merge_conflict_resolver.py`, which pass cleanly outside
the sandbox).

### Added — Channel substrate (Task 1) + 16 channel adapters (Tasks 2–6)

- `lyra_cli.channels.base.{ChannelAdapter, Inbound, Outbound,
  Gateway}` — protocol + dataclasses + multiplexing daemon.
  `Gateway` lazily allocates its `asyncio.Queue` inside
  `start()` so Python 3.9 (whose event loop is created per
  `asyncio.run` call) doesn't crash.
- `_errors.{FeatureUnavailable, AdapterAuthError,
  AdapterRateLimited}` — uniform error types so optional deps
  fail loudly with install hints instead of mysterious
  `ImportError`s.
- **Real adapters:** `slack.SlackAdapter` (`lyra[slack]`),
  `discord.DiscordAdapter` (`lyra[discord]`),
  `matrix.MatrixAdapter` (`lyra[matrix]`),
  `email.EmailAdapter` (`lyra[email]`, IMAP+SMTP via stdlib +
  `aioimaplib`),
  `sms.SmsAdapter` (`lyra[sms]`, backend-agnostic with Twilio +
  Vonage stubs).
- **Long-tail HTTP-shaped adapters:** `feishu`, `wecom`,
  `mattermost`, `bluebubbles`, `whatsapp`, `signal`, `openwebui`,
  `homeassistant`, `qqbot`, `dingtalk`, `webhook` — all 11 are
  thin wrappers over the shared `_HttpChannelAdapter` base, so a
  single contract test covers them parametrically.

### Added — Real remote terminal backends (Tasks 7–9)

- `lyra_core.terminal.modal.ModalBackend` — runs commands in a
  Modal sandbox; `lyra[modal]` extra; raises `FeatureUnavailable`
  with an install hint when `modal` is missing.
- `lyra_core.terminal.ssh.SSHBackend` — paramiko-shaped client,
  `shlex.join` for argv safety, optional `lyra[ssh]` extra.
- `lyra_core.terminal.daytona.DaytonaBackend` — Daytona dev-
  container workspace runner, `lyra[daytona]` extra.
- `lyra_core.terminal.singularity.SingularityBackend` — Apptainer
  CLI wrapper via `subprocess`; checks `singularity` is on
  `PATH` before attempting a run.

All four replace the v1.7.2 stubs that previously raised
`NotImplementedError`.

### Added — Vision toolkit (Task 10)

- `lyra_core.tools.image_describe.make_image_describe_tool` —
  pluggable `VisionLLM` describes a local image. Repo-root
  jail; refuses paths that escape `repo_root`.
- `lyra_core.tools.image_ocr.make_image_ocr_tool` — OCR via
  whichever backend is installed (`pytesseract` / `easyocr`);
  raises a structured `FeatureUnavailable` when none of them
  ship.
- Both tools expose the standard `__tool_schema__` so they
  register cleanly into the tool router.

### Added — Voice toolkit (Task 11)

- `lyra_cli.voice.stt.{STTBackend, transcribe_audio}` —
  protocol + thin pipeline.
- `lyra_cli.voice.tts.{TTSBackend, synthesise_speech}` —
  ditto for TTS.
- `InteractiveSession.voice_mode` + `/voice [on|off|status]`
  slash command — toggles whether the REPL pipes mic audio
  through STT and replies through TTS. Pure flag at dispatch
  time; the audio loop opt-ins from the REPL driver.

### Added — Session replay (Task 12)

- `lyra_cli.interactive.replay.{ReplayController, ReplayEvent,
  load_replay, step_through}` — walks the session's
  `turns.jsonl` event-by-event with a unified diff between
  adjacent turns.
- `/replay [next|prev|reset|status|all]` — REPL-friendly
  controller; cursor lives on the session so successive
  `/replay next` advance the cursor and successive `/replay
  prev` walk back.

### Added — Red-team corpus + safety scorer (Task 13)

- `lyra_core.safety.redteam.{RedTeamCase, RedTeamCorpus,
  RedTeamReport, default_corpus, score_monitor}` — labelled
  corpus + scorer with TPR / FPR / per-category coverage and
  concrete miss / false-positive listings.
- `default_corpus()` ships at least 2 attacks per
  `SafetyMonitor` category plus 4 benign controls, and the
  contract test acts as a regression gate: any rule edit that
  shrinks coverage on the seed corpus fails CI before it
  ships.

### Added — Golden eval corpus + drift gate (Task 14)

- `lyra_core.eval.{EvalCase, EvalCorpus, EvalReport,
  EvalResult, default_corpus, run_eval}` — golden cases keyed
  on expected substrings (mode `all` or `any`); per-category
  pass-rate aggregation.
- `lyra_core.eval.{DriftDecision, DriftGate}` — compares a
  fresh report to a stored baseline; blocks promotion on
  global pass-rate regression beyond `tolerance` (default 2 pp)
  *or* per-category regression beyond `category_tolerance`
  (default 5 pp). Baselines round-trip through JSON on disk.

### Added — Auto-generated wiki + onboarding (Task 15)

- `lyra_core.wiki.{WikiPage, WikiBundle, generate_wiki,
  OnboardingPlan, generate_onboarding}` — offline crawler
  produces a Markdown bundle under `<repo>/.lyra/wiki/`
  (index, one page per top-level package, language inventory)
  and role-targeted onboarding plans.
- `/wiki [generate|preview]` — preview the index in the REPL,
  or write the full bundle to disk.
- `/team-onboarding [engineer|designer|pm|<role>]` — emits a
  first-week briefing rooted at the live wiki state. Unknown
  roles fall back to the engineer template so a fresh teammate
  always gets something useful.

### Roadmap & docs

- Master roadmap (`2026-04-24-full-parity-roadmap.md`) marks
  Wave E **SHIPPED** and Wave F **PLAN READY**.
- New detailed plan: `2026-04-24-v2.0-frontier.md` — the 17
  ★ net-new features and 14 frontier ideas collapse into 15
  task buckets (`f1`…`f15`), each with the same
  Goal/Files/Tests/Notes structure that worked for Wave B–E.
- `feature-parity.md` updated to reflect Wave-E shipments
  (channels, backends, vision, voice, replay, red-team, eval,
  wiki, onboarding).

---

## v1.8.0 "Agentic Backbone" — 2026-04-24 (Wave D of full-parity roadmap)

Wave D of the [full-parity roadmap](docs/superpowers/plans/2026-04-24-full-parity-roadmap.md)
turns Lyra into an actual *agentic harness*. Where v1.7.5 was about
the REPL surface, v1.8.0 is about everything that runs *behind* the
REPL: subagents, presets, DAG fan-out, variant runs, layered
permissions, real `ExecuteCode` and `Browser` tools, custom user
tools, the lifecycle bus, MCP registry, live budget deduction,
preflight wiring, and live-streaming `/pair`.

Net change: **15 new modules, 87 new contract tests** across
`lyra-core` and `lyra-cli`. Total suite: 1143 passed, 0 regressions
(the 4 failures + 7 errors in the sandbox all reduce to long-standing
`git init` permission denials in `test_subagent_parallel.py`,
`test_worktree_lifecycle.py`, and `test_merge_conflict_resolver.py`,
which pass cleanly outside the sandbox).

### Added — Subagent runtime (Tasks 1–5)

- `lyra_core.subagent.runner.SubagentRunner` — single-spawn
  orchestrator. Wraps one `AgentLoop` invocation in a worktree,
  redirects stdout/stderr, tags every HIR event with `scope_id`
  (so `/blame` / `/trace` filter to "events from sub-X"), and
  surfaces a typed `SubagentRunResult` (`status`, `final_text`,
  `error`, `workdir`, `stdout`, `stderr`, `hir_events`).
- `InteractiveSession.subagent_registry` + `focused_subagent` —
  `/agents` now renders a live process table (id / state /
  description) when a registry is attached; `/agents kill <id>`
  cancels a pending record. The static "kinds of subagents"
  overview stays as a fall-back when no registry is wired (so
  older docs / tests keep working).
- `Ctrl+F` (`focus_foreground_subagent` in `keybinds.py`) re-focuses
  the most recently spawned record so the status bar can render
  `→ sub-0007` without the UI dragging registry state around.
- `lyra_core.subagent.presets.{SubagentPreset, PresetBundle,
  load_presets, list_user_dirs}` — drop a YAML / JSON file under
  `~/.lyra/agents/<name>.yaml` and Lyra picks it up. Three
  built-ins ship by default (`explore`, `general`, `plan`); user
  files shadow built-ins by name (`source="user-overrides-builtin"`).
- `lyra_core.subagent.scheduler.{SubagentScheduler, SubagentDAGSpec,
  SubagentDAGRun, SubagentNodeResult, SchedulerError}` — a fan-out
  + join scheduler that takes `[(id, depends_on), …]` nodes,
  validates the graph (no cycles / dupes / unknown deps),
  topologically sorts into levels, runs each level concurrently
  (bounded by `max_parallel`), and skips downstream nodes when an
  upstream node fails so a single bad spec doesn't poison the run.
- `lyra_core.subagent.variants.{run_variants, VariantSpec,
  VariantOutcome, VariantsResult}` — execute the same task `n`
  times in parallel with different `variant_index`es and pick the
  winner via an injected judge. Default judge picks
  `max(payload["score"])`; falls back to "first ok variant" when
  scores are missing. `n=1` short-circuits without invoking the
  judge.

### Added — Layered security (Tasks 6–7)

- `lyra_core.permissions.injection.{injection_guard, GuardResult,
  INJECTION_PATTERNS}` — regex sweep for the eight common
  prompt-injection signatures (`ignore previous instructions`,
  `disregard the above`, `you are now …`, `system override`,
  `BEGIN/END SYSTEM` blocks, `developer mode on`, `DAN mode`,
  inline `system:` markers). Conservative by default — false
  positives are user-visible toasts, false negatives let an
  attacker steer the model.
- `lyra_core.permissions.stack.{PermissionStack, StackInput,
  StackDecision, PermissionMode}` — combines destructive-pattern,
  secrets-scan, and prompt-injection guards behind one `check()`
  with mode awareness (`yolo` short-circuits to allow, `normal` /
  `strict` run all guards). Returns the *first* offending guard's
  name + reason so the REPL can render `blocked by destructive:
  rm -rf /` without parsing multiple decisions.
- `lyra_cli.interactive.tool_approval.ToolApprovalCache` —
  per-session approval ledger. `inquire(tool_name)` returns
  `"allow" | "deny" | "prompt"` based on cached decisions and
  current mode (`yolo` → always allow, `strict` → always re-prompt,
  `normal` → cached decision wins). `approve` / `deny` / `forget` /
  `snapshot` round out the API.

### Added — Real tools (Tasks 8–10)

- `lyra_core.tools.execute_code.{execute_code, ExecuteCodeResult,
  ExecuteCodeStatus, ForbiddenImport}` — sandboxed Python in a
  fresh subprocess. Wall-clock cap (`timeout`, default 10s),
  AST-based import allow-list (rejects forbidden modules *before*
  the subprocess starts; default whitelist covers `math`,
  `statistics`, `json`, `re`, `decimal`, `datetime`, `itertools`,
  `functools`, `collections`, `typing`, `random`, `string`),
  stripped environment (only `$PATH` survives), `stdin=DEVNULL`.
- `lyra_core.tools.browser.{browser_open, BrowserPage,
  BrowserStatus, ensure_playwright}` — Playwright wrapper with
  graceful degradation. Scheme allow-list (`http`, `https`,
  `file`); when Playwright is missing the tool returns a typed
  `BrowserPage` with the `pip install lyra[browser]` install hint
  in `text`, so the agent can self-correct instead of hard-failing.
- `lyra_core.tools.user_tools.{tool, load_user_tools,
  ToolDescriptor, UserToolBundle, ToolRisk}` — drop a Python file
  under `~/.lyra/tools/`, decorate one-or-more callables with
  `@tool(description=…, risk=…)`, and the loader picks them up at
  REPL boot. `risk` is one of `safe | network | filesystem |
  destructive` and flows into the permission stack. Import-time
  errors are recorded in `errors`, not raised, so a single bad
  file doesn't break boot.

### Added — Hooks, MCP, budget, preflight, pair (Tasks 11–15)

- `lyra_core.hooks.lifecycle.{LifecycleBus, LifecycleEvent,
  Subscriber}` — typed pub/sub for the six agent-loop seams
  (`session_start`, `turn_start`, `turn_complete`, `turn_rejected`,
  `tool_call`, `session_end`). Subscriber errors are swallowed
  (telemetry must never break the caller's cascade);
  `unsubscribe` is idempotent.
- `lyra_core.mcp.{MCPRegistry, MCPServer, TrustState,
  trust_banner_for}` — in-memory registry for MCP servers with
  per-server trust state (`trusted` | `untrusted`, defaults
  untrusted). `trust_banner_for` returns the warning banner the
  REPL prints before invoking an untrusted server. Re-registering
  a server preserves trust (operators trust a server, not a
  particular URL revision).
- `lyra_cli.interactive.budget.{BudgetMeter, price_for}` — live
  token → USD deduction. Hand-curated price table for
  GPT-4o/4o-mini, o3/o4-mini, Claude 3.5/3.7/4.1, with a generous
  fallback for unknown models. `record_usage(model,
  prompt_tokens, completion_tokens)` returns the dollar delta;
  `gate()` short-circuits when over the cap.
- `lyra_core.providers.preflight_plugin.PreflightPlugin` — wires
  the Wave-A preflight estimator into the agent loop as a
  `pre_llm_call` hook. Emits `preflight.ok` / `preflight.exceeded`
  HIR events and raises `ContextWindowExceeded` so the caller
  sees a clean stop with a `/compact` hint instead of a
  half-billed provider call.
- `lyra_cli.interactive.pair_stream.PairStream` — live-streaming
  substrate for `/pair`. Subscribes to every `LifecycleEvent` and
  pipes a single line per event into a sink (`console.print` in
  the REPL, `list.append` in tests). `set_enabled(False)` mutes
  without losing the subscriptions; `detach` cleans up.

### Test count

- 15 new contract test files (`lyra-core`: 11, `lyra-cli`: 4).
- 87 new contract tests in v1.8.0 (Wave D), all GREEN.
- Combined pytest run: **1143 passed**, 2 skipped, 0 regressions
  (4 failures + 7 errors are sandbox-only `git init` denials, not
  Wave-D-introduced).

### Substrate-vs-wiring split (post-review honesty)

Wave D ships every claimed module as a real, tested library and
flips the slash-level user-visible toggles (`/agents`, `/budget`,
`/pair`, `/mcp`, `/tools`) where one already existed. The deeper
agent-loop / provider call-site **integration** for several
modules remains the explicit Wave-E focus, captured in
`docs/superpowers/plans/2026-04-24-v1.9-channels-backends-eval.md`:

| module | shipped surface (v1.8.0) | integration depth | remaining Wave-E work |
|---|---|---|---|
| `BudgetMeter` | substrate + `/budget set/status/record/reset` slash + cap classifier | manual `record_usage` via `/budget record`; meter shared with cap | provider usage callbacks auto-call `meter.record_usage` after every LLM round |
| `PreflightPlugin` | plugin + HIR events (`preflight.ok` / `preflight.exceeded`) | substrate ready, plugin attachable to any `AgentLoop` | `llm_factory` auto-installs the plugin per session by default |
| `PairStream` | substrate + `_cmd_pair` attach/detach + sink-callable | `/pair on` attaches the stream to the session lifecycle bus | REPL console sink that redraws the prompt safely from a background subscriber |
| `MCPRegistry` | registry + `trust_banner_for` + real `/mcp [list/register/trust/untrust/remove]` dispatcher | server inventory, trust state, banners — all via the slash | wire-transport client (websockets / stdio) + persisted trust across REPL runs |
| `ToolApprovalCache` | session-scoped ledger + `/tools approve/deny/approvals` slash | mode-aware (`yolo`/`normal`/`strict`); `Alt+M` keybind syncs cache mode | `AgentLoop._dispatch_tool` consults the cache before every tool call |
| `PermissionStack` | layered guards behind one `check()` + `set_mode` | session-attached on first `/tools` use; mode synced from `Alt+M` | `AgentLoop.pre_tool_call` consults the stack on every call + REPL chip render |
| `SubagentRunner` | worktree allocation + HIR scope tagging + stdio capture + **`os.chdir(workdir)`** during the run | file ops inside the spawned loop honour the worktree; cwd restored in `finally` | shell out to `git worktree add` when the parent owns a real repo (currently uses dir-only fall-back) |

This split is intentional: substrates land in v1.8.0, integration
in v1.9.0 (Wave E). The contract tests for the substrates pass
today; the integration tests live in the Wave-E plan.

### Post-review wiring landed in v1.8.0

The Wave-D code-reviewer flagged that several substrates were
shipped without a user-reachable seam. v1.8.0 closes the
quick-win gaps before v1.9.0 begins:

- `_cmd_mcp` is now a real dispatcher backed by `MCPRegistry`
  (`list`, `register`, `trust`, `untrust`, `remove`); the
  placeholder text-only command is gone.
- `_cmd_pair` attaches a `PairStream` to a session-owned
  `LifecycleBus`; toggling `/pair off` mutes without losing the
  subscriptions.
- `_cmd_budget` keeps a `BudgetMeter` per session and adds the
  `record <model> <p_tok> <c_tok>` and `reset` sub-commands;
  `/budget status` reads from the meter when present.
- `_cmd_tools` lazily attaches a `PermissionStack` and
  `ToolApprovalCache`, surfaces the per-tool approval state in
  the table + detail views, and adds `approvals`, `approve <Name>`,
  `deny <Name>` sub-commands.
- `keybinds.toggle_permission_mode` now mirrors the new mode into
  the attached stack and approval cache so `Alt+M` flips the live
  policy in one keystroke.
- `SubagentRunner.run` now `os.chdir`s into the allocated workdir
  for the duration of the loop (restored in `finally`), closing
  the isolation gap the reviewer called out.
- `PermissionStack.set_mode` was added to keep the `Alt+M` lockstep
  symmetric.

### Known sandbox-only failures (carried over from Wave-A/B)

- `tests/test_merge_conflict_resolver.py` (4 tests)
- `tests/test_subagent_parallel.py` (3 errors)
- `tests/test_worktree_lifecycle.py` (4 errors)
- `tests/test_slash_diff.py` (2 skipped — explicit `git not
  available` skip marker)

All four exercise `git init` / `git worktree add`; the macOS
sandbox refuses the `chmod +x .git/hooks/*.sample` step. Pass
cleanly outside the sandbox; not regressions.

## v1.7.5 "REPL Convergence" — 2026-04-24 (Wave C of full-parity roadmap)

Wave C of the [full-parity roadmap](docs/superpowers/plans/2026-04-24-full-parity-roadmap.md)
brings the user-observable REPL surface to strict parity with claw-code,
opencode, and hermes-agent. Every UI / persistence / slash-command
cell that was `NOW`, `v1.5`, or `v1.7` in §1.1–§1.3 of the parity
matrix now flips to `✓ shipped (v1.7.5)`. Two net-new items
(`/red-proof`, `/btw` side-channel log) ship that none of the
reference agents include.

### Added — Persistent sessions & rewind/resume (Tasks 1–2)

- `InteractiveSession.rewind_one()` now persistently truncates the
  on-disk JSONL when `sessions_root` is set, so `Esc Esc` survives a
  REPL restart. The `_TurnSnapshot` schema (line / mode / turn /
  pending_task / cost_usd / tokens_used) round-trips losslessly.
- `InteractiveSession.resume_session(session_id, sessions_root,
  repo_root)` rebuilds a session from disk in the post-turn state, so
  `/resume` lands the user exactly where they left off.
- `lyra_cli.interactive.sessions_store.SessionsStore` — CRUD over
  `<root>/<id>/{turns.jsonl,meta.json}`. Powers `/sessions` (list
  with name/turn/last-modified), `/fork <name>` (deep-copy of the
  current session under a new id), `/rename <name>` (mutates
  `meta.json`), and `/export <path>` (markdown transcript).
- `_default_session_id()` produces collision-resistant
  `sess-<YYYYMMDDhhmmss>-<pid4>` ids so parallel REPLs don't clobber
  each other.

### Added — Repo & runtime introspection (Tasks 3–5)

- `_cmd_map` renders an indented ASCII tree of `*.py` files
  (depth-capped, friendly empty-repo case) — the missing piece for
  "show me what's here without reading READMEs."
- `lyra_core.hir.events.RingBuffer` — bounded, drop-oldest in-memory
  sink for HIR events. Eagerly installed at module import so
  `/blame`, `/trace`, and `/self` always see the same event tape.
- `_cmd_blame` shells out to `git blame -L <line> <file>` with a
  graceful "git not available" fallback; `_cmd_trace` shows the last
  N events from the ring (with the legacy `/trace on|off` verbose
  toggle preserved); `_cmd_self` prints session state plus a ring
  summary so users can audit their own context.
- `lyra_cli.interactive.budget.{BudgetCap,BudgetStatus,BudgetReport,
  enforce}` — classifies current spend into OK / ALERT / EXCEEDED.
  `_cmd_budget set <usd>` mutates the cap; `_cmd_badges` reads
  `<repo>/.lyra/badges.json` and renders an emoji-laden honour roll.

### Added — Direct keybinds & mode dispatcher (Tasks 6–7)

- `lyra_cli.interactive.keybinds` gains 6 pure session-mutator
  helpers: `toggle_task_panel` (`Ctrl+T`), `toggle_verbose_tool_output`
  (`Ctrl+O`), `toggle_deep_think` (`Alt+T`), `cycle_mode` (`Tab` —
  `build → plan → run → retro → explore`), `toggle_permission_mode`
  (`Alt+M` — `normal → strict → yolo`), `rewind_one_persisted`
  (`Esc Esc`). Every helper is unit-tested without `prompt_toolkit`
  installed.
- `_cmd_mode` extended with sub-verbs: `/mode list` (table of
  available modes + descriptions), `/mode toggle` (advance through
  the cycle), and a permission warning when entering `build` while
  `permission_mode == yolo`.
- `InteractiveSession.permission_mode: str` (`strict|normal|yolo`)
  — drives both `/mode build` warning and the future Edit-blocking
  policy (Wave D agent loop).

### Added — Handoff, effort, and review (Tasks 8–10)

- `lyra_cli.interactive.handoff.render_handoff(session, *,
  git_available)` produces a markdown PR description from session
  history (title, summary, test plan, changelog, optional git diff
  stat). `_cmd_handoff` writes it to `<repo>/.lyra/handoff.md`.
- `lyra_cli.interactive.effort.{EffortPicker,
  effort_to_max_completion_tokens, apply_effort}` — interactive
  picker that maps `low|medium|high|max` (alias: `ultra`) to
  `HARNESS_REASONING_EFFORT` and `HARNESS_MAX_OUTPUT_TOKENS` env
  vars. `_cmd_effort` echoes the typed alias while writing the
  canonical level.
- `_cmd_ultrareview` fans out to three mocked reviewer voices
  (correctness, TDD discipline, safety) sharing a single `_local_
  verifier_passes` heuristic. Real subagent fan-out lands in Wave D.
- `_cmd_review` is the single-shot post-turn verifier — TDD-gate +
  safety + evidence — that `_cmd_ultrareview` builds upon.
- `_cmd_tdd_gate <on|off|status>` toggles
  `InteractiveSession.tdd_gate_enabled` (default: True). Wave-D
  agent loop will refuse Edits when no preceding RED test exists.

### Added — Config foundation, vim, RED proof (Tasks 11–13)

- `lyra_cli.interactive.config_store.{Config, apply_to_session,
  to_bool}` — soft-YAML key/value store backing `~/.lyra/config.yaml`.
  PyYAML when installed; line-oriented fallback otherwise. Tolerates
  malformed files at boot.
- `InteractiveSession.from_config(repo_root, config_path=...)` —
  factory that loads the config and applies known keys (theme, vim,
  permission_mode, tdd_gate, effort, budget_cap_usd, model, mode)
  with explicit overrides winning.
- `_cmd_config <list|get <key>|set <key>=<value>>` — surfaces the
  store via slash, persisting every successful `set`.
- 2 net-new built-in themes: **midnight** (deep-night blues for
  low-light coding) and **paper** (high-contrast paper-white for
  screencasts), bringing the total to 10. `/skin` continues to alias
  `/theme`.
- `_cmd_vim` rewritten with `on|off|status` sub-verbs + persistence
  through `Config`. New `lyra_cli.interactive.keybinds.vi_bindings()`
  factory — real `prompt_toolkit.KeyBindings` when installed,
  `_StubKeyBindings` fallback for headless tests.
- `lyra_cli.interactive.red_proof.{RedProofResult, run_red_proof,
  render}` — shells out to `pytest -x -q <target>`, asserts
  non-zero exit (RED proof confirmed), and renders a one-liner +
  6-line tail. `_cmd_red_proof <target>` wires it into the REPL.

### Added — Tools / btw / pair / paste-image (Tasks 14–15)

- `_cmd_tools` extended: `/tools` (full table), `/tools <Name>`
  (detail view with origin / planned milestone), `/tools risk=<level>`
  (filter by `low|medium|high`).
- `_cmd_btw <topic>` — appends to a separate `_btw_log` (FIFO,
  defaulted via `dataclasses.field`) so side-questions never leak
  into `session.history` (and therefore never enter the LLM main
  context). Empty input returns a usage line.
- `_cmd_pair [on|off]` — toggles `InteractiveSession.pair_mode`. The
  status line surfaces `pair: on` only when active so the bar stays
  compact in the common case. Live streaming arrives in Wave D.
- `lyra_cli.interactive.paste.{detect_image_paste, write_attachment,
  substitute_image_tokens}` — detects base64 PNG / JPEG / WebP / GIF
  via data URI **or** raw-base64 magic-byte sniff, writes to
  `<sessions_root>/<session_id>/attachments/<n>.<ext>`, substitutes
  `[Image #N]` in the prompt. PIL not required; OCR / vision-tower
  routing arrives in Wave F.

### Tests

- **+76 new RED/GREEN contract tests** across 15 new files (one per
  Wave-C task, 4–8 tests each):
  - `test_slash_rewind_resume.py` (Task 1)
  - `test_slash_session_management.py` (Task 2)
  - `test_slash_map.py` (Task 3)
  - `test_slash_blame_trace_self.py` (Task 4)
  - `test_slash_budget_badges.py` (Task 5)
  - `test_keybinds_session_toggles.py` (Task 6)
  - `test_slash_mode_full.py` (Task 7)
  - `test_slash_handoff.py` (Task 8)
  - `test_slash_effort.py` (Task 9)
  - `test_slash_review_tdd_gate.py` (Task 10)
  - `test_slash_config.py` (Task 11)
  - `test_slash_vim.py` (Task 12)
  - `test_slash_red_proof.py` (Task 13)
  - `test_slash_tools_btw_pair.py` (Task 14)
  - `test_paste_image.py` (Task 15)
- Full lyra-cli suite: **581 passed / 2 sandbox-skipped** (the same
  `git init`-dependent `/diff` tests as v1.7.4) via
  `python3 -m pytest packages/lyra-cli` — verified 2026-04-24.
  The 28 tests above the headline +76 figure are post-review safety
  hardening (see *Post-review patch* below).
- Combined lyra-cli + lyra-core suite: **1028+ passed / 2 skipped**
  with **~11–12 sandbox-only failures/errors** (every one is a
  `git init` / `git worktree` test blocked from writing
  `.git/hooks/` under the Cursor sandbox: the `/diff` slash test,
  the merge-conflict resolver suite, the subagent-parallel suite,
  the worktree-lifecycle suite, and the post-edit-focused-tests
  scaffold). All pre-date Wave C and pass on a normal dev box.

### Post-review patch (2026-04-24, same release line)

The Wave-C code-quality reviewer flagged **2 MUST-FIX** keymap drifts
and **5 SHOULD-FIX** safety/integrity items. All 7 are addressed in
this same v1.7.5 line so the release that ships *is* the reviewed one:

- **Tab cycle parity (MUST-FIX).** The TTY driver previously cycled
  modes via its own copy of `_MODE_CYCLE` in
  `lyra_cli.interactive.session` (order: `plan → build → run →
  explore → retro`), while the tested helper
  `keybinds.cycle_mode` and the parity-matrix docs declared
  `build → plan → run → retro → explore`. The driver now delegates
  Tab to the tested helper and `_MODE_CYCLE` is re-exported from
  `keybinds._MODE_CYCLE_TAB`, so CI behaviour and TTY behaviour can
  never diverge again.
- **Alt+M wired in TTY (MUST-FIX).** `_build_key_bindings` now
  registers `escape m` → `keybinds.toggle_permission_mode`, with a
  one-line toast in the REPL. Previously the helper existed and was
  unit-tested but no real key reached it.
- **Driver→helper routing (SHOULD-FIX).** Ctrl+T, Ctrl+O, Alt+T,
  and Esc Esc now delegate to the tested helpers (`toggle_task_panel`,
  `toggle_verbose_tool_output`, `toggle_deep_think`,
  `rewind_one_persisted`) instead of duplicating the logic inline.
  Esc Esc in particular now always shrinks the on-disk JSONL when
  `sessions_root` is set (the previous inline path silently no-op'd
  for sessions opened from disk).
- **Path-traversal hardening (SHOULD-FIX).** New
  `lyra_cli.interactive.sessions_store._validate_session_id` rejects
  any id with `/`, `\`, `:`, `..`, NUL, or non-printable bytes
  (allow-list `[A-Za-z0-9._-]+`). Wired into
  `SessionsStore.{fork,rename,export_to,_read_rows}` and
  `InteractiveSession.{_session_dir,resume_session}`. A forged
  `/fork ../etc/passwd` now raises `InvalidSessionId` instead of
  reaching disk; an invalid `session_id` field disables persistence
  rather than crashing the REPL.
- **Atomic persistence (SHOULD-FIX).** New
  `sessions_store._atomic_write_text` (tempfile + `os.replace`) is
  now used for `meta.json`, the truncated `turns.jsonl` after
  `/rewind`, every `export_to` format, and `Config.save`. A crash
  mid-write leaves the previous file intact instead of a
  half-truncated one.
- **Config-store DoS cap (SHOULD-FIX).** New
  `config_store.MAX_CONFIG_BYTES = 256 * 1024`. `Config.load`
  refuses oversized payloads (returns an empty store rather than
  blocking REPL boot) so a malicious or runaway
  `~/.lyra/config.yaml` can't starve memory through a YAML bomb.
- **Doc accuracy sweep (SHOULD-FIX).**
  - `feature-parity.md` `Ctrl+F` row corrected (was claiming v1.7.5;
    now correctly attributed to Wave D, since the kill-subagent
    handler ships with `SubagentRegistry.kill_all`).
  - Test count updated to **553 → 581** with the post-review delta
    called out.
  - "11 new files" → "15 new files" (one per Wave-C task).
  - "6 keyword-only fields" → "9 dataclass fields" (the original
    note undercounted and called the dataclass kw-only when it's
    positional with defaults).
  - Wave-D plan predecessor metric refreshed.
  - Sandbox-failure inventory updated (the `git init` family now
    includes the post-edit-focused-tests scaffold).

### New tests for the post-review patch

- `lyra-cli/tests/test_session_safety.py` — 28 contract tests
  covering: 17 path-traversal cases (12 reject + 5 accept) on
  `_validate_session_id`, 4 fork/rename/export/resume traversal
  rejection tests, 1 `_session_dir` graceful disable test, 3 atomic
  write tests, 3 config-store size-cap tests.

### Files touched in the post-review patch

- `packages/lyra-cli/src/lyra_cli/interactive/sessions_store.py`
  (added `InvalidSessionId`, `_validate_session_id`,
  `_atomic_write_text`; wired into `fork`/`rename`/`export_to`/
  `_read_rows`; switched `meta.json` writes to atomic).
- `packages/lyra-cli/src/lyra_cli/interactive/session.py`
  (re-exported `_MODE_CYCLE` from `keybinds._MODE_CYCLE_TAB`;
  guarded `_session_dir` / `resume_session` with the validator;
  switched `_truncate_persisted_log_by_one` to the atomic helper).
- `packages/lyra-cli/src/lyra_cli/interactive/driver.py` (routed
  Tab / Ctrl+T / Ctrl+O / Alt+T / Esc Esc through the keybind
  helpers; added Alt+M binding).
- `packages/lyra-cli/src/lyra_cli/interactive/config_store.py`
  (added `MAX_CONFIG_BYTES`; size-capped `Config.load`; switched
  `Config.save` to the atomic helper).
- `packages/lyra-cli/tests/test_interactive_features.py` (the
  Wave-A `_MODE_CYCLE` order assertion was updated to the canonical
  Wave-C order, with an inline comment explaining the reset).
- `packages/lyra-cli/tests/test_session_safety.py` (new).
- `docs/feature-parity.md` (test count, Ctrl+F row, file-count
  pluralisation).
- `CHANGELOG.md` (this section).
- `docs/superpowers/plans/2026-04-24-v1.8-agentic-backbone.md`
  (predecessor metric).

### Migration notes

- `InteractiveSession` gains 9 dataclass fields with defaults
  (`sessions_root`, `session_id`, `session_name`, `permission_mode`,
  `tdd_gate_enabled`, `pair_mode`, `_btw_log`, `config_path`,
  `config`) — all backwards-compatible (the dataclass is positional;
  every new field carries a default so existing
  ``InteractiveSession(repo_root=..., model=...)`` call-sites are
  unaffected). The new `from_config` classmethod is opt-in.
- The HIR `RingBuffer` is now eagerly installed at module import
  (`lyra_core.hir.events`). Tests that previously dispatched events
  before subscribing now see the full tape; if you relied on the
  empty-ring-at-import behaviour, call `reset_global_ring()`
  explicitly in your test setup.
- `emit()` and `RingBuffer._on_event()` accept `name` as a
  positional-only argument (Python `/` syntax) so attribute kwargs
  named `name` no longer collide.

### Looking ahead

Wave D ("Agentic Backbone") wires the Wave-C surface into the
agent loop: `/red-proof` becomes the gate `_cmd_tdd_gate` actually
enforces; `/ultrareview` fans out to real subagents; `/btw` opens
a sibling subagent; `/pair` streams thoughts in real time;
`Ctrl+F` kills running subagents. The CLI surface stays exactly
where v1.7.5 puts it.

---

## v1.7.4 "Local-First & Provider Polish" — 2026-04-24 (Wave B of full-parity roadmap)

Wave B of the [full-parity roadmap](docs/superpowers/plans/2026-04-24-full-parity-roadmap.md)
makes Lyra a strict superset of claw-code / opencode / hermes-agent on
the provider axis. Every backend any of the three exposes now has a
Lyra equivalent, plus 5 local-server presets none of them ship.

### Added — Provider ecosystem (claw-code / hermes-agent / opencode parity)

- `lyra_core.providers.dotenv` — stdlib `.env` parser (`parse_dotenv`,
  `load_dotenv_file`, `dotenv_value`). Honours `export` prefix,
  single + double quotes, blank lines, comments, CWD lookup; zero
  external dependencies.
- `lyra_core.providers.auth_hints` — foreign-credential sniffer
  (`ForeignCred`, `KNOWN_FOREIGN_CREDS`, `missing_credential_hint`).
  When the user asks for `--llm anthropic` but only has
  `OPENAI_API_KEY` set, the factory surfaces the canonical fix
  command instead of a bare `MissingCredentials`.
- `lyra_core.providers.aliases` — case-insensitive model-alias
  registry (`AliasRegistry`, `DEFAULT_ALIASES`, `resolve_alias`,
  `provider_key_for`, `register_alias`). Short names users already
  type — `opus`/`sonnet`/`haiku`, `grok`/`grok-mini`,
  `kimi`/`kimi-k1.5`, `qwen-max`/`qwen-plus`/`qwen3-coder`,
  `llama-3.3` — resolve to canonical slugs with provider key attached
  for routing.
- `lyra_core.providers.registry` — plugin `max_output_tokens` override
  via `~/.lyra/settings.json` (`plugin_max_output_tokens`,
  `max_tokens_for_model_with_override`, `_PER_MODEL_MAX_OUTPUT`).
  Per-model defaults plus user-supplied caps with positive-value
  validation.
- `lyra_core.providers.preflight` — context-window preflight
  (`preflight`, `ContextWindowExceeded`, `PreflightReport`,
  `estimate_input_tokens`, `CONTEXT_WINDOW`). 4 chars/token
  heuristic; raises before the round-trip when the messages + system
  + tools + max_output exceed the model's context window. Unknown
  models pass through unchecked.  *Status: library-only in v1.7.4.
  The agent loop and provider adapters do not call `preflight`
  automatically yet — wiring it into the execution path is tracked
  under Wave D.*
- `lyra_cli.providers.openai_compatible.ProviderRouting` —
  OpenRouter-style routing knobs (sort, only, ignore, order,
  require_parameters, data_collection) marshalled into
  `extra_body.provider`. `OpenAICompatibleLLM` gains a
  `_urlopen` test hook with lazy resolution that preserves
  `mock.patch` compatibility.
- `lyra_cli.providers.fallback` — provider cascade
  (`FallbackChain`, `FallbackExhausted`, `classify_error`,
  `is_retryable_error`). Retries on 5xx / 429 / network timeouts,
  short-circuits on auth / 4xx errors, raises `FallbackExhausted`
  with the full per-provider error list when every link in the
  chain has been tried.
- 6 new OpenAI-compatible presets — DashScope (Qwen / Kimi cloud,
  port 443), vLLM (`:8000`), llama.cpp `server` (`:8080`), TGI
  (`:8081`), Llamafile (`:8082`), MLX-LM (`:8083`). Local presets use
  `auth_scheme="none"` and `probe_reachable=True` so the auto cascade
  picks them up only when the daemon is actually listening.
- `lyra_cli.providers.bedrock.AnthropicBedrockLLM` — Anthropic Claude
  via AWS Bedrock Converse API. SigV4 signing via the optional
  `boto3` dep (`lyra[bedrock]`); raises `BedrockUnavailable` with the
  install command when the extra is missing.
- `lyra_cli.providers.vertex.GeminiVertexLLM` — Gemini via Google
  Vertex AI's `generate_content` API, optional
  `google-cloud-aiplatform` dep (`lyra[vertex]`); raises
  `VertexUnavailable` with the install command when missing.
- `lyra_cli.providers.copilot.CopilotLLM` + `CopilotTokenStore` —
  GitHub Copilot as a chat backend. Rotating session tokens (refresh
  on 401, persisted to `~/.lyra/auth.json` with `chmod 600`).
- `lyra_cli.interactive.auth.DeviceCodeAuth` + `/auth` slash —
  RFC 8628 OAuth 2.0 Device Authorization Grant. Honours `slow_down`
  with a clamp that no-ops sleeps when `poll_interval_s=0` so test
  suites stay fast. `/auth list` shows configured providers; `/auth
  logout <provider>` clears tokens.
- `lyra_core.hir.events` — fire-and-forget pub/sub event hub
  (`emit`, `subscribe`, `unsubscribe`, `clear_subscribers`).
  Subscribers are best-effort; the OTel exporter (shipped v1.7.3)
  can subscribe to `provider_selected` without owning a session
  writer.
- `lyra_cli.llm_factory` wiring — `.env` hydration, alias resolution
  on `HARNESS_LLM_MODEL`, `missing_credential_hint` on fail-loud
  paths, and `provider_selected` event emission on every successful
  provider construction.
- `/model list` / `/models` slash — live provider enumeration with
  `●` (selected) / `✓` (configured) / `—` (not configured) markers.
  Combines `known_llm_names()` with the `PRESETS` registry so adding
  a new preset auto-appears.
- `/diff` slash — real `git diff --stat` followed by the unified
  diff body (truncated at 20 000 chars to protect the REPL).
  Friendly errors when outside a git repo, git is missing, or the
  tree is clean.

### Test delta

**+111 contract tests** across 13 new files. Full lyra-core +
lyra-cli suite: **875 → 912 passing, 2 sandbox-skipped** (the 2
skips are the `/diff` git tests that need real `git init`, blocked
in the sandbox). 11 pre-existing git-sandbox-dependent tests in
`test_subagent_parallel.py` / `test_worktree_lifecycle.py` /
`test_merge_conflict_resolver.py` remain skipped on this host.

### Optional dependencies

- `lyra[bedrock]` — `boto3>=1.34`
- `lyra[vertex]` — `google-cloud-aiplatform>=1.42`
- `lyra[copilot]` — stdlib-only umbrella (no SDK pin yet)
- `lyra[oauth]` — stdlib-only umbrella

### Breaking changes

None. Every new signature is additive; every new keyword argument is
keyword-only with a default; existing presets are untouched. The
`/model` slash now routes `/model list` / `/model ls` to the new
list view but `/model <name>` to set the active model is unchanged.

---

## [Unreleased] — v1.8 close-out + v1.9 Phase 1 seeding

**Every Phase-0 RED test for v1.8 is now GREEN** (663 passed → 664
passed, 9 xfailed → **0 xfailed**) and the v1.9 Phase 1 module skeletons
(`lyra_core.org`, `default_prm_adapter`) land their first contract
in-tree. The pass closes the gap from the previous *v1.8 Phase 1 +
Phase 6 + external-bench adapters* milestone (see "Earlier this
release cycle" below): four Phase-1 features land GREEN; the
**`lyra_core.diversity`** module is fully wired into both
`TournamentTts.run` and `ReasoningBank.recall` (the two Echo-Chamber
counter-measures from [arXiv:2604.18005](https://arxiv.org/abs/2604.18005),
ACL 2026 Findings, mirrored at [`papers/diversity-collapse-mas.pdf`](papers/diversity-collapse-mas.pdf));
**v1.8 Phase 6 wiring** ships all four integration contracts; both
external-bench adapters (τ-Bench Phase 6, Terminal-Bench 2.0 Phase 7)
ship their JSONL loader + writer pairs.

### Added — v1.8 Phase 2 (ReasoningBank in-memory store)

- `ReasoningBank.record(trajectory)` distills via the injected
  `Distiller`, persists lessons in an in-memory list, and returns the
  fresh batch. Failure trajectories are first-class: the contract
  guarantees ≥ 1 anti-skill lesson per failure (the failure-distillation
  contract from [arXiv:2509.25140](https://arxiv.org/abs/2509.25140)).
- `ReasoningBank.recall(task_signature, *, k, polarity, diversity_weighted)`
  ranks lessons by **exact-sig match → substring match → recency** and
  filters by polarity when supplied. `diversity_weighted=True` (the v1.8
  Phase 6 Echo-Chamber counter-measure) routes the top-of-rank pool
  through `lyra_core.diversity.mmr_select` so the returned lessons are
  relevant *and* mutually distinct. Empty `k=0` request returns `()`
  by contract.
- `ReasoningBank.matts_prefix(task_signature, attempt_index, *, k)`
  rotates the recall window by `attempt_index` so attempt-N reads a
  *different* slice of the lessons than attempt-(N−1). Combined with
  the per-attempt index header, this guarantees the MaTTS contract
  (different attempt indices yield different prefixes) on any bank
  with ≥ 2 lessons.
- The Phase-2 store is intentionally in-process; the SQLite + FTS5
  swap-in keeps the Protocol identical and lands as part of the
  v1.9 release.

### Added — v1.8 Phase 3 (Skill-RAG router)

- `SkillRagRouter.answer(question, first_attempt, hidden_state)` wires
  the full Phase-3 pipeline: prober diagnoses → registry lookup →
  handler dispatch → result repackaging with the prober's verdict
  attached. The `RecoverySkill.EXIT` path is honoured by simply
  propagating the registered EXIT handler's `answer=None`, so the
  *only* way Skill-RAG returns a hallucination is if a malformed
  registry is wired (and the constructor refuses those at instantiation
  time).
- The router stitches the leading `first_attempt` onto the handler's
  rounds and **caps the result at `max_rounds`**. Treats over-budget
  exploration as a recoverable bug (truncate-and-return) rather than
  a hard failure — the operator's budget is the contract.

### Added — v1.9 Phase 1 seeding

- New **`lyra_core.org`** module — the entry point for *Software Org
  Mode* (multi-persona multi-topology orchestration). Phase-0 ships two
  hard defaults locked to the Pareto-safe values per
  [arXiv:2604.18005](https://arxiv.org/abs/2604.18005) §4 Figure 3 + §5.2
  Figure 10:
  - `DEFAULT_PERSONA_MIX = "vertical"` (Pareto-frontier mix, Vendi ≈
    6.08 × Overall Quality ≈ 8.32);
  - `DEFAULT_TOPOLOGY = "subgroups"` (sustained constructive conflict).
  - `COLLAPSE_PRONE_PERSONA_MIXES = {"leader_led", "interdisciplinary"}`
    and `COLLAPSE_PRONE_TOPOLOGIES = {"standard"}` enumerate the modes
    the v1.9 runner refuses to use *as a default*. Module-level
    asserts make any future regression surface as an `ImportError`.
- New **`default_prm_adapter()`** factory in
  `lyra_core.verifier.prm` — returns Lyra's currently-installed
  default PRM. v1.8 ships a deterministic
  `HeuristicArithmeticPrm` (no network, no GPU) that satisfies the
  property contract `score_step('1+1=2')` ≫ `score_step('1+1=11')` via
  whitelisted arithmetic eval; v1.9 Phase 1 will swap the factory's
  return value to a `Qwen2.5-Math-PRM-7B`-backed adapter behind a
  feature flag while preserving `HeuristicArithmeticPrm` as the
  explicit no-network fallback.

### Phase-0 RED-test contracts now GREEN

Every Phase-0 `xfail(strict=True)` marker is removed in this pass; the
underlying tests are now plain GREEN.

| Test file                                      | Was xfail (Phase 0) | Now GREEN |
| ---                                            | ---                 | ---       |
| `test_memory_reasoning_bank_phase0.py`         | 4                   | 4         |
| `test_retrieval_skill_rag_phase0.py`           | 3                   | 3         |
| `test_verifier_prm_phase0.py` (default factory) | 1                   | 1         |
| `test_diversity_preservation_phase0.py` (org)  | 1                   | 1         |
| **Total this pass**                            | **9**               | **9**     |

### Earlier this release cycle

### Added — Phase 1 implementations

- `lyra_core.verifier.tdd_reward.compute_tdd_reward` — pure function;
  weighted average over `red→green`, `green→green`, and `new-tests`
  signal terms. Inactive-term-aware (a term whose denominator is zero
  is dropped from both numerator and denominator rather than silently
  zeroed). Custom weights override defaults key-wise.
- `lyra_core.tts.tournament.TournamentTts.run` — full single-elimination
  bracket with byes, monotonic-clock + token-budget enforcement,
  per-attempt `wins / participations` scoring, and a structured
  `distilled_summary` string (LLM Parallel-Distill-Refine reserved for
  Phase 2).
- `lyra_core.routing.cascade.ConfidenceCascadeRouter.invoke` — ordered
  cheap → expensive cascade with per-stage threshold acceptance, full
  cost accounting, and a falls-through-to-final-stage safety net.

### Added — Diversity-collapse hardening (`lyra_core.diversity`)

- New module with four orthogonal primitives (`effective_diversity`,
  `mean_pairwise_distance`, `mmr_select`, `ngt_attempt_independence_guard`)
  + two Protocols (`DiversityMetric`, `PairwiseDistanceMetric`).
  Dependency-free fallback distance via `difflib.SequenceMatcher`;
  embedding-backed cosine swaps in v2.0 once an embedding provider is
  registered.
- `mmr_select` — Maximal Marginal Relevance reranker (Carbonell &
  Goldstein 1998); the canonical fix for top-k retrieval echo chambers.
- `ngt_attempt_independence_guard` — pre-flight check enforcing the
  paper's NGT (Nominal Group Technique, Delbecq et al. 1986)
  prescription that parallel attempts must be generated *blind*; raises
  `ValueError` with a remediation hint pointing to arXiv:2604.18005 §5.2.

### Added — Diversity-collapse analysis doc

- New [`docs/research/diversity-collapse-analysis.md`](docs/research/diversity-collapse-analysis.md):
  full mapping of 8 Lyra subsystems against the paper's three-level
  finding stack. **5 at-risk** (Tournament TTS, MaTTS prefix,
  ReasoningBank.recall, subagent dispatcher, planned Software Org Mode);
  **3 resilient by design** (Confidence-Cascade, Skill-RAG, Voyager
  curriculum). Includes risk grading, version-by-version mitigation
  plan, and an open-questions section seeding the v1.8 Phase 6 telemetry.

### Added — v1.8 Phase 6 wiring (Diversity-Collapse Hardening)

Three of the four Phase-6 integration contracts now ship. Each one was
defined as a `xfail(strict=True)` Phase-0 RED test in the previous
Unreleased pass; the markers are stripped and the tests are now plain
GREEN.

- `TtsResult` gains a `pool_diversity: float = 0.0` field. The drift-gate
  reads it to refuse a tournament whose attempt pool collapsed below a
  threshold (the Compute-Efficiency-Paradox failure mode in §3 of the
  paper). Field defaults to 0.0 to keep snapshot loaders backwards-compatible.
- `TournamentTts.run` now (a) builds a per-attempt fingerprint from
  `metadata["context_fingerprint"]` (falls back to `Attempt.id`),
  (b) calls `lyra_core.diversity.ngt_attempt_independence_guard(...)`
  via the *module attribute* so test spies and future telemetry hooks
  can patch in one place, and (c) computes
  `pool_diversity = effective_diversity([a.artefact for a in attempts])`
  before scoring. A pool that collides on context fingerprints raises
  with the remediation hint pointing back to arXiv:2604.18005 §5.2.
- `ReasoningBank.recall` gains a keyword-only `diversity_weighted:
  bool = False` parameter. The implementation lands with v1.8 Phase 2
  (the underlying recall is still `NotImplementedError`); the signature
  contract is here so callers can opt in to MMR rerank as soon as the
  in-memory store ships.

The fourth Phase-6 contract (default `SoftwareOrgMode` topology must be
`vertical+subgroups`) stays RED until v1.9 Phase 1 because the `org`
module doesn't exist yet.

### Added — External-bench adapters (v1.8 Phase 6 + 7)

Both adapters already had frozen-dataclass + `EvalRunner` glue from
Phase 0. The remaining JSONL plumbing now ships, mirroring the
strict-schema posture of `lyra_evals.adapters.swe_bench_pro`:

- **`lyra_evals.adapters.tau_bench`** (Phase 6 — Sierra τ-Bench / τ³-Bench)
  - `load_tau_bench(path, *, limit=None)` reads JSONL → `tuple[TauBenchTask, ...]`-shaped
    immutable list. Required keys (`instance_id`, `domain`, `user_intent`,
    `policy_doc`) raise `ValueError` with the offending **line number** on
    schema drift; optional keys (`allowed_tools`, `ground_truth_actions`,
    `allow_partial_credit`) default to empty / `False`. Honours
    `--budget N` via `limit=`.
  - `write_tau_bench_submission(path, verdicts)` emits per-verdict JSONL
    with the four canonical scoring keys (`instance_id`, `passed`,
    `fraction_correct`, `policy_violations`); `sort_keys=True` keeps
    repeated writes byte-identical for clean PR snapshots.
- **`lyra_evals.adapters.terminal_bench_v2`** (Phase 7 — Stanford NLP TB-2.0)
  - `load_terminal_bench_v2(path, *, limit=None)` same posture; required
    keys (`task_id`, `description`, `initial_filesystem`,
    `checker_command`, `time_limit_s`) raise on miss; `allowed_network`
    defaults to `False` to mirror the upstream offline majority.
  - `write_terminal_bench_v2_submission(path, verdicts)` emits the five
    canonical keys (`task_id`, `passed`, `wall_clock_s`, `exit_code`,
    `notes`) per row.

### Tests

- 13 tests in [`packages/lyra-core/tests/test_diversity_preservation_phase0.py`](packages/lyra-core/tests/test_diversity_preservation_phase0.py):
  9 primitive contracts + 3 Phase-6 wiring contracts + 1 v1.9 Phase 1
  Software-Org-Mode contract — **all GREEN** in this pass.
- Phase-0 RED markers removed for **all** v1.8 Phase 1/2/3/6/7 +
  v1.9 Phase 1 partial features (xfail markers stripped; tests now
  plain GREEN).
- Suite total: **664 passed, 0 xfailed** (was 628 / 23 at end of
  Phase 0; 648 / 16 after Phase 1; 651 / 13 after Phase-6 diversity
  wiring; 655 / 9 after Phase-6/7 external-bench adapters). The full
  arc: **23 → 0 strict-xfail in five mergeable passes, 41 net new
  GREEN tests since Phase 0.** Brand-identity suite (23 tests) still
  GREEN throughout.
- `ruff check` clean across every module + test file edited in this
  pass (full-monorepo `ruff` is still noisy on pre-existing
  not-touched-here files; that cleanup is on the v1.9 housekeeping
  list).

### Notes

- The new diversity module is dependency-free on purpose; the
  `_normalised_token_distance` fallback is good enough for unit tests
  and the drift-gate threshold but should be swapped for cosine-on-
  embeddings in v2.0 when an embedding provider lands.
- `TournamentTts.run` reads `Attempt.metadata["context_fingerprint"]`
  when present, falling back to `Attempt.id`. **Callers who care about
  diversity must populate the fingerprint** — typically a hash of
  `{prompt_template, retrieved_doc_ids, model_id, sampling_temperature,
  matts_prefix}` — otherwise the guard degrades to a uniqueness check
  on attempt IDs.
- `ReasoningBank.recall(diversity_weighted=True)` is now behavioural,
  not just declared. The Phase-2 in-memory store backs both flat
  `top-k` and the MMR-reranked path. The Phase-2 SQLite/FTS5 swap
  preserves both surfaces.
- `default_prm_adapter()` returns the **heuristic** PRM today;
  v1.9 Phase 1 will swap to the Qwen-backed adapter behind a feature
  flag without changing the factory's signature. Anything Lyra ships
  that consumes `default_prm_adapter()` (TournamentTts discriminator,
  ConfidenceCascade confidence source) is therefore swap-safe.
- `lyra_core.org` is **defaults only** in this pass; the runtime
  `OrgPersona` / `Topology` / `OrgRunner` machinery lands with the v1.9
  plugin loader. The constants exist now so that any v1.8 caller can
  already reference Lyra's commitment to the Pareto-safe defaults.

## [Unreleased] — v1.8 Phase 0 "RED bedrock"

TDD-first scaffolding for the eight v1.8 features. Adds module skeletons
+ failing-by-design contract tests; no behaviour change for users.

- New `phase0_red` pytest marker registered in workspace + per-package
  `pyproject.toml` (`xfail(strict=True)` semantics so an accidental
  XPASS surfaces as CI red — forces marker removal in the PR that lands
  the implementation).
- Lyra-core skeletons (Protocols + dataclasses, `NotImplementedError` on
  the would-be hot path):
  - `lyra_core.tts.tournament` — Tournament TTS (Wave-1 §3.1).
  - `lyra_core.memory.reasoning_bank` — ReasoningBank with
    failure-distillation + MaTTS prefix (Wave-1 §3.2).
  - `lyra_core.retrieval.skill_rag` — Skill-RAG hidden-state prober +
    4-skill recovery router (Wave-1 §3.3).
  - `lyra_core.verifier.tdd_reward` — TDD-Reward inference signal
    (Wave-1 §3.4); dataclass renamed `TddTestOutcome` to dodge
    pytest's `Test*` collector.
  - `lyra_core.routing.cascade` — Confidence-Cascade Router across
    FrugalGPT / RouteLLM / Confidence-Driven lineage (Wave-2 §8.2).
  - `lyra_core.verifier.prm` — Process Reward Model adapter
    (Wave-2 §8.5).
- Lyra-evals adapter skeletons (mirror `SWEBenchProAdapter` shape):
  - `lyra_evals.adapters.tau_bench` — τ-Bench / τ³-Bench loader,
    adapter, submission writer (Wave-2 §9).
  - `lyra_evals.adapters.terminal_bench_v2` — Terminal-Bench 2.0
    loader, adapter, submission writer (Wave-2 §9).
- 42 new tests across the 8 modules: 19 contract tests **GREEN today**
  (validate dataclass shapes, enum membership, constructor invariants);
  23 RED tests `xfail(strict=True)` until v1.8 Phase 1–7 land.
- Test count: **609 → 628 GREEN, 23 xfailed**, brand-identity suite
  (23 tests) still GREEN.

## [Planned] — v1.8 / v1.9 / v2.0 / v2.5 "Beyond Test-Time Scaling"

**Fifteen** novel selling points across two waves for the next four
milestones, each grounded in a primary source (arxiv paper or
production OSS), each beating one of {Claude Code, OpenClaw, Hermes,
ARIA} on a specific axis. **Full plan with RED tests, contracts, and
acceptance metrics in [`docs/novel-ideas.md`](docs/novel-ideas.md).**
Underlying papers mirrored under [`papers/`](papers/) (21 PDFs,
~140 MB; Wave 1 = 7, Wave 2 = 14).

### Wave 1 — capabilities

- **v1.8 "Tournament"** — Meta-style Recursive Tournament Voting +
  Parallel-Distill-Refine for coding ([arXiv:2604.16529](https://arxiv.org/abs/2604.16529));
  ReasoningBank with failure-distillation + MaTTS
  ([arXiv:2509.25140](https://arxiv.org/abs/2509.25140)); Skill-RAG
  hidden-state prober + 4-skill recovery router
  ([arXiv:2604.15771](https://arxiv.org/abs/2604.15771)); KnowRL-style
  TDD-reward inference signal as numeric per-step gate
  ([arXiv:2506.19807](https://arxiv.org/abs/2506.19807)).
- **v1.9 "Substrate"** — CubeSandbox-compatible microVM backend
  ([`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox));
  verifiable RAG corpus with sigstore-signed entries + k-of-n
  publisher quorum + PoisonProbe (PoisonedRAG defense,
  [arXiv:2402.07867](https://arxiv.org/abs/2402.07867)); self-wiring
  knowledge graph for procedural memory (GBrain v0.12-inspired).
- **v2.5 "Federation"** — cross-harness trace federation;
  `lyra recall --harness all` answers across CC / OC / Hermes /
  Moraine sessions ([`eric-tramel/moraine`](https://github.com/eric-tramel/moraine)).

### Wave 2 — performance edges (added 2026-04-24)

- **v1.8 (additions)** — confidence-cascade routing across
  FrugalGPT / RouteLLM / Confidence-Driven LLM Router lineage
  ([arXiv:2305.05176](https://arxiv.org/abs/2305.05176),
  [arXiv:2406.18665](https://arxiv.org/abs/2406.18665),
  [arXiv:2502.11021](https://arxiv.org/abs/2502.11021)); pluggable
  Process Reward Model adapter (Qwen2.5-Math-PRM lessons,
  [arXiv:2501.07301](https://arxiv.org/abs/2501.07301)); benchmark
  adapters for τ-Bench ([`sierra-research/tau2-bench`](https://github.com/sierra-research/tau2-bench))
  and Terminal-Bench 2.0 ([`harbor-framework/terminal-bench-2`](https://github.com/harbor-framework/terminal-bench-2)).
- **v1.9 (additions)** — Software Org Mode with first-class Roles +
  SOPs (MetaGPT [arXiv:2308.00352](https://arxiv.org/abs/2308.00352)
  + ChatDev [arXiv:2307.07924](https://arxiv.org/abs/2307.07924));
  Voyager-style autonomous skill curriculum
  ([arXiv:2305.16291](https://arxiv.org/abs/2305.16291)); EAGLE-3
  speculative-decoding profile for the local-OSS ladder
  ([arXiv:2503.01840](https://arxiv.org/abs/2503.01840), up to ×6.5
  speedup on chat / reasoning models).
- **v2.0 "Search + Web"** — intra-attempt MCTS via SWE-Search
  ([arXiv:2410.20285](https://arxiv.org/abs/2410.20285), +23 % rel.
  SWE-bench across five models); first-class Computer-Use browser
  sandbox running inside the v1.9 microVM (Anthropic Computer Use,
  [OSWorld arXiv:2404.07972](https://arxiv.org/abs/2404.07972)).
- **v1.5 carry-over** — GDPval ([arXiv:2510.04374](https://arxiv.org/abs/2510.04374))
  and SWE-Lancer ([`openai/SWELancer-Benchmark`](https://github.com/openai/SWELancer-Benchmark))
  evaluation adapters ship alongside SWE-bench Pro and LoCoEval.
- **Stretch (post-v2.5)** — 8-hour continuous autonomous run profile
  (GLM-5.1-style sustained autonomy); DSPy-compiled skill bodies
  ([`stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy));
  SWE-RL-format outcome-RL training corpus
  ([`facebookresearch/swe-rl`](https://github.com/facebookresearch/swe-rl)).

Stretch (post-v2.5): persistent autonomous worker mode
(`lyra serve --watch`), Phantom-inspired
([`ghostwright/phantom`](https://github.com/ghostwright/phantom)).

## [Unreleased] — v1.7.3 "Cross-Repo Convergence — Phase A" (`v0.3.3-dev`)

**Phase A flips 12 v1.7.2 scaffolds to real implementations.** The
v1.7.2 audit-and-fusion pass shipped scaffolds-with-tests for 15
features so interfaces could stabilise; v1.7.3 Phase A keeps the
TDD discipline (RED contract test → GREEN minimal implementation)
and turns 12 of those scaffolds into real, opt-in optional-dep code.
Every new code path raises `FeatureUnavailable` when its underlying
SDK is missing, so the base install stays lean. Test suite grows
**+77** (798 → **875** passing; 12 git-sandbox-dependent tests
deselected on this host, identical pre-existing infrastructure
constraint).

### Added — Context + subagents + todos

- **Real `/compact` summariser.** `lyra_core.context.compactor`
  ships `compact_messages(messages, *, llm, keep_last, max_summary_tokens)`
  returning a `CompactResult(kept_raw, summary, dropped_count, summary_tokens)`.
  System / SOUL turns are preserved; only the body is summarised so
  archive-then-replace is safe.
- **`/context` token-bar grid.** `lyra_core.context.grid.render_context_grid`
  produces a monospaced bar chart of token usage by message track
  (system / user / assistant / tool) — ANSI-free for clean test
  assertions, opt-in colour for live REPL.
- **`/agents` + `/spawn` real on `SubagentRegistry`.** A
  `SubagentRegistry` (`spawn`, `list`, `get`, `cancel`) tracks
  `SubagentRecord(id, parent_id, status, started_at, finished_at,
  result)`; an injected `task` callable does the heavy lifting so the
  registry stays decoupled from `make_task_tool`. Replaces the v1.7.2
  print-only stubs.
- **`TodoWrite` tool + atomic `TodoStore`.** The Claude-Code-shaped
  tool (`make_todo_write_tool`) writes through `TodoStore` which uses
  `<path>.tmp → rename` so on-disk lists are never half-written.
  Supports `merge=true` (upsert by id) and `merge=false` (replace).

### Added — Tools

- **LSP backend real.** `MultilspyBackend` lazily starts a real
  language server via `multilspy`, with `MockLSPBackend` for
  deterministic unit tests. Both implement `LSPBackend` so the
  v1.7.2 LSP tool contract stays unchanged.
- **Plugin runtime loader.** `PluginRuntime` discovers manifests from
  a search path, lazily imports `LoadedPlugin` entry points, and
  dispatches events to subscribed plugins with per-plugin exception
  isolation (one bad plugin can't crash the bus).
- **Real `DockerBackend`.** A docker-py wrapper that runs each
  command in a fresh container, kills + removes on `timeout_ms`, and
  surfaces `(exit_code, stdout, stderr, duration_ms, truncated)` per
  the `TerminalBackend` protocol. Pluggable `client` + `timeout_exception`
  for unit tests without a live daemon.
- **`WebSearch` + `WebFetch` tools.** `make_web_search_tool` accepts
  any `provider(query, n) -> [{title, url, snippet}]` callable
  (default: DuckDuckGo HTML via httpx + bs4); `make_web_fetch_tool`
  fetches a URL via an injectable `http` client, strips HTML to
  readable text, enforces `max_chars` truncation, and refuses
  `file://` / `javascript:` schemes for safety. 4xx/5xx are surfaced
  in the result, never raised.

### Added — Channels + cron + observability

- **Telegram adapter real Bot API.** `TelegramAdapter` keeps the
  v1.7.2 stub path for existing tests but adds an HTTP path when
  `http=` is injected or `use_http=True` is set. `poll()` calls
  `getUpdates` with offset tracking; `send()` posts `sendMessage`;
  failures raise `GatewayError` (never raw httpx types).
- **Cron daemon.** `CronDaemon.tick(now=...)` is deterministic for
  unit tests (no wall-clock dependency) — fires every active job
  whose `next_run_at <= now`, isolates runner exceptions, removes
  one-shot jobs, and reschedules recurring jobs through the parsed
  `Schedule`. `start()` / `stop()` manage a daemon thread when the
  process actually wants background ticking.
- **`/search` slash UI on FTS5.** A new `_cmd_search` slash command
  in `lyra_cli.interactive.session` recalls hits via an injected
  `InteractiveSession.search_fn` (clean K-cap at 50, default 5,
  optional `--k=N`, "(no matches)" path, "unavailable" path when
  unwired). Registered in the `session` category.
- **`OpenTelemetryCollector`.** A real OpenTelemetry SDK bridge
  implementing the existing `Collector` protocol — converts HIR span
  dicts into OTel spans on an injected `tracer_provider`, with
  primitive coercion for non-OTel-legal attribute values.
  `OTLPExporter` keeps using it, so the same exporter now fans out
  to Jaeger / Honeycomb / Datadog when the real provider is wired.

### Added — Optional-dependency discipline

- New shared sentinel `lyra_core.lsp_backend.errors.FeatureUnavailable`
  is raised by every new code path when its underlying SDK is missing
  (`lyra[lsp]`, `lyra[docker]`, `lyra[web]`, `lyra[otel]`). Imports
  remain lazy so the base install stays lean and unit tests do not
  require any of the optional extras.

### Changed

- **`docs/feature-parity.md` v0.3 snapshot.** Flipped 12 cells from
  `stub`/`scaffold` to `✓ shipped (v1.7.3)` with the corresponding
  symbol + test file, added a v1.7.3 §5b delta table, and refreshed
  the verification snapshot at the top of the doc to reflect the
  combined v1.7.2 + v1.7.3 closure.

### Test counts

- v1.7.3 Phase A: **+77 tests** across 12 new contract files
  (compactor, grid, subagent registry, todo write, LSP multilspy,
  plugin runtime, docker backend, web tools, telegram HTTP, cron
  daemon, `/search` slash UI, OTel collector).
- Whole suite: **875 passed**, 0 failures, 0 xfails (12 git-sandbox
  tests deselected — pre-existing host constraint, unrelated to the
  v1.7.3 surface).

## [Unreleased] — v1.7.2 "Integrity + Fusion" (`v0.3.2-dev`)

**Audit-driven honesty pass and cross-repo feature fusion.** A
verification sweep of `docs/feature-parity.md` against the three
`.ui-refs/` repos (`claw-code`, `hermes-agent`, `opencode`) surfaced a
handful of overclaims and undercounts; this release corrects the
table, fills in the six small CLI features that were already wired
but mis-labelled "NOW", and scaffolds the seven larger subsystems
that were genuinely missing. Test suite grows **+116** (610 → **726
passing**).

### Added — AgentLoop + REPL

- **`post_tool_call` plugin hook** fires after every tool dispatch
  with a `ToolResultCtx(result=…)` — including tool raises — so
  auditors and telemetry plugins can react to real outcomes, not
  just intents. New tests lock the before/after ordering and the
  "hook still runs on tool exceptions" invariant.
- **Hermes-compatible slash aliases.** `/compact` ↔ `/compress`,
  `/cost` ↔ `/usage`, `/stats` ↔ `/insights`, `/theme` ↔ `/skin`.
  Fixes the pre-1.7.2 misassignment where `/usage` was aliased to
  `/context`; parameterised regression test pins this shape.
- **`/cron` scheduled automations scaffold** (`list|add|remove|pause|
  resume|run|edit`). Core is in `lyra_core.cron` (schedule parser for
  one-shot / every-N / 5-field cron, atomic JSON `CronStore` with
  add / pause / edit / add-skill / remove-skill). CLI dispatcher is
  in `lyra_cli.interactive.cron.handle_cron` and wired into the
  REPL command registry via `_cmd_cron`; jobs default to
  `<repo>/.lyra/cron/jobs.json` (override via
  `LYRA_CRON_JOBS_PATH`).
- **Git-worktree isolation on the `task` tool.** `make_task_tool`
  now accepts a `worktree_manager` plus a `worktree: bool` flag; the
  child `AgentLoop` runs inside an allocated worktree, and cleanup
  is guaranteed in a `finally` even when the child raises. Closes
  v1 Phase 7 block 10.

### Added — v1.5 medium features

- **`codesearch` tool** (opencode parity). Ripgrep-backed with a
  pure-Python fallback; returns structured `{path, line, column,
  text}` hits, skips `.git/node_modules/.venv/…`, honours
  `case_insensitive` and `regex` flags, and surfaces an `error`
  field instead of raising on empty pattern.
- **`apply_patch` tool** (Anthropic v4 envelope). Parses `*** Begin
  Patch` / `*** End Patch` with `*** Add|Update|Delete File:`
  verbs, confines writes to `repo_root`, refuses path escapes, and
  returns structured `{ok, files_written, files_deleted, error}`.
- **LSP tool contract tests.** The pre-existing `lsp.py` scaffold
  now has five contract tests locking the JSON schema, XML-shaped
  diagnostics, delegation to the backend, unknown-op error
  handling, and the "no backend configured" path — so the real
  backends (multilspy / pygls) can slot in without regressing the
  surface.

### Added — v1.7 / v1.8 larger subsystems (scaffold + RED tests)

- **ACP (Agent Client Protocol) bridge.** `lyra_core.acp.AcpServer`
  is a JSON-RPC 2.0 dispatcher with notification support, `AcpError`
  mapping to error responses, and a streaming `serve(lines)`
  generator. Hooks the OpenCode-style `lyra acp` stdio server for
  Zed / JetBrains IDEs.
- **Multi-channel gateway adapter layer.** `lyra_core.gateway.ChannelAdapter`
  Protocol plus `InboundMessage` / `OutboundMessage` normals; a
  `TelegramAdapter` stub implements the contract with connect/poll/
  send state machine and wrong-platform rejection.
- **Plugin manifest loader** (`.claude-plugin` / `.lyra-plugin` /
  `plugin.json`). `lyra_core.plugins.load_manifest` and
  `validate_manifest` enforce the required `(name, version, entry)`
  triple and typed `hooks|tools|slash_commands|skills` lists; the
  resulting `PluginManifest.kinds` summarises the plugin's declared
  capabilities.
- **Multi-backend terminal execution.** `lyra_core.terminal.TerminalBackend`
  Protocol + `LocalBackend` (subprocess, timeout → `truncated=True`,
  missing-binary → `TerminalError`), plus stubs for `DockerBackend`,
  `ModalBackend`, `SSHBackend`, `DaytonaBackend`,
  `SingularityBackend` that raise a clear scaffold error pointing at
  the v1.7 Phase 11 implementation blocks.
- **Mock-LLM parity harness** (`lyra_core.mock_llm`). `ScriptedLLM`
  replays scripted `(expected-user-substring, response)` cases
  against either `.generate(...)` or `.stream_generate(...)`,
  records every call, and `.assert_exhausted()` catches silent
  scenario drift. Enables claw-code-style E2E CLI tests without
  hitting the network.
- **RL / Atropos trajectory scaffold** (`lyra_core.rl`).
  `TrajectoryRecorder` persists `(session_id, turn, prompt, action,
  reward, metadata)` as append-only JSONL; `make_rl_list_environments_tool`
  exposes the three default envs (`gsm8k`, `mbpp`, `swebench-lite`)
  as an LLM-callable tool with a JSON schema.
- **`notebook_edit` tool** (claw-code parity). Replace / insert /
  delete / convert operations on `.ipynb` cells by `cell_id` or
  `index`; writes back valid `nbformat` JSON and refuses any path
  outside `repo_root`.
- **`pdf_extract` tool** (claw-code parity). Magic-byte validation,
  `pypdf` → `pdfminer` backend cascade, `max_chars` truncation, and
  a structured `{ok, text, truncated, length}` payload.

### Changed

- **`docs/feature-parity.md` audit** — corrected the hermes MCP
  server cell (— → ✓), tagged honest slash-rename aliases (hermes
  `/compress`, `/usage`, `/insights`, `/skin`; opencode `/new`,
  `/themes`, `/models`), noted opencode's worktree integration as
  *partial* (not yet wired into `Task`), and flipped
  `PostToolUse` / `@file` / multi-line input / external editor
  (`Ctrl+G`) / `/keybindings` / `/cost` / `/stats` / prompt
  continuation glyph from "NOW" to their real "✓ shipped" state
  after cross-checking the code.

### Test counts

- Phase B (CLI hooks + aliases + prompt polish): +16 tests.
- Phase C (LSP + codesearch + apply_patch + worktree-on-task +
  `/cron`): +56 tests.
- Phase D (ACP + gateway + plugin manifest + terminal + mock-LLM +
  RL + NotebookEdit + PDF extract): +60 tests.
- Whole suite: **726 passed**, 0 failures, 0 xfails.

## [Unreleased] — v1.7.1 "Lyra" (`v0.3.0-dev`)

**Second rename: `open-harness → lyra`.** v1.7 was a transitional
build — the name was descriptive but generic. v1.7.1 settles the
final brand as **Lyra** (a **L**ightweight **Y**ielding **R**easoning
**A**gent), ships a four-letter ASCII-Shadow logo that fits any
terminal, and introduces a two-letter shell alias `ly`. Every
feature landed during v1.7 (agent loop, skill self-creation,
SQLite+FTS5 session store, unified command registry, claw-code /
opencode UI polish, provider registry + LSP tool) survives unchanged
— only the brand identity, CLI entry points, module namespaces, and
state directory move. Test suite grows from **596 → 601+** (new
contract tests for the chained migration and LYRA brand scan).

### Added

- **Chained legacy-state migrator.** `lyra_core.migrations.migrate_legacy_state`
  (orchestrator in `lyra_core.migrations.__init__`) walks
  `RepoLayout.legacy_state_dirs` newest-first — `.open-harness/` then
  `.opencoding/` — and stops at the first existing legacy dir. Lets a
  v1.6 user skip the v1.7 hop entirely.
- **Distinct migration markers.** `.lyra/MIGRATED_FROM_OPEN_HARNESS`
  vs `.lyra/MIGRATED_FROM_OPENCODING` so the source of the migration
  is preserved for audit (each file also carries a one-line provenance
  note). Corresponding constants `MARKER_FROM_OPEN_HARNESS` and
  `MARKER_FROM_OPENCODING` in `lyra_core.migrations.state_v1`.
- **Short CLI alias `ly`.** Paired with the primary `lyra` binary via
  `[project.scripts]`. Two-letter alias was chosen over `oh` (the v1.7
  alias) because it's silent in error messages and doesn't collide
  with `op` (1Password) / `oc` (OpenShift) / `oh` (interjection).
- **Redrawn banner.** New ANSI-Shadow "LYRA" wordmark (30 cols × 6 rows,
  down from "OPEN-HARNESS" at 99 × 6). Fancy-panel threshold drops from
  108 cols → 40 cols so every modern 80-col shell gets the gradient
  panel, not the compact fallback. Compact panel floor drops from 40
  → 24 cols with a terser hint variant (`/help · /status · ^D`) for
  sub-48-col panes.
- **Brand-identity contract (v2).** `test_brand_identity.py` now
  scans for BOTH `opencoding*` and `open-harness*` tokens and asserts
  the tree at `projects/lyra/`. Legitimate legacy references (this
  CHANGELOG, the migration guide, the migration modules themselves,
  `RepoLayout.legacy_state_dirs`) are on an explicit allowlist or
  carry the `lyra-legacy-aware` opt-out marker.
- **Chained-migration contract test.** `test_state_dir_migration_v2.py`
  locks the orchestrator behaviour: prefers the newer legacy dir,
  writes the right marker per source, is idempotent across repeat
  invocations.

### Changed

- Default state directory is **`.lyra/`** (was `.open-harness/` in v1.7,
  `.opencoding/` in v1.6). Existing repos get an automatic, idempotent,
  chained migration on first run; both legacy trees stay on disk for
  rollback.
- CLI entry point is **`lyra`** (was `open-harness` / `opencoding`);
  the new `ly` alias points to the same Typer app.
- Python import namespace: `from lyra_core …` / `from lyra_cli …`
  (was `open_harness_core` / `opencoding_core` and their CLI siblings).
  Old names are **not** aliased — imports from the legacy namespaces
  raise `ImportError` by design.
- Entry-point group for plugins: **`lyra.plugins`** (was
  `open_harness.plugins` / `opencoding.plugins`).
- Per-skin `welcome` strings tightened to ≤ 20 chars each so the
  36-col banner panel renders a clean right-aligned subtitle. The
  longer "Type /help for commands" hint now lives in the banner's
  dedicated hint row below the panel.

### Migrations

- **State directory (v2, chained).**
  `lyra_core.migrations.migrate_legacy_state(layout)` returns
  `(performed: bool, source: Path | None)`. On first run it copies the
  newest legacy dir to `.lyra/`, writes the appropriate
  `MIGRATED_FROM_*` marker, and preserves the original for rollback.
  Safe to invoke repeatedly.
- **Primitive migrator.** `lyra_core.migrations.state_v1.migrate_state`
  now accepts `marker_name=MARKER_FROM_OPEN_HARNESS |
  MARKER_FROM_OPENCODING`; default stays the opencoding marker for
  backwards contract with v1.7 callers.
- **Docs.** Full migration manual in
  [`docs/migration-to-lyra.md`](docs/migration-to-lyra.md) covers
  BOTH legacy versions (`.opencoding/` from v1.6 and `.open-harness/`
  from v1.7). The old `migration-from-opencoding.md` has been folded
  into it. Git `log --follow` reproduces file history across both
  renames.

### Tested

- **601+ tests** green (up from 596 at v1.7 tip). New contract files
  for v1.7.1: `test_state_dir_migration_v2` (11 cases covering the
  orchestrator), `test_brand_identity` extended to assert `projects/lyra/`
  and the combined legacy regex. All banner tests re-pinned against
  the 40-col fancy threshold.
- `ruff` and `pyright` clean across all five `lyra-*` packages.

### Not in this release

- Full SemaClaw/Skill-Creator v2 (stays scoped to the Planned v1.7
  block below).
- NGC context compactor (Planned v1.7, Phase 23).
- Production `multilspy` wiring — the LSP tool surface ships, but the
  backend adapters are stubbed pending an LSP-server integration pass.

## [Unreleased] — v1.7 "Full fusion" (superseded by v1.7.1)

> **Historical record only.** v1.7 was the **`open-coding →
> open-harness` rename and AI-assistant fusion** milestone. The
> project name, packages, CLI entry points, module namespaces, and
> state directory all moved to `open-harness`; the runtime gained an
> explicit agent loop, skill self-creation, SQLite+FTS5 session
> store, unified command registry, claw-code / opencode UI polish,
> and a provider registry with capability metadata. Test suite grew
> from **310 → 596** tests, all green. Before this release ever
> shipped, the brand was finalized as **`lyra`** in v1.7.1 (above).
> Every feature below survives unchanged; only the name and state
> dir changed again.

### Added

- **Phase 1 — Rename `open-coding → open-harness`.**
  - New top-level project directory `projects/open-harness/` (subsequently
    renamed again to `projects/lyra/` in v1.7.1).
  - Packages renamed: `open-harness-core`, `open-harness-cli`,
    `open-harness-skills`, `open-harness-mcp`, `open-harness-evals`
    (import paths follow: `open_harness_core`, `open_harness_cli`,
    etc.). **Superseded in v1.7.1** by `lyra-*` / `lyra_*`.
  - CLI entry points: primary `open-harness` **plus** short alias
    `oh`. **Superseded in v1.7.1** by `lyra` + `ly`.
  - State directory moves from `.opencoding/` → `.open-harness/`.
    `open_harness_core.migrations.state_v1.migrate_state` runs at
    first startup, performs a recursive copy (not a mv), and writes
    `.open-harness/MIGRATED_FROM_OPENCODING` for idempotency.
    **Superseded in v1.7.1** by the chained `migrate_legacy_state`
    orchestrator landing in `.lyra/`.
  - New `open_harness_core.paths.RepoLayout` centralizes state-dir
    resolution. **Renamed to `lyra_core.paths.RepoLayout` in v1.7.1**
    with the `legacy_state_dirs` property added.
  - Banner redrawn: ANSI-Shadow "OPEN-HARNESS" wordmark (99 cols),
    cyan→indigo→magenta aurora gradient, `CLI: open-harness (alias: oh)`
    row. **Superseded in v1.7.1** by the compact "LYRA" logo (30 cols).
- **Phase 2 — Agent loop primitives (hermes pattern).**
  - `lyra_core.agent.loop.AgentLoop` with
    `run_conversation(messages, session_id, *, tools, llm, plugins)`
    mirroring `NousResearch/hermes-agent`'s outer loop.
  - `IterationBudget` dataclass — explicit caps on tool-call rounds,
    wall-clock, and token usage; stops the loop with a structured
    `TurnResult` instead of crashing.
  - Plugin hook protocol (`lyra_core.plugins.Plugin`) — four hooks
    (`on_session_start`, `pre_llm_call`, `post_llm_call`,
    `on_session_end`) plus `discover_plugins()` reading the
    `lyra.plugins` entry-point group.
  - Task-tool fork (`lyra_core.tools.task.make_task_tool`) —
    opencode-style subagent spawner with
    `subagent_type ∈ {general, plan, explore}` backed by a fresh
    child `AgentLoop`, isolated from the parent's context.
- **Phase 3 — Skill self-creation loop.**
  - `AgentLoop` tracks `_iters_since_skill`: increments on each
    tool-loop iteration when `skill_manage` is registered, resets
    when the LLM actually calls `skill_manage`, and crosses the nudge
    threshold (`skill_nudge_interval`, default 12) to schedule a
    background review.
  - `lyra_skills.review.background.spawn_skill_review(ctx)` — runs a
    forked `AgentLoop` off the critical path (via injectable
    `review_executor`) so the user never blocks on skill
    consolidation.
  - `lyra_skills.tools.skill_manage` — LLM-callable
    `skill_manage(op, …)` with `list` / `create` / `patch` / `delete`
    across `./.lyra/skills/` (project) and `~/.lyra/skills/`
    (user-global).
  - `SkillRouter.system_prompt_index()` — one-line-per-skill index
    for the system prompt so the LLM knows which skills already exist
    before proposing new ones.
- **Phase 4 — SQLite + FTS5 session store.**
  - `lyra_core.sessions.store.SessionStore` — single SQLite file at
    `.lyra/state.db` (WAL mode). Schema: `sessions(id, created_at,
    meta_json)`, `messages(id, session_id, role, content, tool_name,
    created_at)`, `messages_fts` FTS5 virtual table.
  - Append-only `add_message`, transactional `end_session`,
    `list_sessions(limit, order_by)`, `search(query, limit)`
    returning `MatchResult` rows with `bm25` ranking.
  - `lyra_core.sessions.jsonl_migration.migrate_jsonl_sessions` —
    one-shot migrator from `~/.opencoding/sessions/*.jsonl` (v1.6
    legacy) with a `JSONL_MIGRATED` manifest marker that records the
    already-ingested file names so re-runs append only new JSONL.
    Explicitly tagged `lyra-legacy-aware`.
  - Recall tool `lyra_core.tools.session_search.make_session_search_tool`
    — LLM-callable `session_search(query, limit, summarize)` doing
    FTS lookup followed by an optional LLM summarize pass (hermes
    recall-tool trick) so the agent gets the signal without the token
    bloat.
- **Phase 5 — Unified command registry.**
  - `lyra_cli.commands.registry.COMMAND_REGISTRY` — single source of
    truth (tuple of `CommandSpec` dataclasses). Drives the REPL
    completer, `/help`, the dispatcher, plugin-contributed commands,
    and namespaced `/mcp:*` and `/skill:*` routes.
  - Aliases and name-uniqueness enforced at module-import time;
    scattered slash-handlers are gone.
- **Phase 6 — UI polish (Claude Code + claw-code + opencode fusion).**
  - `lyra_cli.interactive.tool_card` — claw-code-style tool-call card
    (cyan border, bold tool name, styled bash chip for shell
    invocations, error-accent row for failed calls).
  - `lyra_cli.interactive.stream.MarkdownStreamState` — fence-aware
    streaming Markdown buffer; never flushes mid-fence, so code
    blocks don't flicker while streaming.
  - `lyra_cli.interactive.spinner.ThreadedSpinner` — claw-code Braille
    spinner that self-animates in a daemon thread (fixes the
    "tick-once" bug where a blocking call froze the frame).
  - `lyra_cli.interactive.keybinds.LeaderChords` — opencode-style
    leader-chord keybindings over `prompt_toolkit` (e.g.
    `Ctrl-G m` → `/model`).
  - `lyra_cli.interactive.status_source.StatusSource` — contextual
    footer (`cwd · mode · model · turn · cost`) rendered in the slim
    toolbar.
  - Claude Code welcome card, boxed input, inline-bullets, slim
    toolbar all polished to match `claude` aesthetics.
- **Phase 7 — Provider registry + optional LSP tool.**
  - `lyra_core.providers.registry.PROVIDER_REGISTRY` — pure-data tuple
    of `ProviderSpec` entries (OpenAI, Anthropic, Google, xAI, Groq,
    Mistral, DeepSeek, Ollama, …). Each spec carries `env_vars`,
    `default_model`, `context_window`, `supports_tools`,
    `supports_reasoning`, `supports_streaming`, `supports_vision`,
    `notes`, and a `models` tuple.
  - Helpers: `get_provider(key)`,
    `providers_by_capability("supports_reasoning")`.
  - `lyra_core.tools.lsp.make_lsp_tool` — optional LSP tool exposing
    `lsp(operation, file, line, char)` for
    `diagnostics | hover | references | definition`. Diagnostics wrap
    in `<diagnostics file="…">…</diagnostics>` XML (opencode
    injection convention). Off by default — the factory raises
    `LSPUnavailable` unless `multilspy` / `pygls` is installed or a
    backend is injected.

### Changed

- Default state directory is `.open-harness/` (was `.opencoding/`).
  **Superseded in v1.7.1** by `.lyra/` with the chained migrator.
- CLI entry point was `open-harness` (alias `oh`). **Superseded in
  v1.7.1** by `lyra` (alias `ly`).
- Python import namespace was `from open_harness_core …`.
  **Superseded in v1.7.1** by `from lyra_core …`.
- Session history: `AgentLoop` drivers persist through `SessionStore`
  by default; JSONL session dumps are read-only and migrated on first
  touch.

### Migrations

- **State directory (v1, single-hop).** The v1.7 migrator handled
  only `.opencoding/` → `.open-harness/`. **Superseded in v1.7.1**
  by the chained orchestrator — see the v1.7.1 entry above.
- **JSONL sessions.** `migrate_jsonl_sessions(jsonl_dir, store)`
  parses `~/.opencoding/sessions/*.jsonl`, writes rows into SQLite,
  and drops a `JSONL_MIGRATED` manifest listing ingested files.
  Unchanged in v1.7.1 — still targets the v1.6 JSONL format.
- **Docs.** The v1.7 migration manual
  (`docs/migration-from-opencoding.md`) has been folded into the
  consolidated v1.7.1 guide
  [`docs/migration-to-lyra.md`](docs/migration-to-lyra.md) which
  covers both legacy brands.

### Tested

- **596 tests** green at v1.7 tip (up from 310 at start of v1.7).
  New contract files: `test_brand_identity`,
  `test_state_dir_migration`, `test_agent_loop_contract`,
  `test_skill_nudge_counter`, `test_session_store_sqlite_fts5`,
  `test_command_registry_unified`, `test_tool_card_renders_box`,
  `test_stream_markdown_fence_aware`, `test_spinner_animates_threaded`.
  All started as RED (TDD Phase 0) and turned GREEN as each
  implementation phase landed. **v1.7.1 adds** the chained-migration
  tests (`test_state_dir_migration_v2`) and extends
  `test_brand_identity` to scan for both legacy brands.
- `ruff` and `pyright` clean across all five packages at v1.7 tip,
  unchanged in v1.7.1.

### Not in this release

- Full SemaClaw/Skill-Creator v2 (stays scoped to the Planned v1.7
  block below).
- NGC context compactor (Planned v1.7, Phase 23).
- Production `multilspy` wiring — the LSP tool surface ships, but
  the backend adapters are stubbed pending an LSP-server integration
  pass.

## [Planned] — v1.7 "Self-Creating Harness" (`v0.3.0`, ~Q4 2026)

Scope planned (not yet implemented). Full spec in
[`docs/roadmap-v1.5-v2.md`](docs/roadmap-v1.5-v2.md) §1.5. Adopts two
April-2026 anchor works:

- **[Neural Garbage Collection](https://arxiv.org/abs/2604.18002)**
  (Li, Hamid, Fox, Goodman — Stanford, April 2026): cache-eviction
  and token generation are both discrete actions sampled from the
  LM, jointly optimized from outcome reward. 2–3× peak KV
  compression, 49.6% vs 21.2% next-best baseline on Countdown at
  2.4× compression.
- **[Anthropic Skill-Creator v2](https://github.com/anthropics/skills/tree/main/skills/skill-creator)**
  (Dec 2025 release, 121K stars, 176K installs): 4-agent creator
  loop (Executor / Grader / Comparator / Analyzer), iteration
  workspaces, `benchmark.json` artifacts, 60/40 train/test
  description optimizer.

### Planned additions

- **Phase 19 — Skill-Creator engine (`lyra_skills.creator.*`).**
  4-agent loop under `worktrees/`, iteration workspaces at
  `.lyra/creator/<skill>/iter_NNN/`, `benchmark.json` +
  `comparison.json` artifacts, `lyra skills create <name>` /
  `improve <name>` / `benchmark <name>` / `compare`.
- **Phase 20 — Reuse-first hybrid router
  (`lyra_skills.router.hybrid`).** BM25 + dense embeddings
  (BGE-small-en-v1.5 via SQLite-FTS5 + HNSW) + description match;
  explicit `NO_MATCH` / `AMBIGUOUS` / `MATCH` verdicts;
  `lyra skills route <query> --explain` surfaces per-component
  contributions and confidence.
- **Phase 21 — Trigger-eval corpus + description auto-optimizer
  (`lyra_skills.trigger_eval.*`).** Per-skill `triggers.jsonl`
  (should-trigger / should-not-trigger queries), 60/40 train/test
  split, bounded 5-iteration optimizer via LLM rewrite,
  `lyra skills tune <name>` + CI lint (`skills tune --lint`).
- **Phase 22 — In-session synthesis + skill lifecycle
  (`lyra_skills.synthesis.*`, `lyra_skills.lifecycle.*`).**
  Repetition detector (AST fingerprint; threshold ≥ 3 in ≤ 30
  turns), bundled-script detector, `/creator` slash command in the
  REPL, outcome attribution (`shapley_lite`), refine/retire
  proposals via `lyra skills doctor`. Absorbs what was previously
  v2 Phase 20 (self-refining skills).
- **Phase 23 — NGC-inspired context compactor
  (`lyra_core.context.ngc.*`).** Grow-then-evict cadence δ
  (default every 8 turns), block-level eviction on HIR events
  (tool call + result as a unit), budget-aware interoception in
  SOUL (`context_budget`, `context_used`, `eviction_cadence`,
  `cycles_until_evict`), LLM-driven rerank with `block_id` /
  `keep_score` / `rationale`, outcome logging to
  `compactor-outcomes.jsonl` (NGC-format ready for v2 Phase 28
  training-arena export), `lyra compactor` CLI + v1 compactor
  preserved as `--compactor=v1` fallback.

### Planned CLI surface

- `lyra skills create <name>` / `improve <name>` / `benchmark <name>`
  / `compare <a> <b>`.
- `lyra skills route <query> --explain` /
  `lyra skills tune <name>` / `lyra skills doctor`.
- `/creator` slash command inside the interactive REPL (Phase 13
  integration).
- `lyra compactor {run|status|explain <block-id>}` and
  `--compactor={ngc|v1}` flag.

### Planned metrics

- Skill-trigger recall ≥ 80% on a curated eval set.
- Creator converged pass-rate ≥ 90% within 5 iterations.
- NGC compactor ≥ 1.5× compression vs v1.5 compactor at ≤ 1pp
  success-rate cost on the dogfood corpus.

No release artifacts yet; implementation begins after v1.5
(`v0.2.0`) exits.

## [Unreleased] — v1.5 "Parity & Evidence"

Phased work against
[`docs/roadmap-v1.5-v2.md`](docs/roadmap-v1.5-v2.md). Each bullet
cites the phase that landed it.

### Added

- **Phase 13 — Interactive shell (`lyra`).** Running `lyra` with no
  arguments now drops into a Claude-Code-style REPL.
  - `lyra_cli.interactive.session` — pure `InteractiveSession` +
    `CommandResult` + `SLASH_COMMANDS` registry. Dispatch is TTY-free
    and unit-tested (no I/O, no prompt_toolkit). State: mode
    (`plan | run | retro`), model, turn counter, cost accumulator,
    input history, pending task.
  - Slash commands (15): `/help`, `/status`, `/mode`, `/model`,
    `/approve`, `/reject`, `/history`, `/clear`, `/skills`, `/soul`,
    `/policy`, `/doctor`, `/evals`, `/exit`, `/quit`.
  - `lyra_cli.interactive.banner` — Rich-rendered ASCII logo +
    tagline in a cyan panel; metadata block below (`Repo:`, `Model:`,
    `Mode:`). Plain-mode fallback emits ANSI-free text for CI
    captures and piped output.
  - `lyra_cli.interactive.driver` — prompt_toolkit loop with coloured
    prompt (`plan ›`, `run ›`, `retro ›`), bottom status bar
    (`mode │ model │ repo │ turn │ cost │ /help`), slash-command
    completer, and FileHistory at `.lyra/interactive_history`.
    Graceful fallback to `input()` when stdin/stdout isn't a TTY;
    EOF and Ctrl-D both exit cleanly.
  - `lyra_cli.interactive.completer` — prompt_toolkit
    `SlashCompleter` that completes from the live `SLASH_COMMANDS`
    registry.
  - Typer wiring: `app.callback(invoke_without_command=True)` plus
    `--repo-root` / `--model` options on the root;
    `no_args_is_help=False`.
  - New dep: `prompt_toolkit>=3.0` (pulled in transitively by the
    CLI package only).
- **Phase 12 — Public-benchmark adapters (`lyra-evals`).**
  - `lyra_evals.adapters.swe_bench_pro` — `PublicBenchmarkTask`,
    `SWEBenchProAdapter`, `load_swe_bench_pro`, `write_submission`.
    Submission JSONL is byte-compatible with Scale AI's ingestion
    (exactly `instance_id`, `model_name_or_path`, `model_patch` per
    line); extra keys raise.
  - `lyra_evals.adapters.loco_eval` — `LoCoEvalTask`,
    `ConversationDriver`, `LoCoEvalResult`,
    `score_requirement_coverage`. 50-turn driver tracks per-turn
    context usage and halts on budget overflow. Coverage is
    strict-set intersection, no partial credit.
  - `lyra_evals.snapshot` — VeRO-style `HarnessSnapshot` (commit SHA
    + package versions + policy SHA-256 + seed) + `snapshot_hash`
    stable fingerprint (order-independent over packages, sensitive
    to every other field).
  - `lyra_evals.contamination` — `ContaminationGuard` fail-closed on
    corpus-cutoff ≤ model-training-cutoff, fail-closed on unknown
    model cutoffs; `--allow-contaminated` leaves a warning record
    on the guard for retro consumption.
  - CLI: `lyra evals --corpus {swe-bench-pro,loco-eval} --tasks-path
    <jsonl> [--budget N] [--model name] [--output path]`. Helpful
    exit when `--tasks-path` is missing; no Docker / heavy dep
    required for unit tests.
- **Tests.** 56 new tests across Phases 12 and 13. **Phase 12 (29):**
  4 eval red-test files — `test_swebench_pro_adapter.py` (7),
  `test_loco_eval_adapter.py` (6), `test_contamination_guard.py` (6),
  `test_eval_harness_snapshot.py` (5) — plus 5 CLI smoke cases wiring
  `evals --corpus {swe-bench-pro,loco-eval}`. **Phase 13 (27):** 2
  interactive red-test files — `test_interactive_session.py` (21),
  `test_interactive_banner.py` (4) — plus 2 CLI smoke cases
  exercising the no-args launch and EOF-terminates-cleanly path.
  Full suite now 310 tests on Python 3.9, all green; ruff + pyright
  clean.

### Changed

- `lyra` with no arguments no longer prints the Typer help screen —
  it now launches the interactive shell. `lyra --help` and every
  subcommand are unchanged.

## [0.1.0] — 2026-04-22

The **walking-skeleton release**, shipped under the project's
original name `open-coding`: every block in the roadmap has
acceptance tests, 254 tests green, ruff clean, `make ci` reproducible
on a fresh checkout. Not on PyPI; installed editable from the repo.

### Added

#### Kernel (original `opencoding-core`, now `lyra-core`)

- Agent loop primitives via `harness_core`: `Agent`, `Tool`,
  `ToolRegistry`, `PermissionBridge`, hook framework (Pre/Post/Stop
  phases).
- Five native tools (`Read`, `Glob`, `Grep`, `Edit`, `Write`) with
  `repo_root` sandboxing and symlink-escape rejection.
- 5-layer context pipeline (`SOUL`, `STATIC_CACHED`, `DYNAMIC`,
  `COMPACTED`, `MEMORY_REFS`) with SOUL pin and naive compactor that
  strictly reduces token count.
- Procedural memory backed by SQLite FTS5, plus progressive-disclosure
  wrappers (`list_topics` / `get_topic` / `search_topic`) with
  token-bounded results.
- TDD gate contract: `RedProof` validator, coverage-regression gate
  with tolerance, post-edit impact map (`tests_for_edit` heuristics),
  escape-hatch audit log (JSONL).
- Two-phase verifier: objective (acceptance tests + forbidden files
  + coverage) and subjective (LLM-judge with structured rubric).
  Evaluator-family detection flags degraded evals; evidence validator
  rejects hallucinated file/line citations; cross-channel scan
  detects commented-out asserts in "passing" tests.
- Subagents + worktrees: `WorktreeManager` (orphan reconciliation),
  `FsSandbox` (glob-scoped writes, read-outside logging,
  symlink-escape rejection), `SubagentOrchestrator` (scope-collision
  detection, recursion-depth cap), three-way merge with optional LLM
  resolver and stalemate escalation.
- DAG Teams plugin: `validate_dag` (cycles / unknown deps / width
  budget / duplicate IDs), `Scheduler` (topological batches, failure
  propagation, park-on-risk hook).
- Safety monitor: windowed rule-based scanner for prompt injection,
  sabotage patterns, and secret exposure; duplicate-flag suppression.
- Flat HIR event schema with `from_dict`/`to_dict`/`validate_event`/
  `mask_secrets`. In-memory OTLP exporter. Retro-artifact Markdown
  builder.

#### Skills (original `opencoding-skills`, now `lyra-skills`)

- `SkillLoader` — frontmatter-aware parser for `SKILL.md`,
  later-root-wins precedence.
- `SkillRouter` — description-based routing with keyword overlap,
  light stemming, and a coding-verb synonym map.
- `SkillExtractor` — promotes successful trajectories to
  `SkillManifest` proposals (user-review gated).
- Four shipped packs: `atomic-skills` (5 basis skills), `tdd-sprint`
  (7-phase sprint), `karpathy` (think/simplicity/surgical/goal-driven),
  `safety` (injection / secret triage).

#### MCP (original `opencoding-mcp`, now `lyra-mcp`)

- JSON-RPC client `MCPAdapter` with timeout + response-shape
  validation.
- `FakeMCPServer` for in-process testing.
- `TrustBanner` + `guard_third_party_content` — wraps third-party
  output and flags injection phrases.
- `ProgressiveMCP` — umbrella-tool disclosure that surfaces MCP tools
  on demand.
- `LyraMCPApp` (originally `OpenCodingMCPApp`) — exposes
  `read_session` + `get_plan` as MCP server tools behind bearer
  auth.

#### Evals (original `opencoding-evals`, now `lyra-evals`)

- `Task` / `Report` / `EvalRunner` with drift gate.
- Three in-tree corpora: `golden_tasks`, `red_team_tasks`,
  `long_horizon_tasks`.
- Methodology pinned in `docs/benchmarks.md`.

#### CLI (original `opencoding-cli`, now `lyra-cli`)

- Typer app: `init`, `run`, `plan`, `doctor`, `retro`, `evals`,
  `session list`, `session show`.
- Plan Mode default-on with auto-skip for trivial tasks; plans
  written to `.lyra/plans/<session>.md` (originally
  `.opencoding/plans/`).
- `lyra evals --corpus {golden|red-team|long-horizon}
  [--drift-gate N] [--json]`.

### Tested

- 254 tests passing across 5 packages. Phase split:
  - Phase 1 kernel (79), Phase 2 plan mode (47), Phase 3 context +
    memory (13), Phase 4 TDD gate (18), Phase 5 verifier (14),
    Phase 6 skills (19), Phase 7 subagents (17), Phase 8 DAG teams
    (13), Phase 9 safety + HIR + OTLP + retro (14), Phase 10 MCP
    (14), Phase 11 evals (6).
- `ruff check packages` clean (UP / B / E / F / RUF rule sets, py39
  target).
- `pyright` in basic mode across `lyra-core` + `lyra-cli`.
- Reproducible `make ci` target.

### Infrastructure

- `.github/workflows/ci.yml` — lint + test + evals smoke + CLI happy
  path on Python 3.10 / 3.11 / 3.12.
- Monorepo `pyproject.toml` with strict pytest collection
  (`python_functions = "test_*"`) so helpers like `tests_for_edit`
  are never collected.

### Not in this release

Explicitly deferred to v1.5 / v2:

- Remote subagent runners (Modal / Fly execution backends).
- Shallow-worktree optimization for large monorepos.
- PII-aware masking beyond the current regex-based secret detector.
- SWE-bench Verified runner glue.
- Agent-World-style environment synthesis.
- Multica team coordination / cross-repo skill sharing.
- Nightly GitHub Actions for full three-corpus benchmarks.
