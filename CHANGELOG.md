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

## v3.12.0 — 2026-05-09 — "Autonomy Loop — Stop hook + AgentContract + Ralph runner" (unreleased — planning)

Roadmap source: [`LYRA_V3_12_AUTONOMY_LOOP_PLAN.md`](LYRA_V3_12_AUTONOMY_LOOP_PLAN.md).
Closes the field-level *stop-and-ask* gap — the user-visible behaviour
that every coding-agent harness (Claude Code, hermes-agent, OpenClaw,
Lyra v3.11) finishes a task and stops, forcing the user to type
"continue" forever.

Eight phases L312-1..L312-8 staged across six increments:

- **L312-1** — `Stop` / `SubagentStop` lifecycle event with
  `stop_hook_active` infinite-loop guard. The seam every other phase
  composes through.
- **L312-2** — `lyra ralph <prd.json>` Lyra-native Ralph runner
  (worktree-isolated, hook-composed, contract-bounded; refuses
  `--dangerously-skip-permissions`).
- **L312-3** — `/loop` slash + `lyra loop` CLI with cache-aware
  intervals (rejects 300 s as worst-of-both: under-TTL or over-TTL only).
- **L312-4** — `AgentContract` envelope (FULFILLED / VIOLATED /
  EXPIRED / TERMINATED state machine + `BudgetEnvelope`); always
  present; closes the $47 k recursive-clarification-loop incident class
  documented in [`docs/305-agent-contracts-formal-framework.md`](../../docs/305-agent-contracts-formal-framework.md).
- **L312-5** — `HUMAN_DIRECTIVE.md` async-control file watcher per
  iteration boundary.
- **L312-6** — `CronDaemon.run_event_loop()` sleep-until-next-fire
  mode + `after sess-X`, `on git-push`, `on signal SIGUSR1` triggers.
- **L312-7** — `lyra autopilot` long-running supervisor with SQLite
  checkpointing + explicit-only resume.
- **L312-8** — `lyra-plugin-autocontinue` Stop-hook plugin pack with
  the four 2026 best-practice safeguards (flag + cap + watermark +
  predicate).

**Canon deep-dives shipped alongside the plan**:
[`docs/305-agent-contracts-formal-framework.md`](../../docs/305-agent-contracts-formal-framework.md)
(arXiv 2601.08815, COINE 2026),
[`docs/306-stop-hook-auto-continue-pattern.md`](../../docs/306-stop-hook-auto-continue-pattern.md),
[`docs/307-ralph-loop-variations-2026.md`](../../docs/307-ralph-loop-variations-2026.md),
[`docs/308-autonomy-loop-synthesis.md`](../../docs/308-autonomy-loop-synthesis.md).

**Identity preserved.** No v3.11 surface changes; v3.12 is additive.
Existing sessions terminate as before unless a `Stop` hook is registered.

## v3.11.0 — 2026-05-09 — "SOTA 2026 — Agent Teams + Software 3.0 bundle" (unreleased — first increment)

Roadmap source: [`LYRA_V3_11_SOTA_2026_PLAN.md`](LYRA_V3_11_SOTA_2026_PLAN.md).
First v3.11 increment lands two of nine phases:

### Added — L311-1/2/3: Anthropic Agent Teams parallel runtime

Imports the Feb-2026 Anthropic Agent Teams architecture
([`docs/250-anthropic-agent-teams.md`](../../docs/250-anthropic-agent-teams.md))
into Lyra. Coexists with the existing MetaGPT *sequential* `TeamPlan`
in `lyra_core.teams.registry`; the two shapes are complementary.

- **`lyra_core.teams.agent_teams`** — `LeadSession` (lead-and-spokes
  orchestrator), `TeammateSpec` (frozen spec), `TeamReport` (shutdown
  snapshot), `Executor` (LLM-seam callable). Cost guard `LBL-AT-COST`
  warns at K=6 teammates and blocks at K=10 unless
  `allow_unsafe_token_overage=True`. Bright-lines for `LBL-AT-NEST`
  (no nested teams) and `LBL-AT-PROMOTE` (no leadership transfer).
- **`lyra_core.teams.shared_tasks`** — `SharedTaskList` (filesystem
  with POSIX `flock`), `Task` state machine
  (`pending → in_progress → completed | blocked`), automatic
  dependency unblocking, atomic write-temp-then-rename frontmatter
  serialization, stdlib-only YAML frontmatter parser.
- **`lyra_core.teams.mailbox`** — `Mailbox` per-recipient inbox,
  append-only message files, `mark_read` / `purge_older_than`,
  idle-notification message kind.
- **HIR events** emitted: `team.create` / `team.spawn` /
  `team.task_created` / `team.task_completed` / `team.task_failed` /
  `team.teammate_idle` / `team.shutdown` — every existing trace
  subscriber (LangSmith, Langfuse, OTel) lights up without code
  changes.
- **30 new tests** covering spawn lifecycle, K-cap (warn + block),
  shared-list state machine, dependency unblocking, mailbox
  send/read/mark-read, idle notifications, lifecycle event emission.

### Added — L311-4/5/6: Software 3.0 SourceBundle + Agent-Installer + Verifier-Coverage

Imports the Karpathy IICYMI Software 3.0 paradigm
([`docs/239-software-3-0-paradigm.md`](../../docs/239-software-3-0-paradigm.md)
§(b) §(d)) and verifiability framing
([`docs/238-karpathy-agentic-engineering-shift.md`](../../docs/238-karpathy-agentic-engineering-shift.md)).

- **`lyra_core.bundle.source_bundle`** — `SourceBundle` six-part
  artefact (persona + skills + tools + memory + evals + verifier)
  loaded from a directory + `bundle.yaml` manifest. Stable
  content-hash for `LBL-BUNDLE-IDEMPOTENT`. `LBL-BUNDLE-SIX`
  enforced by `validate()`. Stdlib-only minimal YAML parser (no
  PyYAML dep).
- **`lyra_core.bundle.agent_installer`** — `AgentInstaller`
  five-step pipeline (provision → register skills → wire tools →
  smoke-eval → attest). `LBL-AI-EVAL` fails closed below
  `smoke_eval_threshold` (default 0.95). `LBL-AI-IDEMPOTENT`
  short-circuits when `attestation.json` exists with the same bundle
  hash.
- **`lyra_core.bundle.attestation`** — `Attestation` dataclass +
  HMAC-SHA256 sign / verify (swappable for real Sigstore later).
  Constant-time signature compare via `hmac.compare_digest`.
  `LBL-AI-ATTEST` requires every install to emit a signed record.
- **`lyra_core.bundle.verifier_coverage`** — `VerifierCoverageIndex`
  per-domain aggregator surfacing `coverage_score = 0.4 *
  verifier_norm + 0.4 * pass_rate + 0.2 * eval_norm`. Score ≥ 0.7
  recommends `edit_automatically`; 0.4–0.7 → `ask_before_edits`;
  <0.4 → `plan_mode`. Operationalizes Karpathy's verifier-density
  framing as an `auto_mode` admit input.
- **24 new tests** covering bundle load + validate, six-part
  enforcement, hash stability, attestation sign/verify/tamper,
  installer happy path + idempotency + low-eval block, custom smoke
  runners, dual-use propagation, coverage-index scoring + admit
  recommendations.

### Cross-doc anchors

This increment composes:

- [`docs/250-anthropic-agent-teams.md`](../../docs/250-anthropic-agent-teams.md) — runtime spec.
- [`docs/239-software-3-0-paradigm.md`](../../docs/239-software-3-0-paradigm.md) — bundle paradigm.
- [`docs/238-karpathy-agentic-engineering-shift.md`](../../docs/238-karpathy-agentic-engineering-shift.md) — verifier framing.
- [`projects/CROSS_PROJECT_UPGRADE_PLAN_2026.md`](../CROSS_PROJECT_UPGRADE_PLAN_2026.md) — companion cross-project upgrade plan covering all 14 sibling projects.

### Added — L311-7: Four-axis scaling-laws aggregator

Operationalizes the 2026 scaling-law synthesis ([`docs/225`](../../docs/225-agent-era-scaling-synthesis.md))
as a roadmap input.

- **`lyra_core.meta.scaling_axes`** — `ScalingAxes` mutable record +
  `ScalingPosition` per-axis snapshot. Four axes: `pretrain` / `ttc` /
  `memory` / `tool_use`. Each axis exposes `score ∈ [0,1]`,
  `current` (human-readable state), `next_lever` (cheapest single
  upgrade), `cost_hint`, `benefit_hint`.
- **`best_lever()`** picks the axis with the highest cost-benefit
  ratio — answers *"which axis should I invest in next?"*
- **`render_scaling_table()`** for the eventual `/scaling` slash.
- **17 new tests** covering scoring, recommendation transitions per
  axis, validation of [0,1] ranges, and best-lever selection.

### Added — L311-8: Confidence-scored auto-memory tracker

Imports the Claude Code 2026 "instinct extraction" pattern
([`docs/62`](../../docs/62-everything-claude-code.md)).

- **`lyra_core.memory.confidence`** — `ConfidenceTracker` sidecar
  (`{root}/confidence.json` next to v3.7 `access_stats.json`).
  Per-entry `confidence ∈ [0,1]`, `seen_count`, `last_seen_ts`,
  `created_ts`, `extracted_by`. Append-only audit chain preserved;
  aggregates live in the sidecar.
- **Promotion / demotion**: `seen_count ≥ 3 ∧ confidence ≥ 0.85` →
  `PromotionEvent` to caller; `seen_count ≥ 1 ∧ confidence < 0.30 ∧
  age_days > 7` → `DemotionEvent`. Tracker emits events but does
  not perform the durable register / tombstone — that policy lives
  one layer up so the same tracker wires to different durable
  substrates.
- **HIR events** `confidence.promote` / `confidence.demote` emitted
  for every transition.
- **21 new tests** covering record validation, observe / decay
  clamping, promotion / demotion thresholds, listener event firing
  + error swallowing, persistence round-trip, corrupt-sidecar
  recovery.

### Added — L311-9: Cross-harness portable export

Imports the 2026 cross-harness extension contract ([`docs/07`](../../docs/07-model-context-protocol.md),
[`docs/239`](../../docs/239-software-3-0-paradigm.md)). Skills + hooks +
agents + rules + MCP form the de-facto portable surface — a single
SourceBundle now lights up across four harnesses.

- **`lyra_core.bundle.exporters`** — `Exporter` ABC plus four
  concrete exporters:
  - `ClaudeCodeExporter` → `~/.claude/{skills,agents,settings.local.json}/`.
  - `CursorExporter` → `.cursor/{rules,mcp.json}/`.
  - `CodexExporter` → `~/.codex/skills/{bundle}/AGENTS.md`.
  - `GeminiCLIExporter` → `.gemini/extensions/{bundle}/`.
- Each exporter:
  - Emits a `MANIFEST.{target}.{bundle}.txt` audit trail listing
    every file written.
  - Idempotently merges existing MCP server registries (Claude Code's
    `settings.local.json`, Cursor's `mcp.json`).
  - Enforces `LBL-EXPORT-NO-LEAK` — paths that resolve outside the
    target directory raise `ExportError`.
- **`resolve_exporter(target)`** picks the right exporter by name;
  `list_exporters()` enumerates registered targets.
- **12 new tests** covering registry, four-target layout assertions,
  idempotent settings merge, MCP server descriptor preservation,
  path-escape rejection, and an end-to-end "every exporter completes"
  assertion.

### Added — W1 + W2 sample bundles

Seven end-to-end runnable bundles realize the cross-project upgrade
plan's W1 + W2 waves ([`projects/CROSS_PROJECT_UPGRADE_PLAN_2026.md`](../CROSS_PROJECT_UPGRADE_PLAN_2026.md)):

**W1 (foundation):**

- **`projects/argus/bundle/`** — six-skill cascade router (BM25 →
  embedding → cross-encoder → KG-navigate) + HostAdapter +
  marketplace-fetcher; 15 golden traces; MCP server stub.
- **`projects/gnomon/bundle/`** — four-skill failure attributor
  (HIR attribute → classify → propose-patch → cross-harness bundle);
  10 golden traces; MCP server stub.
- **`projects/vertex-eval/bundle/`** — six-skill judge platform
  (Pass@k, Pass^k, judge-pool, PII-anonymizer, pairwise-decorrelation,
  rubric-registry); 12 golden traces; MCP server stub.

**W2 (high-leverage domain agents):**

- **`projects/orion-code/bundle/`** — six-skill autonomous coding
  agent (plan-mode + read/grep + edit/write + bash-allowlist +
  verifier-gate + team-coder role); 20 golden traces (incl. bright-line
  block probes); MCP server stub.
- **`projects/atlas-research/bundle/`** — five-skill long-horizon
  research agent (query-planner + citation-verifier + synthesis-rubric +
  faithfulness-gate + 3-spoke Agent Teams pattern); 15 golden traces;
  MCP server stub.
- **`projects/open-fang/bundle/`** — six-skill paper-research agent
  (paper-ingest + 5-tier verifier + 9-specialist cohort + backlink-rank +
  chaos-hooks + zero-LLM bootstrap); 12 golden traces; MCP server stub.
- **`projects/polaris/bundle/`** — six-skill long-running research
  partner (lifecycle + submission-engine + self-evolve + research-ops +
  20 bright-lines + domain shells); 12 golden traces; MCP server stub.

**21 parameterized tests** across the seven bundles assert: every
bundle loads + validates, installs under the smoke-eval gate (≥0.95),
and exports cleanly to all four cross-harness targets.

### Added — v3.11 LifecycleEvent enum extensions

Adds team / confidence / bundle event constants to
:class:`lyra_core.hooks.lifecycle.LifecycleEvent` so existing
:class:`LifecycleBus` subscribers (LangSmith, Langfuse, OTel) see them
through the typed enum, not just via free-form ``hir.events.emit``:

- ``team.create / spawn / task_created / task_completed / task_failed
  / teammate_idle / shutdown``
- ``confidence.promote / demote``
- ``bundle.provision / register_skills / wire_tools / smoke_eval / attest``

Plus ``register_lifecycle_bus(bus)`` / ``unregister_lifecycle_bus(bus)``
in :mod:`lyra_core.teams.agent_teams` so callers (CLI session, ACP
server, daemons) opt in to the typed-enum fan-out. **5 + 13 new tests**
cover enum presence, bus dispatch, idempotent registration, and
end-to-end fan-out from a `LeadSession` lifetime.

### Added — Executor adapters

:mod:`lyra_core.teams.executor_adapter` ships two stock seams between
:class:`LeadSession.executor` and real LLM-backed runtimes:

- **`AgentLoopExecutor`** — wraps a per-teammate
  :class:`~lyra_core.agent.loop.AgentLoop` (one fresh loop per call,
  isolated context). Persona injection prepends a structured marker
  so the wrapped LLM sees the role brief without us threading a
  system-prompt slot everywhere.
- **`CallableLLMExecutor`** — wraps a bare ``(prompt: str) -> str``
  callable for cases that don't need full loop semantics.

Two convenience factories (``make_executor_from_factory``,
``make_executor_from_chat``) keep the call site short.

### Added — v3.11 slash commands

`lyra-cli/src/lyra_cli/interactive/v311_commands.py` ships four new
slashes wired into ``COMMAND_REGISTRY``:

- **`/agentteams`** (alias `/ateams`) — `list`, `status`, `spawn`,
  `add-task`, `mailbox`, `report`, `help`. Surfaces the Agent Teams
  *parallel* runtime as a REPL primitive. Coexists with the existing
  `/team` (MetaGPT *sequential* pipeline) — the two shapes are
  complementary.
- **`/scaling`** — full four-axis snapshot + `axis <name>` detail.
  Renders the cost-benefit-ranked next lever.
- **`/coverage`** — verifier-coverage index per domain with
  `admit_recommendation` (edit_automatically / ask_before_edits /
  plan_mode).
- **`/bundle`** — `info`, `install`, `export <target>`. Lets the
  user load any bundle from disk, install under the smoke-eval gate,
  or emit a cross-harness view for Claude Code / Cursor / Codex /
  Gemini-CLI.

**22 new tests** verify each subcommand against a stub session, the
W1 sample bundles, the real-LLM wiring path, and the
global-singleton coverage integration.

### Added — LBL-BUNDLE-DUAL-USE install gate

`AgentInstaller.install()` now enforces dual-use authorization:
bundles whose manifest declares `dual_use: true` (helix-bio,
cipher-sec, aegis-ops) require *both* `allow_dual_use=True` AND a
non-empty `authorized_by` identifier. The identifier (operator
name, ticket, attestation fingerprint) folds into the resulting
:class:`Attestation`'s `authorized_by` field so an audit trail
survives the install.

- **`DualUseAuthorizationError`** — typed exception in
  :mod:`lyra_core.bundle.agent_installer`. Raised at the start of
  `install()` before any side-effects.
- **`Attestation.authorized_by`** — new optional field; survives
  `to_dict` / `from_dict`; included in the canonical signing
  payload so tampering breaks the HMAC verify.
- **6 new tests** covering blocked-default, missing-flag, missing-
  identifier, whitespace-only-identifier, signed round-trip, and
  attestation-JSON round-trip.

### Added — Bundle → coverage auto-populate (L311-6 integration)

The :class:`AgentInstaller` now auto-populates a process-wide
:class:`VerifierCoverageIndex` on every successful install. Every
bundle's verifier_domain + smoke_eval_pass_rate + eval_count
contributes to the rolling per-domain coverage signal. The CLI
`/coverage` slash reads the same singleton, so installed bundles
surface automatically.

- **`global_index()`** / **`reset_global_index()`** — process-wide
  singleton in :mod:`lyra_core.bundle.verifier_coverage`.
- **`AgentInstaller.auto_populate_coverage`** — instance flag
  (default True). Set to False for isolated installs.
- **Idempotent installs do not double-count** — re-installing the
  same bundle short-circuits via `LBL-AI-IDEMPOTENT` and leaves
  the index unchanged.
- **7 new tests** covering single-bundle population, two-bundle
  aggregation, multi-domain isolation, opt-out, idempotency, and
  singleton/reset semantics.

### Added — Real-LLM wiring for `/agentteams`

The CLI's `/agentteams spawn` now wires teammates to a real
:class:`AgentLoopExecutor` over the session's actual LLM when one
is connected, instead of always using the deterministic stub. Falls
back to the stub when no LLM is available (mock mode, etc.) so
tests and offline use keep working.

- **`_resolve_real_executor`** — best-effort factory that builds a
  per-teammate :class:`AgentLoop` over `session.llm`,
  `session.tools`, `session.store`. Returns None on missing
  attributes so callers fall back to the stub without raising.

### Added — W3 sample bundles

Six more end-to-end runnable bundles fill out the cross-project
upgrade plan's W3 wave:

**Dual-use trio** (each declares `dual_use: true`):

- **`projects/helix-bio/bundle/`** — six-skill biomedical research
  agent (faithfulness gate + dual-use safety + UniProt/MeSH/ChEMBL
  ontologies + clinical-claim router); 12 golden traces.
- **`projects/cipher-sec/bundle/`** — five-skill authorized pentest
  agent (two-signature scope + deny engine + HMAC audit + HITL
  exploit gate + attacker/defender mutex); 13 golden traces.
- **`projects/aegis-ops/bundle/`** — five-skill SRE/ops agent
  (typed runbook loader + semantic policy + incident classifier +
  HITL gate + hash-chained audit); 13 golden traces.

**Non-dual-use trio:**

- **`projects/syndicate/bundle/`** — four-skill multi-agent product
  control plane (permission registry + signed handoffs + recovery
  engine + visibility projection); 12 golden traces.
- **`projects/harmony-voice/bundle/`** — four-skill real-time voice
  agent (slow thinker prefetch + fast talker cache echo + semantic
  cache + voice event stream); 12 golden traces.
- **`projects/quanta-proof/bundle/`** — five-skill formal-proof
  agent (Lean proxy + lemma memory + LATS-lite search + ribbon
  extractor + mesa guard); 12 golden traces.

**45 parameterized tests** across all 14 W1+W2+W3+W4 bundles assert:
every bundle loads + validates, installs under the smoke-eval gate
(≥0.95) with appropriate dual-use authorization, and exports
cleanly to all four cross-harness targets. **3 dedicated tests**
for the dual-use install-block path.

### Added — Shell-script hook gates for team events

`LeadSession` now consults a process-wide `TeamHookRegistry` before
emitting blockable team events. Matches Claude Code's hook semantics
([`docs/05-hooks.md`](../../docs/05-hooks.md)): user-registered shell
scripts run synchronously on `team.task_created` /
`team.task_completed` / `team.teammate_idle`; **exit-code 2 blocks**
the action.

- **`lyra_core.teams.hooks`** — `HookSpec`, `HookDecision`,
  `GateResult`, `TeamHookRegistry`, `global_registry()`,
  `reset_global_registry()`, `load_hooks_yaml()`.
- **`HookBlockedError`** — typed exception when `add_task` is
  refused by a hook. The task is not created (block happens
  before mutation).
- **`task_completed` block forces revision** — when a completion
  hook returns 2, the task reverts to `blocked` with a
  `hook-blocked: <reason>` failure_reason.
- **`teammate_idle` is advisory** — fires but cannot block (the
  teammate has already finished its claim).
- **Path resolution** — scripts beginning with `/`, `~`, `./`,
  `../` run as executables; everything else routes through
  `sh -c` so shell builtins, pipes, and inline scripts all work.
- **Env + stdin** — every hook gets `LYRA_HOOK_EVENT`,
  `LYRA_HOOK_TEAM`, `LYRA_HOOK_TASK_ID`, `LYRA_HOOK_TEAMMATE` in
  env, plus the full event payload as JSON on stdin.
- **Timeout = block** — hooks exceeding `timeout_s` (default 30s)
  return exit-code 2.
- **YAML loader** — `~/.lyra/hooks.yaml` parses via the existing
  minimal-YAML parser.
- **23 new tests** covering spec validation, registry CRUD, gate
  dispatch (allow/warn/block), multi-hook fan-out, env propagation,
  timeout-as-block, missing-script-as-warning, real path execution,
  LeadSession integration, idle-hook advisory semantic, YAML loader.

### Added — HTTP-API method pack for v3.11

`lyra_core.acp.v311_methods.register_v311_methods(server)` plugs ten
JSON-RPC 2.0 methods into the existing `AcpServer`, opening v3.11 to
non-CLI clients (web UI, IDE extensions, Slack bots,
ACP-compatible tools):

- **`v311.agentteams.spawn / add_task / run / report / mailbox`** —
  Agent Teams runtime over JSON-RPC.
- **`v311.bundle.info / install / export`** — Software 3.0 bundle
  pipeline. `install` honors `LBL-BUNDLE-DUAL-USE` (returns a
  JSON-RPC error when dual-use bundles lack authorization).
- **`v311.scaling.snapshot`** — four-axis position with optional
  per-axis overrides.
- **`v311.coverage.snapshot`** — global verifier-coverage index.
- **17 new tests** covering registration, every method's happy
  path, dual-use block + authorization, unknown-target rejection,
  missing-param errors, and unknown-method routing.

### Added — W4 mentat-learn bundle

The cross-project upgrade plan's W4 wave lands as a runnable
Software 3.0 bundle:

- **`projects/mentat-learn/bundle/`** — five-skill self-improving
  personal assistant (four-layer memory + dialectic user model +
  multi-channel gateway + closed-loop skill extractor + privacy
  redactor); 12 golden traces; MCP server stub.

The bundle integrates v3.11 L311-8 (confidence-scored auto-memory)
as the substrate for skill promotion — patterns with
`seen_count ≥ 3 ∧ confidence ≥ 0.85` auto-promote to procedural
memory.

### Added — Bundle cron/routine integration

Bundles can now declare a `routines:` section in `bundle.yaml` and
the `AgentInstaller` registers each routine into Lyra v3.7 L37-8
cron at install time. This realizes the routine declarations already
referenced in polaris, open-fang, mentat-learn, and gnomon bundle
docs.

- **`RoutineSpec`** — typed dataclass with `kind`
  (`cron|webhook|api`) + `name` + `handler` + per-kind extras
  (`schedule`, `timezone`, `repo`, `events`, `path`).
- **`AgentInstaller.routine_registry`** — optional
  :class:`RoutineRegistry` slot. When set, every routine in the
  bundle gets a workflow stub registered + a typed Routine bound
  into the registry.
- **Workflow naming**: `"<bundle_slug>.<routine_name>"` so multiple
  bundles don't collide.
- **Idempotent re-install** doesn't duplicate routines — the second
  registration silently no-ops.
- **User-supplied workflows take precedence** — when a caller
  pre-registers a workflow at the canonical id before install, the
  installer leaves it alone.
- **12 new tests** covering parse (cron/webhook/api/skip-invalid),
  installer no-registry-skips, three-trigger registration, workflow
  callable dispatch, idempotency, and user-workflow override.

### Added — Bundle marketplace fetcher

`lyra_core.bundle.marketplace` realizes Argus's `marketplace-fetcher`
skill as a v3.11 primitive. Fetches a bundle archive from a remote
URL, verifies its detached signature against a registered marketplace
key, unpacks it into a sandboxed cache, and returns a path the
`AgentInstaller` can ingest.

- **`MarketplaceFetcher`** — pluggable URL fetcher (default
  `urllib.request`); HMAC-SHA256 signature verification (real
  Sigstore swap is a v3.11.x follow-up); tar safety
  (rejects absolute / parent-traversal paths); URL safety
  (refuses non-`http(s)` schemes).
- **`MarketplaceRegistry`** — trust-store + SBOM log.
  `LBL-FETCH-SBOM`: every fetch records `(bundle_name, hash,
  source_url, marketplace, signing_key_fingerprint, fetched_at,
  cache_path)` for audit.
- **Bright lines**: `LBL-FETCH-VERIFY` (signature mismatch =
  rejected), `LBL-FETCH-SCOPE` (tool descriptors that escape the
  cache sandbox = rejected), `LBL-FETCH-SBOM` (every fetch logs).
- **End-to-end test** — fetched bundle is install-able by the
  `AgentInstaller`, proving the marketplace path produces a real
  working bundle.
- **12 new tests** covering registry trust/revoke, happy path,
  signature mismatch, untrusted marketplace, path-escape blocks
  (both archive-level and tool-descriptor-level), URL safety
  (non-http rejected), expected_hash double-check, and SBOM
  serialization.

### Added — Installed-bundles registry + uninstall lifecycle

`lyra_core.bundle.installed_registry` tracks every bundle the
`AgentInstaller` has lit up on the local machine. Filesystem-backed
(`~/.lyra/installed.json`) so a human operator can inspect outside
Lyra.

- **`InstalledRecord`** — typed row with bundle name + version +
  hash + target_dir + attestation_path + dual_use + authorized_by +
  verifier_domain + installed_at + last_verified_at.
- **`InstalledRegistry`** — upsert / find / remove; persistent
  across process restarts; multiple installs of the same bundle in
  different target dirs are distinct entries.
- **`AgentInstaller.installed_registry`** + `auto_register_install`
  — installer auto-populates on every successful install.
  Idempotent re-install preserves `installed_at`, advances
  `last_verified_at`.
- **`uninstall_bundle()`** — re-verifies the attestation
  (`LBL-UNINSTALL-VERIFY`), removes the install dir, drops the
  registry entry, emits `bundle.uninstalled` lifecycle event.
  Operator can override the verify with
  `verify_attestation_first=False`.
- **15 new tests** covering record JSON round-trip, registry
  upsert/find/remove/persistence, distinct-target-dir entries,
  installer auto-populate, dual-use record propagation, idempotent
  install preserves timestamps, opt-out, uninstall removes target,
  uninstall unknown raises, attestation tampering blocks uninstall,
  override skips verify, missing-attestation blocks uninstall,
  uninstall emits event.

### Added — `/bundle list` and `/bundle uninstall` slash subcommands

The `/bundle` REPL slash gains two new subcommands wired to the
installed-registry:

- **`/bundle list`** — formatted table of every installed bundle
  (name, version, domain, dual-use, hash prefix, target_dir).
- **`/bundle uninstall <hash> <target_dir>`** — accepts a short
  hash prefix and disambiguates against the registry; refuses
  ambiguous prefixes.
- **4 new CLI tests** — empty list, post-install list, uninstall
  round-trip with prefix, unknown-hash error path.

### Added — HTTP bridge for ACP method pack

`lyra_core.acp.HttpBridge` wraps an `AcpServer` (with its v3.11
methods registered) in a stdlib `http.server` so real HTTP clients
can POST JSON-RPC requests instead of speaking stdio. No FastAPI
dep — pure stdlib.

- **Endpoints**: `POST /jsonrpc` (single-request JSON-RPC 2.0;
  notifications return 204), `GET /healthz` (liveness),
  `GET /methods` (registered method list).
- **Bright lines**: `LBL-HTTP-AUTH` (Bearer token, constant-time
  compare), `LBL-HTTP-LIMIT` (configurable body cap, default 1
  MiB), `LBL-HTTP-LOOPBACK` (binds 127.0.0.1 by default; explicit
  `host="0.0.0.0"` required to expose beyond loopback).
- **Threaded server** — non-blocking; `start()` returns the bound
  `(host, port)`; supports `with HttpBridge(...) as addr:` context
  manager.
- **15 new tests** covering healthz, methods listing, unknown-path
  404, JSON-RPC happy path + unknown-method + notification + wrong
  path, bundle.info over HTTP, auth required + constant-time
  compare, body-size limit, start-twice-raises, idempotent stop,
  context manager, loopback default.

### Added — `RoutineDaemon` (cron daemon → routine fires)

The v3.7 `RoutineRegistry` only exposed `fire_cron(name)` — something
had to actually call it on schedule. `lyra_core.cron.RoutineDaemon`
does that: parses each cron-triggered routine's expression into a
`Schedule`, sleeps until next-run, fires the routine, records the
firing, and loops.

- **Pluggable clock + sleep_fn** — tests inject deterministic mocks.
- **Best-effort per routine** — workflow exceptions are caught,
  recorded, and the daemon continues; one bad routine doesn't kill
  the whole loop.
- **Stoppable threaded loop** + **`tick_once`** for inline use.
- **Skips non-cron triggers** silently — webhook/api routines fire
  inline elsewhere.
- **HIR event** `routine.fired` with `routine` + `error` + `next_run_at`.
- **12 new tests** covering schedule seeding, tick fires when elapsed,
  workflow error capture, next-run advancement, multi-routine
  independent schedules, unparseable expressions skipped, threaded
  start/stop lifecycle, idempotent stop, double-start raises, HIR
  event emission.

### Added — `/bundle fetch`, `/bundle trust`, plus seven new ACP methods

The marketplace fetcher is now reachable from the REPL and over
JSON-RPC:

- **`/bundle fetch <url> <sig> <market>`** — fetches a remote bundle
  through the marketplace fetcher; reports cache path and next-step.
- **`/bundle trust <market> <fp> <secret_hex>`** — registers a
  trusted marketplace key on the session.
- **`v311.bundle.fetch`**, **`v311.bundle.trust`**,
  **`v311.bundle.list`**, **`v311.bundle.uninstall`** — JSON-RPC
  methods covering the same surface for non-CLI clients.
- **5 new CLI tests + 7 new ACP tests** covering trust + fetch
  round-trip, untrusted-marketplace failure, signature mismatch,
  list-after-install, uninstall round-trip, unknown-hash error.

### Added — End-to-end v3.11 lifecycle test

`test_v311_e2e.py::test_v311_full_lifecycle` exercises every v3.11
surface in one trace: build a dual-use bundle archive, sign it, trust
the marketplace, fetch through the verifier, install with dual-use
authorization (block-then-allow), verify routine registration,
populate the coverage index, list installed bundles, drive one
RoutineDaemon tick that fires the registered routine, spawn an Agent
Teams runtime, run dependent tasks to idle, snapshot scaling axes
+ pick best-lever, export to all four cross-harness targets,
uninstall with attestation re-verify.

### Added — Pluggable `SigningBackend`

`lyra_core.bundle.signing_backend` defines the seam so the HMAC-SHA256
default in `attestation.py` can be swapped for real PKI without
touching call sites.

- **`SigningBackend` Protocol** — `sign(payload) -> str` /
  `verify(payload, signature) -> bool`.
- **`HmacBackend`** — current default, stdlib only.
- **`Ed25519Backend`** — real Ed25519 detached signatures via
  `cryptography`. Clean error when the package is not installed.
- **`SigstoreBackend`** — placeholder documenting the cosign
  integration shape; raises `NotImplementedError` so production
  callers can swap in a real impl.
- **`set_default_signing_backend(b)`** / **`default_signing_backend()`**
  — process-wide swap.
- **15 new tests** (2 cleanly skipped when `cryptography` is absent)
  covering HMAC round-trip + tamper rejection + env-key resolution +
  dev-fallback + constant-time compare; Sigstore placeholder raises;
  Ed25519 round-trip + tamper rejection + missing-key errors;
  default-backend lifecycle + reset.

### Added — Mentat-Learn test suite restoration

The pre-existing test collection error (missing `harness_skills` /
`fastapi` modules) is fixed via a `tests/conftest.py` that prepends
`src/` to `sys.path` and uses `collect_ignore` to skip cleanly when
optional deps are absent. **53 mentat-learn tests now pass.**

### Refreshed — CROSS_PROJECT_UPGRADE_PLAN_2026.md

Status header updated to **"ALL 14 BUNDLES SHIPPED"** with a per-wave
status table; the original plan body remains as design rationale.

---

## v3.8.0 — 2026-05-08 — "Memory tier — Letta tool surface" (unreleased)

Roadmap source: [`docs/184-strongest-memory-techniques-synthesis-may-2026.md`](../../docs/184-strongest-memory-techniques-synthesis-may-2026.md) §6 + [`docs/185-memory-integration-playbook.md`](../../docs/185-memory-integration-playbook.md) §2.
First v3.8 increment: lands the *tool-call surface* (L38-4) so every memory op shows up in the agent trace. The mem0 / Cognee / PPR-fusion adapters (L38-1..3) require external deps and ship in subsequent increments.

### Added — L38-4: Letta-style memory tool surface

- **`lyra_core.memory.memory_tools`** — `MemoryToolset` aggregates over
  Lyra's three existing memory substrates (AutoMemory + ProceduralMemory
  + SqliteReasoningBank) and exposes four tool-call ops:
  - `recall(query, scope, top_k)` — search one substrate or union all.
    Scopes: `"auto"` / `"skill"` / `"lesson"` / `"any"`.
  - `remember(text, scope, **kwargs)` — write a new entry.
    Auto-scope honours `MemoryKind` (project default); skill-scope
    requires `skill_id` / `skill_name` / `skill_description`; lesson-scope
    is read-only (lessons are distilled from trajectories, not authored).
  - `forget(record_id, scope)` — tombstone an auto-memory entry; skill
    + lesson scopes are immutable through this surface.
  - `improve()` — heartbeat hook returning current substrate cardinalities
    (`auto_entries_active` / `skill_count` / `lesson_count`).
- **HIR events** emitted for every op via `lyra_core.hir.events.emit`:
  `memory.{recall,remember,forget,improve}.{start,end}`. The agent's
  reasoning trace now records every memory access.
- **`RecallResult`** carries `scope` + a normalised `(record_id, title,
  body)` view + the original payload — callers don't branch on
  substrate type.
- **22 new tests** covering per-scope recall, union scope, top-k
  truncation, scope-rejection invariants (lesson is read-only,
  procedural-skill cannot be forgotten), and HIR-event capture.
- **Exports**: `AutoMemory`, `MemoryEntry`, `MemoryKind`, `MemoryToolset`,
  `RecallResult`, `Scope`, `SourceRecord`, `ImproveResult` from
  `lyra_core.memory`.

### Deferred — L38-1, L38-2, L38-3

These ship in subsequent v3.8.x increments because each adds a
non-trivial external dependency:

- **L38-1 mem0 adapter** — needs `pip install mem0ai` + LLM-extractor
  budget. Unblocks Hit@1 ≥ 90% on planted preference bench.
- **L38-2 Cognee adapter** — needs `pip install cognee` + Kuzudb
  embedded backend. Unblocks Hit@k=3 ≥ 80% on multi-doc bench.
- **L38-3 PPR fusion** — depends on L38-1/2 substrates being live.

The `MemoryToolset` surface is forward-compatible: adapters land as
new substrate fields (`mem0`, `cognee`) consulted by `recall(scope=...)`
without changing the public ops.

---

## v3.7.0 — 2026-05-08 — "Claude-Code-2026 parity"

Roadmap source: [`LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md`](LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md).
Ports the May-2026 Claude Code feature wave (Dickson Tsai's announcement)
across two themes — **Developer Experience** and **Autonomy** — while
preserving Lyra's existing primitives (`acp/`, `subagent/`, `cron/`,
`permissions/`, `terminal/`, `sessions/`, `memory/`, `brains/`).

### Theme A — Developer Experience

- **L37-1 Remote Control bridge over ACP.** New
  `lyra_core.acp.remote_control` module ships
  `RemoteSession` + `AttachToken` + `RelayHub`. Every attach uses a
  fresh HMAC-signed token (default TTL 300 s); replay raises
  `RemoteAuthError`. Bright-lines: `LBL-RC-AUTH` (replay refused),
  `LBL-RC-SCOPE` (relayed calls outside the session's pre-approved
  set raise `RemoteScopeError` — remote clients cannot upgrade their
  own scope).
- **L37-2 Flicker-free fullscreen TUI + mouse + voice events.** New
  `lyra_core.terminal.fullscreen.FullscreenRenderer` emits typed
  `DiffBlock`s — only the changed rows write back, so a Rich-`Live`
  / prompt-toolkit / raw-ANSI backend can apply minimal updates. New
  `lyra_core.terminal.events` ships typed `MouseEvent` (click /
  double_click / scroll / move) and `VoiceEvent`
  (wake / transcript / silence) so the CLI and any web bridge consume
  identical event types.
- **L37-3 Session manifests.** New `lyra_core.sessions.manifest`
  ships `SessionDirectory` (add/remove/filter/group_by), typed
  `ViewKind` (`PLAN / DIFF / FILES`), and `SplitLayout` for the
  drag-drop split view. Both the CLI and any web client render from
  the same typed manifest.

### Theme B — Autonomy

- **L37-4 Auto-mode safety classifier.** New
  `lyra_core.permissions.auto_classifier.AutoModeClassifier` replaces
  the v3.6 heuristic stub with a real pattern-matcher: destructive
  shell patterns (`rm -rf /`, fork bomb, `curl|sh`, force-push to
  protected branches, `DROP TABLE`, etc.); prompt-injection markers
  (`ignore previous instructions`, `[[SYSTEM]]`, ANSI escapes);
  sensitive paths (`/etc/passwd`, `~/.aws/credentials`, `.env*`,
  `~/.ssh/id_*`); side-effect tool kinds without an allowlist.
  Verdict is `AUTO_RUN / ASK / REFUSE`. Bright-line:
  `LBL-AUTO-REFUSE` — destructive or injection signals are REFUSED
  regardless of bypass flags.
- **L37-5 `/worktree` slash command.** New
  `lyra_cli.interactive.worktree_command` wraps the existing
  `WorktreeManager` with sub-commands `create [name] / list /
  remove <name> / copy <pattern> [name]` and a `CopyPolicy`
  defaulting to `node_modules`, `.venv`, `dist`, `.pytest_cache`.
- **L37-6 Auto-memory (`memory.md`).** New
  `lyra_core.memory.auto_memory.AutoMemory` — append-only `memory.md`
  + `entries.jsonl` per project under `~/.lyra/memory/<project_slug>/`.
  Typed entries: `user / feedback / project / reference`. Methods:
  `save / forget / retrieve / by_kind / session_start_digest`.
  Bright-line: `LBL-AUTO-MEMORY-APPEND-ONLY` — past entries never
  mutate; `forget` writes a tombstone, the original survives in the
  audit chain.
- **L37-7 `/ultrareview` multi-agent review.** New
  `lyra_core.brains.ultrareview.UltraReviewPipeline` enforces a
  cross-family invariant (≥ 2 distinct reviewer families;
  `CrossFamilyError` otherwise), aggregates per-path / per-severity
  findings, and renders a Markdown summary fit for PR comments. New
  `lyra_cli.interactive.ultrareview_command.UltraReviewCommand`
  drives it from the REPL — `/ultrareview` reviews the current branch,
  `/ultrareview <pr-id>` reviews a GitHub PR (diff-fetcher is
  caller-injected so tests don't hit GitHub).
- **L37-8 Routines (cron + webhook + API triggers).** New
  `lyra_core.cron.routines` ships typed
  `CronTrigger / GitHubWebhookTrigger / HttpApiTrigger`,
  `RoutineRegistry`, and HMAC verifiers for each non-cron trigger.
  Bright-lines: `LBL-ROUTINE-AUTH` (unsigned webhook / API firings
  raise `RoutineAuthError`), `LBL-ROUTINE-COST` (over-cap firings are
  *deferred* to a queue, not skipped — `replay_deferred()` runs them
  when the envelope has headroom).

### Invariants added (v3.7)

1. Remote attach never escalates scope.
2. Auto-mode is classifier-driven, not heuristic.
3. Auto-memory is append-only.
4. Routines authenticate every non-cron trigger.

### Tests

| Phase | Tests |
|---|---:|
| L37-1 Remote-control | 11 |
| L37-2 Fullscreen + events | 13 |
| L37-3 Session manifests | 13 |
| L37-4 Auto-mode classifier | 17 |
| L37-5 `/worktree` slash | 14 |
| L37-6 Auto-memory | 12 |
| L37-7 `/ultrareview` (pipeline + slash) | 11 |
| L37-8 Routines | 17 |
| **Total** | **108** |

All 108 v3.7 tests pass; zero regressions vs. v3.6.0.

---

## v3.6.0 — 2026-05-01 — "Four-mode rename"

A user-facing rename of Lyra's four interactive modes from a
**behavioural** taxonomy (`agent / plan / debug / ask`) to a
**permission-flavoured** one
(`edit_automatically / ask_before_edits / plan_mode / auto_mode`)
that mirrors the picker users expect from modern coding-assistant
UIs. The rename is not a label-only change — `ask_before_edits`
introduces real per-write confirmation behaviour, and `auto_mode`
introduces a new heuristic router. The dedicated `debug` mode is
**gone**; its systematic-debugging discipline survives as a regular
skill.

### New

- **`edit_automatically`** — replaces `agent`. Same full-access
  execution loop; the v3.6 name spells out the permission posture
  (edits land without per-write confirmation). Sets
  `permission_mode = "normal"` on entry so the approval cache
  honours the "OK once, OK forever this session" intent.
- **`ask_before_edits`** — new behaviour. Same loop as
  `edit_automatically` (full-access execution, all tools available)
  but every write or destructive tool call pauses for user
  confirmation. Sets `permission_mode = "strict"` on entry so the
  approval cache always re-prompts. The system prompt instructs
  the model to bundle related writes into single messages and to
  surface in one sentence what each write does and why before it
  lands (the user is staring at a confirmation prompt; that
  sentence is what they read).
- **`plan_mode`** — replaces `plan`. Same read-only collaborative
  design loop. `/approve` now hands off to `edit_automatically`
  (was `agent`).
- **`auto_mode`** — new behaviour. Each plain-text turn is
  classified by `_classify_for_auto_mode` (pure function, no LLM
  call) and dispatched to one of the three modes above:
  read-only intent (`explain`, `how does`, `?` etc.) →
  `plan_mode`; risky / destructive verbs (`delete`, `git push`,
  `migrate`, `prod`, …) → `ask_before_edits`; otherwise →
  `edit_automatically`. The session mode itself stays
  `auto_mode`; only the *behaviour for the current turn* is
  borrowed. Every router decision is annotated with a one-line
  `[auto_mode → <picked>]` notice so the choice is visible to the
  user (and reversible with an explicit `/mode <name>`).

### Removed (mode taxonomy only)

- **`debug` as a dedicated mode**. The pre-v3.6 `debug` mode loaded
  a `Hypothesis-Test` system prompt and added three observability
  tools. v3.6 retires the dedicated mode because the same outcome
  is reachable via `auto_mode` (which routes debug-shaped prompts
  to `ask_before_edits`) plus the existing systematic-debugging
  skill. Typing `/mode debug` still works — it remaps to
  `auto_mode` with a one-line "renamed in v3.6" notice. The
  `docs/howto/debug-mode.md` guide was rewritten to reflect the
  skill-based path.
- **`ask` as a dedicated mode**. The pre-v3.6 `ask` mode was
  read-only Q&A. v3.6 retires it because `plan_mode` covers the
  same read-only intent and `auto_mode` covers the same "I just
  want to ask a question" UX. `ask_before_edits` is **not** the
  replacement (it actively edits, just with confirmation). Typing
  `/mode ask` remaps to `plan_mode`.

### Backwards-compatible (every legacy name still works)

`InteractiveSession.__post_init__` and `_cmd_mode` both consult
`_LEGACY_MODE_REMAP`, which now covers all eight prior names:

| Legacy | Canonical (v3.6) |
|---|---|
| `agent`   (v3.2) | `edit_automatically` |
| `plan`    (v3.2) | `plan_mode`          |
| `debug`   (v3.2) | `auto_mode`          |
| `ask`     (v3.2) | `plan_mode`          |
| `build`   (v2.x) | `edit_automatically` |
| `run`     (v2.x) | `edit_automatically` |
| `explore` (v2.x) | `plan_mode`          |
| `retro`   (v2.x) | `auto_mode`          |

Old `settings.json` files, stored session JSONLs, `--mode`
script flags, and muscle memory all keep working unchanged.

### Permission posture is now mode-aligned

`InteractiveSession.__post_init__`, `cycle_mode` (Tab), and
`_cmd_mode` all align `permission_mode` to the active mode:

- `edit_automatically` ↔ `permission_mode = normal` (cached
  approvals)
- `ask_before_edits`   ↔ `permission_mode = strict` (always
  re-prompt)
- `plan_mode` / `auto_mode` leave the existing posture untouched
  (read-only / per-turn router)
- `yolo` is preserved across mode switches; flipping to it still
  requires the explicit `/perm yolo` or `Alt+M` opt-in

The substrate (`PermissionStack`, `ToolApprovalCache`) is updated
in lock-step via `_propagate_permission_mode` / the equivalent
helper in `keybinds.py` so the next tool call sees the new
policy without a manual mirror.

### Tab cycle reorders to protect the user

The Tab rotation is now
`edit_automatically → plan_mode → ask_before_edits → auto_mode`.
The two write-capable modes (`edit_automatically`,
`ask_before_edits`) sit at opposite ends of the cycle so a single
Tab press never accidentally toggles between "edits land" and
"edits land after a confirmation". A test pins the adjacency
constraint
(`test_tab_cycle_separates_the_two_write_capable_modes`).

### System-prompt preamble updated

`_LYRA_MODE_PREAMBLE` now enumerates the four v3.6 modes
verbatim and explicitly disclaims the legacy v3.2 names
(`agent / plan / debug / ask`) and pre-v3.2 names
(`build / run / explore / retro`) as **legacy aliases, not
modes you have**. This defends against the LLM listing the wrong
set when the user asks "how many modes do you have?". The
"exactly four" anchor sentence is preserved.

### Test contract migrated

- `tests/test_modes_taxonomy_v32.py` deleted; replaced by
  `tests/test_modes_taxonomy_v36.py` (40 contract tests covering
  the v3.6 names, the `_classify_for_auto_mode` heuristic, the
  every-legacy-name-remaps table, and the
  permission-posture-on-boot rules).
- `tests/test_chat_mode_handlers.py`,
  `tests/test_slash_mode_full.py`,
  `tests/test_keybinds_session_toggles.py`,
  `tests/test_interactive_session.py`,
  `tests/test_interactive_features.py`,
  `tests/test_interactive_skin_polish.py` updated to assert
  against the new mode names while continuing to exercise the
  legacy-alias path so we know the remap actually fires.

### Documentation rewritten

- `docs/start/four-modes.md` rewritten end-to-end for the new
  taxonomy with a side-by-side legacy-name table.
- `docs/howto/debug-mode.md` rewritten — debug is now a skill
  loaded from `auto_mode` or `ask_before_edits`, not a dedicated
  mode. Both the v3.6 surface and the rationale ("why no
  dedicated debug mode in v3.6?") are documented.
- `docs/features.md` 1.3 (Modes table) rewritten to enumerate the
  v3.6 four with their permission postures, plus a rename table.
- `docs/use-cases.md`, `docs/index.md`,
  `docs/start/first-session.md`, `docs/start/slash-commands.md`,
  `docs/reference/commands.md`,
  `docs/concepts/permission-bridge.md`,
  `docs/concepts/agent-loop.md` — every example REPL transcript,
  table row, slash-command reference, and prose mention updated.
- Brand-identity test markers added to four migration-aware doc
  pages that pre-existed this release
  (`docs/research/index.md`, `docs/start/install.md`,
  `docs/concepts/sessions-and-state.md`,
  `docs/howto/configure-providers.md`); these were already
  failing the `lyra-legacy-aware` check and are now correctly
  opted in.

### Compatibility

- **REPL UX**: zero-impact for users who type slash names by hand
  (every legacy name still works and emits a one-line rename
  notice). Tab now cycles four buttons with new labels.
- **Persisted state**: `~/.lyra/config.json` and per-session
  JSONLs containing `mode = "agent"` etc. continue to load
  unchanged via `_LEGACY_MODE_REMAP`. No migration script
  required.
- **CLI flags**: `lyra run --mode agent` still works (remaps);
  prefer `--mode edit_automatically` going forward.
- **Public API**: `_VALID_MODES`, `_MODE_HANDLERS`,
  `_MODE_SYSTEM_PROMPTS`, `_MODE_BLURBS`,
  `_LYRA_MODE_PREAMBLE`, `_LEGACY_MODE_REMAP`, `_MODE_CYCLE_TAB`
  remain importable; the keys/values are the v3.6 names.
- **`/approve`**: now switches to `edit_automatically` (was
  `agent`). Behaviour-identical for the user; the destination
  string changed.

### Why this rename

The v3.2 taxonomy was a copy of Claude Code's UI from that era.
By v3.6 the picker users expect on every modern coding-assistant
surface (Cursor, Claude Code, Copilot Chat) is permission-flavoured
— "edit automatically" vs "ask before edits" vs "plan mode" vs
"auto mode". The semantic shift fits Lyra's architecture cleanly
because the permission axis (`normal / strict / yolo`) was already
a separate first-class concept; the new modes simply align the
top-level mode selector with that axis so the user only has to
pick once.

## v3.5.5 — 2026-05-01 — "The clean cut"

A truthfulness release. After auditing
[`docs/features.md`](docs/features.md) (introduced in v3.5.4), three
items turned out to be either **structurally inapplicable to a
hosted-API harness** or **vapourware** that had no path to
activation in any version of Lyra a user might run today. The
documentation and the code that backed them have been removed
together so the catalogue means what it says.

### Removed (code + tests + docs in lock-step)

- **`SharedKVPoolProvider` Protocol shim**
  (`lyra_core/providers/shared_kv.py`,
  `tests/test_providers_shared_kv.py`). v3.5.0 shipped this as a
  forward-compat seam in case a self-hosted Lyra profile ever
  wanted to plug a real
  [PolyKV](https://arxiv.org/abs/2604.24971) implementation behind
  it. Six months later, no self-hosted profile is on the roadmap,
  no hosted provider exposes KV-cache injection, and the Protocol
  had **zero callers**. Documentation pretending to be
  architecture. The
  [`PromptCacheCoordinator`](docs/concepts/prompt-cache-coordination.md) —
  the *production* PolyKV absorption that ships against Anthropic,
  OpenAI, DeepSeek, and Gemini cache discounts — is unaffected.
- **`BlockStreamingProvider` Protocol shim**
  (`lyra_core/providers/streaming.py`). Same shape, same fate. It
  was a forward-compat seam for the [CALM
  paper](https://arxiv.org/abs/2604.24026)'s K-token block
  streaming. **No hosted provider streams K-token blocks** —
  Anthropic, OpenAI, Google, xAI, Mistral, DeepSeek, Cerebras,
  Groq all ship token-by-token streaming with discrete
  vocabularies. The shim served no caller and would not have
  served one in any v3.x release.
- **`BrierLM` scorer** (`lyra_evals/scorers/brierlm.py`,
  `tests/test_brierlm.py`,
  `lyra_evals/scorers/__init__.py`). The CALM-derived calibration
  metric. It was hardcoded to return `None` (auto-skip) on every
  real run because **no production provider returns full per-token
  probability distributions** — OpenAI exposes top-K `logprobs`
  only; Anthropic, DeepSeek, and Gemini expose nothing.
- **`Verifiable RAG corpus + sigstore` row** in
  [`docs/features.md`](docs/features.md). It was marked 🟠
  Planned in v3.5.4. There is no implementation, no PR in flight,
  and no concrete plan. Rather than carry a planned row that
  might mislead readers who skim the catalogue, the row is gone.
  If we build the feature, we add the row when the code lands.

### Changed

- **`docs/features.md`** retitled to "v3.5.5 snapshot".
  Maturity legend reduced to four flags (🟢 production,
  🟡 beta, ⚪ reference only, 🔴 studied & rejected) — the
  🔵 "forward-compat shim" and 🟠 "planned" flags are retired,
  because every row in the catalogue now points at code that runs
  *today*. **Copilot** provider corrected from 🔵 to 🟢
  (existed in `providers/copilot.py` all along). **LoCoEval
  adapter** corrected from 🟠 to 🟢 (existed in
  `lyra_evals/adapters/loco_eval.py` all along). **Rubric scorer**
  source path corrected from `lyra_evals/scorers/rubric.py`
  (never existed) to `lyra_core/eval/rubrics/`. The
  "Forward-compat shims" §17 section is gone. The "Internal
  subsystems" section now describes `klong`, `arena`, `rl`,
  `wiki`, `meta` honestly as "importable Python APIs without a
  CLI surface yet" rather than as roadmap items.
- **`docs/use-cases.md`** retitled to "v3.5.5 snapshot". Removed
  BrierLM mentions from "I want to evaluate against benchmarks";
  removed the aspirational HUD roadmap section from "I want a HUD";
  corrected LoCoEval link in "I want to run on a long-horizon
  project" to point at the shipped feature row.
- **`docs/research/papers.md`** restructured. Absorption legend
  drops 🔵 and 🟠 to match the features catalogue. **CALM (#25)**
  reclassified from 🔵 to 🔴 ("studied & rejected for hosted-API
  Lyra"). **PolyKV (#24)** consolidated to a single 🟢 row
  (`PromptCacheCoordinator`) with a note that the
  `SharedKVPoolProvider` shim was deleted. **LoCoEval (#29)**
  promoted from Wave 5 (Planned) into Wave 4 with a 🟢
  classification. Wave 5 split into **5a — validation papers**
  (insights absorbed operationally with no new module) and
  **5b — research backlog** (no code shipped in v3.5; clearly
  flagged as backlog, not roadmap commitments).
- **`docs/research/repos.md`** removed the `polykv-llm` PyPI
  reference row (the shim it backed is gone).
- **`docs/research/calm-evaluation.md`** rewritten as a one-page
  postmortem. Title in nav: **"CALM postmortem (rejected)"**.
- **`docs/research/polykv-evaluation.md`** trimmed to remove the
  `SharedKVPoolProvider` "What we shipped" subsection; replaced
  with a "What we deliberately did not ship" entry explaining why
  the shim was deleted.
- **`docs/howto/customize-hud.md`** rewritten to describe what
  actually ships in v3.5: four built-in presets (`minimal`,
  `compact`, `full`, `inline`), nine widgets, three CLI
  subcommands (`lyra hud preview / presets / inline`), and the
  REPL bottom-toolbar embedding. Removed all aspirational claims
  (background render loop, alt-screen panel, `/hud preset` slash
  command, `/hud widget` toggling, public `Widget` /
  `register()` plug-in API, `~/.lyra/hud.yaml` loader, `--no-hud`
  flag, `LYRA_HUD=off` env var). The "PR path" section explains
  how to add a built-in widget today; the public plug-in API is
  explicitly flagged as wishlist with no implementation.
- **`docs/howto/run-eval.md`** removed every BrierLM mention
  (description, mermaid diagram, scorers list, sample output,
  drift-gate baseline / tolerances). Corrected rubric scorer
  source path. "Where to look" table updated to reflect the
  actual eval module layout
  (`lyra_core/eval/`, `lyra_evals/adapters/`).
- **`docs/howto/cron-skill.md`** "Eval drift watcher" example
  switched its drift signal from BrierLM to `pass@1`.
- **`docs/concepts/prompt-cache-coordination.md`** rewrote the
  closing section "Forward-compat: self-hosted PolyKV" → "Why no
  self-hosted PolyKV shim?" explaining the v3.5.5 deletion.
- **`docs/research/index.md`** updated CALM/PolyKV memo
  descriptions and the research-overview mindmap to remove the
  shim nodes.
- **`docs/architecture/topology.md`** updated `lyra-evals`
  package description from "incl. BrierLM" to
  "public-benchmark adapters".
- **`packages/lyra-core/src/lyra_core/providers/__init__.py`**
  dropped the six `shared_kv` re-exports
  (`DEFAULT_KV_BITS`, `EXPECTED_COMPRESSION_RATIO`,
  `SharedKVPoolHandle`, `SharedKVPoolProvider`,
  `get_default_shared_kv_provider`,
  `register_default_shared_kv_provider`) and the two `streaming`
  re-exports (`BlockStreamingProvider`, `BlockToTokenAdapter`).
  Existing prompt-cache and registry exports are unchanged.
- **`projects/lyra/CONTRIBUTING.md`** and
  **`projects/lyra/THIRD_PARTY_NOTICES.md`** updated to remove
  references to the BrierLM scorer and to mark CALM as studied &
  rejected with the shim removals noted.
- **`mkdocs.yml`** Research nav entry renamed
  "CALM evaluation" → **"CALM postmortem (rejected)"**.

### Compatibility

- **No public API breakage** for anything that runs against a
  hosted provider — the deletions only affected (a) Protocol stubs
  with zero implementations and (b) an experimental scorer that
  never activated against a real provider.
- **`PromptCacheCoordinator`**, `prewarm_for_specs`, all sixteen
  hosted providers, all eval adapters, all CLI subcommands, all
  HUD presets, all skills/hooks APIs unchanged.
- If you were importing `SharedKVPoolProvider`,
  `BlockStreamingProvider`, or `BrierLM` from `lyra_core.providers`
  / `lyra_evals.scorers`: those symbols are gone and there is no
  drop-in replacement, because the Lyra surface they pretended to
  bridge to never existed in any production build. If you have a
  concrete use case (a real PolyKV / CALM provider you want to
  wire), please open an issue and we will reintroduce the
  Protocol *together with* a working implementation on the same
  commit.

### Verification

- `pytest packages/lyra-core packages/lyra-evals packages/lyra-cli`
  → green. No tests reference the deleted modules.
- `python3 -m mkdocs build --strict` → 0 warnings.
- `ruff check projects/lyra/packages` → clean.

## v3.5.4 — 2026-05-01 — "Features catalogue + Use cases (two front doors)"

A docs-only release. Closes the gap that *no single page in the
docs answered "what does Lyra actually do?"* — that information
was scattered across 14 block specs, 17 concept pages, 16 how-to
guides, 7 reference pages, and the source tree. Two new top-level
pages now play the role of front doors:

- **`docs/features.md` (new)** — exhaustive feature catalogue
  organised by surface (CLI, building blocks, providers, routing,
  memory, skills, subagents, verifier, TTS, plan/Org-Mode,
  observability, safety, sessions, eval, integration, cost,
  forward-compat shims). Every shipped feature has four columns:
  **what** · **use case** · **how to invoke** · **where it lives
  in the source** · **maturity flag** (🟢 production / 🟡 beta /
  🔵 forward-compat shim / 🟠 planned). Anchors:
  - 19 Typer subcommands (every `lyra <cmd>` form)
  - ~33 slash commands (grouped: session / plan-build-run / tools-agents
    / observability / config-theme / skill / mcp / plugin / TDD / HUD
    / meta / reflexion / team)
  - 4 modes (agent / plan / debug / ask)
  - 14 building blocks (one row each, linking to canonical specs)
  - 16 LLM providers (with auth env-var per row)
  - The two HUD surfaces: bottom-toolbar (always on) + `lyra hud`
    (preview / presets / inline)
  - The 44 lyra-core internal subsystem directories
- **`docs/use-cases.md` (new)** — task-driven view with **15
  recipes**, each showing the feature stack + a one-screen
  invocation:
  1. Ship a feature with full TDD discipline
  2. Debug a thorny bug systematically
  3. Make my agent remember lessons across sessions
  4. Run N parallel attempts on the same hard task
  5. Run on a tight budget
  6. Enterprise-grade safety
  7. Evaluate the agent against benchmarks
  8. Add a custom tool / skill / hook / MCP server
  9. Replay / audit a past session
  10. Team of role-typed agents (PM / Architect / Engineer / QA)
  11. Embed Lyra into another tool / IDE / custom UI
  12. Evolve / optimize a prompt automatically (`lyra evolve`)
  13. HUD / dashboard for what the agent is doing right now
  14. Long-horizon project (50+ turns)
  15. Schedule a hands-off skill (cron-style)

  Each recipe ends with a "Dig deeper" cross-link table back to
  the relevant concept / how-to / reference pages, so the page is
  a routing layer, not a duplicating layer.

### Changed

- **`mkdocs.yml`** registers a new top-level `Catalogue` tab
  between `Welcome` and `Get Started`, containing the two new
  pages.
- **`docs/index.md`** opens with a new "Two front doors" table
  pointing at `features.md` and `use-cases.md` *before* the four
  reader-track cards, so first-time readers see them immediately.

### Verification

- `python3 -m mkdocs build --strict` → **0 warnings**, 98 HTML
  pages built in 6.98 s (was 96, +2 for the new pages).
- All cross-links to existing concept / how-to / reference / blocks
  / research pages resolve under strict-mode.

## v3.5.3 — 2026-05-01 — "Canonical absorption matrices for papers + repos"

A docs-only release that closes a long-standing audit gap: the
project cited **37 arxiv papers** and **~37 GitHub repos** across
`docs/`, `CHANGELOG.md`, and the source tree, but the bibliography
in `docs/research/papers.md` only listed **25 of the 37 papers**, and
the repo information was split between `docs/community-ecosystem.md`
(13 Claude-Code ecosystem repos) and a flat "Other primary sources"
sublist in `papers.md` (~22 link-only repos). After this release,
every paper and every repo Lyra references is in exactly one
canonical place, with **two new columns** that previous versions
lacked:

- **Lyra absorption mode** — 🟢 adopted / 🔵 forward-compat shim /
  🟡 pattern-mined / 🟠 planned / ⚪ reference-only / 🔴 studied &
  rejected
- **Lyra implementation** — the *exact file path* (or planned slot)
  in the source tree the technique landed in

This makes it possible to walk either matrix top-to-bottom and
answer "*how* does Lyra use Paper X / Repo Y?" without reading the
underlying memos.

### Added

- **`docs/research/papers.md` rewrite** — now 37 papers across five
  waves + a Wave-0 industry-signals section, with the absorption-mode
  + Lyra-implementation columns described above. The 12 papers that
  were cited in `roadmap-v1.5-v2.md` / `roadmap.md` /
  `architecture-tradeoff.md` / `research-synthesis-phase-j.md` /
  `research/memento-skills.md` / `howto/run-eval.md` but missing
  from the bibliography are now in **Wave 5 — research roadmap
  (planned)**: Meta-Harness ([2603.28052](https://arxiv.org/abs/2603.28052)),
  SWE-TRACE ([2604.14820](https://arxiv.org/abs/2604.14820)),
  KLong ([2602.17547](https://arxiv.org/abs/2602.17547)),
  LoCoEval ([2603.06358](https://arxiv.org/abs/2603.06358)),
  BACM-RL ([2604.01664](https://arxiv.org/abs/2604.01664)),
  Refute-or-Promote ([2604.19049](https://arxiv.org/abs/2604.19049)),
  Externalization survey ([2604.08224](https://arxiv.org/abs/2604.08224)),
  VeRO ([2602.22480](https://arxiv.org/abs/2602.22480)),
  Memento RWRL ([2603.18743](https://arxiv.org/abs/2603.18743)),
  Codex pass@k ([2107.03374](https://arxiv.org/abs/2107.03374)),
  Agentless ([2405.15793](https://arxiv.org/abs/2405.15793)),
  Atomic Skills ([2604.05013](https://arxiv.org/abs/2604.05013)),
  Production-agent-gaps survey ([2604.14228](https://arxiv.org/abs/2604.14228)).
  The reproducer download script in the appendix is extended to all
  37 entries.
- **`docs/research/repos.md` (new)** — the canonical repository
  absorption matrix, organised into six sections:
  - **A. Claude-Code / coding-agent ecosystem** (12 unique repos
    after de-duping the `awesome-claude-code` row) — replaces the
    inline 13-row matrix that previously lived in
    `docs/community-ecosystem.md`.
  - **B. Paper reference implementations** (10 repos —
    `aorwall/moatless-tree-search`, `aorwall/moatless-tools`,
    `facebookresearch/swe-rl`, `MineDojo/Voyager`, `stanfordnlp/dspy`,
    `geekan/MetaGPT`, `OpenBMB/ChatDev`, `Xtra-Computing/MAS_Diversity`,
    `Memento-Teams/Memento-Skills`, `polykv-llm` PyPI package).
  - **C. Adjacent infrastructure** (9 repos — `TencentCloud/CubeSandbox`,
    `ghostwright/phantom`, `eric-tramel/moraine`, `midea-ai/SemaClaw`,
    `garrytan/gbrain`, `withseismic/claude-mem`,
    `lyra-contributors/gnomon-hir`, `NousResearch/hermes-agent`,
    `NousResearch/hermes-agent-self-evolution`).
  - **D. Skills + MCP ecosystem** (`anthropics/skills`,
    `skills-mcp/skills-mcp`, `Memento-Teams/Memento-Skills`).
  - **E. Model weights + benchmark corpora** (`openai/SWELancer-Benchmark`,
    `sierra-research/tau2-bench`, `harbor-framework/terminal-bench-2`,
    `openai/prm800k`, `deepseek-ai/DeepSeek-R1`,
    `yuhuili/EAGLE3-LLaMA3.3-Instruct-70B`).
  - **F. Industry signals** (Ryan Leopo *Code is Free* talk,
    GPT-5.5, GLM-5.1, OSS coding-agent star counts).

### Changed

- **`docs/community-ecosystem.md`** is now the **policy + process**
  layer (vendoring tiers, license gates, the seven-step
  add-a-new-repo workflow). The 13-row data table moved to
  `research/repos.md` § A; the page now opens with a quick-link
  table that points at the relevant section of `repos.md` for every
  question type.
- **`docs/research/index.md`** gains a new "Canonical absorption
  matrices" section at the top that surfaces both `papers.md` and
  `repos.md` with their shared six-symbol legend.
- **`mkdocs.yml`** navigation registers the new `research/repos.md`
  page in the Research section, between `Reference papers` and
  `CALM evaluation`.

### Verification

- `python3 -m mkdocs build --strict` → **0 warnings**, 96 HTML pages
  built in 6.84 s (was 95 pages, now +1 for `repos.md`).
- The audit confirmed **no new arxiv IDs or repo URLs** are cited
  in source code, `CHANGELOG.md`, or the source tree but absent
  from the new matrices. If a future contributor adds either, the
  expected workflow is documented in `repos.md` § How to add a new
  repo to this matrix.

### How to read this release

If you only have time for one paragraph: *every arxiv paper and
every GitHub repo Lyra cites is now in one of two pages, with two
new columns that tell you exactly which file in Lyra implements the
technique and what mode that implementation is in (shipped, scaffolded,
pattern-mined, planned, reference, or rejected).* Start at
[`docs/research/papers.md`](docs/research/papers.md) or
[`docs/research/repos.md`](docs/research/repos.md) depending on
which side you care about.

## v3.5.2 — 2026-05-01 — "PolyKV absorption + prompt-cache coordinator"

Honest absorption of the PolyKV paper (Patel & Joshi, April 2026 —
[arXiv:2604.24971](https://arxiv.org/abs/2604.24971)). PolyKV's
literal mechanism (HuggingFace `DynamicCache` injection with q8_0
keys + 3-bit TurboQuant values) requires self-hosted model access
and so doesn't apply to Lyra's hot path of 16 hosted-API providers.
But its architectural insight — *when `N` agents read the same
shared document, share the prefix instead of duplicating it* — maps
directly onto **hosted-provider prompt caching**, which Lyra had
zero infrastructure for. This release ships the production
hosted-API absorption plus a forward-compat shim for the day a
self-hosted Lyra profile lands.

### Added

- **Prompt-cache coordinator
  (`lyra_core.providers.prompt_cache.PromptCacheCoordinator`)**:
  per-process coordinator that holds one anchor per
  `(provider, sha256(shared_text))` pair so sibling subagents
  reading the same document share a single cache write and `N − 1`
  reads. Thread-safe under `concurrent.futures` fan-out, TTL-bounded
  (default 5 min), 4 KB character floor.
- **Five built-in provider adapters**:
  `AnthropicAdapter` (emits `cache_control: ephemeral` block),
  `OpenAIAdapter` (auto-cache by prefix, no payload knob),
  `DeepSeekAdapter` (auto-cache, no payload knob),
  `GeminiAdapter` (emits `CachedContent` resource reference), and
  `NoopAdapter` (telemetry-only fallback for providers without
  caching). Discounts: Anthropic 90%, OpenAI 50%, DeepSeek 90%,
  Gemini 75% on cached tokens.
- **`SharedKVPoolProvider` Protocol shim
  (`lyra_core.providers.shared_kv`)**: forward-compat scaffolding
  mirroring the `BlockStreamingProvider` (CALM) pattern. Declares
  the three methods (`prefill`, `generate`, `release`) a future
  self-hosted PolyKV adapter would implement. Constants
  `DEFAULT_KV_BITS = (8, 3)` and `EXPECTED_COMPRESSION_RATIO ≈ 2.91`
  pinned to the paper's reported numbers. Default registered
  provider raises `NotImplementedError` with a human-readable pointer
  back to the prompt-cache coordinator and the eval doc.
- **Subagent prewarm helper
  (`lyra_core.subagent.cache_prewarm`)**: opt-in
  `SharedPromptDescriptor` + `prewarm_for_specs` + `hit_for_sibling`.
  Pre-warm on the parent thread before
  `SubagentOrchestrator.run_parallel`, workers look up the anchor
  inside the fan-out, get the directive to splice into their own
  request payloads. Guarantees exactly one cache *write* and `N − 1`
  *hits* deterministically across thread races.
- **44 new tests** across
  `test_providers_prompt_cache.py` (25),
  `test_providers_shared_kv.py` (9), and
  `test_subagent_cache_prewarm.py` (10). All pass in 0.12 s.
- **New docs (4 pages, +95 → 95 HTML pages on the strict build)**:
    - [`docs/research/polykv-evaluation.md`](docs/research/polykv-evaluation.md)
      — the honest evaluation memo, mirroring the CALM-evaluation
      shape (TL;DR / what the paper proposes / why most doesn't
      reach a harness / what we shipped / what we didn't / when to
      revisit).
    - [`docs/concepts/prompt-cache-coordination.md`](docs/concepts/prompt-cache-coordination.md)
      — the 15th core concept; sequence diagram, provider discount
      table, telemetry shape, fit in the memory hierarchy.
    - [`docs/howto/use-prompt-cache.md`](docs/howto/use-prompt-cache.md)
      — six recipes (subagent fan-out, Tournament-TTS, custom
      adapter, telemetry, reset, debugging).
    - [`docs/research/papers.md`](docs/research/papers.md) — Wave 4
      added (PolyKV + CALM); reproducer download script extended.
- Cross-links from
  [`docs/concepts/memory-tiers.md`](docs/concepts/memory-tiers.md),
  [`docs/concepts/reasoning-bank.md`](docs/concepts/reasoning-bank.md),
  [`docs/concepts/index.md`](docs/concepts/index.md),
  [`docs/howto/index.md`](docs/howto/index.md),
  [`docs/research/index.md`](docs/research/index.md),
  [`papers/README.md`](papers/README.md), and `mkdocs.yml`.

### What we deliberately did **not** ship

See [`docs/research/polykv-evaluation.md` §"What we deliberately did
not ship"](docs/research/polykv-evaluation.md#what-we-deliberately-did-not-ship)
for the full reasoning. Summary: no `transformers` import, no
TurboQuant vendoring, no automatic cache marking, no cross-provider
anchor sharing. The Protocol shim is option value; the
PromptCacheCoordinator is the production path.

### Verification

- **Lint**: `ruff check` — all checks passed across the 7
  new/modified files.
- **Tests**: 102 pass, 0 fail across the new tests + all 6 existing
  provider tests (regression check on the `__init__.py` export
  expansion).
- **Docs build**: `python3 -m mkdocs build --strict` — 95 HTML pages
  rendered in 6.22 s, zero strict warnings.

## v3.5.1 — 2026-05-01 — "ReasoningBank lift + papers consolidation"

Two themes: complete the ReasoningBank wiring (Phase 2 from
`reasoning_bank.py`'s docstring) and unify the previously-overlapping
`papers/` and `docs/research/` trees behind a single source of truth.

### Added

- **ReasoningBank distillers (`lyra_core.memory.distillers`)**:
  `HeuristicDistiller` (deterministic, no LLM, fills the bank on
  every session-end) and `LLMDistiller` (smart-slot wrapper with
  graceful fallback). Replaces the previous "bring your own
  distiller" friction documented in
  [`docs/concepts/reasoning-bank.md`](docs/concepts/reasoning-bank.md).
- **SQLite persistence layer
  (`lyra_core.memory.reasoning_bank_store.SqliteReasoningBank`)**:
  FTS5-backed store that lives at
  `<repo>/.lyra/memory/reasoning_bank.sqlite` and survives process
  restarts. Same public surface as the in-memory `ReasoningBank` so
  the chat injector and any custom callers swap by changing a
  single line. Falls back to `LIKE` substring scan on SQLite builds
  without FTS5.
- **MaTTS wired into `TournamentTts`**: pass
  `reasoning_bank=<bank>` (and optionally `matts_prefix_k=...`) and
  every attempt is prefixed with a rotated slice of the bank's
  recall window. The §4 diversification guarantee from
  arXiv:2509.25140 is now end-to-end. Without the bank parameter
  behaviour is byte-identical to the previous tournament loop.
- **`lyra memory` CLI subcommand** with `recall`, `list`, `show`,
  `stats`, `wipe`, and `record` verbs. JSON output mode on every
  read verb for scripting.
- **New docs pages**:
  [`docs/concepts/reasoning-bank.md`](docs/concepts/reasoning-bank.md),
  [`docs/howto/use-reasoning-bank.md`](docs/howto/use-reasoning-bank.md),
  and [`docs/research/papers.md`](docs/research/papers.md). The
  reasoning-bank concept page is linked from the memory tiers page;
  the bibliography page replaces the prose previously in
  `papers/README.md`.

### Changed

- **`papers/README.md`** is now a thin pointer (12 lines) to the
  canonical bibliography at `docs/research/papers.md`. PDFs stay in
  `papers/` as binary assets; all prose lives in the docs site.
  Single source of truth for "which papers does Lyra read?" — no
  more risk of bibliography drift between two files.
- `lyra_core.memory.__init__` re-exports the new `HeuristicDistiller`,
  `LLMDistiller`, `SqliteReasoningBank`, `default_db_path`, and
  `open_default_bank` symbols so `from lyra_core.memory import ...`
  is a one-stop import.
- MkDocs nav adds the new concept (Core Concepts → ReasoningBank),
  how-to (How-To → Use the ReasoningBank), and reference (Research
  → Reference papers) entries. Total: **88 → 91 HTML pages**, build
  time **9.30 s → 6.44 s** (strict, no warnings).

### Tests

- 19 new tests for the heuristic distiller (`test_memory_distillers`),
  the SQLite-backed bank (`test_memory_reasoning_bank_sqlite`), and
  the MaTTS / Tournament-TTS integration
  (`test_tts_tournament_matts_integration`). 7 new CLI smoke tests
  for `lyra memory` (`test_command_memory`).
- All 64 existing TTS / memory / reasoning-bank / diversity tests
  continue to pass; no behavioural regression in the in-memory bank.

### Notes

- The ReasoningBank now ships **on by default** when a session has
  write access to `.lyra/memory/`. Disable per-run with
  `--no-memory` (planned v3.6) or by pointing at a read-only
  snapshot via `--db`.
- The `LLMDistiller` is **off the hot path** by design — wire it
  into a `PreSessionEnd` hook or a cron schedule rather than the
  agent loop itself so the smart-slot call doesn't add per-turn
  latency.

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
