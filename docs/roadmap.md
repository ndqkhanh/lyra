# Lyra — Delivery Roadmap

A test-first, milestone-driven path from empty repo to a shippable v1 CLI agent — and from v1 onward, a general-purpose agent that ships TDD as one of several optional discipline plugins. Each milestone has a definition of done (DoD) that is verified by tests in the repo, not by adjectives. No milestone is marked complete until its tests are green on CI.

> **v3.0.0 note.** TDD became opt-in in v3.0.0 (released 2026-04-27).
> The roadmap milestones below are historical artifacts from the
> v0.1 → v2.x era when TDD was the kernel posture; the contracts and
> tests are unchanged, but every "TDD gate must be on" condition now
> reads "TDD gate must be on **when the plugin is enabled**". See
> `migration-to-lyra.md` and `tdd-discipline.md` for the post-v3.0.0
> defaults.

---

## Guiding rules for the roadmap itself

1. **Every milestone starts with red tests.** The acceptance tests for a milestone are written (and committed) before implementation starts. Implementation lands in the same week and turns those tests green.
2. **One milestone per week, usually.** Some milestones span two weeks when the surface is large (e.g., PermissionBridge + hooks together); the plan calls that out explicitly.
3. **No milestone merges with a lower bar than the previous.** If M5 introduces a new test suite, M6 onwards must keep it passing.
4. **The repo must be usable at the end of each milestone.** `lyra init && lyra run "…"` must work, even if the feature set is narrower than v1.
5. **Dogfood from week 2.** Once M2 ships, every new feature is built inside Lyra itself. The harness tests itself (meta-TDD, see [tdd-discipline.md](tdd-discipline.md#meta-tdd-lyra-testing-itself)).

---

## Phase 0 — Repo scaffolding (week 0)

**Scope.** Monorepo layout, CI, formatting, license, docs site. No agent code yet.

**Deliverables.**
- Monorepo under `projects/lyra/` with these packages:
    - `lyra-core/` — loop, permissions, hooks, context, memory adapters.
    - `lyra-skills/` — shipped skill packs + extractor.
    - `lyra-mcp/` — MCP consumer + server adapters.
    - `lyra-cli/` — Typer entrypoint.
    - `lyra-evals/` — test harness, golden trajectories, red-team corpus.
- `pyproject.toml` per package + root workspace file (uv / rye / pdm choose at M0 — default: `uv` for speed).
- GitHub Actions: lint (`ruff`), typecheck (`pyright` strict), test (`pytest -x`), evals smoke.
- `LICENSE` = MIT, `NOTICE` lists upstream influences.
- Pre-commit hooks mirroring the TDD gate hook (dogfood-lite).
- Docs site built from the existing `docs/` (MkDocs with Material theme).

**DoD.** `make ci` passes on an empty but well-structured repo. No runtime code yet.

---

## Phase 1 — Kernel: loop + permissions + hooks (weeks 1–2)

**Scope.** The minimum-viable kernel: agent loop, PermissionBridge, hook framework, three in-tree hooks (tdd-gate stub, destructive-pattern, secrets-scan), five native tools (Read, Glob, Grep, Edit, Write), local-only file logging.

**Red tests first.**
- `test_loop_basic.py` — MockLLM → Read → terminate.
- `test_permission_modes.py` — PLAN denies writes, DEFAULT allows after approval, RED allows only test writes.
- `test_hook_registry.py` — hooks registered, ordered, sandboxed, timeout-respected.
- `test_tdd_gate_minimal.py` — Edit(src/*.py) without a preceding failing test is blocked.
- `test_secrets_scan.py` — `AKIA[0-9A-Z]{16}` in Write args → denied.

**Implementation.**
- Port `harness_core.loop.AgentLoop` with Lyra extensions (TDD phase tracking, repeat detector stub).
- `PermissionBridge` with 4 decisions and mode table (from [block 04](blocks/04-permission-bridge.md)).
- `HookRegistry` with PreToolUse/PostToolUse/Stop events (subset of block 05).
- Event JSONL emitted to `.lyra/<session>/events.jsonl`.

**DoD.**
- `lyra run "ls the repo"` works end-to-end (Plan mode by default, approves read, terminates).
- All red tests now green.
- First dogfood session logged under `.lyra/`.

**Trade-offs locked in this phase.**
- Python-first, not Rust/Go — ships faster, integrates with existing `harness_core`. Cost: startup latency.
- In-process hooks by default — reject per-tool subprocess sandbox for v1 (too slow). Risk accepted: hook misbehavior is a kernel-level concern; hooks are in-tree and reviewed.

---

## Phase 2 — Plan Mode + CLI surface (week 3)

**Scope.** Plan Mode becomes the real entry point. CLI commands: `init`, `run`, `retro`, `doctor`, `session`.

**Red tests first.**
- `test_plan_artifact_shape.py` — plan has frontmatter + required sections + acceptance tests.
- `test_plan_mode_readonly.py` — Planner cannot invoke any write tool.
- `test_plan_approval_flow.py` — unapproved plan does not advance to RED.
- `test_cli_smoke.py` — Typer commands parse, `--help` stable.

**Implementation.**
- `lyra-cli` Typer app.
- Planner sub-loop invoked under `PermissionMode.PLAN`.
- `plans/<session>.md` artifact with the YAML + Markdown schema in [block 02](blocks/02-plan-mode.md).
- `lyra init` writes an initial `SOUL.md` from template, seeds `.lyra/`.

**DoD.** Interactive session with a human writes a plan, shows diff of intended work, demands approval, then runs only the approved feature items.

**Trade-offs.**
- Plan Mode default-on accepted. Cost: extra LLM calls even for trivial tasks; mitigated by auto-skip heuristic (file count ≤ 2, expected steps ≤ 8).
- Typer over Click: richer autocomplete, same ecosystem maturity.

---

## Phase 3 — Context engine + memory tier-1 (week 4)

**Scope.** Five-layer context pipeline; three-tier memory limited to procedural (skills) + episodic (trace digests). Semantic tier stubbed.

**Red tests first.**
- `test_context_layers.py` — SOUL never compacted; ordering invariant holds.
- `test_compaction.py` — compaction preserves preservation set; token count strictly drops.
- `test_memory_procedural.py` — write skill → read back with tokenizer-bounded result.
- `test_progressive_disclosure.py` — three MCP memory tools (`list_topics`, `get_topic`, `search_topic`) work in sequence.

**Implementation.**
- Context assembler ([block 06](blocks/06-context-engine.md)).
- SQLite FTS5 + Chroma adapters ([block 07](blocks/07-memory-three-tier.md)).
- BGE-small-en-v1.5 local embedder default.
- Observation reducer with type-aware rules.

**DoD.** A 40-step session stays under 60% of context budget without identity drift (SOUL still verbatim at step 40).

**Trade-offs.**
- Hybrid SQLite + Chroma vs single store: reader latency wins, writer complexity loses. Accepted.
- On-device embedder default — privacy win, cost: CPU hit at write time. Mitigated by async write queue.

---

## Phase 4 — TDD gate full contract (week 5)

**Scope.** The TDD gate promoted from stub to production. Test runner adapters for pytest, vitest, go test. Coverage regression detection. RED-proof evidence validator.

**Red tests first.**
- `test_tdd_state_machine.py` — IDLE→PLAN→RED→GREEN→REFACTOR→SHIP transitions + illegal transitions rejected.
- `test_red_proof.py` — genuine failing test accepted; flake-passing "red" rejected; syntax-error test rejected.
- `test_coverage_regression.py` — dropping coverage > tolerance blocks; improvement allowed.
- `test_post_edit_focused_tests.py` — post-Edit hook runs only the test file matched by impact map.
- `test_escape_hatch_audit.py` — `--no-tdd` logs and surfaces in `lyra retro`.

**Implementation.**
- [tdd-discipline.md](tdd-discipline.md) contracts wired across hook registry.
- Impact map: edit → tests (by path, then by symbol).
- Coverage deltas via `coverage.py`, `c8`, `go tool cover`.

**DoD.** 100 golden trajectories run under `--strict` mode; every production edit has a preceding RED commit in the trace.

**Trade-offs.**
- Per-language runner adapters vs generic "run `make test`": adapter approach ships three-language support; generic loses signal. Chosen: adapters for v1, generic as fallback with warning.
- RED-proof enforcement is strict: 3–5% extra steps per session. Accepted — the gain in downstream defect rate offsets this.

---

## Phase 5 — Verifier + cross-channel (week 6)

**Scope.** Two-phase verifier with different-family evaluator; cross-channel evidence (trace/diff/snapshot) comparator; filesystem snapshot backend.

**Red tests first.**
- `test_phase1_objective.py` — deterministic pass/fail on frozen inputs.
- `test_phase2_subjective.py` — mocked evaluator verdicts parse; rubric score bounds.
- `test_cross_channel.py` — fabricated test-run claim caught; untracked side effect flagged.
- `test_evidence_validator.py` — hallucinated file:line rejected.
- `test_evaluator_family_detection.py` — same-family fallback tagged `degraded_eval=same_family`.

**Implementation.**
- [Block 11](blocks/11-verifier-cross-channel.md) contracts.
- Snapshot backend: `fsevents` on macOS, `fanotify`+poll fallback on Linux, `ReadDirectoryChangesW` on Windows.
- Trace digest compressor feeding the evaluator.

**DoD.** A hand-crafted sabotage corpus (10 scenarios: disabled test, deleted assertion, commented-out guard, etc.) is caught ≥ 9/10 by the combined TDD gate + verifier + safety monitor pipeline.

**Trade-offs.**
- Snapshot subsystem is OS-specific and fragile → mitigated by polling fallback + CI matrix.
- Evaluator in a different family costs 2× API calls per task-end. Worth it; measured uplift in evaluator recall.

---

## Phase 6 — Skill engine + extractor + shipped packs (week 7)

**Scope.** Skill loader, router, extractor. Ship four packs: `atomic-skills`, `tdd-sprint`, `karpathy`, `safety`.

**Red tests first.**
- `test_skill_loader.py` — discovery from `skills/`, `~/.lyra/skills/`, workspace.
- `test_skill_router.py` — description-based disambiguation; precedence resolution.
- `test_skill_extractor.py` — successful trajectory → candidate proposal → refined SKILL.md.
- `test_shipped_packs.py` — each pack's skills load, route, execute on a golden input.

**Implementation.**
- [Block 09](blocks/09-skill-engine-and-extractor.md) contracts.
- Hermes-style extractor: candidate classifier, refiner, builder, promoter.
- User-gated promotion for third-party skills.

**DoD.** Running `lyra run "extract a skill from yesterday's checkout-bug session"` produces a reviewable SKILL.md PR against the user's personal skill pack.

**Trade-offs.**
- Auto-extraction on by default with always-user-review before promotion: avoids the skill-spam failure mode in [docs/04-skills.md](../../../../docs/04-skills.md#failure-modes).
- Description-based routing (vs function-calling selection) — Claude Code-compatible, ecosystem-portable. Cost: description quality is paramount; linter enforces at pack-load.

---

## Phase 7 — Subagents + worktrees (week 8)

**Scope.** Subagent orchestrator with git worktree isolation. Depth-2 recursion limit. Merge strategy with conflict-resolver.

**Red tests first.**
- `test_worktree_lifecycle.py` — allocate, run, cleanup; no orphan worktrees.
- `test_fs_sandbox.py` — write outside scope rejected; read outside logged.
- `test_parallel_subagents.py` — non-overlapping scopes complete + merge.
- `test_scope_collision.py` — overlapping scopes rejected at dispatch.
- `test_merge_conflict_resolver.py` — 3-way merge with resolver loop; stalemate escalates.

**Implementation.**
- [Block 10](blocks/10-subagent-worktree.md) contracts.
- Recursion depth enforced at `Spawn` tool gate.
- `.lyra/worktrees/` cleanup reconciler at session start.

**DoD.** A task like "add logging across 6 independent modules" completes via 6 parallel subagents and merges without conflict on a clean repo.

**Trade-offs.**
- Full worktrees vs shallow clones: full worktrees are fatter but LSP/indexer-friendly. v2 opt-in shallow.
- Merge conflict resolver uses an LLM; add `--no-auto-merge` opt-out for users who want every conflict surfaced.

---

## Phase 8 — DAG teams plugin (week 9)

**Scope.** SemaClaw-inspired two-phase orchestration: dynamic LLM decomposition + deterministic scheduler + parallel subagent execution.

**Red tests first.**
- `test_dag_validate.py` — cycles rejected; unreferenced nodes rejected; width budget enforced.
- `test_dag_scheduler.py` — topological order; parallel batch sizing; partial-failure propagation.
- `test_dag_parking.py` — park-on-risk at node boundaries; resume with user decision.
- `test_harness_plugin_boundary.py` — `--harness=dag-teams` swaps scheduler; `three-agent` unaffected.

**Implementation.**
- [Block 03](blocks/03-dag-teams.md) contracts.
- `HarnessPlugin` interface so users can ship their own.

**DoD.** A "migrate 40 Django views to DRF" benchmark completes with 4-wide parallelism; merge success rate ≥ 90% on clean repos.

**Trade-offs.**
- Two-phase with LLM-Planner + rule-Scheduler vs fully-LLM scheduling: latency/cost both lower, determinism way higher. Chosen.

---

## Phase 9 — Safety monitor + observability + HIR (weeks 10–11)

**Scope.** Continuous safety monitor. HIR event schema frozen. OpenTelemetry exporters. `lyra retro` / `view` polished.

**Red tests first.**
- `test_safety_monitor_windowing.py` — N-step window, no duplicate flags, triggered scans on patterns.
- `test_safety_corpus.py` — known sabotage patterns flagged at ≥ 0.7 confidence; benign session has 0 flags.
- `test_hir_schema.py` — every event kind validates; round-trips JSON.
- `test_otlp_export.py` — mock collector receives expected spans.
- `test_retro_artifact.py` — retro.md structure + citations to artifacts by hash.

**Implementation.**
- [Block 12](blocks/12-safety-monitor.md) and [Block 13](blocks/13-observability-hir.md) contracts.
- Secrets-masking at trace-emit time.
- Rolling trace policy (default keep 50 sessions).

**DoD.** Red-team corpus run: 0 false positives on 20 benign sessions; ≥ 85% recall on the sabotage corpus (combined with verifier).

**Trade-offs.**
- Safety monitor using `gpt-5-nano` adds ~5% to session cost but catches injection-driven drift the verifier alone misses.
- HIR adoption means extra event-schema work, but makes traces portable and compatible with framework-agnostic eval tooling.

---

## Phase 10 — MCP bidirectional + third-party servers (week 12)

**Scope.** MCP consumer (filesystem, sqlite, jira, notion tested); Lyra as MCP server; trust banners + injection-guard integration; progressive disclosure tiers.

**Red tests first.**
- `test_mcp_adapter.py` — JSON-RPC list_tools + call_tool; timeouts; malformed response.
- `test_mcp_trust_banner.py` — third-party tool output wrapped with banner.
- `test_mcp_progressive.py` — cold tool discovery via umbrella `MCP` tool.
- `test_mcp_server_exposed.py` — Lyra exposes `read_session`, `get_plan`; stdio + HTTP bearer auth.
- `test_mcp_injection.py` — third-party server returns `<system>` payload → guarded.

**Implementation.**
- [Block 14](blocks/14-mcp-adapter.md) contracts.
- `lyra mcp serve --transport {stdio,http}`.
- HTTP server loopback-bind default with generated bearer token.

**DoD.** Lyra runs end-to-end with 3 external MCP servers attached + exposes itself as an MCP server that an external client can consume.

**Trade-offs.**
- Opt-in MCP servers only at `lyra init` — keeps default context small.
- Exposed MCP server's write-capable tools default disabled; opt-in via config with warning.

---

## Phase 11 — Golden evals + release candidate (week 13)

**Scope.** A reproducible evaluation suite, a public benchmark run, v1 release.

**Deliverables.**
- `lyra-evals/` with 3 corpora:
    - `golden/` — 100 curated TDD tasks (pytest, vitest, go test).
    - `red-team/` — 30 sabotage / injection / prompt-leak scenarios.
    - `long-horizon/` — 10 multi-step DAG tasks.
- CI job that runs `golden/smoke` (10 fast tasks) per PR.
- Nightly CI that runs the full corpus; drift gate if p95 success drops > 5% week-over-week.
- `docs/benchmarks.md` with headline numbers and methodology.

**DoD.** v1 tag cut. `pip install lyra` works from PyPI. README on `projects/lyra/` matches what ships.

---

## Target repository layout

```
projects/lyra/
├── LICENSE (MIT)
├── NOTICE
├── README.md
├── pyproject.toml                          # workspace
├── docs/                                   # this directory
│   ├── architecture.md
│   ├── architecture-tradeoff.md
│   ├── system-design.md
│   ├── tdd-discipline.md
│   ├── threat-model.md
│   ├── roadmap.md                          # this file
│   └── blocks/
│       ├── 01-agent-loop.md
│       ├── ...
│       └── 14-mcp-adapter.md
├── packages/
│   ├── lyra-core/
│   │   ├── pyproject.toml
│   │   └── src/lyra_core/
│   │       ├── __init__.py
│   │       ├── loop.py                     # ext of harness_core AgentLoop
│   │       ├── permissions/                # PermissionBridge
│   │       │   ├── bridge.py
│   │       │   ├── modes.py
│   │       │   ├── risk.py
│   │       │   └── policy.py
│   │       ├── hooks/                      # Hook framework
│   │       │   ├── registry.py
│   │       │   ├── events.py
│   │       │   └── builtin/
│   │       │       ├── tdd_gate.py
│   │       │       ├── secrets_scan.py
│   │       │       ├── destructive_pattern.py
│   │       │       ├── injection_guard.py
│   │       │       ├── format_on_edit.py
│   │       │       ├── lint_on_edit.py
│   │       │       ├── typecheck_incremental.py
│   │       │       ├── stop_verifier.py
│   │       │       ├── skill_extractor_trigger.py
│   │       │       └── state_md_persist.py
│   │       ├── context/
│   │       │   ├── pipeline.py             # 5-layer assembler
│   │       │   ├── compactor.py
│   │       │   └── reducer.py              # observation reduction
│   │       ├── memory/
│   │       │   ├── procedural.py           # skills
│   │       │   ├── episodic.py             # trace digests
│   │       │   ├── semantic.py             # facts + wiki
│   │       │   ├── sqlite_fts.py
│   │       │   └── chroma_adapter.py
│   │       ├── plan/
│   │       │   ├── planner.py
│   │       │   ├── artifact.py
│   │       │   └── heuristics.py
│   │       ├── verifier/
│   │       │   ├── objective.py
│   │       │   ├── subjective.py
│   │       │   ├── cross_channel.py
│   │       │   └── snapshot.py
│   │       ├── safety/
│   │       │   ├── monitor.py
│   │       │   └── window.py
│   │       ├── harnesses/                  # plugin slots
│   │       │   ├── base.py
│   │       │   ├── single_agent.py
│   │       │   ├── three_agent.py
│   │       │   └── dag_teams.py
│   │       ├── subagent/
│   │       │   ├── orchestrator.py
│   │       │   ├── worktree.py
│   │       │   └── fs_sandbox.py
│   │       ├── soul/
│   │       │   ├── loader.py
│   │       │   ├── precedence.py
│   │       │   └── drift.py
│   │       ├── observability/
│   │       │   ├── hir.py
│   │       │   ├── otel_export.py
│   │       │   ├── file_export.py
│   │       │   └── artifacts.py
│   │       ├── tools/
│   │       │   ├── read.py
│   │       │   ├── write.py
│   │       │   ├── edit.py
│   │       │   ├── glob.py
│   │       │   ├── grep.py
│   │       │   ├── bash.py
│   │       │   ├── todowrite.py
│   │       │   └── skill.py
│   │       └── state/
│   │           ├── session.py
│   │           └── state_md.py
│   │   └── tests/                          # mirrors src/
│   │
│   ├── lyra-skills/
│   │   ├── pyproject.toml
│   │   └── src/lyra_skills/
│   │       ├── loader.py
│   │       ├── router.py
│   │       ├── extractor/
│   │       │   ├── candidate.py
│   │       │   ├── refiner.py
│   │       │   ├── builder.py
│   │       │   └── promoter.py
│   │       └── packs/
│   │           ├── atomic-skills/
│   │           │   ├── localize/SKILL.md
│   │           │   ├── edit/SKILL.md
│   │           │   ├── test-gen/SKILL.md
│   │           │   ├── reproduce/SKILL.md
│   │           │   └── review/SKILL.md
│   │           ├── tdd-sprint/
│   │           │   └── 7-phase/SKILL.md
│   │           ├── karpathy/
│   │           │   ├── think-before-coding/SKILL.md
│   │           │   ├── simplicity-first/SKILL.md
│   │           │   ├── surgical-changes/SKILL.md
│   │           │   └── goal-driven-execution/SKILL.md
│   │           └── safety/
│   │               ├── injection-triage/SKILL.md
│   │               └── secrets-triage/SKILL.md
│   │
│   ├── lyra-mcp/
│   │   ├── pyproject.toml
│   │   └── src/lyra_mcp/
│   │       ├── client/
│   │       │   ├── adapter.py
│   │       │   ├── bridge.py
│   │       │   ├── progressive.py
│   │       │   └── cache.py
│   │       └── server/
│   │           ├── app.py
│   │           ├── auth.py
│   │           └── handlers.py
│   │
│   ├── lyra-cli/
│   │   ├── pyproject.toml
│   │   └── src/lyra_cli/
│   │       ├── __main__.py                 # typer app
│   │       ├── commands/
│   │       │   ├── init.py
│   │       │   ├── run.py
│   │       │   ├── retro.py
│   │       │   ├── view.py
│   │       │   ├── doctor.py
│   │       │   ├── session.py
│   │       │   ├── artifact.py
│   │       │   ├── skill.py
│   │       │   ├── mcp.py
│   │       │   └── wipe.py
│   │       └── tui/
│   │           ├── approval.py
│   │           └── trace_view.py
│   │
│   └── lyra-evals/
│       ├── pyproject.toml
│       ├── src/lyra_evals/
│       │   ├── runner.py
│       │   ├── golden/
│       │   ├── red_team/
│       │   └── long_horizon/
│       └── tests/
│
├── SOUL.md                                 # lyra's own SOUL
├── .lyra/                            # dogfood state (gitignored partly)
│   └── policy.yaml                         # default policy
└── examples/
    ├── hello-tdd/
    └── migrate-views/
```

## Milestone-to-block map

| Milestone | Block(s) primarily delivered |
|---|---|
| Phase 1 | 01, 04, 05 (minimal) |
| Phase 2 | 02, + CLI |
| Phase 3 | 06, 07 (partial) |
| Phase 4 | 05 (full tdd-gate), [tdd-discipline.md](tdd-discipline.md) |
| Phase 5 | 11 |
| Phase 6 | 08, 09 |
| Phase 7 | 10 |
| Phase 8 | 03 |
| Phase 9 | 12, 13 |
| Phase 10 | 14 |
| Phase 11 | release & benchmarks |

## Risk register (schedule)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Snapshot backend fragility (OS matrix) | M | H | Poll fallback; CI matrix; reduce scope to files-only in v1 if needed |
| Evaluator cost overruns | L | M | Cost caps per session; doctor surface; opt-in `--no-evaluator` |
| MCP spec churn during dev | M | M | Pin spec version; compatibility matrix |
| TDD gate friction rejects dogfood | M | M | Escape hatch is logged; extractor auto-generates red for common edits after soak period |
| Chroma dependency heaviness | M | L | `lyra-core[memory-lite]` extra without Chroma; fallback to FTS-only |
| Plan Mode rejection by users | L | H | Auto-skip heuristic; `--no-plan` flag; measured onboarding success |
| Scope creep on skills extraction | H | M | Promotion gated on user review; doctor lists candidates without auto-merging |

## Success metrics at v1

- ≥ 85% task success on the golden corpus, measured end-to-end.
- ≥ 90% sabotage recall on the red-team corpus.
- p95 first-reply latency ≤ 3 s (single-agent harness, SSD, local embedder).
- Median session cost ≤ $0.25 on the golden corpus (mixed-family model, 8k context budget).
- 0 P0 security incidents in a 30-day internal dogfood window before public release.
- < 1% false-positive rate on the safety monitor for benign dogfood sessions.

## Post-v1 (v1.5, v1.7 and v2)

The detailed plan lives in [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md). At a glance:

- **v1.5 "Parity & Evidence"** (≈ 8 weeks, target `v0.2.0`). Close the most expensive credibility gaps surfaced by the April-2026 landscape study:
    - Phase 12: SWE-bench Pro + LoCoEval adapters in `lyra-evals` (contamination-resistant public benchmarks).
    - Phase 13: **Interactive shell** — `lyra` (no args) drops into a Claude-Code-style REPL with slash commands, status bar, and a non-TTY fallback for CI.
    - Phase 14: CodeAct-style Python-as-action `HarnessPlugin` (OpenHands-style, under our same sandbox + TDD gate).
    - Phase 15: Rubric Process Reward Model verifier + Refute-or-Promote adversarial stage (SWE-TRACE, arXiv:2604.19049).
    - Phase 16: Remote runners (Modal / Fly / Docker) + default rootless-podman sandbox + PII masking at emit time (the items already earmarked in v1).
    - Phase 17: Agentless parallel-candidate `HarnessPlugin` for cost-sensitive / CI flows.
    - Phase 18: ACON-style observation compressor + Devin-Wiki-style auto-indexed repo docs.

- **v1.7 "Self-Creating Harness"** (≈ 6 weeks, target `v0.3.0`). Adopt the April-2026 Stanford NGC paper ([arXiv:2604.18002](https://arxiv.org/abs/2604.18002)) and Anthropic's Skill-Creator v2 ([`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator)). Stop hand-tuning skills and compaction; let outcome reward shape them:
    - Phase 19: **Skill-Creator engine** — 4-agent loop (Executor / Grader / Comparator / Analyzer), iteration workspaces, `benchmark.json` artifacts.
    - Phase 20: **Reuse-first hybrid router** — BM25 + dense embeddings (BGE-small) + description match with confidence gating; explicit `NO_MATCH` / `AMBIGUOUS` verdicts; `lyra skills route --explain`.
    - Phase 21: **Trigger eval corpus + description auto-optimizer** — 60/40 train/test split, 5-iteration bounded optimizer, `lyra skills tune <name>`.
    - Phase 22: **In-session synthesis + lifecycle** — repetition detector, bundled-script detector, `/creator` slash command, outcome attribution, refine/retire proposals. (Absorbs what was previously v2 Phase 20.)
    - Phase 23: **NGC-inspired context compactor** — grow-then-evict cadence, block-level eviction on HIR events, budget-aware interoception in SOUL, LLM-driven rerank, outcome logging to `compactor-outcomes.jsonl` as training corpus for the future learned compactor.

- **v2 "Self-Evolving Harness"** (≈ 14 weeks, target `v0.5.0`). The research-grade bets:
    - Phase 24: **Meta-Harness** outer loop (arXiv:2603.28052) — Lyra optimizes its own harness against your repo.
    - Phase 25: **Arena mode** — blind A/B harness tournaments for ecosystem use (Windsurf Wave 13 pattern).
    - Phase 26: **Federated skill registry** with sigstore signing + policy admission.
    - Phase 27: KLong-style long-horizon checkpoint + resume across model generations.
    - Phase 28: the four already-earmarked v2 items — training-arena corpus exporter (incl. NGC-format `compactor-outcomes.jsonl`), Multica team orchestration, federated retros, Agentic Wiki cross-repo sharing.

Success metrics at v2: ≥ 90% golden, ≥ 96% red-team recall, ≥ 48% SWE-bench Pro (Opus-class), ≥ 65% LoCoEval requirement coverage, Meta-Harness ≥ 5pp beat on user-held-out test sets.

Success metrics at v1.7: ≥ 80% skill-trigger recall on curated eval set, ≥ 90% converged pass-rate after ≤ 5 creator iterations, ≥ 1.5× compactor compression at ≤ 1pp success-rate cost.

See [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md) for the full phase list, red tests, DoDs, trade-offs, and source citations.

## Where we actually are (post-v2.7)

The phases above describe the *original plan*. Lyra has since shipped the v2.x "honest rebuild" line, which absorbed several v1.5/v1.7 phases into the production CLI rather than waiting for separate releases. This is the live status as of **v2.7.1** (2026-04-27):

| Release        | Date         | Theme                                                                      | Status   |
|----------------|--------------|----------------------------------------------------------------------------|----------|
| v2.0 – v2.5    | 2026-Q1      | Provider catalogue, MCP autoload, FTS5 session store, cron daemon, ACP server, plugin discovery | shipped  |
| **v2.6.0**     | 2026-04-23   | "Production-Ready" rewrite of the audit corpus (34 issues found, 34 fixed) | shipped  |
| **v2.7.0**     | 2026-04-26   | Honest-rebuild slash commands: real `/evals`, real `/compact`, LifecycleBus → HIR + OTel, real `git worktree`-isolated `/spawn`, `_LyraCoreLLMAdapter` provider bridge | shipped  |
| **v2.7.1**     | 2026-04-27   | **DeepSeek small/smart split.** Two-tier model routing (`fast_model = deepseek-v4-flash → deepseek-chat`; `smart_model = deepseek-v4-pro → deepseek-reasoner`). `/model fast` / `smart` / `fast=<slug>` / `smart=<slug>` slash UX. Universal + provider env stamping. In-place provider mutation. Subagent runner opens the smart slot before `build_llm`. Full docs sweep across `projects/lyra/`. | **shipped (current)** |

Test count at v2.7.1: **lyra-cli 1016 passed**, **lyra-core 796 passed**, **lyra-mcp 57 passed** (plus `lyra-skills` and `lyra-evals`). See [`projects/lyra/CHANGELOG.md`](../CHANGELOG.md) for the per-release narrative and [`docs/architecture.md` §3.11](architecture.md#311-smallsmart-model-routing-v271) for the small/smart routing contract.

### Next up

* **v2.8 — sandbox + cost dashboard.** Default-on rootless-podman sandbox for `Bash` (deferred from v1 Phase 5/9); first-class `lyra cost` panel that reads the per-turn billing already journaled to `events.jsonl`.
* **v2.9 — slot-aware fallbacks.** Today's fallback list is per-provider; v2.9 makes it slot-aware so `fast` and `smart` can fall back to different families independently.
* **v3.0 — Meta-Harness Phase 24** (originally v2 Phase 24): Lyra optimises its own harness against the user's repo.
