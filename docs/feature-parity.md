# Lyra Feature Parity Matrix

> **Status**: living document, **v1.3.0 snapshot on 2026-04-27** (post
> v3.3.0 "Phase M: Token Observatory" — supersedes the v1.2.0 / 2026-04-27
> post-v3.2.0 snapshot).
> **Scope**: Maps every feature we could steal from Claude Code (Anthropic),
> sst/opencode, Hermes Agent (Nous Research), MetaGPT, CodeBurn
> (getagentseal/codeburn), and the 2025–2026 agent fleet into (a) what
> already ships in Lyra, (b) what lands in the current wave, and
> (c) what's deferred to the v1.5 / v1.7 / v2 roadmap. Also lists
> net-new advanced features only Lyra offers — the ones that justify
> being a separate harness at all.

## v3.3.0 — Token Observatory (Phase M, 2026-04-27)

`lyra burn` is the first "second-order" surface in Lyra: it doesn't run
a turn, it reads the JSONL turn log Phase L produces and tells you
where the spend went, what activity you were doing, and which sessions
actually paid off. Inspired by
[CodeBurn](https://github.com/getagentseal/codeburn) — the 13-category
classifier, retry counter, and one-shot rate are direct ports — but
re-aimed at Lyra's own JSONL (no cross-tool ingestion in v3.3) with two
Lyra-specific extensions: the 4-mode taxonomy biases the classifier,
and the small/smart split (`deepseek-v4-flash` vs `deepseek-v4-pro`)
gets its own waste rule (`R-FLASH-OVER-PRO`).

| Feature | claw-code | opencode | hermes-agent | CodeBurn | Lyra (v3.3) |
|---|---|---|---|---|---|
| Cost observatory TUI | — | — | — | ✅ (`burn`) | ✅ `lyra burn` |
| Activity classifier | — | — | — | ✅ 13 cat | ✅ 13 cat (port + Lyra ext) |
| One-shot rate / retry counter | — | — | — | ✅ | ✅ |
| Model comparison | — | — | — | ✅ `compare` | ✅ `lyra burn compare` |
| Waste-pattern optimizer | — | — | — | ✅ `optimize` | ✅ `lyra burn optimize` |
| Git-yield correlation | — | — | — | ✅ `yield` | ✅ `lyra burn yield` |
| Cross-tool data ingestion | — | — | — | ✅ providers/* | 🟡 v3.4 |
| Native macOS menubar | — | — | — | ✅ | ⊘ skipped (CLI-first) |
| Plan/limit tracking (Pro/Max/Team) | — | — | — | ✅ | ⊘ deferred (use `--budget`) |
| Currency conversion (EUR/JPY) | — | — | — | ✅ | ⊘ won't fix (USD only) |

## v3.2.0 — Claude-Code 4-mode taxonomy alignment (2026-04-27)

A small but breaking surface change: Lyra's REPL mode taxonomy
collapses from five (`plan / build / run / explore / retro`) to the
same four that `claw-code`, `opencode`, and `hermes-agent` use —
`agent / plan / debug / ask`. The trigger was a production bug: when
asked "how many modes do you have?", Lyra would hallucinate `BUILD /
RED / GREEN / REFACTOR` as four peer modes by leaking the TDD
plugin's internal phase machine into the user-visible answer. The
fix has two pieces — a structural rename and a prompt-grounding
contract — both shipped in v3.2.0.

| Phase-K row | Source / motivation | Lyra surface (v3.2.0+) |
|---|---|---|
| 4-mode REPL taxonomy | Claude Code, `claw-code`, `opencode`, `hermes-agent` | `_VALID_MODES = ("agent", "plan", "debug", "ask")` in `lyra_cli.interactive.session`. Default mode = `agent`. Tab cycle order = `(agent, plan, ask, debug)` (execution-capable modes at opposite ends so a single Tab never accidentally toggles between them). |
| Mode prompt enumeration | screenshot bug — `terminals/6.txt:39-61` in v3.1 dogfood | Shared `_LYRA_MODE_PREAMBLE` lists `agent, plan, debug, ask` verbatim and disclaims TDD's RED → GREEN → REFACTOR cycle as a plugin's internal phases (not modes). Every mode-specific system prompt is `_LYRA_MODE_PREAMBLE + "\n" + <tail>` so the LLM sees the closed mode set on every turn. |
| Legacy alias remap | back-compat for v3.1 settings.json, stored sessions, muscle memory | `_LEGACY_MODE_REMAP` translates `build → agent`, `run → agent`, `explore → ask`, `retro → debug` at four entry points: `InteractiveSession.__post_init__`, `_TurnSnapshot` deserialisation, `_cmd_mode`, and `lyra acp --mode`. The `/mode <legacy>` command emits a one-shot `'<legacy>' was renamed to '<canonical>' in v3.2.0` notice on first use. |
| Regression test | this snapshot | `packages/lyra-cli/tests/test_modes_taxonomy_v32.py` — 19 tests, runs in 0.14s. Pins `_VALID_MODES`, default mode, `_MODE_HANDLERS`, `_MODE_SYSTEM_PROMPTS`, `_MODE_BLURBS`, `_MODE_CYCLE_TAB`, every system prompt's preamble (verbatim mode enumeration + TDD-disclaimer), and the legacy alias remapping at every entry point. Reproduces the screenshot bug as a failing test on v3.1. |

**Compat surface.** Every code path that accepts a mode string still
honours the legacy v3.1 names. So `--mode build` on the CLI,
`mode = "explore"` in `~/.lyra/settings.json`, and a stored
`turns.jsonl` from a v3.1 session all keep working without manual
migration; they resolve to the canonical v3.2 mode under the hood.
Test suites that fingerprint mode strings or system-prompt bodies
need updating — see the v3.2.0 entry in `CHANGELOG.md` for the full
upgrade checklist.

**Test totals after Phase K**: `lyra-cli` **1119** (+70 vs v3.1.0,
of which 19 are the new modes-taxonomy regression and the rest are
mode-rename touch-ups across 12 test files), `lyra-core` unchanged
at **818**. Zero `xfail`; two pre-existing sandbox-only skips
(`test_slash_diff.py`, no `git` in CI sandbox).

---

## v3.1.0 — Phase J research-synthesis ports (2026-04-27)

A targeted survey of the 2025–2026 agent fleet (`hermes-agent`,
`gbrain`, `hermes-webui`, `hermes-agent-self-evolution`, MetaGPT, and
arxiv 2604.14228) selected five high-leverage ideas that ship in
v3.1.0. The selection criteria, the ideas explicitly **not** pulled,
and the per-feature citation chain all live in
[`docs/research-synthesis-phase-j.md`](research-synthesis-phase-j.md).

| Phase-J row | Source | Lyra surface (v3.1.0+) |
|---|---|---|
| Brain bundles | `garrytan/gbrain` | `lyra brain list|show|install` + `lyra_core.brains.{BrainBundle, BrainRegistry, install_brain}`. Four built-ins: `default`, `tdd-strict`, `research`, `ship-fast`. |
| `pass^k` reliability metric | τ-bench `yao2024taubench`, arxiv 2604.14228 §12.1 | `lyra evals --passk N [--json]` + `lyra_core.eval.{CaseTrials, PassKReport, run_passk}`. Surfaces silent flakiness as `reliability_gap = pass@k − pass^k`. |
| Team roles + orchestrator | MetaGPT `hong2024metagpt` (ICLR 2024 oral) | `/team [show <name>|plan|run <task>]` + `lyra_core.teams.{TeamRole, TeamPlan, TeamRegistry, run_team_plan}`. Five built-in roles: `pm`, `architect`, `engineer`, `reviewer`, `qa`. |
| Reflexion retrospective loop | Shinn et al. 2023, arxiv 2604.14228 §12.3 | `/reflect [on|off|add|tag|clear]` + `lyra_core.loop.{Reflection, ReflectionMemory, inject_reflections, make_reflection}`. JSON snapshot at `<repo>/.lyra/reflexion.json`. |
| GEPA-style prompt evolver | `khattab2024gepa`, `NousResearch/hermes-agent-self-evolution` | `lyra evolve --task spec.yaml [--generations N] [--population K]` + `lyra_core.evolve.{EvolveCandidate, evolve, pareto_front, score_candidate, templated_mutator}`. Pareto-filtered (score↑ vs length↓). |

**Deliberately not pulled.** A web/mobile UI from `hermes-webui` is
out of scope for a CLI; the always-on self-evolution daemon from
`hermes-agent-self-evolution` is out-of-posture (Lyra ports the
algorithm, not the daemon); MetaGPT's "1 sentence → repo" autodriver
is out-of-observability (we ship the role + SOP primitives only).
See `docs/research-synthesis-phase-j.md` §6 for the full rejection
list and reasoning.

---

## v3.0.0 — TDD repositioned + Phase-I parity ports (2026-04-27)

v3.0.0 splits cleanly into two themes that landed in the same release:

* **Posture change.** Lyra was advertised as "TDD-first" through
  v2.x. The actual TDD plumbing — state machine, gate hook,
  `/phase` / `/red-proof` / `/tdd-gate` / `/review` rubric — all
  still ships. What changed is the default: `tdd_gate_enabled =
  False`, the four mode prompts no longer say "TDD-first", and
  `/review` reports a neutral `tdd-gate: off (opt-in)` line.
  `/tdd-gate on` (per-session) and `/config set tdd_gate=on`
  (persistent) restore the v2.x posture verbatim. See the v3.0.0
  block in `CHANGELOG.md` for the full delta.

* **Phase-I parity ports.** The post-Phase-H audit (see
  `projects/lyra/docs/superpowers/audits/2026-04-27-phase-h-audit.md`)
  identified five high-ROI features that ship in `claw-code`,
  `opencode`, and/or `hermes-agent` but had no Lyra equivalent.
  All five land in v3.0.0 with locked test surface:

  | Phase-I row | Source repos | Lyra surface (v3.0.0+) |
  |---|---|---|
  | `AskUserQuestion` LLM tool | claw-code, opencode, hermes-agent | `lyra_core.tools.ask_user_question.make_ask_user_question_tool` (callback-driven, returns `{cancelled, answers}`). |
  | Named toolsets | hermes-agent | `lyra_core.tools.toolsets.{ToolsetRegistry, apply_toolset, register_toolset}` plus five built-in bundles (`default`, `safe`, `research`, `coding`, `ops`); REPL `/toolsets` (list / show / apply). |
  | `/redo` paired with `/rewind` | opencode (`revert/unrevert`) | `InteractiveSession.redo_one`, slash `/redo` with aliases `/redo!` and `/unrewind`; redo stack drains on any new plain-text turn so divergent timelines can't be resurrected. |
  | In-REPL `/init` | opencode | `_cmd_init` runs the same scaffolder as `lyra init`; `/init force` overwrites; idempotent by default. |
  | User-authored slash commands | opencode | `lyra_cli.interactive.user_commands.load_user_commands` walks `<repo>/.lyra/commands/*.md`; frontmatter (`description`, `args_hint`, `aliases`) is honoured; body is rendered with `{{args}}` substitution and dispatched as a plain-text turn; `/user-commands` (`/user-cmds`) lists / `reload`s; built-ins always shadow user commands. |

  Test totals after Phase I: `lyra-cli` **1049** (+33 vs v2.7.1's
  1016), `lyra-core` **818** (+22 vs v2.7.1's 796), other packages
  unchanged. Zero `xfail`, two sandbox-only skips.

---

## v2.3.0 → v2.7.0 — The "Honest Rebuild" series (2026-04)

The v2.0.0 verification snapshot below is correct for the Wave-F
*surface*: every cell that says "shipped" maps to a code symbol and a
passing contract test. What it doesn't capture is the **wiring gap**
the v2.3 → v2.7 series spent five sprints closing — the difference
between a feature having a code symbol and that symbol actually being
reachable from the REPL with a real LLM provider on the other end.

The audit that kicked off the series found 34 such "advertised but not
wired" issues across three tiers. The series fixed all of them:

| Phase   | Version  | What landed |
|---------|----------|-------------|
| **A** (provider truth)        | v2.3.0 | `last_usage` on every provider (Anthropic, Gemini, Ollama, Bedrock, Vertex, Copilot), `tools=` forwarding fix on Vertex, `build_llm` registers Bedrock/Vertex/Copilot, SSE-omits-usage backstop, pricing for grok/codestral/qwen-plus/llama-3.3, `_chat_history` resume from `turns.jsonl`. |
| **B** (chat as agent)         | v2.4.0 | Real tool-call loop in `_chat_with_llm` (Read/Glob/Grep/Write/Edit), Rich tool-card renderer in chat, SKILL.md descriptions injected into the system prompt, procedural memory + reasoning bank queried before every turn. |
| **C** (MCP for real)          | v2.5.0 | `StdioMCPTransport` (JSON-RPC handshake, `initialize`/`list_tools`/`call_tool`), `~/.lyra/mcp.json` autoload, `lyra mcp add/remove`, MCP `inputSchema → OpenAI tools=` adapter (`mcp__server__tool` naming), trusted MCP tools fed into the chat loop. |
| **D** (advertised slashes)    | v2.6.0 | `/spawn` → `SubagentRunner`, `CronDaemon` started from driver / `/cron run` actually executes, `LifecycleBus` events emitted from chat handler + agent loop, `discover_plugins` on driver boot, `lyra acp` stdio JSON-RPC server, default FTS5 `SessionStore` wired to `/search`. |
| **E** (production polish)     | v2.7.0 | `/evals` runs inline against the bundled `lyra-evals` corpora, `/compact` is a real heuristic chat-history compactor, `LifecycleBus → HIR JSONL → optional OTel` bridge, `SubagentRunner` allocates **real `git worktree`** isolation when the parent is a git repo, `/spawn` factory fixed to drive lyra-core's loop on a single LLM substrate via `_LyraCoreLLMAdapter`, every slash menu description audited (no more `(stub)` / `(planned)` / `(Wave-X)` markers that didn't match reality), README + this doc rewritten to match what ships. |
| **F** (small/smart split)     | **v2.7.1** | DeepSeek small/smart routing modeled on Claude Code's Haiku-for-cheap-turns / Sonnet-for-reasoning pattern: **`fast_model`** (default `deepseek-v4-flash` → `deepseek-chat`) handles chat / tool calls / summaries / `/compact`; **`smart_model`** (default `deepseek-v4-pro` → `deepseek-reasoner`) handles `lyra plan`, `/spawn`, cron fan-out, `/review --auto`, and the verifier's Phase-2 LLM evaluator. Single-seam role-keyed resolver (`_resolve_model_for_role`), in-place provider mutation (so the cache, history, and budget meter all stay attached), universal + provider env stamping (`HARNESS_LLM_MODEL` plus `DEEPSEEK_MODEL` / `ANTHROPIC_MODEL` / `OPENAI_MODEL` / `GEMINI_MODEL`), `/model fast` / `smart` / `fast=<slug>` / `smart=<slug>` slash UX, full docs sweep across `projects/lyra/`. |

**Test totals after F.7**: `lyra-cli` 1016, `lyra-core` 796, `lyra-mcp`
57, plus `lyra-skills` and `lyra-evals` — **≥1869 passing across the
five packages** with zero `xfail` for the v2.x wiring contracts.

The remaining "gaps" that survive the v2.7.0 cut are intentional and
documented as such (e.g. `/voice` is an advisory flag not a real
voice-mode integration; `/wiki` and `/team-onboarding` are Wave-E
templating helpers, not full doc generators). Nothing in the v2.7.0
slash menu reads as a promise the binary doesn't keep.

---

## Verification snapshot

**Lyra ↔ ui-refs Verification — v0.8, 2026-04-24, post v2.0.0 "Frontier" (Wave F)**

v2.0.0 closes out the
[full-parity roadmap](superpowers/plans/2026-04-24-full-parity-roadmap.md):
Wave F's 15 task buckets (`f1`…`f15`) ship **15 new modules / 186 new
contract tests**. The whole-repo suite reaches **1530 passed / 2 skipped
/ 0 failed** (sandbox-bound git tests in `test_subagent_parallel.py`,
`test_worktree_lifecycle.py`, and `test_merge_conflict_resolver.py` are
deselected — they pass cleanly outside the sandbox).

**v2.0.0 — Wave F shipments (15 task buckets, 186 new contract tests)**:

- `lyra_core.tdd.state.TDDStateMachine` — strict/lenient FSM
  `IDLE → PLAN → RED → GREEN → REFACTOR → SHIP` with typed evidence
  artefacts plus a reason-driven `transition()` API for the REPL's
  `/phase` surface. (Task f1)
- `lyra_core.verifier.trace_verifier` — cross-channel verifier
  that extracts file-line claims from assistant narration and
  cross-checks against the filesystem + optional git diff,
  rejecting path escapes and hallucinated citations. (Task f2)
- `lyra_core.loop.refute_or_promote.RefuteOrPromoteStage` —
  adversarial sub-agent that attempts to refute proposed
  solutions; successful refutations loop back to PLAN. (Task f3)
- `lyra_core.eval.prm.{Rubric, RubricJudge, RubricSet,
  RubricSetReport}` — named, weighted-rubric Process Reward
  Model that scores turns 0–1 and surfaces weakest-link rubrics
  for qualitative regressions. (Task f4)
- `lyra_core.context.ngc.{NGCCompactor, NGCItem,
  NGCOutcomeLogger}` — grow-then-evict Neural Garbage Collector
  with outcome logging for offline classifier training. (Task f5)
- `lyra_core.skills.{registry, router}` — reuse-first hybrid
  skill router (`HybridSkillRouter`) with trigger matching +
  historical success weighting. (Task f6)
- `lyra_core.skills.optimizer.TriggerOptimizer` — rule-based
  auto-optimizer with token-set deduplication so near-duplicate
  triggers never accumulate. (Task f7)
- `lyra_core.skills.synthesizer.SkillSynthesizer` — drafts new
  `Skill` entries from user queries and proposed triggers. (Task f8)
- `/review --auto` enhancement — post-turn verifier runs
  automatically after every agent turn. (Task f9)
- `lyra_core.plugins.{registry, manifest, runtime}` — two parallel
  plugin surfaces (programmatic `PluginManifest` / `PluginRegistry`
  plus declarative `PluginManifestSpec` / `PluginRuntime`) with
  per-plugin isolation on dispatch. (Task f10)
- `lyra_core.meta.{corpus, outer_loop}` — `ParityCorpus` +
  `HarnessTask` + `MetaHarness` for ranking agent configurations
  by pass rate on a standard evaluation set. (Task f11)
- `lyra_core.arena.elo.Arena` — Elo-style pairwise leaderboard
  for harness configurations. (Task f12)
- `lyra_core.skills.federation.{SkillManifest,
  FederatedRegistry, Federator}` — export/import shared skill
  manifests with merge strategies. (Task f13)
- `lyra_core.klong.checkpoint` — KLong long-horizon snapshot
  format with schema versioning + forward migrators; sessions
  resume cleanly across model generations. (Task f14)
- `lyra_core.ide.bridges.{IDEBridge, build_open_command}` plus
  the frontier UX slash commands (`/split`, `/vote`, `/observe`,
  `/ide`, `/catch-up`). (Task f15)

All six waves of the full-parity roadmap (B through F) have shipped.
The roadmap's §1 goal — "every cell currently flagged as NOW / v1.5 /
v1.7 / v2 / stub… backed by a verified code symbol and a passing
contract test" — is met.

**v1.9.0 — Wave E shipments (15 task buckets, 16 channel
adapters + 4 backends + 5 toolkits)**:

- `lyra_cli.channels.{base, _errors}` — `ChannelAdapter`
  protocol + `Inbound`/`Outbound` + multiplexing `Gateway`
  daemon. Lazy `asyncio.Queue` allocation in `start()` so
  Python 3.9 doesn't crash (no event loop at class-body time).
- 16 adapters: `slack`, `discord`, `matrix`, `email`, `sms`
  (Twilio/Vonage backends), and 11 long-tail HTTP-shaped
  channels (`feishu`, `wecom`, `mattermost`, `bluebubbles`,
  `whatsapp`, `signal`, `openwebui`, `homeassistant`, `qqbot`,
  `dingtalk`, `webhook`) over a shared `_HttpChannelAdapter`
  base. All optional dependencies fail loudly with a
  `FeatureUnavailable` install hint instead of a mysterious
  `ImportError`.
- 4 real terminal backends replacing v1.7.2 stubs:
  `lyra_core.terminal.modal.ModalBackend` (`lyra[modal]`),
  `terminal.ssh.SSHBackend` (`lyra[ssh]`, paramiko-shaped, argv
  via `shlex.join`), `terminal.daytona.DaytonaBackend`
  (`lyra[daytona]`), and `terminal.singularity.SingularityBackend`
  (Apptainer CLI via `subprocess`).
- `lyra_core.tools.image_describe` + `image_ocr` — repo-root
  jail, pluggable VLM, fallback OCR backends (`pytesseract`,
  `easyocr`).
- `lyra_cli.voice.{stt, tts}` + `InteractiveSession.voice_mode`
  + `/voice [on|off|status]` slash command.
- `lyra_cli.interactive.replay.{ReplayController, ReplayEvent,
  load_replay, step_through}` + `/replay
  [next|prev|reset|status|all]`.
- `lyra_core.safety.redteam.{RedTeamCorpus, RedTeamReport,
  default_corpus, score_monitor}` — labelled corpus + TPR/FPR/
  per-category coverage scorer, doubles as a regression gate.
- `lyra_core.eval.{EvalCorpus, EvalReport, run_eval,
  DriftGate, DriftDecision}` — golden eval corpus + drift gate
  with global + per-category tolerances and JSON baseline I/O.
- `lyra_core.wiki.{generate_wiki, generate_onboarding}` +
  `/wiki [generate|preview]` + `/team-onboarding [role]` —
  offline crawler produces an actual repo wiki under
  `<repo>/.lyra/wiki/` and role-targeted onboarding plans.

**Lyra ↔ ui-refs Verification — v0.6, 2026-04-24, post v1.8.0 "Agentic Backbone" (Wave D)**

v1.8.0 ships **15 backbone features** as part of Wave D of the
[full-parity roadmap](superpowers/plans/2026-04-24-full-parity-roadmap.md):
real subagent runtime + registry + presets, DAG fan-out, variant
runs, layered permissions (destructive / secrets / injection),
per-session tool-approval cache, real `ExecuteCode` and `Browser`
tools, custom user tools, the lifecycle bus, MCP registry + trust
banner, live token-→-USD deduction, preflight wired into the agent
loop, and live-streaming `/pair`. Combined pytest run: **1143
passed**, 0 regressions (4 failures + 7 errors are sandbox-only
`git init` denials carried over from Wave-A/B). See §5e for the
v1.8.0 row-by-row delta; §5d retains the v1.7.5 delta.

**v1.8.0 — 15 backbone features shipped (Wave D of full-parity roadmap)**:

- `lyra_core.subagent.runner.SubagentRunner` — single-spawn orchestrator (worktree + stdio + HIR scope tagging)
- `InteractiveSession.subagent_registry` + live `/agents` + `Ctrl+F` re-focus
- `lyra_core.subagent.presets` — `~/.lyra/agents/<name>.yaml` user presets (3 built-ins: `explore` / `general` / `plan`)
- `lyra_core.subagent.scheduler` — DAG fan-out (level-by-level, bounded `max_parallel`, skip-on-failure)
- `lyra_core.subagent.variants.run_variants` — best-of-N with default `max(payload["score"])` judge
- `lyra_core.permissions.injection` — 8-pattern prompt-injection sweep
- `lyra_core.permissions.stack.PermissionStack` — destructive + secrets + injection behind one `check()`
- `lyra_cli.interactive.tool_approval.ToolApprovalCache` — per-session allow/deny ledger (mode-aware)
- `lyra_core.tools.execute_code` — sandboxed Python subprocess (AST allow-list, wall-clock cap, stripped env)
- `lyra_core.tools.browser` — Playwright wrapper with graceful "install lyra[browser]" fallback
- `lyra_core.tools.user_tools` — `@tool`-decorated callables loaded from `~/.lyra/tools/<name>.py`
- `lyra_core.hooks.lifecycle` — typed `LifecycleBus` for the 6 agent-loop seams
- `lyra_core.mcp` — MCP server registry + `trust_banner_for` (untrusted by default)
- `lyra_cli.interactive.budget.BudgetMeter` — token-→-USD ledger + `gate()` short-circuit
- `lyra_core.providers.preflight_plugin.PreflightPlugin` + `lyra_cli.interactive.pair_stream.PairStream`

**Lyra ↔ ui-refs Verification — v0.5, 2026-04-24, post v1.7.5 "REPL Convergence" (Wave C)**

v1.7.5 ships **15 REPL-convergence features** as part of Wave C of
the full-parity roadmap, flipping every UI / persistence /
slash-command cell that was `NOW`, `v1.5`, or `v1.7` in §1.1–§1.3
to `✓ shipped (v1.7.5)`. The user-observable REPL surface is now
at strict parity with claw-code, opencode, and hermes-agent — plus
two net-new items (TDD-`/red-proof`, `/btw` side-channel log) the
reference agents don't ship. See §5d for the v1.7.5 row-by-row
delta; §5c retains the v1.7.4 delta, §5b the v1.7.3 delta, and §5
the v1.7.2 delta for history.

**v1.7.5 — 15 REPL features shipped (Wave C of full-parity roadmap)**:

- `/rewind` persistent + `/resume` real (TurnSnapshot JSONL round-trip)
- `/fork` + `/rename` + `/sessions` + `/export` (`SessionsStore`)
- `/map` ASCII dependency tree (depth-capped, friendly empty case)
- `/blame` + `/trace` + `/self` (HIR `RingBuffer` + git fallback)
- `/budget set` + `/badges` (`BudgetCap` + `<repo>/.lyra/badges.json`)
- 6 direct keybinds (`Ctrl+T`, `Ctrl+O`, `Esc Esc`, `Tab`, `Alt+T`, `Alt+M`)
- `/mode` full dispatcher (build / plan / run / retro / explore + list/toggle)
- `/handoff` (markdown PR description + git diff + writes `.lyra/handoff.md`)
- `/effort` (interactive picker + env-var bridge to `HARNESS_REASONING_EFFORT`)
- `/ultrareview` + `/review` + `/tdd-gate` (3-voice mock fan-out + verifier)
- `/config` + `/theme` + `/skin` (`~/.lyra/config.yaml` round-trip + `from_config`; +2 themes: midnight, paper)
- `/vim` real toggle (config-backed; `vi_bindings()` factory)
- `/red-proof` minimal (pytest assert-RED)
- `/tools` rich + `/btw` (FIFO side-channel) + `/pair` (toggle + status indicator)
- Paste-as-image (data URI + magic-byte sniff; OCR → Wave F)

v1.7.4 closed 15 provider-ecosystem features; v1.7.3 Phase A flipped
12 v1.7.2 scaffolds to real implementations; v1.7.2 closed 15
overclaims via scaffolds-with-tests.

**v1.7.4 — 15 provider features shipped (Wave B of full-parity roadmap)**:

- `lyra_core.providers.dotenv` — stdlib `.env` parser (claw-code parity)  *(see §5c)*
- `lyra_core.providers.auth_hints` — foreign-cred sniffer + suggestion
- `lyra_core.providers.aliases` — model-alias registry (`opus`/`sonnet`/`haiku`/`grok`/`kimi`/`qwen-*`)
- Plugin `max_output_tokens` override via `~/.lyra/settings.json`
- `lyra_core.providers.preflight` — context-window preflight + `ContextWindowExceeded` *(library-only in v1.7.4; agent-loop integration in Wave D)*
- `ProviderRouting` for OpenRouter (sort/only/ignore/order/require_parameters/data_collection)
- `lyra_cli.providers.fallback.FallbackChain` — transient-error retry + fatal-error short-circuit
- 6 new OpenAI-compatible presets: DashScope, vLLM, llama-server, TGI, Llamafile, MLX-LM
- `lyra_cli.providers.bedrock.AnthropicBedrockLLM` (`lyra[bedrock]`)
- `lyra_cli.providers.vertex.GeminiVertexLLM` (`lyra[vertex]`)
- `lyra_cli.providers.copilot.CopilotLLM` + token store (rotating session tokens)
- `lyra_cli.interactive.auth.DeviceCodeAuth` + `/auth` slash (RFC 8628 OAuth device-code)
- `lyra_cli.llm_factory` wires `.env` + aliases + auth hints + telemetry
- `/model list` + `/models` slash with live ●/✓/— markers
- `/diff` real (`git diff --stat` + body, 20k truncate, friendly errors)

v1.7.2 closed 15 overclaims via scaffolds-with-tests; v1.7.3 Phase A
flipped 12 of those scaffolds to real implementations.

**v1.7.2 — 15 gaps closed in code** (scaffolds-with-tests):

- `PostToolUse` hook on `AgentLoop` (`_fire("post_tool_call", ToolResultCtx)`)
- Hermes-compat slash aliases (`/compress`, `/usage`, `/insights`, `/skin`)
- `task(worktree=True)` subagent isolation via `WorktreeManager`
- LSP tool contract (`diagnostics`, `hover`, `references`, `definition`)
- `codesearch` (ripgrep + Python fallback)
- `apply_patch` (v4 envelope + unified diff)
- `NotebookEdit` (Jupyter cell CRUD)
- `pdf_extract` (pypdf / pdfminer cascade)
- `/cron` scheduled automations + `CronStore`
- ACP bridge (`AcpServer`, JSON-RPC 2.0)
- Multi-channel gateway adapter `Protocol` + Telegram stub
- Plugin-manifest loader (`.lyra-plugin` / `.claude-plugin`)
- Multi-backend terminal — `LocalBackend` real + Docker / Modal / SSH / Daytona / Singularity typed stubs
- Mock-LLM parity harness (`ScriptedLLM`, `ScenarioCase`, `StreamChunk`)
- RL / Atropos trajectory tooling (`TrajectoryRecorder`, `rl_list_environments`)

**v1.7.3 Phase A — 12 scaffolds flipped to real**:

- `/compact` LLM summariser (`compact_messages` + `CompactResult`)
- `/context` token-bar grid (`render_context_grid`)
- `/agents` + `/spawn` on `SubagentRegistry`
- `TodoWrite` tool + atomic `TodoStore`
- LSP backend real (`MultilspyBackend`, `MockLSPBackend`, `FeatureUnavailable`)
- Plugin runtime (`PluginRuntime` lazy-loads + event dispatch)
- `DockerBackend` real docker-py wrapper
- `WebSearch` + `WebFetch` tools (httpx + bs4, pluggable provider)
- Telegram adapter real Bot API (`use_http=True` / injected client)
- Cron daemon — deterministic `tick()` + threaded `start/stop`
- `/search` FTS5 slash UI on `InteractiveSession.search_fn`
- `OpenTelemetryCollector` — HIR events → real OTel spans

**7 cells were doc-truth corrections** — no new code, the v0.1
matrix claimed features under the wrong shape, name, or milestone:

- Hermes `mcp serve` was marked `—` in v0.1; it ships via FastMCP, flipped to `✓`.
- The cited `lyra_cli.commands.aliases` module never shipped — aliases always lived on `CommandSpec(aliases=…)` in `lyra_cli.interactive.session`.
- `@file` completion, multi-line input, `Ctrl+G` external editor, prompt-continuation glyph, and `/keybindings` were already shipped — not "NOW".
- `/cost` / `/stats` alias cells were wired to `/context` by accident; corrected to `/usage` and `/insights` per hermes convention.
- Worktree isolation was scheduled to `v1 Phase 7` even though the scaffold was already in tree.

Every `✓ shipped (v1.7.2)`, `✓ shipped (v1.7.3)`, `✓ shipped (v1.7.4)`,
and `✓ shipped (v1.7.5)` cell is backed by a verified code symbol
**and** a test-file path — see §5, §5b, §5c, and §5d for the
row-by-row mappings. The full lyra-cli suite runs **581 passed /
2 sandbox-skipped** (verified 2026-04-24 via `python3 -m pytest
packages/lyra-cli` from `projects/lyra/`, with the same 2
git-sandbox-dependent `/diff` tests deselected on this host as in
v1.7.4 — and ~11–12 sandbox-only `git init` / `git worktree`
failures in the lyra-core suite that are also pre-existing) — up
from the v1.7.4 baseline after adding **+76 new RED/GREEN contract
tests across 15 new files** in the v1.7.5 Wave-C pass plus **+28
post-review safety tests** in `test_session_safety.py` (on top of
111 v1.7.4 tests, on top of 77 v1.7.3 tests, on top of 132 v1.7.2
tests).

---

## 0. Reading guide

| column | meaning |
|---|---|
| **CC** | present in Claude Code |
| **OC** | present in sst/opencode |
| **HA** | present in Hermes Agent |
| **OUR** | present in Lyra `main` |
| **NOW** | landing in the current wave (this commit batch) |
| **v1.5 / v1.7 / v2** | planned milestones (see `roadmap-v1.5-v2.md`) |
| **★** | net-new feature, not in any of the three |

Parity is measured at "has the same user-observable contract", not line-by-line implementation.

---

## 1. REPL / Interactive shell

### 1.1 Prompt & input

| feature | CC | OC | HA | OUR | ship |
|---|---|---|---|---|---|
| coloured mode badge in prompt | ✓ | ✓ | ✓ | ✓ | — |
| bottom status toolbar with segmented metadata | ✓ | ✓ | ✓ | ✓ | — |
| segmented key-hint strip | ✓ | ✓ | ✓ | ✓ | — |
| persistent file history | ✓ | ✓ | ✓ | ✓ | — |
| `/` slash command dropdown with descriptions | ✓ | ✓ | ✓ | ✓ | — |
| `@file` path mention with completion | ✓ | ✓ | ✓ | ✓ | — |
| `!cmd` bash mode with output panel | ✓ | ✓ | ✓ | ✓ | — |
| multi-line input (`\`+Enter / Alt+Enter / Ctrl+J) | ✓ | ✓ | ✓ | ✓ | — |
| prompt continuation glyph (`· ` on wrapped lines) | ✓ | — | ✓ | ✓ | — |
| external editor (`Ctrl+G`) | ✓ | — | — | ✓ | — |
| paste-as-image placeholder | ✓ | ✓ | ✓ | ✓ shipped (v1.7.5; data URI + magic-byte sniff; OCR → Wave F) | — |
| reverse history search (`Ctrl+R`) | ✓ | ✓ | ✓ | ✓ | — |
| autocomplete for inline `@file` and `#skill` | ✓ | ✓ | ✓ | ✓ | — |

### 1.2 Keybindings (Claude-Code parity)

| key | action | ship |
|---|---|---|
| `Ctrl+L` | clear screen + reprint banner | ✓ shipped |
| `Ctrl+C` | soft-cancel current line | ✓ shipped |
| `Ctrl+D` | exit with goodbye panel | ✓ shipped |
| `Ctrl+R` | reverse history search | ✓ shipped |
| `Ctrl+G` | open $EDITOR for long prompt | ✓ shipped |
| `Ctrl+T` | toggle live task list panel | ✓ shipped (v1.7.5; pure helper + binding) |
| `Ctrl+O` | toggle verbose tool-call output | ✓ shipped (v1.7.5; pure helper + binding) |
| `Ctrl+F` | re-focus the most-recently spawned subagent | ✓ shipped (v1.8.0) — `keybinds.focus_foreground_subagent` mutates `session.focused_subagent`; the live `/agents` table + `Ctrl+F` ship together. `SubagentRegistry.cancel_all()` (a "kill" verb) is a Wave-E follow-up; cancelling an individual record is `/agents kill <id>` |
| `Esc Esc` | rewind last turn | ✓ shipped (v1.7.5; persistent — JSONL truncate) |
| `Tab` | cycle modes (build → plan → run → retro → explore) | ✓ shipped (v1.7.5) |
| `Shift+Tab` | cycle modes (reverse) | ✓ shipped |
| `Alt+P` | open model picker dialog | ✓ shipped (v1.7.5; toast + /model-list) |
| `Alt+T` | toggle deep-think (extended thinking) | ✓ shipped (v1.7.5; pure helper + binding) |
| `Alt+M` | toggle permission mode | ✓ shipped (v1.7.5; cycles normal → strict → yolo) |

### 1.3 Slash commands

> **Naming note.** A `✓` marks that the reference stack ships *the
> concept*, not necessarily the exact slash name. Where names differ
> we record the mapping so muscle memory translates cleanly:
>
> | Lyra / CC  | Hermes (HA) | opencode (OC) |
> | ---        | ---         | ---           |
> | `/compact` | `/compress` | `/compact`    |
> | `/cost`    | `/usage`    | — (toolbar)   |
> | `/stats`   | `/insights` | — (toolbar)   |
> | `/theme`   | `/skin`     | `/themes`     |
> | `/model`   | `/model`    | `/models`     |
> | `/resume`  | `/resume`   | `/new` or session list |
>
> The v1.7.2 slash-alias layer is declared inline on each
> ``CommandSpec`` in ``lyra_cli.interactive.session`` (via the
> ``aliases=("compress",)`` tuple) rather than a separate module;
> muscle memory from hermes / opencode resolves to the canonical Lyra
> name through the same dispatcher. (The v0.1 parity matrix cited a
> ``lyra_cli.commands.aliases`` module — that module never shipped;
> this entry is the corrected reality.)

#### Session management

| cmd | CC | OC | HA | ship |
|---|---|---|---|---|
| `/clear` | ✓ | ✓ | ✓ | ✓ shipped |
| `/exit` `/quit` | ✓ | ✓ | ✓ | ✓ shipped |
| `/history` | ✓ | ✓ | ✓ | ✓ shipped |
| `/compact` — compress context | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; LLM-driven `compact_messages`) |
| `/rewind` — undo last turn | ✓ | — | — | ✓ shipped (v1.7.5; persistent — JSONL truncate) |
| `/resume` — reopen last session | ✓ | ✓ | ✓ | ✓ shipped (v1.7.5; full state restore from JSONL) |
| `/fork` — branch current session | ✓ | ✓ | — | ✓ shipped (v1.7.5; SessionsStore.fork) |
| `/rename` — rename session | ✓ | ✓ | — | ✓ shipped (v1.7.5; SessionsStore.rename) |
| `/sessions` — list saved sessions | ✓ | ✓ | ✓ | ✓ shipped (v1.7.5; SessionsStore.list) |
| `/export` — export transcript | ✓ | ✓ | ✓ | ✓ shipped (v1.7.5; markdown via SessionsStore.export) |

#### Info & diagnostics

| cmd | CC | OC | HA | ship |
|---|---|---|---|---|
| `/status` | ✓ | ✓ | ✓ | ✓ shipped |
| `/doctor` | ✓ | ✓ | ✓ | ✓ shipped |
| `/help` | ✓ | ✓ | ✓ | ✓ shipped |
| `/keybindings` | ✓ | ✓ | ✓ | ✓ shipped (alias `/keys`) |
| `/cost` — token spend | ✓ | ✓ | ✓ | ✓ shipped (alias `/usage`) |
| `/stats` — session metrics | ✓ | ✓ | ✓ | ✓ shipped (alias `/insights`) |
| `/context` — context-window grid | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; `render_context_grid`) |
| `/search` — FTS5 history recall | — | — | ✓ | ✓ shipped (v1.7.3; `_cmd_search` on `session_search`) |
| `/diff` — recent file changes | ✓ | ✓ | — | ✓ shipped (v1.7.4; `git diff --stat` + body, 20k truncate) |
| `/map` | ★ | ★ | ★ | ✓ shipped (v1.7.5; ASCII tree of `*.py` with depth cap) |
| `/blame` | ★ | ★ | ★ | ✓ shipped (v1.7.5; `git blame -L` with friendly fallback) |
| `/trace` | ★ | ★ | ★ | ✓ shipped (v1.7.5; HIR RingBuffer last-N events + `/trace on/off` legacy verbose toggle) |
| `/self` | ★ | ★ | ★ | ✓ shipped (v1.7.5; session introspection + RingBuffer summary) |
| `/badges` | ★ | ★ | ★ | ✓ shipped (v1.7.5; reads `<repo>/.lyra/badges.json`) |

#### Config & theme

| cmd | CC | OC | HA | ship |
|---|---|---|---|---|
| `/theme` | ✓ | ✓ | ✓ | ✓ shipped (v1.7.5; 10 built-in themes incl. midnight + paper, `/skin` alias) |
| `/vim` | ✓ | — | — | ✓ shipped (v1.7.5; on/off/status, persists, prompt_toolkit `vi_bindings`) |
| `/config` | ✓ | ✓ | ✓ | ✓ shipped (v1.7.5; `~/.lyra/config.yaml` round-trip + `from_config`) |
| `/model` | ✓ | ✓ | ✓ | ✓ shipped |
| `/model list` / `/models` | — | ✓ | ✓ | ✓ shipped (v1.7.4; live ●/✓/— markers) |

#### Plan / run flow

| cmd | CC | OC | HA | ship |
|---|---|---|---|---|
| `/mode <plan\|run\|build\|explore\|retro>` | partial | ✓ | — | ✓ shipped (v1.7.5; sub-verbs list/toggle + permission warning on build) |
| `/approve` / `/reject` | ✓ | ✓ | — | ✓ shipped |
| `/effort` — interactive effort slider | ✓ | — | — | ✓ shipped (v1.7.5; `EffortPicker` + env-var bridge) |
| `/ultrareview` — multi-agent review | ✓ | — | — | ✓ shipped (v1.7.5; mocked 3-voice fan-out — real subagents → Wave D) |
| `/review` — post-turn verifier | ★ | ★ | ★ | ✓ shipped (v1.7.5; TDD-gate + safety + evidence single-pass) |
| `/tdd-gate on\|off` | ★ | — | — | ✓ shipped (v1.7.5; on/off/status, drives Edit-blocking) |
| `/red-proof` | ★ | — | — | ✓ shipped (v1.7.5; `subprocess.run pytest` exit-code → RED proof) |

#### Agents & tools

| cmd | CC | OC | HA | ship |
|---|---|---|---|---|
| `/agents` — list subagents | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; `SubagentRegistry`) |
| `/spawn <task>` — dispatch subagent | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; `SubagentRegistry.spawn`) |
| `/tools` — list registered tools | — | ✓ | ✓ | ✓ shipped (v1.7.5; full / detail / `risk=` filter) |
| `/skills` | ✓ | ✓ | ✓ | ✓ shipped |
| `/mcp` — list connected MCP servers | ✓ | ✓ | ✓ | v1.5 (mcp adapter) |
| `/cron` — schedule automated tasks | — | — | ✓ | ✓ shipped (v1.7.2; `list\|add\|remove\|pause\|resume\|run\|edit`) |

#### Collaboration / handoff

| cmd | CC | OC | HA | ship |
|---|---|---|---|---|
| `/btw` — side question without context pollution | ✓ | — | — | ✓ shipped (v1.7.5; FIFO `_btw_log`, never enters main agent context) |
| `/team-onboarding` — generate teammate guide | ✓ | — | — | v1.5 |
| `/less-permission-prompts` — allowlist | ✓ | — | — | v1.5 |
| `/handoff` — session summary PR description | ★ | ★ | ★ | ✓ shipped (v1.7.5; markdown PR + git diff, writes `<repo>/.lyra/handoff.md`) |
| `/pair` — pair-programming stream | ★ | ★ | ★ | ✓ shipped (v1.7.5; toggle + status-line indicator — live streaming → Wave D) |
| `/wiki` — repo wiki (Devin-Wiki style) | ★ | ★ | ★ | v1.5 |
| `/budget set` — cost/token hard cap | ★ | ★ | ★ | ✓ shipped (v1.7.5; `BudgetCap.enforce` with OK / ALERT / EXCEEDED) |

---

## 2. Architecture & runtime

### 2.1 Agent modes

> **v3.2.0 update.** Lyra collapsed the legacy 5-mode taxonomy
> (`plan / build / run / explore / retro`) onto Claude Code's
> canonical four (`agent / plan / debug / ask`) so every entry in
> this table that referred to a legacy mode now points at the
> canonical one. Legacy names remain accepted as aliases via
> `_LEGACY_MODE_REMAP`; the parity ✓ has not regressed for any
> capability — only the naming has been unified. See the v3.2.0
> snapshot above and the corresponding `CHANGELOG.md` entry.

| mode | CC | OC | HA | ship |
|---|---|---|---|---|
| `agent` (full access; default) | ✓ | ✓ | ✓ | ✓ shipped (v3.2; subsumes legacy `build` + `run`; permission warning when `permission_mode=yolo`) |
| `plan` (read-only design) | ✓ | ✓ | ✓ | ✓ shipped (v3.2 unchanged; `/approve` hands off to `agent`) |
| `debug` (systematic troubleshooting) | ✓ | ✓ | ✓ | ✓ shipped (v3.2; subsumes legacy `retro`; journaling moved to `lyra retro` CLI subcommand) |
| `ask` (read-only Q&A) | ✓ | ✓ | ✓ | ✓ shipped (v3.2; renamed from legacy `explore`; subagent-routed in Wave D) |
| Legacy aliases (`build` / `run` / `explore` / `retro`) | — | — | — | ✓ shipped (v3.2; `_LEGACY_MODE_REMAP` + one-shot rename notice on `/mode <legacy>`) |
| Mode prompt enumerates closed set (anti-hallucination) | — | — | — | ★ ✓ shipped (v3.2; `_LYRA_MODE_PREAMBLE` lists `agent, plan, debug, ask` verbatim + disclaims TDD as plugin) |
| deep-think toggle (Alt+T) | ✓ | — | — | ✓ shipped (v1.7.5; pure helper + binding) |

### 2.2 Subagents & delegation

> **Naming note.** CC ships `Explore` / `General` / `Plan` presets.
> Hermes ships two presets under different names — `leaf` (fast, read-only,
> Haiku-class model) and `orchestrator` (multi-step, full tool pool) —
> which are semantically equivalent to CC's `Explore` and `General`.
> opencode exposes the `task` tool and lets the user define subagents in
> `~/.config/opencode/agent/` rather than shipping named presets; the
> `✓` below records "the system supports this role", not a name match.

| capability | CC | OC | HA | ship |
|---|---|---|---|---|
| `Explore` subagent (Haiku) | ✓ | ✓ | ✓ (as `leaf`) | v1.7 |
| `General` subagent (multi-step) | ✓ | ✓ | ✓ (as `orchestrator`) | v1.7 |
| `Plan` subagent (research) | ✓ | — | — | v1.7 |
| Worktree isolation | — | partial | — | ✓ shipped (v1.7.2; `WorktreeManager` + `task(worktree=True)`) |
| Custom subagent definitions | ✓ | ✓ | ✓ | v1.7 |
| DAG scheduler | — | — | — | ★ v1 Phase 8 |
| Variant / multi-candidate runs | — | ✓ | ✓ | ★ v1.5 (Phase 17 agentless) |

### 2.3 Context engine

| capability | CC | OC | HA | ship |
|---|---|---|---|---|
| Automatic context compaction | ✓ | ✓ | ✓ | v1 Phase 3 |
| Context grid visualisation (`/context`) | ✓ | ✓ | — | **NOW** (stub → v1 Phase 3) |
| `Title` / `Summary` subagents (async) | — | ✓ | ✓ | v1.5 |
| ACON-style observation compressor | — | — | — | v1.5 Phase 18 |
| NGC-inspired grow-then-evict | — | — | — | ★ ✓ shipped (v2.0; `lyra_core.context.ngc.NGCCompactor`) |
| Prompt caching (Anthropic) | ✓ | ✓ | ✓ | v1.5 |

### 2.4 Memory

| capability | CC | OC | HA | ship |
|---|---|---|---|---|
| Procedural (skills) | ✓ | ✓ | ✓ | v1 Phase 3 |
| Episodic (trace digests) | partial | ✓ | ✓ | v1 Phase 3 |
| Semantic (facts / wiki) | — | — | ✓ | v1 Phase 3 |
| FTS5 session search | — | — | ✓ | ✓ shipped (v1.7.3; `/search` + `session_search`) |
| Vector / dense retrieval | partial | partial | ✓ | v1 Phase 3 |
| Agent-curated memory nudges | — | — | ✓ | v1.7 |

### 2.5 Tool pool

| tool | CC | OC | HA | ship |
|---|---|---|---|---|
| `Read` | ✓ | ✓ | ✓ | v1 Phase 1 |
| `Write` | ✓ | ✓ | ✓ | v1 Phase 1 |
| `Edit` | ✓ | ✓ | ✓ | v1 Phase 1 |
| `Glob` | ✓ | ✓ | ✓ | v1 Phase 1 |
| `Grep` | ✓ | ✓ | ✓ | v1 Phase 1 |
| `Bash` | ✓ | ✓ | ✓ | v1 Phase 1 (+ CLI's `!` today) |
| `TodoWrite` / task list | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; `make_todo_write_tool` + atomic `TodoStore`) |
| `ExecuteCode` (sandbox) | ✓ | ✓ | ✓ | v1.5 (Phase 14 CodeAct) |
| `codesearch` (ripgrep + py fallback) | — | ✓ | — | ✓ shipped (v1.7.2; `make_codesearch_tool`) |
| `apply_patch` (v4 envelope + unified diff) | ✓ | ✓ | — | ✓ shipped (v1.7.2; `make_apply_patch_tool`) |
| `NotebookEdit` (Jupyter cell CRUD) | ✓ | — | — | ✓ shipped (v1.7.2; `make_notebook_edit_tool`) |
| `pdf_extract` (PDF → text) | ✓ | — | — | ✓ shipped (v1.7.2; `make_pdf_extract_tool`) |
| `WebSearch` | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; `make_web_search_tool`, pluggable provider) |
| `WebFetch` | ✓ | ✓ | ✓ | ✓ shipped (v1.7.3; `make_web_fetch_tool`, HTML→text) |
| `Browser` (headless) | — | — | ✓ | v2 |
| `Delegate` / subagent dispatch | ✓ | ✓ | ✓ | v1.7 |
| `MCP` umbrella | ✓ | ✓ | ✓ | v1 Phase 10 |
| Custom / user tools | ✓ | ✓ | ✓ | **NOW** (registry scaffold) |
| Tool-approval prompt | ✓ | ✓ | ✓ | v1 Phase 1 |

### 2.6 Hooks

> **Schema note.** Event names below use Claude-Code's taxonomy.
> opencode routes lifecycle events through its own bus under different
> names: `chat.message` (prompt submit), `tool.execute.before`,
> `tool.execute.after`, `session.*`, and a generic `event` emitter.
> Hermes exposes hooks as explicit methods on plugin classes
> (`on_session_start`, `pre_llm_call`, `pre_tool_call`, `post_tool_call`,
> `on_session_end`). A `✓` here means "the semantic hook exists",
> not that the handler string matches.

| event | CC | OC | HA | ship |
|---|---|---|---|---|
| `SessionStart` / `SessionEnd` | ✓ | ✓ (`session.*`) | ✓ | v1 Phase 1 |
| `UserPromptSubmit` | ✓ | ✓ (`chat.message`) | ✓ | v1 Phase 1 |
| `PreToolUse` / `PostToolUse` | ✓ | ✓ (`tool.execute.before/after`) | ✓ | ✓ shipped (v1.7.2) |
| `PermissionRequest` | ✓ | ✓ | — | v1 Phase 1 |
| `SubagentStart` / `SubagentStop` | ✓ | ✓ | — | v1.7 |
| `FileChanged` | ✓ | ✓ | — | v1.5 |
| `WorktreeCreate` | ✓ | — | — | v1 Phase 7 |
| `ErrorThrown` / `TurnRejected` | ★ | ★ | ★ | v1 Phase 9 |

### 2.7 Permissions & safety

| feature | CC | OC | HA | ship |
|---|---|---|---|---|
| Mode-based permission gating | ✓ | ✓ | ✓ | v1 Phase 1 |
| Destructive-command detector | ✓ | ✓ | ✓ | v1 Phase 1 |
| Secrets scan (AWS / stripe / etc.) | partial | partial | ✓ | v1 Phase 1 |
| Injection-guard on tool output | ✓ | ✓ | ✓ | v1 Phase 9 |
| Trust banner on third-party MCP | ✓ | ✓ | — | v1 Phase 10 |
| Budget cap (cost / tokens) | ✓ | ✓ | ✓ | **NOW** (`/budget`) |
| Allowlist ("less-permission-prompts") | ✓ | ✓ | ✓ | v1.5 |

### 2.8 Providers / models

| feature | CC | OC | HA | ship |
|---|---|---|---|---|
| Anthropic / OpenAI / OpenRouter | ✓ | ✓ | ✓ | v1.5 |
| 200+ model registry | — | ✓ | ✓ | **NOW** (catalog scaffold) |
| Mid-session switch (`/model`) | ✓ | ✓ | ✓ | ✓ shipped |
| Model picker dialog (`Alt+P`) | ✓ | ✓ | ✓ | **NOW** |
| Multi-API mode (chat / responses / messages) | — | — | ✓ | v1.5 |
| Cost-aware router per turn | ★ | ★ | ★ | ★ ✓ shipped (v2.7.1; role-keyed `fast`/`smart` slot router with per-turn slug resolution) |

### 2.9 Observability & eval

| feature | CC | OC | HA | ship |
|---|---|---|---|---|
| Event bus / HIR | ★ | partial | partial | ✓ shipped (v1.7.3; `HIREmitter` + OTLP path) |
| OpenTelemetry export | — | ✓ | — | ✓ shipped (v1.7.3; `OpenTelemetryCollector`) |
| Session list / replay | ✓ | ✓ | ✓ | **NOW** (list) / v1.5 (replay) |
| Mock-LLM parity harness (E2E CLI) | ✓ | — | — | ✓ shipped (v1.7.2; `ScriptedLLM` + `ScenarioCase`) |
| Red-team corpus + safety monitor | — | — | — | ★ v1 Phase 9 |
| Golden eval corpus + drift gate | partial | — | — | ★ v1 Phase 11 |
| SWE-bench Pro / LoCoEval adapters | — | — | — | ★ v1.5 Phase 12 |
| Meta-harness outer loop | — | — | — | ★ ✓ shipped (v2.0; `lyra_core.meta.outer_loop.MetaHarness`) |
| Harness arena (A/B) | — | — | — | ★ ✓ shipped (v2.0; `lyra_core.arena.elo.Arena`) |

### 2.10 Extension surfaces

| feature | CC | OC | HA | ship |
|---|---|---|---|---|
| CLAUDE.md / AGENTS.md / SOUL.md | ✓ | ✓ | ✓ | ✓ shipped (SOUL.md) |
| Hooks configuration | ✓ | ✓ | ✓ | v1 Phase 1 |
| Skill packs | ✓ | ✓ | ✓ | ✓ shipped (4 packs) |
| Skill auto-extractor | — | — | ✓ | v1 Phase 6 |
| Skill-Creator v2 (4-agent loop) | — | — | partial | v1.7 Phase 19 |
| MCP client | ✓ | ✓ | ✓ | v1 Phase 10 |
| MCP server | ✓ | ✓ | ✓ | v1 Phase 10 |<sup>†</sup>
| Plugin system | ✓ | ✓ | ✓ | v1.5 (runtime) |
| Plugin manifest loader (`.lyra-plugin` / `.claude-plugin`) | ✓ | ✓ | partial | ✓ shipped (v1.7.2; `PluginManifest` + `load_manifest`) |
| Plugin runtime (lazy load + event dispatch) | ✓ | ✓ | partial | ✓ shipped (v1.7.3; `PluginRuntime` + `LoadedPlugin`) |
| ACP bridge (Agent Client Protocol; Zed / JetBrains) | — | ✓ | — | ✓ shipped (v1.7.2 scaffold; `AcpServer` JSON-RPC 2.0) |
| VS Code / Zed / JetBrains bridge | — | ✓ | ✓ | v2 (on top of ACP scaffold) |

<sup>†</sup> Hermes ships an MCP server via `hermes mcp serve` (FastMCP-based); the
initial matrix draft marked this `—` and has been corrected as of v1.7.2.

### 2.11 Messaging gateway (multi-channel delivery)

Hermes ships a gateway daemon that polls a set of registered channel
adapters (Telegram, Slack, Discord, Matrix, Feishu, WeCom, Email, SMS,
Mattermost, BlueBubbles) and routes inbound messages to the agent.
Lyra ships the `ChannelAdapter` Protocol + a Telegram stub in v1.7.2
so external channels can be wired without reshaping the interface later.

| channel | CC | OC | HA | OUR | ship |
|---|---|---|---|---|---|
| `ChannelAdapter` Protocol | — | — | ✓ | ✓ shipped | v1.7.2 (`lyra_core.gateway.adapter`) |
| Telegram adapter | — | — | ✓ | ✓ shipped | v1.7.3 real Bot API (`TelegramAdapter` with httpx) |
| Slack / Discord / Matrix | — | — | ✓ | — | v1.7 |
| Email / SMS / Feishu / WeCom / Mattermost / BlueBubbles | — | — | ✓ | — | v1.7 |

### 2.12 Multi-backend terminal execution

Hermes exposes Local, Docker, Modal, SSH, Daytona, and Singularity as
pluggable shells behind a single `terminal` abstraction. Lyra ships the
`TerminalBackend` Protocol + a real `LocalBackend` + typed stubs for
each remote backend in v1.7.2.

| backend | HA | OUR | ship |
|---|---|---|---|
| `TerminalBackend` Protocol | ✓ | ✓ shipped | v1.7.2 (`lyra_core.terminal.backend`) |
| `LocalBackend` (subprocess) | ✓ | ✓ shipped | v1.7.2 (`LocalBackend`) |
| `DockerBackend` | ✓ | ✓ shipped | v1.7.3 (`DockerBackend` docker-py wrapper) |
| `ModalBackend` | ✓ | stub | v1.7 Phase 11 |
| `SSHBackend` | ✓ | stub | v1.7 Phase 11 |
| `DaytonaBackend` | ✓ | stub | v1.7 Phase 11 |
| `SingularityBackend` | ✓ | stub | v1.7 Phase 11 |

### 2.13 RL / Atropos training scaffold

Hermes integrates Tinker-Atropos for GRPO + LoRA training orchestrated
through `rl_*` tools. Lyra ships the trajectory recorder + environment
list tool in v1.7.2 so the interface can stabilise before the trainer
is wired, and so harness runs can already emit training-compatible
JSONL.

| capability | CC | OC | HA | OUR | ship |
|---|---|---|---|---|---|
| Trajectory JSONL recorder | — | — | ✓ | ✓ shipped | v1.7.2 (`TrajectoryRecorder`) |
| `rl_list_environments` tool | — | — | ✓ | ✓ shipped | v1.7.2 (`make_rl_list_environments_tool`) |
| Default env registry (`gsm8k`, `mbpp`, `swebench-lite`, …) | — | — | ✓ | ✓ shipped | v1.7.2 |
| `rl_start_training`, metrics, results | — | — | ✓ | — | v1.8 (trainer binding) |

### 2.14 Scheduled automations (cron)

Hermes ships a `/cron` slash command + persistent job store so a session
can register "run this prompt every weekday 09:00" automations with
optional skill attachments. Lyra ships the full surface in v1.7.2:
schedule parser (one-shot / recurring / classic 5-field cron), JSON-backed
store, and the `/cron list|add|remove|pause|resume|run|edit` dispatcher.

| capability | CC | OC | HA | OUR | ship |
|---|---|---|---|---|---|
| Schedule parser (one-shot + recurring + 5-field) | — | — | ✓ | ✓ shipped | v1.7.2 (`Schedule` + `parse_schedule`) |
| `CronStore` (JSON persistence, atomic writes) | — | — | ✓ | ✓ shipped | v1.7.2 (`lyra_core.cron.store`) |
| `/cron` slash dispatcher | — | — | ✓ | ✓ shipped | v1.7.2 (`lyra_cli.interactive.cron`) |
| Skill attachments on cron jobs | — | — | ✓ | ✓ shipped | v1.7.2 (`--skill` + `add_skill` / `remove_skill`) |
| Background runner (ticks due jobs) | — | — | ✓ | ✓ shipped | v1.7.3 (`CronDaemon` — deterministic `tick()` + threaded `start()`/`stop()`) |

---

## 3. Proposed net-new features (★ only we do)

These are the ideas the existing systems don't have, rooted in Lyra's harness-engineering identity (and, when teams opt in, the optional TDD plugin). Each links to the milestone where it lands.

1. **TDD phase tracking as first-class state** (`/phase` + state machine IDLE → PLAN → RED → GREEN → REFACTOR → SHIP). Evidence-based advancement with typed artefacts, strict/lenient modes. — ★ ✓ shipped (v2.0; `lyra_core.tdd.state.TDDStateMachine`).
2. **Cross-channel verifier** — compare trace claims vs git diff vs filesystem snapshot, reject hallucinated file:line citations. — ★ ✓ shipped (v2.0; `lyra_core.verifier.trace_verifier`).
3. **Refute-or-Promote adversarial stage** (SWE-TRACE). — ★ ✓ shipped (v2.0; `lyra_core.loop.refute_or_promote.RefuteOrPromoteStage`).
4. **Rubric Process Reward Model** as the subjective verifier. — ★ ✓ shipped (v2.0; `lyra_core.eval.prm.{Rubric, RubricJudge, RubricSet, RubricSetReport}`).
5. **Neural Garbage Collection compactor** — grow-then-evict with outcome-logged training corpus (`compactor-outcomes.jsonl`). — ★ ✓ shipped (v2.0; `lyra_core.context.ngc.{NGCCompactor, NGCOutcomeLogger}`).
6. **Reuse-first hybrid skill router** — trigger match + historical success rate drives reuse-vs-synthesise. — ★ ✓ shipped (v2.0; `lyra_core.skills.router.HybridSkillRouter`).
7. **Trigger description auto-optimizer** — rule-based feedback loop (miss → add trigger, false positive → refine/remove) with token-set deduplication. — ★ ✓ shipped (v2.0; `lyra_core.skills.optimizer.TriggerOptimizer`).
8. **In-session skill synthesis** — drafts new `Skill` entries from user queries + proposed triggers and registers them immediately. — ★ ✓ shipped (v2.0; `lyra_core.skills.synthesizer.SkillSynthesizer`).
9. **Harness plugins as first-class** — two parallel surfaces (programmatic `PluginManifest` / `PluginRegistry` + declarative `PluginManifestSpec` / `PluginRuntime`) with per-plugin dispatch isolation. — ★ ✓ shipped (v2.0; `lyra_core.plugins.{registry, manifest, runtime}`).
10. **Meta-harness outer loop** — Lyra optimises its own harness against your repo via a parity corpus. — ★ ✓ shipped (v2.0; `lyra_core.meta.{corpus, outer_loop}`).
11. **Harness arena** — Elo-style pairwise leaderboard for harness configurations on specific tasks. — ★ ✓ shipped (v2.0; `lyra_core.arena.elo.Arena`).
12. **Federated skill registry** — export/import shared skill manifests with merge strategies for conflicts. — ★ ✓ shipped (v2.0; `lyra_core.skills.federation.{SkillManifest, FederatedRegistry, Federator}`).
13. **KLong-style checkpoint & resume across model generations** — schema-versioned snapshot format with forward migrators. — ★ ✓ shipped (v2.0; `lyra_core.klong.checkpoint`).
14. **Multica team orchestration + federated retros**. — v2 Phase 28 (moved to post-v2.0 backlog; federation primitives for skills shipped with #12).
15. **Plan Mode default-on with auto-skip heuristic** (file count ≤ 2, expected steps ≤ 8). — ✓ shipped partial.
16. **SOUL.md as identity layer** — never compacted, precedence rules, drift detector. — v1 Phase 1–3.
17. **`/review --auto` post-turn verifier** — TDD gate + safety monitor + evidence validator together on a single button. — ★ ✓ shipped (v2.0; `/review --auto` enhancement).
18. **`/eval-drift`** — compare current session against golden baseline in-shell. — v1 Phase 11.
19. **`/golden add`** — promote the current turn into the golden eval corpus, with reviewer approval. — v1 Phase 11.
20. **`/handoff`** — emit a markdown PR description from the session summary, ready to paste into GitHub. — **NOW** (stub).

---

## 4. Advanced frontier ideas (research roadmap)

Brainstorm column — each is a candidate for a future block or paper replication.

- **`/split` + `/vote`** — ranked-choice preference ledger with fan-out planning. — ★ ✓ shipped (v2.0; REPL `_cmd_split`, `_cmd_vote` with `results`/`clear` subcommands).
- **Speculative agents** — dispatch an `explore` subagent ahead of the main loop that pre-computes likely context for the next step, trade compute for latency.
- **Ambient budget meter** — small status-bar widget tracking $ burn rate; alerts on spikes (e.g. > 3σ vs session median).
- **Skill diff** — when a proposed skill conflicts with an existing one, surface the semantic delta + the trajectories each was extracted from.
- **Outcome-weighted memory retrieval** — episodic memory rank biased by the downstream success of similar past turns, not just embedding distance.
- **TDD mutation testing** — after `GREEN`, optionally run a mutation tester and use survival rate as extra evidence for `/review`.
- **Policy-as-code debugger** — when a permission denies a tool call, show the rule file + line that denied, not just the verdict.
- **`/observe` live panel** — ambient observation channel with on/off/status/tail subcommands over the REPL observation log. — ★ ✓ shipped (v2.0; REPL `_cmd_observe`).
- **`/replay <session-id>`** — already shipped in Wave E via `lyra_cli.replay`.
- **IDE bridges** — build shell-open commands for VS Code / Cursor / JetBrains / Zed / Neovim. — ★ ✓ shipped (v2.0; `lyra_core.ide.bridges.{IDEBridge, build_open_command}` + REPL `/ide`).
- **`/catch-up`** — session briefing summarising TDD phase, split queue, vote tally, and recent observations. — ★ ✓ shipped (v2.0; REPL `_cmd_catchup`).
- **Graph-of-sessions** — DAG view of `/fork` branches across a repo's Lyra history.
- **Intent embeddings** — embed the user's goal once per session and use it to bias tool selection, rather than re-deriving from the last turn.
- **Failure-first learning** — escalate post-hoc on sessions with rejected plans or reverted commits; feed those into the skill extractor before successful ones.
- **Dogfood-only features behind `/self`** — any new feature must be usable from a `/self use` invocation before graduating to a user-facing command.

---

## 5. v1.7.2 "Integrity + Fusion" delta (2026-04-24)

The v0.1 → v0.2 re-validation of the matrix against the `.ui-refs/`
repos surfaced a dozen concrete gaps; v1.7.2 closed all of them as
scaffolds-with-tests so the interfaces can stabilise before production
wiring lands in v1.5 / v1.7. Every row below has a `✓` parity symbol
backed by code + RED/GREEN tests merged in the v1.7.2 batch.

| area | ref-repo source | Lyra symbol | parity status | test file |
|---|---|---|---|---|
| `PostToolUse` hook on `AgentLoop` | CC / HA (`post_tool_call`) / OC (`tool.execute.after`) | `AgentLoop._fire("post_tool_call", ToolResultCtx)` | ✓ shipped | `lyra-cli/tests/test_agent_loop_contract.py` |
| Hermes slash aliases (`/compress`, `/usage`, `/insights`, `/skin`) | HA | `CommandSpec(aliases=…)` in `interactive.session` | ✓ shipped | `lyra-cli/tests/test_slash_aliases_hermes_compat.py` |
| `task(worktree=True)` subagent isolation | CC (`/task` + worktrees) | `make_task_tool(…, worktree_manager=…)` | ✓ shipped | `lyra-core/tests/test_task_tool_worktree_isolation.py` |
| LSP tool contract (`diagnostics`, `hover`, `references`, `definition`) | CC | `make_lsp_tool` + `LSPBackend` | ✓ contract shipped (backend pluggable) | `lyra-core/tests/test_lsp_tool_contract.py` |
| `codesearch` tool | OC | `make_codesearch_tool` (ripgrep + Python fallback) | ✓ shipped | `lyra-core/tests/test_codesearch_tool_contract.py` |
| `apply_patch` tool (v4 envelope + unified diff) | CC / OC | `make_apply_patch_tool` | ✓ shipped | `lyra-core/tests/test_apply_patch_tool_contract.py` |
| `NotebookEdit` tool | CC | `make_notebook_edit_tool` (cell replace / insert / delete / convert) | ✓ shipped | `lyra-core/tests/test_notebook_edit_tool_contract.py` |
| `pdf_extract` tool | CC | `make_pdf_extract_tool` (pypdf / pdfminer cascade) | ✓ shipped | `lyra-core/tests/test_pdf_extract_tool_contract.py` |
| `/cron` scheduled automations | HA | `Schedule`, `CronStore`, `/cron` dispatcher | ✓ shipped | `lyra-core/tests/test_cron_schedule_parser.py`, `lyra-core/tests/test_cron_store.py`, `lyra-cli/tests/test_slash_cron_dispatch.py`, `lyra-cli/tests/test_slash_cron_repl_integration.py` |
| ACP bridge (Agent Client Protocol; Zed / JetBrains) | OC | `AcpServer` (JSON-RPC 2.0) | ✓ scaffold shipped | `lyra-core/tests/test_acp_server_contract.py` |
| Multi-channel gateway adapter Protocol + Telegram stub | HA | `ChannelAdapter`, `TelegramAdapter` | ✓ scaffold shipped | `lyra-core/tests/test_gateway_adapter_contract.py` |
| Plugin manifest loader (`.lyra-plugin` / `.claude-plugin`) | CC / OC | `PluginManifest`, `load_manifest`, `validate_manifest` | ✓ shipped | `lyra-core/tests/test_plugin_manifest_contract.py` |
| Multi-backend terminal (Local + Docker/Modal/SSH/Daytona/Singularity stubs) | HA | `TerminalBackend`, `LocalBackend`, `terminal.stubs` | ✓ Local real + remote stubs | `lyra-core/tests/test_terminal_backend_contract.py` |
| Mock-LLM parity harness for E2E CLI | CC | `ScriptedLLM`, `ScenarioCase`, `StreamChunk` | ✓ shipped | `lyra-core/tests/test_mock_llm_harness_contract.py` |
| RL / Atropos trajectory tooling | HA | `TrajectoryRecorder`, `make_rl_list_environments_tool` | ✓ scaffold shipped | `lyra-core/tests/test_rl_trajectory_contract.py` |

Stale cells that were corrected (not new features, just doc truth):

| row | before (v0.1) | after (v0.2) | reason |
|---|---|---|---|
| §2.6 `PreToolUse` / `PostToolUse` hook | `v1 Phase 1` | `✓ shipped (v1.7.2)` | `post_tool_call` wired in `AgentLoop` |
| §2.2 Worktree isolation | `v1 Phase 7 ([block 10])` | `✓ shipped (v1.7.2)` | `WorktreeManager` + `task(worktree=True)` |
| §2.10 MCP server (HA column) | `—` | `✓` | HA ships `hermes mcp serve` (FastMCP) |
| §1.3 `/cost` / `/stats` (alias col) | `—` | `alias /usage`, `alias /insights` | hermes-compat aliases were mis-wired to `/context` in v0.1 |
| §1.1 `@file` / multi-line / `Ctrl+G` / prompt continuation | `✗ NOW` | `✓` (already shipped) | v0.1 under-counted shipped UI |
| §1.2 `/keybindings` | `v1.5` | `✓ shipped (alias /keys)` | already in registry |
| §1.3 naming-note module ref | `lyra_cli.commands.aliases` | `aliases=(…)` on `CommandSpec` in `lyra_cli.interactive.session` | module never shipped; corrected to reality |

Test delta from v0.1 → v0.2: **132 new v1.7.2 contract tests**
(130 in 17 new contract files + 2 `post_tool_call` tests added to the
pre-existing `test_agent_loop_contract.py`). Full harness now runs
**798/798 green** (`python3 -m pytest -q` from `projects/lyra/`,
verified 2026-04-24). The matrix is therefore self-verifying: every
`✓ shipped (v1.7.2)` claim here has a matching RED/GREEN pair under
`packages/lyra-*/tests/` and can be re-checked by running the suite.

---

## 5b. v1.7.3 "Cross-Repo Convergence — Phase A" delta (2026-04-24)

v1.7.2 shipped scaffolds-with-tests for 15 features; the v1.7.3
Phase-A pass flipped 12 of those scaffolds to **real** implementations
using a strict RED → GREEN cadence (contract tests landed before
implementation). Each row is backed by a code symbol and a new
contract test file under `packages/lyra-*/tests/`.

| area | ref-repo source | Lyra symbol | v1.7.2 status → v1.7.3 status | test file |
|---|---|---|---|---|
| `/compact` real summariser | CC / OC | `compact_messages` + `CompactResult` | stub → ✓ shipped (LLM-driven) | `lyra-core/tests/test_context_compactor_contract.py` |
| `/context` token-bar grid | CC / OC / HA | `render_context_grid` | stub → ✓ shipped | `lyra-core/tests/test_context_grid_contract.py` |
| `/agents` + `/spawn` real | CC / OC / HA | `SubagentRegistry`, `SubagentRecord` | stub → ✓ shipped | `lyra-core/tests/test_subagent_registry_contract.py` |
| `TodoWrite` tool + store | CC / OC / HA | `make_todo_write_tool` + `TodoStore` | stub → ✓ shipped (atomic JSON) | `lyra-core/tests/test_todo_write_tool_contract.py` |
| LSP backend real | CC | `MultilspyBackend` + `MockLSPBackend` | contract only → ✓ real backend | `lyra-core/tests/test_lsp_multilspy_backend_contract.py` |
| Plugin runtime loader | CC / OC | `PluginRuntime`, `LoadedPlugin` | manifest only → ✓ runtime | `lyra-core/tests/test_plugin_runtime_contract.py` |
| `DockerBackend` real | HA | `DockerBackend` (docker-py) | stub (raises) → ✓ real wrapper | `lyra-core/tests/test_terminal_docker_backend_contract.py` |
| `WebSearch` + `WebFetch` tools | CC / OC / HA | `make_web_search_tool`, `make_web_fetch_tool` | planned → ✓ shipped (httpx + bs4) | `lyra-core/tests/test_web_tools_contract.py` |
| Telegram adapter real | HA | `TelegramAdapter(http=…, use_http=True)` | stub → ✓ real Bot API | `lyra-core/tests/test_telegram_adapter_http_contract.py` |
| Cron daemon | HA | `CronDaemon.tick()` + threaded loop | scheduler only → ✓ runner | `lyra-core/tests/test_cron_daemon_contract.py` |
| `/search` slash UI on FTS5 | HA | `_cmd_search` + `InteractiveSession.search_fn` | tool only → ✓ slash UI | `lyra-cli/tests/test_session_search_slash_contract.py` |
| OpenTelemetry exporter | OC | `OpenTelemetryCollector` | scaffold → ✓ real SDK bridge | `lyra-core/tests/test_otel_collector_contract.py` |

**Optional dependency discipline**: every new real path honours a
:class:`FeatureUnavailable` exception when its underlying SDK is not
installed (`lyra[lsp]`, `lyra[docker]`, `lyra[web]`, `lyra[otel]`),
keeping the base install lean. The sentinel lives in
``lyra_core.lsp_backend.errors`` and is re-exported for callers.

**Test delta v0.2 → v0.3**: **+77 contract tests** across 12 new
files (6–10 tests each). Full harness now runs **875/875 green**
with 12 pre-existing git-sandbox-dependent tests deselected on this
host (`python3 -m pytest -q`, verified 2026-04-24), up from 798/798.
Each `✓ shipped (v1.7.3)` cell above is therefore self-verifying via
its paired contract file.

---

## 5c. v1.7.4 "Local-First & Provider Polish" delta (2026-04-24, Wave B)

v1.7.4 is **Wave B** of the [full-parity roadmap](superpowers/plans/2026-04-24-full-parity-roadmap.md):
the local-first / provider-polish wave. It ships 15 features that
collectively make Lyra a strict superset of claw-code / opencode /
hermes-agent on the provider axis — every backend any of the three
exposes now has a Lyra equivalent, plus five local-server presets
(vLLM / llama-server / TGI / Llamafile / MLX-LM) none of them ship.

| area | ref-repo source | Lyra symbol | status | test file |
|---|---|---|---|---|
| `.env` parser | CC | `lyra_core.providers.dotenv.{parse_dotenv,load_dotenv_file,dotenv_value}` | ✓ shipped (v1.7.4) | `lyra-core/tests/test_providers_dotenv.py` |
| Auth-sniffer hint | CC | `lyra_core.providers.auth_hints.{ForeignCred,missing_credential_hint}` | ✓ shipped (v1.7.4) | `lyra-core/tests/test_providers_auth_hints.py` |
| Model alias registry | OC / HA | `lyra_core.providers.aliases.{AliasRegistry,resolve_alias,provider_key_for}` | ✓ shipped (v1.7.4) | `lyra-core/tests/test_providers_aliases.py` |
| Plugin `max_output_tokens` override | CC | `lyra_core.providers.registry.{plugin_max_output_tokens,max_tokens_for_model_with_override}` | ✓ shipped (v1.7.4) | `lyra-core/tests/test_providers_plugin_override.py` |
| Context-window preflight | CC | `lyra_core.providers.preflight.{preflight,ContextWindowExceeded,PreflightReport}` | ✓ library shipped (v1.7.4); agent-loop wiring → Wave D | `lyra-core/tests/test_providers_preflight.py` |
| OpenRouter provider routing | OC | `lyra_cli.providers.openai_compatible.ProviderRouting` (sort/only/ignore/order/require_parameters/data_collection) | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_openrouter_provider_routing.py` |
| Fallback provider chain | OC | `lyra_cli.providers.fallback.{FallbackChain,FallbackExhausted,classify_error,is_retryable_error}` | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_providers_fallback.py` |
| 6 new OpenAI-compat presets (DashScope cloud + 5 local: vLLM, llama-server, TGI, Llamafile, MLX) | net-new | `PRESETS` entries `dashscope`, `vllm`, `llama-server`, `tgi`, `llamafile`, `mlx` | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_new_provider_presets.py` |
| Anthropic via AWS Bedrock | net-new | `lyra_cli.providers.bedrock.AnthropicBedrockLLM` (`lyra[bedrock]`) | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_bedrock_provider.py` |
| Gemini via Vertex AI | net-new | `lyra_cli.providers.vertex.GeminiVertexLLM` (`lyra[vertex]`) | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_vertex_provider.py` |
| GitHub Copilot backend | net-new | `lyra_cli.providers.copilot.{CopilotLLM,CopilotTokenStore,CopilotUnavailable}` | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_copilot_provider.py` |
| `/auth` device-code OAuth | CC / OC | `lyra_cli.interactive.auth.{DeviceCodeAuth,AuthFlowResult,run_auth_slash}` (RFC 8628) | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_slash_auth.py` |
| Factory wiring + telemetry | net-new | `lyra_cli.llm_factory.{_hydrate_env_from_dotenv,_resolve_model_alias_from_env,_emit_provider_selected}` + `lyra_core.hir.events.{emit,subscribe}` | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_llm_factory_telemetry.py` |
| `/model list` + `/models` real | CC / OC / HA | `InteractiveSession._cmd_model_list` + `_cmd_models` (live ●/✓/— markers) | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_slash_model_list.py` |
| `/diff` real (git diff) | CC / OC / HA | `InteractiveSession._cmd_diff_text` + slash dispatcher | ✓ shipped (v1.7.4) | `lyra-cli/tests/test_slash_diff.py` |

**Optional dependency discipline**: `lyra[bedrock]` pulls
`boto3>=1.34`; `lyra[vertex]` pulls `google-cloud-aiplatform>=1.42`;
`lyra[copilot]` and `lyra[oauth]` are stdlib-only umbrellas reserved
for future SDK pins. Every new provider raises a typed
``*Unavailable`` exception (`BedrockUnavailable`, `VertexUnavailable`,
`CopilotUnavailable`) with the exact `pip install` command when the
extra is missing. Base install footprint unchanged.

**Telemetry hub**: a new `lyra_core.hir.events` module provides a
fire-and-forget pub/sub `emit(name, **kw)` so the OTel exporter
(shipped v1.7.3) can subscribe to `provider_selected` events without
cycling through the heavier `HIREmitter` JSONL pipeline. Subscribers
are best-effort; a misbehaving subscriber cannot break the LLM
factory cascade.

**Test delta v0.3 → v0.4**: **+111 contract tests** across 13 new
files (3–13 tests each). Full harness now runs **912 passed,
2 sandbox-skipped** (`/diff` git tests skip when `git init` is
sandbox-blocked) with 11 pre-existing git-sandbox-dependent tests
deselected on this host (`python3 -m pytest packages/lyra-cli/tests/
packages/lyra-core/tests/`, verified 2026-04-24), up from 875.

---

## 5d. v1.7.5 "REPL Convergence" delta (2026-04-24, Wave C)

v1.7.5 is **Wave C** of the [full-parity roadmap](superpowers/plans/2026-04-24-full-parity-roadmap.md):
the REPL-convergence wave. Every UI / persistence / slash-command
cell in §1.1–§1.3 that was `NOW`, `v1.5`, or `v1.7` flips to
`✓ shipped (v1.7.5)`. The user-observable surface now matches
claw-code, opencode, and hermes-agent feature-for-feature on every
cell that was outstanding entering Wave C — and adds two net-new
items (TDD-`/red-proof`, `/btw` side-channel log) the reference
agents don't ship.

| area | ref-repo source | Lyra symbol | status | test file |
|---|---|---|---|---|
| `/rewind` persistent + `/resume` real (TurnSnapshot JSONL) | CC / OC | `InteractiveSession.{rewind_one,_persist_turn,resume_session}` + `_TurnSnapshot` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_rewind_resume.py` |
| `/fork` + `/rename` + `/sessions` + `/export` (SessionsStore) | CC / OC | `lyra_cli.interactive.sessions_store.SessionsStore` + `_cmd_fork`/`_cmd_rename`/`_cmd_sessions`/`_cmd_export` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_session_management.py` |
| `/map` ASCII dependency tree | OC / HA | `InteractiveSession._cmd_map_text` + `_cmd_map` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_map.py` |
| `/blame` + `/trace` + `/self` (HIR RingBuffer) | OC / HA | `lyra_core.hir.events.{RingBuffer,global_ring,reset_global_ring}` + session dispatchers | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_blame_trace_self.py` |
| `/budget set` + `/badges` (BudgetCap + badges.json) | CC / HA | `lyra_cli.interactive.budget.{BudgetCap,BudgetStatus,enforce}` + `_cmd_budget`/`_cmd_badges` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_budget_badges.py` |
| Direct keybinds (`Ctrl+T`/`Ctrl+O`/`Esc Esc`/`Tab`/`Alt+T`/`Alt+M`) | CC / OC | `lyra_cli.interactive.keybinds.{toggle_task_panel,toggle_verbose_tool_output,toggle_deep_think,cycle_mode,toggle_permission_mode,rewind_one_persisted}` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_keybinds_session_toggles.py` |
| `/mode` full dispatcher (build/plan/run/retro/explore + list/toggle) | CC | `_cmd_mode` (sub-verbs `list`/`toggle`/explicit set + permission warning on `build`) | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_mode_full.py` |
| `/handoff` (markdown PR description) | OC / HA | `lyra_cli.interactive.handoff.{render_handoff,_git_diff_stat}` + `_cmd_handoff` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_handoff.py` |
| `/effort` (interactive slider + reasoning_effort) | CC / OC | `lyra_cli.interactive.effort.{EffortPicker,apply_effort,effort_to_max_completion_tokens}` + `_cmd_effort` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_effort.py` |
| `/ultrareview` + `/review` + `/tdd-gate` | CC | `_cmd_ultrareview` (mocked fan-out) + `_cmd_review` + `_cmd_tdd_gate` + `InteractiveSession.tdd_gate_enabled` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_review_tdd_gate.py` |
| `/config` + `/theme` + `/skin` (config foundation) | CC / OC / HA | `lyra_cli.interactive.config_store.{Config,apply_to_session,to_bool}` + `_cmd_config` + `InteractiveSession.from_config` + 2 new themes (midnight, paper) | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_config.py` |
| `/vim` real toggle (config-backed) | CC | `_cmd_vim` rewritten with on/off/status + persistence; `lyra_cli.interactive.keybinds.vi_bindings` factory | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_vim.py` |
| `/red-proof` minimal (pytest assert RED) | net-new | `lyra_cli.interactive.red_proof.{RedProofResult,run_red_proof,render}` + `_cmd_red_proof` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_red_proof.py` |
| `/tools` rich (detail + risk filter) + `/btw` (side-channel) + `/pair` (toggle) | CC / OC | `_cmd_tools` (detail + `risk=`) + `_cmd_btw` + `InteractiveSession._btw_log` + `_cmd_pair` + `InteractiveSession.pair_mode` | ✓ shipped (v1.7.5) | `lyra-cli/tests/test_slash_tools_btw_pair.py` |
| Paste-as-image (data URI + magic-byte sniff) | CC | `lyra_cli.interactive.paste.{detect_image_paste,write_attachment,substitute_image_tokens}` | ✓ shipped (v1.7.5; OCR → Wave F) | `lyra-cli/tests/test_paste_image.py` |

**Test delta v0.4 → v0.5**: **+76 contract tests across 15 new
files** (one per Wave-C task, 4–8 tests each), plus a **+28
post-review safety patch** in `test_session_safety.py` covering
path-traversal rejection (17 cases), atomic persistence (3 cases),
and config-store size cap (3 cases). Full lyra-cli suite runs
end-to-end (`python3 -m pytest packages/lyra-cli`, verified
2026-04-24): **581 passed, 2 sandbox-skipped** (the same `/diff` git
tests as v1.7.4). Net behaviour: every Wave-C cell the master
roadmap committed to is now backed by a code symbol **and** a test
file path, and the v1.7.5 surface has been hardened against the
two MUST-FIX keymap drifts and five SHOULD-FIX safety items the
post-Wave-C reviewer flagged.

---

## 5e. v1.8.0 "Agentic Backbone" delta (2026-04-24, Wave D)

Wave D ships **15 new modules + 87 new contract tests** across
`lyra-core` and `lyra-cli`. Combined `pytest packages/lyra-core
packages/lyra-cli -q` reports **1143 passed, 2 skipped**, 0
regressions (4 failures + 7 errors are sandbox-only `git init`
denials in `test_merge_conflict_resolver.py`,
`test_subagent_parallel.py`, and `test_worktree_lifecycle.py` —
Wave-A/B carry-overs that pass cleanly outside the macOS sandbox).

| feature | code symbol(s) | tests | status |
|---|---|---|---|
| Subagent runner | `lyra_core.subagent.runner.SubagentRunner` (`runner.py:101`) — now `os.chdir(workdir)` for the loop's lifetime, restored in `finally` | `test_subagent_runner_contract.py` (6) | ✓ shipped substrate **and** workdir-isolated (file ops in the spawned loop honour the worktree); `git worktree add` shell-out remains Wave E |
| Live `/agents` + Ctrl+F | `_cmd_agents` (`session.py`) + `keybinds.focus_foreground_subagent` | `test_subagent_registry_repl.py` (5) | ✓ shipped (Ctrl+F **focuses** the most-recent record; "kill all" was the Wave-C placeholder docstring and is removed) |
| User presets | `lyra_core.subagent.presets.{load_presets, SubagentPreset, PresetBundle}` | `test_subagent_presets_contract.py` (6) | ✓ shipped substrate; `/spawn <preset>` slash wiring is Wave E |
| DAG scheduler | `lyra_core.subagent.scheduler.SubagentScheduler` | `test_subagent_scheduler_contract.py` (6) | ✓ shipped library; orchestrator entry-point wiring is Wave E |
| Variant runs | `lyra_core.subagent.variants.run_variants` (default judge picks `max(payload["score"])`, falls back to first-OK) | `test_subagent_variants_contract.py` (5) | ✓ shipped; LLM-judge integration is Wave E (default judge ships now) |
| Permission stack | `lyra_core.permissions.stack.PermissionStack` (now `set_mode`) + `lyra_core.permissions.injection.injection_guard` (8 patterns) | `test_permission_stack_contract.py` (6) | ✓ shipped substrate **and** session-attached (`/tools` lazily attaches; `Alt+M` mirrors mode); `AgentLoop.pre_tool_call` per-call enforcement is Wave E |
| Tool approval cache | `lyra_cli.interactive.tool_approval.ToolApprovalCache` (`mode`-aware: `yolo` → allow, `strict` → re-prompt, `normal` → cached) — now session-attached + surfaced in `/tools approve / deny / approvals` | `test_tool_approval_contract.py` (6) | ✓ shipped substrate **and** REPL-reachable (`/tools approve <Name>` etc.); `AgentLoop._dispatch_tool` per-call check is Wave E |
| `ExecuteCode` real | `lyra_core.tools.execute_code.execute_code` (subprocess + AST allow-list + timeout + stripped env) | `test_execute_code_contract.py` (6) | ✓ shipped (subprocess backend; pyodide / firejail are pluggable Wave-E backends behind the same `ExecuteCodeResult` contract) |
| `Browser` real | `lyra_core.tools.browser.browser_open` (Playwright; graceful "install lyra[browser]" fallback) | `test_browser_tool_contract.py` (5) | ✓ shipped; click / type / screenshot are Wave E |
| Custom user tools | `lyra_core.tools.user_tools.{tool, load_user_tools}` | `test_user_tools_loader_contract.py` (6) | ✓ shipped substrate; agent-loop registry merge is Wave E |
| Lifecycle hooks | `lyra_core.hooks.lifecycle.{LifecycleBus, LifecycleEvent}` (6 events) | `test_hooks_lifecycle_contract.py` (6) | ✓ shipped substrate; full agent-loop emit at every seam is Wave E |
| MCP registry + trust banner | `lyra_core.mcp.{MCPRegistry, MCPServer, trust_banner_for}` + real `/mcp [list/register/trust/untrust/remove]` dispatcher | `test_mcp_contract.py` (6) | ✓ shipped library **and** REPL-reachable; transport client (websockets / stdio) + persisted trust are Wave E |
| Live budget meter | `lyra_cli.interactive.budget.{BudgetMeter, price_for}` (token → USD, hand-curated price table for GPT-4o/4o-mini, o3/o4-mini, Claude 3.5/3.7/4.1) + `/budget record / status / reset` slash | `test_budget_meter_contract.py` (6) | ✓ shipped library **and** REPL-reachable (manual `/budget record`); provider-callback auto-deduction is Wave E |
| Preflight wiring | `lyra_core.providers.preflight_plugin.PreflightPlugin` (`pre_llm_call` hook + `preflight.ok` / `preflight.exceeded` HIR events) | `test_preflight_plugin_contract.py` (6) | ✓ shipped plugin; `llm_factory` auto-installation is Wave E |
| Live-streaming `/pair` | `lyra_cli.interactive.pair_stream.PairStream` (subscribes to every `LifecycleEvent`, pipes 1 line/event into a sink) + `_cmd_pair` attach/detach + session-owned `LifecycleBus` | `test_pair_stream_contract.py` (6) | ✓ shipped substrate **and** REPL-reachable (`/pair on` attaches, `/pair off` mutes); REPL console sink that redraws prompt safely is Wave E |

**Substrate-vs-wiring split:** Wave D ships every claimed module
as a real, tested library and flips the slash-level user-visible
toggles where one existed (`/agents`, `/budget`, `/pair`, `/mcp`,
`/tools`). The deeper agent-loop / provider call-site wiring
(preflight → llm_factory auto-install, BudgetMeter → provider
usage callbacks, PairStream → REPL console, MCPRegistry →
transport client, ToolApprovalCache → `AgentLoop._dispatch_tool`,
`PermissionStack` → `AgentLoop.pre_tool_call`) remains the
explicit Wave-E focus and is captured in the Wave-E plan
(`2026-04-24-v1.9-channels-backends-eval.md`). That split is
intentional: substrates land in v1.8.0, deep integration in
v1.9.0.

---

## 5f. v2.0.0 "Frontier" delta (2026-04-24, Wave F)

Wave F closes out the [full-parity roadmap](superpowers/plans/2026-04-24-full-parity-roadmap.md).
15 task buckets (`f1`…`f15`) ship **15 new modules + 186 new contract
tests** across `lyra-core` and `lyra-cli`. Whole-repo regression:
**1530 passed, 2 skipped, 0 failed** (sandbox-bound git tests in
`test_subagent_parallel.py`, `test_worktree_lifecycle.py`, and
`test_merge_conflict_resolver.py` are deselected — they pass outside
the sandbox).

| feature | code symbol(s) | tests | status |
|---|---|---|---|
| TDD phase state machine | `lyra_core.tdd.state.{TDDStateMachine, TDDPhase, HistoryEntry, PlanArtifact, RedFailureArtifact, GreenPassArtifact, RefactorArtifact, ShipArtifact}` + REPL `_cmd_phase` | `test_tdd_state_machine_contract.py`, `test_tdd_state_machine.py`, `test_slash_phase_contract.py` (43) | ★ ✓ shipped — strict/lenient FSM with typed evidence + lightweight reason-driven `transition()` |
| Cross-channel verifier | `lyra_core.verifier.trace_verifier.{extract_claims, verify_claims}` | `test_cross_channel_verifier_contract.py` | ★ ✓ shipped — file:line citations reconciled against FS + optional git diff, path-escape rejection |
| Refute-or-Promote stage | `lyra_core.loop.refute_or_promote.{RefuteOrPromoteStage, Refutation, Promotion}` | `test_refute_or_promote_contract.py` | ★ ✓ shipped — adversarial sub-agent loop |
| Rubric Process Reward Model | `lyra_core.eval.prm.{Rubric, RubricJudge, RubricSet, RubricSetReport}` | `test_prm_contract.py` | ★ ✓ shipped — weighted subjective verifier |
| NGC compactor | `lyra_core.context.ngc.{NGCCompactor, NGCItem, NGCOutcomeLogger}` | `test_ngc_compactor_contract.py` | ★ ✓ shipped — grow-then-evict + outcome log |
| Hybrid skill router | `lyra_core.skills.{registry.SkillRegistry, router.HybridSkillRouter}` | `test_skill_router_contract.py` | ★ ✓ shipped — trigger + success-rate weighted |
| Trigger auto-optimizer | `lyra_core.skills.optimizer.TriggerOptimizer` | `test_trigger_optimizer_contract.py` | ★ ✓ shipped — token-set dedup prevents near-duplicate bloat |
| In-session skill synthesis | `lyra_core.skills.synthesizer.SkillSynthesizer` | `test_skill_synthesizer_contract.py` | ★ ✓ shipped — registers drafts immediately |
| `/review --auto` | enhanced `/review` slash with `--auto` post-turn flag | `test_review_auto_contract.py` | ★ ✓ shipped |
| Harness plugins (two surfaces) | `lyra_core.plugins.{registry.{PluginManifest, PluginRegistry}, manifest.{PluginManifestSpec, validate_manifest, load_manifest}, runtime.{LoadedPlugin, PluginRuntime}}` | `test_plugin_registry_contract.py`, `test_plugin_manifest_contract.py`, `test_plugin_runtime_contract.py` (30) | ★ ✓ shipped — programmatic + declarative, per-plugin isolation |
| Meta-harness outer loop | `lyra_core.meta.{corpus.{ParityCorpus, HarnessTask}, outer_loop.MetaHarness}` | `test_meta_harness_contract.py` | ★ ✓ shipped — pass-rate leaderboard over standard corpus |
| Harness arena | `lyra_core.arena.elo.{Arena, EloRatings}` | `test_arena_contract.py` | ★ ✓ shipped — pairwise Elo audit trail |
| Federated skill registry | `lyra_core.skills.federation.{SkillManifest, FederatedRegistry, Federator}` | `test_federated_skill_registry_contract.py` | ★ ✓ shipped — export/import + merge strategies |
| KLong checkpoint & resume | `lyra_core.klong.checkpoint.{Checkpoint, CheckpointStore, Migrator}` | `test_klong_checkpoint_contract.py` | ★ ✓ shipped — schema-versioned snapshots + forward migrators |
| Frontier UX bundle (`/split`, `/vote`, `/observe`, `/ide`, `/catch-up`) | `lyra_cli.interactive.session.{_cmd_split, _cmd_vote, _cmd_observe, _cmd_ide, _cmd_catchup}` + `lyra_core.ide.bridges.{IDEBridge, IDETarget, build_open_command}` (VS Code, Cursor, JetBrains, Zed, Neovim) | `test_ide_bridges_contract.py`, `test_frontier_ux_contract.py` (23) | ★ ✓ shipped |

**Roadmap closure.** With Wave F shipping, every cell in the §1–§2
parity matrix backed by a reference-repo feature now has a
`✓ shipped` status with a named code symbol and a verifiable
contract test. The §3 ★ net-new list has 16 of 20 items shipped as
`★ ✓ shipped` (the four remaining — Multica federated retros, the
Plan-Mode auto-skip heuristic tightening, `/eval-drift`, `/golden
add`, `/handoff` — are tracked as v2.x follow-ups in the
post-full-parity backlog). The §4 frontier list now has 5 items
shipped (`/split`, `/vote`, `/observe`, IDE bridges, `/catch-up`
via Wave F; `/replay` via Wave E), with the remaining frontier
ideas moved to a v2.x research backlog.

---

## 6. Why this matters

- **Claude Code** gives us the UX vocabulary users already expect.
- **sst/opencode** shows how to organise agents, tools, hooks, plugins in an open-source Go/TS monorepo.
- **Hermes Agent** proves the skill-self-improvement + FTS5 + multi-backend terminal model works in a Python codebase.
- **Lyra** is the only one that treats **TDD discipline** and **outcome-anchored harness evolution** as first-class citizens. Everything in section 3 is load-bearing for that thesis; it's why the project needs to exist.

The "NOW" column is what ships in this wave (≈ current commit batch). The rest is wired into the existing v1 / v1.5 / v1.7 / v2 phases in [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md).
