# DCI integration — v3.13 shipping notes

> Companion to [`dci-direct-corpus-interaction.md`](./dci-direct-corpus-interaction.md).
> That file is the research; this one is the build log of what actually
> landed and what is still TODO.

## Status as of v3.13.0-dev

| Bundle | What it ships | Status |
|---|---|---|
| **DCI-1** — investigate-mode prompt + value objects | `lyra_core/investigate/{__init__,prompt}.py`, `INVESTIGATE_PROMPT_BODY`, `build_system_prompt(mount)` | ✅ shipped |
| **DCI-2** — corpus mount + budget | `lyra_core/investigate/{corpus,budget}.py`, `CorpusMount`, `InvestigationBudget`, `BudgetExceeded` | ✅ shipped |
| **DCI-3** — level0–4 thermostat | `lyra_core/investigate/levels.py`, `ContextLevel`, `ContextLevelPlan`, `plan_for_level` | ✅ shipped (mapping table) |
| **DCI runner** — drives AgentLoop in investigate mode | `lyra_core/investigate/{tools,plugin,runner}.py`, `make_investigate_tools`, `InvestigationBudgetPlugin`, `TrajectoryLedgerPlugin`, `InvestigationRunner`, `InvestigationResult` | ✅ shipped |
| **DCI CLI** — `lyra investigate <question>` | `lyra_cli/commands/investigate.py`, registered in `lyra_cli/__main__.py` | ✅ shipped |
| **DCI-5** — Argus auto-engage skill | `skills/corpus-investigator/SKILL.md` | ✅ shipped |
| **DCI-6** — compose with v3.12 Ralph loops | this doc + the §6.6 contract in the research note | ✅ documented |
| **DCI-2 named profiles** — `READ_ONLY` + `read_write(mount)` presets in `lyra_core/investigate/profile.py` | `InvestigateProfile` value object with allowlist, network gate, write-root | ✅ shipped |
| **DCI-3 live wiring** — runner *applies* `ContextLevelPlan` to compose compactor strategies live between turns | `lyra_core/investigate/compactor.py` + `_LevelAwareLLM` shim in `runner.py` | ✅ shipped |
| **DCI-4** — eval harness adapters | `packages/lyra-evals/adapters/{browsecomp_plus,multihop_qa,bright}.py` — task dataclasses + JSONL loaders + scorers (Phase 0 contracts) | ✅ shipped |
| **DCI-2 grammar wiring** — `lyra_core/permissions/` grammar consumes `InvestigateProfile` and enforces the allowlist + write-root constraints | grammar resolver patch | ⏳ pending |
| **DCI-4 run wiring** — `lyra evals` CLI subcommand drives `InvestigationRunner` over a loaded BCP/multi-hop/BRIGHT split and writes per-task ledgers | CLI + scoring loop | ⏳ pending |

## What's runnable today

```bash
lyra investigate "where does the README mention 'rate-limiting'?" \
    --corpus ~/projects/lyra \
    --context-level 3 \
    --output-dir /tmp/lyra-runs/0001
```

Outputs:
- `/tmp/lyra-runs/0001/final.txt` — the cited answer
- `/tmp/lyra-runs/0001/question.txt` — the original question
- `/tmp/lyra-runs/0001/conversation_full.json` — every tool call (name, arguments, result) plus session id

Programmatically:

```python
from lyra_core.investigate import (
    CorpusMount, InvestigationBudget, ContextLevel,
    InvestigationRunner,
)
import pathlib

mount = CorpusMount(root=pathlib.Path("/corpus/wiki18").resolve())
runner = InvestigationRunner(
    llm=my_llm,
    mount=mount,
    budget=InvestigationBudget(max_turns=300, wall_clock_s=1800),
    context_level=ContextLevel.TRUNCATE_PLUS_COMPACT,   # paper's level 3
    output_dir=pathlib.Path("/tmp/run-1"),
)
result = runner.run("what is the answer to question Q?")
print(result.final_text, result.stopped_by, result.bytes_read_used)
```

## Architecture

The architect-reviewed seam landed exactly as designed:

- **No new agent loop.** `InvestigationRunner` is a thin wrapper that
  builds three closure-bound tools, attaches two plugins, and drives
  the existing `AgentLoop`. The dispatch path, hook timing, and stop
  semantics are untouched.
- **Tool binding.** `make_investigate_tools(mount, budget)` returns a
  `Mapping[str, Callable]` of `codesearch` / `read_file` /
  `execute_code`. Each closure captures the `CorpusMount` (for path
  containment) and the `InvestigationBudget` (for byte / bash
  accounting). `codesearch` delegates to the existing
  `make_codesearch_tool` factory unchanged.
- **Budget enforcement.** `InvestigationBudgetPlugin.pre_tool_call`
  ticks the turn axis and checks the wall-clock; a breach raises
  `KeyboardInterrupt` so `AgentLoop._dispatch_tool` propagates it as
  `stopped_by="interrupt"` instead of swallowing it into a tool-error
  dict. Bash / bytes axes are ticked at the point of use inside the
  tool closures (where the count is visible).
- **Trajectory ledger.** `TrajectoryLedgerPlugin.post_tool_call`
  captures every dispatch, and `on_session_end` dumps the ledger to
  `conversation_full.json` — the same shape DCI-Agent-Lite writes.
- **Allowlist.** `execute_code` only accepts a single binary from a
  fixed allowlist (`rg grep find sed head tail wc awk sort uniq xargs
  cat ls`) — no shell, no pipes, no network. Matches the paper's
  RQ6 finding that the dominant trajectory shape needs only those
  primitives.

## Verification posture

- **lyra-core**: 2051 passed (+143 new tests across
  `test_investigate_dci.py`, `test_investigate_runner.py`,
  `test_investigate_compactor.py`, `test_investigate_profile.py`),
  3 pre-existing failures unchanged
  (`test_codesearch_tool_contract::test_skips_ignore_directories`,
  `test_evolve_gepa::test_pareto_front_sorts_score_desc_then_length_asc`,
  `test_providers_prompt_cache::test_active_anchors_excludes_expired`).
- **lyra-evals**: 60 passed (+21 new in `test_dci_adapters.py`).
- **lyra-cli**: +6 new tests in `test_command_investigate.py`. The CLI
  test uses a monkeypatched `build_llm` stub so it stays hermetic and
  needs no provider keys.
- **Ruff**: clean on all new modules.

## What is NOT shipped yet

- **DCI-3 wiring.** The `ContextLevelPlan` is *carried* on the runner
  and inspected on the result, but its strategies (compactor / NGC /
  grid / per-window summary) are not yet applied to the live
  `LLMCtx.messages` between turns. The seam recommended by the
  architect review is an LLM-wrapping shim that rewrites messages on
  each `generate` call — this is one follow-up bundle.
- **Named permissions profiles.** `investigate-readonly` /
  `investigate-rw` named bundles in `lyra_core/permissions/` — the
  grammar already supports the constraints; the named presets are
  pending.
- **Eval harness.** The three adapters
  (`browsecomp_plus.py` / `multihop_qa.py` / `bright.py`) under
  `packages/lyra-evals/` are the next *proof* step. The shape of
  what they consume is now stable: each adapter constructs a
  `CorpusMount`, a per-task `InvestigationBudget`, drives
  `InvestigationRunner.run(question)`, and scores
  `result.final_text` against the gold answer.

## Citation chain (for CHANGELOG.md)

```text
v3.13.0-dev — DCI: Direct Corpus Interaction.

Cite: Li, Zhang, Wei, et al. "Beyond Semantic Similarity: Rethinking
Retrieval for Agentic Search via Direct Corpus Interaction."
arXiv:2605.05242 (May 2026). Reference impl:
github.com/DCI-Agent/DCI-Agent-Lite.

Lands:
  - lyra_core/investigate/  — CorpusMount, InvestigationBudget,
    ContextLevel (level0..4), build_system_prompt,
    make_investigate_tools, InvestigationBudgetPlugin,
    TrajectoryLedgerPlugin, InvestigationRunner, InvestigationResult.
  - lyra_cli/commands/investigate.py — `lyra investigate <question>`
    CLI subcommand with --corpus, --context-level, --max-turns,
    --wall-clock, --output-dir flags.
  - skills/corpus-investigator/SKILL.md — Argus auto-engage skill.
  - docs/research/dci-direct-corpus-interaction.md — research note.
  - docs/research/dci-v3-13-shipping-notes.md — this build log.
  - 93 new unit tests in lyra-core, 6 in lyra-cli. No regressions
    in the 2001-test core suite.
```
