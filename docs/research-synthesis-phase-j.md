# Research Synthesis — Phase J (v3.1.0)

This document records what was actually surveyed, what was selected, what
was rejected, and where the surviving designs landed in Lyra. It
exists because the brief was explicit ("**Deep research these github
repos and make sure you have selected best things and apply them
inside Lyra**") and Lyra's contract is that every borrowed idea has a
visible citation chain.

## 1. Sources surveyed

| # | Source | Type | Surveyed for |
|---|--------|------|--------------|
| 1 | `NousResearch/hermes-agent` | OSS agent framework, 118k★ | UX patterns, slash surface, persistence, MCP |
| 2 | `garrytan/gbrain` | Opinionated agent persona/preset bundle, 11.5k★ | Bundle install pattern, naming, idempotence |
| 3 | `nesquena/hermes-webui` | Web/mobile UI for Hermes Agent, 4.4k★ | Session streaming, JSONL transport, message shape |
| 4 | `NousResearch/hermes-agent-self-evolution` | DSPy + GEPA self-improvement layer for Hermes Agent | Skill/prompt evolution algorithm |
| 5 | `FoundationAgents/MetaGPT` | Multi-agent software-company framework (`hong2024metagpt`, ICLR 2024 oral) | Role + SOP pattern, role-typed handoffs |
| 6 | arxiv 2604.14228 | Survey-style paper on production agent gaps | Reliability gap (`pass^k`), reflexion as future-direction signal |

The `2604.14228` paper supplied the meta-frame: which gaps in the
2025–2026 fleet are systemic vs incidental. Three of its named
problems map cleanly onto Phase J ports.

## 2. Selection criteria

Every candidate idea was scored against five filters:

1. **Self-contained** — can it ship as a `lyra_core/<module>/` plus
   one CLI surface, without rewiring existing kernel paths?
2. **Offline-testable** — is there a deterministic stub that pins
   the contract without a live LLM?
3. **Opt-in** — does it stay invisible to users who don't ask for
   it? Lyra's v3.0.0 repositioning made TDD opt-in; v3.1.0 keeps
   that posture.
4. **Citation chain** — is there a public paper / repo we can cite
   in `CHANGELOG.md` and module docstrings?
5. **Net-new** — does v3.0.0 already cover this surface? If yes,
   skip and document the existing surface in `feature-parity.md`.

Five ideas passed all five filters; they became Phase J.1 – J.5.
Several promising ideas failed at least one filter and landed in §6
("Not pulled, and why").

## 3. What we pulled

### J.1 — Brain bundles (from `garrytan/gbrain`)

* **Source idea**: a "brain" is one named bundle of `SOUL.md` +
  `policy.yaml` + `.lyra/commands/*.md` that a user installs with one
  command. Each bundle bakes in a persona, toolset binding, and model
  preference.
* **Why selected**: filter 1 (single module), filter 3 (opt-in: only
  applies when the user runs `lyra brain install <name>`), and a
  clear gap — Lyra's `init` command bootstraps an *empty* persona but
  has no curated presets.
* **Where it landed**:
  * `lyra_core/brains/registry.py` — `BrainBundle`, `BrainRegistry`,
    `install_brain`.
  * `lyra-cli/commands/brain.py` — `lyra brain list|show|install`.
  * Built-ins: `default`, `tdd-strict`, `research`, `ship-fast`.
* **Tests**: `packages/lyra-core/tests/test_brains_registry.py`,
  `packages/lyra-cli/tests/test_cli_brain_command.py`.

### J.2 — `pass^k` reliability metric (from arxiv 2604.14228 §12.1, citing τ-bench `yao2024taubench`)

* **Source idea**: a single `pass@1` number hides *silent flakiness*
  — tasks where the agent succeeds sometimes but not always.
  τ-bench's correction: report both `pass@k` (any trial succeeds)
  and `pass^k` (all `K` trials succeed); the gap is the silent-
  flakiness signal.
* **Why selected**: Lyra's eval harness shipped `pass@1` only; this
  closes a directly-named gap from the 2604.14228 survey, and the
  marginal cost is one new module + one CLI flag.
* **Where it landed**:
  * `lyra_core/eval/passk.py` — `CaseTrials`, `PassKReport`,
    `run_passk`.
  * `lyra-cli/commands/evals.py` — `lyra evals --passk N`.
* **Tests**: `packages/lyra-core/tests/test_passk_metric.py`,
  `packages/lyra-cli/tests/test_cli_evals_passk.py`.

### J.3 — Team roles + orchestrator (from MetaGPT `hong2024metagpt`)

* **Source idea**: `Code = SOP(Team)`. Materialise each role's
  Standard Operating Procedure as data, then orchestrate roles as a
  pipeline (PM → Architect → Engineer → Reviewer → QA).
* **Why selected**: Lyra had subagents (`/spawn`) and toolsets
  (`/toolsets apply`) but no notion of *role-typed handoffs*. The
  MetaGPT pattern composes both primitives without changing them.
* **Where it landed**:
  * `lyra_core/teams/registry.py` — `TeamRole`, `TeamPlan`,
    `TeamRegistry`, `run_team_plan`.
  * `lyra-cli/interactive/session.py::_cmd_team` —
    `/team [show <name>|plan|run <task>]`.
  * Built-in roles: `pm`, `architect`, `engineer`, `reviewer`, `qa`.
* **Tests**: `packages/lyra-core/tests/test_teams_registry.py`,
  `packages/lyra-cli/tests/test_slash_team.py`.
* **Deliberately scoped down**: we ship the role + SOP + handoff
  primitives, **not** MetaGPT's full "build a 2048 game from one
  sentence" autodriver. Users compose the pipeline themselves via
  `/team run <task>` so the loop stays observable and interruptible.

### J.4 — Reflexion loop (from Shinn et al. 2023 + 2604.14228)

* **Source idea**: when an attempt fails, generate a verbal lesson
  ("why did this fail; what to try next time"), store it in
  episodic memory, and prepend it to the next attempt's prompt.
  Empirically beats zero-shot on HumanEval without weight updates.
* **Why selected**: complements J.2 — `pass^k` *measures* flakiness;
  Reflexion is one of the cheapest *fixes*. Both surface the same
  underlying signal (the gap between potential and reliable
  performance) at different stages of the loop.
* **Where it landed**:
  * `lyra_core/loop/reflexion.py` — `Reflection`, `ReflectionMemory`,
    `make_reflection`, `inject_reflections`.
  * `lyra-cli/interactive/session.py::_cmd_reflect` —
    `/reflect [on|off|add|tag|clear]`, on-disk snapshot at
    `<repo>/.lyra/reflexion.json`.
* **Tests**: `packages/lyra-core/tests/test_reflexion_loop.py`,
  `packages/lyra-cli/tests/test_slash_reflect.py`.

### J.5 — GEPA prompt evolver (from `khattab2024gepa` and `hermes-agent-self-evolution`)

* **Source idea**: prompt-tuning is a multi-objective problem
  (score vs token cost). Replace scalar fitness with a Pareto front
  and reflective mutation. The DSPy lineage adds the LLM-backed
  mutator. Hermes-agent-self-evolution wraps both into an
  agent-skill-specific optimiser.
* **Why selected**: filter 1 (self-contained), filter 2 (offline-
  testable via templated mutator), filter 3 (opt-in via a CLI), and
  closes a gap Lyra had: there was no first-class way to
  *systematically* improve a `SOUL.md` or a slash-command prompt
  against a held-out test set.
* **Where it landed**:
  * `lyra_core/evolve/gepa.py` — `EvolveCandidate`,
    `EvolveTrainExample`, `evolve`, `pareto_front`,
    `score_candidate`, `templated_mutator`.
  * `lyra-cli/commands/evolve.py` — `lyra evolve --task spec.yaml`.
* **Tests**: `packages/lyra-core/tests/test_evolve_gepa.py`,
  `packages/lyra-cli/tests/test_cli_evolve_command.py`.
* **Deliberately scoped down**: the always-on self-evolution daemon
  from `hermes-agent-self-evolution` is overkill for a single-
  developer CLI. We ship the algorithm as a one-shot command; users
  pick when to run it. The CLI also never *applies* the evolved
  prompt — it prints it. The user copies the new prompt into their
  `SOUL.md` themselves so the change is auditable.

## 4. Citation chain summary

| Phase | Module | Primary citation | Secondary |
|-------|--------|-----------------|-----------|
| J.1 | `lyra_core.brains` | `garrytan/gbrain` | — |
| J.2 | `lyra_core.eval.passk` | `yao2024taubench` (τ-bench) | arxiv 2604.14228 §12.1 |
| J.3 | `lyra_core.teams` | `hong2024metagpt` (ICLR 2024 oral) | — |
| J.4 | `lyra_core.loop.reflexion` | Shinn et al. 2023 | arxiv 2604.14228 §12.3 |
| J.5 | `lyra_core.evolve` | `khattab2024gepa` | `NousResearch/hermes-agent-self-evolution`, DSPy |

Every module's docstring repeats the citation so the chain survives
file moves and rebrands.

## 5. Sequencing rationale

The five ports were ordered J.1 → J.5 to manage risk:

1. **J.1 (brain bundles)** — pure data, no runtime; unblocks
   all subsequent personas.
2. **J.2 (`pass^k`)** — pure measurement, no behaviour change;
   gives J.4/J.5 a way to measure improvement.
3. **J.3 (team roles)** — composition primitive; depends on J.1
   only for the persona vocabulary.
4. **J.4 (Reflexion)** — first behaviour change; reads from
   `_last_user_task` which is a one-line patch in `_dispatch_plain`.
5. **J.5 (GEPA evolver)** — closes the loop: J.2 measures,
   J.4 records, J.5 systematises improvement.

If any port had blocked, the previous ones still ship as standalone
features.

## 6. Not pulled (and why)

| Source | Idea | Filter that failed | Where it could go later |
|--------|------|--------------------|-------------------------|
| `nesquena/hermes-webui` | Web/mobile UI | filter 1 (out of scope for a CLI) | Separate `lyra-webui` package; v3.0.0 already exposes the JSONL session stream and `acp` server it would need. |
| `hermes-agent-self-evolution` | Always-on self-evolution daemon | filter 3 (not opt-in by design) | Could ship behind `lyra evolve --watch`; revisit once v3.1.0 evolver gets real-world traffic. |
| MetaGPT | Baked-in 5-step "1 sentence → repo" autodriver | filter 5 (Lyra has `/run` and subagents already) + observability concern | Recipe in `docs/blocks/` once `/team run` proves itself. |
| Hermes Agent | Skill marketplace | filter 1 (cross-cutting; touches auth, registry, sandbox) | Phase K candidate. |
| arxiv 2604.14228 §12.5 | Continuous benchmark drift detector | filter 5 (`DriftGate` already ships in v2.x) | — |

## 7. Verifying the synthesis

Each of J.1 – J.5 ships:

* a `lyra_core/<module>/` directory with the algorithm,
* a `lyra-cli` slash command or top-level subcommand,
* a contract test file in `packages/lyra-core/tests/` and
* an integration test file in `packages/lyra-cli/tests/`.

Run them with:

```bash
# Per-package (the project convention; running both at once trips
# the conftest.py plugin name collision known since Phase G).
cd packages/lyra-core && pytest -q
cd packages/lyra-cli  && pytest -q
```

The tests pin the contract surface listed in §3 — adding a feature is
fine; removing one without bumping the major version is not.

## 8. Future-direction notes

Two arxiv 2604.14228 gaps Phase J explicitly **does not** close:

* **§12.4 — distributional drift between offline eval and prod
  trajectories.** `pass^k` is a step toward continuous reliability
  monitoring but remains an offline metric. A live-traffic equivalent
  (`pass^k` over the last `N` real sessions) is a Phase K candidate.
* **§12.6 — multi-agent debate as a verification mechanism.** J.3
  ships the role primitive, but the *consensus* layer (debate, vote,
  cross-check) is intentionally out of scope. The right place for it
  is `lyra_core.verifier`, which already has a `RubricSet` interface.
