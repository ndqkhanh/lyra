# Memento-Skills × Read-Write Reflective Learning — Lyra Phase O design memo

> Status: **adopted in v3.5.0**. This memo records what Phase O imported
> from <https://github.com/Memento-Teams/Memento-Skills> and from
> [arXiv:2603.18743](https://arxiv.org/abs/2603.18743), what we
> deliberately rejected, and how each decision maps onto Lyra's
> existing architecture. Future maintainers: when somebody asks
> "why didn't we add hybrid retrieval / a Qt GUI / agent-to-agent
> chat?" — read this first.

## TL;DR

Phase O is **not** a port of Memento-Skills. It is a careful filter
of one specific idea — *learn from your own action history, then
let that history bias future decisions* — onto Lyra's CLI-first,
stdlib-only, leaf-package-first architecture.

We took:

* the **Read-Write Reflective Learning** loop (RWRL),
* the concept of **per-skill utility / outcome scoring**,
* the **dream-daemon equivalent** that consolidates session
  history into new skills,
* the **failure-attribution** pattern that closes the loop on
  *user-visible* outcomes (rejected turns, not just LLM
  completion).

We rejected:

* hybrid BM25 + dense retrieval,
* PyQt GUI shell + multi-IM gateway,
* operator-facing fine-tuning,
* a separate vector store,
* tight coupling between "skill" and "tool".

The rest of this document is the receipts.

## What the sources actually say

### `Memento-Teams/Memento-Skills` (GitHub)

The repo bundles three loosely-coupled subsystems:

1. **Skill router** that picks SKILL.md packs by description match
   and lightweight retrieval.
2. **Reflective loop** that scores each skill's contribution to
   the *task*, persists the score, and uses it to bias future
   selection.
3. **Dream daemon** that runs offline over recent sessions and
   proposes either rewrites of existing skills (`reflect`) or
   brand-new skills consolidated from recurring patterns
   (`consolidate`).

Two integration surfaces ship around the core: a PyQt desktop GUI
and a multi-IM gateway. Neither is part of the core RWRL story —
they're operator UX.

### arXiv:2603.18743 — *Read-Write Reflective Learning*

The paper formalises the loop the repo demonstrates:

* **Read.** A decision step samples not just the current input
  but also a writable, monotonically growing log of past action
  outcomes.
* **Write.** Each step's *result* (success / failure / neutral)
  is appended to that log, attributed to the action that caused
  it.
* **Reflect.** Periodically, an off-line process consumes the log
  and either updates aggregated statistics (cheap) or rewrites
  the action set (expensive). The loop does **not** require a
  training pass — reflection is itself an action.

Three claims in the paper that drove Phase O design:

1. **Outcome attribution must come from the harness, not the
   model.** The paper notes that "model-completed" is a *very*
   noisy proxy for "task-succeeded", and that user-visible signals
   (rollback, retry, override) carry more reliable gradient than
   token-level loss.
2. **A small amount of recency in the utility metric beats a
   pure success-ratio.** Pure ratios reward stale veterans and
   freeze new skills out forever.
3. **Reflection is bursty, not continuous.** A "dream" pass once
   per session is enough; doing it inside every step destroys
   latency without improving choice quality.

## What Lyra imported, and where

| Source concept | Lyra surface (v3.5) | File / function |
|----------------|---------------------|-----------------|
| Skill outcome log | `SkillLedger`, JSON at `~/.lyra/skill_ledger.json` | `lyra_skills/ledger.py` |
| Outcome record | `SkillOutcome(kind ∈ {success, failure, neutral}, ts, session_id, turn, error_kind)` | `lyra_skills/ledger.py` |
| Utility metric | `utility_score(stats)` — success ratio + 24-hour recency boost; tie-broken by activation count, then recency | `lyra_skills/ledger.py` |
| Read at decision time | `select_active_skills(..., utility_resolver=...)` and `_build_utility_resolver` | `lyra_skills/activation.py`, `lyra_cli/interactive/skills_inject.py` |
| Write at turn end | `SkillActivationRecorder` listening on `TURN_COMPLETE` / `TURN_REJECTED` | `lyra_cli/interactive/skills_telemetry.py`, `driver.py::_wire_skill_telemetry_to_lifecycle` |
| Lifecycle event | `LifecycleEvent.SKILLS_ACTIVATED` carrying `{session_id, turn, activated_skills: [{skill_id, reason}, …]}` | `lyra_core/hooks/lifecycle.py` |
| Reflective rewrite | `lyra skill reflect <id>` (LLM-backed, dry-run by default, `--apply` writes `.bak`) | `lyra_cli/commands/skill.py::_call_llm_for_reflection` |
| Dream daemon | `lyra skill consolidate` (clusters recent prompts, asks LLM for new SKILL.md) | `lyra_cli/commands/skill.py::_cluster_prompts`, `_call_llm_for_consolidation` |
| Operator view | `lyra skill stats` Rich table or `--json` | `lyra_cli/commands/skill.py::stats` |

Two design tweaks Lyra made on top of the sources:

1. **`force_ids` always wins.** Memento's router lets utility
   override explicit invocation in some configurations; that's
   surprising in a CLI where the user typed the skill name.
   Lyra's resolver is purely a *tie-breaker*: explicit invocation
   bypasses it.
2. **The utility resolver is a dependency-injection seam.**
   `lyra-skills` is a leaf package — it must not import
   `lyra-cli` or even `lyra-core`. So `select_active_skills`
   accepts an optional callable rather than reaching into the
   ledger directly. The CLI builds the resolver and passes it
   in. Other consumers (tests, plugins, future SDK callers) can
   plug their own ranking in trivially.

## What Lyra rejected, and why

### Hybrid BM25 + dense retrieval

The Memento repo bundles `rank_bm25` and a sentence-transformer
backend for "semantic skill match". Phase O does not.

* **Cost.** Adding `rank_bm25` is fine; pulling in
  `sentence-transformers` is a hundreds-of-MB install for a CLI
  that prides itself on starting cold in <1s.
* **Existing surface.** Lyra already has progressive keyword
  activation (`select_active_skills`). The win from BM25 over
  exact-token match is real but small for the SKILL.md
  description style ("two-line imperative summary").
* **Pluggability.** The `utility_resolver` callable can wrap
  *any* ranking signal — including a BM25 score from a user
  plugin. So we shipped the seam, not the dependency.

### PyQt GUI / multi-IM gateway

Lyra is **CLI-first**. The CLI is the surface, not a side door.
Phase O surfaces (`stats`, `reflect`, `consolidate`) ship as
typer subcommands and reuse the existing Rich rendering, so a
GUI shell adds nothing the user can't already get with `lyra
skill stats --json | jq …`.

If somebody wants a desktop GUI later, the recommended path is to
build it *on top of* `LyraClient` (Phase N) plus the new
`SKILLS_ACTIVATED` lifecycle event — i.e. as a separate package,
not a checkbox in the harness.

### Operator-facing fine-tuning pipeline

Memento has a doc-only pathway for "use the success log to
fine-tune the underlying model". We're not even tempted:

* Lyra runs the harness, not the model. Multi-provider support
  (Phase L) is a hard constraint and fine-tuning a single
  vendor's checkpoint would break it.
* The reflective loop already gives most of the win at zero
  training cost — `lyra skill reflect` rewrites the skill text
  the model reads, which is the cheapest, most controllable
  intervention available.

### A separate vector store

Memento ships an optional FAISS / Chroma backend for "remember
arbitrary task transcripts". Phase O sticks to the SKILL.md
abstraction. Reasons:

* SKILL.md is human-curatable; embedded vectors are not.
* The "consolidate" path produces *new SKILL.md files* on disk
  rather than rows in a hidden DB, so the user can read, edit,
  delete, or git-track them.
* If you really want vector recall, plug it in via the standard
  tool registry — but it shouldn't be wired into the activation
  hot path.

### Tight coupling between "skill" and "tool"

Some Memento examples treat a skill as "an agent + a tool + a
prompt". Lyra keeps these separate by deliberate choice:

* Skills are advisory text the model reads.
* Tools are callable surfaces the model invokes.
* The agent loop is the kernel.

Conflating them leads to Skills that won't load on a different
model or with a different tool set. Phase O preserves the
separation: `SkillStats` is keyed by skill id only, never by
tool name.

## Failure-attribution rules (the part that really matters)

The single most important Phase O decision was *what counts as a
failure?* — because the utility score is only as good as the
signal feeding it.

We picked these rules:

1. **`TURN_COMPLETE` → success** for every skill that activated
   that turn. The model produced something, the user didn't
   reject it. Good enough.
2. **`TURN_REJECTED` → failure** with `last_failure_reason` set
   to the rejection reason. Slash-command revert, plan denied,
   permission refused, sandbox kill — all count.
3. **Tool errors do not directly attribute** to skills. A tool
   throwing is a tool problem; a skill that *recommends* the
   wrong tool will be punished anyway when the turn rejects.
4. **No partial credit.** A turn either succeeded or it didn't.
   The simpler rule was robust enough that we didn't need
   weighted attribution.

Open question for future phases: should skills that are
*advertised* but never *activated* count for anything? Right now
they don't, which means a skill catalog can drift toward
"frequently activated" rather than "actually useful". The
proposed answer is the `--include-zero` flag on `lyra skill
stats` (already shipped) plus an upcoming `lyra skill prune`
command to retire long-stale packs. Tracked separately.

## Pointer back

* Code: `packages/lyra-skills/src/lyra_skills/ledger.py`,
  `packages/lyra-cli/src/lyra_cli/commands/skill.py`,
  `packages/lyra-cli/src/lyra_cli/interactive/skills_telemetry.py`,
  `packages/lyra-cli/src/lyra_cli/interactive/skills_inject.py`.
* Tests: `packages/lyra-skills/tests/test_skill_ledger.py`,
  `packages/lyra-skills/tests/test_skill_activation.py`,
  `packages/lyra-cli/tests/test_skills_telemetry.py`,
  `packages/lyra-cli/tests/test_skill_command.py`,
  `packages/lyra-cli/tests/test_phase_o_smoke.py`.
* CHANGELOG: `v3.5.0 — Phase O: Reflective Learning`.
* User-facing docs: README §"Reflective Learning — skills that
  learn from themselves".
