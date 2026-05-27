---
title: Use the ReasoningBank
description: Practical recipes for inspecting, seeding, and operating Lyra's reasoning memory — from the CLI and from Python.
---

# Use the ReasoningBank <span class="lyra-badge intermediate">intermediate</span>

The ReasoningBank ships **on by default** in Lyra v3.0+: every
session-end trajectory is distilled to lessons and persisted to
`<repo>/.lyra/memory/reasoning_bank.sqlite`, every chat turn recalls
relevant lessons into the system prompt. This guide shows how to
inspect what's in the bank, seed it manually, and tune it.

For the conceptual grounding, see [ReasoningBank](../concepts/reasoning-bank.md).

## Quick reference

```bash
lyra memory stats                            # one-screen summary
lyra memory list                             # all lessons, newest first
lyra memory list --polarity failure          # only anti-skills
lyra memory recall "parse json"              # what would the bank surface?
lyra memory recall "parse json" --diversify  # MMR-reranked
lyra memory show l-primary-abc123            # one lesson in full
lyra memory record "parse json" success \    # seed manually
    --summary "use streaming parser when input > 10MB"
lyra memory wipe                             # nuke everything (asks first)
```

## Recipe: see what the bank knows about a turn

```bash
lyra memory recall "diff format with trailing newlines" --k 5
```

```text
Recall for 'diff format with trailing newlines'

  Polarity   Title                              Body
  ────────   ────────────────────────────────   ───────────────────────────────
  do         Strategy: trim diff trailing       Sequence that worked: view → edit → run pytest. Final artefact 1.2KB.
  avoid      Anti-skill: trim diff trailing     Sequence that failed: write whole file → pytest. Symptom: too much noise.
  do         Recovery hint: trim diff trailing  Trace contained a recovery candidate at step 4: use git apply --check first
```

`do` rows are SUCCESS lessons; `avoid` rows are FAILURE anti-skills.
The agent gets both at the start of any matching turn.

## Recipe: seed the bank with a hand-curated lesson

When you've just discovered a gotcha and want the next session to
know about it:

```bash
lyra memory record "supabase rls policy" failure \
    --summary "RLS rejected silently when client used service_role; switch to anon key" \
    --trajectory-id "manual-2026-05-01"
```

Confirm:

```bash
lyra memory recall "supabase rls"
```

The lesson will surface in any future session that mentions Supabase
or RLS in the user prompt.

## Recipe: programmatic use

```python
from pathlib import Path
from lyra_core.memory import (
    HeuristicDistiller,
    SqliteReasoningBank,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
    default_db_path,
)

bank = SqliteReasoningBank(
    distiller=HeuristicDistiller(),
    db_path=default_db_path(Path.cwd()),
)

# Record after a successful agent loop
bank.record(Trajectory(
    id="t-2026-05-01-supabase",
    task_signature="supabase rls policy",
    outcome=TrajectoryOutcome.SUCCESS,
    steps=(
        TrajectoryStep(0, "tool_call", "view supabase/migrations/policy.sql"),
        TrajectoryStep(1, "edit", "policy.sql"),
        TrajectoryStep(2, "tool_call", "bash supabase test"),
    ),
    final_artefact="diff: 12 lines",
))

# Recall before the next session
for lesson in bank.recall("supabase rls", k=4, diversity_weighted=True):
    print(f"[{lesson.polarity.value}] {lesson.title}")
```

## How the injector renders the block

The chat system prompt gets a *"## Relevant memory"* block prepended
when the bank or procedural memory has hits:

```markdown
## Relevant memory

### Procedural skills
Past patterns the team has captured for similar work. Cite the id and
read the body via the ``Read`` tool if you decide to apply one.

- supabase-rls-debug: Walk RLS policies for a table; verify against …

### Reasoning lessons
Distilled successes (``[do]``) and anti-skills (``[avoid]``) from
prior trajectories. Treat ``[avoid]`` items as documented failure
modes — explicitly check you are not repeating them.

- [avoid] Anti-skill: supabase rls policy: RLS rejected silently when
  client used service_role; switch to anon key.
- [do] Strategy: supabase rls policy: Sequence that worked: view →
  edit → bash supabase test. Final artefact 0.4KB.
```

The injector lives at
[`lyra_cli/interactive/memory_inject.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/interactive/memory_inject.py).
It accepts a `reasoning_bank=` parameter so an embedding caller can
pass an in-process bank; the default chat path opens the SQLite
bank lazily on first turn.

## Recipe: enable MaTTS for Tournament-TTS

If you're using Lyra's Tournament test-time scaling, wiring the bank
in is one parameter:

```python
from lyra_core.tts.tournament import TournamentTts, TtsBudget
from lyra_core.memory import (
    HeuristicDistiller, SqliteReasoningBank, default_db_path,
)
from pathlib import Path

bank = SqliteReasoningBank(
    distiller=HeuristicDistiller(),
    db_path=default_db_path(Path.cwd()),
)

tts = TournamentTts(
    generator=your_attempt_generator,
    discriminator=your_pairwise_judge,
    budget=TtsBudget(max_attempts=8, max_wall_clock_s=60, max_total_tokens=30_000),
    reasoning_bank=bank,
    matts_prefix_k=3,
)
result = tts.run("normalise dates across timezones")
```

Each of the 8 attempts now sees a different MaTTS prefix slice. Even
with a deterministic generator, the candidate pool diversifies — and
the diversity-collapse guard in
[Tournament-TTS](../research/index.md) is now meaningfully exercised.

## Recipe: backups and audits

The bank is one SQLite file. Backup is a copy:

```bash
cp .lyra/memory/reasoning_bank.sqlite .lyra/memory/reasoning_bank.sqlite.bak.$(date +%Y%m%d)
```

Audit the schema:

```bash
sqlite3 .lyra/memory/reasoning_bank.sqlite ".schema lessons"
sqlite3 .lyra/memory/reasoning_bank.sqlite "SELECT polarity, COUNT(*) FROM lessons GROUP BY polarity"
```

The on-disk format is documented in
[`reasoning_bank_store.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank_store.py)
and is forwards-compatible (additive migrations only).

## Recipe: project-scoped vs user-scoped banks

By default Lyra uses a **per-repo** bank
(`<repo>/.lyra/memory/reasoning_bank.sqlite`) so a team's lessons
about Supabase don't leak into a different project. Override:

```bash
# user-global bank (across all repos for this user)
lyra memory recall "parse json" --db ~/.lyra/memory/reasoning_bank.sqlite

# scratch bank for an experiment
lyra memory recall "x" --db /tmp/scratch.sqlite
```

A future release will support **layered recall** that merges per-repo
and per-user lessons at retrieval time; for now you pick one or the
other per command.

## Tuning notes

| Knob | Default | When to change |
|---|---|---|
| `--k` (recall depth) | 5 | Lower for small models with tight context; raise for high-frequency tasks |
| `--diversify` | off | On if recall keeps surfacing near-duplicates |
| `matts_prefix_k` | 3 | Higher = more memory per attempt = more diversity but more tokens |
| Distiller | Heuristic | Switch to `LLMDistiller` for richer lessons; budget for the smart-slot calls |

## When NOT to use the bank

- **Greenfield repo with no prior trajectories.** The bank starts
  empty and needs a few sessions before recall is useful. Seed
  manually if you have hand-curated lessons.
- **High-stakes deterministic CI runs.** The bank introduces
  per-session non-determinism (different lessons surface on
  different days). Pass `--no-memory` (planned for v3.1) or use a
  read-only `--db` snapshot.
- **Cross-project leakage risk.** Per-repo bank is the default for a
  reason; only switch to a user-global bank when you trust the
  signal across projects.

[← How-to index](index.md){ .md-button }
[Concept: ReasoningBank →](../concepts/reasoning-bank.md){ .md-button .md-button--primary }
