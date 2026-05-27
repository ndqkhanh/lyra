# Lyra — Roadmap v1.5, v1.7, and v2

> **See also:** [`novel-ideas.md`](novel-ideas.md) — eight novel selling points for **v1.8 / v1.9 / v2.5** that go *beyond* the milestones below (Meta TTS tournament, ReasoningBank failure-distillation, Skill-RAG, KnowRL-style TDD-reward, CubeSandbox microVM, PoisonedRAG defense, self-wiring memory graph, cross-harness federation). Underlying papers mirrored under [`../papers/`](../papers/).

Continuation of [`roadmap.md`](roadmap.md). v1 is code-complete (v0.1.0, 255 tests green, `make ci` reproducible). This document plans the next three milestones:

- **v1.5 "Parity & Evidence"** (~Q3 2026, target `v0.2.0`) — close the credibility gaps surfaced by the April-2026 landscape study.
- **v1.7 "Self-Creating Harness"** (~Q4 2026, target `v0.3.0`) — add to the 2026 landscape study directly: Neural Garbage Collection ([arXiv:2604.18002](https://arxiv.org/abs/2604.18002), Li et al., Stanford) and Anthropic's Skill-Creator v2 meta-skill ([`anthropics/skills`](https://github.com/anthropics/skills/tree/main/skills/skill-creator), 121K stars, 176K installs). Both say the same thing from different angles — *stop hand-tuning, let outcome reward shape the harness* — one for memory, one for skills. v1.7 converts that into a 5-phase shippable release.
- **v2 "Self-Evolving Harness"** (~Q1 2027, target `v0.5.0`) — Meta-Harness outer loop, arena, federated registry, long-horizon checkpoints.

Same guiding rules apply: red tests first, one phase per 1–2 weeks, no phase merges with a lower bar than the previous, repo usable at every phase boundary, dogfood every new feature inside Lyra itself.

---

## 0. Where we are vs. the April 2026 landscape

### 0.1. SoTA snapshot (as of April 2026)

**Scaffolding matters as much as the base model.** On SWE-bench Verified, the same Claude Opus 4.6 powers results ranging from 44.7% (OpenHands + CodeAct v2) to 72.0% (Augment Code's internal scaffold) — a 27-point swing from orchestration alone. Source: [Awesome Agents SWE-bench Leaderboard, April 19 2026](https://awesomeagents.ai/leaderboards/swe-bench-coding-agent-leaderboard/), [Morph "15 AI Coding Agents (2026)" review](https://www.morphllm.com/ai-coding-agent). This confirms the thesis Lyra was built on: we are a harness engineering project, and the scaffolding layer is where the leverage lives.

**SWE-bench Verified is contaminated.** OpenAI's internal audit found frontier models reproduce verbatim gold patches; Claude Opus 4.5 scores 80.9% Verified but **45.9% on SWE-bench Pro** (same model, contamination-resistant corpus, standardised scaffolding). Source: [CodeAnt SWE-bench leaderboard analysis](https://www.codeant.ai/blogs/swe-bench-scores), [Morph "SWE-bench Pro: why 46% beats 81%"](https://www.morphllm.com/swe-bench-pro). The industry is moving to Pro, temporal holdouts, and private-codebase splits. Our evals module should move with it.

**Open-source scaffolds are within 4pp of proprietary.** OpenHands + CodeAct v3 at 68.4% is essentially tied with Augment's 72.0% on the same base model. The remaining gap is base model quality, not orchestration. Open-source lost the model race but won the scaffold race.

**Top harness innovations worth stealing:**

| Scaffold | Innovation | Evidence |
|---|---|---|
| OpenHands + CodeAct v3 | **Python-as-action**: agent emits executable Python instead of JSON tool calls; runs in sandbox | 68.4% Verified vs 44.7% for older JSON-tool OpenHands v2 on same class of models |
| SWE-agent (Princeton) | **Agent–Computer Interface (ACI)**: purpose-designed tools (`view_file`, `search_dir`, `create_file`) that constrain LLM action space | Now adopted by most commercial scaffolds |
| Moatless Tools | **Minimal context**: symbol-level retrieval, no large file chunks | Best cost-per-resolved-task on weaker models; 35.9% Verified on Haiku 4.5 |
| Agentless | **Parallel patch generation + test-based ranking**; no iterative tool calls | 34.2% Verified at a fraction of the token cost of iterative agents |
| Aider | **Architect mode**: stronger model plans, weaker model implements | Currently 31.4% Verified |
| Windsurf Wave 13 | **Arena mode**: A/B two model identities blind on the same prompt | New ecosystem surface; Grok Build has 8 parallel agents with Society-of-Mind |
| Devin 2.0 | **Devin Wiki**: auto-indexed repo architecture docs, generated and maintained by the agent | Persistent repo knowledge beyond session-local memory |
| Kilo Code | **Mode-first UX**: Architect / Code / Debug / Orchestrator as first-class modes, each with its own tool whitelist | ~1.5M users; popular UX pattern |
| Claude Code (Feb 2026) | **Agent Teams** for multi-agent coordination + custom hooks + MCP | $2.5B ARR — the economic validation of the approach we picked |

### 0.2. Research directions worth adopting

| Paper / System | Key idea | Where it fits in Lyra |
|---|---|---|
| **Meta-Harness** (Lee et al., [arXiv:2603.28052](https://arxiv.org/abs/2603.28052), 2026) | A coding-agent proposer with filesystem access to all prior harness candidates (code + traces + scores) searches over harness code. Beat hand-tuned ACE by 7.7pp on text classification; ranked #1 on TerminalBench-2 among Haiku-4.5 agents. | **v2 headliner.** Adds `lyra harness optimize` — Lyra can evolve its own harness against your repo's corpus. |
| **SWE-TRACE** (Han et al., [arXiv:2604.14820](https://arxiv.org/abs/2604.14820), 2026) | Rubric-Based Process Reward Model gives dense step-level feedback; reused at inference for heuristic Test-Time Scaling (PRM-guided action pruning). | v1.5 verifier upgrade: rubric PRM scores replace binary pass/fail on subjective checks. v2 inference: PRM-pruning at action-selection. |
| **KLong** ([arXiv:2602.17547](https://arxiv.org/abs/2602.17547), 2026) | Extreme long-horizon (>context window) tasks via trajectory-splitting + progressive RL. | v2: 200-step projects with checkpoint / resume across model generations. |
| **LoCoEval** (long-horizon repo conversations, [arXiv:2603.06358](https://arxiv.org/abs/2603.06358), 2026) | Benchmark: 128 samples, 50-turn conversations, 64K–256K tokens, 2.5 requirements per sample. Existing memory systems struggle on this. | v1.5: add as `lyra-evals/locoeval/` long-horizon corpus alongside our 10 DAG tasks. |
| **ACON** (Agent Context Optimization, OpenReview 2026) | Unified compression of observations + interaction histories. 26–54% memory reduction, 95% accuracy retained. | v1.5: replaces our hand-rolled type-aware reducer. |
| **BACM-RL** (Budget-Aware Context Management, [arXiv:2604.01664](https://arxiv.org/abs/2604.01664), 2026) | Curriculum RL for compression-under-budget. 1.6× gains in compositional settings. | v2: bandit policy over compression strategies. |
| **Refute-or-Promote** ([arXiv:2604.19049](https://arxiv.org/abs/2604.19049), 2026) | Adversarial stage-gated multi-agent review with Cross-Model Critic and kill-mandate phase. | v1.5 verifier: Phase-3 "refute" attempt before Phase-2 promote. |
| **Externalization in LLM Agents survey** (Zhou et al., [arXiv:2604.08224](https://arxiv.org/abs/2604.08224), April 2026) | Frames memory / skills / protocols as three externalization dimensions, harness as integration layer. Emerging directions: **self-evolving harnesses** and **shared agent infrastructure**. | Validates the Lyra thesis. v2's self-optimizing harness is the paper's "self-evolving harness" direction; federated skill sharing is "shared infrastructure". |
| **VeRO** (evaluation harness for optimizing agents, [arXiv:2602.22480](https://arxiv.org/abs/2602.22480), 2026) | Versioned agent snapshots + budget-controlled eval + structured traces. | v1.5: every `lyra evals` run pins a harness snapshot hash. |
| **Neural Garbage Collection (NGC)** (Li, Hamid, Fox, Goodman, Stanford, [arXiv:2604.18002](https://arxiv.org/abs/2604.18002), April 2026) | Cache eviction and token generation are both discrete actions sampled from the LM, jointly trained by outcome reward alone. Block-level evictions at cadence δ; budget-aware interoception (tell the model its budget in the prompt); replay attention masks for exact policy-gradient updates. 2–3× peak KV compression with strong accuracy on Countdown/AMC/AIME; **49.6% vs 21.2% next-best baseline** on Countdown at 2.4×. | **v1.7 Phase 23** — we can't train a policy but the *harness pattern* transfers: grow-then-evict cadence, block-level eviction on HIR events, budget meter in SOUL (interoception), LLM-driven rerank + outcome logging as training corpus for future learned compactor. |
| **Anthropic Skill-Creator v2** ([`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator), Dec 2025 release, 121K stars, 176K installs) | A meta-skill for creating/improving/measuring skills via a 4-agent loop: **Executor** (runs skill + baseline in parallel subagents) · **Grader** (assertion pass/fail with `{text, passed, evidence}` schema) · **Comparator** (blind A/B between versions) · **Analyzer** (patterns across evals). 60/40 train/test description optimizer iterates 5× to raise trigger pass-rate without body edits. Durable iteration workspaces + `benchmark.json` artifacts. | **v1.7 Phases 19–22** — direct port of the pattern, adapted to our worktree subagents, TDD gate, and HIR. Addresses the "undertrigger" gap in our keyword router explicitly. |

### 0.3. Gap map: Lyra v0.1.0 vs. the 2026 frontier

| Capability | Lyra v0.1.0 | Frontier in April 2026 | Priority |
|---|---|---|---|
| Base scaffold | Native JSON tools (Read/Write/Edit/Grep/Glob/Bash) | **CodeAct-style Python-as-action** (OpenHands v3), ACI (SWE-agent), Moatless minimal context | P0 — plugin |
| Public benchmarks | 100 internal golden, 30 red-team, 10 long-horizon | SWE-bench Pro + LoCoEval + TerminalBench-2 are the public scoreboards | P0 — must-have |
| Verifier | Objective pass/fail + subjective evaluator + cross-channel | **Rubric PRM** dense step-level + **Refute-or-Promote** adversarial stage | P1 |
| Long-horizon memory | SQLite FTS5 + Chroma + SOUL | **Devin-Wiki auto-indexed repo docs** + ACON-compressed observations | P1 |
| Inference-time scaling | Single-sample action per step | **PRM-guided TTS** (prune weak branches before rollout) | P1 |
| Parallel patch generation | DAG-Teams orchestration (different tasks in parallel) | **Agentless parallel candidates on the same task** + test-based selection | P1 |
| Harness optimization | Hand-tuned heuristics | **Meta-Harness outer loop**: coding agent proposes harness edits from prior trace filesystem | P0 for v2 |
| Arena / A/B | `lyra eval --config A/B` (manual) | **Windsurf Arena Mode**: blind A/B, vote surface | P2 |
| Mode system | Plan / Run / Retro | **Kilo-style 4 modes**: Architect / Code / Debug / Orchestrator | P2 |
| Skill lifecycle | Post-hoc extractor + user-review | **Self-refining skills** with outcome-based retention/forgetting | **P0 — v1.7** (Phase 22; was v2) |
| Skill creation UX | Manual — write SKILL.md by hand or accept extractor proposal verbatim | **4-agent creator loop** (Executor/Grader/Comparator/Analyzer) with iteration workspaces + `benchmark.json` + blind A/B — Anthropic's [`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | **P0 — v1.7 (Phase 19)** |
| Skill router | Keyword + stem + synonym (no confidence, no "no match" verdict) | **Hybrid retrieval**: BM25 + dense embeddings + description match with confidence gating; explicit `NO_MATCH` / `AMBIGUOUS` verdicts | **P0 — v1.7 (Phase 20)** |
| Skill trigger quality | No measurement — skills undertrigger silently | **Trigger eval corpus** (should-trigger / should-not) + description auto-optimizer (60/40 train/test, 5-iter) | **P1 — v1.7 (Phase 21)** |
| In-session skill creation | None (extractor runs post-session only) | Repetition detector + bundled-script detector surface proposals mid-session; `/creator` slash command enters creator loop without leaving REPL | **P0 — v1.7 (Phase 22)** |
| Skill sharing | Per-repo + `~/.lyra/skills` | **Federated sharing** via Git-based skill registries | P2 — v2 (Phase 26) |
| Context compaction | Hand-rolled type-aware reducer — continuous, fixed rules | **NGC-style grow-then-evict cycle** with budget-aware interoception, block-level eviction, LLM-driven rerank, outcome-reward logging, replay masks — [arXiv:2604.18002](https://arxiv.org/abs/2604.18002) | **P0 — v1.7 (Phase 23)** |
| Remote runners | Local only | Modal, Fly, Daytona sandbox (OpenHands); Cursor background agent | P0 — v1.5 carry-over |
| Sandboxing | `--sandbox` opt-in | Default-on rootless Podman (was B.20) | P1 — v1.5 carry-over |
| PII masking | None | Industry-required for enterprise trials | P0 — v1.5 carry-over |
| Non-LLM safety monitor | Single LLM safety monitor | Hybrid ML classifier + rule engine + LLM vote (our injection-guard already ships this for one surface, not safety monitor) | P1 — v1.5 carry-over |

P0 = ship in v1.5 / v1.7 or we are falling behind. P1 = ship in the same milestone if bandwidth, otherwise defer. P2 = v2 or later.

---

## 1. v1.5 — "Parity & Evidence" (≈ 8 weeks)

**Theme.** Close the three most expensive gaps to public credibility: we need numbers on public corpora, the scaffolding innovations proven elsewhere, and the already-earmarked enterprise items (remote runners, PII, sandboxing). No new core abstractions; every feature is a plugin, a hook, or a tightening of an existing block.

**Meta-DoD for v1.5.** `lyra evals --corpus swe-bench-pro` and `--corpus loco-eval` both complete end-to-end and produce a signed report. Every phase below has green tests in CI on Python 3.10 / 3.11 / 3.12. No regressions on the v1 golden/red-team/long-horizon corpora.

### Phase 12 — SWE-bench Pro + LoCoEval integration (week 1–2)

**Scope.** Extend `lyra-evals` with adapter layers for the two public corpora the field now takes seriously. We do not fork either corpus — we adapt our runner to consume them.

**Red tests first.**
- `test_swebench_pro_adapter.py` — a single golden Pro task loads, runs under our EvalRunner, produces the standard SWE-bench Pro pass/fail verdict byte-for-byte compatible with the Scale AI harness.
- `test_loco_eval_adapter.py` — a 50-turn LoCoEval conversation runs to completion; our context budget holds; final verdict matches published oracle.
- `test_eval_harness_snapshot.py` — every eval run pins a harness snapshot (commit SHA + package versions + policy.yaml hash); re-running the same corpus with the same snapshot produces identical results modulo LLM non-determinism, and the non-determinism is bounded and reported (VeRO-style).
- `test_contamination_guard.py` — the runner refuses to evaluate on a corpus that post-dates a model's training cutoff unless `--allow-contaminated` is explicit; warnings surface in `lyra retro`.

**Implementation.**
- `lyra_evals/adapters/swe_bench_pro.py` — wraps the public Pro harness, loads issues, applies our agent, emits the Scale-AI-compatible JSON report.
- `lyra_evals/adapters/loco_eval.py` — loads the 128-sample benchmark, drives 50-turn conversations, measures our context-budget usage turn-by-turn.
- `lyra_evals/snapshot.py` — versioned harness snapshots following VeRO: `{sha, packages[], policy_hash, seed}` tuple attached to every report.
- `lyra evals --corpus {golden,red-team,long-horizon,swe-bench-pro,loco-eval}`.

**DoD.**
- `lyra evals --corpus swe-bench-pro --budget 50` runs on a 50-task SWE-bench Pro subset and produces a report ≤ 10% worse than the published Moatless+Haiku-4.5 baseline when pointed at the same model (sanity check, not a headline claim).
- LoCoEval smoke: we hit ≥ 40% requirement-coverage on a 20-sample subset (the published mean for baseline memory systems; we should beat it because our SOUL + 3-tier memory is designed for exactly this).
- A CI job runs a 10-task Pro smoke per nightly; drift gate ≥ 5% week-over-week triggers a red build.

**Trade-offs.**
- Vendor model keys required for reproducing published numbers. `doctor` surfaces this before the run instead of failing mid-eval.
- SWE-bench Pro Docker images are heavy (~5 GB each). We cache by commit SHA; default corpus run requires ≥ 20 GB disk. Documented in `benchmarks.md`.
- We do **not** submit to the public Pro leaderboard in v1.5 — that's a v2 PR after we've closed the other gaps. But the adapter must be Scale-AI-submission-ready so the step after v1.5 is just administrative.

---

### Phase 13 — Interactive shell: ``lyra`` drops into a Claude-Code-style REPL (week 3)

**Scope.** Running ``lyra`` with no arguments now starts a coloured, slash-command REPL with a bottom status bar, history, and completion. Existing subcommands (`init`, `plan`, `run`, `doctor`, `session`, `retro`, `evals`) are unchanged. This closes the "it looks like a v0 CLI" UX gap that the v1 release surfaced and gives us a surface for the agent-interactive flow that every future phase (CodeAct, Rubric PRM, Arena) will plug into.

**Red tests first.**
- `test_interactive_session.py` — pure-logic dispatcher: default mode is `plan`; `/help` enumerates every registered slash command (no silent gaps); `/status` surfaces mode / model / turn / cost / pending; `/mode <plan|run|retro>` switches and rejects unknown values; `/exit` / `/quit` / `/clear` behave as expected; unknown slash commands return a help hint without incrementing turn; `/history` lists user inputs in order; `/model <name>` replaces the active model; plain text in plan mode records a pending task; `/approve` switches to run mode after a plan; `/reject` drops the pending plan; `/skills` lists the four shipped skill packs.
- `test_interactive_banner.py` — banner contains version, tagline, repo path (even for absolute paths > 120 chars), model, mode, and `/help` hint; plain-mode render has zero ANSI escapes.
- `test_cli_smoke.py` — `lyra` with no arguments starts the REPL and exits cleanly on EOF; `/exit` through a piped stdin produces exit code 0; banner is visible in the captured output.

**Implementation.**
- `lyra_cli.interactive.session` — pure, TTY-free `InteractiveSession` + `CommandResult` + `SLASH_COMMANDS` registry.
- `lyra_cli.interactive.banner` — Rich-rendered ASCII logo + cyan-bordered panel + metadata block; plain-text fallback for non-TTY.
- `lyra_cli.interactive.driver` — prompt_toolkit path (coloured prompt, bottom toolbar, FileHistory at `.lyra/interactive_history`, slash-command completer) with a graceful `input()` fallback when stdin/stdout isn't a TTY.
- `lyra_cli.interactive.completer` — `SlashCompleter` that completes from the live `SLASH_COMMANDS` registry.
- Typer wiring: `app.callback(invoke_without_command=True)`; `--repo-root` / `--model` options on the root; `no_args_is_help=False`.
- New dep: `prompt_toolkit>=3.0`.

**DoD.**
- `lyra` in a terminal shows the banner, a `plan ›` prompt, and a bottom status bar.
- `lyra < scripted.txt` or `echo /exit | lyra` works in CI with zero TTY features required.
- 17 new tests across 3 files; full suite ≥ 310 green on Python 3.9; ruff + pyright clean.
- `/help` lists 15 slash commands; none of them crash or leak state.
- Subcommands (`lyra plan`, `lyra run`, etc.) are untouched.

**Trade-offs.**
- prompt_toolkit adds ~200 KB to the CLI package. It's the de-facto Python TUI library (IPython, ptpython, pgcli), and we need FileHistory + bottom toolbar + completion — Rich alone can't do it cleanly.
- Rich 15 honours `$COLUMNS` above the `Console(width=…)` kwarg. The banner uses a context-managed env-var shim to guarantee width regardless of the caller's terminal size. Documented inline.
- The REPL routes plain text to mode-specific handlers, but real LLM dispatch lands with Phase 14 (CodeAct) — today the handler records the task and bills a turn. This mirrors the "walking skeleton" pattern from v1 and lets every future phase drop into the same surface.

---

### Phase 14 — CodeAct-style Python-as-action plugin (week 4)

**Scope.** Ship `lyra-core[codeact]`: a new `HarnessPlugin` where the agent emits executable Python and a sandbox executor runs it with our existing tool library bound into the Python namespace. This is additive, not a replacement; the JSON-tool harness remains default.

**Red tests first.**
- `test_codeact_execution.py` — the agent emits `files = read("src/foo.py"); edit("src/foo.py", ...)`; the sandbox runs Python, the edits land, and trace records each call as a HIR event.
- `test_codeact_sandbox_escape.py` — attempt to `import subprocess` or `os.system` inside the sandbox is rejected (AST-level filter) unless the active Permission Mode explicitly allows it; attempt to write outside worktree scope rejected by the same FS sandbox we already ship.
- `test_codeact_vs_json_parity.py` — our 100-task golden corpus runs under both harnesses; results are within ±3% of each other and both are audit-trail complete.
- `test_codeact_tdd_gate.py` — TDD gate still fires when the agent writes to `src/**` via Python, same as JSON Edit.

**Implementation.**
- `lyra_core/harnesses/codeact.py` — implements the `HarnessPlugin` interface; the action loop parses Python, executes it under a restricted namespace containing only our whitelisted callables.
- AST-level allowlist: `read`, `write`, `edit`, `glob`, `grep`, `bash` (mode-gated), `skill.invoke`, `spawn` (subagent, depth-limited). No `exec`, `eval`, no `__import__` of anything outside the whitelist, no subprocess.
- HIR extension: `code_act.exec.start` / `code_act.exec.end` events around each Python evaluation; each tool call inside is still emitted as the normal `tool.invoke` event.
- Integration with existing blocks: PermissionBridge, Hook Registry, Safety Monitor all still run on the nested tool calls — CodeAct is a different shape at the loop level, same primitives underneath.

**DoD.**
- `lyra run "add a rate-limit decorator" --harness codeact` completes with TDD gate intact.
- On the golden corpus: CodeAct and the JSON harness are within ±3% end-to-end. Where CodeAct wins, it wins on multi-step refactor tasks (≥ 5 edits in a session). Where JSON wins, it wins on strict-rule-following tasks.
- Token cost per task is reported separately in `lyra retro --compare harness=json vs harness=codeact`.

**Trade-offs.**
- We explicitly **do not** give CodeAct wider execution surface than the JSON harness. The value is in letting the LLM compose tool calls as Python (loops, conditionals, list comprehensions over tool results), not in giving it a bigger blast radius. This is the key Lyra spin on the OpenHands pattern.
- Static AST filter vs. runtime tracing: we chose AST for cost + clarity. Runtime tracing as a backstop is a v2 item if attackers find AST bypasses.
- Adds Python-in-Python complexity for developers debugging traces. Mitigated by `lyra view --format codeact` which renders the Python with each tool-call's inline result.

---

### Phase 15 — Rubric PRM verifier + Refute-or-Promote (week 4)

**Scope.** Upgrade the Phase-2 subjective verifier from a single pass/fail + rubric score to a dense Rubric Process Reward Model, and add a Phase-3 "refute" step where a different-family adversarial critic tries to kill the candidate before promotion.

**Red tests first.**
- `test_prm_rubric_score.py` — given a rubric with N criteria, the PRM returns per-criterion scores + evidence citations + aggregate; missing citations are a hard fail.
- `test_prm_drives_tts.py` — at step t, two action candidates are scored by the PRM; lower-scored action is pruned before environment execution; trace records the pruning decision and its evidence.
- `test_refute_stage.py` — after Phase-2 promote-candidate, a different-family "refuter" tries to write a failing test that passes on the old code and fails on the patched code; if the refuter succeeds, the candidate is rejected with the failing test as artifact.
- `test_refute_opt_out.py` — `--no-refute` disables the phase; trace records `degraded_verifier=refute_disabled`.
- `test_prm_cost_budget.py` — PRM scoring respects a per-session budget; overflow rolls back to the v1 binary verifier with a `degraded_verifier=prm_budget_exceeded` tag.

**Implementation.**
- `lyra_core/verifier/prm.py` — Rubric PRM takes (rubric_yaml, candidate, trace_digest, evidence_budget) → Pydantic `PRMReport`. Criteria cite trace events by hash; evidence validator already in tree rejects hallucinated citations.
- `lyra_core/verifier/refute.py` — Phase-3 adversarial: uses a different-family model (the safety-monitor model, reused) + the refuter skill pack; produces a deliberate counter-test; failure mode: "I could not write a refuting test, promote" is a weaker signal than "refuter passed".
- Hook into `Stop` event: PRM before refute before promote. Trace records each stage's verdict + cost.
- `lyra retro` shows PRM score breakdowns per criterion.

**DoD.**
- On the red-team sabotage corpus (30 scenarios), combined TDD gate + PRM verifier + refute stage catches ≥ 94% (up from 90% at v1).
- On the golden corpus (100 tasks), false-rejection rate from PRM+refute is ≤ 3% (i.e., we block legitimate work rarely).
- Session cost increase ≤ 25% vs v1 verifier. If we exceed, the budget-respect fallback is triggered and `degraded_verifier` tags are visible in retro.

**Trade-offs.**
- Rubric PRM lives in YAML (human-editable), not as a fine-tuned model. We do not train in v1.5. Upside: no training stack dep. Downside: PRM quality depends on prompt + rubric design; mitigated by shipping a starter `rubrics/` directory and a lint that rejects rubrics with fewer than 3 criteria or ambiguous thresholds.
- Refute stage adds one API call per `Stop`; cost modelled explicitly. Users can `--no-refute` to opt out with visible tag.

---

### Phase 16 — Remote runners + default sandbox + PII masking (week 5–6)

**Scope.** The three items already earmarked as v1.5 from the original roadmap. Ships together because they share an enterprise-trust surface.

**Red tests first.**
- `test_remote_runner_modal.py` — `lyra run --runner modal` dispatches to a Modal container; sessions stream trace events back; cleanup runs on crash.
- `test_remote_runner_fly.py` — same contract, Fly.io backend.
- `test_runner_parity.py` — local vs modal vs fly produce identical HIR events on a deterministic task (mock LLM).
- `test_sandbox_default.py` — on Linux/macOS, Bash tool runs inside rootless Podman by default; `--no-sandbox` logs and tags.
- `test_pii_mask_at_emit.py` — emails, phone numbers, SSNs, API keys are masked before HIR events land in `events.jsonl`; mask set is policy-configurable.
- `test_pii_mask_telemetry.py` — OTel spans carry masked values only; originals never leave the process.
- `test_shallow_worktree.py` — a subagent runs in a `git worktree --depth 100` checkout instead of full history when the task doesn't require deeper context.

**Implementation.**
- `lyra_core/runtime/remote/` with adapters: `modal.py`, `fly.py`, plus a docker-local reference adapter. Each implements `RemoteRunner` protocol: `start(session)`, `stream_trace()`, `stop()`, `cleanup()`.
- `lyra_core/permissions/sandbox.py` default-on rootless-podman for Bash; the Bash tool's docstring now documents the sandbox surface.
- `lyra_core/observability/pii.py` — masks at emit time; regex set + entity NER (small spaCy model, ~50 MB); policy-configurable via `.lyra/policy.yaml`.
- `lyra_core/subagent/worktree.py` gains `--depth` parameter; default 100 unless task plan mentions `history` / `blame` / `git log` etc.
- `lyra doctor` reports sandbox availability + PII model status + configured remote runners.

**DoD.**
- A session on Modal completes end-to-end with the same audit trail as local; cost attribution per session is accurate.
- A PII red-team sub-corpus (API keys, PHI-like strings, email lists) runs through the agent and produces `events.jsonl` with 0 leaks verified by a second-pass scanner.
- Bash sandbox overhead ≤ 40% per call on the reference macbook pro M3 (local podman).
- Shallow worktree reduces subagent disk usage by ≥ 60% on a ~500 MB repo.

**Trade-offs.**
- Remote runners add vendor dependency. We ship three (Modal, Fly, local Docker) so no single-vendor lock-in; the adapter boundary is clean enough that users can write their own.
- PII NER adds ~50 MB on install. `lyra-core[no-pii]` extra drops it for users who don't need it (with visible warning).
- Shallow worktree may hide context the agent needs. Heuristic err toward deeper when the plan mentions history; user can override `--worktree-depth full`.

---

### Phase 17 — Agentless parallel-candidate mode (week 7)

**Scope.** A `HarnessPlugin` that implements the Agentless three-stage pipeline (localize → generate N candidates → test-select), as a low-cost alternative to the iterative single-agent harness. Ships as `--harness agentless` alongside `single-agent`, `three-agent`, `dag-teams`, `codeact`.

**Red tests first.**
- `test_agentless_localize.py` — given an issue + repo, returns a ranked list of files:lines sufficient to fix.
- `test_agentless_parallel.py` — 5 patch candidates generated in parallel (with or without the subagent infra).
- `test_agentless_select.py` — candidate-selection runs the test suite on each patch; ties broken by PRM score (reuse phase 14); picks the winner.
- `test_agentless_cost_floor.py` — on the 100-task golden corpus, median cost is ≤ 40% of the single-agent harness's median at ≥ 70% of its success rate. (Hitting either threshold is acceptable; missing both is a red build.)

**Implementation.**
- `lyra_core/harnesses/agentless.py` — three deterministic stages around a generator.
- Reuses the existing subagent infrastructure for parallel generation — worktree isolation, merge strategy, etc.
- Cost knob: `--agentless-n {1..10}` for candidate count.

**DoD.**
- On golden: Agentless hits ≥ 70% of single-agent's success rate at ≤ 40% of its cost. If the win isn't there, the plugin is still correct — we ship it with benchmark numbers and let users opt in for CI / budget-constrained flows.
- `lyra retro --harness agentless` shows per-candidate pass/fail + the selection rationale.

**Trade-offs.**
- Agentless shines on well-specified issues, under-performs on ambiguous ones (where iterative exploration helps). Good fit for Devin-like CI workflows where the task is well-defined. Bad fit for exploratory work. We document this clearly; the harness auto-selector prefers iterative harnesses when the plan's acceptance tests are under-specified.

---

### Phase 18 — ACON-style observation compressor + Devin-Wiki repo index (week 8)

**Scope.** Two related upgrades to the context engine (block 06) and semantic memory tier (block 07): a learned-ish compression of observations, and an auto-maintained repo architecture wiki.

**Red tests first.**
- `test_acon_compressor.py` — an observation of size N tokens compresses to ≤ 0.6·N tokens while the downstream LLM achieves ≥ 95% accuracy on trace-questions over the compressed form (evaluated via the existing verifier).
- `test_acon_trace_fidelity.py` — compressed observations never drop citations or error messages; only prose and repeated whitespace are eligible for compression.
- `test_repo_wiki_generation.py` — on a ~50-file repo, `lyra wiki build` produces a `.lyra/wiki/` with module cards, call-graph summaries, and stable anchors; idempotent.
- `test_repo_wiki_refresh.py` — on a commit that touches 3 files, `lyra wiki refresh` updates only those 3 modules' pages + any cross-references; others untouched.
- `test_wiki_retrieval.py` — `lyra run "how does auth work"` surfaces the relevant wiki pages before file reads.

**Implementation.**
- `lyra_core/context/acon.py` — rule-based first pass (dedup, whitespace, obvious boilerplate), then LLM-based second pass under a compression guideline; the compressor is distilled from the SWE-TRACE + ACON approach but lives in YAML config + a small LLM call (not a trained model).
- `lyra_core/memory/wiki.py` — builds per-module markdown with: inputs, outputs, side-effects, callers, callees, tests, known hazards. Stores in the semantic tier (Chroma + SQLite FTS5).
- `lyra wiki {build,refresh,view}` CLI commands.

**DoD.**
- On a 40-step session in a fresh repo, context budget usage drops by ≥ 25% vs v1.0 with no verifier-measured regression on output quality.
- On a 500-file repo, `lyra wiki build` completes in ≤ 5 minutes with `budget=$5` and produces wiki pages the verifier considers ≥ 90% accurate against ground-truth module docs.

**Trade-offs.**
- Wiki is a second source of truth. We write it to `.lyra/wiki/` (gitignored by default) so users opt in to committing it. Commit-time lint flags wiki pages drifted > N days from source.
- ACON compression can drop signal. We expose `--no-compression` + a `compressed_from_N_to_M` tag on every compressed observation; auditors can always get the raw form from `artifacts/`.

---

### v1.5 exit criteria

- All 6 phases green in CI on Python 3.10/3.11/3.12.
- `lyra evals --corpus swe-bench-pro --budget 50` produces a signed report that could be submitted to the SWE-bench Pro leaderboard (but we hold submission for the v2 headline).
- Remote runners (Modal, Fly, Docker) + PII masking + default sandbox all green in a fresh cloud VM.
- CodeAct, Agentless plugins ship with parity benchmarks documented.
- Rubric PRM + Refute stage in place; v1.5 red-team sabotage recall ≥ 94%.
- `docs/benchmarks.md` updated with Pro + LoCoEval methodology + v1.5 headline numbers.
- CHANGELOG entry tagging `v0.2.0`.

---

## 1.5. v1.7 — "Self-Creating Harness" (≈ 6 weeks)

**Theme.** Close the loop: **the harness creates, reuses, refines, and retires its own skills end-to-end**, and the context compactor exposes its own budget and eviction decisions to the agent instead of hiding behind fixed heuristics. Two research inputs, both from April 2026, both pointing the same way: stop hand-tuning, let outcome reward shape the harness.

- **Anthropic Skill-Creator v2** (Dec 2025 meta-skill, 176K installs) pins down the *procedure* for building a skill that actually works — 4 agents (Executor/Grader/Comparator/Analyzer), durable iteration workspaces, blind A/B, a description-trigger optimizer. We port the pattern; our differentiators are worktree isolation, the TDD gate on every proposed skill, and HIR-compatible artifacts.
- **Neural Garbage Collection** ([arXiv:2604.18002](https://arxiv.org/abs/2604.18002)) reframes memory compaction as a first-class action sampled under the same outcome reward as reasoning. We can't train a policy, but the *harness shape* transfers: grow-then-evict cadence, block-level eviction, budget-aware interoception in the system prompt, LLM-driven rerank with full audit. We also log outcomes as the training corpus for a future learned compactor (deferred to v3).

**Meta-DoD for v1.7.** On a cold repo, `lyra` can:

1. **Route to an existing skill** with confidence ≥ 0.6 correctly on ≥ 90% of a 500-query labelled corpus.
2. **Detect a repeated pattern** (3+ similar tool-call sequences in one session) and propose capturing it as a skill. If the user accepts, run the full creator loop (test, grade, compare, iterate, register) without leaving the REPL.
3. **Auto-optimize** all 4 shipped skill packs' descriptions to ≥ 85% trigger-pass rate with ≤ 15% false-trigger on the held-out test set.
4. **Compact its own context** at a cadence and budget the agent is aware of; every compaction round is replayable from HIR; peak session tokens drop ≥ 25% vs v1 with ≤ 2pp success regression on golden.

**Numbering.** Five new phases (19–23) slot between v1.5 (ends at Phase 18) and v2 (starts at Phase 24 after renumber). v2 Phase 20 "Self-refining skills" is *absorbed* into v1.7 Phase 22 — attribution, refinement, and retirement all land in the same lifecycle surface as creation.

### Phase 19 — Skill-Creator Engine: `lyra skills create` (week 1–2)

**Scope.** A dedicated subcommand that implements the 4-agent creator loop end-to-end, produces durable iteration artifacts, and registers the resulting skill into `~/.lyra/skills/` or `.lyra/skills/`. Direct port of Anthropic's pattern, adapted to our worktree subagents, TDD gate, and HIR.

**Red tests first.**
- `test_skills_create_interview.py` — given a scripted interview transcript fixture (no real LLM), the interview stage produces a populated `SkillDraft` (name, description, trigger contexts, expected-output shape, test-case seed prompts).
- `test_skills_create_executor_parallel.py` — for N=3 eval prompts, executor spawns 2N subagent runs (with-skill + baseline) in one pass; all complete; each writes `outputs/` + `timing.json` to its own eval directory.
- `test_skills_create_grader_schema.py` — grader output exactly conforms to `{text, passed, evidence}` per assertion (Pydantic-enforced). Missing fields fail the test. Matches Anthropic's schema byte-for-byte so our artifacts are compatible with their `eval-viewer/generate_review.py`.
- `test_skills_create_comparator_blind.py` — comparator is given two outputs via a randomized `{a, b}` mapping; the true identity is recorded but never reaches the comparator's prompt; verdict is reproducible under same seed.
- `test_skills_create_analyzer_patterns.py` — on a fixture with one non-discriminating assertion (passes in all 3 with-skill AND all 3 baseline), analyzer flags it; on a fixture with a high-variance eval (95 tokens vs 18k tokens), analyzer flags variance.
- `test_skills_create_benchmark_json.py` — benchmark.json schema: `{skill_name, iteration, configs: {with_skill, without_skill}, per_config: {pass_rate, tokens_mean, tokens_std, duration_mean, duration_std}, delta: {pass_rate, tokens, duration}}`. Writeable and readable round-trip.
- `test_skills_create_iteration_workspace.py` — layout is `./skills-workspace/<skill>/iteration-<N>/eval-<slug>/{with_skill,without_skill}/{outputs,timing.json,grading.json}` + `iteration-<N>/benchmark.json` + `iteration-<N>/report.md`.
- `test_skills_create_tdd_gate_on_new_skill.py` — the skill-creator harness is itself subject to our TDD gate: proposing a new skill without at least one eval case is blocked.
- `test_skills_create_permission_sandbox.py` — executor subagents run in worktree isolation with the same FS sandbox as Phase 7.
- `test_skills_create_snapshot_pinned.py` — every `benchmark.json` carries a Phase-12 `HarnessSnapshot` fingerprint for reproducibility.

**Implementation.**
- `lyra_skills/creator/` subpackage: `interview.py`, `executor.py`, `grader.py`, `comparator.py`, `analyzer.py`, `benchmark.py`, `workspace.py`.
- Pydantic models: `SkillDraft`, `EvalPrompt`, `EvalAssertion`, `RunResult`, `Grading`, `ComparatorVerdict`, `Benchmark`, `AnalystReport`.
- `lyra skills create [--from-conversation <session-id>] [--from-scratch] [--workspace <path>] [--iterations N] [--budget $X]`.
- Reuses Phase 7 subagent orchestrator (worktrees + FS sandbox + 3-way merge); every eval run is a subagent.
- Reuses Phase 12 `HarnessSnapshot` on every benchmark artifact.
- Interview / grader / comparator / analyzer prompts live in `lyra_skills/creator/prompts/` as in-tree SOUL-style skills the creator itself loads.

**DoD.**
- `lyra skills create --from-scratch --workspace /tmp/test-skill` completes a full 3-eval / 2-iteration loop end-to-end with mock LLM, ending in a registered skill under `.lyra/skills/`.
- Benchmark.json schema validates the 4 shipped packs re-evaluated end-to-end; `pass_rate` is stable under fixed seed (bootstrap CI ≤ 5pp wide).
- Creator harness runs under the full TDD gate — no eval-free skill admission possible.
- `ruff` + `pyright` clean; 15+ new tests.

**Trade-offs.**
- We do **not** ship a web viewer in v1.7. Output is a Rich-rendered Markdown `report.md` + the JSON artifacts; Anthropic-schema-compatible so their `eval-viewer/generate_review.py` can also read our files. HTML viewer deferred to v2.
- Interview stage uses the active session's model; large cost variance if the user picks a premium model. Budget knob: `--interview-budget $1` (default).
- Comparator requires a **different-family** judge by default (reuse evaluator-family detection from Phase 5). Same-family is allowed with explicit `--comparator-family-same` and a `degraded_comparator=same_family` tag in retro.

---

### Phase 20 — Reuse-first router: hybrid retrieval + confidence gating (week 3)

**Scope.** Replace the bag-of-stems router with a three-stage retriever — BM25 (cheap), dense embeddings (semantic), description match (metadata) — that returns a confidence score, a top-K with rationale, and an **explicit `NO_MATCH` verdict** when no candidate clears the threshold. This closes the "undertrigger silently" gap.

**Red tests first.**
- `test_router_bm25_match.py` — exact-match query → top-1 skill at confidence ≥ 0.9.
- `test_router_embedding_match.py` — semantic-similar query ("change this function" vs "edit") → top-1 at ≥ 0.6.
- `test_router_hybrid_reranker.py` — BM25 + embedding scores fused via reciprocal-rank fusion; results stable under fixture.
- `test_router_confidence_threshold.py` — queries below τ=0.4 return empty list + `RouteVerdict.NO_MATCH`; `--force-route` overrides with visible `degraded_route=no_match_forced` tag.
- `test_router_ambiguous_query.py` — query that matches 2 skills equally → returns both with `VerdictKind.AMBIGUOUS` + disambiguation prompt text.
- `test_router_calibration.py` — on a held-out 200-query labelled corpus, router confidence is calibrated (Brier score ≤ 0.15); regression guard in CI.
- `test_router_trigger_explanation.py` — every returned match carries an `explanation` field citing the top-2 matching description tokens or embedding-neighbour phrases.
- `test_router_backward_compat.py` — existing code paths that call `router.route(query)` still work; the new structured `router.route_v2(query) -> RouteResult` is additive.

**Implementation.**
- `lyra_skills/router_v2.py` — new hybrid router; old router stays as fallback for opt-outs.
- Embeddings: default **local** BGE-small-en-v1.5 (~130 MB, CPU-fine), with optional OpenAI / Cohere adapters; the embedding index is a SQLite-FTS5 + HNSW hybrid living in `~/.lyra/skills/_index/`.
- Confidence = RRF-fused rank-to-score, recalibrated per-install on skill registration.
- `RouteResult = {matches: [(skill, score, explanation)], verdict: MATCH | AMBIGUOUS | NO_MATCH}`.
- CLI: `lyra skills route "<query>" [--top-k N] [--threshold 0.4] [--explain]`.

**DoD.**
- On a labelled 500-query corpus (built from our existing trajectories + Phase 21 trigger evals): top-1 correct ≥ 82%, top-3 correct ≥ 95%, `NO_MATCH` precision ≥ 90%.
- Router latency ≤ 60 ms p95 on ~50 skills with local embedder on M3.
- First-install embedding index build ≤ 15 s for the 4 shipped packs.

**Trade-offs.**
- Local embedding model is +130 MB. `lyra-skills[no-embed]` extra drops it (router falls back to BM25+description; quality degrades visibly, measured in benchmarks).
- Calibration is per-install — new skills shift the distribution. Recalibration runs on every `skills install` / `skills create` ingest.
- All embedding inference is local; `lyra doctor` warns if an opt-in remote embedder is configured without `--allow-remote-embed`.

---

### Phase 21 — Description optimizer + triggering evals (week 3, overlap)

**Scope.** Direct port of Anthropic's `scripts/run_loop.py` pattern, adapted to our CLI surface and safety rails. Every shipped skill can have its description auto-tuned for trigger accuracy without touching the body.

**Red tests first.**
- `test_trigger_eval_schema.py` — eval set JSON: `[{query, should_trigger: bool, category?, notes?}]`; rejects queries under 20 chars (Anthropic's "bad eval queries" rule codified).
- `test_trigger_eval_run.py` — on a fixture skill + 20-query eval set, each query is run 3× against the current router; per-query trigger rate computed; overall `trigger_pass_rate` and `false_trigger_rate` surfaced.
- `test_trigger_optimizer_train_test_split.py` — 60/40 split with fixed seed is reproducible; best description selected by **test** score, not train (prevents overfit).
- `test_trigger_optimizer_no_body_edits.py` — optimizer only proposes frontmatter diffs; body is frozen (schema-enforced).
- `test_trigger_optimizer_converges.py` — on a pathological "undertriggers" fixture, 5 iterations raise trigger rate from ≤ 30% to ≥ 80%; regression guard on the final score.
- `test_trigger_optimizer_rollback.py` — if the best candidate regresses on should-not-trigger (false-trigger rate rises above baseline + 10pp), the optimizer aborts and keeps the current description.
- `test_skill_pushy_lint.py` — linter flags descriptions without "use when..." phrasing and flags "pure intent descriptions" that don't mention user phrases; documented in `lyra skills lint`.

**Implementation.**
- `lyra_skills/trigger/` subpackage: `eval_runner.py`, `optimizer.py`, `lint.py`.
- `lyra skills trigger-eval <skill> --eval-set path/to/eval.json` — run once, report.
- `lyra skills optimize-description <skill> [--max-iter 5] [--budget $1]` — full loop, `--dry-run` by default; `--apply` is explicit.
- `lyra skills lint` — frontmatter quality check (pushy-style nudge, length, duplicate synonyms across skills).
- Optimizer proposer is a dedicated "description-engineer" SOUL.

**DoD.**
- The 4 shipped skill packs all score ≥ 85% trigger-pass on a 20-query eval set after one optimize run; false-trigger rate ≤ 15%.
- Running `optimize-description` is idempotent: if already optimized, it says "no improvement, skipping" and exits 0.

**Trade-offs.**
- Optimizer edits frontmatter automatically on `--dry-run`-by-default; `--apply` is explicit, mirroring how our extractor already gates promotion.
- Cost: ~30 LLM calls per skill per optimize run. Budget gate enforced; cost estimate surfaced before running.

---

### Phase 22 — In-session skill synthesis + bundled-script detection (week 4)

**Scope.** The feature the user asks for explicitly: *"create necessary skills when doing tasks."* The agent notices repetition during a real session, queues a proposal silently, surfaces it on `/retro` or `/status`. **Absorbs what was v2 Phase 20 (Self-refining skills)** — retirement/refinement proposals land in the same inbox as new-skill creation, unified lifecycle surface.

**Red tests first.**
- `test_insession_repetition_detector.py` — on a fixture HIR with 3 similar tool-call sequences (same 4-tool pattern within 50 turns), detector emits a `SkillProposalSignal` with pattern, representative trace slice, and occurrence count.
- `test_insession_bundled_script_detector.py` — when ≥ 2 subagent runs wrote structurally-similar Python helpers (AST-diff distance ≤ 0.2), detector surfaces it; skill proposal includes the common script as a bundled asset.
- `test_insession_queue_silent_default.py` — default behaviour: proposal goes to `.lyra/skill-proposals.jsonl`; no interruption mid-run, even in `plan` or `retro` mode. Surfaces on next `/retro` or `/status`.
- `test_insession_opt_in_interactive.py` — `--interactive-skill-capture` flag (or `interactive_skill_capture: true` in `.lyra/policy.yaml`) enables inline prompts; still blocked in `run` mode.
- `test_insession_synthesis_enters_creator.py` — on `y` to an inbox proposal, the interactive shell enters a `/creator` sub-mode that reuses the Phase 19 creator engine with the repeated-pattern trace slice as seed; on `n`, signal is kept in inbox with `rejected` flag; on `snooze`, suppressed for N sessions.
- `test_insession_extractor_integration.py` — the Phase 6 extractor is rewired: its output is now a `SkillProposalSignal`, not a direct `SkillManifest`. Proposals flow through Phase 19's creator engine uniformly.
- `test_insession_attribution_shapley_lite.py` — `shapley_lite` attribution (position-based + rule-based) runs on every skill invocation; `lyra skills doctor` surfaces attributed-success + recommended action. No silent overwrite.
- `test_insession_refinement_proposal.py` — a skill below 50% attributed-success over 20 invocations triggers a `refine` proposal; the proposal is a diff against the SKILL.md with rationale and user-visible before it lands.
- `test_insession_retirement.py` — below 30% over 40 invocations → `retire` proposal in the same inbox; user can still keep manually.
- `test_insession_council_prevents_fork.py` — two independent refinement proposals on the same skill cannot both land concurrently; council (= human user by default) arbitrates.

**Implementation.**
- `lyra_skills/insession/` subpackage: `detector.py` (repetition + bundled-script), `proposals.py` (durable inbox with status + `{new, refine, retire}` kinds), `lifecycle.py` (refine + retire + council).
- HIR events already carry tool-call shapes; repetition detector hashes `(tool_name, top-level arg shapes)` tuples and looks for ≥ 3 repeats within a configurable window (default 50 turns).
- Bundled-script detector uses Python `ast` module: parse all scripts written in a session, compute AST-node-class histogram distance; if < 0.2, propose bundling.
- Interactive shell gains `/creator` and `/skills proposals` slash commands (Phase 13 registry extended).
- `lyra skills proposals [--apply] [--inbox .lyra/skill-proposals.jsonl]` — batch review surface, suitable for `/retro` flow.
- Skill metadata gains `first_seen`, `invocations`, `attributed_successes`, `last_refined_at` fields (prepares Phase 26 federated registry metadata too).

**DoD.**
- On a 50-session dogfood, the detector produces ≥ 3 meaningful proposals (human-rated useful); zero proposals flagged as spam (false-positive rate = 0 on the sample).
- Captured skills that pass the Phase 19 creator loop are usable in the same session they were captured (router re-indexed on registration).
- Shipped skill packs get ≥ 200 attribution datapoints in the dogfood; `skills doctor` recommends at least one refinement and one retirement; human review sanity-checks recommendations.
- False-positive retirement rate ≤ 5% on a held-out set of manually-labelled "good" skills.

**Trade-offs.**
- Default is **queue silent** (decided in v1.7 planning). Interrupting the user mid-session hurts flow; proposals surface on `/retro` or `/status`. Explicit `--interactive-skill-capture` opts into mid-run prompts for users who want them.
- Bundled-script detection is AST-shallow; it will miss semantically identical scripts with different variable names + structure. Documented. v2 may adopt tree-edit-distance or learned code similarity.
- Repetition detector's "3+ occurrences" threshold is tunable via `.lyra/policy.yaml`. Too low = noise; too high = miss obvious captures. We ship `3` as the default based on Anthropic's informal guidance; telemetry will refine.
- Attribution (`shapley_lite`) is imperfect by design; v3 may adopt principled causal attribution. We'd rather ship imperfect attribution + human review than perfect attribution delayed.

---

### Phase 23 — NGC-inspired memory interoception: grow-then-evict compactor (week 5–6)

**Scope.** Rebuild the context compactor from "continuous type-aware reducer" into a grow-then-evict cycle with budget-aware interoception, block-level eviction units, LLM-driven rerank, outcome-reward logging, and replay masks. Direct harness-level adaptation of [Li et al., arXiv:2604.18002](https://arxiv.org/abs/2604.18002). We are **not training a policy** in v1.7 — we build the infrastructure so a future NGC-style fine-tune has clean data and clean hooks (deferred to v3).

**Red tests first.**
- `test_compactor_cadence.py` — given cadence δ tokens, eviction rounds fire exactly at multiples of δ; no continuous compaction between rounds.
- `test_compactor_block_level.py` — HIR events are grouped into "blocks" by conversation turn (user msg + assistant msg + tool calls + tool responses = 1 block); eviction selects blocks, never individual events within a block.
- `test_compactor_budget_meter_in_soul.py` — SOUL context includes `budget_used: X/Y tokens`, `next_compaction_in: Z turns`, `last_evicted_blocks: N`. Agent can read it mid-session (we grep the rendered SOUL for these fields).
- `test_compactor_scorer_last_w_turns.py` — block-ranking prior: blocks referenced by the last w=5 turns get a score boost (NGC's "attention-score proxy" at harness level). Reproducible under seed on a HIR fixture.
- `test_compactor_llm_rerank.py` — when cadence hits, an LLM rerank call takes `(remaining blocks, current plan, recent turns, budget)` and returns a keep-set; keep-set respects the budget; decision logged as a HIR `compactor.evict` event with `rationale`.
- `test_compactor_replay_mask.py` — each `compactor.evict` HIR event carries enough information to reconstruct "what the agent saw" at any step; `lyra session show --step N --contemporaneous-view` renders the contemporaneous view.
- `test_compactor_outcome_logging.py` — every session's final verdict + the list of compaction rounds + kept/evicted blocks get joined into `compactor-outcomes.jsonl`. This is the training corpus for any future learned policy; we don't train on it in v1.7.
- `test_compactor_vs_v1_parity.py` — on the golden corpus (100 tasks) with a 16K budget: new compactor ≥ v1 compactor in success rate (within 2pp); median peak tokens ≥ 25% better.
- `test_compactor_budget_breach.py` — if a step would exceed B even after a scheduled eviction, a compactor round fires *early* (grow-then-evict doesn't wait for the cadence when budget is about to be breached).
- `test_compactor_no_soul_eviction.py` — SOUL pin tier is never eligible for eviction (reuses block 06 pin).
- `test_compactor_llm_failure_fallback.py` — LLM rerank returning malformed JSON falls through to the v1 type-aware compactor and logs `degraded_compactor=llm_failed`.

**Implementation.**
- `lyra_core/context/ngc_compactor.py` — new `CompactionPolicy` interface with `propose_evictions(blocks, budget, plan, recent_turns) -> KeepSet`. Default implementation: LLM call with structured-output schema.
- `lyra_core/context/blocks.py` — groups HIR events into blocks, assigns block IDs, exposes `block_weight_from_recent_turns(w=5)`.
- `lyra_core/context/interoception.py` — injects `budget_used / next_compaction_in / last_evicted` into SOUL's runtime substitution surface (the live render, not the file).
- HIR additions: `compactor.round.start`, `compactor.round.end`, `compactor.evict` (per-block).
- `lyra session show --step N` gains a `--contemporaneous-view` flag that reconstructs what the agent saw at step N using the replay-mask artifacts.
- `compactor-outcomes.jsonl` always emitted; `--replay-masks` opt-in for the heavier artifact (~200 KB per session).
- `lyra_core/context/compactor.py` (v1) stays as the fallback; `lyra doctor` reports which is active.

**DoD.**
- On the golden corpus at B=16K: success rate parity with v1 ± 2pp; **median peak tokens down ≥ 25%** (the NGC-flavoured win).
- On LoCoEval (Phase 12): 50-turn conversations complete without budget overflow at B=32K with ≥ 55% requirement coverage (up from ≥ 50% in v1.5 target).
- `compactor-outcomes.jsonl` is generated on every session with kept/evicted trace + final verdict; we ship a 1000-session corpus with the release (sanitized, PII-masked via Phase 16 mask).
- Retro view renders compaction rounds inline with a "what was forgotten" annotation.

**Trade-offs.**
- LLM-in-the-loop compactor adds cost per session: 1 LLM call per compaction round. On a 40-turn session at cadence δ=10 turns, that's 4 calls ≈ $0.02 extra. Budget gate in `doctor`.
- We are **not** training a compaction policy in v1.7. The outcome log is infrastructure for a future NGC-style fine-tune (v3 aspirational). We are explicit about this.
- Replay masks are optional artifacts — off by default (adds ~200 KB per session). `--replay-masks` opt-in; `retro --replay` requires them.
- Grow-then-evict means the compactor never touches context between cadence boundaries. Budget-breach paths (test above) catch runaway cases; documented.
- SOUL pin is hard-enforced never-evicted; rerank only operates on non-SOUL blocks. Fall-through to v1 compactor on any schema-parse failure with `degraded_compactor=llm_failed` tag.

---

### v1.7 exit criteria

- All 5 phases green in CI on Python 3.10/3.11/3.12.
- **Router correctness** (Phase 20 labelled corpus): top-1 ≥ 82%, `NO_MATCH` precision ≥ 90%, Brier ≤ 0.15.
- **Creator loop** (Phase 19) runs end-to-end on mock LLM in ≤ 30 s; on real LLM completes a 3-eval / 2-iteration cycle in ≤ 10 min at ≤ $0.50 median.
- **Description optimization** (Phase 21) raises trigger-pass on all 4 shipped packs to ≥ 85% with false-trigger ≤ 15%.
- **In-session synthesis** (Phase 22) produces ≥ 3 human-rated-useful proposals across a 50-session dogfood; zero false positives on a blind audit. `skills doctor` recommendations accepted rate ≥ 40%.
- **NGC compactor** (Phase 23) ≥ 25% median peak-token reduction at ≤ 2pp success regression on golden; LoCoEval requirement coverage ≥ 55%.
- **CHANGELOG** + **README** + **`docs/roadmap-v1.5-v2.md`** updated; `v0.3.0` tag cut.
- Full test suite ≥ 400 green (310 today + ~90 across 5 phases, conservative estimate).

---

## 2. v2 — "Self-Evolving Harness" (≈ 14 weeks)

**Theme.** Stop hand-tuning. Let the harness search its own design space, let the community share infrastructure, let sessions span model generations. v2 is the paper-grade bet: Meta-Harness outer loop, arena infrastructure, federated skill registry, and long-horizon checkpointing. Plus the already-earmarked v2 items (training-arena, Multica team mode, federated retros, Agentic Wiki cross-repo).

**Sequencing note.** v1.7 absorbed what was previously v2 Phase 20 "Self-refining skills with outcome-based lifecycle" — attribution, refinement, and retirement now land in v1.7 Phase 22 alongside creation. v2 picks up with Meta-Harness; phases are renumbered (19→24, 21→25, 22→26, 23→27, 24→28).

**Meta-DoD for v2.** Lyra optimizes its own harness on a user's repo and a user's skill pack over a weekend and produces a harness that beats the v1.7 hand-tuned default on the user's private corpus by ≥ 5pp with ≥ 95% confidence. All without any code change from the user.

### Phase 24 — Meta-Harness: self-optimizing harness (week 11–14)

**Scope.** Direct implementation of the Meta-Harness pattern (Lee et al., 2026) adapted for coding agents. An outer-loop coding agent proposes harness edits by reading the filesystem of prior candidate harnesses (code + scores + execution traces), evaluates proposals on a held-in corpus, and keeps a Pareto frontier over (success_rate, cost_per_task, p95_latency).

**Red tests first.**
- `test_meta_harness_proposer.py` — proposer agent reads `/harnesses/prior_runs/` filesystem, proposes a new harness variant, writes it to `/harnesses/candidates/NNN/`, returns exit code 0.
- `test_meta_harness_evaluate.py` — evaluator runs the candidate on N-task search set, writes `scores.json`, `trace/*.jsonl`, `cost.json` to the candidate's dir.
- `test_meta_harness_pareto.py` — Pareto frontier correctly updated after each evaluation; dominated candidates retained in the archive but not selected for parent duties.
- `test_meta_harness_interface_validation.py` — a candidate that doesn't implement `HarnessPlugin` is rejected before any search-set eval (save budget).
- `test_meta_harness_no_test_leak.py` — the proposer never receives held-out test-set scores; red-build if it does (static graph check).
- `test_meta_harness_budget.py` — total evaluation budget respected; graceful stop with best-so-far frontier when budget hits.

**Implementation.**
- `lyra_core/meta/filesystem.py` — canonical layout for the candidate archive:
  ```
  .lyra/meta/
    ├── search_set/            # read-only corpus
    ├── test_set/              # read-only, oracle-only
    └── candidates/
        └── NNN_<slug>/
            ├── harness.py     # the proposed plugin
            ├── rationale.md   # proposer's reasoning
            ├── scores.json    # search-set metrics
            ├── cost.json
            └── trace/         # full HIR for each task
  ```
- `lyra_core/meta/proposer.py` — launches a coding-agent Lyra session as the proposer, with its own SOUL.md ("You are a harness optimizer. Read prior candidates. Propose a new harness. Write rationale.md explaining your hypothesis.") and access to the filesystem via native Read/Glob/Grep only (no write to `/test_set`).
- `lyra_core/meta/pareto.py` — multi-objective frontier maintenance over (success_rate ↑, cost_per_task ↓, p95_first_reply ↓).
- `lyra meta optimize --search-set <path> --test-set <path> --budget N` CLI command.

**DoD.**
- On a new repo with a 40-task search set, `lyra meta optimize --budget 30` produces a Pareto frontier of ≥ 5 candidates in ≤ 8 hours; best candidate beats the v1.7 default by ≥ 5pp on the held-out 10-task test set with bootstrap 95% CI excluding 0.
- Pareto frontier can be `lyra meta apply <candidate-id>` — installs that harness as the repo default.

**Trade-offs.**
- This is the single most expensive phase in the whole roadmap. Budget: ~$100 of API spend per full optimization run on typical repos; users must opt in explicitly.
- The proposer writes harness code; code review is mandatory before `meta apply`. We treat this exactly like a skill PR — human gate is the promoter (block 09 pattern, reused).
- The meta loop is itself an Lyra session. We dogfood hard: the meta loop must pass our own TDD gate, verifier, safety monitor. No backdoors for the "special" meta role.

---

### Phase 25 — Arena mode: blind A/B harness tournaments (week 15)

**Scope.** Inspired by Windsurf Wave 13's Arena Mode. Ship `lyra arena` — a blind comparison tool that runs two harness configurations (or two skill packs, or two model routers) on the same task set, hides identities, and surfaces the results for user voting or automatic adjudication.

**Red tests first.**
- `test_arena_double_blind.py` — configs A and B are randomized per task; reports include verdicts bucketed by a/b label, not by config name.
- `test_arena_adjudicate_auto.py` — for tasks with a ground-truth oracle, auto-adjudication works; user only votes on ambiguous tasks.
- `test_arena_budget_stop.py` — arena respects a per-config budget; stops and declares undecided if budget exhausted.
- `test_arena_report_shape.py` — final report has: elo-like rating, per-category breakdown, cost curves, and **citations to trace artifacts** so the loser can be diagnosed.

**Implementation.**
- `lyra_core/arena/` — runner, adjudicator, reporter.
- `lyra arena --a <config.yaml> --b <config.yaml> --corpus <path>` CLI.
- Tight integration with the Meta-Harness archive: every candidate that enters the Pareto frontier automatically gets a cheap arena run against the current default, generating human-visible evidence before `meta apply`.

**DoD.**
- Arena run on a 30-task corpus completes in ≤ 2 hours on local hardware with two harness configs; report is defensible (citations resolve, each verdict is reproducible).

**Trade-offs.**
- Arena adjudication risks systematic bias if the auto-judge shares family with one config. We enforce different-family for the auto-judge (reusing A.8's logic). Users can override; the override logs `degraded_arena=same_family`.

---

### Phase 26 — Federated skill registry + signed skill packs (week 16)

**Scope.** Shared agent infrastructure direction from the externalization survey. Users can publish skill packs to a Git-based registry, consume others', with cryptographic signing and policy-based admission.

**Red tests first.**
- `test_skill_registry_install.py` — `lyra skills install github.com/user/pack` resolves, verifies signature, sandboxes the install, and makes skills discoverable.
- `test_skill_signing.py` — unsigned packs require `--allow-unsigned`; log a warning; telemetry flag in retro.
- `test_skill_policy_admission.py` — `.lyra/skill-policy.yaml` can deny packs by author, ID, or allowlist; CI install refuses to bypass policy.
- `test_skill_vendoring.py` — a pack can be vendored (copied in-tree) vs. linked (installed under `~/.lyra/skills/_vendor/`); both work, vendored wins precedence.
- `test_skill_supply_chain.py` — a pack that carries a network-effecting hook (e.g. one that calls an external service at load time) is flagged and requires explicit allow.

**Implementation.**
- `lyra_skills/registry/` — resolve, fetch, verify, install.
- Signing uses sigstore by default; fallback to GPG for air-gapped orgs.
- `.lyra/skill-policy.yaml` with allowlist / denylist / pattern rules.
- `lyra skills {search,install,update,remove,audit}`.

**DoD.**
- We publish an `lyra-skills-starter` registry with our 4 shipped packs as the first entries and a published pack review policy.
- A third-party pack installed via registry runs under the same TDD-gate + permission bridge as in-tree skills; no bypass.

**Trade-offs.**
- Package supply-chain attack is a real risk; sigstore mitigates. We do not ship a payment / marketplace layer (explicitly out of scope per C.4 v1). Registry remains free & Git-based.
- Skills with dynamic imports or network calls at load time are hard to sandbox fully; policy default **denies** them and requires explicit allow with visible warning banner (similar to MCP trust banners from phase 10).

---

### Phase 27 — KLong / long-horizon checkpointing + resume across model generations (week 17–18)

**Scope.** Support tasks that legitimately exceed a single context window budget by checkpointing + resuming. Plus: resume across model upgrades without losing episodic context. Paper anchor: [KLong 2026].

**Red tests first.**
- `test_long_session_checkpoint.py` — a session can be paused at any step boundary; every persisted artifact (trace, state.md, plan, skill-usage) is self-contained for resume.
- `test_long_session_resume.py` — `lyra resume <session-id>` reconstructs context and continues; the continuation's trace digest is continuous with the original.
- `test_resume_across_model.py` — pausing on model A and resuming on model B works; A's reasoning is preserved as episodic memory; B is briefed on A's decisions without re-doing them.
- `test_checkpoint_invalidation.py` — a checkpoint becomes invalid if source files changed in incompatible ways; resume rejects with a clear report; user can `--force-resume` with tag.

**Implementation.**
- `lyra_core/session/checkpoint.py` — serializes active context, state.md, plan progress, pending hooks, subagent roster.
- `lyra resume <session-id>` reconstitutes.
- Model-family detection at resume time; the briefing prompt is adjusted per family (we have this plumbing from block 11 evaluator; reuse).

**DoD.**
- A 200-step session across 3 checkpoints completes with the same final audit-trail quality as a single 200-step run (verifier verdicts equal).
- Cross-model resume preserves plan semantics; the second leg doesn't re-explore what the first leg already concluded.

**Trade-offs.**
- Full state serialization is ~3 MB typical; storage grows fast for org-level usage. We ship a rolling GC (default keep 50 sessions with checkpoints, 200 without).
- Cross-model resume is imperfect; some styles / rubrics differ per family. We surface `resumed_from_model=X; drift_score=Y` tags in retro.

---

### Phase 28 — v2 already-earmarked items (week 19–20)

Covers the four items already listed as v2 in `roadmap.md`'s Post-v1 line:

1. **Agent-World inspired training arena integration** — a training-arena adapter so users who have a fine-tune pipeline can feed Lyra's executable task corpus into it. We do not ship our own training stack (B.18 stands: API-first). But we expose a SWE-smith-compatible corpus exporter + a DPO-compatible pair exporter over our trace archive, **plus the `compactor-outcomes.jsonl` corpus from v1.7 Phase 23** as a ready-made NGC-style training input.
2. **Multica-style team orchestration** — the "host multiple CLI adapters at runtime" feature from B.17. Ships as `lyra team {claude,gemini,cursor,lyra} --task "…"` with a light coordinator that assigns tasks per-CLI strengths.
3. **Federated retros** — orgs can share retros (with PII masked by v1.5 masking) into a shared retrospective archive for cross-team learning.
4. **Agentic Wiki cross-repo sharing** — the repo wiki from Phase 18 becomes portable: `lyra wiki publish` pushes to a shared wiki service; other users can `wiki import` to prime their context before working in a repo they haven't seen.

Each is a ≤ 3-day phase on top of the infrastructure already in place by Phase 26.

**DoD for Phase 28.**
- Training-arena: SWE-smith-format export runs on our golden corpus and an external fine-tune pipeline can consume it round-trip. `compactor-outcomes.jsonl` export validates against an NGC-compatible schema.
- Multica: a 5-step task that plays to Claude's strengths + Gemini's long-context advantage completes; handoff points are user-approvable.
- Federated retros: a shared retro drop into a community archive surfaces to a second team via `lyra retro search` with no PII leaks on a 100-session audit.
- Agentic Wiki: a wiki from repo A imported into repo B improves first-day productivity (measured by time-to-first-approved-PR) by ≥ 20% on a 10-person dogfood study.

**Trade-offs.**
- Multica "team mode" is still explicitly NOT a production scheduler; it's a v2 research surface. If users want production multi-CLI orchestration they should wire their own (or wait for v3).

---

### v2 exit criteria

- Meta-Harness produces a harness that beats the v1.7 default by ≥ 5pp on a user-held-out test set.
- Skill lifecycle matured from v1.7: on the 4 shipped packs, ≥ 90% of `skills doctor` recommendations have been processed (accepted or explicitly rejected); ≥ 3 new skill packs exist in the federated registry beyond our own.
- Arena becomes a surface external teams use to evaluate their own configs (measured: at least 3 external contributors ran `lyra arena` within 90 days of v2 release).
- Federated skill registry has ≥ 10 pack authors (us + 9 community) within 90 days.
- SWE-bench Pro public submission is made; we are in the published top-10 open-source scaffolds on Pro with Opus 4.6-class models.
- `v0.5.0` tag cut; PyPI release; upgrade notes published.

---

## 3. v3 and beyond (aspirational)

These are not planned milestones; they are the trajectory if v2 goals are met.

- **Joint-RL over 5 atomic skills** (arXiv:2604.05013 follow-ups) — fine-tune a small coding model on our corpus with composition-aware RL. Only makes sense once the Meta-Harness optimizer has produced stable baseline harnesses worth training against.
- **Non-LLM safety monitor tier** — a learned classifier for pattern recognition, reserving LLM for only low-confidence cases. Cost reduction play.
- **Cross-organization federated retros with differential privacy** — share trajectory statistics without sharing traces.
- **Lyra as a first-class MCP server for third-party IDEs** — Cursor/Windsurf/Zed attach to a local Lyra daemon for hooks, permissions, TDD gate, retros, without owning the runtime.
- **Repo-level fine-tuning ("memorize the project")** — once local GPU + LoRA at this scale is cheap, a per-repo model head becomes the fourth memory tier.
- **Formal verification integration** — hook the verifier into external provers (Lean, Coq) for crypto / safety-critical surfaces.

---

## 4. Risk register (schedule + technical)

| Risk | Milestone | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| SWE-bench Pro harness API churn | v1.5 | M | H | Pin to a Scale-AI Pro spec version; track their CHANGELOG; release of our adapter is tied to Pro-version tags |
| CodeAct sandbox escape | v1.5 | L | H | AST allowlist + runtime tracing as v2 backstop; bug bounty before public v0.2 release |
| Rubric PRM cost blowout | v1.5 | M | M | Budget gate + fallback to binary verifier; user-visible `degraded_verifier` tags; cost monitor alerts |
| Creator loop too expensive for casual use | **v1.7** | M | M | Budget gate (`--budget $`); mock-LLM mode for CI; short-circuit option (`--fast-iterate` = 1 eval, no A/B) |
| Router embedding model drift over 6 months | **v1.7** | M | L | BGE-small is stable; rebuild index on version bump; `doctor` flags mismatches |
| In-session prompts interrupt flow | **v1.7** | M | M | Default queue-silent; explicit opt-in for interactive; retro-time batch review |
| Bundled-script detector false positives bundle junk | **v1.7** | M | L | Human-review gate is mandatory before registration; AST-histogram threshold tunable |
| NGC compactor LLM rerank hallucinates "keep SOUL" of the wrong thing | **v1.7** | L | H | SOUL pin is hard-enforced never-evicted; rerank operates only on non-SOUL blocks; fall-through to v1 compactor on schema-parse fail (`degraded_compactor=llm_failed` tag) |
| Trigger eval queries diverge from real usage | **v1.7** | M | M | Mix queries come from shipped fixtures + user-contributed; CI lints for length / specificity (Anthropic's "bad vs good query" rules codified) |
| Description optimizer converges on "pushy" spam descriptions across shipped packs | **v1.7** | M | M | Lint rule: duplicate synonyms across skills flagged; manual review before apply |
| Skill lifecycle attribution error | **v1.7** | H | M | `shapley_lite` is a baseline, not truth; human council arbitrates; attribution confidence surfaced in `skills doctor` |
| Meta-Harness compute overruns | v2 | H | M | Per-optimization budget cap; early-stop on stalled frontier; dry-run that estimates cost before any eval |
| Federated registry supply-chain attack | v2 | M | H | Signing mandatory, network-effecting hooks default-denied, policy allowlist, audit trail + revocation list |
| Remote runner vendor lock-in | v1.5 | L | M | Ship three adapters + clean protocol; local Docker adapter is the escape hatch |
| PII NER model false negatives | v1.5 | M | H | Regex-first (high recall), NER as second pass (high precision); red-team PII corpus grows with each incident |
| Arena adjudicator bias | v2 | M | M | Different-family adjudicator enforced; human voting fallback on ties; published agreement-rate against human raters |
| Long-horizon checkpoint fragility | v2 | M | M | Checkpoint invalidation is explicit, not silent; `--force-resume` with tag; test corpus includes deliberately-invalidated checkpoints |
| v1.7 timeline overruns | **v1.7** | M | M | Phase 23 (NGC compactor) is the biggest; decomposable — we can ship v0.3 with Phases 19–22 only and defer NGC to v0.4 if bandwidth slips |
| v2 timeline overruns | v2 | M | M | Phases 24 (Meta-Harness) and 28 (v2 already-earmarked) are the biggest; decomposable — we can ship v0.5 with Meta-Harness + arena and v0.6 with registry + KLong if bandwidth slips |

---

## 5. Success metrics at v2

Targets relative to v1 baselines. v1.7 column added for the self-creating-harness milestone.

| Metric | v1 baseline | v1.5 target | v1.7 target | v2 target |
|---|---|---|---|---|
| Golden corpus success rate | ≥ 85% | ≥ 87% | ≥ 88% | ≥ 90% |
| Red-team sabotage recall | ≥ 90% | ≥ 94% | ≥ 94% | ≥ 96% |
| p95 first-reply latency | ≤ 3 s | ≤ 3 s | ≤ 3 s | ≤ 2.5 s |
| Median session cost | ≤ $0.25 | ≤ $0.22 | ≤ $0.20 (NGC compaction) | ≤ $0.20 |
| False-positive rate (safety monitor) | < 1% | < 0.8% | < 0.8% | < 0.5% |
| SWE-bench Pro (public corpus, our default harness, Opus-class model) | not reported | ≥ 40% | ≥ 44% | ≥ 48% |
| LoCoEval requirement coverage | not reported | ≥ 50% | ≥ 58% | ≥ 65% |
| **Skill trigger recall on curated eval set** | not measured | not measured | **≥ 80%** | ≥ 90% |
| **Skill creator: first-iteration benchmark pass rate** | n/a | n/a | **≥ 70%** (of rubric) | ≥ 80% |
| **Skill creator: converged pass rate (≤ 5 iterations)** | n/a | n/a | **≥ 90%** | ≥ 95% |
| **NGC compactor: peak KV proxy compression vs v1.5 compactor** | 1.0× | 1.0× | **≥ 1.5×** | ≥ 2× |
| **NGC compactor: success rate at fixed budget (dog-food corpus)** | baseline | baseline | **≥ baseline − 1pp** | ≥ baseline |
| **In-session skill proposals: acceptance rate at retro** | n/a | n/a | **≥ 60%** | ≥ 70% |
| Skill lifecycle: retirement false-positive rate | n/a | n/a | ≤ 5% | ≤ 5% |
| Arena: agreement with human raters | n/a | n/a | n/a | ≥ 85% |
| Meta-Harness: improvement over v1.7 default on user-held-out test set | n/a | n/a | n/a | ≥ 5pp with 95% CI |

---

## 6. Reading order for contributors

- Start with [`roadmap.md`](roadmap.md) for v0 → v1 context.
- Re-read [`architecture-tradeoff.md`](architecture-tradeoff.md) §B.9, §B.14, §B.18, §B.20 — those are the explicit "deferred to v2" items, now scheduled.
- Read this document.
- Pick up the phase whose tests are red; start by writing more red tests; implementation follows.
- Dogfood rule: every phase above must land its own features inside Lyra before declaring DoD. If the meta-loop can't use Meta-Harness on itself, Meta-Harness is not done.

---

## 7. Sources

Selected references, grouped:

**Public benchmark state-of-the-art (April 2026):**
- [Awesome Agents SWE-bench Leaderboard](https://awesomeagents.ai/leaderboards/swe-bench-coding-agent-leaderboard/), April 19 2026.
- [CodeAnt AI — "Understand the SWE-Bench Leaderboard 2026 in Depth"](https://www.codeant.ai/blogs/swe-bench-scores), April 13 2026.
- [Morph — "SWE-Bench Pro: why 46% beats 81%"](https://www.morphllm.com/swe-bench-pro).
- [Morph — "We Tested 15 AI Coding Agents (2026)"](https://www.morphllm.com/ai-coding-agent), March 2026.

**Scaffolds worth studying:**
- [OpenHands + CodeAct v3 architecture](https://docs.openhands.dev/openhands/usage/architecture/runtime) (71.6K stars, 470 contributors as of April 2026).
- SWE-agent, [Princeton NLP](https://github.com/SWE-agent/SWE-agent) — ACI design.
- Moatless Tools — [github.com/aorwall/moatless-tools](https://github.com/aorwall/moatless-tools) — minimal-context / symbol-level retrieval.
- Agentless — [arXiv:2405.15793](https://arxiv.org/abs/2405.15793) — 3-stage pipeline.
- Windsurf Wave 13 — Arena Mode + 5 parallel Cascade agents.
- Kilo Code — 4-mode UX (Architect/Code/Debug/Orchestrator).

**Research anchors:**
- **Meta-Harness**: Lee, Nair, Zhang, Lee, Khattab, Finn. "Meta-Harness: End-to-End Optimization of Model Harnesses." [arXiv:2603.28052](https://arxiv.org/abs/2603.28052), 2026.
- **SWE-TRACE**: Han et al. "Optimizing Long-Horizon SWE Agents through Rubric Process Reward Models and Heuristic Test-Time Scaling." [arXiv:2604.14820](https://arxiv.org/abs/2604.14820), 2026.
- **KLong**: "Training LLM Agent for Extremely Long-horizon Tasks." [arXiv:2602.17547](https://arxiv.org/abs/2602.17547), 2026.
- **LoCoEval**: "A Scalable Benchmark for Repository-Oriented Long-Horizon Conversational Context Management." [arXiv:2603.06358](https://arxiv.org/abs/2603.06358), 2026.
- **ACON**: "Optimizing Context Compression for Long-Horizon Agents." OpenReview 2026.
- **BACM-RL**: "Budget-Aware Context Management for Long-Horizon Search Agents." [arXiv:2604.01664](https://arxiv.org/abs/2604.01664), 2026.
- **Refute-or-Promote**: "Adversarial Stage-Gated Multi-Agent Review." [arXiv:2604.19049](https://arxiv.org/abs/2604.19049), 2026.
- **VeRO**: "An Evaluation Harness for Agents to Optimize Agents." [arXiv:2602.22480](https://arxiv.org/abs/2602.22480), 2026.
- **Externalization survey**: Zhou et al. "Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols, and Harness Engineering." [arXiv:2604.08224](https://arxiv.org/abs/2604.08224), April 2026.

**v1.7 anchors (new):**
- **Neural Garbage Collection (NGC)**: Li, Hamid, Fox, Goodman. "Neural Garbage Collection: Learning to Forget while Learning to Reason." [arXiv:2604.18002](https://arxiv.org/abs/2604.18002), Stanford, April 2026. The source paper for v1.7 Phase 23. Treats cache-eviction decisions as discrete actions sampled from the LM, jointly optimized with reasoning tokens via outcome-based RL. Block-level eviction at cadence δ, budget-aware interoception (tell the model its budget), replay masks for exact policy-gradient updates; 2–3× peak KV compression with strong accuracy (49.6% vs 21.2% next-best baseline on Countdown at 2.4× compression).
- **Anthropic Skill-Creator v2**: `anthropics/skills/skill-creator`, Anthropic public skills repo. [github.com/anthropics/skills/tree/main/skills/skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator). December 2025 release (4-agent loop = Executor/Grader/Comparator/Analyzer; iteration workspaces; `benchmark.json` artifacts; 60/40 train/test description optimizer). 121K stars, 176K installs at the time of v1.7 planning. The source pattern for v1.7 Phases 19–22.
- **Anthropic Agent Skills announcement** (Oct 16 2025): [www.anthropic.com/news/agent-skills](https://www.anthropic.com/news/agent-skills) — introduces Skills and establishes the "skill-creator as first skill" framing.
- **Anthropic engineering: "Equipping agents for the real world with Agent Skills"** ([www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), Oct 2025) — describes progressive disclosure, evaluations, iteration loop; the reference for v1.7 description optimizer ergonomics.
