# lyra-evals

Evaluation harness for **Lyra**. Three corpora, one runner, one CI
gate. Current as of **v2.7.1** (2026-04-27).

```bash
lyra evals --bundle golden          # 100 curated TDD tasks (pytest, vitest, go test)
lyra evals --bundle red-team        # 30 sabotage / injection / prompt-leak scenarios
lyra evals --bundle long-horizon    # 10 multi-step DAG tasks
lyra evals --bundle swe-bench-pro   # contamination-resistant public benchmark (v1.5)
lyra evals --bundle loco-eval       # long-context retrieval benchmark (v1.5)
```

`/evals` from the REPL runs the same harness inline (v2.7.0): the
`_run_bundled` entry point is invoked from `lyra-cli` and renders
pass/total/rate live; pass `--full` for a JSON dump.

## Corpora

| Corpus          | Path                                | Count | Source                                                 |
|-----------------|-------------------------------------|-------|--------------------------------------------------------|
| `golden`        | `src/lyra_evals/golden/`            | 100   | curated TDD tasks (red-then-green, three runners)      |
| `red-team`      | `src/lyra_evals/red_team/`          | 30    | sabotage, prompt-leak, injection-driven tool misuse    |
| `long-horizon`  | `src/lyra_evals/long_horizon/`      | 10    | multi-step DAG tasks for the dag-teams harness         |
| `swe-bench-pro` | adapter only (data fetched at run)  | —     | public benchmark, loaded via the official corpus       |
| `loco-eval`     | adapter only (data fetched at run)  | —     | long-context retrieval; fetched via official corpus    |

Bundled corpora ship inside the wheel and require no network. The
public benchmark adapters fetch their data lazily and cache under
`~/.lyra/evals/cache/`.

## Runner

```python
from lyra_evals import Runner, Bundle

runner = Runner.for_bundle(Bundle.GOLDEN)
report = runner.run(parallel=4)
print(report.success_rate, report.drift_gate_tripped)
```

Every run journals to `.lyra/evals/runs/<run-id>.jsonl` (HIR-compatible
spans) so a regression is replayable, diffable, and bisectable.

## CI gates

* **Per-PR smoke**: `golden/smoke` (10 fast tasks).
* **Nightly full suite**: all bundled corpora; drift gate trips when
  p95 success drops > 5 % week-over-week (`docs/benchmarks.md`).
* **Public benchmark adapters** (v1.5): scheduled weekly because the
  data is large and the runner expensive.

## Model selection inside evals

The runner honours the same fast/smart slot routing as the rest of
Lyra (v2.7.1): the per-task agent loop runs on the **fast slot**
(default `deepseek-v4-flash` → `deepseek-chat`); planner phases and
the Phase-2 LLM evaluator run on the **smart slot** (default
`deepseek-v4-pro` → `deepseek-reasoner`). Override per run via:

```bash
lyra evals --bundle golden \
  --fast-model deepseek-v4-flash \
  --smart-model claude-opus-4-5
```

Or pin one universal model the way you would for `lyra run`:
`lyra evals --bundle golden --model gpt-5`.

## Testing the evals harness itself

```bash
# from projects/lyra/packages/lyra-evals/
uv run pytest -q
```

## See also

* [`projects/lyra/docs/roadmap.md`](../../docs/roadmap.md) — Phase 11 (release-candidate) and post-v1.5 evals plans.
* [`projects/lyra/docs/benchmarks.md`](../../docs/benchmarks.md) — headline numbers + methodology.
* [`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md) — per-release narrative, including when each corpus shipped.
