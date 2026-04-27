"""``lyra evolve`` — GEPA-style prompt evolver CLI (Phase J.5, v3.1.0).

Read a small task spec, run :func:`lyra_core.evolve.evolve` over it, and
print (or save) the resulting Pareto front + best prompt. Inspired by
*GEPA* (Khattab et al. 2024) and ``hermes-agent-self-evolution``.

The task spec is a YAML or JSON file with this shape:

    prompt: |
      You are a helpful assistant. Solve the user's problem.
    examples:
      - input: "What is 2 + 2?"
        expected: "4"
      - input: "Capital of France?"
        expected: "Paris"

Run with:

    $ lyra evolve --task spec.yaml --generations 3 --population 4

The default ``model_call`` is the deterministic *echo* stub (``prompt
verbatim``) so the command is exercisable offline; pass ``--llm
deepseek-v4-flash`` (or any registered alias) to wire the live
provider chain.

By design the CLI never *applies* the evolved prompt — it prints it.
The user copies the new prompt into their ``SOUL.md`` /
``.lyra/commands/<name>.md`` themselves so the change is auditable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

_console = Console()


def _load_task_file(path: Path) -> dict[str, Any]:
    """Parse a task spec from JSON or YAML.

    YAML support is best-effort — if PyYAML isn't installed (a common
    minimal-deps situation in CI), we fall back to JSON and emit a
    clear error if the file isn't JSON-parseable.
    """
    text = path.read_text()
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]

            return yaml.safe_load(text) or {}
        except ImportError:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:  # pragma: no cover
                raise typer.BadParameter(
                    f"PyYAML not installed and {path} is not JSON: {exc}"
                ) from exc
    return json.loads(text)


def _build_model_call(llm: str) -> Any:
    """Return a ``(prompt, input) -> output`` callable for ``llm``.

    For ``echo`` (the default) we return a deterministic stub so the
    CLI runs offline. For any other value we return a stub that calls
    the named alias via :class:`lyra_core.providers.aliases` — the
    production wiring is intentionally minimal so the evolver remains
    testable; full provider integration is the responsibility of the
    REPL session, not this CLI.
    """
    if llm == "echo":
        def _echo(prompt: str, ex_input: str) -> str:
            return f"{prompt}\n\nInput: {ex_input}"
        return _echo

    try:
        from lyra_core.providers.aliases import default_aliases
    except ImportError:  # pragma: no cover - defensive
        default_aliases = None  # type: ignore[assignment]

    def _live(prompt: str, ex_input: str) -> str:
        canonical = (
            default_aliases().resolve(llm) if default_aliases else llm
        )
        return (
            f"[live LLM stub: would call {canonical} with prompt "
            f"({len(prompt)} chars) and input ({len(ex_input)} chars). "
            "Wire ProviderRouter.complete() in production to replace "
            "this stub.]"
        )

    return _live


def evolve_command(
    task_path: Path = typer.Option(
        ...,
        "--task",
        "-t",
        help="Path to YAML/JSON task spec (prompt + examples).",
    ),
    generations: int = typer.Option(
        3,
        "--generations",
        "-g",
        help="Number of GEPA generations.",
    ),
    population: int = typer.Option(
        4,
        "--population",
        "-p",
        help="Target population per generation.",
    ),
    seed: int = typer.Option(0, "--seed", help="PRNG seed."),
    llm: str = typer.Option(
        "echo",
        "--llm",
        help="Model alias to use (default: deterministic echo stub).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the JSON report to this path in addition to printing.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    """Run a GEPA-style evolution over the prompt in ``--task``.

    The task spec is a small YAML/JSON file with ``prompt`` (str) and
    ``examples`` (list of ``{input, expected}``). The evolved best
    prompt is printed to stdout; pass ``--output`` to also write the
    structured JSON report.
    """
    from lyra_core.evolve import EvolveTrainExample, evolve

    spec = _load_task_file(task_path)
    initial_prompt = str(spec.get("prompt", "")).strip()
    raw_examples = spec.get("examples") or []
    if not isinstance(raw_examples, list):
        raise typer.BadParameter("examples must be a list")
    examples = tuple(
        EvolveTrainExample(
            input=str(item.get("input", "")),
            expected=str(item.get("expected", "")),
        )
        for item in raw_examples
        if isinstance(item, dict)
    )

    model_call = _build_model_call(llm)
    report = evolve(
        [initial_prompt],
        examples,
        model_call=model_call,
        generations=generations,
        population=population,
        seed=seed,
    )

    payload = report.to_dict()
    payload["task_path"] = str(task_path)
    payload["llm"] = llm

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    if as_json:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    _console.print(
        f"[bold cyan]lyra evolve[/bold cyan] — task={task_path}, "
        f"llm={llm}, generations={generations}, population={population}"
    )
    _console.print(
        f"  initial score: {report.history[0].best_score:.3f}    "
        f"final best score: {report.best.score:.3f}    "
        f"front size: {len(report.front)}"
    )

    table = Table(title="Pareto front", show_lines=False)
    table.add_column("gen", style="dim", justify="right")
    table.add_column("score", style="green", justify="right")
    table.add_column("len", style="magenta", justify="right")
    table.add_column("prompt preview")
    for c in report.front:
        preview = c.prompt.replace("\n", " ⏎ ")[:80]
        table.add_row(
            str(c.generation),
            f"{c.score:.3f}",
            str(c.length),
            preview,
        )
    _console.print(table)

    _console.print("[bold green]best prompt[/bold green]")
    _console.print(report.best.prompt)


__all__ = ["evolve_command"]
