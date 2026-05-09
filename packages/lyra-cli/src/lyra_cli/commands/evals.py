"""`lyra evals` — smoke run over the bundled + public corpora.

The CLI wrapper does NOT ship Scale AI's evaluator or LoCoEval's oracle;
those are heavy and have their own licences. What the CLI does ship:

- Bundled corpora (golden, red-team, long-horizon) for dogfood health.
- Adapter dispatch for ``swe-bench-pro`` and ``loco-eval`` so operators
  can point the same command at a downloaded Pro JSONL / LoCoEval JSONL
  and get a matching submission artefact back.

The policy wired in the CLI is a stub; real runs replace it with the
``lyra`` loop. The wiring itself is what Phase 12 tests pin.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from lyra_evals import (
    EvalRunner,
    TaskResult,
    golden_tasks,
    long_horizon_tasks,
    red_team_tasks,
)
from lyra_evals.adapters import (
    ConversationDriver,
    LoCoEvalTask,
    PublicBenchmarkTask,
    SWEBenchProAdapter,
    load_swe_bench_pro,
    score_requirement_coverage,
    write_submission,
)

_PUBLIC_CORPORA = {"swe-bench-pro", "loco-eval"}


def _always_pass(task) -> TaskResult:  # type: ignore[no-untyped-def]
    return TaskResult(task_id=task.id, passed=True, reason="stub policy")


def _run_bundled(corpus_lc: str, drift_gate: float) -> dict[str, Any]:
    if corpus_lc == "golden":
        tasks = golden_tasks()
    elif corpus_lc in {"red-team", "red_team", "redteam"}:
        tasks = red_team_tasks()
    elif corpus_lc in {"long-horizon", "long_horizon", "longhorizon"}:
        tasks = long_horizon_tasks()
    else:
        raise typer.BadParameter(f"unknown corpus: {corpus_lc!r}")
    runner = EvalRunner(policy=_always_pass, drift_gate=drift_gate)
    return runner.run(tasks).to_dict()


def _run_swe_bench_pro(
    tasks_path: Path | None,
    budget: int | None,
    model: str,
    drift_gate: float,
    output: Path | None,
) -> dict[str, Any]:
    if tasks_path is None:
        typer.echo(
            "swe-bench-pro requires --tasks-path <path/to/pro.jsonl>; "
            "see docs/benchmarks.md. The adapter is available as "
            "lyra_evals.SWEBenchProAdapter for direct library use."
        )
        raise typer.Exit(code=2)
    tasks = load_swe_bench_pro(tasks_path, limit=budget)
    adapter = SWEBenchProAdapter(model_name_or_path=model)

    def stub_policy(_t: PublicBenchmarkTask) -> tuple[str, bool]:
        return ("", False)

    runner = EvalRunner(policy=adapter.policy(stub_policy), drift_gate=drift_gate)
    report = runner.run([adapter.as_generic_task(t) for t in tasks])
    if output is not None:
        write_submission(output, adapter.predictions())
        typer.echo(f"wrote submission: {output}")
    return report.to_dict()


def _run_loco_eval(
    tasks_path: Path | None, budget: int | None
) -> dict[str, Any]:
    if tasks_path is None:
        typer.echo(
            "loco-eval requires --tasks-path <path/to/loco.jsonl>; each line is "
            "{sample_id, repo, turns[], requirements[], context_budget_tokens}. "
            "The driver is available as lyra_evals.ConversationDriver."
        )
        raise typer.Exit(code=2)
    tasks_raw = tasks_path.read_text(encoding="utf-8").splitlines()
    scores: list[float] = []
    for idx, line in enumerate(tasks_raw):
        if budget is not None and idx >= budget:
            break
        row = json.loads(line)
        task = LoCoEvalTask(
            sample_id=row["sample_id"],
            repo=row.get("repo", ""),
            turns=tuple(row.get("turns", ())),
            requirements=tuple(row.get("requirements", ())),
            context_budget_tokens=int(row.get("context_budget_tokens", 0)),
            tokens_per_turn=int(row.get("tokens_per_turn", 1024)),
        )

        def echo_agent(_i: int, msg: str, _s) -> str:  # type: ignore[no-untyped-def]
            return f"echo: {msg}"

        ConversationDriver(agent=echo_agent).run(task)
        scores.append(
            score_requirement_coverage(task=task, satisfied=set(task.requirements))
        )
    coverage = sum(scores) / len(scores) if scores else 0.0
    return {
        "total": len(scores),
        "requirement_coverage": coverage,
    }


def _run_passk(passk: int, *, as_json: bool) -> dict[str, Any]:
    """Run the kernel golden corpus K times and report ``pass^k``.

    The model is a stub that always answers with the case prompt verbatim
    — that's enough to exercise the metric plumbing end-to-end. Real
    runs replace the callable with a wired LLM client; the surface
    remains the same.
    """
    from lyra_core.eval import default_corpus, run_passk

    cases = list(default_corpus())

    def _stub(prompt: str) -> str:
        return prompt

    report = run_passk(cases, k=passk, model_call=_stub)
    payload = report.to_dict()
    payload.setdefault("corpus", "passk-golden")
    return payload


def evals_command(
    corpus: str = typer.Option(
        "golden",
        help="golden | red-team | long-horizon | swe-bench-pro | loco-eval",
    ),
    drift_gate: float = typer.Option(0.85, help="success-rate floor"),
    tasks_path: Optional[Path] = typer.Option(  # noqa: UP045
        None, "--tasks-path", help="public-corpus JSONL on disk"
    ),
    budget: Optional[int] = typer.Option(  # noqa: UP045
        None, "--budget", help="cap tasks loaded (smoke / CI)"
    ),
    model: str = typer.Option(
        "lyra/mock", "--model", help="model_name_or_path for Pro submission"
    ),
    output: Optional[Path] = typer.Option(  # noqa: UP045
        None, "--output", help="write Pro submission JSONL here"
    ),
    passk: int = typer.Option(
        0,
        "--passk",
        help=(
            "When >0, run the kernel golden corpus K times per case "
            "and report pass@k / pass^k (τ-bench-style silent-flakiness "
            "probe). Mutually exclusive with --corpus public benchmarks."
        ),
    ),
    as_json: bool = typer.Option(False, "--json", help="emit JSON"),
) -> None:
    """Run a smoke pass over one of the bundled or public corpora."""
    if passk > 0:
        payload = _run_passk(passk, as_json=as_json)
        if as_json:
            typer.echo(json.dumps(payload, indent=2))
            return
        typer.echo(
            f"corpus={payload['corpus']} k={payload['k']} "
            f"total_cases={payload['total_cases']}"
        )
        typer.echo(
            f"pass@k={payload['pass_at_k']:.2f} "
            f"pass^k={payload['pass_pow_k']:.2f} "
            f"reliability_gap={payload['reliability_gap']:.2f}"
        )
        flaky = payload["flaky_cases"]
        if flaky:
            typer.echo(f"flaky cases: {', '.join(flaky)}")
        return

    corpus_lc = corpus.strip().lower()
    if corpus_lc == "swe-bench-pro":
        payload = _run_swe_bench_pro(
            tasks_path, budget, model, drift_gate, output
        )
        corpus_name = "swe-bench-pro"
    elif corpus_lc == "loco-eval":
        payload = _run_loco_eval(tasks_path, budget)
        corpus_name = "loco-eval"
    elif corpus_lc in _PUBLIC_CORPORA:  # future-proofing
        raise typer.BadParameter(f"unknown public corpus: {corpus!r}")
    else:
        payload = _run_bundled(corpus_lc, drift_gate)
        corpus_name = corpus_lc

    if as_json:
        out_payload = dict(payload)
        out_payload["corpus"] = corpus_name
        typer.echo(json.dumps(out_payload, indent=2))
        return

    if "success_rate" in payload:
        typer.echo(
            f"corpus={corpus_name} total={payload['total']} passed={payload['passed']}"
        )
        typer.echo(
            f"success_rate={payload['success_rate']:.2f} "
            f"drift_gate_tripped={payload['drift_gate_tripped']}"
        )
    else:
        typer.echo(
            f"corpus={corpus_name} total={payload['total']} "
            f"requirement_coverage={payload['requirement_coverage']:.2f}"
        )
